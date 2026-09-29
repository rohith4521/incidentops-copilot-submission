"""Backend Metrics Service (Phase 6.8A).

Process-local metrics collector for IncidentOps Copilot.
Tracks operational throughput, failures, retries, security detections,
and latency percentiles for Hindsight and LLM inference.
"""

from datetime import datetime, timezone
import threading
from typing import Any, Dict, List


class MetricsService:
    """Thread-safe, process-local metrics aggregator."""

    def __init__(self):
        self._lock = threading.Lock()
        self._start_time = datetime.now(timezone.utc)
        self.reset()

    def reset(self) -> None:
        """Reset all metrics counters and latency histories (useful for testing)."""
        with self._lock:
            self._total_requests = 0
            self._triage_requests = 0
            self._triage_failures = 0
            self._hindsight_failures = 0
            self._llm_failures = 0
            self._llm_retries = 0
            self._degraded_triage_count = 0
            self._webhook_requests = 0
            self._webhook_duplicates = 0
            self._injection_detections = 0
            self._provenance_verification_count = 0
            self._rejected_untrusted_memory_count = 0
            self._hindsight_cb_fast_fails = 0
            self._hindsight_latencies: List[float] = []
            self._llm_latencies: List[float] = []

    # Counters
    def inc_total_requests(self, count: int = 1) -> None:
        with self._lock:
            self._total_requests += count

    def inc_triage_requests(self, count: int = 1) -> None:
        with self._lock:
            self._triage_requests += count

    def inc_triage_failures(self, count: int = 1) -> None:
        with self._lock:
            self._triage_failures += count

    def inc_hindsight_failures(self, count: int = 1) -> None:
        with self._lock:
            self._hindsight_failures += count

    def inc_llm_failures(self, count: int = 1) -> None:
        with self._lock:
            self._llm_failures += count

    def inc_llm_retries(self, count: int = 1) -> None:
        with self._lock:
            self._llm_retries += count

    def inc_degraded_triage_count(self, count: int = 1) -> None:
        with self._lock:
            self._degraded_triage_count += count

    def inc_webhook_requests(self, count: int = 1) -> None:
        with self._lock:
            self._webhook_requests += count

    def inc_webhook_duplicates(self, count: int = 1) -> None:
        with self._lock:
            self._webhook_duplicates += count

    def inc_injection_detections(self, count: int = 1) -> None:
        with self._lock:
            self._injection_detections += count

    def inc_provenance_verification_count(self, count: int = 1) -> None:
        with self._lock:
            self._provenance_verification_count += count

    def inc_rejected_untrusted_memory_count(self, count: int = 1) -> None:
        with self._lock:
            self._rejected_untrusted_memory_count += count

    def inc_hindsight_circuit_breaker_fast_fails(self, count: int = 1) -> None:
        with self._lock:
            self._hindsight_cb_fast_fails += count

    # Latency observations
    def record_hindsight_latency(self, duration_ms: float) -> None:
        if duration_ms is None or duration_ms < 0:
            return
        with self._lock:
            self._hindsight_latencies.append(round(duration_ms, 3))
            # Keep bounded window to prevent memory leak
            if len(self._hindsight_latencies) > 2000:
                self._hindsight_latencies = self._hindsight_latencies[-1000:]

    def record_llm_latency(self, duration_ms: float) -> None:
        if duration_ms is None or duration_ms < 0:
            return
        with self._lock:
            self._llm_latencies.append(round(duration_ms, 3))
            if len(self._llm_latencies) > 2000:
                self._llm_latencies = self._llm_latencies[-1000:]

    def _calc_stats(self, values: List[float]) -> Dict[str, Any]:
        """Calculate count, min, max, avg, p50, and p95 for a list of latency samples."""
        if not values:
            return {
                "count": 0,
                "latest_ms": 0.0,
                "avg_ms": 0.0,
                "min_ms": 0.0,
                "max_ms": 0.0,
                "p50_ms": 0.0,
                "p95_ms": 0.0,
            }
        sorted_vals = sorted(values)
        count = len(sorted_vals)
        latest = values[-1]
        avg_val = round(sum(sorted_vals) / count, 3)
        min_val = sorted_vals[0]
        max_val = sorted_vals[-1]

        idx_50 = min(int(count * 0.50), count - 1)
        idx_95 = min(int(count * 0.95), count - 1)

        return {
            "count": count,
            "latest_ms": latest,
            "avg_ms": avg_val,
            "min_ms": min_val,
            "max_ms": max_val,
            "p50_ms": sorted_vals[idx_50],
            "p95_ms": sorted_vals[idx_95],
        }

    def get_metrics(self) -> Dict[str, Any]:
        """Return snapshot of all process-local counters and latency distributions."""
        with self._lock:
            uptime = (datetime.now(timezone.utc) - self._start_time).total_seconds()
            data = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "uptime_seconds": round(uptime, 2),
                "total_requests": self._total_requests,
                "triage_requests": self._triage_requests,
                "triage_failures": self._triage_failures,
                "hindsight_failures": self._hindsight_failures,
                "hindsight_circuit_breaker_fast_fails": self._hindsight_cb_fast_fails,
                "llm_failures": self._llm_failures,
                "llm_retries": self._llm_retries,
                "degraded_triage_count": self._degraded_triage_count,
                "webhook_requests": self._webhook_requests,
                "webhook_duplicates": self._webhook_duplicates,
                "injection_detections": self._injection_detections,
                "provenance_verification_count": self._provenance_verification_count,
                "rejected_untrusted_memory_count": self._rejected_untrusted_memory_count,
                "latencies": {
                    "hindsight_recall": self._calc_stats(self._hindsight_latencies),
                    "llm_inference": self._calc_stats(self._llm_latencies),
                },
            }

            try:
                from app.services.hindsight_service import hindsight_service
                if hasattr(hindsight_service, "circuit_breaker"):
                    data["hindsight_circuit_breaker"] = hindsight_service.circuit_breaker.get_status()
            except Exception:
                pass

            return data


# Global metrics service singleton
metrics_service = MetricsService()
