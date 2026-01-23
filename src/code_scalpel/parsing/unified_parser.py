"""
Unified parsing with deterministic error handling.

All parsing behavior controlled by .code-scalpel/response_config.json.
This ensures deterministic results: same input + same config = same output.
"""

from __future__ import annotations

import ast
import json
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from code_scalpel.utilities.source_sanitizer import sanitize_python_source


@dataclass
class SanitizationReport:
    """Report of code modifications during parsing."""

    was_sanitized: bool
    changes: list[str] = field(default_factory=list)
    original_code: str | None = None
    sanitized_code: str | None = None


@dataclass
class ParsingConfig:
    """Parsing configuration from response_config.json."""

    mode: str = "strict"  # "strict" or "permissive"
    allow_merge_conflicts: bool = False
    allow_templates: bool = False
    report_modifications: bool = True


class ParsingError(ValueError):
    """Raised when code cannot be parsed deterministically."""

    def __init__(
        self,
        message: str,
        *,
        location: str | None = None,
        suggestion: str | None = None,
    ):
        super().__init__(message)
        self.location = location
        self.suggestion = suggestion


def _load_parsing_config() -> ParsingConfig:
    """Load parsing configuration from response_config.json."""
    try:
        # Look for config in workspace root
        config_path = Path(".code-scalpel/response_config.json")
        if not config_path.exists():
            # Fallback to package root
            package_root = Path(__file__).parent.parent.parent.parent
            config_path = package_root / ".code-scalpel" / "response_config.json"

        if not config_path.exists():
            return ParsingConfig()  # Use defaults

        with open(config_path) as f:
            data = json.load(f)

        parsing = data.get("parsing", {})
        policy = parsing.get("sanitization_policy", {})

        return ParsingConfig(
            mode=parsing.get("mode", "strict"),
            allow_merge_conflicts=policy.get("allow_merge_conflicts", False),
            allow_templates=policy.get("allow_templates", False),
            report_modifications=policy.get("report_modifications", True),
        )
    except Exception:
        # If config loading fails, use strict defaults (fail-fast)
        return ParsingConfig()


def parse_python_code(
    code: str,
    *,
    filename: str | None = None,
    config: ParsingConfig | None = None,
) -> tuple[ast.AST, SanitizationReport]:
    """
    Parse Python code with deterministic error handling.

    Behavior controlled by response_config.json "parsing" section.

    Args:
        code: Python source code to parse
        filename: Optional filename for error messages (e.g., "myfile.py")
        config: Optional config override (uses response_config.json if None)

    Returns:
        (ast_tree, sanitization_report)

    Raises:
        ParsingError: When code cannot be parsed (in strict mode)
                     or when sanitization fails

    Examples:
        # Strict mode (default from response_config.json)
        >>> tree, report = parse_python_code("def foo(): pass")
        >>> assert not report.was_sanitized

        # With merge conflicts (fails in strict mode)
        >>> tree, report = parse_python_code("def foo():\\n<<<<<<< HEAD\\n    pass")
        ParsingError: Code contains merge conflict markers

        # With filename for better error messages
        >>> tree, report = parse_python_code("def broken(:", filename="myfile.py")
        ParsingError: Invalid Python syntax ... (location: "myfile.py:1")

        # Permissive mode (if configured)
        >>> tree, report = parse_python_code("def foo():\\n{{ var }}")
        >>> assert report.was_sanitized
        >>> assert "Jinja2" in report.changes[0]

    [20260119_FEATURE] Added filename parameter for better error context in MCP tools.
    """
    config = config or _load_parsing_config()
    report = SanitizationReport(was_sanitized=False)

    def _format_location(lineno: int | None) -> str | None:
        """Format error location with optional filename prefix."""
        if not lineno:
            return None
        if filename:
            return f"{filename}:{lineno}"
        return f"line {lineno}"

    # Try direct parse first
    try:
        tree = ast.parse(code, filename=filename or "<string>")
        return tree, report

    except SyntaxError as e:
        # In strict mode, fail immediately
        if config.mode == "strict":
            # Check if it's a known fixable issue
            if any(marker in code for marker in ["<<<<<<", "======", ">>>>>>"]):
                raise ParsingError(
                    f"Code contains merge conflict markers: {e}",
                    location=_format_location(e.lineno),
                    suggestion="Resolve merge conflicts before analysis. "
                    "Or set parsing.mode='permissive' in response_config.json",
                ) from e

            if "{{" in code or "{%" in code:
                raise ParsingError(
                    f"Code contains template syntax (Jinja2/Django): {e}",
                    location=_format_location(e.lineno),
                    suggestion="Extract pure Python code or set parsing.mode='permissive'",
                ) from e

            raise ParsingError(
                f"Invalid Python syntax: {e}",
                location=_format_location(e.lineno),
            ) from e

        # Permissive mode: try sanitization
        if not (config.allow_merge_conflicts or config.allow_templates):
            # Permissive but sanitization disabled
            raise ParsingError(
                f"Invalid Python syntax: {e}. " "Sanitization disabled in config.",
                location=_format_location(e.lineno),
            ) from e

        # Attempt sanitization
        sanitized, changed = sanitize_python_source(code)
        if not changed:
            raise ParsingError(
                f"Invalid Python syntax: {e}. " "Code could not be auto-sanitized.",
                location=_format_location(e.lineno),
            ) from e

        # Build report
        report.was_sanitized = True
        report.original_code = code
        report.sanitized_code = sanitized

        # Detailed change tracking
        changes = []
        if "<<<<<<" in code:
            changes.append("Stripped merge conflict markers (<<<<<<, ======, >>>>>>)")
        if "{{" in code:
            changes.append("Replaced Jinja2 expressions ({{ ... }}) with None")
        if "{%" in code or "{#" in code:
            changes.append("Stripped Jinja2 block statements ({% ... %})")

        report.changes = changes

        # Warn user if configured
        if config.report_modifications:
            msg = (
                "Code was auto-sanitized before parsing. "
                f"Changes: {'; '.join(changes)}. "
                "Analysis may not reflect actual code behavior."
            )
            warnings.warn(msg, SyntaxWarning, stacklevel=2)

        # Parse sanitized code
        try:
            tree = ast.parse(sanitized, filename=filename or "<string>")
            return tree, report
        except SyntaxError as e2:
            raise ParsingError(
                f"Invalid Python syntax even after sanitization: {e2}",
                location=_format_location(e2.lineno),
            ) from e2


def parse_javascript_code(
    code: str, *, is_typescript: bool = False, config: ParsingConfig | None = None
) -> tuple[Any, SanitizationReport]:
    """
    Parse JavaScript/TypeScript with tree-sitter and error validation.

    Args:
        code: JavaScript/TypeScript source code
        is_typescript: Whether to use TypeScript parser
        config: Optional config override

    Returns:
        (tree_sitter_tree, sanitization_report)

    Raises:
        ParsingError: When tree-sitter detects ERROR nodes (in strict mode)
    """
    config = config or _load_parsing_config()
    report = SanitizationReport(was_sanitized=False)

    try:
        from tree_sitter import Language, Parser

        if is_typescript:
            import tree_sitter_typescript as ts_ts

            lang = Language(ts_ts.language_typescript())
        else:
            import tree_sitter_javascript as ts_js

            lang = Language(ts_js.language())
    except ImportError as e:
        raise ParsingError(
            f"Tree-sitter not available: {e}",
            suggestion="Install tree-sitter: pip install tree-sitter tree-sitter-javascript",
        ) from e

    parser = Parser(lang)
    tree = parser.parse(bytes(code, "utf-8"))

    # Check for ERROR nodes (tree-sitter never raises exceptions)
    if config.mode == "strict" and tree.root_node.has_error:
        error_node = _find_first_error_node(tree.root_node)
        if error_node:
            line = error_node.start_point[0] + 1
            col = error_node.start_point[1]
            location = f"line {line}, column {col}"

            raise ParsingError(
                "JavaScript/TypeScript contains syntax errors",
                location=location,
                suggestion="Fix syntax errors or set parsing.mode='permissive'",
            )

        raise ParsingError("JavaScript/TypeScript parse failed with ERROR nodes in AST")

    return tree, report


def _find_first_error_node(node: Any) -> Any | None:
    """Recursively find first ERROR node in tree-sitter tree."""
    if node.type == "ERROR":
        return node
    for child in node.children:
        error = _find_first_error_node(child)
        if error:
            return error
    return None


# Backward compatibility aliases
def get_parsing_config() -> ParsingConfig:
    """Get current parsing configuration."""
    return _load_parsing_config()
