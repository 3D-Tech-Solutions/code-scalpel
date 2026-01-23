"""
[20260104_TEST] MCP metadata assertions for update_symbol.
"""

from code_scalpel.mcp.server import mcp


def test_update_symbol_metadata_description_and_name():
    tool = mcp._tool_manager._tools["update_symbol"]

    assert tool.name == "update_symbol"
    assert tool.description
    desc = tool.description.lower()
    assert "replace" in desc or "safely" in desc


def test_update_symbol_input_schema_required_params():
    tool = mcp._tool_manager._tools["update_symbol"]

    params = tool.parameters or {}
    required = set(params.get("required") or []) if isinstance(params, dict) else set()
    properties = params.get("properties") if isinstance(params, dict) else {}

    for required_name in ("file_path", "target_type", "target_name"):
        assert required_name in required
        assert required_name in properties
        spec = properties.get(required_name) or {}
        if isinstance(spec, dict):
            assert spec.get("type") in {"string", "str", None}

    # Optional payloads should still be described in the schema
    assert "new_code" in properties
