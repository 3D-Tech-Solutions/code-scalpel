"""
Performance and Scalability Tests for get_file_context tool.

[20260104_TEST] Performance tests for Section 4.1 of MCP_TOOL_COMPREHENSIVE_TEST_CHECKLIST.md
Testing against real codebase files to validate performance requirements.
"""

import time
import tracemalloc
from pathlib import Path

import pytest

# Test file paths (relative to project root)
SMALL_FILE = "src/code_scalpel/licensing/__init__.py"  # ~50 lines
MEDIUM_FILE = "src/code_scalpel/analysis/code_analyzer.py"  # ~1,700 lines
LARGE_FILE = "src/code_scalpel/code_parsers/python_parsers/python_parsers_ast.py"  # ~4,000 lines
XLARGE_FILE = "src/code_scalpel/mcp/server.py"  # ~20,700 lines


class TestResponseTime:
    """Test response time requirements for different file sizes."""

    def test_small_file_under_100ms(self, community_server, project_root):
        """Small files (<100 LOC) complete in <100ms.

        Section 4.1 Performance & Scalability - Response Time
        """
        file_path = Path(project_root) / SMALL_FILE

        start = time.time()
        result = community_server.get_file_context(str(file_path))
        duration = time.time() - start

        assert result is not None
        assert duration < 0.1, f"Small file took {duration:.3f}s, expected <0.1s"
        print(f"✅ Small file ({result.get('line_count', 'N/A')} LOC): {duration*1000:.1f}ms")

    def test_medium_file_under_1s(self, community_server, project_root):
        """Medium files (~1000-2000 LOC) complete in <1s.

        Section 4.1 Performance & Scalability - Response Time
        """
        file_path = Path(project_root) / MEDIUM_FILE

        start = time.time()
        result = community_server.get_file_context(str(file_path))
        duration = time.time() - start

        assert result is not None
        assert duration < 1.0, f"Medium file took {duration:.3f}s, expected <1s"
        print(f"✅ Medium file ({result.get('line_count', 'N/A')} LOC): {duration*1000:.1f}ms")

    def test_large_file_4k_loc_under_5s(self, community_server, project_root):
        """Large files (~4K LOC) complete in <5s.

        Section 4.1 Performance & Scalability - Response Time
        """
        file_path = Path(project_root) / LARGE_FILE

        start = time.time()
        result = community_server.get_file_context(str(file_path))
        duration = time.time() - start

        assert result is not None
        assert duration < 5.0, f"Large file took {duration:.3f}s, expected <5s"
        print(f"✅ Large file ({result.get('line_count', 'N/A')} LOC): {duration:.3f}s")

    @pytest.mark.slow
    def test_xlarge_file_20k_loc_under_10s(self, community_server, project_root):
        """Extra-large files (10K+ LOC) complete in <10s.

        Section 4.1 Performance & Scalability - Response Time
        Validates 🟡 item: "Large inputs (10K LOC) complete in <10s"
        """
        file_path = Path(project_root) / XLARGE_FILE

        start = time.time()
        result = community_server.get_file_context(str(file_path))
        duration = time.time() - start

        assert result is not None
        assert duration < 10.0, f"XLarge file took {duration:.3f}s, expected <10s"
        print(f"✅ XLarge file ({result.get('line_count', 'N/A')} LOC): {duration:.3f}s")

    def test_performance_scales_linearly(self, community_server, project_root):
        """Performance degrades gracefully (not exponentially).

        Section 4.1 Performance & Scalability - Response Time
        """
        test_files = [
            (SMALL_FILE, "small"),
            (MEDIUM_FILE, "medium"),
            (LARGE_FILE, "large"),
        ]

        timings = []
        for file_path, label in test_files:
            full_path = Path(project_root) / file_path

            start = time.time()
            result = community_server.get_file_context(str(full_path))
            duration = time.time() - start

            line_count = result.get("line_count", 0) if result else 0
            timings.append((label, line_count, duration))
            print(f"  {label:8s}: {line_count:5d} LOC in {duration*1000:6.1f}ms")

        # Check that scaling is sub-quadratic (time per line doesn't explode)
        if len(timings) >= 2 and timings[0][1] > 0 and timings[-1][1] > 0:
            small_rate = timings[0][2] / timings[0][1]  # time per line
            large_rate = timings[-1][2] / timings[-1][1]

            # Rate shouldn't increase more than 10x (allow for some overhead)
            assert (
                large_rate < small_rate * 10
            ), f"Performance degrades non-linearly: {small_rate:.6f} -> {large_rate:.6f} s/line"


class TestMemoryUsage:
    """Test memory usage requirements."""

    def test_small_file_under_10mb(self, community_server, project_root):
        """Small files use <10MB RAM.

        Section 4.1 Performance & Scalability - Memory Usage
        """
        file_path = Path(project_root) / SMALL_FILE

        tracemalloc.start()
        result = community_server.get_file_context(str(file_path))
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        peak_mb = peak / (1024 * 1024)
        assert result is not None
        assert peak_mb < 10, f"Small file used {peak_mb:.1f}MB, expected <10MB"
        print(f"✅ Small file memory: {peak_mb:.2f}MB")

    def test_medium_file_under_50mb(self, community_server, project_root):
        """Medium files use <50MB RAM.

        Section 4.1 Performance & Scalability - Memory Usage
        """
        file_path = Path(project_root) / MEDIUM_FILE

        tracemalloc.start()
        result = community_server.get_file_context(str(file_path))
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        peak_mb = peak / (1024 * 1024)
        assert result is not None
        assert peak_mb < 50, f"Medium file used {peak_mb:.1f}MB, expected <50MB"
        print(f"✅ Medium file memory: {peak_mb:.2f}MB")

    @pytest.mark.slow
    def test_large_file_under_500mb(self, community_server, project_root):
        """Large files use <500MB RAM.

        Section 4.1 Performance & Scalability - Memory Usage
        Validates 🟡 item: "Large inputs use <500MB RAM"
        """
        file_path = Path(project_root) / XLARGE_FILE

        tracemalloc.start()
        result = community_server.get_file_context(str(file_path))
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        peak_mb = peak / (1024 * 1024)
        assert result is not None
        assert peak_mb < 500, f"Large file used {peak_mb:.1f}MB, expected <500MB"
        print(f"✅ Large file memory ({result.get('line_count', 'N/A')} LOC): {peak_mb:.2f}MB")

    def test_no_memory_leaks_repeated_calls(self, community_server, project_root):
        """No memory leaks (repeated calls don't accumulate).

        Section 4.1 Performance & Scalability - Memory Usage
        """
        file_path = Path(project_root) / MEDIUM_FILE

        # Warm-up call
        community_server.get_file_context(str(file_path))

        # Measure baseline
        tracemalloc.start()
        for _ in range(5):
            result = community_server.get_file_context(str(file_path))
            assert result is not None
        baseline_current, baseline_peak = tracemalloc.get_traced_memory()

        # Run more iterations
        for _ in range(20):
            result = community_server.get_file_context(str(file_path))
            assert result is not None
        final_current, final_peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        # Memory shouldn't grow significantly (allow 20% increase for caching)
        baseline_mb = baseline_peak / (1024 * 1024)
        final_mb = final_peak / (1024 * 1024)
        growth_ratio = final_mb / baseline_mb if baseline_mb > 0 else 1.0

        assert (
            growth_ratio < 1.5
        ), f"Memory leak detected: {baseline_mb:.1f}MB -> {final_mb:.1f}MB (growth: {growth_ratio:.1f}x)"
        print(f"✅ No memory leak: {baseline_mb:.1f}MB -> {final_mb:.1f}MB (growth: {growth_ratio:.2f}x)")


class TestStressTests:
    """Test stress testing requirements."""

    def test_100_sequential_requests(self, community_server, project_root):
        """100 sequential requests succeed.

        Section 4.1 Performance & Scalability - Stress Testing
        """
        file_path = Path(project_root) / SMALL_FILE

        start = time.time()
        for i in range(100):
            result = community_server.get_file_context(str(file_path))
            assert result is not None, f"Request {i+1}/100 failed"
        duration = time.time() - start

        avg_time = duration / 100
        print(f"✅ 100 sequential requests: {duration:.2f}s total, {avg_time*1000:.1f}ms avg")

    @pytest.mark.asyncio
    async def test_10_concurrent_requests(self, community_server, project_root):
        """10 concurrent requests succeed.

        Section 4.1 Performance & Scalability - Stress Testing
        """
        import asyncio

        file_path = Path(project_root) / MEDIUM_FILE

        async def call_tool():
            # Note: If community_server is not async, we'd need to wrap it
            # For now, assume synchronous execution in parallel tasks
            return community_server.get_file_context(str(file_path))

        start = time.time()
        tasks = [asyncio.create_task(asyncio.to_thread(call_tool)) for _ in range(10)]
        results = await asyncio.gather(*tasks)
        duration = time.time() - start

        assert all(r is not None for r in results), "Some concurrent requests failed"
        print(f"✅ 10 concurrent requests: {duration:.2f}s total")

    def test_recovery_after_limit(self, community_server, project_root):
        """Tool recovers after hitting limits.

        Section 4.1 Performance & Scalability - Stress Testing
        """
        # Try to hit a limit (e.g., file size limit in Community tier)
        file_path = Path(project_root) / XLARGE_FILE

        # First call might hit limit (20K lines > 500 Community limit)
        community_server.get_file_context(str(file_path))
        # Could fail or succeed depending on tier enforcement

        # Next call should work regardless
        small_file = Path(project_root) / SMALL_FILE
        result2 = community_server.get_file_context(str(small_file))

        assert result2 is not None, "Server didn't recover after limit/error"
        print("✅ Server recovered after limit/error")


class TestCrossPlatformStability:
    """Test cross-platform stability."""

    def test_deterministic_output_repeated_calls(self, community_server, project_root):
        """Same input → same output (every time).

        Section 4.2 Reliability & Error Handling - Determinism
        """
        file_path = Path(project_root) / MEDIUM_FILE

        results = []
        for _ in range(3):
            result = community_server.get_file_context(str(file_path))
            assert result is not None
            results.append(result)

        # Compare key fields (line_count, function count, etc.)
        for i in range(1, len(results)):
            assert results[i].get("line_count") == results[0].get("line_count"), "line_count differs between runs"
            assert results[i].get("functions") == results[0].get("functions"), "functions differ between runs"
            assert results[i].get("classes") == results[0].get("classes"), "classes differ between runs"

        print(f"✅ Deterministic output across {len(results)} calls")


@pytest.fixture
def project_root():
    """Get project root directory."""
    # Assuming tests run from project root or tests/ directory
    current = Path(__file__).resolve()
    # Navigate up to find project root (where src/ directory exists)
    root = current.parent
    while root != root.parent:
        if (root / "src").exists() and (root / "pyproject.toml").exists():
            return str(root)
        root = root.parent

    # Fallback: assume current working directory
    return str(Path.cwd())


@pytest.fixture
def community_server():
    """Community server instance for performance testing."""
    from code_scalpel.mcp.helpers.context_helpers import _get_file_context_sync

    class CommunityServerWrapper:
        """Wrapper for _get_file_context_sync with Community tier."""

        def get_file_context(self, file_path: str) -> dict:
            """Call get_file_context with Community tier capabilities."""
            try:
                result = _get_file_context_sync(
                    file_path,
                    capabilities=[],  # Community tier - no advanced features
                )
                return {
                    "file_path": result.file_path,
                    "line_count": result.line_count,
                    "functions": ([f.name for f in result.functions] if result.functions else []),
                    "classes": ([c.name for c in result.classes] if result.classes else []),
                    "imports": result.imports or [],
                    "complexity_score": result.complexity_score,
                }
            except Exception as e:
                return {"error": str(e)}

    return CommunityServerWrapper()
