# [20260108_TEST] Enterprise approval workflow tests
"""
Tests for Enterprise-tier approval workflow functionality.

Verifies approval integration with external systems:
- Approval request/response protocol
- Status tracking and expiration
- Multi-reviewer support
- Callback integration
- Synchronous waiting
"""

import time

import pytest

from code_scalpel.surgery.approval_workflow import (
    ApprovalRequest,
    ApprovalResponse,
    ApprovalStatus,
    ApprovalWorkflow,
)


class TestApprovalBasics:
    """Test basic approval workflow functionality."""

    def test_approval_request_creation(self):
        """ApprovalRequest can be created."""
        request = ApprovalRequest(
            operation="rename_symbol",
            title="Rename function",
            description="Rename old_func to new_func",
        )

        assert request.operation == "rename_symbol"
        assert request.title == "Rename function"
        assert request.description == "Rename old_func to new_func"
        assert request.created_at is not None

    def test_approval_request_with_reviewers(self):
        """ApprovalRequest supports reviewer list."""
        request = ApprovalRequest(
            operation="refactor",
            title="Major refactor",
            description="Restructure module",
            reviewers=["alice", "bob"],
            require_all_reviewers=True,
        )

        assert request.reviewers == ["alice", "bob"]
        assert request.require_all_reviewers is True

    def test_approval_response_creation(self):
        """ApprovalResponse can be created."""
        response = ApprovalResponse(approval_id="test-123", status=ApprovalStatus.PENDING)

        assert response.approval_id == "test-123"
        assert response.status == ApprovalStatus.PENDING
        assert response.approvers == []
        assert response.rejectors == []

    def test_approval_workflow_init(self):
        """ApprovalWorkflow can be initialized."""
        workflow = ApprovalWorkflow(timeout_seconds=300)

        assert workflow.timeout_seconds == 300
        assert workflow.auto_approve is False


class TestApprovalRequests:
    """Test approval request handling."""

    def test_request_approval_generates_id(self):
        """Requesting approval generates unique ID."""
        workflow = ApprovalWorkflow()

        request = ApprovalRequest(operation="test", title="Test operation", description="Test description")

        approval_id = workflow.request_approval(request)
        assert approval_id is not None
        assert approval_id.startswith("approval-")

    def test_request_approval_tracks_internally(self):
        """Approval requests are tracked internally."""
        workflow = ApprovalWorkflow()

        request = ApprovalRequest(operation="test", title="Test", description="Test")

        approval_id = workflow.request_approval(request)
        status = workflow.check_approval(approval_id)

        assert status == ApprovalStatus.PENDING

    def test_auto_approve_mode(self):
        """Auto-approve mode immediately approves requests."""
        workflow = ApprovalWorkflow(auto_approve=True)

        request = ApprovalRequest(operation="test", title="Test", description="Test")

        approval_id = workflow.request_approval(request)
        status = workflow.check_approval(approval_id)

        assert status == ApprovalStatus.APPROVED

    def test_approval_with_timeout(self):
        """Approval requests can have expiration."""
        workflow = ApprovalWorkflow(timeout_seconds=1)

        request = ApprovalRequest(operation="test", title="Test", description="Test")

        approval_id = workflow.request_approval(request)

        # Should be pending initially
        assert workflow.check_approval(approval_id) == ApprovalStatus.PENDING

        # Wait for expiration
        time.sleep(1.5)

        # Should be expired now
        assert workflow.check_approval(approval_id) == ApprovalStatus.EXPIRED


class TestApprovalActions:
    """Test approval/rejection actions."""

    def test_manual_approval(self):
        """Approvals can be manually recorded."""
        workflow = ApprovalWorkflow()

        request = ApprovalRequest(operation="test", title="Test", description="Test")

        approval_id = workflow.request_approval(request)

        # Approve manually
        success = workflow.approve(approval_id, "alice", "LGTM")
        assert success is True

        # Check status
        status = workflow.check_approval(approval_id)
        assert status == ApprovalStatus.APPROVED

        # Check details
        details = workflow.get_approval_details(approval_id)
        assert details is not None
        assert "alice" in details.approvers
        assert any("LGTM" in comment for comment in details.comments)

    def test_manual_rejection(self):
        """Rejections can be manually recorded."""
        workflow = ApprovalWorkflow()

        request = ApprovalRequest(operation="test", title="Test", description="Test")

        approval_id = workflow.request_approval(request)

        # Reject manually
        success = workflow.reject(approval_id, "bob", "Needs more tests")
        assert success is True

        # Check status
        status = workflow.check_approval(approval_id)
        assert status == ApprovalStatus.REJECTED

        # Check details
        details = workflow.get_approval_details(approval_id)
        assert details is not None
        assert "bob" in details.rejectors
        assert any("Needs more tests" in comment for comment in details.comments)

    def test_cannot_approve_after_rejection(self):
        """Cannot approve after rejection."""
        workflow = ApprovalWorkflow()

        request = ApprovalRequest(operation="test", title="Test", description="Test")

        approval_id = workflow.request_approval(request)

        # Reject first
        workflow.reject(approval_id, "alice", "No")

        # Try to approve after rejection
        success = workflow.approve(approval_id, "bob", "Yes")
        assert success is False

        # Should still be rejected
        assert workflow.check_approval(approval_id) == ApprovalStatus.REJECTED

    def test_cancel_approval(self):
        """Approvals can be cancelled."""
        workflow = ApprovalWorkflow()

        request = ApprovalRequest(operation="test", title="Test", description="Test")

        approval_id = workflow.request_approval(request)

        # Cancel
        success = workflow.cancel(approval_id)
        assert success is True

        # Check status
        status = workflow.check_approval(approval_id)
        assert status == ApprovalStatus.CANCELLED


class TestApprovalCallbacks:
    """Test external callback integration."""

    def test_approval_callback_invoked(self):
        """Approval callback is invoked on request."""
        callback_invoked = []

        def mock_callback(request: ApprovalRequest) -> str:
            callback_invoked.append(request)
            return "external-id-123"

        workflow = ApprovalWorkflow(approval_callback=mock_callback)

        request = ApprovalRequest(operation="test", title="Test", description="Test")

        approval_id = workflow.request_approval(request)

        # Callback should have been invoked
        assert len(callback_invoked) == 1
        assert callback_invoked[0] == request

        # Should use external ID
        assert approval_id == "external-id-123"

    def test_status_callback_invoked(self):
        """Status callback is invoked on check."""
        status_checks = []

        def mock_status_callback(approval_id: str) -> ApprovalStatus:
            status_checks.append(approval_id)
            return ApprovalStatus.APPROVED

        workflow = ApprovalWorkflow(status_callback=mock_status_callback)

        request = ApprovalRequest(operation="test", title="Test", description="Test")

        approval_id = workflow.request_approval(request)
        status = workflow.check_approval(approval_id)

        # Status callback should have been invoked
        assert len(status_checks) == 1
        assert status == ApprovalStatus.APPROVED

    def test_callback_failure_graceful(self):
        """Callback failures are handled gracefully."""

        def broken_callback(request: ApprovalRequest) -> str:
            raise Exception("Callback failed")

        workflow = ApprovalWorkflow(approval_callback=broken_callback)

        request = ApprovalRequest(operation="test", title="Test", description="Test")

        # Should not crash
        approval_id = workflow.request_approval(request)
        assert approval_id is not None


class TestApprovalDetails:
    """Test getting approval details."""

    def test_get_approval_details(self):
        """Can retrieve approval details."""
        workflow = ApprovalWorkflow()

        request = ApprovalRequest(operation="test", title="Test", description="Test")

        approval_id = workflow.request_approval(request)
        details = workflow.get_approval_details(approval_id)

        assert details is not None
        assert details.approval_id == approval_id
        assert details.status == ApprovalStatus.PENDING

    def test_get_nonexistent_approval(self):
        """Returns None for nonexistent approval."""
        workflow = ApprovalWorkflow()

        details = workflow.get_approval_details("nonexistent-id")
        assert details is None


class TestSynchronousWait:
    """Test synchronous waiting for approval."""

    def test_wait_for_approval_immediate(self):
        """Wait returns immediately if already approved."""
        workflow = ApprovalWorkflow(auto_approve=True)

        request = ApprovalRequest(operation="test", title="Test", description="Test")

        approval_id = workflow.request_approval(request)

        # Should return immediately (already approved)
        status = workflow.wait_for_approval(approval_id, poll_interval=0.1)
        assert status == ApprovalStatus.APPROVED

    def test_wait_for_approval_with_timeout(self):
        """Wait respects max_wait timeout."""
        workflow = ApprovalWorkflow()

        request = ApprovalRequest(operation="test", title="Test", description="Test")

        approval_id = workflow.request_approval(request)

        # Wait with short timeout
        start = time.time()
        status = workflow.wait_for_approval(approval_id, poll_interval=0.1, max_wait=0.3)
        elapsed = time.time() - start

        # Should timeout
        assert status == ApprovalStatus.EXPIRED
        assert 0.2 < elapsed < 0.5  # Allow some variance


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
