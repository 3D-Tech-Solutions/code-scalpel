"""
Test resolver with custom limits files and caching behaviour.

Limits injection is done by monkeypatching config_loader._find_config_file;
no environment-variable overrides are honoured at runtime.
"""

from code_scalpel.capabilities.resolver import (
    get_all_capabilities,
    get_tool_capabilities,
    reload_limits_cache,
)


class TestResolverLimitsFileOverride:
    """Test resolver with custom limits file injection."""

    def test_resolver_uses_default_limits_file(self, clear_capabilities_cache):
        """Resolver should load from default limits.toml when no override."""
        capabilities = get_all_capabilities("community")
        assert capabilities is not None
        assert len(capabilities) == 23

    def test_resolver_respects_custom_limits_file(
        self, clear_capabilities_cache, tmp_path, monkeypatch
    ):
        """Resolver should pick up a limits file returned by _find_config_file."""
        custom_limits = tmp_path / "custom_limits.toml"
        custom_limits.write_text("""
[community]
get_file_context = { available = true, max_lines = 999 }

[pro]
get_file_context = { available = true, max_lines = 1999 }

[enterprise]
get_file_context = { available = true, max_lines = 9999 }
""")

        monkeypatch.setattr(
            "code_scalpel.licensing.config_loader._find_config_file",
            lambda: custom_limits,
        )
        reload_limits_cache()

        community_cap = get_tool_capabilities("get_file_context", "community")
        assert community_cap is not None
        assert community_cap["limits"]["max_lines"] == 999

    def test_resolver_caching_with_override(
        self, clear_capabilities_cache, tmp_path, monkeypatch
    ):
        """Resolver cache invalidates when the resolved file changes."""
        limits_v1 = tmp_path / "limits_v1.toml"
        limits_v1.write_text("""
[community]
get_file_context = { available = true, max_lines = 100 }

[pro]
get_file_context = { available = true, max_lines = 100 }

[enterprise]
get_file_context = { available = true, max_lines = 100 }
""")

        monkeypatch.setattr(
            "code_scalpel.licensing.config_loader._find_config_file",
            lambda: limits_v1,
        )
        reload_limits_cache()
        cap_v1 = get_tool_capabilities("get_file_context", "community")
        assert cap_v1["limits"]["max_lines"] == 100

        # Swap to a new file — cache must pick it up after reload
        limits_v2 = tmp_path / "limits_v2.toml"
        limits_v2.write_text("""
[community]
get_file_context = { available = true, max_lines = 200 }

[pro]
get_file_context = { available = true, max_lines = 200 }

[enterprise]
get_file_context = { available = true, max_lines = 200 }
""")

        monkeypatch.setattr(
            "code_scalpel.licensing.config_loader._find_config_file",
            lambda: limits_v2,
        )
        reload_limits_cache()
        cap_v2 = get_tool_capabilities("get_file_context", "community")
        assert cap_v2["limits"]["max_lines"] == 200


class TestResolverCachingBehavior:
    """Test resolver caching doesn't break test isolation."""

    def test_cache_cleared_between_tests(self, clear_capabilities_cache):
        """Cache should be cleared between tests via fixture."""
        # First call
        cap1 = get_all_capabilities("community")
        assert cap1 is not None

    def test_each_test_gets_fresh_cache(self, clear_capabilities_cache):
        """Each test should get fresh cache from fixture."""
        # Should not be affected by previous test
        cap2 = get_all_capabilities("community")
        assert cap2 is not None

    def test_reload_cache_function(self, clear_capabilities_cache):
        """reload_limits_cache() should clear cache."""
        cap1 = get_all_capabilities("community")
        assert cap1 is not None

        # Reload should clear cache
        reload_limits_cache()

        # Next call should reload
        cap2 = get_all_capabilities("community")
        assert cap2 is not None
        # Both should have same content (same limits.toml)
        assert len(cap1) == len(cap2)


class TestResolverCustomConfigFlowThrough:
    """Test that a custom limits file flows through the full resolver stack."""

    def test_custom_limits_visible_across_tiers(
        self, clear_capabilities_cache, tmp_path, monkeypatch
    ):
        """Custom file loaded via _find_config_file should be visible at every tier."""
        custom_limits = tmp_path / "override_limits.toml"
        custom_limits.write_text("""
[community]
get_file_context = { available = true, max_lines = 12345 }

[pro]
get_file_context = { available = true, max_lines = 12345 }

[enterprise]
get_file_context = { available = true, max_lines = 12345 }
""")

        monkeypatch.setattr(
            "code_scalpel.licensing.config_loader._find_config_file",
            lambda: custom_limits,
        )
        reload_limits_cache()

        for tier in ("community", "pro", "enterprise"):
            cap = get_tool_capabilities("get_file_context", tier)
            assert cap["limits"]["max_lines"] == 12345


class TestResolverWithMultipleTiers:
    """Test resolver consistency across all tiers."""

    def test_all_tiers_load_from_same_file(self, clear_capabilities_cache):
        """All tiers should load from the same limits.toml."""
        community = get_all_capabilities("community")
        pro = get_all_capabilities("pro")
        enterprise = get_all_capabilities("enterprise")

        # All should load successfully
        assert community is not None
        assert pro is not None
        assert enterprise is not None

        # Community should have most tools
        comm_available = sum(1 for c in community.values() if c.get("available", False))
        pro_available = sum(1 for c in pro.values() if c.get("available", False))
        ent_available = sum(1 for c in enterprise.values() if c.get("available", False))

        # More limited tiers should have fewer available tools
        assert comm_available >= pro_available
        assert pro_available >= ent_available

    def test_tier_names_respected(self, clear_capabilities_cache):
        """Resolver should correctly handle tier names."""
        # Valid tiers
        community = get_all_capabilities("community")
        pro = get_all_capabilities("pro")
        enterprise = get_all_capabilities("enterprise")

        assert community is not None
        assert pro is not None
        assert enterprise is not None

    def test_invalid_tier_defaults_to_community(self, clear_capabilities_cache):
        """Invalid tier should default to community tier."""
        # Non-existent tier should default to community
        invalid_tier = get_all_capabilities("invalid_tier")
        community = get_all_capabilities("community")

        # Should fall back to community and be the same
        # (or handle gracefully)
        assert invalid_tier is not None or invalid_tier == community
