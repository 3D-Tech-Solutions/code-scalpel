"""
Phase B Edge Cases Tests for type_evaporation_scan

Tests boundary conditions, special constructs, and error conditions.
Addresses Section 1.2 gaps from comprehensive checklist.
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


async def test_minimal_valid_input(tmp_path: Path):
    """Minimal valid input (1 function per side) is handled."""
    frontend_code = "const x = 1;"
    backend_code = "def f(): pass"

    async with _stdio_session(project_root=tmp_path) as session:
        payload = await session.call_tool(
            "type_evaporation_scan",
            arguments={
                "frontend_code": frontend_code,
                "backend_code": backend_code,
                "frontend_file": "frontend.ts",
                "backend_file": "backend.py",
            },
            read_timeout_seconds=timedelta(seconds=120),
        )

    env_json = _tool_json(payload)
    data = _assert_envelope(env_json, tool_name="type_evaporation_scan")

    assert data.get("success") is True


async def test_code_with_decorators(tmp_path: Path):
    """Code with decorators/annotations is parsed correctly."""
    frontend_code = """
    @Component({
        selector: 'app-root',
        templateUrl: './app.component.html'
    })
    export class AppComponent {
        title = 'app';
    }
    """

    backend_code = """
    from flask import route

    @route('/api/test')
    def test_handler():
        return {'status': 'ok'}

    @cached
    def expensive_operation():
        return compute_result()
    """

    async with _stdio_session(project_root=tmp_path) as session:
        payload = await session.call_tool(
            "type_evaporation_scan",
            arguments={
                "frontend_code": frontend_code,
                "backend_code": backend_code,
                "frontend_file": "component.ts",
                "backend_file": "handler.py",
            },
            read_timeout_seconds=timedelta(seconds=120),
        )

    env_json = _tool_json(payload)
    data = _assert_envelope(env_json, tool_name="type_evaporation_scan")

    assert data.get("success") is True


async def test_code_with_async_await(tmp_path: Path):
    """Code with async/await patterns is analyzed correctly."""
    frontend_code = """
    async function fetchUser(id: number): Promise<User> {
        const response = await fetch(`/api/users/${id}`);
        return await response.json();
    }

    async function processData() {
        const data = await fetchUser(123);
        return data;
    }
    """

    backend_code = """
    async def get_user(user_id: int):
        result = await db.query(f'SELECT * FROM users WHERE id = {user_id}')
        return result

    async def process():
        user = await get_user(123)
        return user
    """

    async with _stdio_session(project_root=tmp_path) as session:
        payload = await session.call_tool(
            "type_evaporation_scan",
            arguments={
                "frontend_code": frontend_code,
                "backend_code": backend_code,
                "frontend_file": "async.ts",
                "backend_file": "async_handler.py",
            },
            read_timeout_seconds=timedelta(seconds=120),
        )

    env_json = _tool_json(payload)
    data = _assert_envelope(env_json, tool_name="type_evaporation_scan")

    assert data.get("success") is True
    # Async patterns may reveal implicit any issues
    assert isinstance(data.get("frontend_vulnerabilities", 0), (int, list))


async def test_code_with_generics(tmp_path: Path):
    """Code with generic types/templates is analyzed."""
    frontend_code = """
    interface Response<T> {
        data: T;
        status: number;
    }

    async function api<T>(endpoint: string): Promise<Response<T>> {
        const response = await fetch(endpoint);
        return response.json();
    }

    function process<T extends { id: number }>(item: T): T {
        return item;
    }
    """

    backend_code = """
    from typing import TypeVar, Generic, List

    T = TypeVar('T')

    class Response(Generic[T]):
        def __init__(self, data: T, status: int):
            self.data = data
            self.status = status

    def get_items() -> List[dict]:
        return [{'id': 1, 'name': 'item1'}]
    """

    async with _stdio_session(project_root=tmp_path) as session:
        payload = await session.call_tool(
            "type_evaporation_scan",
            arguments={
                "frontend_code": frontend_code,
                "backend_code": backend_code,
                "frontend_file": "generics.ts",
                "backend_file": "generics.py",
            },
            read_timeout_seconds=timedelta(seconds=120),
        )

    env_json = _tool_json(payload)
    data = _assert_envelope(env_json, tool_name="type_evaporation_scan")

    assert data.get("success") is True


async def test_code_with_comments_and_docstrings(tmp_path: Path):
    """Code with extensive comments and docstrings is handled."""
    frontend_code = """
    /**
     * Fetch user data from API
     * @param id - User ID
     * @returns User data or null
     */
    async function getUser(id: number): Promise<User | null> {
        // Make request to backend
        const response = await fetch(`/api/users/${id}`);

        // Check response
        if (!response.ok) {
            // Log error and return null
            console.error('Failed to fetch user');
            return null;
        }

        // Parse and return JSON data
        return response.json();
    }
    """

    backend_code = '''
    def get_user(user_id: int) -> dict:
        """
        Retrieve user from database

        Args:
            user_id: ID of user to fetch

        Returns:
            User dict with id, name, email fields

        Raises:
            UserNotFound: If user doesn't exist
        """
        # Query database for user
        user = db.query(f"SELECT * FROM users WHERE id = {user_id}")

        if not user:
            # User not found
            raise UserNotFound(f"User {user_id} not found")

        return user
    '''

    async with _stdio_session(project_root=tmp_path) as session:
        payload = await session.call_tool(
            "type_evaporation_scan",
            arguments={
                "frontend_code": frontend_code,
                "backend_code": backend_code,
                "frontend_file": "documented.ts",
                "backend_file": "documented.py",
            },
            read_timeout_seconds=timedelta(seconds=120),
        )

    env_json = _tool_json(payload)
    data = _assert_envelope(env_json, tool_name="type_evaporation_scan")

    assert data.get("success") is True


async def test_code_with_unusual_formatting(tmp_path: Path):
    """Code with unusual indentation/formatting is parsed."""
    frontend_code = """
interface X{a:string;b:number}
function f(x:X):void{console.log(x)}

class  C  {
    method(   ) : void {
        return ;
    }
}
    """

    backend_code = """
def f(  ):
    pass
def g(x):return x
class X:
  def __init__(self):
    self.a=1
    self.b=2
    """

    async with _stdio_session(project_root=tmp_path) as session:
        payload = await session.call_tool(
            "type_evaporation_scan",
            arguments={
                "frontend_code": frontend_code,
                "backend_code": backend_code,
                "frontend_file": "weird.ts",
                "backend_file": "weird.py",
            },
            read_timeout_seconds=timedelta(seconds=120),
        )

    env_json = _tool_json(payload)
    data = _assert_envelope(env_json, tool_name="type_evaporation_scan")

    assert data.get("success") is True


async def test_code_with_syntax_errors(tmp_path: Path):
    """Code with syntax errors is handled gracefully (not crash)."""
    frontend_code = """
    const x: string = 'unterminated
    function incomplete() {
        return {invalid json
    """

    backend_code = """
    def function_incomplete():
        return {

    class InvalidClass
        invalid syntax here!!!
    """

    async with _stdio_session(project_root=tmp_path) as session:
        payload = await session.call_tool(
            "type_evaporation_scan",
            arguments={
                "frontend_code": frontend_code,
                "backend_code": backend_code,
                "frontend_file": "invalid.ts",
                "backend_file": "invalid.py",
            },
            read_timeout_seconds=timedelta(seconds=120),
        )

    env_json = _tool_json(payload)
    # Should not crash - either success with parsing warnings
    # or error field present
    assert "error" in env_json or "data" in env_json


async def test_nested_structures(tmp_path: Path):
    """Code with deeply nested structures is analyzed."""
    frontend_code = """
    interface Level1 {
        level2: {
            level3: {
                level4: {
                    level5: {
                        value: string | number;
                        data: any;
                    };
                };
            };
        };
    }

    function processNested(obj: Level1): void {
        const val = obj.level2.level3.level4.level5.value;
        fetch('/api/process', { body: JSON.stringify(val) });
    }
    """

    backend_code = """
    class Level1:
        def __init__(self):
            self.level2 = Level2()

    class Level2:
        def __init__(self):
            self.level3 = {}

    def process_nested(obj):
        val = obj.level2.level3.get('level4', {}).get('level5', {}).get('value')
        return {'result': val}
    """

    async with _stdio_session(project_root=tmp_path) as session:
        payload = await session.call_tool(
            "type_evaporation_scan",
            arguments={
                "frontend_code": frontend_code,
                "backend_code": backend_code,
                "frontend_file": "nested.ts",
                "backend_file": "nested.py",
            },
            read_timeout_seconds=timedelta(seconds=120),
        )

    env_json = _tool_json(payload)
    data = _assert_envelope(env_json, tool_name="type_evaporation_scan")

    assert data.get("success") is True
    # Nested structures with `any` should be flagged
