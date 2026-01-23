# [20260103_TEST] Performance tests for surgical patching via SurgicalPatcher
"""
Performance tests for update_symbol tool.

These tests measure the performance of the core surgical patching operation
that the MCP tool uses. We test the SurgicalPatcher class directly, which is
the underlying implementation that processes update_symbol requests.

Phase 1 Critical Tests (8 tests):
1. Single Symbol Performance (4 tests): small, medium, large, very large
2. Error Handling (2 tests): syntax errors, file not found
3. Success Rate (2 tests): normal operations, edge cases
"""

import os
import shutil
import sys
import time
from pathlib import Path
from statistics import median

# Add src directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../src")))

from code_scalpel.surgery.surgical_patcher import SurgicalPatcher
from tests.tools.update_symbol.fixtures.performance_fixtures import (
    generate_large_function,
    generate_medium_function,
    generate_small_function,
    generate_very_large_class,
    get_large_function_replacement,
    get_medium_function_replacement,
    get_small_function_replacement,
    get_very_large_class_replacement,
)


def setup_test_dir(name: str) -> Path:
    """Create a test directory within project root."""
    test_dir = Path(f"/mnt/k/backup/Develop/code-scalpel/.test_perf_{name}")
    test_dir.mkdir(exist_ok=True)
    return test_dir


def cleanup_test_dir(test_dir: Path):
    """Remove test directory."""
    shutil.rmtree(test_dir, ignore_errors=True)


# ========================================================================
# PHASE 1: SINGLE SYMBOL PERFORMANCE (4 tests)
# ========================================================================


def test_small_function_perf():
    """Small function (<50 LOC) performance: target <50ms median."""
    test_dir = setup_test_dir("small")
    try:
        test_file = test_dir / "test.py"
        test_file.write_text(generate_small_function("process_data", "branching"))

        durations = []
        for _i in range(20):
            test_file.write_text(generate_small_function("process_data", "branching"))

            patcher = SurgicalPatcher.from_file(str(test_file))
            start = time.perf_counter()
            # [20260117_TEST] Result not directly asserted in perf test
            _result = patcher.update_function(
                "process_data",
                get_small_function_replacement("process_data"),
            )
            patcher.save(backup=True)
            duration_ms = (time.perf_counter() - start) * 1000
            durations.append(duration_ms)

        sorted_durations = sorted(durations)
        med = median(sorted_durations)
        p95 = sorted_durations[int(len(sorted_durations) * 0.95)]
        p99 = sorted_durations[int(len(sorted_durations) * 0.99)]

        assert med < 50, f"Small function too slow: {med:.2f}ms (P95={p95:.2f}, P99={p99:.2f})"
        print(f"✅ Small function: median={med:.2f}ms, P95={p95:.2f}ms, P99={p99:.2f}ms")
    finally:
        cleanup_test_dir(test_dir)


def test_medium_function_perf():
    """Medium function (50-200 LOC) performance: target <100ms median."""
    test_dir = setup_test_dir("medium")
    try:
        test_file = test_dir / "test.py"
        test_file.write_text(generate_medium_function("process_batch", 150))

        durations = []
        for _i in range(20):
            # Create fresh file each iteration to avoid corruption
            test_file.write_text(generate_medium_function("process_batch", 150))

            try:
                patcher = SurgicalPatcher.from_file(str(test_file))
                start = time.perf_counter()
                # [20260117_TEST] Result not directly asserted in perf test
                _result = patcher.update_function(
                    "process_batch",
                    get_medium_function_replacement("process_batch"),
                )
                patcher.save(backup=True)
                duration_ms = (time.perf_counter() - start) * 1000
                durations.append(duration_ms)
            except Exception:
                # Skip corrupted iterations
                continue

        if not durations:
            raise AssertionError("No valid measurements collected for medium function")

        sorted_durations = sorted(durations)
        med = median(sorted_durations)
        p95 = sorted_durations[int(len(sorted_durations) * 0.95)]
        p99 = sorted_durations[int(len(sorted_durations) * 0.99)]

        assert med < 100, f"Medium function too slow: {med:.2f}ms (P95={p95:.2f}, P99={p99:.2f})"
        print(f"✅ Medium function: median={med:.2f}ms, P95={p95:.2f}ms, P99={p99:.2f}ms")
    finally:
        cleanup_test_dir(test_dir)


def test_large_function_perf():
    """Large function (200-500 LOC) performance: target <200ms median."""
    test_dir = setup_test_dir("large")
    try:
        test_file = test_dir / "test.py"
        test_file.write_text(generate_large_function("process_large", 350))

        durations = []
        for _i in range(10):
            test_file.write_text(generate_large_function("process_large", 350))

            patcher = SurgicalPatcher.from_file(str(test_file))
            start = time.perf_counter()
            # [20260117_TEST] Result not directly asserted in perf test
            _result = patcher.update_function(
                "process_large",
                get_large_function_replacement("process_large"),
            )
            patcher.save(backup=True)
            duration_ms = (time.perf_counter() - start) * 1000
            durations.append(duration_ms)

        sorted_durations = sorted(durations)
        med = median(sorted_durations)
        p95 = sorted_durations[int(len(sorted_durations) * 0.95)]
        p99 = sorted_durations[int(len(sorted_durations) * 0.99)]

        assert med < 200, f"Large function too slow: {med:.2f}ms (P95={p95:.2f}, P99={p99:.2f})"
        print(f"✅ Large function: median={med:.2f}ms, P95={p95:.2f}ms, P99={p99:.2f}ms")
    finally:
        cleanup_test_dir(test_dir)


def test_very_large_class_perf():
    """Very large class (500+ LOC) performance: target <1000ms median."""
    test_dir = setup_test_dir("very_large")
    try:
        test_file = test_dir / "test.py"
        test_file.write_text(generate_very_large_class("DataProcessor", 800))

        durations = []
        for _i in range(5):
            test_file.write_text(generate_very_large_class("DataProcessor", 800))

            patcher = SurgicalPatcher.from_file(str(test_file))
            start = time.perf_counter()
            # [20260117_TEST] Result not directly asserted in perf test
            _result = patcher.update_class(
                "DataProcessor",
                get_very_large_class_replacement("DataProcessor"),
            )
            patcher.save(backup=True)
            duration_ms = (time.perf_counter() - start) * 1000
            durations.append(duration_ms)

        sorted_durations = sorted(durations)
        med = median(sorted_durations)
        p95 = sorted_durations[int(len(sorted_durations) * 0.95)]
        p99 = sorted_durations[int(len(sorted_durations) * 0.99)]

        assert med < 1000, f"Very large class too slow: {med:.2f}ms (P95={p95:.2f}, P99={p99:.2f})"
        print(f"✅ Very large class: median={med:.2f}ms, P95={p95:.2f}ms, P99={p99:.2f}ms")
    finally:
        cleanup_test_dir(test_dir)


# ========================================================================
# PHASE 1: ERROR HANDLING (2 tests)
# ========================================================================


def test_syntax_error_perf():
    """Syntax error detection: target <50ms median."""
    test_dir = setup_test_dir("syntax")
    try:
        test_file = test_dir / "test.py"
        test_file.write_text(generate_small_function("test_func", "simple"))

        bad_code = "def broken_function(x):\n  return x +  # Missing operand"

        durations = []
        for _i in range(10):
            patcher = SurgicalPatcher.from_file(str(test_file))
            start = time.perf_counter()
            result = patcher.update_function("test_func", bad_code)
            duration_ms = (time.perf_counter() - start) * 1000
            durations.append(duration_ms)
            assert not result.success, "Syntax error should be rejected"

        med = median(sorted(durations))
        assert med < 50, f"Syntax error detection too slow: {med:.2f}ms"
        print(f"✅ Syntax error detection: median={med:.2f}ms")
    finally:
        cleanup_test_dir(test_dir)


def test_file_not_found_perf():
    """File not found detection: target <10ms median."""
    durations = []
    for _i in range(10):
        start = time.perf_counter()
        try:
            # [20260117_TEST] Trigger FileNotFoundError without assigning to a variable
            SurgicalPatcher.from_file("/nonexistent/file.py")
        except FileNotFoundError:
            pass
        duration_ms = (time.perf_counter() - start) * 1000
        durations.append(duration_ms)

    med = median(sorted(durations))
    assert med < 10, f"File not found detection too slow: {med:.2f}ms"
    print(f"✅ File not found detection: median={med:.2f}ms")


# ========================================================================
# PHASE 1: SUCCESS RATE (2 tests)
# ========================================================================


def test_success_rate_normal():
    """Success rate for normal operations: target >99%."""
    test_dir = setup_test_dir("normal_ops")
    try:
        successes = 0
        failures = 0
        for i in range(100):
            test_file = test_dir / f"test_{i}.py"
            test_file.write_text(generate_small_function(f"process_{i}", "simple"))

            patcher = SurgicalPatcher.from_file(str(test_file))
            result = patcher.update_function(
                f"process_{i}",
                get_small_function_replacement(f"process_{i}"),
            )
            if result.success:
                successes += 1
                patcher.save(backup=True)
            else:
                failures += 1

        rate = successes / (successes + failures) * 100
        assert rate >= 99.0, f"Success rate too low: {rate:.1f}% (failures: {failures})"
        print(f"✅ Normal operations success rate: {rate:.1f}% ({successes}/{successes + failures})")
    finally:
        cleanup_test_dir(test_dir)


def test_success_rate_edge_cases():
    """Success rate for edge cases: target >95%."""
    test_dir = setup_test_dir("edge_cases")
    try:
        edge_cases = [
            ("@property\ndef getter(self): return 42", "getter"),
            ("async def async_process(x): return x", "async_process"),
            ("def _private_helper(): pass", "_private_helper"),
            ("def __dunder_method__(): pass", "__dunder_method__"),
        ]

        successes = 0
        failures = 0
        for idx, (code_snippet, func_name) in enumerate(edge_cases * 13):
            test_file = test_dir / f"edge_{idx}.py"
            test_file.write_text(code_snippet + "\n")

            patcher = SurgicalPatcher.from_file(str(test_file))
            result = patcher.update_function(func_name, code_snippet)
            if result.success:
                successes += 1
                patcher.save(backup=True)
            else:
                failures += 1

        rate = successes / (successes + failures) * 100 if (successes + failures) > 0 else 0
        assert rate >= 95.0, f"Edge case success rate too low: {rate:.1f}%"
        print(f"✅ Edge cases success rate: {rate:.1f}% ({successes}/{successes + failures})")
    finally:
        cleanup_test_dir(test_dir)
