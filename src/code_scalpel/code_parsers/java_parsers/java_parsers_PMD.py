#!/usr/bin/env python3
"""
PMD Java Parser - Source code analyzer for Java.
Parses PMD XML output to extract code violations.
PMD finds common programming flaws like unused variables, empty blocks, etc.
Reference: https://pmd.github.io/
Command: pmd check -d src -R rulesets/java/quickstart.xml -f xml -r report.xml
"""

import subprocess
from dataclasses import dataclass
from pathlib import Path

from defusedxml import ElementTree as ET


@dataclass
class PMDViolation:
    """Represents a PMD rule violation."""

    file: str
    begin_line: int
    end_line: int
    begin_column: int
    end_column: int
    rule: str  # Rule name
    ruleset: str  # Ruleset name (e.g., "Best Practices")
    priority: int  # 1-5, lower is more severe
    message: str
    external_info_url: str | None = None


class PMDParser:
    """
    Parser for PMD Java static analysis.

    PMD is an extensible cross-language static code analyzer that finds:
    - Possible bugs (empty try/catch/finally/switch statements)
    - Dead code (unused variables, parameters, methods)
    - Suboptimal code (wasteful String usage)
    - Overcomplicated expressions
    - Duplicate code (CPD - Copy/Paste Detector)
    """

    # PMD priority levels
    PRIORITY_LEVELS = {
        1: "BLOCKER",
        2: "CRITICAL",
        3: "MAJOR",
        4: "MINOR",
        5: "INFO",
    }

    # Common PMD rulesets
    RULESETS = [
        "category/java/bestpractices.xml",
        "category/java/codestyle.xml",
        "category/java/design.xml",
        "category/java/documentation.xml",
        "category/java/errorprone.xml",
        "category/java/multithreading.xml",
        "category/java/performance.xml",
        "category/java/security.xml",
    ]

    def __init__(
        self,
        pmd_bin: str | None = None,
        rulesets: list[str] | None = None,
    ):
        """
        Initialize PMD parser.

        Args:
            pmd_bin: Path to PMD binary
            rulesets: List of rulesets to use
        """
        self.pmd_bin = pmd_bin or "pmd"
        self.rulesets = rulesets or ["rulesets/java/quickstart.xml"]
        self.language = "java"

    def parse(self, source_path: str) -> list[PMDViolation]:
        """
        Run PMD and parse violations.

        Args:
            source_path: Path to Java source

        Returns:
            List of PMDViolation objects
        """
        xml_output = self.run_pmd(source_path)
        if xml_output:
            return self.parse_xml(xml_output)
        return []

    def run_pmd(self, source_path: str) -> str | None:
        """
        Run PMD on source path.

        Args:
            source_path: Path to Java source

        Returns:
            XML output string or None
        """
        try:
            ruleset_arg = ",".join(self.rulesets)
            result = subprocess.run(
                [
                    self.pmd_bin,
                    "check",
                    "-d",
                    source_path,
                    "-R",
                    ruleset_arg,
                    "-f",
                    "xml",
                ],
                capture_output=True,
                text=True,
                timeout=120,
            )
            return result.stdout
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            print(f"PMD error: {e}")
            return None

    def parse_xml(self, xml_content: str) -> list[PMDViolation]:
        """
        Parse PMD XML output.

        Args:
            xml_content: XML string from PMD

        Returns:
            List of violations
        """
        violations = []
        try:
            root = ET.fromstring(xml_content)
            for file_elem in root.findall(".//file"):
                filename = file_elem.get("name", "")
                for violation in file_elem.findall("violation"):
                    violations.append(
                        PMDViolation(
                            file=filename,
                            begin_line=int(violation.get("beginline", 0)),
                            end_line=int(violation.get("endline", 0)),
                            begin_column=int(violation.get("begincolumn", 0)),
                            end_column=int(violation.get("endcolumn", 0)),
                            rule=violation.get("rule", ""),
                            ruleset=violation.get("ruleset", ""),
                            priority=int(violation.get("priority", 3)),
                            message=violation.text.strip() if violation.text else "",
                            external_info_url=violation.get("externalInfoUrl"),
                        )
                    )
        except ET.ParseError as e:
            print(f"XML parse error: {e}")
        return violations

    def parse_file(self, xml_file: str) -> list[PMDViolation]:
        """
        Parse PMD XML output from file.

        Args:
            xml_file: Path to XML file

        Returns:
            List of violations
        """
        content = Path(xml_file).read_text()
        return self.parse_xml(content)

    def get_by_priority(self, violations: list[PMDViolation], max_priority: int = 2) -> list[PMDViolation]:
        """
        Filter violations by priority.

        Args:
            violations: List of all violations
            max_priority: Maximum priority level to include (1-5)

        Returns:
            List of filtered violations
        """
        return [v for v in violations if v.priority <= max_priority]

    def get_by_ruleset(self, violations: list[PMDViolation], ruleset: str) -> list[PMDViolation]:
        """
        Filter violations by ruleset.

        Args:
            violations: List of all violations
            ruleset: Ruleset name to filter by

        Returns:
            List of filtered violations
        """
        return [v for v in violations if ruleset.lower() in v.ruleset.lower()]
