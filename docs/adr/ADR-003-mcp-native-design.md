<!-- [20251215_DOCS] ADR-003: MCP-Native Design Philosophy -->

# ADR-003: MCP-Native Design Philosophy

**Status:** Accepted  
**Date:** 2025-12-15  
**Authors:** Code Scalpel Team  
**Supersedes:** None

---

## Context

Code Scalpel is designed to be consumed by AI agents (Claude, GitHub Copilot, ChatGPT, etc.) via the Model Context Protocol (MCP). This differs from traditional CLI or library-first tools.

### Problem Statement

1. AI agents have limited context windows (tokens)
2. Agents cannot reliably guess line numbers or code structure
3. Traditional tools return verbose output unsuitable for LLM consumption
4. Agents need structured, actionable responses

---

## Decision

Code Scalpel will be designed **MCP-native**, meaning:

1. **Primary Interface:** MCP tools (not CLI or Python API)
2. **Token Efficiency:** Minimize response size while maximizing usefulness
3. **Surgical Operations:** Extract/modify specific symbols by name, not line ranges
4. **Structured Output:** JSON responses with clear schemas

### Design Principles

| Principle | Implementation |
|-----------|----------------|
| **Symbol-Based Access** | `extract_code(target_name="calculate_tax")` not `read_lines(10, 50)` |
| **Server-Side File Reading** | Agent sends file path, server reads file (saves tokens) |
| **Contextual Extraction** | Include dependencies automatically when requested |
| **Safe Modifications** | `update_symbol()` creates backups, validates syntax |

---

## MCP Tool Design Guidelines

### Request Parameters

```python
# Good: Symbol-based, server reads file
extract_code(
    file_path="/project/utils.py",
    target_type="function",
    target_name="calculate_tax"
)

# Bad: Line-based, agent must read file first
read_file(start_line=10, end_line=50)
```

### Response Format

```python
# Good: Structured, includes metadata
{
    "success": True,
    "code": "def calculate_tax(amount): ...",
    "dependencies": ["TaxRate", "RATE_TABLE"],
    "token_estimate": 150
}

# Bad: Raw text dump
"def calculate_tax(amount): ..."
```

### Error Handling

```python
# Good: Actionable error
{
    "success": False,
    "error": "Function 'calculate_tax' not found",
    "available_functions": ["compute_tax", "apply_discount"]
}

# Bad: Stack trace
"Traceback (most recent call last): ..."
```

---

## Consequences

### Positive

1. **Token Efficiency:** 10-100x reduction in token usage for typical operations
2. **Reliability:** Agents don't hallucinate line numbers or code structure
3. **Safety:** Server validates all operations before applying
4. **Discoverability:** Tools expose available symbols and options

### Negative

1. **CLI Secondary:** Command-line interface is less feature-rich
2. **Learning Curve:** Users must understand MCP concepts
3. **Dependency:** Requires MCP-compatible client

### Mitigations

- Provide REST API wrapper for non-MCP clients
- Document MCP setup clearly
- Include example agent prompts and workflows

---

## Implementation

- **MCP Server:** `src/code_scalpel/mcp/server.py`
- **Tool Definitions:** Registered via `@server.tool()` decorators
- **JSON Schemas:** Auto-generated from Pydantic models

---

## References

- [MCP Specification](https://modelcontextprotocol.io/)
- [Architecture: MCP Integration Patterns](../architecture/MCP_INTEGRATION_PATTERNS.md)
- [Architecture: LLM Context Optimization](../architecture/LLM_CONTEXT_OPTIMIZATION.md)
