"""Security MCP tool registrations.

[20260121_REFACTOR] Apply ToolResponseEnvelope to all tool responses to
meet MCP contract requirements (tier, duration, standardized errors).
"""

from __future__ import annotations

import asyncio
import time
from importlib import import_module

from mcp.server.fastmcp import Context

from code_scalpel import __version__ as _pkg_version
from code_scalpel.licensing.features import get_tool_capabilities
from code_scalpel.mcp.contract import ToolError, ToolResponseEnvelope, make_envelope
from code_scalpel.mcp.helpers.security_helpers import (
    _scan_dependencies_sync,
    _security_scan_sync,
    _type_evaporation_scan_sync,
    _unified_sink_detect_sync,
)
from code_scalpel.mcp.protocol import _get_current_tier, mcp


@mcp.tool()
async def unified_sink_detect(code: str, language: str, confidence_threshold: float = 0.7) -> ToolResponseEnvelope:
    """Unified polyglot sink detection with confidence thresholds."""
    started = time.perf_counter()
    try:
        tier = _get_current_tier()
        capabilities = get_tool_capabilities("unified_sink_detect", tier)
        result = await asyncio.to_thread(
            _unified_sink_detect_sync,
            code,
            language,
            confidence_threshold,
            tier,
            capabilities,
        )
        duration_ms = int((time.perf_counter() - started) * 1000)
        return make_envelope(
            data=result,
            tool_id="unified_sink_detect",
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
            tool_id="unified_sink_detect",
            tool_version=_pkg_version,
            tier=tier,
            duration_ms=duration_ms,
            error=error_obj,
        )


@mcp.tool()
async def type_evaporation_scan(
    frontend_code: str,
    backend_code: str,
    frontend_file: str = "frontend.ts",
    backend_file: str = "backend.py",
) -> ToolResponseEnvelope:
    """Detect Type System Evaporation vulnerabilities across frontend/backend code."""
    started = time.perf_counter()
    try:
        tier = _get_current_tier()
        caps = get_tool_capabilities("type_evaporation_scan", tier) or {}
        cap_set = set(caps.get("capabilities", []))
        limits = caps.get("limits", {}) or {}
        frontend_only = bool(limits.get("frontend_only", False))
        raw_max_files = limits.get("max_files")
        try:
            max_files = int(raw_max_files) if raw_max_files is not None else None
        except (TypeError, ValueError):
            max_files = None

        enable_pro = bool(
            {
                "implicit_any_tracing",
                "network_boundary_analysis",
                "library_boundary_analysis",
            }
            & cap_set
        )
        enable_enterprise = bool(
            {
                "runtime_validation_generation",
                "zod_schema_generation",
                "api_contract_validation",
            }
            & cap_set
        )

        result = await asyncio.to_thread(
            _type_evaporation_scan_sync,
            frontend_code,
            backend_code,
            frontend_file,
            backend_file,
            enable_pro,
            enable_enterprise,
            frontend_only,
            max_files,
        )
        duration_ms = int((time.perf_counter() - started) * 1000)
        return make_envelope(
            data=result,
            tool_id="type_evaporation_scan",
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
            tool_id="type_evaporation_scan",
            tool_version=_pkg_version,
            tier=tier,
            duration_ms=duration_ms,
            error=error_obj,
        )


@mcp.tool()
async def scan_dependencies(
    path: str | None = None,
    project_root: str | None = None,
    scan_vulnerabilities: bool = True,
    include_dev: bool = True,
    timeout: float = 30.0,
    ctx: Context | None = None,
) -> ToolResponseEnvelope:
    """Scan project dependencies for known vulnerabilities."""
    started = time.perf_counter()
    try:
        # Import PROJECT_ROOT from server to avoid circular import issues
        server = import_module("code_scalpel.mcp.server")
        resolved_path = path or project_root or str(server.PROJECT_ROOT)
        tier = _get_current_tier()
        caps = get_tool_capabilities("scan_dependencies", tier)

        if ctx:
            await ctx.report_progress(0, 100, f"Scanning dependencies in {resolved_path}...")

        result = await asyncio.to_thread(
            _scan_dependencies_sync,
            project_root=resolved_path,
            scan_vulnerabilities=scan_vulnerabilities,
            include_dev=include_dev,
            timeout=timeout,
            tier=tier,
            capabilities=caps,
            ctx=ctx,
        )

        if ctx:
            vuln_count = result.total_vulnerabilities
            await ctx.report_progress(100, 100, f"Scan complete: {vuln_count} vulnerabilities found")

        duration_ms = int((time.perf_counter() - started) * 1000)
        return make_envelope(
            data=result,
            tool_id="scan_dependencies",
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
            tool_id="scan_dependencies",
            tool_version=_pkg_version,
            tier=tier,
            duration_ms=duration_ms,
            error=error_obj,
        )


@mcp.tool()
async def security_scan(
    code: str | None = None,
    file_path: str | None = None,
    confidence_threshold: float = 0.7,
) -> ToolResponseEnvelope:
    """Scan code for security vulnerabilities using taint analysis."""
    started = time.perf_counter()
    try:
        tier = _get_current_tier()
        caps = get_tool_capabilities("security_scan", tier)
        result = await asyncio.to_thread(_security_scan_sync, code, file_path, tier, caps, confidence_threshold)
        duration_ms = int((time.perf_counter() - started) * 1000)
        return make_envelope(
            data=result,
            tool_id="security_scan",
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
            tool_id="security_scan",
            tool_version=_pkg_version,
            tier=tier,
            duration_ms=duration_ms,
            error=error_obj,
        )


__all__ = [
    "security_scan",
    "scan_dependencies",
    "type_evaporation_scan",
    "unified_sink_detect",
]
