"""Test cache functionality when enabled via enable_cache parameter."""

import pytest

from code_scalpel.analysis.project_crawler import ProjectCrawler


class TestCacheLifecycle:
    """Validate cache parameter acceptance and basic behavior."""

    def test_crawl_with_cache_enabled_completes(self, small_python_extended):
        """Verify crawl completes successfully with enable_cache=True."""
        crawler = ProjectCrawler(str(small_python_extended), enable_cache=True)
        result = crawler.crawl()

        assert result is not None
        assert result.files_analyzed
        assert result.total_files > 0

    def test_crawl_without_cache_enabled_completes(self, small_python_extended):
        """Verify crawl completes successfully with enable_cache=False (default)."""
        crawler = ProjectCrawler(str(small_python_extended), enable_cache=False)
        result = crawler.crawl()

        assert result is not None
        assert result.files_analyzed
        assert result.total_files > 0

    def test_cached_and_uncached_produce_same_file_count(self, small_python_extended):
        """Verify cached crawl produces same results as uncached crawl."""
        crawler_cached = ProjectCrawler(str(small_python_extended), enable_cache=True)
        result_cached = crawler_cached.crawl()

        crawler_uncached = ProjectCrawler(str(small_python_extended), enable_cache=False)
        result_uncached = crawler_uncached.crawl()

        assert result_cached.total_files == result_uncached.total_files
        assert result_cached.total_functions == result_uncached.total_functions
        assert result_cached.total_classes == result_uncached.total_classes

    def test_cache_parameter_accepted_without_error(self, small_python_extended):
        """Verify enable_cache parameter is accepted by ProjectCrawler."""
        # This should not raise an error even if cache is not fully implemented
        try:
            crawler = ProjectCrawler(str(small_python_extended), enable_cache=True)
            result = crawler.crawl()
            assert result is not None
        except TypeError as e:
            pytest.fail(f"ProjectCrawler should accept enable_cache parameter: {e}")
