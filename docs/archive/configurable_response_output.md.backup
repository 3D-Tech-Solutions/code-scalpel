# Configurable Response Output

**[20251226_FEATURE] v1.0.0 - Token-Efficient Responses**

## Overview

Code Scalpel's MCP server supports fully configurable response output via `.code-scalpel/response_config.json`. This allows teams to customize exactly which fields are returned, optimizing for token efficiency while maintaining the data needed for their specific use case.

## Configuration File

Location: `.code-scalpel/response_config.json`

The server searches for configuration in:
1. `{project_root}/.code-scalpel/response_config.json`
2. `~/.config/code-scalpel/response_config.json`
3. Falls back to built-in defaults

## Profiles

### Minimal (Default)
Maximum token efficiency - only essential data.
- **Envelope fields**: None (just `data`)
- **Excludes**: `success`, `server_version`, `function_count`, `class_count`, `error` (when null)
- **Use case**: Production AI agents with tight token budgets

### Standard
Balanced output with essential metadata.
- **Envelope fields**: `error`, `upgrade_hints`
- **Excludes**: `server_version`, `function_count`, `class_count`
- **Use case**: Most production environments

### Debug
Full output including all metadata.
- **Envelope fields**: All fields
- **Excludes**: Nothing
- **Use case**: Development, troubleshooting

## Configuration Structure

```json
{
  "version": "3.3.0",
  "global": {
    "profile": "minimal",
    "exclude_empty_arrays": true,
    "exclude_empty_objects": true,
    "exclude_null_values": true,
    "exclude_default_values": true
  },
  "profiles": {
    "minimal": { ... },
    "standard": { ... },
    "debug": { ... }
  },
  "tool_overrides": {
    "analyze_code": {
      "profile": "minimal",
      "include_only": [
        "functions",
        "classes",
        "imports",
        "complexity",
        "lines_of_code",
        "function_details",
        "class_details"
      ],
      "exclude_when_tier": {
        "community": [
          "cognitive_complexity",
          "code_smells",
          "halstead_metrics",
          "duplicate_code_blocks",
          "dependency_graph",
          "naming_issues",
          "compliance_issues",
          "custom_rule_violations",
          "organization_patterns"
        ]
      }
    }
  }
}
```

## Per-Tool Configuration

Each tool can have its own configuration:

```json
{
  "tool_overrides": {
    "extract_code": {
      "profile": "minimal",
      "include_only": ["code", "dependencies"]
    },
    "security_scan": {
      "profile": "standard",
      "include_only": ["vulnerabilities", "risk_level", "vulnerability_count"]
    }
  }
}
```

## Tier-Specific Filtering

Automatically exclude tier-inappropriate fields:

```json
{
  "tool_overrides": {
    "analyze_code": {
      "exclude_when_tier": {
        "community": [
          "cognitive_complexity",
          "halstead_metrics"
        ],
        "pro": [
          "compliance_issues"
        ]
      }
    }
  }
}
```

## Debug Mode Override

Set `SCALPEL_MCP_OUTPUT=DEBUG` to force debug profile:
```bash
export SCALPEL_MCP_OUTPUT=DEBUG
# All metadata will be included regardless of configuration
```

## Example Responses

### Minimal Profile (Default)
```json
{
  "data": {
    "functions": ["test", "helper"],
    "classes": ["Calculator"],
    "imports": ["math"],
    "complexity": 2,
    "lines_of_code": 15,
    "function_details": [...],
    "class_details": [...]
  }
}
```

### Standard Profile
```json
{
  "error": null,
  "data": {
    "functions": ["test", "helper"],
    "classes": ["Calculator"],
    "imports": ["math"],
    "complexity": 2,
    "lines_of_code": 15
  }
}
```

### Debug Profile
```json
{
  "tier": "community",
  "tool_version": "3.3.0",
  "tool_id": "analyze_code",
  "request_id": "abc123",
  "capabilities": ["envelope-v1"],
  "duration_ms": 7,
  "error": null,
  "upgrade_hints": [],
  "data": {
    "success": true,
    "server_version": "3.3.0",
    "functions": ["test", "helper"],
    ...
  }
}
```

## Token Savings

- **Minimal vs Debug**: ~150-200 tokens per response
- **1000 tool calls**: 150,000-200,000 tokens saved
- **Preserves context**: Equivalent to 50-70 pages of documentation

## Best Practices

1. **Start Minimal**: Use minimal profile, add fields only if needed
2. **Per-Tool Tuning**: Configure each tool based on actual usage patterns
3. **Tier Awareness**: Exclude tier-inappropriate fields automatically
4. **Debug When Needed**: Use `SCALPEL_MCP_OUTPUT=DEBUG` for troubleshooting
5. **Version Control**: Commit `.code-scalpel/response_config.json` to share team settings

## Schema Validation

The configuration file includes JSON Schema for IDE autocomplete and validation:
```json
{
  "$schema": "./response_config.schema.json",
  ...
}
```

VSCode, IntelliJ, and other IDEs will provide autocomplete and validation automatically.
