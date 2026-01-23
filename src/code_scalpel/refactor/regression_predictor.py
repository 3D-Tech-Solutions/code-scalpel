"""
Regression Prediction - Enterprise Tier Feature.

[20251226_FEATURE] v3.2.9 - Enterprise tier test coverage impact prediction.

This module predicts test coverage changes based on refactored code:
- Estimates which tests may be affected
- Identifies coverage gaps
- Prioritizes test execution
- Analyzes test impact
"""

import ast
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypedDict


class RegressionPredictionDict(TypedDict, total=False):
    """Regression prediction / coverage impact payload."""

    risk_score: float
    risk_level: str  # "low", "medium", "high", "critical"
    risk_factors: list[str]
    affected_areas: list[str]
    recommendation: str
    affected_functions: list[str]
    affected_tests: list[str]
    coverage_before: float
    coverage_after: float
    coverage_delta: float
    low_coverage_functions: list[str]
    test_priorities: list[str]
    summary: str


logger = logging.getLogger(__name__)


@dataclass
class CoverageImpact:
    """Test coverage impact prediction."""

    affected_functions: list[str]  # Functions changed
    affected_tests: list[str]  # Tests that may be affected
    coverage_before: float  # Estimated coverage % before
    coverage_after: float  # Estimated coverage % after
    coverage_delta: float  # Change in coverage %
    low_coverage_functions: list[str]  # Functions with <80% coverage
    test_priorities: list[str]  # Prioritized test list


class RegressionPredictor:
    """
    Predicts test regression risk from refactored code.

    Enterprise tier feature for test impact analysis.
    """

    def __init__(self, coverage_file: str | None = None):
        """
        Initialize the regression predictor.

        Args:
            coverage_file: Path to coverage.py JSON report (default: coverage.json)
        """
        self.coverage_file = coverage_file or "coverage.json"
        self.coverage_data: dict[str, Any] = {}
        self._load_coverage()

    def _load_coverage(self) -> None:
        """Load coverage data from JSON file."""
        path = Path(self.coverage_file)

        if not path.exists():
            logger.warning(f"Coverage file not found: {path}")
            return

        try:
            self.coverage_data = json.loads(path.read_text())
            logger.info(f"Loaded coverage data from {path}")
        except Exception as e:
            logger.error(f"Failed to load coverage data: {e}")

    def extract_functions(self, code: str) -> list[str]:
        """
        Extract function names from code.

        Args:
            code: Python source code

        Returns:
            List of function names
        """
        functions = []

        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    functions.append(node.name)
        except SyntaxError:
            pass

        return functions

    def predict_affected_tests(self, changed_functions: list[str]) -> list[str]:
        """
        Predict which tests may be affected by function changes.

        Args:
            changed_functions: List of modified function names

        Returns:
            List of test names that may need to run
        """
        affected_tests = []

        # Heuristic: tests are named test_<function_name>
        for func in changed_functions:
            affected_tests.append(f"test_{func}")

            # Also add integration tests
            if not func.startswith("_"):  # Public functions
                affected_tests.append(f"test_integration_{func}")

        return affected_tests

    def estimate_coverage(self, functions: list[str]) -> float:
        """
        Estimate coverage percentage for given functions.

        Args:
            functions: List of function names

        Returns:
            Estimated coverage percentage (0-100)
        """
        if not self.coverage_data or not functions:
            return 0.0

        # If coverage data is available, use it
        files = self.coverage_data.get("files", {})

        total_statements = 0
        covered_statements = 0

        for _file_path, file_data in files.items():
            # Check if any of our functions are in this file
            # This is a simplified heuristic
            summary = file_data.get("summary", {})
            total_statements += summary.get("num_statements", 0)
            covered_statements += summary.get("covered_lines", 0)

        if total_statements == 0:
            return 0.0

        return (covered_statements / total_statements) * 100.0

    def identify_low_coverage_functions(self, functions: list[str], threshold: float = 80.0) -> list[str]:
        """
        Identify functions with low test coverage.

        Args:
            functions: List of function names
            threshold: Coverage threshold % (default: 80%)

        Returns:
            List of functions below threshold
        """
        low_coverage = []

        # Simplified heuristic: assume functions starting with _ are private
        # and may have lower coverage
        for func in functions:
            if func.startswith("_"):
                low_coverage.append(func)

        return low_coverage

    def prioritize_tests(self, affected_tests: list[str]) -> list[str]:
        """
        Prioritize test execution order.

        Args:
            affected_tests: List of affected test names

        Returns:
            Prioritized list of tests
        """
        # Prioritize unit tests first, then integration tests
        unit_tests = [t for t in affected_tests if "integration" not in t]
        integration_tests = [t for t in affected_tests if "integration" in t]

        return unit_tests + integration_tests

    def predict_impact(self, original_code: str, new_code: str) -> CoverageImpact:
        """
        Predict test coverage impact from refactoring.

        Args:
            original_code: Original source code
            new_code: Refactored source code

        Returns:
            CoverageImpact with impact analysis
        """
        # Extract functions from both versions
        original_functions = self.extract_functions(original_code)
        new_functions = self.extract_functions(new_code)

        # Identify changed functions
        changed = []
        for func in new_functions:
            if func in original_functions:
                # Function exists in both - may be modified
                changed.append(func)

        # Identify new functions
        added = [f for f in new_functions if f not in original_functions]
        changed.extend(added)

        # Predict affected tests
        affected_tests = self.predict_affected_tests(changed)

        # Estimate coverage
        coverage_before = self.estimate_coverage(original_functions)
        coverage_after = self.estimate_coverage(new_functions)
        coverage_delta = coverage_after - coverage_before

        # Identify low coverage functions
        low_coverage = self.identify_low_coverage_functions(new_functions)

        # Prioritize tests
        test_priorities = self.prioritize_tests(affected_tests)

        return CoverageImpact(
            affected_functions=changed,
            affected_tests=affected_tests,
            coverage_before=coverage_before,
            coverage_after=coverage_after,
            coverage_delta=coverage_delta,
            low_coverage_functions=low_coverage,
            test_priorities=test_priorities,
        )

    def to_dict(self, impact: CoverageImpact) -> RegressionPredictionDict:
        """Convert CoverageImpact to dict for JSON serialization."""
        return {
            "affected_functions": impact.affected_functions,
            "affected_tests": impact.affected_tests,
            "coverage_before": round(impact.coverage_before, 2),
            "coverage_after": round(impact.coverage_after, 2),
            "coverage_delta": round(impact.coverage_delta, 2),
            "low_coverage_functions": impact.low_coverage_functions,
            "test_priorities": impact.test_priorities,
            "summary": f"{len(impact.affected_functions)} functions changed, {len(impact.affected_tests)} tests affected",
        }
