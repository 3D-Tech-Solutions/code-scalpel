import pytest


def test_type_evaporation_cross_file_matches_axios_and_router_decorators():
    from code_scalpel.security.type_safety import analyze_type_evaporation_cross_file

    ts_code = """
// Frontend: template string base + axios call
const API_BASE = "http://localhost:8000";

type Role = 'admin' | 'user'

function submit(roleInput: any) {
  const role = (roleInput as Role);
  return axios.post(`${API_BASE}/api/submit`, {
    role,
  });
}
"""

    py_code = """
from fastapi import APIRouter

router = APIRouter()

@router.post("/api/submit")
def submit(payload: dict):
    # backend trusts payload without validating allowed Role values
    return {"ok": True}
"""

    result = analyze_type_evaporation_cross_file(ts_code, py_code)

    assert result.frontend_result.fetch_endpoints
    assert result.matched_endpoints, "Expected frontend endpoint to match backend route"
    assert result.cross_file_issues, "Expected at least one cross-file type trust issue"


@pytest.mark.parametrize(
    "ts_endpoint,expected",
    [
        ("http://x:1234/api/x?y=1", "/api/x"),
        ("`${BASE}/api/x`", "/api/x"),
        ("/api/x/", "/api/x"),
    ],
)
def test_endpoint_normalization(ts_endpoint, expected):
    from code_scalpel.security.type_safety import TypeEvaporationDetector

    det = TypeEvaporationDetector()
    assert det._normalize_endpoint_candidate(ts_endpoint) == expected


# ---------------------------------------------------------------------------
# [20260314_TEST] PythonBackendAnalyzer unit tests
# ---------------------------------------------------------------------------


def test_python_backend_analyzer_detects_untyped_params():
    """PythonBackendAnalyzer flags unannotated parameters in route handlers."""
    from code_scalpel.security.type_safety.type_evaporation_detector import (
        PythonBackendAnalyzer,
    )

    code = """
from flask import Flask
app = Flask(__name__)

@app.post('/submit')
def submit(user_id, payload):
    return {'ok': True}
"""
    findings = PythonBackendAnalyzer().analyze(code)
    patterns = [f.pattern for f in findings]
    assert "UNTYPED_PARAMETER" in patterns
    untyped = [f for f in findings if f.pattern == "UNTYPED_PARAMETER"]
    assert any(f.parameter_name == "user_id" for f in untyped)
    assert any(f.parameter_name == "payload" for f in untyped)


def test_python_backend_analyzer_detects_kwargs_wildcard():
    """PythonBackendAnalyzer flags **kwargs in route handlers."""
    from code_scalpel.security.type_safety.type_evaporation_detector import (
        PythonBackendAnalyzer,
    )

    code = """
from flask import Flask
app = Flask(__name__)

@app.post('/items')
def create_item(**kwargs):
    return kwargs
"""
    findings = PythonBackendAnalyzer().analyze(code)
    assert any(
        f.pattern == "KWARGS_WILDCARD" for f in findings
    ), f"Expected KWARGS_WILDCARD in findings, got: {[f.pattern for f in findings]}"


def test_python_backend_analyzer_detects_any_annotation():
    """PythonBackendAnalyzer flags parameters annotated as Any."""
    from typing import Any  # noqa: F401 — just to ensure this resolves at import time

    from code_scalpel.security.type_safety.type_evaporation_detector import (
        PythonBackendAnalyzer,
    )

    code = """
from typing import Any
from flask import Flask
app = Flask(__name__)

@app.post('/data')
def receive(payload: Any):
    return payload
"""
    findings = PythonBackendAnalyzer().analyze(code)
    assert any(
        f.pattern == "ANY_TYPE" for f in findings
    ), f"Expected ANY_TYPE in findings, got: {[f.pattern for f in findings]}"


def test_python_backend_analyzer_detects_dict_access():
    """PythonBackendAnalyzer flags dict subscript access on request.get_json() result."""
    from code_scalpel.security.type_safety.type_evaporation_detector import (
        PythonBackendAnalyzer,
    )

    code = """
from flask import Flask, request
app = Flask(__name__)

@app.post('/login')
def login():
    data = request.get_json()
    username = data['username']
    password = data['password']
    return {'ok': True}
"""
    findings = PythonBackendAnalyzer().analyze(code)
    dict_access = [f for f in findings if f.pattern == "DICT_ACCESS_WITHOUT_VALIDATION"]
    assert (
        len(dict_access) >= 2
    ), f"Expected 2+ DICT_ACCESS_WITHOUT_VALIDATION findings, got: {dict_access}"


def test_python_backend_analyzer_no_findings_for_typed_handler():
    """Fully typed handler with Pydantic model produces no untyped-param or dict-access findings."""
    from code_scalpel.security.type_safety.type_evaporation_detector import (
        PythonBackendAnalyzer,
    )

    code = """
from flask import Flask
from pydantic import BaseModel

app = Flask(__name__)


class LoginPayload(BaseModel):
    username: str
    password: str


@app.post('/login')
def login(payload: LoginPayload) -> dict:
    return {'ok': True}
"""
    findings = PythonBackendAnalyzer().analyze(code)
    evaporation = [
        f
        for f in findings
        if f.pattern in ("UNTYPED_PARAMETER", "DICT_ACCESS_WITHOUT_VALIDATION")
    ]
    assert (
        not evaporation
    ), f"Expected no evaporation findings for fully-typed handler, got: {evaporation}"


def test_cross_file_js_backend_integration():
    """JS (no types) frontend with untyped Python handler still produces backend findings."""
    from code_scalpel.security.type_safety import analyze_type_evaporation_cross_file

    js_code = """
async function submit(data) {
    return fetch('/api/items', { method: 'POST', body: JSON.stringify(data) });
}
"""

    py_code = """
from flask import Flask, request

app = Flask(__name__)

@app.post('/api/items')
def create_item(name, qty):
    return {'name': name, 'qty': qty}
"""

    result = analyze_type_evaporation_cross_file(js_code, py_code)
    backend_patterns = [
        getattr(v, "pattern", getattr(v, "vulnerability_type", ""))
        for v in result.backend_vulnerabilities
    ]
    assert any(
        "UNTYPED_PARAMETER" in str(p) for p in backend_patterns
    ), f"Expected UNTYPED_PARAMETER for untyped JS→Python handler, got: {backend_patterns}"
