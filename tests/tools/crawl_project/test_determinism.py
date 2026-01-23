"""Test determinism of crawl_project - results should be consistent across runs."""

from code_scalpel.analysis.project_crawler import ProjectCrawler


class TestDeterminism:
    """Validate that crawl_project produces consistent results."""

    def test_two_crawls_same_file_count(self, small_python_extended, community_env):
        """Test that two crawls return identical file counts.

        This is critical for production - crawl_project must produce
        deterministic results regardless of filesystem state.
        """

        crawler = ProjectCrawler(str(small_python_extended))

        # First crawl
        result1 = crawler.crawl()
        files1 = result1.total_files
        functions1 = result1.total_functions
        classes1 = result1.total_classes

        # Second crawl (immediately after)
        result2 = crawler.crawl()
        files2 = result2.total_files
        functions2 = result2.total_functions
        classes2 = result2.total_classes

        # Validate identical results
        assert files1 == files2, f"File count differs: {files1} vs {files2}"
        assert functions1 == functions2, f"Function count differs: {functions1} vs {functions2}"
        assert classes1 == classes2, f"Class count differs: {classes1} vs {classes2}"

    def test_language_detection_consistent(self, multilang_project, community_env):
        """Test that language detection is consistent across runs."""
        crawler = ProjectCrawler(str(multilang_project))

        # First run
        result1 = crawler.crawl()
        languages1 = sorted([f.language for f in result1.files_analyzed])

        # Second run
        result2 = crawler.crawl()
        languages2 = sorted([f.language for f in result2.files_analyzed])

        # Language list should be identical
        assert languages1 == languages2, f"Languages differ:\n  Run 1: {languages1}\n  Run 2: {languages2}"

    def test_file_ordering_consistent(self, small_python_extended, community_env):
        """Test that files are processed in consistent order.

        File ordering affects hash computation and cache consistency.
        Must be deterministic regardless of filesystem.
        """
        crawler = ProjectCrawler(str(small_python_extended))

        # First crawl
        result1 = crawler.crawl()
        files1 = sorted([f.path for f in result1.files_analyzed])

        # Second crawl
        result2 = crawler.crawl()
        files2 = sorted([f.path for f in result2.files_analyzed])

        # Files should be in identical order
        assert files1 == files2, f"File order differs:\n  {files1}\n  vs\n  {files2}"

    def test_complexity_scores_consistent(self, small_python_extended, community_env):
        """Test that complexity scores are stable across runs.

        Complexity calculation must be deterministic.
        """
        crawler = ProjectCrawler(str(small_python_extended))

        # First crawl
        result1 = crawler.crawl()
        complexity1 = {f.path: f.complexity_score for f in result1.files_analyzed}

        # Second crawl
        result2 = crawler.crawl()
        complexity2 = {f.path: f.complexity_score for f in result2.files_analyzed}

        # Complexity scores should match
        assert complexity1 == complexity2, f"Complexity differs:\n  {complexity1}\n  vs\n  {complexity2}"
