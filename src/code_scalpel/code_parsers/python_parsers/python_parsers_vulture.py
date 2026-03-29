#!/usr/bin/env python3


"""
Vulture Parser - Dead Code Detection.
======================================

Vulture finds unused and unreachable code in Python programs. This is useful
for cleaning up codebases and identifying dead branches. This module provides
structured parsing of Vulture output.

Implementation Status: NOT IMPLEMENTED
Priority: P2 - HIGH
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class SourceLocation:
    """Location in source code."""

    line: int
    column: int = 0
    end_line: int | None = None
    end_column: int | None = None


@dataclass
class UnusedItem:
    """Represents an unused code item."""

    name: str
    item_type: str  # "import", "function", "class", "variable", "attribute", "argument"
    location: SourceLocation
    confidence: int  # 0-100
    message: str = ""


@dataclass
class VultureConfig:
    """Configuration for Vulture parser."""

    min_confidence: int = 80  # Only report items with confidence >= this
    exclude_patterns: list[str] = field(default_factory=list)
    check_unreachable_code: bool = True
    check_unused_arguments: bool = True

    @classmethod
    def from_pyproject(cls, pyproject_path: str | Path) -> "VultureConfig":
        """Load configuration from pyproject.toml."""
        return cls()

    @classmethod
    def from_file(cls, config_path: str | Path) -> "VultureConfig":
        """Load configuration from setup.cfg or .vulture.ini."""
        return cls()


@dataclass
class VultureReport:
    """Results from Vulture analysis."""

    file_path: str
    unused_imports: list[UnusedItem] = field(default_factory=list)
    unused_functions: list[UnusedItem] = field(default_factory=list)
    unused_classes: list[UnusedItem] = field(default_factory=list)
    unused_variables: list[UnusedItem] = field(default_factory=list)
    unused_attributes: list[UnusedItem] = field(default_factory=list)
    unused_arguments: list[UnusedItem] = field(default_factory=list)
    unreachable_code: list[UnusedItem] = field(default_factory=list)
    error: str | None = None

    @property
    def total_unused(self) -> int:
        """Total count of unused items."""
        return (
            len(self.unused_imports)
            + len(self.unused_functions)
            + len(self.unused_classes)
            + len(self.unused_variables)
            + len(self.unused_attributes)
            + len(self.unused_arguments)
            + len(self.unreachable_code)
        )


class VultureParser:

    def __init__(self, config: VultureConfig | None = None):
        """
        Initialize Vulture parser.

        Args:
            config: VultureConfig instance or None to use defaults
        """
        self.config = config or VultureConfig()

    def analyze_file(self, file_path: str | Path) -> VultureReport:
        """
        Find unused code in a Python file.

        Args:
            file_path: Path to Python file

        Returns:
            VultureReport with dead code findings

        """
        # [20260303_FEATURE] run vulture on file, build VultureReport from output
        path = Path(file_path)
        if not shutil.which("vulture"):
            return VultureReport(file_path=str(path), error="vulture not found")
        result = subprocess.run(
            ["vulture", str(path)],
            capture_output=True,
            text=True,
        )
        items = self.parse_output(result.stdout)
        report = VultureReport(file_path=str(path))
        cats = self.categorize_dead_code(items)
        report.unused_functions = cats.get("functions", [])
        report.unused_classes = cats.get("classes", [])
        report.unused_variables = cats.get("variables", [])
        report.unused_imports = cats.get("imports", [])
        report.unused_attributes = cats.get("attributes", [])
        report.unused_arguments = cats.get("arguments", [])
        return report

    def analyze_code(self, code: str, filename: str = "<string>") -> VultureReport:
        """
        Find unused code in Python code string.

        Args:
            code: Python source code
            filename: Filename for error reporting

        Returns:
            VultureReport with dead code findings

        """
        # [20260303_FEATURE] write to temp file, run vulture, build VultureReport
        if not shutil.which("vulture"):
            return VultureReport(file_path=filename, error="vulture not found")
        fd, tmp = tempfile.mkstemp(suffix=".py")
        try:
            os.write(fd, code.encode())
            os.close(fd)
            result = subprocess.run(["vulture", tmp], capture_output=True, text=True)
            items = self.parse_output(result.stdout)
            report = VultureReport(file_path=filename)
            cats = self.categorize_dead_code(items)
            report.unused_functions = cats.get("functions", [])
            report.unused_classes = cats.get("classes", [])
            report.unused_variables = cats.get("variables", [])
            report.unused_imports = cats.get("imports", [])
            report.unused_attributes = cats.get("attributes", [])
            report.unused_arguments = cats.get("arguments", [])
            return report
        finally:
            os.unlink(tmp)

    def load_config(self, config_path: str | Path) -> None:
        """
        Load configuration from Vulture config file.

        Args:
            config_path: Path to setup.cfg or .vulture.ini

        """
        # [20260303_FEATURE] read min_confidence from config file
        path = Path(config_path)
        if not path.exists():
            return
        content = path.read_text(encoding="utf-8")
        for line in content.splitlines():
            stripped = line.strip()
            if "min_confidence" in stripped:
                parts = stripped.split("=", 1)
                if len(parts) == 2:
                    try:
                        self.config.min_confidence = int(parts[1].strip())
                    except ValueError:
                        pass
                break

    def filter_by_confidence(
        self,
        report: VultureReport,
        min_confidence: int | None = None,
    ) -> VultureReport:
        """
        Filter report to only include items with sufficient confidence.

        Args:
            report: VultureReport to filter
            min_confidence: Minimum confidence (0-100) or use config default

        Returns:
            Filtered VultureReport

        """
        # [20260303_FEATURE] filter all UnusedItem lists by confidence threshold
        threshold = (
            min_confidence if min_confidence is not None else self.config.min_confidence
        )
        filtered = VultureReport(file_path=report.file_path, error=report.error)
        filtered.unused_imports = [
            i for i in report.unused_imports if i.confidence >= threshold
        ]
        filtered.unused_functions = [
            i for i in report.unused_functions if i.confidence >= threshold
        ]
        filtered.unused_classes = [
            i for i in report.unused_classes if i.confidence >= threshold
        ]
        filtered.unused_variables = [
            i for i in report.unused_variables if i.confidence >= threshold
        ]
        filtered.unused_attributes = [
            i for i in report.unused_attributes if i.confidence >= threshold
        ]
        filtered.unused_arguments = [
            i for i in report.unused_arguments if i.confidence >= threshold
        ]
        filtered.unreachable_code = [
            i for i in report.unreachable_code if i.confidence >= threshold
        ]
        return filtered

    # -------------------------------------------------------------------------
    # [20260303_FEATURE] New methods added per Stage 4a spec
    # -------------------------------------------------------------------------

    def execute_vulture(self, path: str = ".") -> list[UnusedItem]:
        """Run vulture on path; return [] if not available."""
        if not shutil.which("vulture"):
            return []
        result = subprocess.run(["vulture", path], capture_output=True, text=True)
        return self.parse_output(result.stdout)

    def parse_output(self, output: str) -> list[UnusedItem]:
        """Parse vulture text output into UnusedItem list."""
        pattern = re.compile(
            r"^(.+?):(\d+): unused (\w+)(?:\s+\w+)* '([^']+)' \((\d+)% confidence\)"
        )
        items: list[UnusedItem] = []
        for line in output.splitlines():
            m = pattern.match(line.strip())
            if m:
                _fname, lineno, itype, name, conf = (
                    m.group(1),
                    m.group(2),
                    m.group(3),
                    m.group(4),
                    m.group(5),
                )
                items.append(
                    UnusedItem(
                        name=name,
                        item_type=itype,
                        location=SourceLocation(line=int(lineno)),
                        confidence=int(conf),
                        message=line.strip(),
                    )
                )
        return items

    def categorize_dead_code(
        self, items: list[UnusedItem]
    ) -> dict[str, list[UnusedItem]]:
        """Bucket UnusedItems by type."""
        cats: dict[str, list[UnusedItem]] = {
            "functions": [],
            "classes": [],
            "variables": [],
            "imports": [],
            "attributes": [],
            "arguments": [],
            "other": [],
        }
        type_map = {
            "function": "functions",
            "class": "classes",
            "variable": "variables",
            "import": "imports",
            "attribute": "attributes",
            "argument": "arguments",
            "parameter": "arguments",
        }
        for item in items:
            bucket = type_map.get(item.item_type, "other")
            cats[bucket].append(item)
        return cats

    def generate_report(self, findings: list[UnusedItem], format: str = "json") -> str:
        """Return JSON report of unused code items."""
        items_list = [
            {
                "name": i.name,
                "type": i.item_type,
                "line": i.location.line,
                "confidence": i.confidence,
            }
            for i in findings
        ]
        return json.dumps(
            {"tool": "vulture", "total": len(findings), "items": items_list}, indent=2
        )
