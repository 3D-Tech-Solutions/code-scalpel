"""
Output metadata field tests for get_project_map.

Tests tier transparency fields:
- tier_applied: The tier that was applied to the request
- max_files_applied: The max_files limit applied
- max_modules_applied: The max_modules limit applied
- pro_features_enabled: Whether Pro tier features were enabled
- enterprise_features_enabled: Whether Enterprise tier features were enabled

[20260111_TEST] v3.3.1 - Output metadata field validation for AI agent transparency
"""

import tempfile
from pathlib import Path

import pytest

from code_scalpel.mcp.helpers.graph_helpers import _get_project_map_sync


@pytest.fixture
def temp_project_dir():
    """Create a temporary project directory with Python files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a simple project structure
        src_dir = Path(tmpdir) / "src"
        src_dir.mkdir()

        # Create __init__.py for package
        (src_dir / "__init__.py").write_text("# Package init\n")

        # Create some Python files
        (src_dir / "main.py").write_text('''
"""Main module."""

def main():
    """Entry point."""
    print("Hello, world!")

if __name__ == "__main__":
    main()
''')

        (src_dir / "utils.py").write_text('''
"""Utility functions."""

def helper():
    """A helper function."""
    return 42
''')

        yield tmpdir


class TestOutputMetadataFieldsCommunity:
    """Test output metadata fields at Community tier."""

    def test_tier_applied_is_community(self, temp_project_dir):
        """Community tier: tier_applied should be 'community'."""
        result = _get_project_map_sync(
            project_root=temp_project_dir,
            include_complexity=True,
            complexity_threshold=10,
            include_circular_check=False,
            tier="community",
        )
        assert result.success is True
        assert result.tier_applied == "community"

    def test_max_files_applied_is_100(self, temp_project_dir):
        """Community tier: max_files_applied should be 100."""
        result = _get_project_map_sync(
            project_root=temp_project_dir,
            include_complexity=True,
            complexity_threshold=10,
            include_circular_check=False,
            tier="community",
        )
        assert result.success is True
        assert result.max_files_applied == 100

    def test_max_modules_applied_is_50(self, temp_project_dir):
        """Community tier: max_modules_applied should be 50."""
        result = _get_project_map_sync(
            project_root=temp_project_dir,
            include_complexity=True,
            complexity_threshold=10,
            include_circular_check=False,
            tier="community",
        )
        assert result.success is True
        assert result.max_modules_applied == 50

    def test_pro_features_enabled_is_false(self, temp_project_dir):
        """Community tier: pro_features_enabled should be False."""
        result = _get_project_map_sync(
            project_root=temp_project_dir,
            include_complexity=True,
            complexity_threshold=10,
            include_circular_check=False,
            tier="community",
        )
        assert result.success is True
        assert result.pro_features_enabled is False

    def test_enterprise_features_enabled_is_false(self, temp_project_dir):
        """Community tier: enterprise_features_enabled should be False."""
        result = _get_project_map_sync(
            project_root=temp_project_dir,
            include_complexity=True,
            complexity_threshold=10,
            include_circular_check=False,
            tier="community",
        )
        assert result.success is True
        assert result.enterprise_features_enabled is False

    def test_all_metadata_fields_present(self, temp_project_dir):
        """Community tier: all metadata fields should be present."""
        result = _get_project_map_sync(
            project_root=temp_project_dir,
            include_complexity=True,
            complexity_threshold=10,
            include_circular_check=False,
            tier="community",
        )
        assert result.success is True
        assert hasattr(result, "tier_applied")
        assert hasattr(result, "max_files_applied")
        assert hasattr(result, "max_modules_applied")
        assert hasattr(result, "pro_features_enabled")
        assert hasattr(result, "enterprise_features_enabled")


class TestOutputMetadataFieldsPro:
    """Test output metadata fields at Pro tier."""

    def test_tier_applied_is_pro(self, temp_project_dir):
        """Pro tier: tier_applied should be 'pro'."""
        result = _get_project_map_sync(
            project_root=temp_project_dir,
            include_complexity=True,
            complexity_threshold=10,
            include_circular_check=False,
            tier="pro",
        )
        assert result.success is True
        assert result.tier_applied == "pro"

    def test_max_files_applied_is_1000(self, temp_project_dir):
        """Pro tier: max_files_applied should be 1000."""
        result = _get_project_map_sync(
            project_root=temp_project_dir,
            include_complexity=True,
            complexity_threshold=10,
            include_circular_check=False,
            tier="pro",
        )
        assert result.success is True
        assert result.max_files_applied == 1000

    def test_max_modules_applied_is_200(self, temp_project_dir):
        """Pro tier: max_modules_applied should be 200."""
        result = _get_project_map_sync(
            project_root=temp_project_dir,
            include_complexity=True,
            complexity_threshold=10,
            include_circular_check=False,
            tier="pro",
        )
        assert result.success is True
        assert result.max_modules_applied == 200

    def test_pro_features_enabled_is_true(self, temp_project_dir):
        """Pro tier: pro_features_enabled should be True."""
        result = _get_project_map_sync(
            project_root=temp_project_dir,
            include_complexity=True,
            complexity_threshold=10,
            include_circular_check=False,
            tier="pro",
        )
        assert result.success is True
        assert result.pro_features_enabled is True

    def test_enterprise_features_enabled_is_false(self, temp_project_dir):
        """Pro tier: enterprise_features_enabled should be False."""
        result = _get_project_map_sync(
            project_root=temp_project_dir,
            include_complexity=True,
            complexity_threshold=10,
            include_circular_check=False,
            tier="pro",
        )
        assert result.success is True
        assert result.enterprise_features_enabled is False

    def test_all_metadata_fields_present(self, temp_project_dir):
        """Pro tier: all metadata fields should be present."""
        result = _get_project_map_sync(
            project_root=temp_project_dir,
            include_complexity=True,
            complexity_threshold=10,
            include_circular_check=False,
            tier="pro",
        )
        assert result.success is True
        assert hasattr(result, "tier_applied")
        assert hasattr(result, "max_files_applied")
        assert hasattr(result, "max_modules_applied")
        assert hasattr(result, "pro_features_enabled")
        assert hasattr(result, "enterprise_features_enabled")


class TestOutputMetadataFieldsEnterprise:
    """Test output metadata fields at Enterprise tier."""

    def test_tier_applied_is_enterprise(self, temp_project_dir):
        """Enterprise tier: tier_applied should be 'enterprise'."""
        result = _get_project_map_sync(
            project_root=temp_project_dir,
            include_complexity=True,
            complexity_threshold=10,
            include_circular_check=False,
            tier="enterprise",
        )
        assert result.success is True
        assert result.tier_applied == "enterprise"

    def test_max_files_applied_is_none(self, temp_project_dir):
        """Enterprise tier: max_files_applied should be None (unlimited)."""
        result = _get_project_map_sync(
            project_root=temp_project_dir,
            include_complexity=True,
            complexity_threshold=10,
            include_circular_check=False,
            tier="enterprise",
        )
        assert result.success is True
        assert result.max_files_applied is None

    def test_max_modules_applied_is_1000(self, temp_project_dir):
        """Enterprise tier: max_modules_applied should be 1000."""
        result = _get_project_map_sync(
            project_root=temp_project_dir,
            include_complexity=True,
            complexity_threshold=10,
            include_circular_check=False,
            tier="enterprise",
        )
        assert result.success is True
        assert result.max_modules_applied == 1000

    def test_pro_features_enabled_is_true(self, temp_project_dir):
        """Enterprise tier: pro_features_enabled should be True (inherited)."""
        result = _get_project_map_sync(
            project_root=temp_project_dir,
            include_complexity=True,
            complexity_threshold=10,
            include_circular_check=False,
            tier="enterprise",
        )
        assert result.success is True
        assert result.pro_features_enabled is True

    def test_enterprise_features_enabled_is_true(self, temp_project_dir):
        """Enterprise tier: enterprise_features_enabled should be True."""
        result = _get_project_map_sync(
            project_root=temp_project_dir,
            include_complexity=True,
            complexity_threshold=10,
            include_circular_check=False,
            tier="enterprise",
        )
        assert result.success is True
        assert result.enterprise_features_enabled is True

    def test_all_metadata_fields_present(self, temp_project_dir):
        """Enterprise tier: all metadata fields should be present."""
        result = _get_project_map_sync(
            project_root=temp_project_dir,
            include_complexity=True,
            complexity_threshold=10,
            include_circular_check=False,
            tier="enterprise",
        )
        assert result.success is True
        assert hasattr(result, "tier_applied")
        assert hasattr(result, "max_files_applied")
        assert hasattr(result, "max_modules_applied")
        assert hasattr(result, "pro_features_enabled")
        assert hasattr(result, "enterprise_features_enabled")


class TestOutputMetadataFieldsOnError:
    """Test output metadata fields on error conditions."""

    def test_project_not_found_includes_metadata(self):
        """Error case: project not found should still include metadata fields."""
        result = _get_project_map_sync(
            project_root="/nonexistent/path/that/does/not/exist",
            include_complexity=True,
            complexity_threshold=10,
            include_circular_check=False,
            tier="community",
        )
        assert result.success is False
        assert "not found" in result.error.lower()
        assert result.tier_applied == "community"
        assert hasattr(result, "pro_features_enabled")
        assert hasattr(result, "enterprise_features_enabled")

    def test_error_includes_pro_tier_metadata(self):
        """Error case: Pro tier error should include tier metadata."""
        result = _get_project_map_sync(
            project_root="/nonexistent/path/that/does/not/exist",
            include_complexity=True,
            complexity_threshold=10,
            include_circular_check=False,
            tier="pro",
        )
        assert result.success is False
        assert result.tier_applied == "pro"
        assert result.pro_features_enabled is True
        assert result.enterprise_features_enabled is False

    def test_error_includes_enterprise_tier_metadata(self):
        """Error case: Enterprise tier error should include tier metadata."""
        result = _get_project_map_sync(
            project_root="/nonexistent/path/that/does/not/exist",
            include_complexity=True,
            complexity_threshold=10,
            include_circular_check=False,
            tier="enterprise",
        )
        assert result.success is False
        assert result.tier_applied == "enterprise"
        assert result.pro_features_enabled is True
        assert result.enterprise_features_enabled is True


class TestOutputMetadataConsistency:
    """Test output metadata consistency across calls."""

    def test_metadata_consistent_across_calls(self, temp_project_dir):
        """Metadata should be consistent across multiple calls."""
        results = []
        for _ in range(3):
            result = _get_project_map_sync(
                project_root=temp_project_dir,
                include_complexity=True,
                complexity_threshold=10,
                include_circular_check=False,
                tier="community",
            )
            results.append(result)

        # All results should have identical metadata
        for r in results[1:]:
            assert r.tier_applied == results[0].tier_applied
            assert r.max_files_applied == results[0].max_files_applied
            assert r.max_modules_applied == results[0].max_modules_applied
            assert r.pro_features_enabled == results[0].pro_features_enabled
            assert r.enterprise_features_enabled == results[0].enterprise_features_enabled

    def test_metadata_matches_capabilities(self, temp_project_dir):
        """Pro features enabled should match coupling_metrics presence."""
        result = _get_project_map_sync(
            project_root=temp_project_dir,
            include_complexity=True,
            complexity_threshold=10,
            include_circular_check=False,
            tier="pro",
        )
        assert result.success is True
        # If pro_features_enabled, Pro-tier features should be populated
        if result.pro_features_enabled:
            # coupling_metrics should be a list (even if empty)
            assert result.coupling_metrics is not None or isinstance(result.coupling_metrics, list)
