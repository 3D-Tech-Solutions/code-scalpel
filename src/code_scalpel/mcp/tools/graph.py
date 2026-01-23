"""Graph MCP tool registrations.

[20260121_REFACTOR] Wrap outputs in ToolResponseEnvelope for MCP contract
consistency (tier metadata, duration, standardized errors).
"""

from __future__ import annotations

import asyncio
from typing import Any

from mcp.server.fastmcp import Context

from code_scalpel import __version__ as _pkg_version
from code_scalpel.licensing.features import get_tool_capabilities, has_capability
from code_scalpel.mcp.contract import ToolResponseEnvelope, envelop_tool_function
from code_scalpel.mcp.helpers.graph_helpers import (
    _cross_file_security_scan_sync,
    _get_call_graph_sync,
    _get_cross_file_dependencies_sync,
    _get_graph_neighborhood_sync,
    _get_project_map_sync,
)
from code_scalpel.mcp.protocol import _get_current_tier as _tier_getter
from code_scalpel.mcp.protocol import mcp


def _get_current_tier() -> str:
    """Get current tier using JWT validation (late import to avoid circular dependency)."""
    from code_scalpel.mcp.server import _get_current_tier as get_tier

    return get_tier()


def _coerce_int(value):
    """Coerce common numeric inputs to int when possible."""
    if value is None:
        return None
    if isinstance(value, int):
        return value
    try:
        # Handles numeric strings and floats like '3' or '3.0'
        return int(float(value))
    except Exception:
        return None  # Return None for invalid values


def _coerce_float(value):
    """Coerce common numeric inputs to float when possible."""
    if value is None:
        return None
    if isinstance(value, float):
        return value
    try:
        return float(value)
    except Exception:
        return None
        return None
    if isinstance(value, float):
        return value
    try:
        return float(value)
    except Exception:
        return value


async def _get_call_graph_tool(
    project_root: str | None = None,
    entry_point: str | None = None,
    depth: int = 10,
    include_circular_import_check: bool = True,
    paths_from: str | None = None,
    paths_to: str | None = None,
    focus_functions: list[str] | None = None,
    ctx: Context | None = None,
) -> Any:
    """
    Build a call graph showing function relationships in the project.

    **Tier Behavior:**
    - All tiers: Tool is available.
    - Limits and optional enhancements are applied based on tool capabilities.

    [v1.5.0] Use this tool to understand code flow and function dependencies.
    Analyzes Python source files to build a static call graph with:
    - Line number tracking for each function
    - Entry point detection (main, CLI commands, routes)
    - Depth-limited traversal from any starting function
    - Mermaid diagram generation for visualization
    - Circular import detection

    [v3.0.5] Now reports progress during graph construction.
    [v3.2.8] Tier-based depth limiting for Community tier.
    [v3.3.0] Added path queries, focus mode, call context, and confidence scoring.

    **v3.3.0 Features:**
    - **Path Queries:** Use paths_from and paths_to to find all call paths between functions
    - **Focus Mode:** Use focus_functions to extract a subgraph centered on specific functions
    - **Call Context:** Each edge includes context (in_loop, in_try_block, in_conditional)
    - **Confidence Scoring:** Each edge includes confidence (1.0=static, 0.8=type_hint, 0.5=inferred)
    - **Source URIs:** Each node includes source_uri for IDE click-through (file:///path#L42)

    Why AI agents need this:
    - Navigation: Quickly understand how functions connect
    - Impact analysis: See what breaks if you change a function
    - Refactoring: Identify tightly coupled code
    - Documentation: Generate visual diagrams of code flow
    - Security: Find call paths from user input to dangerous sinks

    Args:
        project_root: Project root directory (default: server's project root)
        entry_point: Starting function name (e.g., "main" or "app.py:main")
                    If None, includes all functions
        depth: Maximum depth to traverse from entry point (default: 10)
        include_circular_import_check: Check for circular imports (default: True)
        paths_from: Source function for path query (e.g., "routes.py:handle_request")
        paths_to: Sink function for path query (e.g., "db.py:execute_query")
        focus_functions: List of functions to focus the subgraph on

    Returns:
        CallGraphResultModel with nodes, edges, Mermaid diagram, paths, and any circular imports
    """
    # [20251220_FEATURE] v3.0.5 - Progress reporting
    if ctx:
        await ctx.report_progress(0, 100, "Building call graph...")

    # [20251225_FEATURE] Capability-driven tier behavior (no upgrade hints)
    tier = _get_current_tier()
    caps = get_tool_capabilities("get_call_graph", tier) or {}
    limits = caps.get("limits", {}) or {}
    cap_set = set(caps.get("capabilities", []) or [])

    max_depth = limits.get("max_depth")
    max_nodes = limits.get("max_nodes")

    # [20260120_FIX] Ensure limits are integers (TOML values should be int, but ensure type safety)
    if max_depth is not None:
        max_depth = int(max_depth)
    if max_nodes is not None:
        max_nodes = int(max_nodes)

    actual_depth = depth
    if max_depth is not None and depth > max_depth:
        actual_depth = max_depth

    # [20260121_BUGFIX] Enable tier-driven advanced resolution and enterprise metrics
    advanced_resolution = "advanced_call_graph" in cap_set
    include_enterprise_metrics = bool(
        {"hot_path_identification", "dead_code_detection", "custom_graph_analysis"} & cap_set
    )

    # [20260120_FEATURE] Call sync function with tier/capabilities for metadata transparency
    result = await asyncio.to_thread(
        _get_call_graph_sync,
        project_root,
        entry_point,
        actual_depth,
        include_circular_import_check,
        max_nodes,
        advanced_resolution,
        include_enterprise_metrics,
        paths_from,
        paths_to,
        focus_functions,
        tier,
        caps,
    )

    # [20260120_FEATURE] Metadata already populated by sync function with tier/caps
    if ctx:
        node_count = len(result.nodes) if result.nodes else 0
        edge_count = len(result.edges) if result.edges else 0
        await ctx.report_progress(
            100,
            100,
            f"Call graph complete: {node_count} functions, {edge_count} calls",
        )

    return result


get_call_graph = mcp.tool()(
    envelop_tool_function(
        _get_call_graph_tool,
        tool_id="get_call_graph",
        tool_version=_pkg_version,
        tier_getter=_tier_getter,
    )
)


async def _get_graph_neighborhood_tool(
    center_node_id: str,
    k: int = 2,
    max_nodes: int = 100,
    direction: str = "both",
    min_confidence: float = 0.0,
    project_root: str | None = None,
    query: str | None = None,
) -> Any:
    """
    Extract k-hop neighborhood subgraph around a center node.

    **Tier Behavior:**
    - All tiers: Tool is available.
    - Limits and optional enhancements are applied based on tool capabilities.

    [v2.5.0] Use this tool to prevent graph explosion when analyzing large
    codebases. Instead of loading the entire graph, extract only the nodes
    within k hops of a specific node.

    [v3.2.8] Tier-based hop limiting for Community tier.
    [v3.5.0] Enterprise: Graph query language support.

    **Graph Pruning Formula:** N(v, k) = {u ∈ V : d(v, u) ≤ k}

    This extracts all nodes u where the shortest path from center v to u
    is at most k hops.

    **Truncation Protection:**
    If the neighborhood exceeds max_nodes, the graph is truncated and
    a warning is returned. This prevents memory exhaustion on dense graphs.

    Key capabilities:
    - Extract focused subgraph around any node
    - Control traversal depth with k parameter
    - Limit graph size with max_nodes
    - Filter by edge direction (incoming, outgoing, both)
    - Filter by minimum confidence score
    - Generate Mermaid visualization
    - Pro: Semantic neighbors and logical relationships
    - Enterprise: Query language for custom graph traversals

    Why AI agents need this:
    - **Focused Analysis:** Analyze only relevant code, not entire codebase
    - **Memory Safety:** Prevent OOM on large graphs
    - **Honest Uncertainty:** Know when graph is incomplete

    Example:
        # Get 2-hop neighborhood around a function
        result = get_graph_neighborhood(
            center_node_id="python::services::function::process_order",
            k=2,
            max_nodes=50
        )
        if result.truncated:
            print(f"Warning: {result.truncation_warning}")

        # Enterprise: Use query language
        result = get_graph_neighborhood(
            center_node_id="python::controllers::function::handle_request",
            query="MATCH (n)-[:calls]->(m:function) WHERE m.name CONTAINS 'DB' RETURN n, m"
        )

    Args:
        center_node_id: ID of the center node (format: language::module::type::name)
        k: Maximum hops from center (default: 2)
        max_nodes: Maximum nodes to include (default: 100)
        direction: "outgoing", "incoming", or "both" (default: "both")
        min_confidence: Minimum edge confidence to follow (default: 0.0)
        project_root: Project root directory (default: server's project root)
        query: Graph query language (Enterprise tier only)

    Returns:
        GraphNeighborhoodResult with subgraph, truncation info, and Mermaid diagram
    """
    return await asyncio.to_thread(
        _get_graph_neighborhood_sync,
        center_node_id,
        k,
        max_nodes,
        direction,
        min_confidence,
        project_root,
        query,
    )


get_graph_neighborhood = mcp.tool()(
    envelop_tool_function(
        _get_graph_neighborhood_tool,
        tool_id="get_graph_neighborhood",
        tool_version=_pkg_version,
        tier_getter=_tier_getter,
    )
)


async def _get_project_map_tool(
    project_root: str | None = None,
    include_complexity: bool = True,
    complexity_threshold: int = 10,
    include_circular_check: bool = True,
    detect_service_boundaries: bool = False,
    min_isolation_score: float = 0.6,
    ctx: Context | None = None,
) -> Any:
    """
    Generate a comprehensive map of the project structure.

    [v1.5.0] Use this tool to get a high-level overview of a codebase before diving in.
    Analyzes all Python files to provide:
    - Package and module structure
    - Function and class inventory per file
    - Entry point detection (main, CLI commands, routes)
    - Complexity hotspots (files that need attention)
    - Circular import detection
    - Mermaid diagram of project structure

    [v3.0.5] Now reports progress during analysis.

    Why AI agents need this:
    - Orientation: Understand project structure before making changes
    - Navigation: Know where to find specific functionality
    - Risk assessment: Identify complex areas that need careful handling
    - Architecture: See how packages and modules are organized

    Args:
        project_root: Project root directory (default: server's project root)
        include_complexity: Calculate cyclomatic complexity (default: True)
        complexity_threshold: Threshold for flagging hotspots (default: 10)
        include_circular_check: Check for circular imports (default: True)

    Returns:
        ProjectMapResult with comprehensive project overview
    """
    # [20251220_FEATURE] v3.0.5 - Progress reporting
    if ctx:
        await ctx.report_progress(0, 100, "Scanning project structure...")

    tier = _get_current_tier()
    caps = get_tool_capabilities("get_project_map", tier) or {}
    limits = caps.get("limits", {}) or {}

    result = await asyncio.to_thread(
        _get_project_map_sync,
        project_root,
        include_complexity,
        complexity_threshold,
        include_circular_check,
        tier=tier,
        capabilities=caps,
        max_files_limit=limits.get("max_files"),
        max_modules_limit=limits.get("max_modules"),
    )

    # Enterprise feature: suggest service boundaries (not a standalone MCP tool).
    if detect_service_boundaries:
        if not has_capability("extract_code", "service_boundaries", tier):
            try:
                result = result.model_copy(
                    update={
                        "service_boundaries_success": False,
                        "service_boundaries_error": "Service boundary detection requires ENTERPRISE tier",
                    }
                )
            except Exception:
                pass
        else:
            try:
                from code_scalpel.surgery.surgical_extractor import (
                    detect_service_boundaries as _detect_boundaries,
                )

                boundaries = await asyncio.to_thread(
                    _detect_boundaries,
                    project_root=project_root,
                    min_isolation_score=min_isolation_score,
                )

                if getattr(boundaries, "success", False):
                    payload: dict[str, Any] = {
                        "service_boundaries_success": True,
                        "suggested_services": [
                            {
                                "service_name": s.service_name,
                                "included_files": s.included_files,
                                "external_dependencies": s.external_dependencies,
                                "internal_dependencies": s.internal_dependencies,
                                "isolation_level": s.isolation_level,
                                "rationale": s.rationale,
                            }
                            for s in boundaries.suggested_services
                        ],
                        "service_dependency_graph": boundaries.dependency_graph,
                        "service_total_files_analyzed": boundaries.total_files_analyzed,
                        "service_boundaries_explanation": boundaries.explanation,
                    }
                else:
                    payload = {
                        "service_boundaries_success": False,
                        "service_boundaries_error": getattr(boundaries, "error", None)
                        or "Service boundary detection failed",
                    }

                result = result.model_copy(update=payload)
            except Exception as e:
                try:
                    result = result.model_copy(
                        update={
                            "service_boundaries_success": False,
                            "service_boundaries_error": f"Service boundary detection failed: {e}",
                        }
                    )
                except Exception:
                    pass

    if ctx:
        msg = f"Analyzed {result.total_files} files, {result.total_lines} lines"
        await ctx.report_progress(100, 100, msg)

    return result


get_project_map = mcp.tool()(
    envelop_tool_function(
        _get_project_map_tool,
        tool_id="get_project_map",
        tool_version=_pkg_version,
        tier_getter=_tier_getter,
    )
)


async def _get_cross_file_dependencies_tool(
    target_file: str,
    target_symbol: str,
    project_root: str | None = None,
    max_depth: int = 3,
    include_code: bool = True,
    include_diagram: bool = True,
    confidence_decay_factor: float = 0.9,
    max_files: int | None = None,
    timeout_seconds: float | None = None,
) -> Any:
    """
    Analyze and extract cross-file dependencies for a symbol.

    [v2.5.0] Use this tool to understand all dependencies a function/class needs
    from other files in the project. It recursively resolves imports and extracts
    the complete dependency chain with source code.

    **Confidence Decay (v2.5.0):**
    Deep dependency chains get exponentially decaying confidence scores.
    Formula: C_effective = 1.0 × confidence_decay_factor^depth

    | Depth | Confidence (factor=0.9) |
    |-------|------------------------|
    | 0     | 1.000 (target)         |
    | 1     | 0.900                  |
    | 2     | 0.810                  |
    | 5     | 0.590                  |
    | 10    | 0.349                  |

    Symbols with confidence < 0.5 are flagged as "low confidence".

    Key capabilities:
    - Resolve imports to their source files
    - Extract code for all dependent symbols
    - Detect circular import cycles
    - Generate import relationship diagrams
    - Provide combined code block ready for AI analysis
    - **Confidence scoring** for each symbol based on depth

    Why AI agents need this:
    - Complete Context: Get all code needed to understand a function
    - Safe Refactoring: Know what depends on what before making changes
    - Debugging: Trace data flow across file boundaries
    - Code Review: Understand the full impact of changes
    - **Honest Uncertainty**: Know when deep dependencies may be unreliable

    Example:
        # Analyze 'process_order' function in 'services/order.py'
        result = get_cross_file_dependencies(
            target_file="services/order.py",
            target_symbol="process_order",
            max_depth=5,
            confidence_decay_factor=0.9
        )
        # Check for low-confidence symbols
        if result.low_confidence_count > 0:
            print(f"Warning: {result.low_confidence_warning}")

    Args:
        target_file: Path to file containing the target symbol (relative to project root)
        target_symbol: Name of the function or class to analyze
        project_root: Project root directory (default: server's project root)
        max_depth: Maximum depth of dependency resolution (default: 3)
        include_code: Include full source code in result (default: True)
        include_diagram: Include Mermaid diagram of imports (default: True)
        confidence_decay_factor: Decay factor per depth level (default: 0.9).
                                 Lower values = faster decay. Range: 0.0-1.0

    Returns:
        CrossFileDependenciesResult with extracted symbols, dependency graph, combined code,
        and confidence scores for each symbol
    """
    # [20251226_FEATURE] Tier-aware limits and capabilities
    tier = _get_current_tier()
    caps = get_tool_capabilities("get_cross_file_dependencies", tier) or {}
    limits = caps.get("limits", {}) or {}

    # Coerce numeric inputs in case MCP transport serialized them as strings
    max_depth = _coerce_int(max_depth) or 3
    confidence_decay_factor = _coerce_float(confidence_decay_factor) or 0.9
    max_files = _coerce_int(max_files) or None
    timeout_seconds = _coerce_float(timeout_seconds) or None

    max_depth_limit = limits.get("max_depth")
    effective_max_depth = max_depth
    if max_depth_limit is not None and (max_depth is None or _coerce_int(max_depth) > max_depth_limit):
        effective_max_depth = max_depth_limit

    max_files_limit = limits.get("max_files")
    if max_files is not None:
        max_files_limit = max_files

    result = await asyncio.to_thread(
        _get_cross_file_dependencies_sync,
        target_file,
        target_symbol,
        project_root,
        effective_max_depth,
        include_code,
        include_diagram,
        confidence_decay_factor,
        tier,
        caps,
        max_files_limit,
        timeout_seconds,
    )

    # [20260120_BUGFIX] Ensure raw envelope callers see an explicit success flag.
    if isinstance(result, ToolResponseEnvelope):
        data = result.data
        if isinstance(data, dict) and "success" not in data:
            data["success"] = result.error is None
            result.data = data
    elif isinstance(result, dict) and "success" not in result:
        result["success"] = True

    return result


get_cross_file_dependencies = mcp.tool()(
    envelop_tool_function(
        _get_cross_file_dependencies_tool,
        tool_id="get_cross_file_dependencies",
        tool_version=_pkg_version,
        tier_getter=_tier_getter,
    )
)


async def _cross_file_security_scan_tool(
    project_root: str | None = None,
    entry_points: list[str] | None = None,
    max_depth: int = 5,
    include_diagram: bool = True,
    timeout_seconds: float | None = 120.0,
    max_modules: int | None = 500,
    confidence_threshold: float = 0.7,
    ctx: Context | None = None,
) -> Any:
    """
    Perform cross-file security analysis tracking taint flow across module boundaries.

    [v1.5.1] Use this tool to detect vulnerabilities where tainted data crosses
    file boundaries before reaching a dangerous sink. This catches security
    issues that single-file analysis would miss.

    [20251215_FEATURE] v2.0.0 - Progress reporting for long-running operations.
    Reports progress during file discovery and taint analysis phases.

    [20251220_PERF] v3.0.4 - Added timeout and module limits to prevent hanging
    on large codebases with circular imports.

    Key capabilities:
    - Track taint flow through function calls across files
    - Detect vulnerabilities where source and sink are in different files
    - Identify all taint entry points (web inputs, file reads, etc.)
    - Map dangerous sinks (SQL execution, command execution, etc.)
    - Generate taint flow diagrams

    Detects cross-file patterns like:
    - User input in routes.py -> SQL execution in db.py (SQL Injection)
    - Request data in views.py -> os.system() in utils.py (Command Injection)
    - Form input in handlers.py -> open() in storage.py (Path Traversal)

    Why AI agents need this:
    - Defense in depth: Find vulnerabilities that span multiple files
    - Architecture review: Understand how untrusted data flows through the app
    - Code audit: Generate security reports for compliance
    - Risk assessment: Identify highest-risk code paths

    Args:
        project_root: Project root directory (default: server's project root)
        entry_points: Optional list of entry point functions to start from
                     (e.g., ["app.py:main", "routes.py:index"])
                     If None, analyzes all detected entry points
        max_depth: Maximum call depth to trace (default: 5)
        include_diagram: Include Mermaid diagram of taint flows (default: True)
        timeout_seconds: Maximum time in seconds for analysis (default: 120)
                        Set to None for no timeout (not recommended for large projects)
        max_modules: Maximum number of modules to analyze (default: 500)
                    Set to None for no limit (not recommended for large projects)

    Returns:
        CrossFileSecurityResult with vulnerabilities, taint flows, and risk assessment
    """
    # [20251215_FEATURE] v2.0.0 - Progress token support
    # [20251220_FEATURE] v3.0.5 - Enhanced progress messages
    if ctx:
        await ctx.report_progress(progress=0, total=100, message="Starting cross-file security scan...")

    tier = _get_current_tier()
    caps = get_tool_capabilities("cross_file_security_scan", tier)

    # Coerce numeric inputs in case MCP transport serialized them as strings
    max_depth = _coerce_int(max_depth) or 5
    timeout_seconds = _coerce_float(timeout_seconds) or 120.0
    max_modules = _coerce_int(max_modules) or 500
    confidence_threshold = _coerce_float(confidence_threshold) or 0.7

    result = await asyncio.to_thread(
        _cross_file_security_scan_sync,
        project_root,
        entry_points,
        max_depth,
        include_diagram,
        timeout_seconds,
        max_modules,
        tier,
        caps,
        confidence_threshold,
    )

    # Report completion with summary
    if ctx:
        vuln_count = result.vulnerability_count
        await ctx.report_progress(
            progress=100,
            total=100,
            message=f"Scan complete: {vuln_count} cross-file vulnerabilities found",
        )

    return result


cross_file_security_scan = mcp.tool()(
    envelop_tool_function(
        _cross_file_security_scan_tool,
        tool_id="cross_file_security_scan",
        tool_version=_pkg_version,
        tier_getter=_tier_getter,
    )
)


__all__ = [
    "get_call_graph",
    "get_graph_neighborhood",
    "get_project_map",
    "get_cross_file_dependencies",
    "cross_file_security_scan",
]
