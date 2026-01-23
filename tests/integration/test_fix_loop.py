"""
[20251217_TEST] Tests for Fix Loop Termination (v3.0.0 Autonomy).

Tests P0 Acceptance Criteria:
- Fix Loop: Terminates after max_attempts (P0)
- Fix Loop: Terminates on timeout (P0)
- Fix Loop: Detects and exits on repeated errors (P0)
- Fix Loop: Escalates to human on failure (P0)
- Success Detection: Returns on first successful fix (P0)
- Success Detection: Validates fix in sandbox before returning (P0)
- Audit Trail: Records all fix attempts (P0)
- Audit Trail: Includes timing information (P0)
- Audit Trail: Includes error analysis and fix applied (P0)
"""

import tempfile
from datetime import datetime
from unittest.mock import Mock

from code_scalpel.autonomy import FixAttempt, FixLoop
from code_scalpel.autonomy.stubs import (
    ErrorAnalysis,
    ErrorToDiffEngine,
    FixHint,
    SandboxExecutor,
    SandboxResult,
)

SAFE_TMP = tempfile.gettempdir()

# [20251217_BUGFIX] Use stub classes for fix_loop tests (different from error_to_diff classes)


class TestFixLoopTermination:
    """Test fix loop termination conditions (P0)."""

    def test_terminates_after_max_attempts(self):
        """P0: Fix loop terminates after max_attempts."""
        # Setup - each attempt gets a different error to avoid repeated error detection
        sandbox = Mock(spec=SandboxExecutor)
        sandbox.execute_with_changes.side_effect = [
            SandboxResult(
                success=False,
                all_passed=False,
                stdout="",
                stderr="Error 1",
                execution_time_ms=100,
            ),
            SandboxResult(
                success=False,
                all_passed=False,
                stdout="",
                stderr="Error 2",
                execution_time_ms=100,
            ),
            SandboxResult(
                success=False,
                all_passed=False,
                stdout="",
                stderr="Error 3",
                execution_time_ms=100,
            ),
        ]

        error_engine = Mock(spec=ErrorToDiffEngine)
        error_engine.analyze_error.return_value = ErrorAnalysis(
            message="Error",
            error_type="runtime",
            fixes=[
                FixHint(
                    description="Try this fix",
                    confidence=0.8,
                    diff="@@ ...",
                    location="file.py:10",
                )
            ],
        )

        # Execute with max_attempts=3
        fix_loop = FixLoop(max_attempts=3)
        result = fix_loop.run(
            initial_error="Error",
            source_code="code",
            language="python",
            sandbox=sandbox,
            error_engine=error_engine,
            project_path="/tmp/test",
        )

        # Assert
        assert not result.success
        assert result.termination_reason == "max_attempts"
        assert len(result.attempts) == 3
        assert result.escalated_to_human

    def test_terminates_on_timeout(self):
        """P0: Fix loop terminates on timeout."""
        # Setup - simulate slow execution with different errors each time
        sandbox = Mock(spec=SandboxExecutor)

        call_count = [0]

        def slow_execution(*args, **kwargs):
            # Simulate time passing
            import time

            time.sleep(0.1)
            call_count[0] += 1
            return SandboxResult(
                success=False,
                all_passed=False,
                stdout="",
                stderr=f"Error {call_count[0]}",  # Different error each time
                execution_time_ms=100,
            )

        sandbox.execute_with_changes.side_effect = slow_execution

        error_engine = Mock(spec=ErrorToDiffEngine)
        error_engine.analyze_error.return_value = ErrorAnalysis(
            message="Error",
            error_type="runtime",
            fixes=[
                FixHint(
                    description="Fix",
                    confidence=0.8,
                    diff="@@ ...",
                    location="file.py:10",
                )
            ],
        )

        # Execute with very short timeout
        fix_loop = FixLoop(max_attempts=100, max_duration_seconds=1)
        start = datetime.now()
        result = fix_loop.run(
            initial_error="Error",
            source_code="code",
            language="python",
            sandbox=sandbox,
            error_engine=error_engine,
            project_path="/tmp/test",
        )
        duration = (datetime.now() - start).total_seconds()

        # Assert
        assert not result.success
        assert result.termination_reason == "timeout"
        assert duration < 2  # Should terminate quickly
        assert result.escalated_to_human
        assert len(result.attempts) < 100  # Should not reach max_attempts

    def test_detects_repeated_errors(self):
        """P0: Fix loop detects and exits on repeated errors."""
        # Setup
        sandbox = Mock(spec=SandboxExecutor)
        sandbox.execute_with_changes.return_value = SandboxResult(
            success=False,
            all_passed=False,
            stdout="",
            stderr="Same error every time",  # Same error
            execution_time_ms=100,
        )

        error_engine = Mock(spec=ErrorToDiffEngine)
        error_engine.analyze_error.return_value = ErrorAnalysis(
            message="Error",
            error_type="runtime",
            fixes=[
                FixHint(
                    description="Fix attempt",
                    confidence=0.8,
                    diff="@@ ...",
                    location="file.py:10",
                )
            ],
        )

        # Execute
        fix_loop = FixLoop(max_attempts=10)
        result = fix_loop.run(
            initial_error="Same error every time",  # Same as stderr
            source_code="code",
            language="python",
            sandbox=sandbox,
            error_engine=error_engine,
            project_path="/tmp/test",
        )

        # Assert - should detect repeated error on 2nd attempt
        assert not result.success
        assert result.termination_reason == "repeated_error"
        assert len(result.attempts) == 1  # Only 1 attempt before detection
        assert result.escalated_to_human

    def test_escalates_on_no_fixes_available(self):
        """P0: Fix loop escalates when no valid fixes available."""
        # Setup
        sandbox = Mock(spec=SandboxExecutor)

        error_engine = Mock(spec=ErrorToDiffEngine)
        error_engine.analyze_error.return_value = ErrorAnalysis(
            message="Error", error_type="runtime", fixes=[]
        )  # No fixes available

        # Execute
        fix_loop = FixLoop(max_attempts=5)
        result = fix_loop.run(
            initial_error="Complex error",
            source_code="code",
            language="python",
            sandbox=sandbox,
            error_engine=error_engine,
            project_path="/tmp/test",
        )

        # Assert
        assert not result.success
        assert result.termination_reason == "no_fixes"
        assert len(result.attempts) == 0  # No attempts made
        assert result.escalated_to_human

    def test_escalates_on_low_confidence_fixes(self):
        """P0: Fix loop escalates when only low-confidence fixes available."""
        # Setup
        sandbox = Mock(spec=SandboxExecutor)

        error_engine = Mock(spec=ErrorToDiffEngine)
        error_engine.analyze_error.return_value = ErrorAnalysis(
            message="Error",
            error_type="runtime",
            fixes=[
                FixHint(
                    description="Uncertain fix",
                    confidence=0.3,  # Below threshold
                    diff="@@ ...",
                    location="file.py:10",
                )
            ],
        )

        # Execute with min_confidence_threshold=0.5
        fix_loop = FixLoop(max_attempts=5, min_confidence_threshold=0.5)
        result = fix_loop.run(
            initial_error="Error",
            source_code="code",
            language="python",
            sandbox=sandbox,
            error_engine=error_engine,
            project_path="/tmp/test",
        )

        # Assert
        assert not result.success
        assert result.termination_reason == "no_fixes"
        assert result.escalated_to_human

    def test_custom_escalation_callback(self):
        """P0: Fix loop calls custom escalation callback."""
        # Setup
        escalation_called = []

        def on_escalate(reason, attempts):
            escalation_called.append((reason, len(attempts)))

        sandbox = Mock(spec=SandboxExecutor)
        error_engine = Mock(spec=ErrorToDiffEngine)
        error_engine.analyze_error.return_value = ErrorAnalysis(message="Error", error_type="runtime", fixes=[])

        # Execute
        fix_loop = FixLoop(max_attempts=3, on_escalate=on_escalate)
        result = fix_loop.run(
            initial_error="Error",
            source_code="code",
            language="python",
            sandbox=sandbox,
            error_engine=error_engine,
            project_path="/tmp/test",
        )

        # Assert
        assert len(escalation_called) == 1
        assert escalation_called[0][0] == "No valid fixes available"
        assert result.escalated_to_human


class TestFixLoopSuccess:
    """Test fix loop success detection (P0)."""

    def test_returns_on_first_successful_fix(self):
        """P0: Fix loop returns on first successful fix."""
        # Setup
        sandbox = Mock(spec=SandboxExecutor)
        sandbox.execute_with_changes.return_value = SandboxResult(
            success=True,  # Success!
            all_passed=True,
            stdout="All tests passed",
            stderr="",
            execution_time_ms=100,
        )

        error_engine = Mock(spec=ErrorToDiffEngine)
        error_engine.analyze_error.return_value = ErrorAnalysis(
            message="Error",
            error_type="runtime",
            fixes=[
                FixHint(
                    description="The fix",
                    confidence=0.9,
                    diff="@@ ...",
                    location="file.py:10",
                )
            ],
        )

        # Execute
        fix_loop = FixLoop(max_attempts=10)
        result = fix_loop.run(
            initial_error="Error",
            source_code="code",
            language="python",
            sandbox=sandbox,
            error_engine=error_engine,
            project_path="/tmp/test",
        )

        # Assert
        assert result.success
        assert result.termination_reason == "success"
        assert len(result.attempts) == 1  # Only 1 attempt needed
        assert result.final_fix is not None
        assert not result.escalated_to_human

    def test_validates_fix_in_sandbox(self):
        """P0: Fix loop validates fix in sandbox before returning."""
        # Setup
        sandbox = Mock(spec=SandboxExecutor)
        sandbox.execute_with_changes.return_value = SandboxResult(
            success=True,
            all_passed=True,
            stdout="All tests passed",
            stderr="",
            execution_time_ms=100,
        )

        error_engine = Mock(spec=ErrorToDiffEngine)
        error_engine.analyze_error.return_value = ErrorAnalysis(
            message="Error",
            error_type="runtime",
            fixes=[
                FixHint(
                    description="Fix",
                    confidence=0.9,
                    diff="@@ ...",
                    location="file.py:10",
                )
            ],
        )

        # Execute
        fix_loop = FixLoop(max_attempts=3)
        fix_loop.run(
            initial_error="Error",
            source_code="code",
            language="python",
            sandbox=sandbox,
            error_engine=error_engine,
            project_path="/tmp/test",
        )

        # Assert - sandbox.execute_with_changes was called
        assert sandbox.execute_with_changes.called
        call_args = sandbox.execute_with_changes.call_args
        assert call_args is not None
        assert "project_path" in call_args.kwargs
        assert "changes" in call_args.kwargs
        assert "test_command" in call_args.kwargs

    def test_retries_after_failed_fix(self):
        """P0: Fix loop retries after failed fix attempt."""
        # Setup - first attempt fails, second succeeds
        sandbox = Mock(spec=SandboxExecutor)
        sandbox.execute_with_changes.side_effect = [
            SandboxResult(
                success=False,
                all_passed=False,
                stdout="",
                stderr="Still failing",
                execution_time_ms=100,
            ),
            SandboxResult(
                success=True,
                all_passed=True,
                stdout="Success!",
                stderr="",
                execution_time_ms=100,
            ),
        ]

        error_engine = Mock(spec=ErrorToDiffEngine)
        error_engine.analyze_error.side_effect = [
            ErrorAnalysis(
                message="Error 1",
                error_type="runtime",
                fixes=[
                    FixHint(
                        description="Fix 1",
                        confidence=0.8,
                        diff="@@ ...",
                        location="file.py:10",
                    )
                ],
            ),
            ErrorAnalysis(
                message="Error 2",
                error_type="runtime",
                fixes=[
                    FixHint(
                        description="Fix 2",
                        confidence=0.8,
                        diff="@@ ...",
                        location="file.py:10",
                    )
                ],
            ),
        ]

        # Execute
        fix_loop = FixLoop(max_attempts=5)
        result = fix_loop.run(
            initial_error="Error",
            source_code="code",
            language="python",
            sandbox=sandbox,
            error_engine=error_engine,
            project_path="/tmp/test",
        )

        # Assert
        assert result.success
        assert len(result.attempts) == 2
        assert result.attempts[0].success is False
        assert result.attempts[1].success is True


class TestFixLoopAuditTrail:
    """Test fix loop audit trail (P0)."""

    def test_records_all_attempts(self):
        """P0: Fix loop records all fix attempts."""
        # Setup - different errors to avoid repeated error detection
        sandbox = Mock(spec=SandboxExecutor)
        sandbox.execute_with_changes.side_effect = [
            SandboxResult(
                success=False,
                all_passed=False,
                stdout="",
                stderr="Error 1",
                execution_time_ms=100,
            ),
            SandboxResult(
                success=False,
                all_passed=False,
                stdout="",
                stderr="Error 2",
                execution_time_ms=100,
            ),
            SandboxResult(
                success=False,
                all_passed=False,
                stdout="",
                stderr="Error 3",
                execution_time_ms=100,
            ),
        ]

        error_engine = Mock(spec=ErrorToDiffEngine)
        error_engine.analyze_error.return_value = ErrorAnalysis(
            message="Error",
            error_type="runtime",
            fixes=[
                FixHint(
                    description="Fix",
                    confidence=0.8,
                    diff="@@ ...",
                    location="file.py:10",
                )
            ],
        )

        # Execute
        fix_loop = FixLoop(max_attempts=3)
        result = fix_loop.run(
            initial_error="Error",
            source_code="code",
            language="python",
            sandbox=sandbox,
            error_engine=error_engine,
            project_path="/tmp/test",
        )

        # Assert
        assert len(result.attempts) == 3
        for i, attempt in enumerate(result.attempts):
            assert attempt.attempt_number == i + 1
            assert isinstance(attempt, FixAttempt)

    def test_includes_timing_information(self):
        """P0: Fix loop includes timing information in audit trail."""
        # Setup - different errors to avoid repeated error detection
        sandbox = Mock(spec=SandboxExecutor)
        sandbox.execute_with_changes.side_effect = [
            SandboxResult(
                success=False,
                all_passed=False,
                stdout="",
                stderr="Error 1",
                execution_time_ms=150,
            ),
            SandboxResult(
                success=False,
                all_passed=False,
                stdout="",
                stderr="Error 2",
                execution_time_ms=150,
            ),
        ]

        error_engine = Mock(spec=ErrorToDiffEngine)
        error_engine.analyze_error.return_value = ErrorAnalysis(
            message="Error",
            error_type="runtime",
            fixes=[
                FixHint(
                    description="Fix",
                    confidence=0.8,
                    diff="@@ ...",
                    location="file.py:10",
                )
            ],
        )

        # Execute
        fix_loop = FixLoop(max_attempts=2)
        result = fix_loop.run(
            initial_error="Error",
            source_code="code",
            language="python",
            sandbox=sandbox,
            error_engine=error_engine,
            project_path="/tmp/test",
        )

        # Assert
        assert result.total_duration_ms == 300  # [20251217_REFACTOR] 2 attempts × 150ms
        for attempt in result.attempts:
            assert attempt.duration_ms == 150
            assert isinstance(attempt.timestamp, datetime)

    def test_includes_error_analysis_and_fix(self):
        """P0: Audit trail includes error analysis and fix applied."""
        # Setup
        sandbox = Mock(spec=SandboxExecutor)
        sandbox.execute_with_changes.return_value = SandboxResult(
            success=True, all_passed=True, stdout="OK", stderr="", execution_time_ms=100
        )

        expected_fix = FixHint(
            description="The perfect fix",
            confidence=0.95,
            diff="@@ specific diff",
            location="file.py:42",
        )

        error_engine = Mock(spec=ErrorToDiffEngine)
        error_engine.analyze_error.return_value = ErrorAnalysis(
            message="Specific error message",
            error_type="syntax",
            line_number=42,
            fixes=[expected_fix],
        )

        # Execute
        fix_loop = FixLoop(max_attempts=5)
        result = fix_loop.run(
            initial_error="Specific error",
            source_code="code",
            language="python",
            sandbox=sandbox,
            error_engine=error_engine,
            project_path="/tmp/test",
        )

        # Assert
        assert len(result.attempts) == 1
        attempt = result.attempts[0]
        assert attempt.error_analysis.message == "Specific error message"
        assert attempt.error_analysis.error_type == "syntax"
        assert attempt.error_analysis.line_number == 42
        assert attempt.fix_applied == expected_fix
        assert attempt.sandbox_result.success is True
