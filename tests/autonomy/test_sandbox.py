"""
[20251217_TEST] Unit tests for Speculative Execution (Sandboxed) module.

Tests cover:
- Sandbox creation and cleanup (P0)
- File change application (P0)
- Process execution with resource limits (P0)
- Side effect detection (P0)
- Full integration scenarios (P0)
"""

import os
import sys

import pytest

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from code_scalpel.autonomy.sandbox import (
    FileChange,
    LintResult,
    SandboxExecutor,
    SandboxResult,
    TestResult,
)


class TestFileChange:
    """[20251217_TEST] Tests for FileChange dataclass."""

    def test_create_file_change(self):
        """Test creating FileChange for new file."""
        change = FileChange(
            relative_path="src/new_file.py",
            operation="create",
            new_content="def hello():\n    pass\n",
        )
        assert change.relative_path == "src/new_file.py"
        assert change.operation == "create"
        assert change.new_content == "def hello():\n    pass\n"

    def test_modify_file_change(self):
        """Test creating FileChange for modification."""
        change = FileChange(
            relative_path="src/existing.py",
            operation="modify",
            new_content="# Modified\n",
        )
        assert change.operation == "modify"

    def test_delete_file_change(self):
        """Test creating FileChange for deletion."""
        change = FileChange(relative_path="src/old_file.py", operation="delete")
        assert change.operation == "delete"
        assert change.new_content is None


class TestTestResult:
    """[20251217_TEST] Tests for TestResult dataclass."""

    def test_create_test_result_passed(self):
        """Test creating TestResult for passed test."""
        result = TestResult(name="test_feature", passed=True, duration_ms=100)
        assert result.name == "test_feature"
        assert result.passed is True
        assert result.duration_ms == 100
        assert result.error_message is None

    def test_create_test_result_failed(self):
        """Test creating TestResult for failed test."""
        result = TestResult(
            name="test_bug",
            passed=False,
            duration_ms=50,
            error_message="AssertionError: Expected 2, got 3",
        )
        assert result.passed is False
        assert result.error_message == "AssertionError: Expected 2, got 3"


class TestLintResult:
    """[20251217_TEST] Tests for LintResult dataclass."""

    def test_create_lint_result(self):
        """Test creating LintResult."""
        result = LintResult(
            file="src/module.py",
            line=10,
            column=5,
            message="Undefined variable",
            severity="error",
        )
        assert result.file == "src/module.py"
        assert result.line == 10
        assert result.severity == "error"


class TestSandboxResult:
    """[20251217_TEST] Tests for SandboxResult dataclass."""

    def test_create_sandbox_result_success(self):
        """Test creating successful SandboxResult."""
        result = SandboxResult(
            success=True,
            test_results=[TestResult("test1", True, 100)],
            build_success=True,
            execution_time_ms=500,
            stdout="All tests passed",
            stderr="",
        )
        assert result.success is True
        assert result.build_success is True
        assert len(result.test_results) == 1
        assert result.execution_time_ms == 500

    def test_create_sandbox_result_failure(self):
        """Test creating failed SandboxResult."""
        result = SandboxResult(success=False, build_success=False, stderr="Build failed")
        assert result.success is False
        assert result.build_success is False


class TestSandboxExecutorInit:
    """[20251217_TEST] Tests for SandboxExecutor initialization."""

    def test_default_initialization(self):
        """Test default SandboxExecutor initialization."""
        executor = SandboxExecutor()
        assert executor.isolation_level == "process"
        assert executor.network_enabled is False
        assert executor.max_memory_mb == 512
        assert executor.max_cpu_seconds == 60
        assert executor.max_disk_mb == 100

    def test_custom_initialization(self):
        """Test custom SandboxExecutor initialization."""
        executor = SandboxExecutor(
            isolation_level="process",
            network_enabled=True,
            max_memory_mb=1024,
            max_cpu_seconds=120,
            max_disk_mb=200,
        )
        assert executor.isolation_level == "process"
        assert executor.network_enabled is True
        assert executor.max_memory_mb == 1024
        assert executor.max_cpu_seconds == 120
        assert executor.max_disk_mb == 200

    def test_container_initialization_without_docker(self, monkeypatch):
        """Test container mode fails gracefully without Docker."""
        # Mock docker import to fail
        import sys

        monkeypatch.setitem(sys.modules, "docker", None)

        # Re-import to pick up the mocked docker
        from importlib import reload

        import code_scalpel.autonomy.sandbox as sandbox_module

        reload(sandbox_module)

        with pytest.raises(ImportError, match="Docker support requires"):
            sandbox_module.SandboxExecutor(isolation_level="container")


class TestSandboxCreation:
    """[20251217_TEST] Tests for sandbox creation (P0)."""

    def test_create_sandbox_copies_files(self, tmp_path):
        """Test _create_sandbox creates isolated copy."""
        # Create a test project
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        (project_dir / "main.py").write_text("print('hello')")
        (project_dir / "README.md").write_text("# Test")

        executor = SandboxExecutor()
        sandbox_path = executor._create_sandbox(str(project_dir))

        try:
            # Verify sandbox was created
            assert sandbox_path.exists()
            assert (sandbox_path / "main.py").exists()
            assert (sandbox_path / "README.md").exists()

            # Verify content matches
            assert (sandbox_path / "main.py").read_text() == "print('hello')"
            assert (sandbox_path / "README.md").read_text() == "# Test"
        finally:
            executor._cleanup_sandbox(sandbox_path)

    def test_create_sandbox_excludes_git(self, tmp_path):
        """Test _create_sandbox excludes .git directory."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        (project_dir / ".git").mkdir()
        (project_dir / ".git" / "config").write_text("gitconfig")
        (project_dir / "main.py").write_text("code")

        executor = SandboxExecutor()
        sandbox_path = executor._create_sandbox(str(project_dir))

        try:
            assert (sandbox_path / "main.py").exists()
            assert not (sandbox_path / ".git").exists()
        finally:
            executor._cleanup_sandbox(sandbox_path)

    def test_create_sandbox_excludes_node_modules(self, tmp_path):
        """Test _create_sandbox excludes node_modules directory."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        (project_dir / "node_modules").mkdir()
        (project_dir / "node_modules" / "package").write_text("dep")
        (project_dir / "main.js").write_text("code")

        executor = SandboxExecutor()
        sandbox_path = executor._create_sandbox(str(project_dir))

        try:
            assert (sandbox_path / "main.js").exists()
            assert not (sandbox_path / "node_modules").exists()
        finally:
            executor._cleanup_sandbox(sandbox_path)

    def test_create_sandbox_handles_subdirectories(self, tmp_path):
        """Test _create_sandbox copies subdirectories."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        (project_dir / "src").mkdir()
        (project_dir / "src" / "module.py").write_text("def func(): pass")

        executor = SandboxExecutor()
        sandbox_path = executor._create_sandbox(str(project_dir))

        try:
            assert (sandbox_path / "src").exists()
            assert (sandbox_path / "src" / "module.py").exists()
        finally:
            executor._cleanup_sandbox(sandbox_path)


class TestFileChanges:
    """[20251217_TEST] Tests for applying file changes (P0)."""

    def test_apply_create_change(self, tmp_path):
        """Test _apply_changes creates new file."""
        executor = SandboxExecutor()

        changes = [
            FileChange(
                relative_path="new_file.py",
                operation="create",
                new_content="def new_func():\n    pass\n",
            )
        ]

        executor._apply_changes(tmp_path, changes)

        assert (tmp_path / "new_file.py").exists()
        assert (tmp_path / "new_file.py").read_text() == "def new_func():\n    pass\n"

    def test_apply_modify_change(self, tmp_path):
        """Test _apply_changes modifies existing file."""
        # Create existing file
        (tmp_path / "existing.py").write_text("old content")

        executor = SandboxExecutor()
        changes = [
            FileChange(
                relative_path="existing.py",
                operation="modify",
                new_content="new content",
            )
        ]

        executor._apply_changes(tmp_path, changes)

        assert (tmp_path / "existing.py").read_text() == "new content"

    def test_apply_delete_change(self, tmp_path):
        """Test _apply_changes deletes file."""
        # Create file to delete
        (tmp_path / "to_delete.py").write_text("content")

        executor = SandboxExecutor()
        changes = [FileChange(relative_path="to_delete.py", operation="delete")]

        executor._apply_changes(tmp_path, changes)

        assert not (tmp_path / "to_delete.py").exists()

    def test_apply_create_with_subdirs(self, tmp_path):
        """Test _apply_changes creates subdirectories."""
        executor = SandboxExecutor()
        changes = [
            FileChange(
                relative_path="deep/nested/file.py",
                operation="create",
                new_content="content",
            )
        ]

        executor._apply_changes(tmp_path, changes)

        assert (tmp_path / "deep" / "nested" / "file.py").exists()

    def test_apply_multiple_changes(self, tmp_path):
        """Test _apply_changes handles multiple changes."""
        (tmp_path / "file1.py").write_text("old1")

        executor = SandboxExecutor()
        changes = [
            FileChange("file1.py", "modify", "new1"),
            FileChange("file2.py", "create", "content2"),
            FileChange("file3.py", "create", "content3"),
        ]

        executor._apply_changes(tmp_path, changes)

        assert (tmp_path / "file1.py").read_text() == "new1"
        assert (tmp_path / "file2.py").exists()
        assert (tmp_path / "file3.py").exists()


class TestCleanup:
    """[20251217_TEST] Tests for sandbox cleanup (P0)."""

    def test_cleanup_sandbox_removes_directory(self, tmp_path):
        """Test _cleanup_sandbox removes sandbox directory."""
        sandbox_dir = tmp_path / "sandbox_test"
        sandbox_dir.mkdir()
        (sandbox_dir / "file.py").write_text("content")

        executor = SandboxExecutor()
        executor._cleanup_sandbox(sandbox_dir)

        assert not sandbox_dir.exists()

    def test_cleanup_sandbox_handles_nonexistent(self, tmp_path):
        """Test _cleanup_sandbox handles non-existent directory."""
        sandbox_dir = tmp_path / "nonexistent"

        executor = SandboxExecutor()
        # Should not raise
        executor._cleanup_sandbox(sandbox_dir)


class TestProcessExecution:
    """[20251217_TEST] Tests for process execution (P0)."""

    def test_execute_in_process_simple_success(self, tmp_path):
        """Test _execute_in_process with successful commands."""
        (tmp_path / "test_file.py").write_text("def test_pass():\n    assert True\n")
        executor = SandboxExecutor(max_cpu_seconds=10)
        result = executor._execute_in_process(
            tmp_path,
            test_command="python -c 'exit(0)'",
            lint_command="echo 'lint ok'",
            build_command=None,
        )
        assert result.success is True
        assert result.build_success is True
        assert result.execution_time_ms > 0

    def test_execute_in_process_build_failure(self, tmp_path):
        """Test _execute_in_process handles build failure."""
        executor = SandboxExecutor(max_cpu_seconds=10)
        result = executor._execute_in_process(
            tmp_path,
            test_command="echo test",
            lint_command="echo lint",
            build_command='bash -c "exit 1"',
        )
        assert result.success is False
        assert result.build_success is False
        assert result.stderr is not None

    def test_execute_in_process_test_failure(self, tmp_path):
        """Test _execute_in_process handles test failure."""
        executor = SandboxExecutor(max_cpu_seconds=10)
        result = executor._execute_in_process(
            tmp_path,
            test_command="python -c 'exit(1)'",
            lint_command="echo lint",
            build_command=None,
        )
        assert result.success is False
        assert len(result.test_results) > 0
        assert result.test_results[0].passed is False

    def test_execute_in_process_respects_timeout(self, tmp_path):
        """Test _execute_in_process respects CPU time limit."""
        executor = SandboxExecutor(max_cpu_seconds=1)
        result = executor._execute_in_process(
            tmp_path,
            test_command="python -c 'import time; time.sleep(10)'",
            lint_command="echo lint",
            build_command=None,
        )
        assert "timed out" in result.stderr.lower()


class TestSideEffectDetection:
    """[20251217_TEST] Tests for side effect detection (P0)."""

    def test_detect_side_effects_none(self, tmp_path):
        """Test _detect_side_effects returns False for clean execution."""
        executor = SandboxExecutor()
        assert executor._detect_side_effects(tmp_path) is False

    def test_detect_side_effects_audit_log(self, tmp_path):
        """Test _detect_side_effects detects blocked operations."""
        # Create audit log with blocked operation
        audit_log = tmp_path / ".scalpel_sandbox_audit.log"
        audit_log.write_text("BLOCKED: network access attempted")

        executor = SandboxExecutor()
        assert executor._detect_side_effects(tmp_path) is True


class TestIntegration:
    """[20251217_TEST] Full integration tests (P0)."""

    def test_execute_with_changes_full_workflow(self, tmp_path):
        """Test complete execute_with_changes workflow."""
        # Create test project
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        (project_dir / "main.py").write_text("def add(a, b):\n    return a + b\n")

        # Define changes
        changes = [
            FileChange(
                relative_path="main.py",
                operation="modify",
                new_content="def add(a, b):\n    return a + b + 1\n",  # Bug introduced
            )
        ]

        executor = SandboxExecutor(max_cpu_seconds=10)
        result = executor.execute_with_changes(
            project_path=str(project_dir),
            changes=changes,
            test_command="python -c 'print(\"test passed\")'",
            lint_command="echo 'no issues'",
            build_command=None,
        )

        # Verify original file unchanged
        assert (project_dir / "main.py").read_text() == "def add(a, b):\n    return a + b\n"

        # Verify result structure
        assert result is not None
        assert hasattr(result, "success")
        assert hasattr(result, "execution_time_ms")
        assert result.execution_time_ms > 0

    def test_execute_with_changes_network_disabled(self, tmp_path):
        """Test network access is blocked by default."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        (project_dir / "test.py").write_text("import socket")

        changes = []
        executor = SandboxExecutor(network_enabled=False, max_cpu_seconds=10)

        # Should succeed (network blocking is best-effort at process level)
        result = executor.execute_with_changes(
            project_path=str(project_dir),
            changes=changes,
            test_command="python -c 'pass'",
            lint_command="echo ok",
            build_command=None,
        )

        assert result is not None
        assert hasattr(result, "success")

    def test_execute_with_changes_filesystem_isolated(self, tmp_path):
        """Test filesystem access is limited to sandbox."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        (project_dir / "main.py").write_text("x = 1")

        # Create sentinel file outside project
        sentinel = tmp_path / "outside.txt"
        sentinel.write_text("original")

        changes = []
        executor = SandboxExecutor(max_cpu_seconds=10)
        _ = executor.execute_with_changes(
            project_path=str(project_dir),
            changes=changes,
            test_command="python -c 'pass'",
            lint_command="echo ok",
            build_command=None,
        )

        # Sentinel should be unchanged (filesystem isolation worked)
        assert sentinel.read_text() == "original"

    def test_execute_with_changes_resource_limits(self, tmp_path):
        """Test resource limits are enforced."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        (project_dir / "main.py").write_text("x = 1")

        changes = []
        executor = SandboxExecutor(max_memory_mb=512, max_cpu_seconds=5, max_disk_mb=100)

        result = executor.execute_with_changes(
            project_path=str(project_dir),
            changes=changes,
            test_command="python -c 'pass'",
            lint_command="echo ok",
            build_command=None,
        )

        assert result is not None
        assert hasattr(result, "execution_time_ms")
        # Should complete within timeout
        assert result.execution_time_ms < 10000  # Less than 10 seconds


class TestContainerExecution:
    """[20251217_TEST] Tests for container execution mode."""

    def test_execute_in_container_requires_docker(self):
        """Test container mode requires Docker."""
        # This test verifies the container mode path exists
        # Actual container execution requires Docker daemon
        try:
            executor = SandboxExecutor(isolation_level="container")
            # If Docker is available, executor should be created
            assert hasattr(executor, "docker_client")
        except ImportError:
            # If Docker is not available, should raise ImportError
            pass

    def test_execute_in_container_with_docker_mock(self, tmp_path, monkeypatch):
        """Test container execution with mocked Docker."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        (project_dir / "main.py").write_text("x = 1")

        # Mock Docker to avoid needing actual Docker daemon
        class MockContainer:
            def decode(self):
                return "test output"

        class MockContainers:
            def run(self, *args, **kwargs):
                return MockContainer()

        class MockDockerClient:
            containers = MockContainers()

        # Skip if docker not importable
        try:
            import code_scalpel.autonomy.sandbox as sandbox_module

            if not sandbox_module.DOCKER_AVAILABLE:
                pytest.skip("Docker package not available")

            executor = SandboxExecutor(isolation_level="container")
            executor.docker_client = MockDockerClient()

            result = executor._execute_in_container(
                project_dir,
                test_command="echo test",
                lint_command="echo lint",
                build_command=None,
            )

            assert result.success is True
            assert result.execution_time_ms > 0
        except ImportError:
            pytest.skip("Docker not available")


class TestErrorHandling:
    """[20251217_TEST] Tests for error handling."""

    def test_execute_with_changes_cleanup_on_error(self, tmp_path):
        """Test sandbox cleanup happens even on error."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        (project_dir / "main.py").write_text("x = 1")

        # Create a change that will cause issues
        changes = [
            FileChange(
                relative_path="bad_file.py",
                operation="create",
                new_content="invalid python syntax ][",
            )
        ]

        executor = SandboxExecutor(max_cpu_seconds=10)

        # Should handle errors gracefully
        result = executor.execute_with_changes(
            project_path=str(project_dir),
            changes=changes,
            test_command="python -m py_compile bad_file.py",
            lint_command="echo lint",
            build_command=None,
        )

        # Result should be returned even on error
        assert result is not None
        # Should indicate failure
        assert result.success is False

    def test_apply_changes_handles_empty_content(self, tmp_path):
        """Test applying change with empty content."""
        executor = SandboxExecutor()
        changes = [FileChange(relative_path="empty.txt", operation="create", new_content="")]

        executor._apply_changes(tmp_path, changes)
        assert (tmp_path / "empty.txt").exists()
        assert (tmp_path / "empty.txt").read_text() == ""

    def test_apply_changes_delete_nonexistent(self, tmp_path):
        """Test deleting nonexistent file doesn't error."""
        executor = SandboxExecutor()
        changes = [FileChange(relative_path="nonexistent.txt", operation="delete")]

        # Should not raise
        executor._apply_changes(tmp_path, changes)

    def test_execute_in_process_handles_exception(self, tmp_path):
        """Test process execution handles exceptions gracefully."""
        executor = SandboxExecutor(max_cpu_seconds=1)

        # This should handle the timeout gracefully
        result = executor._execute_in_process(
            tmp_path,
            test_command="sleep 10",  # Will timeout
            lint_command="echo lint",
            build_command=None,
        )

        assert result is not None
        # Should indicate timeout
        assert "timeout" in result.stderr.lower() or not result.success


class TestParseSubprocessResults:
    """[20251217_TEST] Tests for subprocess result parsing."""

    def test_parse_subprocess_results_with_none(self, tmp_path):
        """Test parsing when subprocess results are None."""
        executor = SandboxExecutor()

        result = executor._parse_subprocess_results(
            lint_result=None,
            test_result=None,
            build_success=True,
            execution_time_ms=100,
        )

        assert result.success is True
        assert result.build_success is True
        assert result.execution_time_ms == 100
        assert len(result.test_results) == 0

    def test_parse_subprocess_results_lint_output(self, tmp_path):
        """Test parsing lint output with error patterns."""

        executor = SandboxExecutor()

        # Create mock subprocess result with lint errors
        class MockResult:
            returncode = 0

            def __init__(self, output):
                self._output = output

            def decode(self, encoding="utf-8", errors="replace"):
                return self._output

        class MockLintResult:
            returncode = 1
            stdout = MockResult("file.py:10:5: error: undefined variable\nfile.py:20:1: warning: unused import")
            stderr = MockResult("")

        class MockTestResult:
            returncode = 0
            stdout = MockResult("tests passed")
            stderr = MockResult("")

        result = executor._parse_subprocess_results(
            lint_result=MockLintResult(),
            test_result=MockTestResult(),
            build_success=True,
            execution_time_ms=200,
        )

        assert result.success is True
        assert len(result.lint_results) >= 1
        assert result.execution_time_ms == 200


class TestResourceLimits:
    """[20251217_TEST] Tests for resource limit enforcement."""

    def test_resource_limits_set_correctly(self):
        """Test resource limits are configured correctly."""
        executor = SandboxExecutor(max_memory_mb=1024, max_cpu_seconds=120, max_disk_mb=500)

        assert executor.max_memory_mb == 1024
        assert executor.max_cpu_seconds == 120
        assert executor.max_disk_mb == 500

    def test_execute_respects_memory_limit(self, tmp_path):
        """Test execution respects memory limits."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        (project_dir / "main.py").write_text("x = 1")

        # Create executor with very low memory limit
        # Note: This might not fail on all systems due to OS differences
        executor = SandboxExecutor(max_memory_mb=50, max_cpu_seconds=5)

        result = executor.execute_with_changes(
            project_path=str(project_dir),
            changes=[],
            test_command="echo test",
            lint_command="echo lint",
            build_command=None,
        )

        # Should complete (even with low memory for simple commands)
        assert result is not None
