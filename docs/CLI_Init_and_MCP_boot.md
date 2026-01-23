# CLI Initialization and MCP Boot Process

<!-- Code Scalpel v3.0.0 - CLI Setup and Server Boot -->

## Overview

This guide covers the Command Line Interface (CLI) initialization process and Model Context Protocol (MCP) server boot sequence for Code Scalpel.

## Table of Contents

- [CLI Initialization](#cli-initialization)
- [MCP Server Boot Process](#mcp-server-boot-process)
- [Configuration Creation](#configuration-creation)
- [Boot Sequence](#boot-sequence)
- [Troubleshooting Boot Issues](#troubleshooting-boot-issues)

## CLI Initialization

### Basic Initialization

The `code-scalpel init` command sets up the local configuration:

```bash
code-scalpel init
```

**What it creates:**
- `.code-scalpel/config.json` - Main configuration file
- `.code-scalpel/governance.yaml` - Governance and policy settings
- `.code-scalpel/agent_limits.yaml` - Tier-specific limits (formerly limits.toml)
- `.code-scalpel/policy.yaml` - Policy definitions
- `.code-scalpel/project-structure.yaml` - Project structure definitions
- `.code-scalpel/policies/` - Directory with architecture, devops, devsecops, and project policies
- `.code-scalpel/license/` - Directory for license files
- `.code-scalpel/README.md` - Configuration documentation
- `.code-scalpel/.gitignore` - Git ignore rules
- `.code-scalpel/audit.log` - Audit trail
- `.code-scalpel/ide-extension.json` - IDE integration config
- `.code-scalpel/HOOKS_README.md` - Hooks documentation
- `.code-scalpel/policy.manifest.json` - Cryptographic policy manifest (full mode only)
- `.env` - Environment variables with generated secrets (full mode only)
- `.env.example` - Environment variable documentation template
- `.gitignore` entries for sensitive files

### Initialization Options

#### Full Initialization (Default)

Creates complete configuration structure with generated cryptographic secrets:

```bash
code-scalpel init
```

#### Templates Only

Creates configuration templates without executing or generating secrets:

```bash
code-scalpel init --mode templates_only
```

#### User-Level Configuration

Creates configuration in user home directory instead of project directory:

```bash
# Set target to user home (handled by SCALPEL_AUTO_INIT_TARGET)
export SCALPEL_AUTO_INIT_TARGET=user
code-scalpel init
```

### Configuration Templates

The init command generates several template files:

#### .env Template

```bash
# Code Scalpel Environment Variables
# =====================================
# Copy this file to .env and update with your actual secrets
# DO NOT commit .env file to version control

# ----------------------------------------------------------------------------
# Policy Engine Secrets
# ----------------------------------------------------------------------------

# SCALPEL_MANIFEST_SECRET (REQUIRED for production with cryptographic verification)
# Used to sign and verify policy manifests to prevent tampering
# Generate with: python -c "import secrets; print(secrets.token_hex(32))"
SCALPEL_MANIFEST_SECRET=your-64-char-hex-secret-key-here

# SCALPEL_TOTP_SECRET (Optional - for human override verification)
# Used for TOTP-based human verification when overriding policy decisions
# Generate with: python -c "import secrets; print(secrets.token_hex(16))"
# SCALPEL_TOTP_SECRET=your-32-char-hex-totp-secret-here

# ----------------------------------------------------------------------------
# Additional Configuration (Optional)
# ----------------------------------------------------------------------------

# Enable debug logging for policy engine
# DEBUG_POLICY_ENGINE=false

# Custom policy file location
# SCALPEL_POLICY_PATH=.code-scalpel/policy.yaml
```

#### config.json Template

```json
{
  "version": "3.0.0",
  "governance": {
    "change_budgeting": {
      "enabled": true,
      "max_lines_per_change": 500,
      "max_files_per_change": 10,
      "max_complexity_delta": 50,
      "require_justification": true,
      "budget_refresh_interval_hours": 24
    },
    "blast_radius": {
      "enabled": true,
      "max_affected_functions": 20,
      "max_affected_classes": 5,
      "max_call_graph_depth": 3,
      "warn_on_public_api_changes": true,
      "block_on_critical_paths": true,
      "critical_paths": [],
      "critical_path_max_lines": 50,
      "critical_path_max_complexity_delta": 10
    },
    "autonomy_constraints": {
      "max_autonomous_iterations": 10,
      "require_approval_for_breaking_changes": true,
      "require_approval_for_security_changes": true,
      "sandbox_execution_required": true
    },
    "audit": {
      "log_all_changes": true,
      "log_rejected_changes": true,
      "retention_days": 90
    }
  }
}
```

#### agent_limits.yaml Template

```yaml
# Agent Operation Limits
# [20251227_FEATURE] Limits for AI agent operations to prevent runaway usage

version: "1.0"

# Global limits per session
limits:
  max_files_read: 100
  max_tokens_per_session: 50000
  max_api_calls_per_hour: 1000

# Relationships:
# - These limits are checked by the MCP governance layer before tool execution
# - They complement change budgeting (autonomy.governance.change_budgeting in governance.yaml)
# - Change budgeting limits code modifications, these limit agent resource usage
```

## MCP Server Boot Process

### Boot Sequence Overview

1. **Environment Setup** - Load environment variables and configuration
2. **Configuration Validation** - Verify config files and licenses
3. **Security Initialization** - Set up integrity verification and secrets
4. **Tool Registration** - Register available MCP tools based on tier
5. **Transport Setup** - Initialize stdio or HTTP transport
6. **Server Start** - Begin accepting MCP requests

### Detailed Boot Steps

#### Step 1: Environment Loading

The server loads configuration in this priority order:

1. Built-in defaults
2. `.env` file
3. Environment variables
4. MCP client configuration
5. Runtime parameters

```python
# Pseudocode for environment loading
def load_environment():
    # Load .env file
    load_dotenv()

    # Override with environment variables
    config = {
        'project_root': os.getenv('SCALPEL_PROJECT_ROOT', '.'),
        'tier': os.getenv('SCALPEL_TIER', 'community'),
        'log_level': os.getenv('SCALPEL_LOG_LEVEL', 'INFO'),
        'cache_enabled': os.getenv('CODE_SCALPEL_CACHE_ENABLED', 'true').lower() == 'true'
    }

    return config
```

#### Step 2: License Validation

For Pro/Enterprise tiers, validate license:

```python
def validate_license():
    tier = os.getenv('SCALPEL_TIER', 'community')

    if tier in ['pro', 'enterprise']:
        license_path = os.getenv('CODE_SCALPEL_LICENSE_PATH')
        if not license_path:
            # Try auto-discovery
            license_path = find_license_file()

        if not license_path:
            raise ValueError(f"License required for {tier} tier")

        # Validate JWT license
        validate_jwt_license(license_path, tier)
```

#### Step 3: Configuration Loading

Load and validate configuration files:

```python
def load_configuration():
    # Load main config
    config_path = Path('.code-scalpel/config.json')
    if config_path.exists():
        with open(config_path) as f:
            config = json.load(f)

        # Validate governance config
        validate_governance_config(config.get('governance', {}))

        # Check integrity if hash provided
        config_hash = os.getenv('SCALPEL_CONFIG_HASH')
        if config_hash:
            validate_config_integrity(config, config_hash)

    # Load response config
    response_config_path = Path('.code-scalpel/response_config.json')
    if response_config_path.exists():
        with open(response_config_path) as f:
            response_config = json.load(f)
    else:
        response_config = get_default_response_config()

    return config, response_config
```

#### Step 4: Tool Registration

Register MCP tools based on tier and configuration:

```python
def register_tools(tier, config):
    tools = []

    # Core tools (all tiers)
    tools.extend([
        ExtractCode(),
        AnalyzeCode(),
        GetProjectMap(),
        GetCallGraph(),
        GetSymbolReferences(),
        GetFileContext()
    ])

    # Security tools (all tiers)
    tools.extend([
        SecurityScan(),
        UnifiedSinkDetect(),
        ScanDependencies()
    ])

    # Advanced tools (tier-dependent)
    if tier in ['pro', 'enterprise']:
        tools.extend([
            SymbolicExecute(),
            GenerateUnitTests(),
            CrossFileSecurityScan(),
            TypeEvaporationScan(),
            GetGraphNeighborhood()
        ])

    # Enterprise-only tools
    if tier == 'enterprise':
        tools.extend([
            GetCrossFileDependencies(),
            CodePolicyCheck(),
            VerifyPolicyIntegrity()
        ])

    # Apply governance filters
    governance_config = config.get('governance', {})
    tools = apply_governance_filters(tools, governance_config)

    return tools
```

#### Step 5: Transport Initialization

Set up the requested transport:

```python
def initialize_transport(transport_type):
    if transport_type == 'stdio':
        # Stdio transport for AI assistants
        return StdioTransport()

    elif transport_type == 'http':
        port = int(os.getenv('SCALPEL_HTTP_PORT', '8593'))
        host = os.getenv('SCALPEL_HTTP_HOST', '127.0.0.1')
        allow_lan = os.getenv('SCALPEL_ALLOW_LAN', 'false').lower() == 'true'

        return HTTPTransport(host=host, port=port, allow_lan=allow_lan)

    else:
        raise ValueError(f"Unknown transport: {transport_type}")
```

#### Step 6: Server Startup

Start the MCP server:

```python
def start_server():
    # Load environment and configuration
    env_config = load_environment()
    main_config, response_config = load_configuration()

    # Validate license
    validate_license()

    # Register tools
    tools = register_tools(env_config['tier'], main_config)

    # Initialize transport
    transport_type = os.getenv('SCALPEL_TRANSPORT', 'stdio')
    transport = initialize_transport(transport_type)

    # Create MCP server
    server = MCPServer(
        tools=tools,
        config=main_config,
        response_config=response_config,
        transport=transport
    )

    # Start serving
    logger.info(f"Starting Code Scalpel MCP server (tier: {env_config['tier']})")
    server.serve()
```

## Configuration Creation

### Auto-Initialization

Enable automatic configuration creation:

```bash
export SCALPEL_AUTO_INIT=1
export SCALPEL_AUTO_INIT_MODE=full  # or 'templates_only'
export SCALPEL_AUTO_INIT_TARGET=project  # or 'user'
```

When enabled, the server automatically creates missing configuration files on first run.

### Manual Configuration

For custom setups, create configuration files manually:

```bash
# Create directory structure
mkdir -p .code-scalpel/license

# Generate secure manifest secret
MANIFEST_SECRET=$(python -c "import secrets; print(secrets.token_hex(32))")

# Create .env file
cat > .env << EOF
SCALPEL_PROJECT_ROOT=.
SCALPEL_TIER=community
SCALPEL_MANIFEST_SECRET=${MANIFEST_SECRET}
CODE_SCALPEL_CACHE_ENABLED=true
EOF

# Create config.json
cat > .code-scalpel/config.json << 'EOF'
{
  "version": "1.0.0",
  "profile": "default",
  "description": "Default balanced configuration"
}
EOF
```

## Boot Sequence

### Normal Boot

```
1. Parse command line arguments
2. Load environment variables
3. Discover and load configuration files
4. Validate license (Pro/Enterprise)
5. Initialize governance controls
6. Register MCP tools based on tier
7. Set up transport (stdio/http)
8. Start MCP server loop
9. Begin accepting requests
```

### Boot with Auto-Initialization

```
1. Parse command line arguments
2. Check for existing configuration
  3. IF no config found:
    a. Create .code-scalpel directory
    b. Generate config.json with defaults
    c. Create agent_limits.yaml
    d. Generate .env template
4. Load environment and configuration
5. Validate license
6. Initialize governance
7. Register tools
8. Set up transport
9. Start server
```

### Boot Time Optimization

For faster startup in production:

```bash
# Pre-compile Python bytecode
python -m compileall .code-scalpel/

# Use PyPy for better performance
pypy -m code_scalpel.mcp.server

# Enable caching
export CODE_SCALPEL_CACHE_ENABLED=1
export SCALPEL_CACHE_DIR=/tmp/code-scalpel-cache
```

## Troubleshooting Boot Issues

### Server Won't Start

**Symptoms:**
- "ModuleNotFoundError" or import errors
- "command not found: code-scalpel"

**Solutions:**
```bash
# Check installation
pip list | grep code-scalpel

# Reinstall if needed
pip install --upgrade code-scalpel

# Check Python path
python -c "import code_scalpel; print(code_scalpel.__file__)"

# Use uv for isolated execution
uvx code-scalpel mcp --stdio
```

### Configuration Errors

**Symptoms:**
- "Invalid configuration" messages
- JSON parsing errors

**Solutions:**
```bash
# Validate JSON syntax
python -m json.tool .code-scalpel/config.json

# Check for missing required fields
python -c "
import json
config = json.load(open('.code-scalpel/config.json'))
print('Config version:', config.get('version'))
print('Governance enabled:', config.get('governance', {}).get('change_budgeting', {}).get('enabled'))
"

# Reset to defaults
code-scalpel config reset
```

### License Validation Failures

**Symptoms:**
- "License not found" or "Invalid license"
- Tools not available

**Solutions:**
```bash
# Check license path
export CODE_SCALPEL_LICENSE_PATH=/path/to/license.jwt
ls -la $CODE_SCALPEL_LICENSE_PATH

# Validate license format
python -m code_scalpel license validate

# Check license expiration
python -c "
import jwt
with open('/path/to/license.jwt') as f:
    token = f.read().strip()
    payload = jwt.decode(token, options={'verify_signature': False})
    print('Tier:', payload.get('tier'))
    print('Expires:', payload.get('exp'))
"
```

### Transport Issues

**Symptoms:**
- Connection refused
- Port already in use
- Firewall blocking connections

**Solutions:**
```bash
# Check port availability
netstat -tlnp | grep :8593

# Try different port
code-scalpel mcp --http --port 8594

# Check firewall
sudo ufw status
sudo ufw allow 8593

# Test connection
curl -v http://localhost:8593/health
```

### Performance Issues

**Symptoms:**
- Slow startup times
- High memory usage during boot

**Solutions:**
```bash
# Enable caching
export CODE_SCALPEL_CACHE_ENABLED=1

# Reduce governance checks for faster boot
export SCALPEL_GOVERNANCE_ENFORCEMENT=advisory

# Use minimal response profile
# Edit response_config.json to use "minimal" profile

# Profile startup time
time code-scalpel mcp --stdio --dry-run
```

### Auto-Initialization Problems

**Symptoms:**
- Configuration not created automatically
- Permission denied errors

**Solutions:**
```bash
# Check permissions
ls -ld .code-scalpel/

# Create directory manually
mkdir -p .code-scalpel

# Run init manually
code-scalpel init

# Check auto-init settings
export SCALPEL_AUTO_INIT=1
export SCALPEL_AUTO_INIT_TARGET=project
```

### Debugging Boot Process

Enable detailed logging:

```bash
# Set debug logging
export SCALPEL_LOG_LEVEL=DEBUG

# Enable tracing
export SCALPEL_ENABLE_TRACING=true

# Boot with verbose output
code-scalpel mcp --stdio --verbose

# Check logs
tail -f /tmp/code-scalpel.log
```

### Common Boot Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `ModuleNotFoundError` | Missing dependencies | `pip install code-scalpel[all]` |
| `Permission denied` | No write access | `chmod 755 .code-scalpel` |
| `Invalid license` | Corrupted license file | Re-download license |
| `Port in use` | Another service using port | Change port with `--port` |
| `Config validation failed` | Invalid JSON | Validate with `python -m json.tool` |
| `Hash mismatch` | Tampered config | Regenerate config hash |

## See Also

- [Configuration Guide](Configuration_Guide.md) - Complete configuration reference
- [MCP Configuration](MCP_Configuration.md) - MCP server setup details
- [Troubleshooting](../troubleshooting/) - General troubleshooting