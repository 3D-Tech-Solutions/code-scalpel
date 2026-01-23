"""Graph-related MCP result models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from code_scalpel import __version__


class CallContextModel(BaseModel):
    """Context information about where a call is made.

    [20260110_FEATURE] v3.3.0 - Call context metadata for security analysis.
    Knowing if a call is conditional or in a try block helps agents assess risk.
    """

    in_loop: bool = Field(default=False, description="Call is inside a loop")
    in_try_block: bool = Field(default=False, description="Call is inside a try block")
    in_conditional: bool = Field(default=False, description="Call is inside an if/else block")
    condition_summary: str | None = Field(default=None, description="Summary of condition, e.g., 'if user.is_admin'")
    in_async: bool = Field(default=False, description="Call is in an async function")
    in_except_handler: bool = Field(default=False, description="Call is in an except handler")


class CallNodeModel(BaseModel):
    """Node in the call graph representing a function."""

    name: str = Field(description="Function name")
    file: str = Field(description="File path (relative) or '<external>'")
    line: int = Field(description="Line number (0 if unknown)")
    end_line: int | None = Field(default=None, description="End line number")
    is_entry_point: bool = Field(default=False, description="Whether function is an entry point")
    # [20260110_FEATURE] v3.3.0 - source_uri for IDE click-through
    source_uri: str | None = Field(default=None, description="IDE-friendly URI: file:///path#L42")
    # [20251225_FEATURE] Enterprise metrics (best-effort)
    in_degree: int | None = Field(default=None, description="Inbound call count")
    out_degree: int | None = Field(default=None, description="Outbound call count")


class CallEdgeModel(BaseModel):
    """Edge in the call graph representing a function call."""

    caller: str = Field(description="Caller function (file:name)")
    callee: str = Field(description="Callee function (file:name or external name)")
    # [20260110_FEATURE] v3.3.0 - Confidence scoring for call edges
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Confidence: 1.0=static, 0.8=type_hint, 0.5=inferred",
    )
    inference_source: str = Field(
        default="static",
        description="How edge was inferred: static, type_hint, class_hierarchy, pattern_match",
    )
    call_line: int | None = Field(default=None, description="Line number of the call")
    # [20260110_FEATURE] v3.3.0 - Call context metadata
    context: CallContextModel | None = Field(default=None, description="Context where call is made")


class CallGraphResultModel(BaseModel):
    """Result of call graph analysis."""

    success: bool = Field(default=True, description="Whether analysis succeeded")
    server_version: str = Field(default=__version__, description="Code Scalpel version")
    nodes: list[CallNodeModel] = Field(default_factory=list, description="Functions in the graph")
    edges: list[CallEdgeModel] = Field(default_factory=list, description="Call relationships")
    entry_point: str | None = Field(default=None, description="Entry point used for filtering")
    depth_limit: int | None = Field(default=None, description="Depth limit used")
    mermaid: str = Field(default="", description="Mermaid diagram representation")
    circular_imports: list[list[str]] = Field(default_factory=list, description="Detected import cycles")
    # [20260110_FEATURE] v3.3.0 - Path query results
    paths: list[list[str]] = Field(
        default_factory=list,
        description="Paths between source and sink (if paths_from/paths_to specified)",
    )
    # [20260110_FEATURE] v3.3.0 - Subgraph focus mode
    focus_functions: list[str] | None = Field(default=None, description="Functions the subgraph is focused on")
    # [20251225_FEATURE] Neutral truncation metadata (tier limits)
    total_nodes: int | None = Field(default=None, description="Total nodes before truncation")
    total_edges: int | None = Field(default=None, description="Total edges before truncation")
    nodes_truncated: bool | None = Field(default=None, description="Whether nodes were truncated")
    edges_truncated: bool | None = Field(default=None, description="Whether edges were truncated")
    truncation_warning: str | None = Field(default=None, description="Neutral truncation note if applied")
    # [20251225_FEATURE] Enterprise extras (best-effort)
    hot_nodes: list[str] = Field(default_factory=list, description="High-degree nodes")
    dead_code_candidates: list[str] = Field(default_factory=list, description="Potentially unreferenced nodes")
    # [20260111_FEATURE] v1.0 validation - Output metadata for transparency
    tier_applied: str = Field(default="community", description="Tier used for analysis")
    max_depth_applied: int | None = Field(default=None, description="Max depth limit applied (None = unlimited)")
    max_nodes_applied: int | None = Field(default=None, description="Max nodes limit applied (None = unlimited)")
    advanced_resolution_enabled: bool = Field(default=False, description="Whether advanced call resolution was enabled")
    enterprise_metrics_enabled: bool = Field(default=False, description="Whether enterprise metrics were enabled")
    error: str | None = Field(default=None, description="Error message if failed")


class NeighborhoodNodeModel(BaseModel):
    """A node in the neighborhood subgraph."""

    id: str = Field(description="Node ID (language::module::type::name)")
    depth: int = Field(description="Distance from center node (0 = center)")
    metadata: dict = Field(default_factory=dict, description="Additional node metadata")
    # [20251226_FEATURE] Optional higher-tier metadata (best-effort)
    in_degree: int | None = Field(default=None, description="Inbound edge count")
    out_degree: int | None = Field(default=None, description="Outbound edge count")


class NeighborhoodEdgeModel(BaseModel):
    """An edge in the neighborhood subgraph."""

    from_id: str = Field(description="Source node ID")
    to_id: str = Field(description="Target node ID")
    edge_type: str = Field(description="Type of relationship")
    confidence: float = Field(description="Confidence score (0.0-1.0)")


class GraphNeighborhoodResult(BaseModel):
    """Result of k-hop neighborhood extraction."""

    success: bool = Field(description="Whether extraction succeeded")
    server_version: str = Field(default=__version__, description="Code Scalpel version")

    # Center node info
    center_node_id: str = Field(default="", description="ID of the center node")
    k: int = Field(default=0, description="Number of hops used")

    # Subgraph
    nodes: list[NeighborhoodNodeModel] = Field(default_factory=list, description="Nodes in the neighborhood")
    edges: list[NeighborhoodEdgeModel] = Field(default_factory=list, description="Edges in the neighborhood")
    total_nodes: int = Field(default=0, description="Number of nodes in subgraph")
    total_edges: int = Field(default=0, description="Number of edges in subgraph")

    # Truncation info
    max_depth_reached: int = Field(default=0, description="Maximum depth actually reached")
    truncated: bool = Field(default=False, description="Whether graph was truncated")
    truncation_warning: str | None = Field(default=None, description="Warning if truncated")

    # Mermaid diagram
    mermaid: str = Field(default="", description="Mermaid diagram of neighborhood")

    # [20251230_BUGFIX] Ensure tier-gated extras exist on the response model.
    # Some clients/tests rely on these fields being present even when empty.
    semantic_neighbors: list[str] = Field(
        default_factory=list,
        description="Pro: semantic neighbor node IDs (best-effort)",
    )
    logical_relationships: list[dict] = Field(
        default_factory=list,
        description="Pro: detected logical relationships (best-effort)",
    )

    query_supported: bool = Field(default=False, description="Enterprise: graph query language supported")
    traversal_rules_available: bool = Field(
        default=False,
        description="Enterprise: custom traversal rules supported",
    )
    path_constraints_supported: bool = Field(
        default=False,
        description="Enterprise: path constraint queries supported",
    )

    # [20251226_FEATURE] Optional higher-tier metadata
    hot_nodes: list[str] = Field(default_factory=list, description="High-degree nodes in the returned subgraph")

    error: str | None = Field(default=None, description="Error message if failed")


class ModuleInfo(BaseModel):
    """Information about a Python module/file."""

    path: str = Field(description="Relative file path")
    functions: list[str] = Field(default_factory=list, description="Function names in the module")
    classes: list[str] = Field(default_factory=list, description="Class names in the module")
    imports: list[str] = Field(default_factory=list, description="Import statements")
    entry_points: list[str] = Field(default_factory=list, description="Detected entry points")
    line_count: int = Field(default=0, description="Number of lines in file")
    complexity_score: int = Field(default=0, description="Cyclomatic complexity score")


class PackageInfo(BaseModel):
    """Information about a Python package (directory with __init__.py)."""

    name: str = Field(description="Package name")
    path: str = Field(description="Relative path to package")
    modules: list[str] = Field(default_factory=list, description="Module names in package")
    subpackages: list[str] = Field(default_factory=list, description="Subpackage names")


class ProjectMapResult(BaseModel):
    """Result of project map analysis."""

    # [20251226_BUGFIX] Ensure tier-gated extras are accessible when schema differs
    try:
        from pydantic import ConfigDict as _ConfigDict  # type: ignore

        model_config = _ConfigDict(extra="allow")
    except Exception:

        class Config:  # type: ignore
            extra = "allow"

    success: bool = Field(default=True, description="Whether analysis succeeded")
    server_version: str = Field(default=__version__, description="Code Scalpel version")
    project_root: str = Field(description="Absolute path to project root")
    total_files: int = Field(default=0, description="Total Python files")
    total_lines: int = Field(default=0, description="Total lines of code")
    languages: dict[str, int] = Field(default_factory=dict, description="Language breakdown by file count")
    packages: list[PackageInfo] = Field(default_factory=list, description="Detected packages")
    modules: list[ModuleInfo] = Field(default_factory=list, description="Modules analyzed (max 50 in Mermaid diagram)")
    entry_points: list[str] = Field(default_factory=list, description="All detected entry points")
    circular_imports: list[list[str]] = Field(default_factory=list, description="Circular import cycles")
    complexity_hotspots: list[str] = Field(default_factory=list, description="Files with high complexity")
    mermaid: str = Field(default="", description="Mermaid diagram of package structure")

    # [20260111_FEATURE] Output metadata fields for tier transparency
    tier_applied: str = Field(
        default="community",
        description="The tier that was applied to this request (community, pro, enterprise)",
    )
    max_files_applied: int | None = Field(
        default=None,
        description="The max_files limit applied (100 for Community, 1000 for Pro, None for Enterprise)",
    )
    max_modules_applied: int | None = Field(
        default=None,
        description="The max_modules limit applied (50 for Community, 200 for Pro, 1000 for Enterprise)",
    )
    pro_features_enabled: bool = Field(
        default=False,
        description="Whether Pro tier features were enabled (coupling_metrics, architectural_layers, etc.)",
    )
    enterprise_features_enabled: bool = Field(
        default=False,
        description="Whether Enterprise tier features were enabled (city_map, force_graph, etc.)",
    )

    # [20251226_BUGFIX] Provide tier-gated attributes via properties when model schema differs
    def _get_extra_value(self, name: str):  # type: ignore[override]

        try:
            extra = object.__getattribute__(self, "__pydantic_extra__")
            if extra:
                return extra.get(name)
        except Exception:
            return None
        return None

    @property
    def module_relationships(self):  # type: ignore[override]
        return self._get_extra_value("module_relationships")

    @property
    def architectural_layers(self):  # type: ignore[override]
        return self._get_extra_value("architectural_layers")

    @property
    def coupling_metrics(self):  # type: ignore[override]
        return self._get_extra_value("coupling_metrics")

    @property
    def dependency_diagram(self):  # type: ignore[override]
        return self._get_extra_value("dependency_diagram")

    @property
    def city_map_data(self):  # type: ignore[override]
        return self._get_extra_value("city_map_data")

    @property
    def force_graph(self):  # type: ignore[override]
        return self._get_extra_value("force_graph")

    @property
    def churn_heatmap(self):  # type: ignore[override]
        return self._get_extra_value("churn_heatmap")

    @property
    def bug_hotspots(self):  # type: ignore[override]
        return self._get_extra_value("bug_hotspots")

    @property
    def git_ownership(self):  # type: ignore[override]
        return self._get_extra_value("git_ownership")

    # [20251231_FEATURE] v3.3.1 - Property getters for new Enterprise fields
    @property
    def multi_repo_summary(self):  # type: ignore[override]
        return self._get_extra_value("multi_repo_summary")

    @property
    def historical_trends(self):  # type: ignore[override]
        return self._get_extra_value("historical_trends")

    @property
    def custom_metrics(self):  # type: ignore[override]
        return self._get_extra_value("custom_metrics")

    @property
    def compliance_overlay(self):  # type: ignore[override]
        return self._get_extra_value("compliance_overlay")

    # [20251226_FEATURE] Tier-aware rich metadata fields
    # [20260102_REFACTOR] Pydantic Fields intentionally mirror property names; silence F811 redefinition.
    module_relationships: list[dict[str, Any]] | None = Field(  # noqa: F811
        default=None,
        description="Import relationship edges between modules (Pro/Enterprise)",
    )
    architectural_layers: list[dict[str, str]] | None = Field(  # noqa: F811
        default=None,
        description="Layer detection results per module (Pro/Enterprise)",
    )
    coupling_metrics: list[dict[str, Any]] | None = Field(  # noqa: F811
        default=None,
        description="Coupling metrics (afferent/efferent/instability) per module",
    )
    dependency_diagram: str | None = Field(  # noqa: F811
        default=None,
        description="Mermaid diagram of dependency graph when enabled",
    )
    city_map_data: dict[str, Any] | None = Field(  # noqa: F811
        default=None,
        description="Abstract city-map payload for Enterprise visualization",
    )
    force_graph: dict[str, Any] | None = Field(  # noqa: F811
        default=None,
        description="Force-directed graph payload for Enterprise",
    )
    churn_heatmap: list[dict[str, Any]] | None = Field(  # noqa: F811
        default=None,
        description="Code churn summary for Enterprise",
    )
    bug_hotspots: list[dict[str, Any]] | None = Field(  # noqa: F811
        default=None,
        description="Bug hotspot heuristics for Enterprise",
    )
    git_ownership: list[dict[str, Any]] | None = Field(  # noqa: F811
        default=None,
        description="Lightweight ownership attribution (Pro/Enterprise)",
    )
    # [20251231_FEATURE] v3.3.1 - New Enterprise fields per roadmap v1.0
    multi_repo_summary: dict[str, Any] | None = Field(  # noqa: F811
        default=None,
        description="Multi-repository aggregation summary (Enterprise)",
    )
    historical_trends: list[dict[str, Any]] | None = Field(  # noqa: F811
        default=None,
        description="Historical architecture trends from git log analysis (Enterprise)",
    )
    custom_metrics: dict[str, Any] | None = Field(  # noqa: F811
        default=None,
        description="Custom map metrics defined in configuration (Enterprise)",
    )
    compliance_overlay: dict[str, Any] | None = Field(  # noqa: F811
        default=None,
        description="Compliance/architecture rule violations overlay (Enterprise)",
    )
    # [20251220_FEATURE] v3.0.5 - Truncation communication
    modules_in_diagram: int = Field(default=0, description="Number of modules shown in Mermaid diagram")
    diagram_truncated: bool = Field(default=False, description="Whether Mermaid diagram was truncated")
    error: str | None = Field(default=None, description="Error message if failed")


class ImportNodeModel(BaseModel):
    """Information about an import in the import graph."""

    module: str = Field(description="Module name (e.g., 'os', 'mypackage.utils')")
    import_type: str = Field(description="Import type: 'direct', 'from', or 'star'")
    names: list[str] = Field(default_factory=list, description="Imported names (for 'from' imports)")
    alias: str | None = Field(default=None, description="Alias if import uses 'as'")
    line: int = Field(default=0, description="Line number of import")


class SymbolDefinitionModel(BaseModel):
    """Information about a symbol defined in a file."""

    name: str = Field(description="Symbol name")
    file: str = Field(description="File where symbol is defined (relative path)")
    line: int = Field(default=0, description="Line number of definition")
    symbol_type: str = Field(description="Type: 'function', 'class', or 'variable'")
    is_exported: bool = Field(default=False, description="Whether symbol is in __all__")


class ExtractedSymbolModel(BaseModel):
    """An extracted symbol with its code and dependencies."""

    name: str = Field(description="Symbol name")
    code: str = Field(description="Full source code of the symbol")
    file: str = Field(description="Source file (relative path)")
    line_start: int = Field(default=0, description="Starting line number")
    line_end: int = Field(default=0, description="Ending line number")
    dependencies: list[str] = Field(default_factory=list, description="Names of symbols this depends on")
    # [20251216_FEATURE] v2.5.0 - Confidence decay for deep dependency chains
    depth: int = Field(default=0, description="Depth from original target (0 = target)")
    confidence: float = Field(
        default=1.0,
        description="Confidence score with decay applied (0.0-1.0). Formula: C_base × 0.9^depth",
    )
    low_confidence: bool = Field(default=False, description="True if confidence is below threshold (0.5)")


class AliasResolutionModel(BaseModel):
    """Import alias resolution details (Pro tier)."""

    alias: str = Field(description="Alias name as used in the importing module")
    original_module: str = Field(description="Module where the symbol originates (pre-alias)")
    original_name: str | None = Field(default=None, description="Original symbol name before aliasing")
    file: str | None = Field(default=None, description="File containing the aliasing import (relative)")
    line: int | None = Field(default=None, description="Line number of the import")


class WildcardExpansionModel(BaseModel):
    """Wildcard import expansion details (Pro tier)."""

    from_module: str = Field(description="Module imported with a wildcard")
    expanded_symbols: list[str] = Field(
        default_factory=list,
        description="Symbols expanded from __all__ or public definitions",
    )


class ReexportChainModel(BaseModel):
    """Re-export chain information (Pro tier)."""

    symbol: str = Field(description="Symbol name exposed by re-export")
    apparent_source: str = Field(description="Module that appears to export the symbol")
    actual_source: str = Field(description="Module where the symbol truly originates")


class ChainedAliasResolutionModel(BaseModel):
    """Multi-hop alias resolution details (Pro tier)."""

    symbol: str = Field(description="Alias as referenced in the target module")
    chain: list[str] = Field(
        default_factory=list,
        description="Modules traversed while resolving the alias chain",
    )
    resolved_module: str | None = Field(default=None, description="Module where the symbol ultimately resides")
    resolved_name: str | None = Field(default=None, description="Original symbol name after resolving aliases")


class CouplingViolationModel(BaseModel):
    """Coupling metric violation (Enterprise tier)."""

    metric: str = Field(description="Metric name, e.g., fan_in/fan_out/dependency_depth")
    value: int | float = Field(description="Observed metric value")
    limit: int | float = Field(description="Configured limit for the metric")
    module: str | None = Field(default=None, description="Module evaluated for coupling")
    severity: str | None = Field(default=None, description="Severity level for violation")
    description: str | None = Field(default=None, description="Human-readable summary")


class ArchitecturalViolationModel(BaseModel):
    """Architectural rule violation (Enterprise tier)."""

    type: str = Field(description="Rule name/type that was violated")
    severity: str = Field(description="Severity classification")
    source: str | None = Field(default=None, description="Source module/file")
    target: str | None = Field(default=None, description="Target module/file")
    from_layer: str | None = Field(default=None, description="Layer of source module")
    to_layer: str | None = Field(default=None, description="Layer of target module")
    description: str | None = Field(default=None, description="Violation description")
    recommendation: str | None = Field(default=None, description="Suggested remediation for the violation")


class BoundaryAlertModel(BaseModel):
    """Layer boundary alert (Enterprise tier)."""

    rule: str | None = Field(default=None, description="Rule producing the alert")
    from_layer: str | None = Field(default=None, description="Origin layer")
    to_layer: str | None = Field(default=None, description="Destination layer")
    source: str | None = Field(default=None, description="Source module/file")
    target: str | None = Field(default=None, description="Target module/file")


class CrossFileDependenciesResult(BaseModel):
    """Result of cross-file dependency analysis."""

    success: bool = Field(description="Whether analysis succeeded")
    server_version: str = Field(default=__version__, description="Code Scalpel version")

    # Target symbol info
    target_name: str = Field(default="", description="Name of the analyzed symbol")
    target_file: str = Field(default="", description="File containing the target symbol")

    # Dependency info
    extracted_symbols: list[ExtractedSymbolModel] = Field(
        default_factory=list,
        description="All symbols extracted (target + dependencies)",
    )
    total_dependencies: int = Field(default=0, description="Number of dependencies resolved")
    unresolved_imports: list[str] = Field(
        default_factory=list, description="External imports that could not be resolved"
    )

    # Import graph info
    import_graph: dict[str, list[str]] = Field(
        default_factory=dict, description="Import graph: file -> list of imported files"
    )
    circular_imports: list[list[str]] = Field(default_factory=list, description="Detected circular import cycles")

    # Combined code for AI consumption
    combined_code: str = Field(default="", description="All extracted code combined, ready for AI consumption")
    token_estimate: int = Field(default=0, description="Estimated token count for combined code")

    # [20251226_FEATURE] Tier-aware metadata
    transitive_depth: int = Field(
        default=0,
        description="Max transitive depth actually analyzed after tier limits",
    )
    # Pro tier dependency insights
    alias_resolutions: list[AliasResolutionModel] = Field(
        default_factory=list,
        description="Resolved import aliases with original modules (Pro)",
    )
    wildcard_expansions: list[WildcardExpansionModel] = Field(
        default_factory=list,
        description="Expanded symbols from wildcard imports (Pro)",
    )
    reexport_chains: list[ReexportChainModel] = Field(
        default_factory=list,
        description="Re-export chains tracing apparent vs actual sources (Pro)",
    )
    chained_alias_resolutions: list[ChainedAliasResolutionModel] = Field(
        default_factory=list,
        description="Multi-hop alias resolution chains (Pro)",
    )

    coupling_score: float | None = Field(
        default=None,
        description="Coupling heuristic (dependencies / unique files) when enabled",
    )
    coupling_violations: list[CouplingViolationModel] = Field(
        default_factory=list,
        description="Coupling metrics exceeding configured limits (Enterprise)",
    )
    dependency_chains: list[list[str]] = Field(
        default_factory=list,
        description="Dependency chains traced when transitive mapping is enabled",
    )
    boundary_violations: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Architectural boundary violations detected (Enterprise)",
    )
    layer_violations: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Layering issues detected (Enterprise)",
    )
    architectural_alerts: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Aggregated alerts for detected violations",
    )
    architectural_violations: list[ArchitecturalViolationModel] = Field(
        default_factory=list,
        description="Architectural rule engine violations (Enterprise)",
    )
    boundary_alerts: list[BoundaryAlertModel] = Field(
        default_factory=list,
        description="Layer boundary alerts with from/to layer context (Enterprise)",
    )
    layer_mapping: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Layer name to file list mapping from architecture rules",
    )
    rules_applied: list[str] = Field(
        default_factory=list,
        description="Architectural rules evaluated by the rule engine",
    )
    architectural_rules_applied: list[str] = Field(
        default_factory=list,
        description="Explicit list of architectural rules applied (Enterprise)",
    )
    exempted_files: list[str] = Field(
        default_factory=list,
        description="Files/modules exempted from rule checks via configuration",
    )

    files_scanned: int = Field(
        default=0,
        description="Unique files observed before truncation",
    )
    files_truncated: int = Field(
        default=0,
        description="Number of files dropped due to tier limits",
    )
    truncation_warning: str | None = Field(
        default=None,
        description="Warning describing any applied truncation",
    )
    truncated: bool = Field(
        default=False,
        description="True if analysis truncated files due to limits",
    )
    files_analyzed: int = Field(
        default=0,
        description="Count of files analyzed (post-truncation, effective)",
    )
    max_depth_reached: int = Field(
        default=0,
        description="Actual maximum dependency depth reached during traversal",
    )

    # Mermaid diagram
    mermaid: str = Field(default="", description="Mermaid diagram of import relationships")

    # [20251216_FEATURE] v2.5.0 - Confidence decay tracking
    confidence_decay_factor: float = Field(
        default=0.9,
        description="Decay factor used: C_effective = C_base × decay_factor^depth",
    )
    low_confidence_count: int = Field(default=0, description="Number of symbols below confidence threshold (0.5)")
    low_confidence_warning: str | None = Field(
        default=None, description="Warning message if low-confidence symbols detected"
    )

    error: str | None = Field(default=None, description="Error message if failed")


class TaintFlowModel(BaseModel):
    """Model for a taint flow across files."""

    source_function: str = Field(description="Function where taint originates")
    source_file: str = Field(description="File containing taint source")
    source_line: int = Field(default=0, description="Line number of taint source")
    sink_function: str = Field(description="Function where taint reaches sink")
    sink_file: str = Field(description="File containing sink")
    sink_line: int = Field(default=0, description="Line number of sink")
    flow_path: list[str] = Field(default_factory=list, description="Path: file:function -> file:function")
    taint_type: str = Field(description="Type of taint source (e.g., 'request_input')")


class CrossFileVulnerabilityModel(BaseModel):
    """Model for a cross-file vulnerability."""

    type: str = Field(description="Vulnerability type (e.g., 'SQL Injection')")
    cwe: str = Field(description="CWE identifier")
    severity: str = Field(description="Severity: low, medium, high, critical")
    source_file: str = Field(description="File where taint originates")
    sink_file: str = Field(description="File where vulnerability manifests")
    description: str = Field(description="Human-readable description")
    flow: TaintFlowModel = Field(description="The taint flow that causes this vulnerability")


class CrossFileSecurityResult(BaseModel):
    """Result of cross-file security analysis."""

    success: bool = Field(description="Whether analysis succeeded")
    server_version: str = Field(default=__version__, description="Code Scalpel version")

    # [20260111_FEATURE] v1.0 - Output metadata fields for transparency
    tier_applied: str = Field(
        default="community",
        description="The tier used for analysis (community, pro, enterprise)",
    )
    max_depth_applied: int | None = Field(
        default=None,
        description="The max depth limit applied (None = unlimited for Enterprise)",
    )
    max_modules_applied: int | None = Field(
        default=None,
        description="The max modules limit applied (None = unlimited for Enterprise)",
    )
    framework_aware_enabled: bool = Field(
        default=False,
        description="Whether framework-aware taint tracking was enabled (Pro+)",
    )
    enterprise_features_enabled: bool = Field(
        default=False,
        description="Whether enterprise features were enabled (global flows, microservice boundaries)",
    )

    # Summary
    files_analyzed: int = Field(default=0, description="Number of files analyzed")
    has_vulnerabilities: bool = Field(default=False, description="Whether vulnerabilities were found")
    vulnerability_count: int = Field(default=0, description="Total vulnerabilities found")
    risk_level: str = Field(default="low", description="Overall risk level")

    # Detailed findings
    vulnerabilities: list[CrossFileVulnerabilityModel] = Field(
        default_factory=list, description="Cross-file vulnerabilities found"
    )
    taint_flows: list[TaintFlowModel] = Field(default_factory=list, description="All taint flows detected")

    # Entry points and sinks
    taint_sources: list[str] = Field(default_factory=list, description="Functions containing taint sources")
    dangerous_sinks: list[str] = Field(default_factory=list, description="Functions containing dangerous sinks")

    # [20251226_FEATURE] Tier-aware optional outputs for Pro/Enterprise
    framework_contexts: list[dict[str, Any]] | None = Field(
        default=None,
        description="Framework-aware context detection (Spring Beans, React Context)",
    )
    dependency_chains: list[dict[str, Any]] | None = Field(
        default=None,
        description="Inter-file dependency chains contributing to taint flows",
    )
    confidence_scores: dict[str, float] | None = Field(default=None, description="Heuristic confidence scores per flow")
    global_flows: list[dict[str, Any]] | None = Field(
        default=None,
        description="Global taint flows across service boundaries (Enterprise)",
    )
    microservice_boundaries: list[dict[str, Any]] | None = Field(
        default=None,
        description="Detected service/domain boundaries (Enterprise)",
    )
    distributed_trace: dict[str, Any] | None = Field(
        default=None, description="Distributed trace representation for flows"
    )

    # Visualization
    mermaid: str = Field(default="", description="Mermaid diagram of taint flows")

    error: str | None = Field(default=None, description="Error message if failed")
