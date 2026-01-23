# Code Parser (Polyglot Parsing System)

**Comprehensive parsing and normalization for 10 programming languages with 40+ parser strategies**

---

## Overview

This directory contains Code Scalpel's **universal parsing system**. It provides:

- **Multi-Language Support** - Python, Java, JavaScript/TypeScript, Go, C#, C++, Kotlin, Ruby, Swift, PHP
- **Multiple Parser Strategies** - 40+ implementations per language (native, linters, analysis tools)
- **Factory Pattern** - Automatic language detection and parser selection
- **Normalized Output** - Consistent AST representation across languages
- **Strategy Selection** - Use best parser for each analysis task

---

## Supported Languages & Strategies

### Python (13 Strategies)
- `python_parsers_ast.py` - Native Python AST ✅
- `python_parsers_bandit.py` - Security-focused scanning
- `python_parsers_mypy.py` - Type checking
- `python_parsers_pylint.py` - Comprehensive linting
- `python_parsers_ruff.py` - Fast linting (Rust-based)
- `python_parsers_flake8.py` - PEP8 style checking
- `python_parsers_pydocstyle.py` - Docstring checking
- `python_parsers_pycodestyle.py` - Style enforcement
- `python_parsers_prospector.py` - Multi-tool orchestration
- `python_parsers_code_quality.py` - Code quality metrics
- Plus 3 more strategies

### Java (10 Strategies)
- `java_parsers_javalang.py` - Native Java parser ✅
- `java_parsers_treesitter.py` - TreeSitter backend
- `java_parsers_SonarQube.py` - SonarQube integration
- `java_parsers_SpotBugs.py` - Bug detection
- `java_parsers_FindSecBugs.py` - Security bugs
- `java_parsers_ErrorProne.py` - Google's error detection
- `java_parsers_Checkstyle.py` - Code style
- `java_parsers_PMD.py` - Pattern matching detection
- `java_parsers_JArchitect.py` - Architecture analysis
- `java_parsers_Infer.py` - Static analysis

### JavaScript/TypeScript (10 Strategies)
- `javascript_parsers_babel.py` - Babel parser ✅
- `javascript_parsers_esprima.py` - ESTree standard
- `javascript_parsers_eslint.py` - ESLint integration
- `javascript_parsers_typescript.py` - TypeScript support
- `javascript_parsers_flow.py` - Flow type checking
- `javascript_parsers_prettier.py` - Code formatting
- `javascript_parsers_standard.py` - StandardJS
- `javascript_parsers_jshint.py` - JSHint checking
- `javascript_parsers_treesitter.py` - TreeSitter backend
- `javascript_parsers_code_quality.py` - Code quality

### Go (4 Strategies)
- `go_parsers_gofmt.py` - Standard formatting
- `go_parsers_golint.py` - Linting
- `go_parsers_govet.py` - Vet analysis
- `go_parsers_staticcheck.py` - Static checking

### C# (4 Strategies)
- `csharp_parsers_StyleCop.py` - Code style
- `csharp_parsers_SonarQube.py` - SonarQube analysis
- `csharp_parsers_Roslyn-Analyzers.py` - Roslyn-based
- `csharp_parsers_ReSharper.py` - JetBrains analysis

### C++ (3 Strategies)
- `cpp_parsers_Clang-Static-Analyzer.py` - Clang analysis
- `cpp_parsers_Cppcheck.py` - C++ checker
- `cpp_parsers_SonarQube.py` - SonarQube analysis

### Kotlin (2 Strategies)
- `kotlin_parsers_Detekt.py` - Static analysis
- `kotlin_parsers_ktlint.py` - Kotlin linting

### Ruby (2 Strategies)
- `ruby_parsers_RuboCop.py` - Ruby style
- `ruby_parsers_Reek.py` - Code smell detection

### Swift (2 Strategies)
- `swift_parsers_SwiftLint.py` - Lint checking
- `swift_parsers_Tailor.py` - Style enforcement

### PHP (3 Strategies)
- `php_parsers_PHPCS.py` - Code sniffer
- `php_parsers_PHPStan.py` - Static analysis
- `php_parsers_Psalm.py` - Psalm type checker

---

## Factory Pattern

```python
from code_scalpel.code_parser import ParserFactory

factory = ParserFactory()

# Automatic language detection
parser = factory.get_parser("src/app.py")      # Returns PythonParser
parser = factory.get_parser("src/Main.java")   # Returns JavaParser
parser = factory.get_parser("src/app.js")      # Returns JSParser

# Explicit strategy selection
parser = factory.get_parser(
    "src/app.py",
    strategy="mypy"  # Use type checking strategy
)

# Parse
result = parser.parse()
```

---

## Usage Examples

### Basic Parsing

```python
from code_scalpel.code_parser import ParserFactory

factory = ParserFactory()
parser = factory.get_parser("src/handlers.py")
result = parser.parse()

print(f"Functions: {len(result.functions)}")
print(f"Classes: {len(result.classes)}")
print(f"Imports: {result.imports}")
```

### Strategy Selection

```python
# Use native parser for basic analysis
native_parser = factory.get_parser("app.py", strategy="ast")
native_result = native_parser.parse()

# Use security parser for vulnerability scanning
security_parser = factory.get_parser("app.py", strategy="bandit")
security_result = security_parser.parse()

# Use type checker
type_parser = factory.get_parser("app.py", strategy="mypy")
type_result = type_parser.parse()
```

### Multi-Language Project

```python
import os
from code_scalpel.code_parser import ParserFactory

factory = ParserFactory()

for root, dirs, files in os.walk("src/"):
    for file in files:
        path = os.path.join(root, file)
        try:
            parser = factory.get_parser(path)
            result = parser.parse()
            print(f"Parsed {path}: {len(result.functions)} functions")
        except UnsupportedLanguageError:
            print(f"Skipping {path}: unsupported language")
```

### Normalized Output

```python
from code_scalpel.code_parser import ParserFactory

factory = ParserFactory()

# Same interface for all languages
for lang in ["python.py", "app.js", "Main.java"]:
    parser = factory.get_parser(lang)
    result = parser.parse()
    
    # Consistent access across languages
    for func in result.functions:
        print(f"Function: {func.name}")
        print(f"  Parameters: {func.parameters}")
        print(f"  Complexity: {func.cyclomatic_complexity}")
        print(f"  Lines: {func.lines_of_code}")
```

---

## Parser Selection Guide

### For AST Analysis
```python
parser = factory.get_parser(file, strategy="ast")  # Python native AST
parser = factory.get_parser(file, strategy="babel")  # JS/TS Babel
parser = factory.get_parser(file, strategy="javalang")  # Java native
```

### For Type Checking
```python
parser = factory.get_parser(file, strategy="mypy")  # Python types
parser = factory.get_parser(file, strategy="flow")  # JS Flow types
parser = factory.get_parser(file, strategy="typescript")  # TS types
```

### For Security Analysis
```python
parser = factory.get_parser(file, strategy="bandit")  # Python security
parser = factory.get_parser(file, strategy="findsecbugs")  # Java security
parser = factory.get_parser(file, strategy="eslint")  # JS security
```

### For Style/Quality
```python
parser = factory.get_parser(file, strategy="pylint")  # Python quality
parser = factory.get_parser(file, strategy="sonarqube")  # Multi-lang
parser = factory.get_parser(file, strategy="checkstyle")  # Java style
```

---

## Architecture

```
Source Code File
    ↓
ParserFactory.get_parser()
    ↓ (detects language)
    ├─ .py → PythonParserFactory
    ├─ .java → JavaParserFactory
    ├─ .js/.ts → JavaScriptParserFactory
    └─ ...
    ↓
Select Strategy (native, linter, type-checker, etc.)
    ↓
Language-Specific Parser
    ↓
Normalized ParseResult
    ↓
AST Tools (analyzer, transformer, etc.)
```

---

## Integration with AST Tools

Parsers output normalized results that feed into AST analysis:

```
Parser Output
    ↓
ASTBuilder (if needed)
    ↓
┌────────────────────────────────┐
│ AST Tools                       │
├────────────────────────────────┤
│ • ASTAnalyzer                  │
│ • CallGraphBuilder             │
│ • TypeInference                │
│ • SecurityAnalyzer             │
│ • etc.                          │
└────────────────────────────────┘
```

---

## Configuration

```python
from code_scalpel.code_parser import ParserFactory

factory = ParserFactory(
    default_strategy="ast",         # Default strategy
    cache_results=True,             # Cache parsed ASTs
    follow_imports=True,            # Resolve imports
    timeout_seconds=300,            # Parse timeout
    max_file_size=10_000_000        # Max file size (bytes)
)
```

---

## Data Flow

### Input (FROM)
```
Source Code Files
    ├─ .py (Python)
    ├─ .java (Java)
    ├─ .js/.ts (JavaScript/TypeScript)
    ├─ .go (Go)
    ├─ .cs (C#)
    ├─ .cpp/.cc (C++)
    ├─ .kt (Kotlin)
    ├─ .rb (Ruby)
    ├─ .swift (Swift)
    └─ .php (PHP)
    ↓
MCP Server / Agents / Users
```

### Processing (WITHIN)
```
ParserFactory.get_parser()
    ↓ (language detection)
Language Selector
    ├─ Python → PythonParserFactory
    ├─ Java → JavaParserFactory
    ├─ JavaScript → JSParserFactory
    └─ ...
    ↓ (strategy selection)
Strategy Selector (ast, bandit, mypy, babel, etc.)
    ↓
Language-Specific Parser
    ├─ Tokenization
    ├─ Parsing
    ├─ AST construction
    └─ Metadata extraction
```

### Output (TO)
```
Normalized ParseResult
    ├─ Functions (name, parameters, returns, complexity)
    ├─ Classes (name, methods, inheritance)
    ├─ Imports (direct, relative, dynamic)
    ├─ Type Information (from annotations)
    ├─ Metrics (LOC, complexity, coverage)
    ├─ Comments (docstrings, inline)
    └─ Errors/Warnings (parse issues)
    ↓
AST Tools (ast_tools/)
    ├─ analyzer.py (metrics)
    ├─ call_graph.py (relationships)
    ├─ type_inference.py (types)
    ├─ control_flow.py (CFG)
    └─ data_flow.py (data analysis)
    ↓
Agents & Security Analysis
```

---

## Development Roadmap

### Phase 1: Current Support (Complete ✅)
- [x] Python parsing (13 strategies)
- [x] Java parsing (10 strategies)
- [x] JavaScript/TypeScript (10 strategies)
- [x] Go parsing (4 strategies)
- [x] C# parsing (4 strategies)
- [x] C++ parsing (3 strategies)
- [x] Kotlin parsing (2 strategies)
- [x] Ruby parsing (2 strategies)
- [x] Swift parsing (2 strategies)
- [x] PHP parsing (3 strategies)

### Phase 2: Enhanced Language Support (Planned 🔄)

#### Strategy Expansion (15+ TODOs)
- [ ] Rust support (5 strategies)
- [ ] Scala support (4 strategies)
- [ ] Kotlin multiplatform (2 additional)
- [ ] Objective-C support (3 strategies)
- [ ] Groovy support (2 strategies)
- [ ] Clojure support (2 strategies)

#### Parser Improvements (20+ TODOs)
- [ ] Incremental parsing for large files
- [ ] Streaming parser support
- [ ] Error recovery improvements
- [ ] Syntax sugar normalization
- [ ] Deprecated syntax handling
- [ ] Language version detection
- [ ] Binary compatibility analysis
- [ ] Performance optimization
- [ ] Memory usage reduction
- [ ] Parser caching & invalidation
- [ ] Parallel parsing for multi-file projects
- [ ] Configuration file parsing (tsconfig, pyproject.toml, etc.)
- [ ] Build tool integration (Maven, Gradle, npm, etc.)
- [ ] Monorepo support
- [ ] Workspace analysis
- [ ] Type definition file parsing (.d.ts, .pyi, etc.)
- [ ] AST normalization across versions
- [ ] Comment preservation
- [ ] Whitespace preservation
- [ ] Raw token stream access

### Phase 3: Intelligence & Integration (Future)
- [ ] Language version inference
- [ ] Framework detection (Django, Spring, Express, etc.)
- [ ] Architecture pattern detection
- [ ] Code style detection (tabs vs spaces, naming conventions)
- [ ] Custom DSL support
- [ ] Polyglot project analysis
- [ ] Cross-language type resolution
- [ ] Build artifact analysis
- [ ] Dependency graph integration with code_parser output
- [ ] Compiler error parsing (gcc, javac, tsc, etc.)

1. **Use Caching** - Enable result caching for repeated analysis
2. **Select Strategy** - Choose fastest appropriate strategy
3. **Parallel Parsing** - Parse multiple files concurrently
4. **Incremental Updates** - Re-parse only changed files
5. **Memory Management** - Clear cache periodically for large projects

---

## File Structure

```
code_parser/
├── README.md                    [This file]
├── __init__.py                  [Exports]
├── base_parser.py               [Abstract base]
├── factory.py                   [Factory pattern]
├── interface.py                 [Parser protocols]
├── python_parser.py             [Python entry point]
│
├── python_parsers/              [13 Python strategies]
│   ├── __init__.py
│   ├── python_parsers_ast.py
│   ├── python_parsers_bandit.py
│   ├── python_parsers_mypy.py
│   └── ... (10 more)
│
├── java_parsers/                [10 Java strategies]
├── javascript_parsers/          [10 JS/TS strategies]
├── go_parsers/                  [4 Go strategies]
├── csharp_parsers/              [4 C# strategies]
├── cpp_parsers/                 [3 C++ strategies]
├── kotlin_parsers/              [2 Kotlin strategies]
├── ruby_parsers/                [2 Ruby strategies]
├── swift_parsers/               [2 Swift strategies]
└── php_parsers/                 [3 PHP strategies]
```

---

## Data Flow

### Language Detection & Parser Selection
```
Source Code + File Extension
    ↓
LanguageDetector.detect()
    ├─ Check file extension
    ├─ Analyze file content
    ├─ Match against patterns
    └─ Return detected language
    ↓
Language Identified
    ↓
ParserFactory.create()
    ├─ Look up language strategies
    ├─ Sort by speed/accuracy
    └─ Select parser instance
    ↓
Parser Instance
```

### Parsing Pipeline
```
Source Code + Selected Parser
    ↓
Parser.parse()
    ├─ Tokenization (lexical analysis)
    ├─ Syntax analysis (parsing)
    ├─ Semantic analysis
    ├─ AST construction
    └─ Normalization
    ↓
Normalized AST
    ├─ Functions extracted
    ├─ Classes identified
    ├─ Imports resolved
    ├─ Variables located
    └─ Metrics calculated
    ↓
Consistent Output Format
```

### Multi-Strategy Analysis
```
Source Code + Analysis Goal
    ↓
ParserFactory.select_strategies()
    ├─ Determine required strategies
    ├─ Sort by performance
    └─ Create parsers
    ↓
Parallel/Sequential Execution
    ├─ Strategy 1 (fastest)
    ├─ Strategy 2 (if needed)
    └─ Strategy N (fallback)
    ↓
Aggregated Results
    ├─ Consensus findings
    ├─ High-confidence issues
    └─ Complementary perspectives
    ↓
Final Analysis Report
```

---

## Development Roadmap

### Phase 1: Language Support Expansion (In Progress 🔄)

#### Python Enhancements (5 TODOs)
- [ ] Async/await pattern detection
- [ ] Decorator analysis
- [ ] Metaclass handling
- [ ] Dynamic module loading
- [ ] Protocol/structural typing support

#### Java Enhancements (6 TODOs)
- [ ] Annotation processing
- [ ] Generics constraint solving
- [ ] Lambda expression handling
- [ ] Module system (Java 9+)
- [ ] Record class support (Java 14+)
- [ ] Sealed classes support (Java 15+)

#### JavaScript/TypeScript Enhancements (7 TODOs)
- [ ] JSX/TSX support (React components)
- [ ] Template literal parsing
- [ ] Async generator support
- [ ] Dynamic import() expressions
- [ ] TypeScript generics
- [ ] TypeScript type guards
- [ ] Map/Set literal support

#### Go Enhancements (4 TODOs)
- [ ] Goroutine analysis
- [ ] Channel type checking
- [ ] Interface satisfaction checking
- [ ] Defer statement handling

### Phase 2: Cross-Language Features (Planned)

#### Parser Infrastructure (10 TODOs)
- [ ] Unified error reporting
- [ ] Performance profiling per parser
- [ ] Caching layer with invalidation
- [ ] Parallel parsing coordination
- [ ] Memory pooling for AST nodes
- [ ] Incremental parsing support
- [ ] Parser conflict resolution
- [ ] Fallback strategy optimization
- [ ] Parser version management
- [ ] Capability negotiation API

#### Quality Improvements (8 TODOs)
- [ ] Fuzzing for parser robustness
- [ ] Error recovery enhancements
- [ ] Partial parsing (incomplete code)
- [ ] Comment preservation
- [ ] Source location accuracy
- [ ] Whitespace normalization
- [ ] Encoding detection
- [ ] Large file handling (streaming)

#### Integration Enhancements (9 TODOs)
- [ ] LSP (Language Server Protocol) support
- [ ] IDE plugin API
- [ ] Docker-based parser execution
- [ ] Remote parser services
- [ ] Parser result validation
- [ ] Result caching strategy
- [ ] Incremental result updates
- [ ] Real-time parsing feedback
- [ ] Parser health monitoring

### Phase 3: Advanced Analysis (Future)

#### Cross-Language Analysis (12 TODOs)
- [ ] Polyglot architecture pattern detection
- [ ] Language-specific design pattern recognition
- [ ] API boundary analysis
- [ ] Type conversion tracking
- [ ] Serialization format verification
- [ ] Protocol conformance checking
- [ ] Compatibility matrix generation
- [ ] Version dependency analysis
- [ ] Feature capability mapping
- [ ] Migration pathway suggestion
- [ ] Performance characteristic comparison
- [ ] Security model comparison

#### Machine Learning Integration (10 TODOs)
- [ ] Anomaly detection in AST patterns
- [ ] Code smell classification
- [ ] Bug pattern learning
- [ ] Performance prediction
- [ ] Refactoring opportunity ranking
- [ ] Code clone detection (ML-based)
- [ ] Author style profiling
- [ ] Complexity estimation
- [ ] Test coverage prediction
- [ ] Vulnerability likelihood scoring

---

**Last Updated:** December 21, 2025  
**Version:** v3.0.0  
**Status:** 40+ Parsers ✅ (Total TODOs: 71)
