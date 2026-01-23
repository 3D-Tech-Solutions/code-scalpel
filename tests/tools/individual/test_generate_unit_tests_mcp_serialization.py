import json


def test_generate_unit_tests_result_is_json_serializable() -> None:
    """Regression: MCP responses must be JSON-serializable.

    This previously surfaced as an MCP `internal_error` even on trivial functions
    when the generated result contained non-JSON-friendly objects.

    [20251230_TEST][unit-tests] Ensure generate_unit_tests is transport-safe.
    """
    from code_scalpel.mcp.server import _generate_tests_sync

    code = """

def add(a, b):
    return a + b
"""

    result = _generate_tests_sync(code=code, framework="pytest")
    assert result.success is True
    assert result.test_count >= 1

    # Pydantic → plain dict → JSON should always succeed for MCP transport.
    payload = result.model_dump()
    json.dumps(payload)
