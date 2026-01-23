# [20251214_TEST] Added low-rate coverage tests for CLI error paths, caching, integrations, and visualization branches.
import ast
from types import SimpleNamespace

import networkx as nx
import pytest

pytest.importorskip("flask")

from code_scalpel import cli
from code_scalpel.analysis.code_analyzer import AnalysisLevel, CodeAnalyzer
from code_scalpel.integrations.crewai import CrewAIScalpel
from code_scalpel.integrations.rest_api_server import MCPServerConfig, create_app
from code_scalpel.ir.normalizers.python_normalizer import PythonNormalizer
from code_scalpel.mcp import server as mcp_server
from code_scalpel.pdg_tools.visualizer import PDGVisualizer


def test_cli_analyze_file_missing_path(capsys):
    exit_code = cli.analyze_file("nonexistent_file.py")
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "File not found" in captured.err


def test_cli_scan_security_analysis_error(monkeypatch, tmp_path, capsys):
    target_file = tmp_path / "sample.py"
    target_file.write_text("print('hi')", encoding="utf-8")

    def _boom(_code: str):  # noqa: ANN001
        raise ValueError("scan failed")

    monkeypatch.setattr("code_scalpel.symbolic_execution_tools.analyze_security", _boom)

    exit_code = cli.scan_security(str(target_file))
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "Error during security analysis: scan failed" in captured.err


def test_code_analyzer_cache_hit_and_full_symbolic():
    analyzer = CodeAnalyzer(level=AnalysisLevel.FULL, cache_enabled=True)
    code = """
if flag:
    value = 1
else:
    value = 2
"""
    first = analyzer.analyze(code)
    second = analyzer.analyze(code)

    assert first is second  # cache hit returns the same object
    assert any(path["type"] == "conditional" for path in first.symbolic_paths)


def test_code_analyzer_cache_disabled_returns_fresh_results():
    analyzer = CodeAnalyzer(level=AnalysisLevel.STANDARD, cache_enabled=False)
    code = """
import math

def compute(x):
    return math.sqrt(x)
"""
    first = analyzer.analyze(code)
    second = analyzer.analyze(code)

    assert first is not second
    assert first.metrics.lines_of_code == second.metrics.lines_of_code


def test_crewai_syntax_error_path():
    tool = CrewAIScalpel()
    result = tool.analyze("def bad(")

    assert result.success is False
    assert result.error and result.error.startswith("Syntax error")
    assert result.analysis.get("parsed") is False


def test_rest_api_analyze_internal_error(monkeypatch):
    def _explode(self, _code):  # noqa: ANN001
        raise RuntimeError("kaboom")

    monkeypatch.setattr(CrewAIScalpel, "analyze", _explode)
    app = create_app(MCPServerConfig())

    with app.test_client() as client:
        response = client.post("/analyze", json={"code": "print('hi')"})

    assert response.status_code == 500
    payload = response.get_json()
    assert payload["success"] is False
    assert "Internal error: kaboom" in payload["error"]


def test_rest_api_security_internal_error(monkeypatch):
    def _explode(self, _code):  # noqa: ANN001
        raise RuntimeError("blow up")

    monkeypatch.setattr(CrewAIScalpel, "analyze_security", _explode)
    app = create_app(MCPServerConfig())

    with app.test_client() as client:
        response = client.post("/security", json={"code": "print('hi')"})

    assert response.status_code == 500
    payload = response.get_json()
    assert payload["success"] is False
    assert "Internal error: blow up" in payload["error"]


class _StubTransportSecurity:
    def __init__(
        self,
        enable_dns_rebinding_protection=True,  # noqa: ANN001, B008
        allowed_hosts=None,
        allowed_origins=None,
    ):
        self.enable_dns_rebinding_protection = enable_dns_rebinding_protection
        self.allowed_hosts = allowed_hosts or []
        self.allowed_origins = allowed_origins or []


class _StubMCP:
    def __init__(self):
        self.settings = SimpleNamespace(host=None, port=None, transport_security=None)
        self.run_calls: list[tuple[tuple, dict]] = []

    def run(self, *args, **kwargs):  # noqa: ANN401
        self.run_calls.append((args, kwargs))


def test_run_server_http_with_lan_warning(monkeypatch, capsys):
    stub = _StubMCP()
    monkeypatch.setattr(mcp_server, "mcp", stub)
    monkeypatch.setattr(
        "mcp.server.transport_security.TransportSecuritySettings",
        _StubTransportSecurity,
    )

    mcp_server.run_server(transport="streamable-http", host="127.0.0.1", allow_lan=True)
    captured = capsys.readouterr()

    assert stub.settings.host == "127.0.0.1"
    assert stub.settings.port == 8080
    assert stub.run_calls[-1][1].get("transport") == "streamable-http"
    assert "LAN access enabled" in captured.out


def test_run_server_stdio_with_missing_root(monkeypatch, tmp_path, capsys):
    stub = _StubMCP()
    missing_root = tmp_path / "does_not_exist"
    monkeypatch.setattr(mcp_server, "mcp", stub)

    mcp_server.run_server(transport="stdio", root_path=str(missing_root))
    captured = capsys.readouterr()

    assert stub.run_calls[-1][0] == ()
    # [20251216_TEST] stdio transport now emits warnings to stderr to avoid JSON-RPC interference
    assert "Warning: Root path" in captured.err


def test_python_normalizer_unsupported_node():
    normalizer = PythonNormalizer()
    match_node = ast.parse("match value:\n    case 1:\n        pass").body[0]

    with pytest.raises(NotImplementedError):
        normalizer.normalize_node(match_node)


def test_visualizer_d3_conversion_and_details_panel():
    graph = nx.DiGraph()
    graph.add_node("n1", type="assign", value="x")
    graph.add_node("n2", type="if", condition="x > 0")
    graph.add_edge("n1", "n2", type="control_dependency")

    visualizer = PDGVisualizer()
    d3 = visualizer._convert_to_d3_format(graph)
    html = visualizer._generate_interactive_html(d3, include_details=True)

    assert d3["nodes"] and d3["links"]
    assert "node-details" in html
    assert "d3.forceSimulation" in html


def test_visualizer_highlight_graph_differences():
    g1 = nx.DiGraph()
    g1.add_node("a", type="assign")
    g2 = nx.DiGraph()
    g2.add_node("b", type="assign")

    visualizer = PDGVisualizer()
    data1 = visualizer._convert_to_d3_format(g1)
    data2 = visualizer._convert_to_d3_format(g2)
    visualizer._highlight_graph_differences(data1, data2)

    assert data1["nodes"][0]["data"]["_status"] == "removed"
    assert data2["nodes"][0]["data"]["_status"] == "added"
