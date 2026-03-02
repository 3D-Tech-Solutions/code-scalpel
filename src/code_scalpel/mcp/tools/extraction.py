"""Extraction and refactor MCP tool registrations."""

from __future__ import annotations

import time

from mcp.server.fastmcp import Context
from code_scalpel.mcp.debug import debug_print
import sys
import traceback

from code_scalpel.mcp.helpers import extraction_helpers as _helpers
from code_scalpel.mcp.models.core import PatchResultModel
from code_scalpel.mcp.protocol import mcp, _get_current_tier
from code_scalpel.mcp.contract import ToolResponseEnvelope, ToolError, make_envelope
from code_scalpel.mcp.oracle_middleware import (
    with_oracle_resilience,
    SymbolStrategy,
    RenameSymbolStrategy,
)
from code_scalpel import __version__ as _pkg_version

_extract_code = getattr(_helpers, "extract_code", None) or getattr(
    _helpers, "_extract_code_impl", None
)
_rename_symbol = getattr(_helpers, "rename_symbol", None)
_update_symbol = getattr(_helpers, "update_symbol", None)

if _extract_code is None or _rename_symbol is None or _update_symbol is None:
    raise ImportError("Extraction helpers missing expected tool implementations.")


@mcp.tool(
    description="Surgically extract a named function, class, or method with optional dependency context."
)
@with_oracle_resilience(tool_id="extract_code", strategy=SymbolStrategy)
async def extract_code(
    target_type: str,
    target_name: str,
    file_path: str | None = None,
    code: str | None = None,
    language: str | None = None,
    include_context: bool = False,
    context_depth: int = 1,
    include_cross_file_deps: bool = False,
    include_token_estimate: bool = True,
    variable_promotion: bool = False,
    closure_detection: bool = False,
    dependency_injection_suggestions: bool = False,
    as_microservice: bool = False,
    microservice_host: str = "127.0.0.1",
    microservice_port: int = 8000,
    organization_wide: bool = False,
    workspace_root: str | None = None,
    ctx: Context | None = None,
) -> ToolResponseEnvelope:
    """Extract code elements with optional dependency context.

    Extracts a specified code element (function, class, method) along with optional
    context, cross-file dependencies, and refactoring suggestions. Provide either
    'file_path' (recommended) or 'code' for the source.

    **Tier Behavior:**
    - Community: Single-file extraction only, basic symbols, max depth 1, 1MB limit
    - Pro: Cross-file dependencies, variable promotion, closure detection, unlimited depth and size
    - Enterprise: Organization-wide resolution, custom patterns, Dockerfile generation, unlimited depth, 100MB limit

    **Tier Capabilities:**
    - Community: single_file_extraction, basic_symbols (max_depth=1, max_file_size_mb=1)
    - Pro: All Community + cross_file_deps, context_extraction, variable_promotion, closure_detection, dependency_injection_suggestions (max_depth=unlimited, max_file_size_mb=100)
    - Enterprise: All Pro + org_wide_resolution, custom_extraction_patterns, dockerfile_generation, service_boundaries (max_depth=unlimited, max_file_size_mb=100)

    **Args:**
        target_type (str): Type of element to extract - "function", "class", or "method".
        target_name (str): Name of the element to extract.
        file_path (str, optional): Path to source file. Either file_path or code required.
        code (str, optional): Source code string. Either file_path or code required.
        language (str, optional): Programming language. Default: auto-detect.
                       Supported: python, javascript, typescript, java, c, cpp, csharp, go
        include_context (bool): Include surrounding code context. Default: False.
        context_depth (int): Depth of context to include. Default: 1.
        include_cross_file_deps (bool): Include cross-file dependencies (Pro+ only). Default: False.
        include_token_estimate (bool): Include token count estimate. Default: True.
        variable_promotion (bool): Suggest variables for external dependencies (Pro+ only). Default: False.
        closure_detection (bool): Detect closure requirements (Pro+ only). Default: False.
        dependency_injection_suggestions (bool): Suggest DI patterns (Pro+ only). Default: False.
        as_microservice (bool): Refactor as microservice (Enterprise only). Default: False.
        microservice_host (str): Host for microservice. Default: "127.0.0.1".
        microservice_port (int): Port for microservice. Default: 8000.
        organization_wide (bool): Organization-wide scope (Enterprise only). Default: False.
        workspace_root (str, optional): Workspace root directory.
        ctx (Context, optional): MCP context for progress reporting.

    **Returns:**
        ToolResponseEnvelope with ContextualExtractionResult containing:
        - success (bool): True if extraction completed successfully
        - server_version (str): Code Scalpel version
        - target_name (str): Name of target element
        - target_code (str): Target element source code
        - context_code (str): Combined dependency source code
        - full_code (str): Complete code block for LLM consumption
        - context_items (list[str]): Names of included dependencies
        - total_lines (int): Total lines in extraction
        - line_start (int): Starting line number of target
        - line_end (int): Ending line number of target
        - token_estimate (int): Estimated token count
        - tier_applied (str): Tier used ("community"/"pro"/"enterprise")
        - language_detected (str): Language detected/used
        - cross_file_deps_enabled (bool): Whether cross-file deps were enabled
        - max_depth_applied (int, optional): Max depth limit applied (None=unlimited)
        - jsx_normalized (bool): Whether JSX syntax was normalized
        - is_server_component (bool): Next.js Server Component flag
        - is_server_action (bool): Next.js Server Action flag
        - component_type (str): React component type ("functional"/"class")
        - warnings (list[str]): Non-fatal warnings
        - advanced (dict): Tier-specific metadata
        - error (str, optional): Error message if extraction failed
        - error (str): Error message if tool execution failed
        - tier_applied (str): Tier used for analysis
        - duration_ms (int): Analysis duration in milliseconds
    """
    started = time.perf_counter()
    try:
        if _extract_code is None:
            from code_scalpel.mcp.models.core import ContextualExtractionResult

            result = ContextualExtractionResult(
                success=False,
                target_name=target_name,
                target_code="",
                context_code="",
                full_code="",
                error="extract_code helper not loaded",
            )
        else:
            result = await _extract_code(
                target_type,
                target_name,
                file_path=file_path,
                code=code,
                language=language,
                include_context=include_context,
                context_depth=context_depth,
                include_cross_file_deps=include_cross_file_deps,
                include_token_estimate=include_token_estimate,
                variable_promotion=variable_promotion,
                closure_detection=closure_detection,
                dependency_injection_suggestions=dependency_injection_suggestions,
                as_microservice=as_microservice,
                microservice_host=microservice_host,
                microservice_port=microservice_port,
                organization_wide=organization_wide,
                workspace_root=workspace_root,
                ctx=ctx,
            )
        duration_ms = int((time.perf_counter() - started) * 1000)
        tier = _get_current_tier()
        return make_envelope(
            data=result,
            tool_id="extract_code",
            tool_version=_pkg_version,
            tier=tier,
            duration_ms=duration_ms,
        )
    except Exception as exc:
        duration_ms = int((time.perf_counter() - started) * 1000)
        tier = _get_current_tier()
        error_obj = ToolError(error=str(exc), error_code="internal_error")
        return make_envelope(
            data=None,
            tool_id="extract_code",
            tool_version=_pkg_version,
            tier=tier,
            duration_ms=duration_ms,
            error=error_obj,
        )


@mcp.tool(
    description="Rename a symbol (function/class/variable) throughout a file or codebase."
)
@with_oracle_resilience(tool_id="rename_symbol", strategy=RenameSymbolStrategy)
async def rename_symbol(
    file_path: str,
    target_type: str,
    target_name: str,
    new_name: str,
    create_backup: bool = True,
) -> ToolResponseEnvelope:
    """Safely rename a function, class, or method in a file.

    **Tier Behavior:**
    - Community: Single-file renames only (definition + local references)
    - Pro: Cross-file renames within project scope
    - Enterprise: Unlimited cross-file renames with audit trail and approval workflows

    **Tier Capabilities:**
    - Community: Single-file renames, definition + local references only (max_files_searched=0, max_files_updated=0)
    - Pro: All Community + unlimited cross-file renames (max_files_searched=unlimited, max_files_updated=unlimited)
    - Enterprise: All Pro + audit trail, approval workflows, unlimited scope (max_files_searched=unlimited, max_files_updated=unlimited)

    **Args:**
        file_path (str): Path to the file containing the symbol to rename.
        target_type (str): Type of symbol - "function", "class", or "method".
        target_name (str): Current name of the symbol to rename.
        new_name (str): New name for the symbol.
        create_backup (bool): Whether to create a backup before renaming. Default: True.

    **Returns:**
        ToolResponseEnvelope containing PatchResultModel with:
        - success (bool): Whether the rename was successful
        - file_path (str): Path to the modified file
        - target_name (str): Name of the modified symbol
        - target_type (str): Type - function, class, or method
        - backup_path (str, optional): Path to backup file if created
        - error (str, optional): Error message if rename failed
        - tier_applied (str): Tier applied ("community"/"pro"/"enterprise")
        - max_files_searched (int): Maximum files that could be searched
        - max_files_updated (int): Maximum files that could be updated
        - warnings (list[str]): Non-fatal warnings
        - error (str): Error message if operation failed
        - tier_applied (str): Tier used for analysis
        - duration_ms (int): Analysis duration in milliseconds
    """
    started = time.perf_counter()
    try:
        if _rename_symbol is None:
            result = PatchResultModel(
                success=False,
                file_path=file_path,
                target_name=target_name,
                target_type=target_type,
                error="rename_symbol helper not loaded",
            )
        else:
            result = await _rename_symbol(
                file_path=file_path,
                target_type=target_type,
                target_name=target_name,
                new_name=new_name,
                create_backup=create_backup,
            )
        duration_ms = int((time.perf_counter() - started) * 1000)
        tier = _get_current_tier()
        return make_envelope(
            data=result,
            tool_id="rename_symbol",
            tool_version=_pkg_version,
            tier=tier,
            duration_ms=duration_ms,
        )
    except Exception as exc:
        duration_ms = int((time.perf_counter() - started) * 1000)
        tier = _get_current_tier()
        error_obj = ToolError(error=str(exc), error_code="internal_error")
        return make_envelope(
            data=None,
            tool_id="rename_symbol",
            tool_version=_pkg_version,
            tier=tier,
            duration_ms=duration_ms,
            error=error_obj,
        )


@mcp.tool(
    description="Replace a named function or class in a file with new code, preserving surrounding code."
)
@with_oracle_resilience(tool_id="update_symbol", strategy=SymbolStrategy)
async def update_symbol(
    file_path: str,
    target_type: str,
    target_name: str,
    new_code: str | None = None,
    operation: str = "replace",
    new_name: str | None = None,
    create_backup: bool = True,
) -> ToolResponseEnvelope:
    """Safely replace a function, class, or method in a file.

    **Tier Behavior:**
    - Community: Syntax validation only, up to 10 updates per call
    - Pro: Syntax + semantic validation, unlimited updates per call
    - Enterprise: Syntax + semantic + full compliance validation, unlimited updates per call

    **Tier Capabilities:**
    - Community: Syntax validation, automatic backups (max_updates=10)
    - Pro: All Community + semantic validation, unlimited updates
    - Enterprise: All Pro + full compliance validation, unlimited updates

    **Args:**
        file_path (str): Path to the file containing the symbol to update.
        target_type (str): Type of symbol - "function", "class", "method".
        target_name (str): Name of the symbol to update.
        new_code (str, optional): New code for the symbol (required for "replace" operation).
        operation (str): Operation type. Default: "replace" (only supported operation).
        new_name (str, optional): Optional new name for the symbol.
        create_backup (bool): Whether to create a backup before updating. Default: True.

    **Returns:**
        ToolResponseEnvelope containing PatchResultModel with:
        - success (bool): Whether the update was successful
        - file_path (str): Path to the modified file
        - target_name (str): Name of the modified symbol
        - target_type (str): Type - function, class, or method
        - error (str, optional): Error message if update failed
        - tier_applied (str): Tier applied ("community"/"pro"/"enterprise")
        - warnings (list[str]): Non-fatal warnings
        - error (str): Error message if operation failed
        - tier_applied (str): Tier used for analysis
        - duration_ms (int): Analysis duration in milliseconds
    """
    started = time.perf_counter()
    try:
        debug_print(
            f"DEBUG:update_symbol: start file_path={file_path!r} target_type={target_type!r} target_name={target_name!r} operation={operation!r}"
        )
        if _update_symbol is None:
            result = PatchResultModel(
                success=False,
                file_path=file_path,
                target_name=target_name,
                target_type=target_type,
                error="update_symbol helper not loaded",
            )
        else:
            try:
                debug_print("DEBUG:update_symbol: calling helper _update_symbol")
                result = await _update_symbol(
                    file_path=file_path,
                    target_type=target_type,
                    target_name=target_name,
                    new_code=new_code,
                    operation=operation,
                    new_name=new_name,
                    create_backup=create_backup,
                )
            except Exception:
                debug_print("ERROR:update_symbol: exception in helper _update_symbol:")
                traceback.print_exc(file=sys.stderr)
                raise
        duration_ms = int((time.perf_counter() - started) * 1000)
        tier = _get_current_tier()
        debug_print(
            f"DEBUG:update_symbol: helper returned, preparing envelope (duration_ms={duration_ms})"
        )
        try:
            env = make_envelope(
                data=result,
                tool_id="update_symbol",
                tool_version=_pkg_version,
                tier=tier,
                duration_ms=duration_ms,
            )
            debug_print("DEBUG:update_symbol: envelope created successfully")
            return env
        except Exception as exc:
            # Log full traceback and return an error envelope so the MCP
            # transport can still send a valid JSON response back to the client.
            debug_print("ERROR:update_symbol: exception while creating envelope:")
            traceback.print_exc(file=sys.stderr)
            # Use a generic internal_error code when the contract's ErrorCode
            # union does not include a custom serialization error string.
            error_obj = ToolError(error=str(exc), error_code="internal_error")
            return make_envelope(
                data=None,
                tool_id="update_symbol",
                tool_version=_pkg_version,
                tier=tier,
                duration_ms=duration_ms,
                error=error_obj,
            )
    except Exception as exc:
        duration_ms = int((time.perf_counter() - started) * 1000)
        tier = _get_current_tier()
        error_obj = ToolError(error=str(exc), error_code="internal_error")
        return make_envelope(
            data=None,
            tool_id="update_symbol",
            tool_version=_pkg_version,
            tier=tier,
            duration_ms=duration_ms,
            error=error_obj,
        )


__all__ = ["extract_code", "rename_symbol", "update_symbol"]
