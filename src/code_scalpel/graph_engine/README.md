# Graph Engine Module

**Purpose:** Code dependency graph construction and analysis

## TODO ITEMS: graph_engine/README.md

### COMMUNITY TIER - Core Documentation
1. Add comprehensive module overview and use cases
2. Add architecture diagram showing relationships
3. Add quick start guide with examples
4. Add installation and setup instructions
5. Add basic graph construction tutorial
6. Add node creation examples for each language
7. Add edge creation and relationship documentation
8. Add traversal algorithm examples (BFS, DFS)
9. Add JSON format specification and examples
10. Add confidence scoring explanation
11. Add HTTP link detection tutorial
12. Add universal node ID format documentation
13. Add API reference for all public methods
14. Add error handling and exceptions guide
15. Add troubleshooting section
16. Add frequently asked questions
17. Add performance characteristics table
18. Add supported languages and versions
19. Add compatibility matrix
20. Add basic examples for each major feature
21. Add code examples for common tasks
22. Add best practices guide
23. Add security checklist
24. Add limitations and known issues
25. Add migration guide from other systems

### PRO TIER - Advanced Documentation
26. Add advanced graph analysis techniques
27. Add performance tuning guide
28. Add scaling strategies for large graphs
29. Add caching optimization
30. Add memory optimization techniques
31. Add distributed graph processing
32. Add custom node type registration
33. Add custom edge type registration
34. Add graph visualization guide
35. Add export format options
36. Add import format options
37. Add graph comparison and diffing
38. Add incremental update procedures
39. Add graph versioning strategies
40. Add backup and recovery procedures
41. Add monitoring and observability
42. Add debugging techniques
43. Add performance profiling
44. Add benchmarking methodology
45. Add cost analysis
46. Add optimization patterns
47. Add testing strategies
48. Add integration with other tools
49. Add extension points documentation
50. Add advanced confidence scoring

### ENTERPRISE TIER - Enterprise Guidance
51. Add enterprise architecture patterns
52. Add high availability configuration
53. Add disaster recovery setup
54. Add multi-region deployment
55. Add data residency options
56. Add encryption configuration
57. Add key management guide
58. Add audit logging setup
59. Add compliance documentation (HIPAA, SOC2, GDPR)
60. Add access control configuration
61. Add RBAC setup guide
62. Add SSO/SAML integration
63. Add multi-factor authentication
64. Add network security setup
65. Add VPC configuration
66. Add firewall rules
67. Add DDoS protection
68. Add rate limiting configuration
69. Add service mesh integration (Istio, Linkerd)
70. Add API gateway integration
71. Add monitoring and alerting setup
72. Add distributed tracing (OpenTelemetry)
73. Add performance SLA documentation
74. Add capacity planning guide
75. Add commercial support and licensing

## Overview

This module provides graph-based code analysis for:
- Cross-file dependency tracking
- Call graph construction
- Confidence-based edge weighting
- HTTP endpoint detection and mapping
- Node ID generation and resolution

## Key Components

### graph.py (16,409 LOC)
Core graph construction and analysis:
- `CodeGraph` - Unified dependency graph structure
- `GraphNode` - Represents functions, classes, modules
- `GraphEdge` - Represents dependencies with confidence scores
- Graph traversal algorithms (BFS, DFS, k-hop neighborhood)
- Import resolution and cross-file tracking

**Key Features:**
- Multi-language support (Python, Java, TypeScript, JavaScript)
- Confidence decay for deep dependencies
- Circular import detection
- Subgraph extraction for focused analysis

### confidence.py (9,175 LOC)
Confidence scoring for graph edges:
- `ConfidenceCalculator` - Computes edge confidence
- Depth-based confidence decay (exponential falloff)
- Type inference confidence
- Import resolution confidence
- Default: 0.9^depth decay factor

**Formula:** `C_effective = 1.0 × 0.9^depth`

### http_detector.py (13,316 LOC)
HTTP endpoint detection and tracking:
- Detects Flask/FastAPI/Django routes
- Maps endpoints to handler functions
- Tracks request parameter flow
- Correlates frontend fetch() calls with backend routes

**Key Features:**
- Detects `@app.route`, `@app.get`, `@router.post`, etc.
- Extracts path parameters (`/users/<id>`)
- Identifies request sources (`request.json`, `request.args`)

### node_id.py (6,431 LOC)
Canonical node ID generation:
- `NodeIdGenerator` - Creates unique node identifiers
- Format: `language::module::type::name`
- Example: `python::services::function::process_order`
- Ensures consistent IDs across analysis runs

## Usage

```python
from code_scalpel.graph_engine import CodeGraph, ConfidenceCalculator

# Build graph from project
graph = CodeGraph(project_root="/path/to/project")
graph.build()

# Get k-hop neighborhood
subgraph = graph.get_neighborhood(
    center_node="python::services::function::process_order",
    k=2,
    min_confidence=0.5
)

# Calculate confidence
calc = ConfidenceCalculator()
confidence = calc.calculate_edge_confidence(
    source_node=node1,
    target_node=node2,
    depth=3
)
```

## Integration

Used by:
- `mcp/server.py` - MCP tools: `get_call_graph`, `get_graph_neighborhood`, `get_cross_file_dependencies`
- `symbolic_execution_tools/cross_file_taint.py` - Cross-file taint tracking
- `policy_engine/` - Dependency-based policy enforcement

## v3.0.5 Status

- Graph construction: Stable, 95%+ coverage
- Confidence scoring: Stable
- HTTP detection: Stable
- Supports Python, Java, TypeScript, JavaScript
