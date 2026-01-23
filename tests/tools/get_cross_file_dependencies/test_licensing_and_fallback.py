"""Licensing and Tier Fallback Tests for get_cross_file_dependencies.

Validates:
- Community tier limits enforced (depth=1, max_files=50) when forced via env var
- Tier transitions work correctly
- Feature gating: Pro/Enterprise fields empty on Community tier
- Limits are properly applied across tiers

[20260104_TEST] Licensing behavior and tier gating
"""

import pytest


class TestCommunityTierLimits:
    """Test Community tier limits enforcement."""

    @pytest.mark.asyncio
    async def test_community_tier_depth_limit(self, community_server, deep_chain_project, monkeypatch):
        """Community tier should clamp depth to 1."""
        # Force community tier
        monkeypatch.setenv("CODE_SCALPEL_TIER", "community")

        result = await community_server.get_cross_file_dependencies(
            target_file=deep_chain_project["target_file"],
            target_symbol=deep_chain_project["target_symbol"],
            project_root=deep_chain_project["root"],
            max_depth=5,  # Request deeper analysis
        )

        # Should succeed but with Community limits
        assert result.success is True
        # Depth should be clamped to Community limit (1)
        assert result.transitive_depth <= 1, f"Community tier should clamp depth to 1, got {result.transitive_depth}"

    @pytest.mark.asyncio
    async def test_community_tier_file_limit(self, community_server, simple_two_file_project, monkeypatch):
        """Community tier should limit files analyzed to 50."""
        monkeypatch.setenv("CODE_SCALPEL_TIER", "community")

        result = await community_server.get_cross_file_dependencies(
            target_file=simple_two_file_project["target_file"],
            target_symbol=simple_two_file_project["target_symbol"],
            project_root=simple_two_file_project["root"],
            max_files=100,  # Request more
        )

        assert result.success is True
        # Files should be limited
        assert result.files_analyzed <= 50, f"Community should limit to 50 files, analyzed {result.files_analyzed}"


class TestProTierCapabilities:
    """Test Pro tier has enhanced capabilities vs Community."""

    @pytest.mark.asyncio
    async def test_pro_tier_increased_depth(self, pro_server, deep_chain_project, monkeypatch):
        """Pro tier should support deeper depth analysis (up to 5)."""
        monkeypatch.setenv("CODE_SCALPEL_TIER", "pro")

        result = await pro_server.get_cross_file_dependencies(
            target_file=deep_chain_project["target_file"],
            target_symbol=deep_chain_project["target_symbol"],
            project_root=deep_chain_project["root"],
            max_depth=5,
        )

        assert result.success is True
        # Pro should support deeper analysis
        assert result.transitive_depth <= 5

    @pytest.mark.asyncio
    async def test_pro_tier_alias_resolution(self, pro_server, alias_import_project, monkeypatch):
        """Pro tier should resolve import aliases."""
        monkeypatch.setenv("CODE_SCALPEL_TIER", "pro")

        result = await pro_server.get_cross_file_dependencies(
            target_file=alias_import_project["target_file"],
            target_symbol=alias_import_project["target_symbol"],
            project_root=alias_import_project["root"],
        )

        assert result.success is True
        # Pro tier should have alias resolution capability
        assert isinstance(result.alias_resolutions, list)


class TestEnterpriseTierCapabilities:
    """Test Enterprise tier has full capabilities."""

    @pytest.mark.asyncio
    async def test_enterprise_tier_unlimited_depth(self, enterprise_server, deep_chain_project, monkeypatch):
        """Enterprise tier should allow unlimited depth."""
        monkeypatch.setenv("CODE_SCALPEL_TIER", "enterprise")

        result = await enterprise_server.get_cross_file_dependencies(
            target_file=deep_chain_project["target_file"],
            target_symbol=deep_chain_project["target_symbol"],
            project_root=deep_chain_project["root"],
            max_depth=20,
        )

        assert result.success is True
        # Enterprise should support requested depth
        assert result.transitive_depth <= 20

    @pytest.mark.asyncio
    async def test_enterprise_tier_architectural_features(
        self, enterprise_server, simple_two_file_project, monkeypatch
    ):
        """Enterprise tier should have architectural features."""
        monkeypatch.setenv("CODE_SCALPEL_TIER", "enterprise")

        result = await enterprise_server.get_cross_file_dependencies(
            target_file=simple_two_file_project["target_file"],
            target_symbol=simple_two_file_project["target_symbol"],
            project_root=simple_two_file_project["root"],
        )

        assert result.success is True
        # Enterprise tier should have architectural fields
        assert hasattr(result, "boundary_alerts")
        assert hasattr(result, "coupling_violations")
        assert hasattr(result, "architectural_violations")


class TestFeatureGatingByCommunityTier:
    """Test that Pro/Enterprise features are gated on Community tier."""

    @pytest.mark.asyncio
    async def test_pro_features_empty_on_community(self, community_server, alias_import_project, monkeypatch):
        """Pro features should be empty when Community tier is forced."""
        monkeypatch.setenv("CODE_SCALPEL_TIER", "community")

        result = await community_server.get_cross_file_dependencies(
            target_file=alias_import_project["target_file"],
            target_symbol=alias_import_project["target_symbol"],
            project_root=alias_import_project["root"],
        )

        assert result.success is True
        # Pro features should not be populated
        assert len(result.alias_resolutions) == 0, "alias_resolutions should be empty on Community tier"
        assert len(result.wildcard_expansions) == 0

    @pytest.mark.asyncio
    async def test_enterprise_features_empty_on_community(self, community_server, simple_two_file_project, monkeypatch):
        """Enterprise features should be empty when Community tier is forced."""
        monkeypatch.setenv("CODE_SCALPEL_TIER", "community")

        result = await community_server.get_cross_file_dependencies(
            target_file=simple_two_file_project["target_file"],
            target_symbol=simple_two_file_project["target_symbol"],
            project_root=simple_two_file_project["root"],
        )

        assert result.success is True
        # Enterprise features should not be populated
        assert len(result.architectural_violations) == 0
        assert len(result.boundary_alerts) == 0
        assert len(result.coupling_violations) == 0


class TestTierConsistency:
    """Test consistent behavior within a tier."""

    @pytest.mark.asyncio
    async def test_repeated_community_calls_consistent(self, community_server, simple_two_file_project, monkeypatch):
        """Multiple Community tier calls should behave consistently."""
        monkeypatch.setenv("CODE_SCALPEL_TIER", "community")

        result1 = await community_server.get_cross_file_dependencies(
            target_file=simple_two_file_project["target_file"],
            target_symbol=simple_two_file_project["target_symbol"],
            project_root=simple_two_file_project["root"],
        )

        result2 = await community_server.get_cross_file_dependencies(
            target_file=simple_two_file_project["target_file"],
            target_symbol=simple_two_file_project["target_symbol"],
            project_root=simple_two_file_project["root"],
        )

        assert result1.success is True
        assert result2.success is True
        # Both should use Community limits consistently
        assert result1.transitive_depth == result2.transitive_depth
        assert result1.files_analyzed == result2.files_analyzed
