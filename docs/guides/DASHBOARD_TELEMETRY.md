# Code Scalpel Dashboard Telemetry

**Version:** 2.1.3 (MVP)
**Status:** Beta
**Last Updated:** 2026-03-27

## Overview

The Code Scalpel Dashboard provides **real-time visibility** into MCP server tool calls and extracted data. When you run `uvx codescalpel mcp`, the dashboard automatically starts and shows:

- **Live tool call stream** - Watch tools execute in real-time
- **Performance metrics** - Success rates, latency, tier information
- **Usage statistics** - Which tools are most used, average execution times
- **Error tracking** - Instantly see failures and error details

```
$ uvx codescalpel mcp
MCP Server: stdio://code-scalpel
Dashboard: http://localhost:7654     ← Open this in your browser!
✓ Telemetry enabled
✓ Ready for connections
```

## Quick Start

### 1. Start the MCP Server

```bash
python -m code_scalpel.mcp.server
```

The terminal will print:
```
Dashboard: http://localhost:7654
```

### 2. Open in Your Browser

Click the URL or open `http://localhost:7654` in your browser.

### 3. Watch Tool Calls

As Claude or your MCP client uses Code Scalpel tools, events stream live into the dashboard.

## What Data is Captured?

For each tool call, the dashboard records:

- **Tool Name** - Which tool was called (analyze_code, security_scan, etc.)
- **Status** - Success/Failure/Timeout
- **Duration** - Execution time in milliseconds
- **Tier** - License tier applied (community/pro/enterprise)
- **Input Summary** - Files analyzed, parameters used (scrubbed for privacy)
- **Output Summary** - Functions found, vulnerabilities detected, etc.
- **Timestamp** - When the call happened
- **Error Details** - If failed, what went wrong

## Dashboard Features (MVP)

### License & Tier Panel
- **Current Tier Display** - Shows community/pro/enterprise badge
- **License Status** - Displays valid/invalid/expired status
- **License Location** - Shows where the license file is loaded from
- **Upgrade Prompt** - When on community tier, shows prominent upgrade section
- **File Upload** - Drag-drop or click to upload license.jwt file
- **Smart Detection** - Automatically shows/hides upgrade panel based on tier

### Real-time Event Stream
- **WebSocket Connection** - Live updates as tools execute
- **Recent Events List** - Shows last 50 tool calls
- **Reverse Chronological** - Newest events at top

### Statistics Panel
- **Total Calls** - How many tools have been called
- **Success Rate** - Percentage of successful executions
- **Average Duration** - Mean execution time across all calls
- **Connection Status** - WebSocket connectivity indicator

### Event Details
- Tool name, status badge, execution time
- Tier information (showing license usage patterns)
- Error messages for failed calls

## License Upgrade Flow

### From Community to Pro/Enterprise

1. **Start MCP Server** with community tier (default)
   ```bash
   python -m code_scalpel.mcp.server
   # Dashboard: http://localhost:7654
   ```

2. **Open Dashboard** - You'll see:
   - Yellow "Community" tier badge
   - "⚠ No valid license" status
   - Prominent upgrade section

3. **Upload License**
   - Click file upload area or drag license.jwt
   - License validates and saves to `~/.code-scalpel/license/`
   - Success message confirms tier (Pro/Enterprise)

4. **Restart Server** for changes to take effect
   - New tier appears in dashboard
   - Enhanced features now available

### What You Get with Each Tier

| Feature | Community | Pro | Enterprise |
|---------|-----------|-----|------------|
| Basic analysis (analyze_code) | ✓ | ✓ | ✓ |
| Security scanning | ✓ | ✓ | ✓ |
| Advanced metrics | ✗ | ✓ | ✓ |
| Symbolic execution paths | Limited | ✓ | ✓ |
| Cross-file taint analysis | ✗ | Limited | ✓ |
| Compliance checking | ✗ | ✗ | ✓ |
| Custom security rules | ✗ | ✗ | ✓ |

## Example Workflow

```python
# In Claude or your MCP client
user> "Analyze this Python file for security issues"

# Claude calls:
→ analyze_code(file_path="app.py")       # 145ms, community tier
→ security_scan(file_path="app.py")      # 234ms, pro tier

# Dashboard shows both calls instantly:
[14:32:01] analyze_code    SUCCESS    145ms   community
[14:32:02] security_scan   SUCCESS    234ms   pro
```

## Architecture

### Components

1. **Telemetry Module** (`src/code_scalpel/telemetry.py`)
   - Event data model with schema validation
   - In-memory event queue (max 50 events)
   - Statistics aggregation
   - Subscriber notification system

2. **Dashboard Service** (`src/code_scalpel/dashboard_service.py`)
   - FastAPI web server (auto-selects available port)
   - HTML5 frontend with vanilla JavaScript
   - WebSocket endpoint for live streaming
   - HTTP endpoints for querying events

3. **Server Integration** (`src/code_scalpel/mcp/server.py`)
   - Auto-starts dashboard on server boot
   - Prints dashboard URL to stderr/stdout
   - Hooks telemetry events to broadcast

4. **Broadcasting Pipeline**
   ```
   Tool Call
      ↓
   emit_tool_event() [telemetry.py]
      ↓
   broadcast_event() [dashboard_service.py]
      ↓
   WebSocket Clients [dashboard UI]
   ```

## Privacy & Security

- **No Code Transmission** - Only metadata and statistics sent to dashboard
- **Localhost Only** - Dashboard binds to 127.0.0.1 by default
- **Input Scrubbing** - File paths and parameters are summarized, not exposed
- **Minimal Data** - Only aggregated statistics stored (max 50 events)
- **Read-Only** - Dashboard is view-only, no input validation/injection risk

## Configuration

### Telemetry Settings

Currently, telemetry is **always enabled** (MVP). Future versions will support:
- `SCALPEL_TELEMETRY_ENABLED=true/false`
- `SCALPEL_DASHBOARD_PORT=7654` (manual port selection)
- `SCALPEL_TELEMETRY_PERSIST=true` (JSONL history)

### Remote License Verification

Code Scalpel supports optional **remote verification** where the license tier is validated against a central authority server. This enables:
- Real-time tier validation
- License revocation enforcement
- Offline grace periods
- Compliance with corporate licensing policies

#### Environment Variables

| Variable | Purpose | Example |
|----------|---------|---------|
| `CODE_SCALPEL_LICENSE_VERIFIER_URL` | Remote verifier endpoint | `https://license.example.com` |
| `CODE_SCALPEL_LICENSE_ENVIRONMENT` | Environment for the verifier | `production`, `staging` |
| `CODE_SCALPEL_LICENSE_VERIFY_TIMEOUT_SECONDS` | Verification timeout | `5` |
| `CODE_SCALPEL_LICENSE_VERIFY_RETRIES` | Retry attempts on failure | `2` |
| `CODE_SCALPEL_LICENSE_CACHE_PATH` | Path to verification cache | `~/.code-scalpel/cache/` |

#### Remote Verification Flow

1. **MCP Server Starts**
   - Loads local JWT license file
   - If `CODE_SCALPEL_LICENSE_VERIFIER_URL` is set, enables remote verification
   - Attempts to contact remote verifier (with timeout/retry)

2. **Decision Making**
   - **Success**: Remote verifier responds with authorization decision
   - **Failure**: Falls back to offline grace period

3. **Verification Results**
   - **remote_verified=true** - Remote server confirmed the license
   - **remote_reason** - Explanation of the result (see below)
   - **remote_tier** - Server-side tier assignment (may differ from local)

#### Remote Verification Reasons

The `remote_reason` field in the `/api/license` endpoint explains the verification status:

| Reason | Meaning | Tier Applied |
|--------|---------|--------------|
| `remote_verified` | License validated by remote server | As per server decision |
| `cache_fresh` | Using cached verification (still valid) | As per cached decision |
| `offline_grace` | Verifier unavailable, grace period active | Local tier (reduced) |
| `offline_denied` | Verifier unavailable, grace expired | Community tier |
| `license_expired` | License past expiration date | Community tier |

#### Offline Grace Period

When the remote verifier is unavailable:
1. **Grace Period Active** (default: 24 hours)
   - Status shows: `remote_reason: "offline_grace"`
   - Tier: Use local JWT tier (reduced to pro if enterprise)
   - Dashboard badge: Yellow ⚠️

2. **Grace Period Expired**
   - Status shows: `remote_reason: "offline_denied"`
   - Tier: Community (limited features)
   - Dashboard badge: Red 🛑

3. **Recovery**
   - When verifier is reachable again, full tier is restored
   - Cache is updated with fresh verification

#### Dashboard License Panel with Remote Verification

When remote verification is enabled, the dashboard shows:

```
📜 License & Tier
├─ Current Tier: Enterprise
├─ Status: ✅ Valid & Verified
├─ License File: ~/.code-scalpel/license/license.jwt
├─ Remote Verification: ✅ Verified
│  └─ Last Verified: 2026-03-28 14:32:01
│  └─ Reason: remote_verified
└─ Upgrade: (hidden, licensed)
```

**Verification Status Badges:**
- 🟢 **remote_verified** - Green badge, "Verified with central system"
- 🔵 **cache_fresh** - Blue badge, "Cached verification (valid until X)"
- 🟡 **offline_grace** - Yellow badge, "Offline grace period (X hours remaining)"
- 🔴 **offline_denied** - Red badge, "Verification failed, reverting to community"

#### Setup Example

##### Local Development (No Remote Verifier)

```bash
export CODE_SCALPEL_LICENSE_VERIFIER_URL=""
python -m code_scalpel.mcp.server
```

Dashboard shows: `remote_verified: false`

##### Production with Remote Verifier

```bash
export CODE_SCALPEL_LICENSE_VERIFIER_URL="https://license.company.com/verify"
export CODE_SCALPEL_LICENSE_VERIFY_TIMEOUT_SECONDS="5"
export CODE_SCALPEL_LICENSE_VERIFY_RETRIES="2"
python -m code_scalpel.mcp.server
```

Dashboard shows: `remote_verified: true` (if server is reachable)

##### Staging with Custom Cache

```bash
export CODE_SCALPEL_LICENSE_VERIFIER_URL="https://staging-license.company.com/verify"
export CODE_SCALPEL_LICENSE_ENVIRONMENT="staging"
export CODE_SCALPEL_LICENSE_CACHE_PATH="/tmp/license-cache/"
python -m code_scalpel.mcp.server
```

## Troubleshooting

### Dashboard won't open

**Issue:** "Connection refused" when opening `http://localhost:7654`

**Solution:**
1. Check the server logs for the dashboard URL
2. Verify port 7654 is not in use: `lsof -i :7654`
3. Try the next available port (server auto-selects if taken)

### Events not appearing

**Issue:** Dashboard loads but no events show up

**Solution:**
1. Make sure tools are actually being called (check MCP client logs)
2. Check browser console for JavaScript errors
3. Verify WebSocket connection: DevTools → Network → WS

### Performance concerns

**Issue:** Dashboard might impact server performance

**Solution:**
- Telemetry is non-blocking (failures are logged but don't fail tools)
- Events are stored in-memory only (max 50 events)
- WebSocket broadcasts happen async

### Remote Verification Issues

**Issue:** Remote verifier always shows `remote_verified: false` or `offline_grace`

**Solution:**
1. Check environment variable is set:
   ```bash
   echo $CODE_SCALPEL_LICENSE_VERIFIER_URL
   ```
2. Verify verifier URL is reachable:
   ```bash
   curl -v https://license.example.com/verify
   ```
3. Check timeout setting (default: 5s):
   ```bash
   export CODE_SCALPEL_LICENSE_VERIFY_TIMEOUT_SECONDS="10"
   python -m code_scalpel.mcp.server
   ```
4. Increase retries:
   ```bash
   export CODE_SCALPEL_LICENSE_VERIFY_RETRIES="3"
   ```

**Issue:** License tier keeps reverting to community despite valid enterprise license

**Solution:**
- Check if grace period has expired: Look for `offline_denied` reason in dashboard
- Verify remote verifier is operational and has correct license database
- Check server-side tier assignment (may differ from local JWT)
- Try clearing cache:
  ```bash
  rm -rf ~/.code-scalpel/cache/
  ```

**Issue:** Verification slows down server startup

**Solution:**
- Reduce `CODE_SCALPEL_LICENSE_VERIFY_TIMEOUT_SECONDS` (min: 1)
- Run verifier closer to network (reduce latency)
- Pre-warm the cache by starting server before peak usage

## Advanced Usage

### Manual Event Emission

```python
from code_scalpel import telemetry

event = telemetry.emit_tool_event(
    tool_name="custom_tool",
    tier_applied="enterprise",
    duration_ms=150.5,
    status="success",
    input_summary={"files": 5},
    output_summary={"results": 42},
)
```

### Getting Recent Events (HTTP API)

```bash
curl http://localhost:7654/api/events | jq
```

Response:
```json
{
  "events": [
    {
      "event_id": "...",
      "tool_name": "analyze_code",
      "status": "success",
      "duration_ms": 145.5,
      "tier_applied": "community",
      "timestamp": 1711532401.5,
      "timestamp_iso": "2026-03-27T14:32:01.500000",
      "input_summary": {...},
      "output_summary": {...}
    }
  ],
  "stats": {
    "total_events": 5,
    "success_rate": 1.0,
    "avg_duration_ms": 150.0,
    "tool_counts": {"analyze_code": 2, "security_scan": 3}
  }
}
```

### WebSocket Connection Example

```javascript
const ws = new WebSocket('ws://localhost:7654/ws');

ws.onmessage = (event) => {
  const msg = JSON.parse(event.data);
  if (msg.type === 'tool_event') {
    console.log(`Tool: ${msg.data.tool_name}, Duration: ${msg.data.duration_ms}ms`);
  }
};
```

## Demo

Try the demo to see telemetry in action:

```bash
python scripts/demo_dashboard_telemetry.py
```

This emits sample events and shows the dashboard with data.

## Roadmap (Future Versions)

**Phase 2 (next quarter):**
- JSONL persistence for historical analysis
- Prometheus/Grafana integration
- Tool-specific drill-down views
- Performance regression detection

**Phase 3:**
- Per-tier usage analytics
- License compliance reporting
- Aggregate telemetry (opt-in, anonymized)
- API rate limiting dashboard

**Phase 4:**
- Slack/email alerts for errors
- Automated performance tuning suggestions
- Multi-session aggregation (for server deployments)

## Feedback

Have ideas? Found a bug? Let us know:
- **GitHub Issues:** [anthropics/code-scalpel#new](https://github.com/anthropics/code-scalpel/issues/new)
- **Discussions:** [GitHub Discussions](https://github.com/anthropics/code-scalpel/discussions)

---

**Made with ❤️ by Code Scalpel**
