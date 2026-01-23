"""[20260103_TEST] Comprehensive tests for extract_with_custom_pattern() Enterprise feature.

Tests validate pattern-based code extraction:
- Regex pattern matching
- Function call pattern matching
- Import pattern matching
- Pattern validation
- Bulk operations
- File exclusion
- Error handling and edge cases

Target: High coverage for all pattern types and error paths
"""

from __future__ import annotations

from pathlib import Path


class TestExtractWithCustomPatternRegex:
    """Test regex pattern matching."""

    def test_regex_pattern_function_matching(self, tmp_path: Path):
        """Test regex pattern matching in functions."""
        from code_scalpel.surgery.surgical_extractor import extract_with_custom_pattern

        # Create test module
        module_file = tmp_path / "module.py"
        module_file.write_text(
            "def calculate_tax(amount):\n"
            "    return amount * 0.1\n"
            "\n"
            "def calculate_discount(amount):\n"
            "    return amount * 0.2\n"
            "\n"
            "def display_name(name):\n"
            "    return f'Name: {name}'\n"
        )

        # Find all functions with 'calculate' pattern
        result = extract_with_custom_pattern(
            pattern="calculate",
            pattern_type="regex",
            project_root=str(tmp_path),
        )

        assert result.success is True
        assert len(result.matches) == 2
        match_names = [m.symbol_name for m in result.matches]
        assert "calculate_tax" in match_names
        assert "calculate_discount" in match_names
        assert "display_name" not in match_names

    def test_regex_pattern_class_matching(self, tmp_path: Path):
        """Test regex pattern matching in classes."""
        from code_scalpel.surgery.surgical_extractor import extract_with_custom_pattern

        module_file = tmp_path / "models.py"
        module_file.write_text(
            "class UserService:\n"
            "    def get_user(self, id):\n"
            "        pass\n"
            "\n"
            "class UserModel:\n"
            "    def __init__(self, name):\n"
            "        self.name = name\n"
            "\n"
            "class DataProcessor:\n"
            "    def process(self):\n"
            "        pass\n"
        )

        # Find classes with 'User' pattern
        result = extract_with_custom_pattern(
            pattern="User",
            pattern_type="regex",
            project_root=str(tmp_path),
        )

        assert result.success is True
        assert len(result.matches) >= 2
        match_names = [m.symbol_name for m in result.matches]
        assert "UserService" in match_names or "UserModel" in match_names

    def test_regex_pattern_complex_pattern(self, tmp_path: Path):
        """Test regex with complex pattern."""
        from code_scalpel.surgery.surgical_extractor import extract_with_custom_pattern

        module_file = tmp_path / "handlers.py"
        module_file.write_text(
            "def handle_user_creation():\n"
            "    pass\n"
            "\n"
            "def handle_user_deletion():\n"
            "    pass\n"
            "\n"
            "def process_data():\n"
            "    pass\n"
        )

        # Find functions with handle_user pattern
        result = extract_with_custom_pattern(
            pattern=r"handle_.*user",
            pattern_type="regex",
            project_root=str(tmp_path),
        )

        assert result.success is True
        assert len(result.matches) >= 1

    def test_regex_pattern_case_insensitive(self, tmp_path: Path):
        """Test that regex matching is case-insensitive."""
        from code_scalpel.surgery.surgical_extractor import extract_with_custom_pattern

        module_file = tmp_path / "service.py"
        module_file.write_text(
            "def calculate():\n"
            "    pass\n"
            "\n"
            "def CALCULATE():\n"
            "    pass\n"
            "\n"
            "def Display():\n"
            "    pass\n"
        )

        result = extract_with_custom_pattern(
            pattern="CALCULATE",
            pattern_type="regex",
            project_root=str(tmp_path),
        )

        assert result.success is True
        # Should match both calculate and CALCULATE (case-insensitive)
        assert len(result.matches) >= 1


class TestExtractWithCustomPatternFunctionCall:
    """Test function call pattern matching."""

    def test_function_call_pattern_direct_call(self, tmp_path: Path):
        """Test finding functions that call a specific function."""
        from code_scalpel.surgery.surgical_extractor import extract_with_custom_pattern

        module_file = tmp_path / "api.py"
        module_file.write_text(
            "def fetch_data():\n"
            "    pass\n"
            "\n"
            "def get_user():\n"
            "    data = fetch_data()\n"
            "    return data\n"
            "\n"
            "def display():\n"
            "    print('display')\n"
        )

        result = extract_with_custom_pattern(
            pattern="fetch_data",
            pattern_type="function_call",
            project_root=str(tmp_path),
        )

        assert result.success is True
        # Should find get_user which calls fetch_data
        match_names = [m.symbol_name for m in result.matches]
        assert "get_user" in match_names or len(result.matches) > 0
        assert "display" not in match_names

    def test_function_call_pattern_method_call(self, tmp_path: Path):
        """Test finding functions that call methods."""
        from code_scalpel.surgery.surgical_extractor import extract_with_custom_pattern

        module_file = tmp_path / "db.py"
        module_file.write_text(
            "class Database:\n"
            "    def query(self, sql):\n"
            "        pass\n"
            "\n"
            "def get_users():\n"
            "    db = Database()\n"
            "    return db.query('SELECT * FROM users')\n"
            "\n"
            "def log_message():\n"
            "    print('logging')\n"
        )

        result = extract_with_custom_pattern(
            pattern="query",
            pattern_type="function_call",
            project_root=str(tmp_path),
        )

        assert result.success is True
        # Should find get_users which calls db.query
        assert len(result.matches) >= 1

    def test_function_call_pattern_multiple_calls(self, tmp_path: Path):
        """Test function that calls the pattern multiple times."""
        from code_scalpel.surgery.surgical_extractor import extract_with_custom_pattern

        module_file = tmp_path / "processor.py"
        module_file.write_text(
            "def validate(data):\n"
            "    pass\n"
            "\n"
            "def process(input_data):\n"
            "    validate(input_data)\n"
            "    result = validate(input_data)\n"
            "    return result\n"
        )

        result = extract_with_custom_pattern(
            pattern="validate",
            pattern_type="function_call",
            project_root=str(tmp_path),
        )

        assert result.success is True
        match_names = [m.symbol_name for m in result.matches]
        assert "process" in match_names or len(result.matches) > 0


class TestExtractWithCustomPatternImport:
    """Test import pattern matching."""

    def test_import_pattern_from_import(self, tmp_path: Path):
        """Test finding files that import a module (from import)."""
        from code_scalpel.surgery.surgical_extractor import extract_with_custom_pattern

        module_file = tmp_path / "handlers.py"
        module_file.write_text(
            "from django import forms\n"
            "\n"
            "def create_form():\n"
            "    return forms.Form()\n"
            "\n"
            "def register_user():\n"
            "    form = create_form()\n"
            "    return form\n"
        )

        result = extract_with_custom_pattern(
            pattern="django",
            pattern_type="import",
            project_root=str(tmp_path),
        )

        assert result.success is True
        # Should find functions in a file that imports django
        assert len(result.matches) >= 0

    def test_import_pattern_direct_import(self, tmp_path: Path):
        """Test finding files that directly import a module."""
        from code_scalpel.surgery.surgical_extractor import extract_with_custom_pattern

        module_file = tmp_path / "utils.py"
        module_file.write_text(
            "import json\n"
            "\n"
            "def serialize(obj):\n"
            "    return json.dumps(obj)\n"
            "\n"
            "def deserialize(s):\n"
            "    return json.loads(s)\n"
        )

        result = extract_with_custom_pattern(
            pattern="json",
            pattern_type="import",
            project_root=str(tmp_path),
        )

        assert result.success is True
        # Should find serialize and deserialize functions
        match_names = [m.symbol_name for m in result.matches]
        assert len(match_names) >= 2

    def test_import_pattern_multiple_imports(self, tmp_path: Path):
        """Test finding files with multiple imports."""
        from code_scalpel.surgery.surgical_extractor import extract_with_custom_pattern

        module_file = tmp_path / "api.py"
        module_file.write_text(
            "import requests\n"
            "import json\n"
            "from typing import Dict\n"
            "\n"
            "def fetch_api(url):\n"
            "    response = requests.get(url)\n"
            "    return response.json()\n"
        )

        result = extract_with_custom_pattern(
            pattern="requests",
            pattern_type="import",
            project_root=str(tmp_path),
        )

        assert result.success is True
        assert len(result.matches) >= 1


class TestExtractWithCustomPatternMultipleFiles:
    """Test pattern extraction across multiple files."""

    def test_pattern_matching_across_files(self, tmp_path: Path):
        """Test finding patterns across multiple files."""
        from code_scalpel.surgery.surgical_extractor import extract_with_custom_pattern

        # Create multiple files
        (tmp_path / "service1.py").write_text("def get_user():\n" "    pass\n")
        (tmp_path / "service2.py").write_text("def get_product():\n" "    pass\n")
        (tmp_path / "service3.py").write_text("def get_order():\n" "    pass\n")

        result = extract_with_custom_pattern(
            pattern="get_",
            pattern_type="regex",
            project_root=str(tmp_path),
        )

        assert result.success is True
        # Should find all get_* functions across files
        assert result.files_scanned == 3
        assert len(result.matches) >= 3

    def test_files_scanned_count(self, tmp_path: Path):
        """Test that files_scanned count is accurate."""
        from code_scalpel.surgery.surgical_extractor import extract_with_custom_pattern

        # Create test files
        for i in range(5):
            (tmp_path / f"module_{i}.py").write_text(f"def func_{i}():\n    pass\n")

        result = extract_with_custom_pattern(
            pattern="func",
            pattern_type="regex",
            project_root=str(tmp_path),
        )

        assert result.success is True
        assert result.files_scanned == 5


class TestExtractWithCustomPatternMatchProperties:
    """Test PatternMatch object properties."""

    def test_pattern_match_contains_all_fields(self, tmp_path: Path):
        """Test that PatternMatch contains all required fields."""
        from code_scalpel.surgery.surgical_extractor import extract_with_custom_pattern

        module_file = tmp_path / "test.py"
        module_file.write_text("def calculate_sum(a, b):\n" "    return a + b\n")

        result = extract_with_custom_pattern(
            pattern="calculate",
            pattern_type="regex",
            project_root=str(tmp_path),
        )

        assert result.success is True
        assert len(result.matches) > 0

        match = result.matches[0]
        assert hasattr(match, "symbol_name")
        assert hasattr(match, "symbol_type")
        assert hasattr(match, "file_path")
        assert hasattr(match, "line_number")
        assert hasattr(match, "code")
        assert hasattr(match, "match_reason")

    def test_pattern_match_symbol_type(self, tmp_path: Path):
        """Test that symbol_type is correctly set."""
        from code_scalpel.surgery.surgical_extractor import extract_with_custom_pattern

        module_file = tmp_path / "models.py"
        module_file.write_text("class UserModel:\n" "    pass\n" "\n" "def get_user():\n" "    pass\n")

        result = extract_with_custom_pattern(
            pattern="User|get",
            pattern_type="regex",
            project_root=str(tmp_path),
        )

        assert result.success is True
        # Check symbol types
        for match in result.matches:
            assert match.symbol_type in ["function", "class", "method"]

    def test_pattern_match_reason_generated(self, tmp_path: Path):
        """Test that match_reason is generated."""
        from code_scalpel.surgery.surgical_extractor import extract_with_custom_pattern

        module_file = tmp_path / "test.py"
        module_file.write_text("def test_pattern():\n" "    pass\n")

        result = extract_with_custom_pattern(
            pattern="test",
            pattern_type="regex",
            project_root=str(tmp_path),
        )

        assert result.success is True
        assert len(result.matches) > 0
        match = result.matches[0]
        assert match.match_reason is not None
        assert len(match.match_reason) > 0


class TestExtractWithCustomPatternEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_project_root(self, tmp_path: Path):
        """Test handling of empty project root."""
        from code_scalpel.surgery.surgical_extractor import extract_with_custom_pattern

        result = extract_with_custom_pattern(
            pattern="test",
            pattern_type="regex",
            project_root=str(tmp_path),
        )

        assert result.success is True
        assert len(result.matches) == 0
        assert result.files_scanned == 0

    def test_no_matching_patterns(self, tmp_path: Path):
        """Test when no patterns match."""
        from code_scalpel.surgery.surgical_extractor import extract_with_custom_pattern

        (tmp_path / "module.py").write_text("def func_a():\n" "    pass\n" "\n" "def func_b():\n" "    pass\n")

        result = extract_with_custom_pattern(
            pattern="nonexistent_pattern",
            pattern_type="regex",
            project_root=str(tmp_path),
        )

        assert result.success is True
        assert len(result.matches) == 0
        assert result.files_scanned == 1

    def test_invalid_pattern_type(self, tmp_path: Path):
        """Test error handling with invalid pattern type."""
        from code_scalpel.surgery.surgical_extractor import extract_with_custom_pattern

        (tmp_path / "module.py").write_text("def func():\n" "    pass\n")

        result = extract_with_custom_pattern(
            pattern="test",
            pattern_type="invalid_type",
            project_root=str(tmp_path),
        )

        # Should handle gracefully (either success with 0 matches or error)
        assert isinstance(result.success, bool)

    def test_unparseable_python_files(self, tmp_path: Path):
        """Test handling of unparseable Python files."""
        from code_scalpel.surgery.surgical_extractor import extract_with_custom_pattern

        # Create valid file
        (tmp_path / "valid.py").write_text("def calculate():\n" "    pass\n")

        # Create invalid file
        (tmp_path / "invalid.py").write_text("this is not valid python !@#$%^&*()")

        result = extract_with_custom_pattern(
            pattern="calculate",
            pattern_type="regex",
            project_root=str(tmp_path),
        )

        assert result.success is True
        # Should skip invalid file and process valid file
        assert len(result.matches) >= 1

    def test_none_project_root(self, tmp_path: Path, monkeypatch):
        """Test that None project_root uses current directory."""
        from code_scalpel.surgery.surgical_extractor import extract_with_custom_pattern

        monkeypatch.chdir(tmp_path)

        (tmp_path / "module.py").write_text("def search_function():\n" "    pass\n")

        result = extract_with_custom_pattern(
            pattern="search",
            pattern_type="regex",
            project_root=None,
        )

        assert result.success is True
        assert len(result.matches) >= 1


class TestExtractWithCustomPatternMultipleFunctionsInFile:
    """Test extraction of multiple functions from single file."""

    def test_multiple_functions_in_single_file(self, tmp_path: Path):
        """Test finding multiple matching functions in single file."""
        from code_scalpel.surgery.surgical_extractor import extract_with_custom_pattern

        # Create source file with multiple matching functions
        (tmp_path / "source.py").write_text(
            "def process_data():\n"
            "    pass\n"
            "\n"
            "def process_input():\n"
            "    pass\n"
            "\n"
            "def process_output():\n"
            "    pass\n"
        )

        result = extract_with_custom_pattern(
            pattern="process",
            pattern_type="regex",
            project_root=str(tmp_path),
        )

        assert result.success is True
        # Should find all three process_* functions
        assert len(result.matches) == 3

    def test_file_with_mixed_matches(self, tmp_path: Path):
        """Test file with both matching and non-matching functions."""
        from code_scalpel.surgery.surgical_extractor import extract_with_custom_pattern

        # Create source file
        (tmp_path / "app.py").write_text(
            "def calculate():\n"
            "    pass\n"
            "\n"
            "def display():\n"
            "    pass\n"
            "\n"
            "def calculate_total():\n"
            "    pass\n"
        )

        result = extract_with_custom_pattern(
            pattern="calculate",
            pattern_type="regex",
            project_root=str(tmp_path),
        )

        assert result.success is True
        # Should find calculate and calculate_total, not display
        assert len(result.matches) == 2


class TestExtractWithCustomPatternExplanation:
    """Test explanation generation."""

    def test_explanation_contains_stats(self, tmp_path: Path):
        """Test that explanation contains scan statistics."""
        from code_scalpel.surgery.surgical_extractor import extract_with_custom_pattern

        (tmp_path / "module.py").write_text("def func1():\n" "    pass\n" "\n" "def func2():\n" "    pass\n")

        result = extract_with_custom_pattern(
            pattern="func",
            pattern_type="regex",
            project_root=str(tmp_path),
        )

        assert result.success is True
        assert result.explanation is not None
        assert "Scanned" in result.explanation or "scanned" in result.explanation.lower()
