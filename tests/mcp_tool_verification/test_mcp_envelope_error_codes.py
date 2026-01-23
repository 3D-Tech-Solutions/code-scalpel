"""Envelope error-code classification tests.

These tests validate that the MCP envelope wrapper classifies exceptions into
standard error codes per the contract (invalid_argument, timeout, internal_error, ...).

They do not exercise JSON-RPC transport, but validate the inner contract logic
used by the MCP boundary, providing concrete evidence for error-code specifics.
"""

import asyncio

import pytest

pytest.importorskip("code_scalpel")


async def _run_wrapped(fn):
    from code_scalpel.mcp.contract import envelop_tool_function

    async def tier_getter():  # type: ignore[return-type]
        return "community"

    wrapped = envelop_tool_function(
        fn,
        tool_id="mcp_code-scalpel_test_tool",
        tool_version="0.0.0",
        tier_getter=lambda: "community",
    )
    return await wrapped()


def test_envelope_invalid_argument_error_code():
    from code_scalpel.mcp.contract import ToolResponseEnvelope

    def bad_args():
        raise ValueError("bad input shape")

    env: ToolResponseEnvelope = asyncio.run(_run_wrapped(bad_args))
    assert env.error is not None
    assert env.error.error_code == "invalid_argument"


def test_envelope_timeout_error_code():
    from code_scalpel.mcp.contract import ToolResponseEnvelope

    async def sleepy():  # async to mimic handler
        raise asyncio.TimeoutError("operation timed out")

    env: ToolResponseEnvelope = asyncio.run(_run_wrapped(sleepy))
    assert env.error is not None
    assert env.error.error_code == "timeout"


def test_envelope_internal_error_code():
    from code_scalpel.mcp.contract import ToolResponseEnvelope

    def kaboom():
        raise RuntimeError("boom")

    env: ToolResponseEnvelope = asyncio.run(_run_wrapped(kaboom))
    assert env.error is not None
    assert env.error.error_code == "internal_error"
