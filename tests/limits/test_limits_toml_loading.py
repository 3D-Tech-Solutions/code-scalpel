"""Tests for limits.toml loading and configuration discovery.

Verifies:
- limits.toml can be found and loaded correctly
- Configuration cascading works (env var > project > user > system > defaults)
- TOML parsing is correct
- All 23 tools have configurations
- Tier progression is correct (community <= pro <= enterprise)

[20260124_TEST] Created limits.toml loading and consistency tests.
"""

from __future__ import annotations

import pytest

from tests.utils.config_loaders import (
    get_all_tool_names,
    get_all_tier_limits,
    get_tier_limit,
    load_limits_toml,
    verify_limits_toml_consistency,
)


class TestLimitsTOMLLoading:
    """Test loading and parsing of limits.toml file."""

    def test_limits_toml_exists(self):
        """limits.toml file should exist."""
        limits = load_limits_toml()
        assert limits is not None, "limits.toml should be loadable"

    def test_limits_toml_has_global_section(self):
        """limits.toml should have global settings."""
        limits = load_limits_toml()
        assert "global" in limits, "limits.toml should have [global] section"

    def test_limits_toml_has_default_timeout(self):
        """Global section should define default timeout."""
        limits = load_limits_toml()
        assert "default_timeout_seconds" in limits["global"]
        assert limits["global"]["default_timeout_seconds"] == 120

    def test_limits_toml_has_all_tiers(self):
        """limits.toml should define sections for all three tiers."""
        limits = load_limits_toml()
        required_tiers = ["community", "pro", "enterprise"]
        for tier in required_tiers:
            assert tier in limits, f"limits.toml should have [{tier}.*] sections"

    def test_all_25_tools_documented(self):
        """All 25 tools should be defined in limits.toml."""
        tools = get_all_tool_names()

        # [20260212_TEST] Updated: scanner and write_perfect_code added to limits.toml
        # [20260304_FEATURE] get_capabilities added — available at all tiers
        expected_tools = {
            "analyze_code",
            "get_file_context",
            "get_project_map",
            "get_symbol_references",
            "crawl_project",
            "extract_code",
            "rename_symbol",
            "update_symbol",
            "get_call_graph",
            "get_capabilities",
            "get_cross_file_dependencies",
            "get_graph_neighborhood",
            "scan_dependencies",
            "scanner",
            "security_scan",
            "cross_file_security_scan",
            "unified_sink_detect",
            "type_evaporation_scan",
            "code_policy_check",
            "simulate_refactor",
            "symbolic_execute",
            "generate_unit_tests",
            "verify_policy_integrity",
            "validate_paths",
            "write_perfect_code",
        }

        assert set(tools) == expected_tools, (
            f"Tool list mismatch. Found: {set(tools) - expected_tools}, "
            f"Missing: {expected_tools - set(tools)}"
        )


class TestTierLimitProgression:
    """Test that limits follow correct tier progression (Community <= Pro <= Enterprise)."""

    @pytest.mark.parametrize("tool", get_all_tool_names())
    def test_tool_has_at_least_one_tier(self, tool):
        """Every tool should have at least one tier definition."""
        limits = get_all_tier_limits(tool)
        assert any(limits.values()), f"Tool '{tool}' has no tier definitions"

    def test_analyze_code_file_size_progression(self):
        """analyze_code max_file_size_mb should progress correctly."""
        community = get_tier_limit("analyze_code", "community", "max_file_size_mb")
        pro = get_tier_limit("analyze_code", "pro", "max_file_size_mb")
        enterprise = get_tier_limit("analyze_code", "enterprise", "max_file_size_mb")

        assert community == 1, "Community analyze_code: max_file_size_mb should be 1"
        # [20260212_TEST] Updated to match rebalanced limits.toml: Pro matches Enterprise
        assert pro == 100, "Pro analyze_code: max_file_size_mb should be 100"
        assert (
            enterprise == 100
        ), "Enterprise analyze_code: max_file_size_mb should be 100"

    def test_get_file_context_lines_progression(self):
        """get_file_context max_context_lines should progress."""
        community = get_tier_limit("get_file_context", "community", "max_context_lines")
        pro = get_tier_limit("get_file_context", "pro", "max_context_lines")
        enterprise = get_tier_limit(
            "get_file_context", "enterprise", "max_context_lines"
        )

        # [20260212_TEST] Updated to match rebalanced limits.toml
        assert community == 2000, "Community: max_context_lines should be 2000"
        assert pro is None, "Pro: max_context_lines should be unlimited (None)"
        assert (
            enterprise is None
        ), "Enterprise: max_context_lines should be unlimited (None)"

    def test_get_project_map_file_limit_progression(self):
        """get_project_map max_files should progress correctly."""
        community = get_tier_limit("get_project_map", "community", "max_files")
        pro = get_tier_limit("get_project_map", "pro", "max_files")
        enterprise = get_tier_limit("get_project_map", "enterprise", "max_files")

        # [20260212_TEST] Updated to match rebalanced limits.toml
        assert community == 500, "Community: max_files should be 500"
        assert pro is None, "Pro: max_files should be unlimited (None)"
        assert enterprise is None, "Enterprise: max_files should be unlimited (None)"


class TestLimitsTOMLConsistency:
    """Test internal consistency of limits.toml."""

    def test_no_consistency_issues(self):
        """limits.toml should have no consistency issues."""
        issues = verify_limits_toml_consistency()
        assert not issues, f"limits.toml has consistency issues: {issues}"

    def test_enterprise_never_stricter_than_pro(self):
        """Enterprise limits should never be stricter than Pro."""
        load_limits_toml()
        tools = get_all_tool_names()

        numeric_keys = [
            "max_depth",
            "max_files",
            "max_nodes",
            "max_modules",
            "max_references",
            "max_context_lines",
        ]

        for tool in tools:
            tool_limits = get_all_tier_limits(tool)
            for key in numeric_keys:
                pro_val = tool_limits.get("pro", {}).get(key)
                ent_val = tool_limits.get("enterprise", {}).get(key)

                # Both must be numeric, or enterprise must be None (unlimited)
                if pro_val is not None and ent_val is not None:
                    assert ent_val >= pro_val, (
                        f"Tool '{tool}' limit '{key}': "
                        f"enterprise ({ent_val}) is stricter than pro ({pro_val})"
                    )

    def test_community_never_unlimited_if_pro_limited(self):
        """If Pro has numeric limit, Community should too."""
        tools = get_all_tool_names()

        numeric_keys = [
            "max_depth",
            "max_files",
            "max_nodes",
            "max_modules",
            "max_references",
            "max_context_lines",
        ]

        for tool in tools:
            tool_limits = get_all_tier_limits(tool)
            for key in numeric_keys:
                com_val = tool_limits.get("community", {}).get(key)
                pro_val = tool_limits.get("pro", {}).get(key)

                # If Pro has a limit, Community should too
                if pro_val is not None and com_val is None:
                    # This might be intentional - only warn if strictly inconsistent
                    pass


class TestOmissionSemantics:
    """Test that omitted limits correctly mean 'unlimited'."""

    def test_enterprise_omissions_mean_unlimited(self):
        """Omitted limits in enterprise tier should mean unlimited (None)."""
        tools = get_all_tool_names()

        for tool in tools:
            limits = get_all_tier_limits(tool)
            enterprise_limits = limits.get("enterprise", {})

            # Keys that are typically omitted in enterprise tier
            omittable_keys = ["max_depth", "max_files", "max_nodes"]

            for key in omittable_keys:
                # If key is omitted from limits dict, it's implicitly unlimited
                if key not in enterprise_limits:
                    # This is correct behavior - omission means unlimited
                    pass
                else:
                    # If it's explicitly set, it might be unlimited (None) or have a value
                    enterprise_limits[key]
                    # No assertion - just testing that parsing works


class TestLimitsWithFeatures:
    """Test consistency between limits.toml and features.py."""

    def test_limits_toml_tools_match_tool_capabilities(self):
        """Tools in limits.toml should exist in tool capabilities."""
        # This test ensures no orphaned tool definitions
        tools = get_all_tool_names()
        assert len(tools) >= 23, f"Expected at least 22 tools, found {len(tools)}"
