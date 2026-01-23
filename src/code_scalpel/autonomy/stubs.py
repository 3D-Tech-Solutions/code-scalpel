"""
[20251217_FEATURE] Stub implementations for autonomy modules.

Placeholder classes for dependencies that will be implemented in future releases.
These stubs enable the Fix Loop and Mutation Gate implementations to be tested
independently.
"""

from dataclasses import dataclass, field


@dataclass
class ErrorAnalysis:
    """Analysis of an error message."""

    message: str
    error_type: str  # "syntax", "runtime", "type", etc.
    line_number: int | None = None
    column_number: int | None = None
    fixes: list["FixHint"] = field(default_factory=list)


@dataclass
class FixHint:
    """A suggested fix for an error."""

    description: str
    confidence: float  # 0.0 to 1.0
    diff: str  # Unified diff format
    location: str  # File and line info


@dataclass
class FileChange:
    """A file change to apply."""

    relative_path: str
    operation: str  # "modify", "create", "delete"
    new_content: str | None = None


@dataclass
# [20251217_DOCS] Keep this name (not "TestResult") to avoid pytest collection
# conflicts with common TestResult types during test discovery.
class ExecutionTestResult:
    """Result of a single test execution."""

    name: str
    passed: bool
    duration_ms: int
    error: str | None = None


@dataclass
class SandboxResult:
    """Result of sandbox execution."""

    success: bool
    all_passed: bool
    stdout: str
    stderr: str
    execution_time_ms: int
    tests: list["ExecutionTestResult"] = field(default_factory=list)


class SandboxExecutor:
    """
    Stub for sandbox execution environment.

    In a real implementation, this would provide isolated execution
    of code changes with proper containerization.
    """

    def execute_with_changes(
        self,
        project_path: str,
        changes: list[FileChange],
        test_command: str,
        lint_command: str | None = None,
    ) -> SandboxResult:
        """Execute tests with applied changes in isolated environment."""
        # Stub implementation - would actually run in container/sandbox
        return SandboxResult(
            success=False,
            all_passed=False,
            stdout="",
            stderr="Not implemented",
            execution_time_ms=0,
        )

    def run_tests(self, code: str, test_files: list[str]) -> SandboxResult:
        """Run tests against code."""
        # Stub implementation
        return SandboxResult(
            success=False,
            all_passed=False,
            stdout="",
            stderr="Not implemented",
            execution_time_ms=0,
        )


class ErrorToDiffEngine:
    """
    Stub for error-to-diff engine.

    In a real implementation, this would analyze errors and generate
    fix suggestions using AI/ML techniques.
    """

    def analyze_error(self, error_output: str, language: str, source_code: str) -> ErrorAnalysis:
        """Analyze error and suggest fixes."""
        # Stub implementation
        return ErrorAnalysis(message=error_output, error_type="unknown", fixes=[])
