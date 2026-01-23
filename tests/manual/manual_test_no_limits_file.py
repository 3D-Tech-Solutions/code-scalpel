#!/usr/bin/env python3
"""
Test what happens when limits.toml is completely missing.
"""

import sys
from pathlib import Path

# Temporarily rename the limits.toml to simulate it not existing
try:
    original_cwd = Path.cwd()
except FileNotFoundError:
    # Handle case where working directory no longer exists
    original_cwd = Path(__file__).parent.parent

limits_path = original_cwd / ".code-scalpel" / "limits.toml"
backup_path = limits_path.with_suffix(".toml.backup")

print("=" * 80)
print("SIMULATING MISSING limits.toml")
print("=" * 80)

if limits_path.exists():
    print(f"Temporarily renaming: {limits_path}")
    limits_path.rename(backup_path)
    print(f"Renamed to: {backup_path}")
else:
    print("No limits.toml found (already missing)")
    backup_path = None

print()

try:
    # Force reload of modules to pick up the change
    if "code_scalpel.licensing.config_loader" in sys.modules:
        del sys.modules["code_scalpel.licensing.config_loader"]
    if "code_scalpel.licensing.features" in sys.modules:
        del sys.modules["code_scalpel.licensing.features"]

    from code_scalpel.licensing.config_loader import _find_config_file, load_limits
    from code_scalpel.licensing.features import get_tool_capabilities

    print("=" * 80)
    print("TEST 1: Config loader results")
    print("=" * 80)

    found_path = _find_config_file()
    print(f"Config file found: {found_path}")

    config = load_limits()
    enterprise_config = config.get("enterprise", {})
    graph_config = enterprise_config.get("get_graph_neighborhood", {})

    print(f"Config loaded: {bool(config)}")
    print(f"Enterprise section: {bool(enterprise_config)}")
    print(f"get_graph_neighborhood config: {graph_config}")
    print()

    print("=" * 80)
    print("TEST 2: Enterprise tier capabilities WITHOUT limits.toml")
    print("=" * 80)

    caps = get_tool_capabilities("get_graph_neighborhood", "enterprise")
    limits = caps.get("limits", {})

    print(f"Enabled: {caps.get('enabled')}")
    print(f"Capabilities count: {len(caps.get('capabilities', set()))}")
    print(f"Limits: {limits}")
    print()
    print(f"max_k: {limits.get('max_k')!r}")
    print(f"max_nodes: {limits.get('max_nodes')!r}")
    print()

    if limits.get("max_k") is None and limits.get("max_nodes") is None:
        print("✅ SUCCESS: WITHOUT limits.toml, enterprise tier is UNLIMITED")
        print("   Falls back to hardcoded defaults in features.py")
    else:
        print("❌ PROBLEM: Without limits.toml, enterprise tier has limits!")
        print(f"   max_k={limits.get('max_k')}, max_nodes={limits.get('max_nodes')}")

    print()
    print("=" * 80)
    print("TEST 3: All tiers WITHOUT limits.toml")
    print("=" * 80)

    for tier in ["community", "pro", "enterprise"]:
        caps = get_tool_capabilities("get_graph_neighborhood", tier)
        limits = caps.get("limits", {})
        max_k = limits.get("max_k")
        max_nodes = limits.get("max_nodes")
        print(f"{tier.upper():12} - max_k: {max_k!r:6}, max_nodes: {max_nodes!r:6}")

finally:
    # Restore the original file
    if backup_path and backup_path.exists():
        print()
        print("=" * 80)
        print("RESTORING limits.toml")
        print("=" * 80)
        backup_path.rename(limits_path)
        print(f"Restored: {limits_path}")
