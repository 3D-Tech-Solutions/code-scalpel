"""
Licensing Module - License management and validation for Code Scalpel.

[20251225_FEATURE] v3.3.0 - JWT-based license validation
[20260102_REFACTOR] Consolidated licensing infrastructure

ARCHITECTURE
============

Licensing Model: Open-core (COMMUNITY/PRO/ENTERPRISE tiers)

JWT License Validation (v3.3.0+):
    - Industry-standard RS256/HS256 signing
    - Cryptographically tamper-proof tokens
    - Community tier: free, no license required
    - Pro/Enterprise tiers: valid JWT required

JWT Claims:
    {
        "iss": "code-scalpel-licensing",
        "sub": "customer_id",
        "tier": "pro" | "enterprise",
        "features": [...],
        "exp": timestamp,
        "iat": timestamp
    }

CONFIGURATION
=============

Priority order:
    1. Environment variable: CODE_SCALPEL_LICENSE_KEY (JWT token)
    2. License file: .scalpel-license (JWT token)
    3. User config: ~/.config/code-scalpel/license
    4. Fallback: COMMUNITY tier (no license required)

USAGE
=====

from code_scalpel.licensing import get_current_tier, get_license_info

# Check tier
tier = get_current_tier()  # Returns: "community" | "pro" | "enterprise"

# Detailed info
info = get_license_info()
print(f"Tier: {info['tier']}")
print(f"Valid: {info['is_valid']}")
print(f"Expires: {info['days_until_expiration']} days")

FEATURES IMPLEMENTED
====================

Community Tier:
    ✓ Tier detection from environment
    ✓ License validation (offline HMAC-SHA256)
    ✓ Validation caching with persistence
    ✓ Feature gating by tier
    ✓ Graceful degradation messaging

Pro Tier:
    ✓ License key management and signing
    ✓ Key revocation support
    ✓ Online validation with grace periods
    ✓ Usage tracking and analytics
    ✓ Concurrent usage monitoring

Enterprise Tier:
    ✓ Multi-seat licensing with limits
    ✓ Concurrent user tracking
    ✓ Organization-level licenses
    ✓ Sub-organization delegation
    ✓ License pooling
    ✓ Custom tier definitions
    ✓ Feature bundle licensing
    ✓ Trial license support

Test Coverage: 190+ tests (all core functionality)
"""

from enum import Enum
from typing import TYPE_CHECKING

# [20251225_FEATURE] Import from submodules
# Use TYPE_CHECKING to avoid circular import issues during runtime
if TYPE_CHECKING:
    from .cache import LicenseCache
    from .license_manager import LicenseInfo, LicenseManager
    from .tier_detector import TierDetector, get_current_tier
    from .validator import LicenseValidator, ValidationResult
else:
    # Runtime imports after Tier enum is defined
    pass


# [20251225_FEATURE] Tier enum for license levels
class Tier(Enum):
    """License tier levels for Code Scalpel."""

    COMMUNITY = "community"
    PRO = "pro"
    ENTERPRISE = "enterprise"

    @classmethod
    def from_string(cls, value: str) -> "Tier":
        """Convert string to Tier enum."""
        value_lower = value.lower().strip()
        for tier in cls:
            if tier.value == value_lower:
                return tier
        return cls.COMMUNITY  # Default to COMMUNITY


# [20260102_REFACTOR] Tier enum defined first; imports remain below for compatibility.
# ruff: noqa: E402
from .cache import LicenseCache

# [20251225_CONFIG] v3.3.0 - TOML-based tier limits configuration
from .config_loader import (
    clear_cache,
    get_cached_limits,
    get_tool_limits,
    load_limits,
    merge_limits,
    reload_config,
)
from .features import (
    TOOL_CAPABILITIES,
    get_all_tools_for_tier,
    get_tool_capabilities,
    get_upgrade_hint,
    has_capability,
)

# [20251225_FEATURE] v3.3.0 - JWT license validation
from .jwt_validator import (
    JWTAlgorithm,
    JWTLicenseData,
    JWTLicenseValidator,
    get_current_tier,
    get_license_info,
)
from .license_manager import LicenseInfo, LicenseManager

# [20251225_FEATURE] Runtime imports after Tier enum definition
from .tier_detector import TierDetector
from .tier_detector import get_current_tier as legacy_get_current_tier
from .validator import LicenseValidator, ValidationResult

__all__ = [
    # Tier enum
    "Tier",
    # JWT validation (NEW in v3.3.0 - PRIMARY)
    "JWTLicenseValidator",
    "JWTLicenseData",
    "JWTAlgorithm",
    "get_current_tier",  # Primary function for v3.3.0+
    "get_license_info",
    # Legacy tier detection
    "TierDetector",
    "legacy_get_current_tier",
    # License management
    "LicenseManager",
    "LicenseInfo",
    # Validation
    "LicenseValidator",
    "ValidationResult",
    # Cache
    "LicenseCache",
    # Feature capabilities
    "get_tool_capabilities",
    "has_capability",
    "get_all_tools_for_tier",
    "get_upgrade_hint",
    "TOOL_CAPABILITIES",
    # Config loader (NEW in v3.3.0)
    "load_limits",
    "get_tool_limits",
    "get_cached_limits",
    "clear_cache",
    "reload_config",
    "merge_limits",
]

__version__ = "1.0.0"
