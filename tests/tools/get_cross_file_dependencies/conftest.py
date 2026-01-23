"""Pytest fixtures for get_cross_file_dependencies tests.

Provides:
- Symbol-level dependency extraction fixtures (target_file + target_symbol)
- Test project templates
- Tier-aware server mocks
- Helper validation functions

[20260103_TEST] v3.3.0 - Symbol-level API fixtures matching actual implementation
[20260111_FIX] v3.3.0 - Fixed tier mocking to properly patch _get_current_tier()
[20260113_FIX] v3.3.0 - Added license state cleanup to prevent tier pollution
"""

from unittest.mock import patch

import pytest


def _cleanup_tier_state():
    """Reset all tier-related caches and globals to prevent test pollution."""
    try:
        import code_scalpel.mcp.server as server

        server._LAST_VALID_LICENSE_AT = None
        server._LAST_VALID_LICENSE_TIER = "community"
    except (ImportError, AttributeError):
        pass

    try:
        from code_scalpel.licensing.config_loader import clear_cache

        clear_cache()
    except (ImportError, AttributeError):
        pass


# ====================
# MCP Server Fixtures
# ====================


@pytest.fixture
def community_server():
    """MCP server with Community tier license (properly mocked).

    [20260111_FIX] Uses patch to mock _get_current_tier() so tier limits
    are actually enforced (max_depth=1, max_files=50).
    [20260113_FIX] Cleans up tier state after use to prevent pollution.
    """
    from code_scalpel.mcp.server import get_cross_file_dependencies

    class MockCommunityServer:
        def __init__(self):
            self._tier = "community"

        async def get_cross_file_dependencies(self, target_file, target_symbol, **kwargs):
            """Symbol-level API with Community tier limits enforced."""
            _cleanup_tier_state()
            with patch("code_scalpel.mcp.server._get_current_tier", return_value="community"):
                result = await get_cross_file_dependencies(
                    target_file=target_file, target_symbol=target_symbol, **kwargs
                )
            _cleanup_tier_state()
            return result

    return MockCommunityServer()


@pytest.fixture
def pro_server():
    """MCP server with Pro tier license (properly mocked).

    [20260111_FIX] Uses patch to mock _get_current_tier() so tier limits
    are actually enforced (max_depth=5, max_files=500).
    [20260113_FIX] Cleans up tier state after use to prevent pollution.
    """
    from code_scalpel.mcp.server import get_cross_file_dependencies

    class MockProServer:
        def __init__(self):
            self._tier = "pro"

        async def get_cross_file_dependencies(self, target_file, target_symbol, **kwargs):
            """Symbol-level API with Pro tier features and limits enforced."""
            _cleanup_tier_state()
            with patch("code_scalpel.mcp.server._get_current_tier", return_value="pro"):
                result = await get_cross_file_dependencies(
                    target_file=target_file, target_symbol=target_symbol, **kwargs
                )
            _cleanup_tier_state()
            return result

    return MockProServer()


@pytest.fixture
def enterprise_server():
    """MCP server with Enterprise tier license (properly mocked).

    [20260111_FIX] Uses patch to mock _get_current_tier() so unlimited
    depth/files is available.
    [20260113_FIX] Cleans up tier state after use to prevent pollution.
    """
    from code_scalpel.mcp.server import get_cross_file_dependencies

    class MockEnterpriseServer:
        def __init__(self):
            self._tier = "enterprise"

        async def get_cross_file_dependencies(self, target_file, target_symbol, **kwargs):
            """Symbol-level API with Enterprise tier features (unlimited)."""
            _cleanup_tier_state()
            with patch("code_scalpel.mcp.server._get_current_tier", return_value="enterprise"):
                result = await get_cross_file_dependencies(
                    target_file=target_file, target_symbol=target_symbol, **kwargs
                )
            _cleanup_tier_state()
            return result

    return MockEnterpriseServer()


# ====================
# Test Project Fixtures
# ====================


@pytest.fixture
def simple_two_file_project(tmp_path):
    """Simple 2-file project: a.py imports b.py"""
    a_py = tmp_path / "a.py"
    b_py = tmp_path / "b.py"

    b_py.write_text("def helper(): return 42")
    a_py.write_text("from b import helper\n\ndef main(): return helper()")

    return {
        "root": str(tmp_path),
        "target_file": str(a_py),
        "target_symbol": "main",
    }


@pytest.fixture
def circular_import_project(tmp_path):
    """Circular import: a.py → b.py → a.py"""
    a_py = tmp_path / "a.py"
    b_py = tmp_path / "b.py"

    a_py.write_text("from b import func_b\n\ndef func_a(): return 'A'")
    b_py.write_text("from a import func_a\n\ndef func_b(): return 'B'")

    return {
        "root": str(tmp_path),
        "target_file": str(a_py),
        "target_symbol": "func_a",
        "circular": True,
    }


@pytest.fixture
def deep_chain_project(tmp_path):
    """Deep dependency chain: a → b → c → d → e"""
    # Create files in reverse order so imports work
    e_py = tmp_path / "e.py"
    d_py = tmp_path / "d.py"
    c_py = tmp_path / "c.py"
    b_py = tmp_path / "b.py"
    a_py = tmp_path / "a.py"

    e_py.write_text("def func_e(): return 'E'")
    d_py.write_text("from e import func_e\ndef func_d(): return func_e()")
    c_py.write_text("from d import func_d\ndef func_c(): return func_d()")
    b_py.write_text("from c import func_c\ndef func_b(): return func_c()")
    a_py.write_text("from b import func_b\ndef func_a(): return func_b()")

    return {
        "root": str(tmp_path),
        "target_file": str(a_py),
        "target_symbol": "func_a",
        "depth": 5,
    }


@pytest.fixture
def wildcard_import_project(tmp_path):
    """Project with wildcard imports and __all__ expansion"""
    utils = tmp_path / "utils.py"
    utils.write_text(
        "__all__ = ['helper1', 'helper2', 'helper3']\n"
        "def helper1(): return 1\n"
        "def helper2(): return 2\n"
        "def helper3(): return 3\n"
        "def _private(): return 'private'\n"
    )

    main = tmp_path / "main.py"
    main.write_text("from utils import *\n\ndef use_all(): return helper1() + helper2()")

    return {
        "root": str(tmp_path),
        "target_file": str(main),
        "target_symbol": "use_all",
        "wildcard": True,
    }


@pytest.fixture
def alias_import_project(tmp_path):
    """Project with import aliases"""
    module_a = tmp_path / "module_a.py"
    module_a.write_text("def original_func(): return 'original'")

    module_b = tmp_path / "module_b.py"
    module_b.write_text(
        "import module_a as m\n"
        "from module_a import original_func as renamed\n"
        "def use_alias(): return m.original_func() + renamed()"
    )

    return {
        "root": str(tmp_path),
        "target_file": str(module_b),
        "target_symbol": "use_alias",
        "aliases": True,
    }


@pytest.fixture
def reexport_project(tmp_path):
    """Project with package re-exports via __init__.py"""
    pkg = tmp_path / "mypackage"
    pkg.mkdir()

    (pkg / "core.py").write_text("def core_func(): return 'core'")
    (pkg / "utils.py").write_text("def util_func(): return 'util'")

    # Package __init__.py re-exports
    (pkg / "__init__.py").write_text(
        "from mypackage.core import core_func\n"
        "from mypackage.utils import util_func\n"
        "__all__ = ['core_func', 'util_func']\n"
    )

    main = tmp_path / "main.py"
    main.write_text("from mypackage import core_func, util_func\n\ndef use(): return core_func()")

    return {
        "root": str(tmp_path),
        "target_file": str(main),
        "target_symbol": "use",
        "reexport": True,
    }


# ====================
# Helper Functions
# ====================


def validate_tier_limits(result, tier, max_depth=None):
    """Validate that result respects tier limits.

    Args:
        result: CrossFileDependenciesResult
        tier: 'community', 'pro', or 'enterprise'
        max_depth: optional expected max depth
    """
    assert result.success is True, f"Analysis failed: {result.error}"

    # Check transitive depth based on tier
    if tier == "community":
        assert result.transitive_depth <= 1, f"Community tier exceeded max_depth=1: got {result.transitive_depth}"
    elif tier == "pro":
        assert result.transitive_depth <= 5, f"Pro tier exceeded max_depth=5: got {result.transitive_depth}"
    elif tier == "enterprise":
        # Enterprise has unlimited depth
        pass

    if max_depth is not None:
        assert result.transitive_depth <= max_depth, f"Expected max_depth={max_depth}, got {result.transitive_depth}"


def get_max_dependency_depth(result):
    """Calculate max depth in dependency chains from result."""
    if not result.dependency_chains:
        return 0
    return max(len(chain) for chain in result.dependency_chains)


# ====================
# License Mock Utilities
# ====================


def mock_expired_license():
    """Mock an expired license (should fallback to Community)."""
    return {"valid": False, "tier": "pro", "expired": True}


def mock_invalid_license():
    """Mock an invalid license (should fallback to Community)."""
    return {"valid": False, "tier": None, "expired": False}


def mock_missing_license():
    """Mock missing license (should default to Community)."""
    return None
