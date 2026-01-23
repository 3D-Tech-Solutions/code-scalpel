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
    JavaParseResult,
    JavaRecord,
    JavaRecordComponent,
    JavaStaticInitializer,
)
from .java_parser_treesitter import JavaParser as TreeSitterJavaParser
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
    MethodCallInfo,
    MethodMetrics,
    SecurityIssue,
    ThreadSafetyInfo,
    TryCatchPattern,
    TypeHierarchy,
)
from .java_parsers_javalang import JavaParser as JavalangParser
from .java_parsers_PMD import PMDParser, PMDViolation
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
]
