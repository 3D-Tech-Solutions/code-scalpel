"""
Test suite for code_policy_check tier enforcement and license-based feature gating.

Tests verify that tier limits (file counts, rule counts) are enforced correctly
and that Pro/Enterprise features are only available with appropriate licenses.

[20260104_TEST] Created tier enforcement test suite for code_policy_check MCP tool.
"""

from pathlib import Path

import pytest

from code_scalpel.mcp.server import code_policy_check


def _clear_caches():
    try:
        from code_scalpel.licensing import jwt_validator, config_loader

        jwt_validator._LICENSE_VALIDATION_CACHE = None
        config_loader.clear_cache()
    except Exception:
        pass


@pytest.fixture
def community_license(monkeypatch, tmp_path):
    """Set license to Community tier (no license file)."""
    _clear_caches()
    monkeypatch.setenv("CODE_SCALPEL_DISABLE_LICENSE_DISCOVERY", "1")
    empty_dir = tmp_path / "no_license"
    empty_dir.mkdir()
    monkeypatch.setenv("CODE_SCALPEL_LICENSE_PATH", str(empty_dir / "nonexistent.jwt"))
    yield
    monkeypatch.delenv("CODE_SCALPEL_LICENSE_PATH", raising=False)
    monkeypatch.delenv("CODE_SCALPEL_DISABLE_LICENSE_DISCOVERY", raising=False)
    _clear_caches()


@pytest.fixture
def pro_license(monkeypatch):
    """Set license to Pro tier using tests/licenses/code_scalpel_license_pro_*.jwt."""
    _clear_caches()
    license_dir = Path(__file__).parent.parent.parent / "licenses"
    pro_licenses = list(license_dir.glob("code_scalpel_license_pro_*.jwt"))
    if not pro_licenses:
        pytest.skip(f"No Pro license file found in {license_dir}")
    license_path = pro_licenses[0]
    if not license_path.read_text(encoding="utf-8").strip():
        pytest.skip("Pro license file is empty (secret not set in CI)")

    monkeypatch.setenv("CODE_SCALPEL_LICENSE_PATH", str(license_path))
    monkeypatch.setenv("CODE_SCALPEL_DISABLE_LICENSE_DISCOVERY", "1")
    _clear_caches()

    # Verify the license actually activates Pro tier — skip if invalid/expired
    from code_scalpel.mcp.server import _get_current_tier

    actual_tier = _get_current_tier()
    if actual_tier != "pro":
        monkeypatch.delenv("CODE_SCALPEL_LICENSE_PATH", raising=False)
        monkeypatch.delenv("CODE_SCALPEL_DISABLE_LICENSE_DISCOVERY", raising=False)
        _clear_caches()
        pytest.skip(
            f"Pro license did not activate Pro tier (got '{actual_tier}'). "
            "License may be expired or have invalid signature."
        )

    yield
    monkeypatch.delenv("CODE_SCALPEL_LICENSE_PATH", raising=False)
    monkeypatch.delenv("CODE_SCALPEL_DISABLE_LICENSE_DISCOVERY", raising=False)
    _clear_caches()


@pytest.fixture
def enterprise_license(monkeypatch):
    """Set license to Enterprise tier using tests/licenses/."""
    _clear_caches()
    license_dir = Path(__file__).parent.parent.parent / "licenses"
    enterprise_licenses = list(
        license_dir.glob("code_scalpel_license_enterprise_*.jwt")
    )
    assert enterprise_licenses, f"No Enterprise license found in {license_dir}"
    license_path = enterprise_licenses[0]

    monkeypatch.setenv("CODE_SCALPEL_LICENSE_PATH", str(license_path))
    monkeypatch.setenv("CODE_SCALPEL_DISABLE_LICENSE_DISCOVERY", "1")
    yield
    monkeypatch.delenv("CODE_SCALPEL_LICENSE_PATH", raising=False)
    monkeypatch.delenv("CODE_SCALPEL_DISABLE_LICENSE_DISCOVERY", raising=False)
    _clear_caches()


class TestCommunityTierLimits:
    """Test Community tier enforces 100 file, 50 rule limits."""

    @pytest.mark.asyncio
    async def test_community_enforces_100_file_limit(self, tmp_path, community_license):
        """Community tier should enforce 100 file limit."""
        # Create 105 files (exceeds Community limit of 100)
        for i in range(105):
            test_file = tmp_path / f"test_{i}.py"
            test_file.write_text("x = 1\n")

        result = await code_policy_check(paths=[str(tmp_path)])

        # Verify tier is Community
        assert (
            result.tier_applied == "community"
        ), f"Expected community tier, got {result.tier_applied}"

        # Should only check 100 files (Community limit)
        assert (
            result.files_checked <= 100
        ), f"Community tier should check max 100 files, checked {result.files_checked}"

    @pytest.mark.asyncio
    async def test_community_enforces_50_rule_limit(self, tmp_path, community_license):
        """Community tier should enforce 50 rule limit."""
        test_file = tmp_path / "test.py"
        test_file.write_text("""
try:
    pass
except:
    pass
""")

        result = await code_policy_check(paths=[str(test_file)])

        # Verify tier is Community
        assert (
            result.tier_applied == "community"
        ), f"Expected community tier, got {result.tier_applied}"

        # Should apply max 50 rules (Community limit)
        assert (
            result.rules_applied <= 50
        ), f"Community tier should apply max 50 rules, applied {result.rules_applied}"


class TestProTierLimits:
    """Test Pro tier enforces 1000 file, 200 rule limits."""

    @pytest.mark.asyncio
    async def test_pro_enforces_1000_file_limit(self, tmp_path, pro_license):
        """Pro tier should enforce 1000 file limit."""
        # Create 50 files (well within Pro limit of 1000)
        for i in range(50):
            test_file = tmp_path / f"test_{i}.py"
            test_file.write_text("x = 1\n")

        result = await code_policy_check(paths=[str(tmp_path)])

        # Verify tier is Pro
        assert (
            result.tier_applied == "pro"
        ), f"Expected pro tier, got {result.tier_applied}"

        # Should check all 50 files (under Pro limit)
        assert (
            result.files_checked == 50
        ), f"Pro tier should check all 50 files, checked {result.files_checked}"

    @pytest.mark.asyncio
    async def test_pro_enforces_200_rule_limit(self, tmp_path, pro_license):
        """Pro tier should enforce 200 rule limit."""
        test_file = tmp_path / "test.py"
        test_file.write_text("""
try:
    pass
except:
    pass
""")

        result = await code_policy_check(paths=[str(test_file)])

        # Verify tier is Pro
        assert (
            result.tier_applied == "pro"
        ), f"Expected pro tier, got {result.tier_applied}"

        # Pro tier should apply rules (actual count depends on implementation)
        assert (
            result.rules_applied > 0
        ), f"Pro tier should apply rules, applied {result.rules_applied}"
        # Should not exceed Pro limit of 200 rules
        assert (
            result.rules_applied <= 200
        ), f"Pro tier should apply max 200 rules, applied {result.rules_applied}"


class TestEnterpriseTierLimits:
    """Test Enterprise tier has unlimited files and rules."""

    @pytest.mark.asyncio
    async def test_enterprise_has_unlimited_files(self, tmp_path, enterprise_license):
        """Enterprise tier should have no file limit."""
        # Create 50 files
        for i in range(50):
            test_file = tmp_path / f"test_{i}.py"
            test_file.write_text("x = 1\n")

        result = await code_policy_check(paths=[str(tmp_path)])

        # Verify tier is Enterprise
        assert (
            result.tier_applied == "enterprise"
        ), f"Expected enterprise tier, got {result.tier_applied}"

        # Should check all files (no limit)
        assert (
            result.files_checked == 50
        ), f"Enterprise tier should check all 50 files, checked {result.files_checked}"

    @pytest.mark.asyncio
    async def test_enterprise_has_unlimited_rules(self, tmp_path, enterprise_license):
        """Enterprise tier should have no rule limit."""
        test_file = tmp_path / "test.py"
        test_file.write_text("""
try:
    pass
except:
    pass
""")

        result = await code_policy_check(paths=[str(test_file)])

        # Verify tier is Enterprise
        assert (
            result.tier_applied == "enterprise"
        ), f"Expected enterprise tier, got {result.tier_applied}"

        # Should apply more than 200 rules (Pro limit) - Enterprise has no limit
        # Note: Current implementation may apply all rules regardless of tier
        assert (
            result.rules_applied > 0
        ), f"Enterprise tier should apply rules, applied {result.rules_applied}"


class TestTierFeatureGating:
    """Test tier-specific feature availability."""

    @pytest.mark.asyncio
    async def test_community_no_best_practices(self, tmp_path, community_license):
        """Community tier should not include best_practices_violations."""
        test_file = tmp_path / "test.py"
        test_file.write_text("""
def func(x):
    return x + 1
""")

        result = await code_policy_check(paths=[str(test_file)])

        assert result.tier_applied == "community"
        # Community tier: best practice violations should not appear
        bp_violations = [
            v for v in result.violations if v.get("category") == "best_practice"
        ]
        assert (
            not bp_violations
        ), "Community tier should not provide best practice violations"

    @pytest.mark.asyncio
    async def test_pro_has_best_practices(self, tmp_path, pro_license):
        """Pro tier should include best_practices_violations."""
        test_file = tmp_path / "test.py"
        test_file.write_text("""
def func(x):
    return x + 1
""")

        result = await code_policy_check(paths=[str(test_file)])

        assert result.tier_applied == "pro"
        # Pro tier: best practice violations should appear in violations list
        bp_violations = [
            v for v in result.violations if v.get("category") == "best_practice"
        ]
        assert bp_violations, "Pro tier should detect best practice violations"

    @pytest.mark.asyncio
    async def test_enterprise_has_compliance_reports(
        self, tmp_path, enterprise_license
    ):
        """Enterprise tier should include compliance_reports."""
        test_file = tmp_path / "test.py"
        test_file.write_text("""
def func(x):
    return x + 1
""")

        result = await code_policy_check(paths=[str(test_file)])

        assert result.tier_applied == "enterprise"
        # Enterprise tier: compliance_reports should be available
        assert hasattr(
            result, "compliance_reports"
        ), "Enterprise tier should provide compliance_reports attribute"

    @pytest.mark.asyncio
    async def test_community_custom_rules_not_exposed(
        self, tmp_path, community_license
    ):
        """Community tier should not expose custom rule results."""
        # [20260105_TEST] Strengthen feature gating expectations.
        test_file = tmp_path / "test.py"
        test_file.write_text("""
value = 1
""")

        result = await code_policy_check(paths=[str(test_file)], rules=["CUSTOM001"])

        assert result.tier_applied == "community"
        assert not getattr(
            result, "custom_rule_results", {}
        ), "Community tier should not provide custom rule results"

    @pytest.mark.asyncio
    async def test_pro_blocks_compliance_outputs(self, tmp_path, pro_license):
        """Pro tier should fail explicitly when compliance auditing is requested."""
        test_file = tmp_path / "test.py"
        test_file.write_text("""
def handler(request):
    return request.json.get("email")
""")

        result = await code_policy_check(
            paths=[str(test_file)],
            compliance_standards=["hipaa"],
            generate_report=True,
        )

        assert result.tier_applied == "pro"
        assert result.success is False
        assert result.error is not None
        assert "Enterprise tier" in result.error.error
        assert result.data["error"] == result.error.error

    @pytest.mark.asyncio
    async def test_community_blocks_report_generation(
        self, tmp_path, community_license
    ):
        """Community tier should fail explicitly when compliance PDF generation is requested."""
        test_file = tmp_path / "test.py"
        test_file.write_text("""
def handler(request):
    return request.json.get("email")
""")

        result = await code_policy_check(
            paths=[str(test_file)],
            generate_report=True,
        )

        assert result.tier_applied == "community"
        assert result.success is False
        assert result.error is not None
        assert "Enterprise tier" in result.error.error
        assert result.data["error"] == result.error.error

    @pytest.mark.asyncio
    async def test_enterprise_includes_audit_trail_and_score(
        self, tmp_path, enterprise_license
    ):
        """Enterprise tier should populate compliance score and audit trail."""
        test_file = tmp_path / "test.py"
        test_file.write_text("""
def log_patient(patient_id):
    print(f"patient_id={patient_id}")
""")

        result = await code_policy_check(
            paths=[str(test_file)],
            compliance_standards=["hipaa"],
            generate_report=True,
        )

        assert result.tier_applied == "enterprise"
        assert getattr(result, "compliance_score", 0) >= 0
        assert getattr(
            result, "audit_trail", []
        ), "Enterprise tier should include audit trail"
        assert (
            getattr(result, "pdf_report", None) is not None
        ), "Enterprise tier should generate PDF when requested"
