# Getting Started with Code Scalpel

Welcome to Code Scalpel v1.0.0 "Autonomy"! This guide covers installation, configuration, and your first analysis.

## What is Code Scalpel?

Code Scalpel is an **MCP server toolkit** for AI agents (Claude, GitHub Copilot, Cursor) to perform surgical code operations. Instead of stuffing entire files into context, Code Scalpel extracts *exactly* what's needed—saving 99% of tokens while improving accuracy.

**Key Capabilities:**
- **22 MCP Tools** for AI agents via Model Context Protocol
- **4 Languages** - Python, TypeScript, JavaScript, Java (all full support)
- **Security Analysis** - 17+ vulnerability types including SQLi, NoSQL, DOM XSS
- **Symbolic Execution** - Z3-powered path exploration and test generation
- **Cross-File Analysis** - Import resolution and taint tracking across modules
- **Unified Graph Engine** - Cross-language dependency tracking with confidence scoring

---

## Quick Start (Recommended)

The fastest way to use Code Scalpel is through your AI assistant with MCP. Choose your editor:

### VS Code / GitHub Copilot (Recommended)

1. Create `.vscode/mcp.json` in your project root:

```json
{
  "servers": {
    "code-scalpel": {
      "type": "stdio",
      "command": "uvx",
      "args": ["code-scalpel", "mcp", "--root", "${workspaceFolder}"]
    }
  }
}
```

2. In VS Code: `Ctrl+Shift+P` → "MCP: List Servers" → Click "Start"
3. Use in Copilot Chat with agent mode (`@workspace`)

**That's it!** Ask Copilot: *"Scan this file for security vulnerabilities"* and it will use Code Scalpel automatically.

### Claude Desktop

1. Find your config file:
   - **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
   - **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
   - **Linux:** `~/.config/Claude/claude_desktop_config.json`

2. Add the server configuration:

```json
{
  "mcpServers": {
    "code-scalpel": {
      "command": "uvx",
      "args": ["code-scalpel", "mcp", "--root", "/path/to/your/project"]
    }
  }
}
```

3. Restart Claude Desktop - look for the hammer icon indicating tools are available

### Cursor IDE

Add to `~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "code-scalpel": {
      "command": "uvx", 
      "args": ["code-scalpel", "mcp", "--root", "/path/to/project"]
    }
  }
}
```

---

## Installation Options

### Option 1: uv (Recommended - Zero Install)

[uv](https://docs.astral.sh/uv/) runs Code Scalpel directly without installation:

```bash
# Install uv (if not installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Run code-scalpel without installing (used in MCP configs above)
uvx codescalpel --help
```

This is the **recommended** approach because:
- No global installation needed
- Always uses the latest version
- Works seamlessly with MCP configs

### Option 2: pip (Traditional)

```bash
pip install codescalpel
```

Then use `python -m code_scalpel.mcp` in your MCP configs instead of `uvx codescalpel mcp`.

### Option 3: Docker (Production/CI)

```bash
# Pull from GitHub Container Registry
docker pull ghcr.io/3D-Tech-Solutions/code-scalpel:3.0.0

# Run HTTP server
docker run -d -p 8593:8593 -p 8594:8594 \
  -v /path/to/project:/project \
  ghcr.io/3D-Tech-Solutions/code-scalpel:3.0.0
```

### Option 4: From Source (Development)

```bash
git clone https://github.com/3D-Tech-Solutions/code-scalpel.git
cd code-scalpel
pip install -e ".[dev]"
```

---

## Additional Server Configuration

### HTTP Transport (Remote/Team Access)

For team-shared servers or remote access:

```bash
# [20260310_DOCS] Use the verified MCP streamable-http transport and /mcp endpoint.
# Start MCP HTTP transport (localhost only)
code-scalpel mcp --transport streamable-http --host 127.0.0.1 --port 8593

# Bind to all interfaces for team use behind a trusted network boundary
code-scalpel mcp --transport streamable-http --host 0.0.0.0 --port 8593

# With specific project root
code-scalpel mcp --transport streamable-http --host 127.0.0.1 --port 8593 --root /path/to/project
```

**Verified MCP Endpoint**:
```bash
curl -i http://localhost:8593/mcp \
  -H "Accept: application/json, text/event-stream"
# Expected without session initialization: HTTP 406 or another MCP negotiation response
```

Current MCP runtime guidance:

- The verified network endpoint is `/mcp` on the configured server port.
- There is no native `/health` endpoint on the MCP runtime contract.
- For container liveness, prefer a TCP port check or an initialized MCP probe managed by your platform.

### Docker Deployment (Production/CI)

```yaml
# docker-compose.yml
version: '3.8'
services:
  code-scalpel:
    image: ghcr.io/3D-Tech-Solutions/code-scalpel:3.0.0
    ports:
      - "8593:8593"
    volumes:
      - ./:/project:ro
    healthcheck:
      test: ["CMD", "python", "-c", "import socket; s = socket.create_connection(('127.0.0.1', 8593), 2); s.close()"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### CI/CD Integration (GitHub Actions)

```yaml
name: Security Scan
on: [push, pull_request]

jobs:
  scan:
    runs-on: ubuntu-latest
    services:
      code-scalpel:
        image: ghcr.io/3D-Tech-Solutions/code-scalpel:3.0.0
        ports:
          - 8593:8593
    steps:
      - uses: actions/checkout@v4
      - name: Wait for MCP port
        run: |
          for i in {1..30}; do
            python - <<'PY'
import socket
try:
    s = socket.create_connection(("127.0.0.1", 8593), 2)
    s.close()
except OSError:
    raise SystemExit(1)
PY
            if [ $? -eq 0 ]; then break; fi
            sleep 1
          done
      - name: Run MCP security scan
        run: |
          curl -X POST http://localhost:8593/mcp \
            -H "Content-Type: application/json" \
            -H "Accept: application/json, text/event-stream" \
            -d '{"method": "tools/call", "params": {"name": "security_scan", "arguments": {"file_path": "src/"}}}'
```

---

## Using Code Scalpel

### Primary: Through Your AI Assistant (Recommended)

Once connected via MCP, simply ask your AI assistant:

> "Analyze the security of my Flask app"

The AI will automatically use Code Scalpel's tools:

```
Security Analysis Results:
- SQL Injection (CWE-89) at line 45
  Taint path: request.args['id'] → user_id → query → cursor.execute()
- Hardcoded Secret (AWS Key) at line 12
  Pattern: AKIA... detected in config.py
```

Other example prompts:
- *"Extract the `calculate_tax` function from utils.py"*
- *"Find all references to the UserService class"*
- *"Generate unit tests for this function"*
- *"Build a call graph starting from main()"*

### Secondary: CLI (Standalone Analysis)

For CI/CD or quick checks without an AI assistant:

```bash
# Security scan
code-scalpel scan app.py

# Analyze code structure
code-scalpel analyze src/ --json

# Start MCP server manually
code-scalpel mcp --transport streamable-http --host 127.0.0.1 --port 8593
```

### Advanced: Python API (Programmatic Use)

For building custom tools on top of Code Scalpel:

```python
from code_scalpel import CodeAnalyzer

analyzer = CodeAnalyzer()

code = """
def calculate_tax(amount, rate=0.1):
    if amount < 0:
        raise ValueError("Amount cannot be negative")
    return amount * rate

def unused_helper():
    pass  # This function is never called

total = calculate_tax(100)
print(total)
"""

result = analyzer.analyze(code)

# View metrics
print(f"Functions: {result.metrics.num_functions}")
print(f"Lines: {result.metrics.lines_of_code}")
print(f"Complexity: {result.metrics.cyclomatic_complexity}")

# Check for dead code
for item in result.dead_code:
    print(f"Dead code: {item.name} - {item.reason}")

# View suggestions
for suggestion in result.refactor_suggestions:
    print(f"Suggestion: {suggestion.description}")
```

### Using CLI

```bash
# Analyze a file
code-scalpel analyze myfile.py

# Output as JSON (for CI/CD)
code-scalpel analyze src/ --json > analysis.json

# Security scan with taint tracking
code-scalpel scan app.py
```

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CODE_SCALPEL_ROOT` | `.` | Default project root for analysis |
| `CODE_SCALPEL_LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `CODE_SCALPEL_CACHE_DIR` | `~/.cache/code-scalpel` | Cache directory for analysis results |
| `CODE_SCALPEL_Z3_TIMEOUT` | `5` | Symbolic execution timeout (seconds) |

---

## Troubleshooting

### Server Won't Start

**Symptom:** `command not found: code-scalpel`

**Solution:** Ensure code-scalpel is installed and in PATH:
```bash
pip install codescalpel
# Or with uv
uvx codescalpel --help
```

### VS Code Can't Find Server

**Symptom:** MCP server shows as "Not Started" in VS Code

**Solutions:**
1. Check `.vscode/mcp.json` syntax (valid JSON)
2. Verify `uvx` or `python` is in PATH
3. Try absolute path: `"command": "/usr/local/bin/uvx"`
4. Check Output → MCP for error messages

### Claude Desktop Not Showing Tools

**Symptom:** No hammer icon in Claude Desktop

**Solutions:**
1. Restart Claude Desktop completely
2. Check config file location (varies by OS)
3. Validate JSON syntax: `cat config.json | python -m json.tool`
4. Check Claude logs: Help → Show Logs

### Docker MCP Listener Check Failing

**Symptom:** Container exits or liveness check fails

**Solutions:**
```bash
# Check container logs
docker logs code-scalpel

# Verify port mapping
docker ps

# Test MCP listener reachability manually
python - <<'PY'
import socket
s = socket.create_connection(("127.0.0.1", 8593), 2)
s.close()
print("MCP listener reachable on 127.0.0.1:8593")
PY
```

### Analysis Timeout

**Symptom:** Analysis hangs on large files

**Solutions:**
1. Increase Z3 timeout: `CODE_SCALPEL_Z3_TIMEOUT=30`
2. Use `AnalysisLevel.BASIC` for faster results
3. Analyze specific files instead of entire directories

---

## Next Steps

- [API Reference](api_reference.md) - Complete API documentation
- [Agent Integration Guide](agent_integration.md) - Deep dive into AI framework integrations
- [MCP Tools Reference](../modules/MCP_SERVER.md) - All 20 tools explained
- [Security Analysis Guide](security_analysis.md) - Vulnerability detection details
- [Examples](examples.md) - Code samples and use cases

---

## Getting Help

- **GitHub Issues:** [Report bugs](https://github.com/3D-Tech-Solutions/code-scalpel/issues)
- **GitHub Discussions:** [Ask questions](https://github.com/3D-Tech-Solutions/code-scalpel/discussions)
- **Release Notes:** [v1.0.0 Changes](release_notes/RELEASE_NOTES_v1.0.0.md)

---

## License

Code Scalpel is released under the MIT License. See [LICENSE](../LICENSE) for details.

"Code Scalpel" is a trademark of 3D Tech Solutions LLC.
