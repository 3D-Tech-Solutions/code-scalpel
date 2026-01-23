"""
[20251217_FEATURE] Autonomy module - v3.0.0 autonomous code repair features.

This module provides supervised autonomous code repair capabilities with
safety guarantees:

1. Error-to-Diff Engine: Converts error messages to actionable fix hints
   with confidence scoring and human review flagging.

2. Fix Loop Termination: Prevents infinite retry loops with hard limits,
   timeouts, and repeated error detection.

3. Mutation Test Gate: Prevents "hollow fixes" where tests pass because
   functionality was deleted, not because the bug was fixed.

4. Audit Trail: Cryptographically-hashed immutable audit log of all
   autonomous operations for compliance and debugging.

5. Framework Integrations: LangGraph state machines, CrewAI tools,
   and AutoGen function schemas for multi-agent workflows.

6. Sandboxed Execution: Speculative execution in isolated temp directories
   with automatic cleanup, resource limits, and side effect detection.

Features:
- Multi-language error parsing (Python, TypeScript, Java)
- Confidence-scored fix generation
- Bounded fix attempts with timeout
- Repeated error detection
- Human escalation on failure
- Full audit trail with SHA-256 hashing
- Hollow fix detection via mutation testing
- Speculative execution in isolated sandbox
- LangGraph, CrewAI, AutoGen integrations

Usage:
    from code_scalpel.autonomy import (
        ErrorToDiffEngine,
        ErrorAnalysis,
        FixLoop,
        MutationTestGate,
        AutonomyAuditTrail,
        SandboxExecutor,
    )

References:
- DEVELOPMENT_ROADMAP.md: v3.0.0 Autonomy specifications
- docs/: Architecture and design documentation
"""

# [20251217_FEATURE] Audit Trail
from code_scalpel.autonomy.audit import AuditEntry, AutonomyAuditTrail

# [20251217_FEATURE] Error-to-Diff Engine (primary exports)
from code_scalpel.autonomy.error_to_diff import (
    ErrorAnalysis,
    ErrorToDiffEngine,
    ErrorType,
    FixHint,
    ParsedError,
)

# [20251217_FEATURE] Fix Loop Termination
from code_scalpel.autonomy.fix_loop import FixAttempt, FixLoop, FixLoopResult

# [20251217_FEATURE] Mutation Test Gate
from code_scalpel.autonomy.mutation_gate import (
    Mutation,
    MutationGateResult,
    MutationResult,
    MutationTestGate,
    MutationType,
)

# [20251217_FEATURE] Sandboxed Execution
from code_scalpel.autonomy.sandbox import ExecutionTestResult, FileChange, LintResult
from code_scalpel.autonomy.sandbox import SandboxExecutor as SandboxExecutorImpl
from code_scalpel.autonomy.sandbox import SandboxResult as SandboxResultImpl

# [20251217_FEATURE] Stubs for external implementations (aliased to avoid conflicts)
from code_scalpel.autonomy.stubs import ErrorAnalysis as StubErrorAnalysis
from code_scalpel.autonomy.stubs import ErrorToDiffEngine as StubErrorToDiffEngine
from code_scalpel.autonomy.stubs import ExecutionTestResult as StubExecutionTestResult
from code_scalpel.autonomy.stubs import FileChange as StubFileChange
from code_scalpel.autonomy.stubs import FixHint as StubFixHint
from code_scalpel.autonomy.stubs import SandboxExecutor as StubSandboxExecutor
from code_scalpel.autonomy.stubs import SandboxResult as StubSandboxResult

__all__ = [
    # Error-to-Diff Engine (primary)
    "ErrorType",
    "FixHint",
    "ErrorAnalysis",
    "ErrorToDiffEngine",
    "ParsedError",
    # Fix Loop
    "FixLoop",
    "FixLoopResult",
    "FixAttempt",
    # Mutation Gate
    "MutationTestGate",
    "MutationGateResult",
    "MutationResult",
    "Mutation",
    "MutationType",
    # Audit Trail
    "AuditEntry",
    "AutonomyAuditTrail",
    # Sandbox (implementation)
    "SandboxExecutorImpl",
    "SandboxResultImpl",
    "FileChange",
    "ExecutionTestResult",
    "LintResult",
    # Stubs (for fix_loop/mutation_gate internal use)
    "StubErrorAnalysis",
    "StubFixHint",
    "StubFileChange",
    "StubExecutionTestResult",
    "StubSandboxResult",
    "StubSandboxExecutor",
    "StubErrorToDiffEngine",
]

# [20251225_RELEASE] v3.3.0 - Project Reorganization (Phases 1-4)
__version__ = "1.0.0"
