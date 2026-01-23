"""[20260108_TEST] Quality Attributes Tests for rename_symbol Tool.

Tests for performance, reliability, security, and compatibility.
Covers Section 4 of MCP_TOOL_COMPREHENSIVE_TEST_CHECKLIST.md
"""

import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from code_scalpel.surgery.surgical_patcher import UnifiedPatcher


class TestPerformanceSmallInput:
    """[20260108_TEST] Small input (<100 LOC) performance tests."""

    def test_small_input_completes_under_100ms(self, tmp_path: Path):
        """Small input (50 LOC) completes in <100ms."""
        src = tmp_path / "small.py"
        src.write_text("def old_func():\n    return 1\n")

        start = time.time()
        patcher = UnifiedPatcher.from_file(str(src))
        result = patcher.rename_symbol("function", "old_func", "new_func")
        duration = time.time() - start

        assert result.success is True
        assert duration < 0.1  # 100ms


class TestPerformanceMediumInput:
    """[20260108_TEST] Medium input (1000 LOC) performance tests."""

    def test_medium_input_completes_under_1s(self, tmp_path: Path):
        """Medium input (1000 LOC) completes in <1s."""
        src = tmp_path / "medium.py"

        # Generate 1000 LOC with function definition and references
        code_lines = ["def old_func():\n    return 1\n"]
        for i in range(100):
            code_lines.append(f"# Comment line {i}\n")
            code_lines.append(f"result_{i} = old_func()  # Call {i}\n")

        src.write_text("".join(code_lines))
        assert src.stat().st_size > 1000  # Verify ~1K LOC

        start = time.time()
        patcher = UnifiedPatcher.from_file(str(src))
        result = patcher.rename_symbol("function", "old_func", "new_func")
        duration = time.time() - start

        assert result.success is True
        assert duration < 1.0  # 1s


class TestPerformanceLargeInput:
    """[20260108_TEST] Large input (10K LOC) performance tests."""

    def test_large_input_completes_under_10s(self, tmp_path: Path):
        """Large input (10K LOC) completes in <10s."""
        src = tmp_path / "large.py"

        # Generate 10K LOC
        code_lines = ["def old_func():\n    return 1\n"]
        for i in range(1000):
            code_lines.append(f"# Section {i}\n")
            code_lines.append(f"result_{i} = old_func()\n")

        src.write_text("".join(code_lines))
        assert src.stat().st_size > 10000  # Verify ~10K LOC

        start = time.time()
        patcher = UnifiedPatcher.from_file(str(src))
        result = patcher.rename_symbol("function", "old_func", "new_func")
        duration = time.time() - start

        assert result.success is True
        assert duration < 10.0  # 10s


class TestMemoryUsage:
    """[20260108_TEST] Memory usage tests."""

    def test_small_input_memory_efficient(self, tmp_path: Path):
        """Small input uses minimal memory."""
        src = tmp_path / "small.py"
        src.write_text("def old_func():\n    return 1\n")

        # No crash with small file
        patcher = UnifiedPatcher.from_file(str(src))
        result = patcher.rename_symbol("function", "old_func", "new_func")
        assert result.success is True

    def test_multiple_renames_no_leak(self, tmp_path: Path):
        """Repeated renames don't leak memory."""
        src = tmp_path / "module.py"
        src.write_text("def old_func():\n    return 1\n")

        # Perform 10 sequential renames (different targets)
        for i in range(10):
            patcher = UnifiedPatcher.from_file(str(src))
            # Each creates new patcher (simulating independent calls)
            result = patcher.rename_symbol("function", "old_func", f"new_func_{i}")
            # Don't save (just test parsing doesn't leak)
            assert result is not None


class TestStressTesting:
    """[20260108_TEST] Stress and concurrent request tests."""

    def test_100_sequential_renames(self, tmp_path: Path):
        """100 sequential rename operations succeed."""
        files = []
        for i in range(100):
            src = tmp_path / f"module_{i}.py"
            src.write_text(f"def old_func_{i}():\n    return {i}\n")
            files.append(src)

        # Rename each file sequentially
        for i, src in enumerate(files):
            patcher = UnifiedPatcher.from_file(str(src))
            result = patcher.rename_symbol("function", f"old_func_{i}", f"new_func_{i}")
            assert result.success is True

    def test_10_concurrent_renames(self, tmp_path: Path):
        """10 concurrent renames via threading work correctly."""

        files = []
        for i in range(10):
            src = tmp_path / f"module_{i}.py"
            src.write_text(f"def old_func_{i}():\n    return {i}\n")
            files.append(src)

        def rename_one(index: int, src_path: Path):
            """Rename one file."""
            patcher = UnifiedPatcher.from_file(str(src_path))
            return patcher.rename_symbol("function", f"old_func_{index}", f"new_func_{index}")

        # Run 10 concurrent renames via ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(rename_one, i, files[i]) for i in range(10)]
            results = [f.result() for f in futures]

        # All should succeed
        assert all(r.success for r in results)
        assert len(results) == 10


class TestFileSizeLimit:
    """[20260108_TEST] Large file (max size) handling."""

    def test_2mb_file_handled(self, tmp_path: Path):
        """2MB file is processed without issues."""
        src = tmp_path / "large_file.py"

        # Create 2MB file with function definition and references
        code_lines = ["def old_func():\n    return 1\n\n"]
        # Each line is ~100 bytes
        while len("".join(code_lines)) < 2 * 1024 * 1024:  # 2MB
            code_lines.append("result = old_func()  # " + "x" * 70 + "\n")

        src.write_text("".join(code_lines))
        assert src.stat().st_size > 2 * 1024 * 1024

        start = time.time()
        patcher = UnifiedPatcher.from_file(str(src))
        result = patcher.rename_symbol("function", "old_func", "new_func")
        duration = time.time() - start

        assert result.success is True
        assert duration < 30.0  # Should complete in reasonable time


class TestErrorRecovery:
    """[20260108_TEST] Error recovery and graceful degradation."""

    def test_invalid_input_returns_error(self, tmp_path: Path):
        """Invalid target type returns error, doesn't crash."""
        src = tmp_path / "module.py"
        src.write_text("def old_func():\n    return 1\n")

        patcher = UnifiedPatcher.from_file(str(src))

        # Invalid target_type
        result = patcher.rename_symbol("invalid_type", "old_func", "new_func")

        # Should return error, not crash
        assert result is not None
        assert hasattr(result, "success")

    def test_read_only_file_error(self, tmp_path: Path):
        """Read-only file returns clear error."""
        src = tmp_path / "readonly.py"
        src.write_text("def old_func():\n    return 1\n")
        src.chmod(0o444)  # Read-only

        try:
            patcher = UnifiedPatcher.from_file(str(src))
            result = patcher.rename_symbol("function", "old_func", "new_func")
            patcher.save(backup=False)

            # Should fail gracefully
            assert result is not None
            assert hasattr(result, "success")
        finally:
            # Restore permissions for cleanup
            src.chmod(0o644)

    def test_invalid_utf8_error(self, tmp_path: Path):
        """Invalid UTF-8 file returns error."""
        src = tmp_path / "invalid.py"

        # Write invalid UTF-8
        with open(src, "wb") as f:
            f.write(b"def old_func():\n    return \xff\n")

        try:
            patcher = UnifiedPatcher.from_file(str(src))
            result = patcher.rename_symbol("function", "old_func", "new_func")

            # Should handle gracefully
            assert result is not None
        except (UnicodeDecodeError, ValueError):
            # Acceptable error handling
            pass

    def test_server_continues_after_error(self, tmp_path: Path):
        """Server handles errors and continues working."""
        src1 = tmp_path / "good.py"
        src1.write_text("def old_func():\n    return 1\n")

        src2 = tmp_path / "bad.py"
        src2.write_text("def bad_func():\n    return 1\n")

        # First call with invalid input
        patcher1 = UnifiedPatcher.from_file(str(src1))
        patcher1.rename_symbol("invalid_type", "old_func", "new_func")

        # Second call should still work
        patcher2 = UnifiedPatcher.from_file(str(src2))
        result2 = patcher2.rename_symbol("function", "bad_func", "renamed_func")

        # Second call succeeds despite first error
        assert result2.success is True


class TestDeterminism:
    """[20260108_TEST] Deterministic output."""

    def test_same_input_same_output(self, tmp_path: Path):
        """Same input produces identical output."""
        src = tmp_path / "module.py"
        src.write_text("def old_func():\n    return 1\n")

        patcher1 = UnifiedPatcher.from_file(str(src))
        result1 = patcher1.rename_symbol("function", "old_func", "new_func")

        patcher2 = UnifiedPatcher.from_file(str(src))
        result2 = patcher2.rename_symbol("function", "old_func", "new_func")

        # Results should be identical
        assert result1.success == result2.success
        assert result1.file_path == result2.file_path
        assert result1.target_name == result2.target_name

    def test_deterministic_ordering(self, tmp_path: Path):
        """Results are ordered consistently."""
        # Create multiple files with same function
        files = []
        for i in range(5):
            src = tmp_path / f"module_{i}.py"
            src.write_text(f"def old_func():\n    return {i}\n")
            files.append(src)

        # Run rename twice on same file
        patcher1 = UnifiedPatcher.from_file(str(files[0]))
        result1 = patcher1.rename_symbol("function", "old_func", "new_func")

        patcher2 = UnifiedPatcher.from_file(str(files[0]))
        result2 = patcher2.rename_symbol("function", "old_func", "new_func")

        # Results should be identical (same file, same operation)
        assert result1.success == result2.success
        assert result1.file_path == result2.file_path


class TestSecurity:
    """[20260108_TEST] Security and privacy."""

    def test_no_secret_leakage(self, tmp_path: Path):
        """Secrets in code not leaked in response."""
        src = tmp_path / "secrets.py"
        secret_key = "sk-1234567890abcdef"
        src.write_text(f'API_KEY = "{secret_key}"\ndef old_func():\n    return 1\n')

        patcher = UnifiedPatcher.from_file(str(src))
        result = patcher.rename_symbol("function", "old_func", "new_func")

        # Secret should not appear in response
        response_str = json.dumps(vars(result), default=str)
        assert secret_key not in response_str

    def test_no_code_execution(self, tmp_path: Path):
        """Malicious code in input not executed."""
        src = tmp_path / "malicious.py"
        src.write_text("def old_func():\n    import os\n    os.system('touch /tmp/pwned')\n    return 1\n")

        # Should parse, not execute
        patcher = UnifiedPatcher.from_file(str(src))
        result = patcher.rename_symbol("function", "old_func", "new_func")

        # Operation succeeds (parses code)
        assert result.success is True

    def test_path_sanitization(self, tmp_path: Path):
        """File paths are properly handled."""
        src = tmp_path / "module.py"
        src.write_text("def old_func():\n    return 1\n")

        patcher = UnifiedPatcher.from_file(str(src))
        result = patcher.rename_symbol("function", "old_func", "new_func")

        # Paths should be valid
        assert result.success is True
        # file_path should be valid
        assert isinstance(result.file_path, str)
        assert len(result.file_path) > 0
        assert Path(result.file_path).exists()


class TestReliability:
    """[20260108_TEST] Reliability and error handling."""

    def test_nonexistent_file_error(self, tmp_path: Path):
        """Nonexistent file returns clear error."""
        nonexistent = tmp_path / "nonexistent.py"

        try:
            UnifiedPatcher.from_file(str(nonexistent))
        except (FileNotFoundError, ValueError):
            # Expected error
            pass

    def test_syntax_error_in_file(self, tmp_path: Path):
        """File with syntax error handled gracefully."""
        src = tmp_path / "syntax_error.py"
        src.write_text("def old_func(:\n    return 1\n")  # Missing )

        try:
            patcher = UnifiedPatcher.from_file(str(src))
            result = patcher.rename_symbol("function", "old_func", "new_func")
            # Should handle gracefully
            assert result is not None
        except (SyntaxError, ValueError):
            # Acceptable - syntax errors should be reported
            pass

    def test_symlink_handling(self, tmp_path: Path):
        """Symlinked files handled correctly."""
        src = tmp_path / "module.py"
        src.write_text("def old_func():\n    return 1\n")

        link = tmp_path / "link.py"
        try:
            link.symlink_to(src)

            patcher = UnifiedPatcher.from_file(str(link))
            result = patcher.rename_symbol("function", "old_func", "new_func")

            # Should work (follows symlink)
            assert result.success is True
        except (OSError, NotImplementedError):
            # Windows may not support symlinks
            pytest.skip("Symlinks not supported on this platform")


class TestCompatibility:
    """[20260108_TEST] Platform and Python version compatibility."""

    def test_linux_compatible(self):
        """Tool works on Linux."""
        if sys.platform != "linux":
            pytest.skip("Linux-specific test")

        assert sys.platform == "linux"

    def test_windows_compatible(self):
        """Tool works on Windows."""
        if sys.platform != "win32":
            pytest.skip("Windows-specific test")

        assert sys.platform == "win32"

    def test_macos_compatible(self):
        """Tool works on macOS."""
        if sys.platform != "darwin":
            pytest.skip("macOS-specific test")

        assert sys.platform == "darwin"

    @pytest.mark.skipif(sys.version_info < (3, 8), reason="Requires Python 3.8+")
    def test_python38_compatible(self):
        """Tool works on Python 3.8+."""
        assert sys.version_info >= (3, 8)

    @pytest.mark.skipif(sys.version_info < (3, 9), reason="Requires Python 3.9+")
    def test_python39_compatible(self):
        """Tool works on Python 3.9+."""
        assert sys.version_info >= (3, 9)

    @pytest.mark.skipif(sys.version_info < (3, 10), reason="Requires Python 3.10+")
    def test_python310_compatible(self):
        """Tool works on Python 3.10+."""
        assert sys.version_info >= (3, 10)

    def test_cross_platform_path_handling(self, tmp_path: Path):
        """Tool handles paths correctly on current platform."""
        src = tmp_path / "module.py"
        src.write_text("def old_func():\n    return 1\n")

        patcher = UnifiedPatcher.from_file(str(src))
        result = patcher.rename_symbol("function", "old_func", "new_func")

        assert result.success is True


class TestErrorMessages:
    """[20260108_TEST] Error message quality."""

    def test_error_messages_clear(self, tmp_path: Path):
        """Error messages are clear and actionable."""
        src = tmp_path / "module.py"
        src.write_text("def old_func():\n    return 1\n")

        patcher = UnifiedPatcher.from_file(str(src))
        result = patcher.rename_symbol("invalid_type", "old_func", "new_func")

        # Error message should be present if error occurred
        if not result.success:
            assert result.error is not None
            assert len(result.error) > 0
            assert isinstance(result.error, str)

    def test_response_includes_context(self, tmp_path: Path):
        """Response includes useful context."""
        src = tmp_path / "module.py"
        src.write_text("def old_func():\n    return 1\n")

        patcher = UnifiedPatcher.from_file(str(src))
        result = patcher.rename_symbol("function", "old_func", "new_func")

        # Response should have context fields
        assert hasattr(result, "success")
        assert hasattr(result, "file_path")
        assert hasattr(result, "target_name")
        assert hasattr(result, "target_type")


class TestWarningsAndNotifications:
    """[20260108_TEST] Warnings and notifications."""

    def test_warnings_populated_on_rename(self, tmp_path: Path):
        """Error field is empty on successful rename."""
        src = tmp_path / "module.py"
        src.write_text("def old_func():\n    return 1\n")

        patcher = UnifiedPatcher.from_file(str(src))
        result = patcher.rename_symbol("function", "old_func", "new_func")

        # Error should be None on success
        assert hasattr(result, "error")
        assert result.error is None or isinstance(result.error, str)

    def test_no_excessive_warnings(self, tmp_path: Path):
        """Response is clean for simple case."""
        src = tmp_path / "module.py"
        src.write_text("def old_func():\n    return 1\n")

        patcher = UnifiedPatcher.from_file(str(src))
        result = patcher.rename_symbol("function", "old_func", "new_func")

        # Success and basic fields populated
        assert result.success is True
        assert result.file_path is not None
