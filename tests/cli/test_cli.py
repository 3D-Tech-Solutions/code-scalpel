"""
Tests for the CLI module.

These tests verify that the command-line interface works correctly.
Goal: Get cli.py from 0% to at least 50% coverage.
"""

import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

# [20251215_TEST] Ensure CLI subprocess invocations can import code_scalpel without editable install
_project_root = Path(__file__).resolve().parents[2]
os.environ["PYTHONPATH"] = os.pathsep.join([str(_project_root / "src"), os.environ.get("PYTHONPATH", "")]).rstrip(
    os.pathsep
)


class TestCLIBasics:
    """Test basic CLI functionality."""

    def test_help_command(self):
        """Test that --help works and shows expected content."""
        result = subprocess.run(
            [sys.executable, "-m", "code_scalpel.cli", "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "code-scalpel" in result.stdout.lower() or "usage" in result.stdout.lower()
        assert "analyze" in result.stdout
        assert "server" in result.stdout
        assert "version" in result.stdout

    def test_version_command(self):
        """Test that version command works."""
        result = subprocess.run(
            [sys.executable, "-m", "code_scalpel.cli", "version"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "0.1.0" in result.stdout or "Code Scalpel" in result.stdout

    def test_analyze_help(self):
        """Test that analyze --help works."""
        result = subprocess.run(
            [sys.executable, "-m", "code_scalpel.cli", "analyze", "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "--code" in result.stdout or "code" in result.stdout.lower()


class TestCLIAnalyze:
    """Test the analyze command."""

    def test_analyze_inline_code(self):
        """Test analyzing inline code with --code flag."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "code_scalpel.cli",
                "analyze",
                "--code",
                "def hello(): return 42",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "Metrics" in result.stdout or "analysis" in result.stdout.lower()

    def test_analyze_inline_code_json(self):
        """Test analyzing inline code with JSON output."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "code_scalpel.cli",
                "analyze",
                "--code",
                "x = 1",
                "--json",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        # JSON output should be parseable
        import json

        try:
            data = json.loads(result.stdout)
            assert "success" in data or "metrics" in data or isinstance(data, dict)
        except json.JSONDecodeError:
            # Might have logging output before JSON
            lines = result.stdout.strip().split("\n")
            for line in lines:
                try:
                    data = json.loads(line)
                    assert isinstance(data, dict)
                    break
                except json.JSONDecodeError:
                    continue

    def test_analyze_file(self, tmp_path):
        """Test analyzing a Python file."""
        # Create a temporary Python file
        test_file = tmp_path / "test_sample.py"
        test_file.write_text("def greet(name):\n    return f'Hello, {name}!'\n")

        result = subprocess.run(
            [sys.executable, "-m", "code_scalpel.cli", "analyze", str(test_file)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0

    def test_analyze_nonexistent_file(self):
        """Test analyzing a file that doesn't exist."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "code_scalpel.cli",
                "analyze",
                "/nonexistent/file.py",
            ],
            capture_output=True,
            text=True,
        )
        # Should fail gracefully
        assert result.returncode != 0 or "error" in result.stderr.lower() or "not found" in result.stdout.lower()

    def test_analyze_syntax_error_code(self):
        """Test analyzing code with syntax errors."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "code_scalpel.cli",
                "analyze",
                "--code",
                "def broken(",
            ],
            capture_output=True,
            text=True,
        )
        # Should handle gracefully, not crash
        # May return 0 with error message or non-zero
        combined = result.stdout + result.stderr
        assert result.returncode != 0 or "error" in combined.lower() or "syntax" in combined.lower()


class TestCLIServer:
    """Test the server command."""

    def test_server_help(self):
        """Test that server --help works."""
        result = subprocess.run(
            [sys.executable, "-m", "code_scalpel.cli", "server", "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "--port" in result.stdout or "port" in result.stdout.lower()


class TestCLIEdgeCases:
    """Test edge cases and error handling."""

    def test_unknown_command(self):
        """Test that unknown commands are handled."""
        result = subprocess.run(
            [sys.executable, "-m", "code_scalpel.cli", "unknowncommand"],
            capture_output=True,
            text=True,
        )
        # Should fail with usage info
        assert result.returncode != 0

    def test_analyze_no_input(self):
        """Test analyze without any input."""
        result = subprocess.run(
            [sys.executable, "-m", "code_scalpel.cli", "analyze"],
            capture_output=True,
            text=True,
        )
        # Should show error or usage
        combined = result.stdout + result.stderr
        assert result.returncode != 0 or "error" in combined.lower() or "usage" in combined.lower()


class TestCLILicenseInstall:
    def test_license_install_writes_dest(self, tmp_path):
        """`code-scalpel license install` validates then installs a license."""
        from code_scalpel.licensing.jwt_generator import generate_license

        token = generate_license(
            tier="pro",
            customer_id="user@example.com",
            duration_days=365,
            algorithm="HS256",
            secret_key="test_secret_key_12345",
        )

        src = tmp_path / "license.jwt"
        src.write_text(token)
        dest = tmp_path / "installed.jwt"

        env = os.environ.copy()
        env["CODE_SCALPEL_ALLOW_HS256"] = "1"
        env["CODE_SCALPEL_SECRET_KEY"] = "test_secret_key_12345"

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "code_scalpel.cli",
                "license",
                "install",
                str(src),
                "--dest",
                str(dest),
            ],
            capture_output=True,
            text=True,
            env=env,
        )

        assert result.returncode == 0, result.stderr
        assert dest.exists()
        assert "Installed to" in result.stdout

    def test_license_install_requires_force_if_exists(self, tmp_path):
        from code_scalpel.licensing.jwt_generator import generate_license

        token = generate_license(
            tier="pro",
            customer_id="user@example.com",
            duration_days=365,
            algorithm="HS256",
            secret_key="test_secret_key_12345",
        )

        src = tmp_path / "license.jwt"
        src.write_text(token)
        dest = tmp_path / "installed.jwt"
        dest.write_text("already")

        env = os.environ.copy()
        env["CODE_SCALPEL_ALLOW_HS256"] = "1"
        env["CODE_SCALPEL_SECRET_KEY"] = "test_secret_key_12345"

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "code_scalpel.cli",
                "license",
                "install",
                str(src),
                "--dest",
                str(dest),
            ],
            capture_output=True,
            text=True,
            env=env,
        )

        assert result.returncode == 1
        combined = (result.stdout + result.stderr).lower()
        assert "destination already exists" in combined


# [20251214_TEST] In-process coverage for cli helpers without subprocess overhead.
class TestCLIInProcess:
    def test_analyze_file_defaults_to_python_for_unknown_extension(self, tmp_path, monkeypatch):
        from code_scalpel import cli

        test_file = tmp_path / "sample.unknown"
        test_file.write_text("x = 1")

        captured = {}

        def fake_analyze_code(code: str, output_format: str, source: str, language: str):
            captured["code"] = code
            captured["source"] = source
            captured["language"] = language
            return 0

        monkeypatch.setattr(cli, "analyze_code", fake_analyze_code)

        exit_code = cli.analyze_file(str(test_file), output_format="json", language=None)

        assert exit_code == 0
        assert captured["language"] == "python"

    def test_analyze_file_missing_returns_error(self, tmp_path):
        from code_scalpel import cli

        missing = tmp_path / "does_not_exist.py"
        exit_code = cli.analyze_file(str(missing))
        assert exit_code == 1

    # [20251214_TEST] Ensure explicit language bypasses auto-detect branch.
    def test_analyze_file_respects_explicit_language(self, tmp_path, monkeypatch):
        from code_scalpel import cli

        target = tmp_path / "explicit.src"
        target.write_text("x = 1")

        captured = {}

        def fake_analyze_code(code: str, output_format: str, source: str, language: str):
            captured["language"] = language
            return 0

        monkeypatch.setattr(cli, "analyze_code", fake_analyze_code)

        exit_code = cli.analyze_file(str(target), output_format="text", language="java")

        assert exit_code == 0
        assert captured["language"] == "java"

    # [20251214_TEST] Exercise .js and .java extension paths in auto-detection.
    def test_analyze_file_detects_js_and_java_extensions(self, tmp_path, monkeypatch):
        from code_scalpel import cli

        languages_seen = []

        def fake_analyze_code(code: str, output_format: str, source: str, language: str):
            languages_seen.append(language)
            return 0

        monkeypatch.setattr(cli, "analyze_code", fake_analyze_code)

        js_file = tmp_path / "script.js"
        js_file.write_text("console.log('hi')")

        java_file = tmp_path / "Main.java"
        java_file.write_text("class Main {}")

        assert cli.analyze_file(str(js_file), output_format="text", language=None) == 0
        assert cli.analyze_file(str(java_file), output_format="text", language=None) == 0

        assert languages_seen == ["javascript", "java"]

    # [20251214_TEST] Capture read failures to cover error branch in analyze_file.
    def test_analyze_file_read_error_returns_failure(self, tmp_path, monkeypatch):
        from pathlib import Path

        from code_scalpel import cli

        target = tmp_path / "bad.py"
        target.write_text("print('hi')")

        def boom(self, *args, **kwargs):
            raise OSError("boom")

        monkeypatch.setattr(Path, "read_text", boom)

        # Analyze code should not be invoked when read fails; would raise if called.
        monkeypatch.setattr(cli, "analyze_code", lambda *a, **k: 999)

        exit_code = cli.analyze_file(str(target), output_format="text", language=None)

        assert exit_code == 1

    def test_analyze_code_json_uses_analyzer(self, capsys, monkeypatch):
        import sys
        from types import SimpleNamespace

        from code_scalpel import cli

        class DummyMetrics:
            lines_of_code = 1
            num_functions = 0
            num_classes = 0
            cyclomatic_complexity = 0
            analysis_time_seconds = 0.01

        class DummyResult:
            metrics = DummyMetrics()
            dead_code = []
            security_issues = []
            refactor_suggestions = []
            errors = []

        class DummyAnalyzer:
            def __init__(self, level):
                self.level = level

            def analyze(self, code: str):
                return DummyResult()

        dummy_module = SimpleNamespace(
            CodeAnalyzer=DummyAnalyzer,
            AnalysisLevel=SimpleNamespace(STANDARD="STANDARD"),
        )
        monkeypatch.setitem(sys.modules, "code_scalpel.code_analyzer", dummy_module)

        exit_code = cli.analyze_code("x = 1", output_format="json", source="inline", language="python")
        captured = capsys.readouterr().out

        assert exit_code == 0
        assert "lines_of_code" in captured

    # [20251214_TEST] Verify language dispatch to JavaScript helper from analyze_code.
    def test_analyze_code_dispatches_javascript_helper(self, monkeypatch):
        from code_scalpel import cli

        called = {}
        monkeypatch.setattr(
            cli,
            "_analyze_javascript",
            lambda code, output_format, source: called.update(code=code, output=output_format, source=source) or 0,
        )

        exit_code = cli.analyze_code(
            "console.log('hi')",
            output_format="text",
            source="inline",
            language="javascript",
        )

        assert exit_code == 0
        assert called == {
            "code": "console.log('hi')",
            "output": "text",
            "source": "inline",
        }

    # [20251214_TEST] Verify language dispatch to Java helper from analyze_code.
    def test_analyze_code_dispatches_java_helper(self, monkeypatch):
        from code_scalpel import cli

        called = {}
        monkeypatch.setattr(
            cli,
            "_analyze_java",
            lambda code, output_format, source: called.update(code=code, output=output_format, source=source) or 0,
        )

        exit_code = cli.analyze_code("class Main {}", output_format="json", source="inline", language="java")

        assert exit_code == 0
        assert called == {"code": "class Main {}", "output": "json", "source": "inline"}

    # [20251214_TEST] Exercise security_issues text branch in analyze_code output.
    def test_analyze_code_text_reports_security_issues(self, capsys, monkeypatch):
        import sys
        from types import SimpleNamespace

        from code_scalpel import cli

        class DummyMetrics:
            lines_of_code = 1
            num_functions = 0
            num_classes = 0
            cyclomatic_complexity = 0
            analysis_time_seconds = 0.01

        class DummyResult:
            metrics = DummyMetrics()
            dead_code = []
            security_issues = [{"type": "SQL Injection", "description": "unescaped input"}]
            refactor_suggestions = []
            errors = []

        class DummyAnalyzer:
            def __init__(self, level):
                self.level = level

            def analyze(self, code: str):
                return DummyResult()

        dummy_module = SimpleNamespace(
            CodeAnalyzer=DummyAnalyzer,
            AnalysisLevel=SimpleNamespace(STANDARD="STANDARD"),
        )
        monkeypatch.setitem(sys.modules, "code_scalpel.code_analyzer", dummy_module)

        exit_code = cli.analyze_code("print('hi')", output_format="text", source="inline", language="python")
        captured = capsys.readouterr().out

        assert exit_code == 0
        assert "Security Issues" in captured

    def test_analyze_javascript_reports_paths(self, capsys, monkeypatch):
        from types import SimpleNamespace

        import code_scalpel.symbolic_execution_tools as symbolic_tools
        from code_scalpel import cli

        class DummyPath:
            def __init__(self):
                self.path_id = 1
                self.status = SimpleNamespace(value="feasible")
                self.model = {"x": 1}

        class DummyResult:
            paths = [DummyPath()]
            feasible_count = 1
            infeasible_count = 0

            def get_feasible_paths(self):
                return self.paths

        class DummyAnalyzer:
            def analyze(self, code: str, language: str):  # noqa: D401 - simple stub
                return DummyResult()

        monkeypatch.setattr(symbolic_tools, "SymbolicAnalyzer", lambda: DummyAnalyzer())

        exit_code = cli._analyze_javascript("code", output_format="json", source="inline")
        captured = capsys.readouterr().out

        assert exit_code == 0
        assert "feasible_count" in captured

    # [20251214_TEST] Cover text output branch for JavaScript analysis.
    def test_analyze_javascript_text_output(self, capsys, monkeypatch):
        from types import SimpleNamespace

        import code_scalpel.symbolic_execution_tools as symbolic_tools
        from code_scalpel import cli

        class DummyPath:
            def __init__(self, path_id: int, model):
                self.path_id = path_id
                self.status = SimpleNamespace(value="ok")
                self.model = model

        class DummyResult:
            paths = [DummyPath(3, None), DummyPath(4, {"a": 1})]
            feasible_count = 2
            infeasible_count = 0

            def get_feasible_paths(self):
                return self.paths

        class DummyAnalyzer:
            def analyze(self, code: str, language: str):
                return DummyResult()

        monkeypatch.setattr(symbolic_tools, "SymbolicAnalyzer", lambda: DummyAnalyzer())

        exit_code = cli._analyze_javascript("code", output_format="text", source="inline")
        output = capsys.readouterr().out

        assert exit_code == 0
        assert "Feasible paths" in output

    # [20251214_TEST] Cover JavaScript analyzer exception handling.
    def test_analyze_javascript_handles_exception(self, capsys, monkeypatch):
        import code_scalpel.symbolic_execution_tools as symbolic_tools
        from code_scalpel import cli

        class DummyAnalyzer:
            def analyze(self, code: str, language: str):
                raise RuntimeError("fail")

        monkeypatch.setattr(symbolic_tools, "SymbolicAnalyzer", lambda: DummyAnalyzer())

        exit_code = cli._analyze_javascript("code", output_format="text", source="inline")
        output = capsys.readouterr().err

        assert exit_code == 1
        assert "Error analyzing JavaScript code" in output

    def test_analyze_non_python_file(self, tmp_path):
        """Test analyzing a non-Python file (should warn)."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Just some text content")

        result = subprocess.run(
            [sys.executable, "-m", "code_scalpel.cli", "analyze", str(test_file)],
            capture_output=True,
            text=True,
        )
        # Should still process but may warn
        combined = result.stdout + result.stderr
        assert "warning" in combined.lower() or result.returncode == 0

    def test_analyze_file_with_dead_code(self, tmp_path):
        """Test analyzing a file with dead code for detection."""
        test_file = tmp_path / "dead_code.py"
        test_file.write_text("""
def unused_function():
    return "never called"

def main():
    return 42
""")

        result = subprocess.run(
            [sys.executable, "-m", "code_scalpel.cli", "analyze", str(test_file)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        # Should show metrics at minimum
        assert "Metrics" in result.stdout or "lines" in result.stdout.lower()

    # [20251214_TEST] Additional in-process coverage for CLI helpers and error paths.
    def test_analyze_code_handles_analyzer_error(self, monkeypatch):
        import sys
        from types import SimpleNamespace

        from code_scalpel import cli

        class DummyAnalyzer:
            def __init__(self, level):
                self.level = level

            def analyze(self, code: str):
                raise RuntimeError("boom")

        dummy_module = SimpleNamespace(
            CodeAnalyzer=DummyAnalyzer,
            AnalysisLevel=SimpleNamespace(STANDARD="STANDARD"),
        )
        monkeypatch.setitem(sys.modules, "code_scalpel.code_analyzer", dummy_module)

        exit_code = cli.analyze_code("x = 1", output_format="text", source="inline", language="python")

        assert exit_code == 1

    def test_analyze_java_reports_paths(self, capsys, monkeypatch):
        from types import SimpleNamespace

        import code_scalpel.symbolic_execution_tools as symbolic_tools
        from code_scalpel import cli

        class DummyPath:
            def __init__(self):
                self.path_id = 2
                self.status = SimpleNamespace(value="ok")
                self.model = None

        class DummyResult:
            paths = [DummyPath()]
            feasible_count = 0
            infeasible_count = 0

            def get_feasible_paths(self):
                return self.paths

        class DummyAnalyzer:
            def analyze(self, code: str, language: str):
                return DummyResult()

        monkeypatch.setattr(symbolic_tools, "SymbolicAnalyzer", lambda: DummyAnalyzer())

        exit_code = cli._analyze_java("code", output_format="json", source="inline")
        captured = capsys.readouterr().out

        assert exit_code == 0
        assert "feasible_count" in captured

    # [20251214_TEST] Cover text output branch for Java analysis.
    def test_analyze_java_text_output(self, capsys, monkeypatch):
        from types import SimpleNamespace

        import code_scalpel.symbolic_execution_tools as symbolic_tools
        from code_scalpel import cli

        class DummyPath:
            def __init__(self, path_id: int, model):
                self.path_id = path_id
                self.status = SimpleNamespace(value="ok")
                self.model = model

        class DummyResult:
            paths = [DummyPath(4, None), DummyPath(5, {"b": 2})]
            feasible_count = 2
            infeasible_count = 0

            def get_feasible_paths(self):
                return self.paths

        class DummyAnalyzer:
            def analyze(self, code: str, language: str):
                return DummyResult()

        monkeypatch.setattr(symbolic_tools, "SymbolicAnalyzer", lambda: DummyAnalyzer())

        exit_code = cli._analyze_java("code", output_format="text", source="inline")
        output = capsys.readouterr().out

        assert exit_code == 0
        assert "Code Scalpel Analysis (Java)" in output

    # [20251214_TEST] Cover Java analyzer exception handling branch.
    def test_analyze_java_handles_exception(self, capsys, monkeypatch):
        import code_scalpel.symbolic_execution_tools as symbolic_tools
        from code_scalpel import cli

        class DummyAnalyzer:
            def analyze(self, code: str, language: str):
                raise RuntimeError("fail-java")

        monkeypatch.setattr(symbolic_tools, "SymbolicAnalyzer", lambda: DummyAnalyzer())

        exit_code = cli._analyze_java("code", output_format="text", source="inline")
        output = capsys.readouterr().err

        assert exit_code == 1
        assert "Error analyzing Java code" in output

    def test_scan_code_security_json_branch(self, capsys, monkeypatch):
        import sys
        from types import SimpleNamespace

        from code_scalpel import cli

        class DummyVuln:
            vulnerability_type = "SQL Injection"
            cwe_id = "CWE-89"
            taint_source = SimpleNamespace(name="request")
            sink_type = SimpleNamespace(name="execute")
            sink_location = (10,)
            taint_path = ["src", "sink"]

        class DummyResult:
            has_vulnerabilities = True
            vulnerability_count = 1
            vulnerabilities = [DummyVuln()]

        fake_module = SimpleNamespace(analyze_security=lambda code: DummyResult())
        monkeypatch.setitem(sys.modules, "code_scalpel.symbolic_execution_tools", fake_module)

        exit_code = cli.scan_code_security("print('hi')", output_format="json")
        captured = capsys.readouterr().out

        assert exit_code == 2
        assert "SQL Injection" in captured

    def test_scan_code_security_error_path(self, monkeypatch):
        import sys

        from code_scalpel import cli

        def explode(code: str):
            raise RuntimeError("scan-error")

        monkeypatch.setitem(
            sys.modules,
            "code_scalpel.symbolic_execution_tools",
            __import__("types").SimpleNamespace(analyze_security=explode),
        )

        exit_code = cli.scan_code_security("print('hi')", output_format="text")
        assert exit_code == 1

    def test_scan_security_missing_file_returns_error(self, tmp_path):
        from code_scalpel import cli

        missing = tmp_path / "nope.py"
        assert cli.scan_security(str(missing)) == 1

    def test_start_server_handles_keyboard_interrupt(self, monkeypatch):
        import sys
        from types import SimpleNamespace

        from code_scalpel import cli

        def fake_run_server(**kwargs):
            raise KeyboardInterrupt()

        monkeypatch.setitem(
            sys.modules,
            "code_scalpel.integrations.rest_api_server",
            SimpleNamespace(run_server=fake_run_server),
        )

        assert cli.start_server("127.0.0.1", 9000) == 0

    def test_start_mcp_server_http_and_lan(self, capsys, monkeypatch, tmp_path):
        import sys
        from types import SimpleNamespace

        from code_scalpel import cli

        captured = {}

        def fake_run_server(**kwargs):
            captured.update(kwargs)

        monkeypatch.setitem(
            sys.modules,
            "code_scalpel.mcp.server",
            SimpleNamespace(run_server=fake_run_server),
        )

        exit_code = cli.start_mcp_server(transport="sse", host="127.0.0.1", port=7777, allow_lan=True, root_path=None)
        output = capsys.readouterr().out

        assert exit_code == 0
        assert captured.get("allow_lan") is True
        assert "LAN access" in output

    # [20251214_TEST] Cover stdio transport path for MCP server startup.
    def test_start_mcp_server_stdio(self, capsys, monkeypatch):
        import sys
        from types import SimpleNamespace

        from code_scalpel import cli

        called = {}

        def fake_run_server(**kwargs):
            called.update(kwargs)

        monkeypatch.setitem(
            sys.modules,
            "code_scalpel.mcp.server",
            SimpleNamespace(run_server=fake_run_server),
        )

        exit_code = cli.start_mcp_server()
        output = capsys.readouterr().out

        assert exit_code == 0
        assert called.get("transport") == "stdio"
        assert "stdio transport" in output

    def test_analyze_file_json_output(self, tmp_path):
        """Test file analysis with JSON output."""
        test_file = tmp_path / "sample.py"
        test_file.write_text("x = 1\ny = 2\n")

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "code_scalpel.cli",
                "analyze",
                str(test_file),
                "--json",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0

        import json

        # Find JSON in output
        for line in result.stdout.strip().split("\n"):
            try:
                data = json.loads(line)
                if isinstance(data, dict):
                    assert "metrics" in data or "source" in data
                    break
            except json.JSONDecodeError:
                continue

    def test_analyze_complex_code(self, tmp_path):
        """Test analyzing more complex code with all features."""
        test_file = tmp_path / "complex.py"
        test_file.write_text("""
import os

class Calculator:
    def __init__(self):
        self.value = 0

    def add(self, x):
        self.value += x
        return self

    def get_value(self):
        return self.value

def risky_function():
    exec("print('danger')")  # Security issue
    return eval("1+1")

def main():
    calc = Calculator()
    calc.add(5).add(10)
    return calc.get_value()
""")

        result = subprocess.run(
            [sys.executable, "-m", "code_scalpel.cli", "analyze", str(test_file)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        # Should detect classes and functions
        assert "Classes" in result.stdout or "Functions" in result.stdout or "Metrics" in result.stdout


class TestCLIDirectImport:
    """Test CLI functions via direct import for better coverage."""

    def test_analyze_file_not_found(self):
        """Test analyze_file with nonexistent file."""
        from code_scalpel.cli import analyze_file

        result = analyze_file("/nonexistent/path/to/file.py")
        assert result == 1

    def test_analyze_file_non_py_extension(self, tmp_path, capsys):
        """Test analyze_file warns for non-.py files."""
        from code_scalpel.cli import analyze_file

        test_file = tmp_path / "test.txt"
        test_file.write_text("x = 1")

        analyze_file(str(test_file))
        captured = capsys.readouterr()
        assert "Warning" in captured.err

    def test_analyze_file_json_format(self, tmp_path, capsys):
        """Test analyze_file with JSON output format."""
        import json

        from code_scalpel.cli import analyze_file

        test_file = tmp_path / "test.py"
        test_file.write_text("def foo(): return 42")

        result = analyze_file(str(test_file), output_format="json")
        captured = capsys.readouterr()

        assert result == 0
        # Output should contain valid JSON
        output_lines = captured.out.strip().split("\n")
        found_json = False
        for line in output_lines:
            try:
                data = json.loads(line)
                if isinstance(data, dict):
                    found_json = True
                    break
            except json.JSONDecodeError:
                continue
        assert found_json or "source" in captured.out

    def test_analyze_code_json_format(self, capsys):
        """Test analyze_code with JSON output format."""
        import json

        from code_scalpel.cli import analyze_code

        result = analyze_code("x = 1", output_format="json")
        captured = capsys.readouterr()

        assert result == 0
        # Try to parse JSON from output
        output_lines = captured.out.strip().split("\n")
        for line in output_lines:
            try:
                data = json.loads(line)
                assert isinstance(data, dict)
                break
            except json.JSONDecodeError:
                continue

    def test_analyze_code_syntax_error(self, capsys):
        """Test analyze_code with code that has syntax error."""
        from code_scalpel.cli import analyze_code

        result = analyze_code("def broken(")
        captured = capsys.readouterr()

        # May succeed (with error in result) or fail
        captured.out + captured.err
        assert result in [0, 1]

    # [20251214_TEST] Exercise Java branch through direct helper to lift cli.py coverage.
    def test_analyze_java_json_reports_paths(self, capsys, monkeypatch):
        from types import SimpleNamespace

        from code_scalpel import cli

        class DummyPath:
            def __init__(self):
                self.path_id = 7
                self.status = SimpleNamespace(value="feasible")
                self.model = {"x": 2}

        class DummyResult:
            paths = [DummyPath()]
            feasible_count = 1
            infeasible_count = 0

            def get_feasible_paths(self):
                return self.paths

        class DummyAnalyzer:
            def analyze(self, code: str, language: str):  # noqa: D401 simple stub
                return DummyResult()

        monkeypatch.setitem(
            sys.modules,
            "code_scalpel.symbolic_execution_tools",
            SimpleNamespace(SymbolicAnalyzer=lambda: DummyAnalyzer()),
        )

        exit_code = cli._analyze_java("code", output_format="json", source="inline")
        captured = capsys.readouterr().out

        assert exit_code == 0
        assert "feasible_count" in captured

    # [20251214_TEST] Cover scan_security and scan_code_security without invoking real analyzer.
    def test_scan_security_json_output(self, tmp_path, capsys, monkeypatch):
        from code_scalpel import cli

        class DummyVulnerability:
            vulnerability_type = "SQLi"
            cwe_id = "CWE-89"
            taint_source = SimpleNamespace(name="user")
            sink_type = SimpleNamespace(name="execute")
            sink_location = (10,)
            taint_path = ["user", "execute"]

        class DummySecurityResult:
            has_vulnerabilities = True
            vulnerability_count = 1
            vulnerabilities = [DummyVulnerability()]

            def summary(self):  # noqa: D401 - test stub
                return "summary"

        monkeypatch.setitem(
            sys.modules,
            "code_scalpel.symbolic_execution_tools",
            SimpleNamespace(analyze_security=lambda code: DummySecurityResult()),
        )

        target = tmp_path / "vuln.py"
        target.write_text("print('hi')")

        exit_code = cli.scan_security(str(target), output_format="json")
        captured = capsys.readouterr().out

        assert exit_code == 2  # returns 2 when vulnerabilities found
        assert "vulnerabilities" in captured

    def test_scan_code_security_json_output(self, capsys, monkeypatch):
        from code_scalpel import cli

        class DummySecurityResult:
            has_vulnerabilities = False
            vulnerability_count = 0
            vulnerabilities = []

            def summary(self):
                return "ok"

        monkeypatch.setitem(
            sys.modules,
            "code_scalpel.symbolic_execution_tools",
            SimpleNamespace(analyze_security=lambda code: DummySecurityResult()),
        )

        exit_code = cli.scan_code_security("print('hi')", output_format="json")
        captured = capsys.readouterr().out

        assert exit_code == 0
        assert "has_vulnerabilities" in captured

    # [20251214_TEST] Cover start_server/start_mcp_server argument plumbing without real servers.
    def test_start_server_invokes_run_server(self, capsys, monkeypatch):
        from code_scalpel import cli

        calls = {}

        def fake_run_server(host: str, port: int, debug: bool):
            calls["host"] = host
            calls["port"] = port
            calls["debug"] = debug

        monkeypatch.setitem(
            sys.modules,
            "code_scalpel.integrations.rest_api_server",
            SimpleNamespace(run_server=fake_run_server),
        )

        exit_code = cli.start_server(host="127.0.0.1", port=1234)
        capsys.readouterr()

        assert exit_code == 0
        assert calls == {"host": "127.0.0.1", "port": 1234, "debug": False}

    def test_start_mcp_server_http_allows_lan_host_rewrite(self, capsys, monkeypatch, tmp_path):
        from code_scalpel import cli

        calls = {}

        def fake_run_server(
            transport: str,
            host: str,
            port: int,
            allow_lan: bool,
            root_path,
            tier=None,
        ):
            calls.update(
                {
                    "transport": transport,
                    "host": host,
                    "port": port,
                    "allow_lan": allow_lan,
                    "root_path": root_path,
                    "tier": tier,
                }
            )

        monkeypatch.setitem(
            sys.modules,
            "code_scalpel.mcp.server",
            SimpleNamespace(run_server=fake_run_server),
        )

        exit_code = cli.start_mcp_server(
            transport="sse",
            host="127.0.0.1",
            port=8081,
            allow_lan=True,
            root_path=str(tmp_path),
        )
        capsys.readouterr()

        assert exit_code == 0
        assert calls["host"] == "127.0.0.1"
        assert calls["allow_lan"] is True
        assert calls["transport"] == "sse"

    def test_main_scan_code_json_uses_scan_code_security(self, capsys, monkeypatch):
        import sys

        from code_scalpel import cli

        monkeypatch.setattr(sys, "argv", ["code-scalpel", "scan", "--code", "print('hi')", "--json"])

        called = {}

        def fake_scan_code_security(code: str, output_format: str):
            called["code"] = code
            called["output_format"] = output_format
            return 0

        monkeypatch.setattr(cli, "scan_code_security", fake_scan_code_security)

        exit_code = cli.main()
        capsys.readouterr()

        assert exit_code == 0
        assert called == {"code": "print('hi')", "output_format": "json"}

    def test_main_no_args(self, capsys, monkeypatch):
        """Test main with no arguments shows help."""
        import sys

        from code_scalpel.cli import main

        monkeypatch.setattr(sys, "argv", ["code-scalpel"])
        result = main()
        captured = capsys.readouterr()

        assert result == 0
        assert "usage" in captured.out.lower() or "code-scalpel" in captured.out.lower()

    def test_main_version(self, capsys, monkeypatch):
        """Test main version command."""
        import sys

        from code_scalpel.cli import main

        monkeypatch.setattr(sys, "argv", ["code-scalpel", "version"])
        result = main()
        captured = capsys.readouterr()

        assert result == 0
        assert "0.1.0" in captured.out or "Code Scalpel" in captured.out

    def test_main_analyze_with_code(self, capsys, monkeypatch):
        """Test main analyze --code."""
        import sys

        from code_scalpel.cli import main

        monkeypatch.setattr(sys, "argv", ["code-scalpel", "analyze", "--code", "x = 1"])
        result = main()
        capsys.readouterr()

        assert result == 0

    def test_main_analyze_no_input(self, capsys, monkeypatch):
        """Test main analyze without file or code."""
        import sys

        from code_scalpel.cli import main

        monkeypatch.setattr(sys, "argv", ["code-scalpel", "analyze"])
        result = main()
        capsys.readouterr()

        assert result == 1  # Should fail with exit code 1
