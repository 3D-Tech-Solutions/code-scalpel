"""
Graph Engine Example - Cross-language dependency analysis with confidence scoring.

[20251216_FEATURE] v2.1.0 - Demonstration of universal graph engine

This example demonstrates the key features from the problem statement:

1. Universal Node IDs - Standardized format across languages
2. Omni-Schema JSON Format - Graph with nodes and edges
3. Confidence Engine - Scoring edges with confidence levels
4. Cross-Boundary Analysis - Track dependencies across languages
5. HTTP Link Detection - Connect frontend API calls to backend endpoints

Example Output:
    {
      "graph": {
        "nodes": [
          {"id": "java::UserController:getUser", "type": "endpoint", "route": "/api/users"},
          {"id": "typescript::fetchUsers", "type": "client", "target": "/api/users"}
        ],
        "edges": [
          {
            "from": "typescript::fetchUsers",
            "to": "java::UserController:getUser",
            "confidence": 0.95,
            "evidence": "Route string match: /api/users",
            "type": "http_call"
          }
        ]
      }
    }
"""

import json

from code_scalpel.graph_engine import (
    ConfidenceEngine,
    EdgeType,
    GraphBuilder,
    HTTPLinkDetector,
    create_node_id,
)


def example_1_universal_node_ids():
    """
    Example 1: Universal Node IDs

    Demonstrates standardized AST node IDs across Python/Java/TypeScript.
    Format: language::module::type::name[:method]
    """
    print("=" * 60)
    print("Example 1: Universal Node IDs")
    print("=" * 60)

    # Create node IDs for different languages
    python_handler = create_node_id("python", "app.handlers", "class", "RequestHandler")

    java_controller = create_node_id("java", "com.example.api", "controller", "UserController", method="getUser")

    ts_function = create_node_id("typescript", "src/api/client", "function", "fetchUsers")

    print(f"Python class:      {python_handler}")
    print(f"Java method:       {java_controller}")
    print(f"TypeScript func:   {ts_function}")
    print()


def example_2_omni_schema_graph():
    """
    Example 2: Omni-Schema JSON Format

    Demonstrates building a cross-language graph with nodes and edges.
    """
    print("=" * 60)
    print("Example 2: Omni-Schema JSON Format")
    print("=" * 60)

    builder = GraphBuilder()

    # Add nodes
    java_endpoint = create_node_id("java", "com.example.api", "endpoint", "UserController", method="getUser")
    builder.add_node(java_endpoint, metadata={"route": "/api/users", "method": "GET"})

    ts_client = create_node_id("typescript", "src/api/client", "client", "fetchUsers")
    builder.add_node(ts_client, metadata={"target": "/api/users"})

    # Add edge with confidence scoring
    builder.add_edge(
        from_id=str(ts_client),
        to_id=str(java_endpoint),
        edge_type=EdgeType.HTTP_CALL,
        context={"route_match": "exact", "method": "GET"},
    )

    graph = builder.build()

    # Display JSON
    print(graph.to_json(indent=2))
    print()


def example_3_confidence_engine():
    """
    Example 3: Confidence Engine

    Demonstrates confidence scoring for different relationship types.
    """
    print("=" * 60)
    print("Example 3: Confidence Engine")
    print("=" * 60)

    engine = ConfidenceEngine()

    # Test different edge types
    test_cases = [
        (EdgeType.IMPORT_STATEMENT, {}, "import X from Y - definite"),
        (EdgeType.TYPE_ANNOTATION, {}, "User: UserType - definite"),
        (EdgeType.HTTP_CALL, {"route_match": "exact"}, 'Exact route: "/api/users"'),
        (EdgeType.ROUTE_PATTERN_MATCH, {}, 'Pattern: "/api/users/{id}"'),
        (EdgeType.STRING_LITERAL_MATCH, {"string_length": 25}, "String literal match"),
        (EdgeType.DYNAMIC_ROUTE, {}, 'Dynamic: "/api/" + version'),
    ]

    print(f"{'Edge Type':<25} {'Confidence':<12} {'Level':<10} {'Requires Approval'}")
    print("-" * 70)

    for edge_type, context, description in test_cases:
        evidence = engine.score_edge(edge_type, context)
        level = engine.get_confidence_level(evidence.final_score)
        requires_approval = engine.requires_human_approval(evidence.final_score)

        print(f"{edge_type.value:<25} {evidence.final_score:<12.2f} " f"{level.value:<10} {str(requires_approval):<5}")
    print()


def example_4_cross_boundary_taint():
    """
    Example 4: Cross-Boundary Taint with Confidence

    Demonstrates tracking data flow across module boundaries.
    """
    print("=" * 60)
    print("Example 4: Cross-Boundary Taint with Confidence")
    print("=" * 60)

    builder = GraphBuilder()

    # Java POJO field
    java_field = create_node_id("java", "com.example.model", "field", "User", method="email")
    builder.add_node(java_field, metadata={"type": "String"})

    # TypeScript interface property
    ts_property = create_node_id("typescript", "src/types", "property", "UserInterface", method="email")
    builder.add_node(ts_property, metadata={"type": "string"})

    # Track taint flow with confidence
    builder.add_edge(
        from_id=str(java_field),
        to_id=str(ts_property),
        edge_type=EdgeType.TYPE_ANNOTATION,
        context={
            "status": "STALE",
            "reason": "Source field renamed from 'email' to 'emailAddress'",
        },
    )

    graph = builder.build()
    # [20240613_BUGFIX] Print the graph to use the variable and demonstrate output
    # [20260114_BUGFIX] Use to_dict() for JSON serialization
    print(json.dumps(graph.to_dict(), indent=2))

    # Display taint flow
    taint_flow = {
        "taint_flow": {
            "source": str(java_field),
            "destinations": [
                {
                    "node": str(ts_property),
                    "confidence": 0.9,
                    "status": "STALE",
                    "reason": "Source field renamed from 'email' to 'emailAddress'",
                }
            ],
        }
    }

    print(json.dumps(taint_flow, indent=2))
    print()


def example_5_http_link_detection():
    """
    Example 5: HTTP Link Detection

    Demonstrates connecting frontend API calls to backend endpoints.
    """
    print("=" * 60)
    print("Example 5: HTTP Link Detection")
    print("=" * 60)

    detector = HTTPLinkDetector()

    # Add frontend client calls
    detector.add_client_call(
        node_id="typescript::src/api/client::function::fetchUsers",
        method="GET",
        route="/api/users",
    )

    detector.add_client_call(
        node_id="typescript::src/api/client::function::createUser",
        method="POST",
        route="/api/users",
    )

    detector.add_client_call(
        node_id="typescript::src/api/client::function::getUserById",
        method="GET",
        route="/api/users/123",
    )

    # Add backend endpoints
    detector.add_endpoint(
        node_id="java::com.example.api::controller::UserController:getUsers",
        method="GET",
        route="/api/users",
    )

    detector.add_endpoint(
        node_id="java::com.example.api::controller::UserController:createUser",
        method="POST",
        route="/api/users",
    )

    detector.add_endpoint(
        node_id="java::com.example.api::controller::UserController:getUser",
        method="GET",
        route="/api/users/{id}",
    )

    # Detect links
    links = detector.detect_links()

    print(f"Found {len(links)} HTTP links:\n")
    for link in links:
        print(f"Client:     {link.client_id}")
        print(f"Endpoint:   {link.endpoint_id}")
        print(f"Method:     {link.method.value}")
        print(f"Route:      {link.client_route} -> {link.endpoint_route}")
        print(f"Confidence: {link.confidence:.2f} ({link.match_type})")
        print(f"Evidence:   {link.evidence}")
        print()


def example_6_get_dependencies():
    """
    Example 6: Get Dependencies with Confidence Filtering

    Demonstrates the agent workflow for checking dependencies.
    """
    print("=" * 60)
    print("Example 6: Get Dependencies (Agent Workflow)")
    print("=" * 60)

    builder = GraphBuilder()

    # Create a main function node
    main_node = create_node_id("python", "app", "function", "main")
    builder.add_node(main_node)

    # Add dependencies with varying confidence
    deps = [
        ("helper1", EdgeType.IMPORT_STATEMENT, {}),  # High confidence
        ("helper2", EdgeType.DIRECT_CALL, {}),  # High confidence
        ("helper3", EdgeType.DYNAMIC_ROUTE, {}),  # Low confidence
        ("helper4", EdgeType.STRING_LITERAL_MATCH, {}),  # Medium confidence
    ]

    for dep_name, edge_type, context in deps:
        dep_node = create_node_id("python", "app", "function", dep_name)
        builder.add_node(dep_node)
        builder.add_edge(str(main_node), str(dep_node), edge_type, context)

    graph = builder.build()

    # Get dependencies with threshold
    result = graph.get_dependencies(str(main_node), min_confidence=0.8)

    print("Definite dependencies (confidence >= 0.8):")
    for edge in result["definite"]:
        print(f"  - {edge.to_id}: {edge.confidence:.2f} ({edge.edge_type.value})")

    print("\nUncertain dependencies (confidence < 0.8):")
    for edge in result["uncertain"]:
        print(f"  - {edge.to_id}: {edge.confidence:.2f} ({edge.edge_type.value})")

    print(f"\nRequires human approval: {result['requires_human_approval']}")
    print()


def main():
    """Run all examples."""
    print("\n" + "=" * 60)
    print("GRAPH ENGINE EXAMPLES")
    print("Cross-Language Dependency Analysis with Confidence Scoring")
    print("=" * 60)
    print()

    example_1_universal_node_ids()
    example_2_omni_schema_graph()
    example_3_confidence_engine()
    example_4_cross_boundary_taint()
    example_5_http_link_detection()
    example_6_get_dependencies()

    print("=" * 60)
    print("All examples completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()
