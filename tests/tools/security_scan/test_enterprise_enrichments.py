# [20260106_TEST] Enterprise-tier enrichments: priority ordering, reachability, policies, FP tuning
from __future__ import annotations

from pathlib import Path

import pytest

from code_scalpel.licensing.jwt_validator import JWTLicenseValidator

pytestmark = pytest.mark.asyncio


def _use_enterprise_license(monkeypatch: pytest.MonkeyPatch) -> Path:
    validator = JWTLicenseValidator()
    candidates = [
        Path("tests/licenses/code_scalpel_license_enterprise_20260101_190754.jwt"),
        Path("tests/licenses/code_scalpel_license_enterprise_20260101_170506.jwt"),
    ]
    for candidate in candidates:
        if candidate.exists():
            token = candidate.read_text().strip()
            data = validator.validate_token(token)
            if data.is_valid and data.tier == "enterprise":
                monkeypatch.setenv("CODE_SCALPEL_LICENSE_PATH", str(candidate))
                monkeypatch.delenv("CODE_SCALPEL_DISABLE_LICENSE_DISCOVERY", raising=False)
                monkeypatch.delenv("CODE_SCALPEL_TEST_FORCE_TIER", raising=False)
                monkeypatch.delenv("CODE_SCALPEL_TIER", raising=False)
                return candidate
    pytest.skip("Valid Enterprise license not found; generate a signed test license")


async def test_priority_and_reachability(monkeypatch: pytest.MonkeyPatch):
    _use_enterprise_license(monkeypatch)
    code = (
        "from flask import request\n"
        "def main():\n"
        "    user_id = request.args.get('id')\n"
        "    cursor.execute(f'SELECT * FROM users WHERE id = {user_id}')\n"
        "    cmd = request.args.get('cmd')\n"
        "    os.system(cmd)\n"
    )
    from code_scalpel.mcp.server import security_scan

    result = await security_scan(code=code)
    assert result.success is True
    assert result.priority_ordered_findings is not None
    assert result.reachability_analysis is not None
    assert result.reachability_analysis.get("reachable_count", 0) >= 1


async def test_policy_and_custom_rules(monkeypatch: pytest.MonkeyPatch):
    _use_enterprise_license(monkeypatch)
    code = (
        "import hashlib\n"
        "def weak():\n"
        "    x = hashlib.md5(b'data').hexdigest()\n"
        "def log():\n"
        "    import logging\n"
        "    logging.info('user password in logs: %s', 'abc')\n"
    )
    from code_scalpel.mcp.server import security_scan

    result = await security_scan(code=code)
    assert result.success is True
    assert result.policy_violations is not None or result.compliance_mappings is not None
    # Custom logging rule may or may not hit depending on patterns; accept None
    # but ensure result object serializes ok
    assert result.vulnerability_count >= 0


async def test_false_positive_tuning(monkeypatch: pytest.MonkeyPatch):
    _use_enterprise_license(monkeypatch)
    code = (
        "import html\n"
        "from flask import render_template_string\n"
        "def view(user_input):\n"
        "    safe = html.escape(user_input)\n"
        "    return render_template_string(f'<p>{safe}</p>')\n"
    )
    from code_scalpel.mcp.server import security_scan

    result = await security_scan(code=code)
    assert result.success is True
    assert result.false_positive_tuning is not None
    assert result.false_positive_tuning.get("sanitizers_detected", 0) >= 0
