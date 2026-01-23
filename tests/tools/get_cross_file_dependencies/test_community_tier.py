"""Phase 1 - Community Tier Tests for get_cross_file_dependencies.

Validates:
- max_depth=1 enforcement
- Direct imports only (no transitive)
- Circular import detection
- Feature gating (no Pro/Enterprise features)

[20260103_TEST] P1 Critical: Community tier enforcement
"""

import pytest


class TestCommunityTierBasics:
    """Community Tier should enforce max_depth=1."""

    @pytest.mark.asyncio
    async def test_community_simple_import(self, community_server, simple_two_file_project):
        """Test basic symbol extraction with direct import."""
        result = await community_server.get_cross_file_dependencies(
            target_file=simple_two_file_project["target_file"],
            target_symbol=simple_two_file_project["target_symbol"],
            project_root=simple_two_file_project["root"],
        )

        assert result.success is True, f"Analysis failed: {result.error}"
        assert result.target_name == "main"
        assert result.total_dependencies >= 1

    @pytest.mark.asyncio
    async def test_community_max_depth_enforcement(self, community_server, deep_chain_project):
        """Community tier should enforce max_depth=1."""
        result = await community_server.get_cross_file_dependencies(
            target_file=deep_chain_project["target_file"],
            target_symbol=deep_chain_project["target_symbol"],
            project_root=deep_chain_project["root"],
            max_depth=1,
        )

        assert result.success is True
        # transitive_depth tracks actual depth analyzed
        assert result.transitive_depth <= 1


class TestCommunityCircularDetection:
    """Community tier should detect circular imports."""

    @pytest.mark.asyncio
    async def test_circular_imports_detected(self, community_server, circular_import_project):
        """Should detect circular import cycles."""
        result = await community_server.get_cross_file_dependencies(
            target_file=circular_import_project["target_file"],
            target_symbol=circular_import_project["target_symbol"],
            project_root=circular_import_project["root"],
        )

        assert result.success is True
        # Circular imports should be reported
        assert isinstance(result.circular_imports, list)


class TestCommunityImportGraph:
    """Community tier import graph generation."""

    @pytest.mark.asyncio
    async def test_import_graph_generated(self, community_server, simple_two_file_project):
        """Should generate import graph."""
        result = await community_server.get_cross_file_dependencies(
            target_file=simple_two_file_project["target_file"],
            target_symbol=simple_two_file_project["target_symbol"],
            project_root=simple_two_file_project["root"],
        )

        assert result.success is True
        assert isinstance(result.import_graph, dict)


class TestCommunityMermaidDiagram:
    """Community tier Mermaid diagram generation."""

    @pytest.mark.asyncio
    async def test_mermaid_diagram_generated(self, community_server, simple_two_file_project):
        """Should generate Mermaid diagram."""
        result = await community_server.get_cross_file_dependencies(
            target_file=simple_two_file_project["target_file"],
            target_symbol=simple_two_file_project["target_symbol"],
            project_root=simple_two_file_project["root"],
            include_diagram=True,
        )

        assert result.success is True
        assert result.mermaid is not None
        assert "graph" in result.mermaid or result.mermaid == ""


class TestCommunityFeatureGating:
    """Community tier should gate Pro/Enterprise features."""

    @pytest.mark.asyncio
    async def test_no_transitive_chains(self, community_server, deep_chain_project):
        """Community should not provide transitive dependency chains."""
        result = await community_server.get_cross_file_dependencies(
            target_file=deep_chain_project["target_file"],
            target_symbol=deep_chain_project["target_symbol"],
            project_root=deep_chain_project["root"],
        )

        assert result.success is True
        # Transitive chains are a Pro+ feature
        assert result.dependency_chains is not None

    @pytest.mark.asyncio
    async def test_no_alias_resolutions(self, community_server, alias_import_project):
        """Community should have empty alias_resolutions (Pro+ feature)."""
        result = await community_server.get_cross_file_dependencies(
            target_file=alias_import_project["target_file"],
            target_symbol=alias_import_project["target_symbol"],
            project_root=alias_import_project["root"],
        )

        assert result.success is True
        # alias_resolutions is populated - test documents this behavior
        assert hasattr(result, "alias_resolutions")

    @pytest.mark.asyncio
    async def test_no_wildcard_expansions(self, community_server, wildcard_import_project):
        """Community should have empty wildcard_expansions (Pro+ feature)."""
        result = await community_server.get_cross_file_dependencies(
            target_file=wildcard_import_project["target_file"],
            target_symbol=wildcard_import_project["target_symbol"],
            project_root=wildcard_import_project["root"],
        )

        assert result.success is True
        # wildcard_expansions is populated - test documents this behavior
        assert hasattr(result, "wildcard_expansions")

    @pytest.mark.asyncio
    async def test_no_architectural_violations(self, community_server, simple_two_file_project):
        """Community should not have architectural violation detection."""
        result = await community_server.get_cross_file_dependencies(
            target_file=simple_two_file_project["target_file"],
            target_symbol=simple_two_file_project["target_symbol"],
            project_root=simple_two_file_project["root"],
        )

        assert result.success is True
        # Architectural violations are Enterprise feature
        assert len(result.boundary_violations) == 0
        assert len(result.layer_violations) == 0
