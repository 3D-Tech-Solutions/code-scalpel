# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.1.0] - 2026-03-02

### Added
- **Full Go language support** via new `GoNormalizer` and `GoVisitor` (tree-sitter-go).
  Handles functions, methods (with receiver stored in metadata), structs, interfaces,
  imports (aliased and grouped), `var`/`const` declarations, `:=` short variable
  declarations, `if`/`for` statements, `return` statements, and call expressions.
  Extensions: `.go`
- `GoParserAdapter` — replaces the previous `NotImplementedError` stub with a full
  implementation that delegates to `GoNormalizer` and returns a typed `ParseResult`.
- Go integrated into `PolyglotExtractor` (`polyglot/extractor.py`) and
  `code_parsers.extractor` — extension-based and content-based detection.
- Content detection heuristics: `package main`, `func `, `import (`, `fmt.Println`,
  `fmt.Printf` — placed before Java check to avoid `"package "` ambiguity.
- `tree-sitter-go>=0.21.0` added to `[all]` and `[polyglot]` optional extras in
  `pyproject.toml`.
- `limits.toml`: `"go"` added to `analyze_code.languages` (Community, Pro, Enterprise);
  `"csharp"` and `"go"` added to `unified_sink_detect.languages` (all tiers — csharp
  was previously missing).
- 23 new Go-specific tests in `tests/languages/test_go_parser.py` covering extension
  detection, content detection, function/method/struct/interface/import extraction,
  `:=` short var, for-loop IR mapping, and round-trip via `PolyglotExtractor`.
- MCP docstrings in `extraction.py`, `analyze.py`, and `security.py` updated to list
  Go as a supported language.
- Internal wiki guides for adding Kotlin, Ruby, Rust, and Swift (four stub languages)
  as standalone documents in `wiki/`.

### Fixed
- `cli.py`: Removed unused `missing: list[str]` parameter from `_print_group()` and
  its three call sites — eliminates the Pyright "parameter declared but never used"
  warning (line 573).
- `go_normalizer.py`: Import alias now stored in `IRImport.alias` field (was
  incorrectly placed in `names=`).

---

## [2.0.2] - 2026-02-25

### Added
- **`unified_sink_detect`**: C and C++ sink detection (`c_sink_detection`, `cpp_sink_detection`) — all tiers
- **`generate_unit_tests`**: C/C++ test framework support (Catch2 — Community+; Google Test — Pro+); C# test framework support (NUnit — Community+; xUnit — Pro+)
- **`code_policy_check`**: C/C++ linting via `clang_tidy_rules` (Community+); C# linting via `roslyn_analyzer_rules` (Community+); MISRA-C safety-critical compliance via `misra_c_compliance` (Enterprise only)
- **`scan_dependencies`**: Package manager scanning for C/C++ via `conan_scanning` and `vcpkg_scanning`; C# via `nuget_scanning` — all tiers
- Tests: `tests/languages/test_v202_capabilities.py` covering all new C/C++/C# capabilities across all four tools

### Changed
- `limits.toml`: Added `"c"` and `"cpp"` to `unified_sink_detect` `languages` array for all three tiers
- `features.toml`: Expanded capability lists for `unified_sink_detect`, `generate_unit_tests`, `code_policy_check`, and `scan_dependencies`

---

## [2.0.1] - 2026-02-25

### Fixed
- Packaging fix: re-release to correct PyPI upload issue with v2.0.0 artifacts
- Documentation: wiki changelog backfill for v1.1.0 through v1.5.0 releases
- VS Code extension version aligned with Python package

---

## [2.0.0] - 2026-02-24

### Added
- **Full C language support** via new `CNormalizer` and `CVisitor` (tree-sitter-c).
  Handles functions (pointer/variadic/static/extern), structs (named, typedef, anonymous),
  unions, enums, `#include`/`#define` macros, bitfields, function pointer typedefs.
  Extensions: `.c`, `.h`
- **Full C++ language support** via new `CppNormalizer` and `CppVisitor` (tree-sitter-cpp).
  Handles classes (inline/out-of-line methods, virtual/override, operator overloading,
  multiple inheritance, nested classes), namespaces, templates (class/function/variadic),
  `enum class`, `constexpr`, move semantics, `= delete`/`= default`, `using`, anonymous
  namespaces, trailing return types.
  Extensions: `.cpp`, `.cc`, `.cxx`, `.c++`, `.hpp`, `.hxx`, `.hh`, `.h++`, `.inl`
- **Full C# language support** via new `CSharpNormalizer` and `CSharpVisitor` (tree-sitter-c-sharp).
  Handles classes, structs, interfaces, records, record structs, enums, methods (async/await,
  extension methods, tuple returns, operator overloads), properties, constructors, indexers,
  delegates, events, partial classes, generics with constraints, pattern-matching switches,
  nullable types.  Extensions: `.cs`
- All three languages integrated into `PolyglotExtractor` and `code_parsers.extractor`.
- `CSharpAdapter` upgraded from a `NotImplementedError` stub to a full implementation.
- 262 new language-specific tests (C, C++, C#) including real-world smoke tests:
  Win32 header, game-engine `Vec3`, Unity `MonoBehaviour` component, STL-style containers.

### Fixed
- `IRIf`/`IRWhile` constructed with wrong `condition=` kwarg in C# normalizer (correct: `test=`);
  caused `TypeError` crash on any `if` inside a C# method body.
- C# `tuple_type` missing from `_TYPE_NODES`; methods with tuple returns had names misidentified.
- C# `operator_declaration` lacked a visitor; operator overloads (`operator+`, `operator==`) were
  silently dropped.
- C++ `_parse_class_body` did not unwrap `field_declaration → class_specifier` wrappers, making
  nested class definitions invisible.

### Changed
- Version bumped from 1.5.0 to 2.0.0 (major: addition of three production language families).
- `capabilities/README.md` language list expanded: added `c`, `cpp`, `csharp`.
- Documentation updated throughout to reflect 7-language polyglot support.

---

## [1.5.0] - 2026-02-24

### Added
- Comprehensive **C and C++ parsing support** via new `c_normalizer` and `cpp_normalizer`.
  - Recognizes `.c`, `.h` (C); `.cpp`, `.cc`, `.cxx`, `.c++`, `.hpp`, `.hxx`, `.hh`, `.h++`, `.inl` (C++).
  - IR nodes for functions, structs, unions, enums, macros, classes, namespaces, templates, \#includes, `using` declarations, qualified method names, lambdas, and more.
  - C/C++ languages integrated into the existing `PolyglotExtractor` abstraction.
  - Language detection heuristics updated to distinguish C vs C++ with content and extension analysis.
  - New tests under `tests/languages/test_c_cpp_parsers.py` exercise realistic 3D project patterns (Vec3, Mesh, AABB, etc.)
- `code_parsers.extractor` now includes C/C++ in its `Language` enum, `EXTENSION_MAP`, detection heuristics, and parsing dispatch.
- Tests and examples migrated off deprecated `code_scalpel.polyglot` module; `code_parsers` is now the canonical import path.

### Changed
- Updated `CHANGELOG.md` and other documentation to reflect migration timeline and new features.

### Deprecated
- `code_scalpel.polyglot` imports used in tests are replaced; polyglot module will be removed in v3.3.0.

## [1.4.1] - 2026-02-24

### Added
- `codescalpel check` command: inspects an existing `.code-scalpel` directory and
  reports which expected configuration files are present, missing-but-recommended,
  or missing-and-required — without modifying anything.
  - `--json` / `-j` flag: machine-readable output with per-file `integrity` object.
  - `--fix` / `-F` flag: fills in any missing files before reporting, so check and
    fix happen in one step (equivalent to `init` followed by `check`).
  - Integrity checking: files are parsed (JSON/YAML/Rego) and flagged if empty or
    corrupt. Required files with integrity failures cause `exit 1` just like missing
    required files.
- `codescalpel init` is now **safe to re-run** on existing configurations: when
  `.code-scalpel/` already exists, `init` calls the new `add_missing_config_files()`
  helper which adds only absent files — all existing customisations are preserved.
  This is the recommended upgrade path when moving between Code Scalpel versions
  (e.g. users missing `response_config.json` after upgrading from <1.4.0).
- `add_missing_config_files(target_dir)` API in `code_scalpel.config.init_config`:
  programmatic equivalent of re-running `init` on an existing directory.

---

## [1.4.0] - 2026-02-20

### Added
- `response_config.json` and `response_config.schema.json` are now created automatically on first MCP server boot / `codescalpel init`, so users and AI agents can immediately control output verbosity without manual setup.
- `exclude_when_tier` support documented in generated schema and template — allows per-tool, per-tier field suppression.

### Changed
- **Tier limit rebalancing:** Data-driven recalibration of all tier limits
  - Community: Raised to cover solo dev projects ≤500 files (scanner 50→500, get_call_graph depth 3→10/nodes 50→200, get_file_context lines 500→2000, symbolic_execute paths 50→100, extract_code depth 0→1, generate_unit_tests cases 5→10, cross_file_security_scan depth 3→5/modules 20→50, code_policy_check files 50→100/rules 20→50)
  - Pro: All numeric limits now unlimited (match Enterprise) — Pro differentiates on features not scale caps
  - Enterprise: Fixed unified_sink_detect.max_sinks bug (was 50, same as Community → now unlimited)
- Updated 25+ tier test files across 8 test directories to reflect new limit values
- Updated capabilities/README.md tier comparison table with accurate limit values
- `response_config.json` template version updated to `1.4.0`.
- Profile default alignment: `DEFAULT_CONFIG` now defaults to `"standard"` instead of `"minimal"`, matching the generated template.
- Non-functional `parsing` section removed from `response_config.json` template and schema.

### Fixed
- Graph tools (`get_call_graph`, `get_graph_neighborhood`, `get_project_map`, `get_cross_file_dependencies`, `cross_file_security_scan`) now respect `response_config.json` filtering.
- Hot reload now works: edits to `response_config.json` take effect without a server restart.
- `features.toml`: Added 3 missing Pro capabilities to Enterprise (closure_detection, dependency_injection_suggestions, variable_promotion in extract_code; code_ownership_mapping in get_project_map)
- `limits.toml`: Enterprise unified_sink_detect.max_sinks was incorrectly 50 (same as Community), now unlimited
- Pre-existing `max_updates_per_session` → `max_updates_per_call` key mismatch in integration tests

### Deprecated
- `ResponseFormatter` class in `response_formatter.py` is now marked as deprecated. It will be removed in v1.5.0.

### Planned
- Custom language profile support (unified LanguageProfile abstraction; Phase 2 parser registries for Go, C#, C++, Ruby, Swift)
- Language Server Protocol (LSP) integration

---

## [1.3.5] - 2026-02-10

### Fixed
- Windows UnicodeEncodeError on `codescalpel init` — all `write_text()`/`read_text()` calls now specify `encoding='utf-8'`
- MCP server auto-init now creates full configuration scaffolding (20 files) instead of empty directory

### Changed
- Enhanced MCP server boot banner: shows license tier, license file path, and visual separators
- Removed internal `limits.toml` and `features.toml` references from public documentation
- **Architectural refactor:** Moved `limits.toml` and `features.toml` from `.code-scalpel/` to `src/code_scalpel/capabilities/` — packaged automatically, no `force-include` needed
- Restructured `.gitignore`: selective ignores for `.code-scalpel/` sensitive files instead of blanket directory ignore
- Untracked private key and runtime audit data from `.code-scalpel/`

### Added
- Startup update check: non-blocking PyPI version query notifies users of available updates
- Unicode encoding validation script (`scripts/validate_encoding.py`) and CI job
- License setup documentation (`docs/LICENSE_SETUP.md`)

---

## [1.3.4] - 2026-02-05

### Added
- **`.code-scalpel/features.toml`**: New bundled TOML source of truth for capability
  feature sets and descriptions (66 sections: 22 tools × 3 tiers).  Replaces the
  1600-line hardcoded `TOOL_CAPABILITIES` dict in `features.py`.
- **`config_loader` features subsystem**: Parallel to limits, adds `_find_features_file()`,
  `load_features()`, `get_cached_features()`, `clear_features_cache()` with the same
  bundled-only + stat-based caching pattern.
- **Sentinel conversion**: `-1` in TOML (numeric limits) is converted to `None`
  (unlimited) at runtime via `_sanitise_limits()` helper.

### Changed
- **limits.toml ownership**: Tier limits are now fully package-managed.  The single
  source of truth is `.code-scalpel/limits.toml`; `hatch force-include` copies it into
  the wheel at `code_scalpel/capabilities/limits.toml`.  No environment-variable or
  user-filesystem overrides are honoured at runtime.
- **`config_loader._find_config_file()`**: Replaced the 7-layer search (env var, CWD,
  home, `/etc/`, package-root walk) with two paths: bundled wheel copy first, dev-checkout
  fallback second.
- **`capabilities/resolver.py`**: Removed duplicate file-finding, TOML loading, and
  thread-locked cache.  Now delegates entirely to `config_loader` for all I/O and caching.
- **`features.py` rewritten as thin loader**: Reduced from ~1600 lines to ~230 lines.
  Now assembles capability envelopes by loading features.toml + limits.toml via
  `config_loader`.  `TOOL_CAPABILITIES` dict is now a lazy-loading `_ToolCapabilitiesProxy`
  shim for backward compatibility with existing test/assertion code.
- **`pyproject.toml` force-include**: Added `.code-scalpel/features.toml` →
  `code_scalpel/capabilities/features.toml` for both wheel and sdist targets.
- **`.code-scalpel/limits.toml`**: Added missing limit keys from the old hardcoded
  features.py (`vulnerability_types`, `max_depth` for `crawl_project`, `frontend_only`,
  `custom_sinks_limit`, `signature_validation`, `tamper_detection`, etc.).  Uses `-1`
  for unlimited values instead of omitting keys.

### Removed
- `src/code_scalpel/capabilities/limits.toml` — was a checked-in duplicate of
  `.code-scalpel/limits.toml`.  The build reproduces it via `force-include`; it is no
  longer committed to the repository.
- Stale override documentation from both `limits.toml` files (env-var, home-dir,
  `/etc/`, `limits.local.toml` references).

### Fixed
- **Test injection pattern**: 6 tests updated from `setenv("CODE_SCALPEL_LIMITS_FILE")`
  (dead env var) to `monkeypatch.setattr("config_loader._find_config_file", lambda: ...)`
  for custom limit injection.
- **Sentinel conversion tests**: Updated `test_update_symbol_tiers.py` assertions from
  `max_updates_per_call == -1` to `is None` (runtime semantic after sentinel conversion).
- **Tool count assertions**: Updated `test_ci_license_injection.py` to match actual
  limits.toml tool counts (pro: 2 locked, enterprise: 14 available).
- **`test_null_values_in_config`**: Updated to assert on `enterprise.update_symbol.max_updates_per_call`
  (which has `-1` → `None` conversion) instead of non-existent `max_depth`.

---

## [1.3.3] - 2026-02-02

### Changed
- **Project Structure Migration**: Consolidated scattered cache directories into `.code-scalpel/cache/`
  - Migrated `.scalpel_cache/`, `.code_scalpel_cache/`, `.scalpel_ast_cache/` → `.code-scalpel/cache/`
  - Renamed `.code-scalpel/license/` → `.code-scalpel/licenses/`
  - Cleaned up temporary directories (`.tmp_tier_comm/`, `.tmp_tier_fallback/`)
  - Updated all runtime cache path references in source code
- **verify.sh Step Numbering**: Fixed inconsistent step numbering (was 1/4, 3/8, 5/8... now consistent 1/11 through 11/11)
- **verify.sh Header Documentation**: Added comprehensive header with purpose, runtime, prerequisites, and usage

### Added
- **Version Sync Check**: Pre-check in `verify.sh` detects version mismatches between `pyproject.toml` and `__init__.py`
- **`scripts/verify_version_sync.sh`**: Standalone version consistency checker
- **`--skip-build` Flag**: `verify.sh` now supports `--skip-build` to skip expensive build check during iteration
- **`scripts/migrate_project_structure.sh`**: One-time migration script for project structure consolidation
- **`docs/PIPELINE.md`**: Comprehensive CI/CD pipeline documentation covering all three validation tiers
- **`tests/README.md`**: Test suite organization guide with category descriptions and usage examples
- **Troubleshooting Docs**: Added detect-secrets, version sync, and --skip-build troubleshooting to `docs/DEVELOPMENT.md`
- **Navigation Links**: Updated `docs/README.md` with links to MCP tools reference, pipeline docs, and development workflow

### Fixed
- Version mismatch between `pyproject.toml` (1.3.2) and `src/code_scalpel/__init__.py` (was 1.3.0, now synced)

---

## [1.3.2] - 2026-02-02

### Changed
- **Security Hardening**: Added 40+ `.gitignore` patterns blocking API tokens, credentials, vault files, environment configs, and CI/CD artifacts

### Added
- **detect-secrets Pre-commit Hook**: Yelp/detect-secrets v1.4.0 integration with `.secrets.baseline`
- **`.gitignore` Security Sections**: API tokens, environment variants, vault management, CI/CD artifacts, test credentials

### Fixed
- Redacted exact JWT file paths and vault key names from `docs/GITHUB_SECRETS.md`
- Removed broken license examples from documentation (pointed to licensing team)

---

## [1.3.1] - 2026-02-01

### Changed
- **Black/Ruff Path Alignment**: Fixed `verify_local.sh` to check only `src/ tests/` (matching CI), not entire repo
- **Pre-commit Hook Speed**: Changed pre-commit hook from `verify.sh` (comprehensive) to `verify_local.sh` (fast auto-fix)

### Added
- **Documentation Validation Steps**: Added Steps 9-11 to `verify.sh` for MCP tools reference and docs sync validation
- **Optional Security Checks**: Added Bandit and pip-audit as warning-only checks in `verify_local.sh`

---

## [1.3.0] - 2026-02-01

### Added
- **Oracle Resilience Middleware**: Automatic error recovery for AI agent mistakes
  - `@with_oracle_resilience` decorator for MCP tools
  - Symbol fuzzy matching with Levenshtein distance (typo correction)
  - Path resolution with workspace-aware suggestions
  - `SymbolStrategy`: Recovers from symbol name typos (e.g., "procss_data" → "process_data")
  - `PathStrategy`: Recovers from path errors with intelligent suggestions
  - `SafetyStrategy`: Validates refactoring operations
  - `NodeIdFormatStrategy`: Recovers from node ID format errors
  - `MethodNameFormatStrategy`: Recovers from method name format errors
  - `CompositeStrategy`: Chain multiple strategies for complex recovery
- **Stage 2 Error Enhancement**: Oracle now enhances both `envelope.error` and `data.error` patterns
  - `_enhance_error_envelope()`: Processes top-level envelope errors
  - `_enhance_data_error()`: Processes nested data.error patterns
  - Consistent error enhancement across all error locations
- 61 comprehensive Oracle middleware tests (100% pass rate)
- Tier isolation tests verifying Oracle behavior across Community/Pro/Enterprise

### Changed
- Updated test suite to handle Oracle-enhanced `ToolError` objects
  - Added `get_error_message()` helper for backward-compatible error checking
  - Tests now work with both string errors and `ToolError` objects
- Moved documentation to organized subdirectories:
  - Oracle docs → `docs/oracle/`
  - Docstring analysis → `docs/reference/`
  - Architecture docs → `docs/architecture/`
- Cleaned up root directory (removed 10+ markdown files to proper locations)

### Fixed
- Black formatting exclusion for `tests/mcp_tool_verification/` (intentionally broken test files)
- Unused imports in test files cleaned up
- `envelope.error` check now uses `model_dump()` for proper Pydantic v2 handling

### Documentation
- Added Oracle Resilience documentation suite:
  - `docs/oracle/ORACLE_INTEGRATION_GUIDE.md` - Complete integration guide
  - `docs/oracle/ORACLE_RESILIENCE_QUICKSTART.md` - Quick start guide
  - `docs/oracle/ORACLE_COMPREHENSIVE_ANALYSIS.md` - Deep dive analysis
  - `docs/ORACLE_RESILIENCE_IMPLEMENTATION.md` - Implementation details
  - `docs/ORACLE_RESILIENCE_TEST_CASES.md` - Test case documentation

---

## [1.2.1] - 2026-01-26

### Fixed
- **UVX Entry Point**: Fixed missing `codescalpel` entry point that prevented `uvx codescalpel` from working
  - v1.1.0 regression: package was renamed to `codescalpel` on PyPI but only had `code-scalpel` entry point
  - Both `codescalpel` and `code-scalpel` commands now available and work identically
  - Verified backward compatibility: all CLI tests pass
  - Fixes deployment for MCP via stdio, HTTP(S), and Docker

---

## [1.2.0] - 2026-01-26

### Added
- **Project Awareness Engine**: New subsystem for intelligent codebase analysis
  - `ProjectWalker`: Fast file discovery with smart filtering (530 lines)
    - 9+ language detection (Python, JS, TS, Java, C++, C#, Ruby, Go, Rust)
    - 19 default exclusion patterns with custom override support
    - Symlink cycle detection using inode tracking
    - Optional .gitignore support
    - Token estimation for context sizing
  - `ProjectContext`: Metadata storage and intelligent caching (514 lines)
    - Directory classification (source, test, build, docs, vendor, config)
    - File importance scoring (0.0-1.0 scale)
    - In-memory and optional SQLite caching
    - Change detection via MD5 hashing
    - TTL-based cache invalidation (configurable per subsystem: 7 days project cache, 24h incremental index, 5 min graph cache)
  - `ParallelCrawler`: Parallel file scanning via `ThreadPoolExecutor` (batch size 100, supports 100k+ files; Pro/Enterprise tier-gated)
  - `IncrementalIndex` / `IncrementalIndexer`: Incremental project updates with SQLite backing, dependency-aware cascading invalidation, optional Redis support
  - `FileInfo`, `DirectoryInfo`, `ProjectMap` data classes
  - `DirectoryType` enum for semantic directory classification
  - All language extension constants exported from analysis module
- Comprehensive documentation: `docs/PROJECT_AWARENESS_ENGINE.md` (473 lines)
  - Quick start guide with 3+ code examples
  - Complete API reference
  - Performance benchmarks
  - 5+ real-world use cases
  - Integration patterns

### Changed
- **ProjectCrawler Refactoring**: Now uses ProjectWalker for file discovery
  - Eliminated 51 lines of duplicate gitignore handling
  - Single source of truth for file discovery
  - 100% backward compatible with existing code

### Testing
- Added 39 comprehensive tests for Project Awareness Engine (100% pass rate)
- All 31 existing ProjectCrawler tests continue to pass
- Performance benchmarking for large project structures
- Symlink cycle handling verification

### Documentation
- Added PROJECT_AWARENESS_ENGINE.md with complete feature documentation
- Updated ARCHITECTURE_IMPLEMENTATION.md references
- Added code examples for all major use cases
- Performance characteristics and scaling notes

### Performance
- File discovery time for 1,000 files: ~50ms
- Memory consumption: ~2MB per 1,000 files
- Symlink cycle detection: O(1) per traversal

---

## [1.1.0] - 2026-01-26

### Added
- Phase 6 Kernel Integration for `analyze_code` tool
- SourceContext model for unified input handling
- SemanticValidator for pre-analysis input validation
- ResponseEnvelope with metadata and tier information
- UpgradeHints for tier-based feature suggestions
- Self-correction support for AI agents

### Changed
- `analyze_code` now uses hybrid kernel architecture
- Enhanced response metadata with version tracking and duration metrics
- Improved error handling with structured error responses

### Fixed
- Package name corrected in pyproject.toml (code-scalpel → codescalpel) for PyPI compatibility
- All documentation updated to reflect correct package name

### Security
- Backward compatible with all existing tools (no breaking changes)
- Hybrid architecture allows gradual kernel adoption across tool suite

---

## [1.0.2] - TBD

### Planned Release Improvements
- Enhanced publication automation
- Streamlined release process documentation
- Multi-platform release verification
- Release notes best practices

**Status**: Planning phase

---

## [1.0.1] - 2025-01-25

### Added
- Tier-based request/response governance (Community/Pro/Enterprise)
- Parameter clamping with applied limits metadata
- Comprehensive refactor validation report
- Installation guide for Claude Desktop (INSTALLING_FOR_CLAUDE.md)
- Release guide documentation (RELEASING.md)
- Release notes template for future releases (RELEASE_NOTES_TEMPLATE.md)
- Enhanced backward compatibility documentation (STABLE PUBLIC API designation)

### Fixed
- Version synchronization: __init__.py now matches pyproject.toml (1.0.1)
- Deprecated datetime.datetime.now() → datetime.now(timezone.utc) in licensing module (6 locations)
- Removed version mismatch between package version strings

### Changed
- Enhanced polyglot module deprecation notice with v3.3.0 timeline
- Improved error handling consistency across all 22 MCP tools
- Better tier enforcement validation with get_tool_capabilities()

### Documentation
- Added REFACTOR_VALIDATION_REPORT.md with tool compliance matrix (100% pass rate)
- Enhanced stability markers for backward-compatible exports
- Clear deprecation timelines (v2.0.0, v3.3.0)
- Comprehensive MCP protocol compliance documentation

### Verified
- All 22 tools pass 13-point compliance criteria (100%)
- Zero duplicate implementations (old + new)
- Zero deprecated imports in active source code
- All helper functions properly mapped

**Release Date**: 2025-01-25
**See also**: [RELEASE_NOTES_v1.0.1.md](docs/release_notes/RELEASE_NOTES_v1.0.1.md)

---

## [1.0.0] - 2026-01-17

### Initial Public Release

Code Scalpel is an MCP server toolkit that enables AI assistants to perform surgical code operations through AST parsing, taint analysis, and symbolic execution.

### Features

#### Code Analysis (6 tools)
- **`analyze_code`** - Parse code structure: functions, classes, imports, complexity metrics
- **`get_file_context`** - Quick file overview without reading full content
- **`crawl_project`** - Comprehensive project-wide analysis
- **`get_project_map`** - Multi-language project structure mapping
- **`scan_dependencies`** - Dependency analysis and version checking
- **`get_graph_neighborhood`** - Extract k-hop subgraphs around code symbols

#### Code Navigation (3 tools)
- **`get_call_graph`** - Function call relationships and dependencies
- **`get_cross_file_dependencies`** - Import resolution across files
- **`get_symbol_references`** - Find all usages of functions, classes, variables

#### Security Analysis (4 tools)
- **`security_scan`** - Taint-based vulnerability detection (SQL injection, XSS, etc.)
- **`cross_file_security_scan`** - Track taint flow across module boundaries
- **`unified_sink_detect`** - Polyglot dangerous function detection with CWE mapping
- **`type_evaporation_scan`** - Detect TypeScript/Python type boundary vulnerabilities

#### Code Extraction & Modification (3 tools)
- **`extract_code`** - Surgically extract functions/classes (99% token reduction)
- **`update_symbol`** - Safe, atomic symbol replacement with backup
- **`rename_symbol`** - Consistent renaming across definition and references

#### Testing & Verification (4 tools)
- **`generate_unit_tests`** - Symbolic execution generates tests for all paths
- **`symbolic_execute`** - Z3-based path exploration and constraint solving
- **`simulate_refactor`** - Verify code changes are safe before applying
- **`code_policy_check`** - Automated compliance and style checking

#### Utilities (2 tools)
- **`validate_paths`** - Security boundary enforcement for file access
- **`verify_policy_integrity`** - Cryptographic policy file verification

### Tier System

- **Community** - Free access to all 22 tools with baseline capabilities
- **Pro** - Unlimited findings, cross-file analysis, advanced features
- **Enterprise** - Compliance reporting, custom policies, audit trails

### Supported Languages

- Python (full AST + PDG + symbolic execution)
- JavaScript/TypeScript (AST + basic analysis)
- Java (AST parsing)
- Go, Rust, Ruby, PHP (AST parsing via tree-sitter)

### MCP Transports

- **stdio** - VS Code, GitHub Copilot, Claude Desktop
- **HTTP/SSE** - Remote servers, team deployments
- **Docker** - Isolated environments, CI/CD pipelines
