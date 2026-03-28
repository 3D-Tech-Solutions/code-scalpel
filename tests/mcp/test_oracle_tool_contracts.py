"""Cross-tool Oracle outcome contracts for public MCP tools.

[20260311_TEST] Enforce one representative guided failure outcome for every
public MCP tool so Oracle and wrapper-level correction behavior cannot drift.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from code_scalpel.mcp.validators.core import ValidationError

pytestmark = pytest.mark.asyncio

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TOOLS_DIR = PROJECT_ROOT / "src" / "code_scalpel" / "mcp" / "tools"


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


def _raise_file_not_found(path: str) -> None:
    raise FileNotFoundError(f"Cannot access path: {path}")


def _assert_error_code(result, expected_error_code: str) -> None:
    assert getattr(result, "error", None) is not None
    error = result.error
    actual = getattr(error, "error_code", None)
    if actual is None and isinstance(error, dict):
        actual = error.get("error_code")
    assert actual == expected_error_code


async def _run_analyze_code(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    from code_scalpel.mcp.tools.analyze import analyze_code
    from code_scalpel.mcp.tools import analyze as analyze_module

    monkeypatch.setattr(
        analyze_module,
        "resolve_path",
        lambda path, project_root=None: _raise_file_not_found(path),
    )
    return await analyze_code(file_path="/K:/repo/missing.py")


async def _run_extract_code(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    from code_scalpel.mcp.tools.extraction import extract_code
    from code_scalpel.mcp.tools import extraction as extraction_module

    async def fake_extract(*args, **kwargs):
        raise ValidationError("Symbol 'process_dta' not found.")

    monkeypatch.setattr(extraction_module, "_extract_code", fake_extract)
    return await extract_code(
        target_type="function",
        target_name="process_dta",
        code="def process_data():\n    return 1\n",
    )


async def _run_rename_symbol(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    from code_scalpel.mcp.tools.extraction import rename_symbol
    from code_scalpel.mcp.tools import extraction as extraction_module

    source_file = tmp_path / "sample.py"
    source_file.write_text("def process_data():\n    return 1\n", encoding="utf-8")

    async def fake_rename(*args, **kwargs):
        raise ValidationError("Symbol 'process_dta' not found.")

    monkeypatch.setattr(extraction_module, "_rename_symbol", fake_rename)
    return await rename_symbol(
        file_path=str(source_file),
        target_type="function",
        target_name="process_dta",
        new_name="process_item",
    )


async def _run_update_symbol(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    from code_scalpel.mcp.tools.extraction import update_symbol
    from code_scalpel.mcp.tools import extraction as extraction_module

    source_file = tmp_path / "sample.py"
    source_file.write_text("def process_data():\n    return 1\n", encoding="utf-8")

    async def fake_update(*args, **kwargs):
        raise ValidationError("Symbol 'process_dta' not found.")

    monkeypatch.setattr(extraction_module, "_update_symbol", fake_update)
    return await update_symbol(
        file_path=str(source_file),
        target_type="function",
        target_name="process_dta",
        new_code="def process_data():\n    return 2\n",
    )


async def _run_unified_sink_detect(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    from code_scalpel.mcp.tools.security import unified_sink_detect

    return await unified_sink_detect("print('hi')", language="elixir")


async def _run_type_evaporation_scan(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    from code_scalpel.mcp.tools.security import type_evaporation_scan
    from code_scalpel.mcp.tools import security as security_module

    monkeypatch.setattr(
        security_module,
        "resolve_path",
        lambda path, project_root=None: _raise_file_not_found(path),
    )
    return await type_evaporation_scan(
        frontend_file_path="/K:/repo/frontend.ts",
        backend_code="def handler():\n    return 1\n",
    )


async def _run_scan_dependencies(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    from code_scalpel.mcp.tools.security import scan_dependencies
    from code_scalpel.mcp.tools import security as security_module

    monkeypatch.setattr(
        security_module,
        "resolve_path",
        lambda path, project_root=None: _raise_file_not_found(path),
    )
    return await scan_dependencies(path="/K:/repo")


async def _run_security_scan(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    from code_scalpel.mcp.tools.security import security_scan
    from code_scalpel.mcp.tools import security as security_module

    monkeypatch.setattr(
        security_module,
        "resolve_path",
        lambda path, project_root=None: _raise_file_not_found(path),
    )
    return await security_scan(file_path="/K:/repo/vuln.py")


async def _run_symbolic_execute(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    from code_scalpel.mcp.tools.symbolic import symbolic_execute

    return await symbolic_execute("def demo(x):\n    return x\n", language="elixir")


async def _run_generate_unit_tests(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    from code_scalpel.mcp.tools.symbolic import generate_unit_tests
    from code_scalpel.mcp.tools import symbolic as symbolic_module

    monkeypatch.setattr(
        symbolic_module,
        "resolve_path",
        lambda path, project_root=None: _raise_file_not_found(path),
    )
    return await generate_unit_tests(file_path="/K:/repo/sample.py")


async def _run_simulate_refactor(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    from code_scalpel.mcp.tools.symbolic import simulate_refactor

    return await simulate_refactor("def demo():\n    return 1\n")


async def _run_crawl_project(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    from code_scalpel.mcp.tools.context import crawl_project
    from code_scalpel.mcp.tools import context as context_module

    monkeypatch.setattr(
        context_module,
        "resolve_path",
        lambda path, project_root=None: _raise_file_not_found(path),
    )
    return await crawl_project(root_path="/K:/repo")


async def _run_get_file_context(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    from code_scalpel.mcp.tools.context import get_file_context
    from code_scalpel.mcp.tools import context as context_module

    async def fake_get_file_context(file_path: str):
        raise FileNotFoundError(file_path)

    monkeypatch.setattr(context_module, "_get_file_context", fake_get_file_context)
    return await get_file_context(file_path=str(tmp_path / "missing.py"))


async def _run_get_symbol_references(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    from code_scalpel.mcp.tools.context import get_symbol_references
    from code_scalpel.mcp.tools import context as context_module

    monkeypatch.setattr(
        context_module,
        "resolve_path",
        lambda path, project_root=None: _raise_file_not_found(path),
    )
    return await get_symbol_references(symbol_name="helper", project_root="/K:/repo")


async def _run_get_call_graph(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    from code_scalpel.mcp.tools.graph import get_call_graph
    from code_scalpel.mcp.tools import graph as graph_module

    monkeypatch.setattr(
        graph_module,
        "resolve_path",
        lambda path, project_root=None: _raise_file_not_found(path),
    )
    return await get_call_graph(project_root="/K:/repo")


async def _run_get_graph_neighborhood(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    from code_scalpel.mcp.tools.graph import get_graph_neighborhood
    from code_scalpel.mcp.tools import graph as graph_module

    monkeypatch.setattr(
        graph_module,
        "resolve_path",
        lambda path, project_root=None: _raise_file_not_found(path),
    )
    return await get_graph_neighborhood(
        center_node_id="python::app.main::function::main",
        project_root="/K:/repo",
    )


async def _run_get_project_map(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    from code_scalpel.mcp.tools.graph import get_project_map
    from code_scalpel.mcp.tools import graph as graph_module

    monkeypatch.setattr(
        graph_module,
        "resolve_path",
        lambda path, project_root=None: _raise_file_not_found(path),
    )
    return await get_project_map(project_root="/K:/repo")


async def _run_get_cross_file_dependencies(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    from code_scalpel.mcp.tools.graph import get_cross_file_dependencies
    from code_scalpel.mcp.tools import graph as graph_module

    monkeypatch.setattr(
        graph_module,
        "resolve_path",
        lambda path, project_root=None: _raise_file_not_found(path),
    )
    return await get_cross_file_dependencies(
        target_file="/K:/repo/service.py",
        target_symbol="helper",
        project_root="/K:/repo",
    )


async def _run_cross_file_security_scan(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    from code_scalpel.mcp.tools.graph import cross_file_security_scan
    from code_scalpel.mcp.tools import graph as graph_module

    monkeypatch.setattr(
        graph_module,
        "resolve_path",
        lambda path, project_root=None: _raise_file_not_found(path),
    )
    return await cross_file_security_scan(project_root="/K:/repo")


async def _run_validate_paths(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    from code_scalpel.mcp.tools.policy import validate_paths
    from code_scalpel.mcp.tools import policy as policy_module

    def fake_validate_paths(*args, **kwargs):
        raise FileNotFoundError("/K:/repo/missing.py")

    monkeypatch.setattr(policy_module, "_validate_paths_sync", fake_validate_paths)
    return await validate_paths(paths=["/K:/repo/missing.py"])


async def _run_verify_policy_integrity(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    from code_scalpel.mcp.tools.policy import verify_policy_integrity
    from code_scalpel.mcp.tools import policy as policy_module

    def fake_verify_policy_integrity(*args, **kwargs):
        raise FileNotFoundError("/K:/repo/.code-scalpel")

    monkeypatch.setattr(
        policy_module,
        "_verify_policy_integrity_sync",
        fake_verify_policy_integrity,
    )
    return await verify_policy_integrity(policy_dir="/K:/repo/.code-scalpel")


async def _run_code_policy_check(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    from code_scalpel.mcp.tools.policy import code_policy_check
    from code_scalpel.mcp.tools import policy as policy_module

    sample_file = tmp_path / "sample.py"
    sample_file.write_text("print('hi')\n", encoding="utf-8")

    monkeypatch.setattr(policy_module, "_get_current_tier", lambda: "community")
    monkeypatch.setattr(
        policy_module,
        "get_tool_capabilities",
        lambda tool_name, tier: {"limits": {"max_files": 100, "max_rules": 50}},
    )
    return await code_policy_check(
        paths=[str(sample_file)],
        compliance_standards=["SOC2"],
    )


async def _run_get_capabilities(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    from code_scalpel.mcp.tools.system import get_capabilities

    return await get_capabilities(tier="ultimate")


ORACLE_CASES = {
    "analyze_code": (_run_analyze_code, "correction_needed"),
    "extract_code": (_run_extract_code, "correction_needed"),
    "rename_symbol": (_run_rename_symbol, "correction_needed"),
    "update_symbol": (_run_update_symbol, "correction_needed"),
    "unified_sink_detect": (_run_unified_sink_detect, "invalid_argument"),
    "type_evaporation_scan": (_run_type_evaporation_scan, "correction_needed"),
    "scan_dependencies": (_run_scan_dependencies, "correction_needed"),
    "security_scan": (_run_security_scan, "correction_needed"),
    "symbolic_execute": (_run_symbolic_execute, "invalid_argument"),
    "generate_unit_tests": (_run_generate_unit_tests, "correction_needed"),
    "simulate_refactor": (_run_simulate_refactor, "invalid_argument"),
    "crawl_project": (_run_crawl_project, "correction_needed"),
    "get_file_context": (_run_get_file_context, "correction_needed"),
    "get_symbol_references": (_run_get_symbol_references, "correction_needed"),
    "get_call_graph": (_run_get_call_graph, "correction_needed"),
    "get_graph_neighborhood": (_run_get_graph_neighborhood, "correction_needed"),
    "get_project_map": (_run_get_project_map, "correction_needed"),
    "get_cross_file_dependencies": (
        _run_get_cross_file_dependencies,
        "correction_needed",
    ),
    "cross_file_security_scan": (
        _run_cross_file_security_scan,
        "correction_needed",
    ),
    "validate_paths": (_run_validate_paths, "correction_needed"),
    "verify_policy_integrity": (
        _run_verify_policy_integrity,
        "correction_needed",
    ),
    "code_policy_check": (_run_code_policy_check, "upgrade_required"),
    "get_capabilities": (_run_get_capabilities, "invalid_argument"),
}


class TestOracleToolContracts:
    """[20260311_TEST] Keep representative Oracle outcomes stable per public tool."""

    async def test_oracle_case_inventory_matches_public_tool_inventory(self) -> None:
        assert sorted(ORACLE_CASES) == _collect_public_mcp_tools()

    @pytest.mark.parametrize(
        ("tool_name", "runner", "expected_error_code"),
        [
            (tool_name, runner, expected_error_code)
            for tool_name, (runner, expected_error_code) in sorted(ORACLE_CASES.items())
        ],
    )
    async def test_public_tool_returns_expected_guided_outcome(
        self,
        tool_name: str,
        runner,
        expected_error_code: str,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        result = await runner(monkeypatch, tmp_path)

        _assert_error_code(result, expected_error_code)
