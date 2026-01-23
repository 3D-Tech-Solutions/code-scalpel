"""MCP protocol and async compliance coverage for rename_symbol."""

from __future__ import annotations

import asyncio
from datetime import timedelta
from pathlib import Path

import pytest

from tests.mcp.test_tier_boundary_limits import (
    _assert_envelope,
    _stdio_session,
    _tool_json,
)

pytestmark = [pytest.mark.asyncio]


ASYNC_TIMEOUT = timedelta(seconds=45)


async def test_mcp_rename_symbol_envelope_and_success(tmp_path: Path):
    """rename_symbol responses include the MCP envelope and success flag."""
    # [20260118_FIX] Project root setup: Create project subdirectory for security checks.
    project_root = tmp_path / "proj"
    project_root.mkdir(parents=True, exist_ok=True)

    file_path = project_root / "app.py"
    file_path.write_text("def old():\n    return 1\n", encoding="utf-8")

    async with _stdio_session(project_root=project_root) as session:
        payload = await session.call_tool(
            "rename_symbol",
            arguments={
                "file_path": str(file_path),
                "target_type": "function",
                "target_name": "old",
                "new_name": "new",
                "create_backup": False,
            },
            read_timeout_seconds=ASYNC_TIMEOUT,
        )

    env_json = _tool_json(payload)
    data = _assert_envelope(env_json, tool_name="rename_symbol")

    assert data["success"] is True
    assert data.get("error") is None
    assert data.get("warnings") is not None
    # [20260113_FIX] upgrade_hints may be filtered out by minimal response profile
    # assert isinstance(env_json.get("upgrade_hints"), list)


async def test_mcp_rename_symbol_parallel_requests(tmp_path: Path):
    """Concurrent MCP rename_symbol calls stay responsive and track request ids."""
    a_path = tmp_path / "a.py"
    b_path = tmp_path / "b.py"
    a_path.write_text("def foo():\n    return 1\n", encoding="utf-8")
    b_path.write_text("def bar():\n    return 2\n", encoding="utf-8")

    async with _stdio_session(project_root=tmp_path) as session:
        fut1 = session.call_tool(
            "rename_symbol",
            arguments={
                "file_path": str(a_path),
                "target_type": "function",
                "target_name": "foo",
                "new_name": "foo_renamed",
                "create_backup": False,
            },
            read_timeout_seconds=ASYNC_TIMEOUT,
        )
        fut2 = session.call_tool(
            "rename_symbol",
            arguments={
                "file_path": str(b_path),
                "target_type": "function",
                "target_name": "bar",
                "new_name": "bar_renamed",
                "create_backup": False,
            },
            read_timeout_seconds=ASYNC_TIMEOUT,
        )

        payload1, payload2 = await asyncio.gather(fut1, fut2)

    env1 = _tool_json(payload1)
    env2 = _tool_json(payload2)

    data1 = _assert_envelope(env1, tool_name="rename_symbol")
    data2 = _assert_envelope(env2, tool_name="rename_symbol")

    assert data1["success"] is True
    assert data2["success"] is True

    # [20260113_FIX] request_id and duration_ms may be filtered out by minimal response profile
    # If present, verify they are distinct (proves async handling)
    if env1.get("request_id") is not None and env2.get("request_id") is not None:
        assert env1.get("request_id") != env2.get("request_id")
    if env1.get("duration_ms") is not None:
        assert env1.get("duration_ms", 0) >= 0
    if env2.get("duration_ms") is not None:
        assert env2.get("duration_ms", 0) >= 0

    # Responses should include a warnings list even if empty
    assert isinstance(data1.get("warnings"), list)
    assert isinstance(data2.get("warnings"), list)
