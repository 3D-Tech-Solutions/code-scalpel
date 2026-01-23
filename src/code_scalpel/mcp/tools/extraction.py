"""Extraction and refactor MCP tool registrations.

[20260121_REFACTOR] Wrap outputs in ToolResponseEnvelope to meet MCP
contract expectations (tier metadata and standardized envelope).
"""

from __future__ import annotations

import sys
import time

from mcp.server.fastmcp import Context

from code_scalpel import __version__ as _pkg_version
from code_scalpel.mcp.contract import ToolError, ToolResponseEnvelope, make_envelope
from code_scalpel.mcp.helpers import extraction_helpers as _helpers
from code_scalpel.mcp.models.core import PatchResultModel
from code_scalpel.mcp.protocol import _get_current_tier, mcp

_extract_code = getattr(_helpers, "extract_code", None) or getattr(_helpers, "_extract_code_impl", None)
_rename_symbol = getattr(_helpers, "rename_symbol", None)
_update_symbol = getattr(_helpers, "update_symbol", None)

if _extract_code is None or _rename_symbol is None or _update_symbol is None:
    raise ImportError("Extraction helpers missing expected tool implementations.")


@mcp.tool()
async def extract_code(
    target_type: str,
    target_name: str,
    file_path: str | None = None,
    code: str | None = None,
    language: str | None = None,
    include_context: bool = False,
    context_depth: int = 1,
    include_cross_file_deps: bool = False,
    include_token_estimate: bool = True,
    variable_promotion: bool = False,
    closure_detection: bool = False,
    dependency_injection_suggestions: bool = False,
    as_microservice: bool = False,
    microservice_host: str = "127.0.0.1",
    microservice_port: int = 8000,
    organization_wide: bool = False,
    workspace_root: str | None = None,
    ctx: Context | None = None,
) -> ToolResponseEnvelope:
    """Extract code elements with optional dependency context."""
    started = time.perf_counter()
    try:
        if _extract_code is None:
            # [20260118_BUGFIX] Return error response instead of raising TypeError
            from code_scalpel.mcp.models.core import ContextualExtractionResult

            result = ContextualExtractionResult(
                success=False,
                target_name=target_name,
                target_code="",
                context_code="",
                full_code="",
                error="extract_code helper not loaded",
            )
        else:
            result = await _extract_code(
                target_type,
                target_name,
                file_path=file_path,
                code=code,
                language=language,
                include_context=include_context,
                context_depth=context_depth,
                include_cross_file_deps=include_cross_file_deps,
                include_token_estimate=include_token_estimate,
                variable_promotion=variable_promotion,
                closure_detection=closure_detection,
                dependency_injection_suggestions=dependency_injection_suggestions,
                as_microservice=as_microservice,
                microservice_host=microservice_host,
                microservice_port=microservice_port,
                organization_wide=organization_wide,
                workspace_root=workspace_root,
                ctx=ctx,
            )
        duration_ms = int((time.perf_counter() - started) * 1000)
        tier = _get_current_tier()
        return make_envelope(
            data=result,
            tool_id="extract_code",
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
            tool_id="extract_code",
            tool_version=_pkg_version,
            tier=tier,
            duration_ms=duration_ms,
            error=error_obj,
        )


@mcp.tool()
async def rename_symbol(
    file_path: str,
    target_type: str,
    target_name: str,
    new_name: str,
    create_backup: bool = True,
) -> ToolResponseEnvelope:
    """Rename a function, class, or method in a file."""
    started = time.perf_counter()
    try:
        if _rename_symbol is None:
            result = PatchResultModel(
                success=False,
                file_path=file_path,
                target_name=target_name,
                target_type=target_type,
                error="rename_symbol helper not loaded",
            )
        else:
            result = await _rename_symbol(
                file_path=file_path,
                target_type=target_type,
                target_name=target_name,
                new_name=new_name,
                create_backup=create_backup,
            )
        duration_ms = int((time.perf_counter() - started) * 1000)
        tier = _get_current_tier()
        return make_envelope(
            data=result,
            tool_id="rename_symbol",
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
            tool_id="rename_symbol",
            tool_version=_pkg_version,
            tier=tier,
            duration_ms=duration_ms,
            error=error_obj,
        )


@mcp.tool()
async def update_symbol(
    file_path: str,
    target_type: str,
    target_name: str,
    new_code: str | None = None,
    operation: str = "replace",
    new_name: str | None = None,
    create_backup: bool = True,
) -> ToolResponseEnvelope:
    """Safely replace a function, class, or method in a file."""
    started = time.perf_counter()
    try:
        if _update_symbol is None:
            result = PatchResultModel(
                success=False,
                file_path=file_path,
                target_name=target_name,
                target_type=target_type,
                error="update_symbol helper not loaded",
            )
        else:
            # Trace wrapper entry to stderr to aid debugging stdio hangs
            try:
                print("[MCP TRACE] wrapper.update_symbol: calling helper", file=sys.stderr)
            except Exception:
                pass

            result = await _update_symbol(
                file_path=file_path,
                target_type=target_type,
                target_name=target_name,
                new_code=new_code,
                operation=operation,
                new_name=new_name,
                create_backup=create_backup,
            )
            try:
                print("[MCP TRACE] wrapper.update_symbol: helper returned", file=sys.stderr)
            except Exception:
                pass
        duration_ms = int((time.perf_counter() - started) * 1000)
        tier = _get_current_tier()
        return make_envelope(
            data=result,
            tool_id="update_symbol",
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
            tool_id="update_symbol",
            tool_version=_pkg_version,
            tier=tier,
            duration_ms=duration_ms,
            error=error_obj,
        )


__all__ = ["extract_code", "rename_symbol", "update_symbol"]
