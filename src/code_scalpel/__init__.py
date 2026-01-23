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
__version__ = "1.0.1"
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

# Autonomy (Error-to-Diff Engine) - v3.0.0
# [20251217_FEATURE] v3.0.0 Autonomy - Error-to-Diff Engine
from .autonomy import ErrorAnalysis, ErrorToDiffEngine, ErrorType, FixHint, ParsedError

# REST API Server (legacy) - LAZY IMPORT
# [20260112_BUGFIX] Flask is optional (code-scalpel[web]). Use lazy imports to avoid
# crash on bare `pip install code-scalpel`. Users who need REST API should either:
# 1. Install: pip install code-scalpel[web]
# 2. Import directly: from code_scalpel.integrations.rest_api_server import run_server


def __getattr__(name: str):
    """Lazy loader for optional dependencies (Flask REST API)."""
    if name in ("MCPServerConfig", "create_app", "run_server"):
        try:
            from .integrations import rest_api_server

            return getattr(rest_api_server, name)
        except ImportError as e:
            raise ImportError("REST API server requires Flask. Install with: pip install code-scalpel[web]") from e
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
    # Autonomy (v3.0.0)
    "ErrorToDiffEngine",
    "ErrorType",
    "ErrorAnalysis",
    "FixHint",
    "ParsedError",
    # MCP tool convenience wrappers
    "extract_code",
    "security_scan",
    "symbolic_execute",
    "generate_unit_tests",
    "simulate_refactor",
]


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
    from code_scalpel.mcp.server import extract_code as _extract_code_async

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
    from code_scalpel.mcp.server import security_scan as _security_scan_async

    return _run_mcp_tool_sync(_security_scan_async, code=code, file_path=file_path)


def symbolic_execute(code: str, max_paths: int | None = None, max_depth: int | None = None):
    """[20251228_FEATURE] Sync wrapper for MCP symbolic_execute tool."""
    from code_scalpel.mcp.server import (
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
    from code_scalpel.mcp.server import (
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
    from code_scalpel.mcp.server import (
        simulate_refactor as _simulate_refactor_async,
    )

    return _run_mcp_tool_sync(
        _simulate_refactor_async,
        original_code=original_code,
        new_code=new_code,
        patch=patch,
        strict_mode=strict_mode,
    )
