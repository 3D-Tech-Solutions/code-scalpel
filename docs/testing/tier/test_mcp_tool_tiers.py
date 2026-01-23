#!/usr/bin/env python3
"""
Test get_graph_neighborhood MCP tool with different tiers.

This validates the end-to-end behavior of the MCP tool, not just the configuration.
"""

import os
import sys
import json
import asyncio
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from code_scalpel.mcp.server import get_graph_neighborhood


async def test_mcp_tool_with_tier(tier_name: str, license_path: str = None, 
                             k: int = 2, max_nodes: int = 50) -> dict:
    """
    Test MCP tool behavior with specified tier.
    
    Args:
        tier_name: "community", "pro", or "enterprise"
        license_path: Path to JWT license (None for community)
        k: Number of hops to request
        max_nodes: Max nodes to request
        
    Returns:
        Dict with test results
    """
    # Setup environment
    old_license_path = os.environ.get("CODE_SCALPEL_LICENSE_PATH")
    
    try:
        # Set license
        if license_path:
            os.environ["CODE_SCALPEL_LICENSE_PATH"] = license_path
        elif "CODE_SCALPEL_LICENSE_PATH" in os.environ:
            del os.environ["CODE_SCALPEL_LICENSE_PATH"]
        
        # Create a mock graph for testing
        # We'll use the actual project as test data
        project_root = str(Path(__file__).parent)
        
        # Call the MCP tool
        try:
            result = await get_graph_neighborhood(
                center_node_id="python::test::function::dummy",  # Dummy node
                k=k,
                max_nodes=max_nodes,
                direction="both",
                min_confidence=0.0,
                project_root=project_root
            )
            
            return {
                "tier": tier_name,
                "license_used": license_path if license_path else "None (community)",
                "requested_k": k,
                "requested_max_nodes": max_nodes,
                "success": True,
                "result": {
                    "node_count": len(result.nodes),
                    "edge_count": len(result.edges),
                    "has_mermaid": bool(result.mermaid),
                    "truncated": result.truncated,
                    "applied_k": result.k,
                    "total_nodes": result.total_nodes,
                    "total_edges": result.total_edges,
                }
            }
        except ValueError as e:
            # Expected for tier limit violations
            return {
                "tier": tier_name,
                "license_used": license_path if license_path else "None (community)",
                "requested_k": k,
                "requested_max_nodes": max_nodes,
                "success": False,
                "error": str(e),
                "error_type": "tier_limit_violation"
            }
        except Exception as e:
            # Unexpected errors
            return {
                "tier": tier_name,
                "license_used": license_path if license_path else "None (community)",
                "requested_k": k,
                "requested_max_nodes": max_nodes,
                "success": False,
                "error": str(e),
                "error_type": "unexpected_error"
            }
    
    finally:
        # Restore environment
        if old_license_path:
            os.environ["CODE_SCALPEL_LICENSE_PATH"] = old_license_path
        elif "CODE_SCALPEL_LICENSE_PATH" in os.environ:
            del os.environ["CODE_SCALPEL_LICENSE_PATH"]


def main():
    """Run MCP tool tests across tiers."""
    print("=" * 80)
    print("MCP TOOL END-TO-END TESTING WITH TIERS")
    print("=" * 80)
    print()
    
    # Locate test licenses
    licenses_dir = Path("tests/licenses")
    pro_license = licenses_dir / "code_scalpel_license_pro_20260101_190345.jwt"
    enterprise_license = licenses_dir / "code_scalpel_license_enterprise_20260101_190754.jwt"
    
    # Verify licenses exist
    if not pro_license.exists() or not enterprise_license.exists():
        print("❌ Test licenses not found")
        return 1
    
    print(f"✅ Test licenses located")
    print()
    
    # Test scenarios
    scenarios = [
        # Community tier - should reject k>1 or nodes>20
        ("community", None, 1, 20, "Community with valid limits"),
        ("community", None, 2, 20, "Community with k=2 (should fail)"),
        ("community", None, 1, 50, "Community with nodes=50 (should fail)"),
        
        # Pro tier - should reject k>5 or nodes>100
        ("pro", str(pro_license), 5, 100, "Pro with valid limits"),
        ("pro", str(pro_license), 10, 100, "Pro with k=10 (should fail)"),
        ("pro", str(pro_license), 5, 200, "Pro with nodes=200 (should fail)"),
        
        # Enterprise tier - should accept any values
        ("enterprise", str(enterprise_license), 100, 5000, "Enterprise with large values"),
        ("enterprise", str(enterprise_license), 1000, 10000, "Enterprise with very large values"),
    ]
    
    results = []
    
    for tier, license_path, k, max_nodes, description in scenarios:
        print(f"Testing: {description}")
        print("-" * 80)
        
        result = asyncio.run(test_mcp_tool_with_tier(tier, license_path, k, max_nodes))
        results.append((description, result))
        
        # Display result
        if result["success"]:
            print(f"  Status: ✅ PASS (request accepted)")
            print(f"  Nodes returned: {result['result']['node_count']}")
            print(f"  Edges returned: {result['result']['edge_count']}")
            print(f"  Has Mermaid diagram: {result['result']['has_mermaid']}")
        else:
            expected_fail = "should fail" in description.lower()
            if expected_fail and result.get("error_type") == "tier_limit_violation":
                print(f"  Status: ✅ PASS (correctly rejected)")
                print(f"  Error: {result['error']}")
            else:
                print(f"  Status: ❌ FAIL")
                print(f"  Error type: {result.get('error_type')}")
                print(f"  Error: {result['error']}")
        
        print()
    
    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    # Analyze results
    community_enforced = any(
        not r[1]["success"] and "k=2" in r[0]
        for r in results
    )
    pro_enforced = any(
        not r[1]["success"] and ("k=10" in r[0] or "nodes=200" in r[0])
        for r in results
    )
    enterprise_unlimited = all(
        r[1]["success"]
        for r in results if "Enterprise" in r[0]
    )
    
    print(f"Community tier limits enforced: {'✅' if community_enforced else '❌'}")
    print(f"Pro tier limits enforced: {'✅' if pro_enforced else '❌'}")
    print(f"Enterprise tier unlimited: {'✅' if enterprise_unlimited else '❌'}")
    print()
    
    if community_enforced and pro_enforced and enterprise_unlimited:
        print("✅ ALL TIER BEHAVIORS CORRECT")
        return 0
    else:
        print("❌ SOME TIER BEHAVIORS INCORRECT")
        return 1


if __name__ == "__main__":
    sys.exit(main())
