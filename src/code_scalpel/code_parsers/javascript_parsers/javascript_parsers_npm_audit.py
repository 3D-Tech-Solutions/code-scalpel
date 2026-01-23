#!/usr/bin/env python3
"""
NPM Audit JavaScript Parser - Vulnerability scanning for npm dependencies.


Reference: https://docs.npmjs.com/cli/v10/commands/npm-audit
Command: npm audit --json
"""

from dataclasses import dataclass
from pathlib import Path


@dataclass
class Vulnerability:
    """NPM audit vulnerability finding."""

    id: str
    cve_id: str | None
    package_name: str
    version: str
    severity: str  # CRITICAL, HIGH, MODERATE, LOW
    title: str
    description: str


class NPMAuditParser:
    """Parser for npm audit vulnerability reports."""

    def __init__(self, audit_output_path: Path):
        """Initialize npm audit parser.

        Args:
            audit_output_path: Path to npm audit JSON output
        """
        self.audit_output_path = Path(audit_output_path)

    def parse(self) -> dict:
        """Parse npm audit vulnerability report.


        Returns:
            Dictionary with vulnerability findings
        """
        raise NotImplementedError("npm audit parser under development")
