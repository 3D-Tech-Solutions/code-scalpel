"""Performance, memory, and stress tests for simulate_refactor.

Covers:
- Large input timing (10K LOC scale, soft threshold)
- Memory allocation snapshot (tracemalloc-based approximation)
- 100 sequential requests stability
"""

import time
import tracemalloc

import pytest

pytest.importorskip("code_scalpel")

from code_scalpel.generators import RefactorSimulator


def _gen_function_block(lines: int) -> str:
    body = "\n".join([f"    x{i} = {i}" for i in range(lines)])
    return f"def f():\n{body}\n    return {max(0, lines - 1)}\n"


class TestSimulateRefactorPerfAndMemory:
    def test_large_input_under_10s_soft_threshold(self):
        """Large input (~10K LOC) completes within 10s (soft threshold)."""
        simulator = RefactorSimulator()

        # Generate ~10k lines across original and new code combined
        original = _gen_function_block(5000)
        new_code = _gen_function_block(5000)

        start = time.time()
        result = simulator.simulate(original, new_code=new_code)
        duration = time.time() - start

        assert result is not None
        # Soft threshold; allow some variance in CI environments
        assert duration < 10.0, f"Duration {duration:.2f}s exceeds soft threshold"

    def test_memory_usage_snapshots(self):
        """Memory snapshot stays within reasonable bounds for medium input."""
        simulator = RefactorSimulator()
        original = _gen_function_block(1000)
        new_code = _gen_function_block(1000)

        tracemalloc.start()
        start_mem, _ = tracemalloc.get_traced_memory()
        _ = simulator.simulate(original, new_code=new_code)
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        # Heuristic bounds; adjust if CI variance is observed
        # We assert peak below ~50MB equivalent in Python object allocations.
        # tracemalloc reports bytes of traced allocations.
        assert peak < 50 * 1024 * 1024, f"Peak allocations too high: {peak} bytes"

    def test_sequential_100_requests(self):
        """Simulator handles 100 sequential requests successfully."""
        simulator = RefactorSimulator()
        for i in range(100):
            original = f"def f{i}():\n    return {i}\n"
            new_code = f"def f{i}():\n    return {i} + 1\n"
            result = simulator.simulate(original, new_code=new_code)
            assert result is not None
            assert result.status.value in {"safe", "warning"}
