# Polyglot Module

**Purpose:** Modern multi-language parsing and analysis using tree-sitter

## Overview

This module provides unified parsing and analysis for multiple programming languages using tree-sitter, with special support for TypeScript/JavaScript ecosystems.

**Key Difference from `code_parsers/`:**
- **polyglot/** uses tree-sitter (modern, fast, error-tolerant)
- **code_parsers/** uses language-specific parsers (legacy)

## Key Components
    
### extractor.py (18,613 LOC)
**Polyglot code extraction**

Surgically extract functions, classes, methods across languages:
```python
class PolyglotExtractor:
    def extract_function(self, code: str, name: str, language: str) -> str:
        """Extract function by name from any supported language."""
        pass
```

**Supported Languages:**
- Python
- JavaScript/JSX
- TypeScript/TSX
- Java
- Go
- Rust
- Ruby
- PHP

### alias_resolver.py (10,341 LOC)
**Import alias resolution**

Resolves import aliases across languages:
```python
from models import User as U  # Python
import { User as U } from './models'  // TypeScript
```

### contract_breach_detector.py (10,956 LOC)
**API contract violation detection**

Detects when function calls don't match expected signatures:
```python
# Expected: foo(x: int, y: int) -> int
foo("string", [1, 2, 3])  # ❌ Contract breach detected
```

### tsx_analyzer.py (5,709 LOC)
**React TSX component analysis**

Specialized analyzer for React components:
- Component prop types
- Hook usage analysis
- Server Components detection (Next.js)
- Server Actions detection (`'use server'`)

## TypeScript Subdirectory

Advanced TypeScript/JSX analysis tools.

### typescript/analyzer.py (11,534 LOC)
**TypeScript-specific analysis**

```python
class TypeScriptAnalyzer:
    def analyze_types(self, code: str) -> TypeAnalysisResult:
        """Analyze TypeScript type system usage."""
        pass
```

**Capabilities:**
- Type inference
- Generic type analysis
- Interface conformance checking
- Enum analysis

### typescript/decorator_analyzer.py (10,051 LOC)
**Decorator analysis**

Analyzes TypeScript/Angular decorators:
```typescript
@Component({selector: 'app-root'})
@Injectable()
class AppComponent {}
```

### typescript/parser.py (14,677 LOC)
**TypeScript parser wrapper**

Wraps tree-sitter TypeScript parser:
```python
class TypeScriptParser:
    def parse(self, code: str) -> TSTree:
        """Parse TypeScript code into tree-sitter AST."""
        pass
```

### typescript/type_narrowing.py (22,166 LOC)
**Type narrowing analysis**

Analyzes TypeScript type guards and narrowing:
```typescript
if (typeof x === "string") {
    // x is narrowed to string here
    x.toLowerCase()
}
```

## Usage

```python
from code_scalpel.polyglot import PolyglotExtractor

# Extract function from any language
extractor = PolyglotExtractor()
func_code = extractor.extract_function(
    code=source_code,
    name="process_order",
    language="typescript"
)

# TypeScript-specific analysis
from code_scalpel.polyglot.typescript import TypeScriptAnalyzer
analyzer = TypeScriptAnalyzer()
result = analyzer.analyze_types(ts_code)
print(f"Interfaces: {result.interfaces}")
print(f"Generics: {result.generics}")

# React component analysis
from code_scalpel.polyglot import tsx_analyzer
component_info = tsx_analyzer.analyze_component(tsx_code)
print(f"Component type: {component_info.component_type}")
print(f"Props: {component_info.props}")
```

## Language Support Matrix

| Language | Parser | Normalizer | Extractor | Analyzer |
|----------|--------|------------|-----------|----------|
| Python | ✓ | ✓ | ✓ | ✓ |
| JavaScript | ✓ | ✓ | ✓ | ✓ |
| TypeScript | ✓ | ✓ | ✓ | ✓ |
| JSX | ✓ | ✓ | ✓ | ✓ |
| TSX | ✓ | ✓ | ✓ | ✓ |
| Java | ✓ | ✓ | ✓ | Partial |
| Go | ✓ | Partial | ✓ | Planned |
| Rust | ✓ | Planned | ✓ | Planned |

## Integration

Used by:
- `mcp/server.py` - MCP tool: `extract_code`
- `surgical_extractor.py` - Multi-language code extraction
- `ir/normalizers/` - IR normalization
- `security/` - Cross-language security analysis

## Migration from code_parser

**Old (code_parser):**
```python
from code_scalpel.code_parser.python_parsers import PythonParser
parser = PythonParser()
ast = parser.parse(code)
```

**New (polyglot):**
```python
from code_scalpel.polyglot import PolyglotExtractor
extractor = PolyglotExtractor()
code = extractor.extract_function(source, "foo", "python")
```

## v3.0.5 Status

- Core polyglot: Stable, 95% coverage
- TypeScript: Stable, 90% coverage
- JSX/TSX: Stable, 90% coverage
- Contract detection: Beta, 80% coverage
- Alias resolution: Stable, 95% coverage
