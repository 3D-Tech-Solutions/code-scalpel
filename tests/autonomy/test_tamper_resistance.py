"""
Tests for Tamper Resistance and Policy Enforcement (v2.5.0 Guardian).

# [20251216_FEATURE] v2.5.0 Guardian P0 - Tamper resistance tests

Tests cover:
- Policy file integrity verification
- Policy file locking (read-only)
- Policy modification prevention
- Override system (TOTP, expiry, single-use)
- Audit log signing and verification
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from code_scalpel.policy_engine import (
    AuditLog,
    Operation,
    OverrideDecision,
    PolicyDecision,
    PolicyModificationError,
    TamperDetectedError,
    TamperResistance,
)


@pytest.fixture
def temp_policy_dir(tmp_path):
    """Create temporary directory for policy files."""
    policy_dir = tmp_path / ".code-scalpel"
    policy_dir.mkdir(parents=True, exist_ok=True)

    # Create a dummy policy file
    policy_file = policy_dir / "policy.yaml"
    policy_file.write_text("# Test policy\nversion: 1.0\n")

    return policy_dir


@pytest.fixture
def tamper_resistance(temp_policy_dir):
    """Create TamperResistance instance with temporary directory."""
    policy_path = temp_policy_dir / "policy.yaml"
    return TamperResistance(policy_path=str(policy_path))


@pytest.fixture
def audit_log(temp_policy_dir):
    """Create AuditLog instance with temporary directory."""
    log_path = temp_policy_dir / "audit.log"
    return AuditLog(log_path=str(log_path))


# =============================================================================
# P0: Tamper Resistance - Policy File Integrity
# =============================================================================


def test_policy_integrity_verification_success(tamper_resistance):
    """Test that policy integrity verification succeeds for unmodified policy."""
    # [20251216_TEST] P0 acceptance criteria
    assert tamper_resistance.verify_policy_integrity() is True


def test_policy_integrity_verification_detects_tampering(tamper_resistance):
    """Test that policy integrity verification detects tampering."""
    # [20251216_TEST] P0 acceptance criteria

    # Make file writable temporarily to tamper with it
    tamper_resistance.policy_path.chmod(0o644)

    # Tamper with policy file
    with open(tamper_resistance.policy_path, "a") as f:
        f.write("\n# Tampered\n")

    # Verify tampering is detected
    with pytest.raises(TamperDetectedError) as exc_info:
        tamper_resistance.verify_policy_integrity()

    assert "integrity check failed" in str(exc_info.value).lower()


def test_policy_file_locking_read_only(temp_policy_dir):
    """Test that policy files are set to read-only."""
    # [20251216_TEST] P0 acceptance criteria

    policy_file = temp_policy_dir / "policy.yaml"
    # Create budget file BEFORE creating TamperResistance instance
    budget_file = temp_policy_dir / "budget.yaml"
    budget_file.write_text("budget: 100\n")

    # Create tamper resistance instance (locks files)
    TamperResistance(policy_path=str(policy_file))

    # Verify policy file is read-only
    stat = policy_file.stat()
    # Mode 0o444 = r--r--r--
    assert (stat.st_mode & 0o777) == 0o444

    # Verify budget file is read-only after locking
    if budget_file.exists():
        stat = budget_file.stat()
        # Should be read-only after locking
        assert (stat.st_mode & 0o777) == 0o444


def test_policy_hash_calculation(tamper_resistance):
    """Test SHA-256 hash calculation for policy file."""
    # [20251216_TEST] P0 acceptance criteria

    # Hash should be non-empty
    assert len(tamper_resistance.policy_hash) == 64  # SHA-256 hex length

    # Recalculating hash should give same result
    new_hash = tamper_resistance._hash_policy_file()
    assert new_hash == tamper_resistance.policy_hash


# =============================================================================
# P0: Tamper Resistance - Policy Modification Prevention
# =============================================================================


def test_prevent_policy_modification_blocks_protected_files(tamper_resistance):
    """Test that policy modification is blocked for protected files."""
    # [20251216_TEST] P0 acceptance criteria

    protected_files = [
        Path(".code-scalpel/policy.yaml"),
        Path(".code-scalpel/budget.yaml"),
        Path("scalpel.policy.yaml"),
    ]

    for protected_file in protected_files:
        operation = Operation(type="file_write", affected_files=[protected_file])

        with pytest.raises(PolicyModificationError) as exc_info:
            tamper_resistance.prevent_policy_modification(operation)

        assert "protected policy file" in str(exc_info.value).lower()


def test_prevent_policy_modification_allows_normal_files(tamper_resistance):
    """Test that normal file operations are allowed."""
    # [20251216_TEST] P0 acceptance criteria

    normal_files = [
        Path("src/main.py"),
        Path("tests/test_foo.py"),
        Path("README.md"),
    ]

    for normal_file in normal_files:
        operation = Operation(type="file_write", affected_files=[normal_file])

        # Should not raise exception
        assert tamper_resistance.prevent_policy_modification(operation) is True


def test_policy_modification_attempt_logged(tamper_resistance):
    """Test that policy modification attempts are logged."""
    # [20251216_TEST] P0 acceptance criteria

    operation = Operation(type="file_write", affected_files=[Path(".code-scalpel/policy.yaml")])

    try:
        tamper_resistance.prevent_policy_modification(operation)
    except PolicyModificationError:
        pass

    # Verify event was logged
    events = tamper_resistance.audit_log.get_events(event_type="POLICY_MODIFICATION_ATTEMPTED")
    assert len(events) > 0
    assert events[-1]["severity"] == "CRITICAL"
    assert ".code-scalpel/policy.yaml" in str(events[-1]["details"])


# =============================================================================
# P0: Override System - TOTP and Human Verification
# =============================================================================


def test_override_system_generates_challenge(tamper_resistance):
    """Test that override system generates challenge."""
    # [20251216_TEST] P0 acceptance criteria

    challenge = tamper_resistance._generate_challenge()
    assert len(challenge) == 32  # hex(16) = 32 chars


def test_override_totp_verification(tamper_resistance):
    """Test TOTP code verification."""
    # [20251216_TEST] P0 acceptance criteria

    challenge = "test_challenge_12345"

    # Generate valid code
    import hashlib
    import hmac

    secret = os.environ.get("SCALPEL_TOTP_SECRET", "default-totp-secret")
    valid_code = hmac.new(secret.encode(), challenge.encode(), hashlib.sha256).hexdigest()[:8]

    # Valid code should pass
    assert tamper_resistance._verify_totp(valid_code, challenge) is True

    # Invalid code should fail
    assert tamper_resistance._verify_totp("invalid", challenge) is False


def test_override_expires_after_time_limit(tamper_resistance):
    """Test that overrides expire after time limit."""
    # [20251216_TEST] P0 acceptance criteria

    override_id = "test_override_123"

    # Recent expiry should be valid
    future_time = datetime.now() + timedelta(minutes=10)
    assert tamper_resistance.is_override_valid(override_id, future_time) is True

    # Past expiry should be invalid
    past_time = datetime.now() - timedelta(minutes=10)
    assert tamper_resistance.is_override_valid(override_id, past_time) is False


def test_override_cannot_be_reused(tamper_resistance):
    """Test that override codes cannot be reused."""
    # [20251216_TEST] P0 acceptance criteria

    override_id = "test_override_456"
    future_time = datetime.now() + timedelta(minutes=30)

    # Mark as used
    tamper_resistance._used_override_ids.add(override_id)

    # Should be invalid after use
    assert tamper_resistance.is_override_valid(override_id, future_time) is False


def test_override_logged_with_justification(tamper_resistance, tmp_path, monkeypatch):
    """Test that overrides are logged with justification."""
    # [20251216_TEST] P0 acceptance criteria

    operation = Operation(type="security_override", affected_files=[Path("src/sensitive.py")])

    policy_decision = PolicyDecision(
        allowed=False,
        violated_policies=["max_complexity"],
        reason="Complexity exceeds limit",
    )

    # Mock the challenge generation to use a fixed challenge
    fixed_challenge = "test_challenge_fixed_12345"

    def mock_generate_challenge():
        return fixed_challenge

    monkeypatch.setattr(tamper_resistance, "_generate_challenge", mock_generate_challenge)

    # Create mock response file in the policy directory
    response_file = tamper_resistance.policy_path.parent / "override_response.json"

    # Generate valid code for the fixed challenge
    import hashlib
    import hmac

    secret = os.environ.get("SCALPEL_TOTP_SECRET", "default-totp-secret")
    valid_code = hmac.new(secret.encode(), fixed_challenge.encode(), hashlib.sha256).hexdigest()[:8]

    response_data = {
        "code": valid_code,
        "justification": "Emergency hotfix required",
        "human_id": "admin@example.com",
    }

    # Write response file before calling require_human_override
    with open(response_file, "w") as f:
        json.dump(response_data, f)

    # Update the tamper resistance to use the test path
    tamper_resistance.audit_log.log_path = tmp_path / ".code-scalpel" / "audit.log"

    # Request override with short timeout
    decision = tamper_resistance.require_human_override(
        operation=operation, policy_decision=policy_decision, timeout_seconds=2
    )

    # Verify override was approved
    assert decision.approved is True
    assert decision.justification == "Emergency hotfix required"
    assert decision.approved_by == "admin@example.com"
    assert decision.override_id is not None

    # Verify logged
    events = tamper_resistance.audit_log.get_events(event_type="OVERRIDE_APPROVED")
    assert len(events) > 0
    assert events[-1]["details"]["justification"] == "Emergency hotfix required"


def test_override_timeout(tamper_resistance):
    """Test that override requests timeout."""
    # [20251216_TEST] P0 acceptance criteria

    operation = Operation(type="security_override", affected_files=[Path("src/test.py")])

    policy_decision = PolicyDecision(allowed=False, violated_policies=["security_check"], reason="Security violation")

    # Request override with very short timeout (no response file)
    decision = tamper_resistance.require_human_override(
        operation=operation, policy_decision=policy_decision, timeout_seconds=1
    )

    # Should timeout
    assert decision.approved is False
    assert "timed out" in decision.reason.lower()

    # Verify timeout logged
    events = tamper_resistance.audit_log.get_events(event_type="OVERRIDE_TIMEOUT")
    assert len(events) > 0


# =============================================================================
# P0: Audit Log - HMAC Signing and Verification
# =============================================================================


def test_audit_log_event_signing(audit_log):
    """Test that audit log events are signed with HMAC."""
    # [20251216_TEST] P0 acceptance criteria

    audit_log.record_event(event_type="TEST_EVENT", severity="MEDIUM", details={"key": "value"})

    # Verify event was written with signature
    with open(audit_log.log_path) as f:
        line = f.readline()
        event = json.loads(line)

    assert "signature" in event
    assert len(event["signature"]) == 64  # SHA-256 hex length


def test_audit_log_integrity_verification_success(audit_log):
    """Test that audit log integrity verification succeeds for valid log."""
    # [20251216_TEST] P0 acceptance criteria

    # Record some events
    audit_log.record_event(event_type="EVENT_1", severity="LOW", details={"info": "test1"})
    audit_log.record_event(event_type="EVENT_2", severity="MEDIUM", details={"info": "test2"})

    # Verify integrity
    assert audit_log.verify_integrity() is True


def test_audit_log_detects_tampering(audit_log):
    """Test that audit log detects tampering."""
    # [20251216_TEST] P0 acceptance criteria

    # Record event
    audit_log.record_event(event_type="ORIGINAL_EVENT", severity="LOW", details={"original": "data"})

    # Tamper with log file
    with open(audit_log.log_path, "a") as f:
        # Add event with invalid signature
        tampered_event = {
            "timestamp": datetime.now().isoformat(),
            "event_type": "TAMPERED_EVENT",
            "severity": "HIGH",
            "details": {"tampered": "data"},
            "signature": "0" * 64,  # Invalid signature
        }
        f.write(json.dumps(tampered_event) + "\n")

    # Verify tampering is detected
    with pytest.raises(TamperDetectedError) as exc_info:
        audit_log.verify_integrity()

    assert "tampering detected" in str(exc_info.value).lower()


def test_audit_log_append_only(audit_log):
    """Test that audit log is append-only."""
    # [20251216_TEST] P0 acceptance criteria

    # Record multiple events
    for i in range(3):
        audit_log.record_event(event_type=f"EVENT_{i}", severity="LOW", details={"index": i})

    # Verify all events are present (no deletion)
    events = audit_log.get_events()
    assert len(events) == 3

    # Verify events maintain order
    for i in range(3):
        assert events[i]["event_type"] == f"EVENT_{i}"
        assert events[i]["details"]["index"] == i


def test_audit_log_get_events_filtering(audit_log):
    """Test audit log event filtering."""
    # [20251216_TEST] Supporting functionality

    # Record events with different types and severities
    audit_log.record_event("TYPE_A", "LOW", {"test": 1})
    audit_log.record_event("TYPE_B", "HIGH", {"test": 2})
    audit_log.record_event("TYPE_A", "CRITICAL", {"test": 3})
    audit_log.record_event("TYPE_C", "LOW", {"test": 4})

    # Filter by event type
    type_a_events = audit_log.get_events(event_type="TYPE_A")
    assert len(type_a_events) == 2

    # Filter by severity
    low_events = audit_log.get_events(severity="LOW")
    assert len(low_events) == 2

    # Filter with limit
    limited_events = audit_log.get_events(limit=2)
    assert len(limited_events) == 2


def test_audit_log_handles_corrupted_json(audit_log):
    """Test that audit log detects corrupted JSON."""
    # [20251216_TEST] P0 acceptance criteria

    # Record valid event
    audit_log.record_event(event_type="VALID_EVENT", severity="LOW", details={"valid": "data"})

    # Corrupt the log file
    with open(audit_log.log_path, "a") as f:
        f.write("This is not valid JSON\n")

    # Verify corruption is detected
    with pytest.raises(TamperDetectedError) as exc_info:
        audit_log.verify_integrity()

    assert "corrupted" in str(exc_info.value).lower()


def test_audit_log_get_events_nonexistent_log(tmp_path):
    """Test get_events with non-existent log file."""
    # [20251216_TEST] Edge case coverage

    log_path = tmp_path / "nonexistent" / "audit.log"
    audit_log = AuditLog(log_path=str(log_path))

    # Should return empty list, not error
    events = audit_log.get_events()
    assert events == []


def test_audit_log_get_events_with_corrupted_lines(audit_log):
    """Test get_events skips corrupted JSON lines."""
    # [20251216_TEST] Edge case coverage

    # Record valid events
    audit_log.record_event("EVENT_1", "LOW", {"test": 1})
    audit_log.record_event("EVENT_2", "HIGH", {"test": 2})

    # Add corrupted line
    with open(audit_log.log_path, "a") as f:
        f.write("CORRUPTED JSON LINE\n")

    # Add another valid event
    audit_log.record_event("EVENT_3", "MEDIUM", {"test": 3})

    # get_events should skip corrupted line and return valid events
    events = audit_log.get_events()
    assert len(events) == 3  # Only valid events
    assert events[0]["event_type"] == "EVENT_1"
    assert events[1]["event_type"] == "EVENT_2"
    assert events[2]["event_type"] == "EVENT_3"


def test_audit_log_verify_integrity_empty_log(tmp_path):
    """Test verify_integrity with empty/non-existent log."""
    # [20251216_TEST] Edge case coverage

    log_path = tmp_path / "empty_audit.log"
    audit_log = AuditLog(log_path=str(log_path))

    # Should succeed for empty log
    assert audit_log.verify_integrity() is True


def test_audit_log_missing_signature(audit_log):
    """Test that audit log detects missing signature."""
    # [20251216_TEST] Edge case coverage

    # Record valid event first
    audit_log.record_event("VALID_EVENT", "LOW", {"test": 1})

    # Add event without signature
    with open(audit_log.log_path, "a") as f:
        event_without_sig = {
            "timestamp": datetime.now().isoformat(),
            "event_type": "NO_SIGNATURE",
            "severity": "HIGH",
            "details": {},
        }
        f.write(json.dumps(event_without_sig) + "\n")

    # Verify missing signature is detected
    with pytest.raises(TamperDetectedError) as exc_info:
        audit_log.verify_integrity()

    assert "missing signature" in str(exc_info.value).lower()


# =============================================================================
# Integration Tests
# =============================================================================


def test_full_tamper_resistance_workflow(temp_policy_dir, tmp_path):
    """Test complete tamper resistance workflow."""
    # [20251216_TEST] Integration test

    policy_file = temp_policy_dir / "policy.yaml"
    tr = TamperResistance(policy_path=str(policy_file))

    # 1. Verify policy integrity on startup
    assert tr.verify_policy_integrity() is True

    # 2. Try to modify policy file (should be blocked)
    operation = Operation(type="file_write", affected_files=[Path(".code-scalpel/policy.yaml")])

    with pytest.raises(PolicyModificationError):
        tr.prevent_policy_modification(operation)

    # 3. Verify modification attempt was logged
    events = tr.audit_log.get_events(event_type="POLICY_MODIFICATION_ATTEMPTED")
    assert len(events) > 0

    # 4. Verify audit log integrity
    assert tr.audit_log.verify_integrity() is True


def test_policy_engine_error_hierarchy():
    """Test that exception hierarchy is correct."""
    # [20251216_TEST] Supporting functionality

    from code_scalpel.policy_engine import PolicyEngineError

    # All exceptions should inherit from PolicyEngineError
    assert issubclass(TamperDetectedError, PolicyEngineError)
    assert issubclass(PolicyModificationError, PolicyEngineError)


def test_operation_dataclass():
    """Test Operation dataclass."""
    # [20251216_TEST] Supporting functionality

    op = Operation(
        type="file_write",
        affected_files=[Path("test.py")],
        metadata={"author": "agent"},
    )

    assert op.type == "file_write"
    assert len(op.affected_files) == 1
    assert op.metadata["author"] == "agent"
    assert isinstance(op.timestamp, datetime)


def test_policy_decision_dataclass():
    """Test PolicyDecision dataclass."""
    # [20251216_TEST] Supporting functionality

    decision = PolicyDecision(
        allowed=False,
        violated_policies=["complexity", "security"],
        reason="Too complex",
        severity="HIGH",
    )

    assert decision.allowed is False
    assert len(decision.violated_policies) == 2
    assert decision.severity == "HIGH"


def test_override_decision_dataclass():
    """Test OverrideDecision dataclass."""
    # [20251216_TEST] Supporting functionality

    decision = OverrideDecision(
        approved=True,
        reason="Human approved",
        override_id="abc123",
        expires_at=datetime.now() + timedelta(minutes=30),
    )

    assert decision.approved is True
    assert decision.override_id == "abc123"
    assert decision.expires_at > datetime.now()
