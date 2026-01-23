"""
Path Constraints - Constraint-based path queries in graphs.

[20251226_FEATURE] Enterprise tier feature for get_graph_neighborhood.

Provides constraint-based path filtering and queries:
- Length constraints (min/max path length)
- Node type constraints (must pass through, must avoid)
- Edge type constraints
- Weight/confidence thresholds
- Pattern matching (sequences of node types)

Usage:
    from code_scalpel.graph.path_constraints import PathConstraintEngine

    engine = PathConstraintEngine()
    engine.load_graph(nodes, edges)

    # Find paths with constraints
    result = engine.find_constrained_paths(
        start='main',
        end='process',
        constraints=ConstraintSet(
            min_length=2,
            max_length=5,
            must_visit=['helper'],
            must_avoid=['deprecated'],
            edge_types=['calls', 'imports'],
        )
    )
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ConstraintType(Enum):
    """Types of path constraints."""

    LENGTH = "length"
    NODE_TYPE = "node_type"
    EDGE_TYPE = "edge_type"
    WEIGHT = "weight"
    PATTERN = "pattern"
    CUSTOM = "custom"


@dataclass
class PathConstraint:
    """A single path constraint."""

    constraint_type: ConstraintType
    name: str
    condition: Any  # Type varies by constraint type
    required: bool = True  # If False, constraint is soft (preference)
    weight: float = 1.0  # For soft constraints


@dataclass
class ConstraintSet:
    """A collection of path constraints."""

    min_length: int | None = None
    max_length: int | None = None
    must_visit: list[str] = field(default_factory=list)
    must_avoid: list[str] = field(default_factory=list)
    edge_types: list[str] | None = None  # Allowed edge types
    node_types: list[str] | None = None  # Allowed node types
    min_confidence: float = 0.0
    max_weight: float | None = None
    pattern: str | None = None  # Node type pattern like "function->class->function"
    custom_constraints: list[PathConstraint] = field(default_factory=list)


@dataclass
class ConstrainedPath:
    """A path that satisfies constraints."""

    nodes: list[dict[str, Any]]
    node_ids: list[str]
    edges: list[dict[str, Any]]
    length: int
    total_weight: float
    total_confidence: float
    constraints_satisfied: list[str]
    constraints_violated: list[str]  # For soft constraints
    score: float  # Overall score (higher is better)


@dataclass
class PathConstraintResult:
    """Result of constrained path finding."""

    success: bool
    paths: list[ConstrainedPath]
    total_paths_found: int
    paths_after_filtering: int
    constraints_applied: list[str]
    stats: dict[str, Any]
    error: str | None = None


class PathConstraintEngine:
    """Engine for constraint-based path queries."""

    def __init__(self):
        """Initialize the path constraint engine."""
        self._nodes: dict[str, dict[str, Any]] = {}
        self._edges: list[dict[str, Any]] = []
        self._adjacency: dict[str, list[tuple[str, dict[str, Any]]]] = {}

    def load_graph(
        self,
        nodes: list[dict[str, Any]],
        edges: list[dict[str, Any]],
    ) -> None:
        """Load graph data for path queries."""
        self._nodes.clear()
        self._edges.clear()
        self._adjacency.clear()

        for node in nodes:
            node_id = str(node.get("id", ""))
            self._nodes[node_id] = node
            self._adjacency[node_id] = []

        for edge in edges:
            self._edges.append(edge)
            from_id = str(edge.get("from_id", ""))
            to_id = str(edge.get("to_id", ""))

            if from_id in self._adjacency:
                self._adjacency[from_id].append((to_id, edge))

    def find_constrained_paths(
        self,
        start: str,
        end: str,
        constraints: ConstraintSet,
        max_paths: int = 10,
        max_search_depth: int = 20,
    ) -> PathConstraintResult:
        """
        Find paths between two nodes satisfying constraints.

        Args:
            start: Starting node ID
            end: Ending node ID
            constraints: Constraint set to apply
            max_paths: Maximum paths to return
            max_search_depth: Maximum depth to search

        Returns:
            PathConstraintResult with valid paths
        """
        if start not in self._nodes:
            return PathConstraintResult(
                success=False,
                paths=[],
                total_paths_found=0,
                paths_after_filtering=0,
                constraints_applied=[],
                stats={},
                error=f"Start node '{start}' not found",
            )

        if end not in self._nodes:
            return PathConstraintResult(
                success=False,
                paths=[],
                total_paths_found=0,
                paths_after_filtering=0,
                constraints_applied=[],
                stats={},
                error=f"End node '{end}' not found",
            )

        try:
            # Determine effective max depth
            effective_max_depth = max_search_depth
            if constraints.max_length is not None:
                effective_max_depth = min(effective_max_depth, constraints.max_length + 1)

            # Find all paths
            all_paths = self._find_all_paths(start, end, effective_max_depth)

            # Build constraint list
            constraints_applied = self._get_constraint_names(constraints)

            # Filter and score paths
            valid_paths: list[ConstrainedPath] = []

            for path_nodes, path_edges in all_paths:
                result = self._evaluate_path(path_nodes, path_edges, constraints)
                if result is not None:
                    valid_paths.append(result)

            # Sort by score and limit
            valid_paths.sort(key=lambda p: -p.score)
            returned_paths = valid_paths[:max_paths]

            return PathConstraintResult(
                success=True,
                paths=returned_paths,
                total_paths_found=len(all_paths),
                paths_after_filtering=len(valid_paths),
                constraints_applied=constraints_applied,
                stats={
                    "start": start,
                    "end": end,
                    "max_search_depth": effective_max_depth,
                    "total_candidates": len(all_paths),
                    "valid_paths": len(valid_paths),
                },
            )

        except Exception as e:
            return PathConstraintResult(
                success=False,
                paths=[],
                total_paths_found=0,
                paths_after_filtering=0,
                constraints_applied=[],
                stats={},
                error=str(e),
            )

    def _find_all_paths(
        self,
        start: str,
        end: str,
        max_depth: int,
    ) -> list[tuple[list[str], list[dict[str, Any]]]]:
        """Find all paths between start and end using DFS."""
        paths: list[tuple[list[str], list[dict[str, Any]]]] = []

        # DFS stack: (current_node, path, edges)
        stack: list[tuple[str, list[str], list[dict[str, Any]]]] = [(start, [start], [])]

        while stack:
            current, path, edges = stack.pop()

            if current == end:
                paths.append((path, edges))
                continue

            if len(path) > max_depth:
                continue

            for neighbor, edge in self._adjacency.get(current, []):
                if neighbor not in path:  # Avoid cycles
                    stack.append((neighbor, path + [neighbor], edges + [edge]))

        return paths

    def _evaluate_path(
        self,
        path_node_ids: list[str],
        path_edges: list[dict[str, Any]],
        constraints: ConstraintSet,
    ) -> ConstrainedPath | None:
        """Evaluate a path against constraints."""
        path_length = len(path_node_ids) - 1
        satisfied: list[str] = []
        violated: list[str] = []

        # Length constraints
        if constraints.min_length is not None:
            if path_length >= constraints.min_length:
                satisfied.append("min_length")
            else:
                return None  # Hard constraint

        if constraints.max_length is not None:
            if path_length <= constraints.max_length:
                satisfied.append("max_length")
            else:
                return None  # Hard constraint

        # Must visit constraints
        set(path_node_ids)
        for must_visit in constraints.must_visit:
            # Support partial matching
            found = False
            for node_id in path_node_ids:
                if must_visit in node_id or must_visit == node_id:
                    found = True
                    break
            if found:
                satisfied.append(f"must_visit:{must_visit}")
            else:
                return None  # Hard constraint

        # Must avoid constraints
        for must_avoid in constraints.must_avoid:
            found = False
            for node_id in path_node_ids:
                if must_avoid in node_id or must_avoid == node_id:
                    found = True
                    break
            if found:
                return None  # Hard constraint
            satisfied.append(f"must_avoid:{must_avoid}")

        # Edge type constraints
        if constraints.edge_types is not None:
            for edge in path_edges:
                edge_type = edge.get("type", edge.get("edge_type", "unknown"))
                if edge_type not in constraints.edge_types:
                    return None
            satisfied.append("edge_types")

        # Node type constraints
        if constraints.node_types is not None:
            for node_id in path_node_ids:
                node = self._nodes.get(node_id, {})
                node_type = node.get("type", node.get("node_type", "unknown"))
                if node_type not in constraints.node_types:
                    return None
            satisfied.append("node_types")

        # Confidence constraint
        total_confidence = 0.0
        for edge in path_edges:
            total_confidence += edge.get("confidence", 1.0)
        avg_confidence = total_confidence / max(len(path_edges), 1)

        if avg_confidence >= constraints.min_confidence:
            satisfied.append("min_confidence")
        else:
            return None

        # Weight constraint
        total_weight = sum(e.get("weight", 1.0) for e in path_edges)
        if constraints.max_weight is not None:
            if total_weight <= constraints.max_weight:
                satisfied.append("max_weight")
            else:
                return None

        # Pattern constraint (node type sequence)
        if constraints.pattern:
            if self._check_pattern(path_node_ids, constraints.pattern):
                satisfied.append("pattern")
            else:
                return None

        # Custom constraints
        for custom in constraints.custom_constraints:
            result = self._evaluate_custom_constraint(path_node_ids, path_edges, custom)
            if result:
                satisfied.append(custom.name)
            elif custom.required:
                return None
            else:
                violated.append(custom.name)

        # Calculate score
        score = self._calculate_path_score(path_length, avg_confidence, total_weight, len(satisfied), len(violated))

        # Build node list with full data
        path_nodes = [self._nodes.get(node_id, {"id": node_id}) for node_id in path_node_ids]

        return ConstrainedPath(
            nodes=path_nodes,
            node_ids=path_node_ids,
            edges=path_edges,
            length=path_length,
            total_weight=total_weight,
            total_confidence=total_confidence,
            constraints_satisfied=satisfied,
            constraints_violated=violated,
            score=score,
        )

    def _check_pattern(self, path_node_ids: list[str], pattern: str) -> bool:
        """
        Check if path matches a node type pattern.

        Pattern format: "function->class->method"
        Uses contains matching on node types.
        """
        parts = [p.strip() for p in pattern.split("->")]

        if len(parts) > len(path_node_ids):
            return False

        # Sliding window match
        for start in range(len(path_node_ids) - len(parts) + 1):
            match = True
            for i, pattern_part in enumerate(parts):
                node_id = path_node_ids[start + i]
                node = self._nodes.get(node_id, {})
                node_type = node.get("type", node.get("node_type", ""))

                if pattern_part.lower() not in node_type.lower():
                    match = False
                    break

            if match:
                return True

        return False

    def _evaluate_custom_constraint(
        self,
        path_node_ids: list[str],
        path_edges: list[dict[str, Any]],
        constraint: PathConstraint,
    ) -> bool:
        """Evaluate a custom constraint."""
        try:
            if callable(constraint.condition):
                return bool(constraint.condition(path_node_ids, path_edges))
            return True
        except Exception:
            return False

    def _calculate_path_score(
        self,
        length: int,
        avg_confidence: float,
        total_weight: float,
        satisfied_count: int,
        violated_count: int,
    ) -> float:
        """Calculate overall path score (higher is better)."""
        # Prefer shorter paths
        length_score = 1.0 / (1.0 + length)

        # Prefer high confidence
        confidence_score = avg_confidence

        # Prefer low weight
        weight_score = 1.0 / (1.0 + total_weight)

        # Prefer more constraints satisfied
        constraint_score = satisfied_count / max(satisfied_count + violated_count, 1)

        # Combine scores
        return 0.3 * length_score + 0.3 * confidence_score + 0.2 * weight_score + 0.2 * constraint_score

    def _get_constraint_names(self, constraints: ConstraintSet) -> list[str]:
        """Get list of constraint names being applied."""
        names = []

        if constraints.min_length is not None:
            names.append(f"min_length={constraints.min_length}")
        if constraints.max_length is not None:
            names.append(f"max_length={constraints.max_length}")
        if constraints.must_visit:
            names.append(f"must_visit={constraints.must_visit}")
        if constraints.must_avoid:
            names.append(f"must_avoid={constraints.must_avoid}")
        if constraints.edge_types:
            names.append(f"edge_types={constraints.edge_types}")
        if constraints.node_types:
            names.append(f"node_types={constraints.node_types}")
        if constraints.min_confidence > 0:
            names.append(f"min_confidence={constraints.min_confidence}")
        if constraints.max_weight is not None:
            names.append(f"max_weight={constraints.max_weight}")
        if constraints.pattern:
            names.append(f"pattern={constraints.pattern}")
        for custom in constraints.custom_constraints:
            names.append(f"custom:{custom.name}")

        return names

    def get_path_statistics(
        self,
        start: str,
        end: str,
        max_depth: int = 10,
    ) -> dict[str, Any]:
        """
        Get statistics about paths between two nodes.

        Returns counts, average lengths, etc. without full path enumeration.
        """
        if start not in self._nodes or end not in self._nodes:
            return {"error": "Invalid nodes"}

        paths = self._find_all_paths(start, end, max_depth)

        if not paths:
            return {
                "total_paths": 0,
                "min_length": None,
                "max_length": None,
                "avg_length": None,
            }

        lengths = [len(p[0]) - 1 for p in paths]

        return {
            "total_paths": len(paths),
            "min_length": min(lengths),
            "max_length": max(lengths),
            "avg_length": sum(lengths) / len(lengths),
            "length_distribution": self._count_distribution(lengths),
        }

    def _count_distribution(self, values: list[int]) -> dict[int, int]:
        """Count distribution of values."""
        dist: dict[int, int] = {}
        for v in values:
            dist[v] = dist.get(v, 0) + 1
        return dict(sorted(dist.items()))


def create_path_constraint_engine() -> PathConstraintEngine:
    """Convenience function to create a path constraint engine."""
    return PathConstraintEngine()
