"""Helper modules for MCP tool implementations.

This package contains the actual implementation logic for MCP tools,
extracted from server.py during the refactoring process.

Structure:
- analyze_helpers.py: Code analysis helper functions
- security_helpers.py: Security scanning helper functions
- symbolic_helpers.py: Symbolic execution and test generation helpers
- extraction_helpers.py: Code extraction and modification helpers
- context_helpers.py: File context and project discovery helpers
- graph_helpers.py: Call graph and dependency analysis helpers
- policy_helpers.py: Policy validation and verification helpers

Usage:
    The tool modules in tools/*.py import from these helper modules:

    # In tools/analyze.py
    from code_scalpel.mcp.helpers.analyze_helpers import _analyze_code_sync

    @mcp.tool()
    async def analyze_code(...):
        return await asyncio.to_thread(_analyze_code_sync, ...)
"""

from __future__ import annotations

from . import (
    analyze_helpers,
    context_helpers,
    extraction_helpers,
    graph_helpers,
    policy_helpers,
    security_helpers,
    symbolic_helpers,
)

__all__ = [
    "analyze_helpers",
    "security_helpers",
    "symbolic_helpers",
    "extraction_helpers",
    "context_helpers",
    "graph_helpers",
    "policy_helpers",
]
