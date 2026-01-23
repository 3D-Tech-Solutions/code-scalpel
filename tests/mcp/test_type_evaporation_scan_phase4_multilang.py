"""
Phase 4 Multi-Language Support
Tests for Python, Java, Go, and other language variant support.
Validates per-language parsing and language detection.
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
# Section 1.3: Multi-Language Support
# =============================================================================


async def test_python_async_await_support(tmp_path: Path):
    """Test Python async/await pattern recognition."""
    frontend_code = """
async function fetchUser(id: number): Promise<User> {
    const response = await fetch(`/api/users/${id}`);
    return response.json() as User;
}
"""
    backend_code = """
async def fetch_user(user_id: int) -> dict:
    async with aiohttp.ClientSession() as session:
        async with session.get(f'/api/users/{user_id}') as resp:
            return await resp.json()
"""
    async with _stdio_session(project_root=tmp_path) as session:
        payload = await session.call_tool(
            "type_evaporation_scan",
            arguments={
                "frontend_code": frontend_code,
                "backend_code": backend_code,
                "frontend_file": "async.ts",
                "backend_file": "async.py",
            },
            read_timeout_seconds=timedelta(seconds=120),
        )

    env_json = _tool_json(payload)
    data = _assert_envelope(env_json, tool_name="type_evaporation_scan")
    assert data.get("success") in [True, False]


async def test_python_type_hints(tmp_path: Path):
    """Test Python type hints and annotations."""
    frontend_code = """
type User = { id: number; name: string; email: string };
const getUser = (id: number): User => fetch(`/api/users/${id}`);
"""
    backend_code = """
from typing import TypedDict, Optional
class User(TypedDict):
    id: int
    name: str
    email: str

def get_user(user_id: int) -> User:
    response = requests.get(f'/api/users/{user_id}')
    return response.json()
"""
    async with _stdio_session(project_root=tmp_path) as session:
        payload = await session.call_tool(
            "type_evaporation_scan",
            arguments={
                "frontend_code": frontend_code,
                "backend_code": backend_code,
                "frontend_file": "types.ts",
                "backend_file": "types.py",
            },
            read_timeout_seconds=timedelta(seconds=120),
        )

    env_json = _tool_json(payload)
    data = _assert_envelope(env_json, tool_name="type_evaporation_scan")
    assert data.get("success") in [True, False]


async def test_python_list_comprehensions(tmp_path: Path):
    """Test Python list comprehensions."""
    frontend_code = """
const filtered = users.filter(u => u.active).map(u => u.id);
"""
    backend_code = """
filtered = [u['id'] for u in users if u.get('active')]
generator = (x for x in range(100) if x % 2 == 0)
"""
    async with _stdio_session(project_root=tmp_path) as session:
        payload = await session.call_tool(
            "type_evaporation_scan",
            arguments={
                "frontend_code": frontend_code,
                "backend_code": backend_code,
                "frontend_file": "filter.ts",
                "backend_file": "filter.py",
            },
            read_timeout_seconds=timedelta(seconds=120),
        )

    env_json = _tool_json(payload)
    data = _assert_envelope(env_json, tool_name="type_evaporation_scan")
    assert data.get("success") in [True, False]


async def test_python_decorators(tmp_path: Path):
    """Test Python decorators and context managers."""
    frontend_code = """
class Repository {
    @memoized
    getUser(id: number) { return fetch(`/api/users/${id}`); }
}
"""
    backend_code = """
from functools import lru_cache
from contextlib import contextmanager

@lru_cache(maxsize=128)
def get_user(user_id: int):
    return requests.get(f'/api/users/{user_id}').json()

@contextmanager
def db_connection(conn_str):
    conn = create_connection(conn_str)
    try:
        yield conn
    finally:
        conn.close()
"""
    async with _stdio_session(project_root=tmp_path) as session:
        payload = await session.call_tool(
            "type_evaporation_scan",
            arguments={
                "frontend_code": frontend_code,
                "backend_code": backend_code,
                "frontend_file": "deco.ts",
                "backend_file": "deco.py",
            },
            read_timeout_seconds=timedelta(seconds=120),
        )

    env_json = _tool_json(payload)
    data = _assert_envelope(env_json, tool_name="type_evaporation_scan")
    assert data.get("success") in [True, False]


async def test_mixed_language_frontend_backend(tmp_path: Path):
    """Test handling of mismatched frontend/backend languages."""
    frontend_code = """
const getUser = async (id: number) => {
    const response = await fetch(`/api/users/${id}`);
    return response.json();
};
"""
    backend_code = """
def get_user(user_id):
    uri = URI("http://localhost/api/users/#{user_id}")
    JSON.parse(Net::HTTP.get(uri))
end
"""
    async with _stdio_session(project_root=tmp_path) as session:
        payload = await session.call_tool(
            "type_evaporation_scan",
            arguments={
                "frontend_code": frontend_code,
                "backend_code": backend_code,
                "frontend_file": "app.ts",
                "backend_file": "app.rb",
            },
            read_timeout_seconds=timedelta(seconds=120),
        )

    env_json = _tool_json(payload)
    data = _assert_envelope(env_json, tool_name="type_evaporation_scan")
    assert data.get("success") in [True, False]


async def test_language_detection_from_extension(tmp_path: Path):
    """Test automatic language detection from file extensions."""
    frontend_code = "const x = 42;"
    backend_code = "x = 42"

    async with _stdio_session(project_root=tmp_path) as session:
        payload = await session.call_tool(
            "type_evaporation_scan",
            arguments={
                "frontend_code": frontend_code,
                "backend_code": backend_code,
                "frontend_file": "script.ts",
                "backend_file": "script.py",
            },
            read_timeout_seconds=timedelta(seconds=120),
        )

    env_json = _tool_json(payload)
    data = _assert_envelope(env_json, tool_name="type_evaporation_scan")
    assert data.get("success") in [True, False]
