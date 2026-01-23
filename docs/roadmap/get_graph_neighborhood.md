# get_graph_neighborhood Tool Roadmap

**Tool Name:** `get_graph_neighborhood`  
**Tool Version:** v1.0  
**Code Scalpel Version:** v3.3.1  
**Current Status:** Stable  
**Primary Module:** `src/code_scalpel/mcp/server.py`  
**Tier Availability:** All tiers (Community, Pro, Enterprise)

---

## Configuration Files

| File | Purpose |
|------|---------|
| `src/code_scalpel/licensing/features.py` | Tier capability definitions |
| `.code-scalpel/limits.toml` | Numeric limits (max_k, max_nodes) |
| `.code-scalpel/response_config.json` | Output filtering (exclude metadata) |

---

## Overview

The `get_graph_neighborhood` tool extracts k-hop neighborhood subgraphs around a center node, preventing graph explosion for large codebases.

**Why AI Agents Need This:**
- **Focused Analysis:** Analyze only relevant code, not entire codebase
- **Memory Safety:** Prevent OOM on large graphs with truncation protection
- **Honest Uncertainty:** Know when graph is incomplete via truncation warnings
- **Impact Assessment:** Understand local blast radius before making changes
- **Dependency Tracing:** Follow call chains without loading full project graph

---

## Research Queries for Future Development

### Foundational Research
| Topic | Query | Purpose |
|-------|-------|---------|
| Graph Algorithms | "k-hop neighborhood extraction algorithms comparison" | Optimize traversal |
| Pruning Strategies | "graph pruning heuristics for code analysis" | Improve truncation |
| Subgraph Matching | "subgraph isomorphism algorithms practical performance" | Pattern matching |
| Memory Efficiency | "memory-efficient graph representation for program analysis" | Scale to large projects |

### Language-Specific Research
| Topic | Query | Purpose |
|-------|-------|---------|
| Call Graph Construction | "call graph construction precision recall tradeoffs" | Better edge detection |
| Dynamic Calls | "static analysis dynamic dispatch resolution techniques" | Handle polymorphism |
| Closure Analysis | "closure and lambda call graph edges detection" | Improve JS/Python support |
| Decorator Analysis | "python decorator call graph impact" | Better Python modeling |

### Advanced Techniques
| Topic | Query | Purpose |
|-------|-------|---------|
| Graph Neural Networks | "graph neural networks code representation learning" | AI-enhanced analysis |
| Semantic Similarity | "semantic code similarity neural approaches" | Improve semantic neighbors |
| Community Detection | "community detection algorithms software graphs" | Auto-cluster related code |
| Incremental Updates | "incremental graph algorithms single node update" | Real-time IDE support |

---

## Current Capabilities (v1.0)

### Community Tier (World-Class Base Features)
- ✅ k-hop neighborhood extraction (k=1 max)
- ✅ Direction filtering (incoming, outgoing, both)
- ✅ Confidence threshold filtering (`min_confidence`)
- ✅ Mermaid diagram generation
- ✅ Truncation protection with warnings
- ✅ Node depth tracking
- ✅ Edge metadata (type, confidence)

**Capability Key:** `basic_neighborhood`

**Limits:**
- `max_k: 1` (immediate neighbors only)
- `max_nodes: 20`

### Pro Tier (Semantic Intelligence)
- ✅ All Community features
- ✅ Extended k-hop (k=5 max)
- ✅ **Semantic neighbor detection** (`semantic_neighbors`)
  - Finds functionally similar nodes via name/docstring similarity
  - Returns similarity scores and relationship types
- ✅ **Logical relationship inference** (`logical_relationship_detection`)
  - Detects caller/callee, producer/consumer, factory patterns
  - Adds logical edges with evidence strings
- ✅ Advanced caching (per cache_variant)

**Capability Keys:** `basic_neighborhood`, `advanced_neighborhood`, `semantic_neighbors`, `logical_relationship_detection`

**Limits:**
- `max_k: 5`
- `max_nodes: 100`

### Enterprise Tier (Query & Scale)
- ✅ All Pro features
- ✅ **Unlimited k and nodes** (no limits)
- ✅ **Graph query language** (`graph_query_language`)
  - Cypher-like syntax for custom traversals
  - Pattern matching across node types
  - Bounded result sets
- ✅ **Custom traversal rules** (`custom_traversal_rules`)
  - Define edge weight priorities
  - Filter by edge type
- ✅ **Path constraint queries** (`path_constraint_queries`)
  - Find paths matching specific patterns
- ✅ **Hot node detection** (high-degree nodes in subgraph)
- ✅ In/out degree metrics per node

**Capability Keys:** All Pro + `custom_traversal`, `weighted_paths`, `graph_query_language`, `custom_traversal_rules`, `path_constraint_queries`

**Limits:** None (unlimited)

---

## Return Model: GraphNeighborhoodResult

```python
class GraphNeighborhoodResult(BaseModel):
    # Core fields (All Tiers)
    success: bool                           # Whether extraction succeeded
    center_node_id: str                     # ID of the center node
    k: int                                  # Number of hops used (may be limited)
    nodes: list[NeighborhoodNodeModel]      # Nodes with id, depth, metadata
    edges: list[NeighborhoodEdgeModel]      # Edges with from_id, to_id, type, confidence
    total_nodes: int                        # Total nodes in subgraph
    total_edges: int                        # Total edges in subgraph
    max_depth_reached: int                  # Actual max depth reached
    truncated: bool                         # Whether truncation occurred
    truncation_warning: str | None          # Warning message if truncated
    mermaid: str                            # Mermaid diagram of neighborhood
    
    # Pro Tier
    semantic_neighbors: list[str]           # Semantic neighbor node IDs (best-effort)
    logical_relationships: list[dict]       # Detected logical relationships
    
    # Enterprise Tier
    query_supported: bool                   # Whether query language is available
    traversal_rules_available: bool         # Custom traversal rules supported
    path_constraints_supported: bool        # Path constraint queries supported
    hot_nodes: list[str]                    # High-degree nodes in subgraph
    
    error: str | None                       # Error message if failed
```

---

## Usage Examples

### Community Tier
```python
result = await get_graph_neighborhood(
    center_node_id="python::services::function::process_order",
    k=1,  # Will be limited to 1 anyway
    max_nodes=20  # Will be limited to 20 anyway
)
# Returns: nodes, edges, mermaid diagram, truncation info
```

### Pro Tier
```python
result = await get_graph_neighborhood(
    center_node_id="python::services::function::process_order",
    k=3,  # Up to 5 allowed
    max_nodes=50,
    direction="outgoing",
    min_confidence=0.5
)
# Additional: semantic_neighbors, logical_relationships populated
```

### Enterprise Tier
```python
# Standard extraction (unlimited)
result = await get_graph_neighborhood(
    center_node_id="python::services::function::process_order",
    k=10,  # No limit
    max_nodes=1000  # No limit
)

# Query language
result = await get_graph_neighborhood(
    center_node_id="python::controllers::function::handle_request",
    query="MATCH (n)-[:calls]->(m:function) WHERE m.name CONTAINS 'DB' RETURN n, m"
)
# Returns: query_supported=True, traversal_rules_available=True, hot_nodes populated
```

---

## MCP Request/Response Examples

### MCP Request Format

```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "mcp_code-scalpel_get_graph_neighborhood",
    "arguments": {
      "center_node_id": "python::services::function::process_order",
      "k": 2,
      "max_nodes": 50,
      "direction": "both",
      "min_confidence": 0.5
    }
  },
  "id": 1
}
```

### Community Tier Response

```json
{
  "jsonrpc": "2.0",
  "result": {
    "success": true,
    "center_node_id": "python::services::function::process_order",
    "k": 1,
    "nodes": [
      {
        "id": "python::services::function::process_order",
        "depth": 0,
        "file": "services/order.py",
        "line": 45,
        "type": "function"
      },
      {
        "id": "python::services::function::validate_order",
        "depth": 1,
        "file": "services/order.py",
        "line": 20,
        "type": "function"
      },
      {
        "id": "python::db::function::save_order",
        "depth": 1,
        "file": "db/queries.py",
        "line": 100,
        "type": "function"
      }
    ],
    "edges": [
      {
        "from_id": "python::services::function::process_order",
        "to_id": "python::services::function::validate_order",
        "type": "calls",
        "confidence": 0.95
      },
      {
        "from_id": "python::services::function::process_order",
        "to_id": "python::db::function::save_order",
        "type": "calls",
        "confidence": 0.92
      }
    ],
    "total_nodes": 3,
    "total_edges": 2,
    "max_depth_reached": 1,
    "truncated": false,
    "truncation_warning": null,
    "mermaid": "graph TD\n  process_order[process_order] --> validate_order[validate_order]\n  process_order --> save_order[save_order]"
  },
  "id": 1
}
```

### Pro Tier Response

```json
{
  "jsonrpc": "2.0",
  "result": {
    "success": true,
    "center_node_id": "python::services::function::process_order",
    "k": 3,
    "nodes": [
      {
        "id": "python::services::function::process_order",
        "depth": 0,
        "file": "services/order.py",
        "line": 45,
        "type": "function"
      },
      {
        "id": "python::services::function::validate_order",
        "depth": 1,
        "file": "services/order.py",
        "line": 20,
        "type": "function"
      },
      {
        "id": "python::db::function::save_order",
        "depth": 1,
        "file": "db/queries.py",
        "line": 100,
        "type": "function"
      },
      {
        "id": "python::models::class::Order",
        "depth": 2,
        "file": "models/order.py",
        "line": 10,
        "type": "class"
      }
    ],
    "edges": [
      {
        "from_id": "python::services::function::process_order",
        "to_id": "python::services::function::validate_order",
        "type": "calls",
        "confidence": 0.95
      },
      {
        "from_id": "python::services::function::process_order",
        "to_id": "python::db::function::save_order",
        "type": "calls",
        "confidence": 0.92
      },
      {
        "from_id": "python::db::function::save_order",
        "to_id": "python::models::class::Order",
        "type": "uses",
        "confidence": 0.88
      }
    ],
    "total_nodes": 4,
    "total_edges": 3,
    "max_depth_reached": 2,
    "truncated": false,
    "truncation_warning": null,
    "mermaid": "graph TD\n  subgraph services\n    process_order --> validate_order\n  end\n  subgraph db\n    save_order\n  end\n  process_order --> save_order\n  save_order --> Order[Order]",
    "semantic_neighbors": [
      "python::services::function::cancel_order",
      "python::services::function::update_order"
    ],
    "logical_relationships": [
      {
        "type": "producer_consumer",
        "from": "process_order",
        "to": "save_order",
        "evidence": "Order object passed from process_order to save_order"
      },
      {
        "type": "validator",
        "from": "validate_order",
        "to": "process_order",
        "evidence": "validate_order called before main processing"
      }
    ]
  },
  "id": 1
}
```

### Enterprise Tier Response

```json
{
  "jsonrpc": "2.0",
  "result": {
    "success": true,
    "center_node_id": "python::services::function::process_order",
    "k": 10,
    "nodes": [
      {
        "id": "python::services::function::process_order",
        "depth": 0,
        "file": "services/order.py",
        "line": 45,
        "type": "function",
        "in_degree": 5,
        "out_degree": 8
      },
      {
        "id": "python::db::function::save_order",
        "depth": 1,
        "file": "db/queries.py",
        "line": 100,
        "type": "function",
        "in_degree": 12,
        "out_degree": 3
      }
    ],
    "edges": [],
    "total_nodes": 45,
    "total_edges": 78,
    "max_depth_reached": 8,
    "truncated": false,
    "truncation_warning": null,
    "mermaid": "graph TD\n  classDef hotNode fill:#ff6b6b\n  process_order --> validate_order\n  process_order --> save_order:::hotNode\n  ...",
    "semantic_neighbors": [
      "python::services::function::cancel_order",
      "python::services::function::update_order",
      "python::services::function::refund_order"
    ],
    "logical_relationships": [
      {
        "type": "producer_consumer",
        "from": "process_order",
        "to": "save_order",
        "evidence": "Order object passed from process_order to save_order"
      }
    ],
    "query_supported": true,
    "traversal_rules_available": true,
    "path_constraints_supported": true,
    "hot_nodes": [
      "python::db::function::save_order",
      "python::utils::function::log_event"
    ]
  },
  "id": 1
}
```

### Enterprise Tier Response (with Query)

```json
{
  "jsonrpc": "2.0",
  "result": {
    "success": true,
    "center_node_id": "python::controllers::function::handle_request",
    "k": 5,
    "query": "MATCH (n)-[:calls]->(m:function) WHERE m.name CONTAINS 'DB' RETURN n, m",
    "query_executed": true,
    "nodes": [
      {
        "id": "python::controllers::function::handle_request",
        "depth": 0,
        "type": "function"
      },
      {
        "id": "python::db::function::queryDB",
        "depth": 2,
        "type": "function",
        "matched_query": true
      }
    ],
    "edges": [
      {
        "from_id": "python::controllers::function::handle_request",
        "to_id": "python::services::function::get_data",
        "type": "calls"
      },
      {
        "from_id": "python::services::function::get_data",
        "to_id": "python::db::function::queryDB",
        "type": "calls"
      }
    ],
    "total_nodes": 3,
    "total_edges": 2,
    "query_supported": true,
    "traversal_rules_available": true,
    "path_constraints_supported": true
  },
  "id": 1
}
```

---

## Roadmap

### v1.1 (Q1 2026): Enhanced Traversal

#### Community Tier
- [x] ~~Edge metadata in results~~ (Done in v1.0)
- [ ] Better truncation warnings with suggestions
- [ ] Multiple center node support

#### Pro Tier
- [ ] Path-constrained neighborhoods
- [ ] Weighted k-hop (by importance score)
- [ ] Time-aware neighborhoods (recent changes prioritized)

#### Enterprise Tier
- [ ] Graph pattern matching (isomorphism)
- [ ] Distributed graph operations
- [ ] Historical graph snapshots

### v1.2 (Q2 2026): Visualization & Export

#### All Tiers
- [ ] GraphViz DOT export
- [ ] Interactive HTML visualization
- [ ] JSON graph export (standard format)

#### Pro Tier
- [ ] Real-time graph exploration
- [ ] 3D force-directed visualization

#### Enterprise Tier
- [ ] Custom visualization templates
- [ ] Dashboard integration
- [ ] Embedding in reports

### v1.3 (Q3 2026): Performance Optimization

#### All Tiers
- [ ] Faster neighborhood extraction (<100ms)
- [ ] Memory optimization for large graphs
- [ ] Incremental graph updates

#### Pro Tier
- [x] ~~Smart caching strategies~~ (Done in v1.0)
- [ ] Parallel graph operations
- [ ] Delta neighborhood computation

#### Enterprise Tier
- [ ] Distributed graph storage
- [ ] Graph sharding for massive codebases
- [ ] Real-time graph streaming

### v1.4 (Q4 2026): Advanced Features

#### Pro Tier
- [ ] Community detection in neighborhoods
- [ ] Centrality scoring
- [ ] Graph anomaly detection

#### Enterprise Tier
- [ ] Graph machine learning features
- [ ] Predictive graph analytics
- [ ] Temporal graph analysis

---

## Known Issues & Limitations

### Current Limitations
- **Large graphs:** Very dense graphs may hit node limits
- **Complex queries:** Query language (Enterprise) has learning curve
- **Performance:** k>10 may be slow on large graphs

### Planned Fixes
- v1.1: Better density handling
- v1.2: Query builder UI
- v1.3: Performance optimization for high k

---

## Success Metrics

### Performance Targets
- **Extraction time:** <500ms for k=2, 100 nodes
- **Memory usage:** <100MB per subgraph
- **Accuracy:** >99% correct neighborhoods

### Adoption Metrics
- **Usage:** 50K+ extractions per month by Q4 2026
- **Avg k:** 2-3 hops
- **Avg nodes:** 50-100 per subgraph

---

## Integration Points

### Related Tools
| Tool | Relationship |
|------|--------------|
| `get_call_graph` | Source graph for neighborhood extraction |
| `get_symbol_references` | Complementary: references vs. graph edges |
| `cross_file_security_scan` | Uses neighborhood for focused taint analysis |
| `get_project_map` | High-level view; neighborhood provides local detail |

### Export Formats
| Format | Status | Use Case |
|--------|--------|----------|
| **Mermaid** | ✅ v1.0 | Quick visualization in docs |
| **JSON** | ✅ v1.0 | Programmatic processing |
| **GraphViz DOT** | 🔄 v1.2 | External visualization tools |
| **Cypher (Neo4j)** | 🔄 v1.3 | Graph database integration |

---

## Competitive Analysis

| Tool | Strengths | Weaknesses | Our Differentiation |
|------|-----------|------------|---------------------|
| **Joern** | Powerful CPG queries | Complex query language | Simpler k-hop API |
| **CodeQL** | GitHub integration | Steep learning curve | MCP-native, AI-friendly |
| **Sourcetrail** | Great visualization | Discontinued | Active development |
| **Neo4j + custom** | Powerful queries | Setup overhead | Zero-config, embedded |
| **NetworkX** | Python-native | Manual graph building | Pre-built code graphs |

---

## Response Configuration

Output verbosity is controlled by `.code-scalpel/response_config.json`:

```json
{
  "get_graph_neighborhood": {
    "profile": "minimal",
    "exclude_fields": ["traversal_statistics", "visited_nodes_raw"]
  }
}
```

**Profile Options:**
- `minimal` - Core fields only (~100-200 tokens)
- `standard` - Include metadata (~200-500 tokens)
- `verbose` - Full detail (~500-2000 tokens)
- `debug` - Everything including raw data

**Note:** Tier capabilities (Pro semantic neighbors, Enterprise query support) are additive - they add fields when the tier enables them. Response config controls verbosity within what the tier allows.

---

## Dependencies

### Internal Dependencies
- `mcp/server.py` - MCP tool implementation
- `graph_engine/graph.py` - Core UniversalGraph engine
- `ast_tools/call_graph.py` - CallGraphBuilder for graph construction
- `graph/semantic_neighbors.py` - SemanticNeighborFinder (Pro)
- `graph/logical_relationships.py` - LogicalRelationshipDetector (Pro)
- `graph/graph_query.py` - GraphQueryEngine (Enterprise)
- `licensing/features.py` - Tier capability definitions

### External Dependencies
- None (pure Python implementation)

---

## Breaking Changes

None planned for v1.x series.

---

**Last Updated:** December 31, 2025  
**Next Review:** March 31, 2026
