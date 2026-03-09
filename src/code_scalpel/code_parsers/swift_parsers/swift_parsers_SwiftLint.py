#!/usr/bin/env python3
"""SwiftLint Parser - Swift Code Style and Linting Analysis.

[20260304_FEATURE] Full implementation replacing Phase 2 stubs.

SwiftLint is the de-facto Swift linting tool maintained by Realm.
Reference: https://github.com/realm/SwiftLint
Command:   swiftlint lint --reporter json [paths...]
Output format: JSON array of violation objects.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


class SwiftLintSeverity(Enum):
    """SwiftLint violation severity levels."""

    NOTICE = "notice"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class SwiftLintViolation:
    """Represents a SwiftLint code violation."""

    rule_id: str
    message: str
    severity: SwiftLintSeverity
    file_path: str
    line_number: int
    column: int
    source: str = ""
    correctable: bool = False


@dataclass
class SwiftLintConfig:
    """SwiftLint configuration for analysis."""

    swiftlint_version: str = "0.48.0"
    config_file: Optional[Path] = None
    excluded_dirs: List[str] = field(default_factory=list)
    enabled_rules: List[str] = field(default_factory=list)
    disabled_rules: List[str] = field(default_factory=list)
    strict_mode: bool = False
    autocorrect: bool = False


# [20260304_FEATURE] CWE mappings for security-relevant SwiftLint rules
_RULE_CWE_MAP: Dict[str, str] = {
    "force_cast": "CWE-704",          # Incorrect Type Conversion
    "force_try": "CWE-390",           # Detection of Error Condition Without Action
    "force_unwrapping": "CWE-476",    # NULL Pointer Dereference
    "weak_delegate": "CWE-401",       # Memory Leak
    "implicit_return": "CWE-710",     # Improper Adherence to Coding Standards
}


class SwiftLintParser:
    """
    Parser for SwiftLint code style and linting analysis.

    [20260304_FEATURE] Full implementation: execute + parse JSON output.

    Graceful degradation: returns [] if swiftlint is not installed.
    """

    def __init__(self) -> None:
        """Initialise SwiftLint parser."""
        self.config = SwiftLintConfig()
        self.violations: List[SwiftLintViolation] = []

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def execute_swiftlint(
        self, paths: List[Path], config: Optional[SwiftLintConfig] = None
    ) -> List[SwiftLintViolation]:
        """
        Run ``swiftlint lint --reporter json`` on the given paths.

        [20260304_FEATURE] Graceful degradation when swiftlint not installed.

        Returns an empty list if swiftlint is unavailable or times out.
        """
        if shutil.which("swiftlint") is None:
            return []
        cmd = ["swiftlint", "lint", "--reporter", "json"] + [str(p) for p in paths]
        cfg = config or self.config
        if cfg.config_file:
            cmd += ["--config", str(cfg.config_file)]
        if cfg.strict_mode:
            cmd.append("--strict")
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,
            )
            return self.parse_json_report_output(result.stdout)
        except (subprocess.TimeoutExpired, OSError):
            return []

    # ------------------------------------------------------------------
    # Parsing
    # ------------------------------------------------------------------

    def parse_json_report(self, report_path: Path) -> List[SwiftLintViolation]:
        """Parse a saved swiftlint JSON report file.

        [20260304_FEATURE] Reads from disk then delegates to parse_json_report_output.
        """
        try:
            return self.parse_json_report_output(report_path.read_text(encoding="utf-8"))
        except OSError:
            return []

    def parse_json_report_output(self, output: str) -> List[SwiftLintViolation]:
        """
        Parse swiftlint --reporter json stdout.

        [20260304_FEATURE] JSON is an array of violation objects.
        Format example::

            [{"character": null, "file": "/p/File.swift", "line": 5,
              "reason": "Trailing whitespace.", "rule_id": "trailing_whitespace",
              "severity": "Warning", "type": "Trailing Whitespace"}]
        """
        if not output or not output.strip():
            return []
        try:
            data = json.loads(output)
        except json.JSONDecodeError:
            return []
        if not isinstance(data, list):
            return []

        violations: List[SwiftLintViolation] = []
        for item in data:
            sev_str = item.get("severity", "warning").lower()
            try:
                severity = SwiftLintSeverity(sev_str)
            except ValueError:
                severity = SwiftLintSeverity.WARNING
            violations.append(
                SwiftLintViolation(
                    rule_id=item.get("rule_id", ""),
                    message=item.get("reason", ""),
                    severity=severity,
                    file_path=item.get("file", ""),
                    line_number=item.get("line", 0),
                    column=item.get("character") or 0,
                    source=item.get("type", ""),
                    correctable=bool(item.get("correctable", False)),
                )
            )
        return violations

    # ------------------------------------------------------------------
    # Analysis helpers
    # ------------------------------------------------------------------

    def load_config(self, config_file: Path) -> SwiftLintConfig:
        """Return a SwiftLintConfig pointing at the given .swiftlint.yml."""
        cfg = SwiftLintConfig()
        cfg.config_file = config_file
        return cfg

    def categorize_violations(
        self, violations: List[SwiftLintViolation]
    ) -> Dict[str, List[SwiftLintViolation]]:
        """
        Group violations by rule category prefix.

        [20260304_FEATURE] Rule IDs are snake_case; we split on first '_' for category.
        """
        categories: Dict[str, List[SwiftLintViolation]] = {}
        for v in violations:
            parts = v.rule_id.split("_", 1)
            category = parts[0].capitalize() if parts else "Other"
            categories.setdefault(category, []).append(v)
        return categories

    def apply_autocorrect(
        self, paths: List[Path], config: Optional[SwiftLintConfig] = None
    ) -> Dict[str, int]:
        """
        Run ``swiftlint --fix`` to autocorrect violations.

        [20260304_FEATURE] Returns {} if swiftlint not installed.
        """
        if shutil.which("swiftlint") is None:
            return {}
        cmd = ["swiftlint", "--fix", "--reporter", "json"] + [str(p) for p in paths]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            data = json.loads(result.stdout or "[]")
            corrected: Dict[str, int] = {}
            for item in data if isinstance(data, list) else []:
                fp = item.get("file", "")
                if fp:
                    corrected[fp] = corrected.get(fp, 0) + 1
            return corrected
        except (subprocess.TimeoutExpired, OSError, json.JSONDecodeError):
            return {}

    def generate_report(
        self, violations: List[SwiftLintViolation], format: str = "json"
    ) -> str:
        """
        Generate a structured report.

        [20260304_FEATURE] JSON and plain-text formats supported.
        """
        if format == "json":
            return json.dumps(
                [
                    {
                        "rule_id": v.rule_id,
                        "message": v.message,
                        "severity": v.severity.value,
                        "file_path": v.file_path,
                        "line_number": v.line_number,
                        "column": v.column,
                        "cwe": _RULE_CWE_MAP.get(v.rule_id),
                    }
                    for v in violations
                ],
                indent=2,
            )
        # plain-text fallback
        lines = [
            f"{v.file_path}:{v.line_number}:{v.column}: {v.severity.value}: {v.message} ({v.rule_id})"
            for v in violations
        ]
        return "\n".join(lines)

    def calculate_metrics(self, violations: List[SwiftLintViolation]) -> Dict[str, Any]:
        """
        Aggregate violation counts by severity and rule.

        [20260304_FEATURE] Returns summary dict.
        """
        by_severity: Dict[str, int] = {}
        by_rule: Dict[str, int] = {}
        for v in violations:
            by_severity[v.severity.value] = by_severity.get(v.severity.value, 0) + 1
            by_rule[v.rule_id] = by_rule.get(v.rule_id, 0) + 1
        return {
            "total": len(violations),
            "by_severity": by_severity,
            "by_rule": by_rule,
            "correctable": sum(1 for v in violations if v.correctable),
        }

    def detect_ios_specific_issues(
        self, violations: List[SwiftLintViolation]
    ) -> List[SwiftLintViolation]:
        """
        Filter violations commonly associated with iOS development.

        [20260304_FEATURE] Rules known to affect UIKit / SwiftUI codebases.
        """
        ios_rules = {
            "force_cast", "force_try", "force_unwrapping",
            "weak_delegate", "prohibited_interface_builder",
            "implicitly_unwrapped_optional",
        }
        return [v for v in violations if v.rule_id in ios_rules]

