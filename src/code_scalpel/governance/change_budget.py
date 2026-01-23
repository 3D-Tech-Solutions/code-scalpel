"""
Change Budget - Blast Radius Control Implementation.

[20251216_FEATURE] Core implementation of change budgeting to limit
agent modification scope and prevent runaway changes.

This module provides:
- Operation and FileChange tracking
- Budget validation with multiple constraint types
- Complexity measurement via AST analysis
- File pattern matching for allowed/forbidden paths
- Clear violation reporting with actionable messages

"""

import ast
import fnmatch
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, BinaryIO, cast

try:
    import tomli as tomllib
except ImportError:
    import tomllib  # type: ignore

# [20251227_BUGFIX] Import yaml for .yaml config files
import yaml


@dataclass
class FileChange:
    """
    Represents changes to a single file.

    [20251216_FEATURE] Tracks added/removed lines for budget calculation.

    """

    file_path: str
    added_lines: list[str] = field(default_factory=list)
    removed_lines: list[str] = field(default_factory=list)
    original_code: str = ""
    modified_code: str = ""

    @property
    def lines_changed(self) -> int:
        """Total lines changed (added + removed)."""
        return len(self.added_lines) + len(self.removed_lines)


@dataclass
class Operation:
    """
    Represents a code modification operation.

    [20251216_FEATURE] Contains all changes for budget validation.

    """

    changes: list[FileChange] = field(default_factory=list)
    description: str = ""

    @property
    def affected_files(self) -> list[str]:
        """List of all files affected by this operation."""
        return [change.file_path for change in self.changes]

    @property
    def total_lines_changed(self) -> int:
        """Total lines changed across all files."""
        return sum(change.lines_changed for change in self.changes)


@dataclass
class BudgetViolation:
    """
    Represents a specific budget constraint violation.

    [20251216_FEATURE] Provides detailed violation information for clear
    error reporting.

    """

    rule: str
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW
    message: str
    limit: int | None = None
    actual: int | None = None
    file: str | None = None

    def __str__(self) -> str:
        """Format violation for display."""
        msg = f"[{self.severity}] {self.message}"
        if self.limit is not None and self.actual is not None:
            msg += f" (limit: {self.limit}, actual: {self.actual})"
        if self.file:
            msg += f" [file: {self.file}]"
        return msg


@dataclass
class BudgetDecision:
    """
    Result of budget validation.

    [20251216_FEATURE] Contains validation result and all violations.

    """

    allowed: bool
    reason: str
    violations: list[BudgetViolation] = field(default_factory=list)
    requires_review: bool = False

    @property
    def has_critical_violations(self) -> bool:
        """Check if any violations are CRITICAL severity."""
        return any(v.severity == "CRITICAL" for v in self.violations)

    def get_error_message(self) -> str:
        """
        Generate comprehensive error message with suggestions.

        [20251216_FEATURE] P0 requirement for clear error messages with
        actionable suggestions.
        """
        if self.allowed:
            return self.reason

        msg = f"{self.reason}\n\nViolations:\n"
        for violation in self.violations:
            msg += f"  - {violation}\n"

        # Add actionable suggestions
        msg += "\nSuggestions to reduce scope:\n"
        if any(v.rule == "max_files" for v in self.violations):
            msg += "  - Split operation into smaller batches affecting fewer files\n"
        if any(v.rule == "max_lines_per_file" for v in self.violations):
            msg += "  - Make more focused changes to individual files\n"
        if any(v.rule == "max_total_lines" for v in self.violations):
            msg += "  - Break down large refactorings into incremental steps\n"
        if any(v.rule == "max_complexity_increase" for v in self.violations):
            msg += "  - Simplify changes to avoid adding control flow complexity\n"
            msg += "  - Consider extracting methods instead of adding nested logic\n"
        if any(v.rule == "allowed_file_patterns" for v in self.violations):
            msg += "  - Ensure files match allowed patterns (e.g., *.py, *.ts, *.java)\n"
        if any(v.rule == "forbidden_paths" for v in self.violations):
            msg += "  - Avoid modifying system/generated files (e.g., .git/, node_modules/)\n"

        return msg


class ChangeBudget:
    """
    Budget constraints for agent operations.

    [20251216_FEATURE] P0 implementation of blast radius control.
    Enforces limits on files, lines, complexity, and file patterns.

    """

    def __init__(self, config: dict[str, Any]):
        """
        Initialize budget with configuration.

        Args:
            config: Dictionary with budget constraints:
                - max_files: Maximum files per operation (default: 5)
                - max_lines_per_file: Max lines changed per file (default: 100)
                - max_total_lines: Max total lines changed (default: 300)
                - max_complexity_increase: Max cyclomatic complexity increase (default: 10)
                - allowed_file_patterns: Glob patterns for allowed files (default: ["*.py", "*.ts", "*.java"])
                - forbidden_paths: Paths that cannot be modified (default: [".git/", "node_modules/", "__pycache__/"])
        """
        self.max_files = config.get("max_files", 5)
        self.max_lines_per_file = config.get("max_lines_per_file", 100)
        self.max_total_lines = config.get("max_total_lines", 300)
        self.max_complexity_increase = config.get("max_complexity_increase", 10)
        self.allowed_file_patterns = config.get("allowed_file_patterns", ["*.py", "*.ts", "*.java"])
        self.forbidden_paths = config.get("forbidden_paths", [".git/", "node_modules/", "__pycache__/"])

    def validate_operation(self, operation: Operation) -> BudgetDecision:
        """
        Validate operation against budget constraints.

        [20251216_FEATURE] P0 core validation logic implementing all
        constraint checks with clear violation reporting.


        Args:
            operation: The operation to validate

        Returns:
            BudgetDecision with allow/deny and detailed violations
        """
        violations = []

        # [20251216_FEATURE] P0: Check file count
        if len(operation.affected_files) > self.max_files:
            violations.append(
                BudgetViolation(
                    rule="max_files",
                    limit=self.max_files,
                    actual=len(operation.affected_files),
                    severity="HIGH",
                    message=f"Operation affects {len(operation.affected_files)} files, exceeds limit of {self.max_files}",
                )
            )

        # [20251216_FEATURE] P0: Check lines per file
        for file_change in operation.changes:
            lines_changed = file_change.lines_changed
            if lines_changed > self.max_lines_per_file:
                violations.append(
                    BudgetViolation(
                        rule="max_lines_per_file",
                        limit=self.max_lines_per_file,
                        actual=lines_changed,
                        file=file_change.file_path,
                        severity="MEDIUM",
                        message=f"Changes to {file_change.file_path} exceed {self.max_lines_per_file} line limit",
                    )
                )

        # [20251216_FEATURE] P0: Check total lines
        total_lines = operation.total_lines_changed
        if total_lines > self.max_total_lines:
            violations.append(
                BudgetViolation(
                    rule="max_total_lines",
                    limit=self.max_total_lines,
                    actual=total_lines,
                    severity="HIGH",
                    message=f"Total lines changed ({total_lines}) exceeds limit of {self.max_total_lines}",
                )
            )

        # [20251216_FEATURE] P0: Check complexity increase
        complexity_delta = self._calculate_complexity_delta(operation)
        if complexity_delta > self.max_complexity_increase:
            violations.append(
                BudgetViolation(
                    rule="max_complexity_increase",
                    limit=self.max_complexity_increase,
                    actual=complexity_delta,
                    severity="MEDIUM",
                    message=f"Complexity increase ({complexity_delta}) exceeds limit of {self.max_complexity_increase}",
                )
            )

        # [20251216_FEATURE] P0: Check file patterns
        for file_path in operation.affected_files:
            if not self._matches_allowed_pattern(file_path):
                violations.append(
                    BudgetViolation(
                        rule="allowed_file_patterns",
                        file=file_path,
                        severity="HIGH",
                        message=f"File {file_path} does not match allowed patterns: {self.allowed_file_patterns}",
                    )
                )

            if self._matches_forbidden_path(file_path):
                violations.append(
                    BudgetViolation(
                        rule="forbidden_paths",
                        file=file_path,
                        severity="CRITICAL",
                        message=f"File {file_path} is in forbidden path",
                    )
                )

        if violations:
            return BudgetDecision(
                allowed=False,
                reason="Budget constraints violated",
                violations=violations,
                requires_review=True,
            )

        return BudgetDecision(allowed=True, reason="Within budget constraints", violations=[])

    def _calculate_complexity_delta(self, operation: Operation) -> int:
        """
        Calculate change in cyclomatic complexity.

        [20251216_FEATURE] Uses AST analysis to measure complexity before
        and after changes.


        Args:
            operation: Operation to analyze

        Returns:
            Total complexity increase (can be negative if simplified)
        """
        total_delta = 0

        for change in operation.changes:
            # [20240613_BUGFIX] Always calculate complexity for changes with modified_code.
            # Treat empty or None original_code (new file) as zero complexity.
            if change.modified_code is not None:
                try:
                    before_complexity = self._measure_complexity(change.original_code) if change.original_code else 0
                    after_complexity = self._measure_complexity(change.modified_code)
                    total_delta += after_complexity - before_complexity
                except SyntaxError:
                    # If code doesn't parse, assume no complexity change
                    # (prevents syntax errors from blocking legitimate changes)
                    pass

        return total_delta

    def _measure_complexity(self, code: str) -> int:
        """
        Measure cyclomatic complexity of code.

        [20251216_FEATURE] AST-based complexity measurement for Python code.
        Counts decision points: if, for, while, except, bool operators.


        Args:
            code: Python source code

        Returns:
            Cyclomatic complexity (base 1 + decision points)
        """
        try:
            tree = ast.parse(code)
        except SyntaxError:
            # Return 0 for unparseable code
            return 0

        complexity = 1  # Base complexity

        for node in ast.walk(tree):
            # [20251216_FEATURE] Count control flow decision points
            if isinstance(node, (ast.If, ast.For, ast.While, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(node, ast.BoolOp):
                # Each additional boolean operand adds a decision point
                complexity += len(node.values) - 1

        return complexity

    def _matches_allowed_pattern(self, file_path: str) -> bool:
        """
        Check if file matches any allowed pattern.

        [20251216_FEATURE] P0 file pattern validation using glob matching.


        Args:
            file_path: Path to check

        Returns:
            True if file matches at least one allowed pattern
        """
        # Normalize path separators
        normalized_path = file_path.replace("\\", "/")
        filename = Path(normalized_path).name

        for pattern in self.allowed_file_patterns:
            # Check both full path and filename
            if fnmatch.fnmatch(normalized_path, pattern) or fnmatch.fnmatch(filename, pattern):
                return True

        return False

    def _matches_forbidden_path(self, file_path: str) -> bool:
        """
        Check if file is in a forbidden path.

        [20251216_FEATURE] P0 forbidden path validation for system/generated files.


        Args:
            file_path: Path to check

        Returns:
            True if file is in any forbidden path
        """
        # Normalize path separators
        normalized_path = file_path.replace("\\", "/")

        for forbidden in self.forbidden_paths:
            # Check if path starts with or contains forbidden segment
            if normalized_path.startswith(forbidden) or f"/{forbidden}" in normalized_path:
                return True

        return False


def load_budget_config(config_path: str | None = None) -> dict[str, Any]:
    """
    Load budget configuration from YAML file.

    [20251216_FEATURE] Configuration loader for .code-scalpel/agent_limits.yaml.

    Args:
        config_path: Path to agent_limits.yaml file (optional)

    Returns:
        Dictionary with budget configuration

    Note:
        Returns default configuration if file not found.
    """
    if config_path is None:
        config_path = ".code-scalpel/agent_limits.yaml"

    config_file = Path(config_path)

    # Default configuration structure (budget-style expected by callers/tests)
    default_budget = {
        "max_files": 5,
        "max_lines_per_file": 100,
        "max_total_lines": 300,
        "max_complexity_increase": 10,
        "allowed_file_patterns": ["*.py", "*.ts", "*.java"],
        "forbidden_paths": [".git/", "node_modules/", "__pycache__/"],
    }

    default_config = {"default": default_budget}

    if not config_file.exists():
        # Return default configuration
        return default_config

    # Load YAML configuration
    # [20251227_BUGFIX] Use yaml.safe_load for .yaml files, tomllib for .toml
    with open(config_file, "r" if config_file.suffix == ".yaml" else "rb") as f:
        if config_file.suffix == ".yaml":
            config = yaml.safe_load(f)
        else:
            config = tomllib.load(cast(BinaryIO, f))

    # [20251227_BUGFIX] Return default if file doesn't have expected structure
    # Expect configuration to define budgets under a top-level key like
    # 'limits' or 'budgets' or directly as profile keys. Normalize to
    # {'default': { ... }} shape for consumers.
    if not config:
        return default_config

    # Accept several possible shapes for backward compatibility
    if isinstance(config, dict):
        # Already in expected profile shape
        if "default" in config and isinstance(config["default"], dict):
            return config

        # Support legacy 'limits' or 'budgets' sections by wrapping them
        if "limits" in config and isinstance(config["limits"], dict):
            limits = config["limits"]
            # If limits contain change-budget keys, treat them as the default
            flat_budget_keys = {"max_files", "max_lines_per_file", "max_total_lines", "max_complexity_increase"}
            if flat_budget_keys.intersection(limits.keys()):
                return {"default": limits}
            # Otherwise the file contains agent/session limits; return the
            # standard default change-budget configuration
            return default_config
        if "budgets" in config and isinstance(config["budgets"], dict):
            return {"default": config["budgets"]}

        # If the file is a flat mapping of budget keys, treat it as the default
        flat_budget_keys = {"max_files", "max_lines_per_file", "max_total_lines", "max_complexity_increase"}
        if flat_budget_keys.intersection(config.keys()):
            return {"default": config}

    # Fallback to default
    return default_config
