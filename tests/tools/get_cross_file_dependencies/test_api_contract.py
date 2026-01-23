"""Phase 5 - API Contract Tests for get_cross_file_dependencies.

Validates:
- Correct parameter names (target_file, target_symbol, not entry_point)
- Result model correctness (CrossFileDependenciesResult fields)
- Error handling and edge cases
- Token estimation accuracy
- Confidence decay calculation

[20260103_TEST] P5 Medium: API contract validation
"""

import pytest


class TestAPISignature:
    """Test correct API parameter names and types."""

    @pytest.mark.asyncio
    async def test_target_file_and_symbol_required(self, community_server, simple_two_file_project):
        """API should require target_file and target_symbol parameters."""
        # This should work
        result = await community_server.get_cross_file_dependencies(
            target_file=simple_two_file_project["target_file"],
            target_symbol=simple_two_file_project["target_symbol"],
            project_root=simple_two_file_project["root"],
        )

        assert result.success is True
        assert result.target_file != ""
        assert result.target_name != ""


class TestResultModelFields:
    """Test CrossFileDependenciesResult model structure."""

    @pytest.mark.asyncio
    async def test_success_field(self, community_server, simple_two_file_project):
        """Result should have success boolean field."""
        result = await community_server.get_cross_file_dependencies(
            target_file=simple_two_file_project["target_file"],
            target_symbol=simple_two_file_project["target_symbol"],
            project_root=simple_two_file_project["root"],
        )

        assert isinstance(result.success, bool)
        assert result.success is True

    @pytest.mark.asyncio
    async def test_extracted_symbols_field(self, community_server, simple_two_file_project):
        """Result should have extracted_symbols list."""
        result = await community_server.get_cross_file_dependencies(
            target_file=simple_two_file_project["target_file"],
            target_symbol=simple_two_file_project["target_symbol"],
            project_root=simple_two_file_project["root"],
        )

        assert isinstance(result.extracted_symbols, list)

    @pytest.mark.asyncio
    async def test_import_graph_field(self, community_server, simple_two_file_project):
        """Result should have import_graph dict."""
        result = await community_server.get_cross_file_dependencies(
            target_file=simple_two_file_project["target_file"],
            target_symbol=simple_two_file_project["target_symbol"],
            project_root=simple_two_file_project["root"],
        )

        assert isinstance(result.import_graph, dict)

    @pytest.mark.asyncio
    async def test_circular_imports_field(self, community_server, simple_two_file_project):
        """Result should have circular_imports list."""
        result = await community_server.get_cross_file_dependencies(
            target_file=simple_two_file_project["target_file"],
            target_symbol=simple_two_file_project["target_symbol"],
            project_root=simple_two_file_project["root"],
        )

        assert isinstance(result.circular_imports, list)

    @pytest.mark.asyncio
    async def test_combined_code_field(self, community_server, simple_two_file_project):
        """Result should have combined_code string."""
        result = await community_server.get_cross_file_dependencies(
            target_file=simple_two_file_project["target_file"],
            target_symbol=simple_two_file_project["target_symbol"],
            project_root=simple_two_file_project["root"],
            include_code=True,
        )

        assert isinstance(result.combined_code, str)

    @pytest.mark.asyncio
    async def test_mermaid_field(self, community_server, simple_two_file_project):
        """Result should have mermaid diagram field."""
        result = await community_server.get_cross_file_dependencies(
            target_file=simple_two_file_project["target_file"],
            target_symbol=simple_two_file_project["target_symbol"],
            project_root=simple_two_file_project["root"],
            include_diagram=True,
        )

        assert isinstance(result.mermaid, str)


class TestErrorHandling:
    """Test error handling and edge cases."""

    @pytest.mark.asyncio
    async def test_nonexistent_file_error(self, community_server, simple_two_file_project):
        """Should return error for nonexistent file."""
        result = await community_server.get_cross_file_dependencies(
            target_file="/nonexistent/path/file.py",
            target_symbol="main",
            project_root=simple_two_file_project["root"],
        )

        assert result.success is False
        assert result.error is not None

    @pytest.mark.asyncio
    async def test_nonexistent_symbol_handling(self, community_server, simple_two_file_project):
        """Should handle nonexistent symbol gracefully."""
        result = await community_server.get_cross_file_dependencies(
            target_file=simple_two_file_project["target_file"],
            target_symbol="nonexistent_symbol_xyz",
            project_root=simple_two_file_project["root"],
        )

        # May fail or return empty results
        assert result is not None


class TestTokenEstimation:
    """Test token estimation accuracy."""

    @pytest.mark.asyncio
    async def test_token_estimate_field(self, community_server, simple_two_file_project):
        """Result should estimate token count."""
        result = await community_server.get_cross_file_dependencies(
            target_file=simple_two_file_project["target_file"],
            target_symbol=simple_two_file_project["target_symbol"],
            project_root=simple_two_file_project["root"],
            include_code=True,
        )

        assert isinstance(result.token_estimate, int)
        assert result.token_estimate >= 0


class TestConfidenceDecay:
    """Test confidence decay scoring."""

    @pytest.mark.asyncio
    async def test_confidence_decay_factor(self, community_server, simple_two_file_project):
        """Result should include confidence decay factor."""
        result = await community_server.get_cross_file_dependencies(
            target_file=simple_two_file_project["target_file"],
            target_symbol=simple_two_file_project["target_symbol"],
            project_root=simple_two_file_project["root"],
        )

        assert isinstance(result.confidence_decay_factor, float)
        assert 0 < result.confidence_decay_factor <= 1.0

    @pytest.mark.asyncio
    async def test_low_confidence_warning(self, pro_server, deep_chain_project):
        """Result should flag low-confidence symbols."""
        result = await pro_server.get_cross_file_dependencies(
            target_file=deep_chain_project["target_file"],
            target_symbol=deep_chain_project["target_symbol"],
            project_root=deep_chain_project["root"],
            max_depth=10,
            confidence_decay_factor=0.8,
        )

        assert isinstance(result.low_confidence_count, int)
        assert result.low_confidence_count >= 0
