# get_file_context Tool Roadmap

**Tool Name:** `get_file_context`  
**Tool Version:** v1.0  
**Code Scalpel Version:** v3.3.1  
**Current Status:** Stable  
**Primary Module:** `src/code_scalpel/mcp/server.py`  
**Tier Availability:** All tiers (Community, Pro, Enterprise)

---

## Overview

The `get_file_context` tool provides file overview without reading full content - returns functions, classes, imports, complexity, and security warnings in ~50-150 tokens depending on tier.

**Why AI Agents Need This:**
- Quickly assess file relevance before extracting code (~50 tokens vs ~10,000)
- Understand file structure without token overhead
- Make informed decisions about which functions to modify
- **All tiers get security warnings** - critical for safe AI-assisted development
- Pro/Enterprise: Get code quality metrics and compliance flags in context

---

## Current Capabilities (v1.0)

### Community Tier (World-Class Base Features)
- ✅ Function and class listing
- ✅ Import detection (max 20, with truncation indicator)
- ✅ Export detection (`__all__`)
- ✅ Line count
- ✅ Cyclomatic complexity scoring
- ✅ **Security warnings with CWE references** (all tiers - because security matters)
- ✅ Module summary generation
- ✅ Multi-language support: Python, JavaScript, TypeScript, Java
- ✅ Path resolution with helpful error messages

**Capability Keys:** `raw_source_retrieval`, `ast_based_outlining`, `function_folding`, `class_folding`, `line_range_extraction`

**Limits:** `max_context_lines: 500`

### Pro Tier (Code Quality Metrics)
- ✅ All Community features
- ✅ **Semantic summarization** (`semantic_summarization`)
  - Enhanced summary with docstring content
- ✅ **Intent extraction** (`intent_extraction`)
  - Auto-tags from function/class names and docstrings
- ✅ **Related imports inclusion** (`related_imports_inclusion`)
  - Resolves local imports to actual file paths
- ✅ **Smart context expansion** (`smart_context_expansion`)
  - Preview of file content (up to 2000 lines)
- ✅ **Code smell detection** (`code_smell_detection`)
  - Long functions (>50 lines)
  - Too many parameters (>5)
  - Deep nesting (>4 levels)
  - God classes (>20 methods)
  - Magic numbers
  - Bare except clauses
- ✅ **Documentation coverage** (`documentation_coverage`)
  - Percentage of functions/classes with docstrings
  - Module docstring detection
- ✅ **Maintainability index** (`maintainability_index`)
  - 0-100 scale (higher is better)
  - Based on Halstead volume, McCabe complexity, LOC

**Limits:** `max_context_lines: 2000`

**Implementation:** `_detect_code_smells()`, `_calculate_doc_coverage()`, `_calculate_maintainability_index()`

### Enterprise Tier (Organizational Metadata)
- ✅ All Pro features
- ✅ **PII redaction** (`pii_redaction`)
  - Email pattern detection and flagging
- ✅ **Secret masking** (`secret_masking`)
  - AWS key detection, password assignments
- ✅ **API key detection** (`api_key_detection`)
  - Flags potential exposed API keys
- ✅ **RBAC-aware retrieval** (`rbac_aware_retrieval`)
  - Access control flag for enterprise governance
- ✅ **File access control** (`file_access_control`)
  - Enterprise-level file permission awareness
- ✅ **Custom metadata extraction** (`custom_metadata_extraction`)
  - Reads `.code-scalpel/metadata.yaml`
  - File-specific and global metadata
- ✅ **Compliance flags** (`compliance_flags`)
  - HIPAA (health data patterns)
  - PCI-DSS (payment card patterns)
  - SOC2 (security/audit patterns)
  - GDPR (personal data patterns)
- ✅ **Technical debt scoring** (`technical_debt_scoring`)
  - Hours estimate based on smells, complexity, doc coverage
- ✅ **Owner/team mapping** (`owner_team_mapping`)
  - CODEOWNERS file parsing
  - Supports `.github/CODEOWNERS`, `CODEOWNERS`, `docs/CODEOWNERS`
- ✅ **Historical metrics** (`historical_metrics`)
  - Git churn (commit count)
  - File age in days
  - Contributor list and count
  - Last modified date

**Limits:** `max_context_lines: None` (unlimited)

**Implementation:** `_load_custom_metadata()`, `_detect_compliance_flags()`, `_calculate_technical_debt()`, `_get_code_owners()`, `_get_historical_metrics()`

---

## Return Model: FileContextResult

```python
class FileContextResult(BaseModel):
    # Core fields (All Tiers)
    success: bool                           # Whether analysis succeeded
    file_path: str                          # Absolute file path
    language: str                           # Detected language
    line_count: int                         # Total lines
    functions: list[str]                    # Top-level function names
    classes: list[str]                      # Class names
    imports: list[str]                      # Module imports (max 20)
    exports: list[str]                      # Exported symbols (__all__)
    complexity_score: int                   # Cyclomatic complexity
    has_security_issues: bool               # Security warnings detected
    security_warnings: list[str]            # CWE-referenced warning descriptions
    summary: str                            # Brief description
    imports_truncated: bool                 # Whether imports were truncated
    total_imports: int                      # Total imports before truncation
    
    # Output Metadata Fields (All Tiers) - [20260108_FEATURE]
    tier_applied: str                       # "community", "pro", or "enterprise"
    max_context_lines_applied: int | None   # 500, 2000, or None (unlimited)
    pro_features_enabled: bool              # Whether Pro tier features were enabled
    enterprise_features_enabled: bool       # Whether Enterprise tier features were enabled
    
    # Pro Tier
    semantic_summary: str | None            # Enhanced summary with docstring
    intent_tags: list[str]                  # Extracted intents/topics
    related_imports: list[str]              # Resolved import file paths
    expanded_context: str | None            # File content preview
    code_smells: list[dict]                 # [{type, line, message, severity}]
    doc_coverage: float | None              # 0.0-100.0 percentage
    maintainability_index: float | None     # 0-100 scale
    
    # Enterprise Tier
    pii_redacted: bool                      # Whether PII was found
    secrets_masked: bool                    # Whether secrets were found
    redaction_summary: list[str]            # Actions taken
    access_controlled: bool                 # RBAC applied
    custom_metadata: dict                   # From .code-scalpel/metadata.yaml
    compliance_flags: list[str]             # HIPAA, PCI, SOC2, etc.
    technical_debt_score: float | None      # Hours estimate
    owners: list[str]                       # From CODEOWNERS
    historical_metrics: dict | None         # Git metrics
```

---

## Output Metadata Fields - Tier Transparency

**[20260108_FEATURE]** Four new output metadata fields provide AI agents with introspection into which tier configuration was applied to their request.

### Why This Matters for AI Agents

When an AI agent calls `get_file_context`, it needs to understand:
1. Which tier's configuration was applied to the response
2. What limits were in effect (e.g., line truncation)
3. Whether Pro/Enterprise features were actually enabled

This transparency enables:
- **Debugging**: Agent can verify expected tier is active
- **Adaptive behavior**: Agent can adjust requests based on tier capabilities
- **User communication**: Agent can inform user which features were available

### Metadata Field Reference

| Field | Type | Description |
|-------|------|-------------|
| `tier_applied` | `str` | The tier that was applied: "community", "pro", or "enterprise" |
| `max_context_lines_applied` | `int \| None` | Line limit: 500 (Community), 2000 (Pro), None (Enterprise) |
| `pro_features_enabled` | `bool` | True if Pro tier capabilities were active |
| `enterprise_features_enabled` | `bool` | True if Enterprise tier capabilities were active |

### Tier-Specific Values

| Tier | tier_applied | max_context_lines_applied | pro_features_enabled | enterprise_features_enabled |
|------|--------------|---------------------------|----------------------|----------------------------|
| Community | "community" | 500 | False | False |
| Pro | "pro" | 2000 | True | False |
| Enterprise | "enterprise" | None | True | True |

### Example Usage

```python
result = await get_file_context("/src/utils.py")

# Check which tier was applied
if result.tier_applied == "community":
    print(f"Community tier: Limited to {result.max_context_lines_applied} lines")
    
# Verify expected capabilities
if not result.pro_features_enabled:
    print("Note: Code smell detection not available in current tier")
    
# Adaptive agent behavior
if result.enterprise_features_enabled:
    # Can rely on PII redaction being active
    print("Enterprise: Full security features active")
```

---

## Usage Examples

### Community Tier
```python
result = await get_file_context("/src/utils.py")
# Returns all core fields:
# - success, file_path, language, line_count
# - functions, classes, imports, exports
# - complexity_score, has_security_issues, security_warnings
# - summary, imports_truncated, total_imports

# Security warnings example:
# security_warnings: [
#     "Use of eval() can execute arbitrary code (CWE-94)",
#     "Shell command execution via os.system() (CWE-78)"
# ]
```

### Pro Tier
```python
result = await get_file_context("/src/payment_handler.py")
# All Community fields PLUS:
# - semantic_summary: "Payment handler module. Docstring: Handles Stripe payments..."
# - intent_tags: ["payment", "stripe", "handler", "process"]
# - related_imports: ["/src/models/transaction.py", "/src/utils/validator.py"]
# - expanded_context: "import stripe\nfrom ..." (first 2000 lines)
# - code_smells: [{"type": "long_function", "line": 45, "message": "...", "severity": "medium"}]
# - doc_coverage: 75.5
# - maintainability_index: 68.2
```

### Enterprise Tier
```python
result = await get_file_context("/src/services/auth.py")
# All Pro fields PLUS:
# - pii_redacted: True
# - secrets_masked: True
# - redaction_summary: ["Redacted email", "Masked aws_access_key"]
# - access_controlled: True
# - custom_metadata: {"team": "security", "pii": true}
# - compliance_flags: ["HIPAA", "SOC2"]
# - technical_debt_score: 4.5
# - owners: ["@security-team", "@alice"]
# - historical_metrics: {"churn": 42, "age_days": 180, "contributors": [...]}
```

---

## MCP Request/Response Examples

### MCP Request Format

```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "mcp_code-scalpel_get_file_context",
    "arguments": {
      "file_path": "/home/user/project/src/utils.py"
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
    "file_path": "/home/user/project/src/utils.py",
    "language": "python",
    "line_count": 150,
    "functions": ["calculate_tax", "format_currency", "validate_email"],
    "classes": ["TaxCalculator", "CurrencyFormatter"],
    "imports": ["decimal", "re", "typing"],
    "exports": ["calculate_tax", "TaxCalculator"],
    "complexity_score": 8,
    "has_security_issues": true,
    "security_warnings": [
      "Use of eval() can execute arbitrary code (CWE-94) at line 45"
    ],
    "summary": "Utility module with 3 functions and 2 classes for financial calculations",
    "imports_truncated": false,
    "total_imports": 3,
    "tier_applied": "community",
    "max_context_lines_applied": 500,
    "pro_features_enabled": false,
    "enterprise_features_enabled": false
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
    "file_path": "/home/user/project/src/utils.py",
    "language": "python",
    "line_count": 150,
    "functions": ["calculate_tax", "format_currency", "validate_email"],
    "classes": ["TaxCalculator", "CurrencyFormatter"],
    "imports": ["decimal", "re", "typing"],
    "exports": ["calculate_tax", "TaxCalculator"],
    "complexity_score": 8,
    "has_security_issues": true,
    "security_warnings": [
      "Use of eval() can execute arbitrary code (CWE-94) at line 45"
    ],
    "summary": "Utility module with 3 functions and 2 classes for financial calculations",
    "imports_truncated": false,
    "total_imports": 3,
    "tier_applied": "pro",
    "max_context_lines_applied": 2000,
    "pro_features_enabled": true,
    "enterprise_features_enabled": false,
    "semantic_summary": "Financial utility module. Docstring: Provides tax calculation, currency formatting, and email validation utilities for the billing system.",
    "intent_tags": ["financial", "tax", "currency", "validation", "utility"],
    "related_imports": [
      "/home/user/project/src/config.py",
      "/home/user/project/src/models/transaction.py"
    ],
    "expanded_context": "\"\"\"Financial utility module.\n\nProvides tax calculation...\"\"\"\n\nfrom decimal import Decimal\nimport re\n...",
    "code_smells": [
      {
        "type": "long_function",
        "line": 45,
        "message": "Function 'validate_email' has 65 lines (>50)",
        "severity": "medium"
      },
      {
        "type": "too_many_params",
        "line": 78,
        "message": "Function 'calculate_tax' has 7 parameters (>5)",
        "severity": "low"
      }
    ],
    "doc_coverage": 66.7,
    "maintainability_index": 72.5
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
    "file_path": "/home/user/project/src/utils.py",
    "language": "python",
    "line_count": 150,
    "functions": ["calculate_tax", "format_currency", "validate_email"],
    "classes": ["TaxCalculator", "CurrencyFormatter"],
    "imports": ["decimal", "re", "typing"],
    "exports": ["calculate_tax", "TaxCalculator"],
    "complexity_score": 8,
    "has_security_issues": true,
    "security_warnings": [
      "Use of eval() can execute arbitrary code (CWE-94) at line 45"
    ],
    "summary": "Utility module with 3 functions and 2 classes for financial calculations",
    "imports_truncated": false,
    "total_imports": 3,
    "tier_applied": "enterprise",
    "max_context_lines_applied": null,
    "pro_features_enabled": true,
    "enterprise_features_enabled": true,
    "semantic_summary": "Financial utility module. Docstring: Provides tax calculation...",
    "intent_tags": ["financial", "tax", "currency", "validation", "utility"],
    "related_imports": ["/home/user/project/src/config.py"],
    "expanded_context": "...",
    "code_smells": [
      {
        "type": "long_function",
        "line": 45,
        "message": "Function 'validate_email' has 65 lines (>50)",
        "severity": "medium"
      }
    ],
    "doc_coverage": 66.7,
    "maintainability_index": 72.5,
    "pii_redacted": true,
    "secrets_masked": false,
    "redaction_summary": ["Redacted email pattern at line 120"],
    "access_controlled": true,
    "custom_metadata": {
      "team": "billing",
      "pii": true,
      "review_required": true
    },
    "compliance_flags": ["PCI-DSS", "SOC2"],
    "technical_debt_score": 3.5,
    "owners": ["@billing-team", "@alice"],
    "historical_metrics": {
      "churn": 28,
      "age_days": 365,
      "contributors": ["alice", "bob", "charlie"],
      "contributor_count": 3,
      "last_modified": "2025-12-15T10:30:00Z"
    }
  },
  "id": 1
}
```

---

## Roadmap

### v1.1 (Q1 2026): Enhanced Metadata

#### Community Tier
- [ ] Test file detection (pytest, unittest patterns)
- [ ] Entry point identification (`__main__`, `if __name__`)
- [ ] License header detection
- [ ] More security patterns (deserialization, XXE, SSRF)

#### Pro Tier
- [ ] API surface extraction (public vs private)
- [ ] Type hint coverage percentage
- [ ] Recent change frequency (from git log)

#### Enterprise Tier
- [ ] Custom compliance pattern rules
- [ ] Team velocity metrics
- [ ] Risk scoring based on history

### v1.2 (Q2 2026): Language Enhancement

#### All Tiers
- [x] ~~JavaScript/TypeScript context extraction~~ (Done in v1.0)
- [x] ~~Java context extraction~~ (Done in v1.0)
- [ ] Go context extraction
- [ ] Rust context extraction

#### Pro Tier
- [ ] Framework-specific metrics (React, Spring, etc.)
- [ ] Dependency analysis per file

### v1.3 (Q3 2026): Performance Optimization

#### All Tiers
- [ ] Faster context extraction (<10ms)
- [ ] Parallel file processing
- [ ] Smart caching with invalidation

#### Enterprise Tier
- [ ] Incremental context updates
- [ ] Batch context extraction API

---

## Known Issues & Limitations

### Current Limitations
- **Best for Python:** Deepest analysis for Python files; JS/TS/Java use generic AST
- **Git dependency:** Historical metrics require git CLI
- **YAML dependency:** Custom metadata requires PyYAML
- **Subprocess calls:** Historical metrics use git CLI

### Planned Fixes
- v1.2: Enhanced multi-language analysis (Go, Rust)
- v1.3: Pure Python git integration (gitpython)

---

## Success Metrics

### Performance Targets
- **Extraction time:** <50ms per file (Community), <100ms (Pro/Enterprise)
- **Accuracy:** >99% correct function/class counts
- **Token efficiency:** <100 tokens (Community), <200 tokens (Pro/Enterprise)

### Quality Targets
- **Maintainability Index accuracy:** ±5% vs manual calculation
- **Code smell detection:** 95%+ precision, 80%+ recall
- **CODEOWNERS parsing:** 100% compatibility with GitHub format

---

## Dependencies

### Internal Dependencies
- `mcp/server.py` - MCP tool implementation
- `licensing/features.py` - Tier capability gating
- `cache/unified_cache.py` - Caching (planned)

### External Dependencies
- **PyYAML** (optional) - Custom metadata parsing
- **git CLI** (optional) - Historical metrics

---

## Research Queries for Future Development

### Competitive Analysis
- How do other tools (SonarQube, CodeClimate) calculate maintainability?
- What code smell patterns are most valuable for AI agents?
- Which compliance patterns should be added?

### Integration Questions
- Should we integrate with JIRA/Linear for technical debt tracking?
- How to handle monorepo CODEOWNERS with path-based ownership?
- ML-based code smell detection feasibility?

---

## Breaking Changes

**v1.4.0 (current):**
- Added 8 new optional fields to FileContextResult
- No breaking changes - new fields are nullable

**v1.5.0 (planned):**
- None expected

---

**Last Updated:** December 31, 2025  
**Next Review:** March 31, 2026
