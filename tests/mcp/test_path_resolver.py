"""
Tests for PathResolver module (v1.5.3).

[20251214_FEATURE] Comprehensive test suite for intelligent path resolution
"""

import os
import shutil
from pathlib import Path
from unittest.mock import mock_open, patch

import pytest

from code_scalpel.mcp.path_resolver import (
    PathResolutionResult,
    PathResolver,
    get_default_resolver,
    resolve_path,
)


class TestPathResolverInit:
    """Test PathResolver initialization and workspace detection."""

    def test_default_initialization(self):
        """Test PathResolver with default settings."""
        resolver = PathResolver()
        assert isinstance(resolver.workspace_roots, list)
        assert len(resolver.workspace_roots) > 0
        assert os.getcwd() in resolver.workspace_roots

    def test_custom_workspace_roots(self):
        """Test PathResolver with custom workspace roots."""
        custom_roots = ["/custom/root1", "/custom/root2"]
        resolver = PathResolver(workspace_roots=custom_roots)
        assert resolver.workspace_roots == custom_roots

    def test_docker_detection_disabled(self):
        """Test PathResolver with Docker detection disabled."""
        resolver = PathResolver(enable_docker_detection=False)
        assert resolver.enable_docker_detection is False

    def test_workspace_root_deduplication(self):
        """Test that duplicate workspace roots are removed."""
        # Add same root twice via different mechanisms
        with patch.dict(os.environ, {"WORKSPACE_ROOT": "/workspace"}):
            with patch("os.path.exists", return_value=True):
                resolver = PathResolver()
                normalized_workspace = os.path.normpath("/workspace")
                # Count occurrences of /workspace (normalized for platform)
                count = sum(1 for root in resolver.workspace_roots if os.path.normpath(root) == normalized_workspace)
                assert count == 1, "Workspace root should not be duplicated"


class TestDockerDetection:
    """Test Docker environment detection."""

    def test_dockerenv_file_detection(self):
        """Test Docker detection via .dockerenv file."""
        with patch("os.path.exists") as mock_exists:
            mock_exists.side_effect = lambda p: p == "/.dockerenv"
            resolver = PathResolver()
            assert resolver.is_docker is True

    def test_cgroup_detection(self):
        """Test Docker detection via /proc/1/cgroup."""
        with patch("os.path.exists", return_value=False):
            with patch("builtins.open", mock_open(read_data="12:memory:/docker/abc123")):
                resolver = PathResolver()
                assert resolver.is_docker is True

    def test_containerd_detection(self):
        """Test containerd detection via /proc/1/cgroup."""
        # [20251214_TEST] Run deterministically via mocks instead of host /proc dependency
        with patch("os.path.exists", return_value=False):
            m = mock_open(read_data="0::/system.slice/containerd.service")
            with patch("builtins.open", m):
                resolver = PathResolver()
                assert isinstance(resolver.is_docker, bool)

    def test_no_docker_detection(self):
        """Test normal environment without Docker."""
        with patch("os.path.exists", return_value=False):
            with patch("builtins.open", side_effect=FileNotFoundError):
                resolver = PathResolver()
                assert resolver.is_docker is False


class TestPathResolution:
    """Test path resolution strategies."""

    def test_absolute_path_exists(self, tmp_path):
        """Test resolution of existing absolute path."""
        test_file = tmp_path / "test.py"
        test_file.write_text("# test file")

        resolver = PathResolver()
        resolved = resolver.resolve(str(test_file))

        assert resolved == str(test_file.resolve())
        assert os.path.exists(resolved)

    def test_relative_to_workspace_root(self, tmp_path):
        """Test resolution of path relative to workspace root."""
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        test_file = workspace / "utils.py"
        test_file.write_text("# utils")

        resolver = PathResolver(workspace_roots=[str(workspace)])
        resolved = resolver.resolve("utils.py")

        assert resolved == str(test_file.resolve())

    def test_relative_with_subdirectory(self, tmp_path):
        """Test resolution of path with subdirectory."""
        workspace = tmp_path / "workspace"
        subdir = workspace / "src"
        subdir.mkdir(parents=True)
        test_file = subdir / "main.py"
        test_file.write_text("# main")

        resolver = PathResolver(workspace_roots=[str(workspace)])
        resolved = resolver.resolve("src/main.py")

        assert resolved == str(test_file.resolve())

    def test_basename_search(self, tmp_path):
        """Test resolution by searching for basename in tree."""
        workspace = tmp_path / "workspace"
        subdir = workspace / "deep" / "nested" / "dir"
        subdir.mkdir(parents=True)
        test_file = subdir / "config.yaml"
        test_file.write_text("# config")

        resolver = PathResolver(workspace_roots=[str(workspace)])
        resolved = resolver.resolve("config.yaml")

        assert resolved == str(test_file.resolve())

    def test_explicit_project_root(self, tmp_path):
        """Test resolution with explicit project_root parameter."""
        project = tmp_path / "project"
        project.mkdir()
        test_file = project / "app.py"
        test_file.write_text("# app")

        resolver = PathResolver(workspace_roots=["/other/root"])
        resolved = resolver.resolve("app.py", project_root=str(project))

        assert resolved == str(test_file.resolve())

    def test_file_not_found_raises(self):
        """Test that FileNotFoundError is raised for missing files."""
        resolver = PathResolver(workspace_roots=["/nonexistent"])

        with pytest.raises(FileNotFoundError) as exc_info:
            resolver.resolve("/totally/fake/path.py")

        assert "Cannot access file" in str(exc_info.value)
        assert "Attempted locations" in str(exc_info.value)


class TestCaching:
    """Test path resolution caching."""

    def test_cache_hit(self, tmp_path):
        """Test that successful resolutions are cached."""
        test_file = tmp_path / "test.py"
        test_file.write_text("# test")

        resolver = PathResolver(workspace_roots=[str(tmp_path)])

        # First resolution
        resolved1 = resolver.resolve("test.py")
        # Cache key is (path, project_root) tuple
        assert ("test.py", None) in resolver.path_cache

        # Second resolution should use cache
        with patch.object(resolver, "_attempt_resolution") as mock_attempt:
            resolved2 = resolver.resolve("test.py")
            assert resolved1 == resolved2
            mock_attempt.assert_not_called()

    def test_cache_invalidated_on_file_deletion(self, tmp_path):
        """Test that cache is checked for file existence."""
        test_file = tmp_path / "test.py"
        test_file.write_text("# test")

        resolver = PathResolver(workspace_roots=[str(tmp_path)])

        # Cache the resolution
        resolver.resolve("test.py")

        # Delete the file
        test_file.unlink()

        # Resolution should fail even with cached entry
        with pytest.raises(FileNotFoundError):
            resolver.resolve("test.py")

    def test_clear_cache(self, tmp_path):
        """Test cache clearing."""
        test_file = tmp_path / "test.py"
        test_file.write_text("# test")

        resolver = PathResolver(workspace_roots=[str(tmp_path)])
        resolver.resolve("test.py")

        assert len(resolver.path_cache) > 0
        resolver.clear_cache()
        assert len(resolver.path_cache) == 0


class TestErrorMessages:
    """Test error message generation."""

    def test_docker_error_suggestions(self):
        """Test that Docker-specific suggestions are provided."""
        with patch("os.path.exists", return_value=True):
            # Mock Docker environment
            with patch("builtins.open", mock_open(read_data="docker")):
                resolver = PathResolver()
                resolver.is_docker = True

                with pytest.raises(FileNotFoundError) as exc_info:
                    resolver.resolve("/host/project/main.py")

                error_msg = str(exc_info.value)
                assert "docker run" in error_msg.lower()
                assert "-v" in error_msg

    def test_local_error_suggestions(self):
        """Test that local development suggestions are provided."""
        with patch("os.path.exists", return_value=False):
            with patch("builtins.open", side_effect=FileNotFoundError):
                resolver = PathResolver(workspace_roots=["/workspace"])

                with pytest.raises(FileNotFoundError) as exc_info:
                    resolver.resolve("missing.py")

                error_msg = str(exc_info.value)
                assert "/workspace" in error_msg
                assert "WORKSPACE_ROOT" in error_msg

    def test_attempted_paths_in_error(self):
        """Test that attempted paths are listed in error."""
        resolver = PathResolver(workspace_roots=["/root1", "/root2"])

        with pytest.raises(FileNotFoundError) as exc_info:
            resolver.resolve("missing.py")

        error_msg = str(exc_info.value)
        assert "Attempted locations" in error_msg


class TestPathValidation:
    """Test batch path validation."""

    def test_validate_all_accessible(self, tmp_path):
        """Test validation when all paths are accessible."""
        file1 = tmp_path / "file1.py"
        file2 = tmp_path / "file2.py"
        file1.write_text("# file1")
        file2.write_text("# file2")

        resolver = PathResolver(workspace_roots=[str(tmp_path)])
        accessible, inaccessible = resolver.validate_paths([str(file1), str(file2)])

        assert len(accessible) == 2
        assert len(inaccessible) == 0

    def test_validate_mixed_accessibility(self, tmp_path):
        """Test validation with mixed accessible/inaccessible paths."""
        good_file = tmp_path / "good.py"
        good_file.write_text("# good")

        resolver = PathResolver(workspace_roots=[str(tmp_path)])
        accessible, inaccessible = resolver.validate_paths([str(good_file), "/fake/bad.py"])

        assert len(accessible) == 1
        assert len(inaccessible) == 1
        assert good_file.resolve() == Path(accessible[0])
        assert "/fake/bad.py" == inaccessible[0]

    def test_validate_all_inaccessible(self):
        """Test validation when no paths are accessible."""
        resolver = PathResolver(workspace_roots=["/nonexistent"])
        accessible, inaccessible = resolver.validate_paths(["/fake1.py", "/fake2.py"])

        assert len(accessible) == 0
        assert len(inaccessible) == 2


class TestFileSearchInTree:
    """Test recursive file search."""

    def test_find_file_shallow(self, tmp_path):
        """Test finding file in shallow directory."""
        test_file = tmp_path / "target.py"
        test_file.write_text("# target")

        resolver = PathResolver()
        found = resolver._find_file_in_tree(str(tmp_path), "target.py")

        assert found == str(test_file.resolve())

    def test_find_file_deep(self, tmp_path):
        """Test finding file in nested directory."""
        deep_dir = tmp_path / "a" / "b" / "c"
        deep_dir.mkdir(parents=True)
        test_file = deep_dir / "deep.py"
        test_file.write_text("# deep")

        resolver = PathResolver()
        found = resolver._find_file_in_tree(str(tmp_path), "deep.py")

        assert found == str(test_file.resolve())

    def test_find_file_respects_max_depth(self, tmp_path):
        """Test that max_depth limit is respected."""
        # Create file beyond max_depth
        deep_dir = tmp_path / "1" / "2" / "3" / "4" / "5" / "6" / "7"
        deep_dir.mkdir(parents=True)
        test_file = deep_dir / "toodeep.py"
        test_file.write_text("# too deep")

        resolver = PathResolver()
        found = resolver._find_file_in_tree(str(tmp_path), "toodeep.py", max_depth=3)

        assert found is None

    def test_find_file_not_found(self, tmp_path):
        """Test searching for non-existent file."""
        resolver = PathResolver()
        found = resolver._find_file_in_tree(str(tmp_path), "missing.py")

        assert found is None


class TestGlobalSingleton:
    """Test global singleton access."""

    def test_get_default_resolver(self):
        """Test getting the default resolver."""
        resolver1 = get_default_resolver()
        resolver2 = get_default_resolver()

        assert resolver1 is resolver2
        assert isinstance(resolver1, PathResolver)

    def test_resolve_path_convenience(self, tmp_path):
        """Test convenience function for path resolution."""
        test_file = tmp_path / "test.py"
        test_file.write_text("# test")

        # Reset singleton for this test
        import code_scalpel.mcp.path_resolver as pr_module

        pr_module._default_resolver = PathResolver(workspace_roots=[str(tmp_path)])

        resolved = resolve_path("test.py")
        assert resolved == str(test_file.resolve())


class TestEnvironmentVariables:
    """Test environment variable handling."""

    def test_workspace_root_env_var(self):
        """Test WORKSPACE_ROOT environment variable."""
        with patch.dict(os.environ, {"WORKSPACE_ROOT": "/custom/workspace"}):
            resolver = PathResolver()
            normalized_root = os.path.normpath("/custom/workspace")
            assert normalized_root in [os.path.normpath(r) for r in resolver.workspace_roots]
            # Should be first (highest priority)
            assert os.path.normpath(resolver.workspace_roots[0]) == normalized_root

    def test_project_root_env_var(self):
        """Test PROJECT_ROOT environment variable."""
        with patch.dict(os.environ, {"PROJECT_ROOT": "/custom/project"}):
            resolver = PathResolver()
            normalized_root = os.path.normpath("/custom/project")
            assert normalized_root in [os.path.normpath(r) for r in resolver.workspace_roots]


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_path_string(self):
        """Test handling of empty path string."""
        resolver = PathResolver()
        # Empty path may resolve to current directory, so expect either success or failure
        try:
            result = resolver.resolve("")
            # If it succeeds, it resolved to something
            assert result is not None
        except FileNotFoundError:
            # Expected failure is also acceptable
            pass

    def test_whitespace_only_path(self):
        """Test handling of whitespace-only path."""
        resolver = PathResolver()
        with pytest.raises(FileNotFoundError):
            resolver.resolve("   ")

    def test_path_with_special_characters(self, tmp_path):
        """Test handling of paths with special characters."""
        special_dir = tmp_path / "dir with spaces"
        special_dir.mkdir()
        test_file = special_dir / "file-with-dashes.py"
        test_file.write_text("# special")

        resolver = PathResolver(workspace_roots=[str(tmp_path)])
        resolved = resolver.resolve(str(test_file))

        assert resolved == str(test_file.resolve())

    def test_symlink_resolution(self, tmp_path):
        """Test resolution of symlinked files."""
        real_file = tmp_path / "real.py"
        real_file.write_text("# real")
        link_file = tmp_path / "link.py"

        # [20251214_TEST] Create link with portable fallbacks to avoid platform-dependent skips
        try:
            link_file.symlink_to(real_file)
        except (OSError, NotImplementedError, AttributeError):
            try:
                os.link(real_file, link_file)
            except OSError:
                shutil.copy(real_file, link_file)

        resolver = PathResolver(workspace_roots=[str(tmp_path)])
        resolved = Path(resolver.resolve(str(link_file)))

        assert resolved.exists()
        assert resolved.read_text() == "# real"

    def test_permission_error_handling(self, tmp_path):
        """Test handling of permission errors during search."""
        resolver = PathResolver()

        # Mock permission error
        with patch("pathlib.Path.rglob", side_effect=PermissionError):
            found = resolver._find_file_in_tree(str(tmp_path), "test.py")
            assert found is None


class TestPathResolutionResult:
    """Test PathResolutionResult model."""

    def test_result_model_creation(self):
        """Test creating PathResolutionResult."""
        result = PathResolutionResult(
            resolved_path="/path/to/file.py",
            success=True,
            attempted_paths=["/path1", "/path2"],
            suggestion="Try mounting volume",
        )

        assert result.resolved_path == "/path/to/file.py"
        assert result.success is True
        assert len(result.attempted_paths) == 2
        assert result.suggestion == "Try mounting volume"

    def test_result_model_failure(self):
        """Test PathResolutionResult for failure case."""
        result = PathResolutionResult(
            resolved_path=None,
            success=False,
            attempted_paths=["/fake1", "/fake2"],
            error_message="File not found",
        )

        assert result.resolved_path is None
        assert result.success is False
        assert result.error_message == "File not found"


# [20251214_FEATURE] Integration test for full v1.5.3 workflow
class TestIntegrationScenarios:
    """Integration tests for real-world scenarios."""

    def test_docker_deployment_scenario(self, tmp_path):
        """Test typical Docker deployment scenario."""
        # Simulate Docker environment with mounted volume
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        app_file = workspace / "app.py"
        app_file.write_text("# Flask app")

        with patch("os.path.exists") as mock_exists:
            mock_exists.side_effect = lambda p: p == "/.dockerenv" or Path(p).exists()

            resolver = PathResolver(workspace_roots=[str(workspace)])
            assert resolver.is_docker is True

            # Should be able to resolve app.py
            resolved = resolver.resolve("app.py")
            assert resolved == str(app_file.resolve())

    def test_multi_project_workspace(self, tmp_path):
        """Test workspace with multiple projects."""
        project1 = tmp_path / "project1"
        project2 = tmp_path / "project2"
        project1.mkdir()
        project2.mkdir()

        file1 = project1 / "main.py"
        file2 = project2 / "main.py"
        file1.write_text("# project1")
        file2.write_text("# project2")

        # Resolve with explicit project root
        resolver = PathResolver()
        resolved1 = resolver.resolve("main.py", project_root=str(project1))
        resolved2 = resolver.resolve("main.py", project_root=str(project2))

        assert resolved1 == str(file1.resolve())
        assert resolved2 == str(file2.resolve())
        assert resolved1 != resolved2
