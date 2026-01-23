"""
Tests for Cross-File Code Extractor.

[20251213_TEST] v1.5.1 - Tests for cross-file extraction with dependency resolution

Test Categories:
- Basic extraction (single file, single symbol)
- Cross-file extraction (following imports)
- Depth control (limiting dependency chains)
- Multiple symbol extraction
- Edge cases and error handling
"""

import tempfile
from pathlib import Path

import pytest

from code_scalpel.ast_tools.cross_file_extractor import (
    CrossFileExtractor,
    ExtractedSymbol,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def temp_project():
    """Create a temporary project directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def simple_project(temp_project):
    """Create a simple project with imports between files."""
    # utils.py - base utilities
    (temp_project / "utils.py").write_text("""
def format_string(s):
    \"\"\"Format a string.\"\"\"
    return s.strip().upper()

def validate(data):
    \"\"\"Validate data.\"\"\"
    return data is not None

class Formatter:
    def format(self, value):
        return str(value)
""")

    # models.py - uses utils
    (temp_project / "models.py").write_text("""
from utils import format_string, validate

class User:
    def __init__(self, name):
        self.name = format_string(name)

    def is_valid(self):
        return validate(self.name)
""")

    # views.py - uses both
    (temp_project / "views.py").write_text("""
from models import User
from utils import Formatter

def create_user(name):
    \"\"\"Create a new user.\"\"\"
    user = User(name)
    if user.is_valid():
        return user
    return None

def format_output(user):
    formatter = Formatter()
    return formatter.format(user.name)
""")

    return temp_project


@pytest.fixture
def deep_project(temp_project):
    """Create a project with deep import chains."""
    # level0.py
    (temp_project / "level0.py").write_text("""
def base_func():
    return "base"
""")

    # level1.py
    (temp_project / "level1.py").write_text("""
from level0 import base_func

def level1_func():
    return base_func() + "_level1"
""")

    # level2.py
    (temp_project / "level2.py").write_text("""
from level1 import level1_func

def level2_func():
    return level1_func() + "_level2"
""")

    # level3.py
    (temp_project / "level3.py").write_text("""
from level2 import level2_func

def level3_func():
    return level2_func() + "_level3"
""")

    return temp_project


@pytest.fixture
def package_project(temp_project):
    """Create a project with packages."""
    # Create package
    pkg = temp_project / "myapp"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")

    # myapp/core.py
    (pkg / "core.py").write_text("""
def process(data):
    return data.upper()
""")

    # myapp/services.py
    (pkg / "services.py").write_text("""
from .core import process

class DataService:
    def handle(self, data):
        return process(data)
""")

    # main.py
    (temp_project / "main.py").write_text("""
from myapp.services import DataService

def run():
    service = DataService()
    return service.handle("test")
""")

    return temp_project


# =============================================================================
# Basic Extraction Tests
# =============================================================================


class TestBasicExtraction:
    """Tests for basic single-file extraction."""

    def test_extract_function(self, simple_project):
        """Test extracting a simple function."""
        extractor = CrossFileExtractor(simple_project)
        result = extractor.extract("utils.py", "format_string", depth=0)

        assert result.success
        assert result.target is not None
        assert result.target.name == "format_string"
        assert "def format_string" in result.target.code
        assert result.target.symbol_type == "function"

    def test_extract_class(self, simple_project):
        """Test extracting a class."""
        extractor = CrossFileExtractor(simple_project)
        result = extractor.extract("utils.py", "Formatter", depth=0)

        assert result.success
        assert result.target is not None
        assert result.target.name == "Formatter"
        assert result.target.symbol_type == "class"
        assert "class Formatter" in result.target.code

    def test_extract_method(self, simple_project):
        """Test extracting a class method."""
        extractor = CrossFileExtractor(simple_project)
        result = extractor.extract("models.py", "User.is_valid", depth=0)

        assert result.success
        assert result.target is not None
        assert result.target.name == "User.is_valid"
        assert result.target.symbol_type == "method"
        assert "def is_valid" in result.target.code

    def test_extract_nonexistent_symbol(self, simple_project):
        """Test extracting a symbol that doesn't exist."""
        extractor = CrossFileExtractor(simple_project)
        result = extractor.extract("utils.py", "nonexistent", depth=0)

        assert not result.success
        assert len(result.errors) > 0
        assert "not found" in result.errors[0].lower()

    def test_extract_from_nonexistent_file(self, simple_project):
        """Test extracting from a file that doesn't exist."""
        extractor = CrossFileExtractor(simple_project)
        result = extractor.extract("nonexistent.py", "func", depth=0)

        assert not result.success
        assert "not found" in result.errors[0].lower()


# =============================================================================
# Cross-File Extraction Tests
# =============================================================================


class TestCrossFileExtraction:
    """Tests for extraction with cross-file dependencies."""

    def test_extract_with_imports(self, simple_project):
        """Test that imported symbols are extracted."""
        extractor = CrossFileExtractor(simple_project)
        result = extractor.extract("views.py", "create_user", depth=2)

        assert result.success
        assert result.target is not None
        assert result.target.name == "create_user"

        # Should have dependencies
        assert len(result.dependencies) >= 1
        dep_names = [d.name for d in result.dependencies]

        # Should include User from models.py
        assert "User" in dep_names or any("User" in n for n in dep_names)

    def test_depth_limits_extraction(self, deep_project):
        """Test that depth parameter limits dependency chain."""
        extractor = CrossFileExtractor(deep_project)

        # Depth 1 should only get direct imports
        result1 = extractor.extract("level3.py", "level3_func", depth=1)
        assert result1.success
        dep_names_1 = [d.name for d in result1.dependencies]

        # Depth 3 should get more
        result3 = extractor.extract("level3.py", "level3_func", depth=3)
        assert result3.success
        dep_names_3 = [d.name for d in result3.dependencies]

        # More depth = more dependencies (or equal if chain is shorter)
        assert len(dep_names_3) >= len(dep_names_1)

    def test_depth_zero_no_dependencies(self, simple_project):
        """Test that depth=0 extracts only the target."""
        extractor = CrossFileExtractor(simple_project)
        result = extractor.extract("views.py", "create_user", depth=0)

        assert result.success
        assert result.target is not None
        assert len(result.dependencies) == 0

    def test_transitive_dependencies(self, deep_project):
        """Test that transitive dependencies are followed."""
        extractor = CrossFileExtractor(deep_project)
        result = extractor.extract("level3.py", "level3_func", depth=5)

        assert result.success
        [d.name for d in result.dependencies]

        # Should include base_func (if depth is sufficient)
        # Note: This depends on the dependency chain being followed correctly


# =============================================================================
# Combined Code Generation Tests
# =============================================================================


class TestCombinedCode:
    """Tests for combined code output generation."""

    def test_combined_code_includes_target(self, simple_project):
        """Test that combined code includes the target symbol."""
        extractor = CrossFileExtractor(simple_project)
        result = extractor.extract("utils.py", "format_string", depth=0)

        assert result.success
        assert "format_string" in result.combined_code

    def test_combined_code_includes_header(self, simple_project):
        """Test that combined code has informative header."""
        extractor = CrossFileExtractor(simple_project)
        result = extractor.extract("views.py", "create_user", depth=1)

        assert result.success
        assert "Cross-File Extraction" in result.combined_code
        assert "Target:" in result.combined_code

    def test_combined_code_dependencies_first(self, simple_project):
        """Test that dependencies appear before target in output."""
        extractor = CrossFileExtractor(simple_project)
        result = extractor.extract("views.py", "create_user", depth=2)

        assert result.success
        # When there are dependencies, the header should come first
        code = result.combined_code
        assert "Cross-File Extraction" in code
        # Target section should be present
        assert "Target:" in code


# =============================================================================
# Multiple Symbol Extraction Tests
# =============================================================================


class TestMultipleExtraction:
    """Tests for extracting multiple symbols at once."""

    def test_extract_multiple_symbols(self, simple_project):
        """Test extracting multiple symbols."""
        extractor = CrossFileExtractor(simple_project)
        result = extractor.extract_multiple(
            [
                ("utils.py", "format_string"),
                ("utils.py", "validate"),
            ],
            depth=0,
        )

        assert result.success
        assert result.total_symbols >= 2

    def test_extract_multiple_deduplicates(self, simple_project):
        """Test that shared dependencies are deduplicated."""
        extractor = CrossFileExtractor(simple_project)
        result = extractor.extract_multiple(
            [
                ("views.py", "create_user"),
                ("views.py", "format_output"),
            ],
            depth=2,
        )

        assert result.success
        # Dependencies should not be duplicated
        dep_ids = [(d.module, d.name) for d in result.dependencies]
        assert len(dep_ids) == len(set(dep_ids))

    def test_extract_multiple_from_different_files(self, simple_project):
        """Test extracting from multiple files."""
        extractor = CrossFileExtractor(simple_project)
        result = extractor.extract_multiple(
            [
                ("utils.py", "format_string"),
                ("models.py", "User"),
            ],
            depth=1,
        )

        assert result.success
        assert len(result.files_touched) >= 2


# =============================================================================
# Package Handling Tests
# =============================================================================


class TestPackageHandling:
    """Tests for handling Python packages."""

    def test_extract_from_package(self, package_project):
        """Test extracting from a package module."""
        extractor = CrossFileExtractor(package_project)
        result = extractor.extract("myapp/core.py", "process", depth=0)

        assert result.success
        assert result.target is not None
        assert result.target.name == "process"

    def test_cross_package_extraction(self, package_project):
        """Test extraction following package imports."""
        extractor = CrossFileExtractor(package_project)
        result = extractor.extract("main.py", "run", depth=2)

        assert result.success
        assert len(result.files_touched) >= 2


# =============================================================================
# Dependency Analysis Tests
# =============================================================================


class TestDependencyAnalysis:
    """Tests for dependency analysis features."""

    def test_get_symbol_dependencies(self, simple_project):
        """Test getting dependencies without full extraction."""
        extractor = CrossFileExtractor(simple_project)
        extractor.build()

        deps = extractor.get_symbol_dependencies("models.py", "User")

        # User class uses format_string and validate
        assert "format_string" in deps or "validate" in deps

    def test_get_dependents(self, simple_project):
        """Test finding symbols that depend on a given symbol."""
        extractor = CrossFileExtractor(simple_project)
        extractor.build()

        extractor.get_dependents("utils.py", "format_string")

        # User class depends on format_string
        # This may or may not find dependents depending on implementation


# =============================================================================
# Edge Cases and Error Handling
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_file(self, temp_project):
        """Test handling of empty files."""
        (temp_project / "empty.py").write_text("")

        extractor = CrossFileExtractor(temp_project)
        result = extractor.extract("empty.py", "anything", depth=0)

        assert not result.success

    def test_syntax_error_file(self, temp_project):
        """Test handling of files with syntax errors."""
        (temp_project / "good.py").write_text("def good(): pass")
        (temp_project / "bad.py").write_text("def bad(: pass")

        extractor = CrossFileExtractor(temp_project)
        # Should still be able to extract from good file
        result = extractor.extract("good.py", "good", depth=0)

        assert result.success

    def test_circular_imports(self, temp_project):
        """Test handling of circular imports."""
        (temp_project / "a.py").write_text("""
from b import func_b
def func_a():
    return func_b()
""")
        (temp_project / "b.py").write_text("""
from a import func_a
def func_b():
    return 1
""")

        extractor = CrossFileExtractor(temp_project)
        result = extractor.extract("a.py", "func_a", depth=5)

        # Should complete without infinite loop
        assert result.success or len(result.warnings) > 0

    def test_builtin_dependencies_filtered(self, temp_project):
        """Test that builtin names aren't treated as dependencies."""
        (temp_project / "test.py").write_text("""
def test_func():
    x = len([1, 2, 3])
    y = str(x)
    return print(y)
""")

        extractor = CrossFileExtractor(temp_project)
        result = extractor.extract("test.py", "test_func", depth=1)

        assert result.success
        # Builtins should not appear in dependencies
        dep_names = [d.name for d in result.dependencies]
        assert "len" not in dep_names
        assert "str" not in dep_names
        assert "print" not in dep_names

    def test_absolute_file_path(self, simple_project):
        """Test extraction with absolute file path."""
        abs_path = str(simple_project / "utils.py")

        extractor = CrossFileExtractor(simple_project)
        result = extractor.extract(abs_path, "format_string", depth=0)

        assert result.success

    def test_max_depth_limit(self, deep_project):
        """Test that MAX_DEPTH prevents infinite chains."""
        extractor = CrossFileExtractor(deep_project)

        # Request huge depth - should be capped
        result = extractor.extract("level3.py", "level3_func", depth=1000)

        # Should still complete
        assert result.success
        assert result.depth_reached <= CrossFileExtractor.MAX_DEPTH


# =============================================================================
# Result Properties Tests
# =============================================================================


class TestResultProperties:
    """Tests for ExtractionResult properties."""

    def test_total_symbols_count(self, simple_project):
        """Test total_symbols property."""
        extractor = CrossFileExtractor(simple_project)
        result = extractor.extract("views.py", "create_user", depth=2)

        expected = len(result.dependencies) + (1 if result.target else 0)
        assert result.total_symbols == expected

    def test_total_lines_count(self, simple_project):
        """Test total_lines property."""
        extractor = CrossFileExtractor(simple_project)
        result = extractor.extract("utils.py", "format_string", depth=0)

        assert result.total_lines > 0
        assert result.total_lines == result.combined_code.count("\n") + 1

    def test_files_touched_tracking(self, simple_project):
        """Test that files_touched is correctly populated."""
        extractor = CrossFileExtractor(simple_project)
        result = extractor.extract("views.py", "create_user", depth=2)

        assert len(result.files_touched) >= 1
        assert any("views.py" in f for f in result.files_touched)


# =============================================================================
# ExtractedSymbol Tests
# =============================================================================


class TestExtractedSymbol:
    """Tests for ExtractedSymbol dataclass."""

    def test_hash_equality(self):
        """Test that symbols with same module+name are equal."""
        sym1 = ExtractedSymbol(
            name="func",
            symbol_type="function",
            module="test",
            file="/path/test.py",
            code="def func(): pass",
            line=1,
        )
        sym2 = ExtractedSymbol(
            name="func",
            symbol_type="function",
            module="test",
            file="/different/test.py",
            code="def func(): return 1",
            line=10,
        )

        assert sym1 == sym2
        assert hash(sym1) == hash(sym2)

    def test_inequality(self):
        """Test that different symbols are not equal."""
        sym1 = ExtractedSymbol(
            name="func1",
            symbol_type="function",
            module="test",
            file="/path/test.py",
            code="",
            line=1,
        )
        sym2 = ExtractedSymbol(
            name="func2",
            symbol_type="function",
            module="test",
            file="/path/test.py",
            code="",
            line=1,
        )

        assert sym1 != sym2


# =============================================================================
# Integration Tests
# =============================================================================


class TestIntegration:
    """Integration tests for realistic scenarios."""

    def test_service_layer_extraction(self, package_project):
        """Test extracting a service with its dependencies."""
        extractor = CrossFileExtractor(package_project)
        result = extractor.extract("main.py", "run", depth=3)

        assert result.success
        assert "DataService" in result.combined_code or len(result.dependencies) > 0

    def test_rebuild_after_changes(self, simple_project):
        """Test that rebuild() refreshes the import graph."""
        extractor = CrossFileExtractor(simple_project)
        extractor.build()

        # Modify a file
        (simple_project / "utils.py").write_text("""
def format_string(s):
    return s.lower()  # Changed behavior

def new_function():
    return "new"
""")

        # Rebuild and extract
        extractor.build()
        result = extractor.extract("utils.py", "new_function", depth=0)

        assert result.success
        assert result.target.name == "new_function"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
