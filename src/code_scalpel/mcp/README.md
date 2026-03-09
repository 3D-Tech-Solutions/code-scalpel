# MCP Server

**Model Context Protocol implementation for AI agent integration**

---

## Overview

This directory contains Code Scalpel's **MCP server implementation**. It provides:

- **Tool Registration** - Expose Code Scalpel capabilities as MCP tools
- **Protocol Implementation** - Standardized communication with AI agents
- **Tool Discovery** - Agent discovery and capability broadcasting
- **Request Handling** - Process and respond to tool calls
- **Result Marshaling** - Convert internal results to MCP format

---

## Core Module (1)

| Module | Purpose | Key Classes | Status |
|--------|---------|------------|--------|
| **server.py** | MCP protocol server (~800 lines) | `MCPServer`, `ToolRegistry` | ✅ Stable |

---

## Available Tools (19 Stable + 4 Experimental)

### Code Extraction & Analysis (5)
- Graph-oriented tools remain Python-first overall, with initial local
    JavaScript/TypeScript parity in `get_call_graph`, `get_graph_neighborhood`,
    and `get_cross_file_dependencies`. JS/TS method-node neighborhoods currently
    rely on advanced resolution.
- `extract_code` - Surgical symbol extraction with dependencies
- `analyze_code` - Parse and extract code structure
- `get_file_context` - Quick file overview
- `get_symbol_references` - Find all symbol usages
- `get_cross_file_dependencies` - Analyze Python-first import/dependency chains with an initial local JS/TS graph-backed slice

### Project Analysis (4)
- `get_call_graph` - Build and trace Python-first function calls with initial JS/TS parity
- `get_project_map` - Generate project structure map
- `get_graph_neighborhood` - Extract Python-first k-hop subgraph with initial JS/TS function parity and JS/TS method neighborhoods via advanced resolution
- `crawl_project` - Project-wide analysis

### Security (5)
- `security_scan` - Taint-based vulnerability detection
- `cross_file_security_scan` - Multi-file vulnerability tracking
- `scan_dependencies` - OSV database vulnerability check
- `unified_sink_detect` - Polyglot sink detection
- `type_evaporation_scan` - Type system boundary vulnerabilities

### Refactoring & Verification (3)
- `simulate_refactor` - Verify code changes safely
- `update_symbol` - Apply safe symbol replacements
- `generate_unit_tests` - Symbolic execution test generation

### Advanced Analysis (2)
- `symbolic_execute` - Explore execution paths
- `validate_paths` - Check path accessibility

---

## Usage

### With Claude/Copilot/Cursor

```python
# Start MCP server
mcp_server = MCPServer()
mcp_server.start()

# Claude connects via MCP protocol
# Claude calls tools: extract_code, security_scan, etc.
# Server returns results
```

### Direct Python Usage

```python
from code_scalpel.mcp.server import MCPServer

server = MCPServer()
tool = server.get_tool("security_scan")
result = tool.execute(file_path="src/app.py")
```

### Tool Registration

```python
from code_scalpel.mcp.server import MCPServer

server = MCPServer()

# Register custom tool
server.register_tool(
    name="my_custom_tool",
    description="Custom analysis tool",
    handler=my_handler_function,
    input_schema={...}
)
```

---

## Tool Categories

### 🔍 Discovery & Analysis
Used to understand code structure before modifications:
- `get_file_context` - Get file overview
- `analyze_code` - Parse structure
- `get_symbol_references` - Find usages
- `get_call_graph` - Trace calls
- `get_project_map` - Overall structure

### 🔧 Extraction & Modification
Safely extract and modify code:
- `extract_code` - Get code with dependencies
- `get_cross_file_dependencies` - Analyze imports
- `simulate_refactor` - Test changes
- `update_symbol` - Apply safely
- `generate_unit_tests` - Create tests

### 🔐 Security
Scan for vulnerabilities:
- `security_scan` - Find issues in file
- `cross_file_security_scan` - Multi-file scan
- `scan_dependencies` - Check CVEs
- `unified_sink_detect` - Find dangerous sinks

### 📊 Advanced
Specialized analysis:
- `symbolic_execute` - Path exploration
- `get_graph_neighborhood` - Subgraph extraction
- `crawl_project` - Full project analysis
- `validate_paths` - Path checking

---

## Tool Invocation Pattern

All tools follow this pattern:

```python
# 1. Agent discovers tool
tool = server.get_tool("extract_code")

# 2. Agent calls with parameters
result = tool.execute(
    file_path="src/handlers.py",
    target_type="function",
    target_name="process_request"
)

# 3. Server returns structured result
# {
#     "code": "def process_request(...): ...",
#     "dependencies": [...],
#     "metadata": {...}
# }
```

---

## Configuration

```python
from code_scalpel.mcp.server import MCPServer

server = MCPServer(
    host="127.0.0.1",              # Listen address
    port=5000,                      # Listen port
    enable_caching=True,            # Cache results
    cache_ttl=3600,                 # Cache duration (seconds)
    max_workers=4,                  # Parallel execution
    timeout_seconds=300,            # Tool timeout
    enable_telemetry=True,          # Log usage
    log_level="INFO"                # Log verbosity
)
```

---

## Integration Points

### With Agents

MCP server is used by agents to perform analysis:

```
Agent.execute_ooda_loop()
    ↓
Agent calls MCP tools
    ├─ observe_file() → get_file_context()
    ├─ find_usages() → get_symbol_references()
    ├─ analyze_security() → security_scan()
    └─ test_change() → simulate_refactor()
    ↓
Agent makes decisions
```

### With External Frameworks

Integrations expose MCP tools in external frameworks:

```
Claude/Copilot
    ↓ (MCP Protocol)
MCPServer
    ↓
Code Scalpel Tools
    ↓
Real Code Analysis
```

---

## Tool Result Format

All tool results follow this structure:

```python
{
    "success": bool,                # Tool succeeded
    "status": str,                  # Tool status
    "result": dict,                 # Tool-specific result
    "metadata": {
        "execution_time_ms": int,   # How long tool took
        "cached": bool,             # Was result cached
        "warnings": list,           # Warnings
        "errors": list              # Errors if failed
    }
}
```

---

## File Structure

```
mcp/
├── README.md                [This file]
├── __init__.py              [Exports]
└── server.py                [MCP protocol server]
```

---

## Data Flow

### MCP Tool Request Processing
```
AI Agent / Claude / Copilot
    ↓
MCP Client
    ├─ Tool discovery (list_tools)
    ├─ Get schema (describe_tool)
    └─ Call tool (call_tool)
    ↓
MCP Server
    ├─ Validate request
    ├─ Check permissions (policies)
    ├─ Route to handler
    └─ Invoke Code Scalpel module
    ↓
Code Scalpel Modules
    ├─ AST Tools (ast_tools/)
    ├─ Security (security/)
    ├─ Code Parser (code_parser/)
    ├─ Autonomy (autonomy/)
    └─ Agents (agents/)
    ↓
Analysis Results
    ↓
Result Marshaling
    ├─ Convert to JSON
    ├─ Attach context
    └─ Format for MCP
    ↓
MCP Response
    ↓
AI Agent (receives results)
```

### Tool Discovery & Registration
```
Server Startup
    ↓
MCPServer.__init__()
    ├─ Register security tools
    ├─ Register analysis tools
    ├─ Register extraction tools
    ├─ Register refactoring tools
    ├─ Register testing tools
    └─ Register autonomy tools
    ↓
Tool Registry Built
    ├─ 19 stable tools
    ├─ 4 experimental tools
    └─ Tool schemas & docs
    ↓
AI Agent Requests Tool Discovery
    ↓
Server Responds with Capabilities
    ├─ Available tools
    ├─ Tool schemas (inputs/outputs)
    ├─ Tool descriptions
    └─ Usage examples
```

---

## Debugging Tools

```python
# Get all available tools
tools = server.list_tools()

# Check tool schema
schema = server.get_tool_schema("security_scan")

# Get tool statistics
stats = server.get_statistics()
print(f"Total calls: {stats['total_calls']}")
print(f"Cache hit rate: {stats['cache_hit_rate']}")
```

---

## Development Roadmap

### Phase 1: Tool Expansion (In Progress 🔄)

#### New Analysis Tools (8 TODOs)
- [ ] Variable tracking & dependency analysis
- [ ] Memory usage profiler
- [ ] Thread safety analyzer
- [ ] API surface analyzer
- [ ] Documentation coverage analyzer
- [ ] Test mutation analyzer
- [ ] Configuration validator
- [ ] Performance bottleneck detector

#### Tool Enhancements (10 TODOs)
- [ ] Caching layer for repeated calls
- [ ] Result streaming support
- [ ] Progress reporting
- [ ] Cancellation support
- [ ] Timeout handling
- [ ] Batch processing
- [ ] Incremental analysis
- [ ] Result filtering
- [ ] Evidence attachment
- [ ] Confidence scoring

#### Protocol Improvements (8 TODOs)
- [ ] Tool chaining/piping
- [ ] Result post-processing
- [ ] Error recovery
- [ ] Partial result handling
- [ ] Webhook notifications
- [ ] Event streaming
- [ ] Subscription support
- [ ] Rate limiting per tool

### Phase 2: Advanced Features (Planned)

#### Intelligent Orchestration (12 TODOs)
- [ ] Automatic tool selection
- [ ] Chain multiple tools
- [ ] Cross-tool result sharing
- [ ] Conflict resolution
- [ ] Recommendation ranking
- [ ] Result deduplication
- [ ] Evidence combination
- [ ] Confidence aggregation
- [ ] Multi-agent coordination
- [ ] Feedback loops
- [ ] Learning from corrections
- [ ] Auto-tuning parameters

#### Integration Expansion (9 TODOs)
- [ ] IDE plugin support (VS Code, IntelliJ)
- [ ] Git hooks integration
- [ ] CI/CD pipeline integration
- [ ] Chat interface (Slack, Discord)
- [ ] Web UI dashboard
- [ ] REST API gateway
- [ ] GraphQL endpoint
- [ ] WebSocket support
- [ ] Webhook system

#### Monitoring & Analytics (10 TODOs)
- [ ] Tool usage analytics
- [ ] Performance metrics
- [ ] Cache hit rates
- [ ] Error tracking
- [ ] Latency monitoring
- [ ] Cost tracking (API usage)
- [ ] User analytics
- [ ] Quality metrics
- [ ] Trend analysis
- [ ] SLA monitoring

### Phase 3: Enterprise Features (Future)

#### Security & Governance (11 TODOs)
- [ ] Multi-tenant isolation
- [ ] Fine-grained permissions
- [ ] API key management
- [ ] Rate limiting
- [ ] Request signing
- [ ] Audit logging
- [ ] Compliance reporting
- [ ] Data retention policies
- [ ] Encryption at rest
- [ ] Encryption in transit
- [ ] Security scanning of tools

#### Scalability (9 TODOs)
- [ ] Distributed tool execution
- [ ] Load balancing
- [ ] Result caching strategies
- [ ] Database persistence
- [ ] Queue-based processing
- [ ] Horizontal scaling
- [ ] Worker pool management
- [ ] Failure recovery
- [ ] Health checking

---

**Last Updated:** December 21, 2025  
**Version:** v3.0.0  
**Status:** 19 Tools Stable ✅ + 4 Experimental 🧪 (Total TODOs: 77)
