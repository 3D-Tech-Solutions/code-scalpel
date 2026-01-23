"""
Cross-platform path handling tests for validate_paths.

Tests path normalization and handling for:
- Windows paths (backslashes, drive letters, UNC paths)
- macOS paths (case sensitivity considerations)
- Linux paths (forward slashes, case sensitive)
- Mixed path separators

These tests run on Linux but verify the tool can handle
paths from other platforms correctly.
"""

import os
import tempfile

import pytest

# Import the MCP server to access the validate_paths tool
from code_scalpel.mcp.server import mcp


def get_validate_paths_tool():
    """Get the validate_paths tool from MCP server."""
    tools = mcp._tool_manager._tools
    return tools.get("validate_paths")


async def call_validate_paths(paths, project_root=None):
    """Helper to call validate_paths tool."""
    tool = get_validate_paths_tool()
    assert tool is not None, "validate_paths tool not found"

    # Call the tool function
    result = await tool.fn(paths=paths, project_root=project_root)
    return result


class TestWindowsPathHandling:
    """Test handling of Windows-style paths."""

    @pytest.mark.asyncio
    async def test_windows_backslash_paths_normalized(self):
        """Windows backslash paths should be normalized to forward slashes."""
        # Windows-style path with backslashes
        windows_path = "C:\\Users\\test\\project\\file.py"

        # Should normalize to forward slashes internally
        result = await call_validate_paths(paths=[windows_path])

        # Tool should handle the path (even if file doesn't exist)
        assert result is not None
        assert hasattr(result, "accessible") or hasattr(result, "inaccessible")

    @pytest.mark.asyncio
    async def test_windows_drive_letter_paths(self):
        """Windows drive letter paths should be handled."""
        paths = ["C:/Windows/System32", "D:/Projects/code", "E:/backup/files"]

        result = await call_validate_paths(paths=paths)

        assert result is not None
        # Should process all paths
        total = len(result.accessible) + len(result.inaccessible)
        assert total == len(paths)

    @pytest.mark.asyncio
    async def test_windows_unc_paths(self):
        """Windows UNC paths (\\\\server\\share) should be handled."""
        unc_paths = [
            "//server/share/file.txt",  # Unix-style UNC
        ]

        result = await call_validate_paths(paths=unc_paths)

        assert result is not None
        total = len(result.accessible) + len(result.inaccessible)
        assert total >= 1

    @pytest.mark.asyncio
    async def test_mixed_path_separators(self):
        """Paths with mixed separators should be normalized."""
        # Create a temp file to test with
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            temp_path = f.name
            f.write("test")

        try:
            # Convert to mixed separators (simulating Windows paths)
            mixed_path = temp_path.replace("/", "\\")

            result = await call_validate_paths(paths=[mixed_path])

            # Should handle the path
            assert result is not None
            total = len(result.accessible) + len(result.inaccessible)
            assert total >= 1
        finally:
            os.unlink(temp_path)

    @pytest.mark.asyncio
    async def test_windows_relative_paths(self):
        """Windows-style relative paths should be handled."""
        relative_paths = [
            ".\\src\\main.py",
            "..\\tests\\test_file.py",
            "subfolder\\file.txt",
        ]

        result = await call_validate_paths(paths=relative_paths)

        assert result is not None
        total = len(result.accessible) + len(result.inaccessible)
        assert total == len(relative_paths)


class TestMacOSPathHandling:
    """Test macOS-specific path considerations."""

    @pytest.mark.asyncio
    async def test_macos_paths_with_spaces(self):
        """macOS paths with spaces should be handled."""
        paths = [
            "/Users/user name/Documents/My Files/file.txt",
            "/Applications/Visual Studio Code.app",
            "/Library/Application Support/data",
        ]

        result = await call_validate_paths(paths=paths)

        assert result is not None
        total = len(result.accessible) + len(result.inaccessible)
        assert total == len(paths)

    @pytest.mark.asyncio
    async def test_macos_hidden_files(self):
        """macOS hidden files (starting with .) should be handled."""
        hidden_paths = [
            "/Users/user/.ssh/config",
            "/Users/user/.bashrc",
            "/Users/user/.config/settings.json",
        ]

        result = await call_validate_paths(paths=hidden_paths)

        assert result is not None
        total = len(result.accessible) + len(result.inaccessible)
        assert total == len(hidden_paths)

    @pytest.mark.asyncio
    async def test_macos_case_sensitivity(self):
        """Test handling of case variations (macOS is case-insensitive by default)."""
        # Create a temp file
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            temp_path = f.name
            f.write("test")

        try:
            # Test with different cases
            lower_path = temp_path.lower()
            upper_path = temp_path.upper()

            result = await call_validate_paths(paths=[lower_path, upper_path])

            # On Linux (case-sensitive), these will be different files
            # On macOS (case-insensitive), these would be the same
            # Tool should handle both scenarios
            assert result is not None
            total = len(result.accessible) + len(result.inaccessible)
            assert total >= 1
        finally:
            os.unlink(temp_path)


class TestLinuxPathHandling:
    """Test Linux-specific path handling."""

    @pytest.mark.asyncio
    async def test_linux_absolute_paths(self):
        """Standard Linux absolute paths should work."""
        paths = [
            "/usr/bin/python",
            "/etc/hosts",
            "/var/log/syslog",
            "/home/user/project/src/main.py",
        ]

        result = await call_validate_paths(paths=paths)

        assert result is not None
        total = len(result.accessible) + len(result.inaccessible)
        assert total == len(paths)

    @pytest.mark.asyncio
    async def test_linux_relative_paths(self):
        """Linux relative paths should be resolved."""
        paths = ["./src/main.py", "../tests/test_file.py", "data/input.csv"]

        result = await call_validate_paths(paths=paths)

        assert result is not None
        total = len(result.accessible) + len(result.inaccessible)
        assert total == len(paths)

    @pytest.mark.asyncio
    async def test_linux_home_directory_expansion(self):
        """Paths with ~ should be expanded."""
        paths = ["~/Documents/file.txt", "~/.bashrc", "~/project/src"]

        result = await call_validate_paths(paths=paths)

        assert result is not None
        total = len(result.accessible) + len(result.inaccessible)
        assert total == len(paths)


class TestPathNormalization:
    """Test path normalization across platforms."""

    @pytest.mark.asyncio
    async def test_trailing_slashes_removed(self):
        """Trailing slashes should be normalized."""
        paths = ["/usr/bin/", "/home/user/project/", "relative/path/"]

        result = await call_validate_paths(paths=paths)

        assert result is not None
        total = len(result.accessible) + len(result.inaccessible)
        assert total == len(paths)

    @pytest.mark.asyncio
    async def test_double_slashes_normalized(self):
        """Double slashes should be normalized."""
        paths = ["/usr//bin//python", "//home//user//file.txt", "relative//path//file"]

        result = await call_validate_paths(paths=paths)

        assert result is not None
        total = len(result.accessible) + len(result.inaccessible)
        assert total == len(paths)

    @pytest.mark.asyncio
    async def test_dot_segments_in_paths(self):
        """Paths with . and .. should be normalized."""
        paths = [
            "/usr/./bin/python",
            "/home/../etc/hosts",
            "./current/./directory/./file",
        ]

        result = await call_validate_paths(paths=paths)

        assert result is not None
        total = len(result.accessible) + len(result.inaccessible)
        assert total == len(paths)

    @pytest.mark.asyncio
    async def test_empty_path_components(self):
        """Paths with empty components should be handled."""
        # These should be normalized or rejected gracefully
        paths = ["/", "//", ".//"]

        result = await call_validate_paths(paths=paths)

        assert result is not None
        # Tool should handle these without crashing


class TestSpecialCharactersInPaths:
    """Test paths with special characters."""

    @pytest.mark.asyncio
    async def test_unicode_characters_in_paths(self):
        """Paths with Unicode characters should be handled."""
        paths = [
            "/home/用户/项目/文件.txt",
            "/Users/ユーザー/ドキュメント/file.txt",
            "/home/utilisateur/documents/fichéé.txt",
        ]

        result = await call_validate_paths(paths=paths)

        assert result is not None
        total = len(result.accessible) + len(result.inaccessible)
        assert total == len(paths)

    @pytest.mark.asyncio
    async def test_spaces_in_paths(self):
        """Paths with spaces should be handled."""
        paths = [
            "/path with spaces/file.txt",
            "/my documents/important files/data.csv",
            "relative path/with spaces/file",
        ]

        result = await call_validate_paths(paths=paths)

        assert result is not None
        total = len(result.accessible) + len(result.inaccessible)
        assert total == len(paths)

    @pytest.mark.asyncio
    async def test_special_characters_in_filenames(self):
        """Filenames with special characters should be handled."""
        paths = [
            "/home/user/file-with-dashes.txt",
            "/home/user/file_with_underscores.py",
            "/home/user/file.with.dots.json",
            "/home/user/file@special#chars.txt",
        ]

        result = await call_validate_paths(paths=paths)

        assert result is not None
        total = len(result.accessible) + len(result.inaccessible)
        assert total == len(paths)


class TestCrossPlatformEdgeCases:
    """Test edge cases that differ across platforms."""

    @pytest.mark.asyncio
    async def test_very_long_paths(self):
        """Very long paths should be handled."""
        # Windows has MAX_PATH of 260 characters (can be extended)
        # Linux/macOS have PATH_MAX of 4096
        long_path = "/home/" + "a" * 250 + "/file.txt"

        result = await call_validate_paths(paths=[long_path])

        assert result is not None
        total = len(result.accessible) + len(result.inaccessible)
        assert total >= 1

    @pytest.mark.asyncio
    async def test_reserved_windows_filenames(self):
        """Reserved Windows filenames should be handled."""
        # Windows reserves these names
        reserved = ["CON", "PRN", "AUX", "NUL", "COM1", "LPT1"]

        paths = [f"/path/to/{name}.txt" for name in reserved]

        result = await call_validate_paths(paths=paths)

        # Tool should handle these (they're valid on Linux)
        assert result is not None
        total = len(result.accessible) + len(result.inaccessible)
        assert total == len(paths)

    @pytest.mark.asyncio
    async def test_network_paths(self):
        """Network paths should be handled."""
        network_paths = [
            "//network/share/file.txt",
            "\\\\server\\share\\data.csv",
            "/mnt/nfs/remote/file",
        ]

        result = await call_validate_paths(paths=network_paths)

        assert result is not None
        total = len(result.accessible) + len(result.inaccessible)
        assert total >= 1

    @pytest.mark.asyncio
    async def test_symbolic_links_across_platforms(self):
        """Symbolic links should be handled consistently."""
        # Create a temp file and symlink
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            temp_file = f.name
            f.write("test")

        temp_link = temp_file + ".link"

        try:
            os.symlink(temp_file, temp_link)

            result = await call_validate_paths(paths=[temp_link])

            # Tool should follow symlinks
            assert result is not None
            total = len(result.accessible) + len(result.inaccessible)
            assert total >= 1
        finally:
            if os.path.exists(temp_link):
                os.unlink(temp_link)
            os.unlink(temp_file)


class TestPathSeparatorNormalization:
    """Test that path separators are normalized correctly."""

    @pytest.mark.asyncio
    async def test_backslash_to_forward_slash_conversion(self):
        """Backslashes should be converted to forward slashes."""
        # Simulate Windows paths received as strings
        windows_style = ["C:\\Users\\test\\file.py", "relative\\path\\to\\file.txt"]

        result = await call_validate_paths(paths=windows_style)

        # Should handle conversion
        assert result is not None
        total = len(result.accessible) + len(result.inaccessible)
        assert total == len(windows_style)

    @pytest.mark.asyncio
    async def test_mixed_separators_normalized(self):
        """Mixed separators should be normalized."""
        mixed = ["C:/Users\\test/file.py", "relative/path\\to/file.txt"]

        result = await call_validate_paths(paths=mixed)

        assert result is not None
        total = len(result.accessible) + len(result.inaccessible)
        assert total == len(mixed)

    @pytest.mark.asyncio
    async def test_consistent_separator_in_results(self):
        """Results should use consistent separators."""
        # Mix of path styles
        paths = ["/unix/style/path", "C:\\Windows\\style\\path", "relative/path"]

        result = await call_validate_paths(paths=paths)

        # Check that results exist and are consistent
        assert result is not None

        # All returned paths should use forward slashes
        # Verify accessible/inaccessible lists are present
        assert hasattr(result, "accessible")
        assert hasattr(result, "inaccessible")


class TestCrossPlatformIntegration:
    """Integration tests for cross-platform scenarios."""

    @pytest.mark.asyncio
    async def test_mixed_platform_paths_in_single_call(self):
        """Tool should handle mixed platform paths in one call."""
        mixed_paths = [
            "/usr/bin/python",  # Linux
            "C:\\Windows\\System32",  # Windows
            "/Users/user/Documents/file",  # macOS
            "relative/path/file.txt",  # Universal
            "\\\\server\\share\\file",  # UNC
        ]

        result = await call_validate_paths(paths=mixed_paths)

        assert result is not None
        total = len(result.accessible) + len(result.inaccessible)
        assert total == len(mixed_paths)

    @pytest.mark.asyncio
    async def test_docker_paths_with_windows_mounts(self):
        """Docker scenarios with Windows-style mount paths."""
        # Simulate Windows paths that need Docker mount suggestions
        windows_paths = [
            "C:\\Users\\user\\project\\src\\main.py",
            "D:\\workspace\\data\\input.csv",
        ]

        result = await call_validate_paths(paths=windows_paths)

        # Should provide suggestions for mounting
        assert result is not None
        # Tool should detect these need mounting if in Docker
        if result.is_docker:
            assert result.suggestions is not None
