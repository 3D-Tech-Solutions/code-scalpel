"""
Traversal Rules - Configurable rules for graph traversal.

[20251226_FEATURE] Enterprise tier feature for get_graph_neighborhood.

Provides a rule engine for controlling graph traversal:
- Boundary rules (stop at certain nodes)
- Weight functions (prioritize certain paths)
- Cycle handling
- Depth limits per edge type
- Module boundary controls

Usage:
    from code_scalpel.graph.traversal_rules import TraversalRuleEngine

    engine = TraversalRuleEngine()
    engine.add_boundary_rule("module_boundary", lambda n: n['module'] != start_module)
    engine.add_weight_rule("complexity_weight", lambda e: 1.0 / (e.get('complexity', 1)))

    results = engine.traverse(graph, start_node, rules=['module_boundary'])
"""

from __future__ import annotations

import heapq
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any


class RuleType(Enum):
    """Types of traversal rules."""

    BOUNDARY = "boundary"  # Stop traversal at matching nodes
    FILTER = "filter"  # Skip edges matching condition
    WEIGHT = "weight"  # Adjust edge weights for priority
    DEPTH_LIMIT = "depth_limit"  # Limit depth by edge type
    AGGREGATE = "aggregate"  # Collect data during traversal


@dataclass
class TraversalRule:
    """A single traversal rule."""

    name: str
    rule_type: RuleType
    condition: Callable[[dict[str, Any]], Any]
    description: str = ""
    priority: int = 0  # Higher = applied first
    enabled: bool = True


@dataclass
class TraversalPath:
    """A path found during traversal."""

    nodes: list[str]
    edges: list[dict[str, Any]]
    total_weight: float
    depth: int
    stopped_by_rule: str | None = None


@dataclass
class TraversalResult:
    """Result of rule-based traversal."""

    success: bool
    start_node: str
    visited_nodes: list[dict[str, Any]]
    visited_edges: list[dict[str, Any]]
    paths: list[TraversalPath]
    rule_activations: dict[str, int]  # rule_name -> times activated
    stats: dict[str, Any]
    error: str | None = None


class TraversalRuleEngine:
    """Engine for rule-based graph traversal."""

    # Built-in rule templates
    BUILTIN_RULES = {
        "skip_external": {
            "type": RuleType.BOUNDARY,
            "condition": lambda n: n.get("module", "") in ("external", "unknown"),
            "description": "Stop at external/unknown modules",
        },
        "skip_tests": {
            "type": RuleType.FILTER,
            "condition": lambda e: "test" in e.get("to_id", "").lower(),
            "description": "Skip edges to test files",
        },
        "skip_private": {
            "type": RuleType.FILTER,
            "condition": lambda e: "::_" in e.get("to_id", "") and "::__" not in e.get("to_id", ""),
            "description": "Skip edges to private functions",
        },
        "complexity_weight": {
            "type": RuleType.WEIGHT,
            "condition": lambda e: 1.0 / max(e.get("complexity", 1), 1),
            "description": "Prefer less complex paths",
        },
        "confidence_weight": {
            "type": RuleType.WEIGHT,
            "condition": lambda e: e.get("confidence", 1.0),
            "description": "Prefer high-confidence edges",
        },
    }

    def __init__(self):
        """Initialize the rule engine."""
        self._rules: dict[str, TraversalRule] = {}
        self._nodes: dict[str, dict[str, Any]] = {}
        self._edges: list[dict[str, Any]] = []
        self._adjacency: dict[str, list[tuple[str, dict[str, Any]]]] = {}
        self._reverse_adjacency: dict[str, list[tuple[str, dict[str, Any]]]] = {}

    def add_rule(
        self,
        name: str,
        rule_type: RuleType,
        condition: Callable[[dict[str, Any]], Any],
        description: str = "",
        priority: int = 0,
    ) -> None:
        """
        Add a traversal rule.

        Args:
            name: Unique rule name
            rule_type: Type of rule (BOUNDARY, FILTER, WEIGHT, etc.)
            condition: Function that takes node/edge data and returns bool/weight
            description: Human-readable description
            priority: Rule priority (higher = applied first)
        """
        self._rules[name] = TraversalRule(
            name=name,
            rule_type=rule_type,
            condition=condition,
            description=description,
            priority=priority,
        )

    def add_builtin_rule(self, name: str) -> bool:
        """
        Add a built-in rule by name.

        Args:
            name: Name of built-in rule

        Returns:
            True if rule was added, False if not found
        """
        if name not in self.BUILTIN_RULES:
            return False

        config = self.BUILTIN_RULES[name]
        self.add_rule(
            name=name,
            rule_type=config["type"],
            condition=config["condition"],
            description=config["description"],
        )
        return True

    def remove_rule(self, name: str) -> bool:
        """Remove a rule by name."""
        if name in self._rules:
            del self._rules[name]
            return True
        return False

    def enable_rule(self, name: str, enabled: bool = True) -> bool:
        """Enable or disable a rule."""
        if name in self._rules:
            self._rules[name].enabled = enabled
            return True
        return False

    def get_rules(self) -> list[TraversalRule]:
        """Get all registered rules."""
        return sorted(self._rules.values(), key=lambda r: -r.priority)

    def load_graph(
        self,
        nodes: list[dict[str, Any]],
        edges: list[dict[str, Any]],
    ) -> None:
        """Load graph data for traversal."""
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
                self._adjacency[from_id].append((to_id, edge))
            if to_id in self._reverse_adjacency:
                self._reverse_adjacency[to_id].append((from_id, edge))

    def traverse(
        self,
        start_id: str,
        max_depth: int = 5,
        direction: str = "both",
        active_rules: set[str] | None = None,
        use_weights: bool = False,
        max_nodes: int = 100,
    ) -> TraversalResult:
        """
        Traverse the graph with rules applied.

        Args:
            start_id: Starting node ID
            max_depth: Maximum traversal depth
            direction: "outgoing", "incoming", or "both"
            active_rules: Set of rule names to apply (None = all enabled)
            use_weights: Use weighted traversal (Dijkstra-like)
            max_nodes: Maximum nodes to visit

        Returns:
            TraversalResult with visited nodes, edges, and rule stats
        """
        if start_id not in self._nodes:
            return TraversalResult(
                success=False,
                start_node=start_id,
                visited_nodes=[],
                visited_edges=[],
                paths=[],
                rule_activations={},
                stats={},
                error=f"Start node '{start_id}' not found",
            )

        try:
            # Get active rules
            rules = self._get_active_rules(active_rules)
            boundary_rules = [r for r in rules if r.rule_type == RuleType.BOUNDARY]
            filter_rules = [r for r in rules if r.rule_type == RuleType.FILTER]
            weight_rules = [r for r in rules if r.rule_type == RuleType.WEIGHT]

            rule_activations: dict[str, int] = {r.name: 0 for r in rules}

            if use_weights and weight_rules:
                return self._weighted_traverse(
                    start_id,
                    max_depth,
                    direction,
                    boundary_rules,
                    filter_rules,
                    weight_rules,
                    rule_activations,
                    max_nodes,
                )
            else:
                return self._bfs_traverse(
                    start_id,
                    max_depth,
                    direction,
                    boundary_rules,
                    filter_rules,
                    rule_activations,
                    max_nodes,
                )

        except Exception as e:
            return TraversalResult(
                success=False,
                start_node=start_id,
                visited_nodes=[],
                visited_edges=[],
                paths=[],
                rule_activations={},
                stats={},
                error=str(e),
            )

    def _get_active_rules(self, active_rules: set[str] | None) -> list[TraversalRule]:
        """Get list of active rules sorted by priority."""
        rules = []
        for rule in self._rules.values():
            if not rule.enabled:
                continue
            if active_rules is not None and rule.name not in active_rules:
                continue
            rules.append(rule)
        return sorted(rules, key=lambda r: -r.priority)

    def _bfs_traverse(
        self,
        start_id: str,
        max_depth: int,
        direction: str,
        boundary_rules: list[TraversalRule],
        filter_rules: list[TraversalRule],
        rule_activations: dict[str, int],
        max_nodes: int,
    ) -> TraversalResult:
        """BFS traversal with rules."""
        visited_nodes: list[dict[str, Any]] = []
        visited_edges: list[dict[str, Any]] = []
        visited_ids: set[str] = {start_id}

        queue: deque[tuple[str, int]] = deque([(start_id, 0)])

        while queue and len(visited_nodes) < max_nodes:
            current_id, depth = queue.popleft()
            current_node = self._nodes.get(current_id, {"id": current_id})

            # Check boundary rules
            stopped = False
            for rule in boundary_rules:
                if rule.condition(current_node):
                    rule_activations[rule.name] += 1
                    stopped = True
                    break

            visited_nodes.append({**current_node, "_depth": depth, "_stopped": stopped})

            if stopped or depth >= max_depth:
                continue

            # Get neighbors
            neighbors = self._get_neighbors(current_id, direction)

            for neighbor_id, edge in neighbors:
                if neighbor_id in visited_ids:
                    continue

                # Check filter rules
                filtered = False
                for rule in filter_rules:
                    if rule.condition(edge):
                        rule_activations[rule.name] += 1
                        filtered = True
                        break

                if filtered:
                    continue

                visited_ids.add(neighbor_id)
                visited_edges.append(edge)
                queue.append((neighbor_id, depth + 1))

        return TraversalResult(
            success=True,
            start_node=start_id,
            visited_nodes=visited_nodes,
            visited_edges=visited_edges,
            paths=[],
            rule_activations=rule_activations,
            stats={
                "max_depth": max_depth,
                "nodes_visited": len(visited_nodes),
                "edges_traversed": len(visited_edges),
            },
        )

    def _weighted_traverse(
        self,
        start_id: str,
        max_depth: int,
        direction: str,
        boundary_rules: list[TraversalRule],
        filter_rules: list[TraversalRule],
        weight_rules: list[TraversalRule],
        rule_activations: dict[str, int],
        max_nodes: int,
    ) -> TraversalResult:
        """Weighted traversal (Dijkstra-like) with rules."""
        visited_nodes: list[dict[str, Any]] = []
        visited_edges: list[dict[str, Any]] = []
        visited_ids: set[str] = set()

        # Priority queue: (weight, depth, node_id)
        heap: list[tuple[float, int, str]] = [(0.0, 0, start_id)]

        while heap and len(visited_nodes) < max_nodes:
            weight, depth, current_id = heapq.heappop(heap)

            if current_id in visited_ids:
                continue

            visited_ids.add(current_id)
            current_node = self._nodes.get(current_id, {"id": current_id})

            # Check boundary rules
            stopped = False
            for rule in boundary_rules:
                if rule.condition(current_node):
                    rule_activations[rule.name] += 1
                    stopped = True
                    break

            visited_nodes.append(
                {
                    **current_node,
                    "_depth": depth,
                    "_weight": weight,
                    "_stopped": stopped,
                }
            )

            if stopped or depth >= max_depth:
                continue

            # Get neighbors
            neighbors = self._get_neighbors(current_id, direction)

            for neighbor_id, edge in neighbors:
                if neighbor_id in visited_ids:
                    continue

                # Check filter rules
                filtered = False
                for rule in filter_rules:
                    if rule.condition(edge):
                        rule_activations[rule.name] += 1
                        filtered = True
                        break

                if filtered:
                    continue

                # Calculate edge weight
                edge_weight = 1.0
                for rule in weight_rules:
                    w = rule.condition(edge)
                    if isinstance(w, (int, float)):
                        edge_weight *= w
                        rule_activations[rule.name] += 1

                new_weight = weight + edge_weight
                visited_edges.append(edge)
                heapq.heappush(heap, (new_weight, depth + 1, neighbor_id))

        return TraversalResult(
            success=True,
            start_node=start_id,
            visited_nodes=visited_nodes,
            visited_edges=visited_edges,
            paths=[],
            rule_activations=rule_activations,
            stats={
                "max_depth": max_depth,
                "nodes_visited": len(visited_nodes),
                "edges_traversed": len(visited_edges),
                "weighted": True,
            },
        )

    def _get_neighbors(
        self,
        node_id: str,
        direction: str,
    ) -> list[tuple[str, dict[str, Any]]]:
        """Get neighbors based on direction."""
        neighbors = []

        if direction in ("outgoing", "both"):
            neighbors.extend(self._adjacency.get(node_id, []))
        if direction in ("incoming", "both"):
            neighbors.extend(self._reverse_adjacency.get(node_id, []))

        return neighbors

    def find_paths_with_rules(
        self,
        start_id: str,
        end_id: str,
        max_depth: int = 10,
        active_rules: set[str] | None = None,
    ) -> list[TraversalPath]:
        """
        Find all paths between two nodes respecting rules.

        Args:
            start_id: Starting node ID
            end_id: Target node ID
            max_depth: Maximum path length
            active_rules: Rules to apply

        Returns:
            List of valid paths
        """
        rules = self._get_active_rules(active_rules)
        boundary_rules = [r for r in rules if r.rule_type == RuleType.BOUNDARY]
        filter_rules = [r for r in rules if r.rule_type == RuleType.FILTER]
        weight_rules = [r for r in rules if r.rule_type == RuleType.WEIGHT]

        paths: list[TraversalPath] = []

        # DFS for path finding
        stack: list[tuple[str, list[str], list[dict[str, Any]], float]] = [(start_id, [start_id], [], 0.0)]

        while stack:
            current_id, path, edges, weight = stack.pop()

            if current_id == end_id:
                paths.append(
                    TraversalPath(
                        nodes=path,
                        edges=edges,
                        total_weight=weight,
                        depth=len(path) - 1,
                    )
                )
                continue

            if len(path) > max_depth:
                continue

            current_node = self._nodes.get(current_id, {"id": current_id})

            # Check boundary (skip if at boundary)
            boundary_hit = False
            for rule in boundary_rules:
                if rule.condition(current_node) and current_id != start_id:
                    boundary_hit = True
                    break
            if boundary_hit:
                continue

            for neighbor_id, edge in self._adjacency.get(current_id, []):
                if neighbor_id in path:  # Avoid cycles
                    continue

                # Check filter
                filtered = False
                for rule in filter_rules:
                    if rule.condition(edge):
                        filtered = True
                        break
                if filtered:
                    continue

                # Calculate weight
                edge_weight = 1.0
                for rule in weight_rules:
                    w = rule.condition(edge)
                    if isinstance(w, (int, float)):
                        edge_weight *= w

                stack.append(
                    (
                        neighbor_id,
                        path + [neighbor_id],
                        edges + [edge],
                        weight + edge_weight,
                    )
                )

        return sorted(paths, key=lambda p: p.total_weight)


def create_rule_engine() -> TraversalRuleEngine:
    """Convenience function to create a rule engine."""
    return TraversalRuleEngine()
