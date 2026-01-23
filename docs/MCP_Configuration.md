# MCP Configuration

<!-- Code Scalpel v3.0.0 - MCP Server Setup and Configuration -->

## Overview

This guide covers the Model Context Protocol (MCP) server configuration for Code Scalpel, including transport options, response formatting, client integrations, and troubleshooting.

## Table of Contents

- [MCP Server Setup](#mcp-server-setup)
- [Transport Options](#transport-options)
- [Response Configuration](#response-configuration)
- [Client Integrations](#client-integrations)
- [Configuration Profiles](#configuration-profiles)
- [Docker Deployment](#docker-deployment)
- [CI/CD Integration](#cicd-integration)
- [Troubleshooting](#troubleshooting)

## MCP Server Setup

### Basic Setup

1. **Install Code Scalpel**
   ```bash
   pip install code-scalpel
   ```

2. **Initialize Configuration**
   ```bash
   code-scalpel init
   ```

3. **Start MCP Server**
   ```bash
   # Stdio transport (recommended for AI assistants)
   code-scalpel mcp --stdio

   # HTTP transport
   code-scalpel mcp --http --port 8593
   ```

### Configuration Files Created

The `code-scalpel init` command creates:

- `.code-scalpel/config.json` - Governance and behavior settings
- `.code-scalpel/limits.toml` - Tier-specific limits
- `.code-scalpel/response_config.json` - MCP response formatting
- `.code-scalpel/license/` - License file directory

## Transport Options

### Stdio Transport (Recommended)

Best for AI assistant integration with direct process communication.

```bash
code-scalpel mcp --stdio --root /path/to/project
```

**Advantages:**
- No network configuration
- Secure (no network exposure)
- Low latency
- Automatic lifecycle management

### HTTP Transport

For remote access, team sharing, or web service integration.

```bash
# Local access only
code-scalpel mcp --http --port 8593

# Allow LAN access for team use
code-scalpel mcp --http --port 8593 --allow-lan

# Custom host/port
code-scalpel mcp --http --host 0.0.0.0 --port 8080
```

**Health Check Endpoint:**
```bash
curl http://localhost:8594/health
# {"status": "healthy", "version": "3.0.0", "tools": 22}
```

### WebSocket Transport

**Note:** WebSocket transport is planned for future release. Currently, stdio and HTTP transports are supported.

## Response Configuration

### Overview

Code Scalpel supports configurable MCP response output for token efficiency. Responses can be customized globally and per-tool.

### Configuration File

Location: `.code-scalpel/response_config.json`

Searches in order:
1. `{project_root}/.code-scalpel/response_config.json`
2. `~/.config/code-scalpel/response_config.json`
3. Built-in defaults

### Profiles

#### Minimal (Default)
Maximum token efficiency - only essential data.
- **Envelope fields**: None (just `data`)
- **Excludes**: `success`, `server_version`, `function_count`, `class_count`, `error` (when null)
- **Use case**: Production AI agents with tight token budgets

#### Standard
Balanced output with essential metadata.
- **Envelope fields**: `error`, `upgrade_hints`
- **Excludes**: `server_version`, `function_count`, `class_count`
- **Use case**: Most production environments

#### Debug
Full output including all metadata.
- **Envelope fields**: All fields
- **Excludes**: Nothing
- **Use case**: Development, troubleshooting

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
    "minimal": {
      "exclude_fields": ["success", "server_version", "function_count", "class_count"],
      "exclude_null_error": true
    },
    "standard": {
      "exclude_fields": ["server_version", "function_count", "class_count"]
    },
    "debug": {
      "exclude_fields": []
    }
  },
  "tool_overrides": {
    "analyze_code": {
      "profile": "minimal",
      "include_only": [
        "functions", "classes", "imports", "complexity",
        "lines_of_code", "function_details", "class_details"
      ]
    }
  }
}
```

### Per-Tool Overrides

Customize responses for specific tools:

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
    },
    "generate_unit_tests": {
      "profile": "debug",
      "include_only": ["tests", "coverage", "execution_paths"]
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
          "cognitive_complexity", "halstead_metrics",
          "compliance_issues", "custom_rule_violations"
        ],
        "pro": ["compliance_issues"]
      }
    }
  }
}
```

### Debug Override

Force debug profile for troubleshooting:

```bash
export SCALPEL_MCP_OUTPUT=DEBUG
# All responses include full metadata regardless of configuration
```

### Example Responses

#### Minimal Profile
```json
{
  "data": {
    "functions": ["process_payment", "validate_input"],
    "classes": ["PaymentProcessor"],
    "complexity": 3,
    "lines_of_code": 45
  }
}
```

#### Standard Profile
```json
{
  "error": null,
  "upgrade_hints": [],
  "data": {
    "functions": ["process_payment", "validate_input"],
    "classes": ["PaymentProcessor"],
    "complexity": 3,
    "lines_of_code": 45,
    "function_details": [...]
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
  "duration_ms": 12,
  "error": null,
  "upgrade_hints": [],
  "data": {
    "success": true,
    "server_version": "3.3.0",
    "functions": ["process_payment", "validate_input"],
    "classes": ["PaymentProcessor"],
    ...
  }
}
```

### Token Efficiency

- **Minimal vs Debug**: ~150-200 tokens saved per response
- **1000 tool calls**: 150,000-200,000 tokens preserved
- **Equivalent to**: 50-70 pages of documentation context

## Client Integrations

### VS Code / GitHub Copilot

**.vscode/mcp.json:**
```json
{
  "mcpServers": {
    "code-scalpel": {
      "command": "python",
      "args": ["-m", "code_scalpel.mcp.server"],
      "env": {
        "SCALPEL_PROJECT_ROOT": "${workspaceFolder}",
        "SCALPEL_TIER": "community"
      }
    }
  }
}
```

### Claude Desktop

**macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`

**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

**Linux:** `~/.config/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "code-scalpel": {
      "command": "code-scalpel",
      "args": ["mcp", "--root", "/path/to/project"],
      "env": {
        "SCALPEL_TIER": "community",
        "SCALPEL_MANIFEST_SECRET": "your-secret-here"
      }
    }
  }
}
```

### Cursor IDE

**.cursor/mcp.json:**
```json
{
  "mcpServers": {
    "code-scalpel": {
      "command": "code-scalpel",
      "args": ["mcp", "--root", "${workspaceFolder}"],
      "env": {
        "SCALPEL_PROJECT_ROOT": "${workspaceFolder}"
      }
    }
  }
}
```

### Custom MCP Client

**HTTP Transport:**
```bash
curl -X POST http://localhost:8593/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "method": "tools/call",
    "params": {
      "name": "analyze_code",
      "arguments": {"file_path": "src/main.py"}
    }
  }'
```

**WebSocket Transport:**
```javascript
// WebSocket transport planned for future release
// Currently use HTTP transport for persistent connections
```

## Configuration Profiles

### Development Profile

```json
{
  "global": {
    "profile": "debug"
  },
  "tool_overrides": {
    "*": {
      "profile": "debug"
    }
  }
}
```

### Production Profile

```json
{
  "global": {
    "profile": "minimal"
  },
  "tool_overrides": {
    "security_scan": {
      "profile": "standard"
    },
    "analyze_code": {
      "profile": "minimal",
      "exclude_when_tier": {
        "community": ["cognitive_complexity", "halstead_metrics"]
      }
    }
  }
}
```

### CI/CD Profile

```json
{
  "global": {
    "profile": "minimal",
    "exclude_null_values": true,
    "exclude_empty_arrays": true
  },
  "tool_overrides": {
    "*": {
      "profile": "minimal",
      "include_only": ["success", "error", "data"]
    }
  }
}
```

## Docker Deployment

### Basic Docker Setup

```bash
# Pull image
docker pull ghcr.io/3d-tech-solutions/code-scalpel:3.0.0

# Run HTTP server
docker run -d -p 8593:8593 -p 8594:8594 \
  -v /path/to/project:/project \
  ghcr.io/3d-tech-solutions/code-scalpel:3.0.0 \
  mcp --http --host 0.0.0.0 --port 8593
```

### Docker Compose

```yaml
version: '3.8'
services:
  code-scalpel:
    image: ghcr.io/3d-tech-solutions/code-scalpel:3.0.0
    ports:
      - "8593:8593"  # MCP server
      - "8594:8594"  # Health check
    volumes:
      - ./:/project:ro
      - ./.code-scalpel:/config
    environment:
      - SCALPEL_PROJECT_ROOT=/project
      - SCALPEL_TIER=community
      - CODE_SCALPEL_CACHE_ENABLED=true
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8594/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### Environment Variables in Docker

```bash
docker run -i \
  -e SCALPEL_PROJECT_ROOT=/workspace \
  -e SCALPEL_TIER=community \
  -e SCALPEL_LOG_LEVEL=INFO \
  -e CODE_SCALPEL_CACHE_ENABLED=true \
  -v $(pwd):/workspace \
  3dtechsolutions/code-scalpel:latest \
  mcp --stdio
```

## CI/CD Integration

### GitHub Actions

```yaml
name: Security Scan
on: [push, pull_request]

jobs:
  scan:
    runs-on: ubuntu-latest
    services:
      code-scalpel:
        image: ghcr.io/3d-tech-solutions/code-scalpel:3.0.0
        ports:
          - 8593:8593
        env:
          SCALPEL_PROJECT_ROOT: ${{ github.workspace }}
          SCALPEL_TIER: community
    steps:
      - uses: actions/checkout@v4
      - name: Wait for server
        run: |
          for i in {1..30}; do
            curl -s http://localhost:8594/health && break
            sleep 1
          done
      - name: Run security scan
        run: |
          curl -X POST http://localhost:8593/mcp \
            -H "Content-Type: application/json" \
            -d '{"method": "tools/call", "params": {"name": "security_scan", "arguments": {"file_path": "src/"}}}'
```

### Jenkins Pipeline

```groovy
pipeline {
    agent any
    stages {
        stage('Security Scan') {
            steps {
                script {
                    docker.image('ghcr.io/3d-tech-solutions/code-scalpel:3.0.0').withRun('-p 8593:8593 -e SCALPEL_PROJECT_ROOT=/workspace') { c ->
                        sh 'sleep 10' // Wait for server to start
                        sh '''
                            curl -X POST http://localhost:8593/mcp \
                              -H "Content-Type: application/json" \
                              -d '{"method": "tools/call", "params": {"name": "security_scan", "arguments": {"file_path": "."}}}'
                        '''
                    }
                }
            }
        }
    }
}
```

### GitLab CI

```yaml
security_scan:
  image: ghcr.io/3d-tech-solutions/code-scalpel:3.0.0
  script:
    - code-scalpel mcp --http --port 8593 &
    - sleep 5
    - curl -X POST http://localhost:8593/mcp \
        -H "Content-Type: application/json" \
        -d '{"method": "tools/call", "params": {"name": "security_scan", "arguments": {"file_path": "."}}}'
```

## Troubleshooting

### Server Won't Start

**Symptoms:**
- "command not found: code-scalpel"
- Import errors

**Solutions:**
```bash
# Install Code Scalpel
pip install code-scalpel

# Or use uv
uvx code-scalpel --help

# Check Python version
python --version  # Should be 3.8+
```

### VS Code Can't Find Server

**Symptoms:**
- MCP server shows as "Not Started"
- Output shows connection errors

**Solutions:**
1. Validate `.vscode/mcp.json` JSON syntax
2. Check absolute paths for commands
3. Verify Python environment
4. Check Output → MCP panel for detailed errors

### Claude Desktop Not Showing Tools

**Symptoms:**
- No hammer icon in Claude
- Tools not available in chat

**Solutions:**
1. Restart Claude Desktop completely
2. Verify config file location (OS-specific)
3. Validate JSON syntax: `python -m json.tool config.json`
4. Check Claude logs for connection errors

### HTTP Transport Issues

**Symptoms:**
- Connection refused
- Health check fails

**Solutions:**
```bash
# Check if server is running
curl -v http://localhost:8594/health

# Check Docker logs
docker logs code-scalpel

# Verify port mapping
docker ps

# Test with different host
code-scalpel mcp --http --host 0.0.0.0 --port 8593
```

### Response Configuration Not Working

**Symptoms:**
- Unexpected response format
- Fields missing or extra

**Solutions:**
```bash
# Check active configuration
python -m code_scalpel config show

# Validate response config
python -c "import json; json.load(open('.code-scalpel/response_config.json'))"

# Force debug mode
export SCALPEL_MCP_OUTPUT=DEBUG
```

### Performance Issues

**Symptoms:**
- Slow response times
- High memory usage

**Solutions:**
```bash
# Enable caching
export CODE_SCALPEL_CACHE_ENABLED=1

# Increase timeouts for large projects
export SCALPEL_MAX_FILE_SIZE=52428800  # 50MB

# Use minimal response profile
# Set profile to "minimal" in response_config.json
```

### License Issues

**Symptoms:**
- Tier not recognized
- Tools unavailable

**Solutions:**
```bash
# Check license path
export CODE_SCALPEL_LICENSE_PATH=/path/to/license.jwt

# Validate license
python -m code_scalpel license validate

# Check tier detection
python -m code_scalpel config show | grep tier
```

## See Also

- [Configuration Guide](Configuration_Guide.md) - Complete configuration reference
- [CLI Initialization](CLI_Init_and_MCP_boot.md) - CLI setup and boot process
- [Tools Reference](../modules/MCP_SERVER.md) - Available MCP tools