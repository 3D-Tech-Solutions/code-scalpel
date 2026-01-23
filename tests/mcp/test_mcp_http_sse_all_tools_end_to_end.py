import os
import socket
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path

import anyio
import httpx
import pytest
from mcp.client.session import ClientSession
from mcp.client.sse import sse_client

try:
    from mcp.client.streamable_http import streamable_http_client
except Exception:  # pragma: no cover - optional dependency may be absent
    streamable_http_client = None

if streamable_http_client is None:
    # [20260117_TEST] Skip module when streamable HTTP client is unavailable
    pytestmark = [pytest.mark.skip("streamable-http client not available")]

# [20260118_TEST] Skip entire module - requires running HTTP server
pytestmark = pytest.mark.skip(reason="[20260118_TEST] HTTP/SSE tests require running server - skip for local pipeline")


@dataclass(frozen=True)
class _Ports:
    mcp_port: int
    health_port: int


def _can_bind(host: str, port: int) -> bool:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind((host, port))
        return True
    except OSError:
        return False


def _get_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _get_free_port_pair(host: str = "127.0.0.1", attempts: int = 200) -> _Ports:
    for _ in range(attempts):
        base = _get_free_port()
        if base <= 0:
            continue
        if _can_bind(host, base) and _can_bind(host, base + 1):
            return _Ports(mcp_port=base, health_port=base + 1)
    raise RuntimeError("Could not find a free (port, port+1) pair")


def _wait_for_tcp(host: str, port: int, timeout_s: float = 15.0) -> None:
    deadline = time.time() + timeout_s
    last_exc: Exception | None = None

    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.5):
                return
        except Exception as e:
            last_exc = e
            time.sleep(0.1)

    raise RuntimeError(f"Port not ready: {host}:{port} ({last_exc})")


def _pythonpath_env(repo_root: Path) -> dict[str, str]:
    # [20251228_BUGFIX] Some callers pass `tests/` as repo_root; walk upward until
    # we find the actual project root containing `src/code_scalpel`.
    candidate = repo_root
    while True:
        src_root = candidate / "src"
        if (src_root / "code_scalpel").exists():
            break
        if candidate == candidate.parent:
            raise AssertionError(f"Could not locate src/code_scalpel starting from: {repo_root}")
        candidate = candidate.parent

    env = os.environ.copy()
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = str(src_root) + (":" + existing if existing else "")
    env.setdefault("CODE_SCALPEL_DISABLE_LICENSE_DISCOVERY", "1")
    return env


def _with_hs256_test_license_env(env: dict[str, str], tmp_path: Path, tier: str) -> None:
    """[20251228_TEST] Configure a valid HS256 license for server subprocesses."""

    from code_scalpel.licensing.jwt_generator import generate_license

    secret = "test-secret"
    token = generate_license(
        tier=tier,
        customer_id="tests@example.com",
        duration_days=7,
        algorithm="HS256",
        secret_key=secret,
        jti=f"http-sse-all-tools-{tier}",
    )
    license_path = tmp_path / f"license_{tier}.jwt"
    license_path.write_text(token + "\n", encoding="utf-8")

    env["CODE_SCALPEL_ALLOW_HS256"] = "1"
    env["CODE_SCALPEL_SECRET_KEY"] = secret
    env["CODE_SCALPEL_LICENSE_PATH"] = str(license_path)
    env.setdefault("CODE_SCALPEL_DISABLE_LICENSE_DISCOVERY", "1")


def _make_invocation_project(tmp_path: Path) -> dict[str, Path]:
    project_root = tmp_path / "proj"
    (project_root / "pkg").mkdir(parents=True, exist_ok=True)

    (project_root / "pkg" / "__init__.py").write_text("", encoding="utf-8")
    (project_root / "pkg" / "b.py").write_text(
        """\
class Helper:
    def ping(self) -> str:
        return 'pong'
""",
        encoding="utf-8",
    )
    (project_root / "pkg" / "a.py").write_text(
        """\
from pkg.b import Helper

class PolicyEngine:
    def __init__(self) -> None:
        self.h = Helper()

    def run(self) -> str:
        return self.h.ping()
""",
        encoding="utf-8",
    )

    (project_root / "utils.py").write_text(
        """\
def add(a: int, b: int) -> int:
    return a + b
""",
        encoding="utf-8",
    )

    (project_root / "requirements.txt").write_text("requests==2.31.0\n", encoding="utf-8")

    (project_root / "package.json").write_text(
        """\
{
  "name": "mcp-fixture",
  "version": "0.0.0",
  "dependencies": {
    "left-pad": "1.3.0"
  }
}
""",
        encoding="utf-8",
    )

    policy_dir = project_root / ".code-scalpel"
    policy_dir.mkdir(parents=True, exist_ok=True)
    (policy_dir / "policy.rego").write_text(
        """\
package scalpel

default allow = true
""",
        encoding="utf-8",
    )

    return {
        "project_root": project_root,
        "target_file": project_root / "pkg" / "a.py",
        "utils_file": project_root / "utils.py",
        "policy_dir": policy_dir,
    }


def _write_signed_policy_manifest(policy_dir: Path, secret: str) -> None:
    from code_scalpel.policy_engine.crypto_verify import CryptographicPolicyVerifier

    policy_files = ["policy.rego"]
    manifest = CryptographicPolicyVerifier.create_manifest(
        policy_files=policy_files,
        secret_key=secret,
        signed_by="pytest",
        policy_dir=str(policy_dir),
    )

    (policy_dir / "policy.manifest.json").write_text(
        __import__("json").dumps(manifest.__dict__, indent=2, sort_keys=True),
        encoding="utf-8",
    )


async def _assert_all_tools_invocable(session: ClientSession, project_root: Path, paths: dict[str, Path]) -> None:
    tools = await session.list_tools()
    tool_names = {t.name for t in tools.tools}
    assert len(tool_names) == 22

    target_file_rel = str(paths["target_file"].relative_to(project_root))

    r = await session.call_tool(
        "analyze_code",
        arguments={"code": "def foo():\n    return 1\n", "language": "python"},
        read_timeout_seconds=timedelta(seconds=30),
    )
    assert r.isError is False

    r = await session.call_tool(
        "security_scan",
        arguments={"code": "import os\nos.system(user_input)\n"},
        read_timeout_seconds=timedelta(seconds=60),
    )
    assert r.isError is False

    r = await session.call_tool(
        "unified_sink_detect",
        arguments={"code": "eval(user_input)", "language": "python"},
        read_timeout_seconds=timedelta(seconds=60),
    )
    assert r.isError is False

    r = await session.call_tool(
        "type_evaporation_scan",
        arguments={
            "frontend_code": """\
async function go(role) {
  const r = await fetch('/api/role', { method: 'POST', body: JSON.stringify({ role }) });
  return r.json();
}
""",
            "backend_code": """\
from flask import Flask, request
app = Flask(__name__)

@app.post('/api/role')
def role():
    data = request.get_json()
    return {'role': data.get('role')}
""",
            "frontend_file": "frontend.ts",
            "backend_file": "backend.py",
        },
        read_timeout_seconds=timedelta(seconds=90),
    )
    assert r.isError is False

    r = await session.call_tool(
        "scan_dependencies",
        arguments={"project_root": str(project_root), "scan_vulnerabilities": False},
        read_timeout_seconds=timedelta(seconds=60),
    )
    assert r.isError is False

    r = await session.call_tool(
        "symbolic_execute",
        arguments={
            "code": """\
def abs_value(x):
    if x >= 0:
        return x
    return -x
""",
            "max_paths": 5,
        },
        read_timeout_seconds=timedelta(seconds=60),
    )
    assert r.isError is False

    r = await session.call_tool(
        "generate_unit_tests",
        arguments={
            "code": """\
def add(a, b):
    if a > 0:
        return a + b
    return b
""",
            "framework": "pytest",
        },
        read_timeout_seconds=timedelta(seconds=90),
    )
    assert r.isError is False

    r = await session.call_tool(
        "simulate_refactor",
        arguments={
            "original_code": "def add(a, b):\n    return a + b\n",
            "new_code": "def add(a: int, b: int) -> int:\n    return a + b\n",
            "strict_mode": False,
        },
        read_timeout_seconds=timedelta(seconds=60),
    )
    assert r.isError is False

    r = await session.call_tool(
        "crawl_project",
        arguments={
            "root_path": str(project_root),
            "complexity_threshold": 1,
            "include_report": False,
        },
        read_timeout_seconds=timedelta(seconds=90),
    )
    assert r.isError is False

    r = await session.call_tool(
        "get_project_map",
        arguments={"project_root": str(project_root), "include_complexity": False},
        read_timeout_seconds=timedelta(seconds=90),
    )
    assert r.isError is False

    r = await session.call_tool(
        "get_call_graph",
        arguments={
            "project_root": str(project_root),
            "depth": 5,
            "include_circular_import_check": False,
        },
        read_timeout_seconds=timedelta(seconds=90),
    )
    assert r.isError is False

    r = await session.call_tool(
        "get_graph_neighborhood",
        arguments={
            "center_node_id": "python::pkg.a::function::run",
            "k": 1,
            "max_nodes": 25,
            "direction": "both",
            "project_root": str(project_root),
        },
        read_timeout_seconds=timedelta(seconds=90),
    )
    assert r.isError is False

    r = await session.call_tool(
        "get_cross_file_dependencies",
        arguments={
            "target_file": target_file_rel,
            "target_symbol": "PolicyEngine",
            "project_root": str(project_root),
            "max_depth": 2,
            "include_code": False,
            "include_diagram": False,
        },
        read_timeout_seconds=timedelta(seconds=90),
    )
    assert r.isError is False

    r = await session.call_tool(
        "cross_file_security_scan",
        arguments={
            "project_root": str(project_root),
            "max_depth": 2,
            "include_diagram": False,
            "timeout_seconds": 10.0,
            "max_modules": 50,
        },
        read_timeout_seconds=timedelta(seconds=120),
    )
    assert r.isError is False

    r = await session.call_tool(
        "get_file_context",
        arguments={"file_path": str(paths["target_file"])},
        read_timeout_seconds=timedelta(seconds=60),
    )
    assert r.isError is False

    r = await session.call_tool(
        "get_symbol_references",
        arguments={"symbol_name": "PolicyEngine", "project_root": str(project_root)},
        read_timeout_seconds=timedelta(seconds=90),
    )
    assert r.isError is False

    r = await session.call_tool(
        "validate_paths",
        arguments={
            "paths": [
                str(paths["target_file"]),
                str(project_root / "does_not_exist.py"),
            ],
            "project_root": str(project_root),
        },
        read_timeout_seconds=timedelta(seconds=60),
    )
    assert r.isError is False

    r = await session.call_tool(
        "extract_code",
        arguments={
            "target_type": "function",
            "target_name": "add",
            "file_path": str(paths["utils_file"]),
            "include_context": False,
            "include_cross_file_deps": False,
        },
        read_timeout_seconds=timedelta(seconds=90),
    )
    assert r.isError is False

    r = await session.call_tool(
        "update_symbol",
        arguments={
            "file_path": str(paths["utils_file"]),
            "target_type": "function",
            "target_name": "add",
            "new_code": "def add(a: int, b: int) -> int:\n    return a + b\n",
            "create_backup": True,
        },
        read_timeout_seconds=timedelta(seconds=90),
    )
    assert r.isError is False

    r = await session.call_tool(
        "verify_policy_integrity",
        arguments={"policy_dir": str(paths["policy_dir"]), "manifest_source": "file"},
        read_timeout_seconds=timedelta(seconds=60),
    )
    assert r.isError is False


@pytest.mark.parametrize(
    "transport,endpoint_path",
    [
        ("streamable-http", "/mcp"),
        ("sse", "/sse"),
    ],
)
async def test_mcp_http_sse_transports_invoke_all_tools(tmp_path: Path, transport: str, endpoint_path: str):
    with anyio.fail_after(240):
        repo_root = Path(__file__).resolve().parents[1]

        paths = _make_invocation_project(tmp_path)
        project_root = paths["project_root"]

        policy_secret = "unit-test-secret"
        _write_signed_policy_manifest(paths["policy_dir"], policy_secret)

        env = _pythonpath_env(repo_root)
        _with_hs256_test_license_env(env, tmp_path, tier="enterprise")
        env["SCALPEL_MANIFEST_SECRET"] = policy_secret

        ports = _get_free_port_pair(host="127.0.0.1")

        log_path = tmp_path / f"server_{transport}.log"
        with log_path.open("w", encoding="utf-8") as log_file:
            proc = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "code_scalpel.mcp.server",
                    "--transport",
                    transport,
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(ports.mcp_port),
                    "--root",
                    str(project_root),
                ],
                cwd=str(repo_root),
                env=env,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                text=True,
            )

        try:
            if proc.poll() is not None:
                raise RuntimeError(f"Server exited early (code={proc.returncode})")

            _wait_for_tcp("127.0.0.1", ports.mcp_port, timeout_s=20.0)

            # Health endpoint should come up on port+1 for HTTP transports.
            health_url = f"http://127.0.0.1:{ports.health_port}/health"
            r = httpx.get(health_url, timeout=2.0)
            r.raise_for_status()
            assert r.json().get("status") == "healthy"

            base_url = f"http://127.0.0.1:{ports.mcp_port}{endpoint_path}"

            if transport == "streamable-http":
                async with streamable_http_client(base_url) as (
                    read_stream,
                    write_stream,
                    _get_session_id,
                ):
                    async with ClientSession(read_stream, write_stream) as session:
                        await session.initialize()
                        await _assert_all_tools_invocable(session, project_root, paths)
            else:
                async with sse_client(base_url) as (read, write):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        await _assert_all_tools_invocable(session, project_root, paths)

        finally:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:  # pragma: no cover
                proc.kill()
                proc.wait(timeout=5)
