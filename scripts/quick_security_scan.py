# [20260119_TEST] Minimal runner to invoke MCP security_scan on a sample snippet
from __future__ import annotations

import asyncio
import json
import os
from typing import Any

from code_scalpel.mcp.tools.security import security_scan


async def main() -> None:
    # Deliberately vulnerable sample: SQL concatenation, command injection, path traversal
    sample_code = (
        "import sqlite3, os\n"
        "conn = sqlite3.connect(':memory:')\n"
        "cur = conn.cursor()\n"
        "user = input('name: ')\n"
        "cur.execute('SELECT * FROM users WHERE name=' + user)\n"
        "os.system('echo ' + user)\n"
        "open('../' + user, 'r')\n"
    )

    res = await security_scan(code=sample_code)

    def to_json(obj: Any) -> Any:
        try:
            return obj.model_dump()  # pydantic BaseModel
        except Exception:
            return str(obj)

    output = {
        "success": res.success,
        "server_version": res.server_version,
        "has_vulnerabilities": res.has_vulnerabilities,
        "vulnerability_count": res.vulnerability_count,
        "risk_level": res.risk_level,
        "vulnerabilities": [to_json(v) for v in res.vulnerabilities],
        "error": res.error,
    }
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    # Ensure license path is visible when running directly
    os.environ.setdefault(
        "CODE_SCALPEL_LICENSE_PATH",
        os.path.join(os.path.dirname(__file__), "..", ".code-scalpel", "license", "license.jwt"),
    )
    asyncio.run(main())
