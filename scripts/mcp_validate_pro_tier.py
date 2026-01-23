"""MCP-first validation of Code Scalpel tools in Pro tier.

This is a Pro-tier companion to scripts/mcp_validate_22_tools.py.

It validates:
- All 22 canonical tools are listed
- All tools can be invoked (smoke)
- Pro features are enabled (rename_symbol succeeds)
- Pro limits exceed Community limits (code_policy_check processes >100 files)
- Enterprise-only features are not accessible in Pro (enterprise flags remain false
  and enterprise compliance outputs remain empty)

Usage:
  CODE_SCALPEL_TIER=pro CODE_SCALPEL_LICENSE_PATH=/abs/path/to/license.jwt \
    python scripts/mcp_validate_pro_tier.py --verbose

Exit code:
  0 on success, 1 on any failed check.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

EXPECTED_ALL_TOOLS: list[str] = [
    "analyze_code",
    "code_policy_check",
    "crawl_project",
    "cross_file_security_scan",
    "extract_code",
    "generate_unit_tests",
    "get_call_graph",
    "get_cross_file_dependencies",
    "get_file_context",
    "get_graph_neighborhood",
    "get_project_map",
    "get_symbol_references",
    "rename_symbol",
    "scan_dependencies",
    "security_scan",
    "simulate_refactor",
    "symbolic_execute",
    "type_evaporation_scan",
    "unified_sink_detect",
    "update_symbol",
    "validate_paths",
    "verify_policy_integrity",
]


@dataclass(frozen=True)
class ToolCheck:
    name: str
    ok: bool
    notes: str


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _default_server_command(repo_root: Path) -> str:
    cli = repo_root / ".venv" / "bin" / "code-scalpel"
    if cli.exists():
        return str(cli)
    return sys.executable


def _make_pro_test_project(base_dir: Path, bulk_files: int = 140) -> tuple[Path, dict[str, Path]]:
    root = base_dir / "proj"
    pkg = root / "pkg"
    bulk = root / "bulk"
    pkg.mkdir(parents=True, exist_ok=True)
    bulk.mkdir(parents=True, exist_ok=True)

    (pkg / "__init__.py").write_text("", encoding="utf-8")

    (pkg / "b.py").write_text(
        """\
class Helper:
    def ping(self) -> str:
        return 'pong'
""",
        encoding="utf-8",
    )

    # a.py contains a rename/update target
    (pkg / "a.py").write_text(
        """\
from pkg.b import Helper

class PolicyEngine:
    def __init__(self) -> None:
        self.h = Helper()

    def run(self) -> str:
        return self.h.ping()


def add(a, b):
    return a + b
""",
        encoding="utf-8",
    )

    # issues.py intentionally triggers Pro best-practice and security warnings
    (pkg / "issues.py").write_text(
        """\
# Intentionally imperfect code for Pro-tier policy checks

password = "super-secret"  # SEC001 hardcoded password


def no_types(x, y):  # BP001 missing type hints
    return x + y


async def missing_await():
    import time
    time.sleep(0.01)  # ASYNC002 blocking call in async
    return 1
""",
        encoding="utf-8",
    )

    # Create enough files to exceed Community max_files=100.
    for i in range(bulk_files):
        (bulk / f"f_{i:03d}.py").write_text(
            f"def f_{i}(x):\n    return x\n",
            encoding="utf-8",
        )

    # Policy dir for verify_policy_integrity
    policy_dir = root / ".code-scalpel"
    policy_dir.mkdir(parents=True, exist_ok=True)
    (policy_dir / "budget.yaml").write_text("limits: {}\n", encoding="utf-8")

    return root, {
        "a": pkg / "a.py",
        "b": pkg / "b.py",
        "issues": pkg / "issues.py",
        "policy_dir": policy_dir,
        "bulk_dir": bulk,
    }


async def _call(session: ClientSession, tool: str, args: dict[str, Any]) -> dict[str, Any]:
    res = await session.call_tool(tool, args)
    return res.model_dump()


def _structured_data(payload: dict[str, Any]) -> dict[str, Any]:
    sc = payload.get("structuredContent") or {}
    data = sc.get("data")
    return data if isinstance(data, dict) else {}


def _mcp_call_ok(payload: dict[str, Any]) -> bool:
    # MCP can return isError for tool exceptions.
    if payload.get("isError") is True:
        return False
    return True


def _get_bool(d: dict[str, Any], key: str, default: bool = False) -> bool:
    v = d.get(key)
    return bool(v) if isinstance(v, bool) else default


async def main() -> int:
    verbose = "--verbose" in set(sys.argv)

    repo_root = _repo_root()
    src_root = repo_root / "src"

    run_dir = Path(tempfile.mkdtemp(prefix="code_scalpel_mcp_validate_pro_"))
    project_root, paths = _make_pro_test_project(run_dir)

    env = os.environ.copy()
    env.setdefault("CODE_SCALPEL_TIER", "pro")

    # Ensure repo code is importable in subprocess
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = str(src_root) + (os.pathsep + existing if existing else "")

    # Require a license path for Pro-tier tests.
    if not env.get("CODE_SCALPEL_LICENSE_PATH"):
        print("FAIL: CODE_SCALPEL_LICENSE_PATH is not set; cannot validate Pro tier")
        return 1

    server_cmd = os.environ.get("CODE_SCALPEL_MCP_COMMAND") or _default_server_command(repo_root)
    if server_cmd.endswith("code-scalpel"):
        server_args = ["mcp", "--root", str(project_root)]
    else:
        server_args = ["-m", "code_scalpel.mcp.server", "--root", str(project_root)]

    params = StdioServerParameters(command=server_cmd, args=server_args, env=env, cwd=run_dir)

    checks: list[ToolCheck] = []

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools_result = await session.list_tools()
            tool_names = sorted({t.name for t in tools_result.tools})

            expected = sorted(EXPECTED_ALL_TOOLS)
            if tool_names != expected:
                missing = sorted(set(expected) - set(tool_names))
                extra = sorted(set(tool_names) - set(expected))
                checks.append(
                    ToolCheck(
                        "list_tools",
                        False,
                        f"Mismatch. missing={missing} extra={extra}",
                    )
                )
            else:
                checks.append(ToolCheck("list_tools", True, "22 tools"))

            py_snippet = "def f(x):\n    if x > 0:\n        return x + 1\n    return 0\n"

            # --- Smoke calls for all tools (basic correctness) ---
            smoke: list[tuple[str, dict[str, Any]]] = [
                ("analyze_code", {"code": py_snippet, "language": "python"}),
                (
                    "security_scan",
                    {
                        "code": 'def f(user_id):\n    q=f"SELECT * FROM t WHERE id={user_id}"\n    cursor.execute(q)\n',
                    },
                ),
                (
                    "unified_sink_detect",
                    {"code": "eval(user_input)", "language": "python"},
                ),
                ("symbolic_execute", {"code": py_snippet, "language": "python"}),
                (
                    "generate_unit_tests",
                    {"code": "def add(a,b):\n    return a+b\n", "framework": "pytest"},
                ),
                (
                    "simulate_refactor",
                    {
                        "original_code": "def add(a,b): return a+b\n",
                        "new_code": "def add(a,b): return eval('a+b')\n",
                    },
                ),
                (
                    "extract_code",
                    {
                        "file_path": str(paths["a"].relative_to(project_root)),
                        "target_type": "function",
                        "target_name": "add",
                    },
                ),
                (
                    "get_file_context",
                    {
                        "file_path": str(paths["a"].relative_to(project_root)),
                    },
                ),
                (
                    "get_symbol_references",
                    {
                        "symbol_name": "add",
                        "project_root": str(project_root),
                    },
                ),
                (
                    "get_cross_file_dependencies",
                    {
                        "target_file": str(paths["a"].relative_to(project_root)),
                        "target_symbol": "add",
                        "project_root": str(project_root),
                        "max_depth": 2,
                        "include_code": True,
                        "include_diagram": False,
                    },
                ),
                (
                    "get_project_map",
                    {
                        "project_root": str(project_root),
                        "include_complexity": True,
                    },
                ),
                (
                    "crawl_project",
                    {
                        "root_path": str(project_root),
                        "include_report": True,
                    },
                ),
                (
                    "get_call_graph",
                    {
                        "project_root": str(project_root),
                        "depth": 25,
                    },
                ),
                (
                    "get_graph_neighborhood",
                    {
                        "center_node_id": "python::pkg.a::function::add",
                        "k": 5,
                        "max_nodes": 200,
                        "project_root": str(project_root),
                    },
                ),
                (
                    "cross_file_security_scan",
                    {
                        "project_root": str(project_root),
                        "max_depth": 3,
                        "timeout_seconds": 30,
                        "max_modules": 200,
                    },
                ),
                (
                    "scan_dependencies",
                    {
                        "path": str(project_root),
                        "scan_vulnerabilities": False,
                        "include_dev": True,
                    },
                ),
                (
                    "verify_policy_integrity",
                    {"policy_dir": str(paths["policy_dir"]), "manifest_source": "file"},
                ),
                (
                    "validate_paths",
                    {"paths": [str(paths["a"])], "project_root": str(project_root)},
                ),
                (
                    "type_evaporation_scan",
                    {
                        "frontend_code": "type Role = 'admin' | 'user';\nexport const role = 'admin' as Role;\n",
                        "backend_code": "def handler(req):\n    return {'role': 'admin'}\n",
                        "frontend_file": "frontend.ts",
                        "backend_file": "backend.py",
                    },
                ),
            ]

            for tool, args in smoke:
                try:
                    payload = await _call(session, tool, args)
                    ok = _mcp_call_ok(payload)
                    checks.append(
                        ToolCheck(
                            tool,
                            ok,
                            "ok" if ok else json.dumps(_structured_data(payload))[:200],
                        )
                    )
                except Exception as e:
                    checks.append(ToolCheck(tool, False, str(e)))

            # --- Pro feature: rename_symbol MUST succeed ---
            try:
                rel_a = str(paths["a"].relative_to(project_root))
                payload = await _call(
                    session,
                    "rename_symbol",
                    {
                        "file_path": rel_a,
                        "target_type": "function",
                        "target_name": "add",
                        "new_name": "add2",
                        "create_backup": True,
                    },
                )
                data = _structured_data(payload)
                ok = _get_bool(data, "success", False)
                if ok:
                    content = paths["a"].read_text(encoding="utf-8")
                    ok = "def add2" in content
                checks.append(
                    ToolCheck(
                        "rename_symbol",
                        ok,
                        "ok" if ok else (data.get("error") or "unexpected result"),
                    )
                )
            except Exception as e:
                checks.append(ToolCheck("rename_symbol", False, f"call failed: {e}"))

            # --- Pro feature: update_symbol should succeed and edit file ---
            try:
                rel_a = str(paths["a"].relative_to(project_root))
                new_code = "def add2(a, b):\n    return a + b + 0\n"
                payload = await _call(
                    session,
                    "update_symbol",
                    {
                        "file_path": rel_a,
                        "target_type": "function",
                        "target_name": "add2",
                        "new_code": new_code,
                        "create_backup": True,
                    },
                )
                data = _structured_data(payload)
                ok = _get_bool(data, "success", False)
                if ok:
                    content = paths["a"].read_text(encoding="utf-8")
                    ok = "return a + b + 0" in content
                checks.append(
                    ToolCheck(
                        "update_symbol",
                        ok,
                        "ok" if ok else (data.get("error") or "unexpected result"),
                    )
                )
            except Exception as e:
                checks.append(ToolCheck("update_symbol", False, f"call failed: {e}"))

            # --- Pro limit: code_policy_check should exceed Community max_files ---
            try:
                payload = await _call(session, "code_policy_check", {"paths": [str(project_root)]})
                data = _structured_data(payload)
                # NOTE: code_policy_check may report `success=False` when violations exist.
                # For tier validation we only care that the tool executed and analyzed >100 files.
                ok = data.get("tier") == "pro"
                files_checked = int(data.get("files_checked") or 0)
                best = data.get("best_practices_violations") or []
                sec = data.get("security_warnings") or []

                # In Pro, we expect >100 files analyzed AND at least one pro-only category populated.
                ok = ok and (files_checked > 100) and (len(best) + len(sec) > 0)
                checks.append(
                    ToolCheck(
                        "code_policy_check_pro_limits",
                        ok,
                        f"tier={data.get('tier')} files_checked={files_checked} pro_hits={len(best)+len(sec)}",
                    )
                )
            except Exception as e:
                checks.append(ToolCheck("code_policy_check_pro_limits", False, str(e)))

            # --- Enterprise feature denial: compliance outputs must remain empty in Pro ---
            try:
                payload = await _call(
                    session,
                    "code_policy_check",
                    {
                        "paths": [str(project_root)],
                        "compliance_standards": ["soc2"],
                        "generate_report": True,
                    },
                )
                data = _structured_data(payload)
                ok = data.get("tier") == "pro"
                ok = ok and (data.get("compliance_reports") in (None, {}, []))
                ok = ok and (float(data.get("compliance_score") or 0.0) == 0.0)
                ok = ok and (data.get("pdf_report") in (None, ""))
                checks.append(
                    ToolCheck(
                        "enterprise_denied_code_policy_check",
                        ok,
                        "ok" if ok else json.dumps(data)[:240],
                    )
                )
            except Exception as e:
                checks.append(ToolCheck("enterprise_denied_code_policy_check", False, str(e)))

            # --- Enterprise feature denial: graph query flags must remain false in Pro ---
            try:
                payload = await _call(
                    session,
                    "get_graph_neighborhood",
                    {
                        "center_node_id": "python::pkg.a::function::add2",
                        "k": 2,
                        "max_nodes": 50,
                        "project_root": str(project_root),
                        "query": "MATCH (n)-[:calls]->(m:function) RETURN n, m",
                    },
                )
                data = _structured_data(payload)
                # Query language is Enterprise-only. In Pro we accept either a hard failure
                # or a successful response that explicitly reports unsupported query features.
                ok = data.get("query_supported") is False
                ok = ok and (data.get("traversal_rules_available") is False)
                ok = ok and (data.get("path_constraints_supported") is False)
                checks.append(
                    ToolCheck(
                        "enterprise_denied_graph_query",
                        ok,
                        "ok" if ok else json.dumps(data)[:240],
                    )
                )
            except Exception as e:
                checks.append(ToolCheck("enterprise_denied_graph_query", False, str(e)))

    width = max(len(c.name) for c in checks) if checks else 10
    failed = [c for c in checks if not c.ok]

    print("\n=== Code Scalpel MCP Pro-tier validation ===")
    for c in checks:
        status = "PASS" if c.ok else "FAIL"
        print(f"{status:<4}  {c.name:<{width}}  {c.notes}")

    print(f"\nTotal: {len(checks)} checks; Failed: {len(failed)}")

    if verbose and failed:
        print("\nFailed checks:")
        for c in failed:
            print(f"- {c.name}: {c.notes}")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
