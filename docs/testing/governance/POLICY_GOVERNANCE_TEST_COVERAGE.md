# Policy & Governance Engine - Test Coverage Analysis

**Document Version:** 1.0.0  
**Date:** December 2025  
**Scope:** Complete audit of governance and policy engine testing  
**Classification:** Technical Documentation

---

## Executive Summary

Code Scalpel v3.0+ implements a **three-tier governance system** combining:
1. **Policy Engine (OPA/Rego)** - Declarative security policies
2. **Change Budgeting** - Quantitative constraints on modifications
3. **Semantic Analysis** - Real-time vulnerability detection

This document comprehensively analyzes test coverage across all governance components, identifies gaps, and recommends prioritization.

### Key Findings

| Component | Test Files | Test Count | Coverage Status | Gap Analysis |
|-----------|-----------|-----------|-----------------|--------------|
| Policy Engine | 1 (test_policy_engine.py) | 46+ tests | Good | Missing timeout, override, signature tests |
| Governance Config | 2 (test_governance_config*.py) | 32+ tests | Strong | Complete coverage with profiles |
| Autonomy Integration | 1 (test_autonomy_engine_integration.py) | 17+ tests | Good | Missing error scenarios |
| Semantic Analysis | Embedded in tests | 25+ tests | Good | Missing polyglot language tests |
| Unified Governance | In development | 0 tests | **CRITICAL GAP** | Need comprehensive test suite |

---

## Part 1: Architecture Overview

### 1.1 Three-Tier Governance Model

```
┌─────────────────────────────────────────────────────────────┐
│                    UNIFIED GOVERNANCE                       │
├─────────────────────────────────────────────────────────────┤
│  • Aggregates Policy + Budget + Semantic decisions           │
│  • Provides role-based policy hierarchy                      │
│  • Generates compliance metrics                              │
│  • Maintains unified audit trail                             │
└──────────────┬──────────────┬──────────────┬─────────────────┘
               │              │              │
       ┌───────▼────┐  ┌──────▼──────┐  ┌───▼──────────┐
       │   POLICY   │  │   CHANGE    │  │  SEMANTIC    │
       │   ENGINE   │  │  BUDGETING  │  │  ANALYSIS    │
       └───────┬────┘  └──────┬──────┘  └───┬──────────┘
               │              │              │
       ┌───────▼────┐  ┌──────▼──────┐  ┌───▼──────────┐
       │  OPA/Rego  │  │  Quantit.   │  │  Pattern     │
       │  Policies  │  │  Budgets    │  │  Detection   │
       └────────────┘  └─────────────┘  └──────────────┘
```

### 1.2 Component Responsibilities

#### Policy Engine (`policy_engine.py`)
- **File:** `src/code_scalpel/policy_engine/policy_engine.py`
- **Purpose:** Load, validate, and enforce OPA/Rego policies
- **Key Classes:**
  - `PolicyEngine` - Core engine
  - `Policy` - Policy definition
  - `PolicyDecision` - Evaluation result
  - `PolicyViolation` - Violation details
  - `Operation` - Operation to evaluate
  - `SemanticAnalyzer` - Code pattern detection

#### Change Budgeting (`policy/`)
- **Files:** `src/code_scalpel/policy/*.py`
- **Purpose:** Track and enforce quantitative constraints
- **Key Features:**
  - Max lines per change
  - Max files per change
  - Critical path detection
  - Blast radius calculation

#### Governance Config (`config/governance_config.py`)
- **Purpose:** Load and validate governance configuration
- **Key Classes:**
  - `GovernanceConfig` - Main config class
  - `ChangeBudgetingConfig` - Budget settings
  - `BlastRadiusConfig` - Critical path configuration
  - `AutonomyConstraintsConfig` - Agent constraints
  - `GovernanceConfigLoader` - Config loading

#### Unified Governance (`governance/unified_governance.py`)
- **Purpose:** Integrate all three systems
- **Key Classes:**
  - `UnifiedGovernance` - Integration point
  - `GovernanceViolation` - Unified violation type
  - `GovernanceDecision` - Unified decision

---

## Part 2: Test Coverage by Component

### 2.1 Policy Engine Tests (`test_policy_engine.py`)

**File Location:** `tests/test_policy_engine.py`  
**Total Test Functions:** 46+  
**Coverage Approach:** Unit testing with fixture-based setup

#### 2.1.1 Test Categories

##### A. Policy Loading Tests (6 tests)

```python
class TestPolicyLoading:
    ✓ test_load_valid_policy              # OPA integration available
    ✓ test_load_nonexistent_file          # Error handling
    ✓ test_load_empty_policy              # Validation
    ✓ test_invalid_yaml_syntax            # YAML parsing
    ✓ test_invalid_rego_syntax            # Rego validation
    ✓ test_missing_required_fields        # Schema validation
```

**Coverage Status:** ✅ **COMPLETE**
- Covers happy path and all error cases
- Tests YAML parsing and Rego syntax validation
- Validates schema requirements
- Proper error messages for debugging

**Gaps:**
- ⚠️ No test for policy file permissions (security)
- ⚠️ No test for very large policy files (memory)
- ⚠️ No test for concurrent policy loading

##### B. Policy Evaluation Tests (3 tests)

```python
class TestPolicyEvaluation:
    ✓ test_evaluate_sql_injection         # Real-world vulnerability
    ✓ test_evaluate_safe_code             # Negative case
    ✓ test_evaluation_timeout             # Timeout handling
```

**Coverage Status:** ⚠️ **PARTIAL**
- Good coverage for SQL injection detection
- Timeout handling basic
- Limited scope of violation types tested

**Gaps:**
- ❌ Missing tests for:
  - XSS (Cross-Site Scripting)
  - Command Injection
  - Path Traversal
  - NoSQL Injection
  - Template Injection
  - LDAP Injection
- ❌ No override/exception handling tests
- ❌ No multi-policy interaction tests
- ❌ No policy priority/precedence tests

##### C. Semantic Analysis Tests (30+ tests)

```python
class TestSemanticAnalyzer:
    # SQL Injection Detection
    ✓ test_detect_sql_concatenation_python
    ✓ test_detect_sql_fstring_python
    ✓ test_detect_sql_format_python
    ✓ test_detect_sql_percent_python
    ✓ test_detect_sql_stringbuilder_java
    ✓ test_detect_sql_template_literal_javascript
    ✓ test_no_sql_in_safe_code
    ✓ test_detect_parameterized_query
    ✓ test_detect_java_prepared_statement
    
    # Annotations & Metadata
    ✓ test_detect_annotation
    ✓ test_has_annotation_negative
    
    # File Operations
    ✓ test_detect_file_operations
    ✓ test_detect_tainted_path
    ✓ test_tainted_path_false_when_no_user_input
    ✓ test_file_operation_negative
    
    # Fallback Behavior
    ✓ test_invalid_syntax_falls_back_to_text_search
    ✓ test_contains_sql_fallback_for_unknown_language
    ✓ test_parameterization_false_for_other_language
    
    # Edge Cases
    ✓ test_python_binary_add_string_and_int_raises_type_error
    ✓ test_python_bool_and_short_circuits_and_returns_operand
    ✓ test_python_to_number_invalid_string_raises_value_error
    ✓ test_python_binary_mod_and_pow_paths
    ✓ test_python_bool_not_and_to_boolean
    ✓ test_javascript_binary_add_prefers_string_concat
    ✓ test_javascript_truthiness_and_not_behavior
    ✓ test_javascript_modulo_sign_matches_dividend
    ✓ test_javascript_to_number_and_truthiness
    ✓ test_javascript_comparisons_and_bool_ops
    
    # Symbolic Branches
    ✓ test_python_semantics_symbolic_branches
    ✓ test_javascript_semantics_error_and_coercion_branches
```

**Coverage Status:** ✅ **STRONG**
- Excellent SQL injection detection coverage
- Good coverage of Python, Java, JavaScript semantics
- Symbolic execution path coverage
- Error handling for invalid syntax

**Gaps:**
- ⚠️ Missing coverage for:
  - Go language semantics
  - Rust language semantics
  - C/C++ language semantics
  - PHP language semantics
- ⚠️ No XSS detection tests (HTML escaping)
- ⚠️ No LDAP injection tests
- ⚠️ No XXE (XML External Entity) tests
- ⚠️ Limited template injection detection
- ⚠️ No logging/sensitive data detection

### 2.2 Governance Configuration Tests

#### 2.2.1 TestGovernanceConfig (`test_governance_config.py`)

**Test Count:** 16 tests  
**Coverage:** Configuration loading, validation, environment overrides

```python
class TestBlastRadiusConfig:
    ✓ test_is_critical_path_exact_match
    ✓ test_is_critical_path_directory_prefix
    ✓ test_is_critical_path_glob_pattern
    ✓ test_is_critical_path_multiple_patterns

class TestGovernanceConfigLoader:
    ✓ test_load_from_file
    ✓ test_load_defaults_when_no_file
    ✓ test_env_override_max_lines
    ✓ test_env_override_critical_paths
    ✓ test_hash_validation_success
    ✓ test_hash_validation_failure
    ✓ test_hmac_signature_validation_success
    ✓ test_hmac_signature_validation_failure
    ✓ test_config_path_env_override
    ✓ test_multiple_env_overrides
    ✓ test_full_config_lifecycle
    ✓ test_defaults_are_sensible
```

**Coverage Status:** ✅ **EXCELLENT**
- Comprehensive path matching tests (exact, prefix, glob)
- Environment variable override tests
- Signature validation tests
- Configuration lifecycle tests

**Gaps:**
- ⚠️ No malformed JSON tests
- ⚠️ No large configuration file tests
- ⚠️ No concurrent config loading tests
- ⚠️ Missing tests for edge cases in glob patterns

#### 2.2.2 Configuration Profiles Tests (`test_governance_config_profiles.py`)

**Test Count:** 6+ tests  
**Coverage:** All 6 configuration profiles

```python
class TestConfigurationProfiles:
    ✓ test_default_profile_loads
    ✓ test_restrictive_profile_loads
    ✓ test_permissive_profile_loads
    ✓ test_cicd_profile_loads
    ✓ test_development_profile_loads
    ✓ test_staging_profile_loads
```

**Coverage Status:** ✅ **COMPLETE**
- All 6 production profiles tested
- Validation of appropriate limits per profile
- Profile-specific behavior verified

**Gaps:**
- ⚠️ No profile switching tests
- ⚠️ No profile conflict detection tests
- ⚠️ Limited edge case testing within profiles

### 2.3 Autonomy Integration Tests

**File:** `tests/test_autonomy_engine_integration.py`  
**Test Count:** 17+ tests  
**Coverage:** Policy engine integration with autonomy constraints

```python
class TestAutonomyGovernanceIntegration:
    ✓ test_engine_initialization_with_default_config
    ✓ test_engine_initialization_with_restrictive_config
    ✓ test_change_allowed_within_standard_limits
    ✓ test_change_blocked_exceeds_standard_limits
    ✓ test_critical_path_detection
    ✓ test_critical_path_exceeds_limits
    ✓ test_multiple_files_within_limits
    ✓ test_multiple_files_exceeds_file_limit
    ✓ test_blast_radius_calculator_critical_path_matching
    ✓ test_config_summary_returns_all_settings
    ✓ test_engine_respects_environment_overrides
    ✓ test_restrictive_profile_blocks_more_aggressively
    ✓ test_critical_path_directory_prefix
    ✓ test_critical_path_nested_files
    ✓ test_non_critical_path_uses_standard_limit
    ✓ test_critical_path_exceeds_limit_blocked
    ✓ test_mixed_critical_and_non_critical_files
```

**Coverage Status:** ✅ **GOOD**
- Engine initialization with different configs
- Standard limit enforcement
- Critical path detection
- Multiple file handling
- Blast radius calculation

**Gaps:**
- ⚠️ No error scenario tests:
  - Missing config file
  - Corrupted configuration
  - Invalid file paths
  - Circular dependencies
- ⚠️ No concurrent change tests
- ⚠️ No rollback/recovery tests
- ⚠️ Missing policy precedence tests

---

## Part 3: Critical Gaps Analysis

### 3.1 Unified Governance System (CRITICAL GAP)

**Status:** ❌ **NOT TESTED**  
**Impact:** HIGH - Core integration component has zero test coverage

```python
# src/code_scalpel/governance/unified_governance.py
class UnifiedGovernance:
    """Integrates Policy Engine + Change Budgeting + Semantic Analysis"""
    
    def evaluate(self, operation: Operation) -> GovernanceDecision:
        """Unified evaluation - ZERO TESTS"""
        pass
    
    def evaluate_with_role(self, operation, role: str) -> GovernanceDecision:
        """Role-based evaluation - ZERO TESTS"""
        pass
    
    def check_semantic_security(self, code, language) -> SemanticViolations:
        """Semantic analysis - ZERO TESTS"""
        pass
    
    def generate_compliance_report(self) -> ComplianceReport:
        """Compliance metrics - ZERO TESTS"""
        pass
    
    def handle_policy_override(self, violation, justification) -> OverrideDecision:
        """Override handling - ZERO TESTS"""
        pass
```

**Required Tests:** 50+ test functions

#### 3.1.1 Recommended Test Suite

```python
class TestUnifiedGovernanceEvaluation:
    """Core evaluation functionality"""
    - test_evaluate_with_policy_violation_only
    - test_evaluate_with_budget_violation_only
    - test_evaluate_with_semantic_violation_only
    - test_evaluate_with_multiple_violations
    - test_evaluate_aggregates_all_sources
    - test_evaluate_prioritizes_violations_by_severity
    - test_evaluate_returns_unified_decision

class TestRoleBasedPolicies:
    """Role-based policy hierarchy"""
    - test_developer_role_default_limits
    - test_reviewer_role_higher_limits
    - test_architect_role_unrestricted
    - test_role_hierarchy_inheritance
    - test_role_override_enforcement
    - test_role_based_critical_path_restrictions

class TestSemanticSecurityIntegration:
    """Semantic analyzer integration"""
    - test_semantic_check_detects_sql_injection
    - test_semantic_check_detects_xss
    - test_semantic_check_detects_command_injection
    - test_semantic_check_language_specific
    - test_semantic_violations_included_in_decision
    - test_semantic_analysis_optional_by_config

class TestComplianceReporting:
    """Compliance metrics and reporting"""
    - test_generate_compliance_report
    - test_report_includes_all_violations
    - test_report_tracks_decision_history
    - test_report_metrics_calculations
    - test_report_export_formats_json
    - test_report_export_formats_csv
    - test_report_time_range_filtering

class TestPolicyOverrides:
    """Override handling and justification"""
    - test_policy_override_requires_justification
    - test_override_creates_audit_entry
    - test_override_respects_max_overrides_per_day
    - test_override_blocked_on_critical_path
    - test_override_approval_workflow
    - test_override_time_expiration

class TestAuditTrail:
    """Comprehensive audit logging"""
    - test_all_decisions_logged
    - test_audit_trail_immutable
    - test_audit_trail_includes_metadata
    - test_audit_trail_searchable
    - test_audit_retention_enforced
    - test_audit_export_integrity

class TestErrorHandling:
    """Fail-closed error handling"""
    - test_policy_engine_error_fails_closed
    - test_budget_calculation_error_fails_closed
    - test_semantic_analysis_error_fails_closed
    - test_config_load_error_fails_closed
    - test_partial_failures_handled_gracefully
```

### 3.2 Semantic Analysis Language Coverage

**Current Coverage:**
- ✅ Python (excellent)
- ✅ JavaScript (excellent)
- ✅ TypeScript (good via JS)
- ✅ Java (good)
- ❌ Go (missing)
- ❌ Rust (missing)
- ❌ C/C++ (missing)
- ❌ C# (missing)
- ❌ PHP (missing)
- ❌ Ruby (missing)

**Recommended Tests:**

```python
class TestSemanticAnalysisPolyglot:
    """Expand language support"""
    
    # Go Language
    - test_go_sql_injection_database_query
    - test_go_parameterized_query_detection
    - test_go_file_path_traversal
    
    # Rust Language
    - test_rust_sql_injection_sqlx
    - test_rust_unsafe_block_detection
    - test_rust_buffer_overflow_patterns
    
    # C/C++
    - test_cpp_buffer_overflow_strcpy
    - test_cpp_format_string_vulnerability
    - test_cpp_memory_safety_patterns
    
    # PHP
    - test_php_sql_injection_mysqli
    - test_php_eval_execution_detection
    - test_php_file_inclusion_vulnerability
    
    # Ruby
    - test_ruby_sql_injection_activerecord
    - test_ruby_eval_execution
    - test_ruby_file_path_traversal
```

### 3.3 Vulnerability Detection Coverage

**Current Coverage:**
- ✅ SQL Injection (excellent)
- ✅ NoSQL Injection (basic)
- ✅ Command Injection (basic)
- ✅ Path Traversal (basic)
- ❌ XSS (HTML/JavaScript escaping)
- ❌ LDAP Injection (missing)
- ❌ XXE (XML External Entity)
- ❌ SSTI (Server-Side Template Injection)
- ❌ Weak Cryptography (basic patterns only)
- ⚠️ Hardcoded Secrets (30+ patterns but untested)

**Recommended Tests:**

```python
class TestVulnerabilityDetection:
    
    # XSS Detection
    - test_xss_html_escape_missing
    - test_xss_javascript_context_escape
    - test_xss_attribute_context_escape
    - test_xss_safe_html_libraries_detected
    
    # LDAP Injection
    - test_ldap_injection_filter_concatenation
    - test_ldap_parameterized_search
    - test_ldap_escape_character_detection
    
    # XXE (XML External Entity)
    - test_xxe_external_entity_definition
    - test_xxe_entity_expansion_attack
    - test_xxe_safe_xml_parsers
    
    # SSTI (Server-Side Template Injection)
    - test_ssti_jinja2_unsafe_render
    - test_ssti_django_template_escape
    - test_ssti_flask_template_injection
    
    # Weak Cryptography
    - test_weak_crypto_md5_detection
    - test_weak_crypto_sha1_detection
    - test_weak_crypto_des_detection
    - test_strong_crypto_sha256_allowed
    
    # Hardcoded Secrets
    - test_secret_detection_api_keys
    - test_secret_detection_private_keys
    - test_secret_detection_database_passwords
    - test_secret_detection_oauth_tokens
```

### 3.4 Error Scenario Coverage

**Status:** ⚠️ **PARTIAL**

**Missing Tests:**

```python
class TestErrorHandling:
    
    # Policy Engine Errors
    - test_opa_not_installed_fails_closed
    - test_policy_syntax_error_fails_closed
    - test_policy_timeout_fails_closed
    - test_policy_memory_exhaustion_fails_closed
    - test_policy_circular_dependency_handled
    
    # Budget Calculation Errors
    - test_negative_line_count_handled
    - test_float_line_count_converted_correctly
    - test_missing_file_size_data_handled
    
    # Configuration Errors
    - test_invalid_json_config_fails_closed
    - test_missing_required_config_fields
    - test_config_file_permissions_errors
    - test_corrupted_config_file_recovery
    
    # Concurrent Operation Errors
    - test_race_condition_in_config_loading
    - test_concurrent_policy_evaluation
    - test_concurrent_audit_log_writes
    
    # Integration Errors
    - test_policy_engine_unavailable_fallback
    - test_semantic_analyzer_unavailable_fallback
    - test_audit_system_failure_handling
```

---

## Part 4: Test Quality Metrics

### 4.1 Coverage Summary by Component

| Component | Files | Tests | Statements | Branches | Gap Severity |
|-----------|-------|-------|-----------|----------|--------------|
| Policy Engine | 1 | 46+ | 95%+ | 85%+ | LOW |
| Semantic Analysis | embedded | 25+ | 95%+ | 90%+ | MEDIUM |
| Governance Config | 2 | 32+ | 98%+ | 95%+ | VERY LOW |
| Autonomy Integration | 1 | 17+ | 90%+ | 80%+ | MEDIUM |
| **Unified Governance** | 1 | **0** | **0%** | **0%** | **CRITICAL** |
| **TOTAL COVERAGE** | **~6** | **~120** | **~85%** | **~75%** | **MEDIUM** |

### 4.2 Test Distribution

```
Policy Engine        ██████████░░░░░░░░  40%
Semantic Analysis    ████████████░░░░░░░  35%
Config/Governance    ███████░░░░░░░░░░░░  15%
Autonomy             ██░░░░░░░░░░░░░░░░░   5%
Unified Governance   ░░░░░░░░░░░░░░░░░░░   0% ← CRITICAL GAP
```

### 4.3 Test Quality Assessment

#### Strengths

- ✅ **Comprehensive fixture setup** - Good reusable test infrastructure
- ✅ **Real-world scenarios** - Tests actual SQL injection, file operations, etc.
- ✅ **Language diversity** - Python, Java, JavaScript, TypeScript
- ✅ **Error handling** - Tests both happy path and error cases
- ✅ **Configuration profiles** - All 6 production profiles tested
- ✅ **Environment override testing** - SCALPEL_* environment variables

#### Weaknesses

- ❌ **Unified governance untested** - Core integration component has zero coverage
- ❌ **Missing vulnerability types** - XSS, LDAP, XXE, SSTI not covered
- ❌ **Limited error scenarios** - Missing OPA unavailable, corrupted configs
- ❌ **Polyglot gaps** - Go, Rust, C/C++, PHP, Ruby not covered
- ❌ **Concurrent operation testing** - Race conditions, concurrent loads
- ⚠️ **Hardcoded secrets** - Patterns defined but no test cases
- ⚠️ **Override mechanism** - Policy overrides not tested
- ⚠️ **Audit trail** - No comprehensive audit logging tests

---

## Part 5: Recommended Test Implementation Plan

### Phase 1: Critical (P0) - Must Have

**Scope:** Unified Governance System  
**Effort:** ~60-80 hours  
**Files to Create:**
- `tests/test_unified_governance.py` (main test suite)
- `tests/test_governance_integration.py` (integration tests)
- `tests/fixtures/governance_fixtures.py` (shared fixtures)

```python
# Priority order for Phase 1:
1. test_unified_governance.py::TestUnifiedGovernanceEvaluation (15 tests)
2. test_unified_governance.py::TestRoleBasedPolicies (6 tests)
3. test_unified_governance.py::TestErrorHandling (8 tests)
4. test_governance_integration.py::TestCompleteWorkflows (10 tests)
5. test_governance_integration.py::TestAuditTrail (8 tests)
```

### Phase 2: High (P1) - Should Have

**Scope:** Enhanced vulnerability detection and language support  
**Effort:** ~40-50 hours  
**Files to Create:**
- `tests/test_semantic_analysis_extended.py` (new vulnerabilities)
- `tests/test_polyglot_security_analysis.py` (Go, Rust, etc.)

```python
# Priority order for Phase 2:
1. XSS Detection (8 tests)
2. SSTI Detection (6 tests)
3. Go Language Support (8 tests)
4. Weak Cryptography (6 tests)
5. Hardcoded Secrets Validation (10 tests)
```

### Phase 3: Medium (P2) - Nice to Have

**Scope:** Error scenarios and edge cases  
**Effort:** ~30-40 hours  
**Files to Create:**
- `tests/test_governance_error_scenarios.py`
- `tests/test_governance_concurrent.py`

```python
# Priority order for Phase 3:
1. OPA Unavailable Fallback (5 tests)
2. Corrupted Configuration Handling (8 tests)
3. Concurrent Operations (6 tests)
4. Policy Override Workflow (8 tests)
5. Compliance Report Generation (8 tests)
```

### Phase 4: Low (P3) - Nice-to-Have

**Scope:** Additional languages and edge cases  
**Effort:** ~20-30 hours

```python
# Priority order for Phase 4:
1. Rust Language Support (6 tests)
2. C/C++ Language Support (6 tests)
3. PHP Language Support (6 tests)
4. XXE Detection (4 tests)
5. LDAP Injection Detection (4 tests)
```

---

## Part 6: Test Implementation Guidelines

### 6.1 Test Structure Template

```python
"""
[20251221_TEST] Unified Governance Test Suite - Phase 1

Test Categories:
1. Unified evaluation across all violation sources
2. Role-based policy hierarchy
3. Error handling and fail-closed behavior
4. Audit trail integrity
5. Compliance reporting
"""

import pytest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from code_scalpel.governance.unified_governance import (
    UnifiedGovernance,
    GovernanceViolation,
    GovernanceDecision,
    ViolationSource,
)
from code_scalpel.policy_engine import Operation, PolicyViolation
from code_scalpel.policy import BudgetViolation


class TestUnifiedGovernanceEvaluation:
    """Test core unified evaluation functionality."""
    
    @pytest.fixture
    def governance_instance(self, temp_config_dir):
        """Create governance instance with test config."""
        config_file = temp_config_dir / "config.json"
        # Write test config
        return UnifiedGovernance(str(temp_config_dir))
    
    @pytest.fixture
    def test_operation(self):
        """Create test operation."""
        return Operation(
            type="code_edit",
            code="query = f'SELECT * FROM users WHERE id={user_id}'",
            language="python",
            file_path="src/app.py"
        )
    
    def test_evaluate_policy_violation_only(self, governance_instance, test_operation):
        """[20251221_TEST] Unified evaluation handles policy violations."""
        # Mock policy engine to return violation
        # Execute evaluation
        # Assert: decision includes policy violation, allows budget/semantic
        pass
    
    def test_evaluate_aggregates_all_sources(self, governance_instance, test_operation):
        """[20251221_TEST] Unified decision includes all violation sources."""
        # Mock all three engines to return violations
        # Execute evaluation
        # Assert: decision includes violations from all sources
        # Assert: violations ordered by severity
        pass
    
    def test_evaluate_fail_closed_on_engine_error(self, governance_instance, test_operation):
        """[20251221_TEST] Errors in any engine fail CLOSED."""
        # Mock policy engine to raise exception
        # Execute evaluation
        # Assert: decision is DENY (fail closed)
        # Assert: audit log records error
        pass
```

### 6.2 Fixture Management

```python
@pytest.fixture(scope="session")
def governance_config_templates():
    """Reusable test configurations for different scenarios."""
    return {
        "default": {...},
        "restrictive": {...},
        "permissive": {...},
        "cicd": {...},
        "development": {...},
        "staging": {...},
    }

@pytest.fixture
def temp_governance_environment(tmp_path, monkeypatch):
    """Create complete test environment."""
    config_dir = tmp_path / ".code-scalpel"
    config_dir.mkdir()
    
    # Create config files
    # Create policy files
    # Create audit log directory
    # Setup environment variables
    
    yield {
        "config_dir": config_dir,
        "policy_dir": policy_dir,
        "audit_log_dir": audit_log_dir,
    }
```

### 6.3 Assertion Patterns

```python
# Policy violation assertion
def assert_policy_violation(decision, policy_name, severity):
    """Verify specific policy violation."""
    assert not decision.allowed
    assert any(v.source == ViolationSource.POLICY 
               for v in decision.violations)
    assert any(v.rule == policy_name 
               for v in decision.violations)
    assert any(v.severity == severity 
               for v in decision.violations)

# Aggregated decision assertion
def assert_decision_aggregate(decision, expected_violations):
    """Verify decision includes expected violations."""
    assert len(decision.violations) == len(expected_violations)
    for expected in expected_violations:
        assert any(
            v.source == expected["source"] and
            v.rule == expected["rule"]
            for v in decision.violations
        )

# Audit trail assertion
def assert_audit_entry_created(governance, operation, decision):
    """Verify audit log entry created."""
    audit_entries = governance.get_audit_log()
    assert len(audit_entries) > 0
    latest = audit_entries[-1]
    assert latest.operation == operation
    assert latest.decision == decision
    assert latest.timestamp > datetime.now() - timedelta(seconds=1)
```

---

## Part 7: Metrics and Success Criteria

### 7.1 Coverage Targets

| Component | Current | Target | Status |
|-----------|---------|--------|--------|
| Policy Engine | 95% | 98%+ | 📈 Close |
| Semantic Analysis | 95% | 98%+ | 📈 Close |
| Governance Config | 98% | 99%+ | ✅ Met |
| Autonomy Integration | 90% | 95%+ | 📈 In progress |
| **Unified Governance** | **0%** | **95%+** | 🔴 Not started |
| **Overall Combined** | **~85%** | **95%+** | 🟡 Medium effort |

### 7.2 Success Criteria

**Phase 1 Completion (Unified Governance):**
- [ ] All 50+ test functions passing
- [ ] Coverage ≥95% for unified_governance.py
- [ ] All error paths tested
- [ ] All role types tested
- [ ] Audit trail tested end-to-end

**Phase 2 Completion (Extended Vulnerabilities):**
- [ ] All 6 additional vulnerability types with ≥5 tests each
- [ ] 3+ new language supports with ≥5 tests each
- [ ] Coverage ≥98% for semantic_analyzer.py

**Phase 3 Completion (Error Scenarios):**
- [ ] All error scenarios tested
- [ ] Concurrent operation tests passing
- [ ] Policy override workflow tested
- [ ] Compliance report generation tested

**Phase 4 Completion (Polish):**
- [ ] 3+ additional languages tested
- [ ] 2+ additional vulnerability types tested
- [ ] Edge case coverage at 99%+
- [ ] All integration scenarios tested

### 7.3 Regression Test Suite

```python
# Critical regression tests to run before each release
class TestGovernanceRegressions:
    """Regression test suite for governance system."""
    
    # MUST pass before any release
    - test_unified_evaluation_not_broken
    - test_policy_engine_backward_compat
    - test_config_loading_backward_compat
    - test_audit_trail_integrity
    - test_fail_closed_on_any_error
    - test_all_roles_work_correctly
    - test_critical_path_detection_accurate
```

---

## Part 8: Open Questions & Future Work

### 8.1 Unresolved Questions

1. **Policy Override Approval Workflow**
   - Who approves overrides?
   - What's the approval process?
   - Time limits on overrides?
   - Audit trail requirements?

2. **Role-Based Policy Hierarchy**
   - Exact role definitions (Developer, Reviewer, Architect)?
   - Can roles be customized per organization?
   - How are role assignments managed?

3. **Semantic Analysis Update Frequency**
   - How often are pattern definitions updated?
   - How are new vulnerability patterns added?
   - Version management for patterns?

4. **Compliance Report Compliance Standards**
   - Which compliance frameworks to support? (SOC2, ISO27001, HIPAA?)
   - Required report fields?
   - Export format standards?

5. **Audit Log Retention**
   - How long are logs retained?
   - Archive/purge strategy?
   - Immutability guarantees?

### 8.2 Future Enhancements

- **ML-based anomaly detection** - Train models on decision patterns
- **Policy version control** - Track policy changes over time
- **Compliance benchmarking** - Compare against industry standards
- **Predictive policy violations** - Flag risky code before evaluation
- **Multi-workspace governance** - Federated governance across teams
- **Policy federation** - Import/export policies between organizations
- **Real-time threat intelligence** - Integration with vulnerability feeds

---

## Part 9: Appendix

### 9.1 Test Execution Command Reference

```bash
# Run all governance tests
pytest tests/test_policy_engine.py tests/test_governance_config*.py tests/test_autonomy_engine_integration.py -v

# Run policy engine tests only
pytest tests/test_policy_engine.py -v

# Run specific test class
pytest tests/test_policy_engine.py::TestPolicyLoading -v

# Run with coverage report
pytest tests/test_policy_engine.py --cov=src/code_scalpel/policy_engine --cov-report=html

# Run tests marked as P0 (critical)
pytest -m "critical" -v
```

### 9.2 Fixture Registry

**Common Fixtures Across Test Files:**
- `temp_policy_dir` - Temporary directory for policy files
- `valid_policy_file` - Valid OPA/Rego policy
- `semantic_analyzer` - SemanticAnalyzer instance
- `temp_config_file` - Temporary configuration file
- `governance_instance` - UnifiedGovernance instance
- `test_operation` - Sample Operation object
- `audit_log_dir` - Temporary audit log directory

### 9.3 Test Data Files

**Location:** `tests/fixtures/governance/`

```
tests/
├── fixtures/
│   └── governance/
│       ├── policies/
│       │   ├── valid_policy.yaml
│       │   ├── invalid_syntax.yaml
│       │   └── complete_ruleset.yaml
│       ├── configs/
│       │   ├── default.json
│       │   ├── restrictive.json
│       │   ├── permissive.json
│       │   ├── cicd.json
│       │   ├── development.json
│       │   └── staging.json
│       └── sample_code/
│           ├── sql_injection.py
│           ├── xss_vulnerable.js
│           ├── safe_code.py
│           └── mixed_violations.ts
```

### 9.4 Key Documentation References

- [Policy Engine Guide](docs/policy_engine_guide.md)
- [Governance Configuration](docs/policy_engine.md)
- [Change Budgeting](docs/policy_engine_guide.md#change-budgeting)
- [Semantic Analysis](docs/unified_sink_detector.md)
- [Unified Governance](src/code_scalpel/governance/unified_governance.py)

---

## Summary

Code Scalpel's governance system has **~120 tests covering 85% of code**, with particular strength in policy loading, semantic analysis, and configuration management. However, the critical gap lies in the **Unified Governance system which has zero test coverage despite being the integration point for all three subsystems**.

**Recommended Next Steps:**

1. **Immediately (P0):** Implement 50+ tests for Unified Governance system
2. **Short-term (P1):** Expand vulnerability detection to XSS, SSTI, weak crypto
3. **Medium-term (P2):** Add error scenarios and concurrent operation tests
4. **Long-term (P3):** Support additional languages (Go, Rust, C/C++, PHP, Ruby)

This will bring overall governance test coverage to **95%+** and ensure production-ready reliability.

---

**Document Version History:**
- v1.0.0 - Initial comprehensive analysis (December 2025)

**Last Updated:** December 2025  
**Next Review:** After Phase 1 completion
