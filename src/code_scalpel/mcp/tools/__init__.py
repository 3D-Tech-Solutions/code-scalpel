"""Tool registration package for MCP tools."""

from __future__ import annotations

from importlib import import_module


def register_tools() -> None:
    """Import tool modules to trigger MCP registration."""
    import_module("code_scalpel.mcp.tools.analyze")
    import_module("code_scalpel.mcp.tools.security")
    import_module("code_scalpel.mcp.tools.extraction")
    import_module("code_scalpel.mcp.tools.symbolic")
    import_module("code_scalpel.mcp.tools.context")
    import_module("code_scalpel.mcp.tools.graph")
    import_module("code_scalpel.mcp.tools.policy")


__all__ = ["register_tools"]
