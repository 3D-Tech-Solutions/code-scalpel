#!/usr/bin/env python3
"""
Fasterer Parser - Ruby Performance Anti-Pattern Detection.

[20260304_FEATURE] Full implementation of Fasterer parser for Ruby performance analysis.
Fasterer suggests speed improvements for Ruby code using fasterer CLI.

Output format: fasterer <path> (text output)
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class PerformanceIssue:
    """Represents a performance issue detected by Fasterer."""

    issue_type: str
    message: str
    file_path: str
    line_number: int
    column: int = 0
    severity: str = "warning"
    suggestion: Optional[str] = None


class FastererParser:
    """
    Parser for Fasterer Ruby performance anti-pattern detection.

    [20260304_FEATURE] Implements execute + parse workflow for Fasterer text output.

    Identifies performance issues and inefficient coding patterns
    in Ruby code that could impact application performance.

    Graceful degradation: returns [] if fasterer is not installed.
    """

    # [20260304_FEATURE] Known Fasterer patterns → suggestion mapping
    SUGGESTIONS: Dict[str, str] = {
        "Array#flatten": "Use Array#flatten(1) or manual concat when depth is known",
        "Array#count": "Use Array#length or Array#size for counting without a block",
        "Hash#keys.each": "Use Hash#each_key instead of Hash#keys.each",
        "Hash#values.each": "Use Hash#each_value instead of Hash#values.each",
        "for loop": "Use .each instead of for loops",
        "define_method": "Use def instead of define_method for simple methods",
        "rescue Exception": "Rescue StandardError instead of Exception",
        "shuffle.first": "Use sample instead of shuffle.first",
        "sort.first": "Use min instead of sort.first",
        "sort.last": "Use max instead of sort.last",
    }

    def __init__(self) -> None:
        """Initialize Fasterer parser."""
        pass

    def execute_fasterer(self, paths: List[Path]) -> List[PerformanceIssue]:
        """
        Run fasterer on given paths.

        [20260304_FEATURE] Graceful degradation when fasterer not installed.
        """
        if shutil.which("fasterer") is None:
            return []
        all_issues: List[PerformanceIssue] = []
        for path in paths:
            try:
                result = subprocess.run(
                    ["fasterer", str(path)],
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
                all_issues.extend(self.parse_text_output(result.stdout, str(path)))
            except (subprocess.TimeoutExpired, OSError):
                continue
        return all_issues

    def parse_text_output(self, output: str, default_file: str = "") -> List[PerformanceIssue]:
        """
        Parse fasterer text output.

        [20260304_FEATURE] Fasterer format:
            path/to/file.rb
              Line 42: shuffle.first is slower than sample.
        """
        if not output or not output.strip():
            return []
        issues: List[PerformanceIssue] = []
        current_file = default_file
        for line in output.splitlines():
            # File header line (no leading whitespace, ends with .rb or similar)
            if not line.startswith(" ") and not line.startswith("\t") and "Line" not in line:
                stripped = line.strip()
                if stripped:
                    current_file = stripped
                continue
            # Issue line: "  Line 42: message"
            m = re.match(r"\s+Line\s+(\d+):\s+(.+)", line)
            if m:
                line_num = int(m.group(1))
                message = m.group(2).strip()
                issue_type = self._classify_issue(message)
                suggestion = self._get_suggestion(message)
                issues.append(
                    PerformanceIssue(
                        issue_type=issue_type,
                        message=message,
                        file_path=current_file,
                        line_number=line_num,
                        suggestion=suggestion,
                    )
                )
        return issues

    def _classify_issue(self, message: str) -> str:
        """Derive an issue type label from the message."""
        lower = message.lower()
        if "n+1" in lower:
            return "n_plus_one_query"
        if any(kw in lower for kw in ("shuffle", "sample", "sort", "min", "max")):
            return "inefficient_enumerable"
        if "each_key" in lower or "each_value" in lower:
            return "hash_traversal"
        if "for loop" in lower or "each" in lower:
            return "loop_style"
        return "performance"

    def _get_suggestion(self, message: str) -> Optional[str]:
        """Look up a suggestion for the given message."""
        for key, suggestion in self.SUGGESTIONS.items():
            if key.lower() in message.lower():
                return suggestion
        return None

    def categorize_issues(self, issues: List[PerformanceIssue]) -> Dict[str, List[PerformanceIssue]]:
        """
        Group issues by type.

        [20260304_FEATURE] Returns dict mapping issue_type → list.
        """
        categories: Dict[str, List[PerformanceIssue]] = {}
        for issue in issues:
            categories.setdefault(issue.issue_type, []).append(issue)
        return categories

    def detect_n_plus_one_queries(
        self, issues: List[PerformanceIssue]
    ) -> List[PerformanceIssue]:
        """Filter N+1 query issues."""
        return [i for i in issues if i.issue_type == "n_plus_one_query"]

    def detect_inefficient_operations(
        self, issues: List[PerformanceIssue]
    ) -> List[PerformanceIssue]:
        """Filter inefficient enumerable and hash traversal issues."""
        return [
            i for i in issues
            if i.issue_type in {"inefficient_enumerable", "hash_traversal"}
        ]

    def calculate_performance_metrics(self, issues: List[PerformanceIssue]) -> Dict[str, Any]:
        """
        Calculate aggregate performance metrics.

        [20260304_FEATURE] Returns counts by type.
        """
        categories = self.categorize_issues(issues)
        return {
            "total_issues": len(issues),
            "by_type": {k: len(v) for k, v in categories.items()},
        }

    def generate_optimization_report(self, issues: List[PerformanceIssue]) -> str:
        """
        Generate a structured JSON optimization report.

        [20260304_FEATURE] Returns JSON string.
        """
        metrics = self.calculate_performance_metrics(issues)
        report: Dict[str, Any] = {
            "tool": "fasterer",
            **metrics,
            "issues": [
                {
                    "type": i.issue_type,
                    "message": i.message,
                    "file": i.file_path,
                    "line": i.line_number,
                    "suggestion": i.suggestion,
                }
                for i in issues
            ],
        }
        return json.dumps(report, indent=2)

    # Alias for consistent naming with other parsers
    def generate_report(self, issues: List[PerformanceIssue], format: str = "json") -> str:
        """Alias for generate_optimization_report."""
        return self.generate_optimization_report(issues)
