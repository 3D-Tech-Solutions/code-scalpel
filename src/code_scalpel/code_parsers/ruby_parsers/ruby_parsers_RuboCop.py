#!/usr/bin/env python3
"""
RuboCop Parser - Ruby Code Style and Linting Analysis.

[20260304_FEATURE] Full implementation of RuboCop parser for Ruby static analysis.
RuboCop is a Ruby static code analyzer and formatter, out of the box it will
enforce many of the guidelines outlined in the community Ruby Style Guide.

Output format: rubocop --format json --no-color
"""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


class RuboCopSeverity(Enum):
    """RuboCop violation severity levels."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    FATAL = "fatal"
    CONVENTION = "convention"
    REFACTOR = "refactor"


@dataclass
class RuboCopViolation:
    """Represents a RuboCop code violation."""

    cop_name: str
    message: str
    severity: RuboCopSeverity
    file_path: str
    line_number: int
    column: int
    source: str = ""
    corrected: bool = False
    cwe: Optional[str] = None


@dataclass
class RuboCopConfig:
    """RuboCop configuration for analysis."""

    rubocop_version: str = "1.0.0"
    config_file: Optional[Path] = None
    excluded_dirs: List[str] = field(default_factory=list)
    enabled_cops: List[str] = field(default_factory=list)
    disabled_cops: List[str] = field(default_factory=list)
    autocorrect: bool = False
    parallel_jobs: int = 1


class RuboCopParser:
    """
    Parser for RuboCop code style and linting analysis.

    [20260304_FEATURE] Implements execute + parse workflow for RuboCop JSON output.

    Integrates RuboCop for comprehensive Ruby code analysis including
    style enforcement, complexity metrics, performance issues, and security.

    Graceful degradation: returns [] if rubocop is not installed.
    """

    # [20260304_FEATURE] Security-related cop prefixes
    SECURITY_COP_PREFIXES = {"Security", "Rails/ContentTag", "Rails/OutputSafety"}

    def __init__(self) -> None:
        """Initialize RuboCop parser."""
        self.config = RuboCopConfig()

    def execute_rubocop(
        self, paths: List[Path], config: Optional[RuboCopConfig] = None
    ) -> List[RuboCopViolation]:
        """
        Run rubocop --format json on given paths.

        [20260304_FEATURE] Graceful degradation when rubocop not installed.

        Returns empty list if rubocop not available.
        """
        if shutil.which("rubocop") is None:
            return []
        cmd = ["rubocop", "--format", "json", "--no-color"] + [str(p) for p in paths]
        cfg = config or self.config
        if cfg.config_file:
            cmd += ["--config", str(cfg.config_file)]
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,
            )
            return self.parse_json_output(result.stdout)
        except (subprocess.TimeoutExpired, OSError):
            return []

    def parse_json_output(self, output: str) -> List[RuboCopViolation]:
        """
        Parse rubocop --format json output.

        [20260304_FEATURE] JSON format: {"files":[{"path":...,"offenses":[...]}],"summary":{...}}
        """
        if not output or not output.strip():
            return []
        try:
            data = json.loads(output)
        except json.JSONDecodeError:
            return []

        violations: List[RuboCopViolation] = []
        for file_entry in data.get("files", []):
            file_path = file_entry.get("path", "")
            for offense in file_entry.get("offenses", []):
                severity_str = offense.get("severity", "warning")
                try:
                    severity = RuboCopSeverity(severity_str)
                except ValueError:
                    severity = RuboCopSeverity.WARNING
                loc = offense.get("location", {})
                violations.append(
                    RuboCopViolation(
                        cop_name=offense.get("cop_name", ""),
                        message=offense.get("message", ""),
                        severity=severity,
                        file_path=file_path,
                        line_number=loc.get("line", 0),
                        column=loc.get("column", 0),
                        source=offense.get("highlighted_source", ""),
                        corrected=offense.get("corrected", False),
                    )
                )
        return violations

    def load_config(self, config_file: Path) -> RuboCopConfig:
        """Load RuboCop configuration from .rubocop.yml."""
        # [20260304_FEATURE] Return config pointing at given file; YAML parsing is optional
        cfg = RuboCopConfig()
        cfg.config_file = config_file
        return cfg

    def categorize_violations(
        self, violations: List[RuboCopViolation]
    ) -> Dict[str, List[RuboCopViolation]]:
        """
        Group violations by cop name prefix.

        [20260304_FEATURE] Groups: Style, Layout, Lint, Metrics, Security, Rails, etc.
        """
        categories: Dict[str, List[RuboCopViolation]] = {}
        for v in violations:
            category = v.cop_name.split("/")[0] if "/" in v.cop_name else "Other"
            categories.setdefault(category, []).append(v)
        return categories

    def apply_autocorrect(
        self, paths: List[Path], config: Optional[RuboCopConfig] = None
    ) -> Dict[str, int]:
        """
        Run rubocop -A on given paths, return corrected counts per file.

        [20260304_FEATURE] Returns {} if rubocop not installed.
        """
        if shutil.which("rubocop") is None:
            return {}
        cmd = ["rubocop", "-A", "--format", "json", "--no-color"] + [str(p) for p in paths]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            data = json.loads(result.stdout or "{}")
        except (subprocess.TimeoutExpired, OSError, json.JSONDecodeError):
            return {}
        corrected: Dict[str, int] = {}
        for file_entry in data.get("files", []):
            corrected[file_entry["path"]] = sum(
                1 for o in file_entry.get("offenses", []) if o.get("corrected")
            )
        return corrected

    def generate_report(
        self, violations: List[RuboCopViolation], format: str = "json"
    ) -> str:
        """
        Generate a structured JSON report of violations.

        [20260304_FEATURE] Returns JSON string.
        """
        categories = self.categorize_violations(violations)
        report: Dict[str, Any] = {
            "tool": "rubocop",
            "total_violations": len(violations),
            "by_category": {
                cat: len(viols) for cat, viols in categories.items()
            },
            "violations": [
                {
                    "cop": v.cop_name,
                    "message": v.message,
                    "severity": v.severity.value,
                    "file": v.file_path,
                    "line": v.line_number,
                    "column": v.column,
                }
                for v in violations
            ],
        }
        return json.dumps(report, indent=2)

    def calculate_metrics(self, violations: List[RuboCopViolation]) -> Dict[str, Any]:
        """
        Calculate aggregate metrics from violations.

        [20260304_FEATURE] Returns counts by severity and category.
        """
        by_severity: Dict[str, int] = {}
        for v in violations:
            by_severity[v.severity.value] = by_severity.get(v.severity.value, 0) + 1
        return {
            "total": len(violations),
            "by_severity": by_severity,
            "by_category": {
                cat: len(viols)
                for cat, viols in self.categorize_violations(violations).items()
            },
        }

    def detect_rails_specific_issues(
        self, violations: List[RuboCopViolation]
    ) -> List[RuboCopViolation]:
        """
        Filter violations that are Rails-specific cops.

        [20260304_FEATURE] Returns violations with cop_name starting with 'Rails/'.
        """
        return [v for v in violations if v.cop_name.startswith("Rails/")]
