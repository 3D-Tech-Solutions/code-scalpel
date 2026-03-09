"""
Feature Capabilities - Hierarchical feature gating for all MCP tools.

[20251225_FEATURE] Implements parameter-level feature gating instead of tool-level hiding.
[20260205_REFACTOR] Externalised TOOL_CAPABILITIES into features.toml + limits.toml.
                    This module is now a thin loader that assembles envelopes from the
                    two bundled TOML files via config_loader.

Architecture:
    - All 22 MCP tools available at all tiers
    - Capabilities (feature sets) loaded from features.toml
    - Limits (numeric thresholds, flags) loaded from limits.toml
    - get_tool_capabilities() assembles both into one envelope per call
    - -1 sentinel in TOML is converted to None at runtime

Usage:
    from code_scalpel.licensing.features import get_tool_capabilities

    caps = get_tool_capabilities("security_scan", "community")
    if "full_vulnerability_list" in caps["capabilities"]:
        # Show all findings
    else:
        # Limit to caps["limits"]["max_findings"]
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Canonical tool-ID list (22 tools).  Kept here as a single source of truth
# for iteration / validation.  The capability and limit data itself lives in
# src/code_scalpel/capabilities/features.toml and limits.toml respectively.
# ---------------------------------------------------------------------------
ALL_TOOLS: List[str] = [
    "analyze_code",
    "code_policy_check",
    "crawl_project",
    "cross_file_security_scan",
    "extract_code",
    "generate_unit_tests",
    "get_call_graph",
    "get_cross_file_dependencies",
    "get_file_context",
    "get_graph_neighborhood",
    "get_project_map",
    "get_symbol_references",
    "rename_symbol",
    "scan_dependencies",
    "security_scan",
    "simulate_refactor",
    "symbolic_execute",
    "type_evaporation_scan",
    "unified_sink_detect",
    "update_symbol",
    "validate_paths",
    "verify_policy_integrity",
]


class _ToolCapabilitiesProxy(dict):
    """Lazy-loading dict shim that reconstructs the legacy TOOL_CAPABILITIES
    structure ``{tool_id: {tier: {enabled, capabilities, limits, description}}}``
    from the two TOML files on first access.

    This keeps ``from code_scalpel.licensing.features import TOOL_CAPABILITIES``
    working without change in assertion helpers and test adapters.
    """

    _TIERS = ("community", "pro", "enterprise")

    def _ensure_populated(self) -> None:
        if super().__len__() > 0:
            return  # already populated
        from .config_loader import get_cached_features, get_cached_limits

        features = get_cached_features()
        limits = get_cached_limits()
        for tool_id in ALL_TOOLS:
            tool_dict: Dict[str, Any] = {}
            for tier in self._TIERS:
                feat = features.get(tier, {}).get(tool_id, {})
                lim = limits.get(tier, {}).get(tool_id, {})
                if not feat and not lim:
                    continue
                caps_raw = feat.get("capabilities", [])
                tool_dict[tier] = {
                    "enabled": feat.get("enabled", True),
                    "capabilities": (
                        set(caps_raw) if isinstance(caps_raw, list) else set()
                    ),
                    "limits": _sanitise_limits(lim),
                    "description": feat.get("description", ""),
                }
            if tool_dict:
                super().__setitem__(tool_id, tool_dict)

    # -- dict protocol overrides that trigger population -------------------
    def __getitem__(self, key: str) -> Any:
        self._ensure_populated()
        return super().__getitem__(key)

    def __contains__(self, key: object) -> bool:
        self._ensure_populated()
        return super().__contains__(key)

    def __iter__(self):  # type: ignore[override]
        self._ensure_populated()
        return super().__iter__()

    def __len__(self) -> int:
        self._ensure_populated()
        return super().__len__()

    def keys(self):  # type: ignore[override]
        self._ensure_populated()
        return super().keys()

    def values(self):  # type: ignore[override]
        self._ensure_populated()
        return super().values()

    def items(self):  # type: ignore[override]
        self._ensure_populated()
        return super().items()

    def get(self, key: str, default: Any = None) -> Any:  # type: ignore[override]
        self._ensure_populated()
        return super().get(key, default)


# Backward-compatible module-level name.  Behaves exactly like the old
# hardcoded dict; populates itself lazily from features.toml + limits.toml
# on first access so that import-time cost is zero.
TOOL_CAPABILITIES: Dict[str, Dict[str, Dict[str, Any]]] = _ToolCapabilitiesProxy()


def _convert_sentinel(value: Any) -> Any:
    """Convert the UNLIMITED sentinel used in limits.toml to Python None.

    Convention: ``-1`` in limits.toml means UNLIMITED (annotated "# UNLIMITED"
    throughout that file).  Only bare integer -1 is converted; strings such as
    ``"all"`` and lists are passed through unchanged.
    """
    if isinstance(value, int) and value == -1:
        return None  # -1  →  UNLIMITED  →  None (no enforcement)
    return value


def _sanitise_limits(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Apply sentinel conversion to every value in a limits dict."""
    return {k: _convert_sentinel(v) for k, v in raw.items()}


def get_tool_capabilities(tool_id: str, tier: str) -> Dict[str, Any]:
    """
    Get capabilities and limits for a tool at a specific tier.

    Assembles the envelope from two TOML sources:
        - features.toml  -> enabled, capabilities (list -> set), description
        - limits.toml    -> limits dict (with -1 -> None conversion)

    Args:
        tool_id: MCP tool identifier
        tier: Tier level ("community", "pro", "enterprise")

    Returns:
        Dictionary with keys: enabled (bool), capabilities (set), limits (dict),
        description (str).  The shape is identical to the previous hardcoded dict.

    Example:
        caps = get_tool_capabilities("security_scan", "community")
        if "full_vulnerability_list" in caps["capabilities"]:
            # Show all findings
        else:
            # Limit to caps["limits"]["max_findings"]
    """
    from .config_loader import get_cached_features, get_cached_limits

    normalized_tier = tier.lower()

    # ── Features (enabled + capabilities + description) ──────────────────
    features_data: Dict[str, Dict[str, Any]] = {}
    try:
        all_features = get_cached_features()
        features_data = all_features.get(normalized_tier, {}).get(tool_id, {})
    except Exception as e:
        logger.debug("Failed to load features for %s/%s: %s", tool_id, tier, e)

    # ── Limits ────────────────────────────────────────────────────────────
    limits_data: Dict[str, Any] = {}
    try:
        all_limits = get_cached_limits()
        limits_data = all_limits.get(normalized_tier, {}).get(tool_id, {})
    except Exception as e:
        logger.debug("Failed to load limits for %s/%s: %s", tool_id, tier, e)

    # ── Fallback when neither TOML source has data ───────────────────────
    if not features_data and not limits_data:
        logger.warning("Unknown tool or tier: %s/%s", tool_id, tier)
        return {
            "enabled": True,
            "capabilities": set(),
            "limits": {},
            "description": "Unknown tool/tier",
        }

    # ── Assemble envelope ─────────────────────────────────────────────────
    enabled_raw = features_data.get("enabled", True)
    enabled: bool = bool(enabled_raw) if isinstance(enabled_raw, bool) else True
    raw_caps = features_data.get("capabilities", [])
    capabilities: Set[str] = set(raw_caps) if isinstance(raw_caps, list) else set()
    description_raw = features_data.get("description", "")
    description: str = str(description_raw) if isinstance(description_raw, str) else ""
    limits: Dict[str, Any] = _sanitise_limits(limits_data)

    return {
        "enabled": enabled,
        "capabilities": capabilities,
        "limits": limits,
        "description": description,
    }


def has_capability(tool_id: str, capability: str, tier: str) -> bool:
    """
    Check if a tool has a specific capability at a tier.

    Args:
        tool_id: MCP tool identifier
        capability: Capability name
        tier: Tier level

    Returns:
        True if capability is available
    """
    caps = get_tool_capabilities(tool_id, tier)
    return capability in caps.get("capabilities", set())


def get_upgrade_hint(
    tool_id: str, missing_capability: str, current_tier: str
) -> Optional[str]:
    """
    Generate upgrade hint for a missing capability.

    Args:
        tool_id: MCP tool identifier
        missing_capability: Capability user tried to use
        current_tier: Current tier level

    Returns:
        Upgrade hint message or None if capability not found in higher tiers
    """
    for tier in ["pro", "enterprise"]:
        if tier == current_tier:
            continue

        if has_capability(tool_id, missing_capability, tier):
            return (
                f"Feature '{missing_capability}' requires {tier.upper()} tier. "
                f"Current tier: {current_tier.upper()}. "
                f"Upgrade at http://codescalpel.dev/pricing"
            )

    return None


def get_all_tools_for_tier(tier: str) -> List[str]:
    """
    Get all tool IDs available at a tier.

    NOTE: This returns ALL tools since all tools are available at all tiers.
    Use get_tool_capabilities() to check feature restrictions.

    Args:
        tier: Tier level

    Returns:
        List of all tool IDs
    """
    return list(ALL_TOOLS)


def get_missing_capabilities(
    tool_id: str, current_tier: str, target_tier: str
) -> Set[str]:
    """
    Get capabilities available in target tier but not in current tier.

    Args:
        tool_id: MCP tool identifier
        current_tier: Current tier level
        target_tier: Target tier level

    Returns:
        Set of capability names
    """
    current_caps = get_tool_capabilities(tool_id, current_tier)
    target_caps = get_tool_capabilities(tool_id, target_tier)

    current_set = current_caps.get("capabilities", set())
    target_set = target_caps.get("capabilities", set())

    return target_set - current_set
