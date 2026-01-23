# Governance Test Coverage - Quick Reference Card

**Print this page for quick reference during implementation**

---

## Test Status Dashboard

```
┌─────────────────────────────────────────────────────────────────┐
│                   GOVERNANCE TEST COVERAGE                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Component              Tests    Coverage    Status   Action     │
│  ─────────────────────────────────────────────────────────────  │
│  Policy Engine            46+      95%+       ✅     Minor tweaks│
│  Semantic Analysis        25+      95%+       ✅     Add poly   │
│  Governance Config        32+      98%+       ✅     ✓ Done      │
│  Autonomy Integration     17+      90%+       ✅     Add errors  │
│  ┌─ UNIFIED GOVERNANCE     0        0%        🔴     CRITICAL   │
│  │  ├─ Evaluation         [needs: 15]                            │
│  │  ├─ Role-Based         [needs: 8]                             │
│  │  ├─ Semantic Integ.    [needs: 8]                             │
│  │  ├─ Compliance Report  [needs: 10]                            │
│  │  ├─ Policy Override    [needs: 10]                            │
│  │  ├─ Audit Trail        [needs: 10]                            │
│  │  └─ Error Handling     [needs: 8]                             │
│  ├─ Integration Tests      [needs: 15]                           │
│  └─ Configuration          [needs: 5]                            │
│  ───────────────────────────────────────────────────────────────│
│  TOTAL (Current)          ~120     ~85%       🟡     Phase 1    │
│  TOTAL (Target)           ~200     95%+       📈     1 month    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Files to Create/Modify

### Create (New Files)

```
tests/
├── test_unified_governance.py           ← NEW (250+ lines, 50+ tests)
├── test_governance_integration.py       ← NEW (150+ lines, 15+ tests)
└── fixtures/
    └── governance_fixtures.py           ← NEW (shared fixtures)
```

### Modify (Existing Files)

```
tests/
├── conftest.py                          ← Add governance fixtures
└── test_autonomy_engine_integration.py  ← Minor: add error tests
```

---

## The 50+ Tests at a Glance

### Phase 1: Unified Governance Tests

#### 1. Evaluation (15 tests)
```
✓ Multiple violation aggregation
✓ Violation severity ordering
✓ Custom operation types
✓ Language-specific semantic analysis
✓ Metadata generation
✓ Remediation suggestions
✓ Config override respect
✓ Partial availability handling
✓ Fail-closed on errors
```

#### 2. Roles (8 tests)
```
✓ Developer limits (500 lines, 10 files)
✓ Reviewer limits (1500 lines, 30 files)
✓ Architect unrestricted
✓ Inheritance & custom roles
✓ Critical path restrictions
✓ Override enforcement
✓ Unknown role handling
✓ Role change stability
```

#### 3. Semantic (8 tests)
```
✓ SQL injection detection
✓ XSS detection
✓ Command injection detection
✓ Path traversal detection
✓ Language-specific patterns
✓ Violation inclusion in decision
✓ Optional analysis by config
✓ Error handling
```

#### 4. Compliance Reporting (10 tests)
```
✓ Report generation
✓ Violation inclusion
✓ Decision history
✓ Metric calculations
✓ Violation distribution
✓ JSON export
✓ CSV export
✓ Time range filtering
✓ Remediation summary
✓ Compliance scoring
```

#### 5. Policy Overrides (10 tests)
```
✓ Justification requirement
✓ With justification
✓ Audit entry creation
✓ Max overrides per day
✓ Critical path blocking
✓ Approval workflows
✓ Time expiration
✓ Scope limitations
✓ Metrics in reports
```

#### 6. Audit Trail (10 tests)
```
✓ All decisions logged
✓ Immutability checks
✓ Complete metadata
✓ Search functionality
✓ Retention enforcement
✓ Export integrity
✓ Error conditions
✓ Chain of custody
✓ Override tracking
✓ Tamper detection
```

#### 7. Error Handling (8 tests)
```
✓ Policy engine errors
✓ Budget calculation errors
✓ Semantic analysis errors
✓ Config loading errors
✓ Partial failures
✓ Timeout handling
✓ Out of memory handling
✓ Concurrent access safety
```

### Phase 2: Integration Tests

#### 8. Workflows (10 tests)
```
✓ Developer safe change
✓ Developer risky change
✓ Budget exceeded escalation
✓ Critical path approval
✓ Multiple violations
✓ Compliance report
✓ Policy update impact
✓ Role change impact
✓ Violation remediation
✓ Escalation path
```

#### 9. Policy Priority (5 tests)
```
✓ Deny overrides allow
✓ Multiple denies
✓ Custom priority ordering
✓ Exception lists
✓ Temporary override expiration
```

#### 10. Configuration (5 tests)
```
✓ Validation on load
✓ Default fallback
✓ Env override validation
✓ Hot reload
✓ Mutual exclusivity
```

---

## Key Test Assertions (Copy-Paste Ready)

### Violation Assertion
```python
assert not decision.allowed
assert any(v.source == ViolationSource.POLICY 
           for v in decision.violations)
```

### Role Assertion
```python
assert governance.get_role_limits("developer").max_lines == 500
assert governance.get_role_limits("architect").max_lines is None
```

### Audit Assertion
```python
entries = governance.get_audit_log()
assert len(entries) > 0
assert entries[-1].decision.allowed == False
```

### Severity Ordering
```python
violations = decision.violations
severities = [v.severity for v in violations]
assert severities == sorted(severities, 
    key=lambda x: {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}[x])
```

---

## Test Execution Quick Commands

```bash
# Run all governance tests
pytest tests/test_unified_governance.py \
        tests/test_governance_integration.py -v

# Run specific test class
pytest tests/test_unified_governance.py::TestUnifiedGovernanceEvaluation -v

# Run with coverage
pytest tests/test_unified_governance.py \
        --cov=src/code_scalpel/governance \
        --cov-report=term-missing

# Run until first failure (debug mode)
pytest tests/test_unified_governance.py -x -v

# Run with detailed output
pytest tests/test_unified_governance.py -vv --tb=long

# Run specific test function
pytest tests/test_unified_governance.py::TestUnifiedGovernanceEvaluation::test_evaluate_policy_violation_only -v

# Parallel execution (5 workers)
pytest tests/test_unified_governance.py -n 5

# Generate HTML report
pytest tests/test_unified_governance.py \
        --html=report.html --self-contained-html
```

---

## Common Fixtures

```python
# In conftest.py or test file

@pytest.fixture
def governance():
    """Minimal governance instance."""
    return UnifiedGovernance(temp_dir)

@pytest.fixture
def operation_safe():
    """Safe operation."""
    return Operation(type="code_edit", code="x = 1", language="python")

@pytest.fixture
def operation_sql_injection():
    """Code with SQL injection."""
    return Operation(
        type="code_edit",
        code="cursor.execute(f'SELECT * FROM users WHERE id={uid}')",
        language="python"
    )

@pytest.fixture
def operation_large():
    """Operation exceeding line budget."""
    return Operation(
        type="code_edit",
        code="x = 1\n" * 600,
        language="python"
    )

@pytest.fixture
def operation_critical_path():
    """Operation on critical path."""
    return Operation(
        type="code_edit",
        code="x = 1",
        language="python",
        file_path="src/security/auth.py"
    )
```

---

## Error Messages to Expect

### POLICY VIOLATIONS
```
"Raw SQL detected without parameterized queries"
"Tainted input used in SQL context"
"Unescaped output in XSS context"
```

### BUDGET VIOLATIONS
```
"Operation exceeds max_lines_per_change (600 > 500)"
"Operation exceeds max_files_per_change (15 > 10)"
"Critical path modification blocked"
```

### SEMANTIC VIOLATIONS
```
"SQL injection detected: string concatenation"
"XSS vulnerability: innerHTML assignment"
"Command injection: os.system() with user input"
"Path traversal: user-controlled file path"
```

### CONFIG ERRORS
```
"Policy file not found"
"Invalid YAML syntax"
"OPA CLI not found - policy engine unavailable"
"Configuration validation failed"
```

---

## Coverage Checklist

### Before Committing Code

- [ ] All tests passing: `pytest --tb=short`
- [ ] Coverage >= 95%: `pytest --cov=src/code_scalpel/governance`
- [ ] No warnings: `pytest -W error::Warning`
- [ ] No lint errors: `ruff check tests/`
- [ ] Code formatted: `black tests/`
- [ ] Type hints present: `pyright tests/`
- [ ] Docstrings complete
- [ ] Comments explain "why", not "what"

### Before Merging PR

- [ ] All tests passing on CI
- [ ] Coverage report reviewed
- [ ] Edge cases covered
- [ ] Error paths tested
- [ ] Performance acceptable (<100ms/test)
- [ ] No flaky tests (passed 5 consecutive runs)
- [ ] Documentation updated
- [ ] Changelog entry added

---

## Key Files Reference

### Source Code
```
src/code_scalpel/
├── governance/
│   └── unified_governance.py          ← Core system (657 lines)
├── policy_engine/
│   ├── policy_engine.py               ← OPA/Rego integration (614 lines)
│   ├── semantic_analyzer.py           ← Pattern detection
│   ├── audit_log.py                   ← Audit logging
│   └── crypto_verify.py               ← Signature verification
├── policy/                            ← Change budgeting system
├── config/
│   └── governance_config.py           ← Configuration loading
└── autonomy/                          ← Autonomy constraints
```

### Test Files
```
tests/
├── test_policy_engine.py              ← 46+ tests, well-covered
├── test_governance_config.py          ← 16+ tests, complete
├── test_governance_config_profiles.py ← 6+ tests, complete
├── test_autonomy_engine_integration.py← 17+ tests, good
├── test_unified_governance.py         ← NEW, 50+ tests
├── test_governance_integration.py     ← NEW, 15+ tests
└── fixtures/
    └── governance_fixtures.py         ← NEW, shared fixtures
```

### Documentation
```
docs/
├── POLICY_GOVERNANCE_TEST_COVERAGE.md          ← Full analysis
├── GOVERNANCE_TEST_COVERAGE_SUMMARY.md         ← Executive summary
├── GOVERNANCE_TEST_IMPLEMENTATION_CHECKLIST.md ← Implementation guide
└── [other docs]
```

---

## Effort Estimate

```
Task                      Hours   Day   Status
─────────────────────────────────────────────
Setup Infrastructure        8     Day 1   👈 START HERE
Evaluation Tests           12     Day 1-2
Roles & Overrides          18     Day 2-3
Compliance & Audit         22     Day 3-4
Error Handling             10     Day 4
Integration Tests          12     Day 5
Configuration Tests         6     Day 5
Documentation & Polish      4     Day 6
───────────────────────────────────────────
TOTAL                      92    6 days  (aggressive: 60-80)
```

---

## Metrics to Track

```
Metric                  Current    Target    Status
────────────────────────────────────────────────
Test Count               ~120       ~200      🟡 Phase 1
Coverage %               ~85%       95%+      🟡 Phase 1
Policy Engine           95%        98%+       ✅ Close
Semantic Analysis       95%        98%+       ✅ Close
Unified Governance       0%        95%+       🔴 START
Tests passing           ~100%      100%       ✅ Goal
Flaky tests              0         0         ✅ Goal
Avg test runtime        ~50ms      <100ms    ✅ Goal
```

---

## Critical Path (Must Do First)

1. **Day 1-2:** Evaluation tests (15 tests, covers basic functionality)
2. **Day 2-3:** Roles + Overrides (18 tests, covers access control)
3. **Day 3-4:** Audit + Error handling (28 tests, covers logging & safety)
4. **Day 4-5:** Integration tests (15 tests, end-to-end scenarios)
5. **Day 5-6:** Polish, docs, metrics

---

## Common Pitfalls to Avoid

❌ **Don't:**
- Test implementation details, only behavior
- Mock too much (mocking hides real bugs)
- Skip error path testing ("it should never happen")
- Leave TODOs in test code (finish the test)
- Commit commented-out test code
- Use sleep() for synchronization (use events/locks)

✅ **Do:**
- Test the public API contracts
- Mock external dependencies only (OPA, files)
- Test error conditions explicitly
- Write self-documenting test names
- Use descriptive assertion messages
- Run tests multiple times for flakiness

---

## Resources

- **Full Analysis:** [POLICY_GOVERNANCE_TEST_COVERAGE.md](POLICY_GOVERNANCE_TEST_COVERAGE.md)
- **Implementation Guide:** [GOVERNANCE_TEST_IMPLEMENTATION_CHECKLIST.md](GOVERNANCE_TEST_IMPLEMENTATION_CHECKLIST.md)
- **Executive Summary:** [GOVERNANCE_TEST_COVERAGE_SUMMARY.md](GOVERNANCE_TEST_COVERAGE_SUMMARY.md)
- **Source Code:** [src/code_scalpel/governance/unified_governance.py](../src/code_scalpel/governance/unified_governance.py)
- **Existing Tests:** [tests/test_policy_engine.py](../tests/test_policy_engine.py)

---

**Print & Keep by Your Desk! 📋**

Last Updated: December 2025
