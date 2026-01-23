#!/usr/bin/env python3
"""
SpotBugs Java Parser - Static analysis to find bugs in Java.
Parses SpotBugs XML output to extract bug patterns.
SpotBugs is the successor to FindBugs.
Reference: https://spotbugs.github.io/
Command: spotbugs -textui -xml -output results.xml classes/
"""

import subprocess
from dataclasses import dataclass
from pathlib import Path

from defusedxml import ElementTree as ET


@dataclass
class SpotBug:
    """Represents a SpotBugs finding."""

    file: str
    line: int
    bug_type: str  # Bug pattern name
    bug_pattern: str  # Full pattern code (e.g., "NP_NULL_ON_SOME_PATH")
    category: str  # Category (e.g., "CORRECTNESS", "PERFORMANCE")
    priority: int  # 1=High, 2=Normal, 3=Low
    rank: int  # Bug rank (1-20, lower is more severe)
    message: str
    class_name: str | None = None
    method_name: str | None = None


class SpotBugsParser:
    """
    Parser for SpotBugs Java static analysis.

    SpotBugs looks for more than 400 bug patterns including:
    - Correctness bugs (null pointer, bad practice)
    - Bad practice (equals/hashCode, serialization)
    - Dodgy code (redundant checks, dead stores)
    - Performance (inefficient code patterns)
    - Multithreaded correctness (synchronization issues)
    - Malicious code vulnerability
    """

    # SpotBugs categories
    CATEGORIES = {
        "CORRECTNESS": "Likely bugs",
        "BAD_PRACTICE": "Violations of good practice",
        "STYLE": "Dodgy code",
        "PERFORMANCE": "Performance issues",
        "MALICIOUS_CODE": "Malicious code vulnerabilities",
        "MT_CORRECTNESS": "Multithreaded correctness",
        "I18N": "Internationalization issues",
        "SECURITY": "Security vulnerabilities",
    }

    def __init__(
        self,
        spotbugs_bin: str | None = None,
        include_filter: str | None = None,
        exclude_filter: str | None = None,
    ):
        """
        Initialize SpotBugs parser.

        Args:
            spotbugs_bin: Path to SpotBugs binary
            include_filter: Path to include filter XML
            exclude_filter: Path to exclude filter XML
        """
        self.spotbugs_bin = spotbugs_bin or "spotbugs"
        self.include_filter = include_filter
        self.exclude_filter = exclude_filter
        self.language = "java"

    def parse(self, class_path: str) -> list[SpotBug]:
        """
        Run SpotBugs and parse bugs.

        Args:
            class_path: Path to compiled classes directory or JAR

        Returns:
            List of SpotBug objects
        """
        xml_output = self.run_spotbugs(class_path)
        if xml_output:
            return self.parse_xml(xml_output)
        return []

    def run_spotbugs(self, class_path: str) -> str | None:
        """
        Run SpotBugs analysis.

        Args:
            class_path: Path to compiled classes

        Returns:
            XML output string or None
        """
        try:
            cmd = [
                self.spotbugs_bin,
                "-textui",
                "-xml",
                class_path,
            ]
            if self.include_filter:
                cmd.extend(["-include", self.include_filter])
            if self.exclude_filter:
                cmd.extend(["-exclude", self.exclude_filter])

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
            )
            return result.stdout
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            print(f"SpotBugs error: {e}")
            return None

    def parse_xml(self, xml_content: str) -> list[SpotBug]:
        """
        Parse SpotBugs XML output.

        Args:
            xml_content: XML string from SpotBugs

        Returns:
            List of bugs
        """
        bugs = []
        try:
            root = ET.fromstring(xml_content)
            for bug_instance in root.findall(".//BugInstance"):
                bug_type = bug_instance.get("type", "")
                category = bug_instance.get("category", "")
                priority = int(bug_instance.get("priority", 2))
                rank = int(bug_instance.get("rank", 10))

                # Get source location
                source_line = bug_instance.find(".//SourceLine[@primary='true']")
                if source_line is None:
                    source_line = bug_instance.find(".//SourceLine")

                file_path = ""
                line_num = 0
                if source_line is not None:
                    file_path = source_line.get("sourcepath", "")
                    line_num = int(source_line.get("start", 0))

                # Get class and method
                class_elem = bug_instance.find(".//Class[@primary='true']")
                if class_elem is None:
                    class_elem = bug_instance.find(".//Class")
                method_elem = bug_instance.find(".//Method[@primary='true']")
                if method_elem is None:
                    method_elem = bug_instance.find(".//Method")

                class_name = class_elem.get("classname") if class_elem is not None else None
                method_name = method_elem.get("name") if method_elem is not None else None

                # Get message
                long_message = bug_instance.find("LongMessage")
                short_message = bug_instance.find("ShortMessage")
                message = ""
                if long_message is not None and long_message.text:
                    message = long_message.text
                elif short_message is not None and short_message.text:
                    message = short_message.text

                bugs.append(
                    SpotBug(
                        file=file_path,
                        line=line_num,
                        bug_type=bug_type,
                        bug_pattern=bug_type,
                        category=category,
                        priority=priority,
                        rank=rank,
                        message=message,
                        class_name=class_name,
                        method_name=method_name,
                    )
                )
        except ET.ParseError as e:
            print(f"XML parse error: {e}")
        return bugs

    def parse_file(self, xml_file: str) -> list[SpotBug]:
        """
        Parse SpotBugs XML output from file.

        Args:
            xml_file: Path to XML file

        Returns:
            List of bugs
        """
        content = Path(xml_file).read_text()
        return self.parse_xml(content)

    def get_high_rank_bugs(self, bugs: list[SpotBug], max_rank: int = 9) -> list[SpotBug]:
        """
        Filter for high-rank (scariest) bugs.

        Args:
            bugs: List of all bugs
            max_rank: Maximum rank to include (1-20, lower is scarier)

        Returns:
            List of high-rank bugs
        """
        return [b for b in bugs if b.rank <= max_rank]

    def get_by_category(self, bugs: list[SpotBug], category: str) -> list[SpotBug]:
        """
        Filter bugs by category.

        Args:
            bugs: List of all bugs
            category: Category to filter by

        Returns:
            List of filtered bugs
        """
        return [b for b in bugs if b.category == category]

    def get_security_bugs(self, bugs: list[SpotBug]) -> list[SpotBug]:
        """
        Filter for security-related bugs.

        Args:
            bugs: List of all bugs

        Returns:
            List of security bugs
        """
        return [b for b in bugs if b.category in ("SECURITY", "MALICIOUS_CODE")]
