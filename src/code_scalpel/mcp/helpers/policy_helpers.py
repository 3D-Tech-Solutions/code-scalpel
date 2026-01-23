from __future__ import annotations

from typing import Any, cast

from code_scalpel.licensing.features import get_tool_capabilities
from code_scalpel.mcp.models.policy import (
    CodePolicyCheckResult,
    PathValidationResult,
    PolicyVerificationResult,
)

# [20260116_BUGFIX] Import _get_current_tier from protocol for consistent license validation
from code_scalpel.mcp.protocol import _get_current_tier
from code_scalpel.policy_engine.audit_log import (
    AuditLog,
)  # [20260121_BUGFIX] Persist audit events


def _validate_paths_sync(
    paths: list[str],
    project_root: str | None,
    tier: str = "community",
    capabilities: dict | None = None,
) -> PathValidationResult:
    """Synchronous implementation of validate_paths."""
    import json
    import re
    from pathlib import Path as PathLib

    from code_scalpel.licensing.config_loader import (
        filter_response,
        get_cached_response_config,
    )
    from code_scalpel.mcp.path_resolver import PathResolver

    if capabilities is None:
        capabilities = get_tool_capabilities("validate_paths", tier) or {}

    caps_set: set[str] = set(capabilities.get("capabilities", []) or [])
    limits = capabilities.get("limits", {}) or {}

    paths_received = len(paths)
    truncated = False
    max_paths_applied: int | None = None

    try:
        max_paths = limits.get("max_paths")
        if max_paths is not None and len(paths) > max_paths:
            truncated = True
            max_paths_applied = int(max_paths)
            paths = paths[:max_paths_applied]

        resolver = PathResolver()
        accessible, inaccessible = resolver.validate_paths(paths, project_root)

        workspace_roots_sorted = sorted(resolver.workspace_roots)

        suggestions: list[str] = []
        if truncated and max_paths_applied is not None:
            suggestions.append(
                f"Input exceeded max_paths={max_paths_applied}; validated first {len(paths)} of {paths_received}."
            )
            suggestions.append("Consider batching into smaller chunks and retrying.")

        if inaccessible:
            if resolver.is_docker:
                suggestions.append("Running in Docker: Mount your project with -v /path/to/project:/workspace")
                suggestions.append("Example: docker run -v $(pwd):/workspace code-scalpel:latest")
            else:
                suggestions.append("Ensure files exist and use absolute paths or place in workspace roots:")
                for root in workspace_roots_sorted[:3]:
                    suggestions.append(f"  - {root}")
            suggestions.append("Set WORKSPACE_ROOT env variable to specify custom root")

        alias_resolutions: list[dict] = []
        dynamic_imports: list[dict] = []
        traversal_vulnerabilities: list[dict] = []
        boundary_violations: list[dict] = []
        security_score: float | None = None

        if "path_alias_resolution" in caps_set and project_root:
            if "tsconfig_paths_support" in caps_set:
                tsconfig_path = PathLib(project_root) / "tsconfig.json"
                if tsconfig_path.exists():
                    try:
                        tsconfig = json.loads(tsconfig_path.read_text())
                        compiler_options = tsconfig.get("compilerOptions", {})
                        paths_config = compiler_options.get("paths", {})
                        base_url = compiler_options.get("baseUrl", ".")
                        for alias, target_patterns in paths_config.items():
                            for target in target_patterns:
                                alias_key = alias.replace("/*", "")
                                target_path = target.replace("/*", "")
                                resolved = str(PathLib(project_root) / base_url / target_path)
                                alias_resolutions.append(
                                    {
                                        "alias": alias_key,
                                        "original_path": target,
                                        "resolved_path": resolved,
                                        "source": "tsconfig.json",
                                    }
                                )
                    except Exception as e:  # noqa: BLE001
                        suggestions.append(f"Could not parse tsconfig.json: {e}")

            if "webpack_alias_support" in caps_set:
                webpack_path = PathLib(project_root) / "webpack.config.js"
                if webpack_path.exists():
                    try:
                        content = webpack_path.read_text()
                        alias_pattern = r"[\"'](@[^\"']+)[\"']\s*:\s*"
                        matches = re.findall(alias_pattern, content)
                        for alias in matches:
                            alias_resolutions.append(
                                {
                                    "alias": alias,
                                    "original_path": f"src/{alias.replace('@', '')}",
                                    "resolved_path": str(PathLib(project_root) / "src" / alias.replace("@", "")),
                                    "source": "webpack.config.js",
                                }
                            )
                    except Exception as e:  # noqa: BLE001
                        suggestions.append(f"Could not parse webpack.config.js: {e}")

        if "dynamic_import_resolution" in caps_set:
            for apath in accessible:
                if apath.endswith((".js", ".ts", ".jsx", ".tsx")):
                    try:
                        content = PathLib(apath).read_text()
                        if "import(" in content:
                            dynamic_imports.append(
                                {
                                    "source_file": apath,
                                    "import_pattern": "dynamic_import_detected",
                                    "resolved_paths": [],
                                }
                            )
                    except Exception:  # noqa: BLE001
                        pass

        if "path_traversal_simulation" in caps_set:
            for p in paths:
                if ".." in p:
                    severity = "high"
                    if p.count("..") > 2:
                        severity = "critical"
                    traversal_vulnerabilities.append(
                        {
                            "path": p,
                            "escape_attempt": f"Contains {p.count('..')} parent directory references",
                            "severity": severity,
                            "recommendation": "Remove traversal sequences or validate against whitelist",
                        }
                    )

        if "security_boundary_testing" in caps_set:
            for p in paths:
                try:
                    abs_path = PathLib(p).resolve()
                    is_within = False
                    for root in resolver.workspace_roots:
                        try:
                            abs_path.relative_to(PathLib(root).resolve())
                            is_within = True
                            break
                        except ValueError:
                            continue
                    if not is_within and not p.startswith(("/usr/", "/lib/", "/etc/")):
                        boundary_violations.append(
                            {
                                "path": str(abs_path),
                                "boundary": (resolver.workspace_roots[0] if resolver.workspace_roots else "unknown"),
                                "violation_type": "workspace_escape",
                                "risk": "high",
                            }
                        )
                except Exception:  # noqa: BLE001
                    pass

        if "security_boundary_testing" in caps_set:
            score = 10.0
            critical_count = sum(1 for v in traversal_vulnerabilities if v.get("severity") == "critical")
            high_count = sum(1 for v in traversal_vulnerabilities if v.get("severity") == "high")
            score -= critical_count * 3.0 + high_count * 1.5
            score -= len(boundary_violations) * 2.0
            score -= len(inaccessible) * 0.5
            security_score = max(0.0, min(10.0, score))
        else:
            security_score = None

        result = PathValidationResult(
            success=len(inaccessible) == 0,
            accessible=accessible,
            inaccessible=inaccessible,
            suggestions=suggestions,
            workspace_roots=workspace_roots_sorted,
            is_docker=resolver.is_docker,
            alias_resolutions=alias_resolutions,
            dynamic_imports=dynamic_imports,
            traversal_vulnerabilities=traversal_vulnerabilities,
            boundary_violations=boundary_violations,
            security_score=security_score,
            truncated=True if truncated else None,
            paths_received=paths_received if truncated else None,
            paths_checked=len(paths) if truncated else None,
            max_paths_applied=max_paths_applied if truncated else None,
        )

        response_config = get_cached_response_config()
        try:
            filtered_dict = filter_response(result.model_dump(), "validate_paths", response_config)
            return PathValidationResult(**filtered_dict)
        except Exception as e:  # noqa: BLE001
            _ = e
            return result

    except Exception as e:  # noqa: BLE001
        return PathValidationResult(
            success=False,
            error=str(e),
            error_code="VALIDATE_PATHS_INTERNAL_ERROR",
            accessible=[],
            inaccessible=[],
            suggestions=[
                "Internal error while validating paths.",
                "Retry, and if it persists, report the error_code and error message.",
            ],
            workspace_roots=[],
            is_docker=False,
            truncated=True if truncated else None,
            paths_received=paths_received if truncated else None,
            paths_checked=len(paths) if truncated else None,
            max_paths_applied=max_paths_applied if truncated else None,
        )


def _verify_policy_integrity_sync(
    policy_dir: str | None = None,
    manifest_source: str = "file",
    tier: str | None = None,
    capabilities: dict | None = None,
) -> PolicyVerificationResult:
    """Synchronous implementation of policy integrity verification."""
    from datetime import datetime

    dir_path = policy_dir or ".code-scalpel"

    if tier is None:
        tier = _get_current_tier()

    if capabilities is None:
        capabilities = get_tool_capabilities("verify_policy_integrity", tier) or {}

    caps_set: set[str] = set(capabilities.get("capabilities", []) or [])
    limits = capabilities.get("limits", {}) or {}

    signature_validation_enabled = limits.get("signature_validation", False)
    tamper_detection_enabled = limits.get("tamper_detection", False)
    audit_logging_enabled = "audit_logging" in caps_set

    def _finalize(result: PolicyVerificationResult) -> PolicyVerificationResult:
        """Attach persistent audit entry when enabled."""

        if audit_logging_enabled:
            severity = "LOW" if result.success else "HIGH"
            try:
                log_path = Path(dir_path) / "audit.log"
                AuditLog(str(log_path)).record_event(
                    event_type="verify_policy_integrity",
                    severity=severity,
                    details={
                        "manifest_source": result.manifest_source,
                        "policy_dir": result.policy_dir,
                        "files_verified": result.files_verified,
                        "files_failed": result.files_failed,
                        "error": result.error,
                        "error_code": result.error_code,
                        "tier": result.tier,
                        "signature_validated": result.signature_validated,
                    },
                )
            except Exception:
                pass

        return result

    result = PolicyVerificationResult(
        success=False,
        manifest_source=manifest_source,
        policy_dir=dir_path,
        tier=tier,
        signature_validated=False,
        tamper_detection_enabled=tamper_detection_enabled,
        audit_log_entry=None,
        error_code=None,
    )

    try:
        if "basic_verification" in caps_set:
            import json
            from pathlib import Path

            import yaml

            policy_path = Path(dir_path)
            if not policy_path.exists():
                result.error = f"Policy directory not found: {dir_path}"
                result.error_code = "POLICY_DIR_NOT_FOUND"
                return _finalize(result)

            policy_files = []
            for ext in ["*.yaml", "*.yml", "*.json"]:
                policy_files.extend(policy_path.glob(ext))

            policy_files = [pf for pf in policy_files if pf.name != "policy.manifest.json"]

            policy_files = sorted(policy_files, key=lambda p: p.name)

            if not policy_files:
                result.error = f"No policy files found in {dir_path}"
                result.error_code = "NO_POLICY_FILES"
                return _finalize(result)

            from code_scalpel.licensing.config_loader import get_tool_limits

            tier_limits = get_tool_limits("verify_policy_integrity", tier)
            max_files = tier_limits.get("max_policy_files")

            if max_files is not None and len(policy_files) > max_files:
                result.error = (
                    f"Policy file limit exceeded: {len(policy_files)} files found, "
                    f"{max_files} allowed for {tier} tier."
                )
                result.success = False
                result.error_code = "POLICY_FILE_LIMIT_EXCEEDED"
                return _finalize(result)

            def _safe_error_text(text: str) -> str:
                out: list[str] = []
                for ch in text:
                    o = ord(ch)
                    if o < 32 and ch not in ("\n", "\r", "\t"):
                        out.append(f"\\x{o:02x}")
                    else:
                        out.append(ch)
                return "".join(out)

            files_verified = 0
            files_failed = []
            for pf in policy_files:
                try:
                    content = pf.read_text()
                    if pf.suffix == ".json":
                        json.loads(content)
                    else:
                        yaml.safe_load(content)
                    files_verified += 1
                except Exception as e:
                    files_failed.append(f"{pf.name}: {_safe_error_text(str(e))}")

            result.files_verified = files_verified
            result.files_failed = files_failed

            if not signature_validation_enabled:
                result.success = len(files_failed) == 0
                if files_failed:
                    result.error = f"Invalid policy files: {', '.join(files_failed)}"
                    result.error_code = "POLICY_PARSE_ERROR"
                return _finalize(result)

        if "signature_validation" in caps_set and signature_validation_enabled:
            from code_scalpel.policy_engine.crypto_verify import (
                CryptographicPolicyVerifier,
                SecurityError,
            )

            try:
                verifier = CryptographicPolicyVerifier(
                    manifest_source=manifest_source,
                    policy_dir=dir_path,
                )

                crypto_result = verifier.verify_all_policies()

                result.success = crypto_result.success
                result.manifest_valid = crypto_result.manifest_valid
                result.files_verified = crypto_result.files_verified
                result.files_failed = crypto_result.files_failed
                result.error = crypto_result.error
                result.signature_validated = crypto_result.manifest_valid

            except SecurityError as e:
                result.success = False
                result.error = str(e)
                result.error_code = "SECURITY_ERROR"
                result.signature_validated = False

        if audit_logging_enabled and "full_integrity_check" in caps_set:
            result.audit_log_entry = {
                "timestamp": datetime.now().isoformat(),
                "action": "policy_verification",
                "policy_dir": dir_path,
                "manifest_source": manifest_source,
                "success": result.success,
                "files_verified": result.files_verified,
                "files_failed": result.files_failed,
                "signature_validated": result.signature_validated,
                "tier": tier,
            }

        return _finalize(result)

    except ImportError as e:
        result.error = f"Policy engine not available: {str(e)}."
        result.error_code = "POLICY_ENGINE_UNAVAILABLE"
        return _finalize(result)
    except Exception as e:  # noqa: BLE001
        result.error = f"Verification failed: {str(e)}."
        result.error_code = "INTERNAL_ERROR"
        return _finalize(result)


def _code_policy_check_sync(
    paths: list[str],
    rules: list[str] | None,
    compliance_standards: list[str] | None,
    generate_report: bool,
    tier: str,
    capabilities: dict[str, Any],
) -> CodePolicyCheckResult:
    """Synchronous implementation of code_policy_check."""
    from code_scalpel.policy_engine.code_policy_check import CodePolicyChecker

    checker = CodePolicyChecker(
        tier=tier,
        compliance_standards=compliance_standards,
    )

    result = checker.check_files(
        paths=paths,
        rules=rules,
        generate_report=generate_report and tier == "enterprise",
    )

    limits = capabilities.get("limits", {})
    files_limit = limits.get("max_files")
    rules_limit = limits.get("max_rules")

    mcp_result = CodePolicyCheckResult(
        success=result.success,
        files_checked=result.files_checked,
        rules_applied=result.rules_applied,
        summary=result.summary,
        tier=tier,
        tier_applied=tier,
        files_limit_applied=files_limit,
        rules_limit_applied=rules_limit,
        violations=[cast(dict[str, Any], v.to_dict() if hasattr(v, "to_dict") else v) for v in result.violations],
        error=result.error,
    )

    set(capabilities.get("capabilities", []))

    if tier in ("pro", "enterprise"):
        mcp_result.best_practices_violations = [
            cast(dict[str, Any], v.to_dict() if hasattr(v, "to_dict") else v) for v in result.best_practices_violations
        ]
        mcp_result.security_warnings = [
            cast(dict[str, Any], w.to_dict() if hasattr(w, "to_dict") else w) for w in result.security_warnings
        ]
        mcp_result.custom_rule_results = result.custom_rule_results

    if tier == "enterprise":
        mcp_result.compliance_reports = {k: v.to_dict() for k, v in result.compliance_reports.items()}
        mcp_result.compliance_score = result.compliance_score
        mcp_result.certifications = [c.to_dict() for c in result.certifications]
        mcp_result.audit_trail = [e.to_dict() for e in result.audit_trail]
        mcp_result.pdf_report = result.pdf_report

    return mcp_result


__all__ = [
    "_get_current_tier",
    "_validate_paths_sync",
    "_verify_policy_integrity_sync",
    "_code_policy_check_sync",
]
