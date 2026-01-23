# Distribution Separation Strategy

**Status**: Implemented in v1.0.0  
**Model**: Open-core with runtime tier enforcement  
**Date**: 2025-01-23

## Overview

Code Scalpel uses an **open-core model** with runtime tier enforcement rather than package separation. All code ships in a single MIT-licensed package, with behavioral restrictions enforced at runtime based on tier configuration.

## Design Decision

### Considered Approaches

1. **Separate Packages** (rejected)
   - Pros: Clear separation, Pro/Enterprise code physically separate
   - Cons: Complex build pipeline, multiple PyPI packages, version synchronization issues

2. **Build-time Exclusion** (rejected)
   - Pros: Community wheel omits restricted modules
   - Cons: Code must be written to handle missing imports, harder to maintain

3. **Runtime Tier Enforcement** ✅ (selected)
   - Pros: Single codebase, simple distribution, clear tier checks in code
   - Cons: All code visible in source, relies on licensing for enforcement

### Rationale

We chose runtime tier enforcement because:

1. **Simplicity**: Single package, single build, single distribution
2. **Transparency**: All code visible for auditing and trust
3. **Maintainability**: No conditional imports or missing module handling
4. **Developer Experience**: Easy to test all tiers in development
5. **Licensing Clarity**: MIT license for Community, commercial licenses for Pro/Enterprise

## Architecture

### Tier Configuration

```python
# In src/code_scalpel/mcp/server.py
CURRENT_TIER = "community"  # Default; can be configured via environment

def _get_current_tier() -> str:
    """Get the current tier from environment or global."""
    tier_env = os.getenv("CODE_SCALPEL_TIER", CURRENT_TIER)
    return tier_env.lower()
```

### Tier Restrictions

All restrictions are enforced at runtime within tool implementations:

| Feature | Community | Pro | Enterprise |
|---------|-----------|-----|------------|
| `crawl_project` | Discovery mode (file inventory + entrypoints) | Deep analysis (full crawl) | Deep analysis |
| `get_symbol_references` | 10 file limit | Unlimited | Unlimited |
| `get_call_graph` | Depth limit = 3 | Configurable depth | Configurable depth |
| `get_graph_neighborhood` | k limit = 1 | Configurable k | Configurable k |

### Tier Check Pattern

```python
@mcp.tool()
def some_tool(param: str) -> ToolResponseEnvelope:
    """Tool with tier-based behavior."""
    tier = _get_current_tier()
    
    if tier == "community":
        # Apply Community limitations
        result = limited_operation(param, max_items=10)
        upgrade_hint = "Upgrade to Pro for unlimited processing"
    else:
        # Pro/Enterprise: full functionality
        result = full_operation(param)
        upgrade_hint = None
    
    return ToolResponseEnvelope(
        tier=tier,
        data=result,
        upgrade_hints=[upgrade_hint] if upgrade_hint else None,
        # ... other fields
    )
```

## Verification

The distribution separation is verified using `scripts/verify_distribution_separation.py`:

```bash
python scripts/verify_distribution_separation.py
```

### Verification Checks

1. **Tier Check Presence**: Ensures `_get_current_tier()` is called in restricted features
2. **Tier Comparisons**: Verifies tier-specific logic branches exist
3. **Restriction Coverage**: Confirms all documented restrictions have implementation

### CI Integration

Add to `.github/workflows/ci.yml`:

```yaml
- name: Verify distribution separation
  run: python scripts/verify_distribution_separation.py
```

## Licensing

- **Community Edition**: MIT License (free, open source)
- **Pro Edition**: Commercial license required (set `CODE_SCALPEL_TIER=pro`)
- **Enterprise Edition**: Commercial license required (set `CODE_SCALPEL_TIER=enterprise`)

**License Enforcement**: Honor system + commercial licensing agreements. All code ships in the MIT-licensed package, but Pro/Enterprise features are licensed separately.

## Migration Path

Users can upgrade without code changes:

```bash
# Community (default)
pip install code-scalpel

# Pro (after purchasing license)
export CODE_SCALPEL_TIER=pro
# Same installation, different behavior

# Enterprise (after purchasing license)
export CODE_SCALPEL_TIER=enterprise
# Same installation, different behavior
```

## Security Considerations

1. **Source Visibility**: All code visible ≠ all code usable without license
2. **Tier Tampering**: Users can modify CURRENT_TIER, but this violates license terms
3. **Audit Trail**: Tier logged in all tool responses for compliance tracking
4. **Trust Model**: Relies on licensing compliance, not technical restrictions

This is intentional and aligns with open-source best practices.

## Implementation Details

### Files Modified

- `src/code_scalpel/mcp/server.py`:
  - Added `CURRENT_TIER` global and `_get_current_tier()`
  - Added tier checks to 4 major tools
  - All responses include `tier` field for audit trail

### Files Created

- `scripts/verify_distribution_separation.py`: Automated verification
- `docs/architecture/distribution_separation.md`: This document

### Test Coverage

- `tests/test_mcp_all_tools_contract.py`: Validates tier field in all responses
- Manual testing: Set `CODE_SCALPEL_TIER` environment variable

## Future Considerations

If physical code separation becomes necessary (e.g., for compliance):

1. Create `code-scalpel-pro` and `code-scalpel-enterprise` packages
2. Move tier-specific modules to separate packages
3. Use dynamic imports with fallback to Community behavior
4. Update verification script to check import boundaries

This would require significant refactoring but is architecturally feasible.

## References

- V1.0 Requirements: Open-core model with distribution separation
- Response Envelope: `docs/reference/mcp_response_envelope.md`
- Error Codes: `docs/reference/error_codes.md`
- Release Checklist: `docs/release_notes/RELEASE_v1.0.0_CHECKLIST.md`
