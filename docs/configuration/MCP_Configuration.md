# MCP Configuration Variables

This document details all environment variables and configuration options related to the Model Context Protocol (MCP) server functionality in Code Scalpel. These variables control logging, licensing, transport, caching, and other MCP-specific behaviors.

## MCP Server Configuration (Directly Controls MCP Behavior)

### SCALPEL_MCP_OUTPUT
- **Description**: Controls log verbosity level for the MCP server.
- **Valid Values**: `DEBUG`, `INFO`, `ALERT`, `WARNING` (case-insensitive).
- **Default**: `WARNING`.
- **Where Used**: Retrieved in `src/code_scalpel/mcp/server.py:139` to set logging level for MCP protocol messages. Also referenced in wiki documentation (`wiki/ENVIRONMENT_VARIABLES.md`) and guides (`docs/guides/configurable_response_output.md`).
- **Usage Example**: `SCALPEL_MCP_OUTPUT=DEBUG python -m code_scalpel.mcp.server`

### SCALPEL_MCP_DEBUG
- **Description**: Enables MCP debug logging.
- **Valid Values**: `0` (disabled), `1` (enabled).
- **Default**: `0`.
- **Where Used**: Mentioned in release notes (`docs/release_notes/RELEASE_NOTES_v1.0.0.md`) for enabling debug output in stderr during MCP server runs.

### SCALPEL_MCP_INFO
- **Description**: Sets log level for MCP debug logs in stderr.
- **Valid Values**: Log levels (e.g., `WARN`).
- **Default**: Not explicitly set (falls back to other logging configs).
- **Where Used**: Mentioned in release notes and used in testing scripts like `scripts/mcp_security_scan_stdio.py:29` where it's set to `DEBUG` for verbose output.

## MCP Transport and Testing (For MCP Server Testing/Invocation)

### CODE_SCALPEL_MCP_COMMAND
- **Description**: Custom command to invoke the MCP server during testing or validation scripts.
- **Valid Values**: Shell command string.
- **Default**: Auto-generated default server command (e.g., `python -m code_scalpel.mcp.server`).
- **Where Used**: Retrieved in testing scripts like `scripts/mcp_validate_enterprise_tier.py:228`, `scripts/mcp_validate_pro_tier.py:205`, and `scripts/mcp_validate_22_tools.py:170` to run MCP contract tests.

### CODE_SCALPEL_MCP_PYTHON
- **Description**: Python executable to use for running the MCP server in testing environments.
- **Valid Values**: Path to Python executable.
- **Default**: `sys.executable` (current Python interpreter).
- **Where Used**: Retrieved in `scripts/mcp_tool_explicit_test.py:210` for MCP tool testing.

### SCALPEL_MCP_BASE
- **Description**: Base URL for MCP HTTP server transport.
- **Valid Values**: HTTP/HTTPS URL (e.g., `http://127.0.0.1:18080`).
- **Default**: `http://127.0.0.1:18080`.
- **Where Used**: Retrieved in `scripts/mcp_security_scan_http.py:28` for HTTP-based MCP security scans.

### MCP_CONTRACT_TRANSPORT
- **Description**: Specifies the transport protocol for MCP contract tests.
- **Valid Values**: `stdio`, `http`.
- **Default**: `stdio`.
- **Where Used**: Retrieved in `tests/mcp/test_mcp_all_tools_contract.py:244` and CI workflows (`.github/workflows/ci.yml`, `.github/workflows/release-confidence.yml`) to run MCP tool contract validation over the specified transport.

### MCP_CONTRACT_ARTIFACT_DIR
- **Description**: Directory to store artifacts from MCP contract tests.
- **Valid Values**: File path.
- **Default**: Temporary directory (e.g., runner temp).
- **Where Used**: Retrieved in `tests/mcp/test_mcp_all_tools_contract.py:72` and CI workflows for evidence collection during MCP testing.

### CODE_SCALPEL_RUN_MCP_CONTRACT
- **Description**: Enables running MCP contract tests.
- **Valid Values**: `0` (disabled), `1` (enabled).
- **Default**: `0`.
- **Where Used**: Retrieved in `tests/mcp/test_mcp_all_tools_contract.py:25` to conditionally execute MCP contract validation.

## Licensing and Tier Configuration (Required for MCP Access)

These are essential for MCP server operation, as the server checks licensing to determine tool availability.

### CODE_SCALPEL_TIER / SCALPEL_TIER
- **Description**: Requests a specific tier for MCP server operations (can only downgrade, not upgrade).
- **Valid Values**: `community`, `pro`, `enterprise`, `free` (alias for community), `all` (alias for enterprise).
- **Default**: Uses licensed tier from license file.
- **Where Used**: Retrieved in `src/code_scalpel/mcp/server.py:178,5103` to determine available MCP tools and features. Also used in tier detection (`src/code_scalpel/licensing/tier_detector.py`) and testing helpers (`src/code_scalpel/mcp/helpers/context_helpers.py`).

### CODE_SCALPEL_LICENSE_PATH
- **Description**: Explicit path to JWT license file for MCP server access.
- **Valid Values**: Absolute or relative file path.
- **Default**: Auto-discovered from standard locations (e.g., `.code-scalpel/license/license.jwt`).
- **Where Used**: Retrieved in `src/code_scalpel/mcp/server.py:220` for license validation before enabling MCP tools. Extensively used in testing and validation scripts.

### CODE_SCALPEL_PROJECT_ROOT
- **Description**: Project root directory for MCP server code analysis.
- **Valid Values**: Directory path.
- **Default**: Current working directory (`.`).
- **Where Used**: Used in MCP server initialization and referenced in release notes for Docker/containerized MCP runs.

### CODE_SCALPEL_DISABLE_LICENSE_DISCOVERY
- **Description**: Disables automatic license file discovery for MCP server.
- **Valid Values**: `0` (enable discovery), `1` (disable, requires explicit `CODE_SCALPEL_LICENSE_PATH`).
- **Default**: `0`.
- **Where Used**: Retrieved in `src/code_scalpel/mcp/server.py:214` to control license loading.

## Caching and Performance (Affects MCP Tool Speed)

### SCALPEL_CACHE_ENABLED
- **Description**: Enables/disables analysis caching for MCP tools.
- **Valid Values**: `0` (disabled), `1` (enabled).
- **Default**: `1`.
- **Where Used**: Retrieved in `src/code_scalpel/mcp/helpers/security_helpers.py:63` and `src/code_scalpel/mcp/helpers/analyze_helpers.py:27` to toggle caching for MCP-based analyses.

### SCALPEL_NO_CACHE
- **Description**: Alternative flag to disable caching for MCP tools.
- **Valid Values**: `0` (enabled), `1` (disabled).
- **Default**: `0`.
- **Where Used**: Retrieved in `src/code_scalpel/mcp/helpers/analyze_helpers.py:28` for per-session cache control.

## Configuration Files (MCP-Related Settings)

These JSON/TOML files control MCP tool behavior, output formatting, and governance within the MCP server context.

### response_config.json (Located at `.code-scalpel/response_config.json`)
- **Description**: Controls output verbosity and formatting for all MCP tools, independent of tier. Defines profiles (e.g., `minimal`, `debug`) to manage token efficiency and response size.
- **Default Profile**: `debug` (includes all metadata for debugging).
- **Where Used**: Loaded by MCP server to customize tool responses; overrides per-tool fields to reduce output size. Referenced in schema validation and tool execution.

### config.json (Located at `.code-scalpel/config.json`)
- **Description**: Governance configuration for MCP autonomy, including change budgeting, blast radius limits, and audit settings that apply to MCP tool operations.
- **Where Used**: Influences MCP server behavior for autonomous changes (e.g., max lines/files per change via tools like `rename_symbol` or `update_symbol`).

### mcp.json (Client Configuration, Mentioned in Release Notes)
- **Description**: MCP client configuration file for connecting to the server.
- **Where Used**: Referenced in `docs/release_notes/RELEASE_NOTES_v1.0.0.md` as the client config for MCP protocol integration.

### CODE_SCALPEL_RESPONSE_CONFIG (Environment Variable for Config Path)
- **Description**: Path to response format configuration file.
- **Valid Values**: File path.
- **Default**: Auto-discovered (e.g., `.code-scalpel/response_config.json`).
- **Where Used**: Allows overriding the default response config location for MCP output control.