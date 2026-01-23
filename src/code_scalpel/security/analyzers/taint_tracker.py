"""
Taint Tracking - The Bloodhound of Security Analysis.

This module provides taint propagation for detecting security vulnerabilities:
- SQL Injection
- XSS (Cross-Site Scripting)
- Path Traversal
- Command Injection

CRITICAL CONCEPT: Taint Sources and Sinks
==========================================

TAINT SOURCE: Where untrusted data enters the system
    - User input (request.args, request.form)
    - File reads
    - Network data
    - Database queries (sometimes)
    - Environment variables

TAINT SINK: Where data reaches dangerous operations
    - SQL queries (cursor.execute)
    - HTML output (render_template, innerHTML)
    - File paths (open(), os.path.join)
    - Shell commands (os.system, subprocess)

A VULNERABILITY exists when:
    TAINTED DATA flows from SOURCE → SINK without SANITIZATION

This module tracks taint through:
1. Variable assignments (x = tainted_input)
2. String operations (query = "SELECT " + tainted_input)
3. Function returns (may or may not propagate taint)
"""

from __future__ import annotations

import ast  # [20251216_FEATURE] v2.2.0 - Required for SSR vulnerability detection
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, TypedDict

from z3 import ExprRef, String


class VulnerabilityDict(TypedDict):
    """Vulnerability information for JSON serialization."""

    type: str  # vulnerability_type
    cwe: str  # CWE-ID
    sink: str  # SecuritySink name
    source: str  # TaintSource name
    taint_path: list[str]
    taint_flow: list[str]  # Alias for clarity
    sink_location: tuple[int, int] | None
    source_location: tuple[int, int] | None
    sanitizers: list[str]
    description: str
    severity: str  # critical, high, medium, low
    recommendation: str
    cwe_link: str


class TaintSource(Enum):
    """
    Categories of taint sources.

    Each source has different security implications:
    - USER_INPUT: Most dangerous, directly controlled by attacker
    - FILE_CONTENT: Dangerous if file path is also tainted
    - NETWORK_DATA: Remote attacker controlled
    - DATABASE: May be pre-tainted from prior injection
    - ENVIRONMENT: Less common attack vector
    """

    USER_INPUT = auto()  # request.args, request.form, sys.argv
    FILE_CONTENT = auto()  # open().read()
    NETWORK_DATA = auto()  # socket.recv(), requests.get()
    DATABASE = auto()  # cursor.fetchone()
    ENVIRONMENT = auto()  # os.environ
    HARDCODED = auto()  # Hardcoded secrets
    UNKNOWN = auto()  # Source couldn't be determined


class SecuritySink(Enum):
    """
    Categories of security sinks where tainted data is dangerous.

    Each sink type corresponds to a different vulnerability class:
    - SQL_QUERY: SQL Injection (CWE-89)
    - HTML_OUTPUT: XSS (CWE-79)
    - FILE_PATH: Path Traversal (CWE-22)
    - SHELL_COMMAND: Command Injection (CWE-78)
    - EVAL: Code Injection (CWE-94)
    - DESERIALIZATION: Insecure Deserialization (CWE-502)
    - WEAK_CRYPTO: Use of Weak Cryptographic Algorithm (CWE-327)
    - SSRF: Server-Side Request Forgery (CWE-918)
    - XXE: XML External Entity Injection (CWE-611) [v1.4.0]
    - SSTI: Server-Side Template Injection (CWE-1336) [v1.4.0]
    - DOM_XSS: DOM-based Cross-Site Scripting (CWE-79) [v2.0.0]
    - PROTOTYPE_POLLUTION: Prototype Pollution (CWE-1321) [v2.0.0]
    - REDIRECT: Open Redirect (CWE-601) [v2.0.0 P1]
    """

    SQL_QUERY = auto()  # cursor.execute(), Session.execute()
    HTML_OUTPUT = auto()  # render_template(), innerHTML
    FILE_PATH = auto()  # open(), os.path.join()
    SHELL_COMMAND = auto()  # os.system(), subprocess.run()
    EVAL = auto()  # eval(), exec()
    DESERIALIZATION = auto()  # pickle.loads(), yaml.load()
    LOG_OUTPUT = auto()  # logging.info() - can leak sensitive data
    HEADER = auto()  # HTTP header injection
    WEAK_CRYPTO = auto()  # hashlib.md5(), hashlib.sha1(), DES
    SSRF = auto()  # requests.get(), urllib.request.urlopen()
    HARDCODED_SECRET = auto()  # Hardcoded secrets (AWS keys, etc.)
    # [20251212_FEATURE] v1.4.0 - New vulnerability types
    XXE = auto()  # xml.etree.ElementTree.parse(), lxml.etree.parse()
    SSTI = auto()  # jinja2.Template(), mako.template.Template()
    # [20251215_FEATURE] v2.0.0 - JavaScript/TypeScript vulnerability types
    DOM_XSS = auto()  # innerHTML, document.write, outerHTML
    PROTOTYPE_POLLUTION = auto()  # Object.assign, _.merge with user input
    # [20251215_FEATURE] v2.0.0 P1 - Additional vulnerability types
    REDIRECT = auto()  # Open Redirect (redirect to user-controlled URL)
    # [20251229_FEATURE] v3.0.4 - Type System Evaporation detection
    UNVALIDATED_OUTPUT = auto()  # Tainted data returned in HTTP response without validation (CWE-20)
    # [20251219_FEATURE] v3.0.4 - Additional 12 vulnerability types for comprehensive coverage
    LDAP_INJECTION = auto()  # LDAP filter injection (CWE-90)
    XPATH_INJECTION = auto()  # XPath query injection (CWE-643)
    NOSQL_INJECTION = auto()  # MongoDB/NoSQL injection (CWE-943)
    EMAIL_INJECTION = auto()  # Email/SMTP header injection (CWE-93)
    REGEX_DOS = auto()  # ReDoS via user-controlled regex (CWE-1333)
    FORMAT_STRING = auto()  # Format string vulnerability (CWE-134)
    UNSAFE_REFLECTION = auto()  # Reflection injection (CWE-470)
    EL_INJECTION = auto()  # Expression Language injection - SpEL, OGNL, MVEL (CWE-917)
    GRAPHQL_INJECTION = auto()  # GraphQL injection/batching attacks (CWE-89)
    CORS_MISCONFIGURATION = auto()  # Dynamic CORS origin from user input (CWE-942)
    JWT_WEAKNESS = auto()  # JWT algorithm confusion, weak secrets (CWE-347)
    HTML_INJECTION = auto()  # HTML injection without script (CWE-80)


class TaintLevel(Enum):
    """
    Confidence level of taint.

    HIGH: Definitely tainted (direct assignment from source)
    MEDIUM: Probably tainted (flows through operations)
    LOW: Possibly tainted (partial sanitization applied)
    NONE: Not tainted (concrete value or sanitized)
    """

    HIGH = auto()
    MEDIUM = auto()
    LOW = auto()
    NONE = auto()


@dataclass
class TaintInfo:
    """
    Taint metadata attached to a symbolic value.

    Attributes:
        source: Where the taint originated
        level: Confidence level of taintedness
        source_location: (line, column) in source code
        propagation_path: List of variable names taint flowed through
        sanitizers_applied: Set of sanitization functions applied
        sanitizer_history: List of sanitizers applied in order
        cleared_sinks: Sinks that are safe due to sanitization
    """

    source: TaintSource
    level: TaintLevel = TaintLevel.HIGH
    source_location: tuple[int, int] | None = None
    propagation_path: list[str] = field(default_factory=list)
    sanitizers_applied: set[str] = field(default_factory=set)
    sanitizer_history: list[str] = field(default_factory=list)
    cleared_sinks: set[SecuritySink] = field(default_factory=set)

    def propagate(self, through_var: str) -> TaintInfo:
        """
        Create new TaintInfo when taint propagates through a variable.

        Args:
            through_var: Name of variable taint is flowing through

        Returns:
            New TaintInfo with updated propagation path
        """
        return TaintInfo(
            source=self.source,
            level=self.level,
            source_location=self.source_location,
            propagation_path=self.propagation_path + [through_var],
            sanitizers_applied=self.sanitizers_applied.copy(),
            sanitizer_history=self.sanitizer_history.copy(),
            cleared_sinks=self.cleared_sinks.copy(),
        )

    def apply_sanitizer(self, sanitizer: str) -> TaintInfo:
        """
        Record that a sanitizer was applied and clear relevant sinks.

        Args:
            sanitizer: Name of sanitization function

        Returns:
            New TaintInfo with sanitizer recorded, level lowered, and sinks cleared
        """
        new_sanitizers = self.sanitizers_applied | {sanitizer}
        new_history = self.sanitizer_history + [sanitizer]

        # Get which sinks this sanitizer clears
        sanitizer_info = SANITIZER_REGISTRY.get(sanitizer)
        new_cleared = self.cleared_sinks.copy()

        if sanitizer_info is not None:
            if sanitizer_info.full_clear:
                # Type coercion (int, float, bool) clears ALL sinks
                new_cleared = set(SecuritySink)
            else:
                # Partial clear - only specific sinks
                new_cleared |= sanitizer_info.clears_sinks

        # Lower taint level based on sanitizer
        new_level = TaintLevel.LOW if len(new_sanitizers) > 0 else self.level

        # If all dangerous sinks are cleared, mark as NONE
        if new_cleared >= {
            SecuritySink.SQL_QUERY,
            SecuritySink.HTML_OUTPUT,
            SecuritySink.FILE_PATH,
            SecuritySink.SHELL_COMMAND,
        }:
            new_level = TaintLevel.NONE

        return TaintInfo(
            source=self.source,
            level=new_level,
            source_location=self.source_location,
            propagation_path=self.propagation_path.copy(),
            sanitizers_applied=new_sanitizers,
            sanitizer_history=new_history,
            cleared_sinks=new_cleared,
        )

    def is_dangerous_for(self, sink: SecuritySink) -> bool:
        """
        Check if this taint is dangerous for a specific sink.

        Some sanitizers are sink-specific:
        - html.escape() → safe for HTML_OUTPUT, NOT for SQL_QUERY
        - int() → safe for ALL sinks (type coercion)

        Args:
            sink: The security sink to check

        Returns:
            True if tainted data reaching this sink is dangerous
        """
        if self.level == TaintLevel.NONE:
            return False

        # Check if this specific sink was cleared by a sanitizer
        if sink in self.cleared_sinks:
            return False

        # Backward compatibility: check SINK_SANITIZERS
        safe_sanitizers = SINK_SANITIZERS.get(sink, set())
        if self.sanitizers_applied & safe_sanitizers:
            return False

        return True


# Mapping of sinks to sanitizers that make them safe
SINK_SANITIZERS: dict[SecuritySink, set[str]] = {
    SecuritySink.SQL_QUERY: {
        "parameterized_query",
        "sqlalchemy_text_bindparams",
        "escape_string",
    },
    SecuritySink.HTML_OUTPUT: {
        "html.escape",
        "markupsafe.escape",
        "bleach.clean",
        "cgi.escape",
    },
    SecuritySink.FILE_PATH: {
        "os.path.basename",
        "pathlib.Path.name",
        "secure_filename",
    },
    SecuritySink.SHELL_COMMAND: {
        "shlex.quote",
        "pipes.quote",
    },
    SecuritySink.EVAL: set(),  # Almost never safe
    SecuritySink.DESERIALIZATION: set(),  # Almost never safe
}


# =============================================================================
# Sanitizer Registry (RFC-002: The Silencer)
# =============================================================================


@dataclass
class SanitizerInfo:
    """
    Information about a sanitizer function.

    Attributes:
        name: Full function name (e.g., "html.escape")
        clears_sinks: Which sink types this sanitizer protects against
        confidence: Confidence score of the sanitizer (0.0-1.0)
    """

    name: str
    clears_sinks: set[SecuritySink] = field(default_factory=set)
    full_clear: bool = False
    confidence: float = 1.0


# Built-in sanitizer registry
# Users can extend via pyproject.toml [tool.code-scalpel.sanitizers]
SANITIZER_REGISTRY: dict[str, SanitizerInfo] = {
    # XSS sanitizers
    "html.escape": SanitizerInfo("html.escape", {SecuritySink.HTML_OUTPUT}),
    "markupsafe.escape": SanitizerInfo("markupsafe.escape", {SecuritySink.HTML_OUTPUT}),
    "markupsafe.Markup": SanitizerInfo("markupsafe.Markup", {SecuritySink.HTML_OUTPUT}),
    "bleach.clean": SanitizerInfo("bleach.clean", {SecuritySink.HTML_OUTPUT}),
    "cgi.escape": SanitizerInfo("cgi.escape", {SecuritySink.HTML_OUTPUT}),
    # SQL sanitizers
    "escape_string": SanitizerInfo("escape_string", {SecuritySink.SQL_QUERY}),
    "mysql.connector.escape_string": SanitizerInfo("mysql.connector.escape_string", {SecuritySink.SQL_QUERY}),
    # Path sanitizers
    "os.path.basename": SanitizerInfo("os.path.basename", {SecuritySink.FILE_PATH}),
    "werkzeug.utils.secure_filename": SanitizerInfo("werkzeug.utils.secure_filename", {SecuritySink.FILE_PATH}),
    "secure_filename": SanitizerInfo("secure_filename", {SecuritySink.FILE_PATH}),
    # Shell sanitizers
    "shlex.quote": SanitizerInfo("shlex.quote", {SecuritySink.SHELL_COMMAND}),
    "pipes.quote": SanitizerInfo("pipes.quote", {SecuritySink.SHELL_COMMAND}),
    # Type coercion - FULL CLEAR (converts to safe type)
    "int": SanitizerInfo("int", set(), full_clear=True),
    "float": SanitizerInfo("float", set(), full_clear=True),
    "bool": SanitizerInfo("bool", set(), full_clear=True),
    "str": SanitizerInfo("str", set(), full_clear=False),  # str() doesn't sanitize!
    "abs": SanitizerInfo("abs", set(), full_clear=True),
    "len": SanitizerInfo("len", set(), full_clear=True),
    "ord": SanitizerInfo("ord", set(), full_clear=True),
    "hex": SanitizerInfo("hex", set(), full_clear=True),
    # [20251212_FEATURE] v1.4.0 - XXE Sanitizers (defusedxml is safe)
    "defusedxml.parse": SanitizerInfo("defusedxml.parse", {SecuritySink.XXE}),
    "defusedxml.fromstring": SanitizerInfo("defusedxml.fromstring", {SecuritySink.XXE}),
    "defusedxml.ElementTree.parse": SanitizerInfo("defusedxml.ElementTree.parse", {SecuritySink.XXE}),
    "defusedxml.ElementTree.fromstring": SanitizerInfo("defusedxml.ElementTree.fromstring", {SecuritySink.XXE}),
    "defusedxml.minidom.parse": SanitizerInfo("defusedxml.minidom.parse", {SecuritySink.XXE}),
    "defusedxml.minidom.parseString": SanitizerInfo("defusedxml.minidom.parseString", {SecuritySink.XXE}),
    "defusedxml.sax.parse": SanitizerInfo("defusedxml.sax.parse", {SecuritySink.XXE}),
    # [20251212_FEATURE] v1.4.0 - SSTI Sanitizers (file-based templates are safe)
    "render_template": SanitizerInfo("render_template", {SecuritySink.SSTI}),  # Flask file-based
    "flask.render_template": SanitizerInfo("flask.render_template", {SecuritySink.SSTI}),
    "django.shortcuts.render": SanitizerInfo("django.shortcuts.render", {SecuritySink.SSTI}),
    # ==========================================================================
    # [20251215_FEATURE] v2.0.0 - JavaScript/TypeScript Sanitizers
    # ==========================================================================
    # DOM XSS Sanitizers
    "DOMPurify.sanitize": SanitizerInfo("DOMPurify.sanitize", {SecuritySink.DOM_XSS, SecuritySink.HTML_OUTPUT}),
    "sanitize-html": SanitizerInfo("sanitize-html", {SecuritySink.DOM_XSS, SecuritySink.HTML_OUTPUT}),
    "xss": SanitizerInfo("xss", {SecuritySink.DOM_XSS, SecuritySink.HTML_OUTPUT}),
    "xss-filters": SanitizerInfo("xss-filters", {SecuritySink.DOM_XSS, SecuritySink.HTML_OUTPUT}),
    "he.encode": SanitizerInfo("he.encode", {SecuritySink.DOM_XSS, SecuritySink.HTML_OUTPUT}),
    "he.escape": SanitizerInfo("he.escape", {SecuritySink.DOM_XSS, SecuritySink.HTML_OUTPUT}),
    "escape-html": SanitizerInfo("escape-html", {SecuritySink.DOM_XSS, SecuritySink.HTML_OUTPUT}),
    "validator.escape": SanitizerInfo("validator.escape", {SecuritySink.DOM_XSS, SecuritySink.HTML_OUTPUT}),
    "textContent": SanitizerInfo("textContent", {SecuritySink.DOM_XSS}),  # Safe DOM API
    "innerText": SanitizerInfo("innerText", {SecuritySink.DOM_XSS}),  # Safe DOM API
    "createTextNode": SanitizerInfo("createTextNode", {SecuritySink.DOM_XSS}),  # Safe DOM API
    # SQL Sanitizers (Node.js)
    "mysql.escape": SanitizerInfo("mysql.escape", {SecuritySink.SQL_QUERY}),
    "mysql2.escape": SanitizerInfo("mysql2.escape", {SecuritySink.SQL_QUERY}),
    "pg.escapeLiteral": SanitizerInfo("pg.escapeLiteral", {SecuritySink.SQL_QUERY}),
    "pg.escapeIdentifier": SanitizerInfo("pg.escapeIdentifier", {SecuritySink.SQL_QUERY}),
    "sqlstring.escape": SanitizerInfo("sqlstring.escape", {SecuritySink.SQL_QUERY}),
    # Path Sanitizers (Node.js)
    "path.basename": SanitizerInfo("path.basename", {SecuritySink.FILE_PATH}),
    "path.normalize": SanitizerInfo("path.normalize", {SecuritySink.FILE_PATH}),
    "sanitize-filename": SanitizerInfo("sanitize-filename", {SecuritySink.FILE_PATH}),
    # Shell Sanitizers (Node.js)
    "shell-escape": SanitizerInfo("shell-escape", {SecuritySink.SHELL_COMMAND}),
    "shell-quote.quote": SanitizerInfo("shell-quote.quote", {SecuritySink.SHELL_COMMAND}),
    # URL Sanitizers
    "encodeURIComponent": SanitizerInfo("encodeURIComponent", {SecuritySink.SSRF}),
    "encodeURI": SanitizerInfo("encodeURI", {SecuritySink.SSRF}),
    # Type coercion in JavaScript
    "Number": SanitizerInfo("Number", set(), full_clear=True),
    "parseInt": SanitizerInfo("parseInt", set(), full_clear=True),
    "parseFloat": SanitizerInfo("parseFloat", set(), full_clear=True),
    "Boolean": SanitizerInfo("Boolean", set(), full_clear=True),
    # JSON parse with validation
    "JSON.parse": SanitizerInfo("JSON.parse", set()),  # Not a sanitizer by itself
    "ajv.validate": SanitizerInfo("ajv.validate", {SecuritySink.DESERIALIZATION}),  # Schema validation
    "joi.validate": SanitizerInfo("joi.validate", {SecuritySink.DESERIALIZATION}),
    "yup.validate": SanitizerInfo("yup.validate", {SecuritySink.DESERIALIZATION}),
    "zod.parse": SanitizerInfo("zod.parse", {SecuritySink.DESERIALIZATION}),
    # ==========================================================================
    # [20251215_FEATURE] v2.0.0 - Java Sanitizers
    # ==========================================================================
    # XSS Sanitizers
    "StringEscapeUtils.escapeHtml4": SanitizerInfo("StringEscapeUtils.escapeHtml4", {SecuritySink.HTML_OUTPUT}),
    "HtmlUtils.htmlEscape": SanitizerInfo("HtmlUtils.htmlEscape", {SecuritySink.HTML_OUTPUT}),  # Spring
    "OWASP.encoder": SanitizerInfo("OWASP.encoder", {SecuritySink.HTML_OUTPUT, SecuritySink.DOM_XSS}),
    "Encode.forHtml": SanitizerInfo("Encode.forHtml", {SecuritySink.HTML_OUTPUT}),  # OWASP Java Encoder
    "Encode.forJavaScript": SanitizerInfo("Encode.forJavaScript", {SecuritySink.DOM_XSS}),
    "Encode.forCssString": SanitizerInfo("Encode.forCssString", {SecuritySink.DOM_XSS}),
    # SQL Sanitizers (parameterized queries)
    "PreparedStatement.setString": SanitizerInfo("PreparedStatement.setString", {SecuritySink.SQL_QUERY}),
    "PreparedStatement.setInt": SanitizerInfo("PreparedStatement.setInt", {SecuritySink.SQL_QUERY}),
    "PreparedStatement.setObject": SanitizerInfo("PreparedStatement.setObject", {SecuritySink.SQL_QUERY}),
    # Path Sanitizers
    "FilenameUtils.getName": SanitizerInfo("FilenameUtils.getName", {SecuritySink.FILE_PATH}),
    "Paths.get": SanitizerInfo("Paths.get", set()),  # Not a sanitizer, but commonly used
    # XXE Safe Parsers
    "DocumentBuilderFactory.setFeature": SanitizerInfo("DocumentBuilderFactory.setFeature", {SecuritySink.XXE}),
    "SAXParserFactory.setFeature": SanitizerInfo("SAXParserFactory.setFeature", {SecuritySink.XXE}),
    # Input validation
    "StringUtils.isNumeric": SanitizerInfo("StringUtils.isNumeric", set(), full_clear=True),
    "StringUtils.isAlphanumeric": SanitizerInfo(
        "StringUtils.isAlphanumeric",
        {SecuritySink.SQL_QUERY, SecuritySink.SHELL_COMMAND},
    ),
    "Integer.parseInt": SanitizerInfo("Integer.parseInt", set(), full_clear=True),
    "Long.parseLong": SanitizerInfo("Long.parseLong", set(), full_clear=True),
    "UUID.fromString": SanitizerInfo("UUID.fromString", set(), full_clear=True),
}


def register_sanitizer(
    name: str,
    clears_sinks: set[SecuritySink] | None = None,
    full_clear: bool = False,
) -> None:
    """
    Register a custom sanitizer function.

    Args:
        name: Full function name (e.g., "my_lib.clean_sql")
        clears_sinks: Which sink types this sanitizer protects against
        full_clear: If True, clears ALL taint

    Example:
        register_sanitizer("my_lib.clean_sql", {SecuritySink.SQL_QUERY})
    """
    SANITIZER_REGISTRY[name] = SanitizerInfo(
        name=name,
        clears_sinks=clears_sinks or set(),
        full_clear=full_clear,
    )


def load_sanitizers_from_config(config_path: str | None = None) -> int:
    """
    Load custom sanitizers from pyproject.toml.

    Expected format:
        [tool.code-scalpel.sanitizers]
        "my_lib.clean_sql" = ["SQL_QUERY"]
        "utils.strip_tags" = ["HTML_OUTPUT"]
        "utils.super_clean" = ["ALL"]  # Full clear

    Args:
        config_path: Path to config file. If None, searches for pyproject.toml
                     in current directory and parent directories.

    Returns:
        Number of sanitizers loaded

    Example pyproject.toml:
        [tool.code-scalpel.sanitizers]
        "my_utils.clean_sql" = ["SQL_QUERY"]
        "my_utils.safe_print" = ["HTML_OUTPUT"]
        "my_utils.super_clean" = ["ALL"]
    """
    import os

    # Find config file
    if config_path is None:
        config_path = _find_config_file()

    if config_path is None or not os.path.exists(config_path):
        return 0

    try:
        config = _load_toml(config_path)
        if config is None:
            return 0

        sanitizers = config.get("tool", {}).get("code-scalpel", {}).get("sanitizers", {})

        count = 0
        for func_name, sinks in sanitizers.items():
            if not isinstance(sinks, list):
                continue  # Invalid format, skip

            # Check for full clear
            if "ALL" in sinks or "*" in sinks:
                register_sanitizer(func_name, full_clear=True)
            else:
                sink_set = set()
                for sink_name in sinks:
                    try:
                        sink_set.add(SecuritySink[sink_name])
                    except KeyError:
                        pass  # Unknown sink name, skip
                if sink_set:  # Only register if we matched at least one sink  # pragma: no branch
                    register_sanitizer(func_name, sink_set)
            count += 1

        return count

    except Exception:
        # Don't crash on config errors, just skip loading
        return 0


def _find_config_file() -> str | None:
    """Search for pyproject.toml in current and parent directories."""
    import os

    try:
        current = os.getcwd()
    except (FileNotFoundError, OSError):
        # Current working directory may have been removed by tests that
        # change into a temporary directory then delete it. Fall back to
        # the directory containing this module so the search can continue
        # without raising an exception.
        current = os.path.dirname(os.path.abspath(__file__))

    # Search up to 10 levels
    for _ in range(10):  # pragma: no branch
        candidate = os.path.join(current, "pyproject.toml")
        if os.path.exists(candidate):
            return candidate

        parent = os.path.dirname(current)
        if parent == current:
            break
        current = parent

    return None


def _load_toml(path: str) -> dict[str, Any] | None:
    """Load a TOML file using available parser."""
    # Python 3.11+ has tomllib built-in
    try:
        import tomllib  # pragma: no cover

        with open(path, "rb") as f:  # pragma: no cover
            return tomllib.load(f)  # pragma: no cover
    except ImportError:
        pass

    # Fallback to tomli (pip install tomli)
    try:
        import tomli

        with open(path, "rb") as f:
            return tomli.load(f)
    except ImportError:
        pass

    # No TOML parser available
    return None


@dataclass
class TaintedValue:
    """
    A symbolic value with taint information attached.

    This wraps a Z3 expression with taint metadata for tracking
    data flow through the program.

    Attributes:
        expr: The Z3 symbolic expression
        taint: Taint metadata (None if not tainted)
    """

    expr: ExprRef
    taint: TaintInfo | None = None

    @property
    def is_tainted(self) -> bool:
        """Check if this value is tainted."""
        return self.taint is not None and self.taint.level != TaintLevel.NONE

    def __repr__(self) -> str:
        if self.is_tainted:
            return (
                f"TaintedValue({self.expr}, taint={self.taint.source.name})"
                if self.taint
                else "TaintedValue(undefined)"
            )
        return f"TaintedValue({self.expr}, clean)"


class TaintTracker:
    """
    Tracks taint propagation through symbolic execution.

    This class maintains a shadow state alongside the symbolic state,
    tracking which variables are tainted and how taint flows through
    operations.

    Example:
        tracker = TaintTracker()

        # Mark user input as tainted
        user_input = tracker.taint_source("user_input", TaintSource.USER_INPUT)

        # Track operations
        query = tracker.concat(StringVal("SELECT * FROM users WHERE id="), user_input)

        # Check for vulnerabilities
        if tracker.reaches_sink(query, SecuritySink.SQL_QUERY):
            print("SQL Injection vulnerability!")
    """

    def __init__(self):
        """Initialize the taint tracker."""
        self._taint_map: dict[str, TaintInfo] = {}
        self._vulnerabilities: list[Vulnerability] = []

    # =========================================================================
    # Taint Sources
    # =========================================================================

    def taint_source(self, name: str, source: TaintSource, location: tuple[int, int] | None = None) -> TaintedValue:
        """
        Create a tainted symbolic string from a source.

        Args:
            name: Variable name
            source: Type of taint source
            location: Source code location (line, col)

        Returns:
            TaintedValue with symbolic string and taint info
        """
        expr = String(name)
        taint = TaintInfo(
            source=source,
            level=TaintLevel.HIGH,
            source_location=location,
            propagation_path=[name],
        )

        self._taint_map[name] = taint

        return TaintedValue(expr=expr, taint=taint)

    def mark_tainted(self, name: str, taint_info: TaintInfo) -> None:
        """
        Mark an existing variable as tainted.

        Args:
            name: Variable name
            taint_info: Taint metadata
        """
        self._taint_map[name] = taint_info

    def get_taint(self, name: str) -> TaintInfo | None:
        """
        Get taint info for a variable.

        Args:
            name: Variable name

        Returns:
            TaintInfo if tainted, None otherwise
        """
        return self._taint_map.get(name)

    def is_tainted(self, name: str) -> bool:
        """
        Check if a variable is tainted.

        Args:
            name: Variable name

        Returns:
            True if variable is tainted
        """
        taint = self._taint_map.get(name)
        return taint is not None and taint.level != TaintLevel.NONE

    # =========================================================================
    # Taint Propagation
    # =========================================================================

    def propagate_assignment(self, target: str, source_names: list[str]) -> TaintInfo | None:
        """
        Propagate taint through an assignment.

        If any source is tainted, the target becomes tainted.

        Args:
            target: Target variable name
            source_names: Names of variables used in RHS

        Returns:
            TaintInfo if target is now tainted
        """
        # [20260119_BUGFIX] Preserve sanitizer history and cleared sinks when merging taint.
        merged_taint = None

        for source_name in source_names:
            source_taint = self._taint_map.get(source_name)
            if source_taint is None:
                continue

            candidate = source_taint.propagate(target)

            if merged_taint is None:
                merged_taint = candidate
                continue

            # Pick the most tainted level (HIGH < MEDIUM < LOW < NONE when using Enum auto values)
            most_tainted = candidate if candidate.level.value < merged_taint.level.value else merged_taint

            combined_sanitizers = merged_taint.sanitizers_applied & candidate.sanitizers_applied
            combined_cleared = merged_taint.cleared_sinks & candidate.cleared_sinks

            combined_history: list[str] = []
            for name in merged_taint.sanitizer_history + candidate.sanitizer_history:
                if name not in combined_history:
                    combined_history.append(name)

            combined_path: list[str] = []
            for name in merged_taint.propagation_path + candidate.propagation_path:
                if name not in combined_path:
                    combined_path.append(name)

            new_level = most_tainted.level
            if combined_cleared >= {
                SecuritySink.SQL_QUERY,
                SecuritySink.HTML_OUTPUT,
                SecuritySink.FILE_PATH,
                SecuritySink.SHELL_COMMAND,
            }:
                new_level = TaintLevel.NONE

            merged_taint = TaintInfo(
                source=most_tainted.source,
                level=new_level,
                source_location=most_tainted.source_location,
                propagation_path=combined_path,
                sanitizers_applied=combined_sanitizers,
                sanitizer_history=combined_history,
                cleared_sinks=combined_cleared,
            )

        if merged_taint is not None:
            self._taint_map[target] = merged_taint
        else:
            # Target is clean - remove any existing taint
            self._taint_map.pop(target, None)

        return merged_taint

    def propagate_concat(self, result_name: str, operand_names: list[str]) -> TaintInfo | None:
        """
        Propagate taint through string concatenation.

        If ANY operand is tainted, the result is tainted.
        This is the key propagation rule for injection vulnerabilities.

        Args:
            result_name: Name of result variable
            operand_names: Names of concatenated strings

        Returns:
            TaintInfo if result is tainted
        """
        return self.propagate_assignment(result_name, operand_names)

    def apply_sanitizer(self, var_name: str, sanitizer: str) -> TaintInfo | None:
        """
        Record that a sanitizer was applied to a variable.

        Args:
            var_name: Variable name
            sanitizer: Name of sanitization function

        Returns:
            Updated TaintInfo
        """
        current_taint = self._taint_map.get(var_name)
        if current_taint is None:
            return None

        new_taint = current_taint.apply_sanitizer(sanitizer)
        self._taint_map[var_name] = new_taint
        return new_taint

    # =========================================================================
    # Sink Detection
    # =========================================================================

    def check_sink(
        self,
        var_name: str,
        sink: SecuritySink,
        location: tuple[int, int] | None = None,
    ) -> Vulnerability | None:
        """
        Check if tainted data reaches a security sink.

        Args:
            var_name: Name of variable being used at sink
            sink: Type of security sink
            location: Source code location

        Returns:
            Vulnerability if detected, None if safe
        """
        taint = self._taint_map.get(var_name)

        if taint is None:
            return None

        if not taint.is_dangerous_for(sink):
            return None

        # Found a vulnerability!
        vuln = Vulnerability(
            sink_type=sink,
            taint_source=taint.source,
            taint_path=taint.propagation_path,
            sink_location=location,
            source_location=taint.source_location,
            sanitizers_applied=taint.sanitizers_applied,
        )

        self._vulnerabilities.append(vuln)
        return vuln

    def get_vulnerabilities(self) -> list[Vulnerability]:
        """Get all detected vulnerabilities."""
        return self._vulnerabilities.copy()

    # =========================================================================
    # State Management
    # =========================================================================

    def fork(self) -> TaintTracker:
        """
        Create an isolated copy for branching.

        Returns:
            New TaintTracker with copied state
        """
        forked = TaintTracker()
        forked._taint_map = {k: v for k, v in self._taint_map.items()}
        forked._vulnerabilities = self._vulnerabilities.copy()
        return forked

    def clear(self) -> None:
        """Reset all taint tracking state."""
        self._taint_map.clear()
        self._vulnerabilities.clear()


@dataclass
class Vulnerability:
    """
    A detected security vulnerability.

    Attributes:
        sink_type: Type of dangerous operation
        taint_source: Where the tainted data originated
        taint_path: Variables the taint flowed through
        sink_location: Where the vulnerability is (line, col)
        source_location: Where tainted data entered (line, col)
        sanitizers_applied: Sanitizers that were applied (but insufficient)
    """

    sink_type: SecuritySink
    taint_source: TaintSource
    taint_path: list[str]
    sink_location: tuple[int, int] | None = None
    source_location: tuple[int, int] | None = None
    sanitizers_applied: set[str] = field(default_factory=set)

    @property
    def vulnerability_type(self) -> str:
        """Get the common name for this vulnerability type."""
        mapping = {
            SecuritySink.SQL_QUERY: "SQL Injection",
            SecuritySink.HTML_OUTPUT: "Cross-Site Scripting (XSS)",
            SecuritySink.FILE_PATH: "Path Traversal",
            SecuritySink.SHELL_COMMAND: "Command Injection",
            SecuritySink.EVAL: "Code Injection",
            SecuritySink.DESERIALIZATION: "Insecure Deserialization",
            SecuritySink.LOG_OUTPUT: "Log Injection",
            SecuritySink.HEADER: "HTTP Header Injection",
            SecuritySink.WEAK_CRYPTO: "Use of Weak Cryptographic Hash",
            SecuritySink.SSRF: "Server-Side Request Forgery (SSRF)",
            SecuritySink.HARDCODED_SECRET: "Hardcoded Secret",
            # [20251212_FEATURE] v1.4.0 vulnerability types
            SecuritySink.XXE: "XML External Entity Injection (XXE)",
            SecuritySink.SSTI: "Server-Side Template Injection (SSTI)",
            # [20251215_FEATURE] v2.0.0 JavaScript vulnerability types
            SecuritySink.DOM_XSS: "DOM-based Cross-Site Scripting (DOM XSS)",
            SecuritySink.PROTOTYPE_POLLUTION: "Prototype Pollution",
            # [20251215_FEATURE] v2.0.0 P1 - Additional vulnerability types
            SecuritySink.REDIRECT: "Open Redirect",
            # [20251229_FEATURE] v3.0.4 - Type System Evaporation
            SecuritySink.UNVALIDATED_OUTPUT: "Unvalidated Input in HTTP Response",
            # [20260119_BUGFIX] Add names for extended sink coverage
            SecuritySink.LDAP_INJECTION: "LDAP Injection",
            SecuritySink.XPATH_INJECTION: "XPath Injection",
            SecuritySink.NOSQL_INJECTION: "NoSQL Injection",
            SecuritySink.EMAIL_INJECTION: "Email Header Injection",
            SecuritySink.REGEX_DOS: "Regular Expression Denial of Service",
            SecuritySink.FORMAT_STRING: "Format String Vulnerability",
            SecuritySink.UNSAFE_REFLECTION: "Unsafe Reflection",
            SecuritySink.EL_INJECTION: "Expression Language Injection",
            SecuritySink.GRAPHQL_INJECTION: "GraphQL Injection",
            SecuritySink.CORS_MISCONFIGURATION: "CORS Misconfiguration",
            SecuritySink.JWT_WEAKNESS: "JWT Weakness",
            SecuritySink.HTML_INJECTION: "HTML Injection",
        }
        return mapping.get(self.sink_type, "Unknown Vulnerability")

    @property
    def cwe_id(self) -> str:
        """Get the CWE identifier for this vulnerability."""
        mapping = {
            SecuritySink.SQL_QUERY: "CWE-89",
            SecuritySink.HTML_OUTPUT: "CWE-79",
            SecuritySink.FILE_PATH: "CWE-22",
            SecuritySink.SHELL_COMMAND: "CWE-78",
            SecuritySink.EVAL: "CWE-94",
            SecuritySink.DESERIALIZATION: "CWE-502",
            SecuritySink.LOG_OUTPUT: "CWE-117",
            SecuritySink.HEADER: "CWE-113",
            SecuritySink.WEAK_CRYPTO: "CWE-327",
            SecuritySink.SSRF: "CWE-918",
            SecuritySink.HARDCODED_SECRET: "CWE-798",
            # [20251212_FEATURE] v1.4.0 CWE mappings
            SecuritySink.XXE: "CWE-611",
            SecuritySink.SSTI: "CWE-1336",
            # [20251215_FEATURE] v2.0.0 JavaScript CWE mappings
            SecuritySink.DOM_XSS: "CWE-79",
            SecuritySink.PROTOTYPE_POLLUTION: "CWE-1321",
            # [20251215_FEATURE] v2.0.0 P1 - Additional CWE mappings
            SecuritySink.REDIRECT: "CWE-601",
            # [20251229_FEATURE] v3.0.4 - Type System Evaporation
            SecuritySink.UNVALIDATED_OUTPUT: "CWE-20",
            # [20251219_FEATURE] v3.0.4 - Additional 12 vulnerability types
            SecuritySink.LDAP_INJECTION: "CWE-90",
            SecuritySink.XPATH_INJECTION: "CWE-643",
            SecuritySink.NOSQL_INJECTION: "CWE-943",
            SecuritySink.EMAIL_INJECTION: "CWE-93",
            SecuritySink.REGEX_DOS: "CWE-1333",
            SecuritySink.FORMAT_STRING: "CWE-134",
            SecuritySink.UNSAFE_REFLECTION: "CWE-470",
            SecuritySink.EL_INJECTION: "CWE-917",
            SecuritySink.GRAPHQL_INJECTION: "CWE-89",
            SecuritySink.CORS_MISCONFIGURATION: "CWE-942",
            SecuritySink.JWT_WEAKNESS: "CWE-347",
            SecuritySink.HTML_INJECTION: "CWE-80",
        }
        return mapping.get(self.sink_type, "CWE-Unknown")

    @property
    def description(self) -> str:
        """
        [20251214_FEATURE] v2.0.0 - Generate human-readable vulnerability description.

        Returns a description that explains:
        - What kind of vulnerability was found
        - Where the tainted data came from
        - How it flowed to the dangerous sink
        """
        # Build data flow description
        if self.taint_path:
            if len(self.taint_path) == 1:
                # Single item - might be a direct dangerous pattern
                flow_desc = self.taint_path[0]
            else:
                # Multiple items - show the flow
                flow_desc = f"'{self.taint_path[0]}' flows to {self.taint_path[-1]}"
                if len(self.taint_path) > 2:
                    middle = " → ".join(self.taint_path[1:-1])
                    flow_desc = f"'{self.taint_path[0]}' flows through {middle} to {self.taint_path[-1]}"
        else:
            flow_desc = "Dangerous pattern detected"

        # Source description - use actual TaintSource enum values
        source_desc = {
            TaintSource.USER_INPUT: "user input",
            TaintSource.FILE_CONTENT: "file contents",
            TaintSource.NETWORK_DATA: "network data",
            TaintSource.DATABASE: "database query result",
            TaintSource.ENVIRONMENT: "environment variable",
            TaintSource.HARDCODED: "hardcoded value",
            TaintSource.UNKNOWN: "untrusted data",
        }.get(self.taint_source, "tainted data")

        # Build final description
        if self.taint_source == TaintSource.UNKNOWN and len(self.taint_path) == 1:
            # Likely a dangerous pattern without taint tracking
            return flow_desc
        else:
            return f"{self.vulnerability_type}: {source_desc} ({flow_desc})"

    def to_dict(self) -> VulnerabilityDict:
        """Convert to dictionary for JSON serialization."""
        return {
            "type": self.vulnerability_type,
            "cwe": self.cwe_id,
            "sink": self.sink_type.name,
            "source": self.taint_source.name,
            "taint_path": self.taint_path,
            "taint_flow": self.taint_path,  # Alias for clearer API
            "sink_location": self.sink_location,
            "source_location": self.source_location,
            "sanitizers": list(self.sanitizers_applied),
            # [20251214_FEATURE] v2.0.0 - Enhanced vulnerability report
            "description": self.description,
            "severity": self._calculate_severity(),
            "recommendation": self._get_recommendation(),
            "cwe_link": f"https://cwe.mitre.org/data/definitions/{self.cwe_id.replace('CWE-', '')}.html",
        }

    def _get_recommendation(self) -> str:
        """
        [20251214_FEATURE] v2.0.0 - Get fix recommendation for vulnerability.
        """
        recommendations = {
            SecuritySink.SQL_QUERY: "Use parameterized queries: cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))",
            SecuritySink.HTML_OUTPUT: "Escape output using html.escape() or a template engine's auto-escape feature",
            SecuritySink.FILE_PATH: "Use os.path.basename() to strip directory traversal, validate against allowed paths",
            SecuritySink.SHELL_COMMAND: "Use subprocess.run() with a list of arguments instead of shell=True",
            SecuritySink.EVAL: "Avoid eval()/exec(). Use ast.literal_eval() for data, or a safe parser",
            SecuritySink.DESERIALIZATION: "Use JSON instead of pickle. If pickle required, use hmac verification",
            SecuritySink.LOG_OUTPUT: "Sanitize sensitive data before logging, redact credentials",
            SecuritySink.HEADER: "Validate header values, remove newline characters",
            SecuritySink.WEAK_CRYPTO: "Use SHA-256 or stronger (hashlib.sha256). For passwords, use bcrypt or argon2",
            SecuritySink.SSRF: "Validate URLs against allowlist, block internal IP ranges",
            SecuritySink.HARDCODED_SECRET: "Use environment variables or a secrets manager (AWS Secrets Manager, HashiCorp Vault)",
            SecuritySink.XXE: "Disable external entity processing: parser.setFeature(feature_external_ges, False)",
            SecuritySink.SSTI: "Use auto-escaping templates, avoid render_template_string() with user input",
            # [20251215_FEATURE] v2.0.0 - JavaScript/TypeScript recommendations
            SecuritySink.DOM_XSS: "Use textContent instead of innerHTML, or sanitize with DOMPurify.sanitize()",
            SecuritySink.PROTOTYPE_POLLUTION: "Use Object.create(null) for dictionaries, validate merge sources, use Map instead of Object",
            # [20251215_FEATURE] v2.0.0 P1 - Additional recommendations
            SecuritySink.REDIRECT: "Validate redirect URLs against allowlist, use relative paths, or verify same-origin",
            # [20251229_FEATURE] v3.0.4 - Type System Evaporation recommendations
            SecuritySink.UNVALIDATED_OUTPUT: "Validate enum/type values against allowed set before returning in HTTP response. Frontend types do NOT enforce runtime values",
            # [20251219_FEATURE] v3.0.4 - Additional 12 vulnerability type recommendations
            SecuritySink.LDAP_INJECTION: "Use parameterized LDAP queries, escape special characters with ldap.filter.escape_filter_chars()",
            SecuritySink.XPATH_INJECTION: "Use parameterized XPath queries or pre-compiled expressions. Validate input against allowlist",
            SecuritySink.NOSQL_INJECTION: "Use parameterized queries, avoid $where/$expr with user input. Sanitize with mongo-sanitize",
            SecuritySink.EMAIL_INJECTION: "Validate email addresses with strict regex, strip newlines from headers. Use email library validation",
            SecuritySink.REGEX_DOS: "Avoid user-controlled regex patterns. Use re2 library or set timeout. Validate regex complexity",
            SecuritySink.FORMAT_STRING: "Never use user input directly in format strings. Use parameterized logging: logger.info('User: %s', user)",
            SecuritySink.UNSAFE_REFLECTION: "Avoid getattr/setattr with user input. Use allowlist of permitted attributes/methods",
            SecuritySink.EL_INJECTION: "Disable SpEL/OGNL evaluation with user input. Use SimpleEvaluationContext in Spring",
            SecuritySink.GRAPHQL_INJECTION: "Disable introspection in production, implement query depth limiting, use persisted queries",
            SecuritySink.CORS_MISCONFIGURATION: "Use strict CORS allowlist, never reflect Origin header directly. Validate against known domains",
            SecuritySink.JWT_WEAKNESS: "Always verify algorithm (reject 'none'), use strong secrets (256+ bits), validate all claims",
            SecuritySink.HTML_INJECTION: "Escape HTML output with html.escape() or use textContent. Even non-script HTML can be dangerous",
        }
        return recommendations.get(self.sink_type, "Review the code for potential security issues")

    def _calculate_severity(self) -> str:
        """
        [20251214_FEATURE] v2.0.0 - Calculate vulnerability severity.

        Based on:
        - Sink type (some are more dangerous than others)
        - Whether sanitizers were bypassed
        - Source type (user input is more risky than env vars)
        """
        high_risk_sinks = {
            SecuritySink.SQL_QUERY,
            SecuritySink.SHELL_COMMAND,
            SecuritySink.EVAL,
            SecuritySink.DESERIALIZATION,
            # [20251219_FEATURE] v3.0.4 - Critical severity vulnerability types
            SecuritySink.EL_INJECTION,  # SpEL/OGNL can lead to RCE
            SecuritySink.LDAP_INJECTION,
            SecuritySink.NOSQL_INJECTION,
            SecuritySink.JWT_WEAKNESS,
            SecuritySink.UNSAFE_REFLECTION,
        }
        medium_risk_sinks = {
            SecuritySink.FILE_PATH,
            SecuritySink.HTML_OUTPUT,
            SecuritySink.SSRF,
            SecuritySink.XXE,
            SecuritySink.SSTI,
            # [20251219_FEATURE] v3.0.4 - Medium severity vulnerability types
            SecuritySink.XPATH_INJECTION,
            SecuritySink.EMAIL_INJECTION,
            SecuritySink.REGEX_DOS,
            SecuritySink.FORMAT_STRING,
            SecuritySink.GRAPHQL_INJECTION,
            SecuritySink.CORS_MISCONFIGURATION,
            SecuritySink.HTML_INJECTION,
        }

        if self.sink_type in high_risk_sinks:
            return "high"
        elif self.sink_type == SecuritySink.HARDCODED_SECRET:
            return "high"
        elif self.sink_type == SecuritySink.WEAK_CRYPTO:
            return "medium"
        elif self.sink_type in medium_risk_sinks:
            return "medium"
        else:
            return "low"

    def __repr__(self) -> str:  # pragma: no cover
        path_str = " → ".join(self.taint_path)
        return f"Vulnerability({self.vulnerability_type}, " f"flow: {path_str}, " f"{self.cwe_id})"


# =============================================================================
# Known Taint Sources - Pattern Matching
# =============================================================================

# Function calls that introduce taint
TAINT_SOURCE_PATTERNS: dict[str, TaintSource] = {
    # Flask/Django request handling
    "request.args.get": TaintSource.USER_INPUT,
    "request.form.get": TaintSource.USER_INPUT,
    "request.form": TaintSource.USER_INPUT,
    "request.args": TaintSource.USER_INPUT,
    "request.data": TaintSource.USER_INPUT,
    "request.json": TaintSource.USER_INPUT,
    "request.get_json": TaintSource.USER_INPUT,  # [20251220_FEATURE] v3.0.4 - Flask method form
    "request.get_data": TaintSource.USER_INPUT,  # [20251220_FEATURE] v3.0.4 - Flask method form
    "request.cookies.get": TaintSource.USER_INPUT,
    "request.headers.get": TaintSource.USER_INPUT,
    "request.GET.get": TaintSource.USER_INPUT,
    "request.POST.get": TaintSource.USER_INPUT,
    "request.GET": TaintSource.USER_INPUT,
    "request.POST": TaintSource.USER_INPUT,
    # Standard input
    "input": TaintSource.USER_INPUT,
    "sys.argv": TaintSource.USER_INPUT,
    # File operations
    "open.read": TaintSource.FILE_CONTENT,
    "file.read": TaintSource.FILE_CONTENT,
    "Path.read_text": TaintSource.FILE_CONTENT,
    # Network
    "socket.recv": TaintSource.NETWORK_DATA,
    "requests.get": TaintSource.NETWORK_DATA,
    "urllib.request.urlopen": TaintSource.NETWORK_DATA,
    # Database
    "cursor.fetchone": TaintSource.DATABASE,
    "cursor.fetchall": TaintSource.DATABASE,
    "cursor.fetchmany": TaintSource.DATABASE,
    # Environment
    "os.environ.get": TaintSource.ENVIRONMENT,
    "os.getenv": TaintSource.ENVIRONMENT,
    # ==========================================================================
    # [20251215_FEATURE] v2.0.0 - JavaScript/TypeScript Taint Sources
    # ==========================================================================
    # Express.js request handling
    "req.query": TaintSource.USER_INPUT,
    "req.body": TaintSource.USER_INPUT,
    "req.params": TaintSource.USER_INPUT,
    "req.headers": TaintSource.USER_INPUT,
    "req.cookies": TaintSource.USER_INPUT,
    "req.get": TaintSource.USER_INPUT,
    "req.param": TaintSource.USER_INPUT,
    # Koa.js
    "ctx.query": TaintSource.USER_INPUT,
    "ctx.request.body": TaintSource.USER_INPUT,
    "ctx.params": TaintSource.USER_INPUT,
    # Fastify
    "request.query": TaintSource.USER_INPUT,
    "request.body": TaintSource.USER_INPUT,
    "request.params": TaintSource.USER_INPUT,
    # Browser DOM
    "document.location": TaintSource.USER_INPUT,
    "document.URL": TaintSource.USER_INPUT,
    "document.documentURI": TaintSource.USER_INPUT,
    "document.referrer": TaintSource.USER_INPUT,
    "document.cookie": TaintSource.USER_INPUT,
    "location.href": TaintSource.USER_INPUT,
    "location.search": TaintSource.USER_INPUT,
    "location.hash": TaintSource.USER_INPUT,
    "location.pathname": TaintSource.USER_INPUT,
    "window.location": TaintSource.USER_INPUT,
    "window.name": TaintSource.USER_INPUT,
    "URLSearchParams": TaintSource.USER_INPUT,
    "postMessage": TaintSource.USER_INPUT,
    # Form inputs
    "document.getElementById": TaintSource.USER_INPUT,
    "document.querySelector": TaintSource.USER_INPUT,
    "element.value": TaintSource.USER_INPUT,
    "input.value": TaintSource.USER_INPUT,
    "textarea.value": TaintSource.USER_INPUT,
    # LocalStorage/SessionStorage (may contain tainted data)
    "localStorage.getItem": TaintSource.USER_INPUT,
    "sessionStorage.getItem": TaintSource.USER_INPUT,
    # Node.js environment
    "process.env": TaintSource.ENVIRONMENT,
    "process.argv": TaintSource.USER_INPUT,
    # Node.js file system
    "fs.readFile": TaintSource.FILE_CONTENT,
    "fs.readFileSync": TaintSource.FILE_CONTENT,
    "fs.createReadStream": TaintSource.FILE_CONTENT,
    # ==========================================================================
    # [20251215_FEATURE] v2.0.0 - Java Taint Sources
    # ==========================================================================
    # Servlet API
    "request.getParameter": TaintSource.USER_INPUT,
    "request.getParameterValues": TaintSource.USER_INPUT,
    "request.getParameterMap": TaintSource.USER_INPUT,
    "request.getQueryString": TaintSource.USER_INPUT,
    "request.getHeader": TaintSource.USER_INPUT,
    "request.getHeaders": TaintSource.USER_INPUT,
    "request.getCookies": TaintSource.USER_INPUT,
    "request.getInputStream": TaintSource.USER_INPUT,
    "request.getReader": TaintSource.USER_INPUT,
    "request.getPathInfo": TaintSource.USER_INPUT,
    "request.getRequestURI": TaintSource.USER_INPUT,
    "request.getRequestURL": TaintSource.USER_INPUT,
    "HttpServletRequest.getParameter": TaintSource.USER_INPUT,
    # Spring MVC
    "@RequestParam": TaintSource.USER_INPUT,
    "@PathVariable": TaintSource.USER_INPUT,
    "@RequestBody": TaintSource.USER_INPUT,
    "@RequestHeader": TaintSource.USER_INPUT,
    "@CookieValue": TaintSource.USER_INPUT,
    "@ModelAttribute": TaintSource.USER_INPUT,
    "WebRequest.getParameter": TaintSource.USER_INPUT,
    # JAX-RS
    "@QueryParam": TaintSource.USER_INPUT,
    "@PathParam": TaintSource.USER_INPUT,
    "@FormParam": TaintSource.USER_INPUT,
    "@HeaderParam": TaintSource.USER_INPUT,
    "@CookieParam": TaintSource.USER_INPUT,
    # File operations
    "FileInputStream": TaintSource.FILE_CONTENT,
    "Files.readAllBytes": TaintSource.FILE_CONTENT,
    "Files.readAllLines": TaintSource.FILE_CONTENT,
    "BufferedReader.readLine": TaintSource.FILE_CONTENT,
    # Database results
    "ResultSet.getString": TaintSource.DATABASE,
    "ResultSet.getObject": TaintSource.DATABASE,
    # System properties and environment
    "System.getProperty": TaintSource.ENVIRONMENT,
    "System.getenv": TaintSource.ENVIRONMENT,
}

# Function calls that are security sinks
SINK_PATTERNS: dict[str, SecuritySink] = {
    # SQL
    "cursor.execute": SecuritySink.SQL_QUERY,
    "connection.execute": SecuritySink.SQL_QUERY,
    "session.execute": SecuritySink.SQL_QUERY,
    "engine.execute": SecuritySink.SQL_QUERY,
    # [20251214_FEATURE] v2.0.0 - Additional SQL execute patterns
    "db.execute": SecuritySink.SQL_QUERY,
    "database.execute": SecuritySink.SQL_QUERY,
    "conn.execute": SecuritySink.SQL_QUERY,
    "cur.execute": SecuritySink.SQL_QUERY,
    "execute": SecuritySink.SQL_QUERY,  # Generic execute
    "executemany": SecuritySink.SQL_QUERY,
    "cursor.executemany": SecuritySink.SQL_QUERY,
    "RawSQL": SecuritySink.SQL_QUERY,
    "django.db.models.expressions.RawSQL": SecuritySink.SQL_QUERY,
    "django.db.models.RawSQL": SecuritySink.SQL_QUERY,
    "extra": SecuritySink.SQL_QUERY,
    "QuerySet.extra": SecuritySink.SQL_QUERY,
    "text": SecuritySink.SQL_QUERY,
    "sqlalchemy.text": SecuritySink.SQL_QUERY,
    "sqlalchemy.sql.expression.text": SecuritySink.SQL_QUERY,
    # HTML/XSS
    "render_template_string": SecuritySink.HTML_OUTPUT,
    "flask.render_template_string": SecuritySink.HTML_OUTPUT,
    "Response": SecuritySink.HTML_OUTPUT,
    "flask.Response": SecuritySink.HTML_OUTPUT,
    "make_response": SecuritySink.HTML_OUTPUT,
    "flask.make_response": SecuritySink.HTML_OUTPUT,
    "Markup": SecuritySink.HTML_OUTPUT,
    # "flask.Markup": SecuritySink.HTML_OUTPUT,  # Duplicate - defined in HTML_INJECTION section
    # "markupsafe.Markup": SecuritySink.HTML_OUTPUT,  # Duplicate - defined in HTML_INJECTION section
    # File paths
    "open": SecuritySink.FILE_PATH,
    "os.path.join": SecuritySink.FILE_PATH,
    "pathlib.Path": SecuritySink.FILE_PATH,
    "shutil.copy": SecuritySink.FILE_PATH,
    # Shell commands
    "os.system": SecuritySink.SHELL_COMMAND,
    "os.popen": SecuritySink.SHELL_COMMAND,
    "subprocess.run": SecuritySink.SHELL_COMMAND,
    "subprocess.call": SecuritySink.SHELL_COMMAND,
    "subprocess.Popen": SecuritySink.SHELL_COMMAND,
    # Eval
    "eval": SecuritySink.EVAL,
    "exec": SecuritySink.EVAL,
    "compile": SecuritySink.EVAL,
    # Deserialization
    "pickle.load": SecuritySink.DESERIALIZATION,
    "pickle.loads": SecuritySink.DESERIALIZATION,
    "_pickle.load": SecuritySink.DESERIALIZATION,
    "_pickle.loads": SecuritySink.DESERIALIZATION,
    "yaml.load": SecuritySink.DESERIALIZATION,
    "yaml.unsafe_load": SecuritySink.DESERIALIZATION,
    "marshal.loads": SecuritySink.DESERIALIZATION,
    # Weak Cryptography (CWE-327)
    "hashlib.md5": SecuritySink.WEAK_CRYPTO,
    "hashlib.sha1": SecuritySink.WEAK_CRYPTO,
    "cryptography.hazmat.primitives.ciphers.algorithms.DES": SecuritySink.WEAK_CRYPTO,
    "Crypto.Cipher.DES": SecuritySink.WEAK_CRYPTO,  # PyCryptodome
    "Crypto.Hash.MD5": SecuritySink.WEAK_CRYPTO,
    "Crypto.Hash.SHA": SecuritySink.WEAK_CRYPTO,
    "DES": SecuritySink.WEAK_CRYPTO,
    "MD5.new": SecuritySink.WEAK_CRYPTO,
    "SHA.new": SecuritySink.WEAK_CRYPTO,
    # SSRF - Server-Side Request Forgery (CWE-918)
    "requests.get": SecuritySink.SSRF,
    "requests.post": SecuritySink.SSRF,
    "requests.put": SecuritySink.SSRF,
    "requests.delete": SecuritySink.SSRF,
    "requests.head": SecuritySink.SSRF,
    "requests.patch": SecuritySink.SSRF,
    "urllib.request.urlopen": SecuritySink.SSRF,
    "urllib.request.Request": SecuritySink.SSRF,
    "urlopen": SecuritySink.SSRF,
    "Request": SecuritySink.SSRF,
    "httpx.get": SecuritySink.SSRF,
    "httpx.post": SecuritySink.SSRF,
    "httpx.AsyncClient.get": SecuritySink.SSRF,
    "aiohttp.ClientSession.get": SecuritySink.SSRF,
    # NoSQL Injection - MongoDB (v1.3.0) [20251219_FEATURE] Updated to NOSQL_INJECTION
    "collection.find": SecuritySink.NOSQL_INJECTION,
    "collection.find_one": SecuritySink.NOSQL_INJECTION,
    "collection.find_one_and_delete": SecuritySink.NOSQL_INJECTION,
    "collection.find_one_and_replace": SecuritySink.NOSQL_INJECTION,
    "collection.find_one_and_update": SecuritySink.NOSQL_INJECTION,
    "collection.aggregate": SecuritySink.NOSQL_INJECTION,
    "collection.count_documents": SecuritySink.NOSQL_INJECTION,
    "collection.distinct": SecuritySink.NOSQL_INJECTION,
    "collection.update_one": SecuritySink.NOSQL_INJECTION,
    "collection.update_many": SecuritySink.NOSQL_INJECTION,
    "collection.delete_one": SecuritySink.NOSQL_INJECTION,
    "collection.delete_many": SecuritySink.NOSQL_INJECTION,
    "collection.insert_one": SecuritySink.NOSQL_INJECTION,
    "collection.insert_many": SecuritySink.NOSQL_INJECTION,
    "collection.replace_one": SecuritySink.NOSQL_INJECTION,
    "db.command": SecuritySink.NOSQL_INJECTION,
    # Motor (async MongoDB)
    "motor_collection.find": SecuritySink.NOSQL_INJECTION,
    "motor_collection.find_one": SecuritySink.NOSQL_INJECTION,
    "motor_collection.aggregate": SecuritySink.NOSQL_INJECTION,
    # MongoEngine ORM
    "Document.objects": SecuritySink.NOSQL_INJECTION,
    "QuerySet.filter": SecuritySink.NOSQL_INJECTION,
    "QuerySet.get": SecuritySink.NOSQL_INJECTION,
    # [20251219_FEATURE] v3.0.4 - Additional NoSQL patterns
    "$where": SecuritySink.NOSQL_INJECTION,  # MongoDB JS execution
    "$expr": SecuritySink.NOSQL_INJECTION,  # MongoDB expression
    "$function": SecuritySink.NOSQL_INJECTION,  # MongoDB JS function
    "pymongo.collection.Collection.find": SecuritySink.NOSQL_INJECTION,
    "pymongo.collection.Collection.aggregate": SecuritySink.NOSQL_INJECTION,
    # LDAP Injection (v1.3.0) [20251219_FEATURE] Updated to LDAP_INJECTION
    "ldap.search": SecuritySink.LDAP_INJECTION,
    "ldap.search_s": SecuritySink.LDAP_INJECTION,
    "ldap.search_st": SecuritySink.LDAP_INJECTION,
    "ldap.search_ext": SecuritySink.LDAP_INJECTION,
    "ldap.search_ext_s": SecuritySink.LDAP_INJECTION,
    "ldap.bind": SecuritySink.LDAP_INJECTION,
    "ldap.bind_s": SecuritySink.LDAP_INJECTION,
    "ldap.simple_bind": SecuritySink.LDAP_INJECTION,
    "ldap.simple_bind_s": SecuritySink.LDAP_INJECTION,
    "ldap.modify": SecuritySink.LDAP_INJECTION,
    "ldap.modify_s": SecuritySink.LDAP_INJECTION,
    "ldap.add": SecuritySink.LDAP_INJECTION,
    "ldap.add_s": SecuritySink.LDAP_INJECTION,
    "ldap.delete": SecuritySink.LDAP_INJECTION,
    "ldap.delete_s": SecuritySink.LDAP_INJECTION,
    # ldap3 library
    "Connection.search": SecuritySink.LDAP_INJECTION,
    "Connection.bind": SecuritySink.LDAP_INJECTION,
    "Connection.modify": SecuritySink.LDAP_INJECTION,
    "Connection.add": SecuritySink.LDAP_INJECTION,
    "Connection.delete": SecuritySink.LDAP_INJECTION,
    # [20251219_FEATURE] v3.0.4 - Additional LDAP patterns
    "ldap.filter_format": SecuritySink.LDAP_INJECTION,
    "ldap3.Server": SecuritySink.LDAP_INJECTION,
    "ldap3.Connection": SecuritySink.LDAP_INJECTION,
    # [20251212_FEATURE] v1.4.0 - XXE (XML External Entity) Injection (CWE-611)
    "xml.etree.ElementTree.parse": SecuritySink.XXE,
    "xml.etree.ElementTree.fromstring": SecuritySink.XXE,
    "xml.etree.ElementTree.iterparse": SecuritySink.XXE,
    "ElementTree.parse": SecuritySink.XXE,
    "ElementTree.fromstring": SecuritySink.XXE,
    "ET.parse": SecuritySink.XXE,
    "ET.fromstring": SecuritySink.XXE,
    "xml.dom.minidom.parse": SecuritySink.XXE,
    "xml.dom.minidom.parseString": SecuritySink.XXE,
    "minidom.parse": SecuritySink.XXE,
    "minidom.parseString": SecuritySink.XXE,
    "xml.sax.parse": SecuritySink.XXE,
    "xml.sax.parseString": SecuritySink.XXE,
    "sax.parse": SecuritySink.XXE,
    "lxml.etree.parse": SecuritySink.XXE,
    "lxml.etree.fromstring": SecuritySink.XXE,
    "lxml.etree.XML": SecuritySink.XXE,
    "etree.parse": SecuritySink.XXE,
    "etree.fromstring": SecuritySink.XXE,
    "etree.XML": SecuritySink.XXE,
    "xmlrpc.client.ServerProxy": SecuritySink.XXE,
    # [20251212_FEATURE] v1.4.0 - SSTI (Server-Side Template Injection) (CWE-1336)
    "jinja2.Template": SecuritySink.SSTI,
    "Template": SecuritySink.SSTI,  # Generic template constructor
    "Environment.from_string": SecuritySink.SSTI,
    "jinja2.Environment.from_string": SecuritySink.SSTI,
    "mako.template.Template": SecuritySink.SSTI,
    "mako.Template": SecuritySink.SSTI,
    "django.template.Template": SecuritySink.SSTI,
    "tornado.template.Template": SecuritySink.SSTI,
    "chameleon.PageTemplate": SecuritySink.SSTI,
    "genshi.template.MarkupTemplate": SecuritySink.SSTI,
    # ==========================================================================
    # [20251215_FEATURE] v2.0.0 - JavaScript/TypeScript Security Sinks
    # [20251215_BUGFIX] Deduplicate overlapping sink keys across languages.
    # ==========================================================================
    # DOM XSS - Direct DOM manipulation with user input (CWE-79)
    "innerHTML": SecuritySink.DOM_XSS,
    "outerHTML": SecuritySink.DOM_XSS,
    "document.write": SecuritySink.DOM_XSS,
    "document.writeln": SecuritySink.DOM_XSS,
    "insertAdjacentHTML": SecuritySink.DOM_XSS,
    "element.innerHTML": SecuritySink.DOM_XSS,
    "element.outerHTML": SecuritySink.DOM_XSS,
    "document.body.innerHTML": SecuritySink.DOM_XSS,
    "jQuery.html": SecuritySink.DOM_XSS,
    "$.html": SecuritySink.DOM_XSS,
    "$().html": SecuritySink.DOM_XSS,
    "React.dangerouslySetInnerHTML": SecuritySink.DOM_XSS,
    "dangerouslySetInnerHTML": SecuritySink.DOM_XSS,
    "v-html": SecuritySink.DOM_XSS,  # Vue.js
    "[innerHTML]": SecuritySink.DOM_XSS,  # Angular
    # JavaScript Eval Injection (CWE-94)
    "Function": SecuritySink.EVAL,
    "new Function": SecuritySink.EVAL,
    "setTimeout": SecuritySink.EVAL,  # When called with string argument
    "setInterval": SecuritySink.EVAL,  # When called with string argument
    "setImmediate": SecuritySink.EVAL,
    "execScript": SecuritySink.EVAL,
    "vm.runInThisContext": SecuritySink.EVAL,
    "vm.runInNewContext": SecuritySink.EVAL,
    "vm.runInContext": SecuritySink.EVAL,
    # Prototype Pollution (CWE-1321)
    "Object.assign": SecuritySink.PROTOTYPE_POLLUTION,
    "_.merge": SecuritySink.PROTOTYPE_POLLUTION,
    "_.extend": SecuritySink.PROTOTYPE_POLLUTION,
    "_.defaultsDeep": SecuritySink.PROTOTYPE_POLLUTION,
    "$.extend": SecuritySink.PROTOTYPE_POLLUTION,
    "jQuery.extend": SecuritySink.PROTOTYPE_POLLUTION,
    "lodash.merge": SecuritySink.PROTOTYPE_POLLUTION,
    "lodash.extend": SecuritySink.PROTOTYPE_POLLUTION,
    "lodash.defaultsDeep": SecuritySink.PROTOTYPE_POLLUTION,
    "deepmerge": SecuritySink.PROTOTYPE_POLLUTION,
    "merge-deep": SecuritySink.PROTOTYPE_POLLUTION,
    "object-path.set": SecuritySink.PROTOTYPE_POLLUTION,
    # Node.js Command Injection (CWE-78)
    "child_process.exec": SecuritySink.SHELL_COMMAND,
    "child_process.execSync": SecuritySink.SHELL_COMMAND,
    "child_process.spawn": SecuritySink.SHELL_COMMAND,
    "child_process.spawnSync": SecuritySink.SHELL_COMMAND,
    "child_process.execFile": SecuritySink.SHELL_COMMAND,
    "child_process.execFileSync": SecuritySink.SHELL_COMMAND,
    "child_process.fork": SecuritySink.SHELL_COMMAND,
    "spawn": SecuritySink.SHELL_COMMAND,
    "spawnSync": SecuritySink.SHELL_COMMAND,
    "shelljs.exec": SecuritySink.SHELL_COMMAND,
    "execa": SecuritySink.SHELL_COMMAND,
    # Node.js File System (Path Traversal - CWE-22)
    "fs.readFile": SecuritySink.FILE_PATH,
    "fs.readFileSync": SecuritySink.FILE_PATH,
    "fs.writeFile": SecuritySink.FILE_PATH,
    "fs.writeFileSync": SecuritySink.FILE_PATH,
    "fs.createReadStream": SecuritySink.FILE_PATH,
    "fs.createWriteStream": SecuritySink.FILE_PATH,
    "fs.unlink": SecuritySink.FILE_PATH,
    "fs.unlinkSync": SecuritySink.FILE_PATH,
    "fs.rmdir": SecuritySink.FILE_PATH,
    "fs.rmdirSync": SecuritySink.FILE_PATH,
    "fs.rename": SecuritySink.FILE_PATH,
    "fs.renameSync": SecuritySink.FILE_PATH,
    "path.join": SecuritySink.FILE_PATH,
    "path.resolve": SecuritySink.FILE_PATH,
    "require": SecuritySink.FILE_PATH,  # Dynamic require with user input
    # Node.js SQL Injection (CWE-89)
    "connection.query": SecuritySink.SQL_QUERY,
    "pool.query": SecuritySink.SQL_QUERY,
    "mysql.query": SecuritySink.SQL_QUERY,
    "mysql2.query": SecuritySink.SQL_QUERY,
    "pg.query": SecuritySink.SQL_QUERY,
    "client.query": SecuritySink.SQL_QUERY,
    "knex.raw": SecuritySink.SQL_QUERY,
    "knex.whereRaw": SecuritySink.SQL_QUERY,
    "knex.havingRaw": SecuritySink.SQL_QUERY,
    "sequelize.query": SecuritySink.SQL_QUERY,
    "Sequelize.query": SecuritySink.SQL_QUERY,
    "prisma.$queryRaw": SecuritySink.SQL_QUERY,
    "prisma.$executeRaw": SecuritySink.SQL_QUERY,
    "typeorm.query": SecuritySink.SQL_QUERY,
    "mongoose.aggregate": SecuritySink.SQL_QUERY,
    "Model.find": SecuritySink.SQL_QUERY,  # MongoDB with user input
    "Model.findOne": SecuritySink.SQL_QUERY,
    "Model.updateOne": SecuritySink.SQL_QUERY,
    "Model.deleteOne": SecuritySink.SQL_QUERY,
    # Node.js SSRF (CWE-918)
    "axios.get": SecuritySink.SSRF,
    "axios.post": SecuritySink.SSRF,
    "axios.put": SecuritySink.SSRF,
    "axios.delete": SecuritySink.SSRF,
    "axios.request": SecuritySink.SSRF,
    "fetch": SecuritySink.SSRF,
    "node-fetch": SecuritySink.SSRF,
    "got": SecuritySink.SSRF,
    "got.get": SecuritySink.SSRF,
    "superagent.get": SecuritySink.SSRF,
    "http.get": SecuritySink.SSRF,
    "https.get": SecuritySink.SSRF,
    "http.request": SecuritySink.SSRF,
    "https.request": SecuritySink.SSRF,
    "request": SecuritySink.SSRF,
    "request.get": SecuritySink.SSRF,
    # Node.js Deserialization (CWE-502)
    "JSON.parse": SecuritySink.DESERIALIZATION,  # When used with untrusted data without validation
    "serialize-javascript": SecuritySink.DESERIALIZATION,
    "node-serialize.unserialize": SecuritySink.DESERIALIZATION,
    "js-yaml.load": SecuritySink.DESERIALIZATION,
    "flatted.parse": SecuritySink.DESERIALIZATION,
    # ==========================================================================
    # [20251229_FEATURE] v3.0.4 - JavaScript/TypeScript Weak Crypto (CWE-327)
    # ==========================================================================
    "crypto.createHash('md5')": SecuritySink.WEAK_CRYPTO,
    "crypto.createHash('sha1')": SecuritySink.WEAK_CRYPTO,
    "crypto.createCipheriv('des')": SecuritySink.WEAK_CRYPTO,
    "crypto.createCipheriv('des-ede')": SecuritySink.WEAK_CRYPTO,
    "crypto.createCipheriv('des-ede3')": SecuritySink.WEAK_CRYPTO,
    "CryptoJS.MD5": SecuritySink.WEAK_CRYPTO,
    "CryptoJS.SHA1": SecuritySink.WEAK_CRYPTO,
    "CryptoJS.DES": SecuritySink.WEAK_CRYPTO,
    "CryptoJS.TripleDES": SecuritySink.WEAK_CRYPTO,
    "CryptoJS.RC4": SecuritySink.WEAK_CRYPTO,
    "md5(": SecuritySink.WEAK_CRYPTO,
    "sha1(": SecuritySink.WEAK_CRYPTO,
    "blueimp-md5": SecuritySink.WEAK_CRYPTO,
    "js-md5": SecuritySink.WEAK_CRYPTO,
    "js-sha1": SecuritySink.WEAK_CRYPTO,
    # ==========================================================================
    # [20251229_FEATURE] v3.0.4 - JavaScript/TypeScript XXE (CWE-611)
    # ==========================================================================
    "DOMParser": SecuritySink.XXE,
    "new DOMParser": SecuritySink.XXE,
    "DOMParser.parseFromString": SecuritySink.XXE,
    "xml2js.parseString": SecuritySink.XXE,
    "xml2js.Parser": SecuritySink.XXE,
    "fast-xml-parser": SecuritySink.XXE,
    "XMLParser": SecuritySink.XXE,
    "xmldom": SecuritySink.XXE,
    "xmldom.DOMParser": SecuritySink.XXE,
    "libxmljs": SecuritySink.XXE,
    "libxmljs.parseXml": SecuritySink.XXE,
    "libxmljs.parseXmlString": SecuritySink.XXE,
    "sax.parser": SecuritySink.XXE,
    "saxes.SaxesParser": SecuritySink.XXE,
    "expat": SecuritySink.XXE,
    "node-expat": SecuritySink.XXE,
    "cheerio.load": SecuritySink.XXE,  # Can parse XML
    # ==========================================================================
    # [20251229_FEATURE] v3.0.4 - JavaScript/TypeScript Log Injection (CWE-117)
    # ==========================================================================
    "console.log": SecuritySink.LOG_OUTPUT,
    "console.error": SecuritySink.LOG_OUTPUT,
    "console.warn": SecuritySink.LOG_OUTPUT,
    "console.info": SecuritySink.LOG_OUTPUT,
    "console.debug": SecuritySink.LOG_OUTPUT,
    "winston.log": SecuritySink.LOG_OUTPUT,
    "winston.info": SecuritySink.LOG_OUTPUT,
    "winston.error": SecuritySink.LOG_OUTPUT,
    "winston.warn": SecuritySink.LOG_OUTPUT,
    "winston.debug": SecuritySink.LOG_OUTPUT,
    "pino": SecuritySink.LOG_OUTPUT,
    "pino.info": SecuritySink.LOG_OUTPUT,
    "pino.error": SecuritySink.LOG_OUTPUT,
    "pino.warn": SecuritySink.LOG_OUTPUT,
    "bunyan": SecuritySink.LOG_OUTPUT,
    "bunyan.info": SecuritySink.LOG_OUTPUT,
    "bunyan.error": SecuritySink.LOG_OUTPUT,
    "log4js": SecuritySink.LOG_OUTPUT,
    "log4js.getLogger": SecuritySink.LOG_OUTPUT,
    "debug(": SecuritySink.LOG_OUTPUT,  # debug module
    "loglevel": SecuritySink.LOG_OUTPUT,
    # ==========================================================================
    # [20251229_FEATURE] v3.0.4 - ReDoS (CWE-1333)
    # ==========================================================================
    "new RegExp": SecuritySink.EVAL,  # Dynamic regex with user input = ReDoS risk
    "RegExp(": SecuritySink.EVAL,
    # ==========================================================================
    # [20251215_FEATURE] v2.0.0 - Java Security Sinks
    # ==========================================================================
    # Java SQL Injection (CWE-89)
    "Statement.execute": SecuritySink.SQL_QUERY,
    "Statement.executeQuery": SecuritySink.SQL_QUERY,
    "Statement.executeUpdate": SecuritySink.SQL_QUERY,
    "PreparedStatement.execute": SecuritySink.SQL_QUERY,
    "createStatement": SecuritySink.SQL_QUERY,
    "createQuery": SecuritySink.SQL_QUERY,  # JPA
    "createNativeQuery": SecuritySink.SQL_QUERY,  # JPA
    "entityManager.createQuery": SecuritySink.SQL_QUERY,
    "entityManager.createNativeQuery": SecuritySink.SQL_QUERY,
    # [20251215_FEATURE] v2.0.1 Spring Data / JPA expansion
    "entityManager.createNamedQuery": SecuritySink.SQL_QUERY,
    "entityManager.createStoredProcedureQuery": SecuritySink.SQL_QUERY,
    "Query.setParameter": SecuritySink.SQL_QUERY,
    "TypedQuery.setParameter": SecuritySink.SQL_QUERY,
    "JpaRepository.deleteBy": SecuritySink.SQL_QUERY,
    "JpaRepository.removeBy": SecuritySink.SQL_QUERY,
    "JdbcTemplate.batchUpdate": SecuritySink.SQL_QUERY,
    "jdbcTemplate.query": SecuritySink.SQL_QUERY,  # Spring
    "jdbcTemplate.queryForObject": SecuritySink.SQL_QUERY,
    "jdbcTemplate.queryForList": SecuritySink.SQL_QUERY,
    "jdbcTemplate.update": SecuritySink.SQL_QUERY,
    "jdbcTemplate.execute": SecuritySink.SQL_QUERY,
    "namedParameterJdbcTemplate.query": SecuritySink.SQL_QUERY,
    # Java Command Injection (CWE-78)
    "Runtime.exec": SecuritySink.SHELL_COMMAND,
    "Runtime.getRuntime().exec": SecuritySink.SHELL_COMMAND,
    "ProcessBuilder": SecuritySink.SHELL_COMMAND,
    "ProcessBuilder.command": SecuritySink.SHELL_COMMAND,
    "ProcessBuilder.start": SecuritySink.SHELL_COMMAND,
    # Java Path Traversal (CWE-22)
    "new File": SecuritySink.FILE_PATH,
    "File": SecuritySink.FILE_PATH,
    "FileInputStream": SecuritySink.FILE_PATH,
    "FileOutputStream": SecuritySink.FILE_PATH,
    "FileReader": SecuritySink.FILE_PATH,
    "FileWriter": SecuritySink.FILE_PATH,
    "Files.readAllBytes": SecuritySink.FILE_PATH,
    "Files.readAllLines": SecuritySink.FILE_PATH,
    "Files.write": SecuritySink.FILE_PATH,
    "Paths.get": SecuritySink.FILE_PATH,
    # Java XXE (CWE-611)
    "DocumentBuilderFactory.newInstance": SecuritySink.XXE,
    "SAXParserFactory.newInstance": SecuritySink.XXE,
    "XMLInputFactory.newInstance": SecuritySink.XXE,
    "TransformerFactory.newInstance": SecuritySink.XXE,
    "SchemaFactory.newInstance": SecuritySink.XXE,
    "XMLReader.parse": SecuritySink.XXE,
    # Java Deserialization (CWE-502)
    "ObjectInputStream.readObject": SecuritySink.DESERIALIZATION,
    "ObjectInputStream": SecuritySink.DESERIALIZATION,
    "readObject": SecuritySink.DESERIALIZATION,
    "XMLDecoder": SecuritySink.DESERIALIZATION,
    "XStream.fromXML": SecuritySink.DESERIALIZATION,
    "ObjectMapper.readValue": SecuritySink.DESERIALIZATION,  # Jackson
    "Gson.fromJson": SecuritySink.DESERIALIZATION,
    # Java SSRF (CWE-918)
    "URL.openConnection": SecuritySink.SSRF,
    "URL.openStream": SecuritySink.SSRF,
    "HttpURLConnection": SecuritySink.SSRF,
    "HttpClient.send": SecuritySink.SSRF,
    "RestTemplate.getForObject": SecuritySink.SSRF,  # Spring
    "RestTemplate.postForObject": SecuritySink.SSRF,
    "RestTemplate.exchange": SecuritySink.SSRF,
    "WebClient.get": SecuritySink.SSRF,  # Spring WebFlux
    "WebClient.post": SecuritySink.SSRF,
    # Java LDAP Injection
    "DirContext.search": SecuritySink.SQL_QUERY,
    "InitialDirContext.search": SecuritySink.SQL_QUERY,
    "LdapTemplate.search": SecuritySink.SQL_QUERY,  # Spring LDAP
    "LdapTemplate.authenticate": SecuritySink.SQL_QUERY,  # [20251215_FEATURE] LDAP auth
    "BindAuthenticator.authenticate": SecuritySink.SQL_QUERY,
    # Java Expression Language Injection (similar to SSTI)
    # Removed duplicate: "ExpressionParser.parseExpression" - defined in EL_INJECTION section
    "SpelExpressionParser": SecuritySink.SSTI,
    "OGNL.getValue": SecuritySink.SSTI,  # Struts
    # Removed duplicate: "MVEL.eval" - defined in EL_INJECTION section
    # ==========================================================================
    # [20251215_FEATURE] v2.0.0 P1 - Additional Spring Security Patterns
    # ==========================================================================
    # Spring Data JPA (CWE-89)
    "JpaRepository.findBy": SecuritySink.SQL_QUERY,  # Custom query methods
    "@Query": SecuritySink.SQL_QUERY,  # JPQL annotation
    "Specification.where": SecuritySink.SQL_QUERY,  # Criteria API
    "CriteriaBuilder.createQuery": SecuritySink.SQL_QUERY,
    # Spring Security expression injection
    "@PreAuthorize": SecuritySink.SSTI,  # SpEL in security annotations
    "@PostAuthorize": SecuritySink.SSTI,
    "@Secured": SecuritySink.SSTI,
    "SecurityExpressionHandler": SecuritySink.SSTI,
    # [20251215_FEATURE] v2.0.1 Spring Security OAuth/SAML coverage
    "JwtDecoder.decode": SecuritySink.SSTI,
    "JwtEncoder.encode": SecuritySink.SSTI,
    "OAuth2AuthorizedClientManager.authorize": SecuritySink.SSTI,
    "Saml2AuthenticationRequestFactory.createAuthenticationRequest": SecuritySink.SSTI,
    "Saml2AuthenticationRequestContext": SecuritySink.SSTI,
    # Spring View resolution (Server-Side Template Injection)
    "ModelAndView": SecuritySink.SSTI,  # View name from user input
    "RedirectView": SecuritySink.REDIRECT,  # Open redirect
    "redirect:": SecuritySink.REDIRECT,
    "forward:": SecuritySink.FILE_PATH,  # Path traversal via forward
    # Spring Messaging (WebSocket)
    "@MessageMapping": SecuritySink.SSTI,  # Message handler
    "SimpMessagingTemplate.convertAndSend": SecuritySink.SSTI,
    # Spring Cloud (SSRF)
    "DiscoveryClient.getInstances": SecuritySink.SSRF,
    "LoadBalancerClient.choose": SecuritySink.SSRF,
    "RestTemplate.getForEntity": SecuritySink.SSRF,
    "WebClient.uri": SecuritySink.SSRF,
    # Spring Batch (File/Path injection)
    "FlatFileItemReader.setResource": SecuritySink.FILE_PATH,
    "FlatFileItemWriter.setResource": SecuritySink.FILE_PATH,
    # Hibernate (CWE-89)
    "Session.createQuery": SecuritySink.SQL_QUERY,
    "Session.createSQLQuery": SecuritySink.SQL_QUERY,
    "Session.createNativeQuery": SecuritySink.SQL_QUERY,
    "Criteria.add": SecuritySink.SQL_QUERY,
    # MyBatis (CWE-89) - ${}  interpolation is vulnerable
    "SqlSession.selectOne": SecuritySink.SQL_QUERY,
    "SqlSession.selectList": SecuritySink.SQL_QUERY,
    "SqlSession.update": SecuritySink.SQL_QUERY,
    "SqlSession.delete": SecuritySink.SQL_QUERY,
    "SqlSession.insert": SecuritySink.SQL_QUERY,
    # ==========================================================================
    # [20251219_FEATURE] v3.0.4 - XPath Injection (CWE-643)
    # ==========================================================================
    # Python
    "lxml.etree.XPath": SecuritySink.XPATH_INJECTION,
    "etree.XPath": SecuritySink.XPATH_INJECTION,
    "xml.etree.ElementTree.find": SecuritySink.XPATH_INJECTION,
    "ElementTree.find": SecuritySink.XPATH_INJECTION,
    "Element.find": SecuritySink.XPATH_INJECTION,
    "Element.findall": SecuritySink.XPATH_INJECTION,
    "Element.findtext": SecuritySink.XPATH_INJECTION,
    "Element.iterfind": SecuritySink.XPATH_INJECTION,
    ".xpath(": SecuritySink.XPATH_INJECTION,  # lxml pattern
    # Java
    "XPathFactory.newInstance": SecuritySink.XPATH_INJECTION,
    "XPath.compile": SecuritySink.XPATH_INJECTION,
    "XPath.evaluate": SecuritySink.XPATH_INJECTION,
    "XPathExpression.evaluate": SecuritySink.XPATH_INJECTION,
    # JavaScript
    "document.evaluate": SecuritySink.XPATH_INJECTION,
    "xpath.select": SecuritySink.XPATH_INJECTION,
    "xpath.parse": SecuritySink.XPATH_INJECTION,
    "xmldom.evaluate": SecuritySink.XPATH_INJECTION,
    # ==========================================================================
    # [20251219_FEATURE] v3.0.4 - Email/SMTP Injection (CWE-93)
    # ==========================================================================
    # Python
    "smtplib.SMTP.sendmail": SecuritySink.EMAIL_INJECTION,
    "smtplib.SMTP_SSL.sendmail": SecuritySink.EMAIL_INJECTION,
    "email.message.EmailMessage": SecuritySink.EMAIL_INJECTION,
    "email.mime.text.MIMEText": SecuritySink.EMAIL_INJECTION,
    "email.mime.multipart.MIMEMultipart": SecuritySink.EMAIL_INJECTION,
    "flask_mail.Message": SecuritySink.EMAIL_INJECTION,
    "django.core.mail.send_mail": SecuritySink.EMAIL_INJECTION,
    "django.core.mail.EmailMessage": SecuritySink.EMAIL_INJECTION,
    # Java
    "MimeMessage.setSubject": SecuritySink.EMAIL_INJECTION,
    "MimeMessage.setRecipients": SecuritySink.EMAIL_INJECTION,
    "MimeMessage.addRecipients": SecuritySink.EMAIL_INJECTION,
    "MimeMessage.setFrom": SecuritySink.EMAIL_INJECTION,
    "Transport.send": SecuritySink.EMAIL_INJECTION,
    "JavaMailSender.send": SecuritySink.EMAIL_INJECTION,
    # JavaScript
    "nodemailer.createTransport": SecuritySink.EMAIL_INJECTION,
    "transporter.sendMail": SecuritySink.EMAIL_INJECTION,
    "sendgrid.send": SecuritySink.EMAIL_INJECTION,
    "mailgun.messages.send": SecuritySink.EMAIL_INJECTION,
    # ==========================================================================
    # [20251219_FEATURE] v3.0.4 - ReDoS via User-Controlled Regex (CWE-1333)
    # ==========================================================================
    # Python
    "re.compile": SecuritySink.REGEX_DOS,
    "re.match": SecuritySink.REGEX_DOS,
    "re.search": SecuritySink.REGEX_DOS,
    "re.findall": SecuritySink.REGEX_DOS,
    "re.sub": SecuritySink.REGEX_DOS,
    "re.split": SecuritySink.REGEX_DOS,
    "regex.compile": SecuritySink.REGEX_DOS,  # regex library
    # Java
    "Pattern.compile": SecuritySink.REGEX_DOS,
    "Pattern.matches": SecuritySink.REGEX_DOS,
    "String.matches": SecuritySink.REGEX_DOS,
    "String.replaceAll": SecuritySink.REGEX_DOS,
    "String.split": SecuritySink.REGEX_DOS,
    # JavaScript (already have new RegExp)
    ".match(": SecuritySink.REGEX_DOS,
    ".replace(": SecuritySink.REGEX_DOS,
    ".split(": SecuritySink.REGEX_DOS,
    "String.prototype.match": SecuritySink.REGEX_DOS,
    "String.prototype.replace": SecuritySink.REGEX_DOS,
    # ==========================================================================
    # [20251219_FEATURE] v3.0.4 - Format String Vulnerability (CWE-134)
    # ==========================================================================
    # Python
    "str.format": SecuritySink.FORMAT_STRING,
    ".format(": SecuritySink.FORMAT_STRING,
    "f-string": SecuritySink.FORMAT_STRING,  # Detected via AST
    "logging.info": SecuritySink.FORMAT_STRING,  # If format string from user
    "logging.warning": SecuritySink.FORMAT_STRING,
    "logging.error": SecuritySink.FORMAT_STRING,
    "logging.debug": SecuritySink.FORMAT_STRING,
    "logging.critical": SecuritySink.FORMAT_STRING,
    "logger.info": SecuritySink.FORMAT_STRING,
    "logger.warning": SecuritySink.FORMAT_STRING,
    "logger.error": SecuritySink.FORMAT_STRING,
    "logger.debug": SecuritySink.FORMAT_STRING,
    # Java
    "String.format": SecuritySink.FORMAT_STRING,
    "PrintStream.printf": SecuritySink.FORMAT_STRING,
    "PrintWriter.printf": SecuritySink.FORMAT_STRING,
    "Formatter.format": SecuritySink.FORMAT_STRING,
    # C/C++ (for completeness, if analyzing native code)
    "printf": SecuritySink.FORMAT_STRING,
    "sprintf": SecuritySink.FORMAT_STRING,
    "fprintf": SecuritySink.FORMAT_STRING,
    "snprintf": SecuritySink.FORMAT_STRING,
    # ==========================================================================
    # [20251219_FEATURE] v3.0.4 - Unsafe Reflection (CWE-470)
    # ==========================================================================
    # Python
    "getattr": SecuritySink.UNSAFE_REFLECTION,
    "setattr": SecuritySink.UNSAFE_REFLECTION,
    "delattr": SecuritySink.UNSAFE_REFLECTION,
    "__import__": SecuritySink.UNSAFE_REFLECTION,
    "importlib.import_module": SecuritySink.UNSAFE_REFLECTION,
    "globals()": SecuritySink.UNSAFE_REFLECTION,
    "locals()": SecuritySink.UNSAFE_REFLECTION,
    "vars()": SecuritySink.UNSAFE_REFLECTION,
    # Java
    "Class.forName": SecuritySink.UNSAFE_REFLECTION,
    "Class.newInstance": SecuritySink.UNSAFE_REFLECTION,
    "Constructor.newInstance": SecuritySink.UNSAFE_REFLECTION,
    "Method.invoke": SecuritySink.UNSAFE_REFLECTION,
    "Field.get": SecuritySink.UNSAFE_REFLECTION,
    "Field.set": SecuritySink.UNSAFE_REFLECTION,
    "ClassLoader.loadClass": SecuritySink.UNSAFE_REFLECTION,
    # JavaScript
    "Reflect.construct": SecuritySink.UNSAFE_REFLECTION,
    "Reflect.get": SecuritySink.UNSAFE_REFLECTION,
    "Reflect.set": SecuritySink.UNSAFE_REFLECTION,
    "Object.getOwnPropertyDescriptor": SecuritySink.UNSAFE_REFLECTION,
    # ==========================================================================
    # [20251219_FEATURE] v3.0.4 - Expression Language Injection (CWE-917)
    # ==========================================================================
    # Spring SpEL
    "SpelExpressionParser.parseExpression": SecuritySink.EL_INJECTION,
    "ExpressionParser.parseExpression": SecuritySink.EL_INJECTION,
    "Expression.getValue": SecuritySink.EL_INJECTION,
    "StandardEvaluationContext": SecuritySink.EL_INJECTION,
    "@Value": SecuritySink.EL_INJECTION,  # Spring annotation with SpEL
    "#{": SecuritySink.EL_INJECTION,  # SpEL expression prefix
    # OGNL (Struts, etc.)
    "Ognl.getValue": SecuritySink.EL_INJECTION,
    "Ognl.setValue": SecuritySink.EL_INJECTION,
    "OgnlRuntime.getMethodValue": SecuritySink.EL_INJECTION,
    "ActionContext.getContext": SecuritySink.EL_INJECTION,
    # MVEL
    "MVEL.eval": SecuritySink.EL_INJECTION,
    "MVEL.executeExpression": SecuritySink.EL_INJECTION,
    "MVEL.compileExpression": SecuritySink.EL_INJECTION,
    # JSP EL
    "${": SecuritySink.EL_INJECTION,  # JSP EL prefix (when user-controlled)
    "ExpressionFactory.createValueExpression": SecuritySink.EL_INJECTION,
    # ==========================================================================
    # [20251219_FEATURE] v3.0.4 - GraphQL Injection (CWE-89 variant)
    # ==========================================================================
    # Python
    "graphene.ObjectType": SecuritySink.GRAPHQL_INJECTION,
    "graphql.graphql_sync": SecuritySink.GRAPHQL_INJECTION,
    "graphql.execute": SecuritySink.GRAPHQL_INJECTION,
    "ariadne.graphql_sync": SecuritySink.GRAPHQL_INJECTION,
    "strawberry.Schema.execute": SecuritySink.GRAPHQL_INJECTION,
    # JavaScript
    "graphql.graphql": SecuritySink.GRAPHQL_INJECTION,
    "apollo-server.ApolloServer": SecuritySink.GRAPHQL_INJECTION,
    "express-graphql.graphqlHTTP": SecuritySink.GRAPHQL_INJECTION,
    "makeExecutableSchema": SecuritySink.GRAPHQL_INJECTION,
    # Java
    "GraphQL.execute": SecuritySink.GRAPHQL_INJECTION,
    "ExecutionInput.newExecutionInput": SecuritySink.GRAPHQL_INJECTION,
    # ==========================================================================
    # [20251219_FEATURE] v3.0.4 - CORS Misconfiguration (CWE-942)
    # ==========================================================================
    # Python
    "flask_cors.CORS": SecuritySink.CORS_MISCONFIGURATION,
    "response.headers['Access-Control-Allow-Origin']": SecuritySink.CORS_MISCONFIGURATION,
    "django-cors-headers": SecuritySink.CORS_MISCONFIGURATION,
    "CORSMiddleware": SecuritySink.CORS_MISCONFIGURATION,
    # JavaScript
    "cors(": SecuritySink.CORS_MISCONFIGURATION,  # Express cors middleware
    "res.setHeader('Access-Control-Allow-Origin'": SecuritySink.CORS_MISCONFIGURATION,
    "Access-Control-Allow-Origin": SecuritySink.CORS_MISCONFIGURATION,
    # Java
    "@CrossOrigin": SecuritySink.CORS_MISCONFIGURATION,
    "CorsConfiguration.setAllowedOrigins": SecuritySink.CORS_MISCONFIGURATION,
    "CorsRegistry.addMapping": SecuritySink.CORS_MISCONFIGURATION,
    # ==========================================================================
    # [20251219_FEATURE] v3.0.4 - JWT Weakness (CWE-347)
    # ==========================================================================
    # Python
    "jwt.decode": SecuritySink.JWT_WEAKNESS,
    "jwt.encode": SecuritySink.JWT_WEAKNESS,
    "PyJWT.decode": SecuritySink.JWT_WEAKNESS,
    "jose.jwt.decode": SecuritySink.JWT_WEAKNESS,
    "python-jose.jwt": SecuritySink.JWT_WEAKNESS,
    # JavaScript
    "jsonwebtoken.verify": SecuritySink.JWT_WEAKNESS,
    "jsonwebtoken.sign": SecuritySink.JWT_WEAKNESS,
    "jwt.verify": SecuritySink.JWT_WEAKNESS,
    "jwt.sign": SecuritySink.JWT_WEAKNESS,
    "jose.jwtVerify": SecuritySink.JWT_WEAKNESS,
    "jose.SignJWT": SecuritySink.JWT_WEAKNESS,
    # Java
    "Jwts.parserBuilder": SecuritySink.JWT_WEAKNESS,
    "JwtParser.parseClaimsJws": SecuritySink.JWT_WEAKNESS,
    "JWT.decode": SecuritySink.JWT_WEAKNESS,  # auth0 java-jwt
    "JWT.require": SecuritySink.JWT_WEAKNESS,
    # ==========================================================================
    # [20251219_FEATURE] v3.0.4 - HTML Injection (CWE-80)
    # ==========================================================================
    # Python
    "markupsafe.Markup": SecuritySink.HTML_INJECTION,
    "flask.Markup": SecuritySink.HTML_INJECTION,
    "django.utils.safestring.mark_safe": SecuritySink.HTML_INJECTION,
    "mark_safe": SecuritySink.HTML_INJECTION,
    "format_html": SecuritySink.HTML_INJECTION,  # Django - can be misused
    # JavaScript (already have innerHTML for DOM_XSS, this is for server-side)
    "escape-html": SecuritySink.HTML_INJECTION,  # If bypassed
    "html-entities": SecuritySink.HTML_INJECTION,
    # Java
    "HtmlUtils.htmlEscape": SecuritySink.HTML_INJECTION,  # If bypassed
    "StringEscapeUtils.escapeHtml4": SecuritySink.HTML_INJECTION,
    # ==========================================================================
    # [20251229_FEATURE] v3.0.4 - Unvalidated Input in HTTP Response (CWE-20)
    # Type System Evaporation: tainted data returned without enum/type validation
    "jsonify": SecuritySink.UNVALIDATED_OUTPUT,
    "flask.jsonify": SecuritySink.UNVALIDATED_OUTPUT,
    "json.dumps": SecuritySink.UNVALIDATED_OUTPUT,
    "JSONResponse": SecuritySink.UNVALIDATED_OUTPUT,  # FastAPI
    "fastapi.responses.JSONResponse": SecuritySink.UNVALIDATED_OUTPUT,
    "starlette.responses.JSONResponse": SecuritySink.UNVALIDATED_OUTPUT,
    "Response.json": SecuritySink.UNVALIDATED_OUTPUT,  # Django REST Framework
    "rest_framework.response.Response": SecuritySink.UNVALIDATED_OUTPUT,
}

# =============================================================================
# [20251216_FEATURE] v2.2.0 - SSR (Server-Side Rendering) Security Sinks
# =============================================================================
# These patterns detect vulnerabilities in modern web frameworks with server-side
# rendering (Next.js, Remix, Nuxt, etc.)
SSR_SINK_PATTERNS: dict[str, SecuritySink] = {
    # Next.js - Pages Router
    "getServerSideProps": SecuritySink.SSTI,
    "getStaticProps": SecuritySink.SSTI,
    "getInitialProps": SecuritySink.SSTI,
    "dangerouslySetInnerHTML": SecuritySink.DOM_XSS,
    # Next.js - App Router (React Server Components)
    "generateMetadata": SecuritySink.SSTI,
    "generateStaticParams": SecuritySink.SSTI,
    # Next.js - Server Actions
    "revalidatePath": SecuritySink.FILE_PATH,
    "revalidateTag": SecuritySink.SSTI,
    "cookies().set": SecuritySink.HEADER,
    "cookies().delete": SecuritySink.HEADER,
    "headers().set": SecuritySink.HEADER,
    # Remix
    "loader": SecuritySink.SSTI,
    "action": SecuritySink.SSTI,
    "headers": SecuritySink.HEADER,
    "json": SecuritySink.HTML_OUTPUT,
    "redirect": SecuritySink.REDIRECT,
    # Nuxt 3
    "useAsyncData": SecuritySink.SSTI,
    "useFetch": SecuritySink.SSRF,
    "defineEventHandler": SecuritySink.SSTI,
    "setResponseHeader": SecuritySink.HEADER,
    "H3Event.node.res.setHeader": SecuritySink.HEADER,
    # SvelteKit
    "load": SecuritySink.SSTI,
    "+page.server.ts": SecuritySink.SSTI,
    "+layout.server.ts": SecuritySink.SSTI,
    "setHeaders": SecuritySink.HEADER,
    # Astro
    "Astro.props": SecuritySink.SSTI,
    "set:html": SecuritySink.DOM_XSS,
}

# Hardcoded Secret Patterns (v1.3.0, enhanced v2.0.0)
# These are regex patterns for detecting hardcoded secrets in string literals
HARDCODED_SECRET_PATTERNS: dict[str, str] = {
    # AWS (enhanced patterns)
    "aws_access_key": r"(?i)AKIA[A-Z0-9]{16}",
    "aws_secret_key": r"(?i)aws[_-]?secret[_-]?access[_-]?key\s*[=:]\s*['\"][A-Za-z0-9/+=]{40}['\"]",
    "aws_session_token": r"(?i)aws[_-]?session[_-]?token\s*[=:]\s*['\"][A-Za-z0-9/+=]{100,}['\"]",
    # GitHub
    "github_token": r"ghp_[a-zA-Z0-9]{36}",
    "github_oauth": r"gho_[a-zA-Z0-9]{36}",
    "github_app": r"ghu_[a-zA-Z0-9]{36}",
    "github_fine_grained": r"github_pat_[a-zA-Z0-9]{22}_[a-zA-Z0-9]{59}",
    # GitLab
    "gitlab_token": r"glpat-[a-zA-Z0-9\-]{20,}",
    "gitlab_runner": r"GR1348941[a-zA-Z0-9\-_]{20,}",
    # [20251214_FEATURE] v2.0.0 - Stripe patterns (enhanced per evaluation report)
    "stripe_live": r"sk_live_[a-zA-Z0-9]{24,}",
    "stripe_test": r"sk_test_[a-zA-Z0-9]{24,}",
    "stripe_restricted": r"rk_live_[a-zA-Z0-9]{24,}",
    "stripe_pk_live": r"pk_live_[a-zA-Z0-9]{24,}",
    "stripe_pk_test": r"pk_test_[a-zA-Z0-9]{24,}",
    # Slack
    "slack_token": r"xox[baprs]-[a-zA-Z0-9\-]{10,}",
    "slack_webhook": r"https://hooks\.slack\.com/services/T[A-Z0-9]+/B[A-Z0-9]+/[a-zA-Z0-9]+",
    # Google/Firebase
    "google_api": r"AIza[0-9A-Za-z\-_]{35}",
    "firebase": r"AAAA[A-Za-z0-9_-]{7}:[A-Za-z0-9_-]{140}",
    "google_oauth": r"[0-9]+-[a-z0-9_]{32}\.apps\.googleusercontent\.com",
    # Twilio
    "twilio_sid": r"AC[a-z0-9]{32}",
    "twilio_token": r"SK[a-z0-9]{32}",
    # SendGrid/Mailgun
    "sendgrid": r"SG\.[a-zA-Z0-9\-_]{22}\.[a-zA-Z0-9\-_]{43}",
    "mailgun": r"key-[a-zA-Z0-9]{32}",
    # Square
    "square_token": r"sq0atp-[a-zA-Z0-9\-_]{22}",
    "square_oauth": r"sq0csp-[a-zA-Z0-9\-_]{43}",
    # Private Keys
    "private_key_rsa": r"-----BEGIN\s+RSA\s+PRIVATE\s+KEY-----",
    "private_key_ec": r"-----BEGIN\s+EC\s+PRIVATE\s+KEY-----",
    "private_key_dsa": r"-----BEGIN\s+DSA\s+PRIVATE\s+KEY-----",
    "private_key_openssh": r"-----BEGIN\s+OPENSSH\s+PRIVATE\s+KEY-----",
    "private_key_generic": r"-----BEGIN\s+PRIVATE\s+KEY-----",
    "private_key_encrypted": r"-----BEGIN\s+ENCRYPTED\s+PRIVATE\s+KEY-----",
    # [20251214_FEATURE] v2.0.0 - JWT tokens (per evaluation report request)
    "jwt_token": r"eyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}",
    # [20251214_FEATURE] v2.0.0 - Additional cloud providers
    "azure_storage": r"DefaultEndpointsProtocol=https;AccountName=[a-z0-9]+;AccountKey=[A-Za-z0-9+/=]{88}",
    "azure_connection": r"(?i)azure[_-]?connection[_-]?string\s*[=:]\s*['\"][^'\"]{50,}['\"]",
    "heroku_api": r"(?i)heroku[_-]?api[_-]?key\s*[=:]\s*['\"][a-f0-9\-]{36}['\"]",
    "digitalocean": r"(?i)do[_-]?api[_-]?token\s*[=:]\s*['\"][a-f0-9]{64}['\"]",
    # [20251214_FEATURE] v2.0.0 - Database connection strings
    "postgres_url": r"postgres(?:ql)?://[^:]+:[^@]+@[^/]+/[^\s'\"]+",
    "mysql_url": r"mysql://[^:]+:[^@]+@[^/]+/[^\s'\"]+",
    "mongodb_url": r"mongodb(?:\+srv)?://[^:]+:[^@]+@[^\s'\"]+",
    "redis_url": r"redis://[^:]*:[^@]+@[^/]+(?:/[0-9]+)?",
    # [20251214_FEATURE] v2.0.0 - NPM/PyPI tokens
    "npm_token": r"npm_[a-zA-Z0-9]{36}",
    "pypi_token": r"pypi-[a-zA-Z0-9]{64,}",
    # Generic patterns (keep at end, more permissive)
    "generic_api_key": r"(?i)(api[_-]?key|apikey)\s*[=:]\s*['\"][a-zA-Z0-9]{20,}['\"]",
    "generic_secret": r"(?i)(secret|password|passwd|pwd|token)\s*[=:]\s*['\"][a-zA-Z0-9!@#$%^&*()_+\-=\[\]{}|;:,.<>?]{8,}['\"]",
    "generic_bearer": r"(?i)bearer\s+[a-zA-Z0-9\-_\.]{20,}",
}

# =============================================================================
# [20251216_FEATURE] v2.2.0 - SSR Framework Detection Patterns
# =============================================================================
# Framework detection based on import statements
SSR_FRAMEWORK_IMPORTS: dict[str, str] = {
    # Next.js
    "next/server": "nextjs",
    "next/navigation": "nextjs",
    "next/headers": "nextjs",
    "next/cache": "nextjs",
    "next": "nextjs",
    # Remix
    "@remix-run/node": "remix",
    "@remix-run/react": "remix",
    "@remix-run/server-runtime": "remix",
    # Nuxt
    "nuxt": "nuxt",
    "nuxt/app": "nuxt",
    "#app": "nuxt",  # Nuxt 3 auto-imports
    "h3": "nuxt",  # Nuxt 3 uses h3 for server
    # SvelteKit
    "@sveltejs/kit": "sveltekit",
    "$app/environment": "sveltekit",
    "$app/stores": "sveltekit",
    # Astro
    "astro": "astro",
    "astro:content": "astro",
}

# [20251214_FEATURE] v2.0.0 - Variable name patterns for detecting secret assignments
# These match variable names that typically hold secrets
SECRET_VARIABLE_PATTERNS: dict[str, str] = {
    "password_var": r"(?i)^(password|passwd|pwd|pass|admin_password|default_password|db_password|user_password|root_password)$",
    "secret_var": r"(?i)^(secret|secret_key|jwt_secret|app_secret|session_secret|encryption_key|private_key|signing_key)$",
    "api_key_var": r"(?i)^(api_key|apikey|api_secret|access_key|access_token|auth_token|bearer_token)$",
    "connection_string": r"(?i)^(connection_string|database_url|db_url|redis_url|mongo_uri)$",
    "credentials": r"(?i)^(credentials|creds|auth|authentication)$",
}
# Sanitizer function patterns
SANITIZER_PATTERNS: dict[str, str] = {
    "html.escape": "html.escape",
    "markupsafe.escape": "markupsafe.escape",
    "bleach.clean": "bleach.clean",
    "cgi.escape": "cgi.escape",
    "shlex.quote": "shlex.quote",
    "os.path.basename": "os.path.basename",
    "werkzeug.utils.secure_filename": "secure_filename",
}


# =============================================================================
# [20251216_FEATURE] v2.2.0 - SSR Framework Detection and Vulnerability Analysis
# =============================================================================


def detect_ssr_framework(tree: ast.AST) -> str | None:
    """
    [20251216_FEATURE] v2.2.0 - Auto-detect SSR framework from imports.

    Analyzes import statements to determine which SSR framework is being used.

    Args:
        tree: AST tree of the code

    Returns:
        Framework name ("nextjs", "remix", "nuxt", "sveltekit", "astro") or None
    """
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in SSR_FRAMEWORK_IMPORTS:
                    return SSR_FRAMEWORK_IMPORTS[alias.name]
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.module in SSR_FRAMEWORK_IMPORTS:
                return SSR_FRAMEWORK_IMPORTS[node.module]
    return None


def is_server_action(node: ast.AST) -> bool:
    """
    [20251216_FEATURE] v2.2.0 - Check if node is a Next.js Server Action.

    Server Actions are marked with 'use server' directive at the top of a function.

    Args:
        node: AST node to check

    Returns:
        True if node is a server action
    """
    if not isinstance(node, ast.FunctionDef):
        return False

    # Check for 'use server' directive in function docstring or first statement
    if node.body:
        first_stmt = node.body[0]
        if isinstance(first_stmt, ast.Expr) and isinstance(first_stmt.value, ast.Constant):
            if isinstance(first_stmt.value.value, str):
                # Check for 'use server' or "use server" (without quotes)
                content = first_stmt.value.value.strip()
                if content == "use server":
                    return True

    return False


def has_input_validation(node: ast.AST) -> bool:
    """
    [20251216_BUGFIX] Accepts both FunctionDef and Lambda nodes for input validation detection.

    Checks for common input validation patterns in function or lambda:
    - Type checking (isinstance, type)
    - Schema validation (zod, joi, yup)
    - Manual validation (if checks on inputs)

    Args:
        node: FunctionDef or Lambda node to check

    Returns:
        True if validation is present
    """
    if isinstance(node, ast.FunctionDef):
        for stmt in ast.walk(node):
            # Check for isinstance or type checks
            if isinstance(stmt, ast.Call):
                if isinstance(stmt.func, ast.Name):
                    if stmt.func.id in {
                        "isinstance",
                        "type",
                        "int",
                        "float",
                        "bool",
                        "str",
                    }:
                        return True
                # Check for schema validators
                if isinstance(stmt.func, ast.Attribute):
                    if stmt.func.attr in {"parse", "validate", "safeParse"}:
                        return True

            # Check for if statements that validate parameters
            if isinstance(stmt, ast.If):
                # Look for parameter checks in the condition
                if isinstance(stmt.test, ast.Compare):
                    return True
        return False
    elif isinstance(node, ast.Lambda):
        # For lambdas, only check the body expression for type checks
        expr = node.body
        # Check for isinstance or type checks in the lambda body
        if isinstance(expr, ast.Call):
            if isinstance(expr.func, ast.Name):
                if expr.func.id in {
                    "isinstance",
                    "type",
                    "int",
                    "float",
                    "bool",
                    "str",
                }:
                    return True
            if isinstance(expr.func, ast.Attribute):
                if expr.func.attr in {"parse", "validate", "safeParse"}:
                    return True
        # Check for comparison in lambda body
        if isinstance(expr, ast.Compare):
            return True
        return False
    else:
        return False


def is_dangerous_html(node: ast.AST) -> bool:
    """
    [20251216_FEATURE] v2.2.0 - Check if node uses dangerouslySetInnerHTML.

    Args:
        node: AST node to check

    Returns:
        True if node uses dangerouslySetInnerHTML
    """
    # [20240613_SECURITY] Removed redundant ast.Name check for dangerouslySetInnerHTML (see CodeQL warning)
    if isinstance(node, ast.Call):
        # Check for dangerouslySetInnerHTML in React/JSX context
        if isinstance(node.func, ast.Attribute):
            if node.func.attr == "dangerouslySetInnerHTML":
                return True

    return False


def detect_ssr_vulnerabilities(
    tree: ast.AST,
    framework: str | None = None,
    taint_tracker: TaintTracker | None = None,
) -> list[Vulnerability]:
    """
    [20251216_FEATURE] v2.2.0 - Detect SSR-specific vulnerabilities.

    Analyzes code for server-side rendering vulnerabilities specific to
    modern web frameworks like Next.js, Remix, Nuxt, etc.

    Args:
        tree: AST tree to analyze
        framework: Framework name or None for auto-detection
        taint_tracker: Optional TaintTracker instance for taint analysis

    Returns:
        List of detected vulnerabilities
    """
    vulnerabilities: list[Vulnerability] = []

    # Auto-detect framework if not provided
    if framework is None:
        framework = detect_ssr_framework(tree)

    if framework is None:
        # No SSR framework detected, skip SSR-specific checks
        return vulnerabilities

    # Track if we're using an external taint tracker
    internal_tracker = taint_tracker is None
    if internal_tracker:
        taint_tracker = TaintTracker()

    # Walk the AST looking for SSR vulnerabilities
    for node in ast.walk(tree):
        # Check for unvalidated Server Actions (Next.js)
        if framework == "nextjs" and isinstance(node, ast.FunctionDef):
            if is_server_action(node) and not has_input_validation(node):
                vulnerabilities.append(
                    Vulnerability(
                        sink_type=SecuritySink.SSTI,
                        taint_source=TaintSource.USER_INPUT,
                        taint_path=["Server Action", node.name],
                        sink_location=((node.lineno, node.col_offset) if hasattr(node, "lineno") else None),
                        source_location=((node.lineno, node.col_offset) if hasattr(node, "lineno") else None),
                    )
                )

        # Check for dangerouslySetInnerHTML with tainted data
        if isinstance(node, ast.Call):
            if is_dangerous_html(node):
                # Check if any argument is tainted
                for arg in node.args:
                    if isinstance(arg, ast.Name) and taint_tracker:
                        if taint_tracker.is_tainted(arg.id):
                            vulnerabilities.append(
                                Vulnerability(
                                    sink_type=SecuritySink.DOM_XSS,
                                    taint_source=TaintSource.USER_INPUT,
                                    taint_path=["dangerouslySetInnerHTML", arg.id],
                                    sink_location=((node.lineno, node.col_offset) if hasattr(node, "lineno") else None),
                                )
                            )

        # Check for unvalidated Remix loaders/actions
        if framework == "remix" and isinstance(node, ast.FunctionDef):
            if node.name in {"loader", "action"} and not has_input_validation(node):
                vulnerabilities.append(
                    Vulnerability(
                        sink_type=SecuritySink.SSTI,
                        taint_source=TaintSource.USER_INPUT,
                        taint_path=["Remix", node.name],
                        sink_location=((node.lineno, node.col_offset) if hasattr(node, "lineno") else None),
                    )
                )

        # Check for unvalidated Nuxt server handlers
        if framework == "nuxt" and isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                if node.func.id == "defineEventHandler":
                    # Check if handler validates input
                    if node.args and isinstance(node.args[0], ast.Lambda):
                        if not has_input_validation(node.args[0]):
                            vulnerabilities.append(
                                Vulnerability(
                                    sink_type=SecuritySink.SSTI,
                                    taint_source=TaintSource.USER_INPUT,
                                    taint_path=["Nuxt", "defineEventHandler"],
                                    sink_location=((node.lineno, node.col_offset) if hasattr(node, "lineno") else None),
                                )
                            )

    return vulnerabilities
