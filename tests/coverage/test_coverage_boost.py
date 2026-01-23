import types

import networkx as nx

from code_scalpel.code_analyzer import CodeAnalyzer
from code_scalpel.generators.test_generator import TestGenerator
from code_scalpel.integrations import rest_api_server
from code_scalpel.integrations.rest_api_server import MCPServerConfig
from code_scalpel.pdg_tools.visualizer import PDGVisualizer

# [20251214_TEST] Target high-yield coverage gaps (CodeAnalyzer, TestGenerator, PDGVisualizer, REST API)
# [20251214_REFACTOR] Remove unused imports flagged by ruff.


def test_code_analyzer_metrics_and_dead_code():
    code = (
        "def used(x):\n"
        "    return x + 1\n\n"
        "def unused_func():\n"
        "    return 0\n\n"
        "unused_var = 5\n"
        "if unused_var > 1:\n"
        "    y = unused_var\n"
    )

    analyzer = CodeAnalyzer()
    result = analyzer.analyze(code)

    assert result.metrics.lines_of_code >= 5
    assert result.metrics.num_functions == 2
    dead_names = {item.name for item in result.dead_code}
    assert "unused_func" in dead_names
    assert "y" in dead_names


def test_test_generator_basic_path_and_values():
    tg = TestGenerator()
    code = """\
def guard(x):
    if x > 10:
        return 1
    return -1
"""

    paths = tg._basic_path_analysis(code, language="python")["paths"]
    assert len(paths) == 2

    greater_val = tg._generate_satisfying_value("x > 10", "x", should_satisfy=True)
    lesser_val = tg._generate_satisfying_value("x > 10", "x", should_satisfy=False)
    assert greater_val > 10
    assert lesser_val <= 10


def test_pdg_visualizer_styles_and_wrapping():
    viz = PDGVisualizer()
    wrapped = viz._wrap_text("word wrap check please", width=10)
    assert "\\n" in wrapped

    g = nx.DiGraph()
    g.add_node("n1", type="assign", lineno=1)
    g.add_edge("n1", "n1", type="control_dependency")

    viz.config.highlight_nodes = {"n1"}
    style = viz._get_node_style("n1", g.nodes["n1"])
    assert style["fillcolor"]
    assert style.get("penwidth") == "3.0"

    edge_style = viz._get_edge_style({"type": "control_dependency"})
    assert edge_style["color"] == "red"


# [20251214_TEST] Exercise REST API input validation and happy-path stubs


def test_rest_api_server_validation_and_analyze(monkeypatch):
    class DummyScalpel:
        def __init__(self, cache_enabled=True):
            self.cache_enabled = cache_enabled

        def analyze(self, code):
            return types.SimpleNamespace(
                success=True,
                analysis={"parsed": True},
                issues=[],
                suggestions=[],
                error=None,
            )

    import sys
    import types as pytypes

    dummy_module = pytypes.ModuleType("code_scalpel.integrations.crewai")
    dummy_module.CrewAIScalpel = DummyScalpel
    monkeypatch.setitem(sys.modules, "code_scalpel.integrations.crewai", dummy_module)
    monkeypatch.setitem(sys.modules, "integrations.crewai", dummy_module)

    config = MCPServerConfig(max_code_size=50, cache_enabled=False)
    app = rest_api_server.create_app(config)
    app.testing = True
    client = app.test_client()

    # Oversized payload rejected
    resp = client.post("/analyze", json={"code": "x" * 200})
    assert resp.status_code in (400, 413)
    payload = resp.get_json(silent=True)
    if payload:
        assert "exceeds maximum" in payload.get("error", "")

    # Happy path with stubbed analyzer
    resp_ok = client.post("/analyze", json={"code": "print('ok')"})
    payload = resp_ok.get_json()
    assert resp_ok.status_code == 200
    assert payload["success"] is True
    assert payload["analysis"]["parsed"] is True
