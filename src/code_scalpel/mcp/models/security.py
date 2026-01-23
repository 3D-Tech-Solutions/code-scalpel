"""Security-related Pydantic models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from code_scalpel import __version__
from code_scalpel.mcp.models.core import VulnerabilityInfo


class SecurityResult(BaseModel):
    """Result of security analysis."""

    success: bool = Field(description="Whether analysis succeeded")
    server_version: str = Field(default=__version__, description="Code Scalpel version")
    has_vulnerabilities: bool = Field(description="Whether vulnerabilities were found")
    vulnerability_count: int = Field(description="Number of vulnerabilities")
    risk_level: str = Field(description="Overall risk level")
    vulnerabilities: list[VulnerabilityInfo] = Field(default_factory=list, description="List of vulnerabilities")
    taint_sources: list[str] = Field(default_factory=list, description="Identified taint sources")
    # [20251226_FEATURE] Tier-aware optional security outputs for Pro/Enterprise
    sanitizer_paths: list[str] | None = Field(default=None, description="Detected sanitizer usages (Pro/Enterprise)")
    confidence_scores: dict[str, float] | None = Field(
        default=None, description="Heuristic confidence scores per finding"
    )
    false_positive_analysis: dict[str, Any] | None = Field(
        default=None, description="False-positive reduction metadata"
    )
    # [20260118_FEATURE] v1.0 - Pro tier remediation suggestions
    remediation_suggestions: list[str] | None = Field(
        default=None,
        description="Remediation suggestions per vulnerability (Pro/Enterprise)",
    )
    policy_violations: list[dict[str, Any]] | None = Field(
        default=None, description="Custom policy violations (Enterprise)"
    )
    compliance_mappings: dict[str, list[str]] | None = Field(
        default=None, description="Compliance framework mappings (Enterprise)"
    )
    custom_rule_results: list[dict[str, Any]] | None = Field(
        default=None, description="Custom rule matches (Enterprise)"
    )
    # [20251230_FEATURE] v1.0 roadmap Enterprise tier fields
    priority_ordered_findings: list[dict[str, Any]] | None = Field(
        default=None, description="Findings sorted by priority (Enterprise)"
    )
    reachability_analysis: dict[str, Any] | None = Field(
        default=None, description="Vulnerability reachability analysis (Enterprise)"
    )
    false_positive_tuning: dict[str, Any] | None = Field(
        default=None, description="False positive tuning results (Enterprise)"
    )
    error: str | None = Field(default=None, description="Error message if failed")


class TypeEvaporationResultModel(BaseModel):
    """Result of type evaporation analysis.

    [20251226_FEATURE] v3.3.0 - Added Pro/Enterprise tier fields for full capabilities.
    """

    success: bool = Field(description="Whether analysis succeeded")
    server_version: str = Field(default=__version__, description="Code Scalpel version")
    frontend_vulnerabilities: int = Field(default=0, description="Number of frontend vulnerabilities")
    backend_vulnerabilities: int = Field(default=0, description="Number of backend vulnerabilities")
    cross_file_issues: int = Field(default=0, description="Number of cross-file issues")
    matched_endpoints: list[str] = Field(default_factory=list, description="Correlated API endpoints")
    vulnerabilities: list[VulnerabilityInfo] = Field(default_factory=list, description="All vulnerabilities")
    summary: str = Field(default="", description="Analysis summary")
    error: str | None = Field(default=None, description="Error message if failed")

    # Pro tier fields
    implicit_any_count: int = Field(default=0, description="[Pro] Count of implicit any detections")
    network_boundaries: list[dict[str, Any]] = Field(
        default_factory=list, description="[Pro] Detected network call boundaries"
    )
    boundary_violations: list[dict[str, Any]] = Field(
        default_factory=list, description="[Pro] Type violations at boundaries"
    )
    library_boundaries: list[dict[str, Any]] = Field(
        default_factory=list, description="[Pro] Library call type boundaries"
    )
    json_parse_locations: list[dict[str, Any]] = Field(
        default_factory=list, description="[Pro] JSON.parse() without validation"
    )

    # Enterprise tier fields
    generated_schemas: list[dict[str, Any]] = Field(
        default_factory=list, description="[Enterprise] Generated Zod schemas"
    )
    validation_code: str | None = Field(default=None, description="[Enterprise] Generated validation code")
    schema_coverage: float | None = Field(
        default=None, description="[Enterprise] Coverage ratio of validated endpoints"
    )
    pydantic_models: list[dict[str, Any]] = Field(
        default_factory=list, description="[Enterprise] Generated Pydantic models"
    )
    api_contract: dict[str, Any] | None = Field(
        default=None, description="[Enterprise] API contract validation results"
    )
    # [20251231_FEATURE] v1.0 - Added missing Enterprise fields
    remediation_suggestions: list[dict[str, Any]] = Field(
        default_factory=list,
        description="[Enterprise] Automated remediation suggestions",
    )
    custom_rule_violations: list[dict[str, Any]] = Field(
        default_factory=list, description="[Enterprise] Custom type rule violations"
    )
    compliance_report: dict[str, Any] | None = Field(
        default=None, description="[Enterprise] Type compliance validation report"
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="Non-fatal warnings (e.g. tier limits applied)",
    )


class DependencyVulnerability(BaseModel):
    """
    Represents a vulnerability detected in a dependency.

    [20251229_FEATURE] v3.3.1 - Standardized vulnerability model.
    [20251231_FEATURE] v3.3.1 - Parity with legacy server outputs.
    """

    id: str = Field(description="OSV vulnerability ID")
    summary: str | None = Field(default=None, description="Short summary of the issue")
    details: str | None = Field(default=None, description="Detailed description")
    severity: str = Field(default="UNKNOWN", description="Severity (CRITICAL, HIGH, MEDIUM, LOW, UNKNOWN)")
    affected_versions: list[str] = Field(default_factory=list, description="Versions affected by this vulnerability")
    fixed_versions: list[str] = Field(default_factory=list, description="Versions that fix this vulnerability")
    references: list[str] = Field(default_factory=list, description="URLs with more information")
    aliases: list[str] = Field(default_factory=list, description="Other IDs (e.g. CVE-2023-1234)")
    # Legacy/compat fields used by helpers
    package: str | None = Field(default=None, description="Package name")
    vulnerable_version: str | None = Field(default=None, description="Version found vulnerable in the project")
    fixed_version: str | None = Field(default=None, description="First version that fixes this vulnerability")


class DependencyInfo(BaseModel):
    """
    Represents a scanned dependency with vulnerability info.

    [20251229_FEATURE] v3.3.1 - Tracking dependency-level risks.
    """

    name: str = Field(description="Package name")
    version: str = Field(description="Package version")
    ecosystem: str = Field(description="Ecosystem (PyPI, npm, Maven)")
    file_path: str = Field(description="File defining this dependency")
    is_dev: bool = Field(default=False, description="Whether this is a dev dependency")
    vulnerabilities: list[DependencyVulnerability] = Field(
        default_factory=list, description="Vulnerabilities affecting this dependency"
    )
    # [20251231_FEATURE] v3.3.1 - Pro tier enrichments
    risk_score: float | None = Field(default=None, description="Calculated risk score (0.0-10.0)")
    is_reachable: bool | None = Field(default=None, description="Whether dependency is imported in code (Pro tier)")
    is_imported: bool | None = Field(default=None, description="Whether dependency is imported in the codebase")
    transitive_depth: int | None = Field(default=None, description="Dependency depth (0=direct, >0=transitive)")
    # [20251231_FEATURE] v3.3.1 - Enterprise enrichments
    license: str | None = Field(default=None, description="License identifier (Enterprise tier)")
    license_compliant: bool | None = Field(default=None, description="Whether license is compliant with policy")
    typosquatting_risk: bool | None = Field(default=None, description="Whether typosquatting risk was detected")
    supply_chain_risk_score: float | None = Field(default=None, description="Supply chain risk score (0.0-1.0)")
    supply_chain_risk_factors: list[str] | None = Field(
        default=None, description="Factors contributing to supply chain risk"
    )
    compliance_status: str | None = Field(default=None, description="Compliance status (compliant, warning, violation)")
    remediation_suggestion: str | None = Field(default=None, description="Suggested fix (e.g. 'upgrade to 2.1.0')")


class DependencyScanResult(BaseModel):
    """
    Comprehensive result of dependency scan with per-dependency grouping.

    [20251220_FEATURE] v3.0.5 - Initial structure.
    [20251229_FEATURE] v3.3.1 - Added Pro/Enterprise tier fields.
    """

    scanned_files: list[str] = Field(default_factory=list, description="List of dependency files scanned")
    total_dependencies: int = Field(default=0, description="Total number of dependencies found")
    vulnerable_count: int = Field(default=0, description="Number of dependencies with vulnerabilities")
    total_vulnerabilities: int = Field(default=0, description="Total number of vulnerabilities found")
    severity_summary: dict[str, int] = Field(default_factory=dict, description="Count of vulnerabilities by severity")
    dependencies: list[DependencyInfo] = Field(
        default_factory=list,
        description="All scanned dependencies with their vulnerabilities",
    )
    # [20251231_FEATURE] v3.3.1 - Enterprise compliance reporting
    compliance_report: dict[str, Any] | None = Field(
        default=None,
        description="Compliance report for SOC2/ISO standards (Enterprise tier)",
    )
    policy_violations: list[dict[str, Any]] | None = Field(
        default=None, description="Policy violations detected (Enterprise tier)"
    )
    errors: list[str] = Field(
        default_factory=list,
        description="Non-fatal errors/warnings encountered during scan (e.g. tier truncation warnings)",
    )
    # Legacy/compat fields for helper parity
    success: bool = Field(default=True, description="Whether the scan completed successfully")
    error: str | None = Field(default=None, description="Error message if failed")


class VulnerabilityFindingModel(BaseModel):
    """A vulnerability found in a dependency."""

    id: str = Field(description="OSV vulnerability ID (e.g., GHSA-xxxx-xxxx-xxxx)")
    cve_id: str | None = Field(default=None, description="CVE ID if available")
    severity: str = Field(default="UNKNOWN", description="Severity: CRITICAL, HIGH, MEDIUM, LOW, UNKNOWN")
    package_name: str = Field(description="Name of the vulnerable package")
    package_version: str = Field(description="Version of the vulnerable package")
    ecosystem: str = Field(description="Package ecosystem (npm, Maven, PyPI)")
    summary: str = Field(default="", description="Brief description of the vulnerability")
    fixed_versions: list[str] = Field(default_factory=list, description="Versions that fix this vulnerability")
    source_file: str = Field(default="", description="Dependency file where package was found")


class DependencyScanResultModel(BaseModel):
    """Result of a dependency vulnerability scan."""

    success: bool = Field(description="Whether the scan completed successfully")
    server_version: str = Field(default=__version__, description="Code Scalpel version")
    error: str | None = Field(default=None, description="Error message if failed")
    dependencies_scanned: int = Field(default=0, description="Number of dependencies checked")
    vulnerabilities_found: int = Field(default=0, description="Number of vulnerabilities found")
    critical_count: int = Field(default=0, description="Number of CRITICAL severity")
    high_count: int = Field(default=0, description="Number of HIGH severity")
    medium_count: int = Field(default=0, description="Number of MEDIUM severity")
    low_count: int = Field(default=0, description="Number of LOW severity")
    findings: list[VulnerabilityFindingModel] = Field(default_factory=list, description="Detailed findings")
    errors: list[str] = Field(default_factory=list, description="Errors encountered during scan")
    summary: str = Field(default="", description="Human-readable summary")


# Ensure forward references are resolved for tool schemas.
SecurityResult.model_rebuild()
TypeEvaporationResultModel.model_rebuild()
DependencyVulnerability.model_rebuild()
DependencyInfo.model_rebuild()
DependencyScanResult.model_rebuild()
VulnerabilityFindingModel.model_rebuild()
DependencyScanResultModel.model_rebuild()
