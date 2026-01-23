# MCP Tool Test Evaluation - Complete Assessment Index

**Date**: January 3, 2026  
**Status**: 21 tools assessed (1 approved, 20 blocking)

---

## Quick Reference - All 22 Tools

### ✅ Approved (1/22)
| # | Tool | Status | Document |
|----|------|--------|----------|
| 1 | **get_symbol_references** | ✅ APPROVED | [get_symbol_references_test_assessment.md](get_symbol_references_test_assessment.md) |

**Why this one approved**: Only tool with comprehensive tier tests + Pro/Enterprise features validated.

---

### 🔴 BLOCKING - No Tier Tests (20/22)

#### Core Analysis Tools
| # | Tool | Status | Document | Priority Gap |
|----|------|--------|----------|--------------|
| 2 | analyze_code | 🔴 BLOCKING | [analyze_code_test_assessment.md](analyze_code_test_assessment.md) | No hallucination tests + Tier tests |
| 3 | extract_code | 🔴 BLOCKING | [extract_code_test_assessment.md](extract_code_test_assessment.md) | Cross-file deps + Tier tests |
| 4 | update_symbol | 🔴 BLOCKING | [update_symbol_test_assessment.md](update_symbol_test_assessment.md) | Accuracy + Tier tests |
| 5 | crawl_project | 🔴 BLOCKING | [crawl_project_test_assessment.md](crawl_project_test_assessment.md) | Accuracy + Tier tests |

#### Security Tools
| # | Tool | Status | Document | Priority Gap |
|----|------|--------|----------|--------------|
| 6 | security_scan | 🟡 AT RISK | [security_scan_test_assessment.md](security_scan_test_assessment.md) | False positives + Tier tests |
| 7 | unified_sink_detect | 🔴 BLOCKING | [unified_sink_detect_test_assessment.md](unified_sink_detect_test_assessment.md) | JS/TS support + Tier tests |
| 8 | cross_file_security_scan | 🔴 BLOCKING | [cross_file_security_scan_test_assessment.md](cross_file_security_scan_test_assessment.md) | Taint tracking + Tier tests |
| 9 | type_evaporation_scan | 🔴 BLOCKING | [type_evaporation_scan_test_assessment.md](type_evaporation_scan_test_assessment.md) | Zod/Pydantic generation + Tier tests |
| 10 | code_policy_check | 🔴 BLOCKING | [code_policy_check_test_assessment.md](code_policy_check_test_assessment.md) | Compliance rules + Tier tests |

#### Generation & Execution Tools
| # | Tool | Status | Document | Priority Gap |
|----|------|--------|----------|--------------|
| 11 | generate_unit_tests | 🔴 BLOCKING | [generate_unit_tests_test_assessment.md](generate_unit_tests_test_assessment.md) | Path coverage + Pro/Enterprise |
| 12 | symbolic_execute | 🔴 BLOCKING | [symbolic_execute_test_assessment.md](symbolic_execute_test_assessment.md) | Loop handling + Tier tests |
| 13 | simulate_refactor | 🔴 BLOCKING | [simulate_refactor_test_assessment.md](simulate_refactor_test_assessment.md) | Patch support + Tier tests |
| 14 | scan_dependencies | 🔴 BLOCKING | [scan_dependencies_test_assessment.md](scan_dependencies_test_assessment.md) | Multi-format + Tier tests |

#### Graph & Navigation Tools
| # | Tool | Status | Document | Priority Gap |
|----|------|--------|----------|--------------|
| 15 | get_file_context | 🔴 BLOCKING | [get_file_context_test_assessment.md](get_file_context_test_assessment.md) | Accuracy + Tier tests |
| 16 | get_cross_file_dependencies | 🔴 BLOCKING | [get_cross_file_dependencies_test_assessment.md](get_cross_file_dependencies_test_assessment.md) | Circular deps + Tier tests |
| 17 | get_call_graph | 🔴 BLOCKING | [get_call_graph_test_assessment.md](get_call_graph_test_assessment.md) | Recursion + Tier tests |
| 18 | get_graph_neighborhood | 🔴 BLOCKING | [get_graph_neighborhood_test_assessment.md](get_graph_neighborhood_test_assessment.md) | Filtering + Tier tests |
| 19 | get_project_map | 🔴 BLOCKING | [get_project_map_test_assessment.md](get_project_map_test_assessment.md) | Complexity + Tier tests |

#### Utility & Infrastructure Tools
| # | Tool | Status | Document | Priority Gap |
|----|------|--------|----------|--------------|
| 20 | validate_paths | 🔴 BLOCKING | [validate_paths_test_assessment.md](validate_paths_test_assessment.md) | Permissions + Tier tests |
| 21 | verify_policy_integrity | 🟡 AT RISK | [verify_policy_integrity_test_assessment.md](verify_policy_integrity_test_assessment.md) | Edge cases + Tier tests |

---

## Assessment Summary by Category

### Release Blocking Status

| Category | Count | Blocking | % Ready |
|----------|-------|----------|---------|
| **Tier Tests** | 22 | 20 | 9% (1/22) |
| **Accuracy Tests** | 22 | 15 | 32% (7/22) |
| **Hallucination Prevention** | 22 | 10 | 55% (12/22) |
| **Pro Tier Features** | 22 | 12 | 45% (10/22) |
| **Enterprise Features** | 22 | 14 | 36% (8/22) |

### Common Gaps (By Frequency)

| Gap | Count | Tools Affected |
|-----|-------|----------------|
| **No tier tests** | 20 | All except get_symbol_references |
| **No invalid license test** | 20 | All except get_symbol_references |
| **No Pro/Enterprise tests** | 18 | All extraction/analysis tools |
| **No accuracy validation** | 15 | extract_code, crawl_project, graph tools, etc. |
| **No edge case tests** | 12 | recursion, circular deps, decorators, etc. |

---

## How to Use This Index

### 1. **For Release Managers**
- 🔴 **BLOCKING**: 20 of 22 tools require tier tests before release
- Only **get_symbol_references** is fully tested
- Cannot release without adding tier tests to remaining 20 tools

### 2. **For Test Writers**
- Start with **get_symbol_references** assessment as template
- Use the MCP_TOOL_TEST_EVALUATION_CHECKLIST.md for test structure
- Follow the "Recommendations" section in each assessment
- Priority 1 items are blocking, Priority 2/3 are post-release

### 3. **For Tool Maintainers**
- Each tool has its own assessment document
- Follow the recommended action items
- Report completion when tier tests added

### 4. **For Quality Assurance**
- Verify each tool passes tests at all three tiers:
  ```bash
  # Community (no license)
  unset CODE_SCALPEL_LICENSE_PATH
  pytest {tool_tests} -v
  
  # Pro
  export CODE_SCALPEL_LICENSE_PATH=tests/licenses/code_scalpel_license_pro_*.jwt
  pytest {tool_tests} -v
  
  # Enterprise
  export CODE_SCALPEL_LICENSE_PATH=tests/licenses/code_scalpel_license_enterprise_*.jwt
  pytest {tool_tests} -v
  ```

---

## Related Documentation

- **[MCP_TOOL_TEST_EVALUATION_CHECKLIST.md](docs/testing/MCP_TOOL_TEST_EVALUATION_CHECKLIST.md)**: Comprehensive framework for all tool testing
- **[test_evaluation_summary.md](test_evaluation_summary.md)**: Executive summary of assessment progress

---

## Master Action Items

### Phase 1: Critical Path (BLOCKING)
Priority: Add tier tests to all 22 tools

```bash
# Create tier test files for each tool
for tool in extract_code update_symbol security_scan unified_sink_detect \
            cross_file_security_scan generate_unit_tests symbolic_execute \
            crawl_project scan_dependencies get_file_context \
            get_cross_file_dependencies get_call_graph get_graph_neighborhood \
            get_project_map validate_paths verify_policy_integrity \
            type_evaporation_scan simulate_refactor code_policy_check; do
  
  echo "Creating tests/mcp_tool_verification/test_${tool}_tiers.py"
  # Use template from Section 2 of MCP_TOOL_TEST_EVALUATION_CHECKLIST.md
done
```

**Timeline**: Required before release
**Effort**: 2-4 hours per tool × 20 tools = 40-80 hours

### Phase 2: High Priority (PRE-RELEASE)
Priority: Add accuracy tests for extraction/analysis tools

**Tools**:
- analyze_code (hallucination prevention)
- extract_code (cross-file deps)
- crawl_project (structure accuracy)
- get_call_graph (recursion handling)
- get_cross_file_dependencies (circular deps)

**Timeline**: Recommended before release
**Effort**: 1-2 hours per tool × 5 tools = 5-10 hours

### Phase 3: Medium Priority (v3.4+)
Priority: Add edge case and performance tests

**Tools**: All 22 tools
**Timeline**: Post-release improvements
**Effort**: 1-3 hours per tool

---

## License Testing Commands

### Run All Tools - Community Tier
```bash
unset CODE_SCALPEL_LICENSE_PATH
pytest tests/mcp_tool_verification/ -v -k "community"
```

### Run All Tools - Pro Tier
```bash
export CODE_SCALPEL_LICENSE_PATH=tests/licenses/code_scalpel_license_pro_20260101_190345.jwt
pytest tests/mcp_tool_verification/ -v
```

### Run All Tools - Enterprise Tier
```bash
export CODE_SCALPEL_LICENSE_PATH=tests/licenses/code_scalpel_license_enterprise_20260101_190754.jwt
pytest tests/mcp_tool_verification/ -v
```

### Run Single Tool Tiers
```bash
# Example: analyze_code
pytest tests/mcp_tool_verification/test_analyze_code_tiers.py::test_analyze_code_community_no_license -v
pytest tests/mcp_tool_verification/test_analyze_code_tiers.py::test_analyze_code_pro_with_license -v
pytest tests/mcp_tool_verification/test_analyze_code_tiers.py::test_analyze_code_enterprise_with_license -v
```

---

## Assessment Artifacts

**Location**: Root directory (for easy access)
- analyze_code_test_assessment.md
- extract_code_test_assessment.md
- update_symbol_test_assessment.md
- security_scan_test_assessment.md
- unified_sink_detect_test_assessment.md
- cross_file_security_scan_test_assessment.md
- generate_unit_tests_test_assessment.md
- symbolic_execute_test_assessment.md
- crawl_project_test_assessment.md
- scan_dependencies_test_assessment.md
- get_file_context_test_assessment.md
- get_symbol_references_test_assessment.md
- get_cross_file_dependencies_test_assessment.md
- get_call_graph_test_assessment.md
- get_graph_neighborhood_test_assessment.md
- get_project_map_test_assessment.md
- validate_paths_test_assessment.md
- verify_policy_integrity_test_assessment.md
- type_evaporation_scan_test_assessment.md
- simulate_refactor_test_assessment.md
- code_policy_check_test_assessment.md

**Framework Documentation**:
- docs/testing/MCP_TOOL_TEST_EVALUATION_CHECKLIST.md
- test_evaluation_summary.md

---

## Next Steps

1. ✅ **Created**: Assessment documents for all 22 tools
2. ✅ **Created**: Test evaluation checklist framework
3. ⏭️ **Next**: Assign tier test creation to team members
4. ⏭️ **Next**: Track completion of blocked items
5. ⏭️ **Next**: Run all tools at all tiers before release
