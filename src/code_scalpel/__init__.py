"""
Code Scalpel - AI Agent toolkit for code analysis using ASTs, PDGs, and Symbolic Execution.

Code Scalpel provides precision tools for AI-driven code analysis and transformation,
enabling AI agents to perform deep analysis and surgical modifications of code.

Quick Start:
    >>> from code_scalpel import CodeAnalyzer
    >>> analyzer = CodeAnalyzer()
    >>> result = analyzer.analyze("def hello(): return 42")
    >>> print(result.metrics.num_functions)
    1

For MCP server:
    >>> from code_scalpel import run_server
    >>> run_server(port=8080)

For AI agent integrations:
    >>> from code_scalpel.integrations import AutogenScalpel, CrewAIScalpel
"""

# [20251228_FEATURE] Public sync wrappers for key MCP tools.
# These are convenience APIs used by tier/tooling validation tests.

# [20251225_RELEASE] v3.3.0 - Project Reorganization (Phases 1-4)
# [20260126_RELEASE] v1.1.0 - Kernel integration pilot for analyze_code
# [20260201_RELEASE] v1.3.0 - Oracle Resilience Middleware
# [20260202_RELEASE] v1.3.2 - Security hardening and CI alignment
# [20260202_RELEASE] v1.3.3 - Pipeline solidification and project organization
# [20260205_RELEASE] v1.3.4 - Bundled-only limits.toml, removed duplicate resolver internals
# [20260210_RELEASE] v1.3.5 - Windows encoding fix, auto-init fix, update check
# [20260220_RELEASE] v1.4.0 - Full response_config coverage (graph tools, hot-reload, template cleanup)
# [20260224_RELEASE] v2.0.0 - Polyglot Expansion: full C, C++, C# support (tree-sitter parsers, IR normalizers, MCP adapters)
# [20260225_RELEASE] v2.0.1 - Patch: documentation updates, wiki changelog backfill, packaging fix
# [20260225_RELEASE] v2.0.2 - C/C++/C# capabilities extended to unified_sink_detect, generate_unit_tests, code_policy_check, scan_dependencies
# [20260302_RELEASE] v2.1.0 - Go language support (GoNormalizer, GoVisitor, GoParserAdapter, tree-sitter-go)
__version__ = "2.1.0"
__author__ = "Timmothy Escolopio"
__email__ = "time@3dtechsolutions.us"

# [20251228_BUGFIX] Prefer reorganized modules to avoid importing deprecated
# shims (keeps backward-compatible top-level symbols without warning noise).
from .analysis.code_analyzer import (
    AnalysisLevel,
    AnalysisMetrics,
    AnalysisResult,
    CodeAnalyzer,
    DeadCodeItem,
    RefactorSuggestion,
    analyze_code,
)

# Project Crawler
from .analysis.project_crawler import (
    CrawlResult,
    FileAnalysisResult,
    ProjectCrawler,
    crawl_project,
)

# Core analysis
# AST tools
from .ast_tools import (
    ASTAnalyzer,
    ASTBuilder,
    ClassMetrics,
    FunctionMetrics,
    build_ast,
    build_ast_from_file,
)


# Autonomy (Error-to-Diff Engine) - v3.0.0 - NOW IN SEPARATE PACKAGE
# [20251225_REFACTOR] Autonomy moved to code-scalpel[agents] package (codescalpel_agents)
# Use lazy import for backward compatibility
def _get_autonomy_import(name: str):
    """Lazy loader for autonomy features (moved to codescalpel-agents package)."""
    try:
        import codescalpel_agents.autonomy as autonomy_module

        return getattr(autonomy_module, name)
    except ImportError as e:
        raise ImportError(
            "Autonomy features require the agents package. Install with: pip install codescalpel[agents]"
        ) from e


def __getattr__(name: str):
    """Lazy loader for optional dependencies (Autonomy, Flask REST API)."""
    # Autonomy exports (moved to codescalpel-agents)
    if name in (
        "ErrorAnalysis",
        "ErrorToDiffEngine",
        "ErrorType",
        "FixHint",
        "ParsedError",
    ):
        return _get_autonomy_import(name)

    # REST API server (moved to codescalpel-web, but kept here for backward compat)
    if name in ("MCPServerConfig", "create_app", "run_server"):
        try:
            from .integrations import rest_api_server

            return getattr(rest_api_server, name)
        except ImportError as e:
            raise ImportError(
                "REST API server requires Flask. Install with: pip install codescalpel[web]"
            ) from e

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


# PDG tools
from .pdg_tools import PDGAnalyzer, PDGBuilder, build_pdg  # noqa: E402

# Surgical Extractor (Token-efficient extraction)
from .surgery.surgical_extractor import (  # noqa: E402
    ContextualExtraction,
    CrossFileResolution,
    CrossFileSymbol,
    ExtractionResult,
    SurgicalExtractor,
    extract_class,
    extract_function,
    extract_method,
    extract_with_context,
)

# Surgical Patcher (Safe code modification)
from .surgery.surgical_patcher import (  # noqa: E402
    PatchResult,
    SurgicalPatcher,
    update_class_in_file,
    update_function_in_file,
    update_method_in_file,
)

# Unified Extractor (Multi-language extraction) - v3.1.0
# [20251221_FEATURE] v3.1.0 - Unified interface for all languages
from .surgery.unified_extractor import (  # noqa: E402
    Language,
    UnifiedExtractionResult,
    UnifiedExtractor,
    detect_language,
    extract_from_code,
    extract_from_file,
)

__all__ = [
    # Version info
    "__version__",
    "__author__",
    "__email__",
    # Core analysis
    "CodeAnalyzer",
    "AnalysisResult",
    "AnalysisLevel",
    "AnalysisMetrics",
    "DeadCodeItem",
    "RefactorSuggestion",
    "analyze_code",
    # AST tools
    "ASTAnalyzer",
    "ASTBuilder",
    "FunctionMetrics",
    "ClassMetrics",
    "build_ast",
    "build_ast_from_file",
    # PDG tools
    "PDGBuilder",
    "PDGAnalyzer",
    "build_pdg",
    # Project Crawler
    "ProjectCrawler",
    "CrawlResult",
    "FileAnalysisResult",
    "crawl_project",
    # Surgical Extractor
    "SurgicalExtractor",
    "ExtractionResult",
    "ContextualExtraction",
    "CrossFileSymbol",
    "CrossFileResolution",
    "extract_function",
    "extract_class",
    "extract_method",
    "extract_with_context",
    # Unified Extractor (v3.1.0)
    "UnifiedExtractor",
    "UnifiedExtractionResult",
    "Language",
    "detect_language",
    "extract_from_file",
    "extract_from_code",
    # Surgical Patcher
    "SurgicalPatcher",
    "PatchResult",
    "update_function_in_file",
    "update_class_in_file",
    "update_method_in_file",
    # MCP Server
    # [20260125_BUGFIX] These are available via __getattr__ for lazy-loading
    # noinspection PyUnresolvedReference
    "create_app",  # type: ignore[reportUnsupportedDunderAll]
    "run_server",  # type: ignore[reportUnsupportedDunderAll]
    "MCPServerConfig",  # type: ignore[reportUnsupportedDunderAll]
    # Autonomy (v3.0.0)
    # [20260125_BUGFIX] These are available via __getattr__ for lazy-loading from agents package
    # noinspection PyUnresolvedReference
    "ErrorToDiffEngine",  # type: ignore[reportUnsupportedDunderAll]
    "ErrorType",  # type: ignore[reportUnsupportedDunderAll]
    "ErrorAnalysis",  # type: ignore[reportUnsupportedDunderAll]
    "FixHint",  # type: ignore[reportUnsupportedDunderAll]
    "ParsedError",  # type: ignore[reportUnsupportedDunderAll]
    # MCP tool convenience wrappers
    "extract_code",
    "security_scan",
    "symbolic_execute",
    "generate_unit_tests",
    "simulate_refactor",
]  # type: ignore[reportUnsupportedDunderAll]


# [20251228_FEATURE] Provide sync wrappers around async MCP tool functions.
def _run_mcp_tool_sync(async_fn, /, *args, **kwargs):
    import asyncio
    from concurrent.futures import ThreadPoolExecutor

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(async_fn(*args, **kwargs))

    # Running inside an event loop (e.g., pytest-asyncio). Run in a separate thread.
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(lambda: asyncio.run(async_fn(*args, **kwargs)))
        return future.result()


def extract_code(
    *,
    target_type: str,
    target_name: str,
    file_path: str | None = None,
    code: str | None = None,
    language: str | None = None,
    include_context: bool = False,
    context_depth: int = 1,
    include_cross_file_deps: bool = False,
    include_token_estimate: bool = True,
):
    """[20251228_FEATURE] Sync wrapper for MCP extract_code tool."""
    from code_scalpel.mcp.tools.extraction import extract_code as _extract_code_async

    return _run_mcp_tool_sync(
        _extract_code_async,
        target_type=target_type,
        target_name=target_name,
        file_path=file_path,
        code=code,
        language=language,
        include_context=include_context,
        context_depth=context_depth,
        include_cross_file_deps=include_cross_file_deps,
        include_token_estimate=include_token_estimate,
    )


def security_scan(code: str | None = None, file_path: str | None = None):
    """[20251228_FEATURE] Sync wrapper for MCP security_scan tool."""
    from code_scalpel.mcp.tools.security import security_scan as _security_scan_async

    return _run_mcp_tool_sync(_security_scan_async, code=code, file_path=file_path)


def symbolic_execute(
    code: str, max_paths: int | None = None, max_depth: int | None = None
):
    """[20251228_FEATURE] Sync wrapper for MCP symbolic_execute tool."""
    from code_scalpel.mcp.tools.symbolic import (
        symbolic_execute as _symbolic_execute_async,
    )

    # Allow mixed value types for optional numeric parameters
    kwargs: dict[str, str | int] = {"code": code}
    if max_paths is not None:
        kwargs["max_paths"] = max_paths
    if max_depth is not None:
        kwargs["max_depth"] = max_depth
    return _run_mcp_tool_sync(_symbolic_execute_async, **kwargs)


def generate_unit_tests(
    code: str | None = None,
    file_path: str | None = None,
    function_name: str | None = None,
    framework: str = "pytest",
):
    """[20251228_FEATURE] Sync wrapper for MCP generate_unit_tests tool."""
    from code_scalpel.mcp.tools.symbolic import (
        generate_unit_tests as _generate_unit_tests_async,
    )

    return _run_mcp_tool_sync(
        _generate_unit_tests_async,
        code=code,
        file_path=file_path,
        function_name=function_name,
        framework=framework,
    )


def simulate_refactor(
    original_code: str,
    new_code: str | None = None,
    patch: str | None = None,
    strict_mode: bool = False,
):
    """[20251228_FEATURE] Sync wrapper for MCP simulate_refactor tool."""
    from code_scalpel.mcp.tools.symbolic import (
        simulate_refactor as _simulate_refactor_async,
    )

    return _run_mcp_tool_sync(
        _simulate_refactor_async,
        original_code=original_code,
        new_code=new_code,
        patch=patch,
        strict_mode=strict_mode,
    )
