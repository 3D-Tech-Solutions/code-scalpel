"""
JavaScript/ECMAScript Parser using Esprima.

Comprehensive JavaScript AST analysis with support for ES6+ features,
cognitive complexity calculation, security vulnerability detection,
and code quality metrics.


Features:
    AST Parsing:
        - Full ES6+ syntax support via Esprima
        - Tolerant parsing with error recovery
        - Location tracking for all nodes

    Complexity Metrics:
        - Cyclomatic complexity calculation
        - Cognitive complexity calculation
        - Halstead metrics (vocabulary, volume, difficulty, effort)
        - Maintainability index calculation

    Function Analysis:
        - Function extraction (declarations, expressions, arrows)
        - Parameter analysis (defaults, rest, destructuring)
        - Async/generator function detection
        - Method and constructor identification
        - Nesting depth tracking

    Call Graph:
        - Function call extraction
        - Method call tracking (object.method)
        - Constructor call detection (new X())
        - Caller/callee mapping

    Security Analysis:
        - eval() and Function constructor detection
        - innerHTML/outerHTML XSS detection
        - document.write detection
        - setTimeout/setInterval string argument detection
        - Hardcoded secrets detection (API keys, passwords)

    Module Tracking:
        - ES6 import extraction (default, named, namespace)
        - ES6 export extraction (default, named, re-exports)
        - Module source tracking

    Code Metrics:
        - Line counts (total, code, comments, blank)
        - Function and class counts
        - Comprehensive CodeMetrics aggregation
"""

import math
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import esprima  # type: ignore[import-untyped]
import esprima.error_handler  # type: ignore[import-untyped]
import esprima.nodes  # type: ignore[import-untyped]

from ..base_parser import BaseParser, Language, ParseResult, PreprocessorConfig

# Type aliases for esprima nodes
JSNode = Any  # esprima.nodes.Node
JSProgram = Any  # esprima.nodes.Program


class SecuritySeverity(Enum):
    """Security issue severity levels."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class DesignPatternType(Enum):
    """Common JavaScript design patterns."""

    MODULE = "module"
    REVEALING_MODULE = "revealing_module"
    SINGLETON = "singleton"
    FACTORY = "factory"
    OBSERVER = "observer"
    PUBSUB = "pubsub"
    DECORATOR = "decorator"
    FACADE = "facade"
    PROXY = "proxy"
    MIXIN = "mixin"
    IIFE = "iife"


@dataclass
class FunctionInfo:
    """Information about a JavaScript function."""

    name: str
    line: int
    column: int
    end_line: int | None = None
    params: list[str] = field(default_factory=list)
    is_async: bool = False
    is_generator: bool = False
    is_arrow: bool = False
    is_method: bool = False
    is_constructor: bool = False
    cyclomatic_complexity: int = 1
    cognitive_complexity: int = 0
    line_count: int = 0
    nested_depth: int = 0


@dataclass
class FunctionCallInfo:
    """Information about a function call."""

    callee: str  # Function being called
    arguments_count: int
    line: int
    column: int
    is_method_call: bool = False
    object_name: str | None = None  # For method calls: object.method()
    is_new_call: bool = False  # new Constructor()
    is_chained: bool = False  # obj.method().another()


@dataclass
class HalsteadMetrics:
    """Halstead software complexity metrics."""

    distinct_operators: int = 0  # n1
    distinct_operands: int = 0  # n2
    total_operators: int = 0  # N1
    total_operands: int = 0  # N2

    @property
    def vocabulary(self) -> int:
        """Program vocabulary (n = n1 + n2)."""
        return self.distinct_operators + self.distinct_operands

    @property
    def length(self) -> int:
        """Program length (N = N1 + N2)."""
        return self.total_operators + self.total_operands

    @property
    def calculated_length(self) -> float:
        """Calculated program length."""
        if self.distinct_operators == 0 or self.distinct_operands == 0:
            return 0.0
        return self.distinct_operators * math.log2(
            max(self.distinct_operators, 1)
        ) + self.distinct_operands * math.log2(max(self.distinct_operands, 1))

    @property
    def volume(self) -> float:
        """Program volume (V = N * log2(n))."""
        if self.vocabulary == 0:
            return 0.0
        return self.length * math.log2(self.vocabulary)

    @property
    def difficulty(self) -> float:
        """Program difficulty (D = (n1/2) * (N2/n2))."""
        if self.distinct_operands == 0:
            return 0.0
        return (self.distinct_operators / 2) * (self.total_operands / self.distinct_operands)

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
        """Estimated bugs (B = V / 3000)."""
        return self.volume / 3000


@dataclass
class ScopeInfo:
    """Information about a JavaScript scope."""

    name: str
    scope_type: str  # "global", "function", "block", "module", "class"
    line: int
    variables: list[str] = field(default_factory=list)
    functions: list[str] = field(default_factory=list)
    classes: list[str] = field(default_factory=list)
    parent_scope: str | None = None
    is_strict: bool = False


@dataclass
class SecurityIssue:
    """Security vulnerability or issue."""

    rule_id: str
    message: str
    severity: SecuritySeverity
    line: int
    column: int
    cwe_id: str | None = None  # Common Weakness Enumeration
    owasp_category: str | None = None
    recommendation: str | None = None
    code_snippet: str | None = None


@dataclass
class DesignPatternMatch:
    """Detected design pattern."""

    pattern_type: DesignPatternType
    name: str
    line: int
    confidence: float  # 0.0 to 1.0
    description: str | None = None


@dataclass
class ImportInfo:
    """ES6 module import information."""

    module: str
    line: int
    is_default: bool = False
    is_namespace: bool = False  # import * as name
    named_imports: list[str] = field(default_factory=list)
    alias: str | None = None


@dataclass
class ExportInfo:
    """ES6 module export information."""

    name: str
    line: int
    is_default: bool = False
    is_named: bool = False
    is_reexport: bool = False
    source_module: str | None = None


@dataclass
class CodeMetrics:
    """Comprehensive code metrics."""

    line_count: int = 0
    code_lines: int = 0
    comment_lines: int = 0
    blank_lines: int = 0
    function_count: int = 0
    class_count: int = 0
    max_cyclomatic_complexity: int = 0
    avg_cyclomatic_complexity: float = 0.0
    max_cognitive_complexity: int = 0
    avg_cognitive_complexity: float = 0.0
    max_nesting_depth: int = 0
    halstead: HalsteadMetrics | None = None
    maintainability_index: float = 0.0


class JavaScriptParser(BaseParser):
    """
    JavaScriptParser is responsible for parsing and analyzing JavaScript code.

    This class uses the Esprima library to parse JavaScript code into an Abstract Syntax Tree (AST),
    performs preprocessing steps, analyzes the code structure, and checks for potential issues.

    Features:
    - ES6+ syntax support
    - Cognitive complexity calculation
    - Halstead metrics extraction
    - Call graph building
    - Security vulnerability detection
    - Design pattern recognition
    - Module import/export tracking

    Attributes:
        _operators: Set of JavaScript operators for Halstead metrics.
        _dangerous_functions: Set of potentially dangerous function names.

    Methods:
        _preprocess_code(code: str, config: Optional[PreprocessorConfig]) -> str:
            Preprocess the JavaScript code based on the provided configuration.

        _parse_javascript(code: str) -> ParseResult:
            Parses JavaScript code with detailed analysis and returns the result.

        _analyze_javascript_code(ast: esprima.nodes.Node) -> Dict[str, int]:
            Analyzes the JavaScript code structure and returns metrics.

        _visit_node(node: esprima.nodes.Node, metrics: Dict[str, int]) -> None:
            Visits nodes in the AST and updates metrics.

        _check_javascript_code(ast: esprima.nodes.Node) -> List[str]:
            Checks for potential code issues and returns warnings.

        get_children(node: esprima.nodes.Node) -> List[esprima.nodes.Node]:
            Returns the child nodes of a given node.
    """

    # JavaScript operators for Halstead metrics
    _operators: set[str] = {
        "+",
        "-",
        "*",
        "/",
        "%",
        "**",  # Arithmetic
        "=",
        "+=",
        "-=",
        "*=",
        "/=",
        "%=",
        "**=",  # Assignment
        "==",
        "===",
        "!=",
        "!==",
        "<",
        ">",
        "<=",
        ">=",  # Comparison
        "&&",
        "||",
        "!",
        "??",
        "?.",  # Logical/Nullish
        "&",
        "|",
        "^",
        "~",
        "<<",
        ">>",
        ">>>",  # Bitwise
        "++",
        "--",  # Increment/Decrement
        "?",
        ":",  # Ternary
        "typeof",
        "instanceof",
        "in",
        "delete",
        "void",
        "new",  # Unary/Keyword
        ".",
        "[]",
        "()",
        "{}",  # Access/Grouping
        "=>",
        "...",
        ",",  # ES6+
    }

    # Dangerous functions that may indicate security issues
    _dangerous_functions: set[str] = {
        "eval",
        "Function",
        "setTimeout",
        "setInterval",  # Code execution
        "document.write",
        "innerHTML",
        "outerHTML",  # DOM XSS
        "insertAdjacentHTML",
        "document.writeln",
        "exec",
        "execSync",
        "spawn",
        "spawnSync",  # Node.js command execution
        "child_process",
        "require",  # Dynamic requires
    }

    def _preprocess_javascript_code(self, code: str, config: PreprocessorConfig | None) -> str:
        """
        Preprocess the JavaScript code.

        :param code: The JavaScript code to preprocess.
        :param config: Configuration for preprocessing.
        :return: The preprocessed code.
        """
        if config is None:
            config = PreprocessorConfig(remove_comments=False, normalize_whitespace=False)
        if config.remove_comments:
            code = self._remove_comments(code, Language.JAVASCRIPT)
        if config.normalize_whitespace:
            code = self._normalize_whitespace(code)
        return code

    def parse_code(
        self,
        code: str,
        preprocess: bool = True,
        config: PreprocessorConfig | None = None,
    ) -> ParseResult:
        """
        Parse JavaScript code implementing BaseParser interface.

        [20251221_FEATURE] Implementation of abstract method for IParser compatibility.

        Args:
            code: JavaScript source code to parse
            preprocess: Whether to preprocess the code
            config: Preprocessing configuration

        Returns:
            ParseResult with AST, errors, warnings, and metrics
        """
        if preprocess:
            code = self._preprocess_javascript_code(code, config)
        return self._parse_javascript(code)

    def _parse_javascript(self, code: str) -> ParseResult:
        """
        Parses JavaScript code with detailed analysis.

        :param code: The JavaScript code to parse.
        :return: The result of parsing the code.
        """
        errors = []
        warnings = []
        metrics = defaultdict(int)

        try:
            # Parse JavaScript code into AST using Esprima
            ast = esprima.parseScript(code, loc=True, tolerant=True)

            # Set parent nodes
            self._set_parent_nodes(ast)

            # Analyze code structure
            metrics.update(self._analyze_javascript_code(ast))

            # Check for potential issues
            warnings.extend(self._check_javascript_code(ast))

            return ParseResult(
                ast=ast,
                errors=errors,
                warnings=warnings,
                tokens=[],  # Tokens not implemented for JavaScript
                metrics=dict(metrics),
                language=Language.JAVASCRIPT,
            )

        except esprima.error_handler.Error as e:
            error_info = {
                "type": type(e).__name__,
                "message": e.message,
                "line": e.lineNumber,
                "column": e.column,
            }
            errors.append(error_info)
            return ParseResult(
                ast=None,
                errors=errors,
                warnings=warnings,
                tokens=[],  # Tokens not implemented for JavaScript
                metrics=dict(metrics),
                language=Language.JAVASCRIPT,
            )

    def _analyze_javascript_code(self, ast: JSNode) -> dict[str, int]:
        """
        Analyzes the JavaScript code structure and returns metrics.

        :param ast: The Abstract Syntax Tree (AST) of the JavaScript code.
        :return: A dictionary of metrics.
        """
        metrics = defaultdict(int)
        self._visit_node(ast, metrics)
        return dict(metrics)

    def _visit_node(self, node: JSNode, metrics: dict[str, int]) -> None:
        """
        Visit nodes in the AST and update metrics.

        :param node: The current AST node.
        :param metrics: The metrics dictionary to update.
        """
        # Count different node types
        metrics[f"count_{type(node).__name__}"] += 1

        # Analyze complexity
        if isinstance(node, esprima.nodes.FunctionDeclaration):
            metrics["function_count"] += 1
            metrics["max_function_complexity"] = max(
                metrics["max_function_complexity"],
                self._calculate_cyclomatic_complexity(node),
            )
        elif isinstance(node, esprima.nodes.ClassDeclaration):
            metrics["class_count"] += 1

        # Recursively visit child nodes
        for child in self.get_children(node):
            self._visit_node(child, metrics)

    def _calculate_cyclomatic_complexity(self, node: JSNode) -> int:
        """
        Calculate the cyclomatic complexity of a function node.

        :param node: The function node.
        :return: The cyclomatic complexity of the function.
        """
        complexity = 1  # Base complexity
        for child in self.get_children(node):
            if isinstance(
                child,
                (
                    esprima.nodes.IfStatement,
                    esprima.nodes.ForStatement,
                    esprima.nodes.WhileStatement,
                ),
            ):
                complexity += 1
            elif isinstance(child, esprima.nodes.SwitchCase):
                complexity += 1
            elif isinstance(child, esprima.nodes.CatchClause):
                complexity += 1
            elif isinstance(child, esprima.nodes.ConditionalExpression):
                complexity += 1
            elif isinstance(child, esprima.nodes.BinaryExpression):
                if hasattr(child, "operator") and child.operator in ("&&", "||", "??"):
                    complexity += 1
            complexity += self._calculate_cyclomatic_complexity(child)
        return complexity

    def calculate_cognitive_complexity(self, node: JSNode) -> int:
        """
        Calculate cognitive complexity for a function.

        Cognitive complexity measures how difficult code is to understand.
        It penalizes nesting and certain control structures.

        :param node: The function node.
        :return: The cognitive complexity score.
        """
        return self._calculate_cognitive_recursive(node, 0)

    def _calculate_cognitive_recursive(self, node: JSNode, nesting: int) -> int:
        """Recursive helper for cognitive complexity calculation."""
        complexity = 0

        # Increment for control structures
        increment_nodes = (
            esprima.nodes.IfStatement,
            esprima.nodes.ForStatement,
            esprima.nodes.ForInStatement,
            esprima.nodes.WhileStatement,
            esprima.nodes.DoWhileStatement,
            esprima.nodes.CatchClause,
            esprima.nodes.ConditionalExpression,
        )

        if isinstance(node, increment_nodes):
            complexity += 1 + nesting  # Base + nesting penalty

        # Increment for else/else if
        if isinstance(node, esprima.nodes.IfStatement):
            if hasattr(node, "alternate") and node.alternate:
                if isinstance(node.alternate, esprima.nodes.IfStatement):
                    complexity += 1  # else if doesn't add nesting penalty
                else:
                    complexity += 1  # else adds 1

        # Increment for switch
        if isinstance(node, esprima.nodes.SwitchStatement):
            complexity += 1 + nesting

        # Increment for logical operators sequences
        if isinstance(node, esprima.nodes.BinaryExpression):
            if hasattr(node, "operator") and node.operator in ("&&", "||", "??"):
                complexity += 1

        # Increment for break to label or continue to label
        if isinstance(node, (esprima.nodes.BreakStatement, esprima.nodes.ContinueStatement)):
            if hasattr(node, "label") and node.label:
                complexity += 1

        # Calculate nesting for children
        new_nesting = nesting
        nesting_nodes = (
            esprima.nodes.IfStatement,
            esprima.nodes.ForStatement,
            esprima.nodes.ForInStatement,
            esprima.nodes.WhileStatement,
            esprima.nodes.DoWhileStatement,
            esprima.nodes.CatchClause,
            esprima.nodes.SwitchStatement,
            esprima.nodes.FunctionDeclaration,
            esprima.nodes.FunctionExpression,
            esprima.nodes.ArrowFunctionExpression,
        )

        if isinstance(node, nesting_nodes):
            new_nesting = nesting + 1

        # Recurse into children
        for child in self.get_children(node):
            complexity += self._calculate_cognitive_recursive(child, new_nesting)

        return complexity

    def extract_halstead_metrics(self, ast: JSNode) -> HalsteadMetrics:
        """
        Extract Halstead software metrics from AST.

        :param ast: The AST to analyze.
        :return: HalsteadMetrics object.
        """
        operators: dict[str, int] = defaultdict(int)
        operands: dict[str, int] = defaultdict(int)

        self._collect_halstead(ast, operators, operands)

        return HalsteadMetrics(
            distinct_operators=len(operators),
            distinct_operands=len(operands),
            total_operators=sum(operators.values()),
            total_operands=sum(operands.values()),
        )

    def _collect_halstead(self, node: JSNode, operators: dict[str, int], operands: dict[str, int]) -> None:
        """Collect operators and operands for Halstead metrics."""
        if isinstance(node, esprima.nodes.BinaryExpression):
            if hasattr(node, "operator"):
                operators[node.operator] += 1
        elif isinstance(node, esprima.nodes.UnaryExpression):
            if hasattr(node, "operator"):
                operators[node.operator] += 1
        elif isinstance(node, esprima.nodes.UpdateExpression):
            if hasattr(node, "operator"):
                operators[node.operator] += 1
        elif isinstance(node, esprima.nodes.AssignmentExpression):
            if hasattr(node, "operator"):
                operators[node.operator] += 1
        elif isinstance(node, esprima.nodes.BinaryExpression):
            if hasattr(node, "operator") and node.operator in ("&&", "||", "??"):
                operators[node.operator] += 1
        elif isinstance(node, esprima.nodes.Identifier):
            if hasattr(node, "name"):
                operands[node.name] += 1
        elif isinstance(node, esprima.nodes.Literal):
            if hasattr(node, "value"):
                operands[str(node.value)] += 1
        elif isinstance(node, esprima.nodes.CallExpression):
            operators["()"] += 1
        elif isinstance(node, esprima.nodes.MemberExpression):
            operators["."] += 1
        elif isinstance(node, esprima.nodes.NewExpression):
            operators["new"] += 1
        elif isinstance(node, esprima.nodes.ConditionalExpression):
            operators["?:"] += 1
        elif isinstance(node, esprima.nodes.ArrayExpression):
            operators["[]"] += 1
        elif isinstance(node, esprima.nodes.ObjectExpression):
            operators["{}"] += 1

        for child in self.get_children(node):
            self._collect_halstead(child, operators, operands)

    def build_call_graph(self, ast: JSNode) -> dict[str, list[FunctionCallInfo]]:
        """
        Build a call graph from the AST.

        :param ast: The AST to analyze.
        :return: Dictionary mapping function names to their call sites.
        """
        call_graph: dict[str, list[FunctionCallInfo]] = defaultdict(list)
        current_function = ["<global>"]

        def visit(node: JSNode) -> None:
            # Track current function context
            if isinstance(
                node,
                (
                    esprima.nodes.FunctionDeclaration,
                    esprima.nodes.FunctionExpression,
                ),
            ):
                name = getattr(node.id, "name", "<anonymous>") if hasattr(node, "id") and node.id else "<anonymous>"
                current_function.append(name)
            elif isinstance(node, esprima.nodes.ArrowFunctionExpression):
                current_function.append("<arrow>")

            # Record call expressions
            if isinstance(node, esprima.nodes.CallExpression):
                call_info = self._extract_call_info(node)
                call_graph[current_function[-1]].append(call_info)

            # Record new expressions as calls
            if isinstance(node, esprima.nodes.NewExpression):
                call_info = self._extract_call_info(node, is_new=True)
                call_graph[current_function[-1]].append(call_info)

            # Recurse
            for child in self.get_children(node):
                visit(child)

            # Pop function context
            if isinstance(
                node,
                (
                    esprima.nodes.FunctionDeclaration,
                    esprima.nodes.FunctionExpression,
                    esprima.nodes.ArrowFunctionExpression,
                ),
            ):
                current_function.pop()

        visit(ast)
        return dict(call_graph)

    def _extract_call_info(self, node: JSNode, is_new: bool = False) -> FunctionCallInfo:
        """Extract function call information from a call/new expression."""
        callee = ""
        is_method = False
        object_name = None

        if hasattr(node, "callee"):
            callee_node = node.callee
            if isinstance(callee_node, esprima.nodes.Identifier):
                callee = callee_node.name
            elif isinstance(callee_node, esprima.nodes.MemberExpression):
                is_method = True
                if hasattr(callee_node, "property") and isinstance(callee_node.property, esprima.nodes.Identifier):
                    callee = callee_node.property.name
                if hasattr(callee_node, "object") and isinstance(callee_node.object, esprima.nodes.Identifier):
                    object_name = callee_node.object.name

        args_count = len(node.arguments) if hasattr(node, "arguments") else 0
        line = node.loc.start.line if hasattr(node, "loc") and node.loc else 0
        column = node.loc.start.column if hasattr(node, "loc") and node.loc else 0

        return FunctionCallInfo(
            callee=callee,
            arguments_count=args_count,
            line=line,
            column=column,
            is_method_call=is_method,
            object_name=object_name,
            is_new_call=is_new,
        )

    def detect_security_issues(self, ast: JSNode, code: str = "") -> list[SecurityIssue]:
        """
        Detect potential security vulnerabilities in the code.

        :param ast: The AST to analyze.
        :param code: Original source code for context.
        :return: List of security issues found.
        """
        issues: list[SecurityIssue] = []

        def visit(node: JSNode) -> None:
            # Check for eval
            if isinstance(node, esprima.nodes.CallExpression):
                if isinstance(node.callee, esprima.nodes.Identifier):
                    if node.callee.name == "eval":
                        issues.append(
                            SecurityIssue(
                                rule_id="no-eval",
                                message="Use of eval() is dangerous and can lead to code injection",
                                severity=SecuritySeverity.CRITICAL,
                                line=(node.loc.start.line if hasattr(node, "loc") and node.loc else 0),
                                column=(node.loc.start.column if hasattr(node, "loc") and node.loc else 0),
                                cwe_id="CWE-95",
                                owasp_category="A03:2021-Injection",
                                recommendation="Use safer alternatives like JSON.parse() or function calls",
                            )
                        )
                    elif node.callee.name == "Function":
                        issues.append(
                            SecurityIssue(
                                rule_id="no-new-func",
                                message="Use of Function constructor is equivalent to eval()",
                                severity=SecuritySeverity.HIGH,
                                line=(node.loc.start.line if hasattr(node, "loc") and node.loc else 0),
                                column=(node.loc.start.column if hasattr(node, "loc") and node.loc else 0),
                                cwe_id="CWE-95",
                                owasp_category="A03:2021-Injection",
                                recommendation="Define functions statically",
                            )
                        )

                # Check for setTimeout/setInterval with strings
                if isinstance(node.callee, esprima.nodes.Identifier):
                    if node.callee.name in ("setTimeout", "setInterval"):
                        if node.arguments and isinstance(node.arguments[0], esprima.nodes.Literal):
                            if isinstance(node.arguments[0].value, str):
                                issues.append(
                                    SecurityIssue(
                                        rule_id="no-implied-eval",
                                        message=f"{node.callee.name} with string argument acts like eval()",
                                        severity=SecuritySeverity.HIGH,
                                        line=(node.loc.start.line if hasattr(node, "loc") and node.loc else 0),
                                        column=(node.loc.start.column if hasattr(node, "loc") and node.loc else 0),
                                        cwe_id="CWE-95",
                                        recommendation="Pass a function reference instead of a string",
                                    )
                                )

            # Check for innerHTML/outerHTML assignments
            if isinstance(node, esprima.nodes.AssignmentExpression):
                if isinstance(node.left, esprima.nodes.MemberExpression):
                    if hasattr(node.left, "property") and isinstance(node.left.property, esprima.nodes.Identifier):
                        if node.left.property.name in ("innerHTML", "outerHTML"):
                            issues.append(
                                SecurityIssue(
                                    rule_id="no-inner-html",
                                    message=f"Assignment to {node.left.property.name} can lead to XSS",
                                    severity=SecuritySeverity.HIGH,
                                    line=(node.loc.start.line if hasattr(node, "loc") and node.loc else 0),
                                    column=(node.loc.start.column if hasattr(node, "loc") and node.loc else 0),
                                    cwe_id="CWE-79",
                                    owasp_category="A03:2021-Injection",
                                    recommendation="Use textContent or DOM manipulation methods",
                                )
                            )

            # Check for document.write
            if isinstance(node, esprima.nodes.CallExpression):
                if isinstance(node.callee, esprima.nodes.MemberExpression):
                    if (
                        hasattr(node.callee, "object")
                        and isinstance(node.callee.object, esprima.nodes.Identifier)
                        and node.callee.object.name == "document"
                    ):
                        if (
                            hasattr(node.callee, "property")
                            and isinstance(node.callee.property, esprima.nodes.Identifier)
                            and node.callee.property.name in ("write", "writeln")
                        ):
                            issues.append(
                                SecurityIssue(
                                    rule_id="no-document-write",
                                    message="document.write can lead to XSS and performance issues",
                                    severity=SecuritySeverity.MEDIUM,
                                    line=(node.loc.start.line if hasattr(node, "loc") and node.loc else 0),
                                    column=(node.loc.start.column if hasattr(node, "loc") and node.loc else 0),
                                    cwe_id="CWE-79",
                                    recommendation="Use DOM manipulation methods instead",
                                )
                            )

            # Check for hardcoded secrets patterns
            if isinstance(node, esprima.nodes.VariableDeclarator):
                if isinstance(node.id, esprima.nodes.Identifier):
                    name_lower = node.id.name.lower()
                    secret_patterns = (
                        "password",
                        "secret",
                        "api_key",
                        "apikey",
                        "token",
                        "auth",
                    )
                    if any(pattern in name_lower for pattern in secret_patterns):
                        if isinstance(node.init, esprima.nodes.Literal):
                            if isinstance(node.init.value, str) and len(node.init.value) > 5:
                                issues.append(
                                    SecurityIssue(
                                        rule_id="no-hardcoded-secrets",
                                        message=f"Potential hardcoded secret in variable '{node.id.name}'",
                                        severity=SecuritySeverity.HIGH,
                                        line=(node.loc.start.line if hasattr(node, "loc") and node.loc else 0),
                                        column=(node.loc.start.column if hasattr(node, "loc") and node.loc else 0),
                                        cwe_id="CWE-798",
                                        recommendation="Use environment variables or secure secret management",
                                    )
                                )

            for child in self.get_children(node):
                visit(child)

        visit(ast)
        return issues

    def extract_functions(self, ast: JSNode) -> list[FunctionInfo]:
        """
        Extract all functions from the AST.

        :param ast: The AST to analyze.
        :return: List of FunctionInfo objects.
        """
        functions: list[FunctionInfo] = []

        def visit(node: JSNode, depth: int = 0) -> None:
            if isinstance(
                node,
                (
                    esprima.nodes.FunctionDeclaration,
                    esprima.nodes.FunctionExpression,
                    esprima.nodes.ArrowFunctionExpression,
                ),
            ):
                is_arrow = isinstance(node, esprima.nodes.ArrowFunctionExpression)
                name = "<anonymous>"
                if hasattr(node, "id") and node.id and hasattr(node.id, "name"):
                    name = node.id.name

                params = []
                if hasattr(node, "params"):
                    for param in node.params:
                        if isinstance(param, esprima.nodes.Identifier):
                            params.append(param.name)
                        elif isinstance(param, esprima.nodes.AssignmentPattern):
                            if hasattr(param, "left") and isinstance(param.left, esprima.nodes.Identifier):
                                params.append(f"{param.left.name}=")
                        elif isinstance(param, esprima.nodes.RestElement):
                            if hasattr(param, "argument") and isinstance(param.argument, esprima.nodes.Identifier):
                                params.append(f"...{param.argument.name}")

                line = node.loc.start.line if hasattr(node, "loc") and node.loc else 0
                column = node.loc.start.column if hasattr(node, "loc") and node.loc else 0
                end_line = node.loc.end.line if hasattr(node, "loc") and node.loc else None

                func_info = FunctionInfo(
                    name=name,
                    line=line,
                    column=column,
                    end_line=end_line,
                    params=params,
                    is_async=getattr(node, "async", False),
                    is_generator=getattr(node, "generator", False),
                    is_arrow=is_arrow,
                    cyclomatic_complexity=self._calculate_cyclomatic_complexity(node),
                    cognitive_complexity=self.calculate_cognitive_complexity(node),
                    nested_depth=depth,
                )

                if end_line and line:
                    func_info.line_count = end_line - line + 1

                functions.append(func_info)

            # Check for method definitions
            if isinstance(node, esprima.nodes.MethodDefinition):
                name = "<anonymous>"
                if hasattr(node, "key") and isinstance(node.key, esprima.nodes.Identifier):
                    name = node.key.name

                value = node.value if hasattr(node, "value") else None
                if value:
                    params = []
                    if hasattr(value, "params"):
                        for param in value.params:
                            if isinstance(param, esprima.nodes.Identifier):
                                params.append(param.name)

                    line = node.loc.start.line if hasattr(node, "loc") and node.loc else 0

                    func_info = FunctionInfo(
                        name=name,
                        line=line,
                        column=(node.loc.start.column if hasattr(node, "loc") and node.loc else 0),
                        params=params,
                        is_method=True,
                        is_constructor=getattr(node, "kind", "") == "constructor",
                        cyclomatic_complexity=self._calculate_cyclomatic_complexity(value),
                        cognitive_complexity=self.calculate_cognitive_complexity(value),
                    )
                    functions.append(func_info)

            # Recurse with depth tracking
            new_depth = depth
            if isinstance(
                node,
                (
                    esprima.nodes.FunctionDeclaration,
                    esprima.nodes.FunctionExpression,
                    esprima.nodes.ArrowFunctionExpression,
                ),
            ):
                new_depth = depth + 1

            for child in self.get_children(node):
                visit(child, new_depth)

        visit(ast)
        return functions

    def extract_imports(self, ast: JSNode) -> list[ImportInfo]:
        """
        Extract ES6 module imports from AST.

        :param ast: The AST to analyze.
        :return: List of ImportInfo objects.
        """
        imports: list[ImportInfo] = []

        def visit(node: JSNode) -> None:
            if isinstance(node, esprima.nodes.ImportDeclaration):
                module = ""
                if hasattr(node, "source") and node.source:
                    source_value = node.source.value
                    module = str(source_value) if source_value else ""
                line = node.loc.start.line if hasattr(node, "loc") and node.loc else 0

                named_imports: list[str] = []
                is_default = False
                is_namespace = False
                alias = None

                if hasattr(node, "specifiers"):
                    for spec in node.specifiers:
                        if isinstance(spec, esprima.nodes.ImportDefaultSpecifier):
                            is_default = True
                            if hasattr(spec.local, "name"):
                                alias = spec.local.name
                        elif isinstance(spec, esprima.nodes.ImportNamespaceSpecifier):
                            is_namespace = True
                            if hasattr(spec.local, "name"):
                                alias = spec.local.name
                        elif isinstance(spec, esprima.nodes.ImportSpecifier):
                            if hasattr(spec.imported, "name"):
                                named_imports.append(spec.imported.name)

                imports.append(
                    ImportInfo(
                        module=module,
                        line=line,
                        is_default=is_default,
                        is_namespace=is_namespace,
                        named_imports=named_imports,
                        alias=alias,
                    )
                )

            for child in self.get_children(node):
                visit(child)

        visit(ast)
        return imports

    def extract_exports(self, ast: JSNode) -> list[ExportInfo]:
        """
        Extract ES6 module exports from AST.

        :param ast: The AST to analyze.
        :return: List of ExportInfo objects.
        """
        exports: list[ExportInfo] = []

        def visit(node: JSNode) -> None:
            if isinstance(node, esprima.nodes.ExportDefaultDeclaration):
                name = "<default>"
                if hasattr(node, "declaration"):
                    decl = node.declaration
                    if isinstance(decl, esprima.nodes.Identifier):
                        name = decl.name
                    else:
                        decl_id = getattr(decl, "id", None)
                        if decl_id and hasattr(decl_id, "name"):
                            name = decl_id.name

                exports.append(
                    ExportInfo(
                        name=name,
                        line=(node.loc.start.line if hasattr(node, "loc") and node.loc else 0),
                        is_default=True,
                    )
                )

            elif isinstance(node, esprima.nodes.ExportNamedDeclaration):
                line = node.loc.start.line if hasattr(node, "loc") and node.loc else 0
                source_module = None
                if hasattr(node, "source") and node.source:
                    source_value = node.source.value
                    source_module = str(source_value) if source_value else None

                if hasattr(node, "declaration") and node.declaration:
                    decl = node.declaration
                    if isinstance(decl, esprima.nodes.Identifier):
                        name = decl.name
                    else:
                        decl_id = getattr(decl, "id", None)
                        if decl_id and hasattr(decl_id, "name"):
                            name = decl_id.name
                            exports.append(
                                ExportInfo(
                                    name=name,
                                    line=line,
                                    is_named=True,
                                )
                            )
                    decl_declarations = getattr(decl, "declarations", None)
                    if decl_declarations and isinstance(decl_declarations, list):
                        for var_decl in decl_declarations:
                            if (
                                hasattr(var_decl, "id")
                                and var_decl.id
                                and isinstance(var_decl.id, esprima.nodes.Identifier)
                            ):
                                exports.append(
                                    ExportInfo(
                                        name=var_decl.id.name,
                                        line=line,
                                        is_named=True,
                                    )
                                )

                if hasattr(node, "specifiers"):
                    for spec in node.specifiers:
                        if hasattr(spec, "exported") and isinstance(spec.exported, esprima.nodes.Identifier):
                            exports.append(
                                ExportInfo(
                                    name=spec.exported.name,
                                    line=line,
                                    is_named=True,
                                    is_reexport=source_module is not None,
                                    source_module=source_module,
                                )
                            )

            for child in self.get_children(node):
                visit(child)

        visit(ast)
        return exports

    def calculate_maintainability_index(self, halstead: HalsteadMetrics, cyclomatic: int, loc: int) -> float:
        """
        Calculate the Maintainability Index.

        MI = 171 - 5.2 * ln(V) - 0.23 * G - 16.2 * ln(LOC)

        :param halstead: Halstead metrics.
        :param cyclomatic: Cyclomatic complexity.
        :param loc: Lines of code.
        :return: Maintainability Index (0-100 scale).
        """
        if loc <= 0 or halstead.volume <= 0:
            return 100.0

        mi = 171 - 5.2 * math.log(max(halstead.volume, 1)) - 0.23 * cyclomatic - 16.2 * math.log(max(loc, 1))

        # Normalize to 0-100 scale
        mi = max(0, min(100, mi * 100 / 171))
        return round(mi, 2)

    def get_comprehensive_metrics(self, ast: JSNode, code: str) -> CodeMetrics:
        """
        Get comprehensive code metrics.

        :param ast: The AST to analyze.
        :param code: Original source code.
        :return: CodeMetrics object.
        """
        lines = code.split("\n")
        code_lines = sum(1 for line in lines if line.strip() and not line.strip().startswith("//"))
        comment_lines = sum(1 for line in lines if line.strip().startswith("//"))
        blank_lines = sum(1 for line in lines if not line.strip())

        functions = self.extract_functions(ast)
        halstead = self.extract_halstead_metrics(ast)

        cyclomatic_values = [f.cyclomatic_complexity for f in functions]
        cognitive_values = [f.cognitive_complexity for f in functions]

        max_cyclomatic = max(cyclomatic_values) if cyclomatic_values else 0
        avg_cyclomatic = sum(cyclomatic_values) / len(cyclomatic_values) if cyclomatic_values else 0.0
        max_cognitive = max(cognitive_values) if cognitive_values else 0
        avg_cognitive = sum(cognitive_values) / len(cognitive_values) if cognitive_values else 0.0
        max_nesting = max(f.nested_depth for f in functions) if functions else 0

        maintainability = self.calculate_maintainability_index(halstead, max_cyclomatic, code_lines)

        return CodeMetrics(
            line_count=len(lines),
            code_lines=code_lines,
            comment_lines=comment_lines,
            blank_lines=blank_lines,
            function_count=len(functions),
            class_count=sum(1 for _ in self._find_classes(ast)),
            max_cyclomatic_complexity=max_cyclomatic,
            avg_cyclomatic_complexity=round(avg_cyclomatic, 2),
            max_cognitive_complexity=max_cognitive,
            avg_cognitive_complexity=round(avg_cognitive, 2),
            max_nesting_depth=max_nesting,
            halstead=halstead,
            maintainability_index=maintainability,
        )

    def _find_classes(self, ast: JSNode):
        """Generator to find all class declarations."""

        def visit(node: JSNode):
            if isinstance(node, esprima.nodes.ClassDeclaration):
                yield node
            for child in self.get_children(node):
                yield from visit(child)

        yield from visit(ast)

    def _check_javascript_code(self, ast: JSNode) -> list[str]:
        """
        Check for potential code issues.

        :param ast: The Abstract Syntax Tree (AST) of the JavaScript code.
        :return: A list of warnings.
        """
        warnings = []

        def find_identifiers(node: JSNode, name: str) -> list:
            """Find identifiers with the given name in the AST."""
            identifiers = []

            def visit(n: JSNode) -> None:
                if isinstance(n, esprima.nodes.Identifier) and n.name == name:
                    identifiers.append(n)
                for child in self.get_children(n):
                    visit(child)

            visit(node)
            return identifiers

        self._visit_for_warnings(ast, warnings, find_identifiers)
        return warnings

    def _visit_for_warnings(self, node: JSNode, warnings: list[str], find_identifiers: Callable) -> None:
        """
        Visit nodes in the AST and collect warnings.

        :param node: The current AST node.
        :param warnings: The list of warnings to update.
        :param find_identifiers: Function to find identifiers in the AST.
        """
        # Check for unused variables
        if isinstance(node, esprima.nodes.VariableDeclarator):
            if hasattr(node, "id") and node.id and isinstance(node.id, esprima.nodes.Identifier):
                if not find_identifiers(node, node.id.name):
                    line = node.loc.start.line if hasattr(node, "loc") and node.loc else 0
                    warnings.append(f"Unused variable '{node.id.name}' at line {line}")

        # Check for unreachable code
        if isinstance(node, esprima.nodes.ReturnStatement) and hasattr(node, "parent"):
            parent_children = self.get_children(node.parent)
            try:
                idx = parent_children.index(node)
                if any(isinstance(n, esprima.nodes.Statement) for n in parent_children[idx + 1 :]):
                    line = node.loc.start.line if hasattr(node, "loc") and node.loc else 0
                    warnings.append(f"Unreachable code after return statement at line {line}")
            except (ValueError, AttributeError):
                pass

        # Recursively visit child nodes
        for child in self.get_children(node):
            self._visit_for_warnings(child, warnings, find_identifiers)

    def get_children(self, node: JSNode) -> list:
        """
        Returns the child nodes of a given node.

        :param node: The node to get children from.
        :return: A list of child nodes.
        """
        children = []
        if isinstance(node, list):
            children.extend([item for item in node if isinstance(item, esprima.nodes.Node)])
        elif isinstance(node, dict):
            children.extend([v for k, v in node.items() if isinstance(v, (dict, list))])
        elif isinstance(node, esprima.nodes.Node):
            for key, field in node.__dict__.items():
                # Prevent cycles after `_set_parent_nodes` attaches back-references.
                if key == "parent":
                    continue
                if isinstance(field, (list, dict, esprima.nodes.Node)):
                    children.append(field)
        return children

    def _set_parent_nodes(self, node: JSNode, parent: JSNode | None = None) -> None:
        """
        Set parent nodes for the AST.

        :param node: The current AST node.
        :param parent: The parent node.
        """
        # Some children are container values (lists/dicts) rather than AST nodes.
        # Only actual Esprima nodes can carry a `.parent` attribute.
        if isinstance(node, esprima.nodes.Node):
            node.parent = parent  # type: ignore[attr-defined]
            next_parent: JSNode | None = node
        else:  # noqa: PLW2901
            next_parent = parent

        for child in self.get_children(node):
            self._set_parent_nodes(child, next_parent)
