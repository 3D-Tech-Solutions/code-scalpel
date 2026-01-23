# C# Parsers Module Documentation

**Status:** Phase 1 Complete - Infrastructure Ready for Phase 2 Implementation  
**Version:** v1.0.0  
**Last Updated:** 2025-12-21  
**Module Location:** `src/code_scalpel/code_parser/csharp_parsers/`

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

The C# Parsers module provides comprehensive static analysis infrastructure for .NET and C# code, integrating industry-standard code analysis tools, security scanners, and quality checkers from Microsoft and the community. This module enables AI agents and automated systems to perform surgical C# code analysis without hallucination risk.

### Key Capabilities

- **Microsoft Ecosystem Integration:** ReSharper, Roslyn, StyleCop integration
- **Security Analysis:** CWE mapping, OWASP compliance, vulnerability detection
- **Code Quality:** Complexity analysis, maintainability index, technical debt
- **Performance Analysis:** Memory profiling, concurrency issue detection
- **Best Practices:** Framework guidelines, design pattern enforcement
- **NuGet Vulnerability Scanning:** Supply chain security

### Module Characteristics

| Characteristic | Value |
|---|---|
| Language Support | C# 7.0 - 12.0, .NET Framework 4.5+ and .NET Core/5+ |
| Parser Classes | 6 (ReSharper, Roslyn, StyleCop, SonarQube, FxCop, SecurityCodeScan) |
| Configuration Formats | XML, JSON, YAML, .editorconfig |
| Report Formats | JSON, SARIF, PlainText, HTML, XML |
| Severity Levels | Critical, Error, Warning, Info, Hint |
| CWE Mapping | Full OWASP/CWE categorization (150+ patterns) |

---

## Supported Tools

### 1. ReSharper - Code Quality & Refactoring

**Purpose:** Comprehensive C# code quality and refactoring suggestions  
**Version:** 2023.3+  
**Implementation Status:** Phase 1 - Stub ✅

```python
parser = ResharperParser(config=ResharperConfig(
    severity_level="WARNING",
    enable_refactorings=True,
    culture="en-US"
))
issues = parser.analyze_code(paths=[Path("src/")])
```

**Capabilities:**
- 2000+ code analysis rules
- Quick-fix suggestions
- Refactoring recommendations
- Code duplication detection
- Dead code elimination
- Performance optimizations
- Security analysis
- Framework best practices

**Rule Categories:**
- **GEN** - General C# rules
- **PERF** - Performance issues
- **SECUR** - Security issues
- **BUG** - Bug patterns
- **DESIGN** - Design pattern violations
- **STYLE** - Coding style issues
- **DEPLOY** - Deployment-time issues
- **LANG** - Language feature issues

**Configuration Example:**
```yaml
resharper:
  severity_level: "WARNING"
  enable_refactorings: true
  enable_dead_code: true
  ignore_code_style_violations: false
  custom_rules: "custom_rules.xml"
```

### 2. Roslyn - .NET Compiler API Analysis

**Purpose:** Code analysis via Microsoft Roslyn compiler  
**Version:** Latest SDK  
**Implementation Status:** Phase 1 - Stub ✅

```python
parser = RoslynParser(config=RoslynConfig(
    target_framework="net6.0",
    language_version="11.0"
))
issues = parser.analyze_syntax_tree(paths=[Path("src/")])
```

**Capabilities:**
- Full syntax tree analysis
- Semantic analysis
- Control flow analysis
- Type checking
- Symbol resolution
- Refactoring API integration
- Diagnostic collector
- Code generator support

**Analysis Types:**
- Syntax errors
- Semantic errors
- Code generation analysis
- API compatibility
- Deprecated API usage
- Type safety issues
- Null reference analysis

**Configuration Example:**
```yaml
roslyn:
  target_framework: "net6.0"
  language_version: "11"
  nullable_context: "enable"
  enable_analyzers: true
  analyzer_packages:
    - "Microsoft.CodeAnalysis.NetAnalyzers"
    - "SecurityCodeScan"
```

### 3. StyleCop - Style & Formatting

**Purpose:** C# coding style enforcement  
**Version:** 1.2.0+  
**Implementation Status:** Phase 1 - Stub ✅

```python
parser = StyleCopParser(config=StyleCopConfig(
    max_line_length=120,
    indent_style="spaces",
    indent_size=4
))
issues = parser.check_style(paths=[Path("src/")])
```

**Checks:**
- Spacing and indentation
- Naming conventions
- Documentation (XML comments)
- Ordering of code elements
- Readability (line length, complexity)
- Maintainability rules
- Unsafe code usage
- File headers and copyrights

**Rule Groups:**
- **SA00** - Special rules
- **SA10** - Spacing rules
- **SA11** - Readability rules
- **SA12** - Ordering rules
- **SA13** - Naming rules
- **SA14** - Maintainability rules
- **SA15** - Documentation rules
- **SA16** - Layout rules

**Configuration Example:**
```yaml
stylecop:
  max_line_length: 120
  indent_style: "spaces"
  indent_size: 4
  require_xml_comments: true
  require_file_header: true
  namespace_declaration_style: "file_scoped"
```

### 4. SonarQube/SonarAnalyzer - Code Quality & Security

**Purpose:** Continuous quality and security analysis  
**Version:** 9.9+  
**Implementation Status:** Phase 1 - Stub ✅

```python
parser = SonarQubeParser(config=SonarQubeConfig(
    project_key="myproject",
    quality_gate="Sonar Way",
    languages=["cs"]
))
issues = parser.analyze_code(paths=[Path("src/")])
```

**Analysis Areas:**
- Security vulnerabilities (CWE/OWASP mapping)
- Code smells
- Bugs and logic errors
- Duplicated code
- Code coverage
- Technical debt
- Maintainability
- Complexity metrics

**Security Rules:**
- Weak cryptography
- SQL injection
- Cross-site scripting (XSS)
- Authentication bypass
- LDAP injection
- Insecure deserialization
- XXE vulnerabilities
- Command injection

**Configuration Example:**
```yaml
sonarqube:
  project_key: "myproject"
  project_name: "My C# Project"
  quality_gate: "Sonar Way"
  dotnet_version: "6.0"
  language_version: "11"
```

### 5. FxCop - Microsoft Code Analysis

**Purpose:** Microsoft security and correctness analysis  
**Version:** Built into Visual Studio  
**Implementation Status:** Phase 1 - Stub ✅

```python
parser = FxCopParser(config=FxCopConfig(
    ruleset="Microsoft All Rules",
    treat_warnings_as_errors=True
))
issues = parser.analyze_assemblies(paths=[Path("bin/")])
```

**Rule Categories:**
- **Design** - Design guidelines
- **Globalization** - Internationalization
- **Interoperability** - COM/P/Invoke compatibility
- **Maintainability** - Code maintenance
- **Mobility** - Mobile optimization
- **Naming** - Naming conventions
- **Performance** - Performance issues
- **Portability** - Framework compatibility
- **Reliability** - Reliability issues
- **Security** - Security vulnerabilities
- **Usage** - API usage correctness

**Configuration Example:**
```yaml
fxcop:
  ruleset: "Microsoft All Rules"
  treat_warnings_as_errors: true
  generate_report: true
  report_format: "sarif"
```

### 6. SecurityCodeScan - Security Vulnerability Detection

**Purpose:** Security-focused code analysis for .NET  
**Version:** 5.2+  
**Implementation Status:** Phase 1 - Stub ✅

```python
parser = SecurityCodeScanParser(config=SecurityCodeScanConfig(
    audit_mode=True,
    cwe_mapping=True
))
issues = parser.scan_security(paths=[Path("src/")])
```

**Security Checks:**
- SQL injection vulnerabilities
- XXE (XML External Entity)
- LDAP injection
- XPath injection
- Hardcoded credentials/secrets
- Weak cryptography
- Insecure deserialization (BinaryFormatter)
- Cross-site scripting (XSS)
- Command injection
- Path traversal
- Insecure randomness
- Cookie security
- CORS misconfiguration
- Authentication issues

**Severity Mapping:**
- `SCS0001` - Hardcoded password
- `SCS0005` - Weak random generator
- `SCS0006` - Weak hashing
- `SCS0007` - XML entity expansion
- `SCS0009` - Missing CSRF token
- `SCS0016` - Controller missing authorization
- `SCS0027` - Open redirect
- `SCS0031` - Hardcoded connection string

**Configuration Example:**
```yaml
security_code_scan:
  audit_mode: true
  cwe_mapping: true
  owasp_mapping: true
  exclude_codes:
    - "SCS0001"
  severity_minimum: "INFO"
```

---

## Architecture

### Module Structure

```
csharp_parsers/
├── __init__.py                              # Factory registry
├── csharp_parsers_resharper.py              # ReSharper parser
├── csharp_parsers_roslyn.py                 # Roslyn parser
├── csharp_parsers_stylecop.py               # StyleCop parser
├── csharp_parsers_sonarqube.py              # SonarQube parser
├── csharp_parsers_fxcop.py                  # FxCop parser
└── csharp_parsers_SecurityCodeScan.py       # SecurityCodeScan parser
```

### Factory Pattern

```python
from code_scalpel.code_parser.csharp_parsers import CsharpParserFactory

# Create specific parser
parser = CsharpParserFactory.create("roslyn")

# Get all available parsers
all_parsers = CsharpParserFactory.get_all_parsers()

# Get parser metadata
metadata = CsharpParserFactory.get_parser_metadata("security_code_scan")
```

### Component Relationships

```
.NET Project Structure
    ↓
Parser Selection (by tool)
    ↓
Tool Execution (Roslyn API / subprocess)
    ↓
Output Parsing (Tool-specific formats)
    ↓
Issue Categorization (CWE/OWASP mapping)
    ↓
Severity & Priority Ranking
    ↓
Report Generation (JSON/SARIF/HTML)
    ↓
Normalized Results
```

---

## Installation & Configuration

### Prerequisites

```bash
# .NET SDK 6.0+
dotnet --version

# Install global tools
dotnet tool install -g SecurityCodeScan
dotnet tool install -g SonarScanner.MSBuild
```

### Project Configuration

**.csproj or .slnf settings:**
```xml
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>net6.0</TargetFramework>
    <LangVersion>11</LangVersion>
    <Nullable>enable</Nullable>
    
    <!-- Enable analyzers -->
    <EnableNETAnalyzers>true</EnableNETAnalyzers>
    <AnalysisLevel>latest</AnalysisLevel>
    
    <!-- Code analysis -->
    <CodeAnalysisTreatWarningsAsErrors>true</CodeAnalysisTreatWarningsAsErrors>
    <EnforceCodeStyleInBuild>true</EnforceCodeStyleInBuild>
  </PropertyGroup>
</Project>
```

### Configuration Files

Create `.editorconfig`:
```ini
root = true

[*.cs]
indent_style = space
indent_size = 4
max_line_length = 120
csharp_style_braces = required
csharp_style_namespace_declarations = file_scoped

# Naming conventions
dotnet_naming_style.pascal_case_style.required_prefix = 
dotnet_naming_style.pascal_case_style.capitalization = pascal_case
```

Create `stylecop.json`:
```json
{
  "$schema": "https://raw.githubusercontent.com/DotNetAnalyzers/StyleCopAnalyzers/master/StyleCop.Analyzers/StyleCop.Analyzers/Settings/stylecop.schema.json",
  "settings": {
    "documentationRules": {
      "documentExposedElements": true,
      "documentInternalElements": false,
      "documentPrivateElements": false,
      "documentInterfaces": true,
      "documentPrivateFields": false
    },
    "maintainabilityRules": {
      "topLevelTypes": ["namespace"],
      "statementMustNotUseMultipleLines": true,
      "accessModifierMustBeDeclaredExplicitly": "explicit"
    }
  }
}
```

---

## API Reference

### ResharperParser

```python
class ResharperParser:
    """ReSharper code quality analysis."""
    
    def analyze_code(self, paths: List[Path]) -> List[Issue]:
        """[20251221_TODO] Run ReSharper analysis."""
    
    def get_quick_fixes(self, issue: Issue) -> List[str]:
        """[20251221_TODO] Get available quick fixes."""
    
    def detect_code_duplication(self, code: str) -> List[Issue]:
        """[20251221_TODO] Find duplicate code blocks."""
    
    def suggest_refactorings(self, code: str) -> List[Issue]:
        """[20251221_TODO] Suggest refactoring opportunities."""
    
    def load_config(self, config_file: Path) -> ResharperConfig:
        """[20251221_TODO] Load ReSharper configuration."""
```

### RoslynParser

```python
class RoslynParser:
    """Roslyn .NET Compiler API analysis."""
    
    def analyze_syntax_tree(self, paths: List[Path]) -> List[Issue]:
        """[20251221_TODO] Analyze syntax trees."""
    
    def analyze_semantics(self, code: str) -> List[Issue]:
        """[20251221_TODO] Perform semantic analysis."""
    
    def check_api_compatibility(self, code: str) -> List[Issue]:
        """[20251221_TODO] Check API usage and compatibility."""
    
    def detect_null_issues(self, code: str) -> List[Issue]:
        """[20251221_TODO] Detect potential null reference issues."""
    
    def load_project(self, project_path: Path) -> bool:
        """[20251221_TODO] Load .NET project."""
```

### StyleCopParser

```python
class StyleCopParser:
    """StyleCop code style enforcement."""
    
    def check_style(self, paths: List[Path]) -> List[Issue]:
        """[20251221_TODO] Check code style compliance."""
    
    def check_naming_conventions(self, code: str) -> List[Issue]:
        """[20251221_TODO] Verify naming conventions."""
    
    def check_documentation(self, code: str) -> List[Issue]:
        """[20251221_TODO] Validate XML documentation."""
    
    def check_spacing(self, code: str) -> List[Issue]:
        """[20251221_TODO] Check spacing and indentation."""
    
    def load_config(self, config_file: Path) -> StyleCopConfig:
        """[20251221_TODO] Load StyleCop configuration."""
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
    
    def map_to_owasp(self, issues: List[Issue]) -> Dict[str, List[Issue]]:
        """[20251221_TODO] Map issues to OWASP Top 10."""
```

### FxCopParser

```python
class FxCopParser:
    """FxCop Microsoft code analysis."""
    
    def analyze_assemblies(self, paths: List[Path]) -> List[Issue]:
        """[20251221_TODO] Analyze compiled assemblies."""
    
    def check_design_rules(self, code: str) -> List[Issue]:
        """[20251221_TODO] Check design guidelines."""
    
    def check_security_rules(self, code: str) -> List[Issue]:
        """[20251221_TODO] Check security compliance."""
    
    def load_ruleset(self, ruleset_file: Path) -> None:
        """[20251221_TODO] Load FxCop ruleset."""
```

### SecurityCodeScanParser

```python
class SecurityCodeScanParser:
    """SecurityCodeScan vulnerability detection."""
    
    def scan_security(self, paths: List[Path]) -> List[SecurityIssue]:
        """[20251221_TODO] Run security vulnerability scan."""
    
    def detect_injection_vulnerabilities(self, code: str) -> List[SecurityIssue]:
        """[20251221_TODO] Find injection attack patterns."""
    
    def detect_cryptography_issues(self, code: str) -> List[SecurityIssue]:
        """[20251221_TODO] Check cryptography usage."""
    
    def map_to_cwe(self, issues: List[SecurityIssue]) -> Dict[str, List[SecurityIssue]]:
        """[20251221_TODO] Map vulnerabilities to CWE IDs."""
```

---

## Integration Examples

### Example 1: Security-First Analysis

```python
from code_scalpel.code_parser.csharp_parsers import SecurityCodeScanParser
from pathlib import Path

# Run security analysis
parser = SecurityCodeScanParser()
issues = parser.scan_security([Path("src/")])

# Filter by severity
critical = [i for i in issues if i.severity == "CRITICAL"]

# Map to CWE
cwe_map = parser.map_to_cwe(critical)

# Report findings
for cwe, vulns in cwe_map.items():
    print(f"{cwe}: {len(vulns)} vulnerabilities")
```

### Example 2: Multi-Tool Quality Gate

```python
from code_scalpel.code_parser.csharp_parsers import CsharpParserFactory
from pathlib import Path

# Analyze with multiple tools
tools = ["roslyn", "stylecop", "security_code_scan"]
all_issues = []

for tool in tools:
    parser = CsharpParserFactory.create(tool)
    issues = parser.analyze([Path("src/")])
    all_issues.extend(issues)

# Check quality gate
errors = [i for i in all_issues if i.severity in ["ERROR", "CRITICAL"]]
if errors:
    print(f"Quality gate FAILED: {len(errors)} errors")
    for error in errors:
        print(f"  {error.file}:{error.line} - {error.message}")
else:
    print("Quality gate PASSED")
```

### Example 3: Code Duplication Detection

```python
from code_scalpel.code_parser.csharp_parsers import ResharperParser
from pathlib import Path

# Find code duplication
parser = ResharperParser()
duplicates = parser.detect_code_duplication(Path("src/"))

# Group by severity
by_severity = {}
for dup in duplicates:
    if dup.severity not in by_severity:
        by_severity[dup.severity] = []
    by_severity[dup.severity].append(dup)

# Report
for severity, issues in sorted(by_severity.items()):
    print(f"{severity}: {len(issues)} duplications found")
```

---

## Phase 2 Roadmap

### Sprint 1: Foundation (Weeks 1-2)
- [20251221_TODO] Implement tool execution via Roslyn API / subprocess
- [20251221_TODO] Add output parsing for all format types
- [20251221_TODO] Create .NET project loading
- **Milestone:** All tools can execute and parse output

### Sprint 2: Integration (Weeks 3-4)
- [20251221_TODO] Implement CWE/OWASP mapping
- [20251221_TODO] Add configuration file support
- [20251221_TODO] Create report generation (JSON/SARIF/HTML)
- **Milestone:** Full configuration support

### Sprint 3: Enhancement (Weeks 5-6)
- [20251221_TODO] Add cross-tool result correlation
- [20251221_TODO] Implement NuGet vulnerability scanning
- [20251221_TODO] Add code complexity metrics
- **Milestone:** Advanced analysis features

### Sprint 4: Testing & Optimization (Weeks 7-8)
- [20251221_TODO] Write 180+ unit tests (95%+ coverage)
- [20251221_TODO] Performance optimization
- [20251221_TODO] Documentation and examples
- **Milestone:** Production-ready C# analysis suite

---

## Troubleshooting

### Common Issues

**Issue:** "Roslyn project loading failed"
```bash
# Solution: Verify .NET SDK installation
dotnet --version
# Ensure MSBuild is available
dotnet --list-sdks
```

**Issue:** "SecurityCodeScan not finding vulnerabilities"
```bash
# Ensure SecurityCodeScan is installed
dotnet tool list -g
# Or update project reference
dotnet add package SecurityCodeScan
```

**Issue:** "SonarQube connection failed"
```bash
# Check SonarQube server
curl -u admin:admin http://localhost:9000/api/system/status
```

---

## Related Documentation

- [C# Parser Implementation](../modules/csharp_parsers.md)
- [Parser Architecture Guide](../architecture/parser_architecture.md)
- [CWE/OWASP Mapping Reference](../compliance/cwe_owasp_mapping.md)
- [AI Agent Integration Guide](../agent_integration.md)

---

**Module Maintainer:** Code Scalpel Team  
**Last Updated:** 2025-12-21  
**License:** MIT
