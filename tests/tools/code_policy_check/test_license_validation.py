"""
Test suite for code_policy_check license validation and fallback behavior.

Tests verify that invalid/broken licenses properly fall back to Community tier
and that license validation errors are handled gracefully.

[20260104_TEST] Created license validation test suite for code_policy_check MCP tool.
"""

from pathlib import Path

import pytest

from code_scalpel.mcp.server import code_policy_check


class TestBrokenLicenseHandling:
    """Test handling of broken/invalid license files."""

    @pytest.mark.asyncio
    async def test_broken_license_falls_back_to_community(self, tmp_path, monkeypatch):
        """Broken license file (missing claims) should fall back to Community tier."""
        # Use the intentionally broken Pro license (missing 'sub' claim)
        license_dir = Path(__file__).parent.parent.parent / "licenses"
        broken_license = license_dir / "code_scalpel_license_pro_test_broken.jwt"

        if not broken_license.exists():
            pytest.skip(f"Broken license file not found: {broken_license}")

        monkeypatch.setenv("CODE_SCALPEL_LICENSE_PATH", str(broken_license))
        monkeypatch.setenv("CODE_SCALPEL_DISABLE_LICENSE_DISCOVERY", "1")

        test_file = tmp_path / "test.py"
        test_file.write_text("x = 1\n")

        result = await code_policy_check(paths=[str(test_file)])

        # Should fall back to Community tier when license is broken
        assert result.tier == "community", f"Broken license should fall back to community tier, got {result.tier}"

        monkeypatch.delenv("CODE_SCALPEL_LICENSE_PATH", raising=False)
        monkeypatch.delenv("CODE_SCALPEL_DISABLE_LICENSE_DISCOVERY", raising=False)

    @pytest.mark.asyncio
    async def test_broken_enterprise_license_falls_back_to_community(self, tmp_path, monkeypatch):
        """Broken Enterprise license should also fall back to Community tier."""
        license_dir = Path(__file__).parent.parent.parent / "licenses"
        broken_license = license_dir / "code_scalpel_license_enterprise_test_broken.jwt"

        if not broken_license.exists():
            pytest.skip(f"Broken license file not found: {broken_license}")

        monkeypatch.setenv("CODE_SCALPEL_LICENSE_PATH", str(broken_license))
        monkeypatch.setenv("CODE_SCALPEL_DISABLE_LICENSE_DISCOVERY", "1")

        test_file = tmp_path / "test.py"
        test_file.write_text("x = 1\n")

        result = await code_policy_check(paths=[str(test_file)])

        assert (
            result.tier == "community"
        ), f"Broken Enterprise license should fall back to community tier, got {result.tier}"

        monkeypatch.delenv("CODE_SCALPEL_LICENSE_PATH", raising=False)
        monkeypatch.delenv("CODE_SCALPEL_DISABLE_LICENSE_DISCOVERY", raising=False)


class TestMissingLicenseHandling:
    """Test handling when no license file is present."""

    @pytest.mark.asyncio
    async def test_missing_license_file_defaults_to_community(self, tmp_path, monkeypatch):
        """When license file doesn't exist, should default to Community tier."""
        # Point to non-existent file and disable discovery
        monkeypatch.setenv("CODE_SCALPEL_LICENSE_PATH", str(tmp_path / "nonexistent.jwt"))
        monkeypatch.setenv("CODE_SCALPEL_DISABLE_LICENSE_DISCOVERY", "1")

        test_file = tmp_path / "test.py"
        test_file.write_text("x = 1\n")

        result = await code_policy_check(paths=[str(test_file)])

        assert result.tier == "community", f"Missing license should default to community tier, got {result.tier}"

        monkeypatch.delenv("CODE_SCALPEL_LICENSE_PATH", raising=False)
        monkeypatch.delenv("CODE_SCALPEL_DISABLE_LICENSE_DISCOVERY", raising=False)

    @pytest.mark.asyncio
    async def test_empty_license_directory_defaults_to_community(self, tmp_path, monkeypatch):
        """Empty license directory should default to Community tier."""
        empty_dir = tmp_path / "empty_license_dir"
        empty_dir.mkdir()

        monkeypatch.setenv("CODE_SCALPEL_LICENSE_PATH", str(empty_dir / "license.jwt"))
        monkeypatch.setenv("CODE_SCALPEL_DISABLE_LICENSE_DISCOVERY", "1")

        test_file = tmp_path / "test.py"
        test_file.write_text("x = 1\n")

        result = await code_policy_check(paths=[str(test_file)])

        assert (
            result.tier == "community"
        ), f"Empty license directory should default to community tier, got {result.tier}"

        monkeypatch.delenv("CODE_SCALPEL_LICENSE_PATH", raising=False)
        monkeypatch.delenv("CODE_SCALPEL_DISABLE_LICENSE_DISCOVERY", raising=False)


class TestLicenseGracefulDegradation:
    """Test graceful degradation when license validation has issues."""

    @pytest.mark.asyncio
    async def test_tool_continues_with_community_tier_on_license_error(self, tmp_path, monkeypatch):
        """Tool should continue working with Community tier even if license validation fails."""
        # Create a malformed JWT file (not valid base64)
        malformed_license = tmp_path / "malformed.jwt"
        malformed_license.write_text("this-is-not-a-valid-jwt-token")

        monkeypatch.setenv("CODE_SCALPEL_LICENSE_PATH", str(malformed_license))
        monkeypatch.setenv("CODE_SCALPEL_DISABLE_LICENSE_DISCOVERY", "1")

        test_file = tmp_path / "test.py"
        test_file.write_text("""
try:
    pass
except:
    pass
""")

        # Should not raise exception, should fall back to Community tier
        result = await code_policy_check(paths=[str(test_file)])

        assert result.success, "Tool should succeed even with malformed license"
        assert result.tier == "community", f"Malformed license should fall back to community tier, got {result.tier}"
        assert len(result.violations) > 0, "Should still detect violations"

        monkeypatch.delenv("CODE_SCALPEL_LICENSE_PATH", raising=False)
        monkeypatch.delenv("CODE_SCALPEL_DISABLE_LICENSE_DISCOVERY", raising=False)

    @pytest.mark.asyncio
    async def test_tool_reports_license_tier_in_result(self, tmp_path, monkeypatch):
        """Result should always include tier information."""
        monkeypatch.setenv("CODE_SCALPEL_DISABLE_LICENSE_DISCOVERY", "1")

        test_file = tmp_path / "test.py"
        test_file.write_text("x = 1\n")

        result = await code_policy_check(paths=[str(test_file)])

        # Verify tier attribute exists
        assert hasattr(result, "tier"), "Result should have tier attribute"
        assert result.tier in [
            "community",
            "pro",
            "enterprise",
        ], f"Tier should be valid value, got {result.tier}"

        monkeypatch.delenv("CODE_SCALPEL_DISABLE_LICENSE_DISCOVERY", raising=False)
