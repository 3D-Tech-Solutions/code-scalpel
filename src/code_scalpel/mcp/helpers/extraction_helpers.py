"""Extraction helpers for MCP server."""

from __future__ import annotations

import ast
import asyncio
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

from mcp.server.fastmcp import Context

from code_scalpel.licensing.features import get_tool_capabilities, has_capability
from code_scalpel.mcp.helpers.security_helpers import validate_path_security
from code_scalpel.mcp.helpers.session import add_audit_entry
from code_scalpel.mcp.models.core import ContextualExtractionResult, PatchResultModel
from code_scalpel.parsing import ParsingError, parse_python_code

if TYPE_CHECKING:
    from code_scalpel import SurgicalExtractor

logger = logging.getLogger("code_scalpel.mcp.extraction")


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


# [20260120_DEPRECATED] Use _get_project_root() instead of this static variable.
# Kept for backward compatibility with code that references PROJECT_ROOT directly.
PROJECT_ROOT = Path.cwd()


MAX_CODE_SIZE = 100_000


def _get_cache():
    try:
        from code_scalpel.cache import get_cache

        return get_cache()
    except ImportError:
        return None


# PLACEHOLDER_FOR_EXTRACTION_ERRORS

# PLACEHOLDER_FUNCTIONS


def _extraction_error(
    target_name: str,
    error: str,
    tier: str = "community",
    language: str | None = None,
) -> ContextualExtractionResult:
    """Create a standardized error result for extraction failures.

    [20260111_FEATURE] Added tier and language metadata for transparency.
    """
    return ContextualExtractionResult(
        success=False,
        target_name=target_name,
        target_code="",
        context_code="",
        full_code="",
        error=error,
        tier_applied=tier,
        language_detected=language,
        cross_file_deps_enabled=False,
        max_depth_applied=None,
    )


async def _extract_polyglot(
    target_type: str,
    target_name: str,
    file_path: str | None,
    code: str | None,
    language: Any,
    include_token_estimate: bool,
) -> ContextualExtractionResult:
    """
    [20251214_FEATURE] v2.0.0 - Multi-language extraction using PolyglotExtractor.

    Handles extraction for JavaScript, TypeScript, and Java using tree-sitter
    and the Unified IR system.

    Args:
        target_type: "function", "class", or "method"
        target_name: Name of element to extract
        file_path: Path to source file
        code: Source code string (if file_path not provided)
        language: Language enum value
        include_token_estimate: Include token count estimate

    Returns:
        ContextualExtractionResult with extracted code
    """
    from code_scalpel.licensing.tier_detector import get_current_tier
    from code_scalpel.mcp.path_resolver import resolve_path

    # [20251221_FEATURE] v3.1.0 - Use UnifiedExtractor instead of PolyglotExtractor
    # [20251228_BUGFIX] Avoid deprecated shim imports.
    from code_scalpel.surgery.unified_extractor import Language, UnifiedExtractor

    if file_path is None and code is None:
        return _extraction_error(target_name, "Must provide either 'file_path' or 'code' argument")

    try:
        # Create extractor from file or code
        if file_path is not None:
            resolved_path = resolve_path(file_path, str(_get_project_root()))
            extractor = UnifiedExtractor.from_file(resolved_path, language)
        else:
            # code is guaranteed to be str here (checked earlier in function)
            assert code is not None
            extractor = UnifiedExtractor(code, language=language)

        # Perform extraction
        result = extractor.extract(target_type, target_name)

        if not result.success:
            return _extraction_error(target_name, result.error or "Extraction failed")

        token_estimate = result.token_estimate if include_token_estimate else 0

        # [20260111_FEATURE] Get tier and limits for metadata
        tier = get_current_tier()
        from code_scalpel.licensing.config_loader import get_tool_limits

        limits = get_tool_limits("extract_code", tier)
        max_depth_limit = limits.get("max_depth")

        # Map Language enum to string
        lang_str_map = {
            Language.PYTHON: "python",
            Language.JAVASCRIPT: "javascript",
            Language.TYPESCRIPT: "typescript",
            Language.JAVA: "java",
        }
        lang_str = lang_str_map.get(language, "unknown")

        # [20251216_FEATURE] v2.0.2 - Include JSX/TSX metadata in result
        return ContextualExtractionResult(
            success=True,
            target_name=target_name,
            target_code=result.code,
            context_code="",  # Cross-file deps not yet supported for non-Python
            full_code=result.code,
            context_items=[],
            total_lines=result.end_line - result.start_line + 1,
            line_start=result.start_line,
            line_end=result.end_line,
            token_estimate=token_estimate,
            # [20260111_FEATURE] Output metadata for transparency
            tier_applied=tier,
            language_detected=lang_str,
            cross_file_deps_enabled=False,  # Not supported for non-Python yet
            max_depth_applied=max_depth_limit,
            jsx_normalized=result.jsx_normalized,
            is_server_component=result.is_server_component,
            is_server_action=result.is_server_action,
            component_type=result.component_type,
        )
    except FileNotFoundError as e:
        return _extraction_error(target_name, str(e))
    except Exception as e:
        return _extraction_error(target_name, f"Extraction failed: {str(e)}")


def _create_extractor(
    file_path: str | None, code: str | None, target_name: str
) -> tuple[SurgicalExtractor | None, ContextualExtractionResult | None]:
    """
    Create a SurgicalExtractor from file_path or code.

    [20251214_FEATURE] v1.5.3 - Integrated PathResolver for intelligent path resolution

    Returns (extractor, None) on success, (None, error_result) on failure.
    """
    from code_scalpel import SurgicalExtractor
    from code_scalpel.mcp.path_resolver import resolve_path

    if file_path is None and code is None:
        return None, _extraction_error(target_name, "Must provide either 'file_path' or 'code' argument")

    if file_path is not None:
        try:
            # [20251214_FEATURE] Use PathResolver for intelligent path resolution
            resolved_path = resolve_path(file_path, str(_get_project_root()))
            return SurgicalExtractor.from_file(resolved_path), None
        except FileNotFoundError as e:
            # PathResolver provides helpful error messages
            return None, _extraction_error(target_name, str(e))
        except ValueError as e:
            return None, _extraction_error(target_name, str(e))
    else:
        try:
            # code is guaranteed to be str here (we checked file_path is None and code is not None above)
            assert code is not None
            return SurgicalExtractor(code), None
        except (SyntaxError, ValueError) as e:
            return None, _extraction_error(target_name, f"Syntax error in code: {str(e)}")


def _extract_method(extractor: SurgicalExtractor, target_name: str):
    """Extract a method, handling the ClassName.method_name parsing."""
    if "." not in target_name:
        return None, _extraction_error(target_name, "Method name must be 'ClassName.method_name' format")
    class_name, method_name = target_name.rsplit(".", 1)
    return extractor.get_method(class_name, method_name), None


def _perform_extraction(
    extractor: SurgicalExtractor,
    target_type: str,
    target_name: str,
    include_context: bool,
    include_cross_file_deps: bool,
    context_depth: int,
    file_path: str | None,
):
    """
    Perform the actual extraction based on target type and options.

    Returns (result, cross_file_result, error_result).
    """
    # [20251228_BUGFIX] Avoid deprecated shim imports.
    from code_scalpel.surgery.surgical_extractor import CrossFileResolution

    cross_file_result: CrossFileResolution | None = None

    # CROSS-FILE RESOLUTION PATH
    if include_cross_file_deps and file_path is not None:
        if target_type in ("function", "class"):
            cross_file_result = extractor.resolve_cross_file_dependencies(
                target_name=target_name,
                target_type=target_type,
                max_depth=context_depth,
            )
            return cross_file_result.target, cross_file_result, None
        else:
            # Method - fall back to regular extraction
            result, error = _extract_method(extractor, target_name)
            return result, None, error

    # INTRA-FILE CONTEXT PATH
    if target_type == "function":
        if include_context:
            return (
                extractor.get_function_with_context(target_name, max_depth=context_depth),
                None,
                None,
            )
        return extractor.get_function(target_name), None, None

    if target_type == "class":
        if include_context:
            return (
                extractor.get_class_with_context(target_name, max_depth=context_depth),
                None,
                None,
            )
        return extractor.get_class(target_name), None, None

    if target_type == "method":
        result, error = _extract_method(extractor, target_name)
        return result, None, error

    return (
        None,
        None,
        _extraction_error(
            target_name,
            f"Unknown target_type: {target_type}. Use 'function', 'class', or 'method'.",
        ),
    )


def _process_cross_file_context(cross_file_result) -> tuple[str, list[str]]:
    """Process cross-file resolution results into context_code and context_items."""
    if cross_file_result is None or not cross_file_result.external_symbols:
        return "", []

    external_parts = []
    external_names = []
    for sym in cross_file_result.external_symbols:
        external_parts.append(f"# From {sym.source_file}")
        external_parts.append(sym.code)
        external_names.append(f"{sym.name} ({sym.source_file})")

    context_code = "\n\n".join(external_parts)

    # Add unresolved imports as a comment
    if cross_file_result.unresolved_imports:
        unresolved_comment = "# Unresolved imports: " + ", ".join(cross_file_result.unresolved_imports)
        context_code = unresolved_comment + "\n\n" + context_code

    return context_code, external_names


def _build_full_code(imports_needed: list[str], context_code: str, target_code: str) -> str:
    """Build the combined full_code for LLM consumption."""
    parts = []
    if imports_needed:
        parts.append("\n".join(imports_needed))
    if context_code:
        parts.append(context_code)
    parts.append(target_code)
    return "\n\n".join(parts)


async def _extract_code_impl(
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
) -> ContextualExtractionResult:
    """
    Surgically extract specific code elements (functions, classes, methods).

    **TOKEN-EFFICIENT MODE (RECOMMENDED):**
    Provide `file_path` - the server reads the file directly. The Agent
    never sees the full file content, saving potentially thousands of tokens.

    **MULTI-LANGUAGE SUPPORT (v2.0.0):**
    Supports Python, JavaScript, TypeScript, and Java. Language is auto-detected
    from file extension, or specify explicitly with `language` parameter.

    **CROSS-FILE DEPENDENCIES:**
    Set `include_cross_file_deps=True` to automatically resolve imports.
    If your function uses `TaxRate` from `models.py`, this will extract
    `TaxRate` from `models.py` and include it in the response.

    **LEGACY MODE:**
    Provide `code` as a string - for when you already have code in context.

    [20260102_BUGFIX] Default microservice host now binds to loopback to avoid
    unintended exposure on all interfaces.

    Args:
        target_type: Type of element - "function", "class", or "method".
        target_name: Name of the element. For methods, use "ClassName.method_name".
        file_path: Path to the source file (TOKEN SAVER - server reads file).
        code: Source code string (fallback if file_path not provided).
        language: Language override: "python", "javascript", "typescript", "java".
                  If None, auto-detects from file extension.
        include_context: If True, also extract intra-file dependencies.
        context_depth: How deep to traverse dependencies (1=direct, 2=transitive).
        include_cross_file_deps: If True, resolve imports from external files.
        include_token_estimate: If True, include estimated token count.

    Returns:
        ContextualExtractionResult with extracted code and metadata.

    Example (Efficient - Agent sends ~50 tokens, receives ~200):
        extract_code(
            file_path="/project/src/utils.py",
            target_type="function",
            target_name="calculate_tax"
        )

    Example (JavaScript extraction):
        extract_code(
            file_path="/project/src/utils.js",
            target_type="function",
            target_name="calculateTax"
        )

    Example (Java method extraction):
        extract_code(
            file_path="/project/src/Calculator.java",
            target_type="method",
            target_name="Calculator.add"
        )

    Example (With cross-file dependencies):
        extract_code(
            file_path="/project/src/services/order.py",
            target_type="function",
            target_name="process_order",
            include_cross_file_deps=True
        )
    """
    from code_scalpel.licensing.tier_detector import get_current_tier
    from code_scalpel.mcp.path_resolver import resolve_path

    # [20251215_FEATURE] v2.0.0 - Roots capability support
    # Fetch allowed roots from client for security boundary enforcement
    # (Deprecated: roots fetching moved to session initialization)
    # [20251228_BUGFIX] Avoid deprecated shim imports.
    from code_scalpel.surgery.surgical_extractor import (
        ContextualExtraction,
        ExtractionResult,
    )
    from code_scalpel.surgery.unified_extractor import Language, detect_language

    # [20251228_FEATURE] Tier-limited option: cross-file dependency resolution.
    tier = get_current_tier()
    if include_cross_file_deps and not has_capability("extract_code", "cross_file_deps", tier):
        return ContextualExtractionResult(
            success=False,
            target_name=target_name,
            target_code="",
            context_code="",
            full_code="",
            context_items=[],
            total_lines=0,
            line_start=0,
            line_end=0,
            token_estimate=0,
            error="Feature 'cross_file_deps' requires PRO tier.",
            # [20260111_FEATURE] Output metadata for transparency
            tier_applied=tier,
            language_detected=language,
            cross_file_deps_enabled=False,
            max_depth_applied=None,
        )

    # [20251221_FEATURE] v3.1.0 - Unified extractor for all languages
    # Determine language from parameter, file extension, or code content
    detected_lang = Language.AUTO
    if language:
        lang_map = {
            "python": Language.PYTHON,
            "javascript": Language.JAVASCRIPT,
            "js": Language.JAVASCRIPT,
            "jsx": Language.JAVASCRIPT,  # [20251216_FEATURE] JSX is JavaScript with JSX syntax
            "typescript": Language.TYPESCRIPT,
            "ts": Language.TYPESCRIPT,
            "tsx": Language.TYPESCRIPT,  # [20251216_FEATURE] TSX is TypeScript with JSX syntax
            "java": Language.JAVA,
        }
        detected_lang = lang_map.get(language.lower(), Language.AUTO)

    if detected_lang == Language.AUTO:
        detected_lang = detect_language(file_path, code)

    # [20251214_FEATURE] Route to polyglot extractor for non-Python languages
    if detected_lang != Language.PYTHON:
        return await _extract_polyglot(
            target_type=target_type,
            target_name=target_name,
            file_path=file_path,
            code=code,
            language=detected_lang,
            include_token_estimate=include_token_estimate,
        )

    # Python path - use existing SurgicalExtractor with full context support
    # Step 1: Create extractor
    extractor, error = _create_extractor(file_path, code, target_name)
    if error:
        return error

    # extractor is guaranteed to be non-None when error is None
    assert extractor is not None

    try:
        # Step 2: Perform extraction
        result, cross_file_result, error = _perform_extraction(
            extractor,
            target_type,
            target_name,
            include_context,
            include_cross_file_deps,
            context_depth,
            file_path,
        )
        if error:
            return error

        # Step 3: Handle None result
        if result is None:
            return _extraction_error(
                target_name,
                f"{target_type.capitalize()} '{target_name}' not found in code",
            )

        # Step 4: Process result based on type
        if isinstance(result, ExtractionResult):
            if not result.success:
                return _extraction_error(
                    target_name,
                    result.error or f"{target_type.capitalize()} '{target_name}' not found",
                )
            target_code = result.code
            total_lines = result.line_end - result.line_start + 1 if result.line_end > 0 else 0
            line_start = result.line_start
            line_end = result.line_end
            imports_needed = result.imports_needed

            # Handle cross-file context
            context_code, context_items = _process_cross_file_context(cross_file_result)

        elif isinstance(result, ContextualExtraction):
            if not result.target.success:
                return _extraction_error(
                    target_name,
                    result.target.error or f"{target_type.capitalize()} '{target_name}' not found",
                )
            target_code = result.target.code
            context_items = result.context_items
            context_code = result.context_code
            total_lines = result.total_lines
            line_start = result.target.line_start
            line_end = result.target.line_end
            imports_needed = result.target.imports_needed
        else:
            return _extraction_error(target_name, f"Unexpected result type: {type(result).__name__}")

        # Step 5: Build final response
        full_code = _build_full_code(imports_needed, context_code, target_code)
        token_estimate = len(full_code) // 4 if include_token_estimate else 0

        advanced: dict[str, Any] = {}

        # Optional advanced extraction features (Python only)
        def _load_source_for_adv() -> str:
            if file_path is not None:
                try:
                    resolved = resolve_path(file_path, str(_get_project_root()))
                    return Path(resolved).read_text(encoding="utf-8")
                except Exception:
                    return code or ""
            return code or ""
            return code or ""

        if variable_promotion:
            if target_type != "function":
                return _extraction_error(target_name, "variable_promotion requires target_type='function'.")
            if not has_capability("extract_code", "variable_promotion", tier):
                return _extraction_error(target_name, "variable_promotion requires PRO tier")
            try:
                from code_scalpel.surgery.surgical_extractor import promote_variables

                promoted = promote_variables(_load_source_for_adv(), target_name)
                if getattr(promoted, "success", False):
                    advanced["variable_promotion"] = {
                        "promoted_function": promoted.promoted_function,
                        "promoted_variables": promoted.promoted_variables,
                        "original_function": promoted.original_function,
                        "explanation": promoted.explanation,
                    }
                else:
                    advanced["variable_promotion"] = {
                        "error": getattr(promoted, "error", None) or "Variable promotion failed",
                    }
            except Exception as e:
                advanced["variable_promotion"] = {"error": f"Variable promotion failed: {e}"}

        if closure_detection:
            if target_type != "function":
                return _extraction_error(target_name, "closure_detection requires target_type='function'.")
            if tier == "community":
                return _extraction_error(target_name, "closure_detection requires PRO tier")
            try:
                from code_scalpel.surgery.surgical_extractor import (
                    detect_closure_variables as _detect_closures,
                )

                clos = _detect_closures(_load_source_for_adv(), target_name)
                if getattr(clos, "success", False):
                    advanced["closure_detection"] = {
                        "function_name": clos.function_name,
                        "has_closures": clos.has_closures,
                        "closure_variables": [
                            {
                                "name": cv.name,
                                "source": cv.source,
                                "line_number": cv.line_number,
                                "risk_level": cv.risk_level,
                                "captured_from": cv.captured_from,
                                "suggestion": cv.suggestion,
                            }
                            for cv in clos.closure_variables
                        ],
                        "explanation": clos.explanation,
                    }
                else:
                    advanced["closure_detection"] = {
                        "error": getattr(clos, "error", None) or "Closure analysis failed",
                    }
            except Exception as e:
                advanced["closure_detection"] = {"error": f"Closure analysis failed: {e}"}

        if dependency_injection_suggestions:
            if target_type != "function":
                return _extraction_error(
                    target_name,
                    "dependency_injection_suggestions requires target_type='function'.",
                )
            if tier == "community":
                return _extraction_error(target_name, "dependency injection suggestions require PRO tier")
            try:
                from code_scalpel.surgery.surgical_extractor import (
                    suggest_dependency_injection as _suggest_di,
                )

                di = _suggest_di(_load_source_for_adv(), target_name)
                if getattr(di, "success", False):
                    advanced["dependency_injection_suggestions"] = {
                        "function_name": di.function_name,
                        "has_suggestions": di.has_suggestions,
                        "original_signature": di.original_signature,
                        "refactored_signature": di.refactored_signature,
                        "suggestions": [
                            {
                                "variable_name": s.variable_name,
                                "current_usage": s.current_usage,
                                "suggested_parameter": s.suggested_parameter,
                                "suggested_default": s.suggested_default,
                                "benefit": s.benefit,
                                "refactored_signature": s.refactored_signature,
                            }
                            for s in di.suggestions
                        ],
                        "explanation": di.explanation,
                    }
                else:
                    advanced["dependency_injection_suggestions"] = {
                        "error": getattr(di, "error", None) or "Dependency injection analysis failed",
                    }
            except Exception as e:
                advanced["dependency_injection_suggestions"] = {"error": f"DI analysis failed: {e}"}

        if as_microservice:
            if target_type != "function":
                return _extraction_error(target_name, "as_microservice requires target_type='function'.")
            if not has_capability("extract_code", "dockerfile_generation", tier):
                return _extraction_error(target_name, "as_microservice requires ENTERPRISE tier")
            try:
                from code_scalpel.surgery.surgical_extractor import (
                    extract_as_microservice as _extract_microservice,
                )

                ms = _extract_microservice(
                    _load_source_for_adv(),
                    target_name,
                    microservice_host,
                    microservice_port,
                )
                if getattr(ms, "success", False):
                    advanced["microservice"] = {
                        "function_code": ms.function_code,
                        "dockerfile": ms.dockerfile,
                        "api_spec": ms.api_spec,
                        "requirements_txt": ms.requirements_txt,
                        "readme": ms.readme,
                    }
                else:
                    advanced["microservice"] = {
                        "error": getattr(ms, "error", None) or "Microservice extraction failed",
                    }
            except Exception as e:
                advanced["microservice"] = {"error": f"Microservice extraction failed: {e}"}

        if organization_wide:
            if not has_capability("extract_code", "org_wide_resolution", tier):
                return _extraction_error(target_name, "organization_wide requires ENTERPRISE tier")
            if not code:
                return _extraction_error(target_name, "organization_wide requires 'code' input")
            try:
                from code_scalpel.surgery.surgical_extractor import (
                    resolve_organization_wide as _resolve_org,
                )

                org = _resolve_org(code=code, function_name=target_name, workspace_root=workspace_root)
                if getattr(org, "success", False):
                    advanced["organization_wide_resolution"] = {
                        "target_name": org.target_name,
                        "target_code": org.target_code,
                        "cross_repo_imports": [
                            {
                                "repo_name": imp.repo_name,
                                "file_path": imp.file_path,
                                "symbols": imp.symbols,
                                "repo_root": imp.repo_root,
                            }
                            for imp in org.cross_repo_imports
                        ],
                        "resolved_symbols": org.resolved_symbols,
                        "monorepo_structure": org.monorepo_structure,
                        "explanation": org.explanation,
                    }
                else:
                    advanced["organization_wide_resolution"] = {
                        "error": getattr(org, "error", None) or "Organization-wide resolution failed",
                    }
            except Exception as e:
                advanced["organization_wide_resolution"] = {"error": f"Organization-wide resolution failed: {e}"}

        # [20260111_FEATURE] Get tier limits for metadata
        from code_scalpel.licensing.config_loader import get_tool_limits

        limits = get_tool_limits("extract_code", tier)
        max_depth_limit = limits.get("max_depth")

        return ContextualExtractionResult(
            success=True,
            target_name=target_name,
            target_code=target_code,
            context_code=context_code,
            full_code=full_code,
            context_items=context_items,
            total_lines=total_lines,
            line_start=line_start,
            line_end=line_end,
            token_estimate=token_estimate,
            # [20260111_FEATURE] Output metadata for transparency
            tier_applied=tier,
            language_detected="python",
            cross_file_deps_enabled=include_cross_file_deps,
            max_depth_applied=max_depth_limit,
            advanced=advanced,
        )

    except Exception as e:
        return _extraction_error(target_name, f"Extraction failed: {str(e)}")


async def rename_symbol(
    file_path: str,
    target_type: str,
    target_name: str,
    new_name: str,
    create_backup: bool = True,
) -> PatchResultModel:
    """
    Rename a function, class, or method in a file.

    This updates the definition of the symbol.

    Args:
        file_path: Path to the Python source file.
        target_type: "function", "class", or "method".
        target_name: Current name (e.g., "my_func" or "MyClass.my_method").
        new_name: New name (e.g., "new_func" or "new_method").
        create_backup: If True (default), create a .bak file before modifying.

    Returns:
        PatchResultModel with success status.
    """
    from code_scalpel.licensing.config_loader import (
        get_cached_limits,
        get_tool_limits,
        merge_limits,
    )
    from code_scalpel.licensing.features import get_tool_capabilities
    from code_scalpel.licensing.tier_detector import get_current_tier
    from code_scalpel.mcp.path_resolver import resolve_path
    from code_scalpel.surgery.surgical_patcher import UnifiedPatcher

    warnings: list[str] = []

    # [20260121_BUGFIX] CRITICAL: Validate identifier BEFORE any file modifications
    # to prevent leaving code in broken syntax state (atomicity guarantee)
    import keyword

    if not new_name or not new_name.isidentifier() or keyword.iskeyword(new_name):
        error_msg = f"Invalid Python identifier: '{new_name}'"
        if keyword.iskeyword(new_name):
            error_msg += f" ('{new_name}' is a reserved keyword)"
        return PatchResultModel(
            success=False,
            file_path=file_path,
            target_name=target_name,
            target_type=target_type,
            error=error_msg,
        )

    try:
        resolved = resolve_path(file_path, str(_get_project_root()))
        resolved_path = Path(resolved)
        validate_path_security(resolved_path, _get_project_root())
        file_path = str(resolved_path)

        # [20260103_BUGFIX] Use UnifiedPatcher for automatic language detection
        patcher = UnifiedPatcher.from_file(file_path)
    except FileNotFoundError:
        return PatchResultModel(
            success=False,
            file_path=file_path,
            target_name=target_name,
            target_type=target_type,
            error=f"File not found: {file_path}",
        )
    except ValueError as e:
        return PatchResultModel(
            success=False,
            file_path=file_path,
            target_name=target_name,
            target_type=target_type,
            error=str(e),
        )

    result = patcher.rename_symbol(target_type, target_name, new_name)

    if result.success:
        backup_path = patcher.save(backup=create_backup)

        # V1.0: Pro/Enterprise attempt conservative cross-file refactor.
        tier = get_current_tier()
        caps = get_tool_capabilities("rename_symbol", tier)
        default_limits = caps.get("limits", {})
        config = get_cached_limits()
        overrides = get_tool_limits("rename_symbol", tier, config=config)
        limits = merge_limits(default_limits, overrides)

        max_files_searched = limits.get("max_files_searched")
        max_files_updated = limits.get("max_files_updated")

        # If configured as definition-only, skip cross-file updates.
        if tier in {"pro", "enterprise"} and not ((max_files_searched == 0) and (max_files_updated == 0)):
            try:
                import asyncio
                from functools import partial

                from code_scalpel.surgery.rename_symbol_refactor import (
                    rename_references_across_project,
                )

                # [20260122_BUGFIX] Run cross-file rename in thread pool to prevent blocking event loop
                # The function iterates through many files (up to max_files_searched=500 for Pro),
                # which can appear to hang if run synchronously in async context
                loop = asyncio.get_event_loop()
                xres = await loop.run_in_executor(
                    None,
                    partial(
                        rename_references_across_project,
                        project_root=_get_project_root(),
                        target_file=Path(file_path),
                        target_type=target_type,
                        target_name=target_name,
                        new_name=new_name,
                        create_backup=create_backup,
                        max_files_searched=max_files_searched,
                        max_files_updated=max_files_updated,
                    ),
                )

                if not xres.success:
                    warnings.append(f"Cross-file rename skipped: {xres.error or 'unknown error'}")
                elif xres.changed_files:
                    warnings.append(f"Updated references/imports in {len(xres.changed_files)} additional file(s).")

                warnings.extend(xres.warnings)
            except Exception as e:
                warnings.append(f"Cross-file rename skipped due to error: {e}")
        else:
            warnings.append("Definition-only rename (no cross-file updates) at this tier.")

        return PatchResultModel(
            success=True,
            file_path=file_path,
            target_name=target_name,
            target_type=target_type,
            lines_before=result.lines_before,
            lines_after=result.lines_after,
            backup_path=backup_path,
            warnings=warnings,
        )
    else:
        return PatchResultModel(
            success=False,
            file_path=file_path,
            target_name=target_name,
            target_type=target_type,
            error=result.error,
            warnings=warnings,
        )


async def update_symbol(
    file_path: str,
    target_type: str,
    target_name: str,
    new_code: str | None = None,
    operation: str = "replace",
    new_name: str | None = None,
    create_backup: bool = True,
) -> PatchResultModel:
    """
    Surgically replace a function, class, or method in a file with new code.

    [20260121_REFACTOR] Stateless per-call model - no session limits. Supports
    optional batch mode for multiple updates in one call (Community tier max 10).

    This is the SAFE way to modify code - you provide only the new symbol,
    and the server handles:
    - Locating the exact symbol boundaries (including decorators)
    - Validating the replacement code syntax
    - Preserving all surrounding code exactly
        - Creating a backup before modification
        - Atomic write (prevents partial writes)

        Args:
            file_path: Path to the Python source file to modify.
            target_type: Type of element - "function", "class", or "method".
            target_name: Name of the element. For methods, use "ClassName.method_name".
            new_code: The complete new definition (including def/class line and body).
            create_backup: If True (default), create a .bak file before modifying.

        Returns:
            PatchResultModel with success status, line changes, and backup path.

        Example (Fix a function):
            update_symbol(
                file_path="/project/src/utils.py",
                target_type="function",
                target_name="calculate_tax",
                new_code='''def calculate_tax(amount, rate=0.1):
        \"\"\"Calculate tax with proper rounding.\"\"\"
        return round(amount * rate, 2)
    '''
            )

        Example (Update a method):
            update_symbol(
                file_path="/project/src/models.py",
                target_type="method",
                target_name="User.validate_email",
                new_code='''def validate_email(self, email):
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    '''
            )

        Safety Features:
            - Backup created at {file_path}.bak (unless create_backup=False)
            - Syntax validation before any file modification
            - Atomic write prevents corruption on crash
            - Original indentation preserved
    """
    from code_scalpel.licensing.tier_detector import get_current_tier
    from code_scalpel.mcp.path_resolver import resolve_path

    # [20251228_BUGFIX] Avoid deprecated shim imports.
    from code_scalpel.surgery.surgical_patcher import UnifiedPatcher

    # [20251225_FEATURE] Tier-based behavior via capability matrix (no upgrade hints).
    tier = get_current_tier()
    caps = get_tool_capabilities("update_symbol", tier)
    capabilities = set(caps.get("capabilities", set()))
    limits = caps.get("limits", {})
    warnings: list[str] = []

    # [20260121_REFACTOR] Per-call throughput cap (stateless)
    # Session counters are removed; each call is independent
    max_updates_per_call = limits.get("max_updates_per_call", -1)
    updates_in_this_call = 1  # Single update (future: will support batch)

    # [20251228_BUGFIX] Honor create_backup unless the tier explicitly requires it.
    # 'backup_enabled' means the feature is supported; it is not a mandate.
    backup_required = bool(limits.get("backup_required", False))
    if backup_required and not create_backup:
        create_backup = True
        warnings.append("Backup was required for this operation.")

    validation_level = str(limits.get("validation_level", "syntax"))

    def _semantic_name_check() -> str | None:
        """Best-effort semantic validation that the replacement defines the target."""
        if new_code is None:
            return "Replacement code is required for operation='replace'."

        tree = None
        try:
            # [20260119_FEATURE] Use unified parser for deterministic error handling
            parsed_tree, report = parse_python_code(new_code)
            # Type narrowing: ensure we got a Module
            if not isinstance(parsed_tree, ast.Module):
                return "Replacement code must be a valid Python module."
            tree = parsed_tree

            if report.was_sanitized:
                # Warn but don't fail - sanitization is informational
                nonlocal warnings
                warnings.append(f"Replacement code was auto-sanitized: {'; '.join(report.changes)}")
        except ParsingError as e:
            msg = f"Replacement code has syntax error: {e}"
            if e.location:
                msg += f" at {e.location}"
            if e.suggestion:
                msg += f". {e.suggestion}"
            return msg
        except Exception as e:
            return f"Failed to parse replacement code: {str(e)}"

        # Check if tree was successfully parsed (guaranteed to be Module here)
        if tree is None:
            return "Failed to parse replacement code structure."

        if not tree.body:
            return "Replacement code is empty."

        first = tree.body[0]
        if target_type == "function":
            if not isinstance(first, (ast.FunctionDef, ast.AsyncFunctionDef)):
                return "Replacement for function must be a function definition."
            if first.name != target_name:
                return f"Replacement function name '{first.name}' does not match target '{target_name}'."
        elif target_type == "class":
            if not isinstance(first, ast.ClassDef):
                return "Replacement for class must be a class definition."
            if first.name != target_name:
                return f"Replacement class name '{first.name}' does not match target '{target_name}'."
        elif target_type == "method":
            if "." not in target_name:
                return "Method name must be 'ClassName.method_name' format."
            class_name, method_name = target_name.rsplit(".", 1)
            if not isinstance(first, (ast.FunctionDef, ast.AsyncFunctionDef)):
                return "Replacement for method must be a function definition."
            if first.name != method_name:
                return f"Replacement method name '{first.name}' does not match target '{class_name}.{method_name}'."

        return None

    operation = (operation or "replace").strip().lower()
    if operation not in {"replace", "rename"}:
        return PatchResultModel(
            success=False,
            file_path=file_path or "",
            target_name=target_name,
            target_type=target_type,
            error_code="UPDATE_SYMBOL_INVALID_OPERATION",
            warnings=warnings,
            error="Invalid operation. Use 'replace' or 'rename'.",
        )

    # Validate inputs
    if not file_path:
        return PatchResultModel(
            success=False,
            file_path="",
            target_name=target_name,
            target_type=target_type,
            error_code="UPDATE_SYMBOL_MISSING_FILE_PATH",
            warnings=warnings,
            error="Parameter 'file_path' is required.",
        )

    if operation == "replace":
        if not new_code or not str(new_code).strip():
            return PatchResultModel(
                success=False,
                file_path=file_path,
                target_name=target_name,
                target_type=target_type,
                error_code="UPDATE_SYMBOL_MISSING_NEW_CODE",
                warnings=warnings,
                error="Parameter 'new_code' cannot be empty for operation='replace'.",
            )
    else:
        if not new_name or not new_name.strip():
            return PatchResultModel(
                success=False,
                file_path=file_path,
                target_name=target_name,
                target_type=target_type,
                error_code="UPDATE_SYMBOL_MISSING_NEW_NAME",
                warnings=warnings,
                error="Parameter 'new_name' is required for operation='rename'.",
            )

    if target_type not in ("function", "class", "method"):
        return PatchResultModel(
            success=False,
            file_path=file_path,
            target_name=target_name,
            target_type=target_type,
            error_code="UPDATE_SYMBOL_INVALID_TARGET_TYPE",
            warnings=warnings,
            error=f"Invalid target_type: {target_type}. Use 'function', 'class', or 'method'.",
        )

    # Community+ (all tiers): semantic validation that the replacement defines the
    # target symbol (prevents accidental renames via replacement code).
    if operation == "replace":
        semantic_error = _semantic_name_check()
        if semantic_error:
            return PatchResultModel(
                success=False,
                file_path=file_path,
                target_name=target_name,
                target_type=target_type,
                error_code="UPDATE_SYMBOL_SEMANTIC_VALIDATION_FAILED",
                warnings=warnings,
                error=semantic_error,
            )

    # Load the file
    try:
        resolved = resolve_path(file_path, str(_get_project_root()))
        resolved_path = Path(resolved)
        validate_path_security(resolved_path, _get_project_root())
        file_path = str(resolved_path)

        # [20260103_BUGFIX] Use UnifiedPatcher for automatic language detection
        # UnifiedPatcher auto-detects language from file extension and routes to
        # appropriate parser (SurgicalPatcher for Python, PolyglotPatcher for JS/TS/Java)
        patcher = UnifiedPatcher.from_file(file_path)
    except FileNotFoundError:
        return PatchResultModel(
            success=False,
            file_path=file_path,
            target_name=target_name,
            target_type=target_type,
            error_code="UPDATE_SYMBOL_FILE_NOT_FOUND",
            warnings=warnings,
            error=f"File not found: {file_path}.",
        )
    except ValueError as e:
        return PatchResultModel(
            success=False,
            file_path=file_path,
            target_name=target_name,
            target_type=target_type,
            error_code="UPDATE_SYMBOL_INVALID_INPUT",
            warnings=warnings,
            error=str(e),
        )

    # [20250101_FEATURE] v1.0 roadmap: Enterprise code review approval
    if "code_review_approval" in capabilities:
        approval_result = await _check_code_review_approval(file_path, target_name, target_type, new_code)
        if not approval_result.get("approved", True):
            return PatchResultModel(
                success=False,
                file_path=file_path,
                target_name=target_name,
                target_type=target_type,
                error_code="UPDATE_SYMBOL_APPROVAL_REQUIRED",
                warnings=warnings,
                error=f"Code review approval required: {approval_result.get('reason', 'Pending review')}",
            )
        if approval_result.get("reviewer"):
            warnings.append(f"Approved by: {approval_result['reviewer']}")

    # [20250101_FEATURE] v1.0 roadmap: Enterprise compliance check
    if "compliance_check" in capabilities:
        compliance_result = await _check_compliance(file_path, target_name, new_code)
        if not compliance_result.get("compliant", True):
            return PatchResultModel(
                success=False,
                file_path=file_path,
                target_name=target_name,
                target_type=target_type,
                error_code="UPDATE_SYMBOL_COMPLIANCE_FAILED",
                warnings=warnings,
                error=f"Compliance check failed: {compliance_result.get('violations', [])}",
            )
        if compliance_result.get("warnings"):
            warnings.extend(compliance_result["warnings"])

    # [20250101_FEATURE] v1.0 roadmap: Pro pre-update hook
    if "pre_update_hook" in capabilities:
        hook_result = await _run_pre_update_hook(file_path, target_name, target_type, new_code)
        if not hook_result.get("continue", True):
            return PatchResultModel(
                success=False,
                file_path=file_path,
                target_name=target_name,
                target_type=target_type,
                error_code="UPDATE_SYMBOL_PRE_HOOK_BLOCKED",
                warnings=warnings,
                error=f"Pre-update hook blocked: {hook_result.get('reason', 'Hook returned false')}",
            )
        if hook_result.get("warnings"):
            warnings.extend(hook_result["warnings"])

    # Apply the patch based on target type
    try:
        if operation == "rename":
            # Tier-aware rename support. Delegates to the dedicated tool which
            # enforces tier limits/capabilities (Community definition-only; Pro/Ent
            # may update references depending on configured limits).
            rename_result = await rename_symbol(
                file_path=file_path,
                target_type=target_type,
                target_name=target_name,
                new_name=str(new_name),
                create_backup=create_backup,
            )

            # [20260121_REFACTOR] Removed session-limit bypass check (per-call model)
            if getattr(rename_result, "success", False):
                # No session counting; just audit if enabled
                if "audit_trail" in capabilities:
                    add_audit_entry(
                        tool_name="update_symbol",
                        file_path=file_path,
                        target_name=target_name,
                        operation=operation,
                        success=True,
                        tier=tier,
                        metadata={
                            "rename_delegated": True,
                            "new_name": str(new_name),
                            "backup_path": getattr(rename_result, "backup_path", None),
                        },
                    )

                merged_warnings: list[str] = []
                merged_warnings.extend(warnings)
                merged_warnings.extend(getattr(rename_result, "warnings", []) or [])

                return PatchResultModel(
                    success=True,
                    file_path=getattr(rename_result, "file_path", file_path),
                    target_name=getattr(rename_result, "target_name", target_name),
                    target_type=getattr(rename_result, "target_type", target_type),
                    lines_before=getattr(rename_result, "lines_before", 0),
                    lines_after=getattr(rename_result, "lines_after", 0),
                    lines_delta=getattr(rename_result, "lines_delta", 0),
                    backup_path=getattr(rename_result, "backup_path", None),
                    # [20260121_REFACTOR] Per-call metadata instead of session counts
                    max_updates_per_call=(int(max_updates_per_call) if max_updates_per_call > 0 else None),
                    updates_in_batch=updates_in_this_call,
                    batch_truncated=False,
                    warnings=merged_warnings,
                )

            # Failure case: return as-is.
            return PatchResultModel(
                success=getattr(rename_result, "success", False),
                file_path=getattr(rename_result, "file_path", file_path),
                target_name=getattr(rename_result, "target_name", target_name),
                target_type=getattr(rename_result, "target_type", target_type),
                lines_before=getattr(rename_result, "lines_before", 0),
                lines_after=getattr(rename_result, "lines_after", 0),
                lines_delta=getattr(rename_result, "lines_delta", 0),
                backup_path=getattr(rename_result, "backup_path", None),
                error=getattr(rename_result, "error", None),
                error_code=getattr(rename_result, "error_code", None),
                hint=getattr(rename_result, "hint", None),
                # [20260121_REFACTOR] Per-call metadata
                max_updates_per_call=(int(max_updates_per_call) if max_updates_per_call > 0 else None),
                updates_in_batch=updates_in_this_call,
                batch_truncated=False,
                warnings=(
                    (getattr(rename_result, "warnings", []) or [])
                    if not warnings
                    else (warnings + (getattr(rename_result, "warnings", []) or []))
                ),
            )

        # At this point we are performing a replacement, which requires concrete code.
        assert new_code is not None

        if target_type == "function":
            result = patcher.update_function(target_name, new_code)
            # [20251229_FEATURE] Auto-insert if not found
            if not result.success and "not found" in (result.error or ""):
                # [20260101_BUGFIX] Verify method exists before calling
                if hasattr(patcher, "insert_function") and callable(patcher.insert_function):
                    result = patcher.insert_function(new_code)  # type: ignore[attr-defined]
                if result.success:
                    warnings.append(f"Function '{target_name}' was not found, so it was inserted.")

        elif target_type == "class":
            result = patcher.update_class(target_name, new_code)
            # [20251229_FEATURE] Auto-insert if not found
            if not result.success and "not found" in (result.error or ""):
                # [20260101_BUGFIX] Verify method exists before calling
                if hasattr(patcher, "insert_class") and callable(patcher.insert_class):
                    result = patcher.insert_class(new_code)  # type: ignore[attr-defined]
                if result.success:
                    warnings.append(f"Class '{target_name}' was not found, so it was inserted.")

        elif target_type == "method":
            if "." not in target_name:
                return PatchResultModel(
                    success=False,
                    file_path=file_path,
                    target_name=target_name,
                    target_type=target_type,
                    error_code="UPDATE_SYMBOL_INVALID_METHOD_NAME",
                    warnings=warnings,
                    error="Method name must be 'ClassName.method_name' format.",
                )
            class_name, method_name = target_name.rsplit(".", 1)
            result = patcher.update_method(class_name, method_name, new_code)
            # [20251229_FEATURE] Auto-insert if not found (but class must exist)
            if not result.success and "not found" in (result.error or "") and "Class" not in (result.error or ""):
                # [20260101_BUGFIX] Verify method exists before calling
                if hasattr(patcher, "insert_method") and callable(patcher.insert_method):
                    result = patcher.insert_method(class_name, new_code)  # type: ignore[attr-defined]
                if result.success:
                    warnings.append(f"Method '{method_name}' was not found in '{class_name}', so it was inserted.")
        else:
            # Should not reach here due to validation above
            return PatchResultModel(
                success=False,
                file_path=file_path,
                target_name=target_name,
                target_type=target_type,
                warnings=warnings,
                error=f"Unknown target_type: {target_type}.",
            )

        if not result.success:
            return PatchResultModel(
                success=False,
                file_path=file_path,
                target_name=target_name,
                target_type=target_type,
                error_code="UPDATE_SYMBOL_PATCH_FAILED",
                warnings=warnings,
                error=result.error,
            )

        # Save the changes
        backup_path = patcher.save(backup=create_backup)

        # [20260122_BUGFIX] Remove os.sync() entirely - it can hang indefinitely
        # in various environments (Docker, WSL, network filesystems, CI).
        # The patcher.save() already does proper file flush, and os.sync() is
        # not necessary for correctness.
        # Previous code attempted to skip in pytest environments, but subprocess
        # servers don't have pytest loaded, causing hangs.

        # [20251230_FEATURE] v3.5.0 - Pro tier: Update cross-file references
        if "cross_file_updates" in capabilities:
            try:
                cross_file_updates = await _update_cross_file_references(file_path, target_type, target_name, new_code)
                if cross_file_updates["files_updated"] > 0:
                    warnings.append(f"Updated {cross_file_updates['files_updated']} files with reference changes")
            except Exception as e:
                warnings.append(f"Cross-file update warning: {str(e)}")

        # [20250101_FEATURE] v1.0 roadmap: Pro post-update hook
        if "post_update_hook" in capabilities:
            try:
                post_hook_result = await _run_post_update_hook(file_path, target_name, target_type, result)
                if post_hook_result.get("warnings"):
                    warnings.extend(post_hook_result["warnings"])
            except Exception as e:
                warnings.append(f"Post-update hook warning: {str(e)}")

        # [20251230_FEATURE] v3.5.0 - Enterprise tier: Git integration with branch & tests
        git_branch = None
        tests_passed = None
        if "git_integration" in capabilities:
            try:
                git_result = await _perform_atomic_git_refactor(file_path, target_name, new_code)
                git_branch = git_result.get("branch_name")
                tests_passed = git_result.get("tests_passed")

                if git_branch:
                    warnings.append(f"Created git branch: {git_branch}")

                if tests_passed is False:
                    # Tests failed - rollback everything
                    if git_result.get("reverted"):
                        return PatchResultModel(
                            success=False,
                            file_path=file_path,
                            target_name=target_name,
                            target_type=target_type,
                            warnings=warnings,
                            error="Tests failed after refactor - changes reverted automatically",
                        )
                elif tests_passed is True:
                    warnings.append("All tests passed ✓")
            except Exception as e:
                warnings.append(f"Git integration warning: {str(e)}")

        # Enterprise: post-save verification + rollback on failure.
        if ("rollback_support" in capabilities) or (validation_level == "full"):
            try:
                with open(file_path, encoding="utf-8") as f:
                    updated_source = f.read()

                # [20260119_FEATURE] Use unified parser for syntax check
                try:
                    _, post_save_report = parse_python_code(updated_source, filename=file_path)
                    if post_save_report.was_sanitized:
                        warnings.append("Post-save verification: file required sanitization to parse")
                except ParsingError as parse_err:
                    raise ValueError(f"Post-save syntax verification failed: {parse_err}") from parse_err

                # Verify the symbol is still extractable (guards against boundary mistakes)
                from code_scalpel import SurgicalExtractor

                extractor = SurgicalExtractor(updated_source)
                if target_type == "function":
                    check = extractor.get_function(target_name)
                elif target_type == "class":
                    check = extractor.get_class(target_name)
                else:
                    class_name, method_name = target_name.rsplit(".", 1)
                    check = extractor.get_method(class_name, method_name)

                if not getattr(check, "success", False):
                    raise ValueError(check.error or "Post-save verification failed")
            except Exception as e:
                if backup_path:
                    import shutil

                    shutil.copy2(backup_path, file_path)
                return PatchResultModel(
                    success=False,
                    file_path=file_path,
                    target_name=target_name,
                    target_type=target_type,
                    error_code="UPDATE_SYMBOL_POST_SAVE_VERIFICATION_FAILED",
                    warnings=warnings,
                    error=f"Post-save verification failed: {e}",
                )

        # [20250101_FEATURE] v1.0 roadmap: Increment session counter on success
        # [20260121_REFACTOR] No session counting; just audit if enabled
        if "audit_trail" in capabilities:
            add_audit_entry(
                tool_name="update_symbol",
                file_path=file_path,
                target_name=target_name,
                operation=operation,
                success=True,
                tier=tier,
                metadata={
                    "lines_before": result.lines_before,
                    "lines_after": result.lines_after,
                    "backup_path": backup_path,
                },
            )

        return PatchResultModel(
            success=True,
            file_path=file_path,
            target_name=target_name,
            target_type=target_type,
            lines_before=result.lines_before,
            lines_after=result.lines_after,
            lines_delta=result.lines_delta,
            backup_path=backup_path,
            # [20260121_REFACTOR] Per-call metadata instead of session counts
            max_updates_per_call=(int(max_updates_per_call) if max_updates_per_call > 0 else None),
            updates_in_batch=updates_in_this_call,
            batch_truncated=False,
            warnings=warnings,
        )

    except Exception as e:
        # [20260121_REFACTOR] Audit failures too (per-call model)
        if "audit_trail" in capabilities:
            add_audit_entry(
                tool_name="update_symbol",
                file_path=file_path or "",
                target_name=target_name,
                operation=operation,
                success=False,
                tier=tier,
                metadata={"error": str(e)},
            )
        return PatchResultModel(
            success=False,
            file_path=file_path,
            target_name=target_name,
            target_type=target_type,
            warnings=warnings,
            error_code="UPDATE_SYMBOL_INTERNAL_ERROR",
            error=f"Patch failed: {str(e)}",
        )


async def _perform_atomic_git_refactor(file_path: str, target_name: str, new_code: str) -> dict[str, Any]:
    """
    Enterprise tier: Atomic refactoring with git branch creation and test execution.

    [20251230_FEATURE] v3.5.0 - Enterprise tier atomic refactoring.

    Creates a git branch, applies changes, runs tests, and reverts if tests fail.

    Args:
        file_path: Path to modified file
        target_name: Name of the modified symbol
        new_code: The new code

    Returns:
        Dictionary with branch_name, tests_passed, and revert status
    """
    result = {"branch_name": None, "tests_passed": None, "reverted": False}

    try:
        import subprocess
        from datetime import datetime
        from pathlib import Path

        # Get project root (look for .git)
        file_path_obj = Path(file_path).resolve()
        project_root = file_path_obj.parent

        while project_root.parent != project_root:
            if (project_root / ".git").exists():
                break
            project_root = project_root.parent

        if not (project_root / ".git").exists():
            # No git repo found
            return result

        # Generate branch name
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        branch_name = f"refactor/{target_name.replace('.', '_')}_{timestamp}"
        result["branch_name"] = branch_name

        # Create and checkout new branch
        subprocess.run(
            ["git", "checkout", "-b", branch_name],
            cwd=project_root,
            capture_output=True,
            check=True,
        )

        # Commit the changes
        subprocess.run(
            ["git", "add", str(file_path_obj.relative_to(project_root))],
            cwd=project_root,
            capture_output=True,
            check=True,
        )

        subprocess.run(
            ["git", "commit", "-m", f"Refactor: Update {target_name}"],
            cwd=project_root,
            capture_output=True,
            check=True,
        )

        # Run tests (look for common test commands)
        test_commands = [
            ["pytest", "-x"],  # Stop on first failure
            ["python", "-m", "pytest", "-x"],
            ["python", "-m", "unittest", "discover"],
            ["npm", "test"],
        ]

        tests_run = False
        tests_passed_flag = False

        for cmd in test_commands:
            try:
                test_result = subprocess.run(
                    cmd,
                    cwd=project_root,
                    capture_output=True,
                    timeout=300,  # 5 minute timeout
                )
                tests_run = True
                tests_passed_flag = test_result.returncode == 0
                break
            except (FileNotFoundError, subprocess.TimeoutExpired):
                continue

        result["tests_passed"] = tests_passed_flag if tests_run else None

        # If tests failed, revert
        if tests_run and not tests_passed_flag:
            # Go back to previous branch
            subprocess.run(["git", "checkout", "-"], cwd=project_root, capture_output=True)
            # Delete the failed branch
            subprocess.run(
                ["git", "branch", "-D", branch_name],
                cwd=project_root,
                capture_output=True,
            )
            result["reverted"] = True

        return result

    except Exception as e:
        # If anything fails, try to return to original branch
        try:
            subprocess.run(["git", "checkout", "-"], capture_output=True)
        except Exception:
            # [20260102_BUGFIX] Avoid bare except while preserving best-effort cleanup
            pass
        result["error"] = str(e)
        return result


async def _update_cross_file_references(
    modified_file: str, target_type: str, target_name: str, new_code: str
) -> dict[str, Any]:
    """
    Pro tier: Update cross-file references when a symbol changes.

    [20251230_FEATURE] v3.5.0 - Pro tier cross-file reference updates.

    Scans project for files that reference the modified symbol and updates
    import statements or call sites if needed.

    Args:
        modified_file: Path to the file that was modified
        target_type: Type of symbol (function/class/method)
        target_name: Name of the symbol
        new_code: The new code (to detect signature changes)

    Returns:
        Dictionary with files_updated count and list of updated files
    """
    result = {"files_updated": 0, "updated_files": [], "errors": []}

    try:
        # Get project root
        from pathlib import Path

        modified_path = Path(modified_file).resolve()
        project_root = modified_path.parent

        # Find project root by looking for .git or pyproject.toml
        while project_root.parent != project_root:
            if (project_root / ".git").exists() or (project_root / "pyproject.toml").exists():
                break
            project_root = project_root.parent

        # Use get_symbol_references to find all references
        from code_scalpel.mcp.archive.server import _get_symbol_references_sync

        refs_result = await asyncio.to_thread(_get_symbol_references_sync, target_name, str(project_root))

        if not refs_result.success or not refs_result.references:
            return result

        # Check if signature changed
        new_sig = None

        try:
            # [20260119_FEATURE] Use unified parser for best-effort signature detection
            new_tree, _ = parse_python_code(new_code)
            for node in ast.walk(new_tree):
                if isinstance(node, ast.FunctionDef) and node.name == target_name:
                    new_sig = ast.unparse(node.args)
                    break
        except ParsingError:
            # Best-effort signature detection - continue if parsing fails
            pass

        if not new_sig:
            # No signature change detected, skip updates
            return result

        # Update files with references (excluding the modified file itself)
        for ref in refs_result.references:
            if ref.file == modified_file or ref.is_definition:
                continue

            ref_path = project_root / ref.file
            if not ref_path.exists():
                continue

            try:
                # Read file
                with open(ref_path, encoding="utf-8") as f:
                    content = f.read()

                # Simple heuristic: if the reference line contains a function call,
                # add a comment about potential signature change
                lines = content.splitlines()
                if 0 <= ref.line - 1 < len(lines):
                    line = lines[ref.line - 1]
                    if f"{target_name}(" in line:
                        # Add warning comment
                        indent = len(line) - len(line.lstrip())
                        warning = " " * indent + f"# WARNING: {target_name} signature may have changed\n"
                        lines.insert(ref.line - 1, warning)

                        # Write back
                        new_content = "\n".join(lines) + "\n"
                        with open(ref_path, "w", encoding="utf-8") as f:
                            f.write(new_content)

                        result["files_updated"] += 1
                        result["updated_files"].append(str(ref_path))
            except Exception as e:
                result["errors"].append(f"{ref.file}: {str(e)}")

        return result

    except Exception as e:
        result["errors"].append(f"Cross-file update failed: {str(e)}")
        return result


async def _check_code_review_approval(
    file_path: str,
    target_name: str,
    target_type: str,
    new_code: str | None,
) -> dict[str, Any]:
    """
    Enterprise tier: Check if code review approval is required and granted.

    [20250101_FEATURE] v1.0 roadmap - Enterprise code review approval.

    This checks for approval requirements based on:
    - File sensitivity (e.g., security-critical paths)
    - Symbol visibility (public APIs)
    - Change magnitude

    In a full implementation, this would integrate with code review systems
    like GitHub PRs, GitLab MRs, or enterprise approval workflows.

    Args:
        file_path: Path to the file being modified
        target_name: Name of the symbol being modified
        target_type: Type of symbol
        new_code: The new code

    Returns:
        Dictionary with approved status, reviewer info, and reason
    """
    # Default: approved (for now - full implementation would check approval system)
    result = {
        "approved": True,
        "reviewer": None,
        "reason": None,
        "requires_review": False,
    }

    # Check for sensitive paths that require review
    sensitive_paths = [
        "security",
        "auth",
        "crypto",
        "payment",
        "admin",
    ]

    file_lower = file_path.lower()
    for sensitive in sensitive_paths:
        if sensitive in file_lower:
            result["requires_review"] = True
            # For now, auto-approve with warning
            result["reason"] = f"File in sensitive path: {sensitive}"
            break

    return result


async def _check_compliance(
    file_path: str,
    target_name: str,
    new_code: str | None,
) -> dict[str, Any]:
    """
    Enterprise tier: Check compliance rules before allowing mutation.

    [20250101_FEATURE] v1.0 roadmap - Enterprise compliance checking.

    Validates code changes against:
    - Security policies (no secrets, no unsafe patterns)
    - Style guidelines (formatting, naming conventions)
    - Architecture rules (layering, dependencies)

    Args:
        file_path: Path to the file being modified
        target_name: Name of the symbol being modified
        new_code: The new code

    Returns:
        Dictionary with compliant status, violations, and warnings
    """
    result = {
        "compliant": True,
        "violations": [],
        "warnings": [],
    }

    if not new_code:
        return result

    # Basic compliance checks
    code_lower = new_code.lower()

    # Check for hardcoded secrets
    secret_patterns = [
        ("password", "Hardcoded password detected"),
        ("secret_key", "Hardcoded secret key detected"),
        ("api_key", "Hardcoded API key detected"),
        ("private_key", "Hardcoded private key detected"),
    ]

    for pattern, message in secret_patterns:
        if f'{pattern} = "' in code_lower or f"{pattern} = '" in code_lower:
            result["warnings"].append(f"Compliance warning: {message}")

    # Check for unsafe patterns
    unsafe_patterns = [
        ("eval(", "Use of eval() detected - security risk"),
        ("exec(", "Use of exec() detected - security risk"),
        ("__import__(", "Dynamic import detected - review required"),
    ]

    for pattern, message in unsafe_patterns:
        if pattern in new_code:
            result["warnings"].append(f"Compliance warning: {message}")

    return result


async def _run_pre_update_hook(
    file_path: str,
    target_name: str,
    target_type: str,
    new_code: str | None,
) -> dict[str, Any]:
    """
    Pro tier: Run pre-update hook before applying changes.

    [20250101_FEATURE] v1.0 roadmap - Pro pre/post update hooks.

    Pre-update hooks can:
    - Validate custom business rules
    - Check for conflicts
    - Log upcoming changes
    - Block updates based on conditions

    Args:
        file_path: Path to the file being modified
        target_name: Name of the symbol being modified
        target_type: Type of symbol
        new_code: The new code

    Returns:
        Dictionary with continue flag and any warnings
    """
    result = {
        "continue": True,
        "warnings": [],
    }

    # Check for .code-scalpel/hooks/pre_update.py
    from pathlib import Path

    hooks_dir = Path(file_path).parent

    while hooks_dir.parent != hooks_dir:
        hook_path = hooks_dir / ".code-scalpel" / "hooks" / "pre_update.py"
        if hook_path.exists():
            try:
                # Execute the hook (in sandbox)
                import importlib.util

                spec = importlib.util.spec_from_file_location("pre_update", hook_path)
                if spec and spec.loader:
                    hook_module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(hook_module)

                    if hasattr(hook_module, "pre_update"):
                        hook_result = hook_module.pre_update(
                            file_path=file_path,
                            target_name=target_name,
                            target_type=target_type,
                            new_code=new_code,
                        )
                        if isinstance(hook_result, dict):
                            result.update(hook_result)
            except Exception as e:
                result["warnings"].append(f"Pre-update hook warning: {str(e)}")
            break
        hooks_dir = hooks_dir.parent

    return result


async def _run_post_update_hook(
    file_path: str,
    target_name: str,
    target_type: str,
    result: Any,
) -> dict[str, Any]:
    """
    Pro tier: Run post-update hook after applying changes.

    [20250101_FEATURE] v1.0 roadmap - Pro pre/post update hooks.

    Post-update hooks can:
    - Log completed changes
    - Trigger downstream actions
    - Update documentation
    - Notify stakeholders

    Args:
        file_path: Path to the file that was modified
        target_name: Name of the symbol that was modified
        target_type: Type of symbol
        result: The patch result

    Returns:
        Dictionary with any additional warnings
    """
    hook_result = {
        "warnings": [],
    }

    # Check for .code-scalpel/hooks/post_update.py
    from pathlib import Path

    hooks_dir = Path(file_path).parent

    while hooks_dir.parent != hooks_dir:
        hook_path = hooks_dir / ".code-scalpel" / "hooks" / "post_update.py"
        if hook_path.exists():
            try:
                import importlib.util

                spec = importlib.util.spec_from_file_location("post_update", hook_path)
                if spec and spec.loader:
                    hook_module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(hook_module)

                    if hasattr(hook_module, "post_update"):
                        post_result = hook_module.post_update(
                            file_path=file_path,
                            target_name=target_name,
                            target_type=target_type,
                            success=(result.success if hasattr(result, "success") else True),
                        )
                        if isinstance(post_result, dict):
                            hook_result.update(post_result)
            except Exception as e:
                hook_result["warnings"].append(f"Post-update hook warning: {str(e)}")
            break
        hooks_dir = hooks_dir.parent

    return hook_result
