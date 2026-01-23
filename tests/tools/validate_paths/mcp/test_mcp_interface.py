"""MCP Tool Interface tests for validate_paths.

These tests validate the MCP tool registration and that invoking the tool
returns a PathValidationResult-compatible object with the contract-critical
fields needed by clients.

Note: This file intentionally avoids asserting on any transport-level envelope
format (JSON-RPC wrappers), since validate_paths returns the tool model.
"""

import pytest

from code_scalpel.mcp.server import mcp


class TestValidatePathsMCPToolAvailability:
    """Test MCP tool registration and availability."""

    def test_validate_paths_tool_registered(self):
        """validate_paths should be registered as an MCP tool."""
        # Check if tool exists in MCP registry
        # _tools is a dict with tool names as keys
        tools = mcp._tool_manager._tools
        tool_names = list(tools.keys())
        assert "validate_paths" in tool_names, f"validate_paths not found in registered tools: {tool_names}"

    def test_validate_paths_tool_has_correct_metadata(self):
        """validate_paths tool should have proper metadata."""
        # Get the tool from dict
        tools = mcp._tool_manager._tools
        tool = tools.get("validate_paths")

        assert tool is not None, "validate_paths tool not found"
        assert tool.name is not None, "Tool should have a name"
        assert tool.name == "validate_paths", f"Tool name should be 'validate_paths', got {tool.name}"
        assert tool.description is not None, "Tool should have a description"

    def test_validate_paths_has_paths_parameter(self):
        """validate_paths tool should accept 'paths' parameter."""
        tools = mcp._tool_manager._tools
        tool = tools.get("validate_paths")

        assert tool is not None, "validate_paths tool not found"
        # Tool should have input schema with paths parameter
        # Check if the tool function has 'paths' parameter
        import inspect

        sig = inspect.signature(tool.fn)
        param_names = list(sig.parameters.keys())
        assert "paths" in param_names, f"Tool should have 'paths' parameter, found: {param_names}"


class TestValidatePathsMCPInvocation:
    """Test MCP tool invocation and parameter handling."""

    @pytest.mark.asyncio
    async def test_invocation_with_valid_paths(self, tmp_path, monkeypatch):
        """Tool should accept list of valid paths and return a model."""
        monkeypatch.setenv("CODE_SCALPEL_DISABLE_LICENSE_DISCOVERY", "1")
        monkeypatch.setenv("CODE_SCALPEL_TEST_FORCE_TIER", "1")
        monkeypatch.setenv("CODE_SCALPEL_TIER", "community")

        p = tmp_path / "ok.txt"
        p.write_text("hi")

        tool = mcp._tool_manager._tools.get("validate_paths")
        assert tool is not None, "validate_paths tool not found"

        result = await tool.fn(paths=[str(p)], project_root=str(tmp_path))
        assert hasattr(result, "success")
        assert result.success is True
        assert str(p) in result.accessible

    @pytest.mark.asyncio
    async def test_invocation_with_empty_paths_list(self, tmp_path, monkeypatch):
        """Tool should handle empty paths list gracefully."""
        monkeypatch.setenv("CODE_SCALPEL_DISABLE_LICENSE_DISCOVERY", "1")
        monkeypatch.setenv("CODE_SCALPEL_TEST_FORCE_TIER", "1")
        monkeypatch.setenv("CODE_SCALPEL_TIER", "community")

        tool = mcp._tool_manager._tools.get("validate_paths")
        assert tool is not None
        result = await tool.fn(paths=[], project_root=str(tmp_path))
        assert result.success is True
        assert result.accessible == []
        assert result.inaccessible == []

    @pytest.mark.asyncio
    async def test_invocation_with_single_path(self, tmp_path, monkeypatch):
        """Tool should handle single path."""
        monkeypatch.setenv("CODE_SCALPEL_DISABLE_LICENSE_DISCOVERY", "1")
        monkeypatch.setenv("CODE_SCALPEL_TEST_FORCE_TIER", "1")
        monkeypatch.setenv("CODE_SCALPEL_TIER", "community")

        p = tmp_path / "single.txt"
        p.write_text("x")
        tool = mcp._tool_manager._tools.get("validate_paths")
        result = await tool.fn(paths=[str(p)], project_root=str(tmp_path))
        assert result.success is True
        assert str(p) in result.accessible

    @pytest.mark.asyncio
    async def test_invocation_with_multiple_paths(self, tmp_path, monkeypatch):
        """Tool should handle multiple paths (mixed accessible/inaccessible)."""
        monkeypatch.setenv("CODE_SCALPEL_DISABLE_LICENSE_DISCOVERY", "1")
        monkeypatch.setenv("CODE_SCALPEL_TEST_FORCE_TIER", "1")
        monkeypatch.setenv("CODE_SCALPEL_TIER", "community")

        ok = tmp_path / "ok.txt"
        ok.write_text("ok")
        missing = tmp_path / "missing.txt"

        tool = mcp._tool_manager._tools.get("validate_paths")
        result = await tool.fn(paths=[str(ok), str(missing)], project_root=str(tmp_path))
        assert str(ok) in result.accessible
        assert str(missing) in result.inaccessible
        assert result.success is False

    @pytest.mark.asyncio
    async def test_invocation_with_absolute_paths(self, tmp_path, monkeypatch):
        """Tool should handle absolute paths."""
        monkeypatch.setenv("CODE_SCALPEL_DISABLE_LICENSE_DISCOVERY", "1")
        monkeypatch.setenv("CODE_SCALPEL_TEST_FORCE_TIER", "1")
        monkeypatch.setenv("CODE_SCALPEL_TIER", "community")

        p = tmp_path / "abs.txt"
        p.write_text("abs")
        tool = mcp._tool_manager._tools.get("validate_paths")
        result = await tool.fn(paths=[str(p)], project_root=str(tmp_path))
        assert str(p) in result.accessible

    @pytest.mark.asyncio
    async def test_invocation_with_relative_paths(self, tmp_path, monkeypatch):
        """Tool should handle relative paths when project_root is provided."""
        monkeypatch.setenv("CODE_SCALPEL_DISABLE_LICENSE_DISCOVERY", "1")
        monkeypatch.setenv("CODE_SCALPEL_TEST_FORCE_TIER", "1")
        monkeypatch.setenv("CODE_SCALPEL_TIER", "community")

        p = tmp_path / "rel.txt"
        p.write_text("rel")
        rel = p.relative_to(tmp_path)
        tool = mcp._tool_manager._tools.get("validate_paths")
        result = await tool.fn(paths=[str(rel)], project_root=str(tmp_path))
        assert str(p) in result.accessible


class TestValidatePathsMCPResponseFormat:
    """Test MCP response format and validation."""

    @pytest.mark.asyncio
    async def test_response_has_required_fields(self, tmp_path, monkeypatch):
        """Response should contain required v1.0 contract fields."""
        monkeypatch.setenv("CODE_SCALPEL_DISABLE_LICENSE_DISCOVERY", "1")
        monkeypatch.setenv("CODE_SCALPEL_TEST_FORCE_TIER", "1")
        monkeypatch.setenv("CODE_SCALPEL_TIER", "community")

        p = tmp_path / "a.txt"
        p.write_text("a")
        tool = mcp._tool_manager._tools.get("validate_paths")
        result = await tool.fn(paths=[str(p)], project_root=str(tmp_path))

        for field in [
            "success",
            "accessible",
            "inaccessible",
            "suggestions",
            "workspace_roots",
            "is_docker",
        ]:
            assert hasattr(result, field), f"Missing required field: {field}"

        assert isinstance(result.accessible, list)
        assert isinstance(result.inaccessible, list)
        assert isinstance(result.suggestions, list)
        assert isinstance(result.workspace_roots, list)
        assert isinstance(result.is_docker, bool)


class TestValidatePathsMCPErrorHandling:
    """Test MCP error handling at tool boundary."""

    @pytest.mark.asyncio
    async def test_paths_with_null_values_are_handled(self, tmp_path, monkeypatch):
        """Tool should not crash on null/invalid path values."""
        monkeypatch.setenv("CODE_SCALPEL_DISABLE_LICENSE_DISCOVERY", "1")
        monkeypatch.setenv("CODE_SCALPEL_TEST_FORCE_TIER", "1")
        monkeypatch.setenv("CODE_SCALPEL_TIER", "community")

        tool = mcp._tool_manager._tools.get("validate_paths")
        # type: ignore[arg-type] - intentionally invalid input to test robustness
        result = await tool.fn(paths=[None], project_root=str(tmp_path))
        assert hasattr(result, "success")


class TestValidatePathsMCPTierFiltering:
    """Test response filtering based on tier."""

    @pytest.mark.asyncio
    async def test_community_tier_100_paths_enforced_in_mcp(self, tmp_path, monkeypatch):
        """Community tier should truncate to 100 paths and signal truncation."""
        monkeypatch.setenv("CODE_SCALPEL_DISABLE_LICENSE_DISCOVERY", "1")
        monkeypatch.setenv("CODE_SCALPEL_TEST_FORCE_TIER", "1")
        monkeypatch.setenv("CODE_SCALPEL_TIER", "community")

        # Create 101 paths; only first 100 should be checked.
        paths = [str(tmp_path / f"f{i}.txt") for i in range(101)]
        tool = mcp._tool_manager._tools.get("validate_paths")
        result = await tool.fn(paths=paths, project_root=str(tmp_path))

        assert result.truncated is True
        assert result.paths_received == 101
        assert result.paths_checked == 100
        assert result.max_paths_applied == 100


class TestValidatePathsMCPEnvelopeFormat:
    """This tool returns the model directly; envelope tests belong to transport suites."""

    def test_returns_model_not_envelope(self):
        """Tool fn should be an async callable returning the tool model."""
        tool = mcp._tool_manager._tools.get("validate_paths")
        assert tool is not None
        assert callable(tool.fn)


class TestValidatePathsMCPCommunityTierInterface:
    """Test MCP interface for Community tier."""

    @pytest.mark.asyncio
    async def test_community_tier_gets_core_response(self, tmp_path, monkeypatch):
        """Community tier should receive core response fields."""
        monkeypatch.setenv("CODE_SCALPEL_DISABLE_LICENSE_DISCOVERY", "1")
        monkeypatch.setenv("CODE_SCALPEL_TEST_FORCE_TIER", "1")
        monkeypatch.setenv("CODE_SCALPEL_TIER", "community")

        p = tmp_path / "core.txt"
        p.write_text("core")
        tool = mcp._tool_manager._tools.get("validate_paths")
        result = await tool.fn(paths=[str(p)], project_root=str(tmp_path))
        assert result.success is True
        assert isinstance(result.workspace_roots, list)


class TestValidatePathsMCPProTierInterface:
    """Test MCP interface for Pro tier."""

    @pytest.mark.asyncio
    async def test_pro_tier_unlimited_paths_in_mcp(self, tmp_path, monkeypatch):
        """Pro tier should not truncate path list."""
        monkeypatch.setenv("CODE_SCALPEL_DISABLE_LICENSE_DISCOVERY", "1")
        monkeypatch.setenv("CODE_SCALPEL_TEST_FORCE_TIER", "1")
        monkeypatch.setenv("CODE_SCALPEL_TIER", "pro")

        # 150 paths should not truncate at pro.
        paths = [str(tmp_path / f"p{i}.txt") for i in range(150)]
        tool = mcp._tool_manager._tools.get("validate_paths")
        result = await tool.fn(paths=paths, project_root=str(tmp_path))
        assert result.truncated is None


class TestValidatePathsMCPEnterpriseTierInterface:
    """Test MCP interface for Enterprise tier."""

    @pytest.mark.asyncio
    async def test_enterprise_tier_includes_security_diagnostics_fields(self, tmp_path, monkeypatch):
        """Enterprise tier should include security diagnostics fields (may be empty)."""
        monkeypatch.setenv("CODE_SCALPEL_DISABLE_LICENSE_DISCOVERY", "1")
        monkeypatch.setenv("CODE_SCALPEL_TEST_FORCE_TIER", "1")
        monkeypatch.setenv("CODE_SCALPEL_TIER", "enterprise")

        tool = mcp._tool_manager._tools.get("validate_paths")
        result = await tool.fn(paths=["../escape.txt"], project_root=str(tmp_path))
        assert hasattr(result, "traversal_vulnerabilities")
        assert hasattr(result, "boundary_violations")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
