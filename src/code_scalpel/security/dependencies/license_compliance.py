"""
License Compliance Scanner - Enterprise Tier Feature.

[20251226_FEATURE] v3.2.9 - Enterprise tier license compliance.

This module scans dependencies for license compliance issues:
- Identifies license types (MIT, GPL, Apache, proprietary, etc.)
- Flags license conflicts (GPL in proprietary software)
- Checks SPDX license compatibility
- Generates compliance reports for legal review
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class LicenseInfo:
    """License information for a dependency."""

    package_name: str
    package_version: str
    license_id: str  # SPDX identifier (e.g., "MIT", "Apache-2.0", "GPL-3.0")
    license_name: str  # Human-readable name
    is_osi_approved: bool  # Open Source Initiative approved
    is_copyleft: bool  # Requires derivative works to use same license
    allows_commercial_use: bool
    requires_attribution: bool
    compatibility_issues: list[str]  # Conflicts with other licenses in project


@dataclass
class ComplianceReport:
    """License compliance analysis report."""

    success: bool
    total_dependencies: int
    licenses_found: dict[str, int]  # License type -> count
    compliance_issues: list[str]  # Violations/conflicts
    high_risk_licenses: list[LicenseInfo]  # GPL, AGPL, etc.
    requires_attribution: list[LicenseInfo]  # Licenses needing attribution
    unknown_licenses: list[str]  # Packages with unknown licenses
    recommendations: list[str]  # Actions to take


class LicenseComplianceScanner:
    """
    Scans dependencies for license compliance.

    Enterprise tier feature that:
    - Identifies all dependency licenses
    - Checks SPDX compatibility
    - Flags GPL/AGPL in proprietary projects
    - Generates compliance reports
    """

    # Common OSI-approved licenses
    OSI_APPROVED = {
        "MIT",
        "Apache-2.0",
        "BSD-2-Clause",
        "BSD-3-Clause",
        "ISC",
        "MPL-2.0",
        "LGPL-2.1",
        "LGPL-3.0",
        "GPL-2.0",
        "GPL-3.0",
        "AGPL-3.0",
    }

    # Copyleft licenses
    COPYLEFT = {"GPL-2.0", "GPL-3.0", "AGPL-3.0", "LGPL-2.1", "LGPL-3.0", "MPL-2.0"}

    # Permissive licenses (safe for commercial use)
    PERMISSIVE = {"MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "ISC"}

    def __init__(self, project_root: str | Path, project_license: str = "proprietary"):
        """
        Initialize the license compliance scanner.

        Args:
            project_root: Root directory of the project
            project_license: License of your project (for compatibility checking)
        """
        self.project_root = Path(project_root)
        self.project_license = project_license.upper()

    def scan_licenses(self, dependencies: list[dict[str, Any]]) -> ComplianceReport:
        """
        Scan dependency licenses for compliance issues.

        Args:
            dependencies: List of dependency dicts with 'name' and 'version'

        Returns:
            ComplianceReport with findings and recommendations
        """
        license_infos: list[LicenseInfo] = []
        licenses_found: dict[str, int] = {}
        compliance_issues: list[str] = []
        high_risk: list[LicenseInfo] = []
        requires_attribution: list[LicenseInfo] = []
        unknown: list[str] = []

        for dep in dependencies:
            name = dep.get("name", "unknown")
            version = dep.get("version", "*")

            # Try to detect license
            license_id = self._detect_license(name, version)

            if not license_id or license_id == "UNKNOWN":
                unknown.append(f"{name}@{version}")
                continue

            # Build license info
            info = LicenseInfo(
                package_name=name,
                package_version=version,
                license_id=license_id,
                license_name=self._license_name(license_id),
                is_osi_approved=license_id in self.OSI_APPROVED,
                is_copyleft=license_id in self.COPYLEFT,
                allows_commercial_use=self._allows_commercial_use(license_id),
                requires_attribution=self._requires_attribution(license_id),
                compatibility_issues=[],
            )

            # Check for compatibility issues
            issues = self._check_compatibility(info)
            info.compatibility_issues = issues
            if issues:
                compliance_issues.extend([f"{name}: {issue}" for issue in issues])

            # Track high-risk licenses
            if info.is_copyleft and self.project_license == "PROPRIETARY":
                high_risk.append(info)

            # Track attribution requirements
            if info.requires_attribution:
                requires_attribution.append(info)

            license_infos.append(info)
            licenses_found[license_id] = licenses_found.get(license_id, 0) + 1

        # Generate recommendations
        recommendations = self._generate_recommendations(high_risk, unknown, compliance_issues)

        return ComplianceReport(
            success=len(compliance_issues) == 0,
            total_dependencies=len(dependencies),
            licenses_found=licenses_found,
            compliance_issues=compliance_issues,
            high_risk_licenses=high_risk,
            requires_attribution=requires_attribution,
            unknown_licenses=unknown,
            recommendations=recommendations,
        )

    def _detect_license(self, package_name: str, version: str) -> str:
        """
        Detect license for a package.

        In production, this would query npm registry, PyPI API, or Maven Central.
        For now, returns common licenses based on heuristics.
        """
        # Check for LICENSE file in project
        license_file = self.project_root / "LICENSE"
        if license_file.exists():
            content = license_file.read_text(encoding="utf-8")
            detected = self._parse_license_text(content)
            if detected:
                return detected

        # Common package patterns (simplified heuristics)
        # In production, query package registries
        common_licenses = {
            "express": "MIT",
            "react": "MIT",
            "django": "BSD-3-Clause",
            "flask": "BSD-3-Clause",
            "pytest": "MIT",
            "numpy": "BSD-3-Clause",
            "pandas": "BSD-3-Clause",
            "requests": "Apache-2.0",
            "urllib3": "MIT",
        }

        return common_licenses.get(package_name.lower(), "UNKNOWN")

    def _parse_license_text(self, text: str) -> str | None:
        """Parse license from LICENSE file text."""
        text_upper = text.upper()

        # MIT
        if "MIT LICENSE" in text_upper or "MIT" in text_upper[:100]:
            return "MIT"

        # Apache 2.0
        if "APACHE LICENSE" in text_upper and "VERSION 2.0" in text_upper:
            return "Apache-2.0"

        # BSD variants
        if "BSD" in text_upper:
            if "3-CLAUSE" in text_upper or "THREE CLAUSE" in text_upper:
                return "BSD-3-Clause"
            elif "2-CLAUSE" in text_upper or "TWO CLAUSE" in text_upper:
                return "BSD-2-Clause"
            else:
                return "BSD-3-Clause"  # Assume 3-clause

        # GPL variants
        if "GNU GENERAL PUBLIC LICENSE" in text_upper:
            if "VERSION 3" in text_upper:
                if "AFFERO" in text_upper:
                    return "AGPL-3.0"
                return "GPL-3.0"
            elif "VERSION 2" in text_upper:
                return "GPL-2.0"

        # LGPL
        if "GNU LESSER GENERAL PUBLIC LICENSE" in text_upper:
            if "VERSION 3" in text_upper:
                return "LGPL-3.0"
            elif "VERSION 2.1" in text_upper:
                return "LGPL-2.1"

        # ISC
        if "ISC LICENSE" in text_upper:
            return "ISC"

        # Mozilla
        if "MOZILLA PUBLIC LICENSE" in text_upper and "2.0" in text_upper:
            return "MPL-2.0"

        return None

    def _license_name(self, license_id: str) -> str:
        """Get human-readable license name."""
        names = {
            "MIT": "MIT License",
            "Apache-2.0": "Apache License 2.0",
            "BSD-2-Clause": "BSD 2-Clause License",
            "BSD-3-Clause": "BSD 3-Clause License",
            "GPL-2.0": "GNU General Public License v2.0",
            "GPL-3.0": "GNU General Public License v3.0",
            "AGPL-3.0": "GNU Affero General Public License v3.0",
            "LGPL-2.1": "GNU Lesser General Public License v2.1",
            "LGPL-3.0": "GNU Lesser General Public License v3.0",
            "MPL-2.0": "Mozilla Public License 2.0",
            "ISC": "ISC License",
        }
        return names.get(license_id, license_id)

    def _allows_commercial_use(self, license_id: str) -> bool:
        """Check if license allows commercial use."""
        # Most open source licenses allow commercial use
        # Only proprietary/source-available might not
        return license_id != "UNKNOWN"

    def _requires_attribution(self, license_id: str) -> bool:
        """Check if license requires attribution."""
        # Most licenses require attribution except truly public domain
        return license_id in self.OSI_APPROVED

    def _check_compatibility(self, info: LicenseInfo) -> list[str]:
        """Check for license compatibility issues."""
        issues = []

        # GPL incompatible with proprietary
        if info.is_copyleft and self.project_license == "PROPRIETARY":
            if info.license_id in ["GPL-2.0", "GPL-3.0", "AGPL-3.0"]:
                issues.append(
                    f"{info.license_id} is copyleft - cannot use in proprietary software without releasing source"
                )

        # AGPL incompatible with web services
        if info.license_id == "AGPL-3.0":
            issues.append("AGPL-3.0 requires source disclosure for network-accessible software")

        # GPL v2/v3 incompatibility
        if info.license_id == "GPL-2.0":
            # Check if project uses GPL-3.0
            issues.append("GPL-2.0 may be incompatible with GPL-3.0 dependencies")

        return issues

    def _generate_recommendations(
        self,
        high_risk: list[LicenseInfo],
        unknown: list[str],
        issues: list[str],
    ) -> list[str]:
        """Generate actionable recommendations."""
        recommendations = []

        if high_risk:
            recommendations.append(
                f"⚠️ {len(high_risk)} copyleft licenses found - review for proprietary project compatibility"
            )
            recommendations.append("Consider replacing GPL/AGPL dependencies with permissive alternatives")

        if unknown:
            recommendations.append(f"{len(unknown)} packages have unknown licenses - manual review required")

        if issues:
            recommendations.append("Review license compatibility issues with legal counsel")
        else:
            recommendations.append("✅ No license compliance issues detected")

        recommendations.append("Generate NOTICE file with required attributions")

        return recommendations
