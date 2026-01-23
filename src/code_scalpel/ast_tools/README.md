# AST Tools

**Comprehensive AST analysis, transformation, and cross-file dependency extraction**

---

## Overview

This directory contains Code Scalpel's **advanced code analysis toolkit**. It provides:

- **AST Parsing & Analysis** - Extract structure, metrics, complexity
- **Code Transformation** - Safe refactoring with verification
- **Cross-File Analysis** - Import resolution, call graphs, dependencies
- **Security Analysis** - Vulnerability detection via taint analysis
- **Type Inference** - Type hint inference and validation
- **Control Flow Analysis** - CFG building and path exploration
- **Data Flow Analysis** - Def-use chains, dead code detection
- **Refactoring Analysis** - Code smell detection and opportunities

---

## Core Modules (6)

| Module | Purpose | Key Classes | Status |
|--------|---------|------------|--------|
| **analyzer.py** | Function/class metrics & analysis | `ASTAnalyzer`, `FunctionMetrics`, `ClassMetrics` | ✅ Stable |
| **builder.py** | AST construction from source | `ASTBuilder`, `NodeVisitor` | ✅ Stable |
| **transformer.py** | Safe AST transformations | `ASTTransformer`, `TransformerResult` | ✅ Stable |
| **validator.py** | Code validation & style checks | `ASTValidator`, `ValidationResult` | ✅ Stable |
| **utils.py** | AST utility functions | `ASTUtils`, helper functions | ✅ Stable |
| **visualizer.py** | AST visualization & export | `ASTVisualizer`, rendering functions | ✅ Stable |

---

## Cross-File Analysis Modules (4)

| Module | Purpose | Key Classes | Status |
|--------|---------|------------|--------|
| **import_resolver.py** | Import resolution across files | `ImportResolver`, `SymbolDefinition` | ✅ Stable |
| **call_graph.py** | Build and analyze call relationships | `CallGraphBuilder`, `CallGraphResult` | ✅ Stable |
| **cross_file_extractor.py** | Surgical symbol extraction with deps | `CrossFileExtractor`, `ExtractedSymbol` | ✅ Stable |
| **dependency_parser.py** | Dependency file parsing | `DependencyParser`, `Dependency` | ✅ Stable |

---

## Dependency Scanning Module (1)

| Module | Purpose | Key Classes | Status |
|--------|---------|------------|--------|
| **osv_client.py** | OSV vulnerability database client | `OSVClient`, `Vulnerability` | ✅ Stable |

---

## Advanced Analysis Modules (5 - New in v3.0.0)

| Module | Purpose | Key Classes | Status |
|--------|---------|------------|--------|
| **type_inference.py** | Type hint inference engine | `TypeInference`, `TypeInfo` | 🆕 Stub |
| **control_flow.py** | Control flow graph builder | `ControlFlowBuilder`, `BasicBlock` | 🆕 Stub |
| **data_flow.py** | Data flow analysis | `DataFlowAnalyzer`, `DataFlow` | 🆕 Stub |
| **ast_refactoring.py** | Refactoring analysis & patterns | `RefactoringAnalyzer`, `CodeSmell` | 🆕 Stub |

---

## Usage Examples

### Basic AST Analysis

```python
from code_scalpel.ast_tools import ASTAnalyzer

analyzer = ASTAnalyzer()
result = analyzer.analyze_file("src/handlers.py")

print(f"Functions: {len(result.functions)}")
print(f"Classes: {len(result.classes)}")
print(f"Complexity: {result.cyclomatic_complexity}")
```

### Cross-File Extraction

```python
from code_scalpel.ast_tools import CrossFileExtractor

extractor = CrossFileExtractor()
symbol = extractor.extract_symbol(
    file="src/services/order.py",
    symbol_name="process_order"
)

print(f"Found: {symbol.name}")
print(f"Dependencies: {symbol.dependencies}")
print(f"Code:\n{symbol.code}")
```

### Call Graph Building

```python
from code_scalpel.ast_tools import CallGraphBuilder

builder = CallGraphBuilder()
graph = builder.build_from_project("src/")

print(f"Nodes: {len(graph.nodes)}")
print(f"Edges: {len(graph.edges)}")
print(f"Entry points: {graph.entry_points}")
```

### Code Transformation (Safe)

```python
from code_scalpel.ast_tools import ASTTransformer

transformer = ASTTransformer()
result = transformer.transform_code(
    original_code=old_code,
    transformations=[rename_function, extract_method]
)

if result.is_safe:
    new_code = result.transformed_code
else:
    print(f"Unsafe: {result.issues}")
```

### Type Inference

```python
from code_scalpel.ast_tools import TypeInference

inferencer = TypeInference()
hints = inferencer.infer_types("src/models.py")

for var_name, type_info in hints.items():
    print(f"{var_name}: {type_info.type_annotation}")
```

### Control Flow Analysis

```python
from code_scalpel.ast_tools import ControlFlowBuilder

builder = ControlFlowBuilder()
cfg = builder.build("src/business_logic.py")

paths = cfg.get_all_paths()
loops = cfg.find_loops()
dominators = cfg.find_dominators()
```

### Data Flow Analysis

```python
from code_scalpel.ast_tools import DataFlowAnalyzer

analyzer = DataFlowAnalyzer()
analysis = analyzer.analyze("src/app.py")

reaching_defs = analysis.get_reaching_definitions(line=42)
live_vars = analysis.get_live_variables(line=42)
dead_code = analysis.find_dead_code()
```

### Refactoring Analysis

```python
from code_scalpel.ast_tools import RefactoringAnalyzer

analyzer = RefactoringAnalyzer()
smells = analyzer.analyze("src/old_code.py")

for smell in smells:
    print(f"{smell.type}: {smell.description}")
    print(f"Refactoring: {smell.suggested_refactoring}")
```

---

## Integration with MCP Tools

AST Tools power these MCP tools:

| MCP Tool | Uses | Purpose |
|----------|------|---------|
| `analyze_code` | ASTAnalyzer | Parse code structure |
| `extract_code` | CrossFileExtractor | Extract symbols with deps |
| `get_file_context` | Analyzer | Get file overview |
| `get_symbol_references` | CallGraphBuilder | Find all usages |
| `get_call_graph` | CallGraphBuilder | Trace function calls |
| `get_project_map` | Analyzer + CallGraph | Project structure |
| `simulate_refactor` | ASTTransformer | Test changes safely |
| `update_symbol` | Transformer | Apply safe changes |
| `scan_dependencies` | OSVClient | Check for CVEs |

---

## Architecture

```
Source Code
    ↓
ASTBuilder (parse to AST)
    ↓
┌──────────────────────────────────────┐
│  Analysis Modules (parallel)         │
├──────────────────────────────────────┤
│ • ASTAnalyzer                        │
│ • CallGraphBuilder                   │
│ • ImportResolver                     │
│ • TypeInference                      │
│ • ControlFlowBuilder                 │
│ • DataFlowAnalyzer                   │
│ • RefactoringAnalyzer                │
│ • SecurityAnalyzer                   │
└──────────────────────────────────────┘
    ↓
Synthesis of Results
    ↓
Agent Actions (refactor, document, test, etc.)
```

---

## Capability Matrix

| Capability | Module | Status | Effort |
|-----------|--------|--------|--------|
| Parse Python | builder.py | ✅ | Done |
| Calculate complexity | analyzer.py | ✅ | Done |
| Extract functions | cross_file_extractor.py | ✅ | Done |
| Build call graphs | call_graph.py | ✅ | Done |
| Resolve imports | import_resolver.py | ✅ | Done |
| Infer types | type_inference.py | 🆕 | In progress |
| Build CFG | control_flow.py | 🆕 | In progress |
| Analyze data flow | data_flow.py | 🆕 | In progress |
| Detect code smells | ast_refactoring.py | 🆕 | In progress |
| Validate code | validator.py | ✅ | Done |
| Transform AST | transformer.py | ✅ | Done |
| Scan dependencies | osv_client.py | ✅ | Done |

---

---

## Data Flow

### Input (FROM)
```
Code Parser (code_parser/)
    ↓ (raw code, detected language)
Source Files (any supported language)
    ↓ (Python, Java, JS/TS, Go, etc.)
MCP Server (mcp_server.py)
    ↓ (tool invocation)
Agents (agents/)
```

### Processing (WITHIN)
```
AST Input (normalized AST)
    ↓ (parallel analysis)
    ├─ ASTAnalyzer (metrics, complexity)
    ├─ CallGraphBuilder (function relationships)
    ├─ ImportResolver (import graph)
    ├─ TypeInference (type hints)
    ├─ ControlFlowBuilder (CFG, paths)
    ├─ DataFlowAnalyzer (def-use chains)
    ├─ RefactoringAnalyzer (code smells)
    └─ SecurityAnalyzer (vulnerabilities)
    ↓ (synthesis)
Multi-dimensional Analysis Results
```

### Output (TO)
```
Analysis Results
    ├─ Metrics (complexity, coupling, cohesion)
    ├─ Relationships (call graph, import graph)
    ├─ Type Information (hints, signatures)
    ├─ Control Flow (CFG, paths, loops)
    ├─ Data Flow (def-use, live vars, dead code)
    ├─ Code Smells (God Class, Feature Envy, etc.)
    └─ Security Issues (vulnerabilities, taint flows)
    ↓
Agents (agents/)
    ↓
MCP Tools (extract_code, simulate_refactor, etc.)
    ↓
User / Claude / Copilot
```

---

## Feature Roadmap by Tier

### TIER 1: COMMUNITY FEATURES (Free, High Priority)

**Foundation capabilities** for code analysis and transformation:

#### Core Analysis
- Basic AST parsing and metrics (analyzer.py)
- Function/class information extraction (utils.py)
- Simple code validation (validator.py)
- Basic visualization (visualizer.py)

#### Import & Call Analysis
- Single-file import resolution (import_resolver.py)
- Call graph building (call_graph.py)
- Basic cross-file extraction (cross_file_extractor.py)

#### Transformation
- Variable and function renaming (transformer.py)
- Basic AST traversal and visiting
- Type hint extraction (type_inference.py)

#### Dependency Scanning
- Single package vulnerability queries (osv_client.py)
- Batch vulnerability checking (100+ packages)
- CVSS severity classification

**Test Coverage Target:** 400+ tests across TIER 1 features
**Implementation Status:** 80% complete (ready for community release)

---

### TIER 2: PRO FEATURES (Commercial, Medium Priority)

**Advanced capabilities** for enterprise code analysis:

#### Advanced Analysis
- Complex code metrics and complexity scoring (analyzer.py)
- Data flow analysis with reaching definitions (data_flow.py)
- Control flow graph building (control_flow.py)
- Comprehensive validation rules (validator.py)

#### Cross-File Analysis
- Import cycle detection (import_resolver.py, call_graph.py)
- Framework-specific pattern recognition (all modules)
- Confidence-based symbol extraction (cross_file_extractor.py)
- Dynamic call detection (call_graph.py)

#### Type System
- Type inference from assignments and operations (type_inference.py)
- Function return type inference
- Class attribute typing
- Type hint generation with formatting

#### Transformation & Refactoring
- Method extraction from code blocks (transformer.py)
- Variable inlining and simplification
- Pattern matching with wildcards
- Transformation composition

#### Visualization & Reporting
- Interactive HTML visualization (visualizer.py)
- Diff visualization between ASTs
- Side-by-side source and AST view
- Multiple export formats (SVG, PDF)

#### Dependency Scanning
- Vulnerability caching with TTL (osv_client.py)
- Ecosystem-specific scoring (PyPI, npm, Maven)
- Advisory enrichment with CVSS and CWE
- Batch deduplication and aggregation
- Local vulnerability database fallback

**Test Coverage Target:** 650+ tests across TIER 2 features
**Implementation Status:** 50% complete (in development)

---

### TIER 3: ENTERPRISE FEATURES (Commercial, Lower Priority)

**State-of-the-art capabilities** for advanced users:

#### ML-Based Analysis
- ML-based type prediction (type_inference.py)
- Vulnerability exploitability prediction (osv_client.py)
- Code anomaly detection (validator.py)
- Refactoring opportunity suggestions (transformer.py)

#### Advanced Transformation
- Semantic-preserving optimizations (transformer.py)
- Type-aware transformations with validation
- Transformation rollback and undo support

#### Advanced Graph Analysis
- Symbolic execution for path exploration
- Dominance analysis and reachability (control_flow.py)
- Interprocedural data flow analysis (data_flow.py)
- Protocol and structural typing (type_inference.py)

#### Visualization & IDE Integration
- 3D visualization with interactive exploration (visualizer.py)
- LSP integration for real-time analysis
- Performance profiling visualization
- Subgraph clustering by module

#### Dependency Analysis
- Vulnerability remediation recommendations (osv_client.py)
- Vulnerability trend analysis and prediction
- Integration with dependency lock files
- Automated security reports

**Test Coverage Target:** 500+ tests across TIER 3 features
**Implementation Status:** 20% complete (research phase)

**Total Test Coverage Across All Tiers:** 1,550+ tests

---
- [ ] Generic type parameter inference
- [ ] Protocol/interface inference
- [ ] Overload resolution
- [ ] Type guard detection
- [ ] Callable type inference
- [ ] Type annotation validation
- [ ] Forward reference resolution
- [ ] Cross-module type consistency
- [ ] Type stub generation
- [ ] Type narrowing analysis
- [ ] Variance handling (covariant/contravariant)
- [ ] Structural subtyping
- [ ] Nominal type support
- [ ] Type hint generation for legacy code

#### Control Flow Analysis (15 TODOs)
- [ ] Basic block identification
- [ ] Dominance frontier computation
- [ ] Loop invariant analysis
- [ ] Loop normalization (rotate, peel, etc.)
- [ ] Irreducible flow handling
- [ ] Exception handling in CFG
- [ ] Async/await control flow
- [ ] Function call sites in CFG
- [ ] Reachability analysis
- [ ] Dead code detection via CFG
- [ ] Path counting & complexity
- [ ] Cyclomatic complexity (classic)
- [ ] Modified condition/decision coverage
- [ ] Condition/decision coverage
- [ ] Interactive CFG visualization

#### Data Flow Analysis (13 TODOs)
- [ ] Reaching definitions computation
- [ ] Live variable analysis
- [ ] Def-use chain generation
- [ ] Use-def chain generation
- [ ] Dead code elimination
- [ ] Unused variable detection
- [ ] Uninitialized variable detection
- [ ] Data dependency graph
- [ ] Memory alias analysis
- [ ] Taint analysis for security
- [ ] Variable lifetime analysis
- [ ] SSA (Static Single Assignment) form
- [ ] Available expression analysis

#### Refactoring Analysis (25 TODOs)
- [ ] God Class detection
- [ ] God Function detection
- [ ] Feature Envy detection
- [ ] Data Clump detection
- [ ] Long Parameter List detection
- [ ] Duplicated Code detection
- [ ] Dead Code detection
- [ ] Primitive Obsession detection
- [ ] Temporary Field detection
- [ ] Lazy Class detection
- [ ] Speculative Generality detection
- [ ] Message Chains detection
- [ ] Middle Man detection
- [ ] Divergent Change detection
- [ ] Shotgun Surgery detection
- [ ] Parallel Inheritance detection
- [ ] Alternative Classes detection
- [ ] Incomplete Library Classes detection
- [ ] Data Classes detection
- [ ] Refused Bequest detection
- [ ] Extract Method suggestion
- [ ] Extract Class suggestion
- [ ] Replace Magic Numbers suggestion
- [ ] Introduce Parameter Object suggestion
- [ ] Preserve Whole Object suggestion

### Phase 3: Performance & Scale (Future)
- [ ] Incremental analysis for file changes
- [ ] Caching layer with invalidation
- [ ] Parallel processing for large projects
- [ ] Memory optimization for deep analysis
- [ ] Timeout handling for complex code
- [ ] Analysis result persistence
- [ ] Streaming analysis for pipelines

---

## Configuration

```python
from code_scalpel.ast_tools import ASTAnalyzer

analyzer = ASTAnalyzer(
    include_metrics=True,           # Calculate complexity
    follow_imports=True,            # Resolve cross-file
    cache_results=True,             # Cache AST
    max_depth=10,                   # Recursion limit
    timeout_seconds=300             # Analysis timeout
)
```

---

## Data Flow

### AST Analysis Pipeline
```
Source Code
    ↓
ASTBuilder.build()
    ├─ Tokenize source
    ├─ Parse to AST
    └─ Validate syntax
    ↓
AST Tree
    ↓
ASTAnalyzer.analyze()
    ├─ Extract functions
    ├─ Extract classes
    ├─ Calculate metrics (complexity, LOC)
    ├─ Identify patterns
    └─ Build symbol table
    ↓
Code Metrics & Structure
```

### Cross-File Extraction
```
Target Symbol + Project Root
    ↓
CrossFileExtractor.extract()
    ├─ Locate symbol definition
    ├─ Resolve imports used
    │  ├─ Built-in modules
    │  ├─ Standard library
    │  ├─ Third-party packages
    │  └─ Local imports
    │
    ├─ Extract dependent symbols
    │  ├─ Called functions
    │  ├─ Used classes
    │  ├─ Type references
    │  └─ Constants
    │
    └─ Build dependency graph
    ↓
Complete Symbol with Dependencies
```

### Call Graph Generation
```
Project Root
    ↓
CallGraphBuilder.build()
    ├─ Identify entry points (main, routes, etc.)
    ├─ Follow function calls
    │  ├─ Direct calls
    │  ├─ Method calls
    │  ├─ Lambda expressions
    │  └─ Higher-order functions
    │
    ├─ Resolve references across files
    ├─ Detect circular dependencies
    └─ Build graph
    ↓
Call Graph (Nodes + Edges + Cycles)
```

### Dependency Scanning
```
Dependency Files
├─ requirements.txt
├─ setup.py
├─ Pipfile
├─ package.json
└─ pom.xml
    ↓
DependencyParser.parse()
    ├─ Extract packages + versions
    ├─ Query OSV database
    ├─ Match against CVE database
    └─ Calculate risk
    ↓
Vulnerability Report
```

---

## Development Roadmap

### Phase 1: Type System Enhancement (In Progress 🔄)

#### Type Inference (12 TODOs)
- [ ] Return type inference
- [ ] Parameter type inference
- [ ] Variable type tracking
- [ ] Generic type support
- [ ] Union type handling
- [ ] Optional/nullable types
- [ ] Callable type inference
- [ ] Protocol/structural typing
- [ ] Type narrowing in conditions
- [ ] Type guard detection
- [ ] Assertion propagation
- [ ] Type stub generation

#### Control Flow Analysis (10 TODOs)
- [ ] Dominance frontier calculation
- [ ] Loop detection & classification
- [ ] Conditional path analysis
- [ ] Exception handling graph
- [ ] Return value tracking
- [ ] Unreachable code detection
- [ ] Infinite loop detection
- [ ] Control dependence computation
- [ ] Reachability analysis
- [ ] Guard condition extraction

#### Data Flow Analysis (10 TODOs)
- [ ] Def-use chain computation
- [ ] Live variable analysis
- [ ] Available expression analysis
- [ ] Reaching definition analysis
- [ ] Dead code detection
- [ ] Unused variable detection
- [ ] Variable escaping analysis
- [ ] Alias analysis
- [ ] Points-to analysis
- [ ] Data dependence computation

### Phase 2: Refactoring & Transformation (Planned)

#### Refactoring Opportunities (15 TODOs)
- [ ] Extract method detection
- [ ] Extract class patterns
- [ ] Move method suggestions
- [ ] Duplicate code detection
- [ ] Long method detection
- [ ] Long parameter list detection
- [ ] Data clumps detection
- [ ] Primitive obsession detection
- [ ] Switch statement polymorphism
- [ ] Temporary field detection
- [ ] Message chains detection
- [ ] Middle man detection
- [ ] Feature envy detection
- [ ] Data class detection
- [ ] Divergent change detection

#### Advanced Transformations (12 TODOs)
- [ ] Safe rename refactoring
- [ ] Extract variable refactoring
- [ ] Inline variable refactoring
- [ ] Move field refactoring
- [ ] Introduce parameter object
- [ ] Replace parameter with method
- [ ] Introduce service parameter
- [ ] Remove parameter
- [ ] Split parameter
- [ ] Preserve whole object
- [ ] Replace array with object
- [ ] Change function declaration

#### Transformation Safety (8 TODOs)
- [ ] Semantic equivalence verification
- [ ] Behavior preservation checking
- [ ] Type safety verification
- [ ] Reference integrity validation
- [ ] Scope correctness checking
- [ ] Dependency impact analysis
- [ ] Performance regression detection
- [ ] Backward compatibility checking

### Phase 3: Advanced Analysis (Future)

#### Architecture Analysis (12 TODOs)
- [ ] Module dependency graphs
- [ ] Layering violation detection
- [ ] Coupling metrics calculation
- [ ] Cohesion metrics calculation
- [ ] Architectural pattern detection
- [ ] Design pattern recognition
- [ ] Anti-pattern detection
- [ ] Circular dependency resolution
- [ ] Module reachability analysis
- [ ] Module isolation measurement
- [ ] API surface analysis
- [ ] Public/private interface validation

#### Performance Analysis (10 TODOs)
- [ ] Algorithmic complexity estimation
- [ ] Big-O analysis
- [ ] Hot code path identification
- [ ] Memory usage estimation
- [ ] Caching opportunity detection
- [ ] Loop optimization suggestions
- [ ] Parallel execution opportunities
- [ ] I/O optimization detection
- [ ] Database query optimization
- [ ] Resource leak detection

---

## Performance Considerations

- **Large Files:** Incremental analysis recommended (WIP)
- **Circular Imports:** Detected and handled gracefully
- **Type Inference:** Expensive, use caching (WIP)
- **Call Graphs:** O(n²) for large projects, pruning recommended

---

## Best Practices

1. **Use CrossFileExtractor** for accurate symbol extraction
2. **Cache imports** when analyzing multiple files
3. **Prune call graphs** for large projects
4. **Validate transformations** before applying
5. **Check dependencies** for CVEs before merging

---

## File Structure

```
ast_tools/
├── README.md                    [This file]
├── __init__.py                  [Exports all modules]
├── analyzer.py                  [AST analysis]
├── builder.py                   [AST building]
├── transformer.py               [AST transformation]
├── validator.py                 [Code validation]
├── utils.py                     [Utilities]
├── visualizer.py                [AST visualization]
├── import_resolver.py           [Import resolution]
├── call_graph.py                [Call graph building]
├── cross_file_extractor.py      [Symbol extraction]
├── dependency_parser.py         [Dependency parsing]
├── osv_client.py                [Vulnerability scanning]
├── type_inference.py            [Type inference]
├── control_flow.py              [Control flow analysis]
├── data_flow.py                 [Data flow analysis]
└── ast_refactoring.py           [Refactoring analysis]
```

---

**Last Updated:** December 21, 2025  
**Version:** v3.0.0  
**Status:** 11 Stable ✅ + 4 Stubs 🆕 (Total TODOs: 98)
