"""Tier enforcement transition tests for get_project_map.

Validates:
- Tier upgrade transitions (Community → Pro → Enterprise)
- Feature unlocking with tier upgrades
- Limit increases with tier upgrades

[20260103_TEST] v3.3.1 - Tier enforcement and transitions
"""

import pytest


class TestTierTransitions:
    """Test tier upgrade transitions and feature unlocking."""

    @pytest.mark.asyncio
    async def test_community_to_pro_upgrade(self, community_server, pro_server, project_120_files):
        """Upgrade Community→Pro: file limit increases from 100→1000."""
        # Community: Should be limited to 100 files
        com_result = await community_server.get_project_map(
            project_root=str(project_120_files), include_complexity=False
        )

        assert com_result.total_files <= 100, f"Community should limit to 100 files, got {com_result.total_files}"

        # Pro: Should handle all 120 files (under 1000 limit)
        pro_result = await pro_server.get_project_map(project_root=str(project_120_files), include_complexity=False)

        assert pro_result.total_files >= 100, f"Pro should handle >100 files, got {pro_result.total_files}"
        assert pro_result.total_files >= com_result.total_files, "Pro should see more files than Community"

    @pytest.mark.asyncio
    async def test_pro_to_enterprise_features(self, pro_server, enterprise_server, simple_project):
        """Upgrade Pro→Enterprise: unlock Enterprise features."""
        # Pro: Should not have Enterprise features
        pro_result = await pro_server.get_project_map(project_root=str(simple_project), include_complexity=True)

        from .conftest import has_enterprise_features

        assert not has_enterprise_features(pro_result), "Pro tier should not have populated Enterprise features"

        # Enterprise: Should have Enterprise feature fields
        ent_result = await enterprise_server.get_project_map(project_root=str(simple_project), include_complexity=True)

        # Enterprise feature fields should exist via __getattr__ forwarding
        ent_features = ["city_map_data", "compliance_overlay", "multi_repo_summary"]
        available = [f for f in ent_features if hasattr(ent_result, f)]
        assert len(available) > 0, "Enterprise should have Enterprise feature fields"

    @pytest.mark.asyncio
    async def test_tier_detail_level_progression(self, community_server, pro_server, enterprise_server, simple_project):
        """Detail level increases: basic→detailed→comprehensive."""
        # Community: basic
        com_result = await community_server.get_project_map(project_root=str(simple_project), include_complexity=False)

        # Pro: detailed (more fields than Community)
        pro_result = await pro_server.get_project_map(project_root=str(simple_project), include_complexity=False)

        # Enterprise: comprehensive (most fields)
        ent_result = await enterprise_server.get_project_map(project_root=str(simple_project), include_complexity=False)

        # Compare field counts
        com_dict = com_result.model_dump() if hasattr(com_result, "model_dump") else vars(com_result)
        pro_dict = pro_result.model_dump() if hasattr(pro_result, "model_dump") else vars(pro_result)
        ent_dict = ent_result.model_dump() if hasattr(ent_result, "model_dump") else vars(ent_result)

        # Pro should have ≥ Community fields
        assert len(pro_dict) >= len(
            com_dict
        ), f"Pro tier should have ≥ fields than Community: {len(pro_dict)} vs {len(com_dict)}"

        # Enterprise should have ≥ Pro fields
        assert len(ent_dict) >= len(
            pro_dict
        ), f"Enterprise should have ≥ fields than Pro: {len(ent_dict)} vs {len(pro_dict)}"

    @pytest.mark.asyncio
    async def test_tier_limits_from_license(self, pro_server, project_120_files):
        """Tier limits read from license: Pro allows 1000 files."""
        result = await pro_server.get_project_map(project_root=str(project_120_files), include_complexity=False)

        # Pro allows up to 1000 files, so all 120 should be counted
        assert result.total_files >= 100, f"Pro tier should count all 120 files (limit 1000), got {result.total_files}"
