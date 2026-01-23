"""
Surgical Patcher - Precision code modification for safe LLM-driven refactoring.

# [20251224_REFACTOR] Moved from code_scalpel/surgical_patcher.py to
# code_scalpel/surgery/surgical_patcher.py as part of Issue #2
# in PROJECT_REORG_REFACTOR.md Phase 1.

This module provides surgical replacement of code elements (functions, classes, methods)
in source files. Instead of having LLMs output entire files (risking accidental deletions),
the LLM provides only the new code for a specific symbol, and we handle the replacement.

Key Principle: "Replace the function, not the file."

Usage:
    from code_scalpel.surgery import SurgicalPatcher

    patcher = SurgicalPatcher.from_file("src/utils.py")

    # Replace a function
    result = patcher.update_function("calculate_tax", new_code)

    # Replace a class
    result = patcher.update_class("TaxCalculator", new_class_code)

    # Replace a method within a class
    result = patcher.update_method("TaxCalculator", "compute", new_method_code)

    # Write changes back to file
    patcher.save()

Safety Features:
    - Creates backup before modification
    - Validates new code parses correctly
    - Preserves surrounding code exactly
    - Atomic write (temp file + rename)

================================

COMMUNITY (Current & Planned):

PRO (Enhanced Features):

ENTERPRISE (Advanced Capabilities):
"""

from __future__ import annotations

import ast
import io
import keyword
import os
import re
import shutil
import tempfile
import tokenize
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from code_scalpel.parsing.unified_parser import ParsingError, parse_python_code
from code_scalpel.utilities.source_sanitizer import sanitize_python_source

__all__ = [
    # Core Python patcher
    "SurgicalPatcher",
    "PatchResult",
    # Polyglot patcher (JS/TS/Java)
    "PolyglotPatcher",
    "PolyglotSymbolLocation",
    "PatchLanguage",
    "BraceMatcher",
    "JavaScriptParser",
    "JavaParser",
    # Unified patcher (auto-routes by language)
    "UnifiedPatcher",
    # Python convenience functions
    "update_function_in_file",
    "update_class_in_file",
    "update_method_in_file",
    # Polyglot convenience functions
    "update_js_function",
    "update_ts_function",
    "update_java_method",
    "update_java_class",
]


# [20260108_BUGFIX] Validate Python identifiers before applying renames
def _is_valid_python_identifier(name: str) -> bool:
    return bool(name) and name.isidentifier() and not keyword.iskeyword(name)


# [20260108_BUGFIX] Basic JavaScript/TypeScript identifier validation with reserved words
_JS_TS_RESERVED = {
    # Keywords
    "break",
    "case",
    "catch",
    "class",
    "const",
    "continue",
    "debugger",
    "default",
    "delete",
    "do",
    "else",
    "export",
    "extends",
    "finally",
    "for",
    "function",
    "if",
    "import",
    "in",
    "instanceof",
    "new",
    "return",
    "super",
    "switch",
    "this",
    "throw",
    "try",
    "typeof",
    "var",
    "void",
    "while",
    "with",
    "yield",
    "let",
    "enum",
    "await",
    "implements",
    "package",
    "protected",
    "static",
    "interface",
    "private",
    "public",
    "null",
    "true",
    "false",
}


def _is_valid_js_identifier(name: str) -> tuple[bool, str]:
    if not name:
        return False, ""
    if not re.match(r"^[A-Za-z_$][A-Za-z0-9_$]*$", name):
        return False, " (invalid identifier)"
    if name.lower() in _JS_TS_RESERVED:
        return False, " (reserved word)"
    return True, ""


@dataclass
class PatchResult:
    """
    Result of a surgical patch operation.

    """

    success: bool
    file_path: str
    target_name: str
    target_type: str  # "function", "class", "method"
    lines_before: int = 0  # Lines in original symbol
    lines_after: int = 0  # Lines in replacement
    backup_path: str | None = None
    error: str | None = None

    @property
    def lines_delta(self) -> int:
        """Change in line count."""
        return self.lines_after - self.lines_before

    # - to_diff() -> str - Generate unified diff
    # - undo() -> PatchResult - Reverse this patch
    # - to_json() -> dict - Serialize for logging
    # - validate() -> list[str] - Run post-patch validation


@dataclass
class _SymbolLocation:
    """
    Internal: Location of a symbol in source code.

    """

    name: str
    node_type: str
    line_start: int  # 1-indexed
    line_end: int  # 1-indexed, inclusive
    col_offset: int
    node: ast.AST
    parent_class: str | None = None  # For methods


# [20251231_FEATURE] Same-file reference rename helpers for Community tier
def _tokenize_code(code: str) -> list[tokenize.TokenInfo]:
    """Tokenize Python code, returning list of tokens."""
    try:
        return list(tokenize.generate_tokens(io.StringIO(code).readline))
    except getattr(tokenize, "TokenizeError", Exception):
        return []


def _apply_token_replacements(
    tokens: list[tokenize.TokenInfo],
    replacements: dict[tuple[int, int], tuple[str, str]],
) -> str:
    """Apply token replacements and reconstruct code."""
    new_tokens: list[tokenize.TokenInfo] = []
    for tok in tokens:
        repl = replacements.get(tok.start)
        if repl and tok.type == tokenize.NAME and tok.string == repl[0]:
            tok = tokenize.TokenInfo(tok.type, repl[1], tok.start, tok.end, tok.line)
        new_tokens.append(tok)
    return tokenize.untokenize(new_tokens)


def _collect_same_file_references(
    code: str,
    target_type: str,
    target_name: str,
    new_name: str,
    definition_line: int,
) -> dict[tuple[int, int], tuple[str, str]]:
    """
    Collect token positions for all references to a symbol within the same file.

    [20251231_FEATURE] Implements same-file reference updates for rename_symbol.

    This finds:
    - Function/method calls: old_name(...) -> new_name(...)
    - Variable references: x = old_name -> x = new_name
    - Decorator usage: @old_name -> @new_name
    - Type hints: -> OldClass, param: OldClass -> -> NewClass, param: NewClass
    - Attribute access for methods: self.old_method -> self.new_method

    Excludes:
    - The definition line itself (already renamed separately)
    - String literals and comments (handled by tokenizer)
    - Import statements (those are cross-file concerns)

    Args:
        code: The source code (definition already renamed)
        target_type: "function", "class", or "method"
        target_name: Original full name (e.g., "my_func" or "ClassName.method")
        new_name: New name to use
        definition_line: Line number of definition (1-indexed) to skip

    Returns:
        Dict mapping (line, col) -> (old_token, new_token) for replacements
    """
    try:
        tree, _report = parse_python_code(code, filename="<token_analysis>")
    except ParsingError:
        return {}

    replacements: dict[tuple[int, int], tuple[str, str]] = {}

    # For methods, we only care about the short name
    if target_type == "method":
        if "." in target_name:
            class_name, old_short = target_name.split(".", 1)
        else:
            old_short = target_name
        new_short = new_name
    else:
        old_short = target_name
        new_short = new_name

    # Walk AST to find references
    for node in ast.walk(tree):
        # Skip nodes without line info
        if not hasattr(node, "lineno") or not hasattr(node, "col_offset"):
            continue

        # Skip the definition line
        # [20260101_BUGFIX] Type assertion for lineno attribute
        if getattr(node, "lineno", -1) == definition_line:
            continue

        # Skip import statements - those are cross-file concerns
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            continue

        # Case 1: Direct Name reference (function/class calls, type hints, decorators)
        if isinstance(node, ast.Name) and target_type in {"function", "class"}:
            if node.id == old_short:
                replacements[(node.lineno, node.col_offset)] = (old_short, new_short)

        # Case 2: Attribute access for methods (self.method_name, obj.method_name)
        elif isinstance(node, ast.Attribute) and target_type == "method":
            if node.attr == old_short:
                # For methods, rename the attribute
                # Calculate position of the attribute name
                if hasattr(node, "end_col_offset") and node.end_col_offset is not None:
                    attr_col = node.end_col_offset - len(old_short)
                    replacements[(node.lineno, attr_col)] = (old_short, new_short)

        # Case 3: Attribute access for class attributes (ClassName.attr after class rename)
        elif isinstance(node, ast.Attribute) and target_type == "class":
            # Check if the value is a Name node with the old class name
            if isinstance(node.value, ast.Name) and node.value.id == old_short:
                replacements[(node.value.lineno, node.value.col_offset)] = (
                    old_short,
                    new_short,
                )

    return replacements


class SurgicalPatcher:
    """
    Precision code patcher using AST-guided line replacement.

    Unlike naive string replacement, this:
    1. Parses the file to find exact symbol boundaries
    2. Validates the replacement code is syntactically correct
    3. Preserves everything outside the target symbol
    4. Creates backups before modification

    Example:
        >>> patcher = SurgicalPatcher.from_file("calculator.py")
        >>> new_code = '''
        ... def add(a, b):
        ...     # Now with logging!
        ...     print(f"Adding {a} + {b}")
        ...     return a + b
        ... '''
        >>> result = patcher.update_function("add", new_code)
        >>> if result.success:
        ...     patcher.save()

    ==========================================

    Core Patching:

    Insertion Operations:

    Deletion Operations:

    Multi-File Operations:

    Safety Features:

    Output & Reporting:
    """

    def __init__(self, code: str, file_path: str | None = None):
        """
        Initialize the patcher with source code.

        Args:
            code: Python source code to modify
            file_path: Path to the source file (required for save())
        """
        self.original_code = code
        self.current_code = code
        self.file_path = file_path
        self._lines = code.splitlines(keepends=True)
        self._tree: ast.Module | None = None
        self._symbols: dict[str, _SymbolLocation] = {}
        self._parsed = False
        self._modified = False
        self._backup_path: str | None = None

    @classmethod
    def from_file(cls, file_path: str, encoding: str = "utf-8") -> SurgicalPatcher:
        """
        Create a patcher by reading from a file.

        Args:
            file_path: Path to the Python source file
            encoding: File encoding (default: utf-8)

        Returns:
            SurgicalPatcher instance ready for modifications

        Raises:
            FileNotFoundError: If the file doesn't exist
            ValueError: If the file can't be read
        """
        if not os.path.isfile(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        try:
            with open(file_path, encoding=encoding) as f:
                code = f.read()
        except (OSError, UnicodeDecodeError) as e:
            # [20260108_BUGFIX] Added UnicodeDecodeError handling for invalid encoding
            raise ValueError(f"Cannot read file {file_path}: {e}")

        return cls(code, file_path=os.path.abspath(file_path))

    def _ensure_parsed(self) -> None:
        """Parse the code and index all symbols."""
        if self._parsed:
            return

        try:
            tree_node, _report = parse_python_code(self.current_code, filename=self.file_path or "<patcher>")
            self._tree = tree_node if isinstance(tree_node, ast.Module) else ast.Module(body=[], type_ignores=[])
        except ParsingError as e:
            # [20260116_BUGFIX] Sanitize malformed source before retrying parse.
            sanitized, changed = sanitize_python_source(self.current_code)
            if not changed:
                raise ValueError(f"Invalid Python code: {e}")
            self.current_code = sanitized
            try:
                tree_node, _report = parse_python_code(self.current_code, filename=self.file_path or "<patcher>")
                self._tree = tree_node if isinstance(tree_node, ast.Module) else ast.Module(body=[], type_ignores=[])
            except ParsingError as e2:
                raise ValueError(f"Invalid Python code after sanitization: {e2}")

        self._index_symbols()
        self._parsed = True

    def _index_symbols(self) -> None:
        """
        Build an index of all functions, classes, and methods.

        """
        self._symbols.clear()

        if self._tree is None:
            return

        for node in ast.walk(self._tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Check if this is a method (inside a class)
                parent_class = self._find_parent_class(node)
                if parent_class:
                    key = f"{parent_class}.{node.name}"
                    symbol = _SymbolLocation(
                        name=node.name,
                        node_type="method",
                        line_start=node.lineno,
                        line_end=self._get_end_line(node),
                        col_offset=node.col_offset,
                        node=node,
                        parent_class=parent_class,
                    )
                else:
                    key = node.name
                    symbol = _SymbolLocation(
                        name=node.name,
                        node_type="function",
                        line_start=node.lineno,
                        line_end=self._get_end_line(node),
                        col_offset=node.col_offset,
                        node=node,
                    )
                self._symbols[key] = symbol

            elif isinstance(node, ast.ClassDef):
                key = node.name
                symbol = _SymbolLocation(
                    name=node.name,
                    node_type="class",
                    line_start=node.lineno,
                    line_end=self._get_end_line(node),
                    col_offset=node.col_offset,
                    node=node,
                )
                self._symbols[key] = symbol

    def _find_parent_class(self, node: ast.AST) -> str | None:
        """Find the parent class of a method node."""
        if self._tree is None:
            return None
        for potential_parent in ast.walk(self._tree):
            if isinstance(potential_parent, ast.ClassDef):
                for child in ast.walk(potential_parent):
                    if child is node and child is not potential_parent:
                        return potential_parent.name
        return None

    def _get_end_line(self, node: ast.AST) -> int:
        """
        Get the end line of an AST node, handling decorators.

        """
        end_lineno = getattr(node, "end_lineno", None)
        if end_lineno is not None:
            return end_lineno

        # Fallback for older Python: estimate from body
        lineno = getattr(node, "lineno", 1)
        max_line = lineno
        for child in ast.walk(node):
            child_lineno = getattr(child, "lineno", None)
            child_end_lineno = getattr(child, "end_lineno", None)
            if child_lineno is not None:
                max_line = max(max_line, child_lineno)
            if child_end_lineno is not None:
                max_line = max(max_line, child_end_lineno)
        return max_line

    def _get_decorator_start(self, node: ast.AST) -> int:
        """
        Get the starting line including decorators.

        """
        decorator_list = getattr(node, "decorator_list", None)
        if decorator_list:
            return min(d.lineno for d in decorator_list)
        lineno = getattr(node, "lineno", 1)
        return lineno

    def _validate_replacement(self, new_code: str, target_type: str) -> None:
        """
        Validate that replacement code is syntactically correct.

        """
        try:
            tree_node, _report = parse_python_code(new_code, filename="<replacement>")
            tree = tree_node if isinstance(tree_node, ast.Module) else ast.Module(body=[], type_ignores=[])
        except ParsingError as e:
            raise ValueError(f"Replacement code has syntax error: {e}")

        # Verify it contains the expected type
        body = tree.body
        if not body:
            raise ValueError("Replacement code is empty")

        if target_type == "function":
            if not isinstance(body[0], (ast.FunctionDef, ast.AsyncFunctionDef)):
                raise ValueError("Replacement for function must be a function definition")
        elif target_type == "class":
            if not isinstance(body[0], ast.ClassDef):
                raise ValueError("Replacement for class must be a class definition")
        elif target_type == "method":
            if not isinstance(body[0], (ast.FunctionDef, ast.AsyncFunctionDef)):
                raise ValueError("Replacement for method must be a function definition")

    def _apply_patch(self, symbol: _SymbolLocation, new_code: str) -> tuple[str, int, int]:
        """
        Apply a patch to the current code.

        Returns:
            Tuple of (new_code, lines_removed, lines_added)

        """
        lines = self.current_code.splitlines(keepends=True)

        # Include decorators in the replacement range
        start_line = self._get_decorator_start(symbol.node)
        end_line = symbol.line_end

        # Determine indentation from the original
        original_indent = ""
        if start_line <= len(lines):
            original_line = lines[start_line - 1]
            original_indent = original_line[: len(original_line) - len(original_line.lstrip())]

        # Prepare replacement lines with proper indentation
        new_lines = new_code.splitlines(keepends=True)
        if new_lines and not new_lines[-1].endswith("\n"):
            new_lines[-1] += "\n"

        # Apply indentation to replacement (detect its base indent and adjust)
        if new_lines:
            # Find the base indentation of the new code
            first_non_empty = next((line for line in new_lines if line.strip()), new_lines[0])
            new_base_indent = first_non_empty[: len(first_non_empty) - len(first_non_empty.lstrip())]

            # Reindent if needed
            if new_base_indent != original_indent:
                adjusted_lines = []
                for line in new_lines:
                    if line.strip():  # Non-empty line
                        if line.startswith(new_base_indent):
                            line = original_indent + line[len(new_base_indent) :]
                    adjusted_lines.append(line)
                new_lines = adjusted_lines

        # Replace lines
        lines_removed = end_line - start_line + 1
        lines_added = len(new_lines)

        result_lines = lines[: start_line - 1] + new_lines + lines[end_line:]
        return "".join(result_lines), lines_removed, lines_added

    def update_function(self, name: str, new_code: str) -> PatchResult:
        """
        Replace a function definition with new code.

        Args:
            name: Name of the function to replace
            new_code: New function definition (including def line and body)

        Returns:
            PatchResult indicating success or failure
        """
        self._ensure_parsed()

        if name not in self._symbols:
            return PatchResult(
                success=False,
                file_path=self.file_path or "",
                target_name=name,
                target_type="function",
                error=f"Function '{name}' not found",
            )

        symbol = self._symbols[name]
        if symbol.node_type != "function":
            return PatchResult(
                success=False,
                file_path=self.file_path or "",
                target_name=name,
                target_type="function",
                error=f"'{name}' is a {symbol.node_type}, not a function",
            )

        try:
            self._validate_replacement(new_code, "function")
        except ValueError as e:
            return PatchResult(
                success=False,
                file_path=self.file_path or "",
                target_name=name,
                target_type="function",
                error=str(e),
            )

        lines_before = symbol.line_end - self._get_decorator_start(symbol.node) + 1
        new_code_str, _, lines_added = self._apply_patch(symbol, new_code)

        self.current_code = new_code_str
        self._parsed = False  # Need to re-parse after modification
        self._modified = True

        return PatchResult(
            success=True,
            file_path=self.file_path or "",
            target_name=name,
            target_type="function",
            lines_before=lines_before,
            lines_after=lines_added,
        )

    def update_class(self, name: str, new_code: str) -> PatchResult:
        """
        Replace a class definition with new code.

        Args:
            name: Name of the class to replace
            new_code: New class definition (including class line and body)

        Returns:
            PatchResult indicating success or failure
        """
        self._ensure_parsed()

        if name not in self._symbols:
            return PatchResult(
                success=False,
                file_path=self.file_path or "",
                target_name=name,
                target_type="class",
                error=f"Class '{name}' not found",
            )

        symbol = self._symbols[name]
        if symbol.node_type != "class":
            return PatchResult(
                success=False,
                file_path=self.file_path or "",
                target_name=name,
                target_type="class",
                error=f"'{name}' is a {symbol.node_type}, not a class",
            )

        try:
            self._validate_replacement(new_code, "class")
        except ValueError as e:
            return PatchResult(
                success=False,
                file_path=self.file_path or "",
                target_name=name,
                target_type="class",
                error=str(e),
            )

        lines_before = symbol.line_end - self._get_decorator_start(symbol.node) + 1
        new_code_str, _, lines_added = self._apply_patch(symbol, new_code)

        self.current_code = new_code_str
        self._parsed = False
        self._modified = True

        return PatchResult(
            success=True,
            file_path=self.file_path or "",
            target_name=name,
            target_type="class",
            lines_before=lines_before,
            lines_after=lines_added,
        )

    def insert_function(self, new_code: str) -> PatchResult:
        """
        Insert a new function at the end of the file.

        Args:
            new_code: New function definition

        Returns:
            PatchResult
        """
        self._ensure_parsed()

        try:
            self._validate_replacement(new_code, "function")
        except ValueError as e:
            return PatchResult(
                success=False,
                file_path=self.file_path or "",
                target_name="<new>",
                target_type="function",
                error=str(e),
            )

        try:
            tree_node, _report = parse_python_code(new_code, filename="<function_update>")
            tree = tree_node if isinstance(tree_node, ast.Module) else ast.Module(body=[], type_ignores=[])
        except ParsingError as e:
            return PatchResult(
                success=False,
                file_path=self.file_path or "",
                target_name="<new>",
                target_type="function",
                error=f"Failed to parse replacement code: {e}",
            )

        # [20260101_BUGFIX] Type assertion for FunctionDef/AsyncFunctionDef node
        first_node = tree.body[0]
        if not isinstance(first_node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return PatchResult(
                success=False,
                file_path=self.file_path or "",
                target_name="<new>",
                target_type="function",
                error="Parsed node is not a function definition",
            )
        name = first_node.name

        if name in self._symbols:
            return PatchResult(
                success=False,
                file_path=self.file_path or "",
                target_name=name,
                target_type="function",
                error=f"Symbol '{name}' already exists",
            )

        if not self.current_code.endswith("\n"):
            self.current_code += "\n"

        if not self.current_code.strip():
            self.current_code += new_code + "\n"
        else:
            self.current_code += "\n\n" + new_code + "\n"

        self._parsed = False
        self._modified = True

        return PatchResult(
            success=True,
            file_path=self.file_path or "",
            target_name=name,
            target_type="function",
            lines_before=0,
            lines_after=len(new_code.splitlines()),
        )

    def insert_class(self, new_code: str) -> PatchResult:
        """
        Insert a new class at the end of the file.

        Args:
            new_code: New class definition

        Returns:
            PatchResult
        """
        self._ensure_parsed()

        try:
            self._validate_replacement(new_code, "class")
        except ValueError as e:
            return PatchResult(
                success=False,
                file_path=self.file_path or "",
                target_name="<new>",
                target_type="class",
                error=str(e),
            )

        try:
            tree_node, _report = parse_python_code(new_code, filename="<class_update>")
            tree = tree_node if isinstance(tree_node, ast.Module) else ast.Module(body=[], type_ignores=[])
        except ParsingError as e:
            return PatchResult(
                success=False,
                file_path=self.file_path or "",
                target_name="<new>",
                target_type="class",
                error=f"Failed to parse replacement code: {e}",
            )

        # [20260101_BUGFIX] Type assertion for ClassDef node
        first_node = tree.body[0]
        if not isinstance(first_node, ast.ClassDef):
            return PatchResult(
                success=False,
                file_path=self.file_path or "",
                target_name="<new>",
                target_type="class",
                error="Parsed node is not a class definition",
            )
        name = first_node.name

        if name in self._symbols:
            return PatchResult(
                success=False,
                file_path=self.file_path or "",
                target_name=name,
                target_type="class",
                error=f"Symbol '{name}' already exists",
            )

        if not self.current_code.endswith("\n"):
            self.current_code += "\n"

        if not self.current_code.strip():
            self.current_code += new_code + "\n"
        else:
            self.current_code += "\n\n" + new_code + "\n"

        self._parsed = False
        self._modified = True

        return PatchResult(
            success=True,
            file_path=self.file_path or "",
            target_name=name,
            target_type="class",
            lines_before=0,
            lines_after=len(new_code.splitlines()),
        )

    def update_method(self, class_name: str, method_name: str, new_code: str) -> PatchResult:
        """
        Replace a method within a class.

        Args:
            class_name: Name of the containing class
            method_name: Name of the method to replace
            new_code: New method definition (including def line and body)

        Returns:
            PatchResult indicating success or failure
        """
        self._ensure_parsed()

        key = f"{class_name}.{method_name}"
        if key not in self._symbols:
            return PatchResult(
                success=False,
                file_path=self.file_path or "",
                target_name=key,
                target_type="method",
                error=f"Method '{method_name}' not found in class '{class_name}'",
            )

        symbol = self._symbols[key]
        if symbol.node_type != "method":
            return PatchResult(
                success=False,
                file_path=self.file_path or "",
                target_name=key,
                target_type="method",
                error=f"'{key}' is a {symbol.node_type}, not a method",
            )

        try:
            self._validate_replacement(new_code, "method")
        except ValueError as e:
            return PatchResult(
                success=False,
                file_path=self.file_path or "",
                target_name=key,
                target_type="method",
                error=str(e),
            )

        lines_before = symbol.line_end - self._get_decorator_start(symbol.node) + 1
        new_code_str, _, lines_added = self._apply_patch(symbol, new_code)

        self.current_code = new_code_str
        self._parsed = False
        self._modified = True

        return PatchResult(
            success=True,
            file_path=self.file_path or "",
            target_name=key,
            target_type="method",
            lines_before=lines_before,
            lines_after=lines_added,
        )

    def insert_method(self, class_name: str, new_code: str) -> PatchResult:
        """
        Insert a new method into an existing class.

        Args:
            class_name: Name of the class
            new_code: New method definition

        Returns:
            PatchResult
        """
        self._ensure_parsed()

        if class_name not in self._symbols:
            return PatchResult(
                success=False,
                file_path=self.file_path or "",
                target_name=class_name,
                target_type="class",
                error=f"Class '{class_name}' not found",
            )

        class_symbol = self._symbols[class_name]
        if class_symbol.node_type != "class":
            return PatchResult(
                success=False,
                file_path=self.file_path or "",
                target_name=class_name,
                target_type="class",
                error=f"'{class_name}' is not a class",
            )

        try:
            self._validate_replacement(new_code, "method")
        except ValueError as e:
            return PatchResult(
                success=False,
                file_path=self.file_path or "",
                target_name="<new>",
                target_type="method",
                error=str(e),
            )

        try:
            tree_node, _report = parse_python_code(new_code, filename="<method_update>")
            tree = tree_node if isinstance(tree_node, ast.Module) else ast.Module(body=[], type_ignores=[])
        except ParsingError as e:
            return PatchResult(
                success=False,
                file_path=self.file_path or "",
                target_name="<new>",
                target_type="method",
                error=f"Failed to parse replacement code: {e}",
            )

        # [20260101_BUGFIX] Type assertion for FunctionDef/AsyncFunctionDef node
        first_node = tree.body[0]
        if not isinstance(first_node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return PatchResult(
                success=False,
                file_path=self.file_path or "",
                target_name="<new>",
                target_type="method",
                error="Parsed node is not a method definition",
            )
        method_name = first_node.name
        key = f"{class_name}.{method_name}"

        if key in self._symbols:
            return PatchResult(
                success=False,
                file_path=self.file_path or "",
                target_name=key,
                target_type="method",
                error=f"Method '{method_name}' already exists in '{class_name}'",
            )

        lines = self.current_code.splitlines(keepends=True)
        end_line = class_symbol.line_end

        # Determine indentation
        class_line = lines[class_symbol.line_start - 1]
        class_indent = class_line[: len(class_line) - len(class_line.lstrip())]
        method_indent = class_indent + "    "  # Default

        # Try to find existing methods to guess indent
        for sym in self._symbols.values():
            if sym.parent_class == class_name:
                method_line = lines[sym.line_start - 1]
                method_indent = method_line[: len(method_line) - len(method_line.lstrip())]
                break

        # Prepare new code
        new_lines = new_code.splitlines(keepends=True)
        indented_lines = []

        first_non_empty = next((line for line in new_lines if line.strip()), new_lines[0])
        base_indent = first_non_empty[: len(first_non_empty) - len(first_non_empty.lstrip())]

        for line in new_lines:
            if line.strip():
                if line.startswith(base_indent):
                    line = method_indent + line[len(base_indent) :]
            indented_lines.append(line)

        if indented_lines and not indented_lines[-1].endswith("\n"):
            indented_lines[-1] += "\n"

        # Insert at end of class
        insert_pos = end_line
        final_lines = ["\n"] + indented_lines

        result_lines = lines[:insert_pos] + final_lines + lines[insert_pos:]

        self.current_code = "".join(result_lines)
        self._parsed = False
        self._modified = True

        return PatchResult(
            success=True,
            file_path=self.file_path or "",
            target_name=key,
            target_type="method",
            lines_before=0,
            lines_after=len(indented_lines),
        )

    def rename_symbol(self, target_type: str, target_name: str, new_name: str) -> PatchResult:
        """
        Rename a symbol (function, class, or method) in the file.

        [20251231_FEATURE] Now updates both definition AND all references in the same file.

        This updates:
        - The definition (def/class statement)
        - All calls and references within the same file
        - Type hints referencing the symbol
        - Decorator usage (for functions/classes)
        - Attribute access (for methods: self.old_method -> self.new_method)

        Args:
            target_type: "function", "class", or "method"
            target_name: Current name (e.g., "my_func" or "MyClass.my_method")
            new_name: New name (e.g., "new_func" or "new_method")

        Returns:
            PatchResult with lines_before/after indicating references updated
        """
        self._ensure_parsed()

        if target_name not in self._symbols:
            return PatchResult(
                success=False,
                file_path=self.file_path or "",
                target_name=target_name,
                target_type=target_type,
                error=f"{target_type.capitalize()} '{target_name}' not found",
            )

        symbol = self._symbols[target_name]
        if symbol.node_type != target_type:
            return PatchResult(
                success=False,
                file_path=self.file_path or "",
                target_name=target_name,
                target_type=target_type,
                error=f"'{target_name}' is a {symbol.node_type}, not a {target_type}",
            )

        # 1. Rename the definition
        lines = self.current_code.splitlines(keepends=True)
        def_line_idx = symbol.line_start - 1
        def_line = lines[def_line_idx]

        if target_type == "method":
            old_short_name = target_name.split(".")[-1]
        else:
            old_short_name = target_name

        prefix = "class" if target_type == "class" else "def"

        # Regex to match "def old_name" or "class old_name"
        match = re.search(rf"{prefix}\s+{re.escape(old_short_name)}\b", def_line)

        if not match:
            # Maybe it's async def?
            match = re.search(rf"async\s+def\s+{re.escape(old_short_name)}\b", def_line)

        if match:
            if "async" in match.group(0):
                new_def_line = re.sub(
                    rf"(async\s+def\s+){re.escape(old_short_name)}\b",
                    rf"\g<1>{new_name}",
                    def_line,
                    count=1,
                )
            else:
                new_def_line = re.sub(
                    rf"({prefix}\s+){re.escape(old_short_name)}\b",
                    rf"\g<1>{new_name}",
                    def_line,
                    count=1,
                )
            lines[def_line_idx] = new_def_line
        else:
            return PatchResult(
                success=False,
                file_path=self.file_path or "",
                target_name=target_name,
                target_type=target_type,
                error=f"Could not locate definition of '{old_short_name}' on line {symbol.line_start}",
            )

        # Update current_code with definition rename
        self.current_code = "".join(lines)

        # 2. [20251231_FEATURE] Update all same-file references
        references_updated = 0
        try:
            replacements = _collect_same_file_references(
                self.current_code,
                target_type,
                target_name,
                new_name,
                symbol.line_start,
            )

            if replacements:
                tokens = _tokenize_code(self.current_code)
                if tokens:
                    new_code = _apply_token_replacements(tokens, replacements)
                    if new_code != self.current_code:
                        self.current_code = new_code
                        references_updated = len(replacements)
        except Exception:
            # If reference update fails, we still have the definition renamed
            # This is a best-effort enhancement
            pass

        self._parsed = False
        self._modified = True

        return PatchResult(
            success=True,
            file_path=self.file_path or "",
            target_name=target_name,
            target_type=target_type,
            lines_before=1,
            lines_after=1 + references_updated,  # 1 for def + N for references
        )

    def get_modified_code(self) -> str:
        """Get the current (possibly modified) code."""
        return self.current_code

    def save(self, backup: bool = True) -> str | None:
        """
        Write modified code back to the file.

        Args:
            backup: If True, create a backup file before saving

        Returns:
            Path to backup file if created, None otherwise

        Raises:
            ValueError: If no file_path was provided
            IOError: If file cannot be written

        """
        if not self.file_path:
            raise ValueError("Cannot save: no file_path specified")

        if not self._modified:
            return None  # Nothing to save

        backup_path = None
        if backup:
            backup_path = f"{self.file_path}.bak"
            shutil.copy2(self.file_path, backup_path)
            self._backup_path = backup_path

        # Atomic write: write to temp file, then rename
        dir_path = os.path.dirname(self.file_path)
        with tempfile.NamedTemporaryFile(mode="w", dir=dir_path, delete=False, suffix=".tmp") as f:
            f.write(self.current_code)
            temp_path = f.name

        os.replace(temp_path, self.file_path)
        self._modified = False
        self.original_code = self.current_code

        return backup_path

    def discard_changes(self) -> None:
        """Discard all modifications and revert to original code."""
        self.current_code = self.original_code
        self._parsed = False
        self._modified = False


# Convenience functions for one-shot operations
def update_function_in_file(file_path: str, function_name: str, new_code: str, backup: bool = True) -> PatchResult:
    """
    Update a function in a file (convenience function).

    Args:
        file_path: Path to the Python file
        function_name: Name of the function to replace
        new_code: New function definition
        backup: Whether to create a backup

    Returns:
        PatchResult indicating success or failure
    """
    patcher = SurgicalPatcher.from_file(file_path)
    result = patcher.update_function(function_name, new_code)
    if result.success:
        result.backup_path = patcher.save(backup=backup)
    return result


def update_class_in_file(file_path: str, class_name: str, new_code: str, backup: bool = True) -> PatchResult:
    """
    Update a class in a file (convenience function).

    Args:
        file_path: Path to the Python file
        class_name: Name of the class to replace
        new_code: New class definition
        backup: Whether to create a backup

    Returns:
        PatchResult indicating success or failure
    """
    patcher = SurgicalPatcher.from_file(file_path)
    result = patcher.update_class(class_name, new_code)
    if result.success:
        result.backup_path = patcher.save(backup=backup)
    return result


def update_method_in_file(
    file_path: str,
    class_name: str,
    method_name: str,
    new_code: str,
    backup: bool = True,
) -> PatchResult:
    """
    Update a method in a file (convenience function).

    Args:
        file_path: Path to the Python file
        class_name: Name of the containing class
        method_name: Name of the method to replace
        new_code: New method definition
        backup: Whether to create a backup

    Returns:
        PatchResult indicating success or failure
    """
    patcher = SurgicalPatcher.from_file(file_path)
    result = patcher.update_method(class_name, method_name, new_code)
    if result.success:
        result.backup_path = patcher.save(backup=backup)
    return result


# =============================================================================
# POLYGLOT PATCHER - Multi-Language Support
# =============================================================================
# [20251221_FEATURE] JavaScript, TypeScript, and Java patching support


class PatchLanguage(Enum):
    """Supported languages for patching."""

    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    JAVA = "java"


@dataclass
class PolyglotSymbolLocation:
    """
    Location of a symbol in source code (language-agnostic).

    [20251221_FEATURE] Cross-language symbol tracking.
    """

    name: str
    symbol_type: str  # "function", "class", "method", "interface"
    line_start: int  # 1-indexed
    line_end: int  # 1-indexed, inclusive
    col_start: int
    col_end: int
    parent_name: str | None = None  # For methods: containing class/interface
    modifiers: list[str] = field(default_factory=list)  # public, static, async, etc.
    decorators: list[str] = field(default_factory=list)  # @decorators / annotations
    raw_text: str = ""  # Original source text

    @property
    def qualified_name(self) -> str:
        """Get fully qualified name."""
        if self.parent_name:
            return f"{self.parent_name}.{self.name}"
        return self.name


class BraceMatcher:
    """
    Utility for matching braces in C-style languages.

    [20251221_FEATURE] Robust brace matching for JS/TS/Java.
    """

    def __init__(self, code: str):
        self.code = code
        self.length = len(code)

    def find_matching_brace(self, start_pos: int) -> int:
        """
        Find the position of the closing brace matching the opening brace at start_pos.

        Args:
            start_pos: Position of opening brace '{'

        Returns:
            Position of matching closing brace, or -1 if not found
        """
        if start_pos >= self.length or self.code[start_pos] != "{":
            return -1

        depth = 0
        in_string = False
        string_char = ""
        in_template = False
        in_line_comment = False
        in_block_comment = False
        i = start_pos

        while i < self.length:
            char = self.code[i]
            next_char = self.code[i + 1] if i + 1 < self.length else ""

            # Handle comments
            if in_line_comment:
                if char == "\n":
                    in_line_comment = False
                i += 1
                continue

            if in_block_comment:
                if char == "*" and next_char == "/":
                    in_block_comment = False
                    i += 2
                    continue
                i += 1
                continue

            if not in_string and not in_template:
                if char == "/" and next_char == "/":
                    in_line_comment = True
                    i += 2
                    continue
                if char == "/" and next_char == "*":
                    in_block_comment = True
                    i += 2
                    continue

            # Handle strings
            if in_string:
                if char == "\\" and i + 1 < self.length:
                    i += 2  # Skip escaped character
                    continue
                if char == string_char:
                    in_string = False
                i += 1
                continue

            # Handle template literals (JS/TS)
            if in_template:
                if char == "\\" and i + 1 < self.length:
                    i += 2
                    continue
                if char == "`":
                    in_template = False
                elif char == "$" and next_char == "{":
                    # Template expression - need to track nested braces
                    depth += 1
                    i += 2
                    continue
                i += 1
                continue

            # Start of string
            if char in "\"'":
                in_string = True
                string_char = char
                i += 1
                continue

            # Start of template literal
            if char == "`":
                in_template = True
                i += 1
                continue

            # Track braces
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    return i

            i += 1

        return -1

    def find_block_end(self, start_line: int) -> int:
        """
        Find the end line of a code block starting at given line.

        Args:
            start_line: 1-indexed line number where block starts

        Returns:
            1-indexed line number where block ends
        """
        lines = self.code.splitlines(keepends=True)
        char_pos = sum(len(lines[i]) for i in range(start_line - 1))

        # Find first opening brace on or after start_line
        brace_pos = self.code.find("{", char_pos)
        if brace_pos == -1:
            return start_line

        end_pos = self.find_matching_brace(brace_pos)
        if end_pos == -1:
            return start_line

        # Convert position to line number
        return self.code[:end_pos].count("\n") + 1


class JavaScriptParser:
    """
    Parser for JavaScript/TypeScript symbol extraction.

    [20251221_FEATURE] JS/TS function and class parsing.
    """

    # Regex patterns for JS/TS symbols
    # [20251231_BUGFIX] Added TypeScript return type annotation support
    FUNCTION_PATTERN = re.compile(
        r"^(\s*)"  # Indentation
        r"(export\s+)?"  # Optional export
        r"(default\s+)?"  # Optional default
        r"(async\s+)?"  # Optional async
        r"function\s+"  # function keyword
        r"(\*?\s*)"  # Optional generator *
        r"(\w+)"  # Function name
        r"\s*\([^)]*\)"  # Parameters
        r"(?:\s*:\s*[^{]+)?"  # Optional return type annotation (TS)
        r"\s*{",  # Opening brace
        re.MULTILINE,
    )

    ARROW_FUNCTION_PATTERN = re.compile(
        r"^(\s*)"  # Indentation
        r"(export\s+)?"  # Optional export
        r"(const|let|var)\s+"  # Variable declaration
        r"(\w+)"  # Function name
        r"(?:\s*:\s*[^=]+)?"  # Optional type annotation (TS)
        r"\s*=\s*"
        r"(async\s+)?"  # Optional async
        r"(\([^)]*\)|[a-zA-Z_]\w*)"  # Parameters or single param
        r"(?:\s*:\s*[^=]+)?"  # Optional return type annotation (TS)
        r"\s*=>\s*"  # Arrow
        r"({|\(|[^;{(])",  # Body start
        re.MULTILINE,
    )

    # [20251231_BUGFIX] Added TypeScript generics support
    CLASS_PATTERN = re.compile(
        r"^(\s*)"  # Indentation
        r"(export\s+)?"  # Optional export
        r"(default\s+)?"  # Optional default
        r"(abstract\s+)?"  # Optional abstract (TS)
        r"class\s+"  # class keyword
        r"(\w+)"  # Class name
        r"(?:\s*<[^>]+>)?"  # Optional generics (TS)
        r"(?:\s+extends\s+\w+(?:<[^>]+>)?)?"  # Optional extends (with generics)
        r"(?:\s+implements\s+[\w,\s<>]+)?"  # Optional implements (TS)
        r"\s*{",  # Opening brace
        re.MULTILINE,
    )

    METHOD_PATTERN = re.compile(
        r"^(\s+)"  # Indentation (methods are indented)
        r"(static\s+)?"  # Optional static
        r"(async\s+)?"  # Optional async
        r"(get\s+|set\s+)?"  # Optional getter/setter
        r"(\#?\w+)"  # Method name (with optional private #)
        r"\s*\([^)]*\)"  # Parameters
        r"(?:\s*:\s*[^{]+)?"  # Optional return type (TS)
        r"\s*{",  # Opening brace
        re.MULTILINE,
    )

    INTERFACE_PATTERN = re.compile(
        r"^(\s*)"  # Indentation
        r"(export\s+)?"  # Optional export
        r"interface\s+"  # interface keyword (TS)
        r"(\w+)"  # Interface name
        r"(?:\s+extends\s+[\w,\s]+)?"  # Optional extends
        r"\s*{",  # Opening brace
        re.MULTILINE,
    )

    TYPE_ALIAS_PATTERN = re.compile(
        r"^(\s*)"  # Indentation
        r"(export\s+)?"  # Optional export
        r"type\s+"  # type keyword (TS)
        r"(\w+)"  # Type name
        r"\s*(?:<[^>]+>)?"  # Optional generics
        r"\s*=",  # Assignment
        re.MULTILINE,
    )

    def __init__(self, code: str, is_typescript: bool = False):
        self.code = code
        self.is_typescript = is_typescript
        self.lines = code.splitlines(keepends=True)
        self.brace_matcher = BraceMatcher(code)

    def find_symbols(self) -> list[PolyglotSymbolLocation]:
        """Find all function, class, and method symbols."""
        symbols: list[PolyglotSymbolLocation] = []

        # Find classes and interfaces first (methods are inside them)
        symbols.extend(self._find_classes())
        symbols.extend(self._find_standalone_functions())

        if self.is_typescript:
            symbols.extend(self._find_interfaces())

        return symbols

    def _find_classes(self) -> list[PolyglotSymbolLocation]:
        """Find all class definitions with their methods."""
        symbols: list[PolyglotSymbolLocation] = []

        for match in self.CLASS_PATTERN.finditer(self.code):
            class_name = match.group(5)
            # [20251231_BUGFIX] Account for newlines in captured indentation group
            indent = match.group(1) or ""
            indent_newlines = indent.count("\n")
            line_start = self.code[: match.start()].count("\n") + 1 + indent_newlines
            line_end = self.brace_matcher.find_block_end(line_start)

            modifiers = []
            if match.group(2):
                modifiers.append("export")
            if match.group(3):
                modifiers.append("default")
            if match.group(4):
                modifiers.append("abstract")

            class_symbol = PolyglotSymbolLocation(
                name=class_name,
                symbol_type="class",
                line_start=line_start,
                line_end=line_end,
                col_start=len(match.group(1)),
                col_end=0,
                modifiers=modifiers,
                raw_text=self._get_lines(line_start, line_end),
            )
            symbols.append(class_symbol)

            # Find methods within this class
            symbols.extend(self._find_methods_in_class(class_name, line_start, line_end))

        return symbols

    def _find_methods_in_class(self, class_name: str, class_start: int, class_end: int) -> list[PolyglotSymbolLocation]:
        """Find methods within a class."""
        methods: list[PolyglotSymbolLocation] = []
        class_code = self._get_lines(class_start, class_end)
        class_offset = sum(len(self.lines[i]) for i in range(class_start - 1))

        for match in self.METHOD_PATTERN.finditer(class_code):
            method_name = match.group(5)
            if method_name in ("constructor", "if", "for", "while", "switch"):
                if method_name != "constructor":
                    continue  # Skip control structures

            rel_line_start = class_code[: match.start()].count("\n") + 1
            abs_line_start = class_start + rel_line_start - 1

            # Find method end
            method_brace_pos = class_offset + match.end() - 1
            method_end_pos = self.brace_matcher.find_matching_brace(method_brace_pos)
            if method_end_pos == -1:
                continue

            abs_line_end = self.code[:method_end_pos].count("\n") + 1

            modifiers = []
            if match.group(2):
                modifiers.append("static")
            if match.group(3):
                modifiers.append("async")
            if match.group(4):
                modifiers.append(match.group(4).strip())

            methods.append(
                PolyglotSymbolLocation(
                    name=method_name,
                    symbol_type="method",
                    line_start=abs_line_start,
                    line_end=abs_line_end,
                    col_start=len(match.group(1)),
                    col_end=0,
                    parent_name=class_name,
                    modifiers=modifiers,
                    raw_text=self._get_lines(abs_line_start, abs_line_end),
                )
            )

        return methods

    def _find_standalone_functions(self) -> list[PolyglotSymbolLocation]:
        """Find standalone function declarations."""
        functions: list[PolyglotSymbolLocation] = []

        # Regular functions
        for match in self.FUNCTION_PATTERN.finditer(self.code):
            func_name = match.group(6)
            # [20251231_BUGFIX] Account for newlines in captured indentation group
            indent = match.group(1) or ""
            indent_newlines = indent.count("\n")
            line_start = self.code[: match.start()].count("\n") + 1 + indent_newlines
            line_end = self.brace_matcher.find_block_end(line_start)

            modifiers = []
            if match.group(2):
                modifiers.append("export")
            if match.group(3):
                modifiers.append("default")
            if match.group(4):
                modifiers.append("async")
            if match.group(5) and match.group(5).strip():
                modifiers.append("generator")

            functions.append(
                PolyglotSymbolLocation(
                    name=func_name,
                    symbol_type="function",
                    line_start=line_start,
                    line_end=line_end,
                    col_start=len(match.group(1)),
                    col_end=0,
                    modifiers=modifiers,
                    raw_text=self._get_lines(line_start, line_end),
                )
            )

        # Arrow functions (named via const/let/var)
        for match in self.ARROW_FUNCTION_PATTERN.finditer(self.code):
            func_name = match.group(4)
            # [20251231_BUGFIX] Account for newlines in captured indentation group
            indent = match.group(1) or ""
            indent_newlines = indent.count("\n")
            line_start = self.code[: match.start()].count("\n") + 1 + indent_newlines

            # Find arrow function end
            body_start = match.group(7)
            if body_start == "{":
                # Block body - find matching brace
                brace_pos = match.end() - 1
                end_pos = self.brace_matcher.find_matching_brace(brace_pos)
                if end_pos == -1:
                    continue
                line_end = self.code[:end_pos].count("\n") + 1
            else:
                # Expression body - find semicolon or end of line
                rest = self.code[match.end() :]
                semi_pos = rest.find(";")
                if semi_pos != -1:
                    line_end = self.code[: match.end() + semi_pos].count("\n") + 1
                else:
                    line_end = line_start

            modifiers = []
            if match.group(2):
                modifiers.append("export")
            if match.group(5):
                modifiers.append("async")

            functions.append(
                PolyglotSymbolLocation(
                    name=func_name,
                    symbol_type="function",
                    line_start=line_start,
                    line_end=line_end,
                    col_start=len(match.group(1)),
                    col_end=0,
                    modifiers=modifiers,
                    raw_text=self._get_lines(line_start, line_end),
                )
            )

        return functions

    def _find_interfaces(self) -> list[PolyglotSymbolLocation]:
        """Find TypeScript interfaces."""
        interfaces: list[PolyglotSymbolLocation] = []

        for match in self.INTERFACE_PATTERN.finditer(self.code):
            interface_name = match.group(3)
            # [20251231_BUGFIX] Account for newlines in captured indentation group
            indent = match.group(1) or ""
            indent_newlines = indent.count("\n")
            line_start = self.code[: match.start()].count("\n") + 1 + indent_newlines
            line_end = self.brace_matcher.find_block_end(line_start)

            modifiers = []
            if match.group(2):
                modifiers.append("export")

            interfaces.append(
                PolyglotSymbolLocation(
                    name=interface_name,
                    symbol_type="interface",
                    line_start=line_start,
                    line_end=line_end,
                    col_start=len(match.group(1)),
                    col_end=0,
                    modifiers=modifiers,
                    raw_text=self._get_lines(line_start, line_end),
                )
            )

        return interfaces

    def _get_lines(self, start: int, end: int) -> str:
        """Get source lines (1-indexed, inclusive)."""
        return "".join(self.lines[start - 1 : end])


class JavaParser:
    """
    Parser for Java symbol extraction.

    [20251221_FEATURE] Java class and method parsing.
    """

    # Regex patterns for Java symbols
    CLASS_PATTERN = re.compile(
        r"^(\s*)"  # Indentation
        r"((?:public|private|protected)\s+)?"  # Access modifier
        r"((?:abstract|final|static)\s+)*"  # Other modifiers
        r"class\s+"  # class keyword
        r"(\w+)"  # Class name
        r"(?:\s*<[^>]+>)?"  # Optional generics
        r"(?:\s+extends\s+\w+(?:<[^>]+>)?)?"  # Optional extends
        r"(?:\s+implements\s+[\w,\s<>]+)?"  # Optional implements
        r"\s*{",  # Opening brace
        re.MULTILINE,
    )

    INTERFACE_PATTERN = re.compile(
        r"^(\s*)"  # Indentation
        r"((?:public|private|protected)\s+)?"  # Access modifier
        r"interface\s+"  # interface keyword
        r"(\w+)"  # Interface name
        r"(?:\s*<[^>]+>)?"  # Optional generics
        r"(?:\s+extends\s+[\w,\s<>]+)?"  # Optional extends
        r"\s*{",  # Opening brace
        re.MULTILINE,
    )

    ENUM_PATTERN = re.compile(
        r"^(\s*)"  # Indentation
        r"((?:public|private|protected)\s+)?"  # Access modifier
        r"enum\s+"  # enum keyword
        r"(\w+)"  # Enum name
        r"(?:\s+implements\s+[\w,\s<>]+)?"  # Optional implements
        r"\s*{",  # Opening brace
        re.MULTILINE,
    )

    METHOD_PATTERN = re.compile(
        r"^(\s+)"  # Indentation (methods are indented)
        r"(@\w+(?:\([^)]*\))?\s+)*"  # Optional annotations
        r"((?:public|private|protected)\s+)?"  # Access modifier
        r"((?:static|final|abstract|synchronized|native)\s+)*"  # Other modifiers
        r"(?:<[\w,\s]+>\s+)?"  # Optional method generics
        r"([\w<>\[\],\s]+?)\s+"  # Return type
        r"(\w+)"  # Method name
        r"\s*\([^)]*\)"  # Parameters
        r"(?:\s+throws\s+[\w,\s]+)?"  # Optional throws
        r"\s*{",  # Opening brace
        re.MULTILINE,
    )

    CONSTRUCTOR_PATTERN = re.compile(
        r"^(\s+)"  # Indentation
        r"(@\w+(?:\([^)]*\))?\s+)*"  # Optional annotations
        r"((?:public|private|protected)\s+)?"  # Access modifier
        r"(\w+)"  # Class name (constructor name matches class)
        r"\s*\([^)]*\)"  # Parameters
        r"(?:\s+throws\s+[\w,\s]+)?"  # Optional throws
        r"\s*{",  # Opening brace
        re.MULTILINE,
    )

    ANNOTATION_PATTERN = re.compile(
        r"^(\s*)(@\w+(?:\([^)]*\))?)\s*$",
        re.MULTILINE,
    )

    def __init__(self, code: str):
        self.code = code
        self.lines = code.splitlines(keepends=True)
        self.brace_matcher = BraceMatcher(code)

    def find_symbols(self) -> list[PolyglotSymbolLocation]:
        """Find all class, interface, enum, and method symbols."""
        symbols: list[PolyglotSymbolLocation] = []

        symbols.extend(self._find_classes())
        symbols.extend(self._find_interfaces())
        symbols.extend(self._find_enums())

        return symbols

    def _find_classes(self) -> list[PolyglotSymbolLocation]:
        """Find all class definitions with their methods."""
        symbols: list[PolyglotSymbolLocation] = []

        for match in self.CLASS_PATTERN.finditer(self.code):
            class_name = match.group(4)
            line_start = self.code[: match.start()].count("\n") + 1

            # Check for annotations above the class
            line_start = self._find_annotation_start(line_start)

            line_end = self.brace_matcher.find_block_end(line_start)

            modifiers = []
            if match.group(2):
                modifiers.append(match.group(2).strip())
            if match.group(3):
                for mod in match.group(3).split():
                    modifiers.append(mod.strip())

            decorators = self._get_annotations(line_start)

            class_symbol = PolyglotSymbolLocation(
                name=class_name,
                symbol_type="class",
                line_start=line_start,
                line_end=line_end,
                col_start=len(match.group(1)),
                col_end=0,
                modifiers=modifiers,
                decorators=decorators,
                raw_text=self._get_lines(line_start, line_end),
            )
            symbols.append(class_symbol)

            # Find methods within this class
            symbols.extend(self._find_methods_in_class(class_name, line_start, line_end))

        return symbols

    def _find_methods_in_class(self, class_name: str, class_start: int, class_end: int) -> list[PolyglotSymbolLocation]:
        """Find methods and constructors within a class."""
        methods: list[PolyglotSymbolLocation] = []
        class_code = self._get_lines(class_start, class_end)
        class_offset = sum(len(self.lines[i]) for i in range(class_start - 1))

        # Find regular methods
        for match in self.METHOD_PATTERN.finditer(class_code):
            method_name = match.group(6)
            if method_name in ("if", "for", "while", "switch", "try", "catch"):
                continue  # Skip control structures

            rel_line_start = class_code[: match.start()].count("\n") + 1
            abs_line_start = class_start + rel_line_start - 1

            # Check for annotations
            abs_line_start = self._find_annotation_start(abs_line_start)

            method_brace_pos = class_offset + match.end() - 1
            method_end_pos = self.brace_matcher.find_matching_brace(method_brace_pos)
            if method_end_pos == -1:
                continue

            abs_line_end = self.code[:method_end_pos].count("\n") + 1

            modifiers = []
            if match.group(3):
                modifiers.append(match.group(3).strip())
            if match.group(4):
                for mod in match.group(4).split():
                    modifiers.append(mod.strip())

            decorators = self._get_annotations(abs_line_start)

            methods.append(
                PolyglotSymbolLocation(
                    name=method_name,
                    symbol_type="method",
                    line_start=abs_line_start,
                    line_end=abs_line_end,
                    col_start=len(match.group(1)),
                    col_end=0,
                    parent_name=class_name,
                    modifiers=modifiers,
                    decorators=decorators,
                    raw_text=self._get_lines(abs_line_start, abs_line_end),
                )
            )

        # Find constructors
        for match in self.CONSTRUCTOR_PATTERN.finditer(class_code):
            ctor_name = match.group(4)
            if ctor_name != class_name:
                continue  # Only actual constructors

            rel_line_start = class_code[: match.start()].count("\n") + 1
            abs_line_start = class_start + rel_line_start - 1
            abs_line_start = self._find_annotation_start(abs_line_start)

            ctor_brace_pos = class_offset + match.end() - 1
            ctor_end_pos = self.brace_matcher.find_matching_brace(ctor_brace_pos)
            if ctor_end_pos == -1:
                continue

            abs_line_end = self.code[:ctor_end_pos].count("\n") + 1

            modifiers = []
            if match.group(3):
                modifiers.append(match.group(3).strip())

            decorators = self._get_annotations(abs_line_start)

            methods.append(
                PolyglotSymbolLocation(
                    name="<init>",  # Java convention for constructors
                    symbol_type="constructor",
                    line_start=abs_line_start,
                    line_end=abs_line_end,
                    col_start=len(match.group(1)),
                    col_end=0,
                    parent_name=class_name,
                    modifiers=modifiers,
                    decorators=decorators,
                    raw_text=self._get_lines(abs_line_start, abs_line_end),
                )
            )

        return methods

    def _find_interfaces(self) -> list[PolyglotSymbolLocation]:
        """Find interface definitions."""
        interfaces: list[PolyglotSymbolLocation] = []

        for match in self.INTERFACE_PATTERN.finditer(self.code):
            interface_name = match.group(3)
            line_start = self.code[: match.start()].count("\n") + 1
            line_start = self._find_annotation_start(line_start)
            line_end = self.brace_matcher.find_block_end(line_start)

            modifiers = []
            if match.group(2):
                modifiers.append(match.group(2).strip())

            decorators = self._get_annotations(line_start)

            interfaces.append(
                PolyglotSymbolLocation(
                    name=interface_name,
                    symbol_type="interface",
                    line_start=line_start,
                    line_end=line_end,
                    col_start=len(match.group(1)),
                    col_end=0,
                    modifiers=modifiers,
                    decorators=decorators,
                    raw_text=self._get_lines(line_start, line_end),
                )
            )

        return interfaces

    def _find_enums(self) -> list[PolyglotSymbolLocation]:
        """Find enum definitions."""
        enums: list[PolyglotSymbolLocation] = []

        for match in self.ENUM_PATTERN.finditer(self.code):
            enum_name = match.group(3)
            line_start = self.code[: match.start()].count("\n") + 1
            line_start = self._find_annotation_start(line_start)
            line_end = self.brace_matcher.find_block_end(line_start)

            modifiers = []
            if match.group(2):
                modifiers.append(match.group(2).strip())

            decorators = self._get_annotations(line_start)

            enums.append(
                PolyglotSymbolLocation(
                    name=enum_name,
                    symbol_type="enum",
                    line_start=line_start,
                    line_end=line_end,
                    col_start=len(match.group(1)),
                    col_end=0,
                    modifiers=modifiers,
                    decorators=decorators,
                    raw_text=self._get_lines(line_start, line_end),
                )
            )

        return enums

    def _find_annotation_start(self, symbol_line: int) -> int:
        """Find the start line including annotations above a symbol."""
        line_idx = symbol_line - 1
        while line_idx > 0:
            prev_line = self.lines[line_idx - 1].strip()
            if prev_line.startswith("@"):
                line_idx -= 1
            elif prev_line == "" or prev_line.startswith("//") or prev_line.startswith("/*"):
                line_idx -= 1
            else:
                break
        return line_idx + 1

    def _get_annotations(self, start_line: int) -> list[str]:
        """Get annotations from lines above start_line."""
        annotations: list[str] = []
        line_idx = start_line - 1
        while line_idx >= 0:
            line = self.lines[line_idx].strip()
            if line.startswith("@"):
                annotations.insert(0, line)
            elif line == "" or line.startswith("//"):
                pass
            else:
                break
            line_idx -= 1
        return annotations

    def _get_lines(self, start: int, end: int) -> str:
        """Get source lines (1-indexed, inclusive)."""
        return "".join(self.lines[start - 1 : end])


class PolyglotPatcher:
    """
    Multi-language surgical patcher for JS, TS, and Java.

    [20251221_FEATURE] Extends patching capability beyond Python.

    Example:
        >>> # JavaScript
        >>> patcher = PolyglotPatcher.from_file("utils.js")
        >>> patcher.update_function("calculateTax", new_code)
        >>> patcher.save()

        >>> # TypeScript
        >>> patcher = PolyglotPatcher.from_file("service.ts")
        >>> patcher.update_class("UserService", new_class_code)
        >>> patcher.save()

        >>> # Java
        >>> patcher = PolyglotPatcher.from_file("Calculator.java")
        >>> patcher.update_method("Calculator", "add", new_method_code)
        >>> patcher.save()
    """

    LANGUAGE_EXTENSIONS = {
        ".js": PatchLanguage.JAVASCRIPT,
        ".mjs": PatchLanguage.JAVASCRIPT,
        ".cjs": PatchLanguage.JAVASCRIPT,
        ".jsx": PatchLanguage.JAVASCRIPT,
        ".ts": PatchLanguage.TYPESCRIPT,
        ".mts": PatchLanguage.TYPESCRIPT,
        ".cts": PatchLanguage.TYPESCRIPT,
        ".tsx": PatchLanguage.TYPESCRIPT,
        ".java": PatchLanguage.JAVA,
    }

    def __init__(self, code: str, language: PatchLanguage, file_path: str | None = None):
        """
        Initialize the polyglot patcher.

        Args:
            code: Source code to modify
            language: Programming language
            file_path: Path to source file (required for save())
        """
        self.original_code = code
        self.current_code = code
        self.language = language
        self.file_path = file_path
        self._lines = code.splitlines(keepends=True)
        self._symbols: dict[str, PolyglotSymbolLocation] = {}
        self._parsed = False
        self._modified = False
        self._backup_path: str | None = None

    @classmethod
    def from_file(
        cls,
        file_path: str,
        language: PatchLanguage | None = None,
        encoding: str = "utf-8",
    ) -> PolyglotPatcher:
        """
        Create a patcher by reading from a file.

        Args:
            file_path: Path to source file
            language: Language (auto-detected if None)
            encoding: File encoding

        Returns:
            PolyglotPatcher instance
        """
        if not os.path.isfile(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        # Auto-detect language
        if language is None:
            ext = Path(file_path).suffix.lower()
            if ext in cls.LANGUAGE_EXTENSIONS:
                language = cls.LANGUAGE_EXTENSIONS[ext]
            else:
                raise ValueError(f"Cannot detect language for extension: {ext}")

        try:
            with open(file_path, encoding=encoding) as f:
                code = f.read()
        except (OSError, UnicodeDecodeError) as e:
            # [20260108_BUGFIX] Added error handling for file read and encoding errors
            raise ValueError(f"Cannot read file {file_path}: {e}")

        return cls(code, language, file_path=os.path.abspath(file_path))

    def _ensure_parsed(self) -> None:
        """Parse the code and index all symbols."""
        if self._parsed:
            return

        if self.language in (PatchLanguage.JAVASCRIPT, PatchLanguage.TYPESCRIPT):
            parser = JavaScriptParser(
                self.current_code,
                is_typescript=(self.language == PatchLanguage.TYPESCRIPT),
            )
        elif self.language == PatchLanguage.JAVA:
            parser = JavaParser(self.current_code)
        else:
            raise ValueError(f"Unsupported language: {self.language}")

        symbols = parser.find_symbols()
        self._symbols = {s.qualified_name: s for s in symbols}
        self._parsed = True

    def list_symbols(self) -> list[PolyglotSymbolLocation]:
        """List all symbols in the code."""
        self._ensure_parsed()
        return list(self._symbols.values())

    def find_symbol(self, name: str) -> PolyglotSymbolLocation | None:
        """Find a symbol by name."""
        self._ensure_parsed()
        return self._symbols.get(name)

    def _apply_patch(self, symbol: PolyglotSymbolLocation, new_code: str) -> tuple[str, int, int]:
        """Apply a patch replacing a symbol."""
        lines = self.current_code.splitlines(keepends=True)

        start_line = symbol.line_start
        end_line = symbol.line_end

        # Preserve original indentation
        original_indent = ""
        if start_line <= len(lines):
            original_line = lines[start_line - 1]
            original_indent = original_line[: len(original_line) - len(original_line.lstrip())]

        # Prepare replacement
        new_lines = new_code.splitlines(keepends=True)
        if new_lines and not new_lines[-1].endswith("\n"):
            new_lines[-1] += "\n"

        # Adjust indentation
        if new_lines:
            first_non_empty = next((line for line in new_lines if line.strip()), new_lines[0])
            new_base_indent = first_non_empty[: len(first_non_empty) - len(first_non_empty.lstrip())]

            if new_base_indent != original_indent:
                adjusted = []
                for line in new_lines:
                    if line.strip():
                        if line.startswith(new_base_indent):
                            line = original_indent + line[len(new_base_indent) :]
                    adjusted.append(line)
                new_lines = adjusted

        lines_removed = end_line - start_line + 1
        lines_added = len(new_lines)

        result = lines[: start_line - 1] + new_lines + lines[end_line:]
        return "".join(result), lines_removed, lines_added

    def update_function(self, name: str, new_code: str) -> PatchResult:
        """
        Replace a function definition.

        Args:
            name: Function name
            new_code: New function code

        Returns:
            PatchResult
        """
        self._ensure_parsed()

        symbol = self._symbols.get(name)
        if not symbol:
            return PatchResult(
                success=False,
                file_path=self.file_path or "",
                target_name=name,
                target_type="function",
                error=f"Function '{name}' not found",
            )

        if symbol.symbol_type != "function":
            return PatchResult(
                success=False,
                file_path=self.file_path or "",
                target_name=name,
                target_type="function",
                error=f"'{name}' is a {symbol.symbol_type}, not a function",
            )

        lines_before = symbol.line_end - symbol.line_start + 1
        new_code_str, _, lines_added = self._apply_patch(symbol, new_code)

        self.current_code = new_code_str
        self._parsed = False
        self._modified = True

        return PatchResult(
            success=True,
            file_path=self.file_path or "",
            target_name=name,
            target_type="function",
            lines_before=lines_before,
            lines_after=lines_added,
        )

    def update_class(self, name: str, new_code: str) -> PatchResult:
        """
        Replace a class/interface definition.

        Args:
            name: Class or interface name
            new_code: New class code

        Returns:
            PatchResult
        """
        self._ensure_parsed()

        symbol = self._symbols.get(name)
        if not symbol:
            return PatchResult(
                success=False,
                file_path=self.file_path or "",
                target_name=name,
                target_type="class",
                error=f"Class '{name}' not found",
            )

        if symbol.symbol_type not in ("class", "interface", "enum"):
            return PatchResult(
                success=False,
                file_path=self.file_path or "",
                target_name=name,
                target_type="class",
                error=f"'{name}' is a {symbol.symbol_type}, not a class",
            )

        lines_before = symbol.line_end - symbol.line_start + 1
        new_code_str, _, lines_added = self._apply_patch(symbol, new_code)

        self.current_code = new_code_str
        self._parsed = False
        self._modified = True

        return PatchResult(
            success=True,
            file_path=self.file_path or "",
            target_name=name,
            target_type=symbol.symbol_type,
            lines_before=lines_before,
            lines_after=lines_added,
        )

    def update_method(self, class_name: str, method_name: str, new_code: str) -> PatchResult:
        """
        Replace a method within a class.

        Args:
            class_name: Containing class name
            method_name: Method name
            new_code: New method code

        Returns:
            PatchResult
        """
        self._ensure_parsed()

        key = f"{class_name}.{method_name}"
        symbol = self._symbols.get(key)

        if not symbol:
            return PatchResult(
                success=False,
                file_path=self.file_path or "",
                target_name=key,
                target_type="method",
                error=f"Method '{method_name}' not found in class '{class_name}'",
            )

        if symbol.symbol_type not in ("method", "constructor"):
            return PatchResult(
                success=False,
                file_path=self.file_path or "",
                target_name=key,
                target_type="method",
                error=f"'{key}' is a {symbol.symbol_type}, not a method",
            )

        lines_before = symbol.line_end - symbol.line_start + 1
        new_code_str, _, lines_added = self._apply_patch(symbol, new_code)

        self.current_code = new_code_str
        self._parsed = False
        self._modified = True

        return PatchResult(
            success=True,
            file_path=self.file_path or "",
            target_name=key,
            target_type=symbol.symbol_type,
            lines_before=lines_before,
            lines_after=lines_added,
        )

    def update_interface(self, name: str, new_code: str) -> PatchResult:
        """
        Replace an interface definition (TypeScript/Java).

        Args:
            name: Interface name
            new_code: New interface code

        Returns:
            PatchResult
        """
        return self.update_class(name, new_code)

    def get_modified_code(self) -> str:
        """Get the current (possibly modified) code."""
        return self.current_code

    def save(self, backup: bool = True) -> str | None:
        """
        Write modified code back to file.

        Args:
            backup: Create backup before saving

        Returns:
            Backup file path if created
        """
        if not self.file_path:
            raise ValueError("Cannot save: no file_path specified")

        if not self._modified:
            return None

        backup_path = None
        if backup:
            backup_path = f"{self.file_path}.bak"
            shutil.copy2(self.file_path, backup_path)
            self._backup_path = backup_path

        dir_path = os.path.dirname(self.file_path)
        with tempfile.NamedTemporaryFile(mode="w", dir=dir_path, delete=False, suffix=".tmp") as f:
            f.write(self.current_code)
            temp_path = f.name

        os.replace(temp_path, self.file_path)
        self._modified = False
        self.original_code = self.current_code

        return backup_path

    def rename_symbol(self, target_type: str, target_name: str, new_name: str) -> PatchResult:
        """
        Rename a symbol (function, class, or method) in JS/TS/Java file.

        [20251231_FEATURE] JavaScript/TypeScript/Java rename support for Community tier.

        This updates:
        - The definition (function/class/method declaration)
        - All references within the same file (calls, type annotations, etc.)

        Args:
            target_type: "function", "class", or "method"
            target_name: Current name (e.g., "myFunc" or "ClassName.methodName")
            new_name: New name (e.g., "newFunc" or "newMethodName")

        Returns:
            PatchResult with success status
        """
        if self.language in (PatchLanguage.JAVASCRIPT, PatchLanguage.TYPESCRIPT):
            valid, reason = _is_valid_js_identifier(new_name)
            if not valid:
                return PatchResult(
                    success=False,
                    file_path=self.file_path or "",
                    target_name=target_name,
                    target_type=target_type,
                    error=f"Invalid JavaScript/TypeScript identifier: {new_name}{reason}",
                )

        self._ensure_parsed()

        # For methods, use qualified name lookup
        if target_type == "method" and "." not in target_name:
            return PatchResult(
                success=False,
                file_path=self.file_path or "",
                target_name=target_name,
                target_type=target_type,
                error="Method name must be qualified as 'ClassName.methodName'",
            )

        symbol = self._symbols.get(target_name)
        if not symbol:
            return PatchResult(
                success=False,
                file_path=self.file_path or "",
                target_name=target_name,
                target_type=target_type,
                error=f"{target_type.capitalize()} '{target_name}' not found",
            )

        expected_types = {
            "function": {"function"},
            "class": {"class", "interface"},
            "method": {"method", "constructor"},
        }
        if symbol.symbol_type not in expected_types.get(target_type, set()):
            return PatchResult(
                success=False,
                file_path=self.file_path or "",
                target_name=target_name,
                target_type=target_type,
                error=f"'{target_name}' is a {symbol.symbol_type}, not a {target_type}",
            )

        # Get the short name for replacement
        if target_type == "method":
            old_short_name = target_name.split(".")[-1]
        else:
            old_short_name = target_name

        # 1. Rename the definition using regex replacement
        lines = self.current_code.splitlines(keepends=True)
        def_line_idx = symbol.line_start - 1

        if def_line_idx >= len(lines):
            return PatchResult(
                success=False,
                file_path=self.file_path or "",
                target_name=target_name,
                target_type=target_type,
                error=f"Definition line {symbol.line_start} out of range",
            )

        def_line = lines[def_line_idx]

        # Build pattern based on target type and language
        if target_type == "function":
            # Match: function name, const name =, let name =, var name =, async function name
            patterns = [
                (
                    rf"(function\s+){re.escape(old_short_name)}(\s*[\(<])",
                    rf"\g<1>{new_name}\g<2>",
                ),
                (
                    rf"(const|let|var)(\s+){re.escape(old_short_name)}(\s*=)",
                    rf"\g<1>\g<2>{new_name}\g<3>",
                ),
                (
                    rf"(async\s+function\s+){re.escape(old_short_name)}(\s*[\(<])",
                    rf"\g<1>{new_name}\g<2>",
                ),
            ]
        elif target_type == "class":
            patterns = [
                (
                    rf"(class\s+){re.escape(old_short_name)}(\s*[{{<]|\s+extends|\s+implements)",
                    rf"\g<1>{new_name}\g<2>",
                ),
                (
                    rf"(interface\s+){re.escape(old_short_name)}(\s*[{{<]|\s+extends)",
                    rf"\g<1>{new_name}\g<2>",
                ),
            ]
        elif target_type == "method":
            # Match method definitions: methodName(, async methodName(, get methodName(, set methodName(
            patterns = [
                (
                    rf"(\s+)(async\s+)?{re.escape(old_short_name)}(\s*[\(<])",
                    rf"\g<1>\g<2>{new_name}\g<3>",
                ),
                (
                    rf"(\s+)(get|set)(\s+){re.escape(old_short_name)}(\s*[\(<])",
                    rf"\g<1>\g<2>\g<3>{new_name}\g<4>",
                ),
                (
                    rf"(\s+)(static\s+)?(async\s+)?{re.escape(old_short_name)}(\s*[\(<])",
                    rf"\g<1>\g<2>\g<3>{new_name}\g<4>",
                ),
            ]
        else:
            patterns = []

        renamed_def = False
        for pattern, replacement in patterns:
            new_def_line, count = re.subn(pattern, replacement, def_line, count=1)
            if count > 0:
                lines[def_line_idx] = new_def_line
                renamed_def = True
                break

        if not renamed_def:
            return PatchResult(
                success=False,
                file_path=self.file_path or "",
                target_name=target_name,
                target_type=target_type,
                error=f"Could not locate definition of '{old_short_name}' on line {symbol.line_start}",
            )

        self.current_code = "".join(lines)

        # 2. Update all same-file references
        references_updated = self._rename_js_references(old_short_name, new_name, target_type, symbol.line_start)

        self._parsed = False
        self._modified = True

        return PatchResult(
            success=True,
            file_path=self.file_path or "",
            target_name=target_name,
            target_type=target_type,
            lines_before=1,
            lines_after=1 + references_updated,
        )

    def _rename_js_references(self, old_name: str, new_name: str, target_type: str, definition_line: int) -> int:
        """
        Rename references to a symbol in JS/TS code.

        [20251231_FEATURE] Same-file reference updates for JS/TS.

        Uses regex-based replacement since we don't have a full JS AST.
        Conservative approach: only rename clear identifier patterns.

        Returns:
            Number of references updated
        """
        lines = self.current_code.splitlines(keepends=True)
        references_updated = 0

        # Pattern for identifiers (word boundary matching)
        # This matches the old name when it's a standalone identifier
        if target_type == "function":
            # Match function calls and references: oldName( or oldName, or oldName; etc.
            # But NOT .oldName (that would be a method/property)
            pattern = re.compile(rf"(?<![.\w]){re.escape(old_name)}(?=\s*[\(,;\)\]\}}\s]|$)")
        elif target_type == "class":
            # Match class references: new ClassName, : ClassName, extends ClassName, etc.
            pattern = re.compile(rf"(?<![.\w]){re.escape(old_name)}(?=\s*[\(,;\)\]\}}<:\s]|$)")
        elif target_type == "method":
            # Match method calls via this. or object.
            pattern = re.compile(rf"(?<=\.){re.escape(old_name)}(?=\s*[\(])")
        else:
            return 0

        for i, line in enumerate(lines):
            line_num = i + 1
            # Skip the definition line
            if line_num == definition_line:
                continue

            # Skip import/export statements for function/class (cross-file concern)
            if target_type in ("function", "class"):
                stripped = line.strip()
                if stripped.startswith(("import ", "export ", "from ")):
                    continue

            new_line, count = pattern.subn(new_name, line)
            if count > 0:
                lines[i] = new_line
                references_updated += count

        if references_updated > 0:
            self.current_code = "".join(lines)

        return references_updated

    def discard_changes(self) -> None:
        """Discard all modifications."""
        self.current_code = self.original_code
        self._parsed = False
        self._modified = False


# =============================================================================
# UNIFIED PATCHER - Language-Agnostic Entry Point
# =============================================================================


class UnifiedPatcher:
    """
    Unified patching interface that routes to appropriate language patcher.

    [20251221_FEATURE] Single entry point for all languages.

    Example:
        >>> patcher = UnifiedPatcher.from_file("code.py")  # Uses SurgicalPatcher
        >>> patcher = UnifiedPatcher.from_file("code.ts")  # Uses PolyglotPatcher
        >>> patcher.update_function("myFunc", new_code)
        >>> patcher.save()
    """

    def __init__(
        self,
        patcher: SurgicalPatcher | PolyglotPatcher,
        language: PatchLanguage,
    ):
        self._patcher = patcher
        self.language = language

    @classmethod
    def from_file(cls, file_path: str, encoding: str = "utf-8") -> UnifiedPatcher:
        """
        Create a unified patcher from a file.

        Args:
            file_path: Path to source file
            encoding: File encoding

        Returns:
            UnifiedPatcher instance
        """
        ext = Path(file_path).suffix.lower()

        if ext in (".py", ".pyw", ".pyi"):
            patcher = SurgicalPatcher.from_file(file_path, encoding=encoding)
            return cls(patcher, PatchLanguage.PYTHON)
        elif ext in PolyglotPatcher.LANGUAGE_EXTENSIONS:
            language = PolyglotPatcher.LANGUAGE_EXTENSIONS[ext]
            patcher = PolyglotPatcher.from_file(file_path, language, encoding=encoding)
            return cls(patcher, language)
        else:
            raise ValueError(f"Unsupported file extension: {ext}")

    @classmethod
    def from_code(cls, code: str, language: PatchLanguage, file_path: str | None = None) -> UnifiedPatcher:
        """
        Create a unified patcher from code string.

        Args:
            code: Source code
            language: Programming language
            file_path: Optional file path for saving

        Returns:
            UnifiedPatcher instance
        """
        if language == PatchLanguage.PYTHON:
            patcher = SurgicalPatcher(code, file_path)
        else:
            patcher = PolyglotPatcher(code, language, file_path)
        return cls(patcher, language)

    def update_function(self, name: str, new_code: str) -> PatchResult:
        """Replace a function definition."""
        return self._patcher.update_function(name, new_code)

    def update_class(self, name: str, new_code: str) -> PatchResult:
        """Replace a class definition."""
        return self._patcher.update_class(name, new_code)

    def update_method(self, class_name: str, method_name: str, new_code: str) -> PatchResult:
        """Replace a method within a class."""
        return self._patcher.update_method(class_name, method_name, new_code)

    def get_modified_code(self) -> str:
        """Get the current (possibly modified) code."""
        return self._patcher.get_modified_code()

    @property
    def original_code(self) -> str:
        """[20260103_BUGFIX] Expose underlying original code for governance budget checks."""
        return getattr(self._patcher, "original_code", "")

    @property
    def current_code(self) -> str:
        """[20260103_BUGFIX] Expose current (possibly modified) code for budget diffing."""
        return getattr(self._patcher, "current_code", self.get_modified_code())

    def save(self, backup: bool = True) -> str | None:
        """Write modified code back to file."""
        return self._patcher.save(backup=backup)

    def rename_symbol(self, target_type: str, target_name: str, new_name: str) -> PatchResult:
        """[20260103_BUGFIX] Forward rename operations to the concrete patcher."""
        file_path = str(getattr(self._patcher, "file_path", ""))
        language = getattr(self._patcher, "language", None)
        is_python = bool(
            file_path.endswith(".py")
            or language == PatchLanguage.PYTHON
            or (language and getattr(language, "name", "") == "PYTHON")
        )

        # [20260108_BUGFIX] Reject invalid Python identifiers before patching
        if is_python and not _is_valid_python_identifier(new_name):
            return PatchResult(
                success=False,
                file_path=file_path,
                target_name=target_name,
                target_type=target_type,
                error=f"Invalid Python identifier: {new_name}",
            )

        is_js_ts = bool(
            language in (PatchLanguage.JAVASCRIPT, PatchLanguage.TYPESCRIPT)
            or (file_path.endswith((".js", ".jsx", ".ts", ".tsx", ".mts", ".cts")))
        )

        if is_js_ts:
            valid, reason = _is_valid_js_identifier(new_name)
            if not valid:
                return PatchResult(
                    success=False,
                    file_path=file_path,
                    target_name=target_name,
                    target_type=target_type,
                    error=f"Invalid JavaScript/TypeScript identifier: {new_name}{reason}",
                )

        return self._patcher.rename_symbol(target_type, target_name, new_name)

    def discard_changes(self) -> None:
        """Discard all modifications."""
        self._patcher.discard_changes()


# =============================================================================
# POLYGLOT CONVENIENCE FUNCTIONS
# =============================================================================


def update_js_function(file_path: str, function_name: str, new_code: str, backup: bool = True) -> PatchResult:
    """Update a JavaScript function in a file."""
    patcher = PolyglotPatcher.from_file(file_path, PatchLanguage.JAVASCRIPT)
    result = patcher.update_function(function_name, new_code)
    if result.success:
        result.backup_path = patcher.save(backup=backup)
    return result


def update_ts_function(file_path: str, function_name: str, new_code: str, backup: bool = True) -> PatchResult:
    """Update a TypeScript function in a file."""
    patcher = PolyglotPatcher.from_file(file_path, PatchLanguage.TYPESCRIPT)
    result = patcher.update_function(function_name, new_code)
    if result.success:
        result.backup_path = patcher.save(backup=backup)
    return result


def update_java_method(
    file_path: str,
    class_name: str,
    method_name: str,
    new_code: str,
    backup: bool = True,
) -> PatchResult:
    """Update a Java method in a file."""
    patcher = PolyglotPatcher.from_file(file_path, PatchLanguage.JAVA)
    result = patcher.update_method(class_name, method_name, new_code)
    if result.success:
        result.backup_path = patcher.save(backup=backup)
    return result


def update_java_class(file_path: str, class_name: str, new_code: str, backup: bool = True) -> PatchResult:
    """Update a Java class in a file."""
    patcher = PolyglotPatcher.from_file(file_path, PatchLanguage.JAVA)
    result = patcher.update_class(class_name, new_code)
    if result.success:
        result.backup_path = patcher.save(backup=backup)
    return result
