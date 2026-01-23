# Tier Testing Documentation

This directory contains documentation and test scripts for validating Code Scalpel's tier-based licensing and limits system.

## Test Scripts

### Comprehensive Tier Validation
- **[test_comprehensive_tier_limits.py](test_comprehensive_tier_limits.py)** - Validates tier configuration across all scenarios
  - Tests Community, Pro, and Enterprise tiers
  - Tests with and without limits.toml present
  - Validates correct fallback to hardcoded defaults
  - Uses actual JWT license files from `tests/licenses/`

### MCP Tool End-to-End Testing
- **[test_mcp_tool_tiers.py](test_mcp_tool_tiers.py)** - End-to-end MCP tool testing with tier enforcement
  - Tests actual MCP tool invocation
  - Validates tier limit enforcement at runtime
  - Tests with different license configurations

### Validation Report
- **[FINAL_VALIDATION_REPORT.py](FINAL_VALIDATION_REPORT.py)** - Summary report generator
  - Displays comprehensive validation results
  - Documents all tier configurations tested
  - Provides final validation summary

## Test Results

### Configuration Tests (6/6 passed)
All tier limits validated correctly across all scenarios:
- ✅ **Community tier**: max_k=1, max_nodes=20 (with & without limits.toml)
- ✅ **Pro tier**: max_k=5, max_nodes=100 (with & without limits.toml)
- ✅ **Enterprise tier**: max_k=None, max_nodes=None (unlimited, with & without limits.toml)

### Key Findings
1. **limits.toml is optional** - missing config falls back to hardcoded defaults
2. **Enterprise is always unlimited** - `None` values preserved in both scenarios
3. **Configuration fallback chain works correctly** - 5-level priority system validated
4. **Merge logic preserves None** - empty TOML sections maintain unlimited status

## Running Tests

### Prerequisites
```bash
# Ensure you're in the code-scalpel root directory
cd /path/to/code-scalpel

# Activate the virtual environment (if using one)
source venv/bin/activate  # or conda activate code-scalpel
```

### Run Comprehensive Tier Limits Test
```bash
python docs/testing/tier/test_comprehensive_tier_limits.py
```

This test validates:
- Community tier configuration (with/without limits.toml)
- Pro tier configuration (with/without limits.toml)
- Enterprise tier configuration (with/without limits.toml)
- Correct use of test JWT licenses from `tests/licenses/`

### Run MCP Tool Test
```bash
python docs/testing/tier/test_mcp_tool_tiers.py
```

This test validates:
- MCP tool invocation with different tiers
- Runtime tier limit enforcement
- License-based tier detection

### Generate Validation Report
```bash
python docs/testing/tier/FINAL_VALIDATION_REPORT.py
```

Displays a comprehensive summary of all tier testing performed.

## Test Licenses

Test JWT licenses are located in `tests/licenses/`:
- `code_scalpel_license_pro_20260101_190345.jwt` - Pro tier test license
- `code_scalpel_license_enterprise_20260101_190754.jwt` - Enterprise tier test license

**Note**: These test licenses have invalid signatures (signed with a different key than production). They are used only for testing the configuration system behavior.

## Related Documentation

### Configuration
- [../../configuration/LIMITS_TOML_BEHAVIOR.md](../../configuration/LIMITS_TOML_BEHAVIOR.md) - Detailed limits.toml behavior
- [../../configuration/LIMITS_TOML_UNIVERSAL_BEHAVIOR.md](../../configuration/LIMITS_TOML_UNIVERSAL_BEHAVIOR.md) - Universal behavior across all tools
- [../../configuration/README.md](../../configuration/README.md) - Configuration documentation index
- [../../TIER_CONFIGURATION.md](../../TIER_CONFIGURATION.md) - Main tier configuration guide

### Source Code
- `src/code_scalpel/licensing/features.py` - Hardcoded tier capabilities and limits
- `src/code_scalpel/licensing/config_loader.py` - Configuration loading and merging logic
- `src/code_scalpel/licensing/tier_detector.py` - Runtime tier detection
- `.code-scalpel/limits.toml` - Project-level limits configuration template

### Test Infrastructure
- `tests/tools/get_graph_neighborhood/test_tier_enforcement.py` - Unit tests for tier enforcement
- `tests/licenses/README.md` - Test license documentation

## Architecture

### Configuration Priority Chain
```
1. CODE_SCALPEL_LIMITS_FILE env var → /custom/path/limits.toml
2. Project config                   → .code-scalpel/limits.toml
3. User config                      → ~/.code-scalpel/limits.toml
4. System config                    → /etc/code-scalpel/limits.toml
5. Hardcoded defaults               → src/code_scalpel/licensing/features.py
```

### Merge Logic
```python
def merge_limits(defaults: dict, overrides: dict) -> dict:
    """Merge TOML overrides into hardcoded defaults.
    
    CRITICAL: Empty overrides dict preserves None values in defaults.
    """
    if not overrides:
        return defaults  # ← Preserves None values
    
    merged = dict(defaults)
    for key, value in overrides.items():
        if value is not None:
            merged[key] = value
    return merged
```

### Universal Behavior
All 22 MCP tools use the same configuration system:
- Single `get_tool_capabilities(tool_id, tier)` function
- Single `merge_limits(defaults, overrides)` logic
- Consistent fallback to hardcoded defaults
- Uniform handling of missing/empty configuration

## Validation Checklist

When adding new tier-based features, verify:

- [ ] Hardcoded defaults defined in `features.py` for all tiers
- [ ] Corresponding sections added to `.code-scalpel/limits.toml`
- [ ] Enterprise section uses "# unlimited - omit" pattern for None values
- [ ] Unit tests added to `tests/tools/<tool_name>/test_tier_enforcement.py`
- [ ] Integration test added covering all tier configurations
- [ ] Documentation updated in `docs/tools/<tool_name>.md`

## Known Issues

None currently. All tier configurations validated successfully.

## Contact

For questions or issues with tier testing:
- See [../../CONTRIBUTING.md](../../CONTRIBUTING.md) for contribution guidelines
- Check [../../issues/](../../issues/) for known issues
- Review [../../DEVELOPMENT_ROADMAP.md](../../DEVELOPMENT_ROADMAP.md) for planned features
