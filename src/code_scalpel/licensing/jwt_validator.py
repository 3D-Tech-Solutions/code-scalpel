"""
JWT License Validator - Industry-standard license key validation using JWT tokens.

# [20251225_TEST] APPLY_PATCH_PROBE

[20251225_FEATURE] v3.3.0 - JWT-based license validation system
Implements RS256/HS256 signed JWT tokens for Pro and Enterprise tier licensing.

JWT Claims Structure:
{
    "iss": "code-scalpel-licensing",
    "sub": "customer_id_12345",
    "tier": "pro" | "enterprise",
    "features": ["cognitive_complexity", "context_aware_scanning", ...],
    "exp": 1735689600,  # Unix timestamp
    "iat": 1704153600,  # Unix timestamp
    "customer_id": "customer_id_12345",
    "organization": "Acme Corp",
    "seats": 10
}

Key Management:
- Private key (RS256): Used by Code Scalpel to sign licenses (never distributed)
- Public key (RS256): Embedded in distribution for verification
- Secret key (HS256): Alternative for shared secret validation

Security Properties:
- Non-repudiation: Only Code Scalpel can issue valid licenses
- Integrity: Any modification invalidates the signature
- Expiration: Built-in expiration with configurable grace period
- Offline validation: No network required for verification
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)


# [20251228_FEATURE] Runtime license validation cache.
# This is a process-local optimization to avoid re-parsing/verifying the same
# license token repeatedly in long-lived servers (e.g., MCP stdio/http).
_LICENSE_VALIDATION_TTL_SECONDS = 24 * 60 * 60


@dataclass
class _LicenseValidationCacheEntry:
    checked_at_epoch: float
    license_path: str
    license_mtime_ns: int
    license_size: int
    crl_path: str | None
    crl_mtime_ns: int
    crl_size: int
    crl_inline_sha256: str | None
    result: JWTLicenseData


_LICENSE_VALIDATION_CACHE: _LicenseValidationCacheEntry | None = None


def clear_license_cache() -> None:
    """
    Clear the module-level license validation cache.

    [20260122_TEST] Used by tests to ensure tier detection respects
    environment variable overrides by clearing cached license state.
    """
    global _LICENSE_VALIDATION_CACHE
    _LICENSE_VALIDATION_CACHE = None


def _utcnow_naive() -> datetime:
    # [20251228_BUGFIX] Avoid deprecated datetime.utcnow() while preserving
    # existing naive-UTC behavior across the licensing stack.
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _utcfromtimestamp_naive(timestamp: int) -> datetime:
    # [20251228_BUGFIX] Avoid deprecated datetime.utcfromtimestamp() while
    # preserving existing naive-UTC behavior.
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).replace(tzinfo=None)


# [20251227_SECURITY] Default time leeway for JWT validation (clock skew tolerance).
# Industry standard is typically 30-60 seconds for distributed systems.
DEFAULT_CLOCK_SKEW_LEEWAY_SECONDS = 60

# [20251227_SECURITY] HS256 acceptance is DEV/TEST only.
# Do not enable in production deployments.
ALLOW_HS256_ENV_VAR = "CODE_SCALPEL_ALLOW_HS256"

# [20251227_SECURITY] Default issuer/audience for Code Scalpel licenses.
# These can be overridden via environment variables for multi-issuer deployments.
DEFAULT_LICENSE_ISSUER = "code-scalpel"
DEFAULT_LICENSE_AUDIENCE = "code-scalpel-users"

LICENSE_ISSUER_ENV_VAR = "CODE_SCALPEL_LICENSE_ISSUER"
LICENSE_AUDIENCE_ENV_VAR = "CODE_SCALPEL_LICENSE_AUDIENCE"

# [20251227_FEATURE] Key rotation support.
LICENSE_PUBLIC_KEYS_JSON_ENV_VAR = "CODE_SCALPEL_LICENSE_PUBLIC_KEYS_JSON"
LICENSE_PUBLIC_KEYS_PATH_ENV_VAR = "CODE_SCALPEL_LICENSE_PUBLIC_KEYS_PATH"

# [20251227_FEATURE] Optional signed CRL token input for jti revocation checks.
LICENSE_CRL_JWT_ENV_VAR = "CODE_SCALPEL_LICENSE_CRL_JWT"
LICENSE_CRL_PATH_ENV_VAR = "CODE_SCALPEL_LICENSE_CRL_PATH"

# [20251228_FEATURE] Support explicit license file path override.
LICENSE_PATH_ENV_VAR = "CODE_SCALPEL_LICENSE_PATH"

# [20251231_TESTABILITY] Disable filesystem license discovery.
# When set to "1", the validator will not search default locations.
# Explicit CODE_SCALPEL_LICENSE_PATH is still honored.
DISABLE_LICENSE_DISCOVERY_ENV_VAR = "CODE_SCALPEL_DISABLE_LICENSE_DISCOVERY"

# Try to import PyJWT, but make it optional for Community tier
try:
    import jwt
    from jwt.exceptions import (
        DecodeError,
        ExpiredSignatureError,
        InvalidSignatureError,
        InvalidTokenError,
    )

    JWT_AVAILABLE = True
except ImportError:
    JWT_AVAILABLE = False
    logger.warning(
        "PyJWT not installed. Pro/Enterprise license validation unavailable. "
        "Install with: pip install PyJWT cryptography"
    )


class JWTAlgorithm(Enum):
    """Supported JWT signing algorithms."""

    RS256 = "RS256"  # RSA with SHA-256 (recommended for production)
    HS256 = "HS256"  # HMAC with SHA-256 (simpler, shared secret)


@dataclass
class JWTLicenseData:
    """Parsed JWT license data."""

    tier: str
    customer_id: str
    organization: str | None
    features: set[str]
    expiration: datetime
    issued_at: datetime
    seats: int | None
    is_valid: bool
    error_message: str | None = None
    is_expired: bool = False
    days_until_expiration: int | None = None
    raw_claims: dict | None = None

    @property
    def is_in_grace_period(self) -> bool:
        """Check if license is expired but within grace period."""
        if not self.is_expired:
            return False
        if self.days_until_expiration is None:
            return False
        # 7-day grace period
        return self.days_until_expiration >= -7


class JWTLicenseValidator:
    """
    Validate JWT-based license keys for Code Scalpel.

    Supports two validation modes:
    1. RS256: Public key verification (recommended)
    2. HS256: Shared secret verification

    License File Locations (in priority order):
    1. Explicit license file path: CODE_SCALPEL_LICENSE_PATH
    2. Project license: .code-scalpel/license.jwt
    3. User config: ~/.config/code-scalpel/license.jwt
    4. Legacy fallback: ~/.code-scalpel/license.jwt
    5. Legacy fallback: .scalpel-license
    """

    DEFAULT_LICENSE_PATHS = [
        ".code-scalpel/license/license.jwt",  # [20251229_FEATURE] Preferred location
        ".code-Scalpel/license/license.jwt",  # [20251230_BUGFIX] Case-variant compatibility
        ".code-scalpel/license.jwt",  # [20251227_FEATURE] Standard location
        ".code-Scalpel/license.jwt",  # [20251230_BUGFIX] Case-variant compatibility
        "~/.config/code-scalpel/license.jwt",  # [20251227_FEATURE] XDG user license
        "~/.code-scalpel/license.jwt",  # [20251227_FEATURE] Legacy user license
        "~/.code-Scalpel/license.jwt",  # [20251230_BUGFIX] Case-variant compatibility
        ".scalpel-license",  # Legacy location
    ]

    # [20251225_SECURITY] Public key for RS256 verification
    # This is embedded in the distribution and used to verify license signatures
    # The corresponding private key is kept secure by Code Scalpel organization
    # [20250101_FEATURE] Load from public_key/ folder for key rotation support
    @classmethod
    def _load_public_key(cls) -> str:
        """Load the current public key from public_key/ folder or fall back to embedded key."""
        try:
            # Try to load the latest key from the public_key directory
            public_key_dir = Path(__file__).parent / "public_key"
            if public_key_dir.exists():
                # Find the most recent .pem file (sorted by name, which includes date)
                pem_files = sorted(public_key_dir.glob("*.pem"), reverse=True)
                if pem_files:
                    latest_key = pem_files[0].read_text().strip()
                    logger.debug(f"Loaded public key from {pem_files[0].name}")
                    return latest_key
        except Exception as e:
            logger.warning(f"Failed to load public key from file: {e}, using embedded key")

        # Fall back to embedded key for backwards compatibility
        return """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAwMT78H1v+IDkVw+gmhyO
Dmr3BKtz7Sd/nXD8ixDwklv2cllovcNRRcXQZpKCkcbspTSuzM/WQwBn/yryve+r
t01oq2SrhVTnYsQder99rFgVFFH+e5OZVmuG0bjGMMEeXniPni3oGCAaaGb2Scv2
ux0oXcVs7njfZL4U77LYopN9lGc8JiNf5gi9KnGLzCK2MDRfeF/AsqMwd8mz76zI
08B2Qw2IYTC/nPkPT8sAWoYl24LNF1ZAnncQMXqSe6p09OqOVKr+iBst9x19MCfF
eGTuegrYAsAfAzRT4z6yecFX7CQFigoW/ak3aaKdyIl4J5gLIbMv3INbVWVi5ec5
BwIDAQAB
-----END PUBLIC KEY-----""".strip()

    PUBLIC_KEY_PEM = _load_public_key.__func__(object)  # Call classmethod as static

    def __init__(
        self,
        public_key: str | None = None,
        secret_key: str | None = None,
        algorithm: JWTAlgorithm = JWTAlgorithm.RS256,
    ):
        """
        Initialize JWT license validator.

        Args:
            public_key: RSA public key in PEM format (for RS256)
            secret_key: Shared secret (for HS256)
            algorithm: JWT signing algorithm to use (defaults to RS256)

        [20251227_BUGFIX] Auto-detect algorithm from token if both keys are available
        [20250101_FEATURE] Load public key from public_key/ folder by default
        """
        if not JWT_AVAILABLE:
            logger.warning("PyJWT not available - license validation disabled")
            self.enabled = False
            return

        self.enabled = True
        self.algorithm = algorithm
        self.public_key = public_key or self._load_public_key()
        self.secret_key = secret_key or os.getenv("CODE_SCALPEL_SECRET_KEY")

        # [20251227_SECURITY] Pin issuer/audience for license verification.
        # These defaults are safe because signature verification is still required.
        self.expected_issuer = os.getenv(LICENSE_ISSUER_ENV_VAR, DEFAULT_LICENSE_ISSUER)
        # [20260101_BUGFIX] Tests and legacy tokens use `aud=code-scalpel`, while
        # newer defaults use `aud=code-scalpel-users`. Accept both by default
        # unless an explicit audience override is configured.
        env_audience = os.getenv(LICENSE_AUDIENCE_ENV_VAR)
        if env_audience is not None:
            self.expected_audience = env_audience
        else:
            # PyJWT accepts an iterable for `audience`.
            self.expected_audience = [DEFAULT_LICENSE_AUDIENCE, "code-scalpel"]

        # [20251227_FEATURE] Optional key rotation via kid→public key mapping.
        self.public_keys_by_kid = self._load_public_keys_by_kid()

        # [20251227_SECURITY] HS256 is dev/test-only and must be explicitly enabled.
        # This prevents accidentally accepting shared-secret tokens in production.
        allow_hs256 = os.getenv(ALLOW_HS256_ENV_VAR, "0").strip() == "1"

        # [20251227_BUGFIX] Support both algorithms if both keys are available
        self.supported_algorithms = []
        if self.public_key:
            self.supported_algorithms.append(JWTAlgorithm.RS256.value)
        if self.secret_key and allow_hs256:
            self.supported_algorithms.append(JWTAlgorithm.HS256.value)

        if algorithm == JWTAlgorithm.RS256 and not self.public_key:
            logger.error("RS256 algorithm requires a public key")
            self.enabled = False
        elif algorithm == JWTAlgorithm.HS256 and not self.secret_key:
            logger.warning("HS256 algorithm requires a secret key - set CODE_SCALPEL_SECRET_KEY")
            self.enabled = False

    def _scan_directory_for_license(self, directory: Path) -> Path | None:
        """
        Scan directory for license files matching pattern.
        Returns the most recently modified file if multiple exist.
        """
        if not directory.exists() or not directory.is_dir():
            return None

        # Look for code_scalpel_license*.jwt (downloaded files)
        candidates = list(directory.glob("code_scalpel_license*.jwt"))
        # Also look for code-scalpel-license*.jwt (common download naming)
        candidates.extend(directory.glob("code-scalpel-license*.jwt"))
        # Also look for license*.jwt (e.g. license (1).jwt)
        candidates.extend(directory.glob("license*.jwt"))
        # Also look for *.license.jwt (repo/dev naming like enterprise.license.jwt)
        candidates.extend(directory.glob("*.license.jwt"))

        if not candidates:
            return None

        # Sort by modification time, newest first
        candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)

        logger.debug(f"Found candidate licenses in {directory}: {[p.name for p in candidates]}")
        return candidates[0]

    def find_license_file(self) -> Path | None:
        """
        Find license file in standard locations.

        Returns:
            Path to license file, or None if not found
        """
        # [20251228_FEATURE] Allow explicit path override for deployments and CLI wiring.
        explicit_path = os.getenv(LICENSE_PATH_ENV_VAR)
        if explicit_path:
            path = Path(explicit_path).expanduser()
            if path.exists() and path.is_file():
                logger.debug(f"Found license file from {LICENSE_PATH_ENV_VAR}: {path}")
                return path
            logger.debug(f"{LICENSE_PATH_ENV_VAR} is set but not a readable file: {path}")

        if os.getenv(DISABLE_LICENSE_DISCOVERY_ENV_VAR, "0").strip() == "1":
            logger.debug(f"{DISABLE_LICENSE_DISCOVERY_ENV_VAR}=1; skipping license discovery")
            return None

        # 1. Check for exact matches in standard locations
        for path_str in self.DEFAULT_LICENSE_PATHS:
            path = Path(path_str).expanduser()
            if path.exists() and path.is_file():
                logger.debug(f"Found license file: {path}")
                return path

        # 2. Smart discovery: Scan standard directories for matching files
        # This handles cases where users download the file and don't rename it
        # [20250108_BUGFIX] Removed archive directories - archive is for expired/old licenses
        search_dirs = [
            Path(".code-scalpel/license").expanduser(),
            Path(".code-scalpel").expanduser(),
            Path(".code-Scalpel/license").expanduser(),
            Path(".code-Scalpel").expanduser(),
            Path("~/.config/code-scalpel").expanduser(),
            Path("~/.code-scalpel").expanduser(),
            Path("~/.code-Scalpel").expanduser(),
        ]

        for directory in search_dirs:
            found = self._scan_directory_for_license(directory)
            if found:
                logger.debug(f"Smart discovery found license: {found}")
                return found

        logger.debug("No license file found in standard locations")
        return None

    def load_license_token(self) -> str | None:
        """
        Load license token from environment or file.

        Priority:
        1. License file from CODE_SCALPEL_LICENSE_PATH or find_license_file()

        Returns:
            License token string, or None if not found
        """
        # [20251227_SECURITY] File-only discovery: do not accept license tokens via env.
        # Environment variables are prone to accidental leaks in logs/process listings.
        license_file = self.find_license_file()
        if license_file:
            try:
                token = license_file.read_text().strip()
                logger.debug(f"Loaded license from file: {license_file}")
                return token
            except Exception as e:
                logger.error(f"Failed to read license file {license_file}: {e}")
                return None

        logger.debug("No license token found")
        return None

    def _load_public_keys_by_kid(self) -> dict[str, str]:
        """Load a kid→public key mapping for RS256 verification.

        [20251227_FEATURE] Supports key rotation without changing shipped code.
        Accepted sources (highest priority first):
        - CODE_SCALPEL_LICENSE_PUBLIC_KEYS_JSON (JSON dict kid→PEM)
        - CODE_SCALPEL_LICENSE_PUBLIC_KEYS_PATH (path to JSON file)
        """

        raw_json = os.getenv(LICENSE_PUBLIC_KEYS_JSON_ENV_VAR)
        if raw_json:
            try:
                parsed = json.loads(raw_json)
                if isinstance(parsed, dict):
                    return {str(k): str(v) for k, v in parsed.items() if isinstance(k, str) and isinstance(v, str)}
            except Exception as e:
                logger.warning(f"Failed to parse {LICENSE_PUBLIC_KEYS_JSON_ENV_VAR}: {e}")

        key_path = os.getenv(LICENSE_PUBLIC_KEYS_PATH_ENV_VAR)
        if key_path:
            try:
                content = Path(key_path).expanduser().read_text().strip()
                parsed = json.loads(content)
                if isinstance(parsed, dict):
                    return {str(k): str(v) for k, v in parsed.items() if isinstance(k, str) and isinstance(v, str)}
            except Exception as e:
                logger.warning(f"Failed to load keyset from {key_path}: {e}")

        return {}

    def _resolve_rs256_verify_key(self, token: str) -> str:
        """Resolve the RS256 verification key, considering optional kid rotation."""

        try:
            header = jwt.get_unverified_header(token)
            kid = header.get("kid")
        except Exception:
            kid = None

        if kid and isinstance(kid, str):
            key = self.public_keys_by_kid.get(kid)
            if key:
                return key

        return self.public_key

    def _load_crl_token(self) -> str | None:
        """Load an optional signed CRL token for revocation checks."""

        inline = os.getenv(LICENSE_CRL_JWT_ENV_VAR)
        if inline:
            return inline.strip()

        path = os.getenv(LICENSE_CRL_PATH_ENV_VAR)
        if path:
            try:
                return Path(path).expanduser().read_text().strip()
            except Exception as e:
                logger.warning(f"Failed to read CRL token from {path}: {e}")
                return None

        return None

    def _revocation_error_if_revoked(
        self,
        jti: str,
        *,
        license_algorithm: str | None = None,
    ) -> str | None:
        """Return an error message if the given jti is revoked.

        [20251227_FEATURE] Supports signed CRL tokens containing a `revoked` list.
        If a CRL is configured but invalid/unverifiable, fail closed.
        """

        crl_token = self._load_crl_token()
        if not crl_token:
            return None

        try:
            try:
                header = jwt.get_unverified_header(crl_token)
                crl_alg = header.get("alg")
            except Exception:
                crl_alg = None

            algorithm_value = crl_alg or JWTAlgorithm.RS256.value

            # If validating an HS256 dev license, ignore any RS256 CRL that may
            # be present from prior runs/tests or a production environment.
            if license_algorithm == JWTAlgorithm.HS256.value and algorithm_value != JWTAlgorithm.HS256.value:
                return None

            # For RS256 production licenses, treat CRL misconfiguration as fatal.
            if license_algorithm == JWTAlgorithm.RS256.value and algorithm_value != JWTAlgorithm.RS256.value:
                return "License revocation list algorithm mismatch"
            if algorithm_value not in {
                JWTAlgorithm.RS256.value,
                JWTAlgorithm.HS256.value,
            }:
                return "License revocation list uses unsupported algorithm"

            if algorithm_value not in self.supported_algorithms:
                return "License revocation list algorithm not enabled"

            if algorithm_value == JWTAlgorithm.RS256.value:
                verify_key = self._resolve_rs256_verify_key(crl_token)
            else:
                verify_key = self.secret_key
                if not verify_key:
                    return "License revocation list requires CODE_SCALPEL_SECRET_KEY"

            crl_claims = jwt.decode(
                crl_token,
                verify_key,
                algorithms=[algorithm_value],
                issuer=self.expected_issuer,
                audience=self.expected_audience,
                options={
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_iat": False,
                    "require": ["iss", "aud", "exp", "iat"],
                },
                leeway=DEFAULT_CLOCK_SKEW_LEEWAY_SECONDS,
            )

            revoked_list = crl_claims.get("revoked", [])
            if not isinstance(revoked_list, list):
                revoked_list = []

            if jti in {str(x) for x in revoked_list}:
                return "License revoked"

            return None
        except Exception as e:
            logger.warning(f"Failed to validate CRL token: {e}")
            # HS256 is DEV/TEST only; do not allow a lingering/unverifiable CRL
            # configuration (often from other tests) to brick local dev licenses.
            if license_algorithm == JWTAlgorithm.HS256.value:
                return None
            return "License revocation list invalid"

    def validate_token(self, token: str) -> JWTLicenseData:
        """
        Validate a JWT license token.

        Args:
            token: JWT token string

        Returns:
            JWTLicenseData with validation results
        """
        if not self.enabled:
            return JWTLicenseData(
                tier="community",
                customer_id="",
                organization=None,
                features=set(),
                expiration=_utcnow_naive(),
                issued_at=_utcnow_naive(),
                seats=None,
                is_valid=False,
                error_message="JWT validation not available (PyJWT not installed)",
            )

        try:
            # [20251227_BUGFIX] Auto-detect algorithm from token header
            # If both RS256 and HS256 keys are available, we support both
            try:
                header = jwt.get_unverified_header(token)
                token_algorithm = header.get("alg")
            except Exception:
                token_algorithm = None

            algorithm_value = token_algorithm or self.algorithm.value
            if algorithm_value not in {
                JWTAlgorithm.RS256.value,
                JWTAlgorithm.HS256.value,
            }:
                return self._create_invalid_license(f"Unsupported token algorithm: {algorithm_value}")

            # Verify the detected algorithm is supported
            if algorithm_value not in self.supported_algorithms:
                return self._create_invalid_license(
                    f"Token uses {algorithm_value} but validator only supports {self.supported_algorithms}"
                )

            # Determine verification key based on algorithm
            if algorithm_value == JWTAlgorithm.RS256.value:
                verify_key = self._resolve_rs256_verify_key(token)
            else:
                verify_key = self.secret_key
                if not verify_key:
                    return self._create_invalid_license("HS256 token requires CODE_SCALPEL_SECRET_KEY")

            # Decode and verify JWT
            claims = jwt.decode(
                token,
                verify_key,
                algorithms=[algorithm_value],  # Only allow the detected algorithm
                issuer=self.expected_issuer,
                audience=self.expected_audience,
                options={
                    "verify_signature": True,
                    "verify_exp": True,
                    # [20251225_BUGFIX] Avoid failing validation on minor clock skew.
                    # We require `iat` for traceability but do not treat it as a
                    # not-before constraint.
                    "verify_iat": False,
                    "require": ["tier", "exp", "iat", "sub", "iss", "aud"],
                },
                # [20251227_SECURITY] Add leeway for clock skew
                leeway=DEFAULT_CLOCK_SKEW_LEEWAY_SECONDS,
            )

            # Parse claims
            tier = claims.get("tier", "community")
            customer_id = claims.get("sub", "")
            organization = claims.get("organization")
            features = set(claims.get("features", []))
            exp_timestamp = claims.get("exp")
            iat_timestamp = claims.get("iat")
            seats = claims.get("seats")

            # [20251227_SECURITY] Paid tiers require a stable token id (jti).
            if tier in {"pro", "enterprise"}:
                jti = claims.get("jti")
                if not jti:
                    return self._create_invalid_license("Missing required claim: jti")

                revocation_error = self._revocation_error_if_revoked(
                    str(jti),
                    license_algorithm=algorithm_value,
                )
                if revocation_error:
                    return self._create_invalid_license(revocation_error)

            expiration = _utcfromtimestamp_naive(exp_timestamp)
            issued_at = _utcfromtimestamp_naive(iat_timestamp)

            # Calculate days until expiration
            delta = expiration - _utcnow_naive()
            days_until_exp = max(-30, delta.days)  # Cap at -30 for display

            return JWTLicenseData(
                tier=tier,
                customer_id=customer_id,
                organization=organization,
                features=features,
                expiration=expiration,
                issued_at=issued_at,
                seats=seats,
                is_valid=True,
                is_expired=False,
                days_until_expiration=days_until_exp,
                raw_claims=claims,
            )

        except ExpiredSignatureError:
            # [20251227_SECURITY] Token is expired, but signature must still be verified.
            # We re-decode with signature verification ON and time checks OFF to safely
            # inspect claims for UX/telemetry without enabling an auth bypass.
            try:
                try:
                    header = jwt.get_unverified_header(token)
                    token_algorithm = header.get("alg")
                except Exception:
                    token_algorithm = None

                algorithm_value = token_algorithm or self.algorithm.value
                if algorithm_value not in {
                    JWTAlgorithm.RS256.value,
                    JWTAlgorithm.HS256.value,
                }:
                    return self._create_invalid_license(f"Unsupported token algorithm: {algorithm_value}")

                if algorithm_value not in self.supported_algorithms:
                    return self._create_invalid_license(
                        f"Token uses {algorithm_value} but validator only supports {self.supported_algorithms}"
                    )

                if algorithm_value == JWTAlgorithm.RS256.value:
                    verify_key = self._resolve_rs256_verify_key(token)
                else:
                    verify_key = self.secret_key
                    if not verify_key:
                        return self._create_invalid_license("HS256 token requires CODE_SCALPEL_SECRET_KEY")

                # For expired tokens we still require a valid signature, but we
                # intentionally skip issuer/audience checks to allow UX/testing
                # to inspect claims even if deployments vary these values.
                claims = jwt.decode(
                    token,
                    verify_key,
                    algorithms=[algorithm_value],
                    options={
                        "verify_signature": True,
                        "verify_exp": False,
                        "verify_iat": False,
                        "verify_nbf": False,
                        "verify_aud": False,
                        "verify_iss": False,
                        "require": ["tier", "exp", "iat", "sub", "iss", "aud"],
                    },
                    leeway=DEFAULT_CLOCK_SKEW_LEEWAY_SECONDS,
                )

                exp_timestamp = claims.get("exp")
                expiration = _utcfromtimestamp_naive(exp_timestamp)
                delta = expiration - _utcnow_naive()
                days_until_exp = delta.days

                return JWTLicenseData(
                    tier=claims.get("tier", "community"),
                    customer_id=claims.get("sub", ""),
                    organization=claims.get("organization"),
                    features=set(claims.get("features", [])),
                    expiration=expiration,
                    issued_at=_utcfromtimestamp_naive(claims.get("iat")),
                    seats=claims.get("seats"),
                    is_valid=False,
                    is_expired=True,
                    days_until_expiration=days_until_exp,
                    error_message=f"License expired {abs(days_until_exp)} days ago",
                    raw_claims=claims,
                )
            except Exception as e:
                logger.error(f"Failed to decode expired token with verified signature: {e}")
                return self._create_invalid_license("License expired")

        except InvalidSignatureError:
            logger.error("Invalid license signature - token may be tampered")
            return self._create_invalid_license("Invalid signature - license may be tampered")

        except DecodeError as e:
            logger.error(f"Failed to decode license token: {e}")
            return self._create_invalid_license(f"Invalid token format: {e}")

        except InvalidTokenError as e:
            logger.error(f"Invalid license token: {e}")
            return self._create_invalid_license(f"Invalid token: {e}")

        except Exception as e:
            logger.error(f"Unexpected error validating license: {e}")
            return self._create_invalid_license(f"Validation error: {e}")

    def validate(self) -> JWTLicenseData:
        """
        Validate the current license from environment/file.

        Returns:
            JWTLicenseData with validation results
        """
        global _LICENSE_VALIDATION_CACHE

        license_file = self.find_license_file()
        if not license_file:
            # No license found - default to community
            return JWTLicenseData(
                tier="community",
                customer_id="",
                organization=None,
                features=set(),
                expiration=_utcnow_naive(),
                issued_at=_utcnow_naive(),
                seats=None,
                is_valid=True,  # Community is always valid
                error_message=None,
            )

        # [20251228_FEATURE] Cache local license validation results for 24h when the
        # license file is unchanged. This reduces repeated crypto work.
        #
        # [20251231_BUGFIX] Include CRL state in the cache key so revocations apply
        # immediately even if the license file does not change.
        try:
            stat = license_file.stat()
            mtime_ns = int(getattr(stat, "st_mtime_ns", int(stat.st_mtime * 1_000_000_000)))
            size = int(getattr(stat, "st_size", -1))
        except Exception:
            mtime_ns = -1
            size = -1

        crl_path: str | None = None
        crl_mtime_ns: int = -1
        crl_size: int = -1
        crl_inline_sha256: str | None = None

        inline_crl = os.getenv(LICENSE_CRL_JWT_ENV_VAR)
        if inline_crl:
            try:
                import hashlib

                crl_inline_sha256 = hashlib.sha256(inline_crl.strip().encode("utf-8")).hexdigest()
            except Exception:
                crl_inline_sha256 = ""
        else:
            env_crl_path = os.getenv(LICENSE_CRL_PATH_ENV_VAR)
            if env_crl_path:
                try:
                    p = Path(env_crl_path).expanduser()
                    crl_path = str(p)
                    st = p.stat()
                    crl_mtime_ns = int(getattr(st, "st_mtime_ns", int(st.st_mtime * 1_000_000_000)))
                    crl_size = int(getattr(st, "st_size", -1))
                except Exception:
                    # If CRL is configured but unreadable, we still want to bust cache.
                    crl_path = str(env_crl_path)
                    crl_mtime_ns = -2
                    crl_size = -2

        now = float(time.time())
        cache = _LICENSE_VALIDATION_CACHE
        if (
            cache is not None
            and cache.license_path == str(license_file)
            and cache.license_mtime_ns == mtime_ns
            and cache.license_size == size
            and cache.crl_path == crl_path
            and cache.crl_mtime_ns == crl_mtime_ns
            and cache.crl_size == crl_size
            and cache.crl_inline_sha256 == crl_inline_sha256
            and (now - float(cache.checked_at_epoch)) <= _LICENSE_VALIDATION_TTL_SECONDS
        ):
            return cache.result

        try:
            token = license_file.read_text().strip()
        except Exception as e:
            logger.error(f"Failed to read license file {license_file}: {e}")
            return self._create_invalid_license(f"Failed to read license file: {e}")

        result = self.validate_token(token)
        _LICENSE_VALIDATION_CACHE = _LicenseValidationCacheEntry(
            checked_at_epoch=now,
            license_path=str(license_file),
            license_mtime_ns=mtime_ns,
            license_size=size,
            crl_path=crl_path,
            crl_mtime_ns=crl_mtime_ns,
            crl_size=crl_size,
            crl_inline_sha256=crl_inline_sha256,
            result=result,
        )
        return result

    def get_current_tier(self) -> str:
        """
        Get the current tier based on license validation.

        Returns:
            Tier string: "community", "pro", or "enterprise"
        """
        license_data = self.validate()

        # If license is valid, return the licensed tier
        if license_data.is_valid:
            return license_data.tier

        # Otherwise, downgrade to community
        logger.info(f"Defaulting to community tier: {license_data.error_message}")
        return "community"

    def _create_invalid_license(self, error_message: str) -> JWTLicenseData:
        """Create an invalid license data object."""
        return JWTLicenseData(
            tier="community",
            customer_id="",
            organization=None,
            features=set(),
            expiration=_utcnow_naive(),
            issued_at=_utcnow_naive(),
            seats=None,
            is_valid=False,
            error_message=error_message,
        )


# [20251225_FEATURE] Helper function for tool handlers
def get_current_tier() -> str:
    """
    Get the current tier for the running Code Scalpel instance.

    This is the primary function tool handlers should use to determine tier.

    Returns:
        Tier string: "community", "pro", or "enterprise"
    """
    validator = JWTLicenseValidator()

    # [20251229_BUGFIX] In Beta/Prod, the remote verifier is authoritative when configured.
    # Do NOT fall back to local signature verification if the verifier is down;
    # only offline grace (based on cached entitlements + license hash) is allowed.
    try:
        from code_scalpel.licensing.remote_verifier import (
            authorize_token,
            remote_verifier_configured,
        )

        if remote_verifier_configured():
            token = validator.load_license_token()
            if not token:
                return "community"

            decision = authorize_token(token)
            ent = decision.entitlements
            if decision.allowed and ent is not None:
                return str(ent.tier or "community").strip().lower()

            if ent is not None and ent.error:
                logger.info("Defaulting to community tier: %s", ent.error)
            return "community"
    except Exception as exc:
        logger.warning("Remote verifier tier check failed: %s", exc)
        if os.getenv("CODE_SCALPEL_LICENSE_VERIFIER_URL"):
            return "community"

    return validator.get_current_tier()


def get_license_info() -> dict:
    """
    Get detailed license information.

    Returns:
        Dictionary with license details
    """
    validator = JWTLicenseValidator()

    # If a remote verifier is configured, it is authoritative.
    # We still return the same shape as the local validator helper.
    try:
        from code_scalpel.licensing.remote_verifier import (
            authorize_token,
            remote_verifier_configured,
        )

        if remote_verifier_configured():
            token = validator.load_license_token()
            if token:
                decision = authorize_token(token)
                ent = decision.entitlements

                exp_dt = _utcfromtimestamp_naive(int(ent.exp)) if ent is not None and ent.exp else _utcnow_naive()
                days_until_exp = (exp_dt - _utcnow_naive()).days

                return {
                    "tier": str((ent.tier if ent is not None else "community") or "community").strip().lower(),
                    "customer_id": (str(ent.customer_id or "") if ent is not None else ""),
                    "organization": ent.organization if ent is not None else None,
                    "features": sorted(list(ent.features)) if ent is not None else [],
                    "expiration": exp_dt.isoformat(),
                    # Remote verifier does not currently provide iat.
                    "issued_at": "",
                    "seats": ent.seats if ent is not None else None,
                    "is_valid": bool(decision.allowed and ent is not None and ent.valid),
                    "is_expired": (
                        bool(_utcnow_naive().timestamp() >= float(ent.exp)) if ent is not None and ent.exp else False
                    ),
                    # Map offline grace to the closest existing concept.
                    "is_in_grace_period": bool(decision.reason == "offline_grace"),
                    "days_until_expiration": days_until_exp,
                    "error_message": (ent.error if ent is not None and not decision.allowed else None),
                }
    except Exception as exc:
        logger.warning("Remote verifier license info check failed: %s", exc)
        if os.getenv("CODE_SCALPEL_LICENSE_VERIFIER_URL"):
            # Verifier is configured but failed unexpectedly: fail closed to community.
            return {
                "tier": "community",
                "customer_id": "",
                "organization": None,
                "features": [],
                "expiration": _utcnow_naive().isoformat(),
                "issued_at": "",
                "seats": None,
                "is_valid": False,
                "is_expired": False,
                "is_in_grace_period": False,
                "days_until_expiration": None,
                "error_message": "Remote verifier error",
            }

    license_data = validator.validate()

    # [20251225_BUGFIX] Restore helper output (was accidentally truncated).
    return {
        "tier": license_data.tier,
        "customer_id": license_data.customer_id,
        "organization": license_data.organization,
        "features": sorted(license_data.features),
        "expiration": license_data.expiration.isoformat(),
        "issued_at": license_data.issued_at.isoformat(),
        "seats": license_data.seats,
        "is_valid": license_data.is_valid,
        "is_expired": license_data.is_expired,
        "is_in_grace_period": license_data.is_in_grace_period,
        "days_until_expiration": license_data.days_until_expiration,
        "error_message": license_data.error_message,
    }
