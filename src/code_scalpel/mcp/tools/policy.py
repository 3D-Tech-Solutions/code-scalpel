"""Policy and governance MCP tool registrations."""

from __future__ import annotations

import asyncio
import time

from code_scalpel.licensing.features import get_tool_capabilities
from code_scalpel.mcp.helpers.policy_helpers import (
    _code_policy_check_sync,
    _get_current_tier,
    _validate_paths_sync,
    _verify_policy_integrity_sync,
)
from code_scalpel.mcp.protocol import mcp
from code_scalpel.mcp.contract import ToolResponseEnvelope, ToolError, make_envelope
from code_scalpel.mcp.oracle_middleware import with_oracle_resilience, PathStrategy
from code_scalpel import __version__ as _pkg_version


@mcp.tool(
    description="Verify file paths are accessible and resolve aliases; detects Docker mounting issues."
)
@with_oracle_resilience(tool_id="validate_paths", strategy=PathStrategy)
async def validate_paths(
    paths: list[str], project_root: str | None = None
) -> ToolResponseEnvelope:
    """Validate that paths are accessible before running file-based operations.

    Checks that provided file paths exist and are accessible within the project,
    preventing invalid file access errors in subsequent operations.

    **Tier Behavior:**
    - Community: Basic path validation (max 100 paths)
    - Pro: All Community + alias resolution and dynamic import detection (unlimited paths)
    - Enterprise: All Pro + security validation and boundary testing (unlimited paths)

    **Tier Capabilities:**
    - Community: path_accessibility_checking, docker_environment_detection, workspace_root_detection (max_paths=100)
    - Pro: All Community + path_alias_resolution, tsconfig_paths_support, webpack_alias_support, dynamic_import_resolution (max_paths=None)
    - Enterprise: All Pro + permission_checks, security_validation, path_traversal_simulation, security_boundary_testing (max_paths=None)

    **Args:**
        paths (list[str]): List of file paths to validate.
        project_root (str, optional): Project root directory for relative path resolution.

    **Returns:**
        ToolResponseEnvelope containing PathValidationResult with:
        - success (bool): True if all paths validated successfully
        - accessible (list[str]): Successfully resolved paths
        - inaccessible (list[str]): Paths that could not be resolved
        - suggestions (list[str]): Actionable suggestions for inaccessible paths
        - workspace_roots (list[str]): Detected workspace root directories
        - is_docker (bool): Whether running in Docker container
        - alias_resolutions (dict): Resolved path aliases (Pro+)
        - dynamic_imports (list[dict]): Detected dynamic import patterns (Pro+)
        - traversal_vulnerabilities (list[dict]): Directory traversal attempts (Enterprise)
        - boundary_violations (list[dict]): Workspace boundary violations (Enterprise)
        - security_score (float, 0.0-10.0): Overall security score (Enterprise)
        - truncated (bool): Whether input was truncated
        - paths_received (int): Original number of paths
        - paths_checked (int): Number of paths actually validated
        - max_paths_applied (int, optional): Applied max_paths limit
        - error (str): Error message if validation failed
        - tier_applied (str): Tier used for analysis
        - duration_ms (int): Analysis duration in milliseconds
    """
    started = time.perf_counter()
    try:
        tier = _get_current_tier()
        capabilities = get_tool_capabilities("validate_paths", tier) or {}
        result = await asyncio.to_thread(
            _validate_paths_sync, paths, project_root, tier, capabilities
        )
        duration_ms = int((time.perf_counter() - started) * 1000)
        return make_envelope(
            data=result,
            tool_id="validate_paths",
            tool_version=_pkg_version,
            tier=tier,
            duration_ms=duration_ms,
        )
    except Exception as exc:
        duration_ms = int((time.perf_counter() - started) * 1000)
        tier = _get_current_tier()
        error_obj = ToolError(error=str(exc), error_code="internal_error")
        return make_envelope(
            data=None,
            tool_id="validate_paths",
            tool_version=_pkg_version,
            tier=tier,
            duration_ms=duration_ms,
            error=error_obj,
        )


@mcp.tool(
    description="Cryptographically verify .code-scalpel policy files have not been tampered with."
)
@with_oracle_resilience(tool_id="verify_policy_integrity", strategy=PathStrategy)
async def verify_policy_integrity(
    policy_dir: str | None = None,
    manifest_source: str = "file",
) -> ToolResponseEnvelope:
    """Verify policy file integrity using cryptographic signatures.

    Validates that policy files have not been tampered with by checking their
    cryptographic signatures against a manifest.

    **Tier Behavior:**
    - Community: Basic verification only
    - Pro: All Community + cryptographic signature validation
    - Enterprise: All Pro + full integrity checking and audit logging

    **Tier Capabilities:**
    - Community: basic_verification only (signature_validation=False, tamper_detection=False)
    - Pro: All Community + signature_validation (signature_validation=True, tamper_detection=True)
    - Enterprise: All Pro + full_integrity_check, audit_logging (signature_validation=True, tamper_detection=True)

    **Args:**
        policy_dir (str, optional): Directory containing policy files. If None, uses project root.
        manifest_source (str): Where to load manifest from. Default: "file". Options: "file", "embedded", "remote".

    **Returns:**
        ToolResponseEnvelope containing PolicyVerificationResult with:
        - success (bool): Whether all policy files verified successfully
        - manifest_valid (bool): Whether manifest signature is valid
        - files_verified (int): Number of files successfully verified
        - files_failed (list[str]): List of files that failed verification
        - error (str, optional): Error message if verification failed
        - error_code (str, optional): Machine-readable error code
        - manifest_source (str, optional): Source of the policy manifest
        - policy_dir (str, optional): Policy directory that was verified
        - tier (str): Tier used for verification
        - signature_validated (bool): Whether HMAC signature was validated
        - tamper_detection_enabled (bool): Whether tamper detection is active
        - audit_log_entry (dict, optional): Enterprise audit log entry
        - error (str): Error message if operation failed
        - tier_applied (str): Tier used for analysis
        - duration_ms (int): Analysis duration in milliseconds
    """
    started = time.perf_counter()
    try:
        tier = _get_current_tier()
        capabilities = get_tool_capabilities("verify_policy_integrity", tier) or {}
        result = await asyncio.to_thread(
            _verify_policy_integrity_sync,
            policy_dir,
            manifest_source,
            tier,
            capabilities,
        )
        duration_ms = int((time.perf_counter() - started) * 1000)
        return make_envelope(
            data=result,
            tool_id="verify_policy_integrity",
            tool_version=_pkg_version,
            tier=tier,
            duration_ms=duration_ms,
        )
    except Exception as exc:
        duration_ms = int((time.perf_counter() - started) * 1000)
        tier = _get_current_tier()
        error_obj = ToolError(error=str(exc), error_code="internal_error")
        return make_envelope(
            data=None,
            tool_id="verify_policy_integrity",
            tool_version=_pkg_version,
            tier=tier,
            duration_ms=duration_ms,
            error=error_obj,
        )


@mcp.tool(
    description="Check code against style guides and compliance standards (HIPAA, SOC2, PCI-DSS)."
)
@with_oracle_resilience(tool_id="code_policy_check", strategy=PathStrategy)
async def code_policy_check(
    paths: list[str],
    rules: list[str] | None = None,
    compliance_standards: list[str] | None = None,
    generate_report: bool = False,
    report_config: dict | None = None,
) -> ToolResponseEnvelope:
    """Check code against style guides, best practices, and compliance standards.

    Analyzes source code files for adherence to coding standards, style guides,
    and best practices. Can optionally enforce organizational compliance standards.

    **Tier Behavior:**
    - Community: Basic style checks (PEP8, ESLint rules, basic patterns)
    - Pro: All Community + best practice analysis, security patterns, async error patterns, custom rules
    - Enterprise: All Pro + compliance standards (HIPAA, SOC2, GDPR, PCI-DSS), auditing, certifications, PDF reports

    **Tier Capabilities:**
    - Community: Style guide checking, PEP8 validation (max_files=100, max_rules=50)
    - Pro: All Community + best practice analysis, custom rules (max_files=1000, max_rules=200)
    - Enterprise: All Pro + compliance standards, PDF reports (max_files=unlimited, max_rules=unlimited)

    **Args:**
        paths (list[str]): List of file paths to check against policies.
        rules (list[str], optional): Specific rules to enforce. If None, use defaults.
        compliance_standards (list[str], optional): Compliance frameworks (HIPAA, SOC2, GDPR, PCI-DSS). Enterprise tier only.
        generate_report (bool): Generate compliance report. Default: False. Enterprise tier only.
        report_config (dict, optional): Organization branding for the PDF report. Enterprise tier only.
            Accepted keys (all optional):
            - organization_name (str): Company name shown on every page.
            - project_name (str): Project or codebase being audited.
            - report_title (str): Custom report title.
            - contact_name (str): Primary contact person.
            - contact_email (str): Contact e-mail.
            - department (str): Department or team responsible for the codebase.
            - prepared_by (str): Name of person who prepared the report.
            - classification (str): Document classification — "CONFIDENTIAL", "INTERNAL", or "PUBLIC".
            - project_description (str): Short description of the project.
            - audit_period (str): Human-readable audit period, e.g. "Q1 2026".
            - version (str): Report version string, e.g. "1.0".
            - logo_b64 (str): Base64-encoded org logo (data-URI, PNG or SVG).
            - custom_footer (str): Additional text appended to every page footer.

    **Returns:**
        ToolResponseEnvelope with CodePolicyCheckResult containing:
        - success (bool): True if check completed (no critical violations)
        - files_checked (int): Number of files analyzed
        - rules_applied (int): Number of rules applied
        - summary (str): Human-readable summary of results
        - violations (list[dict]): Policy violations found
        - best_practices_violations (list[dict]): Best practice violations (Pro/Enterprise)
        - security_warnings (list[dict]): Security warnings detected (Pro/Enterprise)
        - custom_rule_results (list[dict]): Custom rule matches (Pro/Enterprise)
        - compliance_reports (dict): Compliance audit reports by standard (Enterprise)
        - compliance_score (int, 0-100): Overall compliance score (Enterprise)
        - certifications (list[str]): Generated certifications (Enterprise)
        - audit_trail (list[dict]): Audit log entries (Enterprise)
        - pdf_report (str): Base64-encoded PDF report (Enterprise)
        - tier_applied (str): Tier used for analysis
        - files_limit_applied (int, optional): Max files limit applied
        - rules_limit_applied (int, optional): Max rules limit applied
        - error (str, optional): Error message if check failed
        - duration_ms (int): Analysis duration in milliseconds
    """
    started = time.perf_counter()
    try:
        tier = _get_current_tier()
        capabilities = get_tool_capabilities("code_policy_check", tier) or {}

        if compliance_standards and tier != "enterprise":
            compliance_standards = None

        if generate_report and tier != "enterprise":
            generate_report = False

        result = await asyncio.to_thread(
            _code_policy_check_sync,
            paths,
            rules,
            compliance_standards,
            generate_report,
            tier,
            capabilities,
            report_config,
        )
        duration_ms = int((time.perf_counter() - started) * 1000)
        return make_envelope(
            data=result,
            tool_id="code_policy_check",
            tool_version=_pkg_version,
            tier=tier,
            duration_ms=duration_ms,
        )
    except Exception as exc:
        duration_ms = int((time.perf_counter() - started) * 1000)
        tier = _get_current_tier()
        error_obj = ToolError(error=str(exc), error_code="internal_error")
        return make_envelope(
            data=None,
            tool_id="code_policy_check",
            tool_version=_pkg_version,
            tier=tier,
            duration_ms=duration_ms,
            error=error_obj,
        )


__all__ = ["validate_paths", "verify_policy_integrity", "code_policy_check"]
