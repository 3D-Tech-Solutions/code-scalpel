# AI Agent Integration Guide

This guide covers how to integrate Code Scalpel with AI agents and coding assistants.

## Overview

Code Scalpel is designed for AI-driven code analysis. It provides:

- **MCP Server**: Model Context Protocol for Claude, Copilot, Cursor
- **Surgical Tools**: Token-efficient extraction and modification
- **Structured Output**: Pydantic models optimized for LLM consumption
- **20 MCP Tools**: Complete toolkit for code analysis, security, and modification

## Quick Reference: All 20 MCP Tools

| Tool | Category | Purpose |
|------|----------|---------|
| `analyze_code` | Analysis | Parse code structure (functions, classes, imports) |
| `extract_code` | Extraction | Surgically extract functions/classes/methods |
| `update_symbol` | Modification | Safely replace code symbols with backup |
| `get_file_context` | Context | Get file overview without full content |
| `get_symbol_references` | Context | Find all usages of a symbol |
| `get_project_map` | Discovery | Comprehensive project structure map |
| `get_cross_file_dependencies` | Discovery | Resolve import chains with confidence scores |
| `get_call_graph` | Discovery | Function call relationships |
| `get_graph_neighborhood` | Discovery | K-hop subgraph around any node |
| `crawl_project` | Discovery | Analyze all files in project |
| `security_scan` | Security | Taint-based vulnerability detection |
| `unified_sink_detect` | Security | Polyglot sink detection with confidence |
| `type_evaporation_scan` | Security | Detect cross-file type evaporation vulnerabilities (TS ↔ Python) |
| `cross_file_security_scan` | Security | Track taint across module boundaries |
| `scan_dependencies` | Security | Check dependencies against OSV database |
| `verify_policy_integrity` | Security | Cryptographic policy verification |
| `symbolic_execute` | Testing | Path exploration with Z3 solver |
| `generate_unit_tests` | Testing | Auto-generate tests from symbolic execution |
| `simulate_refactor` | Safety | Preview refactoring before applying |
| `validate_paths` | Utility | Validate paths for Docker deployments |

## MCP Server Integration

### Claude Desktop

Add to `claude_desktop_config.json` (usually at `~/.config/claude/`):

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

Restart Claude Desktop. You'll see Code Scalpel tools in the tools menu.

### VS Code with Copilot / Cursor

Create `.vscode/mcp.json` in your workspace:

```json
{
  "servers": {
    "code-scalpel": {
      "command": "uvx",
      "args": ["code-scalpel", "mcp", "--root", "${workspaceFolder}"]
    }
  }
}
```

> **Note for GitHub Copilot Agent users:** <!-- [20251218_DOCS] Added Copilot activation tool note -->
> Copilot may group MCP tools into activation categories (e.g., `activate_code_analysis_and_testing_tools`, 
> `activate_project_structure_and_security_analysis_tools`). If a tool returns "disabled by user" error,
> try calling the relevant activation tool first. This is Copilot's internal tool management behavior 
> to optimize context size, not a Code Scalpel limitation. Other MCP clients (Claude Desktop, Cursor, 
> Cline) expose all 20 tools directly without activation.

### Docker / Network Deployment

For team or remote deployment:

```bash
# Start HTTP server with SSE (port 8593) and health endpoint (port 8594)
docker run -p 8593:8593 -p 8594:8594 -v /path/to/project:/app/code code-scalpel:3.0.0

# Or directly
code-scalpel mcp --http --port 8593 --allow-lan
```

**Health Check (v2.0.0+)**:
```bash
# Verify container is healthy
curl http://localhost:8594/health
# {"status": "healthy", "version": "3.0.0", "timestamp": "2025-12-18T12:00:00Z"}
```

**Docker Compose** (recommended for production):
```yaml
services:
  code-scalpel:
    image: code-scalpel:3.0.0
    ports:
      - "8593:8593"  # SSE endpoint
      - "8594:8594"  # Health endpoint
    volumes:
      - ./:/app/code
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8594/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

## Available Tools

### 1. `extract_code` - Surgical Extraction

**Purpose**: Extract specific code elements without sending entire files.

**Token Savings**: Instead of sending a 5000-line file (~50k tokens), send only the function you need (~200 tokens). **Validated: 99% token reduction.**

**Multi-Language Support (v2.0.0+)**: Works identically across Python, TypeScript, JavaScript, and Java.

```python
# Python extraction
result = extract_code(
    file_path="/project/src/billing/calculator.py",
    target_type="function",
    target_name="calculate_tax",
    include_cross_file_deps=True  # Also gets TaxRate from models.py
)

# TypeScript extraction (NEW v2.0.0)
result = extract_code(
    file_path="/project/src/services/UserService.ts",
    target_type="class",
    target_name="UserService"
)

# JavaScript extraction (NEW v2.0.0)
result = extract_code(
    file_path="/project/src/api/handler.js",
    target_type="function",
    target_name="handleRequest"
)

# Java extraction (NEW v2.0.0)
result = extract_code(
    file_path="/project/src/main/java/AuthController.java",
    target_type="method",
    target_name="AuthController.authenticate"
)

# Agent receives:
# - target_code: The function (~50 lines)
# - context_code: External dependencies
# - token_estimate: ~150 tokens instead of 50,000
```

**Parameters**:
- `file_path`: Path to source file (server reads it - 0 tokens to agent)
- `target_type`: "function", "class", or "method"
- `target_name`: Name of the element (use "ClassName.method" for methods)
- `include_cross_file_deps`: Resolve imports from external files
- `include_context`: Include intra-file dependencies
- `context_depth`: How deep to traverse (1=direct, 2=transitive)

### 2. `update_symbol` - Surgical Modification

**Purpose**: Replace a function/class/method without rewriting entire file.

**Safety Features**:
- Automatic backup creation
- Syntax validation before write
- Preserves surrounding code exactly

```python
# Example: Agent refactored calculate_tax, now wants to update it
result = update_symbol(
    file_path="/project/src/billing/calculator.py",
    target_type="function",
    target_name="calculate_tax",
    new_code="""def calculate_tax(amount: float, rate: float = 0.1) -> float:
    \"\"\"Calculate tax with configurable rate.\"\"\"
    return round(amount * rate, 2)
""",
    create_backup=True
)

# Result:
# - success: true
# - backup_path: /project/src/billing/calculator.py.bak
# - lines_delta: -3 (new code is 3 lines shorter)
```

### 3. `crawl_project` - Project Discovery

**Purpose**: Understand project structure before making changes.

```python
result = crawl_project(
    root_path="/project",
    include_patterns=["*.py"],
    exclude_patterns=["**/test_*", "**/__pycache__/**"],
    include_analysis=True  # Adds function/class counts
)

# Returns tree structure with analysis metadata
```

### 4. `analyze_code` - Deep Analysis

**Purpose**: Get comprehensive code metrics and structure.

```python
result = analyze_code(
    code="def hello(): return 42"  # Or use file_path
)

# Returns metrics, dependencies, call graph
```

### 5. `security_scan` - Vulnerability Detection

**Purpose**: Find security issues via taint analysis.

```python
result = security_scan(
    code=suspicious_code
)

# Returns: SQL injection, XSS, command injection paths
```

### 6. `symbolic_execute` - Path Exploration

**Purpose**: Find all possible execution paths with Z3.

```python
result = symbolic_execute(
    code=complex_function,
    max_depth=50
)

# Returns: All reachable paths with concrete inputs
```

### 7. `generate_unit_tests` - Test Generation

**Purpose**: Create tests that cover all branches.

```python
result = generate_unit_tests(
    code=function_code,
    framework="pytest"
)

# Returns: Complete test file with branch coverage
```

### 8. `simulate_refactor` - Safe Refactoring

**Purpose**: Preview refactoring before applying.

```python
result = simulate_refactor(
    code=original_code,
    refactor_type="rename_variable",
    old_name="x",
    new_name="counter"
)

# Returns: Refactored code + validation results
```

### 9. `get_file_context` - Quick File Overview

**Purpose**: Understand file structure without reading full content.

```python
result = get_file_context(
    file_path="src/services/user_service.py"
)

# Returns:
# - functions: ["get_user", "create_user", "delete_user"]
# - classes: ["UserService", "UserValidator"]
# - imports: ["flask", "sqlalchemy", "models.User"]
# - complexity_score: 15
# - has_security_issues: False
```

### 10. `get_symbol_references` - Find All Usages

**Purpose**: Know all places a function/class is used before modifying.

```python
result = get_symbol_references(
    symbol_name="calculate_tax",
    project_root="/project"
)

# Returns:
# - definition_file: "src/billing/calculator.py"
# - definition_line: 42
# - references: [
#     {"file": "src/api/routes.py", "line": 87, "context": "tax = calculate_tax(amount)"},
#     {"file": "tests/test_calculator.py", "line": 15, "context": "assert calculate_tax(100) == 20"}
#   ]
# - total_references: 15
```

### 11. `get_project_map` - Project Structure Overview

**Purpose**: Get comprehensive project map before making changes.

```python
result = get_project_map(
    project_root="/project",
    include_complexity=True,
    complexity_threshold=10,
    include_circular_check=True
)

# Returns:
# - packages: ["src", "src.models", "src.services", "tests"]
# - modules: [{"path": "src/main.py", "functions": 3, "classes": 1}]
# - entry_points: ["main", "cli.run", "app.create_app"]
# - complexity_hotspots: ["src/legacy/parser.py:parse_xml (complexity: 25)"]
# - circular_imports: [["models.user", "services.auth"]]
# - mermaid: "graph TD; ..."
```

### 12. `get_cross_file_dependencies` - Import Resolution

**Purpose**: Get all code needed to understand a function, including imports.

**v2.5.0 Feature**: Confidence decay for deep dependency chains.

```python
result = get_cross_file_dependencies(
    target_file="services/order.py",
    target_symbol="process_order",
    max_depth=5,
    confidence_decay_factor=0.9  # Each level loses 10% confidence
)

# Returns:
# - extracted_symbols: [
#     {"name": "process_order", "depth": 0, "confidence": 1.0},
#     {"name": "OrderValidator", "depth": 1, "confidence": 0.9, "file": "validators.py"},
#     {"name": "send_notification", "depth": 2, "confidence": 0.81, "file": "notifications.py"},
#     {"name": "EmailTemplate", "depth": 3, "confidence": 0.73, "low_confidence": True}
#   ]
# - combined_code: "# All symbols concatenated for analysis"
# - low_confidence_count: 1
# - low_confidence_warning: "1 symbol(s) have confidence < 0.5"
# - mermaid: "graph TD; process_order --> OrderValidator; ..."
```

### 13. `get_call_graph` - Function Relationships

**Purpose**: Understand how functions call each other.

```python
result = get_call_graph(
    project_root="/project",
    entry_point="main",  # Start from main function
    depth=10,
    include_circular_import_check=True
)

# Returns:
# - nodes: [{"name": "main", "file": "app.py", "line": 10, "is_entry_point": True}]
# - edges: [{"caller": "app.py:main", "callee": "handlers.py:handle_request"}]
# - circular_imports: []
# - mermaid: "graph TD; main --> handle_request; ..."
```

### 14. `get_graph_neighborhood` - Focused Subgraph

**Purpose**: Extract k-hop neighborhood around a node (prevents graph explosion).

```python
result = get_graph_neighborhood(
    center_node_id="python::services::function::process_order",
    k=2,                    # 2 hops from center
    max_nodes=50,           # Prevent memory issues
    direction="both",       # incoming + outgoing
    min_confidence=0.5      # Filter low-confidence edges
)

# Returns:
# - nodes: [{"id": "...", "depth": 0}, {"id": "...", "depth": 1}]
# - edges: [{"from_id": "...", "to_id": "...", "confidence": 0.9}]
# - truncated: False
# - truncation_warning: null  # Or "Graph exceeded 50 nodes, truncated"
# - mermaid: "graph TD; ..."
```

**Node ID Format**: `{language}::{module}::{type}::{name}`
- Example: `python::services.order::function::process_order`

### 15. `scan_dependencies` - Vulnerability Checking

**Purpose**: Check project dependencies for known CVEs.

```python
result = scan_dependencies(
    project_root="/project",
    include_dev=False,
    scan_vulnerabilities=True
)

# Returns:
# - total_dependencies: 45
# - vulnerable_count: 2
# - total_vulnerabilities: 3
# - severity_summary: {"CRITICAL": 1, "HIGH": 1, "MEDIUM": 1}
# - dependencies: [
#     {"name": "flask", "version": "2.0.0", "vulnerabilities": [
#         {"id": "CVE-2023-30861", "severity": "HIGH", "fixed_version": "2.3.2"}
#     ]}
#   ]
```

### 16. `cross_file_security_scan` - Taint Flow Analysis

**Purpose**: Track tainted data across module boundaries.

```python
result = cross_file_security_scan(
    project_root="/project",
    entry_points=["routes.py:user_route"],
    max_depth=5,
    include_diagram=True
)

# Returns:
# - vulnerabilities: [
#     {"type": "SQL Injection", "cwe": "CWE-89", "severity": "critical",
#      "source_file": "routes.py", "sink_file": "db.py",
#      "flow": "routes.py:user_route -> db.py:get_user"}
#   ]
# - taint_flows: [{"source": "request.args", "sink": "cursor.execute", "path": [...]}]
# - mermaid: "graph LR; request.args --> user_id --> query --> execute"
```

### 17. `unified_sink_detect` - Polyglot Detection

**Purpose**: Detect security sinks across languages with confidence scores.

```python
result = unified_sink_detect(
    code=java_code,
    language="java",        # python, java, javascript, typescript
    min_confidence=0.8
)

# Returns:
# - sink_count: 3
# - sinks: [
#     {"pattern": "executeQuery", "sink_type": "SQL_SINK", "confidence": 0.95,
#      "line": 42, "vulnerability_type": "sql_injection", "owasp_category": "A03:2021"}
#   ]
# - coverage_summary: {"total_patterns": 150, "by_language": {"java": 45, "python": 55}}
```

### 18. `verify_policy_integrity` - Policy Verification

**Purpose**: Verify policy files haven't been tampered with.

```python
result = verify_policy_integrity(
    policy_dir=".code-scalpel",
    manifest_source="file"  # "git", "env", or "file"
)

# Returns:
# - success: True/False
# - files_verified: 5
# - error: "SECURITY: Manifest signature invalid" (if tampered)
```

**FAIL CLOSED**: Any error results in security failure.

### 19. `validate_paths` - Docker Path Validation

**Purpose**: Check if paths are accessible before file operations.

```python
result = validate_paths(
    paths=["/app/src/main.py", "/app/tests/"],
    project_root="/app"
)

# Returns:
# - success: True/False
# - accessible: ["/app/src/main.py"]
# - inaccessible: ["/app/tests/"]
# - suggestions: ["Mount volume: -v $(pwd)/tests:/app/tests"]
# - is_docker: True
```

## Token Optimization Strategy

### The Problem

Traditional LLM coding:
```
Agent: "Read file X" → 10,000 tokens
Agent: "Read file Y" → 8,000 tokens
Agent: "Find function Z in X" → reasoning
Agent: "Modify function Z" → send all 10,000 tokens back
TOTAL: ~28,000 tokens
```

### The Scalpel Solution

```
Agent: extract_code(file_path="X", target_name="Z", include_cross_file_deps=True)
Server: Reads X (0 tokens), finds Z, resolves deps from Y
Agent receives: ~200 tokens (just Z + deps)

Agent: "Modify function Z" → reasoning on 200 tokens

Agent: update_symbol(file_path="X", target_name="Z", new_code=modified)
Server: Locates Z, validates, writes
Agent receives: ~50 tokens (success confirmation)

TOTAL: ~500 tokens (56x reduction)
```

## Workflow Examples

### Refactoring a Function

```python
# 1. Agent asks for the function
extract_result = extract_code(
    file_path="src/utils.py",
    target_type="function",
    target_name="calculate_total",
    include_cross_file_deps=True
)

# 2. Agent reasons about the code (only ~200 tokens of context)
# "I see calculate_total uses TaxRate from models.py..."

# 3. Agent generates new code
new_code = """def calculate_total(items, tax_rate=None):
    ...
"""

# 4. Agent applies the change
update_result = update_symbol(
    file_path="src/utils.py",
    target_type="function",
    target_name="calculate_total",
    new_code=new_code
)
```

### Security Audit

```python
# 1. Crawl project
project = crawl_project(root_path="/app", include_patterns=["*.py"])

# 2. Scan each file
for file in project.files:
    scan = security_scan(file_path=file.path)
    if scan.vulnerabilities:
        # Extract the vulnerable function for closer inspection
        for vuln in scan.vulnerabilities:
            code = extract_code(
                file_path=file.path,
                target_type="function",
                target_name=vuln.function_name
            )
```

## Best Practices

1. **Use `file_path` over `code`**: Let the server read files (0 tokens to agent)

2. **Enable cross-file deps**: Get complete context without multiple reads

3. **Use `crawl_project` first**: Understand structure before diving in

4. **Create backups**: Always set `create_backup=True` on `update_symbol`

5. **Validate after update**: Run tests or `analyze_code` after modifications

## Troubleshooting

### "File not found"
- Check the file path is absolute or relative to `--root`
- Verify the MCP server has access to the workspace

### "Function not found"
- Check the exact function name (case-sensitive)
- For methods, use "ClassName.method_name" format
- Use `crawl_project` to discover available symbols

### "Cross-file deps not resolving"
- Ensure `file_path` is set (not `code`)
- Check that import paths are resolvable relative to the file
- Increase `context_depth` for transitive dependencies

## Framework-Specific Integration

### Autogen

```python
from autogen import AssistantAgent
from code_scalpel.integrations import AutogenScalpel

agent = AssistantAgent(
    name="CodeAnalyst",
    llm_config={"model": "gpt-4"},
)

# Add Code Scalpel tools
scalpel = AutogenScalpel()
agent.register_function(scalpel.analyze_code)
agent.register_function(scalpel.extract_code)
```

### CrewAI

```python
from crewai import Agent, Task, Crew
from code_scalpel.integrations import CrewAIScalpel

scalpel_tools = CrewAIScalpel()

analyst = Agent(
    role="Code Analyst",
    tools=[scalpel_tools.analyze, scalpel_tools.extract],
)
```

### LangChain

```python
from langchain.agents import initialize_agent
from code_scalpel.integrations import LangChainScalpel

tools = LangChainScalpel().get_tools()
agent = initialize_agent(tools, llm, agent="zero-shot-react-description")
```
