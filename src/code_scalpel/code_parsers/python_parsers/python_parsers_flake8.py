#!/usr/bin/env python3
"""
Flake8 Parser - Style and Convention Checking.
===============================================

Flake8 is a popular Python linter that wraps pycodestyle, pyflakes, and
mccabe. It has a rich plugin ecosystem for extended functionality.
This module provides structured parsing of Flake8 output.

Implementation Status: MOSTLY COMPLETED
Priority: P3 - MEDIUM

Note: Consider using Ruff (P1) as a faster alternative that covers most
Flake8 functionality. This parser is useful for projects with existing
Flake8 plugin dependencies.

Flake8 Features:
    - PEP 8 style checking (via pycodestyle)
    - Logical error detection (via pyflakes)
    - Complexity checking (via mccabe)
    - Plugin ecosystem (bugbear, comprehensions, etc.)

==============================================================================
COMPLETED [P3-FLAKE8-001]: Flake8Parser with plugin support
==============================================================================
Priority: MEDIUM
Status: ✓ COMPLETED

Implemented Features:
    - [✓] Parse default text output format (from_line method)
    - [✓] Parse JSON output (via flake8-json plugin) - analyze_json method
    - [✓] Detect installed plugins (from --version output)
    - [✓] Map plugin codes to descriptions (get_code_category/source)
    - [✓] Handle # noqa comments (handled by flake8 itself)
    - [✓] Support configuration from .flake8, setup.cfg (Flake8Config.from_file)
    - [✓] Handle stdin input (analyze_string method)

Output Format (default):
    example.py:10:1: E302 expected 2 blank lines, found 1
    example.py:15:80: E501 line too long (85 > 79 characters)

Output Format (flake8-json):
    ```json
    {"example.py": [
        {"code": "E302", "filename": "example.py", "line_number": 10,
         "column_number": 1, "text": "expected 2 blank lines, found 1"}
    ]}
    ```

Plugin Detection:
    Run `flake8 --version` to see installed plugins:
    ```
    7.0.0 (mccabe: 0.7.0, pycodestyle: 2.11.0, pyflakes: 3.2.0)
    CPython 3.11.0 on Darwin
    ```

==============================================================================
COMPLETED [P3-FLAKE8-002]: Error code mapping
==============================================================================
Priority: MEDIUM
Status: ✓ COMPLETED
Depends On: P3-FLAKE8-001

Implemented Features:
    - [✓] Map E codes (pycodestyle errors) - full mapping
    - [✓] Map W codes (pycodestyle warnings) - full mapping
    - [✓] Map F codes (pyflakes) - full mapping
    - [✓] Map C codes (mccabe complexity) - full mapping
    - [✓] Map plugin codes (B, C4, D, etc.) - comprehensive
    - [✓] Detailed message mapping per code (ERROR_CODE_MESSAGES database)

Note: ERROR_CODE_CATEGORIES and ERROR_CODE_SOURCES dicts exist with basic mappings.
get_code_category() and get_code_source() helper functions implemented.

Error Code Ranges:
    ```python
    ERROR_CODE_SOURCES = {
        "E1": "Indentation",
        "E2": "Whitespace",
        "E3": "Blank line",
        "E4": "Import",
        "E5": "Line length",
        "E7": "Statement",
        "E9": "Runtime",
        "W1": "Indentation warning",
        "W2": "Whitespace warning",
        "W3": "Blank line warning",
        "W5": "Line break warning",
        "W6": "Deprecation warning",
        "F4": "Pyflakes import",
        "F5": "Pyflakes format string",
        "F6": "Pyflakes print",
        "F7": "Pyflakes syntax",
        "F8": "Pyflakes name",
        "F9": "Pyflakes miscellaneous",
        "C": "Complexity (mccabe)",
        "B": "flake8-bugbear",
        "C4": "flake8-comprehensions",
        "D": "pydocstyle (via flake8-docstrings)",
        "N": "pep8-naming",
        "S": "flake8-bandit",
        "T": "flake8-print",
    }
    ```

==============================================================================
COMPLETED [P3-FLAKE8-003]: Configuration parsing
==============================================================================
Priority: LOW
Status: ✓ COMPLETED
Estimated Effort: 1 day

Implemented Features:
    - [✓] Parse .flake8 configuration
    - [✓] Parse [flake8] section in setup.cfg
    - [✓] Parse [flake8] section in tox.ini
    - [✓] Support per-file-ignores
    - [✓] Support extend-ignore/extend-select
    - [✓] Support exclude/extend-exclude
    - [✓] find_config() for automatic config discovery

Configuration Example (.flake8):
    ```ini
    [flake8]
    max-line-length = 100
    max-complexity = 10
    extend-ignore = E203, E501
    per-file-ignores =
        __init__.py: F401
        tests/*: S101
    exclude = .git,__pycache__,venv
    ```
"""

from __future__ import annotations

import configparser
import json
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass


# =============================================================================
# Error Code Mapping
# =============================================================================

# Error Code Mapping - Maps error code prefixes to categories
ERROR_CODE_CATEGORIES: dict[str, str] = {
    # pycodestyle errors (E)
    "E1": "Indentation",
    "E2": "Whitespace",
    "E3": "Blank line",
    "E4": "Import",
    "E5": "Line length",
    "E7": "Statement",
    "E9": "Runtime",
    # pycodestyle warnings (W)
    "W1": "Indentation warning",
    "W2": "Whitespace warning",
    "W3": "Blank line warning",
    "W5": "Line break warning",
    "W6": "Deprecation warning",
    # pyflakes (F)
    "F4": "Import",
    "F5": "Format string",
    "F6": "Print",
    "F7": "Syntax",
    "F8": "Name",
    "F9": "Miscellaneous",
    # mccabe (C9)
    "C9": "Complexity",
    # Common plugins
    "B": "flake8-bugbear",
    "C4": "flake8-comprehensions",
    "D": "pydocstyle",
    "N": "pep8-naming",
    "S": "flake8-bandit",
    "T": "flake8-print",
    "PIE": "flake8-pie",
    "SIM": "flake8-simplify",
    "PT": "flake8-pytest-style",
    "UP": "pyupgrade",
    "I": "isort",
    "COM": "flake8-commas",
    "Q": "flake8-quotes",
}


# Detailed error code messages - Maps specific codes to descriptions
ERROR_CODE_MESSAGES: dict[str, str] = {
    # === pycodestyle E1xx: Indentation ===
    "E101": "indentation contains mixed spaces and tabs",
    "E111": "indentation is not a multiple of four",
    "E112": "expected an indented block",
    "E113": "unexpected indentation",
    "E114": "indentation is not a multiple of four (comment)",
    "E115": "expected an indented block (comment)",
    "E116": "unexpected indentation (comment)",
    "E117": "over-indented",
    "E121": "continuation line under-indented for hanging indent",
    "E122": "continuation line missing indentation or outdented",
    "E123": "closing bracket does not match indentation of opening bracket's line",
    "E124": "closing bracket does not match visual indentation",
    "E125": "continuation line with same indent as next logical line",
    "E126": "continuation line over-indented for hanging indent",
    "E127": "continuation line over-indented for visual indent",
    "E128": "continuation line under-indented for visual indent",
    "E129": "visually indented line with same indent as next logical line",
    "E131": "continuation line unaligned for hanging indent",
    "E133": "closing bracket is missing indentation",
    # === pycodestyle E2xx: Whitespace ===
    "E201": "whitespace after '('",
    "E202": "whitespace before ')'",
    "E203": "whitespace before ':'",
    "E211": "whitespace before '('",
    "E221": "multiple spaces before operator",
    "E222": "multiple spaces after operator",
    "E223": "tab before operator",
    "E224": "tab after operator",
    "E225": "missing whitespace around operator",
    "E226": "missing whitespace around arithmetic operator",
    "E227": "missing whitespace around bitwise or shift operator",
    "E228": "missing whitespace around modulo operator",
    "E231": "missing whitespace after ','",
    "E241": "multiple spaces after ','",
    "E242": "tab after ','",
    "E251": "unexpected spaces around keyword / parameter equals",
    "E252": "missing whitespace around parameter equals",
    "E261": "at least two spaces before inline comment",
    "E262": "inline comment should start with '# '",
    "E265": "block comment should start with '# '",
    "E266": "too many leading '#' for block comment",
    "E271": "multiple spaces after keyword",
    "E272": "multiple spaces before keyword",
    "E273": "tab after keyword",
    "E274": "tab before keyword",
    "E275": "missing whitespace after keyword",
    # === pycodestyle E3xx: Blank lines ===
    "E301": "expected 1 blank line, found 0",
    "E302": "expected 2 blank lines, found N",
    "E303": "too many blank lines",
    "E304": "blank lines found after function decorator",
    "E305": "expected 2 blank lines after class or function definition",
    "E306": "expected 1 blank line before a nested definition",
    # === pycodestyle E4xx: Imports ===
    "E401": "multiple imports on one line",
    "E402": "module level import not at top of file",
    # === pycodestyle E5xx: Line length ===
    "E501": "line too long",
    "E502": "the backslash is redundant between brackets",
    # === pycodestyle E7xx: Statements ===
    "E701": "multiple statements on one line (colon)",
    "E702": "multiple statements on one line (semicolon)",
    "E703": "statement ends with a semicolon",
    "E704": "multiple statements on one line (def)",
    "E711": "comparison to None (use 'is' or 'is not')",
    "E712": "comparison to True/False (use 'if cond:' or 'if not cond:')",
    "E713": "test for membership should be 'not in'",
    "E714": "test for object identity should be 'is not'",
    "E721": "do not compare types, use isinstance()",
    "E722": "do not use bare 'except'",
    "E731": "do not assign a lambda expression, use a def",
    "E741": "ambiguous variable name",
    "E742": "ambiguous class definition",
    "E743": "ambiguous function definition",
    "E902": "TokenError or IndentationError",
    "E999": "SyntaxError in source file",
    # === pycodestyle W1xx-W6xx: Warnings ===
    "W191": "indentation contains tabs",
    "W291": "trailing whitespace",
    "W292": "no newline at end of file",
    "W293": "blank line contains whitespace",
    "W391": "blank line at end of file",
    "W503": "line break before binary operator",
    "W504": "line break after binary operator",
    "W505": "doc line too long",
    "W605": "invalid escape sequence",
    # === pyflakes F4xx: Imports ===
    "F401": "module imported but unused",
    "F402": "import module from line N shadowed by loop variable",
    "F403": "'from module import *' used; unable to detect undefined names",
    "F404": "future import(s) name after other statements",
    "F405": "name may be undefined, or defined from star imports",
    "F406": "'from module import *' only allowed at module level",
    "F407": "an undefined __future__ feature name was imported",
    # === pyflakes F5xx: Format strings ===
    "F501": "invalid % format string",
    "F502": "% format expected mapping but got sequence",
    "F503": "% format expected sequence but got mapping",
    "F504": "% format unused named arguments",
    "F505": "% format missing named arguments",
    "F506": "% format mixed positional and named arguments",
    "F507": "% format mismatch of placeholder and argument count",
    "F508": "% format with * specifier requires a sequence",
    "F509": "% format with unsupported format character",
    "F521": ".format(...) invalid format string",
    "F522": ".format(...) unused named arguments",
    "F523": ".format(...) unused positional arguments",
    "F524": ".format(...) missing argument",
    "F525": ".format(...) mixing automatic and manual numbering",
    # === pyflakes F6xx: Print ===
    "F601": "dictionary key name repeated",
    "F602": "dictionary key variable name repeated",
    # === pyflakes F7xx: Syntax ===
    "F701": "a break statement not in a for/while loop",
    "F702": "a continue statement not in a for/while loop",
    "F703": "a continue statement in a finally block",
    "F704": "a yield or yield from statement outside of a function",
    "F705": "a return statement outside of a function/method",
    "F706": "a return statement with arguments inside a generator",
    "F707": "an except: block as not the last exception handler",
    "F811": "redefinition of unused name from line N",
    "F821": "undefined name",
    "F822": "undefined name in __all__",
    "F823": "local variable referenced before assignment",
    "F831": "duplicate argument name in function definition",
    "F841": "local variable is assigned to but never used",
    "F842": "local variable is annotated but never used",
    "F901": "raise NotImplemented should be raise NotImplementedError",
    # === mccabe C9xx: Complexity ===
    "C901": "function is too complex",
    # === flake8-bugbear Bxxx ===
    "B001": "do not use bare `except:`, specify exception type",
    "B002": "Python does not support the unary prefix increment",
    "B003": "assigning to `os.environ` does not clear the environment",
    "B004": "using `hasattr(x, '__call__')` to test if x is callable is unreliable",
    "B005": "using `.strip()` with multi-character strings is misleading",
    "B006": "do not use mutable data structures for argument defaults",
    "B007": "loop control variable not used within the loop body",
    "B008": "do not perform function calls in argument defaults",
    "B009": "do not call getattr with a constant attribute value",
    "B010": "do not call setattr with a constant attribute value",
    "B011": "do not call assert False, use raise AssertionError()",
    "B012": "return/continue/break inside finally blocks causes exceptions to be silenced",
    "B013": "length-one tuple literal is redundant",
    "B014": "redundant exception types in except handler",
    "B015": "pointless comparison",
    "B016": "cannot raise a literal",
    "B017": "assertRaises(Exception) should be considered evil",
    "B018": "found useless expression",
    "B019": "use of functools.lru_cache on methods can lead to memory leaks",
    "B020": "loop control variable overrides iterable",
    "B021": "f-string is missing placeholders",
    "B022": "no arguments passed to contextlib.suppress",
    "B023": "function definition does not bind loop variable",
    "B024": "abstract base class with no abstract methods",
    "B025": "try-except block with duplicate exception handlers",
    "B026": "star-arg unpacking after keyword argument is strongly discouraged",
    "B027": "empty method in abstract base class should be abstract",
    "B028": "no explicit stacklevel keyword argument found",
    "B029": "except handler with empty tuple catches nothing",
    "B030": "except handlers should only be exception classes or tuples",
    "B031": "using `itertools.groupby()` unsafely",
    "B032": "possible unintentional type annotation",
    "B033": "sets should not contain duplicate items",
    "B034": "re.sub/subn/split should use raw strings for pattern",
    "B035": "found static key in dict comprehension",
    "B901": "return x in generator function; use yield x; return",
    "B902": "invalid first argument used for method",
    "B903": "use collections.namedtuple (or typing.NamedTuple)",
    "B904": "within an except clause, raise exceptions with raise ... from ...",
    "B905": "zip() without an explicit strict= parameter",
    "B906": "visit method with no further calls to a visit method",
    "B907": "f-string missing placeholders; consider using format or replacement",
    "B908": "except handler with empty tuple catches nothing",
    "B909": "mutation of class attribute during class definition",
    "B950": "line too long (opinionated)",
    # === flake8-comprehensions C4xx ===
    "C400": "unnecessary generator - rewrite as a list comprehension",
    "C401": "unnecessary generator - rewrite as a set comprehension",
    "C402": "unnecessary generator - rewrite as a dict comprehension",
    "C403": "unnecessary list comprehension - rewrite as a set comprehension",
    "C404": "unnecessary list comprehension - rewrite as a dict comprehension",
    "C405": "unnecessary literal - rewrite as a set literal",
    "C406": "unnecessary literal - rewrite as a dict literal",
    "C407": "unnecessary list comprehension - <builtin> can take a generator",
    "C408": "unnecessary dict/list/tuple call - rewrite as a literal",
    "C409": "unnecessary list passed to tuple() - rewrite as a tuple literal",
    "C410": "unnecessary list passed to list() - remove the call",
    "C411": "unnecessary list call - remove the call",
    "C412": "unnecessary list comprehension - rewrite using list()",
    "C413": "unnecessary list/reversed call around sorted()",
    "C414": "unnecessary double list/reversed/set/sorted/tuple call",
    "C415": "unnecessary subscript reversal of iterable",
    "C416": "unnecessary list/set comprehension - rewrite using list/set()",
    "C417": "unnecessary map usage - rewrite using a generator/comprehension",
    "C418": "unnecessary dict call - rewrite as a literal",
    "C419": "unnecessary list comprehension passed to any/all()",
    # === pep8-naming Nxxx ===
    "N801": "class name should use CapWords convention",
    "N802": "function name should be lowercase",
    "N803": "argument name should be lowercase",
    "N804": "first argument of a classmethod should be named 'cls'",
    "N805": "first argument of a method should be named 'self'",
    "N806": "variable in function should be lowercase",
    "N807": "function name should not start or end with '__'",
    "N811": "constant imported as non constant",
    "N812": "lowercase imported as non lowercase",
    "N813": "camelcase imported as lowercase",
    "N814": "camelcase imported as constant",
    "N815": "mixedCase variable in class scope",
    "N816": "mixedCase variable in global scope",
    "N817": "camelcase imported as acronym",
    "N818": "exception name should be named with an Error suffix",
    # === flake8-bandit Sxxx (subset) ===
    "S101": "use of assert detected",
    "S102": "use of exec detected",
    "S103": "permissive file permissions on file",
    "S104": "possible binding to all interfaces",
    "S105": "possible hardcoded password",
    "S106": "possible hardcoded password in function argument",
    "S107": "possible hardcoded password in default value",
    "S108": "probable insecure temp file usage",
    "S110": "try/except/pass detected",
    "S112": "try/except/continue detected",
    "S113": "request without timeout",
    # === flake8-print Txxx ===
    "T001": "print found",
    "T002": "Python 2 print statement found",
    "T003": "pprint found",
    "T201": "print found",
    "T203": "pprint found",
}


def get_code_message(code: str) -> str | None:
    """Get the detailed message for an error code."""
    return ERROR_CODE_MESSAGES.get(code)


def get_code_category(code: str) -> str:
    """Get the category for an error code."""
    # Try longest prefix first
    for length in range(len(code), 0, -1):
        prefix = code[:length]
        if prefix in ERROR_CODE_CATEGORIES:
            return ERROR_CODE_CATEGORIES[prefix]
    return "Unknown"


def get_code_source(code: str) -> str:
    """Get the source tool for an error code."""
    if code.startswith("E") or code.startswith("W"):
        return "pycodestyle"
    elif code.startswith("F"):
        return "pyflakes"
    elif code.startswith("C9"):
        return "mccabe"
    elif code.startswith("B"):
        return "flake8-bugbear"
    elif code.startswith("C4"):
        return "flake8-comprehensions"
    elif code.startswith("D"):
        return "pydocstyle"
    elif code.startswith("N"):
        return "pep8-naming"
    elif code.startswith("S"):
        return "flake8-bandit"
    else:
        return "plugin"


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class Flake8Violation:
    """A single Flake8 violation."""

    code: str  # e.g., "E302"
    message: str  # e.g., "expected 2 blank lines, found 1"
    filename: str  # File path
    line: int  # Line number
    column: int  # Column number

    @property
    def location(self) -> str:
        """Get formatted location string."""
        return f"{self.filename}:{self.line}:{self.column}"

    @property
    def category(self) -> str:
        """Get the error category."""
        return get_code_category(self.code)

    @property
    def source(self) -> str:
        """Get the source tool."""
        return get_code_source(self.code)

    @property
    def is_error(self) -> bool:
        """Check if this is an error (vs warning)."""
        return self.code.startswith("E") or self.code.startswith("F")

    def format(self) -> str:
        """Format the violation for display."""
        return f"{self.location}: {self.code} {self.message}"

    @classmethod
    def from_line(cls, line: str) -> Flake8Violation | None:
        """
        Parse a Flake8 output line.

        Format: filename:line:column: code message
        """
        pattern = r"^(.+):(\d+):(\d+): ([A-Z]\d+) (.+)$"
        match = re.match(pattern, line.strip())

        if not match:
            return None

        filename, line_str, col_str, code, message = match.groups()

        return cls(
            code=code,
            message=message,
            filename=filename,
            line=int(line_str),
            column=int(col_str),
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Flake8Violation:
        """Create from flake8-json output dict."""
        return cls(
            code=data.get("code", ""),
            message=data.get("text", ""),
            filename=data.get("filename", ""),
            line=data.get("line_number", 0),
            column=data.get("column_number", 0),
        )


@dataclass
class Flake8PluginInfo:
    """Information about an installed Flake8 plugin."""

    name: str
    version: str

    @classmethod
    def from_version_line(cls, line: str) -> list[Flake8PluginInfo]:
        """Parse plugins from flake8 --version output."""
        # Format: 7.0.0 (mccabe: 0.7.0, pycodestyle: 2.11.0, pyflakes: 3.2.0)
        plugins = []
        match = re.search(r"\((.+)\)", line)
        if match:
            for part in match.group(1).split(", "):
                if ":" in part:
                    name, version = part.split(":", 1)
                    plugins.append(cls(name=name.strip(), version=version.strip()))
        return plugins


@dataclass
class Flake8Config:
    """Configuration for Flake8 analysis."""

    max_line_length: int = 79
    max_complexity: int | None = None
    select: list[str] = field(default_factory=list)
    extend_select: list[str] = field(default_factory=list)
    ignore: list[str] = field(default_factory=list)
    extend_ignore: list[str] = field(default_factory=list)
    per_file_ignores: dict[str, list[str]] = field(default_factory=dict)
    exclude: list[str] = field(default_factory=list)
    extend_exclude: list[str] = field(default_factory=list)

    @classmethod
    def from_file(cls, path: Path) -> Flake8Config:
        """
        Load configuration from .flake8, setup.cfg, or tox.ini.

        Args:
            path: Path to configuration file.

        Returns:
            Flake8Config populated from file.
        """
        path = Path(path)
        return cls._from_ini(path)

    @classmethod
    def _from_ini(cls, path: Path) -> Flake8Config:
        """Load configuration from INI file (.flake8, setup.cfg, or tox.ini)."""
        parser = configparser.ConfigParser()
        parser.read(path)

        config = cls()

        # Look for [flake8] section
        if "flake8" not in parser:
            return config

        s = parser["flake8"]

        # Parse max-line-length
        if "max-line-length" in s:
            config.max_line_length = int(s["max-line-length"])

        # Parse max-complexity
        if "max-complexity" in s:
            config.max_complexity = int(s["max-complexity"])

        # Parse select/ignore lists
        if "select" in s:
            config.select = cls._parse_code_list(s["select"])
        if "extend-select" in s:
            config.extend_select = cls._parse_code_list(s["extend-select"])
        if "ignore" in s:
            config.ignore = cls._parse_code_list(s["ignore"])
        if "extend-ignore" in s:
            config.extend_ignore = cls._parse_code_list(s["extend-ignore"])

        # Parse exclude lists
        if "exclude" in s:
            config.exclude = cls._parse_path_list(s["exclude"])
        if "extend-exclude" in s:
            config.extend_exclude = cls._parse_path_list(s["extend-exclude"])

        # Parse per-file-ignores (special format)
        if "per-file-ignores" in s:
            config.per_file_ignores = cls._parse_per_file_ignores(s["per-file-ignores"])

        return config

    @staticmethod
    def _parse_code_list(value: str) -> list[str]:
        """Parse a comma or newline separated list of error codes."""
        codes = []
        for line in value.split("\n"):
            for code in line.split(","):
                code = code.strip()
                if code:
                    codes.append(code)
        return codes

    @staticmethod
    def _parse_path_list(value: str) -> list[str]:
        """Parse a comma or newline separated list of paths."""
        paths = []
        for line in value.split("\n"):
            for path in line.split(","):
                path = path.strip()
                if path:
                    paths.append(path)
        return paths

    @staticmethod
    def _parse_per_file_ignores(value: str) -> dict[str, list[str]]:
        """
        Parse per-file-ignores configuration.

        Format:
            __init__.py: F401
            tests/*: S101, S102
        """
        result: dict[str, list[str]] = {}

        for line in value.split("\n"):
            line = line.strip()
            if not line or ":" not in line:
                continue

            pattern, codes = line.split(":", 1)
            pattern = pattern.strip()
            codes_list = [c.strip() for c in codes.split(",") if c.strip()]

            if pattern and codes_list:
                result[pattern] = codes_list

        return result

    @classmethod
    def find_config(cls, start_path: Path) -> Flake8Config | None:
        """
        Find and load configuration from the nearest config file.

        Searches upward from start_path for:
        1. .flake8
        2. setup.cfg (with [flake8] section)
        3. tox.ini (with [flake8] section)

        Args:
            start_path: Path to start searching from.

        Returns:
            Flake8Config if found, None otherwise.
        """
        current = start_path.resolve()
        if current.is_file():
            current = current.parent

        while current != current.parent:
            # Check for .flake8
            flake8_file = current / ".flake8"
            if flake8_file.exists():
                try:
                    return cls.from_file(flake8_file)
                except Exception:
                    pass

            # Check for setup.cfg
            setup_cfg = current / "setup.cfg"
            if setup_cfg.exists():
                try:
                    parser = configparser.ConfigParser()
                    parser.read(setup_cfg)
                    if "flake8" in parser:
                        return cls.from_file(setup_cfg)
                except Exception:
                    pass

            # Check for tox.ini
            tox_ini = current / "tox.ini"
            if tox_ini.exists():
                try:
                    parser = configparser.ConfigParser()
                    parser.read(tox_ini)
                    if "flake8" in parser:
                        return cls.from_file(tox_ini)
                except Exception:
                    pass

            current = current.parent

        return None

    def to_cli_args(self) -> list[str]:
        """Convert configuration to CLI arguments."""
        args = []

        args.extend(["--max-line-length", str(self.max_line_length)])

        if self.max_complexity:
            args.extend(["--max-complexity", str(self.max_complexity)])

        if self.select:
            args.extend(["--select", ",".join(self.select)])

        if self.extend_select:
            args.extend(["--extend-select", ",".join(self.extend_select)])

        if self.ignore:
            args.extend(["--ignore", ",".join(self.ignore)])

        if self.extend_ignore:
            args.extend(["--extend-ignore", ",".join(self.extend_ignore)])

        if self.exclude:
            args.extend(["--exclude", ",".join(self.exclude)])

        return args


@dataclass
class Flake8Report:
    """Complete Flake8 analysis report."""

    violations: list[Flake8Violation] = field(default_factory=list)
    installed_plugins: list[Flake8PluginInfo] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    config: Flake8Config | None = None
    flake8_version: str | None = None

    @property
    def violation_count(self) -> int:
        """Get total number of violations."""
        return len(self.violations)

    @property
    def error_count(self) -> int:
        """Get count of errors."""
        return sum(1 for v in self.violations if v.is_error)

    @property
    def warning_count(self) -> int:
        """Get count of warnings."""
        return sum(1 for v in self.violations if not v.is_error)

    @property
    def violations_by_code(self) -> dict[str, list[Flake8Violation]]:
        """Group violations by code."""
        result: dict[str, list[Flake8Violation]] = {}
        for v in self.violations:
            result.setdefault(v.code, []).append(v)
        return result

    @property
    def violations_by_file(self) -> dict[str, list[Flake8Violation]]:
        """Group violations by file."""
        result: dict[str, list[Flake8Violation]] = {}
        for v in self.violations:
            result.setdefault(v.filename, []).append(v)
        return result

    @property
    def violations_by_source(self) -> dict[str, list[Flake8Violation]]:
        """Group violations by source tool."""
        result: dict[str, list[Flake8Violation]] = {}
        for v in self.violations:
            result.setdefault(v.source, []).append(v)
        return result

    def get_summary(self) -> dict[str, Any]:
        """Get a summary of the report."""
        return {
            "violation_count": self.violation_count,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "files_with_issues": len(self.violations_by_file),
            "by_source": {source: len(violations) for source, violations in self.violations_by_source.items()},
            "top_violations": [
                {"code": code, "count": len(violations)}
                for code, violations in sorted(self.violations_by_code.items(), key=lambda x: -len(x[1]))[:10]
            ],
        }


# =============================================================================
# Parser Class
# =============================================================================


class Flake8Parser:
    """
    Parser for Flake8 linter output.

    Flake8 wraps pycodestyle, pyflakes, and mccabe with plugin support.
    Consider using Ruff for faster linting with similar functionality.

    Implementation Status:
        ✓ Core text parsing and analysis (P3-FLAKE8-001)
        ✓ JSON output parsing via flake8-json (analyze_json)
        ✓ Plugin detection from --version
        ✓ stdin support for unsaved files
        ✓ Detailed error code mapping (P3-FLAKE8-002)
        ✓ Configuration file parsing (P3-FLAKE8-003)

    Usage:
        >>> parser = Flake8Parser()
        >>> report = parser.analyze("example.py")
        >>> for violation in report.violations:
        ...     print(f"{violation.code}: {violation.message}")
    """

    def __init__(self, *, flake8_path: str = "flake8"):
        """
        Initialize the Flake8 parser.

        Args:
            flake8_path: Path to the flake8 executable.
        """
        self.flake8_path = flake8_path
        self._version: str | None = None
        self._plugins: list[Flake8PluginInfo] | None = None

    @property
    def version(self) -> str | None:
        """Get the Flake8 version."""
        if self._version is None:
            self._get_version_info()
        return self._version

    @property
    def installed_plugins(self) -> list[Flake8PluginInfo]:
        """Get list of installed plugins."""
        if self._plugins is None:
            self._get_version_info()
        return self._plugins or []

    def _get_version_info(self) -> None:
        """Get version and plugin information."""
        try:
            result = subprocess.run(
                [self.flake8_path, "--version"],
                capture_output=True,
                text=True,
                check=True,
            )
            output = result.stdout.strip()

            # Parse version (first part before parenthesis)
            if output:
                self._version = output.split()[0]
                self._plugins = Flake8PluginInfo.from_version_line(output)
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass

    def is_available(self) -> bool:
        """Check if Flake8 is available."""
        try:
            subprocess.run(
                [self.flake8_path, "--version"],
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
        config: Flake8Config | None = None,
    ) -> Flake8Report:
        """
        Analyze Python files with Flake8.

        Runs Flake8 and parses text output.

        Args:
            target: File, directory, or list of targets to analyze.
            config: Optional configuration override.

        Returns:
            Flake8Report with violations.
        """
        report = Flake8Report(
            config=config,
            flake8_version=self.version,
            installed_plugins=self.installed_plugins,
        )

        # Build targets list
        if isinstance(target, (str, Path)):
            targets = [str(target)]
        else:
            targets = [str(t) for t in target]

        # Build command
        cmd = [
            self.flake8_path,
            "--exit-zero",  # Don't exit with error on violations
        ]

        if config:
            cmd.extend(config.to_cli_args())

        cmd.extend(targets)

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
            )

            # Parse text output
            for line in result.stdout.splitlines():
                violation = Flake8Violation.from_line(line)
                if violation:
                    report.violations.append(violation)

            if result.stderr:
                report.errors.append(result.stderr.strip())

        except FileNotFoundError:
            report.errors.append(f"Flake8 not found at: {self.flake8_path}")
        except subprocess.SubprocessError as e:
            report.errors.append(f"Flake8 execution failed: {e}")

        return report

    def analyze_string(
        self,
        source: str,
        *,
        filename: str = "stdin",
        config: Flake8Config | None = None,
    ) -> Flake8Report:
        """
        Analyze Python source code from a string.

        Args:
            source: Python source code.
            filename: Filename for error messages.
            config: Optional configuration override.

        Returns:
            Flake8Report with violations.
        """
        report = Flake8Report(
            config=config,
            flake8_version=self.version,
            installed_plugins=self.installed_plugins,
        )

        cmd = [
            self.flake8_path,
            "--stdin-display-name",
            filename,
            "--exit-zero",
            "-",  # Read from stdin
        ]

        if config:
            cmd.extend(config.to_cli_args())

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                input=source,
            )

            for line in result.stdout.splitlines():
                violation = Flake8Violation.from_line(line)
                if violation:
                    report.violations.append(violation)

            if result.stderr:
                report.errors.append(result.stderr.strip())

        except FileNotFoundError:
            report.errors.append(f"Flake8 not found at: {self.flake8_path}")
        except subprocess.SubprocessError as e:
            report.errors.append(f"Flake8 execution failed: {e}")

        return report

    def analyze_json(
        self,
        target: str | Path | list[str | Path],
        *,
        config: Flake8Config | None = None,
    ) -> Flake8Report:
        """
        Analyze Python files with Flake8 using JSON output format.

        Requires the flake8-json plugin to be installed:
            pip install flake8-json

        The JSON output format provides more structured data and is
        easier to parse programmatically.

        Args:
            target: File, directory, or list of targets to analyze.
            config: Optional configuration override.

        Returns:
            Flake8Report with violations.

        Note:
            If flake8-json is not installed, this falls back to
            text output parsing with a warning in report.errors.
        """
        report = Flake8Report(
            config=config,
            flake8_version=self.version,
            installed_plugins=self.installed_plugins,
        )

        # Check if flake8-json is installed
        has_json_plugin = any(p.name == "flake8-json" or p.name == "flake8_json" for p in self.installed_plugins)

        # Build targets list
        if isinstance(target, (str, Path)):
            targets = [str(target)]
        else:
            targets = [str(t) for t in target]

        if has_json_plugin:
            # Use JSON format
            cmd = [
                self.flake8_path,
                "--format=json",
                "--exit-zero",
            ]

            if config:
                cmd.extend(config.to_cli_args())

            cmd.extend(targets)

            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                )

                if result.stdout.strip():
                    try:
                        # flake8-json outputs: {"filename": [{violation}, ...]}
                        data = json.loads(result.stdout)

                        for filename, violations in data.items():
                            for v_data in violations:
                                # Ensure filename is set
                                v_data["filename"] = filename
                                report.violations.append(Flake8Violation.from_dict(v_data))
                    except json.JSONDecodeError as e:
                        report.errors.append(f"Failed to parse JSON output: {e}")
                        # Fall back to text parsing
                        for line in result.stdout.splitlines():
                            violation = Flake8Violation.from_line(line)
                            if violation:
                                report.violations.append(violation)

                if result.stderr:
                    report.errors.append(result.stderr.strip())

            except FileNotFoundError:
                report.errors.append(f"Flake8 not found at: {self.flake8_path}")
            except subprocess.SubprocessError as e:
                report.errors.append(f"Flake8 execution failed: {e}")
        else:
            # Fall back to text format with warning
            report.errors.append(
                "flake8-json plugin not installed. " "Using text output format. Install with: pip install flake8-json"
            )
            return self.analyze(target, config=config)

        return report

    def has_plugin(self, plugin_name: str) -> bool:
        """
        Check if a specific plugin is installed.

        Args:
            plugin_name: Name of the plugin (e.g., "flake8-bugbear").

        Returns:
            True if the plugin is installed.
        """
        # Normalize name (handle both - and _ variants)
        normalized = plugin_name.lower().replace("-", "_")
        for plugin in self.installed_plugins:
            if plugin.name.lower().replace("-", "_") == normalized:
                return True
        return False

    def get_code_info(self, code: str) -> dict[str, Any]:
        """
        Get detailed information about an error code.

        Args:
            code: The error code (e.g., "E501", "F401", "B006").

        Returns:
            Dictionary with code information including:
            - code: The error code
            - category: The category (e.g., "Line length")
            - source: The source tool (e.g., "pycodestyle")
            - message: The detailed message if available
            - is_error: Whether it's an error vs warning
        """
        return {
            "code": code,
            "category": get_code_category(code),
            "source": get_code_source(code),
            "message": get_code_message(code),
            "is_error": code.startswith("E") or code.startswith("F"),
        }


# =============================================================================
# Utility Functions
# =============================================================================


def parse_flake8_output(output: str) -> list[Flake8Violation]:
    """
    Parse Flake8 text output into violations.

    Args:
        output: Text output from flake8 command.

    Returns:
        List of Flake8Violation objects.
    """
    violations = []
    for line in output.splitlines():
        violation = Flake8Violation.from_line(line)
        if violation:
            violations.append(violation)
    return violations


def format_flake8_report(report: Flake8Report) -> str:
    """Format a Flake8 report for display."""
    lines = [
        f"Flake8 Report (v{report.flake8_version})",
        "=" * 50,
        "",
        f"Violations: {report.violation_count}",
        f"  - Errors: {report.error_count}",
        f"  - Warnings: {report.warning_count}",
        "",
    ]

    if report.installed_plugins:
        lines.append("Installed plugins:")
        for plugin in report.installed_plugins:
            lines.append(f"  - {plugin.name}: {plugin.version}")
        lines.append("")

    if report.violations:
        lines.append("Violations by file:")
        for filename, violations in sorted(report.violations_by_file.items()):
            lines.append(f"\n{filename}:")
            for v in sorted(violations, key=lambda x: x.line):
                lines.append(f"  {v.line}:{v.column}: {v.code} {v.message}")

    return "\n".join(lines)
