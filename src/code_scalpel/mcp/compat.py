"""Compatibility re-exports for legacy test/agent imports.

This module aggregates MCP tools, helper sync functions, and models so that
older code/tests that imported from ``code_scalpel.mcp.server`` can instead
import from ``code_scalpel.mcp.compat`` without pulling in the server module.

Import this module instead of ``code_scalpel.mcp.server`` to avoid loading the
full server and to keep ``server.py`` slim.
"""

from __future__ import annotations

from code_scalpel.mcp.helpers.analyze_helpers import _analyze_code_sync
from code_scalpel.mcp.helpers.context_helpers import (
    _crawl_project_sync,
    _get_file_context_sync,
    _get_symbol_references_sync,
)
from code_scalpel.mcp.helpers.extraction_helpers import _perform_extraction
from code_scalpel.mcp.helpers.graph_helpers import (
    _cross_file_security_scan_sync,
    _get_call_graph_sync,
    _get_cross_file_dependencies_sync,
    _get_project_map_sync,
)
from code_scalpel.mcp.helpers.security_helpers import (
    _get_current_tier as _get_current_tier_security,
)
from code_scalpel.mcp.helpers.security_helpers import (
    _scan_dependencies_sync,
    _security_scan_sync,
    _type_evaporation_scan_sync,
    _unified_sink_detect_sync,
)
from code_scalpel.mcp.helpers.symbolic_helpers import (
    _generate_tests_sync,
    _simulate_refactor_sync,
    _symbolic_execute_sync,
)
from code_scalpel.mcp.models.core import (
    AnalysisResult,
    SecurityResult,
    VulnerabilityInfo,
)
from code_scalpel.mcp.models.graph import (
    BoundaryAlertModel,
    CallContextModel,
    CallEdgeModel,
    CallGraphResultModel,
    CallNodeModel,
    CrossFileDependenciesResult,
    CrossFileSecurityResult,
    CrossFileVulnerabilityModel,
    ExtractedSymbolModel,
    GraphNeighborhoodResult,
    ImportNodeModel,
    ModuleInfo,
    NeighborhoodEdgeModel,
    NeighborhoodNodeModel,
    PackageInfo,
    ProjectMapResult,
    SymbolDefinitionModel,
    TaintFlowModel,
)
from code_scalpel.mcp.models.policy import (
    CodePolicyCheckResult,
    PathValidationResult,
    PolicyVerificationResult,
)
from code_scalpel.mcp.models.security import (
    DependencyInfo,
    DependencyScanResult,
    DependencyScanResultModel,
)
from code_scalpel.mcp.tools.analyze import analyze_code
from code_scalpel.mcp.tools.context import (
    crawl_project,
    get_file_context,
    get_symbol_references,
)
from code_scalpel.mcp.tools.extraction import extract_code, rename_symbol, update_symbol
from code_scalpel.mcp.tools.graph import (
    cross_file_security_scan,
    get_call_graph,
    get_cross_file_dependencies,
    get_graph_neighborhood,
    get_project_map,
)
from code_scalpel.mcp.tools.policy import (
    code_policy_check,
    validate_paths,
    verify_policy_integrity,
)
from code_scalpel.mcp.tools.security import (
    scan_dependencies,
    security_scan,
    type_evaporation_scan,
    unified_sink_detect,
)
from code_scalpel.mcp.tools.symbolic import (
    generate_unit_tests,
    simulate_refactor,
    symbolic_execute,
)

# Choose a single tier helper alias
_get_current_tier = _get_current_tier_security

__all__ = [
    # Tools
    "analyze_code",
    "security_scan",
    "unified_sink_detect",
    "type_evaporation_scan",
    "scan_dependencies",
    "symbolic_execute",
    "generate_unit_tests",
    "simulate_refactor",
    "extract_code",
    "rename_symbol",
    "update_symbol",
    "crawl_project",
    "get_file_context",
    "get_symbol_references",
    "get_call_graph",
    "get_graph_neighborhood",
    "get_project_map",
    "get_cross_file_dependencies",
    "cross_file_security_scan",
    "validate_paths",
    "verify_policy_integrity",
    "code_policy_check",
    # Helpers (sync)
    "_analyze_code_sync",
    "_security_scan_sync",
    "_unified_sink_detect_sync",
    "_type_evaporation_scan_sync",
    "_scan_dependencies_sync",
    "_symbolic_execute_sync",
    "_generate_tests_sync",
    "_simulate_refactor_sync",
    "_perform_extraction",
    "_crawl_project_sync",
    "_get_file_context_sync",
    "_get_symbol_references_sync",
    "_get_cross_file_dependencies_sync",
    "_get_project_map_sync",
    "_get_call_graph_sync",
    "_cross_file_security_scan_sync",
    "_get_current_tier",
    # Models
    "AnalysisResult",
    "SecurityResult",
    "VulnerabilityInfo",
    "CallGraphResultModel",
    "GraphNeighborhoodResult",
    "ModuleInfo",
    "PackageInfo",
    "ProjectMapResult",
    "DependencyInfo",
    "DependencyScanResult",
    "DependencyScanResultModel",
    "PolicyVerificationResult",
    "PathValidationResult",
    "CodePolicyCheckResult",
    "BoundaryAlertModel",
    "CallContextModel",
    "CallEdgeModel",
    "CallNodeModel",
    "CrossFileDependenciesResult",
    "CrossFileSecurityResult",
    "CrossFileVulnerabilityModel",
    "ExtractedSymbolModel",
    "ImportNodeModel",
    "NeighborhoodEdgeModel",
    "NeighborhoodNodeModel",
    "SymbolDefinitionModel",
    "TaintFlowModel",
]
