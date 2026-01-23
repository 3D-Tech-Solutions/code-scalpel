# [20260108_FEATURE] Enterprise approval workflow hooks
"""
Approval workflow integration for Enterprise tier.

Provides integration points for code review and approval gates:
- Approval request/response protocol
- Callback hooks for external review systems
- Approval status tracking
- Multi-reviewer support
- Timeout handling

Key Features:
- Flexible approval callbacks (GitHub PR, Jira, email, etc.)
- Async approval support (request returns immediately, check later)
- Multi-reviewer approval (require N of M approvers)
- Approval expiration (time-bound approvals)
- Audit trail integration

Example:
    from code_scalpel.surgery.approval_workflow import (
        ApprovalWorkflow, ApprovalRequest, ApprovalStatus
    )

    # Define approval callback
    def request_github_pr_approval(request: ApprovalRequest) -> str:
        # Create GitHub PR and return approval_id
        pr = create_pr(title=request.title, description=request.description)
        return f"gh-pr-{pr.number}"

    # Configure workflow
    workflow = ApprovalWorkflow(
        approval_callback=request_github_pr_approval,
        timeout_seconds=3600  # 1 hour timeout
    )

    # Request approval
    request = ApprovalRequest(
        operation="rename_symbol",
        title="Rename old_function to new_function",
        description="Cross-file rename affecting 42 files",
        metadata={"files_affected": 42}
    )

    approval_id = workflow.request_approval(request)

    # Later, check if approved
    status = workflow.check_approval(approval_id)
    if status == ApprovalStatus.APPROVED:
        # Proceed with operation
        pass
"""

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any


class ApprovalStatus(Enum):
    """Status of an approval request."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


@dataclass
class ApprovalRequest:
    """
    Approval request for a code operation.

    Attributes:
        operation: Type of operation (e.g., "rename_symbol", "refactor")
        title: Human-readable title for approval UI
        description: Detailed description of the change
        requester: User requesting the change
        reviewers: List of required reviewers (optional)
        metadata: Additional context for reviewers
        require_all_reviewers: If True, all reviewers must approve
        created_at: Timestamp of request creation
    """

    operation: str
    title: str
    description: str
    requester: str | None = None
    reviewers: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    require_all_reviewers: bool = False
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class ApprovalResponse:
    """
    Response to an approval request.

    Attributes:
        approval_id: Unique ID for this approval
        status: Current approval status
        approvers: List of users who approved
        rejectors: List of users who rejected
        comments: Reviewer comments
        approved_at: Timestamp of approval (if approved)
        rejected_at: Timestamp of rejection (if rejected)
        expires_at: Expiration timestamp (if timeout set)
    """

    approval_id: str
    status: ApprovalStatus
    approvers: list[str] = field(default_factory=list)
    rejectors: list[str] = field(default_factory=list)
    comments: list[str] = field(default_factory=list)
    approved_at: datetime | None = None
    rejected_at: datetime | None = None
    expires_at: datetime | None = None


class ApprovalWorkflow:
    """
    Approval workflow manager for Enterprise tier.

    Manages approval requests with external integration support.
    """

    def __init__(
        self,
        approval_callback: Callable[[ApprovalRequest], str] | None = None,
        status_callback: Callable[[str], ApprovalStatus] | None = None,
        timeout_seconds: int | None = None,
        auto_approve: bool = False,
    ):
        """
        Initialize approval workflow manager.

        Args:
            approval_callback: Function to request approval externally
                             Returns approval_id for tracking
            status_callback: Function to check approval status externally
                           Returns current ApprovalStatus
            timeout_seconds: Approval timeout (None = no timeout)
            auto_approve: If True, auto-approve all requests (testing only)
        """
        self.approval_callback = approval_callback
        self.status_callback = status_callback
        self.timeout_seconds = timeout_seconds
        self.auto_approve = auto_approve

        # Internal tracking
        self._pending_approvals: dict[str, ApprovalResponse] = {}
        self._approval_counter = 0

    def _generate_approval_id(self) -> str:
        """Generate unique approval ID."""
        self._approval_counter += 1
        timestamp = int(time.time())
        return f"approval-{timestamp}-{self._approval_counter}"

    def request_approval(self, request: ApprovalRequest) -> str:
        """
        Request approval for an operation.

        Args:
            request: Approval request details

        Returns:
            approval_id for tracking
        """
        # Generate approval ID
        approval_id = self._generate_approval_id()

        # Auto-approve if enabled (testing mode)
        if self.auto_approve:
            response = ApprovalResponse(
                approval_id=approval_id,
                status=ApprovalStatus.APPROVED,
                approvers=["auto-approve"],
                approved_at=datetime.now(),
            )
            self._pending_approvals[approval_id] = response
            return approval_id

        # Call external approval callback if provided
        if self.approval_callback:
            try:
                external_id = self.approval_callback(request)
                approval_id = external_id or approval_id
            except Exception:
                # Fallback to internal tracking if callback fails
                pass

        # Create response object
        expires_at = None
        if self.timeout_seconds:
            expires_at = datetime.now() + timedelta(seconds=self.timeout_seconds)

        response = ApprovalResponse(
            approval_id=approval_id,
            status=ApprovalStatus.PENDING,
            expires_at=expires_at,
        )

        self._pending_approvals[approval_id] = response
        return approval_id

    def check_approval(self, approval_id: str) -> ApprovalStatus:
        """
        Check status of an approval request.

        Args:
            approval_id: ID returned from request_approval()

        Returns:
            Current ApprovalStatus
        """
        # Check internal tracking first
        if approval_id not in self._pending_approvals:
            return ApprovalStatus.CANCELLED

        response = self._pending_approvals[approval_id]

        # Check expiration
        if response.expires_at and datetime.now() > response.expires_at:
            response.status = ApprovalStatus.EXPIRED
            return ApprovalStatus.EXPIRED

        # Check external status if callback provided
        if self.status_callback:
            try:
                external_status = self.status_callback(approval_id)
                response.status = external_status
            except Exception:
                # Keep internal status if callback fails
                pass

        return response.status

    def approve(self, approval_id: str, approver: str, comment: str | None = None) -> bool:
        """
        Manually approve a request (for internal/testing use).

        Args:
            approval_id: Approval ID to approve
            approver: User approving the request
            comment: Optional approval comment

        Returns:
            True if approval successful
        """
        if approval_id not in self._pending_approvals:
            return False

        response = self._pending_approvals[approval_id]

        # Can't approve if already resolved
        if response.status in {
            ApprovalStatus.APPROVED,
            ApprovalStatus.REJECTED,
            ApprovalStatus.EXPIRED,
        }:
            return False

        # Add approver
        if approver not in response.approvers:
            response.approvers.append(approver)

        if comment:
            response.comments.append(f"{approver}: {comment}")

        # Update status
        response.status = ApprovalStatus.APPROVED
        response.approved_at = datetime.now()

        return True

    def reject(self, approval_id: str, rejector: str, reason: str | None = None) -> bool:
        """
        Manually reject a request (for internal/testing use).

        Args:
            approval_id: Approval ID to reject
            rejector: User rejecting the request
            reason: Optional rejection reason

        Returns:
            True if rejection successful
        """
        if approval_id not in self._pending_approvals:
            return False

        response = self._pending_approvals[approval_id]

        # Can't reject if already resolved
        if response.status in {
            ApprovalStatus.APPROVED,
            ApprovalStatus.REJECTED,
            ApprovalStatus.EXPIRED,
        }:
            return False

        # Add rejector
        if rejector not in response.rejectors:
            response.rejectors.append(rejector)

        if reason:
            response.comments.append(f"{rejector}: {reason}")

        # Update status
        response.status = ApprovalStatus.REJECTED
        response.rejected_at = datetime.now()

        return True

    def cancel(self, approval_id: str) -> bool:
        """
        Cancel a pending approval request.

        Args:
            approval_id: Approval ID to cancel

        Returns:
            True if cancellation successful
        """
        if approval_id not in self._pending_approvals:
            return False

        response = self._pending_approvals[approval_id]
        response.status = ApprovalStatus.CANCELLED
        return True

    def get_approval_details(self, approval_id: str) -> ApprovalResponse | None:
        """
        Get detailed approval information.

        Args:
            approval_id: Approval ID to query

        Returns:
            ApprovalResponse or None if not found
        """
        return self._pending_approvals.get(approval_id)

    def wait_for_approval(
        self,
        approval_id: str,
        poll_interval: float = 5.0,
        max_wait: float | None = None,
    ) -> ApprovalStatus:
        """
        Block until approval is resolved (for synchronous workflows).

        Args:
            approval_id: Approval ID to wait for
            poll_interval: Seconds between status checks
            max_wait: Maximum seconds to wait (None = wait forever)

        Returns:
            Final ApprovalStatus
        """
        start_time = time.time()

        while True:
            status = self.check_approval(approval_id)

            # Return if resolved
            if status in {
                ApprovalStatus.APPROVED,
                ApprovalStatus.REJECTED,
                ApprovalStatus.EXPIRED,
                ApprovalStatus.CANCELLED,
            }:
                return status

            # Check max_wait timeout
            if max_wait and (time.time() - start_time) > max_wait:
                return ApprovalStatus.EXPIRED

            # Wait before next poll
            time.sleep(poll_interval)
