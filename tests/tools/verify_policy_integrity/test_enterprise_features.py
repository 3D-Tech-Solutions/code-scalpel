"""
Enterprise feature distinction tests for verify_policy_integrity.

# [20260103_TEST] Phase 3: Enterprise feature tests (2 tests, 2 hours estimated)

Tests verify Enterprise tier features are distinct from Pro tier:
- full_integrity_check vs signature_validation
- Batch verification performance with many files
"""

from pathlib import Path

import pytest


def test_enterprise_full_integrity_check_includes_audit_logging(
    tmp_path: Path,
    create_policy_file,
    create_manifest,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Enterprise full_integrity_check should include audit logging.

    Validates:
    - Enterprise tier has audit_log_entry field populated
    - Pro tier does not have audit logging
    - Audit log includes verification details

    Clarifies: full_integrity_check = signature_validation + audit_logging
    """
    from code_scalpel.mcp.server import _verify_policy_integrity_sync

    policy_dir = tmp_path / ".code-scalpel"
    policy_file = create_policy_file(policy_dir)

    secret = "test-secret-enterprise-audit"
    monkeypatch.setenv("SCALPEL_MANIFEST_SECRET", secret)
    create_manifest(policy_dir, secret, [policy_file.name])

    # Test Pro tier (should have signature validation but NO audit logging)
    pro_result = _verify_policy_integrity_sync(
        policy_dir=str(policy_dir),
        manifest_source="file",
        tier="pro",
    )

    assert pro_result.success is True
    assert pro_result.tier == "pro"
    assert pro_result.signature_validated is True
    assert pro_result.audit_log_entry is None, "Pro tier should NOT have audit logging"

    # Test Enterprise tier (should have both signature validation AND audit logging)
    enterprise_result = _verify_policy_integrity_sync(
        policy_dir=str(policy_dir),
        manifest_source="file",
        tier="enterprise",
    )

    assert enterprise_result.success is True
    assert enterprise_result.tier == "enterprise"
    assert enterprise_result.signature_validated is True
    assert enterprise_result.audit_log_entry is not None, "Enterprise tier MUST have audit logging"

    # Validate audit log structure
    audit = enterprise_result.audit_log_entry
    assert "timestamp" in audit
    assert "action" in audit
    assert audit["action"] == "policy_verification"
    assert audit["tier"] == "enterprise"
    assert "success" in audit
    assert audit["success"] is True
    assert "files_verified" in audit
    assert audit["files_verified"] == 1


def test_batch_verification_performance_with_many_files(
    tmp_path: Path,
    create_multiple_policies,
    create_manifest,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Batch verification with 200+ files should complete successfully.

    Validates:
    - Enterprise tier handles large policy sets
    - All 200+ files are verified
    - Signature validation works at scale
    - Audit log tracks large verification operations

    Performance: Target <5 seconds for 200 files (per roadmap)
    """
    import time

    from code_scalpel.mcp.server import _verify_policy_integrity_sync

    policy_dir = tmp_path / ".code-scalpel"

    # Create 200 policy files (large batch)
    policy_files = create_multiple_policies(policy_dir, 200)

    secret = "test-secret-batch-200"
    monkeypatch.setenv("SCALPEL_MANIFEST_SECRET", secret)
    create_manifest(policy_dir, secret, [pf.name for pf in policy_files])

    # Measure verification time
    start_time = time.time()

    result = _verify_policy_integrity_sync(
        policy_dir=str(policy_dir),
        manifest_source="file",
        tier="enterprise",
    )

    elapsed_time = time.time() - start_time

    # Validate success
    assert result.success is True, f"Batch verification failed: {result.error}"
    assert result.tier == "enterprise"
    assert result.files_verified == 200
    assert result.signature_validated is True
    assert result.audit_log_entry is not None

    # Validate audit log captured batch operation
    audit = result.audit_log_entry
    assert audit["files_verified"] == 200
    assert audit["success"] is True

    # Performance check: Should complete in reasonable time
    # Note: Actual performance depends on hardware, but should be <5s per roadmap
    # We use a generous 10s limit for CI environments
    assert elapsed_time < 10.0, (
        f"Batch verification took {elapsed_time:.2f}s, " f"expected <10s (roadmap target: <5s for 200 files)"
    )

    print(f"\n✅ Batch verification of 200 files completed in {elapsed_time:.3f}s")


def test_enterprise_vs_pro_feature_matrix(
    tmp_path: Path,
    create_policy_file,
    create_manifest,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Comprehensive feature matrix test: Community vs Pro vs Enterprise.

    Validates complete feature differentiation:

    Community:
    - basic_verification ✓
    - signature_validation ✗
    - tamper_detection ✗
    - audit_logging ✗

    Pro:
    - basic_verification ✓
    - signature_validation ✓
    - tamper_detection ✓
    - audit_logging ✗

    Enterprise:
    - basic_verification ✓
    - signature_validation ✓
    - tamper_detection ✓ (full_integrity_check)
    - audit_logging ✓
    """
    from code_scalpel.mcp.server import _verify_policy_integrity_sync

    policy_dir = tmp_path / ".code-scalpel"
    policy_file = create_policy_file(policy_dir)

    secret = "test-secret-feature-matrix"
    monkeypatch.setenv("SCALPEL_MANIFEST_SECRET", secret)
    create_manifest(policy_dir, secret, [policy_file.name])

    # Community tier
    community_result = _verify_policy_integrity_sync(
        policy_dir=str(policy_dir),
        manifest_source="file",
        tier="community",
    )

    assert community_result.success is True
    assert community_result.signature_validated is False
    assert community_result.tamper_detection_enabled is False
    assert community_result.audit_log_entry is None

    # Pro tier
    pro_result = _verify_policy_integrity_sync(
        policy_dir=str(policy_dir),
        manifest_source="file",
        tier="pro",
    )

    assert pro_result.success is True
    assert pro_result.signature_validated is True
    assert pro_result.tamper_detection_enabled is True
    assert pro_result.audit_log_entry is None

    # Enterprise tier
    enterprise_result = _verify_policy_integrity_sync(
        policy_dir=str(policy_dir),
        manifest_source="file",
        tier="enterprise",
    )

    assert enterprise_result.success is True
    assert enterprise_result.signature_validated is True
    assert enterprise_result.tamper_detection_enabled is True
    assert enterprise_result.audit_log_entry is not None

    print("\n✅ Feature matrix validated:")
    print("   Community: basic_verification only")
    print("   Pro:       + signature_validation + tamper_detection")
    print("   Enterprise: + audit_logging (full_integrity_check)")
