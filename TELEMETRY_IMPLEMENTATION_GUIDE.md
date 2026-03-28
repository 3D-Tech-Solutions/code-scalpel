# Telemetry Implementation Guide

Quick guide for adding telemetry to Code Scalpel MCP tools.

## Quick Start

### 1. Add Imports

```python
from code_scalpel import telemetry
import time
```

### 2. Add Timing and Telemetry Wrap

```python
async def tool_function(...) -> Any:
    start_time = time.time()
    try:
        # ... tool logic ...
        result = ...
        duration_ms = (time.time() - start_time) * 1000

        # Emit success telemetry
        telemetry.emit_tool_event(
            tool_name="tool_name",
            tier_applied=tier,  # or _get_current_tier()
            duration_ms=float(duration_ms),
            status="success",
            input_summary={...},
            output_summary={...},
        )

        return result
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000

        # Emit failure telemetry
        telemetry.emit_tool_event(
            tool_name="tool_name",
            tier_applied=_get_current_tier(),
            duration_ms=float(duration_ms),
            status="failure",
            input_summary={...},
            error=str(e),
        )
        raise
```

## Tools Needing Telemetry

### Graph Tools (graph.py)

#### ✅ get_call_graph_tool - DONE
Captures: entry_point, depth, circular_import_check
Returns: node_count, edge_count, path_count, truncated

#### ❌ get_graph_neighborhood_tool
Add at line ~276 (before `return result`):
```python
    telemetry.emit_tool_event(
        tool_name="get_graph_neighborhood",
        tier_applied=_get_current_tier(),
        duration_ms=float((time.time() - start_time) * 1000),
        status="success",
        input_summary={
            "center_node_id": center_node_id,
            "k": k,
            "max_nodes": max_nodes,
            "direction": direction,
        },
        output_summary={
            "node_count": len(result.nodes) if result.nodes else 0,
            "edge_count": len(result.edges) if result.edges else 0,
            "depth_reached": getattr(result, 'depth_reached', 0),
        },
    )
```

#### ❌ get_project_map_tool
Add before `return result`:
```python
    telemetry.emit_tool_event(
        tool_name="get_project_map",
        tier_applied=_get_current_tier(),
        duration_ms=float((time.time() - start_time) * 1000),
        status="success",
        input_summary={
            "complexity_threshold": complexity_threshold,
            "detect_service_boundaries": detect_service_boundaries,
        },
        output_summary={
            "file_count": len(result.files) if result.files else 0,
            "total_symbols": getattr(result, 'total_symbols', 0),
            "max_complexity": getattr(result, 'max_complexity', 0),
        },
    )
```

#### ❌ get_cross_file_dependencies_tool
Add before `return result`:
```python
    telemetry.emit_tool_event(
        tool_name="get_cross_file_dependencies",
        tier_applied=_get_current_tier(),
        duration_ms=float((time.time() - start_time) * 1000),
        status="success",
        input_summary={
            "target_file": target_file,
            "target_symbol": target_symbol,
            "max_depth": max_depth,
        },
        output_summary={
            "dependency_count": len(result.dependencies) if result.dependencies else 0,
            "max_depth_reached": getattr(result, 'max_depth_reached', 0),
            "file_count": len(result.files) if result.files else 0,
        },
    )
```

#### ❌ cross_file_security_scan_tool
Add before `return result`:
```python
    telemetry.emit_tool_event(
        tool_name="cross_file_security_scan",
        tier_applied=_get_current_tier(),
        duration_ms=float((time.time() - start_time) * 1000),
        status="success",
        input_summary={
            "max_depth": max_depth,
            "confidence_threshold": confidence_threshold,
        },
        output_summary={
            "vulnerability_count": len(result.vulnerabilities) if result.vulnerabilities else 0,
            "high_confidence_count": sum(1 for v in (result.vulnerabilities or [])
                                        if v.get('confidence', 0) >= 0.8),
        },
    )
```

### Security Tools (security.py)

#### ❌ unified_sink_detect
Add before `return make_envelope`:
```python
    telemetry.emit_tool_event(
        tool_name="unified_sink_detect",
        tier_applied=tier,
        duration_ms=float((time.time() - start_time) * 1000),
        status="success" if result.success else "failure",
        input_summary={
            "language": language,
            "code_provided": code is not None,
            "confidence_threshold": confidence_threshold,
        },
        output_summary={
            "sink_count": len(result.sinks) if result.sinks else 0,
            "warning_count": len(result.warnings) if result.warnings else 0,
        },
    )
```

#### ❌ type_evaporation_scan
Add before `return make_envelope`:
```python
    telemetry.emit_tool_event(
        tool_name="type_evaporation_scan",
        tier_applied=tier,
        duration_ms=float((time.time() - start_time) * 1000),
        status="success" if result.success else "failure",
        input_summary={
            "frontend_file": frontend_file_path is not None,
            "backend_file": backend_file_path is not None,
        },
        output_summary={
            "warning_count": len(result.warnings) if result.warnings else 0,
            "erosion_locations": len(result.erosion_points) if result.erosion_points else 0,
        },
    )
```

### Extraction Tools (extraction.py)

#### ❌ rename_symbol
Add before `return make_envelope` (see existing pattern in extract_code):
```python
    # Already has telemetry - verify it's emitting correctly
    # Check lines around where rename_symbol returns
```

#### ❌ update_symbol
Add before `return make_envelope` (see existing pattern in extract_code):
```python
    # Already has telemetry - verify it's emitting correctly
    # Check lines around where update_symbol returns
```

#### ❌ simulate_refactor
Add before `return make_envelope`:
```python
    telemetry.emit_tool_event(
        tool_name="simulate_refactor",
        tier_applied=tier,
        duration_ms=float((time.time() - start_time) * 1000),
        status="success" if result.success else "failure",
        input_summary={
            "original_code_provided": original_code is not None,
            "patch_provided": patch is not None,
            "new_code_provided": new_code is not None,
        },
        output_summary={
            "changed_symbols": len(result.changed_symbols) if result.changed_symbols else 0,
            "safety_score": getattr(result, 'safety_score', 0),
            "behavior_changes_detected": getattr(result, 'behavior_changes', False),
        },
    )
```

### Policy Tools (policy.py)

#### ❌ validate_paths
Add before `return make_envelope`:
```python
    telemetry.emit_tool_event(
        tool_name="validate_paths",
        tier_applied=tier,
        duration_ms=float((time.time() - start_time) * 1000),
        status="success",
        input_summary={
            "path_count": len(paths),
            "project_root_provided": project_root is not None,
        },
        output_summary={
            "valid_count": sum(1 for v in result.validated if v.get('accessible')),
            "invalid_count": sum(1 for v in result.validated if not v.get('accessible')),
        },
    )
```

#### ❌ verify_policy_integrity
Add before `return make_envelope`:
```python
    telemetry.emit_tool_event(
        tool_name="verify_policy_integrity",
        tier_applied=tier,
        duration_ms=float((time.time() - start_time) * 1000),
        status="success" if result.verified else "failure",
        input_summary={
            "policy_dir": policy_dir,
            "manifest_source": manifest_source,
        },
        output_summary={
            "verified": result.verified,
            "policy_count": len(result.policies) if result.policies else 0,
        },
    )
```

#### ❌ code_policy_check
Add before `return make_envelope`:
```python
    telemetry.emit_tool_event(
        tool_name="code_policy_check",
        tier_applied=tier,
        duration_ms=float((time.time() - start_time) * 1000),
        status="success",
        input_summary={
            "path_count": len(paths),
            "rule_count": len(rules) if rules else 0,
            "compliance_standards": compliance_standards,
        },
        output_summary={
            "violation_count": len(result.violations) if result.violations else 0,
            "warning_count": len(result.warnings) if result.warnings else 0,
            "passed_rules": len(result.passed) if result.passed else 0,
        },
    )
```

### Static Analysis Tools (static_analysis.py)

#### ❌ run_static_analysis
Add before `return make_envelope`:
```python
    telemetry.emit_tool_event(
        tool_name="run_static_analysis",
        tier_applied=tier,
        duration_ms=float((time.time() - start_time) * 1000),
        status="success",
        input_summary={
            "file_path": file_path,
            "tool_count": len(tools) if tools else 0,
        },
        output_summary={
            "finding_count": len(result.findings) if result.findings else 0,
            "tools_executed": len(result.tools_run) if result.tools_run else 0,
        },
    )
```

## Testing Telemetry

### Unit Test Pattern
```python
def test_tool_emits_telemetry():
    from code_scalpel import telemetry

    telemetry.clear_events()

    # Call tool
    result = await tool_function(...)

    # Verify telemetry
    events = telemetry.get_recent_events(limit=1)
    assert len(events) > 0
    assert events[0]["tool_name"] == "expected_tool_name"
    assert events[0]["status"] == "success"
    assert events[0]["duration_ms"] > 0
    assert "key_metric" in events[0]["output_summary"]
```

### Integration Test Pattern
```python
def test_tool_logged_to_audit():
    from code_scalpel import telemetry
    from code_scalpel.audit import AuditLog

    audit_log = AuditLog(session_id="test", encryption_enabled=False)
    telemetry.set_audit_log(audit_log)

    # Call tool
    result = await tool_function(...)

    # Verify in audit log
    events = audit_log.get_events(tool_name="expected_tool_name", limit=1)
    assert len(events) > 0
    assert events[0]["status"] == "success"
```

## Checklist for Each Tool

- [ ] Add `import time` and `from code_scalpel import telemetry` to file
- [ ] Add `start_time = time.time()` at tool start
- [ ] Capture relevant output metrics from result
- [ ] Add `telemetry.emit_tool_event()` before return
- [ ] Handle both success and failure paths
- [ ] Write unit test verifying telemetry is emitted
- [ ] Verify in dashboard: tool calls appear in /api/audit/events
- [ ] Check output_summary contains meaningful metrics

## Dashboard Verification

Once telemetry is added:

1. Start MCP server: `python -m code_scalpel.mcp.server`
2. Open dashboard: `curl http://localhost:7654/`
3. Call tool via Claude/MCP client
4. Check dashboard events list
5. Expand event details to see input_summary and output_summary
6. Verify metrics match expected output

## Performance Notes

- Telemetry emission is fast (~0.5ms)
- Wrapped in try/except to never fail tool execution
- Encryption adds ~0.5ms for audit log storage
- Total overhead: ~1-2ms per tool call

## Success Metrics

When complete:
- ✅ All 25 tools emit telemetry
- ✅ Dashboard displays all tool calls with input/output
- ✅ Audit log stores encrypted event history
- ✅ Users can filter and search tool calls
- ✅ Full compliance audit trail available

