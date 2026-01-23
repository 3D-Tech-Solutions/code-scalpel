# PDG Tools Module

**Purpose:** Program Dependence Graph (PDG) construction and analysis

## Overview

This module provides tools for building and analyzing Program Dependence Graphs, which combine control flow and data flow information for program analysis.

## Key Components

### builder.py (19,232 LOC)
**PDG construction from AST/IR**

```python
class PDGBuilder:
    def build_pdg(self, ast: AST) -> PDG:
        """Build PDG from AST."""
        # 1. Build Control Flow Graph (CFG)
        # 2. Compute data dependencies
        # 3. Create PDG nodes and edges
        pass
```

**Key Features:**
- Control dependence analysis
- Data dependence analysis (def-use chains)
- Interprocedural PDG construction
- Handles exceptions and error paths

### analyzer.py (24,927 LOC)
**PDG analysis algorithms**

```python
class PDGAnalyzer:
    def analyze_dependencies(self, pdg: PDG) -> AnalysisResult:
        """Analyze PDG for patterns."""
        pass
```

**Capabilities:**
- Dead code detection (unreachable nodes)
- Dependency cycle detection
- Critical path analysis
- Variable lifetime analysis
- Def-use chain analysis

### slicer.py (14,841 LOC)
**Program slicing on PDG**

```python
class PDGSlicer:
    def slice_backward(self, pdg: PDG, criterion: Node) -> Set[Node]:
        """Compute backward slice from criterion."""
        pass
    
    def slice_forward(self, pdg: PDG, criterion: Node) -> Set[Node]:
        """Compute forward slice from criterion."""
        pass
```

**Key Features:**
- Backward slicing (what affects this variable?)
- Forward slicing (what does this variable affect?)
- Dynamic slicing with execution traces
- Interprocedural slicing

### transformer.py (25,086 LOC)
**PDG transformations and optimizations**

```python
class PDGTransformer:
    def optimize(self, pdg: PDG) -> PDG:
        """Apply optimizations to PDG."""
        pass
```

**Transformations:**
- Dead code elimination
- Constant propagation
- Common subexpression elimination
- Loop optimization
- Inlining

### utils.py (12,356 LOC)
**PDG utilities and helpers**

- Node creation helpers
- Edge management
- Graph traversal utilities
- Serialization/deserialization

### visualizer.py (20,403 LOC)
**PDG visualization**

```python
class PDGVisualizer:
    def to_dot(self, pdg: PDG) -> str:
        """Convert PDG to Graphviz DOT format."""
        pass
    
    def to_mermaid(self, pdg: PDG) -> str:
        """Convert PDG to Mermaid diagram."""
        pass
```

**Output Formats:**
- Graphviz DOT
- Mermaid diagrams
- JSON graph structure
- Interactive HTML

## Usage

```python
from code_scalpel.pdg_tools import PDGBuilder, PDGAnalyzer, PDGSlicer

# Build PDG from code
builder = PDGBuilder()
pdg = builder.build_pdg(ast)

# Analyze dependencies
analyzer = PDGAnalyzer()
result = analyzer.analyze_dependencies(pdg)
print(f"Dead code nodes: {result.dead_code}")

# Perform backward slicing
slicer = PDGSlicer()
slice_nodes = slicer.slice_backward(pdg, criterion=target_node)
print(f"Variables affecting target: {slice_nodes}")

# Visualize
from code_scalpel.pdg_tools import PDGVisualizer
visualizer = PDGVisualizer()
dot_graph = visualizer.to_dot(pdg)
```

## PDG Structure

```
PDG Node:
  - id: unique identifier
  - type: statement, expression, control
  - ast_node: reference to original AST node
  - line: source line number

PDG Edge:
  - source: source node
  - target: target node
  - type: control_dep, data_dep
  - label: condition, variable name
```

## Integration

Used by:
- `mcp/server.py` - MCP tool: `build_pdg`
- `symbolic_execution_tools/` - PDG-based symbolic execution
- `generators/` - Test generation and refactoring
- `security/` - Taint analysis on PDG

## Benefits of PDG

1. **Comprehensive Analysis:** Combines control + data dependencies
2. **Program Slicing:** Extract relevant code for debugging
3. **Optimization:** Identify optimization opportunities
4. **Security:** Track taint flow through program

## v3.0.5 Status

- Builder: Stable, 100% coverage
- Analyzer: Stable, 100% coverage
- Slicer: Stable, 100% coverage
- Transformer: Beta, 85% coverage
- Visualizer: Stable, 90% coverage
