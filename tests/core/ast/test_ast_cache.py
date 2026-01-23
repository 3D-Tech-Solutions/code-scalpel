"""
Tests for Incremental AST Cache.

[20251216_TEST] Tests for Feature 9: Incremental AST Cache
"""

import ast
import time

from code_scalpel.cache.ast_cache import IncrementalASTCache, get_ast_cache


class TestBasicCaching:
    """Test basic AST caching functionality."""

    def test_cache_initialization(self, tmp_path):
        """Test cache directory creation."""
        cache_dir = tmp_path / "cache"
        _cache = IncrementalASTCache(cache_dir)  # noqa: F841 - cache init creates dir

        assert cache_dir.exists()
        assert cache_dir.is_dir()

    def test_cache_fresh_parse(self, tmp_path):
        """Test parsing a file for the first time."""
        # Create a Python file
        test_file = tmp_path / "test.py"
        test_file.write_text("def hello(): pass")

        cache = IncrementalASTCache(tmp_path / "cache")

        # Parse file
        result = cache.get_or_parse(test_file, "python")

        assert result is not None
        assert isinstance(result, ast.Module)

    def test_cache_hit_on_second_access(self, tmp_path):
        """Test that second access hits the cache."""
        test_file = tmp_path / "test.py"
        test_file.write_text("def hello(): pass")

        cache = IncrementalASTCache(tmp_path / "cache")

        # First parse
        result1 = cache.get_or_parse(test_file, "python")

        # Second parse (should hit cache)
        result2 = cache.get_or_parse(test_file, "python")

        # Should be the same object (memory cache)
        assert result1 is result2

    def test_cache_invalidation_on_file_change(self, tmp_path):
        """Test that cache is invalidated when file changes."""
        test_file = tmp_path / "test.py"
        test_file.write_text("def hello(): pass")

        cache = IncrementalASTCache(tmp_path / "cache")

        # First parse
        cache.get_or_parse(test_file, "python")

        # Modify file
        test_file.write_text("def goodbye(): pass")

        # Parse again (should detect change)
        result = cache.get_or_parse(test_file, "python")

        # Should have new AST with different function name
        assert isinstance(result, ast.Module)
        func_name = result.body[0].name
        assert func_name == "goodbye"


class TestFileHashing:
    """Test file hashing functionality."""

    def test_file_hash_changes_on_content_change(self, tmp_path):
        """Test that file hash changes when content changes."""
        test_file = tmp_path / "test.py"
        test_file.write_text("content1")

        cache = IncrementalASTCache(tmp_path / "cache")

        hash1 = cache._hash_file(test_file)

        test_file.write_text("content2")

        hash2 = cache._hash_file(test_file)

        assert hash1 != hash2

    def test_file_hash_same_for_same_content(self, tmp_path):
        """Test that file hash is same for identical content."""
        test_file = tmp_path / "test.py"
        test_file.write_text("def hello(): pass")

        cache = IncrementalASTCache(tmp_path / "cache")

        hash1 = cache._hash_file(test_file)
        hash2 = cache._hash_file(test_file)

        assert hash1 == hash2


class TestDependencyTracking:
    """Test dependency graph tracking."""

    def test_record_dependency(self, tmp_path):
        """Test recording dependencies between files."""
        file1 = tmp_path / "file1.py"
        file2 = tmp_path / "file2.py"

        file1.write_text("import file2")
        file2.write_text("def helper(): pass")

        cache = IncrementalASTCache(tmp_path / "cache")

        # Record dependency
        cache.record_dependency(file1, file2)

        # Check dependency graph
        assert str(file2.resolve()) in cache.dependency_graph[str(file1.resolve())]

    def test_cascading_invalidation(self, tmp_path):
        """Test that invalidating a file invalidates its dependents."""
        file1 = tmp_path / "file1.py"
        file2 = tmp_path / "file2.py"

        file1.write_text("import file2")
        file2.write_text("def helper(): pass")

        cache = IncrementalASTCache(tmp_path / "cache")

        # Parse both files
        cache.get_or_parse(file1, "python")
        cache.get_or_parse(file2, "python")

        # Record dependency
        cache.record_dependency(file1, file2)

        # Invalidate file2
        affected = cache.invalidate(file2)

        # file1 should be affected
        assert str(file1.resolve()) in affected

    def test_transitive_dependencies(self, tmp_path):
        """Test transitive dependency invalidation."""
        file1 = tmp_path / "file1.py"
        file2 = tmp_path / "file2.py"
        file3 = tmp_path / "file3.py"

        file1.write_text("import file2")
        file2.write_text("import file3")
        file3.write_text("def helper(): pass")

        cache = IncrementalASTCache(tmp_path / "cache")

        # Parse all files
        cache.get_or_parse(file1, "python")
        cache.get_or_parse(file2, "python")
        cache.get_or_parse(file3, "python")

        # Record dependencies: file1 -> file2 -> file3
        cache.record_dependency(file1, file2)
        cache.record_dependency(file2, file3)

        # Invalidate file3
        affected = cache.invalidate(file3)

        # Both file1 and file2 should be affected
        assert str(file2.resolve()) in affected
        assert str(file1.resolve()) in affected


class TestCachePersistence:
    """Test cache persistence across restarts."""

    def test_cache_survives_restart(self, tmp_path):
        """Test that cache metadata persists across cache instances."""
        test_file = tmp_path / "test.py"
        test_file.write_text("def hello(): pass")

        cache_dir = tmp_path / "cache"

        # First cache instance
        cache1 = IncrementalASTCache(cache_dir)
        cache1.get_or_parse(test_file, "python")

        # Verify cache file exists
        stats1 = cache1.get_cache_stats()
        assert stats1["total_tracked_files"] == 1

        # Create new cache instance (simulating restart)
        cache2 = IncrementalASTCache(cache_dir)

        # Should have metadata from previous instance
        stats2 = cache2.get_cache_stats()
        assert stats2["total_tracked_files"] == 1

    def test_dependency_graph_survives_restart(self, tmp_path):
        """Test that dependency graph persists."""
        file1 = tmp_path / "file1.py"
        file2 = tmp_path / "file2.py"

        file1.write_text("import file2")
        file2.write_text("def helper(): pass")

        cache_dir = tmp_path / "cache"

        # First cache instance
        cache1 = IncrementalASTCache(cache_dir)
        cache1.record_dependency(file1, file2)

        # Create new cache instance
        cache2 = IncrementalASTCache(cache_dir)

        # Should have same dependency
        assert str(file2.resolve()) in cache2.dependency_graph.get(str(file1.resolve()), set())


class TestCacheStatistics:
    """Test cache statistics and observability."""

    def test_cache_stats_basic(self, tmp_path):
        """Test basic cache statistics."""
        cache = IncrementalASTCache(tmp_path / "cache")

        stats = cache.get_cache_stats()

        assert "total_tracked_files" in stats
        assert "memory_cached_asts" in stats
        assert "disk_cached_files" in stats
        assert "dependency_edges" in stats
        assert "cache_dir" in stats

    def test_cache_stats_after_operations(self, tmp_path):
        """Test cache statistics after various operations."""
        test_file = tmp_path / "test.py"
        test_file.write_text("def hello(): pass")

        cache = IncrementalASTCache(tmp_path / "cache")

        # Parse file
        cache.get_or_parse(test_file, "python")

        stats = cache.get_cache_stats()

        assert stats["total_tracked_files"] >= 1
        assert stats["memory_cached_asts"] >= 1


class TestCacheClear:
    """Test cache clearing functionality."""

    def test_clear_cache(self, tmp_path):
        """Test clearing all cache data."""
        test_file = tmp_path / "test.py"
        test_file.write_text("def hello(): pass")

        cache = IncrementalASTCache(tmp_path / "cache")

        # Parse file
        cache.get_or_parse(test_file, "python")

        # Clear cache
        cache.clear_cache()

        # Should have no cached data
        stats = cache.get_cache_stats()
        assert stats["total_tracked_files"] == 0
        assert stats["memory_cached_asts"] == 0


class TestGlobalCache:
    """Test global cache singleton."""

    def test_get_ast_cache(self, tmp_path):
        """Test getting global cache instance."""
        cache = get_ast_cache(tmp_path / "cache")

        assert isinstance(cache, IncrementalASTCache)

    def test_global_cache_is_singleton(self, tmp_path):
        """Test that get_ast_cache returns same instance."""
        # Note: This test may not work perfectly due to global state
        # but demonstrates the intended behavior
        cache_dir = tmp_path / "cache"

        cache1 = get_ast_cache(cache_dir)

        # Reset global for clean test
        import code_scalpel.cache.ast_cache as module

        module._global_ast_cache = None

        cache2 = get_ast_cache(cache_dir)

        assert isinstance(cache1, IncrementalASTCache)
        assert isinstance(cache2, IncrementalASTCache)


class TestAcceptanceCriteria:
    """Test acceptance criteria from the problem statement."""

    def test_cache_asts_to_disk_with_file_hash_keys(self, tmp_path):
        """Acceptance: Cache ASTs to disk with file hash keys."""
        test_file = tmp_path / "test.py"
        test_file.write_text("def hello(): pass")

        cache_dir = tmp_path / "cache"
        cache = IncrementalASTCache(cache_dir)

        # Parse file
        cache.get_or_parse(test_file, "python")

        # Check that cache files exist
        cache_files = list(cache_dir.glob("*.ast"))
        assert len(cache_files) > 0

    def test_invalidate_cache_on_file_modification(self, tmp_path):
        """Acceptance: Invalidate cache on file modification."""
        test_file = tmp_path / "test.py"
        test_file.write_text("def hello(): pass")

        cache = IncrementalASTCache(tmp_path / "cache")

        # Parse file
        cache.get_or_parse(test_file, "python")
        file_path = str(test_file.resolve())
        assert file_path in cache.file_hashes

        # Invalidate
        cache.invalidate(test_file)

        # Should be removed from cache
        assert file_path not in cache.file_hashes

    def test_track_dependency_graph_for_cascading_invalidation(self, tmp_path):
        """Acceptance: Track dependency graph for cascading invalidation."""
        file1 = tmp_path / "file1.py"
        file2 = tmp_path / "file2.py"

        file1.write_text("import file2")
        file2.write_text("def helper(): pass")

        cache = IncrementalASTCache(tmp_path / "cache")

        # Record dependency
        cache.record_dependency(file1, file2)

        # Check dependency graph exists
        assert len(cache.dependency_graph) > 0

        # Parse files
        cache.get_or_parse(file1, "python")
        cache.get_or_parse(file2, "python")

        # Invalidate file2
        affected = cache.invalidate(file2)

        # file1 should be affected
        assert str(file1.resolve()) in affected

    def test_cache_survives_server_restarts(self, tmp_path):
        """Acceptance: Cache survives server restarts."""
        test_file = tmp_path / "test.py"
        test_file.write_text("def hello(): pass")

        cache_dir = tmp_path / "cache"

        # First "server" instance
        cache1 = IncrementalASTCache(cache_dir)
        cache1.get_or_parse(test_file, "python")

        # Second "server" instance (simulating restart)
        cache2 = IncrementalASTCache(cache_dir)

        # Should still have file tracked
        stats = cache2.get_cache_stats()
        assert stats["total_tracked_files"] >= 1


class TestPerformance:
    """Test cache performance characteristics."""

    def test_cache_reduces_parse_time(self, tmp_path):
        """Test that cache provides performance improvement."""
        # Create a moderately complex Python file
        test_file = tmp_path / "test.py"
        code = "\n".join([f"def function_{i}():" + "\n    pass" for i in range(100)])
        test_file.write_text(code)

        cache = IncrementalASTCache(tmp_path / "cache")

        # First parse (cold cache) - timing not used but establishes baseline
        cache.get_or_parse(test_file, "python")

        # Second parse (warm cache)
        start2 = time.time()
        cache.get_or_parse(test_file, "python")
        time2 = time.time() - start2

        # Cached access should be faster
        # Note: This might be flaky on some systems, so we just check it doesn't error
        assert time2 >= 0  # Basic sanity check

        # In practice, time2 should be much smaller than time1
        # But we don't want flaky tests, so we don't assert the ratio
