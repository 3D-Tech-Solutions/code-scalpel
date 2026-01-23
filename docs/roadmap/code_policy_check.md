# code_policy_check Tool Roadmap

**Tool Name:** `code_policy_check`  
**Tool Version:** v1.0  
**Code Scalpel Version:** v1.0
**Current Status:** Stable  
**Primary Module:** `src/code_scalpel/policy_engine/code_policy_check/analyzer.py`  
**Tier Availability:** Community, Pro, Enterprise

---

## Overview

The `code_policy_check` tool checks code against style guides, best practices, and compliance standards. Tiered feature set from basic style checks to comprehensive compliance auditing.

---

## Current Capabilities (v1.0)

### Community Tier
- ✅ Basic style guide checking (PEP 8, ESLint)
- ✅ Common code smell detection
- ✅ Simple complexity thresholds
- ✅ Supports Python, JavaScript
- ⚠️ **Limits:** Predefined rules only

### Pro Tier
- ✅ All Community features
- ✅ Custom rule definitions
- ✅ Organization-specific policies
- ✅ Advanced pattern matching
- ✅ Multi-language support
- ✅ Policy templates library

### Enterprise Tier
- ✅ All Pro features
- ✅ Compliance framework mapping (PCI-DSS, HIPAA, SOC2)
- ✅ Automated compliance reporting
- ✅ Policy inheritance and composition
- ✅ Audit trail for policy checks
- ✅ Policy governance workflows

---

## MCP Request/Response Examples

### MCP Request Format

```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "mcp_code-scalpel_code_policy_check",
    "arguments": {
      "code": "def processData(x):\n  y=x+1\n  return y",
      "language": "python",
      "policies": ["pep8", "naming"]
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
    "violations": [
      {
        "rule": "E302",
        "message": "Expected 2 blank lines, found 0",
        "line": 1,
        "column": 1,
        "severity": "warning",
        "category": "style"
      },
      {
        "rule": "E225",
        "message": "Missing whitespace around operator",
        "line": 2,
        "column": 4,
        "severity": "warning",
        "category": "style"
      },
      {
        "rule": "C0103",
        "message": "Function name 'processData' doesn't conform to snake_case naming style",
        "line": 1,
        "column": 5,
        "severity": "convention",
        "category": "naming"
      }
    ],
    "violation_count": 3,
    "passed": false,
    "policies_checked": ["pep8", "naming"]
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
    "violations": [
      {
        "rule": "E302",
        "message": "Expected 2 blank lines, found 0",
        "line": 1,
        "column": 1,
        "severity": "warning",
        "category": "style",
        "fix_available": true,
        "suggested_fix": "Add 2 blank lines before function definition"
      },
      {
        "rule": "E225",
        "message": "Missing whitespace around operator",
        "line": 2,
        "column": 4,
        "severity": "warning",
        "category": "style",
        "fix_available": true,
        "suggested_fix": "y = x + 1"
      },
      {
        "rule": "C0103",
        "message": "Function name 'processData' doesn't conform to snake_case naming style",
        "line": 1,
        "column": 5,
        "severity": "convention",
        "category": "naming",
        "fix_available": true,
        "suggested_fix": "process_data"
      }
    ],
    "violation_count": 3,
    "passed": false,
    "policies_checked": ["pep8", "naming"],
    "custom_rules_matched": [],
    "complexity_violations": [],
    "pattern_matches": [],
    "owasp_mapping": {}
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
    "violations": [
      {
        "rule": "E302",
        "message": "Expected 2 blank lines, found 0",
        "line": 1,
        "column": 1,
        "severity": "warning",
        "category": "style",
        "fix_available": true,
        "suggested_fix": "Add 2 blank lines before function definition",
        "compliance_impact": []
      },
      {
        "rule": "E225",
        "message": "Missing whitespace around operator",
        "line": 2,
        "column": 4,
        "severity": "warning",
        "category": "style",
        "fix_available": true,
        "suggested_fix": "y = x + 1",
        "compliance_impact": []
      },
      {
        "rule": "C0103",
        "message": "Function name 'processData' doesn't conform to snake_case naming style",
        "line": 1,
        "column": 5,
        "severity": "convention",
        "category": "naming",
        "fix_available": true,
        "suggested_fix": "process_data",
        "compliance_impact": ["SOC2-CC7.1"]
      }
    ],
    "violation_count": 3,
    "passed": false,
    "policies_checked": ["pep8", "naming"],
    "custom_rules_matched": [],
    "compliance_summary": {
      "frameworks_checked": ["SOC2"],
      "controls_violated": ["CC7.1"],
      "controls_passed": 47,
      "compliance_score": 0.98
    },
    "audit_trail": {
      "check_id": "chk_abc123",
      "timestamp": "2026-01-01T10:30:00Z",
      "policy_version": "v2.1.0",
      "policy_hash": "sha256:a1b2c3..."
    },
    "inherited_policies": ["org-base", "team-backend"]
  },
  "id": 1
}
```

---

## Roadmap

### Cross-Cutting Research Topics

**Research queries (cross-cutting):**
- How do we guarantee deterministic findings across OS/Node/Python versions for external linters (e.g., normalize/lock ESLint + plugins; normalize pycodestyle output)?
- What is the right intermediate representation for multi-language rules: regex-only, AST-only, or a hybrid IR that can map to Python `ast`, JS/TS parsers, and Java parsers?
- What are measurable false-positive/false-negative budgets per rule class (style, smells, security, compliance), and how do we build a benchmark suite to enforce them in CI?
- How should “suppression” work (inline ignores vs policy allowlists vs baselines) without weakening governance/auditability?
- What policy schema versioning strategy prevents breaking changes while enabling richer rules (dependencies, semantic matching, context windows)?

**Research topics (cross-cutting):**
- Evaluation harness: golden fixtures per language, regression scoring, and release gates
- Confidence + “best-effort” semantics: when to omit results vs return partials
- Determinism guarantees: stable outputs across platforms, tool versions, and parallelism
- Policy governance: ownership, change control, review workflows, and tamper resistance (tie-in with `verify_policy_integrity`)
- Performance envelopes: timeouts, incremental scanning, and predictable scaling on large repos

**Success metrics (cross-cutting):**
- Determinism: stable ordering and consistent findings for the same inputs in the supported environment matrix
- Contract stability: backward-compatible policy schema changes only; compatibility checks in CI
- Quality: tracked FP/FN budgets per rule category with regression alerts
- Governance: auditable policy + execution metadata with defined retention and access boundaries

### v1.1 (Q1 2026): Enhanced Rule Engine

#### Community Tier
- [ ] TypeScript style checking
- [ ] Java style checking
- [ ] Configurable severity levels

**Research topics (Q1 / Community):**
- TypeScript linting architecture: ESLint + `@typescript-eslint` vs TypeScript compiler API checks (tradeoffs: fidelity, speed, determinism)
- Java linting architecture: Checkstyle vs SpotBugs vs Error Prone integration model and output normalization
- Severity mapping: policy-driven severity overrides, default severity per rule, and consistent ranking across languages

**Success metrics (Q1 / Community):**
- Language support: TS/Java checks produce actionable spans/line numbers for the majority of findings
- Severity: severity overrides are deterministic and consistently applied across rule sources

#### Pro Tier
- [ ] Semantic rule matching
- [ ] Context-aware rules
- [ ] Rule dependency management
- [ ] Policy testing framework

**Research topics (Q1 / Pro):**
- Semantic matching: rule targets as AST patterns (e.g., “calls to X with tainted arg”) vs structural patterns (tree/graph query language)
- Context windows: surrounding lines/AST parents for rules like “log PHI” or “SQL concat” to reduce false positives
- Rule dependencies: defining prerequisites and composing rules (e.g., taint sources/sinks feeding higher-level findings)
- Policy testing: fixture format, expected findings schema, and “golden test” authoring UX for policy owners

**Success metrics (Q1 / Pro):**
- Semantic rules: measurable FP reduction vs regex-only baselines on benchmark suite
- Policy tests: policy owners can add a new policy + fixture and get deterministic pass/fail in CI

#### Enterprise Tier
- [ ] Policy simulation mode
- [ ] Impact analysis for policy changes
- [ ] Policy versioning and rollback

**Research topics (Q1 / Enterprise):**
- Simulation mode: dry-run outputs that include a delta report vs prior baseline (without mutating audit trails unless explicitly requested)
- Impact analysis: estimating “new violations introduced” vs “existing violations reclassified” when policies change
- Versioning/rollback: policy provenance, signed versions, and safe rollback mechanics with auditability

**Success metrics (Q1 / Enterprise):**
- Impact analysis: accurate delta summaries with stable categorization and low-noise diffs
- Versioning: rollback is fast, traceable, and does not break policy schema compatibility

### v1.2 (Q2 2026): Compliance Expansion

#### Pro Tier
- [ ] OWASP Top 10 mapping
- [ ] CWE compliance checking
- [ ] Security best practices

**Research topics (Q2 / Pro):**
- OWASP mapping granularity: rule-to-OWASP category vs finding-to-category; handling multi-mapped findings
- CWE mapping: canonical CWE IDs for patterns and how to avoid incorrect/overbroad labeling
- Security best practices: defining “best practice” rules with measurable value and bounded false positives

**Success metrics (Q2 / Pro):**
- Mapping accuracy: high agreement between curated ground truth and tool mappings on benchmark suite
- Signal quality: security rule set meets FP/FN budgets and produces actionable remediation guidance

#### Enterprise Tier
- [ ] GDPR compliance rules
- [ ] CCPA compliance rules
- [ ] Industry-specific regulations
- [ ] Custom compliance frameworks

**Research topics (Q2 / Enterprise):**
- Compliance rule authoring model: reusable controls, inheritance, and evidence requirements per standard
- “Custom compliance frameworks”: schema for user-defined standards, scoring, and certification outputs
- Regulatory drift: how to keep standard mappings updated and versioned without breaking reproducibility

**Success metrics (Q2 / Enterprise):**
- Custom frameworks: users can define a standard + controls and generate a consistent report/certification artifact
- Reproducibility: compliance reports are reproducible for a fixed policy version + code snapshot

### v1.3 (Q3 2026): AI-Enhanced Policy Checking

#### Pro Tier
- [ ] ML-based pattern recognition
- [ ] Anomaly-based policy violations
- [ ] Intelligent false positive reduction

**Research topics (Q3 / Pro):**
- ML scope: where ML is appropriate (ranking/triage) vs where deterministic rules are required (compliance/audit)
- False-positive reduction: human-in-the-loop feedback loops with privacy-safe telemetry
- Anomaly detection: defining baselines per repo/org and preventing “learning bad patterns” as normal

**Success metrics (Q3 / Pro):**
- ML assist: reduces triage time / improves ranking without increasing missed critical findings
- Calibration: confidence scores correlate with true-positive likelihood on held-out evaluation sets

#### Enterprise Tier
- [ ] Custom ML model training
- [ ] Organizational pattern learning
- [ ] Predictive policy violations

**Research topics (Q3 / Enterprise):**
- Model governance: auditability, drift detection, and reproducible training datasets
- Org learning: isolating tenant data; privacy boundaries; opt-in and retention controls
- Predictive findings: how to present predictions with calibrated confidence to avoid over-claiming

**Success metrics (Q3 / Enterprise):**
- Governance: training + inference workflows produce auditable artifacts and reproducible evaluations
- Predictive: precision/recall tracked against post-merge outcomes with calibrated uncertainty

### v1.4 (Q4 2026): Integration & Automation

#### Community Tier
- [ ] GitHub Actions integration
- [ ] Pre-commit hooks
- [ ] CI/CD pipeline support

**Research topics (Q4 / Community):**
- CI ergonomics: fast fail vs full report, caching, and baseline-only modes for incremental adoption
- Developer UX: pre-commit latency budgets and clear actionable output formatting

**Success metrics (Q4 / Community):**
- CI adoption: reference workflows run in predictable time with stable outputs and minimal flakes

#### Pro Tier
- [ ] IDE real-time checking
- [ ] Automated fix suggestions
- [ ] Policy violation dashboard

**Research topics (Q4 / Pro):**
- Real-time checking: incremental scanning and diagnostics streaming without leaking source
- Fix suggestions: safety model, confidence scoring, and opt-in auto-fix vs suggested patch outputs
- Dashboard: aggregation model, deduplication, and trend tracking without inflating noise

**Success metrics (Q4 / Pro):**
- Fixes: suggested fixes are accurate and low-regression on benchmark suite
- Dashboard: actionable trends with low duplication and stable severity ranking

#### Enterprise Tier
- [ ] ServiceNow integration
- [ ] Jira compliance tickets
- [ ] Custom webhook notifications
- [ ] SIEM integration

**Research topics (Q4 / Enterprise):**
- Ticketing integrations: mapping findings to issue schemas, deduplication, and lifecycle management
- SIEM integration: event schemas, rate limiting, redaction, and safe transport guarantees
- Webhooks: secure signing, retries, and idempotency guarantees

**Success metrics (Q4 / Enterprise):**
- Integrations: reliable delivery with idempotency; no duplicate storms; clear operational runbooks

---

## v1.0 Pre-Release Validation

> [20260111_DOCS] Added validation status for v1.0 release

### Validation Summary

| Aspect | Status | Notes |
|--------|--------|-------|
| **Test Coverage** | ✅ 78 tests | All passing (~22s) |
| **Rule Coverage** | ✅ 35/35 | All rules validated |
| **Tier Coverage** | ✅ 3/3 | Community, Pro, Enterprise |
| **Config Alignment** | ✅ Fixed | Pro max_files corrected |
| **Output Metadata** | ✅ Added | Transparency fields |

### Tests by Category
- MCP Integration: 18 tests
- Rule Detection: 24 tests  
- Tier Enforcement: 12 tests
- Compliance: 8 tests
- Configuration: 10 tests
- License Validation: 6 tests

### Pre-Release Fixes Applied

1. **Configuration Mismatch** (`[20260111_BUGFIX]`)
   - Issue: Pro tier `max_files` was `None` in features.py but `1000` in limits.toml
   - Fix: Updated features.py to `max_files: 1000`

2. **Output Metadata** (`[20260111_FEATURE]`)
   - Added `tier_applied` field
   - Added `files_limit_applied` field  
   - Added `rules_limit_applied` field

3. **Metadata Tests** (`[20260111_TEST]`)
   - Added 5 validation tests for metadata fields

### Validation Status: ✅ APPROVED FOR v1.0

---

## Known Issues & Limitations

### Current Limitations
- **Language support:** Limited to Python, JavaScript (v1.0)
- **Custom rules:** Complex rules require regex knowledge (Pro)
- **Performance:** Large codebases may be slow (>10K files)

### Planned Fixes
- v1.1: More language support
- v1.2: GUI rule builder
- v1.3: Performance optimization

---

## Success Metrics

### Performance Targets
- **Check time:** <500ms per file
- **Accuracy:** >95% correct violations
- **False positive rate:** <5%

### Adoption Metrics
- **Usage:** 100K+ policy checks per month by Q4 2026
- **Violations found:** 50K+ policy violations detected
- **Compliance:** 1K+ enterprise compliance reports

---

## Dependencies

### Internal Dependencies
- `policy_engine/policy_engine.py` - Policy engine core
- `policy_engine/code_policy_check/patterns.py` - Pattern matching
- `ast_tools/analyzer.py` - Code analysis

### External Dependencies
- None

---

## Breaking Changes

None planned for v1.x series.

**API Stability Promise:**
- Tool signature stable
- Policy format backward compatible
- Violation format consistent

---

**Last Updated:** January 11, 2026  
**Next Review:** March 31, 2026
