# Using the `code_scalpel_community` Export

> [20260108_DOCS] How to stage and publish the Community Edition snapshot while preserving MCP-first design and upgrade hooks.

## Purpose
- Provide a clean, redistributable Community Edition snapshot in `code_scalpel_community/`.
- Keep MCP as the primary interface; CLI secondary; Python package tertiary.
- Preserve upgrade hooks (license-driven enhancement download) without bundling Pro/Enterprise code.

## What lives in `code_scalpel_community/`
- Root metadata: README, LICENSE (MIT, 3D Tech Solutions LLC), pyproject.toml v4.0.0, requirements, MANIFEST, pytest.ini, .gitignore.
- Source (`src/code_scalpel/`):
  - MCP server with all 22 tools registered at Community capabilities.
  - Tier resolver + enhancement manager/loader stubs (no premium code shipped).
  - Community capability map and merge helper.
  - CLI (`code-scalpel init|mcp|version`).
- Docs: Community docs set, roadmap (22 tools), deep dives (9 guides), clean break plan.
- Examples: MCP + Python examples.

## How to use it
1) **Local staging** (already prepared):
   - Content sits under `code_scalpel_community/` and is ignored in the monorepo `.gitignore`.
2) **Standalone repo creation**:
   - Copy `code_scalpel_community/` contents into a fresh repo (e.g., `3D-Tech-Solutions/code_scalpel_community`).
   - Initialize git, set remote, commit.
3) **PyPI publish (Community)**:
   - From `code_scalpel_community/`: `python -m build` then `twine upload dist/*` (using proper credentials). The package name stays `code-scalpel`, version 4.0.0.
4) **MCP usage (primary)**:
   - `uvx code-scalpel init`
   - `uvx code-scalpel mcp`
   - Configure in Claude/Copilot/Cursor via `command: "uvx", args: ["code-scalpel", "mcp"]`.
5) **Upgrade path (Pro/Enterprise)**:
   - User places `license.jwt` at `~/.code-scalpel/license/license.jwt`.
   - On restart, server validates license → attempts enhancement download (from private feed) → merges capabilities; if absent/fails, stays Community.
6) **CLI (secondary) & Python (tertiary)**:
   - CLI available via `code-scalpel init|mcp|version`.
   - Python import available for direct scripting, but MCP is preferred.

## Exclusions (by design)
- No Pro/Enterprise capability code, governance/policy/autonomy modules, private keys/CRL/public endpoints, evidence/release artifacts, internal/prompts, caches, test suites.

## Validation checklist before release
- `code-scalpel mcp` runs in Community mode with no license present.
- Enhancement path degrades gracefully (no crash when enhancements absent).
- Docs links resolve within the exported repo structure.
- No premium code or secrets present in `code_scalpel_community/`.
