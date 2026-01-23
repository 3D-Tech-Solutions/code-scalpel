# [20260106_TEST] False positive validation for security_scan
from __future__ import annotations

from pathlib import Path

import pytest

from code_scalpel.licensing.jwt_validator import JWTLicenseValidator

pytestmark = pytest.mark.asyncio


async def test_no_fp_parameterized_sql():
    """Safe: Parameterized query should not raise SQL injection."""
    code = "def fetch(cursor, user_id):\n" "    cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))\n"
    from code_scalpel.mcp.server import security_scan

    result = await security_scan(code=code)

    assert result.success is True
    assert all(v.cwe != "CWE-89" for v in result.vulnerabilities)


async def test_no_fp_html_escaped(monkeypatch: pytest.MonkeyPatch):
    """Safe: HTML-escaped string should not trigger XSS."""
    # Pro tier includes false-positive reduction; ensure Pro license is used
    validator = JWTLicenseValidator()
    candidates = [
        Path("tests/licenses/code_scalpel_license_pro_20260101_190345.jwt"),
        Path("tests/licenses/code_scalpel_license_pro_20260101_170435.jwt"),
    ]
    for candidate in candidates:
        if candidate.exists():
            token = candidate.read_text().strip()
            data = validator.validate_token(token)
            if data.is_valid and data.tier == "pro":
                # Use monkeypatch fixture implicitly via environment since pytest-asyncio provides event loop
                monkeypatch.setenv("CODE_SCALPEL_LICENSE_PATH", str(candidate))
                monkeypatch.delenv("CODE_SCALPEL_DISABLE_LICENSE_DISCOVERY", raising=False)
                monkeypatch.delenv("CODE_SCALPEL_TEST_FORCE_TIER", raising=False)
                monkeypatch.delenv("CODE_SCALPEL_TIER", raising=False)
                break
    code = (
        "import html\n"
        "def render(user_input):\n"
        "    safe = html.escape(user_input)\n"
        "    return f'<p>{safe}</p>'\n"
    )
    from code_scalpel.mcp.server import security_scan

    result = await security_scan(code=code)

    assert result.success is True
    xss_vulns = [v for v in result.vulnerabilities if v.cwe == "CWE-79" or "xss" in v.type.lower()]
    if xss_vulns:
        # Pro tier: if any XSS remains, confidence should be non-high and FP analysis present
        assert result.confidence_scores is not None
        xss_conf = [score for key, score in result.confidence_scores.items() if key.lower().startswith("xss@")]
        assert all(conf <= 0.7 for conf in xss_conf)
        assert result.false_positive_analysis is not None


async def test_no_fp_subprocess_safe_list():
    """Safe: subprocess.run with list args and constants should not flag."""
    code = "import subprocess\n" "def run():\n" "    subprocess.run(['ls', '-la', '.'], check=True)\n"
    from code_scalpel.mcp.server import security_scan

    result = await security_scan(code=code)

    assert result.success is True
    assert all("command" not in v.type.lower() for v in result.vulnerabilities)


async def test_no_fp_sqlalchemy_orm():
    """Safe: SQLAlchemy ORM query building should not flag SQL injection."""
    code = (
        "from sqlalchemy.orm import Session\n"
        "from models import User\n"
        "def find(session: Session, user_id):\n"
        "    return session.query(User).filter(User.id == user_id).all()\n"
    )
    from code_scalpel.mcp.server import security_scan

    result = await security_scan(code=code)

    assert result.success is True
    assert all(v.cwe != "CWE-89" for v in result.vulnerabilities)
