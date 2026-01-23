"""
Graph Query Language - DSL for custom graph traversals.

[20251226_FEATURE] Enterprise tier feature for get_graph_neighborhood.

Provides a simple query language for graph traversal:
- Node selection predicates
- Edge filtering
- Path patterns
- Aggregation operations

Usage:
    from code_scalpel.graph.graph_query import GraphQueryEngine

    engine = GraphQueryEngine(graph)
    results = engine.execute('''
        MATCH (n:function)-[:calls]->(m:function)
        WHERE n.complexity > 10
        RETURN n, m
    ''')
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class QueryOperator(Enum):
    """Query comparison operators."""

    EQ = "="
    NE = "!="
    GT = ">"
    LT = "<"
    GTE = ">="
    LTE = "<="
    CONTAINS = "contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    MATCHES = "matches"  # Regex


@dataclass
class NodePredicate:
    """A predicate to filter nodes."""

    field: str
    operator: QueryOperator
    value: Any

    def matches(self, node_data: dict[str, Any]) -> bool:
        """Check if a node matches this predicate."""
        actual = node_data.get(self.field)

        if actual is None:
            return False

        if self.operator == QueryOperator.EQ:
            return actual == self.value
        elif self.operator == QueryOperator.NE:
            return actual != self.value
        elif self.operator == QueryOperator.GT:
            return actual > self.value
        elif self.operator == QueryOperator.LT:
            return actual < self.value
        elif self.operator == QueryOperator.GTE:
            return actual >= self.value
        elif self.operator == QueryOperator.LTE:
            return actual <= self.value
        elif self.operator == QueryOperator.CONTAINS:
            return str(self.value) in str(actual)
        elif self.operator == QueryOperator.STARTS_WITH:
            return str(actual).startswith(str(self.value))
        elif self.operator == QueryOperator.ENDS_WITH:
            return str(actual).endswith(str(self.value))
        elif self.operator == QueryOperator.MATCHES:
            return bool(re.search(str(self.value), str(actual)))

        return False


@dataclass
class EdgePredicate:
    """A predicate to filter edges."""

    edge_types: set[str]  # Empty = any type
    min_confidence: float = 0.0
    max_confidence: float = 1.0

    def matches(self, edge_data: dict[str, Any]) -> bool:
        """Check if an edge matches this predicate."""
        if self.edge_types:
            edge_type = edge_data.get("type", edge_data.get("edge_type", ""))
            if edge_type not in self.edge_types:
                return False

        confidence = edge_data.get("confidence", 1.0)
        return self.min_confidence <= confidence <= self.max_confidence


@dataclass
class PathPattern:
    """A pattern for matching paths in the graph."""

    source_predicate: NodePredicate | None = None
    edge_predicate: EdgePredicate | None = None
    target_predicate: NodePredicate | None = None
    min_length: int = 1
    max_length: int = 1
    direction: str = "outgoing"  # outgoing, incoming, both


@dataclass
class QueryResult:
    """Result of a graph query."""

    success: bool
    nodes: list[dict[str, Any]]
    edges: list[dict[str, Any]]
    paths: list[list[str]]
    aggregations: dict[str, Any]
    execution_time_ms: float
    error: str | None = None


@dataclass
class GraphQuery:
    """A parsed graph query."""

    node_predicates: list[NodePredicate] = field(default_factory=list)
    edge_predicates: list[EdgePredicate] = field(default_factory=list)
    path_patterns: list[PathPattern] = field(default_factory=list)
    return_fields: list[str] = field(default_factory=list)
    limit: int | None = None
    skip: int = 0
    order_by: str | None = None
    order_desc: bool = False


class GraphQueryEngine:
    """Execute queries against a graph structure."""

    def __init__(self, graph: Any = None):
        """
        Initialize query engine with a graph.

        Args:
            graph: A graph object with nodes and edges
        """
        self.graph = graph
        self._nodes: dict[str, dict[str, Any]] = {}
        self._edges: list[dict[str, Any]] = []
        self._adjacency: dict[str, list[str]] = {}  # outgoing
        self._reverse_adjacency: dict[str, list[str]] = {}  # incoming

        if graph:
            self._build_index(graph)

    def _build_index(self, graph: Any) -> None:
        """Build internal index from graph structure."""
        # Handle different graph formats
        if hasattr(graph, "nodes") and hasattr(graph, "edges"):
            # UniversalGraph-like
            for node in getattr(graph, "nodes", []):
                if isinstance(node, dict):
                    node_id = str(node.get("id", ""))
                    metadata = node.get("metadata", {}) or {}
                else:
                    node_id = str(getattr(node, "id", ""))
                    metadata = getattr(node, "metadata", {}) or {}

                self._nodes[node_id] = {
                    "id": node_id,
                    "metadata": metadata,
                    **metadata,
                }
                self._adjacency[node_id] = []
                self._reverse_adjacency[node_id] = []

            for edge in getattr(graph, "edges", []):
                if isinstance(edge, dict):
                    from_id = str(edge.get("from_id", ""))
                    to_id = str(edge.get("to_id", ""))
                    edge_type = str(edge.get("type", edge.get("edge_type", "")))
                    confidence = edge.get("confidence", 1.0)
                else:
                    from_id = str(getattr(edge, "from_id", ""))
                    to_id = str(getattr(edge, "to_id", ""))
                    edge_type = str(getattr(edge, "edge_type", ""))
                    confidence = getattr(edge, "confidence", 1.0)

                edge_data = {
                    "from_id": from_id,
                    "to_id": to_id,
                    "type": edge_type,
                    "confidence": confidence,
                }
                self._edges.append(edge_data)

                if from_id in self._adjacency:
                    self._adjacency[from_id].append(to_id)
                if to_id in self._reverse_adjacency:
                    self._reverse_adjacency[to_id].append(from_id)

    def load_graph_data(
        self,
        nodes: list[dict[str, Any]],
        edges: list[dict[str, Any]],
    ) -> None:
        """Load graph data directly."""
        self._nodes.clear()
        self._edges.clear()
        self._adjacency.clear()
        self._reverse_adjacency.clear()

        for node in nodes:
            node_id = str(node.get("id", ""))
            self._nodes[node_id] = node
            self._adjacency[node_id] = []
            self._reverse_adjacency[node_id] = []

        for edge in edges:
            self._edges.append(edge)
            from_id = str(edge.get("from_id", ""))
            to_id = str(edge.get("to_id", ""))

            if from_id in self._adjacency:
                self._adjacency[from_id].append(to_id)
            if to_id in self._reverse_adjacency:
                self._reverse_adjacency[to_id].append(from_id)

    def load_graph(self, nodes: list[dict[str, Any]], edges: list[dict[str, Any]]) -> None:
        """Backwards-compatible alias for loading raw graph data.

        Some internal tier tests and older callers expect `load_graph(nodes, edges)`.
        The canonical method name is `load_graph_data`.
        """
        self.load_graph_data(nodes, edges)

    def execute(self, query: str | GraphQuery) -> QueryResult:
        """
        Execute a graph query.

        Args:
            query: Either a query string or a GraphQuery object

        Returns:
            QueryResult with matching nodes, edges, and paths
        """
        import time

        start = time.time()

        try:
            if isinstance(query, str):
                parsed = self._parse_query(query)
            else:
                parsed = query

            # Filter nodes
            matching_nodes = self._filter_nodes(parsed.node_predicates)

            # Filter edges
            matching_edges = self._filter_edges(parsed.edge_predicates)

            # Find paths if patterns specified
            paths = []
            if parsed.path_patterns:
                for pattern in parsed.path_patterns:
                    found_paths = self._find_paths(pattern, matching_nodes)
                    paths.extend(found_paths)

            # Apply ordering
            if parsed.order_by and matching_nodes:
                order_key = parsed.order_by
                matching_nodes.sort(
                    key=lambda n: n.get(order_key, 0) if order_key else 0,
                    reverse=parsed.order_desc,
                )

            # Apply skip and limit
            if parsed.skip > 0:
                matching_nodes = matching_nodes[parsed.skip :]
            if parsed.limit:
                matching_nodes = matching_nodes[: parsed.limit]

            elapsed = (time.time() - start) * 1000

            return QueryResult(
                success=True,
                nodes=matching_nodes,
                edges=matching_edges,
                paths=paths,
                aggregations={},
                execution_time_ms=elapsed,
            )

        except Exception as e:
            elapsed = (time.time() - start) * 1000
            return QueryResult(
                success=False,
                nodes=[],
                edges=[],
                paths=[],
                aggregations={},
                execution_time_ms=elapsed,
                error=str(e),
            )

    def _parse_query(self, query_str: str) -> GraphQuery:
        """Parse a query string into a GraphQuery object."""
        parsed = GraphQuery()

        # Simple parser for common patterns
        query_str = query_str.strip()

        # Parse WHERE clauses
        where_match = re.search(r"WHERE\s+(.+?)(?:RETURN|LIMIT|ORDER|$)", query_str, re.IGNORECASE)
        if where_match:
            conditions = where_match.group(1).strip()
            parsed.node_predicates = self._parse_conditions(conditions)

        # Parse LIMIT
        limit_match = re.search(r"LIMIT\s+(\d+)", query_str, re.IGNORECASE)
        if limit_match:
            parsed.limit = int(limit_match.group(1))

        # Parse ORDER BY
        order_match = re.search(r"ORDER\s+BY\s+(\w+)(?:\s+(ASC|DESC))?", query_str, re.IGNORECASE)
        if order_match:
            parsed.order_by = order_match.group(1)
            parsed.order_desc = (order_match.group(2) or "").upper() == "DESC"

        return parsed

    def _parse_conditions(self, conditions: str) -> list[NodePredicate]:
        """Parse WHERE conditions into predicates."""
        predicates = []

        # Split by AND (simple case)
        parts = re.split(r"\s+AND\s+", conditions, flags=re.IGNORECASE)

        for part in parts:
            part = part.strip()

            # Match patterns like: field > value, field = 'value', etc.
            match = re.match(
                r'(\w+)\s*(=|!=|>=|<=|>|<|contains|starts_with|ends_with|matches)\s*[\'"]?([^\'"]+)[\'"]?',
                part,
                re.IGNORECASE,
            )

            if match:
                field = match.group(1)
                op_str = match.group(2).lower()
                value = match.group(3).strip()

                # Map operator string to enum
                op_map = {
                    "=": QueryOperator.EQ,
                    "!=": QueryOperator.NE,
                    ">": QueryOperator.GT,
                    "<": QueryOperator.LT,
                    ">=": QueryOperator.GTE,
                    "<=": QueryOperator.LTE,
                    "contains": QueryOperator.CONTAINS,
                    "starts_with": QueryOperator.STARTS_WITH,
                    "ends_with": QueryOperator.ENDS_WITH,
                    "matches": QueryOperator.MATCHES,
                }

                operator = op_map.get(op_str, QueryOperator.EQ)

                # Try to convert value to number if possible
                try:
                    value = int(value)
                except ValueError:
                    try:
                        value = float(value)
                    except ValueError:
                        pass

                predicates.append(NodePredicate(field, operator, value))

        return predicates

    def _filter_nodes(self, predicates: list[NodePredicate]) -> list[dict[str, Any]]:
        """Filter nodes by predicates."""
        if not predicates:
            return list(self._nodes.values())

        matching = []
        for node in self._nodes.values():
            if all(pred.matches(node) for pred in predicates):
                matching.append(node)

        return matching

    def _filter_edges(self, predicates: list[EdgePredicate]) -> list[dict[str, Any]]:
        """Filter edges by predicates."""
        if not predicates:
            return list(self._edges)

        matching = []
        for edge in self._edges:
            if all(pred.matches(edge) for pred in predicates):
                matching.append(edge)

        return matching

    def _find_paths(
        self,
        pattern: PathPattern,
        source_nodes: list[dict[str, Any]],
    ) -> list[list[str]]:
        """Find paths matching a pattern."""
        paths = []

        for source in source_nodes:
            source_id = source.get("id", "")
            found = self._bfs_paths(
                source_id,
                pattern.target_predicate,
                pattern.edge_predicate,
                pattern.min_length,
                pattern.max_length,
                pattern.direction,
            )
            paths.extend(found)

        return paths

    def _bfs_paths(
        self,
        start_id: str,
        target_pred: NodePredicate | None,
        edge_pred: EdgePredicate | None,
        min_length: int,
        max_length: int,
        direction: str,
    ) -> list[list[str]]:
        """BFS to find paths matching constraints."""
        from collections import deque

        paths = []
        # Queue entries: (current_id, path_so_far)
        queue: deque[tuple[str, list[str]]] = deque([(start_id, [start_id])])
        visited = {start_id}

        while queue:
            current, path = queue.popleft()

            if len(path) > max_length + 1:
                continue

            # Get neighbors based on direction
            neighbors = []
            if direction in ("outgoing", "both"):
                neighbors.extend(self._adjacency.get(current, []))
            if direction in ("incoming", "both"):
                neighbors.extend(self._reverse_adjacency.get(current, []))

            for neighbor in neighbors:
                if neighbor in visited:
                    continue

                # Check edge predicate if needed
                if edge_pred:
                    # Find the edge
                    edge_match = False
                    for edge in self._edges:
                        if (edge["from_id"] == current and edge["to_id"] == neighbor) or (
                            edge["to_id"] == current and edge["from_id"] == neighbor
                        ):
                            if edge_pred.matches(edge):
                                edge_match = True
                                break
                    if not edge_match:
                        continue

                new_path = path + [neighbor]

                # Check if this path is valid
                if len(new_path) >= min_length + 1:
                    # Check target predicate
                    if target_pred:
                        target_node = self._nodes.get(neighbor, {})
                        if target_pred.matches(target_node):
                            paths.append(new_path)
                    else:
                        paths.append(new_path)

                if len(new_path) <= max_length:
                    visited.add(neighbor)
                    queue.append((neighbor, new_path))

        return paths

    def select_nodes(
        self,
        predicate: Callable[[dict[str, Any]], bool] | None = None,
        **kwargs,
    ) -> list[dict[str, Any]]:
        """
        Select nodes matching criteria.

        Args:
            predicate: Optional function to filter nodes
            **kwargs: Field=value pairs to match

        Returns:
            List of matching node dictionaries
        """
        matching = []

        for node in self._nodes.values():
            # Check predicate
            if predicate and not predicate(node):
                continue

            # Check kwargs
            matches_kwargs = True
            for key, value in kwargs.items():
                if node.get(key) != value:
                    matches_kwargs = False
                    break

            if matches_kwargs:
                matching.append(node)

        return matching

    def traverse(
        self,
        start_id: str,
        direction: str = "outgoing",
        max_depth: int = 3,
        edge_filter: Callable[[dict[str, Any]], bool] | None = None,
    ) -> Iterator[dict[str, Any]]:
        """
        Traverse the graph from a starting node.

        Args:
            start_id: Starting node ID
            direction: "outgoing", "incoming", or "both"
            max_depth: Maximum traversal depth
            edge_filter: Optional function to filter edges

        Yields:
            Nodes encountered during traversal with depth info
        """
        from collections import deque

        visited = {start_id}
        queue: deque[tuple[str, int]] = deque([(start_id, 0)])

        while queue:
            current_id, depth = queue.popleft()
            current_node = self._nodes.get(current_id, {"id": current_id})

            yield {**current_node, "_depth": depth}

            if depth >= max_depth:
                continue

            neighbors = []
            if direction in ("outgoing", "both"):
                neighbors.extend(self._adjacency.get(current_id, []))
            if direction in ("incoming", "both"):
                neighbors.extend(self._reverse_adjacency.get(current_id, []))

            for neighbor_id in neighbors:
                if neighbor_id in visited:
                    continue

                # Check edge filter
                if edge_filter:
                    edge_ok = False
                    for edge in self._edges:
                        if (edge["from_id"] == current_id and edge["to_id"] == neighbor_id) or (
                            edge["to_id"] == current_id and edge["from_id"] == neighbor_id
                        ):
                            if edge_filter(edge):
                                edge_ok = True
                                break
                    if not edge_ok:
                        continue

                visited.add(neighbor_id)
                queue.append((neighbor_id, depth + 1))


def create_query_engine(graph: Any = None) -> GraphQueryEngine:
    """Convenience function to create a query engine."""
    return GraphQueryEngine(graph)
