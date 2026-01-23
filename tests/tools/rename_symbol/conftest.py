# [20260108_TEST] Fixtures for rename_symbol tier tests
"""
Shared fixtures for rename_symbol tier testing.
"""

import pytest

# NOTE: pytest_plugins moved to root conftest.py (pytest 9.x requirement)
# pytest_plugins = ["tests.tools.rename_symbol.governance_profiles"]


@pytest.fixture
def temp_project(tmp_path):
    """Create a temporary project with multiple files for cross-file testing."""

    # Main module with functions/classes
    main_py = tmp_path / "main.py"
    main_py.write_text("""
def old_function():
    return "hello"

class OldClass:
    def old_method(self):
        return "method"
""".strip())

    # File that imports from main
    utils_py = tmp_path / "utils.py"
    utils_py.write_text("""
from main import old_function, OldClass

def use_old():
    return old_function()

def use_class():
    obj = OldClass()
    return obj.old_method()
""".strip())

    # Another file with module import
    helper_py = tmp_path / "helper.py"
    helper_py.write_text("""
import main

def call_it():
    return main.old_function()
""".strip())

    return tmp_path


@pytest.fixture(autouse=True)
def clear_tier_cache():
    """Clear tier detection cache before each test."""
    from code_scalpel.licensing import config_loader, jwt_validator

    jwt_validator._LICENSE_VALIDATION_CACHE = None
    config_loader.clear_cache()
