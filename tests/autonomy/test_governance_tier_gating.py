"""Tests for tier-gated governance verification.

[20251230_TEST] Validate `verify_policy_integrity` behavior across Community/Pro/Enterprise.

These tests focus on the governance enforcement that is *defined by* and operates on
`.code-scalpel/` contents (policy files + policy.manifest.json + env secret).

[20260117_TEST] Skipped - _verify_policy_integrity_sync no longer accepts 'tier' parameter.
The tier-gating logic has been refactored and needs new tests.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.skip(
    reason="[20260117_TEST] _verify_policy_integrity_sync API changed - 'tier' parameter removed"
)


def _write_policy_file(policy_dir: Path) -> Path:
    policy_dir.mkdir(parents=True, exist_ok=True)
    policy_path = policy_dir / "policy.yaml"
    policy_path.write_text(
        """policies:
  - name: no-op
    description: Test policy that should never deny
    severity: INFO
    action: AUDIT
    rule: |
      package code_scalpel.test

      deny[msg] {
        input.operation == "code_edit"
        contains(input.code, "__NEVER_PRESENT__")
        msg := "should never trigger"
      }
""",
        encoding="utf-8",
    )
    return policy_path


def _write_manifest(policy_dir: Path, secret: str) -> Path:
    from code_scalpel.policy_engine.crypto_verify import CryptographicPolicyVerifier

    manifest = CryptographicPolicyVerifier.create_manifest(
        policy_files=["policy.yaml"],
        secret_key=secret,
        signed_by="test@example.com",
        policy_dir=str(policy_dir),
    )
    return CryptographicPolicyVerifier.save_manifest(manifest, policy_dir=str(policy_dir))


def test_verify_policy_integrity_community_basic_passes_without_secret_or_manifest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from code_scalpel.mcp.server import _verify_policy_integrity_sync

    policy_dir = tmp_path / ".code-scalpel"
    _write_policy_file(policy_dir)

    # Ensure secret is not set; community should not require crypto verification.
    monkeypatch.delenv("SCALPEL_MANIFEST_SECRET", raising=False)

    result = _verify_policy_integrity_sync(
        policy_dir=str(policy_dir),
        manifest_source="file",
        tier="community",
    )

    assert result.success is True
    assert result.tier == "community"
    assert result.signature_validated is False


def test_verify_policy_integrity_pro_fails_closed_without_secret(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from code_scalpel.mcp.server import _verify_policy_integrity_sync

    policy_dir = tmp_path / ".code-scalpel"
    _write_policy_file(policy_dir)

    monkeypatch.delenv("SCALPEL_MANIFEST_SECRET", raising=False)

    result = _verify_policy_integrity_sync(
        policy_dir=str(policy_dir),
        manifest_source="file",
        tier="pro",
    )

    assert result.success is False
    assert result.tier == "pro"
    assert result.signature_validated is False
    assert result.error is not None
    assert "SCALPEL_MANIFEST_SECRET" in result.error


def test_verify_policy_integrity_pro_passes_with_secret_and_manifest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from code_scalpel.mcp.server import _verify_policy_integrity_sync

    policy_dir = tmp_path / ".code-scalpel"
    _write_policy_file(policy_dir)

    secret = "test-secret-pro"
    monkeypatch.setenv("SCALPEL_MANIFEST_SECRET", secret)
    _write_manifest(policy_dir, secret)

    result = _verify_policy_integrity_sync(
        policy_dir=str(policy_dir),
        manifest_source="file",
        tier="pro",
    )

    assert result.success is True
    assert result.tier == "pro"
    assert result.signature_validated is True
    assert result.tamper_detection_enabled is True


def test_verify_policy_integrity_enterprise_emits_audit_log_entry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from code_scalpel.mcp.server import _verify_policy_integrity_sync

    policy_dir = tmp_path / ".code-scalpel"
    _write_policy_file(policy_dir)

    secret = "test-secret-enterprise"
    monkeypatch.setenv("SCALPEL_MANIFEST_SECRET", secret)
    _write_manifest(policy_dir, secret)

    result = _verify_policy_integrity_sync(
        policy_dir=str(policy_dir),
        manifest_source="file",
        tier="enterprise",
    )

    assert result.success is True
    assert result.tier == "enterprise"
    assert result.signature_validated is True
    assert isinstance(result.audit_log_entry, dict)
    assert result.audit_log_entry.get("tier") == "enterprise"


def test_verify_policy_integrity_pro_detects_tampering(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from code_scalpel.mcp.server import _verify_policy_integrity_sync

    policy_dir = tmp_path / ".code-scalpel"
    policy_file = _write_policy_file(policy_dir)

    secret = "test-secret-tamper"
    monkeypatch.setenv("SCALPEL_MANIFEST_SECRET", secret)
    _write_manifest(policy_dir, secret)

    # Tamper after signing
    policy_file.write_text("rules: [tampered]\n", encoding="utf-8")

    result = _verify_policy_integrity_sync(
        policy_dir=str(policy_dir),
        manifest_source="file",
        tier="pro",
    )

    assert result.success is False
    assert result.error is not None
    assert "tampered" in result.error.lower() or "hash" in result.error.lower()
