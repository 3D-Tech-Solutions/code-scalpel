"""
Feature Registry - Central registry of features and their tier requirements.

[20251225_FEATURE] Created as part of Project Reorganization Issue #5.

Provides a central registry mapping features to their minimum required tiers.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class Feature:
    """Definition of a Code Scalpel feature."""

    name: str
    tier: str  # "community", "pro", "enterprise"
    description: str = ""
    category: str = "general"
    deprecated: bool = False
    beta: bool = False
    metadata: dict[str, str] = field(default_factory=dict)


# [20251225_FEATURE] Default feature registry
# All features and their minimum required tiers
DEFAULT_FEATURES: dict[str, Feature] = {
    # COMMUNITY features (always available)
    "analyze_code": Feature(
        name="analyze_code",
        tier="community",
        description="Parse and analyze code structure",
        category="analysis",
    ),
    "extract_code": Feature(
        name="extract_code",
        tier="community",
        description="Surgical code extraction by symbol name",
        category="surgery",
    ),
    "update_symbol": Feature(
        name="update_symbol",
        tier="community",
        description="Safe symbol replacement in files",
        category="surgery",
    ),
    "crawl_project": Feature(
        name="crawl_project",
        tier="community",
        description="Project-wide code analysis",
        category="analysis",
    ),
    "get_file_context": Feature(
        name="get_file_context",
        tier="community",
        description="Get surrounding context for code",
        category="analysis",
    ),
    "get_symbol_references": Feature(
        name="get_symbol_references",
        tier="community",
        description="Find all references to a symbol",
        category="analysis",
    ),
    "get_call_graph": Feature(
        name="get_call_graph",
        tier="community",
        description="Generate call graphs",
        category="analysis",
    ),
    "get_project_map": Feature(
        name="get_project_map",
        tier="community",
        description="Generate project structure map",
        category="analysis",
    ),
    "validate_paths": Feature(
        name="validate_paths",
        tier="community",
        description="Validate path accessibility",
        category="utilities",
    ),
    "security_scan": Feature(
        name="security_scan",
        tier="community",
        description="Taint-based vulnerability detection",
        category="security",
    ),
    "unified_sink_detect": Feature(
        name="unified_sink_detect",
        tier="community",
        description="Polyglot sink detection",
        category="security",
    ),
    "symbolic_execute": Feature(
        name="symbolic_execute",
        tier="community",
        description="Symbolic execution analysis",
        category="analysis",
    ),
    "generate_unit_tests": Feature(
        name="generate_unit_tests",
        tier="community",
        description="Test generation from symbolic paths",
        category="testing",
    ),
    "simulate_refactor": Feature(
        name="simulate_refactor",
        tier="community",
        description="Refactor behavior verification",
        category="surgery",
    ),
    "scan_dependencies": Feature(
        name="scan_dependencies",
        tier="community",
        description="Dependency vulnerability scanning",
        category="security",
    ),
    "get_cross_file_dependencies": Feature(
        name="get_cross_file_dependencies",
        tier="community",
        description="Cross-file dependency analysis",
        category="analysis",
    ),
    "get_graph_neighborhood": Feature(
        name="get_graph_neighborhood",
        tier="community",
        description="Extract graph neighborhood",
        category="analysis",
    ),
    "cross_file_security_scan": Feature(
        name="cross_file_security_scan",
        tier="community",
        description="Cross-module taint tracking",
        category="security",
    ),
    "verify_policy_integrity": Feature(
        name="verify_policy_integrity",
        tier="community",
        description="Cryptographic policy verification",
        category="governance",
    ),
    "type_evaporation_scan": Feature(
        name="type_evaporation_scan",
        tier="community",
        description="TypeScript type evaporation detection",
        category="security",
    ),
    "autonomous_repair": Feature(
        name="autonomous_repair",
        tier="community",
        description="Supervised autonomous code repair",
        category="autonomy",
    ),
    "compliance_report": Feature(
        name="compliance_report",
        tier="community",
        description="Compliance and audit reporting",
        category="governance",
    ),
}

# Tier hierarchy for comparison
TIER_LEVELS = {
    "community": 0,
    "pro": 1,
    "enterprise": 2,
}


class FeatureRegistry:
    """
    Central registry of Code Scalpel features and their tier requirements.

    Usage:
        registry = FeatureRegistry()

        # Check if feature is available
        if registry.is_enabled("security_scan"):
            pass

        # Get all available features
        features = registry.get_available_features()
    """

    def __init__(self, features: dict[str, Feature] | None = None):
        """
        Initialize the registry.

        Args:
            features: Optional custom feature definitions
        """
        self._features = dict(features or DEFAULT_FEATURES)

    def is_enabled(self, feature_name: str) -> bool:
        """
        Check if a feature is enabled at the current tier.

        Args:
            feature_name: Name of the feature

        Returns:
            True if feature is available
        """
        feature = self._features.get(feature_name)
        if not feature:
            logger.warning(f"Unknown feature: {feature_name}")
            return False

        from code_scalpel.licensing import get_current_tier

        current_tier = get_current_tier()

        current_level = TIER_LEVELS.get(current_tier, 0)
        required_level = TIER_LEVELS.get(feature.tier, 0)

        return current_level >= required_level

    def get_tier(self, feature_name: str) -> str:
        """
        Get the minimum required tier for a feature.

        Args:
            feature_name: Name of the feature

        Returns:
            Tier string or "unknown" if not found
        """
        feature = self._features.get(feature_name)
        if not feature:
            return "unknown"
        return feature.tier

    def get_feature(self, feature_name: str) -> Feature | None:
        """Get feature definition by name."""
        return self._features.get(feature_name)

    def get_available_features(self) -> list[Feature]:
        """Get all features available at the current tier."""
        from code_scalpel.licensing import get_current_tier

        current_tier = get_current_tier()
        current_level = TIER_LEVELS.get(current_tier, 0)

        available = []
        for feature in self._features.values():
            required_level = TIER_LEVELS.get(feature.tier, 0)
            if current_level >= required_level:
                available.append(feature)

        return sorted(available, key=lambda f: f.name)

    def get_unavailable_features(self) -> list[Feature]:
        """Get features NOT available at the current tier."""
        from code_scalpel.licensing import get_current_tier

        current_tier = get_current_tier()
        current_level = TIER_LEVELS.get(current_tier, 0)

        unavailable = []
        for feature in self._features.values():
            required_level = TIER_LEVELS.get(feature.tier, 0)
            if current_level < required_level:
                unavailable.append(feature)

        return sorted(unavailable, key=lambda f: (f.tier, f.name))

    def get_features_by_tier(self, tier: str) -> list[Feature]:
        """Get all features that require exactly the specified tier."""
        return [f for f in self._features.values() if f.tier == tier]

    def get_features_by_category(self, category: str) -> list[Feature]:
        """Get all features in a category."""
        return [f for f in self._features.values() if f.category == category]

    def register(self, feature: Feature) -> None:
        """Register a new feature."""
        self._features[feature.name] = feature
        logger.debug(f"Registered feature: {feature.name}")

    def list_all(self) -> list[str]:
        """List all feature names."""
        return sorted(self._features.keys())


# [20251225_FEATURE] Global registry instance
_registry: FeatureRegistry | None = None


def get_registry() -> FeatureRegistry:
    """Get the global feature registry."""
    global _registry
    if _registry is None:
        _registry = FeatureRegistry()
    return _registry


def is_feature_enabled(feature_name: str) -> bool:
    """Check if a feature is enabled at the current tier."""
    return get_registry().is_enabled(feature_name)


def get_feature_tier(feature_name: str) -> str:
    """Get the minimum required tier for a feature."""
    return get_registry().get_tier(feature_name)
