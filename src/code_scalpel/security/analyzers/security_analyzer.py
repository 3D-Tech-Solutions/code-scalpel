"""
Security Analyzer - The Vulnerability Hunter.

This module provides high-level security analysis by combining:
- Symbolic execution (engine.py)
- Taint tracking (taint_tracker.py)
- Sink detection (SINK_PATTERNS)

It can detect:
- SQL Injection (CWE-89)
- Cross-Site Scripting (CWE-79)
- Path Traversal (CWE-22)
- Command Injection (CWE-78)

Usage:
    analyzer = SecurityAnalyzer()
    vulns = analyzer.analyze('''
        user_id = request.args.get("id")
        query = "SELECT * FROM users WHERE id=" + user_id
        cursor.execute(query)
    ''')

    for v in vulns:
        print(f"{v.vulnerability_type} at line {v.sink_location[0]}")
"""

from __future__ import annotations

import ast
import logging
from dataclasses import dataclass, field
from typing import Any, TypedDict, cast

# [20260114_FEATURE] Symbolic execution moved to local import to avoid cycle
# from ...symbolic_execution_tools.engine import SymbolicAnalyzer, PathStatus
# from ...symbolic_execution_tools.type_inference import InferredType

logger = logging.getLogger(__name__)


class TaintFlowDict(TypedDict):
    """Taint flow information for a variable."""

    source: str  # TaintSource name
    level: str  # TaintLevel name
    path: list[str]  # propagation path


class SecurityAnalysisResultDict(TypedDict):
    """Security analysis result with vulnerabilities and taint flows."""

    vulnerability_count: int
    vulnerabilities: list[dict[str, Any]]  # VulnerabilityDict from taint_tracker
    taint_flows: dict[str, TaintFlowDict]
    analyzed_lines: int
    functions_analyzed: list[str]


# [20260102_REFACTOR] Keep imports below to allow class/type definitions before heavy modules.
# ruff: noqa: E402
# [20251225_REFACTOR] Updated import path after security module reorganization
from ..secrets.secret_scanner import SecretScanner
from .taint_tracker import (
    SANITIZER_PATTERNS,
    SANITIZER_REGISTRY,
    SINK_PATTERNS,
    TAINT_SOURCE_PATTERNS,
    SecuritySink,
    TaintInfo,
    TaintLevel,
    TaintSource,
    TaintTracker,
    Vulnerability,
    detect_ssr_vulnerabilities,  # [20251216_FEATURE] v2.2.0
    load_sanitizers_from_config,
)

# Auto-load custom sanitizers from pyproject.toml on module import
_config_loaded = False


def _ensure_config_loaded() -> None:
    """Load config once per process."""
    global _config_loaded
    if not _config_loaded:
        load_sanitizers_from_config()
        _config_loaded = True


@dataclass
class SecurityAnalysisResult:
    """
    Result from security analysis.

    Attributes:
        vulnerabilities: List of detected vulnerabilities
        taint_flows: Map of variable names to their taint info
        analyzed_lines: Number of lines analyzed
        functions_analyzed: Names of functions that were analyzed
    """

    vulnerabilities: list[Vulnerability] = field(default_factory=list)
    taint_flows: dict[str, TaintInfo] = field(default_factory=dict)
    analyzed_lines: int = 0
    functions_analyzed: list[str] = field(default_factory=list)

    @property
    def has_vulnerabilities(self) -> bool:
        """Check if any vulnerabilities were found."""
        return len(self.vulnerabilities) > 0

    @property
    def vulnerability_count(self) -> int:
        """Get total number of vulnerabilities."""
        return len(self.vulnerabilities)

    def get_by_type(self, vuln_type: str) -> list[Vulnerability]:
        """Get vulnerabilities of a specific type."""
        return [v for v in self.vulnerabilities if v.vulnerability_type == vuln_type]

    def get_sql_injections(self) -> list[Vulnerability]:
        """Get SQL injection vulnerabilities."""
        return [v for v in self.vulnerabilities if v.sink_type == SecuritySink.SQL_QUERY]

    def get_xss(self) -> list[Vulnerability]:
        """Get XSS vulnerabilities."""
        return [v for v in self.vulnerabilities if v.sink_type == SecuritySink.HTML_OUTPUT]

    def get_path_traversals(self) -> list[Vulnerability]:
        """Get path traversal vulnerabilities."""
        return [v for v in self.vulnerabilities if v.sink_type == SecuritySink.FILE_PATH]

    def get_command_injections(self) -> list[Vulnerability]:
        """Get command injection vulnerabilities."""
        return [v for v in self.vulnerabilities if v.sink_type == SecuritySink.SHELL_COMMAND]

    def to_dict(self) -> SecurityAnalysisResultDict:
        """Convert to dictionary for JSON serialization."""
        return cast(
            SecurityAnalysisResultDict,
            {
                "vulnerability_count": self.vulnerability_count,
                "vulnerabilities": [v.to_dict() for v in self.vulnerabilities],
                "taint_flows": {
                    name: {
                        "source": info.source.name,
                        "level": info.level.name,
                        "path": list(info.propagation_path),
                    }
                    for name, info in self.taint_flows.items()
                },
                "analyzed_lines": self.analyzed_lines,
                "functions_analyzed": self.functions_analyzed,
            },
        )

    def summary(self) -> str:
        """Get a human-readable summary."""
        if not self.has_vulnerabilities:
            return "No vulnerabilities detected."

        lines = [f"Found {self.vulnerability_count} vulnerability(ies):"]

        for v in self.vulnerabilities:
            loc = f"line {v.sink_location[0]}" if v.sink_location else "unknown"
            desc = v.vulnerability_type

            # Add detail for hardcoded secrets if available
            if v.sink_type == SecuritySink.HARDCODED_SECRET and v.taint_path:
                desc = f"{desc}: {v.taint_path[0]}"

            lines.append(f"  - {desc} ({v.cwe_id}) at {loc}")

        return "\n".join(lines)


class SecurityAnalyzer:
    """
    High-level security analyzer for Python code.

    Combines AST analysis with taint tracking to detect
    security vulnerabilities in Python source code.

    Example:
        analyzer = SecurityAnalyzer()
        result = analyzer.analyze(code)

        if result.has_vulnerabilities:
            for vuln in result.vulnerabilities:
                print(f"SECURITY: {vuln}")
    """

    # [20251214_FEATURE] v2.0.0 - Web framework route decorators
    WEB_ROUTE_DECORATORS = {
        # Flask
        "route",
        "get",
        "post",
        "put",
        "delete",
        "patch",
        "app.route",
        "app.get",
        "app.post",
        "app.put",
        "app.delete",
        "blueprint.route",
        "bp.route",
        # FastAPI
        "app.api_route",
        "router.get",
        "router.post",
        "router.put",
        "router.delete",
        "router.patch",
        "router.api_route",
        # Django (class-based views handled separately)
        "api_view",
        "action",
        # Starlette
        "Route",
    }

    def __init__(self):
        """Initialize the security analyzer."""
        self._taint_tracker: TaintTracker | None = None
        self._current_taint_map: dict[str, TaintInfo] = {}
        self._secret_scanner = SecretScanner()

    def _is_web_framework_route(self, func_node: ast.FunctionDef) -> bool:
        """
        [20251214_FEATURE] v2.0.0 - Check if function is a web framework route.

        Detects:
        - Flask: @app.route, @app.get, @bp.route
        - FastAPI: @app.get, @router.post, etc.
        - Django: @api_view, @action

        Args:
            func_node: FunctionDef AST node

        Returns:
            True if this function appears to be a web route handler
        """
        for decorator in func_node.decorator_list:
            decorator_name = self._get_decorator_name(decorator)
            if decorator_name:
                # Check exact match or partial match (e.g., "app.route" matches "route")
                if decorator_name in self.WEB_ROUTE_DECORATORS:
                    return True
                # Check if any known decorator is a suffix
                for known in self.WEB_ROUTE_DECORATORS:
                    if decorator_name.endswith(known):
                        return True
        return False

    def _get_decorator_name(self, decorator: ast.expr) -> str | None:
        """
        Extract the name of a decorator.

        Handles:
        - @decorator
        - @decorator(args)
        - @module.decorator
        - @module.decorator(args)
        """
        if isinstance(decorator, ast.Name):
            return decorator.id
        elif isinstance(decorator, ast.Attribute):
            # e.g., app.route
            parts = []
            node = decorator
            while isinstance(node, ast.Attribute):
                parts.append(node.attr)
                node = node.value
            if isinstance(node, ast.Name):
                parts.append(node.id)
            return ".".join(reversed(parts))
        elif isinstance(decorator, ast.Call):
            # Decorator with arguments: @app.route("/")
            return self._get_decorator_name(decorator.func)
        return None

    def _verify_vulnerability(self, vuln: Vulnerability, code: str) -> bool:
        """
        [20260114_FEATURE] Verify vulnerability using symbolic execution.

        Checks two things:
        1. Type safety: If variable is proven to be Int/Bool/Float, it's safe from string injection.
        2. Reachability: If sink line is not reachable in any feasible path, it's dead code.

        Args:
            vuln: The detected vulnerability
            code: Source code

        Returns:
            True if vulnerability remains valid (cannot be pruned), False if pruned.
        """
        if not vuln.sink_location:
            return True

        sink_line = vuln.sink_location[0]

        try:
            # [20260114_FIX] Local import to avoid circular dependency
            from ...symbolic_execution_tools.engine import SymbolicAnalyzer
            from ...symbolic_execution_tools.type_inference import InferredType

            # Run symbolic analysis
            # We recreate the analyzer each time because it's stateful,
            # but it uses caching so repeated calls for same code are cheap.
            analyzer = SymbolicAnalyzer(enable_cache=True)
            result = analyzer.analyze(code)

            # --- Pruning Strategy 1: Type Safety ---
            # If the tainted variable is constrained to be a safe type (Int, Bool, Float),
            # it cannot contain injection payloads.
            if vuln.taint_path:
                # The first element in taint_path is specific enough for simple cases.
                # For complex flows, we might need to track the specific variable at the sink.
                # But Vulnerability object doesn't currently store the sink variable name explicitly.
                # Assuming the taint path start is the source is reasonable.
                # Better: check if ANY variable in the taint path is inferred as safe type?
                # No, if source is Int but cast to Str, it might be unsafe?
                # Actually, if source is Int, it's usually safe unless explicitly unsafe cast.
                # Let's check the source var.
                var_name = vuln.taint_path[0]
                if var_name in result.all_variables:
                    inferred = result.all_variables[var_name]
                    if inferred in (
                        InferredType.INT,
                        InferredType.BOOL,
                        InferredType.FLOAT,
                    ):
                        logger.debug(f"Pruned vuln: {var_name} is proven {inferred}")
                        return False

            # --- Pruning Strategy 2: Reachability ---

            # If we have 0 feasible paths, it might mean the code is completely dead
            # or analysis failed to find inputs. We should be conservative.
            feasible_paths = result.get_feasible_paths()

            if not feasible_paths:
                # Conservative fallback: if engine finds nothing, don't prune
                return True

            # Check reachability in any feasible path
            for path in feasible_paths:
                if sink_line in path.visited_lines:
                    return True

            # If we checked all feasible paths and none visited the line
            logger.debug(f"Pruned vuln: line {sink_line} is unreachable")
            return False

        except Exception as e:
            # Fallback on errors (syntax, unsupported capabilities, etc.)
            logger.debug(f"Symbolic verification failed: {e}")
            return True

    def analyze(self, code: str) -> SecurityAnalysisResult:
        """
        Analyze Python code for security vulnerabilities.

        Args:
            code: Python source code

        Returns:
            SecurityAnalysisResult with detected vulnerabilities
        """
        if not code or not code.strip():
            return SecurityAnalysisResult()

        try:
            tree = ast.parse(code)
        except SyntaxError:
            return SecurityAnalysisResult()

        # Initialize fresh tracker
        self._taint_tracker = TaintTracker()
        self._current_taint_map = {}

        # Analyze the AST
        result = SecurityAnalysisResult(
            analyzed_lines=code.count("\n") + 1,
        )

        # Visit all nodes
        self._analyze_node(tree, result)

        # Collect results
        taint_vulns = self._taint_tracker.get_vulnerabilities()

        # [20260114_FEATURE] Part 2: Prune False Positives via Symbolic Execution
        verified_vulns = []
        for vuln in taint_vulns:
            # Check reachability and constraints
            if self._verify_vulnerability(vuln, code):
                verified_vulns.append(vuln)
            else:
                # vuln.sink_location can be None in some cases
                if vuln.sink_location:
                    logger.info(f"Pruned vulnerability at line {vuln.sink_location[0]} using symbolic execution")
                else:
                    logger.info("Pruned vulnerability using symbolic execution")

        taint_vulns = verified_vulns

        secret_vulns = self._secret_scanner.scan(tree)
        # [20251216_FEATURE] v2.2.0 - SSR vulnerability detection
        ssr_vulns = detect_ssr_vulnerabilities(tree, framework=None, taint_tracker=self._taint_tracker)
        result.vulnerabilities = taint_vulns + secret_vulns + ssr_vulns

        result.taint_flows = {
            name: cast(TaintInfo, self._taint_tracker.get_taint(name))
            for name in self._current_taint_map.keys()
            if self._taint_tracker.get_taint(name) is not None
        }

        return result

    def _analyze_node(self, node: ast.AST, result: SecurityAnalysisResult) -> None:
        """Recursively analyze an AST node."""

        if isinstance(node, ast.Module):
            for child in node.body:
                self._analyze_node(child, result)

        elif isinstance(node, ast.FunctionDef):
            result.functions_analyzed.append(node.name)

            # [20251214_FEATURE] v2.0.0 - Detect web framework routes
            is_web_route = self._is_web_framework_route(node)

            # Mark function parameters as taint sources (untrusted input)
            for arg in node.args.args:
                param_name = arg.arg
                # Web routes have higher taint confidence
                taint_level = TaintLevel.HIGH if is_web_route else TaintLevel.HIGH
                taint_info = TaintInfo(
                    source=TaintSource.USER_INPUT,
                    level=taint_level,
                    source_location=(node.lineno, node.col_offset),
                    propagation_path=[],
                )
                if self._taint_tracker:
                    self._taint_tracker.mark_tainted(param_name, taint_info)
                    self._current_taint_map[param_name] = taint_info

            for child in node.body:
                self._analyze_node(child, result)

        elif isinstance(node, ast.Assign):
            self._analyze_assignment(node)

        elif isinstance(node, ast.Expr):
            if isinstance(node.value, ast.Call):
                self._analyze_call(node.value, (node.lineno, node.col_offset))

        elif isinstance(node, ast.If):
            for child in node.body:
                self._analyze_node(child, result)
            for child in node.orelse:
                self._analyze_node(child, result)

        elif isinstance(node, ast.For) or isinstance(node, ast.While):
            for child in node.body:
                self._analyze_node(child, result)

        elif isinstance(node, ast.With):
            # Handle context manager assignments: with open(path) as f:
            for item in node.items:
                # First, analyze the context expression as a potential sink
                if isinstance(item.context_expr, ast.Call):
                    self._analyze_call(item.context_expr, (node.lineno, node.col_offset))

                # Then propagate taint to the bound variable
                if item.optional_vars and isinstance(item.optional_vars, ast.Name):
                    target_var = item.optional_vars.id
                    # Extract variables from the context expression (e.g., open(full_path))
                    source_vars = self._extract_variable_names(item.context_expr)
                    # Propagate taint from source variables to the target
                    # signature: propagate_assignment(target, source_names: List[str])
                    if source_vars and self._taint_tracker:
                        self._taint_tracker.propagate_assignment(target_var, source_vars)

            for child in node.body:
                self._analyze_node(child, result)

        elif isinstance(node, ast.Try):
            for child in node.body:
                self._analyze_node(child, result)
            for handler in node.handlers:
                for child in handler.body:
                    self._analyze_node(child, result)

        elif isinstance(node, ast.Return):
            # Analyze return statements for sink calls
            # e.g., return render_template_string(user_input)
            if node.value and isinstance(node.value, ast.Call):
                self._analyze_call(node.value, (node.lineno, node.col_offset))
            # [20251214_FEATURE] v2.0.0 - Detect XSS in return statements with HTML
            elif node.value:
                self._check_html_return(node)

    def _check_html_return(self, node: ast.Return) -> None:
        """
        [20251214_FEATURE] v2.0.0 - Check for XSS in return statements.

        Detects patterns like:
        - return f"<html>{user_input}</html>"
        - return "<div>" + user_input + "</div>"

        Args:
            node: Return AST node
        """
        if not node.value:
            return

        location = (node.lineno, node.col_offset)

        # Check for JoinedStr (f-string)
        if isinstance(node.value, ast.JoinedStr):
            self._check_fstring_html_xss(node.value, location)
        # Check for BinOp (string concatenation)
        elif isinstance(node.value, ast.BinOp):
            self._check_concat_html_xss(node.value, location)

    def _check_fstring_html_xss(self, fstring: ast.JoinedStr, location: tuple[int, int]) -> None:
        """
        Check f-string return for XSS vulnerability.

        Detects: return f"<html>{tainted_var}</html>"
        """
        # Check if the f-string contains HTML-like content
        has_html = False
        tainted_vars = []

        for value in fstring.values:
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                # Check for HTML tags in the constant parts
                if "<" in value.value or ">" in value.value:
                    has_html = True
            elif isinstance(value, ast.FormattedValue):
                # Extract variable names from formatted values
                var_names = self._extract_variable_names(value.value)
                for var in var_names:
                    if var in self._current_taint_map:
                        tainted_vars.append(var)

        # If we have HTML and tainted variables, flag as XSS
        if has_html and tainted_vars and self._taint_tracker:
            for var in tainted_vars:
                taint_info = self._current_taint_map[var]
                vuln = Vulnerability(
                    sink_type=SecuritySink.HTML_OUTPUT,
                    taint_source=taint_info.source,
                    taint_path=[var, "f-string interpolation", "return statement"],
                    sink_location=location,
                    source_location=taint_info.source_location,
                    sanitizers_applied=taint_info.sanitizers_applied,
                )
                self._taint_tracker._vulnerabilities.append(vuln)

    def _check_concat_html_xss(self, binop: ast.BinOp, location: tuple[int, int]) -> None:
        """
        Check string concatenation return for XSS vulnerability.

        Detects: return "<div>" + user_input + "</div>"
        """
        if not isinstance(binop.op, ast.Add):
            return

        # Collect all parts of the concatenation
        parts = []
        self._collect_concat_parts(binop, parts)

        has_html = False
        tainted_vars = []

        for part in parts:
            if isinstance(part, ast.Constant) and isinstance(part.value, str):
                if "<" in part.value or ">" in part.value:
                    has_html = True
            elif isinstance(part, ast.Name):
                if part.id in self._current_taint_map:
                    tainted_vars.append(part.id)

        if has_html and tainted_vars and self._taint_tracker:
            for var in tainted_vars:
                taint_info = self._current_taint_map[var]
                vuln = Vulnerability(
                    sink_type=SecuritySink.HTML_OUTPUT,
                    taint_source=taint_info.source,
                    taint_path=[var, "string concatenation", "return statement"],
                    sink_location=location,
                    source_location=taint_info.source_location,
                    sanitizers_applied=taint_info.sanitizers_applied,
                )
                self._taint_tracker._vulnerabilities.append(vuln)

    def _collect_concat_parts(self, node: ast.expr, parts: list[ast.expr]) -> None:
        """Recursively collect parts of string concatenation."""
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            self._collect_concat_parts(node.left, parts)
            self._collect_concat_parts(node.right, parts)
        else:
            parts.append(node)

    def _analyze_assignment(self, node: ast.Assign) -> None:
        """Analyze an assignment for taint propagation."""
        # Get target name(s)
        targets = []
        for target in node.targets:
            if isinstance(target, ast.Name):
                targets.append(target.id)
            elif isinstance(target, ast.Tuple):
                for elt in target.elts:
                    if isinstance(elt, ast.Name):
                        targets.append(elt.id)

        if not targets or not self._taint_tracker:
            return

        # Check if RHS is a call that might be a sink (even if also an assignment)
        # e.g., html = render_template_string(user) - user reaches the sink
        if isinstance(node.value, ast.Call):
            self._analyze_call(node.value, (node.lineno, node.col_offset))

        # Check if RHS introduces taint
        source_info = self._check_taint_source(node.value, (node.lineno, node.col_offset))

        if source_info is not None:
            # RHS is a taint source
            for target in targets:
                self._taint_tracker.mark_tainted(target, source_info)
                self._current_taint_map[target] = source_info
        else:
            # Check if RHS is a sanitizer call wrapping tainted data
            sanitizer_result = self._check_sanitizer_call(node.value)

            if sanitizer_result is not None:
                sanitizer_name, sanitized_taint = sanitizer_result
                for target in targets:
                    # Apply sanitizer to propagated taint
                    final_taint = sanitized_taint.apply_sanitizer(sanitizer_name)
                    self._taint_tracker.mark_tainted(target, final_taint)
                    self._current_taint_map[target] = final_taint
            else:
                # Check if RHS propagates taint (no sanitizer)
                source_vars = self._extract_variable_names(node.value)
                for target in targets:
                    propagated = self._taint_tracker.propagate_assignment(target, source_vars)
                    if propagated is not None:
                        self._current_taint_map[target] = propagated

    def _check_sanitizer_call(self, node: ast.expr) -> tuple[str, TaintInfo] | None:
        """
        Check if an expression is a sanitizer call wrapping tainted data.

        Returns:
            Tuple of (sanitizer_name, source_taint) if sanitizer found, None otherwise
        """
        if not isinstance(node, ast.Call) or not self._taint_tracker:
            return None

        func_name = self._get_call_name(node)
        if func_name is None:
            return None

        # Check if this function is a registered sanitizer
        if func_name not in SANITIZER_REGISTRY and func_name not in SANITIZER_PATTERNS:
            return None

        # Get the sanitizer name (prefer registry, fallback to patterns)
        sanitizer_name = func_name

        # Find tainted arguments
        for arg in node.args:  # pragma: no branch - loop continuation
            if isinstance(arg, ast.Name):
                taint = self._taint_tracker.get_taint(arg.id)
                if taint is not None:
                    return (sanitizer_name, taint)
            elif isinstance(arg, ast.BinOp):  # pragma: no branch
                # Tainted expression in argument
                arg_vars = self._extract_variable_names(arg)
                for var in arg_vars:  # pragma: no branch - loop continuation
                    taint = self._taint_tracker.get_taint(var)
                    if taint is not None:  # pragma: no branch
                        return (sanitizer_name, taint)

        return None

    def _analyze_call(self, node: ast.Call, location: tuple[int, int]) -> None:
        """Analyze a function call for sink detection."""
        if not self._taint_tracker:
            return

        # Recursively analyze chained calls like hashlib.md5(...).hexdigest()
        # The inner call (hashlib.md5) is in node.func.value when node.func is Attribute
        if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Call):
            self._analyze_call(node.func.value, location)

        # Also check args that are calls
        # Also check keyword args that are calls (e.g., annotate(val=RawSQL(...)))
        for keyword in node.keywords:
            if isinstance(keyword.value, ast.Call):
                self._analyze_call(keyword.value, location)
        for arg in node.args:
            if isinstance(arg, ast.Call):
                self._analyze_call(arg, location)

        # Get the function name
        func_name = self._get_call_name(node)

        if func_name is None:
            return

        # [20251214_FEATURE] v2.0.0 - Check for dangerous sinks regardless of taint
        self._check_dangerous_patterns(func_name, node, location)

        # Check if this is a security sink
        sink = SINK_PATTERNS.get(func_name)

        if sink is not None:
            # Check all arguments for taint
            for arg in node.args:
                if isinstance(arg, ast.Name):
                    self._taint_tracker.check_sink(arg.id, sink, location)
                elif isinstance(arg, ast.BinOp):
                    # String concatenation in argument
                    arg_vars = self._extract_variable_names(arg)
                    for var in arg_vars:
                        self._taint_tracker.check_sink(var, sink, location)
                elif isinstance(arg, ast.JoinedStr):
                    # f-string
                    arg_vars = self._extract_variable_names(arg)
                    for var in arg_vars:
                        self._taint_tracker.check_sink(var, sink, location)
                elif isinstance(arg, ast.Call):
                    # Method call on tainted variable: var.method()
                    # e.g., user_data.encode() where user_data is tainted
                    arg_vars = self._extract_variable_names(arg)
                    for var in arg_vars:
                        self._taint_tracker.check_sink(var, sink, location)
                # [20251229_FEATURE] v3.0.4 - Type System Evaporation: Check dict values
                elif isinstance(arg, ast.Dict):
                    # Dictionary literal: jsonify({"key": tainted_value})
                    # Check all values in the dictionary for taint
                    for value in arg.values:
                        if value is not None:  # None for **kwargs unpacking
                            arg_vars = self._extract_variable_names(value)
                            for var in arg_vars:
                                self._taint_tracker.check_sink(var, sink, location)

        # Check if this is a sanitizer
        sanitizer = SANITIZER_PATTERNS.get(func_name)

        if sanitizer is not None:
            # Get the variable being sanitized
            for arg in node.args:
                if isinstance(arg, ast.Name):
                    self._taint_tracker.apply_sanitizer(arg.id, sanitizer)

    def _check_taint_source(self, node: ast.expr, location: tuple[int, int]) -> TaintInfo | None:
        """Check if an expression is a taint source."""

        if isinstance(node, ast.Call):
            func_name = self._get_call_name(node)

            if func_name is not None:
                source = TAINT_SOURCE_PATTERNS.get(func_name)

                if source is not None:
                    return TaintInfo(
                        source=source,
                        level=TaintLevel.HIGH,
                        source_location=location,
                        propagation_path=[],
                    )

        elif isinstance(node, ast.Subscript):
            # e.g., request.args["id"]
            call_name = self._get_subscript_base(node)

            if call_name is not None:
                source = TAINT_SOURCE_PATTERNS.get(call_name)

                if source is not None:
                    return TaintInfo(
                        source=source,
                        level=TaintLevel.HIGH,
                        source_location=location,
                        propagation_path=[],
                    )

        # [20251229_FEATURE] v3.0.4 - Type System Evaporation: Handle BoolOp (or/and)
        # e.g., body = request.get_json() or {}
        # The left operand may be a taint source
        elif isinstance(node, ast.BoolOp):
            for value in node.values:
                result = self._check_taint_source(value, location)
                if result is not None:
                    return result

        return None

    def _get_call_name(self, node: ast.Call) -> str | None:
        """Get the full dotted name of a function call."""
        if isinstance(node.func, ast.Name):
            return node.func.id
        elif isinstance(node.func, ast.Attribute):
            parts = []
            current = node.func

            while isinstance(current, ast.Attribute):  # pragma: no branch - loop exit
                parts.append(current.attr)
                current = current.value

            if isinstance(current, ast.Name):
                parts.append(current.id)
                return ".".join(reversed(parts))

        return None

    def _get_subscript_base(self, node: ast.Subscript) -> str | None:
        """Get the base name for a subscript like request.args["id"]."""
        if isinstance(node.value, ast.Attribute):
            parts = []
            current = node.value

            while isinstance(current, ast.Attribute):
                parts.append(current.attr)
                current = current.value

            if isinstance(current, ast.Name):
                parts.append(current.id)
                return ".".join(reversed(parts))

        return None

    def _check_dangerous_patterns(self, func_name: str, node: ast.Call, location: tuple[int, int]) -> None:
        """
        [20251214_FEATURE] v2.0.0 - Check for dangerous patterns regardless of taint.

        These patterns are always dangerous and should be flagged even without
        explicit taint tracking:
        - subprocess.run(..., shell=True) - command injection risk
        - eval() / exec() - code injection risk
        - pickle.loads() - deserialization attack risk
        - hashlib.md5() / hashlib.sha1() - weak cryptography

        Args:
            func_name: Name of the function being called
            node: AST Call node
            location: (line, column) tuple
        """
        # Check for shell=True in subprocess calls
        if func_name in ("subprocess.run", "subprocess.call", "subprocess.Popen"):
            for keyword in node.keywords:
                if keyword.arg == "shell":
                    # Check if shell=True
                    if isinstance(keyword.value, ast.Constant) and keyword.value.value is True:
                        self._add_dangerous_pattern_vuln(
                            sink_type=SecuritySink.SHELL_COMMAND,
                            description=f"{func_name}(shell=True) is dangerous - command injection risk",
                            location=location,
                        )
                    elif isinstance(keyword.value, ast.Name):
                        # shell=some_variable - flag as potential risk
                        self._add_dangerous_pattern_vuln(
                            sink_type=SecuritySink.SHELL_COMMAND,
                            description=f"{func_name}(shell=...) with variable shell argument - verify it's not True",
                            location=location,
                        )

        # Check for always-dangerous functions
        dangerous_funcs = {
            "eval": (
                SecuritySink.EVAL,
                "eval() executes arbitrary code - use ast.literal_eval() for data",
            ),
            "exec": (
                SecuritySink.EVAL,
                "exec() executes arbitrary code - avoid if possible",
            ),
            "pickle.loads": (
                SecuritySink.DESERIALIZATION,
                "pickle.loads() can execute arbitrary code on untrusted data",
            ),
            "pickle.load": (
                SecuritySink.DESERIALIZATION,
                "pickle.load() can execute arbitrary code on untrusted data",
            ),
            "_pickle.loads": (
                SecuritySink.DESERIALIZATION,
                "pickle deserialization on untrusted data is dangerous",
            ),
            "_pickle.load": (
                SecuritySink.DESERIALIZATION,
                "pickle deserialization on untrusted data is dangerous",
            ),
            "yaml.load": (
                SecuritySink.DESERIALIZATION,
                "yaml.load() is unsafe - use yaml.safe_load()",
            ),
            "yaml.unsafe_load": (
                SecuritySink.DESERIALIZATION,
                "yaml.unsafe_load() can execute arbitrary code",
            ),
        }

        if func_name in dangerous_funcs:
            sink_type, description = dangerous_funcs[func_name]
            self._add_dangerous_pattern_vuln(sink_type, description, location)

        # Check for weak cryptography (always flag, not just when used for passwords)
        weak_crypto_funcs = {
            "hashlib.md5": "MD5 is cryptographically broken - use SHA-256 or better",
            "hashlib.sha1": "SHA-1 is cryptographically weak - use SHA-256 or better",
            "MD5.new": "MD5 is cryptographically broken - use SHA-256 or better",
            "SHA.new": "SHA-1 is cryptographically weak - use SHA-256 or better",
            "Crypto.Hash.MD5": "MD5 is cryptographically broken",
            "Crypto.Hash.SHA": "SHA-1 is cryptographically weak",
        }

        if func_name in weak_crypto_funcs:
            self._add_dangerous_pattern_vuln(
                sink_type=SecuritySink.WEAK_CRYPTO,
                description=weak_crypto_funcs[func_name],
                location=location,
            )

    def _add_dangerous_pattern_vuln(self, sink_type: SecuritySink, description: str, location: tuple[int, int]) -> None:
        """
        Add a vulnerability for a dangerous pattern (without taint tracking).

        Args:
            sink_type: Type of security sink
            description: Human-readable description of the issue
            location: (line, column) tuple
        """
        if not self._taint_tracker:
            return

        # Check for duplicates
        for v in self._taint_tracker.get_vulnerabilities():
            if v.sink_location == location and v.sink_type == sink_type:
                return  # Already reported

        vuln = Vulnerability(
            sink_type=sink_type,
            taint_source=TaintSource.UNKNOWN,
            taint_path=[description],
            sink_location=location,
            source_location=None,
            sanitizers_applied=set(),
        )
        self._taint_tracker._vulnerabilities.append(vuln)

    def _extract_variable_names(self, node: ast.expr) -> list[str]:
        """Extract all variable names referenced in an expression."""
        names = []

        if isinstance(node, ast.Name):
            names.append(node.id)
        elif isinstance(node, ast.BinOp):
            names.extend(self._extract_variable_names(node.left))
            names.extend(self._extract_variable_names(node.right))
        elif isinstance(node, ast.Call):
            # Extract from arguments
            for arg in node.args:
                names.extend(self._extract_variable_names(arg))
            # Extract from method receiver: user_data.encode() -> user_data
            if isinstance(node.func, ast.Attribute):
                names.extend(self._extract_variable_names(node.func.value))
        elif isinstance(node, ast.JoinedStr):
            # f-string
            for value in node.values:
                if isinstance(value, ast.FormattedValue):
                    names.extend(self._extract_variable_names(value.value))
        elif isinstance(node, ast.Attribute):
            if isinstance(node.value, ast.Name):
                names.append(node.value.id)

        return names


def analyze_security(code: str) -> SecurityAnalysisResult:
    """
    Convenience function to analyze code for security vulnerabilities.

    Automatically loads custom sanitizers from pyproject.toml if present.

    Args:
        code: Python source code

    Returns:
        SecurityAnalysisResult with detected vulnerabilities

    Example:
        result = analyze_security('''
            user_input = input("Enter ID: ")
            os.system("rm " + user_input)
        ''')

        if result.has_vulnerabilities:
            print(result.summary())
    """
    _ensure_config_loaded()
    analyzer = SecurityAnalyzer()
    return analyzer.analyze(code)


def find_sql_injections(code: str) -> list[Vulnerability]:
    """
    Find SQL injection vulnerabilities in code.

    Args:
        code: Python source code

    Returns:
        List of SQL injection vulnerabilities
    """
    result = analyze_security(code)
    return result.get_sql_injections()


def find_xss(code: str) -> list[Vulnerability]:
    """
    Find XSS vulnerabilities in code.

    Args:
        code: Python source code

    Returns:
        List of XSS vulnerabilities
    """
    result = analyze_security(code)
    return result.get_xss()


def find_command_injections(code: str) -> list[Vulnerability]:
    """
    Find command injection vulnerabilities in code.

    Args:
        code: Python source code

    Returns:
        List of command injection vulnerabilities
    """
    result = analyze_security(code)
    return result.get_command_injections()


def find_path_traversals(code: str) -> list[Vulnerability]:
    """
    Find path traversal vulnerabilities in code.

    Args:
        code: Python source code

    Returns:
        List of path traversal vulnerabilities
    """
    result = analyze_security(code)
    return result.get_path_traversals()
