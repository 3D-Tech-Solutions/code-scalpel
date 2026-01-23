"""
OSV Client - Query Open Source Vulnerabilities database for CVE data.

[20251213_FEATURE] v1.5.0 - New OSV API client for dependency vulnerability scanning.

This module provides a client for the OSV.dev API to check Python and JavaScript
packages for known security vulnerabilities.

Usage:
    client = OSVClient()
    vulns = client.query_package("requests", "2.25.0", "PyPI")
    for v in vulns:
        print(f"{v['id']}: {v['summary']} (fixed in {v['fixed']})")

API Documentation: https://osv.dev/docs/
"""

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, TypedDict


class OSVVulnerabilityDict(TypedDict):
    """OSV vulnerability for JSON serialization."""

    id: str
    summary: str
    severity: str
    package: str
    vulnerable_version: str
    fixed_version: str | None
    aliases: list[str]
    references: list[str]


# [20251213_FEATURE] OSV API configuration
OSV_API_URL = "https://api.osv.dev/v1/query"
OSV_BATCH_URL = "https://api.osv.dev/v1/querybatch"
DEFAULT_TIMEOUT = 10  # seconds
MAX_RETRIES = 3
RETRY_DELAY = 1  # seconds


@dataclass
class Vulnerability:
    """Represents a security vulnerability from OSV."""

    id: str  # e.g., "CVE-2023-32681" or "GHSA-xxx"
    summary: str
    severity: str  # "CRITICAL", "HIGH", "MEDIUM", "LOW", "UNKNOWN"
    package: str
    vulnerable_version: str
    fixed_version: str | None
    aliases: list[str] = field(default_factory=list)
    references: list[str] = field(default_factory=list)

    def to_dict(self) -> OSVVulnerabilityDict:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "summary": self.summary,
            "severity": self.severity,
            "package": self.package,
            "vulnerable_version": self.vulnerable_version,
            "fixed_version": self.fixed_version,
            "aliases": self.aliases,
            "references": self.references,
        }


class OSVClient:
    """
    Client for querying the OSV (Open Source Vulnerabilities) API.

    Supports querying individual packages or batches of packages for
    known security vulnerabilities with CVE/GHSA identifiers.
    """

    # [20251213_FEATURE] Ecosystem mapping for different package managers
    ECOSYSTEM_MAP = {
        "pypi": "PyPI",
        "python": "PyPI",
        "npm": "npm",
        "javascript": "npm",
        "js": "npm",
        "maven": "Maven",
        "java": "Maven",
        "go": "Go",
        "golang": "Go",
        "cargo": "crates.io",
        "rust": "crates.io",
        "nuget": "NuGet",
        "dotnet": "NuGet",
        "rubygems": "RubyGems",
        "ruby": "RubyGems",
    }

    def __init__(self, timeout: int = DEFAULT_TIMEOUT, cache_enabled: bool = True):
        """
        Initialize OSV client.

        Args:
            timeout: Request timeout in seconds
            cache_enabled: Whether to cache results (default: True)
        """
        self.timeout = timeout
        self.cache_enabled = cache_enabled
        self._cache: dict[str, list[Vulnerability]] = {}

    def _normalize_ecosystem(self, ecosystem: str) -> str:
        """Normalize ecosystem name to OSV format."""
        return self.ECOSYSTEM_MAP.get(ecosystem.lower(), ecosystem)

    def _make_request(self, url: str, data: dict[str, Any]) -> dict[str, Any]:
        """
        Make HTTP POST request to OSV API with retry logic.

        Args:
            url: API endpoint URL
            data: Request payload

        Returns:
            Parsed JSON response

        Raises:
            OSVError: If request fails after retries
        """
        payload = json.dumps(data).encode("utf-8")
        headers = {"Content-Type": "application/json"}

        # [20251218_SECURITY] Validate URL scheme to prevent file:/ or custom scheme attacks (B310)
        if not url.startswith(("https://", "http://")):
            raise OSVError(f"Invalid URL scheme. Only http(s):// allowed, got: {url}")

        last_error = None
        for attempt in range(MAX_RETRIES):
            try:
                req = urllib.request.Request(url, data=payload, headers=headers)
                with urllib.request.urlopen(req, timeout=self.timeout) as response:  # nosec B310
                    return json.loads(response.read().decode("utf-8"))
            except urllib.error.HTTPError as e:
                if e.code == 429:  # Rate limited
                    time.sleep(RETRY_DELAY * (attempt + 1))
                    last_error = e
                    continue
                elif e.code >= 500:  # Server error, retry
                    time.sleep(RETRY_DELAY)
                    last_error = e
                    continue
                else:
                    raise OSVError(f"HTTP {e.code}: {e.reason}") from e
            except urllib.error.URLError as e:
                last_error = e
                time.sleep(RETRY_DELAY)
                continue
            except json.JSONDecodeError as e:
                raise OSVError(f"Invalid JSON response: {e}") from e

        raise OSVError(f"Request failed after {MAX_RETRIES} retries: {last_error}")

    def _parse_severity(self, vuln_data: dict[str, Any]) -> str:
        """
        Extract severity from OSV vulnerability data.

        OSV uses CVSS scores in the 'severity' field or 'database_specific'.
        """
        import re

        # [20251213_FEATURE] Parse CVSS severity from multiple possible locations

        def score_to_severity(score: float) -> str:
            """Convert numeric CVSS score to severity level."""
            if score >= 9.0:
                return "CRITICAL"
            elif score >= 7.0:
                return "HIGH"
            elif score >= 4.0:
                return "MEDIUM"
            else:
                return "LOW"

        # Check severity array first (OSV format) - look for numeric scores
        if "severity" in vuln_data:
            for sev in vuln_data["severity"]:
                score_val = sev.get("score")
                # Handle direct numeric scores
                if isinstance(score_val, (int, float)):
                    return score_to_severity(float(score_val))
                # Handle string scores that might be numeric
                if isinstance(score_val, str):
                    # Try to parse as a number first
                    try:
                        numeric_score = float(score_val)
                        return score_to_severity(numeric_score)
                    except ValueError:
                        pass
                    # Try to find a number in the string (e.g., "CVSS:3.1/AV:N/... 9.8")
                    match = re.search(r"(\d+\.?\d*)", score_val)
                    if match:
                        try:
                            return score_to_severity(float(match.group(1)))
                        except ValueError:
                            pass

        # Check database_specific for severity
        db_specific = vuln_data.get("database_specific", {})
        if "severity" in db_specific:
            sev = db_specific["severity"].upper()
            if sev in ("CRITICAL", "HIGH", "MEDIUM", "LOW"):
                return sev

        # Check ecosystem_specific
        eco_specific = vuln_data.get("ecosystem_specific", {})
        if "severity" in eco_specific:
            sev = eco_specific["severity"].upper()
            if sev in ("CRITICAL", "HIGH", "MEDIUM", "LOW"):
                return sev

        # Fallback: try to parse score from any remaining severity entries
        for sev in vuln_data.get("severity", []):
            if "score" in sev:
                try:
                    # Try to extract numeric score
                    score_str = sev["score"]
                    # CVSS scores are 0-10
                    if isinstance(score_str, (int, float)):
                        return score_to_severity(float(score_str))
                    else:
                        # Try to find a number in the string
                        match = re.search(r"(\d+\.?\d*)", str(score_str))
                        if match:
                            return score_to_severity(float(match.group(1)))
                except (ValueError, TypeError):
                    continue

        return "UNKNOWN"

    def _parse_fixed_version(self, affected: list[dict[str, Any]], package_name: str) -> str | None:
        """Extract the fixed version from affected ranges."""
        # [20251213_FEATURE] Parse fixed version from OSV affected ranges
        for aff in affected:
            pkg = aff.get("package", {})
            if pkg.get("name", "").lower() == package_name.lower():
                for rng in aff.get("ranges", []):
                    for event in rng.get("events", []):
                        if "fixed" in event:
                            return event["fixed"]
                # Also check versions array
                aff.get("versions", [])
                # The fixed version is typically not in the versions list,
                # but we might find it in database_specific
        return None

    def query_package(self, package: str, version: str, ecosystem: str = "PyPI") -> list[Vulnerability]:
        """
        Query OSV for vulnerabilities affecting a specific package version.

        Args:
            package: Package name (e.g., "requests")
            version: Package version (e.g., "2.25.0")
            ecosystem: Package ecosystem (e.g., "PyPI", "npm")

        Returns:
            List of Vulnerability objects
        """
        # [20251213_FEATURE] Query single package for vulnerabilities

        # Check cache first
        cache_key = f"{ecosystem}:{package}:{version}"
        if self.cache_enabled and cache_key in self._cache:
            return self._cache[cache_key]

        ecosystem = self._normalize_ecosystem(ecosystem)

        payload = {
            "package": {
                "name": package,
                "ecosystem": ecosystem,
            },
            "version": version,
        }

        try:
            response = self._make_request(OSV_API_URL, payload)
        except OSVError:
            # Return empty list on error (fail open for availability)
            return []

        vulnerabilities = []
        for vuln in response.get("vulns", []):
            v = Vulnerability(
                id=vuln.get("id", "UNKNOWN"),
                summary=vuln.get("summary", vuln.get("details", "No description")),
                severity=self._parse_severity(vuln),
                package=package,
                vulnerable_version=version,
                fixed_version=self._parse_fixed_version(vuln.get("affected", []), package),
                aliases=vuln.get("aliases", []),
                references=[ref.get("url", "") for ref in vuln.get("references", []) if ref.get("url")][
                    :5
                ],  # Limit to 5 references
            )
            vulnerabilities.append(v)

        # Cache result
        if self.cache_enabled:
            self._cache[cache_key] = vulnerabilities

        return vulnerabilities

    def query_batch(self, packages: list[dict[str, str]]) -> dict[str, list[Vulnerability]]:
        """
        Query OSV for vulnerabilities in multiple packages at once.

        Args:
            packages: List of dicts with 'name', 'version', and optionally 'ecosystem'
                      Example: [{"name": "requests", "version": "2.25.0", "ecosystem": "PyPI"}]

        Returns:
            Dict mapping "package:version" to list of vulnerabilities
        """
        # [20251213_FEATURE] Batch query for efficiency with many dependencies

        if not packages:
            return {}

        # Build batch query
        queries = []
        for pkg in packages:
            ecosystem = self._normalize_ecosystem(pkg.get("ecosystem", "PyPI"))
            queries.append(
                {
                    "package": {
                        "name": pkg["name"],
                        "ecosystem": ecosystem,
                    },
                    "version": pkg["version"],
                }
            )

        payload = {"queries": queries}

        try:
            response = self._make_request(OSV_BATCH_URL, payload)
        except OSVError:
            return {}

        results = {}
        for i, result in enumerate(response.get("results", [])):
            if i >= len(packages):
                break

            pkg = packages[i]
            key = f"{pkg['name']}:{pkg['version']}"
            vulnerabilities = []

            for vuln in result.get("vulns", []):
                v = Vulnerability(
                    id=vuln.get("id", "UNKNOWN"),
                    summary=vuln.get("summary", vuln.get("details", "No description")),
                    severity=self._parse_severity(vuln),
                    package=pkg["name"],
                    vulnerable_version=pkg["version"],
                    fixed_version=self._parse_fixed_version(vuln.get("affected", []), pkg["name"]),
                    aliases=vuln.get("aliases", []),
                    references=[ref.get("url", "") for ref in vuln.get("references", []) if ref.get("url")][:5],
                )
                vulnerabilities.append(v)

            results[key] = vulnerabilities

        return results

    def clear_cache(self):
        """Clear the vulnerability cache."""
        self._cache.clear()


class OSVError(Exception):
    """Exception raised for OSV API errors."""

    pass


# [20251225_FEATURE] Export public API
__all__ = [
    "OSVClient",
    "Vulnerability",
    "OSVError",
    # Constants for backward compatibility
    "OSV_API_URL",
    "OSV_BATCH_URL",
    "DEFAULT_TIMEOUT",
    "MAX_RETRIES",
    "RETRY_DELAY",
]
