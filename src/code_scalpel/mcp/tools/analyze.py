"""Analyze MCP tool registrations."""

from __future__ import annotations

import asyncio
import difflib
import os
import time
from typing import Any
from importlib import import_module
from pathlib import Path

from code_scalpel.mcp.helpers.analyze_helpers import _analyze_code_sync
from code_scalpel.mcp.contract import ToolResponseEnvelope, ToolError, make_envelope
from code_scalpel import __version__ as _pkg_version
from code_scalpel.mcp.oracle_middleware import with_oracle_resilience, PathStrategy
from code_scalpel.mcp.path_resolver import resolve_path
from code_scalpel.mcp.protocol import _get_current_tier
from code_scalpel.mcp.v1_1_kernel_adapter import get_adapter

# Avoid static import resolution issues in some type checkers
mcp = import_module("code_scalpel.mcp.protocol").mcp


# [20260305_REFACTOR] Polyglot dispatch extracted to shared helper.
# Import with distinct names to avoid shadowing by the thin wrapper defs below.
from code_scalpel.mcp.helpers.polyglot_dispatch import (
    COMMUNITY_MAX_TOOL_FINDINGS as _COMMUNITY_MAX_TOOL_FINDINGS,
    dispatch_tools as _polyglot_dispatch_tools,
)


def _run_static_tools(file_path: str, tools: list[str], tier: str) -> list[dict]:
    """Synchronously dispatch to language tool parsers and return merged findings.

    [20260303_REFACTOR] Moved from standalone run_static_analysis tool into analyze_code.
    [20260304_FEATURE] Added C# dispatch alongside C++ — language determined from extension.
    [20260304_FEATURE] Added Go dispatch (gofmt, golint, govet, staticcheck, golangci, gosec).
    [20260304_FEATURE] Full polyglot: Python, JS/TS, Java, Ruby, Swift, Kotlin, PHP dispatch.
    Enterprise-only tools (coverity, sonarqube, resharper) skipped unless tier == 'enterprise'.
    Community tier caps total findings at 50.
    """
    from pathlib import Path as _Path

    ext = _Path(file_path).suffix.lower()

    # ── Extension sets for every supported language ────────────────────────────
    cpp_exts = {
        ".cpp",
        ".cc",
        ".cxx",
        ".c++",
        ".c",
        ".h",
        ".hpp",
        ".hxx",
        ".hh",
        ".inl",
    }
    cs_exts = {".cs"}
    go_exts = {".go"}
    py_exts = {".py", ".pyw"}
    js_exts = {".js", ".jsx", ".mjs", ".cjs"}
    ts_exts = {".ts", ".tsx"}
    java_exts = {".java"}
    rb_exts = {".rb", ".rake", ".gemspec"}
    swift_exts = {".swift"}
    kotlin_exts = {".kt", ".kts"}
    php_exts = {".php", ".php3", ".php4", ".php5", ".phtml"}

    _all_known = (
        cpp_exts
        | cs_exts
        | go_exts
        | py_exts
        | js_exts
        | ts_exts
        | java_exts
        | rb_exts
        | swift_exts
        | kotlin_exts
        | php_exts
    )
    if ext not in _all_known:
        return []

    all_findings: list[dict] = []

    # ── C++ ──────────────────────────────────────────────────────────────────
    if ext in cpp_exts:
        from code_scalpel.code_parsers.cpp_parsers import CppParserRegistry

        registry = CppParserRegistry()
        _TOOL_EXEC_METHODS: dict[str, str] = {
            "cppcheck": "execute_cppcheck",
            "clang-tidy": "execute_clang_tidy",
            "clang_tidy": "execute_clang_tidy",
            "clang-sa": "execute_scan_build",
            "clang-static-analyzer": "execute_scan_build",
            "cpplint": "execute_cpplint",
            "coverity": "execute_coverity",
            "sonarqube": "execute_sonarqube",
            "sonar": "execute_sonarqube",
            "sonar-cpp": "execute_sonarqube",
        }
        all_findings.extend(
            _dispatch_tools(tools, registry, _TOOL_EXEC_METHODS, file_path, tier)
        )

    # ── C# ────────────────────────────────────────��──────────────────────────
    elif ext in cs_exts:
        from code_scalpel.code_parsers.csharp_parsers import CSharpParserRegistry

        registry = CSharpParserRegistry()  # type: ignore[assignment]
        _TOOL_EXEC_METHODS = {
            "roslyn": "execute_roslyn",
            "stylecop": "execute_stylecop",
            "scs": "execute_scs",
            "security-code-scan": "execute_scs",
            "fxcop": "execute_fxcop",
            "resharper": "execute_resharper",
            "sonarqube": "execute_sonarqube",
            "sonar": "execute_sonarqube",
        }
        all_findings.extend(
            _dispatch_tools(tools, registry, _TOOL_EXEC_METHODS, file_path, tier)
        )

    # ── Go ───────────────────────────────────────────────────────────────────
    elif ext in go_exts:
        from code_scalpel.code_parsers.go_parsers import GoParserRegistry

        registry = GoParserRegistry()  # type: ignore[assignment]
        _TOOL_EXEC_METHODS = {
            "gofmt": "execute_gofmt",
            "golint": "execute_golint",
            "govet": "execute_govet",
            "staticcheck": "execute_staticcheck",
            "golangci": "execute_golangci_lint",
            "golangci-lint": "execute_golangci_lint",
            "gosec": "execute_gosec",
        }
        all_findings.extend(
            _dispatch_tools(tools, registry, _TOOL_EXEC_METHODS, file_path, tier)
        )

    # ── Python ───────────────────────────────────────────────────────────────
    elif ext in py_exts:
        from code_scalpel.code_parsers.python_parsers import PythonParserRegistry

        registry = PythonParserRegistry()  # type: ignore[assignment]
        _TOOL_EXEC_METHODS = {
            "vulture": "execute_vulture",
            "isort": "execute_isort",
            "radon": "execute_radon_cc",
            "radon-cc": "execute_radon_cc",
            "radon-mi": "execute_radon_mi",
            "pip-audit": "execute_pip_audit",
            "safety": "execute_pip_audit",
            "interrogate": "execute_interrogate",
        }
        all_findings.extend(
            _dispatch_tools(
                tools,
                registry,
                _TOOL_EXEC_METHODS,
                file_path,
                tier,
                call_style="single_str",
            )
        )

    # ── JavaScript (JS tools operate on the project directory, not the file) ─
    elif ext in js_exts:
        from code_scalpel.code_parsers.javascript_parsers import (
            JavaScriptParserRegistry,
        )

        registry = JavaScriptParserRegistry()  # type: ignore[assignment]
        _TOOL_EXEC_METHODS = {
            "npm-audit": "execute_npm_audit",
            "npm_audit": "execute_npm_audit",
        }
        project_dir = str(_Path(file_path).parent)
        all_findings.extend(
            _dispatch_tools(
                tools,
                registry,
                _TOOL_EXEC_METHODS,
                project_dir,
                tier,
                call_style="single_str",
            )
        )

    # ── TypeScript (shares JS tools and project-dir convention) ──────────────
    elif ext in ts_exts:
        from code_scalpel.code_parsers.javascript_parsers import (
            JavaScriptParserRegistry,
        )

        registry = JavaScriptParserRegistry()  # type: ignore[assignment]
        _TOOL_EXEC_METHODS = {
            "npm-audit": "execute_npm_audit",
            "npm_audit": "execute_npm_audit",
        }
        project_dir = str(_Path(file_path).parent)
        all_findings.extend(
            _dispatch_tools(
                tools,
                registry,
                _TOOL_EXEC_METHODS,
                project_dir,
                tier,
                call_style="single_str",
            )
        )

    # ── Java ─────────────────────────────────────────────────────────────────
    elif ext in java_exts:
        from code_scalpel.code_parsers.java_parsers import JavaParserRegistry

        registry = JavaParserRegistry()  # type: ignore[assignment]
        _TOOL_EXEC_METHODS = {
            "semgrep": "execute_semgrep",
        }
        all_findings.extend(
            _dispatch_tools(
                tools,
                registry,
                _TOOL_EXEC_METHODS,
                file_path,
                tier,
                call_style="single_str",
            )
        )

    # ── Ruby ─────────────────────────────────────────────────────────────────
    elif ext in rb_exts:
        from code_scalpel.code_parsers.ruby_parsers import RubyParserRegistry

        registry = RubyParserRegistry()  # type: ignore[assignment]
        _TOOL_EXEC_METHODS = {
            "rubocop": "execute_rubocop",
            "reek": "execute_reek",
            "brakeman": "execute_brakeman",
            "fasterer": "execute_fasterer",
        }
        all_findings.extend(
            _dispatch_tools(
                tools,
                registry,
                _TOOL_EXEC_METHODS,
                file_path,
                tier,
                call_style="list_path",
            )
        )

    # ── Swift ────────────────────────────────────────────────────────────────
    elif ext in swift_exts:
        from code_scalpel.code_parsers.swift_parsers import SwiftParserRegistry

        registry = SwiftParserRegistry()  # type: ignore[assignment]
        _TOOL_EXEC_METHODS = {
            "swiftlint": "execute_swiftlint",
            "tailor": "execute_tailor",
            "sourcekitten": "execute_sourcekitten",
            "swiftformat": "execute_swiftformat",
        }
        all_findings.extend(
            _dispatch_tools(
                tools,
                registry,
                _TOOL_EXEC_METHODS,
                file_path,
                tier,
                call_style="list_path",
            )
        )

    # ── Kotlin ───────────────────────────────────────────────────────────────
    elif ext in kotlin_exts:
        from code_scalpel.code_parsers.kotlin_parsers import KotlinParserRegistry

        registry = KotlinParserRegistry()  # type: ignore[assignment]
        _TOOL_EXEC_METHODS = {
            "diktat": "execute_diktat",
            "compose": "execute_compiler_analysis",
        }
        all_findings.extend(
            _dispatch_tools(
                tools,
                registry,
                _TOOL_EXEC_METHODS,
                file_path,
                tier,
                call_style="single_path",
            )
        )

    # ── PHP ──────────────────────────────────────────────────────────────────
    elif ext in php_exts:
        from code_scalpel.code_parsers.php_parsers import PHPParserRegistry

        registry = PHPParserRegistry()  # type: ignore[assignment]
        _TOOL_EXEC_METHODS = {
            "phpcs": "execute_phpcs",
            "phpstan": "execute_phpstan",
            "psalm": "execute_psalm",
            "phpmd": "execute_phpmd",
            "exakat": "execute_exakat",
        }
        all_findings.extend(
            _dispatch_tools(
                tools,
                registry,
                _TOOL_EXEC_METHODS,
                file_path,
                tier,
                call_style="single_str",
            )
        )

    if tier == "community" and len(all_findings) > _COMMUNITY_MAX_TOOL_FINDINGS:
        all_findings = all_findings[:_COMMUNITY_MAX_TOOL_FINDINGS]
    return all_findings


def _dispatch_tools(
    tools: list[str],
    registry: Any,
    exec_map: dict[str, str],
    file_path: str,
    tier: str,
    call_style: str = "list_str",
) -> list[dict]:
    """[20260305_REFACTOR] Thin wrapper — delegates to polyglot_dispatch.dispatch_tools."""
    return _polyglot_dispatch_tools(
        tools, registry, exec_map, file_path, tier, call_style
    )


def _get_project_files(project_root: str | Path, max_files: int = 1000) -> list[str]:
    """Get list of all files in project for fuzzy matching suggestions.

    Args:
        project_root: Root directory of the project
        max_files: Maximum number of files to collect

    Returns:
        List of relative file paths from project root
    """
    project_root = Path(project_root).resolve()
    files = []

    def _collect_files(directory: Path, current_depth: int) -> None:
        """Recursive file collector with depth limit."""
        if current_depth > 5:  # Limit depth to avoid excessive scanning
            return

        try:
            for item in directory.iterdir():
                if item.name.startswith("."):
                    continue

                if item.is_dir():
                    # Skip common exclude directories
                    if item.name not in {
                        "node_modules",
                        "__pycache__",
                        ".git",
                        ".venv",
                        "venv",
                        ".pytest_cache",
                        ".mypy_cache",
                        ".ruff_cache",
                        "build",
                        "dist",
                    }:
                        _collect_files(item, current_depth + 1)
                elif item.is_file():
                    try:
                        relative_path = str(item.relative_to(project_root))
                        files.append(relative_path)
                        if len(files) >= max_files:
                            return
                    except ValueError:
                        # Skip files outside project root
                        continue

        except (PermissionError, OSError):
            # Skip directories we can't access
            pass

    _collect_files(project_root, 0)
    return files


def _find_similar_file_paths(
    invalid_path: str, project_files: list[str], max_suggestions: int = 3
) -> dict:
    """Find similar file paths using fuzzy string matching.

    Args:
        invalid_path: The invalid file path that was requested
        project_files: List of all valid file paths in the project
        max_suggestions: Maximum number of suggestions to return

    Returns:
        Dict with suggestion, confidence, message, and alternatives
    """
    if not project_files:
        return {}

    # Get filename from path for better matching
    invalid_filename = Path(invalid_path).name

    # Find closest matches using difflib
    matches = difflib.get_close_matches(
        invalid_path, project_files, n=max_suggestions * 2, cutoff=0.4
    )

    # Also try matching just the filename
    filename_matches = difflib.get_close_matches(
        invalid_filename,
        [Path(f).name for f in project_files],
        n=max_suggestions * 2,
        cutoff=0.6,
    )

    # Convert filename matches back to full paths
    filename_to_full = {Path(f).name: f for f in project_files}
    full_filename_matches = [
        filename_to_full[name] for name in filename_matches if name in filename_to_full
    ]

    # Combine and deduplicate matches
    all_matches = list(set(matches + full_filename_matches))

    if not all_matches:
        return {}

    # Calculate confidence scores (higher for better matches)
    scored_matches = []
    for match in all_matches[:max_suggestions]:
        # Use difflib ratio as confidence score
        confidence = difflib.SequenceMatcher(None, invalid_path, match).ratio()
        scored_matches.append((match, confidence))

    # Sort by confidence (highest first)
    scored_matches.sort(key=lambda x: x[1], reverse=True)

    best_match, best_confidence = scored_matches[0]
    alternatives = [match for match, _ in scored_matches[1:max_suggestions]]

    return {
        "suggestion": best_match,
        "confidence": round(best_confidence, 2),
        "message": f"Did you mean '{best_match}'?",
        "alternatives": alternatives,
    }


@mcp.tool(
    description="Parse and extract code structure (functions, classes, imports) from source text or a file. Pass static_tools to also run external linters (cppcheck, clang-tidy, clang-sa, cpplint; coverity/sonarqube on Enterprise) against the file."
)
@with_oracle_resilience(tool_id="analyze_code", strategy=PathStrategy)
async def analyze_code(
    code: str | None = None,
    language: str = "auto",
    file_path: str | None = None,
    static_tools: list[str] | None = None,
) -> ToolResponseEnvelope:
    """Analyze source code structure with AST parsing and metrics.

    Provide either 'code' (string) or 'file_path' (to read from file). Language is
    auto-detected if set to 'auto' (default). Use this tool to understand high-level
    architecture before attempting to edit, preventing hallucinated methods or classes.

    **Tier Behavior:**
    - Community: Basic AST parsing, functions/classes, complexity metrics, imports
    - Pro: All Community + cognitive complexity, code smells, Halstead metrics, duplicate detection
    - Enterprise: All Pro + custom rules, compliance checks, organization patterns, technical debt

    **Tier Capabilities:**
    - Community: Basic metrics only (max_file_size_mb=1)
    - Pro: All Community + advanced metrics and smells (max_file_size_mb=10)
    - Enterprise: All Pro + custom rules, compliance checks (max_file_size_mb=100)

    **Args:**
        code (str, optional): Source code to analyze. Either code or file_path required.
        language (str): Programming language for analysis. Default: "auto" (auto-detect).
                       Supported: python, javascript, typescript, java, c, cpp, csharp, go, kotlin, php, ruby, swift, rust
        file_path (str, optional): Path to file to analyze. Either code or file_path required.
        static_tools (list[str], optional): External static-analysis tools to run against
            file_path in addition to AST analysis.  Requires file_path.
            Community/Pro: ["cppcheck", "clang-tidy", "clang-sa", "cpplint"].
            Enterprise: also ["coverity", "sonarqube"] (report files via parse path).
            Results are returned in ``tool_findings`` of the response.

    **Returns:**
        ToolResponseEnvelope with AnalysisResult containing:
        - success (bool): True if analysis completed successfully
        - functions (list[str]): Function names found
        - classes (list[str]): Class names found
        - imports (list[str]): Import statements
        - complexity (int): Cyclomatic complexity estimate
        - lines_of_code (int): Total lines of code
        - function_details (list[dict]): Function info with line numbers, async status
        - class_details (list[dict]): Class info with line numbers, methods
        - issues (list[dict]): Issues found during analysis
        - cognitive_complexity (int): Cognitive complexity score (Pro/Enterprise, 0 if Community)
        - code_smells (list[dict]): Detected code smells (Pro/Enterprise, empty if Community)
        - halstead_metrics (dict, optional): Halstead complexity metrics (Pro/Enterprise, None if not computed)
        - duplicate_code_blocks (list[dict]): Detected duplicate code blocks (Pro/Enterprise)
        - dependency_graph (dict): Function call adjacency map (Pro/Enterprise)
        - naming_issues (list[dict]): Naming convention issues (Enterprise)
        - compliance_issues (list[dict]): Compliance findings (Enterprise)
        - custom_rule_violations (list[dict]): Custom rule matches (Enterprise)
        - organization_patterns (list[dict]): Detected architectural patterns (Enterprise)
        - frameworks (list[str]): Detected frameworks (Pro/Enterprise)
        - dead_code_hints (list[dict]): Dead code candidates (Pro/Enterprise)
        - decorator_summary (dict): Decorator/annotation summary (Pro/Enterprise)
        - type_summary (dict): Type annotation summary (Pro/Enterprise)
        - architecture_patterns (list[str]): Architecture/service-pattern hints (Enterprise)
        - technical_debt (dict): Technical debt scoring summary (Enterprise)
        - api_surface (dict): API surface summary (Enterprise)
        - prioritized (bool): Whether outputs were priority-ordered (Enterprise)
        - complexity_trends (dict): Historical complexity trend summary (Enterprise)
        - language_detected (str): Language that was actually analyzed
        - tier_applied (str): Tier applied for feature gating
        - error_location (dict, optional): Line/column of syntax error if applicable
        - suggested_fix (str, optional): Suggested fix for syntax error when applicable
        - sanitization_report (dict, optional): Parsing sanitization details
        - parser_warnings (list[str]): Parser warnings (e.g., sanitization notices)
        - tool_findings (list[dict]): Findings from external static tools (when static_tools
            requested and file_path provided). Empty when not requested.
        - error (str): Error message if analysis failed (invalid code, file not found, etc.)
        - tier_applied (str): Tier used for analysis
        - duration_ms (int): Analysis duration in milliseconds
    """
    started = time.perf_counter()
    try:
        adapter = get_adapter()
        tier = _get_current_tier()
        supported_languages = {
            "auto",
            "python",
            "javascript",
            "typescript",
            "java",
            "c",
            "cpp",
            "csharp",
            "go",
            "kotlin",
            "php",
            "ruby",
            "swift",
            "rust",
        }

        # 1. Validate input: either code or file_path must be provided
        if code is None and file_path is None:
            return make_envelope(
                data=None,
                tool_id="analyze_code",
                tool_version=_pkg_version,
                tier=tier,
                duration_ms=int((time.perf_counter() - started) * 1000),
                error=ToolError(
                    error="Either 'code' or 'file_path' must be provided.",
                    error_code="invalid_argument",
                    error_details={
                        "hint": "Provide source code directly or pass a file_path to analyze."
                    },
                ),
            )

        if static_tools and file_path is None:
            return make_envelope(
                data=None,
                tool_id="analyze_code",
                tool_version=_pkg_version,
                tier=tier,
                duration_ms=int((time.perf_counter() - started) * 1000),
                error=ToolError(
                    error="'static_tools' requires 'file_path'.",
                    error_code="invalid_argument",
                    error_details={"static_tools": static_tools},
                ),
            )

        normalized_language = (language or "auto").lower()
        if normalized_language not in supported_languages:
            return make_envelope(
                data=None,
                tool_id="analyze_code",
                tool_version=_pkg_version,
                tier=tier,
                duration_ms=int((time.perf_counter() - started) * 1000),
                error=ToolError(
                    error=(
                        f"Unsupported language: {language}. Must be one of "
                        f"{sorted(supported_languages)}"
                    ),
                    error_code="invalid_argument",
                    error_details={"supported_languages": sorted(supported_languages)},
                ),
            )

        # If code is not provided, read from file_path
        if code is None and file_path is not None:
            # Get tier for limits
            from code_scalpel.mcp.helpers.analyze_helpers import get_tool_capabilities
            from code_scalpel.mcp.helpers.session import _get_project_root

            capabilities = get_tool_capabilities("analyze_code", tier)
            limit_mb = capabilities.get("limits", {}).get("max_file_size_mb")

            project_root = _get_project_root()
            try:
                file_path = resolve_path(
                    file_path,
                    str(project_root) if project_root else None,
                )
            except FileNotFoundError as exc:
                error_details: dict[str, Any] = {"hint": str(exc)}
                if project_root:
                    try:
                        project_files = _get_project_files(
                            str(project_root), max_files=500
                        )
                        oracle_suggestion = _find_similar_file_paths(
                            file_path, project_files
                        )
                        if oracle_suggestion:
                            error_details["oracle_suggestion"] = oracle_suggestion
                    except Exception:
                        pass

                error_obj = ToolError(
                    error=str(exc),
                    error_code="correction_needed",
                    error_details=error_details,
                )
                duration_ms = int((time.perf_counter() - started) * 1000)
                return make_envelope(
                    data=None,
                    tool_id="analyze_code",
                    tool_version=_pkg_version,
                    tier=tier,
                    duration_ms=duration_ms,
                    error=error_obj,
                )

            # Check file size before reading
            file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
            if limit_mb is not None and file_size_mb > limit_mb:
                raise ValueError(
                    f"File size {file_size_mb:.2f} MB exceeds limit of {limit_mb} MB for {tier} tier"
                )

            # Read the file
            with open(file_path, "r", encoding="utf-8") as f:
                code = f.read()

        try:
            ctx = adapter.create_source_context(
                code=code, file_path=file_path, language=language
            )
            is_valid, error_obj, suggestions = adapter.validate_input(ctx)

            if not is_valid and error_obj:
                # Return error response with self-correction suggestions
                duration_ms = int((time.perf_counter() - started) * 1000)
                # Enhance error with suggestions
                error_obj.error_details = error_obj.error_details or {}
                error_obj.error_details["suggestions"] = suggestions
                return make_envelope(
                    data=None,
                    tool_id="analyze_code",
                    tool_version=_pkg_version,
                    tier=tier,
                    duration_ms=duration_ms,
                    error=error_obj,
                )
        except ValueError:
            # Validation setup error
            pass  # Continue with legacy code path

        result = await asyncio.to_thread(
            _analyze_code_sync, code or "", language, file_path
        )
        # [20260303_REFACTOR] Run external static-analysis tools if requested.
        if static_tools and file_path:
            result.tool_findings = await asyncio.to_thread(
                _run_static_tools, file_path, static_tools, tier
            )
        duration_ms = int((time.perf_counter() - started) * 1000)
        return make_envelope(
            data=result,
            tool_id="analyze_code",
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
            tool_id="analyze_code",
            tool_version=_pkg_version,
            tier=tier,
            duration_ms=duration_ms,
            error=error_obj,
        )


__all__ = ["analyze_code"]
