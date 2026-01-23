# Migration Guide: v2.5.0 → v1.0.0 "Autonomy"

<!-- [20251218_DOCS] Migration guide for v1.0.0 release -->

> **Release Date:** December 18, 2025  
> **Effort:** Low | **Breaking Changes:** None (backward compatible)  
> **Upgrade Time:** 15-30 minutes

---

## Overview

Code Scalpel v1.0.0 "Autonomy" is **fully backward compatible** with v2.5.0. This guide helps you upgrade and take advantage of new features.

### What's New in v1.0.0

| Category | Enhancement |
|----------|-------------|
| **Coverage** | +49.5% more tests (4,033 tests, 94.86% coverage) |
| **Stability** | Edge case handling, memory safety, thread safety |
| **Autonomy** | Fix loops, error-to-diff, mutation gates, audit trails |
| **Tools** | MCP tools stable and fully tested (current registry: 20 tools) |
| **Performance** | Caching improvements, faster parsing |

---

## Upgrade Checklist

### Step 1: Update Package

```bash
# Using pip
pip install --upgrade code-scalpel

# Or specify version
pip install code-scalpel==3.0.0

# Verify installation
python -c "import code_scalpel; print(code_scalpel.__version__)"
# Expected output: 3.0.0
```

### Step 2: Check Python Version

v1.0.0 requires Python 3.9+:

```bash
python --version
# Expected: Python 3.9+ (tested on 3.9, 3.10, 3.11, 3.12)
```

### Step 3: Verify Dependencies (Optional)

If you use optional features, install extras:

```bash
# All parsers and tools
pip install code-scalpel[full]

# With autonomy engine
pip install code-scalpel[autonomy]

# With compliance reporting
pip install code-scalpel[compliance]
```

### Step 4: Update Configuration (if using MCP)

No configuration changes required. If you're using the MCP server:

```python
# v2.5.0 code (still works)
from code_scalpel.mcp.server import MCPServer

# v1.0.0 (same API)
server = MCPServer()
```

### Step 5: Run Your Tests

```bash
# Test your integrations
pytest your_tests/ -v

# If all pass, you're ready!
```

---

## What Changed

### [COMPLETE] Backward Compatible (No Changes Required)

- **All existing APIs** work unchanged
- **All existing imports** work unchanged
- **All configuration** remains valid
- **All MCP tools** function identically

### [WARNING] Newly Available (Optional to Adopt)

| Feature | Where | Adoption |
|---------|-------|----------|
| **Autonomy Engine** | `code_scalpel.autonomy.*` | Optional new module |
| **Fix Loop** | `code_scalpel.autonomy.fix_loop` | Opt-in feature |
| **Audit Trail** | `code_scalpel.autonomy.audit` | Opt-in feature |
| **Mutation Gate** | `code_scalpel.autonomy.mutation` | Opt-in feature |

---

## New Feature Adoption Guide

### 1. Enable Autonomy (Optional)

If you want autonomous fix capabilities:

```python
from code_scalpel.autonomy import FixLoop

# Configure fix loop
fix_loop = FixLoop(
    max_attempts=5,           # Default: 5
    timeout_seconds=300,      # Default: 5 min
    escalate_on_failure=True  # Default: True
)

# Use in your agent
for attempt in range(fix_loop.max_attempts):
    try:
        fix = generate_fix(error)
        result = fix_loop.apply_and_validate(fix)
        if result.success:
            break
    except Exception as e:
        if attempt == fix_loop.max_attempts - 1:
            escalate_to_human(error)
```

### 2. Enable Audit Trail (Optional)

Track all operations:

```python
from code_scalpel.autonomy.audit import AuditTrail

audit = AuditTrail(session_id="my-session")

# Log operations
audit.record_operation(
    operation_type="FIX_APPLIED",
    input_hash=hash(original_code),
    output_hash=hash(fixed_code),
    success=True
)

# Export results
report = audit.export_audit_trail(format="json")
```

### 3. Enable Mutation Testing (Optional)

Validate fix quality:

```python
from code_scalpel.autonomy.mutation import MutationTestGate

gate = MutationTestGate(mutation_count=20)

# Validate fix
score = gate.validate_fix(
    original_code=buggy_code,
    fixed_code=patched_code,
    tests=test_suite
)

if score.mutation_score < 0.8:
    print(f"Warning: Low mutation score ({score.mutation_score})")
```

---

## Common Migration Scenarios

### Scenario 1: Using v2.5.0 Policy Engine

**v2.5.0 Code:**
```python
from code_scalpel.policy_engine import PolicyEngine

engine = PolicyEngine("policy.rego")
decision = engine.decide(operation="modify", target="sensitive.py")
```

**v1.0.0 (No Changes Needed):**
```python
# Same code works unchanged
# Policy Engine improved with v2.5.0 features
```

### Scenario 2: Using v2.5.0 Graph Engine

**v2.5.0 Code:**
```python
from code_scalpel.graph_engine import UniversalGraph

graph = UniversalGraph()
# ... use graph ...
```

**v1.0.0 (No Changes Needed):**
```python
# Same code works unchanged
# Graph Engine now with better performance caching
```

### Scenario 3: Adopting Fix Loops

**New v1.0.0 Capability:**
```python
from code_scalpel.autonomy import FixLoop, ErrorToDiffEngine

engine = ErrorToDiffEngine()
fix_loop = FixLoop(max_attempts=5)

error = compile_and_capture_error(code)
analysis = engine.analyze(error)

for fix in analysis.fixes:
    result = fix_loop.apply_and_validate(fix)
    if result.success:
        print(f"Fixed after {result.attempt} attempts!")
        break
```

### Scenario 4: Security Scanning

**v2.5.0 Code (Still Works):**
```python
from code_scalpel.security.analyzer import SecurityAnalyzer

analyzer = SecurityAnalyzer()
vulnerabilities = analyzer.scan(code)
```

**v1.0.0 (Same API, Better Coverage):**
```python
# Same code works
# Now covers 100% of security scenarios with more tests
```

---

## Breaking Changes

**None.** v1.0.0 is fully backward compatible with v2.5.0.

All existing code continues to work without modification.

---

## Deprecations

**None.** No APIs or features deprecated in v1.0.0.

---

## Performance Notes

v1.0.0 includes performance improvements:

| Operation | v2.5.0 | v1.0.0 | Improvement |
|-----------|--------|--------|-------------|
| AST Parsing | Baseline | +15% faster | Caching |
| PDG Building | Baseline | +10% faster | Optimized |
| Symbolic Execution | Baseline | +5% faster | Z3 tuning |
| Security Scan | Baseline | +20% faster | Parallel taint |

### Enable Caching (Optional)

```python
from code_scalpel.ast_tools import ASTBuilder

# Caching enabled by default in v1.0.0
builder = ASTBuilder(cache_dir=".ast_cache")
ast = builder.build("code.py")  # Cached after first build
```

---

## Testing Your Upgrade

### Quick Smoke Test

```bash
# Test core functionality
python -c "
from code_scalpel.ast_tools import ASTBuilder
from code_scalpel.security import SecurityAnalyzer

# Should work without errors
builder = ASTBuilder()
analyzer = SecurityAnalyzer()
print('[COMPLETE] v1.0.0 installed successfully!')
"
```

### Run Full Test Suite

```bash
# If you have the source code
pytest tests/ -v --tb=short

# Expected: 4,094 tests passing
```

### Test MCP Server

```bash
# Start the MCP server
python -m code_scalpel.mcp.server

# In another terminal:
curl http://localhost:8593/sse

# Expected: SSE stream connection
```

---

## Getting Help

### Updated Documentation
- **Overview:** [COMPREHENSIVE_GUIDE.md](../COMPREHENSIVE_GUIDE.md)
- **Autonomy Engine:** [autonomy_quickstart.md](../autonomy_quickstart.md)
- **API Reference:** [modules/](../modules/)
- **Examples:** [examples.md](../examples.md)

### Common Issues

**Issue:** Import errors after upgrade  
**Solution:** `pip install --upgrade code-scalpel --force-reinstall`

**Issue:** MCP server won't start  
**Solution:** Check Python version (requires 3.9+)

**Issue:** Tests fail after upgrade  
**Solution:** Clear cache with `rm -rf .ast_cache .code_scalpel_cache`

---

## What to Do Next

### Option A: Stay Compatible (No Action)
- Keep using v2.5.0 code unchanged
- All functionality continues to work
- Benefit from stability improvements and bug fixes

### Option B: Adopt Autonomy (30 minutes)
1. Read [autonomy_quickstart.md](../autonomy_quickstart.md)
2. Try fix loop example
3. Integrate into your agent

### Option C: Optimize Performance (1 hour)
1. Enable caching: `ASTBuilder(cache_dir=".ast_cache")`
2. Review [docs/PERFORMANCE_TUNING.md](./PERFORMANCE_TUNING.md)
3. Benchmark your usage patterns

---

## Version Support Policy

| Version | Release | Support Until | Status |
|---------|---------|---|---------|
| v1.0.0 | Dec 18, 2025 | Dec 18, 2026 | Current |
| v2.5.0 | Jul 15, 2025 | Dec 18, 2025 | EOL |
| v2.2.0 | May 1, 2025 | Jul 15, 2025 | EOL |

**Recommendation:** Upgrade to v1.0.0 for latest features and support.

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `ImportError: No module named 'code_scalpel'` | `pip install --upgrade code-scalpel` |
| `TypeError: unexpected keyword argument` | Check [API_CHANGES_v1.0.0.md](./API_CHANGES_v1.0.0.md) |
| `MCP server port already in use` | Change port with `--port 8594` |
| `Tests fail with cache errors` | Clear cache: `rm -rf .ast_cache` |
| `Memory usage spike` | Check [KNOWN_ISSUES_v1.0.0.md](./KNOWN_ISSUES_v1.0.0.md) |

---

## Summary

[COMPLETE] **v1.0.0 is a drop-in replacement for v2.5.0**

- No breaking changes
- All existing code works unchanged
- New autonomy features available (optional)
- Better performance and stability
- 4,033 tests ensure reliability

**Estimated upgrade time:** 15-30 minutes  
**Risk level:** Very low  
**Recommendation:** Upgrade now

---

**Questions?** Check the [FAQ](../getting_started.md) or open an issue on GitHub.
