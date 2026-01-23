#!/usr/bin/env python3
"""
Ruff Parser - Fast Rust-based Python Linter Integration.
=========================================================

Ruff is an extremely fast Python linter written in Rust that replaces
Flake8, isort, pyupgrade, and many other tools. This module provides
structured parsing of Ruff output for Code Scalpel integration.

Implementation Status: MOSTLY COMPLETED
Priority: P1 - CRITICAL

Ruff Benefits:
    - 10-100x faster than Flake8
    - Single tool replacing multiple linters
    - Built-in auto-fix capabilities
    - pyproject.toml native configuration
    - Growing rule set including all major linters

==============================================================================
COMPLETED [P1-RUFF-001]: Implement RuffParser as primary linter
==============================================================================
Priority: CRITICAL
Status: ✓ COMPLETED

Implemented Features:
    - [✓] Parse JSON output format (ruff check --output-format=json)
    - [✓] Map rule codes to descriptions (E501, W503, F401, etc.)
    - [✓] Extract auto-fix information when available
    - [✓] Complete RuffViolation.from_dict() parsing
    - [✓] Full analyze() method with subprocess execution
    - [✓] Handle stdin input for unsaved files (analyze_string method)
    - [✓] JSON parsing with error handling
    - [✓] RuffFix and RuffEdit parsing
    - [✓] FixApplicability (safe/unsafe/display) support
    - [✓] Parse configuration from pyproject.toml [tool.ruff]
    - [✓] Support --select and --ignore flag simulation (via RuffConfig.to_cli_args())
    - [✓] Support per-file-ignores configuration
    - [✓] Support extend-select and extend-ignore options

Configuration Sources:
    - pyproject.toml [tool.ruff]
    - ruff.toml
    - .ruff.toml
    - Command-line overrides

Output Format Example (JSON):
    ```json
    {
        "cell": null,
        "code": "F401",
        "end_location": {"column": 10, "row": 1},
        "filename": "example.py",
        "fix": {
            "applicability": "safe",
            "edits": [{"content": "", "end_location": {...}, "location": {...}}],
            "message": "Remove unused import: `os`"
        },
        "location": {"column": 8, "row": 1},
        "message": "`os` imported but unused",
        "noqa_row": 1,
        "url": "https://docs.astral.sh/ruff/rules/unused-import"
    }
    ```

Test Cases:
    - Parse JSON output with violations
    - Parse output with fixes
    - Handle empty output (no violations)
    - Verify rule code mapping
    - Test configuration file detection

==============================================================================
COMPLETED [P1-RUFF-002]: Implement rule category mapping
==============================================================================
Priority: CRITICAL
Status: ✓ COMPLETED
Depends On: P1-RUFF-001

Implemented Features:
    - [✓] Complete RULE_PREFIXES dict with 50+ categories
    - [✓] Map E codes (pycodestyle errors)
    - [✓] Map W codes (pycodestyle warnings)
    - [✓] Map F codes (pyflakes)
    - [✓] Map I codes (isort)
    - [✓] Map B codes (flake8-bugbear)
    - [✓] Map C codes (mccabe complexity)
    - [✓] Map S codes (bandit/flake8-bandit)
    - [✓] Map N codes (pep8-naming)
    - [✓] Map UP codes (pyupgrade)
    - [✓] Map ANN codes (flake8-annotations)
    - [✓] Map RUF codes (Ruff-specific)
    - [✓] Map D codes (pydocstyle)
    - [✓] Map PL codes (Pylint variants)
    - [✓] get_rule_category() function
    - [✓] get_rule_severity() function
    - [✓] RuffViolation.category and .severity properties

Rule Categories Reference:
    ```python
    RULE_CATEGORIES = {
        "E": "pycodestyle errors",
        "W": "pycodestyle warnings",
        "F": "Pyflakes",
        "I": "isort",
        "B": "flake8-bugbear",
        "C": "mccabe",
        "S": "flake8-bandit",
        "N": "pep8-naming",
        "UP": "pyupgrade",
        "ANN": "flake8-annotations",
        "RUF": "Ruff-specific",
        "D": "pydocstyle",
        "PT": "flake8-pytest-style",
        "SIM": "flake8-simplify",
        "ARG": "flake8-unused-arguments",
        "ERA": "eradicate",
        "PL": "Pylint",
        "TRY": "tryceratops",
    }
    ```

==============================================================================
COMPLETED [P1-RUFF-003]: Implement fix application support
==============================================================================
Priority: HIGH
Status: ✓ COMPLETED
Depends On: P1-RUFF-001

Implemented Features:
    - [✓] Parse fix edits from JSON output (RuffEdit.from_dict())
    - [✓] Distinguish safe vs unsafe fixes (FixApplicability enum)
    - [✓] RuffFix.is_safe() method
    - [✓] RuffViolation.has_fix and .is_auto_fixable properties
    - [✓] get_fix_diff() method for preview
    - [✓] apply_fixes() method with unsafe_fixes flag
    - [✓] Complete RuffEdit with location tracking
    - [✓] Apply single fix to source (apply_fix_to_source method)
    - [✓] Apply multiple fixes with conflict detection (apply_edits method)
    - [✓] Preview fix changes before application (get_fix_preview method)
    - [✓] Support dry-run mode via return value
    - [✓] Handle overlapping fix regions with sorting

Data Structures:
    ```python
    @dataclass
    class RuffEdit:
        content: str  # Replacement content
        start_line: int
        start_column: int
        end_line: int
        end_column: int

    @dataclass
    class RuffFix:
        message: str
        applicability: Literal["safe", "unsafe", "display"]
        edits: list[RuffEdit]
    ```

==============================================================================
COMPLETED [P2-RUFF-004]: Configuration parsing
==============================================================================
Priority: HIGH
Status: ✓ COMPLETED

Implemented Features:
    - [✓] RuffConfig dataclass with all settings
    - [✓] to_cli_args() method for command-line conversion
    - [✓] Support for select/ignore/extend options
    - [✓] Line length and target version support
    - [✓] Fixable/unfixable configuration
    - [✓] Parse [tool.ruff] from pyproject.toml (from_pyproject())
    - [✓] Parse standalone ruff.toml (from_ruff_toml())
    - [✓] find_config() for automatic config discovery
    - [✓] Support per-file-ignores
    - [✓] Support extend-select/extend-ignore
    - [✓] Support lint subsection (Ruff 0.1.0+ style)

Configuration Example:
    ```toml
    [tool.ruff]
    line-length = 100
    target-version = "py311"
    select = ["E", "F", "W", "I", "B", "C4"]
    ignore = ["E501"]

    [tool.ruff.per-file-ignores]
    "__init__.py" = ["F401"]
    "tests/*" = ["S101"]
    ```
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

# Try to import tomllib (Python 3.11+) or tomli as fallback
try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib  # type: ignore[import-not-found]
    except ImportError:
        tomllib = None  # type: ignore[assignment]

if TYPE_CHECKING:
    pass


# =============================================================================
# Enums
# =============================================================================


class RuffSeverity(Enum):
    """Severity level for Ruff violations."""

    ERROR = auto()  # E codes, F codes
    WARNING = auto()  # W codes
    CONVENTION = auto()  # Style issues
    REFACTOR = auto()  # Code improvement suggestions


class FixApplicability(Enum):
    """How safe it is to apply a fix."""

    SAFE = "safe"  # Always safe to apply
    UNSAFE = "unsafe"  # May change behavior
    DISPLAY = "display"  # For display only, don't apply


# =============================================================================
# Rule Categories
# =============================================================================

# Complete rule category mapping (50+ categories)
RULE_PREFIXES: dict[str, str] = {
    "E": "pycodestyle (errors)",
    "W": "pycodestyle (warnings)",
    "F": "Pyflakes",
    "I": "isort",
    "B": "flake8-bugbear",
    "C": "mccabe",
    "C4": "flake8-comprehensions",
    "S": "flake8-bandit",
    "N": "pep8-naming",
    "UP": "pyupgrade",
    "ANN": "flake8-annotations",
    "RUF": "Ruff-specific",
    "D": "pydocstyle",
    "PT": "flake8-pytest-style",
    "SIM": "flake8-simplify",
    "ARG": "flake8-unused-arguments",
    "ERA": "eradicate",
    "PL": "Pylint",
    "PLC": "Pylint Convention",
    "PLE": "Pylint Error",
    "PLR": "Pylint Refactor",
    "PLW": "Pylint Warning",
    "TRY": "tryceratops",
    "FLY": "flynt",
    "PERF": "Perflint",
    "LOG": "flake8-logging",
    "G": "flake8-logging-format",
    "INP": "flake8-no-pep420",
    "PIE": "flake8-pie",
    "T20": "flake8-print",
    "Q": "flake8-quotes",
    "RSE": "flake8-raise",
    "RET": "flake8-return",
    "SLF": "flake8-self",
    "SLOT": "flake8-slots",
    "TID": "flake8-tidy-imports",
    "TCH": "flake8-type-checking",
    "INT": "flake8-gettext",
    "PTH": "flake8-use-pathlib",
    "TD": "flake8-todos",
    "FIX": "flake8-fixme",
    "EM": "flake8-errmsg",
    "FA": "flake8-future-annotations",
    "ISC": "flake8-implicit-str-concat",
    "ICN": "flake8-import-conventions",
    "COM": "flake8-commas",
    "A": "flake8-builtins",
    "DJ": "flake8-django",
    "EXE": "flake8-executable",
    "NPY": "NumPy-specific",
    "PD": "pandas-vet",
    "AIR": "Airflow-specific",
    "FAST": "FastAPI-specific",
}


def get_rule_category(code: str) -> str:
    """Get the category description for a rule code."""
    # Try longest prefix first
    for length in range(len(code), 0, -1):
        prefix = code[:length]
        if prefix in RULE_PREFIXES:
            return RULE_PREFIXES[prefix]
    return "Unknown"


def get_rule_severity(code: str) -> RuffSeverity:
    """Determine severity based on rule code."""
    if code.startswith("E") or code.startswith("F"):
        return RuffSeverity.ERROR
    elif code.startswith("W"):
        return RuffSeverity.WARNING
    elif code.startswith(("C", "R", "PLR")):
        return RuffSeverity.REFACTOR
    else:
        return RuffSeverity.CONVENTION


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class SourceLocation:
    """Location in source code."""

    row: int  # 1-indexed line number
    column: int  # 0-indexed column number

    @classmethod
    def from_dict(cls, data: dict[str, int]) -> SourceLocation:
        """Create from Ruff JSON dict."""
        return cls(row=data["row"], column=data["column"])


@dataclass
class RuffEdit:
    """A single edit operation for a fix."""

    content: str
    location: SourceLocation
    end_location: SourceLocation

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RuffEdit:
        """Create from Ruff JSON dict."""
        return cls(
            content=data["content"],
            location=SourceLocation.from_dict(data["location"]),
            end_location=SourceLocation.from_dict(data["end_location"]),
        )


@dataclass
class RuffFix:
    """A fix suggestion with edits."""

    message: str
    applicability: FixApplicability
    edits: list[RuffEdit]

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> RuffFix | None:
        """Create from Ruff JSON dict."""
        if data is None:
            return None
        return cls(
            message=data.get("message", ""),
            applicability=FixApplicability(data.get("applicability", "display")),
            edits=[RuffEdit.from_dict(e) for e in data.get("edits", [])],
        )

    def is_safe(self) -> bool:
        """Check if this fix is safe to apply automatically."""
        return self.applicability == FixApplicability.SAFE


@dataclass
class RuffViolation:
    """A single Ruff violation/diagnostic."""

    code: str  # Rule code (e.g., "F401")
    message: str  # Human-readable message
    filename: str  # File path
    location: SourceLocation  # Start location
    end_location: SourceLocation  # End location
    fix: RuffFix | None = None  # Available fix, if any
    noqa_row: int | None = None  # Line where noqa comment would be effective
    url: str | None = None  # Link to rule documentation
    cell: int | None = None  # For Jupyter notebooks

    @property
    def line(self) -> int:
        """Get the line number (1-indexed)."""
        return self.location.row

    @property
    def column(self) -> int:
        """Get the column number (0-indexed)."""
        return self.location.column

    @property
    def category(self) -> str:
        """Get the rule category."""
        return get_rule_category(self.code)

    @property
    def severity(self) -> RuffSeverity:
        """Get the severity level."""
        return get_rule_severity(self.code)

    @property
    def has_fix(self) -> bool:
        """Check if a fix is available."""
        return self.fix is not None

    @property
    def is_auto_fixable(self) -> bool:
        """Check if this can be auto-fixed safely."""
        return self.fix is not None and self.fix.is_safe()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RuffViolation:
        """Create from Ruff JSON dict."""
        return cls(
            code=data["code"],
            message=data["message"],
            filename=data["filename"],
            location=SourceLocation.from_dict(data["location"]),
            end_location=SourceLocation.from_dict(data["end_location"]),
            fix=RuffFix.from_dict(data.get("fix")),
            noqa_row=data.get("noqa_row"),
            url=data.get("url"),
            cell=data.get("cell"),
        )

    def format(self, *, show_fix: bool = False) -> str:
        """Format the violation for display."""
        msg = f"{self.filename}:{self.line}:{self.column}: {self.code} {self.message}"
        if show_fix and self.fix:
            msg += f" [fix: {self.fix.message}]"
        return msg


@dataclass
class RuffConfig:
    """Configuration for Ruff analysis."""

    line_length: int = 88
    target_version: str = "py311"
    select: list[str] = field(default_factory=lambda: ["E", "F", "W"])
    ignore: list[str] = field(default_factory=list)
    extend_select: list[str] = field(default_factory=list)
    extend_ignore: list[str] = field(default_factory=list)
    per_file_ignores: dict[str, list[str]] = field(default_factory=dict)
    fixable: list[str] = field(default_factory=lambda: ["ALL"])
    unfixable: list[str] = field(default_factory=list)
    exclude: list[str] = field(default_factory=list)

    @classmethod
    def from_pyproject(cls, path: Path) -> RuffConfig:
        """
        Load configuration from pyproject.toml.

        Parses the [tool.ruff] section and returns a RuffConfig instance.

        Args:
            path: Path to pyproject.toml file.

        Returns:
            RuffConfig populated from file.

        Raises:
            ImportError: If tomllib/tomli is not available.
            FileNotFoundError: If file doesn't exist.
            KeyError: If [tool.ruff] section not found.
        """
        if tomllib is None:
            raise ImportError("tomllib (Python 3.11+) or tomli is required for TOML parsing")

        with open(path, "rb") as f:
            data = tomllib.load(f)

        ruff_config = data.get("tool", {}).get("ruff", {})
        if not ruff_config:
            return cls()  # Return defaults if no config

        return cls._from_dict(ruff_config)

    @classmethod
    def from_ruff_toml(cls, path: Path) -> RuffConfig:
        """
        Load configuration from ruff.toml or .ruff.toml.

        Args:
            path: Path to ruff.toml file.

        Returns:
            RuffConfig populated from file.
        """
        if tomllib is None:
            raise ImportError("tomllib (Python 3.11+) or tomli is required for TOML parsing")

        with open(path, "rb") as f:
            data = tomllib.load(f)

        return cls._from_dict(data)

    @classmethod
    def _from_dict(cls, data: dict[str, Any]) -> RuffConfig:
        """Create RuffConfig from a dictionary."""
        config = cls()

        if "line-length" in data:
            config.line_length = data["line-length"]
        if "target-version" in data:
            config.target_version = data["target-version"]
        if "select" in data:
            config.select = list(data["select"])
        if "ignore" in data:
            config.ignore = list(data["ignore"])
        if "extend-select" in data:
            config.extend_select = list(data["extend-select"])
        if "extend-ignore" in data:
            config.extend_ignore = list(data["extend-ignore"])
        if "per-file-ignores" in data:
            config.per_file_ignores = dict(data["per-file-ignores"])
        if "fixable" in data:
            config.fixable = list(data["fixable"])
        if "unfixable" in data:
            config.unfixable = list(data["unfixable"])
        if "exclude" in data:
            config.exclude = list(data["exclude"])

        # Handle lint subsection (Ruff 0.1.0+ style)
        if "lint" in data:
            lint = data["lint"]
            if "select" in lint:
                config.select = list(lint["select"])
            if "ignore" in lint:
                config.ignore = list(lint["ignore"])
            if "extend-select" in lint:
                config.extend_select = list(lint["extend-select"])
            if "extend-ignore" in lint:
                config.extend_ignore = list(lint["extend-ignore"])
            if "per-file-ignores" in lint:
                config.per_file_ignores = dict(lint["per-file-ignores"])
            if "fixable" in lint:
                config.fixable = list(lint["fixable"])
            if "unfixable" in lint:
                config.unfixable = list(lint["unfixable"])

        return config

    @classmethod
    def find_config(cls, start_path: Path) -> RuffConfig | None:
        """
        Find and load configuration from the nearest config file.

        Searches upward from start_path for:
        1. ruff.toml
        2. .ruff.toml
        3. pyproject.toml (with [tool.ruff])

        Args:
            start_path: Path to start searching from.

        Returns:
            RuffConfig if found, None otherwise.
        """
        current = start_path.resolve()
        if current.is_file():
            current = current.parent

        while current != current.parent:
            # Check for ruff.toml
            ruff_toml = current / "ruff.toml"
            if ruff_toml.exists():
                try:
                    return cls.from_ruff_toml(ruff_toml)
                except Exception:
                    pass

            # Check for .ruff.toml
            dot_ruff_toml = current / ".ruff.toml"
            if dot_ruff_toml.exists():
                try:
                    return cls.from_ruff_toml(dot_ruff_toml)
                except Exception:
                    pass

            # Check for pyproject.toml
            pyproject = current / "pyproject.toml"
            if pyproject.exists():
                try:
                    config = cls.from_pyproject(pyproject)
                    if config.select != ["E", "F", "W"] or config.line_length != 88:
                        # Config was actually loaded (not defaults)
                        return config
                except Exception:
                    pass

            current = current.parent

        return None

    def to_cli_args(self) -> list[str]:
        """Convert configuration to CLI arguments."""
        args = []
        args.extend(["--line-length", str(self.line_length)])
        args.extend(["--target-version", self.target_version])
        if self.select:
            args.extend(["--select", ",".join(self.select)])
        if self.ignore:
            args.extend(["--ignore", ",".join(self.ignore)])
        if self.extend_select:
            args.extend(["--extend-select", ",".join(self.extend_select)])
        if self.extend_ignore:
            args.extend(["--extend-ignore", ",".join(self.extend_ignore)])
        if self.fixable and self.fixable != ["ALL"]:
            args.extend(["--fixable", ",".join(self.fixable)])
        if self.unfixable:
            args.extend(["--unfixable", ",".join(self.unfixable)])
        if self.per_file_ignores:
            for pattern, codes in self.per_file_ignores.items():
                codes_str = ",".join(codes) if isinstance(codes, list) else codes
                args.extend(["--per-file-ignores", f"{pattern}:{codes_str}"])
        if self.exclude:
            for pattern in self.exclude:
                args.extend(["--exclude", pattern])
        return args


@dataclass
class RuffReport:
    """Complete Ruff analysis report."""

    violations: list[RuffViolation] = field(default_factory=list)
    files_analyzed: int = 0
    errors: list[str] = field(default_factory=list)
    config: RuffConfig | None = None
    ruff_version: str | None = None

    @property
    def total_violations(self) -> int:
        """Get total number of violations."""
        return len(self.violations)

    @property
    def fixable_count(self) -> int:
        """Get number of auto-fixable violations."""
        return sum(1 for v in self.violations if v.is_auto_fixable)

    @property
    def violations_by_code(self) -> dict[str, list[RuffViolation]]:
        """Group violations by rule code."""
        result: dict[str, list[RuffViolation]] = {}
        for v in self.violations:
            result.setdefault(v.code, []).append(v)
        return result

    @property
    def violations_by_file(self) -> dict[str, list[RuffViolation]]:
        """Group violations by file."""
        result: dict[str, list[RuffViolation]] = {}
        for v in self.violations:
            result.setdefault(v.filename, []).append(v)
        return result

    @property
    def violations_by_category(self) -> dict[str, list[RuffViolation]]:
        """Group violations by category."""
        result: dict[str, list[RuffViolation]] = {}
        for v in self.violations:
            result.setdefault(v.category, []).append(v)
        return result

    def get_summary(self) -> dict[str, Any]:
        """Get a summary of the report."""
        return {
            "total_violations": self.total_violations,
            "fixable_count": self.fixable_count,
            "files_analyzed": self.files_analyzed,
            "by_severity": {s.name: sum(1 for v in self.violations if v.severity == s) for s in RuffSeverity},
            "by_category": {cat: len(violations) for cat, violations in self.violations_by_category.items()},
        }


# =============================================================================
# Parser Class
# =============================================================================


class RuffParser:
    """
    Parser for Ruff linter output.

    Ruff is an extremely fast Python linter that can replace Flake8, isort,
    pyupgrade, and many other tools.

    Status: COMPLETED
    - ✓ P1-RUFF-001: Full JSON parsing and subprocess integration
    - ✓ P1-RUFF-002: Complete rule category mapping (50+ categories)
    - ✓ P1-RUFF-003: Fix parsing and programmatic application
    - ✓ P2-RUFF-004: Config parsing from pyproject.toml, ruff.toml

    Usage:
        >>> parser = RuffParser()
        >>> report = parser.analyze("example.py")
        >>> for violation in report.violations:
        ...     print(f"{violation.code}: {violation.message}")

        >>> # With custom config
        >>> config = RuffConfig(select=["E", "F", "B"])
        >>> report = parser.analyze("example.py", config=config)

        >>> # Apply fixes programmatically
        >>> fixed_source = parser.apply_fix_to_source(source, violation)
    """

    def __init__(self, *, ruff_path: str = "ruff"):
        """
        Initialize the Ruff parser.

        Args:
            ruff_path: Path to the ruff executable.
        """
        self.ruff_path = ruff_path
        self._version: str | None = None

    @property
    def version(self) -> str | None:
        """Get the Ruff version."""
        if self._version is None:
            try:
                result = subprocess.run(
                    [self.ruff_path, "--version"],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                self._version = result.stdout.strip()
            except (subprocess.CalledProcessError, FileNotFoundError):
                pass
        return self._version

    def is_available(self) -> bool:
        """Check if Ruff is available."""
        try:
            subprocess.run(
                [self.ruff_path, "--version"],
                capture_output=True,
                check=True,
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def analyze(
        self,
        target: str | Path | list[str | Path],
        *,
        config: RuffConfig | None = None,
        stdin_source: str | None = None,
    ) -> RuffReport:
        """
        Analyze Python files with Ruff.

        Args:
            target: File, directory, or list of targets to analyze.
            config: Optional configuration override.
            stdin_source: Source code to analyze via stdin (use with single file target).

        Returns:
            RuffReport with violations and metadata.
        """
        report = RuffReport(config=config, ruff_version=self.version)

        # Build targets list
        if isinstance(target, (str, Path)):
            targets = [str(target)]
        else:
            targets = [str(t) for t in target]

        # Build command
        cmd = [
            self.ruff_path,
            "check",
            "--output-format=json",
            "--exit-zero",  # Don't exit with error on violations
        ]

        if config:
            cmd.extend(config.to_cli_args())

        if stdin_source:
            cmd.append("--stdin-filename")
            cmd.append(targets[0])
            cmd.append("-")  # Read from stdin
        else:
            cmd.extend(targets)

        try:
            # Run Ruff
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                input=stdin_source,
            )

            # Parse JSON output
            if result.stdout.strip():
                violations_data = json.loads(result.stdout)
                report.violations = [RuffViolation.from_dict(v) for v in violations_data]

            # Count files (approximate from violations)
            report.files_analyzed = len(set(v.filename for v in report.violations)) or 1

            if result.stderr:
                report.errors.append(result.stderr.strip())

        except FileNotFoundError:
            report.errors.append(f"Ruff not found at: {self.ruff_path}")
        except json.JSONDecodeError as e:
            report.errors.append(f"Failed to parse Ruff output: {e}")
        except subprocess.SubprocessError as e:
            report.errors.append(f"Ruff execution failed: {e}")

        return report

    def analyze_string(
        self,
        source: str,
        *,
        filename: str = "stdin.py",
        config: RuffConfig | None = None,
    ) -> RuffReport:
        """
        Analyze Python source code from a string.

        Args:
            source: Python source code.
            filename: Filename for error messages.
            config: Optional configuration override.

        Returns:
            RuffReport with violations and metadata.
        """
        return self.analyze(filename, config=config, stdin_source=source)

    def get_fix_diff(
        self,
        target: str | Path,
        *,
        config: RuffConfig | None = None,
    ) -> str:
        """
        Get a diff of what Ruff would fix.

        Note: Uses Ruff CLI --diff flag.

        Args:
            target: File to analyze.
            config: Optional configuration override.

        Returns:
            Unified diff string.
        """
        cmd = [
            self.ruff_path,
            "check",
            "--fix",
            "--diff",
            str(target),
        ]

        if config:
            cmd.extend(config.to_cli_args())

        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.stdout

    def apply_fixes(
        self,
        target: str | Path,
        *,
        config: RuffConfig | None = None,
        unsafe_fixes: bool = False,
    ) -> tuple[bool, str]:
        """
        Apply Ruff fixes to a file.

        Note: Uses Ruff CLI --fix flag.

        Args:
            target: File to fix.
            config: Optional configuration override.
            unsafe_fixes: Whether to apply unsafe fixes.

        Returns:
            Tuple of (success, message).
        """
        cmd = [
            self.ruff_path,
            "check",
            "--fix",
            str(target),
        ]

        if unsafe_fixes:
            cmd.append("--unsafe-fixes")

        if config:
            cmd.extend(config.to_cli_args())

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            return True, "Fixes applied successfully"
        else:
            return False, result.stderr or result.stdout

    def apply_fix_to_source(
        self,
        source: str,
        violation: RuffViolation,
    ) -> str | None:
        """
        Apply a single fix to source code programmatically.

        Args:
            source: The source code to modify.
            violation: A violation with a fix to apply.

        Returns:
            The modified source code, or None if no fix available.
        """
        if not violation.fix or not violation.fix.edits:
            return None

        return self.apply_edits(source, violation.fix.edits)

    def apply_edits(
        self,
        source: str,
        edits: list[RuffEdit],
        *,
        check_conflicts: bool = True,
    ) -> str:
        """
        Apply multiple edits to source code.

        Edits are sorted and applied in reverse order (bottom-up) to avoid
        offset invalidation.

        Args:
            source: The source code to modify.
            edits: List of edits to apply.
            check_conflicts: Whether to check for overlapping edits.

        Returns:
            The modified source code.

        Raises:
            ValueError: If edits overlap and check_conflicts is True.
        """
        if not edits:
            return source

        # Convert source to lines for position calculation
        lines = source.splitlines(keepends=True)

        # Add empty string if source doesn't end with newline
        if source and not source.endswith("\n"):
            lines.append("")

        # Helper to convert row/column to absolute offset
        def to_offset(row: int, col: int) -> int:
            offset = sum(len(lines[i]) for i in range(row - 1))
            return offset + col

        # Convert edits to (start_offset, end_offset, content) tuples
        offset_edits: list[tuple[int, int, str]] = []
        for edit in edits:
            start = to_offset(edit.location.row, edit.location.column)
            end = to_offset(edit.end_location.row, edit.end_location.column)
            offset_edits.append((start, end, edit.content))

        # Sort by start position (descending) for reverse application
        offset_edits.sort(key=lambda x: x[0], reverse=True)

        # Check for overlapping edits
        if check_conflicts and len(offset_edits) > 1:
            for i in range(len(offset_edits) - 1):
                curr_start, curr_end, _ = offset_edits[i]
                next_start, next_end, _ = offset_edits[i + 1]
                # Since sorted descending, next_start < curr_start
                if next_end > curr_start:
                    raise ValueError(
                        f"Overlapping edits detected: edit at {next_start}-{next_end} "
                        f"overlaps with edit at {curr_start}-{curr_end}"
                    )

        # Apply edits in reverse order
        result = source
        for start, end, content in offset_edits:
            result = result[:start] + content + result[end:]

        return result

    def get_fix_preview(
        self,
        source: str,
        violation: RuffViolation,
        *,
        context_lines: int = 3,
    ) -> str | None:
        """
        Get a preview of what a fix would change.

        Args:
            source: The source code.
            violation: A violation with a fix.
            context_lines: Number of context lines to show.

        Returns:
            A unified diff string showing the change, or None if no fix.
        """
        if not violation.fix:
            return None

        import difflib

        fixed = self.apply_fix_to_source(source, violation)
        if fixed is None:
            return None

        original_lines = source.splitlines(keepends=True)
        fixed_lines = fixed.splitlines(keepends=True)

        diff = difflib.unified_diff(
            original_lines,
            fixed_lines,
            fromfile=f"a/{violation.filename}",
            tofile=f"b/{violation.filename}",
            n=context_lines,
        )

        return "".join(diff)

    def apply_all_safe_fixes(
        self,
        source: str,
        violations: list[RuffViolation],
    ) -> tuple[str, int]:
        """
        Apply all safe fixes to source code.

        Args:
            source: The source code to modify.
            violations: List of violations to consider.

        Returns:
            Tuple of (modified source, number of fixes applied).
        """
        # Collect all safe edits
        all_edits: list[RuffEdit] = []
        for v in violations:
            if v.fix and v.fix.is_safe():
                all_edits.extend(v.fix.edits)

        if not all_edits:
            return source, 0

        try:
            fixed = self.apply_edits(source, all_edits, check_conflicts=True)
            return fixed, len([v for v in violations if v.fix and v.fix.is_safe()])
        except ValueError:
            # Overlapping edits - apply one at a time
            result = source
            count = 0
            for v in sorted(violations, key=lambda x: (-x.line, -x.column)):
                if v.fix and v.fix.is_safe():
                    try:
                        result = self.apply_edits(result, v.fix.edits, check_conflicts=False)
                        count += 1
                    except Exception:
                        continue
            return result, count


# =============================================================================
# Utility Functions
# =============================================================================


def parse_ruff_json(output: str) -> list[RuffViolation]:
    """
    Parse Ruff JSON output into violations.

    Args:
        output: JSON string from ruff check --output-format=json

    Returns:
        List of RuffViolation objects.
    """
    if not output.strip():
        return []

    data = json.loads(output)
    return [RuffViolation.from_dict(v) for v in data]


def format_violations(
    violations: list[RuffViolation],
    *,
    group_by: Literal["file", "code", "category"] = "file",
    show_fixes: bool = False,
) -> str:
    """
    Format violations for display.

    Args:
        violations: List of violations to format.
        group_by: How to group violations.
        show_fixes: Whether to show fix information.

    Returns:
        Formatted string.
    """
    if not violations:
        return "No violations found."

    lines = []

    if group_by == "file":
        by_file: dict[str, list[RuffViolation]] = {}
        for v in violations:
            by_file.setdefault(v.filename, []).append(v)

        for filename, file_violations in sorted(by_file.items()):
            lines.append(f"\n{filename}:")
            for v in sorted(file_violations, key=lambda x: (x.line, x.column)):
                lines.append(f"  {v.line}:{v.column}: {v.code} {v.message}")
                if show_fixes and v.fix:
                    lines.append(f"    Fix: {v.fix.message}")

    elif group_by == "code":
        by_code: dict[str, list[RuffViolation]] = {}
        for v in violations:
            by_code.setdefault(v.code, []).append(v)

        for code, code_violations in sorted(by_code.items()):
            lines.append(f"\n{code} ({len(code_violations)} violations):")
            for v in code_violations[:5]:  # Show first 5
                lines.append(f"  {v.filename}:{v.line}: {v.message}")
            if len(code_violations) > 5:
                lines.append(f"  ... and {len(code_violations) - 5} more")

    elif group_by == "category":
        by_cat: dict[str, list[RuffViolation]] = {}
        for v in violations:
            by_cat.setdefault(v.category, []).append(v)

        for cat, cat_violations in sorted(by_cat.items()):
            lines.append(f"\n{cat} ({len(cat_violations)} violations):")
            for v in cat_violations[:5]:
                lines.append(f"  {v.code}: {v.message}")
            if len(cat_violations) > 5:
                lines.append(f"  ... and {len(cat_violations) - 5} more")

    return "\n".join(lines)
