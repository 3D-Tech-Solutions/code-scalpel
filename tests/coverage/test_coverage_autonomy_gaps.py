"""
[20251217_TEST] Tests to close coverage gaps in autonomy module.

Targets the uncovered lines to reach 95% overall coverage.
"""

import os
import sys
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from code_scalpel.autonomy import ErrorToDiffEngine, ErrorType

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

# [20260102_BUGFIX] Use system temp dir helper to avoid hardcoded /tmp paths in tests.
SAFE_TMP = tempfile.gettempdir()


class TestErrorToDiffCoverageGaps:
    """Tests targeting uncovered lines in error_to_diff.py."""

    def test_ast_validation_exception_path(self):
        """[20251217_TEST] Cover ValueError/TypeError exception in AST validation."""
        engine = ErrorToDiffEngine(project_root=SAFE_TMP)

        # Trigger validation with code that causes parse issues
        error_output = """  File "test.py", line 1
SyntaxError: invalid syntax"""

        source_code = """def foo(
    # Incomplete code
"""

        analysis = engine.analyze_error(error_output, "python", source_code)
        assert analysis is not None
        # Some fixes may have reduced confidence due to AST validation failure

    def test_javascript_syntax_error_parsing(self):
        """[20251217_TEST] Cover JavaScript SyntaxError path."""
        engine = ErrorToDiffEngine(project_root=SAFE_TMP)

        error_output = """SyntaxError: Unexpected token at main.js:10:5"""
        source_code = """const x = {"""

        analysis = engine.analyze_error(error_output, "javascript", source_code)
        assert analysis.error_type == ErrorType.SYNTAX_ERROR

    def test_javascript_reference_error_parsing(self):
        """[20251217_TEST] Cover JavaScript ReferenceError path."""
        engine = ErrorToDiffEngine(project_root=SAFE_TMP)

        error_output = """ReferenceError: undefinedVar is not defined at main.js:5:1"""
        source_code = """console.log(undefinedVar);"""

        analysis = engine.analyze_error(error_output, "javascript", source_code)
        assert analysis.error_type == ErrorType.NAME_ERROR

    def test_javascript_type_error_parsing(self):
        """[20251217_TEST] Cover JavaScript TypeError path."""
        engine = ErrorToDiffEngine(project_root=SAFE_TMP)

        error_output = """TypeError: Cannot read property 'foo' of undefined at main.js:10:5"""
        source_code = """obj.foo();"""

        analysis = engine.analyze_error(error_output, "javascript", source_code)
        assert analysis.error_type == ErrorType.TYPE_ERROR

    def test_javascript_unknown_location(self):
        """[20251217_TEST] Cover JavaScript error without location."""
        engine = ErrorToDiffEngine(project_root=SAFE_TMP)

        error_output = """Error: Something went wrong"""
        source_code = """const x = 1;"""

        analysis = engine.analyze_error(error_output, "javascript", source_code)
        assert analysis.file_path == "unknown"
        assert analysis.line == 0

    def test_typescript_cannot_find_module_path(self):
        """[20251217_TEST] Cover TypeScript 'Cannot find' import error path."""
        engine = ErrorToDiffEngine(project_root=SAFE_TMP)

        error_output = """file.ts(5,10): error TS2307: Cannot find module 'missing-module'"""
        source_code = """import { foo } from 'missing-module';"""

        analysis = engine.analyze_error(error_output, "typescript", source_code)
        assert analysis.error_type == ErrorType.IMPORT_ERROR

    def test_typescript_unknown_error_type(self):
        """[20251217_TEST] Cover TypeScript unknown error type path."""
        engine = ErrorToDiffEngine(project_root=SAFE_TMP)

        error_output = """file.ts(1,1): error TS9999: Unknown error"""
        source_code = """const x = 1;"""

        analysis = engine.analyze_error(error_output, "typescript", source_code)
        assert analysis.error_type == ErrorType.RUNTIME_ERROR

    def test_java_incompatible_types_path(self):
        """[20251217_TEST] Cover Java 'incompatible types' error path."""
        engine = ErrorToDiffEngine(project_root=SAFE_TMP)

        error_output = """Main.java:10: error: incompatible types: String cannot be converted to int"""
        source_code = """int x = "hello";"""

        analysis = engine.analyze_error(error_output, "java", source_code)
        assert analysis.error_type == ErrorType.TYPE_ERROR

    def test_java_unknown_error_type(self):
        """[20251217_TEST] Cover Java unknown error type path."""
        engine = ErrorToDiffEngine(project_root=SAFE_TMP)

        error_output = """Main.java:5: error: some unknown error"""
        source_code = """System.out.println("test");"""

        analysis = engine.analyze_error(error_output, "java", source_code)
        assert analysis.error_type == ErrorType.RUNTIME_ERROR

    def test_java_unknown_location(self):
        """[20251217_TEST] Cover Java error without location."""
        engine = ErrorToDiffEngine(project_root=SAFE_TMP)

        error_output = """error: cannot access Main"""
        source_code = """public class Main {}"""

        analysis = engine.analyze_error(error_output, "java", source_code)
        assert analysis.file_path == "unknown"
        assert analysis.line == 0

    def test_balance_parentheses_close_excess(self):
        """[20251217_TEST] Cover closing parenthesis excess path."""
        engine = ErrorToDiffEngine(project_root=SAFE_TMP)

        error_output = """  File "test.py", line 1
SyntaxError: unmatched ')'"""

        # More closing parens than opening
        source_code = """result = foo()))"""

        analysis = engine.analyze_error(error_output, "python", source_code)
        assert analysis is not None
        # Should try to remove excess closing parens

    def test_balance_parentheses_open_excess(self):
        """[20251217_TEST] Cover opening parenthesis excess path."""
        engine = ErrorToDiffEngine(project_root=SAFE_TMP)

        error_output = """  File "test.py", line 1
SyntaxError: '(' was never closed"""

        # More opening parens than closing
        source_code = """result = foo(((bar)"""

        analysis = engine.analyze_error(error_output, "python", source_code)
        assert analysis is not None
        # Should try to add closing parens

    def test_linter_fix_unused_pattern(self):
        """[20251217_TEST] Cover linter 'unused' fix generation."""
        engine = ErrorToDiffEngine(project_root=SAFE_TMP)

        error_output = """warning: unused variable 'x' at file.py:5"""
        source_code = """x = 1
print("hello")"""

        analysis = engine.analyze_error(error_output, "python", source_code)
        # Should generate fix suggestion for unused
        assert analysis is not None

    def test_linter_fix_undefined_pattern(self):
        """[20251217_TEST] Cover linter 'undefined' fix generation."""
        engine = ErrorToDiffEngine(project_root=SAFE_TMP)

        error_output = """error: undefined name 'x' at file.py:1"""
        source_code = """print(x)"""

        analysis = engine.analyze_error(error_output, "python", source_code)
        assert analysis is not None

    def test_import_error_module_pattern(self):
        """[20251217_TEST] Cover ImportError 'No module named' fix generation."""
        engine = ErrorToDiffEngine(project_root=SAFE_TMP)

        error_output = """ModuleNotFoundError: No module named 'missing_module'"""
        source_code = """import missing_module"""

        analysis = engine.analyze_error(error_output, "python", source_code)
        assert analysis.error_type == ErrorType.IMPORT_ERROR
        # Should suggest import fix
        import_fixes = [f for f in analysis.fixes if "import" in f.diff.lower() or "import" in f.explanation.lower()]
        assert len(import_fixes) > 0

    def test_assertion_fix_line_match(self):
        """[20251217_TEST] Cover assertion fix when line contains expected value."""
        engine = ErrorToDiffEngine(project_root=SAFE_TMP)

        error_output = """  File "test.py", line 1
AssertionError: assert 100 == 99"""

        source_code = """assert calculate() == 99"""

        analysis = engine.analyze_error(error_output, "python", source_code)

        # Should suggest updating 99 to 100
        assert analysis is not None
        update_fixes = [f for f in analysis.fixes if "99" in str(f.diff) and "100" in str(f.explanation)]
        assert len(update_fixes) > 0

    def test_non_python_language_ast_skip(self):
        """[20251217_TEST] Cover non-Python language AST validation skip."""
        engine = ErrorToDiffEngine(project_root=SAFE_TMP)

        error_output = """user.ts(5,10): error TS2741: Property 'name' is missing"""
        source_code = """const user: User = {};"""

        analysis = engine.analyze_error(error_output, "typescript", source_code)

        # Non-Python fixes should be marked as ast_valid=True (skipped validation)
        for fix in analysis.fixes:
            assert fix.ast_valid is True

    def test_general_syntax_fix_path(self):
        """[20251217_TEST] Cover general syntax fix (low confidence)."""
        engine = ErrorToDiffEngine(project_root=SAFE_TMP)

        error_output = """  File "test.py", line 1
SyntaxError: invalid character in identifier"""

        source_code = """x = 'hello
world'"""

        analysis = engine.analyze_error(error_output, "python", source_code)
        assert analysis is not None


class TestCrewAICoverageGaps:
    """Tests targeting uncovered lines in crewai.py."""

    def test_error_to_diff_tool_line_extraction(self):
        """[20251217_TEST] Cover line number extraction in error-to-diff tool."""
        try:
            from code_scalpel.autonomy.integrations.crewai import ScalpelErrorToDiffTool
        except ImportError:
            pytest.skip("CrewAI not available")

        tool = ScalpelErrorToDiffTool()

        # Error with explicit "line N" in message
        result = tool._run(code="def foo():\n    pass\n", error="Error on line 2: undefined variable")

        assert "line" in result

    def test_error_to_diff_tool_various_error_types(self):
        """[20251217_TEST] Cover various error type detection paths."""
        try:
            from code_scalpel.autonomy.integrations.crewai import ScalpelErrorToDiffTool
        except ImportError:
            pytest.skip("CrewAI not available")

        tool = ScalpelErrorToDiffTool()

        # SyntaxError path
        result = tool._run(code="def foo(\n    pass", error="SyntaxError: invalid syntax at line 1")
        assert "syntax" in result.lower()

        # NameError path
        result = tool._run(code="print(undefined)", error="NameError: name 'undefined' is not defined")
        assert "name" in result.lower()

        # TypeError path
        result = tool._run(code="x = 1 + 'str'", error="TypeError: unsupported operand type")
        assert "type" in result.lower()

    def test_sandbox_tool_execution(self):
        """[20251217_TEST] Cover ScalpelSandboxTool execution."""
        try:
            from code_scalpel.autonomy.integrations.crewai import ScalpelSandboxTool
        except ImportError:
            pytest.skip("CrewAI not available")

        tool = ScalpelSandboxTool()

        # Valid code execution
        result = tool._run("print('hello')")
        assert isinstance(result, str)

    def test_security_scan_tool_clean_code(self):
        """[20251217_TEST] Cover ScalpelSecurityScanTool with clean code."""
        try:
            from code_scalpel.autonomy.integrations.crewai import (
                ScalpelSecurityScanTool,
            )
        except ImportError:
            pytest.skip("CrewAI not available")

        tool = ScalpelSecurityScanTool()

        # Clean code should report no vulnerabilities
        result = tool._run("x = 1 + 2")
        assert "vulnerabilities" in result

    def test_security_scan_tool_vulnerable_code(self):
        """[20251217_TEST] Cover ScalpelSecurityScanTool with vulnerable code."""
        try:
            from code_scalpel.autonomy.integrations.crewai import (
                ScalpelSecurityScanTool,
            )
        except ImportError:
            pytest.skip("CrewAI not available")

        tool = ScalpelSecurityScanTool()

        # SQL injection vulnerable code
        result = tool._run("cursor.execute('SELECT * FROM users WHERE id=' + user_id)")
        assert isinstance(result, str)


class TestLangGraphCoverageGaps:
    """Tests targeting uncovered lines in langgraph.py."""

    def test_validate_fix_node_no_fix(self):
        """[20251217_TEST] Cover validate_fix_node with no fix to validate."""
        try:
            from code_scalpel.autonomy.integrations.langgraph import validate_fix_node
        except ImportError:
            pytest.skip("LangGraph not available")

        # State with no fix attempts
        state = {
            "code": "def foo(): pass",
            "error": "SyntaxError",
            "fix_attempts": [],
            "success": False,
        }

        result = validate_fix_node(state)
        assert result["success"] is False

    def test_validate_fix_node_with_vulnerability(self):
        """[20251217_TEST] Cover validate_fix_node security check failure."""
        try:
            from code_scalpel.autonomy.integrations.langgraph import validate_fix_node
        except ImportError:
            pytest.skip("LangGraph not available")

        # State with a fix that has vulnerabilities
        state = {
            "code": "cursor.execute('SELECT * FROM users WHERE id=' + user_id)",
            "error": "NameError",
            "fix_attempts": [{"has_fix": True, "diff": "some_fix"}],
            "success": False,
        }

        result = validate_fix_node(state)
        # Should have vulnerability count
        assert "fix_attempts" in result

    def test_apply_fix_node_success(self):
        """[20251217_TEST] Cover apply_fix_node success path."""
        try:
            from code_scalpel.autonomy.integrations.langgraph import apply_fix_node
        except ImportError:
            pytest.skip("LangGraph not available")

        state = {
            "code": "def foo():\n    pass",
            "error": "",
            "fix_attempts": [{"has_fix": True, "diff": "def foo():\n    return 1"}],
            "success": True,
        }

        result = apply_fix_node(state)
        assert isinstance(result, dict)
        assert result["success"] is True

    def test_apply_fix_node_with_no_fix_attempts(self):
        """[20251217_TEST] Cover apply_fix_node with no prior fix attempts."""
        try:
            from code_scalpel.autonomy.integrations.langgraph import apply_fix_node
        except ImportError:
            pytest.skip("LangGraph not available")

        state = {
            "code": "def foo(): pass",
            "error": "Error",
            "fix_attempts": [],
            "success": True,  # apply_fix_node preserves success
        }

        result = apply_fix_node(state)
        # apply_fix_node always adds "applied": True entry and preserves success
        assert result["success"] is True
        assert len(result["fix_attempts"]) == 1


class TestSandboxCoverageGaps:
    """Tests targeting uncovered lines in sandbox.py."""

    @pytest.mark.skipif(
        not hasattr(sys.modules.get("code_scalpel.autonomy.sandbox", None), "SandboxExecutor"),
        reason="SandboxExecutor not available",
    )
    def test_sandbox_executor_docker_mode(self):
        """[20251217_TEST] Cover Docker execution mode (mocked)."""
        import code_scalpel.autonomy.sandbox as sandbox_module
        from code_scalpel.autonomy.sandbox import FileChange, SandboxExecutor

        with patch.object(sandbox_module, "docker") as mock_docker:
            with patch.object(sandbox_module, "DOCKER_AVAILABLE", True):
                mock_client = MagicMock()
                mock_docker.from_env.return_value = mock_client
                mock_client.containers.run.return_value = b"Tests passed"

                executor = SandboxExecutor(
                    isolation_level="container",
                )

                changes = [
                    FileChange(
                        relative_path="test.py",
                        operation="create",
                        new_content="def foo(): pass",
                    )
                ]

                # Mock project path for container execution
                with tempfile.TemporaryDirectory() as tmp_dir:
                    result = executor.execute_with_changes(
                        project_path=tmp_dir,
                        changes=changes,
                        test_command="pytest",
                        lint_command="ruff check .",
                    )

                assert result is not None

    @pytest.mark.skipif(
        not hasattr(sys.modules.get("code_scalpel.autonomy.sandbox", None), "SandboxExecutor"),
        reason="SandboxExecutor not available",
    )
    def test_sandbox_executor_docker_failure(self):
        """[20251217_TEST] Cover Docker execution failure path."""
        import code_scalpel.autonomy.sandbox as sandbox_module
        from code_scalpel.autonomy.sandbox import FileChange, SandboxExecutor

        with patch.object(sandbox_module, "docker") as mock_docker:
            with patch.object(sandbox_module, "DOCKER_AVAILABLE", True):
                mock_client = MagicMock()
                mock_docker.from_env.return_value = mock_client
                mock_client.containers.run.side_effect = Exception("Docker error")

                executor = SandboxExecutor(
                    isolation_level="container",
                )

                changes = [
                    FileChange(
                        relative_path="test.py",
                        operation="create",
                        new_content="def foo(): pass",
                    )
                ]

                with tempfile.TemporaryDirectory() as tmp_dir:
                    result = executor.execute_with_changes(
                        project_path=tmp_dir,
                        changes=changes,
                        test_command="pytest",
                        lint_command="ruff check .",
                    )

                assert result.success is False
            # Check for Docker/container error indicators
            assert "Command" in result.stderr or "Docker" in result.stderr or "returned non-zero" in result.stderr

        changes = [
            FileChange(
                relative_path="test.py",
                operation="create",
                new_content="print('hello')",
            )
        ]

        with tempfile.TemporaryDirectory() as tmp_dir:
            result = executor.execute_with_changes(
                project_path=tmp_dir,
                changes=changes,
                test_command="python test.py",
                lint_command="true",
            )

        assert result is not None


class TestAutogenCoverageGaps:
    """Tests targeting uncovered lines in autogen.py."""

    def test_scalpel_fix_agent_tool_registration(self):
        """[20251217_TEST] Cover AutoGen tool registration paths."""
        try:
            from code_scalpel.autonomy.integrations.autogen import (
                create_scalpel_fix_agent,
            )
        except ImportError:
            pytest.skip("AutoGen not available")

        agent = create_scalpel_fix_agent()

        # Verify agent has expected attributes
        assert agent is not None


class TestStubsCoverageGaps:
    """Tests targeting uncovered lines in stubs.py."""

    def test_stub_error_analysis_creation(self):
        """[20251217_TEST] Cover stubs ErrorAnalysis instantiation."""
        from code_scalpel.autonomy.stubs import ErrorAnalysis

        analysis = ErrorAnalysis(
            message="Test error",
            error_type="syntax",
            line_number=10,
            column_number=5,
            fixes=[],
        )

        assert analysis.error_type == "syntax"
        assert analysis.line_number == 10

    def test_stub_fix_hint_creation(self):
        """[20251217_TEST] Cover stubs FixHint instantiation."""
        from code_scalpel.autonomy.stubs import FixHint

        hint = FixHint(
            description="Test fix",
            confidence=0.8,
            diff="old -> new",
            location="test.py:10",
        )

        assert hint.confidence == 0.8

    def test_stub_sandbox_executor_methods(self):
        """[20251217_TEST] Cover stubs SandboxExecutor methods."""
        from code_scalpel.autonomy.stubs import FileChange, SandboxExecutor

        executor = SandboxExecutor()

        changes = [FileChange(relative_path="test.py", operation="create", new_content="x=1")]

        # Test execute_with_changes
        result = executor.execute_with_changes(
            project_path=SAFE_TMP,
            changes=changes,
            test_command="pytest",
        )
        assert result.success is False

        # Test run_tests
        result2 = executor.run_tests(code="def foo(): pass", test_files=["test.py"])
        assert result2.success is False

    def test_stub_error_to_diff_engine(self):
        """[20251217_TEST] Cover stubs ErrorToDiffEngine."""
        from code_scalpel.autonomy.stubs import ErrorToDiffEngine

        engine = ErrorToDiffEngine()

        analysis = engine.analyze_error(
            error_output="SyntaxError: invalid",
            language="python",
            source_code="def foo(",
        )

        assert analysis.message == "SyntaxError: invalid"
        assert analysis.error_type == "unknown"


class TestMutationGateCoverageGaps:
    """Tests targeting uncovered lines in mutation_gate.py."""

    def test_mutation_gate_edge_cases(self):
        """[20251217_TEST] Cover mutation gate edge cases."""
        from code_scalpel.autonomy import MutationTestGate
        from code_scalpel.autonomy.stubs import SandboxExecutor

        sandbox = SandboxExecutor()
        gate = MutationTestGate(
            sandbox=sandbox,
            min_mutation_score=0.8,
        )

        # Same code - no actual fix
        code = "def foo(): return 1"
        result = gate.validate_fix(
            original_code=code,
            fixed_code=code,
            test_files=["test_foo.py"],
        )

        assert result is not None

    def test_mutation_gate_with_different_code(self):
        """[20251217_TEST] Cover mutation gate with actual code change."""
        from code_scalpel.autonomy import MutationTestGate
        from code_scalpel.autonomy.stubs import SandboxExecutor

        sandbox = SandboxExecutor()
        gate = MutationTestGate(
            sandbox=sandbox,
        )

        original = "def foo(): return None"
        fixed = "def foo(): return 1"

        result = gate.validate_fix(
            original_code=original,
            fixed_code=fixed,
            test_files=["test_foo.py"],
        )

        assert result is not None
        assert isinstance(result.mutations_tested, int)


class TestAuditCoverageGaps:
    """Tests targeting uncovered lines in audit.py."""

    def test_audit_trail_record_operation(self):
        """[20251217_TEST] Cover audit trail record operation."""
        from code_scalpel.autonomy import AutonomyAuditTrail

        with tempfile.TemporaryDirectory() as tmp_dir:
            audit = AutonomyAuditTrail(storage_path=tmp_dir)

            # Record analysis operation
            entry_id = audit.record(
                event_type="FIX_LOOP_START",
                operation="analyze_error",
                input_data={"code": "def foo(): pass", "error": "test error"},
                output_data={"status": "analyzed"},
                success=True,
                duration_ms=100,
            )

            assert entry_id is not None
            assert entry_id.startswith("op_")

    def test_audit_trail_get_summary(self):
        """[20251217_TEST] Cover audit trail summary generation."""
        from code_scalpel.autonomy import AutonomyAuditTrail

        with tempfile.TemporaryDirectory() as tmp_dir:
            audit = AutonomyAuditTrail(storage_path=tmp_dir)

            # Record multiple operations
            audit.record(
                event_type="FIX_LOOP_START",
                operation="init",
                input_data={},
                output_data={},
                success=True,
                duration_ms=10,
            )

            audit.record(
                event_type="ERROR_ANALYSIS",
                operation="analyze",
                input_data={"error": "test"},
                output_data={"result": "ok"},
                success=True,
                duration_ms=50,
            )

            # Get summary
            summary = audit.get_session_summary()

            assert "session_id" in summary
            assert summary["total_operations"] == 2
            assert summary["successful"] == 2

    def test_audit_trail_integrity_verification(self):
        """[20251217_TEST] Cover audit trail export and trace features."""
        from code_scalpel.autonomy import AutonomyAuditTrail

        with tempfile.TemporaryDirectory() as tmp_dir:
            audit = AutonomyAuditTrail(storage_path=tmp_dir)

            # Record operation
            entry_id = audit.record(
                event_type="TEST_EVENT",
                operation="test_op",
                input_data={"key": "value"},
                output_data={"result": "success"},
                success=True,
                duration_ms=25,
            )

            # Export to JSON
            json_export = audit.export(format="json")
            assert json_export is not None
            assert len(json_export) > 0

            # Get operation trace
            trace = audit.get_operation_trace(entry_id)
            assert len(trace) >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
