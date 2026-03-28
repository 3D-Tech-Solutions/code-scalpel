Dashboard telemetry plan for Code Scalpel

## Goal
Non-intrusive observability for MCP tool calls. Keep AI agent behavior unchanged while tracking tool events and extracted data in a dashboard.

## 1) Telemetry event model
1.1 tool_call event structure:
- tool_name
- tier_applied (community/pro/enterprise)
- request_id, session_id, user_id
- timestamp
- duration_ms
- status (success/failure), error
- input_summary (scrubbed or hashed)
- output_summary (function_count, class_count, vulnerabilities=[], symbol_refs=[], etc)
- metadata (language, file_path, symbol)

1.2 Sweeps:
- For security_scan/cross_file_security_scan: vulnerabilities found details
- For extract_code: extracted symbol name, lines, dependencies
- For analyze_code: node counts by type, language, parse status

## 2) Implementation outline
2.1 Telemetry module
- src/code_scalpel/telemetry.py
  - emit_tool_event(payload)
  - format_event(tool_name, request, response, meta)
  - sink to JSONL and optionally HTTP sink

2.2 Server hook
- in mcp request dispatcher (e.g., src/code_scalpel/mcp/server.py) add post_tool export:
  - response = await tool(...)
  - try: telemetry.emit_tool_event(construct_event(...))
  - except: log and continue
  - return response

2.3 Config
- .code-scalpel/telemetry.toml
  - enabled = true
  - sink = "jsonl" / "http"
  - jsonl_path = "~/.code-scalpel/telemetry.log"
  - http_endpoint = "http://localhost:9000/telemetry"

## 3) Dashboard plan (MVP)
3.1 Data store 1: JSONL
- One event per line
- Use `scripts/telemetry_stats.py` to parse and summarize

3.2 UI: Static page or Grafana
- Recent calls table (latest 30)
- Tool usage histogram
- Average latency per tool/tier
- Success/error ratio
- Top symbols extracted, top vulnerabilities discovered

3.3 Next step: Live view with basic WebSocket
- Optional enrichment: route to Prometheus+Grafana or small Node/Flask dashboard

## 4) First tool call to validate (community tier)
4.1 test payload for analyze_code
- sample.py with one function + one class

4.2 call path
- `tool_name = "analyze_code"`
- `tier_applied = "community"`
- input_summary: file_count=1, file_path=sample.py
- output_summary: functions=1, classes=1, language=python
- duration_ms from tool internal timer

4.3 verification
- event appears in telemetry file and dashboard
- metrics update: analyze_code +1, duration non-zero
- no exception on telemetry sink failure

## 5) Test case
- add tests in `tests/tools/test_telemetry.py`
- assert the telemetry event schema matches expected values
- assert telemetry emits and does not break tool behavior

## 6) Follow-up
- Include permissions/AUDIT: BOTTOM-LINE that this is only for visibility, not changing tool logic
- Add query convenience for `extract_code` output (symbol + ref list)
- Add dashboard wizard `docs/guides/telemetry.md` for enabling and reading
