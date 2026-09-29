"""Authentication and Identity Verification Service for SRE Memory Lifecycle (Phase 6.3A).

Enforces:
1. Protection of memory verification and commit endpoints with JWT or API-key authentication.
2. Verified identity extraction from validated credentials (never trusting client-supplied strings).
3. Rejection of unauthenticated or invalid requests with HTTP 401.
4. Strict blocking of AI self-verification (HTTP 403 / demotion to DRAFT).
"""

from datetime import datetime, timedelta, timezone
import logging
from typing import Dict, Optional, Tuple
from fastapi import Header, HTTPException, Request
import jwt

from app.config import settings
from app.models.auth import AuthenticatedUser

logger = logging.getLogger("incidentops.auth")


def parse_api_keys() -> Dict[str, Tuple[str, str, bool]]:
    """Parse configured SRE API keys into mapping: key -> (identity, role, is_human)."""
    mapping: Dict[str, Tuple[str, str, bool]] = {}
    raw = settings.auth_sre_api_keys
    if not raw:
        return mapping

    for entry in raw.split(","):
        entry = entry.strip()
        if not entry:
            continue
        parts = entry.split(":")
        if len(parts) >= 2:
            key = parts[0].strip()
            identity = parts[1].strip()
            role = parts[2].strip() if len(parts) >= 3 else "sre"
            is_human = parts[3].strip().lower() != "false" if len(parts) >= 4 else (role != "ai_agent")
            mapping[key] = (identity, role, is_human)
    return mapping


def create_access_token(
    identity: str,
    role: str = "sre",
    is_human: bool = True,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Generate a signed SRE JWT access token for authenticated human verification."""
    now = datetime.now(timezone.utc)
    delta = expires_delta or timedelta(hours=24)
    expire = now + delta

    payload = {
        "sub": identity,
        "identity": identity,
        "role": role,
        "is_human": is_human,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "iss": "incidentops-copilot",
    }

    return jwt.encode(
        payload,
        settings.auth_jwt_secret or "",
        algorithm=settings.auth_jwt_algorithm,
    )


async def get_current_authenticated_user(
    request: Request,
    authorization: Optional[str] = Header(None),
    x_api_key: Optional[str] = Header(None),
) -> AuthenticatedUser:
    """FastAPI dependency: Authenticate incoming request via JWT Bearer token or SRE API key.

    Raises:
        HTTPException(401): If credentials are missing, malformed, invalid, or expired.
    """
    # 1. Check API Key
    if x_api_key:
        api_keys = parse_api_keys()
        if x_api_key in api_keys:
            identity, role, is_human = api_keys[x_api_key]
            logger.info("Authenticated SRE via API key: identity='%s', role='%s'", identity, role)
            return AuthenticatedUser(
                identity=identity,
                role=role,
                auth_type="api_key",
                is_human=is_human,
            )
        logger.warning("Rejected invalid SRE API key: '%s...'", x_api_key[:6] if len(x_api_key) > 6 else x_api_key)
        raise HTTPException(
            status_code=401,
            detail="Invalid SRE API key.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # 2. Check JWT Bearer token
    if authorization:
        if not authorization.startswith("Bearer "):
            raise HTTPException(
                status_code=401,
                detail="Invalid authorization scheme. Expected 'Bearer <token>'.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        token = authorization[7:].strip()
        try:
            payload = jwt.decode(
                token,
                settings.auth_jwt_secret or "",
                algorithms=[settings.auth_jwt_algorithm],
            )
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=401,
                detail="SRE authentication token has expired.",
                headers={"WWW-Authenticate": "Bearer error=\"invalid_token\", error_description=\"token expired\""},
            )
        except (jwt.PyJWTError, Exception) as e:
            raise HTTPException(
                status_code=401,
                detail=f"Invalid SRE authentication token: {str(e)}",
                headers={"WWW-Authenticate": "Bearer error=\"invalid_token\""},
            )

        identity = str(payload.get("sub") or payload.get("identity") or "")
        if not identity:
            raise HTTPException(
                status_code=401,
                detail="Authentication token missing subject identity.",
            )

        role = payload.get("role", "sre")
        is_human = payload.get("is_human", True)

        logger.info("Authenticated SRE via JWT: identity='%s', role='%s', is_human=%s", identity, role, is_human)
        return AuthenticatedUser(
            identity=identity,
            role=role,
            auth_type="jwt",
            is_human=is_human,
        )

    # 3. Missing credentials -> 401
    raise HTTPException(
        status_code=401,
        detail="Authentication credentials required for memory verification. Provide Bearer JWT token or X-API-Key.",
        headers={"WWW-Authenticate": "Bearer, ApiKey"},
    )


async def require_human_verifier(
    request: Request,
    authorization: Optional[str] = Header(None),
    x_api_key: Optional[str] = Header(None),
) -> AuthenticatedUser:
    """Dependency: Require authenticated operator AND enforce that caller is human (no AI self-verification)."""
    user = await get_current_authenticated_user(
        request=request,
        authorization=authorization,
        x_api_key=x_api_key,
    )

    # Strictly block AI self-verification
    is_ai = (
        not user.is_human
        or user.role.lower() in ("ai", "ai_agent", "copilot", "llm", "bot")
        or "ai" in user.identity.lower()
        or "copilot" in user.identity.lower()
    )

    if is_ai:
        logger.warning(
            "[SECURITY] Blocked AI self-verification attempt by identity='%s' (role='%s')",
            user.identity,
            user.role,
        )
        raise HTTPException(
            status_code=403,
            detail=(
                f"Identity '{user.identity}' is recognized as an automated AI agent. "
                "AI agents are strictly forbidden from self-verifying post-mortems. "
                "Human SRE verification is required to promote memory to VERIFIED."
            ),
        )

    return user
