"""Policy and governance MCP tool registrations.

[20260121_REFACTOR] Wrap tool responses with ToolResponseEnvelope to satisfy
MCP contract tests (tier metadata included).
"""

from __future__ import annotations

import asyncio
import time

from code_scalpel import __version__ as _pkg_version
from code_scalpel.licensing.features import get_tool_capabilities
from code_scalpel.mcp.contract import ToolError, ToolResponseEnvelope, make_envelope
from code_scalpel.mcp.helpers.policy_helpers import (
    _code_policy_check_sync,
    _get_current_tier,
    _validate_paths_sync,
    _verify_policy_integrity_sync,
)
from code_scalpel.mcp.protocol import mcp


@mcp.tool()
async def validate_paths(paths: list[str], project_root: str | None = None) -> ToolResponseEnvelope:
    """Validate that paths are accessible before running file-based operations."""
    started = time.perf_counter()
    try:
        tier = _get_current_tier()
        capabilities = get_tool_capabilities("validate_paths", tier) or {}
        result = await asyncio.to_thread(_validate_paths_sync, paths, project_root, tier, capabilities)
        duration_ms = int((time.perf_counter() - started) * 1000)
        return make_envelope(
            data=result,
            tool_id="validate_paths",
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
            tool_id="validate_paths",
            tool_version=_pkg_version,
            tier=tier,
            duration_ms=duration_ms,
            error=error_obj,
        )


@mcp.tool()
async def verify_policy_integrity(
    policy_dir: str | None = None,
    manifest_source: str = "file",
) -> ToolResponseEnvelope:
    """Verify policy file integrity using cryptographic signatures."""
    started = time.perf_counter()
    try:
        tier = _get_current_tier()
        capabilities = get_tool_capabilities("verify_policy_integrity", tier) or {}
        result = await asyncio.to_thread(
            _verify_policy_integrity_sync,
            policy_dir,
            manifest_source,
            tier,
            capabilities,
        )
        duration_ms = int((time.perf_counter() - started) * 1000)
        return make_envelope(
            data=result,
            tool_id="verify_policy_integrity",
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
            tool_id="verify_policy_integrity",
            tool_version=_pkg_version,
            tier=tier,
            duration_ms=duration_ms,
            error=error_obj,
        )


@mcp.tool()
async def code_policy_check(
    paths: list[str],
    rules: list[str] | None = None,
    compliance_standards: list[str] | None = None,
    generate_report: bool = False,
) -> ToolResponseEnvelope:
    """Check code against style guides, best practices, and compliance standards."""
    started = time.perf_counter()
    try:
        tier = _get_current_tier()
        capabilities = get_tool_capabilities("code_policy_check", tier) or {}

        if compliance_standards and tier != "enterprise":
            compliance_standards = None

        if generate_report and tier != "enterprise":
            generate_report = False

        result = await asyncio.to_thread(
            _code_policy_check_sync,
            paths,
            rules,
            compliance_standards,
            generate_report,
            tier,
            capabilities,
        )
        duration_ms = int((time.perf_counter() - started) * 1000)
        return make_envelope(
            data=result,
            tool_id="code_policy_check",
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
            tool_id="code_policy_check",
            tool_version=_pkg_version,
            tier=tier,
            duration_ms=duration_ms,
            error=error_obj,
        )


__all__ = ["validate_paths", "verify_policy_integrity", "code_policy_check"]
