"""Polyglot routing tests for get_file_context.

[20260314_TEST] Verify extension-driven language routing for all 13 shipped
source languages and guard the current misclassification behavior explicitly.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from code_scalpel.mcp.helpers.context_helpers import _get_file_context_sync


@pytest.mark.parametrize(
    ("file_name", "code", "expected_language", "expected_functions", "expected_classes"),
    [
        (
            "sample.py",
            "def helper():\n    return 1\n\nclass Worker:\n    pass\n",
            "python",
            {"helper"},
            {"Worker"},
        ),
        (
            "sample.js",
            "export function run() { return 1; }\nexport class Worker {}\n",
            "javascript",
            {"run"},
            {"Worker"},
        ),
        (
            "sample.ts",
            "export function run(): number { return 1; }\nexport class Worker {}\n",
            "typescript",
            {"run"},
            {"Worker"},
        ),
        (
            "Sample.java",
            "public class Sample { public static void run() {} }\n",
            "java",
            {"run"},
            {"Sample"},
        ),
        (
            "sample.c",
            "#include <stdio.h>\nint run(void) { return 1; }\n",
            "c",
            {"run"},
            set(),
        ),
        (
            "sample.cpp",
            "#include <string>\nclass Worker { public: void run() {} };\n",
            "cpp",
            {"run"},
            {"Worker"},
        ),
        (
            "Sample.cs",
            "using System;\npublic class Sample { public void Run() {} }\n",
            "csharp",
            {"Run"},
            {"Sample"},
        ),
        (
            "sample.go",
            "package main\nfunc run() {}\n",
            "go",
            {"run"},
            set(),
        ),
        (
            "Sample.kt",
            "class Sample { fun run() {} }\n",
            "kotlin",
            {"run"},
            {"Sample"},
        ),
        (
            "sample.php",
            "<?php\nfunction run() { return 1; }\nclass Worker {}\n",
            "php",
            {"run"},
            {"Worker"},
        ),
        (
            "sample.rb",
            "class Worker\n  def run\n  end\nend\n",
            "ruby",
            {"run"},
            {"Worker"},
        ),
        (
            "Sample.swift",
            "class Sample { func run() {} }\n",
            "swift",
            {"run"},
            {"Sample"},
        ),
        (
            "sample.rs",
            "pub fn run() {}\n",
            "rust",
            {"run"},
            set(),
        ),
    ],
)
def test_get_file_context_routes_extensions_to_expected_language(
    tmp_path: Path,
    file_name: str,
    code: str,
    expected_language: str,
    expected_functions: set[str],
    expected_classes: set[str],
) -> None:
    source_file = tmp_path / file_name
    source_file.write_text(code, encoding="utf-8")

    result = _get_file_context_sync(str(source_file), capabilities={})

    assert result.success is True
    assert result.language == expected_language
    assert expected_functions.issubset({getattr(item, "name", item) for item in result.functions})
    assert expected_classes.issubset({getattr(item, "name", item) for item in result.classes})


def test_get_file_context_unknown_extension_returns_unsupported_language(
    tmp_path: Path,
) -> None:
    source_file = tmp_path / "sample.xyz"
    source_file.write_text("plain text\n", encoding="utf-8")

    result = _get_file_context_sync(str(source_file), capabilities={})

    assert result.success is False
    assert result.language == "unknown"
    assert "Unsupported language 'unknown'" in (result.error or "")


def test_get_file_context_python_code_with_javascript_extension_routes_as_javascript(
    tmp_path: Path,
) -> None:
    source_file = tmp_path / "looks_like_python.js"
    source_file.write_text("def helper():\n    return 1\n", encoding="utf-8")

    result = _get_file_context_sync(str(source_file), capabilities={})

    assert result.success is True
    assert result.language == "javascript"
    assert result.summary.startswith("Javascript module")


def test_get_file_context_javascript_code_with_python_extension_routes_as_python(
    tmp_path: Path,
) -> None:
    source_file = tmp_path / "looks_like_javascript.py"
    source_file.write_text("export function run() { return 1; }\n", encoding="utf-8")

    result = _get_file_context_sync(str(source_file), capabilities={})

    assert result.success is False
    assert result.language == "python"
    assert result.error == "Invalid Python syntax and sanitization failed."