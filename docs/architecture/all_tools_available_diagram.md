# All-Tools-Available Architecture Diagram

[20251225_DOCS] Visual representation of the parameter-level feature gating architecture

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         MCP CLIENT (Claude, Copilot)                │
└─────────────────────────────────────┬───────────────────────────────┘
                                      │
                                      │ MCP Request
                                      │
┌─────────────────────────────────────▼───────────────────────────────┐
│                          MCP Server Entry Point                      │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ Tool Handler (e.g., security_scan)                           │  │
│  │                                                               │  │
│  │  1. get_current_tier() → "community"                         │  │
│  │  2. get_tool_capabilities("security_scan", "community")      │  │
│  │  3. Perform basic operation (all tiers)                      │  │
│  │  4. Apply tier-based limits                                  │  │
│  │  5. Check capabilities for advanced features                 │  │
│  │  6. Add upgrade hints if limited/missing features            │  │
│  │  7. Return tier-appropriate result                           │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                      │
└──────────────────────────────────────┬───────────────────────────────┘
                                       │
                                       │
┌──────────────────────────────────────▼───────────────────────────────┐
│                        Licensing System                              │
│                                                                      │
│  ┌────────────────┐    ┌────────────────┐    ┌──────────────────┐  │
│  │ tier_detector  │◄───│ license_manager│◄───│ validator        │  │
│  │ .detect_tier() │    │ .get_tier()    │    │ .validate_key()  │  │
│  └────────────────┘    └────────────────┘    └──────────────────┘  │
│          │                                                           │
│          │                                                           │
│          ▼                                                           │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │                    features.py                                 │ │
│  │                                                                │ │
│  │  TOOL_CAPABILITIES = {                                        │ │
│  │    "security_scan": {                                         │ │
│  │      "community": {                                           │ │
│  │        "limits": {"max_findings": 10},                        │ │
│  │        "capabilities": {"basic_vulnerabilities"}              │ │
│  │      },                                                        │ │
│  │      "pro": {                                                  │ │
│  │        "limits": {"max_findings": None},                      │ │
│  │        "capabilities": {"advanced_taint_flow", ...}           │ │
│  │      },                                                        │ │
│  │      "enterprise": { ... }                                    │ │
│  │    }                                                           │ │
│  │  }                                                             │ │
│  │                                                                │ │
│  │  get_tool_capabilities(tool_id, tier)                         │ │
│  │  has_capability(tool_id, capability, tier)                    │ │
│  │  get_upgrade_hint(tool_id, capability, tier)                  │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

## Request Flow Example: security_scan

```
┌──────────────┐
│  User calls  │
│security_scan │
└──────┬───────┘
       │
       ▼
┌──────────────────────────────────────┐
│ 1. Get Tier                           │
│    tier = get_current_tier()          │
│    → "community"                      │
└──────┬───────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────┐
│ 2. Get Capabilities                   │
│    caps = get_tool_capabilities(      │
│      "security_scan", "community"     │
│    )                                  │
│    → {"limits": {"max_findings": 10}} │
└──────┬───────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────┐
│ 3. Run Scan (ALL TIERS)               │
│    vulnerabilities = scan(code)       │
│    → [25 vulnerabilities found]       │
└──────┬───────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────┐
│ 4. Apply Limits                       │
│    max = caps["limits"]["max_findings"]│
│    if len(vulns) > max:               │
│      vulns = vulns[:max]              │
│      truncated = True                 │
└──────┬───────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────┐
│ 5. Check Advanced Features            │
│    if has_capability(                 │
│      "advanced_taint_flow", tier      │
│    ): # False for community           │
│      # Skip advanced analysis         │
└──────┬───────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────┐
│ 6. Add Upgrade Hints                  │
│    if truncated:                      │
│      hints = [                        │
│        "Showing 10/25 vulnerabilities"│
│        get_upgrade_hint(...)          │
│      ]                                │
└──────┬───────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────┐
│ 7. Return Result                      │
│    {                                  │
│      "tier": "community",             │
│      "vulnerabilities": [10 vulns],   │
│      "truncated": true,               │
│      "upgrade_hints": [...]           │
│    }                                  │
└──────────────────────────────────────┘
```

## Capability Lookup Flow

```
get_tool_capabilities("security_scan", "community")
    │
    ├─ Check TOOL_CAPABILITIES dict
    │
    ├─ TOOL_CAPABILITIES["security_scan"]
    │   │
    │   ├─ ["community"]
    │   │   │
    │   │   ├─ "enabled": True
    │   │   ├─ "capabilities": {"basic_vulnerabilities", "single_file_taint"}
    │   │   ├─ "limits": {"max_findings": 10, "vulnerability_types": [...]}
    │   │   └─ "description": "Basic security scanning"
    │   │
    │   ├─ ["pro"]
    │   │   │
    │   │   ├─ "enabled": True
    │   │   ├─ "capabilities": {all community + "advanced_taint_flow", ...}
    │   │   ├─ "limits": {"max_findings": None, "vulnerability_types": "all"}
    │   │   └─ "description": "Advanced security analysis"
    │   │
    │   └─ ["enterprise"]
    │       │
    │       ├─ "enabled": True
    │       ├─ "capabilities": {all pro + "compliance_reporting", ...}
    │       ├─ "limits": {"max_findings": None, "vulnerability_types": "all"}
    │       └─ "description": "Enterprise security with compliance"
    │
    └─ Return capabilities dict for community tier
```

## Registry Architecture (Before vs After)

### BEFORE (v1.0.0) - Tool-Level Hiding

```
tool_registry.py:
┌────────────────────────────────────┐
│ DEFAULT_TOOLS = {                  │
│   "analyze_code": tier="community" │ ✅ Available
│   "extract_code": tier="community" │ ✅ Available
│   "security_scan": tier="pro"      │ ❌ Hidden from community
│   "symbolic_execute": tier="pro"   │ ❌ Hidden from community
│   ...                              │
│ }                                  │
└────────────────────────────────────┘

Result: Only 10/20 tools available to COMMUNITY
```

### AFTER (v1.0.0) - Parameter-Level Gating

```
tool_registry.py:
┌────────────────────────────────────┐
│ DEFAULT_TOOLS = {                  │
│   "analyze_code": tier="community" │ ✅ Available
│   "extract_code": tier="community" │ ✅ Available
│   "security_scan": tier="community"│ ✅ Available (features gated)
│   "symbolic_execute": tier="community"│ ✅ Available (features gated)
│   ...                              │
│ }                                  │
└────────────────────────────────────┘

features.py:
┌─────────────────────────────────────────────┐
│ TOOL_CAPABILITIES = {                       │
│   "security_scan": {                        │
│     "community": {limits, capabilities},    │
│     "pro": {more limits, more capabilities},│
│     "enterprise": {unlimited, all features} │
│   }                                         │
│ }                                           │
└─────────────────────────────────────────────┘

Result: All 20/20 tools available, capabilities differ by tier
```

## Tier Comparison Flowchart

```
                    ┌──────────────────┐
                    │  User executes   │
                    │  security_scan   │
                    └────────┬─────────┘
                             │
                ┌────────────┴────────────┐
                │                         │
        ┌───────▼───────┐         ┌──────▼──────┐
        │ COMMUNITY     │         │ PRO/        │
        │ TIER          │         │ ENTERPRISE  │
        └───────┬───────┘         └──────┬──────┘
                │                         │
        ┌───────▼──────────┐     ┌───────▼──────────┐
        │ Get capabilities │     │ Get capabilities │
        │ max_findings: 10 │     │ max_findings: ∞  │
        │ basic_vuln_types │     │ all_vuln_types   │
        └───────┬──────────┘     └───────┬──────────┘
                │                         │
        ┌───────▼──────────┐     ┌───────▼──────────┐
        │ Run scan         │     │ Run full scan    │
        │ → 25 vulns found │     │ → 25 vulns found │
        │ (basic patterns) │     │ (all patterns)   │
        └───────┬──────────┘     └───────┬──────────┘
                │                         │
        ┌───────▼──────────┐     ┌───────▼──────────┐
        │ Truncate to 10   │     │ Return all 25    │
        │ truncated: true  │     │ + taint analysis │
        └───────┬──────────┘     └───────┬──────────┘
                │                         │
        ┌───────▼──────────┐     ┌───────▼──────────┐
        │ Return {         │     │ Return {         │
        │   vulns: [10],   │     │   vulns: [25],   │
        │   truncated: true│     │   taint_flows,   │
        │   tier: community│     │   remediation,   │
        │ }                │     │   owasp_cats     │
        │                  │     │ }                │
        └──────────────────┘     └──────────────────┘
        
        Note: No upgrade hints in response
        (users consult documentation)
```

## Tier Information in Responses

```
Every tool response includes tier information:

{
  "tier": "community",           // Current active tier
  "truncated": true,             // If results were limited by scope
  "results": [...],              // Actual data (scope-limited)
  "tier_limited": [              // Features not available at this tier
    "advanced_taint_flow",
    "remediation_suggestions"
  ]
}

Users consult documentation to understand:
- What their current tier provides
- What additional features are available in Pro/Enterprise
- Upgrade options and pricing

No marketing messages in tool responses—keeps context clean.
```

## Tool Categories by Tier Progression

```
┌─────────────────────────────────────────────────────────────┐
│                    ALL 21 TOOLS AVAILABLE AT ALL TIERS      │
├─────────────────────────────────────────────────────────────┤
│  Limits are on SCOPE (how much) and FEATURES (what kind)   │
│  NOT on technical constraints like timeouts or connections  │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────┬───────────────────────────┐
│  TOOLS WITH SCOPE LIMITS        │  TOOLS WITH FEATURE GATES │
│  (Result count/depth/breadth)   │  (Analysis capabilities)  │
├─────────────────────────────────┼───────────────────────────┤
│ • security_scan                 │ • security_scan           │
│   Findings: 10 → ∞ → ∞          │   +taint, +remediation    │
│                                 │                           │
│ • symbolic_execute              │ • crawl_project           │
│   Paths: 10 → 100 → ∞           │   +framework detect       │
│   Depth: 5 → 10 → ∞             │   +entry points           │
│                                 │                           │
│ • crawl_project                 │ • get_call_graph          │
│   Files: 100 → 1000 → ∞         │   +polymorphism           │
│                                 │   +runtime trace          │
│ • get_call_graph                │                           │
│   Depth: 3 → 10 → ∞             │ • verify_policy_integrity │
│   Nodes: 50 → 500 → ∞           │   +signature validation   │
│                                 │   +compliance reports     │
│ • get_graph_neighborhood        │                           │
│   Hops: 2 → 5 → ∞               │ • scan_dependencies       │
│   Nodes: 100 → 1000 → ∞         │   +reachability           │
│                                 │   +license compliance     │
│ • get_symbol_references         │                           │
│   Files: 10 → 200 → ∞           │ • type_evaporation_scan   │
│                                 │   +implicit any tracking  │
│ • cross_file_security_scan      │   +schema generation      │
│   Depth: 5 → 10 → ∞             │                           │
│   Modules: 100 → 500 → ∞        │ • get_file_context        │
│                                 │   +semantic summary       │
│ • scan_dependencies             │   +PII redaction          │
│   Deps: 50 → ∞ → ∞              │                           │
│                                 │                           │
│ • get_cross_file_dependencies   │ • code_policy_check       │
│   Depth: 1 → 3 → ∞              │   +best practices         │
│                                 │   +compliance audits      │
│ • generate_unit_tests           │                           │
│   Tests: 5 → 20 → ∞             │                           │
└─────────────────────────────────┴───────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  TOOLS WITH NO TIER DIFFERENCES (Fully functional all tiers)│
├─────────────────────────────────────────────────────────────┤
│ • analyze_code          • update_symbol                     │
│ • extract_code          • simulate_refactor                 │
│ • unified_sink_detect   • validate_paths                    │
│ • get_project_map                                           │
└─────────────────────────────────────────────────────────────┘
```

## Capability Progression Example: security_scan

```
┌────────────────────────────────────────────────────────────────┐
│                        COMMUNITY TIER                          │
├────────────────────────────────────────────────────────────────┤
│ Scope Limits:                                                  │
│   • max_findings: 10 (result truncation)                       │
│   • vulnerability_types: 10 common patterns                    │
│                                                                │
│ Features Available:                                            │
│   ✅ basic_vulnerabilities (OWASP Top 10 patterns)             │
│   ✅ single_file_taint (within one file)                       │
│   ✅ cwe_mapping (security categorization)                     │
│                                                                │
│ Features NOT Available:                                        │
│   ❌ advanced_taint_flow (multi-path analysis)                 │
│   ❌ remediation_suggestions (how to fix)                      │
│   ❌ owasp_categorization (severity scoring)                   │
│                                                                │
│ Example Result:                                                │
│   {                                                            │
│     "tier": "community",                                       │
│     "vulnerabilities": [10 of 25],                             │
│     "truncated": true                                          │
│   }                                                            │
│                                                                │
│ Note: No upgrade hints in response—users consult docs          │
└────────────────────────────────────────────────────────────────┘
                             ▼ UPGRADE
┌────────────────────────────────────────────────────────────────┐
│                           PRO TIER                             │
├────────────────────────────────────────────────────────────────┤
│ Scope Limits:                                                  │
│   • max_findings: unlimited                                    │
│   • vulnerability_types: all patterns + custom                 │
│                                                                │
│ Features Available:                                            │
│   ✅ All COMMUNITY features +                                  │
│   ✅ advanced_taint_flow (multi-path, cross-function)          │
│   ✅ remediation_suggestions (actionable fixes)                │
│   ✅ owasp_categorization (risk scoring)                       │
│   ✅ context_aware_analysis (sanitizer recognition)            │
│                                                                │
│ Example Result:                                                │
│   {                                                            │
│     "tier": "pro",                                             │
│     "vulnerabilities": [all 25],                               │
│     "taint_flows": [...],                                      │
│     "remediation": [...],                                      │
│     "owasp_categories": {...}                                  │
│   }                                                            │
└────────────────────────────────────────────────────────────────┘
                             ▼ UPGRADE
┌────────────────────────────────────────────────────────────────┐
│                       ENTERPRISE TIER                          │
├────────────────────────────────────────────────────────────────┤
│ Scope Limits:                                                  │
│   • No limits (unlimited scale)                                │
│                                                                │
│ Features Available:                                            │
│   ✅ All PRO features +                                        │
│   ✅ cross_file_taint (global data flow)                       │
│   ✅ compliance_reporting (HIPAA, SOC2, GDPR)                  │
│   ✅ custom_security_rules (org-specific policies)             │
│   ✅ automated_remediation (auto-fix generation)               │
│   ✅ audit_trail (change tracking)                             │
│   ✅ multi_repo_analysis (organization-wide)                   │
│                                                                │
│ Example Result:                                                │
│   {                                                            │
│     "tier": "enterprise",                                      │
│     "vulnerabilities": [all + custom rules],                   │
│     "taint_flows": [...],                                      │
│     "remediation": [...],                                      │
│     "compliance_report": {                                     │
│       "soc2": "passed",                                        │
│       "hipaa": "passed",                                       │
│       "gdpr": "compliant"                                      │
│     },                                                         │
│     "automated_fixes": [...],                                  │
│     "audit_trail": [...]                                       │
│   }                                                            │
└────────────────────────────────────────────────────────────────┘
```

## See Also

- [all_tools_available_summary.md](all_tools_available_summary.md) - Complete summary
- [features.py](../../src/code_scalpel/licensing/features.py) - Implementation
- [tier_capabilities_matrix.md](../reference/tier_capabilities_matrix.md) - Reference
