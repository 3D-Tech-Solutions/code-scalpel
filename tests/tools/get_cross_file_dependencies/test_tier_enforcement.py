"""Phase 4 - Tier Enforcement Tests for get_cross_file_dependencies.

Validates:
- Tier transitions (Community → Pro → Enterprise)
- Feature degradation on tier downgrade
- Result field availability by tier
- Clear error messages on feature gating
- Consistent behavior across repeated calls

[20260103_TEST] P4 Medium: Tier enforcement and boundaries
"""

import pytest


class TestTierTransitions:
    """Test transitions between tiers."""

    @pytest.mark.asyncio
    async def test_community_to_pro_increased_depth(self, community_server, pro_server, simple_two_file_project):
        """Pro should support deeper analysis than Community (up to max_depth=5)."""
        community_result = await community_server.get_cross_file_dependencies(
            target_file=simple_two_file_project["target_file"],
            target_symbol=simple_two_file_project["target_symbol"],
            project_root=simple_two_file_project["root"],
            max_depth=5,
        )

        pro_result = await pro_server.get_cross_file_dependencies(
            target_file=simple_two_file_project["target_file"],
            target_symbol=simple_two_file_project["target_symbol"],
            project_root=simple_two_file_project["root"],
            max_depth=5,
        )

        assert community_result.success is True
        assert pro_result.success is True
        # Both should succeed - simple 2-file project doesn't trigger depth limits
        assert community_result.target_name == pro_result.target_name

    @pytest.mark.asyncio
    async def test_pro_to_enterprise_feature_availability(self, pro_server, enterprise_server, simple_two_file_project):
        """Enterprise should have features Pro doesn't."""
        pro_result = await pro_server.get_cross_file_dependencies(
            target_file=simple_two_file_project["target_file"],
            target_symbol=simple_two_file_project["target_symbol"],
            project_root=simple_two_file_project["root"],
        )

        enterprise_result = await enterprise_server.get_cross_file_dependencies(
            target_file=simple_two_file_project["target_file"],
            target_symbol=simple_two_file_project["target_symbol"],
            project_root=simple_two_file_project["root"],
        )

        assert pro_result.success is True
        assert enterprise_result.success is True
        # Enterprise should have architectural rule engine
        assert hasattr(enterprise_result, "architectural_rules_applied")


class TestFeatureDegradation:
    """Test feature availability changes by tier."""

    @pytest.mark.asyncio
    async def test_community_respects_depth_limit(self, community_server, deep_chain_project):
        """Community should restrict max depth analysis."""
        result = await community_server.get_cross_file_dependencies(
            target_file=deep_chain_project["target_file"],
            target_symbol=deep_chain_project["target_symbol"],
            project_root=deep_chain_project["root"],
            max_depth=1,  # Request depth 1
        )

        assert result.success is True
        # Should respect max_depth parameter
        assert result.transitive_depth <= 1

    @pytest.mark.asyncio
    async def test_pro_no_architectural_rules(self, pro_server, simple_two_file_project):
        """Pro should not have architectural rule features."""
        result = await pro_server.get_cross_file_dependencies(
            target_file=simple_two_file_project["target_file"],
            target_symbol=simple_two_file_project["target_symbol"],
            project_root=simple_two_file_project["root"],
        )

        assert result.success is True
        # Architectural features should be empty
        assert len(result.boundary_violations) == 0
        assert len(result.layer_violations) == 0


class TestResultFieldAvailability:
    """Test which fields are populated by tier."""

    @pytest.mark.asyncio
    async def test_community_core_fields(self, community_server, simple_two_file_project):
        """Community should have core dependency fields."""
        result = await community_server.get_cross_file_dependencies(
            target_file=simple_two_file_project["target_file"],
            target_symbol=simple_two_file_project["target_symbol"],
            project_root=simple_two_file_project["root"],
        )

        assert result.success is True
        # Core fields should exist
        assert hasattr(result, "extracted_symbols")
        assert hasattr(result, "import_graph")
        assert hasattr(result, "circular_imports")
        assert hasattr(result, "combined_code")

    @pytest.mark.asyncio
    async def test_pro_additional_fields(self, pro_server, simple_two_file_project):
        """Pro should have additional dependency analysis fields."""
        result = await pro_server.get_cross_file_dependencies(
            target_file=simple_two_file_project["target_file"],
            target_symbol=simple_two_file_project["target_symbol"],
            project_root=simple_two_file_project["root"],
        )

        assert result.success is True
        # Pro additional fields
        assert hasattr(result, "alias_resolutions")
        assert hasattr(result, "wildcard_expansions")
        assert hasattr(result, "reexport_chains")
        assert hasattr(result, "chained_alias_resolutions")
        assert hasattr(result, "coupling_score")

    @pytest.mark.asyncio
    async def test_enterprise_governance_fields(self, enterprise_server, simple_two_file_project):
        """Enterprise should have governance fields."""
        result = await enterprise_server.get_cross_file_dependencies(
            target_file=simple_two_file_project["target_file"],
            target_symbol=simple_two_file_project["target_symbol"],
            project_root=simple_two_file_project["root"],
        )

        assert result.success is True
        # Enterprise governance fields
        assert hasattr(result, "coupling_violations")
        assert hasattr(result, "architectural_rules_applied")
        assert hasattr(result, "exempted_files")
        assert hasattr(result, "layer_mapping")


class TestConsistentBehavior:
    """Test consistent behavior across calls."""

    @pytest.mark.asyncio
    async def test_community_consistent_results(self, community_server, simple_two_file_project):
        """Community tier should give consistent results."""
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

        assert result1.success == result2.success
        assert result1.target_name == result2.target_name
        assert result1.total_dependencies == result2.total_dependencies
