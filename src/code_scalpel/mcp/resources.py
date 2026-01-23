"""MCP resource handlers."""

from __future__ import annotations

import asyncio
from importlib import import_module
from pathlib import Path
from typing import TYPE_CHECKING

from code_scalpel import __version__
from code_scalpel.mcp.protocol import mcp

if TYPE_CHECKING:
    from code_scalpel.mcp.archive.server import ContextualExtractionResult, TreeNodeDict


def _server():
    return import_module("code_scalpel.mcp.server")


def _run_in_thread(func, *args, **kwargs):
    import asyncio

    return asyncio.to_thread(func, *args, **kwargs)


# ============================================================================
# RESOURCES
# ============================================================================


@mcp.resource("scalpel://project/call-graph")
async def get_project_call_graph() -> str:
    """Return the project-wide call graph as JSON."""
    import json

    from code_scalpel.mcp.helpers.graph_helpers import _get_call_graph_sync

    server = _server()
    result = await _run_in_thread(
        _get_call_graph_sync,
        str(server.PROJECT_ROOT),
        None,
        25,
        True,
        None,
        False,
        False,
        None,
        None,
        None,
    )
    return (
        json.dumps(result.model_dump(), indent=2)
        if result.success
        else json.dumps({"success": False, "error": result.error})
    )


@mcp.resource("scalpel://project/dependencies")
async def get_project_dependencies() -> str:
    """Return detected project dependencies as JSON."""
    import json

    from code_scalpel.ast_tools.dependency_parser import DependencyParser

    server = _server()
    deps = await _run_in_thread(DependencyParser(str(server.PROJECT_ROOT)).get_dependencies)
    return json.dumps(deps, indent=2)


@mcp.resource("scalpel://project/structure")
async def get_project_structure() -> str:
    """Return the project directory structure as JSON."""
    import json

    def build_tree(path: Path) -> TreeNodeDict:
        tree: TreeNodeDict = {"name": path.name, "type": "directory", "children": []}
        try:
            items = sorted(path.iterdir(), key=lambda p: (not p.is_dir(), p.name))
            for item in items:
                if item.name.startswith(".") or item.name in [
                    "__pycache__",
                    "venv",
                    "node_modules",
                    "dist",
                    "build",
                ]:
                    continue

                if item.is_dir():
                    tree["children"].append(build_tree(item))
                else:
                    tree["children"].append({"name": item.name, "type": "file"})
        except PermissionError:
            pass
        return tree

    server = _server()
    tree = await _run_in_thread(build_tree, server.PROJECT_ROOT)
    return json.dumps(tree, indent=2)


@mcp.resource("scalpel://version")
def get_version() -> str:
    """Get Code Scalpel version information."""
    return f"""Code Scalpel v{__version__}

A precision toolkit for AI-driven code analysis.

Features:
- AST Analysis: Parse and analyze code structure
- Security Scanning: Taint-based vulnerability detection
- Symbolic Execution: Path exploration with Z3 solver

Supported Languages:
- Python (full support)
- JavaScript/TypeScript (planned v0.4.0)
"""


@mcp.resource("scalpel://health")
def get_health() -> str:
    """
    Health check endpoint for Docker and orchestration systems.

    [20251215_FEATURE] v2.0.0 - Added health endpoint for Docker health checks.

    Returns immediately with server status. Use this instead of SSE endpoint
    for health checks as SSE connections stay open indefinitely.

    Returns:
        JSON string with health status
    """
    import json

    server = _server()
    return json.dumps(
        {
            "status": "healthy",
            "version": __version__,
            "project_root": str(server.PROJECT_ROOT),
        }
    )


@mcp.resource("scalpel://capabilities")
def get_capabilities() -> str:
    """Get information about Code Scalpel's capabilities."""
    return """# Code Scalpel Capabilities

## Tools

### analyze_code
Parses Python code and extracts:
- Function definitions (sync and async)
- Class definitions
- Import statements
- Cyclomatic complexity
- Lines of code

### security_scan
Detects vulnerabilities:
- SQL Injection (CWE-89)
- Cross-Site Scripting (CWE-79)
- Command Injection (CWE-78)
- Path Traversal (CWE-22)
- Code Injection (CWE-94)

Uses taint analysis to track data flow from sources to sinks.

### symbolic_execute
Explores execution paths:
- Treats function arguments as symbolic
- Uses Z3 SMT solver for constraint solving
- Identifies reachable/unreachable paths
- Reports path conditions

## Security Notes
- Code is PARSED, never executed
- Maximum code size: 100KB
- No filesystem access from analyzed code
- No network access from analyzed code
"""


# ============================================================================
# RESOURCE TEMPLATES - Dynamic URI-based Context
# ============================================================================


@mcp.resource("scalpel://file/{path}")
def get_file_resource(path: str) -> str:
    """
    Read file contents by path (Resource Template).

    [20251215_FEATURE] v2.0.0 - Dynamic file access via URI template.

    This resource template allows clients to construct URIs dynamically
    to access any file within the allowed roots.
    """
    from code_scalpel.mcp.path_resolver import resolve_path

    server = _server()

    try:
        resolved = resolve_path(path, str(server.PROJECT_ROOT))
        file_path = Path(resolved)

        # Security check
        server._validate_path_security(file_path)

        return file_path.read_text(encoding="utf-8")
    except FileNotFoundError as e:
        return f"Error: {e}"
    except PermissionError as e:
        return f"Error: {e}"
    except Exception as e:
        return f"Error reading file: {e}"


@mcp.resource("scalpel://analysis/{path}")
async def get_analysis_resource(path: str) -> str:
    """Get code analysis for a file by path."""
    import json

    from code_scalpel.mcp.path_resolver import resolve_path

    server = _server()

    try:
        resolved = resolve_path(path, str(server.PROJECT_ROOT))
        file_path = Path(resolved)

        server._validate_path_security(file_path)

        code = await _run_in_thread(file_path.read_text, encoding="utf-8")

        analysis, security = await asyncio.gather(
            _run_in_thread(server._analyze_code_sync, code, "python"),
            _run_in_thread(server._security_scan_sync, code),
        )

        return json.dumps(
            {
                "file": str(file_path),
                "analysis": analysis.model_dump(),
                "security_summary": {
                    "has_vulnerabilities": security.has_vulnerabilities,
                    "vulnerability_count": security.vulnerability_count,
                    "risk_level": security.risk_level,
                },
            },
            indent=2,
        )
    except FileNotFoundError as e:
        return json.dumps({"error": str(e)})
    except PermissionError as e:
        return json.dumps({"error": str(e)})
    except Exception as e:
        return json.dumps({"error": f"Analysis failed: {e}"})


# [20251215_BUGFIX] Provide synchronous extraction helper for URI templates using SurgicalExtractor.
def _extract_code_sync(
    target_type: str,
    target_name: str,
    file_path: str | None,
    code: str | None = None,
    include_context: bool = True,
    include_token_estimate: bool = True,
) -> ContextualExtractionResult:
    # [20251228_BUGFIX] Avoid deprecated shim imports.
    from code_scalpel.surgery.surgical_extractor import SurgicalExtractor

    server = _server()

    if not file_path and not code:
        return server._extraction_error(target_name, "Must provide either 'file_path' or 'code' argument")

    extractor = SurgicalExtractor.from_file(file_path) if file_path is not None else SurgicalExtractor(code or "")

    context = None
    if target_type == "class":
        target = extractor.get_class(target_name)
        if include_context:
            context = extractor.get_class_with_context(target_name)
    elif target_type == "method":
        if "." not in target_name:
            return server._extraction_error(target_name, "Method targets must use Class.method format")
        class_name, method_name = target_name.split(".", 1)
        target = extractor.get_method(class_name, method_name)
        if include_context:
            # [20251220_FEATURE] Use get_method_with_context for token-efficient extraction
            # Falls back to class context if method-level context unavailable
            if hasattr(extractor, "get_method_with_context"):
                context = extractor.get_method_with_context(class_name, method_name)
            else:
                context = extractor.get_class_with_context(class_name)
    else:
        target = extractor.get_function(target_name)
        if include_context:
            context = extractor.get_function_with_context(target_name)

    if not target.success:
        return server._extraction_error(target_name, target.error or "Extraction failed")

    context_code = context.context_code if context else ""
    context_items = context.context_items if context else (target.dependencies or [])
    full_code = context.full_code if context else target.code
    total_lines = (
        context.total_lines
        if context
        else (
            target.line_end - target.line_start + 1
            if target.line_end and target.line_start
            else max(1, full_code.count("\n") + 1)
        )
    )
    token_estimate = context.token_estimate if context and include_token_estimate else 0

    # [20260111_FEATURE] Get tier for metadata (sync helper uses default tier)
    tier = server._get_current_tier()
    from code_scalpel.licensing.config_loader import get_tool_limits

    limits = get_tool_limits("extract_code", tier)
    max_depth_limit = limits.get("max_depth")

    return server.ContextualExtractionResult(
        success=True,
        server_version=__version__,
        target_name=target_name,
        target_code=target.code,
        context_code=context_code,
        full_code=full_code,
        context_items=context_items,
        total_lines=total_lines,
        line_start=target.line_start,
        line_end=target.line_end,
        token_estimate=token_estimate,
        error=None,
        # [20260111_FEATURE] Output metadata for transparency
        tier_applied=tier,
        language_detected="python",  # _extract_code_sync is Python-only
        cross_file_deps_enabled=include_context,
        max_depth_applied=max_depth_limit,
    )


@mcp.resource("scalpel://symbol/{file_path}/{symbol_name}")
def get_symbol_resource(file_path: str, symbol_name: str) -> str:
    """
    Extract a specific symbol (function/class) from a file (Resource Template).

    [20251215_FEATURE] v2.0.0 - Surgical symbol extraction via URI template.
    """
    import ast
    import json

    from code_scalpel.mcp.path_resolver import resolve_path

    server = _server()

    try:
        resolved = resolve_path(file_path, str(server.PROJECT_ROOT))
        path = Path(resolved)

        # Security check
        server._validate_path_security(path)

        # Determine target type
        if "." in symbol_name:
            target_type = "method"
        else:
            # Try to detect from code
            code = path.read_text(encoding="utf-8")
            tree = ast.parse(code)

            target_type = "function"
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef) and node.name == symbol_name:
                    target_type = "class"
                    break

        # Use extraction logic
        result = _extract_code_sync(
            target_type=target_type,
            target_name=symbol_name,
            file_path=str(path),
            include_context=True,
            include_token_estimate=True,
        )

        return json.dumps(result.model_dump(), indent=2)
    except FileNotFoundError as e:
        return json.dumps({"error": str(e)})
    except PermissionError as e:
        return json.dumps({"error": str(e)})
    except Exception as e:
        return json.dumps({"error": f"Extraction failed: {e}"})


@mcp.resource("code:///{language}/{module}/{symbol}")
async def get_code_resource(language: str, module: str, symbol: str) -> str:
    """
    Access code elements via parameterized URI (Resource Template).

    [20251216_FEATURE] v2.0.2 - Universal code access via code:/// URIs.
    """
    import json

    from code_scalpel.mcp.module_resolver import get_mime_type, resolve_module_path

    server = _server()

    try:
        # Resolve module to file path
        file_path = resolve_module_path(language, module, server.PROJECT_ROOT)

        if file_path is None:
            return json.dumps(
                {
                    "error": f"Module '{module}' not found for language '{language}'",
                    "language": language,
                    "module": module,
                    "symbol": symbol,
                }
            )

        # Security check
        server._validate_path_security(file_path)

        # [20251216_BUGFIX] Fallback type detection for uppercase function names
        # React components are often functions starting with uppercase (e.g., function Button)
        # Try class first for uppercase names, fall back to function if not found
        if "." in symbol:
            target_types_to_try = ["method"]
        elif symbol and symbol[0].isupper():
            # Uppercase: could be class OR function (React components)
            target_types_to_try = ["class", "function"]
        else:
            target_types_to_try = ["function"]

        # Extract the symbol using extract_code with fallback
        result = None
        last_error = None
        for target_type in target_types_to_try:
            result = await server.extract_code(
                target_type=target_type,
                target_name=symbol,
                file_path=str(file_path),
                language=language,
                include_context=True,
                include_token_estimate=True,
            )
            if result.success:
                break
            last_error = result.error

        if result is None or not result.success:
            return json.dumps(
                {
                    "error": last_error or "Extraction failed",
                    "language": language,
                    "module": module,
                    "symbol": symbol,
                }
            )

        # Return full result with metadata
        return json.dumps(
            {
                "uri": f"code:///{language}/{module}/{symbol}",
                "mimeType": get_mime_type(language),
                "code": result.full_code,
                "metadata": {
                    "file_path": str(file_path),
                    "language": language,
                    "module": module,
                    "symbol": symbol,
                    "line_start": result.line_start,
                    "line_end": result.line_end,
                    "token_estimate": result.token_estimate,
                    # JSX/TSX metadata
                    "jsx_normalized": result.jsx_normalized,
                    "is_server_component": result.is_server_component,
                    "is_server_action": result.is_server_action,
                    "component_type": result.component_type,
                },
            },
            indent=2,
        )

    except PermissionError as e:
        return json.dumps(
            {
                "error": str(e),
                "language": language,
                "module": module,
                "symbol": symbol,
            }
        )
    except Exception as e:
        return json.dumps(
            {
                "error": f"Resource access failed: {str(e)}",
                "language": language,
                "module": module,
                "symbol": symbol,
            }
        )


__all__ = [
    "get_project_call_graph",
    "get_project_dependencies",
    "get_project_structure",
    "get_version",
    "get_health",
    "get_capabilities",
    "get_file_resource",
    "get_analysis_resource",
    "get_symbol_resource",
    "get_code_resource",
]
