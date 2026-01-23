"""
Typosquatting Detector - Enterprise Tier Feature.

[20251226_FEATURE] v3.2.9 - Enterprise tier typosquatting detection.

This module detects potential typosquatting attacks where malicious packages
have names similar to popular packages:
- Levenshtein distance checking
- Visual similarity detection (l vs I, 0 vs O)
- Common typo patterns (missing/extra characters)
- Comparison against known-good package list
"""

import logging
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class TyposquattingAlert:
    """Alert for potential typosquatting."""

    package_name: str
    package_version: str
    suspected_target: str  # The legitimate package name
    similarity_score: float  # 0.0-1.0
    typo_type: str  # "character_swap", "missing_char", "extra_char", "visual_similarity"
    risk_level: str  # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    evidence: str  # Why this is suspicious
    recommendation: str  # What to do


@dataclass
class TyposquattingReport:
    """Report of typosquatting scan results."""

    success: bool
    total_checked: int
    alerts_found: int
    high_risk_count: int
    medium_risk_count: int
    low_risk_count: int
    alerts: list[TyposquattingAlert]
    recommendations: list[str]


class TyposquattingDetector:
    """
    Detects typosquatting attacks in dependencies.

    Enterprise tier feature that compares dependency names against:
    - Popular package registries (npm, PyPI, Maven)
    - Known typosquatting patterns
    - Visual similarity attacks
    """

    # Top 100 most popular packages (subset for demonstration)
    POPULAR_PACKAGES = {
        # Python
        "numpy",
        "pandas",
        "requests",
        "django",
        "flask",
        "pytest",
        "scikit-learn",
        "tensorflow",
        "torch",
        "matplotlib",
        "scipy",
        "pillow",
        "sqlalchemy",
        "boto3",
        "pyyaml",
        # JavaScript/TypeScript
        "react",
        "express",
        "lodash",
        "webpack",
        "typescript",
        "eslint",
        "jest",
        "axios",
        "moment",
        "jquery",
        "vue",
        "angular",
        "next",
        "babel",
        "prettier",
    }

    # Visual similarity pairs
    VISUAL_CONFUSABLES = {
        "l": ["1", "i", "I"],
        "0": ["O", "o"],
        "1": ["l", "i", "I"],
        "i": ["l", "1"],
        "I": ["l", "1"],
        "O": ["0"],
        "o": ["0"],
        "rn": ["m"],
        "vv": ["w"],
    }

    def __init__(self):
        """Initialize the typosquatting detector."""
        pass

    def scan_for_typosquatting(self, dependencies: list[dict[str, Any]]) -> TyposquattingReport:
        """
        Scan dependencies for typosquatting attacks.

        Args:
            dependencies: List of dependency dicts with 'name' and 'version'

        Returns:
            TyposquattingReport with alerts and recommendations
        """
        alerts: list[TyposquattingAlert] = []
        high_risk = 0
        medium_risk = 0
        low_risk = 0

        for dep in dependencies:
            name = dep.get("name", "").lower()
            version = dep.get("version", "*")

            # Check against popular packages
            alert = self._check_typosquatting(name, version)
            if alert:
                alerts.append(alert)

                if alert.risk_level == "HIGH" or alert.risk_level == "CRITICAL":
                    high_risk += 1
                elif alert.risk_level == "MEDIUM":
                    medium_risk += 1
                else:
                    low_risk += 1

        # Generate recommendations
        recommendations = self._generate_recommendations(alerts)

        return TyposquattingReport(
            success=True,
            total_checked=len(dependencies),
            alerts_found=len(alerts),
            high_risk_count=high_risk,
            medium_risk_count=medium_risk,
            low_risk_count=low_risk,
            alerts=alerts,
            recommendations=recommendations,
        )

    def _check_typosquatting(self, package_name: str, version: str) -> TyposquattingAlert | None:
        """
        Check if a package name is potential typosquatting.

        Returns alert if suspicious, None otherwise.
        """
        # Check against popular packages
        for popular in self.POPULAR_PACKAGES:
            similarity = self._calculate_similarity(package_name, popular)

            if 0.7 < similarity < 1.0:  # Similar but not exact match
                # Analyze the type of similarity
                typo_type, evidence = self._analyze_difference(package_name, popular)

                # Calculate risk level
                risk_level = self._assess_risk(similarity, typo_type, package_name, popular)

                if risk_level != "NONE":
                    return TyposquattingAlert(
                        package_name=package_name,
                        package_version=version,
                        suspected_target=popular,
                        similarity_score=similarity,
                        typo_type=typo_type,
                        risk_level=risk_level,
                        evidence=evidence,
                        recommendation=self._generate_alert_recommendation(package_name, popular, risk_level),
                    )

        return None

    def _calculate_similarity(self, name1: str, name2: str) -> float:
        """Calculate similarity score between two package names."""
        # Use SequenceMatcher for basic similarity
        return SequenceMatcher(None, name1, name2).ratio()

    def _analyze_difference(self, suspicious: str, legitimate: str) -> tuple[str, str]:
        """
        Analyze the type of difference between package names.

        Returns (typo_type, evidence).
        """
        # Check for visual similarity
        if self._is_visual_similarity(suspicious, legitimate):
            confusables = self._find_confusables(suspicious, legitimate)
            return (
                "visual_similarity",
                f"Visually similar characters: {', '.join(confusables)}",
            )

        # Check for single character difference
        if len(suspicious) == len(legitimate):
            diff_count = sum(c1 != c2 for c1, c2 in zip(suspicious, legitimate, strict=False))
            if diff_count == 1:
                return (
                    "character_swap",
                    f"Single character differs from '{legitimate}'",
                )

        # Check for missing character
        if len(suspicious) == len(legitimate) - 1:
            return (
                "missing_char",
                f"One character missing from '{legitimate}'",
            )

        # Check for extra character
        if len(suspicious) == len(legitimate) + 1:
            return (
                "extra_char",
                f"One extra character compared to '{legitimate}'",
            )

        # Check for transposition (swapped adjacent chars)
        if self._is_transposition(suspicious, legitimate):
            return (
                "transposition",
                f"Adjacent characters swapped from '{legitimate}'",
            )

        return ("other", f"Similar to popular package '{legitimate}'")

    def _is_visual_similarity(self, name1: str, name2: str) -> bool:
        """Check if names are visually similar (confusable characters)."""
        if len(name1) != len(name2):
            return False

        for _i, (c1, c2) in enumerate(zip(name1, name2, strict=False)):
            if c1 != c2:
                # Check if they're confusable
                if c1 in self.VISUAL_CONFUSABLES:
                    if c2 in self.VISUAL_CONFUSABLES[c1]:
                        return True
                if c2 in self.VISUAL_CONFUSABLES:
                    if c1 in self.VISUAL_CONFUSABLES[c2]:
                        return True

        return False

    def _find_confusables(self, name1: str, name2: str) -> list[str]:
        """Find confusable character pairs."""
        confusables = []
        for _i, (c1, c2) in enumerate(zip(name1, name2, strict=False)):
            if c1 != c2:
                confusables.append(f"'{c1}' vs '{c2}'")
        return confusables

    def _is_transposition(self, name1: str, name2: str) -> bool:
        """Check if one name is a transposition of the other."""
        if len(name1) != len(name2):
            return False

        diff_positions = [i for i, (c1, c2) in enumerate(zip(name1, name2, strict=False)) if c1 != c2]

        # Transposition means exactly 2 adjacent positions differ
        if len(diff_positions) == 2:
            i, j = diff_positions
            if j == i + 1:  # Adjacent
                # Check if they're swapped
                return name1[i] == name2[j] and name1[j] == name2[i]

        return False

    def _assess_risk(self, similarity: float, typo_type: str, suspicious: str, legitimate: str) -> str:
        """Assess risk level of typosquatting."""
        # High similarity + visual confusables = high risk
        if similarity > 0.9 and typo_type == "visual_similarity":
            return "CRITICAL"

        # Single character swap on popular package
        if similarity > 0.85 and typo_type in [
            "character_swap",
            "missing_char",
            "transposition",
        ]:
            return "HIGH"

        # Moderate similarity
        if similarity > 0.8:
            return "MEDIUM"

        # Lower similarity but still suspicious
        if similarity > 0.7:
            return "LOW"

        return "NONE"

    def _generate_alert_recommendation(self, suspicious: str, legitimate: str, risk_level: str) -> str:
        """Generate recommendation for typosquatting alert."""
        if risk_level in ["CRITICAL", "HIGH"]:
            return (
                f"⚠️ URGENT: Verify '{suspicious}' is intentional. "
                f"Did you mean '{legitimate}'? Remove if typosquatting attack."
            )
        elif risk_level == "MEDIUM":
            return (
                f"Review '{suspicious}' - similar to popular package '{legitimate}'. "
                f"Verify it's the correct dependency."
            )
        else:
            return f"Double-check '{suspicious}' - possibly confused with '{legitimate}'."

    def _generate_recommendations(self, alerts: list[TyposquattingAlert]) -> list[str]:
        """Generate overall recommendations."""
        if not alerts:
            return ["✅ No typosquatting alerts detected"]

        recommendations = []

        high_risk = sum(1 for a in alerts if a.risk_level in ["CRITICAL", "HIGH"])
        if high_risk > 0:
            recommendations.append(f"⚠️ {high_risk} high-risk typosquatting alerts - review immediately")

        recommendations.append("Verify all flagged packages are intentional dependencies")
        recommendations.append("Check package registry (npm, PyPI) for legitimacy")
        recommendations.append("Review package download counts and maintainer history")

        return recommendations
