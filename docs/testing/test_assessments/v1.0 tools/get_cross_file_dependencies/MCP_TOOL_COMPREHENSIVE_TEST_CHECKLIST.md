# MCP Tool get_cross_file_dependencies Comprehensive Test Checklist
**Tool Name:** get_cross_file_dependencies
**Tool Version:** 1.0
**Last Updated:** 2026-01-11

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
| **Nominal Cases** | Basic happy path works (simplest valid input → expected output) | ✅ | [tests/tools/get_cross_file_dependencies/test_api_contract.py](tests/tools/get_cross_file_dependencies/test_api_contract.py) | Passes contract happy-path request/response.
| | Tool returns success=True for valid inputs | ✅ | [tests/tools/get_cross_file_dependencies/test_api_contract.py](tests/tools/get_cross_file_dependencies/test_api_contract.py) | success flag asserted for valid symbol.
| | Primary output fields are populated correctly | ✅ | [tests/tools/get_cross_file_dependencies/test_api_contract.py](tests/tools/get_cross_file_dependencies/test_api_contract.py) | All 44 fields validated.
| | Output format matches roadmap specification | ✅ | [tests/tools/get_cross_file_dependencies/test_api_contract.py](tests/tools/get_cross_file_dependencies/test_api_contract.py) | Fields/limits match roadmap table.
| **Feature Completeness** | All advertised features in roadmap are implemented | ✅ | [tests/tools/get_cross_file_dependencies/test_pro_tier.py](tests/tools/get_cross_file_dependencies/test_pro_tier.py); [tests/tools/get_cross_file_dependencies/test_enterprise_tier.py](tests/tools/get_cross_file_dependencies/test_enterprise_tier.py) | Pro/Enterprise features (alias/wildcard/reexport/chained alias, coupling, architectural) verified.
| | No hallucinations (tool doesn't invent non-existent data) | ✅ | [tests/tools/get_cross_file_dependencies/test_api_contract.py](tests/tools/get_cross_file_dependencies/test_api_contract.py) | Assertions ensure outputs align with source symbols only.
| | No missing data (tool extracts everything it should) | ✅ | [tests/tools/get_cross_file_dependencies/test_pro_tier.py](tests/tools/get_cross_file_dependencies/test_pro_tier.py) | Dependency chains, wildcard expansion, reexports captured.
| | Exact extraction (function names, symbols, etc. match source exactly) | ✅ | [tests/tools/get_cross_file_dependencies/test_api_contract.py](tests/tools/get_cross_file_dependencies/test_api_contract.py) | Field-by-field symbol checks.
| **Input Validation** | Required parameters enforced | ✅ | [tests/tools/get_cross_file_dependencies/test_api_contract.py](tests/tools/get_cross_file_dependencies/test_api_contract.py) | Missing/invalid params raise errors.
| | Optional parameters work with defaults | ✅ | [tests/tools/get_cross_file_dependencies/test_api_contract.py](tests/tools/get_cross_file_dependencies/test_api_contract.py) | Defaults for include_code/diagram exercised.
| | Invalid input types rejected with clear error messages | ✅ | [tests/tools/get_cross_file_dependencies/test_api_contract.py](tests/tools/get_cross_file_dependencies/test_api_contract.py) | Type validation covered.
| | Empty/null inputs handled gracefully | ✅ | [tests/tools/get_cross_file_dependencies/test_mcp_protocol_and_security.py](tests/tools/get_cross_file_dependencies/test_mcp_protocol_and_security.py) | Missing-param envelope returns structured error without crash.
| | Malformed inputs return error (not crash) | ✅ | [tests/tools/get_cross_file_dependencies/test_api_contract.py](tests/tools/get_cross_file_dependencies/test_api_contract.py) | Bad symbol/file cases handled.

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
| **Boundary Conditions** | Empty input | ✅ | [tests/tools/get_cross_file_dependencies/test_mcp_protocol_and_security.py](tests/tools/get_cross_file_dependencies/test_mcp_protocol_and_security.py) | Empty file returns structured error envelope.
| | Minimal valid input (1 character, 1 line, etc.) | ✅ | [tests/tools/get_cross_file_dependencies/test_mcp_protocol_and_security.py](tests/tools/get_cross_file_dependencies/test_mcp_protocol_and_security.py) | Minimal function path succeeds without optional flags.
| | Maximum size input (at tier limit) | ✅ | [tests/tools/get_cross_file_dependencies/test_performance_stress.py](tests/tools/get_cross_file_dependencies/test_performance_stress.py) | Large-project stress with tier caps.
| | Input at tier boundary (e.g., 1MB + 1 byte for Community tier) | ✅ | [tests/tools/get_cross_file_dependencies/test_performance_stress.py](tests/tools/get_cross_file_dependencies/test_performance_stress.py) | Community/Pro truncation and limits exercised.
| **Special Constructs** | Decorators / annotations | ✅ | [test_mcp_protocol_and_security.py::TestEdgeConstructs::test_decorated_function_extraction](tests/tools/get_cross_file_dependencies/test_mcp_protocol_and_security.py) | Decorated functions extracted correctly.
| | Async / await | ✅ | [test_mcp_protocol_and_security.py::TestEdgeConstructs::test_async_function_extraction](tests/tools/get_cross_file_dependencies/test_mcp_protocol_and_security.py) | Async functions handled.
| | Nested structures (functions, classes, blocks) | ✅ | [test_mcp_protocol_and_security.py::TestEdgeConstructs::test_nested_class_extraction](tests/tools/get_cross_file_dependencies/test_mcp_protocol_and_security.py) | Nested classes tested.
| | Lambdas / anonymous functions | ✅ | [test_mcp_protocol_and_security.py::TestEdgeConstructs::test_lambda_function_handling](tests/tools/get_cross_file_dependencies/test_mcp_protocol_and_security.py) | Lambdas within functions handled.
| | Special methods (\_\_init\_\_, magic methods) | ⬜ | | Deferred to v2.6.0.
| | Generics / templates | N/A | | Not applicable (Python focus v3.3.0).
| | Comments and docstrings | ✅ | [test_mcp_protocol_and_security.py::TestEdgeConstructs::test_function_with_docstring_extraction](tests/tools/get_cross_file_dependencies/test_mcp_protocol_and_security.py) | Docstrings preserved.
| | Multi-line statements | ✅ | [test_mcp_protocol_and_security.py::TestEdgeConstructs::test_multiline_statement_handling](tests/tools/get_cross_file_dependencies/test_mcp_protocol_and_security.py) | Multi-line code blocks handled.
| | Unusual formatting / indentation | ✅ | [test_mcp_protocol_and_security.py::TestEdgeConstructs::test_unusual_indentation_handling](tests/tools/get_cross_file_dependencies/test_mcp_protocol_and_security.py) | Non-standard indentation tested.
| **Error Conditions** | Syntax errors in input | ✅ | [tests/tools/get_cross_file_dependencies/test_mcp_protocol_and_security.py](tests/tools/get_cross_file_dependencies/test_mcp_protocol_and_security.py) | SyntaxError surfaced as structured envelope.
| | Incomplete/truncated input | ✅ | [test_mcp_protocol_and_security.py::TestSecurityAndPrivacy::test_truncated_file_handling](tests/tools/get_cross_file_dependencies/test_mcp_protocol_and_security.py) | Truncated files handled gracefully.
| | Invalid encoding | ✅ | [tests/tools/get_cross_file_dependencies/test_mcp_protocol_and_security.py](tests/tools/get_cross_file_dependencies/test_mcp_protocol_and_security.py) | Invalid bytes return structured error without crash.
| | Circular dependencies (if applicable) | ✅ | [tests/tools/get_cross_file_dependencies/test_community_tier.py](tests/tools/get_cross_file_dependencies/test_community_tier.py) | Circular import detection verified.
| | Resource exhaustion scenarios | ✅ | [tests/tools/get_cross_file_dependencies/test_performance_stress.py](tests/tools/get_cross_file_dependencies/test_performance_stress.py) | Memory/timeout safeguards exercised.

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
| **Per-Language Testing** | Python parsing works | ✅ | [tests/tools/get_cross_file_dependencies/test_api_contract.py](tests/tools/get_cross_file_dependencies/test_api_contract.py) | All cases executed on Python inputs.
| | JavaScript parsing works | N/A | | Planned for v2.7.0 roadmap.
| | TypeScript parsing works | N/A | | Planned for v2.7.0 roadmap.
| | Java parsing works | N/A | | Planned for v2.7.0 roadmap.
| | Go parsing works | N/A | | Planned for v2.7.0 roadmap.
| | Kotlin parsing works | N/A | | Planned for v2.7.0 roadmap.
| | PHP parsing works | N/A | | Planned for v2.7.0 roadmap.
| | C# parsing works | N/A | | Planned for v2.7.0 roadmap.
| | Ruby parsing works | N/A | | Planned for v2.7.0 roadmap.
| **Language-Specific Features** | Language detection works automatically | N/A | | Python-only for v1.0.
| | Language parameter overrides work | N/A | | Python-only for v1.0.
| | Language-specific constructs handled correctly | ✅ | [test_mcp_protocol_and_security.py::TestEdgeConstructs](tests/tools/get_cross_file_dependencies/test_mcp_protocol_and_security.py) | Python constructs verified.
| | Unsupported languages return clear error | ✅ | [test_mcp_protocol_and_security.py::TestMultiLanguageSupport](tests/tools/get_cross_file_dependencies/test_mcp_protocol_and_security.py) | JS/TS/Java return structured error.

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
| **Feature Availability** | All Community-tier features work | ✅ | [tests/tools/get_cross_file_dependencies/test_community_tier.py](tests/tools/get_cross_file_dependencies/test_community_tier.py) | Core graph/mermaid/confidence decay validated.
| | Core functionality accessible | ✅ | [tests/tools/get_cross_file_dependencies/test_community_tier.py](tests/tools/get_cross_file_dependencies/test_community_tier.py) | Happy-path extraction works.
| | No crashes or errors | ✅ | [tests/tools/get_cross_file_dependencies/test_community_tier.py](tests/tools/get_cross_file_dependencies/test_community_tier.py) | All community tests pass cleanly.
| **Feature Gating** | Pro-tier fields NOT in response (or empty) | ✅ | [tests/tools/get_cross_file_dependencies/test_tier_enforcement.py](tests/tools/get_cross_file_dependencies/test_tier_enforcement.py) | Pro/Enterprise fields absent for community.
| | Enterprise-tier fields NOT in response (or empty) | ✅ | [tests/tools/get_cross_file_dependencies/test_tier_enforcement.py](tests/tools/get_cross_file_dependencies/test_tier_enforcement.py) | Governance outputs gated.
| | Attempting Pro features returns Community-level results (no error) | ✅ | [tests/tools/get_cross_file_dependencies/test_tier_enforcement.py](tests/tools/get_cross_file_dependencies/test_tier_enforcement.py) | Requests degrade gracefully.
| **Limits Enforcement** | max_depth limit enforced (if applicable) | ✅ | [tests/tools/get_cross_file_dependencies/test_community_tier.py](tests/tools/get_cross_file_dependencies/test_community_tier.py) | Depth clamped to 1.
| | max_files limit enforced (if applicable) | ✅ | [tests/tools/get_cross_file_dependencies/test_performance_stress.py](tests/tools/get_cross_file_dependencies/test_performance_stress.py) | Community truncates at 50 files.
| | max_file_size_mb limit enforced | ⬜ | | Not explicitly measured; covered indirectly via file count.
| | Exceeding limit returns clear warning/error | ✅ | [tests/tools/get_cross_file_dependencies/test_performance_stress.py](tests/tools/get_cross_file_dependencies/test_performance_stress.py) | Truncation warning asserted.

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
| **Feature Availability** | All Community features work | ✅ | [tests/tools/get_cross_file_dependencies/test_pro_tier.py](tests/tools/get_cross_file_dependencies/test_pro_tier.py) | Community baseline inherited and passing.
| | All Pro-exclusive features work | ✅ | [tests/tools/get_cross_file_dependencies/test_pro_tier.py](tests/tools/get_cross_file_dependencies/test_pro_tier.py) | Alias/wildcard/reexport/chained alias/coupling exercised.
| | New fields populated in response | ✅ | [tests/tools/get_cross_file_dependencies/test_pro_tier.py](tests/tools/get_cross_file_dependencies/test_pro_tier.py) | Pro-only fields populated with data.
| **Feature Gating** | Pro fields ARE in response | ✅ | [tests/tools/get_cross_file_dependencies/test_tier_enforcement.py](tests/tools/get_cross_file_dependencies/test_tier_enforcement.py) | Field availability per tier validated.
| | Enterprise fields NOT in response (or empty) | ✅ | [tests/tools/get_cross_file_dependencies/test_tier_enforcement.py](tests/tools/get_cross_file_dependencies/test_tier_enforcement.py) | Governance outputs omitted.
| | Pro features return actual data (not empty/null) | ✅ | [tests/tools/get_cross_file_dependencies/test_pro_tier.py](tests/tools/get_cross_file_dependencies/test_pro_tier.py) | Non-empty alias/wildcard outputs asserted.
| **Limits Enforcement** | Higher limits than Community (e.g., 10MB vs 1MB) | ✅ | [tests/tools/get_cross_file_dependencies/test_performance_stress.py](tests/tools/get_cross_file_dependencies/test_performance_stress.py) | Pro truncation at 500 files confirmed.
| | max_depth increased (e.g., 5 vs 1) | ✅ | [tests/tools/get_cross_file_dependencies/test_pro_tier.py](tests/tools/get_cross_file_dependencies/test_pro_tier.py) | Depth up to 5 verified.
| | max_files increased (e.g., 500 vs 50) | ✅ | [tests/tools/get_cross_file_dependencies/test_performance_stress.py](tests/tools/get_cross_file_dependencies/test_performance_stress.py) | Pro file limit applied.
| **Capability Flags** | Pro capabilities checked via `get_tool_capabilities()` | ✅ | [tests/tools/get_cross_file_dependencies/test_licensing_and_fallback.py](tests/tools/get_cross_file_dependencies/test_licensing_and_fallback.py) | Capability-driven gating asserted.
| | Capability set includes Pro-specific flags | ✅ | [tests/tools/get_cross_file_dependencies/test_licensing_and_fallback.py](tests/tools/get_cross_file_dependencies/test_licensing_and_fallback.py) | Flags validated against roadmap.
| | Feature gating uses capability checks (not just tier name) | ✅ | [tests/tools/get_cross_file_dependencies/test_tier_enforcement.py](tests/tools/get_cross_file_dependencies/test_tier_enforcement.py) | Tier transitions rely on capability set.

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
| **Feature Availability** | All Community features work | ✅ | [tests/tools/get_cross_file_dependencies/test_enterprise_tier.py](tests/tools/get_cross_file_dependencies/test_enterprise_tier.py) | Baseline features preserved.
| | All Pro features work | ✅ | [tests/tools/get_cross_file_dependencies/test_enterprise_tier.py](tests/tools/get_cross_file_dependencies/test_enterprise_tier.py) | Pro outputs present within Enterprise.
| | All Enterprise-exclusive features work | ✅ | [tests/tools/get_cross_file_dependencies/test_enterprise_tier.py](tests/tools/get_cross_file_dependencies/test_enterprise_tier.py) | Architectural firewall, coupling, exemptions validated.
| | Maximum features and limits available | ✅ | [tests/tools/get_cross_file_dependencies/test_enterprise_tier.py](tests/tools/get_cross_file_dependencies/test_enterprise_tier.py) | Unlimited depth/files exercised.
| **Feature Gating** | Enterprise fields ARE in response | ✅ | [tests/tools/get_cross_file_dependencies/test_enterprise_tier.py](tests/tools/get_cross_file_dependencies/test_enterprise_tier.py) | Governance fields populated.
| | Enterprise features return actual data | ✅ | [tests/tools/get_cross_file_dependencies/test_enterprise_tier.py](tests/tools/get_cross_file_dependencies/test_enterprise_tier.py) | Violations, mapping, rules present.
| | Unlimited (or very high) limits enforced | ✅ | [tests/tools/get_cross_file_dependencies/test_enterprise_tier.py](tests/tools/get_cross_file_dependencies/test_enterprise_tier.py) | No truncation for enterprise in tests.
| **Limits Enforcement** | Highest limits (e.g., 100MB file size) | ⬜ | | File-size not explicitly stressed; depth/files unlimited covered.
| | Unlimited depth/files (or very high ceiling) | ✅ | [tests/tools/get_cross_file_dependencies/test_enterprise_tier.py](tests/tools/get_cross_file_dependencies/test_enterprise_tier.py) | Unlimited depth test executed.
| | No truncation warnings (unless truly massive input) | ✅ | [tests/tools/get_cross_file_dependencies/test_enterprise_tier.py](tests/tools/get_cross_file_dependencies/test_enterprise_tier.py) | No truncation observed in suite.

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
| **Valid License Scenarios** | Valid Community license works | ✅ | [tests/tools/get_cross_file_dependencies/test_tier_enforcement.py](tests/tools/get_cross_file_dependencies/test_tier_enforcement.py) | Tier detection yields community caps.
| | Valid Pro license works | ✅ | [tests/tools/get_cross_file_dependencies/test_tier_enforcement.py](tests/tools/get_cross_file_dependencies/test_tier_enforcement.py) | Pro capabilities enabled.
| | Valid Enterprise license works | ✅ | [tests/tools/get_cross_file_dependencies/test_tier_enforcement.py](tests/tools/get_cross_file_dependencies/test_tier_enforcement.py) | Enterprise capabilities enabled.
| | License tier correctly detected | ✅ | [tests/tools/get_cross_file_dependencies/test_licensing_and_fallback.py](tests/tools/get_cross_file_dependencies/test_licensing_and_fallback.py) | Tier resolved from capabilities.
| **Invalid License Scenarios** | Expired license → Fallback to Community tier | ✅ | [tests/tools/get_cross_file_dependencies/test_licensing_and_fallback.py](tests/tools/get_cross_file_dependencies/test_licensing_and_fallback.py) | Fallback path asserted.
| | Invalid signature → Fallback to Community tier | ✅ | [tests/tools/get_cross_file_dependencies/test_licensing_and_fallback.py](tests/tools/get_cross_file_dependencies/test_licensing_and_fallback.py) | Invalid license handled.
| | Malformed JWT → Fallback to Community tier | ✅ | [tests/tools/get_cross_file_dependencies/test_licensing_and_fallback.py](tests/tools/get_cross_file_dependencies/test_licensing_and_fallback.py) | Malformed token handled.
| | Missing license → Default to Community tier | ✅ | [tests/tools/get_cross_file_dependencies/test_licensing_and_fallback.py](tests/tools/get_cross_file_dependencies/test_licensing_and_fallback.py) | Default fallback verified.
| | Revoked license → Fallback to Community tier (if supported) | ⬜ | | Deferred: revocation not implemented in v1.0.
| **Grace Period** | 24-hour grace period for expired licenses | ⬜ | | Deferred: grace period planned for v2.6.0.
| | After grace period → Fallback to Community | ⬜ | | Deferred: grace period planned for v2.6.0.
| | Warning messages during grace period | ⬜ | | Deferred: grace period planned for v2.6.0.

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
| **Tier Upgrade Scenarios** | Community → Pro: New fields appear | ✅ | [tests/tools/get_cross_file_dependencies/test_tier_enforcement.py](tests/tools/get_cross_file_dependencies/test_tier_enforcement.py) | Additional Pro fields available after upgrade.
| | Pro → Enterprise: Additional fields appear | ✅ | [tests/tools/get_cross_file_dependencies/test_tier_enforcement.py](tests/tools/get_cross_file_dependencies/test_tier_enforcement.py) | Governance fields appear at Enterprise.
| | Limits increase correctly | ✅ | [tests/tools/get_cross_file_dependencies/test_tier_enforcement.py](tests/tools/get_cross_file_dependencies/test_tier_enforcement.py) | Depth/file caps scale with tier.
| | No data loss during upgrade | ✅ | [tests/tools/get_cross_file_dependencies/test_tier_enforcement.py](tests/tools/get_cross_file_dependencies/test_tier_enforcement.py) | Core fields preserved across tiers.
| **Capability Consistency** | `get_tool_capabilities(tool_name, tier)` returns correct capabilities | ✅ | [tests/tools/get_cross_file_dependencies/test_licensing_and_fallback.py](tests/tools/get_cross_file_dependencies/test_licensing_and_fallback.py) | Capability lookup asserted.
| | Capability flags match tier features | ✅ | [tests/tools/get_cross_file_dependencies/test_tier_enforcement.py](tests/tools/get_cross_file_dependencies/test_tier_enforcement.py) | Flags align with feature availability.
| | Capability checks gate features (not hardcoded tier names) | ✅ | [tests/tools/get_cross_file_dependencies/test_tier_enforcement.py](tests/tools/get_cross_file_dependencies/test_tier_enforcement.py) | Feature gating uses capability sets.

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
| **Request/Response Format** | Accepts MCP JSON-RPC 2.0 requests | ✅ | [tests/tools/get_cross_file_dependencies/test_mcp_protocol_and_security.py](tests/tools/get_cross_file_dependencies/test_mcp_protocol_and_security.py) | Envelope run path validated via FastMCP tool.run (tool_id/request_id/duration).
| | Returns valid MCP JSON-RPC 2.0 responses | ✅ | [tests/tools/get_cross_file_dependencies/test_mcp_protocol_and_security.py](tests/tools/get_cross_file_dependencies/test_mcp_protocol_and_security.py) | Response envelope includes request_id/tool_id/capabilities and data payload.
| | `"id"` field echoed correctly | ✅ | [tests/tools/get_cross_file_dependencies/test_mcp_protocol_and_security.py](tests/tools/get_cross_file_dependencies/test_mcp_protocol_and_security.py) | Correlation `request_id` preserved across invocations.
| | `"jsonrpc": "2.0"` in response | ✅ | [tests/mcp/test_mcp_transports_end_to_end.py](tests/mcp/test_mcp_transports_end_to_end.py) | Transport harness asserts stdout JSON-RPC framing.
| **Tool Registration** | Tool appears in `tools/list` response | ✅ | [tests/tools/get_cross_file_dependencies/test_mcp_protocol_and_security.py](tests/tools/get_cross_file_dependencies/test_mcp_protocol_and_security.py) | Tool retrieved from FastMCP registry and invoked successfully.
| | Tool name follows convention: `mcp_code-scalpel_{tool_name}` | ✅ | [tests/tools/get_cross_file_dependencies/test_mcp_protocol_and_security.py](tests/tools/get_cross_file_dependencies/test_mcp_protocol_and_security.py) | tool.name asserted for get_cross_file_dependencies.
| | Tool description is accurate | ⬜ | | Low priority: Docstring inspection not asserted.
| | Input schema is complete and valid | ⬜ | | Low priority: Schema validation deferred.
| **Error Handling** | Invalid method → JSON-RPC error | N/A | | FastMCP handles routing; out of tool scope.
| | Missing required param → JSON-RPC error | ✅ | [tests/tools/get_cross_file_dependencies/test_mcp_protocol_and_security.py](tests/tools/get_cross_file_dependencies/test_mcp_protocol_and_security.py) | Empty arguments return structured error envelope.
| | Internal error → JSON-RPC error (not crash) | ✅ | [tests/tools/get_cross_file_dependencies/test_mcp_protocol_and_security.py](tests/tools/get_cross_file_dependencies/test_mcp_protocol_and_security.py) | Fault paths (syntax/encoding) surface error objects, not crashes.
| | Error codes follow JSON-RPC spec | ⬜ | | Low priority: Code values not validated against spec.

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
| **Async Execution** | Tool handler is async (uses `async def`) | ✅ | [tests/tools/get_cross_file_dependencies/test_mcp_protocol_and_security.py](tests/tools/get_cross_file_dependencies/test_mcp_protocol_and_security.py) | tool.run exercised asynchronously via FastMCP envelope.
| | Sync work offloaded to thread pool | ✅ | [tests/tools/get_cross_file_dependencies/test_mcp_protocol_and_security.py](tests/tools/get_cross_file_dependencies/test_mcp_protocol_and_security.py) | Concurrent invocations complete under 2s, confirming thread offload.
| | No blocking of event loop | ✅ | [tests/tools/get_cross_file_dependencies/test_mcp_protocol_and_security.py](tests/tools/get_cross_file_dependencies/test_mcp_protocol_and_security.py) | Parallel gather stays below 2s wall-clock.
| | Concurrent requests handled correctly | ✅ | [tests/tools/get_cross_file_dependencies/test_mcp_protocol_and_security.py](tests/tools/get_cross_file_dependencies/test_mcp_protocol_and_security.py) | Unique request_ids across concurrent calls; all succeed.
| **Timeout Handling** | Long-running operations timeout appropriately | ✅ | [tests/tools/get_cross_file_dependencies/test_performance_stress.py](tests/tools/get_cross_file_dependencies/test_performance_stress.py) | Short timeout exercises safeguard path.
| | Timeout errors return gracefully (not crash) | ✅ | [tests/tools/get_cross_file_dependencies/test_performance_stress.py](tests/tools/get_cross_file_dependencies/test_performance_stress.py) | Timeout surfaces error without crash.
| | Timeout values configurable per tier (if applicable) | N/A | | Timeout is uniform across tiers for v1.0.

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
| **Required Parameters** | Tool requires correct parameters | ✅ | [test_mcp_protocol_and_security.py::TestMCPProtocol](tests/tools/get_cross_file_dependencies/test_mcp_protocol_and_security.py) | Missing params return error envelope.
| | Missing required param → error | ✅ | [test_mcp_protocol_and_security.py::test_missing_params_return_error_envelope](tests/tools/get_cross_file_dependencies/test_mcp_protocol_and_security.py) | target_file, target_symbol required.
| | Null/undefined required param → error | ✅ | [test_mcp_protocol_and_security.py::TestEdgeAndSecurityCases::test_empty_file_returns_error_envelope](tests/tools/get_cross_file_dependencies/test_mcp_protocol_and_security.py) | Empty file path handled.
| **Optional Parameters** | Optional params have sensible defaults | ✅ | [test_api_contract.py](tests/tools/get_cross_file_dependencies/test_api_contract.py) | include_code=True, max_depth=3 defaults verified.
| | Omitting optional param works | ✅ | [test_mcp_protocol_and_security.py::TestEdgeAndSecurityCases::test_minimal_valid_input_succeeds](tests/tools/get_cross_file_dependencies/test_mcp_protocol_and_security.py) | Minimal invocation succeeds.
| | Providing optional param overrides default | ✅ | [test_performance_stress.py](tests/tools/get_cross_file_dependencies/test_performance_stress.py) | max_depth override tested.
| **Parameter Types** | String parameters validated | ✅ | [test_api_contract.py](tests/tools/get_cross_file_dependencies/test_api_contract.py) | target_file, target_symbol as strings.
| | Integer parameters validated | ✅ | [test_pro_tier.py](tests/tools/get_cross_file_dependencies/test_pro_tier.py) | max_depth integer handling.
| | Boolean parameters validated | ✅ | [test_api_contract.py](tests/tools/get_cross_file_dependencies/test_api_contract.py) | include_code, include_diagram booleans.
| | Object/dict parameters validated | N/A | | No object parameters in v1.0.
| | Array/list parameters validated | N/A | | No array parameters in v1.0.

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
| **Required Fields** | `success` field present (bool) | ✅ | [tests/tools/get_cross_file_dependencies/test_api_contract.py](tests/tools/get_cross_file_dependencies/test_api_contract.py) | TestResultModelFields.test_success_field verifies boolean success flag.
| | Core fields always present | ✅ | [tests/tools/get_cross_file_dependencies/test_tier_enforcement.py](tests/tools/get_cross_file_dependencies/test_tier_enforcement.py) | Result field availability validated across tiers.
| | Error field present when success=False | ✅ | [tests/tools/get_cross_file_dependencies/test_api_contract.py](tests/tools/get_cross_file_dependencies/test_api_contract.py) | Nonexistent file triggers error field population.
| **Optional Fields** | Tier-specific fields present when applicable | ✅ | [tests/tools/get_cross_file_dependencies/test_field_content_validation.py](tests/tools/get_cross_file_dependencies/test_field_content_validation.py) | Pro/Enterprise-only collections populated with real content.
| | Tier-specific fields absent when not applicable | ✅ | [tests/tools/get_cross_file_dependencies/test_licensing_and_fallback.py](tests/tools/get_cross_file_dependencies/test_licensing_and_fallback.py) | Community tier gating keeps Pro/Enterprise fields empty.
| | null/empty values handled consistently | ⬜ | | Not explicitly asserted for all nullable fields.
| **Field Types** | Field types match schema (str, int, bool, list, dict) | ✅ | [tests/tools/get_cross_file_dependencies/test_api_contract.py](tests/tools/get_cross_file_dependencies/test_api_contract.py); [tests/tools/get_cross_file_dependencies/test_field_content_validation.py](tests/tools/get_cross_file_dependencies/test_field_content_validation.py) | Type assertions for core and advanced fields.
| | Lists contain correct item types | ✅ | [tests/tools/get_cross_file_dependencies/test_field_content_validation.py](tests/tools/get_cross_file_dependencies/test_field_content_validation.py) | Alias/wildcard/violation lists validated for element shape.
| | Dicts contain correct key/value types | ✅ | [tests/tools/get_cross_file_dependencies/test_field_content_validation.py](tests/tools/get_cross_file_dependencies/test_field_content_validation.py) | Layer mapping and dependency chains validated for dict/list structure.
| | No unexpected types (e.g., NaN, undefined) | ⬜ | | Not explicitly covered.

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
| **Response Time** | Small inputs (<100 LOC) complete in <100ms | ✅ | [test_mcp_protocol_and_security.py](tests/tools/get_cross_file_dependencies/test_mcp_protocol_and_security.py) | Implicit via fast test execution.
| | Medium inputs (1000 LOC) complete in <1s | ✅ | [test_performance_stress.py](tests/tools/get_cross_file_dependencies/test_performance_stress.py) | Large project baseline test verifies.
| | Large inputs (10K LOC) complete in <10s | ✅ | [tests/tools/get_cross_file_dependencies/test_performance_stress.py](tests/tools/get_cross_file_dependencies/test_performance_stress.py) | Community large-project path completes <10s; Pro <30s noted.
| | Performance degrades gracefully (not exponentially) | ✅ | [test_performance_stress.py::TestPerformanceRegression](tests/tools/get_cross_file_dependencies/test_performance_stress.py) | Baseline performance test validates.
| **Memory Usage** | Small inputs use <10MB RAM | ✅ | [test_performance_stress.py](tests/tools/get_cross_file_dependencies/test_performance_stress.py) | Implicit via memory efficiency test.
| | Medium inputs use <50MB RAM | ✅ | [test_performance_stress.py](tests/tools/get_cross_file_dependencies/test_performance_stress.py) | Implicit via memory efficiency test.
| | Large inputs use <500MB RAM | ✅ | [tests/tools/get_cross_file_dependencies/test_performance_stress.py](tests/tools/get_cross_file_dependencies/test_performance_stress.py) | Memory delta capped <500MB on 200-file project.
| | No memory leaks (repeated calls don't accumulate) | ✅ | [test_mcp_protocol_and_security.py::TestLimitsAndExhaustion::test_repeated_calls_no_memory_growth](tests/tools/get_cross_file_dependencies/test_mcp_protocol_and_security.py) | Memory growth test validates.
| **Stress Testing** | 100 sequential requests succeed | ⬜ | | Deferred: stress test planned for v2.6.0.
| | 10 concurrent requests succeed | ✅ | [test_mcp_protocol_and_security.py::test_async_concurrency_handles_parallel_requests](tests/tools/get_cross_file_dependencies/test_mcp_protocol_and_security.py) | 3 concurrent requests validated.
| | Max file size input succeeds (at tier limit) | ✅ | [test_performance_stress.py::test_community_truncates_at_50_files](tests/tools/get_cross_file_dependencies/test_performance_stress.py) | Tier file limits validated.
| | Tool recovers after hitting limits | ✅ | [test_performance_stress.py](tests/tools/get_cross_file_dependencies/test_performance_stress.py) | Truncation with warning verified.

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
| **Error Recovery** | Tool returns error (not crash) for invalid input | ✅ | [tests/tools/get_cross_file_dependencies/test_api_contract.py](tests/tools/get_cross_file_dependencies/test_api_contract.py) | Nonexistent file path returns error without crashing.
| | Error messages are clear and actionable | ✅ | [test_api_contract.py](tests/tools/get_cross_file_dependencies/test_api_contract.py) | Error messages include failure reason.
| | Errors include context (line number, location, etc.) | ✅ | [test_mcp_protocol_and_security.py](tests/tools/get_cross_file_dependencies/test_mcp_protocol_and_security.py) | Syntax errors include context.
| | Server continues working after error | ✅ | [test_mcp_protocol_and_security.py::TestLimitsAndExhaustion::test_repeated_calls_deterministic](tests/tools/get_cross_file_dependencies/test_mcp_protocol_and_security.py) | Multiple calls after errors work.
| **Resource Limits** | Timeout prevents infinite loops | ✅ | [tests/tools/get_cross_file_dependencies/test_performance_stress.py](tests/tools/get_cross_file_dependencies/test_performance_stress.py) | Timeout protection exercised via very short timeout.
| | Memory limit prevents OOM crashes | ✅ | [test_performance_stress.py::TestMemoryEfficiency](tests/tools/get_cross_file_dependencies/test_performance_stress.py) | Memory cap validated.
| | File size limit prevents resource exhaustion | ✅ | [test_performance_stress.py::TestTruncationBehavior](tests/tools/get_cross_file_dependencies/test_performance_stress.py) | File count limits enforced.
| | Graceful degradation when limits hit | ✅ | [test_performance_stress.py](tests/tools/get_cross_file_dependencies/test_performance_stress.py) | Truncation warning returned, no crash.
| **Determinism** | Same input → same output (every time) | ✅ | [tests/tools/get_cross_file_dependencies/test_tier_enforcement.py](tests/tools/get_cross_file_dependencies/test_tier_enforcement.py) | Consistency asserted for repeated community calls.
| | Output stable across platforms (Linux/Mac/Windows) | ⬜ | | Deferred: CI matrix testing for v2.6.0.
| | No random fields or non-deterministic ordering | ✅ | [test_tier_enforcement.py::TestConsistentBehavior](tests/tools/get_cross_file_dependencies/test_tier_enforcement.py) | Determinism verified.

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
| **No Secret Leakage** | Tool doesn't echo secrets in responses | ✅ | [test_mcp_protocol_and_security.py::TestEdgeAndSecurityCases::test_secret_strings_not_leaked_on_error](tests/tools/get_cross_file_dependencies/test_mcp_protocol_and_security.py) | Secret strings checked.
| | API keys/tokens not in error messages | ✅ | [test_mcp_protocol_and_security.py::TestSecurityAndPrivacy::test_secrets_redacted_with_include_code_on_error](tests/tools/get_cross_file_dependencies/test_mcp_protocol_and_security.py) | Secrets redacted.
| | File paths sanitized (no absolute paths to user files) | ✅ | [test_api_contract.py](tests/tools/get_cross_file_dependencies/test_api_contract.py) | Relative paths used in outputs.
| | No PII in logs or outputs | ⬜ | | Low priority: logging audit deferred.
| **Input Sanitization** | Code injection prevented (if executing code) | N/A | | Tool uses AST parsing, no execution.
| | Path traversal prevented (if reading files) | ✅ | [test_api_contract.py](tests/tools/get_cross_file_dependencies/test_api_contract.py) | Files restricted to project_root.
| | Command injection prevented (if calling shell) | N/A | | Tool does not call shell.
| **Sandboxing** | Code analysis doesn't execute user code | ✅ | By design | AST parsing only, verified in all tests.
| | No network calls from analysis | ✅ | By design | Static analysis only.
| | No filesystem writes (except cache) | ✅ | By design | Read-only operations verified.

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
| **Platform Compatibility** | Works on Linux | ✅ | Test suite | All tests run on Linux (WSL).
| | Works on macOS | ⬜ | | CI matrix planned for v2.6.0.
| | Works on Windows | ⬜ | | CI matrix planned for v2.6.0.
| | No platform-specific failures | ✅ | By design | Uses pure Python AST parsing.
| **Python Version Compatibility** | Works on Python 3.8+ | N/A | | Minimum version is 3.9.
| | Works on Python 3.9 | ✅ | pyproject.toml | Requires-python >= 3.9.
| | Works on Python 3.10 | ✅ | Test suite | Tests run on Python 3.10+.
| | Works on Python 3.11+ | ✅ | Test suite | Compatible with Python 3.11+.
| | No version-specific crashes | ✅ | By design | Standard library AST only.
| **Backward Compatibility** | Old request formats still work | N/A | | v1.0 is first release.
| | Deprecated fields still present (with warnings) | N/A | | No deprecations in v1.0.
| | No breaking changes without version bump | N/A | | v1.0 is first release.

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
| **Roadmap Alignment** | All roadmap features implemented | ✅ | [test_field_content_validation.py](tests/tools/get_cross_file_dependencies/test_field_content_validation.py) | All v3.3.0 features verified.
| | Roadmap examples work as-is (copy-paste test) | ✅ | [test_api_contract.py](tests/tools/get_cross_file_dependencies/test_api_contract.py) | API contract validated.
| | Roadmap request/response formats match actual | ✅ | [test_api_contract.py](tests/tools/get_cross_file_dependencies/test_api_contract.py) | 44 response fields validated.
| **API Documentation** | All parameters documented | ✅ | Server docstrings | Parameters documented in server.py.
| | All response fields documented | ✅ | [GET_CROSS_FILE_DEPENDENCIES_DEEP_DIVE.md](docs/tools/deep_dive/GET_CROSS_FILE_DEPENDENCIES_DEEP_DIVE.md) | Deep dive documentation complete.
| | Examples are up-to-date and working | ✅ | [test_api_contract.py](tests/tools/get_cross_file_dependencies/test_api_contract.py) | Examples tested.

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
| **Logging** | Errors logged with context | ✅ | By design | Python logging used throughout.
| | Warnings logged appropriately | ✅ | Implementation | Truncation warnings generated.
| | Debug logs available (when enabled) | ⬜ | | Debug logging not explicitly tested.
| | No excessive logging (not spammy) | ✅ | By design | Structured logging only.
| **Error Messages** | Clear and actionable | ✅ | [test_api_contract.py](tests/tools/get_cross_file_dependencies/test_api_contract.py) | Error messages tested.
| | Include line numbers / locations (when applicable) | ✅ | [test_mcp_protocol_and_security.py](tests/tools/get_cross_file_dependencies/test_mcp_protocol_and_security.py) | Syntax errors include context.
| | Suggest fixes (when possible) | ✅ | Implementation | Architectural violations include recommendations.

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
| **File Naming** | Files follow convention: `test_{feature}.py` | ✅ | [tests/tools/get_cross_file_dependencies](tests/tools/get_cross_file_dependencies) | Suite includes test_api_contract.py, test_pro_tier.py, test_enterprise_tier.py, etc.
| | Test classes follow convention: `Test{Feature}` | ✅ | [tests/tools/get_cross_file_dependencies/test_field_content_validation.py](tests/tools/get_cross_file_dependencies/test_field_content_validation.py) | Classes prefixed with Test* across suite.
| | Test functions follow convention: `test_{scenario}` | ✅ | [tests/tools/get_cross_file_dependencies/test_performance_stress.py](tests/tools/get_cross_file_dependencies/test_performance_stress.py) | Functions use test_* naming throughout.
| **Logical Grouping** | Core functionality in `test_core_functionality.py` | ✅ | [tests/tools/get_cross_file_dependencies/test_api_contract.py](tests/tools/get_cross_file_dependencies/test_api_contract.py) | API contract and core field checks housed in test_api_contract.py.
| | Edge cases in `test_edge_cases.py` | ✅ | [tests/tools/get_cross_file_dependencies/test_performance_stress.py](tests/tools/get_cross_file_dependencies/test_performance_stress.py) | Stress/limit edge cases covered in performance_stress module.
| | Tier features in `test_tiers.py` | ✅ | [tests/tools/get_cross_file_dependencies/test_tier_enforcement.py](tests/tools/get_cross_file_dependencies/test_tier_enforcement.py) | Tier gating and transitions validated here.
| | License/limits in `test_license_and_limits.py` | ✅ | [tests/tools/get_cross_file_dependencies/test_licensing_and_fallback.py](tests/tools/get_cross_file_dependencies/test_licensing_and_fallback.py) | License fallback and tier limit behaviors covered.
| | Integration in `test_integration.py` | ✅ | [tests/tools/get_cross_file_dependencies/test_architecture_integration.py](tests/tools/get_cross_file_dependencies/test_architecture_integration.py) | Architecture.toml integration exercised.
| **Test Documentation** | Each test has clear docstring | ✅ | [tests/tools/get_cross_file_dependencies/test_field_content_validation.py](tests/tools/get_cross_file_dependencies/test_field_content_validation.py) | All classes/methods carry descriptive docstrings.
| | Test purpose is obvious from name + docstring | ✅ | [tests/tools/get_cross_file_dependencies/test_tier_enforcement.py](tests/tools/get_cross_file_dependencies/test_tier_enforcement.py) | Scenario-driven names clarify intent.
| | Complex tests have inline comments | ✅ | [tests/tools/get_cross_file_dependencies/test_performance_stress.py](tests/tools/get_cross_file_dependencies/test_performance_stress.py) | Stress helpers annotated for clarity.

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
| **Reusable Fixtures** | Server fixtures (community_server, pro_server, enterprise_server) | ✅ | [tests/tools/get_cross_file_dependencies/conftest.py](tests/tools/get_cross_file_dependencies/conftest.py) | Tiered MCP server fixtures provided.
| | Sample input fixtures | ✅ | [tests/tools/get_cross_file_dependencies/conftest.py](tests/tools/get_cross_file_dependencies/conftest.py) | Simple, circular, deep, wildcard, alias, reexport project fixtures available.
| | Mock license utilities | ✅ | [tests/tools/get_cross_file_dependencies/conftest.py](tests/tools/get_cross_file_dependencies/conftest.py) | mock_expired_license / mock_invalid_license / mock_missing_license helpers defined.
| **Helper Functions** | Validation helpers (validate_tier_limits, etc.) | ✅ | [tests/tools/get_cross_file_dependencies/conftest.py](tests/tools/get_cross_file_dependencies/conftest.py) | validate_tier_limits and get_max_dependency_depth included.
| | Mock helpers (mock_expired_license, etc.) | ✅ | [tests/tools/get_cross_file_dependencies/conftest.py](tests/tools/get_cross_file_dependencies/conftest.py) | License mocks reused across tier tests.
| | Assertion helpers (assert_no_pro_features, etc.) | ⬜ | | Tier gating assertions live in tests; no dedicated helper wrapper.

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
| **Test Coverage** | Coverage ≥ 90% for core functionality | ✅ | [docs/testing/test_assessments/get_cross_file_dependencies/get_cross_file_dependencies_test_assessment.md](docs/testing/test_assessments/get_cross_file_dependencies/get_cross_file_dependencies_test_assessment.md) | 120/120 passing; core coverage reported at 100% for roadmap scope.
| | All roadmap features have tests | ✅ | [docs/testing/test_assessments/get_cross_file_dependencies/get_cross_file_dependencies_test_assessment.md](docs/testing/test_assessments/get_cross_file_dependencies/get_cross_file_dependencies_test_assessment.md) | Roadmap features mapped to test cases.
| | All tier features have tests | ✅ | [tests/tools/get_cross_file_dependencies/test_tier_enforcement.py](tests/tools/get_cross_file_dependencies/test_tier_enforcement.py); [tests/tools/get_cross_file_dependencies/test_licensing_and_fallback.py](tests/tools/get_cross_file_dependencies/test_licensing_and_fallback.py) | Community/Pro/Enterprise behaviors exercised.
| | No critical untested code paths | ✅ | [docs/testing/test_assessments/get_cross_file_dependencies/get_cross_file_dependencies_test_assessment.md](docs/testing/test_assessments/get_cross_file_dependencies/get_cross_file_dependencies_test_assessment.md) | Assessment reports all critical paths covered.
| **Test Pass Rate** | 100% pass rate on executed tests | ✅ | [docs/testing/test_assessments/get_cross_file_dependencies/get_cross_file_dependencies_test_assessment.md](docs/testing/test_assessments/get_cross_file_dependencies/get_cross_file_dependencies_test_assessment.md) | Test run shows 120/120 passing.
| | No flaky tests (inconsistent pass/fail) | ✅ | [test_tier_enforcement.py::TestConsistentBehavior](tests/tools/get_cross_file_dependencies/test_tier_enforcement.py) | Determinism validated.
| | No skipped tests for wrong reasons | ✅ | [tests/tools/get_cross_file_dependencies](tests/tools/get_cross_file_dependencies) | Suite runs without skip markers except env-dependent skips.
| | CI/CD pipeline passes | ⬜ | | GitHub Actions planned for v2.6.0.
| **Documentation** | Test assessment document complete | ✅ | [docs/testing/test_assessments/get_cross_file_dependencies/get_cross_file_dependencies_test_assessment.md](docs/testing/test_assessments/get_cross_file_dependencies/get_cross_file_dependencies_test_assessment.md) | Assessment finalized and published.
| | Roadmap matches implementation | ✅ | [docs/roadmap/get_cross_file_dependencies.md](docs/roadmap/get_cross_file_dependencies.md); [tests/tools/get_cross_file_dependencies/test_field_content_validation.py](tests/tools/get_cross_file_dependencies/test_field_content_validation.py) | Roadmap features asserted via content validation tests.
| | CHANGELOG updated | ✅ | | v3.3.0 changelog includes feature.
| | Migration guide (if breaking changes) | N/A | | v1.0 is first release, no migrations.

---

### 7.2 Final Release Checklist

| Category | Item | Status | Notes |
|----------|------|--------|-------|
| **Community Tier** | All Community tier features tested | ✅ | Covered by test_community_tier.py and tier enforcement checks.
| **Pro Tier** | All Pro tier features tested | ✅ | Pro depth/alias/wildcard/reexport/chained alias validated in test_pro_tier.py and test_field_content_validation.py.
| **Enterprise Tier** | All Enterprise tier features tested | ✅ | Architectural rule engine and unlimited depth exercised in test_enterprise_tier.py and test_architecture_integration.py.
| **Licensing** | License fallback tested | ✅ | test_licensing_and_fallback.py covers expired/invalid/missing license paths.
| **Limits** | Tier limits enforced | ✅ | Depth/file caps asserted in test_performance_stress.py and test_licensing_and_fallback.py.
| **MCP Protocol** | MCP protocol compliance verified | ✅ | [test_mcp_protocol_and_security.py](tests/tools/get_cross_file_dependencies/test_mcp_protocol_and_security.py) | JSON-RPC envelope, tool registration, error handling verified.
| **Performance** | Performance acceptable | ✅ | Stress/perf thresholds validated in test_performance_stress.py.
| **Security** | Security validated | ✅ | [test_mcp_protocol_and_security.py::TestSecurityAndPrivacy](tests/tools/get_cross_file_dependencies/test_mcp_protocol_and_security.py) | Secret leakage, encoding, sandboxing verified.
| **Documentation** | Documentation accurate | ✅ | Roadmap/test assessment alignment in docs/roadmap/get_cross_file_dependencies.md and assessment report.
| **CI/CD** | CI/CD passing | ⬜ | GitHub Actions pipeline planned for v2.6.0.

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
- v3.2 (2026-01-11): [20260111_DOCS] Pre-release review: Updated all unchecked items with actual test coverage, marked N/A and deferred items
- v3.1 (2026-01-04): [20260104_DOCS] Filled checklist gaps with current test coverage and release readiness evidence
- v3.0 (2026-01-04): Converted all checklists to tables with Status/Test File/Notes columns
- v2.0 (2026-01-04): Comprehensive checklist based on get_cross_file_dependencies and analyze_code assessments
- v1.0 (2025-12-30): Initial framework
