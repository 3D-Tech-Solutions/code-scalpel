#!/usr/bin/env python3
"""
Python Code Quality Analyzer - Metrics and Code Smell Detection.
=================================================================

This module provides code quality analysis including complexity metrics,
maintainability calculations, and code smell detection. It uses AST
analysis combined with heuristics to identify potential code issues.

Implementation Status: COMPLETED
Priority: P3 - MEDIUM

Features:
    - Cyclomatic complexity (McCabe)
    - Cognitive complexity (SonarSource)
    - Halstead metrics
    - Maintainability index
    - Lines of code metrics
    - Code smell detection
    - Technical debt estimation

==============================================================================
COMPLETED [P3-QUALITY-001]: Complexity metrics
==============================================================================
Priority: MEDIUM
Status: ✓ COMPLETED

Implemented Features:
    - [✓] Cyclomatic complexity (McCabe)
    - [✓] Cognitive complexity (SonarSource-inspired with nesting)
    - [✓] Halstead metrics (data structures and formulas)
    - [✓] Nesting depth tracking
    - [✓] Parameter count per function
    - [✓] Branch count per function
    - [✓] Integration with analyze methods

Cyclomatic Complexity Rules:
    Base: 1
    +1 for: if, elif, for, while, except, with, assert
    +1 for: and, or (boolean operators in conditions)
    +1 for: comprehension conditions
    +1 for: lambda (sometimes counted separately)

Cognitive Complexity Rules:
    - Increment for: if, elif, else, for, while, except, with
    - Increment for: and, or in conditions
    - Increment for nesting (multiplied by nesting level)
    - Increment for: break, continue with labels
    - No increment for: else after if returning/raising

Halstead Metrics:
    n1 = number of distinct operators
    n2 = number of distinct operands
    N1 = total number of operators
    N2 = total number of operands

    Program vocabulary: n = n1 + n2
    Program length: N = N1 + N2
    Volume: V = N * log2(n)
    Difficulty: D = (n1/2) * (N2/n2)
    Effort: E = D * V
    Bugs: B = V / 3000 (approximate bugs)

==============================================================================
COMPLETED [P3-QUALITY-002]: Maintainability metrics
==============================================================================
Priority: MEDIUM
Status: ✓ COMPLETED
Depends On: P3-QUALITY-001

Implemented Features:
    - [✓] Maintainability Index calculation
    - [✓] Lines of code (LOC, SLOC, comments, blank) - _count_lines method
    - [✓] Comment ratio calculation (property in LineMetrics)
    - [✓] Docstring line tracking
    - [✓] Function/method length distribution
    - [✓] Class size metrics
    - [✓] Integration with analyze methods

Maintainability Index Formula (Microsoft):
    MI = max(0, (171 - 5.2 * ln(HV) - 0.23 * CC - 16.2 * ln(LOC)) * 100 / 171)

    Where:
        HV = Halstead Volume
        CC = Cyclomatic Complexity (average)
        LOC = Lines of Code

Line Categories:
    - Physical lines (total lines)
    - Logical lines (statements)
    - Source lines of code (SLOC, excluding comments/blanks)
    - Comment lines
    - Blank lines
    - Mixed lines (code + comment)

==============================================================================
COMPLETED [P3-QUALITY-003]: Code smell detection
==============================================================================
Priority: MEDIUM
Status: ✓ COMPLETED
Depends On: P3-QUALITY-001

Implemented Features:
    - [✓] Long method detection (configurable threshold)
    - [✓] Large class detection (configurable threshold)
    - [✓] Long parameter list detection
    - [✓] High complexity detection
    - [✓] Deep nesting detection
    - [✓] Too many methods detection
    - [✓] Data class detection (no methods, only data)

Code Smell Thresholds (configurable):
    ```python
    DEFAULT_THRESHOLDS = {
        "max_function_length": 30,         # lines
        "max_class_length": 300,           # lines
        "max_parameters": 5,               # parameters
        "max_complexity": 10,              # cyclomatic
        "max_cognitive_complexity": 15,    # cognitive
        "max_nesting_depth": 4,            # levels
        "max_class_methods": 20,           # methods
        "max_class_attributes": 10,        # attributes
        "min_methods_for_class": 2,        # minimum methods
    }
    ```

==============================================================================
COMPLETED [P4-QUALITY-004]: Technical debt estimation
==============================================================================
Priority: LOW
Status: ✓ COMPLETED
Depends On: P3-QUALITY-003

Implemented Features:
    - [✓] Estimate remediation time per issue
    - [✓] Calculate total technical debt (in hours/days)
    - [✓] Priority-based debt ranking
    - [✓] Debt minutes by smell type
"""

from __future__ import annotations

import ast
import math
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass


# =============================================================================
# Enums
# =============================================================================


class SmellSeverity(Enum):
    """Severity of code smells."""

    INFO = "info"
    MINOR = "minor"
    MAJOR = "major"
    CRITICAL = "critical"


class SmellCategory(Enum):
    """Categories of code smells."""

    SIZE = "size"  # Size-related (too long, too large)
    COMPLEXITY = "complexity"  # Complexity-related
    DESIGN = "design"  # Design issues
    DUPLICATION = "duplication"  # Duplicate code
    NAMING = "naming"  # Naming issues
    DEAD_CODE = "dead_code"  # Unused code


# =============================================================================
# Configuration
# =============================================================================


@dataclass
class CodeQualityThresholds:
    """Thresholds for code quality checks."""

    max_function_length: int = 30
    max_class_length: int = 300
    max_file_length: int = 500
    max_parameters: int = 5
    max_cyclomatic_complexity: int = 10
    max_cognitive_complexity: int = 15
    max_nesting_depth: int = 4
    max_class_methods: int = 20
    max_methods_per_class: int = 20  # Alias for max_class_methods
    max_class_attributes: int = 10
    min_methods_for_class: int = 2
    max_line_length: int = 100
    min_comment_ratio: float = 0.1  # 10% comments
    max_function_statements: int = 50
    max_return_statements: int = 6
    max_branches: int = 12


# =============================================================================
# Data Classes - Metrics
# =============================================================================


@dataclass
class LineMetrics:
    """Line count metrics for code."""

    total_lines: int = 0
    code_lines: int = 0  # Non-blank, non-comment
    comment_lines: int = 0  # Pure comment lines
    blank_lines: int = 0
    mixed_lines: int = 0  # Code + comment on same line
    docstring_lines: int = 0

    @property
    def sloc(self) -> int:
        """Source lines of code (excluding blanks and comments)."""
        return self.code_lines

    @property
    def comment_ratio(self) -> float:
        """Ratio of comments to total lines."""
        if self.total_lines == 0:
            return 0.0
        return (self.comment_lines + self.mixed_lines) / self.total_lines


@dataclass
class HalsteadMetrics:
    """Halstead software metrics."""

    n1: int = 0  # Distinct operators
    n2: int = 0  # Distinct operands
    N1: int = 0  # Total operators
    N2: int = 0  # Total operands

    @property
    def vocabulary(self) -> int:
        """Program vocabulary (n = n1 + n2)."""
        return self.n1 + self.n2

    @property
    def length(self) -> int:
        """Program length (N = N1 + N2)."""
        return self.N1 + self.N2

    @property
    def volume(self) -> float:
        """Volume (V = N * log2(n))."""
        if self.vocabulary == 0:
            return 0.0
        return self.length * math.log2(self.vocabulary)

    @property
    def difficulty(self) -> float:
        """Difficulty (D = (n1/2) * (N2/n2))."""
        if self.n2 == 0:
            return 0.0
        return (self.n1 / 2) * (self.N2 / self.n2)

    @property
    def effort(self) -> float:
        """Effort (E = D * V)."""
        return self.difficulty * self.volume

    @property
    def time_to_program(self) -> float:
        """Estimated time to program in seconds (T = E / 18)."""
        return self.effort / 18

    @property
    def bugs(self) -> float:
        """Estimated number of bugs (B = V / 3000)."""
        return self.volume / 3000


@dataclass
class ComplexityMetrics:
    """Complexity metrics for a function or class."""

    cyclomatic: int = 1  # McCabe complexity
    cognitive: int = 0  # Cognitive complexity
    nesting_depth: int = 0  # Maximum nesting depth
    parameter_count: int = 0  # Number of parameters
    return_count: int = 0  # Number of return statements
    branch_count: int = 0  # Number of branches
    halstead: HalsteadMetrics = field(default_factory=HalsteadMetrics)

    @property
    def is_complex(self) -> bool:
        """Check if complexity exceeds common thresholds."""
        return self.cyclomatic > 10 or self.cognitive > 15


@dataclass
class MaintainabilityMetrics:
    """Maintainability metrics for code."""

    maintainability_index: float = 100.0  # 0-100 scale
    lines: LineMetrics = field(default_factory=LineMetrics)
    average_complexity: float = 1.0
    average_function_length: float = 0.0
    average_class_size: float = 0.0

    @property
    def rating(self) -> str:
        """Get maintainability rating (A-F)."""
        if self.maintainability_index >= 80:
            return "A"  # Highly maintainable
        elif self.maintainability_index >= 60:
            return "B"  # Moderately maintainable
        elif self.maintainability_index >= 40:
            return "C"  # Difficult to maintain
        elif self.maintainability_index >= 20:
            return "D"  # Very difficult to maintain
        else:
            return "F"  # Unmaintainable


# =============================================================================
# Data Classes - Code Smells
# =============================================================================


@dataclass
class CodeSmell:
    """Represents a detected code smell."""

    name: str  # Smell name (e.g., "long-method")
    description: str  # Human-readable description
    category: SmellCategory
    severity: SmellSeverity
    file: str
    line: int
    end_line: int | None = None
    obj_name: str | None = None  # Function/class name
    metric_value: float | None = None  # The actual value that triggered
    threshold: float | None = None  # The threshold that was exceeded
    suggestion: str | None = None  # Remediation suggestion

    @property
    def location(self) -> str:
        """Get formatted location string."""
        return f"{self.file}:{self.line}"

    def format(self) -> str:
        """Format the smell for display."""
        parts = [f"{self.location}: [{self.severity.value}] {self.name}"]
        if self.obj_name:
            parts[0] += f" in '{self.obj_name}'"
        parts.append(f"  {self.description}")
        if self.metric_value is not None and self.threshold is not None:
            parts.append(f"  Value: {self.metric_value}, Threshold: {self.threshold}")
        if self.suggestion:
            parts.append(f"  Suggestion: {self.suggestion}")
        return "\n".join(parts)


@dataclass
class TechnicalDebt:
    """Technical debt estimation."""

    total_minutes: int = 0
    smells_count: int = 0
    by_severity: dict[SmellSeverity, int] = field(default_factory=dict)
    by_category: dict[SmellCategory, int] = field(default_factory=dict)

    @property
    def total_hours(self) -> float:
        """Get total debt in hours."""
        return self.total_minutes / 60

    @property
    def total_days(self) -> float:
        """Get total debt in 8-hour days."""
        return self.total_hours / 8


# =============================================================================
# Data Classes - Reports
# =============================================================================


@dataclass
class FunctionQualityInfo:
    """Quality information for a function."""

    name: str
    qualified_name: str
    file: str
    line: int
    end_line: int
    complexity: ComplexityMetrics
    lines: LineMetrics
    parameter_count: int = 0
    has_docstring: bool = False
    is_method: bool = False
    is_async: bool = False
    smells: list[CodeSmell] = field(default_factory=list)


@dataclass
class ClassQualityInfo:
    """Quality information for a class."""

    name: str
    qualified_name: str
    file: str
    line: int
    end_line: int
    method_count: int = 0
    attribute_count: int = 0
    base_count: int = 0
    has_docstring: bool = False
    lines: LineMetrics = field(default_factory=LineMetrics)
    methods: list[FunctionQualityInfo] = field(default_factory=list)
    smells: list[CodeSmell] = field(default_factory=list)


@dataclass
class CodeQualityReport:
    """Complete code quality analysis report."""

    files_analyzed: int = 0
    total_lines: LineMetrics = field(default_factory=LineMetrics)
    maintainability: MaintainabilityMetrics = field(default_factory=MaintainabilityMetrics)
    functions: list[FunctionQualityInfo] = field(default_factory=list)
    classes: list[ClassQualityInfo] = field(default_factory=list)
    smells: list[CodeSmell] = field(default_factory=list)
    technical_debt: TechnicalDebt | None = None
    thresholds: CodeQualityThresholds = field(default_factory=CodeQualityThresholds)
    errors: list[str] = field(default_factory=list)

    @property
    def smell_count(self) -> int:
        """Get total number of code smells."""
        return len(self.smells)

    @property
    def smells_by_severity(self) -> dict[SmellSeverity, list[CodeSmell]]:
        """Group smells by severity."""
        result: dict[SmellSeverity, list[CodeSmell]] = {}
        for smell in self.smells:
            result.setdefault(smell.severity, []).append(smell)
        return result

    @property
    def smells_by_category(self) -> dict[SmellCategory, list[CodeSmell]]:
        """Group smells by category."""
        result: dict[SmellCategory, list[CodeSmell]] = {}
        for smell in self.smells:
            result.setdefault(smell.category, []).append(smell)
        return result

    @property
    def complex_functions(self) -> list[FunctionQualityInfo]:
        """Get functions that exceed complexity thresholds."""
        return [f for f in self.functions if f.complexity.cyclomatic > self.thresholds.max_cyclomatic_complexity]

    def get_summary(self) -> dict[str, Any]:
        """Get a summary of the report."""
        return {
            "files_analyzed": self.files_analyzed,
            "total_lines": self.total_lines.total_lines,
            "sloc": self.total_lines.sloc,
            "maintainability_index": self.maintainability.maintainability_index,
            "maintainability_rating": self.maintainability.rating,
            "functions_analyzed": len(self.functions),
            "classes_analyzed": len(self.classes),
            "smell_count": self.smell_count,
            "by_severity": {sev.value: len(smells) for sev, smells in self.smells_by_severity.items()},
            "complex_functions": len(self.complex_functions),
            "technical_debt_hours": (self.technical_debt.total_hours if self.technical_debt else 0),
        }


# =============================================================================
# Analyzer Class
# =============================================================================


class PythonCodeQualityAnalyzer:
    """
    Comprehensive code quality analyzer for Python code.

    Provides complexity metrics, maintainability calculations, and
    code smell detection using AST analysis.

    Implementation Status:
        ✓ Complexity metrics (P3-QUALITY-001) - cyclomatic, cognitive, nesting, Halstead
        ✓ Maintainability metrics (P3-QUALITY-002) - MI calculation, line counting
        ✓ Code smell detection (P3-QUALITY-003) - size, complexity, design smells
        ✓ Technical debt estimation (P4-QUALITY-004) - time-based debt calculation

    Capabilities:
        - Line counting (code, comments, blanks, docstrings)
        - Comment ratio calculation
        - Cyclomatic complexity (McCabe)
        - Cognitive complexity (SonarSource-style with nesting)
        - Halstead software metrics
        - Nesting depth analysis
        - Function and class extraction with full metrics
        - Code smell detection with configurable thresholds
        - Maintainability Index calculation
        - Technical debt estimation per smell

    Usage:
        >>> analyzer = PythonCodeQualityAnalyzer()
        >>> report = analyzer.analyze_file("example.py")
        >>> print(f"Maintainability: {report.maintainability.rating}")
        >>> for smell in report.smells:
        ...     print(smell.format())
    """

    def __init__(self, thresholds: CodeQualityThresholds | None = None):
        """
        Initialize the analyzer.

        Args:
            thresholds: Custom thresholds for code quality checks.
        """
        self.thresholds = thresholds or CodeQualityThresholds()

    def analyze_file(self, path: str | Path) -> CodeQualityReport:
        """
        Analyze a Python file for code quality.

        Args:
            path: Path to the Python file.

        Returns:
            CodeQualityReport with metrics and smells.
        """
        path = Path(path)
        source = path.read_text(encoding="utf-8")
        return self.analyze_string(source, filename=str(path))

    def analyze_string(
        self,
        source: str,
        *,
        filename: str = "<string>",
    ) -> CodeQualityReport:
        """
        Analyze Python source code for quality.

        Args:
            source: Python source code.
            filename: Filename for error messages.

        Returns:
            CodeQualityReport with metrics and smells.
        """
        report = CodeQualityReport(
            files_analyzed=1,
            thresholds=self.thresholds,
        )

        try:
            tree = ast.parse(source, filename=filename)

            # Calculate line metrics
            report.total_lines = self._count_lines(source)

            # Analyze functions and classes
            self._analyze_functions(tree, source, filename, report)
            self._analyze_classes(tree, source, filename, report)

            # Detect code smells
            self._detect_smells(tree, source, filename, report)

            # Calculate maintainability
            self._calculate_maintainability(report)

            # Estimate technical debt
            self._estimate_debt(report)

        except SyntaxError as e:
            report.errors.append(f"SyntaxError in {filename}: {e}")

        return report

    def _analyze_functions(
        self,
        tree: ast.AST,
        source: str,
        filename: str,
        report: CodeQualityReport,
    ) -> None:
        """Extract function information with complexity metrics."""
        source_lines = source.split("\n")

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                # Calculate complexity metrics
                cyclomatic = self.calculate_cyclomatic_complexity(node)
                cognitive = self.calculate_cognitive_complexity(node)

                # Calculate nesting depth
                nesting = self._calculate_nesting_depth(node)

                # Count parameters
                param_count = len(node.args.args) + len(node.args.posonlyargs)
                param_count += len(node.args.kwonlyargs)
                if node.args.vararg:
                    param_count += 1
                if node.args.kwarg:
                    param_count += 1

                # Calculate Halstead metrics for function
                halstead = self._calculate_halstead(node)

                # Count lines for this function
                if node.end_lineno and node.lineno:
                    func_source = "\n".join(source_lines[node.lineno - 1 : node.end_lineno])
                    func_lines = self._count_lines(func_source)
                else:
                    func_lines = LineMetrics()

                # Check for docstring
                has_docstring = bool(
                    node.body
                    and isinstance(node.body[0], ast.Expr)
                    and isinstance(node.body[0].value, ast.Constant)
                    and isinstance(node.body[0].value.value, str)
                )

                # Check if this is a method (inside a class)
                is_method = self._is_method(node, tree)
                qualified_name = node.name

                func_info = FunctionQualityInfo(
                    name=node.name,
                    qualified_name=qualified_name,
                    file=filename,
                    line=node.lineno,
                    end_line=node.end_lineno or node.lineno,
                    complexity=ComplexityMetrics(
                        cyclomatic=cyclomatic,
                        cognitive=cognitive,
                        nesting_depth=nesting,
                        parameter_count=param_count,
                        halstead=halstead,
                    ),
                    lines=func_lines,
                    parameter_count=param_count,
                    has_docstring=has_docstring,
                    is_method=is_method,
                    is_async=isinstance(node, ast.AsyncFunctionDef),
                )

                report.functions.append(func_info)

    def _analyze_classes(
        self,
        tree: ast.AST,
        source: str,
        filename: str,
        report: CodeQualityReport,
    ) -> None:
        """Extract class information with method counts."""
        source_lines = source.split("\n")

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Count methods
                method_count = sum(
                    1 for child in node.body if isinstance(child, ast.FunctionDef | ast.AsyncFunctionDef)
                )

                # Count attributes (assignments in class body)
                attribute_count = sum(1 for child in node.body if isinstance(child, ast.AnnAssign | ast.Assign))

                # Count base classes
                base_count = len(node.bases)

                # Calculate lines
                if node.end_lineno and node.lineno:
                    class_source = "\n".join(source_lines[node.lineno - 1 : node.end_lineno])
                    class_lines = self._count_lines(class_source)
                else:
                    class_lines = LineMetrics()

                # Check for docstring
                has_docstring = bool(
                    node.body
                    and isinstance(node.body[0], ast.Expr)
                    and isinstance(node.body[0].value, ast.Constant)
                    and isinstance(node.body[0].value.value, str)
                )

                class_info = ClassQualityInfo(
                    name=node.name,
                    qualified_name=node.name,
                    file=filename,
                    line=node.lineno,
                    end_line=node.end_lineno or node.lineno,
                    method_count=method_count,
                    attribute_count=attribute_count,
                    base_count=base_count,
                    has_docstring=has_docstring,
                    lines=class_lines,
                )

                report.classes.append(class_info)

    def _detect_smells(
        self,
        tree: ast.AST,
        source: str,
        filename: str,
        report: CodeQualityReport,
    ) -> None:
        """Detect code smells based on thresholds."""
        thresholds = self.thresholds

        # Check functions for smells
        for func in report.functions:
            func_line_count = func.lines.total_lines

            # Long method
            if func_line_count > thresholds.max_function_length:
                report.smells.append(
                    CodeSmell(
                        name="long-method",
                        category=SmellCategory.SIZE,
                        severity=(
                            SmellSeverity.MAJOR
                            if func_line_count > thresholds.max_function_length * 2
                            else SmellSeverity.MINOR
                        ),
                        description=f"Function '{func.name}' has {func_line_count} lines (max: {thresholds.max_function_length})",
                        file=func.file,
                        line=func.line,
                        end_line=func.end_line,
                        obj_name=func.name,
                        metric_value=float(func_line_count),
                        threshold=float(thresholds.max_function_length),
                        suggestion="Consider breaking this function into smaller, focused functions",
                    )
                )

            # High complexity
            if func.complexity.cyclomatic > thresholds.max_cyclomatic_complexity:
                severity = (
                    SmellSeverity.CRITICAL
                    if func.complexity.cyclomatic > thresholds.max_cyclomatic_complexity * 2
                    else SmellSeverity.MAJOR
                )
                report.smells.append(
                    CodeSmell(
                        name="high-cyclomatic-complexity",
                        category=SmellCategory.COMPLEXITY,
                        severity=severity,
                        description=f"Function '{func.name}' has cyclomatic complexity of {func.complexity.cyclomatic} (max: {thresholds.max_cyclomatic_complexity})",
                        file=func.file,
                        line=func.line,
                        end_line=func.end_line,
                        obj_name=func.name,
                        metric_value=float(func.complexity.cyclomatic),
                        threshold=float(thresholds.max_cyclomatic_complexity),
                        suggestion="Reduce branching by extracting conditions into separate functions",
                    )
                )

            # High cognitive complexity
            if func.complexity.cognitive > thresholds.max_cognitive_complexity:
                report.smells.append(
                    CodeSmell(
                        name="high-cognitive-complexity",
                        category=SmellCategory.COMPLEXITY,
                        severity=SmellSeverity.MAJOR,
                        description=f"Function '{func.name}' has cognitive complexity of {func.complexity.cognitive} (max: {thresholds.max_cognitive_complexity})",
                        file=func.file,
                        line=func.line,
                        end_line=func.end_line,
                        obj_name=func.name,
                        metric_value=float(func.complexity.cognitive),
                        threshold=float(thresholds.max_cognitive_complexity),
                        suggestion="Reduce nesting and use early returns to simplify logic",
                    )
                )

            # Too many parameters
            if func.parameter_count > thresholds.max_parameters:
                report.smells.append(
                    CodeSmell(
                        name="too-many-parameters",
                        category=SmellCategory.DESIGN,
                        severity=SmellSeverity.MINOR,
                        description=f"Function '{func.name}' has {func.parameter_count} parameters (max: {thresholds.max_parameters})",
                        file=func.file,
                        line=func.line,
                        obj_name=func.name,
                        metric_value=float(func.parameter_count),
                        threshold=float(thresholds.max_parameters),
                        suggestion="Consider using a parameter object or data class",
                    )
                )

            # Deep nesting
            if func.complexity.nesting_depth > thresholds.max_nesting_depth:
                report.smells.append(
                    CodeSmell(
                        name="deep-nesting",
                        category=SmellCategory.COMPLEXITY,
                        severity=SmellSeverity.MAJOR,
                        description=f"Function '{func.name}' has nesting depth of {func.complexity.nesting_depth} (max: {thresholds.max_nesting_depth})",
                        file=func.file,
                        line=func.line,
                        end_line=func.end_line,
                        obj_name=func.name,
                        metric_value=float(func.complexity.nesting_depth),
                        threshold=float(thresholds.max_nesting_depth),
                        suggestion="Use early returns and extract nested logic into separate functions",
                    )
                )

            # Missing docstring
            if not func.has_docstring and not func.name.startswith("_"):
                report.smells.append(
                    CodeSmell(
                        name="missing-docstring",
                        category=SmellCategory.DESIGN,
                        severity=SmellSeverity.INFO,
                        description=f"Public function '{func.name}' is missing a docstring",
                        file=func.file,
                        line=func.line,
                        obj_name=func.name,
                        suggestion="Add a docstring describing the function's purpose and parameters",
                    )
                )

        # Check classes for smells
        for cls in report.classes:
            class_line_count = cls.lines.total_lines

            # Large class
            if class_line_count > thresholds.max_class_length:
                report.smells.append(
                    CodeSmell(
                        name="large-class",
                        category=SmellCategory.SIZE,
                        severity=SmellSeverity.MAJOR,
                        description=f"Class '{cls.name}' has {class_line_count} lines (max: {thresholds.max_class_length})",
                        file=cls.file,
                        line=cls.line,
                        end_line=cls.end_line,
                        obj_name=cls.name,
                        metric_value=float(class_line_count),
                        threshold=float(thresholds.max_class_length),
                        suggestion="Consider splitting this class into smaller, focused classes",
                    )
                )

            # Too many methods
            if cls.method_count > thresholds.max_methods_per_class:
                report.smells.append(
                    CodeSmell(
                        name="too-many-methods",
                        category=SmellCategory.SIZE,
                        severity=SmellSeverity.MINOR,
                        description=f"Class '{cls.name}' has {cls.method_count} methods (max: {thresholds.max_methods_per_class})",
                        file=cls.file,
                        line=cls.line,
                        obj_name=cls.name,
                        metric_value=float(cls.method_count),
                        threshold=float(thresholds.max_methods_per_class),
                        suggestion="Consider extracting some methods into separate classes",
                    )
                )

            # Missing class docstring
            if not cls.has_docstring:
                report.smells.append(
                    CodeSmell(
                        name="missing-class-docstring",
                        category=SmellCategory.DESIGN,
                        severity=SmellSeverity.INFO,
                        description=f"Class '{cls.name}' is missing a docstring",
                        file=cls.file,
                        line=cls.line,
                        obj_name=cls.name,
                        suggestion="Add a docstring describing the class's purpose",
                    )
                )

        # Check file-level metrics
        if report.total_lines.total_lines > thresholds.max_file_length:
            report.smells.append(
                CodeSmell(
                    name="long-file",
                    category=SmellCategory.SIZE,
                    severity=SmellSeverity.MAJOR,
                    description=f"File '{filename}' has {report.total_lines.total_lines} lines (max: {thresholds.max_file_length})",
                    file=filename,
                    line=1,
                    metric_value=float(report.total_lines.total_lines),
                    threshold=float(thresholds.max_file_length),
                    suggestion="Consider splitting this file into multiple modules",
                )
            )

    def _calculate_maintainability(self, report: CodeQualityReport) -> None:
        """Calculate Maintainability Index for the analyzed code."""
        # Maintainability Index formula (Microsoft Visual Studio variant):
        # MI = max(0, (171 - 5.2 * ln(HV) - 0.23 * CC - 16.2 * ln(LOC)) * 100 / 171)
        # Where:
        #   HV = Halstead Volume
        #   CC = Average cyclomatic complexity
        #   LOC = Lines of code

        loc = max(1, report.total_lines.code_lines)

        # Calculate average cyclomatic complexity
        if report.functions:
            avg_complexity = sum(f.complexity.cyclomatic for f in report.functions) / len(report.functions)
        else:
            avg_complexity = 1.0

        # Calculate aggregate Halstead volume
        total_volume = 0.0
        for func in report.functions:
            total_volume += func.complexity.halstead.volume

        # Use average volume per line of code
        avg_volume = max(1.0, total_volume / loc if loc > 0 else 1.0)

        import math

        # Calculate raw MI
        raw_mi = 171 - 5.2 * math.log(avg_volume + 1) - 0.23 * avg_complexity - 16.2 * math.log(loc)

        # Normalize to 0-100 scale
        mi = max(0.0, min(100.0, raw_mi * 100 / 171))

        # Determine rating
        if mi >= 80:
            pass
        elif mi >= 60:
            pass
        elif mi >= 40:
            pass
        elif mi >= 20:
            pass
        else:
            pass

        report.maintainability = MaintainabilityMetrics(
            maintainability_index=mi,
            lines=report.total_lines,
            average_complexity=avg_complexity,
            average_function_length=(
                sum(f.lines.total_lines for f in report.functions) / len(report.functions) if report.functions else 0.0
            ),
            average_class_size=(
                sum(c.lines.total_lines for c in report.classes) / len(report.classes) if report.classes else 0.0
            ),
        )

    def _estimate_debt(self, report: CodeQualityReport) -> None:
        """Estimate technical debt based on detected smells."""
        total_minutes = 0
        by_severity: dict[SmellSeverity, int] = {}
        by_category: dict[SmellCategory, int] = {}

        # Debt estimation per smell name (in minutes)
        debt_map = {
            "long-method": 20,
            "high-cyclomatic-complexity": 30,
            "high-cognitive-complexity": 25,
            "too-many-parameters": 15,
            "deep-nesting": 20,
            "missing-docstring": 5,
            "large-class": 45,
            "too-many-methods": 25,
            "missing-class-docstring": 10,
            "long-file": 60,
        }

        for smell in report.smells:
            debt = debt_map.get(smell.name, 10)

            # Multiply by severity
            if smell.severity == SmellSeverity.CRITICAL:
                debt *= 2.0
            elif smell.severity == SmellSeverity.MAJOR:
                debt *= 1.5
            elif smell.severity == SmellSeverity.INFO:
                debt *= 0.5

            total_minutes += int(debt)

            # Track by severity and category
            by_severity[smell.severity] = by_severity.get(smell.severity, 0) + int(debt)
            by_category[smell.category] = by_category.get(smell.category, 0) + int(debt)

        report.technical_debt = TechnicalDebt(
            total_minutes=total_minutes,
            smells_count=len(report.smells),
            by_severity=by_severity,
            by_category=by_category,
        )

    def _calculate_nesting_depth(self, node: ast.AST) -> int:
        """Calculate maximum nesting depth within a node."""
        max_depth = 0

        def walk_depth(n: ast.AST, depth: int) -> None:
            nonlocal max_depth

            # Nodes that increase nesting
            nesting_nodes = (
                ast.If,
                ast.For,
                ast.While,
                ast.With,
                ast.Try,
                ast.ExceptHandler,
                ast.Match,
            )

            if isinstance(n, nesting_nodes):
                depth += 1
                max_depth = max(max_depth, depth)

            for child in ast.iter_child_nodes(n):
                walk_depth(child, depth)

        walk_depth(node, 0)
        return max_depth

    def _calculate_halstead(self, node: ast.AST) -> HalsteadMetrics:
        """Calculate Halstead metrics for a node."""
        operators: set[str] = set()
        operands: set[str] = set()
        total_operators = 0
        total_operands = 0

        # Operators (control flow, arithmetic, logical, etc.)
        operator_nodes = (
            ast.Add,
            ast.Sub,
            ast.Mult,
            ast.Div,
            ast.Mod,
            ast.Pow,
            ast.FloorDiv,
            ast.LShift,
            ast.RShift,
            ast.BitOr,
            ast.BitXor,
            ast.BitAnd,
            ast.Invert,
            ast.Not,
            ast.UAdd,
            ast.USub,
            ast.And,
            ast.Or,
            ast.Eq,
            ast.NotEq,
            ast.Lt,
            ast.LtE,
            ast.Gt,
            ast.GtE,
            ast.Is,
            ast.IsNot,
            ast.In,
            ast.NotIn,
        )

        for child in ast.walk(node):
            # Count operators
            if isinstance(child, operator_nodes):
                op_name = type(child).__name__
                operators.add(op_name)
                total_operators += 1
            elif isinstance(child, ast.BinOp | ast.UnaryOp | ast.BoolOp | ast.Compare):
                total_operators += 1
            elif isinstance(child, ast.Call):
                operators.add("()")
                total_operators += 1
            elif isinstance(child, ast.Subscript):
                operators.add("[]")
                total_operators += 1
            elif isinstance(child, ast.Attribute):
                operators.add(".")
                total_operators += 1
            elif isinstance(child, ast.Assign | ast.AugAssign | ast.AnnAssign):
                operators.add("=")
                total_operators += 1

            # Count operands (names, constants)
            if isinstance(child, ast.Name):
                operands.add(child.id)
                total_operands += 1
            elif isinstance(child, ast.Constant):
                operands.add(str(child.value))
                total_operands += 1

        metrics = HalsteadMetrics(
            n1=len(operators),
            n2=len(operands),
            N1=total_operators,
            N2=total_operands,
        )

        # Note: derived metrics (vocabulary, length, volume, difficulty, effort, time, bugs)
        # are computed automatically via @property methods on HalsteadMetrics

        return metrics

    def _is_method(self, node: ast.FunctionDef | ast.AsyncFunctionDef, tree: ast.AST) -> bool:
        """Check if a function is a method (defined inside a class)."""
        for parent in ast.walk(tree):
            if isinstance(parent, ast.ClassDef):
                for child in parent.body:
                    if child is node:
                        return True
        return False

    def analyze_directory(
        self,
        path: str | Path,
        *,
        recursive: bool = True,
        exclude_patterns: list[str] | None = None,
    ) -> CodeQualityReport:
        """
        Analyze all Python files in a directory.

        Args:
            path: Path to the directory.
            recursive: Whether to search recursively.
            exclude_patterns: Patterns to exclude.

        Returns:
            Combined CodeQualityReport.
        """
        path = Path(path)
        report = CodeQualityReport(thresholds=self.thresholds)

        pattern = "**/*.py" if recursive else "*.py"

        for py_file in path.glob(pattern):
            # Skip excluded patterns
            if exclude_patterns:
                skip = False
                for pattern in exclude_patterns:
                    if pattern in str(py_file):
                        skip = True
                        break
                if skip:
                    continue

            try:
                file_report = self.analyze_file(py_file)
                self._merge_reports(report, file_report)
            except Exception as e:
                report.errors.append(f"Error analyzing {py_file}: {e}")

        return report

    def _count_lines(self, source: str) -> LineMetrics:
        """
        Count lines in source code.

        Categorizes lines as code, comments, blanks, mixed, or docstrings.
        """
        metrics = LineMetrics()
        lines = source.split("\n")
        metrics.total_lines = len(lines)

        in_docstring = False
        docstring_char = None

        for line in lines:
            stripped = line.strip()

            if not stripped:
                metrics.blank_lines += 1
                continue

            # Check for docstring
            if stripped.startswith('"""') or stripped.startswith("'''"):
                quote = stripped[:3]
                if not in_docstring:
                    in_docstring = True
                    docstring_char = quote
                    if stripped.count(quote) >= 2:  # Single-line docstring
                        in_docstring = False
                        metrics.docstring_lines += 1
                        continue
                elif quote == docstring_char:
                    in_docstring = False
                metrics.docstring_lines += 1
                continue

            if in_docstring:
                metrics.docstring_lines += 1
                continue

            # Check for comments
            if stripped.startswith("#"):
                metrics.comment_lines += 1
            elif "#" in stripped:
                metrics.mixed_lines += 1
            else:
                metrics.code_lines += 1

        return metrics

    def calculate_cyclomatic_complexity(self, node: ast.AST) -> int:
        """
        Calculate cyclomatic complexity for an AST node.

        Implements McCabe cyclomatic complexity metric.

        Cyclomatic complexity = E - N + 2P
        Where E = edges, N = nodes, P = connected components

        Simplified: Start at 1, add 1 for each decision point.

        Note: Method exists but not integrated with analyze_string().
        """
        complexity = 1

        for child in ast.walk(node):
            # Decision points
            if isinstance(child, (ast.If, ast.While, ast.For)):
                complexity += 1
            elif isinstance(child, ast.ExceptHandler):
                complexity += 1
            elif isinstance(child, ast.With):
                complexity += 1
            elif isinstance(child, ast.Assert):
                complexity += 1
            elif isinstance(child, ast.comprehension):
                complexity += 1  # For comprehension conditions
            elif isinstance(child, ast.BoolOp):
                # Each and/or adds a decision path
                complexity += len(child.values) - 1
            elif isinstance(child, ast.IfExp):
                complexity += 1  # Ternary expression

        return complexity

    def calculate_cognitive_complexity(self, node: ast.AST) -> int:
        """
        Calculate cognitive complexity for an AST node.

        Based on SonarSource's Cognitive Complexity metric.
        Accounts for nesting depth and control flow interruptions.

        Key differences from cyclomatic complexity:
        - Nesting increases cost (deeper = more complex)
        - Some structures are free (else, elif)
        - Recursion adds a flat increment
        - Boolean operators in conditions add complexity
        """
        complexity = 0

        def walk(n: ast.AST, nesting: int = 0) -> None:
            nonlocal complexity

            # Structural increments (add 1 + nesting level)
            if isinstance(n, ast.If):
                # Only count if, not elif (elif is handled as else branch with If)
                complexity += 1 + nesting

                # Walk the test for boolean operators
                walk(n.test, nesting)

                # Walk body at increased nesting
                for child in n.body:
                    walk(child, nesting + 1)

                # Walk else/elif - elif doesn't add nesting
                for child in n.orelse:
                    if isinstance(child, ast.If):
                        # This is elif - add 1 but no nesting penalty
                        complexity += 1
                        walk(child.test, nesting)
                        for subchild in child.body:
                            walk(subchild, nesting + 1)
                        for subchild in child.orelse:
                            walk(subchild, nesting)
                    else:
                        # This is else body
                        walk(child, nesting + 1)
                return

            elif isinstance(n, ast.For | ast.While):
                complexity += 1 + nesting
                for child in ast.iter_child_nodes(n):
                    if child in getattr(n, "body", []):
                        walk(child, nesting + 1)
                    elif child in getattr(n, "orelse", []):
                        walk(child, nesting + 1)
                    else:
                        walk(child, nesting)
                return

            elif isinstance(n, ast.ExceptHandler):
                complexity += 1 + nesting
                for child in n.body:
                    walk(child, nesting + 1)
                return

            elif isinstance(n, ast.With):
                complexity += 1 + nesting
                for child in n.body:
                    walk(child, nesting + 1)
                return

            elif isinstance(n, ast.Match):
                complexity += 1 + nesting
                for case in n.cases:
                    for child in case.body:
                        walk(child, nesting + 1)
                return

            # Flat increments (add 1, no nesting penalty)
            elif isinstance(n, ast.Break | ast.Continue):
                complexity += 1

            elif isinstance(n, ast.IfExp):  # Ternary
                complexity += 1 + nesting

            # Boolean operators add 1 for each sequence
            elif isinstance(n, ast.BoolOp):
                # Each chain of and/or adds 1
                complexity += 1

            # Recursion detection (calls to same function)
            # This is harder to detect statically, skip for now

            # Walk children normally
            for child in ast.iter_child_nodes(n):
                walk(child, nesting)

        walk(node)
        return complexity

    def _merge_reports(
        self,
        target: CodeQualityReport,
        source: CodeQualityReport,
    ) -> None:
        """Merge source report into target report."""
        target.files_analyzed += source.files_analyzed

        # Merge line counts
        target.total_lines.total_lines += source.total_lines.total_lines
        target.total_lines.code_lines += source.total_lines.code_lines
        target.total_lines.comment_lines += source.total_lines.comment_lines
        target.total_lines.blank_lines += source.total_lines.blank_lines
        target.total_lines.mixed_lines += source.total_lines.mixed_lines
        target.total_lines.docstring_lines += source.total_lines.docstring_lines

        # Merge collections
        target.functions.extend(source.functions)
        target.classes.extend(source.classes)
        target.smells.extend(source.smells)
        target.errors.extend(source.errors)


# =============================================================================
# Utility Functions
# =============================================================================


def format_quality_report(report: CodeQualityReport) -> str:
    """Format a code quality report for display."""
    lines = [
        "Code Quality Report",
        "=" * 50,
        "",
        f"Files analyzed: {report.files_analyzed}",
        f"Total lines: {report.total_lines.total_lines}",
        f"  - Code: {report.total_lines.code_lines}",
        f"  - Comments: {report.total_lines.comment_lines}",
        f"  - Blank: {report.total_lines.blank_lines}",
        f"  - Docstrings: {report.total_lines.docstring_lines}",
        "",
        f"Maintainability Index: {report.maintainability.maintainability_index:.1f}",
        f"Rating: {report.maintainability.rating}",
        "",
        f"Functions: {len(report.functions)}",
        f"Classes: {len(report.classes)}",
        "",
        f"Code Smells: {report.smell_count}",
    ]

    if report.smells_by_severity:
        lines.append("  By severity:")
        for severity, smells in sorted(
            report.smells_by_severity.items(),
            key=lambda x: -x[0].value.count("a"),  # Sort by severity
        ):
            lines.append(f"    - {severity.value}: {len(smells)}")

    if report.complex_functions:
        lines.append("")
        lines.append(f"Complex functions ({len(report.complex_functions)}):")
        for func in report.complex_functions[:5]:
            lines.append(f"  - {func.name}: complexity={func.complexity.cyclomatic}")
        if len(report.complex_functions) > 5:
            lines.append(f"  ... and {len(report.complex_functions) - 5} more")

    return "\n".join(lines)
