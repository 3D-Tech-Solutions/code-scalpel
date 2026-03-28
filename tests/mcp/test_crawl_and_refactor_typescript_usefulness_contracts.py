"""Public usefulness-contract tests for TypeScript crawl/refactor slices.

[20260315_TEST] Keep the documented TypeScript slices honest at the MCP boundary:
- crawl_project: Contract Only discovery/summary behavior without deep TS semantics
- simulate_refactor: Bounded Useful safe/unsafe verdicts for obvious TS syntax
"""

from __future__ import annotations

from pathlib import Path

import pytest


pytestmark = pytest.mark.asyncio


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


async def test_crawl_project_typescript_is_contract_only(
    tmp_path: Path, pro_tier
) -> None:
    from code_scalpel.mcp.server import crawl_project

    root = tmp_path / "ts-proj"
    root.mkdir()
    _write(
        root / "src" / "utils.ts",
        "export function trimName(name: string): string { return name.trim(); }\n",
    )
    _write(
        root / "src" / "app.ts",
        "import { trimName } from './utils';\n"
        "export const run = (name: string): string => trimName(name);\n",
    )

    result = await crawl_project(root_path=str(root), include_report=False)

    assert result.success is True
    assert result.summary.total_files == 2
    assert result.language_breakdown is not None
    assert result.language_breakdown["typescript"] == 2
    assert all(file.functions == [] for file in result.files)
    assert all(file.classes == [] for file in result.files)
    assert any("./utils" in file.imports for file in result.files if file.path == "src/app.ts")


async def test_simulate_refactor_typescript_safe_change_is_bounded_useful(
    community_tier,
) -> None:
    from code_scalpel.mcp.server import simulate_refactor

    original_code = """
export function greet(name: string): string {
    return name;
}
"""
    new_code = """
export function greet(name: string): string {
    return name.trim();
}
"""

    result = await simulate_refactor(original_code=original_code, new_code=new_code)

    assert result.success is True
    assert result.is_safe is True
    assert result.status == "safe"
    assert result.error is None


async def test_simulate_refactor_typescript_detects_eval_regression(
    community_tier,
) -> None:
    from code_scalpel.mcp.server import simulate_refactor

    original_code = """
export function parseExpression(input: string): string {
    return input.trim();
}
"""
    new_code = """
export function parseExpression(input: string): unknown {
    return eval(input as string);
}
"""

    result = await simulate_refactor(original_code=original_code, new_code=new_code)

    assert result.success is True
    assert result.is_safe is False
    assert result.status == "unsafe"
    assert any(issue.type == "Code Injection" for issue in result.security_issues)