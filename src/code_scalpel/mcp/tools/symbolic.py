"""Symbolic and testing MCP tool registrations."""

from __future__ import annotations

import asyncio
import inspect
import sys
import time
from importlib import import_module

import code_scalpel.licensing.features as feature_caps
from code_scalpel.mcp.helpers import symbolic_helpers as sym_helpers

# [20260213_BUGFIX] Removed jwt_validator.get_current_tier import — use protocol._get_current_tier
# which honors CODE_SCALPEL_TIER env var for downgrade-only semantics

# pragma: no cover
from code_scalpel.mcp.contract import ToolResponseEnvelope, ToolError, make_envelope
from code_scalpel.mcp.oracle_middleware import (
    with_oracle_resilience,
    GenerateTestsStrategy,
)
from code_scalpel.mcp.path_resolver import resolve_path
from code_scalpel import __version__ as _pkg_version
from code_scalpel.mcp.protocol import _get_current_tier
from code_scalpel.mcp.validators.core import ValidationError
from code_scalpel import telemetry

_ORIG_SYM_GENERATE_TESTS = sym_helpers._generate_tests_sync
_ORIG_SYM_SYMBOLIC = sym_helpers._symbolic_execute_sync

_generate_tests_sync = sym_helpers._generate_tests_sync
_symbolic_execute_sync = sym_helpers._symbolic_execute_sync

mcp = import_module("code_scalpel.mcp.protocol").mcp


@mcp.tool(
    description="Explore execution paths symbolically to find edge cases, dead code, and unreachable branches."
)
async def symbolic_execute(
    code: str,
    language: str = "python",
    max_paths: int | None = None,
    max_depth: int | None = None,
) -> ToolResponseEnvelope:
    """Perform symbolic execution on source code.

    [20260309_FEATURE] Added source-language routing so the public symbolic tool
    can expose the existing Java IR-backed engine path. Python still has the
    deepest support; Java currently uses the shared IR path plus a narrow
    fallback branch analysis when needed.

    Analyzes source code symbolically to explore execution paths, discover constraints,
    and identify potential issues without concrete execution.

    **Tier Behavior:**
     - Community: Basic symbolic execution (max_paths=100, max_depth=10)
     - Pro: All Community + advanced symbolic execution with concolic execution (max_paths=unlimited, max_depth=unlimited)
    - Enterprise: All Pro + unlimited symbolic execution with distributed execution and memory modeling

    **Tier Capabilities:**
     - Community: Basic symbolic execution (max_paths=100, max_depth=10, basic constraint types)
     - Pro: All Community + concolic execution (max_paths=unlimited, max_depth=unlimited)
    - Enterprise: All Pro + distributed execution, memory modeling (max_paths=unlimited, max_depth=unlimited)

    **Args:**
        code (str): Source code to symbolically execute.
        language (str): Source language. Supported runtime frontends: ``python``, ``javascript``, ``typescript``, ``java``.
            The TypeScript slice is bounded to IR-backed control-flow and does not model full runtime semantics.
        max_paths (int, optional): Maximum execution paths to explore (subject to tier limits).
        max_depth (int, optional): Maximum loop unrolling depth (subject to tier limits).

    **Returns:**
        ToolResponseEnvelope containing SymbolicResult with:
        - success (bool): True if analysis succeeded
        - paths_explored (int): Number of execution paths explored
        - paths (list[ExecutionPath]): Discovered paths with conditions and constraints
        - symbolic_variables (list[str]): Variables treated symbolically
        - constraints (list[str]): Discovered constraints
        - total_paths (int, optional): Total paths before limiting
        - truncated (bool): Whether paths were limited
        - truncation_warning (str, optional): Warning when limited
        - path_prioritization (dict, optional): Path prioritization (Pro/Enterprise)
        - concolic_results (dict, optional): Concolic execution (Pro/Enterprise)
        - state_space_analysis (dict, optional): State space reduction (Enterprise)
        - memory_model (dict, optional): Memory modeling (Enterprise)
        - error (str, optional): Error message if analysis failed
        - error (str): Error message if operation failed
        - tier_applied (str): Tier used for analysis
        - duration_ms (int): Analysis duration in milliseconds
    """
    started = time.perf_counter()
    try:
        # [20260311_BUGFIX] Validate shape and language at the public wrapper so
        # callers receive guided invalid_argument responses instead of internal_error.
        tier = _get_current_tier()
        supported_languages = {"python", "javascript", "typescript", "java"}

        if not code or not code.strip():
            error_obj = ToolError(
                error="'code' must be a non-empty source string.",
                error_code="invalid_argument",
                error_details={"hint": "Provide source code to symbolically execute."},
            )
            duration_ms = int((time.perf_counter() - started) * 1000)
            return make_envelope(
                data=None,
                tool_id="symbolic_execute",
                tool_version=_pkg_version,
                tier=tier,
                duration_ms=duration_ms,
                error=error_obj,
            )

        normalized_language = (language or "python").lower()
        if normalized_language == "ts":
            normalized_language = "typescript"

        if normalized_language not in supported_languages:
            error_obj = ToolError(
                error=(
                    f"Unsupported language: {language}. Must be one of "
                    f"{sorted(supported_languages)}"
                ),
                error_code="invalid_argument",
                error_details={"supported_languages": sorted(supported_languages)},
            )
            duration_ms = int((time.perf_counter() - started) * 1000)
            return make_envelope(
                data=None,
                tool_id="symbolic_execute",
                tool_version=_pkg_version,
                tier=tier,
                duration_ms=duration_ms,
                error=error_obj,
            )

        if max_paths is not None and max_paths <= 0:
            error_obj = ToolError(
                error="'max_paths' must be a positive integer when provided.",
                error_code="invalid_argument",
                error_details={"max_paths": max_paths},
            )
            duration_ms = int((time.perf_counter() - started) * 1000)
            return make_envelope(
                data=None,
                tool_id="symbolic_execute",
                tool_version=_pkg_version,
                tier=tier,
                duration_ms=duration_ms,
                error=error_obj,
            )

        if max_depth is not None and max_depth <= 0:
            error_obj = ToolError(
                error="'max_depth' must be a positive integer when provided.",
                error_code="invalid_argument",
                error_details={"max_depth": max_depth},
            )
            duration_ms = int((time.perf_counter() - started) * 1000)
            return make_envelope(
                data=None,
                tool_id="symbolic_execute",
                tool_version=_pkg_version,
                tier=tier,
                duration_ms=duration_ms,
                error=error_obj,
            )

        caps = feature_caps.get_tool_capabilities("symbolic_execute", tier)
        limits = caps.get("limits", {}) if isinstance(caps, dict) else {}

        configured_max_paths = limits.get("max_paths")
        configured_max_depth = limits.get("max_depth")
        constraint_types = limits.get("constraint_types")

        effective_max_paths: int | None
        if max_paths is None:
            effective_max_paths = (
                None if configured_max_paths is None else int(configured_max_paths)
            )
        else:
            effective_max_paths = int(max_paths)
            if configured_max_paths is not None:
                effective_max_paths = min(
                    effective_max_paths, int(configured_max_paths)
                )

        effective_max_depth: int | None
        if max_depth is None:
            effective_max_depth = (
                None if configured_max_depth is None else int(configured_max_depth)
            )
        else:
            effective_max_depth = int(max_depth)
            if configured_max_depth is not None:
                effective_max_depth = min(
                    effective_max_depth, int(configured_max_depth)
                )

        helper = sym_helpers._symbolic_execute_sync

        try:
            result = await asyncio.to_thread(
                helper,
                code,
                effective_max_paths,
                effective_max_depth,
                constraint_types,
                language,
                tier=tier,
                capabilities=caps,
            )
            duration_ms = int((time.perf_counter() - started) * 1000)

            # Emit telemetry event for symbolic_execute tool call
            telemetry.emit_tool_event(
                tool_name="symbolic_execute",
                tier_applied=tier,
                duration_ms=float(duration_ms),
                status="success",
                input_summary={
                    "language": language,
                    "code_length": len(code) if code else 0,
                    "max_paths_requested": max_paths,
                    "max_depth_requested": max_depth,
                },
                output_summary={
                    "success": result.success if result else False,
                    "paths_explored": result.paths_explored if result else 0,
                    "total_paths": result.total_paths if result else 0,
                    "truncated": result.truncated if result else False,
                    "symbolic_variables": (
                        len(result.symbolic_variables)
                        if (result and result.symbolic_variables)
                        else 0
                    ),
                    "constraints": (
                        len(result.constraints)
                        if (result and result.constraints)
                        else 0
                    ),
                },
                metadata={
                    "language": language,
                    "effective_max_paths": effective_max_paths,
                    "effective_max_depth": effective_max_depth,
                },
            )

            return make_envelope(
                data=result,
                tool_id="symbolic_execute",
                tool_version=_pkg_version,
                tier=tier,
                duration_ms=duration_ms,
            )
        except Exception as exc:
            duration_ms = int((time.perf_counter() - started) * 1000)
            # Emit failure telemetry
            try:
                telemetry.emit_tool_event(
                    tool_name="symbolic_execute",
                    tier_applied=tier,
                    duration_ms=float(duration_ms),
                    status="failure",
                    error=str(exc),
                    input_summary={
                        "language": language,
                        "code_length": len(code) if code else 0,
                        "max_paths_requested": max_paths,
                        "max_depth_requested": max_depth,
                    },
                )
            except Exception as e:
                import logging

                logging.getLogger(__name__).warning(
                    f"Telemetry emit failed for symbolic_execute: {e}"
                )
            raise
    except Exception as exc:
        duration_ms = int((time.perf_counter() - started) * 1000)
        tier = _get_current_tier()
        error_obj = ToolError(error=str(exc), error_code="internal_error")
        return make_envelope(
            data=None,
            tool_id="symbolic_execute",
            tool_version=_pkg_version,
            tier=tier,
            duration_ms=duration_ms,
            error=error_obj,
        )


@mcp.tool(
    description="Generate unit test cases derived from symbolic execution paths for a function or class."
)
@with_oracle_resilience(tool_id="generate_unit_tests", strategy=GenerateTestsStrategy)
async def generate_unit_tests(
    code: str | None = None,
    file_path: str | None = None,
    function_name: str | None = None,
    language: str = "python",
    framework: str = "pytest",
    data_driven: bool = False,
    crash_log: str | None = None,
) -> ToolResponseEnvelope:
    """Generate unit tests from code using symbolic execution.

        [20260309_FEATURE] Added source-language routing so the public test
        generation tool can reach the existing Java-aware generator path.
        Python remains the deepest path; Java currently uses the partial
        generator support already present underneath this MCP wrapper.

        **Tier Behavior:**
        - Community: Max 5 test cases, pytest framework only
        - Pro: All Community + max 20 test cases, pytest/unittest frameworks, data-driven tests
        - Enterprise: All Pro + unlimited test cases, all frameworks, data-driven tests, bug reproduction

        **Tier Capabilities:**
    - Community: Limited test generation (max_test_cases=10, test_frameworks=["pytest"])
          - Pro: All Community + data-driven tests (max_test_cases=unlimited, test_frameworks=["pytest", "unittest"])
        - Enterprise: All Pro + bug reproduction (max_test_cases=unlimited)

        Input Methods (choose one):
        - `code`: Direct source code string to analyze
        - `file_path`: Path to source file containing the code
        - `function_name`: Name of function to generate tests for (requires file_path)

        **Args:**
            code (str, optional): Source code string to generate tests for.
            file_path (str, optional): Path to source file to analyze.
            function_name (str, optional): Specific function name to target.
            language (str): Source language. Supported: ``python``, ``javascript``, ``java``, ``typescript``.
                The TypeScript path is contract-only and returns a scaffold, not symbolic test semantics.
            framework (str): Test framework. Default: "pytest".
            data_driven (bool): Generate parameterized data-driven tests (Pro+). Default: False.
            crash_log (str, optional): Crash log for bug reproduction tests (Enterprise only).

        **Returns:**
            ToolResponseEnvelope containing TestGenerationResult with:
            - success (bool): True if generation succeeded
            - function_name (str): Target function name
            - test_count (int): Number of test cases generated
            - test_cases (list[dict]): Generated test cases with code, expected results
            - total_test_cases (int): Total tests before truncation
            - framework_used (str): Test framework used
            - data_driven_enabled (bool): Whether data-driven tests were enabled
            - bug_reproduction_enabled (bool): Whether bug reproduction was enabled
            - coverage_estimate (float, 0-100): Code coverage estimate
            - warnings (list[str]): Non-fatal warnings
            - tier_applied (str): Tier used
            - error (str, optional): Error message if generation failed
            - error (str): Error message if operation failed
            - tier_applied (str): Tier used for analysis
            - duration_ms (int): Analysis duration in milliseconds
    """
    started = time.perf_counter()
    try:
        tier = _get_current_tier()
        caps = feature_caps.get_tool_capabilities("generate_unit_tests", tier)
        limits = caps.get("limits", {})
        cap_set = caps.get("capabilities", set())

        supported_languages = {"python", "javascript", "java", "typescript"}

        if code is None and file_path is None:
            return make_envelope(
                data=None,
                tool_id="generate_unit_tests",
                tool_version=_pkg_version,
                tier=tier,
                duration_ms=int((time.perf_counter() - started) * 1000),
                error=ToolError(
                    error="Either 'code' or 'file_path' must be provided.",
                    error_code="invalid_argument",
                    error_details={
                        "hint": "Provide source code directly or pass a file_path for test generation."
                    },
                ),
            )

        normalized_language = (language or "python").lower()
        if normalized_language == "ts":
            normalized_language = "typescript"
        if normalized_language not in supported_languages:
            return make_envelope(
                data=None,
                tool_id="generate_unit_tests",
                tool_version=_pkg_version,
                tier=tier,
                duration_ms=int((time.perf_counter() - started) * 1000),
                error=ToolError(
                    error=(
                        f"Unsupported language: {language}. Must be one of "
                        f"{sorted(supported_languages)}"
                    ),
                    error_code="invalid_argument",
                    error_details={"supported_languages": sorted(supported_languages)},
                ),
            )

        max_test_cases = limits.get("max_test_cases")
        allowed_frameworks = limits.get("test_frameworks")
        data_driven_supported = "data_driven_tests" in cap_set
        bug_reproduction_supported = "bug_reproduction" in cap_set

        if data_driven and not data_driven_supported:
            return make_envelope(
                data=None,
                tool_id="generate_unit_tests",
                tool_version=_pkg_version,
                tier=tier,
                duration_ms=int((time.perf_counter() - started) * 1000),
                error=ToolError(
                    error="Data-driven test generation requires Pro tier or higher.",
                    error_code="upgrade_required",
                    error_details={
                        "feature": "data_driven_tests",
                        "current_tier": tier,
                    },
                ),
            )

        if crash_log and not bug_reproduction_supported:
            return make_envelope(
                data=None,
                tool_id="generate_unit_tests",
                tool_version=_pkg_version,
                tier=tier,
                duration_ms=int((time.perf_counter() - started) * 1000),
                error=ToolError(
                    error="Bug reproduction test generation requires Enterprise tier.",
                    error_code="upgrade_required",
                    error_details={"feature": "bug_reproduction", "current_tier": tier},
                ),
            )

        if (
            isinstance(allowed_frameworks, (list, tuple, set))
            and framework not in allowed_frameworks
        ):
            return make_envelope(
                data=None,
                tool_id="generate_unit_tests",
                tool_version=_pkg_version,
                tier=tier,
                duration_ms=int((time.perf_counter() - started) * 1000),
                error=ToolError(
                    error=f"Unsupported framework: {framework}",
                    error_code="invalid_argument",
                    error_details={
                        "framework": framework,
                        "allowed_frameworks": allowed_frameworks,
                    },
                ),
            )

        # [20260311_BUGFIX] Normalize file_path before helper dispatch so malformed
        # Windows/WSL drive paths return correction-aware errors instead of generic failures.
        if file_path is not None:
            from code_scalpel.mcp.helpers.session import _get_project_root

            try:
                file_path = resolve_path(file_path, str(_get_project_root()))
            except FileNotFoundError as exc:
                duration_ms = int((time.perf_counter() - started) * 1000)
                return make_envelope(
                    data=None,
                    tool_id="generate_unit_tests",
                    tool_version=_pkg_version,
                    tier=tier,
                    duration_ms=duration_ms,
                    error=ToolError(
                        error=str(exc),
                        error_code="correction_needed",
                        error_details={"hint": str(exc)},
                    ),
                )

        helper = sym_helpers._generate_tests_sync
        if sym_helpers._generate_tests_sync is not _ORIG_SYM_GENERATE_TESTS:
            helper = sym_helpers._generate_tests_sync
        else:
            server_mod = sys.modules.get("code_scalpel.mcp.server")
            if server_mod is None:
                try:
                    server_mod = sym_helpers._get_server()
                except Exception:
                    server_mod = None

            if server_mod and hasattr(server_mod, "_generate_tests_sync"):
                candidate = getattr(server_mod, "_generate_tests_sync")
                try:
                    sig = inspect.signature(candidate)
                    if len(sig.parameters) >= 7:
                        helper = candidate
                except Exception:
                    # If signature cannot be inspected, fall back to sym_helpers
                    helper = sym_helpers._generate_tests_sync

        try:
            result = await asyncio.to_thread(
                helper,
                code,
                file_path,
                function_name,
                framework,
                max_test_cases,
                data_driven,
                crash_log,
                language,
            )
        except ValidationError as exc:
            suggestions = GenerateTestsStrategy.suggest(
                exc,
                {
                    "file_path": file_path,
                    "code": code,
                    "function_name": function_name,
                },
            )
            return make_envelope(
                data=None,
                tool_id="generate_unit_tests",
                tool_version=_pkg_version,
                tier=tier,
                duration_ms=int((time.perf_counter() - started) * 1000),
                error=ToolError(
                    error=str(exc),
                    error_code="correction_needed",
                    error_details={
                        "suggestions": suggestions,
                        "hint": str(exc),
                    },
                ),
            )

        try:
            duration_ms = int((time.perf_counter() - started) * 1000)

            # Emit telemetry event for generate_unit_tests tool call
            telemetry.emit_tool_event(
                tool_name="generate_unit_tests",
                tier_applied=tier,
                duration_ms=float(duration_ms),
                status="success",
                input_summary={
                    "language": language,
                    "framework": framework,
                    "data_driven": data_driven,
                    "has_crash_log": crash_log is not None,
                    "code_provided": code is not None,
                    "file_path": file_path,
                    "function_name": function_name,
                },
                output_summary={
                    "success": result.success if result else False,
                    "test_count": result.test_count if result else 0,
                    "total_test_cases": result.total_test_cases if result else 0,
                    "framework_used": result.framework_used if result else None,
                    "data_driven_enabled": (
                        result.data_driven_enabled if result else False
                    ),
                    "truncated": result.truncated if result else False,
                },
                metadata={
                    "language": language,
                    "framework": framework,
                },
            )

            return make_envelope(
                data=result,
                tool_id="generate_unit_tests",
                tool_version=_pkg_version,
                tier=tier,
                duration_ms=duration_ms,
            )
        except Exception as exc:
            duration_ms = int((time.perf_counter() - started) * 1000)
            # Emit failure telemetry
            try:
                telemetry.emit_tool_event(
                    tool_name="generate_unit_tests",
                    tier_applied=tier,
                    duration_ms=float(duration_ms),
                    status="failure",
                    error=str(exc),
                    input_summary={
                        "language": language,
                        "framework": framework,
                        "data_driven": data_driven,
                        "has_crash_log": crash_log is not None,
                        "code_provided": code is not None,
                        "file_path": file_path,
                        "function_name": function_name,
                    },
                )
            except Exception as e:
                import logging

                logging.getLogger(__name__).warning(
                    f"Telemetry emit failed for generate_unit_tests: {e}"
                )
            raise
    except Exception as exc:
        duration_ms = int((time.perf_counter() - started) * 1000)
        tier = _get_current_tier()
        error_obj = ToolError(error=str(exc), error_code="internal_error")
        return make_envelope(
            data=None,
            tool_id="generate_unit_tests",
            tool_version=_pkg_version,
            tier=tier,
            duration_ms=duration_ms,
            error=error_obj,
        )


@mcp.tool(
    description="Simulate a code change and verify it is safe — detects behavior changes and security issues."
)
async def simulate_refactor(
    original_code: str,
    new_code: str | None = None,
    patch: str | None = None,
    strict_mode: bool = False,
) -> ToolResponseEnvelope:
    """Simulate applying a code change and check for safety issues.

    Verifies code changes are safe before applying them by detecting security issues
    and structural changes that could break functionality.

    [20260315_DOCS] The wrapper infers language from the provided source text.
    Python remains the deepest path; JavaScript, TypeScript, and Java currently
    use bounded structural/security checks rather than full semantic parity.

    **Tier Behavior:**
      - Community: Basic refactor simulation (max 5MB file size, basic analysis depth)
      - Pro: All Community + advanced simulation with type checking (max 100MB file size, advanced analysis depth)
    - Enterprise: All Pro + deep simulation with compliance validation (max 100MB file size, deep analysis depth)

    **Tier Capabilities:**
    - Community: basic_simulation, structural_diff (max_file_size_mb=1, analysis_depth="basic")
      - Pro: All Community + advanced_simulation, behavior_preservation, type_checking (max_file_size_mb=100, analysis_depth="advanced")
    - Enterprise: All Pro + regression_prediction, impact_analysis, compliance_validation (max_file_size_mb=100, analysis_depth="deep")

    **Args:**
        original_code (str): Original code before changes.
        new_code (str, optional): Complete new code after changes (alternative to patch).
        patch (str, optional): Patch/diff describing the changes (alternative to new_code).
        strict_mode (bool): Enable strict validation checks. Default: False.

    **Returns:**
        ToolResponseEnvelope with RefactorSimulationResult containing:
        - success (bool): Whether simulation succeeded
        - is_safe (bool): Whether the refactor is safe to apply
        - status (str): Status (safe, unsafe, warning, or error)
        - reason (str, optional): Reason if not safe
        - security_issues (list[dict]): Security issues with type, severity, line, CWE
        - structural_changes (dict): Functions/classes added/removed/modified
        - warnings (list[str]): Non-critical warnings
        - impact_summary (str): Summary of potential impact
        - behavior_changes (list[dict]): Detected behavior changes (Pro+)
        - type_errors (list[dict]): Type checking errors (Pro+)
        - regression_predictions (dict): Regression likelihood (Enterprise)
        - impact_analysis (dict): Detailed impact analysis (Enterprise)
        - tier_applied (str): Tier used
        - error (str, optional): Error message if simulation failed
        - error (str): Error message if operation failed
        - tier_applied (str): Tier used for analysis
        - duration_ms (int): Analysis duration in milliseconds
    """
    started = time.perf_counter()
    try:
        # [20260311_BUGFIX] Validate refactor request shape up front so malformed
        # inputs return explicit invalid_argument results.
        tier = _get_current_tier()

        if not original_code or not original_code.strip():
            error_obj = ToolError(
                error="'original_code' must be a non-empty source string.",
                error_code="invalid_argument",
                error_details={"hint": "Provide the original code to compare against."},
            )
            duration_ms = int((time.perf_counter() - started) * 1000)
            return make_envelope(
                data=None,
                tool_id="simulate_refactor",
                tool_version=_pkg_version,
                tier=tier,
                duration_ms=duration_ms,
                error=error_obj,
            )

        if (new_code is None and patch is None) or (
            new_code is not None and patch is not None
        ):
            error_obj = ToolError(
                error="Provide exactly one of 'new_code' or 'patch'.",
                error_code="invalid_argument",
                error_details={
                    "new_code_provided": new_code is not None,
                    "patch_provided": patch is not None,
                },
            )
            duration_ms = int((time.perf_counter() - started) * 1000)
            return make_envelope(
                data=None,
                tool_id="simulate_refactor",
                tool_version=_pkg_version,
                tier=tier,
                duration_ms=duration_ms,
                error=error_obj,
            )

        caps = feature_caps.get_tool_capabilities("simulate_refactor", tier)
        limits = caps.get("limits", {})
        tool_caps = caps.get("capabilities", set())

        max_file_size_mb = limits.get("max_file_size_mb")
        analysis_depth = limits.get("analysis_depth", "basic")
        compliance_validation = "compliance_validation" in tool_caps

        try:
            result = await asyncio.to_thread(
                sym_helpers._simulate_refactor_sync,
                original_code,
                new_code,
                patch,
                strict_mode,
                max_file_size_mb=max_file_size_mb,
                analysis_depth=analysis_depth,
                compliance_validation=compliance_validation,
            )
            duration_ms = int((time.perf_counter() - started) * 1000)

            # Emit telemetry event for simulate_refactor tool call
            telemetry.emit_tool_event(
                tool_name="simulate_refactor",
                tier_applied=tier,
                duration_ms=float(duration_ms),
                status="success",
                input_summary={
                    "original_code_length": len(original_code) if original_code else 0,
                    "new_code_provided": new_code is not None,
                    "new_code_length": len(new_code) if new_code else 0,
                    "patch_provided": patch is not None,
                    "patch_length": len(patch) if patch else 0,
                    "strict_mode": strict_mode,
                },
                output_summary={
                    "success": result.success if result else False,
                    "is_safe": result.is_safe if result else False,
                    "status": result.status if result else None,
                    "security_issues": (
                        len(result.security_issues)
                        if (result and result.security_issues)
                        else 0
                    ),
                    "structural_changes": (
                        bool(result.structural_changes) if result else False
                    ),
                },
                metadata={
                    "analysis_depth": analysis_depth,
                },
            )

            return make_envelope(
                data=result,
                tool_id="simulate_refactor",
                tool_version=_pkg_version,
                tier=tier,
                duration_ms=duration_ms,
            )
        except Exception as exc:
            duration_ms = int((time.perf_counter() - started) * 1000)
            # Emit failure telemetry
            try:
                telemetry.emit_tool_event(
                    tool_name="simulate_refactor",
                    tier_applied=tier,
                    duration_ms=float(duration_ms),
                    status="failure",
                    error=str(exc),
                    input_summary={
                        "original_code_length": (
                            len(original_code) if original_code else 0
                        ),
                        "new_code_provided": new_code is not None,
                        "new_code_length": len(new_code) if new_code else 0,
                        "patch_provided": patch is not None,
                        "patch_length": len(patch) if patch else 0,
                        "strict_mode": strict_mode,
                    },
                )
            except Exception as e:
                import logging

                logging.getLogger(__name__).warning(
                    f"Telemetry emit failed for simulate_refactor: {e}"
                )
            raise
    except Exception as exc:
        duration_ms = int((time.perf_counter() - started) * 1000)
        tier = _get_current_tier()
        error_obj = ToolError(error=str(exc), error_code="internal_error")
        return make_envelope(
            data=None,
            tool_id="simulate_refactor",
            tool_version=_pkg_version,
            tier=tier,
            duration_ms=duration_ms,
            error=error_obj,
        )


__all__ = ["symbolic_execute", "generate_unit_tests", "simulate_refactor"]
