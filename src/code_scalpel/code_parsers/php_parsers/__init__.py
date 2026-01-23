#!/usr/bin/env python3
# [20260102_REFACTOR] Lazy exports via __getattr__; suppress unused-import lint for optional parsers.
# ruff: noqa: F401
"""
PHP Parser Module - Comprehensive PHP code analysis tooling.

This module provides parsers and analyzers for PHP code, integrating with
industry-standard tools including PHPCS, PHPStan, Psalm, and others.

Planned Features:
    Static Analysis:
        - PHPCS integration for code standard enforcement
        - PHPStan integration for type checking
        - Psalm integration for static analysis

    Type Analysis:
        - Type inference tracking
        - Type coverage measurement
        - Generic type analysis
        - Union/Intersection type support
        - Callable type checking

    Security Analysis:
        - Taint analysis for injection vulnerabilities
        - SQL injection detection
        - XSS vulnerability detection
        - Command injection detection
        - Unsafe function usage detection

    Code Quality:
        - Cyclomatic complexity calculation
        - Cognitive complexity metrics
        - Code smell detection
        - Dead code detection
        - Unused variable detection
        - Duplicate code detection

    Framework Detection:
        - Laravel/Symfony detection
        - WordPress plugin detection
        - Magento module detection
        - Doctrine ORM detection
        - Custom framework patterns

===================================

===================================

==============================================

# [20260102_REFACTOR] Lazy exports via __getattr__; imported parsers appear unused locally.
# ruff: noqa: F401

==========================================

============================================

=======================================

=========================================

====================================================

==================================================

==============================================

============================================================

=======================================
"""

from typing import TYPE_CHECKING

# Lazy imports to avoid circular dependencies
if TYPE_CHECKING:
    from .php_parsers_PHPCS import (
        PHPCSConfig,
        PHPCSParser,
        PHPCSSeverity,
        PHPCSStandard,
        PHPCSViolation,
    )
    from .php_parsers_PHPStan import (
        PHPStanConfig,
        PHPStanError,
        PHPStanErrorType,
        PHPStanLevel,
        PHPStanParser,
    )
    from .php_parsers_Psalm import (
        PsalmConfig,
        PsalmError,
        PsalmErrorType,
        PsalmParser,
        PsalmSeverity,
    )

__all__ = [
    # PHPCS
    "PHPCSParser",
    "PHPCSViolation",
    "PHPCSSeverity",
    "PHPCSStandard",
    "PHPCSConfig",
    # PHPStan
    "PHPStanParser",
    "PHPStanError",
    "PHPStanLevel",
    "PHPStanErrorType",
    "PHPStanConfig",
    # Psalm
    "PsalmParser",
    "PsalmError",
    "PsalmSeverity",
    "PsalmErrorType",
    "PsalmConfig",
]


def __getattr__(name: str):
    """Lazy load parser classes on first access."""
    if name in (
        "PHPCSParser",
        "PHPCSViolation",
        "PHPCSSeverity",
        "PHPCSStandard",
        "PHPCSConfig",
    ):
        from .php_parsers_PHPCS import (
            PHPCSConfig,
            PHPCSParser,  # noqa: F401
            PHPCSSeverity,
            PHPCSStandard,
            PHPCSViolation,
        )

        return locals()[name]
    elif name in (
        "PHPStanParser",
        "PHPStanError",
        "PHPStanLevel",
        "PHPStanErrorType",
        "PHPStanConfig",
    ):
        from .php_parsers_PHPStan import (
            PHPStanConfig,  # noqa: F401
            PHPStanError,
            PHPStanErrorType,
            PHPStanLevel,
            PHPStanParser,
        )

        return locals()[name]
    elif name in (
        "PsalmParser",
        "PsalmError",
        "PsalmSeverity",
        "PsalmErrorType",
        "PsalmConfig",
    ):
        from .php_parsers_Psalm import (
            PsalmConfig,
            PsalmError,  # noqa: F401
            PsalmErrorType,
            PsalmParser,
            PsalmSeverity,
        )

        return locals()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
