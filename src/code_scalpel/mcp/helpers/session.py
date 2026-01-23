"""Session management and audit logging for Code Scalpel MCP.

[20260116_BUGFIX] Consolidated session state - this is the Single Source of Truth.
All session state MUST be imported from this module to avoid split-brain bugs.

This module supports both the new API (tool_name, file_path, etc.) and the legacy
API (operation, details, outcome, user_id) for backward compatibility.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from code_scalpel.policy_engine.audit_log import (
    AuditLog,
)  # [20260121_BUGFIX] Persist audit trail to disk

logger = logging.getLogger("code_scalpel.mcp.session")


# =============================================================================
# MODULE-LEVEL STATE (Single Source of Truth)
# =============================================================================
# These are the CANONICAL instances. All code MUST use these exact objects.
_SESSION_UPDATE_COUNTS: dict[str, int] = {}
_SESSION_AUDIT_TRAIL: list[dict[str, Any]] = []


def _get_project_root() -> Path:
    """Get current project root for locating .code-scalpel.

    [20260121_BUGFIX] Mirror server getter to anchor persistent audit log.
    """

    try:
        from code_scalpel.mcp.server import get_project_root

        return get_project_root()
    except Exception:
        return Path.cwd()


def _get_persistent_audit_log() -> AuditLog | None:
    """Return disk-backed audit log in .code-scalpel/audit.log if available."""

    try:
        log_path = _get_project_root() / ".code-scalpel" / "audit.log"
        return AuditLog(str(log_path))
    except Exception:
        return None


# =============================================================================
# SESSION MANAGER (Singleton wrapper for the module-level state)
# =============================================================================
class SessionManager:
    """Manages session state and audit logs.

    This is a singleton that wraps the module-level state variables.
    Using the singleton or the module-level functions is equivalent -
    they all operate on the same _SESSION_* variables.
    """

    _instance: SessionManager | None = None

    def __init__(self) -> None:
        # SessionManager does NOT have its own state!
        # It uses the module-level _SESSION_* variables.
        pass

    @classmethod
    def get_instance(cls) -> SessionManager:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @property
    def _update_counts(self) -> dict[str, int]:
        """Return the module-level update counts dict (for backward compat)."""
        return _SESSION_UPDATE_COUNTS

    @property
    def _audit_log(self) -> list[dict[str, Any]]:
        """Return the module-level audit trail list (for backward compat)."""
        return _SESSION_AUDIT_TRAIL

    def get_update_count(self, key: str) -> int:
        return _SESSION_UPDATE_COUNTS.get(key, 0)

    def increment_update_count(self, key: str) -> int:
        current = _SESSION_UPDATE_COUNTS.get(key, 0)
        _SESSION_UPDATE_COUNTS[key] = current + 1
        return _SESSION_UPDATE_COUNTS[key]

    def add_audit_entry(self, entry: dict[str, Any]) -> None:
        """Add entry with timestamp."""
        if "timestamp" not in entry:
            entry["timestamp"] = datetime.now(timezone.utc).isoformat()
        _SESSION_AUDIT_TRAIL.append(entry)
        logger.info(
            f"AUDIT [{entry.get('tool', entry.get('operation', 'unknown'))}] {entry.get('success', entry.get('outcome', '-'))}"
        )

        # [20260121_BUGFIX] Persist audit trail to disk (tamper-resistant)
        try:
            audit_log = _get_persistent_audit_log()
            if audit_log is not None:
                severity = "LOW" if entry.get("success", True) else "HIGH"
                details = {
                    "tool": entry.get("tool") or entry.get("operation"),
                    "file_path": entry.get("file_path"),
                    "target_name": entry.get("target_name"),
                    "tier": entry.get("tier"),
                    "metadata": entry.get("metadata"),
                    "outcome": entry.get("outcome"),
                    "user_id": entry.get("user_id"),
                }
                audit_log.record_event(
                    event_type=entry.get("tool") or entry.get("operation") or "audit_event",
                    severity=severity,
                    details=details,
                )
        except Exception:
            logger.warning("Persistent audit logging failed", exc_info=False)


# =============================================================================
# PUBLIC API FUNCTIONS
# =============================================================================


def get_session_update_count(tool_name: str) -> int:
    """Get the current update count for a tool."""
    return _SESSION_UPDATE_COUNTS.get(tool_name, 0)


def increment_session_update_count(tool_name: str) -> int:
    """Increment and return the update count for a tool."""
    current = _SESSION_UPDATE_COUNTS.get(tool_name, 0)
    _SESSION_UPDATE_COUNTS[tool_name] = current + 1
    return _SESSION_UPDATE_COUNTS[tool_name]


def add_audit_entry(
    # Legacy positional API (operation, details, outcome, user_id)
    operation: str | None = None,
    details: dict[str, Any] | None = None,
    outcome: str | None = None,
    user_id: str | None = None,
    # New keyword-only API (tool_name, file_path, etc.)
    *,
    tool_name: str = "",
    file_path: str = "",
    target_name: str = "",
    success: bool = True,
    tier: str = "community",
    metadata: dict[str, Any] | None = None,
) -> None:
    """Add an audit trail entry.

    Supports both APIs:

    New API (preferred):
        add_audit_entry(
            tool_name="extract_code",
            file_path="/path/to/file.py",
            target_name="my_func",
            operation="extract",
            success=True,
            tier="community"
        )

    Legacy API (backward compatibility):
        add_audit_entry(
            "extraction",
            {"file": "/path/to/file.py"},
            "success",
            user_id="user123"
        )
    """
    entry: dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    # New API: tool_name was provided as keyword arg
    if tool_name:
        entry.update(
            {
                "tool": tool_name,
                "file_path": file_path,
                "target_name": target_name,
                "operation": operation or "unknown",
                "success": success,
                "tier": tier,
                "metadata": metadata or {},
            }
        )
    # Legacy API: operation was provided as positional arg
    elif operation:
        entry.update(
            {
                "operation": operation,
                "details": details or {},
                "outcome": outcome or ("success" if success else "failure"),
                "user_id": user_id,
                "success": outcome == "success" if outcome else success,
            }
        )
    else:
        # Minimal entry (shouldn't happen, but be defensive)
        entry.update(
            {
                "operation": "unknown",
                "success": success,
                "metadata": metadata or details or {},
            }
        )

    _SESSION_AUDIT_TRAIL.append(entry)
    log_key = entry.get("tool", entry.get("operation", "unknown"))
    log_outcome = entry.get("success", entry.get("outcome", "-"))
    logger.info(f"AUDIT [{log_key}] {log_outcome}")


def get_audit_trail() -> list[dict[str, Any]]:
    """Return a copy of the audit trail."""
    return _SESSION_AUDIT_TRAIL.copy()


def _get_audit_trail() -> list[dict[str, Any]]:
    """Internal: return the actual audit trail list (not a copy)."""
    return _SESSION_AUDIT_TRAIL


# =============================================================================
# BACKWARD-COMPATIBLE ALIASES
# =============================================================================
_get_session_update_count = get_session_update_count
_increment_session_update_count = increment_session_update_count
_add_audit_entry = add_audit_entry
