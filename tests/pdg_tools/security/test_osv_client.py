"""
Comprehensive tests for OSV Client.

[20251213_TEST] v1.5.0 - Tests for OSV API client with mocked responses.

Tests cover:
- Single package queries
- Batch queries
- Severity parsing from multiple formats
- Fixed version extraction
- Error handling and retries
- Caching behavior
- Ecosystem normalization
"""

import urllib.error
from unittest.mock import MagicMock, patch

import pytest

from code_scalpel.security.dependencies import (
    OSV_API_URL,
    OSVClient,
    OSVError,
    Vulnerability,
)


class TestVulnerability:
    """Tests for the Vulnerability dataclass."""

    def test_vulnerability_creation(self):
        """Test creating a Vulnerability instance."""
        v = Vulnerability(
            id="CVE-2023-12345",
            summary="Test vulnerability",
            severity="HIGH",
            package="requests",
            vulnerable_version="2.25.0",
            fixed_version="2.31.0",
            aliases=["GHSA-xxx"],
            references=["https://example.com/advisory"],
        )
        assert v.id == "CVE-2023-12345"
        assert v.severity == "HIGH"
        assert v.fixed_version == "2.31.0"

    def test_vulnerability_to_dict(self):
        """Test converting Vulnerability to dictionary."""
        v = Vulnerability(
            id="CVE-2023-12345",
            summary="Test vulnerability",
            severity="HIGH",
            package="requests",
            vulnerable_version="2.25.0",
            fixed_version="2.31.0",
        )
        d = v.to_dict()
        assert d["id"] == "CVE-2023-12345"
        assert d["severity"] == "HIGH"
        assert d["fixed_version"] == "2.31.0"
        assert isinstance(d["aliases"], list)
        assert isinstance(d["references"], list)

    def test_vulnerability_default_values(self):
        """Test that default values are set correctly."""
        v = Vulnerability(
            id="TEST",
            summary="Test",
            severity="LOW",
            package="test",
            vulnerable_version="1.0.0",
            fixed_version=None,
        )
        assert v.aliases == []
        assert v.references == []
        assert v.fixed_version is None


class TestOSVClientInit:
    """Tests for OSVClient initialization."""

    def test_default_init(self):
        """Test default initialization."""
        client = OSVClient()
        assert client.timeout == 10
        assert client.cache_enabled is True
        assert client._cache == {}

    def test_custom_timeout(self):
        """Test custom timeout setting."""
        client = OSVClient(timeout=30)
        assert client.timeout == 30

    def test_cache_disabled(self):
        """Test initializing with cache disabled."""
        client = OSVClient(cache_enabled=False)
        assert client.cache_enabled is False


class TestEcosystemNormalization:
    """Tests for ecosystem name normalization."""

    @pytest.mark.parametrize(
        "input_eco,expected",
        [
            ("pypi", "PyPI"),
            ("PyPI", "PyPI"),
            ("python", "PyPI"),
            ("npm", "npm"),
            ("javascript", "npm"),
            ("js", "npm"),
            ("maven", "Maven"),
            ("java", "Maven"),
            ("go", "Go"),
            ("golang", "Go"),
            ("cargo", "crates.io"),
            ("rust", "crates.io"),
            ("nuget", "NuGet"),
            ("dotnet", "NuGet"),
            ("rubygems", "RubyGems"),
            ("ruby", "RubyGems"),
            ("UnknownEco", "UnknownEco"),  # Passthrough for unknown
        ],
    )
    def test_ecosystem_normalization(self, input_eco, expected):
        """Test various ecosystem name normalizations."""
        client = OSVClient()
        assert client._normalize_ecosystem(input_eco) == expected


class TestSeverityParsing:
    """Tests for severity extraction from OSV responses."""

    def test_severity_from_database_specific(self):
        """Test extracting severity from database_specific field."""
        client = OSVClient()
        vuln_data = {"database_specific": {"severity": "HIGH"}}
        assert client._parse_severity(vuln_data) == "HIGH"

    def test_severity_from_ecosystem_specific(self):
        """Test extracting severity from ecosystem_specific field."""
        client = OSVClient()
        vuln_data = {"ecosystem_specific": {"severity": "CRITICAL"}}
        assert client._parse_severity(vuln_data) == "CRITICAL"

    def test_severity_from_cvss_score_critical(self):
        """Test CVSS score >= 9.0 maps to CRITICAL."""
        client = OSVClient()
        vuln_data = {"severity": [{"type": "CVSS_V3", "score": 9.5}]}
        assert client._parse_severity(vuln_data) == "CRITICAL"

    def test_severity_from_cvss_score_high(self):
        """Test CVSS score 7.0-8.9 maps to HIGH."""
        client = OSVClient()
        vuln_data = {"severity": [{"type": "CVSS_V3", "score": 7.5}]}
        assert client._parse_severity(vuln_data) == "HIGH"

    def test_severity_from_cvss_score_medium(self):
        """Test CVSS score 4.0-6.9 maps to MEDIUM."""
        client = OSVClient()
        vuln_data = {"severity": [{"type": "CVSS_V3", "score": 5.0}]}
        assert client._parse_severity(vuln_data) == "MEDIUM"

    def test_severity_from_cvss_score_low(self):
        """Test CVSS score < 4.0 maps to LOW."""
        client = OSVClient()
        vuln_data = {"severity": [{"type": "CVSS_V3", "score": 2.5}]}
        assert client._parse_severity(vuln_data) == "LOW"

    def test_severity_from_cvss_string_score(self):
        """Test parsing numeric score from string."""
        client = OSVClient()
        vuln_data = {"severity": [{"score": "8.1"}]}
        assert client._parse_severity(vuln_data) == "HIGH"

    def test_severity_unknown_when_missing(self):
        """Test UNKNOWN returned when severity not found."""
        client = OSVClient()
        vuln_data = {}
        assert client._parse_severity(vuln_data) == "UNKNOWN"

    def test_severity_unknown_with_invalid_data(self):
        """Test UNKNOWN returned with unparseable data."""
        client = OSVClient()
        vuln_data = {"severity": [{"score": "not-a-number"}]}
        assert client._parse_severity(vuln_data) == "UNKNOWN"

    def test_severity_lowercase_normalized(self):
        """Test that lowercase severity values are uppercased."""
        client = OSVClient()
        vuln_data = {"database_specific": {"severity": "medium"}}
        assert client._parse_severity(vuln_data) == "MEDIUM"


class TestFixedVersionParsing:
    """Tests for fixed version extraction."""

    def test_fixed_version_from_ranges(self):
        """Test extracting fixed version from ranges."""
        client = OSVClient()
        affected = [
            {
                "package": {"name": "requests"},
                "ranges": [
                    {
                        "type": "ECOSYSTEM",
                        "events": [{"introduced": "0"}, {"fixed": "2.31.0"}],
                    }
                ],
            }
        ]
        assert client._parse_fixed_version(affected, "requests") == "2.31.0"

    def test_fixed_version_case_insensitive(self):
        """Test package name matching is case insensitive."""
        client = OSVClient()
        affected = [
            {
                "package": {"name": "Requests"},
                "ranges": [{"events": [{"fixed": "2.31.0"}]}],
            }
        ]
        assert client._parse_fixed_version(affected, "requests") == "2.31.0"

    def test_fixed_version_not_found(self):
        """Test None returned when no fixed version."""
        client = OSVClient()
        affected = [{"package": {"name": "other-package"}, "ranges": []}]
        assert client._parse_fixed_version(affected, "requests") is None

    def test_fixed_version_empty_affected(self):
        """Test None returned with empty affected list."""
        client = OSVClient()
        assert client._parse_fixed_version([], "requests") is None


class TestQueryPackage:
    """Tests for single package queries.

    [20251213_FEATURE] v1.5.2 - Refactored to use proper pytest fixtures
    for mock isolation instead of @patch decorators.
    """

    def test_query_package_success(self, osv_client_no_cache, osv_mock_urlopen, mock_osv_response):
        """Test successful package query."""
        # Set up mock response
        mock_response = mock_osv_response(
            {
                "vulns": [
                    {
                        "id": "CVE-2023-32681",
                        "summary": "Requests vulnerability",
                        "database_specific": {"severity": "HIGH"},
                        "affected": [
                            {
                                "package": {"name": "requests"},
                                "ranges": [{"events": [{"fixed": "2.31.0"}]}],
                            }
                        ],
                        "aliases": ["GHSA-j8r2-6x86-q33q"],
                        "references": [{"url": "https://example.com"}],
                    }
                ]
            }
        )
        osv_mock_urlopen.return_value = mock_response

        # Test
        vulns = osv_client_no_cache.query_package("requests", "2.25.0", "PyPI")

        assert len(vulns) == 1
        assert vulns[0].id == "CVE-2023-32681"
        assert vulns[0].severity == "HIGH"
        assert vulns[0].fixed_version == "2.31.0"
        assert "GHSA-j8r2-6x86-q33q" in vulns[0].aliases

    def test_query_package_no_vulns(self, osv_client_no_cache, osv_mock_urlopen, mock_osv_response):
        """Test query returning no vulnerabilities."""
        mock_response = mock_osv_response({"vulns": []})
        osv_mock_urlopen.return_value = mock_response

        vulns = osv_client_no_cache.query_package("safe-package", "1.0.0")

        assert vulns == []

    def test_query_package_empty_response(self, osv_client_no_cache, osv_mock_urlopen, mock_osv_response):
        """Test query with empty response body."""
        mock_response = mock_osv_response({})
        osv_mock_urlopen.return_value = mock_response

        vulns = osv_client_no_cache.query_package("package", "1.0.0")

        assert vulns == []

    def test_query_package_caching(self, osv_client_with_cache, osv_mock_urlopen, mock_osv_response):
        """Test that results are cached."""
        mock_response = mock_osv_response({"vulns": [{"id": "CVE-123", "summary": "Test"}]})
        osv_mock_urlopen.return_value = mock_response

        # First call
        vulns1 = osv_client_with_cache.query_package("requests", "2.25.0")
        # Second call (should use cache)
        vulns2 = osv_client_with_cache.query_package("requests", "2.25.0")

        # Should only make one HTTP request
        assert osv_mock_urlopen.call_count == 1
        assert len(vulns1) == len(vulns2)

    def test_query_package_error_returns_empty(self, osv_client_no_cache, osv_mock_urlopen, mock_osv_error):
        """Test that errors return empty list (fail open)."""
        osv_mock_urlopen.side_effect = mock_osv_error("URLError")

        vulns = osv_client_no_cache.query_package("requests", "2.25.0")

        assert vulns == []


class TestQueryBatch:
    """Tests for batch package queries.

    [20251213_FEATURE] v1.5.2 - Refactored to use proper pytest fixtures
    for mock isolation instead of @patch decorators.
    """

    def test_query_batch_success(self, osv_client_no_cache, osv_mock_urlopen, mock_osv_response):
        """Test successful batch query."""
        mock_response = mock_osv_response(
            {
                "results": [
                    {"vulns": [{"id": "CVE-1", "summary": "Vuln 1"}]},
                    {"vulns": []},
                ]
            }
        )
        osv_mock_urlopen.return_value = mock_response

        packages = [
            {"name": "requests", "version": "2.25.0"},
            {"name": "flask", "version": "2.0.0"},
        ]
        results = osv_client_no_cache.query_batch(packages)

        assert "requests:2.25.0" in results
        assert "flask:2.0.0" in results
        assert len(results["requests:2.25.0"]) == 1
        assert len(results["flask:2.0.0"]) == 0

    def test_query_batch_empty_input(self):
        """Test batch query with empty package list."""
        client = OSVClient()
        results = client.query_batch([])
        assert results == {}

    def test_query_batch_with_ecosystem(self, osv_client_no_cache, osv_mock_urlopen, mock_osv_response):
        """Test batch query with explicit ecosystems."""
        mock_response = mock_osv_response(
            {
                "results": [
                    {"vulns": []},
                ]
            }
        )
        osv_mock_urlopen.return_value = mock_response

        packages = [
            {"name": "lodash", "version": "4.17.0", "ecosystem": "npm"},
        ]
        results = osv_client_no_cache.query_batch(packages)

        assert "lodash:4.17.0" in results

    def test_query_batch_error_returns_empty(self, osv_client_no_cache, osv_mock_urlopen, mock_osv_error):
        """Test batch query error returns empty dict."""
        osv_mock_urlopen.side_effect = mock_osv_error("URLError")

        packages = [{"name": "requests", "version": "2.25.0"}]
        results = osv_client_no_cache.query_batch(packages)

        assert results == {}


class TestMakeRequest:
    """Tests for HTTP request handling.

    [20251213_FEATURE] v1.5.2 - Refactored to use proper pytest fixtures
    for mock isolation instead of @patch decorators.
    """

    def test_successful_request(self, osv_mock_urlopen, mock_osv_response):
        """Test successful HTTP request."""
        mock_response = mock_osv_response({"vulns": []})
        osv_mock_urlopen.return_value = mock_response

        client = OSVClient()
        result = client._make_request(OSV_API_URL, {"test": "data"})

        assert result == {"vulns": []}

    @patch("code_scalpel.ast_tools.osv_client.time.sleep")
    def test_retry_on_rate_limit(self, mock_sleep, osv_mock_urlopen, mock_osv_response):
        """Test retry on 429 rate limit."""
        # First call: rate limited, second call: success
        mock_rate_limit = urllib.error.HTTPError(url="", code=429, msg="Too Many Requests", hdrs={}, fp=None)
        mock_success = mock_osv_response({"vulns": []})

        osv_mock_urlopen.side_effect = [mock_rate_limit, mock_success]

        client = OSVClient()
        result = client._make_request(OSV_API_URL, {})

        assert result == {"vulns": []}
        assert mock_sleep.called

    @patch("code_scalpel.ast_tools.osv_client.time.sleep")
    def test_retry_on_server_error(self, mock_sleep, osv_mock_urlopen, mock_osv_response):
        """Test retry on 5xx server errors."""
        mock_error = urllib.error.HTTPError(url="", code=500, msg="Internal Server Error", hdrs={}, fp=None)
        mock_success = mock_osv_response({"vulns": []})

        osv_mock_urlopen.side_effect = [mock_error, mock_success]

        client = OSVClient()
        result = client._make_request(OSV_API_URL, {})

        assert result == {"vulns": []}

    def test_raise_on_client_error(self, osv_mock_urlopen):
        """Test OSVError raised on 4xx errors (except 429)."""
        mock_error = urllib.error.HTTPError(url="", code=400, msg="Bad Request", hdrs={}, fp=None)
        osv_mock_urlopen.side_effect = mock_error

        client = OSVClient()
        with pytest.raises(OSVError) as exc_info:
            client._make_request(OSV_API_URL, {})

        assert "400" in str(exc_info.value)

    @patch("code_scalpel.ast_tools.osv_client.time.sleep")
    def test_max_retries_exceeded(self, mock_sleep, osv_mock_urlopen, mock_osv_error):
        """Test OSVError raised after max retries."""
        osv_mock_urlopen.side_effect = mock_osv_error("URLError")

        client = OSVClient()
        with pytest.raises(OSVError) as exc_info:
            client._make_request(OSV_API_URL, {})

        assert "retries" in str(exc_info.value).lower()

    def test_invalid_json_response(self, osv_mock_urlopen, mock_osv_response):
        """Test OSVError on invalid JSON response."""
        mock_response = MagicMock()
        mock_response.read.return_value = b"not valid json"
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)
        osv_mock_urlopen.return_value = mock_response

        client = OSVClient()
        with pytest.raises(OSVError) as exc_info:
            client._make_request(OSV_API_URL, {})

        assert "JSON" in str(exc_info.value)


class TestClearCache:
    """Tests for cache management.

    [20251213_FEATURE] v1.5.2 - Refactored to use proper pytest fixtures.
    """

    def test_clear_cache(self, osv_client_with_cache, osv_mock_urlopen, mock_osv_response):
        """Test clearing the cache."""
        mock_response = mock_osv_response({"vulns": []})
        osv_mock_urlopen.return_value = mock_response

        # Populate cache
        osv_client_with_cache.query_package("requests", "2.25.0")
        assert len(osv_client_with_cache._cache) == 1

        # Clear cache
        osv_client_with_cache.clear_cache()
        assert osv_client_with_cache._cache == {}


class TestIntegrationScenarios:
    """Integration-style tests for realistic scenarios.

    [20251213_FEATURE] v1.5.2 - Refactored to use proper pytest fixtures.
    """

    def test_multiple_vulns_in_package(self, osv_client_no_cache, osv_mock_urlopen, mock_osv_response):
        """Test handling multiple vulnerabilities in one package."""
        mock_response = mock_osv_response(
            {
                "vulns": [
                    {
                        "id": "CVE-2023-001",
                        "summary": "First vulnerability",
                        "database_specific": {"severity": "HIGH"},
                    },
                    {
                        "id": "CVE-2023-002",
                        "summary": "Second vulnerability",
                        "database_specific": {"severity": "CRITICAL"},
                    },
                ]
            }
        )
        osv_mock_urlopen.return_value = mock_response

        vulns = osv_client_no_cache.query_package("vulnerable-pkg", "1.0.0")

        assert len(vulns) == 2
        severities = {v.severity for v in vulns}
        assert "HIGH" in severities
        assert "CRITICAL" in severities

    def test_references_limited_to_five(self, osv_client_no_cache, osv_mock_urlopen, mock_osv_response):
        """Test that references are limited to 5."""
        mock_response = mock_osv_response(
            {
                "vulns": [
                    {
                        "id": "CVE-123",
                        "summary": "Test",
                        "references": [{"url": f"https://example.com/{i}"} for i in range(10)],
                    }
                ]
            }
        )
        osv_mock_urlopen.return_value = mock_response

        vulns = osv_client_no_cache.query_package("test", "1.0.0")

        assert len(vulns[0].references) == 5

    def test_missing_fields_handled_gracefully(self, osv_client_no_cache, osv_mock_urlopen, mock_osv_response):
        """Test handling of vulnerabilities with missing fields."""
        mock_response = mock_osv_response(
            {
                "vulns": [
                    {
                        "id": "CVE-MINIMAL",
                        # No summary, severity, affected, aliases, or references
                    }
                ]
            }
        )
        osv_mock_urlopen.return_value = mock_response

        vulns = osv_client_no_cache.query_package("test", "1.0.0")

        assert len(vulns) == 1
        assert vulns[0].id == "CVE-MINIMAL"
        assert vulns[0].severity == "UNKNOWN"
        assert vulns[0].fixed_version is None
