import sys
import types

import code_scalpel.cli as cli

# [20251214_REFACTOR] Drop unused imports flagged by ruff.


# [20260118_TEST] Verify analyze_file handles missing path gracefully.
def test_analyze_file_missing(tmp_path, capsys):
    missing = tmp_path / "nope.py"
    exit_code = cli.analyze_file(str(missing))
    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Error: File not found" in captured.err


# [20260118_TEST] Ensure analyze_file defaults to python for unknown extensions and invokes analyzer.
def test_analyze_file_defaults_language(monkeypatch, tmp_path):
    target = tmp_path / "snippet.txt"
    target.write_text("x = 1", encoding="utf-8")

    called = {}

    def fake_analyze(code: str, output_format: str, filepath: str, language: str) -> int:
        called.update(
            {
                "code": code,
                "output_format": output_format,
                "filepath": filepath,
                "language": language,
            }
        )
        return 0

    monkeypatch.setattr(cli, "analyze_code", fake_analyze)

    exit_code = cli.analyze_file(str(target))
    assert exit_code == 0
    assert called["language"] == "python"
    assert called["filepath"] == str(target)


# [20260118_TEST] Cover JavaScript analysis path with JSON output.
def test_analyze_code_javascript_json(monkeypatch, capsys):
    class DummyStatus:
        def __init__(self, value: str):
            self.value = value

    class DummyPath:
        def __init__(self, path_id: int):
            self.path_id = path_id
            self.status = DummyStatus("sat")
            self.model = {"x": 1}

    class DummyResult:
        def __init__(self):
            self.paths = [DummyPath(1)]
            self.feasible_count = 1
            self.infeasible_count = 0

        def get_feasible_paths(self):
            return self.paths

    class DummyAnalyzer:
        def analyze(self, code: str, language: str = None):
            assert language == "javascript"
            return DummyResult()

    dummy_module = types.SimpleNamespace(SymbolicAnalyzer=DummyAnalyzer)
    monkeypatch.setitem(sys.modules, "code_scalpel.symbolic_execution_tools", dummy_module)

    exit_code = cli.analyze_code("let x = 1;", output_format="json", source="sample.js", language="javascript")
    out = capsys.readouterr().out
    assert exit_code == 0
    assert '"language": "javascript"' in out
    assert '"feasible_count": 1' in out


# [20260118_TEST] Cover Java analysis path with text output.
def test_analyze_code_java_text(monkeypatch, capsys):
    class DummyStatus:
        def __init__(self, value: str):
            self.value = value

    class DummyPath:
        def __init__(self, path_id: int):
            self.path_id = path_id
            self.status = DummyStatus("sat")
            self.model = None

    class DummyResult:
        def __init__(self):
            self.paths = [DummyPath(2)]
            self.feasible_count = 1
            self.infeasible_count = 0

        def get_feasible_paths(self):
            return self.paths

    class DummyAnalyzer:
        def analyze(self, code: str, language: str = None):
            assert language == "java"
            return DummyResult()

    dummy_module = types.SimpleNamespace(SymbolicAnalyzer=DummyAnalyzer)
    monkeypatch.setitem(sys.modules, "code_scalpel.symbolic_execution_tools", dummy_module)

    exit_code = cli.analyze_code("class Demo {}", output_format="text", source="Demo.java", language="java")
    captured = capsys.readouterr().out
    assert exit_code == 0
    assert "Code Scalpel Analysis (Java): Demo.java" in captured
