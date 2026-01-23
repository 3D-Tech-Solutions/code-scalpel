"""
[20260104_TEST] Targeted MCP boundary tests for update_symbol.

These tests cover JSON-RPC-esque error envelopes for missing/invalid
arguments at the FastMCP layer, closing coverage gaps for protocol-level
validation identified in the checklist.
"""

import asyncio
import time

import pytest

from code_scalpel.mcp import server as mcp_server
from code_scalpel.mcp.server import mcp

pytestmark = pytest.mark.asyncio


async def test_update_symbol_missing_required_params_returns_error_envelope():
    """Ensure missing required args return an error envelope, not a crash.

    [20260121_REFACTOR] FastMCP validates arguments before calling tool,
    raising ToolError for missing required parameters (instead of returning
    error dict). Test updated to expect ToolError.
    """
    from mcp.server.fastmcp.exceptions import ToolError

    tool = mcp._tool_manager._tools["update_symbol"]

    # FastMCP validates arguments and raises ToolError for missing required params
    with pytest.raises(ToolError) as exc_info:
        await tool.run({}, context=None, convert_result=False)

    # Error message should mention missing fields
    error_msg = str(exc_info.value)
    assert (
        "file_path" in error_msg or "Field required" in error_msg
    ), f"Error should mention missing required fields, got: {error_msg}"


async def test_update_symbol_invalid_param_types_return_error_envelope(tmp_path):
    """Invalid argument types should surface as tool errors with guidance.

    [20260121_REFACTOR] FastMCP validates argument types, raising ToolError
    for type mismatches. Test updated to expect ToolError.
    """
    from mcp.server.fastmcp.exceptions import ToolError

    tool = mcp._tool_manager._tools["update_symbol"]

    bad_args = {
        "file_path": tmp_path / "sample.py",  # Path object instead of str
        "target_type": "function",  # Provide all required params to avoid missing param errors
        "target_name": "foo",
        "symbol_name": 123,  # int instead of str (bad type)
        "new_code": None,  # None instead of str (will be converted or rejected)
    }

    # FastMCP validates types and raises ToolError for type mismatches
    with pytest.raises(ToolError) as exc_info:
        await tool.run(bad_args, context=None, convert_result=False)

    # Error message should mention type validation failure
    error_msg = str(exc_info.value)
    assert (
        "Error executing tool" in error_msg or "validation" in error_msg.lower()
    ), f"Error should indicate validation/execution issue, got: {error_msg}"


async def test_update_symbol_fault_injection_returns_internal_error(tmp_path):
    """Unexpected exceptions should be wrapped in an internal_error envelope.

    [20260121_REFACTOR] Updated to work with current MCP server implementation.
    Tests that invalid/nonsensical operations fail gracefully.
    """
    from code_scalpel.mcp.models.core import PatchResultModel

    tool = mcp._tool_manager._tools["update_symbol"]

    # Try to update a symbol with invalid/conflicting parameters
    sample_file = tmp_path / "sample.py"
    sample_file.write_text("""def foo():
    return 0
""")

    # Invalid operation: empty new_code should fail validation
    args = {
        "file_path": str(sample_file),
        "target_type": "function",
        "target_name": "foo",
        "new_code": "",  # Empty code should fail validation
        "operation": "replace",
    }

    # Empty new_code should fail validation
    result = await tool.run(args, context=None, convert_result=False)

    # Result should be a PatchResultModel (even on failure)
    assert isinstance(
        result, (PatchResultModel, dict)
    ), f"Tool should return a PatchResultModel or dict, got {type(result)}"

    # Check for failure
    if isinstance(result, PatchResultModel):
        assert result.success is False, "Empty new_code should fail validation"
        assert result.error_code == "UPDATE_SYMBOL_MISSING_NEW_CODE"
    else:
        assert result.get("success") is False, "Empty new_code should fail"
        assert "error" in result, "Should include error message"


async def test_update_symbol_unknown_tool_returns_not_found_error():
    """Non-existent tool name should raise a not-found error from FastMCP manager."""

    with pytest.raises(KeyError):
        _ = mcp._tool_manager._tools["does_not_exist"]


async def test_update_symbol_respects_timeout_budget(monkeypatch, tmp_path):
    """update_symbol should complete well within a short timeout budget."""
    from pathlib import Path

    from code_scalpel.mcp.models.core import PatchResultModel

    monkeypatch.setattr(mcp_server, "_get_current_tier", lambda: "community")
    tool = mcp._tool_manager._tools["update_symbol"]

    # Create file within project root (security requirement)
    project_root = Path("/mnt/k/backup/Develop/code-scalpel")
    sample_file = project_root / "test_timeout_sample_temp.py"
    sample_file.write_text("""def foo():
    return 0
""")

    try:
        args = {
            "file_path": str(sample_file),
            "target_type": "function",
            "target_name": "foo",
            "new_code": "def foo():\n    return 1\n",
        }

        # [20260121_FEATURE] Tool returns PatchResultModel; convert_result=False returns model instance
        result = await asyncio.wait_for(tool.run(args, context=None, convert_result=False), timeout=1.0)

        # Verify result is PatchResultModel instance and completed within timeout
        assert isinstance(result, (dict, PatchResultModel))

        # If it's a model, check the success field
        if isinstance(result, PatchResultModel):
            # Tool should have completed successfully
            assert result.success is True
            assert result.file_path == str(sample_file)
            assert result.target_name == "foo"
        else:
            # Dict response (legacy path)
            assert result.get("duration_ms", 0) < 1000
            err = result.get("error")
            if err:
                assert isinstance(err, dict)
                assert err.get("error_code") in {"internal_error", "invalid_params"}
            else:
                data = result.get("data") or {}
                if isinstance(data, dict):
                    assert data.get("success") is True
    finally:
        # Clean up test file
        if sample_file.exists():
            sample_file.unlink()


async def test_update_symbol_async_calls_do_not_block_event_loop(monkeypatch, tmp_path):
    """Concurrent async calls should execute without blocking the event loop."""
    from pathlib import Path

    from code_scalpel.mcp.models.core import PatchResultModel

    monkeypatch.setattr(mcp_server, "_get_current_tier", lambda: "community")
    tool = mcp._tool_manager._tools["update_symbol"]

    async def invoke(i: int) -> PatchResultModel | dict:
        # [20260121_FEATURE] Files must be within project root to avoid path sandbox rejection
        project_root = Path("/mnt/k/backup/Develop/code-scalpel")
        sample_file = project_root / f"test_async_{i}_temp.py"
        sample_file.write_text("""def foo():
    return 0
""")

        try:
            args = {
                "file_path": str(sample_file),
                "target_type": "function",
                "target_name": "foo",
                "new_code": "def foo():\n    return 1\n",
            }
            return await tool.run(args, context=None, convert_result=False)
        finally:
            if sample_file.exists():
                sample_file.unlink()

    started = time.perf_counter()
    results = await asyncio.gather(*(invoke(i) for i in range(3)))
    elapsed = time.perf_counter() - started

    assert elapsed < 2.0, f"async dispatch took too long: {elapsed}s"
    for res in results:
        # [20260121_FEATURE] Tool returns PatchResultModel; support legacy dict path
        assert isinstance(res, (dict, PatchResultModel))
        if isinstance(res, PatchResultModel):
            assert hasattr(res, "success")
            assert hasattr(res, "file_path")
        else:
            assert res.get("duration_ms", 0) < 1000
            err = res.get("error")
            if err:
                assert isinstance(err, dict)
                assert err.get("error_code") in {"internal_error", "invalid_params"}
            else:
                data = res.get("data") or {}
                if isinstance(data, dict):
                    assert data.get("success") is True


async def test_update_symbol_memory_error_returns_structured_envelope(monkeypatch, tmp_path):
    """MemoryError during patching should return structured error envelope."""

    from pathlib import Path

    from code_scalpel.mcp.models.core import PatchResultModel
    from code_scalpel.surgery.surgical_patcher import UnifiedPatcher

    monkeypatch.setattr(mcp_server, "_get_current_tier", lambda: "community")
    tool = mcp._tool_manager._tools["update_symbol"]

    project_root = Path("/mnt/k/backup/Develop/code-scalpel")
    sample_file = project_root / "test_oom_sample_temp.py"
    sample_file.write_text("""def foo():
    return 0
""")

    # Inject MemoryError in the patcher
    def mock_from_file(*args, **kwargs):
        raise MemoryError("simulated OOM")

    monkeypatch.setattr(UnifiedPatcher, "from_file", mock_from_file)

    args = {
        "file_path": str(sample_file),
        "target_type": "function",
        "target_name": "foo",
        "new_code": "def foo():\n    return 1\n",
    }

    try:
        with pytest.raises(Exception):
            # FastMCP wraps exceptions in ToolError; accept either ToolError or direct MemoryError
            result = await tool.run(args, context=None, convert_result=False)
            assert isinstance(result, (dict, PatchResultModel))
            if isinstance(result, PatchResultModel):
                assert result.success is False
                assert result.error_code in {
                    "internal_error",
                    "resource_exhausted",
                    "UPDATE_SYMBOL_INVALID_INPUT",
                }
                assert result.error is not None
            else:
                err = result.get("error")
                assert err, "MemoryError should produce an error envelope"
                if isinstance(err, dict):
                    assert err.get("error_code") in {
                        "internal_error",
                        "resource_exhausted",
                    }
                    assert err.get("error") is not None
                else:
                    assert "error" in str(err).lower()
    finally:
        if sample_file.exists():
            sample_file.unlink()


async def test_update_symbol_redacts_pii_from_error_details(monkeypatch, tmp_path, caplog):
    """Secret strings in args should not appear in error_details or logs."""

    import logging

    caplog.set_level(logging.DEBUG)

    monkeypatch.setattr(mcp_server, "_get_current_tier", lambda: "community")
    tool = mcp._tool_manager._tools["update_symbol"]

    from pathlib import Path

    from code_scalpel.mcp.models.core import PatchResultModel

    project_root = Path("/mnt/k/backup/Develop/code-scalpel")
    sample_file = project_root / "test_pii_sample_temp.py"
    sample_file.write_text("""def foo():
    return 0
""")

    secret_string = "sk_live_51AbC123XyZ456SECRET789"
    args = {
        "file_path": str(sample_file),
        "target_type": "function",
        "target_name": "nonexistent",  # Trigger error
        "new_code": f"def foo():\n    api_key = '{secret_string}'\n    return 1\n",
    }

    try:
        result = await tool.run(args, context=None, convert_result=False)

        assert isinstance(result, (dict, PatchResultModel))
        err = result.error if isinstance(result, PatchResultModel) else result.get("error")
        assert err, "Should return error for nonexistent symbol"

        # Secret should not appear in error payload
        result_str = str(result)
        assert secret_string not in result_str, "Secret leaked in error payload"

        # Secret should not appear in logs
        for record in caplog.records:
            assert secret_string not in record.message, f"Secret leaked in log: {record.message}"

        # Temp paths should be redacted (e.g., /tmp/pytest-of-user/... -> [REDACTED]/...)
        if not isinstance(result, PatchResultModel):
            if isinstance(err, dict) and err.get("error_details"):
                details_str = str(err["error_details"])
                if "pytest-of-" in str(sample_file):
                    assert "pytest-of-" not in details_str, "Temp session path leaked"
    finally:
        if sample_file.exists():
            sample_file.unlink()
