# crawl_project Test Checklist - January 3, 2026

**Quick Reference**: Which tests exist, which are missing, and priority for implementation.

---

## Existing Tests (45 total)

### ✅ Core Parser Tests (31 tests)
All in `tests/core/parsers/test_project_crawler.py` - ALL PASSING

**AST Analysis (10 tests)**:
- ✅ test_visit_simple_function
- ✅ test_visit_function_with_branches
- ✅ test_visit_class_with_methods
- ✅ test_visit_imports
- ✅ test_async_function
- ✅ test_class_inheritance
- ✅ test_qualified_name_standalone
- ✅ test_qualified_name_method
- ✅ test_comprehension_complexity
- ✅ test_lambda_functions

**Structure Analysis (6 tests)**:
- ✅ test_crawl_project_structure
- ✅ test_exclude_dirs
- ✅ test_custom_exclude_dirs
- ✅ test_invalid_path_raises
- ✅ test_file_not_directory_raises
- ✅ test_empty_directory

**Complexity Analysis (5 tests)**:
- ✅ test_complexity_warnings
- ✅ test_complexity_warning_threshold
- ✅ test_nested_classes
- ✅ test_only_excluded_dirs
- ✅ test_unicode_content

**Reporting & Serialization (7 tests)**:
- ✅ test_summary_properties
- ✅ test_summary_dict
- ✅ test_generate_report
- ✅ test_report_contains_stats
- ✅ test_report_output_to_file
- ✅ test_to_dict_structure
- ✅ test_to_dict_serializable

**Convenience Functions (3 tests)**:
- ✅ test_crawl_project_function
- ✅ test_crawl_project_with_options
- ✅ test_syntax_error_handling

---

### ✅ MCP Tier Tests (4 tests)
Split between `tests/tools/crawl_project/test_crawl_project_contracts.py` and `tests/tools/tiers/test_crawl_project_tiers.py`

**All Tests** - NOW PASSING AFTER SCHEMA FIXES:
- ✅ test_community_enforces_limit_and_discovery_mode
- ✅ test_community_blocks_enterprise_pattern_feature
- ✅ test_enterprise_creates_incremental_cache
- ✅ test_invalid_tier_env_falls_back_to_community_limits

**Previously SKIPPED** (3) - NOW PASSING:
- ✅ test_crawl_project_community_multilanguage_and_limits (was SKIPPED)
- ✅ test_crawl_project_pro_cache_hits (was SKIPPED)
- ✅ test_crawl_project_enterprise_compliance_best_effort (was SKIPPED)

**Other**:
- ✅ test_crawl_project_enterprise_custom_rules_config

---

### ⚠️ Partial/Indirect Coverage (10 tests)

**Error Handling (4 tests)**:
- ✅ test_syntax_error_handling (MCP aware? - core only)
- ✅ test_invalid_path_raises (core)
- ✅ test_file_not_directory_raises (core)
- ✅ test_unicode_content (core - implicit non-UTF8 handling)

**Complexity (5 tests)**:
- ✅ test_complexity_warnings (core)
- ✅ test_complexity_warning_threshold (core)
- ✅ test_async_function (core)
- ✅ test_comprehension_complexity (core)
- ✅ test_qualified_name_method (core)

**License/Tier (1 test)**:
- ✅ test_invalid_tier_env_falls_back_to_community_limits (MCP)

---

## Missing Tests (69 total to implement)

### 🔴 P0 - BLOCKING (20 tests)

#### 1. Result Schema & Serialization (5 tests)
- ❌ test_result_all_fields_present_community
- ❌ test_result_all_fields_present_pro
- ❌ test_result_all_fields_present_enterprise
- ❌ test_result_json_serializable
- ❌ test_result_field_types_match_schema

#### 4. Language Detection Accuracy (5 tests)
- ❌ test_python_extensions_detected
- ❌ test_javascript_extensions_detected
- ❌ test_typescript_extensions_detected
- ❌ test_java_extensions_detected
- ❌ test_unknown_extension_mapped_correctly

#### 9. Tier Downgrade/License Edge Cases (4 additional tests)
- ❌ test_expired_license_mid_session_grace_period
- ❌ test_revoked_license_immediate_downgrade
- ❌ test_pro_license_accessing_enterprise_feature_denied
- ❌ test_license_cache_invalidation_on_expiry
- (2 tests already covered: invalid tier fallback, feature gating)

#### 14. Determinism & Consistency (4 tests)
- ❌ test_two_crawls_same_project_same_results
- ❌ test_language_breakdown_consistent_across_runs
- ❌ test_framework_hints_stable
- ❌ test_entrypoints_stable

**P0 SUBTOTAL**: 18 tests (⚠️ 1 already passing)

---

### 🟠 P1 - HIGH PRIORITY (35 tests)

#### 2. Gitignore Behavior (4 tests)
- ❌ test_gitignore_patterns_honored
- ❌ test_gitignore_slash_suffix_directory_only
- ❌ test_gitignore_negation_patterns_unsupported
- ❌ test_respect_gitignore_flag_false

#### 3. Framework Detection (6 tests)
- ❌ test_flask_route_decorator_detection
- ❌ test_django_import_and_urls_detection
- ❌ test_fastapi_detection
- ❌ test_nextjs_pages_router_detection
- ❌ test_nextjs_app_router_detection
- ❌ test_framework_signals_not_set_on_community

#### 5. Entrypoint Detection (5 tests)
- ❌ test_main_block_detected
- ❌ test_click_command_detected
- ❌ test_flask_route_is_entrypoint
- ❌ test_django_urls_is_entrypoint
- ❌ test_multiple_entrypoints_collected

#### 6. Cache Lifecycle (6 additional tests)
- ✅ test_cache_file_path_standard_location (1/7 - cache file creation passing)
- ❌ test_cache_mtime_tracking_per_file
- ❌ test_cache_modified_file_reanalyzed
- ❌ test_cache_new_files_added_to_result
- ❌ test_cache_deleted_files_removed_from_cache
- ❌ test_cache_corruption_graceful_recovery
- ❌ test_cache_size_bounded

#### 7. Custom Rules Config (4 additional tests)
- ✅ test_custom_rules_include_extensions (1/5 - custom rules config test passing)
- ❌ test_custom_rules_config_not_found_graceful
- ❌ test_custom_rules_include_extensions_empty_list
- ❌ test_custom_rules_exclude_dirs_merged_with_defaults
- ❌ test_custom_rules_invalid_json_logged_warning

#### 8. Error Handling (3 additional tests)
- ❌ test_unreadable_file_permission_denied
- ❌ test_large_file_over_max_size
- ❌ test_binary_file_detected_skipped

#### 10. Complexity Analysis (1 tier-specific test)
- ❌ test_complexity_threshold_respected_pro (core tests exist, tier test missing)

**P1 SUBTOTAL**: 33 tests

---

### 🟡 P2 - MEDIUM PRIORITY (11 tests)

#### 8. Error Handling (continued - 4 tests)
- ❌ test_non_utf8_file_handled
- ❌ test_symlink_handling
- ❌ test_circular_symlink_no_infinite_loop
- ❌ test_syntax_error_in_python_file

#### 11. Response Config (3 tests)
- ❌ test_response_config_community_truncates_report
- ❌ test_response_config_filters_sensitive_paths
- ❌ test_response_config_pro_vs_community_verbosity

#### 12. Progress Reporting (2 tests)
- ❌ test_progress_reported_0_to_100
- ❌ test_progress_increments_during_crawl

#### 15. Limits Configuration (2 tests)
- ❌ test_limits_toml_override_max_files_community
- ❌ test_limits_toml_invalid_fallback_to_defaults

**P2 SUBTOTAL**: 11 tests

---

### 🔵 P3 - LOW PRIORITY (3 tests)

#### 13. Monorepo Support (3 tests)
- ❌ test_monorepo_multiple_languages_detected
- ❌ test_monorepo_separate_caches_per_module
- ❌ test_monorepo_cross_module_dependency_mapping

**P3 SUBTOTAL**: 3 tests

---

## Summary

| Priority | Existing | Missing | Total | Status |
|----------|----------|---------|-------|--------|
| Core/Tier | 45 | — | 45 | ✅ 45/45 (100%) |
| P0 | — | 18 | 18 | ❌ 0/18 (0%) |
| P1 | — | 33 | 33 | ❌ 0/33 (0%) |
| P2 | — | 11 | 11 | ❌ 0/11 (0%) |
| P3 | — | 3 | 3 | ❌ 0/3 (0%) |
| **TOTAL** | **45** | **65** | **110** | **41/110 (37%)** |

---

## Next Action Items

### Immediate (This Session)
- ✅ Add additional test categories to assessment (DONE)
- ✅ Check for existing tests in each category (DONE)
- ✅ Create this checklist (DONE)

### Phase 1: Quick Wins (~3-4 hours)
1. Determinism tests (4 tests)
2. Language detection (5 tests)
3. Cache file creation (2-3 tests)
4. Gitignore patterns (2-3 tests)

### Phase 2: Core Features (~4-5 hours)
5. Framework detection (6 tests)
6. Entrypoint detection (5 tests)
7. Cache mtime/modification (4 tests)
8. Custom rules edge cases (4 tests)

### Phase 3: Polish (~3-4 hours)
9. Error handling (7 tests)
10. Response config (3 tests)
11. Progress reporting (2 tests)
12. Limits configuration (3 tests)

### Phase 4: Future (Post v1.0)
13. Monorepo support (3 tests)

---

## Files to Create/Modify

### New Test Files Needed
- `tests/tools/crawl_project/test_determinism.py` (4 tests)
- `tests/tools/crawl_project/test_language_detection.py` (5 tests)
- `tests/tools/crawl_project/test_framework_detection.py` (6 tests)
- `tests/tools/crawl_project/test_entrypoint_detection.py` (5 tests)
- `tests/tools/crawl_project/test_cache_lifecycle.py` (7 tests)
- `tests/tools/crawl_project/test_gitignore_behavior.py` (4 tests)
- `tests/tools/crawl_project/test_error_handling.py` (7 tests)
- `tests/tools/crawl_project/test_result_schema.py` (5 tests)

### Existing Files to Update
- `tests/tools/crawl_project/conftest.py` - Add new fixtures as needed
- `tests/tools/crawl_project/test_crawl_project_contracts.py` - Add custom rules edge case tests
- `docs/testing/test_assessments/crawl_project_test_assessment.md` - This document (UPDATED ✅)

---

## Acceptance Criteria for Release

### Release Gate 1: Core Functionality (P0 + Quick Wins)
- ✅ 4/4 MCP tier tests passing
- ⚠️ 18/20 P0 tests (schema, language, license, determinism)
- ✅ ~10-15 quick win tests

**Status**: Ready for internal testing

### Release Gate 2: High-Priority Features (P0 + P1)
- ✅ All P0 tests (20)
- ✅ All P1 tests (35)
- ✅ Core framework/entrypoint/cache tests

**Status**: Ready for customer preview

### Release Gate 3: Full Coverage (P0 + P1 + P2)
- ✅ All P0-P2 tests (66)
- ⚠️ P3 tests deferred to v1.1

**Status**: Ready for production release

### Release Gate 4: Comprehensive (All tests)
- ✅ All tests (P0-P3, 110 total)

**Status**: Long-term goal (v1.1+)

