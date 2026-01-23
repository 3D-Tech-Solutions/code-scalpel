# cross_file_security_scan Tool Roadmap

**Tool Name:** `cross_file_security_scan`  
**Tool Version:** v1.0  
**Code Scalpel Version:** v3.3.0  
**Current Status:** Stable  
**Primary Module:** `src/code_scalpel/security/analyzers/cross_file_taint.py`  
**Tier Availability:** All tiers (Community, Pro, Enterprise)

---

## Overview

The `cross_file_security_scan` tool tracks tainted data flow across file and module boundaries. Essential for detecting vulnerabilities that span multiple files.

---

## Current Capabilities (v1.0)

### Community Tier
- ✅ Cross-file taint tracking (**Python-focused**)
- ✅ Import-graph/module-boundary analysis (Python)
- ✅ Source-to-sink tracing across modules (bounded)
- ✅ Mermaid diagram generation
- ⚠️ **Limits:** `max_depth = 3`, `max_modules = 10`

Notes:
- v1.0 cross-file taint tracking is implemented for Python projects; other languages may appear in heuristic context scanning but are not full taint-tracked.

### Pro Tier
- ✅ All Community features
- ✅ Cross-file taint tracking (**Python-focused**)
- ✅ Dependency-injection / framework context hints (best-effort, lightweight)
- ✅ Confidence scoring for flows (heuristic)
- ⚠️ **Limits:** `max_depth = 10`, `max_modules = 100`

### Enterprise Tier
- ✅ All Pro features
- ✅ Unlimited depth/modules (`max_depth = None`, `max_modules = None`)
- ✅ Repository-wide scan (bounded by runtime timeout)
- ✅ Global flow hints (best-effort heuristics)
- ✅ Microservice boundary hints + distributed trace view (best-effort heuristics)

---

## MCP Request/Response Examples

### MCP Request Format

```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "mcp_code-scalpel_cross_file_security_scan",
    "arguments": {
      "project_root": "/home/user/flask-app",
      "entry_points": ["app.py:main", "routes.py:index"],
      "max_depth": 5,
      "include_diagram": true
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
    "vulnerabilities": [
      {
        "id": "vuln_001",
        "type": "sql_injection",
        "cwe": "CWE-89",
        "severity": "high",
        "source": {
          "file": "routes.py",
          "line": 15,
          "function": "get_user",
          "code": "user_id = request.args.get('id')"
        },
        "sink": {
          "file": "db/queries.py",
          "line": 42,
          "function": "find_user",
          "code": "cursor.execute(f'SELECT * FROM users WHERE id={user_id}')"
        },
        "flow_length": 2
      }
    ],
    "vulnerability_count": 1,
    "risk_level": "high",
    "taint_flows": [
      {
        "source": "routes.py:15",
        "sink": "db/queries.py:42",
        "hops": ["routes.py:get_user", "db/queries.py:find_user"]
      }
    ],
    "mermaid_diagram": "graph LR\n  A[routes.py:get_user] -->|user_id| B[db/queries.py:find_user]\n  B -->|SQL| C((SINK: execute))",
    "modules_analyzed": 10,
    "depth_reached": 3,
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
    "vulnerabilities": [
      {
        "id": "vuln_001",
        "type": "sql_injection",
        "cwe": "CWE-89",
        "severity": "high",
        "confidence": 0.92,
        "source": {
          "file": "routes.py",
          "line": 15,
          "function": "get_user",
          "code": "user_id = request.args.get('id')",
          "taint_type": "http_request"
        },
        "sink": {
          "file": "db/queries.py",
          "line": 42,
          "function": "find_user",
          "code": "cursor.execute(f'SELECT * FROM users WHERE id={user_id}')",
          "sink_type": "sql_execute"
        },
        "flow_length": 2,
        "sanitizers_checked": ["escape_sql", "parameterize"],
        "sanitized": false
      }
    ],
    "vulnerability_count": 1,
    "risk_level": "high",
    "taint_flows": [
      {
        "source": "routes.py:15",
        "sink": "db/queries.py:42",
        "hops": ["routes.py:get_user", "db/queries.py:find_user"],
        "confidence": 0.92,
        "data_type": "string"
      }
    ],
    "sanitized_flows": [
      {
        "source": "routes.py:25",
        "sanitizer": "utils.py:sanitize_input",
        "sink": "db/queries.py:50",
        "safe": true
      }
    ],
    "framework_context": {
      "framework": "flask",
      "route_decorator": "@app.route('/user/<id>')",
      "injection_hints": ["request.args", "request.form"]
    },
    "mermaid_diagram": "graph LR\n  subgraph routes.py\n    A[get_user:15]\n  end\n  subgraph db/queries.py\n    B[find_user:42]\n  end\n  A -->|user_id: 0.92| B\n  B -->|SQL| C((SINK))",
    "modules_analyzed": 45,
    "depth_reached": 10
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
    "vulnerabilities": [
      {
        "id": "vuln_001",
        "type": "sql_injection",
        "cwe": "CWE-89",
        "severity": "high",
        "confidence": 0.92,
        "source": {
          "file": "routes.py",
          "line": 15,
          "function": "get_user",
          "code": "user_id = request.args.get('id')",
          "taint_type": "http_request",
          "service": "api-gateway"
        },
        "sink": {
          "file": "db/queries.py",
          "line": 42,
          "function": "find_user",
          "code": "cursor.execute(f'SELECT * FROM users WHERE id={user_id}')",
          "sink_type": "sql_execute",
          "service": "user-service"
        },
        "flow_length": 2,
        "cross_service": true,
        "service_boundary": "REST",
        "compliance_impact": ["PCI-DSS-6.5.1", "OWASP-A03"]
      }
    ],
    "vulnerability_count": 1,
    "risk_level": "high",
    "taint_flows": [],
    "microservice_boundaries": [
      {
        "from_service": "api-gateway",
        "to_service": "user-service",
        "boundary_type": "REST",
        "endpoint": "/internal/users/{id}",
        "taint_carried": ["user_id"]
      }
    ],
    "global_flow_summary": {
      "entry_points_analyzed": 15,
      "services_traversed": 3,
      "database_sinks": 8,
      "external_api_sinks": 2
    },
    "distributed_trace_view": {
      "trace_id": "trace_abc123",
      "spans": [
        {"service": "api-gateway", "operation": "get_user", "tainted_vars": ["user_id"]},
        {"service": "user-service", "operation": "find_user", "sink": "sql"}
      ]
    },
    "mermaid_diagram": "graph LR\n  subgraph api-gateway\n    A[routes.py:get_user]\n  end\n  subgraph user-service\n    B[db/queries.py:find_user]\n  end\n  A -->|REST: user_id| B\n  B -->|SQL| C((SINK))",
    "modules_analyzed": 250,
    "depth_reached": 15,
    "scan_duration_ms": 4500
  },
  "id": 1
}
```

---

## Roadmap

### Cross-Cutting Research Topics

**Research queries (cross-cutting):**
- What is the FP/FN budget for cross-file flows per sink type (SQL/command/path/XSS/etc), and how do we measure it with a stable benchmark suite?
- How do we define and test “deterministic taint results” (stable ordering, stable flow identity, stable confidence scores) across OS/CPUs?
- What are the safe semantics for partial results under timeouts/module caps (when to omit, when to return partial, and how to label it)?
- How should confidence be calibrated (not just “severity-based”), and what evidence should raise/lower it (sanitizers, path length, aliasing uncertainty)?
- What are the privacy boundaries for reporting flows (avoid leaking secrets in traces/diagrams/logs) while still being actionable?

**Research topics (cross-cutting):**
- Evaluation harness: curated multi-file fixtures, golden outputs, regression scoring, and CI release gates
- Flow identity: stable IDs for flows/vulnerabilities to enable delta reporting across commits
- Determinism: stable sorting, stable truncation policies, stable diagram generation
- Scalability: module discovery bounds, incremental caching, and time/memory envelopes for large repos
- Safety: conservative defaults, best-effort semantics, and explicit uncertainty labeling

**Success metrics (cross-cutting):**
- Determinism: identical results for identical inputs across supported environments
- Quality: measurable FP/FN budgets met on a benchmark suite per sink type
- Safety: no secret exfiltration paths in reports/artifacts; routine scanning in CI
- Reliability: graceful degradation under timeouts/caps (schema-valid partials, no hangs)

### v1.1 (Q1 2026): Enhanced Tracking

#### Community Tier
- [ ] Improved sanitizer recognition (common safe wrappers)
- [ ] Better import resolution for local packages (less missed edges)
- [ ] Clearer partial-result signaling when clamped (depth/modules)

**Research queries (v1.1 / Community):**
- Which sanitizer patterns are safe to recognize by default without causing false negatives?
- What is the minimal evidence to mark a flow as “partial due to cap” while keeping schema stable?
- Which import-resolution failures are most common in the wild (relative imports, namespace packages, monorepos)?

**Success metrics (v1.1 / Community):**
- Sanitizer fixtures: reduced false positives on curated sanitizer benchmark without increasing false negatives beyond budget
- Import resolution: fewer “missing module edge” misses on standard package layouts
- Partial results: explicit, consistent labeling when results are clamped

#### Pro Tier
- [ ] Better handling of callback chains
- [ ] Async/await taint tracking
- [ ] Promise chain analysis

**Research topics (v1.1 / Pro):**
- Callback/promise modeling: practical static approximations and the FP budget impact
- Async/await propagation rules and where to be conservative (await boundaries, tasks)
- Flow deduplication: merging equivalent flows without hiding distinct sinks

**Success metrics (v1.1 / Pro):**
- Async fixtures: improved recall on async-heavy benchmarks without increasing FP beyond budget
- Stability: flow identity remains stable across minor refactors (renames/reorders)

#### Enterprise Tier
- [ ] Microservice boundary tracking
- [ ] gRPC/REST API taint flow
- [ ] Kafka/message queue taint tracking

**Research topics (v1.1 / Enterprise):**
- Service boundary inference: manifests, directories, build descriptors, and ownership signals
- API boundary modeling: request/response schemas, serialization boundaries, and contract drift
- Message queues: correlation IDs, topic routing, and taint persistence semantics

**Success metrics (v1.1 / Enterprise):**
- Cross-service benchmarks: measurable recall lift on multi-service fixtures with calibrated confidence
- Explainability: each cross-service flow includes evidence (boundary type, endpoint/topic) and uncertainty

### v1.2 (Q2 2026): Performance Optimization

#### Community Tier
- [ ] Faster module discovery under tight caps
- [ ] Deterministic truncation (stable ordering of which modules/flows are kept)
- [ ] Lightweight caching for repeated scans of the same fixture set

**Research queries (v1.2 / Community):**
- What truncation policy best preserves “most actionable” findings under module caps (sink severity, confidence, proximity)?
- How do we ensure determinism when the file system order differs across OS/filesystems?
- What caching granularity gives speedups without stale/incorrect flows?

**Success metrics (v1.2 / Community):**
- Performance: faster scans on small repos/fixtures without changing findings
- Determinism: stable results under cap pressure (same kept modules/flows)
- Caching: measurable speedup on repeated runs with zero correctness regressions

#### Pro Tier
- [ ] Incremental analysis (only changed files)
- [ ] Parallel file processing
- [ ] Smart boundary detection

**Research topics (v1.2 / Pro):**
- Incremental invalidation strategy: content hash vs semantic hash and correctness pitfalls
- Deterministic parallelism: stable aggregation independent of worker count
- Boundary detection: how to avoid false edges from similarly named modules/files

**Success metrics (v1.2 / Pro):**
- Incremental: re-scan time scales with change size (not repo size) on benchmark suite
- Parallel: throughput improves with cores while results remain bit-identical

#### Enterprise Tier
- [ ] Distributed analysis
- [ ] Real-time taint streaming
- [ ] Historical taint pattern analysis

**Research topics (v1.2 / Enterprise):**
- Distributed sharding model: partitioning, retries, partial failures, and consistent merge
- Streaming contract: partial result schemas, backpressure, and final-stability semantics
- Historical trends: persistence model, retention, and reproducible comparisons across versions

**Success metrics (v1.2 / Enterprise):**
- Distributed: predictable scaling on large repos with clear failure semantics
- Streaming: schema-valid partials; stable final result identity
- Trends: durable, queryable history with explicit retention policy

### v1.3 (Q3 2026): Language Expansion

#### Community Tier
- [ ] Expanded heuristic context scanning for non-Python projects (no taint guarantees)
- [ ] Better file-type discovery and filtering (ignore vendor/build outputs)
- [ ] Unified “unsupported language” messaging with actionable guidance

**Research queries (v1.3 / Community):**
- What minimum set of heuristics is safe/helpful for non-Python repos without implying taint-tracking coverage?
- Which directories should be ignored by default across ecosystems (node_modules, dist, target, vendor) to reduce noise?
- What messaging prevents users from over-trusting results while still being useful?

**Success metrics (v1.3 / Community):**
- Noise reduction: fewer irrelevant files analyzed by default on polyglot repos
- Clarity: users correctly understand “Python-focused taint tracking” vs heuristic context
- Stability: heuristics do not break existing Python-focused outputs

#### Pro Tier
- [ ] Java cross-file tracking
- [ ] Go cross-package tracking
- [ ] Rust cross-crate tracking

**Research topics (v1.3 / Pro):**
- Per-language source/sink taxonomy and normalization into a unified result schema
- Parsing strategy tradeoffs: tree-sitter vs language-native ASTs and error recovery
- Cross-language consistency: how confidence scoring maps across languages

**Success metrics (v1.3 / Pro):**
- New languages meet baseline extraction + taint-flow accuracy on curated fixtures
- Unified schema remains stable; new languages add data without breaking old clients

#### Enterprise Tier
- [ ] C++ cross-TU (translation unit) tracking
- [ ] Multi-language taint tracking

**Research topics (v1.3 / Enterprise):**
- Cross-language boundary modeling: serialization (JSON/protobuf), DB layers, and shared message buses
- C++ TU challenges: macros, templates, and build-system integration boundaries
- Governance: policy-driven allow/deny of flows by boundary type and confidence

**Success metrics (v1.3 / Enterprise):**
- Multi-language fixtures: measurable recall lift on mixed-language repos with calibrated confidence
- Policy controls: low false positives with clear override workflows and audit trail

### v1.4 (Q4 2026): Advanced Features

#### Community Tier
- [ ] Higher-signal Mermaid diagrams (stable, smaller, easier to read)
- [ ] Minimal “why flagged” evidence summaries per finding
- [ ] Suggested next checks (e.g., run single-file scan on implicated files)

**Research queries (v1.4 / Community):**
- What diagram summarization best reduces clutter while preserving the critical path?
- What is the smallest evidence payload that meaningfully explains a flow (source, sink, key hops) without leaking secrets?
- Which recommended follow-up actions reduce time-to-fix most effectively?

**Success metrics (v1.4 / Community):**
- Diagram usability: smaller diagrams with preserved critical path on benchmark fixtures
- Explainability: higher user correctness in identifying root cause from evidence summaries
- Workflow: reduced time-to-triage in internal benchmarks

#### Pro Tier
- [ ] Taint flow visualization
- [ ] Interactive taint exploration
- [ ] Automated taint breaking suggestions

**Research topics (v1.4 / Pro):**
- Visualization semantics: represent confidence/uncertainty without misleading users
- Suggestion safety: propose remediations that are source-grounded and avoid behavior changes
- UX for exploration: slicing large graphs, deduping, and stable navigation targets

**Success metrics (v1.4 / Pro):**
- Visualization: stable diagrams with bounded size; low-noise navigation on large projects
- Suggestions: low regression rate in remediation benchmark; conservative confidence

#### Enterprise Tier
- [ ] Taint policy enforcement
- [ ] Compliance-based taint rules
- [ ] Automated boundary hardening

**Research topics (v1.4 / Enterprise):**
- Policy model: rule language, inheritance, and tamper-evident provenance
- Compliance mapping: SOC2/GDPR/PCI-style controls translated into boundary/flow rules
- Auto-hardening safety: safe-by-default patches, approval workflows, rollback semantics

**Success metrics (v1.4 / Enterprise):**
- Policies: reproducible enforcement with audit logs and stable rule evaluation
- Compliance: measurable reduction in policy-violating flows on benchmark repos

---

## Known Issues & Limitations

### Current Limitations
- **Depth limit (Community/Pro):** Community and Pro enforce max-depth caps (Community 3, Pro 10)
- **Dynamic imports:** Runtime-only imports not tracked
- **Reflection:** Dynamic method calls may be missed
- **Language scope (v1.0):** Cross-file taint tracking is Python-focused

### Planned Fixes
- v1.1: Improved dynamic import inference
- v1.2: Partial reflection support
- v1.3: Configurable depth limits

---

## Success Metrics

### Performance Targets
- **Scan time:** <2s for 10-file analysis
- **Accuracy:** >90% correct taint flows
- **False positive rate:** <15%

### Adoption Metrics
- **Usage:** 100K+ cross-file scans per month
- **Vulnerabilities found:** 10K+ cross-file issues detected

---

## Dependencies

### Internal Dependencies
- `security/analyzers/taint_tracker.py` - Single-file taint
- `ast_tools/dependency_parser.py` - Import resolution
- `graph_engine/graph.py` - Dependency graph

### External Dependencies
- None

---

## Breaking Changes

None planned for v1.x series.

**API Stability Promise:**
- Tool signature stable
- Finding format consistent with security_scan

---

**Last Updated:** December 30, 2025  
**Next Review:** March 31, 2026
