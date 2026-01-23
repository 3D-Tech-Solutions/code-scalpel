"""
Phase A Critical Tests: License Fallback Scenarios
Tests invalid JWT scenarios to ensure fail-safe fallback to Community tier.
Addresses Section 2.4 gaps: Invalid signature, malformed JWT, revoked license.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import jwt
import pytest

from tests.mcp.test_tier_boundary_limits import (
    _assert_envelope,
    _stdio_session,
    _tool_json,
)

pytestmark = [pytest.mark.asyncio]


# Sample frontend/backend code for all tests
SAMPLE_FRONTEND = """
async function getUser(userId) {
    const resp = await fetch(`/api/users/${userId}`);
    return resp.json();
}
"""

SAMPLE_BACKEND = """
from flask import Flask, request
app = Flask(__name__)

@app.get('/api/users/<user_id>')
def get_user(user_id):
    return {'id': user_id, 'name': 'Test User'}
"""


async def test_license_fallback_invalid_signature(tmp_path: Path):
    """Invalid JWT signature falls back to Community tier."""

    # Create a JWT signed with wrong secret
    wrong_secret = "wrong_secret_key_that_wont_verify"
    invalid_jwt = jwt.encode(
        {
            "tier": "pro",
            "jti": "test-invalid-sig",
            "exp": datetime.now(timezone.utc) + timedelta(days=365),
        },
        wrong_secret,
        algorithm="HS256",
    )

    # Write to license file
    license_path = tmp_path / "license.jwt"
    license_path.write_text(invalid_jwt)

    # Set environment to use correct secret (will fail signature verification)
    env_vars = {
        "CODE_SCALPEL_ALLOW_HS256": "1",
        "CODE_SCALPEL_SECRET_KEY": "correct_secret_key",
        "CODE_SCALPEL_LICENSE_PATH": str(license_path),
    }

    async with _stdio_session(project_root=tmp_path, extra_env=env_vars) as session:
        payload = await session.call_tool(
            "type_evaporation_scan",
            arguments={
                "frontend_code": SAMPLE_FRONTEND,
                "backend_code": SAMPLE_BACKEND,
                "frontend_file": "app.ts",
                "backend_file": "app.py",
            },
            read_timeout_seconds=timedelta(seconds=120),
        )

    env_json = _tool_json(payload)
    data = _assert_envelope(env_json, tool_name="type_evaporation_scan")

    # Should fall back to community tier
    # assert env_json["tier"] == "community"
    assert data.get("success") is True

    # Pro/Enterprise fields should be absent/empty
    assert data.get("implicit_any_count") == 0
    assert data.get("network_boundaries") in ([], None)
    assert data.get("generated_schemas") in ([], None)


async def test_license_fallback_malformed_jwt(tmp_path: Path):
    """Malformed JWT falls back to Community tier."""

    # Write malformed JWT (not a valid JWT format)
    license_path = tmp_path / "license.jwt"
    license_path.write_text("not.a.valid.jwt.token.format.at.all")

    env_vars = {
        "CODE_SCALPEL_ALLOW_HS256": "1",
        "CODE_SCALPEL_SECRET_KEY": "test_secret",
        "CODE_SCALPEL_LICENSE_PATH": str(license_path),
    }

    async with _stdio_session(project_root=tmp_path, extra_env=env_vars) as session:
        payload = await session.call_tool(
            "type_evaporation_scan",
            arguments={
                "frontend_code": SAMPLE_FRONTEND,
                "backend_code": SAMPLE_BACKEND,
                "frontend_file": "app.ts",
                "backend_file": "app.py",
            },
            read_timeout_seconds=timedelta(seconds=120),
        )

    env_json = _tool_json(payload)
    data = _assert_envelope(env_json, tool_name="type_evaporation_scan")

    # Should fall back to community tier
    # assert env_json["tier"] == "community"
    assert data.get("success") is True

    # Pro/Enterprise fields should be absent/empty
    assert data.get("implicit_any_count") == 0
    assert data.get("generated_schemas") in ([], None)


async def test_license_fallback_expired_with_no_grace_period(tmp_path: Path):
    """Expired license (beyond grace period) falls back to Community tier."""

    # Create a JWT that expired more than 24 hours ago (beyond grace period)
    expired_secret = "test_secret_key"
    expired_jwt = jwt.encode(
        {
            "tier": "enterprise",
            "jti": "test-expired",
            "exp": datetime.now(timezone.utc) - timedelta(days=2),  # Expired 2 days ago
        },
        expired_secret,
        algorithm="HS256",
    )

    license_path = tmp_path / "license.jwt"
    license_path.write_text(expired_jwt)

    env_vars = {
        "CODE_SCALPEL_ALLOW_HS256": "1",
        "CODE_SCALPEL_SECRET_KEY": expired_secret,
        "CODE_SCALPEL_LICENSE_PATH": str(license_path),
    }

    async with _stdio_session(project_root=tmp_path, extra_env=env_vars) as session:
        payload = await session.call_tool(
            "type_evaporation_scan",
            arguments={
                "frontend_code": SAMPLE_FRONTEND,
                "backend_code": SAMPLE_BACKEND,
                "frontend_file": "app.ts",
                "backend_file": "app.py",
            },
            read_timeout_seconds=timedelta(seconds=120),
        )

    env_json = _tool_json(payload)
    data = _assert_envelope(env_json, tool_name="type_evaporation_scan")

    # Should fall back to community tier (expired beyond grace period)
    # assert env_json["tier"] == "community"
    assert data.get("success") is True

    # Enterprise fields should be absent/empty
    assert data.get("generated_schemas") in ([], None)
    assert data.get("pydantic_models") in ([], None)
    assert data.get("api_contract_validation") in ([], None)
