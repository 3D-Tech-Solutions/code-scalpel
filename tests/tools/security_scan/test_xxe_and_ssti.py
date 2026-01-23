# [20260106_TEST] Additional detections: XXE (CWE-611) and SSTI (CWE-1336)
from __future__ import annotations

import pytest

pytestmark = pytest.mark.asyncio


async def test_xxe_injection_detection():
    """Detect XXE via tainted XML input (CWE-611)."""
    code = (
        "from flask import request\n"
        "import xml.etree.ElementTree as ET\n"
        "def parse():\n"
        "    xml_data = request.args.get('xml')\n"
        "    root = ET.fromstring(xml_data)\n"
        "    return root.tag\n"
    )
    from code_scalpel.mcp.server import security_scan

    result = await security_scan(code=code)
    assert result.success is True
    assert any(v.cwe == "CWE-611" or "xxe" in v.type.lower() for v in result.vulnerabilities)


async def test_ssti_detection():
    """Detect SSTI via tainted template string (CWE-1336)."""
    code = (
        "from jinja2 import Template\n"
        "from flask import request\n"
        "def render():\n"
        "    tmpl_str = request.args.get('tmpl')\n"
        "    tmpl = Template(tmpl_str)\n"
        "    return tmpl.render(foo='bar')\n"
    )
    from code_scalpel.mcp.server import security_scan

    result = await security_scan(code=code)
    assert result.success is True
    assert any(v.cwe == "CWE-1336" or "template" in v.type.lower() for v in result.vulnerabilities)
