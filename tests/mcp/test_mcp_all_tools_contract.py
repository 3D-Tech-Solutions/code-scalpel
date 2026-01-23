import json
import os
import platform
import socket
import subprocess
import sys
import time
import uuid
from contextlib import asynccontextmanager
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

if os.environ.get("CODE_SCALPEL_RUN_MCP_CONTRACT", "0") != "1":
    pytestmark = [
        pytest.mark.skip("MCP contract suite skipped by default; set CODE_SCALPEL_RUN_MCP_CONTRACT=1 to run"),
        pytest.mark.asyncio,
    ]
else:
    pytestmark = [pytest.mark.asyncio]

# Disable license revalidation thread during contract tests to avoid timeouts.
os.environ.setdefault("CODE_SCALPEL_DISABLE_LICENSE_REVALIDATION", "1")
# Limit transports in CI/test to reduce runtime; stdio is the fastest and most stable.
os.environ.setdefault("MCP_CONTRACT_TRANSPORT", "stdio")

ALL_TOOL_NAMES = {
    "analyze_code",
    "code_policy_check",
    "unified_sink_detect",
    "type_evaporation_scan",
    "scan_dependencies",
    "security_scan",
    "symbolic_execute",
    "generate_unit_tests",
    "simulate_refactor",
    "extract_code",
    "rename_symbol",
    "update_symbol",
    "crawl_project",
    "get_file_context",
    "get_symbol_references",
    "get_call_graph",
    "get_graph_neighborhood",
    "get_project_map",
    "get_cross_file_dependencies",
    "cross_file_security_scan",
    "validate_paths",
    "verify_policy_integrity",
}


def _repo_root() -> Path:
    # [20251228_BUGFIX] tests/mcp/* is two levels below repo root
    return Path(__file__).resolve().parents[2]


def _artifact_root() -> Path:
    raw = os.environ.get("MCP_CONTRACT_ARTIFACT_DIR")
    if raw:
        base = Path(raw).expanduser().resolve()
    else:
        base = _repo_root() / "evidence" / "mcp-contract"
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
        if "success" in data:
            summary["success"] = data.get("success")
        if "risk_level" in data:
            summary["risk_level"] = data.get("risk_level")
        if "nodes" in data and isinstance(data.get("nodes"), list):
            summary["nodes_count"] = len(data["nodes"])  # type: ignore[index]
        if "edges" in data and isinstance(data.get("edges"), list):
            summary["edges_count"] = len(data["edges"])  # type: ignore[index]
        return summary
    if isinstance(data, list):
        return {"_type": "list", "length": len(data)}
    if isinstance(data, str):
        return data[:500]
    return data


class ContractEvidenceRecorder:
    def __init__(
        self,
        *,
        test_name: str,
        transport: str,
        analysis_root: Path,
        artifact_root: Path,
        server: dict | None = None,
    ) -> None:
        self._started_monotonic = time.monotonic()
        self._started_at_utc = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        self._events: list[dict] = []
        self._tool_calls: list[dict] = []
        self._failure: dict | None = None

        self.run_id = uuid.uuid4().hex[:12]
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        filename = f"mcp_contract_{test_name}_{transport}_{stamp}_{self.run_id}.json"
        self.path = artifact_root / filename

        self._base: dict = {
            "schema_version": 1,
            "created_at_utc": self._started_at_utc,
            "run_id": self.run_id,
            "test_name": test_name,
            "transport": transport,
            "analysis_root": str(analysis_root),
            "python": {"executable": sys.executable, "version": sys.version},
            "platform": {"platform": platform.platform()},
            "env": {
                "CI": os.environ.get("CI"),
                "GITHUB_ACTIONS": os.environ.get("GITHUB_ACTIONS"),
                "MCP_CONTRACT_TRANSPORT": os.environ.get("MCP_CONTRACT_TRANSPORT"),
                "MCP_CONTRACT_ARTIFACT_DIR": os.environ.get("MCP_CONTRACT_ARTIFACT_DIR"),
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
                "server": report.get("server"),
                "evidence_path": str(self.path),
                "tool_calls": len(self._tool_calls),
                "duration_seconds": round(duration_seconds, 6),
            }
            with index_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(index_entry, sort_keys=True) + "\n")
        except Exception:  # noqa: BLE001
            return


def _enabled_transports() -> list[str]:
    # [20260210_BUGFIX] Skip streamable-http when client dependency is unavailable
    forced = os.environ.get("MCP_CONTRACT_TRANSPORT")
    if forced:
        if forced not in ("stdio", "streamable-http", "sse"):
            raise RuntimeError(f"Invalid MCP_CONTRACT_TRANSPORT: {forced}")
        # If streamable-http is forced but client is missing, skip
        if forced == "streamable-http" and streamable_http_client is None:
            pytest.skip("streamable-http client not available")
        return [forced]

    transports = ["stdio", "streamable-http", "sse"]
    if streamable_http_client is None:
        transports.remove("streamable-http")
    return transports


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


def _pythonpath_env(repo_root: Path) -> dict[str, str]:
    src_root = repo_root / "src"
    assert (src_root / "code_scalpel").exists()

    env = os.environ.copy()
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = str(src_root) + (":" + existing if existing else "")
    # Avoid nondeterministic tier selection due to stray license files on disk.
    env.setdefault("CODE_SCALPEL_DISABLE_LICENSE_DISCOVERY", "1")
    return env


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


def _assert_envelope(payload: dict, *, tool_name: str) -> dict:
    assert isinstance(payload, dict)

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
        assert key in payload, f"Missing envelope field: {key}"

    assert payload["tool_id"] == tool_name
    assert (
        isinstance(payload["tool_version"], str) and payload["tool_version"]
    ), "tool_version must be a non-empty string"
    assert isinstance(payload["tier"], str) and payload["tier"]
    assert isinstance(payload["request_id"], str) and payload["request_id"]
    assert isinstance(payload["capabilities"], list)
    assert isinstance(payload["upgrade_hints"], list)
    assert isinstance(payload["duration_ms"], int) and payload["duration_ms"] >= 0

    err = payload.get("error")
    if err is not None:
        assert isinstance(err, dict)
        assert isinstance(err.get("error"), str) and err.get("error")
        assert isinstance(err.get("error_code"), str) and err.get("error_code")
        # error_details may be None or dict
        if err.get("error_details") is not None:
            assert isinstance(err.get("error_details"), dict)

    return payload["data"]  # type: ignore[return-value]


def _write_fixture_project(project_root: Path) -> dict[str, Path]:
    project_root.mkdir(parents=True, exist_ok=True)
    (project_root / "pkg").mkdir(parents=True, exist_ok=True)

    (project_root / "requirements.txt").write_text("requests==2.32.3\n", encoding="utf-8")

    app_py = project_root / "app.py"
    app_py.write_text(
        """
from pkg.service import process_order


def calculate_discount(price: int, is_member: bool) -> float:
    if price > 100:
        if is_member:
            return price * 0.8
        return price * 0.9
    return float(price)


def main() -> None:
    print(process_order(10))
""".lstrip(),
        encoding="utf-8",
    )

    (project_root / "pkg" / "__init__.py").write_text("", encoding="utf-8")

    models_py = project_root / "pkg" / "models.py"
    models_py.write_text(
        """
class TaxRate:
    def __init__(self, rate: float) -> None:
        self.rate = rate


DEFAULT_TAX = TaxRate(0.1)
""".lstrip(),
        encoding="utf-8",
    )

    service_py = project_root / "pkg" / "service.py"
    service_py.write_text(
        """
from pkg.models import DEFAULT_TAX


def process_order(amount: int) -> float:
    return amount + (amount * DEFAULT_TAX.rate)
""".lstrip(),
        encoding="utf-8",
    )

    utils_py = project_root / "utils.py"
    utils_py.write_text(
        """
def add(a: int, b: int) -> int:
    return a + b
""".lstrip(),
        encoding="utf-8",
    )

    return {
        "app_py": app_py,
        "models_py": models_py,
        "service_py": service_py,
        "utils_py": utils_py,
    }


def _write_signed_policy_manifest(policy_dir: Path, secret: str) -> None:
    from code_scalpel.policy_engine.crypto_verify import CryptographicPolicyVerifier

    policy_dir.mkdir(parents=True, exist_ok=True)
    (policy_dir / "policy.rego").write_text("package test\n\nallow if true\n", encoding="utf-8")

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


async def _call_tool_json(
    session: ClientSession,
    tool_name: str,
    *,
    arguments: dict,
    read_timeout: timedelta,
    evidence: ContractEvidenceRecorder,
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


@asynccontextmanager
async def _stdio_session(repo_root: Path, project_root: Path):
    env = _pythonpath_env(repo_root)

    server_params = StdioServerParameters(
        command=sys.executable,
        args=[
            "-m",
            "code_scalpel.mcp.server",
            "--transport",
            "stdio",
            "--root",
            str(project_root),
        ],
        env=env,
    )

    async with stdio_client(server_params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            yield session


@asynccontextmanager
async def _http_session(repo_root: Path, project_root: Path, *, transport: str, log_dir: Path):
    """Start an HTTP transport MCP server and return a connected session.

    transport: "streamable-http" or "sse".
    """

    assert transport in ("streamable-http", "sse")

    env = _pythonpath_env(repo_root)

    host = "127.0.0.1"
    mcp_port, health_port = _get_free_port_pair(host=host)

    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"mcp_{transport.replace('-', '_')}_server.log"

    log_file = log_path.open("w", encoding="utf-8")
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
            str(project_root),
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
                    yield session
        else:
            base_url = f"http://{host}:{mcp_port}/sse"
            async with sse_client(base_url) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    yield session

    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:  # pragma: no cover
            proc.kill()
            proc.wait(timeout=5)
        finally:
            log_file.close()


@pytest.mark.parametrize("transport", _enabled_transports())
async def test_mcp_all_tools_independent_contracts(tmp_path: Path, transport: str, monkeypatch: pytest.MonkeyPatch):
    """Calls every MCP tool with a minimal, deterministic input.

    Goal: ensure each tool is callable, returns structured JSON, respects timeouts,
    and (where applicable) returns the expected success/error shape.
    """

    repo_root = _repo_root()
    project_root = tmp_path / "fixture_project"
    files = _write_fixture_project(project_root)

    policy_secret = "unit-test-secret"
    monkeypatch.setenv("SCALPEL_MANIFEST_SECRET", policy_secret)

    policy_dir = project_root / ".code-scalpel"
    _write_signed_policy_manifest(policy_dir, secret=policy_secret)

    artifact_root = _artifact_root()
    log_dir = artifact_root / "logs" / f"{transport}" / datetime.now(timezone.utc).strftime("%Y%m%d")

    server_meta: dict | None = None
    if transport in ("streamable-http", "sse"):
        server_meta = {"transport": transport, "server_log_dir": str(log_dir)}

    evidence = ContractEvidenceRecorder(
        test_name="all_tools",
        transport=transport,
        analysis_root=project_root,
        artifact_root=artifact_root,
        server=server_meta,
    )

    with anyio.fail_after(300):
        try:
            if transport == "stdio":
                session_cm = _stdio_session(repo_root, project_root)
            else:
                session_cm = _http_session(repo_root, project_root, transport=transport, log_dir=log_dir)

            async with session_cm as session:
                tools = await session.list_tools()
                tool_names = {t.name for t in tools.tools}
                evidence.record_event(
                    "list_tools",
                    tool_count=len(tool_names),
                    tool_names=sorted(tool_names),
                )
                assert tool_names == ALL_TOOL_NAMES

                analyze_json = await _call_tool_json(
                    session,
                    "analyze_code",
                    arguments={
                        "code": "def add(a: int, b: int) -> int:\n    return a + b\n",
                        "language": "python",
                    },
                    read_timeout=timedelta(seconds=20),
                    evidence=evidence,
                )
                analyze_data = _assert_envelope(analyze_json, tool_name="analyze_code")
                assert analyze_data.get("success") is True
                assert "functions" in analyze_data

                sinks_json = await _call_tool_json(
                    session,
                    "unified_sink_detect",
                    arguments={
                        "code": "eval(user_input)",
                        "language": "python",
                        "min_confidence": 0.1,
                    },
                    read_timeout=timedelta(seconds=20),
                    evidence=evidence,
                )
                sinks_data = _assert_envelope(sinks_json, tool_name="unified_sink_detect")
                assert sinks_data.get("success") is True
                assert "sink_count" in sinks_data

                tev_json = await _call_tool_json(
                    session,
                    "type_evaporation_scan",
                    arguments={
                        "frontend_code": """
type Role = 'admin' | 'user';
async function send(roleInput: any) {
  const role = roleInput as Role;
  await fetch('/api/role', { method: 'POST', body: JSON.stringify({ role }) });
}
""".lstrip(),
                        "backend_code": """
from flask import Flask, request
app = Flask(__name__)

@app.post('/api/role')
def set_role():
    role = request.get_json(force=True).get('role')
    return {'role': role}
""".lstrip(),
                        "frontend_file": "frontend.ts",
                        "backend_file": "backend.py",
                    },
                    read_timeout=timedelta(seconds=30),
                    evidence=evidence,
                )
                tev_data = _assert_envelope(tev_json, tool_name="type_evaporation_scan")
                assert tev_data.get("success") is True
                assert "vulnerabilities" in tev_data

                deps_json = await _call_tool_json(
                    session,
                    "scan_dependencies",
                    arguments={
                        "project_root": str(project_root),
                        "scan_vulnerabilities": False,
                    },
                    read_timeout=timedelta(seconds=60),
                    evidence=evidence,
                )
                deps_data = _assert_envelope(deps_json, tool_name="scan_dependencies")
                assert deps_data.get("success") is True

                sec_json = await _call_tool_json(
                    session,
                    "security_scan",
                    arguments={"code": "import os\nos.system(user_input)\n"},
                    read_timeout=timedelta(seconds=60),
                    evidence=evidence,
                )
                sec_data = _assert_envelope(sec_json, tool_name="security_scan")
                assert sec_data.get("success") is True
                assert "risk_level" in sec_data

                sym_json = await _call_tool_json(
                    session,
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
                    read_timeout=timedelta(seconds=60),
                    evidence=evidence,
                )
                sym_data = _assert_envelope(sym_json, tool_name="symbolic_execute")
                assert sym_data.get("success") is True

                gen_json = await _call_tool_json(
                    session,
                    "generate_unit_tests",
                    arguments={
                        "framework": "pytest",
                        "code": """\
def add(a, b):
    if a > 0:
        return a + b
    return b
""",
                    },
                    read_timeout=timedelta(seconds=120),
                    evidence=evidence,
                )
                gen_data = _assert_envelope(gen_json, tool_name="generate_unit_tests")
                assert gen_data.get("success") is True

                sim_json = await _call_tool_json(
                    session,
                    "simulate_refactor",
                    arguments={
                        "original_code": "def add(a, b):\n    return a + b\n",
                        "new_code": "def add(a: int, b: int) -> int:\n    return a + b\n",
                        "strict_mode": False,
                    },
                    read_timeout=timedelta(seconds=60),
                    evidence=evidence,
                )
                sim_data = _assert_envelope(sim_json, tool_name="simulate_refactor")
                assert sim_data.get("success") is True

                extract_json = await _call_tool_json(
                    session,
                    "extract_code",
                    arguments={
                        "target_type": "function",
                        "target_name": "add",
                        "file_path": str(files["utils_py"]),
                        "include_context": False,
                        "include_cross_file_deps": False,
                    },
                    read_timeout=timedelta(seconds=20),
                    evidence=evidence,
                )
                extract_data = _assert_envelope(extract_json, tool_name="extract_code")
                assert extract_data.get("success") is True

                update_json = await _call_tool_json(
                    session,
                    "update_symbol",
                    arguments={
                        "file_path": str(files["utils_py"]),
                        "target_type": "function",
                        "target_name": "add",
                        "new_code": "def add(a: int, b: int) -> int:\n    return a + b\n",
                        "create_backup": False,
                    },
                    read_timeout=timedelta(seconds=60),
                    evidence=evidence,
                )
                update_data = _assert_envelope(update_json, tool_name="update_symbol")
                assert update_data.get("success") is True

                crawl_json = await _call_tool_json(
                    session,
                    "crawl_project",
                    arguments={
                        "root_path": str(project_root),
                        "complexity_threshold": 1,
                        "include_report": False,
                    },
                    read_timeout=timedelta(seconds=60),
                    evidence=evidence,
                )
                crawl_data = _assert_envelope(crawl_json, tool_name="crawl_project")
                assert crawl_data.get("success") is True

                ctx_json = await _call_tool_json(
                    session,
                    "get_file_context",
                    arguments={
                        "file_path": str(files["app_py"]),
                    },
                    read_timeout=timedelta(seconds=30),
                    evidence=evidence,
                )
                ctx_data = _assert_envelope(ctx_json, tool_name="get_file_context")
                assert ctx_data.get("success") is True

                refs_json = await _call_tool_json(
                    session,
                    "get_symbol_references",
                    arguments={
                        "symbol_name": "process_order",
                        "project_root": str(project_root),
                    },
                    read_timeout=timedelta(seconds=60),
                    evidence=evidence,
                )
                refs_data = _assert_envelope(refs_json, tool_name="get_symbol_references")
                assert refs_data.get("success") is True

                call_graph_json = await _call_tool_json(
                    session,
                    "get_call_graph",
                    arguments={
                        "project_root": str(project_root),
                        "depth": 5,
                        "include_circular_import_check": False,
                    },
                    read_timeout=timedelta(seconds=90),
                    evidence=evidence,
                )
                call_graph_data = _assert_envelope(call_graph_json, tool_name="get_call_graph")
                assert call_graph_data.get("success") is True

                neigh_json = await _call_tool_json(
                    session,
                    "get_graph_neighborhood",
                    arguments={
                        "max_nodes": 200,
                        "center_node_id": "python::doesnotexist::function::missing",
                        "k": 1,
                        "direction": "both",
                        "min_confidence": 0.0,
                        "project_root": str(project_root),
                    },
                    read_timeout=timedelta(seconds=90),
                    evidence=evidence,
                )
                neigh_data = _assert_envelope(neigh_json, tool_name="get_graph_neighborhood")
                # This tool may legitimately return success False for missing nodes.
                assert neigh_data.get("success") in (True, False)

                map_json = await _call_tool_json(
                    session,
                    "get_project_map",
                    arguments={
                        "project_root": str(project_root),
                        "include_complexity": False,
                        "include_circular_check": False,
                    },
                    read_timeout=timedelta(seconds=90),
                    evidence=evidence,
                )
                map_data = _assert_envelope(map_json, tool_name="get_project_map")
                assert map_data.get("success") is True

                dep_json = await _call_tool_json(
                    session,
                    "get_cross_file_dependencies",
                    arguments={
                        "target_file": str(files["service_py"].relative_to(project_root)),
                        "target_symbol": "process_order",
                        "project_root": str(project_root),
                        "max_depth": 2,
                        "include_code": False,
                        "include_diagram": False,
                    },
                    read_timeout=timedelta(seconds=120),
                    evidence=evidence,
                )
                dep_data = _assert_envelope(dep_json, tool_name="get_cross_file_dependencies")
                assert dep_data.get("success") is True

                cross_sec_json = await _call_tool_json(
                    session,
                    "cross_file_security_scan",
                    arguments={
                        "project_root": str(project_root),
                        "max_depth": 2,
                        "include_diagram": False,
                        "timeout_seconds": 10.0,
                        "max_modules": 50,
                    },
                    read_timeout=timedelta(seconds=180),
                    evidence=evidence,
                )
                cross_sec_data = _assert_envelope(cross_sec_json, tool_name="cross_file_security_scan")
                assert cross_sec_data.get("success") is True

                paths_json = await _call_tool_json(
                    session,
                    "validate_paths",
                    arguments={
                        "paths": [
                            str(files["app_py"]),
                            str(project_root / "missing_123.txt"),
                        ],
                        "project_root": str(project_root),
                    },
                    read_timeout=timedelta(seconds=30),
                    evidence=evidence,
                )
                paths_data = _assert_envelope(paths_json, tool_name="validate_paths")
                assert "accessible" in paths_data and "inaccessible" in paths_data

                policy_json = await _call_tool_json(
                    session,
                    "verify_policy_integrity",
                    arguments={
                        "policy_dir": str(policy_dir),
                        "manifest_source": "file",
                    },
                    read_timeout=timedelta(seconds=60),
                    evidence=evidence,
                )
                policy_data = _assert_envelope(policy_json, tool_name="verify_policy_integrity")
                assert policy_data.get("success") is True
                assert "summary" in tev_data
        except BaseException as exc:  # noqa: BLE001
            evidence.record_failure(exc)
            raise
        finally:
            evidence.write()
