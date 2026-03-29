"""
Tests for Phase 2 testing framework adapters and assertions.

Validates that:
- TierAdapter correctly reports tool availability
- Assertions work with all tiers
- Assertions fail appropriately
"""

import pytest

from code_scalpel.testing import (
    TierAdapter,
    assert_capability_present,
    assert_limit_value,
    assert_tool_available,
    assert_tool_count,
    assert_tool_unavailable,
)


class TestTierAdapter:
    """Test TierAdapter functionality."""

    def test_create_community_adapter(self):
        """Can create adapter for community tier."""
        adapter = TierAdapter("community")
        assert adapter.get_tier() == "community"

    def test_create_pro_adapter(self):
        """Can create adapter for pro tier."""
        adapter = TierAdapter("pro")
        assert adapter.get_tier() == "pro"

    def test_create_enterprise_adapter(self):
        """Can create adapter for enterprise tier."""
        adapter = TierAdapter("enterprise")
        assert adapter.get_tier() == "enterprise"

    def test_invalid_tier_raises(self):
        """Invalid tier raises ValueError."""
        with pytest.raises(ValueError, match="Invalid tier"):
            TierAdapter("invalid")  # type: ignore[arg-type]

    def test_community_has_all_tools(self):
        """Community tier has all 23 tools available."""
        adapter = TierAdapter("community")
        available = adapter.get_available_tools()
        assert len(available) == 23

    def test_pro_has_all_tools(self):
        """Pro tier has all 23 tools available (limits/capabilities differ)."""
        pro = TierAdapter("pro")
        pro_available = len(pro.get_available_tools())
        assert pro_available == 23

    def test_enterprise_has_all_tools(self):
        """Enterprise tier has all 23 tools available (limits/capabilities differ)."""
        enterprise = TierAdapter("enterprise")
        available = enterprise.get_available_tools()
        assert len(available) == 23

    def test_tool_available_true(self):
        """tool_available returns True for available tools."""
        adapter = TierAdapter("community")
        assert adapter.tool_available("analyze_code")

    def test_tool_available_all_tiers_method(self):
        """All tools available at all tiers."""
        for tier in ["community", "pro", "enterprise"]:
            adapter = TierAdapter(tier)
            assert adapter.tool_available("get_file_context")

    def test_get_available_tools(self):
        """get_available_tools returns correct set."""
        adapter = TierAdapter("pro")
        available = adapter.get_available_tools()

        assert "analyze_code" in available
        assert "get_file_context" in available

    def test_get_unavailable_tools(self):
        """get_unavailable_tools returns empty set (all tools available)."""
        adapter = TierAdapter("enterprise")
        unavailable = adapter.get_unavailable_tools()
        assert len(unavailable) == 0  # All 23 tools available

    def test_get_tool_limits(self):
        """get_tool_limits returns tool limits."""
        adapter = TierAdapter("community")
        limits = adapter.get_tool_limits("analyze_code")

        assert isinstance(limits, dict)
        assert "max_file_size_mb" in limits

    def test_assert_tool_available_passes(self):
        """assert_tool_available passes for available tools."""
        adapter = TierAdapter("community")
        adapter.assert_tool_available("analyze_code")  # Should not raise

    def test_assert_tool_available_succeeds_all_tiers(self):
        """assert_tool_available succeeds for all tools at all tiers."""
        for tier in ["community", "pro", "enterprise"]:
            adapter = TierAdapter(tier)
            adapter.assert_tool_available("get_file_context")  # Should not raise

    def test_assert_tool_unavailable_fails_when_available(self):
        """assert_tool_unavailable fails when tool is available."""
        adapter = TierAdapter("enterprise")
        with pytest.raises(AssertionError, match="is available"):
            adapter.assert_tool_unavailable(
                "get_file_context"
            )  # All tools available now

    def test_assert_tool_unavailable_fails(self):
        """assert_tool_unavailable fails for available tools."""
        adapter = TierAdapter("community")

        with pytest.raises(AssertionError, match="is available"):
            adapter.assert_tool_unavailable("analyze_code")


class TestAssertToolAvailable:
    """Test assert_tool_available function."""

    def test_tool_available_community(self):
        """Tool available in community tier."""
        assert_tool_available("analyze_code", "community")  # Should not raise

    def test_tool_available_pro(self):
        """Tool available in pro tier."""
        assert_tool_available("analyze_code", "pro")  # Should not raise

    def test_tool_available_all_tiers_function(self):
        """All tools available at all tiers via function."""
        for tier in ["community", "pro", "enterprise"]:
            assert_tool_available("get_file_context", tier)  # Should not raise

    def test_default_tier_is_community(self):
        """Default tier is community."""
        assert_tool_available("analyze_code")  # Should not raise


class TestAssertToolUnavailable:
    """Test assert_tool_unavailable function."""

    def test_tool_unavailable_raises_when_available(self):
        """Tool unavailable assertion fails when tool is available."""
        with pytest.raises(AssertionError, match="is available"):
            assert_tool_unavailable(
                "get_file_context", "enterprise"
            )  # All tools available

    def test_tool_not_locked_raises(self):
        """Available tool raises AssertionError."""
        with pytest.raises(AssertionError, match="is available"):
            assert_tool_unavailable("analyze_code", "community")


class TestAssertLimitValue:
    """Test assert_limit_value function."""

    def test_limit_matches(self):
        """assert_limit_value passes when limit matches."""
        assert_limit_value("analyze_code", "max_file_size_mb", 1, "community")

    def test_limit_mismatch_raises(self):
        """assert_limit_value raises on mismatch."""
        with pytest.raises(AssertionError, match="is 1"):
            assert_limit_value("analyze_code", "max_file_size_mb", 999, "community")


class TestAssertCapabilityPresent:
    """Test assert_capability_present function."""

    # Note: Capability structure in TOOL_CAPABILITIES may vary
    # Skipping detailed capability tests in favor of integration tests

    def test_capability_missing_raises(self):
        """Missing capability raises AssertionError."""
        with pytest.raises(AssertionError, match="not present"):
            assert_capability_present(
                "analyze_code", "nonexistent_capability", "community"
            )


class TestAssertToolCount:
    """Test assert_tool_count function."""

    def test_community_has_23_tools(self):
        """Community tier has 23 tools."""
        assert_tool_count("community", 23)  # Should not raise

    def test_pro_has_23_tools(self):
        """Pro tier has all 23 tools."""
        assert_tool_count("pro", 23)  # Should not raise

    def test_enterprise_has_23_tools(self):
        """Enterprise tier has all 23 tools."""
        assert_tool_count("enterprise", 23)  # Should not raise

    def test_wrong_count_raises(self):
        """Wrong tool count raises AssertionError."""
        with pytest.raises(AssertionError, match="has.*tools"):
            assert_tool_count("community", 10)


class TestAdapterIntegration:
    """Integration tests for adapters."""

    def test_run_test_for_all_tiers(self):
        """Can check tool availability across all tiers."""
        from code_scalpel.testing import TierAdapterFactory

        adapters = TierAdapterFactory.create_for_all_tiers()

        assert len(adapters) == 3
        assert adapters[0].get_tier() == "community"
        assert adapters[1].get_tier() == "pro"
        assert adapters[2].get_tier() == "enterprise"

    def test_run_test_for_specific_tiers(self):
        """Can create adapters for specific tiers."""
        from code_scalpel.testing import TierAdapterFactory

        adapters = TierAdapterFactory.create_for_tiers("pro", "enterprise")

        assert len(adapters) == 2
        assert adapters[0].get_tier() == "pro"
        assert adapters[1].get_tier() == "enterprise"

    def test_tool_available_different_limits_per_tier(self):
        """All tools available but with different limits per tier."""
        pro_adapter = TierAdapter("pro")
        enterprise_adapter = TierAdapter("enterprise")

        # All tools available at all tiers (limits/capabilities differ)
        assert pro_adapter.tool_available("get_file_context")
        assert enterprise_adapter.tool_available("get_file_context")

    def test_tool_available_all_tiers(self):
        """Some tools available in all tiers."""
        community = TierAdapter("community")
        pro = TierAdapter("pro")
        enterprise = TierAdapter("enterprise")

        # analyze_code should be available in all tiers
        assert community.tool_available("analyze_code")
        assert pro.tool_available("analyze_code")
        assert enterprise.tool_available("analyze_code")
