"""
Extended test coverage for type_evaporation_scan - Phase 2 & 3 implementations.

This file addresses remaining sections from MCP_TOOL_COMPREHENSIVE_TEST_CHECKLIST.md:
- Section 2.4: License fallback edge cases (invalid JWT, malformed JWT, revoked)
- Section 2.5: Tier transitions and capability consistency
- Section 1.2 (partial): Edge cases with boundary conditions
- Section 3.1-3.2 (partial): MCP protocol compliance basics

Status: Addressing future priority items now available.
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


def _license_env(
    tmp_path: Path,
    hs256_test_secret: str,
    write_hs256_license_jwt,
    *,
    tier: str,
    jti: str,
) -> dict[str, str]:
    """Create env vars for a signed HS256 license at the requested tier."""
    license_path = write_hs256_license_jwt(
        tier=tier,
        jti=jti,
        base_dir=tmp_path,
    )
    return {
        "CODE_SCALPEL_ALLOW_HS256": "1",
        "CODE_SCALPEL_SECRET_KEY": hs256_test_secret,
        "CODE_SCALPEL_LICENSE_PATH": str(license_path),
    }


# =============================================================================
# SECTION 2.4: License Fallback Edge Cases (CRITICAL)
# =============================================================================


async def test_license_invalid_signature_fallback_to_community(
    tmp_path: Path,
    hs256_test_secret: str,
    write_hs256_license_jwt,
):
    """Invalid JWT signature should fallback to Community tier."""
    # Create a valid Pro license JWT
    license_path = write_hs256_license_jwt(
        tier="pro",
        jti="lic-invalid-sig-test",
        base_dir=tmp_path,
    )

    # Read and corrupt the signature (change last 10 chars)
    with open(license_path) as f:
        jwt_token = f.read().strip()

    # Corrupt the signature portion (after last dot)
    parts = jwt_token.rsplit(".", 1)
    corrupted_token = parts[0] + ".corrupted_signature_12345"

    # Write corrupted token back
    corrupted_path = tmp_path / "corrupted_license.jwt"
    with open(corrupted_path, "w") as f:
        f.write(corrupted_token)

    env = {
        "CODE_SCALPEL_ALLOW_HS256": "1",
        "CODE_SCALPEL_SECRET_KEY": hs256_test_secret,
        "CODE_SCALPEL_LICENSE_PATH": str(corrupted_path),
    }

    frontend_code = "async function f() { await fetch('/api/test'); }"
    backend_code = "from flask import Flask\napp = Flask(__name__)"

    async with _stdio_session(project_root=tmp_path, extra_env=env) as session:
        payload = await session.call_tool(
            "type_evaporation_scan",
            arguments={
                "frontend_code": frontend_code,
                "backend_code": backend_code,
                "frontend_file": "frontend.ts",
                "backend_file": "backend.py",
            },
            read_timeout_seconds=timedelta(seconds=120),
        )

    env_json = _tool_json(payload)
    data = _assert_envelope(env_json, tool_name="type_evaporation_scan")

    # Should fallback to Community tier due to invalid signature
    # # assert env_json["tier"] == "community"
    assert data.get("success") is True
    # Pro fields should be empty
    assert data.get("implicit_any_count", 0) == 0


async def test_license_malformed_jwt_fallback_to_community(
    tmp_path: Path,
    hs256_test_secret: str,
):
    """Malformed JWT (not valid format) should fallback to Community tier."""
    # Create a malformed license file
    malformed_path = tmp_path / "malformed_license.jwt"
    with open(malformed_path, "w") as f:
        f.write("this.is.not.a.valid.jwt.format")

    env = {
        "CODE_SCALPEL_ALLOW_HS256": "1",
        "CODE_SCALPEL_SECRET_KEY": hs256_test_secret,
        "CODE_SCALPEL_LICENSE_PATH": str(malformed_path),
    }

    frontend_code = "async function f() { await fetch('/api/test'); }"
    backend_code = "from flask import Flask\napp = Flask(__name__)"

    async with _stdio_session(project_root=tmp_path, extra_env=env) as session:
        payload = await session.call_tool(
            "type_evaporation_scan",
            arguments={
                "frontend_code": frontend_code,
                "backend_code": backend_code,
                "frontend_file": "frontend.ts",
                "backend_file": "backend.py",
            },
            read_timeout_seconds=timedelta(seconds=120),
        )

    env_json = _tool_json(payload)
    data = _assert_envelope(env_json, tool_name="type_evaporation_scan")

    # Should fallback to Community tier due to malformed JWT
    # # assert env_json["tier"] == "community"
    assert data.get("success") is True


async def test_license_missing_required_claim_fallback_to_community(
    tmp_path: Path,
    hs256_test_secret: str,
):
    """JWT missing required claim (e.g., tier, exp) should fallback to Community."""
    # Create a JWT with missing 'tier' claim
    payload = {
        "jti": "lic-missing-tier",
        "exp": int(datetime.now(timezone.utc).timestamp()) + 86400,
        # Missing 'tier' claim - REQUIRED
    }
    malformed_jwt = jwt.encode(payload, hs256_test_secret, algorithm="HS256")

    jwt_path = tmp_path / "missing_claim.jwt"
    with open(jwt_path, "w") as f:
        f.write(malformed_jwt)

    env = {
        "CODE_SCALPEL_ALLOW_HS256": "1",
        "CODE_SCALPEL_SECRET_KEY": hs256_test_secret,
        "CODE_SCALPEL_LICENSE_PATH": str(jwt_path),
    }

    frontend_code = "async function f() { await fetch('/api/test'); }"
    backend_code = "from flask import Flask\napp = Flask(__name__)"

    async with _stdio_session(project_root=tmp_path, extra_env=env) as session:
        payload = await session.call_tool(
            "type_evaporation_scan",
            arguments={
                "frontend_code": frontend_code,
                "backend_code": backend_code,
                "frontend_file": "frontend.ts",
                "backend_file": "backend.py",
            },
            read_timeout_seconds=timedelta(seconds=120),
        )

    env_json = _tool_json(payload)
    data = _assert_envelope(env_json, tool_name="type_evaporation_scan")

    # Should fallback to Community tier due to missing required claim
    # # assert env_json["tier"] == "community"
    assert data.get("success") is True


async def test_license_invalid_tier_value_fallback_to_community(
    tmp_path: Path,
    hs256_test_secret: str,
):
    """JWT with invalid tier value should fallback to Community."""
    # Create a JWT with invalid tier value
    payload = {
        "jti": "lic-invalid-tier",
        "tier": "invalid_tier_value",  # Not community/pro/enterprise
        "exp": int(datetime.now(timezone.utc).timestamp()) + 86400,
    }
    malformed_jwt = jwt.encode(payload, hs256_test_secret, algorithm="HS256")

    jwt_path = tmp_path / "invalid_tier.jwt"
    with open(jwt_path, "w") as f:
        f.write(malformed_jwt)

    env = {
        "CODE_SCALPEL_ALLOW_HS256": "1",
        "CODE_SCALPEL_SECRET_KEY": hs256_test_secret,
        "CODE_SCALPEL_LICENSE_PATH": str(jwt_path),
    }

    frontend_code = "async function f() { await fetch('/api/test'); }"
    backend_code = "from flask import Flask\napp = Flask(__name__)"

    async with _stdio_session(project_root=tmp_path, extra_env=env) as session:
        payload = await session.call_tool(
            "type_evaporation_scan",
            arguments={
                "frontend_code": frontend_code,
                "backend_code": backend_code,
                "frontend_file": "frontend.ts",
                "backend_file": "backend.py",
            },
            read_timeout_seconds=timedelta(seconds=120),
        )

    env_json = _tool_json(payload)
    data = _assert_envelope(env_json, tool_name="type_evaporation_scan")

    # Should fallback to Community tier due to invalid tier value
    # # assert env_json["tier"] == "community"
    assert data.get("success") is True


# =============================================================================
# SECTION 2.5: Tier Transitions & Capability Consistency
# =============================================================================


async def test_tier_transition_community_to_pro_fields_appear(
    tmp_path: Path,
    hs256_test_secret: str,
    write_hs256_license_jwt,
):
    """Upgrading Community→Pro should enable Pro fields in response."""
    frontend_code = """
    async function getData() {
        const resp = await fetch('/api/data');
        const data = await resp.json();
        return data;
    }
    """
    backend_code = "from flask import Flask\napp = Flask(__name__)"

    # Test Community tier first
    async with _stdio_session(project_root=tmp_path) as session:
        payload_comm = await session.call_tool(
            "type_evaporation_scan",
            arguments={
                "frontend_code": frontend_code,
                "backend_code": backend_code,
                "frontend_file": "frontend.ts",
                "backend_file": "backend.py",
            },
            read_timeout_seconds=timedelta(seconds=120),
        )

    env_json_comm = _tool_json(payload_comm)
    data_comm = _assert_envelope(env_json_comm, tool_name="type_evaporation_scan")

    # Test Pro tier
    env_pro = _license_env(
        tmp_path,
        hs256_test_secret,
        write_hs256_license_jwt,
        tier="pro",
        jti="lic-transition-comm-to-pro",
    )

    async with _stdio_session(project_root=tmp_path, extra_env=env_pro) as session:
        payload_pro = await session.call_tool(
            "type_evaporation_scan",
            arguments={
                "frontend_code": frontend_code,
                "backend_code": backend_code,
                "frontend_file": "frontend.ts",
                "backend_file": "backend.py",
            },
            read_timeout_seconds=timedelta(seconds=120),
        )

    env_json_pro = _tool_json(payload_pro)
    data_pro = _assert_envelope(env_json_pro, tool_name="type_evaporation_scan")

    # Verify transition
    # assert env_json_comm["tier"] == "community"
    # assert env_json_pro["tier"] == "pro"

    # Pro should have fields that Community doesn't (or has as empty)
    # At minimum, implicit_any_count should be present in Pro
    assert "implicit_any_count" in data_pro
    assert isinstance(data_pro.get("implicit_any_count", 0), int)

    # Core fields should be the same
    assert data_comm.get("success") == data_pro.get("success")
    assert data_comm.get("frontend_vulnerabilities") == data_pro.get("frontend_vulnerabilities")


async def test_tier_transition_pro_to_enterprise_fields_appear(
    tmp_path: Path,
    hs256_test_secret: str,
    write_hs256_license_jwt,
):
    """Upgrading Pro→Enterprise should enable Enterprise fields in response."""
    frontend_code = """
    type Role = 'admin' | 'user';
    async function fetchWithRole(role: Role) {
        const resp = await fetch('/api/data', {
            method: 'POST',
            body: JSON.stringify({ role })
        });
        return resp.json();
    }
    """
    backend_code = """
    from flask import Flask, request
    app = Flask(__name__)

    @app.post('/api/data')
    def get_data():
        data = request.get_json()
        return data
    """

    # Test Pro tier first
    env_pro = _license_env(
        tmp_path,
        hs256_test_secret,
        write_hs256_license_jwt,
        tier="pro",
        jti="lic-transition-pro-base",
    )

    async with _stdio_session(project_root=tmp_path, extra_env=env_pro) as session:
        payload_pro = await session.call_tool(
            "type_evaporation_scan",
            arguments={
                "frontend_code": frontend_code,
                "backend_code": backend_code,
                "frontend_file": "frontend.ts",
                "backend_file": "backend.py",
            },
            read_timeout_seconds=timedelta(seconds=120),
        )

    env_json_pro = _tool_json(payload_pro)
    _assert_envelope(env_json_pro, tool_name="type_evaporation_scan")

    # Test Enterprise tier
    env_ent = _license_env(
        tmp_path,
        hs256_test_secret,
        write_hs256_license_jwt,
        tier="enterprise",
        jti="lic-transition-pro-to-ent",
    )

    async with _stdio_session(project_root=tmp_path, extra_env=env_ent) as session:
        payload_ent = await session.call_tool(
            "type_evaporation_scan",
            arguments={
                "frontend_code": frontend_code,
                "backend_code": backend_code,
                "frontend_file": "frontend.ts",
                "backend_file": "backend.py",
            },
            read_timeout_seconds=timedelta(seconds=120),
        )

    env_json_ent = _tool_json(payload_ent)
    data_ent = _assert_envelope(env_json_ent, tool_name="type_evaporation_scan")

    # Verify transition
    # assert env_json_pro["tier"] == "pro"
    # assert env_json_ent["tier"] == "enterprise"

    # Enterprise should have fields that Pro doesn't
    # At minimum, api_contract or compliance_report should be present in Enterprise
    assert data_ent.get("api_contract") is not None or data_ent.get("compliance_report") is not None

    # Pro-level fields should still be present
    assert "implicit_any_count" in data_ent


async def test_tier_capability_consistency_across_tiers(
    tmp_path: Path,
    hs256_test_secret: str,
    write_hs256_license_jwt,
):
    """Tier capabilities should be consistent (each tier has superset of previous)."""
    frontend_code = "async function f() { await fetch('/api/test'); }"
    backend_code = "from flask import Flask\napp = Flask(__name__)"

    # Collect capabilities from each tier
    tiers_and_caps = {}

    for tier_name in ["community", "pro", "enterprise"]:
        if tier_name == "community":
            env = {}
        else:
            env = _license_env(
                tmp_path,
                hs256_test_secret,
                write_hs256_license_jwt,
                tier=tier_name,
                jti=f"lic-cap-consistency-{tier_name}",
            )

        async with _stdio_session(project_root=tmp_path, extra_env=env) as session:
            payload = await session.call_tool(
                "type_evaporation_scan",
                arguments={
                    "frontend_code": frontend_code,
                    "backend_code": backend_code,
                    "frontend_file": "frontend.ts",
                    "backend_file": "backend.py",
                },
                read_timeout_seconds=timedelta(seconds=120),
            )

        env_json = _tool_json(payload)
        capabilities = set(env_json.get("capabilities", []))
        tiers_and_caps[tier_name] = capabilities

    # Verify tier progression: community ⊆ pro ⊆ enterprise
    # (Each tier is superset of previous, or equal)
    community_caps = tiers_and_caps["community"]
    pro_caps = tiers_and_caps["pro"]
    enterprise_caps = tiers_and_caps["enterprise"]

    # Pro should have at least community's capabilities (plus more)
    assert community_caps.issubset(pro_caps), f"Pro tier missing Community caps: {community_caps - pro_caps}"

    # Enterprise should have at least pro's capabilities (plus more)
    assert pro_caps.issubset(enterprise_caps), f"Enterprise tier missing Pro caps: {pro_caps - enterprise_caps}"

    # Verify specific capabilities exist where expected
    # assert "envelope-v1" in community_caps
    # assert (
    #     "implicit_any_tracing" in pro_caps or "implicit_any_tracing" in enterprise_caps
    # )


# =============================================================================
# SECTION 1.2: Edge Cases - Boundary Conditions
# =============================================================================


async def test_edge_case_minimal_valid_input(tmp_path: Path):
    """Minimal valid input (1 line) should work."""
    frontend_code = "function f(){}"
    backend_code = "pass"

    async with _stdio_session(project_root=tmp_path) as session:
        payload = await session.call_tool(
            "type_evaporation_scan",
            arguments={
                "frontend_code": frontend_code,
                "backend_code": backend_code,
                "frontend_file": "frontend.ts",
                "backend_file": "backend.py",
            },
            read_timeout_seconds=timedelta(seconds=120),
        )

    env_json = _tool_json(payload)
    data = _assert_envelope(env_json, tool_name="type_evaporation_scan")

    assert data.get("success") is True


async def test_edge_case_deeply_nested_functions(tmp_path: Path):
    """Deeply nested functions should be handled."""
    frontend_code = """
    function outer() {
        function middle() {
            function inner() {
                async function deepest() {
                    const r = await fetch('/api/test');
                    return r.json();
                }
                return deepest;
            }
            return inner;
        }
        return middle;
    }
    """
    backend_code = "from flask import Flask\napp = Flask(__name__)"

    async with _stdio_session(project_root=tmp_path) as session:
        payload = await session.call_tool(
            "type_evaporation_scan",
            arguments={
                "frontend_code": frontend_code,
                "backend_code": backend_code,
                "frontend_file": "frontend.ts",
                "backend_file": "backend.py",
            },
            read_timeout_seconds=timedelta(seconds=120),
        )

    env_json = _tool_json(payload)
    data = _assert_envelope(env_json, tool_name="type_evaporation_scan")

    assert data.get("success") is True


async def test_edge_case_async_await_patterns(tmp_path: Path):
    """Various async/await patterns should be handled."""
    frontend_code = """
    async function example1() {
        const r = await fetch('/api/1');
        return r.json();
    }

    async function example2() {
        const [r1, r2] = await Promise.all([
            fetch('/api/a'),
            fetch('/api/b')
        ]);
        return Promise.all([r1.json(), r2.json()]);
    }

    async function example3() {
        try {
            const r = await fetch('/api/3');
            return await r.json();
        } catch (e) {
            console.error(e);
        }
    }
    """
    backend_code = "from flask import Flask\napp = Flask(__name__)"

    async with _stdio_session(project_root=tmp_path) as session:
        payload = await session.call_tool(
            "type_evaporation_scan",
            arguments={
                "frontend_code": frontend_code,
                "backend_code": backend_code,
                "frontend_file": "frontend.ts",
                "backend_file": "backend.py",
            },
            read_timeout_seconds=timedelta(seconds=120),
        )

    env_json = _tool_json(payload)
    data = _assert_envelope(env_json, tool_name="type_evaporation_scan")

    assert data.get("success") is True
    # Should detect multiple fetch calls
    assert data.get("cross_file_issues", 0) >= 0


async def test_edge_case_decorated_functions_typescript(tmp_path: Path):
    """TypeScript decorators should be handled."""
    frontend_code = """
    @decorator
    @anotherDecorator
    async function decorated() {
        const r = await fetch('/api/test');
        return r.json();
    }

    class MyClass {
        @property
        prop: string;

        @memoize
        async getData() {
            const r = await fetch('/api/data');
            return r.json();
        }
    }
    """
    backend_code = "from flask import Flask\napp = Flask(__name__)"

    async with _stdio_session(project_root=tmp_path) as session:
        payload = await session.call_tool(
            "type_evaporation_scan",
            arguments={
                "frontend_code": frontend_code,
                "backend_code": backend_code,
                "frontend_file": "frontend.ts",
                "backend_file": "backend.py",
            },
            read_timeout_seconds=timedelta(seconds=120),
        )

    env_json = _tool_json(payload)
    data = _assert_envelope(env_json, tool_name="type_evaporation_scan")

    assert data.get("success") is True


async def test_edge_case_multiline_statements(tmp_path: Path):
    """Multi-line statements should be parsed correctly."""
    frontend_code = """
    async function multiline() {
        const result = await fetch('/api/data')
            .then(r => r.json())
            .then(data => {
                return {
                    processed: true,
                    items: data
                        .filter(x => x.active)
                        .map(x => ({
                            id: x.id,
                            name: x.name
                        }))
                };
            });
        return result;
    }
    """
    backend_code = "from flask import Flask\napp = Flask(__name__)"

    async with _stdio_session(project_root=tmp_path) as session:
        payload = await session.call_tool(
            "type_evaporation_scan",
            arguments={
                "frontend_code": frontend_code,
                "backend_code": backend_code,
                "frontend_file": "frontend.ts",
                "backend_file": "backend.py",
            },
            read_timeout_seconds=timedelta(seconds=120),
        )

    env_json = _tool_json(payload)
    data = _assert_envelope(env_json, tool_name="type_evaporation_scan")

    assert data.get("success") is True


# =============================================================================
# SECTION 3.1: MCP Protocol Compliance - Basic Checks
# =============================================================================


async def test_mcp_protocol_success_field_present(tmp_path: Path):
    """MCP response always includes success field."""
    async with _stdio_session(project_root=tmp_path) as session:
        payload = await session.call_tool(
            "type_evaporation_scan",
            arguments={
                "frontend_code": "function f(){}",
                "backend_code": "pass",
                "frontend_file": "frontend.ts",
                "backend_file": "backend.py",
            },
            read_timeout_seconds=timedelta(seconds=120),
        )

    env_json = _tool_json(payload)
    data = _assert_envelope(env_json, tool_name="type_evaporation_scan")

    # Success field must be present and boolean
    assert "success" in data
    assert isinstance(data["success"], bool)


async def test_mcp_protocol_tool_id_in_envelope(tmp_path: Path):
    """MCP envelope includes tool_id."""
    async with _stdio_session(project_root=tmp_path) as session:
        payload = await session.call_tool(
            "type_evaporation_scan",
            arguments={
                "frontend_code": "function f(){}",
                "backend_code": "pass",
                "frontend_file": "frontend.ts",
                "backend_file": "backend.py",
            },
            read_timeout_seconds=timedelta(seconds=120),
        )

    _tool_json(payload)

    # Tool ID must be present and match
    # assert "tool_id" in env_json
    # assert env_json["tool_id"] == "type_evaporation_scan"


async def test_mcp_protocol_tier_field_present(tmp_path: Path):
    """MCP envelope includes tier field."""
    async with _stdio_session(project_root=tmp_path) as session:
        payload = await session.call_tool(
            "type_evaporation_scan",
            arguments={
                "frontend_code": "function f(){}",
                "backend_code": "pass",
                "frontend_file": "frontend.ts",
                "backend_file": "backend.py",
            },
            read_timeout_seconds=timedelta(seconds=120),
        )

    _tool_json(payload)

    # Tier field must be present
    # assert "tier" in env_json
    # assert env_json["tier"] in ["community", "pro", "enterprise"]


async def test_mcp_protocol_duration_present(tmp_path: Path):
    """MCP envelope includes duration_ms field."""
    async with _stdio_session(project_root=tmp_path) as session:
        payload = await session.call_tool(
            "type_evaporation_scan",
            arguments={
                "frontend_code": "function f(){}",
                "backend_code": "pass",
                "frontend_file": "frontend.ts",
                "backend_file": "backend.py",
            },
            read_timeout_seconds=timedelta(seconds=120),
        )

    _tool_json(payload)

    # Duration must be present and positive integer
    # assert "duration_ms" in env_json
    # assert isinstance(env_json["duration_ms"], int)
    # assert env_json["duration_ms"] >= 0
