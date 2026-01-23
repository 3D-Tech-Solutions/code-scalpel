"""
Error-to-Diff Engine for Code Scalpel v3.0.0 "Autonomy".

Convert compiler errors, linter warnings, and test failures into actionable
code diffs that agents can apply.

[20251217_FEATURE] v3.0.0 Autonomy - Error-to-Diff Engine
"""

import ast
import difflib
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class ErrorType(Enum):
    """Categories of errors we can convert to diffs."""

    SYNTAX_ERROR = "syntax_error"
    TYPE_ERROR = "type_error"
    NAME_ERROR = "name_error"
    IMPORT_ERROR = "import_error"
    LINT_WARNING = "lint_warning"
    TEST_FAILURE = "test_failure"
    RUNTIME_ERROR = "runtime_error"


@dataclass
class FixHint:
    """A suggested fix for an error."""

    diff: str  # Unified diff format
    confidence: float  # 0.0-1.0 confidence in fix
    explanation: str  # Human-readable explanation
    ast_valid: bool  # True if diff produces valid AST
    alternative_fixes: list["FixHint"] = field(default_factory=list)


@dataclass
class ParsedError:
    """Parsed error information."""

    error_type: ErrorType
    message: str
    file_path: str
    line: int
    column: int | None = None


@dataclass
class ErrorAnalysis:
    """Analysis of an error with fix suggestions."""

    error_type: ErrorType
    message: str
    file_path: str
    line: int
    column: int | None
    fixes: list[FixHint]
    requires_human_review: bool


class ErrorToDiffEngine:
    """
    Convert errors to actionable diffs.

    Supports:
    - Python syntax errors → missing colons, parentheses, indentation
    - Python NameError → import suggestions, typo corrections
    - Python TypeError → argument fixes, type conversions
    - TypeScript/JavaScript compile errors → type annotations, imports
    - Java compile errors → missing imports, type mismatches
    - Test failures → assertion fixes, mock corrections
    - Lint warnings → style fixes, best practices
    """

    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.parsers = {
            "python": PythonErrorParser(),
            "typescript": TypeScriptErrorParser(),
            "javascript": JavaScriptErrorParser(),
            "java": JavaErrorParser(),
        }
        self.fix_generators = {
            ErrorType.SYNTAX_ERROR: SyntaxFixGenerator(),
            ErrorType.TYPE_ERROR: TypeFixGenerator(),
            ErrorType.NAME_ERROR: NameFixGenerator(),
            ErrorType.IMPORT_ERROR: ImportFixGenerator(),
            ErrorType.TEST_FAILURE: TestFixGenerator(),
            ErrorType.LINT_WARNING: LintFixGenerator(),
        }

    def analyze_error(self, error_output: str, language: str, source_code: str) -> ErrorAnalysis:
        """
        Parse error output and generate fix suggestions.

        Args:
            error_output: Raw error message from compiler/linter/test
            language: Programming language
            source_code: The code that produced the error

        Returns:
            ErrorAnalysis with categorized error and fix suggestions
        """
        # Parse error using language-specific parser
        parser = self.parsers.get(language)
        if not parser:
            return ErrorAnalysis(
                error_type=ErrorType.RUNTIME_ERROR,
                message=error_output,
                file_path="unknown",
                line=0,
                column=None,
                fixes=[],
                requires_human_review=True,
            )

        parsed = parser.parse(error_output)

        # Generate fixes
        generator = self.fix_generators.get(parsed.error_type)
        if not generator:
            return ErrorAnalysis(
                error_type=parsed.error_type,
                message=parsed.message,
                file_path=parsed.file_path,
                line=parsed.line,
                column=parsed.column,
                fixes=[],
                requires_human_review=True,
            )

        fixes = generator.generate_fixes(parsed=parsed, source_code=source_code, language=language)

        # Validate fixes produce valid AST (for Python only)
        validated_fixes = []
        for fix in fixes:
            if language == "python":
                try:
                    patched_code = self._apply_diff(source_code, fix.diff)
                    ast.parse(patched_code)  # Validate syntax
                    fix.ast_valid = True
                    validated_fixes.append(fix)
                except SyntaxError:
                    # [20251217_FEATURE] Invalid fix - reduce confidence
                    fix.ast_valid = False
                    fix.confidence *= 0.3
                    validated_fixes.append(fix)
                except (ValueError, TypeError):
                    # [20251217_FEATURE] Diff application error - skip fix
                    fix.ast_valid = False
                    fix.confidence *= 0.1
                    validated_fixes.append(fix)
            else:
                # For non-Python languages, mark as valid (no AST validation)
                fix.ast_valid = True
                validated_fixes.append(fix)

        # Sort by confidence
        validated_fixes.sort(key=lambda f: f.confidence, reverse=True)

        return ErrorAnalysis(
            error_type=parsed.error_type,
            message=parsed.message,
            file_path=parsed.file_path,
            line=parsed.line,
            column=parsed.column,
            fixes=validated_fixes,
            requires_human_review=not any(f.confidence > 0.8 for f in validated_fixes),
        )

    def _apply_diff(self, source: str, diff: str) -> str:
        """
        Apply simple diff to source code.

        This is a simplified diff application that handles line replacements.

        For v3.0.0, we support a minimal "old_line -> new_line" format but apply
        it in a line-aware and ambiguity-checked way:
        - If the old fragment does not appear, we return the source unchanged.
        - If it appears on exactly one line, we replace it only on that line.
        - If it appears on multiple lines, we *do not* apply the diff to avoid
          silently modifying the wrong location.

        [20251217_FEATURE] Simplified diff for v3.0.0, can be enhanced in v3.1.0
        [20251217_BUGFIX] Make diff application line-aware and avoid ambiguous edits
        """
        # For now, treat diff as a simple replacement instruction
        # Format: "old_line -> new_line"
        if " -> " not in diff:
            return source

        old_part, new_part = diff.split(" -> ", 1)
        old_part = old_part.strip()
        new_part = new_part.strip()

        # Split into lines while preserving original line endings
        lines = source.splitlines(keepends=True)

        # Find all line indices that contain the old_part
        matching_indices: list[int] = []
        for idx, line in enumerate(lines):
            if old_part and old_part in line:
                matching_indices.append(idx)

        # No matches: return source unchanged
        if not matching_indices:
            return source

        # Ambiguous matches on multiple lines: fail safe, do not modify
        if len(matching_indices) > 1:
            return source

        # Single unambiguous match: replace only within that line
        target_idx = matching_indices[0]
        lines[target_idx] = lines[target_idx].replace(old_part, new_part)

        return "".join(lines)


class PythonErrorParser:
    """Parse Python error messages."""

    def parse(self, error_output: str) -> ParsedError:
        """Parse Python error message."""
        # Extract file, line, and error type
        file_match = re.search(r'File "([^"]+)", line (\d+)', error_output)
        if file_match:
            file_path = file_match.group(1)
            line = int(file_match.group(2))
        else:
            file_path = "unknown"
            line = 0

        # Determine error type
        if "SyntaxError" in error_output or "IndentationError" in error_output:
            error_type = ErrorType.SYNTAX_ERROR
        elif "NameError" in error_output:
            error_type = ErrorType.NAME_ERROR
        elif "TypeError" in error_output:
            error_type = ErrorType.TYPE_ERROR
        elif "ImportError" in error_output or "ModuleNotFoundError" in error_output:
            error_type = ErrorType.IMPORT_ERROR
        elif "AssertionError" in error_output or "assert" in error_output.lower():
            error_type = ErrorType.TEST_FAILURE
        else:
            error_type = ErrorType.RUNTIME_ERROR

        return ParsedError(
            error_type=error_type,
            message=error_output,
            file_path=file_path,
            line=line,
            column=None,
        )


class TypeScriptErrorParser:
    """Parse TypeScript error messages."""

    def parse(self, error_output: str) -> ParsedError:
        """Parse TypeScript error message."""
        # Extract file and line number
        # Format: "file.ts(line,col): error TS####: message"
        file_match = re.search(r"([^\(]+)\((\d+),(\d+)\):", error_output)
        if file_match:
            file_path = file_match.group(1)
            line = int(file_match.group(2))
            column = int(file_match.group(3))
        else:
            file_path = "unknown"
            line = 0
            column = None

        # Determine error type
        if "Property" in error_output and "missing" in error_output:
            error_type = ErrorType.TYPE_ERROR
        elif "Cannot find" in error_output:
            error_type = ErrorType.IMPORT_ERROR
        else:
            error_type = ErrorType.RUNTIME_ERROR

        return ParsedError(
            error_type=error_type,
            message=error_output,
            file_path=file_path,
            line=line,
            column=column,
        )


class JavaScriptErrorParser:
    """Parse JavaScript error messages."""

    def parse(self, error_output: str) -> ParsedError:
        """Parse JavaScript error message."""
        # Similar to TypeScript but more lenient
        file_match = re.search(r"at ([^\s]+):(\d+):(\d+)", error_output)
        if file_match:
            file_path = file_match.group(1)
            line = int(file_match.group(2))
            column = int(file_match.group(3))
        else:
            file_path = "unknown"
            line = 0
            column = None

        # Determine error type
        if "SyntaxError" in error_output:
            error_type = ErrorType.SYNTAX_ERROR
        elif "ReferenceError" in error_output:
            error_type = ErrorType.NAME_ERROR
        elif "TypeError" in error_output:
            error_type = ErrorType.TYPE_ERROR
        else:
            error_type = ErrorType.RUNTIME_ERROR

        return ParsedError(
            error_type=error_type,
            message=error_output,
            file_path=file_path,
            line=line,
            column=column,
        )


class JavaErrorParser:
    """Parse Java compiler error messages."""

    def parse(self, error_output: str) -> ParsedError:
        """Parse Java compiler error message."""
        # Format: "File.java:line: error: message"
        file_match = re.search(r"([^\s]+\.java):(\d+):", error_output)
        if file_match:
            file_path = file_match.group(1)
            line = int(file_match.group(2))
        else:
            file_path = "unknown"
            line = 0

        # Determine error type
        if "cannot find symbol" in error_output:
            error_type = ErrorType.NAME_ERROR
        elif "incompatible types" in error_output:
            error_type = ErrorType.TYPE_ERROR
        else:
            error_type = ErrorType.RUNTIME_ERROR

        return ParsedError(
            error_type=error_type,
            message=error_output,
            file_path=file_path,
            line=line,
            column=None,
        )


class SyntaxFixGenerator:
    """Generate fixes for syntax errors."""

    SYNTAX_PATTERNS = {
        r"expected ['\"]?:['\"]? after .* definition": {
            "fix": "add_colon",
            "confidence": 0.95,
        },
        r"unexpected indent": {
            "fix": "indentation",
            "confidence": 0.9,
        },
        r"unmatched ['\"]?\)['\"]?": {
            "fix": "balance_parentheses",
            "confidence": 0.85,
        },
        r"invalid syntax": {
            "fix": "general_syntax",
            "confidence": 0.5,
        },
    }

    def generate_fixes(self, parsed: ParsedError, source_code: str, language: str) -> list[FixHint]:
        """Generate syntax fix suggestions."""
        fixes = []

        for pattern, fix_info in self.SYNTAX_PATTERNS.items():
            if re.search(pattern, parsed.message, re.IGNORECASE):
                fix_method = getattr(self, f"_fix_{fix_info['fix']}", None)
                if fix_method:
                    diff = fix_method(source_code, parsed.line, parsed.column)
                    if diff:
                        fixes.append(
                            FixHint(
                                diff=diff,
                                confidence=fix_info["confidence"],
                                explanation=f"Fix: {fix_info['fix'].replace('_', ' ')}",
                                ast_valid=False,  # Will be validated later
                                alternative_fixes=[],
                            )
                        )

        return fixes

    def _fix_add_colon(self, source: str, line: int, col: int | None) -> str | None:
        """Add missing colon after function/class definition."""
        lines = source.split("\n")
        if line < 1 or line > len(lines):
            return None

        target_line = lines[line - 1]

        # Find end of definition (before newline or comment)
        if not target_line.rstrip().endswith(":"):
            old_line = target_line.rstrip()
            new_line = old_line + ":"
            return f"{old_line} -> {new_line}"

        return None

    def _fix_indentation(self, source: str, line: int, col: int | None) -> str | None:
        """Fix indentation issues."""
        lines = source.split("\n")
        if line < 1 or line > len(lines):
            return None

        target_line = lines[line - 1]

        # Detect expected indentation from previous non-empty line
        expected_indent = 0
        for i in range(line - 2, -1, -1):
            if lines[i].strip():
                expected_indent = len(lines[i]) - len(lines[i].lstrip())
                if lines[i].rstrip().endswith(":"):
                    expected_indent += 4  # Python standard
                break

        # Fix indentation
        old_line = target_line.rstrip()
        new_line = " " * expected_indent + target_line.lstrip()
        if old_line != new_line:
            return f"{old_line} -> {new_line}"

        return None

    def _fix_balance_parentheses(self, source: str, line: int, col: int | None) -> str | None:
        """Balance unmatched parentheses."""
        lines = source.split("\n")
        if line < 1 or line > len(lines):
            return None

        # Count parentheses in the problematic line
        target_line = lines[line - 1]
        open_count = target_line.count("(")
        close_count = target_line.count(")")

        if open_count > close_count:
            # Add closing parentheses
            old_line = target_line.rstrip()
            new_line = old_line + ")" * (open_count - close_count)
            return f"{old_line} -> {new_line}"
        elif close_count > open_count:
            # [20251217_BUGFIX] Remove only the excess number of trailing closing parentheses
            # rather than stripping all of them, to preserve balanced parens like foo()).
            old_line = target_line.rstrip()
            excess = close_count - open_count
            chars = list(old_line)
            i = len(chars) - 1
            to_remove = excess
            while i >= 0 and to_remove > 0 and chars[i] == ")":
                chars.pop(i)
                to_remove -= 1
                i -= 1
            new_line = "".join(chars)
            return f"{old_line} -> {new_line}"

        return None

    def _fix_general_syntax(self, source: str, line: int, col: int | None) -> str | None:
        """Attempt general syntax fix (low confidence)."""
        # This is a placeholder for more complex fixes
        return None


class TypeFixGenerator:
    """Generate fixes for type errors."""

    def generate_fixes(self, parsed: ParsedError, source_code: str, language: str) -> list[FixHint]:
        """Generate type fix suggestions."""
        fixes = []

        # TypeScript missing property fix
        if language == "typescript" and "Property" in parsed.message:
            match = re.search(r"Property '(\w+)' is missing", parsed.message)
            if match:
                prop_name = match.group(1)
                fixes.append(
                    FixHint(
                        diff=f"Add property: {prop_name}",
                        confidence=0.8,
                        explanation=f"Add missing property '{prop_name}'",
                        ast_valid=True,
                        alternative_fixes=[],
                    )
                )

        return fixes


class NameFixGenerator:
    """Generate fixes for NameError (undefined names)."""

    def generate_fixes(self, parsed: ParsedError, source_code: str, language: str) -> list[FixHint]:
        """Generate name fix suggestions (typo corrections, imports)."""
        fixes = []

        # Extract undefined name
        # [20251217_FEATURE] Enhanced regex to capture complex identifiers
        name_match = re.search(r"name '([a-zA-Z_][\w.]*)' is not defined", parsed.message)
        if name_match:
            undefined_name = name_match.group(1)

            # Suggest typo corrections (look for similar names in source)
            similar_names = self._find_similar_names(source_code, undefined_name)
            for similar in similar_names[:3]:  # Top 3 suggestions
                confidence = self._calculate_similarity(undefined_name, similar)
                fixes.append(
                    FixHint(
                        diff=f"{undefined_name} -> {similar}",
                        confidence=confidence,
                        explanation=f"Fix typo: '{undefined_name}' → '{similar}'",
                        ast_valid=False,
                        alternative_fixes=[],
                    )
                )

            # [20251217_BUGFIX] Emit actionable import hints only for common stdlib modules
            common_stdlib_modules = {
                "os",
                "sys",
                "re",
                "json",
                "pathlib",
                "math",
                "itertools",
                "collections",
                "typing",
                "datetime",
                "subprocess",
                "logging",
                "functools",
            }
            if undefined_name in common_stdlib_modules:
                fixes.append(
                    FixHint(
                        diff=f"import {undefined_name}",
                        confidence=0.6,
                        explanation=f"Import standard library module '{undefined_name}'",
                        ast_valid=False,
                        alternative_fixes=[],
                    )
                )

        return fixes

    def _find_similar_names(self, source_code: str, target: str) -> list[str]:
        """Find similar variable/function names in source code."""
        # [20251217_FEATURE] Extract identifiers - works for Python, JS, TS, Java
        # Pattern matches: alphanumeric + underscore (Python/Java/JS/TS conventions)
        identifiers = set(re.findall(r"\b[a-zA-Z_]\w*\b", source_code))

        # Calculate similarity and sort
        similar = []
        for ident in identifiers:
            if ident != target and self._calculate_similarity(target, ident) > 0.6:
                similar.append(ident)

        similar.sort(key=lambda x: self._calculate_similarity(target, x), reverse=True)
        return similar

    def _calculate_similarity(self, s1: str, s2: str) -> float:
        """Calculate similarity ratio between two strings (0.0-1.0)."""
        return difflib.SequenceMatcher(None, s1.lower(), s2.lower()).ratio()


class ImportFixGenerator:
    """Generate fixes for import errors."""

    def generate_fixes(self, parsed: ParsedError, source_code: str, language: str) -> list[FixHint]:
        """Generate import fix suggestions."""
        fixes = []

        # Extract missing module name
        module_match = re.search(r"No module named '(\w+)'", parsed.message)
        if module_match:
            module_name = module_match.group(1)
            fixes.append(
                FixHint(
                    diff=f"Add import: import {module_name}",
                    confidence=0.7,
                    explanation=f"Install and import module '{module_name}'",
                    ast_valid=False,
                    alternative_fixes=[],
                )
            )

        return fixes


class TestFixGenerator:
    """Generate fixes for test failures."""

    def generate_fixes(self, parsed: ParsedError, source_code: str, language: str) -> list[FixHint]:
        """Generate test fix suggestions."""
        fixes = []

        # Assertion failures
        if "AssertionError" in parsed.message or "assert" in parsed.message.lower():
            fixes.extend(self._fix_assertion(parsed, source_code))

        # Mock-related failures
        if "mock" in parsed.message.lower() or "MagicMock" in parsed.message:
            fixes.append(
                FixHint(
                    diff="Review mock setup",
                    confidence=0.6,
                    explanation="Review mock object configuration",
                    ast_valid=False,
                    alternative_fixes=[],
                )
            )

        # Missing attribute/method
        if "AttributeError" in parsed.message:
            fixes.append(
                FixHint(
                    diff="Add missing attribute",
                    confidence=0.6,
                    explanation="Add the missing attribute to the class",
                    ast_valid=False,
                    alternative_fixes=[],
                )
            )

        return fixes

    def _fix_assertion(self, parsed: ParsedError, source_code: str) -> list[FixHint]:
        """
        Fix assertion failures by updating expected values.

        Example:
            AssertionError: assert 42 == 41
            Fix: Update expected value from 41 to 42
        """
        fixes = []

        # Extract actual vs expected from assertion message
        match = re.search(r"assert (\S+) == (\S+)", parsed.message)
        if match:
            actual, expected = match.groups()

            # Find assertion line and update expected value
            lines = source_code.split("\n")

            # If we have a specific line number, use it
            if 0 < parsed.line <= len(lines):
                line = lines[parsed.line - 1]
                if expected in line:
                    old_line = line.strip()
                    new_line = line.replace(expected, actual, 1).strip()

                    fixes.append(
                        FixHint(
                            diff=f"{old_line} -> {new_line}",
                            confidence=0.7,
                            explanation=f"Update expected value from {expected} to {actual}",
                            ast_valid=False,
                            alternative_fixes=[],
                        )
                    )
            else:
                # No specific line number, search all lines for the assertion
                for _i, line in enumerate(lines):
                    if expected in line and "assert" in line:
                        old_line = line.strip()
                        new_line = line.replace(expected, actual, 1).strip()

                        fixes.append(
                            FixHint(
                                diff=f"{old_line} -> {new_line}",
                                confidence=0.7,
                                explanation=f"Update expected value from {expected} to {actual}",
                                ast_valid=False,
                                alternative_fixes=[],
                            )
                        )
                        break  # Only fix the first match

        return fixes


class LintFixGenerator:
    """Generate fixes for linter warnings."""

    def generate_fixes(self, parsed: ParsedError, source_code: str, language: str) -> list[FixHint]:
        """Generate linter fix suggestions."""
        fixes = []

        # Common linter patterns
        if "unused" in parsed.message.lower():
            fixes.append(
                FixHint(
                    diff="Remove unused variable/import",
                    confidence=0.8,
                    explanation="Remove the unused code",
                    ast_valid=False,
                    alternative_fixes=[],
                )
            )

        if "undefined" in parsed.message.lower():
            fixes.append(
                FixHint(
                    diff="Define the variable before use",
                    confidence=0.7,
                    explanation="Ensure the variable is defined before use",
                    ast_valid=False,
                    alternative_fixes=[],
                )
            )

        return fixes
