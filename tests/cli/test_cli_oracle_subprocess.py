"""Subprocess-level CLI Oracle output regression tests."""

from __future__ import annotations

import os
import subprocess
import sys


# [20260311_TEST] Keep subprocess CLI tests importable without editable install.
_TEST_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(os.path.dirname(_TEST_DIR))
_SRC_PATH = os.path.join(_PROJECT_ROOT, "src")


def _cli_env() -> dict[str, str]:
    """Build a subprocess environment for stable CLI regression tests."""
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join([_SRC_PATH, env.get("PYTHONPATH", "")]).rstrip(
        os.pathsep
    )
    env.pop("CODE_SCALPEL_LICENSE_PATH", None)
    env["CODE_SCALPEL_TIER"] = "community"
    return env


def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    """Run the CLI as a subprocess for user-facing stderr assertions."""
    return subprocess.run(
        [sys.executable, "-m", "code_scalpel.cli", *args],
        capture_output=True,
        text=True,
        env=_cli_env(),
    )


def _stderr_lines(result: subprocess.CompletedProcess[str]) -> list[str]:
    """Return only the user-facing Oracle stderr lines for exact assertions."""
    prefixes = (
        "Error:",
        "Error Code:",
        "Oracle guidance:",
        "  - ",
        "This feature requires",
        "Current tier:",
        "Required tier:",
        "For licensing information, visit:",
        "  https://",
    )
    return [line for line in result.stderr.splitlines() if line.startswith(prefixes)]


def test_cli_subprocess_correction_needed_stderr_is_exact():
    """[20260311_TEST] CLI should expose exact correction guidance for malformed node IDs."""
    result = _run_cli("get-graph-neighborhood", "bad-node")

    assert result.returncode == 1
    assert _stderr_lines(result) == [
        "Error: Invalid node ID format: 'bad-node'. Expected format: language::module::type::name (e.g., python::app.routes::function::handle_request)",
        "Error Code: correction_needed",
        "Oracle guidance:",
        "  - Use node IDs in the form language::module::type::name, for example python::app.routes::function::handle_request.",
    ]


def test_cli_subprocess_invalid_argument_stderr_is_exact():
    """[20260311_TEST] CLI should expose exact invalid-argument guidance for range errors."""
    result = _run_cli("get-call-graph", "--depth", "0")

    assert result.returncode == 1
    assert _stderr_lines(result) == [
        "Error: Parameter 'depth' must be >= 1.",
        "Error Code: invalid_argument",
        "Oracle guidance:",
        "  - depth: 0",
    ]


def test_cli_subprocess_upgrade_required_stderr_is_exact(tmp_path):
    """[20260311_TEST] CLI should expose exact upgrade messaging for tier-gated requests."""
    target = tmp_path / "sample.py"
    target.write_text("print('ok')\n", encoding="utf-8")

    result = _run_cli("code-policy-check", str(target), "--generate-report")

    assert result.returncode == 1
    assert _stderr_lines(result) == [
        "Error: Compliance PDF reports require Enterprise tier; current tier is community.",
        "Error Code: upgrade_required",
        "This feature requires a higher tier license.",
        "Current tier: COMMUNITY",
        "For licensing information, visit:",
        "  https://github.com/cyanheads/code-scalpel#licensing",
    ]


def test_cli_subprocess_analyze_path_correction_is_exact(tmp_path):
    """[20260311_TEST] Analyze CLI should expose correction guidance for bad file paths."""
    missing = tmp_path / "missing.py"

    result = _run_cli("analyze", str(missing))

    assert result.returncode == 1
    lines = _stderr_lines(result)
    assert lines[0] == f"Error: Cannot access file: {missing} (not found)"
    assert "Error Code: correction_needed" in lines
    assert "Oracle guidance:" in lines
    assert any(
        line == f"  - Cannot access file: {missing} (not found)" for line in lines
    )


def test_cli_subprocess_scan_invalid_argument_is_exact():
    """[20260311_TEST] Scan CLI should expose exact invalid-argument guidance for bad thresholds."""
    result = _run_cli("scan", "--code", "print('x')", "--confidence-threshold", "1.5")

    assert result.returncode == 1
    assert _stderr_lines(result) == [
        "Error: 'confidence_threshold' must be between 0.0 and 1.0.",
        "Error Code: invalid_argument",
        "Oracle guidance:",
        "  - confidence threshold: 1.5",
    ]


def test_cli_subprocess_capabilities_not_found_has_guidance():
    """[20260311_TEST] Capabilities CLI should expose not-found guidance for unknown tools."""
    result = _run_cli("capabilities", "--tool", "not_a_real_tool")

    assert result.returncode == 1
    lines = _stderr_lines(result)
    assert lines[0] == (
        "Error: Unknown tool: 'not_a_real_tool'. Call get_capabilities() without tool_name to list all available tools."
    )
    assert lines[1] == "Error Code: not_found"
    assert lines[2] == "Oracle guidance:"
    assert any(line.startswith("  - available tools: ") for line in lines[3:])


def test_cli_subprocess_extract_code_path_correction_is_exact(tmp_path):
    """[20260311_TEST] Extract-code CLI should expose correction guidance for bad file paths."""
    missing = tmp_path / "missing.py"

    result = _run_cli("extract-code", str(missing), "--name", "target")

    assert result.returncode == 1
    lines = _stderr_lines(result)
    assert lines[0] == f"Error: Cannot access file: {missing} (not found)"
    assert "Error Code: correction_needed" in lines
    assert "Oracle guidance:" in lines
    assert any(
        line == f"  - Cannot access file: {missing} (not found)" for line in lines
    )
