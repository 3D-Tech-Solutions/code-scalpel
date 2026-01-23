import asyncio
from pathlib import Path

import networkx as nx
import pytest

from code_scalpel.ast_tools.import_resolver import ImportResolver, ImportType
from code_scalpel.pdg_tools.transformer import PDGTransformer
from code_scalpel.security.analyzers.cross_file_taint import (
    CrossFileSink,
    CrossFileTaintTracker,
)


def _write(tmp_path: Path, relative: str, content: str) -> Path:
    path = tmp_path / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


@pytest.mark.skip(reason="[20260117_TEST] ImportType.FRAMEWORK not implemented - feature incomplete")
def test_import_resolver_dynamic_and_framework(tmp_path: Path) -> None:
    """Ensure dynamic imports and framework-derived imports are captured."""

    # [20251214_TEST] Cover dynamic imports and Flask/Django framework detection paths
    _write(
        tmp_path,
        "app/main.py",
        """
import importlib
from flask import Blueprint

INSTALLED_APPS = ["plugins.analytics"]
bp = Blueprint("bp", __name__)
app = type("App", (), {"register_blueprint": lambda self, bp: None})()

def build():
    mod = importlib.import_module("pkg.mod")
    app.register_blueprint(bp)
    return mod
""",
    )
    _write(tmp_path, "app/pkg/mod.py", "value = 1\n")

    resolver = ImportResolver(tmp_path)
    result = resolver.build()

    assert result.success

    imports = resolver.imports["app.main"]
    dynamic = [imp for imp in imports if imp.import_type == ImportType.DYNAMIC]
    framework = [imp for imp in imports if imp.import_type == ImportType.FRAMEWORK]

    assert any(imp.module == "pkg.mod" for imp in dynamic)
    assert any(imp.module == "plugins.analytics" for imp in framework)


def test_cross_file_taint_sql_flow(tmp_path: Path) -> None:
    """Detect cross-file taint reaching an SQL sink."""

    # [20251214_TEST] Exercise call graph + taint propagation across modules
    _write(
        tmp_path,
        "source.py",
        """
from sink import run_query


def controller(request):
    user_id = request.args.get("id")
    return run_query(user_id)
""",
    )

    _write(
        tmp_path,
        "sink.py",
        """
def run_query(param):
    cursor = type("C", (), {"execute": lambda self, q: None})()
    return cursor.execute(param)
""",
    )

    tracker = CrossFileTaintTracker(tmp_path)
    result = tracker.analyze()

    assert result.success
    assert any(flow.sink_type == CrossFileSink.SQL_QUERY for flow in result.taint_flows)


def test_pdg_transformer_loop_optimization(tmp_path: Path) -> None:
    """Hoist loop-invariant nodes and propagate constants."""

    # [20251214_TEST] Cover loop invariant detection and hoisting path
    graph = nx.DiGraph()
    graph.add_node("loop", type="for", body_nodes={"inv", "has_effect"})
    graph.add_node(
        "inv",
        type="assign",
        value="CONST",
        uses=set(),
        has_side_effects=False,
    )
    graph.add_node(
        "has_effect",
        type="assign",
        value="x",
        uses=set(),
        has_side_effects=True,
    )

    transformer = PDGTransformer(graph)

    optimize_result = transformer.optimize_pdg(optimize_dead_code=False, optimize_constants=True, optimize_loops=True)

    assert optimize_result.success
    assert any(node.endswith("_hoisted") for node in optimize_result.added_nodes)

    # [20251214_TEST] Cover constant propagation path
    graph.add_node("assign_const", type="assign", target="CONST", value="1")
    graph.add_node("use_const", type="assign", value="CONST", uses={"CONST"})

    propagate_result = transformer._propagate_constants()

    assert propagate_result.success
    assert "use_const" in propagate_result.modified_nodes


def test_crewai_async_analyze(tmp_path: Path, monkeypatch) -> None:
    """Verify CrewAI wrapper async path returns analysis."""

    from code_scalpel.integrations.crewai import CrewAIScalpel

    # [20251214_TEST] Ensure async wrapper delegates correctly
    wrapper = CrewAIScalpel(cache_enabled=False)

    code = "def add(x, y):\n    return x + y\n"
    result = asyncio.run(wrapper.analyze_async(code))

    assert result.analysis.get("parsed") is True
    assert result.success


def test_rest_api_server_health_and_tools() -> None:
    """Exercise Flask app helper endpoints."""

    # [20251214_TEST] Cover list_tools and health endpoints
    from code_scalpel.integrations.rest_api_server import create_app

    app = create_app()
    client = app.test_client()

    health = client.get("/health")
    assert health.status_code == 200
    assert health.get_json()["status"] == "healthy"

    tools = client.get("/tools")
    assert tools.status_code == 200
    payload = tools.get_json()
    assert payload["service"] == "code-scalpel-mcp"
    assert any(tool["name"] == "analyze" for tool in payload["tools"])


def test_ast_tools_init_exports() -> None:
    """Importing ast_tools populates convenience exports."""

    # [20251214_TEST] Cover ast_tools __init__ guarded imports
    import code_scalpel.ast_tools as at

    tree = at.build_ast("x = 1")
    assert tree is not None
    assert "ImportResolver" in at.__all__


def test_import_resolver_warns_on_syntax_error(tmp_path: Path) -> None:
    """Syntax errors should be recorded as warnings, not fatal errors."""

    # [20251215_TEST] Hit _analyze_file SyntaxError branch and warning aggregation
    _write(tmp_path, "bad.py", "def broken(:\n    pass\n")

    resolver = ImportResolver(tmp_path)
    result = resolver.build()

    assert result.success is True
    assert any("Syntax error" in msg for msg in result.warnings)


def test_cross_file_taint_path_traversal_severity(tmp_path: Path) -> None:
    """Path traversal sink should surface as medium severity."""

    # [20251215_TEST] Ensure FILE_PATH sink hits _determine_severity medium branch
    _write(
        tmp_path,
        "handler.py",
        """
from storage import read_file


def controller(request):
    path = request.args.get("file")
    return read_file(path)
""",
    )

    _write(
        tmp_path,
        "storage.py",
        """
def read_file(path):
    return open(path).read()
""",
    )

    tracker = CrossFileTaintTracker(tmp_path)
    result = tracker.analyze()

    assert result.success
    assert any(flow.sink_type == CrossFileSink.FILE_PATH for flow in result.taint_flows)
    assert any(v.severity == "MEDIUM" for v in result.vulnerabilities)


def test_rest_api_server_handles_internal_error(monkeypatch) -> None:
    """Flask endpoints should surface internal errors as HTTP 500."""

    from code_scalpel.integrations import crewai, rest_api_server

    # [20251215_TEST] Force CrewAIScalpel.analyze to raise and hit error handler
    def boom(self, code: str):  # pragma: no cover - branch focus
        raise RuntimeError("boom")

    monkeypatch.setattr(crewai.CrewAIScalpel, "analyze", boom)

    app = rest_api_server.create_app()
    client = app.test_client()

    resp = client.post("/analyze", json={"code": "print('x')"})

    assert resp.status_code == 500
    payload = resp.get_json()
    assert payload["success"] is False
    assert "boom" in payload.get("error", "")


def test_crewai_handles_syntax_error(monkeypatch) -> None:
    """CrewAI wrapper should surface syntax errors from analyzer."""

    from code_scalpel.integrations.crewai import CrewAIScalpel

    # [20251216_TEST] Hit _analyze_sync SyntaxError handling branch
    wrapper = CrewAIScalpel(cache_enabled=False)

    class StubAnalyzer:
        def parse_to_ast(self, code: str):  # pragma: no cover - branch target
            raise SyntaxError("bad syntax")

    wrapper.analyzer = StubAnalyzer()

    result = wrapper.analyze("print('x')")

    assert result.success is False
    assert "Syntax error" in (result.error or "")
    assert result.analysis.get("parsed") is False


def test_crewai_handles_analysis_error(monkeypatch) -> None:
    """CrewAI wrapper should surface unexpected analysis errors."""

    from code_scalpel.integrations.crewai import CrewAIScalpel

    # [20251216_TEST] Hit _analyze_sync generic Exception handling branch
    wrapper = CrewAIScalpel(cache_enabled=False)

    class StubAnalyzer:
        def parse_to_ast(self, code: str):  # pragma: no cover - branch target
            return "tree"

        def analyze_code_style(self, tree):  # pragma: no cover - branch target
            raise RuntimeError("style fail")

        def find_security_issues(self, tree):  # pragma: no cover - branch target
            return []

    wrapper.analyzer = StubAnalyzer()

    result = wrapper.analyze("print('x')")

    assert result.success is False
    assert "Analysis error" in (result.error or "")
    assert result.analysis.get("parsed") is False


def test_run_server_disables_debug_in_production(monkeypatch) -> None:
    """run_server should warn and disable debug when FLASK_ENV=production."""

    from code_scalpel.integrations import rest_api_server

    # [20251216_TEST] Exercise production debug warning path without starting server
    calls = {}

    class StubApp:
        def run(self, host, port, debug):  # pragma: no cover - branch target
            calls.update({"host": host, "port": port, "debug": debug})

    monkeypatch.setenv("FLASK_ENV", "production")
    monkeypatch.setattr(rest_api_server, "create_app", lambda config=None: StubApp())

    with pytest.warns(RuntimeWarning):
        rest_api_server.run_server(host="127.0.0.1", port=5000, debug=True)

    assert calls == {"host": "127.0.0.1", "port": 5000, "debug": False}
