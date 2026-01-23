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
