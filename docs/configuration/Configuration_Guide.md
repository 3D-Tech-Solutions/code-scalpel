# Code Scalpel Configuration Guide

This comprehensive guide covers all aspects of configuring Code Scalpel, including MCP server settings, the `.code-scalpel` directory, CLI initialization, and environment variables. Use this guide to set up and customize Code Scalpel for your development workflow.

## Quick Start

### Basic Setup
1. Initialize configuration:
   ```bash
   code-scalpel init
   ```

2. Set your license (for Pro/Enterprise features):
   ```bash
   # Place license.jwt in .code-scalpel/license/
   cp /path/to/your/license.jwt .code-scalpel/license/
   ```

3. Start MCP server:
   ```bash
   python -m code_scalpel.mcp.server
   ```

### MCP Client Configuration
Create `mcp.json` for your MCP client:
```json
{
  "mcpServers": {
    "code-scalpel": {
      "command": "python",
      "args": ["-m", "code_scalpel.mcp.server"],
      "env": {
        "CODE_SCALPEL_CONFIG_DIR": "/path/to/.code-scalpel",
        "CODE_SCALPEL_LICENSE_PATH": ".code-scalpel/license/license.jwt"
      }
    }
  }
}
```

The `CODE_SCALPEL_CONFIG_DIR` environment variable allows you to specify a custom location for the `.code-scalpel` configuration directory. If not set, Code Scalpel will automatically search for the configuration in standard locations.

## Configuration Areas

### 1. MCP Server Configuration
Configure MCP server behavior through environment variables. See [MCP_Configuration.md](MCP_Configuration.md) for complete details.

#### Essential Variables
```bash
# Enable debug logging
export SCALPEL_MCP_OUTPUT=DEBUG

# Set license path
export CODE_SCALPEL_LICENSE_PATH=.code-scalpel/license/license.jwt

# Control caching
export SCALPEL_CACHE_ENABLED=1
```

#### Advanced MCP Settings
```bash
# Use HTTP transport for MCP
export MCP_CONTRACT_TRANSPORT=http
export SCALPEL_MCP_BASE=http://127.0.0.1:18080

# Enable contract testing
export CODE_SCALPEL_RUN_MCP_CONTRACT=1
```

### 2. .code-scalpel Directory
The `.code-scalpel` directory contains all configuration files. See [Code_Scalpel_Directory_Configuration.md](Code_Scalpel_Directory_Configuration.md) for detailed file descriptions.

#### Key Files to Customize

**config.json** - Governance settings:
```json
{
  "version": "1.0",
  "governance": {
    "change_budgeting": {
      "max_lines_per_change": 500,
      "max_files_per_change": 10
    },
    "blast_radius": {
      "max_complexity_delta": 50
    },
    "audit": {
      "retention_days": 90
    }
  }
}
```

**response_config.json** - MCP response optimization:
```json
{
  "global_profile": "debug",
  "profiles": {
    "minimal": {
      "exclude_empty": true,
      "exclude_null": true
    }
  },
  "tool_overrides": {
    "analyze_code": {
      "exclude": ["raw_ast"]
    }
  }
}
```

**policy.yaml** - Security policies:
```yaml
version: "1.0"
enforcement: "warn"
security_rules:
  sql_injection_protection: true
  command_injection_protection: true
budgeting:
  enabled: false
```

### 3. CLI Init and MCP Boot
See [CLI_Init_and_MCP_Boot.md](CLI_Init_and_MCP_Boot.md) for initialization details.

#### Manual Initialization
```bash
# Full initialization
code-scalpel init

# Initialize in specific directory
code-scalpel init --dir /path/to/project

# Force re-init
code-scalpel init --force
```

#### Automatic MCP Boot Init
```bash
# Enable safe auto-init
export CODE_SCALPEL_CONFIG_AUTO_INIT=1
export CODE_SCALPEL_CONFIG_AUTO_INIT_MODE=safe

# Run MCP server (will auto-create config if needed)
python -m code_scalpel.mcp.server
```

## Environment Variable Reference

### Core Configuration
| Variable | Purpose | Default | Example |
|----------|---------|---------|---------|
| `CODE_SCALPEL_CONFIG_DIR` | Configuration directory location | Auto-discovered | `/path/to/.code-scalpel` |
| `CODE_SCALPEL_LICENSE_PATH` | License file location | Auto-discovered | `.code-scalpel/license/license.jwt` |
| `CODE_SCALPEL_TIER` | Requested tier | Licensed tier | `enterprise` |
| `CODE_SCALPEL_PROJECT_ROOT` | Project root | Current directory | `/path/to/project` |

### MCP Server
| Variable | Purpose | Default | Example |
|----------|---------|---------|---------|
| `SCALPEL_MCP_OUTPUT` | Log level | `WARNING` | `DEBUG` |
| `SCALPEL_MCP_DEBUG` | Debug logging | `0` | `1` |
| `SCALPEL_CACHE_ENABLED` | Enable caching | `1` | `0` |

### Transport & Testing
| Variable | Purpose | Default | Example |
|----------|---------|---------|---------|
| `MCP_CONTRACT_TRANSPORT` | Transport protocol | `stdio` | `http` |
| `SCALPEL_MCP_BASE` | HTTP base URL | `http://127.0.0.1:18080` | Custom URL |
| `CODE_SCALPEL_RUN_MCP_CONTRACT` | Enable contract tests | `0` | `1` |

### Auto-Init
| Variable | Purpose | Default | Example |
|----------|---------|---------|---------|
| `CODE_SCALPEL_CONFIG_AUTO_INIT` | Enable auto-init | `0` | `1` |
| `CODE_SCALPEL_CONFIG_AUTO_INIT_MODE` | Init mode | `safe` | `full` |
| `CODE_SCALPEL_CONFIG_AUTO_TARGET` | Init location | `project` | `user` |

## Advanced Configuration

### Custom Response Profiles
Create custom profiles in `response_config.json`:
```json
{
  "profiles": {
    "production": {
      "exclude": ["debug_info", "raw_data"],
      "max_tokens": 1000
    }
  }
}
```

### Policy Extensions
Add custom Rego policies in `.code-scalpel/policies/`:
```rego
# custom_security.rego
package custom

deny[msg] {
  # Custom security rule
  msg := "Custom security violation"
}
```

### Governance Overrides
Override governance via environment:
```bash
export SCALPEL_CHANGE_BUDGET_MAX_LINES=1000
export SCALPEL_CHANGE_BUDGET_MAX_FILES=20
```

### Tier-Specific Configuration
Different tiers have different limits. Configure in `limits.toml`:
```toml
[community]
max_files_per_change = 5
max_lines_per_change = 200

[pro]
max_files_per_change = 10
max_lines_per_change = 500

[enterprise]
max_files_per_change = 50
max_lines_per_change = 2000
```

## Troubleshooting

### Common Issues

#### MCP Server Won't Start
- Check license file exists and is valid
- Verify `CODE_SCALPEL_LICENSE_PATH` is set correctly
- Ensure `.code-scalpel` directory exists (run `code-scalpel init`)

#### Configuration Not Loading
- Run `code-scalpel validate-config` to check configuration
- Check file permissions on `.code-scalpel/` directory
- Verify JSON/YAML syntax in config files

#### Policy Violations
- Use `code-scalpel verify-policies` to check policy integrity
- Review audit logs in `.code-scalpel/audit.log`
- Check enforcement mode in `policy.yaml` (should be "warn" for testing)

#### Performance Issues
- Enable caching: `export SCALPEL_CACHE_ENABLED=1`
- Adjust response profiles to reduce token usage
- Check complexity history in `.code-scalpel/complexity_history.json`

### Debugging
Enable detailed logging:
```bash
export SCALPEL_MCP_OUTPUT=DEBUG
export SCALPEL_MCP_DEBUG=1
```

### Validation Commands
```bash
# Validate all configuration
code-scalpel validate-config

# Verify policy integrity
code-scalpel verify-policies

# Run MCP contract tests
export CODE_SCALPEL_RUN_MCP_CONTRACT=1
code-scalpel test-mcp
```

## Security Best Practices

1. **Never commit secrets**: Add `.code-scalpel/development-*.private.pem` to `.gitignore`
2. **Use minimal permissions**: Run with least privilege required
3. **Regular audits**: Review `.code-scalpel/audit.log` periodically
4. **Policy verification**: Always verify policies after changes
5. **License management**: Keep license files secure and up-to-date

## Integration Examples

### VS Code Integration
Create `.vscode/settings.json`:
```json
{
  "code-scalpel.licensePath": ".code-scalpel/license/license.jwt",
  "code-scalpel.configPath": ".code-scalpel"
}
```

### CI/CD Integration
```yaml
# .github/workflows/ci.yml
env:
  CODE_SCALPEL_LICENSE_PATH: .code-scalpel/license/license.jwt
  SCALPEL_MCP_OUTPUT: INFO

steps:
  - name: Validate Configuration
    run: code-scalpel validate-config
```

### Docker Integration
```dockerfile
FROM python:3.11

# Copy configuration
COPY .code-scalpel /app/.code-scalpel

# Set environment
ENV CODE_SCALPEL_LICENSE_PATH=/app/.code-scalpel/license/license.jwt
ENV SCALPEL_MCP_OUTPUT=INFO

# Run MCP server
CMD ["python", "-m", "code_scalpel.mcp.server"]
```

## Support and Resources

- **Documentation**: Check individual config files for inline comments
- **Logs**: Review `.code-scalpel/audit.log` for detailed operation logs
- **Validation**: Use built-in validation commands to check setup
- **Community**: Refer to project README for community resources

For additional help, run `code-scalpel --help` or check the project documentation.