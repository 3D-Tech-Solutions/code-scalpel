#!/usr/bin/env python3
"""
mypy Parser — Static Type Checking Integration
=================================================

[20260120_DOCS] Polished public overview and roadmap

What this parser does
---------------------
- Parse mypy text/JSON output into structured diagnostics and revealed types
- Compute type coverage metrics, detect missing stubs, and suggest typeshed packages
- Load mypy configuration (pyproject.toml / mypy.ini / setup.cfg) and map it to CLI args

Status at a glance
------------------
- Implementation: MOSTLY COMPLETED (P2 - HIGH)
- Completed: text/JSON parsing, revealed types, type coverage, config parsing
- In progress: incremental-mode optimization, stub-generation hints, plugin guidance
- Not implemented: .pyi parsing; stub/implementation consistency checks

Tier roadmap (summary)
----------------------
- Community (P0-P2): core checking, severity mapping, coverage calculation (mostly done)
- Pro (P1-P3): protocol/generic/advanced type features (planned)
- Enterprise (P2-P4): multi-project analysis and type quality metrics (planned)

Test inventory (est.)
---------------------
- Total: 280 tests | Community 120 | Pro 95 | Enterprise 65
"""

from __future__ import annotations

import ast
import configparser
import re
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

# Try to import json for JSON output parsing
import json

# =============================================================================
# Typeshed Suggestions - Common packages and their type stub packages
# =============================================================================

TYPESHED_SUGGESTIONS: dict[str, str] = {
    # Web frameworks
    "requests": "types-requests",
    "flask": "types-Flask",
    "aiohttp": "types-aiohttp-cors",
    "werkzeug": "types-Werkzeug",
    "jinja2": "types-Jinja2",
    "click": "types-click",
    "itsdangerous": "types-itsdangerous",
    # Data/serialization
    "pyyaml": "types-PyYAML",
    "yaml": "types-PyYAML",
    "toml": "types-toml",
    "simplejson": "types-simplejson",
    "ujson": "types-ujson",
    "orjson": "types-orjson",
    "jsonschema": "types-jsonschema",
    "protobuf": "types-protobuf",
    # Database
    "redis": "types-redis",
    "pymysql": "types-PyMySQL",
    "psycopg2": "types-psycopg2",
    "pymongo": "types-pymongo",
    "sqlalchemy": "sqlalchemy-stubs",
    # AWS/Cloud
    "boto3": "boto3-stubs",
    "botocore": "botocore-stubs",
    "aiobotocore": "types-aiobotocore",
    # Testing
    "mock": "types-mock",
    "freezegun": "types-freezegun",
    "factory_boy": "types-factory-boy",
    # CLI/Terminal
    "colorama": "types-colorama",
    "tabulate": "types-tabulate",
    "tqdm": "types-tqdm",
    "pygments": "types-Pygments",
    # Crypto/Security
    "cryptography": "types-cryptography",
    "passlib": "types-passlib",
    "pyopenssl": "types-pyOpenSSL",
    "python_jose": "types-python-jose",
    # Date/Time
    "pytz": "types-pytz",
    "dateutil": "types-python-dateutil",
    "python_dateutil": "types-python-dateutil",
    "pendulum": "types-pendulum",
    # Networking
    "paramiko": "types-paramiko",
    "pexpect": "types-pexpect",
    # Misc
    "pillow": "types-Pillow",
    "pil": "types-Pillow",
    "markdown": "types-Markdown",
    "docutils": "types-docutils",
    "decorator": "types-decorator",
    "cachetools": "types-cachetools",
    "retry": "types-retry",
    "pkg_resources": "types-setuptools",
    "setuptools": "types-setuptools",
    "chardet": "types-chardet",
    "filelock": "types-filelock",
    "beautifulsoup4": "types-beautifulsoup4",
    "bs4": "types-beautifulsoup4",
    "lxml": "lxml-stubs",
    "html5lib": "types-html5lib",
    "six": "types-six",
    "pyserial": "types-pyserial",
}


# =============================================================================
# Enums
# =============================================================================


class MypySeverity(Enum):
    """Severity levels for mypy diagnostics."""

    ERROR = "error"
    WARNING = "warning"
    NOTE = "note"


class MypyErrorCategory(Enum):
    """Categories of mypy errors."""

    TYPE_ARG = auto()  # Invalid type arguments
    RETURN_VALUE = auto()  # Return type mismatch
    ARG_TYPE = auto()  # Argument type mismatch
    ASSIGNMENT = auto()  # Assignment type mismatch
    ATTR_DEFINED = auto()  # Attribute not defined
    NAME_DEFINED = auto()  # Name not defined
    CALL_ARG = auto()  # Call argument issues
    OVERRIDE = auto()  # Method override issues
    MISC = auto()  # Miscellaneous
    IMPORT = auto()  # Import errors
    SYNTAX = auto()  # Syntax errors
    UNREACHABLE = auto()  # Unreachable code
    REDUNDANT = auto()  # Redundant code
    TYPE_VAR = auto()  # TypeVar issues
    UNION_ATTR = auto()  # Union attribute access
    TRUTHY = auto()  # Truthy/falsy issues
    OPERATOR = auto()  # Operator type issues
    INDEX = auto()  # Index/subscript issues


# Error code to category mapping
ERROR_CODE_CATEGORIES: dict[str, MypyErrorCategory] = {
    "type-arg": MypyErrorCategory.TYPE_ARG,
    "return-value": MypyErrorCategory.RETURN_VALUE,
    "return": MypyErrorCategory.RETURN_VALUE,
    "arg-type": MypyErrorCategory.ARG_TYPE,
    "assignment": MypyErrorCategory.ASSIGNMENT,
    "attr-defined": MypyErrorCategory.ATTR_DEFINED,
    "name-defined": MypyErrorCategory.NAME_DEFINED,
    "call-arg": MypyErrorCategory.CALL_ARG,
    "call-overload": MypyErrorCategory.CALL_ARG,
    "override": MypyErrorCategory.OVERRIDE,
    "misc": MypyErrorCategory.MISC,
    "import": MypyErrorCategory.IMPORT,
    "syntax": MypyErrorCategory.SYNTAX,
    "unreachable": MypyErrorCategory.UNREACHABLE,
    "redundant-cast": MypyErrorCategory.REDUNDANT,
    "redundant-self": MypyErrorCategory.REDUNDANT,
    "type-var": MypyErrorCategory.TYPE_VAR,
    "union-attr": MypyErrorCategory.UNION_ATTR,
    "truthy-bool": MypyErrorCategory.TRUTHY,
    "truthy-iterable": MypyErrorCategory.TRUTHY,
    "operator": MypyErrorCategory.OPERATOR,
    "index": MypyErrorCategory.INDEX,
}


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class MypyError:
    """A single mypy diagnostic."""

    file: str
    line: int
    column: int | None
    message: str
    severity: MypySeverity
    code: str | None = None  # Error code like "return-value"
    hint: str | None = None  # Additional hint or note
    related_notes: list[MypyError] = field(default_factory=list)
    context: str | None = None  # Source context if --show-error-context
    end_line: int | None = None  # End line for multi-line errors (JSON output)
    end_column: int | None = None  # End column (JSON output)

    @property
    def category(self) -> MypyErrorCategory:
        """Get the error category."""
        if self.code and self.code in ERROR_CODE_CATEGORIES:
            return ERROR_CODE_CATEGORIES[self.code]
        return MypyErrorCategory.MISC

    @property
    def location(self) -> str:
        """Get formatted location string."""
        if self.column is not None:
            return f"{self.file}:{self.line}:{self.column}"
        return f"{self.file}:{self.line}"

    def format(self, *, show_notes: bool = True, show_context: bool = True) -> str:
        """Format the error for display."""
        parts = [f"{self.location}: {self.severity.value}: {self.message}"]
        if self.code:
            parts[0] += f" [{self.code}]"
        if show_context and self.context:
            parts.append(f"  Context: {self.context}")
        if show_notes:
            for note in self.related_notes:
                parts.append(f"  {note.location}: {note.message}")
        return "\n".join(parts)

    @classmethod
    def from_line(cls, line: str, *, context_line: str | None = None) -> MypyError | None:
        """
        Parse a mypy output line.

        Format: file:line:column: severity: message [code]

        Args:
            line: The mypy output line to parse.
            context_line: Optional context line (from --show-error-context).

        Returns:
            MypyError if successfully parsed, None otherwise.
        """
        # Pattern: file:line(:column)?: severity: message
        pattern = r"^(.+):(\d+)(?::(\d+))?: (\w+): (.+?)(?:\s+\[(.+)\])?$"
        match = re.match(pattern, line.strip())

        if not match:
            return None

        file, line_str, col_str, severity_str, message, code = match.groups()

        try:
            severity = MypySeverity(severity_str)
        except ValueError:
            severity = MypySeverity.NOTE

        return cls(
            file=file,
            line=int(line_str),
            column=int(col_str) if col_str else None,
            message=message,
            severity=severity,
            code=code,
            context=context_line,
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MypyError:
        """
        Create MypyError from mypy JSON output.

        mypy JSON format (--output=json):
            {
                "file": "example.py",
                "line": 10,
                "column": 5,
                "message": "Incompatible return value type",
                "hint": "Expected str, got int",
                "code": "return-value",
                "severity": "error"
            }

        Args:
            data: Dictionary from mypy JSON output.

        Returns:
            MypyError populated from JSON data.
        """
        severity_str = data.get("severity", "error")
        try:
            severity = MypySeverity(severity_str)
        except ValueError:
            severity = MypySeverity.ERROR

        return cls(
            file=data.get("file", "<unknown>"),
            line=data.get("line", 1),
            column=data.get("column"),
            message=data.get("message", ""),
            severity=severity,
            code=data.get("code"),
            hint=data.get("hint"),
            end_line=data.get("end_line"),
            end_column=data.get("end_column"),
        )


@dataclass
class RevealedType:
    """
    A revealed type from reveal_type() or reveal_locals().

    Attributes:
        file: Source file path.
        line: Line number of the reveal_type() call.
        variable_name: Variable name (None for expression types).
        revealed_type: The type string revealed by mypy.
        is_inferred: True if type was inferred, False if explicitly annotated.
        narrowing_context: Type narrowing conditions active at this point.
    """

    file: str
    line: int
    variable_name: str | None  # None for expression types
    revealed_type: str
    is_inferred: bool = True  # vs explicitly annotated
    narrowing_context: list[str] = field(default_factory=list)  # Active type narrowing

    @property
    def is_union(self) -> bool:
        """Check if the revealed type is a Union type."""
        return "Union[" in self.revealed_type or "|" in self.revealed_type

    @property
    def is_optional(self) -> bool:
        """Check if the revealed type is Optional (Union with None)."""
        return "None" in self.revealed_type and self.is_union

    @property
    def base_type(self) -> str:
        """Get the base type without generics."""
        # Extract base type from e.g. "builtins.list[builtins.str]"
        if "[" in self.revealed_type:
            return self.revealed_type.split("[")[0]
        return self.revealed_type

    @classmethod
    def from_note(cls, error: MypyError, *, narrowing_context: list[str] | None = None) -> RevealedType | None:
        """
        Parse a reveal_type note from mypy output.

        Args:
            error: MypyError note to parse.
            narrowing_context: Optional list of active type narrowing conditions.

        Returns:
            RevealedType if successfully parsed, None otherwise.
        """
        if error.severity != MypySeverity.NOTE:
            return None

        # Pattern: Revealed type is "type"
        match = re.match(r'Revealed type is "(.+)"', error.message)
        if match:
            return cls(
                file=error.file,
                line=error.line,
                variable_name=None,
                revealed_type=match.group(1),
                narrowing_context=narrowing_context or [],
            )

        # Pattern for reveal_locals: varname: type
        match = re.match(r"(\w+): (.+)", error.message)
        if match:
            return cls(
                file=error.file,
                line=error.line,
                variable_name=match.group(1),
                revealed_type=match.group(2),
                narrowing_context=narrowing_context or [],
            )

        return None


@dataclass
class TypeCoverageInfo:
    """Type coverage statistics."""

    total_functions: int = 0
    typed_functions: int = 0
    partially_typed_functions: int = 0
    untyped_functions: int = 0

    total_variables: int = 0
    typed_variables: int = 0

    total_parameters: int = 0
    typed_parameters: int = 0

    explicit_any_count: int = 0
    implicit_any_count: int = 0

    missing_stubs: list[str] = field(default_factory=list)

    @property
    def function_coverage(self) -> float:
        """Percentage of functions with complete type annotations."""
        if self.total_functions == 0:
            return 100.0
        return (self.typed_functions / self.total_functions) * 100

    @property
    def parameter_coverage(self) -> float:
        """Percentage of parameters with type annotations."""
        if self.total_parameters == 0:
            return 100.0
        return (self.typed_parameters / self.total_parameters) * 100

    @property
    def overall_coverage(self) -> float:
        """Overall type coverage percentage."""
        total = self.total_functions + self.total_variables
        if total == 0:
            return 100.0
        typed = self.typed_functions + self.typed_variables
        return (typed / total) * 100

    @property
    def any_usage_percentage(self) -> float:
        """Percentage of Any usage (explicit + implicit)."""
        typed_things = self.typed_functions + self.typed_variables
        if typed_things == 0:
            return 0.0
        any_count = self.explicit_any_count + self.implicit_any_count
        return (any_count / typed_things) * 100


@dataclass
class MypyConfig:
    """Configuration for mypy analysis."""

    python_version: str = "3.11"
    strict: bool = False
    strict_optional: bool = True
    warn_return_any: bool = True
    warn_unused_configs: bool = True
    warn_redundant_casts: bool = True
    warn_unused_ignores: bool = True
    warn_unreachable: bool = False
    show_error_codes: bool = True
    show_error_context: bool = False
    show_column_numbers: bool = True
    ignore_missing_imports: bool = False
    follow_imports: Literal["normal", "silent", "skip", "error"] = "normal"
    plugins: list[str] = field(default_factory=list)
    per_module_config: dict[str, dict[str, Any]] = field(default_factory=dict)

    @classmethod
    def from_file(cls, path: Path) -> MypyConfig:
        """
        Load configuration from mypy.ini, setup.cfg, or pyproject.toml.

        Args:
            path: Path to configuration file.

        Returns:
            MypyConfig populated from file.

        Raises:
            ValueError: If file type is not supported.
        """
        path = Path(path)

        if path.name == "pyproject.toml":
            return cls._from_pyproject(path)
        elif path.name in ("mypy.ini", ".mypy.ini"):
            return cls._from_ini(path, section="mypy")
        elif path.name == "setup.cfg":
            return cls._from_ini(path, section="mypy")
        else:
            raise ValueError(f"Unsupported config file: {path.name}")

    @classmethod
    def _from_pyproject(cls, path: Path) -> MypyConfig:
        """Load configuration from pyproject.toml."""
        if tomllib is None:
            raise ImportError("tomllib (Python 3.11+) or tomli is required for TOML parsing")

        with open(path, "rb") as f:
            data = tomllib.load(f)

        mypy_config = data.get("tool", {}).get("mypy", {})
        return cls._from_dict(mypy_config)

    @classmethod
    def _from_ini(cls, path: Path, section: str = "mypy") -> MypyConfig:
        """Load configuration from INI file (mypy.ini or setup.cfg)."""
        parser = configparser.ConfigParser()
        parser.read(path)

        config = cls()

        if section not in parser:
            return config

        s = parser[section]

        # Parse string options
        if "python_version" in s:
            config.python_version = s["python_version"]
        if "follow_imports" in s:
            config.follow_imports = s["follow_imports"]  # type: ignore[assignment]
        if "plugins" in s:
            config.plugins = [p.strip() for p in s["plugins"].split(",")]

        # Parse boolean options with fallback to current value
        if "strict" in s:
            config.strict = s.getboolean("strict", fallback=config.strict)
        if "strict_optional" in s:
            config.strict_optional = s.getboolean("strict_optional", fallback=config.strict_optional)
        if "warn_return_any" in s:
            config.warn_return_any = s.getboolean("warn_return_any", fallback=config.warn_return_any)
        if "warn_unused_configs" in s:
            config.warn_unused_configs = s.getboolean("warn_unused_configs", fallback=config.warn_unused_configs)
        if "warn_redundant_casts" in s:
            config.warn_redundant_casts = s.getboolean("warn_redundant_casts", fallback=config.warn_redundant_casts)
        if "warn_unused_ignores" in s:
            config.warn_unused_ignores = s.getboolean("warn_unused_ignores", fallback=config.warn_unused_ignores)
        if "warn_unreachable" in s:
            config.warn_unreachable = s.getboolean("warn_unreachable", fallback=config.warn_unreachable)
        if "show_error_codes" in s:
            config.show_error_codes = s.getboolean("show_error_codes", fallback=config.show_error_codes)
        if "show_error_context" in s:
            config.show_error_context = s.getboolean("show_error_context", fallback=config.show_error_context)
        if "show_column_numbers" in s:
            config.show_column_numbers = s.getboolean("show_column_numbers", fallback=config.show_column_numbers)
        if "ignore_missing_imports" in s:
            config.ignore_missing_imports = s.getboolean(
                "ignore_missing_imports", fallback=config.ignore_missing_imports
            )

        # Parse per-module configuration
        for section_name in parser.sections():
            if section_name.startswith("mypy-"):
                module = section_name[5:]  # Remove "mypy-" prefix
                config.per_module_config[module] = dict(parser[section_name])

        return config

    @classmethod
    def _from_dict(cls, data: dict[str, Any]) -> MypyConfig:
        """Create MypyConfig from a dictionary."""
        config = cls()

        # Handle both underscore and hyphen naming
        def get(key: str) -> Any:
            return data.get(key) or data.get(key.replace("_", "-"))

        if get("python_version"):
            config.python_version = str(get("python_version"))
        if get("strict") is not None:
            config.strict = bool(get("strict"))
        if get("strict_optional") is not None:
            config.strict_optional = bool(get("strict_optional"))
        if get("warn_return_any") is not None:
            config.warn_return_any = bool(get("warn_return_any"))
        if get("warn_unused_configs") is not None:
            config.warn_unused_configs = bool(get("warn_unused_configs"))
        if get("warn_redundant_casts") is not None:
            config.warn_redundant_casts = bool(get("warn_redundant_casts"))
        if get("warn_unused_ignores") is not None:
            config.warn_unused_ignores = bool(get("warn_unused_ignores"))
        if get("warn_unreachable") is not None:
            config.warn_unreachable = bool(get("warn_unreachable"))
        if get("show_error_codes") is not None:
            config.show_error_codes = bool(get("show_error_codes"))
        if get("show_error_context") is not None:
            config.show_error_context = bool(get("show_error_context"))
        if get("show_column_numbers") is not None:
            config.show_column_numbers = bool(get("show_column_numbers"))
        if get("ignore_missing_imports") is not None:
            config.ignore_missing_imports = bool(get("ignore_missing_imports"))
        if get("follow_imports"):
            config.follow_imports = get("follow_imports")
        if get("plugins"):
            config.plugins = list(get("plugins"))

        # Handle overrides section for per-module config
        if "overrides" in data:
            for override in data["overrides"]:
                if "module" in override:
                    modules = override["module"]
                    if isinstance(modules, str):
                        modules = [modules]
                    for module in modules:
                        config.per_module_config[module] = {k: v for k, v in override.items() if k != "module"}

        return config

    @classmethod
    def find_config(cls, start_path: Path) -> MypyConfig | None:
        """
        Find and load configuration from the nearest config file.

        Searches upward from start_path for:
        1. mypy.ini
        2. .mypy.ini
        3. setup.cfg (with [mypy] section)
        4. pyproject.toml (with [tool.mypy])

        Args:
            start_path: Path to start searching from.

        Returns:
            MypyConfig if found, None otherwise.
        """
        current = start_path.resolve()
        if current.is_file():
            current = current.parent

        while current != current.parent:
            # Check for mypy.ini
            mypy_ini = current / "mypy.ini"
            if mypy_ini.exists():
                try:
                    return cls.from_file(mypy_ini)
                except Exception:
                    pass

            # Check for .mypy.ini
            dot_mypy_ini = current / ".mypy.ini"
            if dot_mypy_ini.exists():
                try:
                    return cls.from_file(dot_mypy_ini)
                except Exception:
                    pass

            # Check for setup.cfg
            setup_cfg = current / "setup.cfg"
            if setup_cfg.exists():
                try:
                    parser = configparser.ConfigParser()
                    parser.read(setup_cfg)
                    if "mypy" in parser:
                        return cls.from_file(setup_cfg)
                except Exception:
                    pass

            # Check for pyproject.toml
            pyproject = current / "pyproject.toml"
            if pyproject.exists():
                try:
                    config = cls._from_pyproject(pyproject)
                    # Check if config has non-default values
                    if config.python_version != "3.11" or config.strict:
                        return config
                except Exception:
                    pass

            current = current.parent

        return None

    def to_cli_args(self) -> list[str]:
        """Convert configuration to CLI arguments."""
        args = []
        args.extend(["--python-version", self.python_version])

        if self.strict:
            args.append("--strict")
        if self.strict_optional:
            args.append("--strict-optional")
        if self.warn_return_any:
            args.append("--warn-return-any")
        if self.warn_redundant_casts:
            args.append("--warn-redundant-casts")
        if self.warn_unused_ignores:
            args.append("--warn-unused-ignores")
        if self.warn_unreachable:
            args.append("--warn-unreachable")
        if self.show_error_codes:
            args.append("--show-error-codes")
        if self.show_error_context:
            args.append("--show-error-context")
        if self.show_column_numbers:
            args.append("--show-column-numbers")
        if self.ignore_missing_imports:
            args.append("--ignore-missing-imports")

        args.extend(["--follow-imports", self.follow_imports])

        for plugin in self.plugins:
            args.extend(["--plugins", plugin])

        return args


@dataclass
class MypyReport:
    """Complete mypy analysis report."""

    errors: list[MypyError] = field(default_factory=list)
    revealed_types: list[RevealedType] = field(default_factory=list)
    coverage: TypeCoverageInfo | None = None
    files_analyzed: int = 0
    parse_errors: list[str] = field(default_factory=list)
    config: MypyConfig | None = None
    mypy_version: str | None = None
    success: bool = True

    @property
    def error_count(self) -> int:
        """Get count of errors (excluding notes)."""
        return sum(1 for e in self.errors if e.severity == MypySeverity.ERROR)

    @property
    def warning_count(self) -> int:
        """Get count of warnings."""
        return sum(1 for e in self.errors if e.severity == MypySeverity.WARNING)

    @property
    def errors_by_code(self) -> dict[str, list[MypyError]]:
        """Group errors by error code."""
        result: dict[str, list[MypyError]] = {}
        for e in self.errors:
            code = e.code or "unknown"
            result.setdefault(code, []).append(e)
        return result

    @property
    def errors_by_file(self) -> dict[str, list[MypyError]]:
        """Group errors by file."""
        result: dict[str, list[MypyError]] = {}
        for e in self.errors:
            result.setdefault(e.file, []).append(e)
        return result

    @property
    def errors_by_category(self) -> dict[MypyErrorCategory, list[MypyError]]:
        """Group errors by category."""
        result: dict[MypyErrorCategory, list[MypyError]] = {}
        for e in self.errors:
            result.setdefault(e.category, []).append(e)
        return result

    def get_summary(self) -> dict[str, Any]:
        """Get a summary of the report."""
        return {
            "success": self.success,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "files_analyzed": self.files_analyzed,
            "revealed_types": len(self.revealed_types),
            "coverage": {
                "function_coverage": (self.coverage.function_coverage if self.coverage else None),
                "overall_coverage": (self.coverage.overall_coverage if self.coverage else None),
            },
            "by_category": {cat.name: len(errors) for cat, errors in self.errors_by_category.items()},
        }


# =============================================================================
# Parser Class
# =============================================================================


class MypyParser:
    """
    Parser for mypy static type checker output.

    mypy is Python's most widely used static type checker. This parser
    provides structured access to type errors, coverage metrics, and
    revealed type information.

    Implementation Status:
        ✓ Text output parsing and analysis (P2-MYPY-001)
        ✓ Revealed type extraction (P2-MYPY-003)
        ✓ Type coverage calculation (P2-MYPY-002)
        ✓ Config support - from_file, find_config (P2-MYPY-004)

    Usage:
        >>> parser = MypyParser()
        >>> report = parser.analyze("example.py")
        >>> for error in report.errors:
        ...     print(f"{error.location}: {error.message}")

        >>> # Check type coverage
        >>> coverage = parser.get_type_coverage("src/")
        >>> print(f"Coverage: {coverage.overall_coverage:.1f}%")

        >>> # Load configuration
        >>> config = MypyConfig.find_config(Path("."))
    """

    def __init__(self, *, mypy_path: str = "mypy"):
        """
        Initialize the mypy parser.

        Args:
            mypy_path: Path to the mypy executable.
        """
        self.mypy_path = mypy_path
        self._version: str | None = None

    @property
    def version(self) -> str | None:
        """Get the mypy version."""
        if self._version is None:
            try:
                result = subprocess.run(
                    [self.mypy_path, "--version"],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                self._version = result.stdout.strip()
            except (subprocess.CalledProcessError, FileNotFoundError):
                pass
        return self._version

    def is_available(self) -> bool:
        """Check if mypy is available."""
        try:
            subprocess.run(
                [self.mypy_path, "--version"],
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
        config: MypyConfig | None = None,
    ) -> MypyReport:
        """
        Analyze Python files with mypy.

        Runs mypy and parses text output with error code extraction.

        Args:
            target: File, directory, or list of targets to analyze.
            config: Optional configuration override.

        Returns:
            MypyReport with errors and metadata.
        """
        report = MypyReport(config=config, mypy_version=self.version)

        # Build targets list
        if isinstance(target, (str, Path)):
            targets = [str(target)]
        else:
            targets = [str(t) for t in target]

        # Build command
        cmd = [self.mypy_path]

        if config:
            cmd.extend(config.to_cli_args())
        else:
            # Default options
            cmd.extend(
                [
                    "--show-error-codes",
                    "--show-column-numbers",
                ]
            )

        cmd.extend(targets)

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
            )

            # Parse output
            current_error: MypyError | None = None

            for line in result.stdout.splitlines():
                if not line.strip():
                    continue

                error = MypyError.from_line(line)
                if error:
                    if error.severity == MypySeverity.NOTE and current_error:
                        # Check if it's a revealed type
                        revealed = RevealedType.from_note(error)
                        if revealed:
                            report.revealed_types.append(revealed)
                        else:
                            current_error.related_notes.append(error)
                    else:
                        if current_error:
                            report.errors.append(current_error)
                        current_error = error

            # Don't forget the last error
            if current_error:
                report.errors.append(current_error)

            # Success if no errors (notes are OK)
            report.success = all(e.severity != MypySeverity.ERROR for e in report.errors)
            report.files_analyzed = len(set(e.file for e in report.errors)) or 1

            if result.stderr:
                report.parse_errors.append(result.stderr.strip())

        except FileNotFoundError:
            report.parse_errors.append(f"mypy not found at: {self.mypy_path}")
            report.success = False
        except subprocess.SubprocessError as e:
            report.parse_errors.append(f"mypy execution failed: {e}")
            report.success = False

        return report

    def analyze_json(
        self,
        target: str | Path | list[str | Path],
        *,
        config: MypyConfig | None = None,
    ) -> MypyReport:
        """
        Analyze Python files with mypy using JSON output format.

        Uses mypy's experimental --output=json format for more structured output.
        Falls back to text parsing if JSON output is not available.

        Args:
            target: File, directory, or list of targets to analyze.
            config: Optional configuration override.

        Returns:
            MypyReport with errors and metadata.
        """
        report = MypyReport(config=config, mypy_version=self.version)

        # Build targets list
        if isinstance(target, (str, Path)):
            targets = [str(target)]
        else:
            targets = [str(t) for t in target]

        # Build command with JSON output
        cmd = [self.mypy_path, "--output=json"]

        if config:
            cmd.extend(config.to_cli_args())
        else:
            cmd.extend(
                [
                    "--show-error-codes",
                    "--show-column-numbers",
                ]
            )

        cmd.extend(targets)

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
            )

            # Try to parse as JSON
            for line in result.stdout.splitlines():
                line = line.strip()
                if not line:
                    continue

                try:
                    data = json.loads(line)
                    error = MypyError.from_dict(data)

                    # Check if it's a revealed type note
                    if error.severity == MypySeverity.NOTE and "Revealed type" in error.message:
                        revealed = RevealedType.from_note(error)
                        if revealed:
                            report.revealed_types.append(revealed)
                            continue

                    report.errors.append(error)
                except json.JSONDecodeError:
                    # Fall back to text parsing
                    error = MypyError.from_line(line)
                    if error:
                        report.errors.append(error)

            # Success if no errors
            report.success = all(e.severity != MypySeverity.ERROR for e in report.errors)
            report.files_analyzed = len(set(e.file for e in report.errors)) or 1

            if result.stderr:
                # Check for unsupported --output=json flag
                if "unrecognized arguments: --output=json" in result.stderr:
                    report.parse_errors.append("mypy JSON output not supported; falling back to text parsing")
                    return self.analyze(target, config=config)
                report.parse_errors.append(result.stderr.strip())

        except FileNotFoundError:
            report.parse_errors.append(f"mypy not found at: {self.mypy_path}")
            report.success = False
        except subprocess.SubprocessError as e:
            report.parse_errors.append(f"mypy execution failed: {e}")
            report.success = False

        return report

    def analyze_with_context(
        self,
        target: str | Path | list[str | Path],
        *,
        config: MypyConfig | None = None,
    ) -> MypyReport:
        """
        Analyze Python files with --show-error-context enabled.

        This provides source code context for each error.

        Args:
            target: File, directory, or list of targets to analyze.
            config: Optional configuration override.

        Returns:
            MypyReport with errors including context.
        """
        # Create a modified config with show_error_context enabled
        if config is None:
            config = MypyConfig(show_error_context=True)
        else:
            # Create a copy with context enabled
            config = MypyConfig(
                python_version=config.python_version,
                strict=config.strict,
                strict_optional=config.strict_optional,
                warn_return_any=config.warn_return_any,
                warn_unused_configs=config.warn_unused_configs,
                warn_redundant_casts=config.warn_redundant_casts,
                warn_unused_ignores=config.warn_unused_ignores,
                warn_unreachable=config.warn_unreachable,
                show_error_codes=config.show_error_codes,
                show_error_context=True,  # Enable context
                show_column_numbers=config.show_column_numbers,
                ignore_missing_imports=config.ignore_missing_imports,
                follow_imports=config.follow_imports,
                plugins=config.plugins,
                per_module_config=config.per_module_config,
            )

        report = MypyReport(config=config, mypy_version=self.version)

        # Build targets list
        if isinstance(target, (str, Path)):
            targets = [str(target)]
        else:
            targets = [str(t) for t in target]

        # Build command
        cmd = [self.mypy_path]
        cmd.extend(config.to_cli_args())
        cmd.extend(targets)

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
            )

            # Parse output with context awareness
            lines = result.stdout.splitlines()
            current_error: MypyError | None = None
            context_buffer: list[str] = []

            i = 0
            while i < len(lines):
                line = lines[i].strip()
                if not line:
                    i += 1
                    continue

                # Check if this is an error line
                error = MypyError.from_line(line)
                if error:
                    # Save previous error with accumulated context
                    if current_error:
                        if context_buffer:
                            current_error.context = "\n".join(context_buffer)
                        report.errors.append(current_error)
                        context_buffer = []

                    if error.severity == MypySeverity.NOTE:
                        # Check if it's a revealed type
                        revealed = RevealedType.from_note(error)
                        if revealed:
                            report.revealed_types.append(revealed)
                            i += 1
                            continue
                        # Add as related note
                        if current_error:
                            current_error.related_notes.append(error)
                            i += 1
                            continue

                    current_error = error
                else:
                    # Context line (source code shown with --show-error-context)
                    if current_error and (line.startswith("    ") or line.startswith("\t")):
                        context_buffer.append(line)

                i += 1

            # Don't forget the last error
            if current_error:
                if context_buffer:
                    current_error.context = "\n".join(context_buffer)
                report.errors.append(current_error)

            report.success = all(e.severity != MypySeverity.ERROR for e in report.errors)
            report.files_analyzed = len(set(e.file for e in report.errors)) or 1

            if result.stderr:
                report.parse_errors.append(result.stderr.strip())

        except FileNotFoundError:
            report.parse_errors.append(f"mypy not found at: {self.mypy_path}")
            report.success = False
        except subprocess.SubprocessError as e:
            report.parse_errors.append(f"mypy execution failed: {e}")
            report.success = False

        return report

    def suggest_stubs(self, missing_modules: list[str]) -> dict[str, str | None]:
        """
        Suggest typeshed stub packages for missing modules.

        Args:
            missing_modules: List of module names without stubs.

        Returns:
            Dict mapping module names to suggested stub packages (or None if unknown).
        """
        suggestions: dict[str, str | None] = {}
        for module in missing_modules:
            # Normalize module name (lowercase, remove version suffixes)
            normalized = module.lower().split(".")[0].replace("-", "_")
            suggestions[module] = TYPESHED_SUGGESTIONS.get(normalized)
        return suggestions

    def check_py_typed(self, package_path: str | Path) -> bool:
        """
        Check if a package has a py.typed marker file.

        PEP 561 defines py.typed as a marker file indicating that a package
        supports type checking.

        Args:
            package_path: Path to the package directory.

        Returns:
            True if py.typed marker exists, False otherwise.
        """
        package_path = Path(package_path)
        py_typed = package_path / "py.typed"
        return py_typed.exists()

    def get_type_coverage(
        self,
        target: str | Path,
        *,
        config: MypyConfig | None = None,
    ) -> TypeCoverageInfo:
        """
        Calculate type coverage for a target.

        Uses AST analysis to count type annotations and mypy to detect
        missing stubs.

        Args:
            target: File or directory to analyze.
            config: Optional configuration override.

        Returns:
            TypeCoverageInfo with coverage statistics.
        """
        import ast
        from pathlib import Path

        coverage = TypeCoverageInfo()
        target_path = Path(target)

        # Collect all Python files
        if target_path.is_file():
            files = [target_path]
        else:
            files = list(target_path.rglob("*.py"))

        for file_path in files:
            try:
                source = file_path.read_text(encoding="utf-8")
                tree = ast.parse(source)
                self._analyze_coverage(tree, coverage)
            except (SyntaxError, UnicodeDecodeError):
                continue

        # Run mypy to detect missing stubs
        report = self.analyze(target, config=config)
        for error in report.errors:
            if error.code == "import" and "Cannot find" in error.message:
                # Extract module name from "Cannot find implementation or library stub for module named 'xxx'"
                match = re.search(r"module named ['\"](.+?)['\"]", error.message)
                if match and match.group(1) not in coverage.missing_stubs:
                    coverage.missing_stubs.append(match.group(1))

        return coverage

    def _analyze_coverage(self, tree: ast.Module, coverage: TypeCoverageInfo) -> None:
        """Analyze AST for type coverage."""
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self._analyze_function(node, coverage)
            elif isinstance(node, ast.AnnAssign):
                # Annotated variable
                coverage.total_variables += 1
                if node.annotation:
                    coverage.typed_variables += 1
                    if self._is_any_annotation(node.annotation):
                        coverage.explicit_any_count += 1
            elif isinstance(node, ast.Assign):
                # Unannotated variable (count targets)
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        coverage.total_variables += 1

    def _analyze_function(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        coverage: TypeCoverageInfo,
    ) -> None:
        """Analyze a function for type coverage."""
        coverage.total_functions += 1

        # Count parameters
        all_args = (
            node.args.posonlyargs
            + node.args.args
            + node.args.kwonlyargs
            + ([node.args.vararg] if node.args.vararg else [])
            + ([node.args.kwarg] if node.args.kwarg else [])
        )

        typed_params = 0
        for arg in all_args:
            coverage.total_parameters += 1
            if arg.annotation:
                coverage.typed_parameters += 1
                typed_params += 1
                if self._is_any_annotation(arg.annotation):
                    coverage.explicit_any_count += 1

        # Check return type
        has_return_type = node.returns is not None
        if has_return_type and self._is_any_annotation(node.returns):
            coverage.explicit_any_count += 1

        # Determine function typing status
        total_params = len(all_args)
        if total_params == 0:
            # No params - just check return type
            if has_return_type:
                coverage.typed_functions += 1
            else:
                coverage.untyped_functions += 1
                coverage.implicit_any_count += 1  # Missing return type
        else:
            if typed_params == total_params and has_return_type:
                coverage.typed_functions += 1
            elif typed_params == 0 and not has_return_type:
                coverage.untyped_functions += 1
                coverage.implicit_any_count += total_params + 1  # All params + return
            else:
                coverage.partially_typed_functions += 1
                coverage.implicit_any_count += total_params - typed_params
                if not has_return_type:
                    coverage.implicit_any_count += 1

    def _is_any_annotation(self, annotation: ast.expr | None) -> bool:
        """Check if an annotation is 'Any'."""
        if annotation is None:
            return False
        if isinstance(annotation, ast.Name) and annotation.id == "Any":
            return True
        if isinstance(annotation, ast.Attribute) and annotation.attr == "Any":
            return True
        return False

    def check_string(
        self,
        source: str,
        *,
        filename: str = "<string>",
        config: MypyConfig | None = None,
    ) -> MypyReport:
        """
        Type-check Python source code from a string.

        Note: mypy doesn't support stdin directly, so we write to a temp file.

        Args:
            source: Python source code.
            filename: Filename for error messages.
            config: Optional configuration override.

        Returns:
            MypyReport with errors and metadata.
        """
        import tempfile

        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".py",
            delete=False,
        ) as f:
            f.write(source)
            temp_path = Path(f.name)

        try:
            report = self.analyze(temp_path, config=config)
            # Rewrite file paths to use the provided filename
            for error in report.errors:
                if error.file == str(temp_path):
                    error.file = filename
            return report
        finally:
            temp_path.unlink(missing_ok=True)


# =============================================================================
# Utility Functions
# =============================================================================


def parse_mypy_output(output: str) -> list[MypyError]:
    """
    Parse mypy text output into errors.

    Args:
        output: Text output from mypy command.

    Returns:
        List of MypyError objects.
    """
    errors: list[MypyError] = []
    current_error: MypyError | None = None

    for line in output.splitlines():
        if not line.strip():
            continue

        error = MypyError.from_line(line)
        if error:
            if error.severity == MypySeverity.NOTE and current_error:
                current_error.related_notes.append(error)
            else:
                if current_error:
                    errors.append(current_error)
                current_error = error

    if current_error:
        errors.append(current_error)

    return errors


def format_type_coverage(coverage: TypeCoverageInfo) -> str:
    """Format type coverage for display."""
    lines = [
        "Type Coverage Report",
        "=" * 40,
        f"Function Coverage: {coverage.function_coverage:.1f}%",
        f"  - Fully typed: {coverage.typed_functions}",
        f"  - Partially typed: {coverage.partially_typed_functions}",
        f"  - Untyped: {coverage.untyped_functions}",
        "",
        f"Parameter Coverage: {coverage.parameter_coverage:.1f}%",
        f"  - Typed: {coverage.typed_parameters}/{coverage.total_parameters}",
        "",
        f"Variable Coverage: {coverage.typed_variables}/{coverage.total_variables}",
        "",
        "Any Usage:",
        f"  - Explicit Any: {coverage.explicit_any_count}",
        f"  - Implicit Any: {coverage.implicit_any_count}",
        "",
        f"Overall Coverage: {coverage.overall_coverage:.1f}%",
    ]

    if coverage.missing_stubs:
        lines.append("")
        lines.append("Missing Stubs:")
        for stub in coverage.missing_stubs:
            lines.append(f"  - {stub}")

    return "\n".join(lines)
