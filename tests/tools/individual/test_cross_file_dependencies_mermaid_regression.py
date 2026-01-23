from __future__ import annotations

from pathlib import Path

from code_scalpel.mcp.server import _get_cross_file_dependencies_sync


def test_cross_file_dependencies_include_diagram_does_not_crash(tmp_path: Path) -> None:
    # Minimal 2-file project with an import edge a -> b
    (tmp_path / "b.py").write_text(
        "def bar():\n    return 123\n",
        encoding="utf-8",
    )
    (tmp_path / "a.py").write_text(
        "from b import bar\n\n\n" "def foo():\n" "    return bar()\n",
        encoding="utf-8",
    )

    result = _get_cross_file_dependencies_sync(
        target_file="a.py",
        target_symbol="foo",
        project_root=str(tmp_path),
        max_depth=2,
        include_code=False,
        include_diagram=True,
        confidence_decay_factor=0.9,
    )

    assert result.success is True
    assert result.target_file == "a.py"
    assert result.mermaid.startswith("graph TD")
    assert "-->" in result.mermaid or "[a_py]" in result.mermaid
