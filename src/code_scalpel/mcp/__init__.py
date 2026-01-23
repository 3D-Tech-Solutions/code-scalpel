"""
Code Scalpel MCP Server - Model Context Protocol integration.

This module provides a fully MCP-compliant server that exposes Code Scalpel's
analysis capabilities through the official MCP protocol.

Supports:
- stdio transport (preferred for local integration)
- Streamable HTTP transport (for network deployment)

[20251216_FEATURE] v2.2.0 - Structured MCP Logging
- Tool invocation tracking with timing
- Success/failure metrics
- Analytics queries for usage patterns
    - Export prompt templates as resources (code_review_prompt, security_audit_prompt, etc.)
    - Implement prompt registry with versioning
    - Support custom prompt injection from client

    - Implement request rate limiting by client ID
    - Add quota tracking (requests per hour/day)
    - Support tiered rate limits (free/pro/enterprise)

    - Validate all MCP request payloads against JSON Schema
    - Implement strict type checking for response models
    - Add schema versioning for backwards compatibility

COMMUNITY TIER (Core MCP Integration):

PRO TIER (Enhanced MCP Features):

ENTERPRISE TIER (Distributed & Scale):

"""

# [20260119_BUGFIX] Close module docstring to fix SyntaxError during imports.

from __future__ import annotations

from typing import TYPE_CHECKING, Any

# [20251228_BUGFIX] Avoid stdlib `logging` shadowing when server is run as a script.
from .mcp_logging import (
    MCPAnalytics,
    ToolInvocation,  # noqa: E402
    get_analytics,
    log_tool_error,
    log_tool_invocation,
    log_tool_success,
    mcp_logger,
)

if TYPE_CHECKING:
    # Make `mcp` visible to type checkers without eagerly importing at runtime.
    from .server import mcp as mcp
else:
    mcp: Any


def _load_server():
    # Import lazily to avoid runpy warnings when executing the module as a script
    # (python -m code_scalpel.mcp.server).
    from . import server as _server

    return _server


def get_mcp():
    """Return the FastMCP server instance (lazy import)."""

    return _load_server().mcp


def run_server(*args, **kwargs):
    """Run the MCP server (lazy import)."""

    return _load_server().run_server(*args, **kwargs)


def __getattr__(name: str):
    # Backwards compatibility: older code imported `mcp` from this package.
    if name == "mcp":
        return get_mcp()
    raise AttributeError(name)


__all__ = [
    "get_mcp",
    "mcp",
    "run_server",
    # [20251216_FEATURE] v2.2.0 - Logging exports
    "MCPAnalytics",
    "ToolInvocation",
    "log_tool_invocation",
    "log_tool_success",
    "log_tool_error",
    "get_analytics",
    "mcp_logger",
]
