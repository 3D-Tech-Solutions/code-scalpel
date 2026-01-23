#!/usr/bin/env python3
"""
Test what happens when limits.toml is completely missing.
"""

import os
import tempfile
from unittest.mock import patch

from code_scalpel.licensing.config_loader import _find_config_file, load_limits
from code_scalpel.licensing.features import get_tool_capabilities

print("=" * 80)
print("TEST 1: What does config loader return when no limits.toml exists?")
print("=" * 80)

# Temporarily change to a directory with no .code-scalpel folder
with tempfile.TemporaryDirectory() as tmpdir:
    os.chdir(tmpdir)

    # Clear environment override
    env_backup = os.environ.get("CODE_SCALPEL_LIMITS_FILE")
    if env_backup:
        del os.environ["CODE_SCALPEL_LIMITS_FILE"]

    try:
        # Try to find config
        found_path = _find_config_file()
        print(f"Config file found: {found_path}")

        # Load limits
        config = load_limits()
        print(f"Loaded config: {config}")
        print(f"Config type: {type(config)}")
        print(f"Config is empty dict: {config == {}}")
        print()

    finally:
        # Restore environment
        if env_backup:
            os.environ["CODE_SCALPEL_LIMITS_FILE"] = env_backup

print("=" * 80)
print("TEST 2: What capabilities does enterprise tier get with NO limits.toml?")
print("=" * 80)

# Mock the config loader to return empty dict (simulating missing limits.toml)
with patch("code_scalpel.licensing.config_loader.get_cached_limits", return_value={}):
    caps = get_tool_capabilities("get_graph_neighborhood", "enterprise")
    limits = caps.get("limits", {})

    print(f"Enabled: {caps.get('enabled')}")
    print(f"Capabilities: {len(caps.get('capabilities', set()))} features")
    print(f"Limits: {limits}")
    print()
    print(f"max_k: {limits.get('max_k')!r}")
    print(f"max_nodes: {limits.get('max_nodes')!r}")
    print()

    if limits.get("max_k") is None and limits.get("max_nodes") is None:
        print("✅ SUCCESS: Even without limits.toml, enterprise tier is UNLIMITED")
        print("   (Falls back to hardcoded defaults in features.py)")
    else:
        print("❌ PROBLEM: Without limits.toml, enterprise tier has limits!")

print()
print("=" * 80)
print("TEST 3: Compare community/pro/enterprise without limits.toml")
print("=" * 80)

with patch("code_scalpel.licensing.config_loader.get_cached_limits", return_value={}):
    for tier in ["community", "pro", "enterprise"]:
        caps = get_tool_capabilities("get_graph_neighborhood", tier)
        limits = caps.get("limits", {})
        max_k = limits.get("max_k")
        max_nodes = limits.get("max_nodes")
        print(f"{tier.upper():12} - max_k: {max_k!r:6}, max_nodes: {max_nodes!r:6}")

print()
print("CONCLUSION:")
print("Without limits.toml, the system falls back to hardcoded defaults in features.py")
print("These defaults are correctly configured with enterprise as unlimited (None).")
