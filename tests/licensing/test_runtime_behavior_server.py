"""Runtime behavior tests (server-tier semantics).

[20251228_TEST] Proves mid-session downgrade + in-flight snapshot behavior.
"""

from __future__ import annotations

import asyncio
import time

import pytest
from freezegun import freeze_time


def test_revocation_mid_session_downgrades_to_community(
    monkeypatch,
    tmp_path,
    write_hs256_license_jwt,
    write_hs256_crl_jwt,
    set_hs256_license_env,
):
    jti = "license-jti-123"

    license_path = write_hs256_license_jwt(duration_days=7, jti=jti)
    set_hs256_license_env(license_path=str(license_path))

    from code_scalpel.mcp import server

    assert server._get_current_tier() == "pro"

    crl_path = write_hs256_crl_jwt(revoked_jtis=[jti])
    monkeypatch.setenv("CODE_SCALPEL_LICENSE_CRL_PATH", str(crl_path))

    assert server._get_current_tier() == "community"


@freeze_time("2025-01-01 00:00:00")
def test_expiration_mid_session_24h_grace_then_downgrade(
    monkeypatch,
    tmp_path,
    write_hs256_license_jwt,
    set_hs256_license_env,
):
    jti = "license-jti-456"

    license_path = write_hs256_license_jwt(duration_days=-1, jti=jti)
    set_hs256_license_env(license_path=str(license_path))

    from code_scalpel.mcp import server

    # Simulate that we had a valid Pro license recently (server session context)
    server._LAST_VALID_LICENSE_TIER = "pro"
    server._LAST_VALID_LICENSE_AT = time.time() - 60

    assert server._get_current_tier() == "pro"

    # Grace window expired
    server._LAST_VALID_LICENSE_AT = time.time() - (24 * 3600 + 5)
    assert server._get_current_tier() == "community"


@pytest.mark.asyncio
async def test_in_flight_operation_keeps_tier_snapshot(
    monkeypatch,
    tmp_path,
    write_hs256_license_jwt,
    write_hs256_crl_jwt,
    set_hs256_license_env,
):
    """Verify in-flight operations preserve their tier snapshot even after revocation.

    [20250112_REFACTOR] Updated test to check data.tier_applied which is the
    tier snapshot captured at operation start. Envelope metadata fields are
    filtered by default for token efficiency - tier can be verified in data.
    """
    jti = "license-jti-789"

    license_path = write_hs256_license_jwt(duration_days=7, jti=jti)
    set_hs256_license_env(license_path=str(license_path))

    from code_scalpel.mcp import server
    from code_scalpel.mcp.helpers import policy_helpers

    tool = server.mcp._tool_manager.get_tool("code_policy_check")

    # Make the sync worker slow so we can flip env mid-run.
    # [20260116_BUGFIX] _code_policy_check_sync was refactored to helpers/policy_helpers.py
    original = policy_helpers._code_policy_check_sync

    def _slow_sync(*args, **kwargs):
        time.sleep(0.2)
        return original(*args, **kwargs)

    monkeypatch.setattr(policy_helpers, "_code_policy_check_sync", _slow_sync)

    task = asyncio.create_task(
        tool.run(
            {
                "paths": [str(tmp_path)],
                "rules": None,
                "compliance_standards": None,
                "generate_report": False,
            },
            context=None,
            convert_result=False,
        )
    )

    # Let the task start and snapshot tier.
    await asyncio.sleep(0.01)

    # Revoke mid-flight.
    crl_path = write_hs256_crl_jwt(revoked_jtis=[jti])
    monkeypatch.setenv("CODE_SCALPEL_LICENSE_CRL_PATH", str(crl_path))

    result = await task
    # [20250112_FIX] Check tier in data payload. Result is now a CodePolicyCheckResult dataclass.
    # The tier_applied field captures the snapshot at operation start.
    assert hasattr(result, "tier_applied"), f"Expected dataclass with tier_applied, got {type(result)}"
    assert result.tier_applied == "pro", f"Expected tier_applied=pro, got {result.tier_applied}"
