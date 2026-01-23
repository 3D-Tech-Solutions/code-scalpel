# Swift Parsers Module - Comprehensive Documentation

**Module Location:** `src/code_scalpel/code_parser/swift_parsers/`  
**Status:** Phase 1 Complete (Stub Structure) - Phase 2 In Progress  
**Last Updated:** December 21, 2025  

---

## Table of Contents

1. [Overview](#overview)
2. [Module Architecture](#module-architecture)
3. [Supported Tools](#supported-tools)
4. [Implementation Status](#implementation-status)
5. [API Reference](#api-reference)
6. [Phase 2 Implementation Roadmap](#phase-2-implementation-roadmap)
7. [Integration Guide](#integration-guide)
8. [Example Usage](#example-usage)
9. [Configuration](#configuration)
10. [Performance Considerations](#performance-considerations)

---

## Overview

The Swift Parsers Module provides comprehensive static analysis capabilities for Swift codebases using industry-standard linting, formatting, and AST analysis tools. It serves as a unified interface for multiple Swift analysis engines:

- **SwiftLint** - Linting and code style enforcement
- **Tailor** - Complexity and design metrics analysis
- **SourceKitten** - AST parsing and semantic analysis
- **SwiftFormat** - Code formatting and normalization
- **Periphery** - Dead code detection
- **SPM Analysis** - Swift Package Manager dependency analysis

### Key Capabilities

| Capability | Tools | Status |
|------------|-------|--------|
| Code Style Linting | SwiftLint, Tailor | Phase 2 TODO |
| Complexity Analysis | Tailor, SourceKitten | Phase 2 TODO |
| AST Parsing | SourceKitten | Phase 2 TODO |
| Code Formatting | SwiftFormat | Phase 2 TODO |
| Dead Code Detection | Periphery | Phase 2 TODO |
| Dependency Analysis | SPM | Phase 2 TODO |
| iOS/macOS Detection | Framework Detection | Phase 2 TODO |
| Multi-Format Reports | JSON, SARIF, HTML | Phase 2 TODO |

---

## Module Architecture

### Directory Structure

```
swift_parsers/
├── __init__.py                          # Module registry and factory
├── swift_parsers_SwiftLint.py          # SwiftLint integration
├── swift_parsers_Tailor.py             # Tailor metrics analysis
├── swift_parsers_sourcekitten.py       # SourceKitten AST parser
├── swift_parsers_swiftformat.py        # SwiftFormat integration
├── swift_parsers_periphery.py          # Dead code detection
└── README.md                            # This documentation
```

### Component Relationships

```
SwiftParserRegistry (factory)
├── SwiftLintParser
│   ├── SwiftLintViolation
│   └── SwiftLintConfig
├── TailorParser
│   ├── TailorMetric
│   └── TailorConfig
├── SourceKittenParser
│   ├── SwiftSymbol
│   └── SwiftComplexity
├── SwiftFormatParser
│   └── FormattingIssue
└── PeripheryParser
    └── DeadCodeIssue
```

---

## Supported Tools

### 1. SwiftLint - Code Style Enforcement

**Purpose:** Enforce Swift code style guidelines and best practices

**File:** `swift_parsers_SwiftLint.py`

**Key Metrics:**
- Violation count by severity (Notice, Warning, Error)
- Rule distribution and frequency
- File-level violation density
- Correctable vs. non-correctable violations

**Phase 2 Deliverables:**
1. JSON output parsing from `swiftlint --format=json`
2. `.swiftlint.yml` configuration loading
3. Subprocess execution management
4. Auto-fix application via `swiftlint --fix`
5. SARIF report generation
6. iOS/macOS specific rule handling

**Configuration Example:**
```yaml
disabled_rules:
  - trailing_whitespace
  - force_cast

opt_in_rules:
  - empty_count
  - closure_spacing
  - closure_end_indentation

rule_configs:
  line_length:
    warning: 120
    error: 160
  type_body_length:
    warning: 300
    error: 400
```

### 2. Tailor - Complexity & Design Metrics

**Purpose:** Analyze code complexity, design issues, and maintainability metrics

**File:** `swift_parsers_Tailor.py`

**Key Metrics:**
- Cyclomatic complexity per function
- Cognitive complexity
- Lines of code (LOC)
- NESTING level analysis
- Parameter count analysis
- Return statement count

**Phase 2 Deliverables:**
1. JSON output parsing from `tailor --format=json`
2. `.tailor.yml` configuration support
3. Metric categorization by type
4. Cyclomatic complexity calculation
5. Design issue detection
6. Trend analysis over time

**Metric Categories:**
- **Length:** File size, function size, parameter count
- **Complexity:** Cyclomatic, cognitive, nesting depth
- **Naming:** Identifier length, naming conventions
- **Design:** Coupling, cohesion, architecture issues
- **Style:** Indentation, spacing, formatting

### 3. SourceKitten - AST & Semantic Analysis

**Purpose:** Parse Swift Abstract Syntax Tree and extract semantic information

**File:** `swift_parsers_sourcekitten.py`

**Key Features:**
- Full AST extraction
- Symbol table generation
- Type information resolution
- Documentation comment parsing
- Semantic relationship analysis

**Phase 2 Deliverables:**
1. SourceKitten JSON output parsing
2. AST structure extraction
3. Symbol inventory generation
4. Documentation extraction
5. Type inference analysis
6. Cross-reference generation

**Data Structures:**
```python
SwiftSymbol:
  - name: str
  - kind: str (class, function, var, protocol, etc.)
  - file_path: str
  - line_number: int
  - column: int
  - documentation: Optional[str]
  - accessibility: str (open, public, internal, private)

SwiftComplexity:
  - symbol_name: str
  - cyclomatic_complexity: int
  - cognitive_complexity: int
  - lines_of_code: int
```

### 4. SwiftFormat - Code Formatting

**Purpose:** Enforce consistent code formatting and normalization

**File:** `swift_parsers_swiftformat.py`

**Key Features:**
- Code formatting analysis
- Auto-formatting capability
- Formatting violation detection
- Custom rule configuration

**Phase 2 Deliverables:**
1. SwiftFormat configuration parsing
2. Formatting analysis execution
3. Auto-fix application
4. Formatting report generation
5. Diff generation for changes

### 5. Periphery - Dead Code Detection

**Purpose:** Identify unused code and potential dead code removal opportunities

**File:** `swift_parsers_periphery.py` (planned)

**Key Features:**
- Unused variable detection
- Unused function detection
- Unused type/class detection
- Redundant code identification

**Status:** Phase 2 TODO

### 6. SPM Analysis - Dependency Analysis

**Purpose:** Analyze Swift Package Manager dependencies and build configuration

**File:** `swift_parsers_spm.py` (planned)

**Key Features:**
- Dependency graph analysis
- Version conflict detection
- Build target analysis
- Compilation unit analysis

**Status:** Phase 2 TODO

---

## Implementation Status

### Phase 1: Stub Structure (✅ COMPLETE)
- [x] Create module directory structure
- [x] Define data classes (violations, metrics, symbols)
- [x] Create parser classes with method signatures
- [x] Add comprehensive docstrings
- [x] Create SwiftParserRegistry scaffold
- [x] Tag all TODO items with [20251221_TODO]

### Phase 2: Core Implementation (🟡 IN PROGRESS)

#### SwiftLintParser [20251221_TODO]
- [ ] `execute_swiftlint()` - Run SwiftLint analysis
- [ ] `parse_json_report()` - Parse JSON output
- [ ] `load_config()` - Load .swiftlint.yml
- [ ] `categorize_violations()` - Group by rule
- [ ] `apply_fixes()` - Auto-fix violations
- [ ] `generate_report()` - JSON/SARIF output

#### TailorParser [20251221_TODO]
- [ ] `execute_tailor()` - Run Tailor analysis
- [ ] `parse_json_report()` - Parse JSON output
- [ ] `load_config()` - Load .tailor.yml
- [ ] `detect_complexity_issues()` - Filter metrics
- [ ] `calculate_code_metrics()` - Compute aggregates
- [ ] `analyze_metric_trends()` - Historical analysis

#### SourceKittenParser [20251221_TODO]
- [ ] `execute_sourcekitten()` - Run SourceKitten
- [ ] `parse_sourcekitten_output()` - Parse JSON AST
- [ ] `extract_symbols()` - Symbol table creation
- [ ] `analyze_complexity()` - Complexity metrics
- [ ] `extract_documentation()` - Doc comment parsing
- [ ] `generate_ast_report()` - AST report generation

#### SwiftFormatParser [20251221_TODO]
- [ ] `execute_swiftformat()` - Run SwiftFormat
- [ ] `parse_format_config()` - Load configuration
- [ ] `apply_formatting()` - Auto-format files
- [ ] `detect_formatting_issues()` - Analysis mode
- [ ] `generate_diff()` - Show changes

#### SwiftParserRegistry [20251221_TODO]
- [ ] Factory pattern implementation
- [ ] Lazy-loading optimization
- [ ] Result aggregation across tools
- [ ] Deduplication and filtering
- [ ] Unified output formatting

### Phase 3: Advanced Features (PLANNED)
- [ ] iOS/macOS framework detection
- [ ] Xcode project parsing
- [ ] Performance profiling integration
- [ ] Code coverage correlation
- [ ] Machine learning-based issue categorization

---

## API Reference

### SwiftParserRegistry

```python
class SwiftParserRegistry:
    """Factory and aggregation point for Swift parsers."""
    
    def __init__(self):
        """Initialize registry with lazy-loaded parsers."""
    
    def get_parser(self, tool_name: str) -> BaseSwiftParser:
        """Get parser instance by tool name."""
    
    def analyze(self, path: Path, tools: List[str] = None) -> AnalysisResult:
        """Run specified parsers on given path."""
    
    def get_aggregated_metrics(self) -> Dict[str, Any]:
        """Get metrics from all parsers."""
    
    def generate_unified_report(self, format: str = "json") -> str:
        """Generate aggregated report in specified format."""
```

### SwiftLintParser

```python
class SwiftLintParser:
    """SwiftLint integration for Swift code style enforcement."""
    
    def execute_swiftlint(self, paths: List[Path], config: SwiftLintConfig = None) 
        -> List[SwiftLintViolation]:
        """Execute SwiftLint analysis."""
    
    def parse_json_report(self, report_path: Path) -> List[SwiftLintViolation]:
        """Parse SwiftLint JSON report."""
    
    def load_config(self, config_file: Path) -> SwiftLintConfig:
        """Load .swiftlint.yml configuration."""
    
    def categorize_violations(self, violations: List[SwiftLintViolation]) 
        -> Dict[str, List[SwiftLintViolation]]:
        """Group violations by rule category."""
    
    def apply_fixes(self, violations: List[SwiftLintViolation]) -> Dict[str, int]:
        """Apply auto-fixes to correctable violations."""
    
    def generate_report(self, violations: List[SwiftLintViolation], 
                       format: str = "json") -> str:
        """Generate analysis report in specified format."""
```

### TailorParser

```python
class TailorParser:
    """Tailor integration for complexity and design metrics."""
    
    def execute_tailor(self, paths: List[Path], config: TailorConfig = None) 
        -> List[TailorMetric]:
        """Execute Tailor analysis."""
    
    def parse_json_report(self, report_path: Path) -> List[TailorMetric]:
        """Parse Tailor JSON report."""
    
    def load_config(self, config_file: Path) -> TailorConfig:
        """Load .tailor.yml configuration."""
    
    def categorize_metrics(self, metrics: List[TailorMetric]) 
        -> Dict[MetricType, List[TailorMetric]]:
        """Group metrics by type."""
    
    def calculate_code_metrics(self, metrics: List[TailorMetric]) -> Dict[str, Any]:
        """Calculate aggregate code metrics."""
    
    def analyze_metric_trends(self, historical_data: List[Dict]) -> Dict[str, Any]:
        """Analyze metrics over time."""
```

### SourceKittenParser

```python
class SourceKittenParser:
    """SourceKitten integration for AST and semantic analysis."""
    
    def execute_sourcekitten(self, paths: List[Path]) -> List[SwiftSymbol]:
        """Execute SourceKitten analysis."""
    
    def parse_sourcekitten_output(self, output_path: Path) -> List[SwiftSymbol]:
        """Parse SourceKitten JSON output."""
    
    def extract_symbols(self, output: Dict[str, Any]) -> List[SwiftSymbol]:
        """Extract symbols from SourceKitten output."""
    
    def analyze_complexity(self, symbols: List[SwiftSymbol]) 
        -> List[SwiftComplexity]:
        """Analyze code complexity."""
    
    def extract_documentation(self, symbols: List[SwiftSymbol]) -> Dict[str, str]:
        """Extract documentation from symbols."""
    
    def generate_ast_report(self, symbols: List[SwiftSymbol]) -> str:
        """Generate AST analysis report."""
```

---

## Phase 2 Implementation Roadmap

### Sprint 1: Foundation (Weeks 1-2)
- [x] Module structure and stubs
- [ ] Environment setup (SwiftLint, Tailor, SourceKitten)
- [ ] Basic execution wrappers
- [ ] Output parsing framework

### Sprint 2: Core Parsers (Weeks 3-5)
- [ ] SwiftLintParser full implementation
- [ ] TailorParser full implementation
- [ ] SourceKittenParser basic AST parsing
- [ ] Unit test coverage (>90%)

### Sprint 3: Advanced Features (Weeks 6-7)
- [ ] SwiftFormatParser implementation
- [ ] Result aggregation and deduplication
- [ ] Multi-format report generation
- [ ] iOS/macOS framework detection

### Sprint 4: Integration & Testing (Week 8)
- [ ] SwiftParserRegistry factory
- [ ] End-to-end integration tests
- [ ] Performance benchmarking
- [ ] Documentation completion

---

## Integration Guide

### Standalone Usage

```python
from code_scalpel.code_parser.swift_parsers import SwiftParserRegistry

# Initialize registry
registry = SwiftParserRegistry()

# Analyze with specific tools
result = registry.analyze(
    path=Path("/path/to/swift/project"),
    tools=["swiftlint", "tailor", "sourcekitten"]
)

# Get aggregated metrics
metrics = registry.get_aggregated_metrics()

# Generate report
report = registry.generate_unified_report(format="json")
```

### Integration with Code Scalpel MCP Tools

```python
# Would integrate with extract_code, security_scan, etc.
# Swift-specific symbol extraction and analysis
```

### CI/CD Pipeline Integration

```bash
#!/bin/bash
# Example: GitHub Actions

- name: Run Swift Analysis
  run: |
    python -m code_scalpel.code_parser.swift_parsers \
      --path ./Sources \
      --tools swiftlint,tailor,sourcekitten \
      --format json \
      --output report.json
```

---

## Example Usage

### Basic Analysis

```python
from pathlib import Path
from code_scalpel.code_parser.swift_parsers.swift_parsers_SwiftLint import SwiftLintParser

parser = SwiftLintParser()
violations = parser.execute_swiftlint(
    paths=[Path("./Sources")],
    config=None  # Use default or .swiftlint.yml
)

for violation in violations:
    print(f"{violation.file_path}:{violation.line_number} - {violation.message}")
```

### Custom Configuration

```python
from pathlib import Path
from code_scalpel.code_parser.swift_parsers.swift_parsers_Tailor import TailorParser, TailorConfig

parser = TailorParser()
config = parser.load_config(Path(".tailor.yml"))
config.max_complexity = 12
config.max_length = 200

metrics = parser.execute_tailor(paths=[Path("./Sources")], config=config)
complexity_issues = parser.detect_complexity_issues(metrics)
```

### AST Analysis

```python
from pathlib import Path
from code_scalpel.code_parser.swift_parsers.swift_parsers_sourcekitten import SourceKittenParser

parser = SourceKittenParser()
symbols = parser.execute_sourcekitten(paths=[Path("./Sources")])

for symbol in symbols:
    if symbol.kind in ["class", "struct"]:
        print(f"{symbol.kind} {symbol.name} at {symbol.file_path}:{symbol.line_number}")
```

### Registry-Based Analysis

```python
from pathlib import Path
from code_scalpel.code_parser.swift_parsers import SwiftParserRegistry

registry = SwiftParserRegistry()

# Analyze with all available tools
result = registry.analyze(
    path=Path("./Sources"),
    tools=["swiftlint", "tailor", "sourcekitten", "swiftformat"]
)

# Generate multiple report formats
json_report = registry.generate_unified_report(format="json")
sarif_report = registry.generate_unified_report(format="sarif")
html_report = registry.generate_unified_report(format="html")
```

---

## Configuration

### SwiftLint Configuration (.swiftlint.yml)

```yaml
# File location: .swiftlint.yml
disabled_rules:
  - trailing_whitespace
  - force_cast
  - identifier_name

opt_in_rules:
  - empty_count
  - closure_spacing
  - array_init

rule_configs:
  line_length:
    warning: 120
    error: 160
    ignores_comments: true
    ignores_urls: true

  type_body_length:
    warning: 300
    error: 400

  function_body_length:
    warning: 50
    error: 100

  cyclomatic_complexity:
    warning: 10
    error: 20

included:
  - Sources
  - Tests

excluded:
  - Pods
  - .build
  - DerivedData
```

### Tailor Configuration (.tailor.yml)

```yaml
# File location: .tailor.yml
rules:
  length:
    enabled: true
    line_length:
      warning: 100
      error: 120
    file_length:
      warning: 500
      error: 1000

  complexity:
    enabled: true
    cyclomatic_complexity:
      warning: 10
      error: 20
    parameter_count:
      warning: 5
      error: 8
    nesting_level:
      warning: 3
      error: 5

  naming:
    enabled: true
    type_name_length:
      min: 3
      max: 40

  design:
    enabled: true
    coupling: 5
    cohesion: 0.7

excluded_paths:
  - Pods
  - .build
  - Tests/Fixtures
```

### SourceKitten Configuration

No configuration file needed (uses SPM configuration).

### SwiftFormat Configuration (.swiftformat)

```
# File location: .swiftformat
--indent 4
--tabwidth 4
--semicolons never
--commas inline
--comments indent
--wraparguments before-first
--closingparen balanced
--maxwidth 120
--version 0.52.0
```

---

## Performance Considerations

### Tool Execution Time (Estimated)

| Tool | File Count | Avg Time | Notes |
|------|-----------|----------|-------|
| SwiftLint | 100 files | 5-10s | Fast, I/O bound |
| Tailor | 100 files | 15-20s | More complex analysis |
| SourceKitten | 100 files | 20-30s | AST parsing overhead |
| SwiftFormat | 100 files | 8-12s | Formatting analysis |
| **Total** | 100 files | 50-70s | Parallel execution possible |

### Optimization Strategies

1. **Parallel Execution:** Run tools concurrently when possible
2. **Caching:** Cache results between runs (depends on file modification time)
3. **Incremental Analysis:** Analyze only changed files in CI/CD
4. **Tool Selection:** Choose relevant tools for specific use cases

### Memory Usage

- SwiftLint: ~100MB
- Tailor: ~150MB
- SourceKitten: ~200MB (includes SPM compilation)
- SwiftFormat: ~80MB

**Recommendation:** For projects with >1000 files, use parallel analysis with subprocess pools.

---

## Troubleshooting

### Common Issues

**Issue:** SwiftLint not found in PATH
```bash
# Solution: Install SwiftLint
brew install swiftlint  # macOS
swift run swiftlint     # Via SPM
```

**Issue:** SourceKitten fails to parse project
```bash
# Solution: Ensure Swift Package Manager structure
swift build -c debug  # Pre-build before analysis
```

**Issue:** Configuration file not found
```bash
# Solution: Ensure .swiftlint.yml or .tailor.yml in project root
# Or pass explicit config path to parser methods
```

---

## Related Documentation

- [Swift AST Reference](https://swift.org/documentation/)
- [SwiftLint Rules Documentation](https://realm.github.io/SwiftLint/rule-directory.html)
- [Tailor GitHub Repository](https://github.com/sleekbyte/tailor)
- [SourceKitten GitHub Repository](https://github.com/jpsim/SourceKitten)

---

## Contributing

Contributions are welcome! Please refer to the main [CONTRIBUTING_TO_MCP_REGISTRY.md](../CONTRIBUTING_TO_MCP_REGISTRY.md) for guidelines.

When implementing Phase 2 features:
1. Follow the existing code style and patterns
2. Add comprehensive docstrings and type hints
3. Include unit tests with >90% coverage
4. Use the [20251221_TODO] tagging convention for future work
5. Generate evidence files documenting implementation

---

## License

MIT License - See [LICENSE](../../LICENSE) for details

---

**Last Updated:** December 21, 2025  
**Module Maintainers:** Code Scalpel Team  
**Status:** Phase 1 Complete, Phase 2 In Progress
