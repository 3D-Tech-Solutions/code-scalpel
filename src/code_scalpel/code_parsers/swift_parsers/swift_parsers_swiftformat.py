#!/usr/bin/env python3
"""SwiftFormat Parser - Swift Code Formatting and Style Normalization.

[20260304_FEATURE] Full implementation replacing Phase 2 stubs.

SwiftFormat is a command-line tool for reformatting Swift code.
Reference: https://github.com/nicklockwood/SwiftFormat
Command:   swiftformat --lint [paths...]
Output:    Plain-text lines; exit 1 if files would be reformatted.

           Also supports ``swiftformat --infooptions`` and
           ``swiftformat --quiet --lint`` for CI pipelines.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


# [20260304_FEATURE] Compiled pattern for SwiftFormat lint output lines.
# Example: "/path/to/File.swift:5:1: warning: remove trailing space"
_LINE_RE = re.compile(
    r"^(?P<file>[^:]+):(?P<line>\d+):(?P<col>\d+):\s*(?P<issue_type>[^:]+):\s*(?P<message>.+)$"
)
# Fallback: "  /path/to/File.swift  would reformat"
_REFORMAT_RE = re.compile(r"^\s*(?P<file>\S+\.swift)\s+would reformat\s*$")


@dataclass
class FormattingIssue:
    """Represents a formatting issue detected by SwiftFormat."""

    issue_type: str
    message: str
    file_path: str
    line_number: int
    column: int
    suggested_fix: Optional[str] = None


class SwiftFormatParser:
    """
    Parser for SwiftFormat code formatting and style analysis.

    [20260304_FEATURE] Full implementation: execute + parse text output.

    Graceful degradation: returns [] if swiftformat is not installed.
    """

    def __init__(self) -> None:
        """Initialise SwiftFormat parser."""
        self.issues: List[FormattingIssue] = []

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def execute_swiftformat(
        self, paths: List[Path], options: Optional[List[str]] = None
    ) -> List[FormattingIssue]:
        """
        Run ``swiftformat --lint`` on the given paths.

        [20260304_FEATURE] Graceful degradation when swiftformat not installed.

        Returns an empty list if swiftformat is unavailable or times out.
        """
        if shutil.which("swiftformat") is None:
            return []
        cmd = ["swiftformat", "--lint"] + [str(p) for p in paths]
        if options:
            cmd += options
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,
            )
            # swiftformat exits 1 if any files would be reformatted — not an error
            return self.parse_lint_output(result.stdout + result.stderr)
        except (subprocess.TimeoutExpired, OSError):
            return []

    # ------------------------------------------------------------------
    # Parsing
    # ------------------------------------------------------------------

    def parse_format_config(self, config_path: Path) -> Dict:
        """
        Parse a .swiftformat config file into a dict.

        [20260304_FEATURE] Config is line-separated ``--option value`` pairs.
        """
        config: Dict[str, str] = {}
        try:
            for line in config_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if line.startswith("--"):
                    parts = line[2:].split(None, 1)
                    key = parts[0]
                    value = parts[1] if len(parts) > 1 else "true"
                    config[key] = value
        except OSError:
            pass
        return config

    def parse_lint_output(self, output: str) -> List[FormattingIssue]:
        """
        Parse ``swiftformat --lint`` plain-text output.

        [20260304_FEATURE] Handles two output patterns:
        1. ``/path/File.swift:5:1: warning: <message>``
        2. ``  /path/File.swift  would reformat``
        """
        issues: List[FormattingIssue] = []
        for raw_line in output.splitlines():
            m = _LINE_RE.match(raw_line)
            if m:
                issues.append(
                    FormattingIssue(
                        issue_type=m.group("issue_type").strip(),
                        message=m.group("message").strip(),
                        file_path=m.group("file").strip(),
                        line_number=int(m.group("line")),
                        column=int(m.group("col")),
                    )
                )
                continue
            m2 = _REFORMAT_RE.match(raw_line)
            if m2:
                issues.append(
                    FormattingIssue(
                        issue_type="reformat",
                        message="File would be reformatted",
                        file_path=m2.group("file"),
                        line_number=0,
                        column=0,
                    )
                )
        return issues

    # ------------------------------------------------------------------
    # Analysis helpers
    # ------------------------------------------------------------------

    def apply_formatting(
        self, paths: List[Path], options: Optional[List[str]] = None
    ) -> Dict[str, int]:
        """
        Run ``swiftformat`` (without --lint) to apply in-place formatting.

        [20260304_FEATURE] Returns {file_path: 1} for each reformatted file.
        Returns {} if swiftformat not installed.
        """
        if shutil.which("swiftformat") is None:
            return {}
        cmd = ["swiftformat"] + [str(p) for p in paths]
        if options:
            cmd += options
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            formatted: Dict[str, int] = {}
            for line in (result.stdout + result.stderr).splitlines():
                if "formatted" in line.lower() and ".swift" in line:
                    # Extract file path from lines like "Format /path/file.swift"
                    for token in line.split():
                        if token.endswith(".swift"):
                            formatted[token] = 1
            return formatted
        except (subprocess.TimeoutExpired, OSError):
            return {}

    def detect_formatting_violations(
        self, issues: List[FormattingIssue]
    ) -> List[FormattingIssue]:
        """Return only issues that represent enforcement violations (non-info)."""
        return [i for i in issues if i.issue_type.lower() not in ("info", "debug")]

    def generate_format_report(self, issues: List[FormattingIssue]) -> str:
        """
        Generate a compact plain-text report.

        [20260304_FEATURE] One line per issue.
        """
        lines = [
            f"{i.file_path}:{i.line_number}:{i.column}: {i.issue_type}: {i.message}"
            for i in issues
        ]
        return "\n".join(lines)

