"""
Tool Registry - Central registry of MCP tools and their tier requirements.

[20251225_FEATURE] Created as part of Project Reorganization Issue #5.

Maps MCP tools to their tier requirements and provides runtime gating.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class MCPTool:
    """Definition of an MCP tool."""

    name: str
    tier: str  # "community", "pro", "enterprise"
    description: str
    handler: Callable[..., Any] | None = None
    parameters: dict[str, Any] = field(default_factory=dict)
    category: str = "general"
    deprecated: bool = False
    beta: bool = False
    version: str = "1.0"
    metadata: dict[str, Any] = field(default_factory=dict)


# [20251225_FEATURE] Default MCP tool registry
# All 20 MCP tools and their tier requirements
DEFAULT_TOOLS: dict[str, MCPTool] = {
    # COMMUNITY tools (9 tools - always available)
    "analyze_code": MCPTool(
        name="analyze_code",
        tier="community",
        description="Parse and extract code structure (Python, JS, TS, Java)",
        category="analysis",
        parameters={
            "code": {"type": "string", "required": True},
            "language": {"type": "string", "required": False},
        },
    ),
    "extract_code": MCPTool(
        name="extract_code",
        tier="community",
        description="Surgical extraction by symbol name with cross-file deps",
        category="surgery",
        parameters={
            "file_path": {"type": "string", "required": True},
            "symbol_name": {"type": "string", "required": True},
        },
    ),
    "update_symbol": MCPTool(
        name="update_symbol",
        tier="community",
        description="Safely replace functions/classes/methods in files",
        category="surgery",
        parameters={
            "file_path": {"type": "string", "required": True},
            "symbol_name": {"type": "string", "required": True},
            "new_code": {"type": "string", "required": True},
        },
    ),
    "crawl_project": MCPTool(
        name="crawl_project",
        tier="community",
        description="Project-wide analysis",
        category="analysis",
        parameters={
            "directory": {"type": "string", "required": True},
        },
    ),
    "get_file_context": MCPTool(
        name="get_file_context",
        tier="community",
        description="Get surrounding context for code locations",
        category="analysis",
        parameters={
            "file_path": {"type": "string", "required": True},
            "line_number": {"type": "integer", "required": True},
        },
    ),
    "get_symbol_references": MCPTool(
        name="get_symbol_references",
        tier="community",
        description="Find all uses of a symbol",
        category="analysis",
        parameters={
            "symbol_name": {"type": "string", "required": True},
            "file_path": {"type": "string", "required": False},
        },
    ),
    "get_call_graph": MCPTool(
        name="get_call_graph",
        tier="community",
        description="Generate call graphs and trace execution flow",
        category="analysis",
        parameters={
            "file_path": {"type": "string", "required": True},
        },
    ),
    "get_project_map": MCPTool(
        name="get_project_map",
        tier="community",
        description="Generate comprehensive project structure map",
        category="analysis",
        parameters={
            "directory": {"type": "string", "required": True},
        },
    ),
    "validate_paths": MCPTool(
        name="validate_paths",
        tier="community",
        description="Validate path accessibility for Docker deployments",
        category="utilities",
        parameters={
            "paths": {"type": "array", "required": True},
        },
    ),
    "security_scan": MCPTool(
        name="security_scan",
        tier="community",  # Available at all tiers, features gated
        description="Taint-based vulnerability detection",
        category="security",
        parameters={
            "code": {"type": "string", "required": True},
            "language": {"type": "string", "required": False},
        },
    ),
    "unified_sink_detect": MCPTool(
        name="unified_sink_detect",
        tier="community",
        description="Unified polyglot sink detection with confidence",
        category="security",
        parameters={
            "code": {"type": "string", "required": True},
            "language": {"type": "string", "required": True},
        },
    ),
    "symbolic_execute": MCPTool(
        name="symbolic_execute",
        tier="community",
        description="Symbolic path exploration with Z3",
        category="analysis",
        parameters={
            "code": {"type": "string", "required": True},
        },
    ),
    "generate_unit_tests": MCPTool(
        name="generate_unit_tests",
        tier="community",
        description="Symbolic execution test generation",
        category="testing",
        parameters={
            # [20251225_FEATURE] Align parameters with server signature (code or file_path).
            "code": {"type": "string", "required": False},
            "file_path": {"type": "string", "required": False},
            "function_name": {"type": "string", "required": False},
            "framework": {"type": "string", "required": False},
        },
    ),
    "simulate_refactor": MCPTool(
        name="simulate_refactor",
        tier="community",
        description="Verify refactor preserves behavior",
        category="surgery",
        parameters={
            "original_code": {"type": "string", "required": True},
            "refactored_code": {"type": "string", "required": True},
        },
    ),
    "scan_dependencies": MCPTool(
        name="scan_dependencies",
        tier="community",
        description="Scan for vulnerable dependencies (OSV API)",
        category="security",
        parameters={
            "file_path": {"type": "string", "required": True},
        },
    ),
    "get_cross_file_dependencies": MCPTool(
        name="get_cross_file_dependencies",
        tier="community",
        description="Analyze cross-file dependency chains",
        category="analysis",
        parameters={
            "file_path": {"type": "string", "required": True},
        },
    ),
    "get_graph_neighborhood": MCPTool(
        name="get_graph_neighborhood",
        tier="community",
        description="Extract k-hop neighborhood subgraph",
        category="analysis",
        parameters={
            "node_id": {"type": "string", "required": True},
            "hops": {"type": "integer", "required": False},
        },
    ),
    "cross_file_security_scan": MCPTool(
        name="cross_file_security_scan",
        tier="community",  # Available at all tiers, features gated
        description="Cross-module taint tracking",
        category="security",
        parameters={
            "directory": {"type": "string", "required": True},
        },
    ),
    "verify_policy_integrity": MCPTool(
        name="verify_policy_integrity",
        tier="community",
        description="Cryptographic policy file verification",
        category="governance",
        parameters={
            "policy_file": {"type": "string", "required": True},
        },
    ),
    "type_evaporation_scan": MCPTool(
        name="type_evaporation_scan",
        tier="community",
        description="Detect TypeScript type evaporation vulnerabilities",
        category="security",
        parameters={
            "file_path": {"type": "string", "required": True},
        },
    ),
    # [20251228_FEATURE] Added code_policy_check tool (21st tool)
    "code_policy_check": MCPTool(
        name="code_policy_check",
        tier="community",
        description="Check code against style guides, best practices, and compliance standards",
        category="compliance",
        parameters={
            "paths": {"type": "array", "required": True},
            "rules": {"type": "array", "required": False},
            "compliance_standards": {"type": "array", "required": False},
            "custom_rules": {"type": "string", "required": False},
            "generate_report": {"type": "boolean", "required": False},
        },
    ),
}

# Tier hierarchy for comparison
TIER_LEVELS = {
    "community": 0,
    "pro": 1,
    "enterprise": 2,
}


class ToolRegistry:
    """
    Central registry of MCP tools and their tier requirements.

    Usage:
        registry = ToolRegistry()

        # Check if tool is available
        if registry.is_tool_available("security_scan"):
            pass

        # Get all available tools
        tools = registry.get_available_tools()
    """

    def __init__(self, tools: dict[str, MCPTool] | None = None):
        """
        Initialize the registry.

        Args:
            tools: Optional custom tool definitions
        """
        self._tools = dict(tools or DEFAULT_TOOLS)

    def is_tool_available(self, tool_name: str) -> bool:
        """
        Check if a tool is available at the current tier.

        Args:
            tool_name: Name of the tool

        Returns:
            True if tool is available
        """
        tool = self._tools.get(tool_name)
        if not tool:
            logger.warning(f"Unknown tool: {tool_name}")
            return False

        from code_scalpel.licensing import get_current_tier

        current_tier = get_current_tier()

        current_level = TIER_LEVELS.get(current_tier, 0)
        required_level = TIER_LEVELS.get(tool.tier, 0)

        return current_level >= required_level

    def get_tool_tier(self, tool_name: str) -> str:
        """
        Get the minimum required tier for a tool.

        Args:
            tool_name: Name of the tool

        Returns:
            Tier string or "unknown" if not found
        """
        tool = self._tools.get(tool_name)
        if not tool:
            return "unknown"
        return tool.tier

    def get_tool(self, tool_name: str) -> MCPTool | None:
        """Get tool definition by name."""
        return self._tools.get(tool_name)

    def get_available_tools(self) -> list[MCPTool]:
        """Get all tools available at the current tier."""
        from code_scalpel.licensing import get_current_tier

        current_tier = get_current_tier()
        current_level = TIER_LEVELS.get(current_tier, 0)

        available = []
        for tool in self._tools.values():
            required_level = TIER_LEVELS.get(tool.tier, 0)
            if current_level >= required_level:
                available.append(tool)

        return sorted(available, key=lambda t: t.name)

    def get_unavailable_tools(self) -> list[MCPTool]:
        """Get tools NOT available at the current tier."""
        from code_scalpel.licensing import get_current_tier

        current_tier = get_current_tier()
        current_level = TIER_LEVELS.get(current_tier, 0)

        unavailable = []
        for tool in self._tools.values():
            required_level = TIER_LEVELS.get(tool.tier, 0)
            if current_level < required_level:
                unavailable.append(tool)

        return sorted(unavailable, key=lambda t: (t.tier, t.name))

    def get_tools_by_tier(self, tier: str) -> list[MCPTool]:
        """Get all tools that require exactly the specified tier."""
        return [t for t in self._tools.values() if t.tier == tier]

    def get_tools_by_category(self, category: str) -> list[MCPTool]:
        """Get all tools in a category."""
        return [t for t in self._tools.values() if t.category == category]

    def register(self, tool: MCPTool) -> None:
        """Register a new tool."""
        self._tools[tool.name] = tool
        logger.debug(f"Registered tool: {tool.name}")

    def list_all(self) -> list[str]:
        """List all tool names."""
        return sorted(self._tools.keys())


# [20251225_FEATURE] Global registry instance
_registry: ToolRegistry | None = None


def get_tool_registry() -> ToolRegistry:
    """Get the global tool registry."""
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
    return _registry


def is_tool_available(tool_name: str) -> bool:
    """Check if a tool is available at the current tier."""
    return get_tool_registry().is_tool_available(tool_name)


def get_available_tools() -> list[MCPTool]:
    """Get all tools available at the current tier."""
    return get_tool_registry().get_available_tools()
