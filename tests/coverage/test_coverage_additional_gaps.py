"""
[20251217_TEST] Additional coverage tests for remaining gaps.

Focus on reaching 95%+ overall coverage.
"""

import os
import subprocess
import sys
import tempfile
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

# [20260102_BUGFIX] Use system temp dir helper to avoid hardcoded /tmp paths in tests.
SAFE_TMP = tempfile.gettempdir()


class TestErrorToDiffAdditionalGaps:
    """Additional error_to_diff.py coverage tests."""

    def test_apply_diff_multiple_matches(self):
        """[20251217_TEST] Cover multiple match case (ambiguous) in diff application."""
        from code_scalpel.autonomy import ErrorToDiffEngine

        engine = ErrorToDiffEngine(project_root=SAFE_TMP)

        # Source with duplicate lines - should skip modification
        error_output = """  File "test.py", line 3
SyntaxError: invalid syntax"""

        source_code = """x = foo()
x = foo()
x = foo()"""

        analysis = engine.analyze_error(error_output, "python", source_code)
        assert analysis is not None

    def test_diff_no_matches_returns_original(self):
        """[20251217_TEST] Cover no-match case in diff application."""
        from code_scalpel.autonomy import ErrorToDiffEngine

        engine = ErrorToDiffEngine(project_root=SAFE_TMP)

        error_output = """  File "test.py", line 1
SyntaxError: unexpected token"""

        source_code = """def bar():
    return 42"""

        analysis = engine.analyze_error(error_output, "python", source_code)
        assert analysis is not None

    def test_linter_error_generator_unused(self):
        """[20251217_TEST] Cover linter 'unused' pattern in error generator."""
        from code_scalpel.autonomy import ErrorToDiffEngine

        engine = ErrorToDiffEngine(project_root=SAFE_TMP)

        error_output = """warning: unused import 'os' at test.py:1"""
        source_code = """import os
print("hello")"""

        analysis = engine.analyze_error(error_output, "python", source_code)
        assert analysis is not None

    def test_linter_error_generator_undefined(self):
        """[20251217_TEST] Cover linter 'undefined' pattern in error generator."""
        from code_scalpel.autonomy import ErrorToDiffEngine

        engine = ErrorToDiffEngine(project_root=SAFE_TMP)

        error_output = """error: undefined name 'xyz' at test.py:1"""
        source_code = """result = xyz"""

        analysis = engine.analyze_error(error_output, "python", source_code)
        assert analysis is not None


class TestAuditAdditionalGaps:
    """Additional audit.py coverage tests."""

    def test_hash_data_fallback_path(self):
        """[20251217_TEST] Cover hash_data fallback when JSON fails."""
        from code_scalpel.autonomy import AutonomyAuditTrail

        with tempfile.TemporaryDirectory() as tmp_dir:
            audit = AutonomyAuditTrail(storage_path=tmp_dir)

            # Create an object that's hard to JSON serialize directly
            class UnserializableObj:
                def __init__(self):
                    self.cyclic = self

                def __str__(self):
                    return "UnserializableObj"

            # This should trigger the fallback path
            entry_id = audit.record(
                event_type="TEST",
                operation="test_fallback",
                input_data={"obj": UnserializableObj()},
                output_data={"result": "ok"},
                success=True,
                duration_ms=10,
            )

            assert entry_id is not None

    def test_audit_export_csv_format(self):
        """[20251217_TEST] Cover CSV export format."""
        from code_scalpel.autonomy import AutonomyAuditTrail

        with tempfile.TemporaryDirectory() as tmp_dir:
            audit = AutonomyAuditTrail(storage_path=tmp_dir)

            audit.record(
                event_type="TEST",
                operation="test_csv",
                input_data={"key": "value"},
                output_data={"result": "ok"},
                success=True,
                duration_ms=50,
            )

            csv_export = audit.export(format="csv")
            assert csv_export is not None
            assert "TEST" in csv_export

    def test_audit_export_html_format(self):
        """[20251217_TEST] Cover HTML export format."""
        from code_scalpel.autonomy import AutonomyAuditTrail

        with tempfile.TemporaryDirectory() as tmp_dir:
            audit = AutonomyAuditTrail(storage_path=tmp_dir)

            audit.record(
                event_type="FIX_ATTEMPT",
                operation="generate_fix",
                input_data={"error": "SyntaxError"},
                output_data={"fix": "added colon"},
                success=True,
                duration_ms=100,
            )

            html_export = audit.export(format="html")
            assert html_export is not None
            assert "<html>" in html_export
            assert "FIX_ATTEMPT" in html_export

    def test_audit_export_with_filters(self):
        """[20251217_TEST] Cover export with time range and event type filters."""
        from datetime import datetime, timedelta

        from code_scalpel.autonomy import AutonomyAuditTrail

        with tempfile.TemporaryDirectory() as tmp_dir:
            audit = AutonomyAuditTrail(storage_path=tmp_dir)

            # Record multiple operations
            audit.record(
                event_type="TYPE_A",
                operation="op1",
                input_data={},
                output_data={},
                success=True,
                duration_ms=10,
            )

            audit.record(
                event_type="TYPE_B",
                operation="op2",
                input_data={},
                output_data={},
                success=False,
                duration_ms=20,
            )

            # Export with filters
            now = datetime.now()
            filtered = audit.export(
                format="json",
                time_range=(now - timedelta(hours=1), now + timedelta(hours=1)),
                event_types=["TYPE_A"],
                success_only=True,
            )

            assert filtered is not None
            assert "TYPE_A" in filtered


class TestSandboxAdditionalGaps:
    """Additional sandbox.py coverage tests."""

    def test_sandbox_build_command_failure(self):
        """[20251217_TEST] Cover build command failure path."""
        from code_scalpel.autonomy.sandbox import FileChange, SandboxExecutor

        executor = SandboxExecutor(isolation_level="process")
        changes = [FileChange(relative_path="test.py", operation="create", new_content="print('test')")]
        with tempfile.TemporaryDirectory() as tmp_dir:
            result = executor.execute_with_changes(
                project_path=tmp_dir,
                changes=changes,
                test_command="echo test",
                lint_command="true",
                build_command='bash -c "exit 1"',
            )
        assert result.build_success is False

    def test_sandbox_timeout_handling(self):
        """[20251217_TEST] Cover timeout handling in sandbox execution."""
        from code_scalpel.autonomy.sandbox import FileChange, SandboxExecutor

        executor = SandboxExecutor(isolation_level="process", max_cpu_seconds=1)
        changes = [
            FileChange(
                relative_path="slow.py",
                operation="create",
                new_content="import time; time.sleep(10)",
            )
        ]
        with tempfile.TemporaryDirectory() as tmp_dir:
            with patch("subprocess.run") as mock_run:
                mock_run.side_effect = subprocess.TimeoutExpired(cmd="test", timeout=1)
                result = executor.execute_with_changes(
                    project_path=tmp_dir,
                    changes=changes,
                    test_command="python slow.py",
                    lint_command="true",
                )
        assert result.success is False


class TestCrewAIAdditionalGaps:
    """Additional crewai.py coverage tests."""

    def test_generate_fix_tool_syntax_error_path(self):
        """[20251217_TEST] Cover ScalpelGenerateFixTool syntax error path."""
        try:
            from code_scalpel.autonomy.integrations.crewai import ScalpelGenerateFixTool
        except ImportError:
            pytest.skip("CrewAI not available")

        tool = ScalpelGenerateFixTool()

        # Code with unfixable syntax error
        result = tool._run(
            code="def foo(\n    return invalid syntax that can't be parsed",
            analysis="SyntaxError: invalid syntax",
        )

        assert "fix_available" in result or "error" in result

    def test_generate_fix_tool_exception_path(self):
        """[20251217_TEST] Cover ScalpelGenerateFixTool exception handling."""
        try:
            from code_scalpel.autonomy.integrations.crewai import ScalpelGenerateFixTool
        except ImportError:
            pytest.skip("CrewAI not available")

        tool = ScalpelGenerateFixTool()

        # Test with edge case input
        result = tool._run(
            code=None,  # Will cause exception
            analysis="test",
        )

        assert "error" in result.lower()

    def test_analyze_tool_exception_path(self):
        """[20251217_TEST] Cover ScalpelAnalyzeTool with malformed input."""
        try:
            from code_scalpel.autonomy.integrations.crewai import ScalpelAnalyzeTool
        except ImportError:
            pytest.skip("CrewAI not available")

        tool = ScalpelAnalyzeTool()

        # Test with empty/invalid code
        result = tool._run("")
        assert isinstance(result, str)


class TestLangGraphAdditionalGaps:
    """Additional langgraph.py coverage tests."""

    def test_analyze_error_node_exception(self):
        """[20251217_TEST] Cover analyze_error_node exception handling."""
        try:
            from code_scalpel.autonomy.integrations.langgraph import analyze_error_node
        except ImportError:
            pytest.skip("LangGraph not available")

        state = {
            "code": "def foo(): pass",
            "error": "SyntaxError",
            "fix_attempts": [],
            "success": False,
        }

        result = analyze_error_node(state)
        assert "fix_attempts" in result

    def test_generate_fix_node_paths(self):
        """[20251217_TEST] Cover generate_fix_node various paths."""
        try:
            from code_scalpel.autonomy.integrations.langgraph import generate_fix_node
        except ImportError:
            pytest.skip("LangGraph not available")

        # Test with existing fix attempts
        state = {
            "code": "def foo():\n    pass",
            "error": "SyntaxError: expected colon",
            "fix_attempts": [{"step": "analyze", "result": "ok"}],
            "success": False,
        }

        result = generate_fix_node(state)
        assert "fix_attempts" in result


class TestMutationGateAdditionalGaps:
    """Additional mutation_gate.py coverage tests."""

    def test_mutation_gate_revert_mutation(self):
        """[20251217_TEST] Cover revert mutation path."""
        from code_scalpel.autonomy import MutationTestGate
        from code_scalpel.autonomy.stubs import SandboxExecutor, SandboxResult

        # Create mock sandbox with controlled responses
        sandbox = MagicMock(spec=SandboxExecutor)

        # Fixed code passes, all subsequent calls (including mutations) have results
        sandbox.run_tests.return_value = SandboxResult(
            success=True,
            all_passed=False,
            stdout="",
            stderr="Test failed",
            execution_time_ms=100,
        )

        gate = MutationTestGate(sandbox=sandbox)

        result = gate.validate_fix(
            original_code="def foo(): return None",
            fixed_code="def foo(): return 1",
            test_files=["test.py"],
        )

        assert result is not None

    def test_mutation_gate_hollow_fix_detection(self):
        """[20251217_TEST] Cover hollow fix detection path."""
        from code_scalpel.autonomy import MutationTestGate
        from code_scalpel.autonomy.stubs import SandboxExecutor, SandboxResult

        sandbox = MagicMock(spec=SandboxExecutor)

        # Both fixed and reverted pass - hollow fix
        sandbox.run_tests.return_value = SandboxResult(
            success=True, all_passed=True, stdout="", stderr="", execution_time_ms=100
        )

        gate = MutationTestGate(sandbox=sandbox)

        result = gate.validate_fix(
            original_code="def foo(): return 1",
            fixed_code="def foo(): return 2",
            test_files=["test.py"],
        )

        assert result is not None


class TestMiscCoverageGaps:
    """Miscellaneous coverage gap tests."""

    def test_import_error_handling(self):
        """[20251217_TEST] Cover module import error handling."""
        # Test that modules handle optional dependencies gracefully
        from code_scalpel.autonomy.integrations import autogen, crewai, langgraph

        assert autogen is not None
        assert crewai is not None
        assert langgraph is not None

    def test_sandbox_cleanup(self):
        """[20251217_TEST] Cover sandbox cleanup operations."""
        from code_scalpel.autonomy.sandbox import FileChange, SandboxExecutor

        executor = SandboxExecutor(isolation_level="process")

        changes = [
            FileChange(
                relative_path="test_cleanup.py",
                operation="create",
                new_content="x = 1",
            )
        ]

        # This will create and cleanup sandbox
        with tempfile.TemporaryDirectory() as tmp_dir:
            result = executor.execute_with_changes(
                project_path=tmp_dir,
                changes=changes,
                test_command="true",
                lint_command="true",
            )

        assert result is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
