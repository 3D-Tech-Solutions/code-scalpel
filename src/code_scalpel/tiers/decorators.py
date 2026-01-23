"""
Tier Decorators - Function decorators for tier-gated features.

[20251225_FEATURE] Created as part of Project Reorganization Issue #5.

Provides the @requires_tier decorator for enforcing tier requirements
at runtime on functions and methods.
"""

from __future__ import annotations

import functools
import logging
from collections.abc import Callable
from enum import Enum
from typing import Any, TypeVar

logger = logging.getLogger(__name__)


# [20251225_BUGFIX] Local Tier enum for runtime checks (avoid circular import)
class Tier(Enum):
    """License tier levels for Code Scalpel."""

    COMMUNITY = "Community"
    PRO = "Pro"
    ENTERPRISE = "Enterprise"


# Type variable for decorated functions
F = TypeVar("F", bound=Callable[..., Any])


class TierRequirementError(Exception):
    """Raised when a function is called without required tier access."""

    def __init__(self, feature_name: str, required_tier: str, current_tier: str):
        self.feature_name = feature_name
        self.required_tier = required_tier
        self.current_tier = current_tier

        message = (
            f"Feature '{feature_name}' requires {required_tier.upper()} tier. "
            f"Current tier: {current_tier.upper()}. "
            f"Upgrade at https://code-scalpel.dev/pricing"
        )
        super().__init__(message)


def _get_current_tier() -> str:
    """Get the current tier (lazy import to avoid circular deps)."""
    from code_scalpel.licensing import get_current_tier

    return get_current_tier()


def _tier_level(tier: str) -> int:
    """Get numeric level for tier comparison."""
    levels = {"community": 0, "pro": 1, "enterprise": 2}
    return levels.get(tier.lower(), 0)


def requires_tier(
    tier: str | Tier,  # Accept Tier enum or string
    feature_name: str | None = None,
    graceful: bool = False,
    fallback: Any = None,
) -> Callable[[F], F]:
    """
    Decorator that restricts a function to users with the specified tier or higher.

    Args:
        tier: Minimum required tier ("community", "pro", "enterprise" or Tier enum)
        feature_name: Optional name for error messages (defaults to function name)
        graceful: If True, return fallback instead of raising error
        fallback: Value to return when graceful=True and tier requirement not met

    Usage:
        @requires_tier("pro")
        def advanced_feature():
            # Only runs for PRO or ENTERPRISE users
            pass

        @requires_tier("enterprise", graceful=True, fallback=None)
        def enterprise_only():
            # Returns None for non-enterprise users
            pass

    Raises:
        TierRequirementError: If tier requirement not met and graceful=False
    """
    # Convert Tier enum to string if needed (use hasattr for duck typing)
    tier_str: str = getattr(tier, "value", str(tier)).lower()

    def decorator(func: F) -> F:
        name = feature_name or func.__name__

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            current = _get_current_tier()
            required_level = _tier_level(tier_str)
            current_level = _tier_level(current)

            if current_level >= required_level:
                return func(*args, **kwargs)

            # Tier requirement not met
            if graceful:
                logger.info(
                    f"Feature '{name}' requires {tier_str.upper()} tier "
                    f"(current: {current.upper()}), returning fallback"
                )
                return fallback

            raise TierRequirementError(name, tier_str, current)

        # Async support
        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            current = _get_current_tier()
            required_level = _tier_level(tier_str)
            current_level = _tier_level(current)

            if current_level >= required_level:
                return await func(*args, **kwargs)

            if graceful:
                logger.info(
                    f"Feature '{name}' requires {tier_str.upper()} tier "
                    f"(current: {current.upper()}), returning fallback"
                )
                return fallback

            raise TierRequirementError(name, tier_str, current)

        # Return appropriate wrapper based on function type
        import asyncio

        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        return wrapper  # type: ignore

    return decorator


def requires_feature(
    feature_name: str,
    graceful: bool = False,
    fallback: Any = None,
) -> Callable[[F], F]:
    """
    Decorator that restricts a function based on feature registry.

    Looks up the feature in FeatureRegistry to determine required tier.

    Args:
        feature_name: Name of the feature in the registry
        graceful: If True, return fallback instead of raising error
        fallback: Value to return when graceful=True and feature not available

    Usage:
        @requires_feature("security_scan")
        def run_security_scan():
            pass
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            from .feature_registry import get_feature_tier, is_feature_enabled

            if is_feature_enabled(feature_name):
                return func(*args, **kwargs)

            if graceful:
                logger.info(f"Feature '{feature_name}' not enabled, returning fallback")
                return fallback

            required_tier = get_feature_tier(feature_name)
            current = _get_current_tier()
            raise TierRequirementError(feature_name, required_tier, current)

        return wrapper  # type: ignore

    return decorator
