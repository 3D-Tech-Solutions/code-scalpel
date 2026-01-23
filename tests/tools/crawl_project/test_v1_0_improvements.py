"""
[20260106_TEST] v1.0 Pre-release Validation Tests for crawl_project

Tests validating the pre-release improvements added for v1.0:
1. Output metadata fields (tier_applied, crawl_mode, files_limit_applied)
2. Config alignment between limits.toml and features.py
3. Crawl mode detection (discovery vs deep)

These tests ensure configuration and implementation remain aligned
across releases, similar to analyze_code v1.0 validation tests.
"""

import pytest


class TestOutputMetadata:
    """Tests for output transparency metadata fields."""

    @pytest.fixture
    def temp_project(self, tmp_path):
        """Create a minimal temp project for testing."""
        root = tmp_path / "proj"
        root.mkdir()
        (root / "main.py").write_text("def main(): pass\n")
        (root / "utils.py").write_text("def helper(): return 42\n")
        return root

    @pytest.mark.asyncio
    async def test_tier_applied_field_present(self, temp_project):
        """Verify tier_applied field is populated in output."""
        from code_scalpel.mcp.tools.context import crawl_project

        result = await crawl_project(root_path=str(temp_project))

        assert result.success is True
        assert hasattr(result, "tier_applied")
        assert result.tier_applied is not None
        assert result.tier_applied in ["community", "pro", "enterprise"]

    @pytest.mark.asyncio
    async def test_crawl_mode_field_present(self, temp_project):
        """Verify crawl_mode field is populated in output."""
        from code_scalpel.mcp.tools.context import crawl_project

        result = await crawl_project(root_path=str(temp_project))

        assert result.success is True
        assert hasattr(result, "crawl_mode")
        assert result.crawl_mode is not None
        assert result.crawl_mode in ["discovery", "deep"]

    @pytest.mark.asyncio
    async def test_files_limit_applied_field_present(self, temp_project):
        """Verify files_limit_applied field is populated in output."""
        from code_scalpel.mcp.tools.context import crawl_project

        result = await crawl_project(root_path=str(temp_project))

        assert result.success is True
        assert hasattr(result, "files_limit_applied")
        # Can be None (unlimited) or an integer limit

    @pytest.mark.asyncio
    async def test_community_tier_discovery_mode(self, temp_project, community_env):
        """Community tier should use discovery crawl mode."""
        from code_scalpel.mcp.tools.context import crawl_project

        result = await crawl_project(root_path=str(temp_project))

        assert result.success is True
        assert result.tier_applied == "community"
        assert result.crawl_mode == "discovery"

    @pytest.mark.asyncio
    async def test_pro_tier_deep_mode(self, temp_project, pro_env):
        """Pro tier should use deep crawl mode."""
        from code_scalpel.mcp.tools.context import crawl_project

        result = await crawl_project(root_path=str(temp_project))

        assert result.success is True
        assert result.tier_applied == "pro"
        assert result.crawl_mode == "deep"

    @pytest.mark.asyncio
    async def test_enterprise_tier_deep_mode(self, temp_project, enterprise_env):
        """Enterprise tier should use deep crawl mode."""
        from code_scalpel.mcp.tools.context import crawl_project

        result = await crawl_project(root_path=str(temp_project))

        assert result.success is True
        assert result.tier_applied == "enterprise"
        assert result.crawl_mode == "deep"


class TestConfigAlignment:
    """Tests verifying config files align with implementation."""

    def test_pro_tier_unlimited_files_in_features(self):
        """Pro tier should have unlimited max_files in features.py."""
        from code_scalpel.licensing.features import TOOL_CAPABILITIES

        pro_caps = TOOL_CAPABILITIES["crawl_project"]["pro"]
        # max_files should be None (unlimited) for Pro tier
        assert pro_caps["limits"]["max_files"] is None

    def test_enterprise_tier_unlimited_files_in_features(self):
        """Enterprise tier should have unlimited max_files in features.py."""
        from code_scalpel.licensing.features import TOOL_CAPABILITIES

        enterprise_caps = TOOL_CAPABILITIES["crawl_project"]["enterprise"]
        # max_files should be None (unlimited) for Enterprise tier
        assert enterprise_caps["limits"]["max_files"] is None

    def test_community_tier_has_file_limit_in_features(self):
        """Community tier should have max_files limit in features.py."""
        from code_scalpel.licensing.features import TOOL_CAPABILITIES

        community_caps = TOOL_CAPABILITIES["crawl_project"]["community"]
        # Community should have a limit (100)
        assert community_caps["limits"]["max_files"] == 100

    def test_limits_toml_pro_tier_no_max_files(self):
        """Pro tier in limits.toml should NOT have max_files (removed in v1.0 fix)."""
        from code_scalpel.licensing.config_loader import get_cached_limits

        config = get_cached_limits()

        # Pro crawl_project should NOT have max_files key (unlimited)
        pro_section = config.get("pro", {}).get("crawl_project", {})
        # If max_files exists, it should be None (not a hardcoded limit)
        if "max_files" in pro_section:
            assert pro_section["max_files"] is None, "Pro tier should have unlimited files (max_files=None or omitted)"


class TestCrawlModeCapabilities:
    """Tests for crawl mode-specific capabilities."""

    @pytest.fixture
    def temp_flask_project(self, tmp_path):
        """Create a temp project with Flask app for entrypoint detection."""
        root = tmp_path / "flask_proj"
        root.mkdir()
        flask_code = """
from flask import Flask

app = Flask(__name__)

@app.route("/")
def index():
    return "Hello"

if __name__ == "__main__":
    app.run()
"""
        (root / "app.py").write_text(flask_code)
        return root

    @pytest.mark.asyncio
    async def test_discovery_mode_detects_entrypoints(self, temp_flask_project, community_env):
        """Discovery mode should detect entrypoints."""
        from code_scalpel.mcp.tools.context import crawl_project

        result = await crawl_project(root_path=str(temp_flask_project))

        assert result.success is True
        assert result.crawl_mode == "discovery"
        # Should have entrypoints detected
        assert result.entrypoints is not None
        assert len(result.entrypoints) > 0

    @pytest.mark.asyncio
    async def test_discovery_mode_provides_framework_hints(self, temp_flask_project, community_env):
        """Discovery mode should provide framework hints."""
        from code_scalpel.mcp.tools.context import crawl_project

        result = await crawl_project(root_path=str(temp_flask_project))

        assert result.success is True
        # Should detect Flask
        assert result.framework_hints is not None
        assert "flask" in result.framework_hints

    @pytest.mark.asyncio
    async def test_deep_mode_provides_complexity(self, temp_flask_project, pro_env):
        """Deep mode should provide function/class details."""
        from code_scalpel.mcp.tools.context import crawl_project

        result = await crawl_project(root_path=str(temp_flask_project))

        assert result.success is True
        assert result.crawl_mode == "deep"
        # Deep mode should have functions/classes analyzed
        assert result.summary.total_functions >= 0
        # Files should have function details in deep mode
        if result.files:
            # At least one file should have been analyzed
            analyzed_files = [f for f in result.files if f.status == "success"]
            assert len(analyzed_files) > 0


class TestModelSchema:
    """Tests for ProjectCrawlResult model schema."""

    def test_model_has_metadata_fields(self):
        """ProjectCrawlResult should have new metadata fields."""
        from code_scalpel.mcp.server import ProjectCrawlResult

        # Check field definitions exist
        fields = ProjectCrawlResult.model_fields
        assert "tier_applied" in fields
        assert "crawl_mode" in fields
        assert "files_limit_applied" in fields

    def test_metadata_fields_allow_none(self):
        """Metadata fields should allow None values."""
        from code_scalpel.mcp.server import CrawlSummary, ProjectCrawlResult

        # Should be able to create result with None metadata
        result = ProjectCrawlResult(
            success=True,
            root_path="/test",
            timestamp="2025-01-06T00:00:00",
            summary=CrawlSummary(
                total_files=0,
                successful_files=0,
                failed_files=0,
                total_lines_of_code=0,
                total_functions=0,
                total_classes=0,
                complexity_warnings=0,
            ),
            tier_applied=None,
            crawl_mode=None,
            files_limit_applied=None,
        )
        assert result.tier_applied is None
        assert result.crawl_mode is None
        assert result.files_limit_applied is None

    def test_metadata_fields_serializable(self):
        """Metadata fields should be JSON serializable."""
        from code_scalpel.mcp.server import CrawlSummary, ProjectCrawlResult

        result = ProjectCrawlResult(
            success=True,
            root_path="/test",
            timestamp="2025-01-06T00:00:00",
            summary=CrawlSummary(
                total_files=10,
                successful_files=10,
                failed_files=0,
                total_lines_of_code=500,
                total_functions=20,
                total_classes=5,
                complexity_warnings=2,
            ),
            tier_applied="community",
            crawl_mode="discovery",
            files_limit_applied=100,
        )

        # Should serialize without error
        json_data = result.model_dump_json()
        assert "tier_applied" in json_data
        assert "crawl_mode" in json_data
        assert "files_limit_applied" in json_data
        assert '"community"' in json_data
        assert '"discovery"' in json_data
