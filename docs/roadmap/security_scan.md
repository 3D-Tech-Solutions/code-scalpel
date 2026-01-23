# security_scan Tool Roadmap

**Tool Name:** `security_scan`  
**Tool Version:** v1.0  
**Code Scalpel Version:** v3.3.0  
**Current Status:** Stable  
**Primary Module:** `src/code_scalpel/mcp/server.py` (line 3712)  
**Tier Availability:** All tiers (Community, Pro, Enterprise)

---

## Overview

The `security_scan` tool detects security vulnerabilities using taint-based analysis. Identifies SQL injection, XSS, command injection, path traversal, and more without executing code.

**Why AI Agents Need This:**
- **Secure code generation:** Validate AI-generated code for vulnerabilities before deployment
- **Responsible AI:** Agents can explain why code is insecure and suggest fixes
- **Continuous security:** Integrate into AI-assisted development workflows
- **Learning resource:** CWE mappings help agents understand vulnerability classes
- **Compliance ready:** OWASP categorization for audit trails

---

## Polyglot Architecture Definition

**Current Status:** Partially polyglot. Python has full taint + sanitizer + remediation; JavaScript/TypeScript/Java rely on sink detection only (no taint flows), with optional TypeScript type-evaporation check.

### Language Support Matrix

| Language | Community | Pro | Enterprise | Taint Flows | Sanitizers | Remediation | Type Safety | Status |
|----------|-----------|-----|------------|-------------|------------|-------------|-------------|--------|
| Python | ✅ Full | ✅ Full | ✅ Full | ✅ | ✅ | ✅ | N/A | ✅ Stable |
| JavaScript | ✅ Sink detection | ✅ Sink detection | ✅ Sink detection | ❌ | ❌ | ❌ | ❌ | ⚠️ Limited |
| TypeScript | ✅ Sink detection | ✅ Sink + type evaporation | ✅ Sink + type evaporation | ❌ | ❌ | ❌ | ⚠️ Partial (type evap only) | ⚠️ Limited |
| Java | ✅ Sink detection | ✅ Sink detection | ✅ Sink detection | ❌ | ❌ | ❌ | ❌ | ⚠️ Limited |
| Go | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | 🔴 Missing |
| Rust | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | 🔴 Missing |
| PHP | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | 🔴 Missing |
| Ruby | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | 🔴 Missing |
| C/C++ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | 🔴 Missing |

### Capability Gaps (vs. true polyglot taint)
- Non-Python languages only run **sink detection**; there is **no taint flow** or sanitizer awareness.
- Confidence scoring and remediation are sink-only for JS/TS/Java; sanitizer detection is Python-only.
- TypeScript type-evaporation detector is bolt-on and not integrated into the main vulnerability list.
- Language detection is file-extension-based only (no content-based fallback).
- No Go/Rust/PHP/Ruby/C/C++ support despite roadmap expansion goals.

### Requirements for True Polyglot Shape
1. Add language-specific taint engines for JS/TS/Java (sources, sinks, sanitizers, frameworks).
2. Unify sanitizer detection and confidence scoring across languages; expose consistent fields.
3. Integrate TypeScript type-evaporation findings into the main vulnerability list (shared CWE, severity, remediation).
4. Implement content-based language detection fallback to avoid misclassification.
5. Extend sink + taint coverage to Go/Rust/PHP/Ruby/C/C++ (sink coverage first, taint next).
6. Build cross-language test suites with ≥90% precision/recall per language and FP/FN budgets.

### Polyglot Completion Timeline
- **v1.1 (Q1 2026):** JS/TS/Java taint MVP (sources, sinks, sanitizers) + content-based language detection
- **v1.2 (Q2 2026):** Integrate TS type-evaporation into main findings; harden JS/TS/Java sanitizer + remediation
- **v1.3 (Q3 2026):** Add Go/Rust/PHP sink detection + taint MVP; add Ruby/C/C++ sink coverage
- **v1.4 (Q4 2026):** Polyglot validation: precision/recall, FP/FN budgets, confidence calibration across languages


## Research Queries for Future Development

### Foundational Research
| Topic | Query | Purpose |
|-------|-------|---------|
| Taint Analysis | "taint analysis precision recall tradeoffs static analysis" | Improve accuracy |
| Sanitizer Detection | "automatic sanitizer identification security static analysis" | Reduce false positives |
| Data Flow | "interprocedural data flow analysis scalability" | Cross-function tracking |
| CWE Mapping | "automated CWE classification machine learning" | Better categorization |

### Language-Specific Research
| Topic | Query | Purpose |
|-------|-------|---------|
| Python Security | "python security static analysis eval exec pickle" | Better Python patterns |
| JavaScript | "javascript prototype pollution detection static" | DOM/Node.js security |
| Java | "java security analysis deserialization OWASP" | Enterprise Java support |
| TypeScript | "typescript security patterns type-safe code" | TS-specific checks |

### Advanced Techniques
| Topic | Query | Purpose |
|-------|-------|---------|
| ML-Assisted | "machine learning vulnerability detection code" | AI-enhanced scanning |
| Semantic Analysis | "semantic code analysis security vulnerability patterns" | Context-aware detection |
| False Positive Reduction | "false positive reduction static security analysis" | Better precision |
| Zero-Day | "zero-day vulnerability pattern detection heuristics" | Novel vuln detection |

---

## Current Capabilities (v1.0)

### Community Tier
- ✅ SQL Injection detection (CWE-89) - `sql_injection_detection`
- ✅ XSS detection (CWE-79) - `xss_detection`
- ✅ Command Injection (CWE-78) - `command_injection_detection`
- ✅ Path Traversal (CWE-22) - `path_traversal_detection`
- ✅ Basic taint tracking - `basic_vulnerabilities`
- ✅ OWASP checks - `owasp_checks`
- ✅ AST pattern matching - `ast_pattern_matching`
- ✅ Supports Python, JavaScript, Java, TypeScript
- ⚠️ **Limits:** 50 findings max, 500KB file size max

### Pro Tier
- ✅ All Community features (unlimited findings)
- ✅ NoSQL Injection (MongoDB, etc.) - `nosql_injection_detection`
- ✅ LDAP Injection - `ldap_injection_detection`
- ✅ Secret detection (API keys, passwords) - `secret_detection`
- ✅ **CSRF Detection** (Cross-Site Request Forgery) - `csrf_detection` [20260107]
- ✅ **SSRF Detection** (Server-Side Request Forgery) - `ssrf_detection` [20260107]
- ✅ **JWT Vulnerabilities** (insecure decode, 'none' algorithm) - `jwt_vulnerability_detection` [20260107]
- ✅ Advanced taint tracking - `data_flow_sensitive_analysis`
- ✅ Sanitizer detection (false positive reduction) - `sanitizer_recognition`
- ✅ Confidence scoring - `confidence_scoring`
- ✅ Context-aware scanning - `context_aware_scanning`
- ✅ Remediation suggestions - `remediation_suggestions` [20260107 - Now implemented in SecurityResult]
- ✅ OWASP categorization - `owasp_categorization`
- ✅ Full vulnerability list - `full_vulnerability_list`

### Enterprise Tier
- ✅ All Pro features
- ✅ Custom vulnerability rules - `custom_security_rules`
- ✅ Compliance mapping (OWASP, CWE, PCI-DSS, HIPAA, SOC2) - `compliance_rule_checking`

### v1.1 (Q1 2026): Polyglot Taint Foundations

#### All Tiers
- [ ] JS/TS/Java taint flows (sources→sinks) with sanitizer awareness
- [ ] Content-based language detection fallback (reduce extension misclass)
- [ ] Confidence + remediation attached to non-Python findings

#### Pro/Enterprise
- [ ] Reachability + priority ordering for JS/TS/Java findings
- [ ] Type-evaporation findings mapped into `vulnerabilities` with CWE/severity

- ✅ False positive tuning - `false_positive_tuning`
- ✅ Priority-based finding ordering - `priority_finding_ordering`
- ✅ Vulnerability reachability analysis - `vulnerability_reachability_analysis`
- ✅ Cross-file taint - `cross_file_taint`
- ✅ Custom policy engine - `custom_policy_engine`
- ✅ Organization-specific rules - `org_specific_rules`
- ✅ Compliance reporting - `compliance_reporting`
- ✅ Priority CVE alerts - `priority_cve_alerts`

---

## Return Model: SecurityResult

```python
class SecurityResult(BaseModel):
    # Core fields (All Tiers)
    success: bool                              # Whether scan succeeded
    has_vulnerabilities: bool                  # Quick check if any found
    vulnerability_count: int                   # Total vulnerabilities
    risk_level: str                            # "critical" | "high" | "medium" | "low" | "none"
    vulnerabilities: list[VulnerabilityInfo]   # Detailed findings
    taint_flows: list[TaintFlow]               # Source-to-sink paths
    scan_duration_ms: int                      # Scan time
    
    # Pro Tier
    sanitizer_paths: list[str] | None               # Detected sanitizers (Pro/Enterprise)
    confidence_scores: dict[str, float] | None      # Per-finding confidence
    remediation_suggestions: list[str] | None       # Fix suggestions [20260107 - Implemented]
    false_positive_analysis: dict[str, Any] | None  # FP reduction metadata
    taint_sources: list[str]                        # Identified taint sources
    
    # Enterprise Tier
    compliance_violations: list[ComplianceViol] # HIPAA/SOC2/PCI violations
    priority_order: list[int]                  # Suggested fix order
    custom_rule_matches: list[CustomMatch]     # Organization-specific rules
    
    error: str | None                          # Error message if failed
```

---

## Usage Examples

### Community Tier
```python
result = await security_scan(code='''
def get_user(user_id):
    query = f"SELECT * FROM users WHERE id = {user_id}"
    cursor.execute(query)  # SQL Injection!
''')
# Returns: vulnerability_count=1, risk_level="high",
#          vulnerabilities with CWE-89 SQL Injection
```

### Pro Tier
```python
result = await security_scan(
    file_path="/src/handlers.py",
    include_remediation=True
)
# Additional: confidence_scores, remediation_hints, owasp_mapping,
#             sanitized_flows (shows safe code patterns)
```

### Enterprise Tier
```python
result = await security_scan(
    file_path="/src/handlers.py",
    compliance_frameworks=["hipaa", "pci-dss"],
    custom_rules="security-policy.yaml"
)
# Additional: compliance_violations, priority_order, custom_rule_matches
```

---

## Integration Points

### Related Tools
| Tool | Relationship |
|------|--------------|
| `unified_sink_detect` | Lower-level sink detection |
| `cross_file_security_scan` | Multi-file taint tracking |
| `scan_dependencies` | External dependency vulnerabilities |
| `simulate_refactor` | Security impact of changes |
| `type_evaporation_scan` | Type boundary vulnerabilities |

### Export Formats
| Format | Status | Use Case |
|--------|--------|----------|
| **JSON** | ✅ v1.0 | Programmatic analysis |
| **SARIF** | 🔄 v1.4 | IDE/CI/CD integration |
| **HTML Report** | 🔄 v1.2 | Stakeholder reports |
| **CSV** | 🔄 v1.2 | Spreadsheet tracking |

---

## Competitive Analysis

| Tool | Strengths | Weaknesses | Our Differentiation |
|------|-----------|------------|---------------------|
| **Semgrep** | Fast, good patterns | Pattern-based, no taint | Full taint analysis |
| **Bandit** | Python-focused | Python only | Multi-language |
| **CodeQL** | Powerful queries | Steep learning curve | Simple API, MCP-native |
| **SonarQube** | Enterprise features | Heavy, self-hosted | Lightweight, AI-friendly |
| **Snyk Code** | Good AI | Expensive | Tier-based pricing |
| **Checkmarx** | Enterprise-grade | Very expensive | Accessible pricing |

---

## Configuration Files

### Tier Capabilities
- **File:** `src/code_scalpel/licensing/features.py` (line 100)
- **Structure:** Defines `capabilities` set and `limits` dict per tier

### Numeric Limits
- **File:** `.code-scalpel/limits.toml` (lines 167-175)
- **Community:** `max_findings=50`, `max_file_size_kb=500`
- **Pro/Enterprise:** Unlimited

### Response Verbosity
- **File:** `.code-scalpel/response_config.json` (line 60)
- **Purpose:** User-controlled output verbosity (NOT tier-gated)

---

## MCP Request/Response Examples

### MCP Request Format

```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "mcp_code-scalpel_security_scan",
    "arguments": {
      "code": "def get_user(user_id):\n    query = f\"SELECT * FROM users WHERE id = {user_id}\"\n    cursor.execute(query)"
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
    "has_vulnerabilities": true,
    "vulnerability_count": 1,
    "risk_level": "high",
    "vulnerabilities": [
      {
        "id": "vuln-001",
        "type": "SQL Injection",
        "cwe": "CWE-89",
        "severity": "high",
        "line": 2,
        "column": 12,
        "message": "User input 'user_id' flows into SQL query without sanitization",
        "source": "user_id (parameter)",
        "sink": "cursor.execute(query)",
        "evidence": "query = f\"SELECT * FROM users WHERE id = {user_id}\""
      }
    ],
    "taint_flows": [
      {
        "source": {"type": "parameter", "name": "user_id", "line": 1},
        "sink": {"type": "sql_execute", "name": "cursor.execute", "line": 3},
        "path": ["user_id", "query", "cursor.execute"]
      }
    ],
    "scan_duration_ms": 45,
    "sanitized_flows": null,
    "confidence_scores": null,
    "remediation_hints": null,
    "owasp_mapping": null,
    "compliance_violations": null,
    "priority_order": null,
    "custom_rule_matches": null,
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
    "has_vulnerabilities": true,
    "vulnerability_count": 1,
    "risk_level": "high",
    "vulnerabilities": [
      {
        "id": "vuln-001",
        "type": "SQL Injection",
        "cwe": "CWE-89",
        "severity": "high",
        "line": 2,
        "column": 12,
        "message": "User input 'user_id' flows into SQL query without sanitization",
        "source": "user_id (parameter)",
        "sink": "cursor.execute(query)",
        "evidence": "query = f\"SELECT * FROM users WHERE id = {user_id}\""
      }
    ],
    "taint_flows": [
      {
        "source": {"type": "parameter", "name": "user_id", "line": 1},
        "sink": {"type": "sql_execute", "name": "cursor.execute", "line": 3},
        "path": ["user_id", "query", "cursor.execute"]
      }
    ],
    "scan_duration_ms": 62,
    "sanitized_flows": [],
    "confidence_scores": {
      "vuln-001": 0.95
    },
    "remediation_hints": [
      {
        "vulnerability_id": "vuln-001",
        "suggestion": "Use parameterized queries instead of string formatting",
        "example": "cursor.execute(\"SELECT * FROM users WHERE id = ?\", (user_id,))",
        "references": [
          "https://cheatsheetseries.owasp.org/cheatsheets/Query_Parameterization_Cheat_Sheet.html"
        ]
      }
    ],
    "owasp_mapping": {
      "A03:2021-Injection": ["vuln-001"]
    },
    "compliance_violations": null,
    "priority_order": null,
    "custom_rule_matches": null,
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
    "has_vulnerabilities": true,
    "vulnerability_count": 1,
    "risk_level": "high",
    "vulnerabilities": [
      {
        "id": "vuln-001",
        "type": "SQL Injection",
        "cwe": "CWE-89",
        "severity": "high",
        "line": 2,
        "column": 12,
        "message": "User input 'user_id' flows into SQL query without sanitization",
        "source": "user_id (parameter)",
        "sink": "cursor.execute(query)",
        "evidence": "query = f\"SELECT * FROM users WHERE id = {user_id}\""
      }
    ],
    "taint_flows": [],
    "scan_duration_ms": 78,
    "sanitized_flows": [],
    "confidence_scores": {
      "vuln-001": 0.95
    },
    "remediation_hints": [
      {
        "vulnerability_id": "vuln-001",
        "suggestion": "Use parameterized queries",
        "example": "cursor.execute(\"SELECT * FROM users WHERE id = ?\", (user_id,))"
      }
    ],
    "owasp_mapping": {
      "A03:2021-Injection": ["vuln-001"]
    },
    "compliance_violations": [
      {
        "framework": "PCI-DSS",
        "requirement": "6.5.1",
        "description": "Protect against injection flaws",
        "vulnerability_ids": ["vuln-001"],
        "severity": "critical",
        "remediation_deadline": "immediate"
      },
      {
        "framework": "HIPAA",
        "requirement": "164.312(a)(1)",
        "description": "Access control - unique user identification",
        "vulnerability_ids": ["vuln-001"],
        "severity": "high",
        "remediation_deadline": "30 days"
      }
    ],
    "priority_order": [0],
    "custom_rule_matches": [
      {
        "rule_id": "org-sql-001",
        "rule_name": "No string formatting in SQL",
        "matched": true,
        "vulnerability_ids": ["vuln-001"]
      }
    ],
    "error": null
  },
  "id": 1
}
```

---

## Known Gaps for Polyglot Shape

### Gap #1: Taint is Python-Only
**Issue:** JS/TS/Java use sink detection without taint flows, sanitizers, or remediation.

**Status:** 🔴 BLOCKING polyglot shape

**Resolution Target:** v1.1 (Q1 2026)

**Acceptance Criteria:**
- JS/TS/Java have source→sink taint flows with sanitizer awareness
- Vulnerabilities include CWE, severity, remediation, and confidence (not sink-only)
- Benchmarks show ≥90% precision/recall on curated JS/TS/Java repos

### Gap #2: TypeScript Type Evaporation Not Integrated
**Issue:** Type-evaporation findings are separate from main vulnerability list.

**Status:** 🟡 MAJOR

**Resolution Target:** v1.2 (Q2 2026)

**Acceptance Criteria:**
- Type-evaporation findings appear in `vulnerabilities` with CWE/severity/remediation
- Confidence and reachability are computed for type-evaporation issues

### Gap #3: Language Detection Is Extension-Only
**Issue:** No content-based language detection fallback; misclassification risk on mixed extensions.

**Status:** 🟠 MINOR

**Resolution Target:** v1.1 (Q1 2026)

**Acceptance Criteria:**
- Content-based detection backs file-extension inference
- Fallback path documented; <1% mis-detected language rate on mixed-language corpus

### Gap #4: Missing Languages (Go/Rust/PHP/Ruby/C/C++)
**Issue:** Roadmap lists languages but there is no implementation.

**Status:** 🟡 MAJOR

**Resolution Target:** v1.3 (Q3 2026) for sink coverage; taint MVP prioritized per demand

**Acceptance Criteria:**
- Sink detection for Go/Rust/PHP/Ruby/C/C++ with CWE/severity/confidence
- Taint MVP added for at least Go/Rust/PHP with sanitizer hooks

---

## Roadmap

### Polyglot Blockers (Must Complete First)
- [ ] **Gap #1:** Add JS/TS/Java taint flows with sanitizer + remediation (target v1.1)
- [ ] **Gap #3:** Add content-based language detection fallback (target v1.1)

### v1.0 (Q1 2026): Enhanced Detection

#### Community Tier
- [ ] Regex DoS detection
- [ ] Insecure deserialization
- [ ] XXE (XML External Entity)

#### Pro Tier
- [ ] CSRF detection
- [ ] SSRF detection
- [ ] JWT vulnerability detection
- [ ] OAuth misconfiguration detection

#### Enterprise Tier
- [ ] Zero-day pattern detection
- [ ] Custom sink definitions
- [ ] Automated remediation suggestions

### v1.2 (Q2 2026): Language Expansion

#### All Tiers
- [ ] Rust security scanning (sink + taint MVP)
- [ ] Go security scanning (sink + taint MVP)
- [ ] PHP security scanning (sink + taint MVP)
- [ ] Harden JS/TS/Java sanitizers + remediation (post-taint rollout)
- [ ] Integrate TypeScript type-evaporation into main vulnerability list (CWE/severity/remediation)

#### Pro Tier
- [ ] Ruby security scanning
- [ ] C/C++ security scanning
- [ ] Swift security scanning

### v1.3 (Q3 2026): AI-Enhanced Detection

#### Pro Tier
- [ ] ML-based vulnerability prediction
- [ ] Anomaly-based detection
- [ ] Context-aware severity scoring

#### Enterprise Tier
- [ ] Custom ML model training
- [ ] Behavioral pattern analysis
- [ ] Threat intelligence integration

### v1.4 (Q4 2026): Integration & Automation

#### Community Tier
- [ ] GitHub Security Advisory integration
- [ ] SARIF output format
- [ ] CI/CD integration helpers

#### Pro Tier
- [ ] Jira vulnerability tracking
- [ ] Slack/Teams notifications
- [ ] Automated PR comments

#### Enterprise Tier
- [ ] SIEM integration
- [ ] ServiceNow incident creation
- [ ] Custom webhook notifications

---

## Known Issues & Limitations

### Current Limitations
- **False positives:** Some sanitizers not recognized
- **Interprocedural:** Limited cross-function tracking
- **Dynamic code:** Cannot analyze eval() contents

### Planned Fixes
- v1.0: Expanded sanitizer library
- v1.2: Improved interprocedural analysis
- v1.3: Partial dynamic code inference

---

## Success Metrics

### Performance Targets
- **Scan time:** <500ms for 1000 LOC
- **False positive rate:** <10%
- **Detection rate:** >95% for OWASP Top 10

### Adoption Metrics
- **Usage:** 1M+ scans per month by Q4 2026
- **Critical findings:** 100K+ high-severity issues found

---

## Dependencies

### Internal Dependencies
- `security/analyzers/taint_tracker.py` - Taint analysis
- `security/analyzers/sanitizer_detector.py` - Sanitizer detection
- `security/analyzers/unified_sink_detector.py` - Sink detection

### External Dependencies
- None (self-contained)

---

## Breaking Changes

None planned for v1.x series.

**API Stability Promise:**
- Tool signature stable
- Finding format backward compatible
- CWE mappings stable

---

**Last Updated:** December 30, 2025  
**Next Review:** March 31, 2026
**Changelog:** v1.0 - Added capability names, configuration file references, TypeScript support
