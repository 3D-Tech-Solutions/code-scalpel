# Intermediate Representation (IR) Module

**Purpose:** Language-agnostic code representation and normalization

## TODO ITEMS: IR Module (README.md)

### COMMUNITY TIER - Core Documentation
1. Add diagram showing IR node hierarchy (Statement, Expression inheritance)
2. Add example comparing Python vs JavaScript AST normalization
3. Document all node types with examples (IRFunctionDef, IRClassDef, etc.)
4. Add troubleshooting section for common normalization issues
5. Document IR limitations and design trade-offs
6. Add comparison with other IR systems (LLVM, Roslyn, etc.)
7. Create migration guide for adopting new IR versions
8. Add performance characteristics table (memory, speed)
9. Document AST → IR conversion pipeline in detail
10. Include code examples for accessing normalized IR properties
11. Add quick reference guide for node types
12. Add operator precedence charts for all languages
13. Add operator associativity documentation
14. Create FAQ section for common questions
15. Add error handling and exception documentation
16. Document scope resolution rules
17. Add closure and variable capture documentation
18. Document Python-specific IR mappings
19. Document JavaScript-specific IR mappings
20. Document TypeScript-specific IR mappings
21. Document Java-specific IR mappings
22. Add semantic differences table across languages
23. Create best practices guide for IR usage
24. Add debugging tips for IR analysis
25. Document IR node visitor patterns

### PRO TIER - Advanced Documentation
26. Add semantic analysis details (type inference, scope resolution)
27. Document extensibility points for custom analysis
28. Create advanced troubleshooting guide for edge cases
29. Add performance optimization tips and best practices
30. Document caching strategies for repeated normalizations
31. Create debugging guide for IR structure issues
32. Add cross-language equivalence examples (Python vs JavaScript)
33. Document type annotation preservation and usage
34. Create integration guide for analysis tools (PDG, security, symbolic)
35. Add benchmarking and profiling guide
36. Document memory usage characteristics
37. Add latency analysis for normalization
38. Create performance tuning guide
39. Document incremental IR updates
40. Add caching layer architecture
41. Document distributed IR processing
42. Create multi-language analysis guide
43. Add type inference algorithm documentation
44. Document control flow analysis on IR
45. Create data flow analysis documentation
46. Document symbolic execution on IR
47. Add pattern matching documentation
48. Create code clone detection guide
49. Document complexity metrics calculation
50. Add optimization hint generation guide

### ENTERPRISE TIER - Advanced Guidance
51. Add distributed IR processing architecture
52. Document polyglot analysis patterns and composition
53. Create enterprise deployment guide
54. Add federated IR sharing protocol documentation
55. Document ML optimization hints and training data
56. Create SLA and performance guarantees section
57. Add high-availability configuration guide
58. Document compliance and audit logging features
59. Add custom operator and node type registration guide
60. Create enterprise troubleshooting and support matrix
61. Add multi-tenancy architecture documentation
62. Document IR encryption for secure analysis
63. Create horizontal scaling guide
64. Add vertical scaling optimization guide
65. Document IR sharding strategies
66. Create backup and recovery procedures
67. Add disaster recovery guide
68. Document IR versioning for migrations
69. Create upgrade guide for major versions
70. Add deprecation policy documentation
71. Document semantic evolution tracking
72. Create language support roadmap
73. Add research papers and academic references
74. Document ML model training on IR
75. Create commercial licensing and support guide

## Overview

This module provides a unified intermediate representation (IR) for multiple programming languages, enabling polyglot analysis and transformation.

## Architecture

```
Source Code (Python/Java/JS/TS)
    ↓
Tree-sitter Parse
    ↓
Language-Specific Normalizer
    ↓
Unified IR (nodes.py)
    ↓
Semantic Analysis (semantics.py)
    ↓
Analysis Tools (PDG, Security, Symbolic Execution)
```

## Key Components

### nodes.py (20,775 LOC)
Unified IR node definitions:
- `IRNode` - Base class for all IR nodes
- `FunctionNode` - Function/method definitions
- `ClassNode` - Class/interface definitions
- `VariableNode` - Variable declarations
- `ExpressionNode` - Expressions (binary ops, calls, etc.)
- `StatementNode` - Statements (if, while, return, etc.)
- `TypeNode` - Type annotations

**Key Features:**
- Language-agnostic representation
- Preserves source location information
- Maintains parent-child relationships
- Supports annotations and metadata

### operators.py (3,255 LOC)
Operator definitions and semantics:
- `BinaryOp` - Binary operators (+, -, *, /, ==, !=, etc.)
- `UnaryOp` - Unary operators (-, !, ~, etc.)
- `LogicalOp` - Logical operators (and, or, not)
- `ComparisonOp` - Comparison operators (<, >, <=, >=, ==, !=)

### semantics.py (27,175 LOC)
Semantic analysis on IR:
- `SemanticAnalyzer` - Performs semantic checks
- Type inference
- Name resolution
- Scope analysis
- Dead code detection
- Constant folding

**Key Features:**
- Cross-language type inference
- Control flow analysis on IR
- Data flow analysis on IR
- Detects semantic errors (undefined variables, type mismatches)

## Normalizers

The `normalizers/` subdirectory contains language-specific normalizers that convert language ASTs to unified IR.

### python_normalizer.py (37,869 LOC)
Python AST → IR normalization:
- Handles Python-specific constructs (list comprehensions, decorators, with statements)
- Maps Python types to IR types
- Preserves Python semantics in IR

### java_normalizer.py (38,736 LOC)
Java AST → IR normalization:
- Handles Java-specific constructs (interfaces, generics, annotations)
- Maps Java types to IR types
- Preserves Java semantics (static vs instance, access modifiers)

### javascript_normalizer.py (61,362 LOC)
JavaScript/JSX AST → IR normalization:
- Handles JS-specific constructs (arrow functions, destructuring, async/await)
- JSX/React component normalization
- Prototype chain representation

### typescript_normalizer.py (13,939 LOC)
TypeScript AST → IR normalization:
- Handles TypeScript-specific constructs (interfaces, enums, generics)
- Type annotation preservation
- Extends JavaScript normalizer

### base.py (3,125 LOC)
Base normalizer interface:
- `Normalizer` - Abstract base class for all normalizers
- Common normalization utilities
- Visitor pattern implementation

### tree_sitter_visitor.py (13,122 LOC)
Tree-sitter AST traversal:
- `TreeSitterVisitor` - Generic visitor for tree-sitter ASTs
- Node type dispatching
- Recursive traversal with context

## Usage

```python
from code_scalpel.ir import IRNode, FunctionNode
from code_scalpel.ir.normalizers import PythonNormalizer, JavaNormalizer

# Normalize Python code
python_normalizer = PythonNormalizer()
python_ir = python_normalizer.normalize(python_ast)

# Normalize Java code
java_normalizer = JavaNormalizer()
java_ir = java_normalizer.normalize(java_ast)

# Both produce same IR structure
assert isinstance(python_ir, FunctionNode)
assert isinstance(java_ir, FunctionNode)

# Perform semantic analysis
from code_scalpel.ir.semantics import SemanticAnalyzer
analyzer = SemanticAnalyzer()
errors = analyzer.analyze(python_ir)
```

## Integration

Used by:
- `polyglot/` - Multi-language parsing
- `pdg_tools/` - PDG construction from IR
- `symbolic_execution_tools/` - Symbolic execution on IR
- `security/` - Security analysis on IR

## Benefits of IR

1. **Unified Analysis:** Write analysis once, run on multiple languages
2. **Simplified Tools:** PDG/symbolic execution don't need language-specific logic
3. **Cross-Language Analysis:** Analyze Python calling Java, JS calling TypeScript
4. **Maintenance:** Language changes don't affect analysis tools

## v3.0.5 Status

- IR structure: Stable, 100% coverage
- Python normalizer: Stable, 100% coverage
- Java normalizer: Stable, 95% coverage
- JavaScript normalizer: Stable, 90% coverage
- TypeScript normalizer: Stable, 90% coverage
- Semantic analysis: Beta, 85% coverage
