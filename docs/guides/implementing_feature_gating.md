# Implementing Feature Gating in MCP Tools

[20251225_DOCS] Guide for implementing parameter-level feature gating so all tools are available at all tiers with different capabilities.

## Overview

**Goal**: Make all 20 MCP tools available at COMMUNITY tier, with features/parameters gated by tier.

**Before**: Tools were completely hidden from lower tiers
```python
# tool_registry.py
tier="pro"  # Tool not available to COMMUNITY users
```

**After**: All tools available, features restricted
```python
# tool_registry.py  
tier="community"  # Available at all tiers, features gated

# At runtime:
caps = get_tool_capabilities("security_scan", "community")
max_findings = caps["limits"]["max_findings"]  # 10 for community
```

## Architecture

### 1. Capability Matrix (`licensing/features.py`)

The central source of truth for what each tier gets:

```python
TOOL_CAPABILITIES = {
    "security_scan": {
        "community": {
            "enabled": True,
            "capabilities": {
                "basic_vulnerabilities",
                "single_file_taint",
            },
            "limits": {
                "max_findings": 10,
                "vulnerability_types": ["sql_injection", "xss", "command_injection"],
            },
            "description": "Basic security scanning with limited findings"
        },
        "pro": {
            "enabled": True,
            "capabilities": {
                "basic_vulnerabilities",
                "single_file_taint",
                "advanced_taint_flow",
                "full_vulnerability_list",
                "remediation_suggestions",
                "owasp_categorization",
            },
            "limits": {
                "max_findings": None,  # Unlimited
                "vulnerability_types": "all",
            },
            "description": "Advanced security analysis with full results"
        },
        "enterprise": {
            "enabled": True,
            "capabilities": {
                # All PRO capabilities +
                "cross_file_taint",
                "compliance_reporting",
                "custom_security_rules",
                "automated_remediation",
                "org_wide_scanning",
            },
            "limits": {
                "max_findings": None,
                "vulnerability_types": "all",
            },
            "description": "Enterprise-grade security with compliance"
        }
    }
}
```

### 2. Runtime API (`licensing/features.py`)

Functions to query capabilities:

```python
# Get capabilities for a tool at current tier
caps = get_tool_capabilities("security_scan", "community")

# Check if specific capability exists
if has_capability("security_scan", "advanced_taint_flow", tier):
    result["taint_flows"] = analyze_advanced_taint(code)

# Get upgrade hint for missing feature
hint = get_upgrade_hint("security_scan", "compliance_reporting", "pro")
# Returns: "compliance_reporting requires ENTERPRISE tier. Upgrade to access compliance reports and audit trails."
```

### 3. Tool Registry (`tiers/tool_registry.py`)

All tools set to `tier="community"`:

```python
DEFAULT_TOOLS = {
    "security_scan": ToolSpec(
        name="security_scan",
        tier="community",  # Changed from "pro"
        description="Security vulnerability scanning with tier-based features",
        # ... rest of spec
    ),
    # All 20 tools now have tier="community"
}
```

## Implementation Pattern

### Step 1: Update Tool Registration

```python
# tiers/tool_registry.py
{
    "tool_id": ToolSpec(
        name="tool_name",
        tier="community",  # Make available at all tiers
        description="Description mentioning tier-based features",
        # ...
    )
}
```

### Step 2: Define Capabilities

```python
# licensing/features.py
TOOL_CAPABILITIES = {
    "your_tool": {
        "community": {
            "enabled": True,
            "capabilities": {"basic_feature"},
            "limits": {
                "max_results": 10,
                "depth": 1,
            }
        },
        "pro": {
            "enabled": True,
            "capabilities": {"basic_feature", "advanced_feature"},
            "limits": {
                "max_results": None,
                "depth": 5,
            }
        },
        "enterprise": {
            "enabled": True,
            "capabilities": {
                "basic_feature",
                "advanced_feature", 
                "org_feature"
            },
            "limits": {
                "max_results": None,
                "depth": None,  # Unlimited
            }
        }
    }
}
```

### Step 3: Implement Gating in Tool

```python
async def your_tool_handler(params: dict) -> dict:
    """
    Tool handler with tier-based feature gating.
    """
    # 1. Get current tier
    tier = get_current_tier()
    
    # 2. Get capabilities for this tool at this tier
    caps = get_tool_capabilities("your_tool", tier)
    
    # 3. Perform basic operation (available to all tiers)
    results = perform_basic_operation(params)
    
    # 4. Apply limits
    max_results = caps["limits"]["max_results"]
    if max_results and len(results) > max_results:
        truncated_results = results[:max_results]
        upgrade_hint = get_upgrade_hint("your_tool", "unlimited_results", tier)
        return {
            "results": truncated_results,
            "truncated": True,
            "upgrade_hints": [upgrade_hint]
        }
    
    # 5. Add advanced features if available
    response = {"results": results, "tier": tier}
    
    if has_capability("your_tool", "advanced_feature", tier):
        response["advanced_data"] = perform_advanced_analysis(results)
    
    if has_capability("your_tool", "org_feature", tier):
        response["org_data"] = perform_org_analysis(results)
    
    # 6. Add upgrade hints for missing capabilities
    if tier != "enterprise":
        missing = get_missing_capabilities("your_tool", tier)
        if missing:
            response["upgrade_hints"] = [
                get_upgrade_hint("your_tool", cap, tier)
                for cap in missing[:2]  # Show top 2 missing features
            ]
    
    return response
```

## Real-World Examples

### Example 1: `security_scan` - Limit Findings

```python
async def security_scan(code: str, file_path: str = None) -> dict:
    tier = get_current_tier()
    caps = get_tool_capabilities("security_scan", tier)
    
    # Run full scan (all tiers)
    all_vulnerabilities = run_security_scan(code, file_path)
    
    # Apply findings limit for COMMUNITY
    max_findings = caps["limits"]["max_findings"]
    if max_findings:
        vulnerabilities = all_vulnerabilities[:max_findings]
        truncated = len(all_vulnerabilities) > max_findings
    else:
        vulnerabilities = all_vulnerabilities
        truncated = False
    
    result = {
        "tier": tier,
        "vulnerabilities": vulnerabilities,
        "truncated": truncated,
    }
    
    # Add truncation message
    if truncated:
        total = len(all_vulnerabilities)
        result["upgrade_hints"] = [
            f"Showing {max_findings}/{total} vulnerabilities.",
            get_upgrade_hint("security_scan", "full_vulnerability_list", tier)
        ]
    
    # PRO+: Add advanced taint analysis
    if has_capability("security_scan", "advanced_taint_flow", tier):
        result["taint_flows"] = analyze_advanced_taint(code, vulnerabilities)
    
    # PRO+: Add remediation suggestions
    if has_capability("security_scan", "remediation_suggestions", tier):
        result["remediation"] = generate_remediation(vulnerabilities)
    
    # ENTERPRISE: Add compliance reporting
    if has_capability("security_scan", "compliance_reporting", tier):
        result["compliance"] = generate_compliance_report(vulnerabilities)
    
    return result
```

### Example 2: `symbolic_execute` - Limit Paths

```python
async def symbolic_execute(code: str, max_paths: int = 10) -> dict:
    tier = get_current_tier()
    caps = get_tool_capabilities("symbolic_execute", tier)
    
    # Apply tier-based path limit
    tier_max_paths = caps["limits"]["max_paths"]
    actual_max_paths = min(max_paths, tier_max_paths) if tier_max_paths else max_paths
    
    result = {
        "tier": tier,
        "requested_paths": max_paths,
        "actual_paths": actual_max_paths,
    }
    
    # Notify if limited
    if tier_max_paths and max_paths > tier_max_paths:
        result["upgrade_hints"] = [
            f"Path exploration limited to {tier_max_paths} (requested {max_paths}).",
            get_upgrade_hint("symbolic_execute", "unlimited_paths", tier)
        ]
    
    # Run symbolic execution with limit
    paths = run_symbolic_execution(code, max_paths=actual_max_paths)
    result["paths"] = paths
    
    # PRO+: Add constraint solving
    if has_capability("symbolic_execute", "advanced_constraint_solving", tier):
        result["constraints"] = solve_complex_constraints(paths)
    
    # ENTERPRISE: Add path prioritization
    if has_capability("symbolic_execute", "path_prioritization", tier):
        result["prioritized_paths"] = prioritize_paths(paths)
    
    return result
```

### Example 3: `extract_code` - Cross-File Dependencies

```python
async def extract_code(
    file_path: str,
    target_type: str,
    target_name: str,
    include_cross_file_deps: bool = False,
    max_depth: int = 1,
) -> dict:
    tier = get_current_tier()
    caps = get_tool_capabilities("extract_code", tier)
    
    # Extract target symbol (all tiers)
    extracted = extract_symbol(file_path, target_type, target_name)
    
    result = {
        "tier": tier,
        "code": extracted["code"],
        "lines": extracted["lines"],
    }
    
    # Check cross-file permission
    if include_cross_file_deps:
        if not caps["limits"]["include_cross_file_deps"]:
            result["error"] = "Cross-file dependencies require PRO tier"
            result["upgrade_hints"] = [
                get_upgrade_hint("extract_code", "cross_file_deps", tier)
            ]
            return result
        
        # Apply depth limit
        tier_max_depth = caps["limits"]["max_depth"]
        if tier_max_depth:
            actual_depth = min(max_depth, tier_max_depth)
            if max_depth > tier_max_depth:
                result["limited_depth"] = True
                result["upgrade_hints"] = [
                    f"Depth limited to {tier_max_depth} (requested {max_depth}).",
                    get_upgrade_hint("extract_code", "unlimited_depth", tier)
                ]
        else:
            actual_depth = max_depth
        
        # Resolve dependencies
        result["dependencies"] = resolve_dependencies(
            file_path,
            extracted,
            depth=actual_depth
        )
    
    return result
```

### Example 4: `crawl_project` - File Limits

```python
async def crawl_project(
    directory: str,
    complexity_threshold: int = 10,
) -> dict:
    tier = get_current_tier()
    caps = get_tool_capabilities("crawl_project", tier)
    
    # Discover files (all tiers)
    all_files = discover_files(directory)
    
    # Apply file limit
    max_files = caps["limits"]["max_files"]
    if max_files and len(all_files) > max_files:
        files = all_files[:max_files]
        truncated = True
    else:
        files = all_files
        truncated = False
    
    result = {
        "tier": tier,
        "file_count": len(files),
        "files": [f["path"] for f in files],
    }
    
    # Notify if truncated
    if truncated:
        result["truncated"] = True
        result["upgrade_hints"] = [
            f"Analyzed {max_files}/{len(all_files)} files.",
            get_upgrade_hint("crawl_project", "unlimited_files", tier)
        ]
    
    # COMMUNITY: Discovery mode (basic stats only)
    if tier == "community":
        result["mode"] = "discovery"
        result["entrypoints"] = detect_entrypoints(files)
        result["basic_stats"] = {
            "total_lines": sum(f.get("lines", 0) for f in files),
            "languages": list(set(f.get("language") for f in files)),
        }
        return result
    
    # PRO+: Full AST parsing
    if has_capability("crawl_project", "full_ast_parsing", tier):
        result["mode"] = "deep"
        parsed = parse_all_files(files)
        result["functions"] = extract_functions(parsed)
        result["classes"] = extract_classes(parsed)
    
    # PRO+: Complexity analysis
    if has_capability("crawl_project", "complexity_analysis", tier):
        result["complexity_warnings"] = find_complex_functions(
            result["functions"],
            complexity_threshold
        )
    
    # ENTERPRISE: Organization-wide features
    if has_capability("crawl_project", "org_indexing", tier):
        result["org_index"] = index_for_org(parsed)
    
    return result
```

## Common Patterns

### Pattern 1: Truncation with Upgrade Hint

```python
# Apply limit
max_items = caps["limits"]["max_items"]
if max_items and len(all_items) > max_items:
    items = all_items[:max_items]
    result["truncated"] = True
    result["upgrade_hints"] = [
        f"Showing {max_items}/{len(all_items)} items.",
        get_upgrade_hint(tool_id, "unlimited_items", tier)
    ]
else:
    items = all_items
```

### Pattern 2: Feature Check Before Execution

```python
# Only run expensive operation if tier supports it
if has_capability(tool_id, "expensive_feature", tier):
    result["expensive_data"] = run_expensive_operation()
else:
    # Optionally add upgrade hint
    result["upgrade_hints"] = [
        get_upgrade_hint(tool_id, "expensive_feature", tier)
    ]
```

### Pattern 3: Graceful Degradation

```python
# Basic feature works for all tiers
result = {"basic_results": perform_basic_operation()}

# Add advanced features based on tier
if tier == "pro" or tier == "enterprise":
    result["advanced_results"] = perform_advanced_operation()

if tier == "enterprise":
    result["org_results"] = perform_org_operation()

# Always show what's possible
result["available_capabilities"] = list(caps["capabilities"])
```

### Pattern 4: Parameter Validation

```python
def validate_params(tool_id: str, tier: str, params: dict) -> tuple[bool, str]:
    """
    Validate that requested parameters are allowed at this tier.
    
    Returns:
        (is_valid, error_message)
    """
    caps = get_tool_capabilities(tool_id, tier)
    
    # Check if cross-file deps requested but not allowed
    if params.get("include_cross_file_deps"):
        if not caps["limits"]["include_cross_file_deps"]:
            return False, "Cross-file dependencies require PRO tier"
    
    # Check depth limit
    if "max_depth" in params:
        tier_max = caps["limits"]["max_depth"]
        if tier_max and params["max_depth"] > tier_max:
            return False, f"Max depth is {tier_max} at {tier.upper()} tier"
    
    return True, ""
```

## Testing

### Unit Tests for Capability System

```python
def test_get_tool_capabilities():
    """Test capability retrieval for all tiers."""
    caps_community = get_tool_capabilities("security_scan", "community")
    assert caps_community["limits"]["max_findings"] == 10
    assert "basic_vulnerabilities" in caps_community["capabilities"]
    
    caps_pro = get_tool_capabilities("security_scan", "pro")
    assert caps_pro["limits"]["max_findings"] is None  # Unlimited
    assert "advanced_taint_flow" in caps_pro["capabilities"]

def test_has_capability():
    """Test capability checks."""
    assert has_capability("security_scan", "basic_vulnerabilities", "community")
    assert not has_capability("security_scan", "advanced_taint_flow", "community")
    assert has_capability("security_scan", "advanced_taint_flow", "pro")

def test_get_upgrade_hint():
    """Test upgrade hint generation."""
    hint = get_upgrade_hint("security_scan", "advanced_taint_flow", "community")
    assert "PRO" in hint
    assert "advanced_taint_flow" in hint
```

### Integration Tests for Gating

```python
@pytest.mark.asyncio
async def test_security_scan_community_limits():
    """Test that COMMUNITY tier respects max_findings limit."""
    # Mock license to return COMMUNITY tier
    with mock_tier("community"):
        # Create code with 20 vulnerabilities
        code = generate_vulnerable_code(vuln_count=20)
        
        result = await security_scan(code)
        
        # Should only return 10 findings
        assert len(result["vulnerabilities"]) == 10
        assert result["truncated"] is True
        assert "upgrade_hints" in result

@pytest.mark.asyncio
async def test_security_scan_pro_unlimited():
    """Test that PRO tier gets unlimited findings."""
    with mock_tier("pro"):
        code = generate_vulnerable_code(vuln_count=20)
        
        result = await security_scan(code)
        
        # Should return all 20 findings
        assert len(result["vulnerabilities"]) == 20
        assert result.get("truncated") is False
        assert "taint_flows" in result  # PRO feature

@pytest.mark.asyncio
async def test_extract_code_community_no_cross_file():
    """Test that COMMUNITY cannot use cross-file deps."""
    with mock_tier("community"):
        result = await extract_code(
            "test.py",
            "function",
            "foo",
            include_cross_file_deps=True
        )
        
        assert "error" in result
        assert "upgrade_hints" in result
```

## Migration Checklist

For each tool being updated:

- [ ] Update `tool_registry.py`: Change `tier` to `"community"`
- [ ] Add capabilities to `features.py`: Define `community`, `pro`, `enterprise` capabilities
- [ ] Update tool handler:
  - [ ] Add `get_current_tier()` call
  - [ ] Add `get_tool_capabilities()` call
  - [ ] Implement basic feature (available to all tiers)
  - [ ] Add tier-based limits (max results, depth, etc.)
  - [ ] Add capability checks for advanced features
  - [ ] Add upgrade hints for truncated/missing features
- [ ] Update tests:
  - [ ] Test COMMUNITY tier with limits
  - [ ] Test PRO tier with advanced features
  - [ ] Test ENTERPRISE tier with all features
  - [ ] Test upgrade hints appear correctly
- [ ] Update documentation:
  - [ ] Tool description mentions tier-based features
  - [ ] README shows tool available at all tiers
  - [ ] Examples demonstrate different tier behaviors

## Best Practices

1. **Always Provide Value**: Even at COMMUNITY tier, provide useful results
2. **Clear Messaging**: Use upgrade hints to explain why features are limited
3. **Graceful Degradation**: Never error out; return what you can
4. **Consistent Patterns**: Use same capability-checking code across tools
5. **Test All Tiers**: Ensure each tier gets expected features
6. **Document Clearly**: Show capability differences in tool descriptions

## See Also

- [features.py](../../src/code_scalpel/licensing/features.py) - Capability matrix definitions
- [feature_gating_analysis.md](../architecture/feature_gating_analysis.md) - Architecture analysis
- [feature_gating_example.py](../../examples/feature_gating_example.py) - Working examples
- [TIER_CONFIGURATION.md](../TIER_CONFIGURATION.md) - Tier comparison table
