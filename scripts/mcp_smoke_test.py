"""Smoke-test Code Scalpel MCP tool handlers.

Runs each @mcp.tool() function directly (not over the MCP transport) with
minimal inputs and verifies it returns promptly with a structured result.

This file is intentionally lightweight and is meant for local verification.
"""

from __future__ import annotations

import asyncio
import json
import tempfile
from pathlib import Path


def _make_tiny_project() -> Path:
    root = Path(tempfile.mkdtemp(prefix="code_scalpel_mcp_smoke_"))
    (root / "pkg").mkdir(parents=True, exist_ok=True)

    (root / "pkg" / "__init__.py").write_text("", encoding="utf-8")

    (root / "pkg" / "b.py").write_text(
        """\
class Helper:
    def ping(self) -> str:
        return 'pong'
""",
        encoding="utf-8",
    )

    (root / "pkg" / "a.py").write_text(
        """\
from pkg.b import Helper

class PolicyEngine:
    def __init__(self) -> None:
        self.h = Helper()

    def run(self) -> str:
        return self.h.ping()
""",
        encoding="utf-8",
    )

    return root


async def main() -> int:
    from code_scalpel.mcp import server as mcp_server

    tiny_root = _make_tiny_project()
    target_file = str((tiny_root / "pkg" / "a.py").relative_to(tiny_root))

    repo_root = Path(__file__).resolve().parents[1]

    # Use callables so we don't create coroutines until we are ready to await.
    tests: list[tuple[str, callable[[], object]]] = [
        (
            "analyze_code",
            lambda: mcp_server.analyze_code(code="def foo():\n    return 1\n", language="python"),
        ),
        (
            "unified_sink_detect",
            lambda: mcp_server.unified_sink_detect(code="eval(user_input)", language="python"),
        ),
        (
            "type_evaporation_scan",
            lambda: mcp_server.type_evaporation_scan(
                frontend_code="const x: any = user;",
                backend_code="def f(x):\n    return x\n",
                frontend_file="frontend.ts",
                backend_file="backend.py",
            ),
        ),
        (
            "scan_dependencies",
            lambda: mcp_server.scan_dependencies(
                path=str(tiny_root),
                project_root=str(tiny_root),
                scan_vulnerabilities=False,
                include_dev=False,
                timeout=10.0,
            ),
        ),
        (
            "security_scan",
            lambda: mcp_server.security_scan(code="import os\nos.system('ls')\n", file_path=None),
        ),
        (
            "symbolic_execute",
            lambda: mcp_server.symbolic_execute(
                code="def f(x):\n    if x>0: return 1\n    return 0\n",
                max_paths=5,
            ),
        ),
        (
            "generate_unit_tests",
            lambda: mcp_server.generate_unit_tests(
                code="def add(a,b):\n    return a+b\n",
                framework="pytest",
            ),
        ),
        (
            "simulate_refactor",
            lambda: mcp_server.simulate_refactor(
                original_code="def a():\n    return 1\n",
                new_code="def a():\n    return 2\n",
                strict_mode=False,
            ),
        ),
        (
            "extract_code",
            lambda: mcp_server.extract_code(
                target_type="class",
                target_name="PolicyEngine",
                file_path=str(tiny_root / "pkg" / "a.py"),
                include_context=False,
                include_cross_file_deps=False,
            ),
        ),
        (
            "update_symbol",
            lambda: mcp_server.update_symbol(
                file_path=str(tiny_root / "pkg" / "a.py"),
                target_type="class",
                target_name="PolicyEngine",
                new_code="class PolicyEngine:\n    def run(self):\n        return 'ok'\n",
                create_backup=False,
            ),
        ),
        (
            "crawl_project",
            lambda: mcp_server.crawl_project(
                root_path=str(tiny_root),
                include_report=False,
            ),
        ),
        (
            "get_file_context",
            lambda: mcp_server.get_file_context(file_path=str(tiny_root / "pkg" / "a.py")),
        ),
        (
            "get_symbol_references",
            lambda: mcp_server.get_symbol_references(symbol_name="PolicyEngine", project_root=str(tiny_root)),
        ),
        (
            "get_call_graph",
            lambda: mcp_server.get_call_graph(project_root=str(tiny_root), entry_point=None, depth=5),
        ),
        (
            "get_graph_neighborhood",
            lambda: mcp_server.get_graph_neighborhood(
                center_node_id="PolicyEngine",
                k=1,
                max_nodes=25,
                project_root=str(tiny_root),
            ),
        ),
        (
            "get_project_map",
            lambda: mcp_server.get_project_map(project_root=str(tiny_root), include_complexity=False),
        ),
        (
            "get_cross_file_dependencies",
            lambda: mcp_server.get_cross_file_dependencies(
                target_file=target_file,
                target_symbol="PolicyEngine",
                project_root=str(tiny_root),
                max_depth=2,
                include_code=False,
                include_diagram=False,
            ),
        ),
        (
            "cross_file_security_scan",
            lambda: mcp_server.cross_file_security_scan(
                project_root=str(tiny_root),
                entry_points=[target_file],
                max_depth=2,
                include_diagram=False,
                timeout_seconds=15.0,
                max_modules=50,
            ),
        ),
        (
            "validate_paths",
            lambda: mcp_server.validate_paths(paths=["pkg/a.py", "pkg/b.py"], project_root=str(tiny_root)),
        ),
        (
            "verify_policy_integrity",
            lambda: mcp_server.verify_policy_integrity(
                policy_dir=str(repo_root / ".code-scalpel"), manifest_source="file"
            ),
        ),
    ]

    results: dict[str, dict] = {}
    failures: list[str] = []

    for name, make_call in tests:
        try:
            out = await asyncio.wait_for(make_call(), timeout=20)
            # pydantic models have model_dump
            if hasattr(out, "model_dump"):
                results[name] = out.model_dump()
            else:
                results[name] = json.loads(json.dumps(out, default=str))
        except Exception as e:
            failures.append(f"{name}: {type(e).__name__}: {e}")

    print(
        json.dumps(
            {
                "project_root": str(tiny_root),
                "failures": failures,
                "results_keys": sorted(results.keys()),
            },
            indent=2,
        )
    )

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
