"""
False Positive Reducer - Pro Tier Feature.

[20251226_FEATURE] v3.2.9 - Pro tier false positive reduction.

This module reduces false positives in vulnerability scans by:
- Checking if vulnerable code paths are actually used
- Filtering dev-only dependencies in production
- Analyzing version compatibility more precisely
- Detecting mitigating factors (security wrappers, input validation)
"""

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class FalsePositiveAssessment:
    """Assessment of whether a vulnerability is a false positive."""

    is_false_positive: bool
    confidence: float  # 0.0-1.0
    reasons: list[str]  # Why it's considered false positive
    risk_level: str  # "DISMISSED", "LOW", "MEDIUM", "HIGH", "CRITICAL"
    recommendation: str  # What to do about it


class FalsePositiveReducer:
    """
    Reduces false positives in vulnerability scanning.

    Pro tier feature that analyzes vulnerabilities and filters out:
    - Dev-only dependencies (not in production)
    - Vulnerabilities in unused code paths
    - Already-mitigated vulnerabilities
    - Version range false positives
    """

    def __init__(self, project_root: str | Path):
        """
        Initialize the false positive reducer.

        Args:
            project_root: Root directory of the project
        """
        self.project_root = Path(project_root)

    def assess_vulnerability(
        self,
        package_name: str,
        package_version: str,
        vulnerability: dict[str, Any],
        is_dev_dependency: bool = False,
        is_reachable: bool = True,
    ) -> FalsePositiveAssessment:
        """
        Assess if a vulnerability is a false positive.

        Args:
            package_name: Name of the vulnerable package
            package_version: Version of the package
            vulnerability: Vulnerability data from OSV
            is_dev_dependency: Whether this is a dev dependency
            is_reachable: Whether the vulnerable code is reachable

        Returns:
            FalsePositiveAssessment with detailed analysis
        """
        reasons = []
        is_false_positive = False
        risk_level = vulnerability.get("severity", "UNKNOWN")

        # Check if dev dependency
        if is_dev_dependency:
            if self._is_dev_only_vulnerability(vulnerability):
                is_false_positive = True
                reasons.append("Dev-only dependency - not present in production environment")
                risk_level = "DISMISSED"

        # Check reachability
        if not is_reachable:
            is_false_positive = True
            reasons.append("Vulnerable code is not reachable from your application")
            risk_level = "LOW"  # Keep as LOW not DISMISSED (might become reachable)

        # Check version precision
        version_check = self._check_version_false_positive(package_version, vulnerability)
        if version_check:
            is_false_positive = True
            reasons.append(version_check)
            risk_level = "DISMISSED"

        # Check for mitigation factors
        mitigation = self._check_mitigation_factors(package_name, vulnerability)
        if mitigation:
            reasons.append(f"Mitigation detected: {mitigation}")
            risk_level = self._reduce_risk_level(risk_level)

        # Generate recommendation
        recommendation = self._generate_recommendation(is_false_positive, risk_level, reasons, package_name)

        # Determine confidence
        confidence = self._calculate_confidence(reasons, is_reachable)

        return FalsePositiveAssessment(
            is_false_positive=is_false_positive,
            confidence=confidence,
            reasons=reasons if reasons else ["No false positive indicators found"],
            risk_level=risk_level,
            recommendation=recommendation,
        )

    def _is_dev_only_vulnerability(self, vulnerability: dict[str, Any]) -> bool:
        """Check if vulnerability only affects development environment."""
        summary = vulnerability.get("summary", "").lower()
        details = vulnerability.get("details", "").lower()

        dev_indicators = [
            "test",
            "development",
            "debug",
            "devtool",
            "linter",
            "formatter",
            "build tool",
        ]

        combined = f"{summary} {details}"
        return any(indicator in combined for indicator in dev_indicators)

    def _check_version_false_positive(self, actual_version: str, vulnerability: dict[str, Any]) -> str | None:
        """
        Check if version is actually vulnerable.

        Returns explanation if false positive, None otherwise.
        """
        # Extract affected version ranges
        for affected in vulnerability.get("affected", []):
            for range_data in affected.get("ranges", []):
                if range_data.get("type") == "SEMVER":
                    # Check if version is in vulnerable range
                    events = range_data.get("events", [])
                    fixed = None

                    for event in events:
                        if "introduced" in event:
                            event["introduced"]
                        if "fixed" in event:
                            fixed = event["fixed"]

                    # If we have a fix and version is >= fix, not vulnerable
                    if fixed and self._version_gte(actual_version, fixed):
                        return f"Version {actual_version} >= fixed version {fixed}"

        return None

    def _version_gte(self, v1: str, v2: str) -> bool:
        """Compare versions (simple semantic version comparison)."""
        try:
            # Remove 'v' prefix if present
            v1 = v1.lstrip("v")
            v2 = v2.lstrip("v")

            # Split into parts and compare
            v1_parts = [int(x) for x in re.split(r"[.\-]", v1)[:3]]
            v2_parts = [int(x) for x in re.split(r"[.\-]", v2)[:3]]

            # Pad shorter version
            while len(v1_parts) < 3:
                v1_parts.append(0)
            while len(v2_parts) < 3:
                v2_parts.append(0)

            return v1_parts >= v2_parts
        except (ValueError, IndexError):
            # If parsing fails, be conservative
            return False

    def _check_mitigation_factors(self, package_name: str, vulnerability: dict[str, Any]) -> str | None:
        """
        Check for mitigation factors in the codebase.

        Returns description of mitigation if found.
        """
        # Check for common mitigation patterns
        vuln_type = self._get_vulnerability_type(vulnerability)

        if vuln_type == "injection":
            # Check for input validation wrapper
            if self._has_input_validation(package_name):
                return "Input validation wrapper detected"

        elif vuln_type == "xss":
            # Check for output escaping
            if self._has_output_escaping():
                return "Output escaping detected"

        elif vuln_type == "dos":
            # Check for rate limiting
            if self._has_rate_limiting():
                return "Rate limiting detected"

        return None

    def _get_vulnerability_type(self, vulnerability: dict[str, Any]) -> str:
        """Extract vulnerability type from data."""
        summary = vulnerability.get("summary", "").lower()
        details = vulnerability.get("details", "").lower()
        combined = f"{summary} {details}"

        if any(x in combined for x in ["injection", "sqli", "sql injection"]):
            return "injection"
        elif any(x in combined for x in ["xss", "cross-site scripting"]):
            return "xss"
        elif any(x in combined for x in ["dos", "denial of service"]):
            return "dos"
        elif any(x in combined for x in ["rce", "remote code execution"]):
            return "rce"
        return "unknown"

    def _has_input_validation(self, package_name: str) -> bool:
        """Check if input validation wrapper exists."""
        # Look for validation/sanitization imports
        try:
            for py_file in self.project_root.rglob("*.py"):
                if any(part in py_file.parts for part in (".venv", "venv")):
                    continue

                content = py_file.read_text(encoding="utf-8")
                # Look for validation libraries
                if any(lib in content for lib in ["validator", "sanitize", "escape", "bleach"]):
                    return True
        except Exception as e:
            logger.debug(f"Error checking input validation: {e}")

        return False

    def _has_output_escaping(self) -> bool:
        """Check if output escaping is used."""
        try:
            for py_file in self.project_root.rglob("*.py"):
                if any(part in py_file.parts for part in (".venv", "venv")):
                    continue

                content = py_file.read_text(encoding="utf-8")
                if any(pattern in content for pattern in ["html.escape", "escape(", "Markup("]):
                    return True
        except Exception:
            pass

        return False

    def _has_rate_limiting(self) -> bool:
        """Check if rate limiting is configured."""
        try:
            for py_file in self.project_root.rglob("*.py"):
                if any(part in py_file.parts for part in (".venv", "venv")):
                    continue

                content = py_file.read_text(encoding="utf-8")
                if any(pattern in content for pattern in ["ratelimit", "rate_limit", "throttle"]):
                    return True
        except Exception:
            pass

        return False

    def _reduce_risk_level(self, current_level: str) -> str:
        """Reduce risk level by one step."""
        levels = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "DISMISSED"]
        try:
            idx = levels.index(current_level)
            if idx < len(levels) - 1:
                return levels[idx + 1]
        except ValueError:
            pass
        return current_level

    def _calculate_confidence(self, reasons: list[str], is_reachable: bool) -> float:
        """Calculate confidence in false positive assessment."""
        if not reasons:
            return 0.5  # No evidence either way

        confidence = 0.5  # Base confidence

        # Boost confidence based on reasons
        for reason in reasons:
            if "not reachable" in reason.lower():
                confidence += 0.3
            elif "dev-only" in reason.lower():
                confidence += 0.4
            elif "fixed version" in reason.lower():
                confidence += 0.4
            elif "mitigation" in reason.lower():
                confidence += 0.2

        return min(confidence, 1.0)

    def _generate_recommendation(
        self, is_false_positive: bool, risk_level: str, reasons: list[str], package: str
    ) -> str:
        """Generate actionable recommendation."""
        if is_false_positive:
            if risk_level == "DISMISSED":
                return f"No action required - vulnerability does not affect your usage of {package}."
            elif risk_level == "LOW":
                return f"Low priority - monitor {package} for updates but no immediate action required."
            else:
                return f"Consider updating {package} during next maintenance window."
        else:
            if risk_level == "CRITICAL":
                return f"⚠️ URGENT: Update {package} immediately!"
            elif risk_level == "HIGH":
                return f"High priority: Update {package} as soon as possible."
            elif risk_level == "MEDIUM":
                return f"Medium priority: Schedule update for {package} in next sprint."
            else:
                return f"Update {package} when convenient."
