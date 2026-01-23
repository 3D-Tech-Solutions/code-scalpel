"""
Tests for Contract Breach Detector.

[20251216_TEST] Tests for Feature 11: Contract Breach Detector
"""

from code_scalpel.polyglot.contract_breach_detector import (
    BreachType,
    ContractBreachDetector,
    Edge,
    Node,
    Severity,
    UnifiedGraph,
    detect_breaches,
)


class TestUnifiedGraph:
    """Test the unified graph structure."""

    def test_create_graph(self):
        """Test creating a unified graph."""
        graph = UnifiedGraph()

        assert graph is not None
        assert len(graph.nodes) == 0
        assert len(graph.edges) == 0

    def test_add_node(self):
        """Test adding nodes to the graph."""
        graph = UnifiedGraph()

        node = Node(
            node_id="java::User",
            node_type="class",
            language="java",
            fields={"id", "name", "email"},
        )

        graph.add_node(node)

        assert len(graph.nodes) == 1
        assert "java::User" in graph.nodes

    def test_add_edge(self):
        """Test adding edges to the graph."""
        graph = UnifiedGraph()

        edge = Edge(
            from_id="typescript::fetchUser",
            to_id="java::UserController:getUser",
            edge_type="http_call",
            confidence=0.95,
        )

        graph.add_edge(edge)

        assert len(graph.edges) == 1

    def test_get_edges_to(self):
        """Test getting edges pointing to a node."""
        graph = UnifiedGraph()

        edge1 = Edge(from_id="client1", to_id="server", edge_type="http_call")
        edge2 = Edge(from_id="client2", to_id="server", edge_type="http_call")
        edge3 = Edge(from_id="client3", to_id="other", edge_type="http_call")

        graph.add_edge(edge1)
        graph.add_edge(edge2)
        graph.add_edge(edge3)

        edges_to_server = graph.get_edges_to("server")

        assert len(edges_to_server) == 2


class TestFieldRenameBreach:
    """Test detection of Java POJO field renames breaking TypeScript interfaces."""

    def test_detect_missing_field_breach(self):
        """Test detection of missing field after rename."""
        graph = UnifiedGraph()

        # Server: Java POJO with renamed field (userId -> id)
        server = Node(
            node_id="java::com.example.User",
            node_type="class",
            language="java",
            fields={"id", "name", "email"},  # userId was renamed to id
        )

        # Client: TypeScript interface still using old field name
        client = Node(
            node_id="typescript::src/types::UserInterface",
            node_type="interface",
            language="typescript",
            fields={"userId", "name", "email"},  # Still references userId
            metadata={"referenced_fields": {"userId", "name", "email"}},
        )

        edge = Edge(
            from_id=client.node_id,
            to_id=server.node_id,
            edge_type="type_reference",
            confidence=0.95,
        )

        graph.add_node(server)
        graph.add_node(client)
        graph.add_edge(edge)

        detector = ContractBreachDetector(graph)
        breaches = detector.detect_breaches(server.node_id)

        assert len(breaches) == 1
        assert breaches[0].breach_type == BreachType.MISSING_FIELD
        assert "userId" in breaches[0].fields
        assert breaches[0].severity == Severity.HIGH

    def test_no_breach_when_fields_match(self):
        """Test that no breach is detected when fields match."""
        graph = UnifiedGraph()

        # Server and client both use "id"
        server = Node(
            node_id="java::User",
            node_type="class",
            language="java",
            fields={"id", "name"},
        )

        client = Node(
            node_id="typescript::UserInterface",
            node_type="interface",
            language="typescript",
            fields={"id", "name"},
            metadata={"referenced_fields": {"id", "name"}},
        )

        edge = Edge(
            from_id=client.node_id,
            to_id=server.node_id,
            edge_type="type_reference",
            confidence=1.0,
        )

        graph.add_node(server)
        graph.add_node(client)
        graph.add_edge(edge)

        detector = ContractBreachDetector(graph)
        breaches = detector.detect_breaches(server.node_id)

        assert len(breaches) == 0


class TestEndpointPathBreach:
    """Test detection of REST endpoint path changes breaking frontend."""

    def test_detect_endpoint_path_change(self):
        """Test detection of changed endpoint path."""
        graph = UnifiedGraph()

        # Server: Endpoint path changed
        server = Node(
            node_id="java::UserController:getUser",
            node_type="endpoint",
            language="java",
            metadata={"path": "/api/v2/users/{id}"},  # Changed from /api/users/{id}
        )

        # Client: Still calling old path
        client = Node(
            node_id="typescript::api/userService::fetchUser",
            node_type="function",
            language="typescript",
            metadata={"target_path": "/api/users/{id}"},
        )

        edge = Edge(
            from_id=client.node_id,
            to_id=server.node_id,
            edge_type="http_call",
            confidence=0.9,
        )

        graph.add_node(server)
        graph.add_node(client)
        graph.add_edge(edge)

        detector = ContractBreachDetector(graph)
        breaches = detector.detect_breaches(server.node_id)

        assert len(breaches) == 1
        assert breaches[0].breach_type == BreachType.ENDPOINT_PATH_CHANGED
        assert breaches[0].severity == Severity.CRITICAL
        assert breaches[0].old_value == "/api/users/{id}"
        assert breaches[0].new_value == "/api/v2/users/{id}"

    def test_no_breach_when_paths_match(self):
        """Test that no breach is detected when paths match."""
        graph = UnifiedGraph()

        server = Node(
            node_id="java::UserController:getUser",
            node_type="endpoint",
            language="java",
            metadata={"path": "/api/users/{id}"},
        )

        client = Node(
            node_id="typescript::fetchUser",
            node_type="function",
            language="typescript",
            metadata={"target_path": "/api/users/{id}"},
        )

        edge = Edge(
            from_id=client.node_id,
            to_id=server.node_id,
            edge_type="http_call",
            confidence=1.0,
        )

        graph.add_node(server)
        graph.add_node(client)
        graph.add_edge(edge)

        detector = ContractBreachDetector(graph)
        breaches = detector.detect_breaches(server.node_id)

        assert len(breaches) == 0


class TestResponseFormatBreach:
    """Test detection of response format changes breaking client."""

    def test_detect_response_format_change(self):
        """Test detection of changed response format."""
        graph = UnifiedGraph()

        # Server: Changed response format
        server = Node(
            node_id="java::UserController:getUser",
            node_type="endpoint",
            language="java",
            metadata={
                "response_format": {
                    "id": "string",  # Changed from number
                    "name": "string",
                }
            },
        )

        # Client: Expects old format
        client = Node(
            node_id="typescript::UserService",
            node_type="class",
            language="typescript",
            metadata={"expected_format": {"id": "number", "name": "string"}},  # Expects number
        )

        edge = Edge(
            from_id=client.node_id,
            to_id=server.node_id,
            edge_type="response_consumer",
            confidence=0.85,
        )

        graph.add_node(server)
        graph.add_node(client)
        graph.add_edge(edge)

        detector = ContractBreachDetector(graph)
        breaches = detector.detect_breaches(server.node_id)

        assert len(breaches) == 1
        assert breaches[0].breach_type == BreachType.RESPONSE_FORMAT_CHANGED
        assert breaches[0].severity == Severity.HIGH


class TestConfidenceWeighting:
    """Test confidence-weighted detection."""

    def test_skip_low_confidence_edges(self):
        """Test that low-confidence edges are skipped."""
        graph = UnifiedGraph()

        server = Node(node_id="java::User", node_type="class", language="java", fields={"id"})

        client = Node(
            node_id="typescript::User",
            node_type="interface",
            language="typescript",
            fields={"userId"},
            metadata={"referenced_fields": {"userId"}},
        )

        # Low confidence edge
        edge = Edge(
            from_id=client.node_id,
            to_id=server.node_id,
            edge_type="type_reference",
            confidence=0.5,  # Below default threshold of 0.8
        )

        graph.add_node(server)
        graph.add_node(client)
        graph.add_edge(edge)

        detector = ContractBreachDetector(graph)
        breaches = detector.detect_breaches(server.node_id)

        # Should skip this edge due to low confidence
        assert len(breaches) == 0

    def test_custom_confidence_threshold(self):
        """Test using a custom confidence threshold."""
        graph = UnifiedGraph()

        server = Node(node_id="java::User", node_type="class", language="java", fields={"id"})

        client = Node(
            node_id="typescript::User",
            node_type="interface",
            language="typescript",
            fields={"userId"},
            metadata={"referenced_fields": {"userId"}},
        )

        edge = Edge(
            from_id=client.node_id,
            to_id=server.node_id,
            edge_type="type_reference",
            confidence=0.6,
        )

        graph.add_node(server)
        graph.add_node(client)
        graph.add_edge(edge)

        detector = ContractBreachDetector(graph)

        # With threshold 0.8, should find nothing
        breaches_high = detector.detect_breaches(server.node_id, min_confidence=0.8)
        assert len(breaches_high) == 0

        # With threshold 0.5, should find the breach
        breaches_low = detector.detect_breaches(server.node_id, min_confidence=0.5)
        assert len(breaches_low) == 1


class TestFixHints:
    """Test that fix hints are provided for each breach type."""

    def test_field_breach_has_fix_hint(self):
        """Test that field breach provides a fix hint."""
        graph = UnifiedGraph()

        server = Node(node_id="java::User", node_type="class", language="java", fields={"id"})

        client = Node(
            node_id="typescript::User",
            node_type="interface",
            language="typescript",
            metadata={"referenced_fields": {"userId"}},
        )

        edge = Edge(
            from_id=client.node_id,
            to_id=server.node_id,
            edge_type="type_reference",
            confidence=1.0,
        )

        graph.add_node(server)
        graph.add_node(client)
        graph.add_edge(edge)

        detector = ContractBreachDetector(graph)
        breaches = detector.detect_breaches(server.node_id)

        assert len(breaches) == 1
        assert breaches[0].fix_hint != ""
        assert "typescript::User" in breaches[0].fix_hint

    def test_endpoint_breach_has_fix_hint(self):
        """Test that endpoint breach provides a fix hint."""
        graph = UnifiedGraph()

        server = Node(
            node_id="java::Controller",
            node_type="endpoint",
            language="java",
            metadata={"path": "/v2/users"},
        )

        client = Node(
            node_id="typescript::api",
            node_type="function",
            language="typescript",
            metadata={"target_path": "/v1/users"},
        )

        edge = Edge(
            from_id=client.node_id,
            to_id=server.node_id,
            edge_type="http_call",
            confidence=1.0,
        )

        graph.add_node(server)
        graph.add_node(client)
        graph.add_edge(edge)

        detector = ContractBreachDetector(graph)
        breaches = detector.detect_breaches(server.node_id)

        assert len(breaches) == 1
        assert breaches[0].fix_hint != ""
        assert "/v2/users" in breaches[0].fix_hint


class TestConvenienceFunction:
    """Test the convenience function."""

    def test_detect_breaches_function(self):
        """Test the detect_breaches convenience function."""
        graph = UnifiedGraph()

        server = Node(node_id="server", node_type="class", language="java", fields={"id"})

        client = Node(
            node_id="client",
            node_type="interface",
            language="typescript",
            metadata={"referenced_fields": {"userId"}},
        )

        edge = Edge(
            from_id=client.node_id,
            to_id=server.node_id,
            edge_type="type_reference",
            confidence=1.0,
        )

        graph.add_node(server)
        graph.add_node(client)
        graph.add_edge(edge)

        breaches = detect_breaches(graph, server.node_id)

        assert len(breaches) == 1


class TestAcceptanceCriteria:
    """Test acceptance criteria from the problem statement."""

    def test_detect_java_pojo_field_rename_breaking_ts(self):
        """Acceptance: Detect Java POJO field rename breaking TS interface."""
        graph = UnifiedGraph()

        # Java POJO with renamed field
        server = Node(
            node_id="java::com.example.api::User",
            node_type="class",
            language="java",
            fields={"id", "username", "email"},  # userId renamed to id
        )

        # TypeScript interface with old field name
        client = Node(
            node_id="typescript::src/types::IUser",
            node_type="interface",
            language="typescript",
            metadata={"referenced_fields": {"userId", "username", "email"}},
        )

        edge = Edge(
            from_id=client.node_id,
            to_id=server.node_id,
            edge_type="type_reference",
            confidence=0.9,
        )

        graph.add_node(server)
        graph.add_node(client)
        graph.add_edge(edge)

        breaches = detect_breaches(graph, server.node_id)

        assert len(breaches) == 1
        assert breaches[0].breach_type == BreachType.MISSING_FIELD
        assert "userId" in breaches[0].fields

    def test_detect_rest_endpoint_path_change_breaking_frontend(self):
        """Acceptance: Detect REST endpoint path change breaking frontend."""
        graph = UnifiedGraph()

        server = Node(
            node_id="java::api::UserController:getUser",
            node_type="endpoint",
            language="java",
            metadata={"path": "/api/v2/users/{id}"},
        )

        client = Node(
            node_id="typescript::services::UserService:fetchUser",
            node_type="function",
            language="typescript",
            metadata={"target_path": "/api/users/{id}"},
        )

        edge = Edge(
            from_id=client.node_id,
            to_id=server.node_id,
            edge_type="http_call",
            confidence=0.95,
        )

        graph.add_node(server)
        graph.add_node(client)
        graph.add_edge(edge)

        breaches = detect_breaches(graph, server.node_id)

        assert len(breaches) == 1
        assert breaches[0].breach_type == BreachType.ENDPOINT_PATH_CHANGED

    def test_detect_response_format_change_breaking_client(self):
        """Acceptance: Detect response format change breaking client."""
        graph = UnifiedGraph()

        server = Node(
            node_id="java::api::UserEndpoint",
            node_type="endpoint",
            language="java",
            metadata={"response_format": {"id": "UUID", "name": "string"}},
        )

        client = Node(
            node_id="typescript::client",
            node_type="class",
            language="typescript",
            metadata={"expected_format": {"id": "number", "name": "string"}},
        )

        edge = Edge(
            from_id=client.node_id,
            to_id=server.node_id,
            edge_type="response_consumer",
            confidence=0.9,
        )

        graph.add_node(server)
        graph.add_node(client)
        graph.add_edge(edge)

        breaches = detect_breaches(graph, server.node_id)

        assert len(breaches) == 1
        assert breaches[0].breach_type == BreachType.RESPONSE_FORMAT_CHANGED

    def test_provide_fix_hints_for_each_breach(self):
        """Acceptance: Provide fix hints for each breach."""
        graph = UnifiedGraph()

        server = Node(node_id="server", node_type="class", language="java", fields={"id"})

        client = Node(
            node_id="client",
            node_type="interface",
            language="typescript",
            metadata={"referenced_fields": {"userId"}},
        )

        edge = Edge(
            from_id=client.node_id,
            to_id=server.node_id,
            edge_type="type_reference",
            confidence=1.0,
        )

        graph.add_node(server)
        graph.add_node(client)
        graph.add_edge(edge)

        breaches = detect_breaches(graph, server.node_id)

        assert len(breaches) == 1
        assert breaches[0].fix_hint != ""
        assert len(breaches[0].fix_hint) > 20  # Should be substantial

    def test_confidence_weighted_detection(self):
        """Acceptance: Confidence-weighted detection (skip uncertain links)."""
        graph = UnifiedGraph()

        server = Node(node_id="server", node_type="class", language="java", fields={"id"})
        client = Node(
            node_id="client",
            node_type="interface",
            language="typescript",
            metadata={"referenced_fields": {"userId"}},
        )

        # Low confidence edge
        edge = Edge(
            from_id=client.node_id,
            to_id=server.node_id,
            edge_type="type_reference",
            confidence=0.3,  # Very uncertain
        )

        graph.add_node(server)
        graph.add_node(client)
        graph.add_edge(edge)

        # Should skip uncertain links
        breaches = detect_breaches(graph, server.node_id, min_confidence=0.8)
        assert len(breaches) == 0
