import os
import sys
from contextlib import asynccontextmanager
from datetime import timedelta
from pathlib import Path

import anyio
import mcp.types as mcp_types
import pytest
from anyio.streams.text import TextReceiveStream
from mcp import StdioServerParameters
from mcp.client.session import ClientSession
from mcp.shared.message import SessionMessage

pytestmark = pytest.mark.asyncio


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
        jti=f"stdio-all-tools-{tier}",
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

    (project_root / "vuln.py").write_text(
        """\
import os

def run(cmd: str) -> None:
    os.system(cmd)
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
        "vuln_file": project_root / "vuln.py",
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


@asynccontextmanager
async def _strict_stdio_client(server: StdioServerParameters):
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


async def test_mcp_stdio_invokes_all_tools(tmp_path: Path):
    with anyio.fail_after(180):
        repo_root = Path(__file__).resolve().parents[1]

    paths = _make_invocation_project(tmp_path)
    project_root = paths["project_root"]

    policy_secret = "unit-test-secret"
    _write_signed_policy_manifest(paths["policy_dir"], policy_secret)

    env = _pythonpath_env(repo_root)
    _with_hs256_test_license_env(env, tmp_path, tier="enterprise")
    env["SCALPEL_MANIFEST_SECRET"] = policy_secret

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
            assert len(tool_names) == 22

            # 1) Analysis
            r = await session.call_tool(
                "analyze_code",
                arguments={"code": "def foo():\n    return 1\n", "language": "python"},
                read_timeout_seconds=timedelta(seconds=30),
            )
            assert r.isError is False

            # 2) Security tools
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
                arguments={
                    "project_root": str(project_root),
                    "scan_vulnerabilities": False,
                },
                read_timeout_seconds=timedelta(seconds=60),
            )
            assert r.isError is False

            # 3) Symbolic / testing
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

            # 4) Project discovery / graph
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
                arguments={
                    "project_root": str(project_root),
                    "include_complexity": False,
                },
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

            # Use the returned call graph to pick a valid node id for neighborhood.
            # The tool response is encoded as Text content; assert only tool success here.
            # We can still validate neighborhood on a best-effort basis by probing known ids.
            graph_node_id = "python::pkg.a::function::run"
            r = await session.call_tool(
                "get_graph_neighborhood",
                arguments={
                    "center_node_id": graph_node_id,
                    "k": 1,
                    "max_nodes": 25,
                    "direction": "both",
                    "project_root": str(project_root),
                },
                read_timeout_seconds=timedelta(seconds=90),
            )
            assert r.isError is False

            # 5) Cross-file tools
            target_file_rel = str(paths["target_file"].relative_to(project_root))
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

            # 6) Context tools
            r = await session.call_tool(
                "get_file_context",
                arguments={"file_path": str(paths["target_file"])},
                read_timeout_seconds=timedelta(seconds=60),
            )
            assert r.isError is False

            r = await session.call_tool(
                "get_symbol_references",
                arguments={
                    "symbol_name": "PolicyEngine",
                    "project_root": str(project_root),
                },
                read_timeout_seconds=timedelta(seconds=90),
            )
            assert r.isError is False

            # 7) Filesystem validation
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

            # 8) Extraction + patching
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

            # 9) Governance / crypto
            r = await session.call_tool(
                "verify_policy_integrity",
                arguments={
                    "policy_dir": str(paths["policy_dir"]),
                    "manifest_source": "file",
                },
                read_timeout_seconds=timedelta(seconds=60),
            )
            assert r.isError is False

            # Sanity: ensure the server didn't accidentally launch subprocesses that keep running.
            # (The strict stdio wrapper will terminate the server at exit.)
