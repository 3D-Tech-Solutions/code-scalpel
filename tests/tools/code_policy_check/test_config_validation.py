"""
Configuration validation tests for code_policy_check tool.

CRITICAL: These tests MUST pass before any other tests.
They verify the tool correctly loads tier limits from .code-scalpel/limits.toml.
"""

from pathlib import Path

import pytest

from code_scalpel.licensing.features import get_tool_capabilities


class TestConfigurationLoading:
    """Verify tool reads configuration from .code-scalpel/limits.toml."""

    def test_loads_limits_from_code_scalpel_dir(self):
        """
        CRITICAL: Verify tool reads .code-scalpel/limits.toml.

        Expected behavior:
        - Tool should load limits from .code-scalpel/limits.toml
        - Limits should differ per tier
        - Configuration should override hardcoded defaults
        """
        # Get capabilities for all tiers
        community_caps = get_tool_capabilities("code_policy_check", "community")
        pro_caps = get_tool_capabilities("code_policy_check", "pro")
        enterprise_caps = get_tool_capabilities("code_policy_check", "enterprise")

        # Verify Community tier
        assert community_caps is not None, "Community capabilities not loaded"
        assert "limits" in community_caps, "limits not in Community capabilities"
        assert "max_files" in community_caps["limits"], "max_files not in Community limits"
        assert "max_rules" in community_caps["limits"], "max_rules not in Community limits"

        # Verify Pro tier
        assert pro_caps is not None, "Pro capabilities not loaded"
        assert "limits" in pro_caps, "limits not in Pro capabilities"
        assert "max_files" in pro_caps["limits"], "max_files not in Pro limits"

        # Verify Enterprise tier
        assert enterprise_caps is not None, "Enterprise capabilities not loaded"
        assert "limits" in enterprise_caps, "limits not in Enterprise capabilities"

        # Verify tier progression (limits increase or become unlimited)
        assert community_caps["limits"]["max_files"] < pro_caps["limits"].get(
            "max_files", float("inf")
        ), "Pro max_files should be higher than Community"

    def test_community_max_files_100_from_config(self):
        """
        Verify Community tier max_files = 100 per .code-scalpel/limits.toml.

        Configuration source: .code-scalpel/limits.toml:244-248
        [community.code_policy_check]
        max_files = 100
        """
        caps = get_tool_capabilities("code_policy_check", "community")

        assert (
            caps["limits"]["max_files"] == 100
        ), f"Community max_files should be 100 (from limits.toml), got {caps['limits'].get('max_files')}"

    def test_community_max_rules_50_from_config(self):
        """
        Verify Community tier max_rules = 50 per .code-scalpel/limits.toml.

        Configuration source: .code-scalpel/limits.toml:244-248
        [community.code_policy_check]
        max_rules = 50
        """
        caps = get_tool_capabilities("code_policy_check", "community")

        assert (
            caps["limits"]["max_rules"] == 50
        ), f"Community max_rules should be 50 (from limits.toml), got {caps['limits'].get('max_rules')}"

    def test_pro_max_files_1000_from_config(self):
        """
        Verify Pro tier max_files = 1000 (NOT unlimited) per .code-scalpel/limits.toml.

        Configuration source: .code-scalpel/limits.toml:250-254
        [pro.code_policy_check]
        max_files = 1000

        CRITICAL: Pro is NOT unlimited - it has a 1000 file cap.
        """
        caps = get_tool_capabilities("code_policy_check", "pro")

        assert (
            caps["limits"]["max_files"] == 1000
        ), f"Pro max_files should be 1000 (from limits.toml), got {caps['limits'].get('max_files')}"

    def test_pro_max_rules_200_from_config(self):
        """
        Verify Pro tier max_rules = 200 per .code-scalpel/limits.toml.

        Configuration source: .code-scalpel/limits.toml:250-254
        [pro.code_policy_check]
        max_rules = 200
        """
        caps = get_tool_capabilities("code_policy_check", "pro")

        assert (
            caps["limits"]["max_rules"] == 200
        ), f"Pro max_rules should be 200 (from limits.toml), got {caps['limits'].get('max_rules')}"

    def test_pro_compliance_disabled_from_config(self):
        """
        Verify Pro tier compliance_enabled = false per .code-scalpel/limits.toml.

        Configuration source: .code-scalpel/limits.toml:250-254
        [pro.code_policy_check]
        compliance_enabled = false

        CRITICAL: Pro tier CANNOT access HIPAA/SOC2/GDPR/PCI-DSS.
        Only Enterprise tier has compliance_enabled = true.
        """
        caps = get_tool_capabilities("code_policy_check", "pro")

        assert (
            caps["limits"].get("compliance_enabled") is False
        ), "Pro tier should have compliance_enabled=false (Enterprise-only feature)"

    def test_enterprise_unlimited_files_from_config(self):
        """
        Verify Enterprise tier has unlimited files per .code-scalpel/limits.toml.

        Configuration source: .code-scalpel/limits.toml:256-261
        [enterprise.code_policy_check]
        # max_files and max_rules unlimited - omit

        When limits are omitted in limits.toml, they should be None or very high value.
        """
        caps = get_tool_capabilities("code_policy_check", "enterprise")

        # Enterprise should have no max_files limit (None or very high)
        max_files = caps["limits"].get("max_files")
        assert (
            max_files is None or max_files >= 1000000
        ), f"Enterprise max_files should be unlimited (None or very high), got {max_files}"

    def test_enterprise_compliance_enabled_from_config(self):
        """
        Verify Enterprise tier compliance_enabled = true per .code-scalpel/limits.toml.

        Configuration source: .code-scalpel/limits.toml:256-261
        [enterprise.code_policy_check]
        compliance_enabled = true
        """
        caps = get_tool_capabilities("code_policy_check", "enterprise")

        assert caps["limits"].get("compliance_enabled") is True, "Enterprise tier should have compliance_enabled=true"

    def test_config_file_exists(self):
        """Verify .code-scalpel/limits.toml exists in project."""
        # Try common locations
        possible_paths = [
            Path.cwd() / ".code-scalpel" / "limits.toml",
            Path(__file__).parent.parent.parent.parent / ".code-scalpel" / "limits.toml",
        ]

        exists = any(p.exists() for p in possible_paths)
        assert exists, f".code-scalpel/limits.toml not found in: {[str(p) for p in possible_paths]}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
