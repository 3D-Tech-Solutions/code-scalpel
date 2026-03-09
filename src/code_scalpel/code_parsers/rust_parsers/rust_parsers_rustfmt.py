"""Rustfmt Parser — parse ``rustfmt --check`` output.

[20260305_FEATURE] Free CLI tool; graceful degradation if rustfmt absent.

``rustfmt --check`` exits 1 and prints lines like:
    Diff in src/main.rs at line 5:
    ...
or simply lists files that would be reformatted.

``rustfmt --emit stdout`` (or ``--check --verbose``) shows diffs.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


@dataclass
class RustfmtFinding:
    """A single rustfmt formatting issue.

    [20260305_FEATURE] Represents one file/line that would be reformatted.
    """

    file_path: str
    line: int
    message: str

    def to_dict(self) -> dict:
        return {
            "file_path": self.file_path,
            "line": self.line,
            "message": self.message,
        }


class RustfmtParser:
    """Parser for ``rustfmt --check`` output.

    [20260305_FEATURE] Free CLI tool parser with graceful degradation.

    Execute::
        parser = RustfmtParser()
        findings = parser.execute_rustfmt([Path("src/main.rs")])

    Parse raw output::
        findings = parser.parse_output(raw_output)
    """

    TOOL_NAME = "rustfmt"
    DISPLAY_NAME = "rustfmt"

    # Pattern: "Diff in src/main.rs at line 5:"
    _DIFF_LINE_RE = re.compile(r"Diff in (.+?) at line (\d+):")
    # Pattern: "Would reformat: src/main.rs" (from --check on some versions)
    _WOULD_REFORMAT_RE = re.compile(r"[Ww]ould reformat[:\s]+(.+)")

    # ---------------------------------------------------------------------------
    # Execution
    # ---------------------------------------------------------------------------

    def execute_rustfmt(
        self,
        paths: List[Path],
        extra_args: Optional[List[str]] = None,
    ) -> List[RustfmtFinding]:
        """Run ``rustfmt --check`` on the given source files.

        Args:
            paths: List of ``.rs`` source files or directories.
            extra_args: Extra arguments forwarded to rustfmt.

        Returns:
            List of RustfmtFinding objects, empty list if rustfmt unavailable.
        """
        if shutil.which("rustfmt") is None:
            return []

        results: List[RustfmtFinding] = []

        # Collect .rs files
        rs_files: List[Path] = []
        for path in paths:
            if path.is_dir():
                rs_files.extend(path.rglob("*.rs"))
            elif path.suffix == ".rs":
                rs_files.append(path)

        if not rs_files:
            return []

        cmd = ["rustfmt", "--check"] + [str(f) for f in rs_files]
        if extra_args:
            cmd.extend(extra_args)
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
            )
            results.extend(self.parse_output(proc.stdout + proc.stderr))
        except (subprocess.TimeoutExpired, OSError):
            pass

        return results

    # ---------------------------------------------------------------------------
    # Parsing
    # ---------------------------------------------------------------------------

    def parse_output(self, output: str) -> List[RustfmtFinding]:
        """Parse the output from ``rustfmt --check``.

        Args:
            output: Raw stdout/stderr from rustfmt.

        Returns:
            List of RustfmtFinding objects.
        """
        findings: List[RustfmtFinding] = []
        for line in output.splitlines():
            line = line.strip()
            if not line:
                continue
            # "Diff in src/main.rs at line 5:"
            m = self._DIFF_LINE_RE.search(line)
            if m:
                findings.append(
                    RustfmtFinding(
                        file_path=m.group(1).strip(),
                        line=int(m.group(2)),
                        message="rustfmt: file would be reformatted",
                    )
                )
                continue
            # "Would reformat: src/lib.rs"
            m2 = self._WOULD_REFORMAT_RE.search(line)
            if m2:
                findings.append(
                    RustfmtFinding(
                        file_path=m2.group(1).strip(),
                        line=0,
                        message="rustfmt: file would be reformatted",
                    )
                )
        return findings
