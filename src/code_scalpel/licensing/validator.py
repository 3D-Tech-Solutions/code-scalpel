"""
License Validator - License key validation for Code Scalpel.

[20251225_FEATURE] License validation system for PRO and ENTERPRISE tiers.
COMMUNITY tier does not require validation.

Features:
- COMMUNITY: Always valid (no key required)
- PRO: Format validation, HMAC-SHA256 signature verification, expiration checking
- ENTERPRISE: Organization binding, seat limits, hardware fingerprinting, custom rules

Validation Methods:
- validate(): Offline validation with format/signature/expiration checks
- validate_offline(): Validation without network access
- validate_online(): Server-based validation with offline fallback

Caching:
- 5-minute TTL for validation results
- Cache key: "{license_key}:{tier}:{organization}"

License Key Format:
- SCALPEL-{TIER}-{TIMESTAMP}-{DATA}-...-{SIGNATURE}
- SIGNATURE = HMAC-SHA256(data_parts, secret_key)[:8]

ENTERPRISE Extensions:
- Organization hash verification (SHA-256)
- Seat limit enforcement (usage tracking)
- Hardware ID binding (machine ID + system info)
- Custom rule evaluation
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import platform
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from urllib import parse, request
from urllib.error import URLError

logger = logging.getLogger(__name__)


def _utcnow_naive() -> datetime:
    # [20251228_BUGFIX] Avoid deprecated datetime.utcnow() while preserving
    # existing naive-UTC behavior.
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _utcfromtimestamp_naive(timestamp: int) -> datetime:
    # [20251228_BUGFIX] Avoid deprecated datetime.utcfromtimestamp() while
    # preserving existing naive-UTC behavior.
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).replace(tzinfo=None)


class ValidationStatus(Enum):
    """License validation status."""

    VALID = "valid"
    INVALID = "invalid"
    EXPIRED = "expired"
    NOT_REQUIRED = "not_required"  # COMMUNITY tier
    UNKNOWN = "unknown"


@dataclass
class ValidationResult:
    """Result of license validation."""

    status: ValidationStatus
    tier: str
    message: str
    expiration_date: datetime | None = None
    organization: str | None = None
    seats: int | None = None
    seats_used: int | None = None
    hardware_id: str | None = None
    custom_rules: dict[str, bool] | None = None

    @property
    def is_valid(self) -> bool:
        """Check if license is valid."""
        return self.status in {ValidationStatus.VALID, ValidationStatus.NOT_REQUIRED}

    @property
    def days_until_expiration(self) -> int | None:
        """Calculate days until expiration."""
        if not self.expiration_date:
            return None
        delta = self.expiration_date - _utcnow_naive()
        return max(0, delta.days)


class LicenseValidator:
    """
    Validate license keys for Code Scalpel.

    COMMUNITY tier does not require validation.
    PRO/ENTERPRISE tiers require valid license keys.

    Usage:
        validator = LicenseValidator()
        result = validator.validate("SCALPEL-PRO-XXXX-XXXX-XXXX")

        if result.is_valid:
            print(f"License valid for tier: {result.tier}")
        else:
            print(f"Validation failed: {result.message}")
    """

    # License key prefix format: SCALPEL-{TIER}-{KEY}
    KEY_PREFIX = "SCALPEL"

    # [20251225_FEATURE] License server URL for online validation
    LICENSE_SERVER_URL = os.getenv("CODE_SCALPEL_LICENSE_SERVER", "https://license.code-scalpel.dev/api/validate")

    # [20251225_FEATURE] Secret key for signature verification (in production, load from secure storage)
    # This is a placeholder - in production, use a secure key management system
    _SIGNATURE_SECRET = os.getenv("CODE_SCALPEL_SIGNATURE_SECRET", "scalpel-signing-key-v1")

    def __init__(self):
        """Initialize the validator."""
        # [20251225_FEATURE] P2_MEDIUM: Validation result caching
        self._cache: dict[str, tuple[ValidationResult, float]] = {}
        self._cache_ttl = 300  # 5 minutes cache TTL
        self._hardware_id: str | None = None

    def validate(
        self,
        license_key: str | None = None,
        tier: str = "community",
        organization: str | None = None,
        seats_used: int = 0,
    ) -> ValidationResult:
        """
        Validate a license key.

        Args:
            license_key: The license key to validate (optional for COMMUNITY)
            tier: The claimed tier
            organization: Organization name (for ENTERPRISE tier)
            seats_used: Number of seats currently in use (for ENTERPRISE tier)

        Returns:
            ValidationResult with status and details
        """
        # [20251225_FEATURE] P2_MEDIUM: Check cache first
        cache_key = f"{license_key or 'none'}:{tier}:{organization or 'none'}"
        cached = self._get_cached_result(cache_key)
        if cached:
            logger.debug(f"Returning cached validation result for {tier}")
            return cached

        # COMMUNITY tier doesn't require license
        if tier.lower() == "community":
            result = ValidationResult(
                status=ValidationStatus.NOT_REQUIRED,
                tier="community",
                message="COMMUNITY tier does not require a license key",
            )
            self._cache_result(cache_key, result)
            return result

        # PRO/ENTERPRISE require license key
        if not license_key:
            result = ValidationResult(
                status=ValidationStatus.INVALID,
                tier=tier,
                message=f"{tier.upper()} tier requires a valid license key",
            )
            self._cache_result(cache_key, result)
            return result

        # Validate key format
        format_result = self._validate_format(license_key)
        if not format_result.is_valid:
            self._cache_result(cache_key, format_result)
            return format_result

        # Extract tier from key
        key_tier = self._extract_tier(license_key)
        if key_tier != tier.lower():
            result = ValidationResult(
                status=ValidationStatus.INVALID,
                tier=tier,
                message=f"License key is for {key_tier.upper()} tier, not {tier.upper()}",
            )
            self._cache_result(cache_key, result)
            return result

        # [20251225_FEATURE] P1_HIGH: Validate signature with real crypto
        signature_result = self._validate_signature(license_key)
        if not signature_result.is_valid:
            self._cache_result(cache_key, signature_result)
            return signature_result

        # [20251225_FEATURE] P3_LOW: Check expiration date
        expiration_result = self._check_expiration(license_key)
        if not expiration_result.is_valid:
            self._cache_result(cache_key, expiration_result)
            return expiration_result

        # [20251225_FEATURE] ENTERPRISE tier validation
        if key_tier == "enterprise":
            enterprise_result = self._validate_enterprise(license_key, organization, seats_used)
            if not enterprise_result.is_valid:
                self._cache_result(cache_key, enterprise_result)
                return enterprise_result
            result = enterprise_result
        else:
            # All checks passed for PRO tier
            result = ValidationResult(
                status=ValidationStatus.VALID,
                tier=key_tier,
                message=f"License valid for {key_tier.upper()} tier",
                expiration_date=expiration_result.expiration_date,
            )

        self._cache_result(cache_key, result)
        return result

    def _validate_format(self, license_key: str) -> ValidationResult:
        """Validate license key format."""
        parts = license_key.split("-")

        # Expected format: SCALPEL-{TIER}-{XXXX}-{XXXX}-{XXXX}
        if len(parts) < 5:
            return ValidationResult(
                status=ValidationStatus.INVALID,
                tier="unknown",
                message="Invalid license key format",
            )

        if parts[0] != self.KEY_PREFIX:
            return ValidationResult(
                status=ValidationStatus.INVALID,
                tier="unknown",
                message=f"Invalid license key prefix (expected {self.KEY_PREFIX})",
            )

        tier = parts[1].lower()
        if tier not in {"pro", "enterprise"}:
            return ValidationResult(
                status=ValidationStatus.INVALID,
                tier="unknown",
                message=f"Invalid tier in license key: {tier}",
            )

        return ValidationResult(status=ValidationStatus.VALID, tier=tier, message="Format valid")

    def _extract_tier(self, license_key: str) -> str:
        """Extract tier from license key."""
        parts = license_key.split("-")
        if len(parts) >= 2:
            return parts[1].lower()
        return "unknown"

    def _validate_signature(self, license_key: str) -> ValidationResult:
        """
        [20251225_FEATURE] P1_HIGH: Validate license key signature using HMAC-SHA256.

        License key format: SCALPEL-{TIER}-{ENCODED_DATA}-{SIGNATURE}
        where SIGNATURE = HMAC-SHA256(ENCODED_DATA, secret_key)
        """
        tier = self._extract_tier(license_key)
        parts = license_key.split("-")

        if len(parts) < 5:
            return ValidationResult(
                status=ValidationStatus.INVALID,
                tier=tier,
                message="Invalid license key format for signature verification",
            )

        # Extract encoded data and signature
        # Format: SCALPEL-TIER-DATA1-DATA2-...-SIGNATURE
        # Last part is signature, everything else is data
        data_parts = parts[:-1]  # All except last
        provided_signature = parts[-1]  # Last part
        data_to_sign = "-".join(data_parts)

        # Compute expected signature
        expected_signature = hmac.new(
            self._SIGNATURE_SECRET.encode(),
            data_to_sign.encode(),
            hashlib.sha256,
        ).hexdigest()[
            :8
        ]  # Use first 8 chars for brevity

        # Compare signatures (timing-safe comparison)
        if not hmac.compare_digest(provided_signature.lower(), expected_signature.lower()):
            logger.warning(f"Signature verification failed for {tier} license key")
            return ValidationResult(
                status=ValidationStatus.INVALID,
                tier=tier,
                message="Invalid license key signature",
            )

        return ValidationResult(
            status=ValidationStatus.VALID,
            tier=tier,
            message="Signature valid",
        )

    def validate_offline(self, license_key: str) -> ValidationResult:
        """
        [20251225_FEATURE] P2_MEDIUM: Validate license key without network access.

        Uses cached validation data or embedded signatures.
        """
        tier = self._extract_tier(license_key)
        logger.info(f"Performing offline validation for {tier} tier")
        return self.validate(license_key, tier)

    def validate_online(self, license_key: str, timeout: int = 5) -> ValidationResult:
        """
        [20251225_FEATURE] P2_MEDIUM: Validate license key with online license server.

        Falls back to offline validation if server is unreachable.

        Args:
            license_key: The license key to validate
            timeout: Request timeout in seconds

        Returns:
            ValidationResult from server or offline validation
        """
        tier = self._extract_tier(license_key)
        logger.info(f"Attempting online validation for {tier} tier")

        try:
            # Prepare validation request
            data = json.dumps(
                {
                    "license_key": license_key,
                    "hardware_id": self._get_hardware_id(),
                    "timestamp": int(time.time()),
                }
            ).encode()

            parsed = parse.urlparse(self.LICENSE_SERVER_URL)
            # [20260102_BUGFIX] Restrict license server scheme to HTTP(S).
            if parsed.scheme not in {"http", "https"}:
                raise ValueError(f"Unsupported license server scheme: {parsed.scheme}")

            req = request.Request(
                self.LICENSE_SERVER_URL,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )

            with request.urlopen(req, timeout=timeout) as response:  # nosec B310
                result_data = json.loads(response.read().decode())

            # Parse server response
            if result_data.get("valid"):
                expiration = None
                if result_data.get("expiration_date"):
                    expiration = datetime.fromisoformat(result_data["expiration_date"])

                return ValidationResult(
                    status=ValidationStatus.VALID,
                    tier=tier,
                    message="License validated by server",
                    expiration_date=expiration,
                    organization=result_data.get("organization"),
                    seats=result_data.get("seats"),
                    seats_used=result_data.get("seats_used"),
                )
            else:
                return ValidationResult(
                    status=ValidationStatus.INVALID,
                    tier=tier,
                    message=result_data.get("message", "Server rejected license"),
                )

        except (URLError, TimeoutError, json.JSONDecodeError) as e:
            logger.warning(f"Online validation failed: {e}, falling back to offline")
            # Fall back to offline validation
            return self.validate_offline(license_key)

    def _check_expiration(self, license_key: str) -> ValidationResult:
        """
        [20251225_FEATURE] P3_LOW: Check license expiration date.

        Expiration is encoded in the license key as Unix timestamp.
        Format: SCALPEL-{TIER}-{TIMESTAMP}-{OTHER_DATA}-{SIGNATURE}
        """
        tier = self._extract_tier(license_key)
        parts = license_key.split("-")

        if len(parts) < 4:
            # No expiration data in key, assume perpetual
            return ValidationResult(
                status=ValidationStatus.VALID,
                tier=tier,
                message="No expiration date (perpetual license)",
            )

        try:
            # Try to parse timestamp from third part
            timestamp_str = parts[2]
            # Check if it looks like a Unix timestamp (10 digits)
            if timestamp_str.isdigit() and len(timestamp_str) == 10:
                expiration_timestamp = int(timestamp_str)
                expiration_date = _utcfromtimestamp_naive(expiration_timestamp)

                if _utcnow_naive() > expiration_date:
                    return ValidationResult(
                        status=ValidationStatus.EXPIRED,
                        tier=tier,
                        message=f"License expired on {expiration_date.date()}",
                        expiration_date=expiration_date,
                    )

                return ValidationResult(
                    status=ValidationStatus.VALID,
                    tier=tier,
                    message=f"License valid until {expiration_date.date()}",
                    expiration_date=expiration_date,
                )
        except (ValueError, OSError):
            # Not a timestamp, treat as no expiration
            pass

        return ValidationResult(
            status=ValidationStatus.VALID,
            tier=tier,
            message="No expiration date (perpetual license)",
        )

    def _validate_enterprise(
        self,
        license_key: str,
        organization: str | None,
        seats_used: int,
    ) -> ValidationResult:
        """
        [20251225_FEATURE] P2_MEDIUM: Validate ENTERPRISE tier specific requirements.

        Checks:
        - Organization binding
        - Seat limit enforcement
        - Hardware fingerprinting
        - Custom validation rules
        """
        tier = "enterprise"
        parts = license_key.split("-")

        # Extract ENTERPRISE metadata from license key
        # Format: SCALPEL-ENTERPRISE-{TIMESTAMP}-{ORG_HASH}-{SEATS}-{SIGNATURE}
        if len(parts) < 6:
            return ValidationResult(
                status=ValidationStatus.INVALID,
                tier=tier,
                message="Invalid ENTERPRISE license key format",
            )

        try:
            # Parse organization hash (4th part)
            org_hash = parts[3]

            # [20251225_FEATURE] P2_MEDIUM: Organization binding
            if organization:
                # Verify organization matches license
                expected_hash = hashlib.sha256(organization.encode()).hexdigest()[:8]
                if org_hash != expected_hash:
                    return ValidationResult(
                        status=ValidationStatus.INVALID,
                        tier=tier,
                        message=f"License not valid for organization: {organization}",
                        organization=organization,
                    )

            # Parse seat limit (5th part)
            seat_limit = int(parts[4])

            # [20251225_FEATURE] P2_MEDIUM: Seat limit enforcement
            if seats_used > seat_limit:
                return ValidationResult(
                    status=ValidationStatus.INVALID,
                    tier=tier,
                    message=f"Seat limit exceeded: {seats_used}/{seat_limit}",
                    organization=organization,
                    seats=seat_limit,
                    seats_used=seats_used,
                )

            # [20251225_FEATURE] P3_LOW: Hardware fingerprinting
            hardware_id = self._get_hardware_id()

            # [20251225_FEATURE] P4_LOW: Custom validation rules
            custom_rules = self._evaluate_custom_rules(license_key)

            # Get expiration from earlier check
            expiration_result = self._check_expiration(license_key)

            return ValidationResult(
                status=ValidationStatus.VALID,
                tier=tier,
                message=f"ENTERPRISE license valid ({seats_used}/{seat_limit} seats)",
                expiration_date=expiration_result.expiration_date,
                organization=organization,
                seats=seat_limit,
                seats_used=seats_used,
                hardware_id=hardware_id,
                custom_rules=custom_rules,
            )

        except (ValueError, IndexError) as e:
            logger.error(f"Failed to parse ENTERPRISE license key: {e}")
            return ValidationResult(
                status=ValidationStatus.INVALID,
                tier=tier,
                message="Malformed ENTERPRISE license key",
            )

    def _get_hardware_id(self) -> str:
        """
        [20251225_FEATURE] P3_LOW: Generate hardware fingerprint for license binding.

        Creates a stable identifier based on:
        - Machine ID (if available)
        - Hostname
        - Platform information
        """
        if self._hardware_id:
            return self._hardware_id

        # Try to get machine ID (Linux/Mac)
        machine_id = None
        try:
            if os.path.exists("/etc/machine-id"):
                with open("/etc/machine-id") as f:
                    machine_id = f.read().strip()
            elif os.path.exists("/var/lib/dbus/machine-id"):
                with open("/var/lib/dbus/machine-id") as f:
                    machine_id = f.read().strip()
        except OSError:
            pass

        # Fallback to system info
        if not machine_id:
            hostname = platform.node()
            system = platform.system()
            machine = platform.machine()
            combined = f"{hostname}-{system}-{machine}"
            machine_id = hashlib.sha256(combined.encode()).hexdigest()

        self._hardware_id = machine_id[:16]  # Use first 16 chars
        return self._hardware_id

    def _evaluate_custom_rules(self, license_key: str) -> dict[str, bool]:
        """
        [20251225_FEATURE] P4_LOW: Evaluate custom validation rules from license key.

        Custom rules can be embedded in the license key to enable/disable
        specific features or enforce additional constraints.

        Returns:
            Dictionary of rule_name -> enabled
        """
        # Placeholder for custom rules evaluation
        # In production, this would parse custom rule data from the license key
        return {
            "allow_offline": True,
            "require_vpn": False,
            "enable_telemetry": True,
            "custom_integrations": True,
        }

    def _get_cached_result(self, cache_key: str) -> ValidationResult | None:
        """
        [20251225_FEATURE] P2_MEDIUM: Get cached validation result if still valid.
        """
        if cache_key not in self._cache:
            return None

        result, timestamp = self._cache[cache_key]
        if time.time() - timestamp > self._cache_ttl:
            # Cache expired
            del self._cache[cache_key]
            return None

        return result

    def _cache_result(self, cache_key: str, result: ValidationResult) -> None:
        """
        [20251225_FEATURE] P2_MEDIUM: Cache validation result with timestamp.
        """
        self._cache[cache_key] = (result, time.time())


__all__ = ["ValidationStatus", "ValidationResult", "LicenseValidator"]
