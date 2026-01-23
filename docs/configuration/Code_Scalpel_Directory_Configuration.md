# .code-scalpel Directory Configuration

The `.code-scalpel` directory contains configuration files that govern Code Scalpel's behavior, including MCP server settings, governance policies, security controls, and response formatting. This directory is created by the `code-scalpel init` CLI command or automatically during MCP first boot.

## CLI Command Implementation

The `code-scalpel init` command is implemented in `src/code_scalpel/cli.py` in the `init_configuration` function. It accepts the following arguments:

- `--dir`, `-d`: Target directory (default: current directory)
- `--force`, `-f`: Force initialization even if directory exists

The command calls `init_config_dir()` from `src/code_scalpel/config/init_config.py`, which supports two modes:

- **"full"** (CLI default): Complete initialization with templates, manifest, and .env generation
- **"templates_only"**: Minimal scaffolding for server auto-init

## MCP First Boot Configuration

The MCP server includes automatic configuration initialization via `maybe_auto_init_config_dir()` in `src/code_scalpel/mcp/paths.py`. This is controlled by environment variables:

- `CODE_SCALPEL_CONFIG_AUTO_INIT`: Enable/disable auto-init (truthy values)
- `CODE_SCALPEL_CONFIG_AUTO_INIT_MODE`: "safe" (templates_only) or "full"
- `CODE_SCALPEL_CONFIG_AUTO_TARGET`: "project" (in project root) or "user" (in XDG config)

When enabled, the MCP server will create a minimal `.code-scalpel/` directory on first startup if missing, preventing errors from missing configuration.

## Directory Structure and Files

### Core Configuration Files

#### config.json - Master governance configuration
- **Purpose**: Defines blast radius limits, critical paths, and governance profile
- **Schema**: JSON with version, governance object containing change_budgeting, blast_radius, autonomy_constraints, and audit sections
- **Default Values**:
  - Max lines per change: 500
  - Max files per change: 10
  - Max complexity delta: 50
  - Max autonomous iterations: 10
  - Audit retention: 90 days
- **Configuration Override**: Environment variables like `SCALPEL_CHANGE_BUDGET_MAX_LINES` can override values

#### policy.yaml - Security and code modification policies
- **Purpose**: OPA/Rego-based rules for code analysis and access control
- **Schema**: YAML with version, enforcement mode, security rules, and budgeting settings
- **Default Values**:
  - Enforcement: "warn"
  - SQL injection protection: enabled
  - Command injection protection: enabled
  - Path traversal protection: enabled
  - XSS protection: enabled
  - Change budgeting: disabled by default
- **Configuration Override**: Can be extended with custom Rego policies in the `policies/` subdirectory

#### budget.yaml - Change budget constraints
- **Purpose**: Persists session usage against defined limits for blast radius control
- **Schema**: YAML with version, budgets (file/line limits), reset mode, and exemptions
- **Default Values**:
  - Max files modified: 10
  - Max lines added: 500
  - Max lines deleted: 300
  - Reset mode: "session"
  - Exemptions: test files and docs
- **Configuration Override**: Not directly overridable, but limits can be adjusted manually

#### response_config.json - MCP response token optimization
- **Purpose**: Controls field inclusion/exclusion in MCP tool responses to save tokens
- **Schema**: JSON with global settings, profiles (minimal/standard/verbose/debug), and tool-specific overrides
- **Default Values**:
  - Global profile: "debug"
  - Exclude empty arrays/objects/null values by default
  - Tool-specific exclusions (e.g., exclude raw AST for analyze_code)
- **Configuration Override**: Profile can be set per tool, with tier-based exclusions for get_cross_file_dependencies

### Governance and Policy Files

#### dev-governance.yaml - Development governance policies
- **Purpose**: Meta-policies governing AI agent development workflow behavior
- **Schema**: YAML with policy definitions using Rego rules
- **Default Values**:
  - Mandatory README creation for new modules
  - Architectural boundary enforcement
  - Best practice requirements
- **Configuration Override**: Custom development policies can be added

#### project-structure.yaml - Project organization expectations
- **Purpose**: Defines expected file locations and naming conventions
- **Schema**: YAML with project_config containing file location rules
- **Default Values**:
  - Core modules in `src/code_scalpel/`
  - Tests in `tests/unit/`
  - Policies in `.code-scalpel/policies/`
- **Configuration Override**: Can be customized for project-specific structure

### Policy Engine Files

#### policies/ directory - Reusable Rego policy packs
- **Purpose**: Modular policy templates referenced by `policy.yaml`
- **Subdirectories**:
  - `architecture/`: Layered architecture enforcement
  - `devops/`: DevOps best practices
  - `devsecops/`: Security automation
  - `project/`: Project structure rules
- **Files**:
  - `layered_architecture.rego`: Prevents presentation→infrastructure calls
  - `docker_security.rego`: Dockerfile best practices
  - `secret_detection.rego`: Hardcoded secret detection
  - `project/structure.rego`: Project structure validation

### Security and Integrity Files

#### policy.manifest.json - Policy integrity manifest
- **Purpose**: HMAC-signed manifest ensuring policy files haven't been tampered with
- **Schema**: JSON with file hashes, signatures, and metadata
- **Generation**: Created during `init` with `generate_secret_key()` and `CryptographicPolicyVerifier.create_manifest()`
- **Verification**: Checked via `verify-policies` command or runtime governance

#### development-2025-01.private.pem - Private key for manifest signing
- **Purpose**: RSA private key for cryptographic policy integrity
- **Generation**: Created during init for tamper detection
- **Security**: Should not be committed to version control

### Runtime and Audit Files

#### audit.log - Security audit trail
- **Purpose**: Cryptographically signed log of governance events and policy decisions
- **Format**: Structured log entries with timestamps and signatures
- **Retention**: Configurable via `config.json` audit.retention_days

#### audit.jsonl - Structured audit log
- **Purpose**: JSON-lines format log of all tool executions and governance decisions
- **Format**: One JSON object per line with ts, iso_utc, and event data
- **Usage**: For programmatic analysis and compliance reporting

#### complexity_history.json - Code complexity tracking
- **Purpose**: Historical complexity metrics for trend analysis
- **Schema**: JSON with timestamps and complexity measurements
- **Usage**: By `crawl_project` tool for complexity monitoring

### Operational Files

#### limits.toml - Tier-specific tool limits
- **Purpose**: Defines capabilities for Community/Pro/Enterprise tiers
- **Schema**: TOML with tier sections containing tool limits
- **Configuration Override**: Can be customized per deployment

#### license/ directory - License management
- **Purpose**: Stores license keys and validation state
- **Files**:
  - `README.md`: Documentation
  - `license.jwt`: JWT license file (when installed)
  - `license_state.json`: Cached validation results

### IDE Integration Files

#### ide-extension.json - IDE extension configuration
- **Purpose**: Settings for IDE extensions and hooks
- **Schema**: JSON with enforcement modes, policies, exclusions, and audit settings
- **Default Values**:
  - Enforcement enabled with "warn" mode
  - Syntax validation and security scanning enabled

#### HOOKS_README.md - Claude Code hooks documentation
- **Purpose**: Guide for setting up pre/post-tool-use hooks
- **Content**: Installation instructions and enforcement modes

### Documentation Files

#### README.md - Main directory documentation
#### GOVERNANCE_PROFILES.md - Guide for selecting configuration profiles
#### .gitignore - Excludes sensitive runtime files from version control

## Configuration Override Mechanisms

1. **Environment Variables**: Many settings can be overridden (e.g., `SCALPEL_CHANGE_BUDGET_MAX_LINES`)
2. **Multiple Config Files**: Different profiles can be symlinked as `config.json`
3. **Programmatic**: Direct instantiation with custom values
4. **Per-Tool Overrides**: `response_config.json` allows tool-specific customizations
5. **Tier-Based**: Enterprise features enabled via licensing
6. **Policy Extensions**: Additional Rego policies in `policies/` subdirectories

## Security Model

- **Fail Closed**: All errors result in denying operations
- **Cryptographic Integrity**: HMAC verification of policy files via manifest
- **Audit Trail**: Tamper-evident logging of all decisions
- **Tier Enforcement**: License-gated features with runtime validation
- **Sandbox Execution**: Changes validated in isolated environment before application

## Initialization Flow

1. CLI `init` command → `init_config_dir(mode="full")`
2. Create `.code-scalpel/` directory structure
3. Generate templates via `templates.py`
4. Create HMAC secret and policy manifest
5. Write `.env` with security variables
6. Validate all configuration files

MCP auto-init follows the same flow but with `mode="templates_only"` by default, creating only essential files without secrets or manifests.