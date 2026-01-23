"""
[20260104_TEST] Concurrency and memory regression tests for update_symbol.

Targets checklist gaps: 10-way concurrency success and basic leak guard.
"""

import concurrent.futures
import tracemalloc
from pathlib import Path

from code_scalpel.surgery.surgical_patcher import SurgicalPatcher


def _write_function(name: str) -> str:
    return f"""
def {name}(x: int, y: int) -> int:
    return x + y
"""


def _write_replacement(name: str) -> str:
    return f"""
def {name}(x: int, y: int) -> int:
    return (x * 2) + (y * 2)
"""


def test_update_symbol_concurrent_updates(tmp_path):
    """Run 10 concurrent updates on separate files to ensure no races or corruption."""

    def _do_update(idx: int) -> bool:
        target = tmp_path / f"file_{idx}.py"
        target.write_text(_write_function(f"fn_{idx}"))

        patcher = SurgicalPatcher.from_file(str(target))
        result = patcher.update_function(f"fn_{idx}", _write_replacement(f"fn_{idx}"))
        if result.success:
            patcher.save(backup=False)
        return result.success

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
        results = list(pool.map(_do_update, range(10)))

    assert all(results), f"Concurrent update failed for indices: {[i for i, ok in enumerate(results) if not ok]}"


def test_update_symbol_memory_leak_guard(tmp_path):
    """Guard against unbounded memory growth across repeated operations."""

    tracemalloc.start()

    for idx in range(50):
        target = tmp_path / f"mem_{idx}.py"
        target.write_text(_write_function(f"fn_{idx}"))

        patcher = SurgicalPatcher.from_file(str(target))
        result = patcher.update_function(f"fn_{idx}", _write_replacement(f"fn_{idx}"))
        if result.success:
            patcher.save(backup=False)

    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    # Allow generous headroom; we only care that usage stays within a small envelope
    peak_mb = peak / (1024 * 1024)
    assert peak_mb < 50, f"Peak memory too high for 50 sequential operations: {peak_mb:.2f} MB"


def _generate_lines(name: str, lines: int) -> str:
    body = "\n".join(["    x = x + 1" for _ in range(lines)])
    return f"""
def {name}(x: int) -> int:
{body}
    return x
"""


def _memory_bucket_run(tmp_path: Path, lines: int, iterations: int) -> int:
    from code_scalpel.surgery.surgical_patcher import SurgicalPatcher

    tracemalloc.start()
    for idx in range(iterations):
        target = tmp_path / f"bucket_{lines}_{idx}.py"
        target.write_text(_generate_lines(f"fn_{lines}_{idx}", lines))

        patcher = SurgicalPatcher.from_file(str(target))
        result = patcher.update_function(
            f"fn_{lines}_{idx}",
            _write_replacement(f"fn_{lines}_{idx}"),
        )
        if result.success:
            patcher.save(backup=False)

    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return int(peak / (1024 * 1024))  # MB


def test_update_symbol_memory_buckets(tmp_path):
    """Memory stays within expected limits for small/medium/large inputs."""

    small_peak = _memory_bucket_run(tmp_path, lines=20, iterations=5)
    medium_peak = _memory_bucket_run(tmp_path, lines=1000, iterations=5)
    large_peak = _memory_bucket_run(tmp_path, lines=5000, iterations=3)

    assert small_peak < 10, f"Small bucket peak too high: {small_peak} MB"
    assert medium_peak < 50, f"Medium bucket peak too high: {medium_peak} MB"
    assert large_peak < 500, f"Large bucket peak too high: {large_peak} MB"
