"""Feature gating tests for get_project_map.

Validates that tier restrictions are properly enforced:
- Community tier cannot access Pro features
- Pro tier cannot access Enterprise features
- Feature fields are properly omitted/empty for lower tiers

[20260103_TEST] v3.3.1 - Feature gating validation
"""

import pytest


class TestFeatureGatingCommunityToPro:
    """Test Community tier cannot access Pro features."""

    @pytest.mark.asyncio
    async def test_community_coupling_gated(self, community_server, flask_project):
        """Community attempting Pro coupling_metrics → should be omitted/empty."""
        result = await community_server.get_project_map(project_root=str(flask_project), include_complexity=True)

        result_dict = result.model_dump() if hasattr(result, "model_dump") else vars(result)

        # If coupling_metrics exists, it should be empty
        if "coupling_metrics" in result_dict:
            value = result_dict["coupling_metrics"]
            assert value in [
                None,
                {},
                [],
            ], f"Community should not have coupling_metrics data, got: {type(value)} = {value}"

    @pytest.mark.asyncio
    async def test_community_ownership_gated(self, community_server, simple_project):
        """Community attempting Pro git_ownership → should be omitted/empty."""
        result = await community_server.get_project_map(project_root=str(simple_project), include_complexity=False)

        result_dict = result.model_dump() if hasattr(result, "model_dump") else vars(result)

        # If git_ownership exists, it should be empty
        if "git_ownership" in result_dict:
            value = result_dict["git_ownership"]
            assert value in [
                None,
                {},
                [],
            ], f"Community should not have git_ownership data, got: {value}"

    @pytest.mark.asyncio
    async def test_community_layers_gated(self, community_server, flask_project):
        """Community attempting Pro architectural_layers → should be omitted/empty."""
        result = await community_server.get_project_map(project_root=str(flask_project), include_complexity=False)

        result_dict = result.model_dump() if hasattr(result, "model_dump") else vars(result)

        # If architectural_layers exists, it should be empty
        if "architectural_layers" in result_dict:
            value = result_dict["architectural_layers"]
            assert value in [
                None,
                {},
                [],
            ], f"Community should not have architectural_layers data, got: {value}"


class TestFeatureGatingProToEnterprise:
    """Test Pro tier cannot access Enterprise features."""

    @pytest.mark.asyncio
    async def test_pro_city_map_gated(self, pro_server, simple_project):
        """Pro attempting Enterprise city_map_data → should be omitted/empty."""
        result = await pro_server.get_project_map(project_root=str(simple_project), include_complexity=True)

        result_dict = result.model_dump() if hasattr(result, "model_dump") else vars(result)

        # If city_map_data exists, it should be empty
        if "city_map_data" in result_dict:
            value = result_dict["city_map_data"]
            assert value in [
                None,
                {},
                [],
            ], f"Pro should not have city_map_data, got: {value}"

    @pytest.mark.asyncio
    async def test_pro_compliance_gated(self, pro_server, flask_project):
        """Pro attempting Enterprise compliance_overlay → should be omitted/empty."""
        result = await pro_server.get_project_map(project_root=str(flask_project), include_complexity=False)

        result_dict = result.model_dump() if hasattr(result, "model_dump") else vars(result)

        # If compliance_overlay exists, it should be empty
        if "compliance_overlay" in result_dict:
            value = result_dict["compliance_overlay"]
            assert value in [
                None,
                {},
                [],
            ], f"Pro should not have compliance_overlay, got: {value}"

    @pytest.mark.asyncio
    async def test_pro_multi_repo_gated(self, pro_server, simple_project):
        """Pro attempting Enterprise multi_repo_summary → should be omitted/empty."""
        result = await pro_server.get_project_map(project_root=str(simple_project), include_complexity=False)

        result_dict = result.model_dump() if hasattr(result, "model_dump") else vars(result)

        # If multi_repo_summary exists, it should be empty
        if "multi_repo_summary" in result_dict:
            value = result_dict["multi_repo_summary"]
            assert value in [
                None,
                {},
                [],
            ], f"Pro should not have multi_repo_summary, got: {value}"
