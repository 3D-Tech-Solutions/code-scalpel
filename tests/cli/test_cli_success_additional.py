import json

import pytest

import code_scalpel.cli as cli


@pytest.fixture
def dummy_analysis_result():
    metrics = type(
        "Metrics",
        (),
        {
            "lines_of_code": 10,
            "num_functions": 1,
            "num_classes": 0,
            "cyclomatic_complexity": 2,
            "analysis_time_seconds": 0.01,
        },
    )
    return type(
        "Result",
        (),
        {
            "metrics": metrics,
            "dead_code": [],
            "security_issues": [],
            "refactor_suggestions": [],
            "errors": [],
        },
    )()


def test_analyze_code_json_output(monkeypatch, capsys, dummy_analysis_result):
    # [20251214_TEST] Exercise analyze_code happy path with JSON output
    import sys
    import types

    dummy_module = types.ModuleType("code_scalpel.code_analyzer")

    class DummyAnalyzer:
        def __init__(self, *_, **__):
            pass

        def analyze(self, code):
            return dummy_analysis_result

    dummy_module.CodeAnalyzer = DummyAnalyzer
    dummy_module.AnalysisLevel = type("AL", (), {"STANDARD": "std"})

    monkeypatch.setitem(sys.modules, "code_scalpel.code_analyzer", dummy_module)

    exit_code = cli.analyze_code("print(1)", output_format="json", source="src.py")

    captured = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert captured["source"] == "src.py"
    assert captured["metrics"]["lines_of_code"] == 10


def test_scan_code_security_success(monkeypatch, capsys):
    # [20251214_TEST] Ensure scan_code_security returns 0 on clean result
    import sys
    import types

    result = type(
        "SecResult",
        (),
        {
            "has_vulnerabilities": False,
            "vulnerability_count": 0,
            "vulnerabilities": [],
            "summary": lambda self=None: "OK",
        },
    )()

    dummy_module = types.ModuleType("code_scalpel.symbolic_execution_tools")

    def fake_analyze_security(code):
        return result

    dummy_module.analyze_security = fake_analyze_security
    # [20251214_TEST] Route cli.scan_code_security import to stubbed analyzer
    monkeypatch.setitem(sys.modules, "code_scalpel.symbolic_execution_tools", dummy_module)

    exit_code = cli.scan_code_security("print('ok')", output_format="text")

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "No vulnerabilities" in output


def test_start_mcp_server_uses_http_alias(monkeypatch):
    # [20251214_TEST] Verify start_mcp_server wiring without launching server
    import sys
    import types

    called = {}

    dummy_module = types.ModuleType("code_scalpel.mcp.server")

    def fake_run_server(**kwargs):
        called.update(kwargs)

    dummy_module.run_server = fake_run_server
    # [20251214_TEST] Ensure cli.start_mcp_server imports stubbed MCP server
    monkeypatch.setitem(sys.modules, "code_scalpel.mcp.server", dummy_module)

    result = cli.start_mcp_server(
        transport="stdio",
        host="127.0.0.1",
        port=1234,
        allow_lan=True,
        root_path="/root",
    )

    assert called["allow_lan"] is True
    assert called["root_path"] == "/root"
    assert result == 0
