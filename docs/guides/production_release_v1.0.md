## Code Scalpel V1.0 Production Release — Minimum Requirements

### Executive Summary

The V1.0 release positions Code Scalpel as the first comprehensive code analysis MCP server with an open-core business model. The three tiers are designed to capture individual developers (Free), professional teams (Pro), and regulated enterprises (Enterprise).

---

## Implementation Plan (Do This First — No Code Moves Until This Is Agreed)

This section is a **step-by-step execution plan** for creating a V1.0 “Production” version as a fork from the current repo.

### Non-Negotiable Decisions (Lock These Before Any Engineering)

1) **Licensing strategy (Community):**
	- Community remains **MIT** (true open-core).
	- Implication: Community cannot include restrictions like “no commercial use” (MIT allows commercial use). Any such restriction would require a different license.

2) **Enforcement strategy (Pro/Enterprise):**
	- Do **distribution separation** for Pro/Enterprise rather than relying on runtime checks inside the MIT wheel.
	- Pro/Enterprise capabilities live in separate packages and images (e.g., `code-scalpel-pro`, `code-scalpel-enterprise`).

3) **Public contract:**
	- Freeze the **tool surface** per tier (exact list + parameter schemas). This becomes the contract for docs, clients, and acceptance tests.
	- The contract includes a **standard response envelope** (required fields, structured errors, upgrade hints) and a stable **error code registry**.
	- Enterprise adds a stable **audit event schema** (what’s logged and how), without ever logging code contents.

4) **Influencer/evaluation access:**
	- Provide Pro/Enterprise access **for free** via a time-limited license or private package distribution (GitHub Packages / private index / download portal). This is a GTM choice and does not change the architecture.

> Note: This document is product/engineering planning, not legal advice. Final licensing/EULA/ToS should be reviewed by counsel.

---

## Step-by-Step Execution Plan (End-to-End)

### Phase 0 — Inventory + Contract Freeze (1–2 days)

**Goal:** Determine what the current repo actually ships, and define the V1.0 Production contract.

Steps:
1. **Inventory MCP tools in current repo**
	- Output: a definitive list of all tools currently registered by the server, with name + arguments + response model.
	- Evidence: generated `docs/reference/mcp_tools_current.md` (or equivalent) checked into the Production fork.
	- Current repo note: there are already broad MCP tool contract tests (see [tests/test_mcp_all_tools_contract.py](../../tests/test_mcp_all_tools_contract.py)) and a torture-test contract harness in the Ninja Warrior repo (see [../Code-Scalpel-Ninja-Warrior/torture-tests/mcp_contract/](../../../Code-Scalpel-Ninja-Warrior/torture-tests/mcp_contract/)).

2. **Publish the V1.0 tier tool contract (draft → final)**
	- Output: a tier matrix (Community vs Pro vs Enterprise) using the **actual MCP tool IDs**.
	- Important: If you prefer marketing-friendly names (e.g., “analyze_code_structure”), decide whether to:
	  - keep the underlying tool IDs as-is and document friendly names in docs, or
	  - introduce aliases (new tool IDs) while preserving backwards compatibility.

3. **Freeze the V1.0 response envelope + error codes + audit schema (contract-first)**
	- Output: one canonical “response envelope” required for all tool responses (all tiers).
	- Output: one canonical “error code registry” (machine-parseable) shared across tools.
	- Output: one canonical “audit event schema” (Enterprise) shared across tools.
	- Evidence (recommended): `docs/reference/mcp_response_envelope.md`, `docs/reference/error_codes.md`, `docs/reference/audit_event_schema.md`.

#### Proposed Tier Tool Lists (Draft — Based on Current Repo)

This is a **starting point** that matches the MCP tools currently registered by the server in this repo.
Treat it as the draft contract to confirm/edit before you freeze Phase 0.

Implementation note (current repo): the MCP server supports tier selection via `--tier` and via
`CODE_SCALPEL_TIER` / `SCALPEL_TIER` env vars. The generated, source-of-truth tier matrix is:
- `docs/reference/mcp_tools_by_tier.md`

| MCP Tool ID | Community | Pro | Enterprise | Notes |
|---|---:|---:|---:|---|
| `analyze_code` | ✅ | ✅ | ✅ | Structure + metrics; multi-language “auto” mode |
| `extract_code` | ✅ | ✅ | ✅ | Token-efficient extraction by file path |
| `update_symbol` | ✅ | ✅ | ✅ | Surgical write tool; consider Community limits/guards |
| `get_project_map` | ✅ | ✅ | ✅ | Project structure overview |
| `get_file_context` | ✅ | ✅ | ✅ | Read-only context for a file |
| `get_symbol_references` | ✅ | ✅ | ✅ | Reference search; can be capped in Community |
| `get_call_graph` | ◻️ | ✅ | ✅ | Recommend Pro (can be compute-heavy) |
| `get_graph_neighborhood` | ❌ | ✅ | ✅ | Pro differentiator: k-hop neighborhood |
| `get_cross_file_dependencies` | ❌ | ❌ | ✅ | Enterprise-only: cross-file dependency extraction |
| `cross_file_security_scan` | ❌ | ❌ | ✅ | Enterprise-only: cross-file security coverage |
| `security_scan` | ✅ | ✅ | ✅ | Single-file security scan |
| `unified_sink_detect` | ✅ | ✅ | ✅ | Polyglot sink detection; low-friction, high value |
| `scan_dependencies` | ✅ | ✅ | ✅ | Vulnerable components (OSV) scanning |
| `symbolic_execute` | ❌ | ✅ | ✅ | Pro differentiator: symbolic execution |
| `generate_unit_tests` | ❌ | ✅ | ✅ | Pro differentiator: test generation |
| `simulate_refactor` | ❌ | ✅ | ✅ | Pro differentiator: change simulation + safety |
| `type_evaporation_scan` | ❌ | ✅ | ✅ | Pro differentiator: TS→Python boundary analysis |
| `crawl_project` | ◻️ | ✅ | ✅ | Recommend Pro (resource-intensive); Community could cap scope |
| `validate_paths` | ✅ | ✅ | ✅ | Safety: root/path validation; keep in Community |
| `verify_policy_integrity` | ❌ | ❌ | ✅ | Enterprise-only: governance/policy integrity verification |

Legend:
- ✅ Included in tier
- ❌ Not included in tier
- ◻️ Optional/depends on final product boundary

Enterprise-only tools (future, in `code-scalpel-enterprise`):
- `generate_compliance_report` (PDF/JSON)
- `configure_sso` / `test_sso_connection`
- `manage_roles` / `audit_export`

> Tip: If you want the Free tier to stay “single-file only”, keep any cross-file or project-wide graph builders (dependency extraction, neighborhood, crawl) out of Community.

#### Community vs Pro: `crawl_project` (Feature Split, Not “Usage Caps”)

If Community includes `crawl_project`, the recommended split is **different functionality**, not “same thing but throttled.”

**Community `crawl_project` = Discovery Crawl (feature-limited):**
- Produces a **high-level project inventory** only:
	- language breakdown and file counts
	- top-level directories and “shape” of the repo
	- framework hints (e.g., Flask/Django/FastAPI/Express/Spring) via heuristics
	- likely entrypoints (e.g., `app.py`, `main.py`, `server.ts`, `pom.xml`) and why
	- “recommended next tools” list (e.g., `get_project_map`, `extract_code`, `security_scan`)
- Does **not** attempt:
	- cross-file dependency resolution
	- call graphs / neighborhood graphs
	- cross-file security/taint tracking
	- deep AST extraction across the whole repo
	- returning file contents (only metadata/paths)

**Pro `crawl_project` = Deep Crawl (full functionality):**
- Adds **project-wide computation** and richer outputs:
	- dependency/import resolution across files
	- optional call graph construction / indexing
	- optional cross-file security scanning hooks
	- higher-fidelity structure summaries per module/package

**Stability guardrails (implementation detail, not a sales knob):**
- Regardless of tier, the server should have sane protections (timeouts, max result size, safe roots) to prevent accidental resource exhaustion.
- Community vs Pro differentiation should be communicated as “what it can do,” not “how much you’re allowed to do.”

---

## Three-Level Feature Split by Tool (V1.0 Contract Draft)
---

## Required Output Fields & Contract Testability (All Tools)

To ensure every tool is contract-testable and client-compatible, the following output fields are **required** for all MCP tool responses (unless otherwise noted):

### Universal Output Fields (all tools, all tiers)
- `tier`: string, one of `community`, `pro`, `enterprise` (always present)
- `tool_version`: string, semantic version of the tool implementation (always present)
- `tool_id`: string, the canonical MCP tool ID (always present)
- `request_id`: string, caller-provided or server-generated correlation ID (always present)
- `capabilities`: array of strings, describes what this invocation supports (e.g., `["single-file", "discovery-crawl"]`)
- `duration_ms`: number, end-to-end tool runtime in milliseconds (recommended; required for Pro/Enterprise)
- `error`: object or null, present if the tool failed (standardized error model)
- `upgrade_hints`: array of objects, present if the user is at a lower tier and a higher tier is available; each object includes:
	- `feature`: string (what is unlocked)
	- `tier`: string (which tier unlocks it)
	- `reason`: string (why it’s not available at current tier)

### Tool-Specific Required Fields (examples)
- `crawl_project`:
	- Community: `project_inventory`, `entrypoints`, `framework_hints`, `recommended_next_tools`, `upgrade_hints`
	- Pro: all above + `dependency_index`, `structure_summaries`, `cross_file_hints`
	- Enterprise: all above + `org_indexing_metadata`, `audit_log_refs`
- `security_scan`:
	- All: `findings`, `file_path`, `language`, `tier`, `tool_version`, `capabilities`, `error`, `upgrade_hints`
	- Pro/Enterprise: `cross_file_context`, `fix_impact`, `policy_blocking_decisions`, `audit_refs`
- `update_symbol`:
	- All: `success`, `file_path`, `symbol_name`, `tier`, `tool_version`, `capabilities`, `error`, `upgrade_hints`
	- Pro/Enterprise: `impact_analysis`, `required_approvals`, `audit_refs`

### Error Model (all tools)
- All errors must be returned as a structured object with at least:
	- `error`: string (human-readable)
	- `error_code`: string (machine-parseable, e.g., `invalid_argument`, `timeout`, `not_implemented`, `upgrade_required`)
	- `error_details`: object or null (optional structured details safe for clients; never include code contents)
	- `tier`: string (the tier at which the error occurred)
	- `tool_version`: string
	- `tool_id`: string
	- `request_id`: string

Recommended error codes (minimum set):
- `invalid_argument`, `invalid_path`, `forbidden`, `not_found`, `timeout`, `too_large`, `resource_exhausted`, `not_implemented`, `upgrade_required`, `dependency_unavailable`, `internal_error`

### Versioning in Responses
- Every tool response must include `tool_version` (semver, matches the implementation)
- If the tool contract changes, increment MINOR or MAJOR as appropriate

### Upgrade Hinting (all tools)
- If a user at a lower tier requests a feature only available at a higher tier, the response must include `upgrade_hints` with:
	- `feature`: what is missing
	- `tier`: which tier unlocks it
	- `reason`: why it’s not available (e.g., “cross-file analysis is a Pro feature”)

### Contract Test Requirements
- For every tool/tier, contract tests must:
	- verify all required fields are present and correctly typed
	- verify `tier` and `tool_version` are always present
	- verify `tool_id` and `request_id` are always present
	- verify `upgrade_hints` is present and correct when a feature is unavailable at current tier
	- verify error responses are structured and include `error_code`, `tier`, and `tool_version`
- For every new tool or contract change, add/extend contract tests before release

### Path Safety (applies to any tool that reads/writes files)

Treat path safety as part of the public contract, not “internal hardening.”

Minimum requirements:
- Canonicalize and validate all paths (resolve symlinks; reject traversal).
- Enforce an allowlist of roots (workspace roots); return `invalid_path` or `forbidden` deterministically.
- Never allow tools to read outside configured roots, even indirectly.
- Ensure error responses do not leak file contents.

---

This section is the **concrete, per-tool** Community/Pro/Enterprise split. It is designed to avoid “usage caps as a product feature” and instead define **different outcomes** per tier.

Guiding principle:
- **Community:** local, developer-friendly utility; single-file or shallow repo discovery.
- **Pro:** project-wide computation and higher-fidelity engineering outputs.
- **Enterprise:** organization-grade controls (SSO/RBAC), evidence, approvals, integrations, and on-prem readiness.

> Note: Enterprise differentiation is often delivered as *workflow and governance layers* around the same underlying analysis rather than “more detections.”

### Read/Map Tools

| Tool | Community (what it does) | Pro (adds) | Enterprise (adds) |
|---|---|---|---|
| `get_project_map` | Project overview: directories, key files, language mix | Smarter service/module boundaries + cross-file hints | Org-scoped indexing + RBAC (repo/tool permissions) + retention controls |
| `crawl_project` | Discovery crawl: inventory + entrypoint/framework hints; no graphs | Deep crawl: project-wide indexing and structured summaries | Centralized indexing across repos; scheduled crawls; audit logging + exports |
| `extract_code` | Extract a symbol/component from a file by path; LLM-friendly prompt formatting | Cross-file extraction helpers (resolve imports, include referenced symbols) | RBAC + redaction policies (e.g., secrets); evidence snapshots for audits |
| `get_file_context` | Read-only context for a file (safe boundaries) | Context across related files (imports/callers) | Access controls + retention + audit trail of accessed paths |
| `get_symbol_references` | Find references within allowed roots (bounded output) | Cross-file reference indexing + higher recall | RBAC + exportable “who/what changed” reference reports |

### Graph/Dependency Tools

| Tool | Community (what it does) | Pro (adds) | Enterprise (adds) |
|---|---|---|---|
| `get_call_graph` | Optional (if included): basic call graph for a small scope | Full repo call graph + richer metadata and stability | Org-scale graphs; multi-repo/service mapping; export for governance reviews |
| `get_graph_neighborhood` | Not included (keeps Pro crisp) | K-hop neighborhood extraction for context windows | Governance policies (what is allowed to be surfaced); audit + evidence |
| `get_cross_file_dependencies` | Not included | Dependency extraction across the project; confidence scoring | Compliance-friendly dependency reports + attestations + approvals |
| `validate_paths` | Safety primitive: ensures file access stays within configured roots | Same | Enterprise policies for allowed roots + workspace partitioning + RBAC |

### Analysis Tools

| Tool | Community (what it does) | Pro (adds) | Enterprise (adds) |
|---|---|---|---|
| `analyze_code` | Single-file structure/metrics across languages | Repo-context improvements (resolving types/import context) | Standardized evidence output; policy-driven required checks |
| `type_evaporation_scan` | Not included | Cross-boundary analysis (TS↔Python) with correlation | Policy packs for common frameworks; CI gating + waiver workflow |

### Security Tools

| Tool | Community (what it does) | Pro (adds) | Enterprise (adds) |
|---|---|---|---|
| `unified_sink_detect` | Single-snippet sink detection (polyglot) + OWASP/CWE mapping | Repo-aware confidence tuning and dedupe | Policy-driven blocking decisions; signed evidence outputs |
| `security_scan` | Single-file security scan with clear findings | Higher-fidelity findings using repo context; fix impact hints | Approval flows, audit exports, SIEM/webhooks, exception/waiver management |
| `cross_file_security_scan` | Not included | Cross-file security and taint-style flows across modules | Compliance reporting; scheduled scans; centralized rule/policy management |
| `scan_dependencies` | Vulnerable component scan from manifests/requirements | Multi-ecosystem + transitive attribution; remediation planning | Allow/deny lists, approved vendors, SBOM + attestations, audit exports |

### Symbolic Execution / Testing / Change Safety

| Tool | Community (what it does) | Pro (adds) | Enterprise (adds) |
|---|---|---|---|
| `symbolic_execute` | Not included (keeps Pro differentiated) | Symbolic exploration of execution paths (Z3) | CI policy hooks (required for certain risk classes); audit evidence |
| `generate_unit_tests` | Not included | Deterministic test generation from symbolic paths | Governance: test-gen required for high-risk changes; traceability reports |
| `simulate_refactor` | Not included | Simulate change safety before applying (syntax/security checks, patch mode) | Approvals + cryptographic signing of approved patch bundles + audit export |

### Write/Governance Tools

| Tool | Community (what it does) | Pro (adds) | Enterprise (adds) |
|---|---|---|---|
| `update_symbol` | Safe symbol replacement + validation; local developer workflow | Repo-aware impact checks (callers/refs) before write | Mandatory approvals, change budgets, signed patch bundles, audit trail |
| `verify_policy_integrity` | Not included | Verify governance/policy integrity for Pro features | Enterprise policy distribution + attestation; centralized policy management |

#### Enterprise “Always-On” Cross-Cutting Features (applies to many tools)

To make Enterprise *obviously* distinct across the toolset, implement these as shared platform features:

- **SSO/RBAC:** users only see repos/tools they’re allowed to.
- **Audit trail:** every tool invocation can be logged with stable event schemas (no code contents).
- **Approvals & waivers:** “break glass” and exceptions with expiry and ticket linkage.
- **Compliance exports:** PDF/JSON reports for SOC2/HIPAA/PCI evidence.
- **Deployability:** on-prem/air-gapped support, private registry, reproducible builds.

Acceptance criteria (for this section):
- Every tool has a tier definition (Community/Pro/Enterprise).
- Enterprise differentiation is expressed as governance/workflow/integration, not just “more results.”

3. **Define “V1.0 Production” acceptance tests (contract tests)**
	- For each tier, create automated tests verifying:
	  - server starts
	  - tool discovery returns the expected tool list
	  - each tool validates inputs and returns expected schema
	- Evidence (recommended): `tests/production_contract/` suite.
	- Current repo note: MCP contract-style coverage already exists under [tests/](../../tests/) (for example [tests/test_mcp_all_tools_contract.py](../../tests/test_mcp_all_tools_contract.py)). The V1.0 fork should consolidate this into an explicit tier-aware contract suite.

Acceptance criteria (Phase 0 complete):
- Tool names and schemas are frozen per tier.
- Contract tests exist for the frozen tool surface.

---

### Pre-Fork Enhancements (Recommended Before Tier-Splitting)

These are pragmatic engineering improvements that make tiering, contracts, and enterprise governance *much easier*.

1) **Standard response envelope everywhere**
	- Ensure every tool response conforms to the envelope above, including structured `error` and deterministic `error_code`.
	- Ensure every response contains `tool_id`, `tool_version`, and `request_id` for correlation.

2) **Tier-aware tool registration (registry extension pattern)**
	- Refactor registration into explicit functions/modules:
	  - `register_core_tools(server)` (Community)
	  - `register_pro_tools(server)` (Pro)
	  - `register_enterprise_tools(server)` (Enterprise)
	- Pro/Enterprise packages extend the Community server by importing and calling additional registration functions.

3) **Discovery vs Deep crawl as distinct outcomes (not throttles)**
	- Keep `crawl_project` Community output strictly metadata-only (inventory/entrypoints/hints).
	- Move dependency indexing/graphs/cross-file hints into Pro/Enterprise.

4) **Observability + audit schema (Enterprise-grade, code-safe)**
	- Standardize an audit event schema for tool calls (no source code in logs).
	- Include `request_id`, `tool_id`, `tier`, `duration_ms`, and high-level counters (files_touched, bytes_read) rather than content.
	- Add an “audit reference” field to Enterprise responses where applicable.

---

### Phase 1 — Repo + Package Topology (2–4 days)

**Goal:** Make tiering enforceable via distribution, with minimal disruption.

Recommended topology:

1. **Community repo/package (MIT)**
	- Package: `code-scalpel` (public PyPI)
	- Contains: Community MCP server and Community tools only

2. **Pro package (commercial/private)**
	- Package: `code-scalpel-pro` (private index)
	- Depends on: `code-scalpel`
	- Contains: Pro-only tool implementations + tool registrations

3. **Enterprise package (commercial/private)**
	- Package: `code-scalpel-enterprise` (private index)
	- Depends on: `code-scalpel-pro` and/or `code-scalpel`
	- Contains: enterprise-only integrations (SSO/SAML), compliance reports, on-prem tooling, RBAC

Steps:
1. Create the Production fork repos (or a mono-repo with multiple distributions):
	- `code-scalpel` (Community)
	- `code-scalpel-production` (build/orchestration repo; optional)
	- `code-scalpel-pro` (private)
	- `code-scalpel-enterprise` (private)

2. Implement “tool registry extension” pattern
	- Community server registers Community tools.
	- Pro package extends the registry by importing the Community server and registering additional tools.
	- Enterprise extends Pro similarly.
	- Output: `code-scalpel-pro mcp ...` and `code-scalpel-enterprise mcp ...` entrypoints.

Acceptance criteria (Phase 1 complete):
- Installing only Community exposes only Community tools.
  - `pip install code-scalpel` → Community tool list.
- Installing Pro exposes Community + Pro tool list.
  - `pip install code-scalpel-pro` → Community+Pro tool list.
- Installing Enterprise exposes Community + Pro + Enterprise tool list.
  - `pip install code-scalpel-enterprise` → full list.

---

### Phase 2 — Community V1.0 Cut (1–2 weeks)

**Goal:** Ship a polished Community V1.0 that’s stable and adoption-friendly.

Steps:
1. **Align documentation with the frozen Community contract**
	- Getting Started must match:
	  - version
	  - tool count
	  - install instructions
	  - supported transports

2. **Define and enforce Community limits (technical, not legal)**
	- If you want limits like “1,000 LOC per request”, enforce them via:
	  - explicit server-side guards
	  - deterministic error messages
	- (Avoid “commercial use restrictions” in Community if MIT.)

3. **Packaging and release confidence**
	- Evidence required for each release:
	  - `python -m build` produces sdist/wheel
	  - `twine check` passes
	  - `pytest` passes
	  - `pyright` passes
	  - `pip-audit` passes

Acceptance criteria (Phase 2 complete):
- Community V1.0 can be installed from PyPI.
  - `pip install code-scalpel`
- MCP server starts and responds to tool discovery and tool calls.
- Community docs are consistent and complete.

---

### Phase 3 — Pro V1.0 (1–3 weeks)

**Goal:** Monetize via Pro packaging + distribution, not by weakening Community.

Steps:
1. **Move Pro-only tools/features into `code-scalpel-pro`**
	- Cross-file analysis tools
	- Advanced graph tools
	- Enhanced security gating/guardrails (as product scope dictates)

2. **License & distribution**
	- Recommended: distribution enforcement + optional runtime entitlement checks.
	- Build a simple entitlement flow:
	  - user purchases subscription
	  - receives access token/license
	  - uses it to authenticate to private package registry OR download wheel
	- Influencer program: provide free entitlements to selected users.

3. **Pro documentation**
	- Policy Engine guide
	- Audit Trail setup
	- “How Pro differs from Community” (clear boundary)

Acceptance criteria (Phase 3 complete):
- Pro tool list appears only when Pro package is installed.
  - Community installs never expose Pro tools.
- Pro distribution workflow works end-to-end (purchase → access → install).

---

### Phase 4 — Enterprise V1.0 (2–6 weeks)

**Goal:** Sell enterprise outcomes: identity, reporting, deployment, and governance.

Steps:
1. Implement SSO/SAML and RBAC (if required for launch)
2. Compliance report generation (PDF/JSON) with deterministic output schemas
3. On-prem deployment guide and hardened deployment defaults
4. Security questionnaire responses + contract templates (business workstream)

Acceptance criteria (Phase 4 complete):
- Enterprise features are installable and testable.
  - SSO docs + working integration tests
  - report generation functional
  - on-prem deployment instructions validated

---

## What Changes in This Checklist Under the Recommended Strategy

- Community “limits” should be **technical limits** (LOC caps, request caps), not usage restrictions.
- Pro/Enterprise “license gating middleware” becomes “**separate distribution + entitlements**”.
- Tool counts (15/19/20) must become **one canonical number per tier**.

---

### **Free Tier (Community)**

**Target Users:** Individual developers, open source contributors, students, evaluation

**Core MCP Tools (Full Access — Canonical Tool IDs):**
- `analyze_code` — Structure + metrics (multi-language “auto”)
- `extract_code` — Token-efficient extraction by file path
- `update_symbol` — Surgical modification (write)
- `get_project_map` — Project structure overview
- `get_file_context` — Read-only context for a file
- `get_symbol_references` — Reference search (cap output in Community)
- `security_scan` — Single-file security scan
- `unified_sink_detect` — Polyglot sink detection
- `scan_dependencies` — Vulnerable components scan (OSV)
- `validate_paths` — Root/path safety checks

**Capabilities:**
- Single-file analysis (no cross-file / no project-wide graph builds)
- Multi-language support is allowed in Community, but **scope is single-file**
- Basic security scanning (single-file) + dependency scanning
- Cache-enabled analysis (local only)
- CLI access
- Community Discord support

**Limits:**
- 1,000 LOC per analysis request
- No Policy Engine
- No Audit Trail
- Commercial use allowed (MIT)
- No SLA

**Release Blockers (Free Tier):**

| Release Blocker | Current State (this workspace) | Suggested Evidence/Link |
|---|---|---|
| PyPI package installable via `pip install code-scalpel` | In Progress (build + metadata checks pass locally; publish requires running tag-based workflow) | `.github/workflows/publish-pypi.yml`, `python -m build` + `python -m twine check dist/*` output |
| MCP server starts and responds to protocol messages | Done (MCP all-tools contract test exercises startup + tool calls) | [tests/test_mcp_all_tools_contract.py](../../tests/test_mcp_all_tools_contract.py), [tests/test_mcp_transports_end_to_end.py](../../tests/test_mcp_transports_end_to_end.py) |
| Community tool list frozen and verified by contract tests | In Progress (all-tools list is validated; per-tier tool lists not implemented yet) | [tests/test_mcp_all_tools_contract.py](../../tests/test_mcp_all_tools_contract.py); Tier-aware suite (recommended): `tests/production_contract/` |
| Getting Started guide complete | In Progress | [README.md](../../README.md) (needs V1.0 alignment) |
| MIT license file present | Done | [LICENSE](../../LICENSE) |
| Basic error handling with clear messages | Not Started (no standardized MCP response envelope/error registry enforced across all tools) | Contract tests asserting structured `error` + `error_code` (to add) |

---

### **Pro Tier**

**Target Users:** Professional developers, small teams, SaaS builders, consultancies

**Everything in Free, plus:**

**Advanced MCP Tools (Canonical Tool IDs):**
- `get_cross_file_dependencies` — Project-wide dependency extraction
- `cross_file_security_scan` — Cross-file security scan
- `get_graph_neighborhood` — K-hop neighborhood extraction (context window optimization)
- `get_call_graph` — Call graph generation (project scope)
- `crawl_project` — Project crawl/analysis (project scope)
- `symbolic_execute` — Symbolic execution
- `generate_unit_tests` — Test generation from symbolic execution
- `simulate_refactor` — Simulate edits safely before applying
- `type_evaporation_scan` — TS→Python boundary analysis
- `verify_policy_integrity` — Governance/policy integrity verification

**Pro Features (Already Implemented):**
- **Policy Engine** — Declarative Rego-based governance
- **Audit Trail** — Timestamped decision logging (HMAC-signed)
- **Cryptographic Policy Verification** — SHA-256 signed manifests
- **Change Budgeting** — Per-file/per-session edit limits
- **Semantic Blocking** — Pattern-based vulnerability prevention

**Notes (to keep V1.0 consistent):**
- Items like `cross_file_taint_tracking`, `build_unified_service_graph`, and `vulnerability_shield` are **product concepts** in this document.
	- If they are not exposed as MCP tools under those exact IDs, either:
		- map them to the canonical tool IDs listed above, or
		- add new tool IDs as explicit aliases and cover them with contract tests.

**Capabilities:**
- Unlimited LOC per request
- Full multi-language support (Python, JS/TS, Java)
- Cross-file analysis with confidence scoring
- Confidence decay on deep dependency chains
- Priority email support (48-hour response)
- Commercial use license

**Limits:**
- Single-seat license (per-developer)
- No SSO/SAML integration
- No custom policy templates
- No on-premise deployment support
- No compliance reporting

**Pricing Signal:** $29-49/month per seat (competitive with SonarQube Cloud, Snyk)

**Release Blockers (Pro Tier):**

| Release Blocker | Current State (this workspace) | Suggested Evidence/Link |
|---|---|---|
| Pro package distribution working (private registry or download workflow) | Not Started | Private index/portal docs + install proof |
| Entitlement workflow working (purchase → access token/license → install) | Not Started | Minimal entitlement spec + integration test |
| Pro tools available only when Pro package is installed | Not Started (requires package split + registry extension) | Tier-aware `tools/list` contract tests |
| Pro feature documentation (Policy Engine guide, Audit Trail setup) | In Progress (internal docs exist; needs Pro packaging framing) | [docs/guides/change_budgeting.md](./change_budgeting.md), [src/code_scalpel/policy_engine/README.md](../../src/code_scalpel/policy_engine/README.md) |
| Policy Engine end-to-end functional | Done (implementation + tests present) | [tests/test_policy_engine.py](../../tests/test_policy_engine.py) |
| Change Budgeting tested in CI | Done (tests present; ensure in release gates) | [tests/test_change_budgeting.py](../../tests/test_change_budgeting.py) |
| Benchmark evidence package complete (Ninja Warrior torture test) | In Progress (harness exists; V1.0 run/publish pending) | [Code-Scalpel-Ninja-Warrior/](../../../Code-Scalpel-Ninja-Warrior/) |
| Terms of Service / EULA drafted | Not Started | Legal review artifacts |
| Payment integration (Stripe or Paddle) | Not Started | Payment integration tests + webhook verification |
| License key delivery workflow | Not Started | License format + delivery automation proof |

---

### **Enterprise Tier**

**Target Users:** Regulated industries (finance, healthcare), Fortune 500, government contractors

**Everything in Pro, plus:**

**Enterprise Features:**
- **Compliance Reporter** — PDF/JSON audit reports for SOC2, HIPAA, PCI-DSS
- **Custom Policy Templates** — Pre-built for Spring, Django, Express, JPA
- **SSO/SAML Integration** — Enterprise identity provider support
- **On-Premise Deployment** — Air-gapped installation option
- **Private MCP Registry** — Internal tool distribution
- **Role-Based Access Control** — Fine-grained permissions

**Notes (to keep V1.0 consistent):**
- Enterprise is expected to introduce new admin/reporting tool IDs (e.g., `generate_compliance_report`).
	Those should be designed via RFC + contract tests before they are considered “release blockers complete.”

**Advanced Security:**
- Real-time policy violation alerts (webhook/SIEM integration)
- Human-in-the-loop override workflow (TOTP-based)
- Policy versioning and migration tools
- Custom semantic analyzer plugins
- CVE pattern library updates (monthly)

**Support & SLA:**
- Dedicated account manager
- 4-hour critical issue response
- 99.9% uptime SLA
- Quarterly security review calls
- Custom training sessions

**Deployment Options:**
- Cloud-hosted (multi-tenant or dedicated)
- Self-hosted with license server
- Hybrid (analysis in cloud, policies on-premise)

**Pricing Signal:** Custom pricing, typically $500-2,000/month base + per-seat

**Release Blockers (Enterprise Tier):**

| Release Blocker | Current State (this workspace) | Suggested Evidence/Link |
|---|---|---|
| Enterprise license key format (org-level, seat count) | Not Started | License format spec + validation tests |
| SSO integration documentation | Not Started | SSO setup guide + integration tests |
| On-premise deployment guide | Not Started (Docker quickstart exists; enterprise-hardening pending) | [DOCKER_QUICK_START.md](../../DOCKER_QUICK_START.md) (extend for on-prem) |
| Compliance report generation functional | Done (implementation + tests present) | [src/code_scalpel/governance/compliance_reporter.py](../../src/code_scalpel/governance/compliance_reporter.py), [tests/test_compliance_reporter.py](../../tests/test_compliance_reporter.py) |
| Webhook/SIEM integration tested | Not Started | Webhook schema + integration tests |
| Enterprise sales materials (pitch deck, ROI calculator) | Not Started | Sales collateral |
| Contract templates (MSA, DPA) | Not Started | Legal-reviewed templates |
| Security questionnaire responses prepared | Not Started | Completed questionnaire + evidence links |

---

### Additional High-Value Checklists (Recommended)

These are “make production/forking painless” checklists. They are intentionally implementation-agnostic and can be checked off with evidence.

#### Contract Freeze Checklist (V1.0)

| Item | Status | Evidence |
|---|---|---|
| Canonical tool list per tier is finalized (tool IDs) | Not Started | Tier-specific `tools/list` snapshots |
| Input/output schemas frozen per tool | Not Started | Generated schema docs checked in |
| Response envelope implemented everywhere | Not Started | Contract tests asserting envelope fields (to add) |
| Error code registry defined and used everywhere | Not Started | `error_code` assertions across tool failures (to add) |
| Deprecation policy for tool IDs and fields | In Progress | “Versioning, Compatibility, and Deprecation Policy” section |

#### Tier Split Implementation Checklist

| Item | Status | Evidence |
|---|---|---|
| `register_core_tools` / `register_pro_tools` / `register_enterprise_tools` split | Not Started | Code diff + unit tests |
| Community wheel contains only Community tools | Not Started | Install + `tools/list` contract proof |
| Pro wheel extends Community (no copying) | Not Started | Install + `tools/list` contract proof |
| Enterprise wheel extends Pro (no copying) | Not Started | Install + `tools/list` contract proof |
| CI matrix runs contract tests per tier | Not Started | CI config + logs |

#### Release Evidence Bundle Checklist (Every Release)

| Item | Status | Evidence |
|---|---|---|
| Build artifacts (sdist/wheel) + metadata validation | In Progress (prior bundles exist; local build + twine check passes) | [release_artifacts/](../../release_artifacts/) (prior releases), `.github/workflows/publish-pypi.yml` |
| Full pytest log + summary | In Progress | [release_artifacts/](../../release_artifacts/) |
| Coverage report (`coverage.xml`) | In Progress | [release_artifacts/](../../release_artifacts/) |
| Dependency audit (e.g., `pip-audit`) | In Progress | [release_artifacts/](../../release_artifacts/) |
| MCP tool discovery snapshot (`tools/list`) | In Progress | MCP tool evidence bundles in [release_artifacts/](../../release_artifacts/) |
| SBOM (CycloneDX/SPDX) | In Progress | SBOMs in [release_artifacts/](../../release_artifacts/) |

#### Security & Privacy Checklist (All Tiers)

| Item | Status | Evidence |
|---|---|---|
| Path validation enforced for all file reads/writes | In Progress | Contract tests for traversal/symlink rejection |
| Logs do not contain code contents | In Progress | Logging tests / log review rules |
| Network access policy documented per tool (offline-by-default) | In Progress | Tool docs + tests (no external calls by default) |
| Deterministic resource limits (timeouts/result size) | In Progress | Tests asserting `timeout`/`too_large` errors |
| Secret handling/redaction policy for outputs | In Progress | Security scan tests + redaction tests |

#### Observability & Audit Checklist (Enterprise)

| Item | Status | Evidence |
|---|---|---|
| `request_id` correlation supported end-to-end | Not Started | Contract tests validating field presence (to add) |
| Audit event schema versioned and stable | Not Started | `audit_event_schema.md` + schema tests |
| Audit logs are content-safe (no code bodies) | In Progress | Tests asserting redaction |
| Export format defined (JSON/CSV/HTML) + retention policy | In Progress (export implemented; retention policy/documentation pending) | [tests/test_coverage_additional_gaps.py](../../tests/test_coverage_additional_gaps.py), [src/code_scalpel/autonomy/audit.py](../../src/code_scalpel/autonomy/audit.py) |

---

### V1.0 Launch Readiness Checklist

#### Current Workspace State Snapshot (as of 2025-12-23)

This repo already includes substantial “production-style” evidence and testing; V1.0 work is primarily about **freezing the tier contract** and **splitting distributions**.

- Release evidence bundles exist for prior releases under [release_artifacts/](../../release_artifacts/) (coverage, SBOMs, security evidence, MCP tool evidence).
- MCP contract-style tests already exist in [tests/](../../tests/) (see [tests/test_mcp_all_tools_contract.py](../../tests/test_mcp_all_tools_contract.py)).
- Ninja Warrior torture-test harness exists in the workspace under [Code-Scalpel-Ninja-Warrior/](../../../Code-Scalpel-Ninja-Warrior/) (including MCP contract tests).
- The V1.0 production planning and architecture docs are already present under [docs/guides/](./).

**Important reality check (today):** the current `code-scalpel` package ships *all* tools together (Community/Pro/Enterprise separation is not enforced yet). The V1.0 “Production” work remains primarily: (1) freeze the tier contract, then (2) split distributions.

#### Next Development (Recommended Order)

1. **Generate a definitive MCP tool inventory artifact** (name + args schema + response model) and check it in (e.g., `docs/reference/mcp_tools_current.md`).
2. **Introduce tier-aware tool registration** (`register_core_tools`, `register_pro_tools`, `register_enterprise_tools`) and a config switch selecting a tier.
3. **Add tier-aware contract tests** that assert `tools/list` equals the frozen matrix per tier (and that higher-tier tools are absent when not installed).
4. **Implement a standardized MCP response envelope + error code registry** across tools (and update contract tests to enforce it).
5. **Split distribution** into `code-scalpel` (MIT Community) + separate Pro/Enterprise packages/images and update CI/release workflows accordingly.

#### **Critical Path (All Tiers)**

| Item | Status | Owner | Due |
|------|--------|-------|-----|
| Distribution + entitlement system (Pro/Ent) | Not Started | — | Week 1 |
| User-facing documentation | In Progress | — | Week 2 |
| Benchmark evidence package | In Progress (Ninja Warrior harness exists; V1.0 packaging pending) | — | Week 2 |
| Tool contract tests (MCP) | In Progress (broad coverage exists; tier-freeze suite pending) | — | Week 1 |
| Payment/licensing integration | Not Started | — | Week 3 |
| Marketing site / landing page | Not Started | — | Week 3 |
| Pricing page with tier comparison | Not Started | — | Week 3 |

#### **Technical Validation**

| Validation | Target | Evidence Required | Current State |
|------------|--------|-------------------|--------------|
| Test coverage | ≥90% | `coverage.xml` in release artifacts | Evidence exists for prior releases in [release_artifacts/](../../release_artifacts/) (V1.0 evidence bundle still needs to be generated) |
| False positive rate | <5% | Vulnerability benchmark results | Ninja Warrior benchmark harness exists; publish V1.0 run output |
| Cache performance | >200x speedup | Performance benchmark log | Prior release evidence exists; define V1.0 threshold + publish run output |
| LOC throughput | >200 LOC/s | Benchmark suite results | Harness exists; publish V1.0 run output |
| OWASP block rate | 100% | `owasp_coverage.json` | Prior release evidence exists; publish V1.0 run output |

#### **Documentation Deliverables**

- [ ] Installation Guide (all platforms)
- [ ] Getting Started (5-minute quickstart)
- [ ] MCP Tool Reference (per tier: Community / Pro / Enterprise)
- [ ] Policy Engine Guide (Pro/Enterprise)
- [ ] Integration Recipes (LangChain, Autogen, Cursor, Cline)
- [ ] API Reference (if exposing REST)
- [ ] FAQ / Troubleshooting
- [ ] Changelog / Release Notes

---

## Release Evidence (What to Publish With Every Release)

These artifacts make releases repeatable and defensible.

- **Build artifacts:** sdist + wheel (`dist/`), plus `twine check` output
- **Test evidence:** `pytest` results summary and `coverage.xml` (if coverage is a target)
- **Security evidence:**
  - dependency audit output (`pip-audit` or equivalent)
  - static scan output (Bandit/ruff rules as applicable)
- **Tool contract evidence:** snapshot of tool discovery (`tools/list`) and per-tool schema
- **Benchmark evidence:** Ninja Warrior evidence bundle + performance logs

Recommended (strongly):
- **SBOM:** generate CycloneDX or SPDX for shipped wheels/images
- **Container provenance:** pin base image digests and record build metadata

---

## Versioning, Compatibility, and Deprecation Policy

1) **Semantic versioning (SemVer)**
	- MAJOR: breaking tool changes (rename/remove tool, incompatible schema)
	- MINOR: add tools or backwards-compatible fields
	- PATCH: bugfixes/perf/security fixes with no contract breaks

2) **MCP tool contract stability**
	- Tool IDs are the public API surface.
	- Do not rename tool IDs in-place.
	- If you need a marketing name, document it as an alias in docs; keep tool IDs stable.

3) **Deprecation process**
	- Add a deprecation notice in tool output (and docs) for at least one MINOR cycle.
	- Provide a migration guide and automated lint/check when feasible.
	- Remove only in the next MAJOR release.

---

## Security, Quality, and Operational Methodology (Ongoing)

This is how production quality is maintained after V1.0.

1) **Contract-first development**
	- Every new/changed MCP tool must come with:
	  - schema definition (inputs/outputs)
	  - contract tests (tool discoverable, validates args, stable response shape)

2) **Test strategy**
	- Unit tests for parsing/analysis internals
	- Contract tests for MCP tools (the public API)
	- End-to-end tests for stdio + HTTP transports

3) **CI gates (minimum)**
	- Formatting/lint
	- Type checking
	- `pytest`
	- packaging build + metadata validation
	- dependency audit

4) **Security response**
	- Define a SECURITY policy (intake, triage, severity classification)
	- Set a patch SLA for critical issues (e.g., 72 hours for CVSS high/critical)
	- Track security regressions with dedicated tests

5) **Performance methodology**
	- Maintain a benchmark suite with:
	  - fixed inputs
	  - defined hardware assumptions
	  - regression thresholds (fail builds on unacceptable slowdowns)

---

## Methodology for Future Development (How We Build V1.1+)

This is a repeatable process for extending the product without breaking the contract.

1) **RFCs for product-facing changes**
	- Required for: new tools, tool schema changes, tier boundary changes, licensing/distribution changes
	- RFC includes: motivation, user story, API/tool contract, security concerns, performance concerns, rollout plan

2) **ADRs for architecture decisions**
	- Record key decisions (package split, registry extension approach, entitlement mechanism)
	- Keep ADRs short and searchable

3) **Tier boundary discipline**
	- Community: single-file scope; avoid project-wide graph builders
	- Pro: cross-file/project-wide computation, advanced workflows
	- Enterprise: identity, reporting, deployment, admin capabilities

4) **Release train**
	- Weekly/biweekly minor releases; patch releases as needed
	- Every release publishes the Release Evidence bundle above

5) **Change management**
	- Backwards compatibility is default
	- Breaking changes only in MAJOR releases
	- Maintain a migration guide and deprecation notices

---

## Distribution, Entitlements, and Delivery (Pro/Enterprise)

Choose one primary delivery path and standardize it.

1) **Private Python packages (recommended for fastest iteration)**
	- GitHub Packages, private PyPI (e.g., Gemfury/Cloudsmith), or a simple authenticated download portal.
	- Entitlement is enforced by access to the private index/artifacts.

2) **Container images (recommended for teams/enterprise)**
	- Publish signed images for:
	  - Community (public)
	  - Pro/Enterprise (private)
	- Entitlement can be enforced by registry access and/or runtime auth.

3) **Runtime entitlements (optional, defense-in-depth)**
	- If added, keep it simple and robust:
	  - token-based check at server start
	  - tier is selected once and logged
	  - tools are registered according to tier
	- Avoid per-tool network calls on every request.

Influencer program implementation:
- Provide time-limited Pro/Enterprise entitlements.
- Create a “feedback intake” workflow (issue template + Discord/Slack channel + monthly call).

---

## Privacy, Data Handling, and Telemetry Posture

For developer trust, this should be explicit in V1.0.

- **Default posture:** no code uploaded anywhere by default.
- **Logs:**
  - do not log code contents
  - log only tool name, durations, and truncated errors
- **Telemetry:**
  - if any telemetry exists, make it opt-in and document exactly what is collected
- **Storage:**
  - caches should be local by default
  - document cache locations and retention

---

## Definition of Done (New Tool or Tool Change)

Any new/changed MCP tool is “done” only if all are true:

1) **API contract**
	- tool ID is final
	- input args validated with clear error messages
	- output schema stable and documented

2) **Tests**
	- unit tests for core logic
	- contract tests for MCP registration + schema
	- at least one negative/invalid-input test

3) **Security**
	- does not execute code
	- respects roots/path restrictions
	- has reasonable resource limits (size/time)

4) **Performance**
	- benchmarked on representative inputs
	- no obvious N^2 behavior on common paths

5) **Docs**
	- tool reference updated
	- examples included

---

## Release Runbook (Community / Pro / Enterprise)

This is the repeatable “how we ship” checklist.

1) **Pre-release**
	- update changelog/release notes
	- bump version
	- ensure contract tests match the intended tier surface
	- run release gates (format/lint, typecheck, tests, audits, build)

2) **Build & validate**
	- build wheels/sdists
	- validate metadata
	- generate SBOM (recommended)
	- build container images (if shipping images)

3) **Publish**
	- Community: publish to public PyPI + public image registry
	- Pro/Enterprise: publish to private index/registry (or portal)

4) **Post-release**
	- publish Release Evidence bundle
	- smoke-test install + MCP server startup (stdio + HTTP)
	- announce release and include upgrade notes

---

### Go/No-Go Decision Criteria

**Must Have for V1.0 Launch:**
1. Free tier fully functional (installable, documented, core tools working)
2. Pro tier license gating operational
3. At least one payment method accepting subscriptions
4. Benchmark evidence published and verifiable
5. Landing page live with pricing

**Can Ship Without (V1.1):**
- Enterprise SSO integration
- On-premise deployment docs
- Compliance reporter
- Custom policy templates
- SIEM webhooks