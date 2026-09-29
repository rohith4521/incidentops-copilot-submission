"""Production-grade circuit breaker for external dependencies (Phase 7.6).

Implements the standard state machine:
CLOSED ──(failure threshold reached)──> OPEN
  ▲                                       │
  │ (probe succeeds)                      │ (recovery timeout expires)
  │                                       ▼
  └────────────────────────────────── HALF_OPEN ──(probe fails)──> OPEN

Invariants:
1. Thread-safe and asyncio-concurrency safe.
2. Only genuine dependency failures increment the failure count.
3. Valid empty or no-match recall results count as success, NOT failures.
4. When OPEN, requests fail fast without calling external dependency.
5. In HALF_OPEN, allows exactly one probe; concurrent requests fail fast.
6. Full observability of breaker state, failure counts, and trip metrics.
"""

from enum import Enum
import asyncio
import logging
import time
from typing import Any, Dict, Optional, Tuple

import aiohttp

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    """Circuit breaker operational states."""
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class CircuitOpenError(Exception):
    """Raised or flagged when request is rejected because the circuit is OPEN."""
    def __init__(self, message: str = "Hindsight circuit breaker is OPEN (fail-fast active).", retry_after: float = 0.0):
        super().__init__(message)
        self.retry_after = retry_after


class HindsightCircuitBreaker:
    """Asyncio-aware, thread-safe circuit breaker protecting the Hindsight dependency."""

    def __init__(
        self,
        failure_threshold: int = 3,
        recovery_timeout: float = 30.0,
        request_timeout: float = 10.0,
        name: str = "hindsight-memory-engine",
    ):
        self.name = name
        self.failure_threshold = max(1, int(failure_threshold))
        self.recovery_timeout = max(0.01, float(recovery_timeout))
        self.request_timeout = max(0.01, float(request_timeout))

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time: Optional[float] = None
        self._last_state_change: float = time.monotonic()
        self._half_open_probe_in_flight: bool = False

        # Operational metrics
        self._total_calls = 0
        self._successful_calls = 0
        self._failed_calls = 0
        self._fast_failed_calls = 0
        self._trip_count = 0
        self._probe_count = 0

        self._lock = asyncio.Lock()

    @property
    def state(self) -> CircuitState:
        return self._state

    @property
    def failure_count(self) -> int:
        return self._failure_count

    @property
    def is_open(self) -> bool:
        return self._state == CircuitState.OPEN

    @property
    def is_half_open(self) -> bool:
        return self._state == CircuitState.HALF_OPEN

    @property
    def is_closed(self) -> bool:
        return self._state == CircuitState.CLOSED

    def reset(self) -> None:
        """Reset circuit breaker to pristine CLOSED state (useful for test isolation)."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time = None
        self._last_state_change = time.monotonic()
        self._half_open_probe_in_flight = False
        self._total_calls = 0
        self._successful_calls = 0
        self._failed_calls = 0
        self._fast_failed_calls = 0
        self._trip_count = 0
        self._probe_count = 0

    @staticmethod
    def is_dependency_failure(exc: Exception) -> bool:
        """Categorize whether an exception is a genuine dependency failure.
        
        Genuine dependency failures:
        - Network connection drops, resets, refused connections (aiohttp.ClientError, ConnectionError, OSError)
        - Timeouts (asyncio.TimeoutError, socket timeouts)
        - HTTP 5xx responses from Hindsight API (500, 502, 503, 504)
        
        NOT dependency failures:
        - Empty recall results (normal valid responses)
        - Relevance rejections (valid operational decisions)
        - 404 Bank Not Found
        - Client input validation errors
        """
        if isinstance(exc, (aiohttp.ClientError, asyncio.TimeoutError, ConnectionError, OSError)):
            return True

        status_code = getattr(exc, "status", None) or getattr(exc, "status_code", None)
        if isinstance(status_code, int) and status_code >= 500:
            return True

        msg = str(exc).lower()
        dependency_error_signatures = [
            "connection refused", "connect call failed", "connection reset",
            "timed out", "timeout", "502 bad gateway", "503 service unavailable",
            "504 gateway timeout", "500 internal server error", "unreachable",
            "cannot connect to host", "name resolution failure", "cluster unreachable",
        ]
        return any(sig in msg for sig in dependency_error_signatures)

    async def can_execute(self) -> Tuple[bool, Optional[str]]:
        """Check if an execution is permitted under current circuit state.
        
        Returns:
            (True, None) if call is allowed (CLOSED or allocated the single HALF_OPEN probe).
            (False, reason) if call is rejected (fail fast).
        """
        async with self._lock:
            self._total_calls += 1
            now = time.monotonic()

            if self._state == CircuitState.CLOSED:
                return True, None

            if self._state == CircuitState.OPEN:
                # Check if recovery timeout has elapsed
                elapsed = (now - self._last_failure_time) if self._last_failure_time else 0.0
                if elapsed >= self.recovery_timeout:
                    # Allow exactly ONE probe to transition into HALF_OPEN
                    if not self._half_open_probe_in_flight:
                        self._state = CircuitState.HALF_OPEN
                        self._last_state_change = now
                        self._half_open_probe_in_flight = True
                        self._probe_count += 1
                        logger.info(
                            "[%s CircuitBreaker] Recovery timeout (%.2fs) elapsed. "
                            "Transitioning OPEN -> HALF_OPEN. Permitting 1 probe request.",
                            self.name, self.recovery_timeout,
                        )
                        return True, None
                    else:
                        # Another concurrent request already grabbed the single probe slot
                        self._fast_failed_calls += 1
                        return False, "hindsight_circuit_open"
                else:
                    self._fast_failed_calls += 1
                    return False, "hindsight_circuit_open"

            if self._state == CircuitState.HALF_OPEN:
                # Probe already in flight, reject all other concurrent requests
                self._fast_failed_calls += 1
                return False, "hindsight_circuit_open"

            return False, "hindsight_circuit_open"

    async def record_success(self) -> None:
        """Record a successful execution against the dependency."""
        async with self._lock:
            self._successful_calls += 1
            if self._state == CircuitState.HALF_OPEN:
                logger.info(
                    "[%s CircuitBreaker] HALF_OPEN probe succeeded. "
                    "Transitioning HALF_OPEN -> CLOSED. Normal operations restored.",
                    self.name,
                )
                self._state = CircuitState.CLOSED
                self._last_state_change = time.monotonic()
                self._failure_count = 0
                self._half_open_probe_in_flight = False
                self._last_failure_time = None
            elif self._state == CircuitState.CLOSED:
                self._failure_count = 0

    async def record_failure(self, exc: Exception) -> bool:
        """Record an execution failure against the dependency.
        
        Returns:
            True if the circuit tripped/reopened to OPEN, False otherwise.
        """
        if not self.is_dependency_failure(exc):
            logger.debug("[%s CircuitBreaker] Ignoring non-dependency error: %s", self.name, exc)
            return False

        async with self._lock:
            now = time.monotonic()
            self._failed_calls += 1
            self._last_failure_time = now

            if self._state == CircuitState.HALF_OPEN:
                logger.warning(
                    "[%s CircuitBreaker] HALF_OPEN probe failed (%s). "
                    "Transitioning HALF_OPEN -> OPEN. Resetting recovery window.",
                    self.name, exc,
                )
                self._state = CircuitState.OPEN
                self._last_state_change = now
                self._half_open_probe_in_flight = False
                self._trip_count += 1
                return True

            elif self._state == CircuitState.CLOSED:
                self._failure_count += 1
                logger.warning(
                    "[%s CircuitBreaker] Dependency failure #%d/%d: %s",
                    self.name, self._failure_count, self.failure_threshold, exc,
                )
                if self._failure_count >= self.failure_threshold:
                    logger.error(
                        "[%s CircuitBreaker] Failure threshold (%d) reached. "
                        "Transitioning CLOSED -> OPEN. Fail-fast active for %.2fs.",
                        self.name, self.failure_threshold, self.recovery_timeout,
                    )
                    self._state = CircuitState.OPEN
                    self._last_state_change = now
                    self._trip_count += 1
                    return True

            return False

    def get_status(self) -> Dict[str, Any]:
        """Return diagnostic metrics and state dictionary."""
        now = time.monotonic()
        time_in_state = round(now - self._last_state_change, 2)
        remaining_recovery = 0.0
        if self._state == CircuitState.OPEN and self._last_failure_time:
            remaining_recovery = max(0.0, round(self.recovery_timeout - (now - self._last_failure_time), 2))

        return {
            "name": self.name,
            "state": self._state.value,
            "failure_count": self._failure_count,
            "failure_threshold": self.failure_threshold,
            "recovery_timeout_seconds": self.recovery_timeout,
            "request_timeout_seconds": self.request_timeout,
            "time_in_current_state_seconds": time_in_state,
            "remaining_recovery_seconds": remaining_recovery,
            "half_open_probe_in_flight": self._half_open_probe_in_flight,
            "metrics": {
                "total_calls": self._total_calls,
                "successful_calls": self._successful_calls,
                "failed_calls": self._failed_calls,
                "fast_failed_calls": self._fast_failed_calls,
                "trip_count": self._trip_count,
                "probe_count": self._probe_count,
            },
        }
