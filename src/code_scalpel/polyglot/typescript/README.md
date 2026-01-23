# TypeScript Polyglot Module

**Purpose:** Advanced TypeScript and TSX analysis tools

## Overview

This subdirectory provides specialized analysis for TypeScript, including type system analysis, decorators, and type narrowing detection.

## Key Components

### analyzer.py (11,534 LOC)
**Core TypeScript analysis**

```python
class TypeScriptAnalyzer:
    def analyze(self, code: str) -> TypeScriptAnalysisResult:
        """Analyze TypeScript code structure and types."""
        pass
```

**Capabilities:**
- Type inference from assignments
- Interface and type alias detection
- Generic type parameter analysis
- Enum analysis
- Function signature analysis

### decorator_analyzer.py (10,051 LOC)
**Decorator and annotation analysis**

Analyzes TypeScript/Angular decorators:

```typescript
@Component({
    selector: 'app-root',
    template: '<div>Hello</div>'
})
export class AppComponent {}
```

**Detects:**
- Angular decorators (`@Component`, `@Injectable`, `@Input`)
- Custom decorators
- Decorator arguments and metadata
- Decorator stacking

### parser.py (14,677 LOC)
**TypeScript parser wrapper**

Wraps tree-sitter TypeScript parser with utilities:

```python
class TypeScriptParser:
    def parse(self, code: str) -> TSTree:
        """Parse TypeScript to tree-sitter AST."""
        pass
    
    def parse_tsx(self, code: str) -> TSTree:
        """Parse TSX (TypeScript + JSX)."""
        pass
```

**Features:**
- Error recovery
- Incremental parsing
- Position mapping (line/column)
- Node type queries

### type_narrowing.py (22,166 LOC)
**Type guard and narrowing analysis**

Analyzes TypeScript's type narrowing:

```typescript
function process(x: string | number) {
    if (typeof x === "string") {
        // x is string here
        return x.toUpperCase()
    } else {
        // x is number here
        return x.toFixed(2)
    }
}
```

**Detects:**
- `typeof` type guards
- `instanceof` checks
- Discriminated unions
- `in` operator narrowing
- User-defined type guards (`is` keyword)
- Control flow narrowing

**Example:**
```python
from code_scalpel.polyglot.typescript import TypeNarrowingAnalyzer

analyzer = TypeNarrowingAnalyzer()
result = analyzer.analyze(ts_code)

for guard in result.type_guards:
    print(f"Variable {guard.variable} narrowed from {guard.from_type} to {guard.to_type}")
```

## Usage Examples

### Type Analysis
```python
from code_scalpel.polyglot.typescript import TypeScriptAnalyzer

analyzer = TypeScriptAnalyzer()
result = analyzer.analyze("""
interface User {
    id: number;
    name: string;
}

function getUser(id: number): User {
    return { id, name: "John" };
}
""")

print(result.interfaces)  # [Interface(name='User', properties=[...])]
print(result.functions)   # [Function(name='getUser', return_type='User')]
```

### Decorator Analysis
```python
from code_scalpel.polyglot.typescript import DecoratorAnalyzer

analyzer = DecoratorAnalyzer()
result = analyzer.analyze(angular_component_code)

for decorator in result.decorators:
    print(f"{decorator.name}: {decorator.arguments}")
```

### Type Narrowing
```python
from code_scalpel.polyglot.typescript import TypeNarrowingAnalyzer

analyzer = TypeNarrowingAnalyzer()
result = analyzer.analyze(ts_function)

for guard in result.guards:
    print(f"Line {guard.line}: {guard.variable} narrowed to {guard.narrowed_type}")
```

## Integration

Used by:
- `mcp/server.py` - TypeScript-specific MCP tools
- `polyglot/extractor.py` - TypeScript code extraction
- `security/` - TypeScript security analysis (type evaporation detection)
- `ir/normalizers/typescript_normalizer.py` - TypeScript → IR

## TypeScript-Specific Features

### Type System Analysis
- Structural typing detection
- Nominal typing (classes)
- Generic constraints
- Conditional types
- Mapped types
- Template literal types

### Angular Support
- Component decorator analysis
- Dependency injection detection
- Template binding analysis
- Input/Output property detection

### React Support (TSX)
- Component prop types
- Hook type inference
- Context type analysis
- Generic component props

## v3.0.5 Status

- Analyzer: Stable, 90% coverage
- Parser: Stable, 95% coverage
- Decorator analyzer: Stable, 85% coverage
- Type narrowing: Beta, 80% coverage
