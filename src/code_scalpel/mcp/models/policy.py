"""Pydantic models for policy-related MCP tools."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from code_scalpel import __version__


class PathValidationResult(BaseModel):
    """Result of path validation."""

    success: bool = Field(description="Whether all paths were accessible")
    server_version: str = Field(default=__version__, description="Code Scalpel version")
    error: str | None = Field(default=None, description="Error message if failed")
    error_code: str | None = Field(default=None, description="Machine-readable error code (when failed)")

    # [20260110_FEATURE] Limits-aware metadata (present when max_paths truncation occurs)
    truncated: bool | None = Field(
        default=None,
        description="Whether input paths were truncated due to tier limits",
    )
    paths_received: int | None = Field(
        default=None,
        description="Number of input paths received before truncation",
    )
    paths_checked: int | None = Field(
        default=None,
        description="Number of paths actually validated",
    )
    max_paths_applied: int | None = Field(
        default=None,
        description="Applied max_paths limit when truncation occurred",
    )
    accessible: list[str] = Field(default_factory=list, description="Paths that were successfully resolved")
    inaccessible: list[str] = Field(default_factory=list, description="Paths that could not be resolved")
    suggestions: list[str] = Field(default_factory=list, description="Suggestions for resolving inaccessible paths")
    workspace_roots: list[str] = Field(default_factory=list, description="Detected workspace root directories")
    is_docker: bool = Field(default=False, description="Whether running in Docker container")

    # [20251225_FEATURE] v3.3.0 - Tier-specific outputs
    # Pro tier additions
    alias_resolutions: list[dict] = Field(default_factory=list, description="Resolved path aliases (tsconfig/webpack)")
    dynamic_imports: list[dict] = Field(
        default_factory=list,
        description="Detected dynamic import patterns in source files",
    )
    # Enterprise tier additions
    traversal_vulnerabilities: list[dict] = Field(
        default_factory=list,
        description="Directory traversal attempts detected with severity",
    )
    boundary_violations: list[dict] = Field(default_factory=list, description="Workspace boundary escape violations")
    security_score: float | None = Field(default=None, description="Enterprise: Overall security score (0.0-10.0)")


# [20250108_FEATURE] v2.5.0 Guardian - Policy verification models
class PolicyVerificationResult(BaseModel):
    """Result of cryptographic policy verification."""

    success: bool = Field(description="Whether all policy files verified successfully")
    manifest_valid: bool = Field(default=False, description="Whether manifest signature is valid")
    files_verified: int = Field(default=0, description="Number of files successfully verified")
    files_failed: list[str] = Field(default_factory=list, description="List of files that failed verification")
    error: str | None = Field(default=None, description="Error message if verification failed")
    error_code: str | None = Field(
        default=None,
        description=("Stable, machine-readable error code for failures (non-breaking additive field)"),
    )
    manifest_source: str | None = Field(default=None, description="Source of the policy manifest")
    policy_dir: str | None = Field(default=None, description="Policy directory that was verified")
    # [20251226_FEATURE] Tier-specific outputs
    tier: str = Field(default="community", description="Tier used for verification")
    signature_validated: bool = Field(default=False, description="Pro+: Whether HMAC signature was validated")
    tamper_detection_enabled: bool = Field(default=False, description="Pro+: Whether tamper detection is active")
    audit_log_entry: dict | None = Field(default=None, description="Enterprise: Audit log entry for this verification")


# [20251226_FEATURE] v3.4.0 - Code policy check MCP tool
class CodePolicyCheckResult(BaseModel):
    """Result model for code_policy_check tool."""

    success: bool = Field(description="Whether check passed (no critical violations)")
    files_checked: int = Field(description="Number of files analyzed")
    rules_applied: int = Field(description="Number of rules applied")
    summary: str = Field(description="Human-readable summary")
    tier: str = Field(default="community", description="Current tier level")

    # [20260111_FEATURE] Output metadata for transparency
    tier_applied: str = Field(
        default="community",
        description="Tier used for this analysis (community/pro/enterprise)",
    )
    files_limit_applied: int | None = Field(
        default=None,
        description="Max files limit applied (None=unlimited for Enterprise)",
    )
    rules_limit_applied: int | None = Field(
        default=None,
        description="Max rules limit applied (None=unlimited for Enterprise)",
    )

    # Core violations (all tiers)
    violations: list[dict[str, Any]] = Field(default_factory=list, description="List of policy violations found")

    # Pro tier fields
    best_practices_violations: list[dict[str, Any]] = Field(
        default_factory=list, description="Best practice violations (Pro tier)"
    )
    security_warnings: list[dict[str, Any]] = Field(default_factory=list, description="Security warnings (Pro tier)")
    custom_rule_results: dict[str, list[dict[str, Any]]] = Field(
        default_factory=dict, description="Custom rule matches (Pro tier)"
    )

    # Enterprise tier fields
    compliance_reports: dict[str, dict[str, Any]] = Field(
        default_factory=dict, description="Compliance audit reports (Enterprise tier)"
    )
    compliance_score: float = Field(default=0.0, description="Overall compliance score 0-100 (Enterprise tier)")
    certifications: list[dict[str, Any]] = Field(
        default_factory=list, description="Generated certifications (Enterprise tier)"
    )
    audit_trail: list[dict[str, Any]] = Field(default_factory=list, description="Audit log entries (Enterprise tier)")
    pdf_report: str | None = Field(default=None, description="Base64-encoded PDF report (Enterprise tier)")

    error: str | None = Field(default=None, description="Error message if failed")


# Ensure forward references are resolved for tool schemas.
PathValidationResult.model_rebuild()
PolicyVerificationResult.model_rebuild()
CodePolicyCheckResult.model_rebuild()


__all__ = [
    "PathValidationResult",
    "PolicyVerificationResult",
    "CodePolicyCheckResult",
]
