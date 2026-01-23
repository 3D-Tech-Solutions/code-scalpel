"""Additional coverage for CrewAI integration wrapper.

[20251215_TEST] Add CrewAIScalpel tests for error handling and recommendations.
"""

import builtins
from types import SimpleNamespace

from code_scalpel.integrations.crewai import CrewAIScalpel, RefactorResult


def test_refactor_result_to_dict():
    """Ensure RefactorResult serializes expected fields."""

    result = RefactorResult(original_code="x = 1", analysis={"a": 1}, issues=[{"k": 1}])
    result.suggestions = ["keep it simple"]
    result.refactored_code = "x = 2"
    result.success = False
    result.error = "boom"

    as_dict = result.to_dict()

    assert as_dict["original_code"] == "x = 1"
    assert as_dict["analysis"] == {"a": 1}
    assert as_dict["issues"] == [{"k": 1}]
    assert as_dict["refactored_code"] == "x = 2"
    assert as_dict["success"] is False
    assert as_dict["error"] == "boom"


def test_analyze_syntax_error(monkeypatch):
    """_analyze_sync returns error when parsing fails."""

    scalpel = CrewAIScalpel()

    def bad_parse(code):
        raise SyntaxError("unexpected EOF")

    monkeypatch.setattr(scalpel.analyzer, "parse_to_ast", bad_parse)

    result = scalpel._analyze_sync("broken code")

    assert result.success is False
    assert "Syntax error" in result.error


def test_analyze_security_with_vulns(monkeypatch):
    """analyze_security aggregates vulnerability metadata and risk."""

    scalpel = CrewAIScalpel()

    fake_vuln = SimpleNamespace(
        vulnerability_type="sql_injection",
        cwe_id="CWE-89",
        taint_source=SimpleNamespace(name="user_input"),
        sink_type=SimpleNamespace(name="execute"),
        sink_location=(3, 0),
        taint_path=["user_input", "query"],
        to_dict=lambda: {"type": "sql_injection"},
    )

    class FakeResult:
        vulnerabilities = [fake_vuln]
        vulnerability_count = 1
        has_vulnerabilities = True

        def get_sql_injections(self):
            return [fake_vuln]

        def get_xss(self):
            return []

        def get_command_injections(self):
            return []

        def get_path_traversals(self):
            return []

        def summary(self):
            return "summary"

    original_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name.endswith("symbolic_execution_tools"):
            # Pretend symbolic tools are present and return fake analyzer module
            module = SimpleNamespace(analyze_security=lambda code: FakeResult())
            return module
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    result = scalpel.analyze_security("print('hello')")

    assert result["has_vulnerabilities"] is True
    assert result["vulnerability_count"] == 1
    assert result["risk_level"] == "medium"
    assert result["sql_injections"] == 1


def test_analyze_symbolic_import_error(monkeypatch):
    """analyze_symbolic returns import error payload when SymbolicAnalyzer missing."""

    scalpel = CrewAIScalpel()

    original_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name.endswith("symbolic_execution_tools"):
            raise ImportError("Symbolic tools missing")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    result = scalpel.analyze_symbolic("x = 1")

    assert result["success"] is False
    assert "Symbolic execution tools not available" in result["error"]


def test_recommendations_and_risk_levels():
    """Check security recommendation helpers and risk calculation."""

    scalpel = CrewAIScalpel()

    issues = [
        {"type": "dangerous_function", "function": "eval"},
        {"type": "sql_injection"},
    ]

    recs = scalpel._get_security_recommendations(issues)
    risk = scalpel._calculate_risk_level(issues)
    suggestions = scalpel._generate_suggestions({"deep_nesting": [1]}, issues)

    assert any("ast.literal_eval" in rec for rec in recs)
    assert risk == "high"
    assert any("Reduce nesting depth" in s for s in suggestions)


def test_init_import_fallback(monkeypatch):
    """Cover ASTAnalyzer import fallback path in __init__."""

    import sys
    import types

    counter = {"n": 0}
    original_import = builtins.__import__

    stub_module = types.ModuleType("ast_tools.analyzer")

    class DummyAnalyzer:
        def __init__(self, cache_enabled=True):
            self.cache_enabled = cache_enabled

        def parse_to_ast(self, code):  # pragma: no cover - simple stub
            return None

        def analyze_code_style(self, tree):
            return {}

        def find_security_issues(self, tree):
            return []

        def ast_to_code(self, tree):
            return ""

    stub_module.ASTAnalyzer = DummyAnalyzer
    sys.modules["ast_tools"] = types.ModuleType("ast_tools")
    sys.modules["ast_tools.analyzer"] = stub_module

    def fake_import(name, *args, **kwargs):
        if name.endswith("code_scalpel.ast_tools.analyzer"):
            counter["n"] += 1
            raise ImportError("force fallback")
        if name == "ast_tools.analyzer":
            counter["n"] += 1
            # On first attempt for ast_tools.analyzer, succeed (not fail twice)
            return stub_module
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    scalpel = CrewAIScalpel()

    assert isinstance(scalpel.analyzer, DummyAnalyzer)
    assert scalpel._cache_enabled is True


def test_analyze_symbolic_success(monkeypatch):
    """Cover analyze_symbolic success path with paths info."""

    scalpel = CrewAIScalpel()

    class FakePath:
        def __init__(self):
            self.is_feasible = True
            self.variables = {"x": 1}

    class FakeResult:
        total_paths = 1
        feasible_count = 1
        infeasible_count = 0
        all_variables = {"x": 1}

        def __init__(self):
            self.paths = [FakePath()]

    import code_scalpel.symbolic_execution_tools as sym_tools

    monkeypatch.setattr(
        sym_tools,
        "SymbolicAnalyzer",
        lambda: SimpleNamespace(analyze=lambda code: FakeResult()),
    )

    result = scalpel.analyze_symbolic("x = 1")

    assert result["success"] is True
    assert result["feasible_paths"] == 1
    assert result["paths"][0]["variables"]["x"] == "1"


def test_analyze_security_ast_fallback(monkeypatch):
    """Cover analyze_security AST fallback path when symbolic tools missing."""

    scalpel = CrewAIScalpel()
    # [20260104_BUGFIX] Preserve original __import__ to avoid recursive calls.
    original_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name.endswith("symbolic_execution_tools"):
            raise ImportError("missing")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    scalpel.analyzer = SimpleNamespace(
        parse_to_ast=lambda code: "tree",
        find_security_issues=lambda tree: [{"type": "dangerous_function", "function": "eval"}],
    )

    result = scalpel.analyze_security("print('x')")

    assert result["success"] is True
    assert result["risk_level"] == "medium"
    assert result["analyzer"] == "ast-based (fallback)"
