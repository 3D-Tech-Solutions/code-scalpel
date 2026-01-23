"""Helper implementations for symbolic execution and test generation tools."""

from __future__ import annotations

import ast
import logging
from pathlib import Path
from typing import Any

from code_scalpel.licensing import tier_detector
from code_scalpel.licensing.features import get_tool_capabilities
from code_scalpel.mcp.helpers.analyze_helpers import _get_cache, _validate_code
from code_scalpel.mcp.models.core import (
    ExecutionPath,
    GeneratedTestCase,
    GenerationResult,
    RefactorSecurityIssue,
    RefactorSimulationResult,
    SymbolicResult,
)
from code_scalpel.parsing import ParsingError, parse_python_code

logger = logging.getLogger(__name__)


def _get_server():
    from code_scalpel.mcp import server as _server

    return _server


__all__ = [
    "_detect_requested_constraint_types",
    "_basic_symbolic_analysis",
    "_build_path_prioritization",
    "_build_concolic_results",
    "_build_state_space_analysis",
    "_build_memory_model",
    "_symbolic_execute_sync",
    "_add_tier_features_to_result",
    "_generate_tests_sync",
    "_simulate_refactor_sync",
]


def _detect_requested_constraint_types(code: str) -> set[str]:
    """Best-effort extraction of constraint types implied by code.

    [20251226_FEATURE] Enforce configurable constraint type limits in symbolic_execute.
    [20260119_FEATURE] Uses unified parser for deterministic behavior.
    """

    requested: set[str] = set()
    try:
        tree, _ = parse_python_code(code)
    except ParsingError:
        return requested

    def _norm_type_name(name: str) -> str | None:
        n = name.lower()
        if n in {"int", "integer"}:
            return "int"
        if n in {"bool", "boolean"}:
            return "bool"
        if n in {"str", "string"}:
            return "string"
        if n in {"float", "double", "real"}:
            return "float"
        return None

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for arg in node.args.args:
                ann = arg.annotation
                if isinstance(ann, ast.Name):
                    t = _norm_type_name(ann.id)
                    if t:
                        requested.add(t)
                elif isinstance(ann, ast.Attribute):
                    t = _norm_type_name(ann.attr)
                    if t:
                        requested.add(t)

        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id == "symbolic" and len(node.args) >= 2:
                type_arg = node.args[1]
                if isinstance(type_arg, ast.Name):
                    t = _norm_type_name(type_arg.id)
                    if t:
                        requested.add(t)
                elif isinstance(type_arg, ast.Constant) and isinstance(type_arg.value, str):
                    t = _norm_type_name(type_arg.value)
                    if t:
                        requested.add(t)

    return requested


def _basic_symbolic_analysis(code: str, max_paths: int) -> SymbolicResult:
    """Fallback symbolic analysis using AST inspection.

    [20260119_FEATURE] Uses unified parser for deterministic behavior.
    """
    try:
        tree, _ = parse_python_code(code)

        branch_count = 0
        symbolic_vars: list[str] = []
        conditions: list[str] = []

        for node in ast.walk(tree):
            if isinstance(node, ast.If):
                branch_count += 1
                conditions.append(ast.unparse(node.test))
            elif isinstance(node, ast.While):
                branch_count += 1
                conditions.append(f"while: {ast.unparse(node.test)}")
            elif isinstance(node, ast.For):
                branch_count += 1
                if isinstance(node.target, ast.Name):
                    symbolic_vars.append(node.target.id)
            elif isinstance(node, ast.FunctionDef):
                for arg in node.args.args:
                    symbolic_vars.append(arg.arg)

        estimated_paths = min(2 ** min(branch_count, 20), max_paths)
        paths = [
            ExecutionPath(
                path_id=i,
                conditions=conditions[: i + 1] if i < len(conditions) else conditions,
                final_state={},
                reproduction_input=None,
                is_reachable=True,
            )
            for i in range(estimated_paths)
        ]

        return SymbolicResult(
            success=True,
            paths_explored=estimated_paths,
            total_paths=estimated_paths,
            paths=paths,
            symbolic_variables=list(set(symbolic_vars)),
            constraints=conditions,
        )

    except ParsingError as e:
        return SymbolicResult(
            success=False,
            paths_explored=0,
            error=f"Basic analysis failed: {str(e)}",
        )
    except Exception as e:
        return SymbolicResult(
            success=False,
            paths_explored=0,
            error=f"Basic analysis failed: {str(e)}",
        )


# [20251230_FEATURE] v1.0 roadmap Pro/Enterprise tier helper functions
def _build_path_prioritization(paths: list[ExecutionPath], code: str, smart: bool = False) -> dict[str, Any]:
    """Build path prioritization metadata for Pro/Enterprise tier.

    Smart prioritization (Pro) uses heuristics to rank paths by:
    - Constraint complexity
    - Branch depth
    - Error-prone patterns
    """
    if not paths:
        return {"total_paths": 0, "prioritized_paths": []}

    prioritized = []
    for path in paths:
        # Calculate priority score based on conditions
        complexity = len(path.conditions)
        has_error_patterns = any(
            keyword in str(path.conditions) for keyword in ["None", "null", "0", "empty", "negative"]
        )

        priority_score = complexity * 10
        if has_error_patterns:
            priority_score += 25  # Boost paths with error-prone conditions

        prioritized.append(
            {
                "path_id": path.path_id,
                "priority_score": priority_score,
                "complexity": complexity,
                "has_error_patterns": has_error_patterns,
                "is_reachable": path.is_reachable,
            }
        )

    # Sort by priority score descending
    prioritized.sort(key=lambda x: x["priority_score"], reverse=True)

    return {
        "algorithm": "smart_heuristic" if smart else "complexity_based",
        "total_paths": len(paths),
        "prioritized_paths": prioritized[:10],  # Top 10 for output size
        "highest_priority_path": prioritized[0]["path_id"] if prioritized else None,
    }


def _build_concolic_results(paths: list[ExecutionPath], code: str) -> dict[str, Any]:
    """Build concolic execution results for Pro/Enterprise tier.

    Concolic = concrete + symbolic execution combined.
    Identifies paths that benefit from concrete value injection.
    """
    if not paths:
        return {"mode": "concolic", "concrete_hints": []}

    concrete_hints = []
    for path in paths:
        if path.reproduction_input:
            for var, value in path.reproduction_input.items():
                concrete_hints.append(
                    {
                        "path_id": path.path_id,
                        "variable": var,
                        "concrete_value": value,
                        "type": type(value).__name__,
                    }
                )

    return {
        "mode": "concolic",
        "paths_with_concrete_values": sum(1 for p in paths if p.reproduction_input),
        "total_concrete_hints": len(concrete_hints),
        "concrete_hints": concrete_hints[:20],  # Limit output size
    }


def _build_state_space_analysis(paths: list[ExecutionPath], constraints: list[str]) -> dict[str, Any]:
    """Build state space reduction analysis for Enterprise tier.

    Analyzes the symbolic state space for reduction opportunities.
    """
    # Analyze constraint patterns for reduction opportunities
    unique_vars = set()
    constraint_types = {"equality": 0, "inequality": 0, "boolean": 0, "other": 0}

    for constraint in constraints:
        constraint_lower = constraint.lower()
        if "==" in constraint or "is" in constraint_lower:
            constraint_types["equality"] += 1
        elif any(op in constraint for op in ["<", ">", "<=", ">="]):
            constraint_types["inequality"] += 1
        elif any(kw in constraint_lower for kw in ["and", "or", "not", "true", "false"]):
            constraint_types["boolean"] += 1
        else:
            constraint_types["other"] += 1

        # Extract variable-like tokens
        import re

        vars_found = re.findall(r"\b[a-zA-Z_][a-zA-Z0-9_]*\b", constraint)
        unique_vars.update(v for v in vars_found if not v.isupper() and len(v) > 1)

    # Estimate state space size
    estimated_space = 2 ** min(len(unique_vars), 30)  # Cap at 2^30

    return {
        "unique_variables": len(unique_vars),
        "constraint_breakdown": constraint_types,
        "total_constraints": len(constraints),
        "estimated_state_space": estimated_space,
        "reduction_opportunities": [
            "Constraint merging" if constraint_types["equality"] > 3 else None,
            "Boolean simplification" if constraint_types["boolean"] > 2 else None,
            "Variable pruning" if len(unique_vars) > 10 else None,
        ],
        "reduction_potential": "high" if len(constraints) > 10 else "low",
    }


def _build_memory_model(code: str) -> dict[str, Any]:
    """Build memory modeling results for Enterprise tier.

    Analyzes pointer/reference patterns and aliasing in code.

    [20260119_FEATURE] Uses unified parser for deterministic behavior.
    """
    try:
        tree, _ = parse_python_code(code)
    except ParsingError:
        return {"analysis": "unavailable", "reason": "syntax_error"}

    heap_allocations = []
    pointer_operations = []
    aliases = []

    for node in ast.walk(tree):
        # Detect list/dict creation (heap allocation)
        if isinstance(node, (ast.List, ast.Dict, ast.Set)):
            heap_allocations.append(
                {
                    "type": type(node).__name__,
                    "line": getattr(node, "lineno", 0),
                }
            )
        # Detect assignments that create aliases
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and isinstance(node.value, ast.Name):
                    aliases.append(
                        {
                            "target": target.id,
                            "source": node.value.id,
                            "line": node.lineno,
                        }
                    )
                elif isinstance(target, ast.Subscript):
                    pointer_operations.append(
                        {
                            "type": "subscript_write",
                            "line": node.lineno,
                        }
                    )

    return {
        "heap_allocations": len(heap_allocations),
        "pointer_operations": len(pointer_operations),
        "potential_aliases": len(aliases),
        "aliases": aliases[:10],  # Limit output
        "memory_safety_risk": "medium" if aliases else "low",
        "analysis_depth": "basic",
    }


def _symbolic_execute_sync(
    code: str,
    max_paths: int | None = None,
    max_depth: int | None = None,
    constraint_types: Any = None,
    tier: str | None = None,
    capabilities: dict | None = None,
) -> SymbolicResult:
    """Synchronous implementation of symbolic_execute.

    [20251226_FEATURE] Enforce tier/tool limits via limits.toml (max_paths/max_depth/constraint_types).
    [20251230_FEATURE] v1.0 roadmap alignment - tier-aware Pro/Enterprise features.
    """
    tier = tier or tier_detector.get_current_tier()
    caps = capabilities or get_tool_capabilities("symbolic_execute", tier)
    caps_set = set(caps.get("capabilities", set()) or [])
    limits = caps.get("limits", {}) or {}

    # Apply tier limits if not explicitly provided
    if max_paths is None:
        max_paths = limits.get("max_paths")
    if max_depth is None:
        max_depth = limits.get("max_depth")
    if constraint_types is None:
        constraint_types = limits.get("constraint_types")

    valid, error = _validate_code(code)
    if not valid:
        return SymbolicResult(success=False, paths_explored=0, error=error)

    if max_paths is not None and max_paths < 1:
        return SymbolicResult(success=False, paths_explored=0, error="max_paths must be >= 1")

    if max_depth is not None and max_depth < 1:
        return SymbolicResult(success=False, paths_explored=0, error="max_depth must be >= 1")

    fallback_max_paths = 10 if max_paths is None else int(max_paths)
    effective_max_depth = 10 if max_depth is None else int(max_depth)

    if constraint_types not in (None, "all"):
        try:
            allowed_types = {str(t).lower() for t in constraint_types}
        except Exception:
            allowed_types = set()

        if allowed_types:
            requested_types = _detect_requested_constraint_types(code)
            disallowed = {t for t in requested_types if t not in allowed_types}
            if disallowed:
                basic_result = _basic_symbolic_analysis(code, max_paths=fallback_max_paths)
                basic_result.error = (
                    f"[LIMIT] Symbolic constraint types not enabled ({sorted(disallowed)}); " "using AST-only analysis"
                )
                return basic_result

    cache = _get_cache()
    cache_config = {
        "max_paths": max_paths,
        "max_depth": max_depth,
        "constraint_types": constraint_types,
        "model_schema": "friendly_names_v20251214",
    }

    if cache:
        cached = cache.get(code, "symbolic", cache_config)
        if cached is not None:
            logger.debug("Cache hit for symbolic_execute")
            # [20251227_BUGFIX] v3.1.1 - Handle both dict (JSON cache) and object (pickle cache)
            if isinstance(cached, SymbolicResult):
                return cached
            if isinstance(cached, dict):
                if "paths" in cached:
                    # Handle mixed case: dict with ExecutionPath objects OR plain dicts
                    paths_list = cached["paths"]
                    if paths_list and isinstance(paths_list[0], dict):
                        cached["paths"] = [ExecutionPath(**p) for p in paths_list]
                    # else: already ExecutionPath objects, leave as-is
                return SymbolicResult(**cached)
            return cached

    try:
        from code_scalpel.symbolic_execution_tools import SymbolicAnalyzer
        from code_scalpel.symbolic_execution_tools.engine import PathStatus

        analyzer = SymbolicAnalyzer(max_loop_iterations=effective_max_depth)
        result = analyzer.analyze(code)

        paths: list[ExecutionPath] = []
        all_constraints: list[str] = []

        for path in result.paths:
            conditions = [str(c) for c in path.constraints] if path.constraints else []
            all_constraints.extend(conditions)
            paths.append(
                ExecutionPath(
                    path_id=path.path_id,
                    conditions=conditions,
                    final_state=path.variables or {},
                    reproduction_input=path.model or {},
                    is_reachable=path.status == PathStatus.FEASIBLE,
                )
            )

        total_paths = len(paths)
        truncated = False
        truncation_warning: str | None = None
        if max_paths is not None and total_paths > max_paths:
            truncated = True
            truncation_warning = f"Result limited to {max_paths} paths by current configuration."
            paths = paths[:max_paths]

        symbolic_vars = list(result.all_variables.keys()) if result.all_variables else []
        constraints_list = list(set(all_constraints))

        if not symbolic_vars or not constraints_list:
            basic = _basic_symbolic_analysis(code, max_paths=fallback_max_paths)
            if not symbolic_vars and basic.symbolic_variables:
                symbolic_vars = basic.symbolic_variables
            if not constraints_list and basic.constraints:
                constraints_list = basic.constraints
            if not paths and basic.paths:
                paths = basic.paths
                total_paths = basic.total_paths if basic.total_paths is not None else total_paths

        # [20251230_FEATURE] v1.0 roadmap Pro/Enterprise tier features
        path_prioritization: dict[str, Any] | None = None
        concolic_results: dict[str, Any] | None = None
        state_space_analysis: dict[str, Any] | None = None
        memory_model: dict[str, Any] | None = None

        if "smart_path_prioritization" in caps_set:
            path_prioritization = _build_path_prioritization(paths, code, smart=True)

        if "concolic_execution" in caps_set:
            concolic_results = _build_concolic_results(paths, code)

        if "state_space_reduction" in caps_set:
            state_space_analysis = _build_state_space_analysis(paths, constraints_list)

        if "memory_modeling" in caps_set:
            memory_model = _build_memory_model(code)

        symbolic_result = SymbolicResult(
            success=True,
            paths_explored=len(paths),
            total_paths=total_paths,
            truncated=truncated,
            truncation_warning=truncation_warning,
            paths=paths,
            symbolic_variables=symbolic_vars,
            constraints=constraints_list,
            path_prioritization=path_prioritization,
            concolic_results=concolic_results,
            state_space_analysis=state_space_analysis,
            memory_model=memory_model,
        )

        if cache:
            cache.set(code, "symbolic", symbolic_result.model_dump(), cache_config)

        return symbolic_result

    except ImportError as e:
        logger.warning(f"Symbolic execution not available (ImportError: {e}), using basic analysis")
        basic_result = _basic_symbolic_analysis(code, max_paths=fallback_max_paths)
        basic_result.error = f"[FALLBACK] Symbolic engine not available, using AST analysis: {e}"
        # Add tier-aware features even in fallback
        basic_result = _add_tier_features_to_result(basic_result, code, caps_set)
        return basic_result
    except Exception as e:
        logger.warning(f"Symbolic execution failed, using basic analysis: {e}")
        basic_result = _basic_symbolic_analysis(code, max_paths=fallback_max_paths)
        basic_result.error = f"[FALLBACK] Symbolic execution failed ({type(e).__name__}: {e}), using AST analysis"
        # Add tier-aware features even in fallback
        basic_result = _add_tier_features_to_result(basic_result, code, caps_set)
        return basic_result


def _add_tier_features_to_result(result: SymbolicResult, code: str, caps_set: set) -> SymbolicResult:
    """Add tier-aware features to a SymbolicResult (including fallback results)."""
    if "smart_path_prioritization" in caps_set:
        result.path_prioritization = _build_path_prioritization(result.paths, code, smart=True)

    if "concolic_execution" in caps_set:
        result.concolic_results = _build_concolic_results(result.paths, code)

    if "state_space_reduction" in caps_set:
        result.state_space_analysis = _build_state_space_analysis(result.paths, result.constraints)

    if "memory_modeling" in caps_set:
        result.memory_model = _build_memory_model(code)

    return result


# ==========================================================================
# TEST GENERATION
# ==========================================================================


def _generate_tests_sync(
    code: str | None = None,
    file_path: str | None = None,
    function_name: str | None = None,
    framework: str = "pytest",
    max_test_cases: int | None = None,
    data_driven: bool = False,
    crash_log: str | None = None,
) -> GenerationResult:
    """Synchronous implementation of generate_unit_tests.

    [20251220_FIX] v3.0.5 - Added file_path parameter for consistency with other tools.
    [20251229_FEATURE] v3.3.0 - Added data_driven parameter for Pro tier parametrized tests.
    [20251229_FEATURE] v3.3.0 - Added crash_log parameter for Enterprise tier bug reproduction.
    """
    # Read from file if file_path provided
    if file_path and not code:
        try:
            resolved = Path(file_path)
            if not resolved.is_absolute():
                resolved = _get_server().PROJECT_ROOT / file_path
            if not resolved.exists():
                return GenerationResult(
                    success=False,
                    function_name=function_name or "unknown",
                    test_count=0,
                    total_test_cases=0,
                    error=f"File not found: {file_path}.",
                )
            code = resolved.read_text(encoding="utf-8")
        except Exception as e:
            return GenerationResult(
                success=False,
                function_name=function_name or "unknown",
                test_count=0,
                total_test_cases=0,
                error=f"Failed to read file: {str(e)}.",
            )

    if not code:
        return GenerationResult(
            success=False,
            function_name=function_name or "unknown",
            test_count=0,
            total_test_cases=0,
            error="Either 'code' or 'file_path' must be provided.",
        )

    valid, error = _validate_code(code)
    if not valid:
        return GenerationResult(
            success=False,
            function_name=function_name or "unknown",
            test_count=0,
            total_test_cases=0,
            error=error,
        )

    try:
        from code_scalpel.generators import TestGenerator

        generator = TestGenerator(framework=framework)

        # [20251229_FEATURE] v3.3.0 - Enterprise: Bug reproduction from crash log
        if crash_log:
            result = generator.generate_bug_reproduction_test(
                code=code,
                crash_log=crash_log,
                function_name=function_name,
            )
        else:
            result = generator.generate(code, function_name=function_name)

        total_cases = len(result.test_cases)
        truncated = False
        truncation_warning: str | None = None
        if max_test_cases is not None and max_test_cases >= 0 and total_cases > max_test_cases:
            truncated = True
            truncation_warning = (
                f"Generated {total_cases} test cases; returned {max_test_cases} due to configured limits."
            )
            result.test_cases = result.test_cases[:max_test_cases]

        # [20251230_FIX][unit-tests] Ensure GeneratedTestCase is JSON-serializable.
        # Symbolic execution engines may return solver-specific objects (e.g., Z3 ASTs)
        # that crash MCP transport serialization if returned directly.
        def _json_safe(value: Any) -> Any:
            if value is None or isinstance(value, (str, int, float, bool)):
                return value
            if isinstance(value, (list, tuple)):
                return [_json_safe(v) for v in value]
            if isinstance(value, dict):
                return {str(k): _json_safe(v) for k, v in value.items()}

            # Best-effort Z3 coercion
            as_long = getattr(value, "as_long", None)
            if callable(as_long):
                try:
                    as_long_result = as_long()
                    if isinstance(as_long_result, (int, float, str)):
                        return int(as_long_result)
                except Exception:
                    pass
            as_decimal = getattr(value, "as_decimal", None)
            if callable(as_decimal):
                try:
                    dec = str(as_decimal(20))
                    # Z3 sometimes uses trailing '?' for repeating decimals.
                    return dec.replace("?", "")
                except Exception:
                    pass

            # Fallback: string representation
            try:
                return str(value)
            except Exception:
                return repr(value)

        test_cases = [
            GeneratedTestCase(
                path_id=tc.path_id,
                function_name=tc.function_name,
                inputs=_json_safe(getattr(tc, "inputs", {}) or {}),
                description=tc.description,
                path_conditions=[str(c) for c in (getattr(tc, "path_conditions", []) or [])],
            )
            for tc in result.test_cases
        ]

        # [20251229_FEATURE] v3.3.0 - Pro tier: Data-driven test generation
        # Generate parametrized/data-driven tests if requested
        if data_driven:
            if framework == "pytest":
                pytest_code = result.generate_parametrized_tests()
            else:
                pytest_code = result.pytest_code

            if framework == "unittest":
                unittest_code = result.generate_unittest_subtests()
            else:
                unittest_code = result.unittest_code
        else:
            pytest_code = result.pytest_code
            unittest_code = result.unittest_code

        return GenerationResult(
            success=True,
            function_name=result.function_name,
            test_count=len(test_cases),
            test_cases=test_cases,
            total_test_cases=total_cases,
            truncated=truncated,
            truncation_warning=truncation_warning,
            pytest_code=pytest_code,
            unittest_code=unittest_code,
        )

    except Exception as e:
        return GenerationResult(
            success=False,
            function_name=function_name or "unknown",
            test_count=0,
            total_test_cases=0,
            error=f"Test generation failed: {str(e)}",
        )


# ==========================================================================
# REFACTOR SIMULATION
# ==========================================================================


def _simulate_refactor_sync(
    original_code: str,
    new_code: str | None = None,
    patch: str | None = None,
    strict_mode: bool = False,
    *,
    max_file_size_mb: int | None = None,
    analysis_depth: str = "basic",
    compliance_validation: bool = False,
) -> RefactorSimulationResult:
    """Synchronous implementation of simulate_refactor."""
    # [20251225_FEATURE] Tier-aware input size limits (neutral messaging).
    if max_file_size_mb is not None and max_file_size_mb >= 0:
        max_bytes = int(max_file_size_mb * 1024 * 1024)
        for label, text in (
            ("original_code", original_code),
            ("new_code", new_code or ""),
            ("patch", patch or ""),
        ):
            if len(text.encode("utf-8")) > max_bytes:
                return RefactorSimulationResult(
                    success=False,
                    is_safe=False,
                    status="error",
                    error=(f"Input '{label}' exceeds configured size limit of {max_file_size_mb} MB."),
                )

    valid, error = _validate_code(original_code)
    if not valid:
        return RefactorSimulationResult(
            success=False,
            is_safe=False,
            status="error",
            error=f"Invalid original code: {error}.",
        )

    if new_code is None and patch is None:
        return RefactorSimulationResult(
            success=False,
            is_safe=False,
            status="error",
            error="Must provide either 'new_code' or 'patch'.",
        )

    try:
        from code_scalpel.generators import RefactorSimulator

        # [20251230_FEATURE] Get tier capabilities
        tier = tier_detector.get_current_tier()
        caps = get_tool_capabilities("simulate_refactor", tier) or {}
        cap_set = set(caps.get("capabilities", set()) or [])

        # Enable Pro tier type checking
        enable_type_checking = "type_checking" in cap_set or "build_check" in cap_set

        # Enable Enterprise tier regression prediction
        enable_regression = "regression_prediction" in cap_set

        simulator = RefactorSimulator(strict_mode=strict_mode)
        result = simulator.simulate(
            original_code=original_code,
            new_code=new_code,
            patch=patch,
            enable_type_checking=enable_type_checking,
            enable_regression_prediction=enable_regression,
            project_root=str(_get_server().PROJECT_ROOT),
        )

        security_issues = [
            RefactorSecurityIssue(
                type=issue.type,
                severity=issue.severity,
                line=issue.line,
                description=issue.description,
                cwe=issue.cwe,
            )
            for issue in result.security_issues
        ]

        structural_changes = dict(result.structural_changes or {})

        # [20251225_FEATURE] Pro/Enterprise: deeper structural diff (Python only).
        # [20260119_FEATURE] Uses unified parser for deterministic behavior.
        if analysis_depth in {"advanced", "deep"}:
            try:
                import ast

                def _collect_python_functions(code_text: str) -> dict[str, str]:
                    tree, _ = parse_python_code(code_text)
                    functions: dict[str, str] = {}

                    class StackFrame:
                        __slots__ = ("class_name",)

                        def __init__(self, class_name: str | None):
                            self.class_name = class_name

                    stack: list[StackFrame] = [StackFrame(None)]

                    def visit(node: ast.AST) -> None:
                        if isinstance(node, ast.ClassDef):
                            stack.append(StackFrame(node.name))
                            for child in node.body:
                                visit(child)
                            stack.pop()
                            return
                        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            cls = stack[-1].class_name
                            name = f"{cls}.{node.name}" if cls else node.name
                            functions[name] = ast.dump(node, include_attributes=False)
                            return
                        for child in ast.iter_child_nodes(node):
                            visit(child)

                    visit(tree)
                    return functions

                # Prefer the patched code from simulator when available.
                patched_code = getattr(result, "patched_code", None)
                new_text = patched_code or new_code
                if isinstance(new_text, str):
                    old_funcs = _collect_python_functions(original_code)
                    new_funcs = _collect_python_functions(new_text)
                    modified = sorted(
                        name for name in (set(old_funcs) & set(new_funcs)) if old_funcs[name] != new_funcs[name]
                    )
                    if modified:
                        structural_changes["functions_modified"] = modified
            except Exception:
                # Best-effort enrichment only.
                pass

        # [20251225_FEATURE] Enterprise: optional compliance validation warnings.
        if compliance_validation:
            removed_funcs = structural_changes.get("functions_removed") or []
            removed_classes = structural_changes.get("classes_removed") or []
            if removed_funcs or removed_classes:
                result.warnings.append("Compliance validation: detected removed functions/classes.")

        return RefactorSimulationResult(
            success=True,
            is_safe=result.is_safe,
            status=result.status.value,
            reason=result.reason,
            security_issues=security_issues,
            structural_changes=structural_changes,
            warnings=result.warnings,
        )

    except Exception as e:
        return RefactorSimulationResult(
            success=False,
            is_safe=False,
            status="error",
            error=f"Simulation failed: {str(e)}",
        )
