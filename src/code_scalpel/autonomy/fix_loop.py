"""
[20251217_FEATURE] Fix Loop Termination - Supervised fix loop with safety guarantees.

Implements v3.0.0 P0 requirement: Prevent infinite retry loops and ensure safe
escalation to humans.

Safety features:
- Hard limit on retry attempts
- Timeout for total loop duration
- Detection of repeated failures
- Automatic human escalation
- Full audit trail

State Machine:
              ┌─────────────────────────────────────┐
              │           START                     │
              └──────────────┬──────────────────────┘
                    │
                    ▼
              ┌─────────────────────────────────────┐
              │      Analyze Error                  │
              │   (Error-to-Diff Engine)            │
              └──────────────┬──────────────────────┘
                    │
                ┌─────────┴─────────┐
                │   Fixes found?    │
                └─────────┬─────────┘
                    │
              ┌──────────────┼──────────────┐
              │ No           │              │ Yes
              ▼              │              ▼
      ┌──────────────────┐     │    ┌──────────────────────┐
      │  ESCALATE        │     │    │   Apply Best Fix     │
      │  (no_fixes)      │     │    │   in Sandbox         │
      └──────────────────┘     │    └──────────┬───────────┘
                      │               │
                      │               ▼
                      │    ┌──────────────────────┐
                      │    │   Tests Pass?        │
                      │    └──────────┬───────────┘
                      │               │
                      │    ┌──────────┼──────────┐
                      │    │ Yes      │          │ No
                      │    ▼          │          ▼
                  ┌────────────────┐    │   ┌─────────────────┐
                  │    SUCCESS     │    │   │ attempt < max?  │
                  └────────────────┘    │   └────────┬────────┘
                            │            │
                       ┌──────────┼────────────┼──────────┐
                       │ Yes      │            │          │ No
                       ▼          │            │          ▼
                  ┌───────────────────┐ │         ┌────────────────┐
                  │ Update error      │ │         │   ESCALATE     │
                  │ Loop back         │◄┘         │  (max_attempts)│
                  └───────────────────┘           └────────────────┘
"""

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta

from code_scalpel.autonomy.stubs import (
    ErrorAnalysis,
    ErrorToDiffEngine,
    FileChange,
    FixHint,
    SandboxExecutor,
    SandboxResult,
)


@dataclass
class FixAttempt:
    """
    Record of a single fix attempt.

    [20251217_FEATURE] Full audit trail for fix attempts.
    """

    attempt_number: int
    timestamp: datetime
    error_analysis: ErrorAnalysis
    fix_applied: FixHint
    sandbox_result: SandboxResult
    success: bool
    duration_ms: int


@dataclass
class FixLoopResult:
    """
    Final result of fix loop.

    [20251217_FEATURE] Complete termination information and audit trail.
    """

    success: bool
    final_fix: FixHint | None
    attempts: list[FixAttempt]
    termination_reason: str  # "success", "max_attempts", "timeout", "no_fixes", "human_escalation"  # [20251217_BUGFIX] Normalize annotation layout for parser compatibility
    escalated_to_human: bool
    total_duration_ms: int


class FixLoop:
    """
    Supervised fix loop with termination guarantees.

    [20251217_FEATURE] v3.0.0 P0 requirement - Loop termination.

    Safety features:
    - Hard limit on retry attempts
    - Timeout for total loop duration
    - Detection of repeated failures
    - Automatic human escalation
    - Full audit trail

    Acceptance Criteria (P0):
    - Terminates after max_attempts
    - Terminates on timeout
    - Detects and exits on repeated errors
    - Escalates to human on failure
    - Returns on first successful fix
    - Validates fix in sandbox before returning
    - Records all fix attempts
    - Includes timing information
    - Includes error analysis and fix applied
    """

    def __init__(
        self,
        max_attempts: int = 5,
        max_duration_seconds: int = 300,
        min_confidence_threshold: float = 0.5,
        on_escalate: Callable[[str, list[FixAttempt]], None] | None = None,
    ):
        """
        Initialize fix loop.

        Args:
            max_attempts: Maximum number of fix attempts (default: 5)
            max_duration_seconds: Maximum total duration (default: 300s)
            min_confidence_threshold: Minimum fix confidence (default: 0.5)
            on_escalate: Optional callback for human escalation
        """
        self.max_attempts = max_attempts
        self.max_duration = timedelta(seconds=max_duration_seconds)
        self.max_duration_seconds = float(max_duration_seconds)
        self.min_confidence = min_confidence_threshold
        self.on_escalate = on_escalate
        self.logger = logging.getLogger("scalpel.fix_loop")

    def run(
        self,
        initial_error: str,
        source_code: str,
        language: str,
        sandbox: SandboxExecutor,
        error_engine: ErrorToDiffEngine,
        project_path: str,
    ) -> FixLoopResult:
        """
        Run fix loop until success or termination.

        [20251217_FEATURE] Main loop with all P0 termination conditions.

        Args:
            initial_error: The error message to fix
            source_code: Current source code
            language: Programming language
            sandbox: Sandbox executor for testing fixes
            error_engine: Error-to-diff engine
            project_path: Path to project

        Returns:
            FixLoopResult with success/failure and full history
        """
        attempts: list[FixAttempt] = []
        start_monotonic = time.monotonic()
        current_code = source_code
        current_error = initial_error
        seen_errors: set[int] = set()  # Track unique errors to detect loops

        for attempt_num in range(1, self.max_attempts + 1):
            # [20251217_FEATURE] P0: Check timeout
            if (time.monotonic() - start_monotonic) > self.max_duration_seconds:
                self.logger.warning(f"Fix loop timeout after {attempt_num - 1} attempts")
                return self._create_result(
                    attempts=attempts,
                    success=False,
                    reason="timeout",
                    escalated=self._escalate("Timeout exceeded", attempts),
                )

            # [20251217_FEATURE] P0: Detect repeated errors (stuck in loop)
            # Check BEFORE making an attempt to avoid wasted work
            error_hash = hash(current_error)
            if error_hash in seen_errors:
                self.logger.warning(f"Repeated error detected (attempt {attempt_num})")
                return self._create_result(
                    attempts=attempts,
                    success=False,
                    reason="repeated_error",
                    escalated=self._escalate("Stuck in error loop", attempts),
                )
            seen_errors.add(error_hash)

            # [20251217_FEATURE] Analyze current error
            analysis = error_engine.analyze_error(
                error_output=current_error, language=language, source_code=current_code
            )

            # [20251217_FEATURE] P0: Check for fix availability
            valid_fixes = [f for f in analysis.fixes if f.confidence >= self.min_confidence]
            if not valid_fixes:
                self.logger.warning(f"No valid fixes available (attempt {attempt_num})")
                return self._create_result(
                    attempts=attempts,
                    success=False,
                    reason="no_fixes",
                    escalated=self._escalate("No valid fixes available", attempts),
                )

            # Try best fix
            best_fix = valid_fixes[0]
            self.logger.info(f"Attempt {attempt_num}: Applying fix " f"(confidence={best_fix.confidence:.2f})")

            # [20251217_FEATURE] Apply fix and test in sandbox
            patched_code = self._apply_fix(current_code, best_fix)

            # Timeout guard before launching potentially expensive sandbox execution
            if (time.monotonic() - start_monotonic) > self.max_duration_seconds:
                self.logger.warning(f"Fix loop timeout before sandbox execution (attempt {attempt_num})")
                return self._create_result(
                    attempts=attempts,
                    success=False,
                    reason="timeout",
                    escalated=self._escalate("Timeout exceeded", attempts),
                )

            sandbox_result = sandbox.execute_with_changes(
                project_path=project_path,
                changes=[
                    FileChange(
                        relative_path="target_file",  # Would be actual path
                        operation="modify",
                        new_content=patched_code,
                    )
                ],
                test_command="pytest -x",  # Stop on first failure
                lint_command="ruff check",
            )

            # Enforce timeout even if the sandbox call ran long.
            timed_out = (time.monotonic() - start_monotonic) > self.max_duration_seconds

            # [20251217_FEATURE] P0: Record attempt (full audit trail)
            attempt = FixAttempt(
                attempt_number=attempt_num,
                timestamp=datetime.now(),
                error_analysis=analysis,
                fix_applied=best_fix,
                sandbox_result=sandbox_result,
                success=sandbox_result.success,
                duration_ms=sandbox_result.execution_time_ms,
            )
            attempts.append(attempt)

            if timed_out:
                self.logger.warning(f"Fix loop timeout during sandbox execution (attempt {attempt_num})")
                return self._create_result(
                    attempts=attempts,
                    success=False,
                    reason="timeout",
                    escalated=self._escalate("Timeout exceeded", attempts),
                )

            # [20251217_FEATURE] P0: Check success (validates in sandbox)
            if sandbox_result.success:
                self.logger.info(f"Fix successful on attempt {attempt_num}")
                return self._create_result(
                    attempts=attempts,
                    success=True,
                    reason="success",
                    final_fix=best_fix,
                )

            # Update state for next iteration
            current_code = patched_code
            current_error = sandbox_result.stderr

        # [20251217_FEATURE] P0: Max attempts reached - escalate
        self.logger.warning(f"Max attempts ({self.max_attempts}) reached")
        return self._create_result(
            attempts=attempts,
            success=False,
            reason="max_attempts",
            escalated=self._escalate("Max attempts exceeded", attempts),
        )

    def _escalate(self, reason: str, attempts: list[FixAttempt]) -> bool:
        """
        Escalate to human when loop fails.

        [20251217_FEATURE] P0: Human escalation on failure.
        """
        if self.on_escalate:
            self.on_escalate(reason, attempts)
            return True

        self.logger.error(
            f"HUMAN ESCALATION REQUIRED: {reason}\n"
            f"Attempts: {len(attempts)}\n"
            f"Last error: {attempts[-1].error_analysis.message if attempts else 'N/A'}"
        )
        return True

    def _create_result(
        self,
        attempts: list[FixAttempt],
        success: bool,
        reason: str,
        final_fix: FixHint | None = None,
        escalated: bool = False,
    ) -> FixLoopResult:
        """
        Create fix loop result.

        [20251217_FEATURE] P0: Includes timing information and audit trail.
        """
        total_duration = sum(a.duration_ms for a in attempts)

        return FixLoopResult(
            success=success,
            final_fix=final_fix,
            attempts=attempts,
            termination_reason=reason,
            escalated_to_human=escalated,
            total_duration_ms=total_duration,
        )

    def _apply_fix(self, code: str, fix: FixHint) -> str:
        """
        Apply a fix to the code.

        [20251217_FEATURE] Stub implementation - would use actual patching.

        In a real implementation, this would parse the unified diff
        and apply it to the code.
        """
        # Stub implementation - in reality would apply the diff
        return code + "\n# Fix applied: " + fix.description
