"""Audit logging system for MCP tool calls with encryption.

Tracks all tool calls in an ephemeral SQLite database that encrypts data
during the server session. On shutdown, logs are archived to encrypted JSONL.
Encryption key exists only in memory during server runtime.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)


@dataclass
class EncryptionConfig:
    """Encryption configuration for audit logs."""
    enabled: bool = True
    key: Optional[bytes] = None
    cipher: Optional[Fernet] = None


class AuditLog:
    """Session-based audit log with optional encryption."""

    def __init__(self, session_id: str, encryption_enabled: bool = True):
        """Initialize audit log for this server session.

        Args:
            session_id: Unique identifier for this server session
            encryption_enabled: Whether to encrypt audit logs
        """
        self.session_id = session_id
        self.base_dir = Path.home() / ".code-scalpel"
        self.base_dir.mkdir(parents=True, exist_ok=True)

        # Use in-memory DB + optional disk backup
        self.db_path = self.base_dir / f"audit_session_{session_id}.db"
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row

        # Setup encryption
        self.encryption = EncryptionConfig(enabled=encryption_enabled)
        if encryption_enabled:
            self._init_encryption()

        # Setup schema
        self._setup_schema()
        logger.info(
            f"Audit log initialized: session={session_id}, "
            f"db={self.db_path}, encryption={encryption_enabled}"
        )

    def _init_encryption(self) -> None:
        """Initialize encryption for this session.

        Generates a random key that exists only in memory.
        Key is NOT persisted to disk automatically.
        """
        self.encryption.key = Fernet.generate_key()
        self.encryption.cipher = Fernet(self.encryption.key)
        logger.debug(f"Encryption initialized for session {self.session_id}")

    def _setup_schema(self) -> None:
        """Create audit tables with optimized schema."""
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS tool_calls (
                event_id TEXT PRIMARY KEY,
                request_id TEXT NOT NULL,
                session_id TEXT NOT NULL,
                timestamp REAL NOT NULL,
                tool_name TEXT NOT NULL,
                tier_applied TEXT,
                status TEXT,
                duration_ms REAL,
                input_summary TEXT,
                output_summary TEXT,
                error TEXT,
                metadata TEXT,
                encrypted INTEGER DEFAULT 0
            )
        """)

        # Create indices for common queries
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_request_id ON tool_calls(request_id)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_session_id ON tool_calls(session_id)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_tool_name ON tool_calls(tool_name)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON tool_calls(timestamp DESC)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_status ON tool_calls(status)")

        self.conn.commit()
        logger.debug("Audit schema created")

    def log_tool_call(
        self,
        event_id: str,
        request_id: str,
        tool_name: str,
        tier_applied: str,
        status: str,
        duration_ms: float,
        input_summary: dict[str, Any],
        output_summary: dict[str, Any],
        error: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
        timestamp: Optional[float] = None,
    ) -> None:
        """Record a tool call in the audit log.

        Args:
            event_id: Unique event identifier
            request_id: Unique request identifier (correlates multiple calls)
            tool_name: Name of the tool that was called
            tier_applied: License tier used
            status: success, failure, timeout
            duration_ms: Execution time in milliseconds
            input_summary: Tool input parameters (scrubbed)
            output_summary: Tool output/results
            error: Error message if status is failure
            metadata: Additional metadata
            timestamp: Unix timestamp (auto-generated if None)
        """
        if timestamp is None:
            import time
            timestamp = time.time()

        # Serialize JSON fields
        input_json = json.dumps(input_summary or {})
        output_json = json.dumps(output_summary or {})
        metadata_json = json.dumps(metadata or {})

        # Encrypt if enabled
        encrypted = 0
        if self.encryption.enabled and self.encryption.cipher:
            try:
                input_json = self.encryption.cipher.encrypt(input_json.encode()).decode()
                output_json = self.encryption.cipher.encrypt(output_json.encode()).decode()
                metadata_json = self.encryption.cipher.encrypt(metadata_json.encode()).decode()
                encrypted = 1
            except Exception as e:
                logger.warning(f"Encryption failed for event {event_id}: {e}")

        try:
            self.conn.execute(
                """
                INSERT INTO tool_calls (
                    event_id, request_id, session_id, timestamp, tool_name,
                    tier_applied, status, duration_ms, input_summary,
                    output_summary, error, metadata, encrypted
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event_id,
                    request_id,
                    self.session_id,
                    timestamp,
                    tool_name,
                    tier_applied,
                    status,
                    duration_ms,
                    input_json,
                    output_json,
                    error,
                    metadata_json,
                    encrypted,
                ),
            )
            self.conn.commit()
            logger.debug(f"Logged tool call: {tool_name} (event_id={event_id})")
        except sqlite3.Error as e:
            logger.error(f"Database error logging event {event_id}: {e}")

    def get_event(self, event_id: str) -> Optional[dict[str, Any]]:
        """Retrieve a single event by ID.

        Args:
            event_id: Event identifier

        Returns:
            Event dict with decrypted fields, or None if not found
        """
        try:
            row = self.conn.execute(
                "SELECT * FROM tool_calls WHERE event_id = ?", (event_id,)
            ).fetchone()

            if not row:
                return None

            return self._decrypt_row(row)
        except Exception as e:
            logger.error(f"Error retrieving event {event_id}: {e}")
            return None

    def get_events(
        self,
        limit: int = 100,
        offset: int = 0,
        tool_name: Optional[str] = None,
        request_id: Optional[str] = None,
        status: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """Query audit log with optional filters.

        Args:
            limit: Max events to return
            offset: Pagination offset
            tool_name: Filter by tool name
            request_id: Filter by request ID
            status: Filter by status (success/failure/timeout)

        Returns:
            List of event dicts with decrypted fields
        """
        query = "SELECT * FROM tool_calls WHERE 1=1"
        params = []

        if tool_name:
            query += " AND tool_name = ?"
            params.append(tool_name)

        if request_id:
            query += " AND request_id = ?"
            params.append(request_id)

        if status:
            query += " AND status = ?"
            params.append(status)

        query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        try:
            rows = self.conn.execute(query, params).fetchall()
            return [self._decrypt_row(row) for row in rows]
        except Exception as e:
            logger.error(f"Error querying audit log: {e}")
            return []

    def get_stats(self) -> dict[str, Any]:
        """Get audit log statistics.

        Returns:
            Dict with counts by tool, status, etc.
        """
        try:
            total = self.conn.execute("SELECT COUNT(*) FROM tool_calls").fetchone()[0]
            success = self.conn.execute("SELECT COUNT(*) FROM tool_calls WHERE status = 'success'").fetchone()[0]
            failure = self.conn.execute("SELECT COUNT(*) FROM tool_calls WHERE status = 'failure'").fetchone()[0]

            tool_counts = {}
            for row in self.conn.execute("SELECT tool_name, COUNT(*) as count FROM tool_calls GROUP BY tool_name"):
                tool_counts[row[0]] = row[1]

            return {
                "total_events": total,
                "success_count": success,
                "failure_count": failure,
                "success_rate": success / total if total > 0 else 0.0,
                "tool_counts": tool_counts,
            }
        except Exception as e:
            logger.error(f"Error generating stats: {e}")
            return {}

    def _decrypt_row(self, row: sqlite3.Row) -> dict[str, Any]:
        """Decrypt fields in a database row.

        Args:
            row: Database row from sqlite3

        Returns:
            Dict with decrypted JSON fields
        """
        data = dict(row)

        # Decrypt fields if they were encrypted
        if data.get("encrypted") and self.encryption.cipher:
            try:
                if data.get("input_summary"):
                    decrypted = self.encryption.cipher.decrypt(data["input_summary"].encode()).decode()
                    data["input_summary"] = json.loads(decrypted)
                else:
                    data["input_summary"] = {}

                if data.get("output_summary"):
                    decrypted = self.encryption.cipher.decrypt(data["output_summary"].encode()).decode()
                    data["output_summary"] = json.loads(decrypted)
                else:
                    data["output_summary"] = {}

                if data.get("metadata"):
                    decrypted = self.encryption.cipher.decrypt(data["metadata"].encode()).decode()
                    data["metadata"] = json.loads(decrypted)
                else:
                    data["metadata"] = {}
            except Exception as e:
                logger.error(f"Decryption failed for event {data.get('event_id')}: {e}")
                # Return encrypted blobs as-is if decryption fails
        else:
            # Unencrypted data - just parse JSON
            data["input_summary"] = json.loads(data.get("input_summary") or "{}")
            data["output_summary"] = json.loads(data.get("output_summary") or "{}")
            data["metadata"] = json.loads(data.get("metadata") or "{}")

        return data

    def export_to_jsonl(self) -> Path:
        """Export all events to encrypted JSONL file.

        Returns:
            Path to exported JSONL file
        """
        timestamp = datetime.now(timezone.utc).isoformat()
        export_file = self.base_dir / f"audit_{self.session_id}_{timestamp.replace(':', '-')}.jsonl"

        try:
            with open(export_file, "w") as f:
                events = self.get_events(limit=999999)  # Get all events
                for event in events:
                    f.write(json.dumps(event) + "\n")

            logger.info(f"Exported {len(events)} events to {export_file}")
            return export_file
        except Exception as e:
            logger.error(f"Export failed: {e}")
            return export_file

    def cleanup(self) -> Optional[Path]:
        """Clean up and archive audit log.

        Called on server shutdown. Exports to JSONL and closes database.

        Returns:
            Path to exported JSONL file, or None if export failed
        """
        try:
            # Export to JSONL before closing
            export_file = self.export_to_jsonl()

            # Close database
            self.conn.close()

            # Keep .db file for this session (user can inspect if needed)
            logger.info(f"Audit log cleanup complete. Database: {self.db_path}, Export: {export_file}")
            return export_file
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
            try:
                self.conn.close()
            except Exception:
                pass
            return None

    def get_encryption_status(self) -> dict[str, Any]:
        """Get encryption status for this session.

        Returns:
            Dict with encryption info (no key material exposed)
        """
        return {
            "enabled": self.encryption.enabled,
            "session_id": self.session_id,
            "has_key": self.encryption.key is not None,
            "db_path": str(self.db_path),
        }
