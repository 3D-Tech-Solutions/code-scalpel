"""Analyze MCP tool registrations.

[20260121_REFACTOR] Ensure all MCP tool responses use ToolResponseEnvelope
for contract compliance (tier metadata, duration, standardized errors).
"""

from __future__ import annotations

import asyncio
import time
from importlib import import_module

from code_scalpel import __version__ as _pkg_version
from code_scalpel.mcp.contract import ToolError, ToolResponseEnvelope, make_envelope
from code_scalpel.mcp.helpers.analyze_helpers import _analyze_code_sync
from code_scalpel.mcp.protocol import _get_current_tier

# Avoid static import resolution issues in some type checkers
mcp = import_module("code_scalpel.mcp.protocol").mcp


@mcp.tool()
async def analyze_code(code: str, language: str = "auto", file_path: str | None = None) -> ToolResponseEnvelope:
    """
    Analyze source code structure.

    Use this tool to understand the high-level architecture (classes, functions, imports)
    of a file before attempting to edit it. This helps prevent hallucinating non-existent
    methods or classes.
    """
    started = time.perf_counter()
    try:
        result = await asyncio.to_thread(_analyze_code_sync, code, language, file_path)
        duration_ms = int((time.perf_counter() - started) * 1000)
        tier = _get_current_tier()

        return make_envelope(
            data=result,
            tool_id="analyze_code",
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
            tool_id="analyze_code",
            tool_version=_pkg_version,
            tier=tier,
            duration_ms=duration_ms,
            error=error_obj,
        )


__all__ = ["analyze_code"]
