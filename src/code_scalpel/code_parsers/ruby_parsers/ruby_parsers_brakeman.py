#!/usr/bin/env python3
"""
Brakeman Parser - Ruby Security Vulnerability Scanning.

[20260304_FEATURE] Full implementation of Brakeman parser for Rails security analysis.
Brakeman is a static analysis tool that checks Ruby on Rails applications for
security vulnerabilities.

Output format: brakeman -f json
"""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


# [20260304_FEATURE] Brakeman warning_type → CWE mapping
BRAKEMAN_CWE_MAP: Dict[str, str] = {
    "SQL Injection": "CWE-89",
    "Cross-Site Scripting": "CWE-79",
    "Cross Site Scripting": "CWE-79",
    "Command Injection": "CWE-78",
    "Path Traversal": "CWE-22",
    "Mass Assignment": "CWE-915",
    "Remote Code Execution": "CWE-78",
    "Denial of Service": "CWE-400",
    "CSRF": "CWE-352",
    "Redirect": "CWE-601",
    "File Access": "CWE-22",
    "Deserialization of Untrusted Data": "CWE-502",
    "Hardcoded Secret": "CWE-798",
    "Hardcoded Password": "CWE-798",
    "XML Injection": "CWE-611",
    "Format Validation": "CWE-20",
    "Authentication": "CWE-287",
    "Authorization": "CWE-285",
}


class VulnerabilityType(Enum):
    """Brakeman vulnerability types."""

    SQL_INJECTION = "SQL Injection"
    MASS_ASSIGNMENT = "Mass Assignment"
    XSS = "Cross-Site Scripting"
    CSRF = "CSRF"
    RCE = "Remote Code Execution"
    HARDCODED_SECRET = "Hardcoded Secret"
    REDIRECT = "Redirect"
    PATH_TRAVERSAL = "Path Traversal"
    COMMAND_INJECTION = "Command Injection"


@dataclass
class BrakemanVulnerability:
    """Represents a security vulnerability detected by Brakeman."""

    vuln_type: str
    message: str
    file_path: str
    line_number: int
    severity: str
    confidence: str
    code: str = ""
    cwe: Optional[str] = None
    link: str = ""


class BrakemanParser:
    """
    Parser for Brakeman Rails security vulnerability scanning.

    [20260304_FEATURE] Implements execute + parse workflow for Brakeman JSON output.

    Detects security issues including SQL injection, mass assignment,
    XSS, and other OWASP vulnerabilities in Rails applications.

    Graceful degradation: returns [] if brakeman is not installed.
    """

    def __init__(self) -> None:
        """Initialize Brakeman parser."""
        pass

    def execute_brakeman(self, paths: List[Path]) -> List[BrakemanVulnerability]:
        """
        Run brakeman -f json on given path(s).

        [20260304_FEATURE] Graceful degradation when brakeman not installed.
        """
        if shutil.which("brakeman") is None:
            return []
        cmd = ["brakeman", "-f", "json", "-q"] + [str(p) for p in paths]
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

    def parse_json_output(self, output: str) -> List[BrakemanVulnerability]:
        """
        Parse brakeman -f json output.

        [20260304_FEATURE] JSON format: {"warnings":[{"warning_type":...,"message":...}],...}
        """
        if not output or not output.strip():
            return []
        try:
            data = json.loads(output)
        except json.JSONDecodeError:
            return []

        vulns: List[BrakemanVulnerability] = []
        for warning in data.get("warnings", []):
            vuln_type = warning.get("warning_type", "Unknown")
            cwe = BRAKEMAN_CWE_MAP.get(vuln_type)
            vulns.append(
                BrakemanVulnerability(
                    vuln_type=vuln_type,
                    message=warning.get("message", ""),
                    file_path=warning.get("file", ""),
                    line_number=warning.get("line", 0) or 0,
                    severity=warning.get("confidence", "unknown").lower(),
                    confidence=warning.get("confidence", "Unknown"),
                    code=warning.get("code", ""),
                    cwe=cwe,
                    link=warning.get("link", ""),
                )
            )
        return vulns

    def load_config(self, config_file: Path) -> Dict[str, Any]:
        """Load Brakeman configuration from brakeman.yml."""
        # [20260304_FEATURE] Return config dict; full YAML parsing is optional
        return {"config_file": str(config_file)}

    def categorize_vulnerabilities(
        self, vulns: List[BrakemanVulnerability]
    ) -> Dict[str, List[BrakemanVulnerability]]:
        """
        Group vulnerabilities by type.

        [20260304_FEATURE] Categories: SQL Injection, XSS, etc.
        """
        categories: Dict[str, List[BrakemanVulnerability]] = {}
        for v in vulns:
            categories.setdefault(v.vuln_type, []).append(v)
        return categories

    def detect_sql_injection(
        self, vulns: List[BrakemanVulnerability]
    ) -> List[BrakemanVulnerability]:
        """Filter SQL Injection vulnerabilities."""
        return [v for v in vulns if "SQL" in v.vuln_type or v.cwe == "CWE-89"]

    def detect_mass_assignment(
        self, vulns: List[BrakemanVulnerability]
    ) -> List[BrakemanVulnerability]:
        """Filter Mass Assignment vulnerabilities."""
        return [v for v in vulns if "Mass Assignment" in v.vuln_type]

    def detect_xss_vulnerabilities(
        self, vulns: List[BrakemanVulnerability]
    ) -> List[BrakemanVulnerability]:
        """Filter XSS vulnerabilities."""
        return [v for v in vulns if v.cwe == "CWE-79" or "Scripting" in v.vuln_type]

    def generate_security_report(self, vulns: List[BrakemanVulnerability]) -> str:
        """
        Generate a structured JSON security report.

        [20260304_FEATURE] Returns JSON string with findings and CWE mappings.
        """
        categories = self.categorize_vulnerabilities(vulns)
        report: Dict[str, Any] = {
            "tool": "brakeman",
            "total_vulnerabilities": len(vulns),
            "by_type": {k: len(v) for k, v in categories.items()},
            "vulnerabilities": [
                {
                    "type": v.vuln_type,
                    "message": v.message,
                    "file": v.file_path,
                    "line": v.line_number,
                    "confidence": v.confidence,
                    "cwe": v.cwe,
                }
                for v in vulns
            ],
        }
        return json.dumps(report, indent=2)
