"""
Code Scalpel Capabilities Module

[20260127_FEATURE] Capability resolver and validation for license-aware testing.

This module provides functions to query tool capabilities by tier, reading from
the central limits.toml configuration file.

USAGE:
    from code_scalpel.capabilities import (
        get_tool_capabilities,
        get_all_capabilities,
        get_tool_names,
        get_tier_names,
    )

    # Get capabilities for a specific tool
    caps = get_tool_capabilities("analyze_code", tier="pro")
    print(caps)  # {'tool_id': 'analyze_code', 'tier': 'pro', 'available': True, ...}

    # Get all capabilities for a tier
    all_caps = get_all_capabilities(tier="enterprise")
    print(len(all_caps))  # 22 tools

    # List available tools and tiers
    print(get_tool_names())  # All 23 tool IDs
    print(get_tier_names())  # ["community", "pro", "enterprise"]

DESIGN:
- Single source of truth: src/code_scalpel/capabilities/limits.toml
- Packaged automatically into the wheel (no force-include needed)
- Thread-safe caching to avoid re-parsing
- Stateless resolver (no external dependencies)
- Forward-compatible schema for future features
"""

from .resolver import (
    get_tool_capabilities,
    get_all_capabilities,
    get_tool_names,
    get_tier_names,
    validate_tier,
    reload_limits_cache,
    ALL_TOOLS,
    TIERS,
)

from .schema import (
    Capability,
    CapabilityLimits,
    CapabilityEnvelope,
    validate_capability,
    get_json_schema,
)

__all__ = [
    # Resolver functions
    "get_tool_capabilities",
    "get_all_capabilities",
    "get_tool_names",
    "get_tier_names",
    "validate_tier",
    "reload_limits_cache",
    # Constants
    "ALL_TOOLS",
    "TIERS",
    # Schema classes
    "Capability",
    "CapabilityLimits",
    "CapabilityEnvelope",
    "validate_capability",
    "get_json_schema",
]
