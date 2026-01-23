"""Tier state and caching helpers for MCP server."""

from __future__ import annotations

CURRENT_TIER = "community"
_LAST_VALID_LICENSE_TIER: str | None = None
_LAST_VALID_LICENSE_AT: float | None = None
_MID_SESSION_EXPIRY_GRACE_SECONDS = 24 * 60 * 60
