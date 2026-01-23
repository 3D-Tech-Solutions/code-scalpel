import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import anyio
import httpx
import pytest
from mcp.client.session import ClientSession

try:
    from mcp.client.streamable_http import streamable_http_client
except Exception:  # pragma: no cover - optional dependency may be absent
    streamable_http_client = None

if streamable_http_client is None:
    # [20260117_TEST] Skip module when streamable HTTP client is unavailable
    pytestmark = [pytest.mark.skip("streamable-http client not available")]

pytestmark = pytest.mark.asyncio


def _get_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_for_port_open(host: str, port: int, timeout_s: float = 10.0) -> None:
    deadline = time.time() + timeout_s

    last_exc: Exception | None = None
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.5):
                return
            return
        except Exception as e:  # pragma: no cover
            last_exc = e
            time.sleep(0.1)

    raise RuntimeError(f"Server port not ready: {host}:{port} ({last_exc})")


def _tail_text(path: Path, max_lines: int = 40) -> str:
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception:
        return "(no server log available)"
    tail = lines[-max_lines:]
    return "\n".join(tail) if tail else "(empty server log)"


@pytest.mark.parametrize("transport,expected_path", [("streamable-http", "/mcp"), ("sse", "/sse")])
async def test_http_transport_endpoint_path_matches_fastmcp_defaults(
    tmp_path: Path, transport: str, expected_path: str
):
    """Regression test for the /sse vs /mcp mismatch.

    FastMCP mounts:
      - streamable-http at /mcp
      - sse at /sse

    Code Scalpel should advertise and accept the correct path for the selected transport.
    """

    with anyio.fail_after(90):
        host = "127.0.0.1"
        port = _get_free_port()

        # [20251228_BUGFIX] Walk upward until we find the project root containing
        # `src/code_scalpel`.
        candidate = Path(__file__).resolve().parents[1]
        while True:
            src_root = candidate / "src"
            if (src_root / "code_scalpel").exists():
                repo_root = candidate
                break
            if candidate == candidate.parent:
                raise AssertionError("Could not locate src/code_scalpel from tests")
            candidate = candidate.parent

        log_path = tmp_path / f"mcp_server_{transport}.log"

        # Minimal project root (avoids depending on external repos)
        project_root = tmp_path
        (project_root / "pkg").mkdir(parents=True, exist_ok=True)
        (project_root / "pkg" / "__init__.py").write_text("", encoding="utf-8")

        env = os.environ.copy()
        existing_pythonpath = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = str(src_root) + (":" + existing_pythonpath if existing_pythonpath else "")
        # Avoid nondeterministic tier selection due to stray license files on disk.
        env.setdefault("CODE_SCALPEL_DISABLE_LICENSE_DISCOVERY", "1")

        with log_path.open("w", encoding="utf-8") as log_file:
            proc = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "code_scalpel.mcp.server",
                    "--transport",
                    transport,
                    "--host",
                    host,
                    "--port",
                    str(port),
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
            deadline = time.time() + 20.0
            while time.time() < deadline:
                if proc.poll() is not None:
                    raise RuntimeError(
                        f"MCP server subprocess exited early (code={proc.returncode}).\n"
                        f"--- server log tail ---\n{_tail_text(log_path)}"
                    )
                try:
                    _wait_for_port_open(host, port, timeout_s=0.5)
                    break
                except Exception:
                    time.sleep(0.1)
            else:
                raise RuntimeError(
                    f"MCP server did not open port {host}:{port} in time.\n"
                    f"--- server log tail ---\n{_tail_text(log_path)}"
                )

            url = f"http://{host}:{port}{expected_path}"

            if transport == "streamable-http":
                async with streamable_http_client(url) as (
                    read_stream,
                    write_stream,
                    _get_session_id,
                ):
                    async with ClientSession(read_stream, write_stream) as session:
                        await session.initialize()
                        tools = await session.list_tools()
                        tool_names = {t.name for t in tools.tools}
                        assert "analyze_code" in tool_names
                        assert "get_cross_file_dependencies" in tool_names
                        assert len(tool_names) == 22
            else:
                try:
                    r = httpx.get(url, timeout=httpx.Timeout(2.0, read=0.2))
                    assert r.status_code != 404
                except httpx.ReadTimeout:
                    pass

        finally:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:  # pragma: no cover
                proc.kill()
                proc.wait(timeout=5)
