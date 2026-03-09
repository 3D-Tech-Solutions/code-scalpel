# Language Completion Roadmap

This document tracks the **verified** implementation status of every language's static analysis tool parsers — based on a full file-by-file audit performed 2026-03-03. It sequences the gap-closure work required before a language is considered complete and before a new language can begin.

**Definition of "language complete"**: Phase 1 IR layer fully wired AND all `*_parsers/` tool files fully implemented (execution + output parsing + categorization + CWE mapping + report generation). See [Adding-A-Language.md](Adding-A-Language.md) for the full per-language checklist.

---

## MCP Surface Expansion Policy

> [20260303_DOCS] Established after the C++ static-analysis integration decision.

**Rule**: A new MCP tool is only added when the feature **cannot** be correctly integrated into an existing tool.

Before proposing a new tool, evaluate whether the feature belongs inside an existing one:

| Feature type | Default home |
|---|---|
| Language-specific linter / static-analysis tool output | `analyze_code` (`static_tools` parameter, `tool_findings` in response) |
| Security vulnerability detection (taint/sink) | `security_scan` or `cross_file_security_scan` |
| Dependency CVE check | `scan_dependencies` |
| Structural code query (call graph, refs) | `get_call_graph` / `get_symbol_references` |
| Policy / compliance check | `code_policy_check` |

**Rationale**

Agents that consume MCP tools pay a context-window cost proportional to the number of tools they must reason about. Keeping the surface small means:
- Agents can hold the full tool inventory in working memory without truncation.
- Tool discovery is simpler — one tool does one *conceptual* job.
- Tier gating stays centralised inside existing tools rather than spread across many.

**Acceptable reasons to add a new tool**

- The feature introduces a fundamentally different *interaction pattern* that would break existing callers if added as a parameter (e.g., it is async-streaming, or it returns a live session handle).
- The response schema is incompatible with all existing tools and merging would require a breaking change.
- The feature operates at a different granularity (project-wide vs. single-file) with no natural parent.

If none of the above apply, **extend an existing tool**.

---

## Audit: Verified Implementation Status (2026-03-03)

### Status Key

| Symbol | Meaning |
|--------|---------|
| ✅ COMPLETE | `execute_tool()` + `parse_output()` + categorize + report — production-ready |
| ⚠️ PARTIAL | Dataclasses and structure exist; execution logic raises `NotImplementedError` |
| ❌ STUB | Empty class or `raise NotImplementedError` only; no dataclasses |
| — | Not applicable |

---

### Python — `python_parsers/` (15/15 complete) ✅ COMPLETE [20260303_FEATURE]

Phase 1: ✅ Complete | Adapter: ✅ Complete | Registry: ✅ Working (lazy-load `__getattr__`)

| File | Lines | Status |
|------|-------|--------|
| `python_parsers_ast.py` | 4,047 | ✅ COMPLETE |
| `python_parsers_ruff.py` | 1,191 | ✅ COMPLETE |
| `python_parsers_mypy.py` | 1,472 | ✅ COMPLETE |
| `python_parsers_pylint.py` | 1,687 | ✅ COMPLETE |
| `python_parsers_bandit.py` | 1,647 | ✅ COMPLETE |
| `python_parsers_flake8.py` | 1,228 | ✅ COMPLETE |
| `python_parsers_code_quality.py` | 1,454 | ✅ COMPLETE |
| `python_parsers_pydocstyle.py` | 1,435 | ✅ COMPLETE |
| `python_parsers_pycodestyle.py` | 599 | ✅ COMPLETE |
| `python_parsers_prospector.py` | 1,089 | ✅ COMPLETE |
| `python_parsers_safety.py` | 324 | ✅ COMPLETE [20260303_FEATURE] |
| `python_parsers_isort.py` | 394 | ✅ COMPLETE [20260303_FEATURE] |
| `python_parsers_vulture.py` | 319 | ✅ COMPLETE [20260303_FEATURE] |
| `python_parsers_radon.py` | 568 | ✅ COMPLETE [20260303_FEATURE] |
| `python_parsers_interrogate.py` | 523 | ✅ COMPLETE [20260303_FEATURE] |

**Gap**: None — all 15 parsers complete. [20260303_FEATURE]

---

### JavaScript — `javascript_parsers/` (15/15 complete)

Phase 1: ✅ Complete | Adapter: ✅ Complete | Registry: ✅ Working (direct imports)

| File | Lines | Status |
|------|-------|--------|
| `javascript_parsers_esprima.py` | 1,434 | ✅ COMPLETE |
| `javascript_parsers_code_quality.py` | 1,025 | ✅ COMPLETE |
| `javascript_parsers_eslint.py` | 640 | ✅ COMPLETE |
| `javascript_parsers_treesitter.py` | 939 | ✅ COMPLETE |
| `javascript_parsers_babel.py` | 672 | ✅ COMPLETE |
| `javascript_parsers_flow.py` | 688 | ✅ COMPLETE |
| `javascript_parsers_prettier.py` | 503 | ✅ COMPLETE |
| `javascript_parsers_jshint.py` | 408 | ✅ COMPLETE |
| `javascript_parsers_standard.py` | 367 | ✅ COMPLETE |
| `javascript_parsers_typescript.py` | 815 | ✅ COMPLETE |
| `javascript_parsers_npm_audit.py` | 193 | ✅ COMPLETE |
| `javascript_parsers_jsdoc.py` | 239 | ✅ COMPLETE |
| `javascript_parsers_package_json.py` | 190 | ✅ COMPLETE |
| `javascript_parsers_test_detection.py` | 177 | ✅ COMPLETE |
| `javascript_parsers_webpack.py` | 258 | ✅ COMPLETE |

**Gap**: None — all 15 parsers complete. [20260303_FEATURE]

---

### TypeScript — `typescript_parsers/` (6/6 complete)

Phase 1: ✅ Complete | Adapter: ✅ Complete (via javascript_adapter) | Registry: ✅ Working

| File | Lines | Status |
|------|-------|--------|
| `parser.py` | 428 | ✅ COMPLETE |
| `analyzer.py` | 372 | ✅ COMPLETE |
| `type_narrowing.py` | 709 | ✅ COMPLETE |
| `decorator_analyzer.py` | 306 | ✅ COMPLETE |
| `alias_resolver.py` | 342 | ✅ COMPLETE |
| `tsx_analyzer.py` | 182 | ✅ COMPLETE |

**Gap**: None — TypeScript is fully complete.

---

### Java — `java_parsers/` (16/16 complete)

Phase 1: ✅ Complete | Adapter: ✅ Complete | Registry: ✅ Working (direct imports)

| File | Lines | Status |
|------|-------|--------|
| `java_parser_treesitter.py` | 1,107 | ✅ COMPLETE |
| `java_parsers_javalang.py` | 1,679 | ✅ COMPLETE |
| `java_parsers_SonarQube.py` | 252 | ✅ COMPLETE |
| `java_parsers_SpotBugs.py` | 249 | ✅ COMPLETE |
| `java_parsers_PMD.py` | 205 | ✅ COMPLETE |
| `java_parsers_Checkstyle.py` | 148 | ✅ COMPLETE |
| `java_parsers_ErrorProne.py` | 154 | ✅ COMPLETE |
| `java_parsers_FindSecBugs.py` | 163 | ✅ COMPLETE |
| `java_parsers_Infer.py` | 171 | ✅ COMPLETE |
| `java_parsers_JArchitect.py` | 174 | ✅ COMPLETE |
| `java_parsers_Gradle.py` | 183 | ✅ COMPLETE |
| `java_parsers_Maven.py` | 213 | ✅ COMPLETE |
| `java_parsers_DependencyCheck.py` | 200 | ✅ COMPLETE |
| `java_parsers_JaCoCo.py` | 197 | ✅ COMPLETE |
| `java_parsers_Pitest.py` | 185 | ✅ COMPLETE |
| `java_parsers_Semgrep.py` | 164 | ✅ COMPLETE |

**Gap**: None — all 16 parsers complete. [20260303_FEATURE]

> **Note**: The previous roadmap entry said "2/17 complete" — this was incorrect. The audit confirmed 10 of 16 tool parsers are production-ready. Only build/coverage/mutation tools remain as stubs.

---

### C++ — `cpp_parsers/` (6/6 complete)

Phase 1: ✅ Complete | Adapter: ✅ Complete (`cpp_adapter.py` — [20260303_FEATURE]) | Registry: ✅ Complete (`CppParserRegistry` — [20260303_FEATURE])

| File | Lines | Status |
|------|-------|--------|
| `cpp_parsers_Cppcheck.py` | 422 | ✅ COMPLETE — execute + XML parse + CWE mapping + report |
| `cpp_parsers_clang_tidy.py` | 459 | ✅ COMPLETE — execute + diagnostic/JSON parse + report |
| `cpp_parsers_Clang-Static-Analyzer.py` | 397 | ✅ COMPLETE — scan-build execute + plist parse + bug paths |
| `cpp_parsers_cpplint.py` | 330 | ✅ COMPLETE — execute + stderr parse + style score |
| `cpp_parsers_coverity.py` | 407 | ✅ COMPLETE — enterprise report parse only (execute raises NotImplementedError by design) |
| `cpp_parsers_SonarQube.py` | 400 | ✅ COMPLETE — enterprise API JSON parse (execute raises NotImplementedError by design) |

**Gap**: None — all 6 parsers complete. [20260303_FEATURE]

> **Integration note**: C++ tool-parser results are accessed via `analyze_code(file_path=..., static_tools=["cppcheck", ...])`.
> The `static_tools` parameter was added to `analyze_code` in [20260303_REFACTOR] — no separate MCP tool was created
> (see [MCP Surface Expansion Policy](#mcp-surface-expansion-policy)).
> Results appear in `tool_findings` of the `AnalysisResult`.
> Enterprise-only tools (coverity, sonarqube) require Enterprise tier for execution; all tiers can parse pre-existing report files.

---

### C# — `csharp_parsers/` (6/6 complete) ✅ COMPLETE [20260303_FEATURE]

Phase 1: ✅ Complete | Adapter: ✅ Complete (`csharp_adapter.py`) | Registry: ✅ Complete

| File | Lines | Status |
|------|-------|--------|
| `__init__.py` | 233 | ✅ COMPLETE — `CSharpParserRegistry` + shared `_parse_sarif()` SARIF 2.1 helper |
| `csharp_parsers_fxcop.py` | 260 | ✅ COMPLETE — FxCop XML/SARIF parse + execute + CWE mapping + report |
| `csharp_parsers_SecurityCodeScan.py` | 259 | ✅ COMPLETE — CWE-mapped security scanner; execute + SARIF 2.1 parse |
| `csharp_parsers_ReSharper.py` | 194 | ✅ COMPLETE — enterprise XML parse (execute raises NotImplementedError by design) |
| `csharp_parsers_Roslyn-Analyzers.py` | 172 | ✅ COMPLETE — `dotnet build` SARIF 2.1 output parse |
| `csharp_parsers_StyleCop.py` | 166 | ✅ COMPLETE — MSBuild SARIF 2.1 parse |
| `csharp_parsers_SonarQube.py` | 258 | ✅ COMPLETE — enterprise JSON API parse (execute raises NotImplementedError by design) |

**Tests**: `tests/languages/test_csharp_tool_parsers.py` — 46 tests passing [20260303_FEATURE]

> **Integration note**: C# tool-parser results are accessed via `analyze_code(file_path=..., static_tools=["roslyn", "stylecop", "fxcop", "scs", "resharper", "sonarqube"])`. `resharper` and `sonarqube` are enterprise-only (gated in `_ENTERPRISE_EXEC_TOOLS`).
> Wiring added to `_run_static_tools` in [20260304_FEATURE].

**Gap**: None — all 6 parsers + adapter + registry complete.

---

### Go — `go_parsers/` (6/6 complete) ✅ COMPLETE [20260303_FEATURE]

Phase 1: ✅ Complete | Adapter: ✅ Complete (`go_adapter.py`) | Registry: ✅ Complete

| File | Lines | Status |
|------|-------|--------|
| `__init__.py` | 113 | ✅ COMPLETE — `GoParserRegistry` with lazy-load factory |
| `go_parsers_golangci_lint.py` | 238 | ✅ COMPLETE — `golangci-lint run --out-format json`; Issues array + CWE mapping |
| `go_parsers_gosec.py` | 322 | ✅ COMPLETE — `gosec -fmt json`; built-in CWE IDs; execute + parse |
| `go_parsers_staticcheck.py` | 205 | ✅ COMPLETE — `staticcheck -f json ./...`; code/message/location JSON |
| `go_parsers_govet.py` | 166 | ✅ COMPLETE — `go vet ./...` stderr text parse; file:line:col format |
| `go_parsers_golint.py` | 176 | ✅ COMPLETE — text `file:line:col: msg` parse; confidence scoring |
| `go_parsers_gofmt.py` | 126 | ✅ COMPLETE — `gofmt -l .` file list; diff-based formatting issue report |

**Tests**: `tests/languages/test_go_tool_parsers.py` — 48 tests passing [20260303_FEATURE]

> **Integration note**: Go tool-parser results are accessed via `analyze_code(file_path=..., static_tools=["gofmt", "golint", "govet", "staticcheck", "golangci", "gosec"])`. All 6 Go tools are free/CLI — no enterprise gating.
> Wiring added to `_run_static_tools` in [20260304_FEATURE].

**Gap**: None — all 6 parsers + registry + `analyze_code` wiring complete.

---

### Kotlin — `kotlin_parsers/` (7/7 complete) ✅ COMPLETE [20260303_FEATURE]

Phase 1: ✅ Complete (`kotlin_normalizer.py` — 6 IR bugs fixed [20260303_BUGFIX]) | Adapter: ✅ Complete | Registry: ✅ Complete

| File | Lines | Status |
|------|-------|--------|
| `__init__.py` | 220 | ✅ COMPLETE — `KotlinParserRegistry` with lazy-load + `__getattr__` |
| `kotlin_parsers_Detekt.py` | 265 | ✅ COMPLETE — full integration with findings, severity, config |
| `kotlin_parsers_ktlint.py` | 326 | ✅ COMPLETE — comprehensive with rule sets, auto-correct |
| `kotlin_parsers_diktat.py` | 174 | ✅ COMPLETE — diktat SARIF/XML parse; CWE mapping; execute + parse |
| `kotlin_parsers_gradle.py` | 214 | ✅ COMPLETE — Gradle Kotlin build output; dependency check; task scan |
| `kotlin_parsers_compose.py` | 194 | ✅ COMPLETE — Android Lint SARIF parse; Compose-specific rules |
| `kotlin_parsers_Konsist.py` | 157 | ✅ COMPLETE — JUnit XML test-based architecture rule results |
| `kotlin_parsers_test.py` | 252 | ✅ COMPLETE — Test utilities; JUnit/Kotest/Spek result parsing |

**Tests**: `tests/languages/test_kotlin_tool_parsers.py` — 55 tests passing [20260303_FEATURE]

**Gap**: None — all 7 parsers + Phase 1 IR complete.

> **Normalizer note**: `kotlin_normalizer.py` had 6 bugs fixed [20260303_BUGFIX]: (1) class-level `_tree_cache` shared across instances; (2) dead branch in `visit_function_declaration`; (3) `visit_when_expression` passed entire `when_entry` to `_visit_block`; (4) `visit_for_statement` dropped no-brace single-statement body; (5) `visit_while_statement` same; (6) `visit_infix_expression` return type too narrow.

---

### PHP — `php_parsers/` (7/7 complete) ✅ COMPLETE — Stage 6

Phase 1: ✅ Complete (`php_normalizer.py` — [20260303_FEATURE]) | Adapter: ✅ Complete (`php_adapter.py`) | Registry: ✅ Working (lazy-load `__getattr__` with all 7 parsers)

| File | Status |
|------|--------|
| `__init__.py` | ✅ Registry expanded — all 7 parsers registered [20260304_FEATURE] |
| `php_parsers_PHPCS.py` | ✅ Full implementation — execute, JSON/XML parse, report [20260304_FEATURE] |
| `php_parsers_PHPStan.py` | ✅ Full implementation — execute, JSON parse, CWE map, report [20260304_FEATURE] |
| `php_parsers_Psalm.py` | ✅ Full implementation — execute, JSON parse, taint, CWE, report [20260304_FEATURE] |
| `php_parsers_phpmd.py` | ✅ Full implementation — execute, XML/JSON parse, CWE, report [20260304_FEATURE] |
| `php_parsers_ast.py` | ✅ Full implementation — PHPNormalizer-based extraction, no CLI [20260304_FEATURE] |
| `php_parsers_composer.py` | ✅ Full implementation — JSON parsing, vuln scan, report [20260304_FEATURE] |
| `php_parsers_exakat.py` | ✅ Full implementation — JSON/CSV parse, CWE, NotImplementedError execute [20260304_FEATURE] |

**Tests**: 79/79 passing (`tests/languages/test_php_tool_parsers.py` — [20260304_TEST])

---

### Ruby — `ruby_parsers/` (7/7 complete) ✅ COMPLETE [20260304_FEATURE]

Phase 1: ✅ `ruby_normalizer.py` | Adapter: ✅ `ruby_adapter.py` | Registry: ✅ `ruby_parsers/__init__.py`

| File | Lines | Status |
|------|-------|--------|
| `ruby_parsers_RuboCop.py` | ~230 | ✅ Full implementation — parse_json_output, execute_rubocop, generate_report |
| `ruby_parsers_Reek.py` | ~200 | ✅ Full implementation — parse_json_output, execute_reek, generate_report |
| `ruby_parsers_brakeman.py` | ~200 | ✅ Full implementation — parse_json_output, execute_brakeman, generate_report |
| `ruby_parsers_ast.py` | ~240 | ✅ Full implementation — RubyASTParser wrapping RubyNormalizer |
| `ruby_parsers_bundler.py` | ~230 | ✅ Full implementation — parse_text_output, execute_bundler_audit, generate_report |
| `ruby_parsers_simplecov.py` | ~200 | ✅ Full implementation — parse_resultset_json, coverage metrics |
| `ruby_parsers_fasterer.py` | ~180 | ✅ Full implementation — parse_text_output, performance metrics |

**Gap**: 0 — DONE

**Tests**: `tests/languages/test_ruby_tool_parsers.py` (49 tests) + `tests/languages/test_ruby_parser.py` (14 IR tests) — 63 passing

---

### Swift — `swift_parsers/` (0/4 complete)

Phase 1: ❌ Not started | Adapter: ❌ STUB (`swift_adapter.py`) | Registry: ❌ STUB (27 lines)

| File | Lines | Status |
|------|-------|--------|
| `swift_parsers_SwiftLint.py` | 90 | ⚠️ PARTIAL — SwiftLintViolation/SwiftLintConfig dataclasses; no execution |
| `swift_parsers_Tailor.py` | 85 | ⚠️ PARTIAL — code style; incomplete |
| `swift_parsers_sourcekitten.py` | 61 | ⚠️ PARTIAL — AST extraction; incomplete |
| `swift_parsers_swiftformat.py` | 47 | ⚠️ PARTIAL — code formatting; incomplete |

**Gap**: 4 files + registry + Phase 1 IR layer (not yet started)

---

### Rust

Phase 1: ✅ `rust_normalizer.py` | Adapter: ✅ `rust_adapter.py` | Registry: ✅ `rust_parsers/__init__.py`

| File | Status |
|------|--------|
| `rust_parsers_clippy.py` | ✅ Full implementation — parse compiler JSON, execute CLI, categorize findings [20260305_FEATURE] |
| `rust_parsers_rustfmt.py` | ✅ Full implementation — parse check output, execute CLI [20260305_FEATURE] |
| `rust_parsers_cargo_audit.py` | ✅ Full implementation — parse advisory JSON, execute CLI [20260305_FEATURE] |
| `rust_parsers_cargo_check.py` | ✅ Full implementation — parse compiler diagnostics, execute CLI [20260305_FEATURE] |
| `rust_parsers_rust_analyzer.py` | ✅ Full implementation — parse LSP diagnostics, documented enterprise-style execute stub [20260305_FEATURE] |

**Gap**: 0 — DONE for Phase 1 + current Phase 2 parser set.

---

## MCP Integration Surface Status

> [20260306_DOCS] Language completion is not the same thing as complete MCP-surface parity. This section tracks the runtime integration layer separately so docs do not overstate support.

| MCP Surface | Current Status |
|-------------|----------------|
| `analyze_code` / `extract_code` / `unified_sink_detect` | Broad polyglot support: Python, JavaScript, TypeScript, Java, C, C++, C#, Go, Kotlin, PHP, Ruby, Swift, Rust |
| `run_static_analysis` / shared static-tool dispatch | Polyglot dispatch present for C++, C#, Go, Python, JavaScript, TypeScript, Java, Ruby, Swift, Kotlin, PHP |
| `scalpel://analysis/...` and `scalpel://symbol/...` resources | Language-aware routing for the broad polyglot set; no longer Python-only for JS and similar files |
| `code:///{language}/{module}/{symbol}` resource templates | File-backed module resolution now covers Python, JavaScript, TypeScript, Java, C, C++, C#, Go, Kotlin, PHP, Ruby, Swift, Rust |
| Graph helpers (`get_call_graph`, `get_graph_neighborhood`, `get_cross_file_dependencies`) | Still Python-first overall. `get_call_graph` now has dedicated JavaScript, TypeScript, and Java runtime slices. `get_graph_neighborhood` supports local JS/TS function nodes, JS/TS method nodes when advanced resolution is available, and canonical Java method nodes via the shared call-graph runtime. `get_cross_file_dependencies` now exposes narrow graph-backed slices for JS/TS plus Java method dependencies. Next graph-runtime work should stay narrow and tool-specific rather than broadening cross-language claims. |

---

## Consolidated Gap Summary

| Language | Phase 1 | Adapter | Registry | Complete/Total | Files to write | Priority |
|----------|---------|---------|----------|----------------|---------------|----------|
| **TypeScript** | ✅ | ✅ | ✅ | 6/6 | **0 — DONE** | — |
| **Python** | ✅ | ✅ | ✅ | 15/15 | **0 — DONE** [20260303_FEATURE] | — |
| **JavaScript** | ✅ | ✅ | ✅ | 15/15 | 0 | Complete |
| **Java** | ✅ | ✅ | ✅ | 16/16 | 0 | Complete |
| **C++** | ✅ | ✅ | ✅ | 6/6 | **0 — DONE** | — |
| **C#** | ✅ | ✅ | ✅ | 6/6 | **0 — DONE** [20260303_FEATURE] | — |
| **Go** | ✅ | ✅ | ✅ | 6/6 | **0 — DONE** [20260303_FEATURE] | — |
| **Kotlin** | ✅ | ✅ | ✅ | 7/7 | **0 — DONE** [20260303_FEATURE] | — |
| **PHP** | ✅ | ✅ | ✅ | 7/7 | **0 — DONE** [20260304_FEATURE] | — |
| **Ruby** | ✅ | ✅ | ✅ | 7/7 | **0 — DONE** [20260304_FEATURE] | — |
| **Swift** | ✅ | ✅ | ✅ | 4/4 | **0 — DONE** [20260304_FEATURE] | — |
| **Rust** | ✅ | ✅ | ✅ | 5/5 | **0 — DONE** [20260305_FEATURE] | — |
| **C** | ✅ | ✅ | n/a | n/a | 0 (served by C++ tools) | — |

---

## Work Queue — Ordered by Strategic Priority

The ordering balances: (a) security ecosystem impact, (b) number of files to write, (c) scaffolding already in place.

---

### Stage 1 — C++ Tool Parsers ✅ COMPLETE [20260303_FEATURE]

All C++ tool parsers are fully implemented. Results are available via `analyze_code(file_path=..., static_tools=[...])` — no separate MCP tool was created (see [MCP Surface Expansion Policy](#mcp-surface-expansion-policy)).

| File | Status |
|------|--------|
| `cpp_adapter.py` | ✅ Done |
| `cpp_parsers/__init__.py` | ✅ Done — `CppParserRegistry` |
| `cpp_parsers_Cppcheck.py` | ✅ Done |
| `cpp_parsers_clang_tidy.py` | ✅ Done |
| `cpp_parsers_Clang-Static-Analyzer.py` | ✅ Done |
| `cpp_parsers_cpplint.py` | ✅ Done |
| `cpp_parsers_coverity.py` | ✅ Done (enterprise parse-only) |
| `cpp_parsers_SonarQube.py` | ✅ Done (enterprise parse-only) |

**Tests**: `tests/languages/test_cpp_tool_parsers.py` — 85 tests passing

---

### Stage 2 — C# Tool Parsers ✅ COMPLETE [20260303_FEATURE]

All C# tool parsers, adapter, registry, shared SARIF 2.1 helper, and `analyze_code` MCP wiring are fully implemented. 46 tests passing in `tests/languages/test_csharp_tool_parsers.py`.

**Why second**: .NET ecosystem is large; all 6 C# tools use SARIF 2.1 output, which means one shared `_parse_sarif()` helper in `__init__.py` covers Roslyn, StyleCop, and SecurityCodeScan. C# stubs are more minimal than C++ (28 lines each) — need both dataclass framework AND implementation.

**Files to write**:

| File | Tool type | Output format | Notes |
|------|-----------|--------------|-------|
| `csharp_adapter.py` | Adapter | — | Thin wrapper over `CSharpNormalizer` |
| `csharp_parsers/__init__.py` | Registry + SARIF helper | — | `CSharpParserRegistry` + shared `_parse_sarif()` |
| `csharp_parsers_Roslyn-Analyzers.py` | Free (dotnet build) | SARIF 2.1 JSON | Parse `dotnet build --no-incremental` SARIF output |
| `csharp_parsers_StyleCop.py` | Free (MSBuild) | SARIF 2.1 / XML | StyleCop.Analyzers MSBuild output |
| `csharp_parsers_SecurityCodeScan.py` | Free | SARIF 2.1 JSON | Security scanner; CWE mapping from rule ID prefix |
| `csharp_parsers_fxcop.py` | Free (legacy) | XML / SARIF | FxCop/Roslyn code analysis rules |
| `csharp_parsers_ReSharper.py` | Enterprise | XML (`inspectcode`) | JetBrains `inspectcode.exe` XML output |
| `csharp_parsers_SonarQube.py` | Enterprise | JSON API | Same pattern as C++ SonarQube |

**Tests**: `tests/languages/test_csharp_tool_parsers.py` — fixture-based, focus on SARIF parsing

---

### Stage 3 — Go Tool Parsers ✅ COMPLETE [20260303_FEATURE]

All Go tool parsers, registry, and `analyze_code` MCP wiring are fully implemented. 48 tests passing in `tests/languages/test_go_tool_parsers.py`.

**Why third**: Cloud-native ecosystem. Go adapter is already done. Registry stub exists but is empty. golangci-lint aggregates 50+ linters into one JSON output — implementing it well provides coverage over govet, staticcheck, and many others. gosec provides built-in CWE IDs.

**Files to write**:

| File | Tool type | Output format | Notes |
|------|-----------|--------------|-------|
| `go_parsers/__init__.py` | Registry | — | `GoParserRegistry` with lazy-load factory |
| `go_parsers_golangci_lint.py` | Free CLI | JSON `{"Issues":[...], "Report":{...}}` | **Priority 1** — meta-linter; `golangci-lint run --out-format json` |
| `go_parsers_gosec.py` | Free CLI | JSON `{"Golang gosec":{"Issues":[...]}}` | **Priority 2** — CWE IDs built-in |
| `go_parsers_staticcheck.py` | Free CLI | JSON `[{"code","message","location"}]` | `staticcheck -f json ./...` |
| `go_parsers_govet.py` | Free CLI | text `file:line:col: msg` | `go vet ./...`; stderr parsing |
| `go_parsers_golint.py` | Free CLI | text `file:line:col: msg` | Deprecated but still used |
| `go_parsers_gofmt.py` | Free CLI | unified diff or file list | `gofmt -l .`; returns files with formatting issues |

**Tests**: `tests/languages/test_go_tool_parsers.py` — fixture-based

---

### Stage 4 — Close Quick Wins (Python + JavaScript + Java) ✅ COMPLETE [20260303_FEATURE]

All parsers for Python, JavaScript, and Java are fully implemented. See the per-language audit tables above.

---

### Stage 5 — Kotlin Phase 2 Completion (then Phase 1) ✅ COMPLETE [20260303_FEATURE]

All Kotlin tool parsers are fully implemented and Phase 1 IR normalizer is complete (with 6 bugs fixed). 55 tests passing in `tests/languages/test_kotlin_tool_parsers.py`.

> **Phase 1 normalizer note**: `kotlin_normalizer.py` required 6 bug fixes [20260303_BUGFIX]: class-level `_tree_cache`, unreachable branch in function_declaration, when_entry body extraction, no-brace for/while body drop, return type narrowness. All corrected and verified.

---

### Stage 6 — PHP Phase 2 + Phase 1 ✅ COMPLETE [20260304_FEATURE]

PHP Phase 1 (IR normalizer, extractor, adapter, 32 tests) and Phase 2 (7 tool parsers, 79 tests) are complete. All 7 parsers implemented with execute/parse/report. 816 language tests passing total.

---

### Stage 7 — Ruby Phase 2 + Phase 1 ✅ COMPLETE [20260304_FEATURE]

All Ruby tool parsers (7/7), registry, adapter, and Phase 1 IR normalizer are fully implemented. 63 tests passing across `test_ruby_tool_parsers.py` (49 tests) and `test_ruby_parser.py` (14 IR tests). `test_polyglot_support.py` updated to include Ruby in all extension/detection/matrix rows.

---

### Stage 8 — Swift Phase 2 + Phase 1 ✅ COMPLETE [20260304_FEATURE]

Swift Phase 1 (`swift_normalizer.py`), adapter, registry, and all 4 Swift tool parsers are present in the repo. Resource-template and extraction layers can route Swift files, but graph tooling does not yet offer full language-parity semantics.

---

### Stage 9 — Rust Phase 2 + Phase 1 ✅ COMPLETE [20260305_FEATURE]

Rust Phase 1 (`rust_normalizer.py`), adapter, registry, and the current 5 Rust tool parsers are present in the repo. Resource-template and extraction layers can route Rust files, but graph tooling remains Python-first.

---

### Stage 10 — Graph Runtime Parity (Current Active Track) [20260306_FEATURE]

Graph-runtime parity should continue as targeted vertical slices, not broad language claims.

**Completed in the current slice**:

| Tool | Current JS/TS Status |
|------|----------------------|
| `get_call_graph` | Initial local JS/TS parity slice present |
| `get_graph_neighborhood` | Local JS/TS function nodes supported; JS/TS method nodes supported when advanced resolution is available |
| `get_cross_file_dependencies` | Initial local JS/TS graph-backed parity slice present; narrow Java method dependency slice landed |
| `get_symbol_references` | Initial local JS/TS definition/import/call/reference slice present; narrow Java definition/import/call/reference slice landed |
| `get_project_map` | Initial local JS/TS module discovery and import-derived relationship slice present; narrow Java module/relationship slice landed |

**Stage 10.1 hardening status**:

- [20260307_TEST] Tier/metadata coverage now explicitly exercises the JS/TS runtime slices for `get_call_graph`, `get_graph_neighborhood`, `get_cross_file_dependencies`, `get_symbol_references`, and `get_project_map`.
- [20260308_TEST] Focused graph-runtime coverage now also exercises the narrow Java slices for `get_graph_neighborhood`, `get_cross_file_dependencies`, `get_project_map`, and `get_symbol_references`.
- [20260308_TEST] `get_project_map` now has explicit JavaScript relationship and dependency-diagram fixtures, not just shared JS/TS path coverage via TypeScript cases.
- [20260308_TEST] Java override dispatch is now explicitly covered for `get_call_graph`, `get_graph_neighborhood`, and `get_cross_file_dependencies`, proving the landed Java slices prefer child overrides over superclass fallbacks.
- [20260308_BUGFIX] Java `get_symbol_references` now clears singular `definition_file` and `definition_line` metadata when overloads or overrides make the symbol identity ambiguous.
- [20260308_TEST] Java ambiguity guidance is now directly covered for `get_cross_file_dependencies`, and Java Mermaid/path metadata is explicitly covered for `get_call_graph`, `get_graph_neighborhood`, and `get_cross_file_dependencies`.
- [20260308_FEATURE] Java `get_symbol_references` now emits neutral ambiguity warnings when multiple Java definitions match, instead of only clearing singular definition metadata.
- [20260308_TEST] Java `get_call_graph` now has direct path-query fixtures, and Java `get_graph_neighborhood` now has direct enterprise path-query capability validation for canonical Java method nodes.
- [20260308_FEATURE] Java `get_symbol_references` now exposes structured ambiguity candidates for overload and override collisions, rather than warning-only disambiguation.
- [20260308_FEATURE] The shared Java call-graph runtime now emits signature-qualified selectors for overloaded methods, keeps non-overloaded Java IDs stable, and resolves exact signature then arity fallback through static-import and OO dispatch paths.
- [20260308_TEST] `get_cross_file_dependencies` now accepts structured Java selectors like `Helper.tool(int)`, and `get_graph_neighborhood` now directly validates signature-qualified Java method node IDs such as `java::demo/Helper::method::Helper:tool(int)`.
- [20260307_DOCS] Graph runtime docstrings were audited and corrected where the published tier limits had drifted from `limits.toml`.

**Java reassessment and follow-through**:

> [20260307_DOCS] Reassessed Java as the next graph-runtime candidate after Stage 10.1. Conclusion at that point: not yet a clean next parity slice. Java parser/IR support is mature, but the shared graph runtime was not Java-ready enough to repeat the narrow JS/TS playbook.

> [20260307_FEATURE] Follow-through landed in the shared call-graph stack: `.java` now enters shared file discovery, canonical Java callable nodes are emitted, and `get_call_graph` now has an initial Java runtime slice. Community sees local canonical Java nodes/calls; Pro/Enterprise additionally resolve cross-file Java type/static imports, typed imported instance calls, superclass method dispatch, and field-backed instance calls when the field type is statically declared.

- `get_call_graph` was the blocking prerequisite; that builder/file-discovery gap is now closed for `.java`.
- `get_graph_neighborhood` now accepts canonical Java method node IDs and reuses the shared Java call-graph runtime for local Community neighborhoods plus Pro/Enterprise cross-file neighborhoods.
- `get_cross_file_dependencies` now has a narrow Java method slice: Community resolves local method dependencies, while Pro/Enterprise reuse shared Java call-graph edges for cross-file dependency chains and accept exact structured selectors like `Helper.tool(int)`.
- `get_symbol_references` now includes a narrow Java runtime slice for parser-backed class/method definitions plus conservative import, static-import, call-site, and reference discovery, with structured ambiguity candidates when Java definition identity is ambiguous.
- `get_project_map` now scans `.java` files for class/method inventory and, in Pro/Enterprise, derives file relationships from explicit Java imports and static imports.
- Overloaded Java methods now flow through the shared graph runtime with signature-qualified selectors, which gives `get_call_graph`, `get_cross_file_dependencies`, and `get_graph_neighborhood` a common overload-aware identity model instead of helper-only string matching.

**Current decision**:

- Java is now a real Stage 10 presence across `get_call_graph`, `get_symbol_references`, `get_graph_neighborhood`, `get_cross_file_dependencies`, and `get_project_map`, but still not full graph-runtime parity.
- Keep the remaining Java graph/runtime work narrow and tool-specific, with stronger argument-type inference, constructor overload handling, and broader selector-hardening now the main adjacent work.

**Next roadmap steps**:

| Priority | Scope | Why |
|----------|-------|-----|
| 1 | Harden Java graph/runtime slices around stronger argument typing and selector resolution | The narrow Java slices now share overload-aware identities, but broader parity still depends on sharper call-site typing and selector choice |
| 2 | Extend overload-aware hardening to constructor cases and remaining ambiguous Java edges | Preserves accuracy without over-claiming parity |

**Tracked checklist**:

- [x] `get_call_graph`: initial local JS/TS parity slice landed.
- [x] `get_graph_neighborhood`: local JS/TS function support landed.
- [x] `get_graph_neighborhood`: JS/TS method-node support landed when advanced resolution is available.
- [x] `get_cross_file_dependencies`: initial local JS/TS graph-backed parity slice landed.
- [x] `get_symbol_references`: initial local JS/TS parity slice landed and validated for definitions/imports/calls/reference categories.
- [x] `get_project_map`: initial local JS/TS module discovery and graph-derived relationship slice landed and validated.
- [x] Tier coverage: extend JS/TS metadata-limit tests for all touched runtime surfaces.
- [x] Candidate expansion: reassess Java as the next graph-runtime candidate.
- [x] Java foundation: extend shared call-graph file discovery and canonical node emission to `.java` inputs.
- [x] Java slice viability: reassess and land a narrow Java `get_call_graph`-first runtime slice.
- [x] Java `get_call_graph`: local canonical Java callable nodes/calls plus Pro/Enterprise cross-file type/static-import resolution, typed imported instance calls, superclass method dispatch, and field-backed instance calls.
- [x] Java `get_graph_neighborhood`: canonical Java method-node acceptance plus local Community and cross-file Pro/Enterprise neighborhood extraction via the shared call-graph runtime.
- [x] Java `get_cross_file_dependencies`: narrow Java method dependency slice with local Community behavior and shared-runtime Pro/Enterprise cross-file chains.
- [x] Java `get_project_map`: narrow Java module discovery plus Pro/Enterprise file relationships from explicit imports and static imports.
- [x] Java `get_symbol_references`: narrow Java class/method definition plus import/static-import/call/reference slice landed and validated.
- [x] Java hardening: override-dispatch coverage now explicitly exercises child-over-base resolution for `get_call_graph`, `get_graph_neighborhood`, and `get_cross_file_dependencies`.
- [x] Java hardening: `get_symbol_references` now clears singular definition metadata when overloads or overrides make Java symbol identity ambiguous.
- [x] Java hardening: `get_symbol_references` now emits neutral warnings when Java definition identity is ambiguous.
- [x] Java hardening: ambiguity guidance is explicitly covered for `get_cross_file_dependencies`, and Mermaid/path metadata is explicitly covered for the landed Java graph-runtime slices.
- [x] Java hardening: `get_call_graph` now has direct Java path-query fixtures, and `get_graph_neighborhood` now has direct Java enterprise path-query capability validation.
- [x] Java hardening: `get_symbol_references` now exposes structured ambiguity candidates for overload and override collisions.
- [x] Java hardening: overload-aware selector identities now flow through the shared runtime, `get_cross_file_dependencies` accepts structured selectors like `Helper.tool(int)`, and `get_graph_neighborhood` validates signature-qualified Java method node IDs.
- [x] JavaScript `get_project_map`: direct JavaScript relationship and dependency-diagram fixtures now back the import-derived parity claim.

---

## Adapter Status

> [20260307_DOCS] The earlier adapter-stub table is obsolete. The currently tracked languages already have adapters wired; the active remaining gap is runtime parity in graph/context MCP surfaces.

| Adapter scope | Status |
|-------------|--------|
| `cpp_adapter.py` | ✅ Implemented |
| `csharp_adapter.py` | ✅ Implemented |
| `go_adapter.py` | ✅ Implemented |
| `java_adapter.py` | ✅ Implemented |
| `javascript_adapter.py` | ✅ Implemented |
| `kotlin_adapter.py` | ✅ Implemented |
| `php_adapter.py` | ✅ Implemented |
| `python_adapter.py` | ✅ Implemented |
| `ruby_adapter.py` | ✅ Implemented |
| `rust_adapter.py` | ✅ Implemented |
| `swift_adapter.py` | ✅ Implemented |
| `typescript` adapter path | ✅ Covered via JavaScript/TypeScript wiring |

---

## Tool Parser Implementation Patterns

### Free tool (execute + parse)

```python
import shutil
import subprocess
from pathlib import Path

class SomeToolParser:
    def execute_sometool(self, paths: list[Path], config=None) -> list[SomeIssue]:
        if shutil.which("sometool") is None:
            return []   # graceful: tool not installed
        cmd = ["sometool", "--format=json"] + [str(p) for p in paths]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return self.parse_json_output(result.stdout)

    def parse_json_output(self, output: str) -> list[SomeIssue]:
        import json
        data = json.loads(output or "[]")
        return [self._to_issue(item) for item in data]
```

### Enterprise tool (output file only)

```python
class EnterpriseToolParser:
    def execute_enterprise(self, paths, config=None):
        raise NotImplementedError(
            "EnterpriseTool requires a licensed installation. "
            "Run the tool externally and pass the output file to "
            "parse_json_report() instead."
        )

    def parse_json_report(self, report_path: Path) -> list[Finding]:
        import json
        data = json.loads(report_path.read_text())
        return [self._to_finding(item) for item in data.get("issues", [])]
```

### SARIF 2.1 helper (shared — especially for .NET / C# tools)

```python
def _parse_sarif(sarif_path: Path) -> list[SarifFinding]:
    """Parse SARIF 2.1 format (common across Roslyn, StyleCop, SecurityCodeScan)."""
    import json
    sarif = json.loads(sarif_path.read_text())
    findings = []
    for run in sarif.get("runs", []):
        for result in run.get("results", []):
            for location in result.get("locations", []):
                phys = location.get("physicalLocation", {})
                region = phys.get("region", {})
                findings.append(SarifFinding(
                    rule_id=result.get("ruleId", ""),
                    message=result.get("message", {}).get("text", ""),
                    severity=result.get("level", "warning"),
                    file_path=phys.get("artifactLocation", {}).get("uri", ""),
                    line=region.get("startLine", 0),
                    column=region.get("startColumn", 0),
                ))
    return findings
```

### Registry pattern (lazy-load)

```python
class LanguageParserRegistry:
    def __init__(self):
        from . import tool_a, tool_b, tool_c
        self._parsers = {
            "tool-a": tool_a.ToolAParser,
            "tool-b": tool_b.ToolBParser,
            "tool-c": tool_c.ToolCParser,
        }

    def get_parser(self, tool_name: str):
        cls = self._parsers.get(tool_name.lower())
        if cls is None:
            raise ValueError(
                f"Unknown tool: {tool_name!r}. Available: {sorted(self._parsers)}"
            )
        return cls()

    def analyze(self, path, tools: list[str] | None = None) -> dict[str, list]:
        tools = tools or list(self._parsers)
        results = {}
        for name in tools:
            try:
                parser = self.get_parser(name)
                results[name] = parser.execute(path) if hasattr(parser, "execute") else []
            except (NotImplementedError, FileNotFoundError, OSError):
                results[name] = []
        return results
```

---

## Version Plan (Revised)

| Version | Scope |
|---------|-------|
| `v2.1.x` | ✅ **Stage 1**: C++ tool parsers + adapter + registry; integrated into `analyze_code.static_tools` |
| `v2.1.x` | ✅ **Stage 2**: C# tool parsers + adapter + SARIF helper — 75 tests |
| `v2.1.x` | ✅ **Stage 3**: Go tool parsers + registry — 48 tests |
| `v2.1.x` | ✅ **Stage 4**: Python + JavaScript + Java quick-win stubs — all complete |
| `v2.2.0` | ✅ **Stage 5**: Kotlin Phase 2 completion + Phase 1 IR — 55 tests, 6 normalizer bugs fixed |
| `v2.3.0` | ✅ **Stage 6**: PHP Phase 1 IR (32 tests) + Phase 2 tool parsers (79 tests) — 111 tests total [20260304_FEATURE] |
| `v2.4.0` | **Stage 7**: Ruby Phase 2 + Phase 1 |
| `v2.5.0` | **Stage 8**: Swift Phase 2 + Phase 1 |
| `v2.6.0` | **Stage 9**: Rust Phase 1 + Phase 2 |

---

*Last audited: 2026-03-03 — full file-by-file review of all `code_parsers/` directories*
*Updated: 2026-03-04 — Stage 6 PHP complete: Phase 1 IR + Phase 2 (7 tool parsers, 79 tests, 816 total) [20260304_FEATURE]*
