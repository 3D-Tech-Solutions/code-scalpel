# C# Parsers Module - Quick Start & Development Guide

**Module Status:** Phase 1 Complete - Infrastructure Ready  
**Location:** `src/code_scalpel/code_parser/csharp_parsers/`  
**Parsers:** 6 (ReSharper, Roslyn, StyleCop, SonarQube, FxCop, SecurityCodeScan)

---

## Data Flow Architecture

```
                     .NET/C# Project
                            ↓
         ┌──────────────────┴──────────────────┐
         ↓                                      ↓
    .csproj / .sln                      EditorConfig / Settings
         ↓                                      ↓
    ┌────┴──────────────────────────────────────┘
    ↓
CsharpParserRegistry (Factory)
    ↓
┌───┬────────┬──────────┬──────────┬──────┬──────────────────┐
↓   ↓        ↓          ↓          ↓      ↓                  ↓
ReSharper Roslyn StyleCop SonarQube FxCop SecurityCodeScan
↓   ↓        ↓          ↓          ↓      ↓                  ↓
(xml) (api) (json)    (json)    (xml)   (json)
↓   ↓        ↓          ↓          ↓      ↓                  ↓
└───┴────────┴──────────┴──────────┴──────┴──────────────────┘
               ↓
   Issue Normalization & Categorization
               ↓
    ┌──────────┬──────────┬──────────┐
    ↓          ↓          ↓          ↓
Deduplication CWE Mapping OWASP Top 10 .NET-Specific
    ↓          ↓          ↓          ↓
    └──────────┴──────────┴──────────┘
               ↓
   Unified JSON/SARIF/HTML Report
```

---

## Prioritized TODO Items

### TIER 1: CRITICAL (Foundation - Weeks 1-2)

Essential infrastructure items that block all other development.

1. **CsharpParserRegistry Implementation** [HIGH]
   - File: `__init__.py`
   - Location: Factory pattern implementation
   - Effort: 2-3 days
   - Blocks: All other development
   - TODO: `[20251221_TODO] Create registry factory pattern`

2. **Roslyn Semantic Analysis** [HIGH]
   - File: `csharp_parsers_Roslyn-Analyzers.py`
   - Method: `analyze_semantics()`
   - Effort: 3-4 days
   - Dependencies: CsharpParserRegistry, .NET project loading
   - TODO: `[20251221_TODO] Perform semantic analysis`

3. **ReSharper Integration** [HIGH]
   - File: `csharp_parsers_ReSharper.py`
   - Method: `execute_resharper()`
   - Effort: 2-3 days
   - TODO: `[20251221_TODO] Execute ReSharper analysis`

4. **SecurityCodeScan Execution** [HIGH]
   - File: `csharp_parsers_SecurityCodeScan.py`
   - Method: `scan_security()`
   - Effort: 2-3 days
   - TODO: `[20251221_TODO] Run security vulnerability scan`

### TIER 2: OUTPUT PARSING (Weeks 2-3)

Implement format-specific output parsing for each tool.

5. **Roslyn Output Parsing (API)** [HIGH]
   - File: `csharp_parsers_Roslyn-Analyzers.py`
   - Method: `parse_diagnostic_results()`
   - Effort: 2-3 days
   - TODO: `[20251221_TODO] Parse Roslyn diagnostics`

6. **ReSharper XML Parsing** [HIGH]
   - File: `csharp_parsers_ReSharper.py`
   - Method: `parse_xml_report()`
   - Effort: 2 days
   - TODO: `[20251221_TODO] Parse ReSharper XML output`

7. **StyleCop JSON Parsing** [MEDIUM]
   - File: `csharp_parsers_StyleCop.py`
   - Method: `parse_json_output()`
   - Effort: 1-2 days
   - TODO: `[20251221_TODO] Parse StyleCop JSON report`

8. **SecurityCodeScan JSON Parsing** [MEDIUM]
   - File: `csharp_parsers_SecurityCodeScan.py`
   - Method: `parse_json_report()`
   - Effort: 1-2 days
   - TODO: `[20251221_TODO] Parse vulnerability reports`

### TIER 3: CONFIGURATION & LOADING (Weeks 3-4)

Load configuration from .csproj, .editorconfig, and tool-specific files.

9. **Roslyn Project Loading** [HIGH]
   - File: `csharp_parsers_Roslyn-Analyzers.py`
   - Method: `load_project()`
   - Effort: 2-3 days
   - TODO: `[20251221_TODO] Load .NET project via Roslyn`

10. **EditorConfig Loading** [MEDIUM]
    - File: `csharp_parsers_StyleCop.py`
    - Method: `load_editorconfig()`
    - Effort: 1 day
    - TODO: `[20251221_TODO] Load .editorconfig settings`

11. **ReSharper Config Loading** [MEDIUM]
    - File: `csharp_parsers_ReSharper.py`
    - Method: `load_config()`
    - Effort: 1 day
    - TODO: `[20251221_TODO] Load ReSharper configuration`

12. **SecurityCodeScan Config Loading** [MEDIUM]
    - File: `csharp_parsers_SecurityCodeScan.py`
    - Method: `load_config()`
    - Effort: 1 day
    - TODO: `[20251221_TODO] Load configuration file`

### TIER 4: CATEGORIZATION & MAPPING (Weeks 4-5)

Implement issue categorization, CWE mapping, and OWASP mapping.

13. **Roslyn Null Reference Detection** [MEDIUM]
    - File: `csharp_parsers_Roslyn-Analyzers.py`
    - Method: `detect_null_issues()`
    - Effort: 1-2 days
    - TODO: `[20251221_TODO] Detect null reference issues`

14. **StyleCop Issue Categorization** [MEDIUM]
    - File: `csharp_parsers_StyleCop.py`
    - Method: `categorize_violations()`
    - Effort: 1 day
    - TODO: `[20251221_TODO] Categorize style violations`

15. **SecurityCodeScan CWE Mapping** [HIGH]
    - File: `csharp_parsers_SecurityCodeScan.py`
    - Method: `map_to_cwe()`
    - Effort: 2 days
    - TODO: `[20251221_TODO] Map vulnerabilities to CWE`

16. **OWASP Top 10 Mapping (SecurityCodeScan)** [HIGH]
    - File: `csharp_parsers_SecurityCodeScan.py`
    - Method: `map_to_owasp()`
    - Effort: 2 days
    - TODO: `[20251221_TODO] Map to OWASP Top 10`

### TIER 5: ANALYSIS FEATURES (Weeks 5-6)

Implement advanced analysis capabilities specific to .NET.

17. **ReSharper Refactoring Suggestions** [MEDIUM]
    - File: `csharp_parsers_ReSharper.py`
    - Method: `suggest_refactorings()`
    - Effort: 1-2 days
    - TODO: `[20251221_TODO] Get quick fixes and refactorings`

18. **Code Duplication Detection** [MEDIUM]
    - File: `csharp_parsers_ReSharper.py`
    - Method: `detect_code_duplication()`
    - Effort: 2 days
    - TODO: `[20251221_TODO] Detect duplicate code blocks`

19. **StyleCop Naming Convention Check** [MEDIUM]
    - File: `csharp_parsers_StyleCop.py`
    - Method: `check_naming_conventions()`
    - Effort: 1 day
    - TODO: `[20251221_TODO] Verify naming conventions`

20. **Injection Vulnerability Detection** [HIGH]
    - File: `csharp_parsers_SecurityCodeScan.py`
    - Method: `detect_injection_vulnerabilities()`
    - Effort: 2 days
    - TODO: `[20251221_TODO] Find injection attack patterns`

### TIER 6: .NET-SPECIFIC FEATURES (Weeks 6-7)

Implement .NET ecosystem-specific analysis.

21. **NuGet Vulnerability Scanning** [HIGH]
    - File: `__init__.py` (new feature)
    - Method: `scan_nuget_packages()`
    - Effort: 2-3 days
    - TODO: `[20251221_TODO] Scan NuGet dependencies for CVEs`

22. **Assembly Analysis (FxCop)** [MEDIUM]
    - File: `csharp_parsers_fxcop.py`
    - Method: `analyze_assemblies()`
    - Effort: 2 days
    - TODO: `[20251221_TODO] Analyze compiled assemblies`

23. **API Compatibility Check** [MEDIUM]
    - File: `csharp_parsers_Roslyn-Analyzers.py`
    - Method: `check_api_compatibility()`
    - Effort: 1-2 days
    - TODO: `[20251221_TODO] Check API usage and compatibility`

### TIER 7: REPORTING & OUTPUT (Weeks 7-8)

Implement report generation for all output formats.

24. **Roslyn Report Generation** [MEDIUM]
    - File: `csharp_parsers_Roslyn-Analyzers.py`
    - Method: `generate_report()`
    - Effort: 1 day
    - TODO: `[20251221_TODO] Generate analysis report`

25. **ReSharper Report Generation** [MEDIUM]
    - File: `csharp_parsers_ReSharper.py`
    - Method: `generate_report()`
    - Effort: 1 day
    - TODO: `[20251221_TODO] Generate analysis report`

26. **SecurityCodeScan Report Generation** [MEDIUM]
    - File: `csharp_parsers_SecurityCodeScan.py`
    - Method: `generate_report()`
    - Effort: 1 day
    - TODO: `[20251221_TODO] Generate analysis report`

---

## Module-Level TODOs

**Registry & Aggregation**
- Create CsharpParserRegistry class with factory pattern
- Implement lazy-loading for parser modules
- Add aggregation metrics across multiple parsers
- Implement result deduplication and filtering
- Create unified JSON/SARIF output format

**.NET Ecosystem Integration**
- NuGet vulnerability scanning
- Project file (.csproj) parsing
- Assembly metadata analysis
- Framework compatibility checking
- Roslyn API integration

**Security Analysis**
- Injection detection (SQL, LDAP, XPath)
- Cryptography analysis
- Authentication/authorization checks
- Configuration security analysis

---

## File Structure

```
csharp_parsers/
├── __init__.py                           # Factory registry
├── csharp_parsers_ReSharper.py           # Code quality & refactoring
├── csharp_parsers_Roslyn-Analyzers.py    # Roslyn API analysis
├── csharp_parsers_StyleCop.py            # Style enforcement
├── csharp_parsers_SonarQube.py           # Quality metrics
├── csharp_parsers_fxcop.py               # Microsoft FxCop (NEW)
├── csharp_parsers_SecurityCodeScan.py    # Security scanning (NEW)
└── README.md                             # This file
```

---

## Parser Overview

| Tool | Status | Methods | TODOs | Priority | Effort |
|------|--------|---------|-------|----------|--------|
| ReSharper | Stubbed | 6 | 6 | HIGH | 3d |
| Roslyn | Stubbed | 7 | 7 | HIGH | 3-4d |
| StyleCop | Stubbed | 6 | 6 | MEDIUM | 2-3d |
| SonarQube | Stubbed | 5 | 5 | MEDIUM | 2d |
| FxCop | Stubbed | 5 | 5 | MEDIUM | 2d |
| SecurityCodeScan | Stubbed | 6 | 6 | HIGH | 2-3d |

---

## Development Workflow

### Phase 2 Sprint Structure

**Week 1-2: Foundation**
1. Implement CsharpParserRegistry factory
2. Roslyn project loading and API integration
3. ReSharper and SecurityCodeScan execution

**Week 3-4: Parsing & Config**
1. All output parsers (XML, JSON, API)
2. EditorConfig and project configuration loading
3. .NET-specific settings handling

**Week 5-6: Analysis & Mapping**
1. Issue categorization
2. CWE and OWASP mapping
3. Advanced features (refactoring, duplication detection)
4. NuGet vulnerability scanning

**Week 7-8: Testing & Optimization**
1. Unit tests (150+ tests)
2. Integration tests with real .NET projects
3. Performance optimization
4. Documentation

---

## Quick Reference

### Execute Parser in Development

```python
from csharp_parsers import CsharpParserFactory

# Create parser
parser = CsharpParserFactory.get_parser("roslyn")

# Run analysis on project
issues = parser.analyze_syntax_tree([Path("src/")])

# Generate report
report = parser.generate_report(issues, format="json")
```

### Load .NET Project

```python
from pathlib import Path
parser = CsharpParserFactory.get_parser("roslyn")

# Load project
project_path = Path("MyProject.csproj")
success = parser.load_project(project_path)

# Analyze
issues = parser.analyze_semantics()
```

### Security Scanning

```python
parser = CsharpParserFactory.get_parser("security_code_scan")

# Scan for vulnerabilities
issues = parser.scan_security([Path("src/")])

# Map to CWE
cwe_map = parser.map_to_cwe(issues)
```

---

## Related Documentation

- Full guide: `docs/parsers/CSHARP_PARSERS_README.md` (714 lines)
- Completion status: `docs/parsers/CPLUS_CSHARP_GO_COMPLETION.md`
- Parser architecture: `docs/architecture/parser_architecture.md`
- .NET integration: `docs/guides/dotnet_integration.md`

---

**Last Updated:** 2025-12-21  
**Status:** Phase 1 ✅ | Phase 2 🔄
