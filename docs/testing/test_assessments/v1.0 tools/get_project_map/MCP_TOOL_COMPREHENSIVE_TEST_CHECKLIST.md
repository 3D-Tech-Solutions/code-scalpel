# MCP Tool get_project_map Comprehensive Test Checklist
**Tool Name:** get_project_map
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
| **Nominal Cases** | Basic happy path works (simplest valid input → expected output) | ⬜ | | |
| | Tool returns success=True for valid inputs | ⬜ | | |
| | Primary output fields are populated correctly | ⬜ | | |
| | Output format matches roadmap specification | ⬜ | | |
| **Feature Completeness** | All advertised features in roadmap are implemented | ⬜ | | |
| | No hallucinations (tool doesn't invent non-existent data) | ⬜ | | |
| | No missing data (tool extracts everything it should) | ⬜ | | |
| | Exact extraction (function names, symbols, etc. match source exactly) | ⬜ | | |
| **Input Validation** | Required parameters enforced | ⬜ | | |
| | Optional parameters work with defaults | ⬜ | | |
| | Invalid input types rejected with clear error messages | ⬜ | | |
| | Empty/null inputs handled gracefully | ⬜ | | |
| | Malformed inputs return error (not crash) | ⬜ | | |

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
| **Boundary Conditions** | Empty input | ⬜ | | |
| | Minimal valid input (1 character, 1 line, etc.) | ⬜ | | |
| | Maximum size input (at tier limit) | ⬜ | | |
| | Input at tier boundary (e.g., 1MB + 1 byte for Community tier) | ⬜ | | |
| **Special Constructs** | Decorators / annotations | ⬜ | | |
| | Async / await | ⬜ | | |
| | Nested structures (functions, classes, blocks) | ⬜ | | |
| | Lambdas / anonymous functions | ⬜ | | |
| | Special methods (\_\_init\_\_, magic methods) | ⬜ | | |
| | Generics / templates | ⬜ | | |
| | Comments and docstrings | ⬜ | | |
| | Multi-line statements | ⬜ | | |
| | Unusual formatting / indentation | ⬜ | | |
| **Error Conditions** | Syntax errors in input | ⬜ | | |
| | Incomplete/truncated input | ⬜ | | |
| | Invalid encoding | ⬜ | | |
| | Circular dependencies (if applicable) | ⬜ | | |
| | Resource exhaustion scenarios | ⬜ | | |

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
| **Per-Language Testing** | Python parsing works | ⬜ | | |
| | JavaScript parsing works | ⬜ | | |
| | TypeScript parsing works | ⬜ | | |
| | Java parsing works | ⬜ | | |
| | Go parsing works | ⬜ | | |
| | Kotlin parsing works | ⬜ | | |
| | PHP parsing works | ⬜ | | |
| | C# parsing works | ⬜ | | |
| | Ruby parsing works | ⬜ | | |
| **Language-Specific Features** | Language detection works automatically | ⬜ | | |
| | Language parameter overrides work | ⬜ | | |
| | Language-specific constructs handled correctly | ⬜ | | |
| | Unsupported languages return clear error | ⬜ | | |

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
| **Feature Availability** | All Community-tier features work | ⬜ | | |
| | Core functionality accessible | ⬜ | | |
| | No crashes or errors | ⬜ | | |
| **Feature Gating** | Pro-tier fields NOT in response (or empty) | ⬜ | | |
| | Enterprise-tier fields NOT in response (or empty) | ⬜ | | |
| | Attempting Pro features returns Community-level results (no error) | ⬜ | | |
| **Limits Enforcement** | max_depth limit enforced (if applicable) | ⬜ | | |
| | max_files limit enforced (if applicable) | ⬜ | | |
| | max_file_size_mb limit enforced | ⬜ | | |
| | Exceeding limit returns clear warning/error | ⬜ | | |

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
| **Feature Availability** | All Community features work | ⬜ | | |
| | All Pro-exclusive features work | ⬜ | | |
| | New fields populated in response | ⬜ | | |
| **Feature Gating** | Pro fields ARE in response | ⬜ | | |
| | Enterprise fields NOT in response (or empty) | ⬜ | | |
| | Pro features return actual data (not empty/null) | ⬜ | | |
| **Limits Enforcement** | Higher limits than Community (e.g., 10MB vs 1MB) | ⬜ | | |
| | max_depth increased (e.g., 5 vs 1) | ⬜ | | |
| | max_files increased (e.g., 500 vs 50) | ⬜ | | |
| **Capability Flags** | Pro capabilities checked via `get_tool_capabilities()` | ⬜ | | |
| | Capability set includes Pro-specific flags | ⬜ | | |
| | Feature gating uses capability checks (not just tier name) | ⬜ | | |

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
| **Feature Availability** | All Community features work | ⬜ | | |
| | All Pro features work | ⬜ | | |
| | All Enterprise-exclusive features work | ⬜ | | |
| | Maximum features and limits available | ⬜ | | |
| **Feature Gating** | Enterprise fields ARE in response | ⬜ | | |
| | Enterprise features return actual data | ⬜ | | |
| | Unlimited (or very high) limits enforced | ⬜ | | |
| **Limits Enforcement** | Highest limits (e.g., 100MB file size) | ⬜ | | |
| | Unlimited depth/files (or very high ceiling) | ⬜ | | |
| | No truncation warnings (unless truly massive input) | ⬜ | | |

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
| **Valid License Scenarios** | Valid Community license works | ⬜ | | |
| | Valid Pro license works | ⬜ | | |
| | Valid Enterprise license works | ⬜ | | |
| | License tier correctly detected | ⬜ | | |
| **Invalid License Scenarios** | Expired license → Fallback to Community tier | ⬜ | | |
| | Invalid signature → Fallback to Community tier | ⬜ | | |
| | Malformed JWT → Fallback to Community tier | ⬜ | | |
| | Missing license → Default to Community tier | ⬜ | | |
| | Revoked license → Fallback to Community tier (if supported) | ⬜ | | |
| **Grace Period** | 24-hour grace period for expired licenses | ⬜ | | |
| | After grace period → Fallback to Community | ⬜ | | |
| | Warning messages during grace period | ⬜ | | |

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
| **Request/Response Format** | Accepts MCP JSON-RPC 2.0 requests | ⬜ | | |
| | Returns valid MCP JSON-RPC 2.0 responses | ⬜ | | |
| | `"id"` field echoed correctly | ⬜ | | |
| | `"jsonrpc": "2.0"` in response | ⬜ | | |
| **Tool Registration** | Tool appears in `tools/list` response | ⬜ | | |
| | Tool name follows convention: `mcp_code-scalpel_{tool_name}` | ⬜ | | |
| | Tool description is accurate | ⬜ | | |
| | Input schema is complete and valid | ⬜ | | |
| **Error Handling** | Invalid method → JSON-RPC error | ⬜ | | |
| | Missing required param → JSON-RPC error | ⬜ | | |
| | Internal error → JSON-RPC error (not crash) | ⬜ | | |
| | Error codes follow JSON-RPC spec | ⬜ | | |

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
| **Async Execution** | Tool handler is async (uses `async def`) | ⬜ | | |
| | Sync work offloaded to thread pool | ⬜ | | |
| | No blocking of event loop | ⬜ | | |
| | Concurrent requests handled correctly | ⬜ | | |
| **Timeout Handling** | Long-running operations timeout appropriately | ⬜ | | |
| | Timeout errors return gracefully (not crash) | ⬜ | | |
| | Timeout values configurable per tier (if applicable) | ⬜ | | |

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
| **Required Parameters** | Tool requires correct parameters | ⬜ | | |
| | Missing required param → error | ⬜ | | |
| | Null/undefined required param → error | ⬜ | | |
| **Optional Parameters** | Optional params have sensible defaults | ⬜ | | |
| | Omitting optional param works | ⬜ | | |
| | Providing optional param overrides default | ⬜ | | |
| **Parameter Types** | String parameters validated | ⬜ | | |
| | Integer parameters validated | ⬜ | | |
| | Boolean parameters validated | ⬜ | | |
| | Object/dict parameters validated | ⬜ | | |
| | Array/list parameters validated | ⬜ | | |

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
| **Required Fields** | `success` field present (bool) | ⬜ | | |
| | Core fields always present | ⬜ | | |
| | Error field present when success=False | ⬜ | | |
| **Optional Fields** | Tier-specific fields present when applicable | ⬜ | | |
| | Tier-specific fields absent when not applicable | ⬜ | | |
| | null/empty values handled consistently | ⬜ | | |
| **Field Types** | Field types match schema (str, int, bool, list, dict) | ⬜ | | |
| | Lists contain correct item types | ⬜ | | |
| | Dicts contain correct key/value types | ⬜ | | |
| | No unexpected types (e.g., NaN, undefined) | ⬜ | | |

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
