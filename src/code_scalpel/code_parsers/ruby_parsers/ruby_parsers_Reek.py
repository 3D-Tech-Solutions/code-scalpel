#!/usr/bin/env python3
"""
Reek Parser - Ruby Code Smell Detection.

[20260304_FEATURE] Full implementation of Reek parser for Ruby code quality analysis.
Reek is a tool that examines Ruby classes, modules and methods and reports any
code smells it finds.

Output format: reek --format json
"""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


class SmellType(Enum):
    """Reek code smell types."""

    DUPLICATED_CODE = "DuplicatedCode"
    LONG_METHOD = "LongMethod"
    FEATURE_ENVY = "FeatureEnvy"
    UNCOMMUNICATIVE_NAME = "UncommunicativeName"
    DATA_CLUMP = "DataClump"
    LONG_PARAMETER_LIST = "LongParameterList"
    NESTED_ITERATORS = "NestedIterators"
    TOO_MANY_METHODS = "TooManyMethods"
    TOO_MANY_STATEMENTS = "TooManyStatements"
    CONTROL_PARAMETER = "ControlParameter"
    MODULE_INITIALIZE = "ModuleInitialize"


@dataclass
class ReekSmell:
    """Represents a code smell detected by Reek."""

    smell_type: str
    message: str
    context: str
    file_path: str
    line_number: int
    column: int = 0
    severity: int = 1


@dataclass
class ReekConfig:
    """Reek configuration for analysis."""

    reek_version: str = "6.0.0"
    config_file: Optional[Path] = None
    excluded_dirs: List[str] = field(default_factory=list)
    enabled_smells: List[str] = field(default_factory=list)
    disabled_smells: List[str] = field(default_factory=list)
    max_duplications: int = 2


class ReekParser:
    """
    Parser for Reek code smell detection.

    [20260304_FEATURE] Implements execute + parse workflow for Reek JSON output.

    Detects code smells and design issues in Ruby code including
    duplicated code, long methods, and feature envy patterns.

    Graceful degradation: returns [] if reek is not installed.
    """

    def __init__(self) -> None:
        """Initialize Reek parser."""
        self.config = ReekConfig()

    def execute_reek(
        self, paths: List[Path], config: Optional[ReekConfig] = None
    ) -> List[ReekSmell]:
        """
        Run reek --format json on given paths.

        [20260304_FEATURE] Graceful degradation when reek not installed.
        """
        if shutil.which("reek") is None:
            return []
        cmd = ["reek", "--format", "json"] + [str(p) for p in paths]
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
            return self.parse_json_output(result.stdout)
        except (subprocess.TimeoutExpired, OSError):
            return []

    def parse_json_output(self, output: str) -> List[ReekSmell]:
        """
        Parse reek --format json output.

        [20260304_FEATURE] JSON format: [{"smell_type":...,"message":...,"context":...,"lines":[...]}]
        """
        if not output or not output.strip():
            return []
        try:
            data = json.loads(output)
        except json.JSONDecodeError:
            return []

        smells: List[ReekSmell] = []
        if not isinstance(data, list):
            return []
        for item in data:
            file_path = ""
            line_number = 0
            # Reek puts source_path and lines separately
            source = item.get("source", "")
            lines = item.get("lines", [0])
            if isinstance(lines, list) and lines:
                line_number = lines[0]
            smells.append(
                ReekSmell(
                    smell_type=item.get("smell_type", ""),
                    message=item.get("message", ""),
                    context=item.get("context", ""),
                    file_path=source,
                    line_number=line_number,
                )
            )
        return smells

    def parse_xml_report(self, report_path: Path) -> List[ReekSmell]:
        """
        Parse a saved Reek XML report file.

        [20260304_FEATURE] Parses basic XML format; falls back to empty list on error.
        """
        try:
            import xml.etree.ElementTree as ET

            tree = ET.parse(str(report_path))
            root = tree.getroot()
        except Exception:
            return []

        smells: List[ReekSmell] = []
        for elem in root.iter("smell"):
            smells.append(
                ReekSmell(
                    smell_type=elem.get("type", ""),
                    message=elem.get("message", elem.text or ""),
                    context=elem.get("context", ""),
                    file_path=elem.get("file", ""),
                    line_number=int(elem.get("line", 0)),
                )
            )
        return smells

    def load_config(self, config_file: Path) -> ReekConfig:
        """Load Reek configuration from .reek.yml."""
        cfg = ReekConfig()
        cfg.config_file = config_file
        return cfg

    def categorize_smells(self, smells: List[ReekSmell]) -> Dict[str, List[ReekSmell]]:
        """
        Group smells by type.

        [20260304_FEATURE] Returns dict mapping smell_type → list of ReekSmell.
        """
        categories: Dict[str, List[ReekSmell]] = {}
        for s in smells:
            categories.setdefault(s.smell_type, []).append(s)
        return categories

    def detect_duplicated_code(self, smells: List[ReekSmell]) -> List[ReekSmell]:
        """Filter DuplicatedCode smells."""
        return [s for s in smells if s.smell_type == SmellType.DUPLICATED_CODE.value]

    def detect_long_methods(self, smells: List[ReekSmell]) -> List[ReekSmell]:
        """Filter LongMethod smells."""
        return [s for s in smells if s.smell_type == SmellType.LONG_METHOD.value]

    def generate_report(self, smells: List[ReekSmell], format: str = "json") -> str:
        """
        Generate a structured JSON report of code smells.

        [20260304_FEATURE] Returns JSON string.
        """
        categories = self.categorize_smells(smells)
        report: Dict[str, Any] = {
            "tool": "reek",
            "total_smells": len(smells),
            "by_type": {t: len(s) for t, s in categories.items()},
            "smells": [
                {
                    "type": s.smell_type,
                    "message": s.message,
                    "context": s.context,
                    "file": s.file_path,
                    "line": s.line_number,
                }
                for s in smells
            ],
        }
        return json.dumps(report, indent=2)
