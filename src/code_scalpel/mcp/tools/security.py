"""Security MCP tool registrations."""

from __future__ import annotations

import asyncio
import os
import time
from importlib import import_module
from typing import Optional

from mcp.server.fastmcp import Context
from code_scalpel.licensing.features import get_tool_capabilities
from code_scalpel.mcp.helpers.security_helpers import (
    _unified_sink_detect_sync,
    _type_evaporation_scan_sync,
    _scan_dependencies_sync,
    _security_scan_sync,
)
from code_scalpel.mcp.protocol import mcp, _get_current_tier
from code_scalpel.mcp.contract import ToolResponseEnvelope, ToolError, make_envelope
from code_scalpel.mcp.oracle_middleware import with_oracle_resilience, PathStrategy
from code_scalpel import __version__ as _pkg_version


@mcp.tool(
    description="Detect dangerous sink patterns (SQL injection, XSS, etc.) across Python, JS, TS, and Java."
)
async def unified_sink_detect(
    code: str, language: str = "auto", confidence_threshold: float = 0.7
) -> ToolResponseEnvelope:
    """Detect polyglot security sinks with confidence thresholds.

    Identifies dangerous sinks (functions that handle untrusted data) across multiple
    languages. Language is auto-detected from code if set to 'auto' (default).

    **Tier Behavior:**
    - Community: Basic sink detection, CWE mapping, confidence scoring
    - Pro: All Community + context-aware detection, framework-specific sinks, custom patterns
    - Enterprise: All Pro + compliance reporting, risk scoring, remediation suggestions

    **Tier Capabilities:**
    - Community: Pattern-based detection only
    - Pro: All Community + context analysis, custom patterns
    - Enterprise: All Pro + compliance mappings, remediation suggestions

    **Args:**
        code (str): Source code to scan for sinks.
        language (str): Programming language. Default: "auto" (auto-detect).
                       Supported: python, javascript, typescript, java, c, cpp, csharp, go
        confidence_threshold (float): Minimum confidence score (0.0-1.0). Default: 0.7 (70%).

    **Returns:**
        ToolResponseEnvelope with UnifiedSinkResult containing:
        - success (bool): True if detection completed successfully
        - language (str): Language analyzed
        - sink_count (int): Number of sinks detected
        - sinks (list[dict]): Detected sinks meeting confidence threshold
        - coverage_summary (dict): Summary of sink pattern coverage
        - logic_sinks (list[dict]): Logic sinks detected (Pro)
        - extended_language_sinks (dict): Additional language sink details (Pro)
        - confidence_scores (dict): Per-sink confidence scores (Pro/Enterprise)
        - sink_categories (dict): Sink categorization by risk level (Enterprise)
        - risk_assessments (list[dict]): Risk assessments with clearance (Enterprise)
        - custom_sink_matches (list[dict]): Custom sink pattern matches (Enterprise)
        - context_analysis (dict): Context-aware detection results (Pro)
        - framework_sinks (dict): Framework-specific sink detections (Pro)
        - compliance_mapping (dict): Compliance standard mappings (Enterprise)
        - historical_comparison (dict): Historical sink tracking comparison (Enterprise)
        - remediation_suggestions (list[str]): Automated remediation suggestions (Enterprise)
        - truncated (bool): Whether results were truncated
        - sinks_detected (int): Total sinks detected before truncation
        - max_sinks_applied (int, optional): Max sinks limit applied
        - error (str, optional): Error message if detection failed
        - error (str): Error message if detection failed
        - tier_applied (str): Tier used for detection
        - duration_ms (int): Detection duration in milliseconds
    """
    started = time.perf_counter()
    try:
        if language == "auto" or language is None:
            from code_scalpel.surgery.unified_extractor import Language, detect_language

            detected = detect_language(None, code)
            lang_map = {
                Language.PYTHON: "python",
                Language.JAVASCRIPT: "javascript",
                Language.TYPESCRIPT: "typescript",
                Language.JAVA: "java",
            }
            language = lang_map.get(detected, "python")

        tier = _get_current_tier()
        capabilities = get_tool_capabilities("unified_sink_detect", tier)
        result = await asyncio.to_thread(
            _unified_sink_detect_sync,
            code,
            language,
            confidence_threshold,
            tier,
            capabilities,
        )
        duration_ms = int((time.perf_counter() - started) * 1000)
        return make_envelope(
            data=result,
            tool_id="unified_sink_detect",
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
            tool_id="unified_sink_detect",
            tool_version=_pkg_version,
            tier=tier,
            duration_ms=duration_ms,
            error=error_obj,
        )


@mcp.tool(
    description="Detect TypeScript type-safety erosion: 'any' widening, unsafe casts, and missing guards."
)
@with_oracle_resilience(tool_id="type_evaporation_scan", strategy=PathStrategy)
async def type_evaporation_scan(
    frontend_code: str | None = None,
    backend_code: str | None = None,
    frontend_file_path: str | None = None,
    backend_file_path: str | None = None,
    frontend_file: str = "frontend.ts",
    backend_file: str = "backend.py",
) -> ToolResponseEnvelope:
    """Detect Type System Evaporation vulnerabilities across frontend/backend.

    Identifies security issues when type information is lost at frontend/backend boundaries.
    Provide either code strings or file paths for both frontend and backend code.

    **Tier Behavior:**
    - Community: Frontend-only analysis, basic type checking
    - Pro: All Community + network boundary analysis, implicit any tracing, library boundary checks
    - Enterprise: All Pro + runtime validation generation, Zod schema generation, API contract validation

    **Tier Capabilities:**
    - Community: Frontend analysis only, single file
    - Pro: All Community + network boundary analysis (max_files=10)
    - Enterprise: All Pro + API contracts and validation generation (max_files=unlimited)

    **Args:**
        frontend_code (str, optional): Frontend TypeScript/JavaScript code. Either frontend_code or frontend_file_path required.
        backend_code (str, optional): Backend Python code. Either backend_code or backend_file_path required.
        frontend_file_path (str, optional): Path to frontend file. Either frontend_code or frontend_file_path required.
        backend_file_path (str, optional): Path to backend file. Either backend_code or backend_file_path required.
        frontend_file (str): Display name for frontend file. Default: "frontend.ts".
        backend_file (str): Display name for backend file. Default: "backend.py".

    **Returns:**
        ToolResponseEnvelope with TypeEvaporationResultModel containing:
        - success (bool): True if analysis completed successfully
        - frontend_vulnerabilities (int): Number of frontend vulnerabilities
        - backend_vulnerabilities (int): Number of backend vulnerabilities
        - cross_file_issues (int): Number of cross-file issues
        - matched_endpoints (list[dict]): Correlated API endpoints
        - vulnerabilities (list[dict]): All vulnerabilities found
        - summary (str): Analysis summary
        - implicit_any_count (int): Count of implicit any detections (Pro)
        - network_boundaries (list[dict]): Detected network call boundaries (Pro)
        - boundary_violations (list[dict]): Type violations at boundaries (Pro)
        - library_boundaries (list[dict]): Library call type boundaries (Pro)
        - json_parse_locations (list[dict]): JSON.parse() without validation (Pro)
        - generated_schemas (list[str]): Generated Zod schemas (Enterprise)
        - validation_code (str): Generated validation code (Enterprise)
        - schema_coverage (float): Coverage ratio of validated endpoints (Enterprise)
        - pydantic_models (list[str]): Generated Pydantic models (Enterprise)
        - api_contract (dict): API contract validation results (Enterprise)
        - remediation_suggestions (list[str]): Automated remediation suggestions (Enterprise)
        - custom_rule_violations (list[dict]): Custom type rule violations (Enterprise)
        - compliance_report (dict): Type compliance validation report (Enterprise)
        - warnings (list[str]): Non-fatal warnings
        - error (str, optional): Error message if analysis failed
        - error (str): Error message if analysis failed
        - tier_applied (str): Tier used for analysis
        - duration_ms (int): Analysis duration in milliseconds
    """
    started = time.perf_counter()
    try:
        # Validate input: at least one way to provide each code
        if frontend_code is None and frontend_file_path is None:
            raise ValueError(
                "Either 'frontend_code' or 'frontend_file_path' must be provided"
            )
        if backend_code is None and backend_file_path is None:
            raise ValueError(
                "Either 'backend_code' or 'backend_file_path' must be provided"
            )

        # Read from files if codes not provided
        if frontend_code is None and frontend_file_path is not None:
            if not os.path.isfile(frontend_file_path):
                raise ValueError(f"Frontend file not found: {frontend_file_path}")
            with open(frontend_file_path, "r", encoding="utf-8") as f:
                frontend_code = f.read()
            frontend_file = os.path.basename(frontend_file_path)

        if backend_code is None and backend_file_path is not None:
            if not os.path.isfile(backend_file_path):
                raise ValueError(f"Backend file not found: {backend_file_path}")
            with open(backend_file_path, "r", encoding="utf-8") as f:
                backend_code = f.read()
            backend_file = os.path.basename(backend_file_path)

        tier = _get_current_tier()
        caps = get_tool_capabilities("type_evaporation_scan", tier) or {}
        cap_set = set(caps.get("capabilities", []))
        limits = caps.get("limits", {}) or {}
        frontend_only = bool(limits.get("frontend_only", False))
        raw_max_files = limits.get("max_files")
        try:
            max_files = int(raw_max_files) if raw_max_files is not None else None
        except (TypeError, ValueError):
            max_files = None

        enable_pro = bool(
            {
                "implicit_any_tracing",
                "network_boundary_analysis",
                "library_boundary_analysis",
            }
            & cap_set
        )
        enable_enterprise = bool(
            {
                "runtime_validation_generation",
                "zod_schema_generation",
                "api_contract_validation",
            }
            & cap_set
        )

        # At this point, both frontend_code and backend_code are guaranteed to be set
        # (validated above at lines 111-133)
        assert (
            frontend_code is not None
        ), "frontend_code must be provided or read from file"
        assert (
            backend_code is not None
        ), "backend_code must be provided or read from file"

        result = await asyncio.to_thread(
            _type_evaporation_scan_sync,
            frontend_code,
            backend_code,
            frontend_file,
            backend_file,
            enable_pro,
            enable_enterprise,
            frontend_only,
            max_files,
        )
        duration_ms = int((time.perf_counter() - started) * 1000)
        return make_envelope(
            data=result,
            tool_id="type_evaporation_scan",
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
            tool_id="type_evaporation_scan",
            tool_version=_pkg_version,
            tier=tier,
            duration_ms=duration_ms,
            error=error_obj,
        )


@mcp.tool(
    description="Check requirements/package files for known CVEs via the OSV vulnerability database."
)
@with_oracle_resilience(tool_id="scan_dependencies", strategy=PathStrategy)
async def scan_dependencies(
    path: str | None = None,
    project_root: str | None = None,
    scan_vulnerabilities: bool = True,
    include_dev: bool = True,
    timeout: float = 30.0,
    ctx: Context | None = None,
) -> ToolResponseEnvelope:
    """Scan project dependencies for known vulnerabilities.

    Analyzes project dependency manifests (package.json, requirements.txt, pom.xml, etc.)
    for known security vulnerabilities using CVE databases.

    **Tier Behavior:**
    - Community: Basic vulnerability scanning, CVE mapping only
    - Pro: All Community + license analysis, supply chain insights, automated updates
    - Enterprise: All Pro + priority scoring, compliance reports, SLA tracking

    **Tier Capabilities:**
    - Community: Vulnerabilities only (max_packages=50)
    - Pro: All Community + license and supply chain (max_packages=10000)
    - Enterprise: All Pro + compliance and SLA tracking (max_packages=unlimited)

    **Args:**
        path (str, optional): Path to scan for dependencies. If None, uses project root.
        project_root (str, optional): Project root directory. If None, uses server default.
        scan_vulnerabilities (bool): Scan for vulnerabilities. Default: True.
        include_dev (bool): Include development dependencies. Default: True.
        timeout (float): Scan timeout in seconds. Default: 30.0.
        ctx (Context, optional): MCP context for progress reporting.

    **Returns:**
        ToolResponseEnvelope with DependencyScanResult containing:
        - scanned_files (list[str]): Dependency files scanned
        - total_dependencies (int): Total number of dependencies found
        - vulnerable_count (int): Number of dependencies with vulnerabilities
        - total_vulnerabilities (int): Total number of vulnerabilities found
        - severity_summary (dict): Count by severity (critical, high, medium, low)
        - dependencies (list[dict]): All scanned dependencies with vulnerabilities
        - compliance_report (dict): Compliance report for SOC2/ISO standards (Enterprise)
        - policy_violations (list[dict]): Policy violations detected (Enterprise)
        - errors (list[dict]): Non-fatal errors/warnings encountered during scan
        - success (bool): Whether the scan completed successfully
        - error (str, optional): Error message if failed
        - error (str): Error message if scan failed
        - tier_applied (str): Tier used for scanning
        - duration_ms (int): Scan duration in milliseconds
    """
    started = time.perf_counter()
    try:
        # Import PROJECT_ROOT from server to avoid circular import issues
        server = import_module("code_scalpel.mcp.server")
        resolved_path = path or project_root or str(server.PROJECT_ROOT)
        tier = _get_current_tier()
        caps = get_tool_capabilities("scan_dependencies", tier)

        if ctx:
            await ctx.report_progress(
                0, 100, f"Scanning dependencies in {resolved_path}..."
            )

        result = await asyncio.to_thread(
            _scan_dependencies_sync,
            project_root=resolved_path,
            scan_vulnerabilities=scan_vulnerabilities,
            include_dev=include_dev,
            timeout=timeout,
            tier=tier,
            capabilities=caps,
            ctx=ctx,
        )

        if ctx:
            vuln_count = result.total_vulnerabilities
            await ctx.report_progress(
                100, 100, f"Scan complete: {vuln_count} vulnerabilities found"
            )

        duration_ms = int((time.perf_counter() - started) * 1000)
        return make_envelope(
            data=result,
            tool_id="scan_dependencies",
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
            tool_id="scan_dependencies",
            tool_version=_pkg_version,
            tier=tier,
            duration_ms=duration_ms,
            error=error_obj,
        )


@mcp.tool(
    description="Taint-based vulnerability scan for SQL injection, XSS, command injection, and path traversal."
)
@with_oracle_resilience(tool_id="security_scan", strategy=PathStrategy)
async def security_scan(
    code: Optional[str] = None,
    file_path: Optional[str] = None,
    confidence_threshold: float = 0.7,
) -> ToolResponseEnvelope:
    """Scan code for security vulnerabilities using taint analysis.

    Identifies security vulnerabilities using taint analysis and pattern matching.
    Provide either 'code' or 'file_path'. Language is auto-detected from code content.

    **Tier Behavior:**
    - Community: Basic pattern matching, CWE mapping, confidence scoring
    - Pro: All Community + taint analysis, reachability, false positive tuning, custom rules
    - Enterprise: All Pro + compliance mappings, priority ordering, remediation suggestions

    **Tier Capabilities:**
    - Community: Pattern matching only
    - Pro: All Community + taint analysis, custom patterns (max_complexity=10000)
    - Enterprise: All Pro + compliance and remediation (max_complexity=unlimited)

    **Args:**
        code (str, optional): Source code to scan. Either code or file_path required.
        file_path (str, optional): Path to file to scan. Either code or file_path required.
        confidence_threshold (float): Minimum confidence score (0.0-1.0). Default: 0.7 (70%).

    **Returns:**
        ToolResponseEnvelope with SecurityResult containing:
        - success (bool): True if scan completed successfully
        - has_vulnerabilities (bool): Whether vulnerabilities were found
        - vulnerability_count (int): Number of vulnerabilities
        - risk_level (str): Overall risk level
        - vulnerabilities (list[dict]): List with CWE, severity, location
        - taint_sources (list[str]): Identified taint sources
        - sanitizer_paths (list[dict]): Detected sanitizer usages (Pro/Enterprise)
        - confidence_scores (dict): Heuristic confidence scores per finding
        - false_positive_analysis (dict): False-positive reduction metadata
        - remediation_suggestions (list[str]): Remediation suggestions (Pro/Enterprise)
        - policy_violations (list[dict]): Custom policy violations (Enterprise)
        - compliance_mappings (dict): Compliance framework mappings (Enterprise)
        - custom_rule_results (list[dict]): Custom rule matches (Enterprise)
        - priority_ordered_findings (list[dict]): Findings sorted by priority (Enterprise)
        - reachability_analysis (dict): Vulnerability reachability analysis (Enterprise)
        - false_positive_tuning (dict): False positive tuning results (Enterprise)
        - error (str, optional): Error message if failed
        - error (str): Error message if scan failed
        - tier_applied (str): Tier used for scanning
        - duration_ms (int): Scan duration in milliseconds
    """
    started = time.perf_counter()
    try:
        tier = _get_current_tier()
        caps = get_tool_capabilities("security_scan", tier)
        result = await asyncio.to_thread(
            _security_scan_sync, code, file_path, tier, caps, confidence_threshold
        )
        duration_ms = int((time.perf_counter() - started) * 1000)
        return make_envelope(
            data=result,
            tool_id="security_scan",
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
            tool_id="security_scan",
            tool_version=_pkg_version,
            tier=tier,
            duration_ms=duration_ms,
            error=error_obj,
        )


__all__ = [
    "security_scan",
    "scan_dependencies",
    "type_evaporation_scan",
    "unified_sink_detect",
]
