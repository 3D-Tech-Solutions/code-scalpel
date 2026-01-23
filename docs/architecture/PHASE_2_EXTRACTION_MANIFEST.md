# Phase 2 Extraction Manifest - v4.0.0 Split

**Date:** 2026-01-09  
**Status:** Ready for Execution  
**Pre-Flight:** ✅ Complete (v1.0.0 final monolith tagged and tested)  

---

## Overview

This manifest defines the precise code extraction plan for splitting the v1.0.0 monolith into three distribution packages:

- **Community** (`code-scalpel`) - MIT-licensed, public PyPI
- **Pro** (`code-scalpel-pro`) - Proprietary, private index
- **Enterprise** (`code-scalpel-enterprise`) - Proprietary, private index

All 22 MCP tools remain API-stable. Tier-gated fields are **additive only** (new fields for Pro/Enterprise, no removals).

---

## Phase 2 Execution Plan

### Step 1: Core Infrastructure Setup (Community)

**Purpose:** Create the shared Community package with all v1.0.0 core features.

**Repository:** `/mnt/k/backup/Develop/code_scalpel_community/`  
**Branch:** `phase-2-split`  

#### 1.1 Copy Core MCP Server & Tools
- **Source (monolith):** `src/code_scalpel/mcp/server.py`, `src/code_scalpel/mcp/` (entire module)
- **Target:** `code_scalpel_community/src/code_scalpel/mcp/`
- **Status:** Core infrastructure, no Community-only restrictions
- **Notes:** Handles tool routing, protocol negotiation, tier detection via license

#### 1.2 Copy Analysis & Code Extraction Tools
- **Source:** `src/code_scalpel/analysis/`, `src/code_scalpel/ast_tools/`, `src/code_scalpel/surgical_extractor.py`
- **Target:** `code_scalpel_community/src/code_scalpel/`
- **Features Included:**
  - `analyze_code` tool
  - `extract_code` tool (token-efficient server-side extraction)
  - `get_file_context` tool
  - `get_symbol_references` tool
  - `get_cross_file_dependencies` tool (Community: linear search; Pro: AST-aware; Enterprise: full graph)
  - Call graph generation (Community: basic; Pro/Enterprise: enriched)
- **Tier Limits:**
  - Community: 1,000 LOC max per file, 10,000 LOC per project
  - Pro: 50,000 LOC max
  - Enterprise: unlimited

#### 1.3 Copy Policy Engine & Licensing
- **Source:** `src/code_scalpel/licensing/`, `src/code_scalpel/policy_engine/`, `src/code_scalpel/tiers/`
- **Target:** `code_scalpel_community/src/code_scalpel/`
- **Purpose:** License validation, tier enforcement, feature gating
- **Community Behavior:**
  - All features available
  - No remote verification (offline-first)
  - MIT license header in all files

#### 1.4 Copy CLI & Configuration
- **Source:** `src/code_scalpel/cli.py`, `configs/limits.toml`, `src/code_scalpel/core.py`
- **Target:** `code_scalpel_community/`
- **Status:** Functional for Community tier users

#### 1.5 Copy Tests & Fixtures
- **Source:** `tests/` directory (all test files)
- **Target:** `code_scalpel_community/tests/`
- **Filter:** Remove Enterprise-only autonomy tests (CrewAI, AutoGen integration)
- **Baseline:** 6,685 passing tests (6,690 total minus 5 backburned autonomy tests)

### Step 2: Pro-Tier Extensions (Pro Package)

**Purpose:** Build Pro-tier enhancements (governance, advanced security, Pro features).

**Repository:** `/mnt/k/backup/Develop/code_scalpel_pro/`  
**Branch:** `phase-2-split-pro`  
**Dependencies:** Community `>=4.0.0`

#### 2.1 Governance & Compliance Tools
- **Source:** `src/code_scalpel/policy_engine/` (extended), `src/code_scalpel/surgery/` (governance modules)
- **New Tools for Pro:**
  - `code_policy_check` tool (Pro: 5 rulesets; Enterprise: 10+)
  - `verify_policy_integrity` tool (policy signature verification)
  - Governance audit logging (limited history)
- **Files:**
  - `src/code_scalpel_pro/policy/` - Pro-specific policy rules
  - `src/code_scalpel_pro/governance/` - Audit & approval workflows (limited)
  - `src/code_scalpel_pro/surgery/compliance.py` - Multi-repo refactoring with governance

#### 2.2 Security Enhancements (Pro)
- **Source:** `src/code_scalpel/security/analyzers/` (enhanced), `src/code_scalpel/taint_analysis/`
- **Pro-Specific Features:**
  - `security_scan` tool: SQL injection, XSS, command injection (10+ CWEs)
  - `cross_file_security_scan` tool: Taint tracking across files (limited to 100 files)
  - Library vulnerability scanning (via OSV, with caching)
  - Pro-tier limits: 100,000 LOC per scan, 100-file cross-file limit

#### 2.3 Advanced Refactoring Tools
- **Source:** `src/code_scalpel/surgery/`
- **Pro Features:**
  - `rename_symbol` tool: Multi-file safe refactoring
  - `simulate_refactor` tool: Verify changes are safe before applying
  - Approval workflow (basic; Enterprise: full workflow)
  - Multi-repo support (limited; Enterprise: full governance)

#### 2.4 Pro-Tier Test Suite
- **Source:** `tests/tools/` (Pro-specific test folders)
- **Files:**
  - `tests/tools/code_policy_check/`
  - `tests/tools/rename_symbol/`
  - `tests/tools/security_scan/`
  - Security tier tests (Pro coverage)
- **Expected Tests:** ~800 Pro-specific tests

### Step 3: Enterprise-Tier Features (Enterprise Package)

**Purpose:** Advanced autonomy, governance, and performance.

**Repository:** `/mnt/k/backup/Develop/code_scalpel_enterprise/`  
**Branch:** `phase-2-split-enterprise`  
**Dependencies:** Community `>=4.0.0`, Pro `>=4.0.0` (if governance enabled)

#### 3.1 Autonomy Framework (Enterprise)
- **Source:** `src/code_scalpel/agents/`, `src/code_scalpel/orchestration/`
- **Components:**
  - `base_agent.py` - Async agent framework
  - CrewAI integration (`crew_agent.py`) - backburned tests; code extracted
  - AutoGen integration (`autogen_agent.py`) - backburned tests; code extracted
  - Agent orchestration & task management
- **Enterprise Limit:** Full autonomy (unlimited agent count, orchestration complexity)
- **Note:** 5 autonomy tests backburned; feature code is production-ready; integration tests deferred to v1.0.0+

#### 3.2 Advanced Governance (Enterprise)
- **Source:** `src/code_scalpel/policy_engine/` (full), `src/code_scalpel/surgery/` (full governance)
- **Enterprise Features:**
  - Full approval workflow (`approval_workflow.py`)
  - Comprehensive audit trail (`audit_trail.py`)
  - Multi-repo governance (`multi_repo.py`, `repo_wide.py`)
  - 20+ policy templates
  - Unlimited audit history
  - Tier-based access control (RBAC)

#### 3.3 Advanced Analytics & Graphing
- **Source:** `src/code_scalpel/ast_tools/`, `src/code_scalpel/analysis/` (advanced)
- **Enterprise Tools:**
  - `get_graph_neighborhood` tool: Full graph query language, Mermaid export
  - `get_project_map` tool: Enterprise visualization, dependency matrix
  - Program Dependence Graph (PDG) tools (`tests/pdg_tools/`)
  - Call graph with full enrichment (scope, type info, risk scoring)

#### 3.4 Enterprise Security & Compliance
- **Source:** `src/code_scalpel/security/` (full)
- **Enterprise Features:**
  - Full vulnerability database (all CWEs, 50+ vulnerability patterns)
  - Type evaporation detection (TypeScript/Python API boundary validation)
  - Unified sink detection across 5+ languages
  - Advanced taint analysis with data flow graphs
  - Policy-driven compliance verification

#### 3.5 Enterprise Test Suite
- **Source:** `tests/` (Enterprise tier)
- **Files:**
  - `tests/autonomy/` (backburned tests; included for completeness)
  - `tests/tools/get_graph_neighborhood/`
  - `tests/tools/get_project_map/`
  - `tests/tools/rename_symbol/` (Enterprise: full workflow)
  - `tests/pdg_tools/security/`
  - Enterprise security tests
- **Expected Tests:** ~1,200 Enterprise-specific tests

---

## Inventory Categorization

From [INVENTORY_TRIAGE.md](INVENTORY_TRIAGE.md):

### ✅ False Positives (Do Not Extract)
- **Docs/Roadmaps:** `docs/roadmap/`, `docs/analysis/tool_validation/`, test titles
- **Comments:** Inline "Pro-tier", "Enterprise", "@pro", "@enterprise" references
- **Examples:** `examples/`, docs examples
- **Tests:** Test names containing "pro_" or "enterprise_"
- **Action:** Reference only; do not create separate code paths

### 🎯 Real Proprietary Code (Extract by Tier)

#### Community Core
- `src/code_scalpel/mcp/` - Full MCP protocol
- `src/code_scalpel/analysis/` - Framework detection, smart crawl
- `src/code_scalpel/ast_tools/` - Basic call graphs, import resolution
- `src/code_scalpel/licensing/` - License validation engine
- `src/code_scalpel/core.py` - Core initialization
- `src/code_scalpel/project_crawler.py` - Directory scanning
- `src/code_scalpel/surgical_extractor.py` - Token-efficient extraction

#### Pro Enhancements
- `src/code_scalpel/policy_engine/` - Policy rules (Pro: 5 rulesets)
- `src/code_scalpel/surgery/rename_symbol_refactor.py` - Safe refactoring
- `src/code_scalpel/surgery/surgical_patcher.py` - Patching
- `src/code_scalpel/security/analyzers/security_analyzer.py` - Basic scanning
- `src/code_scalpel/tiers/__init__.py` - Tier validation

#### Enterprise Only
- `src/code_scalpel/agents/` - Autonomy (CrewAI, AutoGen)
- `src/code_scalpel/security/analyzers/unified_sink_detector.py` - Advanced scanning
- `src/code_scalpel/policy_engine/` - Advanced workflows (full rules, 20+)
- Advanced AST tools (full graph, PDG)

---

## Extraction Checklist

### Community Package (code-scalpel)
- [ ] Copy MCP infrastructure + 22 core tools
- [ ] Add Community-tier limits to `limits.toml`
- [ ] Copy licensing validation (MIT enforcement)
- [ ] Copy tests (6,685 tests, exclude 5 autonomy)
- [ ] Update `pyproject.toml` (Community dependencies only; no Pro/Enterprise)
- [ ] Update `setup.py` with v4.0.0 and Community description
- [ ] Create `README.md` (Community feature set)
- [ ] Tag: `v4.0.0` on GitHub

### Pro Package (code-scalpel-pro)
- [ ] Add Community as `>=4.0.0` dependency
- [ ] Copy Pro-tier tools (policy, governance, security enhancements)
- [ ] Copy `src/code_scalpel_pro/` modules
- [ ] Copy Pro-tier tests (~800)
- [ ] Update `pyproject.toml` (include Community dependency, Pro-specific libs)
- [ ] Update `setup.py` with v4.0.0 and Pro description
- [ ] Create `README.md` (Pro feature set, governance/security)
- [ ] Add JWT license validation endpoint config
- [ ] Tag: `v4.0.0` on GitHub

### Enterprise Package (code-scalpel-enterprise)
- [ ] Add Community `>=4.0.0` + optional Pro `>=4.0.0` dependency
- [ ] Copy Enterprise-tier tools (autonomy, advanced analytics, governance)
- [ ] Copy `src/code_scalpel_enterprise/` modules
- [ ] Copy Enterprise-tier tests (~1,200, including backburned autonomy tests)
- [ ] Update `pyproject.toml` (include Community + optional Pro, Enterprise-specific libs)
- [ ] Update `setup.py` with v4.0.0 and Enterprise description
- [ ] Create `README.md` (Enterprise feature set, autonomy/governance/analytics)
- [ ] Add JWT license validation endpoint config
- [ ] Tag: `v4.0.0` on GitHub

---

## Testing Strategy

### Phase 2 Validation
1. **Community Package Tests:**
   - Run 6,685 tests: ✅ Expected pass rate 100%
   - Coverage: 44.96% baseline (will improve with focused extraction)
   - MCP protocol compatibility: All 22 tools functional

2. **Pro Package Tests:**
   - Run ~800 Pro-specific tests
   - Verify tier gating (Pro features unavailable in Community)
   - License validation: Pro JWT tokens accepted

3. **Enterprise Package Tests:**
   - Run ~1,200 Enterprise-specific tests
   - Include backburned autonomy tests (CrewAI, AutoGen)
   - Verify autonomy agent orchestration (async, task management)
   - License validation: Enterprise JWT tokens accepted

4. **Integration Test:**
   - Community + Pro: Verify dependency resolution (no conflicts)
   - Community + Enterprise: Verify multi-package coordination
   - Pro + Enterprise: Verify governance workflow with autonomy

### Test Execution
```bash
# Community (monolith baseline)
cd /mnt/k/backup/Develop/code_scalpel_community
pytest tests/ -v --tb=short

# Pro
cd /mnt/k/backup/Develop/code_scalpel_pro
pytest tests/tools/code_policy_check/ tests/tools/rename_symbol/ tests/tools/security_scan/ -v

# Enterprise
cd /mnt/k/backup/Develop/code_scalpel_enterprise
pytest tests/autonomy/ tests/tools/get_graph_neighborhood/ -v
```

---

## Versioning & Artifact Strategy

### Version: v4.0.0 (Breaking Release)
- **Release Date:** 2026-02-01 (planned)
- **Monolith EOL:** 2026-05-01 (90-day grace period)
- **Package Versions:** All packages v4.0.0 (synchronized)

### Artifacts
- **Community:** PyPI `code-scalpel==4.0.0`
- **Pro:** Private index `https://dist.code-scalpel.io/pro/code-scalpel-pro==4.0.0`
- **Enterprise:** Private index `https://dist.code-scalpel.io/enterprise/code-scalpel-enterprise==4.0.0`

### License Keys
- **Community:** MIT (in-package)
- **Pro/Enterprise:** JWT bearer tokens (issued at contract time, required at runtime)

---

## Success Criteria

- ✅ All 22 MCP tools work identically in split packages
- ✅ No functional regressions (baseline test pass rate maintained)
- ✅ Tier-gating enforced (Community tools unavailable in Pro/Enterprise without Community dep)
- ✅ License validation works seamlessly (Pro/Enterprise JWTs accepted)
- ✅ Size reduction confirmed (Community ~250KB vs monolith 788KB = 68% smaller)
- ✅ CI/CD pipelines updated (separate workflows for Community/Pro/Enterprise)
- ✅ Documentation updated (3 separate README.md + migration guide)

---

## Timeline

| Phase | Task | Target Date | Status |
|-------|------|-------------|--------|
| 1 | Pre-flight validation | 2026-01-09 | ✅ Complete |
| 2a | Community extraction | 2026-01-20 | Pending |
| 2b | Pro extraction | 2026-01-25 | Pending |
| 2c | Enterprise extraction | 2026-01-30 | Pending |
| 3 | Integration testing | 2026-02-01 | Pending |
| 4 | GA release | 2026-02-01 | Pending |

---

## Next Steps

1. Begin Community extraction (Step 1 above)
2. Run Community test suite (6,685 tests)
3. Proceed to Pro extraction (Step 2)
4. Proceed to Enterprise extraction (Step 3)
5. Verify inter-package dependencies and MCP protocol
6. Tag all repos with v4.0.0 and release

**Owner:** Code Scalpel Team  
**Contact:** support@code-scalpel.io

