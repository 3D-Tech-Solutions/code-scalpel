<!-- [20251215_DOCS] Architecture: MCP Integration Patterns -->

# MCP Integration Patterns

This document describes patterns for integrating Code Scalpel with MCP clients (Claude, Copilot, etc.).

---

## MCP Server Overview

Code Scalpel exposes its functionality through the Model Context Protocol (MCP):

```python
from mcp.server import Server
from mcp.types import Tool

server = Server("code-scalpel")

@server.tool()
async def extract_code(
    file_path: str,
    target_type: str,
    target_name: str,
    include_context: bool = False
) -> dict:
    """Extract a function, class, or method by name."""
    ...
```

---

## Tool Categories

### 1. Extraction Tools (Read)

| Tool | Purpose | Token Efficiency |
|------|---------|------------------|
| `extract_code` | Extract function/class/method | Very High |
| `get_file_context` | Get file overview without code | Very High |
| `get_symbol_references` | Find all uses of a symbol | High |
| `get_call_graph` | Trace function call relationships | Medium |

### 2. Analysis Tools (Read)

| Tool | Purpose | Token Efficiency |
|------|---------|------------------|
| `analyze_code` | Parse and extract structure | High |
| `security_scan` | Detect vulnerabilities | High |
| `symbolic_execute` | Explore execution paths | Medium |
| `scan_dependencies` | Check for vulnerable packages | High |

### 3. Modification Tools (Write)

| Tool | Purpose | Safety |
|------|---------|--------|
| `update_symbol` | Replace function/class/method | Backup + Validation |
| `simulate_refactor` | Verify change is safe | No modification |

---

## Integration Patterns

### Pattern 1: Code Review Workflow

```
1. Agent receives code review request
2. get_file_context(file_path) → Overview
3. For each function with high complexity:
   a. extract_code(target_name=func) → Code
   b. security_scan(code) → Vulnerabilities
4. Compile findings and suggest fixes
```

### Pattern 2: Bug Fix Workflow

```
1. Agent receives bug report mentioning function
2. get_symbol_references(symbol_name) → All usages
3. extract_code(target_name=func, include_cross_file_deps=True) → Full context
4. Analyze and propose fix
5. simulate_refactor(original, proposed) → Verify safety
6. update_symbol(target_name, new_code) → Apply fix
```

### Pattern 3: Security Audit Workflow

```
1. Agent receives security audit request
2. crawl_project(root_path) → Project overview
3. cross_file_security_scan(project_root) → Cross-file vulns
4. For each vulnerability:
   a. extract_code(file_path, sink_function) → Context
   b. Propose remediation
5. Generate security report
```

### Pattern 4: Test Generation Workflow

```
1. Agent receives test generation request
2. extract_code(target_name=func) → Function code
3. generate_unit_tests(code) → Test cases
4. Return generated tests to user
```

---

## Client Configuration

### Claude Desktop

```json
{
  "mcpServers": {
    "code-scalpel": {
      "command": "python",
      "args": ["-m", "code_scalpel.mcp.server"],
      "env": {
        "PYTHONPATH": "/path/to/project"
      }
    }
  }
}
```

### VS Code (via Extension)

```json
{
  "mcp.servers": {
    "code-scalpel": {
      "type": "stdio",
      "command": "code-scalpel-mcp"
    }
  }
}
```

### Docker Deployment

```yaml
services:
  code-scalpel:
    image: code-scalpel:latest
    volumes:
      - ./workspace:/workspace
    environment:
      - PROJECT_ROOT=/workspace
```

---

## Error Handling Patterns

### Graceful Degradation

```python
@server.tool()
async def extract_code(file_path: str, target_name: str) -> dict:
    try:
        result = extractor.get_function(target_name)
        return {"success": True, "code": result.code}
    except FunctionNotFound:
        available = extractor.list_functions()
        return {
            "success": False,
            "error": f"Function '{target_name}' not found",
            "available_functions": available[:10]  # Suggest alternatives
        }
    except ParseError as e:
        return {
            "success": False,
            "error": f"Parse error: {e}",
            "suggestion": "Check file syntax"
        }
```

### Actionable Error Messages

```json
{
  "success": false,
  "error": "File not found: /path/to/file.py",
  "suggestion": "Available files: ['utils.py', 'main.py']"
}
```

---

## Performance Optimization

### 1. Caching

Results are cached by content hash:
```python
cache_key = f"{file_hash}:{target_name}:{options_hash}"
```

### 2. Lazy Loading

Cross-file dependencies loaded only when requested:
```python
extract_code(..., include_cross_file_deps=False)  # Fast
extract_code(..., include_cross_file_deps=True)   # Comprehensive
```

### 3. Batch Operations

```python
# Future: batch extraction
extract_code_batch([
    {"file_path": "a.py", "target_name": "func1"},
    {"file_path": "b.py", "target_name": "func2"}
])
```

---

## Security Considerations

### 1. Path Validation

All file paths are validated against workspace root:
```python
def validate_path(path: str) -> Path:
    resolved = Path(path).resolve()
    if not resolved.is_relative_to(WORKSPACE_ROOT):
        raise SecurityError("Path outside workspace")
    return resolved
```

### 2. Code Execution Prevention

Code is analyzed statically; never executed:
```python
# Safe: Parse and analyze
ast.parse(code)

# Never: Execute user code
exec(code)  # NEVER DONE
```

### 3. Resource Limits

```python
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
MAX_ANALYSIS_TIME = 60  # seconds
MAX_PATHS = 100  # symbolic execution
```

---

## References

- [MCP Specification](https://modelcontextprotocol.io/)
- [ADR-003: MCP-Native Design](../adr/ADR-003-mcp-native-design.md)
- [Architecture: LLM Context Optimization](LLM_CONTEXT_OPTIMIZATION.md)
