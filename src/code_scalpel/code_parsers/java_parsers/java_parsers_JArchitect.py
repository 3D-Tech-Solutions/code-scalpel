#!/usr/bin/env python3
"""
JArchitect Parser - Java code quality and architecture analysis.
Parses JArchitect analysis results for architecture and quality metrics.
JArchitect analyzes code structure, dependencies, and quality.
Reference: https://www.jarchitect.com/
Note: JArchitect is a commercial tool with GUI-based analysis.
"""

from dataclasses import dataclass, field
from pathlib import Path

from defusedxml import ElementTree as ET


@dataclass
class QualityMetric:
    """Code quality metric from JArchitect."""

    name: str
    value: float
    threshold: float | None = None
    status: str = "OK"  # "OK", "WARNING", "VIOLATION"


@dataclass
class DependencyIssue:
    """Dependency or architecture issue from JArchitect."""

    source: str  # Source class/package
    target: str  # Target class/package
    issue_type: str  # "CYCLIC_DEPENDENCY", "LAYER_VIOLATION", etc.
    severity: str
    message: str


@dataclass
class JArchitectReport:
    """Full JArchitect analysis report."""

    metrics: list[QualityMetric] = field(default_factory=list)
    dependency_issues: list[DependencyIssue] = field(default_factory=list)
    lines_of_code: int = 0
    num_types: int = 0
    num_methods: int = 0
    cyclomatic_complexity: float = 0.0
    technical_debt: str = ""  # Time estimate


class JArchitectParser:
    """
    Parser for JArchitect Java architecture analysis.

    JArchitect provides:
    - Code quality metrics (cyclomatic complexity, coupling, etc.)
    - Dependency analysis and cycle detection
    - Architecture conformance checking
    - Technical debt estimation
    - Trend analysis over time
    """

    # Common JArchitect metrics
    QUALITY_METRICS = [
        "LinesOfCode",
        "CyclomaticComplexity",
        "TypeCoupling",
        "MethodCoupling",
        "LackOfCohesion",
        "InheritanceDepth",
        "CommentRatio",
    ]

    def __init__(self):
        """Initialize JArchitect parser."""
        self.language = "java"

    def parse(self, report_file: str) -> JArchitectReport:
        """
        Parse JArchitect XML/HTML report.

        Args:
            report_file: Path to JArchitect report file

        Returns:
            JArchitectReport object
        """
        content = Path(report_file).read_text()
        if report_file.endswith(".xml"):
            return self.parse_xml(content)
        else:
            # Placeholder for other formats
            return JArchitectReport()

    def parse_xml(self, xml_content: str) -> JArchitectReport:
        """
        Parse JArchitect XML export.

        Args:
            xml_content: XML content string

        Returns:
            JArchitectReport
        """
        report = JArchitectReport()
        try:
            root = ET.fromstring(xml_content)

            # Parse metrics
            for metric_elem in root.findall(".//Metric"):
                name = metric_elem.get("name", "")
                value = float(metric_elem.get("value", 0))
                threshold = metric_elem.get("threshold")
                status = metric_elem.get("status", "OK")
                report.metrics.append(
                    QualityMetric(
                        name=name,
                        value=value,
                        threshold=float(threshold) if threshold else None,
                        status=status,
                    )
                )

            # Parse dependency issues
            for issue_elem in root.findall(".//DependencyIssue"):
                report.dependency_issues.append(
                    DependencyIssue(
                        source=issue_elem.get("source", ""),
                        target=issue_elem.get("target", ""),
                        issue_type=issue_elem.get("type", ""),
                        severity=issue_elem.get("severity", "WARNING"),
                        message=issue_elem.text or "",
                    )
                )

            # Parse summary
            summary = root.find(".//Summary")
            if summary is not None:
                report.lines_of_code = int(summary.get("loc", 0))
                report.num_types = int(summary.get("types", 0))
                report.num_methods = int(summary.get("methods", 0))
                report.technical_debt = summary.get("technicalDebt", "")

        except ET.ParseError as e:
            print(f"XML parse error: {e}")
        return report

    def get_violations(self, report: JArchitectReport) -> list[QualityMetric]:
        """
        Get metrics that violate thresholds.

        Args:
            report: JArchitect report

        Returns:
            List of violated metrics
        """
        return [m for m in report.metrics if m.status == "VIOLATION"]

    def get_cyclic_dependencies(self, report: JArchitectReport) -> list[DependencyIssue]:
        """
        Get cyclic dependency issues.

        Args:
            report: JArchitect report

        Returns:
            List of cyclic dependency issues
        """
        return [d for d in report.dependency_issues if d.issue_type == "CYCLIC_DEPENDENCY"]
