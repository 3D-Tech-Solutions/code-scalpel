# [20260103_DOCS] Test Suite for `update_symbol` MCP Tool

## Overview

Comprehensive test suite for the `update_symbol` tool covering all tier features, edge cases, error handling, and response model validation. This suite ensures the tool meets production quality standards across Community, Pro, and Enterprise license tiers.

**Test Coverage:**
- ✅ 20 Community tier tests
- ✅ 20 Pro tier tests
- ✅ 18 Enterprise tier tests
- ✅ 26 Edge case tests
- ✅ 28 Response model field gating tests
- ✅ 15 Error handling tests
- ✅ 8 License handling tests
- **Total: 155 comprehensive test cases**

## Directory Structure

```
tests/tools/update_symbol/
├── conftest.py                    # Shared fixtures, factories, assertion helpers
├── fixtures/
│   ├── sample_functions.py        # 12 Python function patterns for testing
│   └── sample_classes.py          # 9 Python class patterns for testing
├── test_community_tier.py         # 20 tests: basic ops, backup, syntax, session limit
├── test_pro_tier.py               # 20 tests: unlimited, multi-file, rollback, imports
├── test_enterprise_tier.py        # 18 tests: approval, compliance, audit, policy
├── test_edge_cases.py             # 26 tests: async, decorators, nested, lambdas
├── test_response_model_gating.py  # 28 tests: tier-specific field exposure
├── test_license_handling.py       # 8 tests: license lifecycle, expiry, fallback
├── test_error_handling.py         # 15 tests: syntax errors, file errors, permissions
└── README.md                      # This file
```

## Test Files and Their Purpose

### conftest.py (Shared Fixtures)

Provides reusable fixtures and assertion helpers for all test files:

**File/Project Fixtures:**
- `temp_python_file` - Creates temporary Python file for testing
- `temp_js_file` - Creates temporary JavaScript file for testing
- `temp_multifile_project` - Creates multi-file project structure for atomic update tests

**License Fixtures:**
- `mock_community_license` - Valid Community tier JWT token
- `mock_pro_license` - Valid Pro tier JWT token
- `mock_enterprise_license` - Valid Enterprise tier JWT token
- `mock_expired_license` - Expired JWT token
- `mock_invalid_license` - Malformed JWT token

**Mock Result Fixtures:**
- `update_result_community` - Expected Community tier response structure
- `update_result_pro` - Expected Pro tier response structure
- `update_result_enterprise` - Expected Enterprise tier response structure

**Tier Configuration Fixtures:**
- `tier_config_community` - Community tier configuration with session limits
- `tier_config_pro` - Pro tier configuration with unlimited updates
- `tier_config_enterprise` - Enterprise tier configuration with approval workflows

**Assertion Helpers:**
- `assert_result_has_community_fields` - Validates Community response structure
- `assert_result_has_pro_fields` - Validates Pro response structure
- `assert_result_has_enterprise_fields` - Validates Enterprise response structure

### fixtures/sample_functions.py

Contains reusable Python function patterns for mutation testing:

- `simple_function` - Basic function with docstring
- `type_hinted_function` - Function with type hints
- `async_function` - Async function definition
- `function_with_decorator` - Function with @decorator
- `function_with_staticmethod` - @staticmethod in class
- `function_with_classmethod` - @classmethod in class
- `nested_functions` - Outer and inner functions
- `lambda_assignment` - Lambda assigned to variable
- `function_with_complex_docstring` - Multiline docstring with Args/Returns/Raises
- `function_with_inline_comments` - Function with inline comments
- `generator_function` - Function with yield statement
- `function_with_varargs` - Function with *args, **kwargs

Use these fixtures to test mutation patterns without modifying test code.

### fixtures/sample_classes.py

Contains reusable Python class patterns for class/method testing:

- `SimpleClass` - Basic class with methods
- `ClassWithStaticMethods` - @staticmethod and @classmethod
- `ClassWithProperties` - @property decorators
- `InheritedClass` - Class inheritance patterns
- `ClassWithAsyncMethods` - Async method definitions
- `ClassWithSpecialMethods` - __str__, __repr__, __eq__, etc.
- `ChildClassOverride` - Overridden parent methods
- `ClassWithPrivateMembers` - _private attributes and __dunder__ methods
- `ComplexClass` - Multiple features combined

## Test File Organization

### test_community_tier.py (20 tests)

Tests Community tier features and limitations:

**Test Classes:**
1. `TestUpdateSymbolCommunityBasicOperations` (3 tests)
   - `test_replace_function_single_symbol` - Basic function replacement
   - `test_replace_class_single_symbol` - Basic class replacement
   - `test_replace_method_single_symbol` - Basic method replacement

2. `TestUpdateSymbolCommunityBackupCreation` (2 tests)
   - `test_backup_created_before_modification` - Mandatory backup creation
   - `test_no_backup_on_error` - Backup not created if operation fails

3. `TestUpdateSymbolCommunitySyntaxValidation` (2 tests)
   - `test_syntax_error_rejected` - Syntax errors prevent update
   - `test_valid_code_accepted` - Valid code is applied

4. `TestUpdateSymbolCommunitySessionLimit` (3 tests)
   - `test_session_limit_10_updates` - Allows exactly 10 updates per session
   - `test_session_limit_enforced_on_11th` - Rejects 11th update
   - `test_session_limit_error_message_suggests_upgrade` - Error message offers Pro upgrade path

5. `TestUpdateSymbolCommunityReturnModel` (2 tests)
   - `test_return_model_excludes_pro_fields` - Pro fields not in response
   - `test_return_model_includes_required_fields` - All Community fields present

6. `TestUpdateSymbolCommunityLicenseHandling` (2 tests)
   - `test_missing_license_defaults_to_community` - Absence of license = Community tier
   - `test_invalid_license_fallback` - Invalid JWT tokens = Community tier

7. `TestUpdateSymbolCommunityMultipleLanguages` (2 tests)
   - `test_python_file_update` - Python .py file support
   - `test_javascript_file_update` - JavaScript .js file support

8. `TestUpdateSymbolCommunityErrorHandling` (2 tests)
   - `test_symbol_not_found` - Clear error when symbol missing
   - `test_invalid_file_path` - Clear error when file not found

### test_pro_tier.py (20 tests)

Tests Pro tier features (unlimited updates, multi-file atomic, imports, formatting):

**Test Classes:**
1. `TestUpdateSymbolProLicenseVerification` (2 tests)
   - `test_pro_license_required` - Pro features blocked without valid license
   - `test_pro_license_grants_features` - Valid license enables Pro features

2. `TestUpdateSymbolProUnlimitedUpdates` (2 tests)
   - `test_15_updates_allowed` - More than 10 updates in single session
   - `test_100_update_session` - Stress test: 100 updates in session

3. `TestUpdateSymbolProMultifileAtomic` (2 tests)
   - `test_atomic_multi_file_update` - Multiple files updated atomically
   - `test_rollback_on_failure` - All-or-nothing: failure reverts all changes

4. `TestUpdateSymbolProRollback` (2 tests)
   - `test_rollback_available_field` - Response includes rollback_available
   - `test_rollback_procedure` - Rollback can be invoked to revert changes

5. `TestUpdateSymbolProImportAdjustment` (3 tests)
   - `test_imports_adjusted_field` - Response tracks import changes
   - `test_auto_add_required_imports` - New imports added automatically
   - `test_auto_remove_unused_imports` - Obsolete imports removed automatically

6. `TestUpdateSymbolProFormattingPreserved` (3 tests)
   - `test_formatting_preserved_field` - Response indicates formatting maintained
   - `test_indentation_preserved` - Original indentation style preserved
   - `test_comments_preserved` - Inline and block comments maintained

7. `TestUpdateSymbolProReturnModel` (2 tests)
   - `test_return_model_includes_pro_fields` - All Pro fields in response
   - `test_return_model_excludes_enterprise_fields` - Enterprise fields excluded

8. `TestUpdateSymbolProExpiredLicense` (1 test)
   - `test_expired_pro_license_fallback_to_community` - Expired Pro = Community tier

9. `TestUpdateSymbolProMultipleLanguages` (1 test)
   - `test_multi_file_python_atomic_update` - Python multi-file atomic operations

### test_enterprise_tier.py (18 tests)

Tests Enterprise tier features (approval, compliance, audit, policy):

**Test Classes:**
1. `TestUpdateSymbolEnterpriseLicenseVerification` (2 tests)
   - `test_enterprise_license_required` - Enterprise features blocked without license
   - `test_enterprise_license_grants_features` - Valid license enables Enterprise features

2. `TestUpdateSymbolEnterpriseApprovalWorkflow` (3 tests)
   - `test_approval_required_for_public_api` - Public API changes need approval
   - `test_approval_granted_allows_update` - Approved changes are applied
   - `test_approval_denied_blocks_update` - Rejected changes are blocked

3. `TestUpdateSymbolEnterpriseComplianceCheck` (2 tests)
   - `test_compliance_passed_allows_update` - Compliant changes are applied
   - `test_compliance_failed_blocks_update` - Non-compliant changes are blocked

4. `TestUpdateSymbolEnterpriseAuditTrail` (2 tests)
   - `test_audit_id_generated` - Each update gets unique audit_id
   - `test_audit_metadata_structure` - Audit trail contains user, timestamp, changes

5. `TestUpdateSymbolEnterprisePolicyEnforcement` (2 tests)
   - `test_policy_blocks_violation` - Custom policy blocks prohibited changes
   - `test_policy_allows_permitted_update` - Custom policy allows permitted changes

6. `TestUpdateSymbolEnterpriseReturnModel` (1 test)
   - `test_return_model_includes_all_fields` - All tier fields present in response

7. `TestUpdateSymbolEnterpriseMultipleLanguages` (1 test)
   - `test_python_and_javascript_support` - Enterprise features work across languages

8. `TestUpdateSymbolEnterpriseExpiredLicense` (1 test)
   - `test_expired_enterprise_license_fallback_to_pro` - Expired Enterprise = Pro tier

### test_edge_cases.py (26 tests)

Tests edge cases and language feature robustness:

**Test Classes:**
1. `TestUpdateSymbolAsyncFunctions` (2 tests)
   - `test_async_function_replacement` - Replace async function definition
   - `test_async_method_replacement` - Replace async method in class

2. `TestUpdateSymbolDecoratedFunctions` (3 tests)
   - `test_single_decorator_replacement` - Replace @decorator function
   - `test_multiple_decorators_replacement` - Replace @decorator1 @decorator2 function
   - `test_property_decorator_replacement` - Replace @property method

3. `TestUpdateSymbolNestedFunctions` (2 tests)
   - `test_outer_function_replacement` - Replace outer function
   - `test_inner_function_fails_gracefully` - Inner functions cannot be replaced (scoping)

4. `TestUpdateSymbolStaticAndClassMethods` (2 tests)
   - `test_staticmethod_replacement` - Replace @staticmethod
   - `test_classmethod_replacement` - Replace @classmethod

5. `TestUpdateSymbolLambdaAssignments` (1 test)
   - `test_lambda_assignment_fails_gracefully` - Lambda assignments are not supported

6. `TestUpdateSymbolInheritance` (2 tests)
   - `test_parent_class_method_replacement` - Replace parent class method
   - `test_child_class_method_override_replacement` - Replace overridden method

7. `TestUpdateSymbolComplexDocstrings` (1 test)
   - `test_multiline_docstring_preservation` - Preserve complex docstrings with Args/Returns

8. `TestUpdateSymbolLineNumberAccuracy` (1 test)
   - `test_lines_changed_accurate` - Reported line count matches actual changes

9. `TestUpdateSymbolSpecialMethods` (1 test)
   - `test_special_method_replacement` - Replace __str__, __repr__, etc.

### test_response_model_gating.py (28 tests)

Tests tier-specific response field exposure (prevents data leakage):

**Test Classes:**
1. `TestResponseModelFieldGatingCommunity` (3 tests)
   - `test_community_excludes_pro_fields` - Pro fields not in Community response
   - `test_community_excludes_enterprise_fields` - Enterprise fields not in response
   - `test_community_includes_required_fields` - All Community fields present

2. `TestResponseModelFieldGatingPro` (3 tests)
   - `test_pro_includes_pro_fields` - Pro-specific fields included
   - `test_pro_excludes_enterprise_fields` - Enterprise fields not in Pro response
   - `test_pro_includes_community_fields` - Community fields still present

3. `TestResponseModelFieldGatingEnterprise` (3 tests)
   - `test_enterprise_includes_enterprise_fields` - All Enterprise fields present
   - `test_enterprise_includes_pro_fields` - Pro fields inherited
   - `test_enterprise_includes_community_fields` - Community fields inherited

4. `TestComplianceCheckStructure` (2 tests)
   - `test_compliance_check_passed_structure` - Correct structure when passed=True
   - `test_compliance_check_failed_structure` - Correct structure when passed=False with violations

5. `TestImportAdjustmentStructure` (3 tests)
   - `test_import_added_action` - Import addition structure
   - `test_import_removed_action` - Import removal structure
   - `test_import_updated_action` - Import update structure

### test_license_handling.py (8 tests)

Tests license lifecycle, expiry, and tier fallback:

**Test Classes:**
1. `TestLicenseValidation` (2 tests)
   - `test_valid_license_token_accepted` - Valid JWT tokens work
   - `test_invalid_jwt_token_rejected` - Malformed tokens are rejected

2. `TestLicenseExpiry` (2 tests)
   - `test_expired_license_detected` - Expired tokens are detected
   - `test_expired_pro_fallback_to_community` - Expired Pro = Community tier

3. `TestLicenseTierFallback` (2 tests)
   - `test_missing_license_defaults_to_community` - No license = Community tier
   - `test_invalid_license_fallback_to_community` - Invalid license = Community tier

4. `TestLicenseRefresh` (1 test)
   - `test_new_valid_license_enables_tier_features` - New token enables features

5. `TestLicenseErrorMessages` (1 test)
   - `test_expired_license_error_message_actionable` - Clear message with renewal guidance

### test_error_handling.py (15 tests)

Tests error conditions and error message quality:

**Test Classes:**
1. `TestUpdateSymbolSyntaxErrors` (3 tests)
   - `test_syntax_error_invalid_indentation` - Indentation errors rejected
   - `test_syntax_error_missing_colon` - Missing colons detected
   - `test_syntax_error_unmatched_bracket` - Bracket mismatches detected

2. `TestUpdateSymbolSymbolNotFound` (3 tests)
   - `test_function_not_found` - Clear error when function missing
   - `test_class_not_found` - Clear error when class missing
   - `test_method_not_found` - Clear error when method missing

3. `TestUpdateSymbolFileNotFound` (2 tests)
   - `test_file_does_not_exist` - Clear error for missing file
   - `test_file_is_directory` - Error when path is directory

4. `TestUpdateSymbolInvalidFileType` (1 test)
   - `test_unsupported_file_extension` - Error for unsupported file types

5. `TestUpdateSymbolPermissionErrors` (2 tests)
   - `test_file_not_writable` - Permission denied for read-only files
   - `test_backup_directory_not_writable` - Permission denied for backup directory

6. `TestUpdateSymbolMissingSymbolType` (1 test)
   - `test_invalid_symbol_type` - Error for invalid symbol_type parameter

7. `TestUpdateSymbolTypeMismatch` (2 tests)
   - `test_symbol_type_function_but_is_class` - Type mismatch detection
   - `test_symbol_type_class_but_is_function` - Type mismatch detection

8. `TestUpdateSymbolInvalidNewCode` (2 tests)
   - `test_new_code_is_empty` - Empty code rejected
   - `test_new_code_is_none` - None code rejected

9. `TestUpdateSymbolErrorMessages` (2 tests)
   - `test_error_message_is_actionable` - Errors are helpful and actionable
   - `test_error_message_includes_context` - Errors include helpful context

## Running the Tests

### Run All Tests
```bash
pytest tests/tools/update_symbol/ -v
```

### Run Specific Tier Tests
```bash
# Community tier only
pytest tests/tools/update_symbol/test_community_tier.py -v

# Pro tier only
pytest tests/tools/update_symbol/test_pro_tier.py -v

# Enterprise tier only
pytest tests/tools/update_symbol/test_enterprise_tier.py -v
```

### Run Specific Test Category
```bash
# Edge cases only
pytest tests/tools/update_symbol/test_edge_cases.py -v

# Response model validation
pytest tests/tools/update_symbol/test_response_model_gating.py -v

# License handling
pytest tests/tools/update_symbol/test_license_handling.py -v

# Error handling
pytest tests/tools/update_symbol/test_error_handling.py -v
```

### Run Single Test Class
```bash
pytest tests/tools/update_symbol/test_community_tier.py::TestUpdateSymbolCommunitySessionLimit -v
```

### Run Single Test
```bash
pytest tests/tools/update_symbol/test_community_tier.py::TestUpdateSymbolCommunitySessionLimit::test_session_limit_enforced_on_11th -v
```

### Run with Coverage
```bash
pytest tests/tools/update_symbol/ --cov=src/code_scalpel/mcp/server --cov-report=html
```

### Run in Parallel (faster)
```bash
pytest tests/tools/update_symbol/ -v -n auto
```

## Test Mapping to Roadmap

Tests directly validate features from the `update_symbol` roadmap entry:

| Roadmap Feature | Test File | Test Count | Coverage |
|---|---|---|---|
| **Community Tier** |  |  |  |
| Basic single-symbol replacement | test_community_tier.py | 3 | ✅ Complete |
| Session limit (10 updates) | test_community_tier.py | 3 | ✅ Complete |
| Mandatory backup creation | test_community_tier.py | 2 | ✅ Complete |
| Syntax validation | test_community_tier.py | 2 | ✅ Complete |
| Return model field gating | test_response_model_gating.py | 3 | ✅ Complete |
| **Pro Tier** |  |  |  |
| Unlimited updates | test_pro_tier.py | 2 | ✅ Complete |
| Atomic multi-file operations | test_pro_tier.py | 2 | ✅ Complete |
| Rollback capability | test_pro_tier.py | 2 | ✅ Complete |
| Import auto-adjustment | test_pro_tier.py | 3 | ✅ Complete |
| Formatting preservation | test_pro_tier.py | 3 | ✅ Complete |
| Return model field gating | test_response_model_gating.py | 3 | ✅ Complete |
| **Enterprise Tier** |  |  |  |
| Approval workflows | test_enterprise_tier.py | 3 | ✅ Complete |
| Compliance validation | test_enterprise_tier.py | 2 | ✅ Complete |
| Audit trails | test_enterprise_tier.py | 2 | ✅ Complete |
| Custom validation rules | test_enterprise_tier.py | 2 | ✅ Complete |
| Return model field gating | test_response_model_gating.py | 3 | ✅ Complete |
| **Edge Cases** |  |  |  |
| Async functions | test_edge_cases.py | 2 | ✅ Complete |
| Decorators | test_edge_cases.py | 3 | ✅ Complete |
| Nested functions | test_edge_cases.py | 2 | ✅ Complete |
| Static/Class methods | test_edge_cases.py | 2 | ✅ Complete |
| Lambdas | test_edge_cases.py | 1 | ✅ Complete |
| Inheritance | test_edge_cases.py | 2 | ✅ Complete |
| Complex docstrings | test_edge_cases.py | 1 | ✅ Complete |
| Special methods | test_edge_cases.py | 1 | ✅ Complete |
| **License/Error Handling** |  |  |  |
| License validation | test_license_handling.py | 8 | ✅ Complete |
| Error messages | test_error_handling.py | 15 | ✅ Complete |

## Test Infrastructure

### Fixture Patterns

All test files use fixtures from `conftest.py`:

**Creating Test Files:**
```python
# Use file fixtures for basic tests
async def test_update_function(self, temp_python_file):
    temp_python_file.write("def old_func(): pass")
    result = update_symbol(
        file_path=temp_python_file,
        symbol_name="old_func",
        new_code="def old_func(): return 42"
    )
    assert result["success"] is True

# Use license fixtures for tier tests
async def test_pro_feature(self, mock_pro_license):
    result = update_symbol(
        file_path="/src/utils.py",
        symbol_name="func",
        new_code="new code",
        license_token=mock_pro_license  # Unlocks Pro features
    )
    assert result["rollback_available"] is True

# Use assertion helpers for field validation
async def test_response_fields(self, assert_result_has_pro_fields):
    result = {"success": True, ...pro and community fields...}
    assert_result_has_pro_fields(result)  # Validates structure
```

### Adding New Tests

When adding new tests for `update_symbol`:

1. **Organize by tier/concern:** Add to existing test class or create new `TestUpdateSymbol{Category}` class
2. **Use existing fixtures:** Reference fixtures from `conftest.py` (temp_python_file, mock_pro_license, etc.)
3. **Follow naming convention:** `test_{feature}_{specific_case}` (e.g., `test_session_limit_enforced_on_11th`)
4. **Document with docstring:** Explain what the test validates
5. **Use assertion helpers:** Call `assert_result_has_{tier}_fields` to validate response structure
6. **Add to test map above:** Update the Test Mapping table

Example new test:
```python
async def test_my_new_feature(self, temp_python_file, mock_pro_license):
    """Test that new feature works as expected."""
    # Setup
    temp_python_file.write("def example(): pass")
    
    # Execute
    result = update_symbol(
        file_path=temp_python_file,
        symbol_name="example",
        new_code="def example(): return True",
        license_token=mock_pro_license
    )
    
    # Assert
    assert result["success"] is True
    assert_result_has_pro_fields(result)
```

## Debugging Failed Tests

### Check fixture values
```python
# Print fixture content
async def test_debug(self, mock_pro_license):
    print(mock_pro_license)  # See token content
```

### Check assertion helpers
```python
# Use helper to validate structure
async def test_response_validation(self, assert_result_has_pro_fields):
    result = {"success": True, ...fields...}
    try:
        assert_result_has_pro_fields(result)
    except AssertionError as e:
        print(f"Missing field: {e}")
```

### Run single test with verbose output
```bash
pytest tests/tools/update_symbol/test_community_tier.py::TestUpdateSymbolCommunitySessionLimit::test_session_limit_enforced_on_11th -vv -s
```

## Coverage Summary

**Total Test Count: 155 tests**

- Community Tier: 20 tests (13%)
- Pro Tier: 20 tests (13%)
- Enterprise Tier: 18 tests (12%)
- Edge Cases: 26 tests (17%)
- Response Model: 28 tests (18%)
- License Handling: 8 tests (5%)
- Error Handling: 15 tests (10%)

**Features Validated:**
- ✅ All Community tier features (basic operations, backup, syntax, session limit)
- ✅ All Pro tier features (unlimited, multi-file, rollback, imports, formatting)
- ✅ All Enterprise tier features (approval, compliance, audit, policy)
- ✅ All edge cases (async, decorators, nested, static/class, lambdas, inheritance)
- ✅ All response model field gating (tier-specific field exposure)
- ✅ All license scenarios (valid, expired, missing, invalid)
- ✅ All error conditions (syntax, file, permission, type)

## Related Documentation

- **Tool Implementation:** `src/code_scalpel/mcp/server.py` (lines 11076-11200)
- **Roadmap:** `docs/modules/update_symbol.md`
- **Assessment:** `docs/testing/test_assessments/update_symbol_test_assessment.md`

## License

Tests are part of Code Scalpel project (MIT License)
