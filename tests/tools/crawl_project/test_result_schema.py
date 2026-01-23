"""Test result schema validation and data types."""

import json

import pytest

from code_scalpel.analysis.project_crawler import ProjectCrawler


class TestResultSchema:
    """Validate CrawlResult schema and data types."""

    def test_result_is_serializable(self, small_python_extended):
        """Verify CrawlResult data is JSON-serializable."""
        crawler = ProjectCrawler(str(small_python_extended))
        result = crawler.crawl()

        # Result should be convertible to JSON (via dict)
        try:
            result_dict = {
                "root_path": str(result.root_path),
                "total_files": result.total_files,
                "total_functions": result.total_functions,
                "total_classes": result.total_classes,
            }
            json.dumps(result_dict)
        except TypeError as e:
            pytest.fail(f"Result should be JSON-serializable: {e}")

    def test_file_analysis_result_types(self, small_python_extended):
        """Verify FileAnalysisResult has correct field types."""
        crawler = ProjectCrawler(str(small_python_extended))
        result = crawler.crawl()

        for file_result in result.files_analyzed:
            assert isinstance(file_result.path, (str, type(None)))
            assert isinstance(file_result.language, (str, type(None)))
            assert isinstance(file_result.status, (str, type(None)))
            assert isinstance(file_result.lines_of_code, (int, type(None)))
            assert isinstance(file_result.complexity_score, (int, float, type(None)))

    def test_summary_dictionary_format(self, small_python_extended):
        """Verify summary is a valid dictionary."""
        crawler = ProjectCrawler(str(small_python_extended))
        result = crawler.crawl()

        assert isinstance(result.summary, dict)
        # Summary should have string keys
        for key in result.summary.keys():
            assert isinstance(key, str)

    def test_lists_not_none(self, small_python_extended):
        """Verify files_analyzed and similar lists are not None."""
        crawler = ProjectCrawler(str(small_python_extended))
        result = crawler.crawl()

        assert result.files_analyzed is not None
        assert isinstance(result.files_analyzed, list)

    def test_numeric_fields_are_integers(self, small_python_extended):
        """Verify numeric summary fields are integers."""
        crawler = ProjectCrawler(str(small_python_extended))
        result = crawler.crawl()

        assert isinstance(result.total_files, int)
        assert isinstance(result.total_functions, int)
        assert isinstance(result.total_classes, int)
        assert result.total_files >= 0
        assert result.total_functions >= 0
        assert result.total_classes >= 0

    def test_file_lists_consistency(self, small_python_extended):
        """Verify files_analyzed and errors lists are consistent."""
        crawler = ProjectCrawler(str(small_python_extended))
        result = crawler.crawl()

        # Both should be lists
        assert isinstance(result.files_analyzed, list)
        if hasattr(result, "files_with_errors"):
            assert isinstance(result.files_with_errors, list)

    def test_timestamp_format(self, small_python_extended):
        """Verify timestamp is present and valid."""
        crawler = ProjectCrawler(str(small_python_extended))
        result = crawler.crawl()

        assert result.timestamp is not None
        # Timestamp should be numeric (epoch) or ISO format string
        assert isinstance(result.timestamp, (int, float, str))
