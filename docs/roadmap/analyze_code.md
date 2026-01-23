# analyze_code Tool Roadmap

**Tool Name:** `analyze_code`  
**Tool Version:** v1.0  
**Code Scalpel Version:** v1.0  
**Current Status:** ✅ **Stable** - Pre-release validation completed  
**Test Coverage:** 107 tests passing (100% pass rate)  
**Primary Module (MCP Tool Implementation):** `src/code_scalpel/mcp/server.py` (`_analyze_code_sync`)  
**Related Module (Python-only deeper analysis pipeline):** `src/code_scalpel/analysis/code_analyzer.py`  
**Tier Availability:** All tiers (Community, Pro, Enterprise)

---

## Overview

The `analyze_code` MCP tool provides static (non-executing) code structure analysis.

What it does today (v3.3):
- Supports **Python** via `ast`.
- Supports **JavaScript/TypeScript** via `tree-sitter`.
- Supports **Java** via a dedicated analyzer.

It extracts functions/classes/imports, computes a basic complexity score, and returns basic heuristics ("issues"). It does **not** run a full vulnerability scan; use `security_scan` for that.

---

## Polyglot Architecture Definition

**Current Status:** Partially polyglot (4 languages, Python-heavy enrichments)

### Language Support Matrix

The tool supports 4 languages but with vastly different enrichment capabilities:

| Language | Community | Pro | Enterprise | Implementation | Status |
|----------|-----------|-----|------------|---|---|
| Python | ✅ Full | ✅ Full | ✅ Full | ast stdlib | ✅ Stable |
| JavaScript | ✅ Basic | ⚠️ Limited | ⚠️ Limited | tree-sitter | ✅ Working |
| TypeScript | ✅ Basic | ⚠️ Limited | ⚠️ Limited | tree-sitter | ✅ Working |
| Java | ✅ Basic | ⚠️ Limited | ⚠️ Limited | tree-sitter | ✅ Working |
| **Go** | ❌ **Not implemented** | ❌ | ❌ | Config only | 🔴 **Advertised but missing** |
| **Rust** | ❌ **Not implemented** | ❌ | ❌ | Config only | 🔴 **Advertised but missing** |

### Enrichment Capability Matrix (The Real Polyglot Gap)

While basic structure extraction (functions, classes, imports) works across all 4 supported languages, **enrichments are predominantly Python-only**:

| Enrichment | Python | Java | JS/TS | Status | Notes |
|---|---|---|---|---|---|
| Functions/Classes | ✅ | ✅ | ✅ | Stable | Unified format |
| Imports | ✅ | ✅ | ✅ | Stable | Unified format |
| Cyclomatic Complexity | ✅ | ⚠️ | ⚠️ | Partial | Basic for non-Python |
| **Cognitive Complexity** | ✅ Pro | ❌ | ❌ | **Python-only** | Sonar metric |
| **Code Smells** | ✅ Pro | ❌ | ❌ | **Python-only** | 7+ patterns |
| **Halstead Metrics** | ✅ Pro | ❌ | ❌ | **Python-only** | n1, n2, N1, N2, volume, effort |
| **Duplicate Detection** | ✅ Pro | ❌ | ❌ | **Python-only** | Sliding window analysis |
| **Dependency Graph** | ✅ Pro | ❌ | ❌ | **Python-only** | Call graph |
| Framework Detection | ✅ | ✅ | ✅ | Best-effort | Heuristic-based |
| **Dead Code Hints** | ✅ Pro | ❌ | ❌ | **Python-only** | Unused imports, unreachable |
| **Decorator Summary** | ✅ Pro | ❌ | ❌ | **Python-only** | Annotation inventory |
| Type Summary | ✅ Pro | ❌ | ✅ | Partial | Basic for TS |
| **Naming Conventions** | ✅ Enterprise | ❌ | ❌ | **Python-only** | PEP8 validation |
| **Compliance Checks** | ✅ Enterprise | ❌ | ❌ | **Python-only** | Bare except, plaintext passwords |
| **Custom Rules** | ✅ Enterprise | ❌ | ❌ | **Python-only** | User-supplied patterns |
| **Architecture Patterns** | ✅ Enterprise | ❌ | ❌ | **Python-only** | Service, controller detection |
| **Technical Debt** | ✅ Enterprise | ❌ | ❌ | **Python-only** | Effort estimation |
| **API Surface** | ✅ Enterprise | ✅ | ✅ | Best-effort | Public symbols inventory |

### Current Limitation: Not True Polyglot

The tool is **partially polyglot** because:

1. **Advertised-but-missing languages:** Config advertises Go/Rust but MCP implementation routes only Python/JavaScript/TypeScript/Java
2. **Enrichment asymmetry:** Pro/Enterprise tiers are Python-centric; non-Python languages get basic structure extraction only
3. **No unified contract:** No definition of what "code smell" means in Java vs Python; no cross-language complexity equivalence
4. **Language-specific heuristics:** Cognitive complexity, code smells, naming violations use Python AST patterns not portable to other languages

### Requirements for True Polyglot Shape

To achieve polyglot shape, the tool must:

1. **Resolve advertised languages:** Either implement Go/Rust analyzers or remove from documentation
2. **Unify enrichment interface:** Define `LanguageAnalyzer` interface all languages implement:
   ```python
   class LanguageAnalyzer(ABC):
       def extract_structure(self, code: str) -> StructureInfo: ...
       def calculate_cognitive_complexity(self, code: str) -> int: ...
       def detect_code_smells(self, code: str) -> List[CodeSmell]: ...
       def detect_naming_violations(self, code: str) -> List[str]: ...
       def build_dependency_graph(self, code: str) -> Dict[str, List[str]]: ...
   ```
3. **Port enrichments:** Implement language-specific equivalents of cognitive complexity, code smells, dependency graphs, dead code detection
4. **Define equivalence:** Document what enrichments mean per language (e.g., "cognitive complexity" in Python = cyclomatic + nesting in Java)
5. **Tier consistency:** All languages provide same tier-gated enrichments (not Python-only)
6. **Validation:** Unified test suite proving all languages produce comparable outputs

### Polyglot Completion Timeline

- **v1.1 (Q1 2026):** Resolve Go/Rust gap + unify core enrichments for Python/Java/JS/TS
- **v1.2 (Q2 2026):** Add Go, Rust, Ruby support with full enrichment parity
- **v1.3 (Q3 2026):** Performance optimization and polyglot validation
- **Tool is polyglot:** When all 7 languages provide equivalent enrichments at all tiers

---

## Known Gaps for Polyglot Shape

### Gap #1: Advertised But Not Implemented

**Status:** ✅ **RESOLVED** (v1.0 pre-release validation, 2026-01-10)

**Resolution Applied:**
- Removed Go/Rust from `.code-scalpel/limits.toml` Pro tier configuration
- Added explicit language validation in `_analyze_code_sync()` to reject unsupported languages with helpful error message
- Added 5 tests validating language rejection behavior and error messages
- Error message now states: "Unsupported language 'X'. Supported: java, javascript, python, typescript. Roadmap: Go/Rust in Q1 2026."

**Acceptance Criteria:**
- ✅ Routing and documentation agree on supported languages (Python, JavaScript, TypeScript, Java only)
- ✅ No advertised but unimplemented languages in configuration
- ✅ Explicit validation prevents silent fallback with incorrect results
- ✅ Configuration alignment validated by automated tests

### Gap #2: Enrichments Are Python-Only

**Issue:** Cognitive complexity, code smells, halstead metrics, dead code hints, naming violations, compliance checks, custom rules, architecture patterns, and technical debt scoring are **all Python-exclusive**

**Status:** 🟡 MAJOR - Prevents true polyglot shape

**Current State:**
- Python: 17+ enrichments across all tiers
- Java/JS/TS: Basic structure extraction only

**Resolution:** v1.2 (Q2 2026) - Port all enrichments to Java, JavaScript, TypeScript
- Implement language-specific code smell detectors
- Implement language-specific cognitive complexity metrics
- Implement language-specific dead code detection
- Implement language-specific naming convention validators

**Acceptance Criteria:**
- All 4 supported languages have ≥90% of enrichments implemented
- Tier-gating applied consistently across languages
- No enrichments marked as Python-only

### Gap #3: No Unified Contract Across Languages

**Issue:** No definition of "equivalence" for enrichments across languages

**Example:** What does "cognitive complexity = 8" mean in Python vs Java? Are they comparable?

**Status:** 🟡 MAJOR - Prevents meaningful comparison

**Resolution:** v1.1 (Q1 2026) - Document cross-language enrichment equivalence

**Acceptance Criteria:**
- Language-independent definitions for each enrichment metric
- Justification for why metrics are/aren't comparable across languages
- Guidance for users interpreting scores across languages

---

## Current Capabilities (v1.0)

### ✅ Pre-Release Validation Completed (2026-01-10)

**Test Coverage:** 107 tests passing (100% pass rate, 2.56s execution)
- 94 existing tests: Core functionality, edge cases, tiers, limits
- 13 new validation tests: Language validation, output metadata, configuration alignment

**Improvements Applied:**
1. **Language Validation**: Explicit rejection of unsupported languages (Go/Rust) with roadmap guidance
2. **Output Metadata**: Added `language_detected` and `tier_applied` fields for transparency
3. **Configuration Alignment**: Removed advertised-but-not-implemented languages from limits.toml
4. **Error UX**: Clear error messages listing supported languages and roadmap timing

**Validated Behavior:**
- ✅ Multi-language parsing (Python, JavaScript, TypeScript, Java)
- ✅ Tier-based feature gating (Community, Pro, Enterprise)
- ✅ Zero hallucination via real parsers (ast, tree-sitter, dedicated analyzers)
- ✅ Graceful error handling with helpful messages
- ✅ Configuration and implementation alignment

### Community Tier
- Parse Python, JavaScript, TypeScript, Java
- Extract functions and classes
- Extract methods list per class (via class details)
- Import parsing
- Basic complexity scoring (cyclomatic-ish)
- Line count metrics
- Notes:
	- No docstring extraction in the MCP `analyze_code` response.
	- “Issues” are lightweight heuristics (e.g., naming heuristics), not a vulnerability scan.
- Configured limits (see `.code-scalpel/limits.toml`):
	- `max_file_size_mb = 1`
	- `languages = ["python", "javascript", "typescript", "java"]`

### Pro Tier
- All Community features
- Tier-gated enrichments (capability-dependent; some are language-specific):
	- Cognitive complexity (Python)
	- Code smell detection (Python)
	- Halstead metrics (Python)
	- Duplicate code block detection (Python)
	- Dependency graph extraction (Python)
	- Framework detection (as `frameworks`) (Python/Java/JS/TS best-effort)
	- Dead code hints (as `dead_code_hints`) (Python best-effort)
	- Decorator summary (as `decorator_summary`) (Python best-effort)
	- Type/generic usage summary (as `type_summary`) (Python best-effort)
- Configured limits (see `.code-scalpel/limits.toml`):
	- `max_file_size_mb = 10`
	- `languages` includes `go`/`rust` in config, but the MCP `analyze_code` implementation currently only routes `python/javascript/typescript/java`.

### Enterprise Tier

- All Pro features
- Tier-gated enrichments (capability-dependent; some are language-specific):
	- Custom rules (as violations) (Python)
	- Compliance checks (as issues) (Python)
	- Organization pattern heuristics (Python)
	- Naming convention checks (Python)
	- Architecture pattern hints (as `architecture_patterns`) (best-effort)
	- Technical debt scoring summary (as `technical_debt`) (Python best-effort)
	- API surface summary (as `api_surface`) (Python/Java/JS/TS best-effort)
	- Priority ordering marker (as `prioritized`) (best-effort)
	- Complexity trends (as `complexity_trends`, requires `file_path`) (best-effort, in-memory per server process)
- Configured limits (see `.code-scalpel/limits.toml`):
	- `max_file_size_mb = 100`
	- `languages` is “unlimited by omission” in config, but the MCP `analyze_code` implementation currently only routes `python/javascript/typescript/java`.

---
## MCP Request/Response Examples

### MCP Request Format

```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "mcp_code-scalpel_analyze_code",
    "arguments": {
      "code": "def calculate_tax(amount, rate):\n    if rate > 1:\n        rate = rate / 100\n    return amount * rate\n\nclass TaxCalculator:\n    def __init__(self, default_rate=0.1):\n        self.rate = default_rate\n    \n    def compute(self, amount):\n        return calculate_tax(amount, self.rate)",
      "language": "python"
    }
  },
  "id": 1
}
```

### Community Tier Response

```json
{
  "jsonrpc": "2.0",
  "result": {
    "success": true,
    "language": "python",
    "functions": ["calculate_tax"],
    "classes": ["TaxCalculator"],
    "imports": [],
    "complexity": 3,
    "lines_of_code": 9,
    "issues": [],
    "function_details": [
      {"name": "calculate_tax", "lineno": 1, "end_lineno": 4, "is_async": false}
    ],
    "class_details": [
      {"name": "TaxCalculator", "lineno": 6, "end_lineno": 11, "methods": ["__init__", "compute"]}
    ],
    "language_detected": "python",
    "tier_applied": "community"
  },
  "id": 1
}
    "classes": ["TaxCalculator"],
    "imports": [],
    "complexity_score": 2,
    "lines_of_code": 11,
    "has_main": false,
    "issues": [
      {
        "type": "naming",
        "message": "Function 'calculate_tax' uses snake_case (OK)",
        "severity": "info"
      }
    ]
  },
  "id": 1
}
```

### Pro Tier Response

```json
{
  "jsonrpc": "2.0",
  "result": {
    "success": true,
    "language": "python",
    "functions": ["calculate_tax"],
    "classes": ["TaxCalculator"],
    "imports": [],
    "complexity_score": 2,
    "cognitive_complexity": 3,
    "lines_of_code": 11,
    "has_main": false,
    "issues": [],
    "code_smells": [],
    "halstead_metrics": {
      "vocabulary": 12,
      "length": 18,
      "difficulty": 4.5,
      "effort": 81.0
    },
    "duplicate_blocks": [],
    "dependency_graph": {},
    "frameworks": [],
    "dead_code_hints": [],
    "decorator_summary": [],
    "type_summary": {
      "typed_params": 0,
      "untyped_params": 4,
      "return_annotations": 0
    }
  },
  "id": 1
}
```

### Enterprise Tier Response

```json
{
  "jsonrpc": "2.0",
  "result": {
    "success": true,
    "language": "python",
    "functions": ["calculate_tax"],
    "classes": ["TaxCalculator"],
    "imports": [],
    "complexity_score": 2,
    "cognitive_complexity": 3,
    "lines_of_code": 11,
    "has_main": false,
    "issues": [],
    "code_smells": [],
    "halstead_metrics": {
      "vocabulary": 12,
      "length": 18,
      "difficulty": 4.5,
      "effort": 81.0
    },
    "violations": [],
    "architecture_patterns": ["utility-module"],
    "technical_debt": {
      "score": 0.15,
      "category": "low",
      "factors": ["missing_type_hints"]
    },
    "api_surface": {
      "public_functions": ["calculate_tax"],
      "public_classes": ["TaxCalculator"],
      "exported_symbols": 2
    },
    "prioritized": true,
    "complexity_trends": {
      "current": 2,
      "previous": null,
      "trend": "stable"
    }
  },
  "id": 1
}
```

---
## Roadmap

### Cross-Cutting Research Topics

**Research topics (cross-cutting):**
- Evaluation harness: golden fixtures per language, regression scoring, and release gates
- False-positive/false-negative budgets per feature class (smells, dead code hints, patterns)
- Confidence scoring and “best-effort” semantics: when to omit fields vs return partials
- Determinism guarantees: stable outputs across platforms, parser versions, and parallelism
- Security and privacy boundaries: ensure analysis artifacts do not leak source or secrets
- Schema/versioning strategy: adding fields safely, deprecations, and compatibility tests

**Success metrics (cross-cutting):**
- Determinism: identical outputs for the same input across OS/CPU within supported matrix
- Contract stability: backward-compatible schema changes only; automated compatibility checks in CI
- Quality gates: measurable FP/FN budgets per feature category with tracked regressions
- Security hygiene: zero known secret exfiltration paths in generated artifacts; routine scanning in CI

### Q1 2026: Resolve Polyglot Gaps & Enhanced Language Support

#### Blocker Items (Must Complete First)
- [ ] **POLYGLOT GAP #1:** Reconcile `.code-scalpel/limits.toml` language lists with MCP routing
  - **Acceptance:** Routing and docs agree on supported languages (remove Go/Rust or implement)
  - **Effort:** 3 hours
  - **Blocker:** Must resolve before adding new languages

#### Community Tier
- [ ] Add Rust AST parsing support (only if Gap #1 resolution includes Rust)
- [ ] Add PHP AST parsing support
- [ ] Improve TypeScript generic handling
- [ ] Enhanced error messages for parsing failures

**Research topics (Q1 / Community):**
- Rust parsing options tradeoffs (tree-sitter-rust vs rust-analyzer AST vs `syn`-based parsing)
- PHP parsing options (tree-sitter-php vs nikic/php-parser) and error recovery behavior
- TypeScript generic/type extraction quality using the TypeScript compiler API vs tree-sitter heuristics
- Parser error UX: actionable diagnostics, snippet localization, and recovery strategies

**Success metrics (Q1 / Community):**
- New languages: function/class extraction accuracy meets or exceeds existing Community baselines
- Error UX: parse failures include actionable reason + localized span for the majority of failures
- Limits alignment: config and routing agree (no "advertised but unsupported" languages)

### Q2 2026: Polyglot Enrichment Parity & Performance

#### Polyglot Enrichment Porting (BLOCKING for true polyglot shape)
- [ ] **Port cognitive complexity** to Java, JavaScript, TypeScript
  - Implement language-appropriate complexity metrics
  - Validate against reference implementations
  - Test on representative codebases
  - **Effort:** 20 hours per language (60 hours total)

- [ ] **Port code smell detection** to Java, JavaScript, TypeScript
  - Map Python smells to language-specific patterns
  - Implement language naming convention validators
  - Long method/function detection per language
  - God class/module detection per language
  - **Effort:** 16 hours per language (48 hours total)

- [ ] **Port dead code detection** to Java, JavaScript, TypeScript
  - Unused import/variable detection per language
  - Unreachable code detection per language
  - **Effort:** 12 hours per language (36 hours total)

- [ ] **Port dependency graph building** to Java, JavaScript, TypeScript
  - Function/method call graph per language
  - Cross-file dependency tracking
  - **Effort:** 14 hours per language (42 hours total)

**Total Polyglot Porting Effort:** ~186 hours

**Success Criteria:**
- All 4 supported languages provide ≥15 enrichments
- Enrichment outputs are tier-gated identically across languages
- No enrichments marked as "Python-only"
- Test coverage ≥95% for all language-specific implementations

#### Pro Tier
- [ ] Add Swift AST parsing
- [ ] Add Kotlin AST parsing
- [ ] Cross-language dependency tracking
- [ ] Semantic code search within analysis

**Research topics (Q2 / Pro):**
- “Good enough” dependency graphs across languages: import graphs vs symbol graphs vs call graphs
- Multi-language symbol resolution strategies (LSP-backed vs static heuristics)
- Semantic search quality metrics (precision/recall, hallucination avoidance) and privacy constraints
- Duplicate-code detection beyond Python (token-based vs AST-based, normalization strategies)

**Success metrics (Q1 / Pro):**
- Dependency tracking: stable graphs on representative repos with bounded false edges
- Semantic search: measured precision/recall targets on a curated benchmark; no source invention
- Duplicate detection: configurable threshold with acceptable false-positive rates on real-world code

#### Enterprise Tier
- [ ] Custom language grammar support
- [ ] Multi-file analysis orchestration
- [ ] Architecture diagram generation
- [ ] Automated refactoring suggestions

**Research topics (Q1 / Enterprise):**
- User-supplied grammar safety model and sandboxing (tree-sitter grammar ingestion risks)
- Multi-file orchestration: incremental dependency ordering, partial failures, and caching boundaries
- Architecture diagram extraction approaches (C4-ish hints, package boundaries, dependency slicing)
- Refactoring suggestion safety: behavior-preservation checks and confidence scoring

**Success metrics (Q1 / Enterprise):**
- Orchestration: multi-file analysis completes under defined time/memory budgets on large repos
- Diagram generation: produces usable, stable diagrams for a curated set of architectures
- Refactoring suggestions: includes confidence + safety checks; low regression rate in evaluation suite

### Q2 2026: Performance & Scalability

#### All Tiers
- [ ] Incremental analysis (only re-analyze changed code)
- [ ] Parallel file processing
- [ ] Memory optimization for large files
- [ ] Streaming analysis for huge codebases

**Research topics (Q2 / All):**
- Incremental parsing primitives per language (AST diffing vs reparse-on-change)
- Deterministic parallelism (stable outputs across worker counts)
- Memory profiles per parser (tree-sitter vs language-native parsers) and mitigation tactics
- Streaming outputs contract (partial result schemas, progress reporting, backpressure)

**Success metrics (Q2 / All):**
- Incremental: re-analysis time scales with changed regions, not full file size
- Parallel: throughput improves with cores while preserving deterministic results
- Memory: bounded peak memory usage for large files within defined envelopes
- Streaming: partial outputs are schema-valid and order-stable under backpressure

#### Pro Tier
- [ ] Distributed analysis across worker nodes
- [ ] Smart caching with invalidation
- [ ] Delta analysis (compare versions)

**Research topics (Q2 / Pro):**
- Cache invalidation keys (file content hash vs semantic hash) and correctness pitfalls
- Delta analysis UX: presenting diffs in a stable, low-noise way
- Cost model for distributed analysis (fan-out, queueing, shard boundaries)

**Success metrics (Q2 / Pro):**
- Caching: correctness-preserving invalidation (no stale results in benchmark suite)
- Delta: low-noise diff output with stable ordering and minimal churn between runs
- Distributed: predictable scaling with observability (queue time, worker utilization)

#### Enterprise Tier
- [ ] Cluster-based analysis
- [ ] Real-time analysis streaming
- [ ] Historical trend analysis
- [ ] Predictive analysis ("this will likely cause issues")

**Research topics (Q2 / Enterprise):**
- Persistence model for historical trends (in-memory vs durable store; retention/aggregation)
- Real-time streaming transport choices and failure semantics
- “Predictive analysis” framing and calibration (avoid overconfident outputs; measure accuracy)

**Success metrics (Q2 / Enterprise):**
- Trends: durable, queryable history with clear retention/aggregation policies
- Streaming: defined delivery guarantees and graceful degradation under failures
- Predictive: calibrated confidence; tracked precision/recall against post-merge outcomes

### Q3 2026: AI-Enhanced Analysis

#### Pro Tier
- [ ] ML-based code smell detection
- [ ] Intelligent complexity prediction
- [ ] Automated documentation generation
- [ ] Code pattern mining

**Research topics (Q3 / Pro):**
- Ground truth for “code smells”: labeling strategy and inter-rater reliability
- Complexity prediction evaluation (baseline heuristics vs learned models)
- Documentation generation constraints (non-executing, no invented APIs, source-grounded)
- Pattern mining: clustering methods and how to avoid leaking sensitive code in artifacts

**Success metrics (Q3 / Pro):**
- Smells: measurable reduction in high-severity false positives vs heuristic baselines
- Complexity prediction: outperforms baseline on held-out benchmark; calibrated uncertainty
- Docs: source-grounded outputs with quality rubric and low hallucination rate
- Pattern mining: produces stable clusters with clear utility and privacy guarantees

#### Enterprise Tier
- [ ] Custom ML model training on org codebase
- [ ] Anomaly detection ("this doesn't match your patterns")
- [ ] Security vulnerability prediction
- [ ] Technical debt forecasting

**Research topics (Q3 / Enterprise):**
- Org-trained models: data governance, opt-in boundaries, and reproducibility
- Anomaly detection: defining “normal” per repo/team and reducing false positives
- Vulnerability prediction: positioning vs deterministic scanners; validation and disclaimers
- Debt forecasting: what signals matter (churn, complexity trends, ownership) and how to calibrate

**Success metrics (Q3 / Enterprise):**
- Org training: reproducible builds with clear data lineage and opt-out controls
- Anomaly detection: false-positive rate within defined budgets per repo/team
- Vulnerability prediction: measured lift over baseline heuristics; conservative confidence
- Debt forecasting: correlates with later remediation effort; clear uncertainty bounds

### Q4 2026: Integration & Automation

#### Community Tier
- [ ] GitHub Action integration
- [ ] GitLab CI integration
- [ ] Pre-commit hook support

**Research topics (Q4 / Community):**
- Minimal CI contract (inputs/outputs) that works across providers
- Pre-commit ergonomics: speed budgets, caching, and “changed files only” operation

**Success metrics (Q4 / Community):**
- CI: drop-in setup with predictable exit codes and machine-readable outputs
- Pre-commit: completes within agreed latency budgets on typical changed-file sets

#### Pro Tier
- [ ] IDE plugin (VSCode, IntelliJ)
- [ ] Slack/Teams notifications
- [ ] Jira integration for technical debt tracking
- [ ] SonarQube export compatibility

**Research topics (Q4 / Pro):**
- IDE integration surface: LSP vs direct extension APIs; latency and offline behavior
- Notifications: deduping, routing, and severity mapping to avoid alert fatigue
- Interop formats: SARIF vs Sonar formats vs custom JSON; compatibility testing

**Success metrics (Q4 / Pro):**
- IDE: interactive latency within defined bounds; resilient offline behavior
- Notifications: low duplicate alert rate; configurable routing by severity/category
- Exports: validated compatibility with at least one reference pipeline per target format

#### Enterprise Tier
- [ ] ServiceNow integration
- [ ] Custom webhook support
- [ ] SSO/SAML authentication
- [ ] Audit log streaming to SIEM

**Research topics (Q4 / Enterprise):**
- Audit log schema and integrity (tamper evidence, correlation IDs)
- SIEM export formats and volume control (sampling/aggregation)
- Auth boundary decisions (tool server vs platform identity) and deployment patterns

**Success metrics (Q4 / Enterprise):**
- Audit logs: complete, tamper-evident records with correlation across tool invocations
- SIEM: controlled volume with clear severity mapping and reliable delivery
- Auth: supports common enterprise deployment patterns with least-privilege defaults

---

## Known Issues & Limitations

### Current Limitations
- **Large files:** Files >10MB may experience performance degradation
- **Obfuscated code:** Cannot analyze minified/obfuscated JavaScript
- **Macros:** C/C++ macro expansion not yet supported
- **Dynamic imports:** Runtime-only imports may not be detected

### Planned Fixes
- Q1 2026: Large file chunking strategy
- Q2 2026: Partial obfuscation handling
- Q3 2026: Macro expansion support
- Q4 2026: Dynamic import inference

---

## Success Metrics

### Performance Targets
- **Parse time:** <100ms for files <1000 LOC
- **Memory usage:** <50MB per 10,000 LOC analyzed
- **Accuracy:** >98% correct function/class extraction
- **Coverage:** Support 15+ languages by EOY 2026

### Adoption Metrics
- **Usage:** 1M+ API calls per month by Q4 2026
- **Satisfaction:** >4.5/5 average rating
- **Retention:** >85% monthly active users

---

## Dependencies

### Internal Dependencies
- `code_parsers/` - Language-specific parsers
- `ast_tools/analyzer.py` - Core AST analysis
- `cache/unified_cache.py` - Result caching
- `licensing/` - Tier enforcement

### External Dependencies
- `tree-sitter` - Polyglot parsing
- Language-specific parsers (varies by language)

---

## Breaking Changes

None planned. Committed to backward compatibility.

**API Stability Promise:** 
- Tool signature stable through 2026
- New fields may be added (non-breaking)
- Deprecated fields marked 6 months before removal

---

**Last Updated:** December 30, 2025  
**Next Review:** March 31, 2026