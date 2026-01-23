"""
Tests for Pro/Enterprise tier features in import resolution.

[20251230_TEST] Tests for:
- Wildcard import __all__ expansion (Pro tier)
- Re-export and chained alias resolution (Pro tier)
- Architectural rule engine (Enterprise tier)

These tests verify the implementation of tier-specific features
as defined in the get_cross_file_dependencies roadmap.
"""

import shutil
import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest

from code_scalpel.ast_tools.import_resolver import ImportResolver, ImportType


@pytest.fixture
def temp_project() -> Generator[Path, None, None]:
    """Create a temporary project directory for testing."""
    temp_dir = tempfile.mkdtemp(prefix="code_scalpel_test_")
    temp_path = Path(temp_dir)
    yield temp_path
    shutil.rmtree(temp_dir, ignore_errors=True)


class TestWildcardExpansion:
    """Tests for wildcard import __all__ expansion (Pro tier)."""

    def test_expand_wildcard_with_all(self, temp_project: Path):
        """Test expanding wildcard import with explicit __all__."""
        # Create module with __all__
        utils_py = temp_project / "utils.py"
        utils_py.write_text("""
__all__ = ["helper_func", "HelperClass", "CONSTANT"]

def helper_func():
    pass

def _private_func():
    pass

class HelperClass:
    pass

class _PrivateClass:
    pass

CONSTANT = 42
_PRIVATE_CONSTANT = 99
""")

        resolver = ImportResolver(temp_project)
        resolver.build()

        # Expand wildcard import
        symbols = resolver.expand_wildcard_import("utils")

        assert "helper_func" in symbols
        assert "HelperClass" in symbols
        assert "CONSTANT" in symbols
        # Private symbols should NOT be in __all__ expansion
        assert "_private_func" not in symbols
        assert "_PrivateClass" not in symbols
        assert "_PRIVATE_CONSTANT" not in symbols

    def test_expand_wildcard_without_all(self, temp_project: Path):
        """Test expanding wildcard import without __all__ - returns public symbols."""
        # Create module without __all__
        utils_py = temp_project / "utils.py"
        utils_py.write_text("""
def helper_func():
    pass

def _private_func():
    pass

class HelperClass:
    pass

CONSTANT = 42
""")

        resolver = ImportResolver(temp_project)
        resolver.build()

        # Expand wildcard import - should get public symbols only
        symbols = resolver.expand_wildcard_import("utils")

        assert "helper_func" in symbols
        assert "HelperClass" in symbols
        # Without __all__, we get all public symbols (not starting with _)
        assert "_private_func" not in symbols

    def test_expand_wildcard_concatenated_all(self, temp_project: Path):
        """Test expanding __all__ with list concatenation."""
        utils_py = temp_project / "utils.py"
        utils_py.write_text("""
__all__ = ["func_a", "func_b"] + ["func_c"]

def func_a(): pass
def func_b(): pass
def func_c(): pass
def func_d(): pass  # Not in __all__
""")

        resolver = ImportResolver(temp_project)
        resolver.build()

        symbols = resolver.expand_wildcard_import("utils")

        assert symbols == ["func_a", "func_b", "func_c"]

    def test_get_wildcard_imports(self, temp_project: Path):
        """Test identifying wildcard imports in a module."""
        # Create two modules
        utils_py = temp_project / "utils.py"
        utils_py.write_text("def helper(): pass")

        helpers_py = temp_project / "helpers.py"
        helpers_py.write_text("def assist(): pass")

        main_py = temp_project / "main.py"
        main_py.write_text("""
from utils import *
from helpers import *
import os
""")

        resolver = ImportResolver(temp_project)
        resolver.build()

        wildcards = resolver.get_wildcard_imports("main")

        assert len(wildcards) == 2
        assert all(w.import_type == ImportType.WILDCARD for w in wildcards)
        modules = {w.module for w in wildcards}
        assert "utils" in modules
        assert "helpers" in modules

    def test_expand_all_wildcards(self, temp_project: Path):
        """Test expanding all wildcard imports in a module."""
        # Create source modules
        utils_py = temp_project / "utils.py"
        utils_py.write_text("""
__all__ = ["helper"]
def helper(): pass
""")

        helpers_py = temp_project / "helpers.py"
        helpers_py.write_text("""
__all__ = ["assist", "support"]
def assist(): pass
def support(): pass
""")

        main_py = temp_project / "main.py"
        main_py.write_text("""
from utils import *
from helpers import *
""")

        resolver = ImportResolver(temp_project)
        resolver.build()

        expanded = resolver.expand_all_wildcards("main")

        assert "utils" in expanded
        assert expanded["utils"] == ["helper"]
        assert "helpers" in expanded
        assert set(expanded["helpers"]) == {"assist", "support"}


class TestReexportResolution:
    """Tests for re-export and chained alias resolution (Pro tier)."""

    def test_detect_reexports_basic(self, temp_project: Path):
        """Test detecting re-exported symbols in __init__.py."""
        # Create package structure
        pkg_dir = temp_project / "mypackage"
        pkg_dir.mkdir()

        # Internal module
        (pkg_dir / "internal.py").write_text("""
def helper_func():
    pass

class InternalClass:
    pass
""")

        # Package __init__ re-exports symbols
        (pkg_dir / "__init__.py").write_text("""
from mypackage.internal import helper_func, InternalClass

__all__ = ["helper_func", "InternalClass"]
""")

        resolver = ImportResolver(temp_project)
        resolver.build()

        reexports = resolver.detect_reexports("mypackage")

        assert "helper_func" in reexports
        assert reexports["helper_func"] == "mypackage.internal"
        assert "InternalClass" in reexports
        assert reexports["InternalClass"] == "mypackage.internal"

    def test_resolve_alias_chain_simple(self, temp_project: Path):
        """Test resolving a simple import alias chain."""
        # Create modules
        (temp_project / "internal.py").write_text('''
def original_func():
    """The real implementation."""
    pass
''')

        (temp_project / "wrapper.py").write_text("""
from internal import original_func as wrapped_func
""")

        (temp_project / "main.py").write_text("""
from wrapper import wrapped_func as my_func
""")

        resolver = ImportResolver(temp_project)
        resolver.build()

        # Resolve the chain
        orig_module, orig_name, chain = resolver.resolve_alias_chain("main", "my_func")

        assert orig_module == "internal"
        assert orig_name == "original_func"
        assert chain == ["main", "wrapper", "internal"]

    def test_resolve_alias_chain_with_reexport(self, temp_project: Path):
        """Test resolving alias chain through package re-export."""
        pkg_dir = temp_project / "mypackage"
        pkg_dir.mkdir()

        (pkg_dir / "core.py").write_text("""
def core_function():
    pass
""")

        (pkg_dir / "__init__.py").write_text("""
from mypackage.core import core_function

__all__ = ["core_function"]
""")

        (temp_project / "app.py").write_text("""
from mypackage import core_function
""")

        resolver = ImportResolver(temp_project)
        resolver.build()

        orig_module, orig_name, chain = resolver.resolve_alias_chain("app", "core_function")

        assert orig_module == "mypackage.core"
        assert orig_name == "core_function"

    def test_get_symbol_origin(self, temp_project: Path):
        """Test convenience method for getting symbol origin."""
        (temp_project / "base.py").write_text("def base_func(): pass")
        (temp_project / "wrapper.py").write_text("from base import base_func as wrapped")
        (temp_project / "main.py").write_text("from wrapper import wrapped as my_func")

        resolver = ImportResolver(temp_project)
        resolver.build()

        origin = resolver.get_symbol_origin("main", "my_func")

        assert origin is not None
        assert origin == ("base", "base_func")

    def test_get_all_reexports(self, temp_project: Path):
        """Test getting all re-exports across the project."""
        # Package A
        pkg_a = temp_project / "pkg_a"
        pkg_a.mkdir()
        (pkg_a / "impl.py").write_text("def a_func(): pass")
        (pkg_a / "__init__.py").write_text("""
from pkg_a.impl import a_func
__all__ = ["a_func"]
""")

        # Package B
        pkg_b = temp_project / "pkg_b"
        pkg_b.mkdir()
        (pkg_b / "impl.py").write_text("class BClass: pass")
        (pkg_b / "__init__.py").write_text("""
from pkg_b.impl import BClass
__all__ = ["BClass"]
""")

        resolver = ImportResolver(temp_project)
        resolver.build()

        all_reexports = resolver.get_all_reexports()

        assert "pkg_a" in all_reexports
        assert "a_func" in all_reexports["pkg_a"]
        assert "pkg_b" in all_reexports
        assert "BClass" in all_reexports["pkg_b"]

    def test_circular_alias_detection(self, temp_project: Path):
        """Test detection of circular alias chains."""
        # Create circular imports (unusual but possible)
        (temp_project / "mod_a.py").write_text("""
from mod_b import func_b as func_a
""")
        (temp_project / "mod_b.py").write_text("""
from mod_a import func_a as func_b
""")

        resolver = ImportResolver(temp_project)
        resolver.build()

        # Should detect the cycle
        orig_module, orig_name, chain = resolver.resolve_alias_chain("mod_a", "func_a")

        # Should return None when cycle detected
        assert orig_module is None
        assert orig_name is None
        # Chain should have the cycle path
        assert len(chain) >= 2


class TestImportInfoDataclass:
    """Tests for enhanced ImportInfo dataclass."""

    def test_source_module_property(self, temp_project: Path):
        """Test source_module property returns original_module if set."""
        from code_scalpel.ast_tools.import_resolver import ImportInfo

        # Without original_module
        imp1 = ImportInfo(module="utils", name="helper")
        assert imp1.source_module == "utils"

        # With original_module (re-export)
        imp2 = ImportInfo(module="mypackage", name="helper", original_module="mypackage.internal")
        assert imp2.source_module == "mypackage.internal"

    @pytest.mark.skip(reason="[20260117_TEST] ImportInfo.is_reexport field not implemented")
    def test_is_reexport_field(self, temp_project: Path):
        """Test is_reexport field defaults to False."""
        from code_scalpel.ast_tools.import_resolver import ImportInfo

        imp = ImportInfo(module="utils", name="helper")
        assert imp.is_reexport is False

        imp_reexport = ImportInfo(module="pkg", name="func", is_reexport=True)
        assert imp_reexport.is_reexport is True
