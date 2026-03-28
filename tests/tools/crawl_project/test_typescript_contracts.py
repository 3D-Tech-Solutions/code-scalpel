from __future__ import annotations

from pathlib import Path


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_crawl_project_sync_preserves_typescript_summary_contract(tmp_path: Path) -> None:
    from code_scalpel.mcp.helpers.context_helpers import _crawl_project_sync

    root = tmp_path / "ts-helper"
    root.mkdir()
    _write(
        root / "src" / "math.ts",
        "export const add = (a: number, b: number): number => a + b;\n",
    )
    _write(
        root / "src" / "index.ts",
        "import { add } from './math';\n"
        "export const run = (): number => add(1, 2);\n",
    )

    result = _crawl_project_sync(
        root_path=str(root),
        include_report=True,
        capabilities=set(),
    )

    assert result.success is True
    assert result.summary.total_files == 2
    assert result.language_breakdown is not None
    assert result.language_breakdown["typescript"] == 2
    assert all(file.functions == [] for file in result.files)
    assert all(file.classes == [] for file in result.files)
    assert "Project Analysis Report" in result.markdown_report
    assert "Project Python Analysis Report" not in result.markdown_report
    index_result = next(file for file in result.files if file.path == "src/index.ts")
    assert "./math" in index_result.imports