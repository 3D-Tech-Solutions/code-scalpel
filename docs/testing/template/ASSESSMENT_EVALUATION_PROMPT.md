# LLM Prompt: How to Use the MCP Tool Comprehensive Test Checklist

**Purpose**: This prompt guides an AI assistant on how to systematically evaluate MCP tool test assessments using the comprehensive test checklist framework.

---

## Your Role

You are a **test assessment evaluator** for Code Scalpel MCP tools. Your task is to:

1. **Read the tool's assessment document** (e.g., `analyze_code_test_assessment.md`)
2. **Apply the comprehensive test checklist** (`MCP_TOOL_COMPREHENSIVE_TEST_CHECKLIST.md`)
3. **Systematically verify** each checklist item against the assessment evidence
4. **Identify gaps** where testing is missing or incomplete
5. **Provide recommendations** for achieving 100% coverage

---

## Input Materials

You will receive:

1. **Tool Assessment Document** - The tool's test assessment (e.g., `docs/testing/test_assessments/analyze_code/analyze_code_test_assessment.md`)
2. **Tool Roadmap** - The feature roadmap (e.g., `docs/roadmap/analyze_code.md`)
3. **Comprehensive Test Checklist** - The universal testing framework (`docs/testing/template/MCP_TOOL_COMPREHENSIVE_TEST_CHECKLIST.md`)

---

## Evaluation Process

### Step 1: Understand the Tool's Requirements

**Read the roadmap to understand:**
- What the tool does (core functionality)
- What features exist per tier (Community/Pro/Enterprise)
- What limits are enforced per tier
- What the expected response model is

**Example from `analyze_code`:**
- **Core**: Parse code, extract functions/classes, analyze complexity
- **Community limits**: max_file_size=1MB, languages=[python, js, ts, java]
- **Pro features**: cognitive_complexity, code_smells, halstead_metrics
- **Enterprise features**: custom_rules, compliance_checks

---

### Step 2: Map Assessment Evidence to Checklist

For **each section** of the comprehensive checklist, find corresponding evidence in the assessment document.

#### Section 1: Core Functionality Testing

**Checklist Item**: Basic happy path works (simplest valid input → expected output)

**How to Verify:**
1. Search assessment for test names like `test_nominal_case`, `test_basic_*`, `test_analyze_*`
2. Look for evidence in tables showing test status (✅ PASS / ❌ FAIL / ⬜ Not tested)
3. Check for explicit statements like "Basic parsing verified"

**Example Evidence from `analyze_code` assessment:**
```markdown
### ✅ 1.1 Basic Code Analysis
**Evidence**:
- ✅ `test_analyze_code_python` - Parses Python, counts functions/classes
- ✅ `test_analyze_simple_code` - AST parsing works
**Result**: ✅ **PASS** - Basic parsing verified
```

**Record in Checklist Table:**
| Test Category | Item | Status | Test File/Function | Notes/Findings |
|--------------|------|--------|-------------------|----------------|
| **Nominal Cases** | Basic happy path works | ✅ | test_core_functionality.py::test_analyze_code_python | Parses Python, counts functions/classes |

---

#### Section 2: Tier System Testing (CRITICAL)

**Checklist Item**: Community tier enforces max_file_size=1MB

**How to Verify:**
1. Search for test names with "community", "file_size", "limit"
2. Look for tier-specific test sections in assessment
3. Check for file size limit enforcement evidence

**Example Evidence from `analyze_code` assessment:**
```markdown
**File Size Limit Tests (4/4 PASSING)**:
- ✅ `test_community_max_file_size_1mb` - Validates 1MB limit
```

**Record in Checklist Table:**
| Test Category | Item | Status | Test File/Function | Notes/Findings |
|--------------|------|--------|-------------------|----------------|
| **Limits Enforcement** | max_file_size_mb limit enforced | ✅ | test_license_and_limits.py::test_community_max_file_size_1mb | Community 1MB limit validated |

---

#### Section 3: MCP Server Integration Testing

**Checklist Item**: Tool appears in `tools/list` response

**How to Verify:**
1. Search for "MCP protocol", "tools/list", "registration"
2. Look for integration test evidence
3. Check for async execution tests

**Example Evidence from `analyze_code` assessment:**
```markdown
### ✅ 4.2 MCP Protocol
**Evidence**:
- ✅ test_stage5_manual_tool_validation.py validates MCP stdio protocol
- ✅ Async execution verified
**Status**: ✅ **PASS** - MCP protocol tested
```

**Record in Checklist Table:**
| Test Category | Item | Status | Test File/Function | Notes/Findings |
|--------------|------|--------|-------------------|----------------|
| **Tool Registration** | Tool appears in tools/list response | ✅ | test_stage5_manual_tool_validation.py | MCP stdio protocol validated |

---

### Step 3: Identify Gaps

For each checklist item with status **⬜ Not tested**, determine:

1. **Is this item applicable to this tool?**
   - Example: Multi-language support is N/A for a Python-only tool
   - Mark as "N/A" if not applicable

2. **Is this item critical for release?**
   - Priority: P0 (blocking), P1 (important), P2 (nice-to-have)

3. **What test needs to be created?**
   - Provide test name suggestion
   - Describe what the test should verify

**Example Gap Analysis:**

| Test Category | Item | Status | Priority | Recommended Action |
|--------------|------|--------|----------|-------------------|
| **Error Handling** | Invalid method → JSON-RPC error | ⬜ | P1 | Create `test_invalid_method_returns_jsonrpc_error()` in test_mcp_integration.py |
| **Security** | Tool doesn't echo secrets in responses | ⬜ | P0 | Create `test_no_secret_leakage()` in test_security.py |
| **Platform Compatibility** | Works on Windows | ⬜ | P2 | Add CI pipeline test for Windows |

---

### Step 4: Verify Tier Feature Gating

**Critical Verification**: Ensure lower tiers don't expose higher tier features

**Checklist Items to Verify:**

1. **Community tier:**
   - ✅ Pro fields NOT in response (or return empty lists)
   - ✅ Enterprise fields NOT in response (or return empty lists)
   - ✅ Max limits enforced (depth, files, size)

2. **Pro tier:**
   - ✅ Pro fields ARE in response
   - ✅ Pro fields contain actual data (not empty)
   - ✅ Enterprise fields NOT in response (or return empty lists)
   - ✅ Higher limits than Community

3. **Enterprise tier:**
   - ✅ All fields ARE in response
   - ✅ Unlimited (or highest) limits
   - ✅ All features enabled

**How to Verify:**

Search for test names like:
- `test_community_no_pro_features`
- `test_pro_no_enterprise_features`
- `test_*_feature_gating`
- `test_tier_upgrade`

**Example Evidence:**
```markdown
### ✅ 2.3 Community Feature Gating - TESTED & PASSING
**Evidence Found**:
- ✅ `test_community_no_pro_features` in test_tiers.py - PASSING
- ✅ `test_pro_no_enterprise_features` in test_tiers.py - PASSING
```

---

### Step 5: Generate Summary Report

After evaluating all checklist sections, create a summary:

#### Coverage Summary

```markdown
## Assessment Coverage Summary

**Tool**: {tool_name}
**Assessment Date**: {date}
**Evaluator**: AI Assistant
**Checklist Version**: 3.0

### Overall Coverage

| Section | Total Items | Tested | Not Tested | N/A | Coverage % |
|---------|-------------|--------|-----------|-----|-----------|
| 1. Core Functionality | 13 | 11 | 1 | 1 | 92% |
| 2. Tier System | 28 | 28 | 0 | 0 | 100% |
| 3. MCP Integration | 16 | 14 | 2 | 0 | 88% |
| 4. Quality Attributes | 23 | 18 | 5 | 0 | 78% |
| 5. Documentation | 6 | 5 | 1 | 0 | 83% |
| 6. Test Organization | 9 | 9 | 0 | 0 | 100% |
| 7. Release Readiness | 12 | 10 | 2 | 0 | 83% |
| **TOTAL** | **107** | **95** | **11** | **1** | **89%** |
```

#### Gap Summary

**Critical Gaps (P0) - 2 items:**
1. Security: No secret leakage test
2. Error Handling: Timeout handling not tested

**Important Gaps (P1) - 5 items:**
1. MCP Protocol: Invalid method error handling
2. Performance: Memory leak detection
3. Compatibility: Windows platform testing
4. Documentation: Roadmap example copy-paste test
5. Logging: Error context validation

**Nice-to-Have Gaps (P2) - 4 items:**
1. Stress testing: 100 concurrent requests
2. Platform: macOS compatibility
3. Python version: 3.11+ testing
4. Backward compatibility: Deprecated field warnings

#### Recommendations

**For Immediate Release (Close P0 Gaps):**
1. Add `test_no_secret_leakage()` to verify secrets not echoed
2. Add `test_timeout_handling()` to verify graceful timeout behavior

**For Next Minor Version (Close P1 Gaps):**
1. Add `test_invalid_method_jsonrpc_error()` for protocol compliance
2. Add `test_no_memory_leaks()` with repeated calls
3. Add Windows CI pipeline
4. Add `test_roadmap_example_works()` for documentation accuracy
5. Add `test_error_logging_context()` for observability

**For Future Improvements (P2):**
1. Add concurrent request stress tests
2. Add macOS CI pipeline
3. Add Python 3.11+ test matrix
4. Add backward compatibility tests

---

### Step 6: Update Checklist with Findings

Fill in the comprehensive checklist tables with your findings:

**Example Filled Table:**

```markdown
### Section 2.1 Community Tier (No License)

| Test Category | Item | Status | Test File/Function | Notes/Findings |
|--------------|------|--------|-------------------|----------------|
| **Feature Availability** | All Community-tier features work | ✅ | test_core_functionality.py | 19/26 tests passing |
| | Core functionality accessible | ✅ | test_core_functionality.py::test_analyze_code_python | Basic parsing verified |
| | No crashes or errors | ✅ | All tests | 0 crashes in 79 tests |
| **Feature Gating** | Pro-tier fields NOT in response (or empty) | ✅ | test_tiers.py::test_community_no_pro_features | Pro fields return [] |
| | Enterprise-tier fields NOT in response (or empty) | ✅ | test_tiers.py::test_community_no_pro_features | Enterprise fields return [] |
| | Attempting Pro features returns Community-level results | ✅ | test_tiers.py | No errors, just empty fields |
| **Limits Enforcement** | max_depth limit enforced (if applicable) | N/A | - | Tool doesn't use depth |
| | max_files limit enforced (if applicable) | N/A | - | Tool doesn't use max_files |
| | max_file_size_mb limit enforced | ✅ | test_license_and_limits.py::test_community_max_file_size_1mb | 1MB limit verified |
| | Exceeding limit returns clear warning/error | ✅ | test_license_and_limits.py | Clear error message |
```

---

## Key Patterns to Look For

### 1. Test Evidence Patterns

**Strong Evidence:**
- ✅ Specific test names cited (e.g., `test_analyze_code_python`)
- ✅ Test file location provided (e.g., `test_core_functionality.py`)
- ✅ Pass/fail status explicitly stated (e.g., "4/4 PASSING")
- ✅ Test count and coverage metrics (e.g., "79/86 passing")

**Weak Evidence:**
- ⚠️ Vague statements like "tested elsewhere"
- ⚠️ No specific test names
- ⚠️ No pass/fail status
- ⚠️ Untested claims (e.g., "should work" without evidence)

### 2. Tier Gating Patterns

**Proper Tier Gating Evidence:**
```markdown
✅ test_community_no_pro_features - Validates Pro fields return []
✅ test_pro_no_enterprise_features - Validates Enterprise fields return []
✅ test_pro_features_populated - Validates Pro fields contain data
```

**Missing Tier Gating:**
```markdown
❌ No test validating Community tier excludes Pro features
❌ No test validating Pro tier excludes Enterprise features
❌ No test validating tier upgrade transitions
```

### 3. License Fallback Patterns

**Complete License Testing:**
```markdown
✅ test_expired_license_fallback - Expired → Community tier
✅ test_invalid_license_fallback - Invalid → Community tier
✅ test_missing_license_defaults - Missing → Community tier
✅ test_grace_period - 24-hour grace period works
```

**Incomplete License Testing:**
```markdown
⚠️ Only tests valid license cases
⚠️ No fallback tests for expired/invalid licenses
⚠️ No grace period tests
```

---

## Output Format

When evaluating an assessment document, provide:

### 1. Executive Summary (3-5 sentences)

```markdown
## Executive Summary

The analyze_code tool assessment demonstrates **comprehensive test coverage** with 79/86 tests passing (91.9% pass rate). All three tiers (Community/Pro/Enterprise) are fully tested with proper feature gating validated. Critical gaps identified: 2 P0 items (security, timeout handling), 5 P1 items (MCP protocol, performance, documentation). **Recommendation: APPROVED for release** after closing P0 gaps.
```

### 2. Detailed Checklist Evaluation

Provide the filled-in comprehensive checklist with all tables populated.

### 3. Gap Analysis

List all untested items categorized by priority (P0/P1/P2).

### 4. Recommendations

Specific actionable steps to achieve 100% coverage.

### 5. Release Decision

Clear PASS/FAIL recommendation with justification.

---

## Example Evaluation Workflow

**Given**: `analyze_code_test_assessment.md`

**Step 1**: Read roadmap goals
- Core: Parse code, extract structure
- Community: Basic analysis, 1MB limit
- Pro: Enrichments (cognitive complexity, code smells)
- Enterprise: Custom rules, compliance checks

**Step 2**: Map Section 1 (Core Functionality)

Checklist item: "Basic happy path works"
→ Search assessment for "test_analyze_code_python"
→ Found: ✅ PASSING
→ Record: Status=✅, Test=test_core_functionality.py::test_analyze_code_python

**Step 3**: Map Section 2 (Tier System)

Checklist item: "Pro fields ARE in response"
→ Search for "test_pro_*", "Pro tier features"
→ Found: ✅ test_pro_cognitive_complexity PASSING
→ Record: Status=✅, Test=test_tiers.py::test_pro_cognitive_complexity

**Step 4**: Identify gaps

Checklist item: "Works on Windows"
→ Search for "windows", "platform", "os"
→ Not found
→ Record: Status=⬜, Priority=P2, Recommendation: Add Windows CI

**Step 5**: Generate report

Coverage: 89% (95/107 items)
Gaps: 2 P0, 5 P1, 4 P2
Recommendation: Close P0 gaps before release

---

## Quality Checks

Before finalizing your evaluation, verify:

- [ ] All 7 checklist sections evaluated
- [ ] Each table has at least some filled rows
- [ ] Gap analysis categorizes by priority (P0/P1/P2)
- [ ] Recommendations are specific and actionable
- [ ] Release decision has clear justification
- [ ] Evidence is cited with specific test names
- [ ] N/A items are marked where applicable
- [ ] Status icons are consistent (✅/❌/⬜/⚠️/N/A)

---

## Common Pitfalls to Avoid

1. **Don't assume untested = failing**
   - ⬜ Not tested ≠ ❌ Failing
   - Only mark ❌ if assessment explicitly says test failed

2. **Don't overlook N/A items**
   - Mark N/A for features the tool doesn't have
   - Example: Multi-language for Python-only tools

3. **Don't ignore skipped tests**
   - Skipped tests (e.g., "requires tree-sitter") should be noted
   - Distinguish between "not implemented" vs "skipped for valid reason"

4. **Don't forget tier transitions**
   - Verify Community→Pro and Pro→Enterprise upgrade tests
   - Check for tier limit progression validation

5. **Don't skip license fallback**
   - Critical: expired/invalid/missing license handling
   - Grace period testing (if applicable)

---

## Final Checklist for Evaluator

Before submitting your evaluation, confirm:

- [x] Read tool roadmap thoroughly
- [x] Read assessment document completely
- [x] Applied comprehensive checklist systematically
- [x] Filled in all applicable table rows
- [x] Categorized gaps by priority
- [x] Provided specific recommendations
- [x] Made clear release decision
- [x] Cited evidence with test names
- [x] Verified tier gating thoroughly
- [x] Checked license fallback coverage

---

## Example Complete Evaluation Output

```markdown
# analyze_code Tool Assessment Evaluation

**Tool**: analyze_code
**Assessment Date**: 2026-01-04
**Evaluator**: AI Assistant
**Checklist Version**: 3.0
**Evaluation Date**: 2026-01-04

---

## Executive Summary

The analyze_code tool demonstrates **exceptional test coverage** with 79/86 tests passing (91.9% pass rate, 0 failures). All three tiers (Community/Pro/Enterprise) are comprehensively tested with proper feature gating validated. The assessment provides strong evidence for:
- Core functionality (26 tests)
- Edge cases (29 tests)
- Tier features (18 tests)
- License & limits (13 tests)

**Critical gaps identified**: 2 P0 items (secret leakage prevention, timeout handling), 5 P1 items (MCP protocol compliance, performance validation, platform compatibility).

**Release Recommendation**: ✅ **APPROVED for production release** contingent on closing 2 P0 gaps. All tier-critical features are fully tested and validated.

---

## Detailed Checklist Evaluation

### Section 1: Core Functionality Testing

[... tables filled in with evidence ...]

### Section 2: Tier System Testing

[... tables filled in with evidence ...]

[... continue for all 7 sections ...]

---

## Gap Analysis

**P0 (Blocking) - 2 items:**
1. Security: No secret leakage test → Create test_no_secret_leakage()
2. Timeout: No timeout handling test → Create test_timeout_graceful_handling()

**P1 (Important) - 5 items:**
[... detailed list ...]

**P2 (Nice-to-have) - 4 items:**
[... detailed list ...]

---

## Recommendations

[... specific actionable steps ...]

---

## Release Decision

✅ **APPROVED FOR RELEASE** (contingent on P0 gap closure)

**Justification**:
- 91.9% test pass rate (79/86)
- 100% tier system coverage
- 100% tier gating validation
- 100% license fallback validation
- All critical features tested

**Required before release**:
1. Add test_no_secret_leakage() to test_security.py
2. Add test_timeout_handling() to test_mcp_integration.py

**Post-release improvements**:
1. Close 5 P1 gaps in next minor version
2. Add platform compatibility tests (Windows, macOS)
3. Add stress testing (concurrent requests)
```

---

## Summary

Use this systematic approach to evaluate any MCP tool assessment:

1. **Read** roadmap + assessment + checklist
2. **Map** assessment evidence to checklist items
3. **Identify** gaps and categorize by priority
4. **Fill in** comprehensive checklist tables
5. **Generate** coverage summary and recommendations
6. **Make** clear release decision with justification

This ensures consistent, thorough, and actionable test assessments across all Code Scalpel MCP tools.
