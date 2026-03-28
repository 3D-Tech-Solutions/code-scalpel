"""Public usefulness-contract tests for cross_file_security_scan.

[20260314_TEST] Verify the documented usefulness slice for cross_file_security_scan
at the public MCP boundary.
"""

from __future__ import annotations

from pathlib import Path

import pytest


pytestmark = pytest.mark.asyncio


async def test_cross_file_security_scan_python_is_core_useful(tmp_path: Path) -> None:
    from code_scalpel.mcp.server import cross_file_security_scan

    (tmp_path / "routes.py").write_text(
        "from flask import request\n"
        "from db import execute_query\n\n"
        "def search():\n"
        "    query = request.args.get('q')\n"
        "    return execute_query(query)\n",
        encoding="utf-8",
    )
    (tmp_path / "db.py").write_text(
        "import sqlite3\n\n"
        "def execute_query(query: str):\n"
        "    sql = f\"SELECT * FROM users WHERE name = '{query}'\"\n"
        "    conn = sqlite3.connect(':memory:')\n"
        "    cursor = conn.cursor()\n"
        "    cursor.execute(sql)\n"
        "    return cursor.fetchall()\n",
        encoding="utf-8",
    )

    result = await cross_file_security_scan(
        project_root=str(tmp_path),
        entry_points=["routes.py"],
        include_diagram=True,
    )

    assert result.success is True
    assert result.files_analyzed >= 2
    assert result.has_vulnerabilities is True
    assert result.vulnerability_count >= 1
    assert any(vulnerability.cwe == "CWE-89" for vulnerability in result.vulnerabilities)
    assert any(flow.sink_file == "db.py" for flow in result.taint_flows)
    assert isinstance(result.mermaid, str)


async def test_cross_file_security_scan_java_is_bounded_useful(tmp_path: Path) -> None:
    from code_scalpel.mcp.server import cross_file_security_scan

    web_dir = tmp_path / "src" / "com" / "example" / "web"
    service_dir = tmp_path / "src" / "com" / "example" / "service"
    repo_dir = tmp_path / "src" / "com" / "example" / "repo"
    util_dir = tmp_path / "src" / "com" / "example" / "util"
    web_dir.mkdir(parents=True)
    service_dir.mkdir(parents=True)
    repo_dir.mkdir(parents=True)
    util_dir.mkdir(parents=True)

    (web_dir / "UserController.java").write_text(
        "package com.example.web;\n\n"
        "import com.example.service.UserService;\n\n"
        "class UserController {\n"
        "    String run(Request request) {\n"
        "        UserService service = new UserService();\n"
        "        String user = request.getParameter(\"id\");\n"
        "        return service.run(user);\n"
        "    }\n"
        "}\n",
        encoding="utf-8",
    )
    (service_dir / "UserService.java").write_text(
        "package com.example.service;\n\n"
        "import com.example.repo.UserRepository;\n\n"
        "class UserService {\n"
        "    String run(String user) {\n"
        "        UserRepository repo = new UserRepository();\n"
        "        return repo.execute(user);\n"
        "    }\n"
        "}\n",
        encoding="utf-8",
    )
    (repo_dir / "UserRepository.java").write_text(
        "package com.example.repo;\n\n"
        "import com.example.util.Sql;\n\n"
        "class UserRepository {\n"
        "    String execute(String query) {\n"
        "        Sql sql = new Sql();\n"
        "        return sql.raw(query);\n"
        "    }\n"
        "}\n",
        encoding="utf-8",
    )
    (util_dir / "Sql.java").write_text(
        "package com.example.util;\n\n"
        "class Sql {\n"
        "    String raw(String sql) {\n"
        "        return sql;\n"
        "    }\n"
        "}\n",
        encoding="utf-8",
    )

    result = await cross_file_security_scan(
        project_root=str(tmp_path),
        include_diagram=False,
        max_depth=3,
        max_modules=10,
        timeout_seconds=10.0,
    )

    assert result.success is True
    assert result.files_analyzed == 4
    assert result.has_vulnerabilities is True
    assert result.vulnerability_count >= 1
    assert any(vulnerability.cwe == "CWE-89" for vulnerability in result.vulnerabilities)
    assert any(
        "Java cross-file security scan currently supports a bounded IR-based subset"
        in warning
        for warning in result.warnings
    )


async def test_cross_file_security_scan_javascript_is_bounded_useful(
    tmp_path: Path,
) -> None:
    from code_scalpel.mcp.server import cross_file_security_scan

    (tmp_path / "source.js").write_text(
        "export function getUserInput() {\n"
        "  return process.env.USER_INPUT;\n"
        "}\n",
        encoding="utf-8",
    )
    (tmp_path / "executor.js").write_text(
        "import { getUserInput } from './source.js';\n\n"
        "export function run() {\n"
        "  const script = getUserInput();\n"
        "  return eval(script);\n"
        "}\n",
        encoding="utf-8",
    )

    result = await cross_file_security_scan(project_root=str(tmp_path))

    assert result.success is True
    assert result.files_analyzed == 2
    assert result.has_vulnerabilities is True
    assert result.vulnerability_count >= 1
    assert any(vulnerability.cwe == "CWE-94" for vulnerability in result.vulnerabilities)
    assert any(flow.sink_file == "executor.js" for flow in result.taint_flows)
    assert not any(
        warning.startswith("Java cross-file security scan")
        or "skipped detected Java files" in warning
        for warning in result.warnings
    )


async def test_cross_file_security_scan_typescript_is_bounded_useful(
    tmp_path: Path,
) -> None:
    from code_scalpel.mcp.server import cross_file_security_scan

    (tmp_path / "source.ts").write_text(
        "export function getUserInput(): string | undefined {\n"
        "  return process.env.USER_INPUT;\n"
        "}\n",
        encoding="utf-8",
    )
    (tmp_path / "executor.ts").write_text(
        "import { getUserInput } from './source';\n\n"
        "export function run(): unknown {\n"
        "  const script = getUserInput();\n"
        "  return eval(script ?? '0');\n"
        "}\n",
        encoding="utf-8",
    )

    result = await cross_file_security_scan(project_root=str(tmp_path))

    assert result.success is True
    assert result.files_analyzed == 2
    assert result.has_vulnerabilities is True
    assert result.vulnerability_count >= 1
    assert any(vulnerability.cwe == "CWE-94" for vulnerability in result.vulnerabilities)
    assert any(flow.sink_file == "executor.ts" for flow in result.taint_flows)
    assert not any(
        warning.startswith("Java cross-file security scan")
        or "skipped detected Java files" in warning
        for warning in result.warnings
    )


async def test_cross_file_security_scan_typescript_tracks_named_import_aliases(
    tmp_path: Path,
) -> None:
    from code_scalpel.mcp.server import cross_file_security_scan

    (tmp_path / "source.ts").write_text(
        "export function getUserInput(): string | undefined {\n"
        "  return process.env.USER_INPUT;\n"
        "}\n",
        encoding="utf-8",
    )
    (tmp_path / "executor.ts").write_text(
        "import { getUserInput as readInput } from './source';\n\n"
        "export function run(): unknown {\n"
        "  const script = readInput();\n"
        "  return eval(script ?? '0');\n"
        "}\n",
        encoding="utf-8",
    )

    result = await cross_file_security_scan(project_root=str(tmp_path))

    assert result.success is True
    assert result.files_analyzed == 2
    assert result.has_vulnerabilities is True
    assert result.vulnerability_count >= 1
    assert any(vulnerability.cwe == "CWE-94" for vulnerability in result.vulnerabilities)
    assert any(flow.sink_file == "executor.ts" for flow in result.taint_flows)


async def test_cross_file_security_scan_typescript_tracks_tsconfig_alias_imports(
    tmp_path: Path,
) -> None:
    from code_scalpel.mcp.server import cross_file_security_scan

    (tmp_path / "tsconfig.json").write_text(
        "{\n"
        '  "compilerOptions": {\n'
        '    "baseUrl": ".",\n'
        '    "paths": {\n'
        '      "@lib/*": ["src/lib/*"]\n'
        "    }\n"
        "  }\n"
        "}\n",
        encoding="utf-8",
    )
    source_dir = tmp_path / "src" / "lib"
    source_dir.mkdir(parents=True)
    (source_dir / "source.ts").write_text(
        "export function getUserInput(): string | undefined {\n"
        "  return process.env.USER_INPUT;\n"
        "}\n",
        encoding="utf-8",
    )
    (tmp_path / "executor.ts").write_text(
        "import { getUserInput } from '@lib/source';\n\n"
        "export function run(): unknown {\n"
        "  const script = getUserInput();\n"
        "  return eval(script ?? '0');\n"
        "}\n",
        encoding="utf-8",
    )

    result = await cross_file_security_scan(project_root=str(tmp_path))

    assert result.success is True
    assert result.files_analyzed == 2
    assert result.has_vulnerabilities is True
    assert result.vulnerability_count >= 1
    assert any(vulnerability.cwe == "CWE-94" for vulnerability in result.vulnerabilities)
    assert any(flow.sink_file == "executor.ts" for flow in result.taint_flows)


async def test_cross_file_security_scan_typescript_tracks_directory_index_imports(
    tmp_path: Path,
) -> None:
    from code_scalpel.mcp.server import cross_file_security_scan

    api_dir = tmp_path / "api"
    api_dir.mkdir()
    (api_dir / "index.ts").write_text(
        "export function getUserInput(): string | undefined {\n"
        "  return process.env.USER_INPUT;\n"
        "}\n",
        encoding="utf-8",
    )
    (tmp_path / "executor.ts").write_text(
        "import { getUserInput } from './api';\n\n"
        "export function run(): unknown {\n"
        "  const script = getUserInput();\n"
        "  return eval(script ?? '0');\n"
        "}\n",
        encoding="utf-8",
    )

    result = await cross_file_security_scan(project_root=str(tmp_path))

    assert result.success is True
    assert result.files_analyzed == 2
    assert result.has_vulnerabilities is True
    assert result.vulnerability_count >= 1
    assert any(vulnerability.cwe == "CWE-94" for vulnerability in result.vulnerabilities)
    assert any(flow.sink_file == "executor.ts" for flow in result.taint_flows)


async def test_cross_file_security_scan_typescript_tracks_req_query_sources(
    tmp_path: Path,
) -> None:
    from code_scalpel.mcp.server import cross_file_security_scan

    (tmp_path / "source.ts").write_text(
        "type Request = { query: Record<string, string | undefined> };\n\n"
        "export function getUserInput(req: Request): string | undefined {\n"
        "  return req.query['script'];\n"
        "}\n",
        encoding="utf-8",
    )
    (tmp_path / "executor.ts").write_text(
        "import { getUserInput } from './source';\n\n"
        "type Request = { query: Record<string, string | undefined> };\n\n"
        "export function run(req: Request): unknown {\n"
        "  const script = getUserInput(req);\n"
        "  return eval(script ?? '0');\n"
        "}\n",
        encoding="utf-8",
    )

    result = await cross_file_security_scan(project_root=str(tmp_path))

    assert result.success is True
    assert result.files_analyzed == 2
    assert result.has_vulnerabilities is True
    assert result.vulnerability_count >= 1
    assert any(vulnerability.cwe == "CWE-94" for vulnerability in result.vulnerabilities)
    assert any(flow.sink_file == "executor.ts" for flow in result.taint_flows)


async def test_cross_file_security_scan_typescript_tracks_req_body_sources(
    tmp_path: Path,
) -> None:
    from code_scalpel.mcp.server import cross_file_security_scan

    (tmp_path / "source.ts").write_text(
        "type Request = { body: Record<string, string | undefined> };\n\n"
        "export function getUserInput(req: Request): string | undefined {\n"
        "  return req.body['script'];\n"
        "}\n",
        encoding="utf-8",
    )
    (tmp_path / "executor.ts").write_text(
        "import { getUserInput } from './source';\n\n"
        "type Request = { body: Record<string, string | undefined> };\n\n"
        "export function run(req: Request): unknown {\n"
        "  const script = getUserInput(req);\n"
        "  return eval(script ?? '0');\n"
        "}\n",
        encoding="utf-8",
    )

    result = await cross_file_security_scan(project_root=str(tmp_path))

    assert result.success is True
    assert result.files_analyzed == 2
    assert result.has_vulnerabilities is True
    assert result.vulnerability_count >= 1
    assert any(vulnerability.cwe == "CWE-94" for vulnerability in result.vulnerabilities)
    assert any(flow.sink_file == "executor.ts" for flow in result.taint_flows)


async def test_cross_file_security_scan_typescript_tracks_req_params_sources(
    tmp_path: Path,
) -> None:
    from code_scalpel.mcp.server import cross_file_security_scan

    (tmp_path / "source.ts").write_text(
        "type Request = { params: Record<string, string | undefined> };\n\n"
        "export function getUserInput(req: Request): string | undefined {\n"
        "  return req.params['script'];\n"
        "}\n",
        encoding="utf-8",
    )
    (tmp_path / "executor.ts").write_text(
        "import { getUserInput } from './source';\n\n"
        "type Request = { params: Record<string, string | undefined> };\n\n"
        "export function run(req: Request): unknown {\n"
        "  const script = getUserInput(req);\n"
        "  return eval(script ?? '0');\n"
        "}\n",
        encoding="utf-8",
    )

    result = await cross_file_security_scan(project_root=str(tmp_path))

    assert result.success is True
    assert result.files_analyzed == 2
    assert result.has_vulnerabilities is True
    assert result.vulnerability_count >= 1
    assert any(vulnerability.cwe == "CWE-94" for vulnerability in result.vulnerabilities)
    assert any(flow.sink_file == "executor.ts" for flow in result.taint_flows)


async def test_cross_file_security_scan_typescript_tracks_req_headers_sources(
    tmp_path: Path,
) -> None:
    from code_scalpel.mcp.server import cross_file_security_scan

    (tmp_path / "source.ts").write_text(
        "type Request = { headers: Record<string, string | undefined> };\n\n"
        "export function getUserInput(req: Request): string | undefined {\n"
        "  return req.headers['x-script'];\n"
        "}\n",
        encoding="utf-8",
    )
    (tmp_path / "executor.ts").write_text(
        "import { getUserInput } from './source';\n\n"
        "type Request = { headers: Record<string, string | undefined> };\n\n"
        "export function run(req: Request): unknown {\n"
        "  const script = getUserInput(req);\n"
        "  return eval(script ?? '0');\n"
        "}\n",
        encoding="utf-8",
    )

    result = await cross_file_security_scan(project_root=str(tmp_path))

    assert result.success is True
    assert result.files_analyzed == 2
    assert result.has_vulnerabilities is True
    assert result.vulnerability_count >= 1
    assert any(vulnerability.cwe == "CWE-94" for vulnerability in result.vulnerabilities)
    assert any(flow.sink_file == "executor.ts" for flow in result.taint_flows)


async def test_cross_file_security_scan_typescript_tracks_req_cookies_sources(
    tmp_path: Path,
) -> None:
    from code_scalpel.mcp.server import cross_file_security_scan

    (tmp_path / "source.ts").write_text(
        "type Request = { cookies: Record<string, string | undefined> };\n\n"
        "export function getUserInput(req: Request): string | undefined {\n"
        "  return req.cookies['script'];\n"
        "}\n",
        encoding="utf-8",
    )
    (tmp_path / "executor.ts").write_text(
        "import { getUserInput } from './source';\n\n"
        "type Request = { cookies: Record<string, string | undefined> };\n\n"
        "export function run(req: Request): unknown {\n"
        "  const script = getUserInput(req);\n"
        "  return eval(script ?? '0');\n"
        "}\n",
        encoding="utf-8",
    )

    result = await cross_file_security_scan(project_root=str(tmp_path))

    assert result.success is True
    assert result.files_analyzed == 2
    assert result.has_vulnerabilities is True
    assert result.vulnerability_count >= 1
    assert any(vulnerability.cwe == "CWE-94" for vulnerability in result.vulnerabilities)
    assert any(flow.sink_file == "executor.ts" for flow in result.taint_flows)


async def test_cross_file_security_scan_typescript_tracks_req_get_sources(
    tmp_path: Path,
) -> None:
    from code_scalpel.mcp.server import cross_file_security_scan

    (tmp_path / "source.ts").write_text(
        "type Request = { get(name: string): string | undefined };\n\n"
        "export function getUserInput(req: Request): string | undefined {\n"
        "  return req.get('x-script');\n"
        "}\n",
        encoding="utf-8",
    )
    (tmp_path / "executor.ts").write_text(
        "import { getUserInput } from './source';\n\n"
        "type Request = { get(name: string): string | undefined };\n\n"
        "export function run(req: Request): unknown {\n"
        "  const script = getUserInput(req);\n"
        "  return eval(script ?? '0');\n"
        "}\n",
        encoding="utf-8",
    )

    result = await cross_file_security_scan(project_root=str(tmp_path))

    assert result.success is True
    assert result.files_analyzed == 2
    assert result.has_vulnerabilities is True
    assert result.vulnerability_count >= 1
    assert any(vulnerability.cwe == "CWE-94" for vulnerability in result.vulnerabilities)
    assert any(flow.sink_file == "executor.ts" for flow in result.taint_flows)


async def test_cross_file_security_scan_typescript_tracks_req_header_sources(
    tmp_path: Path,
) -> None:
    from code_scalpel.mcp.server import cross_file_security_scan

    (tmp_path / "source.ts").write_text(
        "type Request = { header(name: string): string | undefined };\n\n"
        "export function getUserInput(req: Request): string | undefined {\n"
        "  return req.header('x-script');\n"
        "}\n",
        encoding="utf-8",
    )
    (tmp_path / "executor.ts").write_text(
        "import { getUserInput } from './source';\n\n"
        "type Request = { header(name: string): string | undefined };\n\n"
        "export function run(req: Request): unknown {\n"
        "  const script = getUserInput(req);\n"
        "  return eval(script ?? '0');\n"
        "}\n",
        encoding="utf-8",
    )

    result = await cross_file_security_scan(project_root=str(tmp_path))

    assert result.success is True
    assert result.files_analyzed == 2
    assert result.has_vulnerabilities is True
    assert result.vulnerability_count >= 1
    assert any(vulnerability.cwe == "CWE-94" for vulnerability in result.vulnerabilities)
    assert any(flow.sink_file == "executor.ts" for flow in result.taint_flows)


async def test_cross_file_security_scan_typescript_tracks_req_headers_get_sources(
    tmp_path: Path,
) -> None:
    from code_scalpel.mcp.server import cross_file_security_scan

    (tmp_path / "source.ts").write_text(
        "type Headers = { get(name: string): string | undefined };\n"
        "type Request = { headers: Headers };\n\n"
        "export function getUserInput(req: Request): string | undefined {\n"
        "  return req.headers.get('x-script');\n"
        "}\n",
        encoding="utf-8",
    )
    (tmp_path / "executor.ts").write_text(
        "import { getUserInput } from './source';\n\n"
        "type Headers = { get(name: string): string | undefined };\n"
        "type Request = { headers: Headers };\n\n"
        "export function run(req: Request): unknown {\n"
        "  const script = getUserInput(req);\n"
        "  return eval(script ?? '0');\n"
        "}\n",
        encoding="utf-8",
    )

    result = await cross_file_security_scan(project_root=str(tmp_path))

    assert result.success is True
    assert result.files_analyzed == 2
    assert result.has_vulnerabilities is True
    assert result.vulnerability_count >= 1
    assert any(vulnerability.cwe == "CWE-94" for vulnerability in result.vulnerabilities)
    assert any(flow.sink_file == "executor.ts" for flow in result.taint_flows)


async def test_cross_file_security_scan_typescript_tracks_req_cookies_get_sources(
    tmp_path: Path,
) -> None:
    from code_scalpel.mcp.server import cross_file_security_scan

    (tmp_path / "source.ts").write_text(
        "type Cookies = { get(name: string): string | undefined };\n"
        "type Request = { cookies: Cookies };\n\n"
        "export function getUserInput(req: Request): string | undefined {\n"
        "  return req.cookies.get('script');\n"
        "}\n",
        encoding="utf-8",
    )
    (tmp_path / "executor.ts").write_text(
        "import { getUserInput } from './source';\n\n"
        "type Cookies = { get(name: string): string | undefined };\n"
        "type Request = { cookies: Cookies };\n\n"
        "export function run(req: Request): unknown {\n"
        "  const script = getUserInput(req);\n"
        "  return eval(script ?? '0');\n"
        "}\n",
        encoding="utf-8",
    )

    result = await cross_file_security_scan(project_root=str(tmp_path))

    assert result.success is True
    assert result.files_analyzed == 2
    assert result.has_vulnerabilities is True
    assert result.vulnerability_count >= 1
    assert any(vulnerability.cwe == "CWE-94" for vulnerability in result.vulnerabilities)
    assert any(flow.sink_file == "executor.ts" for flow in result.taint_flows)


async def test_cross_file_security_scan_typescript_tracks_request_get_sources(
    tmp_path: Path,
) -> None:
    from code_scalpel.mcp.server import cross_file_security_scan

    (tmp_path / "source.ts").write_text(
        "type Request = { get(name: string): string | undefined };\n\n"
        "export function getUserInput(request: Request): string | undefined {\n"
        "  return request.get('x-script');\n"
        "}\n",
        encoding="utf-8",
    )
    (tmp_path / "executor.ts").write_text(
        "import { getUserInput } from './source';\n\n"
        "type Request = { get(name: string): string | undefined };\n\n"
        "export function run(request: Request): unknown {\n"
        "  const script = getUserInput(request);\n"
        "  return eval(script ?? '0');\n"
        "}\n",
        encoding="utf-8",
    )

    result = await cross_file_security_scan(project_root=str(tmp_path))

    assert result.success is True
    assert result.files_analyzed == 2
    assert result.has_vulnerabilities is True
    assert result.vulnerability_count >= 1
    assert any(vulnerability.cwe == "CWE-94" for vulnerability in result.vulnerabilities)
    assert any(flow.sink_file == "executor.ts" for flow in result.taint_flows)


async def test_cross_file_security_scan_typescript_tracks_request_header_sources(
    tmp_path: Path,
) -> None:
    from code_scalpel.mcp.server import cross_file_security_scan

    (tmp_path / "source.ts").write_text(
        "type Request = { header(name: string): string | undefined };\n\n"
        "export function getUserInput(request: Request): string | undefined {\n"
        "  return request.header('x-script');\n"
        "}\n",
        encoding="utf-8",
    )
    (tmp_path / "executor.ts").write_text(
        "import { getUserInput } from './source';\n\n"
        "type Request = { header(name: string): string | undefined };\n\n"
        "export function run(request: Request): unknown {\n"
        "  const script = getUserInput(request);\n"
        "  return eval(script ?? '0');\n"
        "}\n",
        encoding="utf-8",
    )

    result = await cross_file_security_scan(project_root=str(tmp_path))

    assert result.success is True
    assert result.files_analyzed == 2
    assert result.has_vulnerabilities is True
    assert result.vulnerability_count >= 1
    assert any(vulnerability.cwe == "CWE-94" for vulnerability in result.vulnerabilities)
    assert any(flow.sink_file == "executor.ts" for flow in result.taint_flows)


async def test_cross_file_security_scan_typescript_tracks_request_headers_get_sources(
    tmp_path: Path,
) -> None:
    from code_scalpel.mcp.server import cross_file_security_scan

    (tmp_path / "source.ts").write_text(
        "type Headers = { get(name: string): string | undefined };\n"
        "type Request = { headers: Headers };\n\n"
        "export function getUserInput(request: Request): string | undefined {\n"
        "  return request.headers.get('x-script');\n"
        "}\n",
        encoding="utf-8",
    )
    (tmp_path / "executor.ts").write_text(
        "import { getUserInput } from './source';\n\n"
        "type Headers = { get(name: string): string | undefined };\n"
        "type Request = { headers: Headers };\n\n"
        "export function run(request: Request): unknown {\n"
        "  const script = getUserInput(request);\n"
        "  return eval(script ?? '0');\n"
        "}\n",
        encoding="utf-8",
    )

    result = await cross_file_security_scan(project_root=str(tmp_path))

    assert result.success is True
    assert result.files_analyzed == 2
    assert result.has_vulnerabilities is True
    assert result.vulnerability_count >= 1
    assert any(vulnerability.cwe == "CWE-94" for vulnerability in result.vulnerabilities)
    assert any(flow.sink_file == "executor.ts" for flow in result.taint_flows)


async def test_cross_file_security_scan_typescript_tracks_request_cookies_get_sources(
    tmp_path: Path,
) -> None:
    from code_scalpel.mcp.server import cross_file_security_scan

    (tmp_path / "source.ts").write_text(
        "type Cookies = { get(name: string): string | undefined };\n"
        "type Request = { cookies: Cookies };\n\n"
        "export function getUserInput(request: Request): string | undefined {\n"
        "  return request.cookies.get('script');\n"
        "}\n",
        encoding="utf-8",
    )
    (tmp_path / "executor.ts").write_text(
        "import { getUserInput } from './source';\n\n"
        "type Cookies = { get(name: string): string | undefined };\n"
        "type Request = { cookies: Cookies };\n\n"
        "export function run(request: Request): unknown {\n"
        "  const script = getUserInput(request);\n"
        "  return eval(script ?? '0');\n"
        "}\n",
        encoding="utf-8",
    )

    result = await cross_file_security_scan(project_root=str(tmp_path))

    assert result.success is True
    assert result.files_analyzed == 2
    assert result.has_vulnerabilities is True
    assert result.vulnerability_count >= 1
    assert any(vulnerability.cwe == "CWE-94" for vulnerability in result.vulnerabilities)
    assert any(flow.sink_file == "executor.ts" for flow in result.taint_flows)


async def test_cross_file_security_scan_typescript_tracks_request_query_sources(
    tmp_path: Path,
) -> None:
    from code_scalpel.mcp.server import cross_file_security_scan

    (tmp_path / "source.ts").write_text(
        "type Request = { query: Record<string, string | undefined> };\n\n"
        "export function getUserInput(request: Request): string | undefined {\n"
        "  return request.query['script'];\n"
        "}\n",
        encoding="utf-8",
    )
    (tmp_path / "executor.ts").write_text(
        "import { getUserInput } from './source';\n\n"
        "type Request = { query: Record<string, string | undefined> };\n\n"
        "export function run(request: Request): unknown {\n"
        "  const script = getUserInput(request);\n"
        "  return eval(script ?? '0');\n"
        "}\n",
        encoding="utf-8",
    )

    result = await cross_file_security_scan(project_root=str(tmp_path))

    assert result.success is True
    assert result.files_analyzed == 2
    assert result.has_vulnerabilities is True
    assert result.vulnerability_count >= 1
    assert any(vulnerability.cwe == "CWE-94" for vulnerability in result.vulnerabilities)
    assert any(flow.sink_file == "executor.ts" for flow in result.taint_flows)


async def test_cross_file_security_scan_typescript_tracks_request_body_sources(
    tmp_path: Path,
) -> None:
    from code_scalpel.mcp.server import cross_file_security_scan

    (tmp_path / "source.ts").write_text(
        "type Request = { body: Record<string, string | undefined> };\n\n"
        "export function getUserInput(request: Request): string | undefined {\n"
        "  return request.body['script'];\n"
        "}\n",
        encoding="utf-8",
    )
    (tmp_path / "executor.ts").write_text(
        "import { getUserInput } from './source';\n\n"
        "type Request = { body: Record<string, string | undefined> };\n\n"
        "export function run(request: Request): unknown {\n"
        "  const script = getUserInput(request);\n"
        "  return eval(script ?? '0');\n"
        "}\n",
        encoding="utf-8",
    )

    result = await cross_file_security_scan(project_root=str(tmp_path))

    assert result.success is True
    assert result.files_analyzed == 2
    assert result.has_vulnerabilities is True
    assert result.vulnerability_count >= 1
    assert any(vulnerability.cwe == "CWE-94" for vulnerability in result.vulnerabilities)
    assert any(flow.sink_file == "executor.ts" for flow in result.taint_flows)


async def test_cross_file_security_scan_typescript_tracks_request_params_sources(
    tmp_path: Path,
) -> None:
    from code_scalpel.mcp.server import cross_file_security_scan

    (tmp_path / "source.ts").write_text(
        "type Request = { params: Record<string, string | undefined> };\n\n"
        "export function getUserInput(request: Request): string | undefined {\n"
        "  return request.params['script'];\n"
        "}\n",
        encoding="utf-8",
    )
    (tmp_path / "executor.ts").write_text(
        "import { getUserInput } from './source';\n\n"
        "type Request = { params: Record<string, string | undefined> };\n\n"
        "export function run(request: Request): unknown {\n"
        "  const script = getUserInput(request);\n"
        "  return eval(script ?? '0');\n"
        "}\n",
        encoding="utf-8",
    )

    result = await cross_file_security_scan(project_root=str(tmp_path))

    assert result.success is True
    assert result.files_analyzed == 2
    assert result.has_vulnerabilities is True
    assert result.vulnerability_count >= 1
    assert any(vulnerability.cwe == "CWE-94" for vulnerability in result.vulnerabilities)
    assert any(flow.sink_file == "executor.ts" for flow in result.taint_flows)


async def test_cross_file_security_scan_typescript_tracks_request_headers_sources(
    tmp_path: Path,
) -> None:
    from code_scalpel.mcp.server import cross_file_security_scan

    (tmp_path / "source.ts").write_text(
        "type Request = { headers: Record<string, string | undefined> };\n\n"
        "export function getUserInput(request: Request): string | undefined {\n"
        "  return request.headers['x-script'];\n"
        "}\n",
        encoding="utf-8",
    )
    (tmp_path / "executor.ts").write_text(
        "import { getUserInput } from './source';\n\n"
        "type Request = { headers: Record<string, string | undefined> };\n\n"
        "export function run(request: Request): unknown {\n"
        "  const script = getUserInput(request);\n"
        "  return eval(script ?? '0');\n"
        "}\n",
        encoding="utf-8",
    )

    result = await cross_file_security_scan(project_root=str(tmp_path))

    assert result.success is True
    assert result.files_analyzed == 2
    assert result.has_vulnerabilities is True
    assert result.vulnerability_count >= 1
    assert any(vulnerability.cwe == "CWE-94" for vulnerability in result.vulnerabilities)
    assert any(flow.sink_file == "executor.ts" for flow in result.taint_flows)


async def test_cross_file_security_scan_typescript_tracks_request_cookies_sources(
    tmp_path: Path,
) -> None:
    from code_scalpel.mcp.server import cross_file_security_scan

    (tmp_path / "source.ts").write_text(
        "type Request = { cookies: Record<string, string | undefined> };\n\n"
        "export function getUserInput(request: Request): string | undefined {\n"
        "  return request.cookies['script'];\n"
        "}\n",
        encoding="utf-8",
    )
    (tmp_path / "executor.ts").write_text(
        "import { getUserInput } from './source';\n\n"
        "type Request = { cookies: Record<string, string | undefined> };\n\n"
        "export function run(request: Request): unknown {\n"
        "  const script = getUserInput(request);\n"
        "  return eval(script ?? '0');\n"
        "}\n",
        encoding="utf-8",
    )

    result = await cross_file_security_scan(project_root=str(tmp_path))

    assert result.success is True
    assert result.files_analyzed == 2
    assert result.has_vulnerabilities is True
    assert result.vulnerability_count >= 1
    assert any(vulnerability.cwe == "CWE-94" for vulnerability in result.vulnerabilities)
    assert any(flow.sink_file == "executor.ts" for flow in result.taint_flows)