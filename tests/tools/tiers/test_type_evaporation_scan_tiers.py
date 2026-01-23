import pytest

from code_scalpel.mcp.tools import security


@pytest.mark.asyncio
async def test_type_evaporation_scan_pro_sanity(pro_tier):
    """Pro tier: verifies correlation + boundary analyses populate fields.

    - implicit_any_count > 0
    - network_boundaries detected
    - json_parse_locations detected
    - matched_endpoints present (frontend↔backend correlation)
    """
    # Frontend: define a type and make a fetch with untyped .json()
    frontend_code = ("""
// FILE: frontend.ts
// Keep type definition within ~20 lines of fetch for endpoint association
interface User { name: string; }

async function loadUser() {
  const resp = await fetch('/api/user');
  const data = await resp.json(); // implicit any
  const local = JSON.parse('{"ok": true}'); // JSON.parse without validation
  localStorage.setItem('k', JSON.stringify(data)); // library boundary
  return data as any; // rule trigger (enterprise-only)
}
""").strip()

    # Backend: simple route without validation
    backend_code = ("""
// FILE: backend.py
@app.get('/api/user')
def get_user():
    data = request.get_json()  # unvalidated
    return jsonify(data)
""").strip()

    result = await security.type_evaporation_scan(
        frontend_code=frontend_code,
        backend_code=backend_code,
        frontend_file="frontend.ts",
        backend_file="backend.py",
    )

    assert result.success is True
    # Pro features
    assert result.implicit_any_count >= 1
    assert len(result.network_boundaries) >= 1
    assert len(result.json_parse_locations) >= 1
    # Correlation
    assert len(result.matched_endpoints) >= 1


@pytest.mark.asyncio
async def test_type_evaporation_scan_enterprise_sanity(enterprise_tier):
    """Enterprise tier: verifies schema/model generation and contract validation.

    - generated_schemas not empty
    - validation_code populated
    - pydantic_models not empty
    - api_contract present (with totals)
    - schema_coverage populated
    - custom_rule_violations present (from rules)
    - compliance_report present
    """
    frontend_code = ("""
// FILE: frontend.ts
// Place type alias near fetch to associate endpoint in generator
 type Role = 'admin' | 'user';

async function postUser() {
  const r = await fetch('/api/user', { method: 'POST' });
  const payload = await r.json(); // implicit any (rule)
  const value = JSON.parse('{"x": 1}'); // JSON.parse without validation
  return payload as Role; // unsafe assertion
}
""").strip()

    backend_code = ("""
// FILE: backend.py
@app.post('/api/user')
def create_user():
    body = request.get_json()  # unvalidated
    name = body['name']
    return jsonify({'ok': True, 'name': name})
""").strip()

    result = await security.type_evaporation_scan(
        frontend_code=frontend_code,
        backend_code=backend_code,
        frontend_file="frontend.ts",
        backend_file="backend.py",
    )

    assert result.success is True
    # Enterprise features
    assert len(result.generated_schemas) >= 1
    assert result.validation_code is not None and len(result.validation_code) > 0
    assert len(result.pydantic_models) >= 1
    assert result.api_contract is not None and result.api_contract.get("total_endpoints", 0) >= 1
    assert result.schema_coverage is not None
    # Custom rules and compliance
    assert len(result.custom_rule_violations) >= 1
    assert result.compliance_report is not None
