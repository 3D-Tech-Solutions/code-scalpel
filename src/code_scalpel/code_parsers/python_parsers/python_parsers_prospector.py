#!/usr/bin/env python3
"""
Python Meta-Linter - Prospector Integration.
=============================================

This module provides comprehensive code analysis using Prospector,
a meta-linter that aggregates results from multiple Python linting tools.

Implementation Status: MOSTLY COMPLETED
Priority: P5 - LOW

Features:
    - Aggregated linting from multiple tools
    - Unified message format
    - Profile-based configuration
    - Tool enable/disable control

Integrated Tools:
    - pylint
    - pyflakes
    - pycodestyle (pep8)
    - pydocstyle (pep257)
    - mccabe (complexity)
    - dodgy (security)
    - bandit (optional)
    - mypy (optional)
    - vulture (dead code, optional)

==============================================================================
MOSTLY COMPLETED [P5-PROSPECTOR-001]: Prospector integration
==============================================================================
Priority: LOW
Status: ✓ MOSTLY COMPLETED

Implemented Features:
    - [✓] Run prospector via subprocess
    - [✓] Parse JSON output format (_parse_json_output method)
    - [✓] Support profile configuration (--profile, --profile-path flags)
    - [✓] Support tool enable/disable (with-tool/without-tool)
    - [✓] Support strictness levels (all 5 levels)
    - [✓] Command building (_build_command with all options)
    - [✓] Timeout handling for large codebases

Strictness Levels:
    - verylow: Only severe issues
    - low: Major issues
    - medium: Standard checking (default)
    - high: Thorough checking
    - veryhigh: Maximum checking

==============================================================================
==============================================================================
Priority: LOW
Status: ✅ COMPLETED
Estimated Effort: 0.5 days
Depends On: P5-PROSPECTOR-001

Requirements:
    - [x] Load profiles from .prospector.yaml
    - [x] Support built-in profiles (django, flask, etc.)
    - [x] Merge profile configurations
    - [x] Custom profile creation

Implementation:
    - ProspectorProfile dataclass - Represents loaded profile
    - ProspectorProfileLoader - Loads and parses .prospector.yaml files
    - create_profile() - Creates profile dict for writing
    - merge_profiles() - Merges multiple profiles with priority
    - BUILTIN_PROFILES - Dictionary of built-in profile configurations

Built-in Profiles:
    - default: Standard Python linting
    - django: Django-specific rules
    - flask: Flask-specific rules
    - no_doc_warnings: Disable documentation warnings
    - strictness_*: Preset strictness levels

==============================================================================
==============================================================================
Priority: LOW
Status: ✅ COMPLETED
Estimated Effort: 0.5 days
Depends On: P5-PROSPECTOR-001

Requirements:
    - [x] Identify duplicate messages from different tools
    - [x] Merge or dedupe similar messages
    - [x] Track message origin (which tool) - already tracked in source field
    - [x] Provide unified severity mapping - already implemented in _map_severity()

Implementation:
    - deduplicate_messages() - Main deduplication method
    - _get_dedup_key() - Normalizes error codes across tools
    - _severity_rank() - Ranks severity for keeping highest priority
    - get_unique_issues() - Semantic alias for deduplicate_messages()
    - duplicate_count property - Number of duplicates detected
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any

try:
    import yaml

    HAS_YAML = True
except ImportError:
    yaml = None  # type: ignore[assignment]
    HAS_YAML = False

if TYPE_CHECKING:
    pass


# =============================================================================
# Enums
# =============================================================================


class Strictness(Enum):
    """Prospector strictness levels."""

    VERY_LOW = "verylow"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "veryhigh"


class ProspectorTool(Enum):
    """Tools that Prospector can use."""

    PYLINT = "pylint"
    PYFLAKES = "pyflakes"
    PYCODESTYLE = "pycodestyle"
    PYDOCSTYLE = "pydocstyle"
    MCCABE = "mccabe"
    DODGY = "dodgy"
    BANDIT = "bandit"
    MYPY = "mypy"
    VULTURE = "vulture"
    FROSTED = "frosted"
    PROFILE_VALIDATOR = "profile-validator"


class MessageSeverity(Enum):
    """Unified message severity levels."""

    INFO = "info"
    REFACTOR = "refactor"
    CONVENTION = "convention"
    WARNING = "warning"
    ERROR = "error"
    FATAL = "fatal"


# =============================================================================
# Configuration
# =============================================================================


@dataclass
class ProspectorConfig:
    """Configuration for Prospector execution."""

    strictness: Strictness = Strictness.MEDIUM
    profile: str | None = None
    profile_path: str | None = None

    # Tool control
    with_tools: list[ProspectorTool] = field(default_factory=list)
    without_tools: list[ProspectorTool] = field(default_factory=list)

    # Filtering
    ignore_paths: list[str] = field(default_factory=list)
    ignore_patterns: list[str] = field(default_factory=list)

    # Options
    uses: list[str] = field(default_factory=list)  # e.g., ["django", "celery"]
    doc_warnings: bool = True
    test_warnings: bool = True
    no_autodetect: bool = False
    max_line_length: int | None = None

    # Output
    output_format: str = "json"
    show_profile: bool = False
    extra_args: list[str] = field(default_factory=list)


@dataclass
class ProspectorProfile:
    """Represents a loaded Prospector profile."""

    name: str
    strictness: Strictness = Strictness.MEDIUM
    doc_warnings: bool = True
    test_warnings: bool = True
    max_line_length: int = 100
    autodetect: bool = True

    # Tool configurations
    enabled_tools: list[ProspectorTool] = field(default_factory=list)
    disabled_tools: list[ProspectorTool] = field(default_factory=list)
    tool_options: dict[str, dict[str, Any]] = field(default_factory=dict)

    # Ignore patterns
    ignore_paths: list[str] = field(default_factory=list)
    ignore_patterns: list[str] = field(default_factory=list)

    # Pylint specific
    pylint_disabled: list[str] = field(default_factory=list)

    # Parent profiles to inherit from
    inherits: list[str] = field(default_factory=list)

    def to_config(self) -> ProspectorConfig:
        """Convert profile to ProspectorConfig."""
        return ProspectorConfig(
            strictness=self.strictness,
            profile=self.name,
            with_tools=self.enabled_tools,
            without_tools=self.disabled_tools,
            ignore_paths=self.ignore_paths,
            ignore_patterns=self.ignore_patterns,
            doc_warnings=self.doc_warnings,
            test_warnings=self.test_warnings,
            no_autodetect=not self.autodetect,
            max_line_length=self.max_line_length,
        )


# Built-in profile configurations
BUILTIN_PROFILES: dict[str, dict[str, Any]] = {
    "default": {
        "strictness": "medium",
        "doc-warnings": True,
        "test-warnings": True,
        "autodetect": True,
    },
    "django": {
        "strictness": "medium",
        "doc-warnings": True,
        "uses": ["django"],
        "pylint": {
            "disabled": [
                "no-member",
                "missing-docstring",
            ],
        },
    },
    "flask": {
        "strictness": "medium",
        "doc-warnings": True,
        "uses": ["flask"],
        "pylint": {
            "disabled": [
                "no-member",
            ],
        },
    },
    "no_doc_warnings": {
        "doc-warnings": False,
        "pydocstyle": {
            "run": False,
        },
    },
    "strictness_high": {
        "strictness": "high",
        "doc-warnings": True,
        "test-warnings": True,
    },
    "strictness_very_high": {
        "strictness": "veryhigh",
        "doc-warnings": True,
        "test-warnings": True,
    },
    "strictness_low": {
        "strictness": "low",
        "doc-warnings": False,
        "test-warnings": False,
    },
}


class ProspectorProfileLoader:
    """
    Loader for Prospector profile files.

    Supports loading from:
    - .prospector.yaml / .prospector.yml
    - pyproject.toml [tool.prospector]
    - Built-in profiles
    """

    @classmethod
    def load(cls, path: str | Path) -> ProspectorProfile:
        """
        Load a profile from a file.

        Args:
            path: Path to .prospector.yaml or similar.

        Returns:
            Loaded ProspectorProfile.

        Raises:
            FileNotFoundError: If file doesn't exist.
            ValueError: If YAML parsing fails or yaml not installed.
        """
        if not HAS_YAML or yaml is None:
            raise ValueError("PyYAML is required for loading Prospector profiles. " "Install with: pip install pyyaml")

        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Profile file not found: {path}")

        with path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if not isinstance(data, dict):
            raise ValueError(f"Invalid profile format in {path}")

        return cls._from_dict(data, path.stem)

    @classmethod
    def load_builtin(cls, name: str) -> ProspectorProfile:
        """
        Load a built-in profile by name.

        Args:
            name: Name of built-in profile (default, django, flask, etc.)

        Returns:
            ProspectorProfile for the built-in.

        Raises:
            ValueError: If profile name is not recognized.
        """
        if name not in BUILTIN_PROFILES:
            available = ", ".join(BUILTIN_PROFILES.keys())
            raise ValueError(f"Unknown built-in profile: {name}. " f"Available: {available}")

        return cls._from_dict(BUILTIN_PROFILES[name], name)

    @classmethod
    def _from_dict(cls, data: dict[str, Any], name: str) -> ProspectorProfile:
        """Create profile from dictionary."""
        profile = ProspectorProfile(name=name)

        # Parse strictness
        if "strictness" in data:
            try:
                profile.strictness = Strictness(data["strictness"])
            except ValueError:
                pass

        # Parse boolean options
        profile.doc_warnings = data.get("doc-warnings", True)
        profile.test_warnings = data.get("test-warnings", True)
        profile.autodetect = data.get("autodetect", True)

        # Parse max line length
        if "max-line-length" in data:
            profile.max_line_length = int(data["max-line-length"])

        # Parse ignore patterns
        if "ignore-paths" in data:
            paths = data["ignore-paths"]
            profile.ignore_paths = paths if isinstance(paths, list) else [paths]

        if "ignore-patterns" in data:
            patterns = data["ignore-patterns"]
            profile.ignore_patterns = patterns if isinstance(patterns, list) else [patterns]

        # Parse inherits
        if "inherits" in data:
            inherits = data["inherits"]
            profile.inherits = inherits if isinstance(inherits, list) else [inherits]

        # Parse tool configurations
        for tool in ProspectorTool:
            tool_name = tool.value
            if tool_name in data:
                tool_config = data[tool_name]
                if isinstance(tool_config, dict):
                    if tool_config.get("run") is True:
                        profile.enabled_tools.append(tool)
                    elif tool_config.get("run") is False:
                        profile.disabled_tools.append(tool)

                    # Store options (excluding 'run')
                    options = {k: v for k, v in tool_config.items() if k != "run"}
                    if options:
                        profile.tool_options[tool_name] = options

                    # Special handling for pylint disabled messages
                    if tool_name == "pylint" and "disabled" in tool_config:
                        profile.pylint_disabled = tool_config["disabled"]

        return profile

    @classmethod
    def find_profile(cls, start_dir: str | Path = ".") -> Path | None:
        """
        Find a Prospector profile file by searching upward.

        Args:
            start_dir: Directory to start searching from.

        Returns:
            Path to profile file, or None if not found.
        """
        profile_names = [
            ".prospector.yaml",
            ".prospector.yml",
            "prospector.yaml",
            "prospector.yml",
        ]

        current = Path(start_dir).resolve()

        while current != current.parent:
            for name in profile_names:
                profile_path = current / name
                if profile_path.exists():
                    return profile_path
            current = current.parent

        return None


def merge_profiles(*profiles: ProspectorProfile) -> ProspectorProfile:
    """
    Merge multiple profiles with later profiles taking priority.

    Args:
        *profiles: Profiles to merge, in order of increasing priority.

    Returns:
        Merged profile.
    """
    if not profiles:
        return ProspectorProfile(name="merged")

    if len(profiles) == 1:
        return profiles[0]

    result = ProspectorProfile(name="merged")

    for profile in profiles:
        # Later profiles override earlier ones
        result.strictness = profile.strictness
        result.doc_warnings = profile.doc_warnings
        result.test_warnings = profile.test_warnings
        result.max_line_length = profile.max_line_length
        result.autodetect = profile.autodetect

        # Merge lists (unique items)
        for tool in profile.enabled_tools:
            if tool not in result.enabled_tools:
                result.enabled_tools.append(tool)
            if tool in result.disabled_tools:
                result.disabled_tools.remove(tool)

        for tool in profile.disabled_tools:
            if tool not in result.disabled_tools:
                result.disabled_tools.append(tool)
            if tool in result.enabled_tools:
                result.enabled_tools.remove(tool)

        for path in profile.ignore_paths:
            if path not in result.ignore_paths:
                result.ignore_paths.append(path)

        for pattern in profile.ignore_patterns:
            if pattern not in result.ignore_patterns:
                result.ignore_patterns.append(pattern)

        for msg in profile.pylint_disabled:
            if msg not in result.pylint_disabled:
                result.pylint_disabled.append(msg)

        # Merge tool options (later takes priority)
        for tool_name, options in profile.tool_options.items():
            if tool_name not in result.tool_options:
                result.tool_options[tool_name] = {}
            result.tool_options[tool_name].update(options)

    return result


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class MessageLocation:
    """Location of a message in source code."""

    path: str
    module: str | None = None
    function: str | None = None
    line: int | None = None
    character: int | None = None

    @property
    def location_string(self) -> str:
        """Get formatted location string."""
        if self.line is not None:
            if self.character is not None:
                return f"{self.path}:{self.line}:{self.character}"
            return f"{self.path}:{self.line}"
        return self.path


@dataclass
class ProspectorMessage:
    """A message from Prospector."""

    source: str  # Tool that generated the message
    code: str  # Error/warning code
    message: str
    location: MessageLocation
    severity: MessageSeverity = MessageSeverity.WARNING

    def format(self) -> str:
        """Format the message for display."""
        return f"{self.location.location_string}: " f"[{self.source}] {self.code}: {self.message}"


@dataclass
class ProspectorSummary:
    """Summary of Prospector analysis."""

    time_taken: float = 0.0
    completed: bool = True
    message_count: int = 0

    # Tool statistics
    tools_run: list[str] = field(default_factory=list)
    tool_counts: dict[str, int] = field(default_factory=dict)

    # Profiles
    profiles_used: list[str] = field(default_factory=list)


@dataclass
class ProspectorReport:
    """Complete Prospector analysis report."""

    messages: list[ProspectorMessage] = field(default_factory=list)
    summary: ProspectorSummary = field(default_factory=ProspectorSummary)
    paths_checked: list[str] = field(default_factory=list)
    config: ProspectorConfig = field(default_factory=ProspectorConfig)
    errors: list[str] = field(default_factory=list)

    @property
    def message_count(self) -> int:
        """Get total number of messages."""
        return len(self.messages)

    @property
    def messages_by_tool(self) -> dict[str, list[ProspectorMessage]]:
        """Group messages by source tool."""
        result: dict[str, list[ProspectorMessage]] = {}
        for msg in self.messages:
            result.setdefault(msg.source, []).append(msg)
        return result

    @property
    def messages_by_severity(self) -> dict[MessageSeverity, list[ProspectorMessage]]:
        """Group messages by severity."""
        result: dict[MessageSeverity, list[ProspectorMessage]] = {}
        for msg in self.messages:
            result.setdefault(msg.severity, []).append(msg)
        return result

    @property
    def messages_by_file(self) -> dict[str, list[ProspectorMessage]]:
        """Group messages by file."""
        result: dict[str, list[ProspectorMessage]] = {}
        for msg in self.messages:
            result.setdefault(msg.location.path, []).append(msg)
        return result

    @property
    def error_count(self) -> int:
        """Count of error-level messages."""
        return len([m for m in self.messages if m.severity in (MessageSeverity.ERROR, MessageSeverity.FATAL)])

    @property
    def warning_count(self) -> int:
        """Count of warning-level messages."""
        return len([m for m in self.messages if m.severity == MessageSeverity.WARNING])

    def get_summary(self) -> dict[str, Any]:
        """Get a summary of the report."""
        return {
            "paths_checked": len(self.paths_checked),
            "total_messages": self.message_count,
            "errors": self.error_count,
            "warnings": self.warning_count,
            "by_tool": {tool: len(msgs) for tool, msgs in self.messages_by_tool.items()},
            "by_severity": {sev.value: len(msgs) for sev, msgs in self.messages_by_severity.items()},
            "tools_run": self.summary.tools_run,
            "time_taken": self.summary.time_taken,
        }

    def deduplicate_messages(self) -> list[ProspectorMessage]:
        """
        Remove duplicate messages from different tools.

        Identifies messages that point to the same issue based on:
        - Same file and line
        - Same or similar error type/message

        Returns:
            Deduplicated list of messages, keeping the highest severity.
        """
        # Group messages by location (file:line)
        by_location: dict[str, list[ProspectorMessage]] = {}
        for msg in self.messages:
            key = f"{msg.location.path}:{msg.location.line}"
            by_location.setdefault(key, []).append(msg)

        result: list[ProspectorMessage] = []

        for _location, msgs in by_location.items():
            if len(msgs) == 1:
                result.append(msgs[0])
                continue

            # Group potential duplicates
            seen: dict[str, ProspectorMessage] = {}

            for msg in msgs:
                # Create a normalized key for duplicate detection
                dup_key = self._get_dedup_key(msg)

                if dup_key in seen:
                    existing = seen[dup_key]
                    # Keep the higher severity message
                    if self._severity_rank(msg.severity) > self._severity_rank(existing.severity):
                        seen[dup_key] = msg
                else:
                    seen[dup_key] = msg

            result.extend(seen.values())

        return sorted(result, key=lambda m: (m.location.path, m.location.line))

    def _get_dedup_key(self, msg: ProspectorMessage) -> str:
        """
        Generate a key for duplicate detection.

        This normalizes messages from different tools that report the same issue.
        """
        # Map common equivalent error codes
        code_equivalents = {
            # Import ordering
            "I001": "import-order",
            "I101": "import-order",
            "E401": "import-order",
            # Unused imports
            "F401": "unused-import",
            "W0611": "unused-import",
            # Undefined names
            "F821": "undefined-name",
            "E0602": "undefined-name",
            # Line too long
            "E501": "line-too-long",
            "C0301": "line-too-long",
            # Trailing whitespace
            "W291": "trailing-whitespace",
            "W293": "trailing-whitespace",
            "C0303": "trailing-whitespace",
            # Missing docstrings
            "D100": "missing-docstring",
            "D101": "missing-docstring",
            "D102": "missing-docstring",
            "D103": "missing-docstring",
            "C0114": "missing-docstring",
            "C0115": "missing-docstring",
            "C0116": "missing-docstring",
            # Too many arguments
            "PLR0913": "too-many-args",
            "R0913": "too-many-args",
            # Too many branches
            "PLR0912": "too-many-branches",
            "R0912": "too-many-branches",
            # Complexity
            "C901": "complexity",
            "R0915": "complexity",
        }

        normalized_code = code_equivalents.get(msg.code, msg.code)
        return f"{normalized_code}"

    @staticmethod
    def _severity_rank(severity: MessageSeverity) -> int:
        """Get numeric rank for severity comparison."""
        ranks = {
            MessageSeverity.INFO: 0,
            MessageSeverity.REFACTOR: 1,
            MessageSeverity.CONVENTION: 2,
            MessageSeverity.WARNING: 3,
            MessageSeverity.ERROR: 4,
            MessageSeverity.FATAL: 5,
        }
        return ranks.get(severity, 0)

    def get_unique_issues(self) -> list[ProspectorMessage]:
        """
        Get a list of unique issues, combining reports from multiple tools.

        This is an alias for deduplicate_messages() for clearer semantics.
        """
        return self.deduplicate_messages()

    @property
    def duplicate_count(self) -> int:
        """Get the number of duplicate messages that would be removed."""
        return self.message_count - len(self.deduplicate_messages())


# =============================================================================
# Parser Class
# =============================================================================


class ProspectorParser:
    """
    Parser for Prospector output - meta-linter.

    Provides comprehensive code analysis by aggregating results
    from multiple Python linting tools through Prospector.

    Implementation Status:
        ✓ Core Prospector execution and JSON parsing (P5-PROSPECTOR-001)
        ✓ Full command building with all options
        ✓ Severity mapping and message tracking
        ✓ Profile management via ProspectorProfileLoader (P5-PROSPECTOR-002)
        ✓ Message deduplication via deduplicate_messages() (P5-PROSPECTOR-003)

    Usage:
        >>> parser = ProspectorParser()
        >>> report = parser.analyze_path("src/")
        >>> for msg in report.messages:
        ...     print(msg.format())
    """

    def __init__(self, config: ProspectorConfig | None = None):
        """
        Initialize the parser.

        Args:
            config: Configuration for Prospector.
        """
        self.config = config or ProspectorConfig()
        self._prospector_path: str | None = None

    @property
    def prospector_path(self) -> str | None:
        """Get path to prospector executable."""
        if self._prospector_path is None:
            self._prospector_path = self._find_prospector()
        return self._prospector_path

    def _find_prospector(self) -> str | None:
        """Find prospector executable."""
        try:
            result = subprocess.run(
                ["which", "prospector"],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass
        return None

    def is_available(self) -> bool:
        """Check if prospector is available."""
        return self.prospector_path is not None

    def analyze_file(self, path: str | Path) -> ProspectorReport:
        """
        Analyze a Python file with Prospector.

        Args:
            path: Path to the Python file.

        Returns:
            ProspectorReport with analysis results.
        """
        return self.analyze_path(str(path))

    def analyze_path(self, path: str) -> ProspectorReport:
        """
        Analyze a path (file or directory) with Prospector.

        Runs prospector subprocess and parses JSON output.

        Args:
            path: Path to analyze.

        Returns:
            ProspectorReport with analysis results.
        """
        report = ProspectorReport(
            paths_checked=[path],
            config=self.config,
        )

        if not self.is_available():
            report.errors.append("prospector is not installed or not in PATH")
            return report

        cmd = self._build_command(path)

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600,  # 10 minutes for large codebases
            )

            # Parse JSON output
            if result.stdout:
                self._parse_json_output(result.stdout, report)

            if result.stderr:
                for line in result.stderr.strip().split("\n"):
                    if line and not line.startswith("Checking"):
                        report.errors.append(line)

        except subprocess.TimeoutExpired:
            report.errors.append("prospector timed out after 10 minutes")
        except Exception as e:
            report.errors.append(f"Failed to run prospector: {e}")

        return report

    def _build_command(self, path: str) -> list[str]:
        """Build the prospector command."""
        cmd = ["prospector"]

        # Output format
        cmd.extend(["--output-format", self.config.output_format])

        # Strictness
        cmd.extend(["--strictness", self.config.strictness.value])

        # Profile
        if self.config.profile:
            cmd.extend(["--profile", self.config.profile])

        if self.config.profile_path:
            cmd.extend(["--profile-path", self.config.profile_path])

        # Tool control
        for tool in self.config.with_tools:
            cmd.extend(["--with-tool", tool.value])

        for tool in self.config.without_tools:
            cmd.extend(["--without-tool", tool.value])

        # Ignore paths
        for ignore_path in self.config.ignore_paths:
            cmd.extend(["--ignore-paths", ignore_path])

        for pattern in self.config.ignore_patterns:
            cmd.extend(["--ignore-patterns", pattern])

        # Uses (frameworks)
        for use in self.config.uses:
            cmd.extend(["--uses", use])

        # Options
        if not self.config.doc_warnings:
            cmd.append("--no-doc-warnings")

        if not self.config.test_warnings:
            cmd.append("--no-test-warnings")

        if self.config.no_autodetect:
            cmd.append("--no-autodetect")

        if self.config.max_line_length:
            cmd.extend(["--max-line-length", str(self.config.max_line_length)])

        if self.config.show_profile:
            cmd.append("--show-profile")

        # Extra args
        cmd.extend(self.config.extra_args)

        # Path to analyze
        cmd.append(path)

        return cmd

    def _parse_json_output(
        self,
        output: str,
        report: ProspectorReport,
    ) -> None:
        """
        Parse Prospector JSON output.

        JSON format:
        {
            "messages": [...],
            "summary": {...}
        }
        """
        try:
            data = json.loads(output)
        except json.JSONDecodeError as e:
            report.errors.append(f"Failed to parse JSON output: {e}")
            return

        # Parse messages
        for msg_data in data.get("messages", []):
            location_data = msg_data.get("location", {})
            location = MessageLocation(
                path=location_data.get("path", ""),
                module=location_data.get("module"),
                function=location_data.get("function"),
                line=location_data.get("line"),
                character=location_data.get("character"),
            )

            # Map severity
            severity_str = msg_data.get("severity", "warning")
            severity = self._map_severity(severity_str)

            message = ProspectorMessage(
                source=msg_data.get("source", "unknown"),
                code=msg_data.get("code", ""),
                message=msg_data.get("message", ""),
                location=location,
                severity=severity,
            )
            report.messages.append(message)

        # Parse summary
        summary_data = data.get("summary", {})
        report.summary = ProspectorSummary(
            time_taken=summary_data.get("time_taken", 0.0),
            completed=summary_data.get("completed", True),
            message_count=summary_data.get("message_count", len(report.messages)),
            tools_run=list(summary_data.get("tools", {}).keys()),
            tool_counts=summary_data.get("tools", {}),
            profiles_used=summary_data.get("profiles", []),
        )

    def _map_severity(self, severity_str: str) -> MessageSeverity:
        """Map severity string to enum."""
        severity_map = {
            "info": MessageSeverity.INFO,
            "refactor": MessageSeverity.REFACTOR,
            "convention": MessageSeverity.CONVENTION,
            "warning": MessageSeverity.WARNING,
            "error": MessageSeverity.ERROR,
            "fatal": MessageSeverity.FATAL,
        }
        return severity_map.get(severity_str.lower(), MessageSeverity.WARNING)


# =============================================================================
# Utility Functions
# =============================================================================


def format_prospector_report(report: ProspectorReport) -> str:
    """Format a Prospector report for display."""
    lines = [
        "Prospector Report",
        "=" * 50,
        "",
        f"Paths analyzed: {', '.join(report.paths_checked)}",
        f"Strictness: {report.config.strictness.value}",
        f"Total messages: {report.message_count}",
        f"  - Errors: {report.error_count}",
        f"  - Warnings: {report.warning_count}",
        "",
    ]

    if report.summary.tools_run:
        lines.append("Tools run:")
        for tool in report.summary.tools_run:
            count = report.summary.tool_counts.get(tool, 0)
            lines.append(f"  - {tool}: {count} messages")

    lines.append("")

    if report.messages_by_severity:
        lines.append("By severity:")
        for severity, messages in sorted(report.messages_by_severity.items(), key=lambda x: -len(x[1])):
            lines.append(f"  {severity.value}: {len(messages)}")

    lines.append("")

    if report.messages:
        lines.append("Messages:")
        for msg in report.messages[:15]:
            lines.append(f"  {msg.format()}")
        if len(report.messages) > 15:
            lines.append(f"  ... and {len(report.messages) - 15} more")

    if report.errors:
        lines.extend(["", "Errors:"])
        for error in report.errors:
            lines.append(f"  {error}")

    if report.summary.time_taken:
        lines.extend(
            [
                "",
                f"Time taken: {report.summary.time_taken:.2f}s",
            ]
        )

    return "\n".join(lines)


def create_profile(
    name: str,
    strictness: Strictness = Strictness.MEDIUM,
    with_tools: list[ProspectorTool] | None = None,
    without_tools: list[ProspectorTool] | None = None,
    max_line_length: int = 100,
    doc_warnings: bool = True,
) -> dict[str, Any]:
    """
    Create a Prospector profile configuration.

    Returns a dict that can be written to .prospector.yaml.
    """
    profile: dict[str, Any] = {
        "strictness": strictness.value,
        "max-line-length": max_line_length,
        "doc-warnings": doc_warnings,
    }

    # Add tool configurations
    if with_tools:
        for tool in with_tools:
            profile.setdefault(tool.value, {})["run"] = True

    if without_tools:
        for tool in without_tools:
            profile.setdefault(tool.value, {})["run"] = False

    return profile
