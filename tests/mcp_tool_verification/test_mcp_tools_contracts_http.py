import json
import os
import socket
import subprocess
import sys
import time
from contextlib import asynccontextmanager
from datetime import timedelta
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


def _pythonpath_env(repo_root: Path) -> dict[str, str]:
    src_root = repo_root / "src"
    assert (src_root / "code_scalpel").exists()

    env = os.environ.copy()
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = str(src_root) + (":" + existing if existing else "")
    return env


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


def _get_free_port_pair(host: str = "127.0.0.1", attempts: int = 200) -> tuple[int, int]:
    for _ in range(attempts):
        base = _get_free_port()
        if base <= 0:
            continue
        if _can_bind(host, base) and _can_bind(host, base + 1):
            return base, base + 1
    raise RuntimeError("Could not find a free (port, port+1) pair")


def _wait_for_tcp(host: str, port: int, timeout_s: float = 20.0) -> None:
    deadline = time.time() + timeout_s
    last_exc: Exception | None = None

    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.5):
                return
        except Exception as e:  # noqa: BLE001
            last_exc = e
            time.sleep(0.1)

    raise RuntimeError(f"Port not ready: {host}:{port} ({last_exc})")


def _make_project(tmp_path: Path) -> dict[str, Path]:
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
    policy_file = policy_dir / "policy.rego"
    policy_file.write_text(
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
        "policy_file": policy_file,
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
        json.dumps(manifest.__dict__, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _tool_json(result) -> dict:
    assert result.isError is False
    assert result.content, "Tool returned empty content"
    first = result.content[0]
    assert hasattr(first, "text"), f"Unexpected content type: {type(first)!r}"
    text = first.text
    try:
        envelope = json.loads(text)
    except json.JSONDecodeError as exc:
        raise AssertionError("Tool content is not valid JSON; first 200 chars: " + repr(text[:200])) from exc

    # [v3.2.8] Validate universal response envelope
    assert "tier" in envelope, "Response missing 'tier' field"
    assert "tool_version" in envelope, "Response missing 'tool_version' field"
    assert "tool_id" in envelope, "Response missing 'tool_id' field"
    assert "request_id" in envelope, "Response missing 'request_id' field"
    assert "capabilities" in envelope, "Response missing 'capabilities' field"
    assert "data" in envelope, "Response missing 'data' field"

    # Return the data payload (unwrapped)
    return envelope["data"]


@asynccontextmanager
async def _http_session_for_project(tmp_path: Path):
    repo_root = Path(__file__).resolve().parents[2]
    paths = _make_project(tmp_path)

    policy_secret = "unit-test-secret"
    _write_signed_policy_manifest(paths["policy_dir"], policy_secret)

    env = _pythonpath_env(repo_root)
    env["SCALPEL_MANIFEST_SECRET"] = policy_secret

    host = "127.0.0.1"
    mcp_port, health_port = _get_free_port_pair(host=host)

    log_path = tmp_path / "mcp_http_contract.log"
    with log_path.open("w", encoding="utf-8") as log_file:
        proc = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "code_scalpel.mcp.server",
                "--transport",
                "streamable-http",
                "--host",
                host,
                "--port",
                str(mcp_port),
                "--root",
                str(paths["project_root"]),
            ],
            env=env,
            cwd=str(repo_root),
            stdout=log_file,
            stderr=subprocess.STDOUT,
            text=True,
        )

    try:
        if proc.poll() is not None:
            raise RuntimeError(f"HTTP MCP server exited early (code={proc.returncode})")

        _wait_for_tcp(host, mcp_port, timeout_s=20.0)

        health_url = f"http://{host}:{health_port}/health"
        r = httpx.get(health_url, timeout=2.0)
        r.raise_for_status()
        assert r.json().get("status") == "healthy"

        base_url = f"http://{host}:{mcp_port}/mcp"
        async with streamable_http_client(base_url) as (
            read_stream,
            write_stream,
            _get_session_id,
        ):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                yield session, paths

    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:  # pragma: no cover
            proc.kill()
            proc.wait(timeout=5)


async def test_http_contract_analyze_extract_and_policy(tmp_path: Path):
    with anyio.fail_after(240):
        async with _http_session_for_project(tmp_path) as (session, paths):
            tools = await session.list_tools()
            assert len({t.name for t in tools.tools}) == 22

            ok = await session.call_tool(
                "analyze_code",
                arguments={"code": "def foo():\n    return 1\n", "language": "python"},
                read_timeout_seconds=timedelta(seconds=30),
            )
            ok_json = _tool_json(ok)
            assert ok_json.get("success") is True

            extracted = await session.call_tool(
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
            extracted_json = _tool_json(extracted)
            assert extracted_json.get("success") is True
            assert "def add" in (extracted_json.get("target_code") or "")

            verify_ok = await session.call_tool(
                "verify_policy_integrity",
                arguments={
                    "policy_dir": str(paths["policy_dir"]),
                    "manifest_source": "file",
                },
                read_timeout_seconds=timedelta(seconds=60),
            )
            verify_ok_json = _tool_json(verify_ok)
            assert verify_ok_json.get("success") is True
