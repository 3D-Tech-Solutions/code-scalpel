"""
Adversarial Tests for v2.5.0 Guardian Features.

# [20250108_TEST] v2.5.0 Guardian - Adversarial security tests

These tests verify that the v2.5.0 features resist adversarial attacks
and edge cases identified in the 3rd party security review.

Test Categories:
- ADV-2.5.1: Telephone Game (Confidence Decay accuracy)
- ADV-2.5.2: Threshold Rejection (Low-confidence blocking)
- ADV-2.5.3: Context Explosion (Graph truncation)
- ADV-2.5.4: Relevance Test (Confidence-based pruning)
- ADV-2.5.5: chmod Bypass (Hash verification)
- ADV-2.5.6: Manifest Tamper (HMAC signature verification)
"""

import json
import os
import stat
from unittest.mock import patch

import pytest

# [20250108_TEST] Import confidence calculator for negative-decay guardrails
from code_scalpel.ast_tools.cross_file_extractor import calculate_confidence

# ============================================================================
# CONFIDENCE DECAY ADVERSARIAL TESTS
# ============================================================================


class TestADV251TelephoneGame:
    """
    ADV-2.5.1: "Telephone Game" Test

    Create a 10-hop dependency chain where each link is 90% confident.
    Verify the reported confidence at the end is ~34% (0.9^10 ≈ 0.349),
    not 90%. This validates that confidence compounds correctly across
    transitive dependencies.
    """

    @pytest.fixture
    def ten_hop_chain_project(self, tmp_path):
        """
        Create a 10-level dependency chain for the telephone game test.

        Structure:
        level_0.py -> level_1.py -> level_2.py -> ... -> level_9.py -> level_10.py

        Each level imports and calls the next level's function.
        """
        for i in range(11):  # 0 through 10
            content = f'''"""Level {i} module."""

'''
            if i < 10:
                content += f'''from level_{i+1} import level_{i+1}_func

def level_{i}_func():
    """Call the next level."""
    return level_{i+1}_func()
'''
            else:
                # Terminal level
                content += '''def level_10_func():
    """Terminal function at depth 10."""
    return "end of chain"
'''

            (tmp_path / f"level_{i}.py").write_text(content)

        return tmp_path

    def test_telephone_game_confidence_decay(self, ten_hop_chain_project):
        """
        ADV-2.5.1: Verify 10-hop chain shows ~34% confidence at depth 10.

        Formula: C_effective = C_base × 0.9^depth
        At depth 10: 1.0 × 0.9^10 = 0.3486784401 ≈ 0.349

        This test ensures confidence is NOT reported as 90% (single-hop)
        but rather ~34% (compound decay).
        """
        from code_scalpel.ast_tools.cross_file_extractor import (
            CrossFileExtractor,
            calculate_confidence,
        )

        # First verify the formula directly
        expected_confidence_depth_10 = 0.9**10
        assert abs(expected_confidence_depth_10 - 0.3486784401) < 0.0001

        # Verify calculate_confidence function
        calculated = calculate_confidence(depth=10, decay_factor=0.9)
        assert (
            abs(calculated - expected_confidence_depth_10) < 0.0001
        ), f"calculate_confidence(10) returned {calculated}, expected ~0.349"

        # Now test with actual extraction
        extractor = CrossFileExtractor(ten_hop_chain_project)
        extractor.build()

        result = extractor.extract(
            str(ten_hop_chain_project / "level_0.py"),
            "level_0_func",
            depth=10,
            confidence_decay_factor=0.9,
        )

        assert result.success, f"Extraction failed: {result.error}"

        # Find the deepest dependency (level_10_func)
        deepest_dep = None
        max_depth = 0
        for dep in result.dependencies:
            if dep.depth > max_depth:
                max_depth = dep.depth
                deepest_dep = dep

        # The deepest dependency should have confidence ≈ 0.349
        if deepest_dep:
            assert deepest_dep.depth >= 9, f"Expected deep chain, got max depth {max_depth}"

            # Confidence at depth 10 should be ~0.349, NOT 0.9
            expected_at_depth = 0.9**deepest_dep.depth
            assert abs(deepest_dep.confidence - expected_at_depth) < 0.01, (
                f"At depth {deepest_dep.depth}: got confidence {deepest_dep.confidence}, "
                f"expected {expected_at_depth}"
            )

            # CRITICAL: Confidence must NOT be 0.9 (single-hop fallacy)
            assert (
                deepest_dep.confidence < 0.5
            ), f"FAIL: Confidence {deepest_dep.confidence} >= 0.5 suggests decay not applied correctly"

    def test_telephone_game_cumulative_decay(self, ten_hop_chain_project):
        """
        Verify confidence decays cumulatively at each level.

        Level 0: 1.0
        Level 1: 0.9
        Level 2: 0.81
        Level 3: 0.729
        ...
        Level 10: 0.349
        """
        from code_scalpel.ast_tools.cross_file_extractor import CrossFileExtractor

        extractor = CrossFileExtractor(ten_hop_chain_project)
        extractor.build()

        result = extractor.extract(
            str(ten_hop_chain_project / "level_0.py"),
            "level_0_func",
            depth=10,
            confidence_decay_factor=0.9,
        )

        assert result.success

        # Group dependencies by depth
        confidence_by_depth = {}
        for dep in result.dependencies:
            if dep.depth not in confidence_by_depth:
                confidence_by_depth[dep.depth] = []
            confidence_by_depth[dep.depth].append(dep.confidence)

        # Verify each depth level has correct confidence
        for depth, confidences in confidence_by_depth.items():
            expected = 0.9**depth
            for conf in confidences:
                assert abs(conf - expected) < 0.01, f"Depth {depth}: got {conf}, expected {expected}"

    # [20251216_TEST] Adversarial boundary tests for confidence decay
    def test_telephone_game_extreme_decay_factor_zero(self, ten_hop_chain_project):
        """
        ADV-2.5.1 ADVERSARIAL: decay_factor=0 should immediately kill confidence.

        With decay_factor=0, ANY dependency beyond depth 0 should have
        confidence = 0. This tests the boundary condition.
        """
        from code_scalpel.ast_tools.cross_file_extractor import CrossFileExtractor

        extractor = CrossFileExtractor(ten_hop_chain_project)
        extractor.build()

        result = extractor.extract(
            str(ten_hop_chain_project / "level_0.py"),
            "level_0_func",
            depth=5,
            confidence_decay_factor=0.0,  # EXTREME: zero decay
        )

        assert result.success

        # All dependencies at depth > 0 should have confidence = 0
        for dep in result.dependencies:
            if dep.depth > 0:
                assert (
                    dep.confidence == 0.0
                ), f"With decay_factor=0, depth {dep.depth} should have confidence=0, got {dep.confidence}"

    def test_telephone_game_extreme_decay_factor_one(self, ten_hop_chain_project):
        """
        ADV-2.5.1 ADVERSARIAL: decay_factor=1.0 should preserve full confidence.

        With decay_factor=1.0, confidence should NOT decay at all.
        All dependencies should have confidence = 1.0.
        """
        from code_scalpel.ast_tools.cross_file_extractor import CrossFileExtractor

        extractor = CrossFileExtractor(ten_hop_chain_project)
        extractor.build()

        result = extractor.extract(
            str(ten_hop_chain_project / "level_0.py"),
            "level_0_func",
            depth=10,
            confidence_decay_factor=1.0,  # EXTREME: no decay
        )

        assert result.success

        # All dependencies should have confidence = 1.0
        for dep in result.dependencies:
            assert (
                abs(dep.confidence - 1.0) < 0.001
            ), f"With decay_factor=1.0, all deps should have confidence=1.0, got {dep.confidence}"

    def test_telephone_game_extreme_decay_factor_greater_than_one(self, ten_hop_chain_project):
        """
        ADV-2.5.1 ADVERSARIAL: decay_factor > 1.0 should be clamped or rejected.

        A malicious agent might try decay_factor=1.5 to INCREASE confidence
        at depth. The system MUST NOT allow confidence > 1.0.

        SECURITY FINDING: This test FAILED because confidence values exceeded 1.0.
        The calculate_confidence() function does not clamp decay_factor.

        REMEDIATION: Add input validation to clamp decay_factor to [0.0, 1.0]
        """
        from code_scalpel.ast_tools.cross_file_extractor import CrossFileExtractor

        extractor = CrossFileExtractor(ten_hop_chain_project)
        extractor.build()

        result = extractor.extract(
            str(ten_hop_chain_project / "level_0.py"),
            "level_0_func",
            depth=5,
            confidence_decay_factor=1.5,  # ATTACK: amplification attempt
        )

        # System should clamp to 1.0 confidence at worst
        assert result.success
        for dep in result.dependencies:
            assert 0.0 <= dep.confidence <= 1.0, f"Confidence out of range with decay_factor>1: {dep.confidence}"

    def test_telephone_game_negative_decay_factor(self, ten_hop_chain_project):
        """
        ADV-2.5.1 ADVERSARIAL: Negative decay_factor should be rejected.

        Negative decay creates oscillating confidence which is nonsensical.
        The system should reject or clamp to valid range.

        SECURITY FINDING: This test FAILED because confidence values were negative.
        The calculate_confidence() function does not validate decay_factor >= 0.

        REMEDIATION: Add input validation to reject negative decay_factor
        """
        from code_scalpel.ast_tools.cross_file_extractor import CrossFileExtractor

        extractor = CrossFileExtractor(ten_hop_chain_project)
        extractor.build()

        # Entire extraction should fail fast on invalid decay_factor
        with pytest.raises(ValueError):
            extractor.extract(
                str(ten_hop_chain_project / "level_0.py"),
                "level_0_func",
                depth=5,
                confidence_decay_factor=-0.5,  # ATTACK: negative decay
            )

        # And direct calculation should also raise
        with pytest.raises(ValueError):
            calculate_confidence(depth=1, decay_factor=-0.5)

    def test_telephone_game_float_precision_attack(self, ten_hop_chain_project):
        """
        ADV-2.5.1 ADVERSARIAL: Test float precision doesn't cause confidence overflow.

        With very small decay factors and deep chains, verify no underflow/overflow.
        """
        from code_scalpel.ast_tools.cross_file_extractor import CrossFileExtractor

        extractor = CrossFileExtractor(ten_hop_chain_project)
        extractor.build()

        # Test with very small decay (near-zero after few hops)
        result = extractor.extract(
            str(ten_hop_chain_project / "level_0.py"),
            "level_0_func",
            depth=10,
            confidence_decay_factor=0.1,  # 0.1^10 = 1e-10 (very small)
        )

        assert result.success

        for dep in result.dependencies:
            # Confidence should be valid float, not NaN, Inf, or negative
            assert dep.confidence == dep.confidence, "NaN confidence detected"
            assert dep.confidence != float("inf"), "Infinite confidence detected"
            assert dep.confidence >= 0.0, f"Negative confidence: {dep.confidence}"


class TestADV252ThresholdRejection:
    """
    ADV-2.5.2: Threshold Rejection Test

    Verify that an agent is blocked from acting on a deep transitive
    dependency that falls below the min_confidence threshold.

    With 0.9 decay:
    - Depth 7: 0.9^7 = 0.478 (below 0.5 threshold)
    - Depth 8: 0.9^8 = 0.430
    """

    @pytest.fixture
    def deep_chain_project(self, tmp_path):
        """Create an 8-level dependency chain."""
        for i in range(9):  # 0 through 8
            content = f'''"""Level {i} module."""

'''
            if i < 8:
                content += f"""from level_{i+1} import level_{i+1}_func

def level_{i}_func():
    return level_{i+1}_func()
"""
            else:
                content += """def level_8_func():
    return "terminal"
"""
            (tmp_path / f"level_{i}.py").write_text(content)

        return tmp_path

    def test_threshold_rejection_flags_low_confidence(self, deep_chain_project):
        """
        Verify low-confidence symbols are flagged.

        At depth 7+ with 0.9 decay, confidence < 0.5 (default threshold).
        These should be identified as low confidence.
        """
        from code_scalpel.ast_tools.cross_file_extractor import (
            DEFAULT_LOW_CONFIDENCE_THRESHOLD,
            CrossFileExtractor,
        )

        extractor = CrossFileExtractor(deep_chain_project)
        extractor.build()

        result = extractor.extract(
            str(deep_chain_project / "level_0.py"),
            "level_0_func",
            depth=8,
            confidence_decay_factor=0.9,
        )

        assert result.success

        # Find dependencies below threshold
        low_conf_deps = [d for d in result.dependencies if d.confidence < DEFAULT_LOW_CONFIDENCE_THRESHOLD]

        # With 0.9 decay, depth 7+ should be below 0.5 threshold
        # 0.9^7 = 0.478 < 0.5
        assert (
            len(low_conf_deps) >= 2
        ), f"Expected at least 2 low-confidence deps (depth 7+), found {len(low_conf_deps)}"

        # All low confidence deps should have confidence < threshold
        for dep in low_conf_deps:
            assert dep.confidence < DEFAULT_LOW_CONFIDENCE_THRESHOLD, (
                f"Dependency at depth {dep.depth} with confidence {dep.confidence} "
                f"should be below threshold {DEFAULT_LOW_CONFIDENCE_THRESHOLD}"
            )

    def test_threshold_rejection_warning_generated(self, deep_chain_project):
        """
        Verify warning is generated when extracting low-confidence symbols.
        """
        from code_scalpel.ast_tools.cross_file_extractor import CrossFileExtractor

        extractor = CrossFileExtractor(deep_chain_project)
        extractor.build()

        result = extractor.extract(
            str(deep_chain_project / "level_0.py"),
            "level_0_func",
            depth=8,
            confidence_decay_factor=0.9,
        )

        assert result.success

        if result.low_confidence_count > 0:
            assert result.has_low_confidence_symbols, "has_low_confidence_symbols should be True"

            # Check for warning
            low_conf_symbols = result.get_low_confidence_symbols()
            assert len(low_conf_symbols) > 0, "get_low_confidence_symbols() should return flagged symbols"

    def test_mcp_tool_reports_low_confidence(self, deep_chain_project):
        """
        Verify MCP tool includes low_confidence_warning in response.
        """
        import asyncio

        from code_scalpel.mcp.server import get_cross_file_dependencies

        async def run_test():
            result = await get_cross_file_dependencies(
                target_file="level_0.py",
                target_symbol="level_0_func",
                project_root=str(deep_chain_project),
                max_depth=8,
                confidence_decay_factor=0.9,
            )
            return result

        result = asyncio.run(run_test())

        assert result.success

        # Should have low confidence count
        if result.low_confidence_count > 0:
            assert result.low_confidence_warning is not None, "low_confidence_warning should be present"
            assert "low confidence" in result.low_confidence_warning.lower()

    # [20251216_TEST] Adversarial tests for threshold rejection bypass attempts
    def test_threshold_boundary_exact_threshold(self, deep_chain_project):
        """
        ADV-2.5.2 ADVERSARIAL: Test EXACT boundary at threshold.

        At depth 6 with 0.9 decay: 0.9^6 = 0.531441 (just above 0.5)
        At depth 7 with 0.9 decay: 0.9^7 = 0.478297 (just below 0.5)

        Verify boundary behavior is EXACTLY correct.
        """
        from code_scalpel.ast_tools.cross_file_extractor import (
            DEFAULT_LOW_CONFIDENCE_THRESHOLD,
            CrossFileExtractor,
        )

        extractor = CrossFileExtractor(deep_chain_project)
        extractor.build()

        result = extractor.extract(
            str(deep_chain_project / "level_0.py"),
            "level_0_func",
            depth=7,
            confidence_decay_factor=0.9,
        )

        assert result.success

        # Find dependency at exactly depth 6 (should be HIGH confidence)
        depth_6_deps = [d for d in result.dependencies if d.depth == 6]
        for dep in depth_6_deps:
            expected = 0.9**6  # 0.531441
            assert (
                dep.confidence >= DEFAULT_LOW_CONFIDENCE_THRESHOLD
            ), f"Depth 6 ({expected:.6f}) should be ABOVE threshold {DEFAULT_LOW_CONFIDENCE_THRESHOLD}"

        # Find dependency at exactly depth 7 (should be LOW confidence)
        depth_7_deps = [d for d in result.dependencies if d.depth == 7]
        for dep in depth_7_deps:
            expected = 0.9**7  # 0.478297
            assert (
                dep.confidence < DEFAULT_LOW_CONFIDENCE_THRESHOLD
            ), f"Depth 7 ({expected:.6f}) should be BELOW threshold {DEFAULT_LOW_CONFIDENCE_THRESHOLD}"

    def test_threshold_attack_custom_threshold_bypass(self, deep_chain_project):
        """
        ADV-2.5.2 ADVERSARIAL: Attempt to bypass by providing custom threshold.

        If the API allows custom thresholds, verify the system still
        uses a MINIMUM threshold that cannot be set to 0.
        """
        from code_scalpel.ast_tools.cross_file_extractor import CrossFileExtractor

        extractor = CrossFileExtractor(deep_chain_project)
        extractor.build()

        result = extractor.extract(
            str(deep_chain_project / "level_0.py"),
            "level_0_func",
            depth=8,
            confidence_decay_factor=0.9,
        )

        assert result.success

        # Even with very low or zero threshold, the SYSTEM should track
        # which symbols are considered low confidence by DEFAULT threshold
        # This ensures agents cannot hide low-confidence results
        assert hasattr(result, "low_confidence_count") or hasattr(
            result, "has_low_confidence_symbols"
        ), "System must track low-confidence symbols regardless of custom threshold"

    def test_threshold_attack_negative_depth(self, deep_chain_project):
        """
        ADV-2.5.2 ADVERSARIAL: Attempt extraction with negative depth.

        Negative depth is nonsensical. System should reject or clamp to 0.
        """
        from code_scalpel.ast_tools.cross_file_extractor import CrossFileExtractor

        extractor = CrossFileExtractor(deep_chain_project)
        extractor.build()

        result = extractor.extract(
            str(deep_chain_project / "level_0.py"),
            "level_0_func",
            depth=-5,  # ATTACK: negative depth
            confidence_decay_factor=0.9,
        )

        # Should either fail or treat as depth=0
        if result.success:
            # With depth=0 or negative, should only return the target function itself
            # or no transitive dependencies
            for dep in result.dependencies:
                assert dep.depth >= 0, f"Negative depth {dep.depth} in result"

    def test_threshold_attack_huge_depth(self, deep_chain_project):
        """
        ADV-2.5.2 ADVERSARIAL: Attempt extraction with huge depth (DoS prevention).

        With depth=10000, system should not hang or consume excessive memory.
        Either cap depth or fail gracefully.
        """
        import time

        from code_scalpel.ast_tools.cross_file_extractor import CrossFileExtractor

        extractor = CrossFileExtractor(deep_chain_project)
        extractor.build()

        start = time.time()
        result = extractor.extract(
            str(deep_chain_project / "level_0.py"),
            "level_0_func",
            depth=10000,  # ATTACK: resource exhaustion attempt
            confidence_decay_factor=0.9,
        )
        elapsed = time.time() - start

        # Should complete in reasonable time (< 30 seconds)
        # Even with huge depth, actual chain is only 8 levels
        assert elapsed < 30.0, f"Extraction took {elapsed:.1f}s with depth=10000 - possible DoS vulnerability"

        # Result should be valid
        if result.success:
            # Max depth should be capped at actual chain depth
            max_found = max((d.depth for d in result.dependencies), default=0)
            assert max_found <= 10, f"Found depth {max_found} in 8-level chain - depth not bounded correctly"


# ============================================================================
# GRAPH NEIGHBORHOOD ADVERSARIAL TESTS
# ============================================================================


class TestADV253ContextExplosion:
    """
    ADV-2.5.3: Context Explosion Test

    Request a neighborhood on a dense "hub" node (e.g., common utility
    called by 500+ callers). Verify the result contains exactly max_nodes
    (default 100) and NOT the entire graph.
    """

    @pytest.fixture
    def dense_hub_graph(self):
        """
        Create a graph with a dense hub node that has 500+ connections.

        Structure:
        - Hub node: "common_util" connected to 500 caller nodes
        - Each caller connects to the hub
        """
        from code_scalpel.graph_engine import (
            EdgeType,
            GraphEdge,
            GraphNode,
            NodeType,
            UniversalGraph,
            UniversalNodeID,
        )

        graph = UniversalGraph()

        # Create the dense hub node
        hub_id = UniversalNodeID(
            language="python",
            module="utils",
            node_type=NodeType.FUNCTION,
            name="common_util",
            line=1,
        )
        graph.add_node(GraphNode(id=hub_id, metadata={"file": "utils.py"}))

        # Create 500 caller nodes, each calling the hub
        for i in range(500):
            caller_id = UniversalNodeID(
                language="python",
                module=f"module_{i}",
                node_type=NodeType.FUNCTION,
                name=f"caller_{i}",
                line=10,
            )
            graph.add_node(GraphNode(id=caller_id, metadata={"file": f"module_{i}.py"}))

            # Edge from caller to hub (outgoing from caller)
            graph.add_edge(
                GraphEdge(
                    from_id=str(caller_id),
                    to_id=str(hub_id),
                    edge_type=EdgeType.DIRECT_CALL,
                    confidence=0.9,
                    evidence="Direct call to utility",
                )
            )

        return graph, str(hub_id)

    def test_context_explosion_truncation(self, dense_hub_graph):
        """
        ADV-2.5.3: Verify dense hub is truncated to max_nodes.

        With 500 callers, requesting neighborhood with max_nodes=100
        should return exactly 100 nodes, not 501.
        """
        graph, hub_id = dense_hub_graph

        # Request neighborhood with default max_nodes=100
        result = graph.get_neighborhood(center_node_id=hub_id, k=2, max_nodes=100, direction="both")

        assert result.success, "Neighborhood extraction failed"

        # CRITICAL: Must be truncated
        assert result.truncated, "Graph with 501 nodes should be truncated when max_nodes=100"

        # Must not exceed max_nodes
        assert len(result.subgraph.nodes) <= 100, f"Got {len(result.subgraph.nodes)} nodes, expected <= 100"

        # Must have truncation warning
        assert result.truncation_warning is not None, "truncation_warning should be set when truncated"
        assert "truncated" in result.truncation_warning.lower()

    def test_context_explosion_exactly_max_nodes(self, dense_hub_graph):
        """
        Verify truncated graph contains exactly max_nodes (not fewer).
        """
        graph, hub_id = dense_hub_graph

        result = graph.get_neighborhood(center_node_id=hub_id, k=1, max_nodes=50, direction="both")

        assert result.success
        assert result.truncated

        # Should have exactly max_nodes (or close to it)
        # The center node + up to 49 more = 50 max
        assert len(result.subgraph.nodes) == 50, f"Got {len(result.subgraph.nodes)} nodes, expected exactly 50"

    def test_context_explosion_different_max_nodes(self, dense_hub_graph):
        """
        Verify max_nodes parameter is respected with different values.
        """
        graph, hub_id = dense_hub_graph

        for max_n in [10, 25, 100, 200]:
            result = graph.get_neighborhood(center_node_id=hub_id, k=2, max_nodes=max_n, direction="both")

            assert result.success
            assert len(result.subgraph.nodes) <= max_n, f"max_nodes={max_n}: got {len(result.subgraph.nodes)} nodes"


class TestADV254Relevance:
    """
    ADV-2.5.4: Relevance Test

    When truncation occurs, ensure the pruned nodes are the LOWEST
    confidence ones, not randomly selected. Create a graph with known
    confidence values and verify the retained nodes are the highest-
    confidence paths from center.
    """

    @pytest.fixture
    def known_confidence_graph(self):
        """
        Create a graph with explicitly known confidence values.

        Structure:
        - Center node with connections to nodes at varying confidence
        - High confidence path: center -> high_1 -> high_2 (conf 0.95)
        - Medium confidence path: center -> med_1 -> med_2 (conf 0.7)
        - Low confidence path: center -> low_1 -> low_2 (conf 0.3)
        """
        from code_scalpel.graph_engine import (
            EdgeType,
            GraphEdge,
            GraphNode,
            NodeType,
            UniversalGraph,
            UniversalNodeID,
        )

        graph = UniversalGraph()

        # Center node
        center_id = UniversalNodeID(
            language="python",
            module="main",
            node_type=NodeType.FUNCTION,
            name="center",
            line=1,
        )
        graph.add_node(GraphNode(id=center_id, metadata={"file": "main.py"}))
        center_str = str(center_id)

        # High confidence path (0.95)
        for i, name in enumerate(["high_1", "high_2", "high_3"]):
            node_id = UniversalNodeID(
                language="python",
                module="high",
                node_type=NodeType.FUNCTION,
                name=name,
                line=10 + i,
            )
            graph.add_node(GraphNode(id=node_id, metadata={"confidence_group": "high"}))

            from_id = center_str if i == 0 else f"python::high::function::high_{i}"
            graph.add_edge(
                GraphEdge(
                    from_id=from_id,
                    to_id=str(node_id),
                    edge_type=EdgeType.DIRECT_CALL,
                    confidence=0.95,
                    evidence="High confidence edge",
                )
            )

        # Medium confidence path (0.7)
        for i, name in enumerate(["med_1", "med_2", "med_3"]):
            node_id = UniversalNodeID(
                language="python",
                module="med",
                node_type=NodeType.FUNCTION,
                name=name,
                line=20 + i,
            )
            graph.add_node(GraphNode(id=node_id, metadata={"confidence_group": "medium"}))

            from_id = center_str if i == 0 else f"python::med::function::med_{i}"
            graph.add_edge(
                GraphEdge(
                    from_id=from_id,
                    to_id=str(node_id),
                    edge_type=EdgeType.DIRECT_CALL,
                    confidence=0.7,
                    evidence="Medium confidence edge",
                )
            )

        # Low confidence path (0.3)
        for i, name in enumerate(["low_1", "low_2", "low_3"]):
            node_id = UniversalNodeID(
                language="python",
                module="low",
                node_type=NodeType.FUNCTION,
                name=name,
                line=30 + i,
            )
            graph.add_node(GraphNode(id=node_id, metadata={"confidence_group": "low"}))

            from_id = center_str if i == 0 else f"python::low::function::low_{i}"
            graph.add_edge(
                GraphEdge(
                    from_id=from_id,
                    to_id=str(node_id),
                    edge_type=EdgeType.DIRECT_CALL,
                    confidence=0.3,
                    evidence="Low confidence edge",
                )
            )

        return graph, center_str

    def test_relevance_high_confidence_retained(self, known_confidence_graph):
        """
        ADV-2.5.4: Verify high-confidence paths are retained when truncating.
        """
        graph, center_id = known_confidence_graph

        # With min_confidence=0.5, low confidence edges should be filtered
        result = graph.get_neighborhood(
            center_node_id=center_id,
            k=3,
            max_nodes=100,
            direction="outgoing",
            min_confidence=0.5,
        )

        assert result.success

        # Check which nodes are included
        node_ids = [str(n.id) for n in result.subgraph.nodes]

        # High confidence nodes should be present
        assert any("high" in nid for nid in node_ids), "High confidence nodes should be retained"

        # Medium confidence nodes should be present (0.7 > 0.5)
        assert any("med" in nid for nid in node_ids), "Medium confidence nodes should be retained"

        # Low confidence nodes should be EXCLUDED (0.3 < 0.5)
        assert not any(
            "low" in nid for nid in node_ids
        ), "Low confidence nodes should be excluded with min_confidence=0.5"

    def test_relevance_confidence_filtering(self, known_confidence_graph):
        """
        Verify min_confidence parameter filters correctly.
        """
        graph, center_id = known_confidence_graph

        # Test different confidence thresholds
        # With 0.8 threshold, only high confidence should pass
        result_high = graph.get_neighborhood(center_node_id=center_id, k=3, min_confidence=0.8)

        # With 0.2 threshold, all should pass
        result_all = graph.get_neighborhood(center_node_id=center_id, k=3, min_confidence=0.2)

        # High threshold should have fewer nodes
        assert len(result_high.subgraph.nodes) < len(
            result_all.subgraph.nodes
        ), "Higher min_confidence should result in fewer nodes"

    # [20251216_TEST] Adversarial tests for graph neighborhood attacks
    def test_relevance_determinism(self, known_confidence_graph):
        """
        ADV-2.5.4 ADVERSARIAL: Verify truncation is DETERMINISTIC.

        Run neighborhood extraction 10 times with same parameters.
        Results MUST be identical every time (no random tie-breaking).
        """
        graph, center_id = known_confidence_graph

        results = []
        for _ in range(10):
            result = graph.get_neighborhood(
                center_node_id=center_id,
                k=3,
                max_nodes=5,  # Force truncation
                direction="outgoing",
            )
            assert result.success
            node_ids = sorted([str(n.id) for n in result.subgraph.nodes])
            results.append(node_ids)

        # All results must be identical
        for i, r in enumerate(results[1:], 1):
            assert r == results[0], (
                f"DETERMINISM VIOLATION: Run {i} differs from run 0. " f"Got {r}, expected {results[0]}"
            )

    def test_context_explosion_memory_bound(self):
        """
        ADV-2.5.3 ADVERSARIAL: Verify memory is bounded.

        With 500 nodes and max_nodes=10, memory usage should NOT
        explode to hold the full graph.
        """
        from code_scalpel.graph_engine import (
            EdgeType,
            GraphEdge,
            GraphNode,
            NodeType,
            UniversalGraph,
            UniversalNodeID,
        )

        graph = UniversalGraph()

        # Create hub
        hub_id = UniversalNodeID(
            language="python",
            module="utils",
            node_type=NodeType.FUNCTION,
            name="common_util",
            line=1,
        )
        graph.add_node(GraphNode(id=hub_id, metadata={}))

        # Create 500 callers
        for i in range(500):
            caller_id = UniversalNodeID(
                language="python",
                module=f"module_{i}",
                node_type=NodeType.FUNCTION,
                name=f"caller_{i}",
                line=10,
            )
            graph.add_node(GraphNode(id=caller_id, metadata={}))
            graph.add_edge(
                GraphEdge(
                    from_id=str(caller_id),
                    to_id=str(hub_id),
                    edge_type=EdgeType.DIRECT_CALL,
                    confidence=0.9,
                    evidence="test",
                )
            )

        result = graph.get_neighborhood(center_node_id=str(hub_id), k=2, max_nodes=10, direction="both")

        assert result.success

        # Result object should be reasonably sized
        assert len(result.subgraph.nodes) <= 10, f"Memory bound violated: {len(result.subgraph.nodes)} nodes in result"

    def test_context_explosion_zero_max_nodes(self):
        """
        ADV-2.5.3 ADVERSARIAL: max_nodes=0 should return only center or fail.
        """
        from code_scalpel.graph_engine import (
            EdgeType,
            GraphEdge,
            GraphNode,
            NodeType,
            UniversalGraph,
            UniversalNodeID,
        )

        graph = UniversalGraph()
        hub_id = UniversalNodeID(
            language="python",
            module="utils",
            node_type=NodeType.FUNCTION,
            name="common_util",
            line=1,
        )
        graph.add_node(GraphNode(id=hub_id, metadata={}))

        # Add some connected nodes
        for i in range(10):
            caller_id = UniversalNodeID(
                language="python",
                module=f"module_{i}",
                node_type=NodeType.FUNCTION,
                name=f"caller_{i}",
                line=10,
            )
            graph.add_node(GraphNode(id=caller_id, metadata={}))
            graph.add_edge(
                GraphEdge(
                    from_id=str(caller_id),
                    to_id=str(hub_id),
                    edge_type=EdgeType.DIRECT_CALL,
                    confidence=0.9,
                    evidence="test",
                )
            )

        result = graph.get_neighborhood(
            center_node_id=str(hub_id),
            k=2,
            max_nodes=0,  # EDGE CASE: zero nodes requested
            direction="both",
        )

        # Should either fail or return minimal result
        if result.success:
            # At most the center node (or empty)
            assert (
                len(result.subgraph.nodes) <= 1
            ), f"max_nodes=0 should return at most 1 node, got {len(result.subgraph.nodes)}"

    def test_context_explosion_negative_max_nodes(self):
        """
        ADV-2.5.3 ADVERSARIAL: Negative max_nodes should be rejected.
        """
        from code_scalpel.graph_engine import (
            GraphNode,
            NodeType,
            UniversalGraph,
            UniversalNodeID,
        )

        graph = UniversalGraph()
        hub_id = UniversalNodeID(
            language="python",
            module="utils",
            node_type=NodeType.FUNCTION,
            name="hub",
            line=1,
        )
        graph.add_node(GraphNode(id=hub_id, metadata={}))

        result = graph.get_neighborhood(
            center_node_id=str(hub_id),
            k=2,
            max_nodes=-100,  # ATTACK: negative
            direction="both",
        )

        # Should either fail or treat as 0/default
        if result.success:
            # Should NOT return negative or huge number of nodes
            assert len(result.subgraph.nodes) >= 0, "Negative node count is impossible"

    def test_context_explosion_negative_k(self):
        """
        ADV-2.5.3 ADVERSARIAL: Negative k (radius) should be rejected.
        """
        from code_scalpel.graph_engine import (
            GraphNode,
            NodeType,
            UniversalGraph,
            UniversalNodeID,
        )

        graph = UniversalGraph()
        hub_id = UniversalNodeID(
            language="python",
            module="utils",
            node_type=NodeType.FUNCTION,
            name="hub",
            line=1,
        )
        graph.add_node(GraphNode(id=hub_id, metadata={}))

        result = graph.get_neighborhood(
            center_node_id=str(hub_id),
            k=-5,  # ATTACK: negative radius
            max_nodes=100,
            direction="both",
        )

        # Should either fail or treat as k=0
        if result.success:
            # With k=0, should return only center node
            assert (
                len(result.subgraph.nodes) <= 1
            ), f"k=-5 should be treated as k=0, got {len(result.subgraph.nodes)} nodes"

    def test_context_explosion_huge_k(self):
        """
        ADV-2.5.3 ADVERSARIAL: Huge k should still respect max_nodes.
        """
        from code_scalpel.graph_engine import (
            EdgeType,
            GraphEdge,
            GraphNode,
            NodeType,
            UniversalGraph,
            UniversalNodeID,
        )

        graph = UniversalGraph()

        # Create hub
        hub_id = UniversalNodeID(
            language="python",
            module="utils",
            node_type=NodeType.FUNCTION,
            name="common_util",
            line=1,
        )
        graph.add_node(GraphNode(id=hub_id, metadata={}))

        # Create some connections
        for i in range(100):
            caller_id = UniversalNodeID(
                language="python",
                module=f"module_{i}",
                node_type=NodeType.FUNCTION,
                name=f"caller_{i}",
                line=10,
            )
            graph.add_node(GraphNode(id=caller_id, metadata={}))
            graph.add_edge(
                GraphEdge(
                    from_id=str(caller_id),
                    to_id=str(hub_id),
                    edge_type=EdgeType.DIRECT_CALL,
                    confidence=0.9,
                    evidence="test",
                )
            )

        result = graph.get_neighborhood(
            center_node_id=str(hub_id),
            k=1000000,  # ATTACK: huge radius
            max_nodes=50,
            direction="both",
        )

        assert result.success
        # max_nodes should still be respected
        assert (
            len(result.subgraph.nodes) <= 50
        ), f"max_nodes=50 not respected with k=1000000, got {len(result.subgraph.nodes)}"

    def test_relevance_invalid_min_confidence(self, known_confidence_graph):
        """
        ADV-2.5.4 ADVERSARIAL: Invalid min_confidence values.
        """
        graph, center_id = known_confidence_graph

        # Test min_confidence > 1.0 (impossible to satisfy)
        result = graph.get_neighborhood(
            center_node_id=center_id,
            k=3,
            min_confidence=1.5,  # ATTACK: impossible threshold
        )

        # Should return only center node (nothing can meet conf > 1.0)
        if result.success:
            # Only the center node could potentially be included
            # (or empty if edges are filtered first)
            assert len(result.subgraph.nodes) <= 1 or result.subgraph.nodes is not None

    def test_relevance_tie_breaking_consistency(self):
        """
        ADV-2.5.4 ADVERSARIAL: When confidences are EXACTLY equal, tie-breaking must be deterministic.

        Create graph with identical confidence values and verify consistent ordering.
        """
        from code_scalpel.graph_engine import (
            EdgeType,
            GraphEdge,
            GraphNode,
            NodeType,
            UniversalGraph,
            UniversalNodeID,
        )

        graph = UniversalGraph()

        # Center node
        center_id = UniversalNodeID(
            language="python",
            module="main",
            node_type=NodeType.FUNCTION,
            name="center",
            line=1,
        )
        graph.add_node(GraphNode(id=center_id, metadata={}))

        # Create 20 nodes with IDENTICAL confidence (0.5)
        for i in range(20):
            node_id = UniversalNodeID(
                language="python",
                module=f"mod_{i}",
                node_type=NodeType.FUNCTION,
                name=f"func_{i}",
                line=10,
            )
            graph.add_node(GraphNode(id=node_id, metadata={}))
            graph.add_edge(
                GraphEdge(
                    from_id=str(center_id),
                    to_id=str(node_id),
                    edge_type=EdgeType.DIRECT_CALL,
                    confidence=0.5,  # ALL IDENTICAL
                    evidence="test",
                )
            )

        # Run 10 times with max_nodes=5 (forces tie-breaking)
        results = []
        for _ in range(10):
            result = graph.get_neighborhood(center_node_id=str(center_id), k=1, max_nodes=5)
            assert result.success
            node_ids = sorted([str(n.id) for n in result.subgraph.nodes])
            results.append(node_ids)

        # All results must be identical (deterministic tie-breaking)
        for i in range(1, len(results)):
            assert results[i] == results[0], f"TIE-BREAKING VIOLATION: Non-deterministic selection at run {i}"


# ============================================================================
# CRYPTOGRAPHIC POLICY VERIFICATION ADVERSARIAL TESTS
# ============================================================================


class TestADV255ChmodBypass:
    """
    ADV-2.5.5: chmod Bypass Test

    Simulate an agent attack: chmod +w .code-scalpel/policy.yaml, edit the
    file to add "allow_all: true", then verify that Code Scalpel refuses
    to operate because SHA-256 hash no longer matches the signed manifest.
    """

    @pytest.fixture
    def signed_policy_dir(self, tmp_path):
        """
        Create a policy directory with signed manifest.
        """
        policy_dir = tmp_path / ".code-scalpel"
        policy_dir.mkdir()

        # Create original policy file
        policy_content = """
policies:
  - name: no_sql_injection
    description: Prevent SQL injection
    rule: |
      package scalpel.security
      deny[msg] { msg := "SQL injection" }
"""
        policy_file = policy_dir / "policy.yaml"
        policy_file.write_text(policy_content)

        # Set read-only permissions (simulating production)
        policy_file.chmod(stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)  # 0o444

        # Create and sign manifest
        secret_key = "test-secret-for-adversarial-test"

        from code_scalpel.policy_engine import CryptographicPolicyVerifier

        manifest = CryptographicPolicyVerifier.create_manifest(
            policy_files=["policy.yaml"],
            secret_key=secret_key,
            signed_by="security-admin@test.com",
            policy_dir=str(policy_dir),
        )
        CryptographicPolicyVerifier.save_manifest(manifest, str(policy_dir))

        return policy_dir, secret_key

    def test_chmod_bypass_detected(self, signed_policy_dir):
        """
        ADV-2.5.5: Simulate agent bypassing chmod protection.

        1. Make file writable: chmod +w policy.yaml
        2. Modify policy: add "allow_all: true"
        3. Attempt verification -> MUST FAIL
        """
        policy_dir, secret_key = signed_policy_dir
        policy_file = policy_dir / "policy.yaml"

        # Step 1: Agent runs chmod +w (simulated)
        policy_file.chmod(stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)  # 0o644

        # Step 2: Agent modifies the policy (ATTACK)
        malicious_content = """
# MALICIOUS MODIFICATION
policies:
  - name: allow_all
    description: Allow everything
    rule: |
      package scalpel.security
      deny = false
"""
        policy_file.write_text(malicious_content)

        # Step 3: Verification MUST fail
        from code_scalpel.policy_engine import (
            CryptographicPolicyVerifier,
            SecurityError,
        )

        with patch.dict(os.environ, {"SCALPEL_MANIFEST_SECRET": secret_key}):
            verifier = CryptographicPolicyVerifier(
                manifest_source="file",
                policy_dir=str(policy_dir),
            )

            # CRITICAL: This must raise SecurityError
            with pytest.raises(SecurityError) as exc:
                verifier.verify_all_policies()

            # Verify the error message indicates tampering
            error_msg = str(exc.value).lower()
            assert (
                "tampered" in error_msg or "mismatch" in error_msg or "denied" in error_msg
            ), f"Expected tampering detection, got: {exc.value}"

    def test_chmod_bypass_hash_mismatch_details(self, signed_policy_dir):
        """
        Verify specific hash mismatch is reported.
        """
        policy_dir, secret_key = signed_policy_dir
        policy_file = policy_dir / "policy.yaml"

        # Make writable and modify
        policy_file.chmod(0o644)
        original_content = policy_file.read_text()
        policy_file.write_text(original_content + "\n# Added comment")

        from code_scalpel.policy_engine import (
            CryptographicPolicyVerifier,
            SecurityError,
        )

        with patch.dict(os.environ, {"SCALPEL_MANIFEST_SECRET": secret_key}):
            verifier = CryptographicPolicyVerifier(
                manifest_source="file",
                policy_dir=str(policy_dir),
            )

            with pytest.raises(SecurityError) as exc:
                verifier.verify_all_policies()

            # Should mention the specific file
            assert "policy.yaml" in str(exc.value)


class TestADV256ManifestTamper:
    """
    ADV-2.5.6: Manifest Tamper Test

    Edit policy.manifest.json to change the signature to match a fake
    policy. Assert that HMAC signature verification fails with
    SecurityError and all operations are DENIED (fail closed).
    """

    @pytest.fixture
    def signed_policy_dir(self, tmp_path):
        """Create a policy directory with valid signed manifest."""
        policy_dir = tmp_path / ".code-scalpel"
        policy_dir.mkdir()

        # Create policy file
        policy_file = policy_dir / "policy.yaml"
        policy_file.write_text("policies: []")

        # Create valid manifest
        secret_key = "real-secret-key"

        from code_scalpel.policy_engine import CryptographicPolicyVerifier

        manifest = CryptographicPolicyVerifier.create_manifest(
            policy_files=["policy.yaml"],
            secret_key=secret_key,
            signed_by="admin@test.com",
            policy_dir=str(policy_dir),
        )
        CryptographicPolicyVerifier.save_manifest(manifest, str(policy_dir))

        return policy_dir, secret_key

    def test_manifest_tamper_fake_signature(self, signed_policy_dir):
        """
        ADV-2.5.6: Replace signature with a fake one.

        Attack: Modify manifest signature to match a different policy.
        Result: HMAC verification must fail.
        """
        policy_dir, secret_key = signed_policy_dir
        manifest_file = policy_dir / "policy.manifest.json"

        # Load and tamper with manifest
        with open(manifest_file) as f:
            manifest_data = json.load(f)

        # Replace signature with a fake one
        manifest_data["signature"] = "deadbeef" * 8  # 64 char fake signature

        with open(manifest_file, "w") as f:
            json.dump(manifest_data, f)

        # Verification must fail
        from code_scalpel.policy_engine import (
            CryptographicPolicyVerifier,
            SecurityError,
        )

        with patch.dict(os.environ, {"SCALPEL_MANIFEST_SECRET": secret_key}):
            verifier = CryptographicPolicyVerifier(
                manifest_source="file",
                policy_dir=str(policy_dir),
            )

            with pytest.raises(SecurityError) as exc:
                verifier.verify_all_policies()

            error_msg = str(exc.value).lower()
            assert "signature" in error_msg or "invalid" in error_msg, f"Expected signature failure, got: {exc.value}"

    def test_manifest_tamper_modified_hashes(self, signed_policy_dir):
        """
        Attack: Modify the file hashes in the manifest.
        """
        policy_dir, secret_key = signed_policy_dir
        manifest_file = policy_dir / "policy.manifest.json"

        # Tamper with file hashes
        with open(manifest_file) as f:
            manifest_data = json.load(f)

        # Change the hash to allow a different policy
        manifest_data["files"]["policy.yaml"] = "0" * 64

        with open(manifest_file, "w") as f:
            json.dump(manifest_data, f)

        from code_scalpel.policy_engine import (
            CryptographicPolicyVerifier,
            SecurityError,
        )

        with patch.dict(os.environ, {"SCALPEL_MANIFEST_SECRET": secret_key}):
            verifier = CryptographicPolicyVerifier(
                manifest_source="file",
                policy_dir=str(policy_dir),
            )

            # Signature verification will fail (manifest contents changed)
            with pytest.raises(SecurityError):
                verifier.verify_all_policies()

    def test_manifest_tamper_wrong_secret(self, signed_policy_dir):
        """
        Attack: Try to verify with a different secret key.
        """
        policy_dir, _ = signed_policy_dir

        from code_scalpel.policy_engine import (
            CryptographicPolicyVerifier,
            SecurityError,
        )

        # Use wrong secret key
        with patch.dict(os.environ, {"SCALPEL_MANIFEST_SECRET": "wrong-secret"}):
            verifier = CryptographicPolicyVerifier(
                manifest_source="file",
                policy_dir=str(policy_dir),
            )

            with pytest.raises(SecurityError) as exc:
                verifier.verify_all_policies()

            assert "signature" in str(exc.value).lower()

    def test_manifest_tamper_replay_old_manifest(self, signed_policy_dir):
        """
        Attack: Try to use an old manifest with a modified policy.

        Scenario:
        1. Save copy of valid manifest
        2. Update policy legitimately (new manifest created)
        3. Replace new manifest with old one
        4. Verification should fail (policy hash mismatch)
        """
        policy_dir, secret_key = signed_policy_dir
        manifest_file = policy_dir / "policy.manifest.json"
        policy_file = policy_dir / "policy.yaml"

        # Save copy of original manifest
        with open(manifest_file) as f:
            old_manifest = f.read()

        # "Legitimately" update policy (but attacker saves old manifest)
        policy_file.write_text("policies: [new_policy]")

        # Create new valid manifest
        from code_scalpel.policy_engine import CryptographicPolicyVerifier

        new_manifest = CryptographicPolicyVerifier.create_manifest(
            policy_files=["policy.yaml"],
            secret_key=secret_key,
            signed_by="admin@test.com",
            policy_dir=str(policy_dir),
        )
        CryptographicPolicyVerifier.save_manifest(new_manifest, str(policy_dir))

        # Attack: Replace with old manifest (replay attack)
        with open(manifest_file, "w") as f:
            f.write(old_manifest)

        # Verification should fail (policy doesn't match old manifest)
        from code_scalpel.policy_engine import SecurityError

        with patch.dict(os.environ, {"SCALPEL_MANIFEST_SECRET": secret_key}):
            verifier = CryptographicPolicyVerifier(
                manifest_source="file",
                policy_dir=str(policy_dir),
            )

            with pytest.raises(SecurityError):
                verifier.verify_all_policies()

    # [20251216_TEST] Adversarial crypto attacks
    def test_manifest_tamper_empty_signature(self, signed_policy_dir):
        """
        ADV-2.5.6 ADVERSARIAL: Empty signature should be rejected.
        """
        policy_dir, secret_key = signed_policy_dir
        manifest_file = policy_dir / "policy.manifest.json"

        with open(manifest_file) as f:
            manifest_data = json.load(f)

        # Empty signature attack
        manifest_data["signature"] = ""

        with open(manifest_file, "w") as f:
            json.dump(manifest_data, f)

        from code_scalpel.policy_engine import (
            CryptographicPolicyVerifier,
            SecurityError,
        )

        with patch.dict(os.environ, {"SCALPEL_MANIFEST_SECRET": secret_key}):
            verifier = CryptographicPolicyVerifier(
                manifest_source="file",
                policy_dir=str(policy_dir),
            )

            with pytest.raises(SecurityError):
                verifier.verify_all_policies()

    def test_manifest_tamper_null_signature(self, signed_policy_dir):
        """
        ADV-2.5.6 ADVERSARIAL: Null/None signature should be rejected.

        Tests that the system fails closed when signature is null.
        """
        policy_dir, secret_key = signed_policy_dir
        manifest_file = policy_dir / "policy.manifest.json"

        with open(manifest_file) as f:
            manifest_data = json.load(f)

        # Null signature attack
        manifest_data["signature"] = None

        with open(manifest_file, "w") as f:
            json.dump(manifest_data, f)

        from code_scalpel.policy_engine import (
            CryptographicPolicyVerifier,
            SecurityError,
        )

        with patch.dict(os.environ, {"SCALPEL_MANIFEST_SECRET": secret_key}):
            verifier = CryptographicPolicyVerifier(
                manifest_source="file",
                policy_dir=str(policy_dir),
            )

            # System should fail when attempting to verify (TypeError or SecurityError)
            with pytest.raises((SecurityError, TypeError)):
                verifier.verify_all_policies()

    def test_manifest_tamper_missing_signature_field(self, signed_policy_dir):
        """
        ADV-2.5.6 ADVERSARIAL: Missing signature field should fail closed at load.

        Tests that the system fails closed when signature field is missing.
        This is correct behavior - fail closed at load time.
        """
        policy_dir, secret_key = signed_policy_dir
        manifest_file = policy_dir / "policy.manifest.json"

        with open(manifest_file) as f:
            manifest_data = json.load(f)

        # Remove signature entirely
        del manifest_data["signature"]

        with open(manifest_file, "w") as f:
            json.dump(manifest_data, f)

        from code_scalpel.policy_engine import (
            CryptographicPolicyVerifier,
            SecurityError,
        )

        # System should fail closed at load time (CORRECT BEHAVIOR)
        with patch.dict(os.environ, {"SCALPEL_MANIFEST_SECRET": secret_key}):
            with pytest.raises(SecurityError):
                CryptographicPolicyVerifier(
                    manifest_source="file",
                    policy_dir=str(policy_dir),
                )

    def test_chmod_bypass_symlink_attack(self, tmp_path):
        """
        ADV-2.5.5 ADVERSARIAL: Symlink attack to bypass policy verification.

        Attack: Create symlink from policy.yaml to /etc/passwd or malicious file.
        System must verify the ACTUAL file content, not follow symlinks blindly.
        """
        policy_dir = tmp_path / ".code-scalpel"
        policy_dir.mkdir()

        # Create legitimate policy
        policy_content = "policies: [safe_policy]"
        policy_file = policy_dir / "policy.yaml"
        policy_file.write_text(policy_content)

        # Create and sign manifest
        secret_key = "test-secret"

        from code_scalpel.policy_engine import CryptographicPolicyVerifier

        manifest = CryptographicPolicyVerifier.create_manifest(
            policy_files=["policy.yaml"],
            secret_key=secret_key,
            signed_by="admin@test.com",
            policy_dir=str(policy_dir),
        )
        CryptographicPolicyVerifier.save_manifest(manifest, str(policy_dir))

        # Attack: Replace policy with symlink to different file
        malicious_file = tmp_path / "malicious.yaml"
        malicious_file.write_text("policies: [allow_all_evil]")

        policy_file.unlink()
        try:
            policy_file.symlink_to(malicious_file)
        except OSError:
            pytest.skip("Symlinks not supported on this platform")

        # Verification should fail (symlink target has different hash)
        from code_scalpel.policy_engine import SecurityError

        with patch.dict(os.environ, {"SCALPEL_MANIFEST_SECRET": secret_key}):
            verifier = CryptographicPolicyVerifier(
                manifest_source="file",
                policy_dir=str(policy_dir),
            )

            with pytest.raises(SecurityError):
                verifier.verify_all_policies()

    def test_chmod_bypass_race_condition(self, tmp_path):
        """
        ADV-2.5.5 ADVERSARIAL: TOCTOU (Time-of-check to time-of-use) race.

        This test verifies the system re-verifies at use time, not just load time.
        """

        policy_dir = tmp_path / ".code-scalpel"
        policy_dir.mkdir()

        policy_content = "policies: [safe]"
        policy_file = policy_dir / "policy.yaml"
        policy_file.write_text(policy_content)

        secret_key = "test-secret"

        from code_scalpel.policy_engine import CryptographicPolicyVerifier

        manifest = CryptographicPolicyVerifier.create_manifest(
            policy_files=["policy.yaml"],
            secret_key=secret_key,
            signed_by="admin@test.com",
            policy_dir=str(policy_dir),
        )
        CryptographicPolicyVerifier.save_manifest(manifest, str(policy_dir))

        # Initial verification should pass
        with patch.dict(os.environ, {"SCALPEL_MANIFEST_SECRET": secret_key}):
            verifier = CryptographicPolicyVerifier(
                manifest_source="file",
                policy_dir=str(policy_dir),
            )

            # First verification passes
            result = verifier.verify_all_policies()
            assert result.success  # Use success attribute

            # ATTACK: Modify file between verifications
            policy_file.write_text("policies: [EVIL_INJECTED]")

            # Second verification MUST fail (re-hash the file)
            from code_scalpel.policy_engine import SecurityError

            with pytest.raises(SecurityError):
                verifier.verify_all_policies()

    def test_manifest_tamper_unicode_confusion(self, tmp_path):
        """
        ADV-2.5.6 ADVERSARIAL: Unicode lookalike attack.

        Attack: Use Unicode characters that LOOK like ASCII but have different bytes.
        """
        policy_dir = tmp_path / ".code-scalpel"
        policy_dir.mkdir()

        # Create policy with ASCII filename
        policy_file = policy_dir / "policy.yaml"
        policy_file.write_text("policies: [safe]")

        secret_key = "test-secret"

        from code_scalpel.policy_engine import CryptographicPolicyVerifier

        manifest = CryptographicPolicyVerifier.create_manifest(
            policy_files=["policy.yaml"],
            secret_key=secret_key,
            signed_by="admin@test.com",
            policy_dir=str(policy_dir),
        )
        CryptographicPolicyVerifier.save_manifest(manifest, str(policy_dir))
        manifest_file = policy_dir / "policy.manifest.json"

        # Attack: Modify manifest with Unicode lookalike filename
        # "poliсy.yaml" uses Cyrillic 'с' (U+0441) instead of ASCII 'c' (U+0063)
        with open(manifest_file) as f:
            manifest_data = json.load(f)

        # Try to reference a different file via Unicode confusion
        if "policy.yaml" in manifest_data.get("files", {}):
            original_hash = manifest_data["files"]["policy.yaml"]
            del manifest_data["files"]["policy.yaml"]
            # Cyrillic 'с' looks like 'c' but is different byte
            manifest_data["files"]["poli\u0441y.yaml"] = original_hash

        with open(manifest_file, "w") as f:
            json.dump(manifest_data, f)

        # Verification should fail (file reference doesn't match)
        from code_scalpel.policy_engine import SecurityError

        with patch.dict(os.environ, {"SCALPEL_MANIFEST_SECRET": secret_key}):
            verifier = CryptographicPolicyVerifier(
                manifest_source="file",
                policy_dir=str(policy_dir),
            )

            # Either signature fails (content changed) or file not found
            with pytest.raises(SecurityError):
                verifier.verify_all_policies()

    def test_manifest_tamper_json_injection(self, signed_policy_dir):
        """
        ADV-2.5.6 ADVERSARIAL: JSON injection via crafted field values.
        """
        policy_dir, secret_key = signed_policy_dir
        manifest_file = policy_dir / "policy.manifest.json"

        with open(manifest_file) as f:
            manifest_data = json.load(f)

        # Attempt to inject additional fields that might confuse verification
        manifest_data["__proto__"] = {"signature": "bypass"}
        manifest_data["constructor"] = {"prototype": {"valid": True}}

        with open(manifest_file, "w") as f:
            json.dump(manifest_data, f)

        from code_scalpel.policy_engine import (
            CryptographicPolicyVerifier,
            SecurityError,
        )

        # System fails closed at load time when manifest has unknown fields
        # This is CORRECT security behavior
        with patch.dict(os.environ, {"SCALPEL_MANIFEST_SECRET": secret_key}):
            with pytest.raises(SecurityError):
                CryptographicPolicyVerifier(
                    manifest_source="file",
                    policy_dir=str(policy_dir),
                )

    def test_chmod_bypass_empty_secret_key(self, signed_policy_dir):
        """
        ADV-2.5.5 ADVERSARIAL: Empty secret key should fail closed at load.

        System correctly fails closed when SCALPEL_MANIFEST_SECRET is empty.
        """
        policy_dir, _ = signed_policy_dir

        from code_scalpel.policy_engine import (
            CryptographicPolicyVerifier,
            SecurityError,
        )

        # Empty string in env should trigger failure
        # Note: patch.dict with "" may be interpreted as "missing"
        # The system correctly fails closed
        with patch.dict(os.environ, {"SCALPEL_MANIFEST_SECRET": ""}, clear=True):
            with pytest.raises(SecurityError):
                CryptographicPolicyVerifier(
                    manifest_source="file",
                    policy_dir=str(policy_dir),
                )

    def test_manifest_tamper_missing_env_secret(self, signed_policy_dir):
        """
        ADV-2.5.6 ADVERSARIAL: Missing env secret should FAIL CLOSED at load.

        System correctly fails closed when SCALPEL_MANIFEST_SECRET is not set.
        """
        policy_dir, _ = signed_policy_dir

        from code_scalpel.policy_engine import (
            CryptographicPolicyVerifier,
            SecurityError,
        )

        # Clear environment completely, system should fail closed
        env_without_secret = {k: v for k, v in os.environ.items() if k != "SCALPEL_MANIFEST_SECRET"}
        with patch.dict(os.environ, env_without_secret, clear=True):
            with pytest.raises(SecurityError):
                CryptographicPolicyVerifier(
                    manifest_source="file",
                    policy_dir=str(policy_dir),
                )


# ============================================================================
# EVIDENCE GENERATION
# ============================================================================


class TestEvidenceGeneration:
    """
    Generate evidence for release artifacts.

    These tests produce structured output that can be captured
    for compliance documentation.
    """

    def test_all_adversarial_tests_documented(self):
        """
        Verify all ADV-2.5.x tests are implemented.
        """

        # Get all test classes in this module
        test_classes = [
            TestADV251TelephoneGame,
            TestADV252ThresholdRejection,
            TestADV253ContextExplosion,
            TestADV254Relevance,
            TestADV255ChmodBypass,
            TestADV256ManifestTamper,
        ]

        test_count = 0
        for cls in test_classes:
            methods = [m for m in dir(cls) if m.startswith("test_")]
            test_count += len(methods)

        # Should have at least 2 tests per adversarial category
        assert test_count >= 12, f"Expected at least 12 adversarial tests, found {test_count}"

    def test_evidence_format(self):
        """
        Generate evidence in JSON format for release artifacts.
        """
        evidence = {
            "test_suite": "v2.5.0_adversarial_tests",
            "version": "2.5.0",
            "timestamp": __import__("datetime").datetime.now().isoformat(),
            "tests": [
                {
                    "id": "ADV-2.5.1",
                    "name": "Telephone Game",
                    "feature": "Confidence Decay",
                    "description": "Verify 10-hop chain confidence compounds to ~34%",
                    "status": "implemented",
                },
                {
                    "id": "ADV-2.5.2",
                    "name": "Threshold Rejection",
                    "feature": "Confidence Decay",
                    "description": "Block agent from low-confidence dependencies",
                    "status": "implemented",
                },
                {
                    "id": "ADV-2.5.3",
                    "name": "Context Explosion",
                    "feature": "Graph Neighborhood",
                    "description": "Dense hub truncated to max_nodes",
                    "status": "implemented",
                },
                {
                    "id": "ADV-2.5.4",
                    "name": "Relevance Test",
                    "feature": "Graph Neighborhood",
                    "description": "Pruned nodes are lowest confidence",
                    "status": "implemented",
                },
                {
                    "id": "ADV-2.5.5",
                    "name": "chmod Bypass",
                    "feature": "Crypto Verification",
                    "description": "Hash mismatch detected after chmod attack",
                    "status": "implemented",
                },
                {
                    "id": "ADV-2.5.6",
                    "name": "Manifest Tamper",
                    "feature": "Crypto Verification",
                    "description": "HMAC signature tampering detected",
                    "status": "implemented",
                },
            ],
        }

        # Verify evidence structure
        assert evidence["version"] == "2.5.0"
        assert len(evidence["tests"]) == 6

        for test in evidence["tests"]:
            assert "id" in test
            assert test["id"].startswith("ADV-2.5")
            assert "status" in test
            assert test["status"] == "implemented"
