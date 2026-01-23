# MCP Response Envelope (V2.0 Contract - v1.0.0)

This document defines the universal response envelope for all Code Scalpel MCP tools.

**🆕 v1.0.0**: Responses are now **fully configurable** via `.code-scalpel/response_config.json` for maximum token efficiency.

Source of truth for this requirement: `docs/guides/production_release_v1.0.md` and `docs/guides/configurable_response_output.md`.

## Goals

- Every tool returns a consistent, machine-parseable top-level shape.
- Clients can reliably correlate requests (`request_id`) and determine tier/tool metadata.
- Errors are standardized via `error_code` (see `docs/reference/error_codes.md`).
- **Token efficiency**: Omit redundant metadata by default, include only when needed or in debug mode.

## Envelope Schema (All Tools)

### Default Behavior (Minimal Profile - v1.0.0+)

By default, tools return only the essential data:

```json
{
  "data": { /* tool-specific response */ }
}
```

All metadata fields are **optional** and configurable:

- `tier` (string|null): one of `community`, `pro`, `enterprise` (omitted by default)
- `tool_version` (string|null): semantic version of the tool implementation (omitted by default)
- `tool_id` (string|null): canonical MCP tool id (omitted by default - client knows which tool was called)
- `request_id` (string|null): correlation id (omitted by default unless client-provided)
- `capabilities` (array[string]|null): describes what this invocation supports (omitted by default)
- `duration_ms` (number|null): end-to-end runtime in milliseconds (omitted by default, included in debug mode)
- `error` (object|null): standardized error model (only included when error occurs)
- `upgrade_hints` (array[object]|null): upgrade hints when a feature is unavailable at this tier (only included when hints exist)
- `data` (any|null): tool-specific payload (the tool's existing response model) - **ALWAYS INCLUDED**

### Configuration

Customize which fields are included via `.code-scalpel/response_config.json`:

```json
{
  "global": {
    "profile": "minimal"  // or "standard", "debug"
  },
  "tool_overrides": {
    "analyze_code": {
      "include_only": ["functions", "classes", "complexity"]
    }
  }
}
```

**Debug Mode**: Set `SCALPEL_MCP_OUTPUT=DEBUG` to include all metadata for troubleshooting.

**Learn more**: [Configurable Response Output Guide](../guides/configurable_response_output.md)

## Error Model

When `error` is not null, it MUST include:

- `error` (string): human-readable message
- `error_code` (string): machine-parseable error code
- `error_details` (object|null): optional structured details safe for clients

Notes:
- Error responses MUST NOT include code contents.
- Tools may still include tool-specific failure details inside `data`, but the standardized `error` is the primary contract.

## Upgrade Hints

When a requested feature is not available in the current tier, include one or more entries in `upgrade_hints`:

- `feature` (string)
- `tier` (string)
- `reason` (string)

## Examples

### Successful response (Minimal Profile - Default in v1.0.0+)

```json
{
  "data": {
    "risk_level": "high",
    "vulnerabilities": []
  }
}
```

### Successful response (Debug Mode - SCALPEL_MCP_OUTPUT=DEBUG)

```json
{
  "tier": "pro",
  "tool_version": "3.3.0",
  "tool_id": "security_scan",
  "request_id": "8b3e5f6c0a2f4ed4a3fb9e0b2f8f8d3a",
  "capabilities": ["envelope-v1"],
  "duration_ms": 27,
  "error": null,
  "upgrade_hints": [],
  "data": {
    "risk_level": "high",
    "vulnerabilities": []
  }
}
```

### Error response (Minimal Profile - Default)

```json
{
  "error": {
    "error": "File not found: /missing.py",
    "error_code": "not_found"
  }
}
```

### Error response (Debug Mode - SCALPEL_MCP_OUTPUT=DEBUG)

```json
{
  "tier": "community",
  "tool_version": "3.3.0",
  "tool_id": "extract_code",
  "request_id": "0a46e6c2b6df4e938e8d16ffb567a9b2",
  "capabilities": ["envelope-v1"],
  "duration_ms": 3,
  "error": {
    "error": "File not found: /missing.py",
    "error_code": "not_found",
    "error_details": null
  },
  "upgrade_hints": [],
  "data": null
}
```

---

## Token Efficiency

**v1.0.0 Token Savings:**
- Minimal profile: ~150-200 tokens saved per response
- 1,000 tool calls: 150,000-200,000 tokens preserved
- Equivalent to: 50-70 pages of documentation kept in context

**Why This Matters:**
AI agents have limited context windows. Every token spent on redundant metadata is a token not available for actual code work. Code Scalpel v1.0.0 ensures agents spend tokens on what matters: your code, not protocol overhead.
