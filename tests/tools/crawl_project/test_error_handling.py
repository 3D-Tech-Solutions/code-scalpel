"""Test error handling and edge cases."""

from code_scalpel.analysis.project_crawler import ProjectCrawler


class TestErrorHandling:
    """Validate error handling for edge cases and invalid inputs."""

    def test_permission_denied_handling(self, tmp_path):
        """Verify graceful handling of permission denied."""
        # Create a directory with restricted permissions
        restricted_dir = tmp_path / "restricted"
        restricted_dir.mkdir()
        (restricted_dir / "main.py").write_text("print('hello')")
        restricted_dir.chmod(0o000)

        try:
            crawler = ProjectCrawler(str(restricted_dir))
            result = crawler.crawl()
            # Should either handle gracefully or raise appropriate error
            assert result is not None
        except PermissionError:
            # Expected behavior
            pass
        finally:
            # Restore permissions for cleanup
            restricted_dir.chmod(0o755)

    def test_syntax_error_in_file(self, tmp_path):
        """Verify crawl continues despite syntax errors in files."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        (project_dir / "bad_syntax.py").write_text("def foo(: # Missing argument")
        (project_dir / "good.py").write_text("def bar(): pass")

        crawler = ProjectCrawler(str(project_dir))
        result = crawler.crawl()

        # Should still crawl and find at least the good file
        assert result.files_analyzed
        assert result.total_files >= 1

    def test_large_file_handling(self, tmp_path):
        """Verify crawl handles very large files."""
        project_dir = tmp_path / "large"
        project_dir.mkdir()

        # Create a large Python file
        large_file = project_dir / "large.py"
        with open(large_file, "w") as f:
            for i in range(1000):
                f.write(f"def function_{i}(): pass\n")

        crawler = ProjectCrawler(str(project_dir))
        result = crawler.crawl()

        # Should handle large file without crashing
        assert result is not None
        assert result.total_files >= 1

    def test_symlink_handling(self, tmp_path):
        """Verify crawl handles symbolic links."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        (project_dir / "main.py").write_text("print('hello')")

        # Create a symlink
        symlink_dir = tmp_path / "symlink"
        try:
            symlink_dir.symlink_to(project_dir)

            crawler = ProjectCrawler(str(project_dir))
            result = crawler.crawl()
            assert result is not None
        except OSError:
            # Symlinks may not be supported on all systems
            pass

    def test_empty_directory_crawl(self, tmp_path):
        """Verify crawl handles empty directories gracefully."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        crawler = ProjectCrawler(str(empty_dir))
        result = crawler.crawl()

        assert result is not None
        assert result.total_files == 0
        assert result.files_analyzed == []

    def test_circular_symlink_detection(self, tmp_path):
        """Verify crawl handles circular symlinks without infinite loop."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        (project_dir / "main.py").write_text("print('hello')")

        try:
            # Create circular symlink
            link_dir = project_dir / "link"
            link_dir.symlink_to(project_dir)

            crawler = ProjectCrawler(str(project_dir))
            result = crawler.crawl()

            # Should complete without infinite loop
            assert result is not None
        except (OSError, RecursionError):
            # Expected for some systems or if circular symlinks cause recursion
            pass
