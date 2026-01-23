# Architecture

Code Scalpel is designed as a modular, tier-based MCP server with a focus on surgical code operations and security analysis.

## System Overview

```
┌──────────────────────────────────────────────────────┐
│                   AI Agents                          │
│  (Claude, GitHub Copilot, Cursor, VS Code, etc.)    │
└────────────────────┬─────────────────────────────────┘
                     │ MCP Protocol
                     │ (stdio, HTTP, SSE)
┌────────────────────▼─────────────────────────────────┐
│              MCP Server Layer                        │
│  ┌────────────────────────────────────────────────┐  │
│  │  FastMCP Protocol Handler                      │  │
│  │  - Request routing                             │  │
│  │  - Tool registration                           │  │
│  │  - Tier enforcement                            │  │
│  └────────────────────────────────────────────────┘  │
└────────────────────┬─────────────────────────────────┘
                     │
┌────────────────────▼─────────────────────────────────┐
│              Tool Layer (22 Tools)                   │
│  ┌──────────────┬──────────────┬──────────────────┐  │
│  │ Extraction   │ Security     │ Verification     │  │
│  │ - extract    │ - scan       │ - simulate       │  │
│  │ - update     │ - taint      │ - symbolic       │  │
│  │ - rename     │ - deps       │ - generate_tests │  │
│  └──────────────┴──────────────┴──────────────────┘  │
└────────────────────┬─────────────────────────────────┘
                     │
┌────────────────────▼─────────────────────────────────┐
│              Core Analysis Layer                     │
│  ┌─────────────────────────────────────────────────┐ │
│  │  AST Parsers (tree-sitter, esprima)            │ │
│  │  - Python, JS/TS, Java, Go, Rust, Ruby, PHP    │ │
│  └─────────────────────────────────────────────────┘ │
│  ┌─────────────────────────────────────────────────┐ │
│  │  PDG Builder (Program Dependence Graph)        │ │
│  │  - Data flow analysis                           │ │
│  │  - Control flow analysis                        │ │
│  └─────────────────────────────────────────────────┘ │
│  ┌─────────────────────────────────────────────────┐ │
│  │  Taint Engine                                   │ │
│  │  - Source detection                             │ │
│  │  - Sink detection                               │ │
│  │  - Flow tracking (intra + cross-file)           │ │
│  └─────────────────────────────────────────────────┘ │
│  ┌─────────────────────────────────────────────────┐ │
│  │  Symbolic Execution (Z3 Solver)                 │ │
│  │  - Path exploration                             │ │
│  │  - Constraint solving                           │ │
│  │  - Test generation                              │ │
│  └─────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────┘
```

## Tier System

Code Scalpel implements a three-tier architecture with **progressive enhancement**:

### Community Tier (Open Source)

**License:** MIT (Free)

**Philosophy:** Full functionality with reasonable limits for personal/open-source use.

**Features:**
- ✅ All 22 tools available
- ✅ AST parsing (all languages)
- ✅ Taint-based security scanning
- ✅ Symbolic execution
- ✅ Test generation
- ✅ Cross-file dependency analysis

**Limits:**
- Security findings: 50 per scan
- Symbol references: 100 per query
- Call graph nodes: 500 per analysis
- Project files: 1,000 files
- Test generation: 10 paths

**Implementation:**
```python
# src/code_scalpel/licensing/limits.py
COMMUNITY_LIMITS = {
    "security_findings": 50,
    "symbol_references": 100,
    "call_graph_nodes": 500,
    "project_files": 1000,
    "test_paths": 10,
}
```

### Pro Tier (Commercial)

**License:** Commercial (requires JWT license)

**Target:** Professional developers and teams

**Enhancements:**
- ✅ **Unlimited findings** - No caps on results
- ✅ **Cross-file security scanning** - Track taint across modules
- ✅ **Advanced metrics** - Deeper code analysis
- ✅ **Custom rules** - Define organization-specific policies
- ✅ **Priority support** - Faster response times

**Limits:**
- Security findings: Unlimited
- Symbol references: Unlimited
- Call graph nodes: 10,000 per analysis
- Project files: 10,000 files
- Test generation: 50 paths

### Enterprise Tier (Commercial)

**License:** Commercial (requires JWT license)

**Target:** Large organizations with compliance needs

**Enhancements:**
- ✅ **All Pro features** +
- ✅ **Compliance reporting** (HIPAA, SOC2, GDPR, PCI-DSS)
- ✅ **PDF compliance certificates**
- ✅ **Audit trails** - Full operation logging
- ✅ **Custom policies** - Organization-specific rules
- ✅ **SLA support** - Guaranteed response times
- ✅ **On-premise deployment** - Air-gapped environments

**Limits:**
- All unlimited

## Core Components

### 1. MCP Server

**Location:** `src/code_scalpel/mcp/server.py`

**Responsibilities:**
- Protocol handling (stdio, HTTP, SSE)
- Tool registration and routing
- Request/response serialization
- Tier enforcement
- License validation

**Transport Options:**

#### stdio (Default)
```bash
python -m code_scalpel.mcp.server
```
Used by: VS Code, GitHub Copilot, Claude Desktop, Cursor

#### HTTP
```bash
python -m code_scalpel.mcp.server --transport http --port 8000
```
Used by: Remote deployments, team servers

#### SSE (Server-Sent Events)
```bash
python -m code_scalpel.mcp.server --transport sse --port 8000
```
Used by: Web-based AI assistants

### 2. Tool Layer

**Location:** `src/code_scalpel/mcp/tools/`

**Structure:**
```
tools/
├── extraction.py       # extract_code, update_symbol, rename_symbol
├── analysis.py         # analyze_code, get_file_context, crawl_project
├── navigation.py       # get_symbol_references, get_call_graph, get_dependencies
├── security.py         # security_scan, cross_file_security_scan, unified_sink_detect
├── verification.py     # simulate_refactor, symbolic_execute, generate_unit_tests
├── policy.py           # code_policy_check, verify_policy_integrity
└── utils.py            # validate_paths, scan_dependencies
```

**Tool Registration Pattern:**
```python
from mcp.server.fastmcp import Context
from code_scalpel.mcp.protocol import mcp

@mcp.tool()
async def extract_code(
    target_type: str,
    target_name: str,
    file_path: str | None = None,
    ctx: Context | None = None,
) -> ContextualExtractionResult:
    """Extract code elements with optional dependency context."""
    # Implementation...
```

### 3. AST Parsers

**Location:** `src/code_scalpel/ast_tools/`

**Multi-Language Support:**

| Language | Parser | Features |
|----------|--------|----------|
| Python | `tree-sitter-python` | Full AST + PDG + symbolic |
| JavaScript/TypeScript | `esprima` + `tree-sitter` | Full AST + call graphs |
| Java | `tree-sitter-java` | AST + basic analysis |
| Go | `tree-sitter-go` | AST parsing |
| Rust | `tree-sitter-rust` | AST parsing |
| Ruby | `tree-sitter-ruby` | AST parsing |
| PHP | `tree-sitter-php` | AST parsing |

**Parser Architecture:**
```python
# src/code_scalpel/ast_tools/parser.py
class PolyglotParser:
    def parse(self, code: str, language: str) -> AST:
        if language == "python":
            return self._parse_python(code)
        elif language in ("javascript", "typescript"):
            return self._parse_js(code)
        # ... other languages
        
    def _parse_python(self, code: str) -> AST:
        tree = tree_sitter.parse(code, "python")
        return self._tree_sitter_to_ast(tree)
```

### 4. PDG Builder

**Location:** `src/code_scalpel/pdg/`

**Program Dependence Graph Construction:**

```
Source Code
     ↓
   AST (Abstract Syntax Tree)
     ↓
   CFG (Control Flow Graph)
     ↓
   DFG (Data Flow Graph)
     ↓
   PDG (Program Dependence Graph)
```

**Components:**
- **Control Dependence:** Which statements control execution of others
- **Data Dependence:** Which statements use data from others
- **Call Graph:** Function call relationships
- **Def-Use Chains:** Variable definition and usage tracking

**Example:**
```python
# Code:
def calculate(x):
    if x > 0:
        y = x * 2
    else:
        y = 0
    return y

# PDG:
# Node 1: if x > 0 (control)
# Node 2: y = x * 2 (data: uses x, defines y, control: depends on Node 1)
# Node 3: y = 0 (data: defines y, control: depends on Node 1)
# Node 4: return y (data: uses y, control: depends on Node 1)
```

### 5. Taint Engine

**Location:** `src/code_scalpel/security/analyzers/`

**Taint Analysis Flow:**

```
1. Source Detection
   ↓ (user input, file I/O, network)
   
2. Taint Propagation
   ↓ (track through assignments, calls, returns)
   
3. Sink Detection
   ↓ (dangerous functions: eval, execute, etc.)
   
4. Vulnerability Reporting
   ↓ (CWE classification, severity, flow trace)
```

**Implementation:**
```python
class TaintAnalyzer:
    def __init__(self, pdg: PDG):
        self.pdg = pdg
        self.sources = self._detect_sources()
        self.sinks = self._detect_sinks()
        
    def analyze(self) -> List[Vulnerability]:
        vulnerabilities = []
        for source in self.sources:
            for sink in self.sinks:
                paths = self._find_paths(source, sink)
                if paths:
                    vuln = self._create_vulnerability(source, sink, paths)
                    vulnerabilities.append(vuln)
        return vulnerabilities
```

**Cross-File Taint Tracking:**
```python
# File 1: api/handlers.py
user_id = request.GET['id']  # SOURCE
result = services.get_user(user_id)  # CALL

# File 2: services/user.py
def get_user(user_id):
    query = f"SELECT * FROM users WHERE id={user_id}"  # SINK
    return db.execute(query)

# Taint Engine: Tracks user_id from File 1 → File 2 → SINK
```

### 6. Symbolic Execution Engine

**Location:** `src/code_scalpel/symbolic/`

**Z3 Theorem Prover Integration:**

```
Source Code
     ↓
   AST
     ↓
Symbolic Interpreter
     ↓
Path Constraints (Z3 formulas)
     ↓
Constraint Solver
     ↓
Satisfiable Paths + Test Cases
```

**Example:**
```python
def validate(x, y):
    if x > 0:
        if y < 10:
            return x + y
        else:
            return x - y
    else:
        return 0

# Symbolic Execution finds 3 paths:
# Path 1: x > 0 AND y < 10  → return x + y
# Path 2: x > 0 AND y >= 10 → return x - y
# Path 3: x <= 0            → return 0

# Z3 generates test inputs:
# Path 1: x=1, y=5
# Path 2: x=1, y=15
# Path 3: x=-1, y=0
```

## Data Flow

### Extraction Request Flow

```
1. AI Agent sends MCP request
   ↓
2. MCP Server receives and routes to extract_code tool
   ↓
3. extract_code helper reads file from disk
   ↓
4. PolyglotParser parses code → AST
   ↓
5. Extractor finds target symbol in AST
   ↓
6. (Optional) CrossFileResolver resolves imports
   ↓
7. Returns extracted code + metadata
   ↓
8. MCP Server serializes response
   ↓
9. AI Agent receives ~50 tokens instead of ~10,000
```

### Security Scan Flow

```
1. AI Agent sends code to security_scan
   ↓
2. Parser generates AST
   ↓
3. PDG Builder creates control + data flow graphs
   ↓
4. Source Detector identifies user input points
   ↓
5. Sink Detector identifies dangerous functions
   ↓
6. Taint Analyzer finds paths from sources to sinks
   ↓
7. Vulnerability Reporter classifies by CWE
   ↓
8. Returns vulnerabilities with flow traces
```

## Caching Strategy

**Location:** `src/code_scalpel/cache/`

**Cache Layers:**

1. **AST Cache** - Parsed trees (hot path)
2. **PDG Cache** - Program dependence graphs
3. **Dependency Cache** - Cross-file imports

**Implementation:**
```python
# In-memory LRU cache
ast_cache = LRUCache(maxsize=1000)

# Persistent cache (optional)
CACHE_DIR = os.getenv("SCALPEL_CACHE_DIR", "./.code_scalpel_cache")

# Cache key: file_path + mtime + content_hash
cache_key = f"{file_path}:{mtime}:{content_hash}"
```

**Cache Invalidation:**
- File modification time changed
- Content hash mismatch
- Explicit cache clear

## Concurrency Model

**Async/Await Architecture:**

All MCP tools are async to support concurrent operations:

```python
@mcp.tool()
async def extract_code(...) -> Result:
    # Async file I/O
    content = await aio.read_file(file_path)
    
    # CPU-bound parsing in thread pool
    ast = await asyncio.to_thread(parser.parse, content)
    
    # Return result
    return ContextualExtractionResult(...)
```

**Benefits:**
- Non-blocking I/O
- Parallel tool invocations
- Better resource utilization

## Security Architecture

### Defense in Depth

1. **Path Validation** - Prevent traversal attacks
2. **Sandbox Execution** - Isolate operations
3. **Policy Enforcement** - Compliance checking
4. **Cryptographic Verification** - Prevent tampering
5. **Tier Limits** - Resource exhaustion prevention

### Fail-Closed Model

All security checks use **fail-closed** logic:

```python
# Policy integrity check
if not verify_policy_integrity():
    raise SecurityError("Policy verification failed")
    # DENY ALL operations

# Path validation
if not validate_path(user_path):
    raise SecurityError("Invalid path")
    # DENY file access
```

## Performance Optimizations

### 1. Token Efficiency

**Before Code Scalpel:**
```
Read entire 10,000-line file → 10,000 tokens
```

**With Code Scalpel:**
```
Extract 50-line function → 50 tokens (99% reduction)
```

### 2. Incremental Parsing

Only re-parse changed files:
```python
if file_mtime == cached_mtime and file_hash == cached_hash:
    return cached_ast
```

### 3. Lazy Loading

Load heavy components on-demand:
```python
# Symbolic execution only loaded when needed
if tool_name == "symbolic_execute":
    from code_scalpel.symbolic import SymbolicExecutor
```

### 4. Parallel Processing

Process independent files concurrently:
```python
async with asyncio.TaskGroup() as tg:
    for file_path in files:
        tg.create_task(analyze_file(file_path))
```

## Extensibility Points

### 1. Custom Parsers

Add new language support:
```python
from code_scalpel.ast_tools.parser import register_parser

@register_parser("kotlin")
def parse_kotlin(code: str) -> AST:
    # Implementation...
```

### 2. Custom Security Rules

Add organization-specific rules:
```python
from code_scalpel.security.rules import register_rule

@register_rule("CUSTOM001")
class NoHardcodedCredentials(SecurityRule):
    def check(self, ast: AST) -> List[Violation]:
        # Implementation...
```

### 3. Custom Tools

Extend with new MCP tools:
```python
from code_scalpel.mcp.protocol import mcp

@mcp.tool()
async def custom_analysis(code: str) -> Result:
    # Implementation...
```

## Design Principles

1. **Surgical Precision** - Extract exactly what's needed
2. **Token Efficiency** - Minimize AI agent context consumption
3. **Security First** - Fail-closed, defense in depth
4. **Language Agnostic** - Support multiple languages
5. **Tier Progressive** - Full functionality at all tiers, enhanced limits higher
6. **Deterministic** - Same input → Same output
7. **Extensible** - Plugin architecture for customization

## Technology Stack

- **Core:** Python 3.10+
- **MCP Protocol:** FastMCP
- **AST Parsing:** tree-sitter (multi-language), esprima (JS/TS)
- **PDG Analysis:** Custom implementation
- **Taint Analysis:** Custom implementation
- **Symbolic Execution:** Z3 theorem prover
- **Caching:** In-memory LRU + optional persistent
- **Concurrency:** asyncio
- **Security:** HMAC-SHA256, Sigstore/Cosign

---

**Related Pages:**
- [MCP Tools Reference](MCP-Tools-Reference) - Tool implementations
- [Security](Security) - Security architecture details
- [Contributing](Contributing) - Development architecture
