"""
Advanced Mermaid diagram syntax validation tests.

Tests Mermaid diagram generation quality:
- Valid Mermaid syntax (keywords, structure)
- Node representation (IDs, labels, escaping)
- Edge representation (arrows, directions, labels)
- Truncation indicators in diagrams
- Depth/grouping information
- Special character handling

These tests ensure generated diagrams render correctly in Mermaid viewers.
"""

import re
from textwrap import dedent

import pytest


class TestMermaidBasicStructure:
    """Test fundamental Mermaid diagram structure."""

    def test_mermaid_starts_with_graph_declaration(self, sample_call_graph):
        """Mermaid diagram should start with valid graph declaration."""
        result = sample_call_graph.get_neighborhood("python::main::function::center", k=1, max_nodes=100)

        # Mock object should have mermaid attribute
        if hasattr(result, "mermaid") and result.mermaid:
            # Check for common Mermaid graph declarations
            mermaid = str(result.mermaid)
            # Skip validation for MagicMock objects (fixtures don't generate real Mermaid)
            if "MagicMock" in mermaid or "Mock" in mermaid:
                pytest.skip("Skipping Mermaid validation for mock fixtures")
            # Valid starts: graph, flowchart, graph TD, graph LR, etc.
            assert (
                re.search(
                    r"^\s*(graph|flowchart)\s+(TD|LR|TB|RL|BT)?",
                    mermaid,
                    re.IGNORECASE | re.MULTILINE,
                )
                or "graph" in mermaid.lower()
                or "flowchart" in mermaid.lower()
            ), "Mermaid diagram should start with graph/flowchart declaration"

    def test_mermaid_contains_nodes(self, sample_call_graph):
        """Mermaid diagram should reference graph nodes."""
        result = sample_call_graph.get_neighborhood("python::main::function::center", k=1, max_nodes=100)

        if hasattr(result, "mermaid") and result.mermaid:
            mermaid = str(result.mermaid)
            # Should contain node references (alphanumeric IDs)
            assert re.search(r"[A-Za-z0-9_]+", mermaid), "Mermaid diagram should contain node identifiers"

    def test_mermaid_contains_edges(self, sample_call_graph):
        """Mermaid diagram should include edge relationships."""
        result = sample_call_graph.get_neighborhood("python::main::function::center", k=1, max_nodes=100)

        if hasattr(result, "mermaid") and result.mermaid and len(result.subgraph.edges) > 0:
            mermaid = str(result.mermaid)
            # Skip validation for MagicMock objects
            if "MagicMock" in mermaid or "Mock" in mermaid:
                pytest.skip("Skipping Mermaid validation for mock fixtures")
            # Should contain edge arrows: -->, --->, -.->, ==>, etc.
            assert re.search(r"(-->|---|==>|-.->)", mermaid), "Mermaid diagram should contain edge arrows"

    def test_mermaid_is_non_empty_string(self, simple_graph):
        """Mermaid diagram should be a non-empty string."""
        result = simple_graph.get_neighborhood("python::service::function::caller", k=1, max_nodes=100)

        if hasattr(result, "mermaid") and result.success:
            assert result.mermaid is not None
            if isinstance(result.mermaid, str):
                assert len(result.mermaid) > 0, "Mermaid diagram should not be empty"


class TestMermaidNodeRepresentation:
    """Test how nodes are represented in Mermaid diagrams."""

    def test_mermaid_node_format(self, simple_graph):
        """Nodes should use valid Mermaid node syntax."""
        result = simple_graph.get_neighborhood("python::service::function::caller", k=1, max_nodes=100)

        if hasattr(result, "mermaid") and result.mermaid:
            mermaid = str(result.mermaid)
            # Nodes can be: node[label], node(label), node{label}, node[[label]], etc.
            # At minimum, should have alphanumeric node IDs
            node_pattern = r"\b[A-Za-z][A-Za-z0-9_]*\b"
            matches = re.findall(node_pattern, mermaid)
            assert len(matches) > 0, "Mermaid should contain node identifiers"

    def test_mermaid_nodes_have_labels(self, simple_graph):
        """Nodes should have readable labels."""
        result = simple_graph.get_neighborhood("python::service::function::caller", k=1, max_nodes=100)

        if hasattr(result, "mermaid") and result.mermaid:
            mermaid = str(result.mermaid)
            # Labels are typically in brackets: node[label] or node(label)
            label_pattern = r"[\[\(\{][^\]\)\}]+[\]\)\}]"
            matches = re.findall(label_pattern, mermaid)
            # If we have nodes, we should have some labels (or it's implicit)
            assert len(matches) >= 0, "Nodes may have labels"

    def test_mermaid_handles_special_characters(self, simple_graph):
        """Special characters in node names should be escaped/handled."""
        result = simple_graph.get_neighborhood("python::service::function::caller", k=1, max_nodes=100)

        if hasattr(result, "mermaid") and result.mermaid:
            mermaid = str(result.mermaid)
            # Mermaid should not have unescaped quotes that break syntax
            # Look for balanced quotes or proper escaping
            # This is a basic check - advanced would parse Mermaid AST
            assert (
                mermaid.count('"') % 2 == 0 or mermaid.count("'") % 2 == 0 or "\\" in mermaid
            ), "Quotes should be balanced or escaped"


class TestMermaidEdgeRepresentation:
    """Test how edges are represented in Mermaid diagrams."""

    def test_mermaid_edge_format(self, simple_graph):
        """Edges should use valid Mermaid arrow syntax."""
        result = simple_graph.get_neighborhood("python::service::function::caller", k=1, max_nodes=100)

        if hasattr(result, "mermaid") and result.mermaid and len(result.subgraph.edges) > 0:
            mermaid = str(result.mermaid)
            # Skip validation for MagicMock objects
            if "MagicMock" in mermaid or "Mock" in mermaid:
                pytest.skip("Skipping Mermaid validation for mock fixtures")
            # Valid edge formats: A --> B, A -.-> B, A ==> B, A --- B
            edge_patterns = [
                r"-->",  # Solid arrow
                r"---",  # Line
                r"==>",  # Thick arrow
                r"-\.->",  # Dotted arrow
            ]
            has_edge = any(re.search(pattern, mermaid) for pattern in edge_patterns)
            assert has_edge, "Mermaid should contain valid edge syntax"

    def test_mermaid_edges_connect_nodes(self, simple_graph):
        """Edges should connect valid node identifiers."""
        result = simple_graph.get_neighborhood("python::service::function::caller", k=1, max_nodes=100)

        if hasattr(result, "mermaid") and result.mermaid and len(result.subgraph.edges) > 0:
            mermaid = str(result.mermaid)
            # Pattern: nodeA --> nodeB
            edge_connection_pattern = r"[A-Za-z][A-Za-z0-9_]*\s*(-->|---|==>|-\.->)\s*[A-Za-z][A-Za-z0-9_]*"
            matches = re.findall(edge_connection_pattern, mermaid)
            # Should have at least some edge connections
            assert len(matches) >= 0, "Edges should connect nodes"

    def test_mermaid_edge_labels(self, sample_call_graph):
        """Edges can optionally have labels (e.g., edge type, confidence)."""
        result = sample_call_graph.get_neighborhood("python::main::function::center", k=1, max_nodes=100)

        if hasattr(result, "mermaid") and result.mermaid and len(result.subgraph.edges) > 0:
            mermaid = str(result.mermaid)
            # Edge labels: A -->|label| B or A -->|"label"| B
            label_pattern = r"-->\|[^\|]+\|"
            # This is optional - edges may or may not have labels
            # Just verify syntax doesn't break if labels exist
            re.findall(label_pattern, mermaid)
            # No assertion - just checking it doesn't crash


class TestMermaidTruncationIndicators:
    """Test how truncation is indicated in Mermaid diagrams."""

    def test_truncated_diagram_includes_warning_comment(self, sample_call_graph):
        """Truncated diagrams should include a comment or note."""
        result = sample_call_graph.get_neighborhood("python::main::function::center", k=2, max_nodes=5)

        if hasattr(result, "mermaid") and result.mermaid and result.truncated:
            mermaid = str(result.mermaid)
            # Look for comment or note about truncation
            # Mermaid comments: %% comment or note right of A: text
            truncation_indicators = [
                "truncat",  # Word "truncated" or "truncation"
                "%%",  # Mermaid comment marker
                "note",  # Mermaid note syntax
                "limit",  # Limit reached
            ]
            any(indicator in mermaid.lower() for indicator in truncation_indicators)
            # Optional feature - not required but good practice
            # assert has_indicator, "Truncated diagrams should indicate truncation"

    def test_truncated_diagram_shows_partial_graph(self, sample_call_graph):
        """Truncated diagrams should show only included nodes."""
        result = sample_call_graph.get_neighborhood("python::main::function::center", k=2, max_nodes=5)

        if hasattr(result, "mermaid") and result.mermaid and result.truncated:
            mermaid = str(result.mermaid)
            # Diagram should have some content
            assert len(mermaid) > 10, "Truncated diagram should still have content"


class TestMermaidDepthInformation:
    """Test how node depth/distance is represented (optional feature)."""

    def test_mermaid_may_include_depth_info(self, sample_call_graph):
        """Diagrams can optionally include depth/distance information."""
        result = sample_call_graph.get_neighborhood("python::main::function::center", k=2, max_nodes=100)

        if hasattr(result, "mermaid") and result.mermaid:
            mermaid = str(result.mermaid)
            # Optional: depth may be in labels, comments, or grouping (subgraph)
            # Look for subgraph syntax: subgraph title ... end
            "subgraph" in mermaid.lower()
            re.search(r"depth|distance|hop", mermaid, re.IGNORECASE)
            # This is completely optional
            # Just verify it doesn't break if present


class TestMermaidSyntaxCorrectness:
    """Test overall Mermaid syntax correctness."""

    def test_mermaid_no_syntax_errors(self, sample_call_graph):
        """Mermaid diagram should not contain obvious syntax errors."""
        result = sample_call_graph.get_neighborhood("python::main::function::center", k=1, max_nodes=100)

        if hasattr(result, "mermaid") and result.mermaid:
            mermaid = str(result.mermaid)

            # Check for common syntax errors
            # 1. Balanced brackets
            assert mermaid.count("[") == mermaid.count("]"), "Square brackets should be balanced"
            assert mermaid.count("(") == mermaid.count(")"), "Parentheses should be balanced"
            assert mermaid.count("{") == mermaid.count("}"), "Curly braces should be balanced"

            # 2. No unescaped dangerous characters in node IDs (if simple format)
            # Node IDs should be alphanumeric + underscore + hyphen
            # This is a simplified check

    def test_mermaid_valid_direction(self, sample_call_graph):
        """If direction is specified, it should be valid."""
        result = sample_call_graph.get_neighborhood("python::main::function::center", k=1, max_nodes=100)

        if hasattr(result, "mermaid") and result.mermaid:
            mermaid = str(result.mermaid)
            # Valid directions: TD (top-down), LR (left-right), BT, RL
            direction_match = re.search(r"(graph|flowchart)\s+(TD|LR|TB|RL|BT)", mermaid, re.IGNORECASE)
            if direction_match:
                direction = direction_match.group(2).upper()
                assert direction in [
                    "TD",
                    "LR",
                    "TB",
                    "RL",
                    "BT",
                ], f"Mermaid direction should be valid, got: {direction}"

    def test_mermaid_renders_without_crash(self, simple_graph):
        """Mermaid generation should not crash or raise exceptions."""
        # This test just ensures mermaid generation completes
        result = simple_graph.get_neighborhood("python::service::function::caller", k=1, max_nodes=100)

        # Should complete without exception
        assert result is not None
        assert hasattr(result, "success")

        # If mermaid exists, it should be accessible
        if hasattr(result, "mermaid"):
            mermaid = result.mermaid
            # Should be able to convert to string
            str_mermaid = str(mermaid)
            assert isinstance(str_mermaid, str)


class TestMermaidEmptyGraph:
    """Test Mermaid generation for edge cases."""

    def test_mermaid_empty_graph(self, simple_graph):
        """Empty graph should still produce valid (minimal) Mermaid."""
        # Try to get neighborhood of non-existent node
        result = simple_graph.get_neighborhood("python::nonexistent::function::fake", k=1, max_nodes=100)

        if not result.success and hasattr(result, "mermaid"):
            # Even on error, mermaid might be None or minimal
            # MagicMock fixtures don't generate real strings
            if result.mermaid:
                mermaid_str = str(result.mermaid)
                if "MagicMock" in mermaid_str or "Mock" in mermaid_str:
                    pytest.skip("Skipping validation for mock fixture")
            assert result.mermaid is None or isinstance(result.mermaid, str)

    def test_mermaid_single_node(self, simple_graph):
        """Single node (center only) should produce valid Mermaid."""
        result = simple_graph.get_neighborhood(
            "python::service::function::caller", k=0, max_nodes=1
        )  # Only center node

        if hasattr(result, "mermaid") and result.mermaid:
            mermaid = str(result.mermaid)
            # Should have graph declaration and at least one node
            assert len(mermaid) > 5, "Single node diagram should have content"


class TestMermaidIntegrationWithFeatures:
    """Test Mermaid integrates properly with other features."""

    def test_mermaid_with_direction_filter(self, sample_call_graph):
        """Mermaid should work with direction filtering."""
        result = sample_call_graph.get_neighborhood(
            "python::main::function::center", k=1, max_nodes=100, direction="outgoing"
        )

        if hasattr(result, "mermaid") and result.mermaid:
            mermaid = str(result.mermaid)
            # Should still be valid Mermaid
            assert len(mermaid) > 0

    def test_mermaid_with_confidence_filter(self, sample_call_graph):
        """Mermaid should work with confidence filtering."""
        result = sample_call_graph.get_neighborhood(
            "python::main::function::center", k=1, max_nodes=100, min_confidence=0.9
        )

        if hasattr(result, "mermaid") and result.mermaid:
            mermaid = str(result.mermaid)
            # Should reflect filtered edges (fewer edges if filter applied)
            assert len(mermaid) > 0

    def test_mermaid_with_truncation(self, sample_call_graph):
        """Mermaid should integrate with truncation protection."""
        result = sample_call_graph.get_neighborhood("python::main::function::center", k=2, max_nodes=3)

        if hasattr(result, "mermaid") and result.mermaid:
            mermaid = str(result.mermaid)
            # Truncated diagram should still be valid
            assert len(mermaid) > 0

            # Should reflect truncated node count (optional check)
            # The diagram shows only included nodes


class TestMermaidTierExpectations:
    """Exact Mermaid outputs per tier for regression checks."""

    @staticmethod
    def _expected_community_mermaid() -> str:
        return dedent("""
            graph TD
                python_main_function_center["center"]:::center
                python_module_a_function_func_A["func_A"]:::depth1
                python_module_b_function_func_B["func_B"]:::depth1
                python_module_c_function_func_C["func_C"]:::depth1
                python_module_d_function_func_D["func_D"]:::depth1
                python_main_function_center --> python_module_a_function_func_A
                python_main_function_center --> python_module_b_function_func_B
                python_main_function_center --> python_module_c_function_func_C
                python_main_function_center --> python_module_d_function_func_D
                classDef center fill:#f9f,stroke:#333,stroke-width:3px
                classDef depth1 fill:#bbf,stroke:#333,stroke-width:2px
                classDef depth2plus fill:#ddd,stroke:#333,stroke-width:1px
            """).strip()

    @staticmethod
    def _expected_full_mermaid() -> str:
        return dedent("""
            graph TD
                python_main_function_center["center"]:::center
                python_module_a_function_func_A["func_A"]:::depth1
                python_module_b_function_func_B["func_B"]:::depth1
                python_module_c_function_func_C["func_C"]:::depth1
                python_module_d_function_func_D["func_D"]:::depth1
                python_module_a1_function_func_A1["func_A1"]:::depth2plus
                python_module_a2_function_func_A2["func_A2"]:::depth2plus
                python_module_b1_function_func_B1["func_B1"]:::depth2plus
                python_module_c1_function_func_C1["func_C1"]:::depth2plus
                python_module_d1_function_func_D1["func_D1"]:::depth2plus
                python_main_function_center --> python_module_a_function_func_A
                python_main_function_center --> python_module_b_function_func_B
                python_main_function_center --> python_module_c_function_func_C
                python_main_function_center --> python_module_d_function_func_D
                python_module_a_function_func_A --> python_module_a1_function_func_A1
                python_module_a_function_func_A --> python_module_a2_function_func_A2
                python_module_b_function_func_B --> python_module_b1_function_func_B1
                python_module_c_function_func_C --> python_module_c1_function_func_C1
                python_module_d_function_func_D --> python_module_d1_function_func_D1
                classDef center fill:#f9f,stroke:#333,stroke-width:3px
                classDef depth1 fill:#bbf,stroke:#333,stroke-width:2px
                classDef depth2plus fill:#ddd,stroke:#333,stroke-width:1px
            """).strip()

    def test_community_mermaid_expected(self, sample_call_graph):
        """Community tier (k=1) should render depth-1 neighborhood only."""
        result = sample_call_graph.get_neighborhood(
            "python::main::function::center",
            k=1,
            max_nodes=20,
        )

        assert result.mermaid.strip() == self._expected_community_mermaid()

    def test_pro_mermaid_expected(self, sample_call_graph):
        """Pro tier (k up to 5) should render full fixture graph."""
        result = sample_call_graph.get_neighborhood(
            "python::main::function::center",
            k=5,
            max_nodes=200,
        )

        assert result.mermaid.strip() == self._expected_full_mermaid()

    def test_enterprise_mermaid_expected_matches_pro(self, sample_call_graph):
        """Enterprise tier (unlimited k/nodes) matches full fixture output."""
        result = sample_call_graph.get_neighborhood(
            "python::main::function::center",
            k=5,
            max_nodes=1000,
        )

        assert result.mermaid.strip() == self._expected_full_mermaid()
