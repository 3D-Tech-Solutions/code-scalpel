"""Regression coverage for CodeAnalyzer polyglot language wiring.

[20260313_TEST] Verifies that the shared analyzer path honors explicit language
hints for every analyze_code polyglot language instead of relying on fragile
auto-detection fallbacks.
"""

from __future__ import annotations

from importlib.util import find_spec

import pytest

from code_scalpel.analysis.code_analyzer import AnalysisLanguage, CodeAnalyzer


_TREE_SITTER_MODULES: dict[str, str] = {
    "c": "tree_sitter_c",
    "cpp": "tree_sitter_cpp",
    "csharp": "tree_sitter_c_sharp",
    "go": "tree_sitter_go",
    "kotlin": "tree_sitter_kotlin",
    "php": "tree_sitter_php",
    "ruby": "tree_sitter_ruby",
    "swift": "tree_sitter_swift",
    "rust": "tree_sitter_rust",
}


@pytest.mark.parametrize(
    ("language", "filepath", "code", "expected_functions", "expected_classes"),
    [
        ("c", "sample.c", "int add(int a, int b) { return a + b; }", {"add"}, set()),
        (
            "cpp",
            "sample.cpp",
            "class Box { public: int get() { return 1; } };",
            {"Box.get"},
            {"Box"},
        ),
        (
            "csharp",
            "Program.cs",
            "using System; class Program { static void Main() { Console.WriteLine(\"hi\"); } }",
            {"Program.Main"},
            {"Program"},
        ),
        (
            "go",
            "sample.go",
            "package main\nfunc add(a int, b int) int { return a + b }",
            {"add"},
            set(),
        ),
        (
            "kotlin",
            "sample.kt",
            'class User { fun name(): String = "x" }',
            {"User.name"},
            {"User"},
        ),
        (
            "php",
            "sample.php",
            "<?php\nfunction hi() { return 1; }",
            {"hi"},
            set(),
        ),
        (
            "ruby",
            "sample.rb",
            'class User\n  def name\n    "x"\n  end\nend',
            {"User.name"},
            {"User"},
        ),
        (
            "swift",
            "sample.swift",
            'class User { func name() -> String { return "x" } }',
            {"User.name"},
            {"User"},
        ),
        (
            "rust",
            "sample.rs",
            'struct User; impl User { fn name(&self) -> &str { "x" } }',
            {"User.name"},
            {"User"},
        ),
    ],
)
def test_code_analyzer_explicit_language_hints_cover_polyglot_matrix(
    language: str,
    filepath: str,
    code: str,
    expected_functions: set[str],
    expected_classes: set[str],
) -> None:
    """[20260313_TEST] Explicit language hints should parse through the matching IR normalizer."""
    module_name = _TREE_SITTER_MODULES[language]
    if find_spec(module_name) is None:
        pytest.skip(f"{module_name} not installed in this interpreter")

    analyzer = CodeAnalyzer()

    result = analyzer.analyze(code, language=language, filepath=filepath)

    assert result.language == language
    assert not result.errors
    assert expected_functions.issubset(set(result.functions))
    assert expected_classes.issubset(set(result.classes))


def test_analysis_language_enum_tracks_polyglot_analyze_code_languages() -> None:
    """[20260313_TEST] CodeAnalyzer enum should stay aligned with analyze_code polyglot support."""
    assert {member.value for member in AnalysisLanguage} >= {
        "python",
        "javascript",
        "typescript",
        "java",
        "c",
        "cpp",
        "csharp",
        "go",
        "kotlin",
        "php",
        "ruby",
        "swift",
        "rust",
        "auto",
    }