# MCP Tools Complete Test Coverage Strategy

**Goal**: Ensure all 20 MCP tools have complete, tier-aware test coverage  
**Status**: Assessments in progress (2/20 complete)  
**Timeline**: 8-10 weeks to complete all assessments + implementations  

---

## All 20 MCP Tools - Assessment Status

### Tier 1: Analysis Tools (6 tools)

| Tool | Tests Now | Est. Needed | Status | Priority | Notes |
|------|-----------|------------|--------|----------|-------|
| `analyze_code` | ? | ? | ⏳ Pending | HIGH | Core tool, all langs |
| `extract_code` | ? | ? | ⏳ Pending | HIGH | Multi-lang extraction |
| `security_scan` | ? | ? | ⏳ Pending | CRITICAL | Taint analysis |
| `unified_sink_detect` | ? | ? | ⏳ Pending | CRITICAL | Polyglot sinks |
| `cross_file_security_scan` | ? | ? | ⏳ Pending | CRITICAL | Multi-file taint |
| `symbolic_execute` | ? | ? | ⏳ Pending | HIGH | Z3 solver |

### Tier 2: Modification Tools (2 tools)

| Tool | Tests Now | Est. Needed | Status | Priority | Notes |
|------|-----------|------------|--------|----------|-------|
| `update_symbol` | ? | ? | ⏳ Pending | HIGH | Safe refactoring |
| `simulate_refactor` | ? | ? | ⏳ Pending | HIGH | Behavior verification |

### Tier 3: Code Generation Tools (2 tools)

| Tool | Tests Now | Est. Needed | Status | Priority | Notes |
|------|-----------|------------|--------|----------|-------|
| `generate_unit_tests` | ? | ? | ⏳ Pending | HIGH | Pytest generation |
| `crawl_project` | ? | ? | ⏳ Pending | MEDIUM | Project overview |

### Tier 4: Graph & Reference Tools (6 tools)

| Tool | Tests Now | Est. Needed | Status | Priority | Notes |
|------|-----------|------------|--------|----------|-------|
| `get_symbol_references` | 11 | 17 | 🟡 Actionable | HIGH | **Assessed Jan 3** |
| `get_cross_file_dependencies` | 9 | 46 | ⏳ Pending | CRITICAL | Complex graphs |
| `get_call_graph` | ? | ? | ⏳ Pending | HIGH | Call flow analysis |
| `get_graph_neighborhood` | ? | ? | ⏳ Pending | HIGH | K-hop subgraphs |
| `get_project_map` | 43 | 52 | ⏳ Pending | CRITICAL | Project structure |
| `get_file_context` | ? | ? | ⏳ Pending | MEDIUM | File overview |

### Tier 5: Governance & Validation Tools (4 tools)

| Tool | Tests Now | Est. Needed | Status | Priority | Notes |
|------|-----------|------------|--------|----------|-------|
| `scan_dependencies` | 27 | 22-24 | 🔴 Blocking | CRITICAL | **Assessed Jan 3** |
| `code_policy_check` | 0 | 54 | 🔴 Blocking | CRITICAL | Policy enforcement |
| `validate_paths` | ? | ? | ⏳ Pending | MEDIUM | Docker paths |
| `verify_policy_integrity` | ? | ? | ⏳ Pending | MEDIUM | Crypto verification |
| `type_evaporation_scan` | ? | ? | ⏳ Pending | HIGH | TypeScript/Python |

---

## Release Gate Criteria

### For v3.1.0 (Target: Jan 26, 2026)

**MUST COMPLETE**:
- ✅ Tier enforcement tests for 5 CRITICAL tools
- ✅ Phase 1 implementations (2-3 hours each)
- ✅ Community tier limits verified

**SHOULD COMPLETE**:
- ⏳ All 20 tools assessed (identify gaps)
- ⏳ Test structure created for all tools

**CAN DEFER**:
- ⏳ Pro tier features (Phase 2)
- ⏳ Enterprise features (Phase 3)
- ⏳ Edge case coverage (Phase 4)

---

## Testing Strategy By Tool Type

### Analysis Tools (Security-Critical)
**Approach**: High rigor, taint-based testing
- **Examples**: security_scan, unified_sink_detect, cross_file_security_scan
- **Test Pattern**:
  - Tier enforcement (3-4 tests)
  - Source-sink detection (5-8 tests)
  - Cross-file taint (4-6 tests)
  - FP/FN validation (3-5 tests)
  - Polyglot support (2-3 tests per language)
- **Est. per tool**: 20-30 tests, 8-12 hours

### Graph & Reference Tools (Complexity-Heavy)
**Approach**: Performance + correctness verification
- **Examples**: get_cross_file_dependencies, get_project_map, get_call_graph
- **Test Pattern**:
  - Tier enforcement (3-4 tests)
  - Graph construction (8-10 tests)
  - Query correctness (5-8 tests)
  - Performance at scale (3-5 tests)
  - Edge cases (4-6 tests)
- **Est. per tool**: 25-35 tests, 10-15 hours

### Modification Tools (Safety-Critical)
**Approach**: Behavior preservation, atomic changes
- **Examples**: update_symbol, simulate_refactor
- **Test Pattern**:
  - Tier enforcement (2-3 tests)
  - Syntax validation (3-4 tests)
  - Backup creation (2-3 tests)
  - Behavior preservation (5-8 tests)
  - Rollback capability (2-3 tests)
- **Est. per tool**: 15-22 tests, 7-10 hours

### Governance Tools (Policy-Heavy)
**Approach**: Policy compliance, audit trail
- **Examples**: code_policy_check, scan_dependencies, verify_policy_integrity
- **Test Pattern**:
  - Tier enforcement (3-4 tests)
  - Policy parsing (4-6 tests)
  - Policy enforcement (6-8 tests)
  - License handling (2-3 tests)
  - Audit logging (2-3 tests)
- **Est. per tool**: 20-30 tests, 8-12 hours

---

## Estimated Timeline

### Week 1 (Jan 6-12) - Critical Assessments
- [ ] Assess code_policy_check (14 hours assess + implement)
- [ ] Assess security_scan (12 hours assess + implement)
- [ ] Start get_symbol_references Phase 1 implementation

**Parallel work**: Core team implements tier tests for scan_dependencies Phase 1

### Week 2 (Jan 13-19) - Blocking Tool Assessment
- [ ] Assess get_cross_file_dependencies (9 hours assess)
- [ ] Assess get_project_map (12 hours assess)
- [ ] Complete scan_dependencies Phase 1 tests

**Parallel work**: Testing team creates test structure for 18+ tools

### Week 3 (Jan 20-26) - Remaining Assessments
- [ ] Assess remaining 13 tools (6 hours each = 78 hours)
- [ ] Categorize by risk level
- [ ] Identify must-fix vs. can-defer

**Parallel work**: Begin Phase 2 implementations on highest-risk tools

### Week 4+ (Jan 27+) - Implementation
- [ ] Implement Phase 1 tests for all tools (Est. 50-60 hours)
- [ ] Verify tier enforcement working
- [ ] Release v3.1.0

---

## Risk Assessment

### CRITICAL RISKS 🔴

1. **Tier Enforcement Broken**
   - Impact: Customers on Community tier can access Pro/Enterprise features
   - Probability: HIGH (0 tests = 100% risk)
   - Mitigation: Phase 1 tests (2-3h per tool)

2. **Security Tools Not Auditable**
   - Impact: Cannot prove vulnerabilities detected correctly
   - Probability: MEDIUM (if security_scan untested)
   - Mitigation: Taint flow testing + FP/FN validation

3. **Release Delay**
   - Impact: v3.1.0 delayed past Jan 26 target
   - Probability: MEDIUM (if all 5 critical tools take longer)
   - Mitigation: Parallelize Phase 1 across team

### HIGH RISKS 🟡

4. **Incomplete Test Coverage**
   - Impact: Edge cases cause production bugs
   - Probability: MEDIUM (always risk with new tests)
   - Mitigation: Community tier always tested, Pro/Ent can defer

5. **Tool Interdependencies**
   - Impact: Fixing one tool breaks another
   - Probability: LOW (tools are mostly independent)
   - Mitigation: Integration tests in Phase 2

---

## Success Criteria

### For v3.1.0 Release ✅
- ✅ All 5 CRITICAL tools have Phase 1 tests
- ✅ Tier enforcement verified working
- ✅ No regression in existing tests
- ✅ All 20 tools assessed (gap list created)

### For v3.2.0 Release (Later)
- ✅ Phase 2 tests for all tools (Pro features)
- ✅ Phase 3 tests for governance tools (Enterprise)
- ✅ Performance validation at scale
- ✅ End-to-end integration tests

### For v4.0 Release (Future)
- ✅ 100% test coverage across all tools
- ✅ Polyglot language support validated
- ✅ Enterprise feature completeness proven
- ✅ Security audit trail complete

---

## Resource Allocation

**Recommended Team Structure**:

| Role | Task | Hours/Week | Tools |
|------|------|-----------|-------|
| **Architect** | Assessment methodology, review | 4 | All 20 |
| **Sr. Engineer** | Critical assessments (security, policy) | 8 | 5 critical |
| **Engineers (2)** | Phase 1 implementation (parallel) | 16 total | All 20 |
| **QA** | Test verification, edge cases | 8 | All tests |
| **Automation** | CI integration, test running | 4 | Infrastructure |

**Total**: ~40 hours/week, ~8-10 weeks to completion

---

## Key Metrics to Track

```
Weekly Progress (as of Jan 3, 2026):
┌─────────────────────────────────────────┐
│ Tools Assessed:        2/20 (10%)       │
│ Tests Identified:      38 existing       │
│ Tests Needed:          ~500 estimated    │
│ Total Hours Est:       ~150-180 hours    │
│ Blocking Tests Due:    Jan 13 (2 weeks) │
└─────────────────────────────────────────┘

Phase Completion:
Phase 1 (Tier Tests):    [████░░░░░░░░░░░░░░░]  20%
Phase 2 (Pro Feats):     [░░░░░░░░░░░░░░░░░░░░]   0%
Phase 3 (Enterprise):    [░░░░░░░░░░░░░░░░░░░░]   0%
Phase 4 (Edge Cases):    [░░░░░░░░░░░░░░░░░░░░]   0%
```

---

## Next Steps

1. ✅ **Complete scan_dependencies assessment** (THIS DOCUMENT)
2. ⏳ **Assess code_policy_check** - Start Jan 6 (1 week)
3. ⏳ **Implement scan_dependencies Phase 1** - Start Jan 6 (parallel)
4. ⏳ **Create test structure for all 20 tools** - Start Jan 13
5. ⏳ **Assess remaining 17 tools** - Complete by Jan 26
6. ⏳ **Begin Phase 2 implementations** - Start Feb 2

