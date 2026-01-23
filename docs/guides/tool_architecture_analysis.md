# Code Scalpel Tool Architecture Analysis (V1.0 Baseline)

This document provides a comprehensive architectural analysis of the Code Scalpel toolset as of the V1.0 pre-fork baseline. It details the implementation, dependencies, performance characteristics, and tiering strategy for every MCP tool.

---

## Tool Output/Feature Split Matrix (Community vs Pro vs Enterprise)

This matrix is the **contract-ready** per-tool split. Every MCP tool has an explicit output/feature definition per tier.

Legend:
- **Community:** single-file or discovery outputs; developer utility.
- **Pro:** project-wide computation, cross-file context, deeper engineering workflows.
- **Enterprise:** governance + identity + auditability + evidence exports + integrations.

| Tool | Community output/features | Pro adds (output/features) | Enterprise adds (output/features) |
|---|---|---|---|
| `analyze_code` | Single-file structure/metrics; multi-language parsing where supported | Repo context enrichment (imports/types) where applicable | Standardized evidence output; policy-required checks; audit refs |
| `extract_code` | Extract symbol/component from a file path with metadata | Cross-file extraction helpers (resolve referenced symbols/imports) | RBAC/redaction policies; access auditing; retention controls |
| `get_file_context` | Read-only file context within allowed roots | Optional related-file context (imports/callers) | Access controls + audit logging of file reads |
| `get_symbol_references` | Reference search (single-file or lightweight scan) | Indexed/project-wide references and better resolution | RBAC-scoped reference reporting + export |
| `get_project_map` | Repo structure overview + entrypoint hints | Higher-fidelity module/service boundary hints | Org-scoped indexing + retention + audit export |
| `crawl_project` | Discovery crawl: inventory + entrypoint/framework hints; no graphs | Deep crawl: richer per-module summaries; optional indexing hooks | Scheduled indexing across repos; audit log refs; centralized config |
| `validate_paths` | Safety primitive: root/path validation utilities | Same | Enterprise policies for allowed roots; workspace partitioning + RBAC |
| `get_call_graph` | (Optional) single-file call relationships only | Full project call graph + metadata/confidence | Org-scale graphs; multi-repo mapping; exportable evidence |
| `get_graph_neighborhood` | Not included (keeps Pro crisp) | K-hop neighborhood from built graph for context windows | Governance rules on what can be surfaced; audit refs |
| `get_cross_file_dependencies` | Not included | Project dependency graph + confidence scoring | Compliance-friendly dependency evidence + attestations |
| `unified_sink_detect` | Single-snippet sink detection + CWE/OWASP mapping | Repo-aware tuning/deduping (where applicable) | Policy-driven blocking decisions; signed evidence output |
| `security_scan` | Single-file vulnerability findings + hints | Cross-file context where available; fix impact hints | Waivers/approvals; SIEM/webhooks; audit export |
| `cross_file_security_scan` | Not included | Cross-file taint/flow analysis across modules | Compliance reports; scheduled scans; centralized rule/policy mgmt |
| `scan_dependencies` | Basic vulnerable component scan (OSV) | Transitive attribution + remediation planning | Allow/deny lists; SBOM/attestations; audit exports |
| `type_evaporation_scan` | Not included | TS↔Python boundary correlation and findings | Framework policy packs; CI gating + waiver workflow; evidence export |
| `symbolic_execute` | Not included | Symbolic exploration of paths (Z3) + models | Policy hooks (required for high-risk classes); traceable evidence |
| `generate_unit_tests` | Not included | Deterministic tests generated from symbolic models | Governance: required tests for risk areas; traceability reports |
| `simulate_refactor` | Not included | Change simulation (syntax + security regression checks) | Approvals + signed patch bundles + audit export |
| `update_symbol` | Safe symbol replacement + validation | Repo-aware impact checks (callers/refs) before write | Mandatory approvals; budgets; signed patches; audit trail |
| `verify_policy_integrity` | Not included | Verify policy integrity (hash/signature) | Central policy distribution; attestations; org policy management |

---

## 1. Read & Map Tools

These tools provide context, navigation, and code retrieval. They are the foundation of the "Community" tier.

For the explicit tier output definitions, see the **Tool Output/Feature Split Matrix** above.

### `get_project_map`
- **Purpose:** High-level overview of project structure.
- **Implementation:** Recursive directory walk with file type counting and heuristic entrypoint detection.
- **Dependencies:** `pathlib`, `os`.
- **Performance:** O(files). Fast for most repos; can be slow on massive monorepos without ignore-list optimization.
- **Tier:** Community.
- **Enterprise Upgrade:** RBAC-filtered views, cached indexing for massive repos.

### `crawl_project`
- **Purpose:** Discover project content and structure.
- **Implementation:**
  - *Current:* Recursive walk + file reading.
  - *V1.0 Split:*
    - **Discovery Mode (Community):** Metadata-only walk. Returns file paths, languages, sizes. No file content reading.
    - **Deep Mode (Pro):** Full content analysis, import resolution, graph building.
- **Dependencies:** `pathlib`, `os` (Discovery); `tree-sitter`, `networkx` (Deep).
- **Performance:** Discovery is O(files). Deep is O(code_volume).
- **Tier:** Split (Community/Pro).

### `extract_code`
- **Purpose:** Surgically extract specific symbols (functions/classes) to save context window.
- **Implementation:** AST parsing (Python) or Tree-sitter (Polyglot) to locate nodes by name/span. Returns source text + metadata.
- **Dependencies:** `ast`, `tree-sitter`.
- **Performance:** O(file_size). Very fast.
- **Tier:** Community.
- **Enterprise Upgrade:** Redaction of secrets in output, audit logging of access.

### `get_file_context`
- **Purpose:** Read file content with safety checks.
- **Implementation:** `pathlib.read_text` with strict root validation.
- **Dependencies:** `pathlib`.
- **Performance:** O(file_size).
- **Tier:** Community.
- **Enterprise Upgrade:** Audit logging.

### `get_symbol_references`
- **Purpose:** Find usages of a symbol.
- **Implementation:**
  - *Community:* Text-based search (grep-like) or single-file AST search.
  - *Pro:* Project-wide index lookup or cross-file AST resolution.
- **Dependencies:** `ast`, `tree-sitter`.
- **Performance:** O(files) for text search.
- **Tier:** Community (bounded scope).

---

## 2. Graph & Dependency Tools

These tools build relationships between code units. They are compute-intensive and typically "Pro".

### `get_call_graph`
- **Purpose:** Map function call relationships.
- **Implementation:** Static analysis (AST/Tree-sitter) to find call sites, resolved against imports. Builds a `networkx` DiGraph.
- **Dependencies:** `networkx`, `ast`, `tree-sitter`.
- **Performance:** O(code_volume^2) in worst case (resolution). Heavy compute.
- **Tier:** Pro (recommended). Community version (if any) must be strictly scoped (single file).

### `get_graph_neighborhood`
- **Purpose:** Retrieve K-hop context around a node for LLMs.
- **Implementation:** Graph traversal (BFS) on the pre-built `UniversalGraph`.
- **Dependencies:** `networkx`.
- **Performance:** Fast query O(k * branching_factor), but requires expensive graph build first.
- **Tier:** Pro.

### `get_cross_file_dependencies`
- **Purpose:** Analyze imports and dependencies across the entire project.
- **Implementation:** Parse all files, resolve imports to file paths, build dependency graph.
- **Dependencies:** `networkx`, `ast`, `tree-sitter`.
- **Performance:** O(files * imports).
- **Tier:** Pro.

### `validate_paths`
- **Purpose:** Security utility to check if paths are safe/allowed.
- **Implementation:** Path resolution and prefix checking against `ALLOWED_ROOTS`.
- **Dependencies:** `pathlib`.
- **Performance:** O(1).
- **Tier:** Community (Safety primitive).

---

## 3. Analysis Tools

These tools inspect code structure and quality.

### `analyze_code`
- **Purpose:** Extract structure (AST), metrics (complexity), and metadata.
- **Implementation:** `ast` (Python) or `tree-sitter` (Polyglot). Calculates cyclomatic complexity.
- **Dependencies:** `ast`, `tree-sitter`.
- **Performance:** O(file_size).
- **Tier:** Community.

### `type_evaporation_scan`
- **Purpose:** Detect loss of type safety at boundaries (e.g., TS frontend -> Python backend).
- **Implementation:** Cross-file analysis matching TS `fetch` calls to Python `@app.route` handlers.
- **Dependencies:** `tree-sitter`, `ast`.
- **Performance:** O(frontend_files * backend_files).
- **Tier:** Pro.

---

## 4. Security Tools

These tools detect vulnerabilities.

### `unified_sink_detect`
- **Purpose:** Find dangerous function calls (sinks) like `eval`, `exec`.
- **Implementation:** Regex/Pattern matching (fast) or lightweight AST traversal.
- **Dependencies:** `re`, `tree-sitter` (optional).
- **Performance:** O(file_size). Fast.
- **Tier:** Community.

### `security_scan`
- **Purpose:** Single-file vulnerability scan.
- **Implementation:** AST analysis for known bad patterns (e.g., hardcoded secrets, unsafe yaml load).
- **Dependencies:** `ast`, `bandit` (logic adapted).
- **Performance:** O(file_size).
- **Tier:** Community.

### `cross_file_security_scan`
- **Purpose:** Taint tracking across file boundaries.
- **Implementation:** Taint analysis on the project graph. Traces data flow from sources to sinks across modules.
- **Dependencies:** `networkx`, `z3-solver` (optional for constraint solving).
- **Performance:** High compute.
- **Tier:** Pro.

### `scan_dependencies`
- **Purpose:** Check 3rd-party packages for CVEs.
- **Implementation:** Parses `requirements.txt`/`package.json`, queries OSV database (or local DB).
- **Dependencies:** `requests` (for API), `packaging`.
- **Performance:** Network bound.
- **Tier:** Community (basic). Pro/Ent adds policy/reporting.

---

## 5. Symbolic Execution & Testing

These are advanced "Pro" differentiators relying on formal methods.

### `symbolic_execute`
- **Purpose:** Explore execution paths mathematically.
- **Implementation:** Converts AST to Z3 constraints. Solves for inputs that satisfy path conditions.
- **Dependencies:** `z3-solver`.
- **Performance:** Exponential worst case (path explosion). Heaviest tool.
- **Tier:** Pro.

### `generate_unit_tests`
- **Purpose:** Create tests covering symbolic paths.
- **Implementation:** Uses `symbolic_execute` results to generate `pytest` code strings.
- **Dependencies:** `z3-solver`.
- **Performance:** Bound by symbolic execution.
- **Tier:** Pro.

### `simulate_refactor`
- **Purpose:** Verify safety of a patch before applying.
- **Implementation:** Applies patch in memory, parses result, checks for syntax errors and security regressions.
- **Dependencies:** `ast`, `unified_sink_detect`.
- **Performance:** O(file_size).
- **Tier:** Pro (Workflow value).

---

## 6. Write & Governance Tools

These tools modify code or enforce rules.

### `update_symbol`
- **Purpose:** Apply changes to a file.
- **Implementation:** Locates symbol, replaces text, validates syntax.
- **Dependencies:** `ast`, `tree-sitter`.
- **Performance:** O(file_size).
- **Tier:** Community (Basic write). Pro adds impact analysis.

### `verify_policy_integrity`
- **Purpose:** Ensure governance policies haven't been tampered with.
- **Implementation:** Cryptographic hash verification of policy files.
- **Dependencies:** `cryptography` (or hashlib).
- **Performance:** O(policy_size).
- **Tier:** Pro/Enterprise.

---

## Architectural Recommendations for V1.0 Split

1.  **Decouple Z3:** Ensure `unified_sink_detect` and `security_scan` (Community) do *not* import `z3-solver`. Move Z3 logic to a dedicated `symbolic_engine` module used only by Pro tools.
2.  **Graph Engine Isolation:** Ensure `get_project_map` (Community) does not trigger the full `UniversalGraph` build. It should use a lightweight directory walker.
3.  **Crawl Modes:** Refactor `crawl_project` to explicitly support a `metadata_only=True` flag for the Community tier.
4.  **Pro Entrypoint:** Create a clean pattern where `code-scalpel-pro` imports the base server and adds the Pro tools, rather than having one monolithic server file with runtime flags.
