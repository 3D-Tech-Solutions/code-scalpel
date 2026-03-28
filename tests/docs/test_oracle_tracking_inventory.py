"""Audit tests for Oracle tracking documentation.

[20260311_TEST] Ensure the Oracle tracker documents a scenario inventory for
every public MCP tool.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TOOLS_DIR = PROJECT_ROOT / "src" / "code_scalpel" / "mcp" / "tools"
TRACKER_PATH = PROJECT_ROOT / "docs" / "oracle" / "ORACLE_MCP_CLI_TRACKING.md"
APPENDIX_HEADING = "## Appendix: Per-Tool Testing Checklists"


def _is_mcp_tool_call(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "mcp"
        and node.func.attr == "tool"
    )


def _collect_public_mcp_tools() -> list[str]:
    tool_names: set[str] = set()

    for file_path in sorted(TOOLS_DIR.glob("*.py")):
        if file_path.name in {"__init__.py", "oracle.py"}:
            continue

        module = ast.parse(file_path.read_text(encoding="utf-8"))
        for node in module.body:
            if isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef)) and any(
                _is_mcp_tool_call(decorator) for decorator in node.decorator_list
            ):
                tool_names.add(node.name)
                continue

            if isinstance(node, ast.Assign) and len(node.targets) == 1:
                target = node.targets[0]
                if not isinstance(target, ast.Name):
                    continue
                value = node.value
                if (
                    isinstance(value, ast.Call)
                    and isinstance(value.func, ast.Call)
                    and _is_mcp_tool_call(value.func)
                ):
                    tool_names.add(target.id)

    return sorted(tool_names)


def _parse_appendix_sections(markdown: str) -> dict[str, str]:
    if APPENDIX_HEADING not in markdown:
        raise AssertionError(f"Missing appendix heading: {APPENDIX_HEADING}")

    appendix = markdown.split(APPENDIX_HEADING, 1)[1]
    pattern = re.compile(
        r"^### `(?P<tool>[^`]+)`\n(?P<body>.*?)(?=^### `|\Z)",
        re.MULTILINE | re.DOTALL,
    )
    return {
        match.group("tool"): match.group("body") for match in pattern.finditer(appendix)
    }


class TestOracleTrackingInventory:
    """Keep Oracle tracking docs aligned with the public MCP tool surface."""

    def test_tracker_appendix_covers_every_public_mcp_tool(self) -> None:
        public_tools = _collect_public_mcp_tools()
        tracker = TRACKER_PATH.read_text(encoding="utf-8")
        sections = _parse_appendix_sections(tracker)

        documented_tools = sorted(sections)

        assert documented_tools == public_tools

    def test_each_appendix_section_declares_scenario_inventory_and_checklists(
        self,
    ) -> None:
        tracker = TRACKER_PATH.read_text(encoding="utf-8")
        sections = _parse_appendix_sections(tracker)

        for tool_name, body in sections.items():
            assert "- Applicable scenarios:" in body, tool_name
            assert re.search(r"`[^`]+`", body), tool_name
            assert "- MCP checklist:" in body, tool_name
            assert "- CLI checklist:" in body, tool_name

            checklist_items = re.findall(r"^\s*- \[ \] .+$", body, re.MULTILINE)
            assert len(checklist_items) >= 2, tool_name
