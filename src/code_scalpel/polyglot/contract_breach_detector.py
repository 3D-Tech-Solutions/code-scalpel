from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class BreachType(Enum):
    """Types of contract breaches."""

    MISSING_FIELD = "missing_field"
    FIELD_RENAMED = "field_renamed"
    ENDPOINT_PATH_CHANGED = "endpoint_path_changed"
    RESPONSE_FORMAT_CHANGED = "response_format_changed"
    TYPE_MISMATCH = "type_mismatch"
    METHOD_CHANGED = "method_changed"


class Severity(Enum):
    """Severity levels for contract breaches."""

    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@dataclass
class ContractBreach:
    """
    [20251216_FEATURE] Represents a contract breach between server and client.

    Example:
        >>> breach = ContractBreach(
        ...     server="java::UserController:getUser",
        ...     client="typescript::fetchUser",
        ...     breach_type=BreachType.MISSING_FIELD,
        ...     fields={"userId"},
        ...     severity=Severity.HIGH,
        ...     fix_hint="Update TypeScript interface to use 'id' instead of 'userId'"
        ... )
    """

    server: str  # Server node ID
    client: str  # Client node ID
    breach_type: BreachType
    severity: Severity
    description: str = ""
    fix_hint: str = ""
    confidence: float = 1.0  # 0.0-1.0

    # Additional context
    fields: set[str] = field(default_factory=set)
    old_value: str | None = None
    new_value: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Edge:
    """
    [20251216_FEATURE] Represents a dependency edge in the unified graph.
    """

    from_id: str
    to_id: str
    edge_type: str  # "type_reference", "http_call", "import", etc.
    confidence: float = 1.0


@dataclass
class Node:
    """
    [20251216_FEATURE] Represents a node in the unified graph.
    """

    node_id: str
    node_type: str  # "class", "function", "endpoint", "interface", etc.
    language: str  # "python", "java", "typescript", etc.
    fields: set[str] = field(default_factory=set)
    metadata: dict[str, Any] = field(default_factory=dict)


class UnifiedGraph:
    """
    [20251216_FEATURE] Simplified unified graph for contract breach detection.

    This is a stub implementation that demonstrates the concept.
    A full implementation would integrate with the project's AST analysis.
    """

    def __init__(self):
        """Initialize the unified graph."""
        self.nodes: dict[str, Node] = {}
        self.edges: list[Edge] = []

    def add_node(self, node: Node) -> None:
        """Add a node to the graph."""
        self.nodes[node.node_id] = node

    def add_edge(self, edge: Edge) -> None:
        """Add an edge to the graph."""
        self.edges.append(edge)

    def get_node(self, node_id: str) -> Node | None:
        """Get a node by ID."""
        return self.nodes.get(node_id)

    def get_edges_to(self, node_id: str) -> list[Edge]:
        """Get all edges pointing to a node."""
        return [e for e in self.edges if e.to_id == node_id]

    def get_edges_from(self, node_id: str) -> list[Edge]:
        """Get all edges originating from a node."""
        return [e for e in self.edges if e.from_id == node_id]


class ContractBreachDetector:
    """
    [20251216_FEATURE] Detect contract breaches when a node changes.

    Purpose: Detect when backend API changes break frontend contracts.

    Examples:
    - Java POJO field renamed, TypeScript interface still uses old name
    - REST endpoint path changed, frontend still calls old path
    - Response format changed, frontend expects old format

    Example:
        >>> graph = UnifiedGraph()
        >>> detector = ContractBreachDetector(graph)
        >>> breaches = detector.detect_breaches("java::UserController:getUser")
        >>> for breach in breaches:
        ...     print(f"{breach.severity.value}: {breach.description}")
    """

    def __init__(self, graph: UnifiedGraph):
        """
        Initialize the contract breach detector.

        Args:
            graph: Unified graph with cross-language dependencies

        [20251216_FEATURE] Initialize with unified graph
        """
        self.graph = graph

    def detect_breaches(self, changed_node_id: str, min_confidence: float = 0.8) -> list[ContractBreach]:
        """
        Detect contract breaches when a node changes.

        Args:
            changed_node_id: ID of the node that changed
            min_confidence: Minimum confidence threshold for edges

        Returns:
            List of detected contract breaches

        [20251216_FEATURE] Main breach detection method
        """
        breaches: list[ContractBreach] = []

        # Get the changed node
        changed_node = self.graph.get_node(changed_node_id)
        if not changed_node:
            return breaches

        # Find all clients of this node
        client_edges = self.graph.get_edges_to(changed_node_id)

        for edge in client_edges:
            # Skip low-confidence edges
            if edge.confidence < min_confidence:
                continue

            # Check for staleness
            breach = self._check_staleness(server_node=changed_node_id, client_node=edge.from_id, edge=edge)

            if breach:
                breaches.append(breach)

        return breaches

    def _check_staleness(self, server_node: str, client_node: str, edge: Edge) -> ContractBreach | None:
        """
        Check if client is using outdated contract.

        Args:
            server_node: Server node ID
            client_node: Client node ID
            edge: Edge connecting them

        Returns:
            ContractBreach if detected, None otherwise

        [20251216_FEATURE] Staleness detection for specific edge types
        """
        server = self.graph.get_node(server_node)
        client = self.graph.get_node(client_node)

        if not server or not client:
            return None

        # Field rename detection
        if edge.edge_type == "type_reference":
            return self._detect_field_breach(server, client, edge)

        # REST endpoint detection
        elif edge.edge_type == "http_call":
            return self._detect_endpoint_breach(server, client, edge)

        # Response format detection
        elif edge.edge_type == "response_consumer":
            return self._detect_format_breach(server, client, edge)

        return None

    def _detect_field_breach(self, server: Node, client: Node, edge: Edge) -> ContractBreach | None:
        """
        Detect Java POJO field rename breaking TS interface.

        [20251216_FEATURE] Field rename detection
        """
        # Get referenced fields from client
        client_fields = client.metadata.get("referenced_fields", set())
        server_fields = server.fields

        # Find missing fields
        missing_fields = client_fields - server_fields

        if missing_fields:
            return ContractBreach(
                server=server.node_id,
                client=client.node_id,
                breach_type=BreachType.MISSING_FIELD,
                severity=Severity.HIGH,
                description=f"Client references fields {missing_fields} that no longer exist in server",
                fix_hint=f"Update {client.node_id} to use renamed fields. Check server fields: {server_fields}",
                confidence=edge.confidence,
                fields=missing_fields,
            )

        return None

    def _detect_endpoint_breach(self, server: Node, client: Node, edge: Edge) -> ContractBreach | None:
        """
        Detect REST endpoint path change breaking frontend.

        [20251216_FEATURE] Endpoint path change detection
        """
        server_path = server.metadata.get("path", "")
        client_path = client.metadata.get("target_path", "")

        if server_path and client_path and server_path != client_path:
            return ContractBreach(
                server=server.node_id,
                client=client.node_id,
                breach_type=BreachType.ENDPOINT_PATH_CHANGED,
                severity=Severity.CRITICAL,
                description=f"Endpoint path changed from '{client_path}' to '{server_path}'",
                fix_hint=f"Update {client.node_id} to call '{server_path}' instead of '{client_path}'",
                confidence=edge.confidence,
                old_value=client_path,
                new_value=server_path,
            )

        return None

    def _detect_format_breach(self, server: Node, client: Node, edge: Edge) -> ContractBreach | None:
        """
        Detect response format change breaking client.

        [20251216_FEATURE] Response format change detection
        """
        server_format = server.metadata.get("response_format", {})
        client_expected = client.metadata.get("expected_format", {})

        # Compare field types
        format_mismatches = set()
        for field_name, expected_type in client_expected.items():
            actual_type = server_format.get(field_name)
            if actual_type and actual_type != expected_type:
                format_mismatches.add(f"{field_name}: {expected_type} -> {actual_type}")

        if format_mismatches:
            return ContractBreach(
                server=server.node_id,
                client=client.node_id,
                breach_type=BreachType.RESPONSE_FORMAT_CHANGED,
                severity=Severity.HIGH,
                description=f"Response format changed: {format_mismatches}",
                fix_hint=f"Update {client.node_id} to handle new response format",
                confidence=edge.confidence,
                metadata={"mismatches": format_mismatches},
            )

        return None


# [20251216_FEATURE] Convenience function for quick breach detection
def detect_breaches(graph: UnifiedGraph, changed_node_id: str, min_confidence: float = 0.8) -> list[ContractBreach]:
    """
    Detect contract breaches for a changed node.

    Args:
        graph: Unified graph
        changed_node_id: ID of changed node
        min_confidence: Minimum confidence threshold

    Returns:
        List of contract breaches

    Example:
        >>> breaches = detect_breaches(graph, "java::UserController:getUser")
        >>> print(f"Found {len(breaches)} breaches")
    """
    detector = ContractBreachDetector(graph)
    return detector.detect_breaches(changed_node_id, min_confidence)
