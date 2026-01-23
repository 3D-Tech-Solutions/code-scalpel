<!-- [20251215_DOCS] ADR-001: Intermediate Representation Layer Design -->

# ADR-001: Intermediate Representation (IR) Layer Design

**Status:** Accepted  
**Date:** 2025-12-15  
**Authors:** Code Scalpel Team  
**Supersedes:** None

---

## Context

Code Scalpel needs to analyze code across multiple programming languages (Python, JavaScript, TypeScript, Java). Each language has its own AST structure, making it difficult to write uniform analysis passes.

### Problem Statement

1. Language-specific ASTs have incompatible node types and structures
2. Security analysis logic would need to be duplicated for each language
3. Symbolic execution requires a normalized representation for path exploration
4. Adding new languages requires rewriting analysis passes

---

## Decision

We will implement a **Language-Agnostic Intermediate Representation (IR)** layer that normalizes all source languages into a common set of IR nodes.

### Architecture

```
Source Code (Python/JS/TS/Java)
        │
        ▼
┌───────────────────┐
│  Language Parser  │  (tree-sitter / ast module)
└───────────────────┘
        │
        ▼
┌───────────────────┐
│  IR Normalizer    │  (language-specific → IR nodes)
└───────────────────┘
        │
        ▼
┌───────────────────┐
│  IR Nodes         │  (uniform representation)
└───────────────────┘
        │
        ▼
┌───────────────────┐
│  Analysis Passes  │  (security, symbolic, etc.)
└───────────────────┘
```

### IR Node Types

The IR defines the following core node categories:

| Category | Nodes |
|----------|-------|
| **Declarations** | `FunctionDef`, `ClassDef`, `VariableDecl` |
| **Statements** | `Assignment`, `Return`, `If`, `While`, `For`, `Try` |
| **Expressions** | `BinaryOp`, `UnaryOp`, `Call`, `Attribute`, `Subscript` |
| **Literals** | `IntLiteral`, `StringLiteral`, `BoolLiteral`, `NoneLiteral` |
| **Control** | `Break`, `Continue`, `Pass`, `Raise` |

### Source Location Tracking

Each IR node preserves:
- Original source file path
- Line and column numbers
- Original source text span

---

## Consequences

### Positive

1. **Single Analysis Implementation:** Security patterns, symbolic execution, and code metrics work across all languages
2. **Extensibility:** Adding a new language requires only a new normalizer
3. **Maintainability:** Analysis logic is centralized and testable
4. **Debugging:** Source locations enable accurate error reporting

### Negative

1. **Information Loss:** Some language-specific constructs may be simplified
2. **Complexity:** Additional layer between parsing and analysis
3. **Performance:** Extra transformation step adds latency

### Mitigations

- Store original AST nodes for language-specific features when needed
- Cache normalized IR for repeated analysis
- Profile and optimize hot paths in normalizers

---

## Implementation

- **Location:** `src/code_scalpel/ir/`
- **Nodes:** `nodes.py` - Dataclass definitions for all IR node types
- **Operators:** `operators.py` - Enumeration of binary/unary operators
- **Normalizers:** `normalizers/` - Per-language normalizer implementations

---

## References

- [ADR-005: Multi-Language Approach](ADR-005-multi-language-approach.md)
- [RFC-001: Symbolic Execution](../architecture/RFC-001-SYMBOLIC-EXECUTION.md)
