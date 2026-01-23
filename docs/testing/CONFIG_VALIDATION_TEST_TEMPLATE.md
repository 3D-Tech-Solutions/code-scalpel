# Configuration Validation Test Template

[20251223_DOCS] Configuration Validation Test Standard for All MCP Tools

## Purpose

This document provides a **reusable test template** for validating that MCP tools correctly load and enforce configuration limits from `.code-scalpel/limits.toml`. Every MCP tool MUST have configuration validation tests to ensure tier limits are properly enforced.

## Critical Requirement

**BEFORE any functional testing**, every MCP tool MUST have configuration validation tests that verify:

1. Configuration file exists and is accessible
2. Tier limits load correctly from `.code-scalpel/limits.toml`
3. Actual capability values match documented limits
4. Tool respects tier restrictions at runtime

## Test File Structure

```
tests/tools/{tool_name}/
├── __init__.py
├── test_config_validation.py  (P0 - REQUIRED FIRST)
├── test_tier_enforcement.py   (P0 - Validate runtime behavior)
├── test_functional.py          (P1 - After config validated)
└── test_integration.py         (P2 - After functional works)
```

## Template: test_config_validation.py

```python
"""
Configuration Validation Tests for {tool_name} Tool

[20251223_TEST] Phase 1 Configuration Validation - Foundation Tests

Tests verify that {tool_name} properly loads tier limits from .code-scalpel/limits.toml
and enforces them at runtime. These tests MUST pass before any functional tests are run.

Test Categories:
1. Configuration Loading - Verify limits.toml is read correctly
2. Community Tier Limits - Verify all Community tier restrictions
3. Pro Tier Limits - Verify all Pro tier capabilities and limits
4. Enterprise Tier Limits - Verify Enterprise tier has unlimited/advanced features
5. Configuration File Integrity - Verify limits.toml exists and is parseable
"""

import pytest
from pathlib import Path
from code_scalpel.licensing.features import get_tool_capabilities


class TestConfigurationLoading:
    """Verify {tool_name} loads configuration from .code-scalpel/limits.toml."""
    
    def test_config_file_exists(self):
        """Verify .code-scalpel/limits.toml configuration file exists."""
        config_path = Path(__file__).parents[4] / ".code-scalpel" / "limits.toml"
        assert config_path.exists(), \
            f"Configuration file not found: {config_path}"
    
    def test_loads_limits_from_code_scalpel_dir(self):
        """Verify get_tool_capabilities loads from .code-scalpel/limits.toml."""
        caps = get_tool_capabilities("{tool_name}", "community")
        
        # Capabilities dict should have nested "limits" key
        assert "limits" in caps, \
            "Capabilities dict must have 'limits' key with configuration values"
        
        # Limits should be a dict with actual values
        assert isinstance(caps["limits"], dict), \
            "caps['limits'] must be a dictionary"
        
        # Should have at least one limit defined
        assert len(caps["limits"]) > 0, \
            "Tool must have at least one configuration limit defined"


class TestCommunityTierLimits:
    """Verify Community tier limits from .code-scalpel/limits.toml."""
    
    def test_community_{primary_limit}_from_config(self):
        """Verify Community {primary_limit} matches limits.toml."""
        caps = get_tool_capabilities("{tool_name}", "community")
        
        # Replace with actual limit from limits.toml
        assert caps["limits"]["{primary_limit}"] == {expected_value}, \
            f"Community {primary_limit} should be {expected_value} (from limits.toml), " \
            f"got {caps['limits'].get('{primary_limit}')}"
    
    def test_community_{secondary_limit}_from_config(self):
        """Verify Community {secondary_limit} matches limits.toml."""
        caps = get_tool_capabilities("{tool_name}", "community")
        
        # Replace with actual limit from limits.toml
        assert caps["limits"]["{secondary_limit}"] == {expected_value}, \
            f"Community {secondary_limit} should be {expected_value} (from limits.toml), " \
            f"got {caps['limits'].get('{secondary_limit}')}"
    
    def test_community_restrictions_from_config(self):
        """Verify Community tier has expected feature restrictions."""
        caps = get_tool_capabilities("{tool_name}", "community")
        
        # Verify restricted features (e.g., advanced_feature_enabled=false)
        assert caps["limits"].get("{advanced_feature}_enabled") is False, \
            "Community tier should have {advanced_feature}_enabled=false"


class TestProTierLimits:
    """Verify Pro tier limits from .code-scalpel/limits.toml."""
    
    def test_pro_{primary_limit}_from_config(self):
        """Verify Pro {primary_limit} matches limits.toml (NOT unlimited)."""
        caps = get_tool_capabilities("{tool_name}", "pro")
        
        # Replace with actual limit from limits.toml (NOT None/unlimited)
        assert caps["limits"]["{primary_limit}"] == {expected_value}, \
            f"Pro {primary_limit} should be {expected_value} (from limits.toml), " \
            f"got {caps['limits'].get('{primary_limit}')}"
    
    def test_pro_{secondary_limit}_from_config(self):
        """Verify Pro {secondary_limit} matches limits.toml."""
        caps = get_tool_capabilities("{tool_name}", "pro")
        
        # Replace with actual limit from limits.toml
        assert caps["limits"]["{secondary_limit}"] == {expected_value}, \
            f"Pro {primary_limit} should be {expected_value} (from limits.toml), " \
            f"got {caps['limits'].get('{secondary_limit}')}"
    
    def test_pro_feature_restrictions_from_config(self):
        """Verify Pro tier still has some Enterprise-only restrictions."""
        caps = get_tool_capabilities("{tool_name}", "pro")
        
        # Verify Enterprise-only features still disabled
        assert caps["limits"].get("{enterprise_feature}_enabled") is False, \
            "Pro tier should have {enterprise_feature}_enabled=false (Enterprise-only)"


class TestEnterpriseTierLimits:
    """Verify Enterprise tier limits from .code-scalpel/limits.toml."""
    
    def test_enterprise_unlimited_{primary_limit}_from_config(self):
        """Verify Enterprise {primary_limit} is unlimited."""
        caps = get_tool_capabilities("{tool_name}", "enterprise")
        
        # Enterprise should have unlimited (None or very high value)
        limit_value = caps["limits"].get("{primary_limit}")
        assert limit_value is None or limit_value >= 1000000, \
            f"Enterprise {primary_limit} should be unlimited (None or very high), " \
            f"got {limit_value}"
    
    def test_enterprise_{advanced_feature}_enabled_from_config(self):
        """Verify Enterprise tier has {advanced_feature} enabled."""
        caps = get_tool_capabilities("{tool_name}", "enterprise")
        
        assert caps["limits"].get("{advanced_feature}_enabled") is True, \
            "Enterprise tier should have {advanced_feature}_enabled=true"


class TestConfigurationConsistency:
    """Verify configuration values are consistent across tiers."""
    
    def test_tier_limits_increase_monotonically(self):
        """Verify limits increase from Community → Pro → Enterprise."""
        community_caps = get_tool_capabilities("{tool_name}", "community")
        pro_caps = get_tool_capabilities("{tool_name}", "pro")
        enterprise_caps = get_tool_capabilities("{tool_name}", "enterprise")
        
        community_limit = community_caps["limits"]["{primary_limit}"]
        pro_limit = pro_caps["limits"]["{primary_limit}"]
        enterprise_limit = enterprise_caps["limits"].get("{primary_limit}")
        
        # Community < Pro
        assert community_limit < pro_limit, \
            f"Pro {primary_limit} ({pro_limit}) should be greater than " \
            f"Community ({community_limit})"
        
        # Pro < Enterprise (or Enterprise is None/unlimited)
        if enterprise_limit is not None:
            assert pro_limit < enterprise_limit, \
                f"Enterprise {primary_limit} ({enterprise_limit}) should be greater than " \
                f"Pro ({pro_limit})"
    
    def test_all_tiers_have_required_limits(self):
        """Verify all tiers define required configuration limits."""
        required_limits = ["{primary_limit}", "{secondary_limit}"]
        
        for tier in ["community", "pro", "enterprise"]:
            caps = get_tool_capabilities("{tool_name}", tier)
            
            for limit in required_limits:
                assert limit in caps["limits"], \
                    f"{tier.capitalize()} tier missing required limit: {limit}"
```

## How to Use This Template

### Step 1: Copy Template to Tool Test Directory

```bash
mkdir -p tests/tools/{tool_name}
cp docs/testing/CONFIG_VALIDATION_TEST_TEMPLATE.md tests/tools/{tool_name}/
```

### Step 2: Check limits.toml for Tool Configuration

```bash
# Find your tool's configuration
grep -A 3 "\[community.{tool_name}\]" .code-scalpel/limits.toml
grep -A 3 "\[pro.{tool_name}\]" .code-scalpel/limits.toml
grep -A 3 "\[enterprise.{tool_name}\]" .code-scalpel/limits.toml
```

### Step 3: Replace Template Placeholders

1. **{tool_name}**: Replace with actual tool name (e.g., `code_policy_check`, `analyze_code`)
2. **{primary_limit}**: Replace with main limit key (e.g., `max_files`, `max_depth`)
3. **{secondary_limit}**: Replace with secondary limit key (e.g., `max_rules`, `max_nodes`)
4. **{expected_value}**: Replace with actual value from limits.toml (e.g., `100`, `1000`)
5. **{advanced_feature}**: Replace with feature toggle name (e.g., `compliance`, `custom_rules`)
6. **{enterprise_feature}**: Replace with Enterprise-only feature (e.g., `audit_trail`, `pdf_reports`)

### Step 4: Create __init__.py

```python
"""
Configuration validation tests for {tool_name} MCP tool.

[20251223_TEST] Phase 1 Configuration Validation Tests

This test suite verifies that {tool_name} correctly loads and enforces
tier-based configuration limits from .code-scalpel/limits.toml.
"""
```

### Step 5: Run Tests to Verify Structure

```bash
cd /path/to/code-scalpel
python -m pytest tests/tools/{tool_name}/test_config_validation.py -v
```

## Example: code_policy_check

See `tests/tools/code_policy_check/test_config_validation.py` for a complete working example.

**Key replacements made:**
- `{tool_name}` → `code_policy_check`
- `{primary_limit}` → `max_files`
- `{secondary_limit}` → `max_rules`
- `{expected_value}` for Community → `100` (max_files), `50` (max_rules)
- `{expected_value}` for Pro → `1000` (max_files), `200` (max_rules)
- `{advanced_feature}` → `compliance`, `custom_rules`
- `{enterprise_feature}` → `audit_trail`, `pdf_reports`

## Checklist: Configuration Test Completeness

Before marking configuration validation as complete, verify:

- [ ] `test_config_file_exists` - Verifies .code-scalpel/limits.toml exists
- [ ] `test_loads_limits_from_code_scalpel_dir` - Verifies config loading works
- [ ] Community tier: At least 3 tests (2 limits + 1 restriction)
- [ ] Pro tier: At least 3 tests (2 limits + 1 restriction)
- [ ] Enterprise tier: At least 2 tests (unlimited + advanced feature)
- [ ] Configuration consistency: At least 2 tests (monotonic + required)
- [ ] All tests access nested structure: `caps["limits"]["key"]` NOT `caps["key"]`
- [ ] All expected values match actual limits.toml values (NOT assumed)
- [ ] All tests pass: `pytest tests/tools/{tool_name}/test_config_validation.py`

## Integration with Assessment Checklist

When evaluating MCP tools using `ASSESSMENT_EVALUATION_PROMPT.md`, the **first checklist item** should always be:

```markdown
### Section 1.1: Configuration Validation

| Item | Description | Priority | Status | Evidence |
|------|-------------|----------|--------|----------|
| **Config file validation** | Verify tool loads from .code-scalpel/limits.toml | P0 | ❌ | No config tests |
| **Community limits validation** | Verify Community tier limit values | P0 | ❌ | No config tests |
| **Pro limits validation** | Verify Pro tier limit values (NOT unlimited) | P0 | ❌ | No config tests |
| **Enterprise limits validation** | Verify Enterprise unlimited/advanced features | P0 | ❌ | No config tests |
```

**CRITICAL**: If Section 1.1 is not ✅ (all passing), the tool assessment should be marked as **BLOCK RELEASE** until configuration validation is implemented.

## Common Pitfalls to Avoid

### 1. Accessing caps["key"] Instead of caps["limits"]["key"]

**WRONG:**
```python
assert caps["max_files"] == 100  # KeyError!
```

**CORRECT:**
```python
assert caps["limits"]["max_files"] == 100  # Works!
```

### 2. Assuming Pro Tier is Unlimited

**WRONG:**
```python
# Pro tier should have no max_files limit
assert pro_caps["limits"]["max_files"] is None  # FAILS!
```

**CORRECT:**
```python
# Pro tier has 1000 file limit (from limits.toml)
assert pro_caps["limits"]["max_files"] == 1000  # Works!
```

### 3. Not Checking Actual limits.toml Values

**WRONG:**
```python
# Assuming value without checking config
assert caps["limits"]["max_depth"] == 5  # May be wrong!
```

**CORRECT:**
```python
# First check limits.toml: grep "max_depth" .code-scalpel/limits.toml
# Then use actual value from config
assert caps["limits"]["max_depth"] == 3  # Matches limits.toml
```

### 4. Testing Functional Behavior Before Config Validation

**WRONG ORDER:**
```
1. Create test_functional.py
2. Test rule detection
3. Discover tier limits don't work
4. Add config validation tests (too late!)
```

**CORRECT ORDER:**
```
1. Create test_config_validation.py (THIS TEMPLATE)
2. Verify all config tests pass
3. Create test_tier_enforcement.py (runtime limits)
4. Verify tier enforcement works
5. THEN create test_functional.py (feature tests)
```

## Automated Enforcement

Add this to `.github/copilot-instructions.md` or `CONTRIBUTING.md`:

```markdown
## Rule: Configuration Validation Tests Required

**CRITICAL**: Every new MCP tool MUST have configuration validation tests
before any functional tests are written.

1. Use template: `docs/testing/CONFIG_VALIDATION_TEST_TEMPLATE.md`
2. Create: `tests/tools/{tool_name}/test_config_validation.py`
3. Verify: All 9+ config tests pass
4. ONLY THEN: Write functional tests

**Enforcement**: PR reviews MUST verify config tests exist and pass.
**Rationale**: Prevents assumptions about tier limits, ensures actual configs work.
```

## Pre-Commit Hook (Optional)

```bash
#!/bin/bash
# .git/hooks/pre-commit
# Verify all MCP tools have configuration validation tests

for tool_dir in tests/tools/*/; do
    tool_name=$(basename "$tool_dir")
    
    if [ ! -f "$tool_dir/test_config_validation.py" ]; then
        echo "ERROR: Missing config validation tests for $tool_name"
        echo "Use template: docs/testing/CONFIG_VALIDATION_TEST_TEMPLATE.md"
        exit 1
    fi
done

echo "✓ All tools have configuration validation tests"
```

## References

- Configuration source: `.code-scalpel/limits.toml`
- Config loader: `src/code_scalpel/licensing/config_loader.py`
- Capabilities API: `src/code_scalpel/licensing/features.py::get_tool_capabilities()`
- Example implementation: `tests/tools/code_policy_check/test_config_validation.py`
- Assessment framework: `docs/testing/ASSESSMENT_EVALUATION_PROMPT.md`

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-12-23 | Initial template created from code_policy_check config tests |

---

**REMEMBER**: Configuration validation is P0 (highest priority). All MCP tools MUST validate their configuration before functional testing begins. This prevents assumptions, catches config errors early, and ensures tier limits actually work as documented.
