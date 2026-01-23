"""
Path Prioritization - Crash-Triggering Input Optimization (Pro Tier Feature)

This module provides path prioritization strategies for symbolic execution,
focusing on discovering inputs that trigger error conditions.

[20251226_FEATURE] v3.2.9 Pro tier - Crash-triggering input optimization

Key features:
- Error-prone pattern detection (division by zero, index out of bounds, etc.)
- Path ranking by likelihood of triggering crashes
- Priority-guided path exploration

Use cases:
- Fuzzing optimization: Find bugs faster
- Security testing: Discover crash vulnerabilities
- Test generation: Create tests for edge cases
"""

import ast
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any

from code_scalpel.parsing.unified_parser import ParsingError, parse_python_code

from .state_manager import SymbolicState


class PrioritizationStrategy(Enum):
    """Path prioritization strategies."""

    CRASH_FOCUSED = "crash"  # [20251226_FEATURE] v3.2.9 Pro tier - Prioritize error paths
    COVERAGE_GUIDED = "coverage"  # Future: Target uncovered code
    SECURITY_FOCUSED = "security"  # Future: Prioritize paths to sinks
    COMPLEXITY_BASED = "complexity"  # Future: Simple paths first
    HISTORICAL = "historical"  # Future: Learn from past bugs
    RANDOM = "random"  # Baseline: Random exploration
    DFS = "dfs"  # Depth-first search
    BFS = "bfs"  # Breadth-first search
    BEST_FIRST = "best_first"  # Best-first search


class ErrorPattern(Enum):
    """Types of error-prone patterns to detect."""

    DIV_BY_ZERO = auto()  # Division or modulo by potentially zero value
    INDEX_OUT_OF_BOUNDS = auto()  # List/array indexing with unconstrained index
    NULL_DEREFERENCE = auto()  # Attribute access on potentially None value
    TYPE_ERROR = auto()  # Type mismatch operations
    OVERFLOW = auto()  # Integer overflow potential
    ASSERTION_FAILURE = auto()  # Assert statements
    EXCEPTION_RAISE = auto()  # Explicit raise statements


@dataclass
class PathScore:
    """
    Score for a symbolic execution path.

    Higher scores indicate paths more likely to trigger errors/crashes.
    """

    path_id: int
    priority_score: float = 1.0  # Base priority score
    strategy: PrioritizationStrategy = PrioritizationStrategy.CRASH_FOCUSED
    metadata: dict[str, Any] = field(default_factory=dict)
    error_patterns: list[ErrorPattern] = field(default_factory=list)
    depth: int = 0
    constraint_count: int = 0

    @property
    def total_score(self) -> float:
        """
        Calculate total priority score.

        Formula: priority_score + (error_patterns * 10) - (depth * 0.1)
        - Error patterns heavily weighted (+10 each)
        - Depth slightly penalized to avoid deep paths
        """
        pattern_bonus = len(self.error_patterns) * 10.0
        depth_penalty = self.depth * 0.1
        return self.priority_score + pattern_bonus - depth_penalty


class PathPrioritizer:
    """
    Prioritizes symbolic execution paths to find crash-triggering inputs faster.

    This analyzer scans the code to identify error-prone patterns and ranks
    paths that are more likely to hit those patterns.

    [20251226_FEATURE] v3.2.9 Pro tier implementation
    """

    def __init__(
        self,
        code: str | None = None,
        strategy: PrioritizationStrategy = PrioritizationStrategy.CRASH_FOCUSED,
    ):
        """
        Initialize prioritizer.

        Args:
            code: Optional Python source code to analyze for error patterns
            strategy: Prioritization strategy to use
        """
        self.strategy = strategy
        self.code = code
        self._error_prone_lines: list[int] = []
        self._pattern_map: dict[int, ErrorPattern] = {}

        if code:
            self._analyze_code()

    def _analyze_code(self) -> None:
        """
        Scan code for error-prone patterns.

        Detects:
        - Division/modulo operations (DivByZero)
        - Subscript operations (IndexOutOfBounds)
        - Assert statements (AssertionFailure)
        - Raise statements (ExceptionRaise)
        """
        if not self.code:
            return

        try:
            tree, _report = parse_python_code(self.code, filename="<path_prioritizer>")
        except ParsingError:
            return

        for node in ast.walk(tree):
            lineno = getattr(node, "lineno", None)
            if lineno is None:
                continue

            # Division or modulo - potential div by zero
            if isinstance(node, ast.BinOp):
                if isinstance(node.op, (ast.Div, ast.FloorDiv, ast.Mod)):
                    self._error_prone_lines.append(lineno)
                    self._pattern_map[lineno] = ErrorPattern.DIV_BY_ZERO

            # Subscript operations - potential index error
            elif isinstance(node, ast.Subscript):
                self._error_prone_lines.append(lineno)
                self._pattern_map[lineno] = ErrorPattern.INDEX_OUT_OF_BOUNDS

            # Assert statements
            elif isinstance(node, ast.Assert):
                self._error_prone_lines.append(lineno)
                self._pattern_map[lineno] = ErrorPattern.ASSERTION_FAILURE

            # Explicit raise
            elif isinstance(node, ast.Raise):
                self._error_prone_lines.append(lineno)
                self._pattern_map[lineno] = ErrorPattern.EXCEPTION_RAISE

    def score_path(self, path_id: int, state: SymbolicState) -> PathScore:
        """
        Assign priority score to a path.

        Args:
            path_id: Path identifier
            state: Symbolic state for the path

        Returns:
            PathScore with priority information
        """
        score = PathScore(
            path_id=path_id,
            priority_score=1.0,
            strategy=self.strategy,
            depth=state.depth,
            constraint_count=len(state.constraints),
        )

        if self.strategy == PrioritizationStrategy.CRASH_FOCUSED:
            # Analyze constraints for error patterns
            for constraint in state.constraints:
                constraint_str = str(constraint)

                # Division patterns
                if "/" in constraint_str or "div" in constraint_str.lower():
                    score.error_patterns.append(ErrorPattern.DIV_BY_ZERO)

                # Index patterns
                if "[" in constraint_str or "subscript" in constraint_str.lower():
                    score.error_patterns.append(ErrorPattern.INDEX_OUT_OF_BOUNDS)

            # Additional base score for paths with many constraints
            if score.constraint_count > 5:
                score.priority_score += 2.0

        elif self.strategy == PrioritizationStrategy.DFS:
            # Depth-first: prefer deeper paths
            score.priority_score = float(state.depth)

        elif self.strategy == PrioritizationStrategy.BFS:
            # Breadth-first: prefer shallower paths
            score.priority_score = 1.0 / (float(state.depth) + 1.0)

        return score

    def prioritize_paths(self, states: list[SymbolicState]) -> list[tuple[int, PathScore]]:
        """
        Prioritize paths by crash likelihood or strategy.

        Args:
            states: List of symbolic states (one per path)

        Returns:
            List of (original_index, PathScore) tuples sorted by priority (highest first)

        Example:
            >>> prioritizer = PathPrioritizer(code, strategy=PrioritizationStrategy.CRASH_FOCUSED)
            >>> prioritized = prioritizer.prioritize_paths(terminal_states)
            >>> for idx, score in prioritized[:5]:  # Top 5 paths
            ...     print(f"Path {idx}: score={score.total_score}")
        """
        scores: list[tuple[int, PathScore]] = []

        for i, state in enumerate(states):
            score = self.score_path(i, state)
            scores.append((i, score))

        # Sort by total score descending (highest priority first)
        scores.sort(key=lambda x: x[1].total_score, reverse=True)
        return scores

    def select_next_path(self, pending_paths: list[Any]) -> int | None:
        """
        Select next path to explore from pending paths.

        Args:
            pending_paths: List of pending symbolic states

        Returns:
            Index of highest priority path, or None if no paths available
        """
        if not pending_paths:
            return None

        if not isinstance(pending_paths[0], SymbolicState):
            # Fallback: return first path
            return 0

        prioritized = self.prioritize_paths(pending_paths)
        return prioritized[0][0] if prioritized else None

    def update_strategy(self, exploration_stats: dict[str, Any]) -> None:
        """
        Adaptively update strategy based on progress.

        Args:
            exploration_stats: Dictionary with exploration statistics

        Note:
            Current implementation is a placeholder for future adaptive strategies.
        """
        pass

    def get_error_patterns(self) -> dict[int, ErrorPattern]:
        """
        Get detected error patterns mapped to line numbers.

        Returns:
            Dictionary mapping line number to ErrorPattern
        """
        return self._pattern_map.copy()

    def has_error_prone_code(self) -> bool:
        """Check if code contains any error-prone patterns."""
        return len(self._error_prone_lines) > 0

    def get_error_prone_lines(self) -> list[int]:
        """Get list of line numbers with potential error patterns."""
        return self._error_prone_lines.copy()


def prioritize_for_crashes(code: str, states: list[SymbolicState]) -> list[tuple[int, PathScore]]:
    """
    Convenience function to prioritize paths for crash discovery.

    Args:
        code: Python source code
        states: List of symbolic states from execution

    Returns:
        Prioritized list of (path_index, PathScore) tuples

    Example:
        >>> from code_scalpel.symbolic_execution_tools import SymbolicAnalyzer
        >>> analyzer = SymbolicAnalyzer()
        >>> result = analyzer.analyze(code)
        >>> prioritized = prioritize_for_crashes(code, [s for _, s in result.paths])
    """
    prioritizer = PathPrioritizer(code, strategy=PrioritizationStrategy.CRASH_FOCUSED)
    return prioritizer.prioritize_paths(states)


# Backward compatibility aliases
CrashPrioritizer = PathPrioritizer
