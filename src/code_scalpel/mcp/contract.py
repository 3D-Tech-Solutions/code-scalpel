"""MCP response contract utilities.

This module implements the V1.0 production contract requirements from
`docs/guides/production_release_v1.0.md`:
- Universal response envelope for all tools
- Stable, machine-parseable error codes

The intent is to enforce the contract at the MCP tool boundary so individual
tool implementations can remain focused on their domain logic.
"""

from __future__ import annotations

import inspect
import sys
import time
import uuid
from collections.abc import Awaitable, Callable
from typing import Any, Literal

from pydantic import BaseModel, Field

# [20260121_FEATURE] Response config integration for token-efficient outputs
from code_scalpel.mcp.response_config import (
    filter_tool_response,
    get_response_config,
)


class UpgradeRequiredError(RuntimeError):
    """Raised when a caller requests a capability unavailable at current tier.

    [20251228_FEATURE] Enables structured upgrade-required errors.
    [20260112_REFACTOR] Removed upgrade_url from message - hints belong in docs only.
    """

    def __init__(
        self,
        *,
        tool_id: str,
        feature: str,
        required_tier: str,
        upgrade_url: str | None = None,  # Deprecated, kept for backwards compat
        message: str | None = None,
    ) -> None:
        if message is None:
            message = f"Feature '{feature}' requires {required_tier.upper()} tier."
        super().__init__(message)
        self.tool_id = tool_id
        self.feature = feature
        self.required_tier = required_tier
        self.upgrade_url = upgrade_url  # Deprecated - do not use in new code


ErrorCode = Literal[
    "invalid_argument",
    "invalid_path",
    "forbidden",
    "not_found",
    "timeout",
    "too_large",
    "resource_exhausted",
    "not_implemented",
    "upgrade_required",
    "dependency_unavailable",
    "internal_error",
]


class UpgradeHint(BaseModel):
    feature: str = Field(description="What is unlocked")
    tier: str = Field(description="Tier that unlocks it")
    reason: str = Field(description="Why it is unavailable at current tier")


class ToolError(BaseModel):
    error: str = Field(description="Human-readable error message")
    error_code: ErrorCode = Field(description="Machine-parseable error code")
    error_details: dict[str, Any] | None = Field(
        default=None,
        description="Optional structured details safe for clients; never include code contents",
    )


class ToolResponseEnvelope(BaseModel):
    tier: str | None = Field(
        default=None,
        description="One of: community, pro, enterprise (omitted by default for token efficiency)",
    )
    tier_applied: str | None = Field(
        default=None,
        description="[20260122_FEATURE] Actual tier applied during invocation for metadata tracking",
    )
    files_limit_applied: int | None = Field(
        default=None,
        description="[20260122_FEATURE] File count limit enforced at this tier",
    )
    rules_limit_applied: int | None = Field(
        default=None,
        description="[20260122_FEATURE] Rule count limit enforced at this tier",
    )
    tool_version: str | None = Field(
        default=None,
        description="Semantic version of tool implementation (omitted by default)",
    )
    tool_id: str | None = Field(
        default=None,
        description="Canonical MCP tool ID (omitted by default - client knows which tool was called)",
    )
    request_id: str | None = Field(
        default=None,
        description="Correlation ID (omitted by default unless client-provided)",
    )
    capabilities: list[str] | None = Field(
        default=None,
        description="Capabilities for this invocation (omitted by default)",
    )
    duration_ms: int | None = Field(
        default=None,
        description="End-to-end runtime in milliseconds (omitted by default)",
    )
    error: ToolError | None = Field(
        default=None,
        description="Standardized error model (only included when error occurs)",
    )
    upgrade_hints: list[UpgradeHint] | None = Field(
        default=None,
        description="Upgrade hints when a feature is unavailable at this tier (only included when hints exist)",
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="Non-fatal warnings emitted by the MCP boundary (e.g., governance WARN mode)",
    )
    data: Any | None = Field(default=None, description="Tool-specific payload")

    # [20260121_FEATURE] Transparent attribute forwarding for test compatibility
    # [20260122_BUGFIX] Preserve legacy stringy error access while keeping structured ToolError.
    def __getattribute__(self, name: str) -> Any:
        if name == "error_model":  # Access structured ToolError when needed
            return super().__getattribute__("__dict__").get("error")

        if name == "error":
            env_error = super().__getattribute__("__dict__").get("error")
            if isinstance(env_error, ToolError):
                return env_error.error
            if env_error is not None:
                return env_error
            data_payload = super().__getattribute__("__dict__").get("data")
            if isinstance(data_payload, dict) and "error" in data_payload:
                return data_payload.get("error")
            if hasattr(data_payload, "error"):
                try:
                    return data_payload.error
                except Exception:
                    return None
            return None

        return super().__getattribute__(name)

    def __getattr__(self, name: str) -> Any:
        """Forward attribute access to data payload for test compatibility.

        Allows tests to access result.success instead of result.data['success']
        or result.data.success. Handles both dict and Pydantic model payloads.
        """

        if name in {
            "data",
            "tier",
            "tier_applied",
            "files_limit_applied",
            "rules_limit_applied",
            "tool_version",
            "tool_id",
            "request_id",
            "capabilities",
            "duration_ms",
            "error",
            "upgrade_hints",
            "warnings",
            "error_model",
        }:
            # These are envelope fields - use default behavior
            return object.__getattribute__(self, name)

        # Try to get from data payload
        data = object.__getattribute__(self, "data")

        # Handle dict payloads
        if isinstance(data, dict) and name in data:
            return data[name]

        # [20260121_BUGFIX] Handle Pydantic model payloads
        if hasattr(data, name):
            return getattr(data, name)

        # Fall back to default behavior (raises AttributeError)
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")


def _classify_exception(exc: BaseException) -> ErrorCode:
    # Keep classification conservative; do not leak details.
    if isinstance(exc, UpgradeRequiredError):
        return "upgrade_required"
    if isinstance(exc, (ValueError, TypeError)):
        return "invalid_argument"
    if isinstance(exc, FileNotFoundError):
        return "not_found"
    if isinstance(exc, PermissionError):
        return "forbidden"
    if isinstance(exc, (TimeoutError,)):
        return "timeout"
    # asyncio.TimeoutError is a subclass of TimeoutError in modern Python, but keep safe.
    if exc.__class__.__name__ in {"TimeoutError", "CancelledError"}:
        return "timeout"
    if isinstance(exc, NotImplementedError):
        return "not_implemented"
    if isinstance(exc, MemoryError):
        return "resource_exhausted"
    return "internal_error"


def _maybe_get_success_and_error(payload: Any) -> tuple[bool | None, str | None]:
    """Best-effort introspection of existing tool payloads.

    Many tools in this repo return Pydantic models that include `success` and `error`.
    Some tools return dicts without `success`.
    """

    try:
        # [20260122_BUGFIX] Honor ToolError payloads (common in failure paths)
        if isinstance(payload, ToolError):
            return False, payload.error
        if isinstance(payload, BaseModel):
            success = getattr(payload, "success", None)
            err = getattr(payload, "error", None)
            if success is None and err is not None:
                return False, err
            return (bool(success) if success is not None else None, err)
        if isinstance(payload, dict):
            success = payload.get("success")
            err = payload.get("error")
            return (bool(success) if success is not None else None, err)
    except Exception:
        return None, None
    return None, None


def _classify_failure_message(message: str | None) -> ErrorCode | None:
    if not message:
        return None
    lowered = message.lower()
    if "file not found" in lowered or "no such file" in lowered:
        return "not_found"
    if "not a file" in lowered or "must be" in lowered or "cannot be empty" in lowered:
        return "invalid_argument"
    if "invalid path" in lowered or "path traversal" in lowered:
        return "invalid_path"
    if "permission" in lowered or "forbidden" in lowered:
        return "forbidden"
    if "timeout" in lowered:
        return "timeout"
    if "requires pro tier" in lowered or "requires enterprise tier" in lowered:
        return "upgrade_required"
    if "upgrade:" in lowered or "upgrade at" in lowered:
        return "upgrade_required"
    if "too large" in lowered or "exceeds maximum" in lowered:
        return "too_large"
    if "not implemented" in lowered:
        return "not_implemented"
    return None


def make_envelope(
    data: Any,
    tool_id: str,
    tool_version: str,
    tier: str,
    duration_ms: int | None = None,
    error: ToolError | None = None,
    upgrade_hints: list[UpgradeHint] | None = None,
    warnings: list[str] | None = None,
    request_id: str | None = None,
) -> ToolResponseEnvelope:
    """[20260121_FEATURE] Create a ToolResponseEnvelope for internal tool use.

    This helper is called INSIDE tool functions (not at registration layer) to wrap
    results and metadata. This avoids FastMCP tool discovery issues that occur when
    wrapping at the decorator layer.

    Args:
        data: The tool's actual result payload
        tool_id: Canonical MCP tool ID (e.g., "analyze_code")
        tool_version: Semantic version (from __version__)
        tier: License tier ("community", "pro", "enterprise")
        duration_ms: Execution time in milliseconds (optional)
        error: Error object if tool failed (optional)
        upgrade_hints: Upgrade hints for tier features (optional)
        warnings: Non-fatal warnings (optional)
        request_id: Correlation ID (optional, generated if not provided)

    Returns:
        ToolResponseEnvelope with all metadata populated
    """
    if request_id is None:
        request_id = uuid.uuid4().hex

    # [20260121_FEATURE] Apply response_config filtering to envelope and data
    cfg = get_response_config()
    envelope_fields = cfg.get_envelope_fields(tool_id)

    # [20260122_BUGFIX] Don't convert Pydantic models to dicts - preserve model structure
    # Only filter dict payloads. Pydantic models are returned as-is to preserve
    # attribute access (e.g., ref.owners, f.path) which tests and clients expect.
    filtered_data = data
    try:
        is_error = error is not None
        if isinstance(data, dict):
            # Only filter dict payloads
            filtered_data = filter_tool_response(data, tool_name=tool_id, tier=tier, is_error=is_error)
        # elif isinstance(data, BaseModel):
        #     # Keep Pydantic models as-is to preserve attribute access
        #     filtered_data = data
    except Exception:
        # On filtering error, keep original data
        filtered_data = data

    # [20260122_BUGFIX] Auto-populate envelope error when payload reports failure
    if error is None:
        success, err_msg = _maybe_get_success_and_error(filtered_data)
        if success is False or isinstance(filtered_data, ToolError):
            classified = None
            if isinstance(filtered_data, ToolError):
                err_msg = filtered_data.error
                classified = filtered_data.error_code
            classified = classified or _classify_failure_message(err_msg) or "internal_error"
            error = ToolError(error=err_msg or "Tool failed", error_code=classified)

    # [20260121_BUGFIX] tier is license/server metadata, not configurable output
    # Always include tier field regardless of response_config profile
    # [20260122_FEATURE] Also set tier_applied for metadata tracking
    # Lightweight trace for debugging stdio invocations
    try:
        print(f"[MCP TRACE] make_envelope tool_id={tool_id} data_is_none={filtered_data is None}", file=sys.stderr)
    except Exception:
        pass
    try:
        if error is not None:
            # Print structured error for debugging intermittent tool failures
            try:
                print(f"[MCP TRACE] make_envelope error={error.error} code={error.error_code}", file=sys.stderr)
            except Exception:
                print(f"[MCP TRACE] make_envelope error={error}", file=sys.stderr)
    except Exception:
        pass

    return ToolResponseEnvelope(
        tier=tier,  # ALWAYS include tier (server metadata, not response content)
        tier_applied=tier,  # [20260122_FEATURE] Track which tier was applied during invocation
        tool_version=tool_version if "tool_version" in envelope_fields else None,
        tool_id=tool_id if "tool_id" in envelope_fields else None,
        request_id=request_id if "request_id" in envelope_fields else None,
        capabilities=(["envelope-v1"] if "capabilities" in envelope_fields else None),
        duration_ms=duration_ms if "duration_ms" in envelope_fields else None,
        error=error,  # Always include errors; clients expect them
        upgrade_hints=(upgrade_hints or []) if "upgrade_hints" in envelope_fields else None,
        warnings=warnings or [],
        data=filtered_data,
    )


def envelop_tool_function(
    fn: Callable[..., Any] | Callable[..., Awaitable[Any]],
    *,
    tool_id: str,
    tool_version: str,
    tier_getter: Callable[[], str],
) -> Callable[..., Awaitable[ToolResponseEnvelope]]:
    """Wrap an MCP tool function to always return a ToolResponseEnvelope.

    Preserves the original function signature (via __signature__) so FastMCP can
    generate the same JSON schema for inputs.
    """

    sig = inspect.signature(fn)

    async def _wrapped(*args: Any, **kwargs: Any) -> ToolResponseEnvelope:
        started = time.perf_counter()
        request_id = uuid.uuid4().hex
        tier = (tier_getter() or "enterprise").strip().lower()

        # If the tool received a Context, try to use its request id if available.
        ctx = kwargs.get("ctx")
        for candidate in ("request_id", "requestId", "correlation_id", "correlationId"):
            if ctx is not None and hasattr(ctx, candidate):
                try:
                    val = getattr(ctx, candidate)
                    if isinstance(val, str) and val.strip():
                        request_id = val.strip()
                        break
                except Exception:
                    pass

        try:
            result = fn(*args, **kwargs)
            if inspect.isawaitable(result):
                result = await result

            duration_ms = int((time.perf_counter() - started) * 1000)
            success, err_msg = _maybe_get_success_and_error(result)

            error_obj: ToolError | None = None
            if success is False:
                code = _classify_failure_message(err_msg) or "internal_error"
                error_obj = ToolError(error=err_msg or "Tool failed", error_code=code)

            return ToolResponseEnvelope(
                tier=tier,
                tool_version=tool_version,
                tool_id=tool_id,
                request_id=request_id,
                capabilities=["envelope-v1"],
                duration_ms=duration_ms,
                error=error_obj,
                upgrade_hints=[],
                data=result,
            )
        except BaseException as exc:  # noqa: BLE001
            duration_ms = int((time.perf_counter() - started) * 1000)
            code = _classify_exception(exc)
            return ToolResponseEnvelope(
                tier=tier,
                tool_version=tool_version,
                tool_id=tool_id,
                request_id=request_id,
                capabilities=["envelope-v1"],
                duration_ms=duration_ms,
                error=ToolError(error=str(exc) or "Tool error", error_code=code),
                upgrade_hints=[],
                data=None,
            )

    # Strip annotations from signature to avoid Pydantic forward-ref issues
    try:
        import inspect as _inspect

        _clean_params = [p.replace(annotation=_inspect._empty) for p in sig.parameters.values()]
        _wrapped.__signature__ = sig.replace(parameters=tuple(_clean_params), return_annotation=_inspect._empty)  # type: ignore[attr-defined]
    except Exception:
        _wrapped.__signature__ = sig  # type: ignore[attr-defined]

    # [20260121_BUGFIX] Ensure MCP tool registration uses canonical tool_id for name
    # FastMCP defaults to function __name__ for tool discovery; set to tool_id.
    _wrapped.__name__ = tool_id
    _wrapped.__qualname__ = tool_id
    _wrapped.__doc__ = getattr(fn, "__doc__", None)
    _wrapped.__module__ = getattr(fn, "__module__", __name__)

    # To avoid Pydantic v2 forward-ref issues under future annotations,
    # expose minimal, safe annotation state.
    try:
        # Prefer empty annotations; FastMCP will still infer parameters from the signature.
        _wrapped.__annotations__ = {}
    except Exception:
        pass

    # Copy __globals__ so Pydantic can resolve any typing symbols if needed
    if hasattr(fn, "__globals__"):
        try:
            _wrapped.__globals__.update(fn.__globals__)  # type: ignore[attr-defined]
        except Exception:
            pass

    # Ensure common typing symbols exist in globals for safety
    try:
        from typing import Any as _Any
        from typing import Optional as _Optional
        from typing import Union as _Union

        _wrapped.__globals__.setdefault("Optional", _Optional)
        _wrapped.__globals__.setdefault("Union", _Union)
        _wrapped.__globals__.setdefault("Any", _Any)
    except Exception:
        pass

    return _wrapped
