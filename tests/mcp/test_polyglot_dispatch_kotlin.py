"""Regression tests for Kotlin static-tool dispatch wiring."""

from pathlib import Path
from types import SimpleNamespace


def test_kotlin_static_dispatch_calls_detekt_and_ktlint(monkeypatch, tmp_path):
    """[20260306_TEST] Kotlin static dispatch should expose detekt and ktlint."""
    from code_scalpel.code_parsers.kotlin_parsers.kotlin_parsers_Detekt import (
        DetektParser,
    )
    from code_scalpel.code_parsers.kotlin_parsers.kotlin_parsers_ktlint import (
        KtlintParser,
    )
    from code_scalpel.mcp.helpers.polyglot_dispatch import run_static_tools

    file_path = tmp_path / "Sample.kt"
    file_path.write_text("fun greet() = Unit\n", encoding="utf-8")

    monkeypatch.setattr(
        DetektParser,
        "execute_detekt",
        lambda self, project_path: [
            SimpleNamespace(tool="detekt", path=str(project_path))
        ],
    )
    monkeypatch.setattr(
        KtlintParser,
        "execute_ktlint",
        lambda self, project_path: [
            SimpleNamespace(tool="ktlint", path=str(project_path))
        ],
    )

    findings = run_static_tools(str(file_path), ["detekt", "ktlint"], "community")

    tools = {finding.get("tool") for finding in findings}
    assert tools == {"detekt", "ktlint"}
    assert all(Path(finding["path"]).suffix == ".kt" for finding in findings)