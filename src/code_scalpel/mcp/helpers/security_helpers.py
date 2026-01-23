from __future__ import annotations

import ast
import asyncio
import hashlib
import json
import logging
import os
import re
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from code_scalpel.parsing import ParsingError, parse_python_code

# Fallback Levenshtein if available
try:
    from Levenshtein import distance as levenshtein_distance  # type: ignore
except Exception:  # pragma: no cover - optional dependency

    def levenshtein_distance(s1: str, s2: str) -> int:
        if len(s1) < len(s2):
            return levenshtein_distance(s2, s1)
        if len(s2) == 0:
            return len(s1)
        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        return previous_row[-1]


from mcp.server.fastmcp import Context

from code_scalpel.cache import get_cache
from code_scalpel.licensing.features import get_tool_capabilities
from code_scalpel.licensing.tier_detector import get_current_tier
from code_scalpel.mcp.models.core import (
    UnifiedDetectedSink,
    UnifiedSinkResult,
    VulnerabilityInfo,
)
from code_scalpel.mcp.models.security import (
    DependencyInfo,
    DependencyScanResult,
    DependencyVulnerability,
    SecurityResult,
    TypeEvaporationResultModel,
)
from code_scalpel.security.analyzers import SecurityAnalyzer, UnifiedSinkDetector
from code_scalpel.security.analyzers.policy_engine import PolicyEngine
from code_scalpel.security.type_safety.type_evaporation_detector import (
    TypeEvaporationDetector,
)

logger = logging.getLogger(__name__)
CACHE_ENABLED = os.environ.get("CODE_SCALPEL_CACHE_ENABLED", "1") != "0"


def _get_cache():
    if not CACHE_ENABLED:
        return None
    try:
        return get_cache()
    except ImportError:
        logging.warning("Cache module not available")
        return None


def _get_project_root() -> Path:
    """Get the server's PROJECT_ROOT dynamically.

    [20260120_BUGFIX] Import from server module to get the initialized value.
    Using a getter function ensures we get the value after main() sets it.
    """
    try:
        from code_scalpel.mcp.server import get_project_root

        return get_project_root()
    except ImportError:
        return Path.cwd()


def _get_current_tier() -> str:
    """Return the current licensing tier, defaulting to community on failure."""

    try:
        return get_current_tier()
    except Exception:
        return "community"


MAX_CODE_SIZE = 100_000


def _validate_code(code: str) -> tuple[bool, str | None]:
    """Validate code before analysis."""
    if not code:
        return False, "Code cannot be empty"
    if not isinstance(code, str):
        return False, "Code must be a string"
    if len(code) > MAX_CODE_SIZE:
        return False, f"Code exceeds maximum size of {MAX_CODE_SIZE} characters"
    return True, None


_SINK_DETECTOR = None


def _get_sink_detector() -> UnifiedSinkDetector:
    global _SINK_DETECTOR
    if _SINK_DETECTOR is None:
        _SINK_DETECTOR = UnifiedSinkDetector()
    return _SINK_DETECTOR


def validate_path_security(path: Path, project_root: Path | None = None) -> Path:
    """Validate path is within allowed roots and return resolved path.

    [20260120_BUGFIX] If project_root is None, use the server's PROJECT_ROOT.
    """
    if project_root is None:
        project_root = _get_project_root()
    try:
        resolved = path.resolve()
        root_resolved = project_root.resolve()
        # Simple check: resolved path must start with root path
        if not str(resolved).startswith(str(root_resolved)):
            raise ValueError(f"Access denied: {path} is outside project root {project_root}")
        return resolved
    except Exception as e:
        raise ValueError(f"Invalid path: {e}")


def _unified_sink_detect_sync(
    code: str,
    language: str,
    confidence_threshold: float,
    tier: str = "community",
    capabilities: dict | None = None,
) -> UnifiedSinkResult:
    """Synchronous unified sink detection wrapper.

    [20251225_FEATURE] v3.3.0 - Tier-based gating and outputs.
    """

    from code_scalpel.licensing.features import get_tool_capabilities

    lang = (language or "").lower()

    def _make_sink_id(
        *,
        pattern: str,
        sink_type: str,
        line: int,
        column: int,
        vulnerability_type: str | None,
        cwe_id: str | None,
    ) -> str:
        """Generate a stable sink id for correlation across runs."""

        raw = f"{lang}|{pattern}|{sink_type}|{line}|{column}|" f"{vulnerability_type or ''}|{cwe_id or ''}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]

    def _snippet_from_source(line_no: int) -> str:
        if line_no <= 0:
            return ""
        lines = code.splitlines()
        if 1 <= line_no <= len(lines):
            return lines[line_no - 1]
        return ""

    def _truncate_snippet(snippet: str, *, max_len: int = 200) -> tuple[str, bool, int | None]:
        if len(snippet) <= max_len:
            return snippet, False, None
        # Keep output length stable at max_len, ending with an ellipsis.
        return snippet[: max_len - 1] + "…", True, len(snippet)

    if code is None or code.strip() == "":
        return UnifiedSinkResult(
            success=False,
            error_code="UNIFIED_SINK_DETECT_MISSING_CODE",
            language=lang,
            sink_count=0,
            error="Parameter 'code' is required.",
            coverage_summary={},
        )

    if not 0.0 <= confidence_threshold <= 1.0:
        return UnifiedSinkResult(
            success=False,
            error_code="UNIFIED_SINK_DETECT_INVALID_MIN_CONFIDENCE",
            language=lang,
            sink_count=0,
            error="Parameter 'confidence_threshold' must be between 0.0 and 1.0.",
            coverage_summary={},
        )

    # Load capabilities if not provided
    if capabilities is None:
        capabilities = get_tool_capabilities("unified_sink_detect", tier) or {}
    caps_set: set[str] = set(capabilities.get("capabilities", []) or [])
    limits = capabilities.get("limits", {}) or {}

    # Enforce language limits
    allowed_langs = limits.get("languages")
    if allowed_langs is not None:
        # [20260102_REFACTOR] Avoid ambiguous loop variable names in allowlist check.
        if isinstance(allowed_langs, str):
            allowed_langs_lower = [allowed_langs.lower()]
        else:
            allowed_langs_lower = [str(allowed).lower() for allowed in allowed_langs]

        if allowed_langs_lower and allowed_langs_lower != ["all"]:
            if lang not in allowed_langs_lower:
                return UnifiedSinkResult(
                    success=False,
                    error_code="UNIFIED_SINK_DETECT_UNSUPPORTED_LANGUAGE",
                    language=lang,
                    sink_count=0,
                    error=f"Unsupported language for tier {tier.title()}: {language}",
                    coverage_summary={},
                )

    # [20251220_PERF] v3.0.5 - Use singleton detector to avoid rebuilding patterns
    detector = _get_sink_detector()
    try:
        detected = detector.detect_sinks(code, lang, confidence_threshold)
    except ValueError as e:
        msg = str(e)
        lower_msg = msg.lower()
        if "unsupported" in lower_msg and "language" in lower_msg:
            error_code = "UNIFIED_SINK_DETECT_UNSUPPORTED_LANGUAGE"
        else:
            error_code = "UNIFIED_SINK_DETECT_DETECTOR_ERROR"
        return UnifiedSinkResult(
            success=False,
            error_code=error_code,
            language=lang,
            sink_count=0,
            error=msg,
            coverage_summary=_sink_coverage_summary(detector),
        )

    # Build base sinks
    sinks: list[UnifiedDetectedSink] = []
    for sink in detected:
        owasp = detector.get_owasp_category(sink.vulnerability_type)
        # [20251231_FEATURE] v1.0 - Map CWE from vulnerability type
        cwe_id = _get_cwe_for_sink(sink.vulnerability_type, sink.sink_type)

        sink_type = getattr(sink.sink_type, "name", str(sink.sink_type))
        line = int(getattr(sink, "line", 0) or 0)
        column = int(getattr(sink, "column", 0) or 0)
        vulnerability_type = getattr(sink, "vulnerability_type", None)

        raw_snippet = getattr(sink, "code_snippet", "") or _snippet_from_source(line)
        code_snippet, snippet_truncated, original_len = _truncate_snippet(raw_snippet)
        sinks.append(
            UnifiedDetectedSink(
                sink_id=_make_sink_id(
                    pattern=sink.pattern,
                    sink_type=sink_type,
                    line=line,
                    column=column,
                    vulnerability_type=vulnerability_type,
                    cwe_id=cwe_id,
                ),
                pattern=sink.pattern,
                sink_type=sink_type,
                confidence=sink.confidence,
                line=line,
                column=column,
                code_snippet=code_snippet,
                code_snippet_truncated=snippet_truncated,
                code_snippet_original_len=original_len,
                vulnerability_type=vulnerability_type,
                owasp_category=owasp,
                cwe_id=cwe_id,
            )
        )

    # Enforce max_sinks limit
    max_sinks = limits.get("max_sinks")
    truncated: bool | None = None
    sinks_detected: int | None = None
    max_sinks_applied: int | None = None
    if max_sinks is not None and len(sinks) > max_sinks:
        sinks_detected = len(sinks)
        sinks = sinks[:max_sinks]
        truncated = True
        max_sinks_applied = int(max_sinks)

    # Tier-specific enrichments
    logic_sinks: list[dict[str, Any]] = []
    confidence_scores: dict[str, float] = {}
    sink_categories: dict[str, list[dict[str, Any]]] = {}
    risk_assessments: list[dict[str, Any]] = []
    custom_sink_matches: list[dict[str, Any]] = []
    extended_language_sinks: dict[str, list[dict[str, Any]]] = {}

    def _line_lookup(patterns: list[str]) -> int:
        for idx, line_text in enumerate(code.splitlines(), start=1):
            for p in patterns:
                if p in line_text:
                    return idx
        return 0

    # Pro/Enterprise: Logic sinks
    if "logic_sink_detection" in caps_set:
        if "s3_public_write_detection" in caps_set and "put_object" in code:
            logic_sinks.append(
                {
                    "type": "S3_PUBLIC_WRITE",
                    "line": _line_lookup(["put_object"]),
                    "confidence": 0.8,
                    "recommendation": "Avoid public-read ACL; use private bucket policies.",
                }
            )
        if "payment_api_detection" in caps_set and "stripe" in code:
            logic_sinks.append(
                {
                    "type": "PAYMENT_STRIPE",
                    "line": _line_lookup(["stripe"]),
                    "confidence": 0.82,
                    "recommendation": "Validate payment inputs and use secure tokens.",
                }
            )
        if "email_send_detection" in caps_set and ("SendGridAPIClient" in code or "mail.send" in code):
            logic_sinks.append(
                {
                    "type": "EMAIL_SEND",
                    "line": _line_lookup(["SendGridAPIClient", "mail.send"]),
                    "confidence": 0.75,
                    "recommendation": "Sanitize email content and enforce rate limits.",
                }
            )

    # Confidence scoring (Pro/Enterprise)
    if "sink_confidence_scoring" in caps_set or "logic_sink_detection" in caps_set:
        for sink in sinks:
            key = sink.sink_id
            base = sink.confidence or confidence_threshold
            multiplier = 1.0
            vuln = (sink.vulnerability_type or sink.sink_type or "").upper()
            if "SQL" in vuln:
                multiplier = 0.95
            elif "XSS" in vuln:
                multiplier = 0.85
            confidence_scores[key] = max(0.0, min(1.0, base * multiplier))

    # Enterprise: Custom sink patterns
    if "custom_sink_patterns" in caps_set:
        patterns = {
            "CUSTOM_INTERNAL_API": "internal_api_call",
            "CUSTOM_LEGACY_EXECUTE": "legacy_system.execute",
            "CUSTOM_PRIVILEGED_OPERATION": "privileged_operation",
        }
        for ctype, marker in patterns.items():
            if marker in code:
                custom_sink_matches.append(
                    {
                        "type": ctype,
                        "line": _line_lookup([marker]),
                        "confidence": 0.8,
                        "recommendation": "Review custom sink usage and enforce input validation.",
                    }
                )

    # Enterprise: Categorization and risk assessments
    if "sink_categorization" in caps_set or "risk_level_tagging" in caps_set:
        sink_categories = {"critical": [], "high": [], "medium": [], "low": []}
        for sink in sinks:
            vuln = (sink.vulnerability_type or sink.sink_type or "").upper()
            if "SQL" in vuln:
                category = "critical"
            elif "COMMAND" in vuln or "SHELL" in vuln:
                category = "high"
            elif "XSS" in vuln:
                category = "medium"
            else:
                category = "low"
            sink_categories[category].append(
                {
                    "sink_id": sink.sink_id,
                    "type": vuln,
                    "confidence": confidence_scores.get(sink.sink_id, sink.confidence),
                }
            )

    if "risk_level_tagging" in caps_set:
        # Simple risk scoring based on counts
        critical = len(sink_categories.get("critical", []))
        high = len(sink_categories.get("high", []))
        medium = len(sink_categories.get("medium", []))
        base_score = 10.0 - (critical * 2.5 + high * 1.5 + medium * 0.5)
        base_score = max(0.0, min(10.0, base_score))
        clearance = "ANY"
        if critical > 0:
            clearance = "ADMIN_ONLY"
        elif high > 0:
            clearance = "SENIOR_DEV"
        elif medium > 0:
            clearance = "DEVELOPER"
        risk_assessments.append(
            {
                "risk_score": base_score,
                "clearance_required": clearance,
                "rationale": "Calculated from categorized sinks",
            }
        )

    # Extended language support marker (informational)
    if "extended_language_support" in caps_set and allowed_langs:
        extended_language_sinks[lang] = [s.model_dump() for s in sinks]

    # [20251231_FEATURE] v1.0 - New Pro/Enterprise features
    context_analysis: dict[str, Any] | None = None
    framework_sinks: list[dict[str, Any]] = []
    compliance_mapping: dict[str, Any] | None = None
    historical_comparison: dict[str, Any] | None = None
    remediation_suggestions: list[dict[str, Any]] = []

    # Pro: Context-aware detection
    if "context_aware_detection" in caps_set:
        context_analysis = _analyze_sink_context(code, sinks, lang)

    # Pro: Framework-specific sinks
    if "framework_specific_sinks" in caps_set:
        framework_sinks = _detect_framework_sinks(code, lang)

    # Enterprise: Compliance mapping
    if "compliance_mapping" in caps_set:
        compliance_mapping = _build_sink_compliance_mapping(sinks)

    # Enterprise: Historical tracking (placeholder - requires persistent storage)
    if "historical_sink_tracking" in caps_set:
        historical_comparison = _build_historical_comparison(sinks)

    # Enterprise: Automated remediation
    if "automated_sink_remediation" in caps_set:
        remediation_suggestions = _generate_sink_remediation(sinks, lang)

    return UnifiedSinkResult(
        success=True,
        language=lang,
        sink_count=len(sinks),
        sinks=sinks,
        coverage_summary=_sink_coverage_summary(detector),
        logic_sinks=logic_sinks,
        extended_language_sinks=extended_language_sinks,
        confidence_scores=confidence_scores,
        sink_categories=sink_categories,
        risk_assessments=risk_assessments,
        custom_sink_matches=custom_sink_matches,
        # [20251231_FEATURE] v1.0 - New fields
        context_analysis=context_analysis,
        framework_sinks=framework_sinks,
        compliance_mapping=compliance_mapping,
        historical_comparison=historical_comparison,
        remediation_suggestions=remediation_suggestions,
        truncated=truncated,
        sinks_detected=sinks_detected,
        max_sinks_applied=max_sinks_applied,
    )


def _sink_coverage_summary(detector: UnifiedSinkDetector) -> dict[str, Any]:
    """Compute coverage summary across languages."""

    by_language: dict[str, int] = {}
    total_patterns = 0

    for vuln_sinks in detector.sinks.values():
        for lang, sink_list in vuln_sinks.items():
            by_language[lang] = by_language.get(lang, 0) + len(sink_list)
            total_patterns += len(sink_list)

    return {
        "total_patterns": total_patterns,
        "by_language": by_language,
    }


def _get_cwe_from_sink_type(sink_type) -> str:
    """[20251220_FEATURE] v3.0.4 - Map sink types to CWE IDs.
    [20251220_FIX] v3.0.5 - Added more sink types, fallback to CWE-20 instead of Unknown.
    """
    cwe_map = {
        "SQL_QUERY": "89",
        "HTML_OUTPUT": "79",
        "DOM_XSS": "79",
        "FILE_PATH": "22",
        "SHELL_COMMAND": "78",
        "EVAL": "94",
        "DESERIALIZATION": "502",
        "XXE": "611",
        "SSRF": "918",
        "SSTI": "1336",
        "WEAK_CRYPTO": "327",
        "PROTOTYPE_POLLUTION": "1321",
        "HARDCODED_SECRET": "798",
        "LDAP_QUERY": "90",
        "NOSQL_QUERY": "943",
        "XPATH_QUERY": "643",
        "LOG_INJECTION": "117",
        "HTTP_REDIRECT": "601",
        "REGEX_DOS": "1333",
    }
    sink_name = getattr(sink_type, "name", str(sink_type))
    return cwe_map.get(sink_name, "20")


def _get_cwe_for_sink(vulnerability_type: str | None, sink_type: Any) -> str | None:
    """Map vulnerability/sink type to CWE identifier."""
    vuln = (vulnerability_type or str(sink_type) or "").upper()
    cwe_mapping = {
        "SQL": "CWE-89",  # SQL Injection
        "COMMAND": "CWE-78",  # OS Command Injection
        "SHELL": "CWE-78",
        "EVAL": "CWE-94",  # Code Injection
        "EXEC": "CWE-94",
        "XSS": "CWE-79",  # Cross-site Scripting
        "PATH": "CWE-22",  # Path Traversal
        "FILE": "CWE-73",  # External Control of File Name
        "LDAP": "CWE-90",  # LDAP Injection
        "XML": "CWE-91",  # XML Injection
        "XPATH": "CWE-643",  # XPath Injection
        "DESERIALIZATION": "CWE-502",  # Deserialization
        "SSRF": "CWE-918",  # Server-Side Request Forgery
        "REDIRECT": "CWE-601",  # Open Redirect
        "LOG": "CWE-117",  # Log Injection
        "PROTOTYPE": "CWE-1321",
        "HARDCODED": "CWE-798",
        "NOSQL": "CWE-943",
        "HTTP": "CWE-601",
        "REGEX": "CWE-1333",
    }

    for key, cwe in cwe_mapping.items():
        if key in vuln:
            return cwe

    return None


def _analyze_sink_context(
    code: str,
    sinks: list[UnifiedDetectedSink],
    language: str,
) -> dict[str, Any]:
    """
    [20251231_FEATURE] Analyze context around detected sinks for Pro tier.

    Determines if sinks are in dangerous contexts (user input handling,
    request processing, etc.)
    """
    lines = code.splitlines()

    # Context patterns that indicate higher risk
    high_risk_patterns = {
        "python": ["request.", "input(", "sys.argv", "os.environ", "flask.request"],
        "javascript": [
            "req.body",
            "req.query",
            "req.params",
            "document.",
            "window.location",
        ],
        "typescript": [
            "req.body",
            "req.query",
            "req.params",
            "document.",
            "window.location",
        ],
        "java": ["getParameter", "getHeader", "getInputStream", "Scanner"],
    }

    patterns = high_risk_patterns.get(language.lower(), [])

    context_results: dict[str, Any] = {
        "analyzed_sinks": 0,
        "high_risk_context": 0,
        "medium_risk_context": 0,
        "low_risk_context": 0,
        "details": [],
    }

    for sink in sinks:
        context_results["analyzed_sinks"] += 1

        # Check surrounding lines for context
        start_line = max(0, sink.line - 5)
        end_line = min(len(lines), sink.line + 5)
        context_window = "\n".join(lines[start_line:end_line])

        # Determine risk level based on context
        risk = "low"
        risk_reason = "No immediate user input detected"

        for pattern in patterns:
            if pattern in context_window:
                risk = "high"
                risk_reason = f"User input pattern '{pattern}' found in context"
                break

        if risk == "low" and ("param" in context_window.lower() or "input" in context_window.lower()):
            risk = "medium"
            risk_reason = "Potential input handling detected"

        if risk == "high":
            context_results["high_risk_context"] += 1
        elif risk == "medium":
            context_results["medium_risk_context"] += 1
        else:
            context_results["low_risk_context"] += 1

        context_results["details"].append(
            {
                "line": sink.line,
                "sink_type": sink.sink_type,
                "context_risk": risk,
                "reason": risk_reason,
            }
        )

    return context_results


def _detect_framework_sinks(code: str, language: str) -> list[dict[str, Any]]:
    """
    [20251231_FEATURE] Detect framework-specific sinks for Pro tier.
    """
    framework_sinks: list[dict[str, Any]] = []

    # Framework-specific dangerous patterns
    frameworks = {
        "python": {
            "flask": {
                "patterns": ["render_template_string", "make_response", "send_file"],
                "risk": "Template injection or file exposure",
            },
            "django": {
                "patterns": ["mark_safe", "SafeString", "format_html"],
                "risk": "XSS through unsafe HTML marking",
            },
            "sqlalchemy": {
                "patterns": ["text(", "execute("],
                "risk": "Raw SQL execution",
            },
        },
        "javascript": {
            "express": {
                "patterns": ["res.send(", "res.render(", "res.sendFile("],
                "risk": "Response injection or file exposure",
            },
            "react": {
                "patterns": ["dangerouslySetInnerHTML", "__html"],
                "risk": "XSS through raw HTML insertion",
            },
        },
        "java": {
            "spring": {
                "patterns": ["@RequestMapping", "ResponseEntity", "JdbcTemplate"],
                "risk": "Web exposure or SQL execution",
            },
        },
    }

    lang_frameworks = frameworks.get(language.lower(), {})

    for framework, config in lang_frameworks.items():
        for pattern in config["patterns"]:
            for i, line in enumerate(code.splitlines(), 1):
                if pattern in line:
                    framework_sinks.append(
                        {
                            "framework": framework,
                            "pattern": pattern,
                            "line": i,
                            "risk_description": config["risk"],
                            "code_snippet": line.strip()[:80],
                        }
                    )

    return framework_sinks


def _build_sink_compliance_mapping(sinks: list[UnifiedDetectedSink]) -> dict[str, Any]:
    """
    [20251231_FEATURE] Map sinks to compliance standards for Enterprise tier.
    """
    compliance: dict[str, Any] = {
        "standards_affected": [],
        "violations": [],
        "recommendations": [],
    }

    # Compliance mappings
    compliance_rules = {
        "CWE-89": {  # SQL Injection
            "standards": ["SOC2", "PCI-DSS", "HIPAA"],
            "requirement": "Input validation and parameterized queries required",
        },
        "CWE-78": {  # Command Injection
            "standards": ["SOC2", "PCI-DSS"],
            "requirement": "Command execution must be sandboxed or avoided",
        },
        "CWE-79": {  # XSS
            "standards": ["SOC2", "OWASP"],
            "requirement": "Output encoding required for user-facing content",
        },
        "CWE-94": {  # Code Injection
            "standards": ["SOC2", "PCI-DSS", "HIPAA"],
            "requirement": "Dynamic code execution prohibited without strict controls",
        },
        "CWE-502": {  # Deserialization
            "standards": ["SOC2", "PCI-DSS"],
            "requirement": "Avoid deserializing untrusted data",
        },
    }

    standards_set: set[str] = set()

    for sink in sinks:
        cwe = sink.cwe_id
        if cwe and cwe in compliance_rules:
            rule = compliance_rules[cwe]
            standards_set.update(rule["standards"])

            compliance["violations"].append(
                {
                    "cwe": cwe,
                    "line": sink.line,
                    "sink_type": sink.sink_type,
                    "standards_violated": rule["standards"],
                    "requirement": rule["requirement"],
                }
            )

    compliance["standards_affected"] = list(standards_set)

    # Generate recommendations
    if "PCI-DSS" in standards_set:
        compliance["recommendations"].append(
            "PCI-DSS: Implement input validation and output encoding per Requirement 6.5"
        )
    if "HIPAA" in standards_set:
        compliance["recommendations"].append("HIPAA: Ensure PHI access controls meet Technical Safeguard requirements")
    if "SOC2" in standards_set:
        compliance["recommendations"].append("SOC2: Address security vulnerabilities per CC6.1 control requirements")

    return compliance


def _build_historical_comparison(sinks: list[UnifiedDetectedSink]) -> dict[str, Any]:
    """
    [20251231_FEATURE] Build historical comparison for Enterprise tier.

    Note: Full historical tracking requires persistent storage.
    This provides a snapshot structure for integration.
    """
    return {
        "current_scan": {
            "timestamp": __import__("datetime").datetime.now().isoformat(),
            "total_sinks": len(sinks),
            "by_severity": {
                "critical": sum(1 for s in sinks if "SQL" in (s.sink_type or "").upper()),
                "high": sum(
                    1
                    for s in sinks
                    if "COMMAND" in (s.sink_type or "").upper() or "SHELL" in (s.sink_type or "").upper()
                ),
                "medium": sum(1 for s in sinks if "XSS" in (s.sink_type or "").upper()),
                "low": len(sinks)
                - sum(
                    1
                    for s in sinks
                    if any(k in (s.sink_type or "").upper() for k in ["SQL", "COMMAND", "SHELL", "XSS"])
                ),
            },
        },
        "comparison_available": False,
        "message": "Historical data requires persistent storage integration",
        "integration_hint": "Connect to sink_history table or external tracking service",
    }


def _generate_sink_remediation(
    sinks: list[UnifiedDetectedSink],
    language: str,
) -> list[dict[str, Any]]:
    """
    [20251231_FEATURE] Generate automated remediation suggestions for Enterprise tier.
    """
    remediation: list[dict[str, Any]] = []

    # Remediation templates by CWE
    remediation_templates = {
        "CWE-89": {
            "title": "SQL Injection Prevention",
            "python": "Use parameterized queries: cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))",
            "javascript": "Use prepared statements: db.query('SELECT * FROM users WHERE id = $1', [userId])",
            "java": 'Use PreparedStatement: stmt = conn.prepareStatement("SELECT * FROM users WHERE id = ?"); stmt.setInt(1, userId);',
            "priority": "critical",
        },
        "CWE-78": {
            "title": "Command Injection Prevention",
            "python": "Use subprocess with list args: subprocess.run(['ls', '-la', user_path], shell=False)",
            "javascript": "Use execFile instead of exec: execFile('ls', ['-la', userPath])",
            "java": 'Use ProcessBuilder with argument list: new ProcessBuilder("ls", "-la", userPath)',
            "priority": "critical",
        },
        "CWE-79": {
            "title": "XSS Prevention",
            "python": "Use template auto-escaping or markupsafe.escape(user_input)",
            "javascript": "Use textContent instead of innerHTML: element.textContent = userInput",
            "java": "Use OWASP Encoder: Encode.forHtml(userInput)",
            "priority": "high",
        },
        "CWE-94": {
            "title": "Code Injection Prevention",
            "python": "Avoid eval/exec. Use ast.literal_eval() for safe parsing",
            "javascript": "Avoid eval(). Use JSON.parse() for data parsing",
            "java": "Avoid ScriptEngine with user input. Use predefined operations",
            "priority": "critical",
        },
    }

    lang_key = language.lower()

    for sink in sinks:
        cwe = sink.cwe_id
        if cwe and cwe in remediation_templates:
            template = remediation_templates[cwe]
            fix = template.get(lang_key, template.get("python", "Review and sanitize input"))

            remediation.append(
                {
                    "line": sink.line,
                    "sink_type": sink.sink_type,
                    "cwe": cwe,
                    "title": template["title"],
                    "priority": template["priority"],
                    "suggested_fix": fix,
                    "code_example": f"// Before: {sink.code_snippet[:50]}...\n// After: {fix}",
                }
            )

    return remediation


def _analyze_reachability(project_root: Path) -> set[str]:
    """
    Analyze Python files to find imported packages.

    [20251229_FEATURE] v3.3.1 - Pro tier reachability analysis.
    """
    imported_packages: set[str] = set()
    ignore_dirs = {
        ".venv",
        "venv",
        "node_modules",
        ".git",
        "__pycache__",
        "build",
        "dist",
        ".tox",
        ".pytest_cache",
    }

    for py_file in project_root.rglob("*.py"):
        if any(ignore_dir in py_file.parts for ignore_dir in ignore_dirs):
            continue

        try:
            content = py_file.read_text(encoding="utf-8", errors="ignore")
            # [20260119_FEATURE] Use unified parser for deterministic behavior
            tree, _ = parse_python_code(content, filename=str(py_file))

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        package = alias.name.split(".")[0]
                        imported_packages.add(package)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        package = node.module.split(".")[0]
                        imported_packages.add(package)
        except (ParsingError, UnicodeDecodeError, OSError):
            # Skip unparseable files (existing behavior preserved)
            continue

    return imported_packages


def _fetch_package_license(package_name: str, ecosystem: str) -> str | None:
    """
    Fetch license information from package registries.

    [20251229_FEATURE] v3.3.1 - Enterprise tier license compliance.
    """
    try:
        if ecosystem.lower() == "pypi":
            url = f"https://pypi.org/pypi/{package_name}/json"
            parsed = urllib.parse.urlparse(url)
            if parsed.scheme not in {"http", "https"}:
                raise ValueError(f"Unsupported registry scheme: {parsed.scheme}")
            with urllib.request.urlopen(url, timeout=5) as response:  # nosec B310
                data = json.loads(response.read().decode())
                return data.get("info", {}).get("license") or "Unknown"
        elif ecosystem.lower() == "npm":
            url = f"https://registry.npmjs.org/{package_name}/latest"
            parsed = urllib.parse.urlparse(url)
            if parsed.scheme not in {"http", "https"}:
                raise ValueError(f"Unsupported registry scheme: {parsed.scheme}")
            with urllib.request.urlopen(url, timeout=5) as response:  # nosec B310
                data = json.loads(response.read().decode())
                license_info = data.get("license")
                if isinstance(license_info, dict):
                    return license_info.get("type", "Unknown")
                return str(license_info) if license_info else "Unknown"
    except Exception:
        pass

    return None


def _check_license_compliance(license_str: str | None) -> bool:
    """Check if license complies with organization policy."""
    if not license_str or license_str == "Unknown":
        return False

    permissive_licenses = {
        "mit",
        "apache",
        "bsd",
        "isc",
        "0bsd",
        "wtfpl",
        "apache-2.0",
        "apache 2.0",
        "bsd-3-clause",
        "bsd-2-clause",
        "cc0",
        "unlicense",
        "zlib",
        "mpl-2.0",
    }
    copyleft_licenses = {"gpl", "lgpl", "agpl", "gpl-3.0", "lgpl-3.0", "agpl-3.0"}

    license_lower = license_str.lower()

    if any(perm in license_lower for perm in permissive_licenses):
        return True
    if any(copy in license_lower for copy in copyleft_licenses):
        return False

    return False


def _check_typosquatting(package_name: str, ecosystem: str) -> bool:
    """
    Check for potential typosquatting by comparing against popular packages.

    [20251229_FEATURE] v3.3.1 - Enterprise tier typosquatting detection.
    """
    popular_packages = {
        "pypi": {
            "requests",
            "urllib3",
            "certifi",
            "setuptools",
            "pip",
            "wheel",
            "numpy",
            "pandas",
            "scipy",
            "matplotlib",
            "django",
            "flask",
            "pytest",
            "boto3",
            "sqlalchemy",
            "pillow",
            "cryptography",
            "beautifulsoup4",
            "lxml",
            "pyyaml",
            "click",
            "jinja2",
        },
        "npm": {
            "react",
            "lodash",
            "express",
            "axios",
            "webpack",
            "babel",
            "typescript",
            "eslint",
            "prettier",
            "jest",
            "moment",
            "chalk",
            "commander",
            "async",
            "request",
            "underscore",
            "jquery",
            "vue",
        },
    }

    target_packages = popular_packages.get(ecosystem.lower(), set())
    if not target_packages:
        return False

    package_lower = package_name.lower()
    if package_lower in target_packages:
        return False

    for popular_pkg in target_packages:
        distance = levenshtein_distance(package_lower, popular_pkg)
        if 0 < distance <= 2 and len(package_lower) > 3:
            return True

    return False


def _calculate_supply_chain_risk(
    package_name: str,
    version: str,
    ecosystem: str,
    vulnerabilities: list,
    is_imported: bool | None,
    typosquatting_risk: bool | None,
    license_compliant: bool | None,
) -> tuple[float, list[str]]:
    """Calculate supply chain risk score for a dependency."""
    risk_score = 0.0
    risk_factors: list[str] = []

    if vulnerabilities:
        vuln_score = 0.0
        severity_weights = {"CRITICAL": 0.5, "HIGH": 0.3, "MEDIUM": 0.15, "LOW": 0.05}
        for vuln in vulnerabilities:
            severity = getattr(vuln, "severity", "UNKNOWN")
            vuln_score += severity_weights.get(severity, 0.1)
        vuln_score = min(vuln_score, 0.5)
        risk_score += vuln_score
        risk_factors.append(f"{len(vulnerabilities)} vulnerabilities detected")

    if typosquatting_risk:
        risk_score += 0.3
        risk_factors.append("Potential typosquatting detected")

    if license_compliant is False:
        risk_score += 0.1
        risk_factors.append("License compliance issue")

    if version in ("*", "", "latest", "^", "~"):
        risk_score += 0.05
        risk_factors.append("Unpinned/floating version")

    if is_imported is False and vulnerabilities:
        risk_score *= 0.5
        risk_factors.append("Vulnerability may be unreachable (not imported)")

    risk_score = min(max(risk_score, 0.0), 1.0)
    return round(risk_score, 3), risk_factors


def _generate_compliance_report(
    dependencies: list,
    severity_summary: dict[str, int],
    total_vulnerabilities: int,
    vulnerable_count: int,
) -> dict[str, Any]:
    """Generate compliance report for SOC2/ISO standards."""
    license_issues = sum(1 for d in dependencies if hasattr(d, "license_compliant") and d.license_compliant is False)
    typosquat_risks = sum(1 for d in dependencies if hasattr(d, "typosquatting_risk") and d.typosquatting_risk is True)

    compliance_score = 100.0
    compliance_score -= severity_summary.get("CRITICAL", 0) * 20
    compliance_score -= severity_summary.get("HIGH", 0) * 10
    compliance_score -= severity_summary.get("MEDIUM", 0) * 5
    compliance_score -= license_issues * 5
    compliance_score -= typosquat_risks * 15
    compliance_score = max(compliance_score, 0.0)

    if compliance_score >= 90:
        status = "COMPLIANT"
    elif compliance_score >= 70:
        status = "NEEDS_ATTENTION"
    else:
        status = "NON_COMPLIANT"

    return {
        "generated_at": __import__("datetime").datetime.now().isoformat(),
        "compliance_score": round(compliance_score, 1),
        "status": status,
        "total_dependencies": len(dependencies),
        "vulnerable_dependencies": vulnerable_count,
        "total_vulnerabilities": total_vulnerabilities,
        "severity_breakdown": severity_summary,
        "license_issues": license_issues,
        "typosquatting_risks": typosquat_risks,
        "frameworks": ["SOC2", "ISO27001"],
        "recommendations": _generate_compliance_recommendations(severity_summary, license_issues, typosquat_risks),
    }


def _generate_compliance_recommendations(
    severity_summary: dict[str, int],
    license_issues: int,
    typosquat_risks: int,
) -> list[str]:
    """Generate prioritized compliance recommendations."""
    recommendations = []

    if severity_summary.get("CRITICAL", 0) > 0:
        recommendations.append(f"URGENT: Remediate {severity_summary['CRITICAL']} critical vulnerabilities immediately")
    if severity_summary.get("HIGH", 0) > 0:
        recommendations.append(f"HIGH PRIORITY: Address {severity_summary['HIGH']} high-severity vulnerabilities")
    if typosquat_risks > 0:
        recommendations.append(f"SECURITY: Review {typosquat_risks} packages flagged for potential typosquatting")
    if license_issues > 0:
        recommendations.append(f"LEGAL: Review {license_issues} packages with license compliance issues")
    if severity_summary.get("MEDIUM", 0) > 0:
        recommendations.append(f"Plan remediation for {severity_summary['MEDIUM']} medium-severity vulnerabilities")
    if not recommendations:
        recommendations.append("No immediate action required - continue regular monitoring")

    return recommendations


def _extract_severity(vuln: dict[str, Any]) -> str:
    """Extract severity from OSV vulnerability data."""
    if "database_specific" in vuln:
        db_severity = vuln["database_specific"].get("severity", "")
        if db_severity:
            severity_map = {
                "CRITICAL": "CRITICAL",
                "HIGH": "HIGH",
                "MODERATE": "MEDIUM",
                "MEDIUM": "MEDIUM",
                "LOW": "LOW",
            }
            return severity_map.get(db_severity.upper(), "UNKNOWN")

    if "severity" in vuln:
        for sev in vuln.get("severity", []):
            if sev.get("type") == "CVSS_V3":
                score_str = sev.get("score", "")
                try:
                    if "/" in score_str:
                        pass
                    else:
                        score = float(score_str)
                        if score >= 9.0:
                            return "CRITICAL"
                        elif score >= 7.0:
                            return "HIGH"
                        elif score >= 4.0:
                            return "MEDIUM"
                        else:
                            return "LOW"
                except (ValueError, TypeError):
                    pass

    if "ecosystem_specific" in vuln:
        eco_severity = vuln["ecosystem_specific"].get("severity", "")
        if eco_severity.upper() in ("CRITICAL", "HIGH", "MEDIUM", "MODERATE", "LOW"):
            return "MEDIUM" if eco_severity.upper() == "MODERATE" else eco_severity.upper()

    return "UNKNOWN"


def _extract_fixed_version(vuln: dict[str, Any], package_name: str) -> str | None:
    """Extract fixed version from OSV vulnerability data."""
    for affected in vuln.get("affected", []):
        if affected.get("package", {}).get("name") == package_name:
            for rng in affected.get("ranges", []):
                for event in rng.get("events", []):
                    if "fixed" in event:
                        return event["fixed"]
    return None


def _scan_dependencies_sync(
    project_root: str | None = None,
    path: str | None = None,
    scan_vulnerabilities: bool = True,
    include_dev: bool = True,
    timeout: float = 30.0,
    tier: str | None = None,
    capabilities: dict | None = None,
    ctx: Context | None = None,
) -> DependencyScanResult:
    """
    Synchronous implementation of dependency vulnerability scanning.

    [20251219_FEATURE] v3.0.4 - A06 Vulnerable Components
    [20251220_FIX] v3.0.5 - Added timeout parameter for OSV API calls
    [20251220_FEATURE] v3.0.5 - Returns DependencyScanResult with per-dependency tracking
    [20251229_FEATURE] v3.3.1 - Added tier enforcement and advanced features
    """
    tier = tier or _get_current_tier()
    caps = capabilities or get_tool_capabilities("scan_dependencies", tier)
    caps_set = set(caps.get("capabilities", set()) or [])
    limits = caps.get("limits", {}) or {}
    resolved_path_str = project_root or path or str(_get_project_root())

    try:
        from code_scalpel.security.dependencies import (
            DependencyParser,
            VulnerabilityScanner,
        )

        try:
            resolved_path = Path(resolved_path_str)
        except TypeError as exc:
            return DependencyScanResult(success=False, error=f"Invalid path: {exc}")

        if not resolved_path.is_absolute():
            resolved_path = _get_project_root() / resolved_path_str

        if not resolved_path.exists():
            return DependencyScanResult(
                success=False,
                error=f"Path not found: {resolved_path_str}",
            )

        all_deps: list[Any] = []
        errors: list[str] = []

        if resolved_path.is_file():
            try:
                if resolved_path.name == "requirements.txt":
                    all_deps = DependencyParser.parse_requirements_txt(resolved_path)
                elif resolved_path.name == "pyproject.toml":
                    all_deps = DependencyParser.parse_pyproject_toml(resolved_path)
                elif resolved_path.name == "package.json":
                    all_deps = DependencyParser.parse_package_json(resolved_path)
                elif resolved_path.name == "pom.xml":
                    all_deps = DependencyParser.parse_pom_xml(resolved_path)
                elif resolved_path.name == "build.gradle":
                    all_deps = DependencyParser.parse_build_gradle(resolved_path)
            except Exception as e:
                errors.append(f"Failed to parse {resolved_path}: {str(e)}")
        else:
            dep_files = [
                ("requirements.txt", DependencyParser.parse_requirements_txt),
                ("pyproject.toml", DependencyParser.parse_pyproject_toml),
                ("package.json", DependencyParser.parse_package_json),
                ("pom.xml", DependencyParser.parse_pom_xml),
                ("build.gradle", DependencyParser.parse_build_gradle),
            ]

            for filename, parser in dep_files:
                # [20260116_BUGFIX] Cooperative cancellation for dependency scanning.
                if ctx:
                    if hasattr(ctx, "should_cancel") and ctx.should_cancel():  # type: ignore[attr-defined]
                        raise asyncio.CancelledError("Dependency scan cancelled by user")
                    if (
                        hasattr(ctx, "request_context")
                        and hasattr(ctx.request_context, "lifecycle_context")
                        and ctx.request_context.lifecycle_context.is_cancelled  # type: ignore[attr-defined]
                    ):
                        raise asyncio.CancelledError("Dependency scan cancelled by user")
                file_path = resolved_path / filename
                if file_path.exists():
                    try:
                        parsed_deps = parser(file_path)
                        # [20260118_FIX] Track source file for each dependency
                        for dep in parsed_deps:
                            dep.file_path = str(file_path)  # type: ignore[attr-defined]
                        all_deps.extend(parsed_deps)
                    except Exception as e:
                        errors.append(f"Failed to parse {filename}: {str(e)}")

        if not include_dev:
            all_deps = [d for d in all_deps if not getattr(d, "is_dev", False)]

        max_dependencies = limits.get("max_dependencies")
        original_count = len(all_deps)
        if max_dependencies is not None and max_dependencies > 0:
            if len(all_deps) > max_dependencies:
                all_deps = all_deps[:max_dependencies]
                errors.append(
                    f"Dependency count ({original_count}) exceeds tier limit "
                    f"({max_dependencies}). Only first {max_dependencies} analyzed."
                )

        dependency_infos: list[DependencyInfo] = []
        severity_summary: dict[str, int] = {}
        total_vulns = 0
        vulnerable_count = 0

        imported_packages: set[str] = set()
        if "reachability_analysis" in caps_set and resolved_path.is_dir():
            imported_packages = _analyze_reachability(resolved_path)

        vuln_map: dict[str, list[dict[str, Any]]] = {}
        if scan_vulnerabilities and all_deps:
            try:
                with VulnerabilityScanner(timeout=timeout) as scanner:
                    vuln_map = scanner.osv_client.query_batch(all_deps)
            except Exception as e:
                errors.append(f"OSV query failed: {str(e)}")

        for dep in all_deps:
            # [20260116_BUGFIX] Cooperative cancellation during dependency analysis.
            if ctx:
                if hasattr(ctx, "should_cancel") and ctx.should_cancel():  # type: ignore[attr-defined]
                    raise asyncio.CancelledError("Dependency scan cancelled by user")
                if (
                    hasattr(ctx, "request_context")
                    and hasattr(ctx.request_context, "lifecycle_context")
                    and ctx.request_context.lifecycle_context.is_cancelled  # type: ignore[attr-defined]
                ):
                    raise asyncio.CancelledError("Dependency scan cancelled by user")
            dep_vulns: list[DependencyVulnerability] = []
            dep_key = f"{dep.name}@{dep.version}"

            if dep_key in vuln_map:
                for vuln in vuln_map[dep_key]:
                    severity = _extract_severity(vuln)
                    fixed = _extract_fixed_version(vuln, dep.name)

                    dep_vulns.append(
                        DependencyVulnerability(
                            id=vuln.get("id", "UNKNOWN"),
                            summary=vuln.get("summary", ""),
                            severity=severity,
                            package=dep.name,
                            vulnerable_version=dep.version,
                            fixed_version=fixed,
                        )
                    )

                    severity_summary[severity] = severity_summary.get(severity, 0) + 1
                    total_vulns += 1

            if dep_vulns:
                vulnerable_count += 1

            is_imported = None
            if imported_packages:
                normalized_name = dep.name.lower().replace("-", "_")
                is_imported = dep.name in imported_packages or normalized_name in {
                    p.lower().replace("-", "_") for p in imported_packages
                }

            license_str = None
            license_compliant = None
            if "license_compliance" in caps_set:
                license_str = _fetch_package_license(
                    dep.name, dep.ecosystem if hasattr(dep, "ecosystem") else "unknown"
                )
                if license_str:
                    license_compliant = _check_license_compliance(license_str)

            typosquatting_risk = None
            if "typosquatting_detection" in caps_set:
                typosquatting_risk = _check_typosquatting(
                    dep.name, dep.ecosystem if hasattr(dep, "ecosystem") else "unknown"
                )

            supply_chain_risk_score = None
            supply_chain_risk_factors = None
            if "supply_chain_risk_scoring" in caps_set:
                supply_chain_risk_score, supply_chain_risk_factors = _calculate_supply_chain_risk(
                    dep.name,
                    dep.version,
                    (dep.ecosystem.value if hasattr(dep.ecosystem, "value") else str(dep.ecosystem)),
                    dep_vulns,
                    is_imported,
                    typosquatting_risk,
                    license_compliant,
                )

            dependency_infos.append(
                DependencyInfo(
                    name=dep.name,
                    version=dep.version,
                    ecosystem=(dep.ecosystem.value if hasattr(dep.ecosystem, "value") else str(dep.ecosystem)),
                    file_path=getattr(dep, "file_path", "unknown"),
                    vulnerabilities=dep_vulns,
                    is_imported=is_imported,
                    license=license_str,
                    license_compliant=license_compliant,
                    typosquatting_risk=typosquatting_risk,
                    supply_chain_risk_score=supply_chain_risk_score,
                    supply_chain_risk_factors=supply_chain_risk_factors,
                )
            )

        compliance_report = None
        policy_violations = None
        if "compliance_reporting" in caps_set:
            compliance_report = _generate_compliance_report(
                dependency_infos,
                severity_summary,
                total_vulns,
                vulnerable_count,
            )
            policy_violations = []
            for dep_info in dependency_infos:
                if dep_info.typosquatting_risk:
                    policy_violations.append(
                        {
                            "type": "typosquatting",
                            "package": dep_info.name,
                            "severity": "HIGH",
                            "message": f"Package '{dep_info.name}' flagged for potential typosquatting",
                        }
                    )
                if dep_info.license_compliant is False:
                    policy_violations.append(
                        {
                            "type": "license",
                            "package": dep_info.name,
                            "severity": "MEDIUM",
                            "message": f"Package '{dep_info.name}' has non-compliant license: {dep_info.license}",
                        }
                    )
                if dep_info.supply_chain_risk_score and dep_info.supply_chain_risk_score >= 0.7:
                    policy_violations.append(
                        {
                            "type": "supply_chain",
                            "package": dep_info.name,
                            "severity": "HIGH",
                            "message": f"Package '{dep_info.name}' has high supply chain risk score: {dep_info.supply_chain_risk_score}",
                        }
                    )

        # [20260120_SECURITY] Fail-closed: OSV API failures must return success=False
        # Network errors are NOT a clean bill of health—don't let agents assume safety
        # when the guard dog is asleep. Any OSV query failure means we cannot verify
        # the security posture, so success must be False.
        osv_query_failed = any("OSV query failed" in err for err in errors)
        scan_success = not osv_query_failed

        return DependencyScanResult(
            success=scan_success,
            total_dependencies=len(dependency_infos),
            vulnerable_count=vulnerable_count,
            total_vulnerabilities=total_vulns,
            severity_summary=severity_summary,
            dependencies=dependency_infos,
            compliance_report=compliance_report,
            policy_violations=policy_violations,
            errors=errors,
        )

    except ImportError as exc:
        return DependencyScanResult(success=False, error=f"Dependency scanning unavailable: {exc}")
    except Exception as exc:
        return DependencyScanResult(success=False, error=f"Dependency scan failed: {exc}")


def _security_scan_sync(
    code: str | None = None,
    file_path: str | None = None,
    tier: str | None = None,
    capabilities: dict | None = None,
    confidence_threshold: float = 0.7,
) -> SecurityResult:
    """Synchronous implementation of security_scan."""

    tier = tier or _get_current_tier()
    caps = capabilities or get_tool_capabilities("security_scan", tier)
    caps_set = set(caps.get("capabilities", set()) or [])
    limits = caps.get("limits", {}) or {}

    detected_language = "python"

    def _basic_scan_patterns(
        code_str: str,
    ) -> tuple[list[VulnerabilityInfo], list[str]]:
        patterns = [
            (
                "execute(",
                "SQL Injection",
                "CWE-89",
                "Possible SQL injection via execute()",
            ),
            (
                "cursor.execute",
                "SQL Injection",
                "CWE-89",
                "SQL query execution detected",
            ),
            ("os.system(", "Command Injection", "CWE-78", "os.system() call detected"),
            (
                "subprocess.call(",
                "Command Injection",
                "CWE-78",
                "subprocess.call() detected",
            ),
            ("eval(", "Code Injection", "CWE-94", "eval() call detected"),
            ("exec(", "Code Injection", "CWE-94", "exec() call detected"),
            ("render_template_string(", "XSS", "CWE-79", "Template injection risk"),
        ]
        vulnerabilities: list[VulnerabilityInfo] = []
        taint_sources: list[str] = []
        for line_num, line in enumerate(code_str.splitlines(), 1):
            for pattern, vuln_type, cwe, desc in patterns:
                if pattern in line:
                    vulnerabilities.append(
                        VulnerabilityInfo(
                            type=vuln_type,
                            cwe=cwe,
                            severity="high" if "Injection" in vuln_type else "medium",
                            line=line_num,
                            description=desc,
                        )
                    )

        for source_pattern in ["request.args", "request.form", "input(", "sys.argv"]:
            if source_pattern in code_str:
                taint_sources.append(source_pattern)

        return vulnerabilities, taint_sources

    def _detect_sanitizers(code_str: str) -> list[str]:
        patterns = [r"\bsanitize\w*\s*\(", r"html\.escape\s*\(", r"\bescape\w*\s*\("]
        hits: list[str] = []
        for idx, line in enumerate(code_str.splitlines(), 1):
            for pat in patterns:
                if re.search(pat, line):
                    hits.append(f"L{idx}: {line.strip()}")
        return hits

    def _build_confidence_scores(vulns: list[VulnerabilityInfo]) -> dict[str, float]:
        scores: dict[str, float] = {}
        for vuln in vulns:
            key = f"{vuln.type}@L{vuln.line or 0}"
            scores[key] = 0.9 if vuln.severity.lower() in {"high", "critical"} else 0.7
        return scores

    def _build_false_positive_analysis(count: int, max_limit: int | None) -> dict[str, Any]:
        suppressed = 0
        if max_limit is not None and max_limit >= 0 and count > max_limit:
            suppressed = count - max_limit
        return {
            "total_findings": count,
            "suppressed": suppressed,
            "notes": [] if suppressed == 0 else ["Findings truncated by tier limits"],
        }

    def _detect_policy_violations(code_str: str) -> list[dict[str, Any]]:
        try:
            policy_engine = PolicyEngine()
            violations_list = policy_engine.check_weak_crypto(code_str)
            return [
                {
                    "rule": v.policy_id,
                    "line": v.line,
                    "severity": v.severity,
                    "detail": v.description,
                    "remediation": v.remediation,
                }
                for v in violations_list
            ]
        except Exception as e:
            logger.warning(f"Policy engine check failed: {e}")
            return []

    def _build_compliance_mappings(
        vulns: list[VulnerabilityInfo], policies: list[dict[str, Any]]
    ) -> dict[str, list[str]]:
        if not vulns and not policies:
            return {}
        return {
            "OWASP_TOP_10": ["A01-Broken Access Control", "A03-Injection"],
            "HIPAA": ["164.312(e)(1)"],
            "SOC2": ["CC6.7"],
            "PCI_DSS": ["6.5.1"],
        }

    def _detect_custom_logging_rules(code_str: str) -> list[dict[str, Any]]:
        try:
            policy_engine = PolicyEngine()
            violations_list = policy_engine.check_sensitive_logging(code_str)
            return [
                {
                    "rule": v.policy_id,
                    "line": v.line,
                    "severity": v.severity,
                    "detail": v.description,
                    "remediation": v.remediation,
                }
                for v in violations_list
            ]
        except Exception as e:
            logger.warning(f"Policy engine logging check failed: {e}")
            return []

    def _build_priority_ordered_findings(
        vulns: list[VulnerabilityInfo],
    ) -> list[dict[str, Any]]:
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        cwe_priority = {
            "CWE-89": 1,
            "CWE-78": 1,
            "CWE-94": 1,
            "CWE-79": 2,
            "CWE-22": 3,
            "CWE-90": 2,
            "CWE-943": 2,
        }

        def get_priority(v: VulnerabilityInfo) -> tuple[int, int, int]:
            sev = severity_order.get(v.severity.lower(), 4)
            cwe = cwe_priority.get(v.cwe, 5)
            line = v.line or 9999
            return (sev, cwe, line)

        sorted_vulns = sorted(vulns, key=get_priority)
        return [
            {
                "rank": idx + 1,
                "type": v.type,
                "cwe": v.cwe,
                "severity": v.severity,
                "line": v.line,
                "description": v.description,
                "priority_score": 100 - (get_priority(v)[0] * 20 + get_priority(v)[1] * 5),
            }
            for idx, v in enumerate(sorted_vulns)
        ]

    def _build_reachability_analysis(vulns: list[VulnerabilityInfo], code_str: str) -> dict[str, Any]:
        entry_point_patterns = [
            r"def main\s*\(",
            r"@app\.route\s*\(",
            r"@router\.",
            r"async def \w+_handler\s*\(",
            r"def \w+_view\s*\(",
            r"class \w+View\s*\(",
            r"if __name__\s*==",
        ]

        entry_points: list[dict[str, Any]] = []
        for idx, line in enumerate(code_str.splitlines(), 1):
            for pattern in entry_point_patterns:
                if re.search(pattern, line):
                    entry_points.append(
                        {
                            "line": idx,
                            "pattern": pattern.replace("\\s*", " ").replace("\\(", "("),
                            "code": line.strip()[:80],
                        }
                    )
                    break

        reachable_vulns = []
        unreachable_vulns = []

        for v in vulns:
            vuln_line = v.line or 0
            is_reachable = False
            for ep in entry_points:
                if ep["line"] < vuln_line:
                    is_reachable = True
                    break

            if is_reachable or not entry_points:
                reachable_vulns.append(
                    {
                        "type": v.type,
                        "cwe": v.cwe,
                        "line": v.line,
                        "reachable": True,
                        "reason": ("Downstream of entry point" if entry_points else "No entry point analysis possible"),
                    }
                )
            else:
                unreachable_vulns.append(
                    {
                        "type": v.type,
                        "cwe": v.cwe,
                        "line": v.line,
                        "reachable": False,
                        "reason": "No entry point precedes this vulnerability",
                    }
                )

        return {
            "entry_points_found": len(entry_points),
            "entry_points": entry_points[:5],
            "reachable_count": len(reachable_vulns),
            "unreachable_count": len(unreachable_vulns),
            "reachable_vulnerabilities": reachable_vulns,
            "unreachable_vulnerabilities": unreachable_vulns,
            "analysis_confidence": "high" if entry_points else "low",
        }

    def _build_false_positive_tuning(vulns: list[VulnerabilityInfo], sanitizers: list[str]) -> dict[str, Any]:
        tuning_suggestions: list[dict[str, Any]] = []

        if sanitizers:
            for v in vulns:
                if v.type in {"XSS", "SQL Injection", "Command Injection"}:
                    tuning_suggestions.append(
                        {
                            "vulnerability_type": v.type,
                            "line": v.line,
                            "suggestion": "Review if sanitizer at nearby line handles this input",
                            "sanitizers_detected": sanitizers[:3],
                            "confidence_adjustment": -0.1,
                        }
                    )

        fp_patterns = {
            "test_": "Test file - likely intentional vulnerable code",
            "mock_": "Mock data - likely not real vulnerability",
            "example_": "Example code - likely documentation",
        }

        suppression_candidates = []
        for v in vulns:
            desc_lower = (v.description or "").lower()
            for pattern, reason in fp_patterns.items():
                if pattern in desc_lower:
                    suppression_candidates.append(
                        {
                            "type": v.type,
                            "line": v.line,
                            "pattern": pattern,
                            "reason": reason,
                        }
                    )

        return {
            "sanitizers_detected": len(sanitizers),
            "tuning_suggestions": tuning_suggestions,
            "suppression_candidates": suppression_candidates,
            "recommended_actions": (
                [
                    "Review sanitizer coverage for detected vulnerabilities",
                    "Consider suppressing test/mock file findings",
                    "Add custom rules for organization-specific patterns",
                ]
                if tuning_suggestions or suppression_candidates
                else []
            ),
        }

    def _build_remediation_suggestions_list(
        vulns: list[VulnerabilityInfo],
    ) -> list[str]:
        remediation_map = {
            "CWE-89": "Use parameterized queries or ORM to prevent SQL injection",
            "CWE-78": "Avoid shell=True in subprocess; use list-based arguments",
            "CWE-94": "Avoid eval()/exec(); use safe alternatives like ast.literal_eval()",
            "CWE-79": "Escape user input before rendering; use template auto-escaping",
            "CWE-22": "Validate and sanitize file paths; use pathlib with resolve()",
            "CWE-90": "Use parameterized LDAP queries; escape special characters",
            "CWE-943": "Use parameterized NoSQL queries; validate input types",
            "CWE-502": "Avoid deserializing untrusted data; use JSON instead of pickle",
            "CWE-918": "Validate and whitelist URLs for SSRF prevention",
            "CWE-352": "Implement CSRF tokens for state-changing operations",
            "CWE-347": "Always verify JWT signatures; avoid algorithm='none'",
            "CWE-327": "Use strong cryptographic algorithms (e.g., SHA-256, bcrypt)",
            "CWE-798": "Move secrets to environment variables or secret managers",
            "CWE-611": "Disable external entities in XML parsers",
            "CWE-1336": "Avoid rendering user input directly in templates (SSTI)",
        }

        suggestions: list[str] = []
        seen_cwes: set[str] = set()
        for vuln in vulns:
            cwe = vuln.cwe
            if cwe and cwe not in seen_cwes:
                seen_cwes.add(cwe)
                if cwe in remediation_map:
                    suggestions.append(f"{cwe}: {remediation_map[cwe]}")
                else:
                    suggestions.append(f"{cwe}: Review and remediate {vuln.type}")

        return suggestions

    if file_path is not None:
        try:
            path = Path(file_path)
            if not path.exists():
                return SecurityResult(
                    success=False,
                    has_vulnerabilities=False,
                    vulnerability_count=0,
                    risk_level="unknown",
                    error=f"File not found: {file_path}.",
                )
            if not path.is_file():
                return SecurityResult(
                    success=False,
                    has_vulnerabilities=False,
                    vulnerability_count=0,
                    risk_level="unknown",
                    error=f"Path is not a file: {file_path}.",
                )
            code = path.read_text(encoding="utf-8")

            ext = path.suffix.lower()
            extension_map = {
                ".py": "python",
                ".pyi": "python",
                ".pyw": "python",
                ".js": "javascript",
                ".mjs": "javascript",
                ".cjs": "javascript",
                ".jsx": "javascript",
                ".ts": "typescript",
                ".tsx": "typescript",
                ".mts": "typescript",
                ".cts": "typescript",
                ".java": "java",
            }
            detected_language = extension_map.get(ext, "python")
        except Exception as e:
            return SecurityResult(
                success=False,
                has_vulnerabilities=False,
                vulnerability_count=0,
                risk_level="unknown",
                error=f"Failed to read file: {str(e)}.",
            )

    if code is None:
        return SecurityResult(
            success=False,
            has_vulnerabilities=False,
            vulnerability_count=0,
            risk_level="unknown",
            error="Either 'code' or 'file_path' must be provided.",
        )

    valid, validation_error = _validate_code(code)
    if not valid:
        return SecurityResult(
            success=False,
            has_vulnerabilities=False,
            vulnerability_count=0,
            risk_level="unknown",
            error=validation_error,
        )

    max_file_size_kb = limits.get("max_file_size_kb")
    if max_file_size_kb is not None:
        code_size_kb = len(code.encode("utf-8")) / 1024
        if code_size_kb > max_file_size_kb:
            return SecurityResult(
                success=False,
                has_vulnerabilities=False,
                vulnerability_count=0,
                risk_level="unknown",
                error=(
                    f"Code size {code_size_kb:.1f}KB exceeds tier limit "
                    f"{max_file_size_kb}KB for tier {tier.title()}"
                ),
            )

    cache = _get_cache()
    cache_key = None
    if cache:
        cache_key = f"{tier}:{hashlib.sha256(code.encode('utf-8')).hexdigest()}"
        cached = cache.get(cache_key, "security")
        if cached is not None:
            logger.debug("Cache hit for security_scan")
            if isinstance(cached, SecurityResult):
                return cached
            if isinstance(cached, dict):
                if "vulnerabilities" in cached:
                    vuln_list = cached["vulnerabilities"]
                    if vuln_list and isinstance(vuln_list[0], dict):
                        cached["vulnerabilities"] = [VulnerabilityInfo(**v) for v in vuln_list]
                return SecurityResult(**cached)
            return cached

    vulnerabilities: list[VulnerabilityInfo] = []
    taint_sources: list[str] = []

    try:
        if detected_language != "python":
            detector = _get_sink_detector()
            detected_sinks = detector.detect_sinks(code, detected_language, confidence_threshold)

            for sink in detected_sinks:
                vulnerabilities.append(
                    VulnerabilityInfo(
                        type=getattr(sink, "vulnerability_type", "") or sink.pattern,
                        cwe=f"CWE-{_get_cwe_from_sink_type(sink.sink_type)}",
                        severity="high" if sink.confidence >= 0.9 else "medium",
                        line=sink.line,
                        description=f"Detected {sink.pattern} with {sink.confidence:.0%} confidence",
                    )
                )

            if detected_language == "typescript":
                try:
                    te_detector = TypeEvaporationDetector()
                    te_result = te_detector.analyze(code, file_path or "<string>")

                    for vuln in te_result.vulnerabilities:
                        vulnerabilities.append(
                            VulnerabilityInfo(
                                type=f"Type Evaporation: {vuln.risk_type.name}",
                                cwe=vuln.cwe_id,
                                severity=vuln.severity.lower(),
                                line=vuln.location[0],
                                description=vuln.description,
                            )
                        )
                except ImportError:
                    pass
        else:
            analyzer = SecurityAnalyzer()
            result = analyzer.analyze(code).to_dict()

            for vuln in result.get("vulnerabilities", []):
                sink_loc = vuln.get("sink_location")
                line_number = sink_loc[0] if sink_loc and isinstance(sink_loc, (list, tuple)) else None

                vulnerabilities.append(
                    VulnerabilityInfo(
                        type=vuln.get("type", "Unknown"),
                        cwe=vuln.get("cwe", "Unknown"),
                        severity=vuln.get("severity", "medium"),
                        line=line_number,
                        description=vuln.get("description", ""),
                    )
                )

            for source in result.get("taint_sources", []):
                taint_sources.append(str(source))

    except ImportError:
        vulnerabilities, taint_sources = _basic_scan_patterns(code)
    except Exception as exc:
        return SecurityResult(
            success=False,
            has_vulnerabilities=False,
            vulnerability_count=0,
            risk_level="unknown",
            error=f"Security scan failed: {str(exc)}.",
        )

    max_findings = limits.get("max_findings")
    if max_findings is not None and max_findings >= 0:
        vulnerabilities = vulnerabilities[:max_findings]

    vuln_count = len(vulnerabilities)
    risk_level = "low"
    if vuln_count > 0:
        risk_level = "medium" if vuln_count <= 2 else "high" if vuln_count <= 5 else "critical"

    sanitizer_paths: list[str] | None = None
    confidence_scores: dict[str, float] | None = None
    false_positive_analysis: dict[str, Any] | None = None
    policy_violations: list[dict[str, Any]] | None = None
    compliance_mappings: dict[str, list[str]] | None = None
    custom_rule_results: list[dict[str, Any]] | None = None
    remediation_suggestions: list[str] | None = None
    priority_ordered_findings: list[dict[str, Any]] | None = None
    reachability_analysis: dict[str, Any] | None = None
    false_positive_tuning: dict[str, Any] | None = None

    # [20260120_BUGFIX] Normalize capability flags so Pro/Enterprise populate advanced fields
    has_sanitizers = "sanitizer_detection" in caps_set or "sanitizer_recognition" in caps_set
    has_confidence = "confidence_scores" in caps_set or "confidence_scoring" in caps_set
    has_fp_analysis = "false_positive_analysis" in caps_set or "false_positive_reduction" in caps_set
    has_policy = "policy_checks" in caps_set or "custom_policy_engine" in caps_set or "org_specific_rules" in caps_set
    has_compliance = (
        "compliance_mappings" in caps_set
        or "compliance_rule_checking" in caps_set
        or "compliance_reporting" in caps_set
    )
    has_priority = (
        "priority_findings" in caps_set or "priority_finding_ordering" in caps_set or "priority_cve_alerts" in caps_set
    )

    if has_sanitizers:
        sanitizer_paths = _detect_sanitizers(code)
    if has_confidence:
        confidence_scores = _build_confidence_scores(vulnerabilities)
    if has_fp_analysis:
        false_positive_analysis = _build_false_positive_analysis(len(vulnerabilities), limits.get("max_findings"))
    if has_policy:
        policy_violations = _detect_policy_violations(code)
    if has_compliance:
        compliance_mappings = _build_compliance_mappings(vulnerabilities, policy_violations or [])
    if "custom_logging_rules" in caps_set:
        custom_rule_results = _detect_custom_logging_rules(code)
    if "remediation_suggestions" in caps_set:
        remediation_suggestions = _build_remediation_suggestions_list(vulnerabilities)
    if has_priority:
        priority_ordered_findings = _build_priority_ordered_findings(vulnerabilities)
    if "reachability_analysis" in caps_set or "vulnerability_reachability_analysis" in caps_set:
        reachability_analysis = _build_reachability_analysis(vulnerabilities, code)
    if "false_positive_tuning" in caps_set:
        false_positive_tuning = _build_false_positive_tuning(vulnerabilities, sanitizer_paths or [])

    return SecurityResult(
        success=True,
        has_vulnerabilities=bool(vulnerabilities),
        vulnerability_count=vuln_count,
        risk_level=risk_level,
        vulnerabilities=vulnerabilities,
        taint_sources=taint_sources,
        sanitizer_paths=sanitizer_paths,
        confidence_scores=confidence_scores,
        false_positive_analysis=false_positive_analysis,
        policy_violations=policy_violations,
        compliance_mappings=compliance_mappings,
        custom_rule_results=custom_rule_results,
        remediation_suggestions=remediation_suggestions,
        priority_ordered_findings=priority_ordered_findings,
        reachability_analysis=reachability_analysis,
        false_positive_tuning=false_positive_tuning,
    )


async def _unified_sink_detect_impl(
    code: str,
    language: str,
    confidence_threshold: float = 0.7,
) -> UnifiedSinkResult:
    """
    Unified polyglot sink detection with confidence thresholds.

    Sinks are dangerous functions where untrusted data should never reach directly
    (e.g., eval(), execute(), os.system()). This tool detects sinks across multiple
    languages and maps them to CWE identifiers.

    [20251216_FEATURE] v2.5.0 "Guardian" - Expose unified sink detector via MCP.
    [20251220_BUGFIX] v3.0.5 - Use DEFAULT_MIN_CONFIDENCE for consistency.

    Example::

        result = await unified_sink_detect(
            code="eval(user_input)",
            language="python"
        )

        # Returns UnifiedSinkResult:
        # - sinks: [SinkInfo(name="eval", line=1, cwe="CWE-94", confidence=0.95)]
        # - sink_count: 1
        # - coverage: {"code_injection": True, "sql_injection": False, ...}
        # - language: "python"

        # Multi-language support:
        js_result = await unified_sink_detect(
            code="document.innerHTML = userInput;",
            language="javascript"
        )
        # Detects XSS sink with CWE-79

    Args:
        code: Source code to analyze
        language: Programming language (python, java, typescript, javascript)
        min_confidence: Minimum confidence threshold (0.0-1.0, default: 0.7)

    Returns:
        UnifiedSinkResult with detected sinks, CWE mappings, and coverage summary
    """

    tier = get_current_tier()
    capabilities = get_tool_capabilities("unified_sink_detect", tier)
    return await asyncio.to_thread(
        _unified_sink_detect_sync,
        code,
        language,
        confidence_threshold,
        tier,
        capabilities,
    )


async def _type_evaporation_scan_impl(
    frontend_code: str,
    backend_code: str,
    frontend_file: str = "frontend.ts",
    backend_file: str = "backend.py",
) -> TypeEvaporationResultModel:
    """
    Detect Type System Evaporation vulnerabilities across TypeScript frontend and Python backend.

    [20251229_FEATURE] v3.0.4 - Ninja Warrior Stage 3.1
    [20251226_FEATURE] v3.3.0 - Added Pro/Enterprise tier capabilities

    Type System Evaporation occurs when TypeScript compile-time types (like union types)
    are trusted but evaporate at serialization boundaries (JSON.stringify).

    This tool analyzes:
    - TypeScript frontend: unsafe type assertions, DOM input, fetch boundaries
    - Python backend: unvalidated external input in HTTP responses
    - Cross-file: correlates TS fetch() endpoints with Python @app.route() decorators

    **Pro tier adds:**
    - Implicit any detection from untyped .json() responses
    - Network boundary analysis (fetch, axios, XMLHttpRequest)
    - Library boundary tracking (localStorage, postMessage)
    - JSON.parse location detection

    **Enterprise tier adds:**
    - Zod schema generation for TypeScript validation
    - Pydantic model generation for Python backend
    - API contract validation
    - Schema coverage metrics

    Example vulnerability:
        Frontend: type Role = 'admin' | 'user'; const role = input.value as Role;
        Backend: role = request.get_json()['role']  # No validation!

    The TypeScript type provides NO runtime enforcement - attacker can send any value.

    Args:
        frontend_code: TypeScript/JavaScript frontend code
        backend_code: Python backend code
        frontend_file: Frontend filename for error messages
        backend_file: Backend filename for error messages

    Returns:
        TypeEvaporationResultModel with frontend, backend, and cross-file vulnerabilities.
    """
    # [20251226_FEATURE] Tier-aware feature enablement
    tier = get_current_tier()
    caps = get_tool_capabilities("type_evaporation_scan", tier) or {}
    cap_set = set(caps.get("capabilities", []))
    limits = caps.get("limits", {}) or {}
    frontend_only = bool(limits.get("frontend_only", False))
    raw_max_files = limits.get("max_files")
    try:
        max_files = int(raw_max_files) if raw_max_files is not None else None
    except (TypeError, ValueError):
        max_files = None

    # Pro features: implicit any, network boundaries, library boundaries
    enable_pro = bool(
        {
            "implicit_any_tracing",
            "network_boundary_analysis",
            "library_boundary_analysis",
        }
        & cap_set
    )

    # Enterprise features: schema generation, contract validation
    enable_enterprise = bool(
        {
            "runtime_validation_generation",
            "zod_schema_generation",
            "api_contract_validation",
        }
        & cap_set
    )

    return await asyncio.to_thread(
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


async def _scan_dependencies_impl(
    path: str | None = None,
    project_root: str | None = None,
    scan_vulnerabilities: bool = True,
    include_dev: bool = True,
    timeout: float = 30.0,
    ctx: Context | None = None,
) -> DependencyScanResult:
    """
    Scan project dependencies for known vulnerabilities (A06:2021 - Vulnerable Components).

    [20251219_FEATURE] v3.0.4 - A06 Vulnerable and Outdated Components
    [20251220_FIX] v3.0.5 - Added timeout parameter for OSV API calls
    [20251220_FEATURE] v3.0.5 - Progress reporting during vulnerability scan
    [20251220_FEATURE] v3.0.5 - Returns DependencyScanResult with per-dependency tracking

    This tool scans dependency files and checks them against the Google OSV
    (Open Source Vulnerabilities) database for known CVEs and security advisories.

    Supported dependency files:
    - npm: package.json
    - Maven: pom.xml, build.gradle
    - Python: requirements.txt, pyproject.toml

    Example usage:
    - Scan a single file: scan_dependencies(path="package.json")
    - Scan a project directory: scan_dependencies(project_root="/path/to/project")
    - Without vulnerability check: scan_dependencies(path="requirements.txt", scan_vulnerabilities=False)

    The scan will recursively find all dependency files in a directory,
    skipping node_modules and .venv directories.

    Args:
        path: Path to a dependency file or project directory
        project_root: Alias for 'path' (for backward compatibility)
        scan_vulnerabilities: Whether to check OSV for vulnerabilities (default True)
        include_dev: Whether to include dev dependencies (default True)
        timeout: Timeout in seconds for OSV API calls (default: 30.0)

    Returns:
        DependencyScanResult with dependency-level vulnerability tracking.
    """
    # Resolve path parameter (support both 'path' and 'project_root')
    resolved_path = path or project_root or str(_get_project_root())

    # [20251229_FEATURE] v3.3.1 - Get tier and capabilities
    tier = get_current_tier()
    caps = get_tool_capabilities("scan_dependencies", tier)

    # [20251220_FEATURE] v3.0.5 - Progress reporting
    if ctx:
        await ctx.report_progress(0, 100, f"Scanning dependencies in {resolved_path}...")

    result = await asyncio.to_thread(
        _scan_dependencies_sync,
        project_root=resolved_path,
        scan_vulnerabilities=scan_vulnerabilities,
        include_dev=include_dev,
        timeout=timeout,
        tier=tier,
        capabilities=caps,
    )

    if ctx:
        vuln_count = result.total_vulnerabilities
        await ctx.report_progress(100, 100, f"Scan complete: {vuln_count} vulnerabilities found")

    return result


def _split_virtual_files(code: str) -> list[str]:
    """Split a single code string into virtual files using // FILE: markers.

    If no markers are present, the entire string is treated as one file. This
    allows tests to simulate multi-file inputs for tier limit enforcement without
    changing the public MCP API shape.
    """

    lines = code.splitlines()
    segments: list[list[str]] = []
    current: list[str] = []

    for line in lines:
        if line.strip().startswith("// FILE:"):
            if current:
                segments.append(current)
                current = []
            current.append(line)
        else:
            current.append(line)

    if current:
        segments.append(current)

    if not segments:
        return [code]

    return ["\n".join(seg) for seg in segments]


def _enforce_file_limits(
    frontend_code: str,
    backend_code: str,
    max_files: int | None,
) -> tuple[str, str, list[str]]:
    """Apply virtual file limits using // FILE: markers; return truncated code and warnings."""

    warnings: list[str] = []
    frontend_files = _split_virtual_files(frontend_code)
    backend_files = _split_virtual_files(backend_code)

    total_files = len(frontend_files) + len(backend_files)

    if max_files is not None and max_files >= 0 and total_files > max_files:
        # Reserve at least one slot for backend code
        allowed_frontend = max(max_files - len(backend_files), 0)
        warnings.append(f"Truncated virtual files from {total_files} to {max_files} due to tier max_files limit")
        frontend_files = frontend_files[:allowed_frontend] if allowed_frontend else []

    truncated_frontend = "\n\n".join(frontend_files) if frontend_files else ""
    truncated_backend = "\n\n".join(backend_files) if backend_files else ""

    return truncated_frontend, truncated_backend, warnings


def _type_evaporation_scan_sync(
    frontend_code: str,
    backend_code: str,
    frontend_file: str = "frontend.ts",
    backend_file: str = "backend.py",
    enable_pro_features: bool = False,
    enable_enterprise_features: bool = False,
    frontend_only: bool = False,
    max_files: int | None = None,
) -> TypeEvaporationResultModel:
    """
    Synchronous implementation of cross-file type evaporation analysis.

    [20251229_FEATURE] v3.0.4 - Ninja Warrior Stage 3.1 Type System Evaporation
    [20251226_FEATURE] v3.3.0 - Added Pro/Enterprise tier capabilities
    """
    try:
        # Apply virtual file limits (// FILE: markers) before analysis
        frontend_code, backend_code, warnings = _enforce_file_limits(frontend_code, backend_code, max_files)

        # [20251230_FIX][tiering] Community tier is frontend-only per capability matrix.
        if frontend_only:
            from code_scalpel.security.type_safety.type_evaporation_detector import (
                TypeEvaporationDetector,
            )

            detector = TypeEvaporationDetector()
            frontend_result = detector.analyze(frontend_code, frontend_file)

            all_vulns: list[VulnerabilityInfo] = [
                VulnerabilityInfo(
                    type=f"[Frontend] {v.risk_type.name}",
                    cwe=v.cwe_id,
                    severity=v.severity.lower(),
                    line=v.location[0],
                    description=v.description,
                )
                for v in frontend_result.vulnerabilities
            ]

            # Initialize Pro/Enterprise fields with defaults
            implicit_any_count = 0
            network_boundaries: list[dict[str, Any]] = []
            boundary_violations: list[dict[str, Any]] = []
            library_boundaries: list[dict[str, Any]] = []
            json_parse_locations: list[dict[str, Any]] = []

            # Pro-tier helper analyses are frontend-only; safe to run in this mode when enabled.
            if enable_pro_features:
                implicit_any_count = _detect_implicit_any(frontend_code)
                network_boundaries = _detect_network_boundaries(frontend_code)
                library_boundaries = _detect_library_boundaries(frontend_code)
                json_parse_locations = _detect_json_parse_locations(frontend_code)
                boundary_violations = _detect_boundary_violations(frontend_code, frontend_result)

            return TypeEvaporationResultModel(
                success=True,
                frontend_vulnerabilities=len(frontend_result.vulnerabilities),
                backend_vulnerabilities=0,
                cross_file_issues=0,
                matched_endpoints=[],
                vulnerabilities=all_vulns,
                summary=frontend_result.summary(),
                # Pro tier fields
                implicit_any_count=implicit_any_count,
                network_boundaries=network_boundaries,
                boundary_violations=boundary_violations,
                library_boundaries=library_boundaries,
                json_parse_locations=json_parse_locations,
                # Enterprise tier fields
                generated_schemas=[],
                validation_code=None,
                schema_coverage=None,
                pydantic_models=[],
                api_contract=None,
                # [20251231_FEATURE] v1.0 - New Enterprise fields (defaults for frontend-only)
                remediation_suggestions=[],
                custom_rule_violations=[],
                compliance_report=None,
                warnings=warnings,
            )

        from code_scalpel.security.type_safety import (
            analyze_type_evaporation_cross_file,
        )

        result = analyze_type_evaporation_cross_file(frontend_code, backend_code, frontend_file, backend_file)

        all_vulns: list[VulnerabilityInfo] = []

        # Add frontend vulnerabilities
        for v in result.frontend_result.vulnerabilities:
            all_vulns.append(
                VulnerabilityInfo(
                    type=f"[Frontend] {v.risk_type.name}",
                    cwe=v.cwe_id,
                    severity=v.severity.lower(),
                    line=v.location[0],
                    description=v.description,
                )
            )

        # Add backend vulnerabilities
        for v in result.backend_vulnerabilities:
            all_vulns.append(
                VulnerabilityInfo(
                    type=f"[Backend] {v.vulnerability_type}",
                    cwe=v.cwe_id,
                    severity=getattr(v, "severity", "high"),
                    line=v.sink_location[0] if v.sink_location else None,
                    description=getattr(v, "description", ""),
                )
            )

        # Add cross-file issues
        for v in result.cross_file_issues:
            all_vulns.append(
                VulnerabilityInfo(
                    type=f"[Cross-File] {v.risk_type.name}",
                    cwe=v.cwe_id,
                    severity=v.severity.lower(),
                    line=v.location[0],
                    description=v.description,
                )
            )

        matched = [
            f"{endpoint}: TS line {ts_line} → Python line {py_line}"
            for endpoint, ts_line, py_line in result.matched_endpoints
        ]

        # Initialize Pro/Enterprise fields with defaults
        implicit_any_count = 0
        network_boundaries: list[dict[str, Any]] = []
        boundary_violations: list[dict[str, Any]] = []
        library_boundaries: list[dict[str, Any]] = []
        json_parse_locations: list[dict[str, Any]] = []
        generated_schemas: list[dict[str, Any]] = []
        validation_code: str | None = None
        schema_coverage: float | None = None
        pydantic_models: list[dict[str, Any]] = []
        api_contract: dict[str, Any] | None = None

        # [20251226_FEATURE] Pro tier: Network boundary and implicit any detection
        if enable_pro_features:
            # Detect implicit any from .json() calls without type annotation
            implicit_any_count = _detect_implicit_any(frontend_code)

            # Detect network boundaries (fetch, axios, XMLHttpRequest)
            network_boundaries = _detect_network_boundaries(frontend_code)

            # Detect library call boundaries
            library_boundaries = _detect_library_boundaries(frontend_code)

            # Detect JSON.parse without validation
            json_parse_locations = _detect_json_parse_locations(frontend_code)

            # Track boundary violations (unvalidated type assertions at boundaries)
            boundary_violations = _detect_boundary_violations(frontend_code, result.frontend_result)

        # [20251226_FEATURE] Enterprise tier: Schema generation and contract validation
        if enable_enterprise_features:
            # Generate Zod schemas for matched endpoints
            generated_schemas = _generate_zod_schemas(result.frontend_result.type_definitions, result.matched_endpoints)

            # Generate complete validation code
            if generated_schemas:
                validation_code = _generate_validation_code(generated_schemas)

            # Generate Pydantic models for backend
            pydantic_models = _generate_pydantic_models(
                result.frontend_result.type_definitions, result.matched_endpoints
            )

            # Calculate schema coverage
            if result.matched_endpoints:
                covered = len(generated_schemas)
                total = len(result.matched_endpoints)
                schema_coverage = covered / total if total > 0 else 0.0

            # API contract validation
            api_contract = _validate_api_contract(
                result.frontend_result,
                result.backend_vulnerabilities,
                result.matched_endpoints,
            )

            # [20251231_FEATURE] v1.0 - New Enterprise features
            # Generate automated remediation suggestions
            remediation_suggestions = _generate_remediation_suggestions(
                all_vulns,
                generated_schemas,
                pydantic_models,
            )

            # Check custom type rules
            custom_rule_violations = _check_custom_type_rules(
                frontend_code,
                backend_code,
            )

            # Generate compliance report
            compliance_report = _generate_type_compliance_report(
                all_vulns,
                api_contract,
                custom_rule_violations,
                generated_schemas,
            )
        else:
            remediation_suggestions = []
            custom_rule_violations = []
            compliance_report = None

        return TypeEvaporationResultModel(
            success=True,
            frontend_vulnerabilities=len(result.frontend_result.vulnerabilities),
            backend_vulnerabilities=len(result.backend_vulnerabilities),
            cross_file_issues=len(result.cross_file_issues),
            matched_endpoints=matched,
            vulnerabilities=all_vulns,
            summary=result.summary(),
            # Pro tier fields
            implicit_any_count=implicit_any_count,
            network_boundaries=network_boundaries,
            boundary_violations=boundary_violations,
            library_boundaries=library_boundaries,
            json_parse_locations=json_parse_locations,
            # Enterprise tier fields
            generated_schemas=generated_schemas,
            validation_code=validation_code,
            schema_coverage=schema_coverage,
            pydantic_models=pydantic_models,
            api_contract=api_contract,
            # [20251231_FEATURE] v1.0 - New Enterprise fields
            remediation_suggestions=remediation_suggestions,
            custom_rule_violations=custom_rule_violations,
            compliance_report=compliance_report,
            warnings=warnings,
        )

    except ImportError as e:
        return TypeEvaporationResultModel(
            success=False,
            error=f"Type evaporation detector not available: {str(e)}.",
            warnings=[],
        )
    except Exception as e:
        return TypeEvaporationResultModel(
            success=False,
            error=f"Analysis failed: {str(e)}.",
            warnings=[],
        )


# =============================================================================
# [20251226_FEATURE] Pro tier helper functions for type_evaporation_scan
# =============================================================================


def _detect_implicit_any(code: str) -> int:
    """
    [20251226_FEATURE] Detect implicit any from untyped .json() responses.

    Patterns detected:
    - response.json() without type annotation
    - .then(r => r.json()) - implicit any in callback
    - await fetch().json() without type cast
    """
    count = 0
    lines = code.splitlines()

    for line in lines:
        # .json() call without 'as Type' or ': Type' annotation
        if ".json()" in line:
            # Check if there's a type annotation or cast
            if " as " not in line and ": " not in line.split("=")[0] if "=" in line else True:
                count += 1

        # Untyped destructuring from response
        if re.search(r"const\s+\{.*\}\s*=\s*.*\.json\(\)", line):
            if " as " not in line:
                count += 1

        # response.data without type (axios pattern)
        if ".data" in line and "response" in line.lower():
            if " as " not in line and ":" not in line.split("=")[0] if "=" in line else True:
                count += 1

    return count


def _detect_network_boundaries(code: str) -> list[dict[str, Any]]:
    """
    [20251226_FEATURE] Detect network call boundaries where types evaporate.

    Detects: fetch(), axios.*, XMLHttpRequest
    """
    boundaries: list[dict[str, Any]] = []
    lines = code.splitlines()

    network_patterns = [
        (r"\bfetch\s*\(", "fetch"),
        (r"\baxios\.(get|post|put|delete|patch)\s*\(", "axios"),
        (r"\baxios\s*\(", "axios"),
        (r"new\s+XMLHttpRequest\s*\(", "XMLHttpRequest"),
        (r"XMLHttpRequest\s*\(\s*\)", "XMLHttpRequest"),
    ]

    for i, line in enumerate(lines, 1):
        for pattern, boundary_type in network_patterns:
            if re.search(pattern, line, re.IGNORECASE):
                boundaries.append(
                    {
                        "line": i,
                        "type": "network_call",
                        "boundary_type": boundary_type,
                        "code_snippet": line.strip()[:100],
                        "risk": "high" if ".json()" in line else "medium",
                    }
                )
                break  # One match per line

    return boundaries


def _detect_library_boundaries(code: str) -> list[dict[str, Any]]:
    """
    [20251226_FEATURE] Detect library call boundaries where external data enters.

    Detects: localStorage, sessionStorage, postMessage, WebSocket
    """
    boundaries: list[dict[str, Any]] = []
    lines = code.splitlines()

    library_patterns = [
        (r"localStorage\.(getItem|setItem)", "localStorage"),
        (r"sessionStorage\.(getItem|setItem)", "sessionStorage"),
        (r"\.postMessage\s*\(", "postMessage"),
        (r"new\s+WebSocket\s*\(", "WebSocket"),
        (r"\.addEventListener\s*\(\s*['\"]message['\"]", "message_event"),
    ]

    for i, line in enumerate(lines, 1):
        for pattern, lib_type in library_patterns:
            if re.search(pattern, line):
                boundaries.append(
                    {
                        "line": i,
                        "type": "library_boundary",
                        "library": lib_type,
                        "code_snippet": line.strip()[:100],
                    }
                )
                break

    return boundaries


def _detect_json_parse_locations(code: str) -> list[dict[str, Any]]:
    """
    [20251226_FEATURE] Detect JSON.parse() calls without validation.
    """
    locations: list[dict[str, Any]] = []
    lines = code.splitlines()

    for i, line in enumerate(lines, 1):
        if "JSON.parse" in line:
            has_validation = " as " in line or "schema" in line.lower() or "validate" in line.lower()
            locations.append(
                {
                    "line": i,
                    "code_snippet": line.strip()[:100],
                    "validated": has_validation,
                    "risk": "low" if has_validation else "high",
                }
            )

    return locations


def _detect_boundary_violations(code: str, frontend_result: Any) -> list[dict[str, Any]]:
    """
    [20251226_FEATURE] Detect type violations at serialization boundaries.

    A violation occurs when:
    - Type assertion immediately follows network/JSON call
    - No runtime validation between boundary and type usage
    """
    violations: list[dict[str, Any]] = []

    # Check type assertions from the frontend result
    for type_name, line_num, context in getattr(frontend_result, "type_assertions", []):
        # Skip safe built-in types
        if type_name in ("string", "number", "boolean", "any", "unknown"):
            continue

        # Check if this assertion is near a boundary
        if ".json()" in context or "JSON.parse" in context or ".data" in context:
            violations.append(
                {
                    "line": line_num,
                    "type": type_name,
                    "context": context[:100],
                    "violation": f"Unvalidated type assertion '{type_name}' at boundary",
                    "risk": "high",
                }
            )

    return violations


def _generate_zod_schemas(
    type_definitions: dict[str, tuple[int, str]],
    matched_endpoints: list[tuple[str, int, int]],
) -> list[dict[str, Any]]:
    """
    [20251226_FEATURE] Generate Zod validation schemas from TypeScript types.
    """
    schemas: list[dict[str, Any]] = []

    for type_name, (line, definition) in type_definitions.items():
        # Skip internal/utility types
        if type_name.startswith("_") or type_name in ("Props", "State"):
            continue

        # Parse type definition and generate Zod schema
        zod_schema = _ts_type_to_zod(type_name, definition)

        if zod_schema:
            # Find associated endpoint if any
            endpoint = None
            for ep, ts_line, _py_line in matched_endpoints:
                if abs(ts_line - line) < 20:  # Within 20 lines
                    endpoint = ep
                    break

            schemas.append(
                {
                    "type_name": type_name,
                    "endpoint": endpoint,
                    "schema_type": "zod",
                    "schema": zod_schema,
                    "source_line": line,
                }
            )

    return schemas


def _ts_type_to_zod(type_name: str, definition: str) -> str | None:
    """
    [20251226_FEATURE] Convert TypeScript type definition to Zod schema.
    """
    # Handle interface
    if definition.startswith("interface"):
        fields = _extract_interface_fields(definition)
        if not fields:
            return None

        field_schemas = []
        for field_name, field_type in fields.items():
            zod_type = _ts_primitive_to_zod(field_type)
            field_schemas.append(f"  {field_name}: {zod_type}")

        return f"const {type_name}Schema = z.object({{\n" + ",\n".join(field_schemas) + "\n});"

    # Handle type alias with union
    union_match = re.search(r"type\s+\w+\s*=\s*(.+)", definition)
    if union_match:
        union_value = union_match.group(1).strip().rstrip(";")

        # String literal union: 'admin' | 'user'
        if "'" in union_value or '"' in union_value:
            literals = re.findall(r"['\"]([^'\"]+)['\"]", union_value)
            if literals:
                enum_values = ", ".join(f'"{lit}"' for lit in literals)
                return f"const {type_name}Schema = z.enum([{enum_values}]);"

        # Primitive union: string | number
        parts = [p.strip() for p in union_value.split("|")]
        if all(p in ("string", "number", "boolean", "null", "undefined") for p in parts):
            zod_parts = [_ts_primitive_to_zod(p) for p in parts]
            return f"const {type_name}Schema = z.union([{', '.join(zod_parts)}]);"

    return None


def _extract_interface_fields(definition: str) -> dict[str, str]:
    """Extract field name -> type mapping from interface definition."""
    fields: dict[str, str] = {}

    # Match field: type patterns
    field_pattern = re.compile(r"(\w+)\s*\??\s*:\s*([^;,}]+)")
    for match in field_pattern.finditer(definition):
        field_name = match.group(1)
        field_type = match.group(2).strip()
        if field_name not in ("interface", "type"):
            fields[field_name] = field_type

    return fields


def _ts_primitive_to_zod(ts_type: str) -> str:
    """Convert TypeScript primitive to Zod validator."""
    ts_type = ts_type.strip()
    mapping = {
        "string": "z.string()",
        "number": "z.number()",
        "boolean": "z.boolean()",
        "null": "z.null()",
        "undefined": "z.undefined()",
        "any": "z.any()",
        "unknown": "z.unknown()",
    }

    # Handle arrays
    if ts_type.endswith("[]"):
        inner = ts_type[:-2]
        return f"z.array({_ts_primitive_to_zod(inner)})"

    # Handle optional
    if ts_type.endswith("?"):
        inner = ts_type[:-1]
        return f"{_ts_primitive_to_zod(inner)}.optional()"

    return mapping.get(ts_type, "z.unknown()")


def _generate_validation_code(schemas: list[dict[str, Any]]) -> str:
    """
    [20251226_FEATURE] Generate complete validation code from schemas.
    """
    lines = [
        "// Auto-generated validation code by Code Scalpel",
        "// [20251226_FEATURE] Enterprise tier schema generation",
        "",
        "import { z } from 'zod';",
        "",
    ]

    for schema in schemas:
        lines.append(f"// Schema for {schema['type_name']}")
        lines.append(schema["schema"])
        lines.append("")

        # Add validation helper
        type_name = schema["type_name"]
        lines.append(f"export function validate{type_name}(data: unknown): {type_name} {{")
        lines.append(f"  return {type_name}Schema.parse(data);")
        lines.append("}")
        lines.append("")

    # Add safe fetch wrapper
    lines.extend(
        [
            "// Safe fetch wrapper with validation",
            "export async function safeFetch<T>(url: string, schema: z.Schema<T>): Promise<T> {",
            "  const response = await fetch(url);",
            "  const data = await response.json();",
            "  return schema.parse(data);",
            "}",
        ]
    )

    return "\n".join(lines)


def _generate_pydantic_models(
    type_definitions: dict[str, tuple[int, str]],
    matched_endpoints: list[tuple[str, int, int]],
) -> list[dict[str, Any]]:
    """
    [20251226_FEATURE] Generate Pydantic models for Python backend validation.
    """
    models: list[dict[str, Any]] = []

    for type_name, (line, definition) in type_definitions.items():
        if type_name.startswith("_"):
            continue

        pydantic_model = _ts_type_to_pydantic(type_name, definition)

        if pydantic_model:
            models.append(
                {
                    "type_name": type_name,
                    "model_type": "pydantic",
                    "model": pydantic_model,
                    "source_line": line,
                }
            )

    return models


def _ts_type_to_pydantic(type_name: str, definition: str) -> str | None:
    """
    [20251226_FEATURE] Convert TypeScript type to Pydantic model.
    """
    # Handle interface
    if definition.startswith("interface"):
        fields = _extract_interface_fields(definition)
        if not fields:
            return None

        field_defs = []
        for field_name, field_type in fields.items():
            py_type = _ts_to_python_type(field_type)
            field_defs.append(f"    {field_name}: {py_type}")

        return f"class {type_name}(BaseModel):\n" + "\n".join(field_defs)

    # Handle type alias with union (becomes Literal)
    union_match = re.search(r"type\s+\w+\s*=\s*(.+)", definition)
    if union_match:
        union_value = union_match.group(1).strip().rstrip(";")

        if "'" in union_value or '"' in union_value:
            literals = re.findall(r"['\"]([^'\"]+)['\"]", union_value)
            if literals:
                literal_values = ", ".join(f'"{lit}"' for lit in literals)
                return f"{type_name} = Literal[{literal_values}]"

    return None


def _ts_to_python_type(ts_type: str) -> str:
    """Convert TypeScript type to Python type annotation."""
    ts_type = ts_type.strip()
    mapping = {
        "string": "str",
        "number": "float",
        "boolean": "bool",
        "null": "None",
        "undefined": "None",
        "any": "Any",
    }

    if ts_type.endswith("[]"):
        inner = ts_type[:-2]
        return f"list[{_ts_to_python_type(inner)}]"

    return mapping.get(ts_type, "Any")


def _validate_api_contract(
    frontend_result: Any,
    backend_vulnerabilities: list[Any],
    matched_endpoints: list[tuple[str, int, int]],
) -> dict[str, Any]:
    """
    [20251226_FEATURE] Validate API contract between frontend and backend.
    """
    contract: dict[str, Any] = {
        "total_endpoints": len(matched_endpoints),
        "validated_endpoints": 0,
        "violations": [],
        "recommendations": [],
    }

    # Check each matched endpoint for contract violations
    for endpoint, ts_line, py_line in matched_endpoints:
        violation_found = False

        # Check if backend has input validation vulnerability
        for vuln in backend_vulnerabilities:
            vuln_line = (
                getattr(vuln, "sink_location", (0,))[0] if hasattr(vuln, "sink_location") and vuln.sink_location else 0
            )
            if abs(vuln_line - py_line) < 10:
                contract["violations"].append(
                    {
                        "endpoint": endpoint,
                        "type": "missing_validation",
                        "frontend_line": ts_line,
                        "backend_line": py_line,
                        "description": f"Backend at {endpoint} lacks input validation",
                    }
                )
                violation_found = True
                break

        if not violation_found:
            contract["validated_endpoints"] += 1

    # Generate recommendations
    if contract["violations"]:
        contract["recommendations"].append("Add runtime validation (Pydantic/marshmallow) to backend endpoints")
        contract["recommendations"].append("Use Zod schemas on frontend for response validation")

    return contract


# =============================================================================
# [20251231_FEATURE] v1.0 - Missing Enterprise tier helper functions
# =============================================================================


def _generate_remediation_suggestions(
    vulnerabilities: list[Any],
    generated_schemas: list[dict[str, Any]],
    pydantic_models: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    [20251231_FEATURE] Generate automated remediation suggestions for type evaporation issues.

    Analyzes vulnerabilities and provides actionable fix suggestions with code examples.
    """
    suggestions: list[dict[str, Any]] = []

    for vuln in vulnerabilities:
        vuln_type = getattr(vuln, "type", str(vuln)) if hasattr(vuln, "type") else str(vuln)
        vuln_line = getattr(vuln, "line", 0) if hasattr(vuln, "line") else 0
        vuln_desc = getattr(vuln, "description", "") if hasattr(vuln, "description") else ""

        suggestion: dict[str, Any] = {
            "vulnerability_type": vuln_type,
            "line": vuln_line,
            "priority": ("high" if "Backend" in str(vuln_type) or "Cross-File" in str(vuln_type) else "medium"),
            "fixes": [],
        }

        # Generate specific fixes based on vulnerability type
        if "implicit" in str(vuln_type).lower() or "any" in str(vuln_type).lower():
            suggestion["fixes"].append(
                {
                    "type": "add_type_annotation",
                    "description": "Add explicit type annotation to prevent implicit any",
                    "example": "const data: ResponseType = await response.json();",
                }
            )
            suggestion["fixes"].append(
                {
                    "type": "add_runtime_validation",
                    "description": "Add Zod schema validation at parse boundary",
                    "example": "const data = ResponseSchema.parse(await response.json());",
                }
            )

        if "Backend" in str(vuln_type):
            suggestion["fixes"].append(
                {
                    "type": "add_pydantic_validation",
                    "description": "Add Pydantic model for request validation",
                    "example": "def endpoint(request: RequestModel) -> ResponseModel:",
                }
            )
            suggestion["fixes"].append(
                {
                    "type": "add_input_sanitization",
                    "description": "Validate and sanitize all external input",
                    "example": "validated_data = RequestModel.model_validate(request.json())",
                }
            )

        if "network" in str(vuln_type).lower() or "fetch" in str(vuln_desc).lower():
            suggestion["fixes"].append(
                {
                    "type": "wrap_fetch_with_validation",
                    "description": "Use validated fetch wrapper",
                    "example": "const data = await safeFetch(url, ResponseSchema);",
                }
            )

        if "Cross-File" in str(vuln_type):
            suggestion["fixes"].append(
                {
                    "type": "sync_frontend_backend_types",
                    "description": "Ensure frontend and backend types match",
                    "example": "Generate shared types from OpenAPI spec or use code generation",
                }
            )

        # Link to generated schemas if available
        if generated_schemas:
            suggestion["available_schemas"] = [s["type_name"] for s in generated_schemas]
        if pydantic_models:
            suggestion["available_models"] = [m["type_name"] for m in pydantic_models]

        suggestions.append(suggestion)

    return suggestions


def _check_custom_type_rules(
    frontend_code: str,
    backend_code: str,
    custom_rules: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """
    [20251231_FEATURE] Check code against custom type rules.

    Supports user-defined rules for type safety enforcement.
    Default rules check for common type safety anti-patterns.
    """
    violations: list[dict[str, Any]] = []

    # Default rules if none provided
    default_rules = [
        {
            "id": "NO_EXPLICIT_ANY",
            "pattern": r":\s*any\b",
            "message": "Avoid explicit 'any' type - use specific types or 'unknown'",
            "severity": "warning",
            "applies_to": "frontend",
        },
        {
            "id": "NO_TYPE_ASSERTION_ANY",
            "pattern": r"as\s+any\b",
            "message": "Avoid 'as any' type assertion - loses type safety",
            "severity": "error",
            "applies_to": "frontend",
        },
        {
            "id": "NO_NON_NULL_ASSERTION",
            "pattern": r"\w+!(?:\.|$|\))",
            "message": "Avoid non-null assertion (!) - use proper null checking",
            "severity": "warning",
            "applies_to": "frontend",
        },
        {
            "id": "REQUIRE_TYPE_ON_JSON",
            "pattern": r"\.json\(\)\s*(?:;|$|\))",
            "message": ".json() should have type annotation or validation",
            "severity": "error",
            "applies_to": "frontend",
        },
        {
            "id": "NO_UNTYPED_REQUEST",
            "pattern": r"request\.get_json\(\)\s*(?:\n|$|#)",
            "message": "request.get_json() should be validated with Pydantic",
            "severity": "error",
            "applies_to": "backend",
        },
        {
            "id": "NO_RAW_DICT_ACCESS",
            "pattern": r"request\.json\[['\"]",
            "message": "Direct dict access on request.json - use validated model",
            "severity": "warning",
            "applies_to": "backend",
        },
    ]

    rules = custom_rules if custom_rules else default_rules

    for rule in rules:
        code_to_check = ""
        if rule.get("applies_to") == "frontend":
            code_to_check = frontend_code
        elif rule.get("applies_to") == "backend":
            code_to_check = backend_code
        else:
            code_to_check = frontend_code + "\n" + backend_code

        pattern = rule.get("pattern", "")
        if pattern:
            for i, line in enumerate(code_to_check.split("\n"), 1):
                if re.search(pattern, line):
                    violations.append(
                        {
                            "rule_id": rule.get("id", "CUSTOM"),
                            "line": i,
                            "code": line.strip()[:80],
                            "message": rule.get("message", "Custom rule violation"),
                            "severity": rule.get("severity", "warning"),
                            "applies_to": rule.get("applies_to", "both"),
                        }
                    )

    return violations


def _generate_type_compliance_report(
    vulnerabilities: list[Any],
    api_contract: dict[str, Any] | None,
    custom_rule_violations: list[dict[str, Any]],
    generated_schemas: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    [20251231_FEATURE] Generate type compliance validation report.

    Assesses overall type safety compliance and provides scoring.
    """
    report: dict[str, Any] = {
        "compliance_score": 100.0,
        "grade": "A",
        "findings": [],
        "summary": {
            "total_issues": 0,
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
        },
        "recommendations": [],
    }

    # Count vulnerabilities by severity
    for vuln in vulnerabilities:
        severity = getattr(vuln, "severity", "medium") if hasattr(vuln, "severity") else "medium"
        severity = severity.lower() if isinstance(severity, str) else "medium"

        report["summary"]["total_issues"] += 1

        if severity in ("critical", "high"):
            report["summary"]["high"] += 1
            report["compliance_score"] -= 15
            report["findings"].append(
                {
                    "type": "vulnerability",
                    "severity": severity,
                    "description": str(getattr(vuln, "description", vuln)),
                }
            )
        elif severity == "medium":
            report["summary"]["medium"] += 1
            report["compliance_score"] -= 5
        else:
            report["summary"]["low"] += 1
            report["compliance_score"] -= 2

    # Factor in custom rule violations
    for violation in custom_rule_violations:
        report["summary"]["total_issues"] += 1
        severity = violation.get("severity", "warning")

        if severity == "error":
            report["summary"]["high"] += 1
            report["compliance_score"] -= 10
        else:
            report["summary"]["medium"] += 1
            report["compliance_score"] -= 3

        report["findings"].append(
            {
                "type": "rule_violation",
                "rule_id": violation.get("rule_id"),
                "severity": severity,
                "message": violation.get("message"),
            }
        )

    # Factor in API contract compliance
    if api_contract:
        total_endpoints = api_contract.get("total_endpoints", 0)
        validated = api_contract.get("validated_endpoints", 0)

        if total_endpoints > 0:
            contract_score = (validated / total_endpoints) * 20
            report["compliance_score"] = min(100, report["compliance_score"] + contract_score - 10)

        for violation in api_contract.get("violations", []):
            report["findings"].append(
                {
                    "type": "contract_violation",
                    "severity": "high",
                    "endpoint": violation.get("endpoint"),
                    "description": violation.get("description"),
                }
            )

    # Bonus for having generated schemas
    if generated_schemas:
        report["compliance_score"] = min(100, report["compliance_score"] + 5)

    # Ensure score is within bounds
    report["compliance_score"] = max(0, min(100, report["compliance_score"]))

    # Assign grade
    score = report["compliance_score"]
    if score >= 90:
        report["grade"] = "A"
    elif score >= 80:
        report["grade"] = "B"
    elif score >= 70:
        report["grade"] = "C"
    elif score >= 60:
        report["grade"] = "D"
    else:
        report["grade"] = "F"

    # Generate recommendations based on findings
    if report["summary"]["high"] > 0:
        report["recommendations"].append("CRITICAL: Address high-severity type safety issues immediately")
    if report["summary"]["medium"] > 3:
        report["recommendations"].append("Consider adding runtime validation to reduce medium-severity issues")
    if not generated_schemas:
        report["recommendations"].append("Generate Zod schemas for frontend type validation")
    if api_contract and api_contract.get("violations"):
        report["recommendations"].append("Align frontend/backend types to resolve contract violations")

    return report
