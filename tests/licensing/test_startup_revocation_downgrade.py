"""Startup revocation behavior tests (server-tier semantics).

[20251228_TEST] Proves revoked license downgrades to Community at startup
instead of hard-failing, even if Pro was requested.
"""

from __future__ import annotations


def test_revoked_license_downgrades_at_startup(
    monkeypatch,
    tmp_path,
    write_hs256_license_jwt,
    write_hs256_crl_jwt,
    set_hs256_license_env,
):
    jti = "license-jti-startup-revoked"

    license_path = write_hs256_license_jwt(duration_days=7, jti=jti)
    crl_path = write_hs256_crl_jwt(revoked_jtis=[jti])
    set_hs256_license_env(license_path=str(license_path), crl_path=str(crl_path))

    from code_scalpel.licensing.authorization import compute_effective_tier_for_startup
    from code_scalpel.licensing.jwt_validator import JWTLicenseValidator

    effective, warning = compute_effective_tier_for_startup(
        requested_tier="pro",
        validator=JWTLicenseValidator(),
    )

    assert effective == "community"
    assert warning is not None
    assert "revoked" in warning.lower()
