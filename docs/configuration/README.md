# Configuration Documentation Index

This directory contains documentation for configuring Code Scalpel's various features and behaviors.

## Core Configuration Files

### Tier & Licensing
- **[TIER_CONFIGURATION.md](../TIER_CONFIGURATION.md)** - Complete guide to tier system (Community/Pro/Enterprise)
- **[LIMITS_TOML_BEHAVIOR.md](LIMITS_TOML_BEHAVIOR.md)** - How limits.toml configuration works with tier-based limits
- **[LIMITS_TOML_UNIVERSAL_BEHAVIOR.md](LIMITS_TOML_UNIVERSAL_BEHAVIOR.md)** - Comprehensive analysis proving limits.toml behavior is consistent across all 22 MCP tools

### Runtime Limits
The `limits.toml` file allows you to customize tier-based limits for all MCP tools. See:
- `.code-scalpel/limits.toml` in the project root for the template
- [LIMITS_TOML_BEHAVIOR.md](LIMITS_TOML_BEHAVIOR.md) for detailed behavior documentation
- [LIMITS_TOML_UNIVERSAL_BEHAVIOR.md](LIMITS_TOML_UNIVERSAL_BEHAVIOR.md) for architectural proof of consistency

### Governance
- **[governance_config_schema.md](governance_config_schema.md)** - Schema and configuration for governance policies
- **[TESTING_CONFIGURATIONS.md](TESTING_CONFIGURATIONS.md)** - Test environment configuration

## Key Concepts

### limits.toml Configuration System

The limits.toml file provides a centralized way to configure tool limits for each tier. Key features:

1. **Optional Configuration** - Missing limits.toml falls back to hardcoded defaults in `features.py`
2. **5-Level Priority Chain**:
   - `CODE_SCALPEL_LIMITS_FILE` environment variable
   - Project: `.code-scalpel/limits.toml`
   - User: `~/.code-scalpel/limits.toml`
   - System: `/etc/code-scalpel/limits.toml`
   - Hardcoded defaults in `src/code_scalpel/licensing/features.py`

3. **Enterprise Unlimited Pattern** - Omit numeric limits in enterprise sections to preserve `None` (unlimited) values:
   ```toml
   [enterprise.get_graph_neighborhood]
   # max_k and max_nodes unlimited - omit
   ```

4. **Universal Behavior** - All 22 MCP tools use the same configuration loading mechanism

### Configuration File Locations

Default search paths (in priority order):
1. Environment variable override: `$CODE_SCALPEL_LIMITS_FILE`
2. Project config: `.code-scalpel/limits.toml`
3. User config: `~/.code-scalpel/limits.toml`
4. System config: `/etc/code-scalpel/limits.toml`
5. Bundled defaults: Python package defaults

### Testing Configuration

See [../testing/tier/](../testing/tier/) for tier limit validation tests:
- `test_comprehensive_tier_limits.py` - Validates tier configuration across all scenarios
- `test_mcp_tool_tiers.py` - End-to-end MCP tool testing with tier enforcement
- `FINAL_VALIDATION_REPORT.py` - Summary report generator

## Related Documentation

- [../TIER_CONFIGURATION.md](../TIER_CONFIGURATION.md) - Main tier configuration guide
- [../tools/](../tools/) - Tool-specific documentation
- [../testing/tier/](../testing/tier/) - Tier testing documentation
- [../LICENSE](../../LICENSE) - MIT license for the codebase

## Quick Links

- [Project Root Configuration Template](../../.code-scalpel/limits.toml)
- [Features Matrix](../../src/code_scalpel/licensing/features.py)
- [Configuration Loader](../../src/code_scalpel/licensing/config_loader.py)
