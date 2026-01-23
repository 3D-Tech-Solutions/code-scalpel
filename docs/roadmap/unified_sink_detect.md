# unified_sink_detect Tool Roadmap

**Tool Name:** `unified_sink_detect`  
**Tool Version:** v1.0  
**Code Scalpel Version:** v3.3.1  
**Current Status:** Stable  
**Primary Module:** `src/code_scalpel/mcp/server.py`  
**Tier Availability:** All tiers (Community, Pro, Enterprise)

---

## Overview

The `unified_sink_detect` tool detects dangerous sinks (eval, execute, system, etc.) across multiple languages with confidence thresholds and CWE mapping.

**Why AI Agents Need This:**
- **Language-agnostic security:** One API for all languages
- **Precise detection:** Confidence scores help prioritize real threats
- **Standard compliance:** CWE mapping for security standards
- **Foundation for taint analysis:** Sinks are the endpoints for taint tracking
- **Customizable rules:** Enterprise tier allows organization-specific patterns

---

## Research Queries for Future Development

### Foundational Research
| Topic | Query | Purpose |
|-------|-------|---------|
| Sink Patterns | "dangerous function detection static analysis patterns" | Improve coverage |
| Confidence Scoring | "static analysis confidence scoring calibration" | Better scoring |
| CWE Taxonomy | "common weakness enumeration automated classification" | Accurate mapping |
| False Positives | "security static analysis false positive reduction" | Better precision |

### Language-Specific Research
| Topic | Query | Purpose |
|-------|-------|---------|
| Python Sinks | "python dangerous functions security eval exec os.system" | Complete Python coverage |
| JavaScript | "javascript dangerous patterns eval innerHTML document.write" | DOM security |
| Java | "java security sink functions OWASP" | Enterprise Java |
| Go | "go security dangerous functions exec command injection" | Go support |

### Advanced Techniques
| Topic | Query | Purpose |
|-------|-------|---------|
| Context-Aware | "context-sensitive security analysis false positives" | Better context |
| ML Detection | "machine learning security vulnerability pattern detection" | AI-powered detection |
| Framework-Aware | "framework-specific security patterns detection" | Framework support |
| Semantic Analysis | "semantic code analysis security sink identification" | Deeper understanding |

---

## Current Capabilities (v1.0)

### v1.0 Hardening Notes (Pre-release)
- Stable `sink_id` per sink for correlation across runs
- Snippet truncation with explicit indicators (`code_snippet_truncated`, `code_snippet_original_len`)
- Unsupported-language failures return `error_code=UNIFIED_SINK_DETECT_UNSUPPORTED_LANGUAGE` consistently (including detector-level rejections)

### Community Tier
- ✅ Python sink detection - `python_sink_detection`
- ✅ JavaScript sink detection - `javascript_sink_detection`
- ✅ TypeScript sink detection - `typescript_sink_detection`
- ✅ Java sink detection - `java_sink_detection`
- ✅ Basic confidence scoring - `basic_confidence_scoring`
- ✅ CWE mapping - `cwe_mapping`
- ⚠️ **Limits:** 50 sinks per scan

### Pro Tier
- ✅ All Community features (unlimited sinks)
- ✅ Advanced confidence scoring - `advanced_confidence_scoring`
- ✅ Context-aware detection - `context_aware_detection`
- ✅ Framework-specific sinks - `framework_specific_sinks`
- ✅ Custom sink definitions - `custom_sink_definitions`
- ✅ Sink coverage analysis - `sink_coverage_analysis`

### Enterprise Tier
- ✅ All Pro features
- ✅ Organization-specific sink rules - `organization_sink_rules`
- ✅ Sink risk scoring - `sink_risk_scoring`
- ✅ Compliance mapping - `compliance_mapping`
- ✅ Historical sink tracking - `historical_sink_tracking`
- ✅ Automated remediation suggestions - `automated_sink_remediation`

---

## Return Model: UnifiedSinkResult (Actual v1.0)

The canonical return schema is defined in `src/code_scalpel/mcp/server.py` as `UnifiedSinkResult` and `UnifiedDetectedSink`.

```python
class UnifiedDetectedSink(BaseModel):
  # Core sink fields (All tiers)
  sink_id: str
  pattern: str
  sink_type: str
  confidence: float
  line: int
  column: int
  code_snippet: str
  code_snippet_truncated: bool
  code_snippet_original_len: int | None
  vulnerability_type: str | None
  owasp_category: str | None
  cwe_id: str | None

class UnifiedSinkResult(BaseModel):
  # Core fields (All tiers)
  success: bool
  error_code: str | None
  server_version: str
  language: str
  sink_count: int
  sinks: list[UnifiedDetectedSink]
  coverage_summary: dict[str, Any]

  # Pro tier enrichments
  context_analysis: dict[str, Any] | None
  framework_sinks: list[dict[str, Any]]
  logic_sinks: list[dict[str, Any]]
  confidence_scores: dict[str, float]
  extended_language_sinks: dict[str, list[dict[str, Any]]]

  # Enterprise tier enrichments
  sink_categories: dict[str, list[dict[str, Any]]]
  risk_assessments: list[dict[str, Any]]
  custom_sink_matches: list[dict[str, Any]]
  compliance_mapping: dict[str, Any] | None
  historical_comparison: dict[str, Any] | None
  remediation_suggestions: list[dict[str, Any]]

  # Limit observability (All tiers, populated when applicable)
  truncated: bool | None
  sinks_detected: int | None
  max_sinks_applied: int | None

  # Human-readable error message
  error: str | None
```

---

## Usage Examples

### Community Tier
```python
result = await unified_sink_detect(
    code="eval(user_input)",
    language="python"
)
# Returns: sinks=[UnifiedDetectedSink(pattern="eval", line=1, cwe_id="CWE-94", confidence=...)],
#          sink_count=1, coverage_summary={...}
# Max 50 sinks
```

### Pro Tier
```python
result = await unified_sink_detect(
    code=code,
    language="javascript",
    min_confidence=0.7,
    include_framework_sinks=True
)
# Additional: context_analysis, framework_sinks, custom_matches, coverage_gaps
# Unlimited sinks
```

### Enterprise Tier
```python
result = await unified_sink_detect(
    code=code,
    language="java",
    custom_rules="org-sinks.yaml",
    generate_remediation=True
)
# Additional: risk_scores, compliance_tags, historical_trend, remediation_suggestions
```

---

## Integration Points

### Related Tools
| Tool | Relationship |
|------|--------------|
| `security_scan` | Uses sinks for taint terminus |
| `cross_file_security_scan` | Multi-file sink tracing |
| `type_evaporation_scan` | Type boundaries as pseudo-sinks |
| `crawl_project` | Find all files to scan |

### Export Formats
| Format | Status | Use Case |
|--------|--------|----------|
| **JSON** | ✅ v1.0 | Programmatic analysis |
| **SARIF** | 🔄 v1.3 | IDE integration |
| **CSV** | 🔄 v1.2 | Spreadsheet analysis |
| **HTML** | 🔄 v1.3 | Stakeholder reports |

---

## Competitive Analysis

| Tool | Strengths | Weaknesses | Our Differentiation |
|------|-----------|------------|---------------------|
| **Semgrep** | Pattern-based | Manual rules | Auto-detection |
| **Bandit** | Python-focused | Python only | Multi-language |
| **CodeQL** | Powerful | Complex setup | Simple API |
| **ESLint security** | JS ecosystem | JS only | Unified API |
| **SpotBugs** | Java-focused | Java only | Polyglot support |

---

## Configuration Files

### Tier Capabilities
- **File:** `src/code_scalpel/licensing/features.py` (line 1039)
- **Structure:** Defines `capabilities` set and `limits` dict per tier

### Numeric Limits
- **File:** `.code-scalpel/limits.toml` (lines 195-205)
- **Community:** `max_sinks=50`, languages: python, javascript, typescript, java
- **Pro:** Unlimited sinks. **Note:** current config lists `go` and `rust`, but the underlying detector only supports python/javascript/typescript/java. v1.0 roadmap item: align `limits.toml` with actual detector support to avoid misleading contracts.
- **Enterprise:** Unlimited, all languages

### Response Verbosity
- **File:** `.code-scalpel/response_config.json` (line 161) (tool payload filtering inside envelope `data`)
- **Exclude fields (current):** `detection_metadata`, `pattern_match_details`
- **Note:** these fields are not present in the actual `UnifiedSinkResult` schema, so the current exclude list is effectively a no-op. v1.0 roadmap item: align response filtering with real high-payload fields (e.g., `sinks.code_snippet`, `context_analysis`, `framework_sinks`, `compliance_mapping`, `historical_comparison`, `remediation_suggestions`).

---

## MCP Request/Response Examples

### MCP Request Format

```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "mcp_code-scalpel_unified_sink_detect",
    "arguments": {
      "code": "eval(user_input)",
      "language": "python"
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
    "sinks": [
      {
        "name": "eval",
        "line": 1,
        "column": 0,
        "cwe": "CWE-94",
        "confidence": 0.95,
        "category": "code_injection",
        "context": null
      }
    ],
    "sink_count": 1,
    "coverage": {
      "code_injection": true,
      "sql_injection": false,
      "command_injection": false,
      "xss": false,
      "path_traversal": false,
      "deserialization": false,
      "xxe": false,
      "ldap_injection": false
    },
    "language": "python",
    "context_analysis": null,
    "framework_sinks": null,
    "custom_matches": null,
    "coverage_gaps": null,
    "risk_scores": null,
    "compliance_tags": null,
    "historical_trend": null,
    "remediation_suggestions": null,
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
    "sinks": [
      {
        "name": "eval",
        "line": 1,
        "column": 0,
        "cwe": "CWE-94",
        "confidence": 0.95,
        "category": "code_injection",
        "context": "eval(user_input)  # Direct user input to eval"
      }
    ],
    "sink_count": 1,
    "coverage": {
      "code_injection": true,
      "sql_injection": false,
      "command_injection": false,
      "xss": false,
      "path_traversal": false,
      "deserialization": false,
      "xxe": false,
      "ldap_injection": false
    },
    "language": "python",
    "context_analysis": {
      "eval": "Function parameter 'user_input' flows directly to eval() without sanitization"
    },
    "framework_sinks": [],
    "custom_matches": [],
    "coverage_gaps": [
      "No SQL queries detected - sql_injection not applicable",
      "No shell commands detected - command_injection not applicable"
    ],
    "risk_scores": null,
    "compliance_tags": null,
    "historical_trend": null,
    "remediation_suggestions": null,
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
    "sinks": [
      {
        "name": "eval",
        "line": 1,
        "column": 0,
        "cwe": "CWE-94",
        "confidence": 0.95,
        "category": "code_injection",
        "context": "eval(user_input)"
      }
    ],
    "sink_count": 1,
    "coverage": {
      "code_injection": true,
      "sql_injection": false,
      "command_injection": false,
      "xss": false,
      "path_traversal": false,
      "deserialization": false,
      "xxe": false,
      "ldap_injection": false
    },
    "language": "python",
    "context_analysis": {
      "eval": "Direct user input to eval() without sanitization"
    },
    "framework_sinks": [],
    "custom_matches": [
      {
        "rule_id": "org-no-eval",
        "rule_name": "No eval() usage allowed",
        "sink_name": "eval",
        "line": 1,
        "enforced_by": "security-policy.yaml"
      }
    ],
    "coverage_gaps": [],
    "risk_scores": {
      "eval@line1": 95
    },
    "compliance_tags": {
      "eval@line1": [
        "OWASP-A03:2021-Injection",
        "CWE-94",
        "SANS-TOP25-Injection",
        "PCI-DSS-6.5.1"
      ]
    },
    "historical_trend": {
      "current_count": 1,
      "previous_count": 0,
      "trend": "increasing",
      "first_detected": "2025-12-29T14:30:22Z"
    },
    "remediation_suggestions": [
      {
        "sink": "eval",
        "line": 1,
        "severity": "critical",
        "suggestion": "Replace eval() with safer alternatives",
        "alternatives": [
          "Use ast.literal_eval() for safe literal evaluation",
          "Use json.loads() for JSON parsing",
          "Use a whitelist-based expression evaluator"
        ],
        "example": "import ast\nresult = ast.literal_eval(user_input)  # Only allows literals"
      }
    ],
    "error": null
  },
  "id": 1
}
```

### Pro Tier Response (JavaScript/DOM)

```json
{
  "jsonrpc": "2.0",
  "result": {
    "success": true,
    "sinks": [
      {
        "name": "innerHTML",
        "line": 5,
        "column": 4,
        "cwe": "CWE-79",
        "confidence": 0.92,
        "category": "xss",
        "context": "element.innerHTML = userContent;"
      },
      {
        "name": "eval",
        "line": 8,
        "column": 0,
        "cwe": "CWE-94",
        "confidence": 0.95,
        "category": "code_injection",
        "context": "eval(dynamicCode);"
      }
    ],
    "sink_count": 2,
    "coverage": {
      "code_injection": true,
      "sql_injection": false,
      "command_injection": false,
      "xss": true,
      "path_traversal": false,
      "deserialization": false,
      "xxe": false,
      "ldap_injection": false
    },
    "language": "javascript",
    "context_analysis": {
      "innerHTML": "User-controlled content assigned to innerHTML - XSS risk",
      "eval": "Dynamic code execution from variable"
    },
    "framework_sinks": [
      {
        "name": "dangerouslySetInnerHTML",
        "framework": "React",
        "line": 12,
        "cwe": "CWE-79",
        "confidence": 0.88
      }
    ],
    "custom_matches": [],
    "coverage_gaps": [],
    "risk_scores": null,
    "compliance_tags": null,
    "historical_trend": null,
    "remediation_suggestions": null,
    "error": null
  },
  "id": 1
}
```

---

## Roadmap

### v1.1 (Q1 2026): Language Expansion

#### Community Tier
- [ ] Go sink detection
- [ ] Rust sink detection
- [ ] PHP sink detection

#### Pro Tier
- [ ] C/C++ sink detection
- [ ] Ruby sink detection
- [ ] Swift sink detection

#### Enterprise Tier
- [ ] Kotlin sink detection
- [ ] Scala sink detection
- [ ] Custom language sink definitions

### v1.2 (Q2 2026): Enhanced Detection

#### All Tiers
- [ ] Better framework-specific detection
- [ ] Improved false positive filtering
- [ ] Context-aware severity

#### Pro Tier
- [ ] Chained sink detection
- [ ] Indirect sink detection
- [ ] Sanitizer-aware analysis

#### Enterprise Tier
- [ ] Custom sanitizer definitions
- [ ] Organizational sink patterns
- [ ] ML-based sink prediction

### v1.3 (Q3 2026): Integration Features

#### Community Tier
- [ ] SARIF output format
- [ ] GitHub Security Advisory format
- [ ] CI/CD integration helpers

#### Pro Tier
- [ ] IDE real-time detection
- [ ] Automated PR comments
- [ ] Slack/Teams notifications

#### Enterprise Tier
- [ ] SIEM integration
- [ ] Jira security tickets
- [ ] ServiceNow incident creation

### v1.4 (Q4 2026): Advanced Features

#### Pro Tier
- [ ] Sink visualization
- [ ] Historical sink trends
- [ ] Sink risk forecasting

#### Enterprise Tier
- [ ] Custom compliance frameworks
- [ ] Automated security reviews
- [ ] Zero-day sink pattern matching

---

## Known Issues & Limitations

### Current Limitations
- **Dynamic sinks:** Cannot detect runtime-only sink creation
- **Obfuscated code:** May miss obfuscated sink calls
- **Framework abstractions:** Some framework wrappers not recognized

### Planned Fixes
- v1.1: Better framework coverage
- v1.2: Partial dynamic sink inference
- v1.3: Obfuscation handling

---

## Success Metrics

### Performance Targets
- **Scan time:** <200ms per file
- **Accuracy:** >95% correct sink detection
- **False positive rate:** <5%

### Adoption Metrics
- **Usage:** 200K+ scans per month by Q4 2026
- **Sinks found:** 20K+ dangerous sinks detected

---

## Dependencies

### Internal Dependencies
- `ir/` - Intermediate representation
- `code_parsers/factory.py` - Language detection
- `security/analyzers/confidence_scorer.py` - Confidence scoring

### External Dependencies
- `tree-sitter` - Multi-language parsing

---

## Breaking Changes

None planned for v1.x series.

**API Stability Promise:**
- Tool signature stable
- Sink format backward compatible
- CWE mappings stable

---

**Last Updated:** December 30, 2025  
**Next Review:** March 31, 2026
