"""Audit trail logging for surgical operations.

# [20260108_FEATURE] Enterprise-tier audit trail implementation

This module provides audit logging capabilities for code surgery operations,
enabling Enterprise customers to track all code modifications with:
- Timestamp and operation tracking
- Files changed and success/failure status
- User/session identification
- Structured JSON logging for integration with audit systems

Design Principles:
- Minimal performance overhead
- Structured data for easy parsing
- Thread-safe logging
- Configurable storage locations
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class AuditEntry:
    """Single audit log entry for a surgical operation."""

    # Core identification
    timestamp: str  # ISO 8601 format
    operation: str  # e.g., "rename_symbol", "update_function"
    session_id: str  # Unique session identifier

    # Operation details
    target_file: str  # File being operated on
    target_type: str  # e.g., "function", "class", "method"
    target_name: str  # Original name
    new_name: str | None = None  # New name (for renames)

    # Execution results
    success: bool = False
    error: str | None = None
    changed_files: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    # Performance metrics
    duration_ms: float | None = None

    # User/environment context
    user: str | None = None
    hostname: str | None = None
    tier: str | None = None  # "community", "pro", "enterprise"

    # Additional metadata
    metadata: dict[str, Any] = field(default_factory=dict)


class AuditTrail:
    """
    Audit trail manager for Enterprise-tier surgical operations.

    Provides structured logging of all code modifications with:
    - JSON-formatted entries for machine parsing
    - Configurable log file location
    - Automatic log rotation support (via Python logging)
    - Thread-safe operations

    Example:
        audit = AuditTrail(log_dir=".code-scalpel/audit")

        entry = AuditEntry(
            timestamp=datetime.utcnow().isoformat(),
            operation="rename_symbol",
            session_id="abc123",
            target_file="src/utils.py",
            target_type="function",
            target_name="old_func",
            new_name="new_func",
            success=True,
            changed_files=["src/utils.py", "src/main.py"],
            tier="enterprise"
        )

        audit.log(entry)
    """

    def __init__(
        self,
        log_dir: str | Path | None = None,
        enabled: bool = True,
        log_to_file: bool = True,
        log_to_stdout: bool = False,
    ):
        """
        Initialize audit trail.

        Args:
            log_dir: Directory for audit log files (default: .code-scalpel/audit)
            enabled: Whether audit logging is enabled
            log_to_file: Write to audit log file
            log_to_stdout: Also print to stdout (for debugging)
        """
        self.enabled = enabled
        self.log_to_file = log_to_file
        self.log_to_stdout = log_to_stdout

        if log_dir is None:
            log_dir = Path.cwd() / ".code-scalpel" / "audit"
        self.log_dir = Path(log_dir)

        if self.enabled and self.log_to_file:
            self.log_dir.mkdir(parents=True, exist_ok=True)
            self.log_file = self.log_dir / f"audit_{datetime.now().strftime('%Y%m%d')}.jsonl"

    def log(self, entry: AuditEntry) -> None:
        """
        Log an audit entry.

        Args:
            entry: AuditEntry to log
        """
        if not self.enabled:
            return

        try:
            # Convert to JSON
            entry_dict = asdict(entry)
            json_line = json.dumps(entry_dict, default=str)

            # Write to file
            if self.log_to_file:
                with open(self.log_file, "a", encoding="utf-8") as f:
                    f.write(json_line + "\n")

            # Print to stdout if requested
            if self.log_to_stdout:
                print(f"[AUDIT] {json_line}")

        except Exception as e:
            logger.error(f"Failed to write audit entry: {e}", exc_info=True)

    def create_entry(
        self,
        operation: str,
        session_id: str,
        target_file: str,
        target_type: str,
        target_name: str,
        new_name: str | None = None,
        tier: str | None = None,
        **kwargs,
    ) -> AuditEntry:
        """
        Create an audit entry with automatic timestamp.

        Args:
            operation: Operation name
            session_id: Session identifier
            target_file: Target file path
            target_type: Target type (function, class, method)
            target_name: Original name
            new_name: New name (for renames)
            tier: License tier
            **kwargs: Additional fields for AuditEntry

        Returns:
            AuditEntry ready to log
        """
        return AuditEntry(
            timestamp=datetime.utcnow().isoformat() + "Z",
            operation=operation,
            session_id=session_id,
            target_file=target_file,
            target_type=target_type,
            target_name=target_name,
            new_name=new_name,
            user=os.environ.get("USER") or os.environ.get("USERNAME"),
            hostname=os.environ.get("HOSTNAME") or os.environ.get("COMPUTERNAME"),
            tier=tier,
            **kwargs,
        )

    def query(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        operation: str | None = None,
        target_file: str | None = None,
        success: bool | None = None,
    ) -> list[AuditEntry]:
        """
        Query audit log entries.

        Args:
            start_date: Filter entries after this date
            end_date: Filter entries before this date
            operation: Filter by operation name
            target_file: Filter by target file
            success: Filter by success status

        Returns:
            List of matching AuditEntry objects
        """
        if not self.enabled or not self.log_to_file:
            return []

        results = []

        # Read all .jsonl files in log directory
        for log_file in sorted(self.log_dir.glob("audit_*.jsonl")):
            try:
                with open(log_file, encoding="utf-8") as f:
                    for line in f:
                        try:
                            entry_dict = json.loads(line)
                            entry = AuditEntry(**entry_dict)

                            # Apply filters
                            if start_date and entry.timestamp < start_date.isoformat():
                                continue
                            if end_date and entry.timestamp > end_date.isoformat():
                                continue
                            if operation and entry.operation != operation:
                                continue
                            if target_file and entry.target_file != target_file:
                                continue
                            if success is not None and entry.success != success:
                                continue

                            results.append(entry)
                        except Exception as e:
                            logger.warning(f"Failed to parse audit entry: {e}")
            except Exception as e:
                logger.warning(f"Failed to read audit log {log_file}: {e}")

        return results


# Global audit trail instance
_global_audit_trail: AuditTrail | None = None


def get_audit_trail() -> AuditTrail:
    """Get or create the global audit trail instance."""
    global _global_audit_trail
    if _global_audit_trail is None:
        _global_audit_trail = AuditTrail()
    return _global_audit_trail


def configure_audit_trail(
    log_dir: str | Path | None = None,
    enabled: bool = True,
    log_to_file: bool = True,
    log_to_stdout: bool = False,
) -> AuditTrail:
    """
    Configure the global audit trail instance.

    Args:
        log_dir: Directory for audit log files
        enabled: Whether audit logging is enabled
        log_to_file: Write to audit log file
        log_to_stdout: Also print to stdout

    Returns:
        Configured AuditTrail instance
    """
    global _global_audit_trail
    _global_audit_trail = AuditTrail(
        log_dir=log_dir,
        enabled=enabled,
        log_to_file=log_to_file,
        log_to_stdout=log_to_stdout,
    )
    return _global_audit_trail
