"""Graph MCP tool registrations."""

from __future__ import annotations

import asyncio
from typing import Any

from code_scalpel.mcp.models.graph import GraphNeighborhoodResult
from code_scalpel.mcp.contract import ToolResponseEnvelope, envelop_tool_function
from code_scalpel.mcp.oracle_middleware import (
    with_oracle_resilience,
    PathStrategy,
    NodeIdFormatStrategy,
)

from mcp.server.fastmcp import Context

from code_scalpel.licensing.features import get_tool_capabilities, has_capability
from code_scalpel.mcp.helpers.graph_helpers import (
    _cross_file_security_scan_sync,
    _get_call_graph_sync,
    _get_cross_file_dependencies_sync,
    _get_graph_neighborhood_sync,
    _get_project_map_sync,
)
from code_scalpel.mcp.protocol import mcp
from code_scalpel import __version__ as _pkg_version
from code_scalpel.mcp.protocol import _get_current_tier as _tier_getter


def _get_current_tier() -> str:
    """Get current tier using JWT validation (late import to avoid circular dependency)."""
    from code_scalpel.mcp.server import _get_current_tier as get_tier

    return get_tier()


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
    """Build a call graph showing function relationships in the project.

    [20260308_DOCS] Current graph runtime has multiple parity levels. Python still
    receives the deepest call/node semantics today. JavaScript, TypeScript, and
    Java have dedicated runtime slices. C, C++, C#, Go, Kotlin, PHP, Ruby, Swift,
    and Rust currently expose local callable nodes and same-file call edges via
    the shared IR-backed fallback. Parity is not yet uniform across all supported
    languages.

    **Tier Behavior:**
    - Community: Max depth 10, max nodes 200, basic call graph only
    - Pro: All Community + path queries, focus mode, call context, confidence scoring
    - Enterprise: All Pro + hot path identification, dead code detection, custom graph analysis

    **Tier Capabilities:**
    - Community: Basic call graph (max_depth=10, max_nodes=200)
    - Pro: All Community + advanced features (max_depth=unlimited, max_nodes=unlimited)
    - Enterprise: All Pro + enterprise metrics (max_depth=unlimited, max_nodes=unlimited)

    **Args:**
        project_root (str, optional): Project root directory. Default: server's project root.
        entry_point (str, optional): Starting function name (e.g., "main" or "app.py:main"). If None, includes all functions.
        depth (int): Maximum depth to traverse from entry point. Default: 10.
        include_circular_import_check (bool): Check for circular imports. Default: True.
        paths_from (str, optional): Source function for path query (e.g., "routes.py:handle_request").
        paths_to (str, optional): Sink function for path query (e.g., "db.py:execute_query").
        focus_functions (list[str], optional): List of functions to focus the subgraph on.
        ctx (Context, optional): MCP context for progress reporting.

    **Returns:**
        ToolResponseEnvelope containing CallGraphResultModel with:
        - success (bool): True if graph built successfully
        - nodes (list[dict]): Function nodes with metadata
        - edges (list[dict]): Call relationships between functions
        - mermaid (str): Mermaid diagram representation
        - paths (list[list[str]], optional): Query paths from source to sink (Pro)
        - circular_imports (list[list[str]], optional): Detected circular dependencies
        - metadata (dict): Graph metadata
        - truncated (bool): Whether results were truncated
        - language_parity (dict[str, str]): Current parity level by language
        - parity_legend (dict[str, str]): Human-readable meaning for parity labels
        - runtime_scope_summary (str): Short summary of the current polyglot scope
        - tier_applied (str): Tier used
        - error (str): Error message if graph building failed
        - tier_applied (str): Tier used for analysis
        - duration_ms (int): Analysis duration in milliseconds
    """
    if ctx:
        await ctx.report_progress(0, 100, "Building call graph...")

    tier = _get_current_tier()
    caps = get_tool_capabilities("get_call_graph", tier) or {}
    limits = caps.get("limits", {}) or {}
    cap_set = set(caps.get("capabilities", []) or [])

    max_depth = limits.get("max_depth")
    max_nodes = limits.get("max_nodes")

    if max_depth is not None:
        max_depth = int(max_depth)
    if max_nodes is not None:
        max_nodes = int(max_nodes)

    actual_depth = depth
    if max_depth is not None and depth > max_depth:
        actual_depth = max_depth

    advanced_resolution = "advanced_call_graph" in cap_set
    include_enterprise_metrics = bool(
        {"hot_path_identification", "dead_code_detection", "custom_graph_analysis"}
        & cap_set
    )

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

    if ctx:
        node_count = len(result.nodes) if result.nodes else 0
        edge_count = len(result.edges) if result.edges else 0
        await ctx.report_progress(
            100,
            100,
            f"Call graph complete: {node_count} functions, {edge_count} calls",
        )

    return result


get_call_graph = mcp.tool(
    description="Generate a call graph with advanced Python support, dedicated JS/TS and Java runtime slices, and local-call parity for the broader polyglot IR-backed language set."
)(
    with_oracle_resilience(tool_id="get_call_graph", strategy=PathStrategy)(
        envelop_tool_function(
            _get_call_graph_tool,
            tool_id="get_call_graph",
            tool_version=_pkg_version,
            tier_getter=_tier_getter,
        )
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
    """Extract k-hop neighborhood subgraph around a center node.

    [20260306_DOCS] This tool remains Python-first overall, with an initial
    parity slice for local JavaScript/TypeScript function nodes and a narrow
    Java method-node slice. Supported canonical IDs include
    ``python::pkg.module::function::name``,
    ``typescript::src/api/client::function::fetchUsers``, and
    ``java::demo/App::method::App:main``.

    **Tier Behavior:**
    - Community: Max k=2, max nodes=100
    - Pro: All Community + extended neighborhood
    - Enterprise: All Pro + unlimited neighborhood

    **Tier Capabilities:**
    - Community: Limited neighborhood (max_k=2, max_nodes=100)
    - Pro: Unlimited neighborhood with advanced resolution features
    - Enterprise: Unlimited neighborhood with enterprise graph features

    **Args:**
        center_node_id (str): ID of the center node. Current runtime support is
            for local Python function nodes, local JavaScript/TypeScript
            function nodes, local JavaScript/TypeScript method nodes when
            advanced resolution is enabled, and local Java method nodes in the
            format language::module::type::name (for example,
            python::app.routes::function::handle_request,
            typescript::src/api/client::function::fetchUsers, or
            java::demo/App::method::App:main).
        k (int): Maximum hops from center. Default: 2.
        max_nodes (int): Maximum nodes to include. Default: 100.
        direction (str): "outgoing", "incoming", or "both". Default: "both".
        min_confidence (float): Minimum edge confidence to follow. Default: 0.0.
        project_root (str, optional): Project root directory. Default: server's project root.
        query (str, optional): Graph query language (Enterprise tier only).

    **Returns:**
        ToolResponseEnvelope containing GraphNeighborhoodResult with:
        - success (bool): True if extraction succeeded
        - center_node (dict): Center node details
        - nodes (list[dict]): Subgraph nodes
        - edges (list[dict]): Subgraph edges
        - mermaid (str): Mermaid diagram of neighborhood
        - truncated (bool): Whether results were truncated
        - tier_applied (str): Tier used
        - max_k_applied (int, optional): Max k-hop limit applied
        - max_nodes_applied (int, optional): Max nodes limit applied
        - advanced_resolution_enabled (bool): Whether advanced graph resolution was enabled
        - error (str): Error message if extraction failed
        - duration_ms (int): Analysis duration in milliseconds
    """
    # Pre-validation: Check node ID format early to fail fast
    import re

    # [20260104_BUGFIX] Ensure input types are strictly typed to prevent TypeErrors
    # from bubbling up through the contract wrapper as signature mismatches.
    if not isinstance(center_node_id, str):
        center_node_id = str(center_node_id)

    node_id_pattern = r"^(?P<language>[a-z]+)::(?P<module>[^:]+)::(?P<kind>function|class|method)::(?P<name>.+)$"
    match = re.match(node_id_pattern, center_node_id)
    if not match:
        # Raise ValidationError to trigger oracle suggestions
        from code_scalpel.mcp.validators.core import ValidationError

        raise ValidationError(
            f"Invalid node ID format: '{center_node_id}'. "
            "Expected format: language::module::type::name (e.g., python::app.routes::function::handle_request)"
        )

    language = match.group("language")
    kind = match.group("kind")

    if (
        (kind == "function" and language not in {"python", "javascript", "typescript"})
        or (kind == "method" and language not in {"javascript", "typescript", "java"})
        or kind == "class"
    ):
        from code_scalpel.mcp.validators.core import ValidationError

        raise ValidationError(
            "get_graph_neighborhood currently supports local Python function nodes plus local JavaScript/TypeScript function and method nodes and local Java method nodes only. "
            f"Received '{center_node_id}'. Use a canonical Python node ID such as "
            "python::app.routes::function::handle_request, a canonical JS/TS function node ID such as "
            "typescript::src/api/client::function::fetchUsers, or a JS/TS method node ID such as "
            "typescript::src/services/user_service::method::UserService:fetchUsers, or a Java method node ID such as "
            "java::demo/App::method::App:main."
        )

    # Pre-validation: Check parameter ranges
    try:
        k = int(k)
        max_nodes = int(max_nodes)
    except (ValueError, TypeError):
        raise ValueError(
            "Invalid parameters: 'k' and 'max_nodes' must be valid integers"
        )

    if k < 1:
        raise ValueError("Parameter 'k' must be >= 1")
    if max_nodes < 1:
        raise ValueError("Parameter 'max_nodes' must be >= 1")
    if direction not in ["outgoing", "incoming", "both"]:
        raise ValueError(
            f"Parameter 'direction' must be 'outgoing', 'incoming', or 'both', got '{direction}'"
        )

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


get_graph_neighborhood = mcp.tool(
    description="Extract a Python-first k-hop subgraph around a local Python function node, a local JS/TS function or method node, or a local Java method node from the project's call graph."
)(
    with_oracle_resilience(
        tool_id="get_graph_neighborhood", strategy=NodeIdFormatStrategy
    )(
        envelop_tool_function(
            _get_graph_neighborhood_tool,
            tool_id="get_graph_neighborhood",
            tool_version=_pkg_version,
            tier_getter=_tier_getter,
            legacy_result_type=GraphNeighborhoodResult,
        )
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
    """Generate a comprehensive map of the project structure.

    [20260308_DOCS] This surface remains Python-first overall, but now includes
    an initial local JS/TS slice plus a narrow Java slice for module discovery.
    Pro and Enterprise can also derive Java file relationships from explicit
    imports and static imports through the shared project-map relationship path.

    **Tier Behavior:**
    - Community: Up to 500 files, 100 modules, basic detail level
    - Pro: All Community + unlimited files, 1000 modules, detailed level
    - Enterprise: All Pro + unlimited files, 1000 modules, comprehensive detail level

    **Tier Capabilities:**
    - Community: Basic project map (max_files=500, max_modules=100)
    - Pro: Detailed project map (max_files=unlimited, max_modules=1000)
    - Enterprise: Comprehensive project map (max_files=unlimited, max_modules=1000)

    **Args:**
        project_root (str, optional): Project root directory. Default: server's project root.
        include_complexity (bool): Calculate cyclomatic complexity. Default: True.
        complexity_threshold (int): Threshold for flagging hotspots. Default: 10.
        include_circular_check (bool): Check for circular imports. Default: True.
        detect_service_boundaries (bool): Detect service boundaries. Default: False.
        min_isolation_score (float): Isolation score threshold for boundaries. Default: 0.6.
        ctx (Context, optional): MCP context for progress reporting.

    **Returns:**
        ToolResponseEnvelope containing ProjectMapResult with:
        - success (bool): True if mapping succeeded
        - total_files (int): Total files analyzed
        - total_lines (int): Total lines of code
        - modules (list[dict]): Module metadata
        - dependencies (list[dict]): Inter-module dependencies
        - complexity_hotspots (list[dict]): High complexity locations
        - circular_dependencies (list[list[str]], optional): Detected circular dependencies
        - mermaid (str): Mermaid diagram of structure
        - suggested_services (list[dict], optional): Service boundary suggestions (Enterprise)
        - tier_applied (str): Tier used
        - error (str): Error message if mapping failed
        - tier_applied (str): Tier used for analysis
        - duration_ms (int): Analysis duration in milliseconds
    """
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


get_project_map = mcp.tool(
    description="Produce a high-level project structure map with package hierarchy and complexity hotspots."
)(
    with_oracle_resilience(tool_id="get_project_map", strategy=PathStrategy)(
        envelop_tool_function(
            _get_project_map_tool,
            tool_id="get_project_map",
            tool_version=_pkg_version,
            tier_getter=_tier_getter,
        )
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
    """Analyze and extract cross-file dependencies for a symbol.

    [20260308_DOCS] This dependency workflow remains Python-first overall.
    It now includes an initial JavaScript/TypeScript slice plus a narrow Java
    method slice using the shared graph runtime. Java Community support is
    local-method only; Pro and Enterprise reuse the existing cross-file Java
    call-graph resolution.

    **Tier Behavior:**
    - Community: Limited depth analysis (max_depth=3, max_files=200)
    - Pro: Unlimited depth and files with richer dependency extras
    - Enterprise: Unlimited depth and files with governance analysis

    **Tier Capabilities:**
    - Community: Limited depth analysis (max_depth=3, max_files=200)
    - Pro: Unlimited depth analysis (max_depth=unlimited, max_files=unlimited)
    - Enterprise: Unlimited depth and files

    **Args:**
        target_file (str): Path to file containing the target symbol (relative to project root).
        target_symbol (str): Name of the function or class to analyze.
            Java graph-backed slices accept bare method names or Class.method / Class:method.
        project_root (str, optional): Project root directory. Default: server's project root.
        max_depth (int): Maximum depth of dependency resolution. Default: 3.
        include_code (bool): Include full source code in result. Default: True.
        include_diagram (bool): Include Mermaid diagram of imports. Default: True.
        confidence_decay_factor (float): Decay factor per depth level. Default: 0.9. Range: 0.0-1.0.
        max_files (int, optional): Maximum files to include (subject to tier limit).
        timeout_seconds (float, optional): Timeout in seconds.

    **Returns:**
        ToolResponseEnvelope containing CrossFileDependenciesResult with:
        - success (bool): True if analysis succeeded
        - target_symbol (str): The analyzed symbol
        - extracted_symbols (list[dict]): Extracted dependencies
        - dependency_graph (dict): Dependency relationships
        - combined_code (str): Combined code from all dependencies
        - confidence_scores (dict): Confidence per symbol (Pro+)
        - mermaid (str): Mermaid diagram of dependencies
        - truncated (bool): Whether results were truncated
        - tier_applied (str): Tier used
        - max_depth_applied (int, optional): Max depth limit applied
        - max_files_applied (int, optional): Max files limit applied
        - error (str): Error message if analysis failed
        - duration_ms (int): Analysis duration in milliseconds
    """
    tier = _get_current_tier()
    caps = get_tool_capabilities("get_cross_file_dependencies", tier) or {}
    limits = caps.get("limits", {}) or {}

    max_depth_limit = limits.get("max_depth")
    effective_max_depth = max_depth
    if max_depth_limit is not None and max_depth > max_depth_limit:
        effective_max_depth = int(max_depth_limit)

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

    if isinstance(result, ToolResponseEnvelope):
        data = result.data
        if isinstance(data, dict) and "success" not in data:
            data["success"] = result.error is None
            result.data = data
    elif isinstance(result, dict) and "success" not in result:
        result["success"] = True

    return result


get_cross_file_dependencies = mcp.tool(
    description="Trace Python-first cross-file dependency chains for a symbol, including an initial local JS/TS graph-backed parity slice."
)(
    with_oracle_resilience(
        tool_id="get_cross_file_dependencies", strategy=PathStrategy
    )(
        envelop_tool_function(
            _get_cross_file_dependencies_tool,
            tool_id="get_cross_file_dependencies",
            tool_version=_pkg_version,
            tier_getter=_tier_getter,
        )
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
    """Perform cross-file security analysis tracking taint flow across module boundaries.

    Use this tool to detect vulnerabilities where tainted data crosses file boundaries
    before reaching a dangerous sink. This catches security issues that single-file
    analysis would miss.

    **Tier Behavior:**
    - Community: Basic cross-file scan with single-module taint tracking (max 50 modules, depth 5)
    - Pro: All Community + advanced taint tracking with framework-aware analysis (unlimited modules and depth)
    - Enterprise: All Pro + project-wide scan with custom rules and global flows (unlimited modules/depth)

    **Tier Capabilities:**
    - Community: basic_cross_file_scan, single_module_taint_tracking, source_to_sink_tracing (max_modules=50, max_depth=5)
    - Pro: All Community + advanced_taint_tracking, framework_aware_taint, dependency_injection_resolution (max_modules=unlimited, max_depth=unlimited)
    - Enterprise: All Pro + project_wide_scan, custom_taint_rules, global_taint_flow, microservice_boundary_crossing (max_modules=unlimited, max_depth=unlimited)

    **Args:**
        project_root (str, optional): Project root directory. Default: server's project root.
        entry_points (list[str], optional): Entry point functions (e.g., ["app.py:main", "routes.py:index"]). If None, analyzes all.
        max_depth (int): Maximum call depth to trace. Default: 5.
        include_diagram (bool): Include Mermaid diagram of taint flows. Default: True.
        timeout_seconds (float, optional): Maximum time in seconds. Default: 120. None for no timeout.
        max_modules (int, optional): Maximum modules to analyze. Default: 500. None for no limit.
        confidence_threshold (float): Minimum confidence for reporting. Default: 0.7.
        ctx (Context, optional): MCP context for progress reporting.

    **Returns:**
        ToolResponseEnvelope containing CrossFileSecurityResult with:
        - success (bool): True if analysis completed successfully
        - server_version (str): Code Scalpel version
        - tier_applied (str): Tier used ("community"/"pro"/"enterprise")
        - max_depth_applied (int, optional): Max depth limit applied
        - max_modules_applied (int, optional): Max modules limit applied
        - framework_aware_enabled (bool): Whether framework-aware tracking enabled (Pro+)
        - enterprise_features_enabled (bool): Whether enterprise features enabled
        - files_analyzed (int): Number of files analyzed
        - has_vulnerabilities (bool): Whether vulnerabilities were found
        - vulnerability_count (int): Total vulnerabilities found
        - risk_level (str): Overall risk ("low"/"medium"/"high"/"critical")
        - vulnerabilities (list[CrossFileVulnerabilityModel]): Detailed vulnerabilities
        - taint_flows (list[TaintFlowModel]): Data flow paths
        - taint_sources (list[str]): Functions with taint sources
        - dangerous_sinks (list[str]): Functions with dangerous sinks
        - framework_contexts (dict): Framework detection (Pro+)
        - dependency_chains (list[dict]): Inter-file chains (Pro+)
        - confidence_scores (dict): Confidence per flow (Pro+)
        - global_flows (list[dict]): Global flows (Enterprise)
        - microservice_boundaries (list[dict]): Service boundaries (Enterprise)
        - distributed_trace (dict): Distributed trace (Enterprise)
        - mermaid (str): Mermaid diagram of taint flows
        - error (str, optional): Error message if analysis failed
        - error (str): Error message if tool execution failed
        - tier_applied (str): Tier used for analysis
        - duration_ms (int): Analysis duration in milliseconds
    """
    if ctx:
        await ctx.report_progress(
            progress=0, total=100, message="Starting cross-file security scan..."
        )

    tier = _get_current_tier()
    caps = get_tool_capabilities("cross_file_security_scan", tier)

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

    if ctx:
        vuln_count = result.vulnerability_count
        await ctx.report_progress(
            progress=100,
            total=100,
            message=f"Scan complete: {vuln_count} cross-file vulnerabilities found",
        )

    return result


cross_file_security_scan = mcp.tool(
    description="Detect security vulnerabilities spanning module boundaries via cross-file taint tracking."
)(
    with_oracle_resilience(tool_id="cross_file_security_scan", strategy=PathStrategy)(
        envelop_tool_function(
            _cross_file_security_scan_tool,
            tool_id="cross_file_security_scan",
            tool_version=_pkg_version,
            tier_getter=_tier_getter,
        )
    )
)


__all__ = [
    "get_call_graph",
    "get_graph_neighborhood",
    "get_project_map",
    "get_cross_file_dependencies",
    "cross_file_security_scan",
]
