#!/usr/bin/env python3
# [20260119_TEST] Invoke security_scan via MCP HTTP (JSON-RPC over /mcp)
from __future__ import annotations

import json
import os
import sys
from typing import Any

import requests


def call_tool(base_url: str, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": tool_name, "arguments": arguments},
    }
    resp = requests.post(f"{base_url}/mcp", json=payload, timeout=60)
    resp.raise_for_status()
    return resp.json()


def main() -> int:
    base_url = os.environ.get("SCALPEL_MCP_BASE", "http://127.0.0.1:18080")
    # Simple vulnerable snippet to exercise the scanner
    code = (
        "import sqlite3, os\n"
        "conn = sqlite3.connect(':memory:')\n"
        "cur = conn.cursor()\n"
        "user = 'abc'\n"
        "cur.execute('SELECT * FROM users WHERE name=' + user)\n"
        "os.system('echo ' + user)\n"
    )

    try:
        result = call_tool(base_url, "security_scan", {"code": code})
    except Exception as e:
        print(f"HTTP call failed: {e}", file=sys.stderr)
        return 2

    # Print raw JSON-RPC response for transparency
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
