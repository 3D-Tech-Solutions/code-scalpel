# Python Parsers Module

> **Code Scalpel's Python Parser provides surgical precision for Python code analysis, integrating the best static analysis tools in the Python ecosystem.**

## Overview

This module provides unified interfaces to 10 Python static analysis tools, offering:
- **Consistent API** across all tools
- **Structured output** via dataclasses
- **Configuration parsing** from standard config files
- **Comprehensive coverage** of linting, type checking, security, and quality metrics

## Module Architecture

```
python_parsers/
├── __init__.py              # Public API with lazy loading
├── python_parsers_ast.py    # Core AST analysis, symbols, CFG/DFG
├── python_parsers_ruff.py   # Fast Rust-based linting
├── python_parsers_mypy.py   # Static type checking
├── python_parsers_pylint.py # Code quality analysis
├── python_parsers_bandit.py # Security vulnerability detection
├── python_parsers_flake8.py # Style checking with plugins
├── python_parsers_code_quality.py  # Complexity metrics
├── python_parsers_pydocstyle.py    # Docstring validation
├── python_parsers_pycodestyle.py   # PEP 8 enforcement
├── python_parsers_prospector.py    # Meta-linter aggregation
├── python_parsers_isort.py         # Import sorting (PLANNED)
├── python_parsers_vulture.py       # Dead code detection (PLANNED)
├── python_parsers_radon.py         # Code complexity metrics (PLANNED)
├── python_parsers_safety.py        # Dependency security (PLANNED)
├── python_parsers_interrogate.py   # Documentation coverage (PLANNED)
└── README.md                # This file
```

## Data Flow Architecture

### Input Sources

```
┌─────────────────────────────────────────────────────┐
│           INPUTS TO PYTHON_PARSERS MODULE           │
└─────────────────────────────────────────────────────┘

1. SOURCE CODE
   ├─ Python files (.py)
   ├─ Stub files (.pyi)
   └─ String content (in-memory)

2. CONFIGURATION FILES
   ├─ pyproject.toml
   ├─ .pylintrc / pylintrc
   ├─ setup.cfg
   ├─ ruff.toml
   ├─ mypy.ini
   ├─ .bandit
   ├─ .flake8
   ├─ tox.ini
   ├─ .prospector.yaml
   └─ Programmatic config objects

3. TOOL OUTPUTS
   ├─ JSON output (mypy, pylint, bandit, ruff, prospector)
   ├─ Text output (flake8, pydocstyle, pycodestyle)
   └─ SARIF format (bandit, prospector)

4. ENVIRONMENT
   ├─ Python version
   ├─ Tool installation paths
   ├─ Virtual environment
   └─ Working directory
```

### Processing Pipeline

```
┌──────────────────────────────────────────────────────────────┐
│         PROCESSING PIPELINE WITHIN PARSERS                   │
└──────────────────────────────────────────────────────────────┘

SOURCE CODE INPUT
    │
    ├─→ [PythonASTParser] ─────→ AST Analysis
    │      ├─ Symbol extraction (functions, classes, imports)
    │      ├─ Scope analysis (LEGB rule)
    │      ├─ Control Flow Graph (CFG)
    │      └─ Data Flow Analysis (DFG)
    │
    ├─→ [RuffParser] ──────────→ Fast Linting
    │      ├─ JSON output parsing
    │      ├─ Rule categorization
    │      └─ Auto-fix extraction
    │
    ├─→ [MypyParser] ──────────→ Type Checking
    │      ├─ JSON output parsing
    │      ├─ Error classification
    │      ├─ Type coverage calculation
    │      └─ Typeshed suggestion matching
    │
    ├─→ [PylintParser] ────────→ Quality Analysis
    │      ├─ JSON output parsing
    │      ├─ Message grouping by checker
    │      ├─ Score calculation
    │      └─ Improvement suggestions
    │
    ├─→ [BanditParser] ────────→ Security Analysis
    │      ├─ JSON output parsing
    │      ├─ CWE/CVE mapping
    │      ├─ Severity normalization
    │      └─ SARIF generation
    │
    ├─→ [Flake8Parser] ────────→ Style Checking
    │      ├─ Output parsing
    │      ├─ Plugin detection
    │      └─ Code categorization
    │
    ├─→ [CodeQualityParser] ───→ Complexity Metrics
    │      ├─ Cyclomatic complexity
    │      ├─ Cognitive complexity
    │      ├─ Maintainability index
    │      └─ LOC calculation
    │
    ├─→ [PydocstyleParser] ────→ Docstring Validation
    │      ├─ Convention detection
    │      ├─ Coverage analysis
    │      └─ Quality checking
    │
    ├─→ [PycodestyleParser] ───→ PEP 8 Enforcement
    │      └─ Style compliance percentage
    │
    └─→ [ProspectorParser] ────→ Meta-Linter Aggregation
           ├─ Multi-tool execution
           ├─ Message deduplication
           └─ Profile management

CONFIGURATION PARSING (Parallel)
    │
    ├─→ TOML Parser (tomllib/tomli)
    ├─→ INI Parser (configparser)
    └─→ YAML Parser (PyYAML)
```

### Output Data Structures

```
┌──────────────────────────────────────────────────────────────┐
│              OUTPUTS FROM PYTHON_PARSERS MODULE              │
└──────────────────────────────────────────────────────────────┘

1. STRUCTURED RESULT OBJECTS
   
   Common structure across all parsers:
   ├─ Result/Message/Issue dataclass
   │  ├─ code/id/test_id (unique identifier)
   │  ├─ message/text (human-readable message)
   │  ├─ severity (error, warning, info, note)
   │  ├─ path (file location)
   │  ├─ line (line number)
   │  ├─ column (column number)
   │  └─ metadata (tool-specific)
   │
   ├─ Report/Result dataclass
   │  ├─ messages/results/issues (list of findings)
   │  ├─ statistics (counts, scores, metrics)
   │  ├─ metadata (tool version, execution time)
   │  └─ success (execution status)
   │
   └─ Config dataclass
      ├─ Tool-specific options
      └─ Methods: from_file(), to_cli_args()

2. AGGREGATE REPORT FORMATS
   
   Individual Reports (one per parser):
   ├─ RuffViolation / RuffReport
   ├─ MypyError / MypyResult
   ├─ PylintMessage / PylintReport
   ├─ BanditIssue / BanditReport
   ├─ Flake8Violation / Flake8Report
   ├─ ComplexityMetrics / CodeQualityReport
   ├─ PydocstyleViolation / PydocstyleReport
   ├─ PycodestyleViolation / PycodestyleReport
   └─ ProspectorMessage / ProspectorReport

3. EXPORT FORMATS
   
   ├─ Python dataclass dicts (via asdict())
   ├─ JSON serialization (for APIs, files)
   ├─ SARIF format (bandit, prospector for CI/CD)
   ├─ Human-readable text (format() methods)
   ├─ CSV export (via pandas if available)
   └─ HTML reports (tool-specific)

4. ANALYSIS PRODUCTS
   
   ├─ Symbols: PythonFunction, PythonClass, PythonImport
   ├─ Graphs: CFG (ControlFlowGraph), DFG (DataFlowGraph)
   ├─ Metrics: Complexity, Maintainability, Coverage
   ├─ Coverage: TypeCoverage, DocCoverage, StyleCompliance
   └─ Suggestions: QuickWins, ScoreImprovements, Refactorings
```

### Integration Points with Other Modules

```
┌──────────────────────────────────────────────────────────────┐
│         INTEGRATION WITH CODEBASE ECOSYSTEM                  │
└──────────────────────────────────────────────────────────────┘

UPSTREAM CONSUMERS (Import from python_parsers):
├─ code_scalpel.code_parser (BaseToolParser interface)
├─ code_scalpel.code_analyzer (Cross-language analysis)
├─ code_scalpel.report_generator (Multi-parser reporting)
├─ code_scalpel.ide_integration (VS Code/IDE features)
└─ code_scalpel.cli (Command-line interface)

DOWNSTREAM SOURCES (Provide data to python_parsers):
├─ Filesystem (load Python files, config files)
├─ External tools (ruff, mypy, pylint, bandit, flake8, etc.)
├─ Configuration managers (pyproject.toml, setup.cfg)
└─ Environment (Python version, virtualenv)

CROSS-PARSER DATA FLOW:
├─ AST Parser (foundation)
│  └─ Output: Symbol table, scopes, CFG/DFG
│     └─ Consumed by: Code quality metrics, framework detection
│
├─ Ruff, Mypy, Pylint, Bandit, Flake8 (parallel analysis)
│  └─ Output: Structured findings
│     └─ Aggregated by: ProspectorParser, report_generator
│
├─ ProspectorParser (meta-analysis)
│  └─ Input: Results from all other parsers
│  └─ Output: Deduplicated, unified severity report
│     └─ Consumed by: Report generation, CI/CD pipelines
│
└─ CodeQualityParser (metrics-focused)
   └─ Input: AST output, complexity calculations
   └─ Output: Metrics dashboard data
      └─ Consumed by: Trend analysis, quality gates
```

### Data Flow Diagram (Simplified)

```
FILE SYSTEM              CONFIGURATION           EXTERNAL TOOLS
    │                        │                         │
    │                        │                         │
    ├─ .py files     [pyproject.toml]     [Ruff binary]
    ├─ .pyi files    [.pylintrc]          [mypy binary]
    └─ Directories   [setup.cfg]          [pylint binary]
                     [ruff.toml]          [bandit binary]
                                          [flake8 binary]
    │                │                    │
    └────────────────┴────────────────────┘
                      │
                      ▼
        ┌─────────────────────────────┐
        │  python_parsers module      │
        │  (10 specialized parsers)   │
        └─────────────────────────────┘
                      │
        ┌─────────────┼─────────────┐
        │             │             │
        ▼             ▼             ▼
   AST Analysis  Tool Output    Configuration
   (Symbols,     Parsing        Objects
    CFG/DFG)     (JSON, text)
        │             │             │
        └─────────────┼─────────────┘
                      │
                      ▼
        ┌─────────────────────────────┐
        │ Structured Report Objects   │
        │ (dataclasses with metrics)  │
        └─────────────────────────────┘
                      │
        ┌─────────────┼──────────────┐
        │             │              │
        ▼             ▼              ▼
    Report      JSON/SARIF    Python dicts
    Generator   Export        (asdict)
        │             │              │
        └─────────────┼──────────────┘
                      │
                      ▼
        ┌─────────────────────────────┐
        │   Upstream Consumers        │
        │ (analyzers, reporters, CLI) │
        └─────────────────────────────┘
```

### Example Complete Data Flow

```python
# INPUT: Source file
source_code = Path("example.py").read_text()

# PROCESSING: Multiple parsers in parallel
ast_parser = PythonASTParser()
module = ast_parser.parse_file("example.py")

ruff = RuffParser()
ruff_report = ruff.analyze("example.py")

mypy = MypyParser()
mypy_result = mypy.check("example.py")

# TRANSFORMATION: Extract and enrich results
violations = [
    {
        "tool": "ruff",
        "code": v.code,
        "line": v.line,
        "message": v.message,
        "severity": v.severity.value,
    }
    for v in ruff_report.violations
]

# AGGREGATION: Combine results
from dataclasses import asdict
all_results = {
    "ast": {
        "functions": len(module.functions),
        "classes": len(module.classes),
    },
    "ruff": asdict(ruff_report.statistics),
    "mypy": asdict(mypy_result.statistics),
}

# OUTPUT: Export to various formats
import json
json.dump(all_results, open("report.json", "w"))

# or use in reports
from code_scalpel.report_generator import create_report
report = create_report(
    [ruff_report, mypy_result, ast_output],
    format="html"
)
```

## Parser Summary

| Parser | Tool | Purpose | Status | Key Features |
|--------|------|---------|--------|--------------|
| `PythonASTParser` | Built-in `ast` | Core analysis | ✓ DONE | Symbol extraction, CFG/DFG, scope analysis |
| `RuffParser` | Ruff | Fast linting | ✓ DONE | 800+ rules, auto-fix, pyproject.toml config |
| `MypyParser` | mypy | Type checking | ✓ DONE | Type coverage, JSON output, error context |
| `PylintParser` | Pylint | Quality analysis | ✓ DONE | 200+ messages, scoring, checker grouping |
| `BanditParser` | Bandit | Security | ✓ DONE | CVE/CWE mapping, SARIF output, profiles |
| `Flake8Parser` | Flake8 | Style checking | ✓ DONE | Plugin support, noqa handling |
| `CodeQualityParser` | Built-in | Metrics | ✓ DONE | Cyclomatic/cognitive complexity, LOC |
| `PydocstyleParser` | pydocstyle | Docstrings | ✓ DONE | Convention support, quality analysis |
| `PycodestyleParser` | pycodestyle | PEP 8 | ✓ DONE | Style compliance percentage |
| `ProspectorParser` | Prospector | Meta-linter | ✓ DONE | Profile management, deduplication |
| `IsortParser` | isort | Import sorting | ⏳ PLANNED | Sorting checks, profile support, multi-line imports |
| `VultureParser` | Vulture | Dead code | ⏳ PLANNED | Unused detection, confidence filtering, false positive handling |
| `RadonParser` | Radon | Complexity metrics | ⏳ PLANNED | CC/MI analysis, grading, maintainability scoring |
| `SafetyParser` | Safety | Dependency security | ⏳ PLANNED | CVE mapping, CVSS scoring, remediation steps |
| `InterrogateParser` | Interrogate | Doc coverage | ⏳ PLANNED | Coverage percentage, missing docs, style detection |

## Quick Start

### Basic Usage

```python
from code_scalpel.code_parser.python_parsers import (
    PythonASTParser,
    RuffParser,
    MypyParser,
    PylintParser,
)

# AST Analysis
ast_parser = PythonASTParser()
module = ast_parser.parse_file("example.py")
print(f"Functions: {len(module.functions)}")
print(f"Classes: {len(module.classes)}")

# Linting with Ruff (fast!)
ruff = RuffParser()
report = ruff.analyze("example.py")
for violation in report.violations:
    print(f"{violation.code}: {violation.message}")

# Type Checking with mypy
mypy = MypyParser()
result = mypy.check("example.py")
print(f"Type coverage: {result.coverage.coverage_percent:.1f}%")

# Quality Analysis with Pylint
pylint = PylintParser()
report = pylint.analyze("example.py")
print(f"Score: {report.statistics.score}/10")
```

### Configuration

Each parser supports configuration from standard config files:

```python
from code_scalpel.code_parser.python_parsers import (
    RuffConfig,
    MypyConfig,
    PylintConfig,
)

# Load from pyproject.toml
ruff_config = RuffConfig.from_pyproject("pyproject.toml")
mypy_config = MypyConfig.from_pyproject("pyproject.toml")

# Load from tool-specific files
pylint_config = PylintConfig.from_file(".pylintrc")

# Programmatic configuration
ruff_config = RuffConfig(
    select=["E", "F", "W"],
    ignore=["E501"],
    line_length=120,
    target_version="py311",
)
```

## Detailed Parser Documentation

### PythonASTParser - Core Analysis

The foundation parser providing AST-based analysis:

```python
from code_scalpel.code_parser.python_parsers import (
    PythonASTParser,
    PythonModule,
    PythonFunction,
    PythonClass,
)

parser = PythonASTParser()
module = parser.parse_file("example.py")

# Symbol extraction
for func in module.functions:
    print(f"{func.name}({', '.join(func.parameters)})")
    print(f"  Complexity: {func.complexity}")
    print(f"  Is async: {func.is_async}")

# Control Flow Graph
cfg = parser.build_cfg(module)
for block in cfg.basic_blocks:
    print(f"Block {block.id}: {len(block.statements)} statements")

# Data Flow Analysis
dfg = parser.build_dfg(module)
reaching_defs = dfg.get_reaching_definitions("variable_name")
```

### RuffParser - Fast Linting

Rust-based linter with auto-fix capabilities:

```python
from code_scalpel.code_parser.python_parsers import (
    RuffParser,
    RuffConfig,
    RULE_PREFIXES,
)

# See all rule categories
print(RULE_PREFIXES)  # 53 categories

# Analyze with specific rules
config = RuffConfig(
    select=["E", "F", "B", "I"],  # Error, Flake8, Bugbear, isort
    extend_select=["UP"],         # Add pyupgrade
    fixable=["I"],                # Only autofix imports
)
parser = RuffParser(config)
report = parser.analyze("src/")

# Apply auto-fixes programmatically
from code_scalpel.code_parser.python_parsers import apply_fix_to_source

fixed = apply_fix_to_source(source_code, ruff_fix)
print(get_fix_preview(source_code, ruff_fix))  # Unified diff
```

### MypyParser - Type Checking

Static type analysis with coverage metrics:

```python
from code_scalpel.code_parser.python_parsers import (
    MypyParser,
    MypyConfig,
    TYPESHED_SUGGESTIONS,
)

config = MypyConfig(
    strict=True,
    python_version="3.11",
    enable_error_codes=["redundant-expr", "truthy-bool"],
)
parser = MypyParser(config)
result = parser.check("src/")

# Type coverage
print(f"Coverage: {result.coverage.coverage_percent:.1f}%")
print(f"Typed functions: {result.coverage.typed_functions}")
print(f"Untyped functions: {result.coverage.untyped_functions}")

# Missing stub suggestions
for error in result.errors:
    if "library stub" in error.message:
        package = error.extract_package_name()
        if package in TYPESHED_SUGGESTIONS:
            print(f"Install: pip install {TYPESHED_SUGGESTIONS[package]}")
```

### PylintParser - Quality Analysis

Comprehensive code quality with scoring:

```python
from code_scalpel.code_parser.python_parsers import (
    PylintParser,
    PylintConfig,
    MESSAGE_CHECKERS,
    PylintChecker,
)

parser = PylintParser()
report = parser.analyze("src/")

# Score analysis
print(f"Score: {report.statistics.score}/10")
if report.statistics.score_delta:
    print(f"Change: {report.statistics.score_delta:+.2f}")

# Group messages by checker
by_checker = parser.get_messages_by_checker(report.messages)
for checker, messages in by_checker.items():
    print(f"{checker.value}: {len(messages)} issues")

# Get quick wins for score improvement
quick_wins = parser.get_quick_wins(report)
for win in quick_wins[:5]:
    print(f"Fix {win['count']} {win['symbol']} issues ({win['reason']})")

# Score improvement suggestions
suggestions = parser.get_score_improvement_suggestions(report)
for s in suggestions:
    print(f"{s['description']}")
```

### BanditParser - Security Analysis

Security vulnerability detection:

```python
from code_scalpel.code_parser.python_parsers import (
    BanditParser,
    BanditConfig,
    BANDIT_PROFILES,
)

# Use a security profile
config = BanditConfig(
    profile=BANDIT_PROFILES["high_severity"],
    confidence_level="MEDIUM",
)
parser = BanditParser(config)
report = parser.scan("src/")

# Analyze issues
for issue in report.issues:
    print(f"[{issue.severity}] {issue.test_id}: {issue.issue_text}")
    print(f"  CWE: {issue.cwe}")
    print(f"  File: {issue.filename}:{issue.line_number}")

# SARIF output for CI/CD
sarif = parser.to_sarif(report)
```

### CodeQualityParser - Metrics

Complexity and maintainability metrics:

```python
from code_scalpel.code_parser.python_parsers import (
    CodeQualityParser,
    ComplexityMetrics,
)

parser = CodeQualityParser()
metrics = parser.analyze_file("example.py")

# Complexity metrics
for func in metrics.functions:
    print(f"{func.name}:")
    print(f"  Cyclomatic: {func.cyclomatic_complexity}")
    print(f"  Cognitive: {func.cognitive_complexity}")
    print(f"  Nesting depth: {func.max_nesting}")

# Maintainability
print(f"Maintainability Index: {metrics.maintainability_index:.1f}")
print(f"Lines of Code: {metrics.loc}")
print(f"Comment Ratio: {metrics.comment_ratio:.1%}")
```

### ProspectorParser - Meta-Linter

Aggregate multiple tools with profile management:

```python
from code_scalpel.code_parser.python_parsers import (
    ProspectorParser,
    ProspectorConfig,
    ProspectorProfileLoader,
    BUILTIN_PROFILES,
)

# Load custom profile
loader = ProspectorProfileLoader()
profile = loader.load_profile(".prospector.yaml")

# Or use built-in profiles
config = ProspectorConfig(
    profile="django",
    strictness="high",
    with_tool=["pylint", "pyflakes", "mccabe"],
)
parser = ProspectorParser(config)
report = parser.analyze("src/")

# Deduplicate cross-tool messages
unique = parser.deduplicate_messages(report.messages)
print(f"Total: {len(report.messages)}, Unique: {len(unique)}")
```

## Configuration Files

### pyproject.toml Support

Most parsers read from `pyproject.toml`:

```toml
[tool.ruff]
line-length = 120
target-version = "py311"
select = ["E", "F", "W", "B", "I"]

[tool.ruff.lint]
extend-select = ["UP"]

[tool.mypy]
python_version = "3.11"
strict = true
warn_unused_ignores = true

[tool.pylint.messages_control]
disable = ["C0114", "C0115"]

[tool.bandit]
skips = ["B101"]
```

### Tool-Specific Files

| Tool | Config Files |
|------|--------------|
| Ruff | `ruff.toml`, `pyproject.toml` |
| mypy | `mypy.ini`, `setup.cfg`, `pyproject.toml` |
| Pylint | `.pylintrc`, `pylintrc`, `setup.cfg`, `pyproject.toml` |
| Bandit | `.bandit`, `bandit.yaml`, `pyproject.toml` |
| Flake8 | `.flake8`, `setup.cfg`, `tox.ini` |
| pydocstyle | `.pydocstyle`, `setup.cfg`, `tox.ini` |

## Implementation Status

All major features are implemented. See `__init__.py` for the complete TODO roadmap.

### Completed Features ✅

| Priority | Feature | Status |
|----------|---------|--------|
| P1 | AST parsing, symbol extraction, scope analysis | ✅ Complete |
| P1 | Ruff integration with auto-fix | ✅ Complete |
| P2 | CFG/DFG generation | ✅ Complete |
| P2 | mypy with JSON output, type coverage | ✅ Complete |
| P2 | Pylint with full message parsing | ✅ Complete |
| P2 | Bandit security analysis | ✅ Complete |
| P3 | Complexity metrics (cyclomatic, cognitive) | ✅ Complete |
| P3 | Import analysis and circular detection | ✅ Complete |
| P3 | Flake8 with plugin support | ✅ Complete |
| P3 | pydocstyle with quality analysis | ✅ Complete |
| P4 | pycodestyle PEP 8 checking | ✅ Complete |
| P5 | Prospector with profile management | ✅ Complete |

### Future Development Roadmap

| Priority | Feature | Status |
|----------|---------|--------|
| P4 | Framework detection (Django, Flask, FastAPI) | 🔜 Planned |
| P4 | Pydantic/dataclass analysis | 🔜 Planned |
| P5 | Inter-procedural analysis | 🔜 Planned |
| P5 | Whole-program dead code detection | 🔜 Planned |
| P5 | Refactoring suggestions | 🔜 Planned |
| P5 | Incremental analysis with caching | 🔜 Planned |

## Design Principles

### Consistent Parser Pattern

Every parser follows the same structure:

```python
@dataclass
class ToolConfig:
    """Configuration dataclass with from_file() classmethod."""
    option: str = "default"
    
    @classmethod
    def from_file(cls, path: str) -> "ToolConfig":
        ...
    
    def to_cli_args(self) -> list[str]:
        ...

@dataclass
class ToolResult:
    """Structured result with severity, location, message."""
    code: str
    message: str
    path: str
    line: int
    column: int
    severity: ToolSeverity

@dataclass
class ToolReport:
    """Aggregated results with statistics."""
    results: list[ToolResult]
    statistics: ToolStatistics

class ToolParser:
    """Main parser interface."""
    
    def __init__(self, config: ToolConfig | None = None):
        self.config = config or ToolConfig()
    
    def analyze(self, path: str) -> ToolReport:
        ...
    
    def analyze_string(self, source: str) -> ToolReport:
        ...
```

### Lazy Loading

Imports are lazy-loaded to minimize startup time:

```python
# Only loads when first accessed
from code_scalpel.code_parser.python_parsers import RuffParser
```

### Type Safety

All public APIs are fully typed with Python 3.12 type hints:
- Generic types for collections
- Union types with `|` syntax
- Optional values properly annotated
- TYPE_CHECKING for import-time optimization

## Dependencies

### Required
- Python 3.10+ (3.11+ recommended for `tomllib`)

### Optional (for specific parsers)
- `ruff` - RuffParser
- `mypy` - MypyParser
- `pylint` - PylintParser
- `bandit` - BanditParser
- `flake8` - Flake8Parser
- `pydocstyle` - PydocstyleParser
- `pycodestyle` - PycodestyleParser
- `prospector` - ProspectorParser
- `pyyaml` - ProspectorParser profile loading
- `tomli` - TOML parsing on Python < 3.11

## Testing

Run the parser tests:

```bash
# All parser tests
pytest tests/test_python_parsers/ -v

# Specific parser
pytest tests/test_python_parsers/test_ruff.py -v
pytest tests/test_python_parsers/test_pylint.py -v

# With coverage
pytest tests/test_python_parsers/ --cov=src/code_scalpel/code_parser/python_parsers
```

## Contributing

When adding a new parser:

1. Create `python_parsers_<tool>.py` following the standard pattern
2. Add exports to `__init__.py` in both `__all__` and `__getattr__`
3. Add a TODO section in file header documenting planned features
4. Write comprehensive tests in `tests/test_python_parsers/`
5. Update this README with the new parser documentation
6. Include TODO comments for NotImplementedError methods
7. Document data structures and output formats
8. Provide API design documentation

## Planned Parsers (Future Development)

The following parser stubs have been created for future implementation:

### IsortParser - Import Sorting and Organization

- **Tool**: [isort](https://pycqa.github.io/isort/)
- **Priority**: P2 - HIGH
- **Status**: NOT IMPLEMENTED
- **Purpose**: Validate import ordering and organization
- **Key Features** (Planned):
  - Check import sorting against isort rules
  - Support multiple profiles (black, django, flask, etc.)
  - Identify import categories (stdlib, third-party, local)
  - Detect unsorted imports and multi-line import handling
  - Configuration parsing from setup.cfg/pyproject.toml

**TODO**:
- [ ] P2-ISORT-001: Parse isort output format
- [ ] P2-ISORT-002: Configuration parsing
- [ ] P2-ISORT-003: Import grouping analysis
- [ ] P2-ISORT-004: Sorting correctness checking
- [ ] P2-ISORT-005: Multi-line import handling

### VultureParser - Dead Code Detection

- **Tool**: [Vulture](https://github.com/jendrikseipp/vulture)
- **Priority**: P2 - HIGH
- **Status**: NOT IMPLEMENTED
- **Purpose**: Find unused code and dead branches
- **Key Features** (Planned):
  - Detect unused imports, variables, functions, classes
  - Track confidence levels for findings
  - Support min-confidence filtering
  - Handle __all__ definitions
  - Identify unreachable code

**TODO**:
- [ ] P2-VULTURE-001: Parse Vulture JSON output
- [ ] P2-VULTURE-002: Configuration parsing
- [ ] P2-VULTURE-003: False positive filtering
- [ ] P2-VULTURE-004: Dead code categorization
- [ ] P2-VULTURE-005: Unused import detection

### RadonParser - Code Complexity Metrics

- **Tool**: [Radon](https://radon.readthedocs.io/)
- **Priority**: P2 - HIGH
- **Status**: NOT IMPLEMENTED
- **Purpose**: Measure code complexity with Cyclomatic Complexity and Maintainability Index
- **Key Features** (Planned):
  - Cyclomatic Complexity (CC) analysis
  - Cognitive Complexity analysis
  - Maintainability Index (MI) calculation
  - Complexity grading (A-F)
  - Function and class-level metrics

**TODO**:
- [ ] P2-RADON-001: Parse Radon CC output
- [ ] P2-RADON-002: Parse Radon MI output
- [ ] P2-RADON-003: Cognitive complexity analysis
- [ ] P2-RADON-004: Function and class metrics
- [ ] P2-RADON-005: Complexity grading system

### SafetyParser - Dependency Security Vulnerabilities

- **Tool**: [Safety](https://safety.readthedocs.io/)
- **Priority**: P2 - HIGH
- **Status**: NOT IMPLEMENTED
- **Purpose**: Check dependencies for known security vulnerabilities
- **Key Features** (Planned):
  - Scan dependencies for CVE/CVSS vulnerabilities
  - Map to CVE/CWE identifiers
  - CVSS scoring and severity levels
  - Support requirements.txt and poetry.lock
  - Remediation suggestions
  - Transitive dependency analysis

**TODO**:
- [ ] P2-SAFETY-001: Parse Safety JSON output
- [ ] P2-SAFETY-002: Vulnerability database querying
- [ ] P2-SAFETY-003: CVE/CWE mapping
- [ ] P2-SAFETY-004: Dependency graph analysis
- [ ] P2-SAFETY-005: Remediation suggestion extraction

### InterrogateParser - Documentation Coverage Analysis

- **Tool**: [Interrogate](https://interrogate.readthedocs.io/)
- **Priority**: P3 - MEDIUM
- **Status**: NOT IMPLEMENTED
- **Purpose**: Measure documentation coverage of docstrings
- **Key Features** (Planned):
  - Calculate documentation coverage percentage
  - Identify undocumented functions, classes, methods
  - Detect docstring styles (NumPy, Google, Sphinx, etc.)
  - Module-level and nested documentation tracking
  - Configuration file support

**TODO**:
- [ ] P3-INTERROGATE-001: Parse Interrogate output format
- [ ] P3-INTERROGATE-002: Coverage calculation and reporting
- [ ] P3-INTERROGATE-003: Configuration parsing
- [ ] P3-INTERROGATE-004: Undocumented item identification
- [ ] P3-INTERROGATE-005: Docstring quality analysis

## License

See [LICENSE](../../../../LICENSE) for details.
