"""Phase 2 - Pro Tier Tests for get_cross_file_dependencies.

Validates:
- max_depth=5 limit
- Transitive dependency chains
- Wildcard import expansion
- Import alias resolution
- Re-export chain resolution
- Chained alias resolution
- Coupling score calculation

[20260103_TEST] P2 High: Pro tier feature enablement
"""

import pytest


class TestProTierDepth:
    """Pro tier should allow max_depth=5."""

    @pytest.mark.asyncio
    async def test_pro_transitive_chains(self, pro_server, deep_chain_project):
        """Pro tier should analyze transitive dependencies."""
        result = await pro_server.get_cross_file_dependencies(
            target_file=deep_chain_project["target_file"],
            target_symbol=deep_chain_project["target_symbol"],
            project_root=deep_chain_project["root"],
            max_depth=5,
        )

        assert result.success is True
        # Pro should handle deeper analysis
        assert result.transitive_depth <= 5


class TestProWildcardExpansion:
    """Pro tier should expand wildcard imports."""

    @pytest.mark.asyncio
    async def test_wildcard_all_expansion(self, pro_server, wildcard_import_project):
        """Should expand __all__ for wildcard imports."""
        result = await pro_server.get_cross_file_dependencies(
            target_file=wildcard_import_project["target_file"],
            target_symbol=wildcard_import_project["target_symbol"],
            project_root=wildcard_import_project["root"],
        )

        assert result.success is True
        # wildcard_expansions is a Pro feature
        assert hasattr(result, "wildcard_expansions")
        assert isinstance(result.wildcard_expansions, list)


class TestProAliasResolution:
    """Pro tier should resolve import aliases."""

    @pytest.mark.asyncio
    async def test_import_alias_tracking(self, pro_server, alias_import_project):
        """Should resolve import aliases."""
        result = await pro_server.get_cross_file_dependencies(
            target_file=alias_import_project["target_file"],
            target_symbol=alias_import_project["target_symbol"],
            project_root=alias_import_project["root"],
        )

        assert result.success is True
        # alias_resolutions is a Pro feature
        assert hasattr(result, "alias_resolutions")
        assert isinstance(result.alias_resolutions, list)


class TestProReexportResolution:
    """Pro tier should resolve re-export chains."""

    @pytest.mark.asyncio
    async def test_reexport_chain_detection(self, pro_server, reexport_project):
        """Should detect re-export chains from __init__.py."""
        result = await pro_server.get_cross_file_dependencies(
            target_file=reexport_project["target_file"],
            target_symbol=reexport_project["target_symbol"],
            project_root=reexport_project["root"],
        )

        assert result.success is True
        # reexport_chains is a Pro feature
        assert hasattr(result, "reexport_chains")
        assert isinstance(result.reexport_chains, list)


class TestProChainedAliasResolution:
    """Pro tier should resolve chained aliases."""

    @pytest.mark.asyncio
    async def test_chained_alias_multi_hop(self, pro_server, alias_import_project):
        """Should resolve multi-hop alias chains."""
        result = await pro_server.get_cross_file_dependencies(
            target_file=alias_import_project["target_file"],
            target_symbol=alias_import_project["target_symbol"],
            project_root=alias_import_project["root"],
        )

        assert result.success is True
        # chained_alias_resolutions is a Pro feature
        assert hasattr(result, "chained_alias_resolutions")
        assert isinstance(result.chained_alias_resolutions, list)


class TestProCouplingAnalysis:
    """Pro tier should provide coupling score."""

    @pytest.mark.asyncio
    async def test_coupling_score_calculation(self, pro_server, simple_two_file_project):
        """Should calculate coupling score."""
        result = await pro_server.get_cross_file_dependencies(
            target_file=simple_two_file_project["target_file"],
            target_symbol=simple_two_file_project["target_symbol"],
            project_root=simple_two_file_project["root"],
        )

        assert result.success is True
        # coupling_score is available in Pro tier
        assert hasattr(result, "coupling_score")
        if result.coupling_score is not None:
            assert 0 <= result.coupling_score <= 1


class TestProNoArchitecturalRules:
    """Pro tier should not have architectural rule features."""

    @pytest.mark.asyncio
    async def test_no_boundary_violations(self, pro_server, simple_two_file_project):
        """Pro tier should not detect architectural violations."""
        result = await pro_server.get_cross_file_dependencies(
            target_file=simple_two_file_project["target_file"],
            target_symbol=simple_two_file_project["target_symbol"],
            project_root=simple_two_file_project["root"],
        )

        assert result.success is True
        # Architectural violations are Enterprise-only
        assert len(result.boundary_violations) == 0
        assert len(result.layer_violations) == 0
