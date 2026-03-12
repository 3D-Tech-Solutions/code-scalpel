"""CLI-to-MCP Tool Bridge.

This module provides a bridge layer between CLI commands and MCP tool implementations,
allowing CLI users to access all MCP tools without requiring an MCP client.

Key responsibilities:
1. Convert CLI arguments to MCP tool parameters
2. Invoke MCP tools (async functions) from synchronous CLI context
3. Format ToolResponseEnvelope for terminal output
4. Handle tier-aware limits and errors with upgrade prompts

[20260205_FEATURE] CLI tool bridge for Phase 1 pilot implementation.
"""

from __future__ import annotations

import asyncio
import json
import sys
from typing import Any, Dict

from code_scalpel.mcp.contract import ToolResponseEnvelope, ToolError
from code_scalpel import __version__


def invoke_tool(tool_name: str, args: Dict[str, Any]) -> int:
    """Invoke an MCP tool from CLI context.

    This function:
    1. Dynamically imports the MCP tool function
    2. Converts CLI args to tool parameters
    3. Runs the async tool function synchronously
    4. Formats and prints the response
    5. Returns exit code

    Args:
        tool_name: MCP tool identifier (e.g., "extract_code", "get_call_graph")
        args: Tool arguments as dictionary

    Returns:
        Exit code: 0 for success, 1 for error

    Example:
        >>> invoke_tool("extract_code", {
        ...     "target_type": "function",
        ...     "target_name": "my_func",
        ...     "file_path": "src/main.py"
        ... })
        0
    """
    return invoke_tool_with_format(tool_name, args, "text")


def invoke_tool_with_format(
    tool_name: str, args: Dict[str, Any], output_format: str = "text"
) -> int:
    """Invoke an MCP tool from CLI context with specified output format.

    Args:
        tool_name: MCP tool identifier (e.g., "extract_code", "get_call_graph")
        args: Tool arguments as dictionary (should NOT contain output_format)
        output_format: Output format ("text", "json", "mermaid", etc.)

    Returns:
        Exit code: 0 for success, 1 for error
    """
    # Import tool function dynamically
    tool_func = _get_tool_function(tool_name)
    if tool_func is None:
        print(f"Error: Tool '{tool_name}' not found", file=sys.stderr)
        return 1

    # Run async tool in event loop
    try:
        response = asyncio.run(tool_func(**args))
    except Exception as e:
        print(f"Error invoking tool '{tool_name}': {e}", file=sys.stderr)
        return 1

    # Format and print response
    exit_code = _format_and_print_response(response, output_format)
    return exit_code


def _get_tool_function(tool_name: str):
    """Dynamically import and return MCP tool function.

    Args:
        tool_name: Tool identifier (e.g., "extract_code")

    Returns:
        Tool function or None if not found
    """
    # Map tool names to their module locations
    tool_module_map = {
        # Extraction tools
        "extract_code": "code_scalpel.mcp.tools.extraction",
        "rename_symbol": "code_scalpel.mcp.tools.extraction",
        "update_symbol": "code_scalpel.mcp.tools.extraction",
        "simulate_refactor": "code_scalpel.mcp.tools.symbolic",
        # Analysis tools
        "analyze_code": "code_scalpel.mcp.tools.analyze",
        "get_file_context": "code_scalpel.mcp.tools.context",
        "get_call_graph": "code_scalpel.mcp.tools.graph",
        "get_cross_file_dependencies": "code_scalpel.mcp.tools.graph",
        "get_symbol_references": "code_scalpel.mcp.tools.context",
        "get_graph_neighborhood": "code_scalpel.mcp.tools.graph",
        "get_project_map": "code_scalpel.mcp.tools.graph",
        "crawl_project": "code_scalpel.mcp.tools.context",
        # Security tools
        "security_scan": "code_scalpel.mcp.tools.security",
        "cross_file_security_scan": "code_scalpel.mcp.tools.graph",
        "type_evaporation_scan": "code_scalpel.mcp.tools.security",
        "symbolic_execute": "code_scalpel.mcp.tools.symbolic",
        "unified_sink_detect": "code_scalpel.mcp.tools.security",
        # Testing & generation
        "generate_unit_tests": "code_scalpel.mcp.tools.symbolic",
        "get_capabilities": "code_scalpel.mcp.tools.system",
        # Validation tools
        "validate_paths": "code_scalpel.mcp.tools.policy",
        "scan_dependencies": "code_scalpel.mcp.tools.security",
        "code_policy_check": "code_scalpel.mcp.tools.policy",
        # Policy tools
        "verify_policy_integrity": "code_scalpel.mcp.tools.policy",
    }

    module_name = tool_module_map.get(tool_name)
    if module_name is None:
        return None

    try:
        module = __import__(module_name, fromlist=[tool_name])
        return getattr(module, tool_name, None)
    except (ImportError, AttributeError):
        return None


def _format_and_print_response(
    response: ToolResponseEnvelope, output_format: str = "text"
) -> int:
    """Format MCP tool response for terminal output.

    Handles:
    - Success messages
    - Error messages with tier upgrade prompts
    - Structured data (JSON, Markdown, Mermaid)
    - Tier limit warnings

    Args:
        response: ToolResponseEnvelope from MCP tool
        output_format: Output format ("text", "json", "markdown")

    Returns:
        Exit code: 0 for success, 1 for error
    """
    # Handle JSON output format
    if output_format == "json":
        output = response.model_dump(exclude_none=True)
        print(json.dumps(output, indent=2))
        return 0 if response.data is not None else 1

    # Handle errors
    if response.error:
        _print_error(response.error, response.tier or "community")
        return 1

    # Handle success with warnings
    if response.warnings:
        for warning in response.warnings:
            print(f"Warning: {warning}", file=sys.stderr)

    # Print success message with tier info
    if response.data:
        _print_success_data(response.data, response.tier, response.duration_ms)
        return 0

    # Unexpected: no data and no error
    print("Error: Tool returned no data", file=sys.stderr)
    return 1


def _print_error(error: ToolError | str | Any, tier: str) -> None:
    """Print formatted error message with upgrade hints.

    Args:
        error: ToolError from response, or string error message
        tier: Current tier ("community", "pro", "enterprise")
    """
    # Handle string errors
    if isinstance(error, str):
        print(f"Error: {error}", file=sys.stderr)
        return

    # Handle ToolError objects
    if hasattr(error, "error"):
        error_msg = error.error
        error_code = getattr(error, "error_code", None)
        error_details = getattr(error, "error_details", None)
    else:
        # Fallback for other types
        error_msg = str(error)
        error_code = None
        error_details = None

    print(f"Error: {error_msg}", file=sys.stderr)

    if error_code:
        print(f"Error Code: {error_code}", file=sys.stderr)

        guidance_lines = _format_error_guidance(error_code, error_details)
        if guidance_lines:
            print("", file=sys.stderr)
            print("Oracle guidance:", file=sys.stderr)
            for line in guidance_lines:
                print(f"  - {line}", file=sys.stderr)

        # Print upgrade hint for tier-related errors
        if error_code == "upgrade_required":
            print("", file=sys.stderr)
            print("This feature requires a higher tier license.", file=sys.stderr)
            print(f"Current tier: {tier.upper()}", file=sys.stderr)

            if error_details:
                required_tier = error_details.get("required_tier", "pro")
                print(f"Required tier: {required_tier.upper()}", file=sys.stderr)

            print("", file=sys.stderr)
            print("For licensing information, visit:", file=sys.stderr)
            print(
                "  https://github.com/cyanheads/code-scalpel#licensing", file=sys.stderr
            )


def _format_error_guidance(
    error_code: str | None, error_details: dict[str, Any] | None
) -> list[str]:
    """Convert structured tool error details into CLI-friendly Oracle guidance."""
    if not error_code or not isinstance(error_details, dict):
        return []

    guidance: list[str] = []

    hint = error_details.get("hint")
    if isinstance(hint, str) and hint.strip():
        guidance.append(hint.strip())

    preferred_order = [
        "available_tiers",
        "available_tools",
        "supported_languages",
        "required_tier",
        "direction",
        "target_type",
        "manifest_source",
        "confidence_threshold",
        "complexity_threshold",
        "min_isolation_score",
        "timeout",
        "timeout_seconds",
        "max_depth",
        "max_paths",
        "max_modules",
        "max_files",
        "k",
        "paths_from",
        "paths_to",
    ]

    handled = {"hint"}
    for key in preferred_order:
        if key in error_details and key not in handled:
            value = error_details[key]
            if isinstance(value, (list, tuple, set)):
                rendered = ", ".join(str(item) for item in value)
            else:
                rendered = str(value)
            guidance.append(f"{key.replace('_', ' ')}: {rendered}")
            handled.add(key)

    for key, value in error_details.items():
        if key in handled:
            continue
        if isinstance(value, (list, tuple, set)):
            rendered = ", ".join(str(item) for item in value)
        else:
            rendered = str(value)
        guidance.append(f"{key.replace('_', ' ')}: {rendered}")

    return guidance


def _print_success_data(data: Any, tier: str | None, duration_ms: int | None) -> None:
    """Print formatted success data.

    Args:
        data: Result data from tool (dict or Pydantic model)
        tier: Tier used for execution
        duration_ms: Execution duration in milliseconds
    """
    # Convert Pydantic model to dict if needed
    if hasattr(data, "model_dump"):
        data_dict = data.model_dump(exclude_none=True)
    elif isinstance(data, dict):
        data_dict = data
    else:
        data_dict = {"result": str(data)}

    # Print main result based on tool type
    _print_tool_specific_output(data_dict)

    # Print metadata footer
    if tier or duration_ms:
        print("")
        print("-" * 60)
        if tier:
            print(f"Tier: {tier.upper()}")
        if duration_ms:
            print(f"Duration: {duration_ms}ms")
        print(f"Code Scalpel v{__version__}")


def _print_tool_specific_output(data: Dict[str, Any]) -> None:
    """Print tool-specific formatted output.

    Args:
        data: Tool result data as dictionary
    """
    # Capabilities - print tier summary or per-tool details
    if "capabilities" in data and "tier" in data:
        print(f"Code Scalpel Capabilities - {str(data['tier']).upper()} Tier")
        print(
            f"Available: {data.get('available_count', 0)}/{data.get('tool_count', 0)}"
        )
        return

    if "tool_name" in data and "tier_limits" in data:
        print(f"Tool: {data['tool_name']}")
        if data.get("short_description"):
            print(str(data["short_description"]).strip())
        return

    # Extract code tool - print extracted code
    if "full_code" in data:
        print(data["full_code"])
        if data.get("context_items"):
            print(f"\n# Included dependencies: {', '.join(data['context_items'])}")
        if data.get("warnings"):
            print("\n# Warnings:")
            for warning in data["warnings"]:
                print(f"#   - {warning}")
        return

    # Analysis tool - print structured analysis
    if "functions" in data or "classes" in data or "lines_of_code" in data:
        print("Analysis Summary")
        if "lines_of_code" in data:
            print(f"Lines of code: {data.get('lines_of_code', 0)}")
        if "complexity" in data:
            print(f"Complexity: {data.get('complexity', 0)}")
        if data.get("functions"):
            print(f"Functions ({len(data['functions'])}):")
            for func in data["functions"]:
                if isinstance(func, dict):
                    print(f"  - {func.get('name', 'unknown')}")
                else:
                    print(f"  - {func}")
        if data.get("classes"):
            print(f"Classes ({len(data['classes'])}):")
            for cls in data["classes"]:
                if isinstance(cls, dict):
                    print(f"  - {cls.get('name', 'unknown')}")
                else:
                    print(f"  - {cls}")
        return

    # Call graph - print Mermaid diagram or JSON
    if "mermaid_diagram" in data:
        print(data["mermaid_diagram"])
        return

    # Security scan - print vulnerabilities
    if "vulnerabilities" in data or "has_vulnerabilities" in data:
        vulns = data["vulnerabilities"]
        if not vulns:
            print("No vulnerabilities detected")
            return

        print(f"Vulnerabilities found: {len(vulns)}")
        for vuln in vulns:
            severity = vuln.get("severity", "unknown")
            vuln_type = vuln.get("type", "unknown")
            location = vuln.get("location", "unknown")
            print(f"  [{severity.upper()}] {vuln_type} at {location}")
        return

    # Rename/update result - print success message
    if "success" in data and "file_path" in data:
        if data["success"]:
            print(f"✓ Successfully modified {data['file_path']}")
            if data.get("backup_path"):
                print(f"  Backup created: {data['backup_path']}")
        else:
            print(f"✗ Failed to modify {data['file_path']}")
            if data.get("error"):
                print(f"  Error: {data['error']}")
        return

    # Default: print JSON
    print(json.dumps(data, indent=2))


def format_tool_response(response: ToolResponseEnvelope) -> str:
    """Format MCP tool response as string (for testing).

    Args:
        response: ToolResponseEnvelope to format

    Returns:
        Formatted response string
    """
    if response.error:
        return f"Error: {response.error.error}"

    if response.data:
        if hasattr(response.data, "model_dump"):
            return json.dumps(response.data.model_dump(exclude_none=True), indent=2)
        return json.dumps(response.data, indent=2)

    return "No data"
