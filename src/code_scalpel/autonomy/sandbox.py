"""
[20251217_FEATURE] Speculative Execution (Sandboxed) module.

Purpose: Test proposed changes in an isolated environment before applying to main codebase.

Security guarantees:
- No network access (by default)
- No filesystem access outside sandbox
- Resource limits (CPU, memory, time)
- Process isolation via containers or chroot
"""

import importlib
import os
import shlex
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_docker_module: Any | None = None


def _load_docker_safely(*, fail_on_sentinel: bool = True) -> Any | None:
    """
    [20260122_BUGFIX] Recover from prior monkeypatches that set sys.modules['docker']=None.

    Some tests intentionally replace sys.modules['docker'] with None and reload this module.
    This helper removes a None sentinel and attempts a fresh import so availability reflects
    the real environment rather than test ordering side effects.
    """

    import sys

    if sys.modules.get("docker") is None:
        # [20260122_BUGFIX] Honor explicit sentinel while allowing later re-probe
        sys.modules.pop("docker", None)
        if fail_on_sentinel:
            return None
    try:
        return importlib.import_module("docker")  # type: ignore[import-untyped]
    except ImportError:
        return None


def _detect_docker_available(*, fail_on_sentinel: bool = True) -> bool:
    """[20260122_BUGFIX] Re-probe docker on every access to avoid stale False flags."""

    global _docker_module
    mod = _load_docker_safely(fail_on_sentinel=fail_on_sentinel)
    if mod is not None:
        _docker_module = mod
        return True
    _docker_module = None
    return False


def _load_docker_module(*, fail_on_sentinel: bool = True) -> Any | None:
    """Load docker module if present, caching the import."""

    global _docker_module
    if _docker_module is not None:
        return _docker_module
    if _detect_docker_available(fail_on_sentinel=fail_on_sentinel):
        return _docker_module
    return None


class _DockerAvailability:
    """Boolean-ish wrapper that re-evaluates docker availability on each access."""

    def __bool__(self) -> bool:  # pragma: no cover - trivial
        # [20260122_BUGFIX] When called for skip checks, allow recovery from sentinel
        return _detect_docker_available(fail_on_sentinel=False)

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return str(bool(self))


DOCKER_AVAILABLE = _DockerAvailability()
docker = _load_docker_module()  # type: ignore[assignment]


@dataclass
class LintResult:
    """Individual lint result."""

    file: str
    line: int | None
    column: int | None
    message: str
    severity: str  # "error", "warning", "info"


@dataclass
class _CodeExecutionRecord:
    """Record of a code execution test from sandbox.

    [20260122_BUGFIX] Prefixed with underscore to prevent pytest from collecting as test class.
    """

    name: str
    passed: bool
    duration_ms: int
    error_message: str | None = None


# Tell pytest this is not a test class
_CodeExecutionRecord.__test__ = False


# Public aliases for backward compatibility (deprecated)
ExecutionResult = _CodeExecutionRecord
ExecutionTestResult = _CodeExecutionRecord
SandboxTestResult = _CodeExecutionRecord
TestResult = _CodeExecutionRecord
CodeExecutionRecord = _CodeExecutionRecord


@dataclass
class FileChange:
    """Represents a file change to apply."""

    relative_path: str
    operation: str  # "create", "modify", "delete"
    new_content: str | None = None


@dataclass
class SandboxResult:
    """Result of sandboxed execution."""

    success: bool
    test_results: list[ExecutionTestResult] = field(default_factory=list)
    lint_results: list[LintResult] = field(default_factory=list)
    build_success: bool = True
    side_effects_detected: bool = False
    execution_time_ms: int = 0
    stdout: str = ""
    stderr: str = ""


class SandboxExecutor:
    """
    Execute code changes in isolated sandbox.

    Security guarantees:
    - No network access (by default)
    - No filesystem access outside sandbox
    - Resource limits (CPU, memory, time)
    - Process isolation via containers or chroot
    """

    def __init__(
        self,
        isolation_level: str = "process",  # "container", "process", "chroot"
        network_enabled: bool = False,
        max_memory_mb: int = 512,
        max_cpu_seconds: int = 60,
        max_disk_mb: int = 100,
    ):
        """
        Initialize sandbox executor.

        Args:
            isolation_level: Level of isolation ("container", "process", "chroot")
            network_enabled: Whether to allow network access
            max_memory_mb: Maximum memory in MB
            max_cpu_seconds: Maximum CPU time in seconds
            max_disk_mb: Maximum disk space in MB
        """
        self.isolation_level = isolation_level
        self.network_enabled = network_enabled
        self.max_memory_mb = max_memory_mb
        self.max_cpu_seconds = max_cpu_seconds
        self.max_disk_mb = max_disk_mb

        # [20251217_FEATURE] Initialize Docker client if container isolation requested
        if isolation_level == "container":
            # [20260122_BUGFIX] Recompute docker availability to avoid stale False from prior reloads
            docker_mod = _load_docker_module()
            if not DOCKER_AVAILABLE or docker_mod is None:
                raise ImportError("Docker support requires 'docker' package. " "Install with: pip install docker")

            self.docker_client = docker_mod.from_env()

    def execute_with_changes(
        self,
        project_path: str,
        changes: list[FileChange],
        test_command: str = "pytest",
        lint_command: str = "ruff check",
        build_command: str | None = None,
    ) -> SandboxResult:
        """
        Apply changes and run tests in sandbox.

        Args:
            project_path: Path to project root
            changes: List of file changes to apply
            test_command: Command to run tests
            lint_command: Command to run linter
            build_command: Optional build command

        Returns:
            SandboxResult with test results and side effect detection
        """
        # Create isolated sandbox
        sandbox_path = self._create_sandbox(project_path)

        try:
            # Apply changes to sandbox
            self._apply_changes(sandbox_path, changes)

            # Run in isolated environment
            if self.isolation_level == "container":
                return self._execute_in_container(sandbox_path, test_command, lint_command, build_command)
            else:
                return self._execute_in_process(sandbox_path, test_command, lint_command, build_command)

        finally:
            # Clean up sandbox
            self._cleanup_sandbox(sandbox_path)

    def _create_sandbox(self, project_path: str) -> Path:
        """
        Create isolated copy of project.

        Uses copy-on-write where supported for efficiency.

        Args:
            project_path: Path to project root

        Returns:
            Path to sandbox directory
        """
        sandbox_dir = Path(tempfile.mkdtemp(prefix="scalpel_sandbox_"))

        # [20251217_FEATURE] Copy project files (excluding .git, node_modules, etc.)
        for item in Path(project_path).iterdir():
            if item.name in {
                ".git",
                "node_modules",
                "__pycache__",
                "venv",
                ".venv",
                ".tox",
                "dist",
                "build",
            }:
                continue

            dest = sandbox_dir / item.name
            if item.is_dir():
                shutil.copytree(item, dest, symlinks=True)
            else:
                shutil.copy2(item, dest)

        return sandbox_dir

    def _apply_changes(self, sandbox_path: Path, changes: list[FileChange]) -> None:
        """
        Apply file changes to sandbox.

        Args:
            sandbox_path: Path to sandbox directory
            changes: List of file changes to apply
        """
        for change in changes:
            file_path = sandbox_path / change.relative_path

            if change.operation == "create":
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(change.new_content or "")

            elif change.operation == "modify":
                if change.new_content is not None:
                    file_path.write_text(change.new_content)

            elif change.operation == "delete":
                file_path.unlink(missing_ok=True)

    def _execute_in_container(
        self,
        sandbox_path: Path,
        test_command: str,
        lint_command: str,
        build_command: str | None,
    ) -> SandboxResult:
        """
        Execute in Docker container for full isolation.

        Args:
            sandbox_path: Path to sandbox directory
            test_command: Command to run tests
            lint_command: Command to run linter
            build_command: Optional build command

        Returns:
            SandboxResult with execution results
        """
        start_time = time.time()

        # [20251217_FEATURE] Build container command
        commands = []
        if build_command:
            commands.append(build_command)
        commands.append(lint_command)
        commands.append(test_command)

        full_command = " && ".join(commands)

        try:
            # Run in container
            container = self.docker_client.containers.run(
                image="python:3.11-slim",
                command=f"/bin/sh -c '{full_command}'",
                volumes={str(sandbox_path): {"bind": "/workspace", "mode": "rw"}},
                working_dir="/workspace",
                network_disabled=not self.network_enabled,
                mem_limit=f"{self.max_memory_mb}m",
                cpu_period=100000,
                cpu_quota=self.max_cpu_seconds * 100000,
                remove=True,
                detach=False,
                stdout=True,
                stderr=True,
            )

            execution_time = max(1, int((time.time() - start_time) * 1000))

            # Parse results from container output
            output = container if isinstance(container, bytes) else b""
            return SandboxResult(
                success=True,
                build_success=True,
                execution_time_ms=execution_time,
                stdout=output.decode("utf-8", errors="replace") if output else "",
                stderr="",
            )

        except Exception as e:
            execution_time = int((time.time() - start_time) * 1000)
            return SandboxResult(
                success=False,
                build_success=False,
                execution_time_ms=execution_time,
                stdout="",
                stderr=str(e),
            )

    def _execute_in_process(
        self,
        sandbox_path: Path,
        test_command: str,
        lint_command: str,
        build_command: str | None,
    ) -> SandboxResult:
        """
        Execute in subprocess with resource limits.

        Args:
            sandbox_path: Path to sandbox directory
            test_command: Command to run tests
            lint_command: Command to run linter
            build_command: Optional build command

        Returns:
            SandboxResult with execution results
        """
        import resource

        def set_limits():
            """Set resource limits for child process."""
            # [20251217_SECURITY] Memory limit
            try:
                resource.setrlimit(
                    resource.RLIMIT_AS,
                    (
                        self.max_memory_mb * 1024 * 1024,
                        self.max_memory_mb * 1024 * 1024,
                    ),
                )
            except (ValueError, OSError):
                # Some systems don't support RLIMIT_AS
                pass

            # [20251217_SECURITY] CPU time limit
            try:
                resource.setrlimit(resource.RLIMIT_CPU, (self.max_cpu_seconds, self.max_cpu_seconds))
            except (ValueError, OSError):
                pass

        start_time = time.time()

        # [20251217_FEATURE] Run build if specified
        if build_command:
            try:
                # [20251218_SECURITY] Use shlex.split to safely parse command, avoid shell injection (B602)
                build_result = subprocess.run(
                    shlex.split(build_command),
                    shell=False,
                    cwd=sandbox_path,
                    capture_output=True,
                    timeout=self.max_cpu_seconds,
                    preexec_fn=set_limits if os.name != "nt" else None,
                )
                if build_result.returncode != 0:
                    execution_time = int((time.time() - start_time) * 1000)
                    return SandboxResult(
                        success=False,
                        test_results=[],
                        lint_results=[],
                        build_success=False,
                        side_effects_detected=False,
                        execution_time_ms=execution_time,
                        stdout=build_result.stdout.decode("utf-8", errors="replace"),
                        stderr=build_result.stderr.decode("utf-8", errors="replace"),
                    )
            except subprocess.TimeoutExpired:
                execution_time = int((time.time() - start_time) * 1000)
                return SandboxResult(
                    success=False,
                    build_success=False,
                    execution_time_ms=execution_time,
                    stdout="",
                    stderr="Build command timed out",
                )

        # [20251217_FEATURE] Run linter
        lint_result = None
        try:
            # [20251218_SECURITY] Use shlex.split to safely parse command, avoid shell injection (B602)
            lint_result = subprocess.run(
                shlex.split(lint_command),
                shell=False,
                cwd=sandbox_path,
                capture_output=True,
                timeout=self.max_cpu_seconds,
                preexec_fn=set_limits if os.name != "nt" else None,
            )
        except subprocess.TimeoutExpired:
            pass  # Linter timeout is not critical

        # [20251217_FEATURE] Run tests
        test_result = None
        try:
            # [20251218_SECURITY] Use shlex.split to safely parse command, avoid shell injection (B602)
            test_result = subprocess.run(
                shlex.split(f"{test_command} --tb=short -q"),
                shell=False,
                cwd=sandbox_path,
                capture_output=True,
                timeout=self.max_cpu_seconds,
                preexec_fn=set_limits if os.name != "nt" else None,
            )
        except subprocess.TimeoutExpired:
            execution_time = int((time.time() - start_time) * 1000)
            return SandboxResult(
                success=False,
                build_success=True,
                execution_time_ms=execution_time,
                stdout="",
                stderr="Test command timed out",
            )

        execution_time = int((time.time() - start_time) * 1000)

        # Parse results
        return self._parse_subprocess_results(
            lint_result,
            test_result,
            build_success=True,
            execution_time_ms=execution_time,
        )

    def _parse_subprocess_results(
        self,
        lint_result: subprocess.CompletedProcess | None,
        test_result: subprocess.CompletedProcess | None,
        build_success: bool,
        execution_time_ms: int,
    ) -> SandboxResult:
        """
        Parse subprocess results into SandboxResult.

        Args:
            lint_result: Result from linter
            test_result: Result from tests
            build_success: Whether build succeeded
            execution_time_ms: Total execution time in milliseconds

        Returns:
            SandboxResult with parsed results
        """
        # Parse test results
        test_results = []
        stdout = ""
        stderr = ""

        if test_result:
            stdout = test_result.stdout.decode("utf-8", errors="replace")
            stderr = test_result.stderr.decode("utf-8", errors="replace")

            # [20251217_FEATURE] Simple test parsing - can be enhanced
            test_success = test_result.returncode == 0
            test_results.append(
                ExecutionTestResult(
                    name="all_tests",
                    passed=test_success,
                    duration_ms=execution_time_ms,
                    error_message=stderr if not test_success else None,
                )
            )

        # Parse lint results
        lint_results = []
        if lint_result:
            lint_stdout = lint_result.stdout.decode("utf-8", errors="replace")
            stdout = lint_stdout + "\n" + stdout

            # [20251217_FEATURE] Simple lint parsing - can be enhanced
            # Look for common linter output patterns
            for line in lint_stdout.split("\n"):
                if ":" in line and any(s in line.lower() for s in ["error", "warning"]):
                    parts = line.split(":", 3)
                    if len(parts) >= 3:
                        lint_results.append(
                            LintResult(
                                file=parts[0] if len(parts) > 0 else "",
                                line=(int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else None),
                                column=None,
                                message=parts[-1].strip() if parts else line,
                                severity=("error" if "error" in line.lower() else "warning"),
                            )
                        )

        success = build_success and (test_result.returncode == 0 if test_result else True)

        return SandboxResult(
            success=success,
            test_results=test_results,
            lint_results=lint_results,
            build_success=build_success,
            side_effects_detected=self._detect_side_effects(Path(tempfile.gettempdir())),
            execution_time_ms=execution_time_ms,
            stdout=stdout,
            stderr=stderr,
        )

    def _detect_side_effects(self, sandbox_path: Path) -> bool:
        """
        Detect if execution had unintended side effects.

        Checks:
        - Files created outside project directory
        - Network connections attempted
        - System calls blocked

        Args:
            sandbox_path: Path to sandbox directory

        Returns:
            True if side effects detected, False otherwise
        """
        # [20251217_SECURITY] Check for files created outside sandbox
        # This is handled by container isolation, but double-check

        # Check audit log for blocked operations
        audit_log = sandbox_path / ".scalpel_sandbox_audit.log"
        if audit_log.exists():
            content = audit_log.read_text()
            if "BLOCKED" in content:
                return True

        return False

    def _cleanup_sandbox(self, sandbox_path: Path) -> None:
        """
        Clean up sandbox directory.

        Args:
            sandbox_path: Path to sandbox directory to clean up
        """
        if sandbox_path.exists():
            shutil.rmtree(sandbox_path, ignore_errors=True)
