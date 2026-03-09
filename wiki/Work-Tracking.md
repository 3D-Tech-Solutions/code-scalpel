# Work Tracking — Static Analysis Parser Gap Closure

All phases required to bring every language to **complete** status (Phase 1 IR + Phase 2 tool parsers). Each task is independently assignable. Stages within a phase can be parallelized across agents/teams; tasks within a stage that have no intra-stage dependency are also parallelizable (noted below).

**Reference**: [Language-Completion-Roadmap.md](Language-Completion-Roadmap.md) for full specs, output formats, and implementation patterns.

---

## Legend

| Symbol | Meaning |
|--------|---------|
| `[ ]` | Not started |
| `[~]` | In progress |
| `[x]` | Done |
| **BLOCKS** | Nothing in the same stage can be done before this task |
| **PARALLEL** | Can be done simultaneously with other same-stage tasks |
| **DEPENDS** | Requires a specific earlier task |

---

## Stage 1 — C++ Tool Parsers

**Assignable to**: 1–3 agents in parallel (see dependency notes)
**Blocks**: Nothing outside this stage
**Reference**: [Language-Completion-Roadmap.md § Stage 1](Language-Completion-Roadmap.md#stage-1--c-tool-parsers-immediate)

### Dependencies within Stage 1

```
Task 1.1 (adapter)   ─┐
Task 1.2 (registry)  ─┤── Task 1.9 (tests) — all parsers must exist first
Tasks 1.3–1.8        ─┘
Tasks 1.3–1.8 are PARALLEL to each other
```

---

### Task 1.1 — `cpp_adapter.py` — Implement adapter

- **File**: `src/code_scalpel/code_parsers/adapters/cpp_adapter.py`
- **Read first**: `src/code_scalpel/code_parsers/adapters/go_adapter.py` (reference implementation, 54 lines)
- **Read first**: `src/code_scalpel/ir/normalizers/cpp_normalizer.py` (what to wrap)
- **Status**: `[x]`
- **Parallelism**: PARALLEL — independent of tasks 1.3–1.8

**What to implement** (replace `raise NotImplementedError` body):
```python
def __init__(self):
    from code_scalpel.ir.normalizers.cpp_normalizer import CppNormalizer
    self._normalizer = CppNormalizer()

def parse(self, code: str) -> ParseResult:
    ir_module = self._normalizer.normalize(code)
    return ParseResult(ast_tree=ir_module, language="cpp", success=True)

def get_functions(self, ast_tree) -> list[str]:
    from code_scalpel.ir.nodes import IRFunctionDef
    return [n.name for n in getattr(ast_tree, "body", []) if isinstance(n, IRFunctionDef)]

def get_classes(self, ast_tree) -> list[str]:
    from code_scalpel.ir.nodes import IRClassDef
    return [n.name for n in getattr(ast_tree, "body", []) if isinstance(n, IRClassDef)]
```

**Acceptance criteria**:
- `from code_scalpel.code_parsers.adapters.cpp_adapter import CppAdapter` succeeds
- `CppAdapter().parse("int main() { return 0; }").success == True`

---

### Task 1.2 — `cpp_parsers/__init__.py` — Implement CppParserRegistry

- **File**: `src/code_scalpel/code_parsers/cpp_parsers/__init__.py`
- **Read first**: `src/code_scalpel/code_parsers/python_parsers/__init__.py` (reference lazy-load registry)
- **Status**: `[x]`
- **Parallelism**: PARALLEL — independent of tasks 1.3–1.8

**What to implement**: Replace the 31-line stub with a working `CppParserRegistry` using the registry pattern from [Language-Completion-Roadmap.md § Registry pattern](Language-Completion-Roadmap.md#registry-pattern-lazy-load):

```python
class CppParserRegistry:
    def __init__(self):
        from . import (cpp_parsers_Cppcheck, cpp_parsers_clang_tidy,
                       cpp_parsers_Clang_Static_Analyzer, cpp_parsers_cpplint,
                       cpp_parsers_coverity, cpp_parsers_SonarQube)
        self._parsers = {
            "cppcheck":   cpp_parsers_Cppcheck.CppcheckParser,
            "clang-tidy": cpp_parsers_clang_tidy.ClangTidyParser,
            "clang-sa":   cpp_parsers_Clang_Static_Analyzer.ClangStaticAnalyzerParser,
            "cpplint":    cpp_parsers_cpplint.CppLintParser,
            "coverity":   cpp_parsers_coverity.CoverityParser,
            "sonarqube":  cpp_parsers_SonarQube.SonarQubeCppParser,
        }

    def get_parser(self, tool_name: str): ...
    def analyze(self, path, tools=None) -> dict[str, list]: ...
```

**Acceptance criteria**:
- `CppParserRegistry().get_parser("cppcheck")` returns a `CppcheckParser` instance
- `CppParserRegistry().get_parser("unknown")` raises `ValueError`
- `CppParserRegistry().analyze(Path("."))` returns `{"cppcheck": [], ...}` (graceful when tools absent)

---

### Task 1.3 — `cpp_parsers_Cppcheck.py` — Implement Cppcheck parser

- **File**: `src/code_scalpel/code_parsers/cpp_parsers/cpp_parsers_Cppcheck.py`
- **Read first**: Current file (100 lines — dataclasses already exist)
- **Status**: `[x]`
- **Parallelism**: PARALLEL

**Output format**: `cppcheck --xml-version=2 <paths> 2>&1`
```xml
<results version="2">
  <errors>
    <error id="nullPointer" severity="error" msg="Null pointer dereference"
           cwe="476" file0="main.cpp">
      <location file="main.cpp" line="12" column="5"/>
    </error>
  </errors>
</results>
```

**Methods to implement**:
| Method | Description |
|--------|-------------|
| `execute_cppcheck(paths, config=None)` | `subprocess.run(["cppcheck", "--xml-version=2", "--enable=all", ...])` + graceful `shutil.which` check |
| `parse_xml_string(xml_str)` | Parse XML from stderr; extract `<error>` elements |
| `parse_xml_report(report_path)` | Parse `.xml` file saved from a previous run |
| `load_config(config_file)` | Parse `.cppcheck` project XML |
| `categorize_issues(issues)` | Group by `IssueCategory` enum (already defined) |
| `detect_memory_issues(issues)` | Filter `IssueCategory.MEMORY` |
| `map_to_cwe(issues)` | Use `<error cwe="..."/>` attribute directly |
| `calculate_quality_metrics(issues)` | `{total, by_severity, by_category, cwe_coverage}` dict |
| `generate_report(issues, format="json")` | Normalized JSON or SARIF 2.1 |

**Acceptance criteria**:
- Parses the XML fixture below correctly: 1 error, severity=error, cwe=476, file=main.cpp, line=12
- Returns `[]` when `cppcheck` not installed (graceful)
- `generate_report()` produces valid JSON with `{issues, summary, cwe_map}` structure

---

### Task 1.4 — `cpp_parsers_clang_tidy.py` — Implement clang-tidy parser

- **File**: `src/code_scalpel/code_parsers/cpp_parsers/cpp_parsers_clang_tidy.py`
- **Read first**: Current file (98 lines — dataclasses already exist)
- **Status**: `[x]`
- **Parallelism**: PARALLEL

**Output format** (stderr diagnostic):
```
main.cpp:12:5: warning: use range-based for loop [modernize-loop-convert]
main.cpp:18:3: error: use nullptr [modernize-use-nullptr]
```

**Methods to implement**:
| Method | Description |
|--------|-------------|
| `execute_clang_tidy(paths, config=None)` | `subprocess.run(["clang-tidy", "--export-fixes=-", str(path), "--", ...])` |
| `parse_diagnostic_output(output)` | Parse `file:line:col: severity: msg [check-name]` from stderr |
| `parse_json_report(report_path)` | Parse `--export-fixes` YAML/JSON output |
| `load_config(config_file)` | Parse `.clang-tidy` YAML |
| `categorize_checks(checks)` | Group by `CheckCategory` (modernize, bugprone, performance, readability, etc.) |
| `detect_modernization_opportunities(checks)` | Filter `CheckCategory.MODERNIZE` |
| `apply_fixes(checks)` | Run `clang-tidy --fix`; return `{file: fixes_applied}` |
| `analyze_cpp_standard_compatibility(checks, target_std)` | Filter for standard-relevant checks |
| `generate_report(checks, format="json")` | Normalized JSON or SARIF 2.1 |

**Acceptance criteria**:
- Parses the diagnostic output above: 2 checks, categories modernize, file=main.cpp
- Returns `[]` when `clang-tidy` not installed
- Check name extracted correctly: `modernize-loop-convert` → `CheckCategory.MODERNIZE`

---

### Task 1.5 — `cpp_parsers_Clang-Static-Analyzer.py` — Implement Clang-SA parser

- **File**: `src/code_scalpel/code_parsers/cpp_parsers/cpp_parsers_Clang-Static-Analyzer.py`
- **Read first**: Current file (139 lines — most scaffolded of the 5)
- **Status**: `[x]`
- **Parallelism**: PARALLEL

**Output format**: `.plist` XML from `scan-build -o /tmp/out make`
```xml
<plist version="1.0">
  <dict>
    <key>clang_diagnostics</key>
    <array>
      <dict>
        <key>description</key><string>Use of uninitialized value</string>
        <key>type</key><string>Use of uninitialized value</string>
        <key>check_name</key><string>core.uninitialized.Assign</string>
        <key>location</key>
        <dict><key>file</key><integer>0</integer>
              <key>line</key><integer>42</integer>
              <key>col</key><integer>3</integer></dict>
        <key>path</key><array>...</array>
      </dict>
    </array>
  </dict>
</plist>
```

**Methods to implement**:
| Method | Description |
|--------|-------------|
| `execute_scan_build(paths, config=None)` | `subprocess.run(["scan-build", "-o", tmpdir, "make"])` |
| `parse_plist_report(report_path)` | `plistlib.load()`; extract `clang_diagnostics` array |
| `parse_html_report_dir(report_dir)` | Alternative: scan `scan-build` HTML output dir |
| `extract_bug_paths(findings)` | Extract `path` array steps for each finding |
| `filter_memory_bugs(findings)` | Filter to memory-related `BugType` enum values |
| `generate_report(findings, format="json")` | Normalized JSON or SARIF 2.1 |

**Acceptance criteria**:
- Parses the plist fixture above: 1 finding, type=uninitialized, check=core.uninitialized.Assign, line=42
- Returns `[]` when `scan-build` not installed
- `extract_bug_paths()` returns list of step dicts with `{file, line, col, message}`

---

### Task 1.6 — `cpp_parsers_cpplint.py` — Implement cpplint parser

- **File**: `src/code_scalpel/code_parsers/cpp_parsers/cpp_parsers_cpplint.py`
- **Read first**: Current file (83 lines — dataclasses already exist)
- **Status**: `[x]`
- **Parallelism**: PARALLEL

**Output format** (stderr):
```
main.cpp:42:  Missing space before {  [whitespace/braces] [4]
src/utils.cpp:17:  Use nullptr instead of NULL  [readability/modernize] [5]
```
Format: `file:line:  message  [category/check] [confidence 1-5]`

**Methods to implement**:
| Method | Description |
|--------|-------------|
| `execute_cpplint(paths, config=None)` | `subprocess.run(["cpplint"] + [str(p) for p in paths])` |
| `parse_cpplint_output(output)` | Parse stderr format above with regex |
| `load_config(config_file)` | Parse `CPPLINT.cfg` key=value file |
| `categorize_violations(violations)` | Group by `StyleViolationType` enum |
| `calculate_style_score(violations, total_lines)` | `max(0, 100 - weighted_violations_per_100_lines)` |
| `generate_report(violations, format="json")` | Normalized JSON or SARIF 2.1 |

**Acceptance criteria**:
- Parses the two-line fixture above: 2 violations, correct categories, confidence values 4 and 5
- Returns `[]` when `cpplint` not installed
- `calculate_style_score([], 100)` returns `100.0`

---

### Task 1.7 — `cpp_parsers_coverity.py` — Implement Coverity parser (enterprise)

- **File**: `src/code_scalpel/code_parsers/cpp_parsers/cpp_parsers_coverity.py`
- **Read first**: Current file (100 lines — dataclasses already exist)
- **Status**: `[x]`
- **Parallelism**: PARALLEL

**Output format**: Coverity JSON export
```json
{"issues": [
  {"checkerName": "NULL_RETURNS", "subcategory": "null_ptr",
   "extra": "getUser()",
   "events": [{"eventDescription": "Returned null", "lineNumber": 42,
               "filePathname": "src/user.cpp"}],
   "cwe": 476, "severity": "High"}
]}
```

**Methods to implement**:
| Method | Description |
|--------|-------------|
| `execute_coverity(paths, config=None)` | **ENTERPRISE** — raise `NotImplementedError("Coverity requires a licensed installation. Run cov-analyze externally and pass the JSON export to parse_json_report()")` |
| `parse_json_report(report_path)` | Parse Coverity JSON export file |
| `parse_json_string(json_str)` | Parse JSON string directly |
| `categorize_issues(issues)` | Group by `CoverityCategory` enum |
| `map_to_cwe(issues)` | Use `issue["cwe"]` field |
| `generate_report(issues, format="json")` | Normalized JSON or SARIF 2.1 |

**Acceptance criteria**:
- `execute_coverity([])` raises `NotImplementedError` with instructive message
- `parse_json_report()` parses the fixture above: 1 issue, checker=NULL_RETURNS, cwe=476, line=42
- `map_to_cwe()` returns `{"CWE-476": [<issue>]}`

---

### Task 1.8 — `cpp_parsers_SonarQube.py` — Implement SonarQube C++ parser (enterprise)

- **File**: `src/code_scalpel/code_parsers/cpp_parsers/cpp_parsers_SonarQube.py`
- **Note**: This file is currently empty (1 byte). Build from scratch using `java_parsers_SonarQube.py` as reference.
- **Read first**: `src/code_scalpel/code_parsers/java_parsers/java_parsers_SonarQube.py` (reference — 252 lines)
- **Status**: `[x]`
- **Parallelism**: PARALLEL

**Output format**: SonarQube Web API JSON
```json
{"issues": [
  {"rule": "cpp:S1135", "severity": "INFO", "component": "my-project:src/main.cpp",
   "line": 15, "message": "Complete the task.", "type": "CODE_SMELL"}
]}
```

**Methods to implement**: Mirror `java_parsers_SonarQube.py` — `parse_issues_json()`, `parse_metrics_json()`, `categorize_issues()`, `map_severity()`, `generate_report()`. Add `execute_sonarqube()` that raises `NotImplementedError` (server-based tool).

**Acceptance criteria**:
- Parses the fixture above: 1 issue, rule=cpp:S1135, line=15
- `execute_sonarqube([])` raises `NotImplementedError`
- File is >100 lines (not a skeleton)

---

### Task 1.9 — `test_cpp_tool_parsers.py` — Write test suite

- **File**: `tests/languages/test_cpp_tool_parsers.py`
- **DEPENDS ON**: Tasks 1.1–1.8 all complete
- **Read first**: `tests/languages/test_go_parser.py` (style reference)
- **Status**: `[x]`

**Required test cases (40+ total)**:

| Test name | What it verifies |
|-----------|----------------|
| `test_cppcheck_parse_xml_string_basic` | 1-issue XML → 1 `CppcheckIssue` with correct fields |
| `test_cppcheck_parse_xml_empty` | Empty `<errors/>` → `[]` |
| `test_cppcheck_cwe_mapping` | `<error cwe="476"/>` → `{"CWE-476": [...]}` |
| `test_cppcheck_categorize_memory_issues` | Filter memory issues from mixed list |
| `test_cppcheck_graceful_when_not_installed` | `shutil.which` mocked → `[]` |
| `test_cppcheck_quality_metrics_structure` | Returns dict with `total`, `by_severity`, `by_category` keys |
| `test_clang_tidy_parse_diagnostic_single` | One-line diagnostic → 1 check |
| `test_clang_tidy_parse_diagnostic_multi` | Multi-line stdout → multiple checks |
| `test_clang_tidy_categorize_modernize` | `modernize-*` checks → `CheckCategory.MODERNIZE` |
| `test_clang_tidy_categorize_bugprone` | `bugprone-*` checks → `CheckCategory.BUGPRONE` |
| `test_clang_tidy_graceful_when_not_installed` | Returns `[]` |
| `test_clang_sa_parse_plist_single_finding` | plist with 1 diagnostic → 1 `AnalyzerFinding` |
| `test_clang_sa_extract_bug_paths` | Bug path array → list of step dicts |
| `test_clang_sa_filter_memory_bugs` | Mixed findings → only memory-related |
| `test_clang_sa_graceful_when_not_installed` | Returns `[]` |
| `test_cpplint_parse_output_basic` | Two-line output → 2 violations |
| `test_cpplint_parse_confidence_extracted` | Confidence `[4]` extracted correctly |
| `test_cpplint_calculate_style_score_no_issues` | `[]` + 100 lines → `100.0` |
| `test_cpplint_calculate_style_score_with_issues` | Issues present → score < 100 |
| `test_cpplint_graceful_when_not_installed` | Returns `[]` |
| `test_coverity_execute_raises_not_implemented` | `NotImplementedError` with message |
| `test_coverity_parse_json_string` | JSON fixture → 1 issue, correct CWE |
| `test_coverity_map_to_cwe` | `issue["cwe"] = 476` → `"CWE-476"` key |
| `test_sonarqube_parse_issues_json` | JSON fixture → 1 issue |
| `test_sonarqube_execute_raises_not_implemented` | Server-based tool raises |
| `test_registry_get_parser_cppcheck` | Returns `CppcheckParser` instance |
| `test_registry_get_parser_clang_tidy` | Returns `ClangTidyParser` instance |
| `test_registry_get_parser_unknown_raises` | `ValueError` with tool name |
| `test_registry_analyze_returns_dict` | `analyze(path)` returns `{tool: []}` for all tools |
| `test_adapter_parse_basic_c` | `CppAdapter().parse("int f(){}")` succeeds |
| `test_adapter_get_functions` | Returns function names from IR |
| `test_adapter_get_classes` | Returns struct/class names from IR |

**Acceptance criteria**: `pytest tests/languages/test_cpp_tool_parsers.py -v` — all pass, no installed tools required.

---

## Stage 2 — C# Tool Parsers

**Assignable to**: 1–3 agents in parallel
**Depends on**: Stage 1 complete (not technically blocking, but maintain order)
**Reference**: [Language-Completion-Roadmap.md § Stage 2](Language-Completion-Roadmap.md#stage-2--complete-c-tool-parsers)

### Dependencies within Stage 2

```
Task 2.1 (adapter)       ─┐
Task 2.2 (registry+SARIF) ─┤── Task 2.9 (tests)
Tasks 2.3–2.8             ─┘
Tasks 2.3–2.8: PARALLEL to each other
Tasks 2.3, 2.4, 2.5 DEPEND on SARIF helper in Task 2.2
```

---

### Task 2.1 — `csharp_adapter.py` — Implement adapter

- **File**: `src/code_scalpel/code_parsers/adapters/csharp_adapter.py`
- **Read first**: `src/code_scalpel/code_parsers/adapters/go_adapter.py` (template)
- **Read first**: `src/code_scalpel/code_parsers/adapters/csharp_adapter.py` (current stub)
- **Read first**: `src/code_scalpel/ir/normalizers/csharp_normalizer.py` (what to wrap)
- **Status**: `[ ]`

Implement as thin wrapper over `CSharpNormalizer` — same pattern as `go_adapter.py`.

---

### Task 2.2 — `csharp_parsers/__init__.py` — Implement Registry + SARIF helper

- **File**: `src/code_scalpel/code_parsers/csharp_parsers/__init__.py`
- **Status**: `[ ]`
- **BLOCKS** Tasks 2.3, 2.4, 2.5 (they consume `_parse_sarif`)

**What to implement**:
1. `_parse_sarif(sarif_path: Path) -> list[SarifFinding]` — shared helper (see [Language-Completion-Roadmap.md § SARIF helper](Language-Completion-Roadmap.md#sarif-21-helper-shared--especially-for-net--c-tools))
2. `CSharpParserRegistry` with `get_parser()` and `analyze()` covering all 6 tools

---

### Task 2.3 — `csharp_parsers_Roslyn-Analyzers.py`

- **File**: `src/code_scalpel/code_parsers/csharp_parsers/csharp_parsers_Roslyn-Analyzers.py`
- **DEPENDS ON**: Task 2.2 (SARIF helper)
- **Status**: `[ ]`
- **Output format**: SARIF 2.1 JSON from `dotnet build --no-incremental`
- **Key methods**: `execute_roslyn()`, `parse_sarif_output(sarif_path)` (uses `_parse_sarif`), `categorize_by_rule()`, `generate_report()`
- **Acceptance criteria**: Parses sample SARIF fixture; graceful when `dotnet` not installed

---

### Task 2.4 — `csharp_parsers_StyleCop.py`

- **File**: `src/code_scalpel/code_parsers/csharp_parsers/csharp_parsers_StyleCop.py`
- **DEPENDS ON**: Task 2.2 (SARIF helper)
- **Status**: `[ ]`
- **Output format**: SARIF 2.1 from StyleCop.Analyzers MSBuild
- **Key methods**: `execute_stylecop()`, `parse_sarif_output()`, `categorize_rules()` (SA1xxx naming conventions), `generate_report()`

---

### Task 2.5 — `csharp_parsers_SecurityCodeScan.py`

- **File**: `src/code_scalpel/code_parsers/csharp_parsers/csharp_parsers_SecurityCodeScan.py`
- **DEPENDS ON**: Task 2.2 (SARIF helper)
- **Status**: `[ ]`
- **Output format**: SARIF 2.1 JSON
- **Key methods**: `execute_scs()`, `parse_sarif_output()`, `map_to_cwe()` (SCS rule → CWE), `generate_report()`
- **CWE map** (partial): `SCS0001→CWE-89`, `SCS0007→CWE-79`, `SCS0015→CWE-78`

---

### Task 2.6 — `csharp_parsers_fxcop.py`

- **File**: `src/code_scalpel/code_parsers/csharp_parsers/csharp_parsers_fxcop.py`
- **Status**: `[ ]`
- **Output format**: XML (legacy FxCop) or SARIF (Roslyn-based code analysis)
- **Key methods**: `execute_fxcop()`, `parse_xml_report()`, `parse_sarif_report()`, `categorize_violations()`, `generate_report()`

---

### Task 2.7 — `csharp_parsers_ReSharper.py`

- **File**: `src/code_scalpel/code_parsers/csharp_parsers/csharp_parsers_ReSharper.py`
- **Status**: `[ ]`
- **Output format**: XML from `inspectcode.exe --output=result.xml`
```xml
<IssueTypes><IssueType Id="UnusedVariable" Category="Potential Code Quality Issues" .../>
</IssueTypes>
<Issues><Project Name="MyProject.csproj">
  <Issue TypeId="UnusedVariable" File="Main.cs" Line="12" Message="Unused variable 'x'"/>
</Project></Issues>
```
- **Type**: Enterprise — `execute_resharper()` raises `NotImplementedError`
- **Key methods**: `parse_xml_report()`, `categorize_issues()`, `generate_report()`

---

### Task 2.8 — `csharp_parsers_SonarQube.py`

- **File**: `src/code_scalpel/code_parsers/csharp_parsers/csharp_parsers_SonarQube.py`
- **Status**: `[ ]`
- **Read first**: `src/code_scalpel/code_parsers/java_parsers/java_parsers_SonarQube.py` (copy and adapt)
- Enterprise tool — same pattern as Java SonarQube, different rule key prefix (`csharpsquid:`)

---

### Task 2.9 — `test_csharp_tool_parsers.py` — Write test suite

- **File**: `tests/languages/test_csharp_tool_parsers.py`
- **DEPENDS ON**: Tasks 2.1–2.8 all complete
- **Status**: `[ ]`

**Required test cases (25+ total)**:
- `test_sarif_helper_parses_basic` — SARIF JSON fixture → SarifFinding list
- `test_sarif_helper_empty_runs` — `{"runs": []}` → `[]`
- `test_roslyn_parse_sarif_output` — sample SARIF → issues
- `test_roslyn_graceful_when_dotnet_absent` — `[]`
- `test_stylecop_rule_categorization` — SA1100 range → style category
- `test_scs_cwe_mapping` — SCS0001 → CWE-89
- `test_fxcop_parse_xml_report` — XML fixture → violations
- `test_resharper_execute_raises` — `NotImplementedError`
- `test_resharper_parse_xml_report` — XML fixture → issues
- `test_sonarqube_parse_issues_json` — JSON fixture → issues
- `test_registry_get_parser_roslyn` — returns `RoslynAnalyzersParser`
- `test_registry_get_parser_unknown_raises` — `ValueError`
- `test_adapter_parse_basic_csharp` — parses `class Foo {}` successfully

---

## Stage 3 — Go Tool Parsers

**Assignable to**: 1–2 agents in parallel
**Depends on**: Stage 1 complete (ordering preference, not hard dependency)
**Note**: Go adapter (`go_adapter.py`) is already complete — only the registry and tool parsers need work.
**Reference**: [Language-Completion-Roadmap.md § Stage 3](Language-Completion-Roadmap.md#stage-3--complete-go-tool-parsers)

### Dependencies within Stage 3

```
Task 3.1 (registry)  ──── Task 3.8 (tests)
Tasks 3.2–3.7: PARALLEL to each other and to Task 3.1
```

---

### Task 3.1 — `go_parsers/__init__.py` — Implement GoParserRegistry

- **File**: `src/code_scalpel/code_parsers/go_parsers/__init__.py`
- **Read first**: Current file (40 lines — stub)
- **Status**: `[x]`

Implement `GoParserRegistry` with lazy-load factory covering all 6 tools.

---

### Task 3.2 — `go_parsers_golangci_lint.py` — **PRIORITY 1**

- **File**: `src/code_scalpel/code_parsers/go_parsers/go_parsers_golangci_lint.py`
- **Read first**: Current file (97 lines — `LintIssue`/`GolangciLintConfig` already defined)
- **Status**: `[x]`
- **Parallelism**: PARALLEL

**Output format**: `golangci-lint run --out-format json`
```json
{"Issues": [
  {"FromLinter": "govet", "Text": "printf: Errorf call has arguments but no formatting directives",
   "Severity": "error",
   "Pos": {"Filename": "main.go", "Line": 42, "Column": 5}}
], "Report": {"Warnings": []}}
```

**Methods to implement**:
| Method | Description |
|--------|-------------|
| `execute_golangci_lint(path, config=None)` | `golangci-lint run --out-format json ./...` |
| `parse_json_output(output)` | Parse `{"Issues": [...]}` |
| `load_config(config_file)` | Parse `.golangci.yml` or `.golangci.toml` |
| `categorize_by_linter(issues)` | Group by `FromLinter` field |
| `filter_by_severity(issues, min_severity)` | Filter by severity string |
| `generate_report(issues, format="json")` | Normalized output |

---

### Task 3.3 — `go_parsers_gosec.py` — **PRIORITY 2**

- **File**: `src/code_scalpel/code_parsers/go_parsers/go_parsers_gosec.py`
- **Read first**: Current file (92 lines — dataclasses defined)
- **Status**: `[x]`
- **Parallelism**: PARALLEL

**Output format**: `gosec -fmt=json ./...`
```json
{"Golang gosec": {
  "Issues": [
    {"severity": "HIGH", "confidence": "HIGH",
     "cwe": {"id": "89", "url": "https://cwe.mitre.org/data/definitions/89.html"},
     "rule_id": "G202", "details": "SQL query construction using format string",
     "file": "db/queries.go", "line": "31"}
  ],
  "Stats": {"files": 10, "lines": 450, "nosec": 2, "found": 1}
}}
```

**Methods to implement**: `execute_gosec()`, `parse_json_output()`, `map_to_cwe()` (use `cwe.id` directly), `categorize_by_severity()`, `get_security_stats()`, `generate_report()`

---

### Task 3.4 — `go_parsers_staticcheck.py`

- **File**: `src/code_scalpel/code_parsers/go_parsers/go_parsers_staticcheck.py`
- **Read first**: Current file (37 lines)
- **Status**: `[x]`
- **Parallelism**: PARALLEL

**Output format**: `staticcheck -f json ./...` (one JSON object per line)
```json
{"code": "SA1006", "severity": "error", "location": {"file": "main.go", "line": 15, "column": 3}, "message": "Printf with dynamic first argument and no further arguments"}
```

**Methods to implement**: `execute_staticcheck()`, `parse_jsonl_output()` (JSONL — one object per line), `categorize_by_code()` (SA=simple, S=style, ST=stdlib, QF=quickfix, etc.), `generate_report()`

---

### Task 3.5 — `go_parsers_govet.py`

- **File**: `src/code_scalpel/code_parsers/go_parsers/go_parsers_govet.py`
- **Read first**: Current file (29 lines — stub)
- **Status**: `[x]`
- **Parallelism**: PARALLEL

**Output format**: `go vet ./...` (stderr text)
```
# command-line-arguments
./main.go:42:13: fmt.Sprintf format %d has arg x of wrong type float64
```

**Methods to implement**: `execute_govet()`, `parse_vet_output()` (parse `./file.go:line:col: msg`), `categorize_issues()`, `generate_report()`

---

### Task 3.6 — `go_parsers_golint.py`

- **File**: `src/code_scalpel/code_parsers/go_parsers/go_parsers_golint.py`
- **Read first**: Current file (28 lines — stub)
- **Status**: `[x]`
- **Parallelism**: PARALLEL

**Output format**: `golint ./...` (text)
```
main.go:12:1: exported function Hello should have comment or be unexported
```

**Methods to implement**: `execute_golint()`, `parse_lint_output()`, `categorize_issues()`, `generate_report()`
**Note**: `golint` is deprecated — add deprecation notice in docstring; still widely encountered in CI.

---

### Task 3.7 — `go_parsers_gofmt.py`

- **File**: `src/code_scalpel/code_parsers/go_parsers/go_parsers_gofmt.py`
- **Read first**: Current file (28 lines — stub)
- **Status**: `[x]`
- **Parallelism**: PARALLEL

**Output format**: `gofmt -l .` returns list of files with formatting issues (one file per line)
```
main.go
internal/utils.go
```

**Methods to implement**: `execute_gofmt()`, `parse_file_list()`, `get_diff(file_path)` (`gofmt -d`), `check_files(paths)` → `{file: is_formatted}`, `generate_report()`

---

### Task 3.8 — `test_go_tool_parsers.py` — Write test suite

- **File**: `tests/languages/test_go_tool_parsers.py`
- **DEPENDS ON**: Tasks 3.1–3.7 all complete
- **Status**: `[x]`

**Required test cases (30+ total)**:
- `test_golangci_lint_parse_json_basic` — fixture JSON → 1 issue with correct linter name
- `test_golangci_lint_categorize_by_linter` — groups `{"govet": [...], "errcheck": [...]}`
- `test_golangci_lint_graceful_when_absent` — `[]`
- `test_gosec_parse_json_output` — JSON fixture → 1 issue
- `test_gosec_cwe_mapping` — `issue["cwe"]["id"] = "89"` → `"CWE-89"`
- `test_gosec_graceful_when_absent` — `[]`
- `test_staticcheck_parse_jsonl_single` — one JSON line → 1 issue
- `test_staticcheck_parse_jsonl_multi` — 3 JSON lines → 3 issues
- `test_staticcheck_categorize_by_code` — SA/S/ST prefixes → categories
- `test_govet_parse_vet_output` — fixture stderr → issue list
- `test_golint_parse_output` — fixture text → issues with file/line/message
- `test_gofmt_parse_file_list` — `"main.go\nutils.go\n"` → `["main.go", "utils.go"]`
- `test_registry_get_parser_golangci` — returns `GolangciLintParser`
- `test_registry_get_parser_gosec` — returns `GosecParser`
- `test_registry_analyze_returns_all_tools` — dict with all 6 tool keys

---

## Stage 4 — Quick Wins (Python + JavaScript + Java)

**Assignable to**: 3 agents in parallel (one per language group)
**Depends on**: Stage 1 complete (ordering preference)
**Note**: All three sub-stages (4a, 4b, 4c) are fully independent of each other — assign to separate agents.

---

### Stage 4a — Python Remaining Stubs (5 files) ✅ COMPLETE [20260303_FEATURE]

All tasks are PARALLEL to each other. All read the corresponding current stub file first.

---

#### Task 4a.1 — `python_parsers_safety.py`

- **File**: `src/code_scalpel/code_parsers/python_parsers/python_parsers_safety.py`
- **Status**: `[x]`
- **Output format**: `pip-audit --format json` or `safety check --json`
```json
{"vulnerabilities": [
  {"name": "flask", "version": "0.12.2", "id": "PYSEC-2018-66",
   "fix_versions": ["1.0"], "aliases": ["CVE-2018-1000656"],
   "description": "..."}
]}
```
- **Key methods**: `execute_safety()` / `execute_pip_audit()`, `parse_json_output()`, `map_to_cve()`, `generate_report()`

---

#### Task 4a.2 — `python_parsers_isort.py`

- **File**: `src/code_scalpel/code_parsers/python_parsers/python_parsers_isort.py`
- **Status**: `[x]`
- **Output format**: `isort --check-only --diff .` → unified diff (stderr); exit code 1 if unsorted
- **Key methods**: `execute_isort()`, `parse_diff_output()`, `check_files(paths)` → `{file: is_sorted}`, `get_violations()`, `generate_report()`

---

#### Task 4a.3 — `python_parsers_vulture.py`

- **File**: `src/code_scalpel/code_parsers/python_parsers/python_parsers_vulture.py`
- **Status**: `[x]`
- **Output format**: `vulture .` text
```
src/utils.py:42: unused function 'helper' (60% confidence)
src/models.py:18: unused variable 'temp' (100% confidence)
```
- **Key methods**: `execute_vulture()`, `parse_output()`, `filter_by_confidence(items, min_pct)`, `categorize_dead_code()`, `generate_report()`

---

#### Task 4a.4 — `python_parsers_radon.py`

- **File**: `src/code_scalpel/code_parsers/python_parsers/python_parsers_radon.py`
- **Status**: `[x]`
- **Output format**: `radon cc -j .` (cyclomatic complexity JSON), `radon mi -j .` (maintainability), `radon hal -j .` (Halstead)
- **Key methods**: `execute_radon_cc()`, `execute_radon_mi()`, `parse_cc_json()`, `parse_mi_json()`, `categorize_by_grade()` (A–F), `generate_report()`

---

#### Task 4a.5 — `python_parsers_interrogate.py`

- **File**: `src/code_scalpel/code_parsers/python_parsers/python_parsers_interrogate.py`
- **Status**: `[x]`
- **Output format**: `interrogate --output-format json .`
```json
{"filename": "src/utils.py", "docstring_coverage": 75.0,
 "missing": ["function:helper", "class:MyClass"]}
```
- **Key methods**: `execute_interrogate()`, `parse_json_output()`, `get_coverage_summary()`, `list_missing_docstrings()`, `generate_report()`

---

#### Task 4a.6 — `test_python_remaining_parsers.py`

- **File**: `tests/languages/test_python_remaining_parsers.py`
- **DEPENDS ON**: Tasks 4a.1–4a.5
- **Status**: `[x]`
- ~25 fixture-based tests covering each parser + graceful degradation

---

### Stage 4b — JavaScript Remaining Stubs (5 files)

All tasks are PARALLEL. Each file is currently ~43–46 lines (imports only).

---

#### Task 4b.1 — `javascript_parsers_npm_audit.py`

- **File**: `src/code_scalpel/code_parsers/javascript_parsers/javascript_parsers_npm_audit.py`
- **Status**: `[x]`
- **Output format**: `npm audit --json`
```json
{"auditReportVersion": 2,
 "vulnerabilities": {
   "lodash": {"name": "lodash", "severity": "high", "range": "<4.17.21",
              "via": [{"source": 1084, "name": "lodash", "dependency": "lodash",
                       "url": "https://npmjs.com/advisories/1084",
                       "severity": "high", "cwe": ["CWE-1321"]}]}
 },
 "metadata": {"vulnerabilities": {"total": 1, "high": 1}}}
```
- **Key methods**: `execute_npm_audit()`, `parse_v2_json()`, `map_to_cwe()`, `get_severity_summary()`, `generate_report()`

---

#### Task 4b.2 — `javascript_parsers_jsdoc.py`

- **File**: `src/code_scalpel/code_parsers/javascript_parsers/javascript_parsers_jsdoc.py`
- **Status**: `[x]`
- **Output format**: Parse existing JSDoc comments from source using regex/AST, OR parse `jsdoc -X` JSON output
- **Key methods**: `extract_jsdoc_comments(code)`, `parse_jsdoc_json(output)`, `get_documentation_coverage()`, `list_undocumented_exports()`, `generate_report()`

---

#### Task 4b.3 — `javascript_parsers_package_json.py`

- **File**: `src/code_scalpel/code_parsers/javascript_parsers/javascript_parsers_package_json.py`
- **Status**: `[x]`
- **Input**: `package.json` file (no tool execution — pure file parsing)
- **Key methods**: `parse_package_json(path)`, `get_dependencies()`, `get_dev_dependencies()`, `get_scripts()`, `detect_framework()` (react, vue, angular, etc.), `get_node_engine_requirement()`, `generate_report()`

---

#### Task 4b.4 — `javascript_parsers_test_detection.py`

- **File**: `src/code_scalpel/code_parsers/javascript_parsers/javascript_parsers_test_detection.py`
- **Status**: `[x]`
- **Input**: `package.json` devDependencies + project file tree
- **Key methods**: `detect_test_framework(package_json)` (jest/mocha/vitest/jasmine/ava), `find_test_files(project_root)`, `get_test_config()`, `generate_report()`

---

#### Task 4b.5 — `javascript_parsers_webpack.py`

- **File**: `src/code_scalpel/code_parsers/javascript_parsers/javascript_parsers_webpack.py`
- **Status**: `[x]`
- **Input**: `webpack.config.js` / `webpack.config.ts` — static analysis (no execution)
- **Key methods**: `parse_webpack_config(path)`, `extract_entry_points()`, `extract_aliases()`, `extract_loaders()`, `detect_optimization_plugins()`, `generate_report()`
- **Note**: Webpack config is JS, not JSON — use regex heuristics for key patterns rather than full JS evaluation

---

#### Task 4b.6 — `test_javascript_remaining_parsers.py`

- **File**: `tests/languages/test_javascript_remaining_parsers.py`
- **DEPENDS ON**: Tasks 4b.1–4b.5
- **Status**: `[x]`
- ~25 fixture-based tests

---

### Stage 4c — Java Remaining Stubs (6 files)

All tasks are PARALLEL. These are all build/coverage/mutation tools (lower complexity than security tools).

---

#### Task 4c.1 — `java_parsers_Maven.py`

- **File**: `src/code_scalpel/code_parsers/java_parsers/java_parsers_Maven.py`
- **Status**: `[x]`
- **Input**: `pom.xml` parsing + `mvn` build output text
- **Key methods**: `parse_pom_xml(path)`, `get_dependencies()`, `get_plugins()`, `parse_build_output(text)`, `extract_compile_errors()`, `generate_report()`

---

#### Task 4c.2 — `java_parsers_Gradle.py`

- **File**: `src/code_scalpel/code_parsers/java_parsers/java_parsers_Gradle.py`
- **Status**: `[x]`
- **Input**: `build.gradle` / `build.gradle.kts` parsing + Gradle build output
- **Key methods**: `parse_gradle_file(path)`, `get_dependencies()`, `parse_build_output(text)`, `extract_compile_errors()`, `generate_report()`

---

#### Task 4c.3 — `java_parsers_DependencyCheck.py`

- **File**: `src/code_scalpel/code_parsers/java_parsers/java_parsers_DependencyCheck.py`
- **Status**: `[x]`
- **Output format**: OWASP DependencyCheck XML/JSON/SARIF report
- **Key methods**: `parse_json_report(path)`, `parse_xml_report(path)`, `map_to_cve()`, `map_to_cvss()`, `get_vulnerable_dependencies()`, `generate_report()`

---

#### Task 4c.4 — `java_parsers_JaCoCo.py`

- **File**: `src/code_scalpel/code_parsers/java_parsers/java_parsers_JaCoCo.py`
- **Status**: `[x]`
- **Output format**: JaCoCo XML coverage report
```xml
<report name="MyApp">
  <package name="com/example">
    <class name="UserService" sourcefilename="UserService.java">
      <method name="createUser" desc="(Ljava/lang/String;)V" line="25">
        <counter type="LINE" missed="2" covered="8"/>
      </method>
    </class>
  </package>
</report>
```
- **Key methods**: `parse_xml_report(path)`, `get_class_coverage()`, `get_method_coverage()`, `get_line_coverage()`, `calculate_summary()`, `generate_report()`

---

#### Task 4c.5 — `java_parsers_Pitest.py`

- **File**: `src/code_scalpel/code_parsers/java_parsers/java_parsers_Pitest.py`
- **Status**: `[x]`
- **Output format**: PIT XML mutation testing report
```xml
<mutations>
  <mutation detected="true" status="KILLED" numberOfTestsRun="3">
    <sourceFile>UserService.java</sourceFile>
    <mutatedClass>com.example.UserService</mutatedClass>
    <mutatedMethod>createUser</mutatedMethod>
    <lineNumber>42</lineNumber>
    <mutator>org.pitest.mutationtest.engine.gregor.mutators.ReturnValsMutator</mutator>
  </mutation>
</mutations>
```
- **Key methods**: `parse_xml_report(path)`, `get_mutation_score()`, `get_survived_mutations()`, `categorize_by_mutator()`, `generate_report()`

---

#### Task 4c.6 — `java_parsers_Semgrep.py`

- **File**: `src/code_scalpel/code_parsers/java_parsers/java_parsers_Semgrep.py`
- **Status**: `[x]`
- **Output format**: `semgrep --json` (shared format across all Semgrep-supported languages)
```json
{"results": [
  {"check_id": "java.lang.security.insecure-object-deserialization",
   "path": "src/UserController.java", "start": {"line": 42},
   "extra": {"message": "Insecure deserialization", "severity": "ERROR",
             "metadata": {"cwe": ["CWE-502"]}}}
]}
```
- **Key methods**: `execute_semgrep(paths, ruleset=None)`, `parse_json_output()`, `map_to_cwe()`, `categorize_by_severity()`, `generate_report()`

---

#### Task 4c.7 — `test_java_remaining_parsers.py`

- **File**: `tests/languages/test_java_remaining_parsers.py`
- **DEPENDS ON**: Tasks 4c.1–4c.6
- **Status**: `[x]`
- ~30 fixture-based tests (XML/JSON fixtures; no tools required)

---

## Stage 5 — Kotlin Phase 2 Completion + Phase 1

**Assignable to**: 1–2 agents
**Depends on**: Stages 1–4 complete

---

### Task 5.1 — Complete 5 partial Kotlin tool parsers

All PARALLEL to each other.

| Task | File | Tool | Output format |
|------|------|------|--------------|
| 5.1a | `kotlin_parsers_diktat.py` | diktat | SARIF / XML |
| 5.1b | `kotlin_parsers_gradle.py` | Gradle | `build.gradle.kts` + build output |
| 5.1c | `kotlin_parsers_compose.py` | Compose Lint | Android Lint SARIF |
| 5.1d | `kotlin_parsers_Konsist.py` | Konsist | JUnit XML from test run |
| 5.1e | `kotlin_parsers_test.py` | Test utilities | — helper utilities |

- **Status each**: `[ ]`
- **Read first** for each: the current file (127–146 lines — dataclasses already defined)
- **Reference**: [Adding-Kotlin.md § Phase 2](Adding-Kotlin.md)

---

### Task 5.2 — `kotlin_adapter.py` — Implement adapter

- **File**: `src/code_scalpel/code_parsers/adapters/kotlin_adapter.py`
- **Status**: `[ ]`
- **Note**: Thin wrapper — implement after Phase 1 normalizer exists

---

### Task 5.3 — Kotlin Phase 1 IR layer

- **Reference**: [Adding-Kotlin.md](Adding-Kotlin.md)
- Full checklist: `tree-sitter-kotlin` → `KotlinNormalizer` → extractor wiring → limits.toml → tests
- **Status**: `[ ]`
- **DEPENDS ON**: Task 5.2 (adapter is part of Phase 1 checklist)

---

## Stage 6 — PHP Phase 2 + Phase 1

**Assignable to**: 1 agent
**Depends on**: Stage 5 complete

| Task | File | Tool | Status |
|------|------|------|--------|
| 6.1 | `php_parsers_PHPCS.py` | PHP_CodeSniffer | `[ ]` |
| 6.2 | `php_parsers_PHPStan.py` | PHPStan | `[ ]` |
| 6.3 | `php_parsers_Psalm.py` | Psalm | `[ ]` |
| 6.4 | `php_parsers_phpmd.py` | PHP Mess Detector | `[ ]` |
| 6.5 | `php_parsers_ast.py` | PHP AST utilities | `[ ]` |
| 6.6 | `php_parsers_composer.py` | Composer | `[ ]` |
| 6.7 | `php_parsers_exakat.py` | Exakat | `[ ]` |
| 6.8 | `php_adapter.py` | Adapter | `[ ]` |
| 6.9 | PHP Phase 1 IR layer | tree-sitter-php | `[ ]` |
| 6.10 | `test_php_tool_parsers.py` | Tests | `[ ]` |

---

## Stage 7 — Ruby Phase 2 + Phase 1

**Assignable to**: 1 agent
**Depends on**: Stage 6 complete

| Task | File | Tool | Status |
|------|------|------|--------|
| 7.1 | `ruby_parsers/__init__.py` | RubyParserRegistry | `[ ]` |
| 7.2 | `ruby_parsers_RuboCop.py` | RuboCop | `[ ]` |
| 7.3 | `ruby_parsers_brakeman.py` | Brakeman | `[ ]` |
| 7.4 | `ruby_parsers_Reek.py` | Reek | `[ ]` |
| 7.5 | `ruby_parsers_bundler.py` | Bundler Audit | `[ ]` |
| 7.6 | `ruby_parsers_fasterer.py` | Fasterer | `[ ]` |
| 7.7 | `ruby_parsers_simplecov.py` | SimpleCov | `[ ]` |
| 7.8 | `ruby_parsers_ast.py` | Ruby AST utilities | `[ ]` |
| 7.9 | `ruby_adapter.py` | Adapter | `[ ]` |
| 7.10 | Ruby Phase 1 IR layer | tree-sitter-ruby | `[ ]` |
| 7.11 | `test_ruby_tool_parsers.py` | Tests | `[ ]` |

**Reference**: [Adding-Ruby.md](Adding-Ruby.md)

---

## Stage 8 — Swift Phase 2 + Phase 1

**Assignable to**: 1 agent
**Depends on**: Stage 7 complete

| Task | File | Tool | Status |
|------|------|------|--------|
| 8.1 | `swift_parsers/__init__.py` | SwiftParserRegistry | `[ ]` |
| 8.2 | `swift_parsers_SwiftLint.py` | SwiftLint | `[ ]` |
| 8.3 | `swift_parsers_swiftformat.py` | SwiftFormat | `[ ]` |
| 8.4 | `swift_parsers_sourcekitten.py` | SourceKitten | `[ ]` |
| 8.5 | `swift_parsers_Tailor.py` | Tailor | `[ ]` |
| 8.6 | `swift_adapter.py` | Adapter | `[ ]` |
| 8.7 | Swift Phase 1 IR layer | tree-sitter-swift | `[ ]` |
| 8.8 | `test_swift_tool_parsers.py` | Tests | `[ ]` |

**Reference**: [Adding-Swift.md](Adding-Swift.md)

---

## Stage 9 — Rust Phase 1 + Phase 2

**Assignable to**: 1 agent
**Depends on**: Stage 8 complete
**Note**: `rust_parsers/` directory does not exist yet — create from scratch.

| Task | File | Tool | Status |
|------|------|------|--------|
| 9.1 | Create `rust_parsers/` directory | — | `[ ]` |
| 9.2 | `rust_parsers/__init__.py` | RustParserRegistry | `[ ]` |
| 9.3 | `rust_parsers_clippy.py` | Clippy | `[ ]` |
| 9.4 | `rust_parsers_cargo_audit.py` | cargo-audit | `[ ]` |
| 9.5 | `rust_parsers_cargo_deny.py` | cargo-deny | `[ ]` |
| 9.6 | `rust_parsers_rustfmt.py` | rustfmt | `[ ]` |
| 9.7 | `rust_parsers_semgrep.py` | Semgrep | `[ ]` |
| 9.8 | `rust_adapter.py` | Adapter | `[ ]` |
| 9.9 | Rust Phase 1 IR layer | tree-sitter-rust | `[ ]` |
| 9.10 | `test_rust_tool_parsers.py` | Tests | `[ ]` |

**Reference**: [Adding-Rust.md](Adding-Rust.md)

---

## Parallel Work Assignment Guide

The table below shows which stages can run simultaneously:

```
Stage 1 (C++)
Stage 2 (C#)       ←── can start immediately after Stage 1 (or concurrently with Stage 1)
Stage 3 (Go)       ←── can start immediately; adapter already done
Stage 4a (Python)  ──┐
Stage 4b (JS)      ──┤ All three fully PARALLEL to each other AND to Stages 1-3
Stage 4c (Java)    ──┘
Stage 5 (Kotlin)   ←── after Stages 1-4 done
Stage 6 (PHP)      ←── after Stage 5
Stage 7 (Ruby)     ←── after Stage 6
Stage 8 (Swift)    ←── after Stage 7
Stage 9 (Rust)     ←── after Stage 8
```

**Maximum parallelism** (6 agents simultaneously):
- Agent A: Stage 1 C++ (tasks 1.3–1.6 in parallel within the agent)
- Agent B: Stage 2 C# (after 2.2 SARIF helper done)
- Agent C: Stage 3 Go
- Agent D: Stage 4a Python
- Agent E: Stage 4b JavaScript
- Agent F: Stage 4c Java

---

## Completion Checklist

Before marking any stage complete, verify:

- [ ] All tool files: no `raise NotImplementedError` in `execute_*` or `parse_*` methods
- [ ] Registry `get_parser("tool-name")` works for all tools in the stage
- [ ] All parsers return `[]` (not raise) when CLI tool not installed (`shutil.which` check)
- [ ] `pytest tests/languages/test_{lang}_tool_parsers.py -v` — all green
- [ ] `ruff check` + `black --check` pass
- [ ] `pyright src/` passes (no new type errors)

---

*Last updated: 2026-03-03 — Initial work tracking document based on full audit*
*See [Language-Completion-Roadmap.md](Language-Completion-Roadmap.md) for full output format specs and implementation patterns*
