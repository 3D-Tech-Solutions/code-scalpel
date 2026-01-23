"""
Javalang Java Parser - Pure Python Java AST parsing.
Uses javalang library for detailed Java code analysis without native dependencies.
Provides comprehensive metrics, complexity analysis, and code issue detection.
Implemented Features:
- Cognitive complexity calculation (more accurate than cyclomatic)
- Cyclomatic complexity calculation
- Method call graphs for dependency analysis
- Halstead complexity metrics (vocabulary, volume, difficulty, effort)
- Type hierarchy and inheritance relationships extraction
- Design pattern detection (Singleton, Factory, Builder, etc.)
- Maintainability index calculation
- Magic number detection
- Nesting depth analysis (warns on depth > 4)
- Lines of code metrics (LOC, SLOC, CLOC)
- Empty method and dead code detection
- Try-catch-finally pattern extraction
- Thread safety analysis (synchronized blocks, volatile fields)
- SQL injection vulnerability detection in string concatenation
Note: javalang library has limited support for newer Java features.
For Java 14+ records, Java 17+ sealed classes, and Java 21+ pattern matching,
use the tree-sitter parser instead.
"""

import math
import re
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import javalang  # type: ignore[import-untyped]
import javalang.ast  # type: ignore[import-untyped]
import javalang.tree  # type: ignore[import-untyped]

from ..base_parser import BaseParser, Language, ParseResult, PreprocessorConfig

# Type aliases for javalang types (library lacks type stubs)
JavaNode = Any  # javalang.ast.Node
JavaCompilationUnit = Any  # javalang.tree.CompilationUnit


@dataclass
class MethodCallInfo:
    """Information about a method call."""

    caller_class: str
    caller_method: str
    callee_class: str | None  # None if unknown/same class
    callee_method: str
    line: int


@dataclass
class MethodMetrics:
    """Comprehensive metrics for a single method."""

    name: str
    class_name: str
    line: int
    cyclomatic_complexity: int = 1
    cognitive_complexity: int = 0
    max_nesting_depth: int = 0
    parameter_count: int = 0
    loc: int = 0  # Lines of code
    is_empty: bool = False
    is_synchronized: bool = False
    calls: list[str] = field(default_factory=list)  # Methods this method calls


@dataclass
class HalsteadMetrics:
    """Halstead complexity metrics."""

    n1: int = 0  # Number of distinct operators
    n2: int = 0  # Number of distinct operands
    N1: int = 0  # Total number of operators
    N2: int = 0  # Total number of operands

    @property
    def vocabulary(self) -> int:
        """Program vocabulary (n = n1 + n2)."""
        return self.n1 + self.n2

    @property
    def length(self) -> int:
        """Program length (N = N1 + N2)."""
        return self.N1 + self.N2

    @property
    def calculated_length(self) -> float:
        """Calculated program length."""
        if self.n1 == 0 or self.n2 == 0:
            return 0
        return self.n1 * math.log2(self.n1) + self.n2 * math.log2(self.n2)

    @property
    def volume(self) -> float:
        """Program volume (V = N * log2(n))."""
        if self.vocabulary == 0:
            return 0
        return self.length * math.log2(self.vocabulary)

    @property
    def difficulty(self) -> float:
        """Program difficulty (D = (n1/2) * (N2/n2))."""
        if self.n2 == 0:
            return 0
        return (self.n1 / 2) * (self.N2 / self.n2)

    @property
    def effort(self) -> float:
        """Programming effort (E = D * V)."""
        return self.difficulty * self.volume

    @property
    def time_to_program(self) -> float:
        """Time to program in seconds (T = E / 18)."""
        return self.effort / 18

    @property
    def bugs_estimate(self) -> float:
        """Estimated number of bugs (B = V / 3000)."""
        return self.volume / 3000


@dataclass
class TypeHierarchy:
    """Represents a class/interface in the type hierarchy."""

    name: str
    superclass: str | None = None
    interfaces: list[str] = field(default_factory=list)
    is_interface: bool = False
    is_abstract: bool = False
    subclasses: list[str] = field(default_factory=list)  # Populated after full analysis


@dataclass
class DesignPatternMatch:
    """Represents a detected design pattern."""

    pattern_name: str  # "Singleton", "Factory", "Builder", etc.
    class_name: str
    confidence: float  # 0.0 to 1.0
    evidence: list[str] = field(default_factory=list)


@dataclass
class TryCatchPattern:
    """Information about try-catch-finally usage."""

    line: int
    has_finally: bool
    caught_exceptions: list[str] = field(default_factory=list)
    is_empty_catch: bool = False
    catch_just_logs: bool = False


@dataclass
class ThreadSafetyInfo:
    """Thread safety analysis results."""

    synchronized_methods: list[str] = field(default_factory=list)
    synchronized_blocks: int = 0
    volatile_fields: list[str] = field(default_factory=list)
    potential_race_conditions: list[str] = field(default_factory=list)


@dataclass
class SecurityIssue:
    """Security vulnerability detection."""

    issue_type: str  # "SQL_INJECTION", "HARDCODED_SECRET", etc.
    line: int
    message: str
    severity: str  # "HIGH", "MEDIUM", "LOW"


@dataclass
class CodeMetrics:
    """Comprehensive code metrics for a Java file."""

    # Lines of code
    total_lines: int = 0
    source_lines: int = 0  # SLOC - non-blank, non-comment
    comment_lines: int = 0  # CLOC
    blank_lines: int = 0

    # Complexity
    total_cyclomatic: int = 0
    total_cognitive: int = 0
    max_cyclomatic: int = 0
    max_cognitive: int = 0
    avg_cyclomatic: float = 0.0
    avg_cognitive: float = 0.0
    max_nesting_depth: int = 0

    # Halstead
    halstead: HalsteadMetrics = field(default_factory=HalsteadMetrics)

    # Maintainability
    maintainability_index: float = 0.0

    # Counts
    class_count: int = 0
    interface_count: int = 0
    method_count: int = 0
    field_count: int = 0

    # Issues
    magic_numbers: list[tuple[int, str]] = field(default_factory=list)  # (line, value)
    empty_methods: list[str] = field(default_factory=list)
    deeply_nested: list[tuple[str, int]] = field(default_factory=list)  # (method, depth)


class JavaParser(BaseParser):
    """
    JavaParser is responsible for parsing and analyzing Java code.

    This class uses the javalang library to parse Java code into an Abstract Syntax Tree (AST),
    performs preprocessing steps, analyzes the code structure, and checks for potential issues.

    Provides comprehensive analysis including:
    - Cyclomatic and cognitive complexity
    - Halstead metrics
    - Method call graphs
    - Design pattern detection
    - Thread safety analysis
    - Security vulnerability detection
    - Maintainability index
    """

    # Operators for Halstead metrics
    JAVA_OPERATORS = {
        "+",
        "-",
        "*",
        "/",
        "%",
        "++",
        "--",
        "==",
        "!=",
        ">",
        "<",
        ">=",
        "<=",
        "&&",
        "||",
        "!",
        "&",
        "|",
        "^",
        "~",
        "<<",
        ">>",
        ">>>",
        "=",
        "+=",
        "-=",
        "*=",
        "/=",
        "%=",
        "&=",
        "|=",
        "^=",
        "<<=",
        ">>=",
        ">>>=",
        "?",
        ":",
        "->",
        "::",
        ".",
        ",",
        ";",
        "(",
        ")",
        "[",
        "]",
        "{",
        "}",
        "new",
        "instanceof",
        "throw",
        "throws",
        "return",
        "break",
        "continue",
        "if",
        "else",
        "for",
        "while",
        "do",
        "switch",
        "case",
        "default",
        "try",
        "catch",
        "finally",
        "synchronized",
    }

    # Magic number exceptions (commonly acceptable)
    ACCEPTABLE_NUMBERS = {"-1", "0", "1", "2", "10", "100", "1000"}

    def __init__(self):
        """Initialize the JavaParser."""
        super().__init__()
        self._method_calls: list[MethodCallInfo] = []
        self._type_hierarchy: dict[str, TypeHierarchy] = {}
        self._current_class: str | None = None
        self._current_method: str | None = None

    def _preprocess_java_code(self, code: str, config: PreprocessorConfig | None) -> str:
        """
        Preprocess the Java code.

        :param code: The Java code to preprocess.
        :param config: Configuration for preprocessing.
        :return: The preprocessed code.
        """
        if config is None:
            config = PreprocessorConfig(remove_comments=False, normalize_whitespace=False)
        if config.remove_comments:
            code = self._remove_comments(code, Language.JAVA)
        if config.normalize_whitespace:
            code = self._normalize_whitespace(code)
        return code

    def _parse_java(self, code: str) -> ParseResult:
        """
        Parses Java code with detailed analysis.

        :param code: The Java code to parse.
        :return: The result of parsing the code.
        """
        errors = []
        warnings = []
        metrics = defaultdict(int)

        try:
            # Parse Java code into AST using javalang
            ast = javalang.parse.parse(code)

            # Analyze code structure
            metrics.update(self._analyze_java_code(ast))

            # Check for potential issues
            warnings.extend(self._check_java_code(ast))

            return ParseResult(
                ast=ast,
                errors=errors,
                warnings=warnings,
                tokens=[],  # Tokens not implemented for Java
                metrics=dict(metrics),
                language=Language.JAVA,
            )

        except javalang.parser.JavaSyntaxError as e:
            error_info = {
                "type": type(e).__name__,
                "message": str(e),
                "line": getattr(e, "position", (None, None))[0],
                "column": getattr(e, "position", (None, None))[1],
            }
            errors.append(error_info)
            return ParseResult(
                ast=None,
                errors=errors,
                warnings=warnings,
                tokens=[],  # Tokens not implemented for Java
                metrics=dict(metrics),
                language=Language.JAVA,
            )

    def _analyze_java_code(self, ast: JavaCompilationUnit) -> dict[str, int]:
        """
        Analyzes the Java code structure and returns metrics.

        :param ast: The Abstract Syntax Tree (AST) of the Java code.
        :return: A dictionary of metrics.
        """
        metrics = defaultdict(int)
        self._visit_node(ast, metrics)
        return dict(metrics)

    def _visit_node(self, node: JavaNode, metrics: dict[str, int]) -> None:
        """
        Visit nodes in the AST and update metrics.

        :param node: The current AST node.
        :param metrics: The metrics dictionary to update.
        """
        # Count different node types
        metrics[f"count_{type(node).__name__}"] += 1

        # Analyze complexity
        if isinstance(node, javalang.tree.MethodDeclaration):
            metrics["method_count"] += 1
            metrics["max_method_complexity"] = max(
                metrics["max_method_complexity"],
                self._calculate_cyclomatic_complexity(node),
            )
        elif isinstance(node, javalang.tree.ClassDeclaration):
            metrics["class_count"] += 1

        # Recursively visit child nodes
        for child in self.get_children(node):
            self._visit_node(child, metrics)

    def _calculate_cyclomatic_complexity(self, node: JavaNode) -> int:
        """
        Calculate the cyclomatic complexity of a method node.

        :param node: The method node.
        :return: The cyclomatic complexity of the method.
        """
        complexity = 1  # Base complexity
        for child in self.get_children(node):
            if isinstance(
                child,
                (
                    javalang.tree.IfStatement,
                    javalang.tree.ForStatement,
                    javalang.tree.WhileStatement,
                ),
            ):
                complexity += 1
            if isinstance(child, javalang.ast.Node):
                complexity += self._calculate_cyclomatic_complexity(child) - 1  # Subtract base
        return complexity

    def _check_java_code(self, ast: JavaCompilationUnit) -> list[str]:
        """
        Check for potential code issues.

        :param ast: The Abstract Syntax Tree (AST) of the Java code.
        :return: A list of warnings.
        """
        warnings: list[str] = []

        def find_identifiers(node: JavaNode, name: str) -> list[Any]:
            """Find identifiers with the given name in the AST."""
            identifiers: list[Any] = []

            def visit(node: JavaNode) -> None:
                # Check for variable references, not identifiers
                if hasattr(node, "name") and getattr(node, "name", None) == name:
                    identifiers.append(node)
                for child in self.get_children(node):
                    visit(child)

            visit(node)
            return identifiers

        self._visit_for_warnings(ast, warnings, find_identifiers)
        return warnings

    def _visit_for_warnings(self, node: JavaNode, warnings: list[str], find_identifiers: Callable[..., Any]) -> None:
        """
        Visit nodes in the AST and collect warnings.

        :param node: The current AST node.
        :param warnings: The list of warnings to update.
        :param find_identifiers: Function to find identifiers in the AST.
        """
        # Check for unused variables
        if isinstance(node, javalang.tree.VariableDeclarator):
            var_name = getattr(node, "name", None)
            if var_name and not find_identifiers(node, var_name):
                line = getattr(getattr(node, "position", None), "line", "?")
                warnings.append(f"Unused variable '{var_name}' at line {line}")

        # Check for unreachable code
        if isinstance(node, javalang.tree.ReturnStatement):
            parent = getattr(node, "parent", None)
            if parent:
                try:
                    parent_children = self.get_children(parent)
                    node_index = parent_children.index(node) if node in parent_children else -1
                    if node_index >= 0 and any(
                        isinstance(n, javalang.tree.Statement) for n in parent_children[node_index + 1 :]
                    ):
                        line = getattr(getattr(node, "position", None), "line", "?")
                        warnings.append(f"Unreachable code after return statement at line {line}")
                except (ValueError, AttributeError):
                    pass

        # Recursively visit child nodes
        for child in self.get_children(node):
            self._visit_for_warnings(child, warnings, find_identifiers)

    def get_children(self, node: JavaNode) -> list[JavaNode]:
        """
        Returns the child nodes of a given node.

        :param node: The node to get children from.
        :return: A list of child nodes.
        """
        children: list[Any] = []
        if isinstance(node, list):
            children.extend([item for item in node if isinstance(item, javalang.ast.Node)])
        elif isinstance(node, dict):
            children.extend([v for k, v in node.items() if isinstance(v, (dict, list))])
        elif isinstance(node, javalang.ast.Node):
            for fld in node.__dict__.values():
                if isinstance(fld, (list, dict, javalang.ast.Node)):
                    children.append(fld)
        return children

    # ==================== COGNITIVE COMPLEXITY ====================

    def _calculate_cognitive_complexity(self, node: JavaNode) -> int:
        """
        Calculate cognitive complexity for a method.

        Cognitive complexity is designed to more accurately reflect the mental effort
        required to understand code, unlike cyclomatic complexity which just counts paths.

        Rules:
        - +1 for each control flow break (if, for, while, switch, catch, etc.)
        - +1 for each nesting level when inside control structures
        - +1 for each logical operator sequence break (&&, ||)
        - No increment for else, elif (they don't add mental effort)

        :param node: The method node to analyze.
        :return: Cognitive complexity score.
        """
        return self._cognitive_complexity_recursive(node, nesting=0)

    def _cognitive_complexity_recursive(self, node: JavaNode, nesting: int) -> int:
        """
        Recursively calculate cognitive complexity.

        :param node: Current AST node.
        :param nesting: Current nesting level.
        :return: Cognitive complexity contribution.
        """
        complexity = 0

        # Structural complexity - adds 1 + nesting level
        if isinstance(
            node,
            (
                javalang.tree.IfStatement,
                javalang.tree.ForStatement,
                javalang.tree.WhileStatement,
                javalang.tree.DoStatement,
                javalang.tree.SwitchStatement,
            ),
        ):
            complexity += 1 + nesting
            # Process children with increased nesting
            for child in self.get_children(node):
                complexity += self._cognitive_complexity_recursive(child, nesting + 1)
            return complexity

        # Catch blocks add complexity but don't increase nesting for children
        if isinstance(node, javalang.tree.CatchClause):
            complexity += 1 + nesting

        # Ternary operators add complexity
        if isinstance(node, javalang.tree.TernaryExpression):
            complexity += 1 + nesting

        # Binary operators - check for logical sequences
        if isinstance(node, javalang.tree.BinaryOperation):
            operator = getattr(node, "operator", None)
            if operator and operator in ("&&", "||"):
                complexity += 1

        # Lambda expressions add fundamental complexity
        if isinstance(node, javalang.tree.LambdaExpression):
            complexity += 1

        # Continue and break in unusual places
        if isinstance(node, (javalang.tree.BreakStatement, javalang.tree.ContinueStatement)):
            # Only add if breaking to a label
            label = getattr(node, "label", None)
            if label:
                complexity += 1

        # Recursively process children
        for child in self.get_children(node):
            complexity += self._cognitive_complexity_recursive(child, nesting)

        return complexity

    # ==================== HALSTEAD METRICS ====================

    def _extract_halstead_metrics(self, ast: JavaCompilationUnit) -> HalsteadMetrics:
        """
        Extract Halstead complexity metrics from the AST.

        :param ast: The parsed AST.
        :return: HalsteadMetrics with operator and operand counts.
        """
        operators: dict[str, int] = defaultdict(int)
        operands: dict[str, int] = defaultdict(int)

        self._collect_halstead_tokens(ast, operators, operands)

        return HalsteadMetrics(
            n1=len(operators),  # Distinct operators
            n2=len(operands),  # Distinct operands
            N1=sum(operators.values()),  # Total operators
            N2=sum(operands.values()),  # Total operands
        )

    def _collect_halstead_tokens(self, node: JavaNode, operators: dict[str, int], operands: dict[str, int]) -> None:
        """
        Recursively collect operators and operands from AST.

        :param node: Current AST node.
        :param operators: Dictionary to accumulate operators.
        :param operands: Dictionary to accumulate operands.
        """
        # Operators
        if isinstance(node, javalang.tree.BinaryOperation):
            operator = getattr(node, "operator", None)
            if operator:
                operators[operator] += 1

        elif isinstance(node, javalang.tree.Assignment):
            operators["="] += 1

        elif isinstance(node, (javalang.tree.MemberReference, javalang.tree.MethodInvocation)):
            operators["."] += 1

        elif isinstance(node, javalang.tree.ArraySelector):
            operators["[]"] += 1

        elif isinstance(node, javalang.tree.ClassCreator):
            operators["new"] += 1

        elif isinstance(node, javalang.tree.IfStatement):
            operators["if"] += 1

        elif isinstance(node, javalang.tree.ForStatement):
            operators["for"] += 1

        elif isinstance(node, javalang.tree.WhileStatement):
            operators["while"] += 1

        elif isinstance(node, javalang.tree.ReturnStatement):
            operators["return"] += 1

        elif isinstance(node, javalang.tree.TryStatement):
            operators["try"] += 1

        elif isinstance(node, javalang.tree.ThrowStatement):
            operators["throw"] += 1

        elif isinstance(node, javalang.tree.SwitchStatement):
            operators["switch"] += 1

        elif isinstance(node, javalang.tree.TernaryExpression):
            operators["?:"] += 1

        elif isinstance(node, javalang.tree.LambdaExpression):
            operators["->"] += 1

        elif isinstance(node, javalang.tree.MethodReference):
            operators["::"] += 1

        # Operands
        elif isinstance(node, javalang.tree.Literal):
            value = getattr(node, "value", None)
            if value:
                operands[str(value)] += 1

        elif isinstance(node, javalang.tree.MemberReference):
            member = getattr(node, "member", None)
            if member:
                operands[member] += 1

        elif isinstance(node, javalang.tree.VariableDeclarator):
            name = getattr(node, "name", None)
            if name:
                operands[name] += 1

        elif isinstance(node, javalang.tree.FormalParameter):
            name = getattr(node, "name", None)
            if name:
                operands[name] += 1

        # Recurse
        for child in self.get_children(node):
            self._collect_halstead_tokens(child, operators, operands)

    # ==================== METHOD CALL GRAPH ====================

    def _build_method_call_graph(self, ast: JavaCompilationUnit) -> list[MethodCallInfo]:
        """
        Build a method call graph from the AST.

        :param ast: The parsed AST.
        :return: List of method call relationships.
        """
        self._method_calls = []
        self._current_class = None
        self._current_method = None

        self._traverse_for_calls(ast)
        return self._method_calls

    def _traverse_for_calls(self, node: JavaNode) -> None:
        """
        Traverse AST to find method calls.

        :param node: Current AST node.
        """
        old_class = self._current_class
        old_method = self._current_method

        if isinstance(node, javalang.tree.ClassDeclaration):
            self._current_class = getattr(node, "name", None)

        elif isinstance(node, javalang.tree.MethodDeclaration):
            self._current_method = getattr(node, "name", None)

        elif isinstance(node, javalang.tree.MethodInvocation):
            if self._current_class and self._current_method:
                callee_class = getattr(node, "qualifier", None)
                member = getattr(node, "member", None)
                line = getattr(getattr(node, "position", None), "line", 0) if node.position else 0

                if member:
                    self._method_calls.append(
                        MethodCallInfo(
                            caller_class=self._current_class,
                            caller_method=self._current_method,
                            callee_class=callee_class,
                            callee_method=member,
                            line=line,
                        )
                    )

        # Recurse
        for child in self.get_children(node):
            self._traverse_for_calls(child)

        self._current_class = old_class
        self._current_method = old_method

    # ==================== TYPE HIERARCHY ====================

    def _extract_type_hierarchy(self, ast: JavaCompilationUnit) -> dict[str, TypeHierarchy]:
        """
        Extract type hierarchy (inheritance relationships) from AST.

        :param ast: The parsed AST.
        :return: Dictionary mapping class names to their TypeHierarchy.
        """
        hierarchy: dict[str, TypeHierarchy] = {}

        for _path, node in ast.filter(javalang.tree.ClassDeclaration):  # type: ignore[attr-defined]
            superclass = None
            if node.extends:
                superclass = node.extends.name

            interfaces = []
            if node.implements:
                interfaces = [impl.name for impl in node.implements]

            is_abstract = "abstract" in (node.modifiers or [])

            hierarchy[node.name] = TypeHierarchy(
                name=node.name,
                superclass=superclass,
                interfaces=interfaces,
                is_interface=False,
                is_abstract=is_abstract,
            )

        for _path, node in ast.filter(javalang.tree.InterfaceDeclaration):  # type: ignore[attr-defined]
            extends = []
            if node.extends:
                extends = [ext.name for ext in node.extends]

            hierarchy[node.name] = TypeHierarchy(
                name=node.name,
                superclass=None,
                interfaces=extends,  # Interfaces extend other interfaces
                is_interface=True,
                is_abstract=True,
            )

        # Build reverse relationships (subclasses)
        for name, type_info in hierarchy.items():
            if type_info.superclass and type_info.superclass in hierarchy:
                hierarchy[type_info.superclass].subclasses.append(name)
            for iface in type_info.interfaces:
                if iface in hierarchy:
                    hierarchy[iface].subclasses.append(name)

        return hierarchy

    # ==================== DESIGN PATTERN DETECTION ====================

    def _detect_design_patterns(self, ast: JavaCompilationUnit) -> list[DesignPatternMatch]:
        """
        Detect common design patterns in the code.

        :param ast: The parsed AST.
        :return: List of detected design patterns with confidence scores.
        """
        patterns: list[DesignPatternMatch] = []

        for _path, node in ast.filter(javalang.tree.ClassDeclaration):  # type: ignore[attr-defined]
            # Check for Singleton pattern
            singleton_result = self._check_singleton_pattern(node)
            if singleton_result:
                patterns.append(singleton_result)

            # Check for Builder pattern
            builder_result = self._check_builder_pattern(node)
            if builder_result:
                patterns.append(builder_result)

            # Check for Factory pattern
            factory_result = self._check_factory_pattern(node)
            if factory_result:
                patterns.append(factory_result)

        return patterns

    def _check_singleton_pattern(self, class_node: JavaNode) -> DesignPatternMatch | None:
        """
        Check if class implements Singleton pattern.

        Indicators:
        - Private static instance field
        - Private constructor
        - Public static getInstance() method
        """
        evidence: list[str] = []
        confidence = 0.0

        has_private_constructor = False
        has_static_instance = False
        has_get_instance = False

        # Check constructors
        if class_node.constructors:
            for ctor in class_node.constructors:
                if "private" in (ctor.modifiers or []):
                    has_private_constructor = True
                    evidence.append("Private constructor found")
                    break

        # Check fields
        if class_node.fields:
            for field_decl in class_node.fields:
                modifiers = field_decl.modifiers or []
                if "static" in modifiers and "private" in modifiers:
                    # Check if field type matches class name
                    if hasattr(field_decl, "type") and hasattr(field_decl.type, "name"):
                        if field_decl.type.name == class_node.name:
                            has_static_instance = True
                            evidence.append("Private static instance field found")

        # Check methods
        if class_node.methods:
            for method in class_node.methods:
                modifiers = method.modifiers or []
                if (
                    "static" in modifiers
                    and "public" in modifiers
                    and method.name.lower() in ("getinstance", "instance", "get")
                ):
                    has_get_instance = True
                    evidence.append(f"Static getInstance method: {method.name}")

        # Calculate confidence
        if has_private_constructor:
            confidence += 0.4
        if has_static_instance:
            confidence += 0.3
        if has_get_instance:
            confidence += 0.3

        if confidence >= 0.6:
            return DesignPatternMatch(
                pattern_name="Singleton",
                class_name=class_node.name,
                confidence=confidence,
                evidence=evidence,
            )
        return None

    def _check_builder_pattern(self, class_node: JavaNode) -> DesignPatternMatch | None:
        """
        Check if class implements Builder pattern.

        Indicators:
        - Methods returning 'this' for chaining
        - build() method
        - Class name ends with 'Builder'
        """
        evidence: list[str] = []
        confidence = 0.0

        # Check class name
        if class_node.name.endswith("Builder"):
            confidence += 0.4
            evidence.append("Class name ends with 'Builder'")

        has_build_method = False
        chaining_methods = 0

        if class_node.methods:
            for method in class_node.methods:
                if method.name == "build":
                    has_build_method = True
                    evidence.append("build() method found")

                # Check for methods returning this (return type matches class or is void with common builder patterns)
                if hasattr(method, "return_type") and method.return_type:
                    if hasattr(method.return_type, "name") and method.return_type.name == class_node.name:
                        chaining_methods += 1

        if has_build_method:
            confidence += 0.3
        if chaining_methods >= 2:
            confidence += 0.3
            evidence.append(f"{chaining_methods} chaining methods found")

        if confidence >= 0.6:
            return DesignPatternMatch(
                pattern_name="Builder",
                class_name=class_node.name,
                confidence=confidence,
                evidence=evidence,
            )
        return None

    def _check_factory_pattern(self, class_node: JavaNode) -> DesignPatternMatch | None:
        """
        Check if class implements Factory pattern.

        Indicators:
        - Class name contains 'Factory'
        - Methods that create and return objects
        - Static creation methods
        """
        evidence: list[str] = []
        confidence = 0.0

        # Check class name
        if "Factory" in class_node.name:
            confidence += 0.5
            evidence.append("Class name contains 'Factory'")

        creation_methods = 0

        if class_node.methods:
            for method in class_node.methods:
                modifiers = method.modifiers or []
                method_name_lower = method.name.lower()

                # Check for creation method patterns
                if any(prefix in method_name_lower for prefix in ("create", "make", "build", "new", "get")):
                    if "static" in modifiers or "Factory" in class_node.name:
                        creation_methods += 1
                        evidence.append(f"Creation method: {method.name}")

        if creation_methods >= 1:
            confidence += min(0.5, creation_methods * 0.2)

        if confidence >= 0.5:
            return DesignPatternMatch(
                pattern_name="Factory",
                class_name=class_node.name,
                confidence=confidence,
                evidence=evidence,
            )
        return None

    # ==================== THREAD SAFETY ANALYSIS ====================

    def _analyze_thread_safety(self, ast: JavaCompilationUnit) -> ThreadSafetyInfo:
        """
        Analyze code for thread safety concerns.

        :param ast: The parsed AST.
        :return: ThreadSafetyInfo with analysis results.
        """
        result = ThreadSafetyInfo()

        for path, node in ast.filter(javalang.tree.MethodDeclaration):  # type: ignore[attr-defined]
            modifiers = node.modifiers or []
            if "synchronized" in modifiers:
                class_name = self._get_enclosing_class_name(path)
                result.synchronized_methods.append(f"{class_name}.{node.name}")

        for path, node in ast.filter(javalang.tree.FieldDeclaration):  # type: ignore[attr-defined]
            modifiers = node.modifiers or []
            if "volatile" in modifiers:
                for decl in node.declarators:
                    result.volatile_fields.append(decl.name)

        # Count synchronized blocks
        for path, node in ast.filter(javalang.tree.SynchronizedStatement):  # type: ignore[attr-defined]
            result.synchronized_blocks += 1

        # Detect potential race conditions
        result.potential_race_conditions = self._detect_race_conditions(ast)

        return result

    def _get_enclosing_class_name(self, path: tuple) -> str:
        """Get the name of the enclosing class from the path."""
        for node in reversed(path):
            if isinstance(node, javalang.tree.ClassDeclaration):
                class_name = getattr(node, "name", None)
                if class_name:
                    return class_name
        return "<unknown>"

    def _detect_race_conditions(self, ast: JavaCompilationUnit) -> list[str]:
        """
        Detect potential race conditions (basic heuristics).

        :param ast: The parsed AST.
        :return: List of potential race condition warnings.
        """
        warnings: list[str] = []
        shared_fields: set[str] = set()
        volatile_fields: set[str] = set()

        # Find static non-final fields (potentially shared)
        for _path, node in ast.filter(javalang.tree.FieldDeclaration):  # type: ignore[attr-defined]
            modifiers = node.modifiers or []
            if "static" in modifiers and "final" not in modifiers:
                for decl in node.declarators:
                    shared_fields.add(decl.name)
            if "volatile" in modifiers:
                for decl in node.declarators:
                    volatile_fields.add(decl.name)

        # Check for non-synchronized access to shared fields
        for _path, node in ast.filter(javalang.tree.MethodDeclaration):  # type: ignore[attr-defined]
            modifiers = getattr(node, "modifiers", None) or []
            if "synchronized" not in modifiers:
                # Check if method accesses shared fields
                accessed_shared = self._find_shared_field_access(node, shared_fields - volatile_fields)
                if accessed_shared:
                    method_name = getattr(node, "name", "unknown")
                    warnings.append(
                        f"Method {method_name} accesses shared field(s) {accessed_shared} without synchronization"
                    )

        return warnings

    def _find_shared_field_access(self, node: JavaNode, shared_fields: set[str]) -> set[str]:
        """Find accesses to shared fields in a method."""
        accessed: set[str] = set()

        def traverse(n: JavaNode) -> None:
            if isinstance(n, javalang.tree.MemberReference):
                member = getattr(n, "member", None)
                if member and member in shared_fields:
                    accessed.add(member)
            for child in self.get_children(n):
                traverse(child)

        traverse(node)
        return accessed

    # ==================== SECURITY ANALYSIS ====================

    def _detect_security_issues(self, ast: JavaCompilationUnit, code: str) -> list[SecurityIssue]:
        """
        Detect potential security vulnerabilities.

        :param ast: The parsed AST.
        :param code: Original source code for regex matching.
        :return: List of detected security issues.
        """
        issues: list[SecurityIssue] = []

        # SQL Injection detection
        issues.extend(self._detect_sql_injection(ast, code))

        # Hardcoded secrets
        issues.extend(self._detect_hardcoded_secrets(ast))

        return issues

    def _detect_sql_injection(self, ast: JavaCompilationUnit, code: str) -> list[SecurityIssue]:
        """Detect potential SQL injection vulnerabilities."""
        issues: list[SecurityIssue] = []

        # Pattern: String concatenation with SQL keywords
        sql_pattern = re.compile(
            r"(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER)\s+.*\+\s*\w+",
            re.IGNORECASE,
        )

        lines = code.split("\n")
        for i, line in enumerate(lines, 1):
            if sql_pattern.search(line):
                issues.append(
                    SecurityIssue(
                        issue_type="SQL_INJECTION",
                        line=i,
                        message="Potential SQL injection: string concatenation in SQL query",
                        severity="HIGH",
                    )
                )

        # Also check for executeQuery/executeUpdate with concatenation
        for _path, node in ast.filter(javalang.tree.MethodInvocation):  # type: ignore[attr-defined]
            member = getattr(node, "member", None)
            if member in ("executeQuery", "executeUpdate", "execute"):
                arguments = getattr(node, "arguments", None) or []
                for arg in arguments:
                    if isinstance(arg, javalang.tree.BinaryOperation):
                        operator = getattr(arg, "operator", None)
                        if operator == "+":
                            line = getattr(getattr(node, "position", None), "line", 0) if node.position else 0
                            issues.append(
                                SecurityIssue(
                                    issue_type="SQL_INJECTION",
                                    line=line,
                                    message="SQL query using string concatenation - use PreparedStatement",
                                    severity="HIGH",
                                )
                            )
                            break

        return issues

    def _detect_hardcoded_secrets(self, ast: JavaCompilationUnit) -> list[SecurityIssue]:
        """Detect hardcoded passwords, API keys, etc."""
        issues: list[SecurityIssue] = []
        secret_patterns = (
            "password",
            "passwd",
            "pwd",
            "secret",
            "apikey",
            "api_key",
            "token",
            "credential",
        )

        for _path, node in ast.filter(javalang.tree.VariableDeclarator):  # type: ignore[attr-defined]
            var_name = getattr(node, "name", None)
            if not var_name:
                continue
            name_lower = var_name.lower()
            if any(pattern in name_lower for pattern in secret_patterns):
                initializer = getattr(node, "initializer", None)
                if initializer and isinstance(initializer, javalang.tree.Literal):
                    lit_value = getattr(initializer, "value", None)
                    if lit_value:
                        # Skip empty strings and obvious placeholders
                        value = str(lit_value).strip("\"'")
                        if value and value not in ("", "null", "none", "${", "TODO"):
                            line = getattr(getattr(node, "position", None), "line", 0) if node.position else 0
                            issues.append(
                                SecurityIssue(
                                    issue_type="HARDCODED_SECRET",
                                    line=line,
                                    message=f"Potential hardcoded secret in variable '{var_name}'",
                                    severity="HIGH",
                                )
                            )

        return issues

    # ==================== MAINTAINABILITY INDEX ====================

    def _calculate_maintainability_index(
        self, halstead_volume: float, cyclomatic_complexity: int, lines_of_code: int
    ) -> float:
        """
        Calculate the Maintainability Index.

        MI = 171 - 5.2 * ln(V) - 0.23 * G - 16.2 * ln(LOC)

        Where:
        - V = Halstead Volume
        - G = Cyclomatic Complexity
        - LOC = Lines of Code

        Result is normalized to 0-100 scale.

        :param halstead_volume: Halstead volume metric.
        :param cyclomatic_complexity: Total cyclomatic complexity.
        :param lines_of_code: Source lines of code.
        :return: Maintainability index (0-100).
        """
        if halstead_volume <= 0 or lines_of_code <= 0:
            return 100.0  # Can't calculate, assume maintainable

        v_term = 5.2 * math.log(halstead_volume)
        g_term = 0.23 * cyclomatic_complexity
        loc_term = 16.2 * math.log(lines_of_code)

        mi = 171 - v_term - g_term - loc_term

        # Normalize to 0-100
        mi = max(0, min(100, mi * 100 / 171))

        return round(mi, 2)

    # ==================== MAGIC NUMBER DETECTION ====================

    def _detect_magic_numbers(self, ast: JavaCompilationUnit) -> list[tuple[int, str]]:
        """
        Detect magic numbers (hardcoded numeric literals).

        Excludes common acceptable values like 0, 1, -1, etc.

        :param ast: The parsed AST.
        :return: List of (line, value) tuples for magic numbers.
        """
        magic_numbers: list[tuple[int, str]] = []

        for path, node in ast.filter(javalang.tree.Literal):  # type: ignore[attr-defined]
            lit_value = getattr(node, "value", None)
            if lit_value:
                value = str(lit_value)

                # Check if it's a number
                try:
                    # Handle integer and float literals
                    if value.replace(".", "").replace("-", "").replace("_", "").isdigit():
                        # Normalize: remove underscores, L/l suffix, etc.
                        normalized = value.replace("_", "").rstrip("LlFfDd")

                        if normalized not in self.ACCEPTABLE_NUMBERS:
                            # Check if it's in a constant definition (field with final modifier)
                            if not self._is_in_constant_definition(path):
                                line = getattr(getattr(node, "position", None), "line", 0) if node.position else 0
                                magic_numbers.append((line, value))
                except ValueError:
                    pass

        return magic_numbers

    def _is_in_constant_definition(self, path: tuple) -> bool:
        """Check if the current path is within a constant (final) field definition."""
        for node in path:
            if isinstance(node, javalang.tree.FieldDeclaration):
                modifiers = getattr(node, "modifiers", None) or []
                if "final" in modifiers:
                    return True
        return False

    # ==================== NESTING DEPTH ANALYSIS ====================

    def _calculate_max_nesting_depth(self, node: JavaNode) -> int:
        """
        Calculate maximum nesting depth for a method.

        :param node: The method node.
        :return: Maximum nesting depth.
        """
        return self._nesting_depth_recursive(node, 0)

    def _nesting_depth_recursive(self, node: JavaNode, current_depth: int) -> int:
        """
        Recursively calculate nesting depth.

        :param node: Current AST node.
        :param current_depth: Current nesting level.
        :return: Maximum nesting depth found.
        """
        max_depth = current_depth

        # These constructs increase nesting
        nesting_constructs = (
            javalang.tree.IfStatement,
            javalang.tree.ForStatement,
            javalang.tree.WhileStatement,
            javalang.tree.DoStatement,
            javalang.tree.TryStatement,
            javalang.tree.SwitchStatement,
            javalang.tree.SynchronizedStatement,
        )

        if isinstance(node, nesting_constructs):
            current_depth += 1
            max_depth = current_depth

        for child in self.get_children(node):
            child_depth = self._nesting_depth_recursive(child, current_depth)
            max_depth = max(max_depth, child_depth)

        return max_depth

    # ==================== LOC METRICS ====================

    def _calculate_loc_metrics(self, code: str) -> tuple[int, int, int, int]:
        """
        Calculate lines of code metrics.

        :param code: Source code.
        :return: Tuple of (total_lines, source_lines, comment_lines, blank_lines).
        """
        lines = code.split("\n")
        total_lines = len(lines)
        blank_lines = 0
        comment_lines = 0
        in_block_comment = False

        for line in lines:
            stripped = line.strip()

            if not stripped:
                blank_lines += 1
                continue

            # Handle block comments
            if in_block_comment:
                comment_lines += 1
                if "*/" in stripped:
                    in_block_comment = False
                continue

            if stripped.startswith("/*"):
                comment_lines += 1
                if "*/" not in stripped:
                    in_block_comment = True
                continue

            # Line comment
            if stripped.startswith("//"):
                comment_lines += 1
                continue

            # Mixed line (code + comment) counts as source

        source_lines = total_lines - blank_lines - comment_lines
        return total_lines, source_lines, comment_lines, blank_lines

    # ==================== TRY-CATCH PATTERN EXTRACTION ====================

    def _extract_try_catch_patterns(self, ast: JavaCompilationUnit) -> list[TryCatchPattern]:
        """
        Extract try-catch-finally patterns for error handling analysis.

        :param ast: The parsed AST.
        :return: List of TryCatchPattern instances.
        """
        patterns: list[TryCatchPattern] = []

        for _path, node in ast.filter(javalang.tree.TryStatement):  # type: ignore[attr-defined]
            caught_exceptions: list[str] = []
            is_empty_catch = False
            catch_just_logs = False

            catches = getattr(node, "catches", None)
            if catches:
                for catch in catches:
                    parameter = getattr(catch, "parameter", None)
                    if parameter:
                        # Get exception types
                        exc_types = getattr(parameter, "types", None)
                        if exc_types:
                            for exc_type in exc_types:
                                exc_name = getattr(exc_type, "name", None) or str(exc_type)
                                caught_exceptions.append(exc_name)
                        else:
                            exc_type = getattr(parameter, "type", None)
                            if exc_type:
                                exc_type_name = getattr(exc_type, "name", None)
                                if exc_type_name:
                                    caught_exceptions.append(exc_type_name)

                    # Check if catch block is empty or just logs
                    block = getattr(catch, "block", None)
                    if block:
                        statements = list(block) if block else []
                        if not statements:
                            is_empty_catch = True
                        elif len(statements) == 1:
                            # Check if it's just a logging statement
                            stmt = statements[0]
                            if isinstance(stmt, javalang.tree.StatementExpression):
                                expression = getattr(stmt, "expression", None)
                                if expression and isinstance(expression, javalang.tree.MethodInvocation):
                                    method_member = getattr(expression, "member", None)
                                    if method_member:
                                        method_name = method_member.lower()
                                        if any(
                                            log in method_name
                                            for log in (
                                                "log",
                                                "print",
                                                "debug",
                                                "info",
                                                "warn",
                                                "error",
                                            )
                                        ):
                                            catch_just_logs = True

            patterns.append(
                TryCatchPattern(
                    line=node.position.line if node.position else 0,
                    has_finally=node.finally_block is not None,
                    caught_exceptions=caught_exceptions,
                    is_empty_catch=is_empty_catch,
                    catch_just_logs=catch_just_logs,
                )
            )

        return patterns

    # ==================== EMPTY METHOD DETECTION ====================

    def _detect_empty_methods(self, ast: JavaCompilationUnit) -> list[str]:
        """
        Detect empty methods (excluding abstract/interface methods).

        :param ast: The parsed AST.
        :return: List of empty method names in format "ClassName.methodName".
        """
        empty_methods: list[str] = []

        for path, node in ast.filter(javalang.tree.MethodDeclaration):  # type: ignore[attr-defined]
            modifiers = node.modifiers or []

            # Skip abstract methods - they're meant to be empty
            if "abstract" in modifiers:
                continue

            # Check if method body is empty
            if node.body is None or len(list(node.body)) == 0:
                class_name = self._get_enclosing_class_name(path)
                method_name = getattr(node, "name", "unknown")
                empty_methods.append(f"{class_name}.{method_name}")

        return empty_methods

    # ==================== COMPREHENSIVE ANALYSIS ====================

    def analyze_comprehensive(self, code: str) -> CodeMetrics:
        """
        Perform comprehensive code analysis.

        :param code: Java source code.
        :return: CodeMetrics with all analysis results.
        """
        metrics = CodeMetrics()

        try:
            ast = javalang.parse.parse(code)
        except javalang.parser.JavaSyntaxError:
            return metrics  # Return empty metrics on parse error

        # LOC metrics
        (
            metrics.total_lines,
            metrics.source_lines,
            metrics.comment_lines,
            metrics.blank_lines,
        ) = self._calculate_loc_metrics(code)

        # Halstead metrics
        metrics.halstead = self._extract_halstead_metrics(ast)

        # Count classes, interfaces, methods, fields
        for path, node in ast.filter(javalang.tree.ClassDeclaration):  # type: ignore[attr-defined]
            metrics.class_count += 1
        for path, node in ast.filter(javalang.tree.InterfaceDeclaration):  # type: ignore[attr-defined]
            metrics.interface_count += 1
        for path, node in ast.filter(javalang.tree.FieldDeclaration):  # type: ignore[attr-defined]
            declarators = getattr(node, "declarators", None) or []
            metrics.field_count += len(declarators)

        # Method analysis
        method_complexities: list[int] = []
        method_cognitive: list[int] = []

        for path, node in ast.filter(javalang.tree.MethodDeclaration):  # type: ignore[attr-defined]
            metrics.method_count += 1

            # Cyclomatic complexity
            cc = self._calculate_cyclomatic_complexity(node)
            method_complexities.append(cc)
            metrics.total_cyclomatic += cc

            # Cognitive complexity
            cog = self._calculate_cognitive_complexity(node)
            method_cognitive.append(cog)
            metrics.total_cognitive += cog

            # Nesting depth
            depth = self._calculate_max_nesting_depth(node)
            if depth > metrics.max_nesting_depth:
                metrics.max_nesting_depth = depth
            if depth > 4:
                class_name = self._get_enclosing_class_name(path)
                method_name = getattr(node, "name", "unknown")
                metrics.deeply_nested.append((f"{class_name}.{method_name}", depth))

        if method_complexities:
            metrics.max_cyclomatic = max(method_complexities)
            metrics.avg_cyclomatic = sum(method_complexities) / len(method_complexities)
        if method_cognitive:
            metrics.max_cognitive = max(method_cognitive)
            metrics.avg_cognitive = sum(method_cognitive) / len(method_cognitive)

        # Magic numbers
        metrics.magic_numbers = self._detect_magic_numbers(ast)

        # Empty methods
        metrics.empty_methods = self._detect_empty_methods(ast)

        # Maintainability index
        metrics.maintainability_index = self._calculate_maintainability_index(
            metrics.halstead.volume, metrics.total_cyclomatic, metrics.source_lines
        )

        return metrics

    def analyze_security(self, code: str) -> list[SecurityIssue]:
        """
        Perform security-focused analysis.

        :param code: Java source code.
        :return: List of security issues found.
        """
        try:
            ast = javalang.parse.parse(code)
            return self._detect_security_issues(ast, code)
        except javalang.parser.JavaSyntaxError:
            return []

    def analyze_thread_safety(self, code: str) -> ThreadSafetyInfo:
        """
        Perform thread safety analysis.

        :param code: Java source code.
        :return: ThreadSafetyInfo with analysis results.
        """
        try:
            ast = javalang.parse.parse(code)
            return self._analyze_thread_safety(ast)
        except javalang.parser.JavaSyntaxError:
            return ThreadSafetyInfo()

    def get_method_call_graph(self, code: str) -> list[MethodCallInfo]:
        """
        Build method call graph for the code.

        :param code: Java source code.
        :return: List of method call relationships.
        """
        try:
            ast = javalang.parse.parse(code)
            return self._build_method_call_graph(ast)
        except javalang.parser.JavaSyntaxError:
            return []

    def get_type_hierarchy(self, code: str) -> dict[str, TypeHierarchy]:
        """
        Extract type hierarchy from code.

        :param code: Java source code.
        :return: Dictionary mapping type names to TypeHierarchy.
        """
        try:
            ast = javalang.parse.parse(code)
            return self._extract_type_hierarchy(ast)
        except javalang.parser.JavaSyntaxError:
            return {}

    def detect_patterns(self, code: str) -> list[DesignPatternMatch]:
        """
        Detect design patterns in code.

        :param code: Java source code.
        :return: List of detected design patterns.
        """
        try:
            ast = javalang.parse.parse(code)
            return self._detect_design_patterns(ast)
        except javalang.parser.JavaSyntaxError:
            return []

    def get_try_catch_patterns(self, code: str) -> list[TryCatchPattern]:
        """
        Extract try-catch patterns from code.

        :param code: Java source code.
        :return: List of TryCatchPattern instances.
        """
        try:
            ast = javalang.parse.parse(code)
            return self._extract_try_catch_patterns(ast)
        except javalang.parser.JavaSyntaxError:
            return []
