# Code Scalpel Development Guide

This document is for **developers working ON code-scalpel** (the MCP server itself), not for users using Code Scalpel to analyze their code.

Users should refer to `integration/claude-code/CLAUDE.md` instead.

---

## Quick Start

### Setup Development Environment

```bash
# Clone and install
git clone https://github.com/3D-Tech-Solutions/code-scalpel.git
cd code-scalpel
uv sync

# Run tests
pytest tests/ -v

# Start MCP server locally
python -m code_scalpel.mcp.server
```

### Install MCP in Claude Code (for development)

```bash
# Install locally from your development copy
claude mcp add codescalpel \
  uvx code-scalpel mcp \
  --scope project

# Or with license file
claude mcp add codescalpel \
  -e CODE_SCALPEL_LICENSE_PATH=/path/to/license.jwt \
  uvx code-scalpel mcp \
  --scope project
```

---

## Code Scalpel Tools — When Analyzing code-scalpel Itself

**Apply these priorities when analyzing the code-scalpel codebase:**

### Rule 1: Always Extract, Never Read Whole Files
When reviewing a function or understanding flow:
- ❌ Don't: Read entire parser files (1000+ lines)
- ✅ Do: Use `extract_code` to get just the function you need

**Example:** Review the Java normalizer
```bash
/cs-extract src/code_scalpel/ir/normalizers/java_normalizer.py function normalize_class
```

### Rule 2: Always Use Call Graph for Impact Analysis
When refactoring something, find all callers:
- ❌ Don't: Grep for usages (misses dynamic calls, imports)
- ✅ Do: Use `get_symbol_references` or `get_call_graph`

**Example:** See who calls `normalize_type()`
```bash
/cs-extract [graph_helpers.py] function get_cross_file_dependencies
```

### Rule 3: Security Scan the Tools Themselves
When touching security analysis code:
- ❌ Don't: Manual review for taint issues
- ✅ Do: Use `security_scan` on security tools

**Example:** Verify no injection in cross_file_taint.py
```bash
/cs-security src/code_scalpel/security/analyzers/cross_file_taint.py
```

### Rule 4: Test Generation for Complex Parsers
When working on language parsers:
- ❌ Don't: Write test cases manually
- ✅ Do: Use `generate_unit_tests` from symbolic execution

**Example:** Generate tests for Java parser edge cases
```bash
/cs-tests src/code_scalpel/ir/normalizers/java_normalizer.py function normalize_class
```

### Rule 5: Simulate Before Merging Big Refactors
When refactoring parser architecture:
- ❌ Don't: Commit refactors blindly
- ✅ Do: Use `simulate_refactor` to verify behavior

**Example:** Before splitting a 500-line parser
```bash
/cs-refactor src/code_scalpel/code_parsers/java_parser.py function parse_statement
```

---

## Project Structure

```
code-scalpel/
├── src/code_scalpel/
│   ├── mcp/                          ← MCP Server
│   │   ├── server.py                 ← FastMCP entry point
│   │   ├── protocol.py               ← Tool definitions
│   │   ├── tools/                    ← Tool implementations (23 files)
│   │   │   ├── analyze.py            ← analyze_code, get_file_context
│   │   │   ├── extraction.py         ← extract_code, update_symbol, rename_symbol
│   │   │   ├── context.py            ← context helpers
│   │   │   ├── graph.py              ← get_call_graph, get_graph_neighborhood
│   │   │   ├── security.py           ← security_scan, cross_file_security_scan
│   │   │   ├── symbolic.py           ← symbolic_execute, generate_unit_tests
│   │   │   ├── policy.py             ← code_policy_check, verify_policy_integrity
│   │   │   └── ...
│   │   └── helpers/                  ← Shared utilities
│   │
│   ├── code_parsers/                 ← Language-specific parsers (17 languages)
│   │   ├── python_parser.py
│   │   ├── javascript_parser.py
│   │   ├── typescript_parser.py
│   │   ├── java_parser.py
│   │   ├── go_parser.py
│   │   ├── rust_parser.py
│   │   ├── c_parser.py
│   │   ├── cpp_parser.py
│   │   ├── c_sharp_parser.py
│   │   ├── kotlin_parser.py
│   │   ├── php_parser.py
│   │   ├── ruby_parser.py
│   │   ├── swift_parser.py
│   │   ├── scala_parser.py
│   │   ├── r_parser.py
│   │   ├── lua_parser.py
│   │   ├── dart_parser.py
│   │   └── extractor.py              ← Unified extraction interface
│   │
│   ├── ir/                           ← Intermediate Representation (IR)
│   │   ├── models/                   ← IR AST nodes (20+ types)
│   │   │   ├── expressions.py        ← IRExpr, IRBinOp, IRCall, etc.
│   │   │   ├── statements.py         ← IRIf, IRLoop, IRAssign, etc.
│   │   │   ├── definitions.py        ← IRFunction, IRClass, IRModule
│   │   │   └── ...
│   │   └── normalizers/              ← Per-language IR normalizers (17 files)
│   │       ├── python_normalizer.py
│   │       ├── java_normalizer.py
│   │       ├── typescript_normalizer.py
│   │       └── ...
│   │
│   ├── security/                     ← Security analysis tools
│   │   ├── analyzers/
│   │   │   ├── taint.py              ← Taint flow analysis
│   │   │   ├── cross_file_taint.py   ← Cross-module taint
│   │   │   └── vulnerability_db.py   ← Known vulnerabilities
│   │   └── type_safety/
│   │       └── type_evaporation_detector.py
│   │
│   ├── symbolic_execution_tools/     ← Symbolic execution engine
│   │   ├── engine.py                 ← Z3 solver integration
│   │   ├── ir_interpreter.py         ← IR evaluation
│   │   └── ...
│   │
│   ├── generators/                   ← Code generators
│   │   ├── test_generator.py         ← pytest/unittest generation
│   │   └── ...
│   │
│   └── licensing/                    ← JWT licensing
│       └── jwt_validator.py
│
├── tests/
│   ├── mcp/                          ← MCP server tests
│   ├── tools/                        ← Individual tool tests
│   ├── languages/                    ← Language parser tests
│   ├── symbolic/                     ← Symbolic execution tests
│   └── core/                         ← Core IR tests
│
├── docs/
│   ├── getting_started/
│   ├── guides/
│   ├── QUICK_REFERENCE.md            ← Tool API reference
│   └── ...
│
├── integration/
│   ├── claude-code/                  ← User-facing Claude Code integration
│   │   ├── CLAUDE.md                 ← User template (copy to projects)
│   │   ├── setup.sh                  ← Bootstrap script
│   │   └── skills/                   ← /cs-* slash commands
│   │       ├── cs-setup/
│   │       ├── cs-extract/
│   │       └── ... (8 skills total)
│   └── ...
│
├── .github/workflows/                ← CI/CD pipelines
│   ├── ci.yml                        ← Tests + lint
│   ├── publish-pypi.yml              ← PyPI release
│   ├── publish-vscode.yml            ← VS Code ext
│   └── ...
│
├── pyproject.toml                    ← Project metadata, version 2.2.0
├── uv.lock                           ← Dependency lock file
├── README.md                         ← User-facing README
└── AGENTS.md                         ← Development team guide
```

---

## Key Concepts

### Intermediate Representation (IR)

Code Scalpel converts all 17 languages to a unified **IR (Intermediate Representation)** before analysis. This allows:
- **Polyglot analysis** — Find taint flows across Python and TypeScript
- **Language-agnostic tools** — One taint analyzer works for all languages
- **Consistent behavior** — Same security rules apply everywhere

**Flow:** Source Code → Language Parser → IR Nodes → Analysis Tools

### Taint Analysis

The core security engine tracks how untrusted data (user input, API responses) flows through your code to dangerous functions (SQL execution, shell commands, file writes).

**Key files:**
- `src/code_scalpel/security/analyzers/taint.py` — Basic taint tracking
- `src/code_scalpel/security/analyzers/cross_file_taint.py` — Module boundary taint
- `src/code_scalpel/security/analyzers/vulnerability_db.py` — Known sink patterns

### Symbolic Execution

Explores all possible execution paths through a function using Z3 solver. Finds:
- Edge cases (boundary values)
- Dead code
- Unreachable branches
- Exception cases

**Key files:**
- `src/code_scalpel/symbolic_execution_tools/engine.py` — Z3 orchestration
- `src/code_scalpel/symbolic_execution_tools/ir_interpreter.py` — IR execution

---

## Development Workflow

### 1. Running Tests

```bash
# All tests
pytest tests/

# Specific category
pytest tests/mcp/ -v
pytest tests/tools/security_scan/ -v
pytest tests/languages/test_java_remaining_parsers.py -v

# Specific test
pytest tests/tools/extract_code/test_language_support.py::test_extract_typescript -v

# With coverage
pytest tests/ --cov=src/code_scalpel --cov-report=html
```

### 2. Linting & Formatting

```bash
# Check linting
ruff check src/ tests/

# Fix linting issues
ruff check src/ tests/ --fix

# Format code
black src/ tests/

# Type checking
pyright src/
```

### 3. Building & Publishing

```bash
# Build distribution
python -m build

# Test publish (local)
twine check dist/*

# Publish to PyPI (requires credentials)
twine upload dist/*
```

### 4. Testing MCP Server Locally

```bash
# Start server in one terminal
python -m code_scalpel.mcp.server

# In another terminal, test with claude CLI
claude code --scope project analyze_code /path/to/file
```

---

## Common Development Tasks

### Adding a New Language Parser

1. Create `src/code_scalpel/code_parsers/<language>_parser.py`
2. Implement language-specific AST → IR translation
3. Create `src/code_scalpel/ir/normalizers/<language>_normalizer.py`
4. Add test file: `tests/languages/test_<language>_parser.py`
5. Run: `pytest tests/languages/test_<language>_parser.py`
6. Add language to `src/code_scalpel/mcp/protocol.py` supported languages

### Adding a New Security Rule

1. Add sink pattern to `src/code_scalpel/security/analyzers/vulnerability_db.py`
2. Test with `security_scan` on sample vulnerable code
3. Verify with `cross_file_security_scan` for module boundaries
4. Add test: `tests/tools/security_scan/test_<vulnerability>.py`

### Adding a New Tool

1. Create tool function in `src/code_scalpel/mcp/tools/<module>.py`
2. Add tool definition in `src/code_scalpel/mcp/protocol.py`
3. Write tests in `tests/tools/<tool_name>/`
4. Document in `docs/tools/<tool_name>.md`
5. Reference in `docs/QUICK_REFERENCE.md`

### Refactoring the Parser Infrastructure

1. Use `/cs-map` to understand current architecture
2. Use `/cs-extract` to view specific functions
3. Use `/cs-generate-unit-tests` to create regression tests
4. Use `/cs-simulate-refactor` to verify behavior
5. Use `/cs-refactor` to apply changes safely

---

## Contributing

See `AGENTS.md` for full contribution guidelines.

### Before Committing

```bash
# 1. Check linting
ruff check src/ tests/ --fix
black src/ tests/

# 2. Run type checking
pyright src/

# 3. Run tests
pytest tests/ -x

# 4. Test MCP server
python -m code_scalpel.mcp.server &
# [in another terminal]
claude code analyze_code src/code_scalpel/__init__.py

# 5. Commit with message
git commit -m "feat: add feature description"
```

### PR Checklist

- [ ] Tests pass locally
- [ ] Ruff + Black + Pyright all pass
- [ ] New code has tests (80%+ coverage)
- [ ] Documentation updated
- [ ] Changelog entry added
- [ ] No breaking changes (or documented in PR)

---

## Debugging

### MCP Server Not Responding

```bash
# Check if server is running
lsof -i :8000

# View MCP logs
python -m code_scalpel.mcp.server --debug

# Test with curl
curl http://localhost:8000/health
```

### Parser Not Working for a Language

```bash
# Test the parser directly
python -c "from code_scalpel.code_parsers.java_parser import JavaParser; \
           p = JavaParser(); \
           ir = p.parse('public class Test { }'); \
           print(ir)"

# Use analyze_code to debug
/cs-analyze /path/to/test.java
```

### Taint Flow Not Detected

```bash
# Check vulnerability database
grep -r "SQL_INJECTION" src/code_scalpel/security/

# Test security_scan directly
/cs-security /path/to/vulnerable/code.py

# Use symbolic execution to understand flow
/cs-tests /path/to/function
```

---

## References

- **Full Tool Docs:** `docs/QUICK_REFERENCE.md`
- **MCP Protocol:** `src/code_scalpel/mcp/protocol.py`
- **Team Guide:** `AGENTS.md`
- **Issue Tracker:** https://github.com/3D-Tech-Solutions/code-scalpel/issues
- **GitHub:** https://github.com/3D-Tech-Solutions/code-scalpel

---

## Quick Links

| What | Where |
|------|-------|
| Start using Code Scalpel | `integration/claude-code/CLAUDE.md` |
| API reference for tools | `docs/QUICK_REFERENCE.md` |
| Language support matrix | `docs/COMPLIANCE_CAPABILITY_MATRIX.md` |
| Security analysis docs | `docs/guides/security_analysis.md` |
| Deployment guide | `docs/MCP_DEPLOYMENT_GUIDE.md` |
| Testing locally | `TESTING_LOCAL_DEV.md` |

---

Happy developing! 🔬
