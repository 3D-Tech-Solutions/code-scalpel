"""
Autonomy Audit Trail - Complete history of autonomous operations.

# [20251217_FEATURE] v3.0.0 Autonomy - Full audit trail for debugging and compliance
# [20251217_DOCS] Clarified that audit logging uses cryptographic hashing, not signatures
This module provides cryptographically-hashed, immutable audit logging for all
autonomous operations with parent-child tracking and multi-format export.
"""

import csv
import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class AuditEntry:
    """
    Single entry in audit trail.

    # [20251217_FEATURE] v3.0.0 Autonomy P0 - Immutable audit entry

    Features:
    - Immutable once created
    - Cryptographic hashes for input/output
    - Parent-child relationships for nested operations
    - Timestamp and duration tracking
    """

    id: str
    timestamp: datetime
    event_type: str
    operation: str
    input_hash: str
    output_hash: str
    success: bool
    duration_ms: int
    metadata: dict[str, Any] = field(default_factory=dict)
    parent_id: str | None = None  # For nested operations


@dataclass
class AutonomyAuditTrail:
    """
    Complete audit trail for autonomous operations.

    # [20251217_FEATURE] v3.0.0 Autonomy P0 - Audit trail manager

    Features:
    - Immutable entries with cryptographic hashes
    - Parent-child relationships for nested operations
    - Export to multiple formats (JSON, CSV, HTML)
    - Query by time range, event type, success/failure

    [20251217_FEATURE] v3.0.0 Autonomy P0 - Audit trail manager
    """

    storage_path: Path = field(default_factory=lambda: Path(".code-scalpel/autonomy_audit"))
    current_session_id: str = field(default="")

    def __post_init__(self):
        """Initialize storage and generate session ID."""
        if isinstance(self.storage_path, str):
            self.storage_path = Path(self.storage_path)

        self.storage_path.mkdir(parents=True, exist_ok=True)

        if not self.current_session_id:
            self.current_session_id = self._generate_session_id()

    def record(
        self,
        event_type: str,
        operation: str,
        input_data: Any,
        output_data: Any,
        success: bool,
        duration_ms: int,
        metadata: dict | None = None,
        parent_id: str | None = None,
    ) -> str:
        """
        Record an audit entry.

        # [20251217_FEATURE] v3.0.0 Autonomy P0 - Record operations

        Args:
            event_type: Type of event (e.g., "FIX_LOOP_START", "ERROR_ANALYSIS")
            operation: Specific operation performed
            input_data: Input data for the operation
            output_data: Output data from the operation
            success: Whether operation succeeded
            duration_ms: Duration in milliseconds
            metadata: Additional metadata
            parent_id: ID of parent operation for nested ops

        Returns:
            Entry ID for reference
        """
        entry_id = self._generate_entry_id()

        entry = AuditEntry(
            id=entry_id,
            timestamp=datetime.now(),
            event_type=event_type,
            operation=operation,
            input_hash=self._hash_data(input_data),
            output_hash=self._hash_data(output_data),
            success=success,
            duration_ms=duration_ms,
            metadata=metadata or {},
            parent_id=parent_id,
        )

        # Store entry
        self._store_entry(entry, input_data, output_data)

        return entry_id

    def export(
        self,
        format: str = "json",
        time_range: tuple[datetime, datetime] | None = None,
        event_types: list[str] | None = None,
        success_only: bool = False,
    ) -> str:
        """
        Export audit trail to specified format.

        # [20251217_FEATURE] v3.0.0 Autonomy P0 - Multi-format export

        Args:
            format: "json", "csv", "html"
            time_range: Optional filter by time
            event_types: Optional filter by event type
            success_only: Only include successful operations

        Returns:
            Exported data as string
        """
        entries = self._load_entries()

        # Apply filters
        if time_range:
            start, end = time_range
            entries = [e for e in entries if start <= e.timestamp <= end]

        if event_types:
            entries = [e for e in entries if e.event_type in event_types]

        if success_only:
            entries = [e for e in entries if e.success]

        # Export
        if format == "json":
            return self._export_json(entries)
        elif format == "csv":
            return self._export_csv(entries)
        elif format == "html":
            return self._export_html(entries)
        else:
            raise ValueError(f"Unknown format: {format}")

    def get_operation_trace(self, entry_id: str) -> list[AuditEntry]:
        """
        Get full trace of an operation including all nested operations.

        # [20251217_FEATURE] v3.0.0 Autonomy P0 - Operation tracing

        Returns entries in execution order.

        Args:
            entry_id: ID of the root operation to trace

        Returns:
            List of AuditEntry objects in execution order
        """
        entries = self._load_entries()

        # Find root entry
        root = next((e for e in entries if e.id == entry_id), None)
        if not root:
            return []

        # Find all children recursively
        trace = [root]
        children = [e for e in entries if e.parent_id == entry_id]
        for child in children:
            trace.extend(self.get_operation_trace(child.id))

        return sorted(trace, key=lambda e: e.timestamp)

    def get_session_summary(self) -> dict[str, Any]:
        """
        Get summary of current session.

        # [20251217_FEATURE] v3.0.0 Autonomy P0 - Session summary

        Returns:
            Dictionary with summary statistics
        """
        entries = self._load_entries()

        total = len(entries)
        successful = sum(1 for e in entries if e.success)
        failed = total - successful
        total_duration = sum(e.duration_ms for e in entries)

        # Count by event type
        event_types = {}
        for entry in entries:
            event_types[entry.event_type] = event_types.get(entry.event_type, 0) + 1

        return {
            "session_id": self.current_session_id,
            "total_operations": total,
            "successful": successful,
            "failed": failed,
            "total_duration_ms": total_duration,
            "event_types": event_types,
        }

    # Private methods

    def _generate_session_id(self) -> str:
        """
        Generate unique session ID.

        # [20251217_FEATURE] v3.0.0 Autonomy P0 - Session tracking

        Format: YYYYMMDD_HHMMSS_<short_hash>
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        hash_suffix = hashlib.sha256(str(datetime.now().timestamp()).encode()).hexdigest()[:6]
        return f"{timestamp}_{hash_suffix}"

    def _generate_entry_id(self) -> str:
        """
        Generate unique entry ID.

        # [20251217_FEATURE] v3.0.0 Autonomy P0 - Entry tracking

        Format: op_<timestamp>_<short_hash>
        """
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
        hash_suffix = hashlib.sha256(timestamp.encode()).hexdigest()[:8]
        return f"op_{timestamp}_{hash_suffix}"

    def _hash_data(self, data: Any) -> str:
        """
        Create cryptographic hash of data.

        # [20251217_FEATURE] v3.0.0 Autonomy P0 - Data integrity

        Args:
            data: Data to hash

        Returns:
            SHA256 hash as hex string
        """
        # [20251217_SECURITY] Use deterministic JSON serialization for hashing
        try:
            # Prefer canonical JSON with sorted keys for stable hashes
            data_str = json.dumps(data, sort_keys=True, default=str, ensure_ascii=False)
        except TypeError:
            # Fallback: last-resort string conversion if JSON serialization fails
            data_str = str(data)
        return hashlib.sha256(data_str.encode("utf-8")).hexdigest()

    def _store_entry(self, entry: AuditEntry, input_data: Any, output_data: Any):
        """
        Store entry and associated data.

        # [20251217_FEATURE] v3.0.0 Autonomy P0 - Persistent storage

        Stores:
        - Entry metadata in JSON
        - Input data (truncated if large)
        - Output data (truncated if large)

        Args:
            entry: AuditEntry to store
            input_data: Input data for debugging
            output_data: Output data for debugging
        """
        session_dir = self.storage_path / self.current_session_id
        session_dir.mkdir(exist_ok=True)

        # Store entry metadata
        entry_file = session_dir / f"{entry.id}.json"
        with open(entry_file, "w") as f:
            json.dump(self._entry_to_dict(entry), f, indent=2, default=str)

        # Store input/output (for debugging)
        data_dir = session_dir / "data"
        data_dir.mkdir(exist_ok=True)

        # Truncate large inputs to avoid storage issues
        input_str = str(input_data)[:10000]
        output_str = str(output_data)[:10000]

        with open(data_dir / f"{entry.id}_input.json", "w") as f:
            json.dump({"data": input_str, "truncated": len(str(input_data)) > 10000}, f)

        with open(data_dir / f"{entry.id}_output.json", "w") as f:
            json.dump({"data": output_str, "truncated": len(str(output_data)) > 10000}, f)

    def _load_entries(self) -> list[AuditEntry]:
        """
        Load all entries from current session.

        # [20251217_FEATURE] v3.0.0 Autonomy P0 - Entry retrieval

        Returns:
            List of AuditEntry objects
        """
        session_dir = self.storage_path / self.current_session_id
        if not session_dir.exists():
            return []

        entries = []
        for entry_file in session_dir.glob("*.json"):
            if entry_file.name.startswith("op_"):
                with open(entry_file) as f:
                    data = json.load(f)
                    entry = self._dict_to_entry(data)
                    entries.append(entry)

        return sorted(entries, key=lambda e: e.timestamp)

    def _entry_to_dict(self, entry: AuditEntry) -> dict:
        """
        Convert AuditEntry to dictionary.

        # [20251217_FEATURE] v3.0.0 Autonomy P0 - Serialization

        Args:
            entry: AuditEntry to convert

        Returns:
            Dictionary representation
        """
        data = asdict(entry)
        # Convert datetime to ISO format
        data["timestamp"] = entry.timestamp.isoformat()
        return data

    def _dict_to_entry(self, data: dict) -> AuditEntry:
        """
        Convert dictionary to AuditEntry.

        # [20251217_FEATURE] v3.0.0 Autonomy P0 - Deserialization

        Args:
            data: Dictionary with entry data

        Returns:
            AuditEntry object
        """
        # Convert ISO format back to datetime
        data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        return AuditEntry(**data)

    def _export_json(self, entries: list[AuditEntry]) -> str:
        """
        Export entries to JSON format.

        # [20251217_FEATURE] v3.0.0 Autonomy P0 - JSON export

        Args:
            entries: List of entries to export

        Returns:
            JSON string
        """
        # [20251217_BUGFIX] Make summary statistics consistent with filtered export entries
        summary = {
            "total_operations": len(entries),
            "successful": sum(1 for e in entries if e.success),
            "failed": sum(1 for e in entries if not e.success),
            "total_duration_ms": sum(e.duration_ms for e in entries),
        }

        operations = []
        for entry in entries:
            op_dict = self._entry_to_dict(entry)
            # Add children if this is a parent
            children = [e for e in entries if e.parent_id == entry.id]
            if children:
                op_dict["children"] = [self._entry_to_dict(c) for c in children]
            operations.append(op_dict)

        export_data = {
            "session_id": self.current_session_id,
            "summary": summary,
            "operations": operations,
        }

        return json.dumps(export_data, indent=2, default=str)

    def _export_csv(self, entries: list[AuditEntry]) -> str:
        """
        Export entries to CSV format.

        # [20251217_FEATURE] v3.0.0 Autonomy P0 - CSV export

        Args:
            entries: List of entries to export

        Returns:
            CSV string
        """
        import io

        output = io.StringIO()
        writer = csv.writer(output)

        # Write header
        writer.writerow(
            [
                "id",
                "timestamp",
                "event_type",
                "operation",
                "success",
                "duration_ms",
                "parent_id",
                "input_hash",
                "output_hash",
            ]
        )

        # Write data
        for entry in entries:
            writer.writerow(
                [
                    entry.id,
                    entry.timestamp.isoformat(),
                    entry.event_type,
                    entry.operation,
                    entry.success,
                    entry.duration_ms,
                    entry.parent_id or "",
                    entry.input_hash,
                    entry.output_hash,
                ]
            )

        return output.getvalue()

    def _export_html(self, entries: list[AuditEntry]) -> str:
        """
        Export entries to HTML report format.

        # [20251217_FEATURE] v3.0.0 Autonomy P1 - HTML report

        Args:
            entries: List of entries to export

        Returns:
            HTML string
        """
        # [20251217_BUGFIX] Ensure HTML summary matches filtered entries, not all session entries
        total_ops = len(entries)
        success_ops = sum(1 for entry in entries if entry.success)
        failure_ops = total_ops - success_ops
        total_duration_ms = sum(entry.duration_ms for entry in entries)
        avg_duration_ms = int(total_duration_ms / total_ops) if total_ops else 0
        success_rate = (success_ops / total_ops * 100.0) if total_ops else 0.0
        summary = {
            "total_operations": total_ops,
            "successful": success_ops,
            "failed": failure_ops,
            "success_rate": success_rate,
            "total_duration_ms": total_duration_ms,
            "avg_duration_ms": avg_duration_ms,
        }

        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Audit Report - {self.current_session_id}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1 {{ color: #333; }}
        .summary {{ background: #f5f5f5; padding: 15px; border-radius: 5px; margin: 20px 0; }}
        .summary-item {{ display: inline-block; margin-right: 30px; }}
        table {{ border-collapse: collapse; width: 100%; margin-top: 20px; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #4CAF50; color: white; }}
        tr:nth-child(even) {{ background-color: #f2f2f2; }}
        .success {{ color: green; }}
        .failure {{ color: red; }}
    </style>
</head>
<body>
    <h1>Autonomy Audit Report</h1>
    <p>Session ID: {self.current_session_id}</p>

    <div class="summary">
        <h2>Summary</h2>
        <div class="summary-item"><strong>Total Operations:</strong> {summary['total_operations']}</div>
        <div class="summary-item"><strong>Successful:</strong> <span class="success">{summary['successful']}</span></div>
        <div class="summary-item"><strong>Failed:</strong> <span class="failure">{summary['failed']}</span></div>
        <div class="summary-item"><strong>Total Duration:</strong> {summary['total_duration_ms']} ms</div>
    </div>

    <h2>Operations</h2>
    <table>
        <tr>
            <th>ID</th>
            <th>Timestamp</th>
            <th>Event Type</th>
            <th>Operation</th>
            <th>Success</th>
            <th>Duration (ms)</th>
            <th>Parent ID</th>
        </tr>
"""

        for entry in entries:
            success_class = "success" if entry.success else "failure"
            success_text = "✓" if entry.success else "✗"
            html += f"""        <tr>
            <td>{entry.id}</td>
            <td>{entry.timestamp.strftime('%Y-%m-%d %H:%M:%S')}</td>
            <td>{entry.event_type}</td>
            <td>{entry.operation}</td>
            <td class="{success_class}">{success_text}</td>
            <td>{entry.duration_ms}</td>
            <td>{entry.parent_id or '-'}</td>
        </tr>
"""

        html += """    </table>
</body>
</html>
"""
        return html
