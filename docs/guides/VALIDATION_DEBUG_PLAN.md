# MCP Server Refactor Validation Debug Plan

**Created**: 2026-01-22
**Purpose**: Investigation guide for issues discovered during server.py refactoring validation

---

## Issue Summary

| Issue ID | Category | Severity | Status |
|----------|----------|----------|--------|
| DBG-001 | Contract | Medium | Open |
| DBG-002 | Tier System | High | Open |
| DBG-003 | Performance | Medium | ✅ Resolved |
| DBG-004 | Test Fixtures | Medium | ✅ Resolved |

---

## DBG-001: `tool_id` None in Response Envelope

### Problem
When using the "minimal" response profile, `tool_id` is `None` in the `ToolResponseEnvelope`. Contract tests expect `tool_id` to always be present.

### Root Cause
In `response_config.json`, all tool overrides specify `"profile": "minimal"`, which has an empty `envelope.include` array. The `make_envelope()` function in `contract.py` only includes `tool_id` if it's in the configured envelope fields.

**File**: [contract.py:345](src/code_scalpel/mcp/contract.py#L345)
```python
tool_id=tool_id if "tool_id" in envelope_fields else None,
```

### Investigation Steps

1. **Review response_config.json structure**
   ```bash
   cat .code-scalpel/response_config.json | jq '.profiles.minimal.envelope'
   ```

2. **Check contract test expectations**
   ```bash
   grep -n "tool_id" tests/mcp/test_mcp_all_tools_contract.py
   ```

3. **Verify envelope field selection logic**
   ```bash
   grep -n "get_envelope_fields" src/code_scalpel/mcp/response_config.py
   ```

### Proposed Fix

Add a global `include_tool_id` toggle to `response_config.json`:

```json
{
  "global": {
    "profile": "debug",
    "include_tool_id": true,  // <-- New toggle
    "exclude_empty_arrays": true,
    ...
  }
}
```

Modify `contract.py::make_envelope()` to always include `tool_id` when this toggle is true, regardless of profile.

### Files to Modify
- [response_config.json](.code-scalpel/response_config.json) - Add toggle
- [response_config.py](src/code_scalpel/mcp/response_config.py) - Read toggle
- [contract.py](src/code_scalpel/mcp/contract.py) - Honor toggle in `make_envelope()`

### Acceptance Criteria
- [ ] `include_tool_id: true` causes `tool_id` to always be present
- [ ] `include_tool_id: false` (or absent) uses profile-based behavior
- [ ] Contract tests pass when toggle is enabled
- [ ] Backwards compatible with existing configs

---

## DBG-002: Tier Not Applied Correctly in Tests

### Problem
Tests expecting "pro" or "enterprise" tier are receiving "community". This affects 12 tests in `test_tier_boundary_limits.py`.

### Symptoms
```
AssertionError: Expected tier pro, got community
assert 'community' == 'pro'
```

### Root Cause Hypotheses

1. **License file not being discovered** - Test environment may not have valid test licenses in expected locations
2. **License validation disabled** - Environment variable may be disabling validation
3. **Subprocess environment** - License env vars may not be passed to server subprocess
4. **License path mismatch** - Test generates license but server looks elsewhere

### Investigation Steps

1. **Check license discovery in tests**
   ```bash
   grep -rn "CODE_SCALPEL_LICENSE" tests/mcp/test_tier_boundary_limits.py | head -20
   ```

2. **Verify test license generation**
   ```bash
   grep -rn "_with_hs256_test_license_env\|generate_license" tests/mcp/ | head -20
   ```

3. **Check server tier detection**
   ```bash
   grep -n "_get_current_tier\|compute_effective_tier" src/code_scalpel/mcp/server.py | head -20
   ```

4. **Trace license validation flow**
   ```python
   # Add debug logging to server.py
   import logging
   logging.basicConfig(level=logging.DEBUG)
   # Run failing test and check stderr
   ```

5. **Verify env var propagation to subprocess**
   ```bash
   grep -n "env=" tests/mcp/test_tier_boundary_limits.py | head -10
   ```

### Key Files to Examine
- [test_tier_boundary_limits.py](tests/mcp/test_tier_boundary_limits.py) - Test setup and license injection
- [server.py](src/code_scalpel/mcp/server.py) - `_get_current_tier()` function
- [authorization.py](src/code_scalpel/licensing/authorization.py) - `compute_effective_tier_for_startup()`
- [jwt_validator.py](src/code_scalpel/licensing/jwt_validator.py) - License validation logic

### Debug Commands
```bash
# Run single failing test with verbose output
pytest tests/mcp/test_tier_boundary_limits.py::test_symbolic_execute_pro_tier_enables_list_dict_types -v -s

# Check what tier server reports at startup (look for "Tier:" in stderr)
python -m code_scalpel.mcp.server --transport stdio --root /tmp 2>&1 | head -5
```

### Acceptance Criteria
- [ ] Identify why licenses aren't being picked up
- [ ] Fix license discovery/injection in test setup
- [ ] All 12 failing tier tests pass
- [ ] Tier correctly reported in server startup message

---

## DBG-003: Tool Performance / Timeouts ✅ RESOLVED

### Problem
`test_mcp_stdio_invokes_all_tools` times out after 90 seconds. Some tools are running slower than expected.

### Root Cause (Identified 2026-01-22)
The `update_symbol` helper was calling `os.sync()` after saving files. The previous fix attempted
to skip `os.sync()` in test environments by checking `"pytest" not in sys.modules`, but the MCP
server runs as a subprocess where pytest is NOT loaded. This caused `os.sync()` to be called,
which can hang indefinitely in various environments (Docker, WSL, network filesystems, CI).

### Solution
Removed `os.sync()` entirely from the `update_symbol` helper. The `patcher.save()` already does
proper file flush operations, and `os.sync()` is not necessary for correctness in this context.

**File Modified**: [extraction_helpers.py](src/code_scalpel/mcp/helpers/extraction_helpers.py)

```python
# Before (problematic):
if hasattr(os_module, "sync") and "pytest" not in sys.modules:
    try:
        os_module.sync()  # <-- Can hang in subprocess
    except Exception:
        pass

# After (fixed):
# [20260122_BUGFIX] Remove os.sync() entirely - it can hang indefinitely
# in various environments (Docker, WSL, network filesystems, CI).
# The patcher.save() already does proper file flush, and os.sync() is
# not necessary for correctness.
```

### Verification
```bash
# Test now completes in ~7 seconds (was timing out at 90+ seconds)
pytest tests/mcp/test_mcp_tools_stdio_invocation.py::test_mcp_stdio_invokes_all_tools -v
# PASSED [100%] in 7.02s
```

### Acceptance Criteria
- [x] Identify the slow tool(s) - `update_symbol` was the culprit
- [x] Profile and document bottleneck - `os.sync()` hanging in subprocess
- [x] Either optimize tool or adjust test timeout - Removed `os.sync()`
- [x] Test completes within 60 seconds - Now completes in ~7 seconds

---

## DBG-004: Test Fixture Errors in test_stage5c_tool_validation.py ✅ RESOLVED

### Problem
21 errors in `test_stage5c_tool_validation.py` - all tests in this file fail with fixture/setup errors.

### Root Cause (Identified 2026-01-22)
Two issues were found:

1. **Tier Cache Not Being Cleared**: The session-scoped `set_default_license_path` fixture sets
   `CODE_SCALPEL_LICENSE_PATH` to an enterprise license. When the test's `verify_tier` fixture
   tried to set `CODE_SCALPEL_TIER=community`, the cached enterprise tier from the license
   file detection took precedence.

2. **Stale Import Paths**: 5 tests use convenience functions in `__init__.py` that import from
   `code_scalpel.mcp.archive.server` (the archived monolithic server), which no longer exists.

### Solution Applied
Added tier cache clearing mechanism:
- Added `clear_license_cache()` to [jwt_validator.py](src/code_scalpel/licensing/jwt_validator.py)
- Added `clear_config_cache()` to [config_loader.py](src/code_scalpel/licensing/config_loader.py)
- Added `clear_tier_cache()` to [tier_detector.py](src/code_scalpel/licensing/tier_detector.py)
- Updated test fixture to clear caches and delete `CODE_SCALPEL_LICENSE_PATH` env var

Fixed stale imports in `__init__.py` convenience wrappers:
- Changed all imports from `code_scalpel.mcp.archive.server` to `code_scalpel.mcp.server`
- Updated `extract_code`, `security_scan`, `symbolic_execute`, `generate_unit_tests`, and `simulate_refactor` functions

### Current Status
- **21 tests pass** (tier isolation and imports now work correctly)

### Acceptance Criteria
- [x] Identify fixture/import error
- [x] Fix test setup (tier isolation)
- [x] All 21 tests run (pass or fail properly, not error) - 21/21 pass

---

## Quick Reference: Debug Commands

```bash
# Run single test with maximum verbosity
pytest tests/mcp/TEST_FILE.py::test_name -v -s --tb=long

# Run with coverage to see which code paths execute
pytest tests/mcp/ --cov=code_scalpel.mcp --cov-report=html

# Check for import issues
python -c "from code_scalpel.mcp.server import mcp; print('OK')"

# Verify tool registration
python -c "
from code_scalpel.mcp.tools import register_tools
from code_scalpel.mcp.protocol import mcp
register_tools()
print(f'Tools: {len(mcp._tool_manager._tools)}')"

# Test license validation
python -c "
from code_scalpel.mcp.server import _get_current_tier
print(f'Tier: {_get_current_tier()}')"

# Profile tool execution time
python -c "
import asyncio
import time
from code_scalpel.mcp.tools.analyze import analyze_code
async def test():
    start = time.time()
    result = await analyze_code('def foo(): pass', 'python')
    print(f'Time: {time.time() - start:.2f}s')
asyncio.run(test())"
```

---

## Assignment Matrix

| Issue | Suggested Assignee | Priority | Est. Time |
|-------|-------------------|----------|-----------|
| DBG-001 | Backend Dev | P2 | 2-4 hours |
| DBG-002 | Test/License Dev | P1 | 4-8 hours |
| DBG-003 | Performance Dev | P2 | 4-8 hours |
| DBG-004 | Test Dev | P3 | 1-2 hours |

---

## Related Files

### Configuration
- [.code-scalpel/response_config.json](.code-scalpel/response_config.json)
- [pyproject.toml](pyproject.toml)

### Core Implementation
- [src/code_scalpel/mcp/server.py](src/code_scalpel/mcp/server.py)
- [src/code_scalpel/mcp/contract.py](src/code_scalpel/mcp/contract.py)
- [src/code_scalpel/mcp/response_config.py](src/code_scalpel/mcp/response_config.py)
- [src/code_scalpel/mcp/protocol.py](src/code_scalpel/mcp/protocol.py)

### Tests
- [tests/mcp/test_mcp_all_tools_contract.py](tests/mcp/test_mcp_all_tools_contract.py)
- [tests/mcp/test_tier_boundary_limits.py](tests/mcp/test_tier_boundary_limits.py)
- [tests/mcp/test_mcp_tools_stdio_invocation.py](tests/mcp/test_mcp_tools_stdio_invocation.py)
- [tests/mcp/test_stage5c_tool_validation.py](tests/mcp/test_stage5c_tool_validation.py)

### Previous Documentation
- [src/code_scalpel/mcp/REFACTOR_CHECKLIST.md](src/code_scalpel/mcp/REFACTOR_CHECKLIST.md)
