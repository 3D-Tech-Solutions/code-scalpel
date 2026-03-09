"""Shared polyglot static-tool dispatch machinery.

[20260305_FEATURE] Extracted from mcp/tools/analyze.py so that *any* MCP tool
that needs to run language tool parsers (static_analysis, analyze_code, …) can
import the same dispatcher instead of duplicating logic.

Public surface
--------------
ENTERPRISE_EXEC_TOOLS       — set of tool names that require Enterprise tier
COMMUNITY_MAX_TOOL_FINDINGS — community findings cap
call_parser_method()        — calling-convention adapter
dispatch_tools()            — enterprise-gate + exception-handling loop
run_static_tools()          — top-level 11-language dispatcher
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Tier / capability constants
# ---------------------------------------------------------------------------

# [20260304_FEATURE] resharper added; sonar-cpp alias added
ENTERPRISE_EXEC_TOOLS: frozenset[str] = frozenset(
    {"coverity", "sonarqube", "sonar", "sonar-cpp", "resharper"}
)

COMMUNITY_MAX_TOOL_FINDINGS: int = 50


# ---------------------------------------------------------------------------
# Calling-convention adapter
# ---------------------------------------------------------------------------


def call_parser_method(
    parser: Any, method_name: str, file_path: str, call_style: str
) -> list:
    """Unified adapter for per-language execute-method calling conventions.

    [20260304_REFACTOR] Different languages expose different execute signatures:
      list_str   : method([file_path])        — C++, C#, Go (default)
      single_str : method(file_path)          — Python, JS/TS/npm-audit, Java/semgrep, PHP
      list_path  : method([Path(file_path)])  — Ruby, Swift
      single_path: method(Path(file_path))    — Kotlin

    Returns a normalised list regardless of what the method returns (list, dict, or None).
    """
    method = getattr(parser, method_name)
    if call_style == "single_str":
        raw = method(file_path)
    elif call_style == "list_path":
        raw = method([Path(file_path)])
    elif call_style == "single_path":
        raw = method(Path(file_path))
    else:  # "list_str" — default; used by C++, C#, Go
        raw = method([file_path])

    # Normalise: dict returns (e.g. Kotlin compose/diktat) and None
    if isinstance(raw, dict):
        return [raw] if raw else []
    return raw or []


# ---------------------------------------------------------------------------
# Common dispatch loop
# ---------------------------------------------------------------------------


def dispatch_tools(
    tools: list[str],
    registry: Any,
    exec_map: dict[str, str],
    file_path: str,
    tier: str,
    call_style: str = "list_str",
) -> list[dict]:
    """Enterprise-gate + exception-handling dispatch loop.

    [20260304_REFACTOR] Extracted to avoid duplicating the enterprise-gate +
    exception-handling logic for each language block.
    [20260304_FEATURE] call_style parameter routes to call_parser_method for
    per-language calling convention: list_str (C++/C#/Go), single_str
    (Python/JS/Java/PHP), list_path (Ruby/Swift), single_path (Kotlin).
    """
    import dataclasses

    findings: list[dict] = []
    for tool in tools:
        tool_key = tool.lower()
        if tool_key in ENTERPRISE_EXEC_TOOLS and tier != "enterprise":
            findings.append(
                {
                    "tool": tool_key,
                    "skipped": True,
                    "reason": f"Executing '{tool_key}' requires Enterprise tier.",
                }
            )
            continue
        try:
            parser = registry.get_parser(tool_key)
        except Exception:
            continue
        method_name = exec_map.get(tool_key)
        if not method_name or not hasattr(parser, method_name):
            continue
        try:
            raw = call_parser_method(parser, method_name, file_path, call_style)
        except (NotImplementedError, Exception):
            continue
        for f in raw:
            if hasattr(f, "__dataclass_fields__"):
                findings.append(dataclasses.asdict(f))
            elif hasattr(f, "model_dump"):
                findings.append(f.model_dump())
            elif hasattr(f, "__dict__"):
                findings.append(
                    {k: v for k, v in f.__dict__.items() if not k.startswith("_")}
                )
            else:
                findings.append({"value": str(f)})
    return findings


# ---------------------------------------------------------------------------
# Top-level 11-language dispatcher
# ---------------------------------------------------------------------------


def run_static_tools(file_path: str, tools: list[str], tier: str) -> list[dict]:
    """Synchronously dispatch to every supported language's tool parsers.

    [20260303_REFACTOR] Moved from standalone run_static_analysis tool into analyze_code.
    [20260304_FEATURE] Added C# dispatch alongside C++.
    [20260304_FEATURE] Added Go dispatch (gofmt, golint, govet, staticcheck, golangci, gosec).
    [20260304_FEATURE] Full polyglot: Python, JS/TS, Java, Ruby, Swift, Kotlin, PHP dispatch.
    [20260305_FEATURE] Extracted to shared helper so all MCP tools can reuse.

    Language is determined automatically from the file extension.
    Enterprise-only tools (coverity, sonarqube, resharper) skipped unless
    tier == 'enterprise'.
    Community tier caps total findings at COMMUNITY_MAX_TOOL_FINDINGS.
    """
    ext = Path(file_path).suffix.lower()

    # ── Extension sets ────────────────────────────────────────────────────────
    cpp_exts = {".cpp", ".cc", ".cxx", ".c++", ".c", ".h", ".hpp", ".hxx", ".hh", ".inl"}
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
        cpp_exts | cs_exts | go_exts | py_exts | js_exts | ts_exts
        | java_exts | rb_exts | swift_exts | kotlin_exts | php_exts
    )
    if ext not in _all_known:
        return []

    all_findings: list[dict] = []

    # ── C++ ───────────────────────────────────────────────────────────────────
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
        all_findings.extend(dispatch_tools(tools, registry, _TOOL_EXEC_METHODS, file_path, tier))

    # ── C# ────────────────────────────────────────────────────────────────────
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
        all_findings.extend(dispatch_tools(tools, registry, _TOOL_EXEC_METHODS, file_path, tier))

    # ── Go ────────────────────────────────────────────────────────────────────
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
        all_findings.extend(dispatch_tools(tools, registry, _TOOL_EXEC_METHODS, file_path, tier))

    # ── Python ────────────────────────────────────────────────────────────────
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
            dispatch_tools(tools, registry, _TOOL_EXEC_METHODS, file_path, tier, call_style="single_str")
        )

    # ── JavaScript (tools operate on project directory, not individual file) ──
    elif ext in js_exts:
        from code_scalpel.code_parsers.javascript_parsers import JavaScriptParserRegistry

        registry = JavaScriptParserRegistry()  # type: ignore[assignment]
        _TOOL_EXEC_METHODS = {
            "npm-audit": "execute_npm_audit",
            "npm_audit": "execute_npm_audit",
            # [20260304_FEATURE] ESLint operates on individual files
            "eslint": "execute_eslint",
        }
        project_dir = str(Path(file_path).parent)
        # npm-audit runs on the project dir; eslint runs on the file directly
        npm_tools = [t for t in tools if t.lower() in ("npm-audit", "npm_audit")]
        file_tools = [t for t in tools if t.lower() not in ("npm-audit", "npm_audit")]
        if npm_tools:
            all_findings.extend(
                dispatch_tools(npm_tools, registry, _TOOL_EXEC_METHODS, project_dir, tier, call_style="single_str")
            )
        if file_tools:
            all_findings.extend(
                dispatch_tools(file_tools, registry, _TOOL_EXEC_METHODS, file_path, tier, call_style="single_str")
            )

    # ── TypeScript (shares JS tools and project-dir convention) ───────────────
    elif ext in ts_exts:
        from code_scalpel.code_parsers.javascript_parsers import JavaScriptParserRegistry

        registry = JavaScriptParserRegistry()  # type: ignore[assignment]
        _TOOL_EXEC_METHODS = {
            "npm-audit": "execute_npm_audit",
            "npm_audit": "execute_npm_audit",
            # [20260304_FEATURE] ESLint operates on individual files
            "eslint": "execute_eslint",
        }
        project_dir = str(Path(file_path).parent)
        npm_tools = [t for t in tools if t.lower() in ("npm-audit", "npm_audit")]
        file_tools = [t for t in tools if t.lower() not in ("npm-audit", "npm_audit")]
        if npm_tools:
            all_findings.extend(
                dispatch_tools(npm_tools, registry, _TOOL_EXEC_METHODS, project_dir, tier, call_style="single_str")
            )
        if file_tools:
            all_findings.extend(
                dispatch_tools(file_tools, registry, _TOOL_EXEC_METHODS, file_path, tier, call_style="single_str")
            )

    # ── Java ──────────────────────────────────────────────────────────────────
    elif ext in java_exts:
        from code_scalpel.code_parsers.java_parsers import JavaParserRegistry

        registry = JavaParserRegistry()  # type: ignore[assignment]
        _TOOL_EXEC_METHODS = {
            "semgrep": "execute_semgrep",
            # [20260304_FEATURE] Checkstyle and PMD now have execute_* wrappers
            "checkstyle": "execute_checkstyle",
            "pmd": "execute_pmd",
        }
        all_findings.extend(
            dispatch_tools(tools, registry, _TOOL_EXEC_METHODS, file_path, tier, call_style="single_str")
        )

    # ── Ruby ──────────────────────────────────────────────────────────────────
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
            dispatch_tools(tools, registry, _TOOL_EXEC_METHODS, file_path, tier, call_style="list_path")
        )

    # ── Swift ─────────────────────────────────────────────────────────────────
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
            dispatch_tools(tools, registry, _TOOL_EXEC_METHODS, file_path, tier, call_style="list_path")
        )

    # ── Kotlin ────────────────────────────────────────────────────────────────
    elif ext in kotlin_exts:
        from code_scalpel.code_parsers.kotlin_parsers import KotlinParserRegistry

        registry = KotlinParserRegistry()  # type: ignore[assignment]
        # [20260306_FEATURE] Wire newly implemented Kotlin analyzers into shared dispatch.
        _TOOL_EXEC_METHODS = {
            "diktat": "execute_diktat",
            "compose": "execute_compiler_analysis",
            "detekt": "execute_detekt",
            "ktlint": "execute_ktlint",
        }
        all_findings.extend(
            dispatch_tools(tools, registry, _TOOL_EXEC_METHODS, file_path, tier, call_style="single_path")
        )

    # ── PHP ───────────────────────────────────────────────────────────────────
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
            dispatch_tools(tools, registry, _TOOL_EXEC_METHODS, file_path, tier, call_style="single_str")
        )

    if tier == "community" and len(all_findings) > COMMUNITY_MAX_TOOL_FINDINGS:
        all_findings = all_findings[:COMMUNITY_MAX_TOOL_FINDINGS]
    return all_findings
