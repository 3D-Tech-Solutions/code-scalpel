"""Enterprise feature tests for get_project_map.

Validates Enterprise tier features:
- Interactive city map (3D complexity visualization)
- Force directed graph
- Bug hotspot heatmap
- Code churn visualization
- Multi-repository maps
- Historical architecture trends
- Custom map metrics
- Compliance overlay
- Service boundary detection

[20260103_TEST] v3.3.1 - Enterprise tier feature validation
"""

import pytest


class TestEnterpriseFeatureVisualization:
    """Test Enterprise tier visualization features."""

    @pytest.mark.asyncio
    async def test_city_map_data_accessible(self, enterprise_server, simple_project):
        """Enterprise tier: city_map_data field accessible."""
        result = await enterprise_server.get_project_map(project_root=str(simple_project), include_complexity=True)

        # [20260122_BUGFIX] Use hasattr() which works with __getattr__ forwarding
        assert hasattr(result, "city_map_data"), "Enterprise missing city_map_data"
        assert result.city_map_data is not None

    @pytest.mark.asyncio
    async def test_force_graph_accessible(self, enterprise_server, flask_project):
        """Enterprise tier: force_graph field accessible."""
        result = await enterprise_server.get_project_map(project_root=str(flask_project), include_complexity=False)

        result_dict = result.model_dump() if hasattr(result, "model_dump") else vars(result)

        assert "force_graph" in result_dict, f"Enterprise missing force_graph. Available: {list(result_dict.keys())}"

    @pytest.mark.asyncio
    async def test_pro_no_city_map(self, pro_server, simple_project):
        """Pro tier: city_map_data not populated."""
        result = await pro_server.get_project_map(project_root=str(simple_project), include_complexity=True)

        result_dict = result.model_dump() if hasattr(result, "model_dump") else vars(result)

        if "city_map_data" in result_dict:
            value = result_dict["city_map_data"]
            assert value in [
                None,
                {},
                [],
            ], f"Pro should not have city_map_data, got: {value}"


class TestEnterpriseFeatureHotspots:
    """Test Enterprise tier hotspot analysis features."""

    @pytest.mark.asyncio
    async def test_bug_hotspots_accessible(self, enterprise_server, simple_project):
        """Enterprise tier: bug_hotspots field accessible."""
        result = await enterprise_server.get_project_map(project_root=str(simple_project), include_complexity=False)

        result_dict = result.model_dump() if hasattr(result, "model_dump") else vars(result)

        assert "bug_hotspots" in result_dict, f"Enterprise missing bug_hotspots. Available: {list(result_dict.keys())}"

    @pytest.mark.asyncio
    async def test_churn_heatmap_accessible(self, enterprise_server, simple_project):
        """Enterprise tier: churn_heatmap field accessible."""
        result = await enterprise_server.get_project_map(project_root=str(simple_project), include_complexity=False)

        result_dict = result.model_dump() if hasattr(result, "model_dump") else vars(result)

        assert (
            "churn_heatmap" in result_dict
        ), f"Enterprise missing churn_heatmap. Available: {list(result_dict.keys())}"


class TestEnterpriseFeatureMultiRepo:
    """Test Enterprise tier multi-repository features."""

    @pytest.mark.asyncio
    async def test_multi_repo_summary_accessible(self, enterprise_server, simple_project):
        """Enterprise tier: multi_repo_summary field accessible."""
        result = await enterprise_server.get_project_map(project_root=str(simple_project), include_complexity=False)

        result_dict = result.model_dump() if hasattr(result, "model_dump") else vars(result)

        assert (
            "multi_repo_summary" in result_dict
        ), f"Enterprise missing multi_repo_summary. Available: {list(result_dict.keys())}"

    @pytest.mark.asyncio
    async def test_pro_no_multi_repo(self, pro_server, simple_project):
        """Pro tier: multi_repo_summary not populated."""
        result = await pro_server.get_project_map(project_root=str(simple_project), include_complexity=False)

        result_dict = result.model_dump() if hasattr(result, "model_dump") else vars(result)

        if "multi_repo_summary" in result_dict:
            value = result_dict["multi_repo_summary"]
            assert value in [
                None,
                {},
                [],
            ], f"Pro should not have multi_repo_summary, got: {value}"


class TestEnterpriseFeatureCompliance:
    """Test Enterprise tier compliance features."""

    @pytest.mark.asyncio
    async def test_compliance_overlay_accessible(self, enterprise_server, flask_project):
        """Enterprise tier: compliance_overlay field accessible."""
        result = await enterprise_server.get_project_map(project_root=str(flask_project), include_complexity=False)

        result_dict = result.model_dump() if hasattr(result, "model_dump") else vars(result)

        assert (
            "compliance_overlay" in result_dict
        ), f"Enterprise missing compliance_overlay. Available: {list(result_dict.keys())}"

    @pytest.mark.asyncio
    async def test_pro_no_compliance(self, pro_server, flask_project):
        """Pro tier: compliance_overlay not populated."""
        result = await pro_server.get_project_map(project_root=str(flask_project), include_complexity=False)

        result_dict = result.model_dump() if hasattr(result, "model_dump") else vars(result)

        if "compliance_overlay" in result_dict:
            value = result_dict["compliance_overlay"]
            assert value in [
                None,
                {},
                [],
            ], f"Pro should not have compliance_overlay, got: {value}"


class TestEnterpriseFeatureCustomMetrics:
    """Test Enterprise tier custom metrics and trends."""

    @pytest.mark.asyncio
    async def test_historical_trends_accessible(self, enterprise_server, simple_project):
        """Enterprise tier: historical_trends field accessible."""
        result = await enterprise_server.get_project_map(project_root=str(simple_project), include_complexity=False)

        result_dict = result.model_dump() if hasattr(result, "model_dump") else vars(result)

        # May be named historical_trends or historical_architecture_trends
        has_trends = "historical_trends" in result_dict or "historical_architecture_trends" in result_dict
        assert has_trends, f"Enterprise missing historical trends field. Available: {list(result_dict.keys())}"

    @pytest.mark.asyncio
    async def test_custom_metrics_accessible(self, enterprise_server, simple_project):
        """Enterprise tier: custom_metrics field accessible."""
        result = await enterprise_server.get_project_map(project_root=str(simple_project), include_complexity=False)

        result_dict = result.model_dump() if hasattr(result, "model_dump") else vars(result)

        assert (
            "custom_metrics" in result_dict
        ), f"Enterprise missing custom_metrics. Available: {list(result_dict.keys())}"
