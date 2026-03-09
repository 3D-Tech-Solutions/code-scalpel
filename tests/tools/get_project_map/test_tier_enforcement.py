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
    async def test_community_to_pro_upgrade(
        self, community_server, pro_server, project_120_files
    ):
        """Upgrade Community→Pro: file limit increases from 500→unlimited."""
        # Community: Should be limited to 500 files
        com_result = await community_server.get_project_map(
            project_root=str(project_120_files), include_complexity=False
        )

        assert (
            com_result.total_files <= 500
        ), f"Community should limit to 500 files, got {com_result.total_files}"

        # Pro: Should handle all 120 files (unlimited)
        pro_result = await pro_server.get_project_map(
            project_root=str(project_120_files), include_complexity=False
        )

        assert (
            pro_result.total_files >= 100
        ), f"Pro should handle >100 files, got {pro_result.total_files}"
        assert (
            pro_result.total_files >= com_result.total_files
        ), "Pro should see more files than Community"

    @pytest.mark.asyncio
    async def test_pro_to_enterprise_features(
        self, pro_server, enterprise_server, simple_project
    ):
        """Upgrade Pro→Enterprise: unlock Enterprise features."""
        # Pro: Should not have Enterprise features
        pro_result = await pro_server.get_project_map(
            project_root=str(simple_project), include_complexity=True
        )

        from .conftest import has_enterprise_features

        assert not has_enterprise_features(
            pro_result
        ), "Pro tier should not have populated Enterprise features"

        # Enterprise: Should have Enterprise feature fields
        ent_result = await enterprise_server.get_project_map(
            project_root=str(simple_project), include_complexity=True
        )

        ent_dict = (
            ent_result.model_dump()
            if hasattr(ent_result, "model_dump")
            else vars(ent_result)
        )

        # Enterprise feature fields should exist
        ent_features = ["city_map_data", "compliance_overlay", "multi_repo_summary"]
        available = [f for f in ent_features if f in ent_dict]
        assert (
            len(available) > 0
        ), f"Enterprise should have Enterprise feature fields. Available: {list(ent_dict.keys())}"

    @pytest.mark.asyncio
    async def test_tier_detail_level_progression(
        self, community_server, pro_server, enterprise_server, simple_project
    ):
        """Detail level increases: basic→detailed→comprehensive."""
        # Community: basic
        com_result = await community_server.get_project_map(
            project_root=str(simple_project), include_complexity=False
        )

        # Pro: detailed (more fields than Community)
        pro_result = await pro_server.get_project_map(
            project_root=str(simple_project), include_complexity=False
        )

        # Enterprise: comprehensive (most fields)
        ent_result = await enterprise_server.get_project_map(
            project_root=str(simple_project), include_complexity=False
        )

        # Compare field counts
        com_dict = (
            com_result.model_dump()
            if hasattr(com_result, "model_dump")
            else vars(com_result)
        )
        pro_dict = (
            pro_result.model_dump()
            if hasattr(pro_result, "model_dump")
            else vars(pro_result)
        )
        ent_dict = (
            ent_result.model_dump()
            if hasattr(ent_result, "model_dump")
            else vars(ent_result)
        )

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
        """Tier limits read from license: Pro allows unlimited files."""
        result = await pro_server.get_project_map(
            project_root=str(project_120_files), include_complexity=False
        )

        # Pro allows unlimited files, so all 120 should be counted
        assert (
            result.total_files >= 100
        ), f"Pro tier should count all 120 files (unlimited), got {result.total_files}"

    @pytest.mark.asyncio
    async def test_typescript_project_map_preserves_tier_metadata(
        self, community_server, pro_server, tmp_path
    ):
        """[20260307_TEST] JS/TS project-map slices should still expose tier metadata correctly."""
        root = tmp_path / "ts_project_map_tiers"
        src = root / "src"
        src.mkdir(parents=True)

        (src / "util.ts").write_text(
            "export function helper(): number {\n    return 1\n}\n",
            encoding="utf-8",
        )
        (src / "main.ts").write_text(
            'import { helper } from "./util"\n\n'
            "export function entry(): number {\n    return helper()\n}\n",
            encoding="utf-8",
        )

        community_result = await community_server.get_project_map(
            project_root=str(root), include_complexity=False
        )
        pro_result = await pro_server.get_project_map(
            project_root=str(root), include_complexity=False
        )

        assert community_result.success is True
        assert community_result.tier_applied == "community"
        assert community_result.max_files_applied == 500
        assert community_result.max_modules_applied == 100
        assert community_result.languages.get("typescript") == 2

        assert pro_result.success is True
        assert pro_result.tier_applied == "pro"
        assert pro_result.max_files_applied is None
        assert pro_result.max_modules_applied == 1000
        assert pro_result.languages.get("typescript") == 2

    @pytest.mark.asyncio
    async def test_java_project_map_preserves_tier_metadata(
        self, community_server, pro_server, tmp_path
    ):
        """[20260308_TEST] Java project-map slices should still expose tier metadata correctly."""
        root = tmp_path / "java_project_map_tiers"
        package_dir = root / "demo"
        package_dir.mkdir(parents=True)

        (package_dir / "Helper.java").write_text(
            "package demo;\n\n"
            "public class Helper {\n"
            "    public static void tool() {\n"
            "    }\n"
            "}\n",
            encoding="utf-8",
        )
        (package_dir / "App.java").write_text(
            "package demo;\n\n"
            "import static demo.Helper.tool;\n\n"
            "public class App {\n"
            "    public static void entry() {\n"
            "        tool();\n"
            "    }\n"
            "}\n",
            encoding="utf-8",
        )

        community_result = await community_server.get_project_map(
            project_root=str(root), include_complexity=False
        )
        pro_result = await pro_server.get_project_map(
            project_root=str(root), include_complexity=False
        )

        assert community_result.success is True
        assert community_result.tier_applied == "community"
        assert community_result.max_files_applied == 500
        assert community_result.max_modules_applied == 100
        assert community_result.languages.get("java") == 2

        community_modules = {module.path: module for module in community_result.modules}
        assert "demo/App.java" in community_modules
        assert "demo/Helper.java" in community_modules
        assert "App.entry" in community_modules["demo/App.java"].functions
        assert "Helper.tool" in community_modules["demo/Helper.java"].functions

        assert pro_result.success is True
        assert pro_result.tier_applied == "pro"
        assert pro_result.max_files_applied is None
        assert pro_result.max_modules_applied == 1000
        assert pro_result.languages.get("java") == 2
