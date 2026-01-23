#!/usr/bin/env python3
"""
Error Prone Java Parser - Google's bug-finding static analyzer.

Parses Error Prone output to extract bug patterns and warnings.
Error Prone is a compile-time static analysis tool.

Reference: https://errorprone.info/
Command: javac -XDcompilePolicy=simple -processorpath error_prone.jar \
         '-Xplugin:ErrorProne' src/*.java

"""

import re
import subprocess
from dataclasses import dataclass


@dataclass
class ErrorProneIssue:
    """Represents an Error Prone finding."""

    file: str
    line: int
    column: int | None
    bug_pattern: str  # e.g., "NullAway", "StringSplitter"
    severity: str  # "ERROR", "WARNING"
    message: str
    suggested_fix: str | None = None


class ErrorProneParser:
    """
    Parser for Error Prone Java static analysis.

    Error Prone is a static analysis tool for Java that catches common
    programming mistakes at compile-time.
    """

    def __init__(
        self,
        error_prone_jar: str | None = None,
        additional_checks: list[str] | None = None,
    ):
        """
        Initialize Error Prone parser.

        Args:
            error_prone_jar: Path to Error Prone JAR
            additional_checks: List of additional bug patterns to enable
        """
        self.error_prone_jar = error_prone_jar or "error_prone_core.jar"
        self.additional_checks = additional_checks or []
        self.language = "java"

        # Pattern: file:line: [BugPattern] message
        self.output_pattern = re.compile(r"^(.+):(\d+):\s*(?:error|warning):\s*\[([^\]]+)\]\s*(.+)$")

    def parse(self, source_path: str) -> list[ErrorProneIssue]:
        """
        Run Error Prone and parse issues.

        Args:
            source_path: Path to Java source

        Returns:
            List of ErrorProneIssue objects
        """
        output = self.run_error_prone(source_path)
        if output:
            return self.parse_output(output)
        return []

    def run_error_prone(self, source_path: str) -> str | None:
        """
        Run Error Prone compilation.

        Args:
            source_path: Path to Java source

        Returns:
            Compiler output or None
        """
        try:
            cmd = [
                "javac",
                "-XDcompilePolicy=simple",
                "-processorpath",
                self.error_prone_jar,
                "-Xplugin:ErrorProne",
                source_path,
            ]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,
            )
            return result.stderr  # Error Prone outputs to stderr
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            print(f"Error Prone error: {e}")
            return None

    def parse_output(self, output: str) -> list[ErrorProneIssue]:
        """
        Parse Error Prone compiler output.

        Args:
            output: Compiler stderr output

        Returns:
            List of issues
        """
        issues = []
        for line in output.splitlines():
            match = self.output_pattern.match(line)
            if match:
                file_path, line_num, bug_pattern, message = match.groups()
                severity = "ERROR" if "error:" in line else "WARNING"
                issues.append(
                    ErrorProneIssue(
                        file=file_path,
                        line=int(line_num),
                        column=None,
                        bug_pattern=bug_pattern,
                        severity=severity,
                        message=message.strip(),
                    )
                )
        return issues

    def get_supported_checks(self) -> list[str]:
        """
        Get list of supported bug patterns.

        Returns:
            List of bug pattern names
        """
        # Common Error Prone checks
        return [
            "NullAway",
            "StringSplitter",
            "MissingOverride",
            "DeadException",
            "EmptyCatch",
            "FallThrough",
            "MissingCasesInEnumSwitch",
            "UnnecessaryParentheses",
            "ReferenceEquality",
            "FloatingPointLiteralPrecision",
        ]
