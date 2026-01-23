# C++ Parsers Module - Quick Start & Development Guide

**Module Status:** Phase 1 Complete - Infrastructure Ready  
**Location:** `src/code_scalpel/code_parser/cpp_parsers/`  
**Parsers:** 6 (Clang-Static-Analyzer, Cppcheck, ClangTidy, CppLint, Coverity, SonarQube)

---

## Data Flow Architecture

```
                        C++ Source Code
                              ↓
                    ┌─────────┴─────────┐
                    ↓                   ↓
            Compilation Database    Build Configuration
                    ↓                   ↓
         ┌──────────┴──────────────────┘
         ↓
    CppParserRegistry (Factory)
         ↓
    ┌─────┬──────┬────────┬────────┬──────────┬─────────┐
    ↓     ↓      ↓        ↓        ↓          ↓         ↓
  ClangSA Cppcheck ClangTidy CppLint Coverity SonarQube
    ↓     ↓      ↓        ↓        ↓          ↓         ↓
  (scan) (xml) (json)  (txt)    (json)    (json)
    ↓     ↓      ↓        ↓        ↓          ↓         ↓
    └─────┴──────┴────────┴────────┴──────────┴─────────┘
                         ↓
            Issue Normalization & Categorization
                         ↓
            ┌────────────┬────────────┐
            ↓            ↓            ↓
        Deduplication  CWE Mapping  Severity Ranking
            ↓            ↓            ↓
            └────────────┴────────────┘
                         ↓
            Unified JSON/SARIF/HTML Report
```

---

## Prioritized TODO Items

### TIER 1: CRITICAL (Foundation - Weeks 1-2)

These must be completed first; all other tasks depend on them.

1. **CppParserRegistry Implementation** [HIGH]
   - File: `__init__.py`
   - Location: Factory `get_parser()` method
   - Effort: 2-3 days
   - Blocks: All other development
   - TODO: `[20251221_TODO] Create CppParserRegistry class with factory pattern`

2. **ClangStaticAnalyzer Tool Execution** [HIGH]
   - File: `cpp_parsers_Clang-Static-Analyzer.py`
   - Method: `execute_analysis()`
   - Effort: 3-4 days
   - Dependencies: CppParserRegistry, compilation database
   - TODO: `[20251221_TODO] Execute scan-build analysis`

3. **Cppcheck Tool Execution** [HIGH]
   - File: `cpp_parsers_Cppcheck.py`
   - Method: `execute_cppcheck()`
   - Effort: 2-3 days
   - Dependencies: CppParserRegistry
   - TODO: `[20251221_TODO] Execute Cppcheck analysis`

### TIER 2: OUTPUT PARSING (Weeks 2-3)

Implement output format parsing for all tools.

4. **Clang-SA Output Parsing (Plist Format)** [HIGH]
   - File: `cpp_parsers_Clang-Static-Analyzer.py`
   - Method: `parse_plist_report()`
   - Effort: 2-3 days
   - TODO: `[20251221_TODO] Parse Clang plist report format`

5. **Cppcheck XML Parsing** [HIGH]
   - File: `cpp_parsers_Cppcheck.py`
   - Method: `parse_xml_report()`
   - Effort: 2 days
   - TODO: `[20251221_TODO] Parse Cppcheck XML report`

6. **ClangTidy JSON Parsing** [HIGH]
   - File: `cpp_parsers_clang_tidy.py`
   - Method: `parse_json_output()`
   - Effort: 2 days
   - TODO: `[20251221_TODO] Parse Clang-Tidy JSON report`

7. **CppLint Text Output Parsing** [MEDIUM]
   - File: `cpp_parsers_cpplint.py`
   - Method: `parse_output()`
   - Effort: 1-2 days
   - TODO: `[20251221_TODO] Parse CppLint output format`

### TIER 3: CONFIGURATION & LOADING (Weeks 3-4)

Load configuration from files for each parser.

8. **Clang-SA Configuration Loading** [MEDIUM]
   - File: `cpp_parsers_Clang-Static-Analyzer.py`
   - Method: `load_config()`
   - Effort: 1 day
   - TODO: `[20251221_TODO] Load configuration file`

9. **Cppcheck Configuration Loading** [MEDIUM]
   - File: `cpp_parsers_Cppcheck.py`
   - Method: `load_config()`
   - Effort: 1 day
   - TODO: `[20251221_TODO] Load cppcheck configuration`

10. **ClangTidy Configuration Loading** [MEDIUM]
    - File: `cpp_parsers_clang_tidy.py`
    - Method: `load_config()`
    - Effort: 1 day
    - TODO: `[20251221_TODO] Load .clang-tidy configuration`

11. **CppLint Filter Loading** [MEDIUM]
    - File: `cpp_parsers_cpplint.py`
    - Method: `load_filter_config()`
    - Effort: 1 day
    - TODO: `[20251221_TODO] Load filter configuration`

### TIER 4: CATEGORIZATION & MAPPING (Weeks 4-5)

Implement issue categorization and standard mappings.

12. **ClangSA Memory Bug Filtering** [MEDIUM]
    - File: `cpp_parsers_Clang-Static-Analyzer.py`
    - Method: `filter_memory_bugs()`
    - Effort: 1 day
    - TODO: `[20251221_TODO] Filter for memory-related bugs`

13. **Cppcheck Issue Categorization** [MEDIUM]
    - File: `cpp_parsers_Cppcheck.py`
    - Method: `categorize_issues()`
    - Effort: 2 days
    - TODO: `[20251221_TODO] Categorize issues by category`

14. **ClangTidy Check Categorization** [MEDIUM]
    - File: `cpp_parsers_clang_tidy.py`
    - Method: `categorize_checks()`
    - Effort: 1 day
    - TODO: `[20251221_TODO] Categorize checks by category`

15. **Coverity CWE Mapping** [HIGH]
    - File: `cpp_parsers_coverity.py`
    - Method: `map_to_cwe()`
    - Effort: 2-3 days
    - TODO: `[20251221_TODO] Map defects to CWE identifiers`

### TIER 5: ANALYSIS FEATURES (Weeks 5-6)

Implement advanced analysis capabilities.

16. **Memory Leak Detection (Cppcheck)** [MEDIUM]
    - File: `cpp_parsers_Cppcheck.py`
    - Method: `detect_memory_leaks()`
    - Effort: 1 day
    - TODO: `[20251221_TODO] Filter for memory-related issues`

17. **Modernization Checks (ClangTidy)** [MEDIUM]
    - File: `cpp_parsers_clang_tidy.py`
    - Method: `filter_modernization_checks()`
    - Effort: 1 day
    - TODO: `[20251221_TODO] Filter for modernization checks`

18. **Security Analysis (Coverity)** [HIGH]
    - File: `cpp_parsers_coverity.py`
    - Method: `analyze_security()`
    - Effort: 2 days
    - TODO: `[20251221_TODO] Analyze security vulnerabilities`

19. **Path Extraction (ClangSA)** [MEDIUM]
    - File: `cpp_parsers_Clang-Static-Analyzer.py`
    - Method: `extract_execution_paths()`
    - Effort: 2 days
    - TODO: `[20251221_TODO] Extract execution paths leading to bugs`

### TIER 6: REPORTING & OUTPUT (Weeks 6-7)

Implement report generation for all output formats.

20. **ClangSA Report Generation** [MEDIUM]
    - File: `cpp_parsers_Clang-Static-Analyzer.py`
    - Method: `generate_report()`
    - Effort: 1 day
    - TODO: `[20251221_TODO] Generate analysis report`

21. **Cppcheck Report Generation** [MEDIUM]
    - File: `cpp_parsers_Cppcheck.py`
    - Method: `generate_report()`
    - Effort: 1 day
    - TODO: `[20251221_TODO] Generate analysis report`

22. **ClangTidy Report Generation** [MEDIUM]
    - File: `cpp_parsers_clang_tidy.py`
    - Method: `generate_report()`
    - Effort: 1 day
    - TODO: `[20251221_TODO] Generate analysis report`

### TIER 7: OPTIMIZATION & FEATURES (Weeks 7-8)

Final enhancements and optimization.

23. **C++ Standard Compatibility Check** [MEDIUM]
    - File: `cpp_parsers_clang_tidy.py`
    - Method: `check_cpp_standard_compatibility()`
    - Effort: 2 days
    - TODO: `[20251221_TODO] Analyze C++ standard compatibility`

24. **Style Compliance Score (CppLint)** [LOW]
    - File: `cpp_parsers_cpplint.py`
    - Method: `calculate_compliance_score()`
    - Effort: 1 day
    - TODO: `[20251221_TODO] Calculate overall style compliance score`

25. **Defect Trend Analysis (Coverity)** [LOW]
    - File: `cpp_parsers_coverity.py`
    - Method: `analyze_trends()`
    - Effort: 2 days
    - TODO: `[20251221_TODO] Analyze defect trends over time`

---

## Module-Level TODOs

**Registry & Aggregation**
- Create CppParserRegistry class with factory pattern
- Implement lazy-loading for parser modules
- Add aggregation metrics across multiple parsers
- Implement result deduplication and filtering
- Create unified JSON/SARIF output format

**C++ Specific Features**
- Memory management issue detection
- Template instantiation tracking
- Macro expansion analysis
- Include dependency analysis
- C++ standard version compatibility
- Header guard validation
- Namespace organization analysis

---

## File Structure

```
cpp_parsers/
├── __init__.py                           # Factory registry (60 lines)
├── cpp_parsers_Clang-Static-Analyzer.py  # Deep bug detection (145 lines)
├── cpp_parsers_Cppcheck.py               # Static analysis (130 lines)
├── cpp_parsers_clang_tidy.py             # Modernization (120 lines)
├── cpp_parsers_cpplint.py                # Google style (90 lines)
├── cpp_parsers_coverity.py               # Security analysis (110 lines)
├── cpp_parsers_SonarQube.py              # Code quality (100 lines)
└── README.md                             # This file
```

---

## Parser Overview

| Tool | Lines | Methods | TODOs | Priority | Effort |
|------|-------|---------|-------|----------|--------|
| Clang-SA | 145 | 8 | 8 | HIGH | 3-4d |
| Cppcheck | 130 | 8 | 8 | HIGH | 3-4d |
| ClangTidy | 120 | 8 | 8 | MEDIUM | 3d |
| CppLint | 90 | 6 | 6 | MEDIUM | 2d |
| Coverity | 110 | 8 | 8 | HIGH | 3-4d |
| SonarQube | 100 | 6 | 6 | MEDIUM | 2-3d |

---

## Development Workflow

### Phase 2 Sprint Structure

**Week 1-2: Foundation**
1. Implement CppParserRegistry factory
2. Tool execution for ClangSA and Cppcheck
3. Basic output parsing

**Week 3-4: Integration**
1. All tool execution methods
2. All output parsers (plist, xml, json, txt)
3. Configuration loading

**Week 5-6: Analysis**
1. Issue categorization
2. CWE/OWASP mapping
3. Advanced features (memory detection, security analysis)

**Week 7-8: Testing & Optimization**
1. Unit tests (150+ tests)
2. Integration tests
3. Performance optimization
4. Documentation

---

## Quick Reference

### Execute Parser in Development

```python
from cpp_parsers import CppParserFactory

# Create parser
parser = CppParserFactory.get_parser("cppcheck")

# Run analysis
issues = parser.execute_cppcheck([Path("src/")])

# Get report
report = parser.generate_report(issues)
```

### Add New Tool

1. Create parser file: `cpp_parsers_<tool>.py`
2. Define configuration @dataclass
3. Implement parser class with 6-8 methods
4. Add to CppParserRegistry in `__init__.py`
5. Update Phase 2 TODO list

### Test Output Parsing

```python
# Parse sample output
issues = parser.parse_xml_report(Path("cppcheck_output.xml"))
assert len(issues) > 0
assert all(hasattr(i, 'severity') for i in issues)
```

---

## Related Documentation

- Full guide: `docs/parsers/CPP_PARSERS_README.md` (716 lines)
- Completion status: `docs/parsers/CPLUS_CSHARP_GO_COMPLETION.md`
- Parser architecture: `docs/architecture/parser_architecture.md`

---

**Last Updated:** 2025-12-21  
**Status:** Phase 1 ✅ | Phase 2 🔄
