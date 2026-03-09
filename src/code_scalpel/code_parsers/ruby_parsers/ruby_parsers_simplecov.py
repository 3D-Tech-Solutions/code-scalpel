#!/usr/bin/env python3
"""
SimpleCov Parser - Ruby Test Coverage Analysis.

[20260304_FEATURE] Full implementation of SimpleCov parser for Ruby coverage data.
SimpleCov writes .resultset.json files with per-file line coverage arrays.

No CLI execution needed — reads .resultset.json output files directly.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class FileCoverage:
    """Coverage data for a single source file."""

    file_path: str
    lines: List[Optional[int]]  # None=non-executable, 0=uncovered, N=hit count
    covered_lines: int = 0
    uncovered_lines: int = 0
    total_lines: int = 0
    coverage_percent: float = 0.0


@dataclass
class CoverageMetrics:
    """Aggregate coverage metrics across all files."""

    total_files: int
    covered_lines: int
    uncovered_lines: int
    total_lines: int
    coverage_percent: float
    files: List[FileCoverage] = field(default_factory=list)
    groups: Dict[str, Any] = field(default_factory=dict)


class SimpleCovParser:
    """
    Parser for SimpleCov Ruby test coverage reports.

    [20260304_FEATURE] Reads .resultset.json files produced by SimpleCov.

    SimpleCov JSON structure:
        {
          "<suite_name>": {
            "coverage": {
              "<file_path>": {
                "lines": [null, 1, 0, 3, null, ...]
              }
            }
          }
        }
    Null entries = non-executable lines; integers = hit count (0 = uncovered).
    """

    def __init__(self) -> None:
        """Initialize SimpleCov parser."""
        pass

    def parse_resultset_json(self, path: Path) -> CoverageMetrics:
        """
        Read and parse a .resultset.json file.

        [20260304_FEATURE] Supports single suite or merged multi-suite result sets.
        """
        data = json.loads(path.read_text(encoding="utf-8"))
        return self._parse_resultset_data(data)

    def _parse_resultset_data(self, data: Dict[str, Any]) -> CoverageMetrics:
        """Parse raw resultset dict into CoverageMetrics."""
        merged: Dict[str, List[Optional[int]]] = {}
        for suite_data in data.values():
            if not isinstance(suite_data, dict):
                continue
            coverage = suite_data.get("coverage", {})
            for file_path, file_data in coverage.items():
                lines: List[Optional[int]] = []
                if isinstance(file_data, dict):
                    lines = file_data.get("lines", [])
                elif isinstance(file_data, list):
                    lines = file_data
                if file_path in merged:
                    merged[file_path] = self._merge_line_arrays(merged[file_path], lines)
                else:
                    merged[file_path] = lines
        files = self.parse_coverage_data(merged)
        return self.calculate_coverage_metrics(files)

    def _merge_line_arrays(
        self,
        a: List[Optional[int]],
        b: List[Optional[int]],
    ) -> List[Optional[int]]:
        """Merge two line coverage arrays by summing hit counts."""
        length = max(len(a), len(b))
        result: List[Optional[int]] = []
        for i in range(length):
            va = a[i] if i < len(a) else None
            vb = b[i] if i < len(b) else None
            if va is None and vb is None:
                result.append(None)
            elif va is None:
                result.append(vb)
            elif vb is None:
                result.append(va)
            else:
                result.append(va + vb)
        return result

    def parse_coverage_data(
        self, coverage_dict: Dict[str, List[Optional[int]]]
    ) -> List[FileCoverage]:
        """
        Convert raw coverage dict to FileCoverage objects.

        [20260304_FEATURE] Computes per-file stats.
        """
        file_coverages: List[FileCoverage] = []
        for file_path, lines in coverage_dict.items():
            executable = [(i, v) for i, v in enumerate(lines) if v is not None]
            covered = sum(1 for _, v in executable if v and v > 0)
            uncovered = sum(1 for _, v in executable if v == 0)
            total = len(executable)
            pct = (covered / total * 100.0) if total > 0 else 0.0
            file_coverages.append(
                FileCoverage(
                    file_path=file_path,
                    lines=lines,
                    covered_lines=covered,
                    uncovered_lines=uncovered,
                    total_lines=total,
                    coverage_percent=round(pct, 2),
                )
            )
        return file_coverages

    def calculate_coverage_metrics(self, files: List[FileCoverage]) -> CoverageMetrics:
        """
        Aggregate per-file stats into overall CoverageMetrics.

        [20260304_FEATURE] Returns total and per-file breakdown.
        """
        total_covered = sum(f.covered_lines for f in files)
        total_uncovered = sum(f.uncovered_lines for f in files)
        total_lines = sum(f.total_lines for f in files)
        overall_pct = (total_covered / total_lines * 100.0) if total_lines > 0 else 0.0
        return CoverageMetrics(
            total_files=len(files),
            covered_lines=total_covered,
            uncovered_lines=total_uncovered,
            total_lines=total_lines,
            coverage_percent=round(overall_pct, 2),
            files=files,
        )

    def identify_uncovered_lines(self, file_coverage: FileCoverage) -> List[int]:
        """
        Return 1-based line numbers of uncovered executable lines.

        [20260304_FEATURE] Returns empty list if fully covered.
        """
        return [i + 1 for i, v in enumerate(file_coverage.lines) if v == 0]

    def analyze_coverage_trends(
        self, historical: List[CoverageMetrics]
    ) -> Dict[str, Any]:
        """
        Compare a series of CoverageMetrics snapshots to detect trends.

        [20260304_FEATURE] Returns direction ('improving', 'declining', 'stable').
        """
        if len(historical) < 2:
            return {"direction": "insufficient_data", "snapshots": len(historical)}
        percentages = [m.coverage_percent for m in historical]
        delta = percentages[-1] - percentages[0]
        direction = "improving" if delta > 0.5 else ("declining" if delta < -0.5 else "stable")
        return {
            "direction": direction,
            "start_percent": percentages[0],
            "end_percent": percentages[-1],
            "delta": round(delta, 2),
        }

    def identify_coverage_hotspots(
        self, files: List[FileCoverage], threshold: float = 50.0
    ) -> List[FileCoverage]:
        """
        Identify files with coverage below threshold.

        [20260304_FEATURE] Default threshold 50%.
        """
        return [f for f in files if f.coverage_percent < threshold]

    def generate_coverage_report(self, metrics: CoverageMetrics) -> str:
        """
        Generate a structured JSON coverage report.

        [20260304_FEATURE] Returns JSON string.
        """
        report: Dict[str, Any] = {
            "tool": "simplecov",
            "total_files": metrics.total_files,
            "coverage_percent": metrics.coverage_percent,
            "covered_lines": metrics.covered_lines,
            "uncovered_lines": metrics.uncovered_lines,
            "total_lines": metrics.total_lines,
            "files": [
                {
                    "file": f.file_path,
                    "coverage_percent": f.coverage_percent,
                    "covered": f.covered_lines,
                    "uncovered": f.uncovered_lines,
                    "total": f.total_lines,
                }
                for f in sorted(metrics.files, key=lambda x: x.coverage_percent)
            ],
        }
        return json.dumps(report, indent=2)

    def generate_report(self, metrics: CoverageMetrics, format: str = "json") -> str:
        """Alias for generate_coverage_report."""
        return self.generate_coverage_report(metrics)
