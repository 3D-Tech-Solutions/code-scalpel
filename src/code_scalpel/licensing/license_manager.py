"""
License Manager - Central license management for Code Scalpel.

[20251225_FEATURE] Tier-based licensing with feature availability checks,
license validation, expiration handling, seat counting, and custom terms.

Core Responsibilities:
- Detect and manage license tiers (community, pro, enterprise)
- Validate license keys and enforce expiration/grace periods
- Track feature availability based on current tier
- Manage concurrent user seats and organization hierarchies
- Persist license state and provide renewal reminders

Key Features:
- Feature registry with tier-based access control
- Thread-safe seat counting and concurrent user tracking
- 30-day grace period for expired licenses
- JSON-based state persistence
- Custom license terms and rules evaluation
"""

from __future__ import annotations

import json
import logging
import threading
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .tier_detector import TierDetector
from .validator import LicenseValidator, ValidationStatus

logger = logging.getLogger(__name__)


def _utcnow_naive() -> datetime:
    # [20251228_BUGFIX] Avoid deprecated datetime.utcnow() while preserving
    # existing naive-UTC behavior.
    return datetime.now(timezone.utc).replace(tzinfo=None)


@dataclass
class LicenseInfo:
    """Information about the current license."""

    tier: str
    is_valid: bool
    expiration_date: datetime | None = None
    organization: str | None = None
    seats: int | None = None
    seats_used: int = 0
    concurrent_users: int = 0
    features: set[str] = field(default_factory=set)
    metadata: dict[str, str] = field(default_factory=dict)
    grace_period_days: int = 0
    is_in_grace_period: bool = False
    days_until_expiration: int | None = None
    custom_terms: Mapping[str, str | bool] = field(default_factory=dict)


# [20251225_FEATURE] Feature to tier mapping
# Features are available at the specified tier and all higher tiers
FEATURE_TIERS: dict[str, str] = {
    # COMMUNITY features (always available)
    "analyze_code": "community",
    "extract_code": "community",
    "update_symbol": "community",
    "crawl_project": "community",
    "get_file_context": "community",
    "get_symbol_references": "community",
    "get_call_graph": "community",
    "get_project_map": "community",
    "validate_paths": "community",
    "security_scan": "community",
    "unified_sink_detect": "community",
    # PRO features
    # [20251225_BUGFIX] Align test generation with community availability in limits/docs.
    "symbolic_execute": "pro",
    "generate_unit_tests": "community",
    "simulate_refactor": "pro",
    "scan_dependencies": "pro",
    "get_cross_file_dependencies": "pro",
    "get_graph_neighborhood": "pro",
    # ENTERPRISE features
    "cross_file_security_scan": "enterprise",
    "verify_policy_integrity": "enterprise",
    "type_evaporation_scan": "enterprise",
    "autonomous_repair": "enterprise",
    "compliance_report": "enterprise",
}

# Tier hierarchy for comparison
TIER_HIERARCHY = {
    "community": 0,
    "pro": 1,
    "enterprise": 2,
}


class LicenseManager:
    """
    Central license management for Code Scalpel.

    Coordinates tier detection, license validation, and feature
    availability checks.

    Usage:
        manager = LicenseManager()

        # Get current tier
        tier = manager.get_current_tier()

        # Check feature availability
        if manager.is_feature_available("security_scan"):
            # Run security scan
            pass
        else:
            # Show upgrade message
            pass
    """

    def __init__(
        self,
        tier_detector: TierDetector | None = None,
        validator: LicenseValidator | None = None,
        persistence_path: Path | None = None,
    ):
        """
        Initialize the license manager.

        Args:
            tier_detector: Optional custom tier detector
            validator: Optional custom license validator
            persistence_path: Path to persist license state
        """
        self._tier_detector = tier_detector or TierDetector()
        self._validator = validator or LicenseValidator()
        self._license_info: LicenseInfo | None = None

        # [20251225_FEATURE] P2_MEDIUM: License state persistence
        self._persistence_path = persistence_path or Path(".code-scalpel/license/license_state.json")

        # [20251225_FEATURE] P2_MEDIUM: Seat tracking and concurrent usage
        self._active_users: set[str] = set()
        self._user_lock = threading.Lock()

        # [20251225_FEATURE] P2_MEDIUM: Grace period configuration
        self._default_grace_period_days = 30

        # Load persisted state if available
        self._load_state()

    def get_current_tier(self) -> str:
        """
        Get the current license tier.

        Returns:
            Tier string: "community", "pro", or "enterprise"
        """
        return self._tier_detector.get_tier_string()

    def get_license_info(self) -> LicenseInfo:
        """
        Get detailed license information.

        Returns:
            LicenseInfo with tier, validity, and features
        """
        if self._license_info is None:
            tier_result = self._tier_detector.detect()
            tier = tier_result.tier
            license_key = tier_result.license_key
            organization = tier_result.organization

            # [20251225_FEATURE] P1_HIGH: License key validation
            validation_result = None
            if license_key and tier in {"pro", "enterprise"}:
                validation_result = self._validator.validate(
                    license_key=license_key,
                    tier=tier,
                    organization=organization,
                    seats_used=len(self._active_users),
                )
            elif tier == "community":
                validation_result = self._validator.validate(tier="community")

            # Determine validity
            is_valid = True
            grace_period_days = 0
            is_in_grace_period = False
            days_until_expiration = None

            if validation_result:
                is_valid = validation_result.is_valid

                # [20251225_FEATURE] P2_MEDIUM: License expiration handling
                if validation_result.expiration_date:
                    days_until_expiration = validation_result.days_until_expiration

                    # [20251225_FEATURE] P2_MEDIUM: Grace period support
                    if validation_result.status == ValidationStatus.EXPIRED:
                        days_expired = (_utcnow_naive() - validation_result.expiration_date).days
                        if days_expired <= self._default_grace_period_days:
                            is_valid = True
                            is_in_grace_period = True
                            grace_period_days = self._default_grace_period_days - days_expired
                            logger.warning(
                                f"License expired {days_expired} days ago, "
                                f"in grace period ({grace_period_days} days remaining)"
                            )

            available_features = self._get_available_features(tier)

            # [20251225_FEATURE] P2_MEDIUM: Seat counting
            seats = validation_result.seats if validation_result else None
            seats_used = len(self._active_users)

            # [20251225_FEATURE] P4_LOW: Custom license terms
            custom_terms: Mapping[str, str | bool] = (
                dict(validation_result.custom_rules) if validation_result and validation_result.custom_rules else {}
            )

            self._license_info = LicenseInfo(
                tier=tier,
                is_valid=is_valid,
                expiration_date=(validation_result.expiration_date if validation_result else None),
                organization=organization,
                seats=seats,
                seats_used=seats_used,
                concurrent_users=len(self._active_users),
                features=available_features,
                grace_period_days=grace_period_days,
                is_in_grace_period=is_in_grace_period,
                days_until_expiration=days_until_expiration,
                custom_terms=custom_terms,
            )

            # [20251225_FEATURE] P2_MEDIUM: Persist license state
            self._save_state()

        return self._license_info

    def is_feature_available(self, feature_name: str) -> bool:
        """
        Check if a feature is available at the current tier.

        Args:
            feature_name: Name of the feature to check

        Returns:
            True if feature is available, False otherwise
        """
        current_tier = self.get_current_tier()
        required_tier = FEATURE_TIERS.get(feature_name, "community")

        current_level = TIER_HIERARCHY.get(current_tier, 0)
        required_level = TIER_HIERARCHY.get(required_tier, 0)

        return current_level >= required_level

    def get_upgrade_message(self, feature_name: str) -> str | None:
        """
        Get an upgrade message for a feature not available at current tier.

        Args:
            feature_name: Name of the feature

        Returns:
            Upgrade message if feature unavailable, None if available
        """
        if self.is_feature_available(feature_name):
            return None

        required_tier = FEATURE_TIERS.get(feature_name, "community")
        current_tier = self.get_current_tier()

        return (
            f"Feature '{feature_name}' requires {required_tier.upper()} tier. "
            f"Current tier: {current_tier.upper()}. "
            f"Upgrade at https://code-scalpel.dev/pricing"
        )

    def get_available_features(self) -> list[str]:
        """
        Get list of all features available at current tier.

        Returns:
            List of feature names
        """
        tier = self.get_current_tier()
        return list(self._get_available_features(tier))

    def get_unavailable_features(self) -> list[str]:
        """
        Get list of features NOT available at current tier.

        Returns:
            List of feature names requiring upgrade
        """
        available = set(self.get_available_features())
        all_features = set(FEATURE_TIERS.keys())
        return list(all_features - available)

    def _get_available_features(self, tier: str) -> set[str]:
        """Get all features available at the specified tier."""
        tier_level = TIER_HIERARCHY.get(tier, 0)
        available = set()

        for feature, required_tier in FEATURE_TIERS.items():
            required_level = TIER_HIERARCHY.get(required_tier, 0)
            if tier_level >= required_level:
                available.add(feature)

        return available

    def refresh(self) -> None:
        """Refresh license information (re-detect tier)."""
        self._tier_detector.detect(force_refresh=True)
        self._license_info = None

    def check_expiration(self) -> dict[str, Any] | None:
        """
        [20251225_FEATURE] P2_MEDIUM: Check license expiration status.

        Returns:
            Dictionary with expiration details or None if no expiration
        """
        info = self.get_license_info()

        if not info.expiration_date:
            return None

        return {
            "expiration_date": info.expiration_date,
            "days_until_expiration": info.days_until_expiration,
            "is_expired": info.days_until_expiration == 0,
            "is_in_grace_period": info.is_in_grace_period,
            "grace_period_days_remaining": info.grace_period_days,
            "needs_renewal": info.days_until_expiration is not None and info.days_until_expiration <= 30,
        }

    def get_renewal_reminder(self) -> str | None:
        """
        [20251225_FEATURE] P3_LOW: Get license renewal reminder message.

        Returns:
            Renewal reminder message if license is expiring soon, None otherwise
        """
        expiration = self.check_expiration()

        if not expiration:
            return None

        if expiration["is_in_grace_period"]:
            return (
                f"LICENSE EXPIRED: Your license expired on {expiration['expiration_date'].date()}. "
                f"You have {expiration['grace_period_days_remaining']} days remaining in the grace period. "
                "Please renew immediately at https://code-scalpel.dev/renew"
            )

        if expiration["days_until_expiration"] is not None:
            days = expiration["days_until_expiration"]
            if days <= 7:
                return (
                    f"URGENT: Your license expires in {days} day(s) on {expiration['expiration_date'].date()}. "
                    "Renew now at https://code-scalpel.dev/renew"
                )
            elif days <= 30:
                return (
                    f"NOTICE: Your license expires in {days} days on {expiration['expiration_date'].date()}. "
                    "Renew at https://code-scalpel.dev/renew"
                )

        return None

    def add_user(self, user_id: str) -> bool:
        """
        [20251225_FEATURE] P2_MEDIUM: Add a user to the active user set (seat counting).

        Args:
            user_id: Unique identifier for the user

        Returns:
            True if user added successfully, False if seat limit exceeded
        """
        info = self.get_license_info()

        with self._user_lock:
            # Check seat limit for ENTERPRISE tier
            if info.tier == "enterprise" and info.seats is not None:
                if len(self._active_users) >= info.seats:
                    logger.warning(f"Seat limit reached: {len(self._active_users)}/{info.seats}")
                    return False

            self._active_users.add(user_id)
            logger.info(f"User {user_id} added. Active users: {len(self._active_users)}")

            # Invalidate cached license info to reflect new seat count
            self._license_info = None
            self._save_state()

            return True

    def remove_user(self, user_id: str) -> bool:
        """
        [20251225_FEATURE] P2_MEDIUM: Remove a user from the active user set.

        Args:
            user_id: Unique identifier for the user

        Returns:
            True if user removed, False if user was not active
        """
        with self._user_lock:
            if user_id in self._active_users:
                self._active_users.remove(user_id)
                logger.info(f"User {user_id} removed. Active users: {len(self._active_users)}")

                # Invalidate cached license info
                self._license_info = None
                self._save_state()

                return True
            return False

    def get_active_users(self) -> list[str]:
        """
        [20251225_FEATURE] P3_LOW: Get list of currently active users.

        Returns:
            List of active user IDs
        """
        with self._user_lock:
            return list(self._active_users)

    def get_concurrent_usage(self) -> dict[str, float | int]:
        """
        [20251225_FEATURE] P3_LOW: Get concurrent usage statistics.

        Returns:
            Dictionary with usage statistics
        """
        info = self.get_license_info()

        with self._user_lock:
            return {
                "active_users": len(self._active_users),
                "seat_limit": info.seats if info.seats else -1,
                "seats_available": ((info.seats - len(self._active_users)) if info.seats else -1),
                "utilization_percent": ((len(self._active_users) / info.seats * 100) if info.seats else 0),
            }

    def get_organization_info(self) -> dict[str, Any] | None:
        """
        [20251225_FEATURE] P3_LOW: Get organization management information.

        Returns:
            Dictionary with organization details or None if not applicable
        """
        info = self.get_license_info()

        if not info.organization:
            return None

        tier_result = self._tier_detector.detect()

        return {
            "name": info.organization,
            "tier": info.tier,
            "parent_organizations": tier_result.parent_organizations,
            "custom_tier_name": tier_result.custom_tier_name,
            "seats": info.seats,
            "seats_used": info.seats_used,
            "features": list(info.features),
        }

    def get_custom_terms(self) -> dict[str, str | bool]:
        """
        [20251225_FEATURE] P4_LOW: Get custom license terms.

        Returns:
            Dictionary of custom license terms and conditions
        """
        info = self.get_license_info()
        return dict(info.custom_terms)

    def is_term_enabled(self, term_name: str) -> bool:
        """
        [20251225_FEATURE] P4_LOW: Check if a custom license term is enabled.

        Args:
            term_name: Name of the custom term

        Returns:
            True if term is enabled, False otherwise
        """
        terms = self.get_custom_terms()
        return bool(terms.get(term_name, False))

    def _save_state(self) -> None:
        """
        [20251225_FEATURE] P2_MEDIUM: Persist license state to disk.
        """
        if not self._license_info:
            return

        try:
            # Create directory if it doesn't exist
            self._persistence_path.parent.mkdir(parents=True, exist_ok=True)

            # Prepare state data
            state = {
                "tier": self._license_info.tier,
                "is_valid": self._license_info.is_valid,
                "expiration_date": (
                    self._license_info.expiration_date.isoformat() if self._license_info.expiration_date else None
                ),
                "organization": self._license_info.organization,
                "seats": self._license_info.seats,
                "seats_used": self._license_info.seats_used,
                "active_users": list(self._active_users),
                "grace_period_days": self._license_info.grace_period_days,
                "is_in_grace_period": self._license_info.is_in_grace_period,
                "custom_terms": self._license_info.custom_terms,
                "last_updated": _utcnow_naive().isoformat(),
            }

            # Write to file
            with open(self._persistence_path, "w") as f:
                json.dump(state, f, indent=2)

            logger.debug(f"License state saved to {self._persistence_path}")

        except OSError as e:
            logger.warning(f"Failed to save license state: {e}")

    def _load_state(self) -> None:
        """
        [20251225_FEATURE] P2_MEDIUM: Load persisted license state from disk.
        """
        if not self._persistence_path.exists():
            return

        try:
            with open(self._persistence_path) as f:
                state = json.load(f)

            # Restore active users
            self._active_users = set(state.get("active_users", []))

            logger.debug(
                f"License state loaded from {self._persistence_path}. " f"Active users: {len(self._active_users)}"
            )

        except (OSError, json.JSONDecodeError) as e:
            logger.warning(f"Failed to load license state: {e}")
