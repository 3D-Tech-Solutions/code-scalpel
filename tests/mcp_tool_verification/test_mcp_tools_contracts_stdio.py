import json
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
    src_root = repo_root / "src"
    assert (src_root / "code_scalpel").exists()

    env = os.environ.copy()
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = str(src_root) + (":" + existing if existing else "")
    return env


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

def process_request(engine: PolicyEngine) -> str:
    '''Standalone function for graph neighborhood testing.'''
    return engine.run()
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


def _tool_envelope(result) -> dict:
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
    for key in (
        "tier",
        "tool_version",
        "tool_id",
        "request_id",
        "capabilities",
        "duration_ms",
        "error",
        "upgrade_hints",
        "data",
    ):
        assert key in envelope, f"Response missing '{key}' field"

    return envelope


def _tool_json(result) -> dict:
    envelope = _tool_envelope(result)
    return envelope["data"]


@asynccontextmanager
async def _strict_stdio_client(server: StdioServerParameters):
    """Stdio client that treats stdout as JSON-RPC only."""

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


@asynccontextmanager
async def _session_for_project(tmp_path: Path):
    repo_root = Path(__file__).resolve().parents[2]
    paths = _make_project(tmp_path)

    policy_secret = "unit-test-secret"
    _write_signed_policy_manifest(paths["policy_dir"], policy_secret)

    env = _pythonpath_env(repo_root)
    env["SCALPEL_MANIFEST_SECRET"] = policy_secret
    # [20251226_BUGFIX] Set tier to enterprise for full feature testing
    env["CODE_SCALPEL_TIER"] = "enterprise"

    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "code_scalpel.mcp.server", "--root", str(paths["project_root"])],
        env=env,
    )

    async with _strict_stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            yield session, paths


async def test_tool_analyze_extract_update_and_context(tmp_path: Path):
    with anyio.fail_after(180):
        async with _session_for_project(tmp_path) as (session, paths):
            tools = await session.list_tools()
            assert len({t.name for t in tools.tools}) == 22

            ok = await session.call_tool(
                "analyze_code",
                arguments={"code": "def foo():\n    return 1\n", "language": "python"},
                read_timeout_seconds=timedelta(seconds=30),
            )
            ok_json = _tool_json(ok)
            assert ok_json.get("success") is True
            assert "functions" in ok_json

            bad = await session.call_tool(
                "analyze_code",
                arguments={"code": "def oops(:\n  pass\n", "language": "python"},
                read_timeout_seconds=timedelta(seconds=30),
            )
            bad_env = _tool_envelope(bad)
            bad_json = bad_env["data"]
            assert bad_json.get("success") is False
            err = bad_env.get("error")
            assert isinstance(err, dict)
            assert isinstance(err.get("error"), str) and err.get("error")

            ctx = await session.call_tool(
                "get_file_context",
                arguments={"file_path": str(paths["target_file"])},
                read_timeout_seconds=timedelta(seconds=60),
            )
            ctx_json = _tool_json(ctx)
            assert ctx_json.get("success") is True
            assert ctx_json.get("file_path")

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

            updated = await session.call_tool(
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
            updated_json = _tool_json(updated)
            assert updated_json.get("success") is True
            backup_path = updated_json.get("backup_path")
            assert backup_path and Path(backup_path).exists()

            refs = await session.call_tool(
                "get_symbol_references",
                arguments={
                    "symbol_name": "PolicyEngine",
                    "project_root": str(paths["project_root"]),
                },
                read_timeout_seconds=timedelta(seconds=90),
            )
            refs_json = _tool_json(refs)
            assert refs_json.get("success") is True
            assert refs_json.get("total_references", 0) >= 1

            vp = await session.call_tool(
                "validate_paths",
                arguments={
                    "paths": [
                        str(paths["target_file"]),
                        str(paths["project_root"] / "does_not_exist.py"),
                    ],
                    "project_root": str(paths["project_root"]),
                },
                read_timeout_seconds=timedelta(seconds=60),
            )
            vp_json = _tool_json(vp)
            assert "accessible" in vp_json and "inaccessible" in vp_json
            assert any(str(paths["target_file"]) == p for p in vp_json.get("accessible", []))


async def test_tool_security_type_evaporation_and_testing(tmp_path: Path):
    with anyio.fail_after(180):
        async with _session_for_project(tmp_path) as (session, paths):
            sec = await session.call_tool(
                "security_scan",
                arguments={"code": "import os\nos.system(user_input)\n"},
                read_timeout_seconds=timedelta(seconds=60),
            )
            sec_json = _tool_json(sec)
            assert "has_vulnerabilities" in sec_json

            sinks = await session.call_tool(
                "unified_sink_detect",
                arguments={
                    "code": "eval(user_input)",
                    "language": "python",
                    "min_confidence": 0.0,
                },
                read_timeout_seconds=timedelta(seconds=60),
            )
            sinks_json = _tool_json(sinks)
            assert sinks_json.get("success") is True
            assert "sinks" in sinks_json

            tev = await session.call_tool(
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
            tev_json = _tool_json(tev)
            assert "success" in tev_json
            assert "frontend_vulnerabilities" in tev_json
            assert "backend_vulnerabilities" in tev_json

            sym = await session.call_tool(
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
            sym_json = _tool_json(sym)
            assert sym_json.get("success") is True
            assert sym_json.get("paths_explored", 0) >= 1

            gen = await session.call_tool(
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
            gen_json = _tool_json(gen)
            assert "pytest_code" in gen_json

            sim_err = await session.call_tool(
                "simulate_refactor",
                arguments={"original_code": "def x():\n    return 1\n"},
                read_timeout_seconds=timedelta(seconds=60),
            )
            sim_err_json = _tool_json(sim_err)
            assert sim_err_json.get("success") is False

            sim_ok = await session.call_tool(
                "simulate_refactor",
                arguments={
                    "original_code": "def add(a, b):\n    return a + b\n",
                    "new_code": "def add(a: int, b: int) -> int:\n    return a + b\n",
                    "strict_mode": False,
                },
                read_timeout_seconds=timedelta(seconds=60),
            )
            sim_ok_json = _tool_json(sim_ok)
            assert sim_ok_json.get("success") is True


async def test_tool_graphs_cross_file_and_policy(tmp_path: Path):
    with anyio.fail_after(240):
        async with _session_for_project(tmp_path) as (session, paths):
            crawl = await session.call_tool(
                "crawl_project",
                arguments={
                    "root_path": str(paths["project_root"]),
                    "include_report": False,
                },
                read_timeout_seconds=timedelta(seconds=120),
            )
            crawl_json = _tool_json(crawl)
            assert crawl_json.get("success") is True

            pm = await session.call_tool(
                "get_project_map",
                arguments={
                    "project_root": str(paths["project_root"]),
                    "include_complexity": False,
                },
                read_timeout_seconds=timedelta(seconds=120),
            )
            pm_json = _tool_json(pm)
            assert pm_json.get("success") is True

            cg = await session.call_tool(
                "get_call_graph",
                arguments={
                    "project_root": str(paths["project_root"]),
                    "depth": 5,
                    "include_circular_import_check": False,
                },
                read_timeout_seconds=timedelta(seconds=120),
            )
            cg_json = _tool_json(cg)
            assert cg_json.get("success") is True
            assert "nodes" in cg_json and "edges" in cg_json

            neigh_bad = await session.call_tool(
                "get_graph_neighborhood",
                arguments={
                    "center_node_id": "python::pkg.a::function::process_request",
                    "direction": "sideways",
                    "project_root": str(paths["project_root"]),
                },
                read_timeout_seconds=timedelta(seconds=120),
            )
            neigh_bad_json = _tool_json(neigh_bad)
            assert neigh_bad_json.get("success") is False
            assert neigh_bad_json.get("error")

            neigh_ok = await session.call_tool(
                "get_graph_neighborhood",
                arguments={
                    "center_node_id": "python::pkg.a::function::process_request",
                    "k": 1,
                    "max_nodes": 25,
                    "direction": "both",
                    "project_root": str(paths["project_root"]),
                },
                read_timeout_seconds=timedelta(seconds=120),
            )
            neigh_ok_json = _tool_json(neigh_ok)
            assert neigh_ok_json.get("success") is True

            target_file_rel = str(paths["target_file"].relative_to(paths["project_root"]))
            deps_ok = await session.call_tool(
                "get_cross_file_dependencies",
                arguments={
                    "target_file": target_file_rel,
                    "target_symbol": "PolicyEngine",
                    "project_root": str(paths["project_root"]),
                    "max_depth": 2,
                    "include_code": False,
                    "include_diagram": False,
                },
                read_timeout_seconds=timedelta(seconds=120),
            )
            deps_ok_json = _tool_json(deps_ok)
            assert deps_ok_json.get("success") is True

            deps_err = await session.call_tool(
                "get_cross_file_dependencies",
                arguments={
                    "target_file": "nope.py",
                    "target_symbol": "DoesNotExist",
                    "project_root": str(paths["project_root"]),
                    "max_depth": 1,
                    "include_code": False,
                    "include_diagram": False,
                },
                read_timeout_seconds=timedelta(seconds=60),
            )
            deps_err_json = _tool_json(deps_err)
            assert deps_err_json.get("success") is False
            assert deps_err_json.get("error")

            xsec = await session.call_tool(
                "cross_file_security_scan",
                arguments={
                    "project_root": str(paths["project_root"]),
                    "max_depth": 2,
                    "include_diagram": False,
                    "timeout_seconds": 10.0,
                    "max_modules": 50,
                },
                read_timeout_seconds=timedelta(seconds=180),
            )
            xsec_json = _tool_json(xsec)
            assert "risk_level" in xsec_json

            dep_scan = await session.call_tool(
                "scan_dependencies",
                arguments={
                    "project_root": str(paths["project_root"]),
                    "scan_vulnerabilities": False,
                },
                read_timeout_seconds=timedelta(seconds=60),
            )
            dep_scan_json = _tool_json(dep_scan)
            assert dep_scan_json.get("success") is True

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

            paths["policy_file"].write_text(
                paths["policy_file"].read_text(encoding="utf-8") + "\n# tampered\n",
                encoding="utf-8",
            )

            verify_bad = await session.call_tool(
                "verify_policy_integrity",
                arguments={
                    "policy_dir": str(paths["policy_dir"]),
                    "manifest_source": "file",
                },
                read_timeout_seconds=timedelta(seconds=60),
            )
            verify_bad_json = _tool_json(verify_bad)
            assert verify_bad_json.get("success") is False
            assert verify_bad_json.get("error")
