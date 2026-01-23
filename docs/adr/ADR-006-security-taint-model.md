<!-- [20251215_DOCS] ADR-006: Security Taint Analysis Model -->

# ADR-006: Security Taint Analysis Model

**Status:** Accepted  
**Date:** 2025-12-15  
**Authors:** Code Scalpel Team  
**Supersedes:** None

---

## Context

Code Scalpel's security analysis detects vulnerabilities by tracking how untrusted data flows through a program to dangerous operations.

### Problem Statement

1. What data should be considered "tainted" (untrusted)?
2. How does taint propagate through operations?
3. When is tainted data dangerous (at what "sinks")?
4. How do sanitizers affect taint?

---

## Decision

We will implement a **Source-Sink Taint Analysis** model with configurable sanitizers.

### Core Concepts

| Concept | Definition |
|---------|------------|
| **Source** | Entry point for untrusted data (e.g., `request.args`) |
| **Sink** | Dangerous operation (e.g., `cursor.execute()`) |
| **Taint** | Marker indicating data is untrusted |
| **Sanitizer** | Function that neutralizes taint for specific sinks |
| **Taint Level** | Severity: UNTAINTED, LOW, MEDIUM, HIGH, CRITICAL |

### Taint Flow Model

```
[Source] ──► taint ──► [Propagation] ──► taint ──► [Sink] = VULNERABILITY
                              │
                              ▼
                        [Sanitizer]
                              │
                              ▼
                      cleared_for_sink
```

### Source Patterns

```python
TAINT_SOURCES = {
    # Web frameworks
    "request.args", "request.form", "request.json",
    "request.cookies", "request.headers",
    
    # Environment
    "os.environ", "sys.argv",
    
    # File/Network
    "file.read()", "socket.recv()",
    
    # Database
    "cursor.fetchone()", "cursor.fetchall()"
}
```

### Sink Patterns

```python
TAINT_SINKS = {
    "sql": ["cursor.execute", "connection.execute", "db.query"],
    "command": ["os.system", "subprocess.run", "subprocess.call"],
    "xss": ["render_template_string", "Markup", "innerHTML"],
    "path": ["open", "os.path.join", "shutil.copy"],
    "deserialize": ["pickle.loads", "yaml.load", "json.loads"]
}
```

### Sanitizer Registry

```python
SANITIZERS = {
    "int": {"clears": ["sql", "command", "path"]},  # Type coercion
    "html.escape": {"clears": ["xss"]},
    "shlex.quote": {"clears": ["command"]},
    "os.path.basename": {"clears": ["path"]},
    "parameterized_query": {"clears": ["sql"]}  # Using ? placeholders
}
```

---

## Taint Propagation Rules

### Assignment

```python
# Tainted source
user_input = request.args.get("q")  # user_input is TAINTED

# Propagation through assignment
query = user_input  # query is TAINTED
```

### String Operations

```python
# Concatenation propagates taint
sql = "SELECT * FROM users WHERE id = " + user_input  # sql is TAINTED

# F-strings propagate taint
sql = f"SELECT * FROM users WHERE id = {user_input}"  # sql is TAINTED
```

### Function Calls

```python
# Return value tainted if any argument is tainted
result = process(user_input)  # result is TAINTED (conservative)
```

### Sanitization

```python
# Sanitizer clears specific sinks
safe_id = int(user_input)  # safe_id cleared for sql, command, path
cursor.execute(f"SELECT * FROM users WHERE id = {safe_id}")  # SAFE
```

---

## Consequences

### Positive

1. **Accuracy:** Source-sink model catches real vulnerabilities
2. **Configurability:** Custom sources, sinks, sanitizers
3. **Explainability:** Taint paths show how vulnerability occurs
4. **Multi-Language:** Same model works across all supported languages

### Negative

1. **False Positives:** Conservative propagation may over-taint
2. **False Negatives:** Unknown sanitizers may be missed
3. **Complexity:** Inter-procedural analysis is expensive

### Mitigations

- Allow user-defined sanitizers in config file
- Provide confidence scores with each finding
- Document common false positive patterns

---

## Implementation

- **Location:** `src/code_scalpel/symbolic_execution_tools/taint_tracker.py`
- **Classes:**
  - `TaintInfo` - Tracks taint level and propagation path
  - `TaintTracker` - Manages taint state during analysis
  - `SanitizerRegistry` - Configurable sanitizer definitions
  - `SecurityAnalyzer` - Orchestrates source-sink analysis

---

## References

- [CWE Coverage Matrix](../compliance/CWE_COVERAGE_MATRIX.md)
- [OWASP Top 10 Mapping](../compliance/OWASP_TOP_10_MAPPING.md)
