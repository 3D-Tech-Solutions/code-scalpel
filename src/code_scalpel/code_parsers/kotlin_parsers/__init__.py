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
    from .kotlin_parsers_diktat import (
        DiktatParser, DiktatViolation, DiktatSeverity, DiktatRuleSet, DiktatConfig,
    )
    from .kotlin_parsers_gradle import (
        GradleBuildParser, Dependency, GradlePlugin, BuildConfiguration,
        ConfigurationType, PluginType,
    )
    from .kotlin_parsers_compose import (
        ComposeLinterParser, ComposeIssue, ComposeMetrics, ComposeIssueType, ComposeSeverity,
    )
    from .kotlin_parsers_Konsist import (
        KonsistParser, KonsistViolation, KonsistRule, KonsistSeverity, KonsistRuleType,
    )
    from .kotlin_parsers_test import (
        KotlinTestParser, TestCase, TestSuite, CoverageMetrics, TestStatus, TestFramework,
    )
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
    # diktat
    "DiktatParser", "DiktatViolation", "DiktatSeverity",
    "DiktatRuleSet", "DiktatConfig",
    # gradle
    "GradleBuildParser", "Dependency", "GradlePlugin", "BuildConfiguration",
    "ConfigurationType", "PluginType",
    # compose
    "ComposeLinterParser", "ComposeIssue", "ComposeMetrics",
    "ComposeIssueType", "ComposeSeverity",
    # konsist
    "KonsistParser", "KonsistViolation", "KonsistRule",
    "KonsistSeverity", "KonsistRuleType",
    # kotlin-test
    "KotlinTestParser", "TestCase", "TestSuite", "CoverageMetrics",
    "TestStatus", "TestFramework",
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
        "DiktatParser", "DiktatViolation", "DiktatSeverity", "DiktatRuleSet", "DiktatConfig",
    ):
        from .kotlin_parsers_diktat import (
            DiktatParser, DiktatViolation, DiktatSeverity, DiktatRuleSet, DiktatConfig,
        )
        return locals()[name]

    if name in (
        "GradleBuildParser", "Dependency", "GradlePlugin", "BuildConfiguration",
        "ConfigurationType", "PluginType",
    ):
        from .kotlin_parsers_gradle import (
            GradleBuildParser, Dependency, GradlePlugin, BuildConfiguration,
            ConfigurationType, PluginType,
        )
        return locals()[name]

    if name in (
        "ComposeLinterParser", "ComposeIssue", "ComposeMetrics",
        "ComposeIssueType", "ComposeSeverity",
    ):
        from .kotlin_parsers_compose import (
            ComposeLinterParser, ComposeIssue, ComposeMetrics, ComposeIssueType, ComposeSeverity,
        )
        return locals()[name]

    if name in (
        "KonsistParser", "KonsistViolation", "KonsistRule", "KonsistSeverity", "KonsistRuleType",
    ):
        from .kotlin_parsers_Konsist import (
            KonsistParser, KonsistViolation, KonsistRule, KonsistSeverity, KonsistRuleType,
        )
        return locals()[name]

    if name in (
        "KotlinTestParser", "TestCase", "TestSuite", "CoverageMetrics", "TestStatus", "TestFramework",
    ):
        from .kotlin_parsers_test import (
            KotlinTestParser, TestCase, TestSuite, CoverageMetrics, TestStatus, TestFramework,
        )
        return locals()[name]

    if name in (
        "DetektParser",
        "DetektFinding",
        "DetektSeverity",
        "DetektRuleSet",
        "DetektConfig",
        "DetektReport",
    ):
        from .kotlin_parsers_Detekt import DetektConfig  # noqa: F401
        from .kotlin_parsers_Detekt import (
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
        from .kotlin_parsers_ktlint import KtlintConfig  # noqa: F401
        from .kotlin_parsers_ktlint import (
            KtlintParser,
            KtlintReport,
            KtlintRuleSet,
            KtlintSeverity,
            KtlintViolation,
        )

        return locals()[name]

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


class KotlinParserRegistry:
    """Registry for Kotlin static-analysis tool parsers.

    [20260304_FEATURE] Polyglot Phase 2: lazy-load factory pattern.
    execute_* methods accept a single Path; use call_style='single_path'.
    """

    _TOOL_MAP: dict = {
        "diktat": ("kotlin_parsers_diktat", "DiktatParser"),
        "compose": ("kotlin_parsers_compose", "ComposeLinterParser"),
        "gradle": ("kotlin_parsers_gradle", "GradleBuildParser"),
        "konsist": ("kotlin_parsers_Konsist", "KonsistParser"),
        "test": ("kotlin_parsers_test", "KotlinTestParser"),
        "kotlin-test": ("kotlin_parsers_test", "KotlinTestParser"),
        "kotlin_test": ("kotlin_parsers_test", "KotlinTestParser"),
        "detekt": ("kotlin_parsers_Detekt", "DetektParser"),
        "ktlint": ("kotlin_parsers_ktlint", "KtlintParser"),
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
                f"Unknown Kotlin parser tool: {tool_name!r}. "
                f"Valid options: {sorted(set(self._TOOL_MAP.keys()))}"
            )
        module_name, class_name = self._TOOL_MAP[key]
        module = importlib.import_module(f".{module_name}", package=__package__)
        return getattr(module, class_name)()

    def analyze(self, path, tools=None):
        """Run selected Kotlin parsers against *path* and aggregate results.

        [20260306_FEATURE] Added parity helper so the registry can execute the
        newly-wired Detekt and ktlint parsers the same way other language
        registries do.
        """
        from pathlib import Path

        selected = [t.lower().replace("-", "_") for t in tools] if tools else [
            key for key in self._TOOL_MAP if "-" not in key
        ]
        results: dict = {}
        target = Path(str(path))

        for tool_key in selected:
            try:
                parser = self.get_parser(tool_key)
                if tool_key == "diktat" and hasattr(parser, "execute_diktat"):
                    results[tool_key] = parser.execute_diktat(target)
                elif tool_key == "compose" and hasattr(parser, "execute_compiler_analysis"):
                    results[tool_key] = parser.execute_compiler_analysis(target)
                elif tool_key == "gradle" and hasattr(parser, "parse_build_gradle_kts"):
                    build_file = target / "build.gradle.kts"
                    results[tool_key] = (
                        parser.parse_build_gradle_kts(build_file) if build_file.exists() else None
                    )
                elif tool_key == "konsist" and hasattr(parser, "validate_architecture"):
                    results[tool_key] = parser.validate_architecture(target)
                elif tool_key in {"test", "kotlin_test"}:
                    results[tool_key] = []
                elif tool_key == "detekt" and hasattr(parser, "analyze_project"):
                    results[tool_key] = parser.analyze_project(str(target))
                elif tool_key == "ktlint" and hasattr(parser, "check_directory"):
                    results[tool_key] = parser.check_directory(str(target))
                else:
                    results[tool_key] = []
            except Exception:
                results[tool_key] = []
        return results
