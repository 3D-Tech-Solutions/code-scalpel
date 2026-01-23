"""
Sanitizer Detector - Pro Tier Feature.

[20251226_FEATURE] v3.2.9 - Pro tier sanitizer recognition.

This module detects sanitization functions that neutralize vulnerabilities:
- HTML escape functions (html.escape, bleach.clean)
- SQL parameterization (parameterized queries)
- Input validation functions
- Path sanitization
- Command escaping
"""

import ast
import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class SanitizerMatch:
    """A detected sanitizer function or pattern."""

    function_name: str  # Name of sanitizer function
    line: int  # Line number where used
    sanitizer_type: str  # "html_escape", "sql_param", "validation", etc.
    confidence: float  # 0.0-1.0
    description: str


class SanitizerDetector:
    """
    Detects sanitization functions in code.

    Pro tier feature that identifies functions and patterns that neutralize
    security vulnerabilities.
    """

    # Known sanitizer functions by type
    HTML_SANITIZERS = {
        "html.escape",
        "bleach.clean",
        "bleach.linkify",
        "markupsafe.escape",
        "cgi.escape",
        "flask.escape",
        "django.utils.html.escape",
        "jinja2.escape",
    }

    SQL_SANITIZERS = {
        "?",  # Parameterized query placeholder
        "%s",  # Python DB-API placeholder
        "execute",  # When used with parameters
    }

    VALIDATION_FUNCTIONS = {
        "validate",
        "sanitize",
        "clean",
        "filter",
        "whitelist",
        "strip_tags",
    }

    PATH_SANITIZERS = {
        "os.path.normpath",
        "os.path.abspath",
        "pathlib.Path",
    }

    COMMAND_SANITIZERS = {
        "shlex.quote",
        "pipes.quote",
    }

    def __init__(self):
        """Initialize the sanitizer detector."""
        pass

    def detect_sanitizers(self, code: str) -> list[SanitizerMatch]:
        """
        Detect all sanitizers in the code.

        Args:
            code: Python source code to analyze

        Returns:
            List of SanitizerMatch objects
        """
        sanitizers = []

        try:
            tree = ast.parse(code)
        except SyntaxError:
            return []

        # Walk the AST looking for sanitizer patterns
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                sanitizer = self._check_call_for_sanitizer(node)
                if sanitizer:
                    sanitizers.append(sanitizer)

            elif isinstance(node, ast.FunctionDef):
                # Check if function name suggests validation/sanitization
                if any(keyword in node.name.lower() for keyword in ["validate", "sanitize", "clean", "escape"]):
                    sanitizers.append(
                        SanitizerMatch(
                            function_name=node.name,
                            line=node.lineno,
                            sanitizer_type="validation",
                            confidence=0.7,
                            description=f"Function '{node.name}' appears to be a validation/sanitization function",
                        )
                    )

        return sanitizers

    def _check_call_for_sanitizer(self, node: ast.Call) -> SanitizerMatch | None:
        """Check if a function call is a sanitizer."""
        func_name = self._get_function_name(node)
        if not func_name:
            return None

        line = node.lineno

        # Check HTML sanitizers
        if any(html_san in func_name for html_san in self.HTML_SANITIZERS):
            return SanitizerMatch(
                function_name=func_name,
                line=line,
                sanitizer_type="html_escape",
                confidence=0.95,
                description=f"HTML escaping function '{func_name}' neutralizes XSS",
            )

        # Check SQL parameterization
        if "execute" in func_name:
            # Check if it has parameters (second argument)
            if len(node.args) >= 2 or any(kw.arg == "params" for kw in node.keywords):
                return SanitizerMatch(
                    function_name=func_name,
                    line=line,
                    sanitizer_type="sql_parameterization",
                    confidence=0.9,
                    description=f"Parameterized SQL query at '{func_name}' prevents SQL injection",
                )

        # Check path sanitizers
        if any(path_san in func_name for path_san in self.PATH_SANITIZERS):
            return SanitizerMatch(
                function_name=func_name,
                line=line,
                sanitizer_type="path_sanitization",
                confidence=0.85,
                description=f"Path normalization '{func_name}' prevents path traversal",
            )

        # Check command sanitizers
        if any(cmd_san in func_name for cmd_san in self.COMMAND_SANITIZERS):
            return SanitizerMatch(
                function_name=func_name,
                line=line,
                sanitizer_type="command_escaping",
                confidence=0.9,
                description=f"Command escaping '{func_name}' prevents command injection",
            )

        # Check validation functions
        if any(val_func in func_name.lower() for val_func in self.VALIDATION_FUNCTIONS):
            return SanitizerMatch(
                function_name=func_name,
                line=line,
                sanitizer_type="validation",
                confidence=0.75,
                description=f"Validation function '{func_name}' may neutralize vulnerabilities",
            )

        return None

    def _get_function_name(self, node: ast.Call) -> str | None:
        """Extract function name from Call node."""
        if isinstance(node.func, ast.Name):
            return node.func.id
        elif isinstance(node.func, ast.Attribute):
            # Handle module.function calls
            parts = []
            current = node.func
            while isinstance(current, ast.Attribute):
                parts.append(current.attr)
                current = current.value
            if isinstance(current, ast.Name):
                parts.append(current.id)
            return ".".join(reversed(parts))
        return None

    def analyze_sanitizer_coverage(self, code: str, vulnerabilities: list[dict[str, Any]]) -> dict[str, Any]:
        """
        Analyze how well sanitizers cover detected vulnerabilities.

        Args:
            code: Python source code
            vulnerabilities: List of detected vulnerabilities

        Returns:
            Coverage analysis dict with coverage percentage and details
        """
        sanitizers = self.detect_sanitizers(code)

        if not vulnerabilities:
            return {
                "coverage_percentage": 100.0,
                "sanitizers_found": len(sanitizers),
                "vulnerabilities_covered": 0,
                "vulnerabilities_uncovered": 0,
                "details": "No vulnerabilities detected",
            }

        # Map vulnerability types to sanitizer types
        vuln_to_sanitizer = {
            "SQL Injection": "sql_parameterization",
            "XSS": "html_escape",
            "Path Traversal": "path_sanitization",
            "Command Injection": "command_escaping",
        }

        covered = 0
        for vuln in vulnerabilities:
            vuln_type = vuln.get("type", "")
            vuln_line = vuln.get("line", 0)

            # Check if there's a sanitizer of the right type near this vulnerability
            needed_sanitizer = vuln_to_sanitizer.get(vuln_type)
            if needed_sanitizer:
                # Look for sanitizers within 10 lines before the vulnerability
                for san in sanitizers:
                    if san.sanitizer_type == needed_sanitizer:
                        if abs(san.line - vuln_line) <= 10:
                            covered += 1
                            break

        coverage_pct = (covered / len(vulnerabilities) * 100.0) if vulnerabilities else 0.0

        return {
            "coverage_percentage": coverage_pct,
            "sanitizers_found": len(sanitizers),
            "vulnerabilities_covered": covered,
            "vulnerabilities_uncovered": len(vulnerabilities) - covered,
            "details": f"{covered}/{len(vulnerabilities)} vulnerabilities have nearby sanitizers",
        }
