#!/usr/bin/env python3
"""
SonarQube Java Parser - Code quality and security analysis platform.
Interfaces with SonarQube API to retrieve analysis results.
SonarQube provides continuous inspection of code quality.
Reference: https://docs.sonarsource.com/sonarqube/latest/
Command: sonar-scanner -Dsonar.projectKey=myproject -Dsonar.sources=src
"""

import base64
import json
from dataclasses import dataclass, field
from urllib.error import URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


@dataclass
class SonarIssue:
    """Represents a SonarQube issue."""

    key: str  # Issue unique key
    rule: str  # Rule key (e.g., "java:S1234")
    severity: str  # BLOCKER, CRITICAL, MAJOR, MINOR, INFO
    component: str  # File path
    line: int | None
    message: str
    effort: str  # Remediation effort (e.g., "5min")
    debt: str  # Technical debt
    issue_type: str  # BUG, VULNERABILITY, CODE_SMELL
    tags: list[str] = field(default_factory=list)


@dataclass
class SonarMetrics:
    """SonarQube project metrics."""

    bugs: int = 0
    vulnerabilities: int = 0
    code_smells: int = 0
    coverage: float = 0.0
    duplicated_lines_density: float = 0.0
    ncloc: int = 0  # Non-comment lines of code
    sqale_rating: str = ""  # A, B, C, D, E
    reliability_rating: str = ""
    security_rating: str = ""


class SonarQubeParser:
    """
    Parser for SonarQube Java code quality analysis.

    SonarQube performs continuous inspection for:
    - Bugs and reliability issues
    - Security vulnerabilities
    - Code smells and maintainability
    - Test coverage tracking
    - Duplicate code detection
    """

    # SonarQube severity levels
    SEVERITY_LEVELS = ["BLOCKER", "CRITICAL", "MAJOR", "MINOR", "INFO"]

    # Issue types
    ISSUE_TYPES = ["BUG", "VULNERABILITY", "CODE_SMELL", "SECURITY_HOTSPOT"]

    def __init__(
        self,
        server_url: str = "http://localhost:9000",
        token: str | None = None,
    ):
        """
        Initialize SonarQube parser.

        Args:
            server_url: SonarQube server URL
            token: Authentication token
        """
        self.server_url = server_url.rstrip("/")
        self.token = token
        self.language = "java"

    def _make_request(self, endpoint: str) -> dict | None:
        """
        Make authenticated request to SonarQube API.

        Args:
            endpoint: API endpoint path

        Returns:
            JSON response or None
        """
        parsed_base = urlparse(self.server_url)
        if parsed_base.scheme not in {"http", "https"} or not parsed_base.netloc:
            print("SonarQube API error: server_url must be http(s) with a host (e.g., https://sonar.local:9000)")
            return None

        url = f"{self.server_url}/api/{endpoint}"
        try:
            request = Request(url)
            if self.token:
                # SonarQube uses token:blank for auth
                credentials = base64.b64encode(f"{self.token}:".encode()).decode()
                request.add_header("Authorization", f"Basic {credentials}")

            with urlopen(request, timeout=30) as response:  # nosec B310
                return json.loads(response.read().decode())
        except (URLError, json.JSONDecodeError) as e:
            print(f"SonarQube API error: {e}")
            return None

    def get_issues(self, project_key: str) -> list[SonarIssue]:
        """
        Get all issues for a project.

        Args:
            project_key: SonarQube project key

        Returns:
            List of SonarIssue objects
        """
        issues = []
        page = 1
        page_size = 100

        while True:
            endpoint = f"issues/search?componentKeys={project_key}&ps={page_size}&p={page}"
            data = self._make_request(endpoint)
            if not data or "issues" not in data:
                break

            for issue in data["issues"]:
                issues.append(
                    SonarIssue(
                        key=issue.get("key", ""),
                        rule=issue.get("rule", ""),
                        severity=issue.get("severity", "INFO"),
                        component=issue.get("component", ""),
                        line=issue.get("line"),
                        message=issue.get("message", ""),
                        effort=issue.get("effort", ""),
                        debt=issue.get("debt", ""),
                        issue_type=issue.get("type", "CODE_SMELL"),
                        tags=issue.get("tags", []),
                    )
                )

            # Check if more pages
            total = data.get("total", 0)
            if page * page_size >= total:
                break
            page += 1

        return issues

    def get_metrics(self, project_key: str) -> SonarMetrics:
        """
        Get project metrics.

        Args:
            project_key: SonarQube project key

        Returns:
            SonarMetrics object
        """
        metrics = SonarMetrics()
        metric_keys = (
            "bugs,vulnerabilities,code_smells,coverage,"
            "duplicated_lines_density,ncloc,sqale_rating,"
            "reliability_rating,security_rating"
        )

        endpoint = f"measures/component?component={project_key}&metricKeys={metric_keys}"
        data = self._make_request(endpoint)
        if not data or "component" not in data:
            return metrics

        for measure in data["component"].get("measures", []):
            metric = measure.get("metric", "")
            value = measure.get("value", "")

            if metric == "bugs":
                metrics.bugs = int(value)
            elif metric == "vulnerabilities":
                metrics.vulnerabilities = int(value)
            elif metric == "code_smells":
                metrics.code_smells = int(value)
            elif metric == "coverage":
                metrics.coverage = float(value)
            elif metric == "duplicated_lines_density":
                metrics.duplicated_lines_density = float(value)
            elif metric == "ncloc":
                metrics.ncloc = int(value)
            elif metric == "sqale_rating":
                metrics.sqale_rating = self._rating_to_letter(value)
            elif metric == "reliability_rating":
                metrics.reliability_rating = self._rating_to_letter(value)
            elif metric == "security_rating":
                metrics.security_rating = self._rating_to_letter(value)

        return metrics

    def _rating_to_letter(self, value: str) -> str:
        """Convert SonarQube rating number to letter."""
        ratings = {"1.0": "A", "2.0": "B", "3.0": "C", "4.0": "D", "5.0": "E"}
        return ratings.get(value, value)

    def get_vulnerabilities(self, issues: list[SonarIssue]) -> list[SonarIssue]:
        """
        Filter for security vulnerabilities.

        Args:
            issues: List of all issues

        Returns:
            List of vulnerability issues
        """
        return [i for i in issues if i.issue_type == "VULNERABILITY"]

    def get_bugs(self, issues: list[SonarIssue]) -> list[SonarIssue]:
        """
        Filter for bugs.

        Args:
            issues: List of all issues

        Returns:
            List of bug issues
        """
        return [i for i in issues if i.issue_type == "BUG"]

    def get_by_severity(self, issues: list[SonarIssue], severity: str) -> list[SonarIssue]:
        """
        Filter issues by severity.

        Args:
            issues: List of all issues
            severity: Severity level to filter

        Returns:
            List of filtered issues
        """
        return [i for i in issues if i.severity == severity]
