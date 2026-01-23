"""Symbolic and testing MCP tool registrations.

[20260121_REFACTOR] Wrap outputs in ToolResponseEnvelope for MCP contract.
"""

from __future__ import annotations

import asyncio
import inspect
import sys
import time
from importlib import import_module

import code_scalpel.licensing.features as feature_caps
from code_scalpel import __version__ as _pkg_version
from code_scalpel.licensing import tier_detector

# [20260121_BUGFIX] Move contract imports before variable assignments to satisfy E402
from code_scalpel.mcp.contract import ToolError, ToolResponseEnvelope, make_envelope
from code_scalpel.mcp.helpers import symbolic_helpers as sym_helpers
from code_scalpel.mcp.models.core import GenerationResult
from code_scalpel.mcp.protocol import _get_current_tier

_ORIG_SYM_GENERATE_TESTS = sym_helpers._generate_tests_sync
_ORIG_SYM_SYMBOLIC = sym_helpers._symbolic_execute_sync

# [20260121_TEST] Expose helper aliases for test monkeypatching
_generate_tests_sync = sym_helpers._generate_tests_sync
_symbolic_execute_sync = sym_helpers._symbolic_execute_sync

mcp = import_module("code_scalpel.mcp.protocol").mcp


@mcp.tool()
async def symbolic_execute(
    code: str,
    max_paths: int | None = None,
    max_depth: int | None = None,
) -> ToolResponseEnvelope:
    """Perform symbolic execution on Python code.

    [20251226_FEATURE] Tier-aware limits are loaded from limits.toml via get_tool_capabilities.
    """
    started = time.perf_counter()
    try:
        tier = tier_detector.get_current_tier()
        caps = feature_caps.get_tool_capabilities("symbolic_execute", tier)
        limits = caps.get("limits", {}) if isinstance(caps, dict) else {}

        configured_max_paths = limits.get("max_paths")
        configured_max_depth = limits.get("max_depth")
        constraint_types = limits.get("constraint_types")

        effective_max_paths: int | None
        if max_paths is None:
            effective_max_paths = None if configured_max_paths is None else int(configured_max_paths)
        else:
            effective_max_paths = int(max_paths)
            if configured_max_paths is not None:
                effective_max_paths = min(effective_max_paths, int(configured_max_paths))

        effective_max_depth: int | None
        if max_depth is None:
            effective_max_depth = None if configured_max_depth is None else int(configured_max_depth)
        else:
            effective_max_depth = int(max_depth)
            if configured_max_depth is not None:
                effective_max_depth = min(effective_max_depth, int(configured_max_depth))

        # [20260121_BUGFIX] Resolve helper at runtime; prefer sym_helpers to honor monkeypatches
        helper = sym_helpers._symbolic_execute_sync

        result = await asyncio.to_thread(
            helper,
            code,
            effective_max_paths,
            effective_max_depth,
            constraint_types,
            tier=tier,
            capabilities=caps,
        )
        duration_ms = int((time.perf_counter() - started) * 1000)
        return make_envelope(
            data=result,
            tool_id="symbolic_execute",
            tool_version=_pkg_version,
            tier=tier,
            duration_ms=duration_ms,
        )
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


@mcp.tool()
async def generate_unit_tests(
    code: str | None = None,
    file_path: str | None = None,
    function_name: str | None = None,
    framework: str = "pytest",
    data_driven: bool = False,
    crash_log: str | None = None,
) -> ToolResponseEnvelope:
    """Generate unit tests from code using symbolic execution."""
    started = time.perf_counter()
    try:
        # [20260120_BUGFIX] Consistent tier detection pattern
        tier = tier_detector.get_current_tier()
        caps = feature_caps.get_tool_capabilities("generate_unit_tests", tier)
        limits = caps.get("limits", {})
        cap_set = caps.get("capabilities", set())

        max_test_cases = limits.get("max_test_cases")
        allowed_frameworks = limits.get("test_frameworks")
        # [20251231_BUGFIX] Fixed capabilities check - it's a set, not dict
        data_driven_supported = "data_driven_tests" in cap_set
        bug_reproduction_supported = "bug_reproduction" in cap_set

        # [20251229_FEATURE] v3.3.0 - Pro tier enforcement for data-driven tests
        if data_driven and not data_driven_supported:
            result = GenerationResult(
                success=False,
                function_name=function_name or "unknown",
                test_count=0,
                total_test_cases=0,
                error="Data-driven test generation requires Pro tier or higher.",
                tier_applied=tier,
                framework_used=framework,
                max_test_cases_limit=max_test_cases,
                data_driven_enabled=False,
                bug_reproduction_enabled=False,
            )
            duration_ms = int((time.perf_counter() - started) * 1000)
            return make_envelope(
                data=result,
                tool_id="generate_unit_tests",
                tool_version=_pkg_version,
                tier=tier,
                duration_ms=duration_ms,
            )

        # [20251229_FEATURE] v3.3.0 - Enterprise tier enforcement for bug reproduction
        if crash_log and not bug_reproduction_supported:
            result = GenerationResult(
                success=False,
                function_name=function_name or "unknown",
                test_count=0,
                total_test_cases=0,
                error="Bug reproduction test generation requires Enterprise tier.",
                tier_applied=tier,
                framework_used=framework,
                max_test_cases_limit=max_test_cases,
                data_driven_enabled=data_driven,
                bug_reproduction_enabled=False,
            )
            duration_ms = int((time.perf_counter() - started) * 1000)
            return make_envelope(
                data=result,
                tool_id="generate_unit_tests",
                tool_version=_pkg_version,
                tier=tier,
                duration_ms=duration_ms,
            )

        if isinstance(allowed_frameworks, list) and framework not in allowed_frameworks:
            result = GenerationResult(
                success=False,
                function_name=function_name or "unknown",
                test_count=0,
                total_test_cases=0,
                error=f"Unsupported framework: {framework}",
                tier_applied=tier,
                framework_used=framework,
                max_test_cases_limit=max_test_cases,
                data_driven_enabled=data_driven,
                bug_reproduction_enabled=crash_log is not None,
            )
            duration_ms = int((time.perf_counter() - started) * 1000)
            return make_envelope(
                data=result,
                tool_id="generate_unit_tests",
                tool_version=_pkg_version,
                tier=tier,
                duration_ms=duration_ms,
            )

        # [20260121_BUGFIX] Resolve helper at runtime so tests can monkeypatch either
        # sym_helpers._generate_tests_sync or server._generate_tests_sync.
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
                candidate = server_mod._generate_tests_sync
                try:
                    sig = inspect.signature(candidate)
                    if len(sig.parameters) >= 7:
                        helper = candidate
                except Exception:
                    # If signature cannot be inspected, fall back to sym_helpers
                    helper = sym_helpers._generate_tests_sync

        result = await asyncio.to_thread(
            helper,
            code,
            file_path,
            function_name,
            framework,
            max_test_cases,
            data_driven,
            crash_log,
        )
        duration_ms = int((time.perf_counter() - started) * 1000)
        return make_envelope(
            data=result,
            tool_id="generate_unit_tests",
            tool_version=_pkg_version,
            tier=tier,
            duration_ms=duration_ms,
        )
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


@mcp.tool()
async def simulate_refactor(
    original_code: str,
    new_code: str | None = None,
    patch: str | None = None,
    strict_mode: bool = False,
) -> ToolResponseEnvelope:
    """Simulate applying a code change and check for safety issues."""
    started = time.perf_counter()
    try:
        # [20251225_FEATURE] Tier-based behavior via capability matrix (no upgrade hints).
        tier = tier_detector.get_current_tier()
        caps = feature_caps.get_tool_capabilities("simulate_refactor", tier)
        limits = caps.get("limits", {})
        tool_caps = caps.get("capabilities", set())

        max_file_size_mb = limits.get("max_file_size_mb")
        analysis_depth = limits.get("analysis_depth", "basic")
        compliance_validation = "compliance_validation" in tool_caps

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
        return make_envelope(
            data=result,
            tool_id="simulate_refactor",
            tool_version=_pkg_version,
            tier=tier,
            duration_ms=duration_ms,
        )
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
