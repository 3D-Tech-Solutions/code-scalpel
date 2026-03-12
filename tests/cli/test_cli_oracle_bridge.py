"""CLI Oracle bridge regression tests."""

from __future__ import annotations

from types import SimpleNamespace

import code_scalpel.cli as cli
from code_scalpel.cli_tools import tool_bridge
from code_scalpel.mcp.contract import ToolError


def test_handle_get_graph_neighborhood_uses_mcp_argument_names(monkeypatch):
    """[20260312_TEST] Graph neighborhood CLI should forward Oracle-aware argument names unchanged."""
    captured: dict[str, object] = {}

    def fake_invoke(
        tool_name: str, tool_args: dict[str, object], output_format: str
    ) -> int:
        captured["tool_name"] = tool_name
        captured["tool_args"] = tool_args
        captured["output_format"] = output_format
        return 0

    monkeypatch.setattr(
        "code_scalpel.cli_tools.tool_bridge.invoke_tool_with_format", fake_invoke
    )

    args = SimpleNamespace(
        node_id="python::pkg.mod::function::run",
        project_root="/tmp/project",
        k=2,
        direction="both",
        max_nodes=25,
        min_confidence=0.4,
        json=False,
    )

    exit_code = cli.handle_get_graph_neighborhood(args)

    assert exit_code == 0
    assert captured["tool_name"] == "get_graph_neighborhood"
    assert captured["tool_args"] == {
        "center_node_id": "python::pkg.mod::function::run",
        "project_root": "/tmp/project",
        "k": 2,
        "direction": "both",
        "max_nodes": 25,
        "min_confidence": 0.4,
    }
    assert captured["output_format"] == "text"


def test_handle_validate_paths_uses_paths_list(monkeypatch):
    """[20260312_TEST] Validate-paths CLI should forward list-based path input to the MCP tool."""
    captured: dict[str, object] = {}

    def fake_invoke(
        tool_name: str, tool_args: dict[str, object], output_format: str
    ) -> int:
        captured["tool_name"] = tool_name
        captured["tool_args"] = tool_args
        captured["output_format"] = output_format
        return 0

    monkeypatch.setattr(
        "code_scalpel.cli_tools.tool_bridge.invoke_tool_with_format", fake_invoke
    )

    args = SimpleNamespace(
        paths=["src/app.py", "src/lib.py"],
        project_root="/workspace",
        json=True,
    )

    exit_code = cli.handle_validate_paths(args)

    assert exit_code == 0
    assert captured["tool_name"] == "validate_paths"
    assert captured["tool_args"] == {
        "paths": ["src/app.py", "src/lib.py"],
        "project_root": "/workspace",
    }
    assert captured["output_format"] == "json"


def test_handle_simulate_refactor_uses_code_based_shape(monkeypatch):
    """[20260312_TEST] Simulate-refactor CLI should forward code inputs required by the MCP tool."""
    captured: dict[str, object] = {}

    def fake_invoke(
        tool_name: str, tool_args: dict[str, object], output_format: str
    ) -> int:
        captured["tool_name"] = tool_name
        captured["tool_args"] = tool_args
        captured["output_format"] = output_format
        return 0

    monkeypatch.setattr(
        "code_scalpel.cli_tools.tool_bridge.invoke_tool_with_format", fake_invoke
    )

    args = SimpleNamespace(
        original_code="def old():\n    return 1\n",
        new_code="def old():\n    return 2\n",
        patch=None,
        strict_mode=True,
        json=False,
    )

    exit_code = cli.handle_simulate_refactor(args)

    assert exit_code == 0
    assert captured["tool_name"] == "simulate_refactor"
    assert captured["tool_args"] == {
        "original_code": "def old():\n    return 1\n",
        "new_code": "def old():\n    return 2\n",
        "patch": None,
        "strict_mode": True,
    }
    assert captured["output_format"] == "text"


def test_handle_analyze_routes_to_mcp_tool(monkeypatch):
    """[20260311_TEST] Analyze CLI should route through the MCP bridge with analyze_code arguments."""
    captured: dict[str, object] = {}

    def fake_invoke(
        tool_name: str, tool_args: dict[str, object], output_format: str
    ) -> int:
        captured["tool_name"] = tool_name
        captured["tool_args"] = tool_args
        captured["output_format"] = output_format
        return 0

    monkeypatch.setattr(
        "code_scalpel.cli_tools.tool_bridge.invoke_tool_with_format", fake_invoke
    )

    args = SimpleNamespace(code="x = 1", file=None, language="rust", json=True)

    exit_code = cli.handle_analyze(args)

    assert exit_code == 0
    assert captured["tool_name"] == "analyze_code"
    assert captured["tool_args"] == {
        "code": "x = 1",
        "file_path": None,
        "language": "rust",
    }
    assert captured["output_format"] == "json"


def test_handle_scan_routes_to_mcp_tool(monkeypatch):
    """[20260311_TEST] Scan CLI should route through the MCP bridge with security_scan arguments."""
    captured: dict[str, object] = {}

    def fake_invoke(
        tool_name: str, tool_args: dict[str, object], output_format: str
    ) -> int:
        captured["tool_name"] = tool_name
        captured["tool_args"] = tool_args
        captured["output_format"] = output_format
        return 0

    monkeypatch.setattr(
        "code_scalpel.cli_tools.tool_bridge.invoke_tool_with_format", fake_invoke
    )

    args = SimpleNamespace(
        code=None, file="src/app.py", confidence_threshold=0.9, json=False
    )

    exit_code = cli.handle_scan(args)

    assert exit_code == 0
    assert captured["tool_name"] == "security_scan"
    assert captured["tool_args"] == {
        "code": None,
        "file_path": "src/app.py",
        "confidence_threshold": 0.9,
    }
    assert captured["output_format"] == "text"


def test_handle_capabilities_routes_to_mcp_tool(monkeypatch):
    """[20260311_TEST] Capabilities CLI should route through the MCP bridge with get_capabilities arguments."""
    captured: dict[str, object] = {}

    def fake_invoke(
        tool_name: str, tool_args: dict[str, object], output_format: str
    ) -> int:
        captured["tool_name"] = tool_name
        captured["tool_args"] = tool_args
        captured["output_format"] = output_format
        return 0

    monkeypatch.setattr(
        "code_scalpel.cli_tools.tool_bridge.invoke_tool_with_format", fake_invoke
    )

    args = SimpleNamespace(tier="pro", tool="analyze_code", json=False)

    exit_code = cli.handle_capabilities(args)

    assert exit_code == 0
    assert captured["tool_name"] == "get_capabilities"
    assert captured["tool_args"] == {
        "tier": "pro",
        "tool_name": "analyze_code",
    }
    assert captured["output_format"] == "text"


def test_handle_extract_code_supports_new_target_shape(monkeypatch):
    """[20260311_TEST] Extract-code CLI should forward explicit target types and inline code to the MCP tool."""
    captured: dict[str, object] = {}
    call_count = 0

    def fake_invoke(
        tool_name: str, tool_args: dict[str, object], output_format: str
    ) -> int:
        nonlocal call_count
        call_count += 1
        captured["tool_name"] = tool_name
        captured["tool_args"] = tool_args
        captured["output_format"] = output_format
        return 0

    monkeypatch.setattr(
        "code_scalpel.cli_tools.tool_bridge.invoke_tool_with_format", fake_invoke
    )

    args = SimpleNamespace(
        target_type="class",
        class_name=None,
        target_name="Widget",
        file_path=None,
        code="class Widget:\n    pass\n",
        include_cross_file_deps=False,
        include_context=True,
        output=None,
        json=False,
    )

    exit_code = cli.handle_extract_code(args)

    assert exit_code == 0
    assert captured["tool_name"] == "extract_code"
    assert captured["tool_args"] == {
        "target_type": "class",
        "target_name": "Widget",
        "file_path": None,
        "code": "class Widget:\n    pass\n",
        "include_cross_file_deps": False,
        "include_context": True,
    }
    assert captured["output_format"] == "text"
    assert call_count == 1


def test_show_capabilities_routes_through_bridge(monkeypatch):
    """[20260312_TEST] Direct show_capabilities helper should use the same bridge path as the CLI command."""
    captured: dict[str, object] = {}

    def fake_invoke(
        tool_name: str, tool_args: dict[str, object], output_format: str
    ) -> int:
        captured["tool_name"] = tool_name
        captured["tool_args"] = tool_args
        captured["output_format"] = output_format
        return 0

    monkeypatch.setattr(
        "code_scalpel.cli_tools.tool_bridge.invoke_tool_with_format", fake_invoke
    )

    exit_code = cli.show_capabilities(tier="enterprise", tool_filter="extract_code")

    assert exit_code == 0
    assert captured["tool_name"] == "get_capabilities"
    assert captured["tool_args"] == {
        "tier": "enterprise",
        "tool_name": "extract_code",
    }
    assert captured["output_format"] == "text"


def test_print_error_renders_oracle_guidance(capsys):
    """[20260312_TEST] CLI text output should render structured Oracle guidance for correctable failures."""
    tool_bridge._print_error(
        ToolError(
            error="Parameter 'depth' must be >= 1.",
            error_code="invalid_argument",
            error_details={
                "hint": "Increase depth to at least 1.",
                "max_depth": 0,
                "paths_from": "svc.entry",
            },
        ),
        tier="community",
    )

    captured = capsys.readouterr()

    assert "Error Code: invalid_argument" in captured.err
    assert "Oracle guidance:" in captured.err
    assert "Increase depth to at least 1." in captured.err
    assert "max depth: 0" in captured.err
    assert "paths from: svc.entry" in captured.err
