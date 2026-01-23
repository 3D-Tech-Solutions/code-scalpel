"""
Custom Metrics - Extensible metric collection for project analysis.

[20251226_FEATURE] Enterprise tier feature for crawl_project.

Features:
- Pluggable metric collectors
- Built-in metrics: LOC, complexity, coverage, security
- Custom metric registration
- Aggregation and reporting
- Export to JSON/CSV formats

Usage:
    from code_scalpel.analysis.custom_metrics import MetricsCollector

    collector = MetricsCollector()
    collector.register_metric("my_metric", my_metric_fn)

    results = collector.collect("/path/to/project")
"""

from __future__ import annotations

import ast
import csv
import json
import re
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from io import StringIO
from pathlib import Path
from typing import Any


@dataclass
class MetricValue:
    """A single metric measurement."""

    name: str
    value: int | float | str | bool
    unit: str | None = None
    file_path: str | None = None
    line_number: int | None = None
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class MetricSummary:
    """Summary of a metric across all files."""

    name: str
    total: int | float
    average: float
    min_value: int | float
    max_value: int | float
    count: int
    unit: str | None = None


@dataclass
class MetricsReport:
    """Complete metrics report for a project."""

    project_path: str
    collected_at: str
    metrics: list[MetricValue]
    summaries: dict[str, MetricSummary]
    file_metrics: dict[str, list[MetricValue]]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> str:
        """Export report to JSON."""
        return json.dumps(
            {
                "project_path": self.project_path,
                "collected_at": self.collected_at,
                "summaries": {
                    name: {
                        "name": s.name,
                        "total": s.total,
                        "average": s.average,
                        "min": s.min_value,
                        "max": s.max_value,
                        "count": s.count,
                        "unit": s.unit,
                    }
                    for name, s in self.summaries.items()
                },
                "file_count": len(self.file_metrics),
                "metadata": self.metadata,
            },
            indent=2,
        )

    def to_csv(self) -> str:
        """Export file metrics to CSV."""
        output = StringIO()
        writer = csv.writer(output)

        # Get all metric names
        metric_names: set[str] = set()
        for file_metrics in self.file_metrics.values():
            for m in file_metrics:
                metric_names.add(m.name)

        # Write header
        headers = ["file"] + sorted(metric_names)
        writer.writerow(headers)

        # Write file rows
        for file_path, metrics in self.file_metrics.items():
            row: list[str] = [file_path]
            metric_dict = {m.name: m.value for m in metrics}
            for name in sorted(metric_names):
                # CSV writer expects strings; coerce numeric/bool metrics to str
                row.append(str(metric_dict.get(name, "")))
            writer.writerow(row)

        return output.getvalue()


class MetricCollector(ABC):
    """Abstract base class for metric collectors."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique name for this metric."""
        pass

    @property
    def unit(self) -> str | None:
        """Unit of measurement (e.g., 'lines', 'score')."""
        return None

    @abstractmethod
    def collect(self, file_path: Path, content: str) -> MetricValue | None:
        """
        Collect metric from a file.

        Args:
            file_path: Path to the file
            content: File content

        Returns:
            MetricValue or None if not applicable
        """
        pass


class LinesOfCodeCollector(MetricCollector):
    """Collects lines of code metrics."""

    @property
    def name(self) -> str:
        return "lines_of_code"

    @property
    def unit(self) -> str:
        return "lines"

    def collect(self, file_path: Path, content: str) -> MetricValue:
        lines = content.splitlines()
        total = len(lines)
        blank = sum(1 for line in lines if not line.strip())
        comment = sum(1 for line in lines if line.strip().startswith(("#", "//", "/*", "*")))
        code = total - blank - comment

        return MetricValue(
            name=self.name,
            value=code,
            unit=self.unit,
            file_path=str(file_path),
            details={
                "total_lines": total,
                "blank_lines": blank,
                "comment_lines": comment,
                "code_lines": code,
            },
        )


class CyclomaticComplexityCollector(MetricCollector):
    """Collects cyclomatic complexity for Python files."""

    @property
    def name(self) -> str:
        return "cyclomatic_complexity"

    @property
    def unit(self) -> str:
        return "score"

    def collect(self, file_path: Path, content: str) -> MetricValue | None:
        if file_path.suffix != ".py":
            return None

        try:
            tree = ast.parse(content)
        except SyntaxError:
            return None

        complexity = 1  # Base complexity

        for node in ast.walk(tree):
            # Each decision point adds 1
            if isinstance(node, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(node, ast.BoolOp):
                # and/or add complexity
                complexity += len(node.values) - 1
            elif isinstance(node, ast.comprehension):
                complexity += 1
                if node.ifs:
                    complexity += len(node.ifs)

        return MetricValue(
            name=self.name,
            value=complexity,
            unit=self.unit,
            file_path=str(file_path),
        )


class FunctionCountCollector(MetricCollector):
    """Counts functions/methods in files."""

    @property
    def name(self) -> str:
        return "function_count"

    @property
    def unit(self) -> str:
        return "functions"

    def collect(self, file_path: Path, content: str) -> MetricValue | None:
        count = 0

        if file_path.suffix == ".py":
            try:
                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        count += 1
            except SyntaxError:
                pass
        elif file_path.suffix in (".js", ".ts", ".jsx", ".tsx"):
            # Simple regex for JS/TS functions
            patterns = [
                r"function\s+\w+",
                r"const\s+\w+\s*=\s*(?:async\s*)?\(",
                r"(?:async\s+)?(\w+)\s*\([^)]*\)\s*[{:]",
            ]
            for pattern in patterns:
                count += len(re.findall(pattern, content))

        return MetricValue(
            name=self.name,
            value=count,
            unit=self.unit,
            file_path=str(file_path),
        )


class ClassCountCollector(MetricCollector):
    """Counts classes in files."""

    @property
    def name(self) -> str:
        return "class_count"

    @property
    def unit(self) -> str:
        return "classes"

    def collect(self, file_path: Path, content: str) -> MetricValue | None:
        count = 0

        if file_path.suffix == ".py":
            try:
                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        count += 1
            except SyntaxError:
                pass
        elif file_path.suffix in (".js", ".ts", ".jsx", ".tsx"):
            # Simple regex for JS/TS classes
            count = len(re.findall(r"class\s+\w+", content))
        elif file_path.suffix == ".java":
            count = len(re.findall(r"class\s+\w+", content))

        return MetricValue(
            name=self.name,
            value=count,
            unit=self.unit,
            file_path=str(file_path),
        )


class ImportCountCollector(MetricCollector):
    """Counts imports in files."""

    @property
    def name(self) -> str:
        return "import_count"

    @property
    def unit(self) -> str:
        return "imports"

    def collect(self, file_path: Path, content: str) -> MetricValue | None:
        count = 0

        if file_path.suffix == ".py":
            try:
                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        count += len(node.names)
                    elif isinstance(node, ast.ImportFrom):
                        count += len(node.names)
            except SyntaxError:
                pass
        elif file_path.suffix in (".js", ".ts", ".jsx", ".tsx"):
            count = len(re.findall(r"(?:import|require)\s*\(?\s*['\"]", content))

        return MetricValue(
            name=self.name,
            value=count,
            unit=self.unit,
            file_path=str(file_path),
        )


class TodoCountCollector(MetricCollector):

    @property
    def name(self) -> str:
        return "todo_count"

    @property
    def unit(self) -> str:
        return "items"

    def collect(self, file_path: Path, content: str) -> MetricValue:
        todos = []
        patterns = [
            (r"#\s*(TODO|FIXME|XXX|HACK|BUG)[\s:]+(.+)", "python"),
            (r"//\s*(TODO|FIXME|XXX|HACK|BUG)[\s:]+(.+)", "js"),
            (r"/\*\s*(TODO|FIXME|XXX|HACK|BUG)[\s:]+(.+?)\*/", "block"),
        ]

        for line_num, line in enumerate(content.splitlines(), 1):
            for pattern, _ in patterns:
                matches = re.findall(pattern, line, re.IGNORECASE)
                for match in matches:
                    todos.append(
                        {
                            "type": match[0].upper(),
                            "message": match[1].strip(),
                            "line": line_num,
                        }
                    )

        return MetricValue(
            name=self.name,
            value=len(todos),
            unit=self.unit,
            file_path=str(file_path),
            details={"todos": todos[:20]},  # Limit details
        )


class MetricsCollector:
    """Main metrics collection orchestrator."""

    # Default file extensions to analyze
    SUPPORTED_EXTENSIONS = {
        ".py",
        ".js",
        ".jsx",
        ".ts",
        ".tsx",
        ".java",
        ".go",
        ".rs",
        ".rb",
        ".php",
        ".c",
        ".cpp",
        ".h",
        ".hpp",
        ".cs",
    }

    def __init__(self):
        """Initialize with built-in collectors."""
        self._collectors: dict[str, MetricCollector] = {}
        self._custom_fns: dict[str, tuple[Callable[[Path, str], int | float | None], str | None]] = {}

        # Register built-in collectors
        for collector_cls in [
            LinesOfCodeCollector,
            CyclomaticComplexityCollector,
            FunctionCountCollector,
            ClassCountCollector,
            ImportCountCollector,
            TodoCountCollector,
        ]:
            collector = collector_cls()
            self._collectors[collector.name] = collector

    def register_collector(self, collector: MetricCollector) -> None:
        """Register a custom metric collector."""
        self._collectors[collector.name] = collector

    def register_metric(
        self,
        name: str,
        fn: Callable[[Path, str], int | float | None],
        unit: str | None = None,
    ) -> None:
        """
        Register a simple metric function.

        Args:
            name: Metric name
            fn: Function taking (file_path, content) and returning value
            unit: Optional unit of measurement
        """
        self._custom_fns[name] = (fn, unit)

    def collect(
        self,
        project_path: str | Path,
        extensions: set[str] | None = None,
        exclude_dirs: set[str] | None = None,
    ) -> MetricsReport:
        """
        Collect all metrics for a project.

        Args:
            project_path: Path to the project
            extensions: File extensions to analyze
            exclude_dirs: Directories to exclude

        Returns:
            MetricsReport with all collected metrics
        """
        root = Path(project_path).resolve()
        target_extensions = extensions or self.SUPPORTED_EXTENSIONS
        exclude = exclude_dirs or {
            "node_modules",
            ".git",
            "__pycache__",
            ".venv",
            "venv",
        }

        all_metrics: list[MetricValue] = []
        file_metrics: dict[str, list[MetricValue]] = {}

        for file_path in root.rglob("*"):
            if not file_path.is_file():
                continue
            if file_path.suffix.lower() not in target_extensions:
                continue
            if any(ex in file_path.parts for ex in exclude):
                continue

            try:
                content = file_path.read_text(errors="replace")
            except Exception:
                continue

            rel_path = str(file_path.relative_to(root))
            file_metrics[rel_path] = []

            # Collect from registered collectors
            for collector in self._collectors.values():
                try:
                    metric = collector.collect(file_path, content)
                    if metric:
                        all_metrics.append(metric)
                        file_metrics[rel_path].append(metric)
                except Exception:
                    pass

            # Collect from custom functions
            for name, (fn, unit) in self._custom_fns.items():
                try:
                    value = fn(file_path, content)
                    if value is not None:
                        metric = MetricValue(
                            name=name,
                            value=value,
                            unit=unit,
                            file_path=str(file_path),
                        )
                        all_metrics.append(metric)
                        file_metrics[rel_path].append(metric)
                except Exception:
                    pass

        # Calculate summaries
        summaries = self._calculate_summaries(all_metrics)

        return MetricsReport(
            project_path=str(root),
            collected_at=datetime.now().isoformat(),
            metrics=all_metrics,
            summaries=summaries,
            file_metrics=file_metrics,
            metadata={
                "collector_count": len(self._collectors) + len(self._custom_fns),
                "file_count": len(file_metrics),
            },
        )

    def _calculate_summaries(
        self,
        metrics: list[MetricValue],
    ) -> dict[str, MetricSummary]:
        """Calculate summary statistics for each metric."""
        summaries: dict[str, MetricSummary] = {}

        # Group by metric name
        by_name: dict[str, list[MetricValue]] = {}
        for m in metrics:
            if m.name not in by_name:
                by_name[m.name] = []
            by_name[m.name].append(m)

        for name, values in by_name.items():
            numeric_values = [v.value for v in values if isinstance(v.value, (int, float))]

            if numeric_values:
                summaries[name] = MetricSummary(
                    name=name,
                    total=sum(numeric_values),
                    average=sum(numeric_values) / len(numeric_values),
                    min_value=min(numeric_values),
                    max_value=max(numeric_values),
                    count=len(numeric_values),
                    unit=values[0].unit if values else None,
                )

        return summaries


def collect_metrics(
    project_path: str | Path,
    custom_metrics: dict[str, Callable] | None = None,
) -> MetricsReport:
    """
    Convenience function to collect project metrics.

    Args:
        project_path: Path to the project
        custom_metrics: Optional dict of {name: function} custom metrics

    Returns:
        MetricsReport with all collected metrics
    """
    collector = MetricsCollector()

    if custom_metrics:
        for name, fn in custom_metrics.items():
            collector.register_metric(name, fn)

    return collector.collect(project_path)
