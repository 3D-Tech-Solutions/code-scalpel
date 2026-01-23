"""Pytest fixtures for get_symbol_references tests.

[20260113_REFACTOR] Switched from monkeypatch-based tier mocking to using
actual test license files via CODE_SCALPEL_LICENSE_PATH. This is more reliable
and tests the real license validation path.

License files in tests/licenses/:
- community: No license file (disable discovery, point to non-existent path)
- pro: code_scalpel_license_pro_20260101_190345.jwt
- enterprise: code_scalpel_license_enterprise_20260101_190754.jwt
"""

from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

# Path to test licenses
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
TEST_LICENSES_DIR = PROJECT_ROOT / "tests" / "licenses"
PRO_LICENSE = TEST_LICENSES_DIR / "code_scalpel_license_pro_20260101_190345.jwt"
ENTERPRISE_LICENSE = TEST_LICENSES_DIR / "code_scalpel_license_enterprise_20260101_190754.jwt"
# Non-existent path to force Community tier (no valid license found)
NO_LICENSE = PROJECT_ROOT / "tests" / "licenses" / "nonexistent_license.jwt"


def _clear_license_caches():
    """Clear all license-related caches to ensure fresh tier detection."""
    # Clear JWT validation cache
    try:
        from code_scalpel.licensing import jwt_validator

        jwt_validator._LICENSE_VALIDATION_CACHE = None
    except (ImportError, AttributeError):
        pass

    # Clear config loader cache
    try:
        from code_scalpel.licensing.config_loader import clear_cache

        clear_cache()
    except (ImportError, AttributeError):
        pass

    # Reset server tier state
    try:
        import code_scalpel.mcp.tools.context as server

        server._LAST_VALID_LICENSE_AT = None
        server._LAST_VALID_LICENSE_TIER = "community"
        if hasattr(server, "_GOVERNANCE_VERIFY_CACHE"):
            server._GOVERNANCE_VERIFY_CACHE.clear()
    except (ImportError, AttributeError):
        pass


@pytest.fixture(autouse=True)
def reset_license_state():
    """[20260113_FIX] Clear license caches before and after each test.

    This ensures tests don't pollute each other with cached license state.
    """
    _clear_license_caches()
    yield
    _clear_license_caches()


@pytest.fixture
def make_project(tmp_path: Path) -> Callable[[dict[str, str]], Path]:
    """[20260104_TEST] Create a synthetic project tree with given files.

    Args:
        files: mapping of relative path -> file content.

    Returns:
        Path to the project root.
    """

    def _factory(files: dict[str, str]) -> Path:
        for rel, content in files.items():
            path = tmp_path / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        return tmp_path

    return _factory


@pytest.fixture
def community_license(monkeypatch: pytest.MonkeyPatch):
    """[20260113_TEST] Set up Community tier by pointing to non-existent license.

    Community tier is the default when no valid license is found.
    We explicitly disable discovery and point to a non-existent file.
    """
    _clear_license_caches()
    monkeypatch.setenv("CODE_SCALPEL_DISABLE_LICENSE_DISCOVERY", "1")
    monkeypatch.setenv("CODE_SCALPEL_LICENSE_PATH", str(NO_LICENSE))
    monkeypatch.delenv("CODE_SCALPEL_TIER", raising=False)
    yield {"tier": "community", "license_path": None}


@pytest.fixture
def pro_license(monkeypatch: pytest.MonkeyPatch):
    """[20260113_TEST] Set up Pro tier using actual Pro license file."""
    _clear_license_caches()
    monkeypatch.setenv("CODE_SCALPEL_LICENSE_PATH", str(PRO_LICENSE))
    monkeypatch.delenv("CODE_SCALPEL_TIER", raising=False)
    monkeypatch.delenv("CODE_SCALPEL_DISABLE_LICENSE_DISCOVERY", raising=False)
    yield {"tier": "pro", "license_path": PRO_LICENSE}


@pytest.fixture
def enterprise_license(monkeypatch: pytest.MonkeyPatch):
    """[20260113_TEST] Set up Enterprise tier using actual Enterprise license file."""
    _clear_license_caches()
    monkeypatch.setenv("CODE_SCALPEL_LICENSE_PATH", str(ENTERPRISE_LICENSE))
    monkeypatch.delenv("CODE_SCALPEL_TIER", raising=False)
    monkeypatch.delenv("CODE_SCALPEL_DISABLE_LICENSE_DISCOVERY", raising=False)
    yield {"tier": "enterprise", "license_path": ENTERPRISE_LICENSE}


# Legacy fixtures for backward compatibility
@pytest.fixture
def patch_tier(monkeypatch: pytest.MonkeyPatch) -> Callable[[str], None]:
    """[20260113_DEPRECATED] Legacy fixture - prefer community_license/pro_license/enterprise_license.

    Sets up tier using actual license files instead of env var hacks.
    """

    def _set(tier: str) -> None:
        # CRITICAL: Clear caches BEFORE setting env vars
        _clear_license_caches()

        if tier == "community":
            monkeypatch.setenv("CODE_SCALPEL_DISABLE_LICENSE_DISCOVERY", "1")
            monkeypatch.setenv("CODE_SCALPEL_LICENSE_PATH", str(NO_LICENSE))
        elif tier == "pro":
            monkeypatch.setenv("CODE_SCALPEL_LICENSE_PATH", str(PRO_LICENSE))
            monkeypatch.delenv("CODE_SCALPEL_DISABLE_LICENSE_DISCOVERY", raising=False)
        elif tier == "enterprise":
            monkeypatch.setenv("CODE_SCALPEL_LICENSE_PATH", str(ENTERPRISE_LICENSE))
            monkeypatch.delenv("CODE_SCALPEL_DISABLE_LICENSE_DISCOVERY", raising=False)
        monkeypatch.delenv("CODE_SCALPEL_TIER", raising=False)

        # Clear caches AGAIN after setting env vars to force fresh tier detection
        _clear_license_caches()

    return _set


@pytest.fixture
def patch_capabilities(
    monkeypatch: pytest.MonkeyPatch,
) -> Callable[[dict[str, Any]], None]:
    """[20260104_TEST] Override tool capabilities for deterministic tests."""

    def _set(mapping: dict[str, Any]) -> None:
        import code_scalpel.mcp.helpers.context_helpers as context_helpers

        def _caps(tool: str, tier: str) -> dict[str, Any]:
            return mapping

        monkeypatch.setattr(context_helpers, "get_tool_capabilities", _caps)

    return _set


@pytest.fixture
def patch_license_validator(monkeypatch: pytest.MonkeyPatch) -> Callable[[Any], None]:
    """[20260104_TEST] Stub JWTLicenseValidator.validate() for license scenarios."""

    def _set(fake_result: Any) -> None:
        import code_scalpel.licensing.jwt_validator as jwt_validator

        class _FakeValidator:
            def validate(self) -> Any:  # type: ignore[override]
                return fake_result

            def get_current_tier(self) -> str:
                if getattr(fake_result, "is_valid", False):
                    return getattr(fake_result, "tier", "community")
                return "community"

        monkeypatch.setattr(jwt_validator, "JWTLicenseValidator", _FakeValidator)

    return _set
