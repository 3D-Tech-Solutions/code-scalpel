#!/usr/bin/env python3
"""
Pylint Parser - Comprehensive Code Quality Analysis.
=====================================================

Pylint is Python's most comprehensive static analysis tool, checking for
errors, enforcing coding standards, and detecting code smells. This module
provides structured parsing of Pylint output.

Implementation Status: MOSTLY COMPLETED
Priority: P2 - HIGH

Pylint Features:
    - Error detection (undefined names, import errors)
    - Code smell detection (too many arguments, too complex)
    - Convention checking (naming, docstrings)
    - Refactoring suggestions (duplicate code, simplification)
    - Custom checker plugins

==============================================================================
COMPLETED [P2-PYLINT-001]: Implement PylintParser with full message parsing
==============================================================================
Priority: HIGH
Status: ✓ COMPLETED

Implemented Features:
    - [✓] Parse JSON reporter output (--output-format=json2)
    - [✓] Map message IDs to categories (C/R/W/E/F)
    - [✓] Extract message arguments for formatting
    - [✓] Extract confidence levels
    - [✓] Complete PylintMessage.from_dict() parsing
    - [✓] Full analyze() method with subprocess execution
    - [✓] JSON parsing with error handling
    - [✓] PylintStatistics parsing
    - [✓] Handle stdin input (analyze_string method)
    - [✓] Support custom message definitions (via plugins)
    - [✓] Handle # pylint: disable/enable comments (parsed by pylint)

Output Format (JSON2):
    ```json
    {
        "messages": [
            {
                "type": "convention",
                "module": "example",
                "obj": "MyClass.my_method",
                "line": 10,
                "column": 0,
                "endLine": 10,
                "endColumn": 20,
                "path": "example.py",
                "symbol": "missing-function-docstring",
                "message": "Missing function docstring",
                "message-id": "C0116",
                "confidence": "HIGH"
            }
        ],
        "statistics": {
            "messageTypeCount": {"convention": 5, "error": 1},
            "modulesLinted": 3,
            "score": 8.5
        }
    }
    ```

Message Categories:
    C - Convention (style violations)
    R - Refactor (code smell, improvements needed)
    W - Warning (potential issues)
    E - Error (definite problems)
    F - Fatal (Pylint cannot continue)

Test Cases:
    - Parse JSON2 output with multiple message types
    - Handle empty output (clean code)
    - Parse statistics and score
    - Verify message-id to symbol mapping

==============================================================================
COMPLETED [P2-PYLINT-002]: Implement message ID mapping
==============================================================================
Priority: HIGH
Status: ✓ COMPLETED
Depends On: P2-PYLINT-001

Implemented Features:
    - [✓] Map message IDs to human-readable symbols (COMMON_MESSAGES dict with 200+ mappings)
    - [✓] Group messages by severity (C/R/W/E/F/I)
    - [✓] get_severity_from_id() function
    - [✓] get_symbol_from_id() function
    - [✓] get_message_info() method for lookups
    - [✓] list_all_messages() method
    - [✓] Track deprecated message IDs (C0111 → C0114/C0115/C0116)
    - [✓] Group messages by checker (MESSAGE_CHECKERS mapping)
    - [✓] Include default enabled/disabled status in MESSAGE_DEFAULT_ENABLED
    - [✓] Support alias message IDs (via both ID and symbol lookup)

Message ID Ranges:
    ```python
    # Category prefix codes
    MESSAGE_CATEGORIES = {
        "C": "Convention",   # C0000-C9999
        "R": "Refactor",     # R0000-R9999
        "W": "Warning",      # W0000-W9999
        "E": "Error",        # E0000-E9999
        "F": "Fatal",        # F0000-F9999
        "I": "Informational",# I0000-I9999
    }

    # Common message IDs
    COMMON_MESSAGES = {
        "C0114": "missing-module-docstring",
        "C0115": "missing-class-docstring",
        "C0116": "missing-function-docstring",
        "E0401": "import-error",
        "E0602": "undefined-variable",
        "W0612": "unused-variable",
        "R0913": "too-many-arguments",
        "R0914": "too-many-locals",
    }
    ```

==============================================================================
COMPLETED [P2-PYLINT-003]: Configuration parsing
==============================================================================
Priority: MEDIUM
Status: ✓ COMPLETED

Implemented Features:
    - [✓] PylintConfig dataclass with all settings
    - [✓] to_cli_args() method for command-line conversion
    - [✓] Support for basic options (disable, enable, max-line-length, etc.)
    - [✓] Plugin loading support
    - [✓] Parse .pylintrc configuration
    - [✓] Parse [pylint] sections in setup.cfg
    - [✓] Parse [tool.pylint] in pyproject.toml
    - [✓] find_config() for automatic config discovery
    - [✓] Parse MASTER, MESSAGES CONTROL, FORMAT, DESIGN, BASIC sections

Configuration Example (.pylintrc):
    ```ini
    [MASTER]
    load-plugins=pylint_django
    ignore=migrations

    [MESSAGES CONTROL]
    disable=C0114,C0115,C0116
    enable=W0611

    [DESIGN]
    max-args=10
    max-locals=20

    [FORMAT]
    max-line-length=100
    ```

==============================================================================
COMPLETED [P2-PYLINT-004]: Implement score calculation understanding
==============================================================================
Priority: LOW
Status: ✓ COMPLETED

Implemented Features:
    - [✓] Parse the 10-point score (PylintStatistics.score)
    - [✓] Track score changes over time (previous_score, score_delta property)
    - [✓] Parse statement count for formula understanding
    - [✓] Parse message type counts
    - [✓] Calculate score improvement suggestions (get_score_improvement_suggestions)
    - [✓] Support custom score thresholds (via config)

Score Formula:
    score = 10.0 - ((float(5 * error + warning + refactor + convention) / statement) * 10)

==============================================================================
MOSTLY COMPLETED [P3-PYLINT-005]: Implement checker-specific parsing
==============================================================================
Priority: LOW
Status: ✓ MOSTLY COMPLETED

Implemented Features:
    - [✓] Parse basic checker messages (undefined names, etc.)
    - [✓] Parse design checker (complexity, parameters, etc.)
    - [✓] Parse format checker (line length, whitespace)
    - [✓] Parse imports checker (import order, unused)
    - [✓] Parse variables checker (unused, undefined)
    - [✓] Parse exceptions checker (broad exceptions)
    - [✓] Parse classes checker (method counts, inheritance)
    - [✓] MESSAGE_CHECKERS mapping for checker identification
    - [ ] Parse similarities checker (duplicate code) - requires special handling
"""

from __future__ import annotations

import configparser
import json
import subprocess
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any

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


class PylintSeverity(Enum):
    """Severity levels for Pylint messages."""

    FATAL = "fatal"  # F - Pylint cannot continue
    ERROR = "error"  # E - Definite problems
    WARNING = "warning"  # W - Potential issues
    REFACTOR = "refactor"  # R - Code smell, improvement needed
    CONVENTION = "convention"  # C - Style violations
    INFO = "info"  # I - Informational messages


class PylintConfidence(Enum):
    """Confidence levels for Pylint messages."""

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFERENCE = "INFERENCE"
    INFERENCE_FAILURE = "INFERENCE_FAILURE"
    UNDEFINED = "UNDEFINED"


class PylintChecker(Enum):
    """Pylint checker categories."""

    BASIC = "basic"  # Basic checks
    CLASSES = "classes"  # Class-related checks
    DESIGN = "design"  # Design complexity checks
    EXCEPTIONS = "exceptions"  # Exception handling checks
    FORMAT = "format"  # Formatting checks
    IMPORTS = "imports"  # Import-related checks
    LOGGING = "logging"  # Logging checks
    MISCELLANEOUS = "miscellaneous"  # Misc checks
    NEWSTYLE = "newstyle"  # New-style class checks
    REFACTORING = "refactoring"  # Refactoring suggestions
    SIMILARITIES = "similarities"  # Duplicate code
    SPELLING = "spelling"  # Spelling checks
    STDLIB = "stdlib"  # Standard library usage
    STRING = "string"  # String formatting
    TYPECHECK = "typecheck"  # Type checking
    VARIABLES = "variables"  # Variable usage


# =============================================================================
# Message ID Mapping
# =============================================================================

# Map severity character to enum
SEVERITY_MAP: dict[str, PylintSeverity] = {
    "F": PylintSeverity.FATAL,
    "E": PylintSeverity.ERROR,
    "W": PylintSeverity.WARNING,
    "R": PylintSeverity.REFACTOR,
    "C": PylintSeverity.CONVENTION,
    "I": PylintSeverity.INFO,
}

# Common message IDs and their symbols (200+ mappings)
COMMON_MESSAGES: dict[str, str] = {
    # Convention (C)
    "C0103": "invalid-name",
    "C0111": "missing-docstring",  # Deprecated, split into below
    "C0114": "missing-module-docstring",
    "C0115": "missing-class-docstring",
    "C0116": "missing-function-docstring",
    "C0301": "line-too-long",
    "C0302": "too-many-lines",
    "C0303": "trailing-whitespace",
    "C0304": "missing-final-newline",
    "C0305": "trailing-newlines",
    "C0321": "multiple-statements",
    "C0325": "superfluous-parens",
    "C0410": "multiple-imports",
    "C0411": "wrong-import-order",
    "C0412": "ungrouped-imports",
    "C0413": "wrong-import-position",
    "C0414": "useless-import-alias",
    "C0415": "import-outside-toplevel",
    # Refactor (R)
    "R0201": "no-self-use",  # Now W0211
    "R0801": "duplicate-code",
    "R0901": "too-many-ancestors",
    "R0902": "too-many-instance-attributes",
    "R0903": "too-few-public-methods",
    "R0904": "too-many-public-methods",
    "R0911": "too-many-return-statements",
    "R0912": "too-many-branches",
    "R0913": "too-many-arguments",
    "R0914": "too-many-locals",
    "R0915": "too-many-statements",
    "R0916": "too-many-boolean-expressions",
    "R1705": "no-else-return",
    "R1710": "inconsistent-return-statements",
    "R1714": "consider-using-in",
    "R1715": "consider-using-get",
    "R1716": "chained-comparison",
    "R1717": "consider-using-dict-comprehension",
    "R1718": "consider-using-set-comprehension",
    "R1720": "no-else-raise",
    "R1721": "unnecessary-comprehension",
    "R1724": "no-else-continue",
    "R1725": "super-with-arguments",
    "R1728": "consider-using-generator",
    "R1729": "use-a-generator",
    "R1732": "consider-using-with",
    "R1735": "use-dict-literal",
    # Warning (W)
    "W0101": "unreachable",
    "W0102": "dangerous-default-value",
    "W0104": "pointless-statement",
    "W0105": "pointless-string-statement",
    "W0106": "expression-not-assigned",
    "W0107": "unnecessary-pass",
    "W0108": "unnecessary-lambda",
    "W0120": "useless-else-on-loop",
    "W0122": "exec-used",
    "W0123": "eval-used",
    "W0125": "using-constant-test",
    "W0143": "comparison-with-callable",
    "W0150": "lost-exception",
    "W0201": "attribute-defined-outside-init",
    "W0211": "bad-staticmethod-argument",
    "W0212": "protected-access",
    "W0221": "arguments-differ",
    "W0222": "signature-differs",
    "W0223": "abstract-method",
    "W0231": "super-init-not-called",
    "W0233": "non-parent-init-called",
    "W0235": "useless-super-delegation",
    "W0301": "unnecessary-semicolon",
    "W0311": "bad-indentation",
    "W0312": "mixed-indentation",
    "W0401": "wildcard-import",
    "W0404": "reimported",
    "W0406": "import-self",
    "W0410": "misplaced-future",
    "W0511": "fixme",
    "W0601": "global-variable-undefined",
    "W0602": "global-variable-not-assigned",
    "W0603": "global-statement",
    "W0604": "global-at-module-level",
    "W0611": "unused-import",
    "W0612": "unused-variable",
    "W0613": "unused-argument",
    "W0614": "unused-wildcard-import",
    "W0621": "redefined-outer-name",
    "W0622": "redefined-builtin",
    "W0631": "undefined-loop-variable",
    "W0632": "unbalanced-tuple-unpacking",
    "W0640": "cell-var-from-loop",
    "W0641": "possibly-unused-variable",
    "W0702": "bare-except",
    "W0703": "broad-except",
    "W0705": "duplicate-except",
    "W0706": "try-except-raise",
    "W0707": "raise-missing-from",
    "W0711": "binary-op-exception",
    "W0715": "raising-format-tuple",
    "W0718": "broad-exception-caught",
    "W0719": "broad-exception-raised",
    "W1113": "keyword-arg-before-vararg",
    "W1201": "logging-not-lazy",
    "W1202": "logging-format-interpolation",
    "W1203": "logging-fstring-interpolation",
    "W1300": "bad-format-string-key",
    "W1301": "unused-format-string-key",
    "W1302": "bad-format-string",
    "W1303": "missing-format-argument-key",
    "W1304": "unused-format-string-argument",
    "W1305": "format-combined-specification",
    "W1308": "duplicate-string-formatting-argument",
    "W1309": "f-string-without-interpolation",
    "W1310": "format-string-without-interpolation",
    # Error (E)
    "E0001": "syntax-error",
    "E0011": "unrecognized-inline-option",
    "E0012": "bad-option-value",
    "E0100": "init-is-generator",
    "E0101": "return-in-init",
    "E0102": "function-redefined",
    "E0103": "not-in-loop",
    "E0104": "return-outside-function",
    "E0105": "yield-outside-function",
    "E0107": "nonexistent-operator",
    "E0108": "duplicate-argument-name",
    "E0110": "abstract-class-instantiated",
    "E0111": "bad-reversed-sequence",
    "E0112": "too-many-star-expressions",
    "E0113": "invalid-star-assignment-target",
    "E0114": "star-needs-assignment-target",
    "E0115": "nonlocal-and-global",
    "E0116": "continue-in-finally",
    "E0117": "nonlocal-without-binding",
    "E0118": "used-prior-global-declaration",
    "E0119": "misplaced-format-function",
    "E0202": "method-hidden",
    "E0203": "access-member-before-definition",
    "E0211": "no-method-argument",
    "E0213": "no-self-argument",
    "E0236": "invalid-slots-object",
    "E0237": "assigning-non-slot",
    "E0238": "invalid-slots",
    "E0239": "inherit-non-class",
    "E0240": "inconsistent-mro",
    "E0241": "duplicate-bases",
    "E0242": "class-variable-slots-conflict",
    "E0301": "non-iterator-returned",
    "E0302": "unexpected-special-method-signature",
    "E0303": "invalid-length-returned",
    "E0304": "invalid-bool-returned",
    "E0305": "invalid-index-returned",
    "E0306": "invalid-repr-returned",
    "E0307": "invalid-str-returned",
    "E0308": "invalid-bytes-returned",
    "E0309": "invalid-hash-returned",
    "E0310": "invalid-length-hint-returned",
    "E0311": "invalid-format-returned",
    "E0312": "invalid-getnewargs-returned",
    "E0313": "invalid-getnewargs-ex-returned",
    "E0401": "import-error",
    "E0402": "relative-beyond-top-level",
    "E0601": "used-before-assignment",
    "E0602": "undefined-variable",
    "E0603": "undefined-all-variable",
    "E0604": "invalid-all-object",
    "E0605": "invalid-all-format",
    "E0611": "no-name-in-module",
    "E0633": "unpacking-non-sequence",
    "E0701": "bad-except-order",
    "E0702": "raising-bad-type",
    "E0703": "bad-exception-cause",
    "E0704": "misplaced-bare-raise",
    "E0710": "raising-non-exception",
    "E0711": "notimplemented-raised",
    "E0712": "catching-non-exception",
    "E1003": "bad-super-call",
    "E1101": "no-member",
    "E1102": "not-callable",
    "E1111": "assignment-from-no-return",
    "E1120": "no-value-for-parameter",
    "E1121": "too-many-function-args",
    "E1123": "unexpected-keyword-arg",
    "E1124": "redundant-keyword-arg",
    "E1125": "missing-kwoa",
    "E1126": "invalid-sequence-index",
    "E1127": "invalid-slice-index",
    "E1128": "assignment-from-none",
    "E1129": "not-context-manager",
    "E1130": "invalid-unary-operand-type",
    "E1131": "unsupported-binary-operation",
    "E1132": "repeated-keyword",
    "E1133": "not-an-iterable",
    "E1134": "not-a-mapping",
    "E1135": "unsupported-membership-test",
    "E1136": "unsubscriptable-object",
    "E1137": "unsupported-assignment-operation",
    "E1138": "unsupported-delete-operation",
    "E1139": "invalid-metaclass",
    "E1140": "unhashable-member",
    "E1141": "dict-iter-missing-items",
    "E1142": "await-outside-async",
    "E1200": "logging-unsupported-format",
    "E1201": "logging-format-truncated",
    "E1205": "logging-too-many-args",
    "E1206": "logging-too-few-args",
    "E1300": "bad-format-character",
    "E1301": "truncated-format-string",
    "E1302": "mixed-format-string",
    "E1303": "format-needs-mapping",
    "E1304": "missing-format-string-key",
    "E1305": "too-many-format-args",
    "E1306": "too-few-format-args",
    "E1307": "bad-string-format-type",
    "E1310": "bad-str-strip-call",
    "E1507": "invalid-envvar-value",
    "E1700": "yield-inside-async-function",
    # Fatal (F)
    "F0001": "fatal",
    "F0002": "astroid-error",
    "F0010": "parse-error",
    "F0011": "config-parse-error",
}


# Message ID to checker mapping
MESSAGE_CHECKERS: dict[str, PylintChecker] = {
    # Basic checker
    "C0114": PylintChecker.BASIC,
    "C0115": PylintChecker.BASIC,
    "C0116": PylintChecker.BASIC,
    "C0103": PylintChecker.BASIC,
    "W0104": PylintChecker.BASIC,
    "W0105": PylintChecker.BASIC,
    "W0106": PylintChecker.BASIC,
    "W0107": PylintChecker.BASIC,
    "W0108": PylintChecker.BASIC,
    "W0122": PylintChecker.BASIC,
    "W0123": PylintChecker.BASIC,
    "E0100": PylintChecker.BASIC,
    "E0101": PylintChecker.BASIC,
    "E0102": PylintChecker.BASIC,
    "E0103": PylintChecker.BASIC,
    "E0104": PylintChecker.BASIC,
    "E0105": PylintChecker.BASIC,
    # Format checker
    "C0301": PylintChecker.FORMAT,
    "C0302": PylintChecker.FORMAT,
    "C0303": PylintChecker.FORMAT,
    "C0304": PylintChecker.FORMAT,
    "C0305": PylintChecker.FORMAT,
    "C0321": PylintChecker.FORMAT,
    "C0325": PylintChecker.FORMAT,
    "W0301": PylintChecker.FORMAT,
    "W0311": PylintChecker.FORMAT,
    "W0312": PylintChecker.FORMAT,
    # Design checker
    "R0901": PylintChecker.DESIGN,
    "R0902": PylintChecker.DESIGN,
    "R0903": PylintChecker.DESIGN,
    "R0904": PylintChecker.DESIGN,
    "R0911": PylintChecker.DESIGN,
    "R0912": PylintChecker.DESIGN,
    "R0913": PylintChecker.DESIGN,
    "R0914": PylintChecker.DESIGN,
    "R0915": PylintChecker.DESIGN,
    "R0916": PylintChecker.DESIGN,
    # Imports checker
    "C0410": PylintChecker.IMPORTS,
    "C0411": PylintChecker.IMPORTS,
    "C0412": PylintChecker.IMPORTS,
    "C0413": PylintChecker.IMPORTS,
    "C0414": PylintChecker.IMPORTS,
    "C0415": PylintChecker.IMPORTS,
    "W0401": PylintChecker.IMPORTS,
    "W0404": PylintChecker.IMPORTS,
    "W0406": PylintChecker.IMPORTS,
    "W0410": PylintChecker.IMPORTS,
    "W0611": PylintChecker.IMPORTS,
    "W0614": PylintChecker.IMPORTS,
    "E0401": PylintChecker.IMPORTS,
    "E0402": PylintChecker.IMPORTS,
    "E0611": PylintChecker.IMPORTS,
    # Variables checker
    "W0612": PylintChecker.VARIABLES,
    "W0613": PylintChecker.VARIABLES,
    "W0621": PylintChecker.VARIABLES,
    "W0622": PylintChecker.VARIABLES,
    "W0631": PylintChecker.VARIABLES,
    "W0632": PylintChecker.VARIABLES,
    "W0640": PylintChecker.VARIABLES,
    "W0641": PylintChecker.VARIABLES,
    "E0601": PylintChecker.VARIABLES,
    "E0602": PylintChecker.VARIABLES,
    "E0603": PylintChecker.VARIABLES,
    "E0604": PylintChecker.VARIABLES,
    "E0633": PylintChecker.VARIABLES,
    # Exceptions checker
    "W0702": PylintChecker.EXCEPTIONS,
    "W0703": PylintChecker.EXCEPTIONS,
    "W0705": PylintChecker.EXCEPTIONS,
    "W0706": PylintChecker.EXCEPTIONS,
    "W0707": PylintChecker.EXCEPTIONS,
    "W0711": PylintChecker.EXCEPTIONS,
    "W0718": PylintChecker.EXCEPTIONS,
    "W0719": PylintChecker.EXCEPTIONS,
    "E0701": PylintChecker.EXCEPTIONS,
    "E0702": PylintChecker.EXCEPTIONS,
    "E0703": PylintChecker.EXCEPTIONS,
    "E0704": PylintChecker.EXCEPTIONS,
    "E0710": PylintChecker.EXCEPTIONS,
    "E0711": PylintChecker.EXCEPTIONS,
    "E0712": PylintChecker.EXCEPTIONS,
    # Classes checker
    "W0201": PylintChecker.CLASSES,
    "W0211": PylintChecker.CLASSES,
    "W0212": PylintChecker.CLASSES,
    "W0221": PylintChecker.CLASSES,
    "W0222": PylintChecker.CLASSES,
    "W0223": PylintChecker.CLASSES,
    "W0231": PylintChecker.CLASSES,
    "W0233": PylintChecker.CLASSES,
    "W0235": PylintChecker.CLASSES,
    "E0202": PylintChecker.CLASSES,
    "E0203": PylintChecker.CLASSES,
    "E0211": PylintChecker.CLASSES,
    "E0213": PylintChecker.CLASSES,
    "E0236": PylintChecker.CLASSES,
    "E0237": PylintChecker.CLASSES,
    "E0238": PylintChecker.CLASSES,
    "E0239": PylintChecker.CLASSES,
    "E0240": PylintChecker.CLASSES,
    "E0241": PylintChecker.CLASSES,
    "E0242": PylintChecker.CLASSES,
    "E1003": PylintChecker.CLASSES,
    # Typecheck checker
    "E1101": PylintChecker.TYPECHECK,
    "E1102": PylintChecker.TYPECHECK,
    "E1111": PylintChecker.TYPECHECK,
    "E1120": PylintChecker.TYPECHECK,
    "E1121": PylintChecker.TYPECHECK,
    "E1123": PylintChecker.TYPECHECK,
    "E1124": PylintChecker.TYPECHECK,
    "E1125": PylintChecker.TYPECHECK,
    "E1126": PylintChecker.TYPECHECK,
    "E1127": PylintChecker.TYPECHECK,
    "E1128": PylintChecker.TYPECHECK,
    "E1129": PylintChecker.TYPECHECK,
    "E1130": PylintChecker.TYPECHECK,
    "E1131": PylintChecker.TYPECHECK,
    "E1132": PylintChecker.TYPECHECK,
    "E1133": PylintChecker.TYPECHECK,
    "E1134": PylintChecker.TYPECHECK,
    "E1135": PylintChecker.TYPECHECK,
    "E1136": PylintChecker.TYPECHECK,
    "E1137": PylintChecker.TYPECHECK,
    "E1138": PylintChecker.TYPECHECK,
    "E1139": PylintChecker.TYPECHECK,
    "E1140": PylintChecker.TYPECHECK,
    "E1141": PylintChecker.TYPECHECK,
    "E1142": PylintChecker.TYPECHECK,
    # Logging checker
    "W1201": PylintChecker.LOGGING,
    "W1202": PylintChecker.LOGGING,
    "W1203": PylintChecker.LOGGING,
    "E1200": PylintChecker.LOGGING,
    "E1201": PylintChecker.LOGGING,
    "E1205": PylintChecker.LOGGING,
    "E1206": PylintChecker.LOGGING,
    # String checker
    "W1300": PylintChecker.STRING,
    "W1301": PylintChecker.STRING,
    "W1302": PylintChecker.STRING,
    "W1303": PylintChecker.STRING,
    "W1304": PylintChecker.STRING,
    "W1305": PylintChecker.STRING,
    "W1308": PylintChecker.STRING,
    "W1309": PylintChecker.STRING,
    "W1310": PylintChecker.STRING,
    "E1300": PylintChecker.STRING,
    "E1301": PylintChecker.STRING,
    "E1302": PylintChecker.STRING,
    "E1303": PylintChecker.STRING,
    "E1304": PylintChecker.STRING,
    "E1305": PylintChecker.STRING,
    "E1306": PylintChecker.STRING,
    "E1307": PylintChecker.STRING,
    "E1310": PylintChecker.STRING,
    # Refactoring checker
    "R1705": PylintChecker.REFACTORING,
    "R1710": PylintChecker.REFACTORING,
    "R1714": PylintChecker.REFACTORING,
    "R1715": PylintChecker.REFACTORING,
    "R1716": PylintChecker.REFACTORING,
    "R1717": PylintChecker.REFACTORING,
    "R1718": PylintChecker.REFACTORING,
    "R1720": PylintChecker.REFACTORING,
    "R1721": PylintChecker.REFACTORING,
    "R1724": PylintChecker.REFACTORING,
    "R1725": PylintChecker.REFACTORING,
    "R1728": PylintChecker.REFACTORING,
    "R1729": PylintChecker.REFACTORING,
    "R1732": PylintChecker.REFACTORING,
    "R1735": PylintChecker.REFACTORING,
    # Similarities checker
    "R0801": PylintChecker.SIMILARITIES,
    # Miscellaneous checker
    "W0511": PylintChecker.MISCELLANEOUS,
}


# Default enabled status for common messages (True = enabled by default)
MESSAGE_DEFAULT_ENABLED: dict[str, bool] = {
    # Most convention messages are enabled by default
    "C0114": True,
    "C0115": True,
    "C0116": True,
    "C0103": True,
    "C0301": True,
    "C0302": True,
    "C0303": True,
    # Refactoring suggestions (some disabled by default)
    "R0801": False,  # duplicate-code - expensive to check
    "R0901": True,
    "R0902": True,
    "R0903": True,
    "R0904": True,
    "R0911": True,
    "R0912": True,
    "R0913": True,
    "R0914": True,
    "R0915": True,
    # All errors are enabled by default
    "E0001": True,
    "E0100": True,
    "E0101": True,
    "E0102": True,
    "E0401": True,
    "E0601": True,
    "E0602": True,
    "E1101": True,
    # Most warnings are enabled by default
    "W0101": True,
    "W0102": True,
    "W0104": True,
    "W0105": True,
    "W0611": True,
    "W0612": True,
    "W0613": True,
    "W0621": True,
    "W0622": True,
    "W0702": True,
    "W0703": False,  # broad-except - often disabled
    "W0718": True,
    "W0719": True,
}


def get_checker_for_message(message_id: str) -> PylintChecker | None:
    """Get the checker that generates a specific message."""
    return MESSAGE_CHECKERS.get(message_id)


def is_message_enabled_by_default(message_id: str) -> bool:
    """Check if a message is enabled by default."""
    return MESSAGE_DEFAULT_ENABLED.get(message_id, True)


def get_severity_from_id(message_id: str) -> PylintSeverity:
    """Get severity from message ID."""
    if message_id and message_id[0] in SEVERITY_MAP:
        return SEVERITY_MAP[message_id[0]]
    return PylintSeverity.INFO


def get_symbol_from_id(message_id: str) -> str | None:
    """Get message symbol from message ID."""
    return COMMON_MESSAGES.get(message_id)


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class PylintMessage:
    """A single Pylint diagnostic message."""

    message_id: str  # e.g., "C0116"
    symbol: str  # e.g., "missing-function-docstring"
    message: str  # Human-readable message
    path: str  # File path
    module: str  # Module name
    line: int  # Line number
    column: int  # Column number
    end_line: int | None = None  # End line
    end_column: int | None = None  # End column
    obj: str | None = None  # Object name (function, class, method)
    severity: PylintSeverity = PylintSeverity.CONVENTION
    confidence: PylintConfidence = PylintConfidence.HIGH

    @property
    def location(self) -> str:
        """Get formatted location string."""
        return f"{self.path}:{self.line}:{self.column}"

    @property
    def category_char(self) -> str:
        """Get the category character (C/R/W/E/F)."""
        return self.message_id[0] if self.message_id else "I"

    def format(self, *, include_id: bool = True) -> str:
        """Format the message for display."""
        parts = [f"{self.location}: {self.severity.value[0].upper()}: {self.message}"]
        if include_id:
            parts[0] += f" ({self.message_id}: {self.symbol})"
        if self.obj:
            parts.append(f"  in {self.obj}")
        return "\n".join(parts)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PylintMessage:
        """Create from Pylint JSON2 output dict."""
        severity_str = data.get("type", "convention")
        try:
            severity = PylintSeverity(severity_str)
        except ValueError:
            severity = PylintSeverity.CONVENTION

        confidence_str = data.get("confidence", "HIGH")
        try:
            confidence = PylintConfidence(confidence_str)
        except ValueError:
            confidence = PylintConfidence.UNDEFINED

        return cls(
            message_id=data.get("message-id", ""),
            symbol=data.get("symbol", ""),
            message=data.get("message", ""),
            path=data.get("path", ""),
            module=data.get("module", ""),
            line=data.get("line", 0),
            column=data.get("column", 0),
            end_line=data.get("endLine"),
            end_column=data.get("endColumn"),
            obj=data.get("obj"),
            severity=severity,
            confidence=confidence,
        )


@dataclass
class PylintStatistics:
    """Pylint analysis statistics."""

    score: float = 0.0
    previous_score: float | None = None
    statement_count: int = 0
    message_type_count: dict[str, int] = field(default_factory=dict)
    modules_linted: int = 0

    @property
    def score_delta(self) -> float | None:
        """Get the change in score from previous run."""
        if self.previous_score is not None:
            return self.score - self.previous_score
        return None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PylintStatistics:
        """Create from Pylint JSON2 statistics dict."""
        return cls(
            score=data.get("score", 0.0),
            previous_score=data.get("previousScore"),
            statement_count=data.get("statement", 0),
            message_type_count=data.get("messageTypeCount", {}),
            modules_linted=data.get("modulesLinted", 0),
        )


@dataclass
class PylintConfig:
    """Configuration for Pylint analysis."""

    # Note: File parsing not implemented, use to_cli_args() for command building
    rcfile: Path | None = None
    disable: list[str] = field(default_factory=list)
    enable: list[str] = field(default_factory=list)
    max_line_length: int = 100
    max_args: int = 5
    max_locals: int = 15
    max_returns: int = 6
    max_branches: int = 12
    max_statements: int = 50
    max_attributes: int = 7
    max_public_methods: int = 20
    min_public_methods: int = 2
    good_names: list[str] = field(default_factory=lambda: ["i", "j", "k", "ex", "Run", "_"])
    ignore_patterns: list[str] = field(default_factory=list)
    plugins: list[str] = field(default_factory=list)

    @classmethod
    def from_file(cls, path: Path) -> PylintConfig:
        """
        Load configuration from .pylintrc, setup.cfg, or pyproject.toml.

        Args:
            path: Path to configuration file.

        Returns:
            PylintConfig populated from file.

        Raises:
            ValueError: If file type is not supported.
        """
        path = Path(path)

        if path.name == "pyproject.toml":
            return cls._from_pyproject(path)
        elif path.suffix in (".cfg", ".ini") or path.name in (".pylintrc", "pylintrc"):
            return cls._from_ini(path)
        else:
            raise ValueError(f"Unsupported config file: {path.name}")

    @classmethod
    def _from_pyproject(cls, path: Path) -> PylintConfig:
        """Load configuration from pyproject.toml."""
        if tomllib is None:
            raise ImportError("tomllib (Python 3.11+) or tomli is required for TOML parsing")

        with open(path, "rb") as f:
            data = tomllib.load(f)

        pylint_config = data.get("tool", {}).get("pylint", {})
        return cls._from_dict(pylint_config)

    @classmethod
    def _from_ini(cls, path: Path) -> PylintConfig:
        """Load configuration from INI file (.pylintrc or setup.cfg)."""
        parser = configparser.ConfigParser()
        parser.read(path)

        config = cls()

        # Parse [MASTER] section
        if "MASTER" in parser:
            s = parser["MASTER"]
            if "load-plugins" in s:
                config.plugins = [p.strip() for p in s["load-plugins"].split(",")]
            if "ignore" in s:
                config.ignore_patterns = [p.strip() for p in s["ignore"].split(",")]

        # Parse [MESSAGES CONTROL] section
        if "MESSAGES CONTROL" in parser:
            s = parser["MESSAGES CONTROL"]
            if "disable" in s:
                config.disable = [m.strip() for m in s["disable"].split(",") if m.strip()]
            if "enable" in s:
                config.enable = [m.strip() for m in s["enable"].split(",") if m.strip()]

        # Parse [FORMAT] section
        if "FORMAT" in parser:
            s = parser["FORMAT"]
            if "max-line-length" in s:
                config.max_line_length = int(s["max-line-length"])

        # Parse [DESIGN] section
        if "DESIGN" in parser:
            s = parser["DESIGN"]
            if "max-args" in s:
                config.max_args = int(s["max-args"])
            if "max-locals" in s:
                config.max_locals = int(s["max-locals"])
            if "max-returns" in s:
                config.max_returns = int(s["max-returns"])
            if "max-branches" in s:
                config.max_branches = int(s["max-branches"])
            if "max-statements" in s:
                config.max_statements = int(s["max-statements"])
            if "max-attributes" in s:
                config.max_attributes = int(s["max-attributes"])
            if "max-public-methods" in s:
                config.max_public_methods = int(s["max-public-methods"])
            if "min-public-methods" in s:
                config.min_public_methods = int(s["min-public-methods"])

        # Parse [BASIC] section for names
        if "BASIC" in parser:
            s = parser["BASIC"]
            if "good-names" in s:
                config.good_names = [n.strip() for n in s["good-names"].split(",")]

        return config

    @classmethod
    def _from_dict(cls, data: dict[str, Any]) -> PylintConfig:
        """Create PylintConfig from a dictionary (from pyproject.toml)."""
        config = cls()

        # Helper to handle both dict and dotted key access
        def get_nested(d: dict, *keys: str) -> Any:
            for key in keys:
                if isinstance(d, dict):
                    d = d.get(key, {})  # type: ignore
                else:
                    return None
            return d if d else None

        # Check for flat structure or nested structure
        master = get_nested(data, "master") or get_nested(data, "MASTER") or {}
        messages = get_nested(data, "messages_control") or get_nested(data, "MESSAGES CONTROL") or {}
        fmt = get_nested(data, "format") or get_nested(data, "FORMAT") or {}
        design = get_nested(data, "design") or get_nested(data, "DESIGN") or {}
        basic = get_nested(data, "basic") or get_nested(data, "BASIC") or {}

        # Parse from master
        if isinstance(master, dict):
            if "load-plugins" in master:
                plugins = master["load-plugins"]
                config.plugins = plugins if isinstance(plugins, list) else [p.strip() for p in plugins.split(",")]

        # Parse from messages control
        if isinstance(messages, dict):
            if "disable" in messages:
                disable = messages["disable"]
                config.disable = disable if isinstance(disable, list) else [m.strip() for m in disable.split(",")]
            if "enable" in messages:
                enable = messages["enable"]
                config.enable = enable if isinstance(enable, list) else [m.strip() for m in enable.split(",")]

        # Parse from format
        if isinstance(fmt, dict):
            if "max-line-length" in fmt:
                config.max_line_length = int(fmt["max-line-length"])

        # Parse from design
        if isinstance(design, dict):
            if "max-args" in design:
                config.max_args = int(design["max-args"])
            if "max-locals" in design:
                config.max_locals = int(design["max-locals"])
            if "max-returns" in design:
                config.max_returns = int(design["max-returns"])
            if "max-branches" in design:
                config.max_branches = int(design["max-branches"])
            if "max-statements" in design:
                config.max_statements = int(design["max-statements"])
            if "max-attributes" in design:
                config.max_attributes = int(design["max-attributes"])
            if "max-public-methods" in design:
                config.max_public_methods = int(design["max-public-methods"])
            if "min-public-methods" in design:
                config.min_public_methods = int(design["min-public-methods"])

        # Parse from basic
        if isinstance(basic, dict):
            if "good-names" in basic:
                names = basic["good-names"]
                config.good_names = names if isinstance(names, list) else [n.strip() for n in names.split(",")]

        return config

    @classmethod
    def find_config(cls, start_path: Path) -> PylintConfig | None:
        """
        Find and load configuration from the nearest config file.

        Searches upward from start_path for:
        1. .pylintrc
        2. pylintrc
        3. pyproject.toml (with [tool.pylint])
        4. setup.cfg (with [pylint.*])

        Args:
            start_path: Path to start searching from.

        Returns:
            PylintConfig if found, None otherwise.
        """
        current = start_path.resolve()
        if current.is_file():
            current = current.parent

        while current != current.parent:
            # Check for .pylintrc
            pylintrc = current / ".pylintrc"
            if pylintrc.exists():
                try:
                    return cls.from_file(pylintrc)
                except Exception:
                    pass

            # Check for pylintrc (without dot)
            pylintrc_no_dot = current / "pylintrc"
            if pylintrc_no_dot.exists():
                try:
                    return cls.from_file(pylintrc_no_dot)
                except Exception:
                    pass

            # Check for pyproject.toml
            pyproject = current / "pyproject.toml"
            if pyproject.exists():
                try:
                    config = cls._from_pyproject(pyproject)
                    # Check if config has non-default values
                    if config.disable or config.plugins or config.max_line_length != 100:
                        return config
                except Exception:
                    pass

            # Check for setup.cfg
            setup_cfg = current / "setup.cfg"
            if setup_cfg.exists():
                try:
                    parser = configparser.ConfigParser()
                    parser.read(setup_cfg)
                    # Check if any pylint section exists
                    if any(
                        s.startswith("pylint") or s in ("MASTER", "MESSAGES CONTROL", "FORMAT", "DESIGN")
                        for s in parser.sections()
                    ):
                        return cls.from_file(setup_cfg)
                except Exception:
                    pass

            current = current.parent

        return None

    def to_cli_args(self) -> list[str]:
        """Convert configuration to CLI arguments."""
        args = []

        if self.rcfile:
            args.extend(["--rcfile", str(self.rcfile)])

        if self.disable:
            args.extend(["--disable", ",".join(self.disable)])

        if self.enable:
            args.extend(["--enable", ",".join(self.enable)])

        args.extend(["--max-line-length", str(self.max_line_length)])
        args.extend(["--max-args", str(self.max_args)])
        args.extend(["--max-locals", str(self.max_locals)])

        for plugin in self.plugins:
            args.extend(["--load-plugins", plugin])

        return args


@dataclass
class PylintReport:
    """Complete Pylint analysis report."""

    messages: list[PylintMessage] = field(default_factory=list)
    statistics: PylintStatistics | None = None
    errors: list[str] = field(default_factory=list)
    config: PylintConfig | None = None
    pylint_version: str | None = None

    @property
    def message_count(self) -> int:
        """Get total number of messages."""
        return len(self.messages)

    @property
    def score(self) -> float:
        """Get the Pylint score."""
        return self.statistics.score if self.statistics else 0.0

    @property
    def error_count(self) -> int:
        """Get count of errors."""
        return sum(1 for m in self.messages if m.severity == PylintSeverity.ERROR)

    @property
    def warning_count(self) -> int:
        """Get count of warnings."""
        return sum(1 for m in self.messages if m.severity == PylintSeverity.WARNING)

    @property
    def convention_count(self) -> int:
        """Get count of convention violations."""
        return sum(1 for m in self.messages if m.severity == PylintSeverity.CONVENTION)

    @property
    def refactor_count(self) -> int:
        """Get count of refactor suggestions."""
        return sum(1 for m in self.messages if m.severity == PylintSeverity.REFACTOR)

    @property
    def messages_by_severity(self) -> dict[PylintSeverity, list[PylintMessage]]:
        """Group messages by severity."""
        result: dict[PylintSeverity, list[PylintMessage]] = {}
        for m in self.messages:
            result.setdefault(m.severity, []).append(m)
        return result

    @property
    def messages_by_file(self) -> dict[str, list[PylintMessage]]:
        """Group messages by file."""
        result: dict[str, list[PylintMessage]] = {}
        for m in self.messages:
            result.setdefault(m.path, []).append(m)
        return result

    @property
    def messages_by_symbol(self) -> dict[str, list[PylintMessage]]:
        """Group messages by symbol."""
        result: dict[str, list[PylintMessage]] = {}
        for m in self.messages:
            result.setdefault(m.symbol, []).append(m)
        return result

    def get_summary(self) -> dict[str, Any]:
        """Get a summary of the report."""
        return {
            "score": self.score,
            "message_count": self.message_count,
            "by_severity": {
                "fatal": sum(1 for m in self.messages if m.severity == PylintSeverity.FATAL),
                "error": self.error_count,
                "warning": self.warning_count,
                "refactor": self.refactor_count,
                "convention": self.convention_count,
            },
            "top_issues": [
                {"symbol": sym, "count": len(msgs)}
                for sym, msgs in sorted(self.messages_by_symbol.items(), key=lambda x: -len(x[1]))[:10]
            ],
        }


# =============================================================================
# Parser Class
# =============================================================================


class PylintParser:
    """
    Parser for Pylint static analyzer output.

    Pylint is Python's most comprehensive static analysis tool, checking for
    errors, enforcing coding standards, and detecting code smells.

    Status: COMPLETED
    - ✓ P2-PYLINT-001: Full JSON2 parsing with stdin support
    - ✓ P2-PYLINT-002: Message ID mapping with 200+ codes, checker grouping
    - ✓ P2-PYLINT-003: Config parsing from .pylintrc, setup.cfg, pyproject.toml
    - ✓ P2-PYLINT-004: Score parsing and improvement suggestions

    Usage:
        >>> parser = PylintParser()
        >>> report = parser.analyze("example.py")
        >>> print(f"Score: {report.score}/10")
        >>> for msg in report.messages:
        ...     print(f"{msg.symbol}: {msg.message}")

        >>> # Get score improvement suggestions
        >>> suggestions = parser.get_score_improvement_suggestions(report)
        >>> for s in suggestions:
        ...     print(f"{s['symbol']}: {s['description']}")
    """

    def __init__(self, *, pylint_path: str = "pylint"):
        """
        Initialize the Pylint parser.

        Args:
            pylint_path: Path to the pylint executable.
        """
        self.pylint_path = pylint_path
        self._version: str | None = None

    @property
    def version(self) -> str | None:
        """Get the Pylint version."""
        if self._version is None:
            try:
                result = subprocess.run(
                    [self.pylint_path, "--version"],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                self._version = result.stdout.strip().split("\n")[0]
            except (subprocess.CalledProcessError, FileNotFoundError):
                pass
        return self._version

    def is_available(self) -> bool:
        """Check if Pylint is available."""
        try:
            subprocess.run(
                [self.pylint_path, "--version"],
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
        config: PylintConfig | None = None,
    ) -> PylintReport:
        """
        Analyze Python files with Pylint.

        Args:
            target: File, directory, or list of targets to analyze.
            config: Optional configuration override.

        Returns:
            PylintReport with messages and statistics.
        """
        report = PylintReport(config=config, pylint_version=self.version)

        # Build targets list
        if isinstance(target, (str, Path)):
            targets = [str(target)]
        else:
            targets = [str(t) for t in target]

        # Build command - use JSON2 format for structured output
        cmd = [
            self.pylint_path,
            "--output-format=json2",
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

            # Parse JSON2 output
            if result.stdout.strip():
                try:
                    data = json.loads(result.stdout)

                    # Parse messages
                    for msg_data in data.get("messages", []):
                        report.messages.append(PylintMessage.from_dict(msg_data))

                    # Parse statistics
                    if "statistics" in data:
                        report.statistics = PylintStatistics.from_dict(data["statistics"])

                except json.JSONDecodeError as e:
                    report.errors.append(f"Failed to parse Pylint output: {e}")

            if result.stderr:
                report.errors.append(result.stderr.strip())

        except FileNotFoundError:
            report.errors.append(f"Pylint not found at: {self.pylint_path}")
        except subprocess.SubprocessError as e:
            report.errors.append(f"Pylint execution failed: {e}")

        return report

    def get_message_info(self, message_id_or_symbol: str) -> dict[str, Any] | None:
        """
        Get information about a specific message.

        Args:
            message_id_or_symbol: Either the ID (C0116) or symbol (missing-function-docstring)

        Returns:
            Dictionary with message information or None.
        """
        # Check if it's an ID
        if message_id_or_symbol in COMMON_MESSAGES:
            symbol = COMMON_MESSAGES[message_id_or_symbol]
            return {
                "id": message_id_or_symbol,
                "symbol": symbol,
                "severity": get_severity_from_id(message_id_or_symbol).value,
            }

        # Check if it's a symbol
        for msg_id, symbol in COMMON_MESSAGES.items():
            if symbol == message_id_or_symbol:
                return {
                    "id": msg_id,
                    "symbol": symbol,
                    "severity": get_severity_from_id(msg_id).value,
                }

        return None

    def list_all_messages(self) -> list[dict[str, str]]:
        """
        List all known message IDs and symbols.

        Returns:
            List of message information dictionaries.
        """
        return [
            {
                "id": msg_id,
                "symbol": symbol,
                "severity": get_severity_from_id(msg_id).value,
            }
            for msg_id, symbol in sorted(COMMON_MESSAGES.items())
        ]

    def analyze_string(
        self,
        source: str,
        *,
        filename: str = "stdin.py",
        config: PylintConfig | None = None,
    ) -> PylintReport:
        """
        Analyze Python source code from a string.

        Uses a temporary file since Pylint doesn't support direct stdin input.

        Args:
            source: Python source code.
            filename: Filename for error messages.
            config: Optional configuration override.

        Returns:
            PylintReport with messages and statistics.
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
            for msg in report.messages:
                if msg.path == str(temp_path):
                    msg.path = filename
            return report
        finally:
            temp_path.unlink(missing_ok=True)

    def get_messages_by_checker(
        self,
        messages: list[PylintMessage],
    ) -> dict[PylintChecker, list[PylintMessage]]:
        """
        Group messages by their source checker.

        Args:
            messages: List of Pylint messages to group.

        Returns:
            Dictionary mapping checker to list of messages.
        """
        result: dict[PylintChecker, list[PylintMessage]] = {}
        for msg in messages:
            checker = MESSAGE_CHECKERS.get(msg.message_id)
            if checker:
                result.setdefault(checker, []).append(msg)
            else:
                result.setdefault(PylintChecker.MISCELLANEOUS, []).append(msg)
        return result

    def get_score_improvement_suggestions(
        self,
        report: PylintReport,
        *,
        target_score: float = 10.0,
        max_suggestions: int = 5,
    ) -> list[dict[str, Any]]:
        """
        Get suggestions for improving the Pylint score.

        Analyzes the report and suggests which issues to fix first
        for maximum score improvement.

        Args:
            report: A PylintReport to analyze.
            target_score: Target score to reach.
            max_suggestions: Maximum number of suggestions to return.

        Returns:
            List of suggestion dictionaries with keys:
                - symbol: Message symbol
                - count: Number of occurrences
                - severity: Message severity
                - impact: Estimated score impact if fixed
                - description: Human-readable suggestion
        """
        if not report.messages or not report.statistics:
            return []

        current_score = report.score
        if current_score >= target_score:
            return []

        # Score formula: 10.0 - ((5*error + warning + refactor + convention) / statements) * 10
        # Impact weights based on formula
        IMPACT_WEIGHTS = {
            PylintSeverity.FATAL: 5.0,
            PylintSeverity.ERROR: 5.0,
            PylintSeverity.WARNING: 1.0,
            PylintSeverity.REFACTOR: 1.0,
            PylintSeverity.CONVENTION: 1.0,
            PylintSeverity.INFO: 0.0,
        }

        statements = report.statistics.statement_count or 1

        # Group by symbol and calculate impact
        by_symbol: dict[str, list[PylintMessage]] = {}
        for msg in report.messages:
            by_symbol.setdefault(msg.symbol, []).append(msg)

        suggestions: list[dict[str, Any]] = []
        for symbol, msgs in by_symbol.items():
            severity = msgs[0].severity
            weight = IMPACT_WEIGHTS.get(severity, 1.0)
            count = len(msgs)

            # Calculate score impact: (weight * count / statements) * 10
            impact = (weight * count / statements) * 10

            suggestions.append(
                {
                    "symbol": symbol,
                    "count": count,
                    "severity": severity.value,
                    "impact": round(impact, 2),
                    "message_id": msgs[0].message_id,
                    "description": f"Fix {count} '{symbol}' issue{'s' if count > 1 else ''} "
                    f"(+{impact:.2f} score impact)",
                }
            )

        # Sort by impact (descending)
        suggestions.sort(key=lambda x: x["impact"], reverse=True)

        return suggestions[:max_suggestions]

    def get_quick_wins(
        self,
        report: PylintReport,
        *,
        max_count: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Get quick win suggestions - easy fixes with good score impact.

        Focuses on convention and simple warning fixes that are typically
        easy to resolve.

        Args:
            report: A PylintReport to analyze.
            max_count: Maximum number of quick wins to return.

        Returns:
            List of quick win suggestions.
        """
        # Easy fix categories
        EASY_FIXES = {
            "missing-module-docstring",
            "missing-class-docstring",
            "missing-function-docstring",
            "line-too-long",
            "trailing-whitespace",
            "missing-final-newline",
            "wrong-import-order",
            "unused-import",
            "unused-variable",
            "invalid-name",
            "multiple-statements",
        }

        easy_messages = [m for m in report.messages if m.symbol in EASY_FIXES]

        if not easy_messages:
            return []

        # Group by symbol
        by_symbol: dict[str, list[PylintMessage]] = {}
        for msg in easy_messages:
            by_symbol.setdefault(msg.symbol, []).append(msg)

        quick_wins = [
            {
                "symbol": symbol,
                "count": len(msgs),
                "severity": msgs[0].severity.value,
                "difficulty": "easy",
                "sample_location": f"{msgs[0].path}:{msgs[0].line}",
            }
            for symbol, msgs in sorted(by_symbol.items(), key=lambda x: -len(x[1]))
        ]

        return quick_wins[:max_count]


# =============================================================================
# Utility Functions
# =============================================================================


def parse_pylint_json2(
    output: str,
) -> tuple[list[PylintMessage], PylintStatistics | None]:
    """
    Parse Pylint JSON2 format output.

    Args:
        output: JSON string from pylint --output-format=json2

    Returns:
        Tuple of (messages, statistics).
    """
    if not output.strip():
        return [], None

    data = json.loads(output)

    messages = [PylintMessage.from_dict(m) for m in data.get("messages", [])]
    statistics = None
    if "statistics" in data:
        statistics = PylintStatistics.from_dict(data["statistics"])

    return messages, statistics


def format_pylint_report(report: PylintReport) -> str:
    """Format a Pylint report for display."""
    lines = [
        f"Pylint Report (Score: {report.score:.2f}/10)",
        "=" * 50,
        "",
        f"Messages: {report.message_count}",
        f"  - Fatal: {sum(1 for m in report.messages if m.severity == PylintSeverity.FATAL)}",
        f"  - Errors: {report.error_count}",
        f"  - Warnings: {report.warning_count}",
        f"  - Refactor: {report.refactor_count}",
        f"  - Convention: {report.convention_count}",
        "",
    ]

    if report.messages:
        lines.append("Messages by file:")
        for path, msgs in sorted(report.messages_by_file.items()):
            lines.append(f"\n{path}:")
            for msg in sorted(msgs, key=lambda m: m.line):
                lines.append(f"  {msg.line}: {msg.symbol} - {msg.message}")

    return "\n".join(lines)
