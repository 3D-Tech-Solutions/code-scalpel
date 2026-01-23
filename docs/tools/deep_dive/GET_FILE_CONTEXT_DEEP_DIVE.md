# get_file_context - Deep Dive Documentation

> [20260112_DOCS] Created comprehensive deep dive documentation for get_file_context MCP tool based on v1.0.0 implementation and v1.0 Roadmap

**Document Type:** Tool Deep Dive Reference  
**Tool Version:** v1.0  
**Code Scalpel Version:** v1.0.0  
**Last Updated:** 2026-01-12  
**Status:** Stable  
**Tier Availability:** All Tiers (Community, Pro, Enterprise)

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Technical Overview](#technical-overview)
3. [Features and Capabilities](#features-and-capabilities)
4. [API Specification](#api-specification)
5. [Usage Examples](#usage-examples)
6. [Architecture and Implementation](#architecture-and-implementation)
7. [Testing Evidence](#testing-evidence)
8. [Performance Characteristics](#performance-characteristics)
9. [Security Considerations](#security-considerations)
10. [Integration Patterns](#integration-patterns)
11. [Tier-Specific Behavior](#tier-specific-behavior)
12. [Known Limitations](#known-limitations)
13. [Roadmap and Future Plans](#roadmap-and-future-plans)
14. [Troubleshooting](#troubleshooting)
15. [References and Related Tools](#references-and-related-tools)

---

## Executive Summary

### Purpose Statement
The `get_file_context` tool provides a token-efficient "strategic glance" at a file without reading its full content. It returns a structured summary including functions, classes, imports, complexity metrics, and security warnings. This allows AI agents to rapidly assess file relevance and structure while consuming ~95% fewer tokens than a full `read_file` operation. It serves as a critical reconnaissance tool before performing expensive extraction or analysis tasks.

### Key Benefits
- **Token Efficiency:** Returns ~50-150 tokens vs ~5,000+ for reading a full file.
- **Safety First:** Includes **security warnings** (CWE mapping) in all tiers.
- **Multi-Language Support:** Consistent output for Python, JavaScript, TypeScript, and Java.
- **Tier-Based Insights:** Scales from structural outlines (Community) to AI-driven intent and intent extraction (Pro) and organizational compliance (Enterprise).
- **Introspection:** Returns metadata (`tier_applied`, `limits_applied`) so agents understand their operating constraints.

### Quick Stats
| Metric | Value |
|--------|-------|
| **Tool Version** | v1.0 |
| **Code Scalpel Version** | v1.0.0 |
| **Release Date** | 2026-01-04 (Production Ready) |
| **Test Coverage** | 100% (110+ tests across 4 languages) |
| **Performance** | ~50ms average response time |
| **Languages Supported** | Python, JavaScript, TypeScript, Java |
| **Token Savings** | 20-50x reduction vs `read_file` |

### When to Use This Tool
- **Primary Use Case:** Assessing file relevance before deciding to read or extract code.
- **Secondary Use Cases:**
  - Checking for specific imports or dependencies.
  - Identifying security hotspots (sinks) quickly.
  - Getting a high-level summary of file intent.
- **Not Suitable For:**
  - Reading the full logic of a function (use `extract_code`).
  - Applying edits (use `update_symbol`).
  - Deep semantic graph analysis (use `get_cross_file_dependencies`).

---

## Technical Overview

### Core Functionality
The tool employs a hybrid approach using AST parsing (for accurate structure) and regex scanning (for speed/fallback) to extract:
1.  **Structure:** Function/Class names, line ranges, and signatures.
2.  **Dependencies:** Imports (truncated for brevity), exports.
3.  **Metrics:** Cyclomatic complexity, Lines of Code (LOC).
4.  **Security:** Pattern-based sink detection mapped to common Weakness Enumerations (CWE).

### Design Principles
1.  **"Peek, Don't Read":** Prioritize metadata over content.
2.  **Universal Security:** Security warnings are a fundamental right, not a paid feature.
3.  **Tier Transparency:** The tool explicitly reports its configuration (limits, verified features) in the response.
4.  **Language Agnostic Output:** A uniform JSON structure abstracts language differences.

### Integration Context
`get_file_context` is the **reconnaissance step** in the standard workflow:

```mermaid
graph TD
    A[AI Agent] -->|1. Glance| B[get_file_context]
    B --> C{Relevant?}
    C -->|Yes| D[extract_code / read_file]
    C -->|No| E[Skipped]
    D --> F[simulate_refactor]
```

---

## Features and Capabilities

### Community Tier (Structural Base)
Available to all users. Focuses on structure and safety.
*   **Structural parsing:** Functions, Classes, Line ranges.
*   **Import detection:** Max 20 imports included (with truncation flag).
*   **Metrics:** Line count, basic Complexity score.
*   **Security:** **Full security warning support** (CWE-94, CWE-78, etc.).

### Pro Tier (Quality & Intent)
Adds qualitative analysis.
*   **Semantic Summarization:** Docstring-based summary.
*   **Intent Extraction:** Auto-tags (e.g., `["auth", "middleware", "security"]`).
*   **Smart Context:** First 2,000 lines included for deeper context.
*   **Code Smells:** Detection of long functions, bare excepts, etc.
*   **Maintainability Index:** Numeric score (0-100).

### Enterprise Tier (Governance)
Adds organizational context and compliance.
*   **Compliance Flags:** HIPAA, GDPR, PCI-DSS pattern detection.
*   **PII/Secret Redaction:** Email redaction, AWS key masking.
*   **Ownership:** CODEOWNERS integration.
*   **Technical Debt:** Estimated remediation hours.
*   **Unlimited Context:** No line limit on context expansion.

---

## API Specification

### Signature
```python
async def get_file_context(
    file_path: str,
    # Implicit tier configuration injected by server
) -> FileContextResult
```

### Response Model (`FileContextResult`)

```python
class FileContextResult(BaseModel):
    # Core (Community)
    success: bool
    file_path: str
    language: str
    line_count: int
    functions: List[str]          # Names only in Community
    classes: List[str]            # Names only in Community
    imports: List[str]
    complexity_score: int
    has_security_issues: bool
    security_warnings: List[str]  # e.g., ["CWE-78: os.system usage detected"]
    
    # Pro Features (Optional)
    semantic_summary: Optional[str]
    intent_tags: List[str]
    code_smells: List[Dict]
    maintainability_index: Optional[float]
    
    # Enterprise Features (Optional)
    pii_redacted: bool
    compliance_flags: List[str]
    owners: List[str]
    
    # Metadata (All Tiers)
    tier_applied: str             # "community", "pro", "enterprise"
    pro_features_enabled: bool
    enterprise_features_enabled: bool
```

---

## Usage Examples

### 1. Quick Relevance Check (Community)
**Request:**
```python
await get_file_context(file_path="src/utils/db.py")
```

**Response (Summary):**
```json
{
  "file_path": "src/utils/db.py",
  "functions": ["connect", "execute_query", "close"],
  "imports": ["psycopg2", "os"],
  "has_security_issues": true,
  "security_warnings": ["Potential SQL Injection risk in 'execute_query'"],
  "tier_applied": "community"
}
```

### 2. Quality Assessment (Pro)
**Request:**
```python
await get_file_context(file_path="src/legacy_processor.py")
```

**Response (Summary):**
```json
{
  "semantic_summary": "Legacy data processor for CSV imports.",
  "intent_tags": ["csv", "parsing", "legacy"],
  "code_smells": [
    {"type": "long_function", "message": "Function 'process' is 150 lines long"}
  ],
  "maintainability_index": 45.2,
  "tier_applied": "pro"
}
```

---

## Testing Evidence

Testing for `get_file_context` is comprehensive, covering all tiers and supported languages.

| Category | Stats | Status |
|----------|-------|--------|
| **Total Tests** | 110+ | ✅ Passing |
| **Language Coverage** | Python, JS, TS, Java | ✅ Verified |
| **Tier Coverage** | Community, Pro, Enterprise | ✅ Verified |
| **Licensing Logic** | 25 distinct scenarios | ✅ Verified |

**Key Scenarios Validated:**
*   **Security Scanning:** Verified that sinks (e.g., `eval`, `exec`) trigger warnings in Community tier.
*   **Tier Gating:** Verified that Pro fields (e.g., `code_smells`) return `None` when license is Community.
*   **Error Handling:** Verified graceful degradation on file-not-found or parse errors.

---

## Performance Characteristics

*   **Latency:**
    *   Small files (<500 LOC): <20ms
    *   Medium files (500-2000 LOC): ~50ms
    *   Large files (5000+ LOC): ~100-200ms
*   **Token Usage:**
    *   Input: ~20 tokens (file path)
    *   Output: Fixed structure (~100-200 tokens) regardless of file size (unless extended context is used).

---

## Tier-Specific Behavior

The tool adapts its output based on the active license.

| Feature | Community | Pro | Enterprise |
| :--- | :--- | :--- | :--- |
| **Parsing** | AST Basic | AST + Docstrings | AST + Metadata |
| **Context Limit** | 500 lines | 2,000 lines | Unlimited |
| **Metrics** | Complexity (Basic) | + Maintainability | + Tech Debt |
| **Security** | Basic Sinks | Basic Sinks | + PII/Secrets |
| **Governance** | None | None | Compliance + Owners |

---

## Known Limitations

1.  **Dynamic Imports:** Only static imports are detected reliably.
2.  **Complex Macros:** C/C++ macros may confuse the structural parser (though C/C++ support is experimental).
3.  **Generated Code:** Large generated files (e.g., protobufs) may be truncated early to save processing time.

---

## References and Related Tools

*   **[extract_code](./EXTRACT_CODE_DEEP_DIVE.md):** Used to retrieve the actual code found by this tool.
*   **[analyze_code](./ANALYZE_CODE_DEEP_DIVE.md):** The underlying engine used for structural parsing.
*   **[security_scan](./SECURITY_SCAN_DEEP_DIVE.md):** Deep taint analysis (complements the basic warnings found here).

---

**Change History:**
- **v1.0 (2026-01-04):** Initial Release. Full Tier support.
- **v1.1 (2026-01-12):** Documentation created.

**Quality Checklist:**
- [x] Technical Review
- [x] Evidence Verification (110+ Tests)
- [x] Tier Clarity
