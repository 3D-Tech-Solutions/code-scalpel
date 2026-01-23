# Configuration Guide

<!-- Code Scalpel v3.0.0 - Complete Configuration Reference -->

## Overview

This guide provides comprehensive configuration options for Code Scalpel, including environment variables, governance controls, MCP response formatting, and setup procedures.

## Table of Contents

- [Environment Variables](#environment-variables)
- [Governance Configuration](#governance-configuration)
- [MCP Response Configuration](#mcp-response-configuration)
- [Configuration Files](#configuration-files)
- [Setup and Initialization](#setup-and-initialization)
- [Tier-Specific Configuration](#tier-specific-configuration)
- [Docker Configuration](#docker-configuration)
- [Troubleshooting](#troubleshooting)

## Environment Variables

### Licensing

| Variable | Purpose | Default | Applies To |
|----------|---------|---------|------------|
| `CODE_SCALPEL_LICENSE_PATH` | Path to license file | Auto-discovered | Pro, Enterprise |
| `CODE_SCALPEL_LICENSE_VERIFIER_URL` | Remote verification endpoint | Not set | Pro, Enterprise |
| `CODE_SCALPEL_LICENSE_VERIFY_TIMEOUT_SECONDS` | Timeout for remote verification | `2.0` | Pro, Enterprise |
| `CODE_SCALPEL_LICENSE_VERIFY_RETRIES` | Number of retries for remote verification | `2` | Pro, Enterprise |
| `CODE_SCALPEL_DISABLE_LICENSE_REVALIDATION` | Disable periodic license revalidation | `0` (enabled) | All tiers |

### MCP Server Configuration

| Variable | Purpose | Default | Applies To |
|----------|---------|---------|------------|
| `SCALPEL_MCP_OUTPUT` | Log verbosity level | `WARNING` | All tiers |
| `SCALPEL_PROJECT_ROOT` | Override workspace root | Current directory | All tiers |

### Auto-Initialization

| Variable | Purpose | Default | Applies To |
|----------|---------|---------|------------|
| `SCALPEL_AUTO_INIT` | Enable automatic .code-scalpel/ creation | Disabled | All tiers |
| `SCALPEL_AUTO_INIT_MODE` | Mode for auto-initialization | `full` | All tiers |
| `SCALPEL_AUTO_INIT_TARGET` | Where to create .code-scalpel/ | `project` | All tiers |
| `SCALPEL_HOME` | User-level home directory | `~/.config/code-scalpel` | All tiers |

### Caching

| Variable | Purpose | Default | Applies To |
|----------|---------|---------|------------|
| `CODE_SCALPEL_CACHE_ENABLED` | Enable/disable analysis caching | `1` (enabled) | All tiers |
| `CODE_SCALPEL_CACHE_PERSIST` | Persist license cache to disk | `false` | Pro, Enterprise |
| `CODE_SCALPEL_CACHE_KEY` | Encryption key for persistent cache | Not set | Enterprise |
| `CODE_SCALPEL_CACHE_DISTRIBUTED` | Enable distributed caching (Redis) | `false` | Enterprise |
| `CODE_SCALPEL_REDIS_URL` | Redis URL for distributed caching | `redis://localhost:6379` | Enterprise |

### Governance & Policy

| Variable | Purpose | Default | Applies To |
|----------|---------|---------|------------|
| `SCALPEL_GOVERNANCE_ENFORCEMENT` | Governance enforcement mode | `advisory` | Pro, Enterprise |
| `SCALPEL_GOVERNANCE_MODE` | Legacy alias for enforcement | Not set | Deprecated |
| `SCALPEL_GOVERNANCE_FEATURES` | Comma-separated enabled features | All features | Pro, Enterprise |
| `SCALPEL_GOVERNANCE_REQUIRED` | Require governance configuration | `false` | Enterprise |
| `SCALPEL_CONFIG_PROFILE` | Configuration profile to load | Not set | Pro, Enterprise |
| `SCALPEL_CONFIG` | Path to governance configuration | Auto-discovered | Pro, Enterprise |
| `SCALPEL_CHANGE_BUDGET_MAX_LINES` | Maximum lines per change | Not set | Pro, Enterprise |
| `SCALPEL_CHANGE_BUDGET_MAX_FILES` | Maximum files per change | Not set | Pro, Enterprise |
| `SCALPEL_CHANGE_BUDGET_MAX_COMPLEXITY` | Maximum complexity change | Not set | Pro, Enterprise |
| `SCALPEL_CRITICAL_PATHS` | Comma-separated critical paths | Not set | Pro, Enterprise |
| `SCALPEL_CRITICAL_PATH_MAX_LINES` | Max lines for critical paths | Not set | Pro, Enterprise |
| `SCALPEL_MAX_CALL_GRAPH_DEPTH` | Max call graph analysis depth | Not set | Pro, Enterprise |
| `SCALPEL_MAX_AUTONOMOUS_ITERATIONS` | Max autonomous iterations | Not set | Pro, Enterprise |
| `SCALPEL_AUDIT_RETENTION_DAYS` | Audit log retention | Not set | Pro, Enterprise |

### Security & Integrity

| Variable | Purpose | Default | Applies To |
|----------|---------|---------|------------|
| `SCALPEL_MANIFEST_SECRET` | Secret for policy manifest signing | Not set | Pro, Enterprise |
| `SCALPEL_POLICY_MANIFEST_SOURCE` | Source for policy manifest | `file` | Enterprise |
| `SCALPEL_POLICY_DIR` | Directory containing policy files | `.code-scalpel` | Pro, Enterprise |
| `SCALPEL_POLICY_MANIFEST` | Inline policy manifest JSON | Not set | Enterprise |
| `SCALPEL_CONFIG_HASH` | Expected SHA-256 hash of config | Not set | Enterprise |
| `SCALPEL_CONFIG_SECRET` | Secret for config signature verification | Not set | Enterprise |
| `SCALPEL_CONFIG_SIGNATURE` | Expected config file signature | Not set | Enterprise |
| `SCALPEL_TOTP_SECRET` | TOTP secret for tamper resistance | `default-totp-secret` | Enterprise |
| `SCALPEL_AUDIT_SECRET` | Secret for audit log signing | `default-secret` | Enterprise |

### Path Resolution

| Variable | Purpose | Default | Applies To |
|----------|---------|---------|------------|
| `WORKSPACE_ROOT` | Override workspace root | Current directory | All tiers |
| `PROJECT_ROOT` | Override project root | Current directory | All tiers |
| `SCALPEL_ROOT` / `CODE_SCALPEL_ROOT` | Root directories for file access | Not set | All tiers |
| `WINDOWS_DRIVE_MAP` | Windows drive letter mapping | Not set | Windows |

### Testing & Development

| Variable | Purpose | Default | Applies To |
|----------|---------|---------|------------|
| `CODE_SCALPEL_TEST_FORCE_TIER` | Force tier override for testing | `0` | Testing |
| `CODE_SCALPEL_RUN_MCP_CONTRACT` | Enable MCP contract tests | `0` | Testing |
| `MCP_CONTRACT_TRANSPORT` | Transport for contract tests | `stdio` | Testing |
| `MCP_CONTRACT_ARTIFACT_DIR` | Directory for contract test artifacts | Temp directory | Testing |
| `RUN_DOCKER_TESTS` | Enable Docker integration tests | `0` | Testing |
| `CODE_SCALPEL_DOCKER_IMAGE` | Docker image for tests | Auto-built | Testing |
| `REBUILD_DOCKER_IMAGE` | Force rebuild Docker image | `0` | Testing |
| `RUN_NINJA_WARRIOR` | Enable Ninja Warrior tests | `0` | Testing |
| `RUN_NINJA_WARRIOR_HEAVY` | Enable heavy Ninja Warrior tests | `0` | Testing |
| `NINJA_WARRIOR_ROOT` | Root directory for tests | Not set | Testing |
| `NINJA_WARRIOR_EVIDENCE_DIR` | Evidence directory for tests | Not set | Testing |

### System Environment Variables

These are standard system environment variables used by Code Scalpel:

| Variable | Purpose |
|----------|---------|
| `XDG_CONFIG_HOME` | XDG config directory (Linux/macOS) |
| `USER` / `USERNAME` | Current user name for audit logs |
| `HOSTNAME` / `COMPUTERNAME` | Machine hostname for audit logs |
| `LOCALAPPDATA` | Windows local app data directory |
| `XDG_CACHE_HOME` | XDG cache directory |
| `FLASK_ENV` | Flask environment (for REST API server) |
| `CI` | Indicates CI environment |
| `GITHUB_ACTIONS` | Indicates GitHub Actions environment |

## Governance Configuration

### Overview

Governance controls include Change Budgeting and Blast Radius limits. These settings can be configured in `.vscode/mcp.json` (workspace-specific) or environment variables (system-wide), with cryptographic integrity protection.

### Configuration Locations

#### 1. VS Code MCP Configuration (Workspace-Specific)

**File:** `.vscode/mcp.json`

```json
{
  "servers": {
    "code-scalpel": {
      "type": "stdio",
      "command": "/path/to/code-scalpel",
      "args": ["mcp", "--root", "${workspaceFolder}"],
       "env": {
         "SCALPEL_CONFIG": "${workspaceFolder}/.code-scalpel/governance.yaml",
         "SCALPEL_CONFIG_HASH": "sha256:abc123..."
       }
    }
  }
}
```

#### 2. Scalpel Governance Configuration File (Immutable)

**File:** `.code-scalpel/governance.yaml` (JSON format also supported: `governance.json`)

```yaml
version: "3.0.0"
autonomy:
  governance:
    change_budgeting:
      enabled: true
      max_lines_per_change: 500
      max_files_per_change: 10
      max_complexity_delta: 50
      require_justification: true
      budget_refresh_interval_hours: 24
    blast_radius:
      enabled: true
      max_affected_functions: 20
      max_affected_classes: 5
      max_call_graph_depth: 3
      warn_on_public_api_changes: true
      block_on_critical_paths: true
      critical_paths:
        - "src/core/"
        - "src/security/"
        - "src/symbolic_execution_tools/"
        - "src/mcp/server.py"
      critical_path_max_lines: 50
      critical_path_max_complexity_delta: 10
    autonomy_constraints:
      max_autonomous_iterations: 10
      require_approval_for_breaking_changes: true
      require_approval_for_security_changes: true
      sandbox_execution_required: true
    audit:
      log_all_changes: true
      log_rejected_changes: true
      retention_days: 90
```

#### 3. Environment Variables (System-Wide Override)

Override individual settings via environment variables with `SCALPEL_` prefix:

```bash
# Change Budgeting
export SCALPEL_CHANGE_BUDGET_MAX_LINES=500
export SCALPEL_CHANGE_BUDGET_MAX_FILES=10
export SCALPEL_CHANGE_BUDGET_MAX_COMPLEXITY_DELTA=50

# Blast Radius
export SCALPEL_BLAST_RADIUS_MAX_FUNCTIONS=20
export SCALPEL_BLAST_RADIUS_MAX_CLASSES=5
export SCALPEL_BLAST_RADIUS_MAX_DEPTH=3

# Critical Paths (comma-separated)
export SCALPEL_CRITICAL_PATHS="src/core/,src/security/,src/mcp/server.py"
export SCALPEL_CRITICAL_PATH_MAX_LINES=50
export SCALPEL_CRITICAL_PATH_MAX_COMPLEXITY_DELTA=10

# Autonomy
export SCALPEL_MAX_AUTONOMOUS_ITERATIONS=10
export SCALPEL_REQUIRE_APPROVAL_BREAKING=true
export SCALPEL_REQUIRE_APPROVAL_SECURITY=true
```

### Critical Paths

Critical paths allow designating specific directories or files requiring stricter change controls. This is essential for security-critical, core infrastructure, data processing, and public API code.

### Configuration Schema Reference

#### Change Budgeting Settings

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `enabled` | boolean | `true` | Enable change budgeting |
| `max_lines_per_change` | integer | `500` | Maximum lines modified per change |
| `max_files_per_change` | integer | `10` | Maximum files modified per change |
| `max_complexity_delta` | integer | `50` | Maximum cyclomatic complexity increase |
| `require_justification` | boolean | `true` | Require reason for large changes |
| `budget_refresh_interval_hours` | integer | `24` | Budget reset interval |

#### Blast Radius Settings

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `enabled` | boolean | `true` | Enable blast radius control |
| `max_affected_functions` | integer | `20` | Max functions impacted by change |
| `max_affected_classes` | integer | `5` | Max classes impacted by change |
| `max_call_graph_depth` | integer | `3` | Max depth for impact analysis |
| `warn_on_public_api_changes` | boolean | `true` | Warn when public API modified |
| `block_on_critical_paths` | boolean | `true` | Block changes to critical code paths |
| `critical_paths` | array[string] | `[]` | Directories/files requiring scrutiny |
| `critical_path_max_lines` | integer | `50` | Max lines changed in critical paths |
| `critical_path_max_complexity_delta` | integer | `10` | Max complexity increase in critical paths |

#### Autonomy Constraints

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `max_autonomous_iterations` | integer | `10` | Max autonomous fix attempts |
| `require_approval_for_breaking_changes` | boolean | `true` | Human approval for breaking changes |
| `require_approval_for_security_changes` | boolean | `true` | Human approval for security changes |
| `sandbox_execution_required` | boolean | `true` | Require sandboxed testing before apply |

#### Audit Settings

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `log_all_changes` | boolean | `true` | Log all code modifications |
| `log_rejected_changes` | boolean | `true` | Log rejected changes |
| `retention_days` | integer | `90` | Log retention period |

### Usage Examples

#### Example 1: Restrictive Configuration (Security-Critical Projects)

```json
{
  "version": "3.0.0",
  "autonomy": {
    "governance": {
      "change_budgeting": {
        "enabled": true,
        "max_lines_per_change": 100,
        "max_files_per_change": 3,
        "max_complexity_delta": 10,
        "require_justification": true
      },
      "blast_radius": {
        "enabled": true,
        "max_affected_functions": 5,
        "max_affected_classes": 2,
        "max_call_graph_depth": 2,
        "block_on_critical_paths": true,
        "critical_paths": [
          "src/core/",
          "src/security/",
          "src/symbolic_execution_tools/security_analyzer.py"
        ],
        "critical_path_max_lines": 25,
        "critical_path_max_complexity_delta": 5
      },
      "autonomy_constraints": {
        "max_autonomous_iterations": 3,
        "require_approval_for_breaking_changes": true,
        "require_approval_for_security_changes": true,
        "sandbox_execution_required": true
      }
    }
  }
}
```

#### Example 2: Permissive Configuration (Experimental Projects)

```json
{
  "version": "3.0.0",
  "autonomy": {
    "governance": {
      "change_budgeting": {
        "enabled": true,
        "max_lines_per_change": 2000,
        "max_files_per_change": 50,
        "max_complexity_delta": 200,
        "require_justification": false
      },
      "blast_radius": {
        "enabled": true,
        "max_affected_functions": 100,
        "max_affected_classes": 20,
        "max_call_graph_depth": 5,
        "warn_on_public_api_changes": false,
        "block_on_critical_paths": false,
        "critical_paths": [],
        "critical_path_max_lines": 200,
        "critical_path_max_complexity_delta": 50
      },
      "autonomy_constraints": {
        "max_autonomous_iterations": 50,
        "require_approval_for_breaking_changes": false,
        "require_approval_for_security_changes": true,
        "sandbox_execution_required": true
      }
    }
  }
}
```

## MCP Response Configuration

### Overview

Code Scalpel supports configurable MCP response output for token efficiency. Responses can be customized per tool and profile.

### Configuration File

Location: `.code-scalpel/response_config.json`

### Profiles

#### Minimal (Default)
Maximum token efficiency - only essential data.

#### Standard
Balanced output with essential metadata.

#### Debug
Full output including all metadata.

### Configuration Structure

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

### Per-Tool Configuration

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

### Tier-Specific Filtering

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

### Debug Mode Override

Set `SCALPEL_MCP_OUTPUT=DEBUG` to force debug profile.

### Example Responses

#### Minimal Profile (Default)
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

#### Standard Profile
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

#### Debug Profile
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

### Token Savings

- **Minimal vs Debug**: ~150-200 tokens per response
- **1000 tool calls**: 150,000-200,000 tokens saved

## Configuration Files

### .env File

Create a `.env` file in your project root:

```bash
# ========================================================================
# PROJECT CONFIGURATION
# ========================================================================
SCALPEL_PROJECT_ROOT=/path/to/project
SCALPEL_TIER=community

# ========================================================================
# POLICY INTEGRITY VERIFICATION
# ========================================================================
SCALPEL_MANIFEST_SECRET=your-secret-here

# ========================================================================
# PERFORMANCE
# ========================================================================
SCALPEL_MAX_FILE_SIZE=10485760
CODE_SCALPEL_CACHE_ENABLED=true
SCALPEL_CACHE_DIR=./.code_scalpel_cache

# ========================================================================
# LOGGING
# ========================================================================
SCALPEL_LOG_LEVEL=INFO
SCALPEL_ENABLE_TRACING=false

# ========================================================================
# MCP TRANSPORT
# ========================================================================
SCALPEL_TRANSPORT=stdio
```

### Initialize Configuration

```bash
# Create .env with secure defaults
python -m code_scalpel init
```

## Setup and Initialization

### CLI Initialization

```bash
code-scalpel init
```

This creates:
- `.code-scalpel` directory with configuration files
- `config.json` with governance settings
- `agent_limits.yaml` with operation limits
- `governance.yaml` with autonomy policies
- `policy.yaml` with security policies
- `project-structure.yaml` with project organization rules
- `policies/` directory with policy templates
- `license/` directory for license files
- `.env` with generated secrets (full mode)
- `.env.example` with documentation

### MCP Server Boot Process

1. Load configuration from `.code-scalpel/config.json`
2. Validate license if Pro/Enterprise
3. Initialize governance controls
4. Start MCP server on configured transport (stdio/http)
5. Register available tools based on tier

### Environment Setup

For proper operation, ensure:
- Python 3.8+ installed
- Required dependencies installed
- License file present (Pro/Enterprise)
- Project root correctly configured

## Tier-Specific Configuration

### Community Tier (Default)

Free and open-source (MIT License):

```bash
SCALPEL_TIER=community
```

**Limits:**
- Security findings: 50 per scan
- Symbol references: 100 per query
- Call graph nodes: 500 per analysis
- Project files: 1,000 files
- Test generation: 10 paths

### Pro Tier

Commercial license required:

```bash
SCALPEL_TIER=pro
SCALPEL_LICENSE_PATH=/secure/pro-license.jwt
```

**Limits:**
- Security findings: Unlimited
- Symbol references: Unlimited
- Call graph nodes: 10,000 per analysis
- Project files: 10,000 files
- Test generation: 50 paths

### Enterprise Tier

Enterprise license required:

```bash
SCALPEL_TIER=enterprise
SCALPEL_LICENSE_PATH=/secure/enterprise-license.jwt
```

**Limits:**
- All unlimited

## Docker Configuration

### Environment Variables in Docker

```bash
docker run -i \
  -e SCALPEL_PROJECT_ROOT=/workspace \
  -e SCALPEL_TIER=community \
  -e SCALPEL_LOG_LEVEL=DEBUG \
  -v $(pwd):/workspace \
  3dtechsolutions/code-scalpel:latest
```

### Docker Compose

```yaml
version: '3.8'

services:
  code-scalpel:
    image: 3dtechsolutions/code-scalpel:latest
    environment:
      - SCALPEL_PROJECT_ROOT=/workspace
      - SCALPEL_TIER=community
      - SCALPEL_LOG_LEVEL=INFO
      - CODE_SCALPEL_CACHE_ENABLED=true
      - SCALPEL_MANIFEST_SECRET=${SCALPEL_SECRET}
    volumes:
      - ./:/workspace
      - cache:/cache

volumes:
  cache:
```

## Troubleshooting

### Configuration Not Loading

**Check active configuration:**
```bash
python -m code_scalpel config show
```

### Validate Configuration
```bash
python -m code_scalpel config validate
```

### Reset to Defaults
```bash
python -m code_scalpel config reset
```

### Common Issues

1. **Invalid JSON**: Use `python -c "import json; json.load(open('config.json'))"` to validate
2. **Permission denied**: Ensure write access to `.code-scalpel/` directory
3. **License not found**: Verify `CODE_SCALPEL_LICENSE_PATH` points to valid JWT
4. **Environment variables not working**: Check for typos in variable names

## See Also

- [Governance Configuration Schema](governance_config_schema.md)
- [Limits TOML Behavior](LIMITS_TOML_BEHAVIOR.md)
- [Testing Configurations](TESTING_CONFIGURATIONS.md)
- [Security Documentation](../security/)