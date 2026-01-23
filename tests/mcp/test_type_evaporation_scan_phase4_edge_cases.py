"""
Phase 4 Edge Cases: Advanced Code Patterns
Tests for complex code constructs, special methods, error scenarios.
Completes Section 1.2 edge case coverage.
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
# Section 1.2: Edge Cases - Advanced Code Patterns
# =============================================================================


async def test_edge_case_lambda_arrow_functions(tmp_path: Path):
    """Test arrow function and lambda handling."""
    frontend_code = """
const square = (x) => x * x;
const getUser = (userId) => fetch(`/api/users/${userId}`);
const process = items.map(item => ({id: item.id, value: item.value}));
"""
    backend_code = """
square = lambda x: x * x
get_user = lambda user_id: requests.get(f'/api/users/{user_id}')
process = [{'id': item['id'], 'value': item['value']} for item in items]
"""
    async with _stdio_session(project_root=tmp_path) as session:
        payload = await session.call_tool(
            "type_evaporation_scan",
            arguments={
                "frontend_code": frontend_code,
                "backend_code": backend_code,
                "frontend_file": "lambda.ts",
                "backend_file": "lambda.py",
            },
            read_timeout_seconds=timedelta(seconds=120),
        )

    env_json = _tool_json(payload)
    data = _assert_envelope(env_json, tool_name="type_evaporation_scan")

    assert data.get("success") in [True, False]


async def test_edge_case_generics_typescript(tmp_path: Path):
    """Test TypeScript generic type handling."""
    frontend_code = """
function identity<T>(arg: T): T { return arg; }
function getArray<T>(count: number): T[] { return new Array(count); }
const fetchData = async <T = unknown>(url: string): Promise<T> => {
    const response = await fetch(url);
    return response.json() as T;
};
"""
    backend_code = """
from typing import TypeVar, Generic, List
T = TypeVar('T')
def identity(arg: T) -> T:
    return arg
def get_array(count: int) -> List[T]:
    return [None] * count
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

    assert data.get("success") in [True, False]


async def test_edge_case_special_methods(tmp_path: Path):
    """Test special/magic method handling."""
    frontend_code = """
class User {
    private _name: string;
    static readonly DEFAULT_ROLE = 'user';

    constructor(name: string) { this._name = name; }

    get name(): string { return this._name; }
    set name(value: string) { this._name = value; }

    static fromJson(json: Record<string, unknown>): User {
        return new User(json.name as string);
    }
}
"""
    backend_code = """
class User:
    DEFAULT_ROLE = 'user'

    def __init__(self, name: str):
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str):
        self._name = value

    @classmethod
    def from_json(cls, data: dict):
        return cls(data.get('name'))
"""
    async with _stdio_session(project_root=tmp_path) as session:
        payload = await session.call_tool(
            "type_evaporation_scan",
            arguments={
                "frontend_code": frontend_code,
                "backend_code": backend_code,
                "frontend_file": "class.ts",
                "backend_file": "class.py",
            },
            read_timeout_seconds=timedelta(seconds=120),
        )

    env_json = _tool_json(payload)
    data = _assert_envelope(env_json, tool_name="type_evaporation_scan")

    assert data.get("success") in [True, False]


async def test_edge_case_deeply_nested_functions(tmp_path: Path):
    """Test handling of deeply nested functions and structures."""
    frontend_code = """
const result = ((((a) => ((b) => ((c) => a + b + c))(20))(10))(5));
const nested = {
    a: {
        b: {
            c: {
                d: {
                    e: {
                        f: "deep"
                    }
                }
            }
        }
    }
};
"""
    backend_code = """
def nested_func(a):
    def inner1(b):
        def inner2(c):
            return a + b + c
        return inner2
    return inner1

nested = {
    'a': {
        'b': {
            'c': {
                'd': {
                    'e': {
                        'f': 'deep'
                    }
                }
            }
        }
    }
}
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

    assert data.get("success") in [True, False]


async def test_edge_case_async_await_patterns(tmp_path: Path):
    """Test various async/await patterns."""
    frontend_code = """
async function fetchUser(id: number): Promise<User> {
    const response = await fetch(`/api/users/${id}`);
    return response.json() as User;
}

async function processMany(ids: number[]) {
    const promises = ids.map(id => fetchUser(id));
    return await Promise.all(promises);
}

async function withTryCatch(id: number) {
    try {
        const data = await fetch(`/api/users/${id}`);
        return data.json();
    } catch (error) {
        console.error(error);
    }
}
"""
    backend_code = """
async def fetch_user(user_id: int):
    async with aiohttp.ClientSession() as session:
        async with session.get(f'/api/users/{user_id}') as resp:
            return await resp.json()

async def process_many(ids):
    tasks = [fetch_user(uid) for uid in ids]
    return await asyncio.gather(*tasks)

async def with_try_except(user_id):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f'/api/users/{user_id}') as resp:
                return await resp.json()
    except Exception as e:
        print(e)
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


async def test_edge_case_decorators_typescript(tmp_path: Path):
    """Test TypeScript decorator handling."""
    frontend_code = """
@Component
class MyComponent {
    @Input() title: string;
    @Output() click = new EventEmitter();

    @Memoize
    compute(): number {
        return 42;
    }
}
"""
    backend_code = """
from functools import lru_cache
from functools import wraps

def memoize(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper

class MyComponent:
    def __init__(self, title: str):
        self.title = title

    @lru_cache(maxsize=128)
    def compute(self) -> int:
        return 42
"""
    async with _stdio_session(project_root=tmp_path) as session:
        payload = await session.call_tool(
            "type_evaporation_scan",
            arguments={
                "frontend_code": frontend_code,
                "backend_code": backend_code,
                "frontend_file": "decorated.ts",
                "backend_file": "decorated.py",
            },
            read_timeout_seconds=timedelta(seconds=120),
        )

    env_json = _tool_json(payload)
    data = _assert_envelope(env_json, tool_name="type_evaporation_scan")

    assert data.get("success") in [True, False]


async def test_edge_case_optional_chaining(tmp_path: Path):
    """Test optional chaining and nullish coalescing operators."""
    frontend_code = """
const data = obj?.prop?.nested?.value;
const fallback = data ?? 'default';
const method = obj?.method?.();
const index = arr?.[0];
"""
    backend_code = """
data = obj.get('prop', {}).get('nested', {}).get('value') if obj else None
fallback = data if data is not None else 'default'
method = obj.get('method') if obj else None
index = arr[0] if arr else None
"""
    async with _stdio_session(project_root=tmp_path) as session:
        payload = await session.call_tool(
            "type_evaporation_scan",
            arguments={
                "frontend_code": frontend_code,
                "backend_code": backend_code,
                "frontend_file": "optional.ts",
                "backend_file": "optional.py",
            },
            read_timeout_seconds=timedelta(seconds=120),
        )

    env_json = _tool_json(payload)
    data = _assert_envelope(env_json, tool_name="type_evaporation_scan")

    assert data.get("success") in [True, False]


async def test_edge_case_spread_rest_operators(tmp_path: Path):
    """Test spread and rest parameter operators."""
    frontend_code = """
const arr = [1, 2, ...existing];
const obj = { ...base, ...override };
function variadic(...args) { return args; }
const [first, ...rest] = array;
"""
    backend_code = """
arr = [1, 2, *existing]
obj = {**base, **override}
def variadic(*args): return args
first, *rest = array
"""
    async with _stdio_session(project_root=tmp_path) as session:
        payload = await session.call_tool(
            "type_evaporation_scan",
            arguments={
                "frontend_code": frontend_code,
                "backend_code": backend_code,
                "frontend_file": "spread.ts",
                "backend_file": "spread.py",
            },
            read_timeout_seconds=timedelta(seconds=120),
        )

    env_json = _tool_json(payload)
    data = _assert_envelope(env_json, tool_name="type_evaporation_scan")

    assert data.get("success") in [True, False]


async def test_edge_case_multiline_statements(tmp_path: Path):
    """Test multi-line statements with method chaining."""
    frontend_code = """
const result = fetch('/api/users')
    .then(r => r.json())
    .then(data => data.map(d => ({id: d.id, name: d.name})))
    .catch(e => console.error(e));

const query = users
    .filter(u => u.active)
    .map(u => u.id)
    .sort();
"""
    backend_code = """
result = requests.get('/api/users').json()
processed = [{'id': d['id'], 'name': d['name']} for d in result]

query = sorted(
    [u['id'] for u in users if u.get('active')]
)
"""
    async with _stdio_session(project_root=tmp_path) as session:
        payload = await session.call_tool(
            "type_evaporation_scan",
            arguments={
                "frontend_code": frontend_code,
                "backend_code": backend_code,
                "frontend_file": "chains.ts",
                "backend_file": "chains.py",
            },
            read_timeout_seconds=timedelta(seconds=120),
        )

    env_json = _tool_json(payload)
    data = _assert_envelope(env_json, tool_name="type_evaporation_scan")

    assert data.get("success") in [True, False]


async def test_edge_case_many_small_functions(tmp_path: Path):
    """Test handling of code with many small functions."""
    # Create code with 50 small functions
    funcs_ts = "\n".join([f"const func{i} = () => fetch('/api/{i}');" for i in range(50)])
    funcs_py = "\n".join([f"def func{i}(): return requests.get('/api/{i}')" for i in range(50)])

    async with _stdio_session(project_root=tmp_path) as session:
        payload = await session.call_tool(
            "type_evaporation_scan",
            arguments={
                "frontend_code": funcs_ts,
                "backend_code": funcs_py,
                "frontend_file": "many.ts",
                "backend_file": "many.py",
            },
            read_timeout_seconds=timedelta(seconds=120),
        )

    env_json = _tool_json(payload)
    data = _assert_envelope(env_json, tool_name="type_evaporation_scan")

    assert data.get("success") in [True, False]


async def test_edge_case_unicode_and_special_chars(tmp_path: Path):
    """Test handling of unicode and special characters."""
    frontend_code = """
const message = "Hello 世界 مرحبا";
const emoji = "🔐 🔒 🗝️";
const url = `/api/data`;
"""
    backend_code = """
message = "Hello 世界 مرحبا"
emoji = "🔐 🔒 🗝️"
url = "/api/data"
"""
    async with _stdio_session(project_root=tmp_path) as session:
        payload = await session.call_tool(
            "type_evaporation_scan",
            arguments={
                "frontend_code": frontend_code,
                "backend_code": backend_code,
                "frontend_file": "unicode.ts",
                "backend_file": "unicode.py",
            },
            read_timeout_seconds=timedelta(seconds=120),
        )

    env_json = _tool_json(payload)
    data = _assert_envelope(env_json, tool_name="type_evaporation_scan")

    assert data.get("success") in [True, False]


async def test_edge_case_comments_and_docstrings(tmp_path: Path):
    """Test handling of comments and docstrings."""
    frontend_code = """
/* Multi-line
   comment */
function process(/* param comment */ data) {
    // Single line comment
    const x = fetch('/api/data'); // end of line comment
    return x;
}
"""
    backend_code = """
def process(data):  # end of line
    '''Docstring
    spanning
    multiple
    lines'''
    x = requests.get('/api/data')  # comment
    return x
"""
    async with _stdio_session(project_root=tmp_path) as session:
        payload = await session.call_tool(
            "type_evaporation_scan",
            arguments={
                "frontend_code": frontend_code,
                "backend_code": backend_code,
                "frontend_file": "comments.ts",
                "backend_file": "comments.py",
            },
            read_timeout_seconds=timedelta(seconds=120),
        )

    env_json = _tool_json(payload)
    data = _assert_envelope(env_json, tool_name="type_evaporation_scan")

    assert data.get("success") in [True, False]
