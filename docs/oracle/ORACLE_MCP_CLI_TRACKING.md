# Oracle MCP and CLI Tracking Matrix

> [20260311_DOCS] Living tracking document for Oracle coverage at both the MCP tool boundary and the CLI command boundary.

## Purpose

This document tracks whether Oracle-style corrective error handling is wired correctly for each public Code Scalpel tool when invoked through:

- MCP tool calls
- CLI command calls

It is intended to prevent three classes of drift:

- MCP tools that bypass `with_oracle_resilience` or collapse correctable failures into generic `internal_error`
- CLI commands that expose the same capability but do not route user-correctable failures through an Oracle-aware boundary
- tools that have an Oracle boundary on paper, but still fail to provide actionable guidance for one or more real user failure scenarios

## Oracle Outcome Requirement

For each public tool failure scenario, the system must do one of the following:

1. Return corrective guidance for a user-correctable failure.
2. Return an explicit upgrade or capability explanation for a tier-gated failure.
3. Return a clear non-correctable explanation for a genuinely internal or unsupported failure.

`internal_error` is acceptable only when the failure is not realistically recoverable from user guidance at the current boundary.

## Failure Scenario Classes

Each tool should be reviewed against the scenario classes that apply to it:

- `Path`: bad file path, bad project root, malformed Windows or WSL path, inaccessible report path
- `Symbol`: misspelled symbol, missing function, missing class, missing method, ambiguous symbol selector
- `Node ID`: malformed graph node ID, unsupported graph node kind, missing graph center node
- `Pattern or query`: invalid glob, invalid regex, invalid dependency selector, invalid filter pattern
- `Language or framework`: unsupported language, unsupported test framework, unsupported mode or format
- `Tier`: feature available only at a higher tier, report generation blocked by license tier, enterprise-only analysis request
- `Shape or argument`: missing required argument, invalid value range, malformed structured input
- `Internal`: parser crash, unexpected helper failure, external tool execution problem with no safe correction path

## Expected Guidance Semantics

The tracker should treat these outcomes as correct behavior:

- `correction_needed`: use for correctable path, symbol, node-ID, pattern, or similar user-input failures
- `upgrade_required`: use for explicit tier-gated requests where the next action is a higher capability tier
- `invalid_argument` with explanatory detail: use for malformed input shapes or ranges when the tool can explain what valid input looks like
- `not_found` with hint or alternatives: acceptable for lookup-style tools when the response still provides actionable recovery guidance
- `internal_error`: allowed only after the scenario has been classified as non-correctable at the current surface

## Current Boundary Rules

1. MCP coverage is considered present when the public tool entrypoint is wrapped with `with_oracle_resilience(...)`, or when an explicit exemption is documented.
2. CLI coverage is considered present only when the CLI path has its own Oracle-aware boundary or clearly routes through the Oracle-enabled MCP tool function.
3. Wrapper-level normalization still matters for path-taking tools. Oracle middleware alone is not sufficient when helpers collapse failures into result models instead of raising exceptions.
4. Pre-built `ToolResponseEnvelope` results must pass through the contract layer unchanged. Double-wrapping corrupts `ToolError` payloads and can erase `correction_needed` semantics.

## Current Source-of-Truth Findings

- MCP Oracle coverage is present on 19 public tools under `src/code_scalpel/mcp/tools/`.
- MCP Oracle coverage is currently absent on 4 public tools: `get_capabilities`, `unified_sink_detect`, `symbolic_execute`, and `simulate_refactor`.
- [20260311_DOCS] A shared CLI Oracle boundary is now implemented in `src/code_scalpel/cli_tools/tool_bridge.py` for the 20 MCP-equivalent commands that route through `invoke_tool_with_format(...)`.
- The standalone CLI commands `analyze`, `scan`, and `capabilities` still use separate non-bridge paths and should not be treated as CLI-parity complete.
- The CLI command `check` is a separate configuration audit command and is not the CLI surface for `code_policy_check`.

## Status Legend

- `Enabled`: Oracle boundary exists at that surface.
- `Absent`: No Oracle boundary exists at that surface.
- `Not exposed`: No CLI command exists for that MCP tool.
- `Exempt`: No Oracle boundary is expected for the current tool contract; justification must be documented.

## Tool Matrix

| Tool | CLI command | Primary scenario classes | MCP Oracle | MCP guidance status | CLI guidance status | Notes |
|---|---|---|---|---|---|---|
| `analyze_code` | `analyze` | `Path`, `Language`, `Shape` | Enabled | Complete | Partial | The CLI command now routes through the shared bridge and now has direct subprocess evidence for representative CLI `correction_needed` output on bad file paths, but full per-scenario CLI coverage is still incomplete. |
| `extract_code` | `extract-code` | `Path`, `Symbol`, `Shape` | Enabled | Complete | Partial | The CLI command now routes through the shared bridge and now has direct subprocess evidence for representative CLI `correction_needed` output on bad file paths, but full per-scenario CLI coverage is still incomplete. |
| `rename_symbol` | `rename-symbol` | `Path`, `Symbol`, `Tier`, `Shape` | Enabled | Complete | Partial | The CLI command now routes through the shared bridge and inherits MCP envelopes, but it still needs tool-specific CLI scenario coverage beyond the shared bridge checks. |
| `update_symbol` | `update-symbol` | `Path`, `Symbol`, `Shape` | Enabled | Complete | Partial | The CLI command now routes through the shared bridge and inherits MCP envelopes, but it still needs tool-specific CLI scenario coverage beyond the shared bridge checks. |
| `security_scan` | `scan` | `Path`, `Shape` | Enabled | Complete | Partial | The CLI command now routes through the shared bridge and now has direct subprocess evidence for representative CLI `invalid_argument` output on bad confidence thresholds, but full per-scenario CLI coverage is still incomplete. |
| `type_evaporation_scan` | `type-evaporation-scan` | `Path`, `Shape` | Enabled | Complete | Partial | The CLI command now routes through the shared bridge and inherits MCP envelopes, but it still needs tool-specific CLI scenario coverage beyond the shared bridge checks. |
| `scan_dependencies` | `scan-dependencies` | `Path`, `Shape` | Enabled | Complete | Partial | The CLI command now routes through the shared bridge and inherits MCP envelopes, but it still needs tool-specific CLI scenario coverage beyond the shared bridge checks. |
| `unified_sink_detect` | `unified-sink-detect` | `Language`, `Shape` | Absent | Complete | Partial | Direct wrapper validation now covers empty-code, unsupported-language, and invalid-threshold guidance without Oracle middleware. The CLI command now routes through the shared bridge, but dedicated CLI scenario coverage is still incomplete. |
| `symbolic_execute` | `symbolic-execute` | `Language`, `Shape`, `Internal` | Absent | Complete | Partial | Direct wrapper validation now covers empty-code, unsupported-language, invalid-range inputs, and preserves internal_error for true helper failures. The CLI command now routes through the shared bridge, but dedicated CLI scenario coverage is still incomplete. |
| `generate_unit_tests` | `generate-unit-tests` | `Path`, `Symbol`, `Language or framework`, `Tier` | Enabled | Complete | Partial | The CLI command now routes through the shared bridge and inherits MCP envelopes, but it still needs tool-specific CLI scenario coverage beyond the shared bridge checks. |
| `simulate_refactor` | `simulate-refactor` | `Shape`, `Internal` | Absent | Complete | Partial | Direct wrapper validation now covers malformed refactor-shape inputs and preserves internal_error for true helper failures. The CLI command now routes through the shared bridge, but dedicated CLI scenario coverage is still incomplete. |
| `crawl_project` | `crawl-project` | `Path`, `Pattern or query`, `Shape` | Enabled | Complete | Partial | The CLI command now routes through the shared bridge and inherits MCP envelopes, but it still needs tool-specific CLI scenario coverage beyond the shared bridge checks. |
| `get_file_context` | `get-file-context` | `Path`, `Shape` | Enabled | Complete | Partial | The CLI command now routes through the shared bridge and inherits MCP envelopes, but it still needs tool-specific CLI scenario coverage beyond the shared bridge checks. |
| `get_symbol_references` | `get-symbol-references` | `Path`, `Symbol`, `Tier` | Enabled | Complete | Partial | The CLI command now routes through the shared bridge and inherits MCP envelopes, but it still needs tool-specific CLI scenario coverage beyond the shared bridge checks. |
| `get_call_graph` | `get-call-graph` | `Path`, `Symbol`, `Shape` | Enabled | Complete | Partial | The CLI command now routes through the shared bridge and now has direct subprocess evidence for representative CLI `invalid_argument` output, but full per-scenario CLI coverage is still incomplete. |
| `get_graph_neighborhood` | `get-graph-neighborhood` | `Node ID`, `Path`, `Shape` | Enabled | Complete | Partial | The CLI command now routes through the shared bridge and now has direct subprocess evidence for representative CLI `correction_needed` output, but full per-scenario CLI coverage is still incomplete. |
| `get_project_map` | `get-project-map` | `Path`, `Pattern or query`, `Shape` | Enabled | Complete | Partial | The CLI command now routes through the shared bridge and inherits MCP envelopes, but it still needs tool-specific CLI scenario coverage beyond the shared bridge checks. |
| `get_cross_file_dependencies` | `get-cross-file-dependencies` | `Path`, `Symbol`, `Shape` | Enabled | Complete | Partial | The CLI command now routes through the shared bridge and inherits MCP envelopes, but it still needs tool-specific CLI scenario coverage beyond the shared bridge checks. |
| `cross_file_security_scan` | `cross-file-security-scan` | `Path`, `Pattern or query`, `Tier`, `Shape` | Enabled | Complete | Partial | The CLI command now routes through the shared bridge and inherits MCP envelopes, but it still needs tool-specific CLI scenario coverage beyond the shared bridge checks. |
| `validate_paths` | `validate-paths` | `Path`, `Shape` | Enabled | Complete | Partial | The CLI command now routes through the shared bridge and inherits MCP envelopes, but it still needs tool-specific CLI scenario coverage beyond the shared bridge checks. |
| `verify_policy_integrity` | `verify-policy-integrity` | `Path`, `Tier`, `Shape` | Enabled | Complete | Partial | The CLI command now routes through the shared bridge and inherits MCP envelopes, but it still needs tool-specific CLI scenario coverage beyond the shared bridge checks. |
| `code_policy_check` | `code-policy-check` | `Path`, `Pattern or query`, `Tier`, `Shape` | Enabled | Complete | Partial | The CLI command now routes through the shared bridge and now has direct subprocess evidence for representative CLI `upgrade_required` output, but full per-scenario CLI coverage is still incomplete. The CLI `check` command is not this tool. |
| `get_capabilities` | `capabilities` | `Tier`, `Shape`, `not_found` | Absent | Complete | Partial | Introspection tool; direct wrapper validation now covers invalid-tier and unknown-tool guidance without Oracle middleware. The CLI command now routes through the shared bridge and now has direct subprocess evidence for representative CLI `not_found` guidance on unknown tools, but full per-scenario CLI coverage is still incomplete. |

## Scenario Coverage Audit Rule

The matrix above should not be read as "Oracle exists, therefore coverage is complete." A tool only reaches full coverage when each applicable scenario class has evidence that it returns user-facing guidance rather than a silent fallback or opaque generic error.

Use these status meanings:

- `Missing`: no Oracle boundary or no scenario evidence exists
- `Partial`: Oracle boundary exists, but only some applicable failure scenarios have verified guidance
- `Complete`: all applicable scenario classes have verified guidance behavior and regression coverage
- `Exempt`: the scenario class does not apply to the tool and the exemption is documented

## Per-Tool Audit Checklist Template

For each tool, track these questions during audit:

1. Which scenario classes apply to this tool?
2. For each applicable scenario class, what is the expected error code and hint shape?
3. Is the guidance generated at the MCP boundary, the CLI boundary, or both?
4. Is there focused regression coverage proving the guidance path?
5. If a scenario still returns `internal_error`, is it genuinely non-correctable?

## Acceptance Criteria

The Oracle rollout should not be considered complete until all of the following are true:

- Every public MCP tool has an explicit scenario-class inventory.
- Every user-correctable MCP failure path returns guidance.
- Every tier-gated request returns an explicit upgrade-oriented explanation.
- Every CLI command mapped to an MCP-equivalent tool either provides equivalent guidance or is explicitly marked as non-parity work remaining.
- Regression coverage exists for at least one representative failure per applicable scenario class.
- `internal_error` is reserved for non-correctable failures, not missing recovery plumbing.

## Required Follow-Up for CLI Parity

The CLI now has a shared Oracle-aware boundary in `src/code_scalpel/cli_tools/tool_bridge.py` for the MCP-equivalent commands that use `invoke_tool_with_format(...)`. CLI parity is still incomplete because not every CLI command uses that bridge, and the bridge-routed commands do not yet have scenario-complete CLI regression coverage on a per-tool basis.

For each CLI-exposed tool, the desired end state is one of the following:

1. The CLI command calls the Oracle-enabled MCP function directly through the shared bridge.
2. The CLI command gets a dedicated Oracle-aware correction layer with equivalent `correction_needed` semantics.
3. The tool is explicitly documented as Oracle-exempt at the CLI boundary.

## Verification Checklist

- Confirm the public MCP tool registration is wrapped with `with_oracle_resilience(...)` when corrective recovery is expected.
- Confirm each applicable scenario class for the tool has an expected guidance outcome documented.
- Confirm path-taking MCP tools normalize incoming user paths before helper execution when helpers do not reliably raise correctable exceptions.
- Confirm CLI commands either route through the shared Oracle bridge or document the lack of Oracle parity.
- Confirm focused regression tests cover representative `correction_needed`, `upgrade_required`, or guided `invalid_argument` paths for the MCP boundary.
- Confirm envelope pass-through remains intact so a tool-returned `ToolResponseEnvelope` is not re-wrapped by the contract layer.
- Confirm `internal_error` is not masking a scenario that should be correctable.

## Evidence Pointers

- MCP Oracle middleware: `src/code_scalpel/mcp/oracle_middleware.py`
- Envelope pass-through: `src/code_scalpel/mcp/contract.py`
- Public MCP tools: `src/code_scalpel/mcp/tools/`
- CLI boundary: `src/code_scalpel/cli.py`
- Focused Oracle regressions: `tests/mcp/test_mcp.py`, `tests/mcp/test_oracle_middleware.py`, `tests/cli/test_cli_oracle_bridge.py`, `tests/cli/test_cli_oracle_subprocess.py`
- Testing-team guide: `docs/oracle/ORACLE_TESTING_GUIDE.md`

## Update Procedure

When a tool is changed:

1. Update the relevant row in the matrix.
2. Add or update focused regression coverage.
3. Record whether the change affected the MCP boundary, the CLI boundary, or both.
4. If a tool is intentionally exempt, document the reason in the Notes column instead of leaving the status ambiguous.

## Appendix: Per-Tool Testing Checklists

### `analyze_code`
- Applicable scenarios: `Path`, `Language`, `Shape`
- MCP checklist:
	- [ ] Malformed or missing file paths return `correction_needed` with a usable hint.
	- [ ] Unsupported language or invalid input shape returns guided validation output, not an opaque generic failure.
- CLI checklist:
	- [ ] The `analyze` command either matches MCP guidance behavior or the gap is explicitly recorded.

### `extract_code`
- Applicable scenarios: `Path`, `Symbol`, `Shape`
- MCP checklist:
	- [ ] Missing or misspelled symbols produce Oracle suggestions.
	- [ ] Bad file paths produce guidance rather than a generic failure.
- CLI checklist:
	- [ ] The `extract-code` command either matches MCP guidance behavior or the gap is explicitly recorded.

### `rename_symbol`
- Applicable scenarios: `Path`, `Symbol`, `Tier`, `Shape`
- MCP checklist:
	- [ ] Missing symbols provide rename-oriented recovery guidance.
	- [ ] Tier-gated rename requests explain the upgrade path when applicable.
- CLI checklist:
	- [ ] The `rename-symbol` command either matches MCP guidance behavior or the gap is explicitly recorded.

### `update_symbol`
- Applicable scenarios: `Path`, `Symbol`, `Shape`
- MCP checklist:
	- [ ] Missing or misspelled target symbols provide Oracle guidance.
	- [ ] Invalid replacement shape or target mismatch is explained clearly.
- CLI checklist:
	- [ ] The `update-symbol` command either matches MCP guidance behavior or the gap is explicitly recorded.

### `security_scan`
- Applicable scenarios: `Path`, `Language`, `Shape`
- MCP checklist:
	- [ ] Missing or malformed paths return `correction_needed` with recovery hints.
	- [ ] Unsupported language or malformed request shape returns guided validation output.
- CLI checklist:
	- [ ] The `scan` command either matches MCP guidance behavior or the gap is explicitly recorded.

### `type_evaporation_scan`
- Applicable scenarios: `Path`, `Shape`
- MCP checklist:
	- [ ] Bad frontend or backend file paths return guidance.
	- [ ] Invalid argument combinations are explained clearly.
- CLI checklist:
	- [ ] The `type-evaporation-scan` command either matches MCP guidance behavior or the gap is explicitly recorded.

### `scan_dependencies`
- Applicable scenarios: `Path`, `Pattern or query`, `Tier`
- MCP checklist:
	- [ ] Bad project-root or manifest paths return guidance.
	- [ ] Tier-gated dependency requests explain the required capability upgrade when applicable.
- CLI checklist:
	- [ ] The `scan-dependencies` command either matches MCP guidance behavior or the gap is explicitly recorded.

### `unified_sink_detect`
- Applicable scenarios: `Language`, `Shape`
- MCP checklist:
	- [ ] Unsupported language and malformed request-shape behavior is explicitly audited.
	- [ ] If Oracle remains absent, the missing guidance is documented as a gap rather than treated as acceptable behavior.
- CLI checklist:
	- [ ] The `unified-sink-detect` command either gains Oracle-equivalent guidance or the gap is explicitly recorded.

### `symbolic_execute`
- Applicable scenarios: `Language`, `Shape`, `Internal`
- MCP checklist:
	- [ ] Unsupported language and malformed request-shape behavior is explicitly audited.
	- [ ] True internal failures are distinguished from recoverable user mistakes.
- CLI checklist:
	- [ ] The `symbolic-execute` command either gains Oracle-equivalent guidance or the gap is explicitly recorded.

### `generate_unit_tests`
- Applicable scenarios: `Path`, `Symbol`, `Language or framework`, `Tier`
- MCP checklist:
	- [ ] Bad file paths return `correction_needed` with path hints.
	- [ ] Unsupported frameworks, missing functions, and tier-gated requests return guided recovery output.
- CLI checklist:
	- [ ] The `generate-unit-tests` command either matches MCP guidance behavior or the gap is explicitly recorded.

### `simulate_refactor`
- Applicable scenarios: `Shape`, `Internal`
- MCP checklist:
	- [ ] Malformed change inputs are clearly explained.
	- [ ] Non-correctable internal failures are distinguished from missing Oracle coverage.
- CLI checklist:
	- [ ] The `simulate-refactor` command either gains Oracle-equivalent guidance or the gap is explicitly recorded.

### `crawl_project`
- Applicable scenarios: `Path`, `Pattern or query`, `Shape`
- MCP checklist:
	- [ ] Invalid root paths return actionable path guidance.
	- [ ] Invalid patterns or malformed crawl arguments return guided validation output.
- CLI checklist:
	- [ ] The `crawl-project` command either matches MCP guidance behavior or the gap is explicitly recorded.

### `get_file_context`
- Applicable scenarios: `Path`, `Shape`
- MCP checklist:
	- [ ] Missing files return path guidance.
	- [ ] Invalid argument shape is explained clearly.
- CLI checklist:
	- [ ] The `get-file-context` command either matches MCP guidance behavior or the gap is explicitly recorded.

### `get_symbol_references`
- Applicable scenarios: `Path`, `Symbol`, `Tier`
- MCP checklist:
	- [ ] Bad project roots return guidance when the request is path-correctable.
	- [ ] Symbol lookup behavior is explicitly audited so empty-result contracts are not confused with Oracle failures.
- CLI checklist:
	- [ ] The `get-symbol-references` command either matches MCP guidance behavior or the gap is explicitly recorded.

### `get_call_graph`
- Applicable scenarios: `Path`, `Symbol`, `Shape`
- MCP checklist:
	- [ ] Invalid project roots return guidance.
	- [ ] Invalid entry-point or malformed request-shape behavior is explicitly audited.
- CLI checklist:
	- [ ] The `get-call-graph` command either matches MCP guidance behavior or the gap is explicitly recorded.

### `get_graph_neighborhood`
- Applicable scenarios: `Node ID`, `Path`, `Shape`
- MCP checklist:
	- [ ] Invalid center node IDs return guided format or candidate-node guidance.
	- [ ] Invalid project roots and malformed request shapes return guided recovery output.
- CLI checklist:
	- [ ] The `get-graph-neighborhood` command either matches MCP guidance behavior or the gap is explicitly recorded.

### `get_project_map`
- Applicable scenarios: `Path`, `Pattern or query`, `Shape`
- MCP checklist:
	- [ ] Invalid project roots return path guidance.
	- [ ] Invalid map options or malformed request shape is explained clearly.
- CLI checklist:
	- [ ] The `get-project-map` command either matches MCP guidance behavior or the gap is explicitly recorded.

### `get_cross_file_dependencies`
- Applicable scenarios: `Path`, `Symbol`, `Shape`
- MCP checklist:
	- [ ] Invalid target files and project roots return guidance.
	- [ ] Missing symbols or malformed selectors return guided recovery output.
- CLI checklist:
	- [ ] The `get-cross-file-dependencies` command either matches MCP guidance behavior or the gap is explicitly recorded.

### `cross_file_security_scan`
- Applicable scenarios: `Path`, `Pattern or query`, `Tier`, `Shape`
- MCP checklist:
	- [ ] Invalid project roots return actionable guidance.
	- [ ] Tier-gated or malformed scan requests return clear next-step explanations.
- CLI checklist:
	- [ ] The `cross-file-security-scan` command either matches MCP guidance behavior or the gap is explicitly recorded.

### `validate_paths`
- Applicable scenarios: `Path`, `Shape`
- MCP checklist:
	- [ ] Invalid target paths return guidance.
	- [ ] Malformed validation requests return guided validation output.
- CLI checklist:
	- [ ] The `validate-paths` command either matches MCP guidance behavior or the gap is explicitly recorded.

### `verify_policy_integrity`
- Applicable scenarios: `Path`, `Tier`, `Shape`
- MCP checklist:
	- [ ] Invalid policy directories or manifest sources return guidance.
	- [ ] Tier-specific behavior is explicitly explained when the failure is capability-related.
- CLI checklist:
	- [ ] The `verify-policy-integrity` command either matches MCP guidance behavior or the gap is explicitly recorded.

### `code_policy_check`
- Applicable scenarios: `Path`, `Pattern or query`, `Tier`, `Shape`
- MCP checklist:
	- [ ] Invalid paths or malformed rule requests return guidance.
	- [ ] Tier-gated compliance or report-generation requests return `upgrade_required` with clear explanation.
- CLI checklist:
	- [ ] The `code-policy-check` command either matches MCP guidance behavior or the gap is explicitly recorded.

### `get_capabilities`
- Applicable scenarios: `Tier`, `Shape`, `not_found`
- MCP checklist:
	- [ ] Invalid tier and unknown tool-name behavior is explicitly audited.
	- [ ] If Oracle remains absent, the missing guidance is documented as a gap rather than treated as acceptable behavior.
- CLI checklist:
	- [ ] The `capabilities` command either gains Oracle-equivalent guidance or the gap is explicitly recorded.
