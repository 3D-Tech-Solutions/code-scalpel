#!/usr/bin/env python3
"""Konsist architecture validation parser.

[20260303_FEATURE] Phase 2: full implementation replacing NotImplementedError stubs.
"""

import json
import subprocess
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


class KonsistSeverity(Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class KonsistRuleType(Enum):
    NAMING = "naming"
    ARCHITECTURE = "architecture"
    DEPENDENCY = "dependency"
    LAYER = "layer"
    PACKAGE = "package"
    ANNOTATION = "annotation"
    MODIFIER = "modifier"
    OTHER = "other"


@dataclass
class KonsistViolation:
    rule_name: str
    rule_type: str
    message: str
    file_path: Optional[str] = None
    class_name: Optional[str] = None
    line_number: Optional[int] = None
    severity: str = KonsistSeverity.ERROR.value


@dataclass
class KonsistRule:
    name: str
    rule_type: str
    description: str
    enabled: bool = True
    severity: str = KonsistSeverity.ERROR.value


class KonsistParser:
    """Parser for Konsist architecture violations."""

    def __init__(self) -> None:
        self.violations: List[KonsistViolation] = []
        self.rules: List[KonsistRule] = []

    def parse_violations(self, violations: Any) -> List[KonsistViolation]:
        """Parse violations from JUnit XML string or a list of dicts."""
        if isinstance(violations, str):
            return self._parse_junit_xml(violations)
        if not isinstance(violations, list):
            return []
        result: List[KonsistViolation] = []
        for v in violations:
            rule_name = v.get("ruleName", v.get("rule", ""))
            result.append(
                KonsistViolation(
                    rule_name=rule_name,
                    rule_type=v.get("ruleType", KonsistRuleType.OTHER.value),
                    message=v.get("message", v.get("description", "")),
                    file_path=v.get("file", v.get("filePath")),
                    class_name=v.get("className"),
                    line_number=int(v["line"]) if v.get("line") else None,
                    severity=v.get("severity", KonsistSeverity.ERROR.value),
                )
            )
        self.violations = result
        return result

    def _parse_junit_xml(self, xml_content: str) -> List[KonsistViolation]:
        result: List[KonsistViolation] = []
        try:
            root = ET.fromstring(xml_content)
        except ET.ParseError:
            return result
        for tc in root.iter("testcase"):
            for failure in tc.iter("failure"):
                msg = failure.get("message", failure.text or "")
                result.append(
                    KonsistViolation(
                        rule_name=tc.get("name", "unknown"),
                        rule_type=KonsistRuleType.OTHER.value,
                        message=msg,
                        class_name=tc.get("classname"),
                    )
                )
        self.violations = result
        return result

    def parse_rules(self, rule_definitions: List[Dict[str, Any]]) -> List[KonsistRule]:
        rules: List[KonsistRule] = []
        for rd in rule_definitions:
            rules.append(
                KonsistRule(
                    name=rd.get("name", ""),
                    rule_type=rd.get("type", KonsistRuleType.OTHER.value),
                    description=rd.get("description", ""),
                    enabled=bool(rd.get("enabled", True)),
                    severity=rd.get("severity", KonsistSeverity.ERROR.value),
                )
            )
        self.rules = rules
        return rules

    def validate_architecture(self, project_path: Path) -> Dict[str, Any]:
        """Run Konsist tests via Gradle."""
        gradlew = Path(project_path) / "gradlew"
        if not gradlew.exists():
            return {"violations": [], "error": "gradlew not found"}
        cmd = [str(gradlew), "test", "--tests", "*Konsist*"]
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=300, cwd=str(project_path)
            )
        except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
            return {"violations": [], "error": str(exc)}
        # Try to find JUnit XML reports
        violations: List[KonsistViolation] = []
        report_dir = Path(project_path) / "build" / "reports" / "tests"
        for xml_file in report_dir.rglob("TEST-*.xml"):
            try:
                violations.extend(
                    self._parse_junit_xml(xml_file.read_text(encoding="utf-8"))
                )
            except OSError:
                pass
        if not violations:
            violations = self._parse_junit_xml(result.stdout + result.stderr)
        return {
            "violations": violations,
            "error": None,
            "return_code": result.returncode,
        }

    def generate_report(
        self,
        violations: Optional[List[KonsistViolation]] = None,
        format: str = "json",
    ) -> str:
        vs = violations if violations is not None else self.violations
        if format == "json":
            return json.dumps(
                {
                    "tool": "konsist",
                    "total": len(vs),
                    "violations": [
                        {
                            "rule": v.rule_name,
                            "type": v.rule_type,
                            "message": v.message,
                            "file": v.file_path,
                            "class": v.class_name,
                            "severity": v.severity,
                        }
                        for v in vs
                    ],
                },
                indent=2,
            )
        lines = [f"Konsist: {len(vs)} violation(s)"]
        for v in vs:
            lines.append(f"  [{v.severity}] {v.rule_name}: {v.message} ({v.file_path})")
        return "\n".join(lines)
