import json
import os
import platform
import socket
import subprocess
import sys
import time
import traceback
import uuid
from contextlib import AsyncExitStack, asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

import anyio
import httpx
import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.sse import sse_client
from mcp.client.stdio import stdio_client

try:
    from mcp.client.streamable_http import streamable_http_client
except Exception:  # pragma: no cover - optional dependency may be absent
    streamable_http_client = None

pytestmark = [pytest.mark.asyncio, pytest.mark.ninja_warrior]
if streamable_http_client is None:
    # [20260117_TEST] Skip when streamable HTTP client is unavailable
    pytestmark.append(pytest.mark.skip("streamable-http client not available"))


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _run_git(args: list[str], *, cwd: Path, timeout_s: float = 2.0) -> str | None:
    try:
        cp = subprocess.run(
            ["git", *args],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=timeout_s,
            check=False,
        )
    except Exception:  # noqa: BLE001
        return None

    if cp.returncode != 0:
        return None
    return cp.stdout.strip()


def _git_info(repo_path: Path) -> dict | None:
    if not (repo_path / ".git").exists():
        return None

    sha = _run_git(["rev-parse", "HEAD"], cwd=repo_path)
    if not sha:
        return None

    branch = _run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=repo_path)
    status = _run_git(["status", "--porcelain"], cwd=repo_path)
    dirty = bool(status)
    return {
        "path": str(repo_path),
        "sha": sha,
        "branch": branch,
        "dirty": dirty,
    }


def _safe_slug(text: str) -> str:
    return "".join(ch if (ch.isalnum() or ch in ("-", "_")) else "_" for ch in text)


def _evidence_dir(tmp_path: Path) -> Path:
    raw = os.environ.get("NINJA_WARRIOR_EVIDENCE_DIR")
    if raw:
        base = Path(raw).expanduser().resolve()
    else:
        base = _repo_root() / "evidence" / "ninja-warrior"
    base.mkdir(parents=True, exist_ok=True)
    return base


def _json_size_bytes(data: object) -> int:
    try:
        return len(json.dumps(data, ensure_ascii=False, sort_keys=True).encode("utf-8"))
    except Exception:  # noqa: BLE001
        return 10**9


def _summarize_json(data: object) -> object:
    if isinstance(data, dict):
        summary: dict[str, object] = {
            "_type": "dict",
            "keys": sorted(list(data.keys()))[:200],
        }
        if "nodes" in data and isinstance(data.get("nodes"), list):
            summary["nodes_count"] = len(data["nodes"])  # type: ignore[index]
        if "edges" in data and isinstance(data.get("edges"), list):
            summary["edges_count"] = len(data["edges"])  # type: ignore[index]
        if "files" in data and isinstance(data.get("files"), list):
            summary["files_count"] = len(data["files"])  # type: ignore[index]
        if "success" in data:
            summary["success"] = data.get("success")
        if "risk_level" in data:
            summary["risk_level"] = data.get("risk_level")
        return summary
    if isinstance(data, list):
        return {"_type": "list", "length": len(data)}
    if isinstance(data, str):
        return data[:500]
    return data


class EvidenceRecorder:
    def __init__(
        self,
        *,
        test_name: str,
        transport: str,
        nw_root: Path,
        analysis_root: Path,
        evidence_dir: Path,
        server: dict | None = None,
    ) -> None:
        self._started_at_utc = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        self._events: list[dict] = []
        self._tool_calls: list[dict] = []
        self._failure: dict | None = None

        self.run_id = uuid.uuid4().hex[:12]
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        filename = f"ninja_warrior_{_safe_slug(test_name)}_{_safe_slug(transport)}_{stamp}_{self.run_id}.json"
        self.path = evidence_dir / filename

        self._started_monotonic = time.monotonic()

        self._base: dict = {
            "schema_version": 1,
            "created_at_utc": self._started_at_utc,
            "run_id": self.run_id,
            "test_name": test_name,
            "transport": transport,
            "ninja_warrior_root": str(nw_root),
            "analysis_root": str(analysis_root),
            "python": {
                "executable": sys.executable,
                "version": sys.version,
            },
            "platform": {
                "platform": platform.platform(),
            },
            "env": {
                "RUN_NINJA_WARRIOR": os.environ.get("RUN_NINJA_WARRIOR"),
                "RUN_NINJA_WARRIOR_HEAVY": os.environ.get("RUN_NINJA_WARRIOR_HEAVY"),
                "NINJA_WARRIOR_ROOT": os.environ.get("NINJA_WARRIOR_ROOT"),
                "CI": os.environ.get("CI"),
                "GITHUB_ACTIONS": os.environ.get("GITHUB_ACTIONS"),
            },
            "repos": {
                "code_scalpel": _git_info(_repo_root()),
                "ninja_warrior": _git_info(nw_root),
            },
            "server": server,
        }

    def record_event(self, name: str, **fields: object) -> None:
        self._events.append({"name": name, "ts": time.time(), **fields})

    def record_tool_call(
        self,
        *,
        tool_name: str,
        arguments: dict,
        read_timeout_seconds: float | None,
        duration_seconds: float,
        result_json: object | None,
        is_error: bool,
        parse_error: str | None = None,
    ) -> None:
        payload: dict[str, object] = {
            "tool_name": tool_name,
            "arguments": arguments,
            "read_timeout_seconds": read_timeout_seconds,
            "duration_seconds": round(duration_seconds, 6),
            "is_error": bool(is_error),
            "parse_error": parse_error,
        }

        if result_json is not None:
            size = _json_size_bytes(result_json)
            payload["result_size_bytes"] = size
            if size <= 50_000:
                payload["result_json"] = result_json
            else:
                payload["result_truncated"] = True
                payload["result_summary"] = _summarize_json(result_json)

        self._tool_calls.append(payload)

    def record_failure(self, exc: BaseException) -> None:
        self._failure = {
            "type": type(exc).__name__,
            "message": str(exc),
            "traceback": traceback.format_exc(),
        }

    def write(self) -> None:
        ended_at_utc = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        duration_seconds = time.monotonic() - self._started_monotonic
        status = "failed" if self._failure else "passed"

        report = {
            **self._base,
            "ended_at_utc": ended_at_utc,
            "duration_seconds": round(duration_seconds, 6),
            "status": status,
            "events": self._events,
            "tool_calls": self._tool_calls,
            "failure": self._failure,
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")

        try:
            index_path = self.path.parent / "index.ndjson"
            index_entry = {
                "schema_version": 1,
                "created_at_utc": report.get("created_at_utc"),
                "ended_at_utc": ended_at_utc,
                "run_id": self.run_id,
                "status": status,
                "transport": report.get("transport"),
                "test_name": report.get("test_name"),
                "analysis_root": report.get("analysis_root"),
                "ninja_warrior_root": report.get("ninja_warrior_root"),
                "repos": report.get("repos"),
                "server": report.get("server"),
                "evidence_path": str(self.path),
                "tool_calls": len(self._tool_calls),
                "duration_seconds": round(duration_seconds, 6),
            }
            with index_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(index_entry, sort_keys=True) + "\n")
        except Exception:  # noqa: BLE001
            # Evidence is best-effort; never fail the test just because indexing failed.
            return


def _pythonpath_env(repo_root: Path) -> dict[str, str]:
    src_root = repo_root / "src"
    assert (src_root / "code_scalpel").exists()

    env = os.environ.copy()
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = str(src_root) + (":" + existing if existing else "")
    env.setdefault("CODE_SCALPEL_DISABLE_LICENSE_DISCOVERY", "1")
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


def _wait_for_tcp(host: str, port: int, timeout_s: float = 30.0) -> None:
    deadline = time.time() + timeout_s
    last_exc: Exception | None = None

    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.5):
                return
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            time.sleep(0.1)

    raise RuntimeError(f"Port not ready: {host}:{port} ({last_exc})")


def _tool_json(result) -> dict:
    assert result.isError is False
    assert result.content, "Tool returned empty content"
    first = result.content[0]
    assert hasattr(first, "text"), f"Unexpected content type: {type(first)!r}"
    text = first.text

    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise AssertionError("Tool content is not valid JSON; first 200 chars: " + repr(text[:200])) from exc


def _ninja_warrior_root() -> Path:
    default = Path("/mnt/k/backup/Develop/Code-Scalpel-Ninja-Warrior")
    raw = os.environ.get("NINJA_WARRIOR_ROOT")
    root = Path(raw).expanduser() if raw else default
    return root.resolve()


def _require_ninja_warrior() -> Path:
    if os.environ.get("RUN_NINJA_WARRIOR") != "1":
        pytest.skip("Set RUN_NINJA_WARRIOR=1 to enable Ninja Warrior acceptance harness")

    root = _ninja_warrior_root()
    if not root.exists():
        pytest.skip(f"Ninja Warrior repo not found at: {root}")

    if not (root / "torture-tests").exists():
        pytest.skip(f"Not a Ninja Warrior repo (missing torture-tests/): {root}")

    return root


def _require_ninja_warrior_heavy() -> None:
    if os.environ.get("RUN_NINJA_WARRIOR_HEAVY") != "1":
        pytest.skip("Set RUN_NINJA_WARRIOR_HEAVY=1 to enable heavy Ninja Warrior harness")


@asynccontextmanager
async def _stdio_session_for_root(nw_root: Path):
    repo_root = Path(__file__).resolve().parents[1]
    env = _pythonpath_env(repo_root)

    server_params = StdioServerParameters(
        command=sys.executable,
        args=[
            "-m",
            "code_scalpel.mcp.server",
            "--transport",
            "stdio",
            "--root",
            str(nw_root),
        ],
        env=env,
    )

    async with AsyncExitStack() as stack:
        read_stream, write_stream = await stack.enter_async_context(stdio_client(server_params))
        session = await stack.enter_async_context(ClientSession(read_stream, write_stream))
        await session.initialize()
        yield session


@asynccontextmanager
async def _http_session_for_root(nw_root: Path, log_dir: Path, transport: str):
    """Start an HTTP-transport MCP server and return a connected session.

    transport: "streamable-http" or "sse".
    """

    assert transport in ("streamable-http", "sse")

    repo_root = Path(__file__).resolve().parents[1]
    env = _pythonpath_env(repo_root)

    host = "127.0.0.1"
    mcp_port, health_port = _get_free_port_pair(host=host)

    log_path = log_dir / f"mcp_{transport.replace('-', '_')}_server.log"
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
                str(mcp_port),
                "--root",
                str(nw_root),
            ],
            env=env,
            cwd=str(repo_root),
            stdout=log_file,
            stderr=subprocess.STDOUT,
            text=True,
        )

    try:
        if proc.poll() is not None:
            raise RuntimeError(f"{transport} MCP server exited early (code={proc.returncode})")

        _wait_for_tcp(host, mcp_port, timeout_s=30.0)

        health_url = f"http://{host}:{health_port}/health"
        r = httpx.get(health_url, timeout=2.0)
        r.raise_for_status()
        assert r.json().get("status") == "healthy"

        if transport == "streamable-http":
            base_url = f"http://{host}:{mcp_port}/mcp"
            async with streamable_http_client(base_url) as (
                read_stream,
                write_stream,
                _get_session_id,
            ):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    yield session, {
                        "transport": transport,
                        "host": host,
                        "mcp_port": mcp_port,
                        "health_port": health_port,
                        "base_url": base_url,
                        "health_url": health_url,
                        "server_log_path": str(log_path),
                    }
        else:
            base_url = f"http://{host}:{mcp_port}/sse"
            async with sse_client(base_url) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    yield session, {
                        "transport": transport,
                        "host": host,
                        "mcp_port": mcp_port,
                        "health_port": health_port,
                        "base_url": base_url,
                        "health_url": health_url,
                        "server_log_path": str(log_path),
                    }

    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:  # pragma: no cover
            proc.kill()
            proc.wait(timeout=5)


async def _call_tool_json(
    session: ClientSession,
    tool_name: str,
    *,
    arguments: dict,
    read_timeout: timedelta,
    evidence: EvidenceRecorder,
) -> dict:
    started = time.monotonic()
    parse_error: str | None = None
    parsed: dict | None = None
    result_is_error = False

    try:
        result = await session.call_tool(
            tool_name,
            arguments=arguments,
            read_timeout_seconds=read_timeout,
        )
        result_is_error = bool(getattr(result, "isError", False))
        parsed = _tool_json(result)
        return parsed
    except Exception as exc:  # noqa: BLE001
        parse_error = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        duration = time.monotonic() - started
        evidence.record_tool_call(
            tool_name=tool_name,
            arguments=arguments,
            read_timeout_seconds=float(read_timeout.total_seconds()),
            duration_seconds=duration,
            result_json=parsed,
            is_error=result_is_error,
            parse_error=parse_error,
        )


async def _run_high_signal_subset(session: ClientSession, nw_root: Path, *, evidence: EvidenceRecorder) -> None:
    tools = await session.list_tools()
    tool_names = sorted({t.name for t in tools.tools})
    evidence.record_event("list_tools", tool_count=len(tool_names), tool_names=tool_names)
    assert len(tool_names) == 22

    analyze_json = await _call_tool_json(
        session,
        "analyze_code",
        arguments={
            "code": "def add(a: int, b: int) -> int:\n    return a + b\n",
            "language": "python",
        },
        read_timeout=timedelta(seconds=30),
        evidence=evidence,
    )
    assert analyze_json.get("success") is True

    dep_scan_json = await _call_tool_json(
        session,
        "scan_dependencies",
        arguments={"project_root": str(nw_root), "scan_vulnerabilities": False},
        read_timeout=timedelta(seconds=90),
        evidence=evidence,
    )
    assert dep_scan_json.get("success") is True

    vp_json = await _call_tool_json(
        session,
        "validate_paths",
        arguments={
            "paths": [
                str(nw_root / "README.md"),
                str(nw_root / "does_not_exist_12345.txt"),
            ],
            "project_root": str(nw_root),
        },
        read_timeout=timedelta(seconds=30),
        evidence=evidence,
    )
    assert "accessible" in vp_json and "inaccessible" in vp_json
    assert any(str(nw_root / "README.md") == p for p in vp_json.get("accessible", []))

    xsec_json = await _call_tool_json(
        session,
        "cross_file_security_scan",
        arguments={
            "project_root": str(nw_root),
            "max_depth": 1,
            "include_diagram": False,
            "timeout_seconds": 5.0,
            "max_modules": 25,
        },
        read_timeout=timedelta(seconds=180),
        evidence=evidence,
    )
    assert "risk_level" in xsec_json


async def _run_heavy_graph_subset(session: ClientSession, analysis_root: Path, *, evidence: EvidenceRecorder) -> None:
    crawl_json = await _call_tool_json(
        session,
        "crawl_project",
        arguments={"root_path": str(analysis_root), "include_report": False},
        read_timeout=timedelta(seconds=180),
        evidence=evidence,
    )
    assert crawl_json.get("success") is True

    pm_json = await _call_tool_json(
        session,
        "get_project_map",
        arguments={
            "project_root": str(analysis_root),
            "include_complexity": False,
            "include_circular_check": False,
        },
        read_timeout=timedelta(seconds=180),
        evidence=evidence,
    )
    assert pm_json.get("success") is True

    cg_json = await _call_tool_json(
        session,
        "get_call_graph",
        arguments={
            "project_root": str(analysis_root),
            "depth": 2,
            "include_circular_import_check": False,
        },
        read_timeout=timedelta(seconds=240),
        evidence=evidence,
    )
    assert cg_json.get("success") is True
    assert "nodes" in cg_json and "edges" in cg_json


async def test_ninja_warrior_acceptance_stdio(tmp_path: Path):
    nw_root = _require_ninja_warrior()

    evidence = EvidenceRecorder(
        test_name="test_ninja_warrior_acceptance_stdio",
        transport="stdio",
        nw_root=nw_root,
        analysis_root=nw_root,
        evidence_dir=_evidence_dir(tmp_path),
        server=None,
    )

    try:
        with anyio.fail_after(300):
            async with _stdio_session_for_root(nw_root) as session:
                await _run_high_signal_subset(session, nw_root, evidence=evidence)
    except Exception as exc:  # noqa: BLE001
        evidence.record_failure(exc)
        raise
    finally:
        evidence.write()


async def test_ninja_warrior_acceptance_http(tmp_path: Path):
    nw_root = _require_ninja_warrior()

    evidence_dir = _evidence_dir(tmp_path)

    server_meta: dict | None = None
    evidence: EvidenceRecorder | None = None
    try:
        with anyio.fail_after(360):
            async with _http_session_for_root(nw_root, evidence_dir, "streamable-http") as (
                session,
                meta,
            ):
                server_meta = meta
                evidence = EvidenceRecorder(
                    test_name="test_ninja_warrior_acceptance_http",
                    transport="streamable-http",
                    nw_root=nw_root,
                    analysis_root=nw_root,
                    evidence_dir=evidence_dir,
                    server=server_meta,
                )
                await _run_high_signal_subset(session, nw_root, evidence=evidence)
    except Exception as exc:  # noqa: BLE001
        if evidence is None:
            evidence = EvidenceRecorder(
                test_name="test_ninja_warrior_acceptance_http",
                transport="streamable-http",
                nw_root=nw_root,
                analysis_root=nw_root,
                evidence_dir=evidence_dir,
                server=server_meta,
            )
        evidence.record_failure(exc)
        raise
    finally:
        if evidence is not None:
            evidence.write()


async def test_ninja_warrior_acceptance_sse(tmp_path: Path):
    nw_root = _require_ninja_warrior()

    evidence_dir = _evidence_dir(tmp_path)

    server_meta: dict | None = None
    evidence: EvidenceRecorder | None = None
    try:
        with anyio.fail_after(360):
            async with _http_session_for_root(nw_root, evidence_dir, "sse") as (
                session,
                meta,
            ):
                server_meta = meta
                evidence = EvidenceRecorder(
                    test_name="test_ninja_warrior_acceptance_sse",
                    transport="sse",
                    nw_root=nw_root,
                    analysis_root=nw_root,
                    evidence_dir=evidence_dir,
                    server=server_meta,
                )
                await _run_high_signal_subset(session, nw_root, evidence=evidence)
    except Exception as exc:  # noqa: BLE001
        if evidence is None:
            evidence = EvidenceRecorder(
                test_name="test_ninja_warrior_acceptance_sse",
                transport="sse",
                nw_root=nw_root,
                analysis_root=nw_root,
                evidence_dir=evidence_dir,
                server=server_meta,
            )
        evidence.record_failure(exc)
        raise
    finally:
        if evidence is not None:
            evidence.write()


async def test_ninja_warrior_acceptance_heavy_stdio(tmp_path: Path):
    nw_root = _require_ninja_warrior()
    _require_ninja_warrior_heavy()

    stage1 = nw_root / "torture-tests" / "stage1-qualifying-round"
    analysis_root = stage1 if stage1.exists() else (nw_root / "torture-tests")

    evidence = EvidenceRecorder(
        test_name="test_ninja_warrior_acceptance_heavy_stdio",
        transport="stdio",
        nw_root=nw_root,
        analysis_root=analysis_root,
        evidence_dir=_evidence_dir(tmp_path),
        server=None,
    )

    try:
        with anyio.fail_after(900):
            async with _stdio_session_for_root(nw_root) as session:
                await _run_heavy_graph_subset(session, analysis_root, evidence=evidence)
    except Exception as exc:  # noqa: BLE001
        evidence.record_failure(exc)
        raise
    finally:
        evidence.write()


async def test_ninja_warrior_acceptance_heavy_http(tmp_path: Path):
    nw_root = _require_ninja_warrior()
    _require_ninja_warrior_heavy()

    stage1 = nw_root / "torture-tests" / "stage1-qualifying-round"
    analysis_root = stage1 if stage1.exists() else (nw_root / "torture-tests")

    evidence_dir = _evidence_dir(tmp_path)

    server_meta: dict | None = None
    evidence: EvidenceRecorder | None = None
    try:
        with anyio.fail_after(900):
            async with _http_session_for_root(nw_root, evidence_dir, "streamable-http") as (
                session,
                meta,
            ):
                server_meta = meta
                evidence = EvidenceRecorder(
                    test_name="test_ninja_warrior_acceptance_heavy_http",
                    transport="streamable-http",
                    nw_root=nw_root,
                    analysis_root=analysis_root,
                    evidence_dir=evidence_dir,
                    server=server_meta,
                )
                await _run_heavy_graph_subset(session, analysis_root, evidence=evidence)
    except Exception as exc:  # noqa: BLE001
        if evidence is None:
            evidence = EvidenceRecorder(
                test_name="test_ninja_warrior_acceptance_heavy_http",
                transport="streamable-http",
                nw_root=nw_root,
                analysis_root=analysis_root,
                evidence_dir=evidence_dir,
                server=server_meta,
            )
        evidence.record_failure(exc)
        raise
    finally:
        if evidence is not None:
            evidence.write()


async def test_ninja_warrior_acceptance_heavy_sse(tmp_path: Path):
    nw_root = _require_ninja_warrior()
    _require_ninja_warrior_heavy()

    stage1 = nw_root / "torture-tests" / "stage1-qualifying-round"
    analysis_root = stage1 if stage1.exists() else (nw_root / "torture-tests")

    evidence_dir = _evidence_dir(tmp_path)

    server_meta: dict | None = None
    evidence: EvidenceRecorder | None = None
    try:
        with anyio.fail_after(900):
            async with _http_session_for_root(nw_root, evidence_dir, "sse") as (
                session,
                meta,
            ):
                server_meta = meta
                evidence = EvidenceRecorder(
                    test_name="test_ninja_warrior_acceptance_heavy_sse",
                    transport="sse",
                    nw_root=nw_root,
                    analysis_root=analysis_root,
                    evidence_dir=evidence_dir,
                    server=server_meta,
                )
                await _run_heavy_graph_subset(session, analysis_root, evidence=evidence)
    except Exception as exc:  # noqa: BLE001
        if evidence is None:
            evidence = EvidenceRecorder(
                test_name="test_ninja_warrior_acceptance_heavy_sse",
                transport="sse",
                nw_root=nw_root,
                analysis_root=analysis_root,
                evidence_dir=evidence_dir,
                server=server_meta,
            )
        evidence.record_failure(exc)
        raise
    finally:
        if evidence is not None:
            evidence.write()
