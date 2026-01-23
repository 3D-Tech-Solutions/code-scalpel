<!-- [20251215_DOCS] Architecture: LLM Context Optimization -->

# LLM Context Optimization

This document describes strategies Code Scalpel employs to minimize token usage when serving AI agents.

---

## Problem Statement

Large Language Models have limited context windows:
- Claude: 100K-200K tokens
- GPT-4: 8K-128K tokens
- Copilot: ~8K effective tokens

Traditional code tools return full files or verbose outputs, wasting precious context space.

---

## Token-Efficient Design Principles

### 1. Symbol-Based Extraction (Not Line-Based)

**Traditional Approach (Token-Heavy):**
```
Agent reads entire 500-line file → 5000 tokens
Agent extracts function manually → Manual parsing
```

**Code Scalpel Approach (Token-Efficient):**
```
Agent: extract_code(file_path="utils.py", target_name="calculate_tax")
Server: Returns only the function → 150 tokens
```

**Token Savings:** 97% reduction

### 2. Server-Side File Reading

**Traditional:**
```python
# Agent must read file first
file_content = read_file("utils.py")  # 5000 tokens in
# Then agent parses and extracts
```

**Code Scalpel:**
```python
# Agent sends path, server reads
extract_code(file_path="utils.py", ...)  # 50 tokens in
# Server reads file, extracts, returns  # 150 tokens out
```

**Token Savings:** Agent never sees full file content

### 3. Structured JSON Responses

**Traditional:**
```
Here is the function you requested:

```python
def calculate_tax(amount):
    ...
```

Note: This function depends on TaxRate class...
```

**Code Scalpel:**
```json
{
  "success": true,
  "code": "def calculate_tax(amount): ...",
  "dependencies": ["TaxRate"],
  "token_estimate": 150
}
```

**Benefits:**
- Machine-parseable
- No prose overhead
- Self-documenting structure

---

## Token Estimation

Code Scalpel provides token estimates for extracted code:

```python
def estimate_tokens(code: str) -> int:
    """Estimate tokens using character/word heuristics."""
    # Rough estimate: 1 token ≈ 4 characters for code
    char_estimate = len(code) // 4
    
    # Adjust for code density (keywords, symbols)
    word_count = len(code.split())
    word_estimate = word_count * 1.3
    
    return int((char_estimate + word_estimate) / 2)
```

### Response Includes Token Metadata

```json
{
  "code": "...",
  "token_estimate": 150,
  "context_tokens": 50,
  "total_tokens": 200
}
```

---

## Contextual Extraction

When dependencies are needed, Code Scalpel extracts them efficiently:

### Without Cross-File Dependencies
```json
{
  "code": "def calculate_tax(amount): return amount * TaxRate.STANDARD",
  "dependencies": ["TaxRate"],
  "unresolved_symbols": ["TaxRate"]
}
```

### With Cross-File Dependencies
```json
{
  "code": "def calculate_tax(amount): return amount * TaxRate.STANDARD",
  "dependencies": {
    "TaxRate": {
      "source_file": "models/tax.py",
      "code": "class TaxRate:\n    STANDARD = 0.2"
    }
  },
  "token_estimate": 200
}
```

---

## Comparison: Token Usage by Operation

| Operation | Traditional | Code Scalpel | Savings |
|-----------|-------------|--------------|---------|
| Read function | 5000 tokens | 150 tokens | 97% |
| Security scan | 10000 tokens | 500 tokens | 95% |
| Get file overview | 5000 tokens | 100 tokens | 98% |
| Update function | 10000 tokens | 300 tokens | 97% |

---

## Best Practices for Agents

### 1. Use `get_file_context` Before Extracting

```python
# Get overview first (100 tokens)
context = get_file_context(file_path="utils.py")
# Returns: functions, classes, complexity, no full code

# Then extract specific symbol (150 tokens)
code = extract_code(file_path="utils.py", target_name="calculate_tax")
```

### 2. Request Dependencies Only When Needed

```python
# Without dependencies (faster, fewer tokens)
extract_code(..., include_cross_file_deps=False)

# With dependencies (more tokens, but complete)
extract_code(..., include_cross_file_deps=True)
```

### 3. Use Token Estimates for Planning

```python
# Check token estimate before committing to extraction
if result["token_estimate"] > 1000:
    # Consider extracting only specific methods
    pass
```

---

## Implementation

- **Token Estimation:** `SurgicalExtractor.estimate_tokens()`
- **Contextual Extraction:** `ContextualExtractionResult`
- **File Context:** `get_file_context` MCP tool
- **Symbol References:** `get_symbol_references` MCP tool

---

## References

- [ADR-003: MCP-Native Design](../adr/ADR-003-mcp-native-design.md)
- [Architecture: MCP Integration Patterns](MCP_INTEGRATION_PATTERNS.md)
