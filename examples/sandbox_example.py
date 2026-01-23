"""
[20251217_DOCS] Example: Speculative Execution (Sandboxed)

This example demonstrates how to test proposed code changes in an isolated sandbox
before applying them to the main codebase.

[20260114_BUGFIX] Updated to use SandboxExecutorImpl (renamed from SandboxExecutor).
"""

import tempfile
from pathlib import Path

from code_scalpel.autonomy import FileChange
from code_scalpel.autonomy import SandboxExecutorImpl as SandboxExecutor


def main():
    """Demonstrate sandbox execution."""
    # Create a temporary project directory
    with tempfile.TemporaryDirectory() as project_dir:
        project_path = Path(project_dir)

        # Create a simple Python project
        (project_path / "calculator.py").write_text(
            "def add(a, b):\n" "    return a + b\n" "\n" "def multiply(a, b):\n" "    return a * b\n"
        )

        (project_path / "test_calculator.py").write_text(
            "from calculator import add, multiply\n"
            "\n"
            "def test_add():\n"
            "    assert add(2, 3) == 5\n"
            "\n"
            "def test_multiply():\n"
            "    assert multiply(2, 3) == 6\n"
        )

        print("Original project created.")
        print("=" * 60)

        # Define proposed changes (introducing a bug)
        changes = [
            FileChange(
                relative_path="calculator.py",
                operation="modify",
                new_content=(
                    "def add(a, b):\n"
                    "    return a + b + 1  # BUG: Off-by-one error\n"
                    "\n"
                    "def multiply(a, b):\n"
                    "    return a * b\n"
                ),
            )
        ]

        # Test changes in sandbox
        print("\nTesting proposed changes in sandbox...")
        executor = SandboxExecutor(
            isolation_level="process",
            network_enabled=False,
            max_memory_mb=512,
            max_cpu_seconds=30,
        )

        result = executor.execute_with_changes(
            project_path=str(project_path),
            changes=changes,
            test_command="pytest -xvs",
            lint_command="echo 'Linting...'",
            build_command=None,
        )

        print("=" * 60)
        print("\nSandbox Results:")
        print(f"  Success: {result.success}")
        print(f"  Build Success: {result.build_success}")
        print(f"  Execution Time: {result.execution_time_ms}ms")
        print(f"  Side Effects Detected: {result.side_effects_detected}")
        print("\n  Test Results:")
        for test in result.test_results:
            status = "✓ PASS" if test.passed else "✗ FAIL"
            print(f"    {status} {test.name} ({test.duration_ms}ms)")
            if test.error_message:
                print(f"      Error: {test.error_message}")

        if result.lint_results:
            print("\n  Lint Results:")
            for lint in result.lint_results:
                print(f"    {lint.severity.upper()}: {lint.file}:{lint.line} - {lint.message}")

        # Verify original files are unchanged
        original_content = (project_path / "calculator.py").read_text()
        assert "BUG" not in original_content, "Original file should be unchanged!"
        print("\n✓ Original files remain unchanged (sandbox isolation verified)")

        print("=" * 60)
        print("\nConclusion:")
        if result.success:
            print("  ✓ Changes are safe to apply to main codebase")
        else:
            print("  ✗ Changes introduce failures - do NOT apply to main codebase")
            print("  → Review test failures and fix issues before applying")


if __name__ == "__main__":
    main()
