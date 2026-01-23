# symbolic_execute Tool Roadmap

**Tool Name:** `symbolic_execute`  
**Tool Version:** v1.0  
**Code Scalpel Version:** v3.3.1  
**Current Status:** Stable  
**Primary Module:** `src/code_scalpel/mcp/server.py` (line 6855)  
**Tier Availability:** All tiers (Community, Pro, Enterprise)

---

## Overview

The `symbolic_execute` tool explores all possible execution paths through code using Z3 constraint solving. Identifies edge cases, unreachable code, and potential bugs.

**Why AI Agents Need This:**
- **Complete coverage:** Explore paths that might be missed by concrete testing
- **Edge case discovery:** Find boundary conditions and corner cases automatically
- **Bug detection:** Identify unreachable code and impossible conditions
- **Test generation:** Generate test inputs that exercise specific paths
- **Formal reasoning:** Provide mathematical guarantees about code behavior

---

## Polyglot Architecture Definition

> [20260109_DOCS] Added explicit polyglot architecture, current status, gaps, and blockers.

The polyglot design follows a front-end → IR → solver pipeline to ensure consistent capabilities across languages while keeping solver semantics unified.

- **Language Front-Ends:**
  - Python: AST-based parser (existing)
  - JavaScript/TypeScript: Tree-sitter-based parser with async/await and promise state modeling
  - Java: Tree-sitter or compiler AST with basic object/field constraints, limited exceptions/concurrency initially
  - Go (Pro), C/C++ and Rust (Enterprise): Tree-sitter-based parsing with progressively richer memory and pointer semantics

- **Common IR (Intermediate Representation):**
  - Normalizes control flow (if/else, loops), expressions, and type domains
  - Encodes language-specific semantics (e.g., JS truthiness, TS narrowing, Java nullability) into uniform constraint primitives
  - Provides hooks for memory model adapters (objects, pointers, heap aliases)

- **Constraint Generation:**
  - Maps IR into Z3 constraints for Int, Bool, String, Float (baseline)
  - Incremental addition of collections and object fields, then pointers/aliasing for systems languages
  - Configurable bounds for string/collection constraints to control solver cost

- **Execution Engine:**
  - Tier-aware loop unrolling and path bounding
  - Optional concolic execution and path prioritization in higher tiers
  - Pluggable heuristics for state-space reduction and distributed execution (Enterprise)

- **Result Contract:**
  - Maintains `SymbolicExecutionResult` schema across languages
  - Adds language metadata fields only when strictly necessary; no breaking changes

## Current Polyglot Status

- **Implementation Reality:** Python-only symbolic execution is implemented. The MCP entrypoint `symbolic_execute` currently accepts Python source and advertises Python in the tool docstring.
- **Code Reference:** Implementation lives in `src/code_scalpel/mcp/server.py` within `_symbolic_execute_sync` and `symbolic_execute()`; no language parameter or routing is present.
- **Fallback Behavior:** AST-only “basic symbolic analysis” exists as a fallback for Python code when the symbolic engine is unavailable; no non-Python analysis path is wired for this tool.

## Known Gaps

- **No language routing:** Missing `language` detection/parameter to select front-end and semantics.
- **Front-end absence:** JS/TS/Java/Go/C/C++/Rust front-ends not implemented for this tool.
- **IR completeness:** Shared IR lacks documented support for async semantics, object graphs, and pointer aliasing.
- **Constraint coverage:** Collections, objects, strings (advanced), and memory models not uniformly mapped across languages.
- **Performance safeguards:** Path explosion controls and solver bounds are Python-centric; need cross-language calibration.
- **Test harnesses:** Polyglot fixtures and golden tests are not established for parity validation.

## Polyglot Blockers

- **Async semantics (JS/TS):** Requires modeling of event loop, promises, and `await` scheduling.
- **Object models (Java):** Field constraints, nullability, exceptions, and basic concurrency primitives.
- **Pointers/aliasing (C/C++/Rust):** Memory model with heap, stack, and alias tracking; bounds to avoid solver blowups.
- **String solving costs:** Z3 string constraints need strict bounding and heuristics to remain performant.
- **IR discipline:** Clear separation between language quirks and solver-neutral primitives; avoid leaking language-specific behavior into solver layer.
- **Licensing and tiering:** Ensure advanced features (distributed, GPU, memory modeling) align with tier capabilities and configuration gates.

## Milestone Adjustments (Requirements Completed vs Pending)

- **Completed (v1.0 alignment):**
  - Python symbolic execution with tier-aware limits (`max_paths`, `max_depth`) and capability gating
  - Fallback AST-only analysis with path extraction
  - Optional features wired for higher tiers: smart path prioritization, concolic hints, state-space analysis, memory modeling (Python-only)

- **Pending (polyglot enablement):**
  - Add `language` detection/parameter and router
  - Implement JS/TS front-end + IR mapping for control flow and basic types
  - Implement Java front-end + IR mapping for primitives and object fields (initial subset)
  - Define IR adapters for async (JS/TS) and object semantics (Java)
  - Establish performance bounds for strings/collections per language
  - Build polyglot test suites and parity checks across languages

These adjustments refine the existing v1.2 “Language Expansion” plan to enumerate concrete deliverables and acceptance criteria per language.

---

## Acceptance Criteria

> [20260109_DOCS] Establish concrete, testable criteria for polyglot enablement.

- **Routing & Contract:**
  - `language` parameter accepted by the MCP tool and documented (Python default)
  - Content-based language detection fallback when parameter omitted (file extension + heuristics)
  - Router selects the correct front-end and IR mapping for the requested language
  - Result conforms to `SymbolicExecutionResult` without breaking changes; add minimal language metadata only if necessary

- **Python (Baseline):**
  - Int/Bool/String/Float constraints; loop unrolling per tier limits
  - Path exploration and fallback AST-only analysis if engine unavailable
  - Tier features: smart prioritization, concolic hints, state-space analysis, memory modeling

- **JavaScript/TypeScript (Initial):**
  - Control-flow (if/else, loops) with async awareness (await, promises) modeled conservatively
  - Primitive constraints (number, boolean, string) with bounded string solving
  - TypeScript: basic narrowing respected in IR; no full type soundness required in v1.2

- **Java (Initial):**
  - Primitive constraints (int/boolean/float/string) and field access for simple objects
  - Nullability modeled; exceptions/concurrency deferred
  - Loop unrolling and path exploration within tier limits

- **Systems Languages (C/C++/Rust – Enterprise preview):**
  - Minimal memory model: distinguish stack/heap allocations, basic alias tracking
  - Pointer arithmetic constraints bounded; no undefined behavior modeling in v1.2
  - Performance gates applied to avoid solver blowups

## Validation & Test Plan

> [20260109_DOCS] Define parity tests, bounds, and performance gates.

- **Fixtures:** Curated mini-programs per language covering branches, loops, and boundary conditions
- **Parity Checks:** Equivalent logic cases across Python/JS/TS/Java to compare path counts and constraint shapes
- **Solver Bounds:** Enforce per-language string and collection limits (Community/Pro tiers)
- **Performance Gates:**
  - Path exploration throughput targets (>= 100 paths/sec on baseline fixtures)
  - Constraint solving median latency (< 100 ms per constraint on bounded cases)
- **Concolic Tests (Pro+):** Use generated concrete inputs to validate execution outcomes against expected paths
- **Fallback Verification:** Ensure AST-only analysis produces consistent basic paths when symbolic engine is unavailable

---

## Routing & IR Design

> [20260109_DOCS] Define parameter schema, detection heuristics, resolution order, and IR boundaries.

- **MCP Parameters (Non-breaking additions):**
  - `language: str | None` — Explicit language selector; accepted values: `python`, `javascript`, `typescript`, `java`, `go`, `c`, `cpp`, `rust`, or `auto` (default `auto` with current default effectively `python` until other front-ends land)
  - `file_path: str | None` — Optional file path to improve detection via extension
  - `strict_language: bool = False` — If `True`, return an error when language is unsupported rather than falling back

- **Detection Heuristics & Resolution Order:**
  1. If `language` provided and supported → use that front-end
  2. Else if `file_path` provided → detect via extension map: `.py`→python, `.js`→javascript, `.ts`→typescript, `.java`→java, `.go`→go, `.c`→c, `.cc/.cpp/.cxx`→cpp, `.rs`→rust
  3. Else content heuristics (keywords/tokens): e.g., `def`/`import` (Python), `function`/`=>`/`import from` (JS/TS), `class`/`package`/`public` (Java), `fn`/`pub` (Rust), `#include` (C/C++)
  4. If unresolved → default to `python` for backward compatibility unless `strict_language=True`

- **Error Handling:**
  - Unsupported language with `strict_language=True` → return a structured error with `supported_languages` list
  - Unsupported language without strict mode → perform minimal IR/CFG-only analysis (no solver) and emit a clear `[FALLBACK]` warning in `error`

- **IR Boundary Rules:**
  - Normalize control flow (if/elif/else, loops) and boolean semantics; encode language-specific truthiness explicitly (JS/TS)
  - Primitive domains: unify numeric/boolean/string; bound strings and collection sizes per tier to protect solver performance
  - Object fields: represent as maps from symbols to field symbols; nullability as explicit predicate; exceptions and concurrency deferred to later milestones
  - Memory model hooks: optional adapter layer for systems languages to plug in stack/heap/alias approximations (Enterprise)
  - As-a-rule: keep language quirks in the front-end; IR remains solver-neutral; do not leak language syntax into solver constraints

- **Capability/Tier Gating in Router:**
  - Verify feature availability for requested language vs. current tier; downgrade to CFG-only fallback when capabilities are not licensed/enabled
  - Record `detection_method` (`param|ext|heuristic`) and `language_selected` for telemetry and debugging


---

## Research Queries for Future Development

### Foundational Research
| Topic | Query | Purpose |
|-------|-------|---------|
| Path Explosion | "symbolic execution path explosion mitigation techniques" | Scale to larger functions |
| Constraint Solving | "SMT solver performance optimization Z3 alternatives" | Faster solving |
| State Merging | "state merging symbolic execution effectiveness" | Reduce redundant paths |
| Concolic Testing | "concolic testing practical implementation" | Hybrid execution |

### Language-Specific Research
| Topic | Query | Purpose |
|-------|-------|---------|
| Python Semantics | "python symbolic execution dynamic typing challenges" | Better Python support |
| JavaScript | "javascript symbolic execution async await modeling" | Handle async JS |
| Java | "java symbolic execution object model" | Enterprise Java support |
| Collections | "symbolic execution collection types arrays lists" | Better collection handling |

### Advanced Techniques
| Topic | Query | Purpose |
|-------|-------|---------|
| ML Guidance | "machine learning guided symbolic execution" | Smart path selection |
| Fuzzing Integration | "symbolic execution fuzzing synergy" | Combine approaches |
| Incremental | "incremental symbolic execution code changes" | Real-time analysis |
| Distributed | "distributed symbolic execution scalability" | Large-scale analysis |

---

## Current Capabilities (v1.0)

### Community Tier
- ✅ Basic symbolic execution - `basic_symbolic_execution`
- ✅ Supports Int, Bool, String, Float types - `simple_constraints`
- ✅ Path exploration with constraints - `path_exploration`
- ✅ Loop unrolling (max 10 iterations) - `loop_unrolling`
- ✅ Supports Python
- ⚠️ **Limits:** Max 50 paths explored, max 10 loop depth

### Pro Tier
- ✅ All Community features (unlimited paths)
- ✅ Smart path prioritization - `smart_path_prioritization`
- ✅ Constraint solving optimization - `constraint_optimization`
- ✅ Deeper loop unrolling (max 100 iterations) - `deep_loop_unrolling`
- ✅ Support for List, Dict types - `list_dict_types`
- ✅ Concolic execution (concrete + symbolic) - `concolic_execution`
- ✅ Complex constraints - `complex_constraints`
- ✅ String constraints - `string_constraints`

### Enterprise Tier
- ✅ All Pro features
- ✅ Custom path prioritization strategies - `custom_path_prioritization`
- ✅ Distributed symbolic execution - `distributed_execution`
- ✅ State space reduction heuristics - `state_space_reduction`
- ✅ Support for complex object types - `complex_object_types`
- ✅ Memory modeling - `memory_modeling`
- ✅ Custom solvers - `custom_solvers`
- ✅ Advanced types - `advanced_types`
- ✅ Formal verification - `formal_verification`
- ✅ Equivalence checking - `equivalence_checking`

---

## Return Model: SymbolicExecutionResult

```python
class SymbolicExecutionResult(BaseModel):
    # Core fields (All Tiers)
    success: bool                              # Whether execution succeeded
    paths_explored: int                        # Number of paths found
    paths: list[ExecutionPath]                 # All explored paths
    unreachable_branches: list[Branch]         # Dead code detected
    constraints_used: list[str]                # Symbolic constraints
    execution_time_ms: int                     # Time taken
    
    # Pro Tier
    path_priorities: dict[int, float]          # Path importance scores
    optimized_constraints: list[str]           # Simplified constraints
    test_inputs: list[TestInput]               # Generated test cases
    type_coverage: dict[str, list[str]]        # Types explored per variable
    concolic_hints: list[ConcolicHint]         # Suggestions for concrete values
    
    # Enterprise Tier
    distributed_stats: DistributedStats        # Cluster execution stats
    state_space_coverage: float                # % of state space explored
    formal_proof: FormalProof | None           # Mathematical proof (if available)
    equivalence_result: EquivalenceResult      # Comparison with reference
    
    error: str | None                          # Error message if failed
```

---

## Usage Examples

### Community Tier
```python
result = await symbolic_execute(code='''
def classify(x):
    if x > 10:
        return "high"
    elif x > 5:
        return "medium"
    else:
        return "low"
''')
# Returns: paths_explored=3, paths with constraints:
#   Path 1: x > 10 → "high"
#   Path 2: x <= 10 AND x > 5 → "medium"  
#   Path 3: x <= 5 → "low"
# Limited to 50 paths, 10 loop iterations
```

### Pro Tier
```python
result = await symbolic_execute(
    code=code,
    max_paths=500,
    max_depth=50,
    generate_tests=True
)
# Additional: path_priorities, optimized_constraints, test_inputs,
#             type_coverage, concolic_hints
# Supports List, Dict types
```

### Enterprise Tier
```python
result = await symbolic_execute(
    code=code,
    distributed=True,
    prove_equivalence=reference_code
)
# Additional: distributed_stats, state_space_coverage, formal_proof,
#             equivalence_result
# Unlimited paths, custom solvers
```

---

## Integration Points

### Related Tools
| Tool | Relationship |
|------|--------------|
| `generate_unit_tests` | Uses symbolic paths for test generation |
| `security_scan` | Symbolic execution of taint paths |
| `simulate_refactor` | Equivalence checking |
| `crawl_project` | Complexity guides path prioritization |

### Export Formats
| Format | Status | Use Case |
|--------|--------|----------|
| **JSON** | ✅ v1.0 | Programmatic analysis |
| **pytest** | 🔄 v1.4 | Generated test files |
| **SMT-LIB** | 🔄 v1.3 | Constraint export |
| **Visualization** | 🔄 v1.4 | Path tree diagrams |

---

## Competitive Analysis

| Tool | Strengths | Weaknesses | Our Differentiation |
|------|-----------|------------|---------------------|
| **KLEE** | Mature, proven | C/C++ only | Python/JS/TS support |
| **Angr** | Binary analysis | Complex API | Simple code analysis |
| **PyExZ3** | Python-native | Limited maintenance | Active development |
| **Pex** | .NET integration | .NET only | Multi-language |
| **CrossHair** | Property-based | Limited scalability | Enterprise scalability |

---

## Configuration Files

### Tier Capabilities
- **File:** `src/code_scalpel/licensing/features.py` (line 294)
- **Structure:** Defines `capabilities` set and `limits` dict per tier

### Numeric Limits
- **File:** `.code-scalpel/limits.toml` (lines 314-327)
- **Community:** `max_paths=50`, `max_depth=10`
- **Pro:** `max_paths=unlimited`, `max_depth=100`
- **Enterprise:** Unlimited

### Response Verbosity
- **File:** `.code-scalpel/response_config.json` (line 75)
- **Exclude fields:** `solver_statistics`, `constraint_dump`, `z3_model_dump`, `path_conditions_raw`

---

## MCP Request/Response Examples

### MCP Request Format

```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "mcp_code-scalpel_symbolic_execute",
    "arguments": {
      "code": "def classify(x):\n    if x > 10:\n        return \"high\"\n    elif x > 5:\n        return \"medium\"\n    else:\n        return \"low\""
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
    "paths_explored": 3,
    "paths": [
      {
        "path_id": 1,
        "constraints": ["x > 10"],
        "return_value": "\"high\"",
        "reachable": true,
        "example_input": {"x": 15}
      },
      {
        "path_id": 2,
        "constraints": ["x <= 10", "x > 5"],
        "return_value": "\"medium\"",
        "reachable": true,
        "example_input": {"x": 8}
      },
      {
        "path_id": 3,
        "constraints": ["x <= 5"],
        "return_value": "\"low\"",
        "reachable": true,
        "example_input": {"x": 3}
      }
    ],
    "unreachable_branches": [],
    "constraints_used": ["x: Int"],
    "execution_time_ms": 125,
    "path_priorities": null,
    "optimized_constraints": null,
    "test_inputs": null,
    "type_coverage": null,
    "concolic_hints": null,
    "distributed_stats": null,
    "state_space_coverage": null,
    "formal_proof": null,
    "equivalence_result": null,
    "error": null
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
    "paths_explored": 3,
    "paths": [
      {
        "path_id": 1,
        "constraints": ["x > 10"],
        "return_value": "\"high\"",
        "reachable": true,
        "example_input": {"x": 15},
        "complexity": 1
      },
      {
        "path_id": 2,
        "constraints": ["x <= 10", "x > 5"],
        "return_value": "\"medium\"",
        "reachable": true,
        "example_input": {"x": 8},
        "complexity": 2
      },
      {
        "path_id": 3,
        "constraints": ["x <= 5"],
        "return_value": "\"low\"",
        "reachable": true,
        "example_input": {"x": 3},
        "complexity": 1
      }
    ],
    "unreachable_branches": [],
    "constraints_used": ["x: Int"],
    "execution_time_ms": 145,
    "path_priorities": {
      "1": 0.8,
      "2": 0.9,
      "3": 0.7
    },
    "optimized_constraints": [
      "x > 10 → high",
      "5 < x <= 10 → medium",
      "x <= 5 → low"
    ],
    "test_inputs": [
      {"name": "test_high", "inputs": {"x": 11}, "expected": "high"},
      {"name": "test_medium", "inputs": {"x": 6}, "expected": "medium"},
      {"name": "test_low", "inputs": {"x": 0}, "expected": "low"},
      {"name": "test_boundary_high", "inputs": {"x": 10}, "expected": "medium"},
      {"name": "test_boundary_low", "inputs": {"x": 5}, "expected": "low"}
    ],
    "type_coverage": {
      "x": ["Int (positive)", "Int (negative)", "Int (zero)", "Int (boundary)"]
    },
    "concolic_hints": [
      {"variable": "x", "suggested_values": [0, 5, 6, 10, 11, -1]}
    ],
    "distributed_stats": null,
    "state_space_coverage": null,
    "formal_proof": null,
    "equivalence_result": null,
    "error": null
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
    "paths_explored": 3,
    "paths": [
      {
        "path_id": 1,
        "constraints": ["x > 10"],
        "return_value": "\"high\"",
        "reachable": true,
        "example_input": {"x": 15}
      },
      {
        "path_id": 2,
        "constraints": ["x <= 10", "x > 5"],
        "return_value": "\"medium\"",
        "reachable": true,
        "example_input": {"x": 8}
      },
      {
        "path_id": 3,
        "constraints": ["x <= 5"],
        "return_value": "\"low\"",
        "reachable": true,
        "example_input": {"x": 3}
      }
    ],
    "unreachable_branches": [],
    "constraints_used": ["x: Int"],
    "execution_time_ms": 180,
    "path_priorities": {
      "1": 0.8,
      "2": 0.9,
      "3": 0.7
    },
    "optimized_constraints": [
      "x > 10 → high",
      "5 < x <= 10 → medium",
      "x <= 5 → low"
    ],
    "test_inputs": [
      {"name": "test_high", "inputs": {"x": 11}, "expected": "high"},
      {"name": "test_medium", "inputs": {"x": 6}, "expected": "medium"},
      {"name": "test_low", "inputs": {"x": 0}, "expected": "low"}
    ],
    "type_coverage": {
      "x": ["Int (full range)"]
    },
    "concolic_hints": [],
    "distributed_stats": {
      "nodes_used": 4,
      "total_paths_distributed": 3,
      "execution_time_per_node_ms": [45, 42, 48, 45],
      "speedup_factor": 2.8
    },
    "state_space_coverage": 1.0,
    "formal_proof": {
      "theorem": "∀x ∈ Int: classify(x) ∈ {\"high\", \"medium\", \"low\"}",
      "status": "proved",
      "solver": "Z3",
      "proof_time_ms": 85
    },
    "equivalence_result": null,
    "error": null
  },
  "id": 1
}
```

### Enterprise Tier Response (with Equivalence Checking)

```json
{
  "jsonrpc": "2.0",
  "result": {
    "success": true,
    "paths_explored": 6,
    "paths": [],
    "unreachable_branches": [],
    "constraints_used": ["x: Int"],
    "execution_time_ms": 350,
    "path_priorities": {},
    "optimized_constraints": [],
    "test_inputs": [],
    "type_coverage": {},
    "concolic_hints": [],
    "distributed_stats": {
      "nodes_used": 8,
      "total_paths_distributed": 6
    },
    "state_space_coverage": 1.0,
    "formal_proof": null,
    "equivalence_result": {
      "equivalent": true,
      "confidence": 1.0,
      "counterexample": null,
      "proof_status": "proved",
      "message": "Functions are semantically equivalent for all inputs"
    },
    "error": null
  },
  "id": 1
}
```

---

## Roadmap

### v1.1 (Q1 2026): Type System Expansion

#### Community Tier
- [ ] Tuple type support
- [ ] Set type support
- [ ] Better string constraint solving

#### Pro Tier
- [ ] Nested collection support
- [ ] Class/object symbolic execution
- [ ] Generator/iterator support

#### Enterprise Tier
- [ ] Custom type definitions
- [ ] Polymorphic type handling
- [ ] Memory aliasing analysis

### v1.2 (Q2 2026): Language Expansion

#### All Tiers
- [ ] JavaScript symbolic execution
  - [ ] Router supports `language="javascript"`
  - [ ] Tree-sitter front-end → IR for control flow, primitives
  - [ ] Async awareness for `await`/promises (conservative modeling)
  - [ ] Bounded string constraints; loop unrolling per tier
- [ ] TypeScript symbolic execution
  - [ ] Router supports `language="typescript"`
  - [ ] Front-end respects basic type narrowing in IR
  - [ ] Same constraints as JS baseline; TS-only metadata optional

#### Pro Tier
- [ ] Java symbolic execution
  - [ ] Router supports `language="java"`
  - [ ] Front-end → IR for primitives and simple object fields
  - [ ] Nullability modeled; exceptions/concurrency deferred
- [ ] Go symbolic execution
  - [ ] Router supports `language="go"` (initial parsing only if time permits)
  - [ ] Minimal control-flow and primitives in IR; collections bounded

#### Enterprise Tier
- [ ] C/C++ symbolic execution
  - [ ] Router supports `language="cpp"`/`"c"`
  - [ ] Minimal memory model (stack/heap, basic aliasing)
  - [ ] Pointer arithmetic bounded; no UB modeling in v1.2
- [ ] Rust symbolic execution
  - [ ] Router supports `language="rust"`
  - [ ] Conservative ownership/borrowing constraints limited to simple cases
  - [ ] Memory model hooks aligned with Enterprise capabilities

### v1.3 (Q3 2026): Performance Optimization

#### All Tiers
- [ ] Faster constraint solving
- [ ] Memory usage optimization
- [ ] Parallel path exploration

#### Pro Tier
- [ ] State merging strategies
- [ ] Lazy constraint evaluation
- [ ] Symbolic execution caching

#### Enterprise Tier
- [ ] Distributed execution across cluster
- [ ] GPU-accelerated constraint solving
- [ ] Incremental symbolic execution

### v1.4 (Q4 2026): Advanced Features

#### Pro Tier
- [ ] Interactive path exploration
- [ ] Path visualization
- [ ] Automated test case generation from paths

#### Enterprise Tier
- [ ] Symbolic execution of binary code
- [ ] Firmware symbolic execution
- [ ] Contract verification

---

## Known Issues & Limitations

### Current Limitations
- **Type support:** Limited to basic types + List/Dict (Pro+)
- **Path explosion:** Complex code may hit path limits
- **Solver timeout:** Very complex constraints may timeout
- **External calls:** Cannot symbolically execute library calls

### Planned Fixes
- v1.1: Extended type support
- v1.2: Better path pruning
- v1.3: Solver timeout handling
- v1.4: Library function summaries

---

## Success Metrics

### Performance Targets
- **Path exploration:** >1000 paths/second
- **Constraint solving:** <100ms per constraint
- **Bug detection:** >80% edge case coverage

### Adoption Metrics
- **Usage:** 50K+ executions per month by Q4 2026
- **Bugs found:** 5K+ unique bugs discovered

---

## Dependencies

### Internal Dependencies
- `symbolic_execution_tools/constraint_solver.py` - Z3 integration
- `symbolic_execution_tools/state_manager.py` - State management
- `ir/` - Intermediate representation

### External Dependencies
- `z3-solver` - Constraint solving

---

## Breaking Changes

None planned for v1.x series.

**API Stability Promise:**
- Tool signature stable
- Path representation backward compatible

---

**Last Updated:** December 31, 2025  
**Next Review:** March 31, 2026  
**Changelog:** v1.1 - Added capability names, configuration file references, tier-aware Pro/Enterprise features
