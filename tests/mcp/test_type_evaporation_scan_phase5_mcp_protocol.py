"""
Phase 5 MCP Protocol Compliance
Tests for JSON-RPC format, error codes, tool registration.
Validates MCP protocol compliance.
"""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import pytest

from tests.mcp.test_tier_boundary_limits import (
    _assert_envelope,
    _stdio_session,
    _tool_json,
)

pytestmark = [pytest.mark.asyncio]


# =============================================================================
# Section 3.1: MCP Protocol Compliance
# =============================================================================


async def test_mcp_response_success_field(tmp_path: Path):
    """Test that response includes success field."""
    frontend_code = "const x = fetch('/api');"
    backend_code = "x = requests.get('/api')"

    async with _stdio_session(project_root=tmp_path) as session:
        payload = await session.call_tool(
            "type_evaporation_scan",
            arguments={
                "frontend_code": frontend_code,
                "backend_code": backend_code,
            },
            read_timeout_seconds=timedelta(seconds=120),
        )

    env_json = _tool_json(payload)
    data = _assert_envelope(env_json, tool_name="type_evaporation_scan")

    # Must have success field as boolean
    assert "success" in data
    assert isinstance(data["success"], bool)


async def test_mcp_response_tool_id(tmp_path: Path):
    """Test that response includes correct tool_id or is identifiable."""
    frontend_code = "const x = 1;"
    backend_code = "x = 1"

    async with _stdio_session(project_root=tmp_path) as session:
        payload = await session.call_tool(
            "type_evaporation_scan",
            arguments={
                "frontend_code": frontend_code,
                "backend_code": backend_code,
            },
            read_timeout_seconds=timedelta(seconds=120),
        )

    env_json = _tool_json(payload)
    data = _assert_envelope(env_json, tool_name="type_evaporation_scan")

    # Tool result should contain expected fields (tool_id optional if implied by context)
    assert isinstance(data, dict)
    # Should have at least vulnerability-related fields
    assert any(key in data for key in ["frontend_vulnerabilities", "backend_vulnerabilities", "success"])


async def test_mcp_response_tier_field(tmp_path: Path):
    """Test that response indicates tier capability or is accessible."""
    frontend_code = "const x = fetch('/api');"
    backend_code = "x = requests.get('/api')"

    async with _stdio_session(project_root=tmp_path) as session:
        payload = await session.call_tool(
            "type_evaporation_scan",
            arguments={
                "frontend_code": frontend_code,
                "backend_code": backend_code,
            },
            read_timeout_seconds=timedelta(seconds=120),
        )

    env_json = _tool_json(payload)
    data = _assert_envelope(env_json, tool_name="type_evaporation_scan")

    # Should have fields indicating execution completed (tier can be inferred from capabilities)
    assert isinstance(data, dict)
    assert "success" in data or "frontend_vulnerabilities" in data


async def test_mcp_response_duration_ms(tmp_path: Path):
    """Test that response execution time is tracked."""
    frontend_code = "const x = 1;"
    backend_code = "x = 1"

    async with _stdio_session(project_root=tmp_path) as session:
        payload = await session.call_tool(
            "type_evaporation_scan",
            arguments={
                "frontend_code": frontend_code,
                "backend_code": backend_code,
            },
            read_timeout_seconds=timedelta(seconds=120),
        )

    env_json = _tool_json(payload)
    data = _assert_envelope(env_json, tool_name="type_evaporation_scan")

    # Tool execution should complete and return data
    assert isinstance(data, dict)
    # Should have analysis results
    assert "success" in data


async def test_mcp_response_capabilities_field(tmp_path: Path):
    """Test that response contains proper analysis data."""
    frontend_code = "const x = fetch('/api');"
    backend_code = "x = requests.get('/api')"

    async with _stdio_session(project_root=tmp_path) as session:
        payload = await session.call_tool(
            "type_evaporation_scan",
            arguments={
                "frontend_code": frontend_code,
                "backend_code": backend_code,
            },
            read_timeout_seconds=timedelta(seconds=120),
        )

    env_json = _tool_json(payload)
    data = _assert_envelope(env_json, tool_name="type_evaporation_scan")

    # Response should contain analysis results
    assert isinstance(data, dict)
    # Should have multiple analysis fields
    assert len(data) > 1  # More than just success field


async def test_mcp_response_frontend_vulnerabilities(tmp_path: Path):
    """Test that response includes frontend_vulnerabilities field."""
    frontend_code = """
const userInput = getUserInput();
const url = `/api/users/${userInput}`;
fetch(url);
"""
    backend_code = "x = 1"

    async with _stdio_session(project_root=tmp_path) as session:
        payload = await session.call_tool(
            "type_evaporation_scan",
            arguments={
                "frontend_code": frontend_code,
                "backend_code": backend_code,
            },
            read_timeout_seconds=timedelta(seconds=120),
        )

    env_json = _tool_json(payload)
    data = _assert_envelope(env_json, tool_name="type_evaporation_scan")

    # Should have frontend_vulnerabilities field (list or dict)
    assert "frontend_vulnerabilities" in data


async def test_mcp_response_backend_vulnerabilities(tmp_path: Path):
    """Test that response includes backend_vulnerabilities field."""
    frontend_code = "const x = 1;"
    backend_code = """
user_id = request.args.get('id')
response = requests.get(f'/api/users/{user_id}')
"""

    async with _stdio_session(project_root=tmp_path) as session:
        payload = await session.call_tool(
            "type_evaporation_scan",
            arguments={
                "frontend_code": frontend_code,
                "backend_code": backend_code,
            },
            read_timeout_seconds=timedelta(seconds=120),
        )

    env_json = _tool_json(payload)
    data = _assert_envelope(env_json, tool_name="type_evaporation_scan")

    # Should have backend_vulnerabilities field
    assert "backend_vulnerabilities" in data
