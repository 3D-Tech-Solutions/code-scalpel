# Testing Code Scalpel Local Development Version

Complete guide to test the dashboard telemetry with the local dev version.

## Prerequisites

- Python 3.10+
- pip (or uv)
- Git
- An MCP client (Claude Desktop, Cursor, etc.)

## Part 1: Setup Local Development Environment

### 1.1 Install in Development Mode

```bash
cd /path/to/code-scalpel
pip install -e ".[dev]"
```

This installs the repo as editable, so code changes are immediately available.

### 1.2 Verify Dependencies

```bash
# Check all dependencies installed
pip list | grep -E "fastapi|websockets|uvicorn"

# Should show:
# fastapi>=0.100.0
# websockets>=11.0
# uvicorn
```

If missing, install them:
```bash
pip install fastapi websockets
```

### 1.3 Check Python Path (Important!)

The local `src/` code needs to be imported first:

```bash
python -c "
import sys
sys.path.insert(0, 'src')
from code_scalpel.mcp.server import run_server
print('✓ Local development version loaded')
"
```

**For editable install with `-e`, this should work automatically.**

### 1.4 Configure License File Location (Optional)

Code Scalpel automatically discovers license files in this order:
1. `CODE_SCALPEL_LICENSE_PATH` environment variable (if set)
2. `.code-scalpel/license/license.jwt` (project root)
3. `~/.code-scalpel/license/license.jwt` (user home)
4. Falls back to **Community tier** if no license found

**To use a custom license location:**

```bash
# Option A: Set environment variable
export CODE_SCALPEL_LICENSE_PATH=/path/to/your/license.jwt
python -m code_scalpel.mcp.server

# Option B: Copy license to default location
mkdir -p ~/.code-scalpel/license
cp /path/to/your/license.jwt ~/.code-scalpel/license/license.jwt

# Option C: Configure in Claude Desktop
# Edit ~/.claude/profiles/default/claude_desktop_config.json:
{
  "mcpServers": {
    "code-scalpel": {
      "command": "python",
      "args": ["-m", "code_scalpel.mcp.server"],
      "cwd": "/path/to/code-scalpel",
      "env": {
        "PYTHONPATH": "/path/to/code-scalpel/src",
        "CODE_SCALPEL_LICENSE_PATH": "/path/to/your/license.jwt"
      }
    }
  }
}
```

**Check license status on dashboard:**
- Open `http://localhost:7654`
- Look at the "📜 License & Tier" panel
- Shows current tier (Community/Pro/Enterprise)
- Shows remote verification status (if verifier configured)

## Part 2: Run MCP Server Locally

### 2.1 Start the Server (Development Mode)

```bash
# From the repo root
python -m code_scalpel.mcp.server
```

**Expected output:**
```
============================================================
Code Scalpel MCP Server v2.1.3
============================================================
Project Root: /path/to/code-scalpel
License Tier: ENTERPRISE
Dashboard: http://localhost:7654
============================================================
✓ Telemetry enabled
✓ Ready for connections
```

**Key checks:**
- ✅ Version number is correct
- ✅ Project root points to your repo
- ✅ Dashboard URL is printed
- ✅ Telemetry enabled message appears

**Note:** Server will stay running in the terminal. See section 2.4 for stopping.

### 2.2 Test Dashboard is Accessible

In another terminal:
```bash
curl http://localhost:7654
# Should return HTML with "Code Scalpel Dashboard"
```

Or open in browser: http://localhost:7654

### 2.3 Check Telemetry API

```bash
curl http://localhost:7654/api/events | jq
# Should return:
# {
#   "events": [],
#   "stats": {
#     "total_events": 0,
#     ...
#   }
# }
```

### 2.4 Stop the Server Gracefully

**Option A: Dashboard UI (Recommended)**
1. Open the dashboard: http://localhost:7654
2. Click the **⏹️ Stop Server** button (top-right corner)
3. Confirm shutdown in the modal dialog
4. Server will gracefully shut down, exporting the audit log
5. The terminal will show the server has exited

**Option B: Terminal (Ctrl+C)**
```bash
# Press Ctrl+C in the terminal where the server is running
^C
```

This sends SIGINT to the process. The server will attempt graceful shutdown.

**Option C: kill command**
```bash
# In another terminal
ps aux | grep "code_scalpel.mcp.server"
kill <PID>
```

**Graceful shutdown includes:**
- ✓ Closing all WebSocket connections
- ✓ Exporting audit log to JSONL file
- ✓ Cleaning up resources
- ✓ Saving telemetry data

## Part 3: Test with Real Tool Calls

### Option A: Using Claude Desktop (Recommended)

#### 3A.1 Configure Claude Desktop

Edit `~/.claude/profiles/default/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "code-scalpel": {
      "command": "python",
      "args": ["-m", "code_scalpel.mcp.server"],
      "cwd": "/path/to/code-scalpel",
      "env": {
        "PYTHONPATH": "/path/to/code-scalpel/src"
      }
    }
  }
}
```

**Key points:**
- `cwd` must point to your repo root
- `PYTHONPATH` points to `src/` (ensures local code is used)

#### 3A.2 Restart Claude Desktop

Close and reopen Claude Desktop. It will start your local MCP server.

#### 3A.3 Test a Tool Call

In Claude:
```
Analyze this Python file: /path/to/code-scalpel/src/code_scalpel/telemetry.py

Tell me what functions and classes it defines.
```

Claude will call `analyze_code` tool.

#### 3A.4 Check Dashboard

While Claude runs the analysis, open dashboard: http://localhost:7654

**You should see:**
- Event appearing in real-time
- Tool name: `analyze_code`
- Duration time
- Function/class counts
- Status: SUCCESS

### Option B: Using Cursor (Similar Setup)

Cursor uses the same `claude_desktop_config.json` file.

### Option C: Direct Python Test

```python
import asyncio
import sys
sys.path.insert(0, 'src')

from code_scalpel.mcp.tools.analyze import analyze_code
from code_scalpel.mcp.protocol import set_current_tier

# Set tier for testing
set_current_tier("enterprise")

# Analyze a real file
result = asyncio.run(analyze_code(
    file_path="src/code_scalpel/telemetry.py"
))

print("✓ Tool call completed")
print(f"  Functions: {len(result.data.functions)}")
print(f"  Classes: {len(result.data.classes)}")

# Check telemetry was emitted
from code_scalpel import telemetry
events = telemetry.get_recent_events(limit=1)
print(f"✓ Telemetry event emitted: {events[0]['tool_name']}")
```

Run it:
```bash
python test_local.py
```

Open dashboard while running: http://localhost:7654

**You should see the event appear!**

## Part 4: Verify Telemetry Capture

### 4.1 Check Recent Events (HTTP API)

```bash
curl http://localhost:7654/api/events | jq '.events[0]'
```

Should show:
```json
{
  "event_id": "...",
  "tool_name": "analyze_code",
  "status": "success",
  "tier_applied": "enterprise",
  "duration_ms": 145.5,
  "output_summary": {
    "function_count": 5,
    "class_count": 2,
    ...
  }
}
```

### 4.2 Check Statistics

```bash
curl http://localhost:7654/api/events | jq '.stats'
```

Should show:
```json
{
  "total_events": 1,
  "success_count": 1,
  "failure_count": 0,
  "success_rate": 1.0,
  "avg_duration_ms": 145.5,
  "tool_counts": {
    "analyze_code": 1
  }
}
```

### 4.3 Check License Status

```bash
curl http://localhost:7654/api/license | jq
```

Should show your current tier.

## Part 5: Run Integration Tests

### 5.1 Run Against Local Server

Start server in one terminal:
```bash
python -m code_scalpel.mcp.server
```

Run tests in another:
```bash
# Set PYTHONPATH to use local src/
export PYTHONPATH=/path/to/code-scalpel/src:$PYTHONPATH

python -m pytest tests/integration/test_mcp_telemetry_integration.py -v
```

**Expected: All 6 tests pass ✅**

### 5.2 Run Basic Telemetry Tests

```bash
export PYTHONPATH=/path/to/code-scalpel/src:$PYTHONPATH
python tests/telemetry/test_telemetry_basic.py
```

**Expected: All 5 tests pass ✅**

### 5.3 Run License Tests

```bash
export PYTHONPATH=/path/to/code-scalpel/src:$PYTHONPATH
python tests/telemetry/test_license_upgrade.py
```

**Expected: All 5 tests pass ✅**

## Part 6: Test License Upgrade Flow

### 6.1 Start with Community Tier

```bash
# Force community tier for testing
CODE_SCALPEL_TIER=community python -m code_scalpel.mcp.server
```

Open dashboard: http://localhost:7654

**You should see:**
- Yellow "Community" badge
- "⚠ No valid license" message
- 🚀 "Upgrade Your Tier" section with file upload

### 6.2 Test License Upload (Simulation)

For actual testing, you'd need a valid license.jwt file. To simulate:

```python
# Create a mock license file (for demo only)
import json
import jwt
from pathlib import Path

license_file = Path.home() / ".code-scalpel" / "license" / "license.jwt"
license_file.parent.mkdir(parents=True, exist_ok=True)

# Write a test JWT (not a real license, for testing only)
payload = {
    "tier": "pro",
    "exp": int(__import__('time').time()) + 86400,
}
token = jwt.encode(payload, "test-key", algorithm="HS256")
license_file.write_text(token)

print(f"✓ License written to {license_file}")
```

Restart server - dashboard should now show "Pro" tier.

## Part 7: Debug Telemetry Issues

### Check if Telemetry Module is Loaded

```bash
python -c "
import sys
sys.path.insert(0, 'src')
from code_scalpel import telemetry
print('✓ Telemetry module loaded')
print(f'  Queue size: {len(list(telemetry._EVENT_QUEUE))}')
"
```

### Check if Dashboard is Running

```bash
# Check if port is listening
netstat -tlnp | grep 7654

# Or use Python
import socket
sock = socket.socket()
try:
    sock.connect(('127.0.0.1', 7654))
    print("✓ Dashboard is listening")
finally:
    sock.close()
```

### Check MCP Server Logs

If using Claude Desktop, check logs:
```bash
# macOS
tail -f ~/Library/Logs/Claude/mcp.log

# Linux
tail -f ~/.cache/claude/logs/mcp.log
```

### Enable Debug Output

```bash
SCALPEL_MCP_OUTPUT=debug python -m code_scalpel.mcp.server 2>&1 | grep -E "telemetry|dashboard|DEBUG"
```

## Part 8: Full Integration Test Flow

**Complete end-to-end test:**

```bash
#!/bin/bash
set -e

echo "1. Starting MCP server..."
python -m code_scalpel.mcp.server &
SERVER_PID=$!
sleep 2

echo "2. Checking dashboard..."
curl -s http://localhost:7654 | grep "Code Scalpel" > /dev/null && echo "✓ Dashboard loaded"

echo "3. Running a tool call..."
python << 'EOF'
import asyncio
import sys
sys.path.insert(0, 'src')
from code_scalpel.mcp.tools.analyze import analyze_code
from code_scalpel.mcp.protocol import set_current_tier

set_current_tier("enterprise")
result = asyncio.run(analyze_code(file_path="src/code_scalpel/telemetry.py"))
print(f"✓ Tool completed: {len(result.data.functions)} functions found")
EOF

echo "4. Checking dashboard telemetry..."
curl -s http://localhost:7654/api/events | python -c "
import sys, json
data = json.load(sys.stdin)
print(f\"✓ Total events: {data['stats']['total_events']}\")
if data['events']:
    print(f\"✓ Latest event: {data['events'][0]['tool_name']}\")
"

echo "5. Killing server..."
kill $SERVER_PID

echo ""
echo "✅ All checks passed!"
```

Save as `test_full_flow.sh` and run:
```bash
chmod +x test_full_flow.sh
./test_full_flow.sh
```

## Part 9: Common Issues & Fixes

### Issue: "Module not found" error

**Cause:** Using installed version instead of local src/

**Fix:**
```bash
# Check which version is loaded
python -c "import code_scalpel; print(code_scalpel.__file__)"
# Should show: /path/to/code-scalpel/src/code_scalpel/__init__.py

# If shows site-packages, reinstall in dev mode:
pip uninstall code-scalpel -y
pip install -e ".[dev]"
```

### Issue: Dashboard won't start

**Cause:** Port 7654 already in use

**Check:**
```bash
lsof -i :7654  # See what's using it
```

**Fix:** Dashboard auto-selects next available port. Check server output for actual URL.

### Issue: Telemetry events not appearing

**Cause:** Tool not being called, or wrong path

**Verify:**
1. Tool call is actually happening (check MCP client logs)
2. Dashboard is running (`curl http://localhost:7654`)
3. Local code is being used (check `python -c` test above)

### Issue: "No valid license" always shown

**Cause:** No license file in standard location

**Check:**
```bash
ls -la ~/.code-scalpel/license/
```

**Fix:** For testing, use `-e CODE_SCALPEL_TIER=community` flag.

## Part 10: Testing Checklist

Use this checklist to verify everything works:

```
[ ] Python 3.10+ installed
[ ] pip install -e ".[dev]" successful
[ ] fastapi and websockets installed
[ ] MCP server starts: python -m code_scalpel.mcp.server
[ ] Dashboard accessible: curl http://localhost:7654
[ ] Dashboard API works: curl http://localhost:7654/api/events
[ ] Integration tests pass: pytest tests/integration/...
[ ] Real tool call emits telemetry
[ ] Telemetry appears in dashboard API
[ ] Events visible in browser (http://localhost:7654)
[ ] License panel shows in dashboard
[ ] License API endpoint works: curl http://localhost:7654/api/license
```

## Next Steps

Once local testing is working:

1. **Test with Claude Desktop** - Most realistic scenario
2. **Test with Cursor** - Same MCP protocol
3. **Make code changes** - They'll be reflected immediately
4. **Run integration tests** - Catch any regressions
5. **Iterate** - Dashboard telemetry should show impact

---

**You're now ready to develop and test locally!** 🚀
