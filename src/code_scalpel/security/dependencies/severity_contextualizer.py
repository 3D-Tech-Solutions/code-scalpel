"""
Severity Contextualizer - Pro Tier Feature.

[20251226_FEATURE] v3.2.9 - Pro tier severity contextualization.

This module provides context-aware severity assessment by:
- Adjusting severity based on actual usage patterns
- Considering deployment environment (dev/staging/prod)
- Analyzing exploit likelihood in your specific context
- Providing actionable remediation guidance
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ContextualizedSeverity:
    """Contextualized severity assessment for a vulnerability."""

    original_severity: str
    contextualized_severity: str
    severity_factors: dict[str, Any]  # Factors that influenced severity
    exploit_likelihood: str  # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    business_impact: str  # Description of potential business impact
    remediation_priority: int  # 1-5, where 1 is highest priority
    remediation_guidance: str  # Specific steps to fix
    timeline_recommendation: str  # When to fix ("immediate", "1 week", "1 month")


class SeverityContextualizer:
    """
    Contextualizes vulnerability severity based on actual usage.

    Pro tier feature that adjusts CVSS scores based on:
    - How the vulnerable code is used
    - Deployment environment
    - Attack surface exposure
    - Available mitigations
    """

    def __init__(self, project_root: str | Path, environment: str = "production"):
        """
        Initialize the severity contextualizer.

        Args:
            project_root: Root directory of the project
            environment: Deployment environment (development, staging, production)
        """
        self.project_root = Path(project_root)
        self.environment = environment.lower()

    def contextualize_severity(
        self,
        package_name: str,
        vulnerability: dict[str, Any],
        is_reachable: bool = True,
        is_exposed_to_internet: bool = True,
        has_sensitive_data: bool = False,
    ) -> ContextualizedSeverity:
        """
        Provide contextualized severity assessment.

        Args:
            package_name: Name of the vulnerable package
            vulnerability: Vulnerability data from OSV
            is_reachable: Whether vulnerable code is reachable
            is_exposed_to_internet: Whether app is internet-facing
            has_sensitive_data: Whether app handles sensitive data

        Returns:
            ContextualizedSeverity with adjusted severity and guidance
        """
        original_severity = vulnerability.get("severity", "UNKNOWN")
        if isinstance(original_severity, list):
            # Extract first severity if it's a list
            original_severity = original_severity[0].get("severity", "UNKNOWN") if original_severity else "UNKNOWN"

        # Build severity factors
        factors = {
            "reachable": is_reachable,
            "internet_exposed": is_exposed_to_internet,
            "sensitive_data": has_sensitive_data,
            "environment": self.environment,
            "vulnerability_type": self._classify_vulnerability_type(vulnerability),
        }

        # Calculate contextualized severity
        contextualized = self._adjust_severity(original_severity, factors)

        # Assess exploit likelihood
        exploit_likelihood = self._assess_exploit_likelihood(vulnerability, factors, is_reachable)

        # Determine business impact
        business_impact = self._assess_business_impact(vulnerability, factors, has_sensitive_data)

        # Calculate remediation priority
        remediation_priority = self._calculate_priority(contextualized, exploit_likelihood, business_impact)

        # Generate remediation guidance
        remediation_guidance = self._generate_remediation_guidance(package_name, vulnerability, contextualized)

        # Recommend timeline
        timeline = self._recommend_timeline(contextualized, exploit_likelihood, remediation_priority)

        return ContextualizedSeverity(
            original_severity=original_severity,
            contextualized_severity=contextualized,
            severity_factors=factors,
            exploit_likelihood=exploit_likelihood,
            business_impact=business_impact,
            remediation_priority=remediation_priority,
            remediation_guidance=remediation_guidance,
            timeline_recommendation=timeline,
        )

    def _classify_vulnerability_type(self, vulnerability: dict[str, Any]) -> str:
        """Classify the type of vulnerability."""
        summary = vulnerability.get("summary", "").lower()
        details = vulnerability.get("details", "").lower()
        combined = f"{summary} {details}"

        # Classification hierarchy
        if any(x in combined for x in ["rce", "remote code execution", "code exec"]):
            return "RCE"
        elif any(x in combined for x in ["injection", "sqli", "sql injection", "command"]):
            return "INJECTION"
        elif any(x in combined for x in ["xss", "cross-site scripting"]):
            return "XSS"
        elif any(x in combined for x in ["csrf", "cross-site request forgery"]):
            return "CSRF"
        elif any(x in combined for x in ["auth", "authentication", "authorization", "bypass"]):
            return "AUTH_BYPASS"
        elif any(x in combined for x in ["disclosure", "leak", "exposure"]):
            return "INFO_DISCLOSURE"
        elif any(x in combined for x in ["dos", "denial of service"]):
            return "DOS"
        elif any(x in combined for x in ["prototype pollution", "pollution"]):
            return "PROTOTYPE_POLLUTION"
        else:
            return "OTHER"

    def _adjust_severity(self, original_severity: str, factors: dict[str, Any]) -> str:
        """Adjust severity based on contextual factors."""
        severity_levels = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]

        try:
            current_idx = severity_levels.index(original_severity.upper())
        except ValueError:
            current_idx = 1  # Default to MEDIUM if unknown

        adjustments = 0

        # Reduce severity if not reachable
        if not factors["reachable"]:
            adjustments -= 2

        # Reduce severity in development environment
        if factors["environment"] == "development":
            adjustments -= 1
        elif factors["environment"] == "staging":
            adjustments -= 0.5

        # Increase severity if internet-facing
        if factors["internet_exposed"]:
            if factors["vulnerability_type"] in ["RCE", "INJECTION", "AUTH_BYPASS"]:
                adjustments += 1

        # Increase severity if handling sensitive data
        if factors["sensitive_data"]:
            if factors["vulnerability_type"] in [
                "INFO_DISCLOSURE",
                "AUTH_BYPASS",
                "INJECTION",
            ]:
                adjustments += 1

        # Apply adjustments
        new_idx = current_idx + int(round(adjustments))
        new_idx = max(0, min(new_idx, len(severity_levels) - 1))

        return severity_levels[new_idx]

    def _assess_exploit_likelihood(
        self, vulnerability: dict[str, Any], factors: dict[str, Any], is_reachable: bool
    ) -> str:
        """Assess how likely the vulnerability is to be exploited."""
        if not is_reachable:
            return "LOW"

        vuln_type = factors["vulnerability_type"]

        # High likelihood vulnerabilities
        if vuln_type in ["RCE", "AUTH_BYPASS"] and factors["internet_exposed"]:
            return "CRITICAL"

        # Medium-high likelihood
        if vuln_type in ["INJECTION", "XSS"] and factors["internet_exposed"]:
            return "HIGH"

        # Medium likelihood
        if vuln_type in ["CSRF", "INFO_DISCLOSURE"] and factors["internet_exposed"]:
            return "MEDIUM"

        # Low likelihood
        if not factors["internet_exposed"]:
            return "LOW"

        # Default
        return "MEDIUM"

    def _assess_business_impact(
        self,
        vulnerability: dict[str, Any],
        factors: dict[str, Any],
        has_sensitive_data: bool,
    ) -> str:
        """Assess potential business impact."""
        vuln_type = factors["vulnerability_type"]

        if vuln_type == "RCE":
            return "Complete system compromise, potential data breach, service disruption"

        elif vuln_type == "INJECTION":
            if has_sensitive_data:
                return "Database compromise, data theft, unauthorized access to sensitive information"
            else:
                return "Unauthorized data access, potential system manipulation"

        elif vuln_type == "AUTH_BYPASS":
            return "Unauthorized access to user accounts and protected resources"

        elif vuln_type == "XSS":
            return "Session hijacking, credential theft, malware distribution to users"

        elif vuln_type == "INFO_DISCLOSURE":
            if has_sensitive_data:
                return "Exposure of sensitive user data, compliance violations (GDPR, HIPAA)"
            else:
                return "Information leakage, potential reconnaissance for further attacks"

        elif vuln_type == "DOS":
            return "Service unavailability, revenue loss, reputation damage"

        else:
            return "Potential security compromise, impact depends on exploitation"

    def _calculate_priority(self, severity: str, exploit_likelihood: str, business_impact: str) -> int:
        """
        Calculate remediation priority (1-5, where 1 is highest).

        Uses matrix of severity + exploit likelihood.
        """
        severity_scores = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}
        likelihood_scores = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}

        sev_score = severity_scores.get(severity, 2)
        like_score = likelihood_scores.get(exploit_likelihood, 2)

        # Combined score: average weighted toward likelihood
        combined = (sev_score * 0.4) + (like_score * 0.6)

        # Map to priority (inverted - 1 is highest priority)
        if combined >= 3.5:
            return 1  # Immediate action
        elif combined >= 2.8:
            return 2  # This sprint
        elif combined >= 2.0:
            return 3  # Next sprint
        elif combined >= 1.5:
            return 4  # This quarter
        else:
            return 5  # Backlog

    def _generate_remediation_guidance(self, package_name: str, vulnerability: dict[str, Any], severity: str) -> str:
        """Generate specific remediation guidance."""
        guidance_parts = []

        # Extract fixed version if available
        fixed_version = None
        for affected in vulnerability.get("affected", []):
            for rng in affected.get("ranges", []):
                for event in rng.get("events", []):
                    if "fixed" in event:
                        fixed_version = event["fixed"]
                        break

        if fixed_version:
            guidance_parts.append(f"Update {package_name} to version {fixed_version} or later")
        else:
            guidance_parts.append(f"Check for latest version of {package_name}")

        # Add workarounds if high severity
        if severity in ["HIGH", "CRITICAL"]:
            vuln_id = vulnerability.get("id", "")
            guidance_parts.append(f"Review security advisory {vuln_id} for temporary workarounds")
            guidance_parts.append("Consider removing package if updates not available")

        # Add testing guidance
        guidance_parts.append("Test thoroughly after updating")

        return " | ".join(guidance_parts)

    def _recommend_timeline(self, severity: str, exploit_likelihood: str, priority: int) -> str:
        """Recommend when to fix the vulnerability."""
        if priority == 1:
            return "immediate" if severity == "CRITICAL" else "within 24 hours"
        elif priority == 2:
            return "within 1 week"
        elif priority == 3:
            return "within 1 month"
        elif priority == 4:
            return "within 3 months"
        else:
            return "as time permits"
