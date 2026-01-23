<!-- [20251218_DOCS] Architecture: System Design - Updated for v1.0.0 "Autonomy" -->

# Code Scalpel System Design

> **Version:** 3.0.0 "Autonomy"  
> **Last Updated:** December 18, 2025  
> **Coverage Gate:** ≥90% combined (statement + branch)

This document provides a comprehensive overview of Code Scalpel's architecture and design decisions.

---

## System Overview

Code Scalpel is an MCP-native toolkit enabling AI agents to perform surgical code operations with precision and safety.

### Design Goals

1. **Token Efficiency:** Minimize context usage for LLMs
2. **Surgical Precision:** Extract/modify exact symbols, not line ranges
3. **Multi-Language:** Support Python, JavaScript, TypeScript, Java
4. **Security-First:** Detect vulnerabilities through taint analysis
5. **Safe Modification:** Validate changes before applying
6. **Autonomy Foundation:** Enable bounded autonomous agent operations (v1.0.0+)

---

## Architecture Layers

```
┌─────────────────────────────────────────────────────────────────┐
│                        MCP Interface                             │
│  (Tool definitions, JSON schemas, request/response handling)     │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│                     Analysis Engine                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │ Surgical    │  │ Security    │  │ Symbolic    │             │
│  │ Tools       │  │ Analyzer    │  │ Executor    │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│                    IR / Normalization                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │ IR Nodes    │  │ Normalizers │  │ Operators   │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│                    Language Parsers                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │ Python AST  │  │ tree-sitter │  │ tree-sitter │             │
│  │             │  │ (JS/TS)     │  │ (Java)      │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│                    Infrastructure                                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │ Cache       │  │ File System │  │ Z3 Solver   │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
└─────────────────────────────────────────────────────────────────┘
```

---

## Core Components

### 1. MCP Server (`src/code_scalpel/mcp/server.py`)

The entry point for AI agent interactions.

**Responsibilities:**
- Tool registration and discovery
- Request validation and routing
- Response formatting (JSON)
- Error handling and recovery

**Key Tools:**
- `extract_code` - Symbol-based code extraction
- `update_symbol` - Safe code modification
- `security_scan` - Vulnerability detection
- `analyze_code` - Structure analysis
- `generate_unit_tests` - Test generation

### 2. Surgical Tools (`src/code_scalpel/surgical_*.py`)

Precise code manipulation without line-number guessing.

**SurgicalExtractor:**
- Extract functions, classes, methods by name
- Resolve dependencies (intra-file and cross-file)
- Estimate token usage

**SurgicalPatcher:**
- Replace symbols with validation
- Create backups before modification
- Preserve surrounding code

### 3. Security Analyzer (`src/code_scalpel/symbolic_execution_tools/`)

Taint-based vulnerability detection.

**Components:**
- `TaintTracker` - Track untrusted data flow
- `SecurityAnalyzer` - Source-sink analysis
- `SecretScanner` - Hardcoded credential detection

**Detects:**
- SQL Injection (CWE-89)
- Command Injection (CWE-78)
- XSS (CWE-79)
- Path Traversal (CWE-22)
- SSTI (CWE-1336)
- XXE (CWE-611)

### 4. Symbolic Execution Engine (`src/code_scalpel/symbolic_execution_tools/`)

Path-sensitive analysis using Z3 SMT solver.

**Components:**
- `SymbolicEngine` - Main execution loop
- `IRInterpreter` - Statement interpretation
- `StateManager` - Symbolic variable management
- `ConstraintSolver` - Z3 integration

**Capabilities:**
- Path condition collection
- Concrete input generation
- Feasibility checking

### 5. IR Layer (`src/code_scalpel/ir/`)

Language-agnostic intermediate representation.

**Components:**
- `nodes.py` - IR node definitions
- `operators.py` - Binary/unary operators
- `normalizers/` - Per-language converters

### 6. PDG Tools (`src/code_scalpel/pdg_tools/`)

Program Dependence Graph construction and analysis.

**Components:**
- `PDGBuilder` - Graph construction
- `PDGAnalyzer` - Pattern analysis
- `PDGSlicer` - Program slicing

---

## Data Flow

### Extraction Flow

```
File Path → Parser → AST → Symbol Search → Code Extract → Dependencies → Response
```

### Analysis Flow

```
Code → Parser → AST → IR Normalize → Analysis Pass → Results → Response
```

### Security Scan Flow

```
Code → Parser → Taint Sources → Propagation → Sink Detection → Vulnerabilities
```

### Modification Flow

```
Target + New Code → Validate → Locate Symbol → Backup → Replace → Verify → Save
```

---

## Cross-Cutting Concerns

### Caching

All expensive operations are cached by content hash:

```python
cache_key = sha256(content + str(options))
```

**Cached:** AST parsing, PDG building, security scans, symbolic execution

### Error Handling

Structured error responses with actionable suggestions:

```python
{
    "success": False,
    "error": "Function 'foo' not found",
    "available_functions": ["bar", "baz"]
}
```

### Logging

Structured logging with context:

```python
logger.info("Extracted symbol", extra={
    "file": path,
    "symbol": name,
    "tokens": estimate
})
```

### Configuration

Environment-based configuration:

```python
PROJECT_ROOT = os.getenv("PROJECT_ROOT", os.getcwd())
MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", 10_000_000))
```

---

## Extension Points

### Adding a New Language

1. Create normalizer in `ir/normalizers/{lang}_normalizer.py`
2. Add parser integration (tree-sitter or native)
3. Define language-specific sinks in `taint_tracker.py`
4. Add tests in `tests/test_{lang}_*.py`

### Adding a New MCP Tool

1. Define tool in `mcp/server.py` with `@server.tool()`
2. Implement handler function
3. Add JSON schema for parameters
4. Document in tool description
5. Add integration tests

### Adding a Security Pattern

1. Define source/sink patterns in `taint_tracker.py`
2. Add sanitizer if applicable
3. Add CWE mapping
4. Create test case in `test_security_analysis.py`

---

## Deployment Models

### 1. Local MCP Server

Direct integration with Claude Desktop, VS Code, etc.

```bash
python -m code_scalpel.mcp.server
```

### 2. Docker Container

Isolated deployment with volume mounts.

```bash
docker run -v $(pwd):/workspace code-scalpel
```

### 3. REST API

HTTP wrapper for non-MCP clients.

```bash
python -m code_scalpel.rest_api_server
```

---

## Performance Characteristics

| Operation | Typical Latency | Memory |
|-----------|-----------------|--------|
| Parse (1K lines) | 20ms | 5MB |
| Extract symbol | 10ms | 2MB |
| Security scan | 50ms | 10MB |
| Symbolic execute | 100ms | 20MB |
| Project crawl (100 files) | 2s | 50MB |

---

## References

- [Component Diagrams](COMPONENT_DIAGRAMS.md)
- [Sequence Diagrams](SEQUENCE_DIAGRAMS.md)
- [Scalability Analysis](SCALABILITY_ANALYSIS.md)
- [MCP Integration Patterns](MCP_INTEGRATION_PATTERNS.md)
