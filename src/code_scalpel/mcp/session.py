"""Session counters and audit helpers for MCP server.

[20260116_BUGFIX] This file is now a thin re-export layer.
The Single Source of Truth is: code_scalpel.mcp.helpers.session

All state is managed in helpers/session.py to avoid split-brain bugs.
"""

from __future__ import annotations

# Re-export everything from the SSOT
from code_scalpel.mcp.helpers.session import (
    _SESSION_AUDIT_TRAIL,
    # Module-level state (same objects, not copies!)
    _SESSION_UPDATE_COUNTS,
    # SessionManager class
    SessionManager,
    _add_audit_entry,
    _get_audit_trail,
    _get_session_update_count,
    _increment_session_update_count,
    add_audit_entry,
    get_audit_trail,
    # Public functions
    get_session_update_count,
    increment_session_update_count,
)

__all__ = [
    "_SESSION_UPDATE_COUNTS",
    "_SESSION_AUDIT_TRAIL",
    "get_session_update_count",
    "increment_session_update_count",
    "add_audit_entry",
    "get_audit_trail",
    "_get_audit_trail",
    "_add_audit_entry",
    "_get_session_update_count",
    "_increment_session_update_count",
    "SessionManager",
]
