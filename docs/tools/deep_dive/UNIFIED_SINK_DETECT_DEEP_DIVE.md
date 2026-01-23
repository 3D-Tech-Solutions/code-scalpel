# unified_sink_detect - Deep Dive Documentation

**Document Type:** Tool Deep Dive Reference  
**Tool Name:** unified_sink_detect  
**Status:** Live (v1.0)  
**Last Updated:** 2026-01-12  
**Tier Availability:** Community (Limited), Pro (Unlimited + Context), Enterprise (Full Risk Suite)

## What is this tool?
`unified_sink_detect` provides a polyglot approach to detecting dangerous "sinks"—functions where untrusted data execution leads to vulnerability exploitations (e.g., `eval`, `exec`, `innerHTML`, `Runtime.exec`). Unlike traditional grep-based searching, this tool applies confidence scoring, CWE mapping, and context-aware analysis to reduce false positives.

**Key capabilities:**
- **Polyglot Parsing:** Native support for Python, JavaScript, TypeScript, and Java.
- **Safety Primitives:** Identifies raw dangerous functions regardless of framework abstraction.
- **Compliance Mapping:** Automatically tags findings with CWE and OWASP identifiers.
- **Tiered Analysis:** Scales from basic signature matching (Community) to context-aware validation (Pro) and risk assessment (Enterprise).

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

## Executive Summary
`unified_sink_detect` is the foundational security scanner in the Code Scalpel suite. It serves as the primary mechanism for identifying "sinks"—points in code where data is executed, rendered, or interpreted.

By extracting these sinks with high precision, the tool enables downstream agents to focus their expensive symbolic execution and taint analysis on the code paths that actually matter. It is designed to be **fast** (AST/regex hybrid), **accurate** (confidence scoring), and **comprehensive** (covers 10+ vulnerability categories including SQLi, XSS, and RCE).

The tool operates on a "Safety First" principle: it assumes code is vulnerable until proven safe, flagging high-risk patterns for review while filtering out obvious noise via its confidence engine.

## Technical Overview
The tool functions as a high-performance polyglot analyzer that normalizes security findings across different programming languages into a single unified schema.

### Core Components
1.  **Language Parsers**: Uses language-specific processing (AST for Python/JS, tailored Regex for Java) to identify function calls and assignments.
2.  **Sink Database**: A curated library of over 500 dangerous function signatures mapped to CWE IDs (e.g., `CWE-78` for Command Injection).
3.  **Confidence Engine**: Assigns scores (0.0 - 1.0) based on signal strength.
    *   **High (0.9-1.0)**: Unambiguous sinks (e.g., `eval(user_input)`).
    *   **Medium (0.6-0.8)**: Framework calls that might be safe depending on config.
    *   **Low (0.0-0.5)**: Heuristic matches requiring manual review.
4.  **Tier Controller**: Enforces limits on sink counts and capabilities (e.g., masking Enterprise risk scores for Community users).

### Supported Languages
| Language | Analysis Method | Key Sinks Detected |
| :--- | :--- | :--- |
| **Python** | AST + Regex | `eval`, `exec`, `subprocess.call`, `sqlite3.execute` |
| **JavaScript** | AST (Babel-like) | `eval`, `document.write`, `child_process.exec` |
| **TypeScript** | AST | `innerHTML`, `dangerouslySetInnerHTML`, `exec` |
| **Java** | Regex / Tokenizer | `Runtime.getRuntime().exec`, `ProcessBuilder` |

## Features and Capabilities

### 1. Unified Sinks Database
Centralized definition of dangerous functions across languages, mapped to industry standards.
-   **SQL Injection (SQLi)**: `cursor.execute`, `RAW()`, `Query()`
-   **Cross-Site Scripting (XSS)**: `innerHTML`, `outerHTML`, `document.write`
-   **Remote Code Execution (RCE)**: `eval`, `exec`, `os.system`
-   **Path Traversal**: `open()`, `File()`, `FileReader`

### 2. Tiered Capability Matrix

#### Community Tier (Free)
Designed for individual developers and small verification tasks.
-   **Limit**: Max **50** detected sinks per scan.
-   **Detection**: Basic signature matching.
-   **Output**: Standard list of sinks with file/line locations.
-   **License Enforcement**: Downgrades gracefully if license is invalid/expired.

#### Pro Tier (Paid/Licensed)
For professional development and comprehensive audits.
-   **Limit**: **Unlimited** sinks.
-   **Context-Aware Analysis**: Checks surrounding code to rule out safe usages (e.g., hardcoded strings passed to `eval`).
-   **Advanced Confidence Scoring**: Granular scores based on variable provenance (distinguishes literal vs. variable).
-   **Framework Support**: Deeper understanding of patterns in Flask, Django, Express, and Spring.

#### Enterprise Tier (Corporate)
For large-scale compliance and automated governance.
-   **Features**: Includes all Pro features.
-   **Risk Scoring**: Assigns severity levels (Critical, High, Medium, Low) to findings.
-   **Compliance Mapping**: Maps sinks to specific regulation violations (GDPR, PCI-DSS).
-   **Remediation Advice**: Provides actionable fix suggestions for detected vulnerabilities.

## API Specification

The tool is exposed via `mcp_code-scalpel_unified_sink_detect`.

### Request Schema
```python
class UnifiedSinkDetectRequest(BaseModel):
    code: str              # Source code to analyze
    language: str          # 'python', 'javascript', 'typescript', 'java'
    min_confidence: float = 0.5  # Filter threshold (default: 0.5)
```

### Response Schema
```python
class UnifiedSinkResult(BaseModel):
    sinks: List[SinkInfo]
    sink_count: int
    coverage: Dict[str, bool]  # Maps sink categories to detection status
    language: str

class SinkInfo(BaseModel):
    name: str           # Function name (e.g., 'eval')
    line: int           # Line number (1-based)
    cwe: str            # CWE ID (e.g., 'CWE-94')
    confidence: float   # 0.0 to 1.0
    category: str       # OWASP Category (e.g., 'A03:2021-Injection')
    
    # Enterprise Fields (Only populated in Enterprise Tier)
    risk_score: Optional[int]
    remediation_suggestion: Optional[str]
    compliance_violation: Optional[str]
```

## Usage Examples

### 1. Python SQL Injection Detection
detecting a raw SQL execution pattern.

**Request:**
```python
await unified_sink_detect(
    code="""
    query = "SELECT * FROM users WHERE id = " + user_input
    cursor.execute(query)
    """,
    language="python",
    min_confidence=0.7
)
```

**Response:**
```json
{
  "sinks": [
    {
      "name": "cursor.execute",
      "line": 3,
      "cwe": "CWE-89",
      "confidence": 0.95,
      "category": "A03:2021-Injection"
    }
  ],
  "sink_count": 1,
  "coverage": { "sql_injection": true, "xss": false },
  "language": "python"
}
```

### 2. JavaScript XSS Detection
Detecting unsafe DOM manipulation.

**Request:**
```python
await unified_sink_detect(
    code="document.getElementById('app').innerHTML = userInput;",
    language="javascript"
)
```

### 3. Tier Limit Behavior (Community)
If a file contains 100 sinks, a Community user will see:
```json
{
  "sinks": [ ... 50 items ... ],
  "sink_count": 50,
  "truncated": true,
  "warning": "Free tier limit reached. Only first 50 sinks shown."
}
```

## Architecture and Implementation

### Modular Design
The tool is built on a plugin-based architecture where each language support is a separate module implementing a common `SinkDetector` interface.

1.  **Frontend (MCP Interface)**: Handles request validation, tier enforcement, and response formatting.
2.  **Orchestrator**: Routes the code to the appropriate language parser based on the `language` parameter.
3.  **Detectors**:
    *   `PythonDetector`: Uses Python's native `ast` module.
    *   `JSDetector`: Uses regex and tokenization (migrating to AST).
    *   `JavaDetector`: Uses advanced pattern matching.
4.  **Normalizer**: Converts language-specific findings into the unified `SinkInfo` model, enriching them with CWE and OWASP metadata.

### Confidence Scoring Logic
*   **1.0 (Certain)**: Direct usage of a notorious sink with evident dynamic arguments (e.g., `eval(foo)`).
*   **0.8 (Likely)**: Dangerous function called with a variable, but function name might be overloaded (e.g., `execute(query)`).
*   **0.5 (Possible)**: Function matches a sink name but usage is ambiguous or arguments appear static/safe.
*   **0.0 (Safe)**: Hardcoded/constant values passed to dangerous functions (filtered out by default).

## Testing Evidence
As of January 10, 2026 (v1.0), the tool is validated by a robust test suite:

*   **Total Tests**: 88 dedicated tests (551 in full suite).
*   **Coverage**:
    *   ✅ **Python**: 20+ scenarios (SQLAlchemy, standard lib).
    *   ✅ **JavaScript/TypeScript**: 16+ scenarios (DOM XSS, Node.js RCE).
    *   ✅ **Java**: 5+ scenarios (Runtime, ProcessBuilder).
*   **Tier Enforcement**: 7 specialized tests verifying limits (50 sinks) and license fallbacks (Pro → Community).
*   **Enterprise Features**: Verified schema enrichment (risk scores, remediation) for Enterprise licenses.

## Performance Characteristics
*   **Speed**: Optimized for rapid scanning. AST parsing for Python/JS is sub-millisecond for typical file sizes.
*   **Memory**: Stateless operation. Memory usage scales linearly with the size of the input code string.
*   **Scalability**: Tier limits prevent abuse in the Community edition, while Enterprise edition supports batch processing of massive files.

## Security Considerations
*   **Input Sanitization**: The tool parses untrusted code. It relies on robust standard library parsers (`ast`) which are designed to handle malformed code safely without executing it.
*   **No Execution**: This is a *static* analysis tool. It **never** executes the provided code, eliminating RCE risks during analysis.
*   **Fail-Safe**: If a parser crashes on invalid syntax, the tool catches the exception and returns an empty sink list with an error flag, ensuring service stability.

## Integration Patterns
*   **Pre-Commit Hook**: Run fast scans on changed files to block obvious `eval()` or `debug` statements.
*   **CI/CD Pipeline**: Integrate as a blocking step for high-severity sinks (Confidence > 0.9).
*   **Agent Workflow**: Use as the "eyes" for a remediation agent—first find the sinks, then feed locations to `extract_code` for fixing.

## Tier-Specific Behavior

| Feature | Community | Pro | Enterprise |
| :--- | :--- | :--- | :--- |
| **Sink Limit** | 50 per scan | Unlimited | Unlimited |
| **Analysis Depth** | Regex/Basic AST | Context-Aware | Context-Aware |
| **Risk Scoring** | ❌ (Hidden) | ❌ (Hidden) | ✅ Visible |
| **Compliance** | ❌ | ❌ | ✅ Included |
| **Remediation** | ❌ | ❌ | ✅ Included |

**License Fallback**: If a Pro/Enterprise license expires or is invalid, the tool automatically downgrades to Community mode (50 sink limit) to ensure business continuity while enforcing commercial terms.

## Known Limitations
*   **Framework Blindness (v1.0)**: Supports raw language constructs well, but may miss high-level framework sinks (e.g., specific Spring Boot sanitization annotations) until v1.0.0.
*   **Data Flow**: Does not perform full Taint Analysis (tracing data from source to sink). It only identifies the *sink* itself. Use `cross_file_security_scan` for full flow analysis.
*   **Obfuscation**: Heavily obfuscated code (packed JS, encoded Python) will likely bypass detection.

## Roadmap and Future Plans
*   **v1.0.0**: Framework-specific sink definitions (Django, Flask, Spring, Express).
*   **v1.0.0**: Custom sink definitions (User-defined regex/AST patterns).
*   **v1.0.0**: Organization-specific policies (Allow/Deny lists).
*   **v1.0.0**: Historical sink tracking (Dashboarding trends over time).

## Troubleshooting

### Issue: "No sinks found in obviously vulnerable code"
*   **Cause**: `min_confidence` might be set too high.
*   **Fix**: Lower `min_confidence` to 0.1 or 0.0 to see all potential matches, then filter manually.
*   **Cause**: Code might be using a framework wrapper not yet in the default list.

### Issue: "Response truncated"
*   **Cause**: Community tier limit (50 sinks) exceeded.
*   **Fix**: Upgrade license or scan smaller code chunks.

## References and Related Tools
*   **CWE Top 25**: [https://cwe.mitre.org/top25/](https://cwe.mitre.org/top25/)
*   **OWASP Top 10**: [https://owasp.org/www-project-top-ten/](https://owasp.org/www-project-top-ten/)
*   **Related Tool**: `cross_file_security_scan` (Connects sinks to sources).
*   **Related Tool**: `type_evaporation_scan` (Detects type-safety gaps).

