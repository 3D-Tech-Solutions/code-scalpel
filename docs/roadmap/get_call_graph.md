# get_call_graph Tool Roadmap

**Tool Name:** `get_call_graph`  
**Tool Version:** v1.0  
**Code Scalpel Version:** v3.3.0  
**Current Status:** Stable  
**Primary Module:** `src/code_scalpel/ast_tools/call_graph.py`  
**Tier Availability:** All tiers (Community, Pro, Enterprise)

---

## Overview

The `get_call_graph` tool generates call graphs showing function relationships, entry points, and circular dependencies across codebases. Call graphs are fundamental for understanding program structure, enabling refactoring impact analysis, dead code detection, and security auditing (tracking data flow paths to sensitive sinks).

### Why Call Graphs Matter for AI Agents

1. **Context Window Optimization:** Agents can request only the transitive closure of functions relevant to a task instead of loading entire files
2. **Safe Refactoring:** Before renaming or modifying a function, agents can enumerate all call sites
3. **Security Auditing:** Trace paths from untrusted inputs to dangerous sinks (SQL, exec, file operations)
4. **Architecture Understanding:** Visualize module boundaries, identify god functions, detect circular dependencies

---

## Current Capabilities (v1.0)

### Community Tier
- ✅ Function-to-function call mapping
- ✅ Entry point identification (`__main__`, CLI decorators, web framework routes, test functions)
- ✅ Circular dependency detection (import cycles and call cycles)
- ✅ Supports Python, JavaScript, TypeScript
- ✅ Basic graph visualization (Mermaid diagrams)
- ✅ Depth-limited traversal from specified entry points
- ⚠️ **Limits:** Project-wide scan with strict truncation (depth/node limits from `.code-scalpel/limits.toml`; defaults currently `max_depth=3`, `max_nodes=50`)

### Pro Tier
- ✅ All Community features
- ✅ Higher limits (defaults currently `max_depth=50`, `max_nodes=500`)
- ✅ Optional enhanced resolution when licensed via capabilities (e.g., `polymorphism_resolution`, `advanced_call_graph`)
- ✅ Better caller attribution for complex patterns (callbacks, closures)

### Enterprise Tier
- ✅ All Pro features
- ✅ Optional graph metrics when licensed via capabilities (e.g., `hot_path_identification`, `dead_code_detection`, `custom_graph_analysis`)
- ✅ Typically configured with very high/unlimited limits (via `.code-scalpel/limits.toml`)
- ✅ Integration with governance policies for architectural enforcement

---

## MCP Request/Response Examples

### MCP Request Format

```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "mcp_code-scalpel_get_call_graph",
    "arguments": {
      "project_root": "/home/user/flask-app",
      "entry_point": "main",
      "depth": 5,
      "include_circular_import_check": true
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
    "nodes": [
      {"id": "main", "file": "app.py", "line": 10, "type": "function"},
      {"id": "process_request", "file": "handlers.py", "line": 25, "type": "function"},
      {"id": "validate_input", "file": "validators.py", "line": 5, "type": "function"},
      {"id": "save_to_db", "file": "db/queries.py", "line": 42, "type": "function"}
    ],
    "edges": [
      {"from": "main", "to": "process_request", "call_site_line": 15},
      {"from": "process_request", "to": "validate_input", "call_site_line": 30},
      {"from": "process_request", "to": "save_to_db", "call_site_line": 35}
    ],
    "entry_points": [
      {"name": "main", "file": "app.py", "type": "__main__"}
    ],
    "circular_imports": [],
    "circular_calls": [],
    "mermaid_diagram": "graph TD\n  main[main] --> process_request[process_request]\n  process_request --> validate_input[validate_input]\n  process_request --> save_to_db[save_to_db]",
    "depth_reached": 3,
    "node_count": 4,
    "truncated": false,
    "truncation_reason": null
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
    "nodes": [
      {"id": "main", "file": "app.py", "line": 10, "type": "function", "complexity": 3},
      {"id": "process_request", "file": "handlers.py", "line": 25, "type": "function", "complexity": 8},
      {"id": "validate_input", "file": "validators.py", "line": 5, "type": "function", "complexity": 5},
      {"id": "save_to_db", "file": "db/queries.py", "line": 42, "type": "function", "complexity": 4},
      {"id": "UserModel.save", "file": "models/user.py", "line": 50, "type": "method", "complexity": 2}
    ],
    "edges": [
      {"from": "main", "to": "process_request", "call_site_line": 15, "edge_type": "direct"},
      {"from": "process_request", "to": "validate_input", "call_site_line": 30, "edge_type": "direct"},
      {"from": "process_request", "to": "save_to_db", "call_site_line": 35, "edge_type": "direct"},
      {"from": "save_to_db", "to": "UserModel.save", "call_site_line": 48, "edge_type": "method_call"}
    ],
    "entry_points": [
      {"name": "main", "file": "app.py", "type": "__main__"},
      {"name": "handle_webhook", "file": "webhooks.py", "type": "flask_route"}
    ],
    "circular_imports": [],
    "circular_calls": [],
    "polymorphism_hints": [
      {"method": "save", "classes": ["UserModel", "OrderModel"], "resolution": "type_hint_based"}
    ],
    "callback_edges": [
      {"from": "process_request", "to": "on_complete_handler", "pattern": "callback_param"}
    ],
    "mermaid_diagram": "graph TD\n  subgraph app.py\n    main[main]\n  end\n  subgraph handlers.py\n    process_request[process_request]\n  end\n  main --> process_request\n  process_request --> validate_input\n  process_request --> save_to_db",
    "depth_reached": 5,
    "node_count": 12,
    "truncated": false
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
    "nodes": [
      {"id": "main", "file": "app.py", "line": 10, "type": "function", "complexity": 3, "owner": "@platform-team"},
      {"id": "process_request", "file": "handlers.py", "line": 25, "type": "function", "complexity": 8, "owner": "@backend-team"},
      {"id": "validate_input", "file": "validators.py", "line": 5, "type": "function", "complexity": 5, "owner": "@backend-team"},
      {"id": "save_to_db", "file": "db/queries.py", "line": 42, "type": "function", "complexity": 4, "owner": "@data-team"}
    ],
    "edges": [
      {"from": "main", "to": "process_request", "call_site_line": 15, "edge_type": "direct", "frequency_hint": "high"},
      {"from": "process_request", "to": "validate_input", "call_site_line": 30, "edge_type": "direct"},
      {"from": "process_request", "to": "save_to_db", "call_site_line": 35, "edge_type": "direct", "frequency_hint": "high"}
    ],
    "entry_points": [
      {"name": "main", "file": "app.py", "type": "__main__"},
      {"name": "handle_webhook", "file": "webhooks.py", "type": "flask_route"},
      {"name": "scheduled_cleanup", "file": "jobs.py", "type": "cron_job"}
    ],
    "circular_imports": [],
    "circular_calls": [],
    "hot_paths": [
      {
        "path": ["main", "process_request", "save_to_db"],
        "estimated_frequency": "high",
        "total_complexity": 15
      }
    ],
    "dead_code_candidates": [
      {"function": "deprecated_handler", "file": "handlers.py", "line": 150, "reason": "no_incoming_edges"}
    ],
    "architectural_violations": [
      {
        "type": "layer_violation",
        "from": "handlers.py:process_request",
        "to": "db/queries.py:raw_execute",
        "rule": "handlers_should_use_repositories",
        "severity": "warning"
      }
    ],
    "graph_metrics": {
      "total_nodes": 45,
      "total_edges": 78,
      "average_fan_out": 2.3,
      "max_depth": 8,
      "strongly_connected_components": 2
    },
    "mermaid_diagram": "graph TD\n  classDef hot fill:#ff6b6b\n  main[main]:::hot --> process_request[process_request]:::hot\n  process_request --> save_to_db[save_to_db]:::hot",
    "depth_reached": 10,
    "node_count": 45
  },
  "id": 1
}
```

---

## Research Queries

### Foundational Research
| Topic | Query | Purpose |
|-------|-------|---------|
| Static Call Graph Construction | "points-to analysis call graph construction Andersen Steensgaard" | Understand precision vs. scalability tradeoffs |
| Dynamic Dispatch Resolution | "class hierarchy analysis devirtualization call graph" | Improve OOP call resolution accuracy |
| JavaScript Call Graphs | "JavaScript call graph npm ACG approximate call graph" | State-of-art for dynamic languages |
| Incremental Analysis | "incremental call graph update demand-driven analysis" | Enable real-time graph updates |
| Graph Compression | "call graph compression summarization large-scale" | Handle million-function codebases |

### Language-Specific Research
| Language | Query | Focus |
|----------|-------|-------|
| Python | "Python type inference call graph mypy pytype" | Leverage type hints for precision |
| TypeScript | "TypeScript control flow analysis type narrowing" | Use TS type system for resolution |
| Java | "Java call graph Soot WALA pointer analysis" | Mature ecosystem to learn from |
| Go | "Go static analysis call graph golang.org/x/tools" | Interface-based dispatch patterns |
| Rust | "Rust trait object call graph monomorphization" | Trait dispatch and generics |

### Advanced Techniques
| Technique | Query | Application |
|-----------|-------|-------------|
| Machine Learning | "neural call graph completion deep learning code" | Infer missing edges from patterns |
| Probabilistic Graphs | "probabilistic call graph dynamic dispatch confidence" | Confidence scores for uncertain edges |
| Hybrid Analysis | "hybrid static dynamic call graph profiling" | Combine static + runtime data |
| Semantic Similarity | "code embedding semantic call graph prediction" | Predict calls based on code semantics |

---

## Roadmap

### v1.1 (Q1 2026): Enhanced Analysis & Robustness

#### Community Tier
- [ ] **Graceful Parse Failure Handling:** Report parse failures per-file instead of silently skipping; include partial results with warnings
- [ ] **GraphViz DOT Export:** Add `output_format="dot"` alongside Mermaid for integration with external visualization tools
- [ ] **Deterministic Truncation:** Ensure truncation messages and node ordering are fully deterministic for reproducible test assertions
- [ ] **Entry Point Taxonomy:** Classify entry points by type (CLI, web route, test, scheduled task, event handler) with metadata
- [ ] **Call Site Context:** Include caller line numbers and argument patterns in edge metadata

#### Pro Tier
- [ ] **JS/TS Import Resolution Improvements:**
  - Handle namespace imports (`import * as utils from './utils'`)
  - Resolve re-exports and barrel files (`index.ts` aggregations)
  - Track dynamic imports (`import()` expressions) as potential edges
- [ ] **Enhanced Caller Attribution:**
  - Arrow functions with inferred names from assignment context
  - Class field initializers and property methods
  - Callback parameters (e.g., `array.map(fn)` → edge to `fn`)
- [ ] **Python Dynamic Dispatch:**
  - Best-effort `self.method()` resolution using class hierarchy analysis
  - Simple polymorphism via declared type hints
  - Protocol/ABC tracking for interface-like patterns

#### Enterprise Tier
- [ ] **Call Graph Diffing:** Compare graphs between two commits/branches to identify added/removed/changed edges
- [ ] **Architectural Boundary Enforcement:** Define allowed/forbidden call patterns via policy; flag violations
- [ ] **Service-to-Service Mapping:** Framework adapters for Flask, FastAPI, Express, Spring to identify HTTP/RPC boundaries

**Research Focus:**
- "incremental call graph algorithms on-demand analysis"
- "JavaScript module resolution CommonJS ESM interop"
- "Python class hierarchy analysis type inference"

---

### v1.2 (Q2 2026): Language Expansion

#### All Tiers
- [ ] **Java Call Graph:**
  - Method resolution with inheritance hierarchy
  - Interface/abstract class dispatch tracking
  - Constructor chains and static initializers
- [ ] **Go Call Graph:**
  - Interface satisfaction tracking
  - Goroutine spawn points (`go func()`)
  - Channel communication edges (optional)

#### Pro Tier
- [ ] **C/C++ Call Graph:**
  - Direct call resolution via AST
  - Virtual method dispatch approximation
  - Function pointer tracking (best-effort)
- [ ] **Rust Call Graph:**
  - Trait method dispatch resolution
  - Generic monomorphization awareness
  - Async function chains (`.await` points)

#### Enterprise Tier
- [ ] **Multi-Language Unified Graph:** Single graph spanning Python + JS + Java in monorepos
- [ ] **Cross-Language Call Tracking:**
  - Python ↔ C extension boundaries (via ctypes, pybind11 annotations)
  - JS ↔ WASM call boundaries
  - JNI call tracking (Java ↔ native)
- [ ] **Language Bridge Detection:** Identify FFI, subprocess, HTTP calls between languages

**Research Focus:**
- "Java call graph Soot WALA bytecode analysis"
- "Go interface dispatch static analysis"
- "cross-language call graph FFI boundary detection"

---

### v1.3 (Q3 2026): Performance & Scalability

#### All Tiers
- [ ] **Incremental Graph Building:** Only recompute affected subgraph when files change; cache invalidation by file hash
- [ ] **Parallel Graph Construction:** Multi-threaded AST parsing and edge extraction
- [ ] **Memory-Efficient Representation:** Compressed adjacency lists for graphs with 100K+ nodes
- [ ] **Streaming Output:** Emit nodes/edges as they're discovered for long-running builds

#### Pro Tier
- [ ] **Smart Caching with Invalidation:**
  - Content-hash based cache keys
  - Dependency-aware invalidation (if A calls B and B changes, invalidate A's outgoing edges)
- [ ] **Delta Graph Updates:** Given a diff, compute only the changed portion of the graph
- [ ] **On-Demand Subgraph Loading:** Lazy-load subgraphs only when traversed

#### Enterprise Tier
- [ ] **Distributed Graph Construction:** Shard analysis across workers for massive codebases (10M+ LOC)
- [ ] **Real-Time Graph Updates:** Integrate with file watchers for live dashboard updates
- [ ] **Historical Graph Analysis:** Store graph snapshots over time; query how call relationships evolved
- [ ] **Graph Database Export:** Export to Neo4j, TigerGraph, or similar for advanced querying

**Research Focus:**
- "incremental program analysis demand-driven"
- "distributed static analysis large-scale"
- "call graph compression sparse representation"

**Performance Targets:**
| Metric | Target | Measurement |
|--------|--------|-------------|
| 1K functions | <500ms | Cold build time |
| 10K functions | <5s | Cold build time |
| 100K functions | <60s | Cold build with parallelism |
| Incremental update | <200ms | Single file change |
| Memory (10K funcs) | <50MB | Peak RSS |

---

### v1.4 (Q4 2026): Advanced Analysis Features

#### Pro Tier
- [ ] **Call Frequency Hints:** Integrate with profiling data to annotate edges with runtime frequency
- [ ] **Hot Path Identification:** Highlight critical execution paths based on frequency/cost
- [ ] **Refactoring Impact Analysis:**
  - "If I rename function X, what breaks?"
  - "If I change X's signature, which callers need updates?"
  - "What's the blast radius of deleting module Y?"
- [ ] **Dead Code Detection:** Functions with no incoming edges and not entry points
- [ ] **Cyclomatic Complexity Overlay:** Annotate nodes with complexity scores

#### Enterprise Tier
- [ ] **Custom Graph Metrics:** User-defined metrics computed over the graph (e.g., "coupling score", "cohesion index")
- [ ] **Graph-Based Compliance Checking:**
  - "No direct calls from UI layer to database layer"
  - "All security-sensitive functions must go through auth middleware"
- [ ] **Automated Architecture Validation:** Compare actual call graph against declared architecture diagrams
- [ ] **Change Risk Scoring:** ML-based prediction of which changes are high-risk based on graph topology
- [ ] **API Surface Extraction:** Identify public API boundaries from call patterns

**Research Focus:**
- "software architecture compliance checking call graph"
- "change impact analysis call graph machine learning"
- "dead code detection static analysis precision"

---

### v1.5 (Q1 2027): AI-Enhanced Analysis

#### Pro Tier
- [ ] **Call Pattern Templates:** Recognize common patterns (factory, observer, decorator) and label them
- [ ] **Similar Function Clustering:** Group functions with similar call signatures/patterns
- [ ] **Suggested Refactorings:** Based on call patterns, suggest extract-method or move-function

#### Enterprise Tier
- [ ] **Neural Call Graph Completion:** ML model to predict missing edges from code patterns
- [ ] **Natural Language Graph Queries:** "Show me all functions that eventually call the database"
- [ ] **Anomaly Detection:** Identify unusual call patterns that may indicate bugs or security issues
- [ ] **Architecture Smell Detection:** Automatically identify god classes, circular dependencies, feature envy

**Research Focus:**
- "graph neural network code analysis call prediction"
- "code clone detection call graph similarity"
- "architecture smell detection machine learning"

---

## Known Issues & Limitations

### Current Limitations
| Limitation | Impact | Workaround |
|------------|--------|------------|
| **Dynamic calls** | Cannot track `getattr(obj, method_name)()` or similar runtime-only calls | Use type hints to enable best-effort inference |
| **Reflection** | Dynamic method invocation (`eval`, `exec`) not tracked | Mark reflective calls in comments for manual review |
| **External libraries** | Third-party library internals not analyzed | Use stub files or type annotations |
| **Monkey patching** | Runtime modifications to classes not detected | Static analysis limitation; use runtime profiling |
| **Decorators with wrappers** | Some decorator patterns obscure the actual callee | Decorator-aware analysis in Pro tier |

### Planned Fixes
| Version | Fix | Approach |
|---------|-----|----------|
| v1.1 | Partial dynamic call inference | Type-hint-guided resolution for `self.*` calls |
| v1.2 | Reflection support (basic) | Pattern recognition for common reflection idioms |
| v1.3 | Library stub generation | Auto-generate stubs from type hints and docstrings |
| v1.4 | Decorator unwrapping | AST pattern matching for `functools.wraps` and similar |

---

## Success Metrics

### Accuracy Targets
| Metric | Community | Pro | Enterprise | Measurement Method |
|--------|-----------|-----|------------|-------------------|
| **Precision** | >90% | >95% | >98% | Manual review of 100 random edges |
| **Recall** | >85% | >92% | >95% | Compare against runtime profiling ground truth |
| **Entry Point Detection** | >95% | >98% | >99% | Known entry point test corpus |
| **Circular Dependency Detection** | 100% | 100% | 100% | Synthetic cycle test suite |

### Performance Targets
| Metric | Target | Measurement |
|--------|--------|-------------|
| **Graph generation (1K functions)** | <500ms | Cold build, single-threaded |
| **Graph generation (10K functions)** | <5s | Cold build, parallel |
| **Incremental update** | <200ms | Single file change |
| **Memory usage (10K functions)** | <50MB | Peak RSS during build |
| **Memory usage (100K functions)** | <500MB | Peak RSS with compression |

### Adoption Metrics
| Metric | Q2 2026 | Q4 2026 | Q2 2027 |
|--------|---------|---------|---------|
| **Monthly graph generations** | 25K | 75K | 150K |
| **Average graph size (nodes)** | 200 | 500 | 1000 |
| **Unique users** | 1K | 5K | 15K |
| **Enterprise deployments** | 10 | 50 | 150 |

### Quality Metrics
| Metric | Target | Measurement |
|--------|--------|-------------|
| **Test coverage** | >95% | Line coverage on `call_graph.py` |
| **Documentation coverage** | 100% | All public functions documented |
| **API stability** | No breaking changes in v1.x | Semantic versioning compliance |

---

## Integration Points

### MCP Tool Integration
```json
{
  "tool": "get_call_graph",
  "parameters": {
    "entry_point": "main.py:main",
    "depth": 5,
    "include_circular_check": true
  }
}
```

### Related Tools
| Tool | Relationship |
|------|--------------|
| `get_graph_neighborhood` | Uses call graph as underlying data structure |
| `get_symbol_references` | Complementary: references vs. calls |
| `cross_file_security_scan` | Uses call graph for taint propagation |
| `get_project_map` | Provides high-level view; call graph provides detailed edges |

### Export Formats
| Format | Status | Use Case |
|--------|--------|----------|
| **Mermaid** | ✅ v1.0 | Documentation, README diagrams |
| **JSON** | ✅ v1.0 | Programmatic analysis, custom visualization |
| **GraphViz DOT** | 🔄 v1.1 | External tools (Gephi, yEd) |
| **Neo4j Cypher** | 🔄 v1.3 | Graph database import |
| **SARIF** | 🔄 v1.4 | IDE integration, CI/CD pipelines |

---

## Competitive Analysis

### Key Competitors
| Tool | Strengths | Weaknesses | Our Differentiation |
|------|-----------|------------|---------------------|
| **Understand (SciTools)** | Mature, multi-language | Expensive, closed source | OSS-friendly, MCP-native |
| **Sourcetrail** | Great visualization | Discontinued | Active development, AI integration |
| **CodeScene** | Behavioral analysis | Requires git history | Real-time static analysis |
| **Joern** | Security-focused CPG | Steep learning curve | Simpler API, broader use cases |
| **tree-sitter + custom** | Flexible | DIY complexity | Batteries-included solution |

### Differentiation Strategy
1. **MCP-Native:** First-class support for AI agent workflows
2. **Tier-Based:** Accessible Community tier, powerful Enterprise features
3. **Multi-Language:** Unified API across Python, JS, TS, Java, Go
4. **Incremental:** Real-time updates for IDE integration
5. **Confidence Scores:** Honest uncertainty for AI agents

---

## Dependencies

### Internal Dependencies
| Module | Purpose |
|--------|---------|
| `src/code_scalpel/ast_tools/call_graph.py` | Core call graph builder |
| `src/code_scalpel/mcp/server.py` | MCP tool wrapper + tier limits |
| `src/code_scalpel/code_parsers/` | Language-specific parsers |
| `src/code_scalpel/graph_engine/` | Graph data structures and algorithms |
| `src/code_scalpel/tier/capabilities.py` | Tier-based feature gating |

### External Dependencies
| Package | Purpose | Version |
|---------|---------|---------|
| `esprima` | JS/TS parsing fallback | ^4.0 |
| `tree-sitter` | Fast multi-language parsing | ^0.20 |
| `tree-sitter-python` | Python grammar | ^0.20 |
| `tree-sitter-javascript` | JS/TS grammar | ^0.20 |
| `networkx` | Graph algorithms (optional) | ^3.0 |

---

## Security Considerations

### Data Handling
- **No code execution:** Pure static analysis; code is parsed, never run
- **No external calls:** Analysis is fully offline (no telemetry)
- **Memory bounds:** Truncation limits prevent memory exhaustion attacks

### Governance Integration
- **Audit logging:** All tool invocations logged when governance enabled
- **Policy enforcement:** Architectural boundaries can be enforced via governance policies
- **Access control:** Tier-based limits prevent resource exhaustion

---

## Breaking Changes

### v1.x Compatibility Promise
- No breaking changes planned for v1.x series
- New features are additive (new fields, new options)
- Deprecations announced at least one minor version before removal

### Migration Notes
| From | To | Notes |
|------|-----|-------|
| v0.x | v1.0 | `CallGraphResult` fields renamed for clarity |
| v1.0 | v1.1 | No breaking changes; new optional `output_format` parameter |

---

## Appendix: Entry Point Detection Patterns

### Python
| Pattern | Example | Detection Method |
|---------|---------|------------------|
| `__main__` block | `if __name__ == "__main__":` | AST pattern match |
| CLI decorators | `@click.command()` | Decorator inspection |
| pytest | `def test_*():` | Function name pattern |
| unittest | `class Test*(unittest.TestCase)` | Class hierarchy |
| Flask routes | `@app.route("/")` | Decorator inspection |
| FastAPI routes | `@app.get("/")` | Decorator inspection |
| Django views | `def view(request):` | URL conf tracing |
| Celery tasks | `@celery.task` | Decorator inspection |
| AWS Lambda | `def handler(event, context):` | Signature pattern |

### JavaScript/TypeScript
| Pattern | Example | Detection Method |
|---------|---------|------------------|
| Module exports | `export function main()` | Export declaration |
| Express routes | `app.get('/', handler)` | Call pattern |
| React components | `export default function App()` | Export + JSX return |
| Jest tests | `test('...', () => {})` | Call pattern |
| Event handlers | `element.addEventListener(...)` | Call pattern |
| AWS Lambda | `exports.handler = async (event) => {}` | Export pattern |

---

**Last Updated:** December 31, 2025  
**Next Review:** March 31, 2026
