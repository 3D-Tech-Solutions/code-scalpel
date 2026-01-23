"""[20260104_TEST] Performance, memory, and stress tests for get_graph_neighborhood

Validates:
- Response time benchmarks
- Memory usage (RSS) tracking
- Memory leak detection
- Sequential load handling
- Concurrent request handling
"""

import asyncio
import gc
import time
from unittest.mock import patch

try:
    import psutil

    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

import pytest

from code_scalpel.mcp.server import GraphNeighborhoodResult, get_graph_neighborhood

pytestmark = pytest.mark.asyncio


# ============================================================================
# PERFORMANCE TIMING TESTS
# ============================================================================


class TestPerformanceTimings:
    """Test response time characteristics."""

    async def test_simple_graph_response_time(self, tmp_path):
        """Simple graph extraction should complete under 2 seconds."""
        # Create minimal project
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        (project_dir / "main.py").write_text("def foo():\n    return bar()\n\ndef bar():\n    return 1\n")

        with patch("code_scalpel.mcp.server._get_current_tier", return_value="community"):
            with patch("code_scalpel.mcp.server.get_tool_capabilities") as mock_caps:
                mock_caps.return_value = {
                    "capabilities": ["basic_neighborhood"],
                    "limits": {"max_k": 1, "max_nodes": 20},
                }

                start = time.perf_counter()
                result = await get_graph_neighborhood(
                    center_node_id="python::main::function::foo",
                    k=1,
                    max_nodes=20,
                    project_root=str(project_dir),
                )
                elapsed = time.perf_counter() - start

                assert elapsed < 2.0, f"Response time {elapsed:.2f}s exceeds 2s threshold"
                # Result may succeed or fail (node not found), timing is key
                assert isinstance(result, GraphNeighborhoodResult)

    async def test_large_graph_with_truncation_timing(self, tmp_path):
        """Large graph with truncation should complete under 5 seconds."""
        # Create project with many interconnected functions
        project_dir = tmp_path / "large_project"
        project_dir.mkdir()

        # Generate file with many functions
        functions = []
        for i in range(50):
            functions.append(f"def func_{i}():\n")
            if i > 0:
                functions.append(f"    return func_{i-1}()\n")
            else:
                functions.append("    return 1\n")
            functions.append("\n")

        (project_dir / "large.py").write_text("".join(functions))

        with patch("code_scalpel.mcp.server._get_current_tier", return_value="pro"):
            with patch("code_scalpel.mcp.server.get_tool_capabilities") as mock_caps:
                mock_caps.return_value = {
                    "capabilities": ["basic_neighborhood", "advanced_neighborhood"],
                    "limits": {"max_k": 5, "max_nodes": 200},
                }

                start = time.perf_counter()
                result = await get_graph_neighborhood(
                    center_node_id="python::large::function::func_49",
                    k=3,
                    max_nodes=30,
                    project_root=str(project_dir),
                )
                elapsed = time.perf_counter() - start

                assert elapsed < 5.0, f"Response time {elapsed:.2f}s exceeds 5s threshold"
                assert isinstance(result, GraphNeighborhoodResult)

    async def test_confidence_filtering_performance(self, tmp_path):
        """Confidence filtering should not significantly degrade performance."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        (project_dir / "main.py").write_text(
            "def a():\n    return b()\n\ndef b():\n    return c()\n\ndef c():\n    return 1\n"
        )

        with patch("code_scalpel.mcp.server._get_current_tier", return_value="community"):
            with patch("code_scalpel.mcp.server.get_tool_capabilities") as mock_caps:
                mock_caps.return_value = {
                    "capabilities": ["basic_neighborhood"],
                    "limits": {"max_k": 1, "max_nodes": 20},
                }

                # Baseline: no filtering
                start_baseline = time.perf_counter()
                await get_graph_neighborhood(
                    center_node_id="python::main::function::a",
                    k=1,
                    min_confidence=0.0,
                    project_root=str(project_dir),
                )
                elapsed_baseline = time.perf_counter() - start_baseline

                # With filtering
                start_filtered = time.perf_counter()
                await get_graph_neighborhood(
                    center_node_id="python::main::function::a",
                    k=1,
                    min_confidence=0.9,
                    project_root=str(project_dir),
                )
                elapsed_filtered = time.perf_counter() - start_filtered

                # Filtering should not add more than 50% overhead
                overhead_ratio = elapsed_filtered / max(elapsed_baseline, 0.001)
                assert overhead_ratio < 1.5, f"Filtering overhead {overhead_ratio:.2f}x too high"


# ============================================================================
# MEMORY USAGE (RSS) TESTS
# ============================================================================


@pytest.mark.skipif(not HAS_PSUTIL, reason="psutil not available for memory measurements")
class TestMemoryUsage:
    """Test memory footprint characteristics."""

    async def test_baseline_memory_footprint(self, tmp_path):
        """Baseline memory usage should be under 100MB delta."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        (project_dir / "main.py").write_text("def foo():\n    return 1\n")

        process = psutil.Process()
        gc.collect()
        mem_before = process.memory_info().rss / 1024 / 1024  # MB

        with patch("code_scalpel.mcp.server._get_current_tier", return_value="community"):
            with patch("code_scalpel.mcp.server.get_tool_capabilities") as mock_caps:
                mock_caps.return_value = {
                    "capabilities": ["basic_neighborhood"],
                    "limits": {"max_k": 1, "max_nodes": 20},
                }

                await get_graph_neighborhood(
                    center_node_id="python::main::function::foo",
                    k=1,
                    max_nodes=20,
                    project_root=str(project_dir),
                )

        gc.collect()
        mem_after = process.memory_info().rss / 1024 / 1024  # MB
        mem_delta = mem_after - mem_before

        assert mem_delta < 100, f"Memory delta {mem_delta:.2f}MB exceeds 100MB threshold"

    async def test_large_graph_memory_bounded(self, tmp_path):
        """Large graph extraction should stay under 500MB delta."""
        project_dir = tmp_path / "large_project"
        project_dir.mkdir()

        # Generate large interconnected graph
        functions = []
        for i in range(100):
            functions.append(f"def func_{i}():\n")
            if i > 0:
                functions.append(f"    x = func_{i-1}()\n")
                functions.append(f"    y = func_{i-2 if i > 1 else 0}()\n")
                functions.append("    return x + y\n")
            else:
                functions.append("    return 1\n")
            functions.append("\n")

        (project_dir / "large.py").write_text("".join(functions))

        process = psutil.Process()
        gc.collect()
        mem_before = process.memory_info().rss / 1024 / 1024  # MB

        with patch("code_scalpel.mcp.server._get_current_tier", return_value="enterprise"):
            with patch("code_scalpel.mcp.server.get_tool_capabilities") as mock_caps:
                mock_caps.return_value = {
                    "capabilities": [
                        "basic_neighborhood",
                        "advanced_neighborhood",
                        "semantic_neighbors",
                    ],
                    "limits": {"max_k": None, "max_nodes": None},
                }

                await get_graph_neighborhood(
                    center_node_id="python::large::function::func_99",
                    k=5,
                    max_nodes=200,
                    project_root=str(project_dir),
                )

        gc.collect()
        mem_after = process.memory_info().rss / 1024 / 1024  # MB
        mem_delta = mem_after - mem_before

        assert mem_delta < 500, f"Memory delta {mem_delta:.2f}MB exceeds 500MB threshold"

    async def test_truncation_prevents_memory_explosion(self, tmp_path):
        """Truncation should prevent unbounded memory growth."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        # Generate highly connected graph
        functions = []
        for i in range(200):
            functions.append(f"def func_{i}():\n")
            # Each function calls 3 others
            functions.append(f"    a = func_{(i+1) % 200}()\n")
            functions.append(f"    b = func_{(i+2) % 200}()\n")
            functions.append(f"    c = func_{(i+3) % 200}()\n")
            functions.append("    return a + b + c\n")
            functions.append("\n")

        (project_dir / "dense.py").write_text("".join(functions))

        process = psutil.Process()
        gc.collect()
        mem_before = process.memory_info().rss / 1024 / 1024  # MB

        with patch("code_scalpel.mcp.server._get_current_tier", return_value="community"):
            with patch("code_scalpel.mcp.server.get_tool_capabilities") as mock_caps:
                mock_caps.return_value = {
                    "capabilities": ["basic_neighborhood"],
                    "limits": {"max_k": 1, "max_nodes": 20},
                }

                result = await get_graph_neighborhood(
                    center_node_id="python::dense::function::func_0",
                    k=1,
                    max_nodes=20,  # Strict truncation
                    project_root=str(project_dir),
                )

                # Verify truncation occurred
                if result.success:
                    assert result.truncated or result.total_nodes <= 20

        gc.collect()
        mem_after = process.memory_info().rss / 1024 / 1024  # MB
        mem_delta = mem_after - mem_before

        # Truncation should keep memory under 100MB even for dense graph
        assert mem_delta < 100, f"Truncated operation used {mem_delta:.2f}MB (should be under 100MB)"


# ============================================================================
# MEMORY LEAK DETECTION
# ============================================================================


@pytest.mark.skipif(not HAS_PSUTIL, reason="psutil not available for memory measurements")
class TestMemoryLeaks:
    """Test for memory leaks over repeated operations."""

    async def test_repeated_calls_no_leak(self, tmp_path):
        """Repeated calls should not leak memory."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        (project_dir / "main.py").write_text("def foo():\n    return bar()\n\ndef bar():\n    return 1\n")

        process = psutil.Process()
        gc.collect()

        # Warmup
        with patch("code_scalpel.mcp.server._get_current_tier", return_value="community"):
            with patch("code_scalpel.mcp.server.get_tool_capabilities") as mock_caps:
                mock_caps.return_value = {
                    "capabilities": ["basic_neighborhood"],
                    "limits": {"max_k": 1, "max_nodes": 20},
                }
                for _ in range(5):
                    await get_graph_neighborhood(
                        center_node_id="python::main::function::foo",
                        k=1,
                        max_nodes=20,
                        project_root=str(project_dir),
                    )

        gc.collect()
        mem_baseline = process.memory_info().rss / 1024 / 1024  # MB

        # Run 50 iterations
        with patch("code_scalpel.mcp.server._get_current_tier", return_value="community"):
            with patch("code_scalpel.mcp.server.get_tool_capabilities") as mock_caps:
                mock_caps.return_value = {
                    "capabilities": ["basic_neighborhood"],
                    "limits": {"max_k": 1, "max_nodes": 20},
                }
                for _ in range(50):
                    await get_graph_neighborhood(
                        center_node_id="python::main::function::foo",
                        k=1,
                        max_nodes=20,
                        project_root=str(project_dir),
                    )

        gc.collect()
        mem_final = process.memory_info().rss / 1024 / 1024  # MB
        mem_growth = mem_final - mem_baseline

        # Allow 20MB growth for caching, but not unbounded
        assert mem_growth < 20, f"Memory grew by {mem_growth:.2f}MB over 50 iterations (leak suspected)"


# ============================================================================
# SEQUENTIAL LOAD TESTS
# ============================================================================


class TestSequentialLoad:
    """Test handling of sequential request patterns."""

    async def test_sequential_varying_k(self, tmp_path):
        """Sequential requests with varying k should all complete."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        (project_dir / "main.py").write_text(
            "def a():\n    return b()\n\ndef b():\n    return c()\n\ndef c():\n    return 1\n"
        )

        with patch("code_scalpel.mcp.server._get_current_tier", return_value="pro"):
            with patch("code_scalpel.mcp.server.get_tool_capabilities") as mock_caps:
                mock_caps.return_value = {
                    "capabilities": ["basic_neighborhood", "advanced_neighborhood"],
                    "limits": {"max_k": 5, "max_nodes": 200},
                }

                # Sequential requests with k=1,2,3,4,5
                for k_val in range(1, 6):
                    result = await get_graph_neighborhood(
                        center_node_id="python::main::function::a",
                        k=k_val,
                        max_nodes=50,
                        project_root=str(project_dir),
                    )
                    assert isinstance(result, GraphNeighborhoodResult)

    async def test_sequential_different_nodes(self, tmp_path):
        """Sequential requests for different nodes should all complete."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        (project_dir / "main.py").write_text(
            "def a():\n    return 1\n\ndef b():\n    return 2\n\ndef c():\n    return 3\n"
        )

        with patch("code_scalpel.mcp.server._get_current_tier", return_value="community"):
            with patch("code_scalpel.mcp.server.get_tool_capabilities") as mock_caps:
                mock_caps.return_value = {
                    "capabilities": ["basic_neighborhood"],
                    "limits": {"max_k": 1, "max_nodes": 20},
                }

                for func_name in ["a", "b", "c"]:
                    result = await get_graph_neighborhood(
                        center_node_id=f"python::main::function::{func_name}",
                        k=1,
                        max_nodes=20,
                        project_root=str(project_dir),
                    )
                    assert isinstance(result, GraphNeighborhoodResult)


# ============================================================================
# CONCURRENT LOAD TESTS
# ============================================================================


class TestConcurrentLoad:
    """Test handling of concurrent requests."""

    async def test_concurrent_same_node(self, tmp_path):
        """Concurrent requests for same node should all complete."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        (project_dir / "main.py").write_text("def foo():\n    return bar()\n\ndef bar():\n    return 1\n")

        with patch("code_scalpel.mcp.server._get_current_tier", return_value="community"):
            with patch("code_scalpel.mcp.server.get_tool_capabilities") as mock_caps:
                mock_caps.return_value = {
                    "capabilities": ["basic_neighborhood"],
                    "limits": {"max_k": 1, "max_nodes": 20},
                }

                # Launch 10 concurrent requests for same node
                tasks = [
                    get_graph_neighborhood(
                        center_node_id="python::main::function::foo",
                        k=1,
                        max_nodes=20,
                        project_root=str(project_dir),
                    )
                    for _ in range(10)
                ]
                results = await asyncio.gather(*tasks)

                # All should complete
                assert len(results) == 10
                for result in results:
                    assert isinstance(result, GraphNeighborhoodResult)

    async def test_concurrent_different_nodes(self, tmp_path):
        """Concurrent requests for different nodes should all complete."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        (project_dir / "main.py").write_text("\n".join([f"def func_{i}():\n    return {i}\n" for i in range(10)]))

        with patch("code_scalpel.mcp.server._get_current_tier", return_value="pro"):
            with patch("code_scalpel.mcp.server.get_tool_capabilities") as mock_caps:
                mock_caps.return_value = {
                    "capabilities": ["basic_neighborhood", "advanced_neighborhood"],
                    "limits": {"max_k": 5, "max_nodes": 200},
                }

                # Launch concurrent requests for different nodes
                tasks = [
                    get_graph_neighborhood(
                        center_node_id=f"python::main::function::func_{i}",
                        k=1,
                        max_nodes=50,
                        project_root=str(project_dir),
                    )
                    for i in range(10)
                ]
                results = await asyncio.gather(*tasks)

                assert len(results) == 10
                for result in results:
                    assert isinstance(result, GraphNeighborhoodResult)

    async def test_concurrent_mixed_tiers(self, tmp_path):
        """Concurrent requests with different tier limits should not interfere."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        (project_dir / "main.py").write_text("def foo():\n    return bar()\n\ndef bar():\n    return 1\n")

        async def request_community():
            with patch("code_scalpel.mcp.server._get_current_tier", return_value="community"):
                with patch("code_scalpel.mcp.server.get_tool_capabilities") as mock_caps:
                    mock_caps.return_value = {
                        "capabilities": ["basic_neighborhood"],
                        "limits": {"max_k": 1, "max_nodes": 20},
                    }
                    return await get_graph_neighborhood(
                        center_node_id="python::main::function::foo",
                        k=1,
                        max_nodes=20,
                        project_root=str(project_dir),
                    )

        async def request_pro():
            with patch("code_scalpel.mcp.server._get_current_tier", return_value="pro"):
                with patch("code_scalpel.mcp.server.get_tool_capabilities") as mock_caps:
                    mock_caps.return_value = {
                        "capabilities": ["basic_neighborhood", "advanced_neighborhood"],
                        "limits": {"max_k": 5, "max_nodes": 200},
                    }
                    return await get_graph_neighborhood(
                        center_node_id="python::main::function::foo",
                        k=2,
                        max_nodes=100,
                        project_root=str(project_dir),
                    )

        # Mix Community and Pro requests
        tasks = []
        for i in range(10):
            if i % 2 == 0:
                tasks.append(request_community())
            else:
                tasks.append(request_pro())

        results = await asyncio.gather(*tasks)
        assert len(results) == 10
        for result in results:
            assert isinstance(result, GraphNeighborhoodResult)
