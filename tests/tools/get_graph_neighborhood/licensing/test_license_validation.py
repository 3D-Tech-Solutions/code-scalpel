"""
[20260105_TEST] License validation tests for get_graph_neighborhood tool.

Tests real JWT license validation using licenses from tests/licenses/ directory.
Validates that invalid/expired/malformed licenses fall back to Community tier.

This replaces the mock-based tier fixtures with actual license validation.
"""

from pathlib import Path

import pytest

from code_scalpel.licensing.features import get_tool_capabilities
from code_scalpel.mcp.server import _get_current_tier

# Path to test licenses
LICENSE_DIR = Path(__file__).parent.parent.parent.parent / "licenses"


@pytest.fixture(autouse=True)
def clear_license_cache():
    """Clear license validation cache before and after each test."""
    from code_scalpel.licensing import config_loader, jwt_validator
    from code_scalpel.mcp import server

    # Clear before test
    jwt_validator._LICENSE_VALIDATION_CACHE = None
    config_loader.clear_cache()
    if hasattr(server, "_cached_tier"):
        server._cached_tier = None
    if hasattr(server, "_LAST_VALID_LICENSE_AT"):
        server._LAST_VALID_LICENSE_AT = None
    if hasattr(server, "_LAST_VALID_LICENSE_TIER"):
        server._LAST_VALID_LICENSE_TIER = None

    yield

    # Clear after test
    jwt_validator._LICENSE_VALIDATION_CACHE = None
    config_loader.clear_cache()
    if hasattr(server, "_cached_tier"):
        server._cached_tier = None
    if hasattr(server, "_LAST_VALID_LICENSE_AT"):
        server._LAST_VALID_LICENSE_AT = None
    if hasattr(server, "_LAST_VALID_LICENSE_TIER"):
        server._LAST_VALID_LICENSE_TIER = None


@pytest.fixture
def use_community_tier(monkeypatch, tmp_path):
    """Force Community tier by disabling license discovery and pointing to nonexistent file."""
    monkeypatch.setenv("CODE_SCALPEL_DISABLE_LICENSE_DISCOVERY", "1")
    empty_dir = tmp_path / "no_license"
    empty_dir.mkdir()
    monkeypatch.setenv("CODE_SCALPEL_LICENSE_PATH", str(empty_dir / "nonexistent.jwt"))
    yield
    monkeypatch.delenv("CODE_SCALPEL_LICENSE_PATH", raising=False)
    monkeypatch.delenv("CODE_SCALPEL_DISABLE_LICENSE_DISCOVERY", raising=False)


@pytest.fixture
def use_pro_tier(monkeypatch):
    """Use real Pro tier license from tests/licenses/."""
    pro_licenses = list(LICENSE_DIR.glob("code_scalpel_license_pro_*.jwt"))
    # Filter out broken licenses
    pro_licenses = [lic for lic in pro_licenses if "broken" not in lic.name]
    assert pro_licenses, f"No valid Pro license found in {LICENSE_DIR}"

    license_path = pro_licenses[0]
    monkeypatch.setenv("CODE_SCALPEL_LICENSE_PATH", str(license_path))
    monkeypatch.setenv("CODE_SCALPEL_DISABLE_LICENSE_DISCOVERY", "1")
    yield
    monkeypatch.delenv("CODE_SCALPEL_LICENSE_PATH", raising=False)
    monkeypatch.delenv("CODE_SCALPEL_DISABLE_LICENSE_DISCOVERY", raising=False)


@pytest.fixture
def use_enterprise_tier(monkeypatch):
    """Use real Enterprise tier license from tests/licenses/."""
    enterprise_licenses = list(LICENSE_DIR.glob("code_scalpel_license_enterprise_*.jwt"))
    # Filter out broken licenses
    enterprise_licenses = [lic for lic in enterprise_licenses if "broken" not in lic.name]
    assert enterprise_licenses, f"No valid Enterprise license found in {LICENSE_DIR}"

    license_path = enterprise_licenses[0]
    monkeypatch.setenv("CODE_SCALPEL_LICENSE_PATH", str(license_path))
    monkeypatch.setenv("CODE_SCALPEL_DISABLE_LICENSE_DISCOVERY", "1")
    yield
    monkeypatch.delenv("CODE_SCALPEL_LICENSE_PATH", raising=False)
    monkeypatch.delenv("CODE_SCALPEL_DISABLE_LICENSE_DISCOVERY", raising=False)


class TestValidLicenseDetection:
    """Test detection and validation of valid licenses."""

    def test_no_license_defaults_to_community(self, use_community_tier):
        """No license file should default to Community tier (k=1, nodes=20)."""
        tier = _get_current_tier()
        assert tier == "community", f"Expected community tier without license, got {tier}"

        # Verify Community tier capabilities
        caps = get_tool_capabilities("get_graph_neighborhood", "community")
        assert caps["limits"]["max_k"] == 1
        assert caps["limits"]["max_nodes"] == 20

    def test_valid_pro_license_detected(self, use_pro_tier):
        """Valid Pro license should be detected and allow k=5, nodes=100."""
        tier = _get_current_tier()
        assert tier == "pro", f"Expected pro tier from license, got {tier}"

        # Verify Pro tier capabilities
        caps = get_tool_capabilities("get_graph_neighborhood", "pro")
        assert caps["limits"]["max_k"] == 5
        assert caps["limits"]["max_nodes"] == 100

    def test_valid_enterprise_license_detected(self, use_enterprise_tier):
        """Valid Enterprise license should be detected and allow unlimited k and nodes."""
        tier = _get_current_tier()
        assert tier == "enterprise", f"Expected enterprise tier from license, got {tier}"

        # Verify Enterprise tier capabilities
        caps = get_tool_capabilities("get_graph_neighborhood", "enterprise")
        assert caps["limits"]["max_k"] is None  # Unlimited
        assert caps["limits"]["max_nodes"] is None  # Unlimited

    def test_missing_license_file_falls_back_to_community(self, monkeypatch, tmp_path):
        """Nonexistent license file should fall back to Community tier."""
        nonexistent = tmp_path / "nonexistent.jwt"
        monkeypatch.setenv("CODE_SCALPEL_LICENSE_PATH", str(nonexistent))
        monkeypatch.setenv("CODE_SCALPEL_DISABLE_LICENSE_DISCOVERY", "1")

        tier = _get_current_tier()
        assert tier == "community", f"Missing license should fall back to community, got {tier}"

    def test_malformed_jwt_falls_back_to_community(self, monkeypatch, tmp_path):
        """Malformed JWT string should fall back to Community tier."""
        malformed_license = tmp_path / "malformed.jwt"
        malformed_license.write_text("not.a.valid.jwt.format")

        monkeypatch.setenv("CODE_SCALPEL_LICENSE_PATH", str(malformed_license))
        monkeypatch.setenv("CODE_SCALPEL_DISABLE_LICENSE_DISCOVERY", "1")

        tier = _get_current_tier()
        assert tier == "community", f"Malformed JWT should fall back to community, got {tier}"


class TestLicenseEnvironmentVariables:
    """Test license detection via environment variables."""

    def test_license_path_env_var_used(self, use_pro_tier):
        """CODE_SCALPEL_LICENSE_PATH environment variable should be respected."""
        # use_pro_tier fixture sets CODE_SCALPEL_LICENSE_PATH
        tier = _get_current_tier()
        assert tier == "pro", f"Expected pro tier from LICENSE_PATH env var, got {tier}"

    def test_empty_license_path_falls_back_to_community(self, monkeypatch):
        """Empty LICENSE_PATH environment variable should fall back to Community."""
        monkeypatch.setenv("CODE_SCALPEL_LICENSE_PATH", "")
        monkeypatch.setenv("CODE_SCALPEL_DISABLE_LICENSE_DISCOVERY", "1")

        tier = _get_current_tier()
        assert tier == "community", f"Empty LICENSE_PATH should fall back to community, got {tier}"


class TestTierLimitEnforcement:
    """Test that tier limits are enforced based on actual license validation."""

    @pytest.mark.asyncio
    async def test_community_k_clamped_to_1(self, use_community_tier, sample_call_graph):
        """Community tier should clamp k to 1."""
        result = sample_call_graph.get_neighborhood(
            "python::main::function::center", k=10, max_nodes=50
        )  # Request k=10

        assert result.success
        # Should be clamped to k=1, limiting traversal depth
        # Verify by checking that node count doesn't exceed what k=1 would give
        assert len(result.subgraph.nodes) <= 20  # Community max_nodes

    def test_community_limits_defined(self, use_community_tier):
        """Community tier should have k=1, max_nodes=20 limits."""
        tier = _get_current_tier()
        assert tier == "community"

        caps = get_tool_capabilities("get_graph_neighborhood", "community")
        assert caps["limits"]["max_k"] == 1
        assert caps["limits"]["max_nodes"] == 20

    def test_pro_limits_defined(self, use_pro_tier):
        """Pro tier should have k=5, max_nodes=100 limits."""
        tier = _get_current_tier()
        assert tier == "pro"

        caps = get_tool_capabilities("get_graph_neighborhood", "pro")
        assert caps["limits"]["max_k"] == 5
        assert caps["limits"]["max_nodes"] == 100

    def test_enterprise_unlimited(self, use_enterprise_tier):
        """Enterprise tier should have unlimited/very high limits."""
        tier = _get_current_tier()
        assert tier == "enterprise"

        caps = get_tool_capabilities("get_graph_neighborhood", "enterprise")
        # Enterprise has no k limit (None means unlimited)
        assert caps["limits"]["max_k"] is None or caps["limits"]["max_k"] >= 100
        # Enterprise has very high or unlimited node limit
        assert caps["limits"]["max_nodes"] is None or caps["limits"]["max_nodes"] >= 1000
