import json
import os
import socket
import subprocess
import time
from dataclasses import dataclass
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


@dataclass(frozen=True)
class _Ports:
    mcp_port: int
    health_port: int


def _docker_available() -> bool:
    try:
        subprocess.run(
            ["docker", "version"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
            timeout=10,
        )
        return True
    except Exception:
        return False


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


def _wait_for_tcp(host: str, port: int, timeout_s: float = 30.0) -> None:
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


def _ensure_docker_image(repo_root: Path) -> str:
    """Return a docker image reference suitable for tests.

    - If CODE_SCALPEL_DOCKER_IMAGE is set, use it.
    - Otherwise build a local image tag (cached by Docker) unless it already exists.
    """

    image = os.environ.get("CODE_SCALPEL_DOCKER_IMAGE")
    if image:
        return image

    image = "code-scalpel:pytest"

    # If the image already exists, reuse it unless REBUILD_DOCKER_IMAGE=1
    rebuild = os.environ.get("REBUILD_DOCKER_IMAGE") == "1"
    if not rebuild:
        probe = subprocess.run(
            ["docker", "image", "inspect", image],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=15,
        )
        if probe.returncode == 0:
            return image

    build = subprocess.run(
        ["docker", "build", "-t", image, "."],
        cwd=str(repo_root),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=15 * 60,
    )
    if build.returncode != 0:
        raise RuntimeError(f"docker build failed:\n{build.stdout}")

    return image


def _tool_json(result) -> dict:
    assert result.isError is False
    assert result.content
    first = result.content[0]
    assert hasattr(first, "text"), f"Unexpected content type: {type(first)!r}"
    return json.loads(first.text)


@pytest.mark.docker
async def test_mcp_docker_streamable_http_end_to_end(tmp_path: Path):
    with anyio.fail_after(8 * 60):
        if os.environ.get("RUN_DOCKER_TESTS") != "1":
            pytest.skip("Set RUN_DOCKER_TESTS=1 to run Docker-based MCP tests")
        if not _docker_available():
            pytest.skip("Docker is not available")

        repo_root = Path(__file__).resolve().parents[1]

        paths = _make_project(tmp_path)
        project_root = paths["project_root"]

        policy_secret = "unit-test-secret"
        _write_signed_policy_manifest(paths["policy_dir"], policy_secret)

        image = _ensure_docker_image(repo_root)

        ports = _get_free_port_pair(host="127.0.0.1")

        container_name = f"code-scalpel-mcp-pytest-{int(time.time())}-{os.getpid()}"

        log_path = tmp_path / "docker_mcp_server.log"
        with log_path.open("w", encoding="utf-8") as log_file:
            proc = subprocess.Popen(
                [
                    "docker",
                    "run",
                    "--rm",
                    "--name",
                    container_name,
                    "-p",
                    f"127.0.0.1:{ports.mcp_port}:8593",
                    "-p",
                    f"127.0.0.1:{ports.health_port}:8594",
                    "-e",
                    "SCALPEL_ROOT=/workspace",
                    "-e",
                    f"SCALPEL_MANIFEST_SECRET={policy_secret}",
                    "-v",
                    f"{project_root}:/workspace",
                    image,
                ],
                stdout=log_file,
                stderr=subprocess.STDOUT,
                text=True,
            )

        try:
            if proc.poll() is not None:
                raise RuntimeError(f"docker run exited early (code={proc.returncode})")

            _wait_for_tcp("127.0.0.1", ports.mcp_port, timeout_s=30.0)

            health_url = f"http://127.0.0.1:{ports.health_port}/health"
            r = httpx.get(health_url, timeout=5.0)
            r.raise_for_status()
            assert r.json().get("status") == "healthy"

            base_url = f"http://127.0.0.1:{ports.mcp_port}/mcp"

            async with streamable_http_client(base_url) as (
                read_stream,
                write_stream,
                _get_session_id,
            ):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()

                    tools = await session.list_tools()
                    assert len({t.name for t in tools.tools}) == 22

                    # Representative file-based operations exercising the volume mount.
                    ctx = await session.call_tool(
                        "get_file_context",
                        arguments={"file_path": "/workspace/pkg/a.py"},
                        read_timeout_seconds=timedelta(seconds=60),
                    )
                    assert _tool_json(ctx).get("success") is True

                    extracted = await session.call_tool(
                        "extract_code",
                        arguments={
                            "target_type": "function",
                            "target_name": "add",
                            "file_path": "/workspace/utils.py",
                            "include_context": False,
                            "include_cross_file_deps": False,
                        },
                        read_timeout_seconds=timedelta(seconds=90),
                    )
                    assert "def add" in (_tool_json(extracted).get("target_code") or "")

                    deps = await session.call_tool(
                        "get_cross_file_dependencies",
                        arguments={
                            "target_file": "pkg/a.py",
                            "target_symbol": "PolicyEngine",
                            "project_root": "/workspace",
                            "max_depth": 2,
                            "include_code": False,
                            "include_diagram": False,
                        },
                        read_timeout_seconds=timedelta(seconds=120),
                    )
                    assert _tool_json(deps).get("success") is True

                    policy = await session.call_tool(
                        "verify_policy_integrity",
                        arguments={
                            "policy_dir": "/workspace/.code-scalpel",
                            "manifest_source": "file",
                        },
                        read_timeout_seconds=timedelta(seconds=60),
                    )
                    assert _tool_json(policy).get("success") is True

        finally:
            try:
                subprocess.run(
                    ["docker", "stop", "-t", "2", container_name],
                    check=False,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=10,
                )
            except Exception:
                pass

            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:  # pragma: no cover
                proc.kill()
                proc.wait(timeout=10)
