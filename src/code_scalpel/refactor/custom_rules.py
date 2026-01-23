"""
Custom Rules Engine - Enterprise Tier Feature.

[20251226_FEATURE] v3.2.9 - Enterprise tier custom refactor rules.

This module loads and enforces custom validation rules from .code-scalpel/rules.toml:
- Function naming conventions
- Complexity limits
- Documentation requirements
- Custom patterns
"""

import ast
import logging
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypedDict

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


class RuleSummaryDict(TypedDict):
    """Custom rules validation summary dictionary."""

    total_violations: int
    by_severity: dict[str, int]
    violations: list[dict[str, Any]]


logger = logging.getLogger(__name__)


@dataclass
class CustomRuleViolation:
    """A custom rule violation."""

    rule_id: str  # Unique rule identifier
    rule_name: str  # Human-readable name
    severity: str  # "error", "warning", "info"
    line: int  # Line number
    description: str  # Violation description
    suggestion: str  # How to fix


class CustomRulesEngine:
    """
    Enforces custom validation rules on refactored code.

    Enterprise tier feature for organization-specific refactoring standards.
    """

    def __init__(self, rules_path: str | None = None):
        """
        Initialize the custom rules engine.

        Args:
            rules_path: Path to rules.toml file (default: .code-scalpel/rules.toml)
        """
        if rules_path is None:
            rules_path = ".code-scalpel/rules.toml"

        self.rules_path = rules_path
        self.rules: dict[str, dict[str, Any]] = {}
        self._load_rules()

    def _load_rules(self) -> None:
        """Load rules from TOML file."""
        path = Path(self.rules_path)

        if not path.exists():
            # Load default rules
            self.rules = self._get_default_rules()
            logger.debug(f"Rules file not found at {path}, using defaults")
            return

        try:
            with open(path, "rb") as f:
                config = tomllib.load(f)
            self.rules = config.get("rules", {})
            logger.info(f"Loaded {len(self.rules)} custom rules from {path}")
        except Exception as e:
            logger.error(f"Failed to load rules from {path}: {e}")
            self.rules = self._get_default_rules()

    def _get_default_rules(self) -> dict[str, dict[str, Any]]:
        """Get default validation rules."""
        return {
            "function_naming": {
                "id": "RULE001",
                "name": "Function Naming Convention",
                "severity": "warning",
                "pattern": r"^[a-z_][a-z0-9_]*$",
                "description": "Functions must use snake_case naming",
                "suggestion": "Rename function to use lowercase with underscores",
                "enabled": True,
            },
            "max_function_complexity": {
                "id": "RULE002",
                "name": "Maximum Function Complexity",
                "severity": "warning",
                "max_complexity": 10,
                "description": "Functions must not exceed complexity of 10",
                "suggestion": "Refactor function to reduce complexity",
                "enabled": True,
            },
            "require_docstrings": {
                "id": "RULE003",
                "name": "Require Function Docstrings",
                "severity": "info",
                "description": "Public functions should have docstrings",
                "suggestion": "Add a docstring describing the function",
                "enabled": False,  # Disabled by default
            },
            "no_long_functions": {
                "id": "RULE004",
                "name": "Maximum Function Length",
                "severity": "warning",
                "max_lines": 50,
                "description": "Functions should not exceed 50 lines",
                "suggestion": "Split function into smaller functions",
                "enabled": True,
            },
        }

    def check_function_naming(self, code: str) -> list[CustomRuleViolation]:
        """Check function naming conventions."""
        rule = self.rules.get("function_naming", {})
        if not rule.get("enabled", False):
            return []

        violations = []
        pattern = re.compile(rule.get("pattern", r"^[a-z_][a-z0-9_]*$"))

        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if not pattern.match(node.name):
                        violations.append(
                            CustomRuleViolation(
                                rule_id=rule["id"],
                                rule_name=rule["name"],
                                severity=rule["severity"],
                                line=node.lineno,
                                description=f"{rule['description']}: '{node.name}' violates naming convention",
                                suggestion=rule["suggestion"],
                            )
                        )
        except SyntaxError:
            pass  # Syntax errors handled elsewhere

        return violations

    def check_function_complexity(self, code: str) -> list[CustomRuleViolation]:
        """Check function complexity limits."""
        rule = self.rules.get("max_function_complexity", {})
        if not rule.get("enabled", False):
            return []

        violations = []
        max_complexity = rule.get("max_complexity", 10)

        try:
            from code_scalpel.analysis import CodeAnalyzer

            analyzer = CodeAnalyzer()
            result = analyzer.analyze(code)

            for func in result.functions:  # type: ignore[reportAttributeAccessIssue]
                if func.complexity > max_complexity:  # type: ignore[reportAttributeAccessIssue]
                    violations.append(
                        CustomRuleViolation(
                            rule_id=rule["id"],
                            rule_name=rule["name"],
                            severity=rule["severity"],
                            line=func.lineno,  # type: ignore[reportAttributeAccessIssue]
                            description=f"{rule['description']}: '{func.name}' has complexity {func.complexity}",  # type: ignore[reportAttributeAccessIssue]
                            suggestion=rule["suggestion"],
                        )
                    )
        except Exception as e:
            logger.warning(f"Failed to check complexity: {e}")

        return violations

    def check_docstrings(self, code: str) -> list[CustomRuleViolation]:
        """Check for function docstrings."""
        rule = self.rules.get("require_docstrings", {})
        if not rule.get("enabled", False):
            return []

        violations = []

        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    # Skip private functions (starting with _)
                    if node.name.startswith("_"):
                        continue

                    # Check if function has a docstring
                    docstring = ast.get_docstring(node)
                    if not docstring:
                        violations.append(
                            CustomRuleViolation(
                                rule_id=rule["id"],
                                rule_name=rule["name"],
                                severity=rule["severity"],
                                line=node.lineno,
                                description=f"{rule['description']}: '{node.name}' missing docstring",
                                suggestion=rule["suggestion"],
                            )
                        )
        except SyntaxError:
            pass

        return violations

    def check_function_length(self, code: str) -> list[CustomRuleViolation]:
        """Check function length limits."""
        rule = self.rules.get("no_long_functions", {})
        if not rule.get("enabled", False):
            return []

        violations = []
        max_lines = rule.get("max_lines", 50)

        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    # Calculate function length
                    if hasattr(node, "end_lineno") and node.end_lineno:
                        func_length = node.end_lineno - node.lineno + 1
                        if func_length > max_lines:
                            violations.append(
                                CustomRuleViolation(
                                    rule_id=rule["id"],
                                    rule_name=rule["name"],
                                    severity=rule["severity"],
                                    line=node.lineno,
                                    description=f"{rule['description']}: '{node.name}' is {func_length} lines (max {max_lines})",
                                    suggestion=rule["suggestion"],
                                )
                            )
        except SyntaxError:
            pass

        return violations

    def check_all_rules(self, code: str) -> list[CustomRuleViolation]:
        """
        Run all enabled custom rules.

        Args:
            code: Source code to check

        Returns:
            List of all rule violations
        """
        all_violations = []

        all_violations.extend(self.check_function_naming(code))
        all_violations.extend(self.check_function_complexity(code))
        all_violations.extend(self.check_docstrings(code))
        all_violations.extend(self.check_function_length(code))

        return all_violations

    def to_dict(self, violations: list[CustomRuleViolation]) -> list[dict[str, Any]]:
        """Convert violations to dict list for JSON serialization."""
        return [
            {
                "rule_id": v.rule_id,
                "rule_name": v.rule_name,
                "severity": v.severity,
                "line": v.line,
                "description": v.description,
                "suggestion": v.suggestion,
            }
            for v in violations
        ]
