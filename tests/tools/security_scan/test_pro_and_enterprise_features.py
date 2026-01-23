# [20260106_TEST] Pro/Enterprise feature validation for security_scan
from __future__ import annotations

from pathlib import Path

import pytest

from code_scalpel.licensing.jwt_validator import JWTLicenseValidator

pytestmark = pytest.mark.asyncio


def _use_real_license(monkeypatch: pytest.MonkeyPatch, tier: str) -> Path:
    validator = JWTLicenseValidator()
    candidates = {
        "pro": [
            Path("tests/licenses/code_scalpel_license_pro_20260101_190345.jwt"),
            Path("tests/licenses/code_scalpel_license_pro_20260101_170435.jwt"),
        ],
        "enterprise": [
            Path("tests/licenses/code_scalpel_license_enterprise_20260101_190754.jwt"),
            Path("tests/licenses/code_scalpel_license_enterprise_20260101_170506.jwt"),
        ],
    }.get(tier, [])
    for candidate in candidates:
        if candidate.exists():
            token = candidate.read_text().strip()
            data = validator.validate_token(token)
            if data.is_valid and data.tier == tier:
                monkeypatch.setenv("CODE_SCALPEL_LICENSE_PATH", str(candidate))
                monkeypatch.delenv("CODE_SCALPEL_DISABLE_LICENSE_DISCOVERY", raising=False)
                monkeypatch.delenv("CODE_SCALPEL_TEST_FORCE_TIER", raising=False)
                monkeypatch.delenv("CODE_SCALPEL_TIER", raising=False)
                return candidate
    pytest.skip(f"Valid {tier} license not found; generate a signed test license")


async def test_pro_sanitizer_recognition_reduces_findings(
    monkeypatch: pytest.MonkeyPatch,
):
    """Pro: Sanitizer recognition should reduce or remove XSS findings."""
    _use_real_license(monkeypatch, "pro")

    unsanitized = (
        "from flask import render_template_string\n"
        "def view(user_input):\n"
        "    return render_template_string('<p>' + user_input + '</p>')\n"
    )
    sanitized = (
        "import html\n"
        "from flask import render_template_string\n"
        "def view(user_input):\n"
        "    safe = html.escape(user_input)\n"
        "    return render_template_string(f'<p>{safe}</p>')\n"
    )

    from code_scalpel.mcp.server import security_scan

    unsanitized_result = await security_scan(code=unsanitized)
    sanitized_result = await security_scan(code=sanitized)

    assert unsanitized_result.success is True and sanitized_result.success is True
    assert sanitized_result.vulnerability_count <= unsanitized_result.vulnerability_count
    assert sanitized_result.false_positive_analysis is not None


async def test_pro_confidence_scores_present_and_bounded(
    monkeypatch: pytest.MonkeyPatch,
):
    """Pro: Confidence scores should be present and within [0,1]."""
    _use_real_license(monkeypatch, "pro")

    code = (
        "from flask import request\n"
        "import os\n"
        "def run():\n"
        "    cmd = request.args.get('cmd')\n"
        "    os.system(cmd)\n"
    )
    from code_scalpel.mcp.server import security_scan

    result = await security_scan(code=code)

    assert result.success is True
    assert result.vulnerability_count >= 1
    assert result.confidence_scores is not None
    for conf in result.confidence_scores.values():
        assert 0.0 <= conf <= 1.0


async def test_enterprise_compliance_mapping_present(monkeypatch: pytest.MonkeyPatch):
    """Enterprise: Compliance mapping should be populated for clear vulnerabilities."""
    _use_real_license(monkeypatch, "enterprise")

    code = (
        "from flask import request\n"
        "def handler(cursor):\n"
        "    user_id = request.args.get('id')\n"
        "    cursor.execute(f'SELECT * FROM users WHERE id = {user_id}')\n"
    )
    from code_scalpel.mcp.server import security_scan

    result = await security_scan(code=code)

    assert result.success is True
    assert result.vulnerability_count >= 1
    assert result.compliance_mappings is not None and len(result.compliance_mappings) >= 1
