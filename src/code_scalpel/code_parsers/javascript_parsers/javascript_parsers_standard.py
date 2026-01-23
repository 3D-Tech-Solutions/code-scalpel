#!/usr/bin/env python3
"""
StandardJS Parser - Zero-config JavaScript style enforcement.

Parses StandardJS output for style violations and automatic fixing.
StandardJS is a popular zero-configuration linter/formatter following
a consistent style guide (2 spaces, single quotes, no semicolons).


Features:
    Output Parsing:
        - StandardJS JSON output parsing
        - Violation extraction with ESLint rule IDs
        - Severity classification (warning, error)
        - Fix information extraction

    Execution:
        - Real-time StandardJS execution via subprocess
        - File and code string checking
        - Auto-fix mode support
        - Configurable StandardJS path

    Configuration:
        - Parser options (babel-eslint, @typescript-eslint/parser)
        - Global variable declarations
        - Plugin support (standard-react, etc.)
        - Environment configuration
        - File extension filtering

    Analysis:
        - Fixable violation filtering
        - Group by rule ID
        - Violation summary statistics
        - Rule documentation URL generation

Future Enhancements:
    - Snazzy formatter output parsing
    - CI/CD integration helpers
    - Migration helpers from other linters
"""

import json
import shutil
import subprocess
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class StandardSeverity(Enum):
    """StandardJS severity levels (mirrors ESLint)."""

    WARNING = 1
    ERROR = 2


@dataclass
class StandardViolation:
    """Represents a single StandardJS style violation."""

    rule_id: str  # ESLint rule name (e.g., "semi", "no-unused-vars")
    message: str  # Human-readable message
    severity: StandardSeverity
    line: int
    column: int
    end_line: int | None = None
    end_column: int | None = None
    fix: dict[str, Any] | None = None  # Auto-fix info if available

    @property
    def is_fixable(self) -> bool:
        """Check if this violation can be auto-fixed."""
        return self.fix is not None

    @property
    def rule_url(self) -> str:
        """Get URL to rule documentation."""
        # StandardJS uses ESLint rules
        return f"https://eslint.org/docs/rules/{self.rule_id}"


@dataclass
class StandardFileResult:
    """StandardJS results for a single file."""

    file_path: str
    violations: list[StandardViolation] = field(default_factory=list)

    @property
    def error_count(self) -> int:
        """Count of errors."""
        return sum(1 for v in self.violations if v.severity == StandardSeverity.ERROR)

    @property
    def warning_count(self) -> int:
        """Count of warnings."""
        return sum(1 for v in self.violations if v.severity == StandardSeverity.WARNING)

    @property
    def fixable_count(self) -> int:
        """Count of auto-fixable violations."""
        return sum(1 for v in self.violations if v.is_fixable)

    @property
    def has_violations(self) -> bool:
        """Check if file has any violations."""
        return len(self.violations) > 0


@dataclass
class StandardConfig:
    """StandardJS configuration options."""

    # Parser options
    parser: str = "babel-eslint"  # Default parser

    # Globals (variables that are globally available)
    globals: list[str] = field(default_factory=list)

    # Plugins
    plugins: list[str] = field(default_factory=list)

    # Environment (node, browser, mocha, etc.)
    env: list[str] = field(default_factory=list)

    # Ignore patterns
    ignore: list[str] = field(default_factory=list)

    # Extensions to check
    extensions: list[str] = field(default_factory=lambda: [".js", ".jsx", ".mjs", ".cjs"])


class StandardJSParser:
    """
    Parser for StandardJS output and execution.

    StandardJS is a zero-configuration style guide based on ESLint.
    It enforces a consistent style without needing a config file.

    Key rules enforced:
    - 2 spaces for indentation
    - Single quotes for strings
    - No semicolons
    - No unused variables
    - Space after keywords
    - And many more...

    Example usage:
        parser = StandardJSParser()

        # Check a file
        result = parser.check_file('src/app.js')

        # Check code
        result = parser.check_code(source_code)

        # Fix a file
        fixed = parser.fix_file('src/app.js')
    """

    def __init__(self, standard_path: str | None = None):
        """
        Initialize StandardJS parser.

        :param standard_path: Path to standard executable.
        """
        self._standard_path = standard_path or self._find_standard()

    def _find_standard(self) -> str | None:
        """Find StandardJS executable."""
        standard = shutil.which("standard")
        if standard:
            return standard

        local = Path("node_modules/.bin/standard")
        if local.exists():
            return str(local)

        if shutil.which("npx"):
            return "npx standard"

        return None

    def parse_output(self, json_output: str) -> list[StandardFileResult]:
        """
        Parse StandardJS JSON output.

        :param json_output: StandardJS output from --reporter=json.
        :return: List of StandardFileResult for each file.
        """
        try:
            # StandardJS uses ESLint's JSON format
            data = json.loads(json_output)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid StandardJS JSON output: {e}")

        results: list[StandardFileResult] = []

        for file_data in data:
            violations: list[StandardViolation] = []

            for msg in file_data.get("messages", []):
                violation = StandardViolation(
                    rule_id=msg.get("ruleId", "unknown"),
                    message=msg.get("message", ""),
                    severity=StandardSeverity(msg.get("severity", 2)),
                    line=msg.get("line", 0),
                    column=msg.get("column", 0),
                    end_line=msg.get("endLine"),
                    end_column=msg.get("endColumn"),
                    fix=msg.get("fix"),
                )
                violations.append(violation)

            results.append(
                StandardFileResult(
                    file_path=file_data.get("filePath", "unknown"),
                    violations=violations,
                )
            )

        return results

    def check_file(self, file_path: str) -> StandardFileResult:
        """
        Run StandardJS on a file.

        :param file_path: Path to JavaScript file.
        :return: StandardFileResult with violations.
        """
        if not self._standard_path:
            raise RuntimeError("StandardJS not found. Install with: npm install standard")

        cmd = self._standard_path.split() if " " in self._standard_path else [self._standard_path]
        cmd.extend(["--reporter", "json", file_path])

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            output = result.stdout or "[]"
            results = self.parse_output(output)
            return results[0] if results else StandardFileResult(file_path=file_path)
        except subprocess.TimeoutExpired:
            raise TimeoutError(f"StandardJS timed out on {file_path}")
        except subprocess.SubprocessError as e:
            raise RuntimeError(f"StandardJS failed: {e}")

    def check_code(self, code: str, filename: str = "input.js") -> StandardFileResult:
        """
        Run StandardJS on source code string.

        :param code: JavaScript source code.
        :param filename: Virtual filename.
        :return: StandardFileResult with violations.
        """
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", suffix=".js", delete=False) as f:
            f.write(code)
            temp_path = f.name

        try:
            result = self.check_file(temp_path)
            result.file_path = filename
            return result
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def fix_file(self, file_path: str) -> bool:
        """
        Auto-fix StandardJS violations in a file.

        :param file_path: Path to JavaScript file.
        :return: True if file was modified.
        """
        if not self._standard_path:
            raise RuntimeError("StandardJS not found. Install with: npm install standard")

        # Check original state
        original = Path(file_path).read_text()

        cmd = self._standard_path.split() if " " in self._standard_path else [self._standard_path]
        cmd.extend(["--fix", file_path])

        try:
            subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            modified = Path(file_path).read_text()
            return original != modified
        except subprocess.TimeoutExpired:
            raise TimeoutError(f"StandardJS timed out on {file_path}")

    def fix_code(self, code: str) -> tuple[str, bool]:
        """
        Auto-fix StandardJS violations in code.

        :param code: JavaScript source code.
        :return: Tuple of (fixed_code, was_modified).
        """
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", suffix=".js", delete=False) as f:
            f.write(code)
            temp_path = f.name

        try:
            was_modified = self.fix_file(temp_path)
            fixed_code = Path(temp_path).read_text()
            return fixed_code, was_modified
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def get_fixable_violations(self, result: StandardFileResult) -> list[StandardViolation]:
        """
        Get only auto-fixable violations.

        :param result: StandardFileResult to filter.
        :return: List of fixable violations.
        """
        return [v for v in result.violations if v.is_fixable]

    def group_by_rule(self, result: StandardFileResult) -> dict[str, list[StandardViolation]]:
        """
        Group violations by rule ID.

        :param result: StandardFileResult to group.
        :return: Dictionary mapping rule IDs to violations.
        """
        grouped: dict[str, list[StandardViolation]] = {}
        for violation in result.violations:
            if violation.rule_id not in grouped:
                grouped[violation.rule_id] = []
            grouped[violation.rule_id].append(violation)
        return grouped

    def get_violation_summary(self, results: list[StandardFileResult]) -> dict[str, int]:
        """
        Get summary of violations across multiple files.

        :param results: List of StandardFileResult.
        :return: Dictionary with counts by rule.
        """
        summary: dict[str, int] = {}
        for result in results:
            for violation in result.violations:
                rule = violation.rule_id
                summary[rule] = summary.get(rule, 0) + 1
        return dict(sorted(summary.items(), key=lambda x: x[1], reverse=True))
