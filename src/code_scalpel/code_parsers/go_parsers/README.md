# Go Parsers Module - Quick Start & Development Guide

**Module Status:** Phase 1 Complete - Infrastructure Ready  
**Location:** `src/code_scalpel/code_parser/go_parsers/`  
**Parsers:** 6 (Gofmt, Golint, Govet, Staticcheck, Golangci-lint, Gosec)

---

## Data Flow Architecture

```
                    Go Source Code
                          ↓
         ┌────────────────┴────────────────┐
         ↓                                  ↓
    go.mod / go.sum                  .golangci.yml
         ↓                                  ↓
    ┌────┴──────────────────────────────────┘
    ↓
GoParserRegistry (Factory)
    ↓
┌───┬─────────┬──────────┬──────────┬────────────┬──────┐
↓   ↓         ↓          ↓          ↓            ↓      ↓
Gofmt Golint Govet Staticcheck Golangci-lint Gosec
↓   ↓         ↓          ↓          ↓            ↓      ↓
(text) (text) (text)  (json)     (json)       (json)
↓   ↓         ↓          ↓          ↓            ↓      ↓
└───┴─────────┴──────────┴──────────┴────────────┴──────┘
              ↓
  Issue Normalization & Categorization
              ↓
   ┌──────────┬──────────┬──────────┐
   ↓          ↓          ↓          ↓
Deduplication CWE Mapping Severity Race Detector
   ↓          ↓          ↓          ↓
   └──────────┴──────────┴──────────┘
              ↓
  Unified JSON/SARIF/PlainText Report
```

---

## Prioritized TODO Items

### TIER 1: CRITICAL (Foundation - Weeks 1-2)

Essential infrastructure items that block all other development.

1. **GoParserRegistry Implementation** [HIGH]
   - File: `__init__.py`
   - Location: Factory pattern implementation
   - Effort: 2-3 days
   - Blocks: All other development
   - TODO: `[20251221_TODO] Create GoParserRegistry class with factory`

2. **Golangci-lint Execution** [HIGH]
   - File: `go_parsers_golangci_lint.py`
   - Method: `run_linters()`
   - Effort: 2-3 days
   - Dependencies: GoParserRegistry, .golangci.yml config
   - TODO: `[20251221_TODO] Run all configured linters`

3. **Gosec Security Scanning** [HIGH]
   - File: `go_parsers_gosec.py`
   - Method: `execute_gosec()`
   - Effort: 2-3 days
   - TODO: `[20251221_TODO] Execute Gosec analysis`

4. **Govet Pattern Detection** [MEDIUM]
   - File: `go_parsers_govet.py`
   - Method: `analyze_patterns()`
   - Effort: 2 days
   - TODO: `[20251221_TODO] Analyze code patterns with govet`

### TIER 2: OUTPUT PARSING (Weeks 2-3)

Implement format-specific output parsing for each tool.

5. **Golangci-lint JSON Parsing** [HIGH]
   - File: `go_parsers_golangci_lint.py`
   - Method: `parse_json_output()`
   - Effort: 2 days
   - TODO: `[20251221_TODO] Parse golangci-lint JSON report`

6. **Gosec JSON Parsing** [HIGH]
   - File: `go_parsers_gosec.py`
   - Method: `parse_json_report()`
   - Effort: 1-2 days
   - TODO: `[20251221_TODO] Parse Gosec JSON report`

7. **Staticcheck JSON Parsing** [MEDIUM]
   - File: `go_parsers_staticcheck.py`
   - Method: `parse_json_output()`
   - Effort: 1-2 days
   - TODO: `[20251221_TODO] Parse Staticcheck JSON output`

8. **Govet Text Output Parsing** [MEDIUM]
   - File: `go_parsers_govet.py`
   - Method: `parse_output()`
   - Effort: 1-2 days
   - TODO: `[20251221_TODO] Parse govet text output`

### TIER 3: CONFIGURATION & LOADING (Weeks 3-4)

Load configuration from .golangci.yml and tool-specific files.

9. **Golangci-lint Config Loading** [HIGH]
   - File: `go_parsers_golangci_lint.py`
   - Method: `load_config()`
   - Effort: 1-2 days
   - TODO: `[20251221_TODO] Load golangci-lint configuration`

10. **Gosec Config Loading** [MEDIUM]
    - File: `go_parsers_gosec.py`
    - Method: `load_config()`
    - Effort: 1 day
    - TODO: `[20251221_TODO] Load Gosec configuration`

11. **Staticcheck Config Loading** [MEDIUM]
    - File: `go_parsers_staticcheck.py`
    - Method: `load_config()`
    - Effort: 1 day
    - TODO: `[20251221_TODO] Load Staticcheck configuration`

12. **Go Module Handling** [MEDIUM]
    - File: `__init__.py`
    - Method: `handle_go_modules()`
    - Effort: 1-2 days
    - TODO: `[20251221_TODO] Parse and validate go.mod/go.sum`

### TIER 4: CATEGORIZATION & MAPPING (Weeks 4-5)

Implement issue categorization, CWE mapping, and Go-specific checks.

13. **Golangci-lint Result Categorization** [MEDIUM]
    - File: `go_parsers_golangci_lint.py`
    - Method: `categorize_by_linter()`
    - Effort: 1-2 days
    - TODO: `[20251221_TODO] Categorize issues by linter source`

14. **Gosec CWE Mapping** [HIGH]
    - File: `go_parsers_gosec.py`
    - Method: `map_to_cwe()`
    - Effort: 2 days
    - TODO: `[20251221_TODO] Map vulnerabilities to CWE IDs`

15. **Govet Nil Dereference Detection** [MEDIUM]
    - File: `go_parsers_govet.py`
    - Method: `check_nil_dereference()`
    - Effort: 1 day
    - TODO: `[20251221_TODO] Detect nil pointer dereferences`

16. **Staticcheck API Usage Checking** [MEDIUM]
    - File: `go_parsers_staticcheck.py`
    - Method: `check_api_usage()`
    - Effort: 1-2 days
    - TODO: `[20251221_TODO] Verify correct API usage`

### TIER 5: ANALYSIS FEATURES (Weeks 5-6)

Implement advanced analysis capabilities specific to Go.

17. **Race Condition Detection** [HIGH]
    - File: `go_parsers_govet.py`
    - Method: `check_channels()`
    - Effort: 2 days
    - TODO: `[20251221_TODO] Analyze channel operations`

18. **Security Vulnerability Detection** [HIGH]
    - File: `go_parsers_gosec.py`
    - Method: `detect_injection_vulnerabilities()`
    - Effort: 2 days
    - TODO: `[20251221_TODO] Detect injection attack patterns`

19. **Code Duplication Detection** [MEDIUM]
    - File: `go_parsers_staticcheck.py`
    - Method: `detect_code_duplication()`
    - Effort: 1-2 days
    - TODO: `[20251221_TODO] Find duplicate code patterns`

20. **Test Coverage Analysis** [MEDIUM]
    - File: `__init__.py`
    - Method: `analyze_test_coverage()`
    - Effort: 1-2 days
    - TODO: `[20251221_TODO] Parse Go test coverage reports`

### TIER 6: GO ECOSYSTEM FEATURES (Weeks 6-7)

Implement Go-specific analysis and dependency management.

21. **Go Module Dependency Analysis** [MEDIUM]
    - File: `__init__.py`
    - Method: `analyze_dependencies()`
    - Effort: 2 days
    - TODO: `[20251221_TODO] Analyze Go module dependencies`

22. **Vulnerability Scanning (go mod audit)** [HIGH]
    - File: `__init__.py`
    - Method: `scan_vulnerabilities()`
    - Effort: 2 days
    - TODO: `[20251221_TODO] Scan Go mod vulnerabilities`

23. **Interface Implementation Checking** [MEDIUM]
    - File: `go_parsers_staticcheck.py`
    - Method: `check_interfaces()`
    - Effort: 1-2 days
    - TODO: `[20251221_TODO] Verify interface implementations`

### TIER 7: REPORTING & OUTPUT (Weeks 7-8)

Implement report generation for all output formats.

24. **Golangci-lint Report Generation** [MEDIUM]
    - File: `go_parsers_golangci_lint.py`
    - Method: `generate_report()`
    - Effort: 1 day
    - TODO: `[20251221_TODO] Generate analysis report`

25. **Gosec Report Generation** [MEDIUM]
    - File: `go_parsers_gosec.py`
    - Method: `generate_report()`
    - Effort: 1 day
    - TODO: `[20251221_TODO] Generate analysis report`

26. **Unified Report Format** [MEDIUM]
    - File: `__init__.py`
    - Method: `create_unified_report()`
    - Effort: 2 days
    - TODO: `[20251221_TODO] Generate unified JSON/SARIF report`

---

## Module-Level TODOs

**Registry & Aggregation**
- Create GoParserRegistry class with factory pattern
- Implement lazy-loading for parser modules
- Add aggregation metrics across multiple parsers
- Implement result deduplication and filtering
- Create unified JSON/SARIF output format

**Go Ecosystem Integration**
- Go module dependency analysis (via go.mod)
- Vulnerability scanning (go mod audit)
- Test coverage parsing (coverage.out)
- Benchmark result analysis
- Go version compatibility checking

**Security & Analysis**
- Hardcoded secret detection (via Gosec)
- Weak cryptography detection
- SQL injection vulnerability detection
- Command injection detection
- Race condition detection

---

## File Structure

```
go_parsers/
├── __init__.py                         # Factory registry
├── go_parsers_gofmt.py                 # Code formatting
├── go_parsers_golint.py                # Style checking
├── go_parsers_govet.py                 # Pattern detection
├── go_parsers_staticcheck.py           # Code quality
├── go_parsers_golangci_lint.py         # Linter aggregation (NEW)
├── go_parsers_gosec.py                 # Security scanning (NEW)
└── README.md                           # This file
```

---

## Parser Overview

| Tool | Status | Methods | TODOs | Priority | Effort |
|------|--------|---------|-------|----------|--------|
| Gofmt | Stubbed | 5 | 5 | LOW | 1-2d |
| Golint | Stubbed | 5 | 5 | MEDIUM | 2d |
| Govet | Stubbed | 6 | 6 | HIGH | 2-3d |
| Staticcheck | Stubbed | 6 | 6 | HIGH | 2-3d |
| Golangci-lint | Stubbed | 6 | 6 | HIGH | 2-3d |
| Gosec | Stubbed | 7 | 7 | HIGH | 2-3d |

---

## Development Workflow

### Phase 2 Sprint Structure

**Week 1-2: Foundation**
1. Implement GoParserRegistry factory
2. Golangci-lint and Gosec execution
3. Govet and Staticcheck integration
4. Basic JSON output parsing

**Week 2-3: Parsing & Config**
1. All output parsers (JSON, text formats)
2. .golangci.yml configuration loading
3. Go module (go.mod) handling

**Week 4-5: Analysis & Mapping**
1. Issue categorization by linter
2. CWE vulnerability mapping
3. Go ecosystem features (mod audit, coverage)
4. Advanced features (race detection, duplication)

**Week 6-8: Testing & Optimization**
1. Unit tests (150+ tests)
2. Integration tests with Go projects
3. Race detector output parsing
4. Performance optimization
5. Documentation and examples

---

## Quick Reference

### Execute Parser in Development

```python
from go_parsers import GoParserFactory

# Create parser
parser = GoParserFactory.create("golangci_lint")

# Run all configured linters
issues = parser.run_linters([Path(".")])

# Generate report
report = parser.generate_report(issues, format="json")
```

### Load Configuration

```python
from pathlib import Path
import yaml

# Load golangci-lint config
with open(".golangci.yml") as f:
    config = yaml.safe_load(f)

parser = GoParserFactory.create("golangci_lint")
issues = parser.run_linters([Path(".")], config=config)
```

### Security Scanning

```python
parser = GoParserFactory.create("gosec")

# Scan for security vulnerabilities
issues = parser.execute_gosec([Path(".")])

# Map to CWE
cwe_map = parser.map_to_cwe(issues)

# Filter by severity
critical = parser.filter_by_severity(issues, "CRITICAL")
```

### Go Module Analysis

```python
# Analyze module dependencies and vulnerabilities
parser = GoParserFactory.get_parser("registry")

deps = parser.analyze_dependencies(Path("."))
vulns = parser.scan_vulnerabilities(Path("."))
```

---

## Related Documentation

- Full guide: `docs/parsers/GO_PARSERS_README.md` (717 lines)
- Completion status: `docs/parsers/CPLUS_CSHARP_GO_COMPLETION.md`
- Parser architecture: `docs/architecture/parser_architecture.md`
- Go ecosystem guide: `docs/guides/go_integration.md`

---

**Last Updated:** 2025-12-21  
**Status:** Phase 1 ✅ | Phase 2 🔄
