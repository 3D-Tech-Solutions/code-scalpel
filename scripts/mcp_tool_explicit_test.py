"""Explicit MCP-first tool validation (tier + response config).

[20251228_TEST] This script validates tools through the MCP protocol (stdio),
not by calling Python tool handlers directly.

It is intentionally small and deterministic:
- Spins up a tiny synthetic project.
- Starts the MCP server over stdio.
- Calls a small representative tool set.
- Optionally exercises tier fallback, paid-tier capabilities, and response profiles.

Usage examples:
  # Community fallback (no license)
  python scripts/mcp_tool_explicit_test.py --tier pro --license-mode none --profile debug

  # Pro with HS256 test license (dev/test only)
  python scripts/mcp_tool_explicit_test.py --tier pro --license-mode hs256-test --profile debug

  # Enterprise with HS256 test license
  python scripts/mcp_tool_explicit_test.py --tier enterprise --license-mode hs256-test --profile debug
"""

from __future__ import annotations

import argparse
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

# [20251228_TEST] Canonical MCP tool registry (all tiers list all tools).
EXPECTED_ALL_TOOLS: set[str] = {
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
}


@dataclass(frozen=True)
class RunResult:
    tier_requested: str
    license_mode: str
    response_profile: str
    startup_ok: bool
    startup_error: str | None
    tools_ok: bool
    tool_results: dict[str, Any]


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _make_tiny_project(base_dir: Path) -> tuple[Path, str]:
    root = base_dir / "proj"
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

    target_file = str((root / "pkg" / "a.py").relative_to(root))
    return root, target_file


def _write_response_config(out_dir: Path, *, profile: str, source_repo_root: Path) -> None:
    cfg_src = source_repo_root / ".code-scalpel" / "response_config.json"
    cfg = json.loads(cfg_src.read_text(encoding="utf-8"))
    cfg.setdefault("global", {})
    cfg["global"]["profile"] = profile

    cfg_dir = out_dir / ".code-scalpel"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    (cfg_dir / "response_config.json").write_text(
        json.dumps(cfg, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _configure_license(
    env: dict[str, str],
    *,
    cwd: Path,
    tier: str,
    license_mode: str,
) -> None:
    # Clear any ambient license env that could pollute results.
    for k in [
        "CODE_SCALPEL_LICENSE_PATH",
        "CODE_SCALPEL_SECRET_KEY",
        "CODE_SCALPEL_ALLOW_HS256",
        "CODE_SCALPEL_LICENSE_CRL_PATH",
        "CODE_SCALPEL_LICENSE_CRL_JWT",
    ]:
        env.pop(k, None)

    lic_path = cwd / ".code-scalpel" / "license.jwt"
    if lic_path.exists():
        lic_path.unlink()

    if license_mode == "none":
        return

    if license_mode != "hs256-test":
        raise ValueError(f"Unsupported license_mode: {license_mode}")

    # [20251228_BUGFIX] This script can be run via an interpreter that has `mcp`
    # installed but not `code_scalpel` as a package. Ensure we can import from
    # the repo's `src/` directory.
    repo_root = _repo_root()
    src_root = repo_root / "src"
    if str(src_root) not in sys.path:
        sys.path.insert(0, str(src_root))

    from code_scalpel.licensing.jwt_generator import generate_license

    secret = "test-secret"
    token = generate_license(
        tier=tier,
        customer_id="tests@example.com",
        organization="Test Org",
        duration_days=7,
        algorithm="HS256",
        secret_key=secret,
        jti=f"mcp-explicit-{tier}",
    )

    lic_path.parent.mkdir(parents=True, exist_ok=True)
    lic_path.write_text(token + "\n", encoding="utf-8")

    env["CODE_SCALPEL_ALLOW_HS256"] = "1"
    env["CODE_SCALPEL_SECRET_KEY"] = secret


async def _run_once(
    *,
    tier: str,
    license_mode: str,
    profile: str,
    include_paid_capability_probe: bool,
) -> RunResult:
    repo_root = _repo_root()

    run_dir = Path(tempfile.mkdtemp(prefix="code_scalpel_mcp_explicit_"))
    project_root, _target_file = _make_tiny_project(run_dir)

    _write_response_config(run_dir, profile=profile, source_repo_root=repo_root)

    env = os.environ.copy()
    env["CODE_SCALPEL_TIER"] = tier

    # Ensure repo code is importable in subprocess
    src_root = repo_root / "src"
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = str(src_root) + (os.pathsep + existing if existing else "")

    _configure_license(env, cwd=run_dir, tier=tier, license_mode=license_mode)

    # [20251228_BUGFIX] Allow choosing a known-good Python for the server subprocess.
    # This helps when the developer has multiple Python installs with different
    # mcp/pydantic compatibility.
    server_python = os.environ.get("CODE_SCALPEL_MCP_PYTHON", sys.executable)

    params = StdioServerParameters(
        command=server_python,
        args=["-m", "code_scalpel.mcp.server", "--root", str(project_root)],
        env=env,
        cwd=run_dir,
    )

    tool_results: dict[str, Any] = {}
    tools_ok = False

    try:
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                tools_result = await session.list_tools()
                tool_names = {t.name for t in tools_result.tools}
                tools_ok = tool_names == EXPECTED_ALL_TOOLS

                # 1) Community-safe baseline
                tool_results["analyze_code"] = (
                    await session.call_tool(
                        "analyze_code",
                        {"code": "def f(x):\n    return x + 1\n", "language": "python"},
                    )
                ).model_dump()

                tool_results["security_scan"] = (
                    await session.call_tool(
                        "security_scan",
                        {
                            "code": 'def f(user_id):\n    query = f"SELECT * FROM users WHERE id = {user_id}"\n    cursor.execute(query)\n',
                        },
                    )
                ).model_dump()

                tool_results["unified_sink_detect"] = (
                    await session.call_tool(
                        "unified_sink_detect",
                        {"code": "eval(user_input)", "language": "python"},
                    )
                ).model_dump()

                # 2) Paid capability probe (cross-file deps) if requested.
                if include_paid_capability_probe:
                    tool_results["extract_code_cross_file"] = (
                        await session.call_tool(
                            "extract_code",
                            {
                                "target_type": "class",
                                "target_name": "PolicyEngine",
                                "file_path": str(project_root / "pkg" / "a.py"),
                                "include_context": False,
                                "include_cross_file_deps": True,
                            },
                        )
                    ).model_dump()

        startup_ok = True
        startup_error = None
    except Exception as e:
        startup_ok = False
        startup_error = f"{type(e).__name__}: {e}"

    return RunResult(
        tier_requested=tier,
        license_mode=license_mode,
        response_profile=profile,
        startup_ok=startup_ok,
        startup_error=startup_error,
        tools_ok=tools_ok,
        tool_results=tool_results,
    )


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--tier", choices=["community", "pro", "enterprise"], required=True)
    p.add_argument(
        "--license-mode",
        choices=["none", "hs256-test"],
        default="none",
        help="Use hs256-test only for local/dev validation.",
    )
    p.add_argument(
        "--profile",
        choices=["minimal", "standard", "debug"],
        default="debug",
        help="Response profile from .code-scalpel/response_config.json.",
    )
    p.add_argument(
        "--paid-probe",
        action="store_true",
        help="Also probe a paid-tier-only capability (cross-file deps).",
    )
    return p.parse_args()


async def main() -> int:
    args = _parse_args()

    result = await _run_once(
        tier=args.tier,
        license_mode=args.license_mode,
        profile=args.profile,
        include_paid_capability_probe=bool(args.paid_probe),
    )

    print(
        json.dumps(
            {
                "tier_requested": result.tier_requested,
                "license_mode": result.license_mode,
                "response_profile": result.response_profile,
                "startup_ok": result.startup_ok,
                "startup_error": result.startup_error,
                "tool_registry_matches_expected": result.tools_ok,
                "tools_ran": sorted(result.tool_results.keys()),
            },
            indent=2,
        )
    )

    # Exit codes:
    # - If Pro/Enterprise is requested with no license, fail-closed startup is expected.
    if args.license_mode == "none" and args.tier in {"pro", "enterprise"}:
        return 0 if not result.startup_ok else 2

    # Otherwise we expect startup to succeed and registry to match.
    if not result.startup_ok:
        return 3
    return 1 if not result.tools_ok else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
