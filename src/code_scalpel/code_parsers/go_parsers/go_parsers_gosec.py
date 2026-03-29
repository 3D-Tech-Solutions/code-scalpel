#!/usr/bin/env python3
"""Gosec Go security parser - Go security vulnerability detection.

[20260303_FEATURE] Phase 2: full implementation replacing NotImplementedError stubs.
Phase 1 data structures retained; Phase 2 adds execution + parsing logic.

Reference: https://github.com/securego/gosec
Command: gosec -fmt=json ./...
Output: {"Golang gosec": {"Issues": [...], "Stats": {...}}}
"""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Union


class VulnerabilityType(Enum):
    """Security vulnerability types detected by gosec."""

    SQL_INJECTION = "sql_injection"
    HARDCODED_CREDENTIALS = "hardcoded_credentials"
    WEAK_CRYPTOGRAPHY = "weak_cryptography"
    UNSAFE_EXEC = "unsafe_exec"
    RACE_CONDITION = "race_condition"
    INSECURE_RAND = "insecure_rand"
    PATH_TRAVERSAL = "path_traversal"
    INSECURE_TAINT = "insecure_taint"
    BUFFER_OVERFLOW = "buffer_overflow"
    UNSAFE_POINTER = "unsafe_pointer"
    UNKNOWN = "unknown"


@dataclass
class SecurityIssue:
    """Represents a security issue found by gosec."""

    rule_id: str
    severity: str
    confidence: str
    vulnerability_type: VulnerabilityType
    message: str
    code: str
    file_path: str
    line: int
    column: int
    cwe_id: Optional[str] = None


@dataclass
class GosecStats:
    """gosec scan statistics."""

    files: int = 0
    lines: int = 0
    nosec: int = 0
    found: int = 0


@dataclass
class GosecConfig:
    """Gosec configuration for analysis."""

    gosec_version: str = "2.18.0"
    config_file: Optional[Path] = None
    exclude_rules: List[str] = field(default_factory=list)
    include_rules: List[str] = field(default_factory=list)


# gosec rule ID prefix → VulnerabilityType mapping (partial)
_RULE_TYPE_MAP: Dict[str, VulnerabilityType] = {
    "G101": VulnerabilityType.HARDCODED_CREDENTIALS,
    "G102": VulnerabilityType.INSECURE_TAINT,
    "G103": VulnerabilityType.UNSAFE_POINTER,
    "G104": VulnerabilityType.UNKNOWN,
    "G106": VulnerabilityType.WEAK_CRYPTOGRAPHY,
    "G107": VulnerabilityType.INSECURE_TAINT,
    "G108": VulnerabilityType.INSECURE_TAINT,
    "G109": VulnerabilityType.BUFFER_OVERFLOW,
    "G110": VulnerabilityType.BUFFER_OVERFLOW,
    "G111": VulnerabilityType.PATH_TRAVERSAL,
    "G112": VulnerabilityType.INSECURE_TAINT,
    "G113": VulnerabilityType.INSECURE_TAINT,
    "G114": VulnerabilityType.INSECURE_TAINT,
    "G115": VulnerabilityType.BUFFER_OVERFLOW,
    "G201": VulnerabilityType.SQL_INJECTION,
    "G202": VulnerabilityType.SQL_INJECTION,
    "G203": VulnerabilityType.INSECURE_TAINT,
    "G204": VulnerabilityType.UNSAFE_EXEC,
    "G301": VulnerabilityType.INSECURE_TAINT,
    "G302": VulnerabilityType.INSECURE_TAINT,
    "G303": VulnerabilityType.INSECURE_TAINT,
    "G304": VulnerabilityType.PATH_TRAVERSAL,
    "G305": VulnerabilityType.PATH_TRAVERSAL,
    "G306": VulnerabilityType.INSECURE_TAINT,
    "G307": VulnerabilityType.INSECURE_TAINT,
    "G401": VulnerabilityType.WEAK_CRYPTOGRAPHY,
    "G402": VulnerabilityType.WEAK_CRYPTOGRAPHY,
    "G403": VulnerabilityType.WEAK_CRYPTOGRAPHY,
    "G404": VulnerabilityType.INSECURE_RAND,
    "G405": VulnerabilityType.WEAK_CRYPTOGRAPHY,
    "G406": VulnerabilityType.WEAK_CRYPTOGRAPHY,
    "G501": VulnerabilityType.WEAK_CRYPTOGRAPHY,
    "G502": VulnerabilityType.WEAK_CRYPTOGRAPHY,
    "G503": VulnerabilityType.WEAK_CRYPTOGRAPHY,
    "G504": VulnerabilityType.WEAK_CRYPTOGRAPHY,
    "G505": VulnerabilityType.WEAK_CRYPTOGRAPHY,
    "G506": VulnerabilityType.WEAK_CRYPTOGRAPHY,
    "G601": VulnerabilityType.RACE_CONDITION,
    "G602": VulnerabilityType.RACE_CONDITION,
}


class GosecParser:
    """Parser for Gosec Go security vulnerability detection.

    [20260303_FEATURE] Phase 2: full implementation.

    Scans Go code for security vulnerabilities including SQL injection,
    weak cryptography, hardcoded credentials, and more.
    Falls back to ``[]`` when ``gosec`` is not on PATH.
    """

    def __init__(self) -> None:
        """Initialize Gosec parser."""
        self.config = GosecConfig()
        self.issues: List[SecurityIssue] = []

    def execute_gosec(
        self,
        paths: Union[List[Path], Path, str],
        config: Optional[GosecConfig] = None,
    ) -> List[SecurityIssue]:
        """Run ``gosec -fmt=json`` and return security issues.

        Returns ``[]`` gracefully when ``gosec`` is not on PATH.
        """
        if not shutil.which("gosec"):
            return []

        target = (
            str(paths)
            if not isinstance(paths, list)
            else " ".join(str(p) for p in paths)
        )
        cmd = ["gosec", "-fmt=json", target]
        if config and config.exclude_rules:
            cmd += ["-exclude=" + ",".join(config.exclude_rules)]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            return self.parse_json_output(result.stdout)
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return []

    def parse_json_output(self, output: str) -> List[SecurityIssue]:
        """Parse ``gosec -fmt=json`` stdout.

        [20260303_FEATURE] Handles the gosec JSON output format.

        Args:
            output: JSON string from gosec (stdout or file content).
        """
        if not output or not output.strip():
            return []
        try:
            data = json.loads(output)
        except json.JSONDecodeError:
            return []

        # Top-level may be {"Golang gosec": {...}} or directly {"Issues": [...]}
        if "Golang gosec" in data:
            inner = data["Golang gosec"]
        else:
            inner = data

        issues: List[SecurityIssue] = []
        for item in inner.get("Issues", []):
            rule_id = item.get("rule_id", "")
            vtype = _RULE_TYPE_MAP.get(rule_id, VulnerabilityType.UNKNOWN)
            # CWE info is nested: {"id": "89", "url": "..."}
            cwe_data = item.get("cwe", {})
            cwe_id = f"CWE-{cwe_data['id']}" if cwe_data.get("id") else None
            try:
                line_val = int(item.get("line", 0))
            except (ValueError, TypeError):
                line_val = 0
            # column may be int or str
            try:
                col_val = int(item.get("column", 0))
            except (ValueError, TypeError):
                col_val = 0
            issues.append(
                SecurityIssue(
                    rule_id=rule_id,
                    severity=item.get("severity", "MEDIUM"),
                    confidence=item.get("confidence", "MEDIUM"),
                    vulnerability_type=vtype,
                    message=item.get("details", ""),
                    code=item.get("code", ""),
                    file_path=item.get("file", ""),
                    line=line_val,
                    column=col_val,
                    cwe_id=cwe_id,
                )
            )
        return issues

    # Alias for backward compatibility
    def parse_json_report(self, report_path: Union[str, Path]) -> List[SecurityIssue]:
        """Parse a pre-saved gosec JSON report file."""
        try:
            content = Path(report_path).read_text(encoding="utf-8")
            return self.parse_json_output(content)
        except OSError:
            return []

    def load_config(self, config_file: Path) -> GosecConfig:
        """Load gosec configuration file."""
        return GosecConfig(config_file=config_file)

    def map_to_cwe(self, issues: List[SecurityIssue]) -> Dict[str, List[SecurityIssue]]:
        """Group issues by CWE ID (from the ``cwe.id`` field).

        [20260303_FEATURE] Uses the cwe_id populated during parse_json_output.
        """
        result: Dict[str, List[SecurityIssue]] = {}
        for issue in issues:
            key = issue.cwe_id or "UNKNOWN"
            result.setdefault(key, []).append(issue)
        return result

    def categorize_by_severity(
        self, issues: List[SecurityIssue]
    ) -> Dict[str, List[SecurityIssue]]:
        """Group issues by severity (HIGH, MEDIUM, LOW)."""
        result: Dict[str, List[SecurityIssue]] = {}
        for issue in issues:
            result.setdefault(issue.severity.upper(), []).append(issue)
        return result

    def categorize_vulnerabilities(
        self, issues: List[SecurityIssue]
    ) -> Dict[VulnerabilityType, List[SecurityIssue]]:
        """Group issues by VulnerabilityType enum."""
        result: Dict[VulnerabilityType, List[SecurityIssue]] = {}
        for issue in issues:
            result.setdefault(issue.vulnerability_type, []).append(issue)
        return result

    def filter_by_severity(
        self,
        issues: List[SecurityIssue],
        min_severity: str,
    ) -> List[SecurityIssue]:
        """Filter to issues with severity ≥ *min_severity*."""
        order = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
        threshold = order.get(min_severity.upper(), 0)
        return [i for i in issues if order.get(i.severity.upper(), 0) >= threshold]

    def get_security_stats(self, output: str) -> GosecStats:
        """Extract scan statistics from gosec JSON output.

        [20260303_FEATURE] Returns GosecStats from the Stats block.
        """
        try:
            data = json.loads(output)
        except (json.JSONDecodeError, TypeError):
            return GosecStats()
        inner = data.get("Golang gosec", data)
        stats = inner.get("Stats", {})
        return GosecStats(
            files=stats.get("files", 0),
            lines=stats.get("lines", 0),
            nosec=stats.get("nosec", 0),
            found=stats.get("found", 0),
        )

    def generate_report(self, issues: List[SecurityIssue], format: str = "json") -> str:
        """Return a JSON or text security report."""
        cwe_map = self.map_to_cwe(issues)
        if format == "json":
            return json.dumps(
                {
                    "tool": "gosec",
                    "total": len(issues),
                    "cwe_map": {k: len(v) for k, v in cwe_map.items()},
                    "by_severity": {
                        k: len(v)
                        for k, v in self.categorize_by_severity(issues).items()
                    },
                    "issues": [
                        {
                            "rule_id": i.rule_id,
                            "severity": i.severity,
                            "confidence": i.confidence,
                            "type": i.vulnerability_type.value,
                            "cwe": i.cwe_id,
                            "message": i.message,
                            "file": i.file_path,
                            "line": i.line,
                        }
                        for i in issues
                    ],
                },
                indent=2,
            )
        return "\n".join(
            f"{i.file_path}:{i.line}: [{i.rule_id}] {i.severity} - {i.message}"
            for i in issues
        )

