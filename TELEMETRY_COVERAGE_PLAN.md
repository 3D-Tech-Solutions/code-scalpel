# Code Scalpel Telemetry Coverage Plan

## Current Status

**Tools with Telemetry: 8 (32%)**
- ✅ analyze_code (analyze.py)
- ✅ crawl_project (context.py)
- ✅ get_file_context (context.py)
- ✅ extract_code (extraction.py)
- ✅ security_scan (security.py)
- ✅ scan_dependencies (security.py)
- ✅ symbolic_execute (symbolic.py)
- ✅ generate_unit_tests (symbolic.py)

**Tools WITHOUT Telemetry: 17 (68%)**

### Graph Tools (5)
- ❌ get_call_graph (graph.py)
- ❌ get_graph_neighborhood (graph.py)
- ❌ get_project_map (graph.py)
- ❌ get_cross_file_dependencies (graph.py)
- ❌ cross_file_security_scan (graph.py)

### Security Tools (2 - partial)
- ❌ unified_sink_detect (security.py)
- ❌ type_evaporation_scan (security.py)

### Extraction Tools (3 - partial)
- ❌ rename_symbol (extraction.py)
- ❌ update_symbol (extraction.py)
- ❌ simulate_refactor (extraction.py)

### Policy Tools (3)
- ❌ validate_paths (policy.py)
- ❌ verify_policy_integrity (policy.py)
- ❌ code_policy_check (policy.py)

### Static Analysis Tools (1)
- ❌ run_static_analysis (static_analysis.py)

---

## Implementation Strategy

### Phase 1: Dashboard Ready ✅
- [x] Audit log storage (encrypted SQLite)
- [x] Dashboard API endpoints (/api/audit/events, /api/audit/call-chain, /api/audit/status)
- [x] Dashboard frontend updated to fetch from audit log
- [x] Event rendering with input/output summaries

### Phase 2: Complete Telemetry Coverage (IN PROGRESS)

Add telemetry to all remaining 17 tools using the standard pattern:

```python
from code_scalpel import telemetry
import time

# At tool execution:
start_time = time.time()
try:
    # ... tool execution code ...
    result = ...

    # Emit success event
    telemetry.emit_tool_event(
        tool_name="tool_name",
        tier_applied=tier,
        duration_ms=float((time.time() - start_time) * 1000),
        status="success",
        input_summary={
            # Capture input parameters (user-facing config)
        },
        output_summary={
            # Capture key output metrics
        },
    )
    return result
except Exception as e:
    # Emit failure event
    telemetry.emit_tool_event(
        tool_name="tool_name",
        tier_applied=_get_current_tier(),
        duration_ms=float((time.time() - start_time) * 1000),
        status="failure",
        input_summary={...},
        error=str(e),
    )
    raise
```

---

## Tools to Add Telemetry (Recommended Order)

### HIGH PRIORITY (Most Used)
These tools are frequently called and return important analysis data.

#### 1. Graph Tools (graph.py) - 5 tools
**get_call_graph**
- Input: project_root, entry_point, depth, focus_functions
- Output: node_count, edge_count, paths_found, truncated

**get_project_map**
- Input: project_root, complexity_threshold, include_complexity
- Output: file_count, total_symbols, complexity_score

**get_cross_file_dependencies**
- Input: target_file, target_symbol
- Output: dependency_count, max_depth, confidence_scores

**get_graph_neighborhood**
- Input: center_node_id, k, max_nodes, direction
- Output: node_count, edge_count, depth_reached

**cross_file_security_scan**
- Input: project_root, entry_points, max_depth
- Output: vulnerability_count, suspicious_patterns, confidence_threshold

#### 2. Security Tools (security.py) - 2 tools
**unified_sink_detect**
- Input: code, language, confidence_threshold
- Output: sink_count, warning_count, severity_distribution

**type_evaporation_scan**
- Input: frontend_code, backend_code (optional)
- Output: type_erosion_count, severity_levels, mismatches

### MEDIUM PRIORITY (Analysis Tools)

#### 3. Extraction Tools (extraction.py) - 3 tools
**rename_symbol**
- Input: file_path, target_type, target_name, new_name
- Output: renamed_count, files_modified, error_count

**update_symbol**
- Input: file_path, target_type, target_name, operation
- Output: updated_symbol_count, lines_changed, validation_passed

**simulate_refactor**
- Input: original_code, new_code/patch
- Output: safety_score, changed_symbols, potential_issues

#### 4. Policy Tools (policy.py) - 3 tools
**code_policy_check**
- Input: paths, rules, compliance_standards
- Output: violation_count, warning_count, passed_rules

**validate_paths**
- Input: paths, project_root
- Output: valid_count, invalid_count, resolved_paths

**verify_policy_integrity**
- Input: policy_dir, manifest_source
- Output: verified, signature_valid, policy_count

### LOW PRIORITY (Infrastructure Tools)

#### 5. Static Analysis (static_analysis.py) - 1 tool
**run_static_analysis**
- Input: file_path, tools, tier
- Output: finding_count, tool_count, report_generated

---

## Implementation Checklist

### Graph Tools
- [ ] get_call_graph
- [ ] get_graph_neighborhood
- [ ] get_project_map
- [ ] get_cross_file_dependencies
- [ ] cross_file_security_scan

### Security Tools
- [ ] unified_sink_detect
- [ ] type_evaporation_scan

### Extraction Tools
- [ ] rename_symbol
- [ ] update_symbol
- [ ] simulate_refactor

### Policy Tools
- [ ] code_policy_check
- [ ] validate_paths
- [ ] verify_policy_integrity

### Static Analysis
- [ ] run_static_analysis

---

## Testing Strategy

Once telemetry is added to each tool:

1. **Unit Test**: Verify telemetry event is emitted with correct structure
2. **Integration Test**: Call tool via dashboard API and verify event in audit log
3. **Audit Log Test**: Check that event is stored in SQLite with encryption
4. **Dashboard Display**: Verify event appears in dashboard UI with input/output

Example test pattern:
```python
def test_tool_emits_telemetry():
    from code_scalpel import telemetry

    telemetry.clear_events()
    # Call tool with test inputs
    result = run_tool(...)

    # Verify event was emitted
    events = telemetry.get_recent_events(limit=1)
    assert len(events) > 0
    assert events[0]["tool_name"] == "tool_name"
    assert events[0]["status"] == "success"
    assert "key_metric" in events[0]["output_summary"]
```

---

## Dashboard Display Features

Once all tools have telemetry:

### Event List
- [x] Tool name, status, duration
- [x] Input parameters (collapsed)
- [x] Output results (collapsed)
- [x] Error messages (if failed)
- [x] Event ID, session ID, tier used

### Filtering (via /api/audit/events parameters)
- [x] By tool name
- [x] By status (success/failure)
- [x] By request ID (call chains)
- [x] Pagination (limit, offset)

### Call Chains (via /api/audit/call-chain)
- [x] Group events by request_id
- [x] Show execution order
- [x] Link related tool calls

### Statistics (via /api/audit/status)
- [x] Total events
- [x] Success/failure counts
- [x] Success rate
- [x] Tool usage breakdown

---

## Benefits of Complete Coverage

1. **Audit Trail**: Every tool call captured with full context
2. **Performance Metrics**: Track execution time and success rates
3. **Debugging**: See exact inputs and outputs for failed calls
4. **Usage Analytics**: Understand which tools are used most
5. **Compliance**: Prove analysis was performed (GDPR, SOC2, etc.)
6. **Optimization**: Identify slow tools and bottlenecks

---

## Next Steps

1. Add telemetry to Graph tools (5 tools)
2. Add telemetry to Security tools (2 tools)
3. Add telemetry to Extraction tools (3 tools)
4. Add telemetry to Policy tools (3 tools)
5. Add telemetry to Static Analysis tools (1 tool)
6. Write comprehensive integration tests
7. Update documentation

**Estimated Effort**: 2-4 hours for complete implementation
**Expected Outcome**: 100% tool telemetry coverage + full audit trail
