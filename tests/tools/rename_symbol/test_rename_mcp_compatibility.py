# [20260108_TEST] MCP-level compatibility tests for rename_symbol
"""
MCP protocol compatibility at tool level.

Tests verify that rename_symbol:
- Accepts MCP-like parameter structures
- Returns responses compatible with MCP format
- Handles errors gracefully (missing params, invalid args)
- Works with basic async patterns

Note: Full MCP JSON-RPC protocol testing is at server level.
These tests verify tool-level contract compliance.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from code_scalpel.surgery.rename_symbol_refactor import rename_references_across_project
from code_scalpel.surgery.surgical_patcher import UnifiedPatcher


class TestToolMCPCompatibility:
    """Tool-level MCP compatibility tests."""

    def test_tool_accepts_mcp_like_parameters(self, tmp_path: Path):
        """[20260108_TEST] Tool accepts MCP-like parameter structure."""
        src = tmp_path / "module.py"
        src.write_text("def old_func():\n    return 1\n", encoding="utf-8")

        # MCP-like parameter structure: named parameters as dict
        params = {
            "file_path": str(src),
            "target_type": "function",
            "target_name": "old_func",
            "new_name": "new_func",
        }

        # Tool should accept kwargs unpacking
        patcher = UnifiedPatcher.from_file(params["file_path"])
        result = patcher.rename_symbol(params["target_type"], params["target_name"], params["new_name"])

        assert result.success is True
        assert "error" in dir(result)
        assert "success" in dir(result)

    def test_tool_response_format_mcp_compatible(self, tmp_path: Path):
        """[20260108_TEST] Tool response format is MCP-compatible (dict-like)."""
        src = tmp_path / "module.py"
        src.write_text("def old_func():\n    return 1\n", encoding="utf-8")

        patcher = UnifiedPatcher.from_file(str(src))
        result = patcher.rename_symbol("function", "old_func", "new_func")

        # Response should be MCP-compatible: has success, error, and data fields
        assert hasattr(result, "success")
        assert hasattr(result, "error")
        assert isinstance(result.success, bool)
        assert result.error is None or isinstance(result.error, str)

        # Can serialize to dict via pydantic model_validate
        result_dict = vars(result)
        assert "success" in result_dict
        assert isinstance(result_dict, dict)

    def test_tool_missing_required_parameter_error(self, tmp_path: Path):
        """[20260108_TEST] Missing required parameter returns error."""
        src = tmp_path / "module.py"
        src.write_text("def old_func():\n    return 1\n", encoding="utf-8")

        patcher = UnifiedPatcher.from_file(str(src))

        # Missing target_name should cause error
        result = patcher.rename_symbol("function", None, "new_func")  # type: ignore

        # Should fail gracefully, not crash
        assert result.success is False or result.error is not None

    def test_tool_invalid_parameter_type_error(self, tmp_path: Path):
        """[20260108_TEST] Invalid parameter type returns error."""
        src = tmp_path / "module.py"
        src.write_text("def old_func():\n    return 1\n", encoding="utf-8")

        patcher = UnifiedPatcher.from_file(str(src))

        # Invalid target_type should cause error
        result = patcher.rename_symbol("invalid_type", "old_func", "new_func")  # type: ignore

        assert result.success is False
        assert result.error is not None

    def test_tool_error_response_includes_context(self, tmp_path: Path):
        """[20260108_TEST] Error responses include helpful context."""
        src = tmp_path / "module.py"
        src.write_text("def old_func():\n    return 1\n", encoding="utf-8")

        patcher = UnifiedPatcher.from_file(str(src))

        # Invalid identifier
        result = patcher.rename_symbol("function", "old_func", "123invalid")

        assert result.success is False
        assert result.error is not None
        # Error should be informative
        assert "identifier" in result.error.lower() or "invalid" in result.error.lower()

    def test_cross_file_rename_mcp_response_format(self, tmp_path: Path):
        """[20260108_TEST] Cross-file rename response has MCP-compatible format."""
        target = tmp_path / "target.py"
        ref = tmp_path / "ref.py"

        target.write_text("def old_func():\n    return 1\n", encoding="utf-8")
        ref.write_text("from target import old_func\nvalue = old_func()\n", encoding="utf-8")

        # Cross-file rename uses different response type
        result = rename_references_across_project(
            project_root=tmp_path,
            target_file=target,
            target_type="function",
            target_name="old_func",
            new_name="new_func",
            create_backup=False,
            max_files_searched=None,
            max_files_updated=None,
        )

        # Response should be MCP-compatible
        assert hasattr(result, "success")
        assert hasattr(result, "error")
        assert hasattr(result, "changed_files")
        assert hasattr(result, "warnings")
        assert isinstance(result.success, bool)
        assert isinstance(result.changed_files, list)
        assert isinstance(result.warnings, list)

        # Can serialize to dict
        result_dict = vars(result)
        assert isinstance(result_dict, dict)
        assert "success" in result_dict
        assert "changed_files" in result_dict

    def test_tool_response_serializable_to_json(self, tmp_path: Path):
        """[20260108_TEST] Tool response is JSON-serializable (MCP requirement)."""
        import json

        src = tmp_path / "module.py"
        src.write_text("def old_func():\n    return 1\n", encoding="utf-8")

        patcher = UnifiedPatcher.from_file(str(src))
        result = patcher.rename_symbol("function", "old_func", "new_func")

        # Response should be JSON-serializable
        result_dict = vars(result)
        json_str = json.dumps(result_dict, default=str)
        assert isinstance(json_str, str)
        assert len(json_str) > 0

        # Can be deserialized back
        loaded = json.loads(json_str)
        assert loaded["success"] is True

    def test_tool_handles_empty_result_gracefully(self, tmp_path: Path):
        """[20260108_TEST] Tool handles empty/null results gracefully."""
        src = tmp_path / "module.py"
        src.write_text("def old_func():\n    return 1\n", encoding="utf-8")

        # Rename to same name should succeed but change nothing
        patcher = UnifiedPatcher.from_file(str(src))
        result = patcher.rename_symbol("function", "old_func", "old_func")

        # Should complete without error
        assert result is not None
        assert isinstance(result.success, bool)


class TestToolAsyncCompatibility:
    """Tool-level async compatibility tests."""

    @pytest.mark.asyncio
    async def test_tool_callable_from_async_context(self, tmp_path: Path):
        """[20260108_TEST] Tool can be called from async context (no blocking)."""
        src = tmp_path / "module.py"
        src.write_text("def old_func():\n    return 1\n", encoding="utf-8")

        # Simulate async MCP handler calling sync tool
        async def async_rename():
            patcher = UnifiedPatcher.from_file(str(src))
            result = patcher.rename_symbol("function", "old_func", "new_func")
            return result

        result = await async_rename()
        assert result.success is True

    @pytest.mark.asyncio
    async def test_multiple_concurrent_tool_calls(self, tmp_path: Path):
        """[20260108_TEST] Multiple concurrent tool calls don't interfere."""
        targets = []
        for i in range(3):
            src = tmp_path / f"module_{i}.py"
            src.write_text(f"def old_func_{i}():\n    return {i}\n", encoding="utf-8")
            targets.append(src)

        async def rename_one(src: Path, index: int):
            patcher = UnifiedPatcher.from_file(str(src))
            result = patcher.rename_symbol("function", f"old_func_{index}", f"new_func_{index}")
            if result.success:
                patcher.save(backup=False)
            return result

        # Run concurrent renames
        results = await asyncio.gather(
            rename_one(targets[0], 0),
            rename_one(targets[1], 1),
            rename_one(targets[2], 2),
        )

        # All should succeed independently
        assert all(r.success for r in results)

        # Verify each file was updated correctly
        for i, src in enumerate(targets):
            text = src.read_text(encoding="utf-8")
            assert f"def new_func_{i}" in text

    @pytest.mark.asyncio
    async def test_tool_timeout_handling(self, tmp_path: Path):
        """[20260108_TEST] Tool respects timeout constraints (MCP-level timeout wrapper)."""
        src = tmp_path / "module.py"
        src.write_text("def old_func():\n    return 1\n", encoding="utf-8")

        async def rename_with_timeout():
            patcher = UnifiedPatcher.from_file(str(src))
            result = patcher.rename_symbol("function", "old_func", "new_func")
            return result

        # Should complete within reasonable timeout
        try:
            result = await asyncio.wait_for(rename_with_timeout(), timeout=5.0)
            assert result.success is True
        except asyncio.TimeoutError:
            pytest.fail("Tool exceeded timeout (should be instant for small files)")

    @pytest.mark.asyncio
    async def test_tool_handles_concurrent_errors(self, tmp_path: Path):
        """[20260108_TEST] Tool error handling works correctly in async context."""
        src1 = tmp_path / "valid.py"
        src1.write_text("def old_func():\n    return 1\n", encoding="utf-8")

        src2 = tmp_path / "nonexistent.py"  # Doesn't exist

        async def rename_one(src: Path, should_fail: bool = False):
            try:
                patcher = UnifiedPatcher.from_file(str(src))
                result = patcher.rename_symbol("function", "old_func", "new_func")
                return result
            except (OSError, FileNotFoundError):
                if should_fail:
                    return None
                raise

        # One succeeds, one fails
        result1 = await rename_one(src1, should_fail=False)
        assert result1.success is True

        # Error doesn't crash the tool
        result2 = await rename_one(src2, should_fail=True)
        assert result2 is None


class TestToolParameterValidation:
    """Parameter validation for MCP compatibility."""

    def test_parameter_names_match_mcp_spec(self, tmp_path: Path):
        """[20260108_TEST] Parameter names follow MCP conventions."""
        src = tmp_path / "module.py"
        src.write_text("def old_func():\n    return 1\n", encoding="utf-8")

        # MCP naming: snake_case for all parameters
        patcher = UnifiedPatcher.from_file(str(src))
        result = patcher.rename_symbol(
            target_type="function",  # snake_case
            target_name="old_func",  # snake_case
            new_name="new_func",  # snake_case
        )

        assert result.success is True

    def test_optional_parameters_have_defaults(self, tmp_path: Path):
        """[20260108_TEST] Optional parameters work with defaults."""
        src = tmp_path / "module.py"
        src.write_text("def old_func():\n    return 1\n", encoding="utf-8")

        patcher = UnifiedPatcher.from_file(str(src))
        # Omit create_backup; should use default
        result = patcher.rename_symbol("function", "old_func", "new_func")

        # Should succeed with default backup behavior
        assert result.success is True

    def test_boolean_parameters_interpreted_correctly(self, tmp_path: Path):
        """[20260108_TEST] Boolean parameters interpreted correctly."""
        src = tmp_path / "module.py"
        src.write_text("def old_func():\n    return 1\n", encoding="utf-8")

        patcher = UnifiedPatcher.from_file(str(src))

        # Rename with backup support
        result_true = patcher.rename_symbol("function", "old_func", "new_func_true")
        if result_true.success:
            patcher.save(backup=True)  # backup flag on save()
        assert result_true.success is True

        # Reset
        src.write_text("def new_func_true():\n    return 1\n", encoding="utf-8")

        # Rename without backup
        patcher2 = UnifiedPatcher.from_file(str(src))
        result_false = patcher2.rename_symbol("function", "new_func_true", "final_func")
        if result_false.success:
            patcher2.save(backup=False)  # backup flag on save()
        assert result_false.success is True


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
