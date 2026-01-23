"""
Code Scalpel Graph Module - Advanced graph analysis features.

This module provides tier-based graph analysis capabilities:

**Pro Tier:**
- SemanticNeighborFinder: Find semantically similar functions/classes
- LogicalRelationshipDetector: Detect non-call relationships

**Enterprise Tier:**
- GraphQueryEngine: DSL for graph traversals (Cypher-like)
- TraversalRuleEngine: Configurable rule-based traversal
- PathConstraintEngine: Constraint-based path queries

Usage:
    # Pro tier - semantic neighbors
    from code_scalpel.graph import SemanticNeighborFinder
    finder = SemanticNeighborFinder(graph)
    neighbors = finder.find_semantic_neighbors(node_id)

    # Pro tier - logical relationships
    from code_scalpel.graph import LogicalRelationshipDetector
    detector = LogicalRelationshipDetector()
    relationships = detector.find_relationships(nodes, file_map)

    # Enterprise tier - graph queries
    from code_scalpel.graph import GraphQueryEngine
    engine = GraphQueryEngine()
    result = engine.execute("MATCH (n)-[r]->(m) WHERE n.type = 'function'")

    # Enterprise tier - traversal rules
    from code_scalpel.graph import TraversalRuleEngine
    engine = TraversalRuleEngine()
    engine.add_builtin_rule("skip_tests")
    result = engine.traverse(start_id, max_depth=5)

    # Enterprise tier - path constraints
    from code_scalpel.graph import PathConstraintEngine, ConstraintSet
    engine = PathConstraintEngine()
    constraints = ConstraintSet(min_length=2, max_length=5)
    result = engine.find_constrained_paths(start, end, constraints)
"""

from code_scalpel.graph.graph_query import GraphQueryEngine, QueryResult
from code_scalpel.graph.logical_relationships import (
    LogicalRelationship,
    LogicalRelationshipDetector,
    LogicalRelationshipResult,
)
from code_scalpel.graph.path_constraints import (
    ConstrainedPath,
    ConstraintSet,
    ConstraintType,
    PathConstraint,
    PathConstraintEngine,
    PathConstraintResult,
)
from code_scalpel.graph.semantic_neighbors import (
    SemanticNeighbor,
    SemanticNeighborFinder,
    SemanticNeighborResult,
)
from code_scalpel.graph.traversal_rules import (
    RuleType,
    TraversalPath,
    TraversalResult,
    TraversalRule,
    TraversalRuleEngine,
)

__all__ = [
    # Pro tier - Semantic Neighbors
    "SemanticNeighborFinder",
    "SemanticNeighborResult",
    "SemanticNeighbor",
    # Pro tier - Logical Relationships
    "LogicalRelationshipDetector",
    "LogicalRelationshipResult",
    "LogicalRelationship",
    # Enterprise tier - Graph Query Language
    "GraphQueryEngine",
    "QueryResult",
    # Enterprise tier - Traversal Rules
    "TraversalRuleEngine",
    "TraversalResult",
    "TraversalRule",
    "TraversalPath",
    "RuleType",
    # Enterprise tier - Path Constraints
    "PathConstraintEngine",
    "PathConstraintResult",
    "ConstrainedPath",
    "ConstraintSet",
    "PathConstraint",
    "ConstraintType",
]
