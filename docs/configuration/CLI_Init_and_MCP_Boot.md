# CLI Init and MCP Boot Configuration

This document covers the `code-scalpel init` CLI command and the automatic configuration initialization during MCP server first boot.

## CLI Init Command

### Command Syntax
```bash
code-scalpel init [--dir DIRECTORY] [--force]
```

### Arguments
- `--dir`, `-d`: Target directory for initialization (default: current working directory)
- `--force`, `-f`: Force initialization even if `.code-scalpel` directory already exists

### Implementation Details
The command is implemented in `src/code_scalpel/cli.py` in the `init_configuration` function. It calls `init_config_dir()` from `src/code_scalpel/config/init_config.py`.

### Initialization Modes
- **"full"** (default): Complete initialization including templates, manifest, and .env generation
- **"templates_only"**: Minimal scaffolding for server auto-init

### What Gets Created
When running `code-scalpel init`, the following directory structure is created in the target directory:

```
.code-scalpel/
├── config.json                    # Master governance configuration
├── policy.yaml                    # Security and modification policies
├── budget.yaml                    # Change budget constraints
├── response_config.json           # MCP response optimization
├── dev-governance.yaml           # Development governance policies
├── project-structure.yaml        # Project organization expectations
├── policies/                     # Reusable Rego policy packs
│   ├── architecture/
│   ├── devops/
│   ├── devsecops/
│   └── project/
├── policy.manifest.json          # Policy integrity manifest
├── development-2025-01.private.pem # Private key for signing
├── audit.log                     # Security audit trail
├── audit.jsonl                   # Structured audit log
├── complexity_history.json       # Code complexity tracking
├── limits.toml                   # Tier-specific tool limits
├── license/                      # License management
│   ├── README.md
│   └── license.jwt (when installed)
├── ide-extension.json            # IDE extension configuration
├── HOOKS_README.md               # Claude Code hooks documentation
├── README.md                     # Main directory documentation
├── GOVERNANCE_PROFILES.md        # Configuration profiles guide
└── .gitignore                    # Excludes sensitive files
```

### Security Considerations
- The private key (`development-2025-01.private.pem`) is generated during init and should never be committed to version control
- The policy manifest ensures cryptographic integrity of policy files
- Audit logs provide tamper-evident logging of all decisions

## MCP First Boot Configuration

### Automatic Initialization
The MCP server includes automatic configuration initialization via `maybe_auto_init_config_dir()` in `src/code_scalpel/mcp/paths.py`. This prevents errors when the MCP server starts without a pre-existing `.code-scalpel` directory.

### Environment Variables for Auto-Init
- `CODE_SCALPEL_CONFIG_AUTO_INIT`: Enable/disable automatic initialization (any truthy value enables)
- `CODE_SCALPEL_CONFIG_AUTO_INIT_MODE`: Initialization mode
  - `"safe"` or `"templates_only"`: Minimal initialization without secrets/manifest
  - `"full"`: Complete initialization (same as CLI init)
- `CODE_SCALPEL_CONFIG_AUTO_TARGET`: Target location
  - `"project"`: Initialize in project root (default)
  - `"user"`: Initialize in user XDG config directory

### Auto-Init Flow
1. MCP server startup checks for `.code-scalpel` directory
2. If missing and auto-init enabled, creates directory structure
3. Uses specified mode (`templates_only` by default for safety)
4. Generates essential configuration files without sensitive secrets
5. Logs initialization actions for transparency

### Differences from CLI Init
- **CLI Init**: Always runs when requested, creates full configuration including secrets
- **MCP Auto-Init**: Only runs when directory is missing, defaults to minimal mode
- **Security**: Auto-init avoids creating private keys or manifests by default to prevent accidental exposure

## Configuration Validation

Both initialization methods validate configuration files after creation:

1. Schema validation for JSON/YAML files
2. Policy manifest creation and verification
3. License file discovery and validation
4. Cross-file consistency checks

## Usage Examples

### CLI Initialization
```bash
# Initialize in current directory
code-scalpel init

# Initialize in specific directory
code-scalpel init --dir /path/to/project

# Force re-initialization
code-scalpel init --force
```

### MCP Auto-Init
```bash
# Enable auto-init for project
export CODE_SCALPEL_CONFIG_AUTO_INIT=1
export CODE_SCALPEL_CONFIG_AUTO_INIT_MODE=safe

# Run MCP server - will auto-create config if needed
python -m code_scalpel.mcp.server
```

## Troubleshooting

### Common Issues
- **Permission Errors**: Ensure write access to target directory
- **Existing Directory**: Use `--force` flag or remove existing `.code-scalpel` directory
- **Validation Failures**: Check file permissions and schema compliance

### Validation Commands
After initialization, you can verify the setup:
```bash
code-scalpel verify-policies  # Check policy integrity
code-scalpel validate-config  # Validate configuration files
```

### Logs and Debugging
- Initialization actions are logged to stderr during MCP server startup
- Use `SCALPEL_MCP_OUTPUT=DEBUG` for detailed logging
- Check audit logs in `.code-scalpel/audit.log` for post-init activity