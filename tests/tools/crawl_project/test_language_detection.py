"""Test language detection accuracy in crawl_project."""

from code_scalpel.analysis.project_crawler import ProjectCrawler


class TestLanguageDetection:
    """Validate accurate language detection across file extensions."""

    def test_python_detection(self, small_python_extended, community_env):
        """Test that Python files are detected correctly."""
        crawler = ProjectCrawler(str(small_python_extended))
        result = crawler.crawl()

        # Find Python files
        python_files = [f for f in result.files_analyzed if f.language == "python"]
        assert len(python_files) > 0, "No Python files detected"

    def test_multilanguage_detection(self, multilang_project, community_env):
        """Test that multiple languages are detected in mixed project."""
        crawler = ProjectCrawler(str(multilang_project))
        result = crawler.crawl()

        # Get languages detected
        languages = {f.language for f in result.files_analyzed}

        # Should detect multiple languages
        assert len(languages) > 1, f"Expected multiple languages, got {languages}"

    def test_language_count_consistency(self, multilang_project, community_env):
        """Test that language counts are consistent."""
        crawler = ProjectCrawler(str(multilang_project))

        # First run
        result1 = crawler.crawl()
        lang_count1 = {
            lang: sum(1 for f in result1.files_analyzed if f.language == lang)
            for lang in {f.language for f in result1.files_analyzed}
        }

        # Second run
        result2 = crawler.crawl()
        lang_count2 = {
            lang: sum(1 for f in result2.files_analyzed if f.language == lang)
            for lang in {f.language for f in result2.files_analyzed}
        }

        # Language counts should match
        assert lang_count1 == lang_count2, f"Language counts differ: {lang_count1} vs {lang_count2}"

    def test_all_files_have_language(self, multilang_project, community_env):
        """Test that all files have a detected language."""
        crawler = ProjectCrawler(str(multilang_project))
        result = crawler.crawl()

        # All files should have a language
        for f in result.files_analyzed:
            assert f.language, f"File {f.path} has no language detected"

    def test_files_grouped_by_language(self, multilang_project, community_env):
        """Test that files can be grouped and counted by language."""
        crawler = ProjectCrawler(str(multilang_project))
        result = crawler.crawl()

        # Group files by language
        by_language = {}
        for f in result.files_analyzed:
            if f.language not in by_language:
                by_language[f.language] = []
            by_language[f.language].append(f.path)

        # Should have at least 2 languages
        assert len(by_language) >= 2, f"Expected at least 2 languages, got {list(by_language.keys())}"

        # Each group should have files
        for lang, files in by_language.items():
            assert len(files) > 0, f"No files for language {lang}"
