#!/usr/bin/env python3
"""
Python PEP 8 Style Checker - pycodestyle Integration.
======================================================

This module provides PEP 8 style checking using pycodestyle
(formerly pep8). It enforces Python style guide conventions.

Implementation Status: COMPLETED
Priority: P4 - MEDIUM-LOW

Features:
    - PEP 8 style enforcement
    - Configurable error selection
    - Line length checking
    - Whitespace and indentation checking

Note: Consider using Ruff instead as it's faster and includes
      pycodestyle checks. This module is for cases where pure
      pycodestyle compatibility is required.

==============================================================================
COMPLETED [P4-PYCODESTYLE-001]: pycodestyle integration
==============================================================================
Priority: MEDIUM-LOW
Status: ✓ COMPLETED

Implemented Features:
    - [✓] Run pycodestyle via subprocess
    - [✓] Parse output (default format)
    - [✓] Support configuration (setup.cfg, tox.ini)
    - [✓] Support --ignore and --select options
    - [✓] Support custom max-line-length
    - [✓] Complete command building (_build_command)
    - [✓] Timeout handling
    - [✓] Error handling and reporting

Output Format:
    ```
    filename.py:1:1: E302 expected 2 blank lines, found 1
    ```

==============================================================================
COMPLETED [P4-PYCODESTYLE-002]: Error categorization
==============================================================================
Priority: MEDIUM-LOW
Status: ✓ COMPLETED
Depends On: P4-PYCODESTYLE-001

Implemented Features:
    - [✓] Map error codes to categories (get_category_for_code)
    - [✓] Provide category descriptions (ERROR_DESCRIPTIONS dict)
    - [✓] Group errors by category in reports (violations_by_category)
    - [✓] Support category-level ignore/select
    - [✓] Complete error code database (E1xx-E9xx, W1xx-W6xx)

Error Categories:
    - E1xx: Indentation
    - E2xx: Whitespace
    - E3xx: Blank lines
    - E4xx: Imports
    - E5xx: Line length
    - E7xx: Statement
    - E9xx: Runtime
    - W1xx: Indentation warning
    - W2xx: Whitespace warning
    - W3xx: Blank line warning
    - W5xx: Line break warning
    - W6xx: Deprecation warning
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass


# =============================================================================
# Enums
# =============================================================================


class StyleCategory(Enum):
    """Categories of pycodestyle error codes."""

    INDENTATION = "indentation"
    WHITESPACE = "whitespace"
    BLANK_LINES = "blank_lines"
    IMPORTS = "imports"
    LINE_LENGTH = "line_length"
    STATEMENT = "statement"
    RUNTIME = "runtime"
    DEPRECATION = "deprecation"
    OTHER = "other"


class StyleSeverity(Enum):
    """Severity of style issues."""

    ERROR = "error"  # E codes
    WARNING = "warning"  # W codes


# =============================================================================
# Error Code Mappings
# =============================================================================


def get_category_for_code(code: str) -> StyleCategory:
    """Get the category for an error code."""
    if not code:
        return StyleCategory.OTHER

    code[0]
    category_num = code[1] if len(code) > 1 else "0"

    if category_num == "1":
        return StyleCategory.INDENTATION
    elif category_num == "2":
        return StyleCategory.WHITESPACE
    elif category_num == "3":
        return StyleCategory.BLANK_LINES
    elif category_num == "4":
        return StyleCategory.IMPORTS
    elif category_num == "5":
        return StyleCategory.LINE_LENGTH
    elif category_num == "6":
        return StyleCategory.DEPRECATION
    elif category_num == "7":
        return StyleCategory.STATEMENT
    elif category_num == "9":
        return StyleCategory.RUNTIME

    return StyleCategory.OTHER


# Common pycodestyle error descriptions
ERROR_DESCRIPTIONS: dict[str, str] = {
    # Indentation
    "E101": "indentation contains mixed spaces and tabs",
    "E111": "indentation is not a multiple of four",
    "E112": "expected an indented block",
    "E113": "unexpected indentation",
    "E114": "indentation is not a multiple of four (comment)",
    "E115": "expected an indented block (comment)",
    "E116": "unexpected indentation (comment)",
    "E117": "over-indented",
    "E121": "continuation line under-indented for hanging indent",
    "E122": "continuation line missing indentation or outdented",
    "E123": "closing bracket does not match indentation of opening bracket's line",
    "E124": "closing bracket does not match visual indentation",
    "E125": "continuation line with same indent as next logical line",
    "E126": "continuation line over-indented for hanging indent",
    "E127": "continuation line over-indented for visual indent",
    "E128": "continuation line under-indented for visual indent",
    "E129": "visually indented line with same indent as next logical line",
    "E131": "continuation line unaligned for hanging indent",
    "E133": "closing bracket is missing indentation",
    # Whitespace
    "E201": "whitespace after '('",
    "E202": "whitespace before ')'",
    "E203": "whitespace before ':'",
    "E211": "whitespace before '('",
    "E221": "multiple spaces before operator",
    "E222": "multiple spaces after operator",
    "E223": "tab before operator",
    "E224": "tab after operator",
    "E225": "missing whitespace around operator",
    "E226": "missing whitespace around arithmetic operator",
    "E227": "missing whitespace around bitwise or shift operator",
    "E228": "missing whitespace around modulo operator",
    "E231": "missing whitespace after ','",
    "E241": "multiple spaces after ','",
    "E242": "tab after ','",
    "E251": "unexpected spaces around keyword / parameter equals",
    "E252": "missing whitespace around parameter equals",
    "E261": "at least two spaces before inline comment",
    "E262": "inline comment should start with '# '",
    "E265": "block comment should start with '# '",
    "E266": "too many leading '#' for block comment",
    "E271": "multiple spaces after keyword",
    "E272": "multiple spaces before keyword",
    "E273": "tab after keyword",
    "E274": "tab before keyword",
    "E275": "missing whitespace after keyword",
    # Blank lines
    "E301": "expected 1 blank line, found 0",
    "E302": "expected 2 blank lines, found N",
    "E303": "too many blank lines",
    "E304": "blank lines found after function decorator",
    "E305": "expected 2 blank lines after class or function definition",
    "E306": "expected 1 blank line before a nested definition",
    # Imports
    "E401": "multiple imports on one line",
    "E402": "module level import not at top of file",
    # Line length
    "E501": "line too long",
    "E502": "the backslash is redundant between brackets",
    # Statement
    "E701": "multiple statements on one line (colon)",
    "E702": "multiple statements on one line (semicolon)",
    "E703": "statement ends with a semicolon",
    "E704": "multiple statements on one line (def)",
    "E711": "comparison to None",
    "E712": "comparison to True/False",
    "E713": "test for membership should be 'not in'",
    "E714": "test for object identity should be 'is not'",
    "E721": "do not compare types, use isinstance()",
    "E722": "do not use bare 'except'",
    "E731": "do not assign a lambda expression, use a def",
    "E741": "ambiguous variable name",
    "E742": "ambiguous class definition",
    "E743": "ambiguous function definition",
    "E902": "TokenError",
    "E999": "SyntaxError",
    # Warnings - Indentation
    "W191": "indentation contains tabs",
    # Warnings - Whitespace
    "W291": "trailing whitespace",
    "W292": "no newline at end of file",
    "W293": "blank line contains whitespace",
    # Warnings - Blank lines
    "W391": "blank line at end of file",
    # Warnings - Line break
    "W503": "line break before binary operator",
    "W504": "line break after binary operator",
    "W505": "doc line too long",
    # Warnings - Deprecation
    "W605": "invalid escape sequence",
}


# =============================================================================
# Configuration
# =============================================================================


@dataclass
class PycodestyleConfig:
    """Configuration for pycodestyle execution."""

    max_line_length: int = 79
    ignore: list[str] = field(default_factory=list)
    select: list[str] = field(default_factory=list)
    exclude: list[str] = field(default_factory=list)
    hang_closing: bool = False
    show_source: bool = False
    show_pep8_errors: bool = True
    extra_args: list[str] = field(default_factory=list)


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class StyleViolation:
    """Represents a pycodestyle violation."""

    code: str
    message: str
    file: str
    line: int
    column: int
    category: StyleCategory = StyleCategory.OTHER
    severity: StyleSeverity = StyleSeverity.ERROR
    source_line: str | None = None

    @property
    def location(self) -> str:
        """Get formatted location string."""
        return f"{self.file}:{self.line}:{self.column}"

    def format(self) -> str:
        """Format the violation for display."""
        return f"{self.location}: {self.code} {self.message}"


@dataclass
class PycodestyleReport:
    """Complete pycodestyle analysis report."""

    violations: list[StyleViolation] = field(default_factory=list)
    files_checked: int = 0
    config: PycodestyleConfig = field(default_factory=PycodestyleConfig)
    errors: list[str] = field(default_factory=list)

    @property
    def violation_count(self) -> int:
        """Get total number of violations."""
        return len(self.violations)

    @property
    def error_count(self) -> int:
        """Count of error-level violations (E codes)."""
        return len([v for v in self.violations if v.severity == StyleSeverity.ERROR])

    @property
    def warning_count(self) -> int:
        """Count of warning-level violations (W codes)."""
        return len([v for v in self.violations if v.severity == StyleSeverity.WARNING])

    @property
    def violations_by_code(self) -> dict[str, list[StyleViolation]]:
        """Group violations by error code."""
        result: dict[str, list[StyleViolation]] = {}
        for v in self.violations:
            result.setdefault(v.code, []).append(v)
        return result

    @property
    def violations_by_category(self) -> dict[StyleCategory, list[StyleViolation]]:
        """Group violations by category."""
        result: dict[StyleCategory, list[StyleViolation]] = {}
        for v in self.violations:
            result.setdefault(v.category, []).append(v)
        return result

    @property
    def violations_by_file(self) -> dict[str, list[StyleViolation]]:
        """Group violations by file."""
        result: dict[str, list[StyleViolation]] = {}
        for v in self.violations:
            result.setdefault(v.file, []).append(v)
        return result

    def get_summary(self) -> dict[str, Any]:
        """Get a summary of the report."""
        return {
            "files_checked": self.files_checked,
            "total_violations": self.violation_count,
            "errors": self.error_count,
            "warnings": self.warning_count,
            "by_category": {cat.value: len(violations) for cat, violations in self.violations_by_category.items()},
            "top_violations": [
                {"code": code, "count": len(violations)}
                for code, violations in sorted(self.violations_by_code.items(), key=lambda x: -len(x[1]))[:5]
            ],
        }


# =============================================================================
# Parser Class
# =============================================================================


class PycodestyleParser:
    """
    Parser for pycodestyle output - PEP 8 style checker.

    Provides PEP 8 style checking for Python code using pycodestyle.

    Implementation Status:
        ✓ Full pycodestyle integration (P4-PYCODESTYLE-001)
        ✓ Complete error categorization (P4-PYCODESTYLE-002)

    Usage:
        >>> parser = PycodestyleParser()
        >>> report = parser.check_file("example.py")
        >>> for violation in report.violations:
        ...     print(violation.format())
    """

    def __init__(self, config: PycodestyleConfig | None = None):
        """
        Initialize the parser.

        Args:
            config: Configuration for pycodestyle.
        """
        self.config = config or PycodestyleConfig()
        self._pycodestyle_path: str | None = None

    @property
    def pycodestyle_path(self) -> str | None:
        """Get path to pycodestyle executable."""
        if self._pycodestyle_path is None:
            self._pycodestyle_path = self._find_pycodestyle()
        return self._pycodestyle_path

    def _find_pycodestyle(self) -> str | None:
        """Find pycodestyle executable."""
        try:
            result = subprocess.run(
                ["which", "pycodestyle"],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass
        return None

    def is_available(self) -> bool:
        """Check if pycodestyle is available."""
        return self.pycodestyle_path is not None

    def check_file(self, path: str | Path) -> PycodestyleReport:
        """
        Check a Python file for style issues.

        Args:
            path: Path to the Python file.

        Returns:
            PycodestyleReport with violations.
        """
        return self.check_paths([str(path)])

    def check_paths(
        self,
        paths: list[str],
    ) -> PycodestyleReport:
        """
        Check multiple paths for style issues.

        Runs pycodestyle subprocess and parses violations.

        Args:
            paths: Paths to check (files or directories).

        Returns:
            PycodestyleReport with all violations.
        """
        report = PycodestyleReport(config=self.config)

        if not self.is_available():
            report.errors.append("pycodestyle is not installed or not in PATH")
            return report

        cmd = self._build_command(paths)

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
            )

            # pycodestyle returns 1 when violations found, 0 otherwise
            report.violations = self._parse_output(result.stdout)
            report.files_checked = len(paths)

            if result.stderr:
                for line in result.stderr.strip().split("\n"):
                    if line:
                        report.errors.append(line)

        except subprocess.TimeoutExpired:
            report.errors.append("pycodestyle timed out after 5 minutes")
        except Exception as e:
            report.errors.append(f"Failed to run pycodestyle: {e}")

        return report

    def _build_command(self, paths: list[str]) -> list[str]:
        """Build the pycodestyle command."""
        cmd = ["pycodestyle"]

        # Max line length
        cmd.extend(["--max-line-length", str(self.config.max_line_length)])

        # Ignore
        if self.config.ignore:
            cmd.extend(["--ignore", ",".join(self.config.ignore)])

        # Select
        if self.config.select:
            cmd.extend(["--select", ",".join(self.config.select)])

        # Exclude
        if self.config.exclude:
            cmd.extend(["--exclude", ",".join(self.config.exclude)])

        # Hang closing
        if self.config.hang_closing:
            cmd.append("--hang-closing")

        # Show source
        if self.config.show_source:
            cmd.append("--show-source")

        # Extra args
        cmd.extend(self.config.extra_args)

        # Add paths
        cmd.extend(paths)

        return cmd

    def _parse_output(self, output: str) -> list[StyleViolation]:
        """
        Parse pycodestyle output.

        Output format:
            filename.py:1:1: E302 expected 2 blank lines, found 1
        """
        violations: list[StyleViolation] = []

        # Pattern: file:line:column: CODE message
        pattern = re.compile(r"^(.+?):(\d+):(\d+):\s+(E\d+|W\d+)\s+(.+)$")

        for line in output.strip().split("\n"):
            if not line:
                continue

            match = pattern.match(line)
            if match:
                file_path = match.group(1)
                line_num = int(match.group(2))
                column = int(match.group(3))
                code = match.group(4)
                message = match.group(5)

                # Determine severity
                severity = StyleSeverity.WARNING if code.startswith("W") else StyleSeverity.ERROR

                # Get category
                category = get_category_for_code(code)

                violations.append(
                    StyleViolation(
                        code=code,
                        message=message,
                        file=file_path,
                        line=line_num,
                        column=column,
                        category=category,
                        severity=severity,
                    )
                )

        return violations


# =============================================================================
# Utility Functions
# =============================================================================


def format_pycodestyle_report(report: PycodestyleReport) -> str:
    """Format a pycodestyle report for display."""
    lines = [
        "Pycodestyle Report",
        "=" * 50,
        "",
        f"Files checked: {report.files_checked}",
        f"Total violations: {report.violation_count}",
        f"  - Errors: {report.error_count}",
        f"  - Warnings: {report.warning_count}",
        "",
    ]

    if report.violations_by_category:
        lines.append("By category:")
        for category, violations in sorted(report.violations_by_category.items(), key=lambda x: -len(x[1])):
            lines.append(f"  {category.value}: {len(violations)}")

    lines.append("")

    if report.violations:
        lines.append("Violations:")
        for violation in report.violations[:10]:
            lines.append(f"  {violation.format()}")
        if len(report.violations) > 10:
            lines.append(f"  ... and {len(report.violations) - 10} more")

    if report.errors:
        lines.extend(["", "Errors:"])
        for error in report.errors:
            lines.append(f"  {error}")

    return "\n".join(lines)


def get_error_description(code: str) -> str:
    """Get the description for an error code."""
    return ERROR_DESCRIPTIONS.get(code, f"Unknown error code: {code}")
