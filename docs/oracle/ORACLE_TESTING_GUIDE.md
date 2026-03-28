# Oracle Testing Guide

> [20260311_DOCS] Testing-team guide for Oracle resilience behavior, expected outcomes, and regression strategy.

## What Oracle Does

Oracle is the corrective error-recovery layer around public tool boundaries.

Its job is not to hide failures. Its job is to turn user-correctable failures into actionable guidance so an AI agent or human user can recover on the next attempt.

At the MCP boundary, Oracle currently works by:

- intercepting correctable exceptions such as `ValidationError` and `FileNotFoundError`
- inspecting tool results that already contain an error envelope
- applying a recovery strategy such as `PathStrategy`, `SymbolStrategy`, `RenameSymbolStrategy`, `NodeIdFormatStrategy`, or `GenerateTestsStrategy`
- returning a structured error response with guidance instead of a bare opaque failure

In practice, Oracle should answer the question:

"The tool could not complete the request. Can we tell the caller what to fix next?"

## What Oracle Is Not

Oracle is not:

- a success-path feature
- a silent fallback mechanism
- a replacement for input validation
- a license bypass
- a justification for returning `internal_error` on correctable user mistakes

If the failure is user-correctable, Oracle should provide guidance.
If the failure is tier-gated, the response should explain the upgrade requirement.
If the failure is truly internal or non-correctable, the tool may still return `internal_error`.

## Expected Outcomes

Testing should treat these outcomes as correct behavior:

- `correction_needed`
  Use for misspelled symbols, malformed paths, bad node IDs, invalid selectors, and similar recoverable user-input errors.

- `upgrade_required`
  Use for explicit tier-gated requests where the next action is to move to a higher tier.

- `invalid_argument` with guidance
  Use for malformed argument shapes or invalid value ranges when the tool can explain valid input.

- `not_found` with guidance
  Acceptable for lookup-style flows if the response still tells the user what nearby valid target exists.

- `internal_error`
  Acceptable only when the test confirms the failure is not realistically correctable from the current boundary.

## What Good Oracle Guidance Looks Like

For a correctable failure, the response should:

- identify the failed input clearly
- indicate that the failure is recoverable
- provide one or more concrete next-step suggestions
- preserve machine-readable structure for agent retries

Typical response characteristics:

- `error.error_code == "correction_needed"`
- `error.error` contains a human-readable explanation
- `error.error_details` contains guidance payloads such as suggestions, hints, or alternatives

## Failure Scenario Classes to Test

Each public tool should be audited against the scenario classes that apply to it.

### 1. Path failures

Examples:

- misspelled file path
- bad project root
- malformed Windows or WSL path such as `/K:/...`
- inaccessible report path

Expected result:

- `correction_needed`
- a hint or candidate corrected path

### 2. Symbol failures

Examples:

- misspelled function name
- missing method name
- missing class name
- ambiguous selector

Expected result:

- `correction_needed`
- suggested nearby symbols with confidence or ranking metadata when available

### 3. Node ID failures

Examples:

- malformed graph node ID
- unsupported node kind
- valid-looking node ID pointing to a missing node

Expected result:

- `correction_needed` or guided `invalid_argument`
- explanation of the required node-ID format or a candidate valid node

### 4. Pattern or query failures

Examples:

- invalid glob
- invalid regex
- unsupported dependency selector
- invalid filter syntax

Expected result:

- guided `invalid_argument` or `correction_needed`
- explicit examples of valid patterns or filters

### 5. Language or framework failures

Examples:

- unsupported language
- unsupported test framework
- unsupported output format

Expected result:

- guided `invalid_argument`
- list of supported values

### 6. Tier failures

Examples:

- Enterprise-only compliance report request at Community tier
- Pro-only feature invoked at Community tier

Expected result:

- `upgrade_required`
- explanation of what capability is missing

### 7. Shape or argument failures

Examples:

- missing required parameter
- negative depth where depth must be positive
- malformed structured selector

Expected result:

- guided `invalid_argument`
- explanation of the accepted argument shape or range

### 8. Internal failures

Examples:

- parser crash
- unexpected helper failure
- external tool process failure with no actionable correction

Expected result:

- `internal_error`
- clear explanation, but not a fake correction

## Testing Principles

### Test user-correctable failures, not only happy paths

Oracle is an error-path feature. A test suite that only validates successful execution tells us almost nothing about Oracle.

### Test the public boundary, not only helper internals

Oracle exists at the public MCP tool boundary. The primary tests should call the public tool function or the CLI command, not only lower-level helper functions.

### Verify guidance quality, not just status codes

A test should not stop at `error_code == "correction_needed"`. It should also check that the response includes useful hints or suggestions.

### Do not confuse empty results with Oracle failure

Some tools are intentionally designed to return empty results rather than errors for certain lookups. Those should be documented and tested as intentional behavior rather than mislabeled Oracle failures.

### Avoid asserting implementation trivia

Tests should prefer verifying behavior over exact wording. Assert for key fields and recovery semantics, not fragile full-string matches, unless the wording itself is the contract under test.

## Required Test Layers

### 1. Strategy unit tests

Purpose:

- verify that a recovery strategy produces useful suggestions from a given error and context

Examples:

- `PathStrategy` suggesting a nearby path
- `SymbolStrategy` suggesting similar function names

Current reference:

- `tests/mcp/test_oracle_middleware.py`

### 2. Decorator and middleware tests

Purpose:

- verify that `with_oracle_resilience(...)` intercepts the right failures and preserves structured error output

Test for:

- `ValidationError` interception
- `FileNotFoundError` interception
- pass-through of non-recoverable exceptions
- envelope enhancement behavior
- contract pass-through of pre-built `ToolResponseEnvelope`

Current reference:

- `tests/mcp/test_oracle_middleware.py`

### 3. Public MCP tool regression tests

Purpose:

- verify that each public tool returns Oracle guidance for representative real failure scenarios

Test for:

- malformed paths
- misspelled symbols
- bad node IDs
- tier-gated requests
- bad frameworks or unsupported language inputs where applicable

Current references:

- `tests/mcp/test_mcp.py`
- tool-specific test modules under `tests/tools/`

### 4. CLI parity tests

Purpose:

- verify whether CLI commands provide equivalent guidance to their MCP counterparts

Important current state:

- CLI Oracle parity is broadly missing today
- tests should make that visible instead of assuming parity exists

That means CLI tests should currently do one of two things:

- prove equivalent guidance if the CLI path has been upgraded
- document the gap clearly if the CLI path still returns unenhanced failures

## Minimum Assertions Per Oracle Test

For a correctable failure, a good test should usually assert:

- the call returns an error state
- the error code is correct for the scenario
- the response includes guidance payloads or hints
- the guidance references a plausible corrected value

Example assertion pattern:

```python
assert result.error is not None
assert result.error.error_code == "correction_needed"
assert result.error.error_details is not None
assert "hint" in result.error.error_details or "suggestions" in result.error.error_details
```

For tier failures, assert:

```python
assert result.error is not None
assert result.error.error_code == "upgrade_required"
assert "Enterprise" in result.error.error or "Pro" in result.error.error
```

For truly internal failures, assert:

```python
assert result.error is not None
assert result.error.error_code == "internal_error"
```

but only after confirming the scenario is genuinely non-correctable.

## Common Testing Mistakes

### Mistake 1: Treating every failure as an Oracle failure

If a tool is designed to return zero results instead of erroring, that is a contract question, not automatically an Oracle defect.

### Mistake 2: Accepting `internal_error` for a typo or path mistake

If the user made a normal recoverable mistake, `internal_error` is usually a bug or missing Oracle plumbing.

### Mistake 3: Testing only the presence of the decorator

Decorator coverage is not enough. The actual failure path must still produce guidance.

### Mistake 4: Asserting exact suggestion ordering without reason

Suggestion ranking may evolve. Assert that the expected candidate appears, and reserve strict ordering checks for strategy tests where ranking is the contract.

### Mistake 5: Forgetting wrapper-level normalization

Some helpers return result models instead of raising exceptions. In those cases, Oracle middleware alone is not enough. Tests must cover the public wrapper behavior.

## Recommended Audit Workflow

For each public tool:

1. Identify the applicable failure scenario classes.
2. Choose at least one representative failure from each applicable class.
3. Test the public MCP tool boundary.
4. Verify the response tells the caller what to do next.
5. If a CLI command exists, test whether it matches MCP guidance.
6. If the CLI does not match, record the parity gap explicitly.

## Pass and Fail Criteria

### Pass

A scenario passes when:

- the tool responds with the right error class for the scenario
- the response contains actionable guidance for the caller
- the guidance is machine-readable enough for an AI retry or clear enough for a human retry

### Fail

A scenario fails when:

- a recoverable mistake returns a bare `internal_error`
- the response says the request failed but provides no next action
- the tool returns a malformed error envelope
- a tier-gated request does not explain the tier requirement
- MCP and CLI behavior diverge without the gap being documented

## Current Important Reality for the Team

As of this document:

- Oracle behavior is strongest at the MCP boundary
- CLI parity is not complete and should be tested as a known gap area
- path normalization is a major source of Oracle regressions for path-taking tools
- contract pass-through matters because double-wrapping envelopes can corrupt `ToolError` payloads

## Where to Look in the Codebase

- Oracle middleware: `src/code_scalpel/mcp/oracle_middleware.py`
- Envelope contract: `src/code_scalpel/mcp/contract.py`
- Public MCP tools: `src/code_scalpel/mcp/tools/`
- CLI boundary: `src/code_scalpel/cli.py`
- Oracle middleware tests: `tests/mcp/test_oracle_middleware.py`
- Public MCP Oracle regressions: `tests/mcp/test_mcp.py`
- Live coverage tracker: `docs/oracle/ORACLE_MCP_CLI_TRACKING.md`

## Testing Team Summary

Oracle should be tested as a recovery contract.

The core question is not "Did the tool fail?"

The core question is:

"When the tool failed, did we give the AI or user enough structured guidance to recover correctly on the next attempt?"