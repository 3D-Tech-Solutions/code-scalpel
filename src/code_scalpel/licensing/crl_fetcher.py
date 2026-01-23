"""CRL fetching and caching utilities for license revocation.

[20251228_FEATURE] Startup + background CRL refresh with offline cache.

This module is intentionally lightweight:
- Uses stdlib HTTP (urllib.request)
- Caches CRL JWT to disk with sidecar metadata
- Supports using stale/expired CRL for a bounded offline window

The validator still verifies signatures and iss/aud.
"""

from __future__ import annotations

import json
import os
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

DEFAULT_CRL_URL = "http://codescalpel.dev/.well-known/license-crl.jwt"

CRL_URL_ENV_VAR = "CODE_SCALPEL_LICENSE_CRL_URL"
CRL_ENABLE_FETCH_ENV_VAR = "CODE_SCALPEL_ENABLE_CRL_FETCH"
CRL_MAX_CACHE_AGE_DAYS_ENV_VAR = "CODE_SCALPEL_LICENSE_CRL_MAX_AGE_DAYS"

CRL_PATH_ENV_VAR = "CODE_SCALPEL_LICENSE_CRL_PATH"


@dataclass(frozen=True)
class CRLCachePaths:
    token_path: Path
    meta_path: Path


def _xdg_config_home() -> Path:
    base = os.getenv("XDG_CONFIG_HOME")
    if base:
        return Path(base).expanduser()
    return Path.home() / ".config"


def default_cache_paths() -> CRLCachePaths:
    cache_dir = _xdg_config_home() / "code-scalpel"
    token_path = cache_dir / "license_crl.jwt"
    meta_path = cache_dir / "license_crl.jwt.meta.json"
    return CRLCachePaths(token_path=token_path, meta_path=meta_path)


def _now_epoch() -> float:
    return time.time()


def _max_cache_age_seconds() -> int:
    raw = os.getenv(CRL_MAX_CACHE_AGE_DAYS_ENV_VAR, "7").strip()
    try:
        days = int(raw)
    except ValueError:
        days = 7
    if days < 0:
        days = 0
    return days * 24 * 60 * 60


def fetch_crl_token(url: str, timeout_seconds: float = 10.0) -> str:
    import urllib.parse

    parsed = urllib.parse.urlparse(url)
    # [20260102_BUGFIX] Restrict CRL fetch to HTTP(S) to avoid file:// access.
    if parsed.scheme not in {"http", "https"}:
        raise ValueError(f"Unsupported CRL URL scheme: {parsed.scheme}")

    req = urllib.request.Request(  # type: ignore
        url,
        headers={"User-Agent": "code-scalpel/CRLFetcher"},
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:  # nosec B310  # type: ignore
        body = resp.read().decode("utf-8", errors="replace")
    token = body.strip()
    if not token:
        raise ValueError("Empty CRL response")
    return token


def write_cache(token: str, paths: CRLCachePaths | None = None) -> CRLCachePaths:
    paths = paths or default_cache_paths()
    paths.token_path.parent.mkdir(parents=True, exist_ok=True)
    paths.token_path.write_text(token + "\n", encoding="utf-8")
    paths.meta_path.write_text(
        json.dumps({"fetched_at": _now_epoch()}, separators=(",", ":")),
        encoding="utf-8",
    )
    return paths


def load_cache_if_fresh(
    paths: CRLCachePaths | None = None,
) -> CRLCachePaths | None:
    paths = paths or default_cache_paths()
    if not (paths.token_path.exists() and paths.meta_path.exists()):
        return None

    try:
        meta = json.loads(paths.meta_path.read_text(encoding="utf-8"))
        fetched_at = float(meta.get("fetched_at", 0))
    except Exception:
        return None

    age_s = max(0.0, _now_epoch() - fetched_at)
    if age_s <= _max_cache_age_seconds():
        return paths

    # Cache exists but too old for offline tolerance.
    return None


def ensure_crl_available() -> CRLCachePaths | None:
    """Ensure a CRL token is available via CODE_SCALPEL_LICENSE_CRL_PATH.

    Behavior:
    - If CRL path already configured, do nothing.
    - If CRL fetch is not enabled, do nothing.
    - If enabled: try fetch, cache, set env var.
    - If fetch fails: use cached token if within max age.

    Returns:
        Cache paths in use, or None if no CRL is configured/available.
    """

    if os.getenv(CRL_PATH_ENV_VAR):
        return None

    enabled = os.getenv(CRL_ENABLE_FETCH_ENV_VAR, "0").strip() == "1"
    if not enabled:
        return None

    url = os.getenv(CRL_URL_ENV_VAR, DEFAULT_CRL_URL).strip() or DEFAULT_CRL_URL
    cache_paths = default_cache_paths()

    try:
        token = fetch_crl_token(url)
        write_cache(token, cache_paths)
        os.environ[CRL_PATH_ENV_VAR] = str(cache_paths.token_path)
        return cache_paths
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError):
        cached = load_cache_if_fresh(cache_paths)
        if cached:
            os.environ[CRL_PATH_ENV_VAR] = str(cached.token_path)
            return cached
        return None


def start_crl_refresh_thread(interval_seconds: int = 3600) -> None:
    """Start a daemon thread to periodically refresh the CRL cache.

    [20251228_FEATURE] Used by the MCP server so revocations apply mid-session.
    """

    enabled = os.getenv(CRL_ENABLE_FETCH_ENV_VAR, "0").strip() == "1"
    if not enabled:
        return

    def _loop() -> None:
        while True:
            try:
                ensure_crl_available()
            except Exception:
                # Never crash the server due to CRL refresh.
                pass
            time.sleep(max(10, int(interval_seconds)))

    t = threading.Thread(target=_loop, name="code-scalpel-crl-refresh", daemon=True)
    t.start()
