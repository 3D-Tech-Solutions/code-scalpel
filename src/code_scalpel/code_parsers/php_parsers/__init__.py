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
    from .php_parsers_phpmd import (
        PHPMDConfig,
        PHPMDParser,
        PHPMDPriority,
        PHPMDRuleType,
        PHPMDViolation,
    )
    from .php_parsers_ast import (
        PHPClass,
        PHPFunction,
        PHPParserAST,
    )
    from .php_parsers_composer import (
        ComposerConfig,
        ComposerPackage,
        ComposerParser,
    )
    from .php_parsers_exakat import (
        ExakatCategory,
        ExakatIssue,
        ExakatParser,
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
    # PHPMD — [20260304_FEATURE] Phase 2
    "PHPMDParser",
    "PHPMDViolation",
    "PHPMDPriority",
    "PHPMDRuleType",
    "PHPMDConfig",
    # PHP AST — [20260304_FEATURE] Phase 2
    "PHPParserAST",
    "PHPClass",
    "PHPFunction",
    # Composer — [20260304_FEATURE] Phase 2
    "ComposerParser",
    "ComposerPackage",
    "ComposerConfig",
    # Exakat — [20260304_FEATURE] Phase 2
    "ExakatParser",
    "ExakatIssue",
    "ExakatCategory",
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
        from .php_parsers_PHPCS import PHPCSParser  # noqa: F401
        from .php_parsers_PHPCS import (
            PHPCSConfig,
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
        from .php_parsers_PHPStan import PHPStanConfig  # noqa: F401
        from .php_parsers_PHPStan import (
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
        from .php_parsers_Psalm import PsalmError  # noqa: F401
        from .php_parsers_Psalm import (
            PsalmConfig,
            PsalmErrorType,
            PsalmParser,
            PsalmSeverity,
        )

        return locals()[name]
    elif name in (
        "PHPMDParser",
        "PHPMDViolation",
        "PHPMDPriority",
        "PHPMDRuleType",
        "PHPMDConfig",
    ):
        from .php_parsers_phpmd import (
            PHPMDConfig,
            PHPMDParser,
            PHPMDPriority,
            PHPMDRuleType,
            PHPMDViolation,
        )

        return locals()[name]
    elif name in ("PHPParserAST", "PHPClass", "PHPFunction"):
        from .php_parsers_ast import PHPClass, PHPFunction, PHPParserAST

        return locals()[name]
    elif name in ("ComposerParser", "ComposerPackage", "ComposerConfig"):
        from .php_parsers_composer import (
            ComposerConfig,
            ComposerPackage,
            ComposerParser,
        )

        return locals()[name]
    elif name in ("ExakatParser", "ExakatIssue", "ExakatCategory"):
        from .php_parsers_exakat import ExakatCategory, ExakatIssue, ExakatParser

        return locals()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


class PHPParserRegistry:
    """Registry for PHP static-analysis tool parsers.

    [20260304_FEATURE] Polyglot Phase 2: lazy-load factory pattern.
    All execute_* methods accept a single str/Path; use call_style='single_str'.
    """

    _TOOL_MAP: dict = {
        "phpcs": ("php_parsers_PHPCS", "PHPCSParser"),
        "phpstan": ("php_parsers_PHPStan", "PHPStanParser"),
        "psalm": ("php_parsers_Psalm", "PsalmParser"),
        "phpmd": ("php_parsers_phpmd", "PHPMDParser"),
        "exakat": ("php_parsers_exakat", "ExakatParser"),
    }

    def get_parser(self, tool_name: str):
        """Return an instantiated parser for *tool_name*.

        Args:
            tool_name: One of the recognised tool identifiers (case-insensitive).

        Raises:
            ValueError: If *tool_name* is not a recognised tool.
        """
        import importlib

        key = tool_name.lower()
        if key not in self._TOOL_MAP:
            raise ValueError(
                f"Unknown PHP parser tool: {tool_name!r}. "
                f"Valid options: {sorted(set(self._TOOL_MAP.keys()))}"
            )
        module_name, class_name = self._TOOL_MAP[key]
        module = importlib.import_module(f".{module_name}", package=__package__)
        return getattr(module, class_name)()
