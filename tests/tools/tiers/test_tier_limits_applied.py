#!/usr/bin/env python3
"""
Test to verify enterprise tier has unlimited k and max_nodes in practice.
"""

import pytest

from code_scalpel.licensing.features import get_tool_capabilities


@pytest.mark.parametrize(
    "tier,expected_max_k,expected_max_nodes",
    [
        ("community", 1, 20),
        ("pro", 5, 100),  # Pro has higher limits
        ("enterprise", None, None),  # Enterprise is unlimited
    ],
)
def test_tier_limits(tier: str, expected_max_k, expected_max_nodes):
    caps = get_tool_capabilities("get_graph_neighborhood", tier)
    limits = caps.get("limits", {})
    max_k = limits.get("max_k")
    max_nodes = limits.get("max_nodes")

    assert max_k == expected_max_k, f"{tier} expected max_k={expected_max_k}, got {max_k}"
    assert max_nodes == expected_max_nodes, f"{tier} expected max_nodes={expected_max_nodes}, got {max_nodes}"


print("  Enterprise: Unlimited (None) - should allow k=100, max_nodes=5000")
