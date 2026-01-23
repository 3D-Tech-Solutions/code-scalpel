# Developer Tier Controls

[20251225_DOCS] Guide for developers to override tier limits during development and testing.

---

## Overview

Code Scalpel enforces tier-based limits on tool capabilities. During development and testing, you may need to override these limits. This guide shows you how.

## Environment Variable Override

The simplest way to change tiers is using the `CODE_SCALPEL_TIER` environment variable.

### Priority Order

Tier detection follows this priority:

1. **Environment variable `CODE_SCALPEL_TIER`** (highest priority)
2. Config file `.code-scalpel/license.json`
3. Default to `COMMUNITY` (lowest priority)

### Usage

```bash
# Set tier for current session
export CODE_SCALPEL_TIER=enterprise

# Run with specific tier (one-time)
CODE_SCALPEL_TIER=pro pytest tests/test_extract_code_tiers.py

# In test files
import os
os.environ["CODE_SCALPEL_TIER"] = "enterprise"
```

### Valid Tier Values

- `community` (default)
- `pro`
- `enterprise`

---

## Tool-Specific Limits

Limits are defined in `src/code_scalpel/licensing/features.py` in the `TOOL_CAPABILITIES` dictionary.

### Example: extract_code Limits

```python
TOOL_CAPABILITIES = {
    "extract_code": {
        "community": {
            "limits": {
                "include_cross_file_deps": False,
                "max_depth": 0,
                "max_extraction_size_mb": 1,
            }
        },
        "pro": {
            "limits": {
                "include_cross_file_deps": True,
                "max_depth": 2,
                "max_extraction_size_mb": 10,
            }
        },
        "enterprise": {
            "limits": {
                "include_cross_file_deps": True,
                "max_depth": None,  # Unlimited
                "max_extraction_size_mb": 100,
            }
        }
    }
}
```

### Modifying Limits

**Option 1: Change Environment Variable (Recommended)**

```bash
# Test enterprise features
CODE_SCALPEL_TIER=enterprise python your_script.py
```

**Option 2: Modify features.py (Development Only)**

For temporary testing, edit `src/code_scalpel/licensing/features.py`:

```python
# Temporarily give community unlimited depth
"community": {
    "limits": {
        "include_cross_file_deps": True,  # Changed from False
        "max_depth": None,                # Changed from 0
    }
}
```

⚠️ **Warning:** Don't commit changes to `features.py`. Use environment variables for testing.

**Option 3: Runtime Override (Advanced)**

For programmatic testing, you can override limits at runtime:

```python
from code_scalpel.licensing.features import TOOL_CAPABILITIES

# Temporarily override for testing
original = TOOL_CAPABILITIES["extract_code"]["community"]["limits"]["max_depth"]
TOOL_CAPABILITIES["extract_code"]["community"]["limits"]["max_depth"] = 5

try:
    # Your test code here
    result = await extract_code(...)
finally:
    # Restore original
    TOOL_CAPABILITIES["extract_code"]["community"]["limits"]["max_depth"] = original
```

---

## Testing Different Tiers

### Pytest Fixtures

Create a fixture to test all tiers:

```python
import pytest
import os

@pytest.fixture(params=["community", "pro", "enterprise"])
def tier(request, monkeypatch):
    """Parametrized fixture to test all tiers."""
    monkeypatch.setenv("CODE_SCALPEL_TIER", request.param)
    return request.param

def test_extract_code_respects_tier(tier):
    result = await extract_code(
        target_type="function",
        target_name="foo",
        code="def foo(): pass",
        include_cross_file_deps=True,  # Will be disabled for community
        context_depth=10,               # Will be capped to tier limit
    )
    
    if tier == "community":
        assert result.context_depth <= 0
    elif tier == "pro":
        assert result.context_depth <= 2
    # enterprise has no limit
```

### Monkeypatch in Tests

```python
def test_community_blocks_cross_file(monkeypatch):
    monkeypatch.setenv("CODE_SCALPEL_TIER", "community")
    # Test that cross_file_deps is disabled
    ...

def test_enterprise_unlimited_depth(monkeypatch):
    monkeypatch.setenv("CODE_SCALPEL_TIER", "enterprise")
    # Test that max_depth is unlimited
    ...
```

---

## How Tier Gating Works

### In Tool Handlers

Each tool handler checks tier and applies limits:

```python
async def extract_code(..., include_cross_file_deps: bool, context_depth: int):
    # 1. Get current tier
    tier = _get_current_tier()
    
    # 2. Get capabilities for this tool at this tier
    capabilities = get_tool_capabilities("extract_code", tier)
    limits = capabilities.get("limits", {})
    
    # 3. Enforce cross-file capability
    allowed_cross = bool(limits.get("include_cross_file_deps", False))
    if not allowed_cross:
        include_cross_file_deps = False  # Override user request
    
    # 4. Enforce depth limit
    max_depth_limit = limits.get("max_depth", None)
    if max_depth_limit is not None:
        context_depth = min(context_depth, max_depth_limit)
    
    # 5. Proceed with enforced limits
    ...
```

### Tier Detection Flow

```
Tool Handler
    ↓
_get_current_tier()
    ↓
TierDetector.detect()
    ↓
1. Check CODE_SCALPEL_TIER env var
2. Check .code-scalpel/license.json
3. Default to "community"
    ↓
Return tier string
```

---

## Configuration Files

### License Config File

Create `.code-scalpel/license.json` in your project root:

```json
{
  "tier": "enterprise",
  "license_key": "your-jwt-token-here",
  "expires": "2025-12-31T23:59:59Z"
}
```

The environment variable `CODE_SCALPEL_TIER` overrides this file.

### .env File (Project-Level)

Add to your project's `.env`:

```bash
# Default tier for local development
CODE_SCALPEL_TIER=pro

# Or for testing
CODE_SCALPEL_TIER=enterprise
```

Then load with `python-dotenv`:

```python
from dotenv import load_dotenv
load_dotenv()
```

---

## Common Scenarios

### Scenario 1: Test Cross-File Extraction (Pro Feature)

```bash
CODE_SCALPEL_TIER=pro pytest tests/test_extract_code_tiers.py::test_pro_cross_file_depth_cap
```

### Scenario 2: Test Unlimited Depth (Enterprise Feature)

```bash
CODE_SCALPEL_TIER=enterprise python examples/extract_deep_deps.py
```

### Scenario 3: CI/CD Testing

```yaml
# .github/workflows/test.yml
test-all-tiers:
  strategy:
    matrix:
      tier: [community, pro, enterprise]
  steps:
    - run: CODE_SCALPEL_TIER=${{ matrix.tier }} pytest
```

### Scenario 4: Development with Enterprise Features

```bash
# In your shell profile (.bashrc, .zshrc)
export CODE_SCALPEL_TIER=enterprise

# Now all code-scalpel tools use enterprise limits
```

---

## Debugging Tier Issues

### Check Current Tier

```python
from code_scalpel.licensing import _get_current_tier

tier = _get_current_tier()
print(f"Current tier: {tier}")
```

### Check Tool Capabilities

```python
from code_scalpel.licensing.features import get_tool_capabilities

caps = get_tool_capabilities("extract_code", "pro")
print(f"Pro limits: {caps['limits']}")
# Output: {'include_cross_file_deps': True, 'max_depth': 2, ...}
```

### Verify Limit Enforcement

```python
# See what limits would be applied
tier = "community"
caps = get_tool_capabilities("extract_code", tier)
limits = caps["limits"]

print(f"Max depth for {tier}: {limits.get('max_depth', 'unlimited')}")
print(f"Cross-file allowed: {limits.get('include_cross_file_deps', False)}")
```

---

## Best Practices

1. **Use Environment Variables for Testing**
   - Cleanest approach
   - No code changes needed
   - Easy to automate in CI/CD

2. **Don't Commit Tier Overrides**
   - Never commit changes to `features.py`
   - Never commit `.env` with tier overrides
   - Use `.env.example` for documentation

3. **Test All Tiers**
   - Use parametrized fixtures
   - Ensure tier limits are respected
   - Verify graceful degradation

4. **Document Tier Requirements**
   - Mark tests that require specific tiers
   - Use pytest markers: `@pytest.mark.requires_pro`
   - Skip tests if tier not available

---

## Related Files

- `src/code_scalpel/licensing/features.py` - Capability definitions
- `src/code_scalpel/licensing/tier_detector.py` - Tier detection logic
- `src/code_scalpel/mcp/server.py` - Tool handler implementations
- `tests/test_extract_code_tiers.py` - Example tier tests

---

## FAQ

**Q: Can I disable tier checks completely?**

A: Not recommended for production, but for development you can set `CODE_SCALPEL_TIER=enterprise` to get unlimited access.

**Q: Do tier limits apply to all tools?**

A: Yes, every tool has tier-specific capabilities and limits defined in `features.py`.

**Q: What happens if I request a feature not available in my tier?**

A: The tool will silently apply the tier limit. For example, requesting `max_depth=10` on Community tier will be capped to `max_depth=0`.

**Q: Can I create custom tiers?**

A: The infrastructure exists (`_custom_tiers` in `TierDetector`) but isn't fully implemented yet. Stick to `community`, `pro`, `enterprise` for now.

**Q: How do I get an enterprise license for testing?**

A: For development, just set `CODE_SCALPEL_TIER=enterprise`. For production, contact the Code Scalpel team for a license key.

---

## See Also

- [Tier Configuration](../TIER_CONFIGURATION.md)
- [All Tools Available Summary](../architecture/all_tools_available_summary.md)
- [Implementing Feature Gating](implementing_feature_gating.md)
