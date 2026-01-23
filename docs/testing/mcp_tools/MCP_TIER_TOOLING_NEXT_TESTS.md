# MCP Tier/Tooling: What To Test Next

> [20251228_DOCS] Follow-on validation plan after migrating tier/license management to a standalone repo.

This repo’s primary integration surface is the **MCP server**. The next testing focus should be: **license discovery + tier fallback**, **license/CRL online integration**, **per-tool correctness via MCP**, **tier-aware expected outcomes**, and **response output shaping via `.code-scalpel/response_config.json`**.

## 1) Community fallback (no license in `.code-scalpel/`)

Goal: prove the server cleanly runs as Community when no license exists, even if the user requests Pro/Enterprise.

**Cases to test (MCP-first):**
- No `.code-scalpel/` directory at all.
- `.code-scalpel/` exists but no `license.jwt`.
- Default / Community requested with no license → effective tier is Community.
- `CODE_SCALPEL_TIER=pro` (or `enterprise`) but no license → server should **fail closed at startup** with a clear message.
- Invalid/unreadable license file (empty file, missing file, permission denied) → Community.

**Acceptance checks:**
- `list_tools` succeeds (tool surface still listed).
- A representative tool call succeeds (e.g., `analyze_code`).
- A paid-tier-only capability fails with a stable error envelope (upgrade-required) and does **not** crash the server.

## 2) MCP server “boot” + license/CRL online checks (local Docker)

> [20251228_DOCS] Local dev uses Docker verifier; beta/prod assumes verifier reachable.

### 2.1 Boot tier / identity information

What you can reliably test today via MCP:
- Effective `tier` included in responses when using the **debug** response profile (see section 5).
- Tool capability metadata (debug profile) matches the expected tier.

If testing remote-only verification, set `CODE_SCALPEL_LICENSE_VERIFIER_URL` to your verifier container and confirm:
- Boot succeeds when verifier is reachable.
- Boot succeeds when verifier is down but cached verification is fresh.

**Potential gap (confirm desired behavior):**
- The MCP server does not currently expose customer/org identity as a first-class MCP field at initialize-time. If you need customer/org surfaced, add an explicit, privacy-reviewed surface (e.g., a `get_license_info` tool or a `/health` payload field).

### 2.2 Online revocation (CRL fetch) via Docker containers

This repo supports CRL fetch/caching via `CODE_SCALPEL_ENABLE_CRL_FETCH=1` and `CODE_SCALPEL_LICENSE_CRL_URL=...`.

Test matrix:
- CRL server reachable → CRL cached → revoked `jti` downgrades to Community.
- CRL server down → cached CRL within offline window is used.
- CRL server down + no cache → startup still works (but revocation checks may be unavailable).

Suggested local setup:
- Run a small container that serves `/.well-known/license-crl.jwt`.
- Start MCP server with `CODE_SCALPEL_ENABLE_CRL_FETCH=1` and point `CODE_SCALPEL_LICENSE_CRL_URL` at the container.

## 3) Test each tool independently via MCP (Python libraries secondary)

Goal: validate each tool handler through the **MCP transport**, not direct Python calls.

Recommended approach:
- Use a stdio client (most deterministic) to:
  - `initialize` → `list_tools` → `call_tool` for exactly one tool.
- Repeat for streamable-http/SSE after stdio is stable.

Automation helper:
- Use [scripts/mcp_tool_explicit_test.py](../../scripts/mcp_tool_explicit_test.py) to run a focused MCP invocation set.

## 4) Test each tool by tier (expected vs actual)

Goal: “all tools are listed at all tiers” but **capabilities/limits differ**.

For each tier:
- Community:
  - Basic functionality works.
  - Paid capabilities are rejected with `upgrade_required` envelope.
- Pro:
  - Pro-only capabilities succeed.
  - Enterprise-only capabilities are rejected (if any).
- Enterprise:
  - Everything succeeds within configured limits.

Key tier-sensitive targets:
- Cross-file dependency resolution flags (`extract_code(include_cross_file_deps=True)`).
- Cross-file taint scan depth/limits.
- Dependency vulnerability scanning limits/timeouts.
- Policy/compliance reporting fields (Enterprise).

## 5) Response output shaping via `.code-scalpel/response_config.json`

Goal: prove response payload shape is controlled by config and remains contract-safe.

**Profiles to validate:**
- `minimal` (default): smallest payload.
- `standard`: includes `error` / `upgrade_hints` envelope fields.
- `debug`: includes `tier`, `capabilities`, timing metadata.

**Invariants to enforce:**
- Tool payload `success` remains present (contract-critical).
- Switching profile changes **only** response shape, not behavior.

Suggested checks:
- For the same tool call (e.g., `analyze_code`), record the JSON keys returned under each profile and diff them.

## 6) Additional functionality testing (as needed)

High-value follow-ups:
- **Transport robustness**: ensure zero stdout leakage for stdio.
- **Roots enforcement**: `validate_paths` and root-boundary behavior.
- **Regression set**: “invoke all tools” end-to-end remains green for stdio + HTTP/SSE.

