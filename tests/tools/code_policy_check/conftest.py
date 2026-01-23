"""Fixtures for code_policy_check tests."""

import pytest

from tests.utils.tier_setup import activate_tier, clear_tier_caches


@pytest.fixture(autouse=True)
def clear_tier_cache():
    """Clear tier detection cache before and after each test."""
    clear_tier_caches()
    yield
    clear_tier_caches()


@pytest.fixture
def pro_tier():
    """Fixture that sets up Pro tier for testing."""
    clear_tier_caches()
    license_path = activate_tier("pro", skip_if_missing=False)
    try:
        yield {
            "tier": "pro",
            "license_path": license_path,
            "is_mocked": license_path is None,
        }
    finally:
        clear_tier_caches()


@pytest.fixture
def enterprise_tier():
    """Fixture that sets up Enterprise tier for testing."""
    clear_tier_caches()
    license_path = activate_tier("enterprise", skip_if_missing=False)
    try:
        yield {
            "tier": "enterprise",
            "license_path": license_path,
            "is_mocked": license_path is None,
        }
    finally:
        clear_tier_caches()


@pytest.fixture
def community_tier():
    """Fixture that sets up Community tier for testing."""
    clear_tier_caches()
    activate_tier("community")
    try:
        yield {"tier": "community", "license_path": None, "is_mocked": False}
    finally:
        clear_tier_caches()
