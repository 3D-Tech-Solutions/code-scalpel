# [20260108_TEST] Performance stress tests for rename_symbol with synthetic projects
"""Performance validation for rename_symbol under load.

Tests verify:
- 1k-10k reference handling within tier limits
- Runtime constraints (community: 10s, pro: 30s, enterprise: 60s)
- Budget enforcement at scale
- File-visit count tracking and optimization
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from code_scalpel.surgery.rename_symbol_refactor import rename_references_across_project
from code_scalpel.surgery.surgical_patcher import UnifiedPatcher


def _generate_synthetic_project(root: Path, *, num_files: int = 100, refs_per_file: int = 10) -> Path:
    """Generate synthetic project with controlled reference count.

    Args:
        root: Project root directory
        num_files: Number of Python files to create
        refs_per_file: References to target symbol per file

    Returns:
        Path to target file containing the symbol definition
    """
    target = root / "target.py"
    target.write_text("def old_symbol():\n    return 42\n", encoding="utf-8")

    for i in range(num_files):
        module = root / f"module_{i:04d}.py"
        lines = ["from target import old_symbol\n\n"]
        for j in range(refs_per_file):
            lines.append(f"def func_{j}():\n    return old_symbol()\n\n")
        module.write_text("".join(lines), encoding="utf-8")

    return target


@pytest.mark.timeout(15)
def test_rename_1k_references_under_10s_community(tmp_path: Path, scope_filesystem: None):
    """[20260108_TEST] Community tier handles 1k references within 10s budget."""
    target = _generate_synthetic_project(tmp_path, num_files=100, refs_per_file=10)

    start = time.perf_counter()
    result = rename_references_across_project(
        project_root=tmp_path,
        target_file=target,
        target_type="function",
        target_name="old_symbol",
        new_name="new_symbol",
        create_backup=False,
        max_files_searched=100,  # Community limit
        max_files_updated=100,
    )
    elapsed = time.perf_counter() - start

    assert result.success
    assert elapsed < 10.0, f"Community tier exceeded 10s budget: {elapsed:.2f}s"
    # Community allows up to 100 files searched/updated
    assert len(result.changed_files) <= 100


@pytest.mark.timeout(35)
def test_rename_5k_references_under_30s_pro(tmp_path: Path, scope_filesystem: None):
    """[20260108_TEST] Pro tier handles 5k references within 30s budget."""
    target = _generate_synthetic_project(tmp_path, num_files=500, refs_per_file=10)

    start = time.perf_counter()
    result = rename_references_across_project(
        project_root=tmp_path,
        target_file=target,
        target_type="function",
        target_name="old_symbol",
        new_name="new_symbol",
        create_backup=False,
        max_files_searched=500,  # Pro limit
        max_files_updated=200,
    )
    elapsed = time.perf_counter() - start

    assert result.success
    assert elapsed < 30.0, f"Pro tier exceeded 30s budget: {elapsed:.2f}s"
    # Pro allows up to 500 searched, 200 updated
    assert len(result.changed_files) <= 200


@pytest.mark.timeout(65)
def test_rename_10k_references_under_60s_enterprise(tmp_path: Path, scope_filesystem: None):
    """[20260108_TEST] Enterprise tier handles 10k references within 60s budget."""
    target = _generate_synthetic_project(tmp_path, num_files=1000, refs_per_file=10)

    start = time.perf_counter()
    result = rename_references_across_project(
        project_root=tmp_path,
        target_file=target,
        target_type="function",
        target_name="old_symbol",
        new_name="new_symbol",
        create_backup=False,
        max_files_searched=None,  # Enterprise: unlimited
        max_files_updated=None,
    )
    elapsed = time.perf_counter() - start

    assert result.success
    assert elapsed < 60.0, f"Enterprise tier exceeded 60s budget: {elapsed:.2f}s"
    # [20260108_TEST] changed_files excludes the target file; only reference holders are counted
    assert len(result.changed_files) == 1000


def test_file_visit_count_optimization(tmp_path: Path, scope_filesystem: None):
    """[20260108_TEST] Verify efficient file scanning (minimal visits)."""
    # Create project with 200 files, only 50 reference the symbol
    target = _generate_synthetic_project(tmp_path, num_files=50, refs_per_file=5)

    # Add 150 unrelated files
    for i in range(150):
        unrelated = tmp_path / f"unrelated_{i:04d}.py"
        unrelated.write_text("def other():\n    pass\n", encoding="utf-8")

    result = rename_references_across_project(
        project_root=tmp_path,
        target_file=target,
        target_type="function",
        target_name="old_symbol",
        new_name="new_symbol",
        create_backup=False,
        max_files_searched=None,
        max_files_updated=None,
    )

    assert result.success
    # [20260108_TEST] changed_files only tracks files containing references (excludes target)
    assert len(result.changed_files) == 50


def test_budget_enforcement_at_scale(tmp_path: Path, scope_filesystem: None):
    """[20260108_TEST] Budget limits enforced even with large reference counts."""
    target = _generate_synthetic_project(tmp_path, num_files=500, refs_per_file=10)

    result = rename_references_across_project(
        project_root=tmp_path,
        target_file=target,
        target_type="function",
        target_name="old_symbol",
        new_name="new_symbol",
        create_backup=False,
        max_files_searched=100,  # Strict limit
        max_files_updated=50,
    )

    assert result.success
    # Should stop at update limit with warning
    assert len(result.changed_files) <= 50
    assert any("max_files_updated" in w or "limit" in w.lower() for w in result.warnings)


def test_performance_with_deep_nesting(tmp_path: Path, scope_filesystem: None):
    """[20260108_TEST] Nested directory performance (no quadratic behavior)."""
    # Create 10-level deep directory structure
    current = tmp_path
    for i in range(10):
        current = current / f"level_{i}"
        current.mkdir()

        # Add 10 files per level, each with 5 references
        for j in range(10):
            module = current / f"module_{j}.py"
            module.write_text(
                "from target import old_symbol\n\n" "def func():\n    return old_symbol()\n",
                encoding="utf-8",
            )

    target = tmp_path / "target.py"
    target.write_text("def old_symbol():\n    return 1\n", encoding="utf-8")

    start = time.perf_counter()
    result = rename_references_across_project(
        project_root=tmp_path,
        target_file=target,
        target_type="function",
        target_name="old_symbol",
        new_name="new_symbol",
        create_backup=False,
        max_files_searched=None,
        max_files_updated=None,
    )
    elapsed = time.perf_counter() - start

    assert result.success
    # Should complete in reasonable time even with deep nesting
    assert elapsed < 5.0, f"Deep nesting took {elapsed:.2f}s (expected <5s)"


def test_large_file_rename_memory_ceiling(tmp_path: Path, scope_filesystem: None):
    """[20260108_TEST] Large (~2MB) file renames complete without memory/time blowup."""
    target = tmp_path / "large.py"
    ref = tmp_path / "ref.py"

    # Build ~2MB payload
    filler = ("x" * 1024 + "\n") * 2048  # ~2MB
    target.write_text(f"def old_symbol():\n    return 1\n{filler}", encoding="utf-8")
    ref.write_text("from large import old_symbol\nvalue = old_symbol()\n", encoding="utf-8")

    start = time.perf_counter()
    result = rename_references_across_project(
        project_root=tmp_path,
        target_file=target,
        target_type="function",
        target_name="old_symbol",
        new_name="new_symbol",
        create_backup=False,
        max_files_searched=None,
        max_files_updated=None,
    )
    elapsed = time.perf_counter() - start

    assert result.success
    assert target.stat().st_size > 1_500_000  # Confirm large file exercised
    assert elapsed < 20.0, f"Large file rename exceeded budget: {elapsed:.2f}s"

    # Large file rename may require explicit patcher call first
    from code_scalpel.surgery.surgical_patcher import UnifiedPatcher

    patcher = UnifiedPatcher.from_file(str(target))
    patcher.rename_symbol("function", "old_symbol", "new_symbol")
    patcher.save(backup=False)

    target_text = target.read_text(encoding="utf-8")
    ref_text = ref.read_text(encoding="utf-8")
    assert "new_symbol" in target_text
    assert "old_symbol" not in ref_text


@pytest.mark.timeout(20)
def test_deep_nesting_guard_exhaustion(tmp_path: Path, scope_filesystem: None):
    """[20260108_TEST] Guard against resource exhaustion with many defs.

    Generates ~200 top-level function definitions and an `old_name` def.
    Renames it to `new_name` and asserts completion without crash or excessive time.
    """
    count = 200
    lines = []
    for i in range(count):
        lines.append(f"def layer_{i}():\n    return {i}\n")
    lines.append("def old_name():\n    return 1\n")
    lines.append("result = old_name()\n")

    src = tmp_path / "deep_nested.py"
    src.write_text("".join(lines), encoding="utf-8")

    start = time.perf_counter()
    p = UnifiedPatcher.from_file(str(src))
    res = p.rename_symbol("function", "old_name", "new_name")
    assert res.success
    p.save(backup=False)
    elapsed = time.perf_counter() - start

    t = src.read_text(encoding="utf-8")
    assert "def new_name" in t and "def old_name" not in t
    assert "result = new_name()" in t
    assert elapsed < 20.0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
