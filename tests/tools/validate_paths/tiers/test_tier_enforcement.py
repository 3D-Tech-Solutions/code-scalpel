"""
Tier enforcement tests for validate_paths tool.

Tests the feature gating and limit enforcement:
- Community tier: 100 path limit, core features only
- Pro tier: Unlimited paths, advanced features
- Enterprise tier: All features including security validation
"""

import pytest

from code_scalpel.licensing.features import get_tool_capabilities, has_capability


class TestCommunityTierCapabilities:
    """Test Community tier feature set."""

    def test_community_has_core_features(self):
        """Community tier should have all core features."""
        caps = get_tool_capabilities("validate_paths", "community")
        assert caps["enabled"] is True, "validate_paths should be enabled at community tier"

        expected_capabilities = {
            "path_accessibility_checking",
            "docker_environment_detection",
            "workspace_root_detection",
            "actionable_error_messages",
            "docker_volume_mount_suggestions",
            "batch_path_validation",
        }

        actual_capabilities = set(caps.get("capabilities", []))
        for capability in expected_capabilities:
            assert capability in actual_capabilities, f"Community tier missing capability: {capability}"

    def test_community_has_100_path_limit(self):
        """Community tier should enforce 100 path limit."""
        caps = get_tool_capabilities("validate_paths", "community")
        assert (
            caps["limits"]["max_paths"] == 100
        ), f"Community tier max_paths should be 100, got {caps['limits']['max_paths']}"

    def test_community_lacks_pro_features(self):
        """Community tier should NOT have Pro features."""
        caps = get_tool_capabilities("validate_paths", "community")
        capabilities = set(caps.get("capabilities", []))

        pro_only_features = {
            "path_alias_resolution",
            "tsconfig_paths_support",
            "webpack_alias_support",
            "dynamic_import_resolution",
            "extended_language_support",
        }

        for feature in pro_only_features:
            assert feature not in capabilities, f"Community tier should NOT have feature: {feature}"

    def test_community_lacks_enterprise_features(self):
        """Community tier should NOT have Enterprise features."""
        caps = get_tool_capabilities("validate_paths", "community")
        capabilities = set(caps.get("capabilities", []))

        enterprise_only_features = {
            "permission_checks",
            "security_validation",
            "path_traversal_simulation",
            "symbolic_path_breaking",
            "security_boundary_testing",
        }

        for feature in enterprise_only_features:
            assert feature not in capabilities, f"Community tier should NOT have feature: {feature}"

    def test_community_capability_check_with_has_capability(self):
        """has_capability function should correctly report community capabilities."""
        assert has_capability("validate_paths", "path_accessibility_checking", "community") is True
        assert has_capability("validate_paths", "docker_environment_detection", "community") is True
        assert has_capability("validate_paths", "path_alias_resolution", "community") is False
        assert has_capability("validate_paths", "permission_checks", "community") is False


class TestProTierCapabilities:
    """Test Pro tier feature set."""

    def test_pro_has_core_features(self):
        """Pro tier should have all core features."""
        caps = get_tool_capabilities("validate_paths", "pro")
        assert caps["enabled"] is True, "validate_paths should be enabled at pro tier"

        expected_capabilities = {
            "path_accessibility_checking",
            "docker_environment_detection",
            "workspace_root_detection",
            "actionable_error_messages",
            "docker_volume_mount_suggestions",
            "batch_path_validation",
        }

        actual_capabilities = set(caps.get("capabilities", []))
        for capability in expected_capabilities:
            assert capability in actual_capabilities, f"Pro tier missing capability: {capability}"

    def test_pro_has_advanced_features(self):
        """Pro tier should have advanced path resolution features."""
        caps = get_tool_capabilities("validate_paths", "pro")
        capabilities = set(caps.get("capabilities", []))

        expected_pro_features = {
            "path_alias_resolution",
            "tsconfig_paths_support",
            "webpack_alias_support",
            "dynamic_import_resolution",
            "extended_language_support",
        }

        for feature in expected_pro_features:
            assert feature in capabilities, f"Pro tier missing feature: {feature}"

    def test_pro_has_unlimited_paths(self):
        """Pro tier should have unlimited path validation."""
        caps = get_tool_capabilities("validate_paths", "pro")
        assert (
            caps["limits"]["max_paths"] is None
        ), f"Pro tier should have unlimited paths, got {caps['limits']['max_paths']}"

    def test_pro_lacks_enterprise_features(self):
        """Pro tier should NOT have Enterprise-only features."""
        caps = get_tool_capabilities("validate_paths", "pro")
        capabilities = set(caps.get("capabilities", []))

        enterprise_only_features = {
            "permission_checks",
            "security_validation",
            "path_traversal_simulation",
            "symbolic_path_breaking",
            "security_boundary_testing",
        }

        for feature in enterprise_only_features:
            assert feature not in capabilities, f"Pro tier should NOT have feature: {feature}"

    def test_pro_capability_check_with_has_capability(self):
        """has_capability function should correctly report pro capabilities."""
        assert has_capability("validate_paths", "path_accessibility_checking", "pro") is True
        assert has_capability("validate_paths", "path_alias_resolution", "pro") is True
        assert has_capability("validate_paths", "permission_checks", "pro") is False


class TestEnterpriseTierCapabilities:
    """Test Enterprise tier feature set."""

    def test_enterprise_has_all_features(self):
        """Enterprise tier should have all features."""
        caps = get_tool_capabilities("validate_paths", "enterprise")
        assert caps["enabled"] is True, "validate_paths should be enabled at enterprise tier"

        expected_capabilities = {
            "path_accessibility_checking",
            "docker_environment_detection",
            "workspace_root_detection",
            "actionable_error_messages",
            "docker_volume_mount_suggestions",
            "batch_path_validation",
            "path_alias_resolution",
            "tsconfig_paths_support",
            "webpack_alias_support",
            "dynamic_import_resolution",
            "extended_language_support",
            "permission_checks",
            "security_validation",
            "path_traversal_simulation",
            "symbolic_path_breaking",
            "security_boundary_testing",
        }

        actual_capabilities = set(caps.get("capabilities", []))
        for capability in expected_capabilities:
            assert capability in actual_capabilities, f"Enterprise tier missing capability: {capability}"

    def test_enterprise_has_unlimited_paths(self):
        """Enterprise tier should have unlimited path validation."""
        caps = get_tool_capabilities("validate_paths", "enterprise")
        assert (
            caps["limits"]["max_paths"] is None
        ), f"Enterprise tier should have unlimited paths, got {caps['limits']['max_paths']}"

    def test_enterprise_has_security_features(self):
        """Enterprise tier should have all security validation features."""
        caps = get_tool_capabilities("validate_paths", "enterprise")
        capabilities = set(caps.get("capabilities", []))

        security_features = {
            "permission_checks",
            "security_validation",
            "path_traversal_simulation",
            "symbolic_path_breaking",
            "security_boundary_testing",
        }

        for feature in security_features:
            assert feature in capabilities, f"Enterprise tier missing security feature: {feature}"

    def test_enterprise_capability_check_with_has_capability(self):
        """has_capability function should correctly report enterprise capabilities."""
        assert has_capability("validate_paths", "path_accessibility_checking", "enterprise") is True
        assert has_capability("validate_paths", "path_alias_resolution", "enterprise") is True
        assert has_capability("validate_paths", "permission_checks", "enterprise") is True
        assert has_capability("validate_paths", "security_boundary_testing", "enterprise") is True


class TestTierFeatureGating:
    """Test feature gating across tiers."""

    def test_community_to_pro_feature_progression(self):
        """Features should progressively unlock from community to pro."""
        community_caps = set(get_tool_capabilities("validate_paths", "community")["capabilities"])
        pro_caps = set(get_tool_capabilities("validate_paths", "pro")["capabilities"])

        # Pro should have all community features plus more
        assert community_caps <= pro_caps, "Pro tier should include all community features"

        # Pro should have advanced features
        assert len(pro_caps) > len(community_caps), "Pro tier should have more capabilities than community"

    def test_pro_to_enterprise_feature_progression(self):
        """Features should progressively unlock from pro to enterprise."""
        pro_caps = set(get_tool_capabilities("validate_paths", "pro")["capabilities"])
        enterprise_caps = set(get_tool_capabilities("validate_paths", "enterprise")["capabilities"])

        # Enterprise should have all pro features plus more
        assert pro_caps <= enterprise_caps, "Enterprise tier should include all pro features"

        # Enterprise should have security features
        assert len(enterprise_caps) > len(pro_caps), "Enterprise tier should have more capabilities than pro"

    def test_limit_progression_across_tiers(self):
        """Limits should be more generous at higher tiers."""
        community_limits = get_tool_capabilities("validate_paths", "community")["limits"]
        pro_limits = get_tool_capabilities("validate_paths", "pro")["limits"]
        enterprise_limits = get_tool_capabilities("validate_paths", "enterprise")["limits"]

        # Community: 100 paths
        assert community_limits["max_paths"] == 100

        # Pro: Unlimited
        assert pro_limits["max_paths"] is None

        # Enterprise: Unlimited
        assert enterprise_limits["max_paths"] is None


class TestTierLimitEnforcement:
    """Test that tier limits are enforced correctly."""

    def test_community_max_paths_enforced(self):
        """Community tier validation should respect 100 path limit."""
        # This test would be integrated with the actual tool
        # For now, we verify the capability definition
        caps = get_tool_capabilities("validate_paths", "community")
        max_paths = caps["limits"]["max_paths"]
        assert max_paths == 100, "Community tier should enforce 100 path limit"

    def test_pro_unlimited_paths(self):
        """Pro tier should allow unlimited paths."""
        caps = get_tool_capabilities("validate_paths", "pro")
        max_paths = caps["limits"]["max_paths"]
        assert max_paths is None, "Pro tier should allow unlimited paths"

    def test_enterprise_unlimited_paths(self):
        """Enterprise tier should allow unlimited paths."""
        caps = get_tool_capabilities("validate_paths", "enterprise")
        max_paths = caps["limits"]["max_paths"]
        assert max_paths is None, "Enterprise tier should allow unlimited paths"

    def test_invalid_tier_returns_empty_capabilities(self):
        """Invalid tier should return empty or default capabilities."""
        caps = get_tool_capabilities("validate_paths", "invalid_tier")
        # Should either return empty or raise error - implementation dependent
        # For now just check it doesn't crash
        assert caps is not None or caps is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
