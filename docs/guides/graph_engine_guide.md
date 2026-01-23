# Graph Engine Guide

**Version:** 3.0.0  
**Date:** December 18, 2025  
**Status:** Production Ready

## Overview

The Graph Engine provides a unified cross-language code graph with confidence scoring. It enables AI agents to:

1. **Universal Node IDs** - Standardize AST node identification across Python/Java/TypeScript
2. **Omni-Schema JSON** - Represent code relationships in a unified format
3. **Confidence Scoring** - Assign reliability scores (0.0-1.0) to relationships
4. **Cross-Boundary Analysis** - Track dependencies and taint flow across languages
5. **HTTP Link Detection** - Connect frontend API calls to backend endpoints

## Table of Contents

- [Quick Start](#quick-start)
- [Universal Node IDs](#universal-node-ids)
- [Confidence Engine](#confidence-engine)
- [Graph Structure](#graph-structure)
- [HTTP Link Detection](#http-link-detection)
- [API Reference](#api-reference)
- [Examples](#examples)

---

## Quick Start

```python
from code_scalpel.graph_engine import (
    GraphBuilder,
    create_node_id,
    EdgeType,
    HTTPLinkDetector,
)

# Create a graph builder
builder = GraphBuilder()

# Add nodes for different languages
python_node = create_node_id("python", "app.handlers", "class", "RequestHandler")
java_node = create_node_id("java", "com.example", "controller", "UserController", method="getUser")

builder.add_node(python_node)
builder.add_node(java_node)

# Add edge with automatic confidence scoring
builder.add_edge(
    from_id=str(python_node),
    to_id=str(java_node),
    edge_type=EdgeType.HTTP_CALL,
    context={"route_match": "exact"}
)

# Build and export
graph = builder.build()
print(graph.to_json())
```

---

## Universal Node IDs

### Format

```
language::module::type::name[:method]
```

### Components

| Component | Description | Example |
|-----------|-------------|---------|
| `language` | Programming language | `python`, `java`, `typescript`, `javascript` |
| `module` | Module/package path | `app.handlers`, `com.example.api` |
| `type` | Node type | `function`, `class`, `method`, `endpoint` |
| `name` | Element name | `RequestHandler`, `UserController` |
| `method` | Optional method name | `getUser`, `createUser` |

### Examples

```python
# Python class
"python::app.handlers::class::RequestHandler"

# Java method
"java::com.example.api::controller::UserController:getUser"

# TypeScript function
"typescript::src/api/client::function::fetchUsers"

# JavaScript endpoint
"javascript::routes/users::endpoint::getUsersRoute"
```

### Creating Node IDs

```python
from code_scalpel.graph_engine import create_node_id, NodeType

# Using string type
node_id = create_node_id(
    language="python",
    module="app.handlers",
    node_type="class",
    name="RequestHandler"
)

# Using enum type
node_id = create_node_id(
    language="java",
    module="com.example.api",
    node_type=NodeType.METHOD,
    name="UserController",
    method="getUser",
    line=42,
    file="UserController.java"
)

print(str(node_id))
# Output: java::com.example.api::method::UserController:getUser
```

### Parsing Node IDs

```python
from code_scalpel.graph_engine import parse_node_id

node_id = parse_node_id("java::com.example.api::controller::UserController:getUser")

print(node_id.language)  # "java"
print(node_id.module)    # "com.example.api"
print(node_id.node_type) # NodeType.CONTROLLER
print(node_id.name)      # "UserController"
print(node_id.method)    # "getUser"
```

---

## Confidence Engine

The Confidence Engine assigns reliability scores (0.0-1.0) to relationships between code elements.

### Confidence Levels

| Level | Score Range | Description | Human Approval |
|-------|-------------|-------------|----------------|
| **DEFINITE** | 1.0 | Certain relationship | Not required |
| **HIGH** | 0.8-0.99 | Very likely correct | Optional |
| **MEDIUM** | 0.5-0.79 | Moderately confident | Recommended |
| **LOW** | 0.3-0.49 | Uncertain | Required |
| **UNCERTAIN** | < 0.3 | Very uncertain | Block until reviewed |

### Confidence Rules

```python
CONFIDENCE_RULES = {
    # Definite relationships (1.0)
    "import_statement": 1.0,      # import X from Y - definite
    "type_annotation": 1.0,       # User: UserType - definite
    "inheritance": 1.0,           # extends/implements - definite
    
    # High confidence (0.8-0.95)
    "route_exact_match": 0.95,    # "/api/users" == "/api/users"
    "route_pattern_match": 0.8,   # "/api/users/{id}" ~= "/api/users/123"
    "direct_call": 0.95,          # function() - direct call
    
    # Medium confidence (0.5-0.7)
    "string_literal_match": 0.7,  # Heuristic based on string content
    "field_access": 0.85,         # object.field
    
    # Low confidence (0.3-0.5)
    "dynamic_route": 0.5,         # "/api/" + version + "/user" - uncertain
    "indirect_call": 0.6,         # Callback, higher-order function
}
```

### Using the Confidence Engine

```python
from code_scalpel.graph_engine import ConfidenceEngine, EdgeType

engine = ConfidenceEngine(min_threshold=0.8)

# Score an edge
evidence = engine.score_edge(
    EdgeType.HTTP_CALL,
    context={"route_match": "exact", "typed_client": True}
)

print(f"Confidence: {evidence.final_score:.2f}")
print(f"Level: {engine.get_confidence_level(evidence.final_score).value}")
print(f"Explanation: {evidence.explanation}")
print(f"Requires approval: {engine.requires_human_approval(evidence.final_score)}")
```

### Context-Based Adjustments

The confidence engine adjusts scores based on context:

```python
# HTTP Call with exact route match
context = {
    "route_match": "exact",      # +0.15 to base score
    "typed_client": True,        # +0.05 to base score
}
evidence = engine.score_edge(EdgeType.HTTP_CALL, context)
# Base: 0.8, Adjustments: +0.20, Final: 1.0

# Route pattern with multiple matches
context = {
    "exact_match": True,         # +0.15
    "match_count": 3,            # -0.20 (penalty for ambiguity)
}
evidence = engine.score_edge(EdgeType.ROUTE_PATTERN_MATCH, context)
# Base: 0.8, Final: 0.75

# String match with URL pattern
context = {
    "string_length": 30,         # +0.10 (long strings are specific)
    "is_url_pattern": True,      # +0.10 (URLs are reliable)
}
evidence = engine.score_edge(EdgeType.STRING_LITERAL_MATCH, context)
# Base: 0.7, Final: 0.9
```

---

## Graph Structure

### Omni-Schema JSON Format

```json
{
  "graph": {
    "nodes": [
      {
        "id": "java::UserController:getUser",
        "language": "java",
        "module": "com.example.api",
        "type": "endpoint",
        "name": "UserController",
        "method": "getUser",
        "route": "/api/users",
        "line": 42
      },
      {
        "id": "typescript::fetchUsers",
        "language": "typescript",
        "module": "src/api/client",
        "type": "client",
        "name": "fetchUsers",
        "target": "/api/users"
      }
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
  },
  "metadata": {
    "project": "example-api",
    "timestamp": "2025-12-16T10:00:00Z"
  }
}
```

### Building Graphs

```python
from code_scalpel.graph_engine import GraphBuilder, EdgeType

builder = GraphBuilder()

# Add nodes
java_endpoint = create_node_id("java", "com.example", "endpoint", "UserController", method="getUser")
builder.add_node(java_endpoint, metadata={"route": "/api/users", "method": "GET"})

ts_client = create_node_id("typescript", "src/api", "client", "fetchUsers")
builder.add_node(ts_client, metadata={"target": "/api/users"})

# Add edges with automatic confidence scoring
builder.add_edge(
    from_id=str(ts_client),
    to_id=str(java_endpoint),
    edge_type=EdgeType.HTTP_CALL,
    context={"route_match": "exact"}
)

# Build final graph
graph = builder.build()

# Export to JSON
json_output = graph.to_json(indent=2)
print(json_output)

# Or get as dictionary
graph_dict = graph.to_dict()
```

### Querying Graphs

```python
# Get a specific node
node = graph.get_node("java::UserController:getUser")
print(node.metadata)

# Get outgoing edges
edges_from = graph.get_edges_from("typescript::fetchUsers")
for edge in edges_from:
    print(f"{edge.from_id} -> {edge.to_id}: {edge.confidence}")

# Get incoming edges
edges_to = graph.get_edges_to("java::UserController:getUser")

# Get dependencies with confidence filtering
deps = graph.get_dependencies("typescript::fetchUsers", min_confidence=0.8)
print(f"Definite: {len(deps['definite'])}")
print(f"Uncertain: {len(deps['uncertain'])}")
print(f"Requires approval: {deps['requires_human_approval']}")
```

---

## HTTP Link Detection

The HTTP Link Detector connects frontend API calls to backend endpoints.

### Detection Patterns

**Client-side patterns:**
```python
HTTP_CLIENT_PATTERNS = {
    "javascript": ["fetch", "axios.get", "axios.post", "$http", "ajax"],
    "typescript": ["fetch", "axios", "HttpClient"],
    "python": ["requests.get", "requests.post", "httpx.get"],
}
```

**Server-side patterns:**
```python
HTTP_ENDPOINT_PATTERNS = {
    "java": ["@GetMapping", "@PostMapping", "@RequestMapping", "@RestController"],
    "python": ["@app.route", "@router.get", "@api_view"],
    "typescript": ["@Get", "@Post", "@Controller"],
}
```

### Using the Detector

```python
from code_scalpel.graph_engine import HTTPLinkDetector, HTTPMethod

detector = HTTPLinkDetector()

# Add client-side calls
detector.add_client_call(
    node_id="typescript::src/api/client::function::fetchUsers",
    method="GET",
    route="/api/users"
)

detector.add_client_call(
    node_id="typescript::src/api/client::function::getUserById",
    method="GET",
    route="/api/users/123"
)

# Add server-side endpoints
detector.add_endpoint(
    node_id="java::com.example.api::controller::UserController:getUsers",
    method="GET",
    route="/api/users"
)

detector.add_endpoint(
    node_id="java::com.example.api::controller::UserController:getUser",
    method="GET",
    route="/api/users/{id}"
)

# Detect links
links = detector.detect_links()

for link in links:
    print(f"Client: {link.client_id}")
    print(f"Endpoint: {link.endpoint_id}")
    print(f"Confidence: {link.confidence:.2f} ({link.match_type})")
    print(f"Evidence: {link.evidence}")
    print()
```

### Route Matching

The detector supports three types of route matching:

1. **Exact Match** (confidence: 0.95)
   ```
   Client: /api/users
   Server: /api/users
   → Match: exact
   ```

2. **Pattern Match** (confidence: 0.8)
   ```
   Client: /api/users/123
   Server: /api/users/{id}
   → Match: pattern
   ```

3. **Dynamic Match** (confidence: 0.5)
   ```
   Client: "/api/" + version + "/users"
   Server: /api/v1/users
   → Match: dynamic (fuzzy)
   ```

### Finding Unmatched Elements

```python
# Get client calls with no matching endpoints
unmatched_clients = detector.get_unmatched_clients()
for client in unmatched_clients:
    print(f"Unmatched client: {client['node_id']} - {client['route']}")

# Get endpoints with no matching clients
unmatched_endpoints = detector.get_unmatched_endpoints()
for endpoint in unmatched_endpoints:
    print(f"Unmatched endpoint: {endpoint['node_id']} - {endpoint['route']}")
```

---

## API Reference

### Node ID Functions

```python
def create_node_id(
    language: str,
    module: str,
    node_type: str | NodeType,
    name: str,
    method: Optional[str] = None,
    line: Optional[int] = None,
    file: Optional[str] = None,
) -> UniversalNodeID
```

```python
def parse_node_id(id_string: str) -> UniversalNodeID
```

### GraphBuilder Methods

```python
class GraphBuilder:
    def add_node(
        self,
        node_id: UniversalNodeID,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> GraphNode
    
    def add_edge(
        self,
        from_id: str,
        to_id: str,
        edge_type: EdgeType,
        context: Optional[Dict[str, Any]] = None,
    ) -> GraphEdge
    
    def build(self) -> UniversalGraph
    
    def reset(self) -> None
```

### UniversalGraph Methods

```python
class UniversalGraph:
    def add_node(self, node: GraphNode) -> None
    
    def add_edge(self, edge: GraphEdge) -> None
    
    def get_node(self, node_id: str) -> Optional[GraphNode]
    
    def get_edges_from(self, node_id: str) -> List[GraphEdge]
    
    def get_edges_to(self, node_id: str) -> List[GraphEdge]
    
    def get_dependencies(
        self,
        node_id: str,
        min_confidence: float = 0.8
    ) -> Dict[str, List[GraphEdge]]
    
    def to_dict(self) -> dict
    
    def to_json(self, indent: int = 2) -> str
    
    @staticmethod
    def from_dict(data: dict) -> UniversalGraph
    
    @staticmethod
    def from_json(json_str: str) -> UniversalGraph
```

### ConfidenceEngine Methods

```python
class ConfidenceEngine:
    def __init__(self, min_threshold: float = 0.8)
    
    def score_edge(
        self,
        edge_type: EdgeType,
        context: Dict[str, Any]
    ) -> ConfidenceEvidence
    
    def get_confidence_level(self, score: float) -> ConfidenceLevel
    
    def requires_human_approval(self, score: float) -> bool
```

### HTTPLinkDetector Methods

```python
class HTTPLinkDetector:
    def add_client_call(
        self,
        node_id: str,
        method: str | HTTPMethod,
        route: str,
        metadata: Optional[Dict] = None,
    ) -> None
    
    def add_endpoint(
        self,
        node_id: str,
        method: str | HTTPMethod,
        route: str,
        metadata: Optional[Dict] = None,
    ) -> None
    
    def detect_links(self) -> List[HTTPLink]
    
    def get_unmatched_clients(self) -> List[Dict]
    
    def get_unmatched_endpoints(self) -> List[Dict]
```

---

## Examples

Complete examples are available in `examples/graph_engine_example.py`.

### Example 1: Cross-Language Graph

```python
from code_scalpel.graph_engine import GraphBuilder, create_node_id, EdgeType

builder = GraphBuilder()

# Python backend
python_api = create_node_id("python", "app.api", "endpoint", "get_users")
builder.add_node(python_api, metadata={"route": "/api/users", "method": "GET"})

# TypeScript frontend
ts_client = create_node_id("typescript", "src/api", "client", "fetchUsers")
builder.add_node(ts_client)

# Connect with confidence
builder.add_edge(
    from_id=str(ts_client),
    to_id=str(python_api),
    edge_type=EdgeType.HTTP_CALL,
    context={"route_match": "exact"}
)

graph = builder.build()
print(graph.to_json())
```

### Example 2: Taint Flow Analysis

```python
# Source: Java field
java_field = create_node_id("java", "com.example", "field", "User", method="email")
builder.add_node(java_field)

# Sink: TypeScript property
ts_property = create_node_id("typescript", "types", "property", "UserInterface", method="email")
builder.add_node(ts_property)

# Track taint flow
builder.add_edge(
    from_id=str(java_field),
    to_id=str(ts_property),
    edge_type=EdgeType.TYPE_ANNOTATION,
    context={"status": "STALE"}
)

graph = builder.build()
deps = graph.get_dependencies(str(java_field))
```

---

## Integration with MCP Server

The Graph Engine can be integrated into MCP tools for cross-language analysis:

```python
@mcp.tool()
async def analyze_cross_language_dependencies(
    entry_point: str,
    languages: list[str] = ["python", "java", "typescript"]
) -> dict:
    """Analyze dependencies across multiple languages."""
    builder = GraphBuilder()
    
    # Build graph from multiple language files
    # ... (language-specific parsing logic)
    
    graph = builder.build()
    
    # Return analysis with confidence scores
    return {
        "graph": graph.to_dict(),
        "summary": {
            "total_nodes": len(graph.nodes),
            "total_edges": len(graph.edges),
            "languages": languages,
        }
    }
```

---

## Best Practices

1. **Use Appropriate Confidence Thresholds**
   - Critical operations: 0.9+
   - Automated refactoring: 0.8+
   - Exploratory analysis: 0.5+

2. **Request Human Approval for Low Confidence**
   ```python
   deps = graph.get_dependencies(node_id, min_confidence=0.8)
   if deps['requires_human_approval']:
       # Show uncertain dependencies to user
       for edge in deps['uncertain']:
           print(f"Please confirm: {edge.evidence}")
   ```

3. **Provide Context for Better Scoring**
   ```python
   # Good: Provide routing context
   builder.add_edge(
       from_id, to_id, EdgeType.HTTP_CALL,
       context={"route_match": "exact", "typed_client": True}
   )
   
   # Bad: No context
   builder.add_edge(from_id, to_id, EdgeType.HTTP_CALL)
   ```

4. **Use Metadata for Additional Information**
   ```python
   builder.add_node(
       node_id,
       metadata={
           "file": "UserController.java",
           "line": 42,
           "route": "/api/users",
           "method": "GET",
           "return_type": "List<User>",
       }
   )
   ```

---

## Troubleshooting

### Issue: Low Confidence Scores

**Problem:** All edges have low confidence scores.

**Solution:** Provide more context when creating edges:
```python
# Instead of:
builder.add_edge(from_id, to_id, EdgeType.HTTP_CALL, {})

# Use:
builder.add_edge(
    from_id, to_id, EdgeType.HTTP_CALL,
    context={"route_match": "exact", "typed_client": True}
)
```

### Issue: Routes Not Matching

**Problem:** HTTP detector not finding links between client and server.

**Solution:** Check route formats and HTTP methods:
```python
# Ensure routes match format
detector.add_client_call("ts::fetch", "GET", "/api/users")  # [COMPLETE] Correct
detector.add_endpoint("java::getUsers", "GET", "/api/users")  # [COMPLETE] Correct

# Not: detector.add_client_call("ts::fetch", "GET", "api/users")  # [FAILED] Missing /
```

### Issue: Node IDs Not Parsing

**Problem:** `ValueError: Invalid node ID format`

**Solution:** Ensure correct format with 4 components:
```python
# Correct formats:
"python::app.handlers::class::RequestHandler"
"java::com.example::controller::UserController:getUser"

# Incorrect:
"python::app.handlers::RequestHandler"  # Missing node type
"python::app::handlers::class::RequestHandler"  # Extra component
```

---

## Performance Considerations

- **Graph Size**: Graph operations are O(n) for nodes, O(m) for edges
- **Confidence Scoring**: Edge scoring is O(1) with context adjustments
- **HTTP Detection**: Route matching is O(n×m) where n=clients, m=endpoints
- **Serialization**: JSON export scales linearly with graph size

For large projects:
- Build graphs incrementally
- Use graph databases for persistence (Neo4j, etc.)
- Cache confidence scores for repeated edge types

---

## Future Enhancements

- [ ] Graph database persistence (Neo4j, etc.)
- [ ] Advanced route pattern matching (regex, wildcards)
- [ ] ML-based confidence scoring
- [ ] Visualization tools (Mermaid, GraphViz)
- [ ] Real-time graph updates
- [ ] Cross-project dependency tracking

---

## See Also

- [Examples](../examples/graph_engine_example.py)
- [API Tests](../tests/test_graph_engine_*.py)
- [MCP Server Integration](mcp_server_guide.md)
- [Security Analysis](security_analysis.md)
