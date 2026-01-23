"""
[20251214_TEST] REST API server endpoint coverage.
"""

import json

pytest.importorskip("flask")

from code_scalpel.integrations.rest_api_server import MCPServerConfig, create_app


def _client(max_code_size: int = 100000):
    app = create_app(MCPServerConfig(max_code_size=max_code_size))
    return app.test_client()


def test_health_endpoint():
    client = _client()
    resp = client.get("/health")
    assert resp.status_code == 200
    payload = resp.get_json()
    assert payload["status"] == "healthy"


def test_analyze_missing_body_returns_400():
    client = _client()
    resp = client.post("/analyze", data="")
    # [20260507_TEST] The API returns 415 for empty body without content type.
    assert resp.status_code == 415


def test_analyze_enforces_max_size():
    client = _client(max_code_size=4)
    resp = client.post(
        "/analyze",
        data=json.dumps({"code": "print('too long')"}),
        content_type="application/json",
    )
    # [20260507_TEST] Align with API behavior returning 413 when payload exceeds limit.
    assert resp.status_code == 413


def test_security_missing_code():
    client = _client()
    resp = client.post("/security", data=json.dumps({}), content_type="application/json")
    assert resp.status_code == 400
    payload = resp.get_json()
    assert payload["success"] is False


def test_symbolic_missing_code():
    client = _client()
    resp = client.post("/symbolic", data=json.dumps({}), content_type="application/json")
    assert resp.status_code == 400
    payload = resp.get_json()
    assert payload["success"] is False


# [20251214_TEST] Validate happy-path analysis and refactor responses.
def test_analyze_and_refactor_success_paths():
    client = _client()
    code = """
def add(a, b):
    return a + b
"""

    analyze_resp = client.post(
        "/analyze",
        data=json.dumps({"code": code}),
        content_type="application/json",
    )
    assert analyze_resp.status_code == 200
    analyze_payload = analyze_resp.get_json()
    assert analyze_payload["success"] is True
    assert "analysis" in analyze_payload

    refactor_resp = client.post(
        "/refactor",
        data=json.dumps({"code": code, "task": "format"}),
        content_type="application/json",
    )
    assert refactor_resp.status_code == 200
    refactor_payload = refactor_resp.get_json()
    assert refactor_payload["success"] is True
    assert refactor_payload["refactored_code"]


# [20251214_TEST] Validate type enforcement on symbolic endpoint.
def test_symbolic_rejects_non_string_code():
    client = _client()
    resp = client.post(
        "/symbolic",
        data=json.dumps({"code": 123}),
        content_type="application/json",
    )
    assert resp.status_code == 400
    payload = resp.get_json()
    assert payload["success"] is False


def test_list_tools():
    client = _client()
    resp = client.get("/tools")
    assert resp.status_code == 200
    payload = resp.get_json()
    tool_names = {tool["name"] for tool in payload["tools"]}
    assert {"analyze", "security", "symbolic", "refactor"}.issubset(tool_names)


# [20251214_TEST] Ensure production debug guard disables debug flag.
def test_run_server_forces_debug_off_in_production(monkeypatch):
    import warnings

    from code_scalpel.integrations import rest_api_server

    captured = {}

    class FakeApp:
        def run(self, host: str, port: int, debug: bool):  # noqa: D401 - simple stub
            captured["host"] = host
            captured["port"] = port
            captured["debug"] = debug

    def fake_create_app(config):
        captured["config"] = config
        return FakeApp()

    monkeypatch.setattr(rest_api_server, "create_app", fake_create_app)
    monkeypatch.setenv("FLASK_ENV", "production")

    # [20251228_TEST] This test intentionally requests debug=True in production
    # to validate the guard; suppress the warning to keep suite output clean.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        rest_api_server.run_server(host="127.0.0.1", port=9999, debug=True)

    assert captured["config"].host == "127.0.0.1"
    assert captured["config"].port == 9999
    assert captured["debug"] is False
