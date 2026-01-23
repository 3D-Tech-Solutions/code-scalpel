"""
Test suite for code_policy_check MCP integration and protocol compliance.

Tests verify that the tool properly integrates with the MCP (Model Context Protocol)
server infrastructure, including async execution, parameter validation, error handling,
and result format compliance.

[20260104_TEST] Created MCP integration test suite for code_policy_check tool.
"""

import inspect
import json

import pytest

from code_scalpel.mcp.server import code_policy_check


class TestMCPAsyncExecution:
    """Test async/await execution patterns required by MCP."""

    @pytest.mark.asyncio
    async def test_code_policy_check_is_async(self, tmp_path):
        """Verify code_policy_check is an async function."""
        import inspect

        assert inspect.iscoroutinefunction(
            code_policy_check
        ), "code_policy_check must be async function for MCP compatibility"

    @pytest.mark.asyncio
    async def test_async_execution_returns_result(self, tmp_path):
        """Async execution should return result object, not coroutine."""
        test_file = tmp_path / "test.py"
        test_file.write_text("x = 1\n")

        # Should be awaitable and return result directly
        result = await code_policy_check(paths=[str(test_file)])

        # Should be result object, not coroutine
        assert not inspect.iscoroutine(result), "Result should be resolved object, not coroutine"
        assert hasattr(result, "success"), "Result should have success attribute"


class TestParameterValidation:
    """Test parameter validation and error handling."""

    @pytest.mark.asyncio
    async def test_accepts_single_file_path(self, tmp_path):
        """Should accept single file path."""
        test_file = tmp_path / "test.py"
        test_file.write_text("x = 1\n")

        result = await code_policy_check(paths=[str(test_file)])

        assert result.success, "Should successfully check single file"
        assert result.files_checked == 1

    @pytest.mark.asyncio
    async def test_accepts_directory_path(self, tmp_path):
        """Should accept directory path and scan for Python files."""
        (tmp_path / "file1.py").write_text("x = 1\n")
        (tmp_path / "file2.py").write_text("y = 2\n")

        result = await code_policy_check(paths=[str(tmp_path)])

        assert result.success, "Should successfully scan directory"
        assert result.files_checked == 2

    @pytest.mark.asyncio
    async def test_accepts_multiple_paths(self, tmp_path):
        """Should accept list of multiple paths."""
        file1 = tmp_path / "test1.py"
        file1.write_text("x = 1\n")
        file2 = tmp_path / "test2.py"
        file2.write_text("y = 2\n")

        result = await code_policy_check(paths=[str(file1), str(file2)])

        assert result.success, "Should successfully check multiple files"
        assert result.files_checked == 2

    @pytest.mark.asyncio
    async def test_handles_nonexistent_path_gracefully(self, tmp_path):
        """Should handle non-existent paths without crashing."""
        nonexistent = tmp_path / "does_not_exist.py"

        # Should not raise exception
        result = await code_policy_check(paths=[str(nonexistent)])

        # Should return result (may have error or zero files checked)
        assert hasattr(result, "success"), "Should return result object"
        assert result.files_checked == 0, "Should check 0 files for nonexistent path"


class TestResultFormatCompliance:
    """Test that results conform to expected MCP result format."""

    @pytest.mark.asyncio
    async def test_result_has_required_attributes(self, tmp_path):
        """Result should have all required attributes for MCP protocol."""
        test_file = tmp_path / "test.py"
        test_file.write_text("x = 1\n")

        result = await code_policy_check(paths=[str(test_file)])

        # Core attributes required by MCP
        required_attrs = [
            "success",
            "files_checked",
            "rules_applied",
            "summary",
            "violations",
            "tier",
        ]

        for attr in required_attrs:
            assert hasattr(result, attr), f"Result missing required attribute: {attr}"

    @pytest.mark.asyncio
    async def test_result_violations_format(self, tmp_path):
        """Violations should be properly formatted list of dicts."""
        test_file = tmp_path / "test.py"
        test_file.write_text("""
try:
    pass
except:
    pass
""")

        result = await code_policy_check(paths=[str(test_file)])

        assert isinstance(result.violations, list), "Violations should be list"

        if len(result.violations) > 0:
            violation = result.violations[0]
            assert isinstance(violation, dict), "Each violation should be dict"

            # Required violation fields
            required_fields = ["rule_id", "file", "line", "message", "severity"]
            for field in required_fields:
                assert field in violation, f"Violation missing field: {field}"

    @pytest.mark.asyncio
    async def test_result_is_serializable(self, tmp_path):
        """Result should be JSON-serializable for MCP transport."""
        test_file = tmp_path / "test.py"
        test_file.write_text("x = 1\n")

        result = await code_policy_check(paths=[str(test_file)])

        # Pydantic models have .model_dump() for serialization
        assert hasattr(result, "model_dump"), "Result should have model_dump method"

        result_dict = result.model_dump()
        assert isinstance(result_dict, dict), "model_dump() should return dict"

        # Verify can be converted to JSON (basic serialization check)
        json_str = json.dumps(result_dict)
        assert len(json_str) > 0, "Result should be JSON-serializable"


class TestErrorHandling:
    """Test error handling and reporting."""

    @pytest.mark.asyncio
    async def test_empty_path_list_handled_gracefully(self, tmp_path):
        """Empty path list should be handled gracefully."""
        # Should not raise exception
        result = await code_policy_check(paths=[])

        assert hasattr(result, "success"), "Should return result object"
        assert result.files_checked == 0, "Should check 0 files for empty path list"

    @pytest.mark.asyncio
    async def test_tool_does_not_crash_on_syntax_errors(self, tmp_path):
        """Tool should handle files with syntax errors gracefully."""
        test_file = tmp_path / "syntax_error.py"
        test_file.write_text("""
def broken(
    # Missing closing parenthesis
""")

        # Should not raise exception
        result = await code_policy_check(paths=[str(test_file)])

        # Should return result (may report error in summary)
        assert hasattr(result, "success"), "Should return result object"


# [20260111_TEST] Added output metadata validation tests
class TestOutputMetadata:
    """Test output metadata fields for transparency and debugging."""

    @pytest.mark.asyncio
    async def test_result_has_tier_applied_metadata(self, tmp_path):
        """Result should include tier_applied metadata."""
        test_file = tmp_path / "test.py"
        test_file.write_text("x = 1\n")

        result = await code_policy_check(paths=[str(test_file)])

        assert hasattr(result, "tier_applied"), "Result missing tier_applied metadata"
        assert result.tier_applied in (
            "community",
            "pro",
            "enterprise",
        ), f"Invalid tier_applied value: {result.tier_applied}"

    @pytest.mark.asyncio
    async def test_result_has_files_limit_metadata(self, tmp_path):
        """Result should include files_limit_applied metadata."""
        test_file = tmp_path / "test.py"
        test_file.write_text("x = 1\n")

        result = await code_policy_check(paths=[str(test_file)])

        assert hasattr(result, "files_limit_applied"), "Result missing files_limit_applied metadata"
        # Value is int or None (None = unlimited for Enterprise)
        assert result.files_limit_applied is None or isinstance(
            result.files_limit_applied, int
        ), f"files_limit_applied should be int or None, got: {type(result.files_limit_applied)}"

    @pytest.mark.asyncio
    async def test_result_has_rules_limit_metadata(self, tmp_path):
        """Result should include rules_limit_applied metadata."""
        test_file = tmp_path / "test.py"
        test_file.write_text("x = 1\n")

        result = await code_policy_check(paths=[str(test_file)])

        assert hasattr(result, "rules_limit_applied"), "Result missing rules_limit_applied metadata"
        # Value is int or None (None = unlimited for Enterprise)
        assert result.rules_limit_applied is None or isinstance(
            result.rules_limit_applied, int
        ), f"rules_limit_applied should be int or None, got: {type(result.rules_limit_applied)}"

    @pytest.mark.asyncio
    async def test_tier_applied_matches_tier(self, tmp_path):
        """tier_applied should match tier field."""
        test_file = tmp_path / "test.py"
        test_file.write_text("x = 1\n")

        result = await code_policy_check(paths=[str(test_file)])

        assert (
            result.tier_applied == result.tier
        ), f"tier_applied ({result.tier_applied}) should match tier ({result.tier})"

    @pytest.mark.asyncio
    async def test_metadata_included_in_serialization(self, tmp_path):
        """Metadata fields should be included in model serialization."""
        test_file = tmp_path / "test.py"
        test_file.write_text("x = 1\n")

        result = await code_policy_check(paths=[str(test_file)])
        result_dict = result.model_dump()

        assert "tier_applied" in result_dict, "tier_applied missing from serialization"
        assert "files_limit_applied" in result_dict, "files_limit_applied missing from serialization"
        assert "rules_limit_applied" in result_dict, "rules_limit_applied missing from serialization"
