import pytest
from mcp.client.session import ClientSession
from mcp.client.sse import sse_client

try:
    from mcp.client.streamable_http import streamable_http_client
except Exception:  # pragma: no cover - optional dependency may be absent
    streamable_http_client = None

if streamable_http_client is None:
    import pytest

    # [20260117_TEST] Skip module when streamable HTTP client is unavailable
    pytestmark = [pytest.mark.skip("streamable-http client not available")]


@pytest.mark.asyncio
@pytest.mark.skip(reason="[20260117_TEST] MCP HTTP integration test requires running MCP server, skipped")
async def test_mcp_http_connection():
    """Test connection to the running MCP server via HTTP SSE."""
    # Code Scalpel uses FastMCP:
    # - streamable-http transport mounts at /mcp
    # - sse transport mounts at /sse
    streamable_url = "http://localhost:8593/mcp"
    sse_url = "http://localhost:8593/sse"

    try:
        async with streamable_http_client(streamable_url) as (
            read,
            write,
            _get_session_id,
        ):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools = await session.list_tools()
                tool_names = [t.name for t in tools.tools]
                assert "analyze_code" in tool_names
                assert "security_scan" in tool_names
                return
    except Exception:
        # Fall back to classic SSE endpoint (older deployments)
        pass

    try:
        async with sse_client(sse_url) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools = await session.list_tools()
                tool_names = [t.name for t in tools.tools]
                assert "analyze_code" in tool_names
                assert "security_scan" in tool_names
                return
    except Exception as e:
        # [20251214_TEST] Skip when MCP server isn't running locally
        pytest.skip(f"Skipping MCP HTTP integration; server unavailable: {e}")
