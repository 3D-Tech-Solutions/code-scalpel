# Quick Start: Code Scalpel Dashboard Telemetry

Get the dashboard running in 5 minutes.

## 1. Install Dependencies

```bash
pip install fastapi websockets httpx pytest-asyncio
```

## 2. Run the Demo

See sample telemetry data with the demo:

```bash
python scripts/demo_dashboard_telemetry.py
```

Opens dashboard at: **http://localhost:7654**

You'll see sample events:
- analyze_code (145ms)
- security_scan (234ms)
- extract_code (89ms)
- ... and more

## 3. Run Tests

Verify everything works:

```bash
# Basic telemetry tests
python tests/telemetry/test_telemetry_basic.py

# Integration tests (real tool calls)
python -m pytest tests/integration/test_mcp_telemetry_integration.py -v

# License upgrade tests
python tests/telemetry/test_license_upgrade.py
```

**Expected:** All tests pass ✅

## 4. Start the MCP Server

```bash
python -m code_scalpel.mcp.server
```

Terminal output:
```
Code Scalpel MCP Server v2.1.3
========================================
License Tier: ENTERPRISE
Dashboard: http://localhost:7654
========================================
```

**Dashboard will be running** with telemetry enabled.

## 5. Use the Dashboard

**Open:** http://localhost:7654

You'll see:
- 📊 **Real-time tool calls** - Streams in as tools run
- 📈 **Statistics** - Success rate, avg duration, tool counts
- 🔐 **License status** - Current tier, validation status
- 📤 **Upgrade panel** - (if community tier) Upload license.jwt

## 6. Test with Real Tool Calls

In another terminal, call a tool via MCP:

```bash
# Using Claude Desktop / Cursor / any MCP client
# Ask Claude to "analyze this file" or "scan for security issues"
# Watch telemetry events appear in dashboard in real-time!
```

Or test programmatically:

```python
import asyncio
from code_scalpel.mcp.tools.analyze import analyze_code

# This will emit telemetry automatically
result = asyncio.run(analyze_code(file_path="your_file.py"))

# Check dashboard - event should appear within 1 second!
```

## What You're Looking At

### Event in Dashboard

```
[14:32:01] analyze_code    SUCCESS    145ms   community
├─ Tool name: analyze_code
├─ Status: ✓ SUCCESS
├─ Duration: 145 milliseconds
└─ Tier: community tier
```

### Stats

```
Total Calls: 5
Success Rate: 100%
Avg Duration: 168ms
```

### License Panel (Community Tier)

```
📜 License & Tier
🟡 Community

⚠ No valid license

🚀 Upgrade Your Tier
├─ Click to select or drag license.jwt
└─ Instructions: 5 steps to upgrade
```

## Key Files

| File | Purpose |
|------|---------|
| `src/code_scalpel/telemetry.py` | Event model & queue |
| `src/code_scalpel/dashboard_service.py` | FastAPI + HTML UI |
| `docs/guides/DASHBOARD_TELEMETRY.md` | Full documentation |
| `tests/integration/test_mcp_telemetry_integration.py` | Integration tests |

## Troubleshooting

### Dashboard won't open

Check if port 7654 is in use:
```bash
lsof -i :7654
```

If taken, dashboard auto-selects next available port. Check server output for actual URL.

### Events not appearing

1. Verify tools are being called (check MCP client logs)
2. Check browser console (F12) for JavaScript errors
3. Verify WebSocket connection in DevTools → Network → WS

### No telemetry emitted

Make sure you're using the latest `analyze_code` from `src/` (not installed version):
```bash
python -c "import sys; sys.path.insert(0, 'src'); from code_scalpel.mcp.tools.analyze import analyze_code; print('✓ Correct version loaded')"
```

## What's Next?

- ✅ Dashboard boots with MCP
- ✅ Real telemetry from tools
- ✅ License upgrade UI
- ⏳ JSONL persistence (Phase 1)
- ⏳ More tools with telemetry (Phase 1)
- ⏳ Prometheus/Grafana (Phase 2)

## Questions?

Check: `docs/guides/DASHBOARD_TELEMETRY.md`

Report issues: https://github.com/anthropics/code-scalpel/issues

---

**Ready to go!** 🚀
