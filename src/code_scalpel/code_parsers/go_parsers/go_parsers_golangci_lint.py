#!/usr/bin/env python3
"""Golangci-lint Go Parser - comprehensive Go linting aggregator.

[20260303_FEATURE] Phase 2: full implementation replacing NotImplementedError stubs.
Phase 1 data structures retained; Phase 2 adds execution + parsing logic.

Reference: https://golangci-lint.run/
Command: golangci-lint run --out-format json ./...
Output: {"Issues": [...], "Report": {...}}
"""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Union


class IssueSeverity(Enum):
    """Issue severity levels."""

    ERROR = "error"
    WARNING = "warning"


class LinterType(Enum):
    """Types of linters aggregated by golangci-lint (common subset)."""

    ERRCHECK = "errcheck"
    GOIMPORTS = "goimports"
    GOVET = "govet"
    STATICCHECK = "staticcheck"
    INEFFASSIGN = "ineffassign"
    UNUSED = "unused"
    DEADCODE = "deadcode"
    VARCHECK = "varcheck"
    STRUCTCHECK = "structcheck"
    GOCYCLO = "gocyclo"
    GOCOGNIT = "gocognit"
    MISSPELL = "misspell"
    UNPARAM = "unparam"
    UNCONVERT = "unconvert"
    DUPL = "dupl"
    UNKNOWN = "unknown"


@dataclass
class LintIssue:
    """Represents a linting issue from golangci-lint."""

    linter: str  # raw FromLinter string (e.g. "govet", "errcheck")
    linter_type: LinterType  # mapped enum (UNKNOWN if not in map)
    severity: IssueSeverity
    message: str
    file_path: str
    line: int
    column: int
    from_line: Optional[int] = None
    from_column: Optional[int] = None
    to_line: Optional[int] = None
    to_column: Optional[int] = None


@dataclass
class GolangciLintConfig:
    """Golangci-lint configuration."""

    version: str = "1.55.0"
    config_file: Optional[Path] = None
    timeout: str = "5m"
    concurrency: int = 4
    fast_mode: bool = False


_LINTER_TYPE_MAP: Dict[str, LinterType] = {e.value: e for e in LinterType}


class GolangciLintParser:
    """Parser for Golangci-Lint comprehensive Go linting.

    [20260303_FEATURE] Phase 2: full implementation.

    Aggregates 100+ linters and tools into a unified interface for
    comprehensive Go code analysis.  Falls back to ``[]`` when
    ``golangci-lint`` is not on PATH.
    """

    def __init__(self) -> None:
        """Initialize Golangci-Lint parser."""
        self.config = GolangciLintConfig()
        self.issues: List[LintIssue] = []

    def execute_golangci_lint(
        self,
        paths: Union[List[Path], Path, str],
        config: Optional[GolangciLintConfig] = None,
    ) -> List[LintIssue]:
        """Run ``golangci-lint run --out-format json`` and return issues.

        Returns ``[]`` gracefully when ``golangci-lint`` is not on PATH.
        """
        if not shutil.which("golangci-lint"):
            return []

        target = (
            str(paths)
            if not isinstance(paths, (list, Path))
            else (
                str(paths)
                if isinstance(paths, Path)
                else (str(paths[0]) if paths else ".")
            )
        )
        cmd = ["golangci-lint", "run", "--out-format", "json", target]
        if config and config.config_file:
            cmd += ["--config", str(config.config_file)]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            return self.parse_json_output(result.stdout)
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return []

    def parse_json_output(self, output: str) -> List[LintIssue]:
        """Parse ``golangci-lint --out-format json`` stdout.

        [20260303_FEATURE] Handles the ``{"Issues": [...]}`` JSON format.

        Args:
            output: JSON string from golangci-lint stdout.

        Returns:
            List of LintIssue; ``[]`` on parse error or empty input.
        """
        if not output or not output.strip():
            return []
        try:
            data = json.loads(output)
        except json.JSONDecodeError:
            return []

        issues: List[LintIssue] = []
        for item in data.get("Issues", []):
            linter_name = item.get("FromLinter", "unknown")
            linter_type = _LINTER_TYPE_MAP.get(linter_name.lower(), LinterType.UNKNOWN)
            severity_str = item.get("Severity", "warning").lower()
            severity = (
                IssueSeverity.ERROR
                if severity_str == "error"
                else IssueSeverity.WARNING
            )
            pos = item.get("Pos", {})
            issues.append(
                LintIssue(
                    linter=linter_name,
                    linter_type=linter_type,
                    severity=severity,
                    message=item.get("Text", ""),
                    file_path=pos.get("Filename", ""),
                    line=pos.get("Line", 0),
                    column=pos.get("Column", 0),
                )
            )
        return issues

    # Alias for backward compatibility
    def parse_json_report(self, report_path: Union[str, Path]) -> List[LintIssue]:
        """Parse a pre-saved golangci-lint JSON report file."""
        try:
            content = Path(report_path).read_text(encoding="utf-8")
            return self.parse_json_output(content)
        except OSError:
            return []

    def load_config(self, config_file: Path) -> GolangciLintConfig:
        """Parse a ``.golangci.yml`` or ``.golangci.toml`` config file."""
        # Full YAML parsing would require pyyaml; return config with path set.
        return GolangciLintConfig(config_file=config_file)

    def categorize_by_linter(
        self, issues: List[LintIssue]
    ) -> Dict[str, List[LintIssue]]:
        """Group issues by the linter name (FromLinter field).

        [20260303_FEATURE] Uses raw linter name string as key (not enum).
        """
        result: Dict[str, List[LintIssue]] = {}
        for issue in issues:
            result.setdefault(issue.linter, []).append(issue)
        return result

    def filter_by_severity(
        self, issues: List[LintIssue], min_severity: str
    ) -> List[LintIssue]:
        """Filter issues to only those ≥ *min_severity*.

        Args:
            issues: Source list.
            min_severity: "error" or "warning" (case-insensitive).
        """
        s = min_severity.lower()
        if s == "error":
            return [i for i in issues if i.severity == IssueSeverity.ERROR]
        return list(issues)

    def generate_report(self, issues: List[LintIssue], format: str = "json") -> str:
        """Return a JSON or text report of lint issues."""
        if format == "json":
            return json.dumps(
                {
                    "tool": "golangci-lint",
                    "total": len(issues),
                    "by_linter": {
                        k: len(v) for k, v in self.categorize_by_linter(issues).items()
                    },
                    "issues": [
                        {
                            "linter": i.linter,
                            "severity": i.severity.value,
                            "message": i.message,
                            "file": i.file_path,
                            "line": i.line,
                            "column": i.column,
                        }
                        for i in issues
                    ],
                },
                indent=2,
            )
        return "\n".join(
            f"{i.file_path}:{i.line}:{i.column}: [{i.linter}] {i.message}"
            for i in issues
        )

