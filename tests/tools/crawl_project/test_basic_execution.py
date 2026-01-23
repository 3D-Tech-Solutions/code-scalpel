"""Test basic ProjectCrawler tool execution and functionality."""

import pytest

from code_scalpel.analysis.project_crawler import ProjectCrawler


class TestBasicExecution:
    """Test core ProjectCrawler invocation and happy path."""

    def test_tool_invocation_with_minimal_params(self, small_python_extended):
        """Verify ProjectCrawler can be invoked with just root_path."""
        crawler = ProjectCrawler(str(small_python_extended))
        result = crawler.crawl()

        assert result is not None
        assert hasattr(result, "files_analyzed")
        assert hasattr(result, "total_files")

    def test_happy_path_crawl_small_project(self, small_python_extended):
        """Verify happy path: crawl completes, returns results."""
        crawler = ProjectCrawler(str(small_python_extended))
        result = crawler.crawl()

        # Basic assertions about the crawl
        assert result.files_analyzed
        assert result.total_files >= 4  # main.py, utils.py, config.py, test_utils.py
        assert result.total_functions >= 2  # At least some functions
        assert result.timestamp is not None

    def test_error_handling_nonexistent_path(self):
        """Verify ProjectCrawler raises error for nonexistent path."""
        nonexistent = "/nonexistent/path/to/project"

        # ProjectCrawler should raise ValueError for nonexistent paths
        with pytest.raises(ValueError):
            ProjectCrawler(nonexistent)

    def test_result_contains_required_fields(self, small_python_extended):
        """Verify CrawlResult contains all required fields."""
        crawler = ProjectCrawler(str(small_python_extended))
        result = crawler.crawl()

        required_fields = [
            "root_path",
            "timestamp",
            "total_files",
            "total_functions",
            "total_classes",
        ]
        for field in required_fields:
            assert hasattr(result, field), f"Result missing required field: {field}"

    def test_file_analysis_contains_required_fields(self, small_python_extended):
        """Verify FileAnalysisResult contains required fields for each file."""
        crawler = ProjectCrawler(str(small_python_extended))
        result = crawler.crawl()

        assert result.files_analyzed, "Should have analyzed files"
        required_fields = ["path", "language", "status"]
        for file_result in result.files_analyzed:
            for field in required_fields:
                assert hasattr(file_result, field), f"FileAnalysisResult missing required field: {field}"
