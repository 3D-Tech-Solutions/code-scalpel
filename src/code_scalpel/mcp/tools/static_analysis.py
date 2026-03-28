"""Polyglot static-analysis helpers backing analyze_code static_tools.

[20260303_FEATURE] Added shared static-analysis execution helpers for the C++
tool parser registry (Cppcheck, clang-tidy, Clang-SA, cpplint, Coverity,
SonarQube).

[20260305_REFACTOR] Language dispatch delegated to the shared
``polyglot_dispatch.run_static_tools`` helper so that ALL supported languages
(C++, C#, Go, Python, JS/TS, Java, Ruby, Swift, Kotlin, PHP) are available
via the same MCP endpoint – language is detected automatically from the file
extension of each path in ``paths``.

Design notes
------------
- Free/open tools are available at Community tier and above.
- Enterprise-only tools (Coverity, SonarQube, ReSharper) require Enterprise tier for
  execution; all tiers can *parse* a pre-existing report file (C++ only at present).
- Community: max 50 total findings returned.
- Pro / Enterprise: unlimited findings returned.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from code_scalpel import __version__ as _pkg_version
from code_scalpel import telemetry
from code_scalpel.mcp.contract import ToolError, ToolResponseEnvelope, make_envelope
from code_scalpel.mcp.path_resolver import resolve_path
from code_scalpel.mcp.protocol import _get_current_tier

# [20260305_REFACTOR] Shared polyglot dispatch replaces the old C++-only dispatch
from code_scalpel.mcp.helpers.polyglot_dispatch import (
    COMMUNITY_MAX_TOOL_FINDINGS as _COMMUNITY_MAX_FINDINGS,
    run_static_tools as _run_static_tools_for_file,
)

# ---------------------------------------------------------------------------
# Synchronous implementation (runs in a thread)
# ---------------------------------------------------------------------------


def _run_static_analysis_sync(
    language: str,
    paths: List[str],
    tool: str,
    report_path: Optional[str],
    tier: str,
) -> Dict[str, Any]:
    """Run the appropriate tool parser and return structured findings.

    [20260303_FEATURE] Core sync implementation dispatched via asyncio.to_thread.
    [20260305_REFACTOR] Execution path delegates to polyglot_dispatch.run_static_tools
    so all 11 supported languages are automatically available.  The ``language``
    parameter is accepted for backward compatibility but execution now relies on
    file-extension detection inside run_static_tools.
    ``report_path`` triggers C++ report-file parsing (all tiers allowed).
    """
    tool_key = tool.lower()

    # -----------------------------------------------------------------------
    # Report-file parsing path (C++ only; all tiers may parse existing reports)
    # -----------------------------------------------------------------------
    if report_path is not None:
        from code_scalpel.code_parsers.cpp_parsers import CppParserRegistry

        registry = CppParserRegistry()
        try:
            parser = registry.get_parser(tool_key)
        except ValueError as exc:
            raise ValueError(str(exc)) from exc

        findings_raw = _parse_report(parser, tool_key, Path(report_path))
        findings_dicts = [_finding_to_dict(f) for f in findings_raw]

        max_findings = _COMMUNITY_MAX_FINDINGS if tier == "community" else -1
        truncated = False
        if max_findings > 0 and len(findings_dicts) > max_findings:
            findings_dicts = findings_dicts[:max_findings]
            truncated = True

        try:
            report_json = parser.generate_report(findings_raw, format="json")
            import json as _json

            report_data = _json.loads(report_json)
        except Exception:
            report_data = {"tool": tool_key, "findings": findings_dicts}

        return {
            "success": True,
            "language": "cpp",
            "tool": tool_key,
            "finding_count": len(findings_dicts),
            "findings": findings_dicts,
            "truncated": truncated,
            "max_findings_applied": max_findings if max_findings > 0 else None,
            "report": report_data,
            "tier_applied": tier,
        }

    # -----------------------------------------------------------------------
    # Tool-execution path — polyglot dispatch via run_static_tools
    # [20260305_REFACTOR] One call per path; community cap applied globally.
    # -----------------------------------------------------------------------
    all_findings: List[Dict[str, Any]] = []
    for path_str in paths:
        # run_static_tools auto-detects language from extension and applies
        # its own community cap per file; we re-apply globally below.
        per_file = _run_static_tools_for_file(path_str, [tool_key], tier)
        all_findings.extend(per_file)

    max_findings = _COMMUNITY_MAX_FINDINGS if tier == "community" else -1
    truncated = False
    if max_findings > 0 and len(all_findings) > max_findings:
        all_findings = all_findings[:max_findings]
        truncated = True

    # Best-effort language detection from first path with a known extension.
    detected_language = language.lower()
    if paths:
        ext = Path(paths[0]).suffix.lower()
        _ext_lang_map = {
            ".cpp": "cpp",
            ".cc": "cpp",
            ".cxx": "cpp",
            ".c": "cpp",
            ".h": "cpp",
            ".hpp": "cpp",
            ".hxx": "cpp",
            ".cs": "csharp",
            ".go": "go",
            ".py": "python",
            ".pyw": "python",
            ".js": "javascript",
            ".jsx": "javascript",
            ".ts": "typescript",
            ".tsx": "typescript",
            ".java": "java",
            ".rb": "ruby",
            ".swift": "swift",
            ".kt": "kotlin",
            ".kts": "kotlin",
            ".php": "php",
        }
        detected_language = _ext_lang_map.get(ext, language.lower())

    return {
        "success": True,
        "language": detected_language,
        "tool": tool_key,
        "finding_count": len(all_findings),
        "findings": all_findings,
        "truncated": truncated,
        "max_findings_applied": max_findings if max_findings > 0 else None,
        "report": {"tool": tool_key, "findings": all_findings},
        "tier_applied": tier,
    }


# ---------------------------------------------------------------------------
# Report parsing helpers (used only when report_path is provided — C++ only)
# ---------------------------------------------------------------------------


def _parse_report(parser: Any, tool_key: str, report_path: Path) -> List[Any]:
    """Dispatch to the correct parse_*_report method based on tool key."""
    suffix = report_path.suffix.lower()

    # Try format-specific methods first.
    if suffix in (".xml",) and hasattr(parser, "parse_xml_report"):
        return parser.parse_xml_report(report_path) or []
    if suffix in (".json",) and hasattr(parser, "parse_json_report"):
        return parser.parse_json_report(report_path) or []
    if suffix in (".plist",) and hasattr(parser, "parse_plist_report"):
        return parser.parse_plist_report(report_path) or []

    # Fallback: try xml then json then plist.
    for attr_name in ("parse_xml_report", "parse_json_report", "parse_plist_report"):
        if hasattr(parser, attr_name):
            try:
                result = getattr(parser, attr_name)(report_path) or []
                return result
            except Exception:
                continue
    return []


def _finding_to_dict(finding: Any) -> Dict[str, Any]:
    """Convert a dataclass/object finding to a plain dict."""
    if hasattr(finding, "__dataclass_fields__"):
        import dataclasses

        return dataclasses.asdict(finding)
    if hasattr(finding, "model_dump"):
        return finding.model_dump()
    if hasattr(finding, "__dict__"):
        return {k: v for k, v in finding.__dict__.items() if not k.startswith("_")}
    return {"value": str(finding)}


async def run_static_analysis(
    paths: List[str],
    tool: str = "cppcheck",
    language: str = "cpp",
    report_path: Optional[str] = None,
) -> ToolResponseEnvelope:
    """Run polyglot static-analysis helpers and return structured findings.

    [20260311_REFACTOR] This is no longer a public MCP tool. Public static
    analysis requests should flow through analyze_code(static_tools=...).

    Language is auto-detected from the file extension of each path in
    ``paths``.  When a tool CLI binary is not installed the parser returns an
    empty findings list (no error).  Provide ``report_path`` to parse a
    pre-existing C++ report file instead of executing the tool.

    **Tier Behavior:**
    - Community: Free tools — max 50 total findings.
      Enterprise-only tools (Coverity, SonarQube, ReSharper) are skipped.
    - Pro: Free tools — unlimited findings.
    - Enterprise: All tools including Coverity, SonarQube and ReSharper —
      unlimited findings.

    **Supported tools (``tool`` parameter) by language:**
    - C++  : ``cppcheck``, ``clang-tidy``, ``clang-sa``, ``cpplint``,
             ``coverity``\* (Enterprise), ``sonarqube``\* (Enterprise)
    - C#   : ``roslyn``, ``stylecop``, ``scs``, ``fxcop``,
             ``resharper``\* (Enterprise), ``sonarqube``\* (Enterprise)
    - Go     : ``gofmt``, ``golint``, ``govet``, ``staticcheck``,
               ``golangci-lint``, ``gosec``
    - Python : ``vulture``, ``isort``, ``radon``, ``radon-cc``, ``radon-mi``,
               ``pip-audit``, ``safety``, ``interrogate``
    - JS/TS  : ``npm-audit``
    - Java   : ``semgrep``
    - Ruby   : ``rubocop``, ``reek``, ``brakeman``, ``fasterer``
    - Swift  : ``swiftlint``, ``tailor``, ``sourcekitten``, ``swiftformat``
    - Kotlin : ``diktat``, ``compose``
    - PHP    : ``phpcs``, ``phpstan``, ``psalm``, ``phpmd``, ``exakat``

    **Args:**
        paths (List[str]): Source files or directories to analyse.
        tool (str): Static analysis tool to run. Default: ``cppcheck``.
        language (str): Hint for the source language (used for backward
            compatibility and report metadata).  Execution now relies on
            file-extension auto-detection.
        report_path (str, optional): Path to a pre-existing C++ report file.
            When provided the tool CLI is *not* executed; the report is parsed
            instead.  All tiers may parse enterprise tool reports.

    **Returns:**
        ToolResponseEnvelope with a dict containing:
        - success (bool): True if analysis completed without fatal errors.
        - language (str): Detected or provided language.
        - tool (str): Canonical tool name used.
        - finding_count (int): Number of findings returned.
        - findings (list[dict]): Structured findings.
        - truncated (bool): True if Community tier cap was applied.
        - max_findings_applied (int | None): Cap applied (None = unlimited).
        - report (dict): Full structured report from the parser.
        - tier_applied (str): Tier used for the request.
        - error (str, optional): Error message on failure.
        - duration_ms (int): Elapsed time in milliseconds.
    """
    import asyncio

    started = time.perf_counter()
    tier = _get_current_tier()

    try:
        from code_scalpel.mcp.helpers.session import _get_project_root

        # [20260311_BUGFIX] Normalize path inputs before helper dispatch so malformed
        # Windows/WSL drive paths return correction-aware errors instead of generic failures.
        base_root = str(_get_project_root())
        resolved_paths = [resolve_path(path, base_root) for path in paths]
        resolved_report_path = (
            resolve_path(report_path, base_root) if report_path is not None else None
        )

        try:
            result = await asyncio.to_thread(
                _run_static_analysis_sync,
                language,
                resolved_paths,
                tool,
                resolved_report_path,
                tier,
            )
            duration_ms = int((time.perf_counter() - started) * 1000)

            # Emit success telemetry
            try:
                telemetry.emit_tool_event(
                    tool_name="run_static_analysis",
                    tier_applied=tier,
                    duration_ms=float(duration_ms),
                    status="success",
                    input_summary={
                        "tool": tool,
                        "language": language,
                        "has_report_path": report_path is not None,
                        "path_count": len(resolved_paths),
                    },
                )
            except Exception as e:
                import logging

                logging.getLogger(__name__).warning(
                    f"Telemetry emit failed for run_static_analysis: {e}"
                )

            return make_envelope(
                data=result,
                tool_id="run_static_analysis",
                tool_version=_pkg_version,
                tier=tier,
                duration_ms=duration_ms,
            )
        except Exception as exc:
            duration_ms = int((time.perf_counter() - started) * 1000)

            # Emit failure telemetry
            try:
                telemetry.emit_tool_event(
                    tool_name="run_static_analysis",
                    tier_applied=tier,
                    duration_ms=float(duration_ms),
                    status="failure",
                    error=str(exc),
                    input_summary={
                        "tool": tool,
                        "language": language,
                        "has_report_path": report_path is not None,
                    },
                )
            except Exception as e:
                import logging

                logging.getLogger(__name__).warning(
                    f"Telemetry emit failed for run_static_analysis: {e}"
                )

            raise
    except FileNotFoundError as exc:
        duration_ms = int((time.perf_counter() - started) * 1000)
        return make_envelope(
            data=None,
            tool_id="run_static_analysis",
            tool_version=_pkg_version,
            tier=tier,
            duration_ms=duration_ms,
            error=ToolError(
                error=str(exc),
                error_code="correction_needed",
                error_details={"hint": str(exc)},
            ),
        )
    except Exception as exc:
        duration_ms = int((time.perf_counter() - started) * 1000)
        return make_envelope(
            data=None,
            tool_id="run_static_analysis",
            tool_version=_pkg_version,
            tier=tier,
            duration_ms=duration_ms,
            error=ToolError(error=str(exc), error_code="internal_error"),
        )
