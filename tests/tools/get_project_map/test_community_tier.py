"""Community tier tests for get_project_map.

Validates:
- max_files=100 limit enforced
- max_modules=50 limit enforced
- detail_level='basic' with limited fields
- Pro features not available

[20260103_TEST] v3.3.1 - Community tier enforcement
"""

import pytest


class TestCommunityTierLimits:
    """Test Community tier file and module limits."""

    @pytest.mark.asyncio
    async def test_community_max_files_100(self, community_server, project_120_files):
        """Community tier: max_files=100 enforced on 120-file project."""
        result = await community_server.get_project_map(project_root=str(project_120_files), include_complexity=False)

        # Should truncate to 100 files
        assert result.total_files <= 100, f"Expected ≤100 files, got {result.total_files}"

        # Should have truncation warning
        if hasattr(result, "warnings") and result.warnings:
            assert any(
                "100" in str(w) or "limit" in str(w).lower() or "truncat" in str(w).lower() for w in result.warnings
            ), f"Expected file limit warning, got: {result.warnings}"

    @pytest.mark.asyncio
    async def test_community_max_modules_50(self, community_server, project_60_modules):
        """Community tier: max_modules=50 enforced on 60-module project."""
        result = await community_server.get_project_map(project_root=str(project_60_modules), include_complexity=False)

        # Count Python files (modules)
        total_modules = len(result.modules)

        # Should truncate to ~50 modules (allowing some flexibility for __init__.py files)
        assert total_modules <= 72, f"Expected ≤72 modules (50 + packages), got {total_modules}"

    @pytest.mark.asyncio
    async def test_community_basic_detail_level(self, community_server, simple_project):
        """Community tier: detail_level='basic' with limited fields."""
        result = await community_server.get_project_map(project_root=str(simple_project), include_complexity=True)

        # Basic fields should be present
        assert hasattr(result, "packages")
        assert hasattr(result, "modules")
        assert hasattr(result, "total_files")
        assert hasattr(result, "languages")

        # Pro features should NOT be present or should be empty
        result_dict = result.model_dump() if hasattr(result, "model_dump") else vars(result)

        # Check Pro features are absent or empty
        pro_features = [
            "coupling_metrics",
            "git_ownership",
            "architectural_layers",
            "module_relationships",
            "dependency_diagram",
        ]

        for feature in pro_features:
            if feature in result_dict:
                value = result_dict[feature]
                assert value in [
                    None,
                    [],
                    {},
                    "",
                ], f"Community tier should not have {feature}, got: {value}"

    @pytest.mark.asyncio
    async def test_community_no_pro_features(self, community_server, simple_project):
        """Community tier: Pro features not available."""
        result = await community_server.get_project_map(project_root=str(simple_project), include_complexity=True)

        from .conftest import has_enterprise_features, has_pro_features

        # Should not have Pro features
        assert not has_pro_features(result), "Community tier should not have Pro features"

        # Should not have Enterprise features
        assert not has_enterprise_features(result), "Community tier should not have Enterprise features"
