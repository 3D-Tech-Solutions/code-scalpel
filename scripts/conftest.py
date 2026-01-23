"""
Root conftest.py for pytest configuration.

This file must be at the repository root to properly configure pytest plugins.
Moved from tests/tools/rename_symbol/conftest.py due to pytest 9.x requirement.
"""

import os
from pathlib import Path

import pytest

# [20260112_FIX] Store original cwd to prevent collection errors when
# tests change directory to temp paths that get cleaned up.
_ORIGINAL_CWD = Path.cwd()

# Plugins for rename_symbol tier testing
pytest_plugins = ["tests.tools.rename_symbol.governance_profiles"]


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_collect_file(parent, file_path):
    """Ensure cwd is reset before each file collection."""
    try:
        os.chdir(_ORIGINAL_CWD)
    except OSError:
        pass
    yield


@pytest.fixture(autouse=True)
def reset_tier_globals():
    """[20260113_FIX] Reset tier-related globals to prevent test pollution.

    Some tests set environment variables or modify tier state. This fixture
    ensures the tier state is clean before AND after each test to prevent flaky
    failures due to state leakage between tests.

    Note: We don't clear env vars here because that interferes with test fixtures
    that intentionally set them (like patch_tier). Instead, we just reset the
    internal caches that cause stale state.
    """

    def _reset():
        # Reset tier globals in MCP server
        try:
            import code_scalpel.mcp.server as server

            server._LAST_VALID_LICENSE_AT = None
            server._LAST_VALID_LICENSE_TIER = "community"
        except (ImportError, AttributeError):
            pass

        # Clear config cache to force fresh tier detection
        try:
            from code_scalpel.licensing.config_loader import clear_cache

            clear_cache()
        except (ImportError, AttributeError):
            pass

        # Clear governance cache
        try:
            import code_scalpel.mcp.server as server

            if hasattr(server, "_GOVERNANCE_VERIFY_CACHE"):
                server._GOVERNANCE_VERIFY_CACHE.clear()
        except (ImportError, AttributeError):
            pass

    # Reset BEFORE the test runs
    _reset()

    yield  # Run the test

    # Reset AFTER the test completes
    _reset()
