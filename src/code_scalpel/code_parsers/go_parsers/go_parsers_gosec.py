#!/usr/bin/env python3
# Phase 1: Define data structures and class skeleton for Gosec parser
# This module sets up the framework for integrating Gosec
# into the code analysis tool. The actual implementation of methods will be
# completed in Phase 2.

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


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
    cwe_id: str | None = None


@dataclass
class GosecConfig:
    """Gosec configuration for analysis."""

    gosec_version: str = "2.18.0"
    config_file: Path | None = None
    exclude_rules: list[str] = field(default_factory=list)
    include_rules: list[str] = field(default_factory=list)


class GosecParser:
    """
    Parser for Gosec Go security vulnerability detection.

    Scans Go code for security vulnerabilities and weaknesses
    including injection attacks, weak cryptography, and unsafe operations.
    """

    def __init__(self):
        """Initialize Gosec parser."""
        self.config = GosecConfig()
        self.issues: list[SecurityIssue] = []

    def execute_gosec(self, paths: list[Path], config: GosecConfig | None = None) -> list[SecurityIssue]:
        raise NotImplementedError("Phase 2: Gosec execution")

    def parse_json_report(self, report_path: Path) -> list[SecurityIssue]:
        raise NotImplementedError("Phase 2: JSON report parsing")

    def load_config(self, config_file: Path) -> GosecConfig:
        raise NotImplementedError("Phase 2: Config loading")

    def categorize_vulnerabilities(self, issues: list[SecurityIssue]) -> dict[VulnerabilityType, list[SecurityIssue]]:
        raise NotImplementedError("Phase 2: Vulnerability categorization")

    def filter_by_severity(self, issues: list[SecurityIssue], min_severity: str) -> list[SecurityIssue]:
        raise NotImplementedError("Phase 2: Severity filtering")

    def map_to_cwe(self, issues: list[SecurityIssue]) -> dict[str, list[SecurityIssue]]:
        raise NotImplementedError("Phase 2: CWE mapping")

    def generate_report(self, issues: list[SecurityIssue], format: str = "json") -> str:
        raise NotImplementedError("Phase 2: Report generation")
