"""
[20251217_FEATURE] Mutation Test Gate - Prevent hollow fixes via mutation testing.

Implements v3.0.0 P0 requirement from 3rd party security review:
"What if agent *thinks* it succeeded but actually deleted functionality?"

Solution: After agent claims fix, revert the fix and verify tests fail.
If tests still pass after reverting, the fix was hollow.

Problem Statement:
    # Original test (failing)
    def test_calculate_tax():
        assert calculate_tax(100, 0.1) == 10

    # Agent's "fix" - hollow, deletes functionality
    def test_calculate_tax():
        pass  # Tests pass now! But we lost the test.

    # Or worse - function hollowed out
    def calculate_tax(amount, rate):
        return 0  # Tests might pass if assertions were weak

Acceptance Criteria (P0):
- Detects hollow fixes (tests pass after revert)
- Generates additional mutations
- Calculates mutation score
- Gates on minimum score threshold

Acceptance Criteria (P1):
- Identifies weak tests
- Provides actionable recommendations
"""

import ast
import copy
from dataclasses import dataclass
from enum import Enum

from code_scalpel.autonomy.stubs import SandboxExecutor


class MutationType(Enum):
    """
    Types of mutations to apply.

    [20251217_FEATURE] P0: Mutation types for testing.
    """

    REVERT_FIX = "revert_fix"  # Undo the agent's fix
    NEGATE_CONDITION = "negate"  # Flip boolean conditions
    BOUNDARY_VALUE = "boundary"  # Change +1 to -1, etc.
    NULL_RETURN = "null_return"  # Return None/null/0
    REMOVE_STATEMENT = "remove"  # Delete a statement


@dataclass
class MutationResult:
    """
    Result of a mutation test.

    [20251217_FEATURE] P0: Track whether mutation was caught.
    """

    mutation_type: MutationType
    original_code: str
    mutated_code: str
    tests_failed: bool  # True = good (mutation was caught)
    tests_that_failed: list[str]
    tests_that_passed: list[str]  # These tests are weak


@dataclass
class MutationGateResult:
    """
    Overall result of mutation gate validation.

    [20251217_FEATURE] P0: Complete mutation testing results.
    """

    passed: bool
    mutations_tested: int
    mutations_caught: int  # Tests failed (good)
    mutations_survived: int  # Tests passed (bad - weak tests)
    hollow_fix_detected: bool
    weak_tests: list[str]
    recommendations: list[str]


@dataclass
class Mutation:
    """
    A code mutation for testing.

    [20251217_FEATURE] P0: Mutation definition.
    """

    type: MutationType
    code: str
    description: str


class MutationTestGate:
    """
    Verify fixes are genuine by ensuring tests would fail if bug reintroduced.

    [20251217_FEATURE] v3.0.0 P0 requirement from 3rd party review.

    Addresses 3rd party review feedback on v3.0.0 Autonomy:
    "What if agent *thinks* it succeeded but actually deleted functionality?"

    Solution: After agent claims fix, revert the fix and verify tests fail.
    If tests still pass after reverting, the fix was hollow.

    Acceptance Criteria (P0):
    - Detects hollow fixes (tests pass after revert)
    - Generates additional mutations
    - Calculates mutation score
    - Gates on minimum score threshold

    Acceptance Criteria (P1):
    - Identifies weak tests
    - Provides actionable recommendations
    """

    def __init__(
        self,
        sandbox: SandboxExecutor,
        min_mutation_score: float = 0.8,  # 80% of mutations must be caught
        max_additional_mutations: int = 5,  # [20251217_FEATURE] Configurable per PR review
    ):
        """
        Initialize mutation test gate.

        Args:
            sandbox: Sandbox executor for running tests
            min_mutation_score: Minimum mutation score to pass (default: 0.8)
            max_additional_mutations: Maximum additional mutations to test (default: 5)
        """
        self.sandbox = sandbox
        self.min_mutation_score = min_mutation_score
        self.max_additional_mutations = max_additional_mutations

    def validate_fix(
        self,
        original_code: str,
        fixed_code: str,
        test_files: list[str],
        language: str = "python",
    ) -> MutationGateResult:
        """
        Validate that a fix is genuine, not hollow.

        [20251217_FEATURE] P0: Main validation logic.

        Args:
            original_code: Code before the agent's fix (with bug)
            fixed_code: Code after the agent's fix
            test_files: List of test files to run
            language: Programming language

        Returns:
            MutationGateResult with validation status

        Process:
            1. Verify fixed_code passes tests (sanity check)
            2. Revert to original_code, verify tests fail
            3. Apply additional mutations, verify tests catch them
            4. Calculate mutation score, gate on threshold
        """
        results: list[MutationResult] = []

        # [20251217_FEATURE] Step 1: Sanity check - fixed code should pass
        fixed_result = self.sandbox.run_tests(fixed_code, test_files)
        if not fixed_result.all_passed:
            return MutationGateResult(
                passed=False,
                mutations_tested=0,
                mutations_caught=0,
                mutations_survived=0,
                hollow_fix_detected=False,
                weak_tests=[],
                recommendations=["Fix does not pass tests - not ready for mutation testing"],
            )

        # [20251217_FEATURE] P0: Step 2: Critical - revert fix, tests MUST fail
        revert_result = self._test_mutation(
            mutated_code=original_code,  # Revert to buggy code
            test_files=test_files,
            mutation_type=MutationType.REVERT_FIX,
        )
        results.append(revert_result)

        # [20251217_FEATURE] P0: HOLLOW FIX DETECTION
        if not revert_result.tests_failed:
            # HOLLOW FIX DETECTED
            return MutationGateResult(
                passed=False,
                mutations_tested=1,
                mutations_caught=0,
                mutations_survived=1,
                hollow_fix_detected=True,
                weak_tests=revert_result.tests_that_passed,
                recommendations=[
                    "HOLLOW FIX DETECTED: Reverting the fix does not cause tests to fail.",
                    "The agent may have deleted test assertions or hollowed out the function.",
                    "Review the fix manually before accepting.",
                ],
            )

        # [20251217_FEATURE] P0: Step 3: Additional mutations for thoroughness
        additional_mutations = self._generate_mutations(fixed_code, language)

        for mutation in additional_mutations[: self.max_additional_mutations]:
            result = self._test_mutation(
                mutated_code=mutation.code,
                test_files=test_files,
                mutation_type=mutation.type,
            )
            results.append(result)

        # [20251217_FEATURE] P0: Step 4: Calculate mutation score
        caught = sum(1 for r in results if r.tests_failed)
        survived = sum(1 for r in results if not r.tests_failed)
        score = caught / len(results) if results else 0

        # [20251217_FEATURE] P1: Identify weak tests
        weak_tests: set[str] = set()
        for r in results:
            if not r.tests_failed:
                weak_tests.update(r.tests_that_passed)

        # [20251217_FEATURE] P1: Provide actionable recommendations
        recommendations: list[str] = []
        if survived > 0:
            recommendations.append(f"{survived} mutations survived. Consider strengthening these tests: {weak_tests}")

        return MutationGateResult(
            passed=score >= self.min_mutation_score,
            mutations_tested=len(results),
            mutations_caught=caught,
            mutations_survived=survived,
            hollow_fix_detected=False,
            weak_tests=list(weak_tests),
            recommendations=recommendations,
        )

    def _test_mutation(self, mutated_code: str, test_files: list[str], mutation_type: MutationType) -> MutationResult:
        """
        Run tests against mutated code.

        [20251217_FEATURE] P0: Execute mutation test.
        """
        result = self.sandbox.run_tests(mutated_code, test_files)

        return MutationResult(
            mutation_type=mutation_type,
            original_code="",  # Not needed for result
            mutated_code=mutated_code,
            tests_failed=not result.all_passed,
            tests_that_failed=[t.name for t in result.tests if not t.passed],
            tests_that_passed=[t.name for t in result.tests if t.passed],
        )

    def _generate_mutations(self, code: str, language: str) -> list[Mutation]:
        """
        Generate additional mutations for the code.

        [20251217_FEATURE] P0: Mutation generation for Python.

        Currently supports Python only. Future versions will support
        additional languages.
        """
        mutations: list[Mutation] = []

        if language == "python":
            try:
                tree = ast.parse(code)
            except SyntaxError:
                # Cannot parse - return empty list
                return mutations

            # [20251217_BUGFIX] Track node identity to avoid duplicate mutations
            # per PR review - ast.walk() returns nodes in arbitrary order
            seen_nodes: set[int] = set()

            # [20251217_FEATURE] P0: Mutation: Negate conditions
            for node in ast.walk(tree):
                if isinstance(node, ast.If):
                    node_id = id(node)
                    if node_id in seen_nodes:
                        continue
                    seen_nodes.add(node_id)

                    mutated_tree = copy.deepcopy(tree)
                    # Find the matching node in the copy by line and col offset
                    for m_node in ast.walk(mutated_tree):
                        if (
                            isinstance(m_node, ast.If)
                            and m_node.lineno == node.lineno
                            and m_node.col_offset == node.col_offset
                        ):
                            m_node.test = ast.UnaryOp(op=ast.Not(), operand=m_node.test)
                            break

                    try:
                        mutations.append(
                            Mutation(
                                type=MutationType.NEGATE_CONDITION,
                                code=ast.unparse(mutated_tree),
                                description=f"Negated condition at line {node.lineno}:{node.col_offset}",
                            )
                        )
                    except Exception:
                        # Skip mutations that fail to unparse
                        pass

            # [20251217_FEATURE] P0: Mutation: Change return values
            seen_nodes.clear()  # Reset for next mutation type
            for node in ast.walk(tree):
                if isinstance(node, ast.Return) and node.value:
                    node_id = id(node)
                    if node_id in seen_nodes:
                        continue
                    seen_nodes.add(node_id)

                    mutated_tree = copy.deepcopy(tree)
                    # Find the matching node in the copy by line and col offset
                    for m_node in ast.walk(mutated_tree):
                        if (
                            isinstance(m_node, ast.Return)
                            and m_node.lineno == node.lineno
                            and m_node.col_offset == node.col_offset
                        ):
                            m_node.value = ast.Constant(value=None)
                            break

                    try:
                        mutations.append(
                            Mutation(
                                type=MutationType.NULL_RETURN,
                                code=ast.unparse(mutated_tree),
                                description=f"Changed return to None at line {node.lineno}:{node.col_offset}",
                            )
                        )
                    except Exception:
                        # Skip mutations that fail to unparse
                        pass

        return mutations
