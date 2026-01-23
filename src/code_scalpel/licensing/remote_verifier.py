"""Remote-only JWT license verification with offline grace.

[20251228_FEATURE] Remote verifier integration for MCP servers.

Implements the policy:
- Refresh remote verification every 24h.
- If remote verification fails, allow an additional 24h offline grace (48h total)
  *only* when the current license token hash matches the last successfully
  verified token hash.

This module is intentionally signature-agnostic. The verifier server is the
only authority for JWT signature and claim validity.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


VERIFIER_BASE_URL_ENV_VAR = "CODE_SCALPEL_LICENSE_VERIFIER_URL"
VERIFIER_ENVIRONMENT_ENV_VAR = "CODE_SCALPEL_LICENSE_ENVIRONMENT"

LICENSE_CACHE_PATH_ENV_VAR = "CODE_SCALPEL_LICENSE_CACHE_PATH"

VERIFY_TIMEOUT_SECONDS_ENV_VAR = "CODE_SCALPEL_LICENSE_VERIFY_TIMEOUT_SECONDS"
VERIFY_RETRIES_ENV_VAR = "CODE_SCALPEL_LICENSE_VERIFY_RETRIES"

DEFAULT_VERIFY_TIMEOUT_SECONDS = 2.0
DEFAULT_VERIFY_RETRIES = 2

REFRESH_SECONDS = 24 * 60 * 60
OFFLINE_GRACE_SECONDS = 24 * 60 * 60

# [20251228_SECURITY] Allowlist of trusted verifier URLs to prevent arbitrary endpoint exploitation.
# Users cannot point to malicious verifiers that always return valid=true, tier=enterprise.
TRUSTED_VERIFIER_URLS = {
    "https://verifier.codescalpel.dev",  # Production verifier
    "http://scalpel-verifier:8000",  # Docker internal network
    "http://127.0.0.1:8003",  # Local development (host)
    "http://localhost:8003",  # Local development (localhost)
    "http://127.0.0.1:8000",  # Local development (default port)
    "http://localhost:8000",  # Local development (default port)
}


def _is_loopback_verifier_url(url: str) -> bool:
    """Return True if the verifier URL points at a local loopback interface.

    This is intentionally permissive on port to support test harnesses that bind
    to ephemeral ports.
    """

    try:
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in {"http", "https"}:
            return False
        host = (parsed.hostname or "").strip().lower()
        if host in {"localhost", "127.0.0.1", "::1"}:
            return True
        return False
    except Exception:
        return False


@dataclass(frozen=True)
class VerifiedEntitlements:
    valid: bool
    exp: int
    tier: str
    features: list[str]
    customer_id: str | None = None
    organization: str | None = None
    seats: int | None = None
    error: str | None = None


@dataclass
class LicenseCacheState:
    last_verified_at_epoch: float | None = None
    last_verified_at_utc: str | None = None
    license_hash: str | None = None
    valid: bool | None = None
    exp: int | None = None
    tier: str | None = None
    features: list[str] | None = None
    customer_id: str | None = None
    organization: str | None = None
    seats: int | None = None


_CACHE_LOCK = threading.Lock()
_IN_MEMORY_CACHE: LicenseCacheState | None = None


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _default_cache_path() -> Path:
    xdg = os.getenv("XDG_CONFIG_HOME")
    base = Path(xdg).expanduser() if xdg else Path("~/.config").expanduser()
    return base / "code-scalpel" / "license_cache.json"


def cache_path() -> Path:
    override = os.getenv(LICENSE_CACHE_PATH_ENV_VAR)
    if override:
        return Path(override).expanduser()
    return _default_cache_path()


def verifier_base_url() -> str | None:
    # NOTE: Remote verifier must be explicitly configured.
    # If unset/empty, the system should fall back to local RS256 validation.
    raw = os.getenv(VERIFIER_BASE_URL_ENV_VAR)
    if not raw:
        return None

    url = raw.rstrip("/")

    # [20251228_SECURITY] Validate against allowlist to prevent malicious verifier exploitation
    if url not in TRUSTED_VERIFIER_URLS and not _is_loopback_verifier_url(url):
        logger.error(
            "SECURITY: Untrusted verifier URL rejected: %s. " "Only trusted verifiers are allowed. " "Trusted URLs: %s",
            url,
            sorted(TRUSTED_VERIFIER_URLS),
        )
        raise ValueError(
            f"Untrusted verifier URL: {url}. " f"Only trusted verifiers are allowed: {sorted(TRUSTED_VERIFIER_URLS)}"
        )

    return url


def remote_verifier_configured() -> bool:
    return verifier_base_url() is not None


def verifier_environment() -> str | None:
    raw = os.getenv(VERIFIER_ENVIRONMENT_ENV_VAR)
    if raw is None:
        return None
    v = raw.strip()
    return v or None


def sha256_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _hash_hint(token_hash: str) -> str:
    """Return a short, non-sensitive identifier for logs/errors."""

    h = (token_hash or "").strip()
    if len(h) <= 12:
        return h
    return f"{h[:6]}...{h[-6:]}"


def _read_json_file(path: Path) -> dict[str, Any] | None:
    try:
        if not path.exists():
            return None
        content = path.read_text(encoding="utf-8").strip()
        if not content:
            return None
        parsed = json.loads(content)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        return None
    return None


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    serialized = json.dumps(payload, sort_keys=True)
    tmp.write_text(serialized, encoding="utf-8")
    # [20251228_BUGFIX] Some Docker bind mounts (notably `/mnt/*`-backed mounts)
    # can intermittently surface a just-written temp file as missing at rename
    # time (ENOENT). Retry briefly to avoid crashing the server at startup.
    for attempt in range(5):
        try:
            tmp.replace(path)
            return
        except FileNotFoundError:
            if attempt < 4:
                time.sleep(0.02 * (attempt + 1))
                continue

            # As a last resort, avoid crashing the server: write non-atomically.
            # This is a cache file; correctness of allow/deny is driven by the
            # verifier response and cached values, not by atomicity guarantees.
            path.write_text(serialized, encoding="utf-8")
            return


def load_cache_state() -> LicenseCacheState:
    global _IN_MEMORY_CACHE

    with _CACHE_LOCK:
        if _IN_MEMORY_CACHE is not None:
            return _IN_MEMORY_CACHE

        data = _read_json_file(cache_path())
        state = LicenseCacheState()
        if not data:
            _IN_MEMORY_CACHE = state
            return state

        state.last_verified_at_epoch = data.get("last_verified_at_epoch")
        state.last_verified_at_utc = data.get("last_verified_at")
        state.license_hash = data.get("license_hash")
        state.valid = data.get("valid")
        state.exp = data.get("exp")
        state.tier = data.get("tier")
        state.features = data.get("features")
        state.customer_id = data.get("customer_id")
        state.organization = data.get("organization")
        state.seats = data.get("seats")

        _IN_MEMORY_CACHE = state
        return state


def save_cache_state(entitlements: VerifiedEntitlements, token_hash: str) -> None:
    global _IN_MEMORY_CACHE

    now_epoch = time.time()
    payload: dict[str, Any] = {
        "last_verified_at": _utc_now_iso(),
        "last_verified_at_epoch": now_epoch,
        "license_hash": token_hash,
        "valid": bool(entitlements.valid),
        "exp": int(entitlements.exp),
        "tier": entitlements.tier,
        "features": list(entitlements.features),
        "customer_id": entitlements.customer_id,
        "organization": entitlements.organization,
        "seats": entitlements.seats,
    }

    _atomic_write_json(cache_path(), payload)

    with _CACHE_LOCK:
        _IN_MEMORY_CACHE = LicenseCacheState(
            last_verified_at_epoch=payload["last_verified_at_epoch"],
            last_verified_at_utc=payload["last_verified_at"],
            license_hash=payload["license_hash"],
            valid=payload["valid"],
            exp=payload["exp"],
            tier=payload["tier"],
            features=payload["features"],
            customer_id=payload.get("customer_id"),
            organization=payload.get("organization"),
            seats=payload.get("seats"),
        )


def _verify_timeout_seconds() -> float:
    raw = os.getenv(VERIFY_TIMEOUT_SECONDS_ENV_VAR)
    if not raw:
        return DEFAULT_VERIFY_TIMEOUT_SECONDS
    try:
        return max(0.1, float(raw))
    except Exception:
        return DEFAULT_VERIFY_TIMEOUT_SECONDS


def _verify_retries() -> int:
    raw = os.getenv(VERIFY_RETRIES_ENV_VAR)
    if not raw:
        return DEFAULT_VERIFY_RETRIES
    try:
        return max(0, int(raw))
    except Exception:
        return DEFAULT_VERIFY_RETRIES


def remote_verify(token: str, *, environment: str | None) -> VerifiedEntitlements:
    base = verifier_base_url()
    if not base:
        raise RuntimeError(f"Remote verifier URL not configured. Set {VERIFIER_BASE_URL_ENV_VAR}.")

    import urllib.parse

    parsed = urllib.parse.urlparse(base)
    # [20260102_BUGFIX] Enforce network-only verifier base URL.
    if parsed.scheme not in {"http", "https"}:
        raise RuntimeError(f"Unsupported verifier scheme: {parsed.scheme}")

    url = f"{base}/verify"
    parsed = urllib.parse.urlparse(url)
    # [20260102_BUGFIX] Restrict verifier endpoint to HTTP(S).
    if parsed.scheme not in {"http", "https"}:
        raise RuntimeError(f"Unsupported verifier URL scheme: {parsed.scheme}")

    # Contract tests expect the verifier request to include the full token under
    # `token`. The verifier is responsible for not logging sensitive data.
    payload = {"token": token.strip(), "environment": environment}
    body = json.dumps(payload).encode("utf-8")

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "code-scalpel-mcp/remote-verifier",
    }

    req = urllib.request.Request(url, data=body, headers=headers, method="POST")  # type: ignore

    token_hash_hint = _hash_hint(sha256_token(token.strip()))

    last_exc: Exception | None = None
    for attempt in range(_verify_retries() + 1):
        try:
            with urllib.request.urlopen(req, timeout=_verify_timeout_seconds()) as resp:  # nosec B310  # type: ignore
                raw = resp.read().decode("utf-8")
            parsed = json.loads(raw)
            if not isinstance(parsed, dict):
                raise RuntimeError("Verifier response is not an object")

            valid = bool(parsed.get("valid"))
            error = parsed.get("error")
            lic = parsed.get("license")
            if not isinstance(lic, dict):
                lic = {}

            exp = int(lic.get("exp") or 0)
            tier = str(lic.get("tier") or "community").strip().lower()
            features = lic.get("features") or []
            if not isinstance(features, list):
                features = []

            # [20251228_BUGFIX] Accept multiple verifier field conventions.
            # The in-repo verifier service returns `customer`/`org` (VerifiedLicense),
            # while the MCP contract tests use `customer_id`/`organization`.
            customer_id: str | None = None
            if isinstance(lic.get("customer_id"), str):
                customer_id = lic.get("customer_id")
            elif isinstance(lic.get("customer"), str):
                customer_id = lic.get("customer")

            organization: str | None = None
            if isinstance(lic.get("organization"), str):
                organization = lic.get("organization")
            elif isinstance(lic.get("org"), str):
                organization = lic.get("org")

            seats_val = lic.get("seats")
            seats: int | None = None
            if isinstance(seats_val, (str, int, float)):
                try:
                    seats = int(seats_val)
                except Exception:
                    seats = None

            return VerifiedEntitlements(
                valid=valid,
                exp=exp,
                tier=tier,
                features=[str(x) for x in features if isinstance(x, (str, int, float))],
                customer_id=customer_id,
                organization=organization,
                seats=seats,
                error=(str(error) if error is not None else None),
            )
        except (
            urllib.error.URLError,  # type: ignore
            TimeoutError,
            json.JSONDecodeError,
            RuntimeError,
        ) as exc:
            last_exc = exc
            # brief backoff
            if attempt < _verify_retries():
                time.sleep(0.05 * (attempt + 1))
                continue
            break

    # Never include the token or request body in exception strings.
    exc_name = type(last_exc).__name__ if last_exc is not None else "UnknownError"
    logger.warning(
        "Remote verify failed (hash=%s, error=%s)",
        token_hash_hint,
        exc_name,
    )
    raise RuntimeError(f"Remote verify failed (hash={token_hash_hint}, error={exc_name})")


@dataclass(frozen=True)
class AuthorizationDecision:
    allowed: bool
    entitlements: VerifiedEntitlements | None
    reason: str


def authorize_token(token: str) -> AuthorizationDecision:
    """Authorize based on the on-demand policy described in the contract."""

    token = token.strip()
    current_hash = sha256_token(token)
    now = time.time()

    state = load_cache_state()

    # No verified cache yet => must try remote verify.
    if not state.last_verified_at_epoch or not state.exp or not state.license_hash:
        ent = remote_verify(token, environment=verifier_environment())
        save_cache_state(ent, current_hash)
        if now >= ent.exp:
            return AuthorizationDecision(False, ent, "license_expired")
        return AuthorizationDecision(bool(ent.valid), ent, "remote_verified")

    # If now >= exp => deny always.
    if now >= float(state.exp):
        ent = VerifiedEntitlements(
            valid=False,
            exp=int(state.exp),
            tier=str(state.tier or "community"),
            features=list(state.features or []),
            customer_id=state.customer_id,
            organization=state.organization,
            seats=state.seats,
            error="License expired",
        )
        return AuthorizationDecision(False, ent, "license_expired")

    age = now - float(state.last_verified_at_epoch)

    # Fresh cache window: rely on cached validity only.
    if age <= REFRESH_SECONDS:
        ent = VerifiedEntitlements(
            valid=bool(state.valid),
            exp=int(state.exp),
            tier=str(state.tier or "community"),
            features=list(state.features or []),
            customer_id=state.customer_id,
            organization=state.organization,
            seats=state.seats,
            error=None,
        )
        return AuthorizationDecision(bool(state.valid), ent, "cache_fresh")

    # Stale => try remote verify.
    try:
        ent = remote_verify(token, environment=verifier_environment())
        save_cache_state(ent, current_hash)
        if now >= ent.exp:
            return AuthorizationDecision(False, ent, "license_expired")
        return AuthorizationDecision(bool(ent.valid), ent, "remote_verified")
    except Exception:
        # Offline grace: 24h beyond refresh window.
        if (
            age <= (REFRESH_SECONDS + OFFLINE_GRACE_SECONDS)
            and state.license_hash == current_hash
            and bool(state.valid) is True
        ):
            ent = VerifiedEntitlements(
                valid=True,
                exp=int(state.exp),
                tier=str(state.tier or "community"),
                features=list(state.features or []),
                customer_id=state.customer_id,
                organization=state.organization,
                seats=state.seats,
                error=None,
            )
            return AuthorizationDecision(True, ent, "offline_grace")

        ent = VerifiedEntitlements(
            valid=False,
            exp=int(state.exp),
            tier=str(state.tier or "community"),
            features=list(state.features or []),
            customer_id=state.customer_id,
            organization=state.organization,
            seats=state.seats,
            error="Remote verification unavailable and grace expired",
        )
        return AuthorizationDecision(False, ent, "offline_denied")


def refresh_cache(token: str) -> VerifiedEntitlements:
    """Force a remote verification and update the persisted cache.

    This bypasses the refresh/grace decision logic and is intended for the
    background refresh loop.
    """

    token = token.strip()
    token_hash = sha256_token(token)
    ent = remote_verify(token, environment=verifier_environment())
    save_cache_state(ent, token_hash)
    return ent
