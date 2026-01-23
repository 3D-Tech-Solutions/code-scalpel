"""
Fixtures for get_graph_neighborhood tests.

Provides:
- Sample call graphs with known topology
- Tier configuration fixtures
- Project root fixtures
"""

from unittest.mock import MagicMock

import pytest

try:
    from code_scalpel.mcp.server import (
        NeighborhoodEdgeModel,
        NeighborhoodNodeModel,
    )

    MCP_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    # MCP server dependencies not installed - skip fixtures that need them
    MCP_AVAILABLE = False
    NeighborhoodNodeModel = None
    NeighborhoodEdgeModel = None

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def _generate_test_mermaid(
    node_ids: list[str],
    edges: list[tuple[str, str, float]],
    node_depths: dict[str, int],
    center_node_id: str,
) -> str:
    """Generate Mermaid diagram from fixture data.

    Args:
        node_ids: List of node ID strings
        edges: List of (from_id, to_id, confidence) tuples
        node_depths: Dict mapping node_id -> depth
        center_node_id: ID of center node

    Returns:
        Mermaid diagram string
    """
    # Convert to Pydantic models
    nodes = [NeighborhoodNodeModel(id=node_id, depth=node_depths.get(node_id, 0), metadata={}) for node_id in node_ids]
    edge_models = [NeighborhoodEdgeModel(from_id=f, to_id=t, edge_type="calls", confidence=c) for f, t, c in edges]

    # Generate Mermaid (same logic as server.py:15919-15952)
    lines = ["graph TD"]
    for node in nodes:
        safe_id = node.id.replace("::", "_").replace(".", "_").replace("-", "_")
        label = node.id.split("::")[-1] if "::" in node.id else node.id
        if node.depth == 0:
            lines.append(f'    {safe_id}["{label}"]:::center')
        elif node.depth == 1:
            lines.append(f'    {safe_id}["{label}"]:::depth1')
        else:
            lines.append(f'    {safe_id}["{label}"]:::depth2plus')
    for edge in edge_models:
        from_safe = edge.from_id.replace("::", "_").replace(".", "_").replace("-", "_")
        to_safe = edge.to_id.replace("::", "_").replace(".", "_").replace("-", "_")
        lines.append(f"    {from_safe} --> {to_safe}")
    lines.extend(
        [
            "    classDef center fill:#f9f,stroke:#333,stroke-width:3px",
            "    classDef depth1 fill:#bbf,stroke:#333,stroke-width:2px",
            "    classDef depth2plus fill:#ddd,stroke:#333,stroke-width:1px",
        ]
    )
    return "\n".join(lines)


# ============================================================================
# GRAPH FIXTURES - Sample graphs with known topology for testing
# ============================================================================


@pytest.fixture
def sample_call_graph():
    """
    Create a sample call graph with known topology for k-hop testing.

    Graph structure (call relationships):
    ```
    center
    ├─ func_A (depth 1)
    │  ├─ func_A1 (depth 2)
    │  └─ func_A2 (depth 2)
    ├─ func_B (depth 1)
    │  └─ func_B1 (depth 2)
    ├─ func_C (depth 1)
    │  └─ func_C1 (depth 2)
    └─ func_D (depth 1)
       └─ func_D1 (depth 2)
    ```

    All edges have confidence 0.9 by default.
    """
    mock_graph = MagicMock()

    # Nodes: center at depth 0, 4 at depth 1, 7 at depth 2
    nodes_by_depth = {
        0: ["python::main::function::center"],
        1: [
            "python::module_a::function::func_A",
            "python::module_b::function::func_B",
            "python::module_c::function::func_C",
            "python::module_d::function::func_D",
        ],
        2: [
            "python::module_a1::function::func_A1",
            "python::module_a2::function::func_A2",
            "python::module_b1::function::func_B1",
            "python::module_c1::function::func_C1",
            "python::module_d1::function::func_D1",
        ],
    }

    # Flatten for easy access
    all_nodes = []
    for nodes in nodes_by_depth.values():
        all_nodes.extend(nodes)

    # Define edges (source -> target with confidence)
    edges = [
        # Center -> depth 1
        ("python::main::function::center", "python::module_a::function::func_A", 0.95),
        ("python::main::function::center", "python::module_b::function::func_B", 0.90),
        ("python::main::function::center", "python::module_c::function::func_C", 0.88),
        ("python::main::function::center", "python::module_d::function::func_D", 0.92),
        # Depth 1 -> depth 2
        (
            "python::module_a::function::func_A",
            "python::module_a1::function::func_A1",
            0.93,
        ),
        (
            "python::module_a::function::func_A",
            "python::module_a2::function::func_A2",
            0.91,
        ),
        (
            "python::module_b::function::func_B",
            "python::module_b1::function::func_B1",
            0.89,
        ),
        (
            "python::module_c::function::func_C",
            "python::module_c1::function::func_C1",
            0.87,
        ),
        (
            "python::module_d::function::func_D",
            "python::module_d1::function::func_D1",
            0.94,
        ),
    ]

    # Setup mock methods
    mock_graph.nodes = all_nodes
    mock_graph.edges = edges
    mock_graph.nodes_by_depth = nodes_by_depth

    def mock_get_neighborhood(center_id, k=1, max_nodes=100, direction="both", min_confidence=0.0):
        """Simulate neighborhood extraction with depth limiting."""
        result = MagicMock()
        result.success = True

        # Simulate depth-based filtering
        included_nodes = [center_id]  # Always include center

        # Add nodes up to depth k
        for depth in range(1, k + 1):
            if depth in nodes_by_depth:
                included_nodes.extend(nodes_by_depth[depth])

        # Filter by confidence if specified
        included_edges = [
            (src, dst, conf)
            for src, dst, conf in edges
            if src in included_nodes and dst in included_nodes and conf >= min_confidence
        ]

        # Handle truncation
        if len(included_nodes) > max_nodes:
            included_nodes = included_nodes[:max_nodes]
            result.truncated = True
            result.truncation_warning = f"Graph truncated from {len(all_nodes)} to {max_nodes} nodes"
        else:
            result.truncated = False
            result.truncation_warning = None

        result.subgraph = MagicMock()
        result.subgraph.nodes = included_nodes
        result.subgraph.edges = included_edges
        result.node_depths = {
            node: depth for depth, nodes in nodes_by_depth.items() for node in nodes if node in included_nodes
        }
        result.node_depths[center_id] = 0

        # Generate Mermaid diagram
        result.mermaid = _generate_test_mermaid(
            node_ids=included_nodes,
            edges=included_edges,
            node_depths=result.node_depths,
            center_node_id=center_id,
        )

        return result

    mock_graph.get_neighborhood = mock_get_neighborhood
    return mock_graph


@pytest.fixture
def simple_graph():
    """Minimal graph for basic tests (3 nodes, 2 edges)."""
    mock_graph = MagicMock()

    nodes = [
        "python::service::function::caller",
        "python::service::function::target",
        "python::db::function::query",
    ]

    edges = [
        (
            "python::service::function::caller",
            "python::service::function::target",
            0.95,
        ),
        ("python::service::function::target", "python::db::function::query", 0.90),
    ]

    mock_graph.nodes = nodes
    mock_graph.edges = edges

    def mock_get_neighborhood(center_id, k=1, max_nodes=100, direction="both", min_confidence=0.0):
        result = MagicMock()
        result.success = center_id in nodes
        result.subgraph = MagicMock()

        if result.success:
            if center_id == "python::service::function::caller" and k >= 1:
                result.subgraph.nodes = nodes[:2]
                result.subgraph.edges = [edges[0]]
            elif center_id == "python::service::function::target" and k >= 1:
                result.subgraph.nodes = nodes[1:]
                result.subgraph.edges = [edges[1]]
            else:
                result.subgraph.nodes = [center_id]
                result.subgraph.edges = []
            result.truncated = False

            # Build node depths dict (center=0, all neighbors=1)
            node_depths_dict = {node: 0 if node == center_id else 1 for node in result.subgraph.nodes}
            result.node_depths = node_depths_dict

            # Generate Mermaid diagram
            result.mermaid = _generate_test_mermaid(
                node_ids=result.subgraph.nodes,
                edges=result.subgraph.edges,
                node_depths=node_depths_dict,
                center_node_id=center_id,
            )
        else:
            result.error = f"Node {center_id} not found"
            result.mermaid = None
            result.node_depths = {}

        return result

    mock_graph.get_neighborhood = mock_get_neighborhood
    return mock_graph


# ============================================================================
# TIER CONFIGURATION FIXTURES
# ============================================================================


@pytest.fixture
def community_tier_config():
    """Community tier configuration (k=1 max, nodes=20 max)."""
    return {
        "tier": "community",
        "capabilities": ["basic_neighborhood"],
        "limits": {
            "max_k": 1,
            "max_nodes": 20,
        },
    }


@pytest.fixture
def pro_tier_config():
    """Pro tier configuration (k=5 max, nodes=200 max)."""
    return {
        "tier": "pro",
        "capabilities": [
            "basic_neighborhood",
            "advanced_neighborhood",
            "semantic_neighbors",
            "logical_relationship_detection",
        ],
        "limits": {
            "max_k": 5,
            "max_nodes": 200,
        },
    }


@pytest.fixture
def enterprise_tier_config():
    """Enterprise tier configuration (unlimited k and nodes)."""
    return {
        "tier": "enterprise",
        "capabilities": [
            "basic_neighborhood",
            "advanced_neighborhood",
            "semantic_neighbors",
            "logical_relationship_detection",
            "graph_query_language",
            "custom_traversal_rules",
            "path_constraint_queries",
        ],
        "limits": {
            "max_k": None,  # Unlimited
            "max_nodes": None,  # Unlimited
        },
    }


@pytest.fixture
def invalid_tier_config():
    """Invalid/expired license (should fallback to Community)."""
    return {
        "tier": "invalid",
        "capabilities": [],
        "limits": {},
    }


# ============================================================================
# PROJECT FIXTURES
# ============================================================================


@pytest.fixture
def temp_project_dir(tmp_path):
    """Create a temporary project directory with sample Python files."""
    project_dir = tmp_path / "sample_project"
    project_dir.mkdir()

    # Create a simple package structure
    src_dir = project_dir / "src"
    src_dir.mkdir()

    # Create a main module
    main_py = src_dir / "main.py"
    main_py.write_text("""
def center_function():
    return func_a()

def func_a():
    return func_a1()

def func_a1():
    return "result"
""")

    # Create dependent modules
    utils_py = src_dir / "utils.py"
    utils_py.write_text("""
def func_b():
    return func_b1()

def func_b1():
    return "utility"
""")

    return project_dir


# ============================================================================
# MOCKING FIXTURES FOR TIER ENFORCEMENT
# ============================================================================


@pytest.fixture
def mock_tier_community(monkeypatch):
    """Mock the tier system to return Community tier."""
    mock_get_tier = MagicMock(return_value="community")
    monkeypatch.setattr(
        "code_scalpel.mcp.server._get_current_tier",
        mock_get_tier,
    )
    return mock_get_tier


@pytest.fixture
def mock_tier_pro(monkeypatch):
    """Mock the tier system to return Pro tier."""
    mock_get_tier = MagicMock(return_value="pro")
    monkeypatch.setattr(
        "code_scalpel.mcp.server._get_current_tier",
        mock_get_tier,
    )
    return mock_get_tier


@pytest.fixture
def mock_tier_enterprise(monkeypatch):
    """Mock the tier system to return Enterprise tier."""
    mock_get_tier = MagicMock(return_value="enterprise")
    monkeypatch.setattr(
        "code_scalpel.mcp.server._get_current_tier",
        mock_get_tier,
    )
    return mock_get_tier


@pytest.fixture
def mock_capabilities(monkeypatch):
    """Mock get_tool_capabilities to return tier-specific capabilities."""

    def mock_get_capabilities(tool_name, tier):
        capabilities_map = {
            "community": {
                "capabilities": ["basic_neighborhood"],
                "limits": {"max_k": 1, "max_nodes": 20},
            },
            "pro": {
                "capabilities": [
                    "basic_neighborhood",
                    "advanced_neighborhood",
                    "semantic_neighbors",
                    "logical_relationship_detection",
                ],
                "limits": {"max_k": 5, "max_nodes": 200},
            },
            "enterprise": {
                "capabilities": [
                    "basic_neighborhood",
                    "advanced_neighborhood",
                    "semantic_neighbors",
                    "logical_relationship_detection",
                    "graph_query_language",
                    "custom_traversal_rules",
                    "path_constraint_queries",
                ],
                "limits": {"max_k": None, "max_nodes": None},
            },
        }
        return capabilities_map.get(tier, {})

    monkeypatch.setattr(
        "code_scalpel.mcp.server.get_tool_capabilities",
        mock_get_capabilities,
    )
    return mock_get_capabilities
