#!/usr/bin/env python3
"""
Quick test to verify how limits.toml omission affects get_graph_neighborhood.
"""

from code_scalpel.licensing.config_loader import (
    get_tool_limits,
    load_limits,
    merge_limits,
)
from code_scalpel.licensing.features import TOOL_CAPABILITIES, get_tool_capabilities

# Check hardcoded defaults
print("=" * 80)
print("HARDCODED DEFAULTS from features.py:")
print("=" * 80)
enterprise_defaults = TOOL_CAPABILITIES.get("get_graph_neighborhood", {}).get("enterprise", {})
print(f"Enterprise limits (hardcoded): {enterprise_defaults.get('limits', {})}")
print()

# Load from TOML
print("=" * 80)
print("TOML CONFIGURATION:")
print("=" * 80)
config = load_limits()
enterprise_toml = get_tool_limits("get_graph_neighborhood", "enterprise", config)
print(f"Enterprise limits (TOML): {enterprise_toml}")
print()

# Get merged capabilities
print("=" * 80)
print("MERGED RESULT from get_tool_capabilities():")
print("=" * 80)
caps = get_tool_capabilities("get_graph_neighborhood", "enterprise")
print(f"Enabled: {caps.get('enabled')}")
print(f"Capabilities: {caps.get('capabilities', set())}")
print(f"Limits: {caps.get('limits', {})}")
print()

# Test the merge logic directly
print("=" * 80)
print("TESTING MERGE LOGIC:")
print("=" * 80)
defaults = {"max_k": None, "max_nodes": None}
overrides_empty = {}
overrides_partial = {"max_k": 10}

merged_empty = merge_limits(defaults, overrides_empty)
merged_partial = merge_limits(defaults, overrides_partial)

print(f"Defaults: {defaults}")
print(f"Overrides (empty): {overrides_empty}")
print(f"Merged (empty): {merged_empty}")
print()
print(f"Overrides (partial): {overrides_partial}")
print(f"Merged (partial): {merged_partial}")
print()

# Key question: Does omitting values from TOML preserve None?
print("=" * 80)
print("CRITICAL TEST: Does omission preserve None (unlimited)?")
print("=" * 80)
final_limits = caps.get("limits", {})
max_k = final_limits.get("max_k")
max_nodes = final_limits.get("max_nodes")

print(f"max_k = {max_k!r} (type: {type(max_k).__name__})")
print(f"max_nodes = {max_nodes!r} (type: {type(max_nodes).__name__})")
print()
print(f"max_k is None: {max_k is None}")
print(f"max_nodes is None: {max_nodes is None}")
print()

if max_k is None and max_nodes is None:
    print("✅ SUCCESS: Omitting values from TOML preserves None (unlimited)")
else:
    print("❌ PROBLEM: Omitting values did NOT preserve None")
    print("   This means enterprise tier still has limits!")
