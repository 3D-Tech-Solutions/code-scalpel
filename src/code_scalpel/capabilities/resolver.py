"""
Capability Resolver - Resolve tool capabilities by tier and license.

[20260127_FEATURE] Centralized capability resolution system for license-aware testing.
[20260205_REFACTOR] Removed duplicate file-finding / caching; delegates to config_loader.

This module provides functions to query which capabilities are available at a given
tier.  All TOML loading and caching is handled by config_loader; this module is a
thin envelope layer on top.

USAGE:
    from code_scalpel.capabilities import get_tool_capabilities, get_all_capabilities

    caps = get_tool_capabilities("analyze_code", tier="pro")
    # {'tool_id': 'analyze_code', 'tier': 'pro', 'available': True, 'limits': {...}}

    all_caps = get_all_capabilities(tier="enterprise")
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from code_scalpel.licensing.config_loader import get_cached_limits, reload_config

logger = logging.getLogger(__name__)

# All 23 tools in Code Scalpel (alphabetical order)
# Note: These are the tools registered in TOOL_CAPABILITIES
# (excludes oracle tools and special system tools)
ALL_TOOLS = [
    "analyze_code",
    "code_policy_check",
    "crawl_project",
    "cross_file_security_scan",
    "extract_code",
    "generate_unit_tests",
    "get_call_graph",
    "get_capabilities",
    "get_cross_file_dependencies",
    "get_file_context",
    "get_graph_neighborhood",
    "get_project_map",
    "get_symbol_references",
    "rename_symbol",
    "scan_dependencies",
    "security_scan",
    "simulate_refactor",
    "symbolic_execute",
    "type_evaporation_scan",
    "unified_sink_detect",
    "update_symbol",
    "validate_paths",
    "verify_policy_integrity",
]

# All tier names
TIERS = ["community", "pro", "enterprise"]


def get_tool_capabilities(tool_id: str, tier: str = "community") -> Dict[str, Any]:
    """
    Get the capabilities/limits for a specific tool at a specific tier.

    Args:
        tool_id: Tool identifier (e.g., "analyze_code")
        tier: Tier name ("community", "pro", "enterprise")

    Returns:
        Dictionary with structure:
        {
            "tool_id": "analyze_code",
            "tier": "pro",
            "available": True,
            "limits": {
                "max_file_size_mb": 10,
                "languages": ["python", "javascript", ...]
            }
        }

        If tool is not available at the tier, "available" is False and "limits" is empty.

    Example:
        >>> caps = get_tool_capabilities("analyze_code", tier="pro")
        >>> print(caps["available"])  # True
        >>> print(caps["limits"]["max_file_size_mb"])  # 10
    """
    # Normalize inputs
    tool_id_lower = tool_id.lower()
    tier_lower = tier.lower()

    # Validate tier
    if tier_lower not in TIERS:
        logger.warning(f"Invalid tier: {tier_lower}. Valid tiers: {TIERS}")
        tier_lower = "community"

    # Load limits from shared config_loader cache
    limits = get_cached_limits()

    # Look for limits[tier][tool_id] (nested dict structure)
    tier_limits = limits.get(tier_lower, {})
    tool_limits = tier_limits.get(tool_id_lower, {})

    # Return capability envelope
    return {
        "tool_id": tool_id_lower,
        "tier": tier_lower,
        "available": bool(tool_limits),  # Available if section exists
        "limits": tool_limits if tool_limits else {},
    }


def get_all_capabilities(tier: str = "community") -> Dict[str, Dict[str, Any]]:
    """
    Get all capabilities for all 23 tools at a specific tier.

    Args:
        tier: Tier name ("community", "pro", "enterprise")

    Returns:
        Dictionary mapping tool_id -> capability dict for that tool at the tier.

        {
            "analyze_code": {
                "tool_id": "analyze_code",
                "tier": "pro",
                "available": True,
                "limits": {...}
            },
            "get_file_context": {
                "tool_id": "get_file_context",
                "tier": "pro",
                "available": True,
                "limits": {...}
            },
            ...
        }

    Example:
        >>> all_caps = get_all_capabilities(tier="pro")
        >>> print(len(all_caps))  # 23
        >>> print(all_caps["analyze_code"]["available"])  # True
    """
    return {tool: get_tool_capabilities(tool, tier) for tool in ALL_TOOLS}


def get_tool_names() -> list[str]:
    """Get the list of all 23 tool names."""
    return ALL_TOOLS.copy()


def get_tier_names() -> list[str]:
    """Get the list of all supported tier names."""
    return TIERS.copy()


def validate_tier(tier: str) -> bool:
    """Check if a tier name is valid."""
    return tier.lower() in TIERS


def reload_limits_cache() -> None:
    """Force reload of the limits.toml file (delegates to config_loader)."""
    reload_config()
    logger.info("Limits cache reloaded")
