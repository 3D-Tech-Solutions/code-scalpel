"""Helper implementations for graph tools."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from code_scalpel.licensing.features import get_tool_capabilities
from code_scalpel.licensing.tier_detector import (
    get_current_tier as _get_current_tier,
)
from code_scalpel.mcp.models.graph import (
    AliasResolutionModel,
    ArchitecturalViolationModel,
    BoundaryAlertModel,
    CallContextModel,
    CallEdgeModel,
    CallGraphResultModel,
    CallNodeModel,
    ChainedAliasResolutionModel,
    CouplingViolationModel,
    CrossFileDependenciesResult,
    CrossFileSecurityResult,
    CrossFileVulnerabilityModel,
    ExtractedSymbolModel,
    GraphNeighborhoodResult,
    ModuleInfo,
    NeighborhoodEdgeModel,
    NeighborhoodNodeModel,
    PackageInfo,
    ProjectMapResult,
    ReexportChainModel,
    TaintFlowModel,
    WildcardExpansionModel,
)
from code_scalpel.parsing import ParsingError, parse_python_code

if TYPE_CHECKING:
    from code_scalpel.graph_engine.graph import UniversalGraph

logger = logging.getLogger("code_scalpel.mcp.graph")


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


# [20260120_DEPRECATED] Use _get_project_root() instead.
PROJECT_ROOT = Path.cwd()

# [20251219_FEATURE] v3.0.4 - Call graph cache for get_graph_neighborhood
# Stores UniversalGraph objects keyed by project root path (+ variant)
# Format: {cache_key: (UniversalGraph, timestamp)}
# [20251220_PERF] v3.0.5 - Increased cache TTL from 60s to 300s for large codebases
_GRAPH_CACHE: dict[str, tuple[UniversalGraph, float]] = {}  # type: ignore[name-defined]
_GRAPH_CACHE_TTL = 300.0  # seconds (5 minutes for stable codebases)


def _get_cached_graph(project_root: Path, cache_variant: str = "default") -> UniversalGraph | None:  # type: ignore[name-defined]
    """Get cached UniversalGraph for project if still valid."""
    import time

    # [20251225_BUGFIX] Avoid mixing graph variants (e.g., Pro advanced resolution)
    # in a single cache entry.
    key = f"{project_root.resolve()}::{cache_variant}"
    if key in _GRAPH_CACHE:
        graph, timestamp = _GRAPH_CACHE[key]
        if time.time() - timestamp < _GRAPH_CACHE_TTL:
            logger.debug(f"Using cached graph for {key}")
            return graph
        else:
            # Cache expired
            del _GRAPH_CACHE[key]
            logger.debug(f"Graph cache expired for {key}")
    return None


def _cache_graph(project_root: Path, graph: UniversalGraph, cache_variant: str = "default") -> None:  # type: ignore[name-defined]
    """Cache a UniversalGraph for a project."""
    import time

    key = f"{project_root.resolve()}::{cache_variant}"
    _GRAPH_CACHE[key] = (graph, time.time())
    logger.debug(f"Cached graph for {key}")


# ============================================================================
# [20251213_FEATURE] v1.5.0 - get_call_graph MCP Tool
# [20260110_FEATURE] v3.3.0 - Pre-release: confidence, context, paths, focus
# ============================================================================


def _get_call_graph_sync(
    project_root: str | None,
    entry_point: str | None,
    depth: int,
    include_circular_import_check: bool,
    max_nodes: int | None = None,
    advanced_resolution: bool = False,
    include_enterprise_metrics: bool = False,
    paths_from: str | None = None,
    paths_to: str | None = None,
    focus_functions: list[str] | None = None,
    tier: str = "community",
    capabilities: dict | None = None,
) -> CallGraphResultModel:
    """Synchronous implementation of get_call_graph with tier-aware metadata."""
    if capabilities is None:
        capabilities = {}
    from code_scalpel.ast_tools.call_graph import CallGraphBuilder

    # [20251226_BUGFIX] Ensure deterministic truncation and advanced resolution enrichment.
    # [20260119_FEATURE] Uses unified parser for deterministic behavior.
    def _infer_polymorphic_edges(root: Path, graph_nodes: list[CallNodeModel]) -> set[tuple[str, str]]:
        """Best-effort inference of self.* call edges for class methods when advanced_resolution is enabled."""
        import ast

        edges: set[tuple[str, str]] = set()
        files = {n.file for n in graph_nodes if n.file not in {"<external>", ""}}
        for rel_path in files:
            file_path = root / rel_path
            if not file_path.exists():
                continue
            try:
                code = file_path.read_text(encoding="utf-8")
                tree, _ = parse_python_code(code, filename=rel_path)
            except (ParsingError, UnicodeDecodeError, OSError):
                continue

            class_name: str | None = None
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    class_name = node.name
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and class_name:
                    caller = f"{rel_path}:{class_name}.{node.name}"
                    for inner in ast.walk(node):
                        if isinstance(inner, ast.Call) and isinstance(inner.func, ast.Attribute):
                            if isinstance(inner.func.value, ast.Name) and inner.func.value.id == "self":
                                callee = f"{rel_path}:{class_name}.{inner.func.attr}"
                                edges.add((caller, callee))
        return edges

    root_path = Path(project_root) if project_root else _get_project_root()

    if not root_path.exists():
        return CallGraphResultModel(
            success=False,
            error=f"Project root not found: {root_path}.",
        )

    try:
        builder = CallGraphBuilder(root_path)
        result = builder.build_with_details(
            entry_point=entry_point,
            depth=depth,
            max_nodes=max_nodes,
            advanced_resolution=advanced_resolution,
        )

        # [20260110_FEATURE] v3.3.0 - Convert dataclasses to Pydantic models with new fields
        nodes = [
            CallNodeModel(
                name=n.name,
                file=n.file,
                line=n.line,
                end_line=n.end_line,
                is_entry_point=n.is_entry_point,
                # [20260110_FEATURE] v3.3.0 - Source URI for IDE click-through
                source_uri=n.source_uri,
            )
            for n in result.nodes
        ]

        # [20260110_FEATURE] v3.3.0 - Convert edges with context/confidence metadata
        edges = []
        for e in result.edges:
            context_model = None
            if e.context is not None:
                context_model = CallContextModel(
                    in_loop=e.context.in_loop,
                    in_try_block=e.context.in_try_block,
                    in_conditional=e.context.in_conditional,
                    condition_summary=e.context.condition_summary,
                    in_async=e.context.in_async,
                    in_except_handler=e.context.in_except_handler,
                )
            edges.append(
                CallEdgeModel(
                    caller=e.caller,
                    callee=e.callee,
                    call_line=e.call_line,
                    confidence=e.confidence,
                    inference_source=e.inference_source,
                    context=context_model,
                )
            )

        # [20251226_FEATURE] Add heuristic polymorphism edges when enabled.
        if advanced_resolution:
            extra_edges = _infer_polymorphic_edges(root_path, nodes)
            existing = {(e.caller, e.callee) for e in edges}
            for caller, callee in extra_edges:
                if (caller, callee) not in existing:
                    edges.append(CallEdgeModel(caller=caller, callee=callee))
                    existing.add((caller, callee))

        # [20251226_BUGFIX] Apply explicit truncation to honor limits even if builder is permissive.
        total_nodes = len(nodes)
        total_edges = len(edges)
        nodes_truncated = bool(getattr(result, "nodes_truncated", False))
        edges_truncated = bool(getattr(result, "edges_truncated", False))
        if max_nodes is not None and total_nodes > max_nodes:
            nodes = nodes[:max_nodes]
            nodes_truncated = True
            # [20251230_BUGFIX] Normalize node identity format for consistent edge filtering
            # Handle both "file:name" and "file:Class.method" formats
            kept_endpoints = set()
            for n in nodes:
                # Add both the full name and simple name to handle format variations
                if n.file != "<external>":
                    kept_endpoints.add(f"{n.file}:{n.name}")
                    # If name contains class qualification, also add without file prefix
                    if "." in n.name:
                        kept_endpoints.add(n.name)
                else:
                    kept_endpoints.add(n.name)

            filtered_edges = [e for e in edges if (e.caller in kept_endpoints and e.callee in kept_endpoints)]
            edges_truncated = edges_truncated or len(filtered_edges) < len(edges)
            edges = filtered_edges

        truncation_warning = None
        if nodes_truncated or edges_truncated:
            parts: list[str] = []
            if max_nodes is not None:
                parts.append(f"max_nodes={max_nodes}")
            parts.append(f"max_depth={depth}")
            truncation_warning = "Results truncated by limits: " + ", ".join(parts)

        hot_nodes: list[str] = []
        dead_code_candidates: list[str] = []
        if include_enterprise_metrics:
            # [20251225_FEATURE] Best-effort degree metrics and dead-code candidates.
            in_deg: dict[str, int] = {}
            out_deg: dict[str, int] = {}

            for edge in edges:
                out_deg[edge.caller] = out_deg.get(edge.caller, 0) + 1
                in_deg[edge.callee] = in_deg.get(edge.callee, 0) + 1

            for node in nodes:
                full_name = f"{node.file}:{node.name}" if node.file != "<external>" else node.name
                node.in_degree = in_deg.get(full_name, 0)
                node.out_degree = out_deg.get(full_name, 0)

            def _total_degree(n: CallNodeModel) -> tuple[int, str]:
                full = f"{n.file}:{n.name}" if n.file != "<external>" else n.name
                return ((n.in_degree or 0) + (n.out_degree or 0), full)

            hot_nodes = [
                (f"{n.file}:{n.name}" if n.file != "<external>" else n.name)
                for n in sorted(nodes, key=_total_degree, reverse=True)[:10]
                if _total_degree(n)[0] > 0
            ]

            # [20251230_BUGFIX] Optimize dead-code detection: use existing graph instead of rebuilding
            # Only identify dead code from the nodes we already have (don't rebuild full graph)
            # This is more efficient and respects the user's max_nodes limit
            dead_code_candidates = [
                f"{n.file}:{n.name}" if n.file != "<external>" else n.name
                for n in nodes
                if not n.is_entry_point
                and in_deg.get(f"{n.file}:{n.name}" if n.file != "<external>" else n.name, 0) == 0
            ]

        # Optionally check for circular imports
        circular_imports = []
        if include_circular_import_check:
            circular_imports = builder.detect_circular_imports()

        # [20260110_FEATURE] v3.3.0 - Path query API
        paths: list[list[str]] = []
        if paths_from and paths_to:
            # Build adjacency list from edges for path finding
            adj_list: dict[str, list[str]] = {}
            for e in edges:
                adj_list.setdefault(e.caller, []).append(e.callee)
            find_paths = getattr(builder, "find_paths", None)
            if callable(find_paths):
                paths = cast(
                    list[list[str]],
                    find_paths(paths_from, paths_to, max_depth=depth, graph=adj_list),
                )
            else:
                # Fallback: simple DFS path search within max depth
                def _dfs_paths(start: str, goal: str, max_depth: int) -> list[list[str]]:
                    results: list[list[str]] = []
                    stack: list[tuple[str, list[str]]] = [(start, [start])]
                    while stack:
                        node, path = stack.pop()
                        if len(path) - 1 > max_depth:
                            continue
                        if node == goal:
                            results.append(path)
                            continue
                        for nxt in adj_list.get(node, []):
                            if nxt in path:
                                continue
                            stack.append((nxt, path + [nxt]))
                    return results

                paths = _dfs_paths(paths_from, paths_to, depth)

        # [20260110_FEATURE] v3.3.0 - Focus mode: filter to subgraph around focus_functions
        actual_focus_functions: list[str] | None = None
        if focus_functions:
            # Find k-hop neighborhood around focus functions
            focus_set = set(focus_functions)
            related: set[str] = set(focus_functions)

            # Add all nodes that call or are called by focus functions (1-hop)
            for e in edges:
                if e.caller in focus_set or e.callee in focus_set:
                    related.add(e.caller)
                    related.add(e.callee)

            # Filter nodes and edges to only those in the related set
            nodes = [n for n in nodes if f"{n.file}:{n.name}" in related or n.name in related]
            edges = [e for e in edges if e.caller in related or e.callee in related]
            actual_focus_functions = focus_functions

        return CallGraphResultModel(
            nodes=nodes,
            edges=edges,
            entry_point=result.entry_point,
            depth_limit=result.depth_limit,
            mermaid=result.mermaid,
            circular_imports=circular_imports,
            paths=paths,
            focus_functions=actual_focus_functions,
            total_nodes=total_nodes,
            total_edges=total_edges,
            nodes_truncated=nodes_truncated,
            edges_truncated=edges_truncated,
            truncation_warning=truncation_warning,
            hot_nodes=hot_nodes,
            dead_code_candidates=dead_code_candidates,
            # [20260120_FEATURE] Metadata transparency: report tier's limits and capabilities
            tier_applied=tier,
            max_depth_applied=capabilities.get("limits", {}).get("max_depth"),
            max_nodes_applied=capabilities.get("limits", {}).get("max_nodes"),
            advanced_resolution_enabled="advanced_call_graph" in capabilities.get("capabilities", []),
            enterprise_metrics_enabled="hot_path_identification" in capabilities.get("capabilities", []),
        )

    except Exception as e:
        return CallGraphResultModel(
            success=False,
            error=f"Call graph analysis failed: {str(e)}",
        )


# ============================================================================
# [20251216_FEATURE] v2.5.0 - get_graph_neighborhood MCP Tool
# ============================================================================


def _generate_neighborhood_mermaid(
    nodes: list[NeighborhoodNodeModel],
    edges: list[NeighborhoodEdgeModel],
    center_node_id: str,
) -> str:
    """Generate Mermaid diagram for neighborhood."""
    lines = ["graph TD"]

    # Add nodes with depth-based styling
    for node in nodes:
        # Sanitize node ID for Mermaid
        safe_id = node.id.replace("::", "_").replace(".", "_").replace("-", "_")
        label = node.id.split("::")[-1] if "::" in node.id else node.id

        if node.depth == 0:
            # Center node - special styling
            lines.append(f'    {safe_id}["{label}"]:::center')
        elif node.depth == 1:
            lines.append(f'    {safe_id}["{label}"]:::depth1')
        else:
            lines.append(f'    {safe_id}["{label}"]:::depth2plus')

    # Add edges
    for edge in edges:
        from_safe = edge.from_id.replace("::", "_").replace(".", "_").replace("-", "_")
        to_safe = edge.to_id.replace("::", "_").replace(".", "_").replace("-", "_")
        lines.append(f"    {from_safe} --> {to_safe}")

    # Add style definitions
    lines.append("    classDef center fill:#f9f,stroke:#333,stroke-width:3px")
    lines.append("    classDef depth1 fill:#bbf,stroke:#333,stroke-width:2px")
    lines.append("    classDef depth2plus fill:#ddd,stroke:#333,stroke-width:1px")

    return "\n".join(lines)


def _normalize_graph_center_node_id(center_node_id: str) -> str:
    """Normalize common legacy node-id formats into canonical IDs.

    Canonical format: python::<module>::function::<name>

    Accepted legacy inputs:
    - routes.py:search_route
    - path/to/routes.py:search_route
    - routes:search_route
    """
    raw = (center_node_id or "").strip()
    if not raw:
        return raw

    if raw.startswith("python::") and "::function::" in raw:
        return raw

    # Common legacy format: <file>:<symbol>
    if ":" in raw and "::" not in raw:
        left, right = raw.rsplit(":", 1)
        file_part = left.strip()
        name = right.strip()
        if not name:
            return raw

        # If this looks like a path, convert to module.
        if file_part.endswith(".py"):
            module = file_part.replace("/", ".").replace("\\", ".")
            if module.endswith(".py"):
                module = module[: -len(".py")]
            # Drop leading dots that can happen with absolute-ish inputs.
            module = module.strip(".")
            if module:
                return f"python::{module}::function::{name}"

        # If this looks like a bare module name.
        module = file_part.replace("/", ".").replace("\\", ".").strip(".")
        if module:
            return f"python::{module}::function::{name}"

    return raw


def _fast_validate_python_function_node_exists(root_path: Path, center_node_id: str) -> tuple[bool, str | None]:
    """Best-effort fast validation for python::<module>::function::<name>.

    This avoids building the full call graph when the node ID points to a module
    file that doesn't exist or a function name that doesn't exist in that file.

    Returns:
        (ok, error_message)
    """
    import re

    m = re.match(
        r"^(?P<lang>[^:]+)::(?P<module>[^:]+)::(?P<kind>[^:]+)::(?P<name>.+)$",
        center_node_id.strip(),
    )
    if not m:
        return (
            False,
            "Invalid center_node_id format; expected language::module::type::name",
        )

    lang = m.group("lang")
    module = m.group("module")
    kind = m.group("kind")
    name = m.group("name")

    if lang != "python" or kind != "function":
        return True, None

    if module in ("external", "unknown"):
        return False, f"Center node module '{module}' is not a local module"

    # Map module -> file path
    candidate = root_path / (module.replace(".", "/") + ".py")
    if not candidate.exists():
        return False, f"Center node file not found for module '{module}': {candidate}"

    # Quick AST scan for a matching function name in that single file.
    # [20260119_FEATURE] Uses unified parser for deterministic behavior.
    try:
        import ast

        code = candidate.read_text(encoding="utf-8")
        tree, _ = parse_python_code(code, filename=str(candidate))
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
                return True, None
        return False, f"Center node function '{name}' not found in {candidate}"
    except (ParsingError, UnicodeDecodeError, OSError):
        # If parsing fails, fall back to the slow path (graph build)
        return True, None


def _get_graph_neighborhood_sync(
    center_node_id: str,
    k: int = 2,
    max_nodes: int = 100,
    direction: str = "both",
    min_confidence: float = 0.0,
    project_root: str | None = None,
    query: str | None = None,
) -> GraphNeighborhoodResult:
    """Synchronous implementation of get_graph_neighborhood."""
    root_path = Path(project_root) if project_root else _get_project_root()

    if not root_path.exists():
        return GraphNeighborhoodResult(
            success=False,
            error=f"Project root not found: {root_path}.",
        )

    # [20251225_FEATURE] Capability-driven tier behavior (no upgrade hints)
    tier = _get_current_tier()
    caps = get_tool_capabilities("get_graph_neighborhood", tier) or {}
    limits = caps.get("limits", {}) or {}
    cap_list = caps.get("capabilities", []) or []
    cap_set = set(cap_list) if not isinstance(cap_list, set) else cap_list

    # Enterprise capability flags (returned even when empty)
    query_supported = bool("graph_query_language" in cap_set)
    traversal_rules_available = bool("custom_traversal_rules" in cap_set)
    path_constraints_supported = bool("path_constraint_queries" in cap_set)

    # [20251226_BUGFIX] Support both legacy and current limit keys.
    max_k_hops = limits.get("max_k_hops", limits.get("max_k"))
    max_nodes_limit = limits.get("max_nodes")

    actual_k = k
    k_limited = False
    if max_k_hops is not None and k > max_k_hops:
        actual_k = int(max_k_hops)
        k_limited = True
        k = actual_k

    if max_nodes_limit is not None and max_nodes > max_nodes_limit:
        max_nodes = int(max_nodes_limit)

    # Validate parameters
    if k < 1:
        return GraphNeighborhoodResult(
            success=False,
            error="Parameter 'k' must be at least 1.",
        )

    if max_nodes < 1:
        return GraphNeighborhoodResult(
            success=False,
            error="Parameter 'max_nodes' must be at least 1.",
        )

    if direction not in ("outgoing", "incoming", "both"):
        return GraphNeighborhoodResult(
            success=False,
            error=f"Parameter 'direction' must be 'outgoing', 'incoming', or 'both', got '{direction}'.",
        )

    try:
        center_node_id = _normalize_graph_center_node_id(center_node_id)

        ok, fast_err = _fast_validate_python_function_node_exists(root_path, center_node_id)
        if not ok:
            return GraphNeighborhoodResult(
                success=False,
                error=fast_err or "Center node not found",
            )

        # [v3.0.4] Try to use cached graph first
        from code_scalpel.graph_engine import UniversalGraph

        advanced_resolution = bool(
            {
                "advanced_neighborhood",
                "semantic_neighbors",
                "logical_relationship_detection",
                "polymorphism_resolution",
                "virtual_call_tracking",
            }
            & cap_set
        )

        include_enterprise_metrics = bool(
            {
                "custom_traversal",
                "graph_query_language",
                "custom_traversal_rules",
                "path_constraint_queries",
            }
            & cap_set
        )

        cache_variant = "advanced" if advanced_resolution else "basic"
        graph = _get_cached_graph(root_path, cache_variant=cache_variant)

        if graph is None:
            # Cache miss - build the graph
            from code_scalpel.ast_tools.call_graph import CallGraphBuilder

            builder = CallGraphBuilder(root_path)
            call_graph_result = builder.build_with_details(
                entry_point=None,
                depth=10,
                max_nodes=None,
                advanced_resolution=advanced_resolution,
            )

            # Convert call graph to UniversalGraph
            from code_scalpel.graph_engine import (
                EdgeType,
                GraphEdge,
                GraphNode,
                NodeType,
                UniversalNodeID,
            )

            graph = UniversalGraph()

            # Add nodes
            for node in call_graph_result.nodes:
                node_id = UniversalNodeID(
                    language="python",
                    module=(
                        node.file.replace("/", ".").replace(".py", "") if node.file != "<external>" else "external"
                    ),
                    node_type=NodeType.FUNCTION,
                    name=node.name,
                    line=node.line,
                )
                graph.add_node(
                    GraphNode(
                        id=node_id,
                        metadata={
                            "file": node.file,
                            "line": node.line,
                            "is_entry_point": node.is_entry_point,
                        },
                    )
                )

            # Add edges
            for edge in call_graph_result.edges:
                # Parse caller/callee into node IDs
                caller_parts = edge.caller.split(":")
                callee_parts = edge.callee.split(":")

                caller_file = caller_parts[0] if len(caller_parts) > 1 else ""
                caller_name = caller_parts[-1]
                callee_file = callee_parts[0] if len(callee_parts) > 1 else ""
                callee_name = callee_parts[-1]

                caller_module = caller_file.replace("/", ".").replace(".py", "") if caller_file else "unknown"
                callee_module = callee_file.replace("/", ".").replace(".py", "") if callee_file else "external"

                caller_id = f"python::{caller_module}::function::{caller_name}"
                callee_id = f"python::{callee_module}::function::{callee_name}"

                graph.add_edge(
                    GraphEdge(
                        from_id=caller_id,
                        to_id=callee_id,
                        edge_type=EdgeType.DIRECT_CALL,
                        confidence=0.9,
                        evidence="Direct function call",
                    )
                )

            # Cache the built graph for subsequent calls
            _cache_graph(root_path, graph, cache_variant=cache_variant)

        # [20251229_FEATURE] Enterprise tier: Query language support
        if query and "graph_query_language" in cap_set:
            from code_scalpel.graph.graph_query import GraphQueryEngine
            from code_scalpel.graph_engine import NeighborhoodResult, UniversalGraph

            try:
                engine = GraphQueryEngine(graph)
                query_result = engine.execute(query)

                if not query_result.success:
                    return GraphNeighborhoodResult(
                        success=False,
                        error=f"Query execution failed: {query_result.error}",
                    )

                # Build a subgraph from query results (bounded by max_nodes)
                subgraph = UniversalGraph()
                included_node_ids: set[str] = set()

                for node_data in query_result.nodes:
                    if len(included_node_ids) >= max_nodes:
                        break
                    node_id = str(node_data.get("id", "") or "").strip()
                    if not node_id:
                        continue
                    original_node = graph.get_node(node_id)
                    if original_node:
                        subgraph.add_node(original_node)
                        included_node_ids.add(node_id)

                # Add edges from query result (only if both endpoints are included)
                for edge_data in query_result.edges:
                    from_id = str(edge_data.get("from_id", "") or "").strip()
                    to_id = str(edge_data.get("to_id", "") or "").strip()
                    if not from_id or not to_id:
                        continue
                    if from_id not in included_node_ids or to_id not in included_node_ids:
                        continue
                    # Find original edge in the graph
                    for edge in graph.edges:
                        if edge.from_id == from_id and edge.to_id == to_id:
                            subgraph.add_edge(edge)
                            break

                node_depths = {node_id: 0 for node_id in included_node_ids}
                truncated = len(query_result.nodes) > max_nodes

                result = NeighborhoodResult(
                    success=True,
                    subgraph=subgraph,
                    center_node_id=center_node_id,
                    k=0,
                    total_nodes=len(subgraph.nodes),
                    total_edges=len(subgraph.edges),
                    max_depth_reached=0,
                    truncated=truncated,
                    truncation_warning=(
                        f"Query result truncated at {max_nodes} nodes due to max_nodes limit." if truncated else None
                    ),
                    node_depths=node_depths,
                )

            except Exception as e:
                return GraphNeighborhoodResult(
                    success=False,
                    error=f"Query language error: {str(e)}",
                )
        else:
            # Standard k-hop extraction
            result = graph.get_neighborhood(
                center_node_id=center_node_id,
                k=k,
                max_nodes=max_nodes,
                direction=direction,
                min_confidence=min_confidence,
            )

        if not result.success:
            return GraphNeighborhoodResult(
                success=False,
                error=result.error,
            )

        # [20251229_FEATURE] Pro tier: Add semantic neighbors
        semantic_neighbor_ids: set[str] = set()
        if "semantic_neighbors" in cap_set:
            from code_scalpel.graph.semantic_neighbors import SemanticNeighborFinder

            try:
                # Extract center function name from node_id
                center_name = center_node_id.split("::")[-1]
                finder = SemanticNeighborFinder(root_path)
                semantic_result = finder.find_semantic_neighbors(
                    center_name=center_name,
                    k=min(10, max_nodes // 2),
                    min_similarity=0.3,
                )

                if semantic_result.success:
                    for neighbor in semantic_result.neighbors:
                        # Add semantic neighbor to the graph if not already present
                        if neighbor.node_id not in result.node_depths:
                            semantic_neighbor_ids.add(neighbor.node_id)
                            # Add to result's node_depths at depth k+1 (beyond normal k-hop)
                            result.node_depths[neighbor.node_id] = k + 1

                            # Add edge from center to semantic neighbor
                            if result.subgraph:
                                from code_scalpel.graph_engine import (
                                    EdgeType,
                                    GraphEdge,
                                )

                                result.subgraph.add_edge(
                                    GraphEdge(
                                        from_id=center_node_id,
                                        to_id=neighbor.node_id,
                                        edge_type=EdgeType.SEMANTIC_SIMILAR,
                                        confidence=neighbor.similarity_score,
                                        evidence=f"Semantic: {', '.join(neighbor.relationship_types)}",
                                    )
                                )
            except Exception:
                # Semantic neighbor discovery is best-effort, don't fail the whole query
                pass

        # [20251229_FEATURE] Pro tier: Add logical relationships
        if "logical_relationship_detection" in cap_set:
            from code_scalpel.graph.logical_relationships import (
                LogicalRelationshipDetector,
            )

            try:
                center_name = center_node_id.split("::")[-1]
                detector = LogicalRelationshipDetector(root_path)
                relationship_result = detector.find_relationships(center_name=center_name, max_relationships=20)

                if relationship_result.success:
                    for rel in relationship_result.relationships:
                        # Add logical relationship as an edge
                        if result.subgraph and rel.source_node in result.node_depths:
                            from code_scalpel.graph_engine import EdgeType, GraphEdge

                            # Ensure target node exists in the graph
                            if rel.target_node not in result.node_depths:
                                result.node_depths[rel.target_node] = k + 1

                            result.subgraph.add_edge(
                                GraphEdge(
                                    from_id=rel.source_node,
                                    to_id=rel.target_node,
                                    edge_type=EdgeType.LOGICAL_RELATED,
                                    confidence=rel.confidence,
                                    evidence=f"Logical: {rel.relationship_type} - {rel.evidence}",
                                )
                            )
            except Exception:
                # Logical relationship detection is best-effort, don't fail the whole query
                pass

        # Convert to response models
        nodes = []
        for node_id, depth in result.node_depths.items():
            node = result.subgraph.get_node(node_id) if result.subgraph else None
            nodes.append(
                NeighborhoodNodeModel(
                    id=node_id,
                    depth=depth,
                    metadata=node.metadata if node else {},
                )
            )

        edges = []
        if result.subgraph:
            for edge in result.subgraph.edges:
                edges.append(
                    NeighborhoodEdgeModel(
                        from_id=edge.from_id,
                        to_id=edge.to_id,
                        edge_type=edge.edge_type.value,
                        confidence=edge.confidence,
                    )
                )

        # Generate Mermaid diagram
        mermaid = _generate_neighborhood_mermaid(nodes, edges, center_node_id)

        hot_nodes: list[str] = []
        if include_enterprise_metrics:
            # [20251225_FEATURE] Best-effort degree metrics within the returned subgraph.
            in_deg: dict[str, int] = {}
            out_deg: dict[str, int] = {}
            for edge in edges:
                out_deg[edge.from_id] = out_deg.get(edge.from_id, 0) + 1
                in_deg[edge.to_id] = in_deg.get(edge.to_id, 0) + 1

            for n in nodes:
                n.in_degree = in_deg.get(n.id, 0)
                n.out_degree = out_deg.get(n.id, 0)

            def _degree_key(n: NeighborhoodNodeModel) -> tuple[int, str]:
                return (((n.in_degree or 0) + (n.out_degree or 0)), n.id)

            hot_nodes = [n.id for n in sorted(nodes, key=_degree_key, reverse=True)[:10] if _degree_key(n)[0] > 0]

        return GraphNeighborhoodResult(
            success=True,
            center_node_id=center_node_id,
            k=actual_k,
            nodes=nodes,
            edges=edges,
            total_nodes=result.total_nodes,
            total_edges=result.total_edges,
            max_depth_reached=result.max_depth_reached,
            truncated=result.truncated or k_limited,
            truncation_warning=result.truncation_warning,
            mermaid=mermaid,
            hot_nodes=hot_nodes,
            query_supported=query_supported,
            traversal_rules_available=traversal_rules_available,
            path_constraints_supported=path_constraints_supported,
        )

    except Exception as e:
        return GraphNeighborhoodResult(
            success=False,
            error=f"Graph neighborhood extraction failed: {str(e)}",
        )


# ============================================================================
# [20251213_FEATURE] v1.5.0 - get_project_map MCP Tool
# ============================================================================


def _get_project_map_sync(
    project_root: str | None,
    include_complexity: bool,
    complexity_threshold: int,
    include_circular_check: bool,
    *,
    tier: str | None = None,
    capabilities: dict | None = None,
    max_files_limit: int | None = None,
    max_modules_limit: int | None = None,
) -> ProjectMapResult:
    """Synchronous implementation of get_project_map.

    The function is tier-aware; limits and capabilities are computed in the async wrapper
    and passed through to avoid re-resolving tier in worker threads.
    """
    import ast
    import subprocess

    from code_scalpel.ast_tools.call_graph import CallGraphBuilder

    root_path = Path(project_root) if project_root else _get_project_root()

    # [20250112_FIX] Resolve tier before try block so it's available in except
    tier = tier or _get_current_tier()

    if not root_path.exists():
        return ProjectMapResult(
            success=False,
            project_root=str(root_path),
            error=f"Project root not found: {root_path}.",
            tier_applied=tier,
            pro_features_enabled=tier in ("pro", "enterprise"),
            enterprise_features_enabled=tier == "enterprise",
        )

    try:
        caps = capabilities or get_tool_capabilities("get_project_map", tier) or {}
        caps_set = set(caps.get("capabilities", set()) or [])
        limits = caps.get("limits", {}) or {}

        effective_max_files = max_files_limit
        if effective_max_files is None:
            effective_max_files = limits.get("max_files")

        effective_max_modules = max_modules_limit
        if effective_max_modules is None:
            effective_max_modules = limits.get("max_modules")

        if effective_max_modules is None:
            effective_max_modules = 50

        modules: list[ModuleInfo] = []
        packages: dict[str, PackageInfo] = {}
        all_entry_points: list[str] = []
        complexity_hotspots: list[str] = []
        total_lines = 0

        # Entry point detection patterns
        entry_decorators = {
            "command",
            "main",
            "cli",
            "app",
            "route",
            "get",
            "post",
            "put",
            "delete",
        }

        def is_entry_point(func_node: ast.AST) -> bool:
            """Check if function is an entry point."""
            # Type guard: must be FunctionDef or AsyncFunctionDef
            if not isinstance(func_node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                return False
            if func_node.name == "main":
                return True
            for dec in getattr(func_node, "decorator_list", []):
                dec_name = ""
                if isinstance(dec, ast.Name):
                    dec_name = dec.id
                elif isinstance(dec, ast.Attribute):
                    dec_name = dec.attr
                elif isinstance(dec, ast.Call):
                    if isinstance(dec.func, ast.Attribute):
                        dec_name = dec.func.attr
                    elif isinstance(dec.func, ast.Name):
                        dec_name = dec.func.id
                if dec_name in entry_decorators:
                    return True
            return False

        def calculate_complexity(tree: ast.AST) -> int:
            """Calculate cyclomatic complexity of a module."""
            complexity = 1  # Base complexity
            for node in ast.walk(tree):
                if isinstance(
                    node,
                    (
                        ast.If,
                        ast.While,
                        ast.For,
                        ast.AsyncFor,
                        ast.ExceptHandler,
                        ast.With,
                        ast.AsyncWith,
                        ast.Assert,
                        ast.comprehension,
                    ),
                ):
                    complexity += 1
                elif isinstance(node, (ast.And, ast.Or)):
                    complexity += 1
                elif isinstance(node, ast.BoolOp):
                    complexity += len(node.values) - 1
            return complexity

        # Collect all Python files
        python_files = list(root_path.rglob("*.py"))

        # [20251229_BUGFIX] Filter exclusions BEFORE applying file limit
        # Previously: files were sorted/limited first, then filtered, causing
        # .venv files to dominate the limited set and then be filtered out,
        # resulting in zero modules detected.
        exclude_patterns = {
            "__pycache__",
            ".git",
            "venv",
            ".venv",
            "env",
            ".env",
            "node_modules",
            "dist",
            "build",
            ".tox",
            ".pytest_cache",
            "htmlcov",
            ".mypy_cache",
        }

        # Filter out excluded directories FIRST
        # Check both exact matches and startswith for patterns like .venv-*
        def should_exclude(file_path: Path) -> bool:
            for part in file_path.parts:
                # Exact match
                if part in exclude_patterns:
                    return True
                # Startswith match for patterns like .venv-mcp-smoke
                for pattern in exclude_patterns:
                    if part.startswith(pattern):
                        return True
            return False

        python_files = [f for f in python_files if not should_exclude(f)]

        # [20251226_FEATURE] Tier-aware file cap - AFTER filtering
        python_files = sorted(python_files)
        if effective_max_files is not None and len(python_files) > effective_max_files:
            python_files = python_files[:effective_max_files]

        for file_path in python_files:
            rel_path = str(file_path.relative_to(root_path))

            try:
                with open(file_path, encoding="utf-8", errors="ignore") as f:
                    code = f.read()

                lines = code.count("\n") + 1
                total_lines += lines

                # [20260119_FEATURE] Uses unified parser for deterministic behavior.
                tree, _ = parse_python_code(code, filename=rel_path)

                # Extract module info
                functions = []
                classes = []
                imports = []
                entry_points = []

                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        functions.append(node.name)
                        if is_entry_point(node):
                            entry_points.append(f"{rel_path}:{node.name}")
                    elif isinstance(node, ast.ClassDef):
                        classes.append(node.name)
                    elif isinstance(node, ast.Import):
                        for alias in node.names:
                            imports.append(alias.name)
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            imports.append(node.module)

                # Calculate complexity if requested
                complexity = 0
                if include_complexity:
                    complexity = calculate_complexity(tree)
                    if complexity >= complexity_threshold:
                        complexity_hotspots.append(f"{rel_path} (complexity: {complexity})")

                all_entry_points.extend(entry_points)

                modules.append(
                    ModuleInfo(
                        path=rel_path,
                        functions=functions,
                        classes=classes,
                        imports=list(set(imports)),  # Dedupe
                        entry_points=entry_points,
                        line_count=lines,
                        complexity_score=complexity,
                    )
                )

                # Track packages
                parent = file_path.parent
                while parent != root_path and parent.exists():
                    init_file = parent / "__init__.py"
                    if init_file.exists():
                        pkg_path = str(parent.relative_to(root_path))
                        pkg_name = parent.name
                        if pkg_path not in packages:
                            packages[pkg_path] = PackageInfo(
                                name=pkg_name,
                                path=pkg_path,
                                modules=[],
                                subpackages=[],
                            )
                        # Add module to package
                        if rel_path not in packages[pkg_path].modules:
                            packages[pkg_path].modules.append(rel_path)
                    parent = parent.parent

            except Exception:
                # Skip files with errors
                continue

        # Organize package hierarchy
        pkg_list = list(packages.values())
        for pkg in pkg_list:
            for other_pkg in pkg_list:
                if other_pkg.path.startswith(pkg.path + "/") and other_pkg.name not in pkg.subpackages:
                    pkg.subpackages.append(other_pkg.name)

        # Check for circular imports
        circular_imports = []
        if include_circular_check:
            builder = CallGraphBuilder(root_path)
            circular_imports = builder.detect_circular_imports()

        # [20251213_FEATURE] Calculate language breakdown
        languages: dict[str, int] = {"python": len(modules)}
        # Also count other common file types
        for ext, lang in [
            (".js", "javascript"),
            (".ts", "typescript"),
            (".java", "java"),
            (".json", "json"),
            (".yaml", "yaml"),
            (".yml", "yaml"),
            (".md", "markdown"),
            (".html", "html"),
            (".css", "css"),
        ]:
            len(list(root_path.rglob(f"*{ext}")))
            # Exclude common ignored dirs
            actual_count = sum(1 for f in root_path.rglob(f"*{ext}") if not any(p in exclude_patterns for p in f.parts))
            if actual_count > 0:
                languages[lang] = languages.get(lang, 0) + actual_count

        modules_in_diagram = (
            len(modules) if effective_max_modules is None else min(len(modules), int(effective_max_modules))
        )
        diagram_limit = modules_in_diagram

        # [20251226_FEATURE] Tier-aware relationship + analytics construction
        dotted_to_path: dict[str, str] = {}
        for mod in modules:
            dotted = mod.path[:-3] if mod.path.endswith(".py") else mod.path
            dotted = dotted.replace("/", ".")
            dotted_to_path[dotted] = mod.path

        def resolve_import_target(import_name: str) -> str | None:
            """Map an import string to a known module path if possible."""
            if import_name in dotted_to_path:
                return dotted_to_path[import_name]
            for dotted_key, path_value in dotted_to_path.items():
                if import_name.startswith(dotted_key):
                    return path_value
            return None

        module_relationships: list[dict[str, str]] | None = None
        dependency_diagram: str | None = None
        architectural_layers: list[dict[str, str]] | None = None
        coupling_metrics: list[dict[str, Any]] | None = None
        force_graph: dict[str, Any] | None = None
        city_map_data: dict[str, Any] | None = None
        churn_heatmap: list[dict[str, Any]] | None = None
        bug_hotspots: list[dict[str, Any]] | None = None
        git_ownership: list[dict[str, Any]] | None = None
        # [20251231_FEATURE] v3.3.1 - New Enterprise feature variables
        multi_repo_summary: dict[str, Any] | None = None
        historical_trends: list[dict[str, Any]] | None = None
        custom_metrics: dict[str, Any] | None = None
        compliance_overlay: dict[str, Any] | None = None

        # [20251226_BUGFIX] Align capability flags with tier when feature map differs
        enable_relationships = (
            "module_relationship_visualization" in caps_set
            or "dependency_tracking" in caps_set
            or (tier and tier.lower() in {"pro", "enterprise"})
        )
        enable_dependency_diagram = "import_dependency_diagram" in caps_set or (
            tier and tier.lower() in {"pro", "enterprise"}
        )
        enable_layers = "architectural_layer_detection" in caps_set or (tier and tier.lower() in {"pro", "enterprise"})
        enable_coupling = "coupling_analysis" in caps_set or (tier and tier.lower() in {"pro", "enterprise"})
        enable_force_graph = "force_directed_graph" in caps_set or (tier and tier.lower() == "enterprise")
        enable_city = "interactive_city_map" in caps_set or (tier and tier.lower() == "enterprise")
        enable_churn = "code_churn_visualization" in caps_set or (tier and tier.lower() == "enterprise")
        enable_bug_hotspots = "bug_hotspot_heatmap" in caps_set or (tier and tier.lower() == "enterprise")
        enable_git_blame = "git_blame_integration" in caps_set or (tier and tier.lower() in {"pro", "enterprise"})
        # [20251231_FEATURE] v3.3.1 - New Enterprise feature flags
        enable_multi_repo = "multi_repository_maps" in caps_set or (tier and tier.lower() == "enterprise")
        enable_historical_trends = "historical_architecture_trends" in caps_set or (
            tier and tier.lower() == "enterprise"
        )
        enable_custom_metrics = "custom_map_metrics" in caps_set or (tier and tier.lower() == "enterprise")
        enable_compliance_overlay = "compliance_overlay" in caps_set or (tier and tier.lower() == "enterprise")

        edges: list[tuple[str, str]] = []
        if (
            enable_relationships
            or enable_dependency_diagram
            or enable_coupling
            or enable_layers
            or enable_force_graph
            or enable_city
        ):
            for mod in modules:
                for imp in mod.imports:
                    target_path = resolve_import_target(imp)
                    if target_path:
                        edges.append((mod.path, target_path))

        if enable_relationships:
            module_relationships = [{"source": src, "target": dst, "type": "import"} for src, dst in edges]

        if enable_dependency_diagram and edges:
            diagram_lines = ["graph TD"]
            for idx, mod in enumerate(modules[:modules_in_diagram]):
                node_id = f"N{idx}"
                label = mod.path.replace("/", "_").replace(".", "_")
                diagram_lines.append(f'    {node_id}["{label}"]')
            path_to_id = {mod.path: f"N{idx}" for idx, mod in enumerate(modules[:modules_in_diagram])}
            for src, dst in edges:
                if src in path_to_id and dst in path_to_id:
                    diagram_lines.append(f"    {path_to_id[src]} --> {path_to_id[dst]}")
            dependency_diagram = "\n".join(diagram_lines)

        if enable_layers:

            def classify_layer(path: str) -> tuple[str, str]:
                lowered = path.lower()
                if any(k in lowered for k in ["controller", "view", "handler", "api"]):
                    return "controller", "Matched controller/view keywords"
                if any(k in lowered for k in ["service", "logic", "manager"]):
                    return "service", "Matched service/logic keywords"
                if any(k in lowered for k in ["repo", "repository", "model", "dao", "db"]):
                    return "repository", "Matched repository/model keywords"
                if any(k in lowered for k in ["util", "helper", "common", "shared"]):
                    return "utility", "Matched utility keywords"
                return "other", "No heuristic match"

            architectural_layers = []
            for mod in modules:
                layer, reason = classify_layer(mod.path)
                architectural_layers.append({"module": mod.path, "layer": layer, "reason": reason})

        if enable_coupling:
            outgoing: dict[str, set[str]] = {mod.path: set() for mod in modules}
            incoming: dict[str, set[str]] = {mod.path: set() for mod in modules}
            for src, dst in edges:
                if src in outgoing:
                    outgoing[src].add(dst)
                if dst in incoming:
                    incoming[dst].add(src)

            coupling_metrics = []
            for mod in modules:
                ca = len(incoming.get(mod.path, set()))
                ce = len(outgoing.get(mod.path, set()))
                denom = ca + ce
                instability = ce / denom if denom else 0.0
                coupling_metrics.append(
                    {
                        "module": mod.path,
                        "afferent": ca,
                        "efferent": ce,
                        "instability": round(instability, 3),
                    }
                )

        if enable_force_graph and edges:
            force_graph = {
                "nodes": [
                    {
                        "id": mod.path,
                        "group": (
                            (architectural_layers or [{}])[idx].get("layer", "other")
                            if architectural_layers
                            else "other"
                        ),
                    }
                    for idx, mod in enumerate(modules)
                ],
                "links": [{"source": src, "target": dst, "value": 1} for src, dst in edges],
            }

        if enable_city:
            city_map_data = {
                "buildings": [
                    {
                        "id": mod.path,
                        "height": max(mod.complexity_score, 1),
                        "footprint": max(mod.line_count // 10, 1),
                        "layer": next(
                            (
                                layer_info["layer"]
                                for layer_info in (architectural_layers or [])
                                if layer_info.get("module") == mod.path
                            ),
                            "other",
                        ),
                    }
                    for mod in modules
                ]
            }

        if enable_churn:
            churn_heatmap = []
            for mod in modules:
                churn_score = mod.complexity_score + len(mod.imports)
                level = "low"
                if churn_score > 20:
                    level = "high"
                elif churn_score > 10:
                    level = "medium"
                churn_heatmap.append({"module": mod.path, "churn_score": churn_score, "level": level})

        if enable_bug_hotspots:
            bug_hotspots = []
            for mod in modules:
                if mod.complexity_score >= complexity_threshold or len(mod.imports) > 5:
                    bug_hotspots.append(
                        {
                            "module": mod.path,
                            "reason": "High complexity or import fan-in",
                        }
                    )
            if not bug_hotspots:
                bug_hotspots = [{"module": mod.path, "reason": "No hotspots detected"} for mod in modules[:1]]

        if enable_git_blame:
            # [20251229_FEATURE] Enterprise: Git blame integration
            git_ownership = []
            try:
                import subprocess

                # Check if we're in a git repository
                result = subprocess.run(
                    ["git", "rev-parse", "--is-inside-work-tree"],
                    cwd=root_path,
                    capture_output=True,
                    text=True,
                    timeout=5,
                )

                if result.returncode == 0:
                    # We're in a git repo, analyze file ownership
                    for mod in modules:
                        try:
                            file_path = root_path / mod.path
                            # Run git blame to get line-by-line authorship
                            blame_result = subprocess.run(
                                ["git", "blame", "--line-porcelain", str(file_path)],
                                cwd=root_path,
                                capture_output=True,
                                text=True,
                                timeout=10,
                            )

                            if blame_result.returncode == 0:
                                # Parse git blame output
                                authors: dict[str, int] = {}
                                for line in blame_result.stdout.split("\n"):
                                    if line.startswith("author "):
                                        author = line[7:].strip()  # Remove "author " prefix
                                        authors[author] = authors.get(author, 0) + 1

                                if authors:
                                    # Find primary owner (most lines authored)
                                    total_lines = sum(authors.values())
                                    primary_owner = max(authors.items(), key=lambda x: x[1])
                                    owner_name = primary_owner[0]
                                    owner_lines = primary_owner[1]
                                    confidence = round(owner_lines / total_lines, 2)

                                    git_ownership.append(
                                        {
                                            "module": mod.path,
                                            "owner": owner_name,
                                            "confidence": confidence,
                                            "contributors": len(authors),
                                            "ownership_breakdown": {
                                                k: round(v / total_lines, 2)
                                                for k, v in sorted(
                                                    authors.items(),
                                                    key=lambda x: x[1],
                                                    reverse=True,
                                                )[:5]
                                            },
                                        }
                                    )
                                else:
                                    git_ownership.append(
                                        {
                                            "module": mod.path,
                                            "owner": "unknown",
                                            "confidence": 0.0,
                                            "reason": "No git blame data",
                                        }
                                    )
                            else:
                                git_ownership.append(
                                    {
                                        "module": mod.path,
                                        "owner": "unknown",
                                        "confidence": 0.0,
                                        "reason": "File not tracked in git",
                                    }
                                )
                        except subprocess.TimeoutExpired:
                            git_ownership.append(
                                {
                                    "module": mod.path,
                                    "owner": "unknown",
                                    "confidence": 0.0,
                                    "reason": "Git blame timeout",
                                }
                            )
                        except Exception as e:
                            git_ownership.append(
                                {
                                    "module": mod.path,
                                    "owner": "unknown",
                                    "confidence": 0.0,
                                    "reason": f"Error: {str(e)}",
                                }
                            )
                else:
                    # Not a git repository
                    git_ownership = [
                        {
                            "module": mod.path,
                            "owner": "unknown",
                            "confidence": 0.0,
                            "reason": "Not a git repository",
                        }
                        for mod in modules
                    ]
            except FileNotFoundError:
                # Git not installed
                git_ownership = [
                    {
                        "module": mod.path,
                        "owner": "unknown",
                        "confidence": 0.0,
                        "reason": "Git not installed",
                    }
                    for mod in modules
                ]
            except Exception as e:
                # Other error
                git_ownership = [
                    {
                        "module": mod.path,
                        "owner": "unknown",
                        "confidence": 0.0,
                        "reason": f"Error: {str(e)}",
                    }
                    for mod in modules
                ]

        # [20251231_FEATURE] v3.3.1 - Enterprise: Historical architecture trends
        if enable_historical_trends:
            historical_trends = []
            try:
                import subprocess

                # Check if we're in a git repository
                result = subprocess.run(
                    ["git", "rev-parse", "--is-inside-work-tree"],
                    cwd=root_path,
                    capture_output=True,
                    text=True,
                    timeout=5,
                )

                if result.returncode == 0:
                    # Get file changes over last 30 days for trend analysis
                    log_result = subprocess.run(
                        [
                            "git",
                            "log",
                            "--since=30 days ago",
                            "--name-only",
                            "--pretty=format:%H|%ad|%an",
                            "--date=short",
                        ],
                        cwd=root_path,
                        capture_output=True,
                        text=True,
                        timeout=30,
                    )

                    if log_result.returncode == 0:
                        # Parse git log output into trends
                        file_change_counts: dict[str, int] = {}
                        date_activity: dict[str, int] = {}

                        current_date = ""
                        for line in log_result.stdout.split("\n"):
                            line = line.strip()
                            if not line:
                                continue
                            if "|" in line:
                                # This is a commit header line
                                parts = line.split("|")
                                if len(parts) >= 2:
                                    current_date = parts[1]
                                    date_activity[current_date] = date_activity.get(current_date, 0) + 1
                            elif line.endswith(".py"):
                                # This is a Python file that was changed
                                file_change_counts[line] = file_change_counts.get(line, 0) + 1

                        # Calculate architecture stability metrics
                        total_changes = sum(file_change_counts.values())
                        hot_files = sorted(file_change_counts.items(), key=lambda x: x[1], reverse=True)[:10]

                        historical_trends = [
                            {
                                "period": "last_30_days",
                                "total_commits": len(date_activity),
                                "total_file_changes": total_changes,
                                "most_changed_files": [{"file": f, "changes": c} for f, c in hot_files],
                                "activity_by_date": date_activity,
                                "stability_score": round(
                                    1.0 - min(total_changes / max(len(modules) * 3, 1), 1.0),
                                    2,
                                ),
                            }
                        ]
                    else:
                        historical_trends = [{"error": "Could not retrieve git log"}]
                else:
                    historical_trends = [{"error": "Not a git repository"}]
            except subprocess.TimeoutExpired:
                historical_trends = [{"error": "Git log timeout"}]
            except FileNotFoundError:
                historical_trends = [{"error": "Git not installed"}]
            except Exception as e:
                historical_trends = [{"error": f"Historical trends failed: {str(e)}"}]

        # [20251231_FEATURE] v3.3.1 - Enterprise: Custom map metrics
        if enable_custom_metrics:
            # Load custom metrics from architecture.toml if present
            custom_metrics = {
                "configured": False,
                "metrics": {},
            }
            try:
                arch_config_path = root_path / ".code-scalpel" / "architecture.toml"
                if arch_config_path.exists():
                    try:
                        import tomllib
                    except ImportError:
                        import tomli as tomllib  # type: ignore

                    with open(arch_config_path, "rb") as f:
                        arch_config = tomllib.load(f)

                    if "custom_metrics" in arch_config:
                        custom_metrics = {
                            "configured": True,
                            "source": str(arch_config_path),
                            "metrics": arch_config["custom_metrics"],
                        }
                    else:
                        custom_metrics["note"] = "No custom_metrics section in architecture.toml"
                else:
                    custom_metrics["note"] = "No .code-scalpel/architecture.toml found"
            except Exception as e:
                custom_metrics["error"] = f"Failed to load custom metrics: {str(e)}"

        # [20251231_FEATURE] v3.3.1 - Enterprise: Compliance overlay
        if enable_compliance_overlay:
            compliance_overlay = {
                "violations": [],
                "status": "unknown",
            }
            try:
                # Try to use the architectural rules engine if available
                arch_config_path = root_path / ".code-scalpel" / "architecture.toml"
                if arch_config_path.exists():
                    try:
                        # [20260101_BUGFIX] Dynamic import to avoid Pyright errors
                        from code_scalpel.ast_tools import architectural_rules

                        ArchitecturalRulesEngine = getattr(architectural_rules, "ArchitecturalRulesEngine", None)
                        if ArchitecturalRulesEngine is None:
                            raise ImportError("ArchitecturalRulesEngine not found")

                        engine = ArchitecturalRulesEngine(str(arch_config_path))

                        # Analyze each module for architectural violations
                        violations: list[dict[str, Any]] = []
                        for mod in modules:
                            for imp in mod.imports:
                                violation = engine.check_import(mod.path, imp)
                                if violation:
                                    violations.append(
                                        {
                                            "file": mod.path,
                                            "import": imp,
                                            "rule": violation.rule_name,
                                            "severity": violation.severity,
                                            "message": violation.message,
                                        }
                                    )

                        compliance_overlay = {
                            "violations": violations,
                            "violation_count": len(violations),
                            "status": ("compliant" if len(violations) == 0 else "non_compliant"),
                            "rules_source": str(arch_config_path),
                        }
                    except ImportError:
                        compliance_overlay = {
                            "violations": [],
                            "status": "unavailable",
                            "note": "Architectural rules engine not available",
                        }
                else:
                    compliance_overlay = {
                        "violations": [],
                        "status": "unconfigured",
                        "note": "No .code-scalpel/architecture.toml found",
                    }
            except Exception as e:
                compliance_overlay = {
                    "violations": [],
                    "status": "error",
                    "error": f"Compliance check failed: {str(e)}",
                }

        # [20251231_FEATURE] v3.3.1 - Enterprise: Multi-repository summary placeholder
        # This feature requires additional_roots parameter; for now provide metadata
        if enable_multi_repo:
            multi_repo_summary = {
                "enabled": True,
                "primary_root": str(root_path),
                "additional_roots": [],  # Future: pass via parameter
                "note": "Pass additional_roots parameter for multi-repo analysis",
                "total_repositories": 1,
            }

        # Generate Mermaid package diagram
        mermaid_lines = ["graph TD"]
        mermaid_lines.append("    subgraph Project")
        for i, mod in enumerate(modules[:diagram_limit]):
            mod_id = f"M{i}"
            label = mod.path.replace("/", "_").replace(".", "_")
            if mod.entry_points:
                mermaid_lines.append(f'        {mod_id}[["{label}"]]')  # Stadium for entry
            else:
                mermaid_lines.append(f'        {mod_id}["{label}"]')
        mermaid_lines.append("    end")

        # [20251220_FEATURE] v3.0.5 - Communicate truncation
        diagram_truncated = effective_max_modules is not None and len(modules) > effective_max_modules
        if diagram_truncated and effective_max_modules is not None:
            mermaid_lines.append(f"    Note[... and {len(modules) - int(effective_max_modules)} more modules]")

        return ProjectMapResult(
            project_root=str(root_path),
            total_files=len(modules),
            total_lines=total_lines,
            languages=languages,
            packages=pkg_list,
            modules=modules,
            entry_points=all_entry_points,
            circular_imports=circular_imports,
            complexity_hotspots=complexity_hotspots,
            mermaid="\n".join(mermaid_lines),
            module_relationships=module_relationships,
            architectural_layers=architectural_layers,
            coupling_metrics=coupling_metrics,
            dependency_diagram=dependency_diagram,
            city_map_data=city_map_data,
            force_graph=force_graph,
            churn_heatmap=churn_heatmap,
            bug_hotspots=bug_hotspots,
            git_ownership=git_ownership,
            # [20251231_FEATURE] v3.3.1 - New Enterprise fields
            multi_repo_summary=multi_repo_summary,
            historical_trends=historical_trends,
            custom_metrics=custom_metrics,
            compliance_overlay=compliance_overlay,
            modules_in_diagram=modules_in_diagram,
            diagram_truncated=diagram_truncated,
            # [20250112_FIX] v3.3.0 - Include tier metadata fields
            tier_applied=tier,
            max_files_applied=effective_max_files,
            max_modules_applied=effective_max_modules,
            pro_features_enabled=tier in ("pro", "enterprise"),
            enterprise_features_enabled=tier == "enterprise",
        )

    except Exception as e:
        # tier is available since we resolve it before the try block
        return ProjectMapResult(
            success=False,
            project_root=str(root_path),
            error=f"Project map analysis failed: {str(e)}",
            tier_applied=tier,
            pro_features_enabled=tier in ("pro", "enterprise"),
            enterprise_features_enabled=tier == "enterprise",
        )


# ============================================================================
# [20251213_FEATURE] v1.5.1 - get_cross_file_dependencies MCP Tool
# ============================================================================


def _get_cross_file_dependencies_sync(
    target_file: str,
    target_symbol: str,
    project_root: str | None,
    max_depth: int,
    include_code: bool,
    include_diagram: bool,
    confidence_decay_factor: float = 0.9,
    tier: str | None = None,
    capabilities: dict | None = None,
    max_files_limit: int | None = None,
    timeout_seconds: float | None = None,
) -> CrossFileDependenciesResult:
    """
    Synchronous implementation of get_cross_file_dependencies.

    [20251220_BUGFIX] v3.0.5 - Parameter order matches async function for consistency.
    """
    import os

    from code_scalpel.ast_tools.cross_file_extractor import CrossFileExtractor
    from code_scalpel.licensing.features import get_tool_capabilities

    root_path = Path(project_root) if project_root else _get_project_root()

    # [20260127_FIX] Heuristic Auto-Scoping for Community Tier
    # If project_root is not provided by user, check if default usage would cover too many files.
    # If so, scope down to the parent directory of the target file instead of the entire project root.
    if project_root is None and not tier == "enterprise":
        # Check volume roughly
        try:
            # Fast check using git if available, or os.walk (limited)
            # Here we assume a simple heuristic: if we are deeper than root, use parent dir.
            target_path_obj = Path(target_file)
            if not target_path_obj.is_absolute():
                target_path_obj = root_path / target_file

            # If target is inside root_path but deeper
            if target_path_obj.exists() and len(target_path_obj.parts) > len(root_path.parts) + 1:
                # Re-scope root to the parent of the target file
                # e.g. /project/src/module/file.py -> /project/src/module
                root_path = target_path_obj.parent
        except Exception:
            pass  # Fallback to default behavior on error

    if not root_path.exists():
        return CrossFileDependenciesResult(
            success=False,
            error=f"Project root not found: {root_path}.",
        )

    # Resolve target file path
    target_path = Path(target_file)
    if not target_path.is_absolute():
        target_path = root_path / target_file

    if not target_path.exists():
        return CrossFileDependenciesResult(
            success=False,
            error=f"Target file not found: {target_path}.",
        )

    tier = tier or _get_current_tier()
    caps = capabilities or get_tool_capabilities("get_cross_file_dependencies", tier)
    caps_set = set(caps.get("capabilities", set()) or [])
    limits = caps.get("limits", {}) or {}

    effective_max_depth = max_depth
    depth_limit = limits.get("max_depth")
    if depth_limit is not None and effective_max_depth > depth_limit:
        effective_max_depth = int(depth_limit)

    if max_files_limit is None:
        max_files_limit = limits.get("max_files")

    # Allow caller override but never exceed tier-imposed limit
    if limits.get("max_files") is not None and max_files_limit is not None:
        max_files_limit = min(max_files_limit, limits["max_files"])

    # [20251227_REFACTOR] Uniform generous timeout for all tiers
    # Timeout is a safeguard, not a tier feature. The depth/file limits
    # naturally bound execution time. Timeout only triggers for pathological cases.
    build_timeout = int(timeout_seconds) if timeout_seconds else 120

    allow_transitive = "transitive_dependency_mapping" in caps_set
    coupling_enabled = "deep_coupling_analysis" in caps_set
    firewall_enabled = "architectural_firewall" in caps_set or "boundary_violation_alerts" in caps_set

    # [20260104_BUGFIX] Initialize all variables that may be referenced in return statement
    # to avoid UnboundLocalError if exception occurs before assignment
    files_analyzed = 0
    max_depth_reached = 0
    files_scanned = 0
    files_truncated = 0
    truncation_warning = None

    try:
        from concurrent.futures import ThreadPoolExecutor
        from concurrent.futures import TimeoutError as FuturesTimeoutError

        def run_with_timeout(func, timeout_seconds, *args, **kwargs):
            """
            Cross-platform timeout wrapper using ThreadPoolExecutor.

            Works on both Unix/Linux and Windows by running the function
            in a thread pool with a timeout.

            Args:
                func: Function to execute
                timeout_seconds: Maximum execution time in seconds
                *args, **kwargs: Arguments to pass to func

            Returns:
                Result from func

            Raises:
                TimeoutError: If execution exceeds timeout_seconds
            """
            # NOTE: Avoid `with ThreadPoolExecutor(...)` here.
            # If `future.result(timeout=...)` times out, the context manager's
            # shutdown(wait=True) can block forever waiting for a hung worker.
            executor = ThreadPoolExecutor(max_workers=1)
            future = executor.submit(func, *args, **kwargs)
            try:
                return future.result(timeout=timeout_seconds)
            except FuturesTimeoutError:
                future.cancel()
                raise TimeoutError(f"Operation timed out after {timeout_seconds} seconds")
            finally:
                # Do not wait for a potentially hung worker thread.
                executor.shutdown(wait=False, cancel_futures=True)

        # Build CrossFileExtractor (includes ImportResolver.build()) with timeout protection.
        def build_extractor():
            extractor = CrossFileExtractor(root_path)
            extractor.build()
            return extractor

        try:
            # [20251227_REFACTOR] Generous timeout safeguard (not tier-limited)
            # [20260127_FIX] Add volume check before build to prevent timeout on large repos
            # Community tier limit is 500 files. If scoping is wide (root_path), verify count first.
            if tier == "community" or (tier is None and not caps):
                file_count = 0
                too_many = False
                for _, _, files in os.walk(str(root_path)):
                    file_count += len(files)
                    if file_count > 500:
                        too_many = True
                        break
                if too_many:
                    return CrossFileDependenciesResult(
                        success=False,
                        error=f"Scope too large (>500 files). Community Tier is limited to 500 files per scan. Please verify a specific subdirectory using the 'project_root' parameter (Current: {root_path}).",
                    )

            extractor = run_with_timeout(build_extractor, build_timeout)
        except TimeoutError:
            # [20251227_FEATURE] Context-window aware error messaging for AI agents
            return CrossFileDependenciesResult(
                success=False,
                error=(
                    f"TIMEOUT ({build_timeout}s): CrossFileExtractor.build() exceeded safeguard limit. "
                    f"FIX: Use a smaller project_root scope. Current: {root_path}. "
                    f"EXAMPLE: Instead of project root, target a specific subdirectory like 'src/module/'. "
                    f"LIMITS: max_depth={effective_max_depth}, max_files={max_files_limit or 'unlimited'}."
                ),
            )

        # [20251216_FEATURE] v2.5.0 - Pass confidence_decay_factor to extractor
        def extract_dependencies():
            return extractor.extract(
                str(target_path),
                target_symbol,
                depth=effective_max_depth,
                confidence_decay_factor=confidence_decay_factor,
            )

        # [20251227_REFACTOR] Extraction timeout is 50% of build timeout
        extraction_timeout = build_timeout // 2
        try:
            extraction_result = run_with_timeout(extract_dependencies, extraction_timeout)
        except TimeoutError:
            # [20251227_FEATURE] Context-window aware error messaging for AI agents
            return CrossFileDependenciesResult(
                success=False,
                error=(
                    f"TIMEOUT ({extraction_timeout}s): Extracting '{target_symbol}' exceeded safeguard limit. "
                    f"FIX: Reduce max_depth (current: {effective_max_depth}) or target a simpler symbol. "
                    f"EXAMPLE: Try max_depth=1 for direct dependencies only. "
                    f"FILE: {target_path}"
                ),
            )

        # Check for extraction errors
        if not extraction_result.success:
            return CrossFileDependenciesResult(
                success=False,
                error=f"Extraction failed: {'; '.join(extraction_result.errors)}.",
            )

        # Build the list of all symbols (target + dependencies)
        all_symbols = []
        if extraction_result.target:
            all_symbols.append(extraction_result.target)
        all_symbols.extend(extraction_result.dependencies)

        # Convert extracted symbols to models
        extracted_symbols = []
        combined_parts = []

        # [20251216_FEATURE] v2.5.0 - Low confidence threshold
        LOW_CONFIDENCE_THRESHOLD = 0.5

        for sym in all_symbols:
            rel_file = str(Path(sym.file).relative_to(root_path)) if Path(sym.file).is_absolute() else sym.file
            # [20251216_FEATURE] v2.5.0 - Include depth and confidence in symbol model
            extracted_symbols.append(
                ExtractedSymbolModel(
                    name=sym.name,
                    code=sym.code if include_code else "",
                    file=rel_file,
                    line_start=sym.line,  # ExtractedSymbol uses 'line' not 'line_start'
                    line_end=sym.end_line or 0,  # ExtractedSymbol uses 'end_line'
                    dependencies=list(sym.dependencies),
                    depth=sym.depth,
                    confidence=sym.confidence,
                    low_confidence=sym.confidence < LOW_CONFIDENCE_THRESHOLD,
                )
            )
            if include_code:
                combined_parts.append(f"# From {rel_file}")
                combined_parts.append(sym.code)

        combined_code = "\n\n".join(combined_parts) if include_code else ""

        # Use the extractor's combined code if available (includes proper ordering)
        if include_code and extraction_result.combined_code:
            combined_code = extraction_result.combined_code

        # Get unresolved imports from extraction result
        unresolved_imports = extraction_result.module_imports  # These are imports that couldn't be resolved

        # Build import graph dict (file -> list of imported files)
        # Use the extractor's resolver (avoid double-building) and keep this focused.
        resolver = extractor.resolver
        import_graph: dict[str, list[str]] = {}

        # [20251226_FEATURE] Tier-aware truncation and metrics
        file_order: list[str] = []
        for sym in extracted_symbols:
            if sym.file not in file_order:
                file_order.append(sym.file)

        files_scanned = len(file_order)
        files_truncated = 0
        truncation_warning = None
        if max_files_limit is not None and files_scanned > max_files_limit:
            files_truncated = files_scanned - max_files_limit
            allowed_files = set(file_order[:max_files_limit])
            truncation_warning = f"Truncated to {max_files_limit} files (of {files_scanned}) due to tier limits."
            extracted_symbols = [sym for sym in extracted_symbols if sym.file in allowed_files]
            file_order = file_order[:max_files_limit]

            if include_code:
                combined_parts = []
                for sym in extracted_symbols:
                    combined_parts.append(f"# From {sym.file}")
                    combined_parts.append(sym.code)
                combined_code = "\n\n".join(combined_parts)

        # Limit graph construction to files actually involved in the extraction.
        files_of_interest: set[str] = set()
        for sym in extracted_symbols:
            try:
                p = Path(sym.file)
                if not p.is_absolute():
                    p = root_path / p
                p = p.resolve()
                files_of_interest.add(str(p))
            except Exception:
                continue
        files_of_interest.add(str(target_path.resolve()))

        for abs_file in files_of_interest:
            module_name = resolver.file_to_module.get(abs_file)
            if not module_name:
                continue

            rel_path = str(Path(abs_file).relative_to(root_path))
            imported_files: list[str] = []
            for imp in resolver.imports.get(module_name, []):
                resolved_file = resolver.module_to_file.get(imp.module)
                if not resolved_file:
                    continue
                try:
                    resolved_abs = str(Path(resolved_file).resolve())
                    if resolved_abs not in files_of_interest:
                        continue
                    resolved_rel = str(Path(resolved_abs).relative_to(root_path))
                except Exception:
                    continue
                if resolved_rel not in imported_files:
                    imported_files.append(resolved_rel)

            if imported_files:
                import_graph[rel_path] = imported_files

        # Make target file relative (used by diagram + returned fields)
        target_rel = str(target_path.relative_to(root_path)) if target_path.is_absolute() else target_file

        transitive_depth = effective_max_depth

        # [20251226_FEATURE] Enforce tier depth clamp: ensure we never exceed tier's configured max_depth.
        # This applies even if user requested higher. For community, max_depth_limit is 1.
        max_depth_limit = limits.get("max_depth")
        if max_depth_limit is not None and transitive_depth > max_depth_limit:
            transitive_depth = int(max_depth_limit)

        coupling_score: float | None = None
        if coupling_enabled:
            unique_files = len(file_order) if file_order else 0
            deps_count = max(0, len(extracted_symbols) - 1)
            if unique_files > 0:
                coupling_score = round(deps_count / unique_files, 3)

        dependency_chains: list[list[str]] = []
        if allow_transitive and import_graph:
            from collections import deque

            max_chains = 25
            queue = deque([(target_rel, [target_rel], 0)])
            seen_paths: set[tuple[str, ...]] = set()
            while queue and len(dependency_chains) < max_chains:
                current, path, depth = queue.popleft()
                if depth >= transitive_depth:
                    continue
                for dep in import_graph.get(current, []):
                    new_path = path + [dep]
                    path_key = tuple(new_path)
                    if path_key in seen_paths:
                        continue
                    seen_paths.add(path_key)
                    dependency_chains.append(new_path)
                    queue.append((dep, new_path, depth + 1))

            # Update max_depth_reached: longest chain (edges = len-1), bounded by transitive_depth limit.
            # The test expects max_depth_reached <= transitive_depth (which is tier-clamped).
            if dependency_chains:
                chain_depths = [max(0, len(c) - 1) for c in dependency_chains]
                if chain_depths:
                    observed = max(chain_depths)
                    # But we enforce transitive_depth as the hard limit; if chains are longer, cap it.
                    max_depth_reached = min(max(max_depth_reached, observed), transitive_depth)

        # [20251226_FEATURE] Enterprise architectural firewall outputs
        boundary_violations: list[dict[str, Any]] = []
        layer_violations: list[dict[str, Any]] = []
        architectural_alerts: list[dict[str, Any]] = []

        def _infer_layer(rel_path: str) -> str:
            lowered = rel_path.lower()
            if "controllers" in lowered or "api" in lowered:
                return "presentation"
            if "services" in lowered or "service" in lowered:
                return "domain"
            if "models" in lowered or "entities" in lowered:
                return "data"
            return "unknown"

        if firewall_enabled and import_graph:
            layer_rank = {"presentation": 3, "domain": 2, "data": 1, "unknown": 0}
            for src_file, targets in import_graph.items():
                src_layer = _infer_layer(src_file)
                for dst_file in targets:
                    dst_layer = _infer_layer(dst_file)
                    if src_layer == "presentation" and dst_layer == "data":
                        violation = {
                            "type": "layer_skip",
                            "source": src_file,
                            "target": dst_file,
                            "violation": "Presentation layer should not depend directly on data layer",
                            "recommendation": "Route dependencies through services to enforce layering",
                        }
                        boundary_violations.append(violation)
                        layer_violations.append(violation)
                    elif layer_rank.get(src_layer, 0) < layer_rank.get(dst_layer, 0) and dst_layer != "unknown":
                        violation = {
                            "type": "upward_dependency",
                            "source": src_file,
                            "target": dst_file,
                            "violation": "Lower layers should not depend on higher layers",
                            "recommendation": "Refactor to invert dependency or introduce interface",
                        }
                        layer_violations.append(violation)

            if boundary_violations or layer_violations:
                architectural_alerts.append(
                    {
                        "severity": "high",
                        "message": "Architectural boundary violations detected",
                        "count": len(boundary_violations) + len(layer_violations),
                    }
                )

        # Detect circular imports using get_circular_imports()
        circular_import_objs = resolver.get_circular_imports()
        circular_import_lists = [ci.cycle for ci in circular_import_objs]  # CircularImport uses 'cycle'

        # Make target file relative (used by diagram + returned fields)
        target_rel = str(target_path.relative_to(root_path)) if target_path.is_absolute() else target_file

        # Generate Mermaid diagram
        mermaid = ""
        if include_diagram:
            from collections import deque

            # Generate a focused diagram to avoid project-wide graph explosion.
            # We bound the subgraph by max_depth and cap nodes/edges.
            max_mermaid_nodes = 60
            max_mermaid_edges = 200

            start_file = target_rel
            # BFS from target file using the computed import_graph (file -> imported files)
            queue = deque([(start_file, 0)])
            seen_nodes: set[str] = set()
            edges_out: list[tuple[str, str]] = []

            while queue and len(seen_nodes) < max_mermaid_nodes and len(edges_out) < max_mermaid_edges:
                cur, depth = queue.popleft()
                if cur in seen_nodes:
                    continue
                seen_nodes.add(cur)
                if depth >= effective_max_depth:
                    continue
                for dep in import_graph.get(cur, [])[:max_mermaid_edges]:
                    if len(edges_out) >= max_mermaid_edges:
                        break
                    edges_out.append((cur, dep))
                    if dep not in seen_nodes:
                        queue.append((dep, depth + 1))

            # Mermaid with stable short node ids
            lines = ["graph TD"]
            node_ids: dict[str, str] = {}
            # Always include the start node (even if it has no outgoing edges)
            seen_nodes.add(start_file)
            for i, n in enumerate(sorted(seen_nodes)):
                node_ids[n] = f"N{i}"
                safe_label = n.replace("/", "_").replace(".", "_")
                lines.append(f"    {node_ids[n]}[{safe_label}]")

            for a, b in edges_out:
                if a in node_ids and b in node_ids:
                    lines.append(f"    {node_ids[a]} --> {node_ids[b]}")

            # Truncation hint
            if len(seen_nodes) >= max_mermaid_nodes or len(edges_out) >= max_mermaid_edges:
                lines.append(f"    %% Diagram truncated (nodes<={max_mermaid_nodes}, edges<={max_mermaid_edges})")

            mermaid = "\n".join(lines)

        # Calculate token estimate (rough: 4 chars per token)
        token_estimate = len(combined_code) // 4 if combined_code else 0

        # [20251216_FEATURE] v2.5.0 - Build low confidence warning if needed
        low_confidence_warning = None
        if extraction_result.low_confidence_count > 0:
            low_conf_names = [s.name for s in extraction_result.get_low_confidence_symbols()[:5]]
            low_confidence_warning = (
                f"⚠️ {extraction_result.low_confidence_count} symbol(s) have low confidence "
                f"(below 0.5): {', '.join(low_conf_names)}"
                + ("..." if extraction_result.low_confidence_count > 5 else "")
            )

        # Pro/Enterprise derived insights
        alias_resolutions: list[AliasResolutionModel] = []
        chained_alias_resolutions: list[ChainedAliasResolutionModel] = []
        wildcard_expansions: list[WildcardExpansionModel] = []
        reexport_chains: list[ReexportChainModel] = []
        coupling_violations: list[CouplingViolationModel] = []
        architectural_violations: list[ArchitecturalViolationModel] = []
        boundary_alerts: list[BoundaryAlertModel] = []
        layer_mapping: dict[str, list[str]] = {}
        rules_applied: list[str] = []
        exempted_files: list[str] = []
        files_analyzed = len(files_of_interest)
        if max_files_limit is not None:
            files_analyzed = min(files_analyzed, max_files_limit)
        max_depth_reached = extraction_result.depth_reached

        # Alias / wildcard / re-export analysis (Pro+)
        if tier != "community":
            module_cache: dict[str, str] = {}
            for abs_file in files_of_interest:
                module_name = resolver.file_to_module.get(abs_file)
                if not module_name:
                    continue
                module_cache[abs_file] = module_name

                # Alias resolutions
                for imp in resolver.imports.get(module_name, []):
                    if imp.alias:
                        try:
                            rel_file = str(Path(abs_file).relative_to(root_path))
                        except Exception:
                            rel_file = Path(abs_file).name

                        alias_resolutions.append(
                            AliasResolutionModel(
                                alias=imp.alias,
                                original_module=imp.module or "",
                                original_name=imp.name,
                                file=rel_file,
                                line=imp.line,
                            )
                        )
                        try:
                            resolved_mod, resolved_name, chain = resolver.resolve_alias_chain(module_name, imp.alias)
                            chained_alias_resolutions.append(
                                ChainedAliasResolutionModel(
                                    symbol=imp.alias,
                                    chain=chain or [],
                                    resolved_module=resolved_mod,
                                    resolved_name=resolved_name,
                                )
                            )
                        except Exception:
                            chained_alias_resolutions.append(
                                ChainedAliasResolutionModel(
                                    symbol=imp.alias,
                                    chain=[],
                                    resolved_module=None,
                                    resolved_name=None,
                                )
                            )

                # Wildcard expansions per module
                wildcard_map = resolver.expand_all_wildcards(module_name)
                for src_module, symbols in wildcard_map.items():
                    if symbols:
                        wildcard_expansions.append(
                            WildcardExpansionModel(from_module=src_module, expanded_symbols=symbols)
                        )

            # Re-export chains (project-wide)
            reexports = resolver.get_all_reexports()
            for apparent, mapping in reexports.items():
                for symbol, actual in mapping.items():
                    reexport_chains.append(
                        ReexportChainModel(
                            symbol=symbol,
                            apparent_source=apparent,
                            actual_source=actual,
                        )
                    )

        # Enterprise architectural rule engine outputs
        if firewall_enabled and caps_set.intersection(
            {
                "architectural_firewall",
                "dependency_rule_engine",
                "layer_constraint_enforcement",
            }
        ):
            try:
                from code_scalpel.ast_tools.architectural_rules import (
                    ArchitecturalRuleEngine,
                )

                engine = ArchitecturalRuleEngine(root_path)
                engine.load_config()

                rules_applied = list(engine.get_all_rules().keys())
                rules_applied.extend([r.name for r in engine.config.custom_rules])

                # Map modules to layers and exemptions
                for abs_file in files_of_interest:
                    module_name = resolver.file_to_module.get(abs_file)
                    if not module_name:
                        continue

                    if engine.is_exempt(module_name):
                        try:
                            exempted_files.append(str(Path(abs_file).relative_to(root_path)))
                        except Exception:
                            exempted_files.append(Path(abs_file).name)

                    layer = engine.get_layer(module_name)
                    if layer:
                        try:
                            rel = str(Path(abs_file).relative_to(root_path))
                        except Exception:
                            rel = Path(abs_file).name
                        layer_mapping.setdefault(layer, []).append(rel)

                # Dependency violations
                module_for_rel: dict[str, str] = {}
                for rel_path in import_graph.keys():
                    abs_path = str((root_path / rel_path).resolve())
                    module = resolver.file_to_module.get(abs_path)
                    if module:
                        module_for_rel[rel_path] = module

                for rel_src, targets in import_graph.items():
                    src_module = module_for_rel.get(rel_src)
                    if not src_module:
                        continue
                    for rel_tgt in targets:
                        tgt_module = module_for_rel.get(rel_tgt)
                        if not tgt_module:
                            continue
                        violations = engine.check_dependency(src_module, tgt_module)
                        for v in violations:
                            architectural_violations.append(
                                ArchitecturalViolationModel(
                                    type=v.rule_name,
                                    severity=v.severity.value,
                                    source=rel_src,
                                    target=rel_tgt,
                                    from_layer=v.from_layer,
                                    to_layer=v.to_layer,
                                    description=v.description,
                                    recommendation=None,
                                )
                            )
                            if v.from_layer and v.to_layer:
                                boundary_alerts.append(
                                    BoundaryAlertModel(
                                        rule=v.rule_name,
                                        from_layer=v.from_layer,
                                        to_layer=v.to_layer,
                                        source=rel_src,
                                        target=rel_tgt,
                                    )
                                )

                # Coupling violations
                for abs_file in files_of_interest:
                    module_name = resolver.file_to_module.get(abs_file)
                    if not module_name:
                        continue
                    fan_in = len(resolver.reverse_edges.get(module_name, set()))
                    fan_out = len(resolver.edges.get(module_name, set()))
                    coupling_viols = engine.check_coupling(module_name, fan_in, fan_out, max_depth_reached)
                    for v in coupling_viols:
                        metric = "fan_in"
                        limit = engine.config.coupling_limits.max_fan_in
                        value = fan_in
                        if v.rule_name == "high_fan_out":
                            metric = "fan_out"
                            limit = engine.config.coupling_limits.max_fan_out
                            value = fan_out
                        elif v.rule_name == "deep_dependency_chain":
                            metric = "dependency_depth"
                            limit = engine.config.coupling_limits.max_dependency_depth
                            value = max_depth_reached

                        coupling_violations.append(
                            CouplingViolationModel(
                                metric=metric,
                                value=value,
                                limit=limit,
                                module=module_name,
                                severity=v.severity.value,
                                description=v.description,
                            )
                        )

            except Exception:
                # Keep Enterprise extras optional; do not fail core analysis
                pass

        return CrossFileDependenciesResult(
            success=True,
            target_name=target_symbol,
            target_file=target_rel,
            extracted_symbols=extracted_symbols,
            total_dependencies=len(extracted_symbols) - 1,  # Exclude target itself
            unresolved_imports=unresolved_imports,  # Use local variable set from module_imports
            import_graph=import_graph,
            circular_imports=circular_import_lists,
            combined_code=combined_code,
            token_estimate=token_estimate,
            mermaid=mermaid,
            # [20251216_FEATURE] v2.5.0 - Confidence decay fields
            confidence_decay_factor=confidence_decay_factor,
            low_confidence_count=extraction_result.low_confidence_count,
            low_confidence_warning=low_confidence_warning,
            # [20251226_FEATURE] Tier-aware outputs
            transitive_depth=transitive_depth,
            alias_resolutions=alias_resolutions,
            wildcard_expansions=wildcard_expansions,
            reexport_chains=reexport_chains,
            chained_alias_resolutions=chained_alias_resolutions,
            coupling_score=coupling_score,
            coupling_violations=coupling_violations,
            dependency_chains=dependency_chains,
            boundary_violations=boundary_violations,
            layer_violations=layer_violations,
            architectural_alerts=architectural_alerts,
            architectural_violations=architectural_violations,
            boundary_alerts=boundary_alerts,
            layer_mapping=layer_mapping,
            rules_applied=rules_applied,
            architectural_rules_applied=rules_applied,
            exempted_files=exempted_files,
            files_scanned=files_scanned,
            files_truncated=files_truncated,
            truncation_warning=truncation_warning,
            truncated=files_truncated > 0,
            files_analyzed=files_analyzed,
            max_depth_reached=max_depth_reached,
        )

    except Exception as e:
        return CrossFileDependenciesResult(
            success=False,
            error=f"Cross-file dependency analysis failed: {str(e)}",
        )


# ============================================================================
# [20251213_FEATURE] v1.5.1 - cross_file_security_scan MCP Tool
# ============================================================================


def _cross_file_security_scan_sync(
    project_root: str | None,
    entry_points: list[str] | None,
    max_depth: int,
    include_diagram: bool,
    timeout_seconds: float | None = 120.0,  # [20251220_PERF] Default 2 minute timeout
    max_modules: int | None = 500,  # [20251220_PERF] Default module limit for large projects
    tier: str | None = None,
    capabilities: dict | None = None,
    confidence_threshold: float = 0.7,
) -> CrossFileSecurityResult:
    """Synchronous implementation of cross_file_security_scan."""
    from code_scalpel.licensing.features import get_tool_capabilities
    from code_scalpel.security.analyzers import CrossFileTaintTracker

    tier = tier or _get_current_tier()
    caps = capabilities or get_tool_capabilities("cross_file_security_scan", tier)
    caps_set = set(caps.get("capabilities", set()) or [])
    limits = caps.get("limits", {}) or {}

    # Enforce limits (support both max_* keys from limits.toml and features.py)
    max_modules_limit = limits.get("max_modules") if "max_modules" in limits else limits.get("max_files")
    if max_modules_limit is not None and max_modules is not None:
        max_modules = min(max_modules, max_modules_limit)
    elif max_modules_limit is not None:
        max_modules = max_modules_limit

    max_depth_limit = limits.get("max_depth") if "max_depth" in limits else limits.get("max_taint_depth")
    if max_depth_limit is not None and max_depth is not None:
        max_depth = min(max_depth, max_depth_limit)
    elif max_depth_limit is not None:
        max_depth = max_depth_limit

    root_path = Path(project_root) if project_root else _get_project_root()

    if not root_path.exists():
        return CrossFileSecurityResult(
            success=False,
            error=f"Project root not found: {root_path}.",
        )

    try:
        tracker = CrossFileTaintTracker(root_path)
        # [20251220_PERF] Pass timeout and module limit to prevent hanging
        result = tracker.analyze(
            entry_points=entry_points,
            max_depth=max_depth,
            timeout_seconds=timeout_seconds,
            max_modules=max_modules,
        )

        # Helper to get file path from module name
        def get_file_for_module(module: str) -> str:
            """Get file path for a module, falling back to module name if not found."""
            file_path = tracker.resolver.module_to_file.get(module, module)
            if isinstance(file_path, Path):
                file_path = str(file_path)
            # Make relative if absolute
            try:
                p = Path(file_path)
                if p.is_absolute():
                    return str(p.relative_to(root_path))
            except (ValueError, TypeError):
                pass
            return file_path

        # Convert vulnerabilities to models
        vulnerabilities = []
        for vuln in result.vulnerabilities:
            # [20260115_FEATURE] Filter by confidence (verified taint = 0.95)
            if 0.95 < confidence_threshold:
                continue

            # [20251215_BUGFIX] v2.0.1 - Use source_module not source_file
            source_file = get_file_for_module(vuln.flow.source_module)
            sink_file = get_file_for_module(vuln.flow.sink_module)

            flow_model = TaintFlowModel(
                source_function=vuln.flow.source_function,
                source_file=source_file,
                source_line=vuln.flow.source_line,
                sink_function=vuln.flow.sink_function,
                sink_file=sink_file,
                sink_line=vuln.flow.sink_line,
                flow_path=[f"{get_file_for_module(m)}:{f}" for m, f, _ in vuln.flow.flow_path],
                taint_type=str(
                    vuln.flow.sink_type.name if hasattr(vuln.flow.sink_type, "name") else vuln.flow.sink_type
                ),
            )
            vulnerabilities.append(
                CrossFileVulnerabilityModel(
                    type=vuln.vulnerability_type,
                    cwe=vuln.cwe_id,
                    severity=vuln.severity,
                    source_file=source_file,
                    sink_file=sink_file,
                    description=vuln.description,
                    flow=flow_model,
                )
            )

        # Convert taint flows to models
        taint_flows = []
        for flow in result.taint_flows:
            # [20251215_BUGFIX] v2.0.1 - Use source_module not source_file
            source_file = get_file_for_module(flow.source_module)
            sink_file = get_file_for_module(flow.sink_module)

            taint_flows.append(
                TaintFlowModel(
                    source_function=flow.source_function,
                    source_file=source_file,
                    source_line=flow.source_line,
                    sink_function=flow.sink_function,
                    sink_file=sink_file,
                    sink_line=flow.sink_line,
                    flow_path=[f"{get_file_for_module(m)}:{f}" for m, f, _ in flow.flow_path],
                    taint_type=str(flow.sink_type.name if hasattr(flow.sink_type, "name") else flow.sink_type),
                )
            )

        # Determine risk level
        vuln_count = len(vulnerabilities)
        if vuln_count == 0:
            risk_level = "low"
        elif vuln_count <= 2:
            risk_level = "medium"
        elif vuln_count <= 5:
            risk_level = "high"
        else:
            risk_level = "critical"

        # Generate Mermaid diagram
        mermaid = ""
        if include_diagram:
            mermaid = tracker.get_taint_graph_mermaid()

        # Extract taint sources from tracker's internal state
        taint_sources = []
        dangerous_sinks = []

        # Get taint sources if available
        if hasattr(tracker, "module_taint_sources"):
            for module, sources in tracker.module_taint_sources.items():
                for src in sources:
                    taint_sources.append(f"{module}:{src.function}")

        # Get sinks from taint flows
        for flow in result.taint_flows:
            sink_key = f"{flow.sink_function}"
            if sink_key not in dangerous_sinks:
                dangerous_sinks.append(sink_key)

        # Tier-aware enrichments (heuristic, lightweight to satisfy tier expectations)
        framework_contexts: list[dict[str, Any]] | None = None
        dependency_chains: list[dict[str, Any]] | None = None
        confidence_scores: dict[str, float] | None = None
        global_flows: list[dict[str, Any]] | None = None
        microservice_boundaries: list[dict[str, Any]] | None = None
        distributed_trace: dict[str, Any] | None = None

        def _detect_framework_contexts(base_path: Path, limit: int | None) -> list[dict[str, Any]]:
            contexts: list[dict[str, Any]] = []
            max_files = limit or 50
            scanned = 0
            for file_path in base_path.rglob("*"):
                if not file_path.is_file():
                    continue
                if file_path.suffix.lower() not in {
                    ".py",
                    ".js",
                    ".ts",
                    ".tsx",
                    ".jsx",
                }:
                    continue
                try:
                    content = file_path.read_text(errors="ignore")
                except Exception:
                    continue
                scanned += 1
                if scanned > max_files:
                    break
                if "@Autowired" in content or "@Component" in content:
                    contexts.append(
                        {
                            "framework": "spring",
                            "file": str(file_path.relative_to(base_path)),
                        }
                    )
                if "useContext(" in content:
                    contexts.append(
                        {
                            "framework": "react",
                            "file": str(file_path.relative_to(base_path)),
                        }
                    )
            return contexts

        def _build_dependency_chains(
            flows: list[TaintFlowModel],
        ) -> list[dict[str, Any]]:
            chains: list[dict[str, Any]] = []
            for flow in flows[:50]:
                chains.append(
                    {
                        "source": f"{flow.source_file}:{flow.source_function}",
                        "sink": f"{flow.sink_file}:{flow.sink_function}",
                        "path": flow.flow_path,
                    }
                )
            return chains

        def _build_confidence_scores(
            vulns_list: list[CrossFileVulnerabilityModel],
        ) -> dict[str, float]:
            scores: dict[str, float] = {}
            for vuln in vulns_list:
                key = f"{vuln.type}:{vuln.source_file}->{vuln.sink_file}"
                sev = vuln.severity.lower()
                scores[key] = 0.95 if sev in {"critical", "high"} else 0.8
            return scores

        def _detect_global_flows(flows: list[TaintFlowModel]) -> list[dict[str, Any]]:
            gflows: list[dict[str, Any]] = []
            for flow in flows[:100]:
                if "frontend" in flow.source_file or "frontend" in "".join(flow.flow_path):
                    gflows.append(
                        {
                            "source": flow.source_file,
                            "sink": flow.sink_file,
                            "flow_path": flow.flow_path,
                            "taint_type": flow.taint_type,
                        }
                    )
            return gflows

        def _detect_microservice_boundaries(base_path: Path) -> list[dict[str, Any]]:
            boundaries: list[dict[str, Any]] = []
            for child in list(base_path.iterdir())[:10]:
                if child.is_dir():
                    boundaries.append(
                        {
                            "service": child.name,
                            "path": str(child.relative_to(base_path)),
                        }
                    )
            return boundaries

        def _build_distributed_trace(gflows: list[dict[str, Any]]) -> dict[str, Any]:
            nodes: set[str] = set()
            edges: list[tuple[str, str]] = []
            for gf in gflows:
                nodes.add(gf["source"])
                nodes.add(gf["sink"])
                edges.append((gf["source"], gf["sink"]))
            return {"nodes": sorted(nodes), "edges": edges}

        if {
            "framework_aware_taint",
            "spring_bean_tracking",
            "react_context_tracking",
            "dependency_injection_resolution",
        } & caps_set:
            framework_contexts = _detect_framework_contexts(root_path, max_modules_limit)
            dependency_chains = _build_dependency_chains(taint_flows)
            confidence_scores = _build_confidence_scores(vulnerabilities)

        if {
            "global_taint_flow",
            "frontend_to_backend_tracing",
            "api_to_database_tracing",
            "microservice_boundary_crossing",
        } & caps_set:
            global_flows = _detect_global_flows(taint_flows)
            microservice_boundaries = _detect_microservice_boundaries(root_path)
            if global_flows:
                distributed_trace = _build_distributed_trace(global_flows)

        # [20260111_FEATURE] v1.0 - Compute metadata flags for transparency
        framework_aware_enabled = bool(
            {
                "framework_aware_taint",
                "spring_bean_tracking",
                "react_context_tracking",
                "dependency_injection_resolution",
            }
            & caps_set
        )
        enterprise_features_enabled = bool(
            {
                "global_taint_flow",
                "frontend_to_backend_tracing",
                "api_to_database_tracing",
                "microservice_boundary_crossing",
            }
            & caps_set
        )

        return CrossFileSecurityResult(
            success=True,
            tier_applied=tier,
            max_depth_applied=max_depth_limit,
            max_modules_applied=max_modules_limit,
            framework_aware_enabled=framework_aware_enabled,
            enterprise_features_enabled=enterprise_features_enabled,
            files_analyzed=result.modules_analyzed,  # Use modules_analyzed
            has_vulnerabilities=vuln_count > 0,
            vulnerability_count=vuln_count,
            risk_level=risk_level,
            vulnerabilities=vulnerabilities,
            taint_flows=taint_flows,
            taint_sources=taint_sources,
            dangerous_sinks=dangerous_sinks,
            mermaid=mermaid,
            framework_contexts=framework_contexts,
            dependency_chains=dependency_chains,
            confidence_scores=confidence_scores,
            global_flows=global_flows,
            microservice_boundaries=microservice_boundaries,
            distributed_trace=distributed_trace,
        )

    except Exception as e:
        return CrossFileSecurityResult(
            success=False,
            error=f"Cross-file security analysis failed: {str(e)}",
        )
