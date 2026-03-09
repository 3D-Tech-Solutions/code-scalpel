#!/usr/bin/env python3
# Phase 1: Define Java parser registry and import core parsers
# This module sets up the framework for integrating various Java parsers
# into the code analysis tool. The actual implementation of registry methods
# will be completed in Phase 2.

from .java_parser_treesitter import (
    JavaAnnotation,
    JavaClass,
    JavaEnum,
    JavaEnumConstant,
    JavaField,
    JavaInterface,
    JavaMethod,
    JavaModule,
    JavaModuleDirective,
    JavaParameter,
)
from .java_parser_treesitter import JavaParser as TreeSitterJavaParser
from .java_parser_treesitter import (
    JavaParseResult,
    JavaRecord,
    JavaRecordComponent,
    JavaStaticInitializer,
)
from .java_parsers_Checkstyle import CheckstyleParser, CheckstyleViolation
from .java_parsers_ErrorProne import ErrorProneIssue, ErrorProneParser
from .java_parsers_FindSecBugs import FindSecBugsParser, SecurityBug
from .java_parsers_Infer import InferIssue, InferParser
from .java_parsers_JArchitect import (
    DependencyIssue,
    JArchitectParser,
    JArchitectReport,
    QualityMetric,
)
from .java_parsers_javalang import (
    CodeMetrics,
    DesignPatternMatch,
    HalsteadMetrics,
)
from .java_parsers_javalang import JavaParser as JavalangParser
from .java_parsers_javalang import (
    MethodCallInfo,
    MethodMetrics,
    SecurityIssue,
    ThreadSafetyInfo,
    TryCatchPattern,
    TypeHierarchy,
)
from .java_parsers_DependencyCheck import CVEFinding, DependencyCheckParser
from .java_parsers_Gradle import GradleCompileError, GradleDependency, GradleParser
from .java_parsers_JaCoCo import ClassCoverage, CoverageMetrics, JaCoCoParser
from .java_parsers_Maven import CompileError, MavenDependency, MavenParser, MavenPlugin
from .java_parsers_Pitest import MutationResult, PitestParser
from .java_parsers_PMD import PMDParser, PMDViolation
from .java_parsers_Semgrep import SemgrepFinding, SemgrepParser
from .java_parsers_SonarQube import SonarIssue, SonarMetrics, SonarQubeParser
from .java_parsers_SpotBugs import SpotBug, SpotBugsParser

__all__ = [
    # Core parsers
    "TreeSitterJavaParser",
    "JavalangParser",
    # Tree-sitter dataclasses
    "JavaParseResult",
    "JavaClass",
    "JavaMethod",
    "JavaField",
    "JavaParameter",
    "JavaAnnotation",
    "JavaEnum",
    "JavaEnumConstant",
    "JavaInterface",
    # Java 14+ Records
    "JavaRecord",
    "JavaRecordComponent",
    # Java 9+ Modules
    "JavaModule",
    "JavaModuleDirective",
    # Static initializers
    "JavaStaticInitializer",
    # Javalang dataclasses
    "MethodCallInfo",
    "MethodMetrics",
    "HalsteadMetrics",
    "TypeHierarchy",
    "DesignPatternMatch",
    "TryCatchPattern",
    "ThreadSafetyInfo",
    "SecurityIssue",
    "CodeMetrics",
    # Static analysis
    "CheckstyleParser",
    "CheckstyleViolation",
    "PMDParser",
    "PMDViolation",
    "SpotBugsParser",
    "SpotBug",
    "ErrorProneParser",
    "ErrorProneIssue",
    "InferParser",
    "InferIssue",
    # Security
    "FindSecBugsParser",
    "SecurityBug",
    # Architecture
    "JArchitectParser",
    "JArchitectReport",
    "QualityMetric",
    "DependencyIssue",
    # Quality platform
    "SonarQubeParser",
    "SonarIssue",
    "SonarMetrics",
    # Build tools — Stage 4c [20260303_FEATURE]
    "MavenParser",
    "MavenDependency",
    "MavenPlugin",
    "CompileError",
    "GradleParser",
    "GradleDependency",
    "GradleCompileError",
    # Coverage / mutation
    "JaCoCoParser",
    "CoverageMetrics",
    "ClassCoverage",
    "PitestParser",
    "MutationResult",
    # Vulnerability / SAST
    "DependencyCheckParser",
    "CVEFinding",
    "SemgrepParser",
    "SemgrepFinding",
    # Registry
    "JavaParserRegistry",
]


class JavaParserRegistry:
    """Registry for Java static-analysis tool parsers.

    [20260304_FEATURE] Polyglot Phase 2: lazy-load factory for Java tools.
    Exposes semgrep, checkstyle, and pmd — all have execute_* methods.
    SpotBugs/SonarQube require XML report files and are excluded here.
    """

    _TOOL_MAP: dict = {
        "semgrep": ("java_parsers_Semgrep", "SemgrepParser"),
        # [20260304_FEATURE] Checkstyle and PMD now have execute_* wrappers
        "checkstyle": ("java_parsers_Checkstyle", "CheckstyleParser"),
        "pmd": ("java_parsers_PMD", "PMDParser"),
    }

    def get_parser(self, tool_name: str):
        """Return an instantiated parser for *tool_name*.

        Args:
            tool_name: One of the recognised tool identifiers (case-insensitive).

        Raises:
            ValueError: If *tool_name* is not a recognised executable tool.
        """
        import importlib

        key = tool_name.lower()
        if key not in self._TOOL_MAP:
            raise ValueError(
                f"Unknown Java parser tool: {tool_name!r}. "
                f"Valid options: {sorted(set(self._TOOL_MAP.keys()))}"
            )
        module_name, class_name = self._TOOL_MAP[key]
        module = importlib.import_module(f".{module_name}", package=__package__)
        return getattr(module, class_name)()
