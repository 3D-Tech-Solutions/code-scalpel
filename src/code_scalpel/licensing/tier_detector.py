"""
Tier Detector - Detect current license tier from environment and configuration.

[20251225_FEATURE] Tier detection system with multi-source support and organization hierarchy.

DETECTION PRIORITY ORDER:
1. Environment variable: CODE_SCALPEL_TIER
2. License file: CODE_SCALPEL_LICENSE_PATH (JWT validation)
3. License key extraction: SCALPEL-{TIER}-{DATA} format
4. Config file: .code-scalpel/license.json
5. Organization hierarchy: CODE_SCALPEL_ORGANIZATION env var
6. Default: COMMUNITY tier

FEATURES IMPLEMENTED:
- Multi-source tier detection (environment, config, license, organization)
- License key parsing with SCALPEL-{TIER}-{DATA} format
- Configuration file support with custom tier definitions
- Organization-based tier assignment and hierarchy
- Tier validation with comprehensive audit logging
- In-memory caching with force_refresh capability
- Custom tier name mapping (e.g., "startup" -> "pro")
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


# [20251225_FEATURE] Import Tier from parent module to avoid circular import
# We use a string import here since __init__.py imports this module
class Tier:
    """Placeholder - real Tier enum is in __init__.py"""

    COMMUNITY = "community"
    PRO = "pro"
    ENTERPRISE = "enterprise"


@dataclass
class TierDetectionResult:
    """Result of tier detection."""

    tier: str
    source: str  # "environment", "config", "license", "organization", "default"
    confidence: float  # 0.0 to 1.0
    details: str | None = None
    license_key: str | None = None
    organization: str | None = None
    parent_organizations: list[str] = field(default_factory=list)
    custom_tier_name: str | None = None
    is_validated: bool = False


class TierDetector:
    """
    Detect the current license tier from environment and configuration.

    Priority order:
    1. Environment variable CODE_SCALPEL_TIER (highest)
    2. License file CODE_SCALPEL_LICENSE_PATH (JWT validation)
    3. License key extraction from passed key
    4. Config file .code-scalpel/license.json
    5. Organization-based detection
    6. Default to COMMUNITY (lowest)
    """

    ENV_VAR = "CODE_SCALPEL_TIER"
    CONFIG_PATHS = [
        ".code-scalpel/license.json",
        ".code-Scalpel/license.json",
        "~/.code-scalpel/license.json",
        "~/.code-Scalpel/license.json",
        "/etc/code-scalpel/license.json",
    ]

    def __init__(self, config_dir: Path | None = None):
        """
        Initialize the tier detector.

        Args:
            config_dir: Optional custom config directory
        """
        self.config_dir = config_dir
        self._cached_result: TierDetectionResult | None = None
        # [20251225_FEATURE] P2_MEDIUM: Organization hierarchy for tier inheritance
        self._org_hierarchy: dict[str, list[str]] = {}  # org -> parent orgs
        # [20251225_FEATURE] P4_LOW: Custom tier definitions
        self._custom_tiers: dict[str, str] = {}  # custom_name -> standard_tier

    def detect(self, force_refresh: bool = False, license_key: str | None = None) -> TierDetectionResult:
        """
        Detect the current tier.

        Args:
            force_refresh: If True, bypass cache and re-detect
            license_key: Optional license key to extract tier from

        Returns:
            TierDetectionResult with tier and source
        """
        if self._cached_result and not force_refresh:
            return self._cached_result

        # Priority 1: Environment variable
        env_tier = self._detect_from_environment()
        if env_tier:
            # [20251225_FEATURE] P2_MEDIUM: Validate and log tier
            validated = self._validate_and_log_tier(env_tier)
            self._cached_result = validated
            return validated

        # Priority 2: License file
        license_file_tier = self._detect_from_license_file()
        if license_file_tier:
            validated = self._validate_and_log_tier(license_file_tier)
            self._cached_result = validated
            return validated

        # Priority 3: License key tier extraction
        if license_key:
            license_tier = self._detect_from_license_key(license_key)
            if license_tier:
                validated = self._validate_and_log_tier(license_tier)
                self._cached_result = validated
                return validated

        # Priority 4: Config file
        config_tier = self._detect_from_config()
        if config_tier:
            validated = self._validate_and_log_tier(config_tier)
            self._cached_result = validated
            return validated

        # Priority 5: Organization-based detection
        org_tier = self._detect_from_organization()
        if org_tier:
            validated = self._validate_and_log_tier(org_tier)
            self._cached_result = validated
            return validated

        # Priority 5: Default
        default_tier = TierDetectionResult(
            tier=Tier.COMMUNITY,
            source="default",
            confidence=1.0,
            details="No tier configuration found, defaulting to COMMUNITY",
            is_validated=True,
        )
        logger.info("No tier configuration found, using COMMUNITY tier")
        self._cached_result = default_tier
        return default_tier

    def _detect_from_environment(self) -> TierDetectionResult | None:
        """Detect tier from environment variable."""
        tier_value = os.environ.get(self.ENV_VAR)
        if not tier_value:
            return None

        tier_lower = tier_value.lower().strip()
        valid_tiers = {Tier.COMMUNITY, Tier.PRO, Tier.ENTERPRISE}

        if tier_lower in valid_tiers:
            logger.debug(f"Detected tier '{tier_lower}' from environment variable {self.ENV_VAR}")
            return TierDetectionResult(
                tier=tier_lower,
                source="environment",
                confidence=1.0,
                details=f"Set via {self.ENV_VAR}={tier_value}",
            )
        else:
            logger.warning(f"Invalid tier '{tier_value}' in {self.ENV_VAR}, ignoring")
            return None

    def _detect_from_license_file(self) -> TierDetectionResult | None:
        """Detect tier from license file."""
        try:
            from code_scalpel.licensing.jwt_validator import get_current_tier as jwt_get_current_tier

            tier = jwt_get_current_tier()
            if tier != "community":  # Only return if it's not the default
                logger.debug(f"Detected tier '{tier}' from license file")
                return TierDetectionResult(
                    tier=tier,
                    source="license_file",
                    confidence=0.95,
                    details="Validated from JWT license file",
                )
        except Exception as e:
            logger.debug(f"License file detection failed: {e}")
        return None

    def _detect_from_config(self) -> TierDetectionResult | None:
        """Detect tier from config file."""
        config_paths = self.CONFIG_PATHS.copy()

        # Add custom config dir if specified
        if self.config_dir:
            config_paths.insert(0, str(self.config_dir / "license.json"))

        for config_path_str in config_paths:
            config_path = Path(config_path_str).expanduser()
            if config_path.exists():
                try:
                    with open(config_path) as f:
                        config = json.load(f)

                    tier_value = config.get("tier", "").lower().strip()

                    # [20251225_FEATURE] P4_LOW: Check for custom tier definitions
                    if tier_value not in {Tier.COMMUNITY, Tier.PRO, Tier.ENTERPRISE}:
                        # Check if it's a custom tier name
                        if tier_value in self._custom_tiers:
                            actual_tier = self._custom_tiers[tier_value]
                            logger.debug(
                                f"Resolved custom tier '{tier_value}' to '{actual_tier}' from config {config_path}"
                            )
                            return TierDetectionResult(
                                tier=actual_tier,
                                source="config",
                                confidence=0.9,
                                details=f"Loaded from {config_path} (custom tier: {tier_value})",
                                license_key=config.get("license_key"),
                                organization=config.get("organization"),
                                custom_tier_name=tier_value,
                            )
                        else:
                            logger.warning(f"Invalid tier '{tier_value}' in {config_path}, ignoring")
                            continue

                    if tier_value in {Tier.COMMUNITY, Tier.PRO, Tier.ENTERPRISE}:
                        logger.debug(f"Detected tier '{tier_value}' from config file {config_path}")

                        # Extract additional metadata
                        license_key = config.get("license_key")
                        organization = config.get("organization")

                        # Load organization hierarchy if present
                        if "organization_hierarchy" in config:
                            self._load_org_hierarchy(config["organization_hierarchy"])

                        # Load custom tier definitions if present
                        if "custom_tiers" in config:
                            self._load_custom_tiers(config["custom_tiers"])

                        return TierDetectionResult(
                            tier=tier_value,
                            source="config",
                            confidence=0.9,
                            details=f"Loaded from {config_path}",
                            license_key=license_key,
                            organization=organization,
                        )
                except (OSError, json.JSONDecodeError) as e:
                    logger.warning(f"Error reading config file {config_path}: {e}")

        return None

    def get_tier_string(self) -> str:
        """Get the current tier as a string."""
        result = self.detect()
        return result.tier

    def is_pro_or_higher(self) -> bool:
        """Check if current tier is PRO or ENTERPRISE."""
        tier = self.get_tier_string()
        return tier in {Tier.PRO, Tier.ENTERPRISE}

    def is_enterprise(self) -> bool:
        """Check if current tier is ENTERPRISE."""
        return self.get_tier_string() == Tier.ENTERPRISE

    def _detect_from_license_key(self, license_key: str) -> TierDetectionResult | None:
        """
        [20251225_FEATURE] P1_HIGH: Extract tier from license key.

        License key format: SCALPEL-{TIER}-{DATA}...
        """
        parts = license_key.split("-")

        if len(parts) < 2 or parts[0] != "SCALPEL":
            logger.warning("Invalid license key format, cannot extract tier")
            return None

        tier_value = parts[1].lower()
        valid_tiers = {Tier.COMMUNITY, Tier.PRO, Tier.ENTERPRISE}

        if tier_value not in valid_tiers:
            logger.warning(f"Invalid tier '{tier_value}' extracted from license key")
            return None

        logger.info(f"Extracted tier '{tier_value}' from license key")
        return TierDetectionResult(
            tier=tier_value,
            source="license",
            confidence=0.95,
            details="Extracted from license key",
            license_key=license_key,
        )

    def _detect_from_organization(self) -> TierDetectionResult | None:
        """
        [20251225_FEATURE] P2_MEDIUM: Detect tier based on organization.

        Checks environment variable CODE_SCALPEL_ORGANIZATION and looks up
        the organization's tier from configuration or hierarchy.
        """
        org_name = os.environ.get("CODE_SCALPEL_ORGANIZATION")
        if not org_name:
            return None

        logger.debug(f"Attempting organization-based tier detection for: {org_name}")

        # Check if organization has a configured tier
        org_tier = self._get_organization_tier(org_name)
        if org_tier:
            # [20251225_FEATURE] P3_LOW: Tier inheritance from parent orgs
            parent_orgs = self._get_parent_organizations(org_name)

            return TierDetectionResult(
                tier=org_tier,
                source="organization",
                confidence=0.85,
                details=f"Tier assigned to organization: {org_name}",
                organization=org_name,
                parent_organizations=parent_orgs,
            )

        return None

    def _validate_and_log_tier(self, result: TierDetectionResult) -> TierDetectionResult:
        """
        [20251225_FEATURE] P2_MEDIUM: Validate and log tier detection result.

        Performs validation checks and logs detailed information about the
        detected tier for audit and debugging purposes.
        """
        # Validate tier is one of the known tiers
        valid_tiers = {Tier.COMMUNITY, Tier.PRO, Tier.ENTERPRISE}
        if result.tier not in valid_tiers:
            logger.error(f"Invalid tier '{result.tier}' detected from {result.source}. Valid tiers: {valid_tiers}")
            # Return default tier on validation failure
            return TierDetectionResult(
                tier=Tier.COMMUNITY,
                source="default",
                confidence=1.0,
                details=f"Validation failed for tier '{result.tier}', defaulting to COMMUNITY",
                is_validated=True,
            )

        # Log tier detection with full context
        log_msg = f"Tier detected: {result.tier.upper()} (source: {result.source}, confidence: {result.confidence:.2f})"
        if result.organization:
            log_msg += f" [org: {result.organization}]"
        if result.license_key:
            log_msg += " [has license key]"
        if result.custom_tier_name:
            log_msg += f" [custom: {result.custom_tier_name}]"

        logger.info(log_msg)

        # Additional validation warnings
        if result.tier in {Tier.PRO, Tier.ENTERPRISE} and not result.license_key:
            logger.warning(
                f"{result.tier.upper()} tier detected but no license key found. License validation may fail."
            )

        if result.tier == Tier.ENTERPRISE and not result.organization:
            logger.warning(
                "ENTERPRISE tier detected but no organization specified. Organization-specific features may not work."
            )

        result.is_validated = True
        return result

    def _get_organization_tier(self, org_name: str) -> str | None:
        """
        [20251225_FEATURE] P2_MEDIUM: Get tier for an organization.

        Looks up the tier assigned to an organization. In production, this
        would query a database or API. For now, uses environment variables.
        """
        # Check environment variable for organization tier
        # Format: CODE_SCALPEL_ORG_{ORG_HASH}_TIER
        org_hash = hashlib.sha256(org_name.encode()).hexdigest()[:8].upper()
        env_var = f"CODE_SCALPEL_ORG_{org_hash}_TIER"
        tier_value = os.environ.get(env_var, "").lower().strip()

        if tier_value in {Tier.COMMUNITY, Tier.PRO, Tier.ENTERPRISE}:
            logger.debug(f"Found tier '{tier_value}' for organization {org_name}")
            return tier_value

        return None

    def _get_parent_organizations(self, org_name: str) -> list[str]:
        """
        [20251225_FEATURE] P3_LOW: Get parent organizations for tier inheritance.

        Returns the hierarchy of parent organizations. Child organizations
        can inherit tier from parent organizations.
        """
        return self._org_hierarchy.get(org_name, [])

    def _load_org_hierarchy(self, hierarchy_config: dict[str, list[str]]) -> None:
        """
        [20251225_FEATURE] P3_LOW: Load organization hierarchy from config.

        Args:
            hierarchy_config: Dict mapping org_name -> [parent_orgs]
        """
        self._org_hierarchy.update(hierarchy_config)
        logger.debug(f"Loaded organization hierarchy for {len(hierarchy_config)} organizations")

    def _load_custom_tiers(self, custom_tiers_config: dict[str, str]) -> None:
        """
        [20251225_FEATURE] P4_LOW: Load custom tier definitions from config.

        Allows organizations to define custom tier names that map to
        standard tiers (e.g., "startup" -> "pro", "corporate" -> "enterprise").

        Args:
            custom_tiers_config: Dict mapping custom_name -> standard_tier
        """
        for custom_name, standard_tier in custom_tiers_config.items():
            if standard_tier.lower() in {Tier.COMMUNITY, Tier.PRO, Tier.ENTERPRISE}:
                self._custom_tiers[custom_name.lower()] = standard_tier.lower()
            else:
                logger.warning(f"Invalid standard tier '{standard_tier}' for custom tier '{custom_name}'")

        logger.debug(f"Loaded {len(self._custom_tiers)} custom tier definitions")

    def set_custom_tier(self, custom_name: str, standard_tier: str) -> bool:
        """
        [20251225_FEATURE] P4_LOW: Register a custom tier mapping.

        Args:
            custom_name: Custom tier name (e.g., "startup", "corporate")
            standard_tier: Standard tier to map to ("community", "pro", "enterprise")

        Returns:
            True if successfully registered, False if invalid
        """
        if standard_tier.lower() not in {Tier.COMMUNITY, Tier.PRO, Tier.ENTERPRISE}:
            logger.error(f"Cannot register custom tier: invalid standard tier '{standard_tier}'")
            return False

        self._custom_tiers[custom_name.lower()] = standard_tier.lower()
        logger.info(f"Registered custom tier '{custom_name}' -> '{standard_tier}'")

        # Invalidate cache to force re-detection
        self._cached_result = None
        return True

    def set_organization_tier(self, org_name: str, tier: str, parent_orgs: list[str] | None = None) -> bool:
        """
        [20251225_FEATURE] P2_MEDIUM: Assign a tier to an organization.

        Args:
            org_name: Organization name
            tier: Tier to assign ("community", "pro", "enterprise")
            parent_orgs: Optional list of parent organizations for inheritance

        Returns:
            True if successfully assigned, False if invalid
        """
        if tier.lower() not in {Tier.COMMUNITY, Tier.PRO, Tier.ENTERPRISE}:
            logger.error(f"Cannot assign organization tier: invalid tier '{tier}'")
            return False

        # Set environment variable for this session
        org_hash = hashlib.sha256(org_name.encode()).hexdigest()[:8].upper()
        env_var = f"CODE_SCALPEL_ORG_{org_hash}_TIER"
        os.environ[env_var] = tier.lower()

        # Store hierarchy if provided
        if parent_orgs:
            self._org_hierarchy[org_name] = parent_orgs

        logger.info(f"Assigned tier '{tier}' to organization '{org_name}'")

        # Invalidate cache to force re-detection
        self._cached_result = None
        return True


# [20251225_FEATURE] Convenience function for quick tier detection
def get_current_tier() -> str:
    """
    Get the current license tier.

    Returns:
        Tier string: "community", "pro", or "enterprise"
    """
    detector = TierDetector()
    return detector.get_tier_string()


def clear_tier_cache() -> None:
    """
    Clear all tier-related caches to allow fresh detection.

    [20260122_TEST] This function clears both the jwt_validator cache
    and config_loader cache to ensure environment variable overrides
    take effect in tests.
    """
    # Clear jwt_validator cache
    try:
        from code_scalpel.licensing.jwt_validator import clear_license_cache

        clear_license_cache()
    except ImportError:
        pass

    # Clear config_loader cache
    try:
        from code_scalpel.licensing.config_loader import clear_config_cache

        clear_config_cache()
    except (ImportError, AttributeError):
        pass
