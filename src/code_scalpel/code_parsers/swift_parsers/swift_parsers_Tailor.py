#!/usr/bin/env python3
"""Tailor Parser - Swift Code Metrics Analysis.

[20260304_FEATURE] Full implementation replacing Phase 2 stubs.

Tailor is an open-source Swift static analysis tool.
Reference: https://tailor.sh
Command:   tailor --format json [paths...]
Output format: JSON object with "files" array.

Note: Tailor development has been largely inactive since ~2019.
The parser supports its JSON output format for legacy integration.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


class MetricType(Enum):
    """Tailor metric types."""

    COMPLEXITY = "complexity"
    LENGTH = "length"
    NAMING = "naming"
    STYLE = "style"
    DESIGN = "design"


@dataclass
class TailorMetric:
    """Represents a metric or violation detected by Tailor."""

    metric_type: MetricType
    message: str
    severity: str
    file_path: str
    line_number: int
    column: int
    value: Optional[float] = None


@dataclass
class TailorConfig:
    """Tailor configuration for analysis."""

    tailor_version: str = "0.29.0"
    config_file: Optional[Path] = None
    excluded_dirs: List[str] = field(default_factory=list)
    max_complexity: int = 15
    max_length: int = 80


# [20260304_FEATURE] Rule keyword → MetricType mapping
_RULE_TYPE_MAP: Dict[str, MetricType] = {
    "length": MetricType.LENGTH,
    "line-length": MetricType.LENGTH,
    "name": MetricType.NAMING,
    "naming": MetricType.NAMING,
    "cyclomatic": MetricType.COMPLEXITY,
    "complexity": MetricType.COMPLEXITY,
    "trailing": MetricType.STYLE,
    "leading": MetricType.STYLE,
    "brace": MetricType.STYLE,
    "parenthesis": MetricType.STYLE,
    "comment": MetricType.DESIGN,
    "todo": MetricType.DESIGN,
}


def _infer_metric_type(rule: str) -> MetricType:
    """Guess MetricType from a rule identifier string."""
    rule_lower = rule.lower()
    for keyword, mtype in _RULE_TYPE_MAP.items():
        if keyword in rule_lower:
            return mtype
    return MetricType.STYLE


class TailorParser:
    """
    Parser for Tailor Swift code metrics analysis.

    [20260304_FEATURE] Full implementation: execute + parse JSON output.

    Graceful degradation: returns [] if tailor is not installed.
    """

    def __init__(self) -> None:
        """Initialise Tailor parser."""
        self.config = TailorConfig()
        self.metrics: List[TailorMetric] = []

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def execute_tailor(
        self, paths: List[Path], config: Optional[TailorConfig] = None
    ) -> List[TailorMetric]:
        """
        Run ``tailor --format json`` on the given paths.

        [20260304_FEATURE] Graceful degradation when tailor not installed.

        Returns an empty list if tailor is unavailable or times out.
        """
        if shutil.which("tailor") is None:
            return []
        cmd = ["tailor", "--format", "json"] + [str(p) for p in paths]
        cfg = config or self.config
        if cfg.config_file:
            cmd += ["--config", str(cfg.config_file)]
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,
            )
            return self.parse_json_report(result.stdout)
        except (subprocess.TimeoutExpired, OSError):
            return []

    # ------------------------------------------------------------------
    # Parsing
    # ------------------------------------------------------------------

    def parse_json_report(self, output: str) -> List[TailorMetric]:
        """
        Parse ``tailor --format json`` stdout.

        [20260304_FEATURE] JSON format::

            {"files": [{"path": "...",
                        "violations": [{"location": {"line": 5, "column": 1},
                                        "severity": "warning",
                                        "rule": "trailing-whitespace",
                                        "message": "..."}]}]}
        """
        if not output or not output.strip():
            return []
        try:
            data = json.loads(output)
        except json.JSONDecodeError:
            return []

        metrics: List[TailorMetric] = []
        for file_entry in data.get("files", []):
            file_path = file_entry.get("path", "")
            for v in file_entry.get("violations", []):
                loc = v.get("location", {})
                rule = v.get("rule", "")
                metrics.append(
                    TailorMetric(
                        metric_type=_infer_metric_type(rule),
                        message=v.get("message", ""),
                        severity=v.get("severity", "warning"),
                        file_path=file_path,
                        line_number=loc.get("line", 0),
                        column=loc.get("column", 0),
                    )
                )
        return metrics

    # ------------------------------------------------------------------
    # Analysis helpers
    # ------------------------------------------------------------------

    def load_config(self, config_file: Path) -> TailorConfig:
        """Return a TailorConfig pointing at the given config file."""
        cfg = TailorConfig()
        cfg.config_file = config_file
        return cfg

    def categorize_metrics(
        self, metrics: List[TailorMetric]
    ) -> Dict[str, List[TailorMetric]]:
        """
        Group by MetricType name.

        [20260304_FEATURE] Returns {"STYLE": [...], "COMPLEXITY": [...], ...}.
        """
        categories: Dict[str, List[TailorMetric]] = {}
        for m in metrics:
            key = m.metric_type.name
            categories.setdefault(key, []).append(m)
        return categories

    def detect_complexity_issues(
        self, metrics: List[TailorMetric]
    ) -> List[TailorMetric]:
        """Filter metrics of type COMPLEXITY."""
        return [m for m in metrics if m.metric_type == MetricType.COMPLEXITY]

    def calculate_code_metrics(self, metrics: List[TailorMetric]) -> Dict[str, Any]:
        """
        Aggregate metric counts.

        [20260304_FEATURE] Returns total and per-type breakdown.
        """
        by_type: Dict[str, int] = {}
        by_severity: Dict[str, int] = {}
        for m in metrics:
            by_type[m.metric_type.value] = by_type.get(m.metric_type.value, 0) + 1
            by_severity[m.severity] = by_severity.get(m.severity, 0) + 1
        return {
            "total": len(metrics),
            "by_type": by_type,
            "by_severity": by_severity,
        }

    def generate_report(self, metrics: List[TailorMetric], format: str = "json") -> str:
        """
        Generate a structured report.

        [20260304_FEATURE] JSON and plain-text formats.
        """
        if format == "json":
            return json.dumps(
                [
                    {
                        "metric_type": m.metric_type.value,
                        "message": m.message,
                        "severity": m.severity,
                        "file_path": m.file_path,
                        "line_number": m.line_number,
                        "column": m.column,
                    }
                    for m in metrics
                ],
                indent=2,
            )
        lines = [
            f"{m.file_path}:{m.line_number}:{m.column}: {m.severity}: {m.message}"
            for m in metrics
        ]
        return "\n".join(lines)

    def analyze_metric_trends(self, historical_data: List[Dict]) -> Dict[str, Any]:
        """
        Analyse trends across historical metric snapshots.

        [20260304_FEATURE] Each entry in historical_data should be the output of
        calculate_code_metrics() for a given snapshot.
        """
        if not historical_data:
            return {}
        totals = [d.get("total", 0) for d in historical_data]
        return {
            "snapshots": len(historical_data),
            "first_total": totals[0],
            "last_total": totals[-1],
            "delta": totals[-1] - totals[0],
            "trend": "improving" if totals[-1] < totals[0] else "worsening" if totals[-1] > totals[0] else "stable",
        }

