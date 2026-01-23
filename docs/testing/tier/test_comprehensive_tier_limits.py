#!/usr/bin/env python3
"""
Comprehensive tier limit testing for get_graph_neighborhood.

Tests all combinations:
- Community tier (no license) with/without limits.toml
- Pro tier (with JWT) with/without limits.toml  
- Enterprise tier (with JWT) with/without limits.toml

Expected behaviors:
- Community: max_k=1, max_nodes=20
- Pro: max_k=5, max_nodes=100
- Enterprise: max_k=None (unlimited), max_nodes=None (unlimited)
"""

import os
import sys
import shutil
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from code_scalpel.licensing.features import get_tool_capabilities


def test_tier_limits(tier_name: str, license_path: str = None, 
                     config_present: bool = True) -> dict:
    """
    Test tier limits for get_graph_neighborhood.
    
    Args:
        tier_name: "community", "pro", or "enterprise"
        license_path: Path to JWT license file (None for community)
        config_present: Whether limits.toml should be present
        
    Returns:
        Dict with test results
    """
    # Setup environment
    old_license_path = os.environ.get("CODE_SCALPEL_LICENSE_PATH")
    limits_toml = Path(".code-scalpel/limits.toml")
    backup_path = Path(".code-scalpel/limits.toml.backup")
    
    try:
        # Set license if provided
        if license_path:
            os.environ["CODE_SCALPEL_LICENSE_PATH"] = license_path
        elif "CODE_SCALPEL_LICENSE_PATH" in os.environ:
            del os.environ["CODE_SCALPEL_LICENSE_PATH"]
        
        # Handle limits.toml presence
        if not config_present and limits_toml.exists():
            # Temporarily rename limits.toml
            shutil.move(str(limits_toml), str(backup_path))
        
        # Get capabilities for current tier
        caps = get_tool_capabilities("get_graph_neighborhood", tier_name)
        
        # Extract limits - caps is already filtered for the specified tier
        limits = caps.get("limits", {})
        
        result = {
            "tier": tier_name,
            "license_used": license_path if license_path else "None (community default)",
            "config_present": config_present,
            "max_k": limits.get("max_k"),
            "max_nodes": limits.get("max_nodes"),
            "success": True
        }
        
        # Validate expected behavior
        if tier_name == "community":
            expected_k, expected_nodes = 1, 20
        elif tier_name == "pro":
            expected_k, expected_nodes = 5, 100
        elif tier_name == "enterprise":
            expected_k, expected_nodes = None, None
        else:
            result["success"] = False
            result["error"] = f"Unknown tier: {tier_name}"
            return result
        
        if limits.get("max_k") != expected_k or limits.get("max_nodes") != expected_nodes:
            result["success"] = False
            result["error"] = f"Expected max_k={expected_k}, max_nodes={expected_nodes}, " \
                            f"got max_k={limits.get('max_k')}, max_nodes={limits.get('max_nodes')}"
        
        return result
        
    finally:
        # Restore environment
        if old_license_path:
            os.environ["CODE_SCALPEL_LICENSE_PATH"] = old_license_path
        elif "CODE_SCALPEL_LICENSE_PATH" in os.environ:
            del os.environ["CODE_SCALPEL_LICENSE_PATH"]
        
        # Restore limits.toml if we moved it
        if not config_present and backup_path.exists():
            shutil.move(str(backup_path), str(limits_toml))


def main():
    """Run comprehensive tier tests."""
    print("=" * 80)
    print("COMPREHENSIVE TIER LIMIT TESTING")
    print("=" * 80)
    print()
    
    # Locate test licenses
    licenses_dir = Path("tests/licenses")
    pro_license = licenses_dir / "code_scalpel_license_pro_20260101_190345.jwt"
    enterprise_license = licenses_dir / "code_scalpel_license_enterprise_20260101_190754.jwt"
    
    # Verify licenses exist
    if not pro_license.exists():
        print(f"❌ Pro license not found: {pro_license}")
        return 1
    if not enterprise_license.exists():
        print(f"❌ Enterprise license not found: {enterprise_license}")
        return 1
    
    print(f"✅ Found pro license: {pro_license}")
    print(f"✅ Found enterprise license: {enterprise_license}")
    print()
    
    # Test scenarios
    scenarios = [
        # Community tier (no license)
        ("community", None, True, "Community with limits.toml"),
        ("community", None, False, "Community WITHOUT limits.toml"),
        
        # Pro tier (with license)
        ("pro", str(pro_license), True, "Pro with limits.toml"),
        ("pro", str(pro_license), False, "Pro WITHOUT limits.toml"),
        
        # Enterprise tier (with license)
        ("enterprise", str(enterprise_license), True, "Enterprise with limits.toml"),
        ("enterprise", str(enterprise_license), False, "Enterprise WITHOUT limits.toml"),
    ]
    
    results = []
    all_passed = True
    
    for tier, license_path, config_present, description in scenarios:
        print(f"Testing: {description}")
        print("-" * 80)
        
        result = test_tier_limits(tier, license_path, config_present)
        results.append(result)
        
        # Display result
        status = "✅ PASS" if result["success"] else "❌ FAIL"
        print(f"  Status: {status}")
        print(f"  Tier: {result['tier']}")
        print(f"  License: {result['license_used']}")
        print(f"  Config present: {result['config_present']}")
        print(f"  max_k: {result['max_k']}")
        print(f"  max_nodes: {result['max_nodes']}")
        
        if not result["success"]:
            print(f"  Error: {result.get('error', 'Unknown error')}")
            all_passed = False
        
        print()
    
    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    passed = sum(1 for r in results if r["success"])
    total = len(results)
    print(f"Tests passed: {passed}/{total}")
    print()
    
    if all_passed:
        print("✅ ALL TESTS PASSED")
        print()
        print("Key findings:")
        print("- Community tier: max_k=1, max_nodes=20 (both with/without config)")
        print("- Pro tier: max_k=5, max_nodes=100 (both with/without config)")
        print("- Enterprise tier: max_k=None, max_nodes=None (unlimited, both with/without config)")
        print()
        print("Conclusion: Configuration fallback chain works correctly.")
        print("Missing limits.toml does NOT affect tier limits - hardcoded defaults are used.")
        return 0
    else:
        print("❌ SOME TESTS FAILED")
        print()
        print("Failed scenarios:")
        for r in results:
            if not r["success"]:
                print(f"  - {r['tier']} (config={r['config_present']}): {r.get('error')}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
