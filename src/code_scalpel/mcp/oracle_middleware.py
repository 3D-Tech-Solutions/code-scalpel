"""Oracle resilience middleware for MCP tools.

Provides the @with_oracle_resilience decorator that intercepts tool failures
and generates intelligent suggestions using fuzzy matching.

This middleware implements the Active Resilience Model:
  Normalize → Validate → Suggest → Execute

When a tool raises ValidationError or FileNotFoundError, the oracle will:
1. Detect the error type and context
2. Apply the appropriate recovery strategy
3. Return suggestions with confidence scores
4. Return error_code="correction_needed" for LLM self-correction
"""

from __future__ import annotations

import asyncio
import functools
import logging
import os
import time
from typing import Any, Callable, TypeVar

from code_scalpel.mcp.contract import ToolError, ToolResponseEnvelope, make_envelope
from code_scalpel.mcp.validators.core import ValidationError, SemanticValidator
from code_scalpel.mcp.models.context import SourceContext, Language
from code_scalpel.mcp.routers import LanguageRouter
from code_scalpel.mcp.protocol import _get_current_tier
from code_scalpel import __version__ as _pkg_version

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


def _extract_path_from_kwargs(kwargs: dict[str, Any]) -> str | None:
    """Return the most relevant path-like argument from a tool call.

    [20260311_BUGFIX] Oracle path recovery must work for tools that use
    project_root, root_path, target_file, report_path, or path lists rather
    than only a single file_path parameter.
    """
    candidate_keys = (
        "file_path",
        "project_root",
        "root_path",
        "target_file",
        "path",
        "report_path",
        "policy_dir",
        "frontend_file_path",
        "backend_file_path",
    )
    for key in candidate_keys:
        value = kwargs.get(key)
        if isinstance(value, str) and value.strip():
            return value

    raw_paths = kwargs.get("paths")
    if isinstance(raw_paths, list):
        for value in raw_paths:
            if isinstance(value, str) and value.strip():
                return value

    return None


class RecoveryStrategy:
    """Base class for oracle recovery strategies."""

    @staticmethod
    def suggest(error: Exception, context: dict[str, Any]) -> list[dict[str, Any]]:
        """Generate suggestions for an error.

        Args:
            error: The exception that was raised
            context: Context dict with file_path, code, symbol_name, etc.

        Returns:
            List of suggestion dicts with 'symbol'/'path', 'score', and 'reason'
        """
        return []


class SymbolStrategy(RecoveryStrategy):
    """Recovery strategy for missing symbols (functions, classes, methods).

    Uses WeightedSymbolMatcher to suggest similar symbols when a symbol
    lookup fails, with locality and export boosts applied.
    """

    @staticmethod
    def suggest(error: Exception, context: dict[str, Any]) -> list[dict[str, Any]]:
        """Use SemanticValidator to suggest similar symbols.

        Args:
            error: The ValidationError that was raised
            context: Context dict with 'file_path', 'code', 'symbol_name'

        Returns:
            List of similar symbol suggestions with scores
        """
        file_path = context.get("file_path")
        code = context.get("code")
        symbol_name = context.get("symbol_name")

        if not symbol_name:
            return []

        # Build SourceContext for validation
        try:
            if file_path:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
            elif code:
                content = code
            else:
                return []

            # Auto-detect language
            lang_enum = Language.UNKNOWN
            if file_path:
                # Try to detect from extension
                _, ext = os.path.splitext(file_path)
                if ext in (".py", ".pyx"):
                    lang_enum = Language.PYTHON
                elif ext in (".js", ".jsx", ".ts", ".tsx"):
                    lang_enum = Language.JAVASCRIPT
            else:
                # Try to auto-detect from content
                try:
                    detection = LanguageRouter.detect(content, file_path=file_path)
                    lang_enum = detection.language
                except Exception:
                    lang_enum = Language.PYTHON  # Default fallback

            source_ctx = SourceContext(
                content=content,
                file_path=file_path,
                is_memory=(code is not None),
                language=lang_enum,
            )

            # Use existing SemanticValidator to get suggestions
            validator = SemanticValidator()
            try:
                validator.validate_symbol_exists(source_ctx, symbol_name)
            except ValidationError as ve:
                # ValidationError already has suggestions!
                suggestions = []
                if ve.suggestions:
                    for i, suggestion in enumerate(ve.suggestions[:3], 1):  # Top 3
                        # Calculate score (linear falloff from 0.95)
                        score = 0.95 - (i - 1) * 0.05
                        suggestions.append(
                            {
                                "symbol": suggestion,
                                "score": max(0.6, score),
                                "reason": "fuzzy_match",
                            }
                        )
                return suggestions

        except Exception as e:
            logger.debug(f"SymbolStrategy suggestion generation failed: {e}")
            return []

        return []


class PathStrategy(RecoveryStrategy):
    """Recovery strategy for missing files/directories.

    Uses Levenshtein distance to suggest similar file paths when a file
    is not found, searching in the parent directory.
    """

    @staticmethod
    def suggest(error: Exception, context: dict[str, Any]) -> list[dict[str, Any]]:
        """Use difflib to suggest similar file paths.

        Args:
            error: The FileNotFoundError that was raised
            context: Context dict with 'file_path'

        Returns:
            List of similar path suggestions with scores
        """
        file_path = context.get("file_path")

        if not file_path:
            return []

        abs_path = os.path.abspath(file_path)
        parent = os.path.dirname(abs_path)
        filename = os.path.basename(abs_path)

        if not os.path.exists(parent):
            return []

        # Get all files in parent directory
        try:
            siblings = [
                f for f in os.listdir(parent) if os.path.isfile(os.path.join(parent, f))
            ]
        except (OSError, PermissionError):
            return []

        if not siblings:
            return []

        # Use difflib for fuzzy matching
        from difflib import SequenceMatcher

        matches = []
        for sibling in siblings:
            ratio = SequenceMatcher(None, filename.lower(), sibling.lower()).ratio()
            if ratio > 0.6:  # Threshold
                full_path = os.path.join(parent, sibling)
                matches.append(
                    {
                        "path": full_path,
                        "score": round(ratio, 2),
                        "reason": "path_similarity",
                    }
                )

        # Sort by score descending
        matches.sort(key=lambda x: x["score"], reverse=True)
        return matches[:3]  # Top 3


class SafetyStrategy(RecoveryStrategy):
    """Recovery strategy for collision detection (rename conflicts).

    Detects when a rename target already exists in scope using semantic analysis.
    Provides scope-aware collision detection and suggests alternative names.
    """

    @staticmethod
    def suggest(error: Exception, context: dict[str, Any]) -> list[dict[str, Any]]:
        """Detect if new_name already exists and suggest alternatives.

        Args:
            error: The exception (ValidationError or other)
            context: Context dict with 'new_name', 'file_path', 'code', optionally 'target_type'

        Returns:
            List of safety suggestions with collision info
        """
        new_name = context.get("new_name")
        file_path = context.get("file_path")
        code = context.get("code")

        if not new_name:
            return []

        try:
            if file_path:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
            elif code:
                content = code
            else:
                return [
                    {
                        "hint": f"Rename to '{new_name}'. Verify uniqueness in scope.",
                        "reason": "collision_risk",
                        "score": 0.6,
                    }
                ]

            # Use SemanticValidator to get accurate symbol information
            try:
                source_ctx = SourceContext(
                    content=content,
                    file_path=file_path,
                    is_memory=(code is not None),
                    language=Language.PYTHON,  # Default to Python for now
                )

                validator = SemanticValidator()
                # Try to validate if new_name exists
                try:
                    validator.validate_symbol_exists(source_ctx, new_name)
                    # If validation passed, symbol exists
                    return [
                        {
                            "hint": f"Symbol '{new_name}' already exists in this file. Choose a unique name.",
                            "reason": "name_collision_detected",
                            "score": 0.99,
                            "suggestions": [
                                f"{new_name}_new",
                                f"{new_name}_v2",
                                f"{new_name}_backup",
                            ],
                        }
                    ]
                except ValidationError:
                    # Symbol doesn't exist, no collision
                    pass

            except Exception as e:
                logger.debug(f"SafetyStrategy semantic check failed: {e}")
                # Fall back to regex-based detection
                import re

                pattern = rf"\b(?:def|class)\s+{re.escape(new_name)}\b"
                if re.search(pattern, content):
                    return [
                        {
                            "hint": f"Symbol '{new_name}' already exists. Choose a unique name.",
                            "reason": "name_collision_detected",
                            "score": 0.99,
                        }
                    ]

        except Exception as e:
            logger.debug(f"SafetyStrategy check failed: {e}")

        return []


class NodeIdFormatStrategy(RecoveryStrategy):
    """Recovery strategy for invalid graph node ID formats.

    Validates node IDs match the required pattern: language::module::type::name
    Provides helpful suggestions when format is incorrect.
    """

    @staticmethod
    def suggest(error: Exception, context: dict[str, Any]) -> list[dict[str, Any]]:
        """Detect invalid node ID format and suggest corrections.

        Args:
            error: The exception that was raised
            context: Context dict with 'center_node_id' or similar

        Returns:
            List of format suggestion hints
        """
        node_id = context.get("center_node_id")
        if not node_id:
            return []

        import re

        # Expected format: language::module::type::name
        # Example: python::app.main::function::process_data
        pattern = r"^[a-z]+::[^:]+::(function|class|method)::[^:]+$"

        if re.match(pattern, node_id):
            # Format is actually valid
            return []

        # Format is invalid, provide helpful suggestions
        parts = node_id.split("::")
        expected_parts = 4

        if len(parts) < expected_parts:
            return [
                {
                    "hint": f"Node ID format should be: language::module::type::name. Got {len(parts)} parts, expected {expected_parts}.",
                    "reason": "format_error",
                    "score": 0.3,
                    "example": "python::app.routes::function::handle_request",
                }
            ]
        elif len(parts) > expected_parts:
            return [
                {
                    "hint": f"Node ID has too many components. Expected 4 (language::module::type::name), got {len(parts)}.",
                    "reason": "format_error",
                    "score": 0.3,
                    "example": "python::app.routes::function::handle_request",
                }
            ]
        else:
            # Has 4 parts but invalid type or format
            if parts[2] not in ["function", "class", "method"]:
                return [
                    {
                        "hint": f"Type '{parts[2]}' is invalid. Expected 'function', 'class', or 'method'.",
                        "reason": "format_error",
                        "score": 0.4,
                        "example": f"{parts[0]}::{parts[1]}::function::{parts[3]}",
                    }
                ]

        return []


class MethodNameFormatStrategy(RecoveryStrategy):
    """Recovery strategy for invalid method name formats.

    Validates method names match the required ClassName.method_name pattern.
    """

    @staticmethod
    def suggest(error: Exception, context: dict[str, Any]) -> list[dict[str, Any]]:
        """Detect invalid method name format and suggest corrections.

        Args:
            error: The exception that was raised
            context: Context dict with 'target_name' and optionally 'target_type'

        Returns:
            List of format suggestions
        """
        target_name = context.get("symbol_name") or context.get("target_name")
        target_type = context.get("target_type")

        if not target_name or target_type != "method":
            return []

        # Method names should have format: ClassName.method_name
        if "." not in target_name:
            return [
                {
                    "hint": f"Method name should use format 'ClassName.method_name', but got '{target_name}'.",
                    "reason": "format_error",
                    "score": 0.5,
                    "example": "User.validate_email",
                }
            ]

        # Has dot, check structure
        parts = target_name.split(".")
        if len(parts) != 2:
            return [
                {
                    "hint": f"Method name should have exactly one dot separating class and method (e.g., 'User.validate'), but got '{target_name}'.",
                    "reason": "format_error",
                    "score": 0.4,
                }
            ]

        class_name, method_name = parts
        if not class_name or not method_name:
            return [
                {
                    "hint": f"Invalid method format: both ClassName and method_name must be non-empty. Got '{target_name}'.",
                    "reason": "format_error",
                    "score": 0.3,
                }
            ]

        return []


class RenameSymbolStrategy(RecoveryStrategy):
    """Recovery strategy for rename operations.

    Combines SymbolStrategy (for typos in target_name) and SafetyStrategy
    (for collision detection in new_name) into a single strategy.
    """

    @staticmethod
    def suggest(error: Exception, context: dict[str, Any]) -> list[dict[str, Any]]:
        """Apply both SymbolStrategy and SafetyStrategy for rename operations.

        Args:
            error: The exception that was raised
            context: Context dict with 'target_name' and 'new_name'

        Returns:
            Combined suggestions from both strategies
        """
        all_suggestions = []

        # First apply SymbolStrategy to suggest corrections for target_name typos
        symbol_suggestions = SymbolStrategy.suggest(error, context)
        if symbol_suggestions:
            all_suggestions.extend(symbol_suggestions)

        # Then apply SafetyStrategy to check for collision with new_name
        safety_suggestions = SafetyStrategy.suggest(error, context)
        if safety_suggestions:
            all_suggestions.extend(safety_suggestions)

        # Return deduplicated and ranked suggestions
        seen: dict[tuple[str, Any] | str, dict[str, Any]] = {}
        for suggestion in all_suggestions:
            key: tuple[str, Any] | str
            if "symbol" in suggestion:
                key = ("symbol", suggestion["symbol"])
            elif "path" in suggestion:
                key = ("path", suggestion["path"])
            elif "hint" in suggestion:
                key = ("hint", suggestion["hint"])
            else:
                key = ("unknown", str(suggestion))

            if key not in seen or suggestion.get("score", 0) > seen[key].get(
                "score", 0
            ):
                seen[key] = suggestion

        sorted_suggestions = sorted(
            seen.values(), key=lambda x: x.get("score", 0), reverse=True
        )

        return sorted_suggestions[:3]


class CompositeStrategy(RecoveryStrategy):
    """Recovery strategy that chains multiple recovery strategies together.

    Tries each strategy in order and combines suggestions from all of them,
    ranking by confidence score.
    """

    def __init__(self, strategies: list[type[RecoveryStrategy]]):
        """Initialize with list of strategies to chain.

        Args:
            strategies: List of RecoveryStrategy classes to apply in order
        """
        self.strategies = strategies

    def suggest(
        self, error: Exception, context: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Apply all strategies and combine suggestions.

        Args:
            error: The exception that was raised
            context: Context dict with parameters

        Returns:
            Combined and ranked suggestions from all strategies
        """
        all_suggestions = []

        for strategy_class in self.strategies:
            try:
                suggestions = strategy_class.suggest(error, context)
                all_suggestions.extend(suggestions)
            except Exception as e:
                logger.debug(f"Strategy {strategy_class.__name__} failed: {e}")
                continue

        # Deduplicate and rank by score
        return self._rank_and_dedupe(all_suggestions)

    @staticmethod
    def _rank_and_dedupe(suggestions: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Deduplicate suggestions and rank by score.

        Args:
            suggestions: List of suggestion dicts

        Returns:
            Deduplicated and ranked suggestions
        """
        # Use symbol/path as unique key, keep highest score
        seen: dict[tuple[str, Any] | str, dict[str, Any]] = {}

        for suggestion in suggestions:
            # Determine unique key
            key: tuple[str, Any] | str
            if "symbol" in suggestion:
                key = ("symbol", suggestion["symbol"])
            elif "path" in suggestion:
                key = ("path", suggestion["path"])
            elif "hint" in suggestion:
                key = ("hint", suggestion["hint"])
            else:
                key = ("unknown", str(suggestion))

            # Keep suggestion with highest score
            if key not in seen or suggestion.get("score", 0) > seen[key].get(
                "score", 0
            ):
                seen[key] = suggestion

        # Sort by score descending and return top 3
        sorted_suggestions = sorted(
            seen.values(), key=lambda x: x.get("score", 0), reverse=True
        )

        return sorted_suggestions[:3]


def with_oracle_resilience(
    tool_id: str,
    strategy: type[RecoveryStrategy] = SymbolStrategy,
) -> Callable[[F], F]:
    """Decorator that adds oracle resilience to MCP tools.

    Wraps an async tool function to intercept both exceptions AND error envelopes,
    generating intelligent suggestions using the specified recovery strategy.

    Usage:
        @mcp.tool()
        @with_oracle_resilience(tool_id="extract_code", strategy=SymbolStrategy)
        async def extract_code(...) -> ToolResponseEnvelope:
            # Implementation

    The oracle intercepts errors in two ways:
    1. Direct exceptions: ValidationError, FileNotFoundError raised during execution
    2. Error envelopes: When tool returns envelope with error (tool catches first)

    For correctable errors, returns ToolError with error_code="correction_needed"
    and suggestions.

    Args:
        tool_id: MCP tool ID for envelope creation (e.g., "extract_code")
        strategy: Recovery strategy class to use for suggestions

    Returns:
        Decorated function that returns ToolResponseEnvelope with oracle suggestions

    Raises:
        TypeError: If decorating a non-async function
    """

    def decorator(func: F) -> F:
        # Verify it's an async function
        if not asyncio.iscoroutinefunction(func):
            raise TypeError(
                f"@with_oracle_resilience can only decorate async functions. "
                f"Got {func.__name__} which is not async."
            )

        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> ToolResponseEnvelope:
            started = time.perf_counter()

            try:
                # Call the original tool function
                result = await func(*args, **kwargs)

                # [20260201_BUGFIX] Two-stage post-processing for error envelopes
                # Stage 2a: Check envelope.error field
                if isinstance(result, ToolResponseEnvelope) and result.error:
                    enhanced = _enhance_error_envelope(
                        result, tool_id, strategy, kwargs, started
                    )
                    if enhanced:
                        return enhanced

                # [20260201_BUGFIX] Stage 2b: Check data.error field (tools that return
                # errors in response.data instead of response.error)
                # NOTE: Use model_dump() to access the actual envelope.error field,
                # because result.error might delegate to data["error"] via __getattr__
                envelope_dict = result.model_dump()
                if (
                    isinstance(result, ToolResponseEnvelope)
                    and envelope_dict.get("error") is None
                ):
                    enhanced = _enhance_data_error(
                        result, tool_id, strategy, kwargs, started
                    )
                    if enhanced:
                        return enhanced

                return result

            except ValidationError as ve:
                # Oracle intercepts ValidationError (direct exception)
                logger.info(f"Oracle: Intercepted ValidationError in {tool_id}")
                logger.debug(f"  Error: {ve}")

                # Build context from kwargs for strategy
                context = {
                    "file_path": _extract_path_from_kwargs(kwargs),
                    "code": kwargs.get("code"),
                    "symbol_name": kwargs.get("target_name"),
                    "new_name": kwargs.get("new_name"),
                }

                # Generate suggestions using strategy
                suggestions = strategy.suggest(ve, context)

                # Build user-friendly error message
                error_msg = str(ve)
                if suggestions:
                    suggestion_names = [
                        s.get("symbol") or s.get("path") or s.get("hint", "")
                        for s in suggestions
                        if s.get("symbol") or s.get("path") or s.get("hint")
                    ]
                    if suggestion_names:
                        error_msg = f"{str(ve)} Did you mean: {', '.join(suggestion_names[:3])}?"

                duration_ms = int((time.perf_counter() - started) * 1000)
                tier = _get_current_tier()

                # Return correction_needed envelope
                return make_envelope(
                    data=None,
                    tool_id=tool_id,
                    tool_version=_pkg_version,
                    tier=tier,
                    duration_ms=duration_ms,
                    error=ToolError(
                        error=error_msg,
                        error_code="correction_needed",
                        error_details={
                            "suggestions": suggestions,
                            "hint": error_msg,
                        },
                    ),
                )

            except FileNotFoundError as fnf:
                # Oracle intercepts FileNotFoundError (direct exception)
                logger.info(f"Oracle: Intercepted FileNotFoundError in {tool_id}")
                logger.debug(f"  Error: {fnf}")

                # Extract file path from context or error message
                file_path = _extract_path_from_kwargs(kwargs)
                if not file_path:
                    # Try to extract from error message
                    error_str = str(fnf)
                    if ":" in error_str:
                        file_path = error_str.split(":")[0].strip("'\" ")

                context = {"file_path": file_path}

                # Use PathStrategy
                suggestions = PathStrategy.suggest(fnf, context)

                # Build user-friendly error message
                error_msg = str(fnf)
                if suggestions:
                    suggestion_paths = [
                        s.get("path") for s in suggestions if s.get("path")
                    ]
                    if suggestion_paths:
                        error_msg = f"{str(fnf)} Did you mean: {suggestion_paths[0]}?"

                duration_ms = int((time.perf_counter() - started) * 1000)
                tier = _get_current_tier()

                return make_envelope(
                    data=None,
                    tool_id=tool_id,
                    tool_version=_pkg_version,
                    tier=tier,
                    duration_ms=duration_ms,
                    error=ToolError(
                        error=error_msg,
                        error_code="correction_needed",
                        error_details={
                            "suggestions": suggestions,
                            "hint": error_msg,
                        },
                    ),
                )

            except Exception as exc:
                # Pass through other exceptions to tool's normal error handling
                logger.debug(
                    f"Oracle: Not intercepting {type(exc).__name__} in {tool_id}"
                )
                raise

        return wrapper  # type: ignore

    return decorator


def _enhance_error_envelope(
    envelope: ToolResponseEnvelope,
    tool_id: str,
    strategy: type[RecoveryStrategy],
    kwargs: dict,
    started: float,
) -> ToolResponseEnvelope | None:
    """Post-process error envelopes to add oracle suggestions.

    This handles cases where the tool catches an error and returns an envelope
    with error info already set. We check if it's a correctable error and
    add suggestions.

    Args:
        envelope: The tool response envelope with error
        tool_id: Tool ID for logging
        strategy: Recovery strategy to use
        kwargs: Original tool kwargs
        started: Start time for duration calculation

    Returns:
        Enhanced envelope with suggestions, or None if not correctable
    """
    if not envelope.error:
        return None

    # Safely extract error message
    if isinstance(envelope.error, ToolError):
        error_msg = envelope.error.error or ""
    elif isinstance(envelope.error, str):
        error_msg = envelope.error
    else:
        error_msg = str(envelope.error)

    # Check if this looks like a symbol not found error
    if "not found" in error_msg.lower() and any(
        word in error_msg.lower() for word in ["symbol", "function", "class", "method"]
    ):
        logger.info(f"Oracle: Post-processing symbol error in {tool_id}")

        context = {
            "file_path": kwargs.get("file_path"),
            "code": kwargs.get("code"),
            "symbol_name": kwargs.get("target_name"),
        }

        # Create a fake ValidationError for the strategy
        error = ValidationError(error_msg)
        suggestions = strategy.suggest(error, context)

        if suggestions:
            # Enhance the error with suggestions
            enhanced_msg = error_msg
            suggestion_names = [
                s.get("symbol") or s.get("path") or s.get("hint", "")
                for s in suggestions
                if s.get("symbol") or s.get("path") or s.get("hint")
            ]
            if suggestion_names:
                enhanced_msg = (
                    f"{error_msg} Did you mean: {', '.join(suggestion_names[:3])}?"
                )

            # Update error code and details
            enhanced_error = ToolError(
                error=enhanced_msg,
                error_code="correction_needed",
                error_details={
                    "suggestions": suggestions,
                    "hint": enhanced_msg,
                },
            )

            # Return a new envelope with updated error
            duration_ms = int((time.perf_counter() - started) * 1000)
            tier = _get_current_tier()

            return make_envelope(
                data=envelope.data,
                tool_id=tool_id,
                tool_version=_pkg_version,
                tier=tier,
                duration_ms=duration_ms,
                error=enhanced_error,
            )

    return None


def _enhance_data_error(
    envelope: ToolResponseEnvelope,
    tool_id: str,
    strategy: type[RecoveryStrategy],
    kwargs: dict,
    started: float,
) -> ToolResponseEnvelope | None:
    """Post-process envelopes where error is in data.error field (Stage 2b).

    [20260201_BUGFIX] Some tools return errors in response.data.error instead of
    response.error. This function handles that case by checking data.error and
    enhancing the envelope when correctable errors are found.

    Args:
        envelope: The tool response envelope (with error possibly in data.error)
        tool_id: Tool ID for logging
        strategy: Recovery strategy to use
        kwargs: Original tool kwargs
        started: Start time for duration calculation

    Returns:
        Enhanced envelope with suggestions, or None if not correctable
    """
    # Check if data is a dict with an error field
    if not envelope.data or not isinstance(envelope.data, dict):
        return None

    data_error = envelope.data.get("error")
    if not data_error or not isinstance(data_error, str):
        return None

    # Also check for success=False pattern
    if envelope.data.get("success") is not False:
        return None

    error_msg = data_error
    logger.debug(f"Oracle: Checking data.error field in {tool_id}: {error_msg[:100]}")

    # Check if this looks like a correctable error (symbol or path not found)
    is_symbol_error = "not found" in error_msg.lower() and any(
        word in error_msg.lower() for word in ["symbol", "function", "class", "method"]
    )
    is_path_error = any(
        phrase in error_msg.lower()
        for phrase in ["cannot access file", "file not found", "no such file", "path"]
    )

    if not is_symbol_error and not is_path_error:
        return None

    logger.info(f"Oracle: Post-processing data.error in {tool_id}")

    # Build context for strategy
    context = {
        "file_path": _extract_path_from_kwargs(kwargs),
        "code": kwargs.get("code"),
        "symbol_name": kwargs.get("target_name") or kwargs.get("symbol_name"),
    }

    # Create a fake error for the strategy
    if is_symbol_error:
        error = ValidationError(error_msg)
    else:
        error = FileNotFoundError(error_msg)

    suggestions = strategy.suggest(error, context)

    if suggestions:
        # Enhance the error message with suggestions
        suggestion_names = [
            s.get("symbol") or s.get("path") or s.get("hint", "")
            for s in suggestions
            if s.get("symbol") or s.get("path") or s.get("hint")
        ]
        enhanced_msg = error_msg
        if suggestion_names:
            enhanced_msg = (
                f"{error_msg} Did you mean: {', '.join(suggestion_names[:3])}?"
            )

        # Create enhanced error in envelope.error (proper location)
        enhanced_error = ToolError(
            error=enhanced_msg,
            error_code="correction_needed",
            error_details={
                "suggestions": suggestions,
                "hint": enhanced_msg,
                "original_location": "data.error",
            },
        )

        duration_ms = int((time.perf_counter() - started) * 1000)
        tier = _get_current_tier()

        # Return new envelope with error promoted to envelope.error
        # Keep data but mark it as having been enhanced
        enhanced_data = dict(envelope.data)
        enhanced_data["_oracle_enhanced"] = True

        return make_envelope(
            data=enhanced_data,
            tool_id=tool_id,
            tool_version=_pkg_version,
            tier=tier,
            duration_ms=duration_ms,
            error=enhanced_error,
        )

    return None


class GenerateTestsStrategy(RecoveryStrategy):
    """Recovery strategy for generate_unit_tests tool.

    Combines PathStrategy for file_path and SymbolStrategy for function_name
    validation in test generation operations.
    """

    @staticmethod
    def suggest(error: Exception, context: dict[str, Any]) -> list[dict[str, Any]]:
        """Detect file path or function name errors and suggest corrections.

        Args:
            error: The exception that was raised
            context: Context dict with 'file_path' and 'function_name'

        Returns:
            Combined suggestions from both path and symbol validation
        """
        all_suggestions = []

        # Check file_path first (PathStrategy)
        if context.get("file_path"):
            path_suggestions = PathStrategy.suggest(error, context)
            all_suggestions.extend(path_suggestions)

        # Check function_name (SymbolStrategy)
        if context.get("function_name"):
            symbol_context = {
                "file_path": context.get("file_path"),
                "code": context.get("code"),
                "symbol_name": context.get("function_name"),
            }
            symbol_suggestions = SymbolStrategy.suggest(error, symbol_context)
            all_suggestions.extend(symbol_suggestions)

        # Deduplicate and rank
        return CompositeStrategy._rank_and_dedupe(all_suggestions)


__all__ = [
    "RecoveryStrategy",
    "SymbolStrategy",
    "PathStrategy",
    "SafetyStrategy",
    "NodeIdFormatStrategy",
    "MethodNameFormatStrategy",
    "RenameSymbolStrategy",
    "GenerateTestsStrategy",
    "CompositeStrategy",
    "with_oracle_resilience",
]
