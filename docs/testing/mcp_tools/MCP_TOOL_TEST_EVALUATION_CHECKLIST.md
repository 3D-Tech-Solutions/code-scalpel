# MCP Tool Test Evaluation Checklist

**Purpose**: Standardized framework for evaluating test coverage of MCP tools, ensuring consistent quality across all 22 tools.

**Created**: January 3, 2026  
**Version**: 1.0

---

## Test Evaluation Framework

### Overview

Every MCP tool must be evaluated against this checklist to ensure:
1. **Functional correctness** - Tool works as documented
2. **Tier compliance** - Features properly gated by license tier
3. **License enforcement** - Features unavailable without valid license
4. **Error handling** - Graceful failure on invalid input
5. **Performance** - Meets SLA requirements
6. **Documentation alignment** - Tests validate docstring claims

---

## Tier & License Baseline (REQUIRED FOR ALL TOOLS)

### License File Locations
Test licenses are available in:
- `tests/licenses/code_scalpel_license_pro_20260101_190345.jwt` (Pro tier)
- `tests/licenses/code_scalpel_license_enterprise_20260101_190754.jwt` (Enterprise tier)

### License Configuration
Licenses are loaded via:
- **Environment Variable**: `CODE_SCALPEL_LICENSE_PATH=/path/to/license.jwt`
- **MCP Server Flag**: `--license-file=/path/to/license.jwt`
- **Local Discovery**: `.code-scalpel/license.jwt` (if exists)

### Community Tier Baseline (NO LICENSE)
- ✅ **Default behavior**: Without any license, system must operate in COMMUNITY tier
- ✅ Tool must be callable and return basic results
- ✅ Advanced features MUST be unavailable or filtered
- ✅ No error about missing license (graceful degradation)
- ❌ Pro/Enterprise features completely unavailable

---

## Section 1: Core Functionality Tests

### 1.1 Basic Operation
- [ ] **Test**: Tool executes with minimal valid input
- [ ] **Test**: Tool returns response object of correct type
- [ ] **Test**: Response contains required fields per AnalysisResult/SecurityResult/etc.
- [ ] **Evidence**: Test name format: `test_{tool_name}_basic_operation()`

### 1.2 Input Validation
- [ ] **Test**: Tool rejects empty/None input with clear error
- [ ] **Test**: Tool rejects wrong type (e.g., int when expecting string)
- [ ] **Test**: Tool rejects invalid language parameter
- [ ] **Evidence**: Test name format: `test_{tool_name}_input_validation_*`

### 1.3 Error Handling
- [ ] **Test**: Syntax errors in code don't crash tool (return `success=False`)
- [ ] **Test**: Invalid parameters return helpful error message
- [ ] **Test**: Large input (100KB+) handled gracefully (timeout or limit)
- [ ] **Evidence**: Test name format: `test_{tool_name}_error_handling_*`

### 1.4 Documentation Alignment
- [ ] **Checklist**: Tool docstring claims are verifiable by tests
- [ ] **Checklist**: Example code in docstring actually works
- [ ] **Checklist**: Return type matches documented AnalysisResult
- [ ] **Checklist**: All documented parameters are tested

---

## Section 2: Tier-Gated Features Tests (CRITICAL)

### 2.1 Community Tier Baseline (NO LICENSE)

```bash
# Test without any license
unset CODE_SCALPEL_LICENSE_PATH
pytest tests/mcp_tool_verification/test_analyze_code.py::test_analyze_code_community
```

- [ ] **Test**: Tool available at community tier
- [ ] **Test**: Community features work (per tier limits.toml)
- [ ] **Test**: Pro features UNAVAILABLE (missing from result)
- [ ] **Test**: Enterprise features UNAVAILABLE (missing from result)
- [ ] **Evidence**: 
  - Test calls tool WITHOUT setting `CODE_SCALPEL_LICENSE_PATH`
  - Asserts `result.pro_feature is None` or `pro_feature not in dir(result)`
  - Test name: `test_{tool_name}_community_no_license`

### 2.2 Pro Tier (WITH PRO LICENSE)

```bash
# Test with Pro license
export CODE_SCALPEL_LICENSE_PATH=tests/licenses/code_scalpel_license_pro_20260101_190345.jwt
pytest tests/mcp_tool_verification/test_analyze_code.py::test_analyze_code_pro
```

- [ ] **Test**: Tool available with Pro license
- [ ] **Test**: Community features work
- [ ] **Test**: Pro features NOW AVAILABLE (present in result)
- [ ] **Test**: Enterprise features STILL UNAVAILABLE
- [ ] **Evidence**:
  - Test explicitly sets `CODE_SCALPEL_LICENSE_PATH` to Pro license
  - Asserts `result.pro_feature is not None`
  - Asserts Pro feature returns expected value/structure
  - Test name: `test_{tool_name}_pro_with_license`

### 2.3 Enterprise Tier (WITH ENTERPRISE LICENSE)

```bash
# Test with Enterprise license
export CODE_SCALPEL_LICENSE_PATH=tests/licenses/code_scalpel_license_enterprise_20260101_190754.jwt
pytest tests/mcp_tool_verification/test_analyze_code.py::test_analyze_code_enterprise
```

- [ ] **Test**: Tool available with Enterprise license
- [ ] **Test**: Community features work
- [ ] **Test**: Pro features NOW AVAILABLE
- [ ] **Test**: Enterprise features NOW AVAILABLE
- [ ] **Evidence**:
  - Test explicitly sets `CODE_SCALPEL_LICENSE_PATH` to Enterprise license
  - Asserts `result.enterprise_feature is not None`
  - Asserts all three tiers' features present and working
  - Test name: `test_{tool_name}_enterprise_with_license`

### 2.4 License Expiration / Invalid License

```bash
# Test with broken/expired license (should degrade to community)
export CODE_SCALPEL_LICENSE_PATH=tests/licenses/code_scalpel_license_pro_test_broken.jwt
pytest tests/mcp_tool_verification/test_analyze_code.py::test_analyze_code_invalid_license
```

- [ ] **Test**: Tool gracefully falls back to Community when license invalid/expired
- [ ] **Test**: Community features still work
- [ ] **Test**: Pro features UNAVAILABLE (no error, just missing)
- [ ] **Evidence**:
  - Test uses broken license (missing required claims)
  - Asserts tool returns community-only results
  - No "license error" in response, just graceful degradation
  - Test name: `test_{tool_name}_invalid_license_fallback`

---

## Section 3: Accuracy & Correctness Tests

### 3.1 Structure Extraction (for `analyze_code`, `extract_code`, etc.)

- [ ] **Test**: Named functions are extracted with exact names
  ```python
  code = "def my_function(): pass"
  result = analyze_code(code)
  assert "my_function" in result.functions  # NOT just count check
  ```

- [ ] **Test**: No false positives (hallucinations)
  ```python
  code = "def real(): pass"
  result = analyze_code(code)
  assert "fake_function" not in result.functions
  ```

- [ ] **Test**: Edge cases handled
  - Decorators (`@decorator\ndef func()`)
  - Nested functions (`def outer():\n  def inner()`)
  - Async functions (`async def func()`)
  - Class methods, properties, classmethods
  - Lambda functions (if applicable)

- [ ] **Test**: Multi-language support (if applicable)
  - Python code extraction
  - Java code extraction (if supported)
  - JavaScript/TypeScript extraction (if supported)

- [ ] **Evidence**: Test name format: `test_{tool_name}_extraction_accuracy_*`

### 3.2 Complexity Metrics (if applicable)

- [ ] **Test**: Complexity score correlates with code complexity
  ```python
  simple = "def f(): return 1"
  complex = "def f(x):\n  if x: return 1\n  elif: return 2\n  else: return 3"
  
  simple_result = analyze_code(simple)
  complex_result = analyze_code(complex)
  
  assert complex_result.complexity_score > simple_result.complexity_score
  ```

- [ ] **Test**: Complexity score is consistent across runs
- [ ] **Test**: Complexity score matches documented calculation
- [ ] **Evidence**: Test name format: `test_{tool_name}_complexity_accuracy`

### 3.3 Security Vulnerability Detection (for `security_scan`, `unified_sink_detect`, etc.)

- [ ] **Test**: Known vulnerability is detected
  ```python
  vulnerable = "query = f'SELECT * FROM users WHERE id = {user_id}'"
  result = security_scan(vulnerable)
  assert result.has_vulnerabilities
  assert any("SQL" in v.type for v in result.vulnerabilities)
  ```

- [ ] **Test**: No false positives on safe code
  ```python
  safe = "query = 'SELECT * FROM users WHERE id = ?'"
  result = security_scan(safe)
  assert not result.has_vulnerabilities  # or minimal low-severity
  ```

- [ ] **Test**: CWE/OWASP mapping correct
- [ ] **Test**: Confidence scores within [0.0, 1.0]
- [ ] **Evidence**: Test name format: `test_{tool_name}_vulnerability_detection_*`

---

## Section 4: Integration & Protocol Tests

### 4.1 HTTP/SSE Interface

- [ ] **Test**: Tool callable via HTTP POST
- [ ] **Test**: Response is valid JSON
- [ ] **Test**: Response filtering applied per tier
- [ ] **Test**: Error codes correct (400, 401, 403, 500)
- [ ] **Command**: `CODE_SCALPEL_LICENSE_PATH=... pytest tests/mcp_tool_verification/test_mcp_tools_contracts_http.py::test_{tool_name} -v`
- [ ] **Evidence**: Test file `test_mcp_tools_contracts_http.py`

### 4.2 Stdio/MCP Interface

- [ ] **Test**: Tool callable via MCP protocol
- [ ] **Test**: Response follows JSONSchema
- [ ] **Test**: Async execution works
- [ ] **Test**: Timeout handling (long-running tools)
- [ ] **Command**: `CODE_SCALPEL_LICENSE_PATH=... pytest tests/mcp_tool_verification/test_mcp_tools_contracts_stdio.py::test_{tool_name} -v`
- [ ] **Evidence**: Test file `test_mcp_tools_contracts_stdio.py`

### 4.3 CLI Interface

- [ ] **Test**: Tool callable from command line (if applicable)
- [ ] **Test**: Output format correct (JSON/text)
- [ ] **Test**: Help text available
- [ ] **Evidence**: Test file `tests/cli/test_cli.py`

---

## Section 5: Performance & Scale Tests

### 5.1 Performance SLAs

- [ ] **Test**: Tool completes within documented SLA
  ```python
  import time
  start = time.time()
  result = analyze_code(large_code)
  elapsed = time.time() - start
  assert elapsed < SLA_MS / 1000  # e.g., < 2.0 seconds
  ```

- [ ] **Test**: Response time consistent across runs
- [ ] **Test**: No unbounded memory growth
- [ ] **Evidence**: Test name format: `test_{tool_name}_performance_*`

### 5.2 Scale Testing

- [ ] **Test**: Large input handled (100+ classes, functions)
- [ ] **Test**: Very large input gracefully degraded (timeout or limit)
- [ ] **Evidence**: Test name format: `test_{tool_name}_scale_*`

---

## Section 6: Test Suite Structure

### Required Test Files

For each tool `{tool_name}`:

1. **Functional Tests** (Required)
   - Location: `tests/mcp_tool_verification/test_{tool_name}.py` OR
   - Location: `tests/core/test_{tool_name}.py`
   - Coverage: Sections 1-3 above

2. **Tier Tests** (Required - CRITICAL)
   - Location: `tests/tools/tiers/test_{tool_name}_tiers.py` OR
   - Location: Included in functional test file with tier fixtures
   - Coverage: Section 2 above
   - **IMPORTANT**: Must test with/without license

3. **Integration Tests** (Required)
   - Location: `tests/mcp_tool_verification/test_mcp_tools_contracts_*.py`
   - Coverage: Section 4 above

4. **Performance Tests** (Optional - Recommended)
   - Location: `tests/performance/test_{tool_name}_perf.py`
   - Coverage: Section 5 above

### Test Naming Convention

```python
# Functional tests
test_{tool_name}_basic_operation()
test_{tool_name}_input_validation_*()
test_{tool_name}_error_handling_*()

# Tier tests (CRITICAL)
test_{tool_name}_community_no_license()      # Without license
test_{tool_name}_pro_with_license()          # With Pro license
test_{tool_name}_enterprise_with_license()   # With Enterprise license
test_{tool_name}_invalid_license_fallback()  # Broken license

# Integration tests
test_{tool_name}_http_interface()
test_{tool_name}_stdio_interface()
test_{tool_name}_cli_interface()

# Accuracy tests
test_{tool_name}_extraction_accuracy_*()
test_{tool_name}_vulnerability_detection_*()
test_{tool_name}_complexity_accuracy()
```

---

## Section 7: Verification Checklist

Use this checklist when evaluating a tool's test suite:

### Core Tests
- [ ] Functional tests exist and pass
- [ ] Input validation tests exist
- [ ] Error handling tests exist
- [ ] Documentation alignment verified

### Tier Tests (CRITICAL - DO NOT SKIP)
- [ ] Community tier test (NO license) ✓
  - [ ] Tool callable without license
  - [ ] Community features work
  - [ ] Pro features unavailable (not in result)
  - [ ] Enterprise features unavailable
  
- [ ] Pro tier test (WITH Pro license) ✓
  - [ ] Test sets `CODE_SCALPEL_LICENSE_PATH=tests/licenses/code_scalpel_license_pro_*.jwt`
  - [ ] Community + Pro features work
  - [ ] Enterprise features unavailable
  
- [ ] Enterprise tier test (WITH Enterprise license) ✓
  - [ ] Test sets `CODE_SCALPEL_LICENSE_PATH=tests/licenses/code_scalpel_license_enterprise_*.jwt`
  - [ ] All features (Community + Pro + Enterprise) work
  
- [ ] Invalid/Expired license test ✓
  - [ ] Gracefully falls back to Community
  - [ ] No error message, just feature reduction

### Accuracy Tests
- [ ] Structure extraction tests (if applicable)
- [ ] Vulnerability detection tests (if applicable)
- [ ] Complexity/metric tests (if applicable)
- [ ] No hallucination tests (specific names, not just counts)

### Integration Tests
- [ ] HTTP/SSE interface tests
- [ ] Stdio/MCP protocol tests
- [ ] Response filtering by tier validated

### Documentation
- [ ] All docstring claims are testable
- [ ] Example code actually works
- [ ] Return type matches reality

---

## Example: analyze_code Test Evaluation

**Tool**: `analyze_code`  
**Status**: ⚠️ INCOMPLETE - Needs tier tests

### Current Tests
- ✅ test_analyze_code_python - Basic structure count
- ✅ test_analyze_code_community_limits - Community tier
- ❌ test_analyze_code_pro_with_license - MISSING
- ❌ test_analyze_code_enterprise_with_license - MISSING
- ❌ test_analyze_code_invalid_license_fallback - MISSING
- ❌ test_analyze_code_extraction_accuracy - MISSING (names, not counts)
- ❌ test_analyze_code_no_false_positives - MISSING
- ❌ test_analyze_code_imports_extraction - MISSING

### Required Additions
1. **Pro tier test**: Extract with `CODE_SCALPEL_LICENSE_PATH` set to Pro license
2. **Enterprise tier test**: Extract with Enterprise license
3. **Accuracy tests**: Verify specific function/class names extracted
4. **Imports test**: Validate imports list

---

## Commands for Tier Testing

### Run all tools at community tier (NO LICENSE)
```bash
unset CODE_SCALPEL_LICENSE_PATH
pytest tests/mcp_tool_verification/ -v -k "community"
```

### Run all tools at Pro tier
```bash
export CODE_SCALPEL_LICENSE_PATH=tests/licenses/code_scalpel_license_pro_20260101_190345.jwt
pytest tests/mcp_tool_verification/ -v
```

### Run all tools at Enterprise tier
```bash
export CODE_SCALPEL_LICENSE_PATH=tests/licenses/code_scalpel_license_enterprise_20260101_190754.jwt
pytest tests/mcp_tool_verification/ -v
```

### Run only tier-gated tests
```bash
pytest tests/tools/tiers/ -v
```

---

## Release Gate Requirement

**BLOCKING ISSUE**: Before release, verify that:
- [ ] All 22 tools have tier tests
- [ ] All tier tests use proper license paths (test/licenses/*.jwt)
- [ ] Community tier is default (no license required)
- [ ] Pro/Enterprise features are unavailable without proper license
- [ ] License expiration degrades to Community (no error)
- [ ] All docstring claims have supporting tests
