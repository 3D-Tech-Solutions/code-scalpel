"""Helper implementations for analyze_code MCP tool."""

from __future__ import annotations

import ast
import logging
import math
import os
import re
import time
from typing import Any

from code_scalpel.licensing.features import get_tool_capabilities, has_capability
from code_scalpel.licensing.jwt_validator import (
    get_current_tier as get_current_tier_from_license,
)
from code_scalpel.mcp.models.core import AnalysisResult, ClassInfo, FunctionInfo
from code_scalpel.parsing import ParsingError, parse_python_code

logger = logging.getLogger(__name__)

# [20260122_BUGFIX] Align analyze_code with MCP contract constant (100_000 chars in tests)
MAX_CODE_SIZE = 100_000

# Caching enabled by default
CACHE_ENABLED = os.environ.get("CODE_SCALPEL_CACHE_ENABLED", "1") != "0"

# [20251231_FEATURE] v3.3.x - Best-effort enrichments for analyze_code
_ANALYZE_CODE_COMPLEXITY_HISTORY: dict[str, list[dict[str, Any]]] = {}

__all__ = [
    "_analyze_code_sync",
    "_analyze_java_code",
    "_analyze_javascript_code",
    "_walk_ts_tree",
    "_detect_frameworks_from_code",
    "_detect_dead_code_hints_python",
    "_summarize_decorators_python",
    "_summarize_types_python",
    "_compute_api_surface_from_symbols",
    "_priority_sort",
    "_update_and_get_complexity_trends",
]


def _get_cache():
    """Get the analysis cache (lazy initialization)."""
    if not CACHE_ENABLED:
        return None
    try:
        # [20251223_CONSOLIDATION] Import from unified cache
        from code_scalpel.cache import get_cache

        return get_cache()
    except ImportError:
        logger.warning("Cache module not available")
        return None


def _validate_code(code: str) -> tuple[bool, str | None]:
    """Validate code before analysis."""
    if not code:
        return False, "Code cannot be empty"
    if not isinstance(code, str):
        return False, "Code must be a string"
    if len(code) > MAX_CODE_SIZE:
        return False, f"Code exceeds maximum size of {MAX_CODE_SIZE} characters"
    return True, None


def _count_complexity(tree: ast.AST) -> int:
    """Estimate cyclomatic complexity."""
    complexity = 1
    for node in ast.walk(tree):
        if isinstance(node, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
            complexity += 1
        elif isinstance(node, ast.BoolOp) and isinstance(node.op, (ast.And, ast.Or)):
            complexity += len(node.values) - 1
    return complexity


def _calculate_cognitive_complexity_python(tree: ast.AST) -> int:
    """
    Calculate cognitive complexity for Python code.

    [20251229_FEATURE] v3.3.0 - Implements Sonar cognitive complexity metric.

    Cognitive complexity measures code understandability by penalizing:
    - Nested control structures (heavier weight)
    - Control flow breaks (continue, break, return)
    - Recursive calls

    Returns:
        int: Cognitive complexity score
    """
    complexity = 0

    def visit_node(node: ast.AST, parent_nesting: int) -> None:
        nonlocal complexity
        local_complexity = 0
        current_nesting = parent_nesting

        # Increment for control structures
        if isinstance(node, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
            local_complexity = 1 + current_nesting
            current_nesting += 1
        elif isinstance(node, ast.BoolOp):
            # Logical operators add complexity
            local_complexity = len(node.values) - 1
        elif isinstance(node, (ast.Break, ast.Continue, ast.Return)):
            # Control flow breaks
            local_complexity = 1
        elif isinstance(node, ast.Lambda):
            # Lambdas increase nesting
            current_nesting += 1

        complexity += local_complexity

        # Recursively visit children
        for child in ast.iter_child_nodes(node):
            visit_node(child, current_nesting)

    visit_node(tree, 0)
    return complexity


def _detect_code_smells_python(tree: ast.AST, code: str) -> list[str]:
    """
    Detect code smells in Python code.

    [20251229_FEATURE] v3.3.0 - Code smell detection for PRO tier.

    Detects:
    - Long methods (>50 lines)
    - God classes (>10 methods)
    - Too many parameters (>5 parameters)
    - Deep nesting (>4 levels)

    Returns:
        list[str]: List of code smell descriptions
    """
    smells = []
    code.splitlines()

    def _max_nesting(n: ast.AST, depth: int = 0) -> int:
        depths = [depth]
        for child in ast.iter_child_nodes(n):
            if isinstance(
                child,
                (
                    ast.If,
                    ast.For,
                    ast.While,
                    ast.Try,
                    ast.With,
                    ast.AsyncWith,
                    ast.FunctionDef,
                    ast.AsyncFunctionDef,
                ),
            ):
                depths.append(_max_nesting(child, depth + 1))
            else:
                depths.append(_max_nesting(child, depth))
        return max(depths) if depths else depth

    for node in ast.walk(tree):
        # Long method detection
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if hasattr(node, "end_lineno") and node.end_lineno and node.lineno:
                method_length = node.end_lineno - node.lineno
                if method_length > 50:
                    smells.append(
                        f"Long method '{node.name}' ({method_length} lines) "
                        f"at line {node.lineno}. Consider breaking into smaller functions."
                    )

            # Too many parameters
            if len(node.args.args) > 5:
                smells.append(
                    f"Method '{node.name}' has {len(node.args.args)} parameters "
                    f"at line {node.lineno}. Consider using parameter objects."
                )

            # Deep nesting and high complexity hints
            depth = _max_nesting(node, 0)
            if depth > 4:
                smells.append(f"Method '{node.name}' has deep nesting (>{depth} levels) at line {node.lineno}.")
            try:
                func_tree = ast.Module(body=node.body, type_ignores=[])
                func_complexity = _count_complexity(func_tree)
                if func_complexity > 10:
                    smells.append(
                        f"Method '{node.name}' has high cyclomatic complexity ({func_complexity}) at line {node.lineno}."
                    )
            except Exception:
                pass

        # God class detection
        elif isinstance(node, ast.ClassDef):
            methods = [n for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
            if len(methods) > 10:
                smells.append(
                    f"God class '{node.name}' with {len(methods)} methods "
                    f"at line {node.lineno}. Consider splitting responsibilities."
                )

    return smells


# [20251225_FEATURE] Tier-gated advanced metrics and detections for analyze_code
def _compute_halstead_metrics_python(tree: ast.AST) -> dict[str, float]:
    """Compute Halstead metrics for Python code using AST traversal."""
    operators: list[str] = []
    operands: list[str] = []

    def op_name(node: ast.AST) -> str:
        return type(node).__name__

    for node in ast.walk(tree):
        if isinstance(node, (ast.BinOp, ast.BoolOp, ast.UnaryOp, ast.Compare)):
            operators.append(op_name(node))
        elif isinstance(node, (ast.Assign, ast.AugAssign, ast.AnnAssign)):
            operators.append(op_name(node))
        elif isinstance(node, ast.Call):
            operators.append(op_name(node))
        elif isinstance(node, ast.IfExp):
            operators.append(op_name(node))

        if isinstance(node, ast.Name):
            operands.append(node.id)
        elif isinstance(node, ast.Constant):
            operands.append(repr(node.value))

    distinct_operators = len(set(operators))
    distinct_operands = len(set(operands))
    total_operators = len(operators)
    total_operands = len(operands)

    vocabulary = distinct_operators + distinct_operands
    length = total_operators + total_operands
    volume = length * math.log2(vocabulary) if vocabulary > 0 else 0.0
    difficulty = (distinct_operators / 2) * (total_operands / distinct_operands) if distinct_operands > 0 else 0.0
    effort = difficulty * volume

    return {
        "n1": float(distinct_operators),
        "n2": float(distinct_operands),
        "N1": float(total_operators),
        "N2": float(total_operands),
        "vocabulary": float(vocabulary),
        "length": float(length),
        "volume": float(volume),
        "difficulty": float(difficulty),
        "effort": float(effort),
    }


def _detect_duplicate_code_blocks(code: str, min_lines: int = 5) -> list[dict[str, Any]]:
    """Detect duplicate code blocks using line-hash sliding windows."""
    lines = [ln.strip() for ln in code.splitlines() if ln.strip() and not ln.strip().startswith("#")]
    if len(lines) < min_lines:
        return []

    window_map: dict[str, list[int]] = {}
    for i in range(len(lines) - min_lines + 1):
        window = "\n".join(lines[i : i + min_lines])
        block_hash = hash(window)
        window_map.setdefault(str(block_hash), []).append(i + 1)

    duplicates: list[dict[str, Any]] = []
    for block_hash, occurrences in window_map.items():
        if len(occurrences) > 1:
            duplicates.append({"hash": block_hash, "occurrences": occurrences})
    return duplicates


def _build_dependency_graph_python(tree: ast.AST) -> dict[str, list[str]]:
    """Build a lightweight intra-module call graph for Python code."""
    graph: dict[str, list[str]] = {}

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            caller = node.name
            callees: set[str] = set()
            for child in ast.walk(node):
                if isinstance(child, ast.Call):
                    func = child.func
                    if isinstance(func, ast.Name):
                        callees.add(func.id)
                    elif isinstance(func, ast.Attribute):
                        callees.add(func.attr)
            graph[caller] = sorted(callees)
    return graph


def _detect_naming_issues_python(tree: ast.AST) -> list[str]:
    """Detect simple naming convention issues (snake_case for functions, PascalCase for classes)."""
    issues: list[str] = []
    snake = re.compile(r"^[a-z_][a-z0-9_]*$")
    pascal = re.compile(r"^[A-Z][A-Za-z0-9]*$")

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and not snake.match(node.name):
            issues.append(f"Function '{node.name}' should be snake_case at line {node.lineno}.")
        if isinstance(node, ast.ClassDef) and not pascal.match(node.name):
            issues.append(f"Class '{node.name}' should be PascalCase at line {node.lineno}.")
    return issues


def _apply_custom_rules_python(code: str) -> list[dict[str, Any]]:
    """Apply a small built-in custom rule set for Enterprise tier."""
    rules = {
        "CR-001": (re.compile(r"\beval\("), "Avoid eval for safety"),
        "CR-002": (re.compile(r"\bexec\("), "Avoid exec for safety"),
        "CR-003": (
            re.compile(r"\bprint\("),
            "Prefer structured logging over print",
        ),
    }
    findings: list[dict[str, Any]] = []
    for idx, line in enumerate(code.splitlines(), 1):
        for rule, (pattern, message) in rules.items():
            if pattern.search(line):
                findings.append(
                    {
                        "rule": rule,
                        "line": idx,
                        "detail": line.strip(),
                        "message": message,
                    }
                )
    return findings


def _detect_compliance_issues_python(tree: ast.AST, code: str) -> list[str]:
    """Detect simple compliance-related patterns (bare except, missing logging)."""
    issues: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler) and node.type is None:
            issues.append(f"Bare except detected at line {node.lineno}. Specify exception types.")
    if "password" in code.lower() and "hashlib" not in code.lower():
        issues.append("Potential plaintext password handling detected. Ensure hashing/encryption.")
    return issues


def _detect_organization_patterns_python(tree: ast.AST) -> list[str]:
    """Detect coarse architectural hints from class naming conventions."""
    patterns: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            if node.name.endswith("Controller"):
                patterns.append(f"Controller pattern detected: {node.name}")
            if node.name.endswith("Service"):
                patterns.append(f"Service pattern detected: {node.name}")
            if node.name.endswith("Repository"):
                patterns.append(f"Repository pattern detected: {node.name}")
    return patterns


def _analyze_java_code(code: str) -> AnalysisResult:
    """Analyze Java code using tree-sitter."""
    try:
        from code_scalpel.code_parsers.java_parsers.java_parser_treesitter import (
            JavaParser,
        )

        parser = JavaParser()
        result = parser.parse(code)
        return AnalysisResult(
            success=True,
            functions=result["functions"],
            classes=result["classes"],
            imports=result["imports"],
            complexity=result["complexity"],
            lines_of_code=result["lines_of_code"],
            issues=result["issues"],
        )
    except ImportError:
        return AnalysisResult(
            success=False,
            functions=[],
            classes=[],
            imports=[],
            complexity=0,
            lines_of_code=0,
            error="Java support not available. Please install tree-sitter and tree-sitter-java.",
        )
    except Exception as e:
        return AnalysisResult(
            success=False,
            functions=[],
            classes=[],
            imports=[],
            complexity=0,
            lines_of_code=0,
            error=f"Java analysis failed: {str(e)}.",
        )


def _analyze_javascript_code(code: str, is_typescript: bool = False) -> AnalysisResult:
    """
    Analyze JavaScript/TypeScript code using tree-sitter.

    [20251220_FEATURE] v3.0.4 - Multi-language analyze_code support.
    [20251220_BUGFIX] v3.0.5 - Consolidated tree-sitter imports.
    """
    try:
        from tree_sitter import Language, Parser

        if is_typescript:
            import tree_sitter_typescript as ts_ts

            lang = Language(ts_ts.language_typescript())
        else:
            import tree_sitter_javascript as ts_js

            lang = Language(ts_js.language())

        parser = Parser(lang)
        tree = parser.parse(bytes(code, "utf-8"))

        functions = []
        function_details = []
        classes = []
        class_details = []
        imports = []

        def walk_tree(node, depth=0):
            """Walk tree-sitter tree to extract structure."""
            node_type = node.type

            # Functions (function declarations, arrow functions, methods)
            if node_type in (
                "function_declaration",
                "function",
                "generator_function_declaration",
            ):
                name_node = node.child_by_field_name("name")
                name = name_node.text.decode("utf-8") if name_node else "<anonymous>"
                functions.append(name)
                function_details.append(
                    FunctionInfo(
                        name=name,
                        lineno=node.start_point[0] + 1,
                        end_lineno=node.end_point[0] + 1,
                        is_async=any(c.type == "async" for c in node.children),
                    )
                )

            # Arrow functions with variable declaration
            elif node_type == "lexical_declaration" or node_type == "variable_declaration":
                for child in node.children:
                    if child.type == "variable_declarator":
                        name_node = child.child_by_field_name("name")
                        value_node = child.child_by_field_name("value")
                        if value_node and value_node.type == "arrow_function":
                            name = name_node.text.decode("utf-8") if name_node else "<anonymous>"
                            functions.append(name)
                            function_details.append(
                                FunctionInfo(
                                    name=name,
                                    lineno=child.start_point[0] + 1,
                                    end_lineno=child.end_point[0] + 1,
                                    is_async=any(c.type == "async" for c in value_node.children),
                                )
                            )

            # Classes
            elif node_type == "class_declaration":
                name_node = node.child_by_field_name("name")
                name = name_node.text.decode("utf-8") if name_node else "<anonymous>"

                # Extract methods
                methods = []
                body_node = node.child_by_field_name("body")
                if body_node:
                    for member in body_node.children:
                        if member.type == "method_definition":
                            method_name_node = member.child_by_field_name("name")
                            if method_name_node:
                                methods.append(method_name_node.text.decode("utf-8"))

                classes.append(name)
                class_details.append(
                    ClassInfo(
                        name=name,
                        lineno=node.start_point[0] + 1,
                        end_lineno=node.end_point[0] + 1,
                        methods=methods,
                    )
                )

            # Imports (ES6 import statements)
            elif node_type == "import_statement":
                source_node = node.child_by_field_name("source")
                if source_node:
                    module = source_node.text.decode("utf-8").strip("'\"")
                    imports.append(module)

            # CommonJS require
            elif node_type == "call_expression":
                func_node = node.child_by_field_name("function")
                if func_node and func_node.text == b"require":
                    args_node = node.child_by_field_name("arguments")
                    if args_node and args_node.children:
                        for arg in args_node.children:
                            if arg.type == "string":
                                imports.append(arg.text.decode("utf-8").strip("'\""))

            # Recurse into children
            for child in node.children:
                walk_tree(child, depth + 1)

        walk_tree(tree.root_node)

        # Estimate complexity (branches)
        complexity = 1
        for node in _walk_ts_tree(tree.root_node):
            if node.type in (
                "if_statement",
                "while_statement",
                "for_statement",
                "for_in_statement",
                "catch_clause",
                "ternary_expression",
                "switch_case",
            ):
                complexity += 1
            elif node.type == "binary_expression":
                op_node = node.child_by_field_name("operator")
                if op_node and op_node.text in (b"&&", b"||"):
                    complexity += 1

        lang_name = "TypeScript" if is_typescript else "JavaScript"
        return AnalysisResult(
            success=True,
            functions=functions,
            classes=classes,
            imports=imports,
            complexity=complexity,
            lines_of_code=len(code.splitlines()),
            issues=[],
            function_details=function_details,
            class_details=class_details,
        )
    except ImportError as e:
        lang_name = "TypeScript" if is_typescript else "JavaScript"
        return AnalysisResult(
            success=False,
            functions=[],
            classes=[],
            imports=[],
            complexity=0,
            lines_of_code=0,
            error=f"{lang_name} support not available. Please install tree-sitter packages: {str(e)}.",
        )
    except Exception as e:
        lang_name = "TypeScript" if is_typescript else "JavaScript"
        return AnalysisResult(
            success=False,
            functions=[],
            classes=[],
            imports=[],
            complexity=0,
            lines_of_code=0,
            error=f"{lang_name} analysis failed: {str(e)}.",
        )


def _walk_ts_tree(node):
    """Generator to walk all nodes in a tree-sitter tree."""
    yield node
    for child in node.children:
        yield from _walk_ts_tree(child)


def _detect_frameworks_from_code(
    code: str,
    language: str,
    imports: list[str] | None = None,
) -> list[str]:
    """Heuristic framework detection for a single code blob.

    This intentionally remains lightweight and non-executing.
    """
    lang = (language or "").lower()
    imports_set = set(imports or [])
    code_lower = code.lower()
    frameworks: set[str] = set()

    # Python web frameworks
    if any(i.startswith("django") for i in imports_set) or "django" in code_lower:
        frameworks.add("django")
    if any(i.startswith("flask") for i in imports_set) or "flask" in code_lower:
        frameworks.add("flask")
    if any(i.startswith("fastapi") for i in imports_set) or "fastapi" in code_lower:
        frameworks.add("fastapi")

    # Java / Spring
    if lang == "java" or "org.springframework" in code_lower or "@component" in code_lower:
        if "springframework" in code_lower or "@autowired" in code_lower or "@component" in code_lower:
            frameworks.add("spring")

    # React / Next.js style patterns (JS/TS)
    if lang in {"javascript", "typescript"} or "tsx" in lang:
        if "from 'react'" in code_lower or 'from "react"' in code_lower or "react" in code_lower:
            if "usestate(" in code_lower or "useeffect(" in code_lower or "usecontext(" in code_lower:
                frameworks.add("react")
            # Even without hooks, a React import is a strong signal.
            elif "react" in code_lower:
                frameworks.add("react")

    return sorted(frameworks)


def _detect_dead_code_hints_python(tree: ast.AST, code: str) -> list[str]:
    """Best-effort dead code hints for Python.

    This is intentionally conservative: it flags obvious unreachable statements
    and unused imports in the single file.
    """
    hints: list[str] = []
    try:
        used_names: set[str] = set()
        imported_names: list[tuple[str, int]] = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                used_names.add(node.id)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.asname or alias.name.split(".")[0]
                    imported_names.append((name, getattr(node, "lineno", 0) or 0))
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    name = alias.asname or alias.name
                    imported_names.append((name, getattr(node, "lineno", 0) or 0))

        for name, lineno in imported_names:
            if name and name not in used_names:
                hints.append(f"Unused import '{name}' (L{lineno})")

        def _scan_block_for_unreachable(stmts: list[ast.stmt], scope: str) -> None:
            terminated = False
            for st in stmts:
                if terminated:
                    ln = getattr(st, "lineno", None)
                    hints.append(f"Unreachable statement after terminator in {scope} (L{ln})")
                    continue
                if isinstance(st, (ast.Return, ast.Raise)):  # simple terminators
                    terminated = True
                # Recurse into nested blocks for basic coverage
                if isinstance(st, ast.If):
                    _scan_block_for_unreachable(st.body or [], f"{scope} (if-body)")
                    _scan_block_for_unreachable(st.orelse or [], f"{scope} (if-else)")
                elif isinstance(st, (ast.For, ast.While, ast.With, ast.Try)):
                    _scan_block_for_unreachable(
                        getattr(st, "body", []) or [],
                        f"{scope} (loop/with/try)",
                    )
                    _scan_block_for_unreachable(getattr(st, "orelse", []) or [], f"{scope} (orelse)")
                    _scan_block_for_unreachable(getattr(st, "finalbody", []) or [], f"{scope} (finally)")
                    for h in getattr(st, "handlers", []) or []:
                        _scan_block_for_unreachable(getattr(h, "body", []) or [], f"{scope} (except)")

        for node in tree.body if isinstance(tree, ast.Module) else []:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                _scan_block_for_unreachable(node.body or [], f"function '{node.name}'")
            elif isinstance(node, ast.ClassDef):
                for inner in node.body:
                    if isinstance(inner, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        _scan_block_for_unreachable(
                            inner.body or [],
                            f"method '{node.name}.{inner.name}'",
                        )

    except Exception:
        return hints

    # Deduplicate while keeping stable order
    seen: set[str] = set()
    out: list[str] = []
    for h in hints:
        if h not in seen:
            seen.add(h)
            out.append(h)
    return out


def _summarize_decorators_python(tree: ast.AST) -> dict[str, Any]:
    decorators: set[str] = set()

    def _decorator_name(d: ast.AST) -> str:
        if isinstance(d, ast.Name):
            return d.id
        if isinstance(d, ast.Attribute):
            # best-effort flatten
            parts: list[str] = []
            cur: ast.AST | None = d
            while isinstance(cur, ast.Attribute):
                parts.append(cur.attr)
                cur = cur.value
            if isinstance(cur, ast.Name):
                parts.append(cur.id)
            return ".".join(reversed(parts))
        if isinstance(d, ast.Call):
            return _decorator_name(d.func)
        return d.__class__.__name__

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            for d in getattr(node, "decorator_list", []) or []:
                decorators.add(_decorator_name(d))

    return {"decorators": sorted(decorators), "decorator_count": len(decorators)}


def _summarize_types_python(tree: ast.AST) -> dict[str, Any]:
    total_funcs = 0
    funcs_with_any_annotations = 0
    annotated_params = 0
    annotated_returns = 0
    generic_like_uses = 0

    generic_names = {
        "list",
        "dict",
        "set",
        "tuple",
        "optional",
        "union",
        "sequence",
        "mapping",
        "iterable",
        "type",
        "callable",
        "generic",
    }

    def _subscript_head(n: ast.AST) -> str | None:
        if isinstance(n, ast.Subscript):
            v = n.value
            if isinstance(v, ast.Name):
                return v.id
            if isinstance(v, ast.Attribute):
                return v.attr
        return None

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            total_funcs += 1
            has_ann = False
            for a in list(getattr(node.args, "args", []) or []) + list(getattr(node.args, "kwonlyargs", []) or []):
                if getattr(a, "annotation", None) is not None:
                    annotated_params += 1
                    has_ann = True
            if (
                getattr(node.args, "vararg", None) is not None
                and getattr(node.args.vararg, "annotation", None) is not None
            ):
                annotated_params += 1
                has_ann = True
            if (
                getattr(node.args, "kwarg", None) is not None
                and getattr(node.args.kwarg, "annotation", None) is not None
            ):
                annotated_params += 1
                has_ann = True
            if getattr(node, "returns", None) is not None:
                annotated_returns += 1
                has_ann = True
            if has_ann:
                funcs_with_any_annotations += 1

        head = _subscript_head(node)
        if head and head.lower() in generic_names:
            generic_like_uses += 1

    return {
        "functions_total": total_funcs,
        "functions_with_any_annotations": funcs_with_any_annotations,
        "annotated_params": annotated_params,
        "annotated_returns": annotated_returns,
        "generic_type_uses": generic_like_uses,
    }


def _compute_api_surface_from_symbols(functions: list[str], classes: list[str]) -> dict[str, Any]:
    def _is_public(name: str) -> bool:
        # Treat async prefix as implementation detail in inventory
        norm = name.replace("async ", "")
        return bool(norm) and not norm.startswith("_")

    public_functions = sorted({f for f in functions if _is_public(f)})
    public_classes = sorted({c for c in classes if _is_public(c)})
    return {
        "public_functions": public_functions,
        "public_classes": public_classes,
        "public_function_count": len(public_functions),
        "public_class_count": len(public_classes),
    }


def _priority_sort(items: list[Any]) -> list[Any]:
    """Sort a list of issue/smell labels by severity keywords.

    If items are not strings, return them unchanged to avoid type errors.
    """

    if not items or not all(isinstance(s, str) for s in items):
        return list(items)

    def _rank(s: str) -> tuple[int, str]:
        low = s.lower()
        if "critical" in low:
            return (0, s)
        if "high" in low:
            return (1, s)
        if "medium" in low:
            return (2, s)
        if "low" in low:
            return (3, s)
        return (4, s)

    return sorted(items, key=_rank)


def _update_and_get_complexity_trends(
    *,
    file_path: str | None,
    cyclomatic: int,
    cognitive: int,
    max_points: int = 50,
) -> dict[str, Any] | None:
    if not file_path:
        return None
    key = str(file_path)
    history = _ANALYZE_CODE_COMPLEXITY_HISTORY.setdefault(key, [])
    history.append({"cyclomatic": cyclomatic, "cognitive": cognitive, "ts": time.time()})
    if len(history) > max_points:
        history[:] = history[-max_points:]

    if len(history) < 2:
        delta_cyclomatic = 0
        delta_cognitive = 0
    else:
        delta_cyclomatic = history[-1]["cyclomatic"] - history[0]["cyclomatic"]
        delta_cognitive = history[-1]["cognitive"] - history[0]["cognitive"]

    return {
        "file_path": key,
        "samples": history[-10:],
        "sample_count": len(history),
        "delta_cyclomatic": delta_cyclomatic,
        "delta_cognitive": delta_cognitive,
    }


def _analyze_code_sync(code: str, language: str = "auto", file_path: str | None = None) -> AnalysisResult:
    """Synchronous implementation of analyze_code.

    [20251219_BUGFIX] v3.0.4 - Auto-detect language from content if not specified.
    [20251219_BUGFIX] v3.0.4 - Strip UTF-8 BOM if present.
    [20251220_FEATURE] v3.0.4 - Multi-language support for JavaScript/TypeScript.
    [20251221_FEATURE] v3.1.0 - Use unified_extractor for language detection.
    [20251229_FEATURE] v3.3.0 - Tier-based feature gating for advanced metrics.

    Tier Capabilities:
        COMMUNITY: Basic AST parsing, function/class inventory, cyclomatic complexity
        PRO: + Cognitive complexity, code smell detection
        ENTERPRISE: + Custom rules, compliance checks, organization patterns
    """
    # [20251229_FEATURE] v3.3.0 - Detect tier and get capabilities
    tier = get_current_tier_from_license()
    capabilities = get_tool_capabilities("analyze_code", tier)
    logger.debug(
        f"analyze_code running with tier={tier.title()}, capabilities={capabilities.get('capabilities', set())}"
    )

    # [20251219_BUGFIX] Strip UTF-8 BOM if present
    if code.startswith("\ufeff"):
        code = code[1:]

    # [20260121_BUGFIX] Enforce tier-based file size limits before parsing
    limit_mb = capabilities.get("limits", {}).get("max_file_size_mb")
    if limit_mb is not None and limit_mb >= 0:
        max_bytes = int(limit_mb * 1024 * 1024)
        if len(code.encode("utf-8")) > max_bytes:
            return AnalysisResult(
                success=False,
                functions=[],
                classes=[],
                imports=[],
                complexity=0,
                lines_of_code=0,
                error=(f"Input exceeds configured size limit of {limit_mb} MB for analyze_code"),
            )

    # [20251221_FEATURE] v3.1.0 - Use unified_extractor for language detection
    if language == "auto" or language is None:
        # [20251228_BUGFIX] Avoid deprecated shim imports.
        from code_scalpel.surgery.unified_extractor import Language, detect_language

        detected = detect_language(None, code)
        lang_map = {
            Language.PYTHON: "python",
            Language.JAVASCRIPT: "javascript",
            Language.TYPESCRIPT: "typescript",
            Language.JAVA: "java",
        }
        language = lang_map.get(detected, "python")

    # [20260110_FEATURE] v1.0 - Explicit language validation (BEFORE code validation)
    # Must happen before _validate_code() to prevent parsing unsupported languages as Python
    SUPPORTED_LANGUAGES = {"python", "javascript", "typescript", "java"}
    if language.lower() not in SUPPORTED_LANGUAGES:
        return AnalysisResult(
            success=False,
            functions=[],
            classes=[],
            imports=[],
            complexity=0,
            lines_of_code=0,
            error=f"Unsupported language '{language}'. Supported: {', '.join(sorted(SUPPORTED_LANGUAGES))}. Roadmap: Go/Rust in Q1 2026.",
        )

    valid, error = _validate_code(code)
    if not valid:
        return AnalysisResult(
            success=False,
            functions=[],
            classes=[],
            imports=[],
            complexity=0,
            lines_of_code=0,
            error=error,
        )

    # Check cache first
    cache = _get_cache()
    cache_config = {
        "language": language,
        "tier": tier,
    }  # [20251229_FEATURE] v3.3.0 - Include tier in cache key
    if cache:
        cached = cache.get(code, "analysis", cache_config)
        if cached is not None:
            logger.debug("Cache hit for analyze_code")
            # Convert dict back to AnalysisResult if needed
            if isinstance(cached, dict):
                # [20251228_BUGFIX] Backward-compatibility for cached entries
                # from token-saving schemas where `success` was omitted/None.
                if cached.get("success") is None:
                    cached["success"] = True
                return AnalysisResult(**cached)
            return cached

    if language.lower() == "java":
        result = _analyze_java_code(code)
        if result.success:
            # [20260110_FEATURE] Populate metadata fields
            result.language_detected = "java"
            result.tier_applied = tier

            if has_capability("analyze_code", "framework_detection", tier):
                result.frameworks = _detect_frameworks_from_code(code, "java", result.imports)

            if has_capability("analyze_code", "api_surface_analysis", tier):
                result.api_surface = _compute_api_surface_from_symbols(result.functions, result.classes)

            if has_capability("analyze_code", "priority_ordering", tier):
                result.issues = _priority_sort(result.issues)
                result.code_smells = _priority_sort(result.code_smells)
                result.dead_code_hints = _priority_sort(result.dead_code_hints)
                result.prioritized = True

            if has_capability("analyze_code", "complexity_trends", tier):
                result.complexity_trends = _update_and_get_complexity_trends(
                    file_path=file_path,
                    cyclomatic=result.complexity,
                    cognitive=getattr(result, "cognitive_complexity", 0) or 0,
                )
        if cache and result.success:
            cache.set(code, "analysis", result.model_dump(), cache_config)
        return result

    # [20251220_FEATURE] v3.0.4 - Route JavaScript/TypeScript to tree-sitter analyzer
    if language.lower() == "javascript":
        result = _analyze_javascript_code(code, is_typescript=False)
        if result.success:
            # [20260110_FEATURE] Populate metadata fields
            result.language_detected = "javascript"
            result.tier_applied = tier

            if has_capability("analyze_code", "framework_detection", tier):
                result.frameworks = _detect_frameworks_from_code(code, "javascript", result.imports)

            if has_capability("analyze_code", "api_surface_analysis", tier):
                result.api_surface = _compute_api_surface_from_symbols(result.functions, result.classes)

            if has_capability("analyze_code", "priority_ordering", tier):
                result.issues = _priority_sort(result.issues)
                result.code_smells = _priority_sort(result.code_smells)
                result.dead_code_hints = _priority_sort(result.dead_code_hints)
                result.prioritized = True

            if has_capability("analyze_code", "complexity_trends", tier):
                result.complexity_trends = _update_and_get_complexity_trends(
                    file_path=file_path,
                    cyclomatic=result.complexity,
                    cognitive=getattr(result, "cognitive_complexity", 0) or 0,
                )
        if cache and result.success:
            cache.set(code, "analysis", result.model_dump(), cache_config)
        return result

    if language.lower() == "typescript":
        result = _analyze_javascript_code(code, is_typescript=True)
        if result.success:
            # [20260110_FEATURE] Populate metadata fields
            result.language_detected = "typescript"
            result.tier_applied = tier

            if has_capability("analyze_code", "framework_detection", tier):
                result.frameworks = _detect_frameworks_from_code(code, "typescript", result.imports)

            if has_capability("analyze_code", "api_surface_analysis", tier):
                result.api_surface = _compute_api_surface_from_symbols(result.functions, result.classes)

            if has_capability("analyze_code", "priority_ordering", tier):
                result.issues = _priority_sort(result.issues)
                result.code_smells = _priority_sort(result.code_smells)
                result.dead_code_hints = _priority_sort(result.dead_code_hints)
                result.prioritized = True

            if has_capability("analyze_code", "complexity_trends", tier):
                result.complexity_trends = _update_and_get_complexity_trends(
                    file_path=file_path,
                    cyclomatic=result.complexity,
                    cognitive=getattr(result, "cognitive_complexity", 0) or 0,
                )
        if cache and result.success:
            cache.set(code, "analysis", result.model_dump(), cache_config)
        return result

    # Python analysis using unified parser
    # [20260119_FEATURE] Use parse_python_code for deterministic error handling
    try:
        tree, sanitization_report = parse_python_code(code)

        # Track parser warnings for sanitization
        parser_warnings: list[str] = []
        sanitization_dict: dict[str, Any] | None = None
        if sanitization_report.was_sanitized:
            parser_warnings.append(f"Code was auto-sanitized: {'; '.join(sanitization_report.changes)}")
            sanitization_dict = {
                "was_sanitized": True,
                "changes": sanitization_report.changes,
            }

        functions = []
        function_details = []
        classes = []
        class_details = []
        imports = []
        issues = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                functions.append(node.name)
                function_details.append(
                    FunctionInfo(
                        name=node.name,
                        lineno=node.lineno,
                        end_lineno=getattr(node, "end_lineno", None),
                        is_async=False,
                    )
                )
                # Flag potential issues
                if len(node.name) < 2:
                    issues.append(f"Function '{node.name}' has very short name")
            elif isinstance(node, ast.AsyncFunctionDef):
                functions.append(f"async {node.name}")
                function_details.append(
                    FunctionInfo(
                        name=node.name,
                        lineno=node.lineno,
                        end_lineno=getattr(node, "end_lineno", None),
                        is_async=True,
                    )
                )
            elif isinstance(node, ast.ClassDef):
                classes.append(node.name)
                # Extract method names
                methods = [n.name for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
                class_details.append(
                    ClassInfo(
                        name=node.name,
                        lineno=node.lineno,
                        end_lineno=getattr(node, "end_lineno", None),
                        methods=methods,
                    )
                )
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    imports.append(f"{module}.{alias.name}")

        # [20251229_FEATURE] v3.3.0 - Compute tier-based advanced metrics
        cognitive_complexity = 0
        code_smells = []
        halstead_metrics: dict[str, float] | None = None
        duplicate_code_blocks: list[dict[str, Any]] = []
        dependency_graph: dict[str, list[str]] = {}
        naming_issues: list[str] = []
        compliance_issues: list[str] = []
        custom_rule_violations: list[dict[str, Any]] = []
        organization_patterns: list[str] = []

        # [20251231_FEATURE] Additional tier-gated enrichments
        frameworks: list[str] = []
        dead_code_hints: list[str] = []
        decorator_summary: dict[str, Any] | None = None
        type_summary: dict[str, Any] | None = None
        architecture_patterns: list[str] = []
        technical_debt: dict[str, Any] | None = None
        api_surface: dict[str, Any] | None = None
        prioritized: bool = False
        complexity_trends: dict[str, Any] | None = None

        # [20251228_BUGFIX] Complexity metrics now available at COMMUNITY tier
        # COMMUNITY: Basic cyclomatic complexity
        # PRO: Add cognitive complexity, code smells, halstead metrics
        # ENTERPRISE: Add duplicate detection, dependency graph
        if has_capability("analyze_code", "complexity_metrics", tier):
            # Basic cyclomatic complexity available at Community
            cyclomatic = _count_complexity(tree)
            logger.debug(f"Computed cyclomatic complexity: {cyclomatic}")

            # PRO tier: Cognitive complexity
            if has_capability("analyze_code", "cognitive_complexity", tier):
                cognitive_complexity = _calculate_cognitive_complexity_python(tree)
                logger.debug(f"Computed cognitive complexity: {cognitive_complexity}")

            # PRO tier: Code smell detection
            if has_capability("analyze_code", "code_smells", tier):
                code_smells = _detect_code_smells_python(tree, code)
                logger.debug(f"Detected {len(code_smells)} code smells")

            if has_capability("analyze_code", "halstead_metrics", tier):
                halstead_metrics = _compute_halstead_metrics_python(tree)
                logger.debug("Computed Halstead metrics")

            if has_capability("analyze_code", "duplicate_code_detection", tier):
                duplicate_code_blocks = _detect_duplicate_code_blocks(code)
                logger.debug(f"Detected {len(duplicate_code_blocks)} duplicate code block(s)")

            if has_capability("analyze_code", "dependency_graph", tier):
                dependency_graph = _build_dependency_graph_python(tree)
                logger.debug("Built dependency graph")

        if has_capability("analyze_code", "naming_conventions", tier):
            naming_issues = _detect_naming_issues_python(tree)

        if has_capability("analyze_code", "custom_rules", tier):
            custom_rule_violations = _apply_custom_rules_python(code)

        if has_capability("analyze_code", "compliance_checks", tier):
            compliance_issues = _detect_compliance_issues_python(tree, code)

        if has_capability("analyze_code", "organization_patterns", tier):
            organization_patterns = _detect_organization_patterns_python(tree)

        if has_capability("analyze_code", "framework_detection", tier):
            frameworks = _detect_frameworks_from_code(code, "python", imports)

        if has_capability("analyze_code", "dead_code_detection", tier):
            dead_code_hints = _detect_dead_code_hints_python(tree, code)

        if has_capability("analyze_code", "decorator_analysis", tier):
            decorator_summary = _summarize_decorators_python(tree)
            type_summary = _summarize_types_python(tree)

        if has_capability("analyze_code", "architecture_patterns", tier):
            # Reuse org pattern detector output as a baseline.
            architecture_patterns = list(organization_patterns)
            for fw in frameworks:
                architecture_patterns.append(f"framework:{fw}")
            architecture_patterns = sorted({p for p in architecture_patterns if p})

        if has_capability("analyze_code", "technical_debt_scoring", tier):
            try:
                from code_scalpel.code_parsers.python_parsers.python_parsers_code_quality import (
                    PythonCodeQualityAnalyzer,
                )

                analyzer = PythonCodeQualityAnalyzer()
                report = analyzer.analyze_string(code, filename=file_path or "<string>")
                technical_debt = {
                    "technical_debt_hours": float(
                        getattr(
                            getattr(report, "technical_debt", None),
                            "total_hours",
                            0,
                        )
                        or 0
                    ),
                    "maintainability_index": float(
                        getattr(
                            getattr(report, "maintainability", None),
                            "maintainability_index",
                            0,
                        )
                        or 0
                    ),
                    "smell_count": int(getattr(report, "smell_count", 0) or 0),
                }
            except Exception as e:
                technical_debt = {"error": f"Technical debt scoring failed: {e}"}

        if has_capability("analyze_code", "api_surface_analysis", tier):
            api_surface = _compute_api_surface_from_symbols(functions, classes)

        if has_capability("analyze_code", "priority_ordering", tier):
            issues = _priority_sort(issues)
            code_smells = _priority_sort(code_smells)
            dead_code_hints = _priority_sort(dead_code_hints)
            prioritized = True

        if has_capability("analyze_code", "complexity_trends", tier):
            complexity_trends = _update_and_get_complexity_trends(
                file_path=file_path,
                cyclomatic=_count_complexity(tree),
                cognitive=cognitive_complexity,
            )

        result = AnalysisResult(
            success=True,
            functions=functions,
            classes=classes,
            imports=imports,
            complexity=_count_complexity(tree),
            lines_of_code=len(code.splitlines()),
            issues=issues,
            function_details=function_details,
            class_details=class_details,
            cognitive_complexity=cognitive_complexity,
            code_smells=code_smells,
            halstead_metrics=halstead_metrics,
            duplicate_code_blocks=duplicate_code_blocks,
            dependency_graph=dependency_graph,
            naming_issues=naming_issues,
            compliance_issues=compliance_issues,
            custom_rule_violations=custom_rule_violations,
            organization_patterns=organization_patterns,
            frameworks=frameworks,
            dead_code_hints=dead_code_hints,
            decorator_summary=decorator_summary,
            type_summary=type_summary,
            architecture_patterns=architecture_patterns,
            technical_debt=technical_debt,
            api_surface=api_surface,
            prioritized=prioritized,
            complexity_trends=complexity_trends,
            # [20260110_FEATURE] v1.0 - Metadata fields
            language_detected="python",
            tier_applied=tier,
            # [20260119_FEATURE] Parsing context fields (governed by response_config.json)
            sanitization_report=sanitization_dict,
            parser_warnings=parser_warnings,
        )

        # Cache successful result
        if cache:
            cache.set(code, "analysis", result.model_dump(), cache_config)

        return result

    except ParsingError as e:
        # [20260119_FEATURE] Deterministic parsing error with context fields
        return AnalysisResult(
            success=False,
            functions=[],
            classes=[],
            imports=[],
            complexity=0,
            lines_of_code=0,
            error=str(e),
            error_location=e.location,
            suggested_fix=e.suggestion,
        )
    except Exception as e:
        return AnalysisResult(
            success=False,
            functions=[],
            classes=[],
            imports=[],
            complexity=0,
            lines_of_code=0,
            error=f"Analysis failed: {str(e)}",
        )
