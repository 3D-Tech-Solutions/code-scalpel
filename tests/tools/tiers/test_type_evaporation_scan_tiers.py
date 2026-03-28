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
    # Note: validation_code and compliance_report are excluded by response_config.json for token efficiency
    assert len(result.pydantic_models) >= 1
    assert (
        result.api_contract is not None
        and result.api_contract.get("total_endpoints", 0) >= 1
    )
    assert result.schema_coverage is not None
    # Custom rules
    assert len(result.custom_rule_violations) >= 1


@pytest.mark.asyncio
async def test_type_evaporation_scan_resolves_malformed_windows_paths(monkeypatch):
    """Malformed '/K:/...' file paths should resolve before scanning."""
    frontend_real = "/tmp/frontend.ts"
    backend_real = "/tmp/backend.py"

    def _fake_resolve(path: str, project_root: str | None = None) -> str:
        if path.endswith("frontend.ts"):
            return frontend_real
        if path.endswith("backend.py"):
            return backend_real
        return path

    monkeypatch.setattr("code_scalpel.mcp.tools.security.resolve_path", _fake_resolve)
    monkeypatch.setattr(
        "builtins.open",
        lambda path, mode="r", encoding=None: __import__("io").StringIO(
            "const payload = JSON.parse('{}');"
            if str(path).endswith("frontend.ts")
            else "def handler():\n    return {}\n"
        ),
    )

    result = await security.type_evaporation_scan(
        frontend_file_path="/K:/backup/Develop/code-scalpel-ninja-warrior/frontend.ts",
        backend_file_path="/K:/backup/Develop/code-scalpel-ninja-warrior/backend.py",
    )

    assert result.error is None
    assert result.success is True


@pytest.mark.asyncio
async def test_type_evaporation_scan_returns_correction_needed_for_unresolvable_windows_path(
    monkeypatch,
):
    """Unresolvable '/K:/...' file paths should return correction_needed."""
    resolver_error = FileNotFoundError(
        "Cannot access file: /K:/backup/Develop/code-scalpel-ninja-warrior/frontend.ts (not found)\n\n"
        "Suggestion:\n"
        "Windows path detected but file not accessible.\n"
        "If running in WSL, the path should be accessible at:\n\n"
        "  /mnt/k/backup/Develop/code-scalpel-ninja-warrior/frontend.ts"
    )

    monkeypatch.setattr(
        "code_scalpel.mcp.tools.security.resolve_path",
        lambda path, project_root=None: (_ for _ in ()).throw(resolver_error),
    )

    result = await security.type_evaporation_scan(
        frontend_file_path="/K:/backup/Develop/code-scalpel-ninja-warrior/frontend.ts",
        backend_code="def handler():\n    return {}\n",
    )

    assert result.error is not None
    assert result.error.error_code == "correction_needed"
    assert "/mnt/k/backup/Develop/code-scalpel-ninja-warrior/frontend.ts" in result.error.error
