"""JSON-RPC error handling tests for simulate_refactor.

These are placeholders to validate protocol-level error behavior. They are
skipped until an MCP transport harness is available in tests.
"""

import pytest

pytest.importorskip("code_scalpel")


@pytest.mark.skip(reason="MCP transport harness not available in tests")
def test_invalid_method_returns_jsonrpc_error():
    """Calling an unknown method should return JSON-RPC error (-32601)."""
    # Placeholder: when MCP server harness is available, construct a JSON-RPC request
    # with an invalid method and assert the error response structure and code.
    # Example shape:
    # request = {"jsonrpc": "2.0", "method": "tools/unknown", "id": 42}
    # response = mcp_server.handle_request(request)
    # assert response["error"]["code"] == -32601
    pass


@pytest.mark.skip(reason="MCP transport harness not available in tests")
def test_internal_error_returns_jsonrpc_error_not_crash():
    """Server internal exceptions should return JSON-RPC error (-32603) gracefully."""
    # Placeholder: force an internal error (e.g., raise Exception inside tool handler)
    # and assert the response is an error object with -32603, not a crash.
    pass
