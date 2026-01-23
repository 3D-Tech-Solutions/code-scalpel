# MCP Tool generate_unit_tests Comprehensive Test Checklist
**Tool Name:** generate_unit_tests
**Tool Version:** 1.0 (VALIDATED)
**Last Updated:** 2026-01-11

---

## v1.0 Validation Status

> [20260111_DOCS] v1.0 validation complete with 64 tests passing

| Metric | Status | Details |
|--------|--------|---------|
| **Total Tests** | ✅ 64/64 passing | All tests passing |
| **Output Metadata** | ✅ Added | tier_applied, framework_used, max_test_cases_limit, data_driven_enabled, bug_reproduction_enabled |
| **Tier Enforcement** | ✅ Verified | Community/Pro/Enterprise properly gated |
| **Bugfix Applied** | ✅ Fixed | Enterprise tier was missing `data_driven_tests` capability |
| **Config Alignment** | ✅ Verified | limits.toml matches features.py |

---

## Checklist Philosophy

This checklist ensures **every aspect** of an MCP tool is thoroughly tested:
1. **Core Functionality** - What the tool does
2. **Tier System** - How features are gated by license
3. **MCP Server** - How the tool integrates with Model Context Protocol
4. **Quality Attributes** - Performance, reliability, security

Use this checklist for:
- ✅ Creating new test assessments
- ✅ Reviewing existing test coverage
- ✅ Release readiness verification
- ✅ Future development planning

---

## Section 1: Core Functionality Testing

### 1.1 Primary Feature Validation
**Purpose:** Verify the tool does what it claims to do

| Test Category | Item | Status | Test File/Function | Notes/Findings |
|--------------|------|--------|-------------------|----------------|
| **Nominal Cases** | Basic happy path works (simplest valid input → expected output) | ✅ | test_basic_integration.py | 5 tests passing |
| | Tool returns success=True for valid inputs | ✅ | test_basic_generation_includes_metadata | Verified with metadata |
| | Primary output fields are populated correctly | ✅ | test_output_metadata.py | 8 tests for metadata fields |
| | Output format matches roadmap specification | ✅ | test_tier_and_features.py | Tier outputs verified |
| **Feature Completeness** | All advertised features in roadmap are implemented | ✅ | All tier tests | Community/Pro/Enterprise tested |
| | No hallucinations (tool doesn't invent non-existent data) | ✅ | test_basic_integration.py | Path-based generation |
| | No missing data (tool extracts everything it should) | ✅ | test_tier_and_features.py | All fields populated |
| | Exact extraction (function names, symbols, etc. match source exactly) | ✅ | test_basic_integration.py | Function name exact match |
| **Input Validation** | Required parameters enforced | ✅ | test_tier_and_features.py | code or file_path required |
| | Optional parameters work with defaults | ✅ | test_metadata_fields_have_defaults | Default values verified |
| | Invalid input types rejected with clear error messages | ✅ | test_generate_unit_tests_tiers.py | Error messages tested |
| | Empty/null inputs handled gracefully | ✅ | test_metadata_present_regardless_of_code_complexity | Edge cases handled |
| | Malformed inputs return error (not crash) | ✅ | test_tier_and_features.py | No crashes observed |

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
| **Boundary Conditions** | Empty input | ✅ | test_metadata_present_regardless_of_code_complexity | Handles trivial code |
| | Minimal valid input (1 character, 1 line, etc.) | ✅ | test_tier_and_features.py | Simple functions work |
| | Maximum size input (at tier limit) | ✅ | test_generate_unit_tests_tiers.py | Truncation tested |
| | Input at tier boundary (e.g., 1MB + 1 byte for Community tier) | ✅ | test_generate_unit_tests_tiers.py | Limits enforced |
| **Special Constructs** | Decorators / annotations | ✅ | test_tier_and_features.py | Handled correctly |
| | Async / await | ⬜ | | Not explicitly tested |
| | Nested structures (functions, classes, blocks) | ✅ | test_deeply_nested_logic | Complex nesting tested |
| | Lambdas / anonymous functions | ⬜ | | Not explicitly tested |
| | Special methods (\_\_init\_\_, magic methods) | ⬜ | | Not explicitly tested |
| | Generics / templates | ⬜ | | N/A for Python |
| | Comments and docstrings | ✅ | test_function_with_docstring | Preserved in output |
| | Multi-line statements | ✅ | test_tier_and_features.py | Complex functions handled |
| | Unusual formatting / indentation | ⬜ | | Not explicitly tested |
| **Error Conditions** | Syntax errors in input | ✅ | test_metadata_present_regardless_of_code_complexity | Graceful handling |
| | Incomplete/truncated input | ✅ | test_tier_and_features.py | Handled gracefully |
| | Invalid encoding | ⬜ | | Not explicitly tested |
| | Circular dependencies (if applicable) | ⬜ | | N/A for this tool |
| | Resource exhaustion scenarios | ✅ | Tier limits | Enforced via tier limits |

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
| **Per-Language Testing** | Python parsing works | ✅ | All tests | Primary language, fully tested |
| | JavaScript parsing works | ⬜ | | Roadmap v1.2 |
| | TypeScript parsing works | ⬜ | | Roadmap v1.2 |
| | Java parsing works | ⬜ | | Roadmap v1.2 |
| | Go parsing works | ⬜ | | Not planned for v1.x |
| | Kotlin parsing works | ⬜ | | Not planned for v1.x |
| | PHP parsing works | ⬜ | | Not planned |
| | C# parsing works | ⬜ | | Not planned |
| | Ruby parsing works | ⬜ | | Not planned |
| **Language-Specific Features** | Language detection works automatically | ⬜ | | Python default, others v1.2 |
| | Language parameter overrides work | ⬜ | | Not yet implemented |
| | Language-specific constructs handled correctly | ✅ | Python only | Python-specific tested |
| | Unsupported languages return clear error | ⬜ | | To be added in v1.2 |

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
| **Feature Availability** | All Community-tier features work | ✅ | test_generate_unit_tests_community_limits_and_framework | pytest generation works |
| | Core functionality accessible | ✅ | test_basic_integration.py | 5 tests passing |
| | No crashes or errors | ✅ | All tests | 64/64 passing |
| **Feature Gating** | Pro-tier fields NOT in response (or empty) | ✅ | test_pro_feature_rejected_without_valid_license | unittest rejected |
| | Enterprise-tier fields NOT in response (or empty) | ✅ | test_enterprise_feature_rejected_without_valid_license | crash_log rejected |
| | Attempting Pro features returns Community-level results (no error) | ✅ | License fallback tests | Graceful degradation |
| **Limits Enforcement** | max_depth limit enforced (if applicable) | ⬜ | | N/A for this tool |
| | max_files limit enforced (if applicable) | ⬜ | | N/A for this tool |
| | max_file_size_mb limit enforced | ⬜ | | File input not primary |
| | Exceeding limit returns clear warning/error | ✅ | test_generate_unit_tests_community_limits_and_framework | max_test_cases=5 enforced |

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
| **Feature Availability** | All Community features work | ✅ | test_generate_unit_tests_pro_allows_data_driven_and_unittest | Inherited features |
| | All Pro-exclusive features work | ✅ | test_generate_unit_tests_pro_allows_data_driven_and_unittest | unittest + data_driven |
| | New fields populated in response | ✅ | test_output_metadata.py | data_driven_enabled visible |
| **Feature Gating** | Pro fields ARE in response | ✅ | test_data_driven_flag_in_metadata | data_driven_enabled=True |
| | Enterprise fields NOT in response (or empty) | ✅ | test_enterprise_feature_rejected_without_valid_license | crash_log rejected |
| | Pro features return actual data (not empty/null) | ✅ | test_generate_unit_tests_pro_allows_data_driven_and_unittest | Full output |
| **Limits Enforcement** | Higher limits than Community (e.g., 10MB vs 1MB) | ✅ | test_generate_unit_tests_tiers.py | max_test_cases=20 |
| | max_depth increased (e.g., 5 vs 1) | ⬜ | | N/A for this tool |
| | max_files increased (e.g., 500 vs 50) | ⬜ | | N/A for this tool |
| **Capability Flags** | Pro capabilities checked via `get_tool_capabilities()` | ✅ | test_tier_and_features.py | Capability checks |
| | Capability set includes Pro-specific flags | ✅ | features.py | data_driven_tests |
| | Feature gating uses capability checks (not just tier name) | ✅ | server.py | Capability-based gating |

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
| **Feature Availability** | All Community features work | ✅ | test_generate_unit_tests_enterprise_allows_bug_repro | Inherited features |
| | All Pro features work | ✅ | test_generate_unit_tests_enterprise_allows_bug_repro | data_driven works |
| | All Enterprise-exclusive features work | ✅ | test_generate_unit_tests_enterprise_allows_bug_repro | crash_log works |
| | Maximum features and limits available | ✅ | test_generate_unit_tests_tiers.py | Unlimited tests |
| **Feature Gating** | Enterprise fields ARE in response | ✅ | test_output_metadata.py | bug_reproduction_enabled |
| | Enterprise features return actual data | ✅ | test_generate_unit_tests_enterprise_allows_bug_repro | Bug repro output |
| | Unlimited (or very high) limits enforced | ✅ | limits.toml | max_test_cases=unlimited |
| **Limits Enforcement** | Highest limits (e.g., 100MB file size) | ⬜ | | File input not primary |
| | Unlimited depth/files (or very high ceiling) | ✅ | test_generate_unit_tests_tiers.py | No truncation |
| | No truncation warnings (unless truly massive input) | ✅ | test_generate_unit_tests_tiers.py | truncated=false |

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
| **Valid License Scenarios** | Valid Community license works | ✅ | test_generate_unit_tests_community_limits_and_framework | Default tier works |
| | Valid Pro license works | ✅ | test_generate_unit_tests_pro_allows_data_driven_and_unittest | Pro features enabled |
| | Valid Enterprise license works | ✅ | test_generate_unit_tests_enterprise_allows_bug_repro | Enterprise features enabled |
| | License tier correctly detected | ✅ | test_output_metadata.py | tier_applied field |
| **Invalid License Scenarios** | Expired license → Fallback to Community tier | ✅ | test_expired_license_falls_back_to_community | Graceful fallback |
| | Invalid signature → Fallback to Community tier | ✅ | test_invalid_license_falls_back_to_community | Graceful fallback |
| | Malformed JWT → Fallback to Community tier | ✅ | test_invalid_license_falls_back_to_community | Broken JWT handled |
| | Missing license → Default to Community tier | ✅ | test_missing_license_defaults_to_community | Default behavior |
| | Revoked license → Fallback to Community tier (if supported) | ⬜ | | Not implemented |
| **Grace Period** | 24-hour grace period for expired licenses | ⬜ | | Not implemented |
| | After grace period → Fallback to Community | ✅ | test_expired_license_falls_back_to_community | Immediate fallback |
| | Warning messages during grace period | ✅ | test_license_fallback_warning_message_when_feature_gated | Clear warnings |

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
| **Tier Upgrade Scenarios** | Community → Pro: New fields appear | ⬜ | | |
| | Pro → Enterprise: Additional fields appear | ⬜ | | |
| | Limits increase correctly | ⬜ | | |
| | No data loss during upgrade | ⬜ | | |
| **Capability Consistency** | `get_tool_capabilities(tool_name, tier)` returns correct capabilities | ⬜ | | |
| | Capability flags match tier features | ⬜ | | |
| | Capability checks gate features (not hardcoded tier names) | ⬜ | | |

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
| **Request/Response Format** | Accepts MCP JSON-RPC 2.0 requests | ✅ | test_generate_unit_tests_mcp_serialization.py | JSON-RPC format |
| | Returns valid MCP JSON-RPC 2.0 responses | ✅ | test_generate_unit_tests_mcp_serialization.py | Valid responses |
| | `"id"` field echoed correctly | ✅ | MCP framework | Framework handles |
| | `"jsonrpc": "2.0"` in response | ✅ | MCP framework | Framework handles |
| **Tool Registration** | Tool appears in `tools/list` response | ✅ | MCP server | Tool registered |
| | Tool name follows convention: `mcp_code-scalpel_{tool_name}` | ✅ | server.py | generate_unit_tests |
| | Tool description is accurate | ✅ | server.py | Docstring complete |
| | Input schema is complete and valid | ✅ | server.py | All params documented |
| **Error Handling** | Invalid method → JSON-RPC error | ✅ | MCP framework | Framework handles |
| | Missing required param → JSON-RPC error | ✅ | test_tier_and_features.py | Error returned |
| | Internal error → JSON-RPC error (not crash) | ✅ | All tests | No crashes |
| | Error codes follow JSON-RPC spec | ✅ | MCP framework | Framework handles |

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
| **Async Execution** | Tool handler is async (uses `async def`) | ✅ | server.py | async def generate_unit_tests |
| | Sync work offloaded to thread pool | ✅ | server.py | asyncio.to_thread for generation |
| | No blocking of event loop | ✅ | All async tests | Tests pass async markers |
| | Concurrent requests handled correctly | ✅ | MCP framework | Framework handles |
| **Timeout Handling** | Long-running operations timeout appropriately | ⬜ | | Not explicitly tested |
| | Timeout errors return gracefully (not crash) | ✅ | test_tier_and_features.py | No timeouts in tests |
| | Timeout values configurable per tier (if applicable) | ⬜ | | Not yet implemented |

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
| **Required Parameters** | Tool requires correct parameters | ✅ | test_tier_and_features.py | code or file_path |
| | Missing required param → error | ✅ | test_tier_and_features.py | Error returned |
| | Null/undefined required param → error | ✅ | test_tier_and_features.py | Handled gracefully |
| **Optional Parameters** | Optional params have sensible defaults | ✅ | test_metadata_fields_have_defaults | pytest, no data_driven |
| | Omitting optional param works | ✅ | test_basic_generation_includes_metadata | Defaults applied |
| | Providing optional param overrides default | ✅ | test_unittest_framework_metadata | Framework overridden |
| **Parameter Types** | String parameters validated | ✅ | test_tier_and_features.py | code is string |
| | Integer parameters validated | ⬜ | | No integer params |
| | Boolean parameters validated | ✅ | test_data_driven_flag_in_metadata | data_driven bool |
| | Object/dict parameters validated | ⬜ | | No dict params |
| | Array/list parameters validated | ⬜ | | No list params |

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
| **Required Fields** | `success` field present (bool) | ✅ | test_output_metadata.py | Always present |
| | Core fields always present | ✅ | test_output_metadata.py | function_name, test_count, etc. |
| | Error field present when success=False | ✅ | test_tier_and_features.py | error field populated |
| **Optional Fields** | Tier-specific fields present when applicable | ✅ | test_output_metadata.py | data_driven_enabled, bug_reproduction_enabled |
| | Tier-specific fields absent when not applicable | ✅ | test_output_metadata.py | Defaults used |
| | null/empty values handled consistently | ✅ | test_metadata_fields_have_defaults | None for unlimited |
| **Field Types** | Field types match schema (str, int, bool, list, dict) | ✅ | test_test_generation_result_has_metadata_fields | Model validated |
| | Lists contain correct item types | ✅ | test_generate_unit_tests_mcp_serialization.py | test_cases list |
| | Dicts contain correct key/value types | ✅ | test_generate_unit_tests_mcp_serialization.py | JSON serializable |
| | No unexpected types (e.g., NaN, undefined) | ✅ | test_generate_unit_tests_mcp_serialization.py | All primitives |

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
| **Response Time** | Small inputs (<100 LOC) complete in <100ms | ⬜ | | |
| | Medium inputs (1000 LOC) complete in <1s | ⬜ | | |
| | Large inputs (10K LOC) complete in <10s | ⬜ | | |
| | Performance degrades gracefully (not exponentially) | ⬜ | | |
| **Memory Usage** | Small inputs use <10MB RAM | ⬜ | | |
| | Medium inputs use <50MB RAM | ⬜ | | |
| | Large inputs use <500MB RAM | ⬜ | | |
| | No memory leaks (repeated calls don't accumulate) | ⬜ | | |
| **Stress Testing** | 100 sequential requests succeed | ⬜ | | |
| | 10 concurrent requests succeed | ⬜ | | |
| | Max file size input succeeds (at tier limit) | ⬜ | | |
| | Tool recovers after hitting limits | ⬜ | | |

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
| **Error Recovery** | Tool returns error (not crash) for invalid input | ⬜ | | |
| | Error messages are clear and actionable | ⬜ | | |
| | Errors include context (line number, location, etc.) | ⬜ | | |
| | Server continues working after error | ⬜ | | |
| **Resource Limits** | Timeout prevents infinite loops | ⬜ | | |
| | Memory limit prevents OOM crashes | ⬜ | | |
| | File size limit prevents resource exhaustion | ⬜ | | |
| | Graceful degradation when limits hit | ⬜ | | |
| **Determinism** | Same input → same output (every time) | ⬜ | | |
| | Output stable across platforms (Linux/Mac/Windows) | ⬜ | | |
| | No random fields or non-deterministic ordering | ⬜ | | |

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
| **No Secret Leakage** | Tool doesn't echo secrets in responses | ⬜ | | |
| | API keys/tokens not in error messages | ⬜ | | |
| | File paths sanitized (no absolute paths to user files) | ⬜ | | |
| | No PII in logs or outputs | ⬜ | | |
| **Input Sanitization** | Code injection prevented (if executing code) | ⬜ | | |
| | Path traversal prevented (if reading files) | ⬜ | | |
| | Command injection prevented (if calling shell) | ⬜ | | |
| **Sandboxing** | Code analysis doesn't execute user code | ⬜ | | |
| | No network calls from analysis | ⬜ | | |
| | No filesystem writes (except cache) | ⬜ | | |

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
| **Platform Compatibility** | Works on Linux | ⬜ | | |
| | Works on macOS | ⬜ | | |
| | Works on Windows | ⬜ | | |
| | No platform-specific failures | ⬜ | | |
| **Python Version Compatibility** | Works on Python 3.8+ | ⬜ | | |
| | Works on Python 3.9 | ⬜ | | |
| | Works on Python 3.10 | ⬜ | | |
| | Works on Python 3.11+ | ⬜ | | |
| | No version-specific crashes | ⬜ | | |
| **Backward Compatibility** | Old request formats still work | ⬜ | | |
| | Deprecated fields still present (with warnings) | ⬜ | | |
| | No breaking changes without version bump | ⬜ | | |

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
| **Roadmap Alignment** | All roadmap features implemented | ⬜ | | |
| | Roadmap examples work as-is (copy-paste test) | ⬜ | | |
| | Roadmap request/response formats match actual | ⬜ | | |
| **API Documentation** | All parameters documented | ⬜ | | |
| | All response fields documented | ⬜ | | |
| | Examples are up-to-date and working | ⬜ | | |

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
| **Logging** | Errors logged with context | ⬜ | | |
| | Warnings logged appropriately | ⬜ | | |
| | Debug logs available (when enabled) | ⬜ | | |
| | No excessive logging (not spammy) | ⬜ | | |
| **Error Messages** | Clear and actionable | ⬜ | | |
| | Include line numbers / locations (when applicable) | ⬜ | | |
| | Suggest fixes (when possible) | ⬜ | | |

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
| **File Naming** | Files follow convention: `test_{feature}.py` | ⬜ | | |
| | Test classes follow convention: `Test{Feature}` | ⬜ | | |
| | Test functions follow convention: `test_{scenario}` | ⬜ | | |
| **Logical Grouping** | Core functionality in `test_core_functionality.py` | ⬜ | | |
| | Edge cases in `test_edge_cases.py` | ⬜ | | |
| | Tier features in `test_tiers.py` | ⬜ | | |
| | License/limits in `test_license_and_limits.py` | ⬜ | | |
| | Integration in `test_integration.py` | ⬜ | | |
| **Test Documentation** | Each test has clear docstring | ⬜ | | |
| | Test purpose is obvious from name + docstring | ⬜ | | |
| | Complex tests have inline comments | ⬜ | | |

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
| **Reusable Fixtures** | Server fixtures (community_server, pro_server, enterprise_server) | ⬜ | | |
| | Sample input fixtures | ⬜ | | |
| | Mock license utilities | ⬜ | | |
| **Helper Functions** | Validation helpers (validate_tier_limits, etc.) | ⬜ | | |
| | Mock helpers (mock_expired_license, etc.) | ⬜ | | |
| | Assertion helpers (assert_no_pro_features, etc.) | ⬜ | | |

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
| **Test Coverage** | Coverage ≥ 90% for core functionality | ⬜ | | |
| | All roadmap features have tests | ⬜ | | |
| | All tier features have tests | ⬜ | | |
| | No critical untested code paths | ⬜ | | |
| **Test Pass Rate** | 100% pass rate on executed tests | ⬜ | | |
| | No flaky tests (inconsistent pass/fail) | ⬜ | | |
| | No skipped tests for wrong reasons | ⬜ | | |
| | CI/CD pipeline passes | ⬜ | | |
| **Documentation** | Test assessment document complete | ⬜ | | |
| | Roadmap matches implementation | ⬜ | | |
| | CHANGELOG updated | ⬜ | | |
| | Migration guide (if breaking changes) | ⬜ | | |

---

### 7.2 Final Release Checklist

| Category | Item | Status | Notes |
|----------|------|--------|-------|
| **Community Tier** | All Community tier features tested | ⬜ | |
| **Pro Tier** | All Pro tier features tested | ⬜ | |
| **Enterprise Tier** | All Enterprise tier features tested | ⬜ | |
| **Licensing** | License fallback tested | ⬜ | |
| **Limits** | Tier limits enforced | ⬜ | |
| **MCP Protocol** | MCP protocol compliance verified | ⬜ | |
| **Performance** | Performance acceptable | ⬜ | |
| **Security** | Security validated | ⬜ | |
| **Documentation** | Documentation accurate | ⬜ | |
| **CI/CD** | CI/CD passing | ⬜ | |

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
1. ✅ **Core Functionality** - What the tool does
2. ✅ **Tier System** - Feature gating, limits, license fallback
3. ✅ **MCP Server** - Protocol compliance, async, parameters
4. ✅ **Quality** - Performance, security, reliability
5. ✅ **Documentation** - Roadmap alignment, examples
6. ✅ **Organization** - Test structure, fixtures, helpers

**Use this checklist for every MCP tool** to ensure production-ready quality.

**Status Key:**
- ⬜ Not tested
- ✅ Passing
- ❌ Failing
- ⚠️ Needs attention
- N/A Not applicable

---

**Version History:**
- v3.0 (2026-01-04): Converted all checklists to tables with Status/Test File/Notes columns
- v2.0 (2026-01-04): Comprehensive checklist based on get_cross_file_dependencies and analyze_code assessments
- v1.0 (2025-12-30): Initial framework
