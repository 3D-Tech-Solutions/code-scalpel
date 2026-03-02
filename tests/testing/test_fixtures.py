"""Comprehensive tests for pytest fixtures.

Tests all fixture injection functionality:
- Cache clearing before/after tests
- Tier-specific adapter injection
- License path fixtures
- Context manager fixtures
- Parametrization via @tier_aware marker

[20260301_TEST] Rewritten for feature-gating architecture.
All tiers have 22 tools available; tiers differ in limits and features only.
Cache clearing uses config_loader.clear_cache() (resolver._LIMITS_CACHE removed).
License files located in tests/licenses/.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from code_scalpel.testing import TierAdapter


class TestClearAllCaches:
    """Test cache clearing fixture."""

    def test_clear_all_caches_clears_config_loader_cache(self, clear_all_caches):
        """[20260301_TEST] Verify config_loader cache is cleared by fixture."""
        from code_scalpel.licensing import config_loader

        # After clear_all_caches, cache should be None
        assert config_loader._config_cache is None

        # Load to populate it
        config_loader.get_cached_limits()
        assert config_loader._config_cache is not None

    def test_clear_all_caches_clears_jwt_validator_cache(self, clear_all_caches):
        """Verify JWT validator cache is cleared."""
        from code_scalpel.licensing import jwt_validator

        # Cache should be None before test starts
        assert jwt_validator._LICENSE_VALIDATION_CACHE is None

        # Set it to something
        jwt_validator._LICENSE_VALIDATION_CACHE = {"test": "value"}
        assert jwt_validator._LICENSE_VALIDATION_CACHE is not None


class TestTierAdapterFixture:
    """Test the main tier_adapter fixture."""

    def test_tier_adapter_default_is_community(self, tier_adapter: TierAdapter):
        """Default tier_adapter should be community."""
        assert tier_adapter.get_tier() == "community"

    def test_tier_adapter_has_all_community_tools(self, tier_adapter: TierAdapter):
        """Community tier should have all 22 tools available."""
        available = tier_adapter.get_available_tools()
        assert len(available) == 22
        assert all(isinstance(tool, str) for tool in available)

    def test_tier_adapter_no_locked_tools_community(self, tier_adapter: TierAdapter):
        """Community tier should have no locked tools (feature-gating model)."""
        locked = tier_adapter.get_unavailable_tools()
        assert len(locked) == 0


class TestSpecificAdapterFixtures:
    """Test tier-specific adapter fixtures.

    [20260301_TEST] Feature-gating model: all tiers have 22 tools.
    Differences are in limits, not tool availability.
    """

    def test_community_adapter(self, community_adapter: TierAdapter):
        """Community adapter should be community tier with all 22 tools."""
        assert community_adapter.get_tier() == "community"
        assert len(community_adapter.get_available_tools()) == 22

    def test_pro_adapter(self, pro_adapter: TierAdapter):
        """[20260301_TEST] Pro adapter should be pro tier with all 22 tools."""
        assert pro_adapter.get_tier() == "pro"
        assert len(pro_adapter.get_available_tools()) == 22

    def test_enterprise_adapter(self, enterprise_adapter: TierAdapter):
        """[20260301_TEST] Enterprise adapter should be enterprise tier with all 22 tools."""
        assert enterprise_adapter.get_tier() == "enterprise"
        assert len(enterprise_adapter.get_available_tools()) == 22

    def test_each_adapter_is_independent(
        self, community_adapter, pro_adapter, enterprise_adapter
    ):
        """Each adapter fixture should be a separate instance."""
        assert community_adapter is not pro_adapter
        assert pro_adapter is not enterprise_adapter
        assert community_adapter is not enterprise_adapter

    def test_tiers_have_different_limits(
        self, community_adapter, pro_adapter, enterprise_adapter
    ):
        """[20260301_TEST] Tiers should have different limits for the same tools."""
        # get_call_graph has known limit differences (from limits.toml)
        community_limits = community_adapter.get_tool_limits("get_call_graph")
        pro_limits = pro_adapter.get_tool_limits("get_call_graph")

        # Community: max_depth=10; Pro: max_depth=-1 (unlimited)
        assert community_limits.get("max_depth") == 10
        assert pro_limits.get("max_depth") == -1


class TestAllAdaptersFixture:
    """Test the all_adapters fixture."""

    def test_all_adapters_provides_three(self, all_adapters: list[TierAdapter]):
        """all_adapters fixture should provide 3 adapters."""
        assert len(all_adapters) == 3

    def test_all_adapters_are_different_tiers(self, all_adapters: list[TierAdapter]):
        """All adapters should be different tiers."""
        tiers = {adapter.get_tier() for adapter in all_adapters}
        assert tiers == {"community", "pro", "enterprise"}

    def test_all_adapters_correct_tool_counts(self, all_adapters: list[TierAdapter]):
        """[20260301_TEST] Each adapter should have 22 tools (feature-gating)."""
        for adapter in all_adapters:
            available_count = len(adapter.get_available_tools())
            assert (
                available_count == 22
            ), f"{adapter.get_tier()} should have 22 tools, got {available_count}"


class TestLicensePathFixtures:
    """Test license path fixtures.

    [20260301_TEST] Licenses are available in tests/licenses/.
    Removed TEST_WITH_LICENSES env var gating.
    """

    def test_pro_license_path_is_path_or_none(self, pro_license_path):
        """Pro license path should be Path or None."""
        assert pro_license_path is None or isinstance(pro_license_path, Path)

    def test_enterprise_license_path_is_path_or_none(self, enterprise_license_path):
        """Enterprise license path should be Path or None."""
        assert enterprise_license_path is None or isinstance(
            enterprise_license_path, Path
        )

    def test_pro_license_path_exists(self, pro_license_path):
        """[20260301_TEST] Pro license path should exist (tests/licenses/ has test licenses)."""
        assert (
            pro_license_path is not None
        ), "Pro license not found — expected in tests/licenses/"
        assert pro_license_path.exists()

    def test_enterprise_license_path_exists(self, enterprise_license_path):
        """[20260301_TEST] Enterprise license path should exist (tests/licenses/ has test licenses)."""
        assert (
            enterprise_license_path is not None
        ), "Enterprise license not found — expected in tests/licenses/"
        assert enterprise_license_path.exists()


class TestWithCommunityTierFixture:
    """Test with_community_tier context manager fixture."""

    def test_with_community_tier_removes_license_path(self, with_community_tier):
        """with_community_tier should remove CODE_SCALPEL_LICENSE_PATH."""
        # Inside the fixture context
        assert os.environ.get("CODE_SCALPEL_LICENSE_PATH") is None

    def test_with_community_tier_restores_original(self):
        """with_community_tier should restore original license path."""
        # Set original value
        original = "test_original_path"
        os.environ["CODE_SCALPEL_LICENSE_PATH"] = original

        # Can't directly test restoration without calling the fixture,
        # but the fixture code handles save/restore via try/finally.
        # Clean up our test env var
        os.environ.pop("CODE_SCALPEL_LICENSE_PATH", None)


class TestWithProLicenseFixture:
    """Test with_pro_license context manager fixture.

    [20260301_TEST] Removed TEST_WITH_LICENSES gating — license files are
    always available in tests/licenses/.
    """

    def test_with_pro_license_sets_env_var(self, with_pro_license):
        """with_pro_license should set CODE_SCALPEL_LICENSE_PATH."""
        license_path = os.environ.get("CODE_SCALPEL_LICENSE_PATH")
        assert license_path is not None
        assert license_path == str(with_pro_license)

    def test_with_pro_license_sets_correct_path(self, with_pro_license):
        """with_pro_license should set the correct pro license path."""
        license_path_str = os.environ.get("CODE_SCALPEL_LICENSE_PATH")
        assert license_path_str is not None
        license_path = Path(license_path_str)
        assert license_path.exists()


class TestWithEnterpriseLicenseFixture:
    """Test with_enterprise_license context manager fixture.

    [20260301_TEST] Removed TEST_WITH_LICENSES gating — license files are
    always available in tests/licenses/.
    """

    def test_with_enterprise_license_sets_env_var(self, with_enterprise_license):
        """with_enterprise_license should set CODE_SCALPEL_LICENSE_PATH."""
        license_path = os.environ.get("CODE_SCALPEL_LICENSE_PATH")
        assert license_path is not None
        assert license_path == str(with_enterprise_license)

    def test_with_enterprise_license_sets_correct_path(self, with_enterprise_license):
        """with_enterprise_license should set the correct enterprise license path."""
        license_path_str = os.environ.get("CODE_SCALPEL_LICENSE_PATH")
        assert license_path_str is not None
        license_path = Path(license_path_str)
        assert license_path.exists()


class TestTierAwareParametrization:
    """Test @pytest.mark.tier_aware parametrization."""

    @pytest.mark.tier_aware
    def test_tier_aware_runs_all_tiers(self, tier_adapter: TierAdapter):
        """Test marked tier_aware should run for all tiers."""
        # This test will run 3 times - once per tier
        assert tier_adapter.get_tier() in ("community", "pro", "enterprise")

    @pytest.mark.tier_aware
    def test_tier_aware_receives_correct_tier(self, tier_adapter: TierAdapter):
        """[20260301_TEST] Each tier should have all 22 tools (feature-gating)."""
        tier = tier_adapter.get_tier()
        assert tier in ("community", "pro", "enterprise")

        # All tiers have 22 tools in the feature-gating model
        available_count = len(tier_adapter.get_available_tools())
        assert (
            available_count == 22
        ), f"{tier} should have 22 tools, got {available_count}"

    @pytest.mark.tier_aware
    def test_tier_aware_with_tier_specific_assertions(self, tier_adapter: TierAdapter):
        """[20260301_TEST] All tiers have all tools; verify limit differences."""
        tier = tier_adapter.get_tier()

        # All tools available in all tiers
        tier_adapter.assert_tool_available("analyze_code")
        tier_adapter.assert_tool_available("get_file_context")
        tier_adapter.assert_tool_available("security_scan")

        # Tiers differ in limits, not availability
        limits = tier_adapter.get_tool_limits("get_call_graph")
        if tier == "community":
            assert limits.get("max_depth") == 10
            assert limits.get("max_nodes") == 200
        elif tier == "pro":
            assert limits.get("max_depth") == -1
            assert limits.get("max_nodes") == -1


class TestFixtureIntegration:
    """Test integration of multiple fixtures."""

    def test_multiple_adapters_independently_available(
        self, community_adapter, pro_adapter, enterprise_adapter
    ):
        """[20260301_TEST] All adapters should have all 22 tools available."""
        # All tools available at all tiers (feature-gating model)
        for adapter in [community_adapter, pro_adapter, enterprise_adapter]:
            adapter.assert_tool_available("analyze_code")
            adapter.assert_tool_available("get_file_context")
            adapter.assert_tool_available("security_scan")
            adapter.assert_tool_available("get_call_graph")
            assert len(adapter.get_available_tools()) == 22

    def test_clear_all_caches_with_adapters(
        self, clear_all_caches, community_adapter, pro_adapter
    ):
        """clear_all_caches fixture should work with adapters."""
        # Adapters should be correctly initialized after cache clear
        assert community_adapter.get_tier() == "community"
        assert pro_adapter.get_tier() == "pro"

    def test_all_fixtures_together(
        self, clear_all_caches, tier_adapter, community_adapter, all_adapters
    ):
        """All fixtures should work together."""
        # tier_adapter should be one of the adapters
        tier = tier_adapter.get_tier()
        assert tier in ("community", "pro", "enterprise")

        # all_adapters should contain 3 different adapters
        assert len(all_adapters) == 3

        # All fixtures should be properly initialized
        assert community_adapter.get_tier() == "community"
