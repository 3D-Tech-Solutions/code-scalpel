"""Public analyze_code polyglot matrix coverage.

[20260314_TEST] Verify the public analyze_code MCP surface succeeds for every
currently shipped programming language in the analyze_code contract.
"""

from __future__ import annotations

from importlib.util import find_spec

import pytest

pytestmark = pytest.mark.asyncio


_TREE_SITTER_MODULES: dict[str, str] = {
    "javascript": "tree_sitter_javascript",
    "typescript": "tree_sitter_typescript",
    "java": "tree_sitter_java",
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


def _parser_available(language: str) -> bool:
    """Return whether the parser runtime for a language is installed."""
    module_name = _TREE_SITTER_MODULES.get(language)
    return module_name is None or find_spec(module_name) is not None


@pytest.mark.parametrize(
    (
        "language",
        "code",
        "expected_functions",
        "expected_classes",
        "expected_class_methods",
        "expected_import",
    ),
    [
        (
            "python",
            "import math\n\ndef add(x, y):\n    return x + y\n",
            {"add"},
            set(),
            {},
            "math",
        ),
        (
            "javascript",
            "import util from './util.js';\nfunction add(x, y) { return x + y; }\n",
            {"add"},
            set(),
            {},
            "./util.js",
        ),
        (
            "typescript",
            "import { util } from './util';\nexport function add(x: number, y: number): number { return x + y; }\n",
            {"add"},
            set(),
            {},
            "./util",
        ),
        (
            "java",
            "import java.util.List;\npublic class Box { public int add(int x, int y) { return x + y; } }\n",
            {"add"},
            {"Box"},
            {},
            "java.util.List",
        ),
        (
            "c",
            "#include <stdio.h>\nint add(int x, int y) { return x + y; }\n",
            {"add"},
            set(),
            {},
            None,
        ),
        (
            "cpp",
            "#include <string>\nclass Box { public: int get() { return 1; } };\n",
            {"get"},
            {"Box"},
            {"Box": {"get"}},
            None,
        ),
        (
            "csharp",
            'using System;\nclass Program { static void Main() { Console.WriteLine("hi"); } }\n',
            {"Main"},
            {"Program"},
            {"Program": {"Main"}},
            None,
        ),
        (
            "go",
            'package main\nimport "fmt"\nfunc add(x int, y int) int { return x + y }\n',
            {"add"},
            set(),
            {},
            "fmt",
        ),
        (
            "kotlin",
            'class User { fun name(): String = "x" }\n',
            {"name"},
            {"User"},
            {"User": {"name"}},
            None,
        ),
        (
            "php",
            "<?php\nfunction hi() { return 1; }\n",
            {"hi"},
            set(),
            {},
            None,
        ),
        (
            "ruby",
            'class User\n  def name\n    "x"\n  end\nend\n',
            {"name"},
            {"User"},
            {"User": {"name"}},
            None,
        ),
        (
            "swift",
            'import Foundation\nclass User { func name() -> String { return "x" } }\n',
            {"name"},
            {"User"},
            {"User": {"name"}},
            "Foundation",
        ),
        (
            "rust",
            'use std::fmt;\nstruct User; impl User { fn name(&self) -> &str { "x" } }\n',
            {"name"},
            {"User"},
            {"User": {"name"}},
            "std::fmt",
        ),
    ],
)
async def test_public_analyze_code_polyglot_matrix(
    language: str,
    code: str,
    expected_functions: set[str],
    expected_classes: set[str],
    expected_class_methods: dict[str, set[str]],
    expected_import: str | None,
) -> None:
    """[20260314_TEST] Public analyze_code should honor the full shipped language matrix."""
    if not _parser_available(language):
        pytest.skip(
            f"Parser runtime for {language} is not installed in this interpreter"
        )

    from code_scalpel.mcp.server import analyze_code

    result = await analyze_code(code=code, language=language)

    assert result.success is True
    assert result.error is None
    assert result.language_detected == language
    assert expected_functions.issubset(set(result.functions))
    assert expected_classes.issubset(set(result.classes))
    raw_class_details = (result.data or {}).get("class_details", [])
    class_details = {
        class_info.get("name"): set(class_info.get("methods", []))
        for class_info in raw_class_details
        if isinstance(class_info, dict) and class_info.get("name")
    }
    for class_name, method_names in expected_class_methods.items():
        assert class_name in class_details
        assert method_names.issubset(class_details[class_name])
    assert result.tier_applied in {"community", "pro", "enterprise"}
    assert result.lines_of_code >= 1
    assert result.complexity >= 0
    if expected_import is not None:
        assert any(expected_import in import_name for import_name in result.imports)
