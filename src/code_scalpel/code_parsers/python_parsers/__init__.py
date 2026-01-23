#!/usr/bin/env python3
"""
Python Parser Module - Comprehensive Python Code Analysis Tooling.
==================================================================

Code Scalpel's Python Parser provides surgical precision for Python code analysis,
integrating the best static analysis tools in the Python ecosystem.

Module Structure
----------------
This module is organized into specialized parsers, each with a focused responsibility:

    python_parsers_ast.py       - Core AST analysis, symbol extraction, CFG/DFG
    python_parsers_ruff.py      - Fast Rust-based linting (replaces Flake8/isort)
    python_parsers_mypy.py      - Static type checking and type coverage
    python_parsers_pylint.py    - Comprehensive code quality analysis
    python_parsers_bandit.py    - Security vulnerability detection
    python_parsers_flake8.py    - Style and convention checking
    python_parsers_code_quality.py - Complexity metrics and code smells
    python_parsers_pydocstyle.py   - Docstring validation and coverage
    python_parsers_pycodestyle.py  - PEP 8 style guide enforcement
    python_parsers_prospector.py   - Meta-linter aggregating multiple tools

Architecture
------------
All parsers follow a consistent pattern:
    1. Config dataclass   - Tool-specific configuration options
    2. Result dataclasses - Structured output (violations, issues, metrics)
    3. Parser class       - Main interface inheriting from BaseToolParser
    4. Report dataclass   - Aggregated analysis results

Usage
-----
    >>> from code_scalpel.code_parser.python_parsers import PythonASTParser
    >>> parser = PythonASTParser()
    >>> module = parser.parse_file("example.py")
    >>> print(module.functions)  # List of PythonFunction objects

    >>> from code_scalpel.code_parser.python_parsers import RuffParser
    >>> ruff = RuffParser()
    >>> report = ruff.analyze("example.py")
    >>> for violation in report.violations:
    ...     print(f"{violation.code}: {violation.message}")

"""

from __future__ import annotations

from typing import TYPE_CHECKING

# =============================================================================
# Module Version and Metadata
# =============================================================================
__version__ = "0.1.0"
__author__ = "Code Scalpel Team"

# =============================================================================
# Lazy Imports for Type Checking
# =============================================================================
# Using lazy loading via __getattr__ to avoid circular dependencies and improve
# startup time. All imports happen on first access, not at module initialization.

if TYPE_CHECKING:
    # Type stubs for IDE support - actual imports happen in __getattr__
    pass


# =============================================================================
# Public API - Exported Symbols
# =============================================================================
# Note: Exports are handled via lazy loading in __getattr__. This __all__
# list is intentionally minimal to avoid import errors. Actual exports
# are defined in each parser module and loaded on-demand.
__all__ = [
    # Convenience functions
    "get_available_parsers",
    "get_parser_info",
]


# =============================================================================
# Lazy Loading Implementation
# =============================================================================
def __getattr__(name: str):
    """
    Lazy load parser classes on first access.

    This improves import time by deferring the loading of parser modules
    until they are actually needed. Each parser module may have its own
    dependencies (subprocess calls to tools, etc.) that we don't want to
    load eagerly.

    Args:
        name: The attribute name being accessed.

    Returns:
        The requested class or object.

    Raises:
        AttributeError: If the name is not a valid export.
    """
    # AST Parser exports
    _ast_exports = {
        "PythonASTParser",
        "PythonModule",
        "PythonClass",
        "PythonFunction",
        "PythonImport",
        "PythonSymbol",
        "PythonScope",
        "CallGraph",
        "ControlFlowGraph",
        "DataFlowInfo",
        # Optimization analysis exports
        "Expression",
        "ConstantValue",
    }
    if name in _ast_exports:
        from . import python_parsers_ast

        return getattr(python_parsers_ast, name)

    # Ruff Parser exports
    _ruff_exports = {
        "RuffParser",
        "RuffViolation",
        "RuffFix",
        "RuffEdit",
        "RuffConfig",
        "RuffReport",
        "RuffSeverity",
        "SourceLocation",
        "FixApplicability",
        # Rule category mapping
        "RULE_PREFIXES",
    }
    if name in _ruff_exports:
        from . import python_parsers_ruff

        return getattr(python_parsers_ruff, name)

    # mypy Parser exports
    _mypy_exports = {
        "MypyParser",
        "MypyError",
        "MypySeverity",
        "MypyErrorCategory",
        "MypyConfig",
        "MypyReport",
        "TypeCoverageInfo",
        "RevealedType",
        # Typeshed suggestions mapping
        "TYPESHED_SUGGESTIONS",
    }
    if name in _mypy_exports:
        from . import python_parsers_mypy

        return getattr(python_parsers_mypy, name)

    # Pylint Parser exports
    _pylint_exports = {
        "PylintParser",
        "PylintMessage",
        "PylintSeverity",
        "PylintConfidence",
        "PylintChecker",
        "PylintConfig",
        "PylintReport",
        "PylintStatistics",
        # Message mappings
        "MESSAGE_CHECKERS",
        "MESSAGE_DEFAULT_ENABLED",
        "COMMON_MESSAGES",
    }
    if name in _pylint_exports:
        from . import python_parsers_pylint

        return getattr(python_parsers_pylint, name)

    # Bandit Parser exports
    _bandit_exports = {
        "BanditParser",
        "BanditIssue",
        "BanditSeverity",
        "BanditConfidence",
        "BanditConfig",
        "BanditReport",
        # Security analysis exports
        "CWE_FIX_SUGGESTIONS",
        "OWASPCategory",
        "OWASP_TOP_10_MAPPING",
    }
    if name in _bandit_exports:
        from . import python_parsers_bandit

        return getattr(python_parsers_bandit, name)

    # Flake8 Parser exports
    _flake8_exports = {
        "Flake8Parser",
        "Flake8Violation",
        "Flake8Config",
        "Flake8Report",
        # Error code mapping exports
        "ERROR_CODE_MESSAGES",
    }
    if name in _flake8_exports:
        from . import python_parsers_flake8

        return getattr(python_parsers_flake8, name)

    # Code Quality exports
    _quality_exports = {
        "PythonCodeQualityAnalyzer",
        "CodeSmell",
        "ComplexityMetrics",
        "MaintainabilityMetrics",
        "CodeQualityReport",
    }
    if name in _quality_exports:
        from . import python_parsers_code_quality

        return getattr(python_parsers_code_quality, name)

    # pydocstyle Parser exports
    _pydocstyle_exports = {
        "PydocstyleParser",
        "PydocstyleViolation",
        "PydocstyleConvention",
        "PydocstyleConfig",
        "PydocstyleReport",
        # Docstring quality analysis exports
        "DocstringQualityAnalyzer",
        "DocstringQualityIssueType",
        "FunctionDocstringQuality",
        "ModuleDocstringQuality",
    }
    if name in _pydocstyle_exports:
        from . import python_parsers_pydocstyle

        return getattr(python_parsers_pydocstyle, name)

    # pycodestyle Parser exports
    _pycodestyle_exports = {
        "PycodestyleParser",
        "PycodestyleViolation",
        "PycodestyleConfig",
        "PycodestyleReport",
    }
    if name in _pycodestyle_exports:
        from . import python_parsers_pycodestyle

        return getattr(python_parsers_pycodestyle, name)

    # Prospector Parser exports
    _prospector_exports = {
        "ProspectorParser",
        "ProspectorMessage",
        "ProspectorConfig",
        "ProspectorReport",
        # Profile management exports
        "ProspectorProfile",
        "ProspectorProfileLoader",
        "BUILTIN_PROFILES",
        "merge_profiles",
    }
    if name in _prospector_exports:
        from . import python_parsers_prospector

        return getattr(python_parsers_prospector, name)

    # isort Parser exports (PLANNED)
    _isort_exports = {
        "IsortParser",
        "ImportGroup",
        "ImportIssue",
        "IsortConfig",
        "IsortReport",
    }
    if name in _isort_exports:
        from . import python_parsers_isort

        return getattr(python_parsers_isort, name)

    # Vulture Parser exports (PLANNED)
    _vulture_exports = {
        "VultureParser",
        "UnusedItem",
        "VultureConfig",
        "VultureReport",
    }
    if name in _vulture_exports:
        from . import python_parsers_vulture

        return getattr(python_parsers_vulture, name)

    # Radon Parser exports (PLANNED)
    _radon_exports = {
        "RadonParser",
        "ComplexityMetrics",
        "FunctionComplexity",
        "ClassComplexity",
        "RadonConfig",
        "RadonReport",
    }
    if name in _radon_exports:
        from . import python_parsers_radon

        return getattr(python_parsers_radon, name)

    # Safety Parser exports (PLANNED)
    _safety_exports = {
        "SafetyParser",
        "CVSSScore",
        "Vulnerability",
        "DependencyVulnerability",
        "SafetyConfig",
        "SafetyReport",
    }
    if name in _safety_exports:
        from . import python_parsers_safety

        return getattr(python_parsers_safety, name)

    # Interrogate Parser exports (PLANNED)
    _interrogate_exports = {
        "InterrogateParser",
        "DocumentedItem",
        "DocumentationCoverage",
        "InterrogateConfig",
        "InterrogateReport",
    }
    if name in _interrogate_exports:
        from . import python_parsers_interrogate

        return getattr(python_parsers_interrogate, name)

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


# =============================================================================
# Convenience Functions
# =============================================================================
def get_available_parsers() -> list[str]:
    """
    Get list of all available parsers (completed and planned).

    Returns:
        List of available parser class names.
    """
    return [
        # Completed Parsers
        "PythonASTParser",
        "RuffParser",
        "MypyParser",
        "PylintParser",
        "BanditParser",
        "Flake8Parser",
        "PythonCodeQualityAnalyzer",
        "PydocstyleParser",
        "PycodestyleParser",
        "ProspectorParser",
        # Planned Parsers (NOT IMPLEMENTED - stubs only)
        "IsortParser",
        "VultureParser",
        "RadonParser",
        "SafetyParser",
        "InterrogateParser",
    ]


def get_parser_info() -> dict[str, dict[str, str]]:
    """
    Get information about each available parser.

    Returns:
        Dictionary mapping parser names to their descriptions and priorities.
    """
    return {
        "PythonASTParser": {
            "description": "Core AST analysis with symbol extraction and CFG/DFG",
            "priority": "P1 - Critical",
            "status": "✓ COMPLETED",
        },
        "RuffParser": {
            "description": "Fast Rust-based linter replacing Flake8/isort/pyupgrade",
            "priority": "P1 - Critical",
            "status": "✓ COMPLETED",
        },
        "MypyParser": {
            "description": "Static type checking and type coverage analysis",
            "priority": "P2 - High",
            "status": "✓ COMPLETED",
        },
        "PylintParser": {
            "description": "Comprehensive code quality and convention checking",
            "priority": "P2 - High",
            "status": "✓ COMPLETED",
        },
        "BanditParser": {
            "description": "Security vulnerability and CWE detection",
            "priority": "P2 - High",
            "status": "✓ COMPLETED",
        },
        "Flake8Parser": {
            "description": "Style checking with plugin ecosystem support",
            "priority": "P3 - Medium",
            "status": "✓ COMPLETED",
        },
        "PythonCodeQualityAnalyzer": {
            "description": "Complexity metrics, code smells, maintainability",
            "priority": "P3 - Medium",
            "status": "✓ COMPLETED",
        },
        "PydocstyleParser": {
            "description": "Docstring coverage and convention validation",
            "priority": "P3 - Medium",
            "status": "✓ COMPLETED",
        },
        "PycodestyleParser": {
            "description": "PEP 8 style guide enforcement",
            "priority": "P4 - Medium-Low",
            "status": "✓ COMPLETED",
        },
        "ProspectorParser": {
            "description": "Meta-linter aggregating multiple tool results",
            "priority": "P5 - Low",
            "status": "✓ COMPLETED",
        },
        # Planned Parsers (NOT IMPLEMENTED - stubs only)
        "IsortParser": {
            "description": "Import sorting and organization validation",
            "priority": "P2 - High",
            "status": "⏳ NOT IMPLEMENTED (stub)",
        },
        "VultureParser": {
            "description": "Dead code and unused symbol detection",
            "priority": "P2 - High",
            "status": "⏳ NOT IMPLEMENTED (stub)",
        },
        "RadonParser": {
            "description": "Code complexity metrics (CC, MI, cognitive)",
            "priority": "P2 - High",
            "status": "⏳ NOT IMPLEMENTED (stub)",
        },
        "SafetyParser": {
            "description": "Dependency security vulnerability checking",
            "priority": "P2 - High",
            "status": "⏳ NOT IMPLEMENTED (stub)",
        },
        "InterrogateParser": {
            "description": "Documentation coverage analysis",
            "priority": "P3 - Medium",
            "status": "⏳ NOT IMPLEMENTED (stub)",
        },
    }
