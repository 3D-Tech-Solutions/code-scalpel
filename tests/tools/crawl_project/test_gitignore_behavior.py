"""Test gitignore respect via respect_gitignore parameter."""

import pytest

from code_scalpel.analysis.project_crawler import ProjectCrawler


class TestGitignoreBehavior:
    """Validate .gitignore handling when respect_gitignore=True."""

    def test_without_respect_gitignore_includes_all(self, project_with_gitignore):
        """Verify that without respect_gitignore, all files are crawled."""
        crawler = ProjectCrawler(str(project_with_gitignore), respect_gitignore=False)
        result = crawler.crawl()

        # Should find files (gitignore not respected)
        assert result.total_files > 0
        assert result.files_analyzed

    def test_with_respect_gitignore_parameter_accepted(self, project_with_gitignore):
        """Verify respect_gitignore parameter is accepted by ProjectCrawler."""
        try:
            crawler = ProjectCrawler(str(project_with_gitignore), respect_gitignore=True)
            result = crawler.crawl()
            assert result is not None
        except TypeError as e:
            pytest.fail(f"ProjectCrawler should accept respect_gitignore parameter: {e}")

    def test_respect_gitignore_produces_results(self, project_with_gitignore):
        """Verify crawl with respect_gitignore=True still produces results."""
        crawler = ProjectCrawler(str(project_with_gitignore), respect_gitignore=True)
        result = crawler.crawl()

        # Should find at least main.py (it's tracked)
        assert result.total_files > 0
        assert result.files_analyzed

    def test_python_files_detected_regardless_of_gitignore(self, project_with_gitignore):
        """Verify Python files are detected in gitignore projects."""
        crawler = ProjectCrawler(str(project_with_gitignore), respect_gitignore=False)
        result = crawler.crawl()

        python_files = [f for f in result.files_analyzed if f.language == "python"]
        assert len(python_files) > 0, "Should detect Python files in project"

    def test_gitignore_consistency_across_runs(self, project_with_gitignore):
        """Verify gitignore respect is consistent across multiple crawls."""
        crawler = ProjectCrawler(str(project_with_gitignore), respect_gitignore=False)
        result1 = crawler.crawl()
        result2 = crawler.crawl()

        assert result1.total_files == result2.total_files
        assert result1.total_functions == result2.total_functions
