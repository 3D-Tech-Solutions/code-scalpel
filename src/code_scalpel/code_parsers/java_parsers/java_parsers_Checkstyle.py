#!/usr/bin/env python3
"""
Checkstyle Java Parser - Java code style checker.

Parses Checkstyle XML output to extract code style violations.
Checkstyle enforces coding standards for Java code.

Reference: https://checkstyle.org/
Command: java -jar checkstyle.jar -c /config.xml -f xml src/

"""

import subprocess
from dataclasses import dataclass
from pathlib import Path

from defusedxml import ElementTree as ET


@dataclass
class CheckstyleViolation:
    """Represents a single Checkstyle violation."""

    file: str
    line: int
    column: int | None
    severity: str  # "error", "warning", "info"
    message: str
    source: str  # Checkstyle rule name


class CheckstyleParser:
    """
    Parser for Checkstyle Java code style analysis.

    Checkstyle checks Java source code for adherence to a coding standard.
    This parser runs Checkstyle and parses the XML output.
    """

    def __init__(
        self,
        checkstyle_jar: str | None = None,
        config_file: str | None = None,
    ):
        """
        Initialize Checkstyle parser.

        Args:
            checkstyle_jar: Path to checkstyle JAR file
            config_file: Path to checkstyle configuration XML
        """
        self.checkstyle_jar = checkstyle_jar or "checkstyle.jar"
        self.config_file = config_file or "google_checks.xml"
        self.language = "java"

    def parse(self, source_path: str) -> list[CheckstyleViolation]:
        """
        Run Checkstyle and parse violations.

        Args:
            source_path: Path to Java source file or directory

        Returns:
            List of CheckstyleViolation objects
        """
        xml_output = self.run_checkstyle(source_path)
        if xml_output:
            return self.parse_xml(xml_output)
        return []

    def run_checkstyle(self, source_path: str) -> str | None:
        """
        Run Checkstyle on source path.

        Args:
            source_path: Path to Java source

        Returns:
            XML output string or None if failed
        """
        try:
            result = subprocess.run(
                [
                    "java",
                    "-jar",
                    self.checkstyle_jar,
                    "-c",
                    self.config_file,
                    "-f",
                    "xml",
                    source_path,
                ],
                capture_output=True,
                text=True,
                timeout=120,
            )
            return result.stdout
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            print(f"Checkstyle error: {e}")
            return None

    def parse_xml(self, xml_content: str) -> list[CheckstyleViolation]:
        """
        Parse Checkstyle XML output.

        Args:
            xml_content: XML string from Checkstyle

        Returns:
            List of violations
        """
        violations = []
        try:
            root = ET.fromstring(xml_content)
            for file_elem in root.findall(".//file"):
                filename = file_elem.get("name", "")
                for error in file_elem.findall("error"):
                    violations.append(
                        CheckstyleViolation(
                            file=filename,
                            line=int(error.get("line", 0)),
                            column=(int(error.get("column", 0)) if error.get("column") else None),
                            severity=error.get("severity", "warning"),
                            message=error.get("message", ""),
                            source=error.get("source", ""),
                        )
                    )
        except ET.ParseError as e:
            print(f"XML parse error: {e}")
        return violations

    def parse_file(self, xml_file: str) -> list[CheckstyleViolation]:
        """
        Parse Checkstyle XML output from file.

        Args:
            xml_file: Path to XML output file

        Returns:
            List of violations
        """
        content = Path(xml_file).read_text()
        return self.parse_xml(content)
