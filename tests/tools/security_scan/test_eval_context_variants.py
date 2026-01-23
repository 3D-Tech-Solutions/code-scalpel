# [20260106_TEST] Code injection eval() contexts (CWE-94)
from __future__ import annotations

import pytest

pytestmark = pytest.mark.asyncio


async def test_eval_with_globals_locals_detected():
    """Detect eval injection even when globals/locals provided."""
    code = (
        "from flask import request\n"
        "def do_eval():\n"
        "    expr = request.args.get('e')\n"
        "    return eval(expr, {'__builtins__': {}}, {'x': 1})\n"
    )
    from code_scalpel.mcp.server import security_scan

    result = await security_scan(code=code)
    assert result.success is True
    assert any(v.cwe == "CWE-94" or "code" in v.type.lower() for v in result.vulnerabilities)
