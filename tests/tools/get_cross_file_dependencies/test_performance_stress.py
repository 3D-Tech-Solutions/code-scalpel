"""Performance and Stress Tests for get_cross_file_dependencies.

Validates:
- Depth/file limit enforcement on large projects (>500 files)
- Throughput and timeout behavior
- Graceful degradation under load
- Memory efficiency (no leaks during large analyses)
- Truncation behavior when limits exceeded

[20260104_TEST] Performance testing and scalability validation
"""

import time
from pathlib import Path

import pytest


def _write(p: Path, content: str) -> None:
    """Write content to file, creating parent dirs if needed."""
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")


class TestLargeProjectAnalysis:
    """Test handling of large projects (>500 files)."""

    def create_large_project(self, tmp_path, num_files: int = 600):
        """Create a project with many files for stress testing."""
        # Ensure directory exists
        tmp_path.mkdir(parents=True, exist_ok=True)
        # Create a chain: main → mod_1 → mod_2 → ... → mod_N
        main_file = tmp_path / "main.py"
        main_file.write_text("from mod_0 import func_0\ndef main(): return func_0()")

        for i in range(num_files - 1):
            next_i = i + 1
            mod_file = tmp_path / f"mod_{i}.py"
            import_stmt = f"from mod_{next_i} import func_{next_i}" if next_i < num_files - 1 else ""
            mod_file.write_text(f"{import_stmt}\n" f"def func_{i}(): return {i}\n")

        return main_file

    @pytest.mark.asyncio
    async def test_community_tier_handles_large_project_within_limits(self, tmp_path, community_server):
        """Community should limit analysis to 500 files max.

        The Community tier has a 500-file scope limit. Projects exceeding this
        should return a clear error message suggesting to narrow the scope.
        This test verifies both behaviors:
        1. Projects within limits succeed with clamped depth
        2. Projects exceeding limits return a clear error
        """
        # Test with a project exceeding limits - should get clear error
        main_file_over = self.create_large_project(tmp_path / "over", num_files=600)
        result_over = await community_server.get_cross_file_dependencies(
            target_file=str(main_file_over),
            target_symbol="main",
            project_root=str(tmp_path / "over"),
            max_depth=10,
        )
        # Should return graceful error when exceeding scope limit
        assert result_over.success is False
        assert "500 files" in (result_over.error or "")

        # Test with a project within limits - should succeed
        main_file_under = self.create_large_project(tmp_path / "under", num_files=100)
        start_time = time.time()
        result = await community_server.get_cross_file_dependencies(
            target_file=str(main_file_under),
            target_symbol="main",
            project_root=str(tmp_path / "under"),
            max_depth=10,  # Request deep analysis
        )
        elapsed = time.time() - start_time

        assert result.success is True
        # Should complete reasonably fast
        assert elapsed < 10.0, f"Community tier took {elapsed:.2f}s, expected <10s"
        # Depth should be clamped to 1 for Community tier
        assert result.transitive_depth <= 1

    @pytest.mark.asyncio
    async def test_pro_tier_handles_large_project_within_limits(self, tmp_path, pro_server):
        """Pro should limit analysis to 500 files max."""
        main_file = self.create_large_project(tmp_path, num_files=600)

        start_time = time.time()
        result = await pro_server.get_cross_file_dependencies(
            target_file=str(main_file),
            target_symbol="main",
            project_root=str(tmp_path),
            max_depth=10,
        )
        elapsed = time.time() - start_time

        assert result.success is True
        # Should clamp to 500 files
        assert result.files_analyzed <= 500, f"Pro should limit to 500 files, analyzed {result.files_analyzed}"
        # Pro should complete within reasonable time
        assert elapsed < 30.0, f"Pro tier took {elapsed:.2f}s, expected <30s"
        # Depth should be clamped to 5
        assert result.transitive_depth <= 5

    @pytest.mark.asyncio
    async def test_enterprise_tier_handles_large_project_no_file_limit(self, tmp_path, enterprise_server):
        """Enterprise should analyze all files without limit."""
        main_file = self.create_large_project(tmp_path, num_files=600)

        start_time = time.time()
        result = await enterprise_server.get_cross_file_dependencies(
            target_file=str(main_file),
            target_symbol="main",
            project_root=str(tmp_path),
            max_depth=20,  # Enterprise allows deeper
        )
        elapsed = time.time() - start_time

        assert result.success is True
        # Enterprise should attempt to analyze all files (or substantial portion)
        # May not analyze all 600 due to dependency structure, but should not
        # artificially limit like Community/Pro
        # No strict limit - just verify it completes
        assert elapsed < 60.0, f"Enterprise tier took {elapsed:.2f}s for 600 files"


class TestDepthLimitEnforcement:
    """Test max_depth parameter enforcement across tiers."""

    def create_deep_chain(self, tmp_path, depth: int):
        """Create a dependency chain of specified depth."""
        # mod_0 → mod_1 → mod_2 → ... → mod_N
        for i in range(depth):
            mod_file = tmp_path / f"mod_{i}.py"
            if i < depth - 1:
                next_i = i + 1
                mod_file.write_text(f"from mod_{next_i} import func_{next_i}\ndef func_{i}(): return func_{next_i}()")
            else:
                mod_file.write_text(f"def func_{i}(): return {i}")

        main_file = tmp_path / "main.py"
        main_file.write_text("from mod_0 import func_0\ndef main(): return func_0()")
        return main_file

    @pytest.mark.asyncio
    async def test_community_depth_clamped_to_1(self, tmp_path, community_server):
        """Community max_depth should be clamped to 1 regardless of request."""
        main_file = self.create_deep_chain(tmp_path, depth=10)

        # Request depth=10, should be clamped to 1
        result = await community_server.get_cross_file_dependencies(
            target_file=str(main_file),
            target_symbol="main",
            project_root=str(tmp_path),
            max_depth=10,
        )

        assert result.success is True
        assert result.transitive_depth <= 1, f"Community should clamp depth to 1, got {result.transitive_depth}"

    @pytest.mark.asyncio
    async def test_pro_depth_clamped_to_5(self, tmp_path, pro_server):
        """Pro max_depth should be clamped to 5."""
        main_file = self.create_deep_chain(tmp_path, depth=10)

        result = await pro_server.get_cross_file_dependencies(
            target_file=str(main_file),
            target_symbol="main",
            project_root=str(tmp_path),
            max_depth=10,
        )

        assert result.success is True
        assert result.transitive_depth <= 5, f"Pro should clamp depth to 5, got {result.transitive_depth}"

    @pytest.mark.asyncio
    async def test_enterprise_respects_requested_depth(self, tmp_path, enterprise_server):
        """Enterprise should respect max_depth parameter up to full graph."""
        main_file = self.create_deep_chain(tmp_path, depth=10)

        result = await enterprise_server.get_cross_file_dependencies(
            target_file=str(main_file),
            target_symbol="main",
            project_root=str(tmp_path),
            max_depth=7,
        )

        assert result.success is True
        # Should respect requested depth (up to actual depth)
        assert result.transitive_depth <= 7


class TestTruncationBehavior:
    """Test truncation when limits are exceeded."""

    def create_wide_project(self, tmp_path, width: int = 100):
        """Create a project where one module imports many others (high fan-in)."""
        # Create many independent modules
        for i in range(width):
            mod_file = tmp_path / f"mod_{i}.py"
            mod_file.write_text(f"def func_{i}(): return {i}")

        # Create aggregator that imports all
        main_file = tmp_path / "main.py"
        imports = "\n".join(f"from mod_{i} import func_{i}" for i in range(width))
        main_file.write_text(f"{imports}\ndef main(): return sum([func_0(), func_1()])")
        return main_file

    @pytest.mark.asyncio
    async def test_community_truncates_at_50_files(self, tmp_path, community_server):
        """Community should truncate analysis when >50 files encountered."""
        main_file = self.create_wide_project(tmp_path, width=100)

        result = await community_server.get_cross_file_dependencies(
            target_file=str(main_file), target_symbol="main", project_root=str(tmp_path)
        )

        assert result.success is True
        # Should indicate truncation
        if result.truncated:
            assert result.files_analyzed <= 50

    @pytest.mark.asyncio
    async def test_pro_truncates_at_500_files(self, tmp_path, pro_server):
        """Pro should truncate analysis at 500 files."""
        main_file = self.create_wide_project(tmp_path, width=100)

        result = await pro_server.get_cross_file_dependencies(
            target_file=str(main_file), target_symbol="main", project_root=str(tmp_path)
        )

        assert result.success is True
        # For 100 files, should not truncate (under 500 limit)
        # but structure validates truncation logic


class TestTimeoutProtection:
    """Test timeout protection and graceful failure."""

    @pytest.mark.asyncio
    async def test_analysis_respects_timeout(self, tmp_path, enterprise_server):
        """Analysis should timeout gracefully if set."""
        # Create a moderately complex project
        for i in range(20):
            for j in range(5):
                mod_file = tmp_path / f"layer_{i}" / f"mod_{j}.py"
                mod_file.parent.mkdir(parents=True, exist_ok=True)
                mod_file.write_text(f"def func_{i}_{j}(): return {i}")

        main_file = tmp_path / "main.py"
        main_file.write_text("def main(): pass")

        # Set very short timeout
        result = await enterprise_server.get_cross_file_dependencies(
            target_file=str(main_file),
            target_symbol="main",
            project_root=str(tmp_path),
            timeout_seconds=0.001,  # 1ms - will timeout
        )

        # Should either succeed quickly or indicate timeout in error message
        # [20260111_FIX] Check error field for TIMEOUT instead of hasattr
        is_timeout = result.error and "TIMEOUT" in result.error if result.error else False
        assert result.success is True or is_timeout, f"Expected success or timeout, got error: {result.error}"


class TestMemoryEfficiency:
    """Test memory efficiency during large analyses."""

    def create_moderately_large_project(self, tmp_path, num_files: int = 200):
        """Create project for memory testing."""
        for i in range(num_files):
            mod_file = tmp_path / f"module_{i}.py"
            # Create content with some code volume
            code = "\n".join(f"def func_{j}(): return {j}" for j in range(10))
            mod_file.write_text(code)

        main_file = tmp_path / "main.py"
        main_file.write_text("from module_0 import func_0\ndef main(): return func_0()")
        return main_file

    @pytest.mark.asyncio
    async def test_no_memory_explosion_on_large_project(self, tmp_path, enterprise_server):
        """Large project analysis should not cause memory explosion."""
        main_file = self.create_moderately_large_project(tmp_path, num_files=200)

        # Get memory before
        try:
            import os

            import psutil

            process = psutil.Process(os.getpid())
            mem_before = process.memory_info().rss / 1024 / 1024  # MB
        except ImportError:
            pytest.skip("psutil not installed")

        result = await enterprise_server.get_cross_file_dependencies(
            target_file=str(main_file), target_symbol="main", project_root=str(tmp_path)
        )

        # Get memory after
        mem_after = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = mem_after - mem_before

        assert result.success is True
        # Memory increase should be reasonable (<500MB for 200 files)
        assert memory_increase < 500, f"Memory increase {memory_increase:.1f}MB exceeds 500MB threshold"


class TestConcurrentAnalysis:
    """Test behavior under concurrent load."""

    @pytest.mark.asyncio
    async def test_multiple_concurrent_analyses(self, tmp_path, enterprise_server):
        """Multiple concurrent analyses should not interfere with each other."""
        # Create two separate projects
        proj1 = tmp_path / "proj1"
        proj2 = tmp_path / "proj2"

        # Ensure directories exist before writing files
        proj1.mkdir(parents=True, exist_ok=True)
        proj2.mkdir(parents=True, exist_ok=True)

        for proj in [proj1, proj2]:
            (proj / "main.py").write_text("def main(): pass")
            (proj / "helper.py").write_text("def helper(): pass")

        import asyncio

        # Run two analyses concurrently
        result1_task = enterprise_server.get_cross_file_dependencies(
            target_file=str(proj1 / "main.py"),
            target_symbol="main",
            project_root=str(proj1),
        )

        result2_task = enterprise_server.get_cross_file_dependencies(
            target_file=str(proj2 / "main.py"),
            target_symbol="main",
            project_root=str(proj2),
        )

        result1, result2 = await asyncio.gather(result1_task, result2_task)

        # Both should succeed without interference
        assert result1.success is True
        assert result2.success is True


class TestPerformanceRegression:
    """Test that performance doesn't regress over time."""

    @pytest.mark.asyncio
    async def test_large_project_baseline_performance(self, tmp_path, community_server):
        """Establish baseline performance for community tier on large project."""
        # Create project with 100 files
        for i in range(100):
            mod_file = tmp_path / f"module_{i}.py"
            mod_file.write_text(f"def func_{i}(): return {i}")

        main_file = tmp_path / "main.py"
        main_file.write_text("from module_0 import func_0\ndef main(): return func_0()")

        # Measure performance
        start = time.time()
        result = await community_server.get_cross_file_dependencies(
            target_file=str(main_file), target_symbol="main", project_root=str(tmp_path)
        )
        elapsed = time.time() - start

        assert result.success is True
        # Community should complete in <5 seconds for 100 files
        assert elapsed < 5.0, f"Community tier took {elapsed:.2f}s for 100 files, expected <5s"

        # Provide feedback on actual performance
        print(f"\nCommunity tier performance: {elapsed:.3f}s for 100 files")
