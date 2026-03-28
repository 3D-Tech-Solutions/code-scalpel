"""Public usefulness-contract tests for TypeScript security_scan slices.

[20260315_TEST] Verify the bounded TypeScript single-file security slice at the
public MCP boundary.
"""

from __future__ import annotations

from pathlib import Path

import pytest


pytestmark = pytest.mark.asyncio


async def test_security_scan_typescript_dom_xss_is_bounded_useful(
    tmp_path: Path,
) -> None:
    from code_scalpel.mcp.server import security_scan

    ts_file = tmp_path / "app.ts"
    ts_file.write_text(
        "function renderUser(name: string): void {\n"
        "  const userDiv = document.getElementById('user');\n"
        "  if (userDiv) {\n"
        "    userDiv.innerHTML = name;\n"
        "  }\n"
        "}\n",
        encoding="utf-8",
    )

    result = await security_scan(file_path=str(ts_file))

    assert result.success is True
    assert result.vulnerability_count >= 1
    assert any(vulnerability.cwe == "CWE-79" for vulnerability in result.vulnerabilities)


async def test_security_scan_typescript_sql_injection_is_bounded_useful(
    tmp_path: Path,
) -> None:
    from code_scalpel.mcp.server import security_scan

    ts_file = tmp_path / "db.ts"
    ts_file.write_text(
        "async function getUser(id: string): Promise<any> {\n"
        "  const query = `SELECT * FROM users WHERE id=${id}`;\n"
        "  return await database.query(query);\n"
        "}\n",
        encoding="utf-8",
    )

    result = await security_scan(file_path=str(ts_file))

    assert result.success is True
    assert result.vulnerability_count >= 1
    assert any(vulnerability.cwe == "CWE-89" for vulnerability in result.vulnerabilities)


async def test_security_scan_typescript_command_injection_is_bounded_useful(
    tmp_path: Path,
) -> None:
    from code_scalpel.mcp.server import security_scan

    ts_file = tmp_path / "cmd.ts"
    ts_file.write_text(
        "import { exec } from 'child_process';\n"
        "function runCommand(userCmd: string): void {\n"
        "  exec(`ls -la ${userCmd}`);\n"
        "}\n",
        encoding="utf-8",
    )

    result = await security_scan(file_path=str(ts_file))

    assert result.success is True
    assert result.vulnerability_count >= 1
    assert any(vulnerability.cwe == "CWE-78" for vulnerability in result.vulnerabilities)