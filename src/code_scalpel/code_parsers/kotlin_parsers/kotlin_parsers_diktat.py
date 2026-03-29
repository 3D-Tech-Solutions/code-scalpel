#!/usr/bin/env python3
"""diktat Parser — Kotlin style and quality checker integration.

[20260303_FEATURE] Phase 2: full implementation replacing NotImplementedError stubs.
"""

import json
import shutil
import subprocess
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


class DiktatSeverity(Enum):
    ERROR = "error"
    WARN = "warn"
    INFO = "info"


class DiktatRuleSet(Enum):
    STYLE = "style"
    COMMENTS = "comments"
    NAMING = "naming"
    SMELLS = "smells"
    POTENTIAL_BUGS = "potential-bugs"
    PERFORMANCE = "performance"


@dataclass
class DiktatViolation:
    rule_id: str
    rule_set: str
    message: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    column: Optional[int] = None
    severity: Optional[str] = None
    fix_available: bool = False


@dataclass
class DiktatConfig:
    config_file: Optional[Path] = None
    rules_enabled: List[str] = field(default_factory=list)
    rules_disabled: List[str] = field(default_factory=list)
    warnings_as_errors: bool = False


_RULE_SET_MAP: Dict[str, str] = {
    "STYLE": "style",
    "COMMENT": "comments",
    "NAMING": "naming",
    "CODE_SMELL": "smells",
    "BUG": "potential-bugs",
    "PERF": "performance",
}


def _infer_rule_set(rule_id: str) -> str:
    prefix = rule_id.split("_")[0].upper() if "_" in rule_id else rule_id.upper()
    return _RULE_SET_MAP.get(prefix, "style")


class DiktatParser:
    """Parser for diktat style and quality violations."""

    def __init__(self) -> None:
        self.violations: List[DiktatViolation] = []
        self.config: Optional[DiktatConfig] = None

    def parse_json_report(self, json_data: str) -> List[DiktatViolation]:
        """Parse diktat JSON report."""
        if not json_data or not json_data.strip():
            return []
        try:
            data = json.loads(json_data)
        except json.JSONDecodeError:
            return []
        results: List[DiktatViolation] = []
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict) and "violations" in item:
                    fp = item.get("fileName", item.get("file", ""))
                    for v in item.get("violations", []):
                        results.append(self._make_violation(v, fp))
                elif isinstance(item, dict) and "ruleId" in item:
                    results.append(self._make_violation(item, ""))
        elif isinstance(data, dict) and "violations" in data:
            for v in data["violations"]:
                results.append(self._make_violation(v, data.get("fileName", "")))
        self.violations = results
        return results

    def _make_violation(self, v: Dict[str, Any], file_path: str) -> DiktatViolation:
        rule_id = v.get("ruleId", v.get("rule", ""))
        return DiktatViolation(
            rule_id=rule_id,
            rule_set=v.get("ruleSet", _infer_rule_set(rule_id)),
            message=v.get("message", v.get("details", "")),
            file_path=v.get("fileName", v.get("file", file_path)) or file_path,
            line_number=int(v["line"]) if v.get("line") else None,
            column=int(v["column"]) if v.get("column") else None,
            severity=v.get("severity", "warn"),
            fix_available=bool(v.get("fixable", v.get("fix", False))),
        )

    def parse_config(self, config_path: Path) -> DiktatConfig:
        """Parse diktat YAML config."""
        config = DiktatConfig(config_file=config_path)
        try:
            import yaml  # type: ignore[import]

            raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
            for rule in raw.get("rules", []):
                name = rule.get("name", "")
                if rule.get("enabled", True):
                    config.rules_enabled.append(name)
                else:
                    config.rules_disabled.append(name)
            config.warnings_as_errors = bool(raw.get("warningsAsErrors", False))
        except Exception:
            pass
        self.config = config
        return config

    def execute_diktat(
        self, project_path: Path, format_code: bool = False
    ) -> Dict[str, Any]:
        """Execute diktat via Gradle or standalone binary."""
        gradlew = Path(project_path) / "gradlew"
        if not gradlew.exists() and not shutil.which("diktat"):
            return {"violations": [], "error": "diktat not found"}
        task = "diktatFix" if format_code else "diktat"
        cmd = (
            [str(gradlew), task] if gradlew.exists() else ["diktat", str(project_path)]
        )
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=120, cwd=str(project_path)
            )
        except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
            return {"violations": [], "error": str(exc)}
        report_path = (
            Path(project_path) / "build" / "reports" / "diktat" / "diktat.json"
        )
        if report_path.exists():
            violations = self.parse_json_report(report_path.read_text(encoding="utf-8"))
        else:
            violations = self.parse_json_report(result.stdout or result.stderr or "")
        return {"violations": violations, "error": None}

    def generate_fix_suggestions(self) -> List[str]:
        """Return fix suggestions for current violations."""
        suggestions: List[str] = []
        for v in self.violations:
            if v.fix_available:
                suggestions.append(
                    f"{v.file_path}:{v.line_number}: auto-fix available for {v.rule_id}"
                )
            else:
                suggestions.append(
                    f"{v.file_path}:{v.line_number}: manual fix — {v.message}"
                )
        return suggestions

    def compare_with_detekt(self, detekt_violations: List[Any]) -> Dict[str, Any]:
        """Compare diktat vs Detekt violations."""
        dk = {(v.rule_id, v.file_path, v.line_number) for v in self.violations}
        dt = {
            (
                getattr(d, "rule_id", ""),
                getattr(d, "file_path", ""),
                getattr(d, "line", None),
            )
            for d in detekt_violations
        }
        return {
            "diktat_only": len(dk - dt),
            "detekt_only": len(dt - dk),
            "overlap": len(dk & dt),
            "total_diktat": len(dk),
            "total_detekt": len(dt),
        }

    def generate_report(
        self, violations: Optional[List[DiktatViolation]] = None, format: str = "json"
    ) -> str:
        """Generate summary report."""
        vs = violations if violations is not None else self.violations
        if format == "json":
            return json.dumps(
                {
                    "tool": "diktat",
                    "total": len(vs),
                    "violations": [
                        {
                            "rule_id": v.rule_id,
                            "rule_set": v.rule_set,
                            "message": v.message,
                            "file": v.file_path,
                            "line": v.line_number,
                            "severity": v.severity,
                        }
                        for v in vs
                    ],
                },
                indent=2,
            )
        lines = [f"diktat: {len(vs)} violation(s)"]
        for v in vs:
            lines.append(
                f"  [{v.severity or 'warn'}] {v.file_path}:{v.line_number} — {v.rule_id}: {v.message}"
            )
        return "\n".join(lines)
