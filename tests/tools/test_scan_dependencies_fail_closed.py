"""
[20260120_TEST] Fail-closed security tests for scan_dependencies

Tests that scan_dependencies returns success=False when OSV API fails,
preventing AI agents from hallucinating "no vulnerabilities found" when
the security scanner cannot verify the dependency safety.

Security Principle: Network error is NOT a clean bill of health.
"""

from unittest.mock import MagicMock, patch

from code_scalpel.mcp.helpers.security_helpers import _scan_dependencies_sync
from code_scalpel.security.dependencies.osv_client import OSVError


class TestScanDependenciesFailClosed:
    """Test that scan_dependencies fails closed on OSV API errors."""

    def test_osv_timeout_returns_failure(self, tmp_path):
        """OSV API timeout must return success=False, not success=True."""
        # Create a minimal requirements.txt
        req_file = tmp_path / "requirements.txt"
        req_file.write_text("requests==2.28.0\n")

        # Mock OSV client to raise timeout
        with patch("code_scalpel.security.dependencies.VulnerabilityScanner") as mock_scanner_class:
            mock_scanner = MagicMock()
            mock_scanner.osv_client.query_batch.side_effect = OSVError("Timeout after 30s")
            mock_scanner_class.return_value.__enter__.return_value = mock_scanner

            result = _scan_dependencies_sync(
                path=str(req_file),
                scan_vulnerabilities=True,
                timeout=30,
            )

        # CRITICAL: Must return success=False (not True)
        assert result.success is False, (
            "OSV timeout must return success=False (fail-closed). "
            f"Got success={result.success} with errors={result.errors}"
        )
        assert len(result.errors) > 0, "Should have error message"
        assert any(
            "OSV query failed" in err for err in result.errors
        ), f"Expected 'OSV query failed' in errors, got: {result.errors}"

    def test_osv_network_error_returns_failure(self, tmp_path):
        """OSV API network error must return success=False."""
        req_file = tmp_path / "requirements.txt"
        req_file.write_text("flask==2.0.0\n")

        with patch("code_scalpel.security.dependencies.VulnerabilityScanner") as mock_scanner_class:
            mock_scanner = MagicMock()
            mock_scanner.osv_client.query_batch.side_effect = OSVError("Connection refused")
            mock_scanner_class.return_value.__enter__.return_value = mock_scanner

            result = _scan_dependencies_sync(
                path=str(req_file),
                scan_vulnerabilities=True,
            )

        assert result.success is False, "Network error must return success=False"
        assert len(result.errors) > 0
        assert any("OSV query failed" in err for err in result.errors)

    def test_osv_rate_limit_returns_failure(self, tmp_path):
        """OSV API rate limit must return success=False."""
        req_file = tmp_path / "requirements.txt"
        req_file.write_text("django==3.2.0\n")

        with patch("code_scalpel.security.dependencies.VulnerabilityScanner") as mock_scanner_class:
            mock_scanner = MagicMock()
            mock_scanner.osv_client.query_batch.side_effect = OSVError("Rate limit exceeded")
            mock_scanner_class.return_value.__enter__.return_value = mock_scanner

            result = _scan_dependencies_sync(
                path=str(req_file),
                scan_vulnerabilities=True,
            )

        assert result.success is False, "Rate limit must return success=False"
        assert len(result.errors) > 0
        assert any("OSV query failed" in err for err in result.errors)

    def test_successful_scan_returns_success(self, tmp_path):
        """When OSV API succeeds, scan should return success=True."""
        req_file = tmp_path / "requirements.txt"
        req_file.write_text("requests==2.28.0\n")

        # Mock successful OSV response (no vulnerabilities)
        with patch("code_scalpel.security.dependencies.VulnerabilityScanner") as mock_scanner_class:
            mock_scanner = MagicMock()
            mock_scanner.osv_client.query_batch.return_value = {}  # No vulns found
            mock_scanner_class.return_value.__enter__.return_value = mock_scanner

            result = _scan_dependencies_sync(
                path=str(req_file),
                scan_vulnerabilities=True,
            )

        assert result.success is True, "Successful scan should return success=True"
        assert len(result.errors) == 0, f"Should have no errors, got: {result.errors}"

    def test_scan_with_vulnerabilities_returns_success(self, tmp_path):
        """Finding vulnerabilities is still a successful scan (data retrieved)."""
        req_file = tmp_path / "requirements.txt"
        req_file.write_text("requests==2.20.0\n")  # Known vulnerable version

        # Mock OSV response with vulnerability
        with patch("code_scalpel.security.dependencies.VulnerabilityScanner") as mock_scanner_class:
            mock_scanner = MagicMock()
            mock_scanner.osv_client.query_batch.return_value = {
                "requests@2.20.0": [
                    {
                        "id": "CVE-2018-18074",
                        "summary": "Redirect vulnerability",
                        "database_specific": {"severity": "MODERATE"},
                    }
                ]
            }
            mock_scanner_class.return_value.__enter__.return_value = mock_scanner

            result = _scan_dependencies_sync(
                path=str(req_file),
                scan_vulnerabilities=True,
            )

        # Finding vulnerabilities is STILL success=True (we got data from API)
        assert result.success is True, "Finding vulns should return success=True"
        assert result.total_vulnerabilities > 0, "Should have found vulnerabilities"
        assert len(result.errors) == 0

    def test_scan_without_osv_query_returns_success(self, tmp_path):
        """Scan with scan_vulnerabilities=False should always succeed."""
        req_file = tmp_path / "requirements.txt"
        req_file.write_text("requests==2.28.0\n")

        result = _scan_dependencies_sync(
            path=str(req_file),
            scan_vulnerabilities=False,  # Skip OSV query
        )

        assert result.success is True, "Scan without OSV should return success=True"
        assert len(result.errors) == 0

    def test_error_message_contains_failure_reason(self, tmp_path):
        """Error message should explain why OSV query failed."""
        req_file = tmp_path / "requirements.txt"
        req_file.write_text("flask==2.0.0\n")

        specific_error = "OSV API returned 503 Service Unavailable"
        with patch("code_scalpel.security.dependencies.VulnerabilityScanner") as mock_scanner_class:
            mock_scanner = MagicMock()
            mock_scanner.osv_client.query_batch.side_effect = OSVError(specific_error)
            mock_scanner_class.return_value.__enter__.return_value = mock_scanner

            result = _scan_dependencies_sync(
                path=str(req_file),
                scan_vulnerabilities=True,
            )

        assert result.success is False
        assert len(result.errors) == 1
        assert "OSV query failed" in result.errors[0]
        assert specific_error in result.errors[0]

    def test_multiple_errors_all_fail_closed(self, tmp_path):
        """If OSV fails AND other errors occur, still fail closed."""
        req_file = tmp_path / "requirements.txt"
        req_file.write_text("requests==2.28.0\n")

        with patch("code_scalpel.security.dependencies.VulnerabilityScanner") as mock_scanner_class:
            mock_scanner = MagicMock()
            mock_scanner.osv_client.query_batch.side_effect = OSVError("Network down")
            mock_scanner_class.return_value.__enter__.return_value = mock_scanner

            result = _scan_dependencies_sync(
                path=str(req_file),
                scan_vulnerabilities=True,
            )

        # Even if multiple errors, OSV failure means success=False
        assert result.success is False
        assert any("OSV query failed" in err for err in result.errors)
