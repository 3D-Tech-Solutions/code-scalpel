# [20260108_TEST] Enterprise repository-wide rename optimization tests
"""
Tests for Enterprise-tier repository-wide rename optimization.

Verifies performance optimizations for large-scale operations:
- Parallel file processing
- Memory-efficient iteration
- Progress reporting
- Intelligent file filtering
- Batch processing
"""

from pathlib import Path

import pytest

from code_scalpel.surgery.repo_wide import RepoWideRename, RepoWideRenameResult


class TestRepoWideBasics:
    """Test basic repo-wide rename functionality."""

    def test_repo_wide_result_creation(self):
        """RepoWideRenameResult can be created."""
        result = RepoWideRenameResult()
        assert result.files_scanned == 0
        assert result.files_updated == 0
        assert result.files_skipped == 0
        assert result.files_failed == 0
        assert result.total_replacements == 0
        assert result.duration_seconds == 0.0
        assert result.errors == []
        assert result.warnings == []

    def test_repo_wide_rename_init(self, temp_project):
        """RepoWideRename can be initialized."""
        renamer = RepoWideRename(project_root=temp_project, max_workers=4, batch_size=50)

        assert renamer.project_root == temp_project
        assert renamer.max_workers == 4
        assert renamer.batch_size == 50

    def test_repo_wide_rename_default_workers(self, temp_project):
        """RepoWideRename uses CPU count by default."""
        renamer = RepoWideRename(project_root=temp_project)
        assert renamer.max_workers >= 1  # At least 1 worker


class TestFileFiltering:
    """Test file filtering and skip logic."""

    def test_skip_binary_files(self, temp_project):
        """Binary files are skipped."""
        renamer = RepoWideRename(project_root=temp_project)

        # Test various binary extensions
        binary_files = [
            Path("test.pyc"),
            Path("lib.so"),
            Path("app.exe"),
            Path("image.png"),
            Path("doc.pdf"),
        ]

        for file_path in binary_files:
            should_skip, reason = renamer.should_skip_file(file_path)
            assert should_skip is True
            assert "binary" in reason

    def test_skip_directories(self, temp_project):
        """Files in skip directories are skipped."""
        renamer = RepoWideRename(project_root=temp_project)

        skip_paths = [
            Path("__pycache__/module.py"),
            Path(".git/config"),
            Path("node_modules/package.json"),
            Path("venv/lib/python3.10/site.py"),
        ]

        for file_path in skip_paths:
            should_skip, reason = renamer.should_skip_file(file_path)
            assert should_skip is True
            assert "directory" in reason or "." in reason

    def test_allow_python_files(self, temp_project):
        """Python files are not skipped."""
        renamer = RepoWideRename(project_root=temp_project)

        # Create actual file so stat() doesn't fail
        src_dir = temp_project / "src"
        src_dir.mkdir(exist_ok=True)
        py_file = src_dir / "module.py"
        py_file.write_text("# Test module")

        should_skip, reason = renamer.should_skip_file(py_file)
        assert should_skip is False
        assert reason is None

    def test_is_text_file_detection(self, temp_project):
        """Text file detection works."""
        renamer = RepoWideRename(project_root=temp_project)

        # Create a text file
        text_file = temp_project / "test.txt"
        text_file.write_text("Hello, world!")

        assert renamer.is_text_file(text_file) is True


class TestCandidateFileFinding:
    """Test finding candidate files for rename."""

    def test_find_python_files(self, temp_project):
        """Finds Python files in project."""
        renamer = RepoWideRename(project_root=temp_project)

        # temp_project fixture creates main.py, utils.py, helper.py
        candidates = renamer.find_candidate_files(file_extensions={".py"})

        # Should find at least the main.py file
        assert len(candidates) >= 1
        assert all(f.suffix == ".py" for f in candidates)

    def test_find_files_with_progress(self, temp_project):
        """Progress callback is invoked during file search."""
        renamer = RepoWideRename(project_root=temp_project)

        progress_calls = []

        def track_progress(count):
            progress_calls.append(count)

        # Create many files to trigger progress callback
        for i in range(150):
            (temp_project / f"file{i}.py").write_text(f"# File {i}")

        candidates = renamer.find_candidate_files(file_extensions={".py"}, progress_callback=track_progress)

        # Should have found at least 150 files
        assert len(candidates) >= 150

        # Progress callback should have been called (every 100 files)
        assert len(progress_calls) >= 1

    def test_find_files_skips_pycache(self, temp_project):
        """__pycache__ directories are skipped."""
        renamer = RepoWideRename(project_root=temp_project)

        # Create __pycache__ directory
        pycache = temp_project / "__pycache__"
        pycache.mkdir(exist_ok=True)
        (pycache / "test.pyc").write_bytes(b"compiled")

        candidates = renamer.find_candidate_files(file_extensions={".py", ".pyc"})

        # Should not find .pyc files in __pycache__
        assert not any("__pycache__" in str(f) for f in candidates)


class TestSymbolSearch:
    """Test searching for symbols in files."""

    def test_search_file_finds_symbol(self, temp_project):
        """Searching finds symbol in file."""
        renamer = RepoWideRename(project_root=temp_project)

        test_file = temp_project / "search_test.py"
        test_file.write_text("def my_function():\n    pass\n")

        assert renamer.search_file_for_symbol(test_file, "my_function") is True
        assert renamer.search_file_for_symbol(test_file, "nonexistent") is False

    def test_search_handles_unicode_errors(self, temp_project):
        """Search handles files with encoding issues."""
        renamer = RepoWideRename(project_root=temp_project)

        test_file = temp_project / "binary.dat"
        test_file.write_bytes(b"\xff\xfe\x00\x00invalid")

        # Should not crash, returns False
        result = renamer.search_file_for_symbol(test_file, "test")
        assert result is False


class TestBatchProcessing:
    """Test parallel batch processing."""

    def test_process_file_batch(self, temp_project):
        """File batch processing works."""
        renamer = RepoWideRename(project_root=temp_project)

        # Create test files
        file1 = temp_project / "file1.py"
        file1.write_text("def target_func(): pass")

        file2 = temp_project / "file2.py"
        file2.write_text("def other_func(): pass")

        batch = [file1, file2]
        result = renamer.process_file_batch(batch, "target_func")

        assert result["files_scanned"] == 2
        assert len(result["files_with_symbol"]) == 1
        assert file1 in result["files_with_symbol"]
        assert file2 not in result["files_with_symbol"]

    def test_batch_handles_errors(self, temp_project):
        """Batch processing handles file errors."""
        renamer = RepoWideRename(project_root=temp_project)

        # Include non-existent file
        nonexistent = temp_project / "nonexistent.py"

        batch = [nonexistent]
        result = renamer.process_file_batch(batch, "symbol")

        # Should not crash
        assert result["files_scanned"] == 0 or result["files_failed"] >= 0


class TestRepositoryWideRename:
    """Test full repository-wide rename operation."""

    def test_rename_dry_run(self, temp_project):
        """Dry run identifies files without modifying."""
        renamer = RepoWideRename(project_root=temp_project, max_workers=2)

        # Create test files
        (temp_project / "module1.py").write_text("def old_function(): pass")
        (temp_project / "module2.py").write_text("old_function()")
        (temp_project / "module3.py").write_text("def other_function(): pass")

        result = renamer.rename_across_repository(
            target_type="function",
            old_name="old_function",
            new_name="new_function",
            dry_run=True,
        )

        assert result.files_scanned >= 3
        assert result.files_updated == 0  # Dry run doesn't update
        assert result.duration_seconds > 0

    def test_rename_with_progress_callback(self, temp_project):
        """Progress callback is invoked during rename."""
        renamer = RepoWideRename(project_root=temp_project, max_workers=2)

        # Create test files
        for i in range(10):
            (temp_project / f"file{i}.py").write_text(f"def func{i}(): pass")

        progress_updates = []

        def track_progress(completed, total):
            progress_updates.append((completed, total))

        renamer.rename_across_repository(
            target_type="function",
            old_name="func0",
            new_name="new_func0",
            dry_run=True,
            progress_callback=track_progress,
        )

        # Progress callback should have been called
        assert len(progress_updates) > 0

    def test_rename_no_candidates(self, temp_project):
        """Handles case with no candidate files."""
        # Empty directory
        empty_dir = temp_project / "empty_subdir"
        empty_dir.mkdir()

        renamer = RepoWideRename(project_root=empty_dir, max_workers=2)

        result = renamer.rename_across_repository(
            target_type="function",
            old_name="symbol",
            new_name="new_symbol",
            dry_run=True,
        )

        assert result.files_scanned == 0
        assert len(result.warnings) > 0
        assert "No candidate files" in result.warnings[0]

    def test_rename_custom_extensions(self, temp_project):
        """Supports custom file extensions."""
        renamer = RepoWideRename(project_root=temp_project, max_workers=2)

        # Create .pyx file (Cython)
        (temp_project / "cython_module.pyx").write_text("def cython_func(): pass")

        result = renamer.rename_across_repository(
            target_type="function",
            old_name="cython_func",
            new_name="new_cython_func",
            file_extensions={".pyx"},
            dry_run=True,
        )

        # Should have scanned the .pyx file
        assert result.files_scanned >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
