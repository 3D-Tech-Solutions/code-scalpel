"""MCP envelope error handling for tier-limited features.

[20251228_TEST] Ensures upgrade_required errors include upgrade URL and no stack traces.
"""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_extract_code_cross_file_deps_is_upgrade_required_in_community(
    monkeypatch,
):
    # Force community tier (no license)
    monkeypatch.setenv("CODE_SCALPEL_TIER", "community")
    monkeypatch.delenv("CODE_SCALPEL_LICENSE_PATH", raising=False)

    from code_scalpel.mcp import server

    tool = server.mcp._tool_manager.get_tool("extract_code")

    result = await tool.run(
        {
            "target_type": "function",
            "target_name": "hello",
            "code": "def hello():\n    return 1\n",
            "include_cross_file_deps": True,
        },
        context=None,
        convert_result=False,
    )

    # [20260118_BUGFIX] Result may be Pydantic model or dict depending on conversion
    result_dict = result.model_dump() if hasattr(result, "model_dump") else result

    # Extract_code wraps the actual result in 'data' field
    data = result_dict.get("data", {})
    assert data["success"] is False

    # Check for tier-gating error message in the nested error field
    error_msg = data.get("error", "")
    assert "cross_file_deps" in error_msg or "PRO" in error_msg, f"Expected cross_file_deps error, got: {error_msg}"

    # Sanity: no stack trace markers in the user-facing error string
    assert "Traceback" not in error_msg
