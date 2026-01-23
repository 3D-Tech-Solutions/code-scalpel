import json

import pytest

pytest.importorskip("flask")

from code_scalpel.integrations.rest_api_server import (
    MCPServerConfig,
    _elapsed_ms,
    create_app,
)


def test_elapsed_ms_positive():
    # [20251214_TEST] Ensure elapsed time helper returns positive ms
    start = 0.0
    assert _elapsed_ms(start) > 0


@pytest.fixture
def app(monkeypatch):
    # Stub CrewAIScalpel to avoid heavy dependencies
    import sys
    import types

    class DummyResult:
        def __init__(self, success=True):
            self.success = success
            self.analysis = {}
            self.issues = []
            self.suggestions = []
            self.error = None

    class DummyScalpel:
        def __init__(self, cache_enabled=True):
            self.cache_enabled = cache_enabled

        def analyze(self, code):
            return DummyResult()

        def refactor(self, code, task):
            return DummyResult()

        def analyze_security(self, code):
            return {"success": True, "issues": []}

        def analyze_symbolic(self, code):
            return {"success": True, "paths": []}

    dummy_module = types.ModuleType("code_scalpel.integrations.crewai")
    dummy_module.CrewAIScalpel = DummyScalpel
    # [20251214_TEST] Provide stub CrewAIScalpel for create_app import paths
    monkeypatch.setitem(sys.modules, "code_scalpel.integrations.crewai", dummy_module)
    monkeypatch.setitem(sys.modules, "integrations.crewai", dummy_module)
    cfg = MCPServerConfig(cache_enabled=False)
    app = create_app(cfg)
    app.testing = True
    return app


def test_health_and_tools_endpoints(app):
    client = app.test_client()

    health = client.get("/health")
    tools = client.get("/tools")

    assert health.status_code == 200
    assert tools.status_code == 200
    assert "tools" in tools.get_json()


def test_analyze_validation_errors(app):
    client = app.test_client()

    # Missing body
    resp = client.post("/analyze", data="{}", content_type="application/json")
    assert resp.status_code == 400

    # Invalid code type
    payload = json.dumps({"code": 123})
    resp = client.post("/analyze", data=payload, content_type="application/json")
    assert resp.status_code == 400
