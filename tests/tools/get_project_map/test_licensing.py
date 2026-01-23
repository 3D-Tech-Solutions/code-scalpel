"""License fallback tests for get_project_map.

Validates:
- Expired license → fallback to Community tier
- Invalid license → fallback to Community tier
- Missing license → default to Community tier

[20260103_TEST] v3.3.1 - License validation and fallback behavior
"""

import pytest


class TestLicenseFallback:
    """Test invalid/expired license handling."""

    @pytest.mark.asyncio
    async def test_expired_license_fallback(self, server_expired_license, project_120_files):
        """Expired license → fallback to Community tier with warning."""
        result = await server_expired_license.get_project_map(
            project_root=str(project_120_files), include_complexity=False
        )

        # Should fallback to Community limits (max 100 files)
        assert (
            result.total_files <= 100
        ), f"Expired license should fallback to Community (100 files), got {result.total_files}"

        # Should have warning about expired license
        assert hasattr(result, "warnings") and result.warnings, "Expected warnings about expired license"

        assert any(
            "expired" in str(w).lower() for w in result.warnings
        ), f"Expected 'expired' warning, got: {result.warnings}"

    @pytest.mark.asyncio
    async def test_invalid_license_fallback(self, server_invalid_license, project_120_files):
        """Invalid license → fallback to Community tier with warning."""
        result = await server_invalid_license.get_project_map(
            project_root=str(project_120_files), include_complexity=False
        )

        # Should fallback to Community limits
        assert (
            result.total_files <= 100
        ), f"Invalid license should fallback to Community (100 files), got {result.total_files}"

        # Should have warning about invalid license
        assert hasattr(result, "warnings") and result.warnings, "Expected warnings about invalid license"

        assert any(
            "invalid" in str(w).lower() for w in result.warnings
        ), f"Expected 'invalid' warning, got: {result.warnings}"

    @pytest.mark.asyncio
    async def test_missing_license_default_community(self, server_no_license, project_120_files):
        """Missing license file → default to Community tier."""
        result = await server_no_license.get_project_map(project_root=str(project_120_files), include_complexity=False)

        # Should default to Community limits (max 100 files)
        assert (
            result.total_files <= 100
        ), f"Missing license should default to Community (100 files), got {result.total_files}"

    @pytest.mark.asyncio
    async def test_valid_pro_license_unlocks_features(self, community_server, pro_server, simple_project):
        """Valid Pro license unlocks Pro features vs Community."""
        # Community: No Pro features
        com_result = await community_server.get_project_map(project_root=str(simple_project), include_complexity=False)

        from .conftest import has_pro_features

        assert not has_pro_features(com_result), "Community tier should not have Pro features"

        # Pro: Pro features available
        pro_result = await pro_server.get_project_map(project_root=str(simple_project), include_complexity=False)

        # Pro should have Pro feature fields in model
        pro_dict = pro_result.model_dump() if hasattr(pro_result, "model_dump") else vars(pro_result)
        pro_features = ["coupling_metrics", "git_ownership", "architectural_layers"]

        available = [f for f in pro_features if f in pro_dict]
        assert len(available) > 0, f"Pro tier should have Pro feature fields. Available: {list(pro_dict.keys())}"
