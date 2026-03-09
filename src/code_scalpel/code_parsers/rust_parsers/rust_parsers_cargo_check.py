"""Cargo Check Parser — parse ``cargo check --message-format json`` output.

[20260305_FEATURE] Free CLI tool; graceful degradation if cargo absent.

Uses the same compiler-message JSON format as cargo clippy.
Finds compilation errors and warnings without running the linker.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


@dataclass
class CargoCheckDiagnostic:
    """Single cargo-check compiler diagnostic.

    [20260305_FEATURE] Represents one compiler error or warning.
    """

    level: str  # "error", "warning", "note"
    message: str
    code: Optional[str]
    file_path: Optional[str]
    line: int
    column: int

    def to_dict(self) -> dict:
        return {
            "level": self.level,
            "message": self.message,
            "code": self.code,
            "file_path": self.file_path,
            "line": self.line,
            "column": self.column,
        }


class CargoCheckParser:
    """Parser for ``cargo check --message-format json`` output.

    [20260305_FEATURE] Free CLI tool parser with graceful degradation.
    Uses the same JSON format as clippy — shares the parsing logic.

    Execute::
        parser = CargoCheckParser()
        findings = parser.execute_cargo_check([Path("my_project/")])

    Parse raw output::
        findings = parser.parse_output(raw_json_lines)
    """

    TOOL_NAME = "cargo-check"
    DISPLAY_NAME = "cargo check"

    # ---------------------------------------------------------------------------
    # Execution
    # ---------------------------------------------------------------------------

    def execute_cargo_check(
        self,
        paths: List[Path],
        extra_args: Optional[List[str]] = None,
    ) -> List[CargoCheckDiagnostic]:
        """Run ``cargo check --message-format json``.

        Args:
            paths: Project directories containing Cargo.toml.
            extra_args: Extra arguments forwarded to cargo check.

        Returns:
            List of CargoCheckDiagnostic objects.
        """
        if shutil.which("cargo") is None:
            return []

        results: List[CargoCheckDiagnostic] = []
        for path in paths:
            cwd = path if path.is_dir() else path.parent
            cmd = ["cargo", "check", "--message-format", "json", "--all-targets"]
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

    def parse_output(self, output: str) -> List[CargoCheckDiagnostic]:
        """Parse the newline-delimited JSON output from ``cargo check``.

        Args:
            output: Raw stdout from ``cargo check --message-format json``.

        Returns:
            List of CargoCheckDiagnostic objects.
        """
        findings: List[CargoCheckDiagnostic] = []
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

    def _parse_message(self, msg: dict) -> Optional[CargoCheckDiagnostic]:
        """Parse a single compiler-message object."""
        level = msg.get("level", "")
        if level not in ("error", "warning", "note"):
            return None
        text = msg.get("message", "")
        if not text or text.startswith("aborting due to"):
            return None

        code_obj = msg.get("code") or {}
        code = code_obj.get("code") if code_obj else None

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

        return CargoCheckDiagnostic(
            level=level,
            message=text,
            code=code,
            file_path=file_path,
            line=line,
            column=column,
        )
