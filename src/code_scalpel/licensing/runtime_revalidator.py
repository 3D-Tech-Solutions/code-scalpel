"""Runtime license revalidation for long-lived server processes.

[20251228_FEATURE] Periodic re-validation loop for MCP server.

This is intentionally offline-first:
- No network calls
- Uses the existing JWTLicenseValidator (file-based token discovery)

[20251228_FEATURE] If a remote verifier is configured, this thread performs a
best-effort remote refresh on the revalidation interval (24h + jitter).

The MCP server already snapshots tier per-tool invocation. This loop primarily
supports operational visibility and ensures license status is re-checked even
if the server is idle.
"""

from __future__ import annotations

import logging
import os
import random
import threading
import time
from dataclasses import dataclass

from code_scalpel.licensing.jwt_validator import JWTLicenseValidator

logger = logging.getLogger(__name__)

DISABLE_REVALIDATION_ENV_VAR = "CODE_SCALPEL_DISABLE_LICENSE_REVALIDATION"


@dataclass
class RevalidationState:
    last_checked_at: float | None = None
    last_tier: str | None = None
    last_is_valid: bool | None = None
    last_error: str | None = None


_STATE = RevalidationState()


def get_revalidation_state() -> RevalidationState:
    return _STATE


def start_license_revalidation_thread(interval_seconds: int = 24 * 60 * 60) -> None:
    """Start a daemon thread that periodically re-validates the current license."""

    if os.getenv(DISABLE_REVALIDATION_ENV_VAR, "0").strip() == "1":
        return

    def _loop() -> None:
        validator = JWTLicenseValidator()
        while True:
            try:
                # [20251228_FEATURE] If a remote verifier is configured, force-refresh
                # the persisted cache on the revalidation interval.
                from code_scalpel.licensing.remote_verifier import (
                    refresh_cache,
                    remote_verifier_configured,
                )

                if remote_verifier_configured():
                    token = validator.load_license_token()
                    if token:
                        ent = refresh_cache(token)
                        _STATE.last_checked_at = time.time()
                        _STATE.last_tier = (ent.tier or "community").strip().lower()
                        _STATE.last_is_valid = bool(ent.valid)
                        _STATE.last_error = ent.error
                    else:
                        data = validator.validate()
                        _STATE.last_checked_at = time.time()
                        _STATE.last_tier = (data.tier or "community").strip().lower()
                        _STATE.last_is_valid = bool(data.is_valid)
                        _STATE.last_error = data.error_message
                else:
                    data = validator.validate()
                    _STATE.last_checked_at = time.time()
                    _STATE.last_tier = (data.tier or "community").strip().lower()
                    _STATE.last_is_valid = bool(data.is_valid)
                    _STATE.last_error = data.error_message
            except Exception as exc:
                _STATE.last_checked_at = time.time()
                _STATE.last_tier = None
                _STATE.last_is_valid = False
                _STATE.last_error = str(exc)
                logger.warning("License revalidation failed: %s", exc)

            jitter = random.randint(0, 15 * 60)
            time.sleep(max(10, int(interval_seconds) + jitter))

    t = threading.Thread(target=_loop, name="code-scalpel-license-revalidate", daemon=True)
    t.start()
