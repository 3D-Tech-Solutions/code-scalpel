# Go Parsers Module Documentation

**Status:** Phase 1 Complete - Infrastructure Ready for Phase 2 Implementation  
**Version:** v1.0.0  
**Last Updated:** 2025-12-21  
**Module Location:** `src/code_scalpel/code_parser/go_parsers/`

---

## Table of Contents

1. [Overview](#overview)
2. [Supported Tools](#supported-tools)
3. [Architecture](#architecture)
4. [Installation & Configuration](#installation--configuration)
5. [API Reference](#api-reference)
6. [Integration Examples](#integration-examples)
7. [Phase 2 Roadmap](#phase-2-roadmap)
8. [Troubleshooting](#troubleshooting)

---

## Overview

The Go Parsers module provides comprehensive static analysis infrastructure for Go code, integrating multiple industry-standard linters, security scanners, and code analysis tools. This module enables AI agents and automated systems to perform surgical Go code analysis without hallucination risk.

### Key Capabilities

- **Multi-Linter Integration:** 5 complementary Go linting tools
- **Security Analysis:** Gosec, Staticcheck security patterns
- **Code Quality:** Gofmt formatting, style compliance checking
- **Performance:** Race condition detection, memory analysis
- **Test Coverage:** Go test framework integration
- **Module Dependencies:** Go module validation and vulnerability scanning

### Module Characteristics

| Characteristic | Value |
|---|---|
| Language Support | Go 1.16+ |
| Parser Classes | 6 (Gofmt, Golint, Govet, Staticcheck, Golangci-lint, Gosec) |
| Configuration Formats | YAML, JSON, TOML |
| Report Formats | JSON, SARIF, PlainText |
| Severity Levels | Critical, High, Medium, Low, Info |
| CWE Mapping | Full OWASP/CWE categorization |

---

## Supported Tools

### 1. Gofmt - Go Formatter

**Purpose:** Code formatting and style consistency  
**Version:** Go 1.20+  
**Implementation Status:** Phase 1 - Stub ✅

```python
parser = GofmtParser(config=GofmtConfig(
    line_length=100,
    tab_width=4,
    format_comments=True
))
issues = parser.execute_formatter(paths=[Path("src/")])
```

**Capabilities:**
- Line length enforcement
- Tab/space normalization
- Comment formatting
- Import organization
- Brace style enforcement

**Configuration Example:**
```yaml
gofmt:
  line_length: 100
  tab_width: 4
  format_comments: true
  normalize_newlines: true
```

### 2. Golint - Go Style Lint

**Purpose:** Go stylistic conventions enforcement  
**Version:** Latest  
**Implementation Status:** Phase 1 - Stub ✅

```python
parser = GolintParser(config=GolintConfig(
    enforce_naming: True,
    enforce_comments: True
))
issues = parser.check_style(paths=[Path("pkg/")])
```

**Detects:**
- Poor naming conventions
- Missing package documentation
- Unexported function documentation
- Interface naming patterns
- Exported field documentation

**Configuration Example:**
```yaml
golint:
  enforce_naming: true
  enforce_comments: true
  min_comment_length: 3
  max_line_length: 100
```

### 3. Govet - Go Vet (Static Analyzer)

**Purpose:** Suspicious code pattern detection  
**Version:** Go 1.20+  
**Implementation Status:** Phase 1 - Stub ✅

```python
parser = GovetParser(config=GovetConfig(
    check_unreachable: True,
    check_nil_dereference: True
))
issues = parser.analyze_patterns(paths=[Path("cmd/")])
```

**Detects:**
- Nil pointer dereferences
- Unreachable code
- Unused variables/imports
- Type assertions
- Channel operations
- Printf format strings

**Configuration Example:**
```yaml
govet:
  check_unreachable: true
  check_nil_dereference: true
  check_unused_variables: true
  check_unused_imports: true
  check_channel_operations: true
```

### 4. Staticcheck - Advanced Static Analysis

**Purpose:** Advanced code quality issues and bugs  
**Version:** 2023.1+  
**Implementation Status:** Phase 1 - Stub ✅

```python
parser = StaticcheckParser(config=StaticcheckConfig(
    checks=["all"],
    fail_on_errors: True
))
issues = parser.run_analysis(paths=[Path("internal/")])
```

**Detects:**
- Inefficient code patterns
- Unused code (fields, functions, imports)
- Incorrect API usage
- Resource leaks
- Concurrency issues
- Performance anti-patterns

**Checks Categories:**
- **S (Staticcheck):** Code quality issues
- **ST (Style):** Style-related issues
- **QF (Quickfix):** Quick-fixable issues
- **SA (Simplification):** Code simplification opportunities

**Configuration Example:**
```yaml
staticcheck:
  checks: ["all"]
  fail_on_errors: true
  fail_on_warnings: false
  ignore:
    - U1000  # Unused variable
    - SA4000  # Comparison always true
```

### 5. Golangci-lint - Aggregated Linter

**Purpose:** 100+ linters for comprehensive analysis  
**Version:** 1.55.0+  
**Implementation Status:** Phase 1 - Stub ✅

```python
parser = GolangciLintParser(config=GolangciLintConfig(
    linters=["go", "style", "security"],
    strict: True
))
issues = parser.run_linters(paths=[Path("./")])
```

**Integrated Linters (100+):**
- Formatters: gofmt, goimports, gofumpt
- Analyzers: staticcheck, govet, errcheck
- Style: golint, revive, misspell
- Security: gosec, insecure
- Performance: unused, ineffectual, unparam
- Complexity: cyclop, funlen, cognitive

**Configuration Example:**
```yaml
golangci-lint:
  timeout: 5m
  linters:
    enable:
      - staticcheck
      - gosec
      - errcheck
      - unused
    disable:
      - gochecknoglobals
  linters-settings:
    staticcheck:
      checks: ["all"]
    gosec:
      excludes: ["G204"]
```

### 6. Gosec - Go Security Scanner

**Purpose:** Security vulnerability detection  
**Version:** 2.18.0+  
**Implementation Status:** Phase 1 - Stub ✅

```python
parser = GosecParser(config=GosecConfig(
    exclude_rules=[],
    include_rules=["G201", "G202"]
))
issues = parser.execute_gosec(paths=[Path(".")])
```

**Security Checks:**
- Hardcoded credentials/secrets
- Weak cryptography algorithms
- SQL injection vulnerabilities
- Command injection risks
- XXE vulnerabilities
- Insecure random number generation
- Race conditions
- Buffer overflow patterns
- Unsafe pointer operations
- Path traversal vulnerabilities

**Severity Levels:**
- **CRITICAL:** Immediate security risk
- **HIGH:** Significant security concern
- **MEDIUM:** Moderate risk
- **LOW:** Minor issue
- **INFO:** Informational only

**Configuration Example:**
```yaml
gosec:
  exclude_rules: []
  include_rules:
    - G201  # SQL injection
    - G202  # SQL injection (via format string)
    - G203  # SQL injection (database/sql)
  severity: MEDIUM
  confidence: HIGH
```

---

## Architecture

### Module Structure

```
go_parsers/
├── __init__.py              # Factory registry and exports
├── go_parsers_gofmt.py      # Gofmt parser stub
├── go_parsers_golint.py     # Golint parser stub
├── go_parsers_govet.py      # Govet parser stub
├── go_parsers_staticcheck.py # Staticcheck parser stub
├── go_parsers_golangci_lint.py # Golangci-lint parser stub
└── go_parsers_gosec.py      # Gosec parser stub
```

### Factory Pattern

The module uses a factory pattern for convenient parser instantiation:

```python
from code_scalpel.code_parser.go_parsers import GoParserFactory

# Create specific parser
parser = GoParserFactory.create("golangci_lint")

# Get all available parsers
all_parsers = GoParserFactory.get_all_parsers()

# Get parser metadata
metadata = GoParserFactory.get_parser_metadata("staticcheck")
```

### Data Flow Architecture

```
Input (Go Code)
    ↓
Parser Selection (Factory)
    ↓
Tool Execution (subprocess/API)
    ↓
Output Parsing (Tool-specific)
    ↓
Issue Categorization (CWE/OWASP)
    ↓
Report Generation (JSON/SARIF/PlainText)
    ↓
Output (Normalized Results)
```

### Component Relationships

```
BaseParser
    ├── GofmtParser (Formatting)
    ├── GolintParser (Style)
    ├── GovetParser (Pattern Detection)
    ├── StaticcheckParser (Code Quality)
    ├── GolangciLintParser (Aggregated)
    └── GosecParser (Security)

Common Data Classes:
    ├── Issue / Violation
    ├── SeverityLevel
    ├── IssueCategory
    ├── AnalysisResult
    └── ParserConfig
```

---

## Installation & Configuration

### Prerequisites

```bash
# Go 1.16+ required
go version

# Install all linting tools
go install github.com/golangci/golangci-lint/cmd/golangci-lint@latest
go install honnef.co/go/tools/cmd/staticcheck@latest
go install golang.org/x/lint/golint@latest
go install github.com/securego/gosec/v2/cmd/gosec@latest
go get -u golang.org/x/tools/cmd/goimports
```

### Configuration Files

Create `.golangci.yml` in project root:

```yaml
linters:
  enable:
    - staticcheck
    - gosec
    - errcheck
    - unused
    - goimports
    - gofmt
  disable:
    - unparam
    - cyclop

linters-settings:
  staticcheck:
    checks: ["all"]
  
  gosec:
    severity: MEDIUM
    confidence: HIGH
    
  errcheck:
    check-type-assertions: true
    check-blank: true

issues:
  exclude-rules:
    - path: _test\.go
      linters:
        - gosec
```

Create `.gosec.json`:

```json
{
  "global": {
    "nosec": true,
    "audit": false
  },
  "severity": "MEDIUM",
  "confidence": "HIGH",
  "exclude-dir": [
    "vendor",
    "test"
  ],
  "exclude": [
    "G204",
    "G301",
    "G302"
  ]
}
```

---

## API Reference

### GofmtParser

```python
class GofmtParser:
    """Gofmt code formatter."""
    
    def execute_formatter(self, paths: List[Path]) -> List[Issue]:
        """[20251221_TODO] Execute Gofmt formatting check."""
    
    def check_formatting(self, code: str) -> List[Issue]:
        """[20251221_TODO] Check if code meets Gofmt standards."""
    
    def load_config(self, config_file: Path) -> GofmtConfig:
        """[20251221_TODO] Load Gofmt configuration."""
    
    def categorize_issues(self, issues: List[Issue]) -> Dict:
        """[20251221_TODO] Categorize formatting issues."""
    
    def generate_report(self, issues: List[Issue], format: str) -> str:
        """[20251221_TODO] Generate formatting report."""
```

### GolintParser

```python
class GolintParser:
    """Golint style checker."""
    
    def check_style(self, paths: List[Path]) -> List[Issue]:
        """[20251221_TODO] Check Go style conventions."""
    
    def check_naming(self, code: str) -> List[Issue]:
        """[20251221_TODO] Check naming conventions."""
    
    def check_documentation(self, code: str) -> List[Issue]:
        """[20251221_TODO] Check documentation compliance."""
    
    def load_config(self, config_file: Path) -> GolintConfig:
        """[20251221_TODO] Load Golint configuration."""
```

### GovetParser

```python
class GovetParser:
    """Go vet static analyzer."""
    
    def analyze_patterns(self, paths: List[Path]) -> List[Issue]:
        """[20251221_TODO] Analyze code patterns with govet."""
    
    def check_nil_dereference(self, code: str) -> List[Issue]:
        """[20251221_TODO] Detect nil pointer dereferences."""
    
    def check_type_assertions(self, code: str) -> List[Issue]:
        """[20251221_TODO] Check type assertion safety."""
    
    def check_channels(self, code: str) -> List[Issue]:
        """[20251221_TODO] Analyze channel operations."""
```

### StaticcheckParser

```python
class StaticcheckParser:
    """Staticcheck advanced analyzer."""
    
    def run_analysis(self, paths: List[Path]) -> List[Issue]:
        """[20251221_TODO] Run Staticcheck analysis."""
    
    def check_unused_code(self, code: str) -> List[Issue]:
        """[20251221_TODO] Detect unused code patterns."""
    
    def detect_inefficient_patterns(self, code: str) -> List[Issue]:
        """[20251221_TODO] Find inefficient code patterns."""
    
    def check_api_usage(self, code: str) -> List[Issue]:
        """[20251221_TODO] Verify correct API usage."""
```

### GolangciLintParser

```python
class GolangciLintParser:
    """Golangci-lint aggregated linter."""
    
    def run_linters(self, paths: List[Path]) -> List[Issue]:
        """[20251221_TODO] Run all configured linters."""
    
    def load_config(self, config_file: Path) -> GolangciLintConfig:
        """[20251221_TODO] Load golangci-lint configuration."""
    
    def get_enabled_linters(self) -> List[str]:
        """[20251221_TODO] Get list of enabled linters."""
    
    def categorize_by_linter(self, issues: List[Issue]) -> Dict[str, List[Issue]]:
        """[20251221_TODO] Group issues by source linter."""
```

### GosecParser

```python
class GosecParser:
    """Go security scanner."""
    
    def execute_gosec(self, paths: List[Path]) -> List[SecurityIssue]:
        """[20251221_TODO] Execute Gosec security analysis."""
    
    def parse_json_report(self, report_path: Path) -> List[SecurityIssue]:
        """[20251221_TODO] Parse Gosec JSON report."""
    
    def map_to_cwe(self, issues: List[SecurityIssue]) -> Dict[str, List[SecurityIssue]]:
        """[20251221_TODO] Map vulnerabilities to CWE identifiers."""
    
    def filter_by_severity(self, issues: List[SecurityIssue], min_severity: str) -> List[SecurityIssue]:
        """[20251221_TODO] Filter by severity level."""
```

---

## Integration Examples

### Example 1: Basic Code Analysis

```python
from code_scalpel.code_parser.go_parsers import GoParserFactory
from pathlib import Path

# Create parser
parser = GoParserFactory.create("golangci_lint")

# Analyze code
issues = parser.run_linters([Path("./cmd")])

# Report results
for issue in issues:
    print(f"{issue.severity}: {issue.message}")
```

### Example 2: Security Analysis

```python
from code_scalpel.code_parser.go_parsers import GosecParser

# Create security scanner
parser = GosecParser()

# Run analysis
issues = parser.execute_gosec([Path(".")])

# Filter critical issues
critical = parser.filter_by_severity(issues, "CRITICAL")

# Generate report
report = parser.generate_report(critical, format="json")
```

### Example 3: Multi-Tool Analysis

```python
from code_scalpel.code_parser.go_parsers import GoParserFactory

# Analyze with multiple tools
tools = ["gofmt", "staticcheck", "gosec"]
all_issues = []

for tool in tools:
    parser = GoParserFactory.create(tool)
    issues = parser.analyze(Path("."))
    all_issues.extend(issues)

# Categorize by tool
by_tool = {}
for issue in all_issues:
    if issue.tool not in by_tool:
        by_tool[issue.tool] = []
    by_tool[issue.tool].append(issue)

# Print summary
for tool, issues in by_tool.items():
    print(f"{tool}: {len(issues)} issues found")
```

### Example 4: Configuration-Based Analysis

```python
from code_scalpel.code_parser.go_parsers import GolangciLintParser, GolangciLintConfig
from pathlib import Path
import yaml

# Load configuration
with open(".golangci.yml") as f:
    config_data = yaml.safe_load(f)

# Create parser with config
config = GolangciLintConfig.from_dict(config_data)
parser = GolangciLintParser(config=config)

# Run analysis
issues = parser.run_linters([Path(".")])

# Export report
parser.export_report(issues, "report.json")
```

---

## Phase 2 Roadmap

### Sprint 1: Foundation (Weeks 1-2)
- [20251221_TODO] Implement all parser execute methods
- [20251221_TODO] Add output format parsing (JSON, PlainText, SARIF)
- [20251221_TODO] Create comprehensive error handling
- **Milestone:** All parsers can execute and parse output

### Sprint 2: Integration (Weeks 3-4)
- [20251221_TODO] Implement configuration loading from files
- [20251221_TODO] Add CWE/OWASP mapping for all issue types
- [20251221_TODO] Create report generation pipeline
- **Milestone:** Full configuration support with normalized reports

### Sprint 3: Enhancement (Weeks 5-6)
- [20251221_TODO] Add cross-parser consistency checking
- [20251221_TODO] Implement issue deduplication logic
- [20251221_TODO] Add performance metrics collection
- **Milestone:** Multi-tool result aggregation

### Sprint 4: Testing & Optimization (Weeks 7-8)
- [20251221_TODO] Write 150+ unit tests (95%+ coverage)
- [20251221_TODO] Performance optimization
- [20251221_TODO] Documentation and examples
- **Milestone:** Production-ready parsers

---

## Troubleshooting

### Common Issues

**Issue:** "golangci-lint not found in PATH"
```bash
# Solution: Install golangci-lint
go install github.com/golangci/golangci-lint/cmd/golangci-lint@latest
export PATH=$PATH:$(go env GOPATH)/bin
```

**Issue:** "Gosec returning empty results"
```bash
# Solution: Check configuration
gosec --help
gosec ./...  # Run manually to debug
```

**Issue:** "Configuration not being loaded"
```bash
# Solution: Verify config file location and format
cat .golangci.yml  # Verify YAML syntax
golangci-lint run --print-config  # Print resolved config
```

### Performance Tuning

```yaml
# Optimize for faster analysis
linters:
  fast: true
  disable-all: true
  enable:
    - staticcheck
    - gofmt

timeout: 5m
jobs: 4  # Number of parallel jobs
```

### Debug Mode

```python
import logging

logging.basicConfig(level=logging.DEBUG)
parser = GolangciLintParser(debug=True)
issues = parser.run_linters([Path(".")])
```

---

## Related Documentation

- [Go Parser Implementation Details](../modules/go_parsers.md)
- [Parser Architecture Guide](../architecture/parser_architecture.md)
- [CWE/OWASP Mapping Reference](../compliance/cwe_owasp_mapping.md)
- [Integration Guide for AI Agents](../agent_integration.md)

---

**Module Maintainer:** Code Scalpel Team  
**Last Updated:** 2025-12-21  
**License:** MIT
