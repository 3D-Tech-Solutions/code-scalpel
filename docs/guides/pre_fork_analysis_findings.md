# Pre-Fork Architecture Analysis Findings

## 1. Public Contract Inventory

### Tool Registry Truth
The server currently registers **20 MCP tools**.
- **Read/Map:** `get_project_map`, `crawl_project`, `extract_code`, `get_file_context`, `get_symbol_references`
- **Graph/Dependency:** `get_call_graph`, `get_graph_neighborhood`, `get_cross_file_dependencies`, `validate_paths`
- **Analysis:** `analyze_code`, `type_evaporation_scan`
- **Security:** `unified_sink_detect`, `security_scan`, `cross_file_security_scan`, `scan_dependencies`
- **Symbolic/Testing:** `symbolic_execute`, `generate_unit_tests`, `simulate_refactor`
- **Write/Governance:** `update_symbol`, `verify_policy_integrity`

### Behavioral Contract
- **Transport:** stdio and HTTP transports are supported. HTTP binds to `127.0.0.1` by default.
- **CLI:** `code-scalpel mcp` is the primary entrypoint.
- **Error Shapes:** Tools return structured objects, often with `success: bool` and `error: str | None`.

## 2. Tier Boundary Feasibility (Coupling Analysis)

### Dependency Graph by Tool
- **Heavy Dependencies:**
    - `z3-solver`: Used by `symbolic_execute`, `generate_unit_tests`, `type_inference`, `taint_tracker`.
    - `tree-sitter`: Used by `analyze_code` (multi-lang), `unified_sink_detect`, `type_evaporation_scan`, and parsers.
    - `networkx`: Used by `get_call_graph`, `get_graph_neighborhood`, `get_cross_file_dependencies`, `build_pdg`.

### Coupling Hotspots
- **Symbolic Execution Tools:** The `symbolic_execution_tools` module is a monolith containing both "Pro" features (symbolic exec, test gen) and "Community" features (sink detection).
    - *Recommendation:* Split `unified_sink_detect` (regex/pattern-based) from `symbolic_execute` (Z3-based) to avoid pulling Z3 into the Community tier if possible, or accept Z3 as a core dep.
- **Graph Engine:** `UniversalGraph` and `networkx` usage is spread across tools.
    - *Recommendation:* Ensure `get_project_map` (Community) doesn't trigger expensive graph builds intended for Pro tools.

### Cross-File Compute Boundary
- **Implicit Project-Wide Tools:**
    - `crawl_project`: Currently does a file walk. Needs strict "Discovery" vs "Deep" mode implementation.
    - `get_call_graph`, `get_graph_neighborhood`, `get_cross_file_dependencies`: These are inherently project-wide and compute-intensive.
    - `cross_file_security_scan`: Explicitly project-wide.

### Write-Safety Boundary
- `update_symbol` uses `SurgicalPatcher`.
- *Risk:* If `SurgicalPatcher` relies on `simulate_refactor` logic (which might use Z3 or heavy analysis), Community writes might become heavy.
- *Finding:* `simulate_refactor` is a separate tool. `update_symbol` seems to use lighter validation, which is good for Community.

## 3. Security Architecture (Production Hardening)

### File Access Model
- **Validation:** `_validate_path_security` exists in `server.py` and checks against `ALLOWED_ROOTS`.
- *Gap:* Need to verify *every* tool calls this. `validate_paths` tool exposes this logic, but internal calls must be consistent.

### Code Execution Guarantees
- **No Execution:** Grep for `eval`, `exec`, `subprocess` shows they are primarily in *detection patterns* (strings looking for vulnerabilities), not in server logic executing user code.
- *Exception:* `scan_dependencies` might run `pip-audit` or similar via subprocess? (Need to verify implementation details of `scan_dependencies`).

### HTTP Posture
- Binds to `127.0.0.1`.
- *Recommendation:* Ensure `allow-lan` flag is explicit and warns user.

## 4. Packaging & Distribution Architecture

### Current Packaging
- `pyproject.toml` defines one `code-scalpel` package with `all`, `polyglot`, `dev` extras.
- *Change:* Need to split into `code-scalpel` (Community) and `code-scalpel-pro` (Pro).

### Pro Package Design
- *Strategy:* `code-scalpel-pro` should depend on `code-scalpel`.
- *Registry Extension:* `code-scalpel-pro` can define a separate MCP server entrypoint that imports the core server and registers extra tools, OR use a plugin mechanism if the core server supports it.
- *Recommendation:* Simple entrypoint wrapper `code-scalpel-pro mcp` is easiest.

## 5. Operational Architecture

### Config Layering
- Currently relies on CLI args (`--root`, `--transport`) and some env vars (`SCALPEL_MCP_OUTPUT`).
- *Recommendation:* Standardize on `config.yaml` or `.env` for Enterprise settings (SSO, license keys).

## 6. Data Model & Evidence Architecture

### Event Model
- *Gap:* No standardized audit event schema exists yet.
- *Recommendation:* Define `AuditLogEvent` Pydantic model for Enterprise.

### Report Schemas
- *Gap:* No compliance report generation yet.
- *Recommendation:* Define JSON schemas for SOC2/HIPAA reports.

## Summary of Required Refactors Before Fork
1. **Decouple Z3 (Optional but nice):** If `unified_sink_detect` can run without Z3, move Z3-dependent code to a separate module to keep Community lighter.
2. **Strict "Discovery" Crawl:** Implement the "Discovery" mode for `crawl_project` that avoids full graph building.
3. **Path Validation Audit:** Audit all 20 tools to ensure they call `_validate_path_security`.
4. **Entrypoint Split:** Prepare the code structure to allow a "Pro" wrapper to register additional tools.
