"""
Policy file limit enforcement tests for verify_policy_integrity.

# [20260103_TEST] Phase 1: Policy file limit tests (4 tests, 3 hours estimated)

Tests verify that tier limits for max_policy_files are enforced:
- Community: 50 files max
- Pro: 200 files max
- Enterprise: unlimited
"""

from pathlib import Path

import pytest


def test_community_50_policy_files_allowed(
    tmp_path: Path,
    create_multiple_policies,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Community tier: 50 policy files should be allowed (at limit).

    Validates:
    - Community tier max_policy_files = 50 from limits.toml
    - Tool accepts exactly 50 files
    - No error raised at the limit
    """
    from code_scalpel.mcp.server import _verify_policy_integrity_sync

    policy_dir = tmp_path / ".code-scalpel"

    # Create exactly 50 policy files (Community limit)
    create_multiple_policies(policy_dir, 50)

    # Community tier doesn't require secret
    monkeypatch.delenv("SCALPEL_MANIFEST_SECRET", raising=False)

    result = _verify_policy_integrity_sync(
        policy_dir=str(policy_dir),
        manifest_source="file",
        tier="community",
    )

    assert result.success is True, f"Expected success at 50 files, got error: {result.error}"
    assert result.tier == "community"
    assert result.files_verified == 50
    assert result.error is None


def test_community_51_policy_files_rejected(
    tmp_path: Path,
    create_multiple_policies,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Community tier: 51 policy files should be rejected (over limit).

    Validates:
    - Community tier max_policy_files = 50 from limits.toml
    - Tool rejects 51 files with clear error message
    - Error mentions limit and tier
    """
    from code_scalpel.mcp.server import _verify_policy_integrity_sync

    policy_dir = tmp_path / ".code-scalpel"

    # Create 51 policy files (1 over Community limit)
    create_multiple_policies(policy_dir, 51)

    monkeypatch.delenv("SCALPEL_MANIFEST_SECRET", raising=False)

    result = _verify_policy_integrity_sync(
        policy_dir=str(policy_dir),
        manifest_source="file",
        tier="community",
    )

    assert result.success is False, "Expected failure with 51 files on Community tier"
    assert result.tier == "community"
    assert result.error is not None
    assert "51" in result.error, f"Error should mention 51 files: {result.error}"
    assert "50" in result.error, f"Error should mention 50 limit: {result.error}"
    assert "community" in result.error.lower(), f"Error should mention tier: {result.error}"
    assert "limit exceeded" in result.error.lower(), f"Error should be clear: {result.error}"


def test_pro_200_policy_files_allowed(
    tmp_path: Path,
    create_multiple_policies,
    create_manifest,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Pro tier: 200 policy files should be allowed (at limit).

    Validates:
    - Pro tier max_policy_files = 200 from limits.toml
    - Tool accepts exactly 200 files
    - Signature validation still works with many files
    """
    from code_scalpel.mcp.server import _verify_policy_integrity_sync

    policy_dir = tmp_path / ".code-scalpel"

    # Create exactly 200 policy files (Pro limit)
    policy_files = create_multiple_policies(policy_dir, 200)

    # Pro tier requires secret and manifest
    secret = "test-secret-pro-200"
    monkeypatch.setenv("SCALPEL_MANIFEST_SECRET", secret)
    create_manifest(policy_dir, secret, [pf.name for pf in policy_files])

    result = _verify_policy_integrity_sync(
        policy_dir=str(policy_dir),
        manifest_source="file",
        tier="pro",
    )

    assert result.success is True, f"Expected success at 200 files on Pro, got error: {result.error}"
    assert result.tier == "pro"
    assert result.files_verified == 200
    assert result.signature_validated is True
    assert result.error is None


def test_enterprise_unlimited_policy_files(
    tmp_path: Path,
    create_multiple_policies,
    create_manifest,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Enterprise tier: Unlimited policy files (test with 250 > Pro limit).

    Validates:
    - Enterprise tier has no max_policy_files limit
    - Tool accepts >200 files (more than Pro limit)
    - Audit logging still works with many files
    """
    from code_scalpel.mcp.server import _verify_policy_integrity_sync

    policy_dir = tmp_path / ".code-scalpel"

    # Create 250 policy files (exceeds Pro limit of 200)
    policy_files = create_multiple_policies(policy_dir, 250)

    secret = "test-secret-enterprise-unlimited"
    monkeypatch.setenv("SCALPEL_MANIFEST_SECRET", secret)
    create_manifest(policy_dir, secret, [pf.name for pf in policy_files])

    result = _verify_policy_integrity_sync(
        policy_dir=str(policy_dir),
        manifest_source="file",
        tier="enterprise",
    )

    assert result.success is True, f"Expected success with 250 files on Enterprise, got error: {result.error}"
    assert result.tier == "enterprise"
    assert result.files_verified == 250
    assert result.signature_validated is True
    assert result.audit_log_entry is not None
    assert result.error is None
