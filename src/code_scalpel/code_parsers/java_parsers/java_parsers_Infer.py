#!/usr/bin/env python3
"""
Facebook Infer Parser - Static analyzer for Java, C, C++, Objective-C.

Parses Infer JSON output to extract bugs and issues.
Infer finds null pointer exceptions, resource leaks, and more.

Reference: https://fbinfer.com/
Command: infer run -- javac *.java

"""

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class InferIssue:
    """Represents an issue found by Facebook Infer."""

    file: str
    line: int
    column: int
    bug_type: str  # e.g., "NULL_DEREFERENCE", "RESOURCE_LEAK"
    severity: str  # "ERROR", "WARNING", "INFO"
    qualifier: str  # Detailed message
    procedure: str  # Method name
    bug_trace: list[dict]  # Trace of the bug


class InferParser:
    """
    Parser for Facebook Infer static analysis.

    Infer is a static analysis tool that finds bugs in Java, C, C++,
    and Objective-C. It's particularly good at finding:
    - Null pointer dereferences
    - Resource leaks
    - Thread safety violations
    - Security vulnerabilities
    """

    # Common Infer bug types
    BUG_TYPES = {
        "NULL_DEREFERENCE": {
            "severity": "ERROR",
            "description": "Null pointer dereference",
        },
        "RESOURCE_LEAK": {"severity": "ERROR", "description": "Resource leak"},
        "THREAD_SAFETY_violation": {
            "severity": "ERROR",
            "description": "Thread safety violation",
        },
        "DEADLOCK": {"severity": "ERROR", "description": "Potential deadlock"},
        "USE_AFTER_FREE": {"severity": "ERROR", "description": "Use after free"},
        "BUFFER_OVERRUN": {"severity": "ERROR", "description": "Buffer overrun"},
        "UNINITIALIZED_VALUE": {
            "severity": "WARNING",
            "description": "Uninitialized value",
        },
        "ERADICATE_NULLABLE_DEREFERENCE": {
            "severity": "ERROR",
            "description": "Nullable dereference",
        },
    }

    def __init__(self, infer_out_dir: str | None = None):
        """
        Initialize Infer parser.

        Args:
            infer_out_dir: Path to infer-out directory
        """
        self.infer_out_dir = infer_out_dir or "infer-out"
        self.language = "java"

    def parse(self, source_path: str | None = None) -> list[InferIssue]:
        """
        Parse Infer results from report.json.

        Args:
            source_path: Optional source path (if running infer)

        Returns:
            List of InferIssue objects
        """
        report_path = Path(self.infer_out_dir) / "report.json"
        if report_path.exists():
            return self.parse_json(report_path.read_text())
        return []

    def run_infer(self, compile_command: list[str]) -> str | None:
        """
        Run Infer analysis.

        Args:
            compile_command: Compilation command (e.g., ["javac", "*.java"])

        Returns:
            Path to results or None
        """
        try:
            cmd = ["infer", "run", "--"] + compile_command
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
            )
            if result.returncode == 0:
                return self.infer_out_dir
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            print(f"Infer error: {e}")
        return None

    def parse_json(self, json_content: str) -> list[InferIssue]:
        """
        Parse Infer report.json content.

        Args:
            json_content: JSON string from report.json

        Returns:
            List of issues
        """
        issues = []
        try:
            report = json.loads(json_content)
            for bug in report:
                issues.append(
                    InferIssue(
                        file=bug.get("file", ""),
                        line=bug.get("line", 0),
                        column=bug.get("column", 0),
                        bug_type=bug.get("bug_type", ""),
                        severity=bug.get("severity", "ERROR"),
                        qualifier=bug.get("qualifier", ""),
                        procedure=bug.get("procedure", ""),
                        bug_trace=bug.get("bug_trace", []),
                    )
                )
        except json.JSONDecodeError as e:
            print(f"JSON parse error: {e}")
        return issues

    def get_null_dereferences(self, issues: list[InferIssue]) -> list[InferIssue]:
        """
        Filter for null dereference issues.

        Args:
            issues: List of all issues

        Returns:
            List of null dereference issues
        """
        return [i for i in issues if "NULL" in i.bug_type.upper()]

    def get_resource_leaks(self, issues: list[InferIssue]) -> list[InferIssue]:
        """
        Filter for resource leak issues.

        Args:
            issues: List of all issues

        Returns:
            List of resource leak issues
        """
        return [i for i in issues if "RESOURCE_LEAK" in i.bug_type.upper()]
