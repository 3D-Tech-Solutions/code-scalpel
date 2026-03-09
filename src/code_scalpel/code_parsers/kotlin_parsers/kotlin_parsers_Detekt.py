#!/usr/bin/env python3
"""
Detekt Parser - Kotlin static code analysis integration.

Detekt is a static code analysis tool for Kotlin that finds code smells,
complexity issues, and potential bugs. This parser integrates with Detekt
for comprehensive Kotlin code quality analysis.

Detekt provides:
- Code smell detection (complexity, style, potential bugs)
- Customizable rule sets
- Baseline support for legacy code
- Multiple output formats (XML, HTML, SARIF, plain text)
"""

import shutil
import json
import re
import subprocess
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional


class DetektSeverity(Enum):
    """Detekt finding severity levels."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    STYLE = "style"


class DetektRuleSet(Enum):
    """Detekt rule set categories."""

    COMPLEXITY = "complexity"
    COROUTINES = "coroutines"
    EMPTY_BLOCKS = "empty-blocks"
    EXCEPTIONS = "exceptions"
    NAMING = "naming"
    PERFORMANCE = "performance"
    POTENTIAL_BUGS = "potential-bugs"
    STYLE = "style"
    COMMENTS = "comments"
    FORMATTING = "formatting"


@dataclass
class DetektFinding:
    """Represents a single Detekt finding."""

    rule_id: str
    rule_set: str
    message: str
    severity: DetektSeverity
    file_path: str
    line: int
    column: int
    end_line: Optional[int] = None
    end_column: Optional[int] = None
    snippet: Optional[str] = None
    documentation_url: Optional[str] = None

    @property
    def location(self) -> str:
        """Get formatted location string."""
        return f"{self.file_path}:{self.line}:{self.column}"

    @property
    def is_error(self) -> bool:
        """Check if finding is an error."""
        return self.severity == DetektSeverity.ERROR


@dataclass
class DetektConfig:
    """Detekt configuration representation."""

    # Build configuration
    build_upon_default_config: bool = True
    parallel: bool = True
    fail_fast: bool = False

    # Thresholds
    max_issues: int = 0
    exclude_correctable: bool = False

    # Rule sets enabled
    rule_sets: dict[str, bool] = field(default_factory=dict)

    # Rule overrides
    rules: dict[str, dict[str, Any]] = field(default_factory=dict)

    # Exclude patterns
    excludes: list[str] = field(default_factory=list)
    includes: list[str] = field(default_factory=list)


@dataclass
class DetektReport:
    """Complete Detekt analysis report."""

    findings: list[DetektFinding] = field(default_factory=list)
    config: Optional[DetektConfig] = None
    execution_time_ms: Optional[float] = None
    kotlin_version: Optional[str] = None
    detekt_version: Optional[str] = None

    @property
    def error_count(self) -> int:
        """Count of error-level findings."""
        return sum(1 for f in self.findings if f.severity == DetektSeverity.ERROR)

    @property
    def warning_count(self) -> int:
        """Count of warning-level findings."""
        return sum(1 for f in self.findings if f.severity == DetektSeverity.WARNING)

    @property
    def total_count(self) -> int:
        """Total finding count."""
        return len(self.findings)

    def by_rule_set(self) -> dict[str, list[DetektFinding]]:
        """Group findings by rule set."""
        result: dict[str, list[DetektFinding]] = {}
        for finding in self.findings:
            if finding.rule_set not in result:
                result[finding.rule_set] = []
            result[finding.rule_set].append(finding)
        return result

    def by_file(self) -> dict[str, list[DetektFinding]]:
        """Group findings by file."""
        result: dict[str, list[DetektFinding]] = {}
        for finding in self.findings:
            if finding.file_path not in result:
                result[finding.file_path] = []
            result[finding.file_path].append(finding)
        return result


class DetektParser:
    """
    Parser for Detekt static analysis output.

    Detekt is a static code analysis tool for Kotlin. This parser can:
    - Parse Detekt XML/SARIF/text output
    - Execute Detekt via CLI
    - Parse detekt.yml configuration
    - Generate baseline files

    Example usage:
        parser = DetektParser()

        # Parse existing report
        report = parser.parse_xml_report('build/reports/detekt/detekt.xml')

        # Run Detekt on a project
        report = parser.analyze_project('/path/to/kotlin/project')

        # Get findings by severity
        errors = [f for f in report.findings if f.is_error]

    """

    def __init__(self, detekt_path: Optional[str] = None):
        """
        Initialize Detekt parser.

        :param detekt_path: Path to Detekt CLI jar or script.
        """
        self._detekt_path = detekt_path or self._find_detekt()

    @staticmethod
    def _coerce_severity(value: Optional[str]) -> DetektSeverity:
        normalized = (value or "warning").strip().lower()
        if normalized in {"error", "errors"}:
            return DetektSeverity.ERROR
        if normalized in {"info", "informational"}:
            return DetektSeverity.INFO
        if normalized in {"style", "code_smell", "code-smell"}:
            return DetektSeverity.STYLE
        return DetektSeverity.WARNING

    @staticmethod
    def _infer_rule_set(rule_id: str, source: Optional[str] = None) -> str:
        for candidate in (source or "", rule_id):
            lowered = candidate.lower()
            for rule_set in DetektRuleSet:
                if rule_set.value in lowered:
                    return rule_set.value
        return DetektRuleSet.STYLE.value

    def _make_finding(
        self,
        *,
        rule_id: str,
        message: str,
        severity: Optional[str],
        file_path: str,
        line: int,
        column: int,
        end_line: Optional[int] = None,
        end_column: Optional[int] = None,
        snippet: Optional[str] = None,
        documentation_url: Optional[str] = None,
        source: Optional[str] = None,
    ) -> DetektFinding:
        return DetektFinding(
            rule_id=rule_id,
            rule_set=self._infer_rule_set(rule_id, source),
            message=message,
            severity=self._coerce_severity(severity),
            file_path=file_path,
            line=line,
            column=column,
            end_line=end_line,
            end_column=end_column,
            snippet=snippet,
            documentation_url=documentation_url,
        )

    def _parse_inline_yaml_value(self, value: str) -> Any:
        normalized = value.strip().strip('"\'')
        lowered = normalized.lower()
        if lowered in {"true", "false"}:
            return lowered == "true"
        if lowered in {"[]", "{}"}:
            return [] if lowered == "[]" else {}
        if normalized.startswith("[") and normalized.endswith("]"):
            return [item.strip().strip('"\'') for item in normalized[1:-1].split(",") if item.strip()]
        if re.fullmatch(r"-?\d+", normalized):
            return int(normalized)
        return normalized

    def _run_detekt_command(self, args: list[str], cwd: Optional[str] = None) -> str:
        if self._detekt_path is None:
            return ""
        cmd = [self._detekt_path]
        if Path(self._detekt_path).name == "gradlew" or self._detekt_path.endswith("gradlew"):
            cmd.extend(["detekt", *args])
        else:
            cmd.extend(args)
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
                cwd=cwd,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            return ""
        return result.stdout or result.stderr or ""

    def _find_detekt(self) -> Optional[str]:
        """Find Detekt executable."""
        # Check for detekt CLI in PATH
        detekt = shutil.which("detekt")
        if detekt:
            return detekt

        # Check for Gradle wrapper
        if Path("gradlew").exists():
            return "./gradlew"

        return None

    def parse_xml_report(self, xml_path: str) -> DetektReport:
        """
        Parse Detekt XML report.

        :param xml_path: Path to Detekt XML report file.
        :return: DetektReport with findings.

        """
        # [20260306_FEATURE] Support Detekt checkstyle-style XML reports.
        report = DetektReport()
        try:
            tree = ET.parse(xml_path)
        except (ET.ParseError, FileNotFoundError, OSError):
            return report

        root = tree.getroot()
        findings: list[DetektFinding] = []
        for file_elem in root.findall(".//file"):
            file_path = file_elem.get("name", "")
            for error_elem in file_elem.findall("error"):
                source = error_elem.get("source", "")
                rule_id = source.split(".")[-1] if source else error_elem.get("rule", "unknown")
                findings.append(
                    self._make_finding(
                        rule_id=rule_id,
                        message=error_elem.get("message", ""),
                        severity=error_elem.get("severity"),
                        file_path=file_path,
                        line=int(error_elem.get("line", 1)),
                        column=int(error_elem.get("column", 1)),
                        source=source,
                    )
                )

        report.findings = findings
        return report

    def parse_sarif_report(self, sarif_path: str) -> DetektReport:
        """
        Parse Detekt SARIF report.

        :param sarif_path: Path to Detekt SARIF report file.
        :return: DetektReport with findings.

        """
        # [20260306_FEATURE] Support SARIF output used by CI integrations.
        report = DetektReport()
        try:
            data = json.loads(Path(sarif_path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return report

        findings: list[DetektFinding] = []
        for run in data.get("runs", []):
            for result in run.get("results", []):
                location = (result.get("locations") or [{}])[0].get("physicalLocation", {})
                region = location.get("region", {})
                artifact = location.get("artifactLocation", {})
                findings.append(
                    self._make_finding(
                        rule_id=result.get("ruleId", "unknown"),
                        message=result.get("message", {}).get("text", ""),
                        severity=result.get("level"),
                        file_path=artifact.get("uri", ""),
                        line=int(region.get("startLine", 1)),
                        column=int(region.get("startColumn", 1)),
                        end_line=region.get("endLine"),
                        end_column=region.get("endColumn"),
                    )
                )

        report.findings = findings
        return report

    def parse_text_report(self, text: str) -> DetektReport:
        """
        Parse Detekt plain text output.

        :param text: Detekt plain text output.
        :return: DetektReport with findings.

        """
        # [20260306_FEATURE] Parse CLI text like path:line:col: severity: message [RuleId].
        report = DetektReport()
        findings: list[DetektFinding] = []
        pattern = re.compile(
            r"^(?P<file>.+?):(?P<line>\d+):(?P<column>\d+):\s*"
            r"(?:(?P<severity>error|warning|info|style):\s*)?"
            r"(?P<message>.+?)\s*\[(?P<rule>[^\]]+)\]$",
            re.IGNORECASE,
        )
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            match = pattern.match(line)
            if not match:
                continue
            findings.append(
                self._make_finding(
                    rule_id=match.group("rule"),
                    message=match.group("message"),
                    severity=match.group("severity"),
                    file_path=match.group("file"),
                    line=int(match.group("line")),
                    column=int(match.group("column")),
                )
            )
        report.findings = findings
        return report

    def parse_config(self, config_path: str = "detekt.yml") -> DetektConfig:
        """
        Parse Detekt configuration file.

        :param config_path: Path to detekt.yml.
        :return: DetektConfig object.

        """
        # [20260306_FEATURE] Best-effort parser for common detekt.yml keys.
        config = DetektConfig()
        path = Path(config_path)
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            return config

        section_stack: list[tuple[int, str]] = []
        current_rule_set: Optional[str] = None
        current_rule: Optional[str] = None

        for raw_line in lines:
            if not raw_line.strip() or raw_line.lstrip().startswith("#"):
                continue

            indent = len(raw_line) - len(raw_line.lstrip(" "))
            stripped = raw_line.strip()

            if stripped.startswith("- "):
                item = stripped[2:].strip().strip('"\'')
                if section_stack:
                    current_section = section_stack[-1][1]
                    if current_section == "excludes":
                        config.excludes.append(item)
                    elif current_section == "includes":
                        config.includes.append(item)
                continue

            while section_stack and indent <= section_stack[-1][0]:
                popped = section_stack.pop()
                if popped[1] == current_rule:
                    current_rule = None
                if popped[1] == current_rule_set:
                    current_rule_set = None

            key, _, raw_value = stripped.partition(":")
            key = key.strip().strip('"\'')
            value = raw_value.strip()

            if not value:
                section_stack.append((indent, key))
                if key in {rule_set.value for rule_set in DetektRuleSet}:
                    current_rule_set = key
                    config.rule_sets.setdefault(key, True)
                elif current_rule_set is not None:
                    current_rule = key
                    config.rules.setdefault(current_rule_set, {}).setdefault(current_rule, {})
                continue

            parsed_value = self._parse_inline_yaml_value(value)
            if key == "build":
                continue
            if key == "buildUponDefaultConfig":
                config.build_upon_default_config = bool(parsed_value)
            elif key == "parallel":
                config.parallel = bool(parsed_value)
            elif key == "failFast":
                config.fail_fast = bool(parsed_value)
            elif key == "maxIssues":
                config.max_issues = int(parsed_value)
            elif key == "excludeCorrectable":
                config.exclude_correctable = bool(parsed_value)
            elif key == "active" and current_rule_set and current_rule is None:
                config.rule_sets[current_rule_set] = bool(parsed_value)
            elif key == "active" and current_rule_set and current_rule:
                config.rules[current_rule_set].setdefault(current_rule, {})[key] = bool(parsed_value)
            elif key in {"includes", "excludes"} and isinstance(parsed_value, list):
                target = config.includes if key == "includes" else config.excludes
                target.extend(str(item) for item in parsed_value)
            elif current_rule_set and current_rule:
                config.rules[current_rule_set].setdefault(current_rule, {})[key] = parsed_value

        return config

    def analyze_project(
        self,
        project_path: str,
        config_path: Optional[str] = None,
    ) -> DetektReport:
        """
        Run Detekt on a Kotlin project.

        :param project_path: Path to Kotlin project.
        :param config_path: Optional path to detekt.yml.
        :return: DetektReport with findings.

        """
        # [20260306_FEATURE] Gracefully execute Detekt when available; otherwise return an empty report.
        report = DetektReport()
        if config_path:
            report.config = self.parse_config(config_path)
        output = self._run_detekt_command(
            ["--input", project_path, "--report", "txt:stdout", *( ["--config", config_path] if config_path else [])],
            cwd=project_path,
        )
        if output:
            return self.parse_text_report(output)
        return report

    def analyze_file(self, file_path: str) -> DetektReport:
        """
        Run Detekt on a single file.

        :param file_path: Path to Kotlin file.
        :return: DetektReport with findings.

        """
        # [20260306_FEATURE] Single-file analysis shares the same CLI parser path as project analysis.
        output = self._run_detekt_command(["--input", file_path, "--report", "txt:stdout"], cwd=str(Path(file_path).parent))
        if output:
            return self.parse_text_report(output)
        return DetektReport()

    # [20260306_FEATURE] Adapter used by shared MCP static-tool dispatch.
    def execute_detekt(self, project_path: Path) -> list[DetektFinding]:
        """Return Detekt findings for a file or project path."""
        path = Path(project_path)
        if path.is_dir():
            report = self.analyze_project(str(path))
        else:
            report = self.analyze_file(str(path))
        return report.findings

    def generate_baseline(
        self,
        project_path: str,
        output_path: str = "detekt-baseline.xml",
    ) -> str:
        """
        Generate a baseline file for existing issues.

        :param project_path: Path to Kotlin project.
        :param output_path: Output path for baseline file.
        :return: Path to generated baseline file.

        """
        # [20260306_FEATURE] Emit an empty baseline when the CLI is unavailable and return its path.
        baseline_path = Path(output_path)
        output = self._run_detekt_command(
            ["--input", project_path, "--create-baseline", str(baseline_path)],
            cwd=project_path,
        )
        if not baseline_path.exists():
            baseline_path.write_text(
                "<?xml version=\"1.0\" encoding=\"UTF-8\"?><SmellBaseline><ManuallySuppressedIssues/></SmellBaseline>",
                encoding="utf-8",
            )
        if output:
            return str(baseline_path)
        return str(baseline_path)
