# update_symbol Performance & Scale Test Plan

**Created**: January 3, 2026  
**Tool**: `update_symbol` - Surgical symbol replacement with tier-gated features  
**Purpose**: Define comprehensive performance and scale testing strategy  

---

## Performance Requirements (from Roadmap)

**Targets**:
- **Update Time**: <100ms per symbol
- **Success Rate**: >99%

**Current Status**: 🔴 **UNTESTED** - No performance benchmarks exist

---

## Test Categories

### 1. Single Symbol Update Performance

**Goal**: Validate <100ms update time for individual symbols

#### 1.1 Small Symbols (< 50 LOC)
- **Test**: `test_small_function_update_time`
- **Scenario**: Replace 10-line function
- **Metric**: Median time across 100 iterations
- **Acceptance**: <50ms (50% of target)
- **Fixture**: Simple arithmetic function

#### 1.2 Medium Symbols (50-200 LOC)
- **Test**: `test_medium_function_update_time`
- **Scenario**: Replace 100-line function with multiple branches
- **Metric**: Median time across 100 iterations
- **Acceptance**: <100ms (target)
- **Fixture**: Function with nested conditionals, loops

#### 1.3 Large Symbols (200-500 LOC)
- **Test**: `test_large_function_update_time`
- **Scenario**: Replace 300-line function
- **Metric**: Median time across 50 iterations
- **Acceptance**: <200ms (2x target, still reasonable)
- **Fixture**: Complex business logic function

#### 1.4 Very Large Symbols (500+ LOC)
- **Test**: `test_very_large_class_update_time`
- **Scenario**: Replace 800-line class with 20+ methods
- **Metric**: Median time across 20 iterations
- **Acceptance**: <500ms (document degradation)
- **Fixture**: Large Django/Flask model class

**Total Tests**: 4  
**Location**: `tests/tools/update_symbol/test_performance_single_symbol.py`

---

### 2. File Size Impact

**Goal**: Understand how file size affects update performance

#### 2.1 Small File Context (< 500 LOC)
- **Test**: `test_update_in_small_file`
- **Scenario**: Update 50-line function in 300-line file
- **Metric**: Update time
- **Acceptance**: <100ms
- **Fixture**: Typical utility module

#### 2.2 Medium File Context (500-2000 LOC)
- **Test**: `test_update_in_medium_file`
- **Scenario**: Update 50-line function in 1000-line file
- **Metric**: Update time
- **Acceptance**: <150ms
- **Fixture**: Service layer module

#### 2.3 Large File Context (2000-5000 LOC)
- **Test**: `test_update_in_large_file`
- **Scenario**: Update 50-line function in 3000-line file
- **Metric**: Update time
- **Acceptance**: <300ms
- **Fixture**: Monolithic module (anti-pattern but exists)

#### 2.4 Very Large File Context (5000+ LOC)
- **Test**: `test_update_in_very_large_file`
- **Scenario**: Update 50-line function in 8000-line file
- **Metric**: Update time
- **Acceptance**: <500ms (document performance warning)
- **Fixture**: Legacy monolith file

**Total Tests**: 4  
**Location**: `tests/tools/update_symbol/test_performance_file_size.py`

---

### 3. Batch Operations Performance (Pro Tier)

**Goal**: Validate performance of multiple updates in sequence

#### 3.1 Sequential Updates - Same File
- **Test**: `test_10_sequential_updates_same_file`
- **Scenario**: Update 10 different functions in same file
- **Metric**: Total time, per-update average
- **Acceptance**: <1 second total, <100ms average
- **Fixture**: Module with 10 small functions

#### 3.2 Sequential Updates - Different Files
- **Test**: `test_10_sequential_updates_different_files`
- **Scenario**: Update 1 function in each of 10 files
- **Metric**: Total time, per-update average
- **Acceptance**: <1.5 seconds total, <150ms average
- **Fixture**: 10 separate modules

#### 3.3 Unlimited Pro Updates
- **Test**: `test_50_updates_pro_tier`
- **Scenario**: 50 updates in single session (Pro tier unlimited)
- **Metric**: Total time, memory usage
- **Acceptance**: <5 seconds total, <2GB memory
- **Fixture**: 50 small functions across 10 files

#### 3.4 High-Volume Pro Updates
- **Test**: `test_100_updates_pro_tier`
- **Scenario**: 100 updates in single session
- **Metric**: Total time, memory usage, no degradation
- **Acceptance**: <10 seconds total, linear scaling
- **Fixture**: 100 small functions across 20 files

**Total Tests**: 4  
**Location**: `tests/tools/update_symbol/test_performance_batch.py`

---

### 4. Multi-File Atomic Operations (Pro Tier)

**Goal**: Measure performance of atomic multi-file updates

#### 4.1 Small Multi-File (2-3 files)
- **Test**: `test_atomic_update_3_files`
- **Scenario**: Atomic update across 3 files
- **Metric**: Transaction time, rollback time if fails
- **Acceptance**: <500ms transaction, <200ms rollback
- **Fixture**: 3 interdependent modules

#### 4.2 Medium Multi-File (5-10 files)
- **Test**: `test_atomic_update_10_files`
- **Scenario**: Atomic update across 10 files
- **Metric**: Transaction time, rollback time
- **Acceptance**: <2 seconds transaction, <500ms rollback
- **Fixture**: 10 interdependent modules

#### 4.3 Large Multi-File (20+ files)
- **Test**: `test_atomic_update_25_files`
- **Scenario**: Atomic update across 25 files
- **Metric**: Transaction time, rollback time
- **Acceptance**: <5 seconds transaction, <1 second rollback
- **Fixture**: 25 interdependent modules

#### 4.4 Rollback Performance Under Failure
- **Test**: `test_rollback_performance_midpoint_failure`
- **Scenario**: Atomic update of 10 files, fail at file 6
- **Metric**: Rollback time, cleanup verification
- **Acceptance**: <1 second rollback, all files restored
- **Fixture**: 10 files with intentional failure at midpoint

**Total Tests**: 4  
**Location**: `tests/tools/update_symbol/test_performance_multifile.py`

---

### 5. Import Adjustment Performance (Pro Tier)

**Goal**: Measure overhead of import auto-adjustment

#### 5.1 No Import Changes
- **Test**: `test_update_no_import_impact`
- **Scenario**: Update function, no imports affected
- **Metric**: Time comparison vs baseline
- **Acceptance**: <10ms overhead
- **Fixture**: Self-contained function

#### 5.2 Add Single Import
- **Test**: `test_update_add_one_import`
- **Scenario**: Update requires adding 1 new import
- **Metric**: Time including import adjustment
- **Acceptance**: <150ms total
- **Fixture**: Function using new stdlib module

#### 5.3 Add Multiple Imports
- **Test**: `test_update_add_5_imports`
- **Scenario**: Update requires adding 5 imports
- **Metric**: Time including all import adjustments
- **Acceptance**: <250ms total
- **Fixture**: Function using multiple new modules

#### 5.4 Remove Unused Imports
- **Test**: `test_update_remove_3_unused_imports`
- **Scenario**: Update makes 3 imports unused
- **Metric**: Time including cleanup
- **Acceptance**: <200ms total
- **Fixture**: Function refactored to remove dependencies

**Total Tests**: 4  
**Location**: `tests/tools/update_symbol/test_performance_imports.py`

---

### 6. Compliance & Audit Performance (Enterprise Tier)

**Goal**: Measure overhead of Enterprise-tier compliance checks

#### 6.1 Compliance Check - Pass
- **Test**: `test_compliance_check_overhead_pass`
- **Scenario**: Update with policy check (passes)
- **Metric**: Time vs non-compliance update
- **Acceptance**: <50ms overhead
- **Fixture**: Compliant function update

#### 6.2 Compliance Check - Fail Early
- **Test**: `test_compliance_check_overhead_fail`
- **Scenario**: Update fails compliance (early detection)
- **Metric**: Time to rejection
- **Acceptance**: <100ms (fail fast)
- **Fixture**: Non-compliant function update

#### 6.3 Audit Trail Logging
- **Test**: `test_audit_logging_overhead`
- **Scenario**: Update with full audit trail generation
- **Metric**: Time overhead for logging
- **Acceptance**: <30ms overhead
- **Fixture**: Any enterprise update

#### 6.4 Approval Workflow Overhead
- **Test**: `test_approval_workflow_overhead`
- **Scenario**: Update requiring approval (approved)
- **Metric**: Time from submission to execution
- **Acceptance**: <100ms processing time (excluding human delay)
- **Fixture**: Public API function requiring approval

**Total Tests**: 4  
**Location**: `tests/tools/update_symbol/test_performance_enterprise.py`

---

### 7. Concurrent Operations Stress Test

**Goal**: Validate behavior under concurrent load

#### 7.1 Concurrent Same-File Updates
- **Test**: `test_10_concurrent_updates_same_file`
- **Scenario**: 10 threads updating different functions in same file
- **Metric**: Success rate, time, file integrity
- **Acceptance**: 100% success, proper locking, <2 seconds
- **Fixture**: File with 10 functions, ThreadPoolExecutor

#### 7.2 Concurrent Different-File Updates
- **Test**: `test_50_concurrent_updates_different_files`
- **Scenario**: 50 threads updating 50 different files
- **Metric**: Success rate, time, no file corruption
- **Acceptance**: 100% success, <3 seconds
- **Fixture**: 50 files, ThreadPoolExecutor

#### 7.3 Concurrent Multi-File Atomic Updates
- **Test**: `test_5_concurrent_atomic_multifile`
- **Scenario**: 5 threads, each doing atomic 5-file updates
- **Metric**: Success rate, no deadlocks, proper rollback
- **Acceptance**: 100% success or proper rollback, <5 seconds
- **Fixture**: 25 files (5 groups of 5), ThreadPoolExecutor

#### 7.4 Session Limit Under Concurrency
- **Test**: `test_community_session_limit_concurrent`
- **Scenario**: Community tier, 10 threads trying 2 updates each
- **Metric**: Proper limit enforcement, no race conditions
- **Acceptance**: Exactly 10 updates succeed, others rejected
- **Fixture**: Shared session, ThreadPoolExecutor

**Total Tests**: 4  
**Location**: `tests/tools/update_symbol/test_performance_concurrent.py`

---

### 8. Memory & Resource Usage

**Goal**: Ensure memory efficiency and no leaks

#### 8.1 Memory Profile - Single Update
- **Test**: `test_memory_usage_single_update`
- **Scenario**: Track memory before/during/after single update
- **Metric**: Peak memory increase
- **Acceptance**: <50MB increase for typical update
- **Fixture**: Medium-sized function update

#### 8.2 Memory Profile - 100 Sequential Updates
- **Test**: `test_memory_leak_100_updates`
- **Scenario**: 100 updates, check for memory leaks
- **Metric**: Memory growth pattern
- **Acceptance**: Linear growth only (no leaks), <500MB total
- **Fixture**: 100 small function updates

#### 8.3 Backup File Disk Usage
- **Test**: `test_backup_disk_usage_cleanup`
- **Scenario**: 50 updates with backups, check disk usage
- **Metric**: Disk space consumed, cleanup effectiveness
- **Acceptance**: Backups created, old ones cleaned
- **Fixture**: 50 updates with backup rotation

#### 8.4 File Handle Leaks
- **Test**: `test_file_handle_cleanup`
- **Scenario**: 200 updates, check file handle leaks
- **Metric**: Open file descriptors before/after
- **Acceptance**: No file handle leaks
- **Fixture**: 200 updates, check `lsof` or equivalent

**Total Tests**: 4  
**Location**: `tests/tools/update_symbol/test_performance_resources.py`

---

### 9. Error Handling Performance

**Goal**: Validate fast-fail behavior and error overhead

#### 9.1 Syntax Error Detection Speed
- **Test**: `test_syntax_error_detection_time`
- **Scenario**: Submit invalid code
- **Metric**: Time to rejection
- **Acceptance**: <50ms (fail fast)
- **Fixture**: Code with syntax error

#### 9.2 File Not Found Detection
- **Test**: `test_file_not_found_detection_time`
- **Scenario**: Update non-existent file
- **Metric**: Time to error
- **Acceptance**: <10ms (filesystem check)
- **Fixture**: Invalid file path

#### 9.3 Session Limit Rejection Time
- **Test**: `test_session_limit_rejection_time`
- **Scenario**: 11th update in Community tier
- **Metric**: Time to rejection
- **Acceptance**: <5ms (counter check)
- **Fixture**: Community session at limit

#### 9.4 License Validation Time
- **Test**: `test_license_validation_overhead`
- **Scenario**: Validate Pro/Enterprise license
- **Metric**: Time overhead per validation
- **Acceptance**: <20ms (JWT decode + verify)
- **Fixture**: Valid Pro license token

**Total Tests**: 4  
**Location**: `tests/tools/update_symbol/test_performance_errors.py`

---

### 10. Success Rate Validation

**Goal**: Validate >99% success rate under normal conditions

#### 10.1 Success Rate - 1000 Updates
- **Test**: `test_success_rate_1000_updates`
- **Scenario**: 1000 valid updates (mix of sizes/types)
- **Metric**: Success rate, failure analysis
- **Acceptance**: >99% success (≤10 failures)
- **Fixture**: 1000 diverse valid update scenarios

#### 10.2 Success Rate - Edge Cases
- **Test**: `test_success_rate_500_edge_cases`
- **Scenario**: 500 edge case updates (async, decorators, nested, etc.)
- **Metric**: Success rate for challenging scenarios
- **Acceptance**: >95% success (edge cases harder)
- **Fixture**: 500 edge case scenarios

#### 10.3 Success Rate - Multi-File Atomic
- **Test**: `test_success_rate_100_multifile_atomic`
- **Scenario**: 100 atomic multi-file updates (3-5 files each)
- **Metric**: Success rate, rollback effectiveness
- **Acceptance**: >99% success or proper rollback
- **Fixture**: 100 multi-file update scenarios

#### 10.4 Failure Classification
- **Test**: `test_failure_reasons_analysis`
- **Scenario**: Analyze all failures from above tests
- **Metric**: Categorize failure types
- **Acceptance**: No systemic failures, only edge cases
- **Fixture**: Results from tests 10.1-10.3

**Total Tests**: 4  
**Location**: `tests/tools/update_symbol/test_performance_reliability.py`

---

## Test Infrastructure Requirements

### Performance Measurement Utilities

**File**: `tests/tools/update_symbol/conftest.py` (extend existing)

```python
import time
import psutil
import pytest
from contextlib import contextmanager
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class PerformanceMetrics:
    """Performance measurement results"""
    duration_ms: float
    memory_delta_mb: float
    success: bool
    iterations: int
    median_ms: Optional[float] = None
    p95_ms: Optional[float] = None
    p99_ms: Optional[float] = None

@contextmanager
def measure_performance(iterations: int = 1):
    """Context manager for performance measurement"""
    process = psutil.Process()
    mem_before = process.memory_info().rss / 1024 / 1024  # MB
    durations: List[float] = []
    
    start = time.perf_counter()
    try:
        yield durations
    finally:
        end = time.perf_counter()
        mem_after = process.memory_info().rss / 1024 / 1024  # MB
        
        duration_ms = (end - start) * 1000
        memory_delta = mem_after - mem_before
        
        # Calculate percentiles if multiple iterations
        median = None
        p95 = None
        p99 = None
        if len(durations) > 1:
            sorted_durations = sorted(durations)
            median = sorted_durations[len(sorted_durations) // 2]
            p95 = sorted_durations[int(len(sorted_durations) * 0.95)]
            p99 = sorted_durations[int(len(sorted_durations) * 0.99)]
        
        metrics = PerformanceMetrics(
            duration_ms=duration_ms,
            memory_delta_mb=memory_delta,
            success=True,
            iterations=iterations,
            median_ms=median,
            p95_ms=p95,
            p99_ms=p99
        )
        return metrics

@pytest.fixture
def performance_threshold():
    """Fixture providing performance thresholds"""
    return {
        "small_symbol": 50,      # <50ms for small symbols
        "medium_symbol": 100,    # <100ms for medium symbols
        "large_symbol": 200,     # <200ms for large symbols
        "very_large_symbol": 500,  # <500ms for very large symbols
        "multifile_3": 500,      # <500ms for 3-file atomic
        "multifile_10": 2000,    # <2s for 10-file atomic
        "import_overhead": 50,   # <50ms import adjustment overhead
        "compliance_overhead": 50,  # <50ms compliance check overhead
    }

@pytest.fixture
def large_file_fixture(tmp_path):
    """Generate large file for performance testing"""
    file_path = tmp_path / "large_module.py"
    
    # Generate 5000-line file with 100 functions
    lines = []
    for i in range(100):
        lines.append(f"def function_{i}(x, y):")
        lines.append(f'    """Function {i} docstring"""')
        for j in range(48):  # 48 lines per function = 50 total
            lines.append(f"    # Line {j}")
        lines.append(f"    return x + y + {i}")
        lines.append("")
    
    file_path.write_text("\n".join(lines))
    return file_path
```

### Fixture Generators

**File**: `tests/tools/update_symbol/fixtures/performance_fixtures.py`

```python
"""
Performance test fixtures for update_symbol tool.

Generates various sizes of functions, classes, and files for benchmarking.
"""

def generate_small_function(name: str, lines: int = 10) -> str:
    """Generate small function (< 50 LOC)"""
    return f'''def {name}(a, b):
    """Small function for performance testing"""
    result = a + b
    if result > 10:
        result *= 2
    elif result < 0:
        result = 0
    else:
        result += 1
    return result
'''

def generate_medium_function(name: str, lines: int = 100) -> str:
    """Generate medium function (50-200 LOC)"""
    # Implementation generating 100-line function with branches, loops
    pass

def generate_large_function(name: str, lines: int = 300) -> str:
    """Generate large function (200-500 LOC)"""
    # Implementation generating 300-line function
    pass

def generate_very_large_class(name: str, methods: int = 20) -> str:
    """Generate very large class (500+ LOC)"""
    # Implementation generating 800-line class with 20 methods
    pass

def generate_file_with_n_functions(n: int, lines_per_function: int = 50) -> str:
    """Generate file with N functions of specified size"""
    # Implementation generating file with N functions
    pass
```

---

## Acceptance Criteria Summary

### Must Pass (Blockers)

| Category | Metric | Target | Test Count |
|----------|--------|--------|-----------|
| **Single Symbol Time** | Median update time | <100ms | 4 |
| **Success Rate** | Valid operations | >99% | 4 |
| **Memory Efficiency** | No leaks | 0 leaks | 4 |
| **Error Fast-Fail** | Rejection time | <50ms | 4 |

**Total Critical Tests**: 16

### Should Pass (Important)

| Category | Metric | Target | Test Count |
|----------|--------|--------|-----------|
| **File Size Impact** | Large file handling | <500ms | 4 |
| **Batch Operations** | 50 updates | <5s total | 4 |
| **Multi-File Atomic** | 10-file transaction | <2s | 4 |
| **Import Overhead** | Auto-adjustment | <50ms overhead | 4 |

**Total Important Tests**: 16

### Nice to Have (Informational)

| Category | Metric | Target | Test Count |
|----------|--------|--------|-----------|
| **Enterprise Overhead** | Compliance checks | <50ms overhead | 4 |
| **Concurrent Load** | 50 concurrent ops | No corruption | 4 |
| **Resource Cleanup** | Disk/handles | No leaks | 4 |
| **Failure Analysis** | Failure categorization | Root cause ID | 1 |

**Total Informational Tests**: 13

---

## Total Test Plan Summary

| Test File | Tests | Priority | Status |
|-----------|-------|----------|--------|
| test_performance_single_symbol.py | 4 | 🔴 CRITICAL | ❌ Not Implemented |
| test_performance_file_size.py | 4 | 🟡 IMPORTANT | ❌ Not Implemented |
| test_performance_batch.py | 4 | 🟡 IMPORTANT | ❌ Not Implemented |
| test_performance_multifile.py | 4 | 🟡 IMPORTANT | ❌ Not Implemented |
| test_performance_imports.py | 4 | 🟡 IMPORTANT | ❌ Not Implemented |
| test_performance_enterprise.py | 4 | 🟢 INFORMATIONAL | ❌ Not Implemented |
| test_performance_concurrent.py | 4 | 🟢 INFORMATIONAL | ❌ Not Implemented |
| test_performance_resources.py | 4 | 🔴 CRITICAL | ❌ Not Implemented |
| test_performance_errors.py | 4 | 🔴 CRITICAL | ❌ Not Implemented |
| test_performance_reliability.py | 4 | 🔴 CRITICAL | ❌ Not Implemented |

**Total Performance Tests**: 40 comprehensive benchmarks

**Estimated Implementation Time**: 8-12 hours (with fixtures and utilities)

---

## Implementation Phases

### Phase 1: Critical Tests (Must-Have for Release)
**Priority**: 🔴 CRITICAL  
**Tests**: 16 (single symbol, success rate, memory, errors)  
**Estimated Time**: 4 hours  
**Acceptance**: ALL 16 must pass targets

### Phase 2: Important Tests (Should-Have for Production)
**Priority**: 🟡 IMPORTANT  
**Tests**: 16 (file size, batch, multi-file, imports)  
**Estimated Time**: 4 hours  
**Acceptance**: ≥14 tests pass targets (87.5%)

### Phase 3: Informational Tests (Nice-to-Have)
**Priority**: 🟢 INFORMATIONAL  
**Tests**: 8 (enterprise, concurrent, resources, analysis)  
**Estimated Time**: 3 hours  
**Acceptance**: Document actual performance, no hard requirements

---

## Success Criteria for Release

**Minimum for v1.0 Release**:
1. ✅ Phase 1 Critical Tests: ALL 16 passing
2. ✅ Performance Target Met: Median <100ms for medium symbols
3. ✅ Success Rate Met: >99% across 1000 valid operations
4. ✅ No Memory Leaks: Validated across 100 sequential updates
5. ✅ Fast Error Handling: <50ms rejection for invalid input

**Recommended for Production**:
- All above + Phase 2 Important Tests ≥87.5% passing

**Complete Validation**:
- All above + Phase 3 Informational Tests documented

---

## Next Steps

1. **User Decision**: Determine which phase(s) are required for release
2. **Implementation Order**: Start with Phase 1 Critical Tests
3. **Fixture Creation**: Build reusable performance fixtures
4. **Baseline Establishment**: Run tests to establish current performance
5. **Optimization**: If targets not met, profile and optimize
6. **Documentation**: Update assessment document with results

---

## Questions for User

1. **Release Blocking**: Are Phase 1 Critical Tests (16 tests) sufficient for v1.0 release?
2. **Performance Target**: Is <100ms median acceptable, or should we target <50ms?
3. **Success Rate**: Is >99% success rate acceptable, or require 100%?
4. **Concurrent Load**: Should concurrent operations (Phase 3) be required for release?
5. **Implementation Priority**: Should we implement all 40 tests, or focus on Phase 1 first?
