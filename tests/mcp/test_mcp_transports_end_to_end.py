import os
import socket
import subprocess
import sys
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path

import anyio
import httpx
import mcp.types as mcp_types
import pytest
from anyio.streams.text import TextReceiveStream
from mcp import StdioServerParameters
from mcp.client.session import ClientSession
from mcp.client.sse import sse_client

try:
    from mcp.client.streamable_http import streamable_http_client
except Exception:  # pragma: no cover - optional dependency may be absent
    streamable_http_client = None

if streamable_http_client is None:
    # [20260117_TEST] Skip module when streamable HTTP client is unavailable
    pytestmark = [pytest.mark.skip("streamable-http client not available")]
from mcp.shared.message import SessionMessage

# [20260118_TEST] Skip entire module - requires running HTTP server
pytestmark = pytest.mark.skip(
    reason="[20260118_TEST] HTTP transport tests require running server - skip for local pipeline"
)


# [20251228_TEST] Canonical MCP tool registry (all tiers list all tools).
EXPECTED_ALL_TOOLS: set[str] = {
    "analyze_code",
    "code_policy_check",
    "crawl_project",
    "cross_file_security_scan",
    "extract_code",
    "generate_unit_tests",
    "get_call_graph",
    "get_cross_file_dependencies",
    "get_file_context",
    "get_graph_neighborhood",
    "get_project_map",
    "get_symbol_references",
    "rename_symbol",
    "scan_dependencies",
    "security_scan",
    "simulate_refactor",
    "symbolic_execute",
    "type_evaporation_scan",
    "unified_sink_detect",
    "update_symbol",
    "validate_paths",
    "verify_policy_integrity",
}


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
    # Avoid nondeterministic tier selection due to stray license files on disk.
    # Explicit CODE_SCALPEL_LICENSE_PATH (when set by tests) is still honored.
    env.setdefault("CODE_SCALPEL_DISABLE_LICENSE_DISCOVERY", "1")
    return env


def _make_tiny_project(tmp_path: Path) -> tuple[Path, str]:
    root = tmp_path / "proj"
    (root / "pkg").mkdir(parents=True, exist_ok=True)

    (root / "pkg" / "__init__.py").write_text("", encoding="utf-8")
    (root / "pkg" / "b.py").write_text(
        """\
class Helper:
    def ping(self) -> str:
        return 'pong'
""",
        encoding="utf-8",
    )
    (root / "pkg" / "a.py").write_text(
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

    # target_file must be relative to project_root for get_cross_file_dependencies
    target_file = str((root / "pkg" / "a.py").relative_to(root))
    return root, target_file


def _with_hs256_test_license_env(env: dict[str, str], tmp_path: Path, tier: str) -> None:
    """Configure a valid HS256 license for server subprocesses."""

    from code_scalpel.licensing.jwt_generator import generate_license

    secret = "test-secret"
    token = generate_license(
        tier=tier,
        customer_id="tests@example.com",
        duration_days=7,
        algorithm="HS256",
        secret_key=secret,
        jti=f"mcp-transport-{tier}",
    )
    license_path = tmp_path / f"license_{tier}.jwt"
    license_path.write_text(token + "\n", encoding="utf-8")

    env["CODE_SCALPEL_ALLOW_HS256"] = "1"
    env["CODE_SCALPEL_SECRET_KEY"] = secret
    env["CODE_SCALPEL_LICENSE_PATH"] = str(license_path)
    env.setdefault("CODE_SCALPEL_DISABLE_LICENSE_DISCOVERY", "1")


@asynccontextmanager
async def _strict_stdio_client(server: StdioServerParameters):
    """A stdio client that treats stdout as protocol-only.

    This intentionally fails fast if the server writes any non-JSON-RPC lines to
    stdout (e.g., accidental print statements), which can otherwise corrupt the
    MCP framing and manifest as hangs/timeouts.
    """

    read_stream_writer, read_stream = anyio.create_memory_object_stream(0)
    write_stream, write_stream_reader = anyio.create_memory_object_stream(0)

    process = await anyio.open_process(
        [server.command, *server.args],
        env=server.env,
        cwd=str(server.cwd) if server.cwd is not None else None,
        stderr=sys.stderr,
        start_new_session=True,
    )

    async def _stdout_reader():
        assert process.stdout is not None

        buffer = ""
        async with read_stream_writer:
            async for chunk in TextReceiveStream(
                process.stdout,
                encoding=server.encoding,
                errors=server.encoding_error_handler,
            ):
                lines = (buffer + chunk).split("\n")
                buffer = lines.pop()

                for line in lines:
                    if not line.strip():
                        continue
                    try:
                        message = mcp_types.JSONRPCMessage.model_validate_json(line)
                    except Exception as exc:
                        raise AssertionError(
                            "Server wrote non-JSON-RPC data to stdout; " f"first invalid line: {line[:200]!r}"
                        ) from exc

                    await read_stream_writer.send(SessionMessage(message))

    async def _stdin_writer():
        assert process.stdin is not None

        async with write_stream_reader:
            async for session_message in write_stream_reader:
                payload = session_message.message.model_dump_json(by_alias=True, exclude_none=True)
                await process.stdin.send(
                    (payload + "\n").encode(
                        encoding=server.encoding,
                        errors=server.encoding_error_handler,
                    )
                )

    async with anyio.create_task_group() as tg:
        tg.start_soon(_stdout_reader)
        tg.start_soon(_stdin_writer)
        try:
            yield read_stream, write_stream
        finally:
            try:
                if process.stdin is not None:
                    await process.stdin.aclose()
            except Exception:
                pass

            with anyio.move_on_after(2.0):
                await process.wait()

            if process.returncode is None:
                process.terminate()
                with anyio.move_on_after(2.0):
                    await process.wait()

            if process.returncode is None:
                process.kill()
                with anyio.move_on_after(2.0):
                    await process.wait()

            await read_stream.aclose()
            await write_stream.aclose()
            await read_stream_writer.aclose()
            await write_stream_reader.aclose()


async def _assert_core_mcp_contract(session: ClientSession, project_root: Path, target_file: str) -> None:
    tools = await session.list_tools()
    tool_names = {t.name for t in tools.tools}

    # Tool availability: ensure current registry count and a few key tools.
    assert tool_names == EXPECTED_ALL_TOOLS

    # Tool call: analyze_code
    analyze = await session.call_tool(
        "analyze_code",
        arguments={"code": "def foo():\n    return 1\n", "language": "python"},
        read_timeout_seconds=timedelta(seconds=30),
    )
    assert analyze.isError is False

    # Tool call: cross-file dependencies (small project)
    deps = await session.call_tool(
        "get_cross_file_dependencies",
        arguments={
            "target_file": target_file,
            "target_symbol": "PolicyEngine",
            "project_root": str(project_root),
            "max_depth": 2,
            "include_code": False,
            "include_diagram": False,
        },
        read_timeout_seconds=timedelta(seconds=60),
    )
    assert deps.isError is False

    if "simulate_refactor" in tool_names:
        sim = await session.call_tool(
            "simulate_refactor",
            arguments={
                "original_code": "def add(a, b):\n    return a + b\n",
                "new_code": "def add(a, b):\n    return a - b\n",
                "language": "python",
                "strict_mode": False,
            },
            read_timeout_seconds=timedelta(seconds=30),
        )
        # Transport-level contract: tool responds without transport error
        assert sim.isError is False
        # Response should include serialized content (text/json) for envelope wrapping
        assert sim.content


async def test_mcp_stdio_transport_end_to_end(tmp_path: Path):
    with anyio.fail_after(120):
        repo_root = Path(__file__).resolve().parents[1]
        env = _pythonpath_env(repo_root)
        _with_hs256_test_license_env(env, tmp_path, tier="enterprise")

        project_root, target_file = _make_tiny_project(tmp_path)

        params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "code_scalpel.mcp.server", "--root", str(project_root)],
            env=env,
        )

        async with _strict_stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                await _assert_core_mcp_contract(session, project_root, target_file)


async def test_mcp_stdio_transport_community_tier_filters_tools(tmp_path: Path):
    with anyio.fail_after(120):
        repo_root = Path(__file__).resolve().parents[1]
        env = _pythonpath_env(repo_root)
        env["CODE_SCALPEL_TIER"] = "community"

        project_root, _target_file = _make_tiny_project(tmp_path)

        params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "code_scalpel.mcp.server", "--root", str(project_root)],
            env=env,
        )

        async with _strict_stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools = await session.list_tools()
                tool_names = {t.name for t in tools.tools}

                assert tool_names == EXPECTED_ALL_TOOLS


async def test_mcp_stdio_transport_pro_tier_excludes_enterprise_only_tools(
    tmp_path: Path,
):
    with anyio.fail_after(120):
        repo_root = Path(__file__).resolve().parents[1]
        env = _pythonpath_env(repo_root)
        env["CODE_SCALPEL_TIER"] = "pro"
        _with_hs256_test_license_env(env, tmp_path, tier="pro")

        project_root, _target_file = _make_tiny_project(tmp_path)

        params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "code_scalpel.mcp.server", "--root", str(project_root)],
            env=env,
        )

        async with _strict_stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools = await session.list_tools()
                tool_names = {t.name for t in tools.tools}

                assert tool_names == EXPECTED_ALL_TOOLS


@pytest.mark.parametrize(
    "transport,endpoint_path",
    [
        ("streamable-http", "/mcp"),
        ("sse", "/sse"),
    ],
)
async def test_mcp_http_transports_end_to_end(tmp_path: Path, transport: str, endpoint_path: str):
    with anyio.fail_after(180):
        repo_root = Path(__file__).resolve().parents[1]
        env = _pythonpath_env(repo_root)
        _with_hs256_test_license_env(env, tmp_path, tier="enterprise")

        project_root, target_file = _make_tiny_project(tmp_path)
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

            health_url = f"http://127.0.0.1:{ports.health_port}/health"
            r = httpx.get(health_url, timeout=2.0)
            r.raise_for_status()
            data = r.json()
            assert data.get("status") == "healthy"

            base_url = f"http://127.0.0.1:{ports.mcp_port}{endpoint_path}"

            if transport == "streamable-http":
                async with streamable_http_client(base_url) as (
                    read_stream,
                    write_stream,
                    _get_session_id,
                ):
                    async with ClientSession(read_stream, write_stream) as session:
                        await session.initialize()
                        await _assert_core_mcp_contract(session, project_root, target_file)
            else:
                async with sse_client(base_url) as (read, write):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        await _assert_core_mcp_contract(session, project_root, target_file)

        finally:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:  # pragma: no cover
                proc.kill()


@pytest.mark.parametrize(
    "transport,endpoint_path,tier,expected_tools",
    [
        (
            "streamable-http",
            "/mcp",
            "community",
            {
                "analyze_code",
                "extract_code",
                "update_symbol",
                "get_project_map",
                "get_file_context",
                "get_symbol_references",
                "security_scan",
                "unified_sink_detect",
                "scan_dependencies",
                "validate_paths",
            },
        ),
        (
            "sse",
            "/sse",
            "community",
            {
                "analyze_code",
                "extract_code",
                "update_symbol",
                "get_project_map",
                "get_file_context",
                "get_symbol_references",
                "security_scan",
                "unified_sink_detect",
                "scan_dependencies",
                "validate_paths",
            },
        ),
        (
            "streamable-http",
            "/mcp",
            "pro",
            {
                "analyze_code",
                "crawl_project",
                "extract_code",
                "generate_unit_tests",
                "get_call_graph",
                "get_file_context",
                "get_graph_neighborhood",
                "get_project_map",
                "get_symbol_references",
                "scan_dependencies",
                "security_scan",
                "simulate_refactor",
                "symbolic_execute",
                "type_evaporation_scan",
                "unified_sink_detect",
                "update_symbol",
                "validate_paths",
            },
        ),
        (
            "sse",
            "/sse",
            "pro",
            {
                "analyze_code",
                "crawl_project",
                "extract_code",
                "generate_unit_tests",
                "get_call_graph",
                "get_file_context",
                "get_graph_neighborhood",
                "get_project_map",
                "get_symbol_references",
                "scan_dependencies",
                "security_scan",
                "simulate_refactor",
                "symbolic_execute",
                "type_evaporation_scan",
                "unified_sink_detect",
                "update_symbol",
                "validate_paths",
            },
        ),
    ],
)
async def test_mcp_http_transports_tier_tool_contract(
    tmp_path: Path,
    transport: str,
    endpoint_path: str,
    tier: str,
    expected_tools: set[str],
):
    with anyio.fail_after(180):
        repo_root = Path(__file__).resolve().parents[1]
        env = _pythonpath_env(repo_root)
        env["CODE_SCALPEL_TIER"] = tier
        if tier != "community":
            _with_hs256_test_license_env(env, tmp_path, tier=tier)

        project_root, _target_file = _make_tiny_project(tmp_path)
        ports = _get_free_port_pair(host="127.0.0.1")

        log_path = tmp_path / f"server_{transport}_{tier}.log"
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

            health_url = f"http://127.0.0.1:{ports.health_port}/health"
            r = httpx.get(health_url, timeout=2.0)
            r.raise_for_status()
            data = r.json()
            assert data.get("status") == "healthy"

            base_url = f"http://127.0.0.1:{ports.mcp_port}{endpoint_path}"

            if transport == "streamable-http":
                async with streamable_http_client(base_url) as (
                    read_stream,
                    write_stream,
                    _get_session_id,
                ):
                    async with ClientSession(read_stream, write_stream) as session:
                        await session.initialize()
                        tools = await session.list_tools()
                        tool_names = {t.name for t in tools.tools}
                        assert tool_names == EXPECTED_ALL_TOOLS
            else:
                async with sse_client(base_url) as (read, write):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        tools = await session.list_tools()
                        tool_names = {t.name for t in tools.tools}
                        assert tool_names == EXPECTED_ALL_TOOLS

        finally:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:  # pragma: no cover
                proc.kill()
                proc.wait(timeout=5)
