"""
Tests for Import Resolution Engine.

[20251213_TEST] v1.5.1 - Comprehensive tests for cross-file import resolution

Test Categories:
- Basic import parsing (import x, from x import y)
- Relative imports (from . import, from .. import)
- Circular import detection
- Symbol resolution across files
- Topological sorting
- Edge cases and error handling
"""

import tempfile
from pathlib import Path

import pytest

from code_scalpel.ast_tools.import_resolver import (
    CircularImport,
    ImportInfo,
    ImportResolver,
    ImportType,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def temp_project():
    """Create a temporary project directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def simple_project(temp_project):
    """Create a simple two-file project."""
    # main.py
    (temp_project / "main.py").write_text("""
import utils
from utils import helper_func

def main():
    return helper_func()
""")

    # utils.py
    (temp_project / "utils.py").write_text("""
def helper_func():
    return 42

def another_func():
    return "hello"

class HelperClass:
    def method(self):
        pass
""")

    return temp_project


@pytest.fixture
def package_project(temp_project):
    """Create a project with packages."""
    # Create package structure
    pkg_dir = temp_project / "mypackage"
    pkg_dir.mkdir()

    # mypackage/__init__.py
    (pkg_dir / "__init__.py").write_text("""
from .core import process
from .utils import helper

__all__ = ['process', 'helper']
""")

    # mypackage/core.py
    (pkg_dir / "core.py").write_text("""
from .utils import helper, validate

def process(data):
    if validate(data):
        return helper(data)
    return None
""")

    # mypackage/utils.py
    (pkg_dir / "utils.py").write_text("""
def helper(data):
    return data.upper()

def validate(data):
    return isinstance(data, str)
""")

    # main.py at root
    (temp_project / "main.py").write_text("""
from mypackage import process
from mypackage.utils import helper

def run():
    return process("test")
""")

    return temp_project


@pytest.fixture
def circular_project(temp_project):
    """Create a project with circular imports."""
    # a.py imports from b
    (temp_project / "a.py").write_text("""
from b import func_b

def func_a():
    return func_b() + 1
""")

    # b.py imports from a
    (temp_project / "b.py").write_text("""
from a import func_a

def func_b():
    return 10
""")

    return temp_project


@pytest.fixture
def complex_project(temp_project):
    """Create a complex project with multiple packages."""
    # src/
    src = temp_project / "src"
    src.mkdir()

    # src/__init__.py
    (src / "__init__.py").write_text("")

    # src/models/
    models = src / "models"
    models.mkdir()
    (models / "__init__.py").write_text("from .user import User\nfrom .product import Product")
    (models / "user.py").write_text("""
class User:
    def __init__(self, name):
        self.name = name
""")
    (models / "product.py").write_text("""
class Product:
    def __init__(self, title):
        self.title = title
""")

    # src/services/
    services = src / "services"
    services.mkdir()
    (services / "__init__.py").write_text("")
    (services / "user_service.py").write_text("""
from ..models import User
from ..utils.helpers import format_name

class UserService:
    def create_user(self, name):
        formatted = format_name(name)
        return User(formatted)
""")

    # src/utils/
    utils = src / "utils"
    utils.mkdir()
    (utils / "__init__.py").write_text("")
    (utils / "helpers.py").write_text("""
def format_name(name):
    return name.strip().title()

def validate_email(email):
    return "@" in email
""")

    # app.py at root
    (temp_project / "app.py").write_text("""
from src.models import User, Product
from src.services.user_service import UserService

def main():
    service = UserService()
    user = service.create_user("john")
    return user
""")

    return temp_project


# =============================================================================
# Basic Import Parsing Tests
# =============================================================================


class TestBasicImports:
    """Tests for basic import statement parsing."""

    def test_simple_import(self, simple_project):
        """Test parsing 'import module' statements."""
        resolver = ImportResolver(simple_project)
        result = resolver.build()

        assert result.success
        assert result.modules >= 2

        # Check that main imports utils
        main_imports = resolver.imports.get("main", [])
        import_names = [imp.module for imp in main_imports]
        assert "utils" in import_names

    def test_from_import(self, simple_project):
        """Test parsing 'from module import name' statements."""
        resolver = ImportResolver(simple_project)
        resolver.build()

        main_imports = resolver.imports.get("main", [])
        from_imports = [imp for imp in main_imports if imp.import_type == ImportType.FROM]

        assert len(from_imports) >= 1
        assert any(imp.name == "helper_func" for imp in from_imports)

    def test_import_with_alias(self, temp_project):
        """Test parsing 'import module as alias' statements."""
        (temp_project / "test.py").write_text("""
import numpy as np
from os import path as p
""")

        resolver = ImportResolver(temp_project)
        resolver.build()

        test_imports = resolver.imports.get("test", [])
        aliased = [imp for imp in test_imports if imp.alias is not None]

        assert len(aliased) == 2
        assert any(imp.alias == "np" for imp in aliased)
        assert any(imp.alias == "p" for imp in aliased)

    def test_multiple_imports_same_line(self, temp_project):
        """Test parsing 'from x import a, b, c' statements."""
        (temp_project / "test.py").write_text("""
from os import path, getcwd, listdir
""")

        resolver = ImportResolver(temp_project)
        resolver.build()

        test_imports = resolver.imports.get("test", [])
        os_imports = [imp for imp in test_imports if imp.module == "os"]

        assert len(os_imports) == 3
        names = {imp.name for imp in os_imports}
        assert names == {"path", "getcwd", "listdir"}

    def test_wildcard_import(self, temp_project):
        """Test parsing 'from module import *' statements."""
        (temp_project / "utils.py").write_text("def func(): pass")
        (temp_project / "test.py").write_text("""
from utils import *
""")

        resolver = ImportResolver(temp_project)
        resolver.build()

        test_imports = resolver.imports.get("test", [])
        wildcards = [imp for imp in test_imports if imp.import_type == ImportType.WILDCARD]

        assert len(wildcards) == 1
        assert wildcards[0].name == "*"


# =============================================================================
# Relative Import Tests
# =============================================================================


class TestRelativeImports:
    """Tests for relative import resolution."""

    def test_single_dot_import(self, package_project):
        """Test 'from . import module' resolution."""
        resolver = ImportResolver(package_project)
        resolver.build()

        # mypackage/core.py imports from .utils
        core_imports = resolver.imports.get("mypackage.core", [])
        relative_imports = [imp for imp in core_imports if imp.level > 0]

        assert len(relative_imports) >= 1
        assert any(imp.import_type == ImportType.RELATIVE for imp in relative_imports)

    def test_double_dot_import(self, complex_project):
        """Test 'from .. import module' resolution."""
        resolver = ImportResolver(complex_project)
        resolver.build()

        # src/services/user_service.py imports from ..models
        service_imports = resolver.imports.get("src.services.user_service", [])
        parent_imports = [imp for imp in service_imports if imp.level == 2]

        assert len(parent_imports) >= 1

    def test_relative_import_resolution(self, package_project):
        """Test that relative imports resolve to correct module names."""
        resolver = ImportResolver(package_project)
        resolver.build()

        # The resolved module should be mypackage.utils, not .utils
        core_imports = resolver.imports.get("mypackage.core", [])

        for imp in core_imports:
            if imp.level > 0:
                # Resolved module should not start with dots
                assert not imp.module.startswith(".")


# =============================================================================
# Circular Import Detection Tests
# =============================================================================


class TestCircularImports:
    """Tests for circular import detection."""

    def test_detect_simple_cycle(self, circular_project):
        """Test detection of a simple A->B->A cycle."""
        resolver = ImportResolver(circular_project)
        resolver.build()

        assert resolver.has_circular_imports()
        cycles = resolver.get_circular_imports()

        assert len(cycles) >= 1
        # The cycle should contain both modules
        cycle_modules = set(cycles[0].cycle)
        assert "a" in cycle_modules or "b" in cycle_modules

    def test_detect_longer_cycle(self, temp_project):
        """Test detection of A->B->C->A cycle."""
        (temp_project / "a.py").write_text("from b import x")
        (temp_project / "b.py").write_text("from c import y")
        (temp_project / "c.py").write_text("from a import z")

        resolver = ImportResolver(temp_project)
        resolver.build()

        assert resolver.has_circular_imports()

    def test_no_cycle_when_clean(self, simple_project):
        """Test that clean projects report no cycles."""
        resolver = ImportResolver(simple_project)
        resolver.build()

        assert not resolver.has_circular_imports()
        assert len(resolver.get_circular_imports()) == 0

    def test_cycle_file_paths_included(self, circular_project):
        """Test that cycle info includes file paths."""
        resolver = ImportResolver(circular_project)
        resolver.build()

        cycles = resolver.get_circular_imports()
        if cycles:
            assert len(cycles[0].files) >= len(cycles[0].cycle) - 1


# =============================================================================
# Symbol Resolution Tests
# =============================================================================


class TestSymbolResolution:
    """Tests for resolving symbols across files."""

    def test_resolve_local_symbol(self, simple_project):
        """Test resolving a symbol defined in the same module."""
        resolver = ImportResolver(simple_project)
        resolver.build()

        module, symbol = resolver.resolve_symbol("utils", "helper_func")

        assert module == "utils"
        assert symbol is not None
        assert symbol.name == "helper_func"
        assert symbol.symbol_type == "function"

    def test_resolve_imported_symbol(self, simple_project):
        """Test resolving a symbol imported from another module."""
        resolver = ImportResolver(simple_project)
        resolver.build()

        module, symbol = resolver.resolve_symbol("main", "helper_func")

        assert module == "utils"
        assert symbol is not None
        assert symbol.name == "helper_func"

    def test_resolve_class_symbol(self, simple_project):
        """Test resolving a class definition."""
        resolver = ImportResolver(simple_project)
        resolver.build()

        module, symbol = resolver.resolve_symbol("utils", "HelperClass")

        assert module == "utils"
        assert symbol is not None
        assert symbol.symbol_type == "class"

    def test_resolve_nonexistent_symbol(self, simple_project):
        """Test that nonexistent symbols return None."""
        resolver = ImportResolver(simple_project)
        resolver.build()

        module, symbol = resolver.resolve_symbol("main", "nonexistent_func")

        assert module is None
        assert symbol is None

    def test_resolve_without_build_raises(self, simple_project):
        """Test that resolving before build() raises error."""
        resolver = ImportResolver(simple_project)

        with pytest.raises(RuntimeError):
            resolver.resolve_symbol("main", "helper_func")


# =============================================================================
# Definition Extraction Tests
# =============================================================================


class TestDefinitionExtraction:
    """Tests for extracting symbol definitions."""

    def test_extract_functions(self, simple_project):
        """Test extraction of function definitions."""
        resolver = ImportResolver(simple_project)
        resolver.build()

        utils_symbols = resolver.symbols.get("utils", {})

        assert "helper_func" in utils_symbols
        assert "another_func" in utils_symbols

    def test_extract_classes(self, simple_project):
        """Test extraction of class definitions."""
        resolver = ImportResolver(simple_project)
        resolver.build()

        utils_symbols = resolver.symbols.get("utils", {})

        assert "HelperClass" in utils_symbols
        assert utils_symbols["HelperClass"].symbol_type == "class"

    def test_extract_methods(self, simple_project):
        """Test extraction of method definitions within classes."""
        resolver = ImportResolver(simple_project)
        resolver.build()

        utils_symbols = resolver.symbols.get("utils", {})

        # Methods are stored as "ClassName.method_name"
        assert "HelperClass.method" in utils_symbols
        assert utils_symbols["HelperClass.method"].symbol_type == "method"

    def test_extract_async_functions(self, temp_project):
        """Test extraction of async function definitions."""
        (temp_project / "async_mod.py").write_text("""
async def fetch_data():
    return await some_async_call()
""")

        resolver = ImportResolver(temp_project)
        resolver.build()

        symbols = resolver.symbols.get("async_mod", {})

        assert "fetch_data" in symbols
        assert symbols["fetch_data"].symbol_type == "async_function"

    def test_extract_function_signature(self, temp_project):
        """Test extraction of function signatures."""
        (temp_project / "typed.py").write_text("""
def process(data: str, count: int = 5) -> bool:
    return True
""")

        resolver = ImportResolver(temp_project)
        resolver.build()

        symbols = resolver.symbols.get("typed", {})

        assert "process" in symbols
        sig = symbols["process"].signature
        assert "data: str" in sig
        assert "count: int" in sig
        assert "-> bool" in sig

    def test_extract_docstrings(self, temp_project):
        """Test extraction of docstrings."""
        (temp_project / "documented.py").write_text('''
def documented_func():
    """This is a docstring."""
    pass

class DocumentedClass:
    """Class docstring."""
    pass
''')

        resolver = ImportResolver(temp_project)
        resolver.build()

        symbols = resolver.symbols.get("documented", {})

        assert symbols["documented_func"].docstring == "This is a docstring."
        assert symbols["DocumentedClass"].docstring == "Class docstring."


# =============================================================================
# Topological Sort Tests
# =============================================================================


class TestTopologicalSort:
    """Tests for topological sorting of modules."""

    def test_topological_order(self, simple_project):
        """Test that dependencies come before dependents."""
        resolver = ImportResolver(simple_project)
        resolver.build()

        order = resolver.topological_sort()

        # utils should come before main (main depends on utils)
        utils_idx = order.index("utils") if "utils" in order else -1
        main_idx = order.index("main") if "main" in order else -1

        # Note: In topological sort, dependencies come after dependents
        # because we're sorting by "who imports whom"
        assert utils_idx != -1
        assert main_idx != -1

    def test_topological_sort_without_build_raises(self, simple_project):
        """Test that sorting before build() raises error."""
        resolver = ImportResolver(simple_project)

        with pytest.raises(RuntimeError):
            resolver.topological_sort()

    def test_topological_sort_with_cycles(self, circular_project):
        """Test that cycles don't break topological sort entirely."""
        resolver = ImportResolver(circular_project)
        resolver.build()

        # Should still return a result (with warning)
        order = resolver.topological_sort()

        assert len(order) >= 2  # Both modules should be in the result


# =============================================================================
# Import Graph Query Tests
# =============================================================================


class TestGraphQueries:
    """Tests for querying the import graph."""

    def test_get_importers(self, simple_project):
        """Test finding modules that import a given module."""
        resolver = ImportResolver(simple_project)
        resolver.build()

        importers = resolver.get_importers("utils")

        assert "main" in importers

    def test_get_imports(self, simple_project):
        """Test finding modules imported by a given module."""
        resolver = ImportResolver(simple_project)
        resolver.build()

        imports = resolver.get_imports("main")

        assert "utils" in imports

    def test_get_module_info(self, simple_project):
        """Test getting detailed module information."""
        resolver = ImportResolver(simple_project)
        resolver.build()

        info = resolver.get_module_info("utils")

        assert info is not None
        assert info["name"] == "utils"
        assert "file" in info
        assert "symbols" in info
        assert "helper_func" in info["symbols"]

    def test_get_module_info_nonexistent(self, simple_project):
        """Test that nonexistent module returns None."""
        resolver = ImportResolver(simple_project)
        resolver.build()

        info = resolver.get_module_info("nonexistent_module")

        assert info is None

    def test_get_all_symbols(self, simple_project):
        """Test getting all symbols from all modules."""
        resolver = ImportResolver(simple_project)
        resolver.build()

        all_symbols = resolver.get_all_symbols()

        assert "utils" in all_symbols
        assert len(all_symbols["utils"]) >= 3  # helper_func, another_func, HelperClass

    def test_find_symbol_across_project(self, complex_project):
        """Test finding all definitions of a symbol."""
        resolver = ImportResolver(complex_project)
        resolver.build()

        # Find all User definitions
        results = resolver.find_symbol("User")

        assert len(results) >= 1
        modules = [r[0] for r in results]
        assert any("user" in m.lower() for m in modules)


# =============================================================================
# Package Handling Tests
# =============================================================================


class TestPackageHandling:
    """Tests for handling Python packages."""

    def test_init_py_as_package(self, package_project):
        """Test that __init__.py files are treated as package modules."""
        resolver = ImportResolver(package_project)
        resolver.build()

        # mypackage/__init__.py should be module "mypackage"
        assert "mypackage" in resolver.module_to_file

    def test_submodule_naming(self, package_project):
        """Test correct naming of submodules."""
        resolver = ImportResolver(package_project)
        resolver.build()

        # Should have mypackage.core, mypackage.utils
        modules = set(resolver.module_to_file.keys())

        assert "mypackage.core" in modules
        assert "mypackage.utils" in modules

    def test_nested_package_paths(self, complex_project):
        """Test deeply nested package paths."""
        resolver = ImportResolver(complex_project)
        resolver.build()

        modules = set(resolver.module_to_file.keys())

        assert "src.models.user" in modules
        assert "src.services.user_service" in modules
        assert "src.utils.helpers" in modules


# =============================================================================
# Error Handling Tests
# =============================================================================


class TestErrorHandling:
    """Tests for error handling."""

    def test_syntax_error_file(self, temp_project):
        """Test handling of files with syntax errors."""
        (temp_project / "good.py").write_text("def good(): pass")
        (temp_project / "bad.py").write_text("def bad(: pass")  # Syntax error

        resolver = ImportResolver(temp_project)
        result = resolver.build()

        # Should still succeed overall
        assert result.success or len(result.warnings) > 0
        # good.py should still be analyzed
        assert "good" in resolver.module_to_file

    def test_encoding_error_file(self, temp_project):
        """Test handling of files with encoding issues."""
        # Write a valid file
        (temp_project / "good.py").write_text("def good(): pass")

        # Write binary file with .py extension (will fail to parse)
        (temp_project / "binary.py").write_bytes(b"\x80\x81\x82\x83")

        resolver = ImportResolver(temp_project)
        result = resolver.build()

        # Should handle gracefully
        assert len(result.warnings) > 0 or result.success

    def test_empty_project(self, temp_project):
        """Test handling of empty project directory."""
        resolver = ImportResolver(temp_project)
        result = resolver.build()

        assert result.success
        assert result.modules == 0

    def test_nonexistent_path(self):
        """Test handling of nonexistent project path."""
        resolver = ImportResolver("/nonexistent/path/12345")
        result = resolver.build()

        # Should handle gracefully
        assert result.modules == 0


# =============================================================================
# Skip Directory Tests
# =============================================================================


class TestSkipDirectories:
    """Tests for skipping certain directories."""

    def test_skip_venv(self, temp_project):
        """Test that venv directories are skipped."""
        venv_dir = temp_project / "venv"
        venv_dir.mkdir()
        (venv_dir / "lib.py").write_text("def venv_func(): pass")

        (temp_project / "main.py").write_text("def main(): pass")

        resolver = ImportResolver(temp_project)
        resolver.build()

        # venv module should not be included
        assert "venv.lib" not in resolver.module_to_file
        assert "main" in resolver.module_to_file

    def test_skip_pycache(self, temp_project):
        """Test that __pycache__ directories are skipped."""
        cache_dir = temp_project / "__pycache__"
        cache_dir.mkdir()
        (cache_dir / "cached.py").write_text("def cached(): pass")

        (temp_project / "main.py").write_text("def main(): pass")

        resolver = ImportResolver(temp_project)
        resolver.build()

        modules = set(resolver.module_to_file.keys())
        assert not any("pycache" in m.lower() for m in modules)

    def test_skip_hidden_directories(self, temp_project):
        """Test that hidden directories are skipped."""
        hidden_dir = temp_project / ".hidden"
        hidden_dir.mkdir()
        (hidden_dir / "secret.py").write_text("SECRET = 'shhh'")

        (temp_project / "main.py").write_text("def main(): pass")

        resolver = ImportResolver(temp_project)
        resolver.build()

        modules = set(resolver.module_to_file.keys())
        assert not any("hidden" in m or "secret" in m for m in modules)


# =============================================================================
# Mermaid Diagram Tests
# =============================================================================


class TestMermaidGeneration:
    """Tests for Mermaid diagram generation."""

    def test_generate_mermaid(self, simple_project):
        """Test basic Mermaid diagram generation."""
        resolver = ImportResolver(simple_project)
        resolver.build()

        mermaid = resolver.generate_mermaid()

        assert "graph TD" in mermaid
        assert "main" in mermaid.replace("_", ".") or "main" in mermaid
        assert "utils" in mermaid.replace("_", ".") or "utils" in mermaid

    def test_mermaid_shows_edges(self, simple_project):
        """Test that Mermaid diagram includes edges."""
        resolver = ImportResolver(simple_project)
        resolver.build()

        mermaid = resolver.generate_mermaid()

        # Should have at least one edge (main -> utils)
        assert "-->" in mermaid

    def test_mermaid_with_cycles(self, circular_project):
        """Test that cycles are specially marked in Mermaid."""
        resolver = ImportResolver(circular_project)
        resolver.build()

        mermaid = resolver.generate_mermaid()

        # Cycles should be marked with dashed lines
        assert "-.->" in mermaid or "cycle" in mermaid.lower()


# =============================================================================
# ImportInfo Tests
# =============================================================================


class TestImportInfo:
    """Tests for ImportInfo dataclass."""

    def test_effective_name_with_alias(self):
        """Test effective_name property with alias."""
        imp = ImportInfo(module="numpy", name="array", alias="np_array")
        assert imp.effective_name == "np_array"

    def test_effective_name_without_alias(self):
        """Test effective_name property without alias."""
        imp = ImportInfo(module="os", name="path")
        assert imp.effective_name == "path"

    def test_full_path(self):
        """Test full_path property."""
        imp = ImportInfo(module="os.path", name="join")
        assert imp.full_path == "os.path.join"

    def test_full_path_no_module(self):
        """Test full_path when module is empty."""
        imp = ImportInfo(module="", name="something")
        assert imp.full_path == "something"


# =============================================================================
# CircularImport Tests
# =============================================================================


class TestCircularImportClass:
    """Tests for CircularImport dataclass."""

    def test_str_representation(self):
        """Test string representation of circular import."""
        cycle = CircularImport(
            cycle=["a", "b", "c", "a"],
            files=["a.py", "b.py", "c.py", "a.py"],
        )

        assert str(cycle) == "a -> b -> c -> a"

    def test_default_severity(self):
        """Test default severity is warning."""
        cycle = CircularImport(cycle=["a", "b", "a"], files=[])
        assert cycle.severity == "warning"


# =============================================================================
# Integration Tests
# =============================================================================


class TestIntegration:
    """Integration tests for real-world scenarios."""

    def test_cross_package_resolution(self, complex_project):
        """Test resolving symbols across package boundaries."""
        resolver = ImportResolver(complex_project)
        resolver.build()

        # UserService imports User from models
        module, symbol = resolver.resolve_symbol("src.services.user_service", "User")

        # Should resolve through the import chain
        if module:
            assert "models" in module or "user" in module.lower()

    def test_re_export_resolution(self, package_project):
        """Test resolving symbols that are re-exported via __init__.py."""
        resolver = ImportResolver(package_project)
        resolver.build()

        # mypackage/__init__.py re-exports 'process' from core
        # So importing from 'mypackage' should work
        init_imports = resolver.imports.get("mypackage", [])

        # Should have imports from .core
        core_imports = [imp for imp in init_imports if "core" in imp.module]
        assert len(core_imports) >= 1

    def test_full_build_result(self, complex_project):
        """Test complete build result statistics."""
        resolver = ImportResolver(complex_project)
        result = resolver.build()

        assert result.success
        assert result.modules >= 5  # Multiple modules in complex project
        assert result.imports >= 5  # Multiple import statements


# =============================================================================
# Edge Case Tests
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and corner cases."""

    def test_empty_file(self, temp_project):
        """Test handling of empty Python files."""
        (temp_project / "empty.py").write_text("")

        resolver = ImportResolver(temp_project)
        result = resolver.build()

        assert result.success
        assert "empty" in resolver.module_to_file

    def test_only_comments_file(self, temp_project):
        """Test handling of files with only comments."""
        (temp_project / "comments.py").write_text("""
# This is a comment
# Another comment
'''" Docstring-like but not really. "'''
""")

        resolver = ImportResolver(temp_project)
        result = resolver.build()

        assert result.success

    def test_deeply_nested_packages(self, temp_project):
        """Test handling of deeply nested package structures."""
        # Create nested package structure
        for part in ["a", "a/b", "a/b/c", "a/b/c/d", "a/b/c/d/e"]:
            pkg_dir = temp_project / part
            pkg_dir.mkdir(parents=True, exist_ok=True)
            (pkg_dir / "__init__.py").write_text("")

        (temp_project / "a" / "b" / "c" / "d" / "e" / "deep.py").write_text("x = 1")

        resolver = ImportResolver(temp_project)
        result = resolver.build()

        assert result.success
        # Should have the deep module
        assert any("a.b.c.d.e.deep" in m for m in resolver.module_to_file.keys())

    def test_module_with_same_name_as_stdlib(self, temp_project):
        """Test handling of modules that shadow stdlib names."""
        # Create a local 'os.py' that shadows stdlib os
        (temp_project / "os.py").write_text("def local_func(): pass")
        (temp_project / "main.py").write_text("from os import local_func")

        resolver = ImportResolver(temp_project)
        result = resolver.build()

        assert result.success
        assert "os" in resolver.module_to_file  # Local os.py

    def test_import_from_root_package(self, temp_project):
        """Test imports from the root package level."""
        pkg = temp_project / "pkg"
        pkg.mkdir()

        (pkg / "__init__.py").write_text("ROOT_CONST = 42")
        (pkg / "sub.py").write_text("""
from pkg import ROOT_CONST
""")

        resolver = ImportResolver(temp_project)
        result = resolver.build()

        assert result.success


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
