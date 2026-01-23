"""Context and discovery MCP tool registrations.

[20260121_REFACTOR] Wrap tool responses in ToolResponseEnvelope for MCP
contract compliance across HTTP and stdio transports.
"""

from __future__ import annotations

import time

from mcp.server.fastmcp import Context

from code_scalpel import __version__ as _pkg_version
from code_scalpel.mcp.contract import ToolError, ToolResponseEnvelope, make_envelope
from code_scalpel.mcp.helpers.context_helpers import (
    crawl_project as _crawl_project,
)
from code_scalpel.mcp.helpers.context_helpers import (
    get_file_context as _get_file_context,
)
from code_scalpel.mcp.helpers.context_helpers import (
    get_symbol_references as _get_symbol_references,
)
from code_scalpel.mcp.protocol import _get_current_tier, mcp


@mcp.tool()
async def crawl_project(
    root_path: str | None = None,
    exclude_dirs: list[str] | None = None,
    complexity_threshold: int = 10,
    include_report: bool = True,
    pattern: str | None = None,
    pattern_type: str = "regex",
    include_related: list[str] | None = None,
    ctx: Context | None = None,
) -> ToolResponseEnvelope:
    """Crawl a project directory and analyze Python files."""
    started = time.perf_counter()
    try:
        result = await _crawl_project(
            root_path=root_path,
            exclude_dirs=exclude_dirs,
            complexity_threshold=complexity_threshold,
            include_report=include_report,
            pattern=pattern,
            pattern_type=pattern_type,
            include_related=include_related,
            ctx=ctx,
        )
        duration_ms = int((time.perf_counter() - started) * 1000)
        tier = _get_current_tier()
        return make_envelope(
            data=result,
            tool_id="crawl_project",
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
            tool_id="crawl_project",
            tool_version=_pkg_version,
            tier=tier,
            duration_ms=duration_ms,
            error=error_obj,
        )


@mcp.tool()
async def get_file_context(file_path: str) -> ToolResponseEnvelope:
    """Get a file overview without reading full content."""
    started = time.perf_counter()
    try:
        result = await _get_file_context(file_path)
        duration_ms = int((time.perf_counter() - started) * 1000)
        tier = _get_current_tier()
        return make_envelope(
            data=result,
            tool_id="get_file_context",
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
            tool_id="get_file_context",
            tool_version=_pkg_version,
            tier=tier,
            duration_ms=duration_ms,
            error=error_obj,
        )


@mcp.tool()
async def get_symbol_references(
    symbol_name: str,
    project_root: str | None = None,
    scope_prefix: str | None = None,
    include_tests: bool = True,
    ctx: Context | None = None,
) -> ToolResponseEnvelope:
    """Find all references to a symbol across the project."""
    started = time.perf_counter()
    try:
        result = await _get_symbol_references(
            symbol_name,
            project_root=project_root,
            scope_prefix=scope_prefix,
            include_tests=include_tests,
            ctx=ctx,
        )
        duration_ms = int((time.perf_counter() - started) * 1000)
        tier = _get_current_tier()
        return make_envelope(
            data=result,
            tool_id="get_symbol_references",
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
            tool_id="get_symbol_references",
            tool_version=_pkg_version,
            tier=tier,
            duration_ms=duration_ms,
            error=error_obj,
        )


__all__ = ["crawl_project", "get_file_context", "get_symbol_references"]
