"""Clippy Parser — parse `cargo clippy --message-format json` output.

[20260305_FEATURE] Free CLI tool; graceful degradation if cargo/clippy absent.

Output format: newline-delimited JSON objects (compiler-message format).
Each object has:
    {"reason": "compiler-message", "message": {"code": ..., "level": "warning|error",
     "message": "...", "spans": [{"file_name": ..., "line_start": ..., "line_end": ...,
     "column_start": ...}]}}
"""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


@dataclass
class ClippyDiagnostic:
    """Single Clippy diagnostic finding.

    [20260305_FEATURE] Represents one Clippy warning or error.
    """

    level: str  # "warning", "error", "note", "help"
    message: str
    code: Optional[str]
    file_path: Optional[str]
    line: int
    column: int
    suggestion: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "level": self.level,
            "message": self.message,
            "code": self.code,
            "file_path": self.file_path,
            "line": self.line,
            "column": self.column,
            "suggestion": self.suggestion,
        }


class ClippyParser:
    """Parser for `cargo clippy --message-format json` output.

    [20260305_FEATURE] Free CLI tool parser with graceful degradation.

    Execute::
        clippy_parser = ClippyParser()
        findings = clippy_parser.execute_clippy([Path("my_project/")])

    Parse raw output::
        findings = clippy_parser.parse_output(raw_json_lines)
    """

    TOOL_NAME = "clippy"
    DISPLAY_NAME = "Clippy"

    # ---------------------------------------------------------------------------
    # Execution
    # ---------------------------------------------------------------------------

    def execute_clippy(
        self,
        paths: List[Path],
        extra_args: Optional[List[str]] = None,
    ) -> List[ClippyDiagnostic]:
        """Run ``cargo clippy`` on the given project paths.

        Args:
            paths: List of project directories (containing Cargo.toml).
            extra_args: Extra arguments forwarded to cargo clippy.

        Returns:
            List of ClippyDiagnostic objects, empty list if clippy unavailable.
        """
        if shutil.which("cargo") is None:
            return []

        results: List[ClippyDiagnostic] = []
        for path in paths:
            cwd = path if path.is_dir() else path.parent
            cmd = [
                "cargo",
                "clippy",
                "--message-format",
                "json",
                "--all-targets",
                "--all-features",
            ]
            if extra_args:
                cmd.extend(extra_args)
            try:
                proc = subprocess.run(
                    cmd,
                    cwd=str(cwd),
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
                results.extend(self.parse_output(proc.stdout))
            except (subprocess.TimeoutExpired, OSError):
                pass

        return results

    # ---------------------------------------------------------------------------
    # Parsing
    # ---------------------------------------------------------------------------

    def parse_output(self, output: str) -> List[ClippyDiagnostic]:
        """Parse the newline-delimited JSON output from ``cargo clippy``.

        Args:
            output: Raw stdout from ``cargo clippy --message-format json``.

        Returns:
            List of ClippyDiagnostic objects.
        """
        findings: List[ClippyDiagnostic] = []
        for line in output.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if obj.get("reason") != "compiler-message":
                continue
            msg_obj = obj.get("message", {})
            finding = self._parse_message(msg_obj)
            if finding:
                findings.append(finding)
        return findings

    def _parse_message(self, msg: dict) -> Optional[ClippyDiagnostic]:
        """Parse a single compiler-message object."""
        level = msg.get("level", "")
        if level not in ("warning", "error", "note", "help"):
            return None
        text = msg.get("message", "")
        if not text:
            return None
        # Skip "aborting due to N previous errors" noise
        if text.startswith("aborting due to"):
            return None

        code_obj = msg.get("code") or {}
        code = code_obj.get("code") if code_obj else None

        # Primary span
        spans = msg.get("spans", [])
        primary_span = next((s for s in spans if s.get("is_primary")), None)
        if primary_span is None and spans:
            primary_span = spans[0]

        file_path: Optional[str] = None
        line = 0
        column = 0
        if primary_span:
            file_path = primary_span.get("file_name")
            line = primary_span.get("line_start", 0)
            column = primary_span.get("column_start", 0)

        # Suggestion from children
        suggestion: Optional[str] = None
        for child in msg.get("children", []):
            if child.get("level") == "help":
                suggestion = child.get("message", "")
                break

        return ClippyDiagnostic(
            level=level,
            message=text,
            code=code,
            file_path=file_path,
            line=line,
            column=column,
            suggestion=suggestion,
        )

    def categorize(self, finding: ClippyDiagnostic) -> str:
        """Return a category string for a finding.

        Categories: 'error', 'style', 'correctness', 'performance', 'complexity',
        'suspicious', 'pedantic', 'nursery', 'restriction', 'unknown'.
        """
        code = finding.code or ""
        if "deny" in finding.message.lower() or finding.level == "error":
            return "error"
        # Clippy lint categories embedded in code
        prefixes = {
            "clippy::perf": "performance",
            "clippy::correctness": "correctness",
            "clippy::complexity": "complexity",
            "clippy::style": "style",
            "clippy::suspicious": "suspicious",
            "clippy::pedantic": "pedantic",
            "clippy::nursery": "nursery",
            "clippy::restriction": "restriction",
        }
        for prefix, cat in prefixes.items():
            if code.startswith(prefix):
                return cat
        if code.startswith("clippy::"):
            return "style"
        return "unknown"
