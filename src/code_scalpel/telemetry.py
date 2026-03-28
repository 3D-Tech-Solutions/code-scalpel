"""Telemetry module for Code Scalpel MCP server.

Non-intrusive event tracking for tool calls. Events are emitted to an in-memory
queue and can be streamed to WebSocket clients or persisted to JSONL.
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from collections import deque
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Global event queue (in-memory, max 50 events)
_EVENT_QUEUE: deque = deque(maxlen=50)

# Track open WebSocket subscribers for live streaming
_SUBSCRIBERS: set = set()

# Audit log instance (initialized by MCP server on startup)
_AUDIT_LOG: Optional[Any] = None


def set_audit_log(audit_log: Any) -> None:
    """Register audit log instance for telemetry events.

    Args:
        audit_log: AuditLog instance from src/code_scalpel/audit.py
    """
    global _AUDIT_LOG
    _AUDIT_LOG = audit_log
    logger.debug("Audit log registered for telemetry")


@dataclass
class TelemetryEvent:
    """Schema for a tool call telemetry event."""

    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)
    tool_name: str = ""
    tier_applied: str = "community"
    request_id: str = ""
    session_id: str = ""
    duration_ms: float = 0.0
    status: str = "success"  # success, failure, timeout
    error: Optional[str] = None
    input_summary: dict[str, Any] = field(default_factory=dict)
    output_summary: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert event to dictionary for JSON serialization."""
        data = asdict(self)
        data["timestamp_iso"] = datetime.fromtimestamp(self.timestamp).isoformat()
        return data

    def to_json(self) -> str:
        """Convert event to JSON line."""
        return json.dumps(self.to_dict())


def emit_tool_event(
    tool_name: str,
    tier_applied: str = "community",
    request_id: str = "",
    session_id: str = "",
    duration_ms: float = 0.0,
    status: str = "success",
    error: Optional[str] = None,
    input_summary: Optional[dict[str, Any]] = None,
    output_summary: Optional[dict[str, Any]] = None,
    metadata: Optional[dict[str, Any]] = None,
) -> TelemetryEvent:
    """Emit a tool call event to the telemetry queue.

    Args:
        tool_name: Name of the tool that was called
        tier_applied: License tier under which tool ran
        request_id: Unique request ID
        session_id: Session ID for grouping related calls
        duration_ms: Execution time in milliseconds
        status: "success", "failure", or "timeout"
        error: Error message if status is failure
        input_summary: Scrubbed input summary (file counts, paths, etc)
        output_summary: Output summary (counts, findings, etc)
        metadata: Additional metadata (language, symbols, etc)

    Returns:
        The emitted TelemetryEvent
    """
    event = TelemetryEvent(
        tool_name=tool_name,
        tier_applied=tier_applied,
        request_id=request_id,
        session_id=session_id,
        duration_ms=duration_ms,
        status=status,
        error=error,
        input_summary=input_summary or {},
        output_summary=output_summary or {},
        metadata=metadata or {},
    )

    try:
        _EVENT_QUEUE.append(event)
        notify_subscribers(event)

        # Log to audit log if available
        if _AUDIT_LOG is not None:
            try:
                _AUDIT_LOG.log_tool_call(
                    event_id=event.event_id,
                    request_id=request_id or event.event_id,
                    tool_name=tool_name,
                    tier_applied=tier_applied,
                    status=status,
                    duration_ms=duration_ms,
                    input_summary=event.input_summary,
                    output_summary=event.output_summary,
                    error=error,
                    metadata=event.metadata,
                    timestamp=event.timestamp,
                )
            except Exception as e:
                logger.warning(f"Audit log: failed to log event {event.event_id}: {e}")

        logger.debug(f"Telemetry: emitted {tool_name} event (id={event.event_id})")
    except Exception as e:
        logger.warning(f"Telemetry: failed to emit event: {e}")

    return event


def get_recent_events(limit: int = 50) -> list[dict[str, Any]]:
    """Get recent telemetry events as JSON-serializable dicts.

    Args:
        limit: Maximum number of recent events to return

    Returns:
        List of event dicts, newest first
    """
    events = list(_EVENT_QUEUE)
    # Reverse to show newest first
    events.reverse()
    return [e.to_dict() for e in events[:limit]]


def get_event_stats() -> dict[str, Any]:
    """Get basic statistics about recent events.

    Returns:
        Dict with counts, success rate, latency stats, etc
    """
    events = list(_EVENT_QUEUE)
    if not events:
        return {
            "total_events": 0,
            "success_count": 0,
            "failure_count": 0,
            "success_rate": 0.0,
            "avg_duration_ms": 0.0,
            "tool_counts": {},
        }

    total = len(events)
    successes = sum(1 for e in events if e.status == "success")
    failures = sum(1 for e in events if e.status == "failure")
    durations = [e.duration_ms for e in events if e.duration_ms > 0]

    tool_counts = {}
    for e in events:
        tool_counts[e.tool_name] = tool_counts.get(e.tool_name, 0) + 1

    return {
        "total_events": total,
        "success_count": successes,
        "failure_count": failures,
        "success_rate": successes / total if total > 0 else 0.0,
        "avg_duration_ms": sum(durations) / len(durations) if durations else 0.0,
        "tool_counts": tool_counts,
    }


def clear_events() -> None:
    """Clear the event queue. (Debug/testing only)"""
    _EVENT_QUEUE.clear()


def add_subscriber(callback: Any) -> None:
    """Register a callback to receive new events."""
    _SUBSCRIBERS.add(callback)


def remove_subscriber(callback: Any) -> None:
    """Unregister a callback."""
    _SUBSCRIBERS.discard(callback)


def notify_subscribers(event: TelemetryEvent) -> None:
    """Notify all subscribers of a new event (for WebSocket streaming)."""
    for callback in _SUBSCRIBERS:
        try:
            callback(event.to_dict())
        except Exception as e:
            logger.warning(f"Subscriber callback failed: {e}")
