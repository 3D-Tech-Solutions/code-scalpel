# Code Scalpel Documentation Index

> [20260207_DOCS] Added regulated enterprise deployment gameplan reference.
> [20260224_DOCS] Updated to v2.0.0: C/C++/C# language support, social media marketing guide, polyglot test suite.
> [20260327_DOCS] Updated to v2.1.2: Go/PHP language support, Oracle error recovery, 22-tool maturity.
> [20260328_DOCS] Updated to v2.2.0: Claude Code integration bundle, 8 slash commands, system prompts, setup.sh bootstrap.

**Updated:** March 28, 2026
**Version:** 2.2.0

---

## Quick Links

- **[Getting Started](getting_started/getting_started.md)** - Installation and first steps
- **[Claude Code Integration Guide](CLAUDE_CODE_INTEGRATION.md)** - Complete documentation for the v2.2.0 integration bundle (NEW) ⭐
- **[Claude Code Setup (User Guide)](../integration/claude-code/CLAUDE.md)** - Installation, priority rules, workflows
- **[Installing for Claude](INSTALLING_FOR_CLAUDE.md)** - Claude Desktop/VSCode integration
- **[Setup Checklist](SETUP_CHECKLIST.md)** - 5-minute setup guide
- **[Oracle Resilience](oracle/ORACLE_RESILIENCE_QUICKSTART.md)** - Automatic error recovery (NEW in v1.3)

---

## Documentation by Category

### 🚀 Getting Started
- [Getting Started Guide](getting_started/getting_started.md)
- [Installing for Claude](INSTALLING_FOR_CLAUDE.md)
- [Setup Checklist](SETUP_CHECKLIST.md)
- [Beginner Guide](BEGINNER_GUIDE.md)
- [Beginner FAQ](BEGINNER_FAQ.md)

### 🎯 Claude Code Integration (v2.2.0) ⭐
**Complete system for using Code Scalpel in Claude Code with slash commands and system prompts**
- [Complete Integration Guide](../integration/claude-code/CLAUDE.md) — Installation, priority rules, workflows, auto-use triggers
- [Setup Bootstrap Script](../integration/claude-code/setup.sh) — One-liner: `curl -fsSL ... | bash`
- **8 Slash Commands:**
  - `/cs-setup` — Install MCP, verify, show capabilities
  - `/cs-extract` — Get code by name (99.5% context savings)
  - `/cs-analyze` — Understand structure, find hotspots
  - `/cs-security` — Full audit (local → cross-file → dependencies → polyglot)
  - `/cs-tests` — Generate tests from execution paths
  - `/cs-refactor` — Safe workflow (refs → deps → extract → test → simulate → apply)
  - `/cs-map` — Architecture mapping (crawl → call graph → map → critical paths)
  - `/cs-policy` — Compliance check (HIPAA, SOC2, PCI-DSS, custom rules)
- **Developer Guide:** [CLAUDE.md](../CLAUDE.md) in project root — For developers working ON code-scalpel

### 🔧 Oracle Resilience Middleware (v1.3.0)
- [Quick Start](oracle/ORACLE_RESILIENCE_QUICKSTART.md) - Get started with Oracle
- [Integration Guide](oracle/ORACLE_INTEGRATION_GUIDE.md) - Complete integration reference
- [MCP and CLI Tracking Matrix](oracle/ORACLE_MCP_CLI_TRACKING.md) - Live coverage tracker for Oracle usage across public tool boundaries
- [Testing Guide](oracle/ORACLE_TESTING_GUIDE.md) - What Oracle does and how QA should validate it
- [Implementation Details](ORACLE_RESILIENCE_IMPLEMENTATION.md) - Technical deep dive
- [Test Cases](ORACLE_RESILIENCE_TEST_CASES.md) - Test coverage documentation
- [Comprehensive Analysis](oracle/ORACLE_COMPREHENSIVE_ANALYSIS.md) - Full analysis report

### 📖 Reference Documentation
- [Quick Reference](QUICK_REFERENCE.md) - Common operations at a glance
- [Docstring Specifications](reference/DOCSTRING_SPECIFICATIONS.md) - MCP tool documentation
- [Docstring Examples](reference/DOCSTRING_EXAMPLES.md) - Usage examples
- [Audit Report](reference/AUDIT_REPORT.md) - Tool inventory and status
- [Tool Language Integration Matrix](tools/TOOL_LANGUAGE_INTEGRATION_MATRIX.md) - Clean 22-tool by 13-language support matrix

### 🏗️ Architecture
- [Codebase Exploration](architecture/CODEBASE_EXPLORATION_REPORT.md) - System overview
- [Tier Testing Architecture](architecture/TIER_TESTING_ARCHITECTURE.md) - Licensing tiers
- [Deterministic Implementation](DETERMINISTIC_IMPLEMENTATION_SUMMARY.md) - Parsing guarantees
- [Project Awareness Engine](PROJECT_AWARENESS_ENGINE.md) - Intelligent codebase analysis

### 🔒 Security & Compliance
- [App Security Methodology](app_sec_star_methodology.md) - Security analysis approach
- [GitHub Secrets](GITHUB_SECRETS.md) - Secret management
- [Compliance Runtime Guide](compliance/README.md) - Current compliance tier-gating and verification behavior
- **Enterprise Compliance (NEW in v1.3.0):** ⭐
  - **[📦 Complete Documentation Package](COMPLIANCE_DOCUMENTATION_DELIVERABLES.md)** - All deliverables index
  - [For CTOs](guides/ENTERPRISE_COMPLIANCE_FOR_CTOS.md) - Business value & ROI
  - [For Engineers](guides/ENTERPRISE_COMPLIANCE_FOR_ENGINEERS.md) - Technical implementation
  - [Quick Start Examples](guides/COMPLIANCE_QUICK_START_EXAMPLES.md) - Practical examples & code samples ⭐
  - [Capability Matrix](guides/COMPLIANCE_CAPABILITY_MATRIX.md) - Feature comparison table
  - [Verification Report](testing/COMPLIANCE_VERIFICATION_REPORT.md) - 100% test coverage proof ✅
  - **Marketing Materials:**
    - [One-Pager](marketing/COMPLIANCE_ONE_PAGER.md) - Sales & demo material
    - [Comparison vs Alternatives](marketing/COMPLIANCE_COMPARISON.md) - Feature & cost comparison
    - [Social Media & Platform Guide](marketing/SOCIAL_MEDIA.md) - Platform-specific copy (HN, Reddit, LinkedIn, Twitter/X, Dev.to, Product Hunt)
    - [Presentation Library](marketing/presentations/README.md) - Customer, client, investor, and Aegis OS deck blueprints
    - [Presentation Approval Packet](marketing/presentations/APPROVAL_PACKET.md) - Bundled review set for internal and public positioning materials
    - [Buyer Tone Variants](marketing/presentations/BUYER_TONE_VARIANTS.md) - Startup versus enterprise narrative tuning
    - [Technical Specialist Briefing](marketing/presentations/TECHNICAL_SPECIALIST_BRIEFING.md) - Architecture and integration guidance for AST, IR, graph, and symbolic workflows

### 📦 Release & Deployment
- [Release Process](RELEASE_PROCESS.md) - How to release
- [Releasing Guide](RELEASING.md) - Detailed release steps
- [Pre-Release Pipeline](PRE_RELEASE_PIPELINE.md) - CI/CD validation
- [Pre-Release Walkthrough](PRE_RELEASE_WALKTHROUGH.md) - Step-by-step guide
- [Deployment Guides](deployment/DEPLOYMENT_INDEX.md) - Platform and infrastructure deployments
- [Regulated Enterprise Gameplan](deployment/infrastructure/regulated-enterprise-gameplan.md) - Enterprise tier deployment plan
- [Aegis Runtime Questionnaire](deployment/infrastructure/AEGIS_CODE_SCALPEL_RUNTIME_QUESTIONNAIRE.md) - Verified MCP runtime contract for Aegis adapter handoff

### 🧪 Testing
- [Testing Framework](TESTING_FRAMEWORK.md) - Test organization
- [Testing Guide](TESTING.md) - How to run tests
- [Stress Testing](stress_test.md) - Performance testing
- [Compliance Testing Strategy](testing/COMPLIANCE_TESTING_STRATEGY.md) - Two-tier compliance testing approach (NEW)
- [Compliance Verification Report](testing/COMPLIANCE_VERIFICATION_REPORT.md) - Enterprise compliance testing (NEW)

### � Documentation Governance
- [Documentation Strategy](DOC_STRATEGY.md) - Content ownership, update contracts, anti-patterns

### 📁 Subdirectories
- `archive/` - Historical documentation
- `compliance/` - Current compliance runtime behavior and operational guidance
- `getting_started/` - Onboarding materials
- `guides/` - How-to guides
- `marketing/` - Marketing materials and sales collateral
- `oracle/` - Oracle middleware documentation (NEW)
- `reference/` - API and specification docs
- `release_automation/` - Release tooling docs
- `release_notes/` - Version release notes
- `testing/` - Testing documentation and verification reports
- `roadmap/` - Future plans
- `tools/` - Tool-specific documentation
- `../integration/claude-code/` - Claude Code integration bundle (NEW in v2.2.0) — User-facing CLAUDE.md, setup.sh, and 8 slash command skills

---

## Version History

| Version | Date | Highlights |
|---------|------|------------|
| v2.2.0 | 2026-03-28 | Claude Code integration bundle, 8 slash commands, system prompts, crash-safe telemetry |
| v2.1.2 | 2026-03-10 | Oracle patch for error recovery |
| v2.1.0 | 2026-03-06 | Go & PHP language support; 23 tools; expanded language matrix |
| v2.0.0 | 2026-02-24 | C, C++, C# language support; 23 tools; 7,575+ tests |
| v1.5.0 | 2026-02-24 | C and C++ initial parser implementation |
| v1.4.0 | 2026-02-20 | Tier Limit Rebalancing & Website |
| v1.3.0 | 2026-02-01 | Oracle Resilience Middleware |
| v1.2.1 | 2026-01-26 | UVX entry point fix |
| v1.2.0 | 2026-01-26 | Project Awareness Engine |
| v1.1.0 | 2026-01-26 | Kernel Integration |
| v1.0.0 | 2026-01-20 | Initial release |

---

## Document Overview

### 📘 Main Documents

#### 1. **PRE_RELEASE_PIPELINE.md** (50 KB, 1583 lines)
**Full Specification for Development Team**

This is the **primary reference document** for implementing the entire pre-release validation system.

**What It Contains:**
- Executive summary with key decisions
- Purpose, goals, and success criteria
- Current state analysis
- Proposed architecture with detailed diagrams
- Core principles (5 non-negotiable rules)
- Capability model specification
- License architecture (existing + enhancements)
- Test matrix & coverage (300 tests)
- CI/CD pipeline specification (8 stages)
- Enforcement rules & blockers (7 blockers, 4 warnings)
- Design patterns (forbidden vs required)
- 4-phase implementation roadmap
- Success criteria & metrics
- FAQ & troubleshooting
- Appendices with glossary

**Who Should Read:** Development Team Leads, Architecture Review, Implementation Team

**Read Time:** 20-30 minutes (or reference as needed)

**Key Sections:**
- [Core Principles](#core-principles) - Non-negotiable rules
- [Capability Model](#capability-model) - How tier limits work
- [Test Matrix](#test-matrix--coverage) - All test scenarios
- [CI/CD Pipeline](#cicd-pipeline-specification) - 8-stage workflow
- [Design Patterns](#design-patterns--best-practices) - What to do/not do
- [Implementation Roadmap](#implementation-roadmap) - 4-week plan

---

#### 2. **QUICK_REFERENCE.md** (9 KB, 340 lines)
**Quick Start Guide for All Teams**

A **condensed, scannable reference** for developers, DevOps, QA, and product teams.

**What It Contains:**
- TL;DR (60 seconds)
- Key changes overview
- New files/directories
- For tool developers (new pattern)
- For DevOps (secrets setup)
- For QA (test coverage)
- For product (pricing enforcement)
- Adding new tier-gated features (step-by-step)
- Capability snapshot approval workflow
- Troubleshooting section
- Key files to know
- One-minute recap table

**Who Should Read:** All team members (especially non-architects)

**Read Time:** 2-3 minutes

**Best For:** Onboarding new team members, quick lookups

---

### 📋 Supporting Documents

#### 3. **CODEBASE_EXPLORATION_REPORT.md** (Existing)
**Deep Dive: Current Licensing & Tier System**

Understanding what already exists before building on it.

**What It Contains:**
- License/tier implementation (JWT, offline validation)
- Tool registration (21 MCP tools, tier mapping)
- CLI architecture
- Test infrastructure
- License storage/injection patterns

**Read When:** Need to understand existing systems (Phase 1)

---

## Quick Navigation

### For Architects & Decision-Makers

**Start Here:**
1. Read: PRE_RELEASE_PIPELINE.md → [Executive Summary](#executive-summary)
2. Review: [Key Decisions](#what-weve-delivered)
3. Approve: [Sign-Off & Approval](#sign-off--approval) section

**Deliverables to Evaluate:**
- Test matrix scope: 300+ tests across 3 tiers × 3 transports
- Capability model: auto-generated golden files + manual approval
- CI pipeline: 8-stage workflow with blocker enforcement
- Timeline: 4 weeks (Jan 27 – Feb 21)

**Decision Gates:**
- ✅ Full coverage test matrix approved
- ✅ Hybrid capability snapshots approved  
- ✅ GitHub secrets ready
- ✅ Timeline acceptable

---

### For Implementation Team (Phase 1-4 Leaders)

**Phase 1 Lead:** Capability Model & Resolver
- Read: PRE_RELEASE_PIPELINE.md → [Capability Model](#capability-model)
- Read: PRE_RELEASE_PIPELINE.md → [Implementation Roadmap](#implementation-roadmap) → Phase 1
- Deliverables: Resolver function, golden files, MCP method

**Phase 2 Lead:** Test Infrastructure
- Read: PRE_RELEASE_PIPELINE.md → [Test Architecture](#test-architecture)
- Read: QUICK_REFERENCE.md → [For QA](#for-qa-new-test-coverage)
- Deliverables: Adapters, matrix tests, 150+ test cases

**Phase 3 Lead:** CI/CD Pipeline
- Read: PRE_RELEASE_PIPELINE.md → [CI/CD Pipeline](#cicd-pipeline-specification)
- Reference: GitHub Actions YAML template in document
- Deliverables: 8-stage pipeline, blockers functional

**Phase 4 Lead:** Documentation & Training
- Read: PRE_RELEASE_PIPELINE.md → [Design Patterns](#design-patterns--best-practices)
- Reference: Quick Reference guide
- Deliverables: Guides, examples, team training

---

### For Tool Developers

**Essential Reading:**
1. QUICK_REFERENCE.md → [For Tool Developers](#for-tool-developers-new-pattern-required)
2. PRE_RELEASE_PIPELINE.md → [Design Patterns](#design-patterns--best-practices)
3. PRE_RELEASE_PIPELINE.md → [Adding New Tier-Gated Features](#adding-a-new-tier-gated-feature)

**What You Need to Know:**
- ❌ Don't: Hardcode tier limits in tool code
- ✅ Do: Read limits from `get_tool_capabilities()`
- ✅ Do: Use `limits.toml` as single source of truth
- ✅ Do: Write tests for each tier
- ⚠️ Remember: All 23 tools always registered, schema never changes

---

### For DevOps Engineers

**Essential Reading:**
1. QUICK_REFERENCE.md → [For DevOps](#for-devops-new-secrets-required)
2. PRE_RELEASE_PIPELINE.md → [License Architecture](#license-architecture-existing-enhanced)
3. PRE_RELEASE_PIPELINE.md → [CI/CD Pipeline Specification](#cicd-pipeline-specification)

**What You Need to Do:**
- [ ] Configure GitHub secrets: `CODESCALPEL_LICENSE_PRO` and `CODESCALPEL_LICENSE_ENTERPRISE`
- [ ] Deploy 8-stage GitHub Actions workflow
- [ ] Set calendar reminder: 30 days before license expiry
- [ ] Implement secret rotation procedure

---

### For QA Engineers

**Essential Reading:**
1. QUICK_REFERENCE.md → [For QA](#for-qa-new-test-coverage)
2. PRE_RELEASE_PIPELINE.md → [Test Matrix & Coverage](#test-matrix--coverage)
3. PRE_RELEASE_PIPELINE.md → [Enforcement Rules](#enforcement-rules--blockers)

**What You'll Test:**
- Tool availability (23 tools × 3 tiers = 69 tests)
- Tier limits (enforcement, not just documentation)
- License validation (secrets injection, expiry)
- Capability snapshots (regression detection)
- All 3 transports (stdio, HTTP, Docker)

**Total Coverage:** ~300 tests, 15-minute runtime

---

### For Product Managers

**Essential Reading:**
1. QUICK_REFERENCE.md → [For Product](#for-product-what-changes)
2. PRE_RELEASE_PIPELINE.md → [Core Principles](#core-principles)
3. PRE_RELEASE_PIPELINE.md → [Capability Model](#capability-model)

**What Changes:**
- Pricing is now **executable code** (tested in CI)
- Capabilities are **discoverable** (agents can query)
- Changes are **auditable** (golden files show diffs)
- Releases are **validated** (no pricing escapes)

**Tier Change Process:**
1. Update limits in `limits.toml`
2. PR generates new capability snapshot
3. CI shows diff for review
4. Approve with "regenerate-capabilities" label
5. Golden files auto-update on merge
6. Release with confidence

---

## Key Concepts Explained

### Stable Tool Surface
**What It Means:** All 23 tools always present, never hidden

- ✅ 23 tools in tool list (always)
- ✅ Tool schemas immutable
- ❌ No per-tier tool hiding
- ❌ No per-tier schema changes

**Why?** Prevents LLM agents from hallucinating unavailable tools

---

### Capability Envelope
**What It Means:** Runtime vector describing what's available

```json
{
  "tier": "pro",
  "tools": {
    "analyze_code": {
      "available": true,
      "max_files": 5000,
      "max_depth": 15
    },
    "unified_sink_detect": {
      "available": false,
      "requires_tier": "enterprise"
    }
  }
}
```

**Queryable Via:**
- MPC method: `capabilities/get`
- CLI: `codescalpel capabilities --json`
- Programmatically: `get_tool_capabilities(tool_id)`

---

### Golden Capability Files
**What They Are:** Committed reference files for regression testing

- `capabilities/community.json` - All capabilities at COMMUNITY tier
- `capabilities/pro.json` - All capabilities at PRO tier
- `capabilities/enterprise.json` - All capabilities at ENTERPRISE tier

**What Happens on Change:**
1. Code changes → CI generates new capability
2. CI compares against golden file
3. If different → CI fails with diff
4. Developer reviews diff
5. If intentional → Approve PR with "regenerate-capabilities" label
6. Golden file auto-regenerates on merge

---

### Blocker Violations
**What They Are:** Tests that MUST pass for release

| Blocker | Why | Example |
|---------|-----|---------|
| Tool count ≠ 22 | Schema stability | Expected 22, got 21 |
| Schema changed | Client contract | Input type changed |
| Limits not enforced | Pricing integrity | PRO can access FREE limit |
| Capability mismatch | Pricing audit | max_files changed without approval |
| License not injected | Tier detection | Secret empty |

**CI Behavior:** Automatic PR block (no manual override possible)

---

## File Locations

```
Code Scalpel Repository Root
│
├── docs/
│   ├── PRE_RELEASE_PIPELINE.md         ← Primary specification
│   ├── QUICK_REFERENCE.md              ← Quick start guide
│   ├── CODEBASE_EXPLORATION_REPORT.md  ← Existing systems
│   └── CI_ENHANCED_ARCHITECTURE.md     ← Early draft (reference)
│
├── src/code_scalpel/
│   ├── capabilities/
│   │   ├── resolver.py                 ← NEW: Capability lookup
│   │   └── limits.toml                 ← Central tier limits
│   │
│   └── mcp/
│       └── protocol.py                 ← NEW: get_capabilities() method
│
├── capabilities/
│   ├── community.json                       ← NEW: Golden file
│   ├── pro.json                        ← NEW: Golden file
│   ├── enterprise.json                 ← NEW: Golden file
│   └── schema.json                     ← NEW: JSON schema
│
├── tests/
│   ├── transports/
│   │   ├── adapter.py                  ← NEW: Unified interface
│   │   ├── stdio_adapter.py            ← NEW: Subprocess adapter
│   │   ├── http_adapter.py             ← NEW: HTTP adapter
│   │   └── docker_adapter.py           ← NEW: Container adapter
│   │
│   ├── tier_enforcement/
│   │   ├── test_tool_availability.py   ← NEW: Tool matrix tests
│   │   ├── test_tool_limits.py         ← NEW: Limit tests
│   │   └── test_feature_gating.py      ← NEW: Feature tests
│   │
│   └── capabilities/
│       ├── test_capability_snapshot.py ← NEW: Regression tests
│       └── test_capability_schema.py   ← NEW: Schema validation
│
└── .github/workflows/
    └── ci-tier-validation.yml          ← NEW: 8-stage pipeline
```

---

## Timeline at a Glance

```
Week 1 (Jan 27-31): Foundation
├── Capability resolver ✓
├── Golden files ✓
├── MCP method ✓
└── GitHub secrets ✓

Week 2 (Feb 3-7): Test Infrastructure
├── Transport adapters
├── Tool tests (23 tools × 3 tiers)
├── Limit tests
└── Feature tests (24 features × 3 tiers)

Week 3 (Feb 10-14): CI Pipeline
├── 8-stage workflow
├── Blocker enforcement
└── Real PR testing

Week 4 (Feb 17-21): Documentation
├── Development guide
├── Examples
└── Team training

Week 5+: Production Use
├── Full CI/CD active
├── All PRs validated
└── Continuous improvement
```

---

## Success Metrics

| Metric | Target | How Measured |
|--------|--------|--------------|
| **Tool Stability** | 0 breaking changes | JSON schema diff |
| **Tier Limits** | 100% enforced | All 66 limit tests pass |
| **Capability Accuracy** | 100% match | Golden file comparison |
| **License Validation** | 100% working | Secret injection tests |
| **CI Runtime** | <15 minutes | GitHub Actions timer |
| **Coverage** | ≥95% tools/tier | Pytest coverage report |
| **False Positives** | <2% | Alert ratio over time |
| **Release Confidence** | 100% pass | Release test results |

---

## Common Questions

**Q: Do I need to read the entire 50KB document?**
A: No. Start with QUICK_REFERENCE.md (2 min), then read relevant sections in PRE_RELEASE_PIPELINE.md as needed.

**Q: When do I need this?**
A: Immediately if you're on implementation team. Soon if you're a tool developer. Before release for everyone else.

**Q: What if I don't understand something?**
A: Check the FAQ section in PRE_RELEASE_PIPELINE.md. Ask your team lead.

**Q: Can we start before all 4 phases?**
A: No. Phase 1 foundation is required before phases 2-4.

**Q: What if the timeline slips?**
A: Document will be updated. Current plan: 4 weeks.

---

## Next Actions

### For Architects (Today)
- [ ] Review both documents
- [ ] Check against template provided
- [ ] Approve architecture
- [ ] Assign implementation leads

### For Implementation Team (This Week)
- [ ] Read PRE_RELEASE_PIPELINE.md
- [ ] Schedule Phase 1 kickoff
- [ ] Plan Phase 1 deliverables

### For DevOps (This Week)
- [ ] Verify GitHub secrets configured
- [ ] Review CI/CD pipeline spec
- [ ] Plan GitHub Actions deployment

### For QA (This Week)
- [ ] Review test matrix (300 tests)
- [ ] Understand blocker rules
- [ ] Prepare test environment

### For All Teams (Week 2)
- [ ] Read QUICK_REFERENCE.md
- [ ] Understand new patterns
- [ ] Get ready for Phase 1 completion

---

## Document Maintenance

**Version History:**
| Version | Date | Changes |
|---------|------|---------|
| 1.0 | Jan 27, 2026 | Initial specification |

**Last Updated:** January 27, 2026  
**Next Review:** Upon Phase 1 completion (Week 1)

---

## Questions or Issues?

**Report bugs/feedback:** GitHub Issues with label `[docs]`  
**Architecture questions:** Contact Development Team Lead  
**Implementation help:** Contact Phase Lead  

---

**Status: ✅ Ready for Implementation**

These documents provide the complete specification for a commercial-grade, pre-release validation system ensuring Code Scalpel's tier enforcement is correct, testable, and auditable.

Every release will be validated automatically against this specification.

---

**Created by:** OpenCode Agent  
**Date:** January 27, 2026  
**Version:** 1.0
