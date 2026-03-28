"""Representative public-surface success coverage for the 22 functional MCP tools.

[20260314_TEST] Keep one success-path scenario for each functional public MCP tool
stable at the server boundary. This intentionally excludes the introspection-only
get_capabilities tool from the 22-tool functional inventory.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.asyncio

PROJECT_ROOT = Path(__file__).resolve().parents[2]


FUNCTIONAL_MCP_TOOLS = [
    "analyze_code",
    "extract_code",
    "rename_symbol",
    "update_symbol",
    "unified_sink_detect",
    "type_evaporation_scan",
    "scan_dependencies",
    "security_scan",
    "symbolic_execute",
    "generate_unit_tests",
    "simulate_refactor",
    "crawl_project",
    "get_file_context",
    "get_symbol_references",
    "get_call_graph",
    "get_graph_neighborhood",
    "get_project_map",
    "get_cross_file_dependencies",
    "cross_file_security_scan",
    "validate_paths",
    "verify_policy_integrity",
    "code_policy_check",
]


def _item_attr(item, name: str):
    if isinstance(item, dict):
        return item.get(name)
    return getattr(item, name)


def _result_data(result):
    data = getattr(result, "data", None)
    if isinstance(data, dict):
        return data
    if data is not None and hasattr(data, "model_dump"):
        return data.model_dump()
    if data is not None and hasattr(data, "dict"):
        return data.dict()
    return {}


def _workspace_scratch_dir(tmp_path: Path) -> Path:
    scratch_dir = PROJECT_ROOT / ".tmp_mcp_success" / tmp_path.name
    scratch_dir.mkdir(parents=True, exist_ok=True)
    return scratch_dir


async def _run_analyze_code(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from code_scalpel.mcp.server import analyze_code

    result = await analyze_code(
        code="def add(a, b):\n    return a + b\n",
        language="python",
    )

    assert result.success is True
    assert result.language_detected == "python"
    assert "add" in result.functions


async def _run_extract_code(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from code_scalpel.mcp.server import extract_code

    result = await extract_code(
        code="def helper():\n    return 1\n\ndef main():\n    return helper()\n",
        target_type="function",
        target_name="main",
        include_context=True,
        context_depth=1,
    )

    assert result.success is True
    assert result.target_name == "main"
    assert "helper" in result.context_code


async def _run_rename_symbol(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from code_scalpel.mcp.server import rename_symbol

    source_file = _workspace_scratch_dir(tmp_path) / "rename_target.py"
    source_file.write_text(
        "def old_name():\n    return 1\n\nvalue = old_name()\n",
        encoding="utf-8",
    )

    result = await rename_symbol(
        file_path=str(source_file),
        target_type="function",
        target_name="old_name",
        new_name="new_name",
    )

    assert result.success is True
    updated = source_file.read_text(encoding="utf-8")
    assert "new_name" in updated
    assert "old_name" not in updated


async def _run_update_symbol(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from code_scalpel.mcp.server import update_symbol

    source_file = _workspace_scratch_dir(tmp_path) / "update_target.py"
    source_file.write_text(
        "def target():\n    return 1\n\ndef helper():\n    return 2\n",
        encoding="utf-8",
    )

    result = await update_symbol(
        file_path=str(source_file),
        target_type="function",
        target_name="target",
        new_code="def target():\n    return 42\n",
    )

    assert result.success is True
    updated = source_file.read_text(encoding="utf-8")
    assert "return 42" in updated
    assert "return 2" in updated


async def _run_unified_sink_detect(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from code_scalpel.mcp.server import unified_sink_detect

    result = await unified_sink_detect(
        code=(
            "import sqlite3\n"
            "user_input = input()\n"
            'cursor.execute("SELECT * FROM users WHERE id=" + user_input)\n'
        ),
        language="python",
        confidence_threshold=0.8,
    )

    assert result.success is True
    assert result.sink_count > 0


async def _run_type_evaporation_scan(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from code_scalpel.mcp.server import type_evaporation_scan

    result = await type_evaporation_scan(
        frontend_code=(
            "async function loadUser() {\n"
            "  const response = await fetch('/api/user');\n"
            "  const payload = await response.json();\n"
            "  const parsed = JSON.parse('{\"x\": 1}');\n"
            "  return payload ?? parsed;\n"
            "}\n"
        ),
        backend_code=(
            "@app.get('/api/user')\n"
            "def get_user():\n"
            "    body = request.get_json()\n"
            "    return jsonify(body)\n"
        ),
        frontend_file="frontend.ts",
        backend_file="backend.py",
    )

    assert result.success is True
    assert hasattr(result, "implicit_any_count")


async def _run_scan_dependencies(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from code_scalpel.mcp.server import scan_dependencies

    (tmp_path / "requirements.txt").write_text(
        "requests==2.31.0\npytest==8.3.5\n",
        encoding="utf-8",
    )

    result = await scan_dependencies(
        path=str(tmp_path),
        scan_vulnerabilities=False,
    )

    assert result.success is True
    assert result.total_dependencies >= 2


async def _run_security_scan(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from code_scalpel.mcp.server import security_scan

    result = await security_scan(
        code="def dangerous(user_input):\n    return eval(user_input)\n",
        confidence_threshold=0.4,
    )

    assert result.success is True
    assert result.has_vulnerabilities is True
    assert result.vulnerability_count >= 1


async def _run_symbolic_execute(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from code_scalpel.mcp.server import symbolic_execute

    result = await symbolic_execute(
        "def classify(x):\n    if x > 0:\n        return 1\n    return 0\n"
    )

    assert result.success is True
    assert result.paths_explored >= 1


async def _run_generate_unit_tests(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from code_scalpel.mcp.server import generate_unit_tests

    result = await generate_unit_tests(
        code="def add(a, b):\n    return a + b\n",
        framework="pytest",
    )

    assert result.success is True
    assert result.test_count >= 1
    assert result.framework_used == "pytest"


async def _run_simulate_refactor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from code_scalpel.mcp.server import simulate_refactor

    result = await simulate_refactor(
        original_code="def add(a, b):\n    return a + b\n",
        new_code="def add(a: int, b: int) -> int:\n    return a + b\n",
    )

    assert result.success is True
    assert result.is_safe is True


async def _run_crawl_project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from code_scalpel.mcp.server import crawl_project

    (tmp_path / "app.py").write_text(
        "def main():\n    return 1\n",
        encoding="utf-8",
    )

    result = await crawl_project(root_path=str(tmp_path))

    assert result.success is True
    summary = _item_attr(result.summary, "total_files")
    assert summary >= 1


async def _run_get_file_context(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from code_scalpel.mcp.server import get_file_context

    source_file = tmp_path / "context_target.py"
    source_file.write_text(
        "import os\n\n"
        "def helper_function():\n    return 42\n\n"
        "class MyClass:\n    pass\n",
        encoding="utf-8",
    )

    result = await get_file_context(str(source_file))

    assert result.success is True
    assert result.language == "python"
    assert result.line_count > 0


async def _run_get_symbol_references(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from code_scalpel.mcp.server import get_symbol_references

    (tmp_path / "utils.py").write_text(
        "def helper_function():\n    return 42\n",
        encoding="utf-8",
    )
    (tmp_path / "main.py").write_text(
        "from utils import helper_function\n\ndef main():\n    return helper_function()\n",
        encoding="utf-8",
    )

    result = await get_symbol_references("helper_function", str(tmp_path))

    assert result.success is True
    assert result.total_references >= 2


async def _run_get_call_graph(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from code_scalpel.mcp.server import get_call_graph

    (tmp_path / "graph_sample.py").write_text(
        "def helper():\n    return 1\n\n" "def main():\n    return helper()\n",
        encoding="utf-8",
    )

    result = await get_call_graph(project_root=str(tmp_path))

    assert result.success is True
    assert len(result.nodes) >= 1


async def _run_get_graph_neighborhood(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from code_scalpel.mcp.server import get_call_graph, get_graph_neighborhood

    (tmp_path / "neighborhood_sample.py").write_text(
        "def helper():\n    return 1\n\n" "def main():\n    return helper()\n",
        encoding="utf-8",
    )

    graph_result = await get_call_graph(project_root=str(tmp_path))
    assert graph_result.success is True
    assert len(graph_result.nodes) >= 1
    center_node_id = "python::neighborhood_sample::function::main"

    result = await get_graph_neighborhood(
        center_node_id=center_node_id,
        project_root=str(tmp_path),
    )

    assert result.success is True
    assert len(result.nodes) >= 1


async def _run_get_project_map(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from code_scalpel.mcp.server import get_project_map

    (tmp_path / "app.py").write_text(
        "def main():\n    return 1\n",
        encoding="utf-8",
    )

    result = await get_project_map(project_root=str(tmp_path))

    assert result.success is True
    assert result.total_files >= 1
    assert any("main" in entry_point for entry_point in result.entry_points)


async def _run_get_cross_file_dependencies(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from code_scalpel.mcp.server import get_cross_file_dependencies

    (tmp_path / "helper.py").write_text(
        "def helper():\n    return 'help'\n",
        encoding="utf-8",
    )
    (tmp_path / "main.py").write_text(
        "from helper import helper\n\ndef main():\n    return helper()\n",
        encoding="utf-8",
    )

    result = await get_cross_file_dependencies(
        target_file="main.py",
        target_symbol="main",
        project_root=str(tmp_path),
    )

    assert result.success is True
    assert len(result.extracted_symbols) >= 1


async def _run_cross_file_security_scan(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from code_scalpel.mcp.server import cross_file_security_scan

    (tmp_path / "safe.py").write_text(
        "def safe_function(x):\n    return x * 2\n",
        encoding="utf-8",
    )

    result = await cross_file_security_scan(project_root=str(tmp_path))

    assert result.success is True
    assert result.vulnerability_count == 0


async def _run_validate_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from code_scalpel.mcp.server import validate_paths

    target_file = tmp_path / "present.py"
    target_file.write_text("value = 1\n", encoding="utf-8")

    result = await validate_paths(paths=[str(target_file)])
    payload = _result_data(result)
    accessible = payload.get("accessible", getattr(result, "accessible", []))

    assert result.error is None
    assert result.success is True
    assert str(target_file) in accessible


async def _run_verify_policy_integrity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from code_scalpel.mcp.server import verify_policy_integrity
    from code_scalpel.mcp.tools import policy as policy_module

    policy_dir = tmp_path / ".code-scalpel"
    policy_dir.mkdir(parents=True, exist_ok=True)

    # [20260314_TEST] Success-path coverage for this wrapper uses a helper stub
    # because local cryptographic manifests are not stable test fixtures here.
    monkeypatch.setattr(
        policy_module,
        "_verify_policy_integrity_sync",
        lambda *args, **kwargs: {
            "success": True,
            "manifest_valid": True,
            "files_verified": 1,
            "files_failed": [],
            "manifest_source": "file",
            "policy_dir": str(policy_dir),
        },
    )

    result = await verify_policy_integrity(policy_dir=str(policy_dir))

    assert result.success is True
    assert result.manifest_valid is True
    assert result.files_verified == 1


async def _run_code_policy_check(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from code_scalpel.mcp.server import code_policy_check

    target_file = tmp_path / "clean_policy.py"
    target_file.write_text(
        "def add(a, b):\n    return a + b\n",
        encoding="utf-8",
    )

    result = await code_policy_check(paths=[str(target_file)])

    assert result.success is True
    assert result.files_checked == 1


SUCCESS_CASES = {
    "analyze_code": _run_analyze_code,
    "extract_code": _run_extract_code,
    "rename_symbol": _run_rename_symbol,
    "update_symbol": _run_update_symbol,
    "unified_sink_detect": _run_unified_sink_detect,
    "type_evaporation_scan": _run_type_evaporation_scan,
    "scan_dependencies": _run_scan_dependencies,
    "security_scan": _run_security_scan,
    "symbolic_execute": _run_symbolic_execute,
    "generate_unit_tests": _run_generate_unit_tests,
    "simulate_refactor": _run_simulate_refactor,
    "crawl_project": _run_crawl_project,
    "get_file_context": _run_get_file_context,
    "get_symbol_references": _run_get_symbol_references,
    "get_call_graph": _run_get_call_graph,
    "get_graph_neighborhood": _run_get_graph_neighborhood,
    "get_project_map": _run_get_project_map,
    "get_cross_file_dependencies": _run_get_cross_file_dependencies,
    "cross_file_security_scan": _run_cross_file_security_scan,
    "validate_paths": _run_validate_paths,
    "verify_policy_integrity": _run_verify_policy_integrity,
    "code_policy_check": _run_code_policy_check,
}


class TestPublicToolSuccessMatrix:
    """[20260314_TEST] Representative success-path coverage per functional MCP tool."""

    async def test_functional_tool_inventory_is_exactly_22(self) -> None:
        from code_scalpel.mcp import server

        assert len(FUNCTIONAL_MCP_TOOLS) == 22
        assert sorted(FUNCTIONAL_MCP_TOOLS) == sorted(SUCCESS_CASES)
        assert callable(server.get_capabilities)
        assert "get_capabilities" not in FUNCTIONAL_MCP_TOOLS
        assert all(
            callable(getattr(server, tool_name)) for tool_name in FUNCTIONAL_MCP_TOOLS
        )

    @pytest.mark.parametrize("tool_name", FUNCTIONAL_MCP_TOOLS)
    async def test_public_tool_success_case(
        self,
        tool_name: str,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        await SUCCESS_CASES[tool_name](tmp_path, monkeypatch)
