"""Cargo Audit Parser — parse ``cargo audit --json`` output.

[20260305_FEATURE] Free CLI tool; graceful degradation if cargo-audit absent.

JSON output structure (cargo-audit ≥ 0.17):
    {
      "database": {...},
      "lockfile": {...},
      "settings": {...},
      "vulnerabilities": {
        "found": true,
        "count": 2,
        "list": [
          {
            "advisory": {
              "id": "RUSTSEC-2023-0001",
              "package": "openssl",
              "title": "...",
              "description": "...",
              "severity": "high",
              "url": "https://rustsec.org/advisories/RUSTSEC-2023-0001"
            },
            "versions": {"patched": [...], "unaffected": [...]},
            "affected": {...}
          }
        ]
      }
    }
"""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


@dataclass
class CargoAuditFinding:
    """A single cargo audit vulnerability.

    [20260305_FEATURE] Represents one RUSTSEC advisory.
    """

    advisory_id: str
    package: str
    title: str
    description: str
    severity: Optional[str]
    url: Optional[str]
    patched_versions: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "advisory_id": self.advisory_id,
            "package": self.package,
            "title": self.title,
            "description": self.description,
            "severity": self.severity,
            "url": self.url,
            "patched_versions": self.patched_versions,
        }


class CargoAuditParser:
    """Parser for ``cargo audit --json`` output.

    [20260305_FEATURE] Free CLI tool parser with graceful degradation.

    Execute::
        parser = CargoAuditParser()
        findings = parser.execute_cargo_audit([Path("my_project/")])

    Parse raw output::
        findings = parser.parse_output(raw_json)
    """

    TOOL_NAME = "cargo-audit"
    DISPLAY_NAME = "cargo audit"

    # ---------------------------------------------------------------------------
    # Execution
    # ---------------------------------------------------------------------------

    def execute_cargo_audit(
        self,
        paths: List[Path],
        extra_args: Optional[List[str]] = None,
    ) -> List[CargoAuditFinding]:
        """Run ``cargo audit --json`` on the given project paths.

        Args:
            paths: Project directories containing Cargo.lock.
            extra_args: Extra arguments forwarded to cargo audit.

        Returns:
            List of CargoAuditFinding objects, empty if tool unavailable.
        """
        if shutil.which("cargo") is None:
            return []

        results: List[CargoAuditFinding] = []
        for path in paths:
            cwd = path if path.is_dir() else path.parent
            cmd = ["cargo", "audit", "--json"]
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
                # cargo audit exits 1 when vulnerabilities are found — still parse
                results.extend(self.parse_output(proc.stdout or proc.stderr))
            except (subprocess.TimeoutExpired, OSError):
                pass

        return results

    # ---------------------------------------------------------------------------
    # Parsing
    # ---------------------------------------------------------------------------

    def parse_output(self, output: str) -> List[CargoAuditFinding]:
        """Parse the JSON output from ``cargo audit --json``.

        Args:
            output: Raw stdout from ``cargo audit --json``.

        Returns:
            List of CargoAuditFinding objects.
        """
        findings: List[CargoAuditFinding] = []
        if not output or not output.strip():
            return findings
        try:
            data = json.loads(output)
        except json.JSONDecodeError:
            # Try first valid JSON object (some versions emit extra lines)
            for line in output.splitlines():
                line = line.strip()
                if line.startswith("{"):
                    try:
                        data = json.loads(line)
                        break
                    except json.JSONDecodeError:
                        continue
            else:
                return findings

        vuln_section = data.get("vulnerabilities", {})
        vuln_list = vuln_section.get("list", [])
        for item in vuln_list:
            advisory = item.get("advisory", {})
            versions = item.get("versions", {})
            patched = versions.get("patched", [])
            findings.append(
                CargoAuditFinding(
                    advisory_id=advisory.get("id", ""),
                    package=advisory.get("package", ""),
                    title=advisory.get("title", ""),
                    description=advisory.get("description", ""),
                    severity=advisory.get("severity"),
                    url=advisory.get("url"),
                    patched_versions=patched,
                )
            )
        return findings
