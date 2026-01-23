# extract_code - Deep Dive Documentation

> [20260103_DOCS] Created comprehensive deep dive documentation for extract_code MCP tool based on v1.0 implementation

**Document Type:** Tool Deep Dive Reference  
**Tool Version:** v1.0  
**Code Scalpel Version:** v3.3  
**Last Updated:** 2026-01-03  
**Status:** Stable  
**Tier Availability:** All Tiers (Community, Pro, Enterprise)

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Technical Overview](#technical-overview)
3. [Features and Capabilities](#features-and-capabilities)
4. [API Specification](#api-specification)
5. [Usage Examples](#usage-examples)
6. [Architecture and Implementation](#architecture-and-implementation)
7. [Testing Evidence](#testing-evidence)
8. [Performance Characteristics](#performance-characteristics)
9. [Security Considerations](#security-considerations)
10. [Integration Patterns](#integration-patterns)
11. [Tier-Specific Behavior](#tier-specific-behavior)
12. [Known Limitations](#known-limitations)
13. [Roadmap and Future Plans](#roadmap-and-future-plans)
14. [Troubleshooting](#troubleshooting)
15. [References and Related Tools](#references-and-related-tools)

---

## Executive Summary

### Purpose Statement
The `extract_code` MCP tool surgically extracts specific code elements (functions, classes, methods) by name from source files with **maximum token efficiency**. Instead of AI agents reading entire files (consuming thousands of tokens), the server reads the file and returns only the requested symbol. This is the **primary code retrieval tool** for Code Scalpel, designed to eliminate line-number guessing and provide actionable context for refactoring, analysis, and modification tasks.

### Key Benefits
- **Token Efficiency:** Agent sends ~50 tokens, receives ~200 (vs 10,000+ for full file)
- **Precision:** Extract by symbol name, not line numbers (no guessing)
- **Multi-Language:** Python (full AST), JavaScript/TypeScript/Java (tree-sitter parsing)
- **Context-Aware:** Optionally include intra-file dependencies (imports, helper functions)
- **Cross-File Resolution:** Pro/Enterprise can resolve imports from external files
- **Deterministic:** Same input = same output (stable across runs)
- **React Support:** JSX/TSX metadata for React components (hooks, props, server components)

### Quick Stats
| Metric | Value |
|--------|-------|
| **Tool Version** | v1.0 |
| **Code Scalpel Version** | v3.3 |
| **Release Date** | 2025-12-21 (v1.0.0 unified extractor) |
| **Token Savings** | ~99% (50 vs 10,000+ tokens) |
| **Supported Languages** | Python, JavaScript, TypeScript, Java |
| **React Metadata** | JSX/TSX (v2.0.2) |
| **Cross-File Deps** | Python (Pro/Enterprise) |
| **Extraction Time** | <50ms (target) |

### When to Use This Tool
- **Primary Use Case:** Retrieve specific functions/classes for analysis or modification
- **Secondary Use Cases:**
  - Understand function implementation before refactoring
  - Extract code with dependencies for standalone testing
  - Get React component code with metadata
  - Retrieve Java methods or JavaScript functions
  - Build prompts for code generation (provide examples)
- **Not Suitable For:**
  - Whole-file reading (use `read_file` or `analyze_code`)
  - Multi-symbol extraction across files (use `crawl_project`)
  - Dynamic/runtime code generation (static analysis only)

---

## Technical Overview

### Core Functionality
The `extract_code` tool performs precise symbol extraction through multi-layered parsing:

**Layer 1 - Language Detection:** Auto-detect from file extension or explicit parameter  
**Layer 2 - Parsing:** AST (Python), tree-sitter (JS/TS/Java)  
**Layer 3 - Symbol Lookup:** Find target by name (function, class, method)  
**Layer 4 - Boundary Detection:** Determine exact start/end lines (decorators, docstrings)  
**Layer 5 - Context Resolution:** Optionally include intra-file dependencies  
**Layer 6 - Cross-File Resolution:** (Pro/Enterprise) Resolve imports from external files

Results provide:
1. **Target Code:** Exact symbol code with decorators and docstrings
2. **Context Code:** Intra-file dependencies (optional)
3. **Cross-File Dependencies:** External imports resolved (Pro/Enterprise, Python only)
4. **Metadata:** Line numbers, language, token estimate, React metadata (JSX/TSX)
5. **Full Code:** Combined target + context for standalone use

**Key Principle:** Tool is **server-side** file reader. The AI agent never sees the full file content—only the extracted symbol. This is the foundation of Code Scalpel's token efficiency.

### Design Principles
1. **Token Efficiency First:** Server reads files, agent receives only what's needed
2. **Symbol-Name Targeting:** Eliminate line-number guessing and line-range errors
3. **Multi-Language Support:** Unified API across Python/JS/TS/Java
4. **Tier-Based Context:** Community gets intra-file, Pro gets cross-file (Python)
5. **Deterministic Boundaries:** Decorators, docstrings, comments included consistently
6. **Safe Defaults:** No cross-file resolution unless explicitly requested

### System Requirements
- **Python Version:** Python 3.9+
- **Dependencies:**
  - `ast` (Python, built-in) for Python AST parsing
  - `tree-sitter` (optional) for JavaScript/TypeScript/Java parsing
  - `SurgicalExtractor` (internal) for Python extraction
  - `UnifiedExtractor` (internal) for polyglot extraction
- **Performance:** <50ms extraction target for single symbol
- **Memory:** ~20MB baseline + ~5KB per symbol

### Integration Context
The `extract_code` tool is typically used **after identifying targets** with other tools:

```mermaid
graph TD
    A[Start] --> B[analyze_code]
    B --> C{Find target<br/>symbol?}
    C -->|Yes| D[extract_code]
    D --> E[Refactor/Analyze]
    
    F[crawl_project] --> G[Identify hotspot]
    G --> D
    
    H[security_scan] --> I[Find vulnerable function]
    I --> D
    
    D --> J[update_symbol]
    D --> K[simulate_refactor]
```

**Upstream:** `analyze_code` (identify symbols), `crawl_project` (find hotspots), `security_scan` (find vulnerabilities)  
**Downstream:** `update_symbol` (modify), `simulate_refactor` (verify changes)

---

## Features and Capabilities

### Core Features (All Tiers)

#### Feature 1: Function Extraction by Name
**Description:** Extract functions by exact name, including decorators and docstrings

**Capabilities:**
- Find function by name (no line numbers needed)
- Include decorators (@staticmethod, @property, etc.)
- Include docstrings
- Preserve type hints
- Return exact line boundaries

**Output:**
```json
{
  "target_code": "def calculate_tax(amount: float, rate: float = 0.1) -> float:\n    \"\"\"Calculate tax.\"\"\"\n    return amount * rate",
  "line_start": 15,
  "line_end": 18
}
```

#### Feature 2: Class Extraction
**Description:** Extract entire classes with all methods and attributes

**Capabilities:**
- Extract class definition
- Include all methods
- Include class-level attributes
- Include nested classes
- Preserve decorators and docstrings

#### Feature 3: Method Extraction
**Description:** Extract specific methods from classes

**Format:** `ClassName.method_name`

**Capabilities:**
- Extract single method from class
- Include method decorators
- Include method docstring
- Preserve type hints
- Return class context (optional)

#### Feature 4: Multi-Language Support
**Description:** Extract code from Python, JavaScript, TypeScript, and Java

**Languages Supported:**
- **Python:** Full AST parsing, complete context resolution
- **JavaScript:** Tree-sitter parsing, basic metadata
- **TypeScript:** Tree-sitter parsing, basic metadata
- **Java:** Tree-sitter parsing, method extraction

#### Feature 5: Token Estimation
**Description:** Estimate token count for extracted code

**Purpose:** Help agents manage context windows

**Calculation:** GPT-4-based tokenization estimate

### Community Tier Features

| Feature | Status | Description |
|---------|--------|-------------|
| Function extraction | ✅ Stable | By name, all languages |
| Class extraction | ✅ Stable | Python, Java |
| Method extraction | ✅ Stable | ClassName.method format |
| Intra-file context | ✅ Stable | Python only |
| Token estimation | ✅ Stable | GPT-4-based estimate |
| React metadata | ✅ Stable | JSX/TSX components |

**Configured Limits:**
- Cross-file deps: Disabled
- Context depth: Intra-file only
- Languages: Python (full), JS/TS/Java (single-symbol)

**Example Community Output:**
```json
{
  "success": true,
  "target_name": "calculate_tax",
  "target_code": "def calculate_tax(amount: float, rate: float = 0.1) -> float:\n    \"\"\"Calculate tax.\"\"\"\n    return amount * rate",
  "line_start": 15,
  "line_end": 18,
  "language": "python",
  "context_code": "",
  "cross_file_deps": [],
  "cross_file_deps_note": "Cross-file dependency resolution disabled for Community tier",
  "token_estimate": 42
}
```

### Pro Tier Features (Additive)

| Feature | Status | Description |
|---------|--------|-------------|
| Cross-file dependencies | ✅ Stable | Python only, direct imports |
| Confidence scoring | ✅ Stable | Dependency resolution confidence |
| Decorator preservation | ✅ Stable | All decorators included |
| Type hint preservation | ✅ Stable | Full type annotation support |
| React component metadata | ✅ Stable | Hooks, props, server components |
| Smart context ordering | ✅ Stable | Imports → types → helpers → target |

**Cross-File Resolution (Pro, Python):**
```python
# Example: calculate_tax uses TaxRate from config.py
# Pro tier automatically extracts TaxRate
{
  "target_code": "def calculate_tax(...)...",
  "cross_file_deps": [
    {
      "symbol": "TaxRate",
      "source_file": "config.py",
      "depth": 1,
      "confidence": 0.9,
      "code": "TaxRate = 0.1"
    }
  ]
}
```

**React Metadata (Pro):**
```json
{
  "react_metadata": {
    "component_type": "functional",
    "is_server_component": false,
    "has_server_action": false,
    "hooks_used": ["useState", "useEffect"],
    "props_interface": "ButtonProps"
  }
}
```

**Example Pro Tier Output (Additional Fields):**
```json
{
  "success": true,
  "target_name": "calculate_tax",
  "target_code": "def calculate_tax(...)...",
  "line_start": 15,
  "line_end": 18,
  "language": "python",
  "type_hints": {
    "params": {"amount": "float", "rate": "float"},
    "return": "float"
  },
  "cross_file_deps": [
    {
      "symbol": "DEFAULT_TAX_RATE",
      "source_file": "config.py",
      "depth": 1,
      "confidence": 0.9,
      "code": "DEFAULT_TAX_RATE = 0.1"
    }
  ],
  "token_estimate": 87
}
```

### Enterprise Tier Features (Additive)

| Feature | Status | Description |
|---------|--------|-------------|
| Organization-wide resolution | ✅ Stable | Monorepo/multi-repo support |
| Custom extraction patterns | ✅ Stable | Regex/import/function-call patterns |
| Service boundary detection | ✅ Stable | Microservice context |
| Packaging hints | ✅ Stable | Dockerfile-ready, standalone flags |
| Dependency graph visualization | ⏳ Roadmap v1.1 | Mermaid diagrams |
| Extraction templates | ⏳ Roadmap v1.1 | Preset bundles |

**Organization Context (Enterprise):**
```json
{
  "organization_context": {
    "module_owner": "@tax-team",
    "service_boundary": "billing-service",
    "api_visibility": "internal"
  },
  "packaging_hints": {
    "dockerfile_ready": true,
    "standalone_capable": true,
    "external_deps": ["decimal"]
  }
}
```

---

## API Specification

### MCP Tool Signature

```python
@mcp.tool()
async def extract_code(
    target_type: str,
    target_name: str,
    file_path: str | None = None,
    code: str | None = None,
    language: str | None = None,
    include_context: bool = False,
    context_depth: int = 1,
    include_cross_file_deps: bool = False,
    include_token_estimate: bool = True,
    ctx: Context | None = None
) -> ContextualExtractionResult:
    """
    Surgically extract specific code elements (functions, classes, methods).
    
    TOKEN-EFFICIENT MODE (RECOMMENDED):
    Provide file_path - server reads file, agent saves thousands of tokens.
    
    MULTI-LANGUAGE SUPPORT (v2.0.0):
    Python, JavaScript, TypeScript, Java. Auto-detects from extension.
    
    CROSS-FILE DEPENDENCIES (Pro/Enterprise, Python):
    Set include_cross_file_deps=True to resolve imports automatically.
    
    Tier Capabilities:
        COMMUNITY: Single-symbol extraction, intra-file context (Python)
        PRO: + Cross-file dependencies (Python), React metadata (JSX/TSX)
        ENTERPRISE: + Org-wide resolution, custom patterns, service boundaries
    
    Args:
        target_type: "function", "class", or "method"
        target_name: Symbol name (use "Class.method" for methods)
        file_path: Path to source file (TOKEN SAVER - server reads)
        code: Source code string (fallback if file_path not provided)
        language: Language override ("python", "javascript", "typescript", "java")
        include_context: Include intra-file dependencies (default: False)
        context_depth: Dependency traversal depth (default: 1)
        include_cross_file_deps: Resolve external imports (Pro/Enterprise, Python)
        include_token_estimate: Include token count estimate (default: True)
        ctx: MCP context (optional)
        
    Returns:
        ContextualExtractionResult with code, metadata, and dependencies
    """
```

### Parameters

#### Required Parameters

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `target_type` | `str` | Symbol type | `"function"`, `"class"`, `"method"` |
| `target_name` | `str` | Symbol name | `"calculate_tax"`, `"Calculator.add"` |

#### Optional Parameters

| Parameter | Type | Default | Description | Example |
|-----------|------|---------|-------------|---------|
| `file_path` | `str \| None` | `None` | Path to source file | `/project/src/utils.py` |
| `code` | `str \| None` | `None` | Source code string | `"def foo(): ..."` |
| `language` | `str \| None` | `None` | Language override | `"python"`, `"javascript"` |
| `include_context` | `bool` | `False` | Include intra-file deps | `True` |
| `context_depth` | `int` | `1` | Dependency depth | `2` |
| `include_cross_file_deps` | `bool` | `False` | Resolve external imports (Pro) | `True` |
| `include_token_estimate` | `bool` | `True` | Include token count | `True` |
| `ctx` | `Context \| None` | `None` | MCP context | (internal) |

### Return Value Structure

#### Community Tier Response

```json
{
  "success": true,
  "target_name": "calculate_tax",
  "target_code": "def calculate_tax(amount: float, rate: float = 0.1) -> float:\n    \"\"\"Calculate tax for a given amount.\"\"\"\n    if rate > 1:\n        rate = rate / 100\n    return amount * rate",
  "context_code": "",
  "full_code": "def calculate_tax(amount: float, rate: float = 0.1) -> float:\n    \"\"\"Calculate tax for a given amount.\"\"\"\n    if rate > 1:\n        rate = rate / 100\n    return amount * rate",
  "context_items": [],
  "total_lines": 5,
  "line_start": 15,
  "line_end": 20,
  "language": "python",
  "token_estimate": 42,
  "cross_file_deps": [],
  "cross_file_deps_note": "Cross-file dependency resolution disabled for Community tier"
}
```

#### Pro Tier Response (Additional Fields)

```json
{
  "success": true,
  "target_name": "calculate_tax",
  "target_code": "...",
  "line_start": 15,
  "line_end": 20,
  "language": "python",
  "type_hints": {
    "params": {
      "amount": "float",
      "rate": "float"
    },
    "return": "float"
  },
  "decorators": [],
  "docstring": "Calculate tax for a given amount.",
  "cross_file_deps": [
    {
      "symbol": "DEFAULT_TAX_RATE",
      "source_file": "/project/src/config.py",
      "depth": 1,
      "confidence": 0.9,
      "code": "DEFAULT_TAX_RATE = 0.1"
    }
  ],
  "react_metadata": null,
  "token_estimate": 87
}
```

#### Pro Tier Response (React/TSX)

```json
{
  "success": true,
  "target_name": "TaxCalculator",
  "target_code": "export function TaxCalculator({ rate }: Props) {\n  const [amount, setAmount] = useState(0);\n  const tax = calculateTax(amount, rate);\n  return <div className=\"calculator\">...</div>;\n}",
  "line_start": 10,
  "line_end": 25,
  "language": "tsx",
  "react_metadata": {
    "component_type": "functional",
    "is_server_component": false,
    "has_server_action": false,
    "hooks_used": ["useState"],
    "props_interface": "Props"
  },
  "cross_file_deps": [
    {
      "symbol": "calculateTax",
      "source_file": "/project/src/utils/tax.ts",
      "depth": 1,
      "confidence": 0.9
    }
  ],
  "token_estimate": 124
}
```

#### Enterprise Tier Response (Additional Fields)

```json
{
  "success": true,
  "target_name": "calculate_tax",
  "target_code": "...",
  "line_start": 15,
  "line_end": 20,
  "language": "python",
  "cross_file_deps": [
    {
      "symbol": "DEFAULT_TAX_RATE",
      "source_file": "/project/src/config.py",
      "depth": 1,
      "confidence": 0.9,
      "code": "DEFAULT_TAX_RATE = 0.1"
    }
  ],
  "organization_context": {
    "module_owner": "@tax-team",
    "service_boundary": "billing-service",
    "api_visibility": "internal"
  },
  "packaging_hints": {
    "dockerfile_ready": true,
    "standalone_capable": true,
    "external_deps": ["decimal"]
  },
  "token_estimate": 125
}
```

### Error Handling

| Error Type | Condition | Response |
|------------|-----------|----------|
| `MissingTarget` | Symbol not found | `{"success": false, "error": "Function 'foo' not found"}` |
| `InvalidFormat` | Method format wrong | `{"success": false, "error": "Use Class.method format"}` |
| `FileNotFound` | file_path doesn't exist | `{"success": false, "error": "File not found"}` |
| `ParseError` | Syntax errors | `{"success": false, "error": "Parse error at line X"}` |
| `TierLimited` | Cross-file deps on Community | `{"success": false, "error": "Requires PRO tier"}` |

---

## Usage Examples

### Example 1: Basic Function Extraction (Community Tier)

**Scenario:** Extract tax calculation function

```json
{
  "target_type": "function",
  "target_name": "calculate_tax",
  "file_path": "/home/user/project/src/utils.py"
}
```

**Response:**
```json
{
  "success": true,
  "target_code": "def calculate_tax(amount: float, rate: float = 0.1) -> float:\n    \"\"\"Calculate tax for a given amount.\"\"\"\n    if rate > 1:\n        rate = rate / 100\n    return amount * rate",
  "line_start": 15,
  "line_end": 20,
  "language": "python",
  "token_estimate": 42
}
```

### Example 2: Method Extraction from Class

**Scenario:** Extract specific method from Calculator class

```json
{
  "target_type": "method",
  "target_name": "Calculator.add",
  "file_path": "/home/user/project/src/calculator.py"
}
```

**Response:**
```json
{
  "success": true,
  "target_code": "def add(self, a: int, b: int) -> int:\n    \"\"\"Add two numbers.\"\"\"\n    return a + b",
  "line_start": 10,
  "line_end": 13,
  "language": "python",
  "token_estimate": 28
}
```

### Example 3: Pro Tier with Cross-File Dependencies

**Scenario:** Extract function with external imports

```json
{
  "target_type": "function",
  "target_name": "process_order",
  "file_path": "/home/user/project/src/services/order.py",
  "include_cross_file_deps": true
}
```

**Response:**
```json
{
  "success": true,
  "target_code": "def process_order(order_id: str) -> OrderResult:\n    config = TaxConfig()\n    tax = calculate_tax(order.amount, config.rate)\n    return OrderResult(total=order.amount + tax)",
  "line_start": 25,
  "line_end": 30,
  "cross_file_deps": [
    {
      "symbol": "TaxConfig",
      "source_file": "/home/user/project/src/config.py",
      "depth": 1,
      "confidence": 0.9,
      "code": "class TaxConfig:\n    rate = 0.1"
    },
    {
      "symbol": "calculate_tax",
      "source_file": "/home/user/project/src/utils.py",
      "depth": 1,
      "confidence": 0.95,
      "code": "def calculate_tax(amount, rate):\n    return amount * rate"
    }
  ],
  "token_estimate": 145
}
```

### Example 4: React Component Extraction (Pro Tier)

**Scenario:** Extract React component with hooks

```json
{
  "target_type": "function",
  "target_name": "TaxCalculator",
  "file_path": "/home/user/project/src/components/TaxCalculator.tsx"
}
```

**Response:**
```json
{
  "success": true,
  "target_code": "export function TaxCalculator({ rate }: Props) {\n  const [amount, setAmount] = useState(0);\n  const tax = calculateTax(amount, rate);\n  return <div className=\"calculator\">\n    <input value={amount} onChange={e => setAmount(Number(e.target.value))} />\n    <p>Tax: ${tax}</p>\n  </div>;\n}",
  "line_start": 10,
  "line_end": 18,
  "language": "tsx",
  "react_metadata": {
    "component_type": "functional",
    "is_server_component": false,
    "has_server_action": false,
    "hooks_used": ["useState"],
    "props_interface": "Props"
  },
  "token_estimate": 118
}
```

### Example 5: AI Agent Integration (Claude)

**Scenario:** Claude extracts function for refactoring

```python
# User: "Refactor the calculate_tax function to use Decimal"

# Claude invokes:
result = await extract_code(
    target_type="function",
    target_name="calculate_tax",
    file_path="/home/user/project/src/utils.py",
    include_cross_file_deps=True
)

# Claude receives:
# - target_code: "def calculate_tax(...)..."
# - cross_file_deps: [TaxConfig, DEFAULT_TAX_RATE]
# - token_estimate: 87

# Claude responds:
# "I'll refactor calculate_tax to use Decimal for precision:
#
# Current implementation uses float, which can cause rounding errors.
# I'll update it to use the Decimal type from Python's decimal module.
#
# Here's the refactored version:
# [shows updated code with Decimal]
#
# This change also affects TaxConfig (imported from config.py).
# Should I update that as well?"
```

### Example 6: Java Method Extraction

**Scenario:** Extract Java method

```json
{
  "target_type": "method",
  "target_name": "Calculator.add",
  "file_path": "/home/user/project/src/Calculator.java"
}
```

**Response:**
```json
{
  "success": true,
  "target_code": "public int add(int a, int b) {\n    return a + b;\n}",
  "line_start": 15,
  "line_end": 18,
  "language": "java",
  "token_estimate": 22
}
```

---

## Architecture and Implementation

### Component Architecture

```mermaid
graph TB
    subgraph "extract_code MCP Tool"
        A[Input Validator]
        B[Language Detector]
        C[Tier Capability Checker]
        D[Router]
    end
    
    subgraph "Python Path"
        E[SurgicalExtractor]
        F[AST Parser]
        G[Symbol Lookup]
        H[Context Resolver]
        I[Cross-File Resolver]
    end
    
    subgraph "Polyglot Path"
        J[UnifiedExtractor]
        K[Tree-sitter Parser]
        L[Symbol Boundary Detector]
        M[React Metadata Extractor]
    end
    
    subgraph "Result Assembly"
        N[Code Combiner]
        O[Token Estimator]
        P[Metadata Builder]
        Q[JSON Formatter]
    end
    
    A --> B
    B --> C
    C --> D
    D -->|Python| E
    D -->|JS/TS/Java| J
    E --> F
    F --> G
    G --> H
    H --> I
    J --> K
    K --> L
    L --> M
    I --> N
    M --> N
    N --> O
    O --> P
    P --> Q
```

### Algorithm Overview

#### Primary Algorithm: AST-Based Symbol Extraction (Python)
**Complexity:** O(n) where n = lines in file  
**Description:** Parse file, walk AST, find symbol by name, extract boundaries

**Pseudocode:**
```
1. Validate inputs (target_type, target_name, file_path or code)
2. Detect language from file extension or parameter
3. If Python:
   a. Parse file into AST
   b. Walk AST nodes (FunctionDef, ClassDef, AsyncFunctionDef)
   c. Match node.name == target_name
   d. Extract decorators (lines before node)
   e. Extract docstring (first statement if Expr with Constant)
   f. Determine boundaries (decorator_start to body_end)
   g. Extract code from original source (preserve formatting)
   h. If include_context:
      - Find dependencies (called functions, used classes)
      - Extract dependency code (recursive up to context_depth)
   i. If include_cross_file_deps (Pro/Enterprise):
      - Resolve imports from external files
      - Extract imported symbols (recursive with confidence decay)
4. Else (JS/TS/Java):
   a. Parse with tree-sitter
   b. Find symbol in parse tree
   c. Extract boundaries
   d. If JSX/TSX: extract React metadata (hooks, props, server components)
5. Combine target + context
6. Estimate tokens (GPT-4 tokenization)
7. Return ContextualExtractionResult
```

### Data Flow

```mermaid
sequenceDiagram
    participant Agent as AI Agent
    participant Tool as extract_code
    participant Parser as AST/Tree-sitter
    participant Extractor as SurgicalExtractor
    participant FileSystem as File System
    
    Agent->>Tool: extract_code(file_path, target_name)
    Tool->>Tool: Validate tier capabilities
    Tool->>FileSystem: Read file (server-side)
    FileSystem-->>Tool: File content
    Tool->>Parser: Parse(content, language)
    Parser-->>Tool: AST/Parse Tree
    Tool->>Extractor: Find symbol(target_name)
    Extractor->>Extractor: Walk AST nodes
    Extractor->>Extractor: Match node.name == target
    Extractor->>Extractor: Determine boundaries
    Extractor->>Extractor: Extract code
    alt include_cross_file_deps (Pro/Enterprise)
        Extractor->>FileSystem: Read imported files
        FileSystem-->>Extractor: External symbols
        Extractor->>Extractor: Resolve dependencies
    end
    Extractor-->>Tool: ExtractionResult
    Tool->>Tool: Estimate tokens
    Tool->>Tool: Build metadata
    Tool-->>Agent: ContextualExtractionResult
```

### Key Implementation Details

#### Detail 1: Decorator Inclusion
Decorators are always included:
```python
# Decorator lines tracked back from function definition
@staticmethod
@cached_property
def calculate_tax(...):
    ...
# All 3 lines extracted
```

#### Detail 2: Docstring Detection
First statement checked for docstring:
```python
def foo():
    """This is a docstring."""  # Included
    x = 1  # Not a docstring
```

#### Detail 3: Method Extraction Format
Methods use "Class.method" format:
```python
# Input: target_name="Calculator.add"
# Finds: class Calculator, then method add
class Calculator:
    def add(self, a, b):  # This method extracted
        return a + b
```

#### Detail 4: Cross-File Confidence Decay
Confidence decreases with depth:
```python
# Depth 1: confidence = 0.9
# Depth 2: confidence = 0.9 * 0.9 = 0.81
# Depth 3: confidence = 0.9 * 0.9 * 0.9 = 0.729
```

#### Detail 5: React Metadata Detection
JSX/TSX components analyzed for:
```typescript
// Detected: functional component, useState hook, Props interface
export function MyComponent({ name }: Props) {
  const [count, setCount] = useState(0);
  return <div>{name}: {count}</div>;
}
```

### Dependencies

| Dependency | Version | Purpose | Tier |
|------------|---------|---------|------|
| `ast` | Built-in | Python AST parsing | All |
| `tree-sitter` | Optional | JS/TS/Java parsing | All |
| `SurgicalExtractor` | Internal | Python extraction engine | All |
| `UnifiedExtractor` | Internal | Polyglot extraction engine | All |

---

## Testing Evidence

### Test Coverage

| Test Category | Tests | Coverage | Status |
|---------------|-------|----------|--------|
| Unit Tests | TBD | TBD | ⬜ Pending Evidence |
| Integration Tests | TBD | TBD | ⬜ Pending Evidence |
| Language Tests | TBD | TBD | ⬜ Pending Evidence |
| Performance Tests | TBD | N/A | ⬜ Pending Evidence |

**Status:** Test evidence gathering in progress.

### Critical Test Cases (Planned)

#### Test Case 1: Decorator Preservation
**Purpose:** Verify decorators are always included  
**Input:** Function with @staticmethod, @property decorators  
**Expected:** All decorators in target_code  
**Status:** ⬜ Test exists, evidence pending

#### Test Case 2: Cross-File Resolution Accuracy
**Purpose:** Verify Pro tier resolves imports correctly  
**Input:** Function using TaxConfig from config.py  
**Expected:** TaxConfig included in cross_file_deps with confidence 0.9  
**Status:** ⬜ Test exists, evidence pending

#### Test Case 3: React Metadata Extraction
**Purpose:** Verify JSX/TSX components get correct metadata  
**Input:** React functional component with useState  
**Expected:** react_metadata.hooks_used = ["useState"]  
**Status:** ⬜ Test exists, evidence pending

#### Test Case 4: Multi-Language Extraction
**Purpose:** Verify all languages extract correctly  
**Input:** Same symbol name across Python/JS/TS/Java  
**Expected:** Correct extraction for each language  
**Status:** ⬜ Test exists, evidence pending

#### Test Case 5: Token Estimation Accuracy
**Purpose:** Verify token estimates within ±10%  
**Input:** Known code with actual token count  
**Expected:** Estimate within 10% of actual  
**Status:** ⬜ Test exists, evidence pending

---

## Performance Characteristics

### Benchmarks (Targets)

#### Benchmark 1: Extraction Time by File Size
**Test Configuration:** Various file sizes, single symbol

| File Size | Target Time | Notes |
|-----------|-------------|-------|
| Small (<100 lines) | <10ms | Baseline |
| Medium (100-500 lines) | <20ms | Typical |
| Large (500-2K lines) | <50ms | Target |
| Very Large (2K-10K lines) | <200ms | Acceptable |

**Status:** Targets defined, actual benchmarks pending.

#### Benchmark 2: Token Savings
**Test Configuration:** Compare full file vs extract_code

| File Size | Full File Tokens | Extracted Tokens | Savings |
|-----------|------------------|------------------|---------|
| 100 lines | ~2,500 | ~50 | 98% |
| 500 lines | ~12,500 | ~150 | 98.8% |
| 2K lines | ~50,000 | ~200 | 99.6% |
| 10K lines | ~250,000 | ~250 | 99.9% |

**Status:** Targets defined, actual measurements pending.

### Performance Characteristics

**Best Case:** Small file, function at top (~5ms)  
**Average Case:** Medium file, function in middle (~20ms)  
**Worst Case:** Large file, class with many methods (~200ms)

### Scalability

**File Size:** No hard limit, scales linearly with file size  
**Symbol Count:** Single symbol per call (batch extraction not supported)  
**Language:** Python fastest (AST), JS/TS/Java slightly slower (tree-sitter)

---

## Security Considerations

### Threat Model

**Assets Protected:**
- Source code (confidentiality)
- File paths (information disclosure)
- Extracted symbols (could reveal business logic)

**Threat Actors:**
- Attacker with file system access (reads arbitrary files)
- Insider threat (extracts proprietary code)
- Path traversal attacker (accesses files outside project)

### Attack Vectors

**Vector 1: Path Traversal**
- **Threat:** file_path="../../../etc/passwd"
- **Mitigation:** Path validation, workspace root enforcement

**Vector 2: Information Disclosure**
- **Threat:** Extract sensitive functions (auth, crypto)
- **Mitigation:** Tier-based limits, audit logging (Enterprise)

**Vector 3: Token Exhaustion**
- **Threat:** Request extraction with massive cross-file deps
- **Mitigation:** Depth limits per tier, timeout enforcement

### Security Features

#### Input Validation
- **Method:** Path validation, symbol name sanitization
- **Sanitization:** Paths normalized, relative to workspace root
- **Rejection Criteria:** Invalid paths, permission denied, outside workspace

#### Safe Defaults
- **Cross-File:** Disabled by default (Community)
- **Depth:** Capped at 1 (direct dependencies only)
- **Workspace Roots:** Enforced via MCP roots capability (v2.0.0)

---

## Integration Patterns

### MCP Client Integration

#### Claude Desktop Integration

**Configuration:**
```json
{
  "mcpServers": {
    "code-scalpel": {
      "command": "python",
      "args": ["-m", "code_scalpel.mcp_server"],
      "env": {
        "PROJECT_ROOT": "/path/to/project",
        "CODE_SCALPEL_LICENSE_KEY": "your-license-key"
      }
    }
  }
}
```

**Usage Example:**
```
User: "Show me the calculate_tax function"

Claude:
1. Invokes: extract_code(file_path="src/utils.py", target_name="calculate_tax")
2. Receives: target_code (5 lines), token_estimate: 42
3. Responds: "Here's the calculate_tax function:

def calculate_tax(amount: float, rate: float = 0.1) -> float:
    \"\"\"Calculate tax for a given amount.\"\"\"
    if rate > 1:
        rate = rate / 100
    return amount * rate

This function takes an amount and optional rate, normalizes percentage rates,
and returns the calculated tax."
```

### Resource Template Access

**URI Format:** `code:///{language}/{module}/{symbol}`

**Examples:**
```python
# Access via URI (no file path needed)
code:///python/utils/calculate_tax
code:///typescript/components/UserCard
code:///java/services.AuthService/authenticate
```

**Integration:**
```python
# MCP resource access
@mcp.resource("code:///{language}/{module}/{symbol}")
async def get_code_resource(language, module, symbol):
    # Automatically resolves to file path
    # Extracts symbol
    # Returns JSON
```

### LangChain Integration

```python
from langchain.tools import StructuredTool
from code_scalpel.mcp_tools import extract_code

def extract_code_wrapper(file_path: str, target_name: str) -> dict:
    """Wrapper for LangChain."""
    return extract_code(
        target_type="function",
        target_name=target_name,
        file_path=file_path
    )

langchain_tool = StructuredTool.from_function(
    func=extract_code_wrapper,
    name="extract_code",
    description="Extract specific functions/classes by name"
)

# Use in agent
agent = initialize_agent([langchain_tool], llm=llm)
result = agent.run("Extract the process_order function from services/order.py")
```

---

## Tier-Specific Behavior

### Community Tier

**Available Features:**
- ✅ Function extraction by name
- ✅ Class extraction
- ✅ Method extraction (Class.method)
- ✅ Intra-file context (Python only)
- ✅ Multi-language (Python, JS, TS, Java)
- ✅ Token estimation
- ✅ React metadata (JSX/TSX)

**Limits:**
- Cross-file dependencies: **Disabled**
- Context depth: **Intra-file only**
- Languages: Python (full), JS/TS/Java (single-symbol)

**Example Workflow:**
```
User: extract_code(file_path="utils.py", target_name="calculate_tax")
→ Server reads file
→ Extracts function with decorators
→ Returns 42 tokens (vs 2,500 for full file)
→ Agent saves 98% tokens
```

### Pro Tier

**Additional Features:**
- ✅ Cross-file dependencies (Python)
- ✅ Confidence scoring (depth-based decay)
- ✅ Smart context ordering (imports → types → helpers)
- ✅ Conditional import handling
- ✅ Type hint preservation
- ✅ React component metadata (hooks, props)

**Enhanced Capabilities:**
- Cross-file deps: **Direct imports (depth=1)**
- Context depth: **Up to 2 levels**
- Confidence: **0.9 at depth 1, 0.81 at depth 2**

**Example Workflow:**
```
User: extract_code(
    file_path="services/order.py",
    target_name="process_order",
    include_cross_file_deps=True
)
→ Extracts process_order function
→ Resolves TaxConfig from config.py (confidence 0.9)
→ Resolves calculate_tax from utils.py (confidence 0.9)
→ Returns target + 2 dependencies
→ Token estimate: 145 (vs 50 without cross-file)
```

### Enterprise Tier

**Additional Features:**
- ✅ Organization-wide resolution (monorepo)
- ✅ Custom extraction patterns
- ✅ Service boundary detection
- ✅ Packaging hints (Dockerfile-ready)
- ✅ Module ownership (CODEOWNERS)
- ⏳ Dependency graph visualization (v1.1)
- ⏳ Extraction templates (v1.1)

**Enhanced Capabilities:**
- Cross-file deps: **Unlimited depth**
- Organization context: **Multi-repo support**
- Custom patterns: **Regex/import/function-call**

**Example Workflow:**
```
User: extract_code(
    file_path="billing-service/src/tax.py",
    target_name="calculate_tax",
    organization_wide=True
)
→ Extracts from monorepo
→ Detects service boundary (billing-service)
→ Identifies module owner (@tax-team from CODEOWNERS)
→ Checks packaging (Dockerfile-ready: true)
→ Returns with org context + packaging hints
```

---

## Known Limitations

### Current Limitations

#### Limitation 1: Cross-File Resolution Python-Only (v1.0)
**Impact:** JavaScript/TypeScript/Java don't support cross-file dependency resolution  
**Workaround:** Extract dependencies manually for non-Python languages  
**Planned Fix:** v1.2 Q2 2026 - Multi-language cross-file resolution

#### Limitation 2: Dynamic Symbols Not Extracted
**Impact:** Functions created at runtime (exec, eval, metaclasses) not found  
**Workaround:** None; static analysis limitation  
**Planned Fix:** v1.3 Q3 2026 - Dynamic symbol inference (best-effort)

#### Limitation 3: Complex Generics (TypeScript)
**Impact:** Some TypeScript generic types may not preserve fully  
**Workaround:** None currently  
**Planned Fix:** v1.1 Q1 2026 - Improved generic handling

#### Limitation 4: Single Symbol Per Call
**Impact:** Can't batch extract multiple symbols  
**Workaround:** Call extract_code multiple times  
**Planned Fix:** v1.3 Q3 2026 - Parallel batch extraction

### Language Support

| Language | v1.0 | v1.1 | v1.2 |
|----------|------|------|------|
| Python | ✅ Full (AST + cross-file) | ✅ Full | ✅ Full |
| JavaScript | ✅ Single-symbol | ✅ Single-symbol | ✅ Cross-file |
| TypeScript | ✅ Single-symbol + JSX | ✅ Generics | ✅ Cross-file |
| Java | ✅ Single-symbol | ✅ Single-symbol | ✅ Cross-file |
| Rust | ❌ | ⏳ Q2 2026 | ✅ Q2 2026 |
| Go | ❌ | ⏳ Q2 2026 | ✅ Q2 2026 |

---

## Roadmap and Future Plans

### v1.1 (Q1 2026): Enhanced Dependency Resolution

#### All Tiers
- [ ] Improved error messages (suggest closest matches)
- [ ] Nested class extraction (Python)
- [ ] Circular dependency detection (intra-file)

#### Pro Tier
- [ ] Smart dependency ordering (imports first)
- [ ] Conditional import handling (TYPE_CHECKING)
- [ ] Test-only dependencies (opt-in)

#### Enterprise Tier
- [ ] Dependency graph visualization (Mermaid)
- [ ] Custom dependency filters (deny/allow lists)
- [ ] Extraction templates (preset bundles)

**Target Date:** March 31, 2026

### v1.2 (Q2 2026): Language Expansion

#### All Tiers
- [ ] Rust function extraction
- [ ] Go function extraction
- [ ] PHP function extraction

#### Pro Tier
- [ ] Ruby method extraction
- [ ] Kotlin function extraction
- [ ] Cross-file resolution for JS/TS

**Target Date:** June 30, 2026

### v1.3 (Q3 2026): Performance Optimization

#### All Tiers
- [ ] Parallel batch extraction
- [ ] Streaming extraction (large symbols)
- [ ] Memory optimization

#### Pro Tier
- [ ] Incremental extraction (delta mode)
- [ ] Smart caching with invalidation

#### Enterprise Tier
- [ ] Distributed extraction across workers
- [ ] Real-time monitoring dashboard

**Target Date:** September 30, 2026

### v1.4 (Q4 2026): Advanced Features

#### Pro Tier
- [ ] Extract with documentation
- [ ] Extract with usage examples
- [ ] Extract with test coverage info

#### Enterprise Tier
- [ ] Extract with security context
- [ ] Extract with compliance metadata
- [ ] Custom post-extraction hooks

**Target Date:** December 31, 2026

---

## Troubleshooting

### Common Issues

#### Issue 1: "Symbol not found"
**Symptoms:** `{"success": false, "error": "Function 'foo' not found"}`  
**Cause:** Symbol name typo or not in file  
**Solution:**
```python
# Use analyze_code first to list available symbols
result = await analyze_code(file_path="utils.py")
print(result.functions)  # ['calculate_tax', 'format_currency']

# Then extract correct symbol
result = await extract_code(
    file_path="utils.py",
    target_name="calculate_tax"  # Correct name
)
```

#### Issue 2: "Method targets must use Class.method format"
**Symptoms:** Error when extracting method  
**Cause:** Forgot "Class.method" format  
**Solution:**
```python
# Wrong
extract_code(target_name="add")

# Correct
extract_code(target_name="Calculator.add")
```

#### Issue 3: "Cross-file deps requires PRO tier"
**Symptoms:** Tier limit error  
**Cause:** Community tier doesn't support cross-file resolution  
**Solution:**
```python
# Option 1: Upgrade to Pro tier
# Option 2: Extract dependencies manually
main_fn = await extract_code(file_path="main.py", target_name="process")
dep_fn = await extract_code(file_path="utils.py", target_name="helper")
# Combine manually
```

#### Issue 4: Missing decorators/docstrings
**Symptoms:** Extracted code incomplete  
**Cause:** Parsing error or edge case  
**Solution:**
```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
code-scalpel extract-code --file-path utils.py --target-name foo
```

### Debugging

**Enable Debug Mode:**
```bash
export LOG_LEVEL=DEBUG
export CODE_SCALPEL_VERBOSE=1

code-scalpel extract-code --file-path utils.py --target-name calculate_tax
```

**Debug Output:**
```
DEBUG: Loading file: utils.py
DEBUG: Detected language: python
DEBUG: Parsing AST...
DEBUG: Walking AST nodes...
DEBUG: Found FunctionDef: calculate_tax at line 15
DEBUG: Extracting decorators: none
DEBUG: Extracting docstring: "Calculate tax for a given amount."
DEBUG: Boundaries: lines 15-20
DEBUG: Extraction complete in 12ms
```

---

## References and Related Tools

### Related Code Scalpel Tools

- **analyze_code:** List all symbols in file (use before extract_code)
- **update_symbol:** Modify extracted code and write back
- **simulate_refactor:** Verify extracted code changes are safe
- **get_cross_file_dependencies:** Understand dependency chains
- **crawl_project:** Identify symbols to extract across project

### External References

- **Python AST:** https://docs.python.org/3/library/ast.html
- **Tree-sitter:** https://tree-sitter.github.io/tree-sitter/
- **React Hooks:** https://react.dev/reference/react

### Tools Referenced

- **tree-sitter-python:** https://github.com/tree-sitter/tree-sitter-python
- **tree-sitter-typescript:** https://github.com/tree-sitter/tree-sitter-typescript
- **tree-sitter-java:** https://github.com/tree-sitter/tree-sitter-java

### Further Reading

- **Tool Roadmap:** [docs/roadmap/extract_code.md](../roadmap/extract_code.md)
- **Token Efficiency Guide:** [docs/guides/token_efficiency.md](../guides/token_efficiency.md) (TBD)
- **Cross-File Resolution:** [docs/guides/cross_file_deps.md](../guides/cross_file_deps.md) (TBD)

---

## Document Metadata

**Template Version:** 1.0.0  
**Created:** 2026-01-03  
**Last Updated:** 2026-01-03  
**Maintained By:** Code Scalpel Documentation Team  
**Review Cycle:** Quarterly (next review: April 3, 2026)

**Change History:**
- 2026-01-03: Initial deep dive creation for `extract_code` v1.0 (Code Scalpel v3.3)

**Quality Checklist:**
- [x] All sections completed
- [x] Code examples align with roadmap specification
- [x] MCP request/response examples included
- [x] Tier behavior documented from roadmap and implementation
- [x] Known limitations documented
- [x] Roadmap integrated
- [ ] Performance benchmarks executed (pending)
- [ ] Test coverage verified (pending evidence gathering)
- [ ] Security audit completed (pending)
- [ ] Links validated (pending)
- [ ] Peer reviewed (pending)
- [ ] User tested (pending)

**Evidence Status:**
- ⏳ Test evidence gathering in progress
- ⏳ Performance benchmarks in progress
- ⏳ Security audit scheduled
- ✅ Roadmap integrated
- ✅ MCP examples verified against roadmap and implementation

---

**End of Document**

> **Note:** This deep dive document is based on the authoritative roadmap specification in `docs/roadmap/extract_code.md` dated December 30, 2025, and the implementation in `src/code_scalpel/mcp/server.py` (lines 9995-10200 and 12632-12850) and related extraction modules. Test evidence, performance benchmarks, and security audits are scheduled for completion during Q1 2026 evidence-gathering phase.
