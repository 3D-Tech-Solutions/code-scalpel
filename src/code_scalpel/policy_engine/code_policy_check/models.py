"""
Code Policy Check - Data Models.

[20251226_FEATURE] v3.4.0 - Models for code policy check results and violations.

This module defines all data models used by the code_policy_check tool:
- Violation and warning models
- Result models for each tier
- Compliance and certification models
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, TypedDict


class PolicyViolationDict(TypedDict):
    """Policy violation dictionary for JSON serialization."""

    file: str
    line: int
    column: int
    rule_id: str
    message: str
    severity: str
    category: str
    code_snippet: str | None
    suggestion: str | None


class BestPracticeViolationDict(TypedDict):
    """Best practice violation dictionary for JSON serialization."""

    file: str
    line: int
    pattern_id: str
    description: str
    severity: str
    category: str
    recommendation: str | None
    documentation_url: str | None


class ViolationSeverity(str, Enum):
    """Severity levels for policy violations."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class PolicyViolation:
    """
    Represents a single policy violation found in code.

    [20251226_FEATURE] Core violation model for all tiers.
    """

    file: str
    line: int
    column: int
    rule_id: str
    message: str
    severity: ViolationSeverity = ViolationSeverity.WARNING
    category: str = "style"  # style, pattern, security, compliance
    code_snippet: str | None = None
    suggestion: str | None = None

    def to_dict(self) -> PolicyViolationDict:
        """Convert to dictionary for serialization."""
        return {
            "file": self.file,
            "line": self.line,
            "column": self.column,
            "rule_id": self.rule_id,
            "message": self.message,
            "severity": self.severity.value,
            "category": self.category,
            "code_snippet": self.code_snippet,
            "suggestion": self.suggestion,
        }


@dataclass
class BestPracticeViolation:
    """
    Represents a best practice violation (Pro tier).

    [20251226_FEATURE] Pro tier model for best practice analysis.
    """

    file: str
    line: int
    pattern_id: str
    description: str
    severity: ViolationSeverity = ViolationSeverity.WARNING
    category: str = "best_practice"  # async, error_handling, resource_mgmt, typing
    recommendation: str | None = None
    documentation_url: str | None = None

    def to_dict(self) -> BestPracticeViolationDict:
        """Convert to dictionary for serialization."""
        return {
            "file": self.file,
            "line": self.line,
            "pattern_id": self.pattern_id,
            "description": self.description,
            "severity": self.severity.value,
            "category": self.category,
            "recommendation": self.recommendation,
            "documentation_url": self.documentation_url,
        }


@dataclass
class PatternMatch:
    """
    Represents a matched pattern (Pro tier custom rules).

    [20251226_FEATURE] Pro tier model for custom pattern matching.
    """

    file: str
    line: int
    pattern_name: str
    matched_text: str
    context: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "file": self.file,
            "line": self.line,
            "pattern_name": self.pattern_name,
            "matched_text": self.matched_text,
            "context": self.context,
        }


@dataclass
class SecurityWarning:
    """
    Represents a security-related warning (Pro tier).

    [20251226_FEATURE] Pro tier model for security pattern detection.
    """

    file: str
    line: int
    warning_type: str
    description: str
    severity: ViolationSeverity = ViolationSeverity.ERROR
    cwe_id: str | None = None
    remediation: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "file": self.file,
            "line": self.line,
            "warning_type": self.warning_type,
            "description": self.description,
            "severity": self.severity.value,
            "cwe_id": self.cwe_id,
            "remediation": self.remediation,
        }


@dataclass
class ComplianceReport:
    """
    Represents a compliance audit report (Enterprise tier).

    [20251226_FEATURE] Enterprise tier model for regulatory compliance.
    """

    standard: str  # HIPAA, SOC2, GDPR, PCI-DSS
    status: str  # compliant, non_compliant, partial
    score: float  # 0.0 - 100.0
    findings: list[dict[str, Any]] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "standard": self.standard,
            "status": self.status,
            "score": self.score,
            "findings": self.findings,
            "recommendations": self.recommendations,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class AuditEntry:
    """
    Represents an audit trail entry (Enterprise tier).

    [20251226_FEATURE] Enterprise tier model for audit logging.
    """

    timestamp: datetime
    action: str
    user: str | None
    files_checked: list[str]
    rules_applied: int
    violations_found: int
    compliance_standards: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "action": self.action,
            "user": self.user,
            "files_checked": self.files_checked,
            "rules_applied": self.rules_applied,
            "violations_found": self.violations_found,
            "compliance_standards": self.compliance_standards,
            "metadata": self.metadata,
        }


@dataclass
class Certification:
    """
    Represents a compliance certification (Enterprise tier).

    [20251226_FEATURE] Enterprise tier model for PDF certificates.
    """

    standard: str
    issued_date: datetime
    valid_until: datetime
    certificate_id: str
    issuer: str = "Code Scalpel"
    status: str = "valid"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "standard": self.standard,
            "issued_date": self.issued_date.isoformat(),
            "valid_until": self.valid_until.isoformat(),
            "certificate_id": self.certificate_id,
            "issuer": self.issuer,
            "status": self.status,
        }


@dataclass
class ReportConfig:
    """
    Organization-specific configuration for compliance PDF reports (Enterprise tier).

    Pass this to code_policy_check via the report_config parameter to white-label
    the generated PDF with your organization's branding, contact details, and
    project metadata.

    Fields
    ------
    organization_name : str
        Company / organization name shown on the cover page and every page header.
    project_name : str
        Name of the project or codebase being audited.
    report_title : str | None
        Custom report title. Defaults to "<standard> Compliance Audit Report".
    contact_name : str | None
        Primary contact person for this report.
    contact_email : str | None
        Contact e-mail shown in the report metadata.
    department : str | None
        Department or team responsible for the codebase (e.g. "Engineering", "InfoSec").
    prepared_by : str | None
        Name of the person who commissioned / prepared the report.
    classification : str
        Document classification banner on every page.
        One of: "CONFIDENTIAL", "INTERNAL", "PUBLIC".  Default: "CONFIDENTIAL".
    project_description : str | None
        One- or two-sentence description of the project, shown in the executive summary.
    audit_period : str | None
        Human-readable audit period, e.g. "Q1 2026" or "2026-01-01 – 2026-03-31".
    version : str
        Report version string (default "1.0").
    logo_b64 : str | None
        Base64-encoded PNG or SVG logo to display on the cover page alongside the
        Code Scalpel branding. Supply a data-URI string, e.g.
        ``"data:image/png;base64,iVBOR..."``.
    custom_footer : str | None
        Additional text appended to every page footer (e.g. legal disclaimers).
    """

    organization_name: str = "Your Organization"
    project_name: str = "Code Review"
    report_title: str | None = None
    contact_name: str | None = None
    contact_email: str | None = None
    department: str | None = None
    prepared_by: str | None = None
    classification: str = "CONFIDENTIAL"
    project_description: str | None = None
    audit_period: str | None = None
    version: str = "1.0"
    logo_b64: str | None = None
    custom_footer: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict (suitable for JSON / MCP transport)."""
        return {
            "organization_name": self.organization_name,
            "project_name": self.project_name,
            "report_title": self.report_title,
            "contact_name": self.contact_name,
            "contact_email": self.contact_email,
            "department": self.department,
            "prepared_by": self.prepared_by,
            "classification": self.classification,
            "project_description": self.project_description,
            "audit_period": self.audit_period,
            "version": self.version,
            "logo_b64": self.logo_b64,
            "custom_footer": self.custom_footer,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ReportConfig":
        """Deserialize from a plain dict (e.g. received over MCP)."""
        valid_keys = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)


@dataclass
class CodePolicyResult:
    """
    Complete result from code policy check.

    [20251226_FEATURE] Main result model with tier-specific fields.

    Fields by tier:
    - Community: success, violations, files_checked, rules_applied, summary
    - Pro: + best_practices_violations, pattern_matches, security_warnings, custom_rule_results
    - Enterprise: + compliance_reports, audit_trail, pdf_report, compliance_score, certifications
    """

    # Core fields (all tiers)
    success: bool
    files_checked: int
    rules_applied: int
    summary: str
    violations: list[PolicyViolation] = field(default_factory=list)

    # Pro tier fields
    best_practices_violations: list[BestPracticeViolation] = field(default_factory=list)
    pattern_matches: list[PatternMatch] = field(default_factory=list)
    security_warnings: list[SecurityWarning] = field(default_factory=list)
    custom_rule_results: dict[str, list[dict[str, Any]]] = field(default_factory=dict)

    # Enterprise tier fields
    compliance_reports: dict[str, ComplianceReport] = field(default_factory=dict)
    audit_trail: list[AuditEntry] = field(default_factory=list)
    pdf_report: str | None = None  # Base64 encoded PDF
    compliance_score: float = 0.0  # 0.0-100.0
    certifications: list[Certification] = field(default_factory=list)

    # Metadata
    tier: str = "community"
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = {
            "success": self.success,
            "files_checked": self.files_checked,
            "rules_applied": self.rules_applied,
            "summary": self.summary,
            "violations": [v.to_dict() for v in self.violations],
            "tier": self.tier,
            "error": self.error,
        }

        # Add Pro tier fields if present
        if self.tier in ("pro", "enterprise"):
            result["best_practices_violations"] = [
                v.to_dict() for v in self.best_practices_violations
            ]
            result["pattern_matches"] = [m.to_dict() for m in self.pattern_matches]
            result["security_warnings"] = [w.to_dict() for w in self.security_warnings]
            result["custom_rule_results"] = self.custom_rule_results

        # Add Enterprise tier fields if present
        if self.tier == "enterprise":
            result["compliance_reports"] = {
                k: v.to_dict() for k, v in self.compliance_reports.items()
            }
            result["audit_trail"] = [e.to_dict() for e in self.audit_trail]
            result["pdf_report"] = self.pdf_report
            result["compliance_score"] = self.compliance_score
            result["certifications"] = [c.to_dict() for c in self.certifications]

        return result


@dataclass
class CustomRule:
    """
    Represents a custom rule definition (Pro tier).

    [20251226_FEATURE] Pro tier model for user-defined rules.
    """

    name: str
    description: str
    pattern: str  # Regex pattern or AST pattern
    pattern_type: str = "regex"  # regex, ast
    severity: ViolationSeverity = ViolationSeverity.WARNING
    message_template: str = "Matched pattern: {pattern_name}"
    enabled: bool = True

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "description": self.description,
            "pattern": self.pattern,
            "pattern_type": self.pattern_type,
            "severity": self.severity.value,
            "message_template": self.message_template,
            "enabled": self.enabled,
        }
