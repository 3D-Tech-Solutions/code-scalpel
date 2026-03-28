# Code Scalpel Audit Logging Guide

## Overview

The Code Scalpel MCP server now tracks all tool calls in an encrypted audit log. This provides a complete audit trail of:
- What tools were called
- What parameters were passed (input_summary)
- What data was returned (output_summary)
- How long each call took
- The license tier used
- Any errors that occurred

## Key Features

### 🔐 Encrypted Storage
- **Encryption**: All audit data is encrypted using Fernet (industry-standard AES-128)
- **Key Management**: Encryption key exists only in memory during server runtime
- **Persistence**: After server shutdown, data is unencrypted JSONL file in `~/.code-scalpel/`
- **Privacy**: Users cannot access audit data after server stops without the key

### 📊 Audit Data Structure
Each event captures:
```json
{
  "event_id": "unique-uuid",
  "request_id": "correlates multiple calls in one MCP request",
  "session_id": "unique per server session",
  "timestamp": 1711651234.567,
  "tool_name": "security_scan",
  "tier_applied": "enterprise",
  "status": "success",
  "duration_ms": 234.5,
  "input_summary": { /* tool-specific input parameters */ },
  "output_summary": { /* tool-specific results */ },
  "error": null,
  "metadata": { /* additional context */ }
}
```

### 📦 Storage Locations
```
~/.code-scalpel/
├── audit_session_{session_id}.db          # Encrypted SQLite during runtime
├── audit_{session_id}_{timestamp}.jsonl   # Exported on shutdown
├── audit_{session_id}_{timestamp}.jsonl   # Previous sessions
└── license/
    └── license.jwt
```

## Using the Audit Log API

### 1. Get Recent Events
Query recent audit events with optional filtering:

```bash
curl "http://localhost:7654/api/audit/events?limit=20&tool_name=security_scan"
```

**Parameters:**
- `limit` (default: 100) - Max events to return
- `offset` (default: 0) - Pagination offset
- `tool_name` - Filter by tool name
- `request_id` - Filter by request ID (correlates calls)
- `status` - Filter by status (success/failure/timeout)

**Response:**
```json
{
  "events": [
    {
      "event_id": "...",
      "tool_name": "security_scan",
      "status": "success",
      "duration_ms": 145.5,
      "input_summary": { ... },
      "output_summary": { ... }
    }
  ],
  "stats": {
    "total_events": 42,
    "success_count": 40,
    "failure_count": 2,
    "success_rate": 0.952,
    "tool_counts": {
      "security_scan": 15,
      "extract_code": 12,
      ...
    }
  }
}
```

### 2. Get Call Chain for a Request
Get all tool calls that happened as part of a single MCP request:

```bash
curl "http://localhost:7654/api/audit/call-chain?request_id=abc123"
```

This is useful for understanding the full impact of a single user action that may have triggered multiple tool calls.

**Response:**
```json
{
  "request_id": "abc123",
  "call_count": 3,
  "calls": [
    { "event_id": "...", "tool_name": "analyze_code", ... },
    { "event_id": "...", "tool_name": "security_scan", ... },
    { "event_id": "...", "tool_name": "generate_unit_tests", ... }
  ]
}
```

### 3. Get Audit Status
Check audit log status and encryption details:

```bash
curl "http://localhost:7654/api/audit/status"
```

**Response:**
```json
{
  "status": "active",
  "encryption": {
    "enabled": true,
    "has_key": true,
    "note": "Key exists only in memory during server runtime"
  },
  "database": {
    "path": "/home/user/.code-scalpel/audit_session_abc123def.db",
    "session_id": "abc123def"
  },
  "stats": {
    "total_events": 42,
    "success_count": 40,
    "failure_count": 2,
    "success_rate": 0.952,
    "tool_counts": { ... }
  }
}
```

## Database Space Estimation

**Typical event size:** 500-2000 bytes (compressed text only)
**Max in-memory events:** 50 (SQLite, then exported on shutdown)
**Storage:** Minimal (~1MB per 1000 events)

**Examples:**
- 1 hour of heavy use: ~100 events → ~100 KB
- 1 week of normal use: ~1000 events → ~1 MB
- 1 month of heavy use: ~10,000 events → ~10 MB

Archive files are simple JSONL (one JSON per line), easily compressible.

## On-Disk Persistence

### During Server Runtime
- Events stored in **encrypted SQLite database**
- Location: `~/.code-scalpel/audit_session_{session_id}.db`
- Accessible via `/api/audit/*` endpoints
- Decrypted on-the-fly using in-memory key

### On Server Shutdown
- All events exported to **encrypted JSONL**
- Location: `~/.code-scalpel/audit_{session_id}_{timestamp}.jsonl`
- SQLite database (.db) remains on disk for inspection
- JSONL contains all event data with decrypted fields

### After Server Stops
- Audit data is **unencrypted** in JSONL
- Cannot be decrypted without original key
- Key is not persisted anywhere
- User retains control of exported data

## Security Properties

### ✅ What's Protected
- Tool call parameters (input_summary)
- Tool outputs (output_summary)
- Timing information
- Error messages

### ✅ What's Encrypted
- All sensitive data at rest in database
- Key is ephemeral (memory-only)
- File permissions: mode 0600 (user read/write only)

### ✅ What's Not Protected
- Tool call timestamps (coarse granularity)
- Tool names (needed for queries)
- Tier and status fields (for filtering)
- Session/request IDs (for correlation)

## Environment Variables

### `CODE_SCALPEL_AUDIT_ENCRYPTION`
Enable/disable audit log encryption (default: enabled)
```bash
export CODE_SCALPEL_AUDIT_ENCRYPTION=true
```

## Querying Audit Data

### Find all calls from a specific tool
```bash
curl "http://localhost:7654/api/audit/events?tool_name=security_scan"
```

### Find all failed calls
```bash
curl "http://localhost:7654/api/audit/events?status=failure"
```

### Get statistics for the session
```bash
curl "http://localhost:7654/api/audit/status" | jq '.stats'
```

### Analyze performance
```bash
curl "http://localhost:7654/api/audit/events?limit=999" | jq '
  .events |
  group_by(.tool_name) |
  map({
    tool: .[0].tool_name,
    count: length,
    avg_duration: (map(.duration_ms) | add / length)
  })'
```

## Use Cases

### 1. **Compliance & Auditing**
Track what tools were used, when, and by whom (via request_id)

### 2. **Performance Analysis**
Identify slow tool calls and optimization opportunities

### 3. **Debugging**
See full input/output for a failed tool call

### 4. **Cost Analysis** (Future)
Understand which tools consume the most resources

### 5. **Usage Patterns**
Aggregate statistics on tool usage and tier utilization

## Examples

### Export audit data to CSV (after server stops)
```bash
# Read JSONL file and convert to CSV
jq -r '.event_id, .tool_name, .status, .duration_ms' \
  ~/.code-scalpel/audit_*.jsonl | \
  paste -d, - - - - > audit_report.csv
```

### Find slowest calls
```bash
curl "http://localhost:7654/api/audit/events?limit=999" | jq '
  .events |
  sort_by(-.duration_ms) |
  .[0:10] |
  map("\(.tool_name): \(.duration_ms)ms")'
```

### Count calls per hour
```bash
curl "http://localhost:7654/api/audit/events?limit=999" | jq '
  .events |
  map(.timestamp | floor / 3600) |
  group_by(.) |
  map({hour: .[0], count: length})'
```

## Data Retention

The audit log system is **ephemeral by design**:
- Database is **not persisted** after server shutdown
- JSONL exports are kept in `~/.code-scalpel/` for user review
- User controls retention by managing JSONL files manually
- No automatic cleanup or rotation (user decides)

## Privacy & Data Control

✅ **User Owns All Data**
- No telemetry is sent to external servers
- No central audit log aggregation
- All data stays local

✅ **Encryption During Session**
- Data is encrypted in database
- Key is memory-only, never written to disk
- Encrypted data cannot be accessed after shutdown

✅ **Transparent Export**
- On shutdown, data is exported as plain JSONL for user review
- User can delete, archive, or analyze as needed

## Troubleshooting

### "Audit log not initialized"
The server might not have started correctly. Check:
```bash
curl "http://localhost:7654/api/audit/status"
```

### Check current session ID
```bash
curl "http://localhost:7654/api/audit/status" | jq '.database.session_id'
```

### Find exported JSONL files
```bash
ls -la ~/.code-scalpel/audit_*.jsonl
```

### Read exported data
```bash
jq '.' ~/.code-scalpel/audit_*.jsonl | head -50
```

## Future Enhancements

Potential additions:
- Dashboard UI for audit browsing (collapsible event details)
- CSV/PDF export endpoints
- Retention policies and automatic cleanup
- Query builder UI for complex filtering
- Audit log rotation on file size
- Optional persistent encryption key management
