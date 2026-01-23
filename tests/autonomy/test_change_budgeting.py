"""
Tests for Change Budgeting (Blast Radius Control).

[20251216_TEST] Comprehensive test suite for P0 change budgeting feature.
Tests all constraint validations and policy enforcement.
"""

from code_scalpel.governance.change_budget import (
    ChangeBudget,
    FileChange,
    Operation,
    load_budget_config,
)


class TestBudgetValidation:
    """Test core budget validation logic."""

    def test_max_files_limit_enforced(self):
        """[20251216_TEST] P0: Enforces max_files limit."""
        budget = ChangeBudget({"max_files": 3})

        # Operation with 4 files exceeds limit
        operation = Operation(
            changes=[FileChange(file_path=f"src/file{i}.py", added_lines=["x = 1"]) for i in range(4)]
        )

        decision = budget.validate_operation(operation)

        assert not decision.allowed
        assert len(decision.violations) == 1
        assert decision.violations[0].rule == "max_files"
        assert decision.violations[0].severity == "HIGH"
        assert decision.violations[0].limit == 3
        assert decision.violations[0].actual == 4

    def test_max_files_limit_respected(self):
        """[20251216_TEST] Operation within max_files limit is allowed."""
        budget = ChangeBudget({"max_files": 5})

        operation = Operation(
            changes=[FileChange(file_path=f"src/file{i}.py", added_lines=["x = 1"]) for i in range(3)]
        )

        decision = budget.validate_operation(operation)

        assert decision.allowed
        assert len(decision.violations) == 0

    def test_max_lines_per_file_enforced(self):
        """[20251216_TEST] P0: Enforces max_lines_per_file limit."""
        budget = ChangeBudget({"max_lines_per_file": 50})

        # File with 60 lines changed exceeds limit
        operation = Operation(
            changes=[
                FileChange(
                    file_path="src/large.py",
                    added_lines=[f"line_{i}" for i in range(60)],
                )
            ]
        )

        decision = budget.validate_operation(operation)

        assert not decision.allowed
        assert len(decision.violations) == 1
        assert decision.violations[0].rule == "max_lines_per_file"
        assert decision.violations[0].severity == "MEDIUM"
        assert decision.violations[0].limit == 50
        assert decision.violations[0].actual == 60
        assert decision.violations[0].file == "src/large.py"

    def test_max_lines_per_file_counts_added_and_removed(self):
        """[20251216_TEST] Lines per file includes both added and removed."""
        budget = ChangeBudget({"max_lines_per_file": 50})

        operation = Operation(
            changes=[
                FileChange(
                    file_path="src/modified.py",
                    added_lines=[f"new_{i}" for i in range(30)],
                    removed_lines=[f"old_{i}" for i in range(25)],
                )
            ]
        )

        decision = budget.validate_operation(operation)

        # 30 + 25 = 55 lines changed, exceeds limit
        assert not decision.allowed
        assert decision.violations[0].actual == 55

    def test_max_total_lines_enforced(self):
        """[20251216_TEST] P0: Enforces max_total_lines limit."""
        budget = ChangeBudget({"max_total_lines": 100})

        # Three files with 40 lines each = 120 total
        operation = Operation(
            changes=[
                FileChange(
                    file_path=f"src/file{i}.py",
                    added_lines=[f"line_{j}" for j in range(40)],
                )
                for i in range(3)
            ]
        )

        decision = budget.validate_operation(operation)

        assert not decision.allowed
        assert len(decision.violations) == 1
        assert decision.violations[0].rule == "max_total_lines"
        assert decision.violations[0].severity == "HIGH"
        assert decision.violations[0].limit == 100
        assert decision.violations[0].actual == 120

    def test_max_complexity_increase_enforced(self):
        """[20251216_TEST] P0: Enforces max_complexity_increase limit."""
        budget = ChangeBudget({"max_complexity_increase": 5})

        # Original code: complexity = 1 (base)
        original_code = """
def simple():
    return 42
"""

        # Modified code: complexity = 8 (1 base + 7 decision points)
        modified_code = """
def complex():
    if x > 0:  # +1
        if y > 0:  # +1
            for i in range(10):  # +1
                while j < 5:  # +1
                    if z > 0:  # +1
                        if a or b:  # +2 (1 for if, 1 for or)
                            return i
    return 0
"""

        operation = Operation(
            changes=[
                FileChange(
                    file_path="src/complex.py",
                    original_code=original_code,
                    modified_code=modified_code,
                )
            ]
        )

        decision = budget.validate_operation(operation)

        assert not decision.allowed
        assert any(v.rule == "max_complexity_increase" for v in decision.violations)
        complexity_violation = next(v for v in decision.violations if v.rule == "max_complexity_increase")
        assert complexity_violation.severity == "MEDIUM"
        assert complexity_violation.limit == 5
        # Complexity delta = 8 - 1 = 7
        assert complexity_violation.actual == 7

    def test_complexity_with_syntax_error_doesnt_block(self):
        """[20251216_TEST] Syntax errors in code don't block operations."""
        budget = ChangeBudget({"max_complexity_increase": 5})

        # Original code has syntax error
        original_code = "def broken(:"

        # Modified code is valid
        modified_code = """
def fixed():
    return 42
"""

        operation = Operation(
            changes=[
                FileChange(
                    file_path="src/fixed.py",
                    original_code=original_code,
                    modified_code=modified_code,
                )
            ]
        )

        decision = budget.validate_operation(operation)

        # Should not have complexity violation (treats unparseable as 0 complexity)
        complexity_violations = [v for v in decision.violations if v.rule == "max_complexity_increase"]
        assert len(complexity_violations) == 0

    def test_allowed_file_patterns_enforced(self):
        """[20251216_TEST] P0: Respects allowed_file_patterns."""
        budget = ChangeBudget({"allowed_file_patterns": ["*.py", "*.ts"]})

        # Java file not in allowed patterns
        operation = Operation(changes=[FileChange(file_path="src/Main.java", added_lines=["System.out.println();"])])

        decision = budget.validate_operation(operation)

        assert not decision.allowed
        assert any(v.rule == "allowed_file_patterns" for v in decision.violations)
        pattern_violation = next(v for v in decision.violations if v.rule == "allowed_file_patterns")
        assert pattern_violation.severity == "HIGH"
        assert pattern_violation.file == "src/Main.java"

    def test_allowed_file_patterns_glob_matching(self):
        """[20251216_TEST] File patterns support glob matching."""
        budget = ChangeBudget({"allowed_file_patterns": ["*.py"]})

        # Match nested path (checks filename)
        operation1 = Operation(changes=[FileChange(file_path="src/utils/helper.py", added_lines=["x = 1"])])
        decision1 = budget.validate_operation(operation1)
        assert decision1.allowed

        # Match tests path
        operation2 = Operation(changes=[FileChange(file_path="tests/test_foo.py", added_lines=["x = 1"])])
        decision2 = budget.validate_operation(operation2)
        assert decision2.allowed

    def test_forbidden_paths_enforced(self):
        """[20251216_TEST] P0: Blocks forbidden_paths."""
        budget = ChangeBudget({"forbidden_paths": [".git/", "node_modules/"]})

        # Attempt to modify .git file
        operation = Operation(changes=[FileChange(file_path=".git/config", added_lines=["[core]"])])

        decision = budget.validate_operation(operation)

        assert not decision.allowed
        assert any(v.rule == "forbidden_paths" for v in decision.violations)
        forbidden_violation = next(v for v in decision.violations if v.rule == "forbidden_paths")
        assert forbidden_violation.severity == "CRITICAL"
        assert forbidden_violation.file == ".git/config"

    def test_forbidden_paths_nested(self):
        """[20251216_TEST] Forbidden paths block nested files."""
        budget = ChangeBudget({"forbidden_paths": ["node_modules/"]})

        # Nested in node_modules
        operation = Operation(changes=[FileChange(file_path="node_modules/lodash/index.js", added_lines=["// bad"])])

        decision = budget.validate_operation(operation)

        assert not decision.allowed
        assert any(v.severity == "CRITICAL" for v in decision.violations)

    def test_multiple_violations_reported(self):
        """[20251216_TEST] Multiple violations are all reported."""
        budget = ChangeBudget(
            {
                "max_files": 2,
                "max_total_lines": 50,
                "allowed_file_patterns": ["*.py"],  # Add to avoid pattern violation
                "forbidden_paths": [".git/"],
            }
        )

        operation = Operation(
            changes=[
                FileChange(file_path=".git/config", added_lines=["[core]"]),
                FileChange(
                    file_path="src/file1.py",
                    added_lines=[f"line_{i}" for i in range(30)],
                ),
                FileChange(
                    file_path="src/file2.py",
                    added_lines=[f"line_{i}" for i in range(30)],
                ),
            ]
        )

        decision = budget.validate_operation(operation)

        assert not decision.allowed
        # Should have at least: max_files, max_total_lines, forbidden_paths
        # (may also have allowed_file_patterns for .git/config)
        assert len(decision.violations) >= 3
        assert any(v.rule == "max_files" for v in decision.violations)
        assert any(v.rule == "max_total_lines" for v in decision.violations)
        assert any(v.rule == "forbidden_paths" for v in decision.violations)


class TestBudgetPolicies:
    """Test budget policy configuration and application."""

    def test_default_budget_applied(self):
        """[20251216_TEST] P0: Default budget applied to all operations."""
        # Default budget with standard limits
        budget = ChangeBudget(
            {
                "max_files": 5,
                "max_lines_per_file": 100,
                "max_total_lines": 300,
            }
        )

        # Operation within default limits
        operation = Operation(
            changes=[
                FileChange(
                    file_path="src/file.py",
                    added_lines=[f"line_{i}" for i in range(50)],
                )
            ]
        )

        decision = budget.validate_operation(operation)
        assert decision.allowed

    def test_critical_files_budget_stricter(self):
        """[20251216_TEST] P0: Critical files budget stricter than default."""
        # Critical files budget with stricter limits
        critical_budget = ChangeBudget(
            {
                "max_files": 1,
                "max_lines_per_file": 20,
                "max_total_lines": 20,
                "max_complexity_increase": 0,
            }
        )

        # Operation that would pass default but fails critical
        operation = Operation(
            changes=[
                FileChange(
                    file_path="src/security/auth.py",
                    added_lines=[f"line_{i}" for i in range(30)],
                )
            ]
        )

        decision = critical_budget.validate_operation(operation)

        assert not decision.allowed
        # Should violate max_lines_per_file (30 > 20)
        assert any(v.rule == "max_lines_per_file" for v in decision.violations)

    def test_budget_customization_per_project(self):
        """[20251216_TEST] P0: Budget can be customized per project."""
        # Custom project-specific budget
        custom_budget = ChangeBudget(
            {
                "max_files": 10,  # More permissive
                "max_lines_per_file": 200,  # More permissive
                "allowed_file_patterns": ["*.py"],  # Project-specific
            }
        )

        operation = Operation(
            changes=[
                FileChange(
                    file_path="lib/utils.py",
                    added_lines=[f"line_{i}" for i in range(150)],
                )
            ]
        )

        decision = custom_budget.validate_operation(operation)

        # Should pass with custom budget
        assert decision.allowed


class TestErrorMessages:
    """Test error message quality and actionability."""

    def test_clear_violation_explanation(self):
        """[20251216_TEST] P0: Clear explanation of violated constraint."""
        budget = ChangeBudget({"max_files": 3})

        operation = Operation(
            changes=[FileChange(file_path=f"src/file{i}.py", added_lines=["x = 1"]) for i in range(5)]
        )

        decision = budget.validate_operation(operation)

        error_msg = decision.get_error_message()

        # Should clearly explain the violation
        assert "Budget constraints violated" in error_msg
        assert "exceeds limit of 3" in error_msg
        assert "5 files" in error_msg or "actual: 5" in error_msg
        # Should mention files constraint
        assert "files" in error_msg.lower()

    def test_error_message_suggests_scope_reduction(self):
        """[20251216_TEST] P0: Suggests how to reduce scope."""
        budget = ChangeBudget(
            {
                "max_files": 2,
                "max_total_lines": 50,
            }
        )

        operation = Operation(
            changes=[
                FileChange(
                    file_path=f"src/file{i}.py",
                    added_lines=[f"line_{j}" for j in range(30)],
                )
                for i in range(3)
            ]
        )

        decision = budget.validate_operation(operation)
        error_msg = decision.get_error_message()

        # Should include actionable suggestions
        assert "Suggestions to reduce scope:" in error_msg
        assert "Split operation into smaller batches" in error_msg
        assert "Break down large refactorings" in error_msg

    def test_complexity_limit_exceeded_message(self):
        """[20251216_TEST] P0: Reports 'Complexity Limit Exceeded' correctly."""
        budget = ChangeBudget({"max_complexity_increase": 3})

        original_code = "def simple(): return 1"
        modified_code = """
def complex():
    if x:
        if y:
            if z:
                if a:
                    return 1
    return 0
"""

        operation = Operation(
            changes=[
                FileChange(
                    file_path="src/complex.py",
                    original_code=original_code,
                    modified_code=modified_code,
                )
            ]
        )

        decision = budget.validate_operation(operation)
        error_msg = decision.get_error_message()

        # Should mention complexity explicitly
        assert "Complexity" in error_msg or "complexity" in error_msg
        assert "exceeds limit" in error_msg
        # Should provide actionable suggestions
        assert "Simplify changes" in error_msg or "extracting methods" in error_msg

    def test_forbidden_path_critical_severity(self):
        """[20251216_TEST] Forbidden paths marked as CRITICAL."""
        budget = ChangeBudget({"forbidden_paths": [".git/"]})

        operation = Operation(changes=[FileChange(file_path=".git/hooks/pre-commit", added_lines=["#!/bin/bash"])])

        decision = budget.validate_operation(operation)

        assert not decision.allowed
        assert decision.has_critical_violations
        forbidden_violation = next(v for v in decision.violations if v.rule == "forbidden_paths")
        assert forbidden_violation.severity == "CRITICAL"

    def test_pattern_mismatch_includes_patterns(self):
        """[20251216_TEST] Pattern violations show allowed patterns."""
        budget = ChangeBudget({"allowed_file_patterns": ["*.py", "*.ts"]})

        operation = Operation(changes=[FileChange(file_path="src/Main.java", added_lines=["class Main {}"])])

        decision = budget.validate_operation(operation)
        error_msg = decision.get_error_message()

        # Should show what patterns are allowed
        assert "*.py" in error_msg or "'*.py'" in error_msg
        assert "*.ts" in error_msg or "'*.ts'" in error_msg


class TestComplexityMeasurement:
    """Test cyclomatic complexity calculation."""

    def test_simple_function_complexity(self):
        """[20251216_TEST] Simple function has base complexity of 1."""
        budget = ChangeBudget({})

        code = "def simple(): return 42"
        complexity = budget._measure_complexity(code)

        assert complexity == 1

    def test_if_increases_complexity(self):
        """[20251216_TEST] If statement increases complexity."""
        budget = ChangeBudget({})

        code = """
def check(x):
    if x > 0:
        return True
    return False
"""
        complexity = budget._measure_complexity(code)

        assert complexity == 2  # base + if

    def test_loops_increase_complexity(self):
        """[20251216_TEST] Loops increase complexity."""
        budget = ChangeBudget({})

        code = """
def iterate(items):
    for item in items:
        while item.ready():
            process(item)
"""
        complexity = budget._measure_complexity(code)

        assert complexity == 3  # base + for + while

    def test_exception_handler_increases_complexity(self):
        """[20251216_TEST] Exception handlers increase complexity."""
        budget = ChangeBudget({})

        code = """
def safe_operation():
    try:
        risky()
    except ValueError:
        handle_error()
"""
        complexity = budget._measure_complexity(code)

        assert complexity == 2  # base + except

    def test_boolean_operators_increase_complexity(self):
        """[20251216_TEST] Boolean operators increase complexity."""
        budget = ChangeBudget({})

        code = """
def check(a, b, c):
    if a and b and c:
        return True
    return False
"""
        complexity = budget._measure_complexity(code)

        # base + if + 2 (for 'and' operators: 3 values = 2 decision points)
        assert complexity == 4

    def test_nested_complexity(self):
        """[20251216_TEST] Nested structures accumulate complexity."""
        budget = ChangeBudget({})

        code = """
def nested(items):
    for item in items:
        if item.valid:
            while not item.done():
                try:
                    process(item)
                except Error:
                    retry()
"""
        complexity = budget._measure_complexity(code)

        # base + for + if + while + except = 5
        assert complexity == 5

    def test_empty_code_complexity(self):
        """[20251216_TEST] Empty code has base complexity."""
        budget = ChangeBudget({})

        complexity = budget._measure_complexity("")

        assert complexity == 1

    def test_syntax_error_returns_zero(self):
        """[20251216_TEST] Syntax error returns 0 complexity."""
        budget = ChangeBudget({})

        complexity = budget._measure_complexity("def broken(:")

        assert complexity == 0


class TestFilePatternMatching:
    """Test file pattern matching logic."""

    def test_exact_extension_match(self):
        """[20251216_TEST] Exact file extension matches."""
        budget = ChangeBudget({"allowed_file_patterns": ["*.py"]})

        assert budget._matches_allowed_pattern("test.py")
        assert not budget._matches_allowed_pattern("test.js")

    def test_multiple_patterns(self):
        """[20251216_TEST] Multiple patterns allow different file types."""
        budget = ChangeBudget({"allowed_file_patterns": ["*.py", "*.ts", "*.java"]})

        assert budget._matches_allowed_pattern("app.py")
        assert budget._matches_allowed_pattern("app.ts")
        assert budget._matches_allowed_pattern("App.java")
        assert not budget._matches_allowed_pattern("app.rs")

    def test_path_pattern_matching(self):
        """[20251216_TEST] Patterns can match filenames."""
        budget = ChangeBudget({"allowed_file_patterns": ["*.py"]})

        # Checks filename pattern matching
        assert budget._matches_allowed_pattern("src/utils/helper.py")

    def test_windows_path_separators(self):
        """[20251216_TEST] Windows backslashes handled correctly."""
        budget = ChangeBudget({"allowed_file_patterns": ["*.py"]})

        # Should normalize backslashes to forward slashes
        assert budget._matches_allowed_pattern(r"src\utils\test.py")

    def test_forbidden_path_prefix_match(self):
        """[20251216_TEST] Forbidden paths match prefixes."""
        budget = ChangeBudget({"forbidden_paths": [".git/"]})

        assert budget._matches_forbidden_path(".git/config")
        assert budget._matches_forbidden_path(".git/hooks/pre-commit")
        assert not budget._matches_forbidden_path("src/.gitignore")

    def test_forbidden_path_anywhere_in_path(self):
        """[20251216_TEST] Forbidden paths match anywhere in full path."""
        budget = ChangeBudget({"forbidden_paths": ["node_modules/"]})

        assert budget._matches_forbidden_path("node_modules/lodash/index.js")
        assert budget._matches_forbidden_path("project/node_modules/react/index.js")


class TestConfigurationLoading:
    """Test configuration loading from YAML files."""

    def test_default_config_when_file_missing(self):
        """[20251216_TEST] Returns default config when file doesn't exist."""
        config = load_budget_config("nonexistent/budget.yaml")

        assert "default" in config
        assert config["default"]["max_files"] == 5
        assert config["default"]["max_lines_per_file"] == 100
        assert config["default"]["max_total_lines"] == 300
        assert config["default"]["max_complexity_increase"] == 10

    def test_default_config_structure(self):
        """[20251216_TEST] Default config has all required fields."""
        config = load_budget_config()

        default = config["default"]
        assert "max_files" in default
        assert "max_lines_per_file" in default
        assert "max_total_lines" in default
        assert "max_complexity_increase" in default
        assert "allowed_file_patterns" in default
        assert "forbidden_paths" in default

    def test_default_forbidden_paths_include_common(self):
        """[20251216_TEST] Default forbidden paths include common system dirs."""
        config = load_budget_config()

        forbidden = config["default"]["forbidden_paths"]
        assert ".git/" in forbidden
        assert "node_modules/" in forbidden
        assert "__pycache__/" in forbidden


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_operation(self):
        """[20251216_TEST] Empty operation is allowed."""
        budget = ChangeBudget({})

        operation = Operation(changes=[])

        decision = budget.validate_operation(operation)

        assert decision.allowed

    def test_error_message_for_allowed_operation(self):
        """[20251216_TEST] Error message for allowed operation just returns reason."""
        budget = ChangeBudget({})

        operation = Operation(changes=[FileChange(file_path="src/test.py", added_lines=["x = 1"])])

        decision = budget.validate_operation(operation)

        assert decision.allowed
        error_msg = decision.get_error_message()
        assert error_msg == "Within budget constraints"

    def test_zero_line_change(self):
        """[20251216_TEST] File with no line changes is allowed."""
        budget = ChangeBudget({"max_lines_per_file": 10})

        operation = Operation(changes=[FileChange(file_path="src/empty.py", added_lines=[], removed_lines=[])])

        decision = budget.validate_operation(operation)

        assert decision.allowed

    def test_negative_complexity_delta_allowed(self):
        """[20251216_TEST] Simplifying code (negative complexity) is allowed."""
        budget = ChangeBudget({"max_complexity_increase": 5})

        # Original code is complex
        original_code = """
def complex():
    if x:
        if y:
            if z:
                return 1
    return 0
"""

        # Simplified code
        modified_code = "def simple(): return 1"

        operation = Operation(
            changes=[
                FileChange(
                    file_path="src/simplified.py",
                    original_code=original_code,
                    modified_code=modified_code,
                )
            ]
        )

        decision = budget.validate_operation(operation)

        # Negative delta doesn't trigger violation
        assert decision.allowed or not any(v.rule == "max_complexity_increase" for v in decision.violations)

    def test_exactly_at_limit_allowed(self):
        """[20251216_TEST] Operations exactly at limits are allowed."""
        budget = ChangeBudget(
            {
                "max_files": 3,
                "max_lines_per_file": 50,
                "max_total_lines": 150,
            }
        )

        operation = Operation(
            changes=[
                FileChange(
                    file_path=f"src/file{i}.py",
                    added_lines=[f"line_{j}" for j in range(50)],
                )
                for i in range(3)
            ]
        )

        decision = budget.validate_operation(operation)

        # Exactly at limits should be allowed
        assert decision.allowed

    def test_one_over_limit_rejected(self):
        """[20251216_TEST] One over limit is rejected."""
        budget = ChangeBudget({"max_files": 3})

        operation = Operation(
            changes=[FileChange(file_path=f"src/file{i}.py", added_lines=["x = 1"]) for i in range(4)]
        )

        decision = budget.validate_operation(operation)

        assert not decision.allowed

    def test_complexity_with_both_syntax_errors(self):
        """[20251216_TEST] Handle case where both original and modified have syntax errors."""
        budget = ChangeBudget({"max_complexity_increase": 5})

        # Both have syntax errors - should not cause delta
        operation = Operation(
            changes=[
                FileChange(
                    file_path="src/broken.py",
                    original_code="def broken(:",
                    modified_code="def still_broken(:",
                )
            ]
        )

        decision = budget.validate_operation(operation)

        # Should not have complexity violation (both treated as 0)
        complexity_violations = [v for v in decision.violations if v.rule == "max_complexity_increase"]
        assert len(complexity_violations) == 0

    def test_operation_missing_code_for_complexity(self):
        """[20251216_TEST] File changes without original/modified code don't affect complexity."""
        budget = ChangeBudget({"max_complexity_increase": 5})

        # File change without original/modified code
        operation = Operation(
            changes=[
                FileChange(file_path="src/example.py", added_lines=["x = 1"]),
            ]
        )

        decision = budget.validate_operation(operation)

        # Should not have complexity violation (no code to analyze)
        complexity_violations = [v for v in decision.violations if v.rule == "max_complexity_increase"]
        assert len(complexity_violations) == 0
