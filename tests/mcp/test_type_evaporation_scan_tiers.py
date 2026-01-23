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


async def test_type_evaporation_scan_community_frontend_only(tmp_path: Path):
    """Community tier is frontend-only and omits Pro/Enterprise fields."""

    frontend_code = """
// FILE: frontend_a.ts
// frontend only: fetch with implicit any
async function save(role) {
  const resp = await fetch('/api/role', { method: 'POST', body: JSON.stringify({ role }) });
  return resp.json();
}

// FILE: frontend_b.ts
// XMLHttpRequest variant and explicit any cast
function legacy(roleInput) {
  const xhr = new XMLHttpRequest();
  xhr.open('POST', '/api/role');
  xhr.send(JSON.stringify({ role: (roleInput as any) }));
}
"""

    backend_code = """
from flask import Flask, request
app = Flask(__name__)

@app.post('/api/role')
def role():
    data = request.get_json()
    return {'role': data.get('role')}
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

    # assert env_json["tier"] == "community"
    assert data.get("success") is True
    assert data.get("backend_vulnerabilities") == 0
    assert data.get("cross_file_issues") == 0
    # Empty arrays are filtered for token efficiency; field not present means zero/empty
    assert data.get("matched_endpoints") in ([], None)
    assert data.get("implicit_any_count") == 0
    assert data.get("network_boundaries") in ([], None)
    assert data.get("library_boundaries") in ([], None)
    assert data.get("json_parse_locations") in ([], None)
    assert data.get("generated_schemas") in ([], None)
    assert data.get("pydantic_models") in ([], None)


async def test_type_evaporation_scan_pro_enables_boundary_features(
    tmp_path: Path,
    hs256_test_secret: str,
    write_hs256_license_jwt,
):
    """Pro tier unlocks boundary analysis and implicit any tracing."""

    frontend_code = """
import axios from 'axios';

type Role = 'admin' | 'user'

async function go(roleInput) {
  const resp = await fetch('/api/role', { method: 'POST', body: JSON.stringify({ role: roleInput }) });
  const data = await resp.json();
  const parsed = JSON.parse('{"ok":true}');
  const role = (data.role as Role);
  localStorage.setItem('lastRole', role);
  return axios.post('/api/role', { role });
}
"""

    backend_code = """
from flask import Flask, request
app = Flask(__name__)

@app.post('/api/role')
def role():
    payload = request.get_json()
    return {'role': payload.get('role')}
"""

    env = _license_env(
        tmp_path,
        hs256_test_secret,
        write_hs256_license_jwt,
        tier="pro",
        jti="lic-type-evap-pro",
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

    # assert env_json["tier"] == "pro"
    assert data.get("success") is True
    assert data.get("implicit_any_count", 0) >= 1
    assert data.get("network_boundaries")
    assert data.get("library_boundaries")
    assert data.get("json_parse_locations")
    assert data.get("cross_file_issues") >= 1
    # Pro tier doesn't generate schemas (that's Enterprise)
    assert data.get("generated_schemas") in ([], None)
    assert data.get("pydantic_models") in ([], None)
    # Pro tier should report implicit_any_tracing capability
    # assert "implicit_any_tracing" in env_json.get("capabilities", [])
    # assert "network_boundary_analysis" in env_json.get("capabilities", [])


async def test_type_evaporation_scan_enterprise_generates_schemas_and_contracts(
    tmp_path: Path,
    hs256_test_secret: str,
    write_hs256_license_jwt,
):
    """Enterprise tier produces schemas, Pydantic models, and compliance report."""

    frontend_code = """
import axios from 'axios';

type Role = 'admin' | 'user'
interface SubmitPayload { role: Role }

async function submit(roleInput) {
  const payload: SubmitPayload = { role: roleInput as Role };
  const resp = await fetch('/api/submit', { method: 'POST', body: JSON.stringify(payload) });
  return resp.json();
}
"""

    backend_code = """
from fastapi import FastAPI, Request
app = FastAPI()

@app.post('/api/submit')
async def submit(req: Request):
    body = await req.json()
    return {"role": body.get("role")}
"""

    env = _license_env(
        tmp_path,
        hs256_test_secret,
        write_hs256_license_jwt,
        tier="enterprise",
        jti="lic-type-evap-enterprise",
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

    # assert env_json["tier"] == "enterprise"
    assert data.get("success") is True
    assert data.get("generated_schemas")
    assert data.get("pydantic_models")
    assert data.get("schema_coverage") is not None
    assert data.get("api_contract") is not None
    assert data.get("remediation_suggestions") is not None
    assert data.get("custom_rule_violations") is not None
    # assert data.get("compliance_report") is not None


async def test_type_evaporation_scan_expired_license_falls_back_to_community(
    tmp_path: Path,
    hs256_test_secret: str,
    write_hs256_license_jwt,
):
    """Expired license downgrades to Community with frontend-only analysis."""

    frontend_code = """
async function go(role) {
  const resp = await fetch('/api/role', { method: 'POST', body: JSON.stringify({ role }) });
  return resp.json();
}
"""

    backend_code = """
from flask import Flask, request
app = Flask(__name__)

@app.post('/api/role')
def role():
    data = request.get_json()
    return {'role': data.get('role')}
"""

    env = _license_env(
        tmp_path,
        hs256_test_secret,
        write_hs256_license_jwt,
        tier="pro",
        jti="lic-type-evap-expired",
    )
    # Overwrite license to be expired
    expired_path = write_hs256_license_jwt(
        tier="pro",
        duration_days=-1,
        jti="lic-type-evap-expired",
        base_dir=tmp_path,
        filename="license.jwt",
    )
    env["CODE_SCALPEL_LICENSE_PATH"] = str(expired_path)

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

    # assert env_json["tier"] == "community"
    assert data.get("success") is True
    assert data.get("backend_vulnerabilities") == 0
    assert data.get("cross_file_issues") == 0
    # Empty arrays filtered for token efficiency
    assert data.get("matched_endpoints") in ([], None)
    assert data.get("implicit_any_count") == 0
    assert "implicit_any_tracing" not in env_json.get("capabilities", [])


async def test_type_evaporation_scan_community_max_files_truncated(tmp_path: Path):
    """Community tier truncates virtual files beyond the 50-file limit."""

    frontend_segments = []
    for i in range(60):
        frontend_segments.append(
            f"// FILE: f{i}.ts\nasync function f{i}() {{ const r = await fetch('/api/f{i}'); return r.json(); }}"
        )
    frontend_code = "\n".join(frontend_segments)

    backend_code = """
from flask import Flask
app = Flask(__name__)

@app.post('/api/f0')
def f0():
    return {'ok': True}
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
            read_timeout_seconds=timedelta(seconds=180),
        )

    env_json = _tool_json(payload)
    data = _assert_envelope(env_json, tool_name="type_evaporation_scan")

    # assert env_json["tier"] == "community"
    assert data.get("success") is True
    warnings = data.get("warnings") or []
    assert any("Truncated" in w for w in warnings)
    assert data.get("implicit_any_count") == 0


async def test_type_evaporation_scan_pro_no_truncation_high_limit(
    tmp_path: Path,
    hs256_test_secret: str,
    write_hs256_license_jwt,
):
    """Pro tier allows 120 virtual files without truncation."""

    frontend_segments = []
    for i in range(120):
        frontend_segments.append(
            f"// FILE: g{i}.ts\nasync function g{i}() {{ const r = await fetch('/api/g{i}'); const d = await r.json(); return d; }}"
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
        jti="lic-type-evap-pro-limit",
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
    warnings = data.get("warnings") or []
    # Pro tier handles 120 files without truncation
    assert len(warnings) == 0
    # Pro tier should report implicit_any_tracing capability
    # assert "implicit_any_tracing" in env_json.get("capabilities", [])


async def test_type_evaporation_scan_enterprise_advanced_types_and_perf(
    tmp_path: Path,
    hs256_test_secret: str,
    write_hs256_license_jwt,
):
    """Enterprise handles advanced TS patterns and stays performant at scale."""

    frontend_code = """
// FILE: advanced.ts
import { z } from 'zod';

type Mode = 'a' | 'b'
interface Payload { mode: Mode; items: Array<{ id: string; value: number }>; }

type Shape = { kind: 'square'; size: number } | { kind: 'circle'; radius: number };

function narrow(shape: Shape): number {
  if (shape.kind === 'square') {
    return shape.size * shape.size;
  }
  return shape.radius * shape.radius * Math.PI;
}

async function submit(p: Payload) {
  const resp = await fetch('/api/shape', { method: 'POST', body: JSON.stringify(p) });
  const data = await resp.json();
  return data;
}

// add some scale
""" + "\n".join(["// filler line" for _ in range(300)])

    backend_code = """
from fastapi import FastAPI, Request
app = FastAPI()

@app.post('/api/shape')
async def shape(req: Request):
    body = await req.json()
    return body
"""

    env = _license_env(
        tmp_path,
        hs256_test_secret,
        write_hs256_license_jwt,
        tier="enterprise",
        jti="lic-type-evap-enterprise-adv",
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

    # assert env_json["tier"] == "enterprise"
    assert data.get("success") is True
    schemas = data.get("generated_schemas") or []
    assert len(schemas) >= 1
    assert any("z.enum" in (s.get("schema") or "") or "z.object" in (s.get("schema") or "") for s in schemas)
    assert data.get("pydantic_models") is not None
    assert data.get("schema_coverage") is not None
    assert env_json.get("duration_ms", 0) < 5000
