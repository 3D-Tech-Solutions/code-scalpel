"""Authorization helpers for tier/license decisions.

[20251228_REFACTOR] Centralize tier decision logic so the MCP server can remain a
license consumer. This logic is intended to be portable to a separate license
management service.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from code_scalpel.licensing.jwt_validator import JWTLicenseValidator


_DISABLE_LICENSE_DISCOVERY_ENV_VAR = "CODE_SCALPEL_DISABLE_LICENSE_DISCOVERY"


def _license_discovery_disabled() -> bool:
    return os.getenv(_DISABLE_LICENSE_DISCOVERY_ENV_VAR, "0").strip() == "1"


def compute_effective_tier_for_startup(
    *,
    requested_tier: str | None,
    validator: JWTLicenseValidator,
) -> tuple[str, str | None]:
    """Compute the effective tier for server startup.

    [20251228_BUGFIX] Revoked licenses downgrade to Community instead of
    hard-failing startup, even if Pro/Enterprise was requested.

    Returns:
        (effective_tier, startup_warning_message)
    """

    if requested_tier is not None:
        requested_tier = requested_tier.strip().lower()

    if requested_tier == "free":
        requested_tier = "community"
    if requested_tier == "all":
        requested_tier = "enterprise"

    if requested_tier is not None and requested_tier not in {
        "community",
        "pro",
        "enterprise",
    }:
        raise ValueError(
            "Invalid tier. Expected one of: community, pro, enterprise " "(or set CODE_SCALPEL_TIER/SCALPEL_TIER)"
        )

    # [20251229_BUGFIX] Remote verifier is authoritative when configured.
    # Avoid local JWT signature validation in this mode; only verifier + cache/grace.
    try:
        from .remote_verifier import authorize_token, remote_verifier_configured

        if remote_verifier_configured():
            token = (validator.load_license_token() or "").strip()
            token_present = bool(token)

            if not token_present:
                licensed_tier = "community"
                ent_error = "No license token found"
                decision_allowed = True  # community is always allowed
            else:
                decision = authorize_token(token)
                ent = decision.entitlements
                decision_allowed = bool(decision.allowed)
                licensed_tier = (
                    str(ent.tier or "community").strip().lower()
                    if (decision_allowed and ent is not None)
                    else "community"
                )
                ent_error = (ent.error if ent is not None else None) or "Verifier denied"

            if licensed_tier == "free":
                licensed_tier = "community"
            if licensed_tier == "all":
                licensed_tier = "enterprise"

            tier_rank = {"community": 0, "pro": 1, "enterprise": 2}
            max_allowed_rank = tier_rank.get(licensed_tier, 0)

            if requested_tier is None:
                # No explicit tier requested: run at the verifier-authorized tier.
                return licensed_tier, None

            requested_rank = tier_rank[requested_tier]
            if requested_rank > 0:
                # Paid tier requested: require an authorized verifier decision.
                if token_present and ("revoked" in (str(ent_error).lower())):
                    return "community", "License revoked. Running in Community mode."
                if (not token_present) or (not decision_allowed):
                    # [20260101_TESTABILITY] MCP contract tests set tier via env to
                    # exercise full tool surfaces without provisioning a license.
                    # Only permit this when license discovery is explicitly disabled.
                    if _license_discovery_disabled() and (not token_present):
                        return requested_tier, None
                    raise SystemExit(
                        "License required: Pro/Enterprise tier requested but no valid license was found. "
                        "Ensure the verifier is reachable and a license is saved to the `.code-scalpel` directory or set CODE_SCALPEL_LICENSE_PATH. "
                        "Purchase: http://codescalpel.dev/pricing"
                    )

            effective_tier = requested_tier if requested_rank <= max_allowed_rank else licensed_tier
            return effective_tier, None
    except Exception as exc:
        # If remote verifier is configured, don't fall back to local RS256 validation
        # which may fail with "Could not parse public key" or other errors.
        # Instead, log the verifier error and fail closed to Community tier.
        import logging

        logger = logging.getLogger(__name__)
        logger.error("Remote verifier authorization failed: %s", exc, exc_info=True)

        # If verifier is explicitly configured, fail closed rather than attempting
        # local RS256 validation which requires different key material.
        if remote_verifier_configured():
            logger.warning("Verifier configured but failed - defaulting to Community tier")
            return "community", f"Remote verifier error: {exc}"

        # Otherwise fall through to local validation mode
        logger.debug("Falling back to local JWT validation mode")

    license_data = validator.validate()

    # [20251227_SECURITY] Invalid/expired licenses never grant paid tier.
    if not license_data.is_valid:
        licensed_tier = "community"
    else:
        licensed_tier = (license_data.tier or "community").strip().lower()
    if licensed_tier == "free":
        licensed_tier = "community"
    if licensed_tier == "all":
        licensed_tier = "enterprise"

    tier_rank = {"community": 0, "pro": 1, "enterprise": 2}
    max_allowed_rank = tier_rank.get(licensed_tier, 0)

    if requested_tier is None:
        return licensed_tier, None

    requested_rank = tier_rank[requested_tier]

    # If a paid tier is requested, a license token must be present.
    if requested_rank > 0:
        token_present = bool(validator.load_license_token())
        err = (license_data.error_message or "").lower()
        is_revoked = (not license_data.is_valid) and ("revoked" in err)

        # Revocation is not a hard lockout.
        if is_revoked:
            return "community", "License revoked. Running in Community mode."

        # All other invalid/missing license cases fail closed for paid tiers.
        if (not token_present) or (not license_data.is_valid):
            # [20260101_TESTABILITY] Allow tier override without a license when
            # discovery is explicitly disabled (test harness isolation).
            if _license_discovery_disabled() and (not token_present):
                return requested_tier, None
            raise SystemExit(
                "License required: Pro/Enterprise tier requested but no valid license was found. "
                "Provide --license-file /path/to/license.jwt or set CODE_SCALPEL_LICENSE_PATH. "
                "Purchase: http://codescalpel.dev/pricing"
            )

    # Clamp to the maximum allowed by the license.
    effective_tier = requested_tier if requested_rank <= max_allowed_rank else licensed_tier
    return effective_tier, None
