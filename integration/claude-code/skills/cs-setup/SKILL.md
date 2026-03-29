---
name: cs-setup
description: |
  Install and verify the Code Scalpel MCP server. Checks if codescalpel is already
  installed in Claude Code, runs `claude mcp add` if needed, and confirms connection
  by fetching capabilities.
allowed-tools:
  - Bash
  - mcp__codescalpel__get_capabilities
preamble-tier: 1
---

# /cs-setup — Install & Verify Code Scalpel MCP

This command installs the Code Scalpel MCP server and verifies it's working correctly.

## What it does

1. **Checks** if `codescalpel` is already registered in `claude mcp list`
2. **Installs** the MCP server if not present: `claude mcp add codescalpel uvx codescalpel mcp`
3. **Verifies** connection by calling `get_capabilities`
4. **Shows** your license tier and available tools

## For Pro/Enterprise Users

If you have a license file, install with:
```bash
claude mcp add codescalpel \
  -e CODE_SCALPEL_LICENSE_PATH=/path/to/license.jwt \
  uvx codescalpel mcp
```

## Next Steps

Once verified, try these commands:
- `/cs-extract` — Extract a function by name (saves 95% context vs reading whole files)
- `/cs-security` — Run a full security audit
- `/cs-analyze` — Analyze your project structure

See `CLAUDE.md` in your project root for the complete guide.
