#!/usr/bin/env python3
# [20260102_REFACTOR] Lazy exports via __getattr__; suppress unused-import lint for optional parsers.
# ruff: noqa: F401
"""
Kotlin Parser Module - Comprehensive Kotlin code analysis tooling.

This module provides parsers and analyzers for Kotlin code, integrating with
popular Kotlin tooling including Detekt, ktlint, and the Kotlin compiler.

Planned Features:
    Static Analysis:
        - Detekt integration for code smell detection
        - ktlint integration for style enforcement
        - Kotlin compiler diagnostics parsing

    Code Quality:
        - Cyclomatic complexity calculation
        - Cognitive complexity metrics
        - Code smell detection (long methods, large classes, etc.)
        - Duplicate code detection

    Type Analysis:
        - Type inference tracking
        - Null safety analysis
        - Smart cast detection
        - Generic type analysis

    Coroutine Analysis:
        - Coroutine scope detection
        - Suspend function tracking
        - Flow/Channel usage analysis
        - Structured concurrency validation

    DSL Detection:
        - Builder pattern detection
        - Type-safe builder analysis
        - Custom DSL identification

===================================

===================================

=================================================

==============================================

============================================

# [20260102_REFACTOR] Lazy exports via __getattr__; imported parsers appear unused locally.
# ruff: noqa: F401

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
    from .kotlin_parsers_Detekt import (
        DetektConfig,
        DetektFinding,
        DetektParser,
        DetektReport,
        DetektRuleSet,
        DetektSeverity,
    )
    from .kotlin_parsers_ktlint import (
        KtlintConfig,
        KtlintParser,
        KtlintReport,
        KtlintRuleSet,
        KtlintSeverity,
        KtlintViolation,
    )

__all__ = [
    # Detekt
    "DetektParser",
    "DetektFinding",
    "DetektSeverity",
    "DetektRuleSet",
    "DetektConfig",
    "DetektReport",
    # ktlint
    "KtlintParser",
    "KtlintViolation",
    "KtlintSeverity",
    "KtlintRuleSet",
    "KtlintConfig",
    "KtlintReport",
]


def __getattr__(name: str):
    """Lazy load parser classes on first access."""
    if name in (
        "DetektParser",
        "DetektFinding",
        "DetektSeverity",
        "DetektRuleSet",
        "DetektConfig",
        "DetektReport",
    ):
        from .kotlin_parsers_Detekt import (
            DetektConfig,  # noqa: F401
            DetektFinding,
            DetektParser,
            DetektReport,
            DetektRuleSet,
            DetektSeverity,
        )

        return locals()[name]

    if name in (
        "KtlintParser",
        "KtlintViolation",
        "KtlintSeverity",
        "KtlintRuleSet",
        "KtlintConfig",
        "KtlintReport",
    ):
        from .kotlin_parsers_ktlint import (
            KtlintConfig,  # noqa: F401
            KtlintParser,
            KtlintReport,
            KtlintRuleSet,
            KtlintSeverity,
            KtlintViolation,
        )

        return locals()[name]

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
