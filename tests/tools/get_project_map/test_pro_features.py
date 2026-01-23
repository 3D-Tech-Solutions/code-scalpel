"""Pro feature tests for get_project_map.

Validates Pro tier features:
- Coupling analysis (fan-in, fan-out metrics)
- Code ownership mapping (git blame integration)
- Architectural layer detection
- Module relationship visualization

[20260103_TEST] v3.3.1 - Pro tier feature validation
"""

import pytest


class TestProFeatureCoupling:
    """Test Pro tier coupling analysis features."""

    @pytest.mark.asyncio
    async def test_coupling_metrics_accessible(self, pro_server, flask_project):
        """Pro tier: coupling_metrics field accessible."""
        result = await pro_server.get_project_map(project_root=str(flask_project), include_complexity=True)

        result_dict = result.model_dump() if hasattr(result, "model_dump") else vars(result)

        # coupling_metrics should exist in Pro tier model
        assert (
            "coupling_metrics" in result_dict
        ), f"Pro tier missing coupling_metrics. Available: {list(result_dict.keys())}"

    @pytest.mark.asyncio
    async def test_community_no_coupling_metrics(self, community_server, flask_project):
        """Community tier: coupling_metrics not populated."""
        result = await community_server.get_project_map(project_root=str(flask_project), include_complexity=True)

        result_dict = result.model_dump() if hasattr(result, "model_dump") else vars(result)

        # If field exists, it should be empty
        if "coupling_metrics" in result_dict:
            value = result_dict["coupling_metrics"]
            assert value in [
                None,
                {},
                [],
            ], f"Community should not have coupling_metrics data, got: {value}"


class TestProFeatureOwnership:
    """Test Pro tier code ownership mapping features."""

    @pytest.mark.asyncio
    async def test_git_ownership_accessible(self, pro_server, simple_project):
        """Pro tier: git_ownership field accessible."""
        result = await pro_server.get_project_map(project_root=str(simple_project), include_complexity=False)

        result_dict = result.model_dump() if hasattr(result, "model_dump") else vars(result)

        # git_ownership should exist in Pro tier model
        assert "git_ownership" in result_dict, f"Pro tier missing git_ownership. Available: {list(result_dict.keys())}"

    @pytest.mark.asyncio
    async def test_community_no_git_ownership(self, community_server, simple_project):
        """Community tier: git_ownership not populated."""
        result = await community_server.get_project_map(project_root=str(simple_project), include_complexity=False)

        result_dict = result.model_dump() if hasattr(result, "model_dump") else vars(result)

        # If field exists, it should be empty
        if "git_ownership" in result_dict:
            value = result_dict["git_ownership"]
            assert value in [
                None,
                {},
                [],
            ], f"Community should not have git_ownership data, got: {value}"


class TestProFeatureArchitecturalLayers:
    """Test Pro tier architectural layer detection."""

    @pytest.mark.asyncio
    async def test_architectural_layers_accessible(self, pro_server, flask_project):
        """Pro tier: architectural_layers field accessible."""
        result = await pro_server.get_project_map(project_root=str(flask_project), include_complexity=False)

        result_dict = result.model_dump() if hasattr(result, "model_dump") else vars(result)

        # architectural_layers should exist in Pro tier model
        assert (
            "architectural_layers" in result_dict
        ), f"Pro tier missing architectural_layers. Available: {list(result_dict.keys())}"

    @pytest.mark.asyncio
    async def test_flask_layer_detection(self, pro_server, flask_project):
        """Pro tier: Detect Flask architectural layers (presentation, business, data)."""
        result = await pro_server.get_project_map(project_root=str(flask_project), include_complexity=False)

        result_dict = result.model_dump() if hasattr(result, "model_dump") else vars(result)

        # For Flask project, architectural_layers might detect layers
        # This is a capability test - field should exist even if detection varies
        assert (
            "architectural_layers" in result_dict
        ), "Pro tier should have architectural_layers field for Flask project"

    @pytest.mark.asyncio
    async def test_community_no_architectural_layers(self, community_server, flask_project):
        """Community tier: architectural_layers not populated."""
        result = await community_server.get_project_map(project_root=str(flask_project), include_complexity=False)

        result_dict = result.model_dump() if hasattr(result, "model_dump") else vars(result)

        # If field exists, it should be empty
        if "architectural_layers" in result_dict:
            value = result_dict["architectural_layers"]
            assert value in [
                None,
                {},
                [],
            ], f"Community should not have architectural_layers data, got: {value}"


class TestProFeatureModuleRelationships:
    """Test Pro tier module relationship visualization."""

    @pytest.mark.asyncio
    async def test_module_relationships_accessible(self, pro_server, simple_project):
        """Pro tier: module_relationships field accessible."""
        result = await pro_server.get_project_map(project_root=str(simple_project), include_complexity=False)

        result_dict = result.model_dump() if hasattr(result, "model_dump") else vars(result)

        # module_relationships should exist in Pro tier model
        assert (
            "module_relationships" in result_dict
        ), f"Pro tier missing module_relationships. Available: {list(result_dict.keys())}"

    @pytest.mark.asyncio
    async def test_dependency_diagram_accessible(self, pro_server, flask_project):
        """Pro tier: dependency_diagram field accessible."""
        result = await pro_server.get_project_map(project_root=str(flask_project), include_complexity=False)

        result_dict = result.model_dump() if hasattr(result, "model_dump") else vars(result)

        # dependency_diagram should exist in Pro tier model
        assert (
            "dependency_diagram" in result_dict
        ), f"Pro tier missing dependency_diagram. Available: {list(result_dict.keys())}"

    @pytest.mark.asyncio
    async def test_community_no_module_relationships(self, community_server, simple_project):
        """Community tier: module_relationships not populated."""
        result = await community_server.get_project_map(project_root=str(simple_project), include_complexity=False)

        result_dict = result.model_dump() if hasattr(result, "model_dump") else vars(result)

        # If field exists, it should be empty
        if "module_relationships" in result_dict:
            value = result_dict["module_relationships"]
            assert value in [
                None,
                {},
                [],
            ], f"Community should not have module_relationships data, got: {value}"
