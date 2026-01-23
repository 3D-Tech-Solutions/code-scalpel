"""
Tests for universal graph structure.

[20251216_FEATURE] v2.1.0 - Test universal graph with nodes and edges
"""

import json

from code_scalpel.graph_engine.confidence import EdgeType
from code_scalpel.graph_engine.graph import (
    GraphBuilder,
    GraphEdge,
    GraphNode,
    UniversalGraph,
)
from code_scalpel.graph_engine.node_id import (  # [20240613_REFACTOR] Remove unused imports UniversalNodeID, NodeType per CodeQL warning
    create_node_id,
)


class TestGraphNode:
    """Tests for GraphNode class."""

    def test_create_node(self):
        """Test creating a graph node."""
        node_id = create_node_id("python", "app.handlers", "class", "Handler")
        node = GraphNode(id=node_id)

        assert node.id == node_id
        assert node.metadata == {}

    def test_create_node_with_metadata(self):
        """Test creating a node with metadata."""
        node_id = create_node_id("java", "com.example", "endpoint", "getUser")
        metadata = {"route": "/api/users", "method": "GET"}
        node = GraphNode(id=node_id, metadata=metadata)

        assert node.metadata["route"] == "/api/users"
        assert node.metadata["method"] == "GET"

    def test_node_to_dict(self):
        """Test converting node to dictionary."""
        node_id = create_node_id("python", "app.handlers", "class", "Handler", line=10)
        metadata = {"complexity": 5}
        node = GraphNode(id=node_id, metadata=metadata)

        d = node.to_dict()
        assert d["language"] == "python"
        assert d["module"] == "app.handlers"
        assert d["type"] == "class"
        assert d["name"] == "Handler"
        assert d["line"] == 10
        assert d["complexity"] == 5

    def test_node_from_dict(self):
        """Test creating node from dictionary."""
        data = {
            "id": "python::app.handlers::class::Handler",
            "language": "python",
            "module": "app.handlers",
            "type": "class",
            "name": "Handler",
            "route": "/api/handler",
        }

        node = GraphNode.from_dict(data)
        assert node.id.language == "python"
        assert node.metadata["route"] == "/api/handler"


class TestGraphEdge:
    """Tests for GraphEdge class."""

    def test_create_edge(self):
        """Test creating a graph edge."""
        edge = GraphEdge(
            from_id="python::app.handlers::class::Handler",
            to_id="python::app.models::class::User",
            edge_type=EdgeType.IMPORT_STATEMENT,
            confidence=1.0,
            evidence="Direct import statement",
        )

        assert edge.from_id == "python::app.handlers::class::Handler"
        assert edge.to_id == "python::app.models::class::User"
        assert edge.edge_type == EdgeType.IMPORT_STATEMENT
        assert edge.confidence == 1.0
        assert edge.evidence == "Direct import statement"

    def test_edge_to_dict(self):
        """Test converting edge to dictionary."""
        edge = GraphEdge(
            from_id="python::app::function::main",
            to_id="python::app::function::helper",
            edge_type=EdgeType.DIRECT_CALL,
            confidence=0.95,
            evidence="Direct function call",
            metadata={"line": 42},
        )

        d = edge.to_dict()
        assert d["from"] == "python::app::function::main"
        assert d["to"] == "python::app::function::helper"
        assert d["type"] == "direct_call"
        assert d["confidence"] == 0.95
        assert d["evidence"] == "Direct function call"
        assert d["line"] == 42

    def test_edge_from_dict(self):
        """Test creating edge from dictionary."""
        data = {
            "from": "typescript::client::function::fetchUsers",
            "to": "java::UserController:getUser",
            "type": "http_call",
            "confidence": 0.9,
            "evidence": "Route match: /api/users",
            "method": "GET",
        }

        edge = GraphEdge.from_dict(data)
        assert edge.from_id == "typescript::client::function::fetchUsers"
        assert edge.to_id == "java::UserController:getUser"
        assert edge.edge_type == EdgeType.HTTP_CALL
        assert edge.confidence == 0.9
        assert edge.metadata["method"] == "GET"


class TestUniversalGraph:
    """Tests for UniversalGraph class."""

    def test_create_empty_graph(self):
        """Test creating an empty graph."""
        graph = UniversalGraph()

        assert len(graph.nodes) == 0
        assert len(graph.edges) == 0
        assert graph.metadata == {}

    def test_add_node(self):
        """Test adding a node to the graph."""
        graph = UniversalGraph()
        node_id = create_node_id("python", "app", "function", "main")
        node = GraphNode(id=node_id)

        graph.add_node(node)
        assert len(graph.nodes) == 1
        assert graph.nodes[0] == node

    def test_add_duplicate_node(self):
        """Test adding duplicate node (should not duplicate)."""
        graph = UniversalGraph()
        node_id = create_node_id("python", "app", "function", "main")
        node1 = GraphNode(id=node_id)
        node2 = GraphNode(id=node_id)

        graph.add_node(node1)
        graph.add_node(node2)

        # Should only have one node
        assert len(graph.nodes) == 1

    def test_add_edge(self):
        """Test adding an edge to the graph."""
        graph = UniversalGraph()
        edge = GraphEdge(
            from_id="python::app::function::main",
            to_id="python::app::function::helper",
            edge_type=EdgeType.DIRECT_CALL,
            confidence=0.95,
            evidence="Direct call",
        )

        graph.add_edge(edge)
        assert len(graph.edges) == 1
        assert graph.edges[0] == edge

    def test_get_node(self):
        """Test getting a node by ID."""
        graph = UniversalGraph()
        node_id = create_node_id("python", "app", "function", "main")
        node = GraphNode(id=node_id)
        graph.add_node(node)

        retrieved = graph.get_node("python::app::function::main")
        assert retrieved == node

    def test_get_node_not_found(self):
        """Test getting a non-existent node."""
        graph = UniversalGraph()
        retrieved = graph.get_node("python::app::function::nonexistent")
        assert retrieved is None

    def test_get_edges_from(self):
        """Test getting edges from a node."""
        graph = UniversalGraph()

        edge1 = GraphEdge(
            from_id="python::app::function::main",
            to_id="python::app::function::helper1",
            edge_type=EdgeType.DIRECT_CALL,
            confidence=0.95,
            evidence="Call 1",
        )
        edge2 = GraphEdge(
            from_id="python::app::function::main",
            to_id="python::app::function::helper2",
            edge_type=EdgeType.DIRECT_CALL,
            confidence=0.95,
            evidence="Call 2",
        )
        edge3 = GraphEdge(
            from_id="python::app::function::other",
            to_id="python::app::function::helper1",
            edge_type=EdgeType.DIRECT_CALL,
            confidence=0.95,
            evidence="Call 3",
        )

        graph.add_edge(edge1)
        graph.add_edge(edge2)
        graph.add_edge(edge3)

        edges = graph.get_edges_from("python::app::function::main")
        assert len(edges) == 2
        assert edge1 in edges
        assert edge2 in edges

    def test_get_edges_to(self):
        """Test getting edges to a node."""
        graph = UniversalGraph()

        edge1 = GraphEdge(
            from_id="python::app::function::main",
            to_id="python::app::function::helper",
            edge_type=EdgeType.DIRECT_CALL,
            confidence=0.95,
            evidence="Call 1",
        )
        edge2 = GraphEdge(
            from_id="python::app::function::other",
            to_id="python::app::function::helper",
            edge_type=EdgeType.DIRECT_CALL,
            confidence=0.95,
            evidence="Call 2",
        )

        graph.add_edge(edge1)
        graph.add_edge(edge2)

        edges = graph.get_edges_to("python::app::function::helper")
        assert len(edges) == 2

    def test_get_dependencies(self):
        """Test getting dependencies with confidence filtering."""
        graph = UniversalGraph()

        # High confidence edge
        edge1 = GraphEdge(
            from_id="python::app::function::main",
            to_id="python::app::function::helper1",
            edge_type=EdgeType.IMPORT_STATEMENT,
            confidence=1.0,
            evidence="Import",
        )

        # Low confidence edge
        edge2 = GraphEdge(
            from_id="python::app::function::main",
            to_id="python::app::function::helper2",
            edge_type=EdgeType.DYNAMIC_ROUTE,
            confidence=0.5,
            evidence="Dynamic",
        )

        graph.add_edge(edge1)
        graph.add_edge(edge2)

        deps = graph.get_dependencies("python::app::function::main", min_confidence=0.8)

        assert len(deps["definite"]) == 1
        assert len(deps["uncertain"]) == 1
        assert deps["requires_human_approval"] is True

    def test_to_dict(self):
        """Test converting graph to dictionary."""
        graph = UniversalGraph()

        node_id = create_node_id("python", "app", "function", "main")
        node = GraphNode(id=node_id)
        graph.add_node(node)

        edge = GraphEdge(
            from_id="python::app::function::main",
            to_id="python::app::function::helper",
            edge_type=EdgeType.DIRECT_CALL,
            confidence=0.95,
            evidence="Direct call",
        )
        graph.add_edge(edge)

        d = graph.to_dict()
        assert "graph" in d
        assert "nodes" in d["graph"]
        assert "edges" in d["graph"]
        assert len(d["graph"]["nodes"]) == 1
        assert len(d["graph"]["edges"]) == 1

    def test_to_json(self):
        """Test converting graph to JSON string."""
        graph = UniversalGraph()

        node_id = create_node_id("python", "app", "function", "main")
        node = GraphNode(id=node_id)
        graph.add_node(node)

        json_str = graph.to_json()
        assert isinstance(json_str, str)

        # Should be valid JSON
        parsed = json.loads(json_str)
        assert "graph" in parsed

    def test_from_dict(self):
        """Test creating graph from dictionary."""
        data = {
            "graph": {
                "nodes": [
                    {
                        "id": "python::app::function::main",
                        "language": "python",
                        "module": "app",
                        "type": "function",
                        "name": "main",
                    }
                ],
                "edges": [
                    {
                        "from": "python::app::function::main",
                        "to": "python::app::function::helper",
                        "type": "direct_call",
                        "confidence": 0.95,
                        "evidence": "Direct call",
                    }
                ],
            },
            "metadata": {"project": "test"},
        }

        graph = UniversalGraph.from_dict(data)
        assert len(graph.nodes) == 1
        assert len(graph.edges) == 1
        assert graph.metadata["project"] == "test"

    def test_from_json(self):
        """Test creating graph from JSON string."""
        json_str = """
        {
            "graph": {
                "nodes": [
                    {
                        "id": "python::app::function::main",
                        "language": "python",
                        "module": "app",
                        "type": "function",
                        "name": "main"
                    }
                ],
                "edges": []
            },
            "metadata": {}
        }
        """

        graph = UniversalGraph.from_json(json_str)
        assert len(graph.nodes) == 1


class TestGraphBuilder:
    """Tests for GraphBuilder class."""

    def test_create_builder(self):
        """Test creating a graph builder."""
        builder = GraphBuilder()

        assert builder.graph is not None
        assert len(builder.graph.nodes) == 0
        assert len(builder.graph.edges) == 0

    def test_add_node(self):
        """Test adding a node via builder."""
        builder = GraphBuilder()

        node_id = create_node_id("python", "app", "function", "main")
        node = builder.add_node(node_id, metadata={"complexity": 5})

        assert len(builder.graph.nodes) == 1
        assert node.metadata["complexity"] == 5

    def test_add_duplicate_node_via_builder(self):
        """Test adding duplicate node via builder."""
        builder = GraphBuilder()

        node_id = create_node_id("python", "app", "function", "main")
        node1 = builder.add_node(node_id)
        node2 = builder.add_node(node_id)

        # Should return same node
        assert node1 == node2
        assert len(builder.graph.nodes) == 1

    def test_add_edge(self):
        """Test adding an edge via builder."""
        builder = GraphBuilder()

        edge = builder.add_edge(
            from_id="python::app::function::main",
            to_id="python::app::function::helper",
            edge_type=EdgeType.DIRECT_CALL,
            context={},
        )

        assert len(builder.graph.edges) == 1
        assert edge.confidence > 0.0

    def test_add_edge_with_context(self):
        """Test adding edge with context for confidence scoring."""
        builder = GraphBuilder()

        edge = builder.add_edge(
            from_id="typescript::client::function::fetchUsers",
            to_id="java::UserController:getUser",
            edge_type=EdgeType.HTTP_CALL,
            context={"route_match": "exact"},
        )

        # Should have high confidence with exact route match
        assert edge.confidence >= 0.9

    def test_build(self):
        """Test building the final graph."""
        builder = GraphBuilder()

        node_id = create_node_id("python", "app", "function", "main")
        builder.add_node(node_id)

        graph = builder.build()
        assert isinstance(graph, UniversalGraph)
        assert len(graph.nodes) == 1

    def test_reset(self):
        """Test resetting the builder."""
        builder = GraphBuilder()

        node_id = create_node_id("python", "app", "function", "main")
        builder.add_node(node_id)

        builder.reset()
        assert len(builder.graph.nodes) == 0
        assert len(builder.graph.edges) == 0
