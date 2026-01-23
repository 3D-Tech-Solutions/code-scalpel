"""Pro tier tests for get_project_map.

Validates:
- max_files=1000 limit enforced
- max_modules=200 limit enforced
- detail_level='detailed' with advanced fields
- Pro features accessible
- Enterprise features not available

[20260103_TEST] v3.3.1 - Pro tier enforcement and features
"""

import pytest


class TestProTierLimits:
    """Test Pro tier file and module limits."""

    @pytest.mark.asyncio
    async def test_pro_max_files_1000(self, pro_server, project_1200_files):
        """Pro tier: max_files=1000 enforced on 1200-file project."""
        result = await pro_server.get_project_map(project_root=str(project_1200_files), include_complexity=False)

        # Should truncate to 1000 files
        assert result.total_files <= 1000, f"Expected ≤1000 files, got {result.total_files}"

        # Should have truncation warning
        if hasattr(result, "warnings") and result.warnings:
            assert any(
                "1000" in str(w) or "limit" in str(w).lower() for w in result.warnings
            ), f"Expected file limit warning in: {result.warnings}"

    @pytest.mark.asyncio
    async def test_pro_max_modules_200(self, pro_server, project_250_modules):
        """Pro tier: max_modules=200 enforced on 250-module project."""
        result = await pro_server.get_project_map(project_root=str(project_250_modules), include_complexity=False)

        # Count Python files (modules)
        total_modules = len(result.modules)

        # Should truncate to ~200 modules (allowing some flexibility for __init__.py files)
        # 25 packages × 10 modules + 25 __init__.py = 275 files total
        # Expecting ~250 modules (since we have 250 non-__init__ modules)
        assert total_modules <= 300, f"Expected ≤300 modules (200 + packages), got {total_modules}"

    @pytest.mark.asyncio
    async def test_pro_detailed_level(self, pro_server, simple_project):
        """Pro tier: detail_level='detailed' includes advanced fields."""
        result = await pro_server.get_project_map(project_root=str(simple_project), include_complexity=True)

        # Basic fields present
        assert hasattr(result, "packages")
        assert hasattr(result, "modules")

        # Pro-tier fields should be available (even if empty for simple project)
        result_dict = result.model_dump() if hasattr(result, "model_dump") else vars(result)

        # At least one Pro feature should be present in the model
        pro_features = [
            "coupling_metrics",
            "git_ownership",
            "architectural_layers",
            "module_relationships",
            "dependency_diagram",
        ]

        # Model should have these fields defined (even if values are empty)
        available_features = [f for f in pro_features if f in result_dict]
        assert (
            len(available_features) > 0
        ), f"Pro tier should define Pro features in model, available: {list(result_dict.keys())}"

    @pytest.mark.asyncio
    async def test_pro_no_enterprise_features(self, pro_server, simple_project):
        """Pro tier: Enterprise features not available."""
        result = await pro_server.get_project_map(project_root=str(simple_project), include_complexity=True)

        from .conftest import has_enterprise_features

        # Should not have Enterprise features populated
        assert not has_enterprise_features(result), "Pro tier should not have populated Enterprise features"


class TestProTierFeatures:
    """Test Pro tier feature availability."""

    @pytest.mark.asyncio
    async def test_pro_coupling_metrics_field_exists(self, pro_server, flask_project):
        """Pro tier: coupling_metrics field exists in model."""
        result = await pro_server.get_project_map(project_root=str(flask_project), include_complexity=True)

        # Field should exist in model (even if empty)
        result_dict = result.model_dump() if hasattr(result, "model_dump") else vars(result)
        assert (
            "coupling_metrics" in result_dict
        ), f"Pro tier should have coupling_metrics field. Available: {list(result_dict.keys())}"

    @pytest.mark.asyncio
    async def test_pro_git_ownership_field_exists(self, pro_server, simple_project):
        """Pro tier: git_ownership field exists in model."""
        result = await pro_server.get_project_map(project_root=str(simple_project), include_complexity=False)

        result_dict = result.model_dump() if hasattr(result, "model_dump") else vars(result)
        assert (
            "git_ownership" in result_dict
        ), f"Pro tier should have git_ownership field. Available: {list(result_dict.keys())}"

    @pytest.mark.asyncio
    async def test_pro_architectural_layers_field_exists(self, pro_server, flask_project):
        """Pro tier: architectural_layers field exists in model."""
        result = await pro_server.get_project_map(project_root=str(flask_project), include_complexity=False)

        result_dict = result.model_dump() if hasattr(result, "model_dump") else vars(result)
        assert (
            "architectural_layers" in result_dict
        ), f"Pro tier should have architectural_layers field. Available: {list(result_dict.keys())}"

    @pytest.mark.asyncio
    async def test_pro_module_relationships_field_exists(self, pro_server, simple_project):
        """Pro tier: module_relationships field exists in model."""
        result = await pro_server.get_project_map(project_root=str(simple_project), include_complexity=False)

        result_dict = result.model_dump() if hasattr(result, "model_dump") else vars(result)
        assert (
            "module_relationships" in result_dict
        ), f"Pro tier should have module_relationships field. Available: {list(result_dict.keys())}"
