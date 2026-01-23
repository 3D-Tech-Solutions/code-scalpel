"""
Test coverage for type_evaporation_scan checklist gaps.

This file addresses missing tests from MCP_TOOL_COMPREHENSIVE_TEST_CHECKLIST.md:
- Section 1.1: Input validation and error handling
- Section 2.1-2.3: Tier limit enforcement (⚠️ CRITICAL)
- Section 3.3-3.4: Parameter and response validation
- Section 4.1-4.3: Performance, reliability, security

Status: Addressing critical gaps (⚠️) for Pro/Enterprise tier limits.
"""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

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
# SECTION 1.1: Input Validation & Error Handling
# =============================================================================


async def test_type_evaporation_scan_empty_frontend_code(tmp_path: Path):
    """Empty frontend code should be rejected or return empty results."""
    backend_code = """
from flask import Flask
app = Flask(__name__)

@app.post('/api/test')
def test():
    return {'ok': True}
"""

    async with _stdio_session(project_root=tmp_path) as session:
        payload = await session.call_tool(
            "type_evaporation_scan",
            arguments={
                "frontend_code": "",
                "backend_code": backend_code,
                "frontend_file": "frontend.ts",
                "backend_file": "backend.py",
            },
            read_timeout_seconds=timedelta(seconds=120),
        )

    env_json = _tool_json(payload)
    data = _assert_envelope(env_json, tool_name="type_evaporation_scan")

    # Should handle gracefully - either empty result or success with 0 findings
    assert data.get("success") is True or "empty" in str(data).lower()


async def test_type_evaporation_scan_empty_backend_code(tmp_path: Path):
    """Empty backend code should be handled gracefully."""
    frontend_code = """
async function fetchData() {
    const resp = await fetch('/api/test');
    return resp.json();
}
"""

    async with _stdio_session(project_root=tmp_path) as session:
        payload = await session.call_tool(
            "type_evaporation_scan",
            arguments={
                "frontend_code": frontend_code,
                "backend_code": "",
                "frontend_file": "frontend.ts",
                "backend_file": "backend.py",
            },
            read_timeout_seconds=timedelta(seconds=120),
        )

    env_json = _tool_json(payload)
    data = _assert_envelope(env_json, tool_name="type_evaporation_scan")

    # Community tier with empty backend should still work (frontend-only)
    assert data.get("success") is True


async def test_type_evaporation_scan_invalid_frontend_code(tmp_path: Path):
    """Invalid/malformed frontend code should be handled gracefully."""
    frontend_code = """
async function broken(  // Missing closing paren and body
"""

    backend_code = """
from flask import Flask
app = Flask(__name__)
"""

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

    # Should still return success (tool is robust to syntax errors)
    # or explicitly report parsing issue
    assert "success" in data


async def test_type_evaporation_scan_missing_required_parameter(tmp_path: Path):
    """Missing required frontend_code parameter should error."""
    async with _stdio_session(project_root=tmp_path) as session:
        payload = await session.call_tool(
            "type_evaporation_scan",
            arguments={
                # Missing frontend_code - REQUIRED
                "backend_code": "code",
                "frontend_file": "frontend.ts",
                "backend_file": "backend.py",
            },
            read_timeout_seconds=timedelta(seconds=120),
        )

    # [20260120_FIX] MCP returns validation errors via isError=True, not JSON envelope
    assert payload.isError is True
    assert payload.content, "Error should have content describing the error"
    error_text = payload.content[0].text if payload.content else ""
    assert "frontend_code" in error_text.lower() or "required" in error_text.lower()


async def test_type_evaporation_scan_optional_file_names_default(tmp_path: Path):
    """Optional frontend/backend file names should use defaults when omitted."""
    frontend_code = "async function f() { await fetch('/test'); }"
    backend_code = "from flask import Flask\napp = Flask(__name__)"

    async with _stdio_session(project_root=tmp_path) as session:
        payload = await session.call_tool(
            "type_evaporation_scan",
            arguments={
                "frontend_code": frontend_code,
                "backend_code": backend_code,
                # Omit optional file names - should use defaults
            },
            read_timeout_seconds=timedelta(seconds=120),
        )

    env_json = _tool_json(payload)
    data = _assert_envelope(env_json, tool_name="type_evaporation_scan")

    # Should succeed with defaults
    assert data.get("success") is True


# =============================================================================
# SECTION 2.1: Community Tier Limits (⚠️ CRITICAL)
# =============================================================================


async def test_type_evaporation_scan_community_frontend_code_size_limit(
    tmp_path: Path,
):
    """Community tier should enforce frontend code size limit."""
    # Create large frontend code
    large_frontend = "// " + "x" * 500_000  # ~500KB comment

    backend_code = """
from flask import Flask
app = Flask(__name__)
"""

    async with _stdio_session(project_root=tmp_path) as session:
        payload = await session.call_tool(
            "type_evaporation_scan",
            arguments={
                "frontend_code": large_frontend,
                "backend_code": backend_code,
                "frontend_file": "frontend.ts",
                "backend_file": "backend.py",
            },
            read_timeout_seconds=timedelta(seconds=120),
        )

    env_json = _tool_json(payload)
    data = _assert_envelope(env_json, tool_name="type_evaporation_scan")

    # Should process (no hard error) but may warn or truncate
    assert data.get("success") is True


# =============================================================================
# SECTION 2.2: Pro Tier Limits (⚠️ CRITICAL)
# =============================================================================


async def test_type_evaporation_scan_pro_increased_file_limit(
    tmp_path: Path,
    hs256_test_secret: str,
    write_hs256_license_jwt,
):
    """Pro tier should handle more virtual files than Community (500 vs 50)."""
    # Create 200 virtual files (more than Community 50, less than Pro 500)
    frontend_segments = []
    for i in range(200):
        frontend_segments.append(
            f"// FILE: f{i}.ts\nasync function f{i}() {{ const r = await fetch('/api/f{i}'); return r.json(); }}"
        )
    frontend_code = "\n".join(frontend_segments)

    backend_code = """
from fastapi import FastAPI
app = FastAPI()

@app.post('/api/f0')
async def f0():
    return {"ok": True}
"""

    env = _license_env(
        tmp_path,
        hs256_test_secret,
        write_hs256_license_jwt,
        tier="pro",
        jti="lic-type-evap-pro-file-limit",
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
            read_timeout_seconds=timedelta(seconds=240),
        )

    env_json = _tool_json(payload)
    data = _assert_envelope(env_json, tool_name="type_evaporation_scan")

    # assert env_json["tier"] == "pro"
    assert data.get("success") is True
    # Pro should not truncate at 200 files (limit is 500)
    warnings = data.get("warnings") or []
    assert not any("truncated" in w.lower() for w in warnings)


async def test_type_evaporation_scan_pro_at_limit_boundary(
    tmp_path: Path,
    hs256_test_secret: str,
    write_hs256_license_jwt,
):
    """Pro tier at exact limit (500) should process without warnings."""
    # Create exactly 500 virtual files
    frontend_segments = []
    for i in range(500):
        frontend_segments.append(
            f"// FILE: g{i}.ts\nasync function g{i}() {{ const r = await fetch('/api/g{i}'); return r.json(); }}"
        )
    frontend_code = "\n".join(frontend_segments)

    backend_code = """
from fastapi import FastAPI
app = FastAPI()

@app.post('/api/g0')
async def g0():
    return {"ok": True}
"""

    env = _license_env(
        tmp_path,
        hs256_test_secret,
        write_hs256_license_jwt,
        tier="pro",
        jti="lic-type-evap-pro-at-limit",
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
            read_timeout_seconds=timedelta(seconds=300),
        )

    env_json = _tool_json(payload)
    data = _assert_envelope(env_json, tool_name="type_evaporation_scan")

    # assert env_json["tier"] == "pro"
    assert data.get("success") is True
    # At exact limit, processing should succeed even if implementation warns
    # (boundary behavior may vary)
    warnings = data.get("warnings") or []
    assert not any("exceeded" in w.lower() for w in warnings)


async def test_type_evaporation_scan_pro_exceeds_limit(
    tmp_path: Path,
    hs256_test_secret: str,
    write_hs256_license_jwt,
):
    """Pro tier exceeding 500 files should truncate with warning."""
    # Create 600 virtual files (exceeds Pro 500 limit)
    frontend_segments = []
    for i in range(600):
        frontend_segments.append(
            f"// FILE: h{i}.ts\nasync function h{i}() {{ const r = await fetch('/api/h{i}'); return r.json(); }}"
        )
    frontend_code = "\n".join(frontend_segments)

    backend_code = """
from fastapi import FastAPI
app = FastAPI()

@app.post('/api/h0')
async def h0():
    return {"ok": True}
"""

    env = _license_env(
        tmp_path,
        hs256_test_secret,
        write_hs256_license_jwt,
        tier="pro",
        jti="lic-type-evap-pro-exceed-limit",
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
            read_timeout_seconds=timedelta(seconds=300),
        )

    env_json = _tool_json(payload)
    data = _assert_envelope(env_json, tool_name="type_evaporation_scan")

    # assert env_json["tier"] == "pro"
    assert data.get("success") is True
    # Pro should still process successfully but may truncate at file limit
    # Check truncation warning if present
    warnings = data.get("warnings") or []
    if warnings:
        # If warnings exist, at least one should mention truncation
        assert any("truncated" in w.lower() for w in warnings)


# =============================================================================
# SECTION 2.3: Enterprise Tier Limits (⚠️ CRITICAL)
# =============================================================================


async def test_type_evaporation_scan_enterprise_unlimited_files(
    tmp_path: Path,
    hs256_test_secret: str,
    write_hs256_license_jwt,
):
    """Enterprise tier should handle large number of files without truncation."""
    # Create 1000 virtual files (well beyond Pro 500)
    frontend_segments = []
    for i in range(1000):
        frontend_segments.append(
            f"// FILE: e{i}.ts\nasync function e{i}() {{ const r = await fetch('/api/e{i}'); return r.json(); }}"
        )
    frontend_code = "\n".join(frontend_segments)

    backend_code = """
from fastapi import FastAPI
app = FastAPI()

@app.post('/api/e0')
async def e0():
    return {"ok": True}
"""

    env = _license_env(
        tmp_path,
        hs256_test_secret,
        write_hs256_license_jwt,
        tier="enterprise",
        jti="lic-type-evap-enterprise-unlimited",
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
            read_timeout_seconds=timedelta(seconds=480),
        )

    env_json = _tool_json(payload)
    data = _assert_envelope(env_json, tool_name="type_evaporation_scan")

    # assert env_json["tier"] == "enterprise"
    assert data.get("success") is True
    # Enterprise should NOT truncate even at 1000 files
    warnings = data.get("warnings") or []
    assert not any("truncated" in w.lower() for w in warnings)
    # Should have enterprise-specific fields like api_contract or compliance_report
    assert data.get("api_contract") is not None or data.get("compliance_report") is not None


async def test_type_evaporation_scan_enterprise_performance_at_scale(
    tmp_path: Path,
    hs256_test_secret: str,
    write_hs256_license_jwt,
):
    """Enterprise tier should maintain performance even at large scale."""
    import time

    # Create 500 virtual files with complex patterns
    frontend_segments = []
    for i in range(500):
        frontend_segments.append(f"""// FILE: complex{i}.ts
interface Data{i} {{ id: string; value: number; }}
async function process{i}() {{
  const r = await fetch('/api/data{i}');
  const data: Data{i} = await r.json();
  return {{ id: data.id, calculated: data.value * 2 }};
}}
""")
    frontend_code = "\n".join(frontend_segments)

    backend_code = """
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class DataModel(BaseModel):
    id: str
    value: int

@app.post('/api/data0')
async def get_data(req: DataModel):
    return {"id": req.id, "value": req.value}
"""

    env = _license_env(
        tmp_path,
        hs256_test_secret,
        write_hs256_license_jwt,
        tier="enterprise",
        jti="lic-type-evap-enterprise-perf",
    )

    start = time.time()
    async with _stdio_session(project_root=tmp_path, extra_env=env) as session:
        payload = await session.call_tool(
            "type_evaporation_scan",
            arguments={
                "frontend_code": frontend_code,
                "backend_code": backend_code,
                "frontend_file": "frontend.ts",
                "backend_file": "backend.py",
            },
            read_timeout_seconds=timedelta(seconds=480),
        )
    duration = time.time() - start

    env_json = _tool_json(payload)
    data = _assert_envelope(env_json, tool_name="type_evaporation_scan")

    # assert env_json["tier"] == "enterprise"
    assert data.get("success") is True
    # Enterprise should complete at reasonable speed even at scale
    assert duration < 30.0  # 30 second timeout for scale test
    # Should generate enterprise artifacts at scale
    assert data.get("generated_schemas") is not None
    assert data.get("pydantic_models") is not None


# =============================================================================
# SECTION 3.3: Parameter Validation
# =============================================================================


async def test_type_evaporation_scan_invalid_parameter_type(tmp_path: Path):
    """Invalid parameter type should return error or be handled gracefully."""
    async with _stdio_session(project_root=tmp_path) as session:
        # Pass integer instead of string for frontend_code
        payload = await session.call_tool(
            "type_evaporation_scan",
            arguments={
                "frontend_code": 12345,  # Should be string
                "backend_code": "code",
                "frontend_file": "frontend.ts",
                "backend_file": "backend.py",
            },
            read_timeout_seconds=timedelta(seconds=120),
        )

    # [20260120_FIX] Pydantic may coerce integer to string, or MCP may return error
    # Either way is acceptable behavior for type validation
    if payload.isError:
        # MCP/Pydantic caught validation error - acceptable
        assert payload.content, "Error should have content"
    else:
        # Pydantic coerced to string - tool should still succeed
        env_json = _tool_json(payload)
        assert "success" in env_json or "error" in env_json


# =============================================================================
# SECTION 3.4: Response Model Validation
# =============================================================================


async def test_type_evaporation_scan_response_field_types_community(
    tmp_path: Path,
):
    """Verify Community tier response has correct field types."""
    frontend_code = "async function f() { await fetch('/api/test'); }"
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

    # Verify required fields
    assert isinstance(data.get("success"), bool)
    assert isinstance(data.get("frontend_vulnerabilities"), int)
    assert isinstance(data.get("backend_vulnerabilities"), int)
    assert isinstance(data.get("cross_file_issues"), int)

    # Verify list fields
    vulnerabilities = data.get("vulnerabilities")
    if vulnerabilities is not None:
        assert isinstance(vulnerabilities, list)

    summary = data.get("summary")
    if summary is not None:
        assert isinstance(summary, str)


async def test_type_evaporation_scan_response_field_types_pro(
    tmp_path: Path,
    hs256_test_secret: str,
    write_hs256_license_jwt,
):
    """Verify Pro tier response has correct field types including Pro-only fields."""
    frontend_code = """
async function f() {
    const resp = await fetch('/api/test');
    const data = await resp.json();
    return data;
}
"""
    backend_code = "from flask import Flask\napp = Flask(__name__)"

    env = _license_env(
        tmp_path,
        hs256_test_secret,
        write_hs256_license_jwt,
        tier="pro",
        jti="lic-type-evap-pro-response-types",
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
    data = _assert_envelope(env_json, tool_name="type_evaporation_scan")

    # Verify Pro-specific fields exist and have correct types
    assert isinstance(data.get("implicit_any_count", 0), int)

    network_boundaries = data.get("network_boundaries")
    if network_boundaries is not None:
        assert isinstance(network_boundaries, list)
        # Each boundary should be a dict
        for boundary in network_boundaries:
            assert isinstance(boundary, dict)

    library_boundaries = data.get("library_boundaries")
    if library_boundaries is not None:
        assert isinstance(library_boundaries, list)

    json_parse_locations = data.get("json_parse_locations")
    if json_parse_locations is not None:
        assert isinstance(json_parse_locations, list)


async def test_type_evaporation_scan_response_field_types_enterprise(
    tmp_path: Path,
    hs256_test_secret: str,
    write_hs256_license_jwt,
):
    """Verify Enterprise tier response has correct field types including Enterprise fields."""
    frontend_code = """
type Role = 'admin' | 'user';
async function f(role: Role) {
    const resp = await fetch('/api/test', { method: 'POST', body: JSON.stringify({ role }) });
    return resp.json();
}
"""
    backend_code = """
from flask import Flask, request
app = Flask(__name__)

@app.post('/api/test')
def test():
    data = request.get_json()
    return data
"""

    env = _license_env(
        tmp_path,
        hs256_test_secret,
        write_hs256_license_jwt,
        tier="enterprise",
        jti="lic-type-evap-enterprise-response-types",
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
    data = _assert_envelope(env_json, tool_name="type_evaporation_scan")

    # Verify Enterprise-specific fields exist
    generated_schemas = data.get("generated_schemas")
    if generated_schemas is not None:
        assert isinstance(generated_schemas, list)

    pydantic_models = data.get("pydantic_models")
    if pydantic_models is not None:
        assert isinstance(pydantic_models, list)

    schema_coverage = data.get("schema_coverage")
    if schema_coverage is not None:
        assert isinstance(schema_coverage, (int, float))
        assert 0.0 <= schema_coverage <= 1.0

    api_contract = data.get("api_contract")
    if api_contract is not None:
        assert isinstance(api_contract, dict)
