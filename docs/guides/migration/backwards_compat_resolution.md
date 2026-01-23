## Backward Compatibility Stub Cleanup Checklist

### Phase 1: Core __init__.py Updates (MUST DO FIRST)
- [ ] Update __init__.py line 76: `taint_tracker` relative import → `code_scalpel.security.analyzers.taint_tracker`
- [ ] Update __init__.py line 94: `security_analyzer` relative import → `code_scalpel.security.analyzers.security_analyzer`
- [ ] Update __init__.py line 105: `unified_sink_detector` relative import → `code_scalpel.security.analyzers.unified_sink_detector`
- [ ] Update __init__.py line 115: `schema_drift_detector` relative import → `code_scalpel.integrations.protocol_analyzers.schema.drift_detector`
- [ ] Update __init__.py line 127: `grpc_contract_analyzer` relative import → `code_scalpel.integrations.protocol_analyzers.grpc.contract_analyzer`
- [ ] Update __init__.py line 141: `graphql_schema_tracker` relative import → `code_scalpel.integrations.protocol_analyzers.graphql.schema_tracker`
- [ ] Update __init__.py line 158: `kafka_taint_tracker` relative import → `code_scalpel.integrations.protocol_analyzers.kafka.taint_tracker`
- [ ] Update __init__.py line 174: `frontend_input_tracker` relative import → `code_scalpel.integrations.protocol_analyzers.frontend.input_tracker`
- [ ] Update __init__.py line 199: `cross_file_taint` relative import (try/except) → `code_scalpel.security.analyzers.cross_file_taint`
- [ ] Run tests: `pytest tests/test_symbolic_execution_engine.py -q`

### Phase 2: Core Source Files (12 files)
- [ ] `mcp/server.py` - Update security_analyzer imports
- [ ] `generators/refactor_simulator.py` - Update security_analyzer imports
- [ ] `pdg/pdg_analyzer.py` - Update taint_tracker imports
- [ ] __init__.py - Update unified_sink_detector imports
- [ ] __init__.py - Update protocol analyzer imports
- [ ] __init__.py docstrings (lines 47-57) - Update examples
- [ ] __init__.py docstrings - Update examples
- [ ] Run: `ruff check src/ --select F401,F811`
- [ ] Run: `pyright src/code_scalpel/ | grep -i error`

### Phase 3A: High-Volume Test Files (10 files)
- [ ] `tests/test_taint_tracker.py` (26 occurrences)
- [ ] `tests/test_security_analyzer.py` (20 occurrences)
- [ ] test_coverage_final_push.py (16 occurrences)
- [ ] test_uncovered_lines_final.py (13 occurrences)
- [ ] test_unified_sink_detector.py (4+ occurrences)
- [ ] `tests/test_secret_scanner.py` (5 occurrences)
- [ ] test_branch_coverage_95.py (multiple)
- [ ] test_coverage_ultra_final.py (multiple)
- [ ] test_coverage_branches_95.py (multiple)
- [ ] test_final_95_push.py (multiple)
- [ ] Run: `pytest tests/test_taint_tracker.py tests/test_security_analyzer.py -q`

### Phase 3B: Remaining Test Files (~97 files)
- [ ] Batch update all remaining test files with sed/automated replacement
- [ ] Verify no import errors: `python -c "import sys; sys.path.insert(0, 'src'); import tests"`
- [ ] Run full test suite: `pytest tests/ -q --tb=line`

### Phase 4: Examples (2 files)
- [ ] security_analysis_example.py
- [ ] symbolic_execution_example.py
- [ ] Run: `python examples/security_analysis_example.py`
- [ ] Run: `python examples/symbolic_execution_example.py`

### Phase 5: Documentation (51 files - Low Priority)
- [ ] COMPREHENSIVE_GUIDE.md (12 occurrences)
- [ ] `docs/guides/security_analysis_guide.md` (7 occurrences)
- [ ] `docs/modules/symbolic_execution_tools.md` (5 occurrences)
- [ ] `docs/architecture/security_architecture.md` (4 occurrences)
- [ ] All other doc files (47 remaining)
- [ ] Verify: `grep -r "from code_scalpel.symbolic_execution_tools" docs/`

### Phase 6: Final Verification
- [ ] Run full test suite: `pytest tests/ -x`
- [ ] Check for remaining old imports: `grep -r "from code_scalpel.symbolic_execution_tools\.(taint|security|unified|schema|grpc|graphql|kafka|frontend|cross_file|secret|type_evap|ml_vuln)" src/ tests/`
- [ ] Run Pyright: `pyright src/ --outputjson | grep errorCount`
- [ ] Run Ruff: `ruff check src/ tests/`
- [ ] Test import from new locations: `python -c "from code_scalpel.security.analyzers import TaintTracker, SecurityAnalyzer, UnifiedSinkDetector"`

### Phase 7: Remove Stub Files (FINAL STEP - Only after all above complete)
- [ ] Delete `symbolic_execution_tools/taint_tracker.py`
- [ ] Delete `symbolic_execution_tools/security_analyzer.py`
- [ ] Delete `symbolic_execution_tools/unified_sink_detector.py`
- [ ] Delete `symbolic_execution_tools/cross_file_taint.py`
- [ ] Delete `symbolic_execution_tools/schema_drift_detector.py`
- [ ] Delete grpc_contract_analyzer.py
- [ ] Delete graphql_schema_tracker.py
- [ ] Delete `symbolic_execution_tools/kafka_taint_tracker.py`
- [ ] Delete `symbolic_execution_tools/frontend_input_tracker.py`
- [ ] Delete `symbolic_execution_tools/secret_scanner.py`
- [ ] Delete `symbolic_execution_tools/type_evaporation_detector.py`
- [ ] Delete `symbolic_execution_tools/ml_vulnerability_predictor.py`
- [ ] Delete `symbolic_execution_tools/sanitizer_analyzer.py`
- [ ] Delete `symbolic_execution_tools/vulnerability_scanner.py`
- [ ] Final test: `pytest tests/ -x` (must pass 100%)
- [ ] Clear Python cache: `find src -name "*.pyc" -delete && find src -type d -name __pycache__ -exec rm -rf {} +`

### Phase 8: Documentation Update
- [ ] Update CHANGELOG.md with breaking changes note
- [ ] Create migration guide if needed
- [ ] Update version number if this is a breaking change release

---

**Total Items:** 141 checkboxes  
**Estimated Time:** 2-4 hours (with automation)  
**Risk Level:** Medium (comprehensive testing required)