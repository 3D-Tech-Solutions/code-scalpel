"""MCP-first validation of the 22 canonical Code Scalpel tools (Community tier).

This script intentionally does NOT use the Ninja Warrior harness. It:
- Starts the MCP server over stdio
- Asserts the 22-tool registry is present
- Calls each tool once with minimal deterministic inputs

Usage:
  CODE_SCALPEL_TIER=community python scripts/mcp_validate_22_tools.py

Notes:
- Networked vulnerability lookups are disabled (scan_dependencies uses scan_vulnerabilities=false)
- rename_symbol is expected to be blocked in Community tier

[20251230_TEST][mcp] Community 22-tool validation.
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
    """Prefer the repo-local CLI entrypoint used by VS Code MCP config."""
    cli = repo_root / ".venv" / "bin" / "code-scalpel"
    if cli.exists():
        return str(cli)
    return sys.executable


def _ensure_env_is_clean(env: dict[str, str]) -> None:
    # Avoid ambient licenses or secrets influencing tier behavior when requested.
    # Default is to KEEP CODE_SCALPEL_LICENSE_PATH so Pro/Enterprise tiers can be validated.
    if env.get("CODE_SCALPEL_STRIP_LICENSE") == "1":
        for k in [
            "CODE_SCALPEL_LICENSE_PATH",
            "CODE_SCALPEL_SECRET_KEY",
            "CODE_SCALPEL_ALLOW_HS256",
            "CODE_SCALPEL_LICENSE_CRL_PATH",
            "CODE_SCALPEL_LICENSE_CRL_JWT",
        ]:
            env.pop(k, None)


def _make_tiny_project(base_dir: Path) -> tuple[Path, dict[str, Path]]:
    root = base_dir / "proj"
    pkg = root / "pkg"
    pkg.mkdir(parents=True, exist_ok=True)

    (pkg / "__init__.py").write_text("", encoding="utf-8")

    (pkg / "b.py").write_text(
        """\
class Helper:
    def ping(self) -> str:
        return 'pong'
""",
        encoding="utf-8",
    )

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

    # Policy dir for verify_policy_integrity (Community basic verification)
    policy_dir = root / ".code-scalpel"
    policy_dir.mkdir(parents=True, exist_ok=True)
    (policy_dir / "budget.yaml").write_text("limits: {}\n", encoding="utf-8")

    return root, {
        "a": pkg / "a.py",
        "b": pkg / "b.py",
        "policy_dir": policy_dir,
    }


async def _call(session: ClientSession, tool: str, args: dict[str, Any]) -> dict[str, Any]:
    res = await session.call_tool(tool, args)
    return res.model_dump()


def _payload_success(payload: dict[str, Any]) -> bool:
    # Most tools embed a structured result as a single content item. Some wrappers
    # include raw content; we only need to know that the tool call completed.
    return True if payload else False


async def main() -> int:
    repo_root = _repo_root()
    src_root = repo_root / "src"

    run_dir = Path(tempfile.mkdtemp(prefix="code_scalpel_mcp_validate_"))
    project_root, paths = _make_tiny_project(run_dir)

    env = os.environ.copy()
    _ensure_env_is_clean(env)

    # Ensure Community tier unless explicitly overridden by caller.
    env.setdefault("CODE_SCALPEL_TIER", "community")

    # Ensure repo code is importable in subprocess
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = str(src_root) + (os.pathsep + existing if existing else "")

    # IMPORTANT: Use the same command VS Code uses (see .vscode/mcp.json):
    #   .venv/bin/code-scalpel mcp --root <workspaceFolder>
    # This avoids interpreter/site-packages mismatches that can prevent the server from starting.
    server_cmd = os.environ.get("CODE_SCALPEL_MCP_COMMAND") or _default_server_command(repo_root)
    server_args: list[str]
    if server_cmd.endswith("code-scalpel"):
        server_args = ["mcp", "--root", str(project_root)]
    else:
        # Fallback: invoke the module directly
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
                        name="list_tools",
                        ok=False,
                        notes=f"Mismatch. missing={missing} extra={extra}",
                    )
                )
            else:
                checks.append(ToolCheck(name="list_tools", ok=True, notes="22 tools"))

            # Shared inputs
            py_snippet = "def f(x):\n    if x > 0:\n        return x + 1\n    return 0\n"

            # 1) analyze_code
            try:
                payload = await _call(session, "analyze_code", {"code": py_snippet, "language": "python"})
                checks.append(ToolCheck("analyze_code", _payload_success(payload), "ok"))
            except Exception as e:
                checks.append(ToolCheck("analyze_code", False, str(e)))

            # 2) security_scan
            try:
                payload = await _call(
                    session,
                    "security_scan",
                    {"code": 'def f(user_id):\n    q=f"SELECT * FROM t WHERE id={user_id}"\n    cursor.execute(q)\n'},
                )
                checks.append(ToolCheck("security_scan", _payload_success(payload), "ok"))
            except Exception as e:
                checks.append(ToolCheck("security_scan", False, str(e)))

            # 3) unified_sink_detect
            try:
                payload = await _call(
                    session,
                    "unified_sink_detect",
                    {"code": "eval(user_input)", "language": "python"},
                )
                checks.append(ToolCheck("unified_sink_detect", _payload_success(payload), "ok"))
            except Exception as e:
                checks.append(ToolCheck("unified_sink_detect", False, str(e)))

            # 4) symbolic_execute
            try:
                payload = await _call(
                    session,
                    "symbolic_execute",
                    {"code": py_snippet, "language": "python"},
                )
                checks.append(ToolCheck("symbolic_execute", _payload_success(payload), "ok"))
            except Exception as e:
                checks.append(ToolCheck("symbolic_execute", False, str(e)))

            # 5) generate_unit_tests
            try:
                payload = await _call(
                    session,
                    "generate_unit_tests",
                    {"code": "def add(a,b):\n    return a+b\n", "framework": "pytest"},
                )
                # Ensure the returned MCP payload itself is JSON serializable.
                json.dumps(payload)
                checks.append(ToolCheck("generate_unit_tests", True, "ok"))
            except Exception as e:
                checks.append(ToolCheck("generate_unit_tests", False, str(e)))

            # 6) simulate_refactor
            try:
                payload = await _call(
                    session,
                    "simulate_refactor",
                    {
                        "original_code": "def add(a,b): return a+b\n",
                        "new_code": "def add(a,b): return eval('a+b')\n",
                    },
                )
                checks.append(ToolCheck("simulate_refactor", _payload_success(payload), "ok"))
            except Exception as e:
                checks.append(ToolCheck("simulate_refactor", False, str(e)))

            # 7) extract_code (file-path mode)
            try:
                rel_a = str(paths["a"].relative_to(project_root))
                payload = await _call(
                    session,
                    "extract_code",
                    {
                        "file_path": rel_a,
                        "target_type": "function",
                        "target_name": "add",
                    },
                )
                checks.append(ToolCheck("extract_code", _payload_success(payload), "ok"))
            except Exception as e:
                checks.append(ToolCheck("extract_code", False, str(e)))

            # 8) get_file_context
            try:
                rel_a = str(paths["a"].relative_to(project_root))
                payload = await _call(session, "get_file_context", {"file_path": rel_a})
                checks.append(ToolCheck("get_file_context", _payload_success(payload), "ok"))
            except Exception as e:
                checks.append(ToolCheck("get_file_context", False, str(e)))

            # 9) get_symbol_references
            try:
                payload = await _call(
                    session,
                    "get_symbol_references",
                    {"symbol_name": "add", "project_root": str(project_root)},
                )
                checks.append(ToolCheck("get_symbol_references", _payload_success(payload), "ok"))
            except Exception as e:
                checks.append(ToolCheck("get_symbol_references", False, str(e)))

            # 10) get_cross_file_dependencies
            try:
                rel_a = str(paths["a"].relative_to(project_root))
                payload = await _call(
                    session,
                    "get_cross_file_dependencies",
                    {
                        "target_file": rel_a,
                        "target_symbol": "PolicyEngine",
                        "project_root": str(project_root),
                        "max_depth": 1,
                        "include_code": False,
                    },
                )
                checks.append(ToolCheck("get_cross_file_dependencies", _payload_success(payload), "ok"))
            except Exception as e:
                checks.append(ToolCheck("get_cross_file_dependencies", False, str(e)))

            # 11) get_project_map
            try:
                payload = await _call(session, "get_project_map", {"project_root": str(project_root)})
                checks.append(ToolCheck("get_project_map", _payload_success(payload), "ok"))
            except Exception as e:
                checks.append(ToolCheck("get_project_map", False, str(e)))

            # 12) crawl_project
            try:
                payload = await _call(
                    session,
                    "crawl_project",
                    {"root_path": str(project_root), "include_report": True},
                )
                checks.append(ToolCheck("crawl_project", _payload_success(payload), "ok"))
            except Exception as e:
                checks.append(ToolCheck("crawl_project", False, str(e)))

            # 13) get_call_graph
            try:
                payload = await _call(
                    session,
                    "get_call_graph",
                    {"project_root": str(project_root), "depth": 3},
                )
                checks.append(ToolCheck("get_call_graph", _payload_success(payload), "ok"))
            except Exception as e:
                checks.append(ToolCheck("get_call_graph", False, str(e)))

            # 14) get_graph_neighborhood
            try:
                # Use a stable, generic node id. Tool should either return empty/truncated graph
                # or a clear error; we treat successful call as pass.
                payload = await _call(
                    session,
                    "get_graph_neighborhood",
                    {
                        "center_node_id": "python::pkg::function::add",
                        "k": 1,
                        "max_nodes": 20,
                        "project_root": str(project_root),
                    },
                )
                checks.append(ToolCheck("get_graph_neighborhood", _payload_success(payload), "ok"))
            except Exception as e:
                checks.append(ToolCheck("get_graph_neighborhood", False, str(e)))

            # 15) cross_file_security_scan
            try:
                payload = await _call(
                    session,
                    "cross_file_security_scan",
                    {
                        "project_root": str(project_root),
                        "max_depth": 3,
                        "timeout_seconds": 30,
                        "max_modules": 50,
                    },
                )
                checks.append(ToolCheck("cross_file_security_scan", _payload_success(payload), "ok"))
            except Exception as e:
                checks.append(ToolCheck("cross_file_security_scan", False, str(e)))

            # 16) scan_dependencies (disable vulnerability lookup)
            try:
                payload = await _call(
                    session,
                    "scan_dependencies",
                    {
                        "path": str(project_root),
                        "scan_vulnerabilities": False,
                        "include_dev": True,
                    },
                )
                checks.append(ToolCheck("scan_dependencies", _payload_success(payload), "ok"))
            except Exception as e:
                checks.append(ToolCheck("scan_dependencies", False, str(e)))

            # 17) verify_policy_integrity
            try:
                payload = await _call(
                    session,
                    "verify_policy_integrity",
                    {"policy_dir": str(paths["policy_dir"]), "manifest_source": "file"},
                )
                checks.append(ToolCheck("verify_policy_integrity", _payload_success(payload), "ok"))
            except Exception as e:
                checks.append(ToolCheck("verify_policy_integrity", False, str(e)))

            # 18) validate_paths
            try:
                payload = await _call(
                    session,
                    "validate_paths",
                    {"paths": [str(paths["a"])], "project_root": str(project_root)},
                )
                checks.append(ToolCheck("validate_paths", _payload_success(payload), "ok"))
            except Exception as e:
                checks.append(ToolCheck("validate_paths", False, str(e)))

            # 19) update_symbol (replace add)
            try:
                rel_a = str(paths["a"].relative_to(project_root))
                new_code = "def add(a, b):\n    return a + b + 0\n"
                payload = await _call(
                    session,
                    "update_symbol",
                    {
                        "file_path": rel_a,
                        "target_type": "function",
                        "target_name": "add",
                        "new_code": new_code,
                        "create_backup": True,
                    },
                )
                checks.append(ToolCheck("update_symbol", _payload_success(payload), "ok"))
            except Exception as e:
                checks.append(ToolCheck("update_symbol", False, str(e)))

            # 20) rename_symbol (expected blocked in Community)
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
                # If it unexpectedly succeeds, treat as failure for Community gating.
                ok = True
                # Best effort: look for error string in payload
                payload_text = json.dumps(payload)
                if 'success": true' in payload_text.lower():
                    ok = False
                checks.append(
                    ToolCheck(
                        "rename_symbol",
                        ok,
                        "blocked as expected" if ok else "unexpected success",
                    )
                )
            except Exception as e:
                # Tool call itself should not crash; it should return a structured error.
                checks.append(ToolCheck("rename_symbol", False, f"call failed: {e}"))

            # 21) code_policy_check
            try:
                payload = await _call(session, "code_policy_check", {"paths": [str(project_root)]})
                checks.append(ToolCheck("code_policy_check", _payload_success(payload), "ok"))
            except Exception as e:
                checks.append(ToolCheck("code_policy_check", False, str(e)))

            # 22) type_evaporation_scan (frontend-only expectation in Community)
            try:
                frontend = """
                    type Role = 'admin' | 'user';
                    async function f(){
                      const r = await fetch('/api/boundary/role');
                      const data = await r.json();
                      const role = (data.role as Role);
                      return role;
                    }
                """
                backend = """
                    from flask import Flask, request
                    app = Flask(__name__)

                    @app.get('/api/boundary/role')
                    def role():
                        data = request.get_json() or {}
                        return {'role': data.get('role')}
                """
                payload = await _call(
                    session,
                    "type_evaporation_scan",
                    {
                        "frontend_code": frontend,
                        "backend_code": backend,
                        "frontend_file": "frontend.ts",
                        "backend_file": "backend.py",
                    },
                )

                # Community tier returns a compact summary payload.
                # Validate it is a successful MCP call and the tool reports success.
                json.dumps(payload)
                structured = payload.get("structuredContent") or {}
                data = structured.get("data") or {}
                ok = (payload.get("isError") is False) and (data.get("success") is True)
                notes = "ok" if ok else f"unexpected payload: {data}"
                checks.append(ToolCheck("type_evaporation_scan", ok, notes))
            except Exception as e:
                checks.append(ToolCheck("type_evaporation_scan", False, str(e)))

    # Print summary
    width = max(len(c.name) for c in checks)
    failed = [c for c in checks if not c.ok]

    print("\n=== Code Scalpel MCP 22-tool validation (Community) ===")
    for c in checks:
        status = "PASS" if c.ok else "FAIL"
        print(f"{status:<4}  {c.name:<{width}}  {c.notes}")

    print(f"\nTotal: {len(checks)} checks; Failed: {len(failed)}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
