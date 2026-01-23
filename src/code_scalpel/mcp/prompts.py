"""Code Scalpel intent-driven prompts.

[20260116_REFACTOR] Overhauled prompt registry to six canonical prompts.
"""

from __future__ import annotations

from mcp.server.fastmcp.prompts.base import Message as PromptMessage
from mcp.server.fastmcp.prompts.base import UserMessage

from code_scalpel.mcp.protocol import mcp


# [20260116_REFACTOR] Canonical prompt: deep_security_audit
@mcp.prompt(title="Deep Security Audit")
def deep_security_audit(path: str) -> list[PromptMessage]:
    """Guide a comprehensive, multi-tool security audit."""
    return [
        UserMessage(
            content=(
                "Perform a deep security audit of the project at: "
                f"{path}.\n\n"
                "Steps:\n"
                "1) Run security_scan to find direct vulnerabilities.\n"
                "2) If findings exist, run cross_file_security_scan to trace taint flow.\n"
                "3) Run unified_sink_detect to validate framework-specific sinks.\n"
                "4) Run scan_dependencies for CVEs.\n"
                "5) Summarize results by severity with fixes and exact locations."
            )
        )
    ]


# [20260116_REFACTOR] Canonical prompt: safe_refactor
@mcp.prompt(title="Refactor Safely")
def safe_refactor(file_path: str, symbol_name: str, goal: str) -> list[PromptMessage]:
    """Guide a safe refactor workflow with verification steps."""
    return [
        UserMessage(
            content=(
                "Safely refactor the symbol "
                f"{symbol_name} in {file_path}.\n\n"
                f"Goal: {goal}\n\n"
                "Steps:\n"
                "1) get_symbol_references for impact analysis.\n"
                "2) get_cross_file_dependencies to understand dependencies.\n"
                "3) extract_code for current implementation.\n"
                "4) generate_unit_tests for baseline behavior.\n"
                "5) simulate_refactor to verify no behavioral regressions.\n"
                "6) update_symbol with the final change only after checks pass."
            )
        )
    ]


# [20260116_REFACTOR] Canonical prompt: modernize_legacy
@mcp.prompt(title="Modernize Legacy Code")
def modernize_legacy(path: str) -> list[PromptMessage]:
    """Guide modernization of legacy codebases."""
    return [
        UserMessage(
            content=(
                "Modernize the legacy code at: "
                f"{path}.\n\n"
                "Steps:\n"
                "1) type_evaporation_scan for type boundary risks.\n"
                "2) analyze_code to locate high complexity and hotspots.\n"
                "3) security_scan to flag insecure patterns.\n"
                "4) scan_dependencies for outdated or vulnerable packages.\n"
                "5) Provide a prioritized modernization plan and example fixes."
            )
        )
    ]


# [20260116_REFACTOR] Canonical prompt: map_architecture
@mcp.prompt(title="Map Architecture")
def map_architecture(module_path: str) -> list[PromptMessage]:
    """Guide architectural mapping and dependency visualization."""
    return [
        UserMessage(
            content=(
                "Map the architecture of: "
                f"{module_path}.\n\n"
                "Steps:\n"
                "1) crawl_project for a high-level inventory.\n"
                "2) get_call_graph and get_graph_neighborhood for dependencies.\n"
                "3) get_cross_file_dependencies for critical paths.\n"
                "4) Summarize key components, entry points, and risks."
            )
        )
    ]


# [20260116_REFACTOR] Canonical prompt: verify_supply_chain
@mcp.prompt(title="Verify Supply Chain")
def verify_supply_chain(project_root: str) -> list[PromptMessage]:
    """Guide a software supply chain verification workflow."""
    return [
        UserMessage(
            content=(
                "Verify the software supply chain for: "
                f"{project_root}.\n\n"
                "Steps:\n"
                "1) scan_dependencies for CVEs and version risks.\n"
                "2) If relevant, run code_policy_check for policy violations.\n"
                "3) Summarize high-risk dependencies and remediation steps."
            )
        )
    ]


# [20260116_REFACTOR] Canonical prompt: explain_and_document
@mcp.prompt(title="Explain and Document")
def explain_and_document(target: str) -> list[PromptMessage]:
    """Guide explanation and documentation of code or architecture."""
    return [
        UserMessage(
            content=(
                "Explain and document the target: "
                f"{target}.\n\n"
                "Steps:\n"
                "1) analyze_code or extract_code as needed to understand structure.\n"
                "2) Provide a clear summary of behavior and responsibilities.\n"
                "3) Document key inputs/outputs, edge cases, and examples."
            )
        )
    ]
