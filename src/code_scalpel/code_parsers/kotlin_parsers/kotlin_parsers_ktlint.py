#!/usr/bin/env python3
"""
ktlint Parser - Kotlin linter and formatter integration.

ktlint is an anti-bikeshedding Kotlin linter with built-in formatter.
It enforces the official Kotlin coding conventions and Android Kotlin Style Guide.

ktlint provides:
- Zero-configuration Kotlin linting
- Built-in code formatter
- Custom rule set support
- EditorConfig integration
- Baseline support
"""

import shutil
import json
import re
import subprocess
import tempfile
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional


class KtlintSeverity(Enum):
    """ktlint violation severity levels."""

    ERROR = "error"
    WARNING = "warning"


class KtlintRuleSet(Enum):
    """ktlint rule set categories."""

    STANDARD = "standard"
    EXPERIMENTAL = "experimental"
    CUSTOM = "custom"


@dataclass
class KtlintViolation:
    """Represents a single ktlint violation."""

    rule_id: str
    rule_set: str
    message: str
    severity: KtlintSeverity
    file_path: str
    line: int
    column: int
    can_be_auto_corrected: bool = False
    detail: Optional[str] = None

    @property
    def location(self) -> str:
        """Get formatted location string."""
        return f"{self.file_path}:{self.line}:{self.column}"

    @property
    def full_rule_id(self) -> str:
        """Get full rule ID including rule set."""
        return f"{self.rule_set}:{self.rule_id}"

    def get_docs_url(self) -> str:
        """Get documentation URL for the rule."""
        # ktlint standard rules documentation
        if self.rule_set == "standard":
            return f"https://pinterest.github.io/ktlint/latest/rules/standard/#{self.rule_id}"
        elif self.rule_set == "experimental":
            return f"https://pinterest.github.io/ktlint/latest/rules/experimental/#{self.rule_id}"
        return "https://pinterest.github.io/ktlint/latest/rules/"


@dataclass
class KtlintConfig:
    """ktlint configuration from .editorconfig."""

    # Indentation
    indent_size: int = 4
    indent_style: str = "space"  # "space" or "tab"

    # Max line length
    max_line_length: int = -1  # -1 means no limit

    # Disabled rules
    disabled_rules: list[str] = field(default_factory=list)

    # Experimental rules opt-in
    experimental_rules: bool = False

    # Android style
    android_style: bool = False

    # Code style
    code_style: str = "official"  # "official" or "android"

    # Additional ktlint-specific settings
    ktlint_settings: dict[str, Any] = field(default_factory=dict)


@dataclass
class KtlintReport:
    """Complete ktlint analysis report."""

    violations: list[KtlintViolation] = field(default_factory=list)
    config: Optional[KtlintConfig] = None
    files_checked: int = 0
    execution_time_ms: Optional[float] = None
    ktlint_version: Optional[str] = None

    @property
    def error_count(self) -> int:
        """Count of errors."""
        return sum(1 for v in self.violations if v.severity == KtlintSeverity.ERROR)

    @property
    def warning_count(self) -> int:
        """Count of warnings."""
        return sum(1 for v in self.violations if v.severity == KtlintSeverity.WARNING)

    @property
    def fixable_count(self) -> int:
        """Count of auto-fixable violations."""
        return sum(1 for v in self.violations if v.can_be_auto_corrected)

    @property
    def total_count(self) -> int:
        """Total violation count."""
        return len(self.violations)

    def by_rule(self) -> dict[str, list[KtlintViolation]]:
        """Group violations by rule ID."""
        result: dict[str, list[KtlintViolation]] = {}
        for violation in self.violations:
            key = violation.full_rule_id
            if key not in result:
                result[key] = []
            result[key].append(violation)
        return result

    def by_file(self) -> dict[str, list[KtlintViolation]]:
        """Group violations by file."""
        result: dict[str, list[KtlintViolation]] = {}
        for violation in self.violations:
            if violation.file_path not in result:
                result[violation.file_path] = []
            result[violation.file_path].append(violation)
        return result


class KtlintParser:
    """
    Parser for ktlint linter output.

    ktlint is a Kotlin linter and formatter. This parser can:
    - Parse ktlint JSON/text output
    - Execute ktlint via CLI
    - Parse .editorconfig for ktlint settings
    - Run formatter and generate diffs

    Example usage:
        parser = KtlintParser()

        # Parse existing report
        report = parser.parse_json_report('ktlint-report.json')

        # Run ktlint on files
        report = parser.check_file('src/main/kotlin/App.kt')

        # Format a file
        formatted = parser.format_file('src/main/kotlin/App.kt')

    """

    def __init__(self, ktlint_path: Optional[str] = None):
        """
        Initialize ktlint parser.

        :param ktlint_path: Path to ktlint executable or jar.
        """
        self._ktlint_path = ktlint_path or self._find_ktlint()

    @staticmethod
    def _split_rule(rule_value: str) -> tuple[str, str]:
        if ":" in rule_value:
            rule_set, rule_id = rule_value.split(":", 1)
            return rule_set or KtlintRuleSet.STANDARD.value, rule_id
        return KtlintRuleSet.STANDARD.value, rule_value

    @staticmethod
    def _coerce_severity(value: Optional[str]) -> KtlintSeverity:
        return KtlintSeverity.WARNING if (value or "").strip().lower() == "warning" else KtlintSeverity.ERROR

    def _make_violation(
        self,
        *,
        rule_value: str,
        message: str,
        file_path: str,
        line: int,
        column: int,
        severity: Optional[str] = None,
        can_be_auto_corrected: bool = False,
        detail: Optional[str] = None,
    ) -> KtlintViolation:
        rule_set, rule_id = self._split_rule(rule_value)
        return KtlintViolation(
            rule_id=rule_id,
            rule_set=rule_set,
            message=message,
            severity=self._coerce_severity(severity),
            file_path=file_path,
            line=line,
            column=column,
            can_be_auto_corrected=can_be_auto_corrected,
            detail=detail,
        )

    def _parse_json_payload(self, payload: Any) -> KtlintReport:
        report = KtlintReport()
        violations: list[KtlintViolation] = []

        if isinstance(payload, dict) and "violations" in payload:
            items = [payload]
        elif isinstance(payload, list):
            items = payload
        else:
            items = []

        files_seen: set[str] = set()
        for item in items:
            if not isinstance(item, dict):
                continue
            file_path = item.get("file") or item.get("filePath") or item.get("path") or ""
            if file_path:
                files_seen.add(file_path)
            for violation in item.get("violations", []):
                if not isinstance(violation, dict):
                    continue
                violations.append(
                    self._make_violation(
                        rule_value=violation.get("rule") or violation.get("ruleId") or "standard:unknown",
                        message=violation.get("message", ""),
                        file_path=file_path,
                        line=int(violation.get("line", 1)),
                        column=int(violation.get("column", 1)),
                        severity=violation.get("severity"),
                        can_be_auto_corrected=bool(
                            violation.get("canBeAutoCorrected", violation.get("fixable", False))
                        ),
                        detail=violation.get("detail"),
                    )
                )

        report.violations = violations
        report.files_checked = len(files_seen)
        return report

    def _run_ktlint_command(
        self,
        args: list[str],
        *,
        cwd: Optional[str] = None,
        stdin: Optional[str] = None,
    ) -> str:
        if self._ktlint_path is None:
            return ""
        cmd = [self._ktlint_path, *args]
        try:
            result = subprocess.run(
                cmd,
                input=stdin,
                capture_output=True,
                text=True,
                timeout=300,
                cwd=cwd,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            return ""
        return result.stdout or result.stderr or ""

    def _find_ktlint(self) -> Optional[str]:
        """Find ktlint executable."""
        # Check for ktlint in PATH
        ktlint = shutil.which("ktlint")
        if ktlint:
            return ktlint

        # Check for local installation
        local = Path("ktlint")
        if local.exists():
            return str(local)

        # Check for Gradle wrapper
        if Path("gradlew").exists():
            return "./gradlew"

        return None

    def parse_json_report(self, json_path: str) -> KtlintReport:
        """
        Parse ktlint JSON report.

        :param json_path: Path to ktlint JSON report.
        :return: KtlintReport with violations.

        """
        # [20260306_FEATURE] Support reading persisted ktlint JSON reports.
        try:
            payload = json.loads(Path(json_path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return KtlintReport()
        return self._parse_json_payload(payload)

    def parse_json_output(self, json_output: str) -> KtlintReport:
        """
        Parse ktlint JSON output string.

        :param json_output: ktlint JSON output.
        :return: KtlintReport with violations.

        """
        # [20260306_FEATURE] Support both array payloads and JSON-lines output.
        if not json_output.strip():
            return KtlintReport()
        try:
            payload = json.loads(json_output)
            return self._parse_json_payload(payload)
        except json.JSONDecodeError:
            payload: list[Any] = []
            for raw_line in json_output.splitlines():
                line = raw_line.strip()
                if not line:
                    continue
                try:
                    payload.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
            return self._parse_json_payload(payload)

    def parse_text_output(self, text: str) -> KtlintReport:
        """
        Parse ktlint plain text output.

        :param text: ktlint plain text output.
        :return: KtlintReport with violations.

        """
        # [20260306_FEATURE] Parse standard ktlint CLI output lines.
        report = KtlintReport()
        pattern = re.compile(
            r"^(?P<file>.+?):(?P<line>\d+):(?P<column>\d+):\s*"
            r"(?P<message>.+?)\s*\((?P<rule>[^)]+)\)$"
        )
        violations: list[KtlintViolation] = []
        files_seen: set[str] = set()
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            match = pattern.match(line)
            if not match:
                continue
            file_path = match.group("file")
            files_seen.add(file_path)
            violations.append(
                self._make_violation(
                    rule_value=match.group("rule"),
                    message=match.group("message"),
                    file_path=file_path,
                    line=int(match.group("line")),
                    column=int(match.group("column")),
                )
            )
        report.violations = violations
        report.files_checked = len(files_seen)
        return report

    def parse_editorconfig(self, config_path: str = ".editorconfig") -> KtlintConfig:
        """
        Parse .editorconfig for ktlint settings.

        :param config_path: Path to .editorconfig.
        :return: KtlintConfig object.

        """
        # [20260306_FEATURE] Parse common ktlint and IntelliJ Kotlin editorconfig keys.
        config = KtlintConfig()
        try:
            lines = Path(config_path).read_text(encoding="utf-8").splitlines()
        except OSError:
            return config

        for raw_line in lines:
            line = raw_line.strip()
            if not line or line.startswith(('#', ';', '[')) or '=' not in line:
                continue
            key, value = [part.strip() for part in line.split('=', 1)]
            lowered = value.lower()
            if key == 'indent_size' and value.isdigit():
                config.indent_size = int(value)
            elif key == 'indent_style':
                config.indent_style = value
            elif key == 'max_line_length' and re.fullmatch(r'-?\d+', value):
                config.max_line_length = int(value)
            elif key == 'ktlint_experimental':
                config.experimental_rules = lowered == 'enabled'
            elif key == 'ktlint_android':
                config.android_style = lowered == 'enabled'
            elif key == 'ktlint_code_style':
                config.code_style = value
            elif key == 'ktlint_disabled_rules':
                config.disabled_rules.extend(rule.strip() for rule in value.split(',') if rule.strip())
            else:
                config.ktlint_settings[key] = value
        return config

    def check_file(
        self,
        file_path: str,
        config_path: Optional[str] = None,
    ) -> KtlintReport:
        """
        Run ktlint on a single file.

        :param file_path: Path to Kotlin file.
        :param config_path: Optional path to .editorconfig.
        :return: KtlintReport with violations.

        """
        # [20260306_FEATURE] Run ktlint on a single file when available.
        report = KtlintReport()
        if config_path:
            report.config = self.parse_editorconfig(config_path)
        output = self._run_ktlint_command(
            ["--reporter=json", file_path],
            cwd=str(Path(file_path).parent),
        )
        return self.parse_json_output(output) if output else report

    def check_code(
        self,
        code: str,
        filename: str = "input.kt",
    ) -> KtlintReport:
        """
        Run ktlint on code string via stdin.

        :param code: Kotlin source code.
        :param filename: Virtual filename for reporting.
        :return: KtlintReport with violations.

        """
        # [20260306_FEATURE] Use a temporary file so ktlint can report stable locations.
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_path = Path(tmpdir) / filename
            temp_path.write_text(code, encoding="utf-8")
            report = self.check_file(str(temp_path))
            for violation in report.violations:
                violation.file_path = filename
            return report

    def check_directory(
        self,
        directory: str,
        patterns: Optional[list[str]] = None,
    ) -> KtlintReport:
        """
        Run ktlint on a directory.

        :param directory: Path to directory.
        :param patterns: Optional glob patterns to include.
        :return: KtlintReport with violations.

        """
        # [20260306_FEATURE] Run ktlint across a directory, optionally with explicit glob patterns.
        report = KtlintReport()
        args = ["--reporter=json"]
        if patterns:
            args.extend(patterns)
        else:
            args.append(directory)
        output = self._run_ktlint_command(args, cwd=directory)
        return self.parse_json_output(output) if output else report

    # [20260306_FEATURE] Adapter used by shared MCP static-tool dispatch.
    def execute_ktlint(self, project_path: Path) -> list[KtlintViolation]:
        """Return ktlint violations for a file or project path."""
        path = Path(project_path)
        if path.is_dir():
            report = self.check_directory(str(path))
        else:
            report = self.check_file(str(path))
        return report.violations

    def format_file(
        self,
        file_path: str,
        dry_run: bool = False,
    ) -> tuple[str, bool]:
        """
        Format a Kotlin file.

        :param file_path: Path to Kotlin file.
        :param dry_run: If True, don't write changes.
        :return: Tuple of (formatted_code, was_modified).

        """
        # [20260306_FEATURE] Format a file in place when ktlint is available; otherwise return original content.
        path = Path(file_path)
        original = path.read_text(encoding="utf-8")
        if self._ktlint_path is None:
            return original, False

        if dry_run:
            formatted, was_modified = self.format_code(original)
            return formatted, was_modified

        self._run_ktlint_command(["-F", file_path], cwd=str(path.parent))
        updated = path.read_text(encoding="utf-8")
        return updated, updated != original

    def format_code(self, code: str) -> tuple[str, bool]:
        """
        Format Kotlin code string.

        :param code: Kotlin source code.
        :return: Tuple of (formatted_code, was_modified).

        """
        # [20260306_FEATURE] Best-effort formatter wrapper using a temporary Kotlin file.
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_path = Path(tmpdir) / "input.kt"
            temp_path.write_text(code, encoding="utf-8")
            formatted, was_modified = self.format_file(str(temp_path), dry_run=False)
            return formatted, was_modified

    def get_fixable_violations(self, report: KtlintReport) -> list[KtlintViolation]:
        """Get violations that can be auto-fixed."""
        return [v for v in report.violations if v.can_be_auto_corrected]

    def generate_baseline(
        self,
        directory: str,
        output_path: str = ".ktlint-baseline.xml",
    ) -> str:
        """
        Generate a baseline file for existing violations.

        :param directory: Directory to analyze.
        :param output_path: Output path for baseline file.
        :return: Path to generated baseline file.

        """
        # [20260306_FEATURE] Generate a minimal baseline file when CLI support is unavailable.
        baseline_path = Path(output_path)
        if self._ktlint_path is not None:
            self._run_ktlint_command(
                [f"--baseline={baseline_path}", directory],
                cwd=directory,
            )
        if not baseline_path.exists():
            baseline_path.write_text(
                "<?xml version=\"1.0\" encoding=\"UTF-8\"?><baseline/>",
                encoding="utf-8",
            )
        return str(baseline_path)
