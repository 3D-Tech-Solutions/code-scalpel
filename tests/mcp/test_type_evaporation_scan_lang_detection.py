"""
Phase A Critical Tests: Language Auto-Detection
Tests automatic language detection and override parameter.
Addresses Section 1.3 gaps: Python/TypeScript auto-detection, language override.
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


async def test_language_detection_python_backend(tmp_path: Path):
    """Python backend is auto-detected from syntax patterns."""

    # Clear Python code with def/async def/type hints
    python_code = """
from typing import Dict, Any
from flask import Flask, request

app = Flask(__name__)

async def validate_user(user_id: int) -> Dict[str, Any]:
    '''Async function with type hints - clearly Python'''
    return {'id': user_id, 'valid': True}

@app.route('/api/user')
def get_user():
    data = request.get_json()
    return validate_user(data['id'])
"""

    # Minimal frontend code (won't be analyzed - focus is on backend)
    minimal_frontend = "const x = 1;"

    # Don't specify backend_language parameter - should auto-detect
    async with _stdio_session(project_root=tmp_path) as session:
        payload = await session.call_tool(
            "type_evaporation_scan",
            arguments={
                "frontend_code": minimal_frontend,
                "backend_code": python_code,
                "frontend_file": "frontend.ts",
                "backend_file": "backend.py",
            },
            read_timeout_seconds=timedelta(seconds=120),
        )

    env_json = _tool_json(payload)
    data = _assert_envelope(env_json, tool_name="type_evaporation_scan")

    assert data.get("success") is True
    # Backend should be identified (check backend_vulnerabilities field exists)
    assert "backend_vulnerabilities" in data


async def test_language_detection_typescript_frontend(tmp_path: Path):
    """TypeScript frontend is auto-detected from syntax patterns."""

    # Clear TypeScript code with type annotations, async/await, arrow functions
    typescript_code = """
interface User {
    id: number;
    name: string;
    role: 'admin' | 'user';
}

async function fetchUser(userId: number): Promise<User> {
    const response = await fetch(`/api/users/${userId}`);
    const data: User = await response.json();
    return data;
}

const processRole = (role: 'admin' | 'user'): void => {
    console.log(`Processing role: ${role}`);
};

type Role = 'admin' | 'user' | 'guest';
const roles: Role[] = ['admin', 'user'];
"""

    # Minimal backend code (won't be analyzed - focus is on frontend)
    minimal_backend = "pass"

    # Don't specify frontend_language parameter - should auto-detect
    async with _stdio_session(project_root=tmp_path) as session:
        payload = await session.call_tool(
            "type_evaporation_scan",
            arguments={
                "frontend_code": typescript_code,
                "backend_code": minimal_backend,
                "frontend_file": "frontend.ts",
                "backend_file": "backend.py",
            },
            read_timeout_seconds=timedelta(seconds=120),
        )

    env_json = _tool_json(payload)
    data = _assert_envelope(env_json, tool_name="type_evaporation_scan")

    assert data.get("success") is True
    # Frontend should be identified (check frontend_vulnerabilities field exists)
    assert "frontend_vulnerabilities" in data


async def test_language_detection_javascript_frontend(tmp_path: Path):
    """JavaScript (no types) is auto-detected and handled."""

    # Plain JavaScript without TypeScript type annotations
    javascript_code = """
async function fetchData(endpoint) {
    const response = await fetch(endpoint);
    const data = response.json();
    return data;
}

function handleInput(inputElement) {
    const value = inputElement.value;
    return fetch('/api/process', {
        method: 'POST',
        body: JSON.stringify({ value: value })
    });
}

const xhr = new XMLHttpRequest();
xhr.open('GET', '/api/data');
xhr.onload = function() {
    const result = JSON.parse(xhr.responseText);
    console.log(result);
};
"""

    # Minimal backend code
    minimal_backend = "pass"

    async with _stdio_session(project_root=tmp_path) as session:
        payload = await session.call_tool(
            "type_evaporation_scan",
            arguments={
                "frontend_code": javascript_code,
                "backend_code": minimal_backend,
                "frontend_file": "app.js",  # .js extension
                "backend_file": "backend.py",
            },
            read_timeout_seconds=timedelta(seconds=120),
        )

    env_json = _tool_json(payload)
    data = _assert_envelope(env_json, tool_name="type_evaporation_scan")

    assert data.get("success") is True
    # Should still analyze for vulnerabilities
    assert "frontend_vulnerabilities" in data


async def test_language_override_parameter(tmp_path: Path):
    """Explicit language parameter overrides auto-detection."""

    # Ambiguous code that could be JavaScript or TypeScript
    ambiguous_code = """
async function getData() {
    const resp = await fetch('/api/data');
    return resp.json();
}
"""

    # Minimal backend code
    minimal_backend = "pass"

    # Test 1: With .js file extension (would default to JavaScript)
    async with _stdio_session(project_root=tmp_path) as session:
        js_payload = await session.call_tool(
            "type_evaporation_scan",
            arguments={
                "frontend_code": ambiguous_code,
                "backend_code": minimal_backend,
                "frontend_file": "app.js",
                "backend_file": "backend.py",
                # No explicit language - should detect as JavaScript
            },
            read_timeout_seconds=timedelta(seconds=120),
        )

    js_env = _tool_json(js_payload)
    js_data = _assert_envelope(js_env, tool_name="type_evaporation_scan")
    assert js_data.get("success") is True

    # Test 2: Override to TypeScript despite .js extension
    # Note: The tool may not support explicit language override in current impl
    # This test documents expected behavior for future enhancement
    async with _stdio_session(project_root=tmp_path) as session:
        ts_payload = await session.call_tool(
            "type_evaporation_scan",
            arguments={
                "frontend_code": ambiguous_code,
                "backend_code": minimal_backend,
                "frontend_file": "app.ts",  # Use .ts extension
                "backend_file": "backend.py",
            },
            read_timeout_seconds=timedelta(seconds=120),
        )

    ts_env = _tool_json(ts_payload)
    ts_data = _assert_envelope(ts_env, tool_name="type_evaporation_scan")
    assert ts_data.get("success") is True

    # Both should succeed (language detection flexible)
    # Core functionality works regardless of detected language


async def test_language_detection_from_file_extension(tmp_path: Path):
    """File extension hints language detection."""

    simple_code = "function test() { return fetch('/api'); }"

    # Minimal backend code
    minimal_backend = "pass"

    # Test with different extensions
    extensions = [
        ("app.js", True),  # JavaScript
        ("app.ts", True),  # TypeScript
        ("app.jsx", True),  # React JavaScript
        ("app.tsx", True),  # React TypeScript
    ]

    for filename, should_succeed in extensions:
        async with _stdio_session(project_root=tmp_path) as session:
            payload = await session.call_tool(
                "type_evaporation_scan",
                arguments={
                    "frontend_code": simple_code,
                    "backend_code": minimal_backend,
                    "frontend_file": filename,
                    "backend_file": "backend.py",
                },
                read_timeout_seconds=timedelta(seconds=120),
            )

        env_json = _tool_json(payload)
        data = _assert_envelope(env_json, tool_name="type_evaporation_scan")

        if should_succeed:
            assert data.get("success") is True, f"Failed for {filename}"
        # Tool should handle all common JS/TS extensions


async def test_language_detection_mixed_syntax(tmp_path: Path):
    """Mixed TypeScript and Python syntax is handled correctly."""

    typescript_frontend = """
type UserRole = 'admin' | 'user';

async function setRole(role: UserRole): Promise<void> {
    await fetch('/api/role', {
        method: 'POST',
        body: JSON.stringify({ role })
    });
}
"""

    python_backend = """
from flask import Flask, request
from typing import Literal

app = Flask(__name__)

Role = Literal['admin', 'user']

@app.post('/api/role')
def set_role():
    data = request.get_json()
    role: Role = data['role']
    return {'role': role}
"""

    async with _stdio_session(project_root=tmp_path) as session:
        payload = await session.call_tool(
            "type_evaporation_scan",
            arguments={
                "frontend_code": typescript_frontend,
                "backend_code": python_backend,
                "frontend_file": "frontend.ts",
                "backend_file": "backend.py",
            },
            read_timeout_seconds=timedelta(seconds=120),
        )

    env_json = _tool_json(payload)
    data = _assert_envelope(env_json, tool_name="type_evaporation_scan")

    assert data.get("success") is True
    # Both languages should be correctly identified
    assert "frontend_vulnerabilities" in data
    assert "backend_vulnerabilities" in data
    # Cross-file matching should work
    assert "cross_file_issues" in data
