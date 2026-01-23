# C++ Parsers Module Documentation

**Status:** Phase 1 Complete - Infrastructure Ready for Phase 2 Implementation  
**Version:** v1.0.0  
**Last Updated:** 2025-12-21  
**Module Location:** `src/code_scalpel/code_parser/cpp_parsers/`

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

The C++ Parsers module provides comprehensive static analysis infrastructure for C and C++ code, integrating industry-leading static analysis tools, security scanners, and code quality checkers. This module enables AI agents and automated systems to perform surgical C/C++ code analysis without hallucination risk.

### Key Capabilities

- **Deep Static Analysis:** Clang Static Analyzer, Cppcheck, Coverity
- **Security Scanning:** Vulnerability detection, secret detection, taint analysis
- **Code Quality:** Google style enforcement, modernization suggestions
- **Standards Compliance:** MISRA C/C++, CERT, CWE/OWASP mapping
- **Performance Analysis:** Race conditions, memory leaks, inefficient patterns
- **Build Integration:** Seamless CI/CD pipeline integration

### Module Characteristics

| Characteristic | Value |
|---|---|
| Language Support | C (99, 11, 17) and C++ (11, 14, 17, 20, 23) |
| Parser Classes | 6 (Clang-Static-Analyzer, Cppcheck, ClangTidy, CppLint, Coverity, SonarQube) |
| Configuration Formats | YAML, JSON, CMake, SCons |
| Report Formats | JSON, SARIF, PlainText, HTML, XML |
| Severity Levels | Critical, High, Medium, Low, Info, Note |
| CWE Mapping | Full OWASP/CWE categorization (200+ patterns) |

---

## Supported Tools

### 1. Clang Static Analyzer - Deep Bug Detection

**Purpose:** Deep interprocedural static analysis  
**Version:** LLVM 15+  
**Implementation Status:** Phase 1 - Stub ✅

```python
parser = ClangStaticAnalyzerParser(config=ClangConfig(
    checkers="core,security",
    analyze_headers=True,
    max_depth=10
))
issues = parser.analyze_paths(paths=[Path("src/")])
```

**Capabilities:**
- Null pointer dereference detection
- Use-after-free detection
- Memory leak detection
- Division by zero detection
- Integer overflow detection
- Logic error detection
- Dead code detection
- Interprocedural analysis

**Supported Checkers:**
- `core` - Core correctness issues
- `security` - Security-related issues
- `unix` - Unix API usage
- `osx` - macOS-specific issues
- `cplusplus` - C++-specific issues
- `deadcode` - Dead code analysis
- `nullability` - Null pointer checks
- `valist` - Variable argument lists

**Configuration Example:**
```yaml
clang_static_analyzer:
  checkers: ["core", "security", "cplusplus"]
  analyze_headers: true
  analyze_system_headers: false
  max_depth: 10
  enable_checker: "security.insecureAPI"
  report_format: "json"
```

### 2. Cppcheck - Static Code Analysis

**Purpose:** Comprehensive static analysis for C/C++  
**Version:** 2.12+  
**Implementation Status:** Phase 1 - Stub ✅

```python
parser = CppcheckParser(config=CppcheckConfig(
    standard="c++17",
    platform="native",
    enable=["all", "missingInclude"]
))
issues = parser.scan_code(paths=[Path("src/")])
```

**Detects:**
- Memory leaks and resource leaks
- Buffer overflows
- Logic errors
- Unused code (variables, functions, types)
- Style issues
- Performance issues
- MISRA violations
- CWE violations
- Security issues

**Enable Options:**
- `warning` - Production warnings (default)
- `style` - Code style issues
- `performance` - Performance suggestions
- `portability` - Portability issues
- `information` - Informational messages
- `missingInclude` - Missing includes
- `unusedFunction` - Unused functions
- `all` - All checks

**Configuration Example:**
```yaml
cppcheck:
  standard: ["c++17"]
  platform: "native"
  enable: ["all", "missingInclude"]
  inline-suppr: true
  max-configs: 12
  jobs: 4
  suppress:
    - "unusedFunction"
    - "missingInclude"
  suppressions-list: "suppressions.txt"
```

### 3. Clang-Tidy - Modernization & Linting

**Purpose:** C/C++ linting and modernization suggestions  
**Version:** LLVM 15+  
**Implementation Status:** Phase 1 - Stub ✅

```python
parser = ClangTidyParser(config=ClangTidyConfig(
    checks="modernize-*,readability-*",
    fix_suggestions=True
))
issues = parser.lint_code(paths=[Path("src/")])
```

**Check Categories:**
- `modernize-*` - C++11/14/17/20 modernization
- `readability-*` - Readability improvements
- `performance-*` - Performance optimizations
- `portability-*` - Portability improvements
- `cert-*` - CERT C++ guidelines
- `cppcoreguidelines-*` - C++ Core Guidelines
- `google-*` - Google C++ Style Guide
- `llvm-*` - LLVM coding standards

**Notable Checks:**
- `modernize-use-auto` - Use auto for type deduction
- `readability-identifier-naming` - Naming conventions
- `performance-unnecessary-copy-initialization` - Copy elimination
- `cert-err61-cpp` - Exception handling
- `google-readability-braces-around-statements` - Brace style

**Configuration Example:**
```yaml
clang_tidy:
  checks: "modernize-*,readability-*,-readability-magic-numbers"
  header-filter: ".*"
  fix-suggestions: true
  format-style: "google"
  warnings-as-errors: "modernize-*"
```

### 4. CppLint - Google Style Enforcement

**Purpose:** Google C++ Style Guide enforcement  
**Version:** 1.5.5+  
**Implementation Status:** Phase 1 - Stub ✅

```python
parser = CppLintParser(config=CppLintConfig(
    style="google",
    strict=True,
    linelength=80
))
issues = parser.check_style(paths=[Path("src/")])
```

**Checks:**
- Header guard naming
- Namespace definitions
- Include order
- Macro naming
- Line length (configurable)
- Comment style
- Whitespace conventions
- Function documentation
- Type casting style

**Configuration Example:**
```yaml
cpplint:
  style: "google"
  strict: true
  linelength: 80
  extensions: ["cc", "cpp", "h", "hpp"]
  filter: "-legal/copyright,-build/include_what_you_use"
  root: "src"
```

### 5. Coverity - Enterprise Security Analysis

**Purpose:** Deep security and quality analysis  
**Version:** 2023.12+  
**Implementation Status:** Phase 1 - Stub ✅

```python
parser = CoverityParser(config=CoverityConfig(
    checkers_enabled="SECURITY",
    impact="High",
    cwe_mapping=True
))
issues = parser.run_coverity(paths=[Path("src/")])
```

**Analysis Capabilities:**
- Security vulnerabilities (CWE mapping)
- Resource leaks
- Logic errors
- API usage errors
- Concurrency issues
- Memory safety issues
- Integer overflow/underflow
- Type safety issues
- Null pointer dereferences

**Impact Levels:**
- High - Likely real defects
- Medium - Potential issues
- Low - Minor issues
- Info - Informational

**Configuration Example:**
```yaml
coverity:
  checkers_enabled: ["SECURITY", "RESOURCE_LEAK", "NULL_RETURNS"]
  impact: ["High", "Medium"]
  cwe_mapping: true
  report_format: "json"
  intermediate_directory: "cov-int"
```

### 6. SonarQube - Continuous Code Quality

**Purpose:** Comprehensive code quality and security  
**Version:** 9.9+  
**Implementation Status:** Phase 1 - Stub ✅

```python
parser = SonarQubeParser(config=SonarQubeConfig(
    project_key="myproject",
    quality_gate="Sonar Way",
    languages=["c", "cpp"]
))
issues = parser.analyze_code(paths=[Path("src/")])
```

**Analysis Areas:**
- Security vulnerabilities
- Code smells
- Bugs and logic errors
- Duplicated code
- Complexity analysis
- Code coverage gaps
- Technical debt
- Maintainability index

**Quality Gates:**
- Sonar Way (Default)
- Security-focused
- Reliability-focused
- Custom quality gates

**Configuration Example:**
```yaml
sonarqube:
  project_key: "myproject"
  project_name: "My C++ Project"
  quality_gate: "Sonar Way"
  languages: ["c", "cpp"]
  c_cpp_std: "c++17"
  inclusions: ["src/**/*.cpp"]
  exclusions: ["test/**", "third-party/**"]
```

---

## Architecture

### Module Structure

```
cpp_parsers/
├── __init__.py                                    # Factory registry
├── cpp_parsers_Clang-Static-Analyzer.py          # Clang SA parser
├── cpp_parsers_Cppcheck.py                       # Cppcheck parser
├── cpp_parsers_clang_tidy.py                     # Clang-Tidy parser
├── cpp_parsers_cpplint.py                        # CppLint parser
├── cpp_parsers_coverity.py                       # Coverity parser
└── cpp_parsers_sonarqube.py                      # SonarQube parser
```

### Factory Pattern

```python
from code_scalpel.code_parser.cpp_parsers import CppParserFactory

# Create specific parser
parser = CppParserFactory.create("cppcheck")

# Get all available parsers
all_parsers = CppParserFactory.get_all_parsers()

# Get parser metadata
metadata = CppParserFactory.get_parser_metadata("clang_tidy")
```

### Data Flow Architecture

```
C/C++ Source Code
    ↓
Parser Selection (Factory)
    ↓
Tool Execution (with compilation database)
    ↓
Output Parsing (Format-specific)
    ↓
Issue Categorization (CWE/CERT/MISRA)
    ↓
Severity Ranking
    ↓
Report Generation (JSON/SARIF/HTML)
    ↓
Normalized Results
```

---

## Installation & Configuration

### Prerequisites

```bash
# Install LLVM/Clang tools
# macOS
brew install llvm clang-tools cppcheck

# Ubuntu/Debian
sudo apt-get install clang clang-tools clang-tidy cppcheck

# Windows (Visual Studio)
# Included in Visual Studio 2019+
```

### Build System Integration

**CMake Integration:**
```cmake
# CMakeLists.txt
enable_language(C CXX)
set(CMAKE_CXX_STANDARD 17)

# Clang-Tidy
set(CMAKE_CXX_CLANG_TIDY "clang-tidy;-checks=*")

# Cppcheck
set(CMAKE_CXX_CPPCHECK "cppcheck;--enable=all")
```

**Compile Flags:**
```bash
# Generate compilation database
cmake -DCMAKE_EXPORT_COMPILE_COMMANDS=ON

# Run clang-static-analyzer
scan-build -o reports cmake --build .
```

### Configuration Files

Create `.clang-tidy`:
```yaml
---
Checks: "modernize-*,readability-*,performance-*,google-*"
CheckOptions:
  - key: readability-identifier-naming.VariableCase
    value: lower_case
  - key: readability-identifier-naming.FunctionCase
    value: lower_case
HeaderFilterRegex: "src/.*"
WarningsAsErrors: "modernize-*,performance-*"
```

Create `cppcheck.cfg`:
```xml
<?xml version="1.0"?>
<project version="1">
    <paths>
        <exclude>third_party</exclude>
        <exclude>build</exclude>
    </paths>
    <includedir>include</includedir>
    <standards>
        <c>c99</c>
        <cpp>c++17</cpp>
    </standards>
</project>
```

---

## API Reference

### ClangStaticAnalyzerParser

```python
class ClangStaticAnalyzerParser:
    """Clang Static Analyzer for deep bug detection."""
    
    def analyze_paths(self, paths: List[Path]) -> List[Issue]:
        """[20251221_TODO] Run deep static analysis."""
    
    def analyze_function(self, function_name: str, code: str) -> List[Issue]:
        """[20251221_TODO] Analyze specific function."""
    
    def check_null_pointers(self, code: str) -> List[Issue]:
        """[20251221_TODO] Detect null pointer issues."""
    
    def check_memory_leaks(self, code: str) -> List[Issue]:
        """[20251221_TODO] Find memory leak patterns."""
    
    def load_config(self, config_file: Path) -> ClangConfig:
        """[20251221_TODO] Load configuration from file."""
    
    def enable_checker(self, checker_name: str) -> None:
        """[20251221_TODO] Enable specific checker."""
```

### CppcheckParser

```python
class CppcheckParser:
    """Cppcheck static analysis parser."""
    
    def scan_code(self, paths: List[Path]) -> List[Issue]:
        """[20251221_TODO] Run Cppcheck analysis."""
    
    def check_for_leaks(self, code: str) -> List[Issue]:
        """[20251221_TODO] Detect memory/resource leaks."""
    
    def detect_buffer_overflows(self, code: str) -> List[Issue]:
        """[20251221_TODO] Detect buffer overflow patterns."""
    
    def check_misra_compliance(self, code: str) -> List[Issue]:
        """[20251221_TODO] Check MISRA C/C++ compliance."""
    
    def load_suppression_file(self, suppress_file: Path) -> None:
        """[20251221_TODO] Load suppression configuration."""
```

### ClangTidyParser

```python
class ClangTidyParser:
    """Clang-Tidy modernization and linting."""
    
    def lint_code(self, paths: List[Path]) -> List[Issue]:
        """[20251221_TODO] Run clang-tidy linting."""
    
    def suggest_modernization(self, code: str) -> List[Issue]:
        """[20251221_TODO] Suggest C++17/20 improvements."""
    
    def check_readability(self, code: str) -> List[Issue]:
        """[20251221_TODO] Check readability standards."""
    
    def apply_fixes(self, paths: List[Path]) -> bool:
        """[20251221_TODO] Auto-apply suggested fixes."""
    
    def get_fix_suggestions(self, issue: Issue) -> List[str]:
        """[20251221_TODO] Get detailed fix suggestions."""
```

### CppLintParser

```python
class CppLintParser:
    """CppLint Google style enforcement."""
    
    def check_style(self, paths: List[Path]) -> List[Issue]:
        """[20251221_TODO] Check Google C++ style."""
    
    def check_headers(self, code: str) -> List[Issue]:
        """[20251221_TODO] Check header format."""
    
    def check_naming_conventions(self, code: str) -> List[Issue]:
        """[20251221_TODO] Verify naming conventions."""
    
    def load_config(self, config_file: Path) -> CppLintConfig:
        """[20251221_TODO] Load style configuration."""
```

### CoverityParser

```python
class CoverityParser:
    """Coverity deep security analysis."""
    
    def run_coverity(self, paths: List[Path]) -> List[Issue]:
        """[20251221_TODO] Execute Coverity analysis."""
    
    def analyze_security(self, code: str) -> List[Issue]:
        """[20251221_TODO] Security-focused analysis."""
    
    def detect_concurrency_issues(self, code: str) -> List[Issue]:
        """[20251221_TODO] Find race conditions."""
    
    def map_to_cwe(self, issues: List[Issue]) -> Dict[str, List[Issue]]:
        """[20251221_TODO] Map findings to CWE IDs."""
```

### SonarQubeParser

```python
class SonarQubeParser:
    """SonarQube quality and security analysis."""
    
    def analyze_code(self, paths: List[Path]) -> List[Issue]:
        """[20251221_TODO] Run SonarQube analysis."""
    
    def evaluate_quality_gate(self, issues: List[Issue]) -> bool:
        """[20251221_TODO] Check quality gate compliance."""
    
    def calculate_technical_debt(self, issues: List[Issue]) -> float:
        """[20251221_TODO] Calculate remediation time."""
    
    def generate_report(self, issues: List[Issue], format: str) -> str:
        """[20251221_TODO] Generate analysis report."""
```

---

## Integration Examples

### Example 1: Security Analysis Pipeline

```python
from code_scalpel.code_parser.cpp_parsers import CppParserFactory
from pathlib import Path

# Create security-focused parser
parser = CppParserFactory.create("coverity")

# Analyze code
issues = parser.run_coverity([Path("src/")])

# Filter critical issues
critical = [i for i in issues if i.severity == "CRITICAL"]

# Generate report
report = parser.generate_report(critical, format="sarif")
```

### Example 2: Code Quality Compliance

```python
from code_scalpel.code_parser.cpp_parsers import (
    ClangTidyParser,
    CppLintParser
)

# Modernization check
tidy_parser = ClangTidyParser()
modernization_issues = tidy_parser.lint_code([Path("src/")])

# Style check
lint_parser = CppLintParser()
style_issues = lint_parser.check_style([Path("src/")])

# Combined report
all_issues = modernization_issues + style_issues
print(f"Found {len(all_issues)} issues")
for issue in all_issues:
    print(f"  [{issue.severity}] {issue.message}")
```

### Example 3: Multi-Tool Analysis Aggregation

```python
from code_scalpel.code_parser.cpp_parsers import CppParserFactory

tools = ["cppcheck", "clang_static_analyzer", "clang_tidy"]
all_issues = []

for tool in tools:
    parser = CppParserFactory.create(tool)
    issues = parser.analyze([Path("src/")])
    all_issues.extend(issues)

# Deduplicate issues
unique_issues = {}
for issue in all_issues:
    key = f"{issue.file}:{issue.line}:{issue.message}"
    if key not in unique_issues:
        unique_issues[key] = issue

# Export results
import json
with open("analysis_report.json", "w") as f:
    json.dump([i.__dict__ for i in unique_issues.values()], f, indent=2)
```

---

## Phase 2 Roadmap

### Sprint 1: Foundation (Weeks 1-2)
- [20251221_TODO] Implement tool execution via subprocess/API
- [20251221_TODO] Add output parsing for JSON/XML/text formats
- [20251221_TODO] Create compilation database handling
- **Milestone:** All tools can execute and produce normalized output

### Sprint 2: Integration (Weeks 3-4)
- [20251221_TODO] Implement CWE/CERT/MISRA mapping
- [20251221_TODO] Add configuration file loading
- [20251221_TODO] Create report generation (JSON/SARIF/HTML)
- **Milestone:** Full configuration support with normalized output

### Sprint 3: Enhancement (Weeks 5-6)
- [20251221_TODO] Add cross-tool result correlation
- [20251221_TODO] Implement incremental analysis
- [20251221_TODO] Add performance profiling
- **Milestone:** Multi-tool orchestration and result aggregation

### Sprint 4: Testing & Optimization (Weeks 7-8)
- [20251221_TODO] Write 200+ unit tests (95%+ coverage)
- [20251221_TODO] Performance optimization
- [20251221_TODO] Documentation and examples
- **Milestone:** Production-ready C/C++ analysis suite

---

## Troubleshooting

### Common Issues

**Issue:** "Compilation database not found"
```bash
# Solution: Generate compile_commands.json
cmake -DCMAKE_EXPORT_COMPILE_COMMANDS=ON .
```

**Issue:** "Clang-Tidy configuration not being loaded"
```bash
# Verify .clang-tidy format
clang-tidy --dump-config
```

**Issue:** "SonarQube connection failed"
```bash
# Check SonarQube server availability
curl -u admin:admin http://localhost:9000/api/system/status
```

### Performance Tuning

```yaml
# Parallel analysis
clang_tidy:
  jobs: 8
  header_filter: "src/.*"
  
cppcheck:
  jobs: 8
  enable: ["performance"]  # Reduce enabled checks
```

---

## Related Documentation

- [C++ Parser Implementation Details](../modules/cpp_parsers.md)
- [Parser Architecture Guide](../architecture/parser_architecture.md)
- [CWE/CERT/MISRA Mapping](../compliance/standards_mapping.md)
- [AI Agent Integration Guide](../agent_integration.md)

---

**Module Maintainer:** Code Scalpel Team  
**Last Updated:** 2025-12-21  
**License:** MIT
