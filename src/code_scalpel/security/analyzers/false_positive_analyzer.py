"""
False Positive Analyzer - Pro Tier Feature.

[20251226_FEATURE] v3.2.9 - Pro tier false positive reduction.

This module identifies and filters false positive security findings:
- Test code detection (pytest, unittest files)
- Documentation/example code
- Dead code analysis
- Context-based filtering
"""

import ast
import logging
from typing import Any

logger = logging.getLogger(__name__)


class FalsePositiveAnalyzer:
    """
    Analyzes security findings for false positives.

    Pro tier feature that reduces noise by filtering out findings in:
    - Test code
    - Example/documentation code
    - Dead/unreachable code
    - Known safe patterns
    """

    def __init__(self):
        """Initialize the false positive analyzer."""
        pass

    def is_test_code(self, code: str, filename: str = "") -> bool:
        """
        Detect if code is a test file.

        Args:
            code: Python source code
            filename: Optional filename for path-based detection

        Returns:
            True if this appears to be test code
        """
        # Check filename
        if filename:
            test_indicators = [
                "test_",
                "_test.py",
                "/tests/",
                "\\tests\\",
                "pytest",
                "unittest",
            ]
            if any(indicator in filename.lower() for indicator in test_indicators):
                return True

        # Check code content
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return False

        # Look for test frameworks
        test_imports = {"pytest", "unittest", "mock", "nose"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if any(test_pkg in alias.name for test_pkg in test_imports):
                        return True
            elif isinstance(node, ast.ImportFrom):
                if node.module and any(test_pkg in node.module for test_pkg in test_imports):
                    return True

        # Look for test function patterns
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                if node.name.startswith("test_") or "test" in node.name.lower():
                    return True
                # Check for unittest method names
                if node.name in ["setUp", "tearDown", "setUpClass", "tearDownClass"]:
                    return True

        return False

    def is_example_code(self, code: str, filename: str = "") -> bool:
        """
        Detect if code is example/documentation code.

        Args:
            code: Python source code
            filename: Optional filename

        Returns:
            True if this appears to be example code
        """
        # Check filename
        if filename:
            example_indicators = [
                "example",
                "demo",
                "sample",
                "docs/",
                "documentation/",
            ]
            if any(indicator in filename.lower() for indicator in example_indicators):
                return True

        # Check for docstring-heavy code (documentation)
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return False

        docstring_count = 0
        code_count = 0

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.Module)):
                docstring = ast.get_docstring(node)
                if docstring:
                    docstring_count += len(docstring)
            elif isinstance(node, ast.stmt):
                code_count += 1

        # If docstrings are >50% of content, likely documentation
        if code_count > 0:
            ratio = docstring_count / (code_count * 50)  # Approximate ratio
            if ratio > 0.5:
                return True

        return False

    def analyze_false_positives(
        self, vulnerabilities: list[dict[str, Any]], code: str, filename: str = ""
    ) -> dict[str, Any]:
        """
        Analyze vulnerabilities for false positives.

        Args:
            vulnerabilities: List of detected vulnerabilities
            code: Source code being analyzed
            filename: Optional filename

        Returns:
            Analysis dict with false positive info
        """
        if not vulnerabilities:
            return {
                "total_findings": 0,
                "false_positives": 0,
                "true_positives": len(vulnerabilities),
                "filtered_vulnerabilities": vulnerabilities,
                "reasons": [],
            }

        is_test = self.is_test_code(code, filename)
        is_example = self.is_example_code(code, filename)

        false_positive_count = 0
        reasons = []

        if is_test:
            false_positive_count = len(vulnerabilities)
            reasons.append(f"Test code: All {len(vulnerabilities)} findings suppressed")
            filtered = []  # Remove all from test code
        elif is_example:
            false_positive_count = len(vulnerabilities)
            reasons.append(f"Example code: All {len(vulnerabilities)} findings suppressed")
            filtered = []  # Remove all from example code
        else:
            # Keep all findings for production code
            filtered = vulnerabilities

        return {
            "total_findings": len(vulnerabilities),
            "false_positives": false_positive_count,
            "true_positives": len(filtered),
            "filtered_vulnerabilities": filtered,
            "reasons": reasons,
            "is_test_code": is_test,
            "is_example_code": is_example,
        }

    def filter_by_pattern(self, vulnerabilities: list[dict[str, Any]], code: str) -> list[dict[str, Any]]:
        """
        Filter vulnerabilities by known false positive patterns.

        Args:
            vulnerabilities: List of vulnerabilities
            code: Source code

        Returns:
            Filtered list of vulnerabilities
        """
        filtered = []

        for vuln in vulnerabilities:
            vuln_type = vuln.get("type", "")
            vuln_line = vuln.get("line", 0)

            # Get the line of code
            lines = code.split("\n")
            if 0 < vuln_line <= len(lines):
                line_content = lines[vuln_line - 1]

                # Check for known false positive patterns
                is_false_positive = False

                # Pattern 1: Hardcoded secrets that are obviously examples
                if vuln_type == "Hardcoded Secret":
                    if any(
                        marker in line_content.lower()
                        for marker in [
                            "example",
                            "sample",
                            "test",
                            "dummy",
                            "placeholder",
                            "xxx",
                        ]
                    ):
                        is_false_positive = True

                # Pattern 2: SQL injection with obvious parameterization
                if vuln_type == "SQL Injection":
                    if "?" in line_content or "%s" in line_content:
                        is_false_positive = True

                # Pattern 3: Weak crypto in test/example context
                if vuln_type == "Weak Cryptography":
                    if "test" in line_content.lower() or "example" in line_content.lower():
                        is_false_positive = True

                if not is_false_positive:
                    filtered.append(vuln)
            else:
                # Keep if we can't check the line
                filtered.append(vuln)

        return filtered

    def generate_false_positive_report(self, analysis: dict[str, Any]) -> str:
        """
        Generate a human-readable false positive report.

        Args:
            analysis: Analysis result from analyze_false_positives

        Returns:
            Formatted report string
        """
        total = analysis.get("total_findings", 0)
        fp = analysis.get("false_positives", 0)
        tp = analysis.get("true_positives", 0)
        reasons = analysis.get("reasons", [])

        if total == 0:
            return "No findings to analyze"

        report_parts = [f"False Positive Analysis: {fp}/{total} findings filtered"]

        if reasons:
            report_parts.append("Reasons:")
            for reason in reasons:
                report_parts.append(f"  - {reason}")

        if tp > 0:
            report_parts.append(f"\nRemaining findings: {tp} (requires review)")

        return "\n".join(report_parts)
