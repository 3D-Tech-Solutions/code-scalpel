#!/usr/bin/env python3
"""
Find Security Bugs Parser - Security-focused SpotBugs plugin.

Parses Find Security Bugs XML output for security vulnerabilities.
Find Security Bugs is a SpotBugs plugin for security audits.

Reference: https://find-sec-bugs.github.io/
Command: spotbugs -pluginList findsecbugs-plugin.jar -xml -output results.xml classes/

"""

from dataclasses import dataclass
from pathlib import Path

from defusedxml import ElementTree as ET


@dataclass
class SecurityBug:
    """Represents a security vulnerability found by Find Security Bugs."""

    file: str
    line: int
    bug_type: str  # e.g., "SQL_INJECTION", "XSS_SERVLET"
    category: str  # e.g., "SECURITY", "MALICIOUS_CODE"
    priority: int  # 1=High, 2=Medium, 3=Low
    message: str
    cwe_id: int | None = None  # Common Weakness Enumeration ID
    class_name: str | None = None
    method_name: str | None = None


class FindSecBugsParser:
    """
    Parser for Find Security Bugs security analysis.

    Find Security Bugs detects 141+ security-related bug patterns including:
    - Injection flaws (SQL, LDAP, XPath, OS Command)
    - Cross-Site Scripting (XSS)
    - Cryptographic weaknesses
    - Path traversal
    - XML External Entity (XXE)
    """

    # Security bug categories
    SECURITY_CATEGORIES = {
        "SQL_INJECTION": {"cwe": 89, "severity": "HIGH"},
        "XSS_SERVLET": {"cwe": 79, "severity": "HIGH"},
        "PATH_TRAVERSAL_IN": {"cwe": 22, "severity": "HIGH"},
        "COMMAND_INJECTION": {"cwe": 78, "severity": "CRITICAL"},
        "XXE_SAXPARSER": {"cwe": 611, "severity": "HIGH"},
        "WEAK_RANDOM": {"cwe": 330, "severity": "MEDIUM"},
        "HARD_CODE_PASSWORD": {"cwe": 798, "severity": "HIGH"},
        "INSECURE_COOKIE": {"cwe": 614, "severity": "MEDIUM"},
        "CSRF": {"cwe": 352, "severity": "HIGH"},
        "LDAP_INJECTION": {"cwe": 90, "severity": "HIGH"},
    }

    def __init__(self):
        """Initialize Find Security Bugs parser."""
        self.language = "java"

    def parse(self, xml_file: str) -> list[SecurityBug]:
        """
        Parse Find Security Bugs XML output.

        Args:
            xml_file: Path to XML output file

        Returns:
            List of SecurityBug objects
        """
        content = Path(xml_file).read_text()
        return self.parse_xml(content)

    def parse_xml(self, xml_content: str) -> list[SecurityBug]:
        """
        Parse Find Security Bugs XML content.

        Args:
            xml_content: XML string

        Returns:
            List of security bugs
        """
        bugs = []
        try:
            root = ET.fromstring(xml_content)
            for bug_instance in root.findall(".//BugInstance"):
                bug_type = bug_instance.get("type", "")
                category = bug_instance.get("category", "")
                priority = int(bug_instance.get("priority", 3))

                # Get source location
                source_line = bug_instance.find(".//SourceLine")
                file_path = ""
                line_num = 0
                if source_line is not None:
                    file_path = source_line.get("sourcepath", "")
                    line_num = int(source_line.get("start", 0))

                # Get class and method
                class_elem = bug_instance.find(".//Class")
                method_elem = bug_instance.find(".//Method")
                class_name = class_elem.get("classname") if class_elem is not None else None
                method_name = method_elem.get("name") if method_elem is not None else None

                # Get message
                long_message = bug_instance.find("LongMessage")
                message = long_message.text if long_message is not None else bug_type

                # Get CWE if available
                cwe_id = self.SECURITY_CATEGORIES.get(bug_type, {}).get("cwe")

                bugs.append(
                    SecurityBug(
                        file=file_path,
                        line=line_num,
                        bug_type=bug_type,
                        category=category,
                        priority=priority,
                        message=message or "",
                        cwe_id=cwe_id,
                        class_name=class_name,
                        method_name=method_name,
                    )
                )
        except ET.ParseError as e:
            print(f"XML parse error: {e}")
        return bugs

    def get_high_severity_bugs(self, bugs: list[SecurityBug]) -> list[SecurityBug]:
        """
        Filter for high severity (priority 1) bugs.

        Args:
            bugs: List of all bugs

        Returns:
            List of high severity bugs
        """
        return [b for b in bugs if b.priority == 1]

    def get_bugs_by_cwe(self, bugs: list[SecurityBug], cwe_id: int) -> list[SecurityBug]:
        """
        Filter bugs by CWE ID.

        Args:
            bugs: List of all bugs
            cwe_id: CWE ID to filter by

        Returns:
            List of bugs matching CWE
        """
        return [b for b in bugs if b.cwe_id == cwe_id]
