<!-- [20251215_DOCS] ADR-005: Multi-Language Support Approach -->

# ADR-005: Multi-Language Support Approach

**Status:** Accepted  
**Date:** 2025-12-15  
**Authors:** Code Scalpel Team  
**Supersedes:** None

---

## Context

Code Scalpel initially supported only Python. Version 2.0.0 ("Polyglot") extends support to JavaScript, TypeScript, and Java.

### Requirements

| Requirement | Priority |
|-------------|----------|
| Support Python, JavaScript, TypeScript, Java | Must Have |
| Uniform security analysis across languages | Must Have |
| Accurate source location tracking | Must Have |
| Extensibility for future languages | Should Have |
| Consistent API regardless of language | Must Have |

---

## Decision

We will use a **tree-sitter based parsing** approach with **language-specific normalizers** that convert to a common IR.

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Source Code                              │
│            (Python / JS / TS / Java)                         │
└─────────────────────────────────────────────────────────────┘
                          │
            ┌─────────────┼─────────────┐
            ▼             ▼             ▼
    ┌───────────┐  ┌───────────┐  ┌───────────┐
    │ Python    │  │ tree-     │  │ tree-     │
    │ ast       │  │ sitter-js │  │ sitter-   │
    │ module    │  │           │  │ java      │
    └───────────┘  └───────────┘  └───────────┘
            │             │             │
            ▼             ▼             ▼
    ┌───────────┐  ┌───────────┐  ┌───────────┐
    │ Python    │  │ JavaScript│  │ Java      │
    │ Normalizer│  │ Normalizer│  │ Normalizer│
    └───────────┘  └───────────┘  └───────────┘
            │             │             │
            └─────────────┼─────────────┘
                          ▼
              ┌───────────────────────┐
              │   Common IR Nodes     │
              └───────────────────────┘
                          │
                          ▼
              ┌───────────────────────┐
              │   Analysis Passes     │
              │ (Security, Symbolic)  │
              └───────────────────────┘
```

### Language Detection

```python
EXTENSION_MAP = {
    '.py': 'python',
    '.js': 'javascript',
    '.mjs': 'javascript',
    '.jsx': 'javascript',
    '.ts': 'typescript',
    '.tsx': 'typescript',
    '.java': 'java',
}
```

### Parser Selection

| Language | Parser | Rationale |
|----------|--------|-----------|
| Python | `ast` module | Native, accurate, fast |
| JavaScript | tree-sitter-javascript | Handles ES6+, JSX |
| TypeScript | tree-sitter-typescript | Type annotations, TSX |
| Java | tree-sitter-java | Modern Java features |

---

## Security Sink Coverage

Each language has specific security sinks:

### Python Sinks
- `cursor.execute()` - SQL Injection
- `os.system()`, `subprocess.run()` - Command Injection
- `render_template_string()` - SSTI
- `open()` - Path Traversal

### JavaScript/TypeScript Sinks
- `innerHTML`, `document.write()` - DOM XSS
- `eval()`, `Function()` - Code Injection
- `child_process.exec()` - Command Injection
- `$.html()` - jQuery XSS

### Java Sinks
- `Statement.executeQuery()` - SQL Injection
- `Runtime.exec()` - Command Injection
- `XMLReader.parse()` - XXE
- `ObjectInputStream.readObject()` - Deserialization

---

## Consequences

### Positive

1. **Unified Analysis:** Same security patterns work across languages
2. **Consistent API:** `extract_code()` works identically for all languages
3. **Extensibility:** Adding a language = new normalizer only
4. **Accuracy:** tree-sitter provides production-grade parsing

### Negative

1. **Complexity:** Multiple parsers and normalizers to maintain
2. **Dependencies:** tree-sitter requires native binaries
3. **Coverage Gaps:** Not all language features are normalized

### Mitigations

- Comprehensive test suites for each normalizer
- Fallback to raw extraction when normalization fails
- Document unsupported language features

---

## Implementation

- **Location:** `src/code_scalpel/ir/normalizers/`
- **Python:** `python_normalizer.py`
- **JavaScript:** `javascript_normalizer.py`
- **TypeScript:** `typescript_normalizer.py` (extends JS normalizer)
- **Java:** `java_normalizer.py`

---

## References

- [ADR-001: IR Layer Design](ADR-001-ir-layer-design.md)
- [tree-sitter Documentation](https://tree-sitter.github.io/)
