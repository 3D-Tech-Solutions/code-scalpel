#!/usr/bin/env python3
# [20260119_TEST] Invoke security_scan via MCP stdio transport
from __future__ import annotations

import asyncio
import json
import os

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main() -> None:
    server_cmd = [
        "python",
        "-m",
        "code_scalpel.mcp.server",
        "--transport",
        "stdio",
        "--root",
        ".",
    ]
    env = os.environ.copy()
    env.setdefault("PYTHONPATH", os.path.abspath("src"))
    env.setdefault(
        "CODE_SCALPEL_LICENSE_PATH",
        os.path.abspath(".code-scalpel/license/license.jwt"),
    )
    env.setdefault("SCALPEL_MCP_INFO", "DEBUG")

    params = StdioServerParameters(command=server_cmd[0], args=server_cmd[1:], env=env)
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize MCP session and wait briefly for tool registration
            await session.initialize()
            await asyncio.sleep(0.2)
            code = (
                "import sqlite3\n"
                "def get_user(user_id):\n"
                "    conn = sqlite3.connect(':memory:')\n"
                "    cur = conn.cursor()\n"
                "    query = 'SELECT * FROM users WHERE id=' + str(user_id)\n"
                "    cur.execute(query)\n"
                "    return cur.fetchone()\n"
            )
            res = await session.call_tool("security_scan", {"code": code})
            try:
                payload = res.model_dump()
            except Exception:
                # Fallback for older client lib versions
                payload = json.loads(json.dumps(res, default=str))
            print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
