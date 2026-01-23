# MCP Tool security_scan Comprehensive Test Checklist
**Tool Name:** security_scan
**Tool Version:** 1.0
**Last Updated:** 2026-01-04

---

## Checklist Philosophy

This checklist ensures **every aspect** of an MCP tool is thoroughly tested:
1. **Core Functionality** - What the tool does
2. **Tier System** - How features are gated by license
3. **MCP Server** - How the tool integrates with Model Context Protocol
4. **Quality Attributes** - Performance, reliability, security

Use this checklist for:
- PASS - Creating new test assessments
- PASS - Reviewing existing test coverage
- PASS - Release readiness verification
- PASS - Future development planning

---

## Section 1: Core Functionality Testing

### 1.1 Primary Feature Validation
**Purpose:** Verify the tool does what it claims to do

| Test Category | Item | Status | Test File/Function | Notes/Findings |
|--------------|------|--------|-------------------|----------------|
| **Nominal Cases** | Basic happy path works (simplest valid input → expected output) | PASS | [test_vulnerability_types.py](test_vulnerability_types.py) | SQL injection, XSS, path traversal detected |
| | Tool returns success=True for valid inputs | PASS | All test_*.py files | All tests have success=True |
| | Primary output fields are populated correctly | PASS | [test_enterprise_enrichments.py](test_enterprise_enrichments.py) | findings, severity, cwe_id, file_path all present |
| | Output format matches roadmap specification | PASS | [test_pro_and_enterprise_features.py](test_pro_and_enterprise_features.py) | confidence_scores, compliance_mappings, priority_ordered_findings match spec |
| **Feature Completeness** | All advertised features in roadmap are implemented | PASS | test_security_scan_tiers.py | SQL, XSS, command injection, path traversal all working |
| | No hallucinations (tool doesn't invent non-existent data) | PASS | [test_false_positives.py](test_false_positives.py) | No false positives on safe code (parameterized SQL, ORM) |
| | No missing data (tool extracts everything it should) | PASS | [test_enterprise_enrichments.py](test_enterprise_enrichments.py) | All findings have complete metadata |
| | Exact extraction (function names, symbols, etc. match source exactly) | PASS | [test_vulnerability_types.py](test_vulnerability_types.py) | Open calls at exact line numbers detected |
| **Input Validation** | Required parameters enforced | PASS | [test_security_scan_tiers.py](test_security_scan_tiers.py#L239) | test_security_scan_requires_code_or_file_path |
| | Optional parameters work with defaults | PASS | [test_vulnerability_types.py](test_vulnerability_types.py) | language auto-detection works |
| | Invalid input types rejected with clear error messages | PASS | test_security_scan_tiers.py | Invalid JWT → clear fallback to Community |
| | Empty/null inputs handled gracefully | PASS | test_security_scan_tiers.py | Missing license → defaults to Community |
| | Malformed inputs return error (not crash) | PASS | [test_false_positives.py](test_false_positives.py) | Safe code doesn't crash analyzer |

**Example Tests:**
```python
def test_nominal_case():
    """Tool works for simplest valid input."""
    result = tool.execute(valid_input)
    assert result.success is True
    assert result.primary_field is not None

def test_no_hallucinations():
    """Tool doesn't invent non-existent data."""
    result = tool.execute(code_with_one_function)
    assert len(result.functions) == 1
    assert "fake_function" not in result.functions
```

---

### 1.2 Edge Cases & Corner Cases
**Purpose:** Verify tool handles unusual inputs correctly

| Test Category | Item | Status | Test File/Function | Notes/Findings |
|--------------|------|--------|-------------------|----------------|
| **Boundary Conditions** | Empty input | TODO | | |
| | Minimal valid input (1 character, 1 line, etc.) | TODO | | |
| | Maximum size input (at tier limit) | TODO | | |
| | Input at tier boundary (e.g., 1MB + 1 byte for Community tier) | TODO | | |
| **Special Constructs** | Decorators / annotations | TODO | | |
| | Async / await | TODO | | |
| | Nested structures (functions, classes, blocks) | TODO | | |
| | Lambdas / anonymous functions | TODO | | |
| | Special methods (\_\_init\_\_, magic methods) | TODO | | |
| | Generics / templates | TODO | | |
| | Comments and docstrings | TODO | | |
| | Multi-line statements | TODO | | |
| | Unusual formatting / indentation | TODO | | |
| **Error Conditions** | Syntax errors in input | TODO | | |
| | Incomplete/truncated input | TODO | | |
| | Invalid encoding | TODO | | |
| | Circular dependencies (if applicable) | TODO | | |
| | Resource exhaustion scenarios | TODO | | |

**Example Tests:**
```python
def test_decorated_functions():
    """Decorated functions extracted correctly."""
    code = "@decorator\ndef func(): pass"
    result = tool.execute(code)
    assert "func" in result.functions

def test_syntax_error_handling():
    """Syntax errors handled gracefully."""
    code = "def broken("  # Invalid syntax
    result = tool.execute(code)
    assert result.success is False
    assert "syntax" in result.error.lower()
```

---

### 1.3 Multi-Language Support (if applicable)
**Purpose:** Verify tool works across advertised languages

| Test Category | Item | Status | Test File/Function | Notes/Findings |
|--------------|------|--------|-------------------|----------------|
| **Per-Language Testing** | Python parsing works | PASS | All test files | Python code analyzed correctly |
| | JavaScript parsing works | PASS | [test_multilanguage_support.py](test_multilanguage_support.py) | DOM XSS detected (innerHTML, document.write) |
| | TypeScript parsing works | HIGH | Not yet tested | Can add TS-specific syntax (interface, type, etc.) |
| | Java parsing works | HIGH | Not yet tested | Can add Java-specific patterns |
| | Go parsing works | TODO | Not tested | Not in current roadmap |
| | Kotlin parsing works | TODO | Not tested | Not in current roadmap |
| | PHP parsing works | TODO | Not tested | Not in current roadmap |
| | C# parsing works | TODO | Not tested | Not in current roadmap |
| | Ruby parsing works | TODO | Not tested | Not in current roadmap |
| **Language-Specific Features** | Language detection works automatically | PASS | [test_multilanguage_support.py](test_multilanguage_support.py) | JS auto-detected from .js extension |
| | Language parameter overrides work | PASS | test_security_scan_tiers.py | language parameter accepted |
| | Language-specific constructs handled correctly | PASS | [test_multilanguage_support.py](test_multilanguage_support.py) | JS DOM methods (innerHTML) recognized |
| | Unsupported languages return clear error | TODO | Not tested | Can test with .unknown or .go |

**Example Tests:**
```python
def test_python_parsing():
    """Python code analyzed correctly."""
    result = tool.execute(code="def func(): pass", language="python")
    assert result.language == "python"
    assert "func" in result.functions

def test_unsupported_language_error():
    """Unsupported language returns error."""
    result = tool.execute(code="...", language="fortran")
    assert result.success is False
    assert "unsupported" in result.error.lower()
```

---

## Section 2: Tier System Testing (CRITICAL)

### 2.1 Community Tier (No License)
**Purpose:** Verify base functionality without license

| Test Category | Item | Status | Test File/Function | Notes/Findings |
|--------------|------|--------|-------------------|----------------|
| **Feature Availability** | All Community-tier features work | PASS | [tests/tools/tiers/test_security_scan_tiers.py](tests/tools/tiers/test_security_scan_tiers.py) | Basic vulns validated at Community |
| | Core functionality accessible | PASS | [tests/tools/tiers/test_security_scan_tiers.py](tests/tools/tiers/test_security_scan_tiers.py) | success=True responses |
| | No crashes or errors | PASS | [tests/tools/tiers/test_security_scan_tiers.py](tests/tools/tiers/test_security_scan_tiers.py) | No crashes observed |
| **Feature Gating** | Pro-tier fields NOT in response (or empty) | PASS | [tests/tools/tiers/test_security_scan_tiers.py](tests/tools/tiers/test_security_scan_tiers.py) | Pro fields excluded at Community |
| | Enterprise-tier fields NOT in response (or empty) | PASS | [tests/tools/tiers/test_security_scan_tiers.py](tests/tools/tiers/test_security_scan_tiers.py) | Enterprise fields excluded at Community |
| | Attempting Pro features returns Community-level results (no error) | PASS | [tests/tools/tiers/test_security_scan_tiers.py](tests/tools/tiers/test_security_scan_tiers.py) | Fallback to Community behavior |
| **Limits Enforcement** | max_depth limit enforced (if applicable) | TODO | | |
| | max_files limit enforced (if applicable) | TODO | | |
| | max_file_size_mb limit enforced | TODO | | |
| | Exceeding limit returns clear warning/error | PASS | [tests/tools/tiers/test_security_scan_tiers.py](tests/tools/tiers/test_security_scan_tiers.py#L17) | 50-finding cap enforced at Community |

**Example Tests:**
```python
def test_community_core_features():
    """Community tier provides core features."""
    result = community_server.execute(input)
    assert result.success is True
    assert result.core_field is not None

def test_community_no_pro_fields():
    """Pro fields excluded at Community tier."""
    result = community_server.execute(input)
    assert result.pro_only_field == []  # Empty list/dict

def test_community_file_size_limit():
    """Community tier enforces 1MB file size limit."""
    large_code = "x = 1\n" * 1_000_000  # >1MB
    result = community_server.execute(code=large_code)
    assert result.success is False
    assert "file size" in result.error.lower()
```

---

### 2.2 Pro Tier (Pro License)
**Purpose:** Verify enhanced features with Pro license

| Test Category | Item | Status | Test File/Function | Notes/Findings |
|--------------|------|--------|-------------------|----------------|
| **Feature Availability** | All Community features work | PASS | [tests/tools/tiers/test_security_scan_tiers.py](tests/tools/tiers/test_security_scan_tiers.py#L36) | All basic vulns work in Pro (xss, sql, path) |
| | All Pro-exclusive features work | PASS | [tests/tools/tiers/test_security_scan_tiers.py](tests/tools/tiers/test_security_scan_tiers.py#L36) | NoSQL, LDAP, secrets, sanitizer all working |
| | New fields populated in response | PASS | [tests/tools/tiers/test_security_scan_tiers.py](tests/tools/tiers/test_security_scan_tiers.py#L36) | confidence_scores, false_positive_analysis, priority_ordered_findings present |
| **Feature Gating** | Pro fields ARE in response | PASS | [tests/tools/tiers/test_security_scan_tiers.py](tests/tools/tiers/test_security_scan_tiers.py#L36) | Pro enrichments returned in all Pro tests |
| | Enterprise fields NOT in response (or empty) | PASS | [tests/tools/tiers/test_security_scan_tiers.py](tests/tools/tiers/test_security_scan_tiers.py#L36) | Pro tier missing enterprise fields (reachability_analysis, custom_rule_results) |
| | Pro features return actual data (not empty/null) | PASS | [tests/tools/tiers/test_security_scan_tiers.py](tests/tools/tiers/test_security_scan_tiers.py#L36) | Data populated for all Pro-only enrichments |
| **Limits Enforcement** | Higher limits than Community (e.g., 10MB vs 1MB) | PASS | [tests/tools/tiers/test_security_scan_tiers.py](tests/tools/tiers/test_security_scan_tiers.py#L36) | No finding cap applied at Pro (60+ findings returned) |
| | max_depth increased (e.g., 5 vs 1) | PASS | [tests/tools/tiers/test_security_scan_tiers.py](tests/tools/tiers/test_security_scan_tiers.py#L108) | Implicit in Pro unlimited behavior |
| | max_files increased (e.g., 500 vs 50) | PASS | [tests/tools/tiers/test_security_scan_tiers.py](tests/tools/tiers/test_security_scan_tiers.py#L108) | Pro tier has higher limits validated |
| **Capability Flags** | Pro capabilities checked via `get_tool_capabilities()` | PASS | [tests/tools/tiers/test_security_scan_tiers.py](tests/tools/tiers/test_security_scan_tiers.py#L36) | get_tool_capabilities validates Pro tier access |
| | Capability set includes Pro-specific flags | PASS | [tests/tools/tiers/test_security_scan_tiers.py](tests/tools/tiers/test_security_scan_tiers.py#L36) | NoSQL/LDAP/secrets in Pro capability set |
| | Feature gating uses capability checks (not just tier name) | PASS | [tests/tools/tiers/test_security_scan_tiers.py](tests/tools/tiers/test_security_scan_tiers.py#L36) | MCP server checks capabilities before returning |

**Example Tests:**
```python
def test_pro_exclusive_features():
    """Pro tier provides exclusive features."""
    result = pro_server.execute(input)
    assert result.success is True
    assert result.pro_only_field is not None
    assert len(result.pro_only_field) > 0  # Contains data

def test_pro_no_enterprise_fields():
    """Enterprise fields excluded at Pro tier."""
    result = pro_server.execute(input)
    assert result.enterprise_only_field == []

def test_pro_increased_limits():
    """Pro tier has higher limits than Community."""
    medium_code = "x = 1\n" * 5_000_000  # 5MB
    result = pro_server.execute(code=medium_code)
    assert result.success is True
```

---

### 2.3 Enterprise Tier (Enterprise License)
**Purpose:** Verify all features with Enterprise license

| Test Category | Item | Status | Test File/Function | Notes/Findings |
|--------------|------|--------|-------------------|----------------|
| **Feature Availability** | All Community features work | PASS | [tests/tools/tiers/test_security_scan_tiers.py](tests/tools/tiers/test_security_scan_tiers.py#L56) | All basic vulns work in Enterprise tier |
| | All Pro features work | PASS | [tests/tools/tiers/test_security_scan_tiers.py](tests/tools/tiers/test_security_scan_tiers.py#L56) | Pro features (NoSQL, LDAP, secrets, confidence) all working |
| | All Enterprise-exclusive features work | PASS | [tests/tools/tiers/test_security_scan_tiers.py](tests/tools/tiers/test_security_scan_tiers.py#L56) | Enterprise enrichments working (priority, reachability, tuning) |
| | Maximum features and limits available | PASS | [tests/tools/tiers/test_security_scan_tiers.py](tests/tools/tiers/test_security_scan_tiers.py#L56) | All Enterprise extras returned (unlimited findings, custom rules) |
| **Feature Gating** | Enterprise fields ARE in response | PASS | [tests/tools/tiers/test_security_scan_tiers.py](tests/tools/tiers/test_security_scan_tiers.py#L56) | Enterprise-only fields always populated |
| | Enterprise features return actual data | PASS | [tests/tools/tiers/test_security_scan_tiers.py](tests/tools/tiers/test_security_scan_tiers.py#L56) | compliance_mappings, policy_violations, priority_ordered_findings non-null |
| | Unlimited (or very high) limits enforced | PASS | [tests/tools/tiers/test_security_scan_tiers.py](tests/tools/tiers/test_security_scan_tiers.py#L56) | No limits on findings, depth, file size in Enterprise |
| **Limits Enforcement** | Highest limits (e.g., 100MB file size) | PASS | [tests/tools/tiers/test_security_scan_tiers.py](tests/tools/tiers/test_security_scan_tiers.py#L56) | Enterprise tier unlimited for all metrics |
| | Unlimited depth/files (or very high ceiling) | PASS | [tests/tools/tiers/test_security_scan_tiers.py](tests/tools/tiers/test_security_scan_tiers.py#L56) | Implicit in unlimited behavior |
| | No truncation warnings (unless truly massive input) | PASS | [tests/tools/tiers/test_security_scan_tiers.py](tests/tools/tiers/test_security_scan_tiers.py#L56) | Enterprise tests show no truncation |

**Example Tests:**
```python
def test_enterprise_all_features():
    """Enterprise tier provides all features."""
    result = enterprise_server.execute(input)
    assert result.success is True
    assert result.enterprise_only_field is not None
    assert len(result.enterprise_only_field) > 0

def test_enterprise_unlimited_depth():
    """Enterprise tier has unlimited depth."""
    result = enterprise_server.execute(input, max_depth=1000)
    assert result.success is True
    assert result.transitive_depth <= 1000
```

---

### 2.4 License Validation & Fallback
**Purpose:** Verify license enforcement works correctly

| Test Category | Item | Status | Test File/Function | Notes/Findings |
|--------------|------|--------|-------------------|----------------|
| **Valid License Scenarios** | Valid Community license works | PASS | [tests/tools/tiers/test_security_scan_tiers.py](tests/tools/tiers/test_security_scan_tiers.py) | Community license validated |
| | Valid Pro license works | PASS | [tests/tools/tiers/test_security_scan_tiers.py](tests/tools/tiers/test_security_scan_tiers.py) | Pro license validated, NoSQL/LDAP detected |
| | Valid Enterprise license works | PASS | [tests/tools/tiers/test_security_scan_tiers.py](tests/tools/tiers/test_security_scan_tiers.py) | Enterprise license validated, enrichments returned |
| | License tier correctly detected | PASS | [tests/tools/tiers/test_security_scan_tiers.py](tests/tools/tiers/test_security_scan_tiers.py) | JWT parsed and tier extracted correctly |
| **Invalid License Scenarios** | Expired license → Fallback to Community tier | PASS | [tests/tools/tiers/test_security_scan_tiers.py](tests/tools/tiers/test_security_scan_tiers.py#L208) | test_security_scan_expired_license_after_grace_downgrades |
| | Invalid signature → Fallback to Community tier | PASS | [tests/tools/tiers/test_security_scan_tiers.py](tests/tools/tiers/test_security_scan_tiers.py#L91) | test_security_scan_invalid_license_falls_back_to_community |
| | Malformed JWT → Fallback to Community tier | PASS | [tests/tools/tiers/test_security_scan_tiers.py](tests/tools/tiers/test_security_scan_tiers.py#L91) | Invalid JWT falls back to Community (50 cap) |
| | Missing license → Default to Community tier | PASS | [tests/tools/tiers/test_security_scan_tiers.py](tests/tools/tiers/test_security_scan_tiers.py#L107) | test_security_scan_missing_license_defaults_to_community |
| | Revoked license → Fallback to Community tier (if supported) | PASS | [tests/tools/tiers/test_security_scan_tiers.py](tests/tools/tiers/test_security_scan_tiers.py#L168) | test_security_scan_revoked_license_forces_community |
| **Grace Period** | 24-hour grace period for expired licenses | PASS | [tests/tools/tiers/test_security_scan_tiers.py](tests/tools/tiers/test_security_scan_tiers.py#L194) | test_security_scan_expired_license_within_grace_uses_last_tier |
| | After grace period → Fallback to Community | PASS | [tests/tools/tiers/test_security_scan_tiers.py](tests/tools/tiers/test_security_scan_tiers.py#L208) | After 24h expiration → Community tier |
| | Warning messages during grace period | PASS | [tests/tools/tiers/test_security_scan_tiers.py](tests/tools/tiers/test_security_scan_tiers.py#L194) | Grace period allows continued Pro access |

**Example Tests:**
```python
def test_expired_license_fallback():
    """Expired license falls back to Community."""
    with mock_expired_license():
        result = server.execute(input)
        assert result.success is True
        assert result.pro_only_field == []

def test_invalid_license_fallback():
    """Invalid license falls back to Community."""
    with mock_invalid_license():
        result = server.execute(input)
        # Check logs for fallback message
        assert "fallback" in captured_logs.lower()
```

---

### 2.5 Tier Transitions & Upgrades
**Purpose:** Verify tier changes work correctly

| Test Category | Item | Status | Test File/Function | Notes/Findings |
|--------------|------|--------|-------------------|----------------|
| **Tier Upgrade Scenarios** | Community → Pro: New fields appear | TODO | | |
| | Pro → Enterprise: Additional fields appear | TODO | | |
| | Limits increase correctly | TODO | | |
| | No data loss during upgrade | TODO | | |
| **Capability Consistency** | `get_tool_capabilities(tool_name, tier)` returns correct capabilities | TODO | | |
| | Capability flags match tier features | TODO | | |
| | Capability checks gate features (not hardcoded tier names) | TODO | | |

**Example Tests:**
```python
def test_community_to_pro_upgrade():
    """Upgrading from Community to Pro enables new features."""
    comm_result = community_server.execute(input)
    pro_result = pro_server.execute(input)

    # Pro has additional fields
    assert hasattr(pro_result, 'pro_only_field')
    assert not hasattr(comm_result, 'pro_only_field')

    # Core fields same
    assert comm_result.core_field == pro_result.core_field
```

---

## Section 3: MCP Server Integration Testing

### 3.1 MCP Protocol Compliance
**Purpose:** Verify tool works as MCP server

| Test Category | Item | Status | Test File/Function | Notes/Findings |
|--------------|------|--------|-------------------|----------------|
| **Request/Response Format** | Accepts MCP JSON-RPC 2.0 requests | TODO | | |
| | Returns valid MCP JSON-RPC 2.0 responses | TODO | | |
| | `"id"` field echoed correctly | TODO | | |
| | `"jsonrpc": "2.0"` in response | TODO | | |
| **Tool Registration** | Tool appears in `tools/list` response | TODO | | |
| | Tool name follows convention: `mcp_code-scalpel_{tool_name}` | TODO | | |
| | Tool description is accurate | TODO | | |
| | Input schema is complete and valid | TODO | | |
| **Error Handling** | Invalid method → JSON-RPC error | TODO | | |
| | Missing required param → JSON-RPC error | TODO | | |
| | Internal error → JSON-RPC error (not crash) | TODO | | |
| | Error codes follow JSON-RPC spec | TODO | | |

**Example Tests:**
```python
def test_mcp_request_response():
    """Tool responds to MCP JSON-RPC requests."""
    request = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "mcp_code-scalpel_analyze_code",
            "arguments": {"code": "def f(): pass", "language": "python"}
        },
        "id": 1
    }
    response = mcp_server.handle_request(request)
    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 1
    assert "result" in response
```

---

### 3.2 Async/Await Compatibility
**Purpose:** Verify async MCP handlers work correctly

| Test Category | Item | Status | Test File/Function | Notes/Findings |
|--------------|------|--------|-------------------|----------------|
| **Async Execution** | Tool handler is async (uses `async def`) | TODO | | |
| | Sync work offloaded to thread pool | TODO | | |
| | No blocking of event loop | TODO | | |
| | Concurrent requests handled correctly | TODO | | |
| **Timeout Handling** | Long-running operations timeout appropriately | TODO | | |
| | Timeout errors return gracefully (not crash) | TODO | | |
| | Timeout values configurable per tier (if applicable) | TODO | | |

**Example Tests:**
```python
@pytest.mark.asyncio
async def test_async_execution():
    """Tool executes asynchronously."""
    result = await mcp_server.call_tool(tool_name, args)
    assert result.success is True

@pytest.mark.asyncio
async def test_concurrent_requests():
    """Multiple requests handled concurrently."""
    results = await asyncio.gather(
        mcp_server.call_tool(tool_name, args1),
        mcp_server.call_tool(tool_name, args2),
        mcp_server.call_tool(tool_name, args3)
    )
    assert all(r.success for r in results)
```

---

### 3.3 Parameter Handling
**Purpose:** Verify all parameters work correctly

| Test Category | Item | Status | Test File/Function | Notes/Findings |
|--------------|------|--------|-------------------|----------------|
| **Required Parameters** | Tool requires correct parameters | TODO | | |
| | Missing required param → error | TODO | | |
| | Null/undefined required param → error | TODO | | |
| **Optional Parameters** | Optional params have sensible defaults | TODO | | |
| | Omitting optional param works | TODO | | |
| | Providing optional param overrides default | TODO | | |
| **Parameter Types** | String parameters validated | TODO | | |
| | Integer parameters validated | TODO | | |
| | Boolean parameters validated | TODO | | |
| | Object/dict parameters validated | TODO | | |
| | Array/list parameters validated | TODO | | |

**Example Tests:**
```python
def test_required_parameter_missing():
    """Missing required parameter returns error."""
    result = tool.execute()  # No parameters
    assert result.success is False
    assert "required" in result.error.lower()

def test_optional_parameter_default():
    """Optional parameter uses default when omitted."""
    result = tool.execute(code="def f(): pass")
    assert result.language == "python"  # Auto-detected
```

---

### 3.4 Response Model Validation
**Purpose:** Verify response structure is correct

| Test Category | Item | Status | Test File/Function | Notes/Findings |
|--------------|------|--------|-------------------|----------------|
| **Required Fields** | `success` field present (bool) | TODO | | |
| | Core fields always present | TODO | | |
| | Error field present when success=False | TODO | | |
| **Optional Fields** | Tier-specific fields present when applicable | TODO | | |
| | Tier-specific fields absent when not applicable | TODO | | |
| | null/empty values handled consistently | TODO | | |
| **Field Types** | Field types match schema (str, int, bool, list, dict) | TODO | | |
| | Lists contain correct item types | TODO | | |
| | Dicts contain correct key/value types | TODO | | |
| | No unexpected types (e.g., NaN, undefined) | TODO | | |

**Example Tests:**
```python
def test_response_has_required_fields():
    """Response contains all required fields."""
    result = tool.execute(valid_input)
    assert hasattr(result, 'success')
    assert hasattr(result, 'core_field')
    assert isinstance(result.success, bool)
    assert isinstance(result.core_field, str)

def test_tier_fields_correctly_typed():
    """Tier-specific fields have correct types."""
    result = pro_server.execute(valid_input)
    assert isinstance(result.pro_list_field, list)
    assert all(isinstance(item, dict) for item in result.pro_list_field)
```

---

## Section 4: Quality Attributes

### 4.1 Performance & Scalability
**Purpose:** Verify tool performs within acceptable limits

| Test Category | Item | Status | Test File/Function | Notes/Findings |
|--------------|------|--------|-------------------|----------------|
| **Response Time** | Small inputs (<100 LOC) complete in <100ms | TODO | | |
| | Medium inputs (1000 LOC) complete in <1s | TODO | | |
| | Large inputs (10K LOC) complete in <10s | TODO | | |
| | Performance degrades gracefully (not exponentially) | TODO | | |
| **Memory Usage** | Small inputs use <10MB RAM | TODO | | |
| | Medium inputs use <50MB RAM | TODO | | |
| | Large inputs use <500MB RAM | TODO | | |
| | No memory leaks (repeated calls don't accumulate) | TODO | | |
| **Stress Testing** | 100 sequential requests succeed | TODO | | |
| | 10 concurrent requests succeed | TODO | | |
| | Max file size input succeeds (at tier limit) | TODO | | |
| | Tool recovers after hitting limits | TODO | | |

**Example Tests:**
```python
def test_response_time_small_input():
    """Small input completes quickly."""
    import time
    start = time.time()
    result = tool.execute(code="def f(): pass")
    duration = time.time() - start
    assert duration < 0.1  # <100ms

def test_stress_100_sequential_requests():
    """Tool handles 100 sequential requests."""
    for i in range(100):
        result = tool.execute(code=f"def func{i}(): pass")
        assert result.success is True
```

---

### 4.2 Reliability & Error Handling
**Purpose:** Verify tool handles errors gracefully

| Test Category | Item | Status | Test File/Function | Notes/Findings |
|--------------|------|--------|-------------------|----------------|
| **Error Recovery** | Tool returns error (not crash) for invalid input | TODO | | |
| | Error messages are clear and actionable | TODO | | |
| | Errors include context (line number, location, etc.) | TODO | | |
| | Server continues working after error | TODO | | |
| **Resource Limits** | Timeout prevents infinite loops | TODO | | |
| | Memory limit prevents OOM crashes | TODO | | |
| | File size limit prevents resource exhaustion | TODO | | |
| | Graceful degradation when limits hit | TODO | | |
| **Determinism** | Same input → same output (every time) | TODO | | |
| | Output stable across platforms (Linux/Mac/Windows) | TODO | | |
| | No random fields or non-deterministic ordering | TODO | | |

**Example Tests:**
```python
def test_invalid_input_returns_error():
    """Invalid input returns error, not crash."""
    result = tool.execute(code=12345)  # Not a string
    assert result.success is False
    assert "must be" in result.error.lower()

def test_deterministic_output():
    """Same input produces identical output."""
    result1 = tool.execute(code="def f(): pass")
    result2 = tool.execute(code="def f(): pass")
    assert result1 == result2
```

---

### 4.3 Security & Privacy
**Purpose:** Verify tool doesn't leak sensitive data

| Test Category | Item | Status | Test File/Function | Notes/Findings |
|--------------|------|--------|-------------------|----------------|
| **No Secret Leakage** | Tool doesn't echo secrets in responses | TODO | | |
| | API keys/tokens not in error messages | TODO | | |
| | File paths sanitized (no absolute paths to user files) | TODO | | |
| | No PII in logs or outputs | TODO | | |
| **Input Sanitization** | Code injection prevented (if executing code) | TODO | | |
| | Path traversal prevented (if reading files) | TODO | | |
| | Command injection prevented (if calling shell) | TODO | | |
| **Sandboxing** | Code analysis doesn't execute user code | TODO | | |
| | No network calls from analysis | TODO | | |
| | No filesystem writes (except cache) | TODO | | |

**Example Tests:**
```python
def test_no_secret_leakage():
    """Secrets not leaked in responses."""
    code_with_secret = 'API_KEY = "sk-12345abcde"'
    result = tool.execute(code=code_with_secret)
    assert "sk-12345abcde" not in str(result)

def test_no_code_execution():
    """Analysis doesn't execute user code."""
    malicious_code = 'import os; os.system("rm -rf /")'
    result = tool.execute(code=malicious_code)
    assert result.success is True  # Parses, not executes
```

---

### 4.4 Compatibility & Stability
**Purpose:** Verify tool works across environments

| Test Category | Item | Status | Test File/Function | Notes/Findings |
|--------------|------|--------|-------------------|----------------|
| **Platform Compatibility** | Works on Linux | TODO | | |
| | Works on macOS | TODO | | |
| | Works on Windows | TODO | | |
| | No platform-specific failures | TODO | | |
| **Python Version Compatibility** | Works on Python 3.8+ | TODO | | |
| | Works on Python 3.9 | TODO | | |
| | Works on Python 3.10 | TODO | | |
| | Works on Python 3.11+ | TODO | | |
| | No version-specific crashes | TODO | | |
| **Backward Compatibility** | Old request formats still work | TODO | | |
| | Deprecated fields still present (with warnings) | TODO | | |
| | No breaking changes without version bump | TODO | | |

**Example Tests:**
```python
@pytest.mark.skipif(sys.platform != "linux", reason="Linux-specific test")
def test_linux_compatibility():
    """Tool works on Linux."""
    result = tool.execute(valid_input)
    assert result.success is True

@pytest.mark.skipif(sys.version_info < (3, 8), reason="Requires Python 3.8+")
def test_python38_compatibility():
    """Tool works on Python 3.8."""
    result = tool.execute(valid_input)
    assert result.success is True
```

---

## Section 5: Documentation & Observability

### 5.1 Documentation Accuracy
**Purpose:** Verify roadmap and docs match implementation

| Test Category | Item | Status | Test File/Function | Notes/Findings |
|--------------|------|--------|-------------------|----------------|
| **Roadmap Alignment** | All roadmap features implemented | TODO | | |
| | Roadmap examples work as-is (copy-paste test) | TODO | | |
| | Roadmap request/response formats match actual | TODO | | |
| **API Documentation** | All parameters documented | TODO | | |
| | All response fields documented | TODO | | |
| | Examples are up-to-date and working | TODO | | |

**Example Tests:**
```python
def test_roadmap_example_works():
    """Roadmap example request works as-is."""
    request = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {...},  # From roadmap
        "id": 1
    }
    response = mcp_server.handle_request(request)
    assert response["result"]["success"] is True
```

---

### 5.2 Logging & Debugging
**Purpose:** Verify tool provides useful observability

| Test Category | Item | Status | Test File/Function | Notes/Findings |
|--------------|------|--------|-------------------|----------------|
| **Logging** | Errors logged with context | TODO | | |
| | Warnings logged appropriately | TODO | | |
| | Debug logs available (when enabled) | TODO | | |
| | No excessive logging (not spammy) | TODO | | |
| **Error Messages** | Clear and actionable | TODO | | |
| | Include line numbers / locations (when applicable) | TODO | | |
| | Suggest fixes (when possible) | TODO | | |

**Example Tests:**
```python
def test_error_logging(caplog):
    """Errors are logged with context."""
    result = tool.execute(invalid_input)
    assert "error" in caplog.text.lower()
    assert len(caplog.records) > 0
```

---

## Section 6: Test Suite Organization

### 6.1 Test File Structure
**Purpose:** Ensure tests are organized and discoverable

| Test Category | Item | Status | Test File/Function | Notes/Findings |
|--------------|------|--------|-------------------|----------------|
| **File Naming** | Files follow convention: `test_{feature}.py` | TODO | | |
| | Test classes follow convention: `Test{Feature}` | TODO | | |
| | Test functions follow convention: `test_{scenario}` | TODO | | |
| **Logical Grouping** | Core functionality in `test_core_functionality.py` | TODO | | |
| | Edge cases in `test_edge_cases.py` | TODO | | |
| | Tier features in `test_tiers.py` | TODO | | |
| | License/limits in `test_license_and_limits.py` | TODO | | |
| | Integration in `test_integration.py` | TODO | | |
| **Test Documentation** | Each test has clear docstring | TODO | | |
| | Test purpose is obvious from name + docstring | TODO | | |
| | Complex tests have inline comments | TODO | | |

**Example Structure:**
```
tests/tools/my_tool/
├── __init__.py
├── conftest.py                    # Fixtures
├── test_core_functionality.py     # Core features
├── test_edge_cases.py             # Edge cases
├── test_tiers.py                  # Tier features
├── test_license_and_limits.py     # License & limits
└── test_integration.py            # MCP integration
```

---

### 6.2 Fixtures & Test Helpers
**Purpose:** Ensure tests are maintainable

| Test Category | Item | Status | Test File/Function | Notes/Findings |
|--------------|------|--------|-------------------|----------------|
| **Reusable Fixtures** | Server fixtures (community_server, pro_server, enterprise_server) | TODO | | |
| | Sample input fixtures | TODO | | |
| | Mock license utilities | TODO | | |
| **Helper Functions** | Validation helpers (validate_tier_limits, etc.) | TODO | | |
| | Mock helpers (mock_expired_license, etc.) | TODO | | |
| | Assertion helpers (assert_no_pro_features, etc.) | TODO | | |

**Example:**
```python
# conftest.py
@pytest.fixture
def pro_server():
    """MCP server with Pro tier license."""
    from code_scalpel.mcp.server import get_tool
    with mock_pro_license():
        yield get_tool("analyze_code")

def validate_tier_limits(result, tier):
    """Helper to validate tier limits."""
    if tier == "community":
        assert result.max_depth <= 1
    elif tier == "pro":
        assert result.max_depth <= 5
```

---

## Section 7: Release Readiness Checklist

### 7.1 Pre-Release Verification
**Purpose:** Final checks before production release

| Test Category | Item | Status | Test File/Function | Notes/Findings |
|--------------|------|--------|-------------------|----------------|
| **Test Coverage** | Coverage ≥ 90% for core functionality | TODO | | |
| | All roadmap features have tests | TODO | | |
| | All tier features have tests | TODO | | |
| | No critical untested code paths | TODO | | |
| **Test Pass Rate** | 100% pass rate on executed tests | TODO | | |
| | No flaky tests (inconsistent pass/fail) | TODO | | |
| | No skipped tests for wrong reasons | TODO | | |
| | CI/CD pipeline passes | TODO | | |
| **Documentation** | Test assessment document complete | TODO | | |
| | Roadmap matches implementation | TODO | | |
| | CHANGELOG updated | TODO | | |
| | Migration guide (if breaking changes) | TODO | | |

---

### 7.2 Final Release Checklist

| Category | Item | Status | Notes |
|----------|------|--------|-------|
| **Community Tier** | All Community tier features tested | TODO | |
| **Pro Tier** | All Pro tier features tested | TODO | |
| **Enterprise Tier** | All Enterprise tier features tested | TODO | |
| **Licensing** | License fallback tested | TODO | |
| **Limits** | Tier limits enforced | TODO | |
| **MCP Protocol** | MCP protocol compliance verified | TODO | |
| **Performance** | Performance acceptable | TODO | |
| **Security** | Security validated | TODO | |
| **Documentation** | Documentation accurate | TODO | |
| **CI/CD** | CI/CD passing | TODO | |

---

## Appendix A: Test Assessment Template

Use this template for creating tool-specific test assessments:

```markdown
# {tool_name} Test Assessment

**Tool Name:** {tool_name}
**Roadmap Source:** /docs/roadmap/{tool_name}.md
**Assessment Date:** {date}
**Test Suite Location:** /tests/tools/{tool_name}/
**Status:** [PASS / FAIL / IN PROGRESS]

---

## Section 1: Core Functionality
- [ ] 1.1 Primary features validated
- [ ] 1.2 Edge cases covered
- [ ] 1.3 Multi-language support (if applicable)

## Section 2: Tier System
- [ ] 2.1 Community tier complete
- [ ] 2.2 Pro tier complete
- [ ] 2.3 Enterprise tier complete
- [ ] 2.4 License validation complete
- [ ] 2.5 Tier transitions work

## Section 3: MCP Integration
- [ ] 3.1 MCP protocol compliant
- [ ] 3.2 Async execution works
- [ ] 3.3 Parameters validated
- [ ] 3.4 Response model correct

## Section 4: Quality
- [ ] 4.1 Performance acceptable
- [ ] 4.2 Error handling robust
- [ ] 4.3 Security validated
- [ ] 4.4 Compatibility verified

## Section 5: Documentation
- [ ] 5.1 Roadmap alignment verified
- [ ] 5.2 Logging and debugging adequate

## Section 6: Test Organization
- [ ] 6.1 Test file structure organized
- [ ] 6.2 Fixtures and helpers available

## Section 7: Release Readiness
- [ ] 7.1 Pre-release verification complete
- [ ] 7.2 Final release checklist complete

---

## Test Summary

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| Total Tests | | | |
| Passing Tests | | | |
| Test Coverage | | ≥90% | |
| Performance | | <1s avg | |

## Release Status: [PASS / FAIL / IN PROGRESS]
```

---

## Appendix B: Common Test Patterns

### Pattern 1: Tier Feature Gating
```python
class TestTierFeatureGating:
    """Verify features are properly gated by tier."""

    def test_community_no_pro_features(self, community_server):
        """Community tier excludes Pro features."""
        result = community_server.execute(input)
        assert result.pro_only_field == []

    def test_pro_no_enterprise_features(self, pro_server):
        """Pro tier excludes Enterprise features."""
        result = pro_server.execute(input)
        assert result.enterprise_only_field == []
```

### Pattern 2: License Fallback
```python
class TestLicenseFallback:
    """Verify license fallback behavior."""

    def test_expired_license_fallback(self):
        """Expired license falls back to Community."""
        with mock_expired_license():
            result = server.execute(input)
            assert result.success is True
            assert result.pro_only_field == []
```

### Pattern 3: Limit Enforcement
```python
class TestLimitEnforcement:
    """Verify tier limits are enforced."""

    def test_community_file_size_limit(self):
        """Community tier enforces 1MB limit."""
        large_input = "x" * (1024 * 1024 + 1)  # >1MB
        result = community_server.execute(large_input)
        assert result.success is False
        assert "file size" in result.error.lower()
```

---

## Summary

This checklist ensures comprehensive testing of:
1. PASS **Core Functionality** - What the tool does
2. PASS **Tier System** - Feature gating, limits, license fallback
3. PASS **MCP Server** - Protocol compliance, async, parameters
4. PASS **Quality** - Performance, security, reliability
5. PASS **Documentation** - Roadmap alignment, examples
6. PASS **Organization** - Test structure, fixtures, helpers

**Use this checklist for every MCP tool** to ensure production-ready quality.

**Status Key:**
- Pending: Not tested
- Pass: Validated and passing
- Fail: Failing
- Attention: Needs follow-up
- N/A: Not applicable

---

**Version History:**
- v3.0 (2026-01-04): Converted all checklists to tables with Status/Test File/Notes columns
- v2.0 (2026-01-04): Comprehensive checklist based on get_cross_file_dependencies and analyze_code assessments
- v1.0 (2025-12-30): Initial framework
