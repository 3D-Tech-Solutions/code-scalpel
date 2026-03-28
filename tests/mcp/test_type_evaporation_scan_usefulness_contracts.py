"""Public usefulness-contract tests for type_evaporation_scan.

[20260314_TEST] Verify the documented usefulness slice for type_evaporation_scan:
- TypeScript = Core Useful: TS frontend type-evaporation detection at community tier
- JavaScript = Bounded Useful: JS frontend fetch pattern detection (no TS types)
- Python   = Bounded Useful: Python backend route-handler type evaporation analysis
  (tested at the analyze_type_evaporation_cross_file() boundary, which runs at Pro+
  tier through the MCP layer or unbounded when called directly)
"""

from __future__ import annotations

import pytest

# ---------------------------------------------------------------------------
# TypeScript (Core Useful) — MCP community-tier boundary
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ts_frontend_is_core_useful() -> None:
    """TypeScript frontend analysis detects type evaporation at community tier."""
    from code_scalpel.mcp.server import type_evaporation_scan

    ts_code = """
type Role = 'admin' | 'user';

async function submitRole(roleInput: any) {
    const role = roleInput as Role;
    const resp = await fetch('/api/role', { method: 'POST', body: JSON.stringify({ role }) });
    return resp.json();
}
"""

    result = await type_evaporation_scan(
        frontend_code=ts_code,
        backend_code="",
        frontend_file="frontend.ts",
        backend_file="backend.py",
    )

    assert result.success is True
    # TS frontend analysis runs at community tier and must find the `as Role` cast
    assert (
        result.frontend_vulnerabilities >= 1
    ), "Expected at least one TS type-evaporation finding for `roleInput as Role`"


# ---------------------------------------------------------------------------
# JavaScript (Bounded Useful) — MCP community-tier boundary
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_js_frontend_is_bounded_useful() -> None:
    """JavaScript frontend analysis succeeds without crash (no TS types, but fetch detected)."""
    from code_scalpel.mcp.server import type_evaporation_scan

    js_code = """
async function submitData(payload) {
    const resp = await fetch('/api/data', { method: 'POST', body: JSON.stringify(payload) });
    return resp.json();
}
"""

    result = await type_evaporation_scan(
        frontend_code=js_code,
        backend_code="",
        frontend_file="frontend.js",
        backend_file="backend.py",
    )

    assert result.success is True
    # JS frontend should not crash; result shape must be valid
    assert isinstance(result.frontend_vulnerabilities, int)


# ---------------------------------------------------------------------------
# Python (Bounded Useful) — analyze_type_evaporation_cross_file() boundary
# The function-level boundary is tested directly (no tier gating) so the
# Python backend contract is exercised regardless of license tier.
# ---------------------------------------------------------------------------


def test_ts_python_cross_file_type_matching() -> None:
    """TS type assertion to untyped Python handler generates cross-file type trust issues."""
    from code_scalpel.security.type_safety import analyze_type_evaporation_cross_file

    ts_code = """
type Role = 'admin' | 'user';

async function go(roleInput: any) {
    const role = roleInput as Role;
    const resp = await fetch('/api/role', { method: 'POST', body: JSON.stringify({ role }) });
    return resp.json();
}
"""

    py_code = """
from flask import Flask, request

app = Flask(__name__)

@app.post('/api/role')
def role():
    data = request.get_json()
    return {'role': data.get('role')}
"""

    result = analyze_type_evaporation_cross_file(ts_code, py_code)

    assert (
        result.matched_endpoints
    ), "Expected TS fetch('/api/role') to match Python @app.post('/api/role') route"
    assert (
        result.cross_file_issues
    ), "Expected at least one CROSS_FILE_TYPE_TRUST issue for TS `Role` type assertion"


def test_python_untyped_handler_generates_backend_vulnerabilities() -> None:
    """Untyped Python handler parameters are flagged as backend vulnerabilities."""
    from code_scalpel.security.type_safety import analyze_type_evaporation_cross_file

    ts_code = "async function go() { return fetch('/api/submit', {method: 'POST'}); }"

    py_code = """
from flask import Flask, request

app = Flask(__name__)

@app.post('/api/submit')
def submit(user_id, payload):
    data = request.get_json()
    value = data['key']
    return {'ok': True}
"""

    result = analyze_type_evaporation_cross_file(ts_code, py_code)

    assert (
        result.backend_vulnerabilities
    ), "Expected PythonBackendAnalyzer to flag untyped params and dict access in handler"
    py_patterns = [
        getattr(v, "pattern", getattr(v, "vulnerability_type", ""))
        for v in result.backend_vulnerabilities
    ]
    assert any(
        "UNTYPED_PARAMETER" in str(p) or "DICT_ACCESS" in str(p) for p in py_patterns
    ), f"Expected UNTYPED_PARAMETER or DICT_ACCESS in findings, got: {py_patterns}"


def test_python_typed_handler_has_no_evaporation_findings() -> None:
    """Fully typed Pydantic-based Python handler produces no type-evaporation findings."""
    from code_scalpel.security.type_safety.type_evaporation_detector import (
        PythonBackendAnalyzer,
    )

    py_code = """
from flask import Flask
from pydantic import BaseModel

app = Flask(__name__)


class RolePayload(BaseModel):
    role: str


@app.post('/api/role')
def submit_role(payload: RolePayload) -> dict:
    return {'role': payload.role}
"""

    findings = PythonBackendAnalyzer().analyze(py_code, "backend.py")
    # Fully typed + no dict subscript on request JSON → no UNTYPED_PARAMETER or DICT_ACCESS
    evaporation_findings = [
        f
        for f in findings
        if f.pattern in ("UNTYPED_PARAMETER", "DICT_ACCESS_WITHOUT_VALIDATION")
    ]
    assert not evaporation_findings, (
        f"Expected no evaporation findings for a fully-typed handler, "
        f"got: {evaporation_findings}"
    )


def test_mismatched_endpoints_produce_no_false_positive_matches() -> None:
    """Non-overlapping routes produce empty matched_endpoints — no false positives."""
    from code_scalpel.security.type_safety import analyze_type_evaporation_cross_file

    ts_code = "async function go() { return fetch('/api/users', {method: 'GET'}); }"

    py_code = """
from flask import Flask

app = Flask(__name__)

@app.get('/api/orders')
def orders():
    return []
"""

    result = analyze_type_evaporation_cross_file(ts_code, py_code)

    assert (
        result.matched_endpoints == []
    ), "Non-overlapping routes /api/users vs /api/orders must not match"
