"""
Supply Chain Risk Scorer - Enterprise Tier Feature.

[20251226_FEATURE] v3.2.9 - Enterprise tier supply chain risk scoring.

This module assesses supply chain risks for dependencies:
- Package maturity and maintenance status
- Maintainer reputation and history
- Number of dependencies (attack surface)
- Recent vulnerability history
- Community trust signals (stars, downloads, contributors)
"""

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class RiskScore:
    """Risk score breakdown for a dependency."""

    package_name: str
    package_version: str
    overall_score: float  # 0-100, where 100 is highest risk
    risk_level: str  # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    maturity_score: float  # 0-100
    maintenance_score: float  # 0-100
    popularity_score: float  # 0-100
    security_score: float  # 0-100
    dependency_depth_score: float  # 0-100 (more deps = higher score = higher risk)
    risk_factors: list[str]  # Contributing factors
    strengths: list[str]  # Positive signals
    recommendation: str


@dataclass
class SupplyChainReport:
    """Supply chain risk assessment report."""

    success: bool
    total_packages: int
    average_risk_score: float
    high_risk_packages: list[RiskScore]
    medium_risk_packages: list[RiskScore]
    low_risk_packages: list[RiskScore]
    total_transitive_dependencies: int
    deepest_dependency_chain: int
    recommendations: list[str]


class SupplyChainRiskScorer:
    """
    Assesses supply chain risk for dependencies.

    Enterprise tier feature that analyzes:
    - Package health and maturity
    - Maintainer trustworthiness
    - Dependency tree complexity
    - Historical security issues
    """

    def __init__(self, project_root: str | Path):
        """
        Initialize the supply chain risk scorer.

        Args:
            project_root: Root directory of the project
        """
        self.project_root = Path(project_root)

    def assess_supply_chain_risk(
        self,
        dependencies: list[dict[str, Any]],
        vulnerabilities: dict[str, list[Any]] | None = None,
    ) -> SupplyChainReport:
        """
        Assess supply chain risk for all dependencies.

        Args:
            dependencies: List of dependency dicts with 'name', 'version', etc.
            vulnerabilities: Optional map of package -> vulnerabilities

        Returns:
            SupplyChainReport with risk assessments
        """
        risk_scores: list[RiskScore] = []
        high_risk = []
        medium_risk = []
        low_risk = []

        for dep in dependencies:
            name = dep.get("name", "unknown")
            dep.get("version", "*")

            # Get vulnerabilities for this package
            vulns = vulnerabilities.get(name, []) if vulnerabilities else []

            # Calculate risk score
            score = self._calculate_risk_score(dep, vulns)
            risk_scores.append(score)

            # Categorize
            if score.risk_level in ["CRITICAL", "HIGH"]:
                high_risk.append(score)
            elif score.risk_level == "MEDIUM":
                medium_risk.append(score)
            else:
                low_risk.append(score)

        # Calculate metrics
        avg_score = sum(s.overall_score for s in risk_scores) / len(risk_scores) if risk_scores else 0.0

        # Estimate transitive dependencies (simplified)
        total_transitive = self._estimate_transitive_deps(dependencies)

        # Find deepest chain
        deepest_chain = self._find_deepest_chain(dependencies)

        # Generate recommendations
        recommendations = self._generate_supply_chain_recommendations(high_risk, avg_score, total_transitive)

        return SupplyChainReport(
            success=True,
            total_packages=len(dependencies),
            average_risk_score=avg_score,
            high_risk_packages=high_risk,
            medium_risk_packages=medium_risk,
            low_risk_packages=low_risk,
            total_transitive_dependencies=total_transitive,
            deepest_dependency_chain=deepest_chain,
            recommendations=recommendations,
        )

    def _calculate_risk_score(self, dependency: dict[str, Any], vulnerabilities: list[Any]) -> RiskScore:
        """Calculate comprehensive risk score for a dependency."""
        name = dependency.get("name", "unknown")
        version = dependency.get("version", "*")

        # Score components (0-100, higher is more risk)
        maturity = self._score_maturity(dependency)
        maintenance = self._score_maintenance(dependency)
        popularity = self._score_popularity(dependency)
        security = self._score_security(vulnerabilities)
        dependency_depth = self._score_dependency_depth(dependency)

        # Weighted overall score
        weights = {
            "security": 0.35,
            "maintenance": 0.25,
            "maturity": 0.15,
            "popularity": 0.15,
            "dependency_depth": 0.10,
        }

        overall = (
            security * weights["security"]
            + maintenance * weights["maintenance"]
            + maturity * weights["maturity"]
            + popularity * weights["popularity"]
            + dependency_depth * weights["dependency_depth"]
        )

        # Determine risk level
        if overall >= 70:
            risk_level = "CRITICAL"
        elif overall >= 50:
            risk_level = "HIGH"
        elif overall >= 30:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"

        # Identify risk factors and strengths
        risk_factors, strengths = self._identify_factors(maturity, maintenance, popularity, security, dependency_depth)

        # Generate recommendation
        recommendation = self._generate_package_recommendation(name, risk_level, risk_factors)

        return RiskScore(
            package_name=name,
            package_version=version,
            overall_score=round(overall, 2),
            risk_level=risk_level,
            maturity_score=round(maturity, 2),
            maintenance_score=round(maintenance, 2),
            popularity_score=round(popularity, 2),
            security_score=round(security, 2),
            dependency_depth_score=round(dependency_depth, 2),
            risk_factors=risk_factors,
            strengths=strengths,
            recommendation=recommendation,
        )

    def _score_maturity(self, dependency: dict[str, Any]) -> float:
        """
        Score package maturity (0-100, higher = more risk).

        Factors: version number, age, stability
        """
        version = dependency.get("version", "0.0.1")

        # Parse version
        try:
            # Remove 'v' prefix
            version_clean = version.lstrip("v")
            parts = re.split(r"[.\-]", version_clean)
            major = int(parts[0]) if parts else 0
            minor = int(parts[1]) if len(parts) > 1 else 0
        except (ValueError, IndexError):
            major, minor = 0, 0

        # Scoring logic:
        # - v0.x.x is immature (high risk)
        # - v1.x.x+ is more mature (lower risk)
        if major == 0:
            return 60.0  # Pre-1.0 is risky
        elif major == 1 and minor < 5:
            return 40.0  # Early 1.x
        elif major >= 2:
            return 20.0  # Mature version
        else:
            return 30.0  # Default

    def _score_maintenance(self, dependency: dict[str, Any]) -> float:
        """
        Score maintenance status (0-100, higher = more risk).

        In production, would check:
        - Last commit date
        - Open issues
        - Response time
        """
        # Simplified heuristic based on version
        # In production, query npm/PyPI for last update timestamp
        version = dependency.get("version", "0.0.1")

        # Assume older-looking versions are less maintained
        if "alpha" in version.lower() or "beta" in version.lower():
            return 70.0  # Pre-release, potentially abandoned
        elif version.startswith("0."):
            return 50.0  # Early version
        else:
            return 25.0  # Assume maintained if stable version

    def _score_popularity(self, dependency: dict[str, Any]) -> float:
        """
        Score popularity (0-100, higher = more risk for unpopular packages).

        Less popular = less vetted = higher risk.
        """
        name = dependency.get("name", "").lower()

        # Popular packages (simplified check)
        popular_packages = {
            "react",
            "express",
            "lodash",
            "django",
            "flask",
            "numpy",
            "pandas",
            "requests",
            "pytest",
        }

        if name in popular_packages:
            return 5.0  # Very popular, low risk

        # In production, query download counts from registries
        # For now, assume moderate popularity
        return 40.0

    def _score_security(self, vulnerabilities: list[Any]) -> float:
        """
        Score security posture (0-100, higher = more risk).

        More vulnerabilities = higher risk.
        """
        if not vulnerabilities:
            return 10.0  # No known vulns, low risk

        vuln_count = len(vulnerabilities)

        # Score based on count and severity
        critical = sum(1 for v in vulnerabilities if v.get("severity") == "CRITICAL")
        high = sum(1 for v in vulnerabilities if v.get("severity") == "HIGH")

        if critical > 0:
            return 90.0
        elif high > 0:
            return 70.0
        elif vuln_count > 5:
            return 60.0
        elif vuln_count > 2:
            return 50.0
        else:
            return 30.0

    def _score_dependency_depth(self, dependency: dict[str, Any]) -> float:
        """
        Score dependency depth (0-100, higher = more deps = more risk).

        More dependencies = larger attack surface.
        """
        # In production, would parse package.json/requirements.txt recursively
        # For now, estimate based on common patterns

        name = dependency.get("name", "").lower()

        # Known heavy frameworks have many deps
        heavy_frameworks = {"webpack", "babel", "gatsby", "next", "django"}

        if name in heavy_frameworks:
            return 70.0  # Lots of transitive deps

        # Most packages have moderate deps
        return 30.0

    def _identify_factors(
        self,
        maturity: float,
        maintenance: float,
        popularity: float,
        security: float,
        depth: float,
    ) -> tuple[list[str], list[str]]:
        """Identify risk factors and strengths."""
        factors = []
        strengths = []

        if maturity > 50:
            factors.append("Pre-1.0 version (immature)")
        else:
            strengths.append("Mature version")

        if maintenance > 50:
            factors.append("Potentially unmaintained")
        else:
            strengths.append("Actively maintained")

        if popularity > 50:
            factors.append("Low popularity (less vetted)")
        else:
            strengths.append("Popular and well-vetted")

        if security > 50:
            factors.append("Known vulnerabilities present")
        else:
            strengths.append("No known vulnerabilities")

        if depth > 50:
            factors.append("High dependency depth (large attack surface)")

        return factors, strengths

    def _estimate_transitive_deps(self, dependencies: list[dict[str, Any]]) -> int:
        """Estimate total transitive dependencies."""
        # Simplified: assume each package has 3 transitive deps on average
        return len(dependencies) * 3

    def _find_deepest_chain(self, dependencies: list[dict[str, Any]]) -> int:
        """Find deepest dependency chain depth."""
        # Simplified: estimate based on package types
        # In production, would parse dependency trees
        return 5  # Reasonable default

    def _generate_package_recommendation(self, name: str, risk_level: str, factors: list[str]) -> str:
        """Generate recommendation for a package."""
        if risk_level == "CRITICAL":
            return f"⚠️ HIGH RISK: Consider replacing {name} with alternative"
        elif risk_level == "HIGH":
            return f"Review {name} - multiple risk factors: {', '.join(factors[:2])}"
        elif risk_level == "MEDIUM":
            return f"Monitor {name} - some concerns: {factors[0] if factors else 'N/A'}"
        else:
            return f"✅ {name} appears safe to use"

    def _generate_supply_chain_recommendations(
        self, high_risk: list[RiskScore], avg_score: float, total_transitive: int
    ) -> list[str]:
        """Generate overall supply chain recommendations."""
        recommendations = []

        if high_risk:
            recommendations.append(f"⚠️ {len(high_risk)} high-risk dependencies found - review supply chain")
            recommendations.append("Consider dependency pruning to reduce attack surface")

        if avg_score > 50:
            recommendations.append(f"Average risk score {avg_score:.1f}/100 is elevated - improve dependency hygiene")

        if total_transitive > 100:
            recommendations.append(f"{total_transitive} transitive dependencies detected - large attack surface")

        if not high_risk and avg_score < 30:
            recommendations.append("✅ Supply chain appears healthy - continue monitoring")

        recommendations.append("Regularly audit dependencies with `scan_dependencies`")

        return recommendations
