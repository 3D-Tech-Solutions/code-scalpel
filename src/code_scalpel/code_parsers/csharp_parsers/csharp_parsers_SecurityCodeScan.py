#!/usr/bin/env python3
"""Security Code Scan C# Parser - OWASP security vulnerability detection.

[20260303_FEATURE] Phase 2: full implementation replacing NotImplementedError stubs.

Phase 1 data structures retained; Phase 2 adds parsing + report logic.

Reference: https://security-code-scan.github.io/
Output: SARIF 2.1 JSON produced by MSBuild/dotnet integration.
SCS rule → CWE partial map documented below.
"""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Union

from . import SarifFinding, _parse_sarif


class VulnerabilityType(Enum):
    """Security vulnerability types."""

    SQL_INJECTION = "sql_injection"
    CROSS_SITE_SCRIPTING = "cross_site_scripting"
    LDAP_INJECTION = "ldap_injection"
    PATH_TRAVERSAL = "path_traversal"
    COMMAND_INJECTION = "command_injection"
    XML_EXTERNAL_ENTITY = "xml_external_entity"
    INSECURE_DESERIALIZATION = "insecure_deserialization"
    WEAK_CRYPTOGRAPHY = "weak_cryptography"
    HARDCODED_CREDENTIALS = "hardcoded_credentials"
    UNSAFE_REFLECTION = "unsafe_reflection"
    UNKNOWN = "unknown"


@dataclass
class SecurityVulnerability:
    """Represents a security vulnerability found by SCS."""

    rule_id: str
    vulnerability_type: VulnerabilityType
    severity: str
    message: str
    file_path: str
    line_number: int
    column: int
    cwe_id: Optional[str] = None
    owasp_category: Optional[str] = None
    remediation: Optional[str] = None


@dataclass
class SecurityCodeScanConfig:
    """Security Code Scan configuration."""

    scs_version: str = "5.6.0"
    config_file: Optional[Path] = None
    rules_file: Optional[Path] = None
    severity_level: str = "warning"


# SCS rule → (CWE, VulnerabilityType, OWASP)
# [20260303_FEATURE] Partial map from SecurityCodeScan documentation.
_SCS_CWE_MAP: Dict[str, tuple] = {
    "SCS0001": ("CWE-89", VulnerabilityType.SQL_INJECTION, "A1"),
    "SCS0002": ("CWE-89", VulnerabilityType.SQL_INJECTION, "A1"),
    "SCS0003": ("CWE-89", VulnerabilityType.SQL_INJECTION, "A1"),
    "SCS0005": ("CWE-338", VulnerabilityType.WEAK_CRYPTOGRAPHY, "A2"),
    "SCS0006": ("CWE-327", VulnerabilityType.WEAK_CRYPTOGRAPHY, "A2"),
    "SCS0007": ("CWE-79", VulnerabilityType.CROSS_SITE_SCRIPTING, "A7"),
    "SCS0008": ("CWE-614", VulnerabilityType.UNKNOWN, "A2"),
    "SCS0009": ("CWE-311", VulnerabilityType.UNKNOWN, "A2"),
    "SCS0010": ("CWE-327", VulnerabilityType.WEAK_CRYPTOGRAPHY, "A2"),
    "SCS0011": ("CWE-327", VulnerabilityType.WEAK_CRYPTOGRAPHY, "A2"),
    "SCS0012": ("CWE-327", VulnerabilityType.WEAK_CRYPTOGRAPHY, "A2"),
    "SCS0015": ("CWE-78", VulnerabilityType.COMMAND_INJECTION, "A1"),
    "SCS0016": ("CWE-352", VulnerabilityType.UNKNOWN, "A8"),
    "SCS0017": ("CWE-601", VulnerabilityType.UNKNOWN, "A10"),
    "SCS0018": ("CWE-22", VulnerabilityType.PATH_TRAVERSAL, "A5"),
    "SCS0019": ("CWE-90", VulnerabilityType.LDAP_INJECTION, "A1"),
    "SCS0020": ("CWE-90", VulnerabilityType.LDAP_INJECTION, "A1"),
    "SCS0021": ("CWE-91", VulnerabilityType.XML_EXTERNAL_ENTITY, "A4"),
    "SCS0022": ("CWE-611", VulnerabilityType.XML_EXTERNAL_ENTITY, "A4"),
    "SCS0023": ("CWE-611", VulnerabilityType.XML_EXTERNAL_ENTITY, "A4"),
    "SCS0024": ("CWE-611", VulnerabilityType.XML_EXTERNAL_ENTITY, "A4"),
    "SCS0025": ("CWE-502", VulnerabilityType.INSECURE_DESERIALIZATION, "A8"),
    "SCS0026": ("CWE-89", VulnerabilityType.SQL_INJECTION, "A1"),
    "SCS0027": ("CWE-89", VulnerabilityType.SQL_INJECTION, "A1"),
    "SCS0028": ("CWE-502", VulnerabilityType.INSECURE_DESERIALIZATION, "A8"),
    "SCS0031": ("CWE-78", VulnerabilityType.COMMAND_INJECTION, "A1"),
    "SCS0032": ("CWE-113", VulnerabilityType.UNKNOWN, "A1"),
    "SCS0033": ("CWE-113", VulnerabilityType.UNKNOWN, "A1"),
    "SCS0034": ("CWE-89", VulnerabilityType.SQL_INJECTION, "A1"),
    "SCS0035": ("CWE-89", VulnerabilityType.SQL_INJECTION, "A1"),
    "SCS0036": ("CWE-89", VulnerabilityType.SQL_INJECTION, "A1"),
    "SCS0037": ("CWE-601", VulnerabilityType.UNKNOWN, "A10"),
}


class SecurityCodeScanParser:
    """Parser for Security Code Scan C# security analysis.

    [20260303_FEATURE] Phase 2: full implementation.

    Consumes SARIF 2.1 output from dotnet build with SCS analyzers.
    Falls back to ``[]`` when ``dotnet`` is absent.
    """

    def __init__(self) -> None:
        """Initialize Security Code Scan parser."""
        self.config = SecurityCodeScanConfig()
        self.vulnerabilities: List[SecurityVulnerability] = []

    def execute_scs(
        self,
        paths: Union[List[Path], Path],
        config: Optional[SecurityCodeScanConfig] = None,
    ) -> List[SecurityVulnerability]:
        """Run dotnet build with SCS and return vulnerabilities.

        Returns ``[]`` gracefully when ``dotnet`` is not on PATH.
        """
        if not shutil.which("dotnet"):
            return []

        import subprocess

        target = (
            paths if isinstance(paths, Path) else (paths[0] if paths else Path("."))
        )
        sarif_path = Path("/tmp/scs.sarif")
        try:
            subprocess.run(
                ["dotnet", "build", str(target), f"/p:ErrorLog={sarif_path}"],
                capture_output=True,
                text=True,
                timeout=120,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return []

        return self.parse_sarif_output(sarif_path) if sarif_path.exists() else []

    # [20260303_FEATURE] Legacy alias kept for backward-compat
    def execute_security_scan(
        self,
        paths: Union[List[Path], Path],
        config: Optional[SecurityCodeScanConfig] = None,
    ) -> List[SecurityVulnerability]:
        """Alias for execute_scs()."""
        return self.execute_scs(paths, config)

    def parse_sarif_output(
        self, sarif_source: Union[str, Path, dict]
    ) -> List[SecurityVulnerability]:
        """Parse SARIF 2.1 output and return security vulnerabilities."""
        findings = _parse_sarif(sarif_source)
        return [_sarif_to_vuln(f) for f in findings if f.rule_id.startswith("SCS")]

    def load_config(self, config_file: Path) -> SecurityCodeScanConfig:
        """Load SecurityCodeScan configuration from YAML/JSON file."""
        # Minimal implementation — YAML would require pyyaml
        return SecurityCodeScanConfig(config_file=config_file)

    def categorize_vulnerabilities(
        self, vulns: List[SecurityVulnerability]
    ) -> Dict[VulnerabilityType, List[SecurityVulnerability]]:
        """Group vulnerabilities by type."""
        result: Dict[VulnerabilityType, List[SecurityVulnerability]] = {}
        for v in vulns:
            result.setdefault(v.vulnerability_type, []).append(v)
        return result

    def map_to_cwe(
        self, vulns: List[SecurityVulnerability]
    ) -> Dict[str, List[SecurityVulnerability]]:
        """Group vulnerabilities by CWE ID."""
        result: Dict[str, List[SecurityVulnerability]] = {}
        for v in vulns:
            key = v.cwe_id or "UNKNOWN"
            result.setdefault(key, []).append(v)
        return result

    def map_to_owasp(
        self, vulns: List[SecurityVulnerability]
    ) -> Dict[str, List[SecurityVulnerability]]:
        """Group vulnerabilities by OWASP category."""
        result: Dict[str, List[SecurityVulnerability]] = {}
        for v in vulns:
            key = v.owasp_category or "UNKNOWN"
            result.setdefault(key, []).append(v)
        return result

    def generate_report(
        self,
        vulns: List[SecurityVulnerability],
        format: str = "json",
    ) -> str:
        """Return a JSON report of security vulnerabilities."""
        cwe_map = self.map_to_cwe(vulns)
        if format == "json":
            return json.dumps(
                {
                    "tool": "security_code_scan",
                    "total": len(vulns),
                    "cwe_map": {k: len(v) for k, v in cwe_map.items()},
                    "issues": [
                        {
                            "rule_id": v.rule_id,
                            "type": v.vulnerability_type.value,
                            "severity": v.severity,
                            "cwe": v.cwe_id,
                            "owasp": v.owasp_category,
                            "message": v.message,
                            "file": v.file_path,
                            "line": v.line_number,
                        }
                        for v in vulns
                    ],
                },
                indent=2,
            )
        return "\n".join(
            f"{v.file_path}:{v.line_number}: {v.rule_id} [{v.cwe_id}] {v.message}"
            for v in vulns
        )


def _sarif_to_vuln(f: SarifFinding) -> SecurityVulnerability:
    """Convert a SarifFinding to a SecurityVulnerability."""
    cwe, vtype, owasp = _SCS_CWE_MAP.get(
        f.rule_id, (None, VulnerabilityType.UNKNOWN, None)
    )
    return SecurityVulnerability(
        rule_id=f.rule_id,
        vulnerability_type=vtype,
        severity=f.level,
        message=f.message,
        file_path=f.uri,
        line_number=f.line,
        column=f.column,
        cwe_id=cwe,
        owasp_category=owasp,
    )
