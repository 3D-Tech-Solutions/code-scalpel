"""
Custom Rules Engine - Enterprise Tier Feature.

[20251226_FEATURE] v3.2.9 - Enterprise tier custom security rules.

This module allows organizations to define custom security rules:
- Pattern-based detection
- AST-based detection
- Custom severity levels
- Organization-specific requirements
"""

import ast
import logging
import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class CustomRule:
    """A custom security rule."""

    rule_id: str  # Unique identifier
    name: str  # Rule name
    description: str  # What this rule checks
    severity: str  # "critical", "high", "medium", "low"
    pattern: str | None = None  # Regex pattern (for pattern-based rules)
    ast_check: Callable[[ast.AST], bool] | None = None  # AST checker function
    enabled: bool = True


@dataclass
class CustomRuleResult:
    """Result of a custom rule check."""

    rule_id: str
    rule_name: str
    severity: str
    line: int
    description: str
    matched_text: str | None = None


class CustomRulesEngine:
    """
    Custom security rules engine.

    Enterprise tier feature for organization-specific security rules.
    """

    def __init__(self):
        """Initialize the custom rules engine."""
        self.rules: dict[str, CustomRule] = {}
        self._load_example_rules()

    def _load_example_rules(self) -> None:
        """Load example custom rules."""
        # Example rule: Detect TODO/FIXME in security-sensitive code
        self.add_rule(
            CustomRule(
                rule_id="CUSTOM001",
                name="TODO in Security Code",
                description="TODO/FIXME comments in security-sensitive code",
                severity="medium",
                pattern=r"#\s*(TODO|FIXME).*(?:auth|password|token|secret|crypto)",
            )
        )

        # Example rule: Detect print statements in production code
        self.add_rule(
            CustomRule(
                rule_id="CUSTOM002",
                name="Debug Print Statements",
                description="print() statements may leak sensitive data",
                severity="low",
                pattern=r"print\s*\(",
            )
        )

        # Example rule: Detect use of assert for security checks
        self.add_rule(
            CustomRule(
                rule_id="CUSTOM003",
                name="Assert for Security Check",
                description="assert statements are removed in optimized Python",
                severity="high",
                pattern=r"assert\s+.*(?:auth|admin|permission|role)",
            )
        )

    def add_rule(self, rule: CustomRule) -> None:
        """
        Add a custom rule.

        Args:
            rule: CustomRule to add
        """
        self.rules[rule.rule_id] = rule
        logger.debug(f"Added custom rule: {rule.rule_id} - {rule.name}")

    def remove_rule(self, rule_id: str) -> bool:
        """
        Remove a custom rule.

        Args:
            rule_id: Rule ID to remove

        Returns:
            True if removed, False if not found
        """
        if rule_id in self.rules:
            del self.rules[rule_id]
            return True
        return False

    def enable_rule(self, rule_id: str) -> bool:
        """Enable a rule."""
        if rule_id in self.rules:
            self.rules[rule_id].enabled = True
            return True
        return False

    def disable_rule(self, rule_id: str) -> bool:
        """Disable a rule."""
        if rule_id in self.rules:
            self.rules[rule_id].enabled = False
            return True
        return False

    def check_pattern_rules(self, code: str) -> list[CustomRuleResult]:
        """
        Check all pattern-based rules.

        Args:
            code: Source code to check

        Returns:
            List of custom rule violations
        """
        results = []
        lines = code.split("\n")

        for rule in self.rules.values():
            if not rule.enabled or not rule.pattern:
                continue

            pattern = re.compile(rule.pattern, re.IGNORECASE)

            for line_num, line in enumerate(lines, start=1):
                match = pattern.search(line)
                if match:
                    results.append(
                        CustomRuleResult(
                            rule_id=rule.rule_id,
                            rule_name=rule.name,
                            severity=rule.severity,
                            line=line_num,
                            description=rule.description,
                            matched_text=match.group(0),
                        )
                    )

        return results

    def check_ast_rules(self, code: str) -> list[CustomRuleResult]:
        """
        Check all AST-based rules.

        Args:
            code: Source code to check

        Returns:
            List of custom rule violations
        """
        results = []

        try:
            tree = ast.parse(code)
        except SyntaxError:
            return []

        for rule in self.rules.values():
            if not rule.enabled or not rule.ast_check:
                continue

            # Walk the AST and apply the custom checker
            for node in ast.walk(tree):
                if rule.ast_check(node):
                    results.append(
                        CustomRuleResult(
                            rule_id=rule.rule_id,
                            rule_name=rule.name,
                            severity=rule.severity,
                            line=getattr(node, "lineno", 0),
                            description=rule.description,
                        )
                    )

        return results

    def check_all_rules(self, code: str) -> list[CustomRuleResult]:
        """
        Check all custom rules.

        Args:
            code: Source code to check

        Returns:
            List of all custom rule violations
        """
        results = []

        results.extend(self.check_pattern_rules(code))
        results.extend(self.check_ast_rules(code))

        return results

    def get_enabled_rules(self) -> list[CustomRule]:
        """Get all enabled rules."""
        return [rule for rule in self.rules.values() if rule.enabled]

    def get_rule(self, rule_id: str) -> CustomRule | None:
        """Get a rule by ID."""
        return self.rules.get(rule_id)

    def get_all_rules(self) -> list[CustomRule]:
        """Get all rules (enabled and disabled)."""
        return list(self.rules.values())

    def add_pattern_rule(
        self,
        rule_id: str,
        name: str,
        description: str,
        severity: str,
        pattern: str,
    ) -> None:
        """
        Convenience method to add a pattern-based rule.

        Args:
            rule_id: Unique rule ID
            name: Rule name
            description: Rule description
            severity: Severity level
            pattern: Regex pattern to match
        """
        self.add_rule(
            CustomRule(
                rule_id=rule_id,
                name=name,
                description=description,
                severity=severity,
                pattern=pattern,
            )
        )

    def add_ast_rule(
        self,
        rule_id: str,
        name: str,
        description: str,
        severity: str,
        checker: Callable[[ast.AST], bool],
    ) -> None:
        """
        Convenience method to add an AST-based rule.

        Args:
            rule_id: Unique rule ID
            name: Rule name
            description: Rule description
            severity: Severity level
            checker: Function that takes AST node and returns True if violation
        """
        self.add_rule(
            CustomRule(
                rule_id=rule_id,
                name=name,
                description=description,
                severity=severity,
                ast_check=checker,
            )
        )

    def generate_rules_summary(self) -> dict[str, Any]:
        """
        Generate a summary of all rules.

        Returns:
            Dict with rule statistics
        """
        all_rules = self.get_all_rules()
        enabled_rules = self.get_enabled_rules()

        severity_counts = {}
        for rule in enabled_rules:
            severity_counts[rule.severity] = severity_counts.get(rule.severity, 0) + 1

        return {
            "total_rules": len(all_rules),
            "enabled_rules": len(enabled_rules),
            "disabled_rules": len(all_rules) - len(enabled_rules),
            "severity_breakdown": severity_counts,
            "rule_ids": [rule.rule_id for rule in enabled_rules],
        }
