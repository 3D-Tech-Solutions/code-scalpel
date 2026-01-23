"""Additional CLI coverage tests.

[20251215_TEST] Add CLI branch coverage for MCP, JS analysis, and security scan.
"""

import json
import sys

from code_scalpel import cli


def test_analyze_file_unknown_extension(monkeypatch, tmp_path, capsys):
    """Exercise analyze_file fallback language selection."""

    file_path = tmp_path / "sample.txt"
    file_path.write_text("print('hello')", encoding="utf-8")

    call_args = {}

    def fake_analyze_code(code, output_format, source, language):
        call_args.update(
            {
                "code": code,
                "output_format": output_format,
                "source": source,
                "language": language,
            }
        )
        return 0

    monkeypatch.setattr(cli, "analyze_code", fake_analyze_code)

    exit_code = cli.analyze_file(str(file_path))
    captured = capsys.readouterr()

    assert exit_code == 0
    assert call_args["language"] == "python"  # Unknown extension falls back to python
    assert "Warning: Unknown extension" in captured.err


def test_analyze_code_text_with_stub(monkeypatch, capsys):
    """Cover analyze_code text output using a lightweight analyzer stub."""

    class FakeMetrics:
        lines_of_code = 1
        num_functions = 0
        num_classes = 0
        cyclomatic_complexity = 1
        analysis_time_seconds = 0.01

    class FakeResult:
        metrics = FakeMetrics()
        dead_code = []
        security_issues = []
        refactor_suggestions = []
        errors = []

    class FakeAnalyzer:
        def __init__(self, level):
            self.level = level

        def analyze(self, code):
            return FakeResult()

    monkeypatch.setattr(cli, "CodeAnalyzer", FakeAnalyzer, raising=False)

    exit_code = cli.analyze_code("x = 1", output_format="text", source="sample.py")
    out = capsys.readouterr().out

    assert exit_code == 0
    assert "Lines of code" in out
    assert "Cyclomatic complexity" in out


def test_analyze_javascript_json(monkeypatch, capsys):
    """Ensure JavaScript analysis JSON branch serializes paths."""

    class FakeStatus:
        value = "ok"

    class FakePath:
        def __init__(self, idx):
            self.path_id = idx
            self.status = FakeStatus()
            self.model = {"x": idx}

    class FakeResult:
        def __init__(self):
            self.paths = [FakePath(1)]
            self.feasible_count = 1
            self.infeasible_count = 0

        def get_feasible_paths(self):
            return self.paths

    class FakeAnalyzer:
        def analyze(self, code, language="javascript"):
            return FakeResult()

    import code_scalpel.symbolic_execution_tools as sym_tools

    monkeypatch.setattr(sym_tools, "SymbolicAnalyzer", FakeAnalyzer, raising=False)

    exit_code = cli._analyze_javascript("code", output_format="json", source="file.js")
    data = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert data["language"] == "javascript"
    assert data["feasible_count"] == 1
    assert data["paths"][0]["status"] == "ok"


def test_scan_code_security_json(monkeypatch, capsys):
    """Cover scan_code_security JSON serialization with fake result."""

    class FakeEnum:
        def __init__(self, name):
            self.name = name

    class FakeVulnerability:
        def __init__(self):
            self.vulnerability_type = "SQL Injection"
            self.cwe_id = "CWE-89"
            self.taint_source = FakeEnum("user_input")
            self.sink_type = FakeEnum("execute")
            self.sink_location = (10,)
            self.taint_path = ["user_input", "query"]

    class FakeResult:
        has_vulnerabilities = True
        vulnerability_count = 1
        vulnerabilities = [FakeVulnerability()]

    import code_scalpel.symbolic_execution_tools as security_tools

    monkeypatch.setattr(security_tools, "analyze_security", lambda code: FakeResult())

    exit_code = cli.scan_code_security("print('x')", output_format="json")
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 2
    assert payload["has_vulnerabilities"] is True
    assert payload["vulnerabilities"][0]["cwe"] == "CWE-89"


def test_scan_security_text_branches(monkeypatch, tmp_path, capsys):
    """Exercise scan_security text output for vuln and non-vuln cases."""

    class FakeEnum:
        def __init__(self, name):
            self.name = name

    class FakeVulnerability:
        vulnerability_type = "XSS"
        cwe_id = "CWE-79"
        taint_source = FakeEnum("req")
        sink_type = FakeEnum("render")
        sink_location = (5,)
        taint_path = ["req", "render"]

    class FakeResult:
        def __init__(self, has_vulns):
            self.has_vulnerabilities = has_vulns
            self.vulnerability_count = 1 if has_vulns else 0
            self.vulnerabilities = [FakeVulnerability()] if has_vulns else []

        def summary(self):
            return "summary"

    file_path = tmp_path / "vuln.py"
    file_path.write_text("print('hi')", encoding="utf-8")

    import code_scalpel.symbolic_execution_tools as security_tools

    # First run: vulnerabilities present
    monkeypatch.setattr(security_tools, "analyze_security", lambda code: FakeResult(True))
    exit_code_vuln = cli.scan_security(str(file_path), output_format="text")
    out_vuln = capsys.readouterr().out

    # Second run: no vulnerabilities
    monkeypatch.setattr(security_tools, "analyze_security", lambda code: FakeResult(False))
    exit_code_clean = cli.scan_security(str(file_path), output_format="text")
    out_clean = capsys.readouterr().out

    assert exit_code_vuln == 2
    assert "Found 1 vulnerability" in out_vuln
    assert exit_code_clean == 0
    assert "No vulnerabilities detected" in out_clean


def test_start_mcp_server_http_keyboard_interrupt(monkeypatch, capsys, tmp_path):
    """Cover HTTP branch and KeyboardInterrupt handling in start_mcp_server."""

    import code_scalpel.mcp.server as mcp_server

    def _boom(**kwargs):  # noqa: ANN001
        raise KeyboardInterrupt()

    monkeypatch.setattr(mcp_server, "run_server", _boom)

    exit_code = cli.start_mcp_server(
        transport="sse",
        host="127.0.0.1",
        port=9100,
        allow_lan=True,
        root_path=str(tmp_path),
    )

    out = capsys.readouterr().out

    assert exit_code == 0
    assert "HTTP transport" in out
    assert "LAN access: ENABLED" in out


def test_start_server_keyboard_interrupt(monkeypatch, capsys):
    """Ensure start_server handles KeyboardInterrupt gracefully."""

    import code_scalpel.integrations.rest_api_server as rest_server

    def _boom(**kwargs):  # noqa: ANN001
        raise KeyboardInterrupt()

    monkeypatch.setattr(rest_server, "run_server", _boom)

    exit_code = cli.start_server(host="localhost", port=5055)
    out = capsys.readouterr().out

    assert exit_code == 0
    assert "REST API Server" in out


def test_main_mcp_allows_lan(monkeypatch):
    """Verify mcp command adjusts host when allow-lan is set."""

    captured = {}

    def fake_start_mcp_server(transport, host, port, allow_lan, root_path, tier=None):
        captured.update(
            {
                "transport": transport,
                "host": host,
                "port": port,
                "allow_lan": allow_lan,
                "root_path": root_path,
                "tier": tier,
            }
        )
        return 0

    monkeypatch.setattr(cli, "start_mcp_server", fake_start_mcp_server)
    monkeypatch.setattr(
        sys,
        "argv",
        ["prog", "mcp", "--allow-lan", "--port", "9999", "--host", "127.0.0.1"],
    )

    exit_code = cli.main()

    assert exit_code == 0
    assert captured["host"] == "127.0.0.1"
    assert captured["allow_lan"] is True
    assert captured["transport"] == "stdio"


# [20251214_TEST] Cover CLI failure paths for analyze and scan helpers.
def test_analyze_file_missing_path(capsys):
    exit_code = cli.analyze_file("/nonexistent/path.py")
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "File not found" in captured.err


def test_analyze_code_handles_analyzer_exceptions(monkeypatch, capsys):
    class _Boom:
        def analyze(self, code):
            raise RuntimeError("kaboom")

    import code_scalpel.code_analyzer as code_analyzer

    monkeypatch.setattr(code_analyzer, "CodeAnalyzer", lambda level=None: _Boom())

    exit_code = cli.analyze_code("print('x')")
    assert exit_code == 1
    assert "Error analyzing code" in capsys.readouterr().err


def test_scan_code_security_handles_exceptions(monkeypatch, capsys):
    import code_scalpel.symbolic_execution_tools as security_tools

    def _raise(_code):
        raise RuntimeError("fail")

    monkeypatch.setattr(security_tools, "analyze_security", _raise)

    exit_code = cli.scan_code_security("print('hi')")
    assert exit_code == 1
    assert "Error during security analysis" in capsys.readouterr().err


# [20251214_TEST] Cover CLI main dispatch branches without launching servers.
def test_main_no_command_shows_help(monkeypatch, capsys):
    monkeypatch.setattr(cli.sys, "argv", ["code-scalpel"])
    result = cli.main()
    out = capsys.readouterr().out

    assert result == 0
    assert "code-scalpel" in out


def test_main_version(monkeypatch, capsys):
    monkeypatch.setattr(cli.sys, "argv", ["code-scalpel", "version"])
    result = cli.main()
    out = capsys.readouterr().out

    assert result == 0
    assert "Code Scalpel" in out


def test_main_mcp_http_allow_lan(monkeypatch):
    called = {}

    def _stub(transport, host, port, allow_lan, root_path, tier=None):  # noqa: ANN001
        called.update(
            {
                "transport": transport,
                "host": host,
                "port": port,
                "allow_lan": allow_lan,
                "root_path": root_path,
                "tier": tier,
            }
        )
        return 0

    monkeypatch.setattr(cli, "start_mcp_server", _stub)
    monkeypatch.setattr(
        cli.sys,
        "argv",
        [
            "code-scalpel",
            "mcp",
            "--http",
            "--allow-lan",
            "--port",
            "9000",
            "--host",
            "127.0.0.1",
        ],
    )

    result = cli.main()

    assert result == 0
    assert called["transport"] == "sse"
    assert called["host"] == "127.0.0.1"
    assert called["port"] == 9000
    assert called["allow_lan"] is True


def test_main_server_dispatch(monkeypatch):
    called = {}

    def _server(host, port):  # noqa: ANN001
        called["host"] = host
        called["port"] = port
        return 0

    monkeypatch.setattr(cli, "start_server", _server)
    monkeypatch.setattr(cli.sys, "argv", ["code-scalpel", "server", "--port", "5050"])

    result = cli.main()

    assert result == 0
    assert called["host"] == "127.0.0.1"
    assert called["port"] == 5050


def test_main_scan_code_dispatch(monkeypatch):
    def _scan(code, output_format):  # noqa: ANN001
        assert output_format == "json"
        return 0

    monkeypatch.setattr(cli, "scan_code_security", _scan)
    monkeypatch.setattr(cli.sys, "argv", ["code-scalpel", "scan", "--code", "print('x')", "--json"])

    result = cli.main()
    assert result == 0
