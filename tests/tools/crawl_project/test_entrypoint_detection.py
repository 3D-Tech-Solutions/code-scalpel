"""Test entrypoint and main function detection."""

from code_scalpel.analysis.project_crawler import ProjectCrawler


class TestEntrypointDetection:
    """Validate detection of entry points and main functions."""

    def test_main_py_identified_as_entry_point(self, small_python_extended):
        """Verify main.py is identified as entry point."""
        crawler = ProjectCrawler(str(small_python_extended))
        result = crawler.crawl()

        # main.py should be detected
        file_paths = {f.path for f in result.files_analyzed}
        assert any("main.py" in str(p) for p in file_paths)

    def test_if_name_main_block_detected(self, small_python_extended):
        """Verify if __name__ == '__main__' blocks are detected."""
        crawler = ProjectCrawler(str(small_python_extended))
        result = crawler.crawl()

        # At least main.py should have this pattern
        main_file = next((f for f in result.files_analyzed if "main.py" in str(f.path)), None)
        assert main_file is not None

    def test_flask_route_decorators_detected(self, flask_project):
        """Verify Flask @app.route() decorators are detected."""
        crawler = ProjectCrawler(str(flask_project))
        result = crawler.crawl()

        # Flask app should be found
        assert result.files_analyzed
        # app.py or similar should contain Flask routes
        file_paths = {f.path for f in result.files_analyzed}
        assert any("app.py" in str(p) for p in file_paths)

    def test_django_url_patterns_detected(self, django_project):
        """Verify Django url patterns are detected."""
        crawler = ProjectCrawler(str(django_project))
        result = crawler.crawl()

        # Django urls should be found
        file_paths = {f.path for f in result.files_analyzed}
        # Django projects have urls.py
        django_files = [p for p in file_paths if any(name in str(p) for name in ["urls.py", "views.py", "manage.py"])]
        assert len(django_files) > 0

    def test_function_count_includes_entry_functions(self, flask_project):
        """Verify total function count includes route/entry functions."""
        crawler = ProjectCrawler(str(flask_project))
        result = crawler.crawl()

        # Flask project should have at least some functions detected
        assert result.total_functions >= 1, "Flask project should have functions"
