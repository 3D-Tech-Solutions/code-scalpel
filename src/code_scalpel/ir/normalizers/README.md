# IR Normalizers Module

**Purpose:** Language-specific AST → IR normalization

## Overview

This directory contains normalizers that convert language-specific Abstract Syntax Trees (ASTs) to the unified Intermediate Representation (IR) defined in `ir/nodes.py`.

## Normalizers

### base.py (3,125 LOC)
**Base normalizer interface and utilities**

```python
class Normalizer(ABC):
    @abstractmethod
    def normalize(self, ast: Any) -> IRNode:
        """Convert language AST to IR."""
        pass
```

### python_normalizer.py (37,869 LOC)
**Python AST → IR**

Handles:
- Functions and methods → `FunctionNode`
- Classes → `ClassNode`
- List comprehensions → `ListCompNode`
- Decorators → `DecoratorNode`
- Context managers (`with`) → `WithNode`
- Async/await → `AsyncFunctionNode`

### java_normalizer.py (38,736 LOC)
**Java AST → IR**

Handles:
- Classes and interfaces → `ClassNode`
- Methods → `FunctionNode`
- Generics → `GenericTypeNode`
- Annotations → `AnnotationNode`
- Static vs instance members
- Access modifiers (public, private, protected)

### javascript_normalizer.py (61,362 LOC)
**JavaScript/JSX AST → IR**

Handles:
- Functions and arrow functions → `FunctionNode`
- Classes and prototypes → `ClassNode`
- JSX elements → `JSXNode`
- React components → `ComponentNode`
- Destructuring → expanded assignments
- Async/await → `AsyncFunctionNode`
- Template literals → string operations

### typescript_normalizer.py (13,939 LOC)
**TypeScript AST → IR**

Extends JavaScript normalizer with:
- Interfaces → `InterfaceNode`
- Enums → `EnumNode`
- Type annotations → `TypeNode`
- Generics → `GenericTypeNode`
- Type guards → control flow constraints

### tree_sitter_visitor.py (13,122 LOC)
**Generic tree-sitter traversal**

Provides visitor pattern for tree-sitter ASTs:
- Node type dispatching
- Recursive traversal
- Context management (parent nodes, scope)

## Usage

```python
from code_scalpel.ir.normalizers import (
    PythonNormalizer,
    JavaNormalizer,
    JavaScriptNormalizer,
    TypeScriptNormalizer
)

# Python
python_normalizer = PythonNormalizer()
python_ir = python_normalizer.normalize(python_ast)

# Java
java_normalizer = JavaNormalizer()
java_ir = java_normalizer.normalize(java_ast)

# JavaScript
js_normalizer = JavaScriptNormalizer()
js_ir = js_normalizer.normalize(js_ast)

# TypeScript
ts_normalizer = TypeScriptNormalizer()
ts_ir = ts_normalizer.normalize(ts_ast)
```

## Normalization Rules

### Common Patterns

| Source Language | IR Representation |
|----------------|-------------------|
| Function/Method | `FunctionNode` |
| Class/Interface | `ClassNode` |
| Variable Declaration | `VariableNode` |
| Binary Operation | `BinaryOpNode` |
| Function Call | `CallNode` |
| If Statement | `IfNode` |
| Loop | `WhileNode` / `ForNode` |

### Language-Specific Mappings

**Python:**
- `def foo():` → `FunctionNode`
- `class Foo:` → `ClassNode`
- `[x for x in y]` → `ListCompNode`
- `@decorator` → `DecoratorNode`

**Java:**
- `public void foo() {}` → `FunctionNode(visibility=public)`
- `interface Foo {}` → `InterfaceNode`
- `@Override` → `AnnotationNode`
- `List<String>` → `GenericTypeNode`

**JavaScript:**
- `function foo() {}` → `FunctionNode`
- `const foo = () => {}` → `FunctionNode(is_arrow=true)`
- `<Button />` → `JSXNode`
- `` `Hello ${name}` `` → `BinaryOpNode('+', 'Hello ', name)`

**TypeScript:**
- `interface Foo {}` → `InterfaceNode`
- `enum Color {}` → `EnumNode`
- `function foo(): number {}` → `FunctionNode(return_type=number)`

## Integration

Called by:
- `polyglot/` parsers
- `ir/semantics.py` for semantic analysis
- `pdg_tools/builder.py` for PDG construction

## v3.0.5 Status

- Python: Stable, 100% coverage
- Java: Stable, 95% coverage
- JavaScript: Stable, 90% coverage
- TypeScript: Stable, 90% coverage
