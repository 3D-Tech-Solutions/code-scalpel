#!/usr/bin/env python3
"""
JSHint Parser - JavaScript error detection and code quality.

Parses JSHint output for detecting errors and potential problems in JavaScript code.
JSHint is a community-driven tool that detects errors and potential problems.


Features:
    Output Parsing:
        - JSHint JSON reporter output parsing
        - Error and warning extraction with codes
        - Severity classification (Info, Warning, Error)
        - Evidence/context line extraction

    Configuration:
        - .jshintrc file parsing
        - Enforcing options (bitwise, curly, eqeqeq, etc.)
        - Relaxing options (asi, boss, evil, etc.)
        - Environment configuration (browser, node, etc.)
        - Global variable declarations

    Execution:
        - Real-time JSHint execution via subprocess
        - File and code string analysis
        - Configurable JSHint path

    Analysis:
        - Filter by severity level
        - Filter/group by error code
        - Error and warning counts

Future Enhancements:
    - Error code documentation mapping
    - Fix suggestions for common errors
    - .jshintignore file parsing
    - Comparison with ESLint rules
"""

import json
import shutil
import subprocess
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class JSHintSeverity(Enum):
    """JSHint severity levels."""

    INFO = "I"
    WARNING = "W"
    ERROR = "E"


@dataclass
class JSHintError:
    """Represents a single JSHint error or warning."""

    code: str  # e.g., "W033", "E001"
    reason: str  # Error message
    evidence: str  # The offending line of code
    line: int
    character: int  # Column
    scope: str = "(main)"  # Function scope

    @property
    def severity(self) -> JSHintSeverity:
        """Determine severity from error code."""
        if self.code.startswith("E"):
            return JSHintSeverity.ERROR
        elif self.code.startswith("W"):
            return JSHintSeverity.WARNING
        return JSHintSeverity.INFO

    @property
    def is_error(self) -> bool:
        """Check if this is an error (not a warning)."""
        return self.severity == JSHintSeverity.ERROR


@dataclass
class JSHintFileResult:
    """JSHint results for a single file."""

    file_path: str
    errors: list[JSHintError] = field(default_factory=list)

    @property
    def error_count(self) -> int:
        """Count of actual errors."""
        return sum(1 for e in self.errors if e.is_error)

    @property
    def warning_count(self) -> int:
        """Count of warnings."""
        return sum(1 for e in self.errors if not e.is_error)

    @property
    def has_errors(self) -> bool:
        """Check if file has any actual errors."""
        return self.error_count > 0


@dataclass
class JSHintConfig:
    """JSHint configuration representation."""

    # Enforcing options
    bitwise: bool = False  # Prohibit bitwise operators
    curly: bool = False  # Require curly braces
    eqeqeq: bool = False  # Require === and !==
    esversion: int = 5  # ECMAScript version
    forin: bool = False  # Require filtering in for..in
    freeze: bool = False  # Prohibit native prototype extension
    futurehostile: bool = False  # Warn about future reserved words
    latedef: bool = False  # Prohibit variable use before definition
    leanswitch: bool = False  # Prohibit unnecessary switch case fall-through
    maxcomplexity: int | None = None  # Max cyclomatic complexity
    maxdepth: int | None = None  # Max block nesting
    maxerr: int = 50  # Max errors before stopping
    maxparams: int | None = None  # Max function parameters
    maxstatements: int | None = None  # Max statements per function
    noarg: bool = False  # Prohibit arguments.caller/callee
    nocomma: bool = False  # Prohibit comma operator
    nonbsp: bool = False  # Warn about non-breaking spaces
    nonew: bool = False  # Prohibit constructor side effects
    notypeof: bool = False  # Don't warn about invalid typeof
    shadow: bool = False  # Suppress variable shadowing warnings
    singleGroups: bool = False  # Prohibit unnecessary grouping operators
    strict: bool = False  # Require strict mode
    trailingcomma: bool = False  # Warn about trailing commas
    undef: bool = False  # Prohibit undefined variables
    unused: bool = False  # Warn about unused variables
    varstmt: bool = False  # Prohibit var statements

    # Relaxing options
    asi: bool = False  # Suppress missing semicolon warnings
    boss: bool = False  # Suppress assignment in conditions
    debug: bool = False  # Suppress debugger statement warnings
    elision: bool = False  # Allow ES3 array elisions
    evil: bool = False  # Suppress eval warnings
    expr: bool = False  # Suppress expression statement warnings
    funcscope: bool = False  # Suppress function scope warnings
    iterator: bool = False  # Suppress __iterator__ warnings
    lastsemic: bool = False  # Suppress missing semicolon in one-liners
    loopfunc: bool = False  # Suppress functions in loops warnings
    noyield: bool = False  # Suppress generator without yield warnings
    plusplus: bool = False  # Prohibit ++ and --
    proto: bool = False  # Suppress __proto__ warnings
    scripturl: bool = False  # Suppress javascript: URL warnings
    supernew: bool = False  # Suppress weird constructor warnings
    validthis: bool = False  # Suppress this in non-constructor warnings
    withstmt: bool = False  # Suppress with statement warnings

    # Environments
    browser: bool = False  # Browser globals
    browserify: bool = False  # Browserify globals
    couch: bool = False  # CouchDB globals
    devel: bool = False  # Development globals (console, alert)
    dojo: bool = False  # Dojo globals
    jasmine: bool = False  # Jasmine testing globals
    jquery: bool = False  # jQuery globals
    mocha: bool = False  # Mocha testing globals
    mootools: bool = False  # MooTools globals
    node: bool = False  # Node.js globals
    nonstandard: bool = False  # Nonstandard globals (escape, unescape)
    phantom: bool = False  # PhantomJS globals
    prototypejs: bool = False  # Prototype.js globals
    qunit: bool = False  # QUnit testing globals
    rhino: bool = False  # Rhino globals
    shelljs: bool = False  # ShellJS globals
    typed: bool = False  # Typed array globals
    worker: bool = False  # Web Worker globals
    wsh: bool = False  # Windows Script Host globals
    yui: bool = False  # YUI globals

    # Custom globals
    globals: dict[str, bool] = field(default_factory=dict)
    # Predefined globals to ignore
    predef: list[str] = field(default_factory=list)


class JSHintParser:
    """
    Parser for JSHint output and configuration files.

    Provides methods to:
    - Parse JSHint JSON reporter output
    - Parse .jshintrc configuration files
    - Execute JSHint on source code
    - Categorize errors by severity

    Example usage:
        parser = JSHintParser()

        # Parse existing JSHint output
        results = parser.parse_output(json_string)

        # Run JSHint on code
        result = parser.analyze_code(source_code)

        # Parse config
        config = parser.parse_config('.jshintrc')
    """

    def __init__(self, jshint_path: str | None = None):
        """
        Initialize JSHint parser.

        :param jshint_path: Path to JSHint executable.
        """
        self._jshint_path = jshint_path or self._find_jshint()

    def _find_jshint(self) -> str | None:
        """Find JSHint executable."""
        jshint = shutil.which("jshint")
        if jshint:
            return jshint

        local = Path("node_modules/.bin/jshint")
        if local.exists():
            return str(local)

        if shutil.which("npx"):
            return "npx jshint"

        return None

    def parse_output(self, json_output: str) -> list[JSHintFileResult]:
        """
        Parse JSHint JSON reporter output.

        :param json_output: JSHint output from --reporter=json.
        :return: List of JSHintFileResult for each file.
        """
        try:
            data = json.loads(json_output)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSHint JSON output: {e}")

        # JSHint JSON reporter outputs {result: [...], data: [...]}
        if isinstance(data, dict):
            errors_data = data.get("result", [])
        else:
            errors_data = data

        # Group by file
        files: dict[str, list[JSHintError]] = {}

        for error_data in errors_data:
            file_path = error_data.get("file", "unknown")
            error = error_data.get("error", error_data)

            jshint_error = JSHintError(
                code=error.get("code", "W000"),
                reason=error.get("reason", error.get("message", "")),
                evidence=error.get("evidence", ""),
                line=error.get("line", 0),
                character=error.get("character", error.get("col", 0)),
                scope=error.get("scope", "(main)"),
            )

            if file_path not in files:
                files[file_path] = []
            files[file_path].append(jshint_error)

        return [JSHintFileResult(file_path=fp, errors=errs) for fp, errs in files.items()]

    def parse_config(self, config_path: str) -> JSHintConfig:
        """
        Parse .jshintrc configuration file.

        :param config_path: Path to .jshintrc file.
        :return: JSHintConfig object.
        """
        path = Path(config_path)

        if not path.exists():
            raise FileNotFoundError(f"JSHint config not found: {config_path}")

        with open(path) as f:
            # JSHint config allows comments, need to strip them
            content = f.read()
            # Remove single-line comments
            lines = []
            for line in content.split("\n"):
                # Simple comment removal (doesn't handle all edge cases)
                if "//" in line:
                    line = line[: line.index("//")]
                lines.append(line)
            content = "\n".join(lines)

            try:
                config_data = json.loads(content)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid .jshintrc: {e}")

        config = JSHintConfig()

        # Map config data to dataclass fields
        for key, value in config_data.items():
            if hasattr(config, key):
                setattr(config, key, value)
            elif key == "globals":
                config.globals = value
            elif key == "predef":
                config.predef = value

        return config

    def analyze_file(self, file_path: str, config_path: str | None = None) -> JSHintFileResult:
        """
        Run JSHint on a file.

        :param file_path: Path to JavaScript file.
        :param config_path: Optional path to .jshintrc.
        :return: JSHintFileResult with errors.
        """
        if not self._jshint_path:
            raise RuntimeError("JSHint not found. Install with: npm install jshint")

        cmd = self._jshint_path.split() if " " in self._jshint_path else [self._jshint_path]
        cmd.extend(["--reporter=json", file_path])
        if config_path:
            cmd.extend(["--config", config_path])

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            output = result.stdout or result.stderr
            if not output.strip():
                return JSHintFileResult(file_path=file_path)
            results = self.parse_output(output)
            return results[0] if results else JSHintFileResult(file_path=file_path)
        except subprocess.TimeoutExpired:
            raise TimeoutError(f"JSHint timed out on {file_path}")
        except subprocess.SubprocessError as e:
            raise RuntimeError(f"JSHint failed: {e}")

    def analyze_code(self, code: str, filename: str = "input.js", config_path: str | None = None) -> JSHintFileResult:
        """
        Run JSHint on source code string.

        :param code: JavaScript source code.
        :param filename: Virtual filename.
        :param config_path: Optional path to .jshintrc.
        :return: JSHintFileResult with errors.
        """
        # JSHint doesn't support stdin well, write to temp file
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", suffix=".js", delete=False) as f:
            f.write(code)
            temp_path = f.name

        try:
            result = self.analyze_file(temp_path, config_path)
            result.file_path = filename  # Replace temp path
            return result
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def get_by_severity(self, result: JSHintFileResult, severity: JSHintSeverity) -> list[JSHintError]:
        """
        Get errors of a specific severity.

        :param result: JSHintFileResult to filter.
        :param severity: Desired severity level.
        :return: List of matching errors.
        """
        return [e for e in result.errors if e.severity == severity]

    def get_by_code(self, result: JSHintFileResult, code: str) -> list[JSHintError]:
        """
        Get errors with a specific error code.

        :param result: JSHintFileResult to filter.
        :param code: Error code (e.g., "W033").
        :return: List of matching errors.
        """
        return [e for e in result.errors if e.code == code]

    def group_by_code(self, result: JSHintFileResult) -> dict[str, list[JSHintError]]:
        """
        Group errors by their error code.

        :param result: JSHintFileResult to group.
        :return: Dictionary mapping codes to errors.
        """
        grouped: dict[str, list[JSHintError]] = {}
        for error in result.errors:
            if error.code not in grouped:
                grouped[error.code] = []
            grouped[error.code].append(error)
        return grouped
