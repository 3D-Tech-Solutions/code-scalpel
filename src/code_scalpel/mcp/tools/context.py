"""Context and discovery MCP tool registrations."""

from __future__ import annotations

import time

from mcp.server.fastmcp import Context

from code_scalpel.mcp.helpers.context_helpers import (
    crawl_project as _crawl_project,
    get_file_context as _get_file_context,
    get_symbol_references as _get_symbol_references,
)
from code_scalpel.mcp.protocol import mcp, _get_current_tier
from code_scalpel.mcp.contract import ToolResponseEnvelope, ToolError, make_envelope
from code_scalpel.mcp.oracle_middleware import (
    with_oracle_resilience,
    SymbolStrategy,
    PathStrategy,
)
from code_scalpel import __version__ as _pkg_version


@mcp.tool(
    description="Crawl a directory and return a file inventory with complexity metrics and security warnings."
)
@with_oracle_resilience(tool_id="crawl_project", strategy=PathStrategy)
async def crawl_project(
    root_path: str | None = None,
    exclude_dirs: list[str] | None = None,
    complexity_threshold: int = 10,
    include_report: bool = True,
    pattern: str | None = None,
    pattern_type: str = "regex",
    include_related: list[str] | None = None,
    ctx: Context | None = None,
) -> ToolResponseEnvelope:
    """Crawl a project directory and analyze Python files.

    **Tier Behavior:**
    - Community: Limited to 500 files, basic file tree indexing with language breakdown and entrypoint detection
    - Pro: Unlimited files/depth, parallel processing, incremental crawling, framework detection, dependency mapping, hotspot identification
    - Enterprise: Unlimited files/depth/repos, distributed crawling, historical trends, custom rules, compliance scanning, monorepo support

    **Tier Capabilities:**
    - Community: Full file tree indexing, language breakdown, gitignore respect, basic statistics, entrypoint detection (max 500 files, 10 depth)
    - Pro: All Community features + parallel processing, incremental crawling, smart crawl, framework entrypoint detection, dependency mapping, hotspot identification, generated code detection, Next.js/Django/Flask route detection (unlimited files/depth)
    - Enterprise: All Pro features + distributed crawling, historical trend analysis, custom crawl rules, compliance scanning, incremental indexing, monorepo support, cross-repo dependency linking, 100k+ files support (unlimited files/depth/repos)

    **Args:**
        root_path: Root directory to crawl (default: server's project root)
        exclude_dirs: List of directory names to exclude
        complexity_threshold: Threshold for complexity analysis (default: 10)
        include_report: Whether to include detailed report (default: True)
        pattern: Optional pattern to filter files
        pattern_type: Type of pattern matching ("regex" or "glob", default: "regex")
        include_related: Optional list of related file types to include

    **Returns:**
        ToolResponseEnvelope with crawl results:
        - success: True if crawl completed successfully
        - data: ProjectCrawlResult containing:
          - success: True if crawl succeeded
          - root_path: Project root path
          - timestamp: When the crawl was performed
          - summary: CrawlSummary with statistics (total_files, total_lines_of_code, total_functions, total_classes, complexity_warnings)
          - files: List of CrawlFileResult with detailed file analysis
          - errors: List of CrawlFileResult for files that failed analysis
          - markdown_report: Human-readable report
          - language_breakdown: Files per detected language (Pro/Enterprise)
          - cache_hits: Number of files reused from cache (Pro/Enterprise incremental)
          - framework_hints: Detected frameworks in discovery mode (Pro/Enterprise)
          - entrypoints: Detected entrypoint file paths (Pro/Enterprise)
          - compliance_summary: Enterprise compliance scanning results (Enterprise)
          - tier_applied: Which tier was used ("community"/"pro"/"enterprise")
          - crawl_mode: "discovery" (Community) or "deep" (Pro/Enterprise)
          - files_limit_applied: Max files limit applied (None=unlimited)
          - error: Error message if crawl failed
        - error: Error message if analysis failed (permission denied, invalid path, etc.)
        - tier_applied: Tier used for analysis (community/pro/enterprise)
        - duration_ms: Analysis duration in milliseconds
    """
    started = time.perf_counter()
    try:
        result = await _crawl_project(
            root_path=root_path,
            exclude_dirs=exclude_dirs,
            complexity_threshold=complexity_threshold,
            include_report=include_report,
            pattern=pattern,
            pattern_type=pattern_type,
            include_related=include_related,
            ctx=ctx,
        )
        duration_ms = int((time.perf_counter() - started) * 1000)
        tier = _get_current_tier()
        return make_envelope(
            data=result,
            tool_id="crawl_project",
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
            tool_id="crawl_project",
            tool_version=_pkg_version,
            tier=tier,
            duration_ms=duration_ms,
            error=error_obj,
        )


@mcp.tool(
    description="Get a file overview (functions, classes, imports, summary) without reading the full content."
)
@with_oracle_resilience(tool_id="get_file_context", strategy=PathStrategy)
async def get_file_context(file_path: str) -> ToolResponseEnvelope:
    """Get a file overview without reading full content.

    **Tier Behavior:**
    - Community: Limited to 500 lines of context, basic file structure analysis
    - Pro: Up to 2000 lines of context, code quality metrics and semantic analysis
    - Enterprise: Unlimited context lines, security redaction and organizational metadata

    **Tier Capabilities:**
    - Community: Basic file structure, imports, functions, classes (up to 500 lines)
    - Pro: Code smells detection, documentation coverage, maintainability index, semantic summarization, intent extraction, related imports inclusion, smart context expansion (up to 2000 lines)
    - Enterprise: PII redaction, secret masking, API key detection, RBAC-aware retrieval, file access control, custom metadata extraction, compliance flags, technical debt scoring, owner team mapping, historical metrics (unlimited lines)

    **Args:**
        file_path (str): Path to the file to analyze for context information

    **Returns:**
        ToolResponseEnvelope with file context summary:
        - success: True if analysis completed successfully
        - data: FileContextResult containing:
          - success: True if analysis succeeded
          - file_path: Path to the analyzed file
          - language: Detected language
          - line_count: Total lines in file
          - functions: Function names or detailed info
          - classes: Class names or detailed info
          - imports: Import statements (max 20)
          - exports: Exported symbols (__all__)
          - complexity_score: Overall cyclomatic complexity
          - has_security_issues: Whether file has security issues
          - summary: Brief description of file purpose
          - imports_truncated: Whether imports list was truncated
          - total_imports: Total imports before truncation
          - semantic_summary: AI-lite semantic summary when enabled (Pro)
          - intent_tags: Extracted intents/topics from docstrings/names (Pro)
          - related_imports: Resolved related imports for context expansion (Pro)
          - expanded_context: Smartly expanded context when allowed by tier limits (Pro)
          - pii_redacted: Whether PII content was redacted (Enterprise)
          - secrets_masked: Whether secrets/API keys were masked (Enterprise)
          - redaction_summary: What redactions/masking actions were taken (Enterprise)
          - access_controlled: Whether RBAC/file access controls were applied (Enterprise)
          - code_smells: Detected code smells (Pro)
          - doc_coverage: Documentation coverage percentage (Pro)
          - maintainability_index: Maintainability index (Pro)
          - custom_metadata: Custom metadata from .code-scalpel/metadata.yaml (Enterprise)
          - compliance_flags: Compliance flags detected (Enterprise)
          - technical_debt_score: Technical debt score (Enterprise)
          - owners: Code owners from CODEOWNERS file (Enterprise)
          - historical_metrics: Historical metrics from git (Enterprise)
          - tier_applied: The tier used for analysis
          - max_context_lines_applied: The max context lines limit applied
          - pro_features_enabled: Whether Pro tier features were enabled
          - enterprise_features_enabled: Whether Enterprise tier features were enabled
          - error: Error message if failed
        - error: Error message if analysis failed (file not found, invalid syntax, etc.)
        - tier_applied: Tier used for analysis (community/pro/enterprise)
        - duration_ms: Analysis duration in milliseconds
    """
    started = time.perf_counter()
    try:
        result = await _get_file_context(file_path)
        duration_ms = int((time.perf_counter() - started) * 1000)
        tier = _get_current_tier()
        return make_envelope(
            data=result,
            tool_id="get_file_context",
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
            tool_id="get_file_context",
            tool_version=_pkg_version,
            tier=tier,
            duration_ms=duration_ms,
            error=error_obj,
        )


@mcp.tool(
    description="Find all references, definitions, and call sites for a named symbol across the project, with an initial local JS/TS parity slice."
)
@with_oracle_resilience(tool_id="get_symbol_references", strategy=SymbolStrategy)
async def get_symbol_references(
    symbol_name: str,
    project_root: str | None = None,
    scope_prefix: str | None = None,
    include_tests: bool = True,
    ctx: Context | None = None,
) -> ToolResponseEnvelope:
    """Find all references to a symbol across the project.

    [20260308_DOCS] This workflow remains Python-first overall, but now includes
    an initial local JavaScript, TypeScript, and Java parity slice for
    definition/import/call-site discovery in non-Python source files.

    **Tier Behavior:**
     - Community: Limited to 200 files searched, 200 references returned, basic symbol location
    - Pro: Unlimited files and references, enhanced categorization (definition/import/call/read/write/reference), scope filtering, test file filtering
    - Enterprise: Unlimited files and references, CODEOWNERS integration, ownership attribution, impact analysis with risk scoring

    **Tier Capabilities:**
     - Community: Up to 200 files searched, 200 references returned
    - Pro: Unlimited files and references
    - Enterprise: Unlimited files and references

    **Args:**
        symbol_name: Name of the symbol to find references for
        project_root: Project root directory (default: server's project root)
        scope_prefix: Optional prefix to limit search scope
        include_tests: Whether to include test files in search (default: True)

    **Returns:**
        ToolResponseEnvelope with symbol references:
        - success: True if search completed successfully
        - data: SymbolReferencesResult containing:
          - success: True if search succeeded
          - symbol_name: Name of the searched symbol
          - definition_file: File where symbol is defined (if found)
          - definition_line: Line where symbol is defined (if found)
          - references: List of SymbolReference objects (max limited by tier):
            - file: File path containing the reference
            - line: Line number of the reference
            - column: Column number (default 0)
            - context: Code snippet showing usage context
            - is_definition: Whether this is the definition
            - reference_type: Category (definition/import/call/read/write/reference) (Pro+)
            - is_test_file: Whether reference is in a test file
            - owners: CODEOWNERS owners for the file (Enterprise)
          - total_references: Total reference count before truncation
          - files_scanned: Number of files actually scanned
          - total_files: Total candidate files before filtering
          - files_truncated: Whether file scanning was truncated
          - file_truncation_warning: Warning if file scan was truncated
          - category_counts: Counts by reference category (Pro+)
          - owner_counts: Counts by CODEOWNERS owner (Enterprise)
          - change_risk: Heuristic change risk assessment (Enterprise)
          - references_truncated: Whether references list was truncated
          - truncation_warning: Warning if results truncated
          - risk_score: Weighted risk score 0-100 (Enterprise)
          - risk_factors: List of factors contributing to risk (Enterprise)
          - tier_applied: Tier used for search (community/pro/enterprise)
          - max_files_applied: Max files limit applied
          - max_references_applied: Max references limit applied
          - pro_features_enabled: List of Pro features enabled
          - enterprise_features_enabled: List of Enterprise features enabled
        - error: Error message if search failed (invalid symbol, permission denied, etc.)
        - tier_applied: Tier used for analysis (community/pro/enterprise)
        - duration_ms: Search duration in milliseconds
    """
    started = time.perf_counter()
    try:
        result = await _get_symbol_references(
            symbol_name,
            project_root=project_root,
            scope_prefix=scope_prefix,
            include_tests=include_tests,
            ctx=ctx,
        )
        duration_ms = int((time.perf_counter() - started) * 1000)
        tier = _get_current_tier()
        return make_envelope(
            data=result,
            tool_id="get_symbol_references",
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
            tool_id="get_symbol_references",
            tool_version=_pkg_version,
            tier=tier,
            duration_ms=duration_ms,
            error=error_obj,
        )


__all__ = ["crawl_project", "get_file_context", "get_symbol_references"]
