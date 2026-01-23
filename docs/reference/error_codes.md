# Error Codes (V1.0 Contract)

This document defines the minimum error-code registry shared by all Code Scalpel MCP tools.

Source of truth for this requirement: `docs/guides/production_release_v1.0.md`.

## Principles

- Error codes are stable and machine-parseable.
- Error codes are independent of transport and client.
- The human-readable `error` message may change; `error_code` should not.

## Minimum Registry

The following error codes are the minimum set required for V1.0:

- `invalid_argument`: input schema/type/value invalid
- `invalid_path`: path rejected due to validation, traversal, or outside allowed roots
- `forbidden`: permission denied or policy forbids the operation
- `not_found`: referenced file/resource does not exist
- `timeout`: operation exceeded configured limits
- `too_large`: request or result exceeded size bounds
- `resource_exhausted`: memory/CPU/resource limits exceeded
- `not_implemented`: feature not implemented in this distribution/tier
- `upgrade_required`: request requires a higher tier
- `dependency_unavailable`: required dependency missing/unavailable
- `internal_error`: unexpected failure

## Usage

In the universal response envelope (`docs/reference/mcp_response_envelope.md`), errors are represented as:

- `error.error_code`: one of the codes above

## Non-goals

- This registry is not an exhaustive taxonomy.
- Tool-specific subcodes may be introduced later, but the top-level `error_code` must remain within the registry.
