# JWT License System - Quick Reference for Tool Handlers

[20251225_REFERENCE] v1.0.0 - Tool handler integration quick reference

## 3-Step Integration Pattern

Every tool handler follows this pattern:

```python
from code_scalpel.licensing import get_current_tier, get_tool_capabilities

def my_tool_handler(code: str, options: dict):
    # STEP 1: Get current tier
    tier = get_current_tier()
    
    # STEP 2: Get capabilities for this tool at this tier
    caps = get_tool_capabilities("my_tool", tier)
    
    # STEP 3: Process, apply limits, add features
    result = do_analysis(code)
    
    # Apply tier-based limits
    if caps.limits.get("max_results"):
        result = result[:caps.limits["max_results"]]
    
    # Add tier-specific features
    if "advanced_feature" in caps.capabilities:
        result = add_advanced_processing(result)
    
    return result
```

## Get Tier

```python
from code_scalpel.licensing import get_current_tier

tier = get_current_tier()  # "community", "pro", or "enterprise"
```

**Returns**: String tier name

## Get Capabilities

```python
from code_scalpel.licensing import get_tool_capabilities

caps = get_tool_capabilities("tool_name", tier)

# Structure:
# {
#     "capabilities": [...],  # Features available at this tier
#     "limits": {...},        # Tier-based limits (max_results, max_depth, etc.)
# }
```

**Returns**: Dictionary with `capabilities` array and `limits` dict

## Apply Limits

```python
# Get limit value
max_findings = caps.limits.get("max_findings")

# Apply to results
if max_findings:
    results = results[:max_findings]
```

## Add Features

```python
# Check if feature available
if "remediation_suggestions" in caps.capabilities:
    results = add_remediation_hints(results)

if "code_smell_detection" in caps.capabilities:
    results = add_code_smells(results)
```

## Example: security_scan Handler

```python
from code_scalpel.licensing import get_current_tier, get_tool_capabilities

def security_scan_handler(code: str, options: dict):
    # 1. Get tier
    tier = get_current_tier()
    
    # 2. Get capabilities
    caps = get_tool_capabilities("security_scan", tier)
    
    # 3. Run basic analysis
    vulnerabilities = run_taint_analysis(code)
    
    # Apply tier limits
    max_findings = caps.limits.get("max_findings")
    if max_findings:
        vulnerabilities = vulnerabilities[:max_findings]
    
    # Add Pro+ features
    if "remediation_suggestions" in caps.capabilities:
        vulnerabilities = add_remediation_hints(vulnerabilities)
    
    # Add Enterprise features
    if "compliance_mapping" in caps.capabilities:
        vulnerabilities = add_compliance_context(vulnerabilities)
    
    return {
        "vulnerabilities": vulnerabilities,
        "tier": tier,
    }
```

## Common Limits by Tool

| Tool | Community | Pro | Enterprise |
|------|-----------|-----|------------|
| `security_scan` | 10 findings | Unlimited | Unlimited |
| `crawl_project` | All files | All files | All files (indexed) |
| `extract_code` | 1 hop | 5 hops | Unlimited |
| `symbolic_execute` | 10 paths | 100 paths | Unlimited |
| `get_call_graph` | 5 depth, 100 nodes | 15 depth, 500 nodes | Unlimited |

## Common Features by Tier

### Community (All Tools)
- Basic functionality
- Standard limits
- Local analysis only

### Pro (All Tools)
- Advanced features
- Higher limits
- Framework detection
- Context awareness
- Cross-file analysis

### Enterprise (All Tools)
- All Pro features
- No limits
- Formal verification
- Compliance features
- Multi-repo support

## Testing Your Tool

```bash
# Test Community tier
python -c "from code_scalpel.licensing import get_tool_capabilities; print(get_tool_capabilities('my_tool', 'community'))"

# Test Pro tier
export CODE_SCALPEL_LICENSE_PATH="/path/to/pro.license.jwt"
python -c "from code_scalpel.licensing import get_tool_capabilities; print(get_tool_capabilities('my_tool', 'pro'))"

# Test Enterprise tier
export CODE_SCALPEL_LICENSE_PATH="/path/to/enterprise.license.jwt"
python -c "from code_scalpel.licensing import get_tool_capabilities; print(get_tool_capabilities('my_tool', 'enterprise'))"
```

## Generate Test License

```bash
python -m code_scalpel.licensing.jwt_generator \
    --tier pro \
    --customer "test" \
    --duration 365 \
    --algorithm HS256 \
    --secret "test_secret_key_12345" \
    --print
```

## Common Patterns

### Pattern 1: Enforce Limits

```python
# Get max results for this tier
max_results = caps.limits.get("max_results")

# Apply limit
if max_results:
    results = results[:max_results]
```

### Pattern 2: Check Feature

```python
# Add feature if available
if "feature_name" in caps.capabilities:
    results = add_feature(results)
```

### Pattern 3: Conditional Processing

```python
# Different processing based on tier
if "deep_analysis" in caps.capabilities:
    results = deep_analyze(code)
else:
    results = quick_analyze(code)
```

### Pattern 4: Get Limit Value

```python
# Get specific limit (returns None if not set)
limit = caps.limits.get("max_depth", 5)  # Default to 5 if not specified

# Use in processing
nodes = get_nodes(code, max_depth=limit)
```

## Integration Checklist

For each tool handler:

- [ ] Import `get_current_tier` and `get_tool_capabilities`
- [ ] Call `tier = get_current_tier()` at start
- [ ] Call `caps = get_tool_capabilities(tool_name, tier)`
- [ ] Apply limits from `caps.limits`
- [ ] Add features from `caps.capabilities`
- [ ] Return results (no upgrade hints!)
- [ ] Test with all 3 tiers
- [ ] Verify limits enforced
- [ ] Verify features available as expected
- [ ] Add unit tests for tier behavior

## Expected Changes Per Tool

**Scope**: 15-30 minutes per tool
**Pattern**: Consistent 3-step pattern
**Testing**: 2-3 test cases per tool (community/pro/enterprise)
**Documentation**: Update docstring to mention tier-based behavior

## Files You'll Need

| File | Purpose |
|------|---------|
| `src/code_scalpel/licensing/__init__.py` | Import `get_current_tier`, `get_tool_capabilities` |
| `docs/JWT_LICENSE_IMPLEMENTATION_GUIDE.md` | Full integration guide |
| `examples/jwt_license_example.py` | Working examples |
| `tests/licensing/test_jwt_integration.py` | Test patterns |

## Don't Forget

❌ **Don't add upgrade hints** - Documentation is authoritative
❌ **Don't skip the license check** - Even Community tier needs to be detected
❌ **Don't hardcode limits** - Always get from capabilities
❌ **Don't assume features exist** - Always check with `in caps.capabilities`

✅ **Do check limits exist** - Some tiers have no limit (None)
✅ **Do return tier in response** - Helps with testing and debugging
✅ **Do test all 3 tiers** - Each has different behavior
✅ **Do keep pattern consistent** - All 20 tools use same 3 steps

## Support

- Questions? See [Implementation Guide](docs/JWT_LICENSE_IMPLEMENTATION_GUIDE.md)
- Examples? See [jwt_license_example.py](examples/jwt_license_example.py)
- Tests? See [test_jwt_integration.py](tests/licensing/test_jwt_integration.py)
- Architecture? See [ARCHITECTURAL_DECISIONS_v1.0.0.md](docs/architecture/ARCHITECTURAL_DECISIONS_v1.0.0.md)

---

**Quick Links**:
- JWT System: [src/code_scalpel/licensing/](src/code_scalpel/licensing/)
- Implementation: [docs/JWT_LICENSE_IMPLEMENTATION_GUIDE.md](docs/JWT_LICENSE_IMPLEMENTATION_GUIDE.md)
- Status: ✅ READY FOR INTEGRATION
