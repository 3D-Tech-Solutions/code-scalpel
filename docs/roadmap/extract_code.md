# extract_code Tool Roadmap

**Tool Name:** `extract_code`  
**Tool Version:** v1.0  
**Code Scalpel Version:** v3.3.0  
**Current Status:** Stable  
**Primary Module:** `src/code_scalpel/surgery/surgical_extractor.py`  
**Tier Availability:** All tiers (Community, Pro, Enterprise)

---

## Overview

The `extract_code` tool surgically extracts specific code elements (functions, classes, methods) by name.

It is designed to:
- Eliminate line-number guessing (exact symbol boundaries)
- Minimize token usage (server-side file reads)
- Provide actionable context (intra-file context + tier-limited cross-file dependencies)
- Work across languages (Python + polyglot parsing for JS/TS/Java)

---

## Polyglot Architecture Definition

**Current Status:** Partially polyglot (Python full, JS/TS/Java single-symbol; cross-file deps Python-only)

### Language Support Matrix

| Language | Community | Pro | Enterprise | Cross-File Deps | Implementation | Status |
|----------|-----------|-----|------------|-----------------|----------------|--------|
| Python | ✅ Full | ✅ Full | ✅ Full | ✅ Depth-limited | surgical_extractor | ✅ Stable |
| JavaScript | ✅ Single symbol | ✅ React metadata | ✅ React metadata | ❌ | tree-sitter + unified_extractor | ⚠️ Limited (no deps) |
| TypeScript | ✅ Single symbol | ✅ React metadata | ✅ React metadata | ❌ | tree-sitter + unified_extractor | ⚠️ Limited (no deps) |
| Java | ✅ Single symbol | ✅ Single symbol | ✅ Single symbol | ❌ | tree-sitter + unified_extractor | ⚠️ Limited (no deps) |
| Go | ❌ Not implemented | ❌ | ❌ | ❌ | N/A | 🔴 Missing |
| Rust | ❌ Not implemented | ❌ | ❌ | ❌ | N/A | 🔴 Missing |
| PHP | ❌ Not implemented | ❌ | ❌ | ❌ | N/A | 🔴 Missing |
| Ruby | ❌ Not implemented | ❌ | ❌ | ❌ | N/A | 🔴 Missing |
| Kotlin | ❌ Not implemented | ❌ | ❌ | ❌ | N/A | 🔴 Missing |

### Capability Gaps

- Cross-file dependency extraction exists **only for Python** (Pro/Enterprise); all other languages stop at single-symbol extraction
- Confidence scoring and depth clamping apply only to Python dependency paths
- React metadata exists for JS/TS but is not paired with cross-file deps
- No unified equivalence contract for dependency representation across languages

### Requirements for True Polyglot Shape

1. Implement language-specific dependency resolvers (JS/TS, Java first; then Go/Rust/PHP/Ruby/Kotlin)
2. Unify dependency schema and confidence semantics across languages
3. Support tier-gated depth clamping for all languages
4. Add cross-file tests per language with ≥95% accuracy on representative repos
5. Keep API contract stable (single entry point, same response fields) across languages

### Polyglot Completion Timeline

- **v1.1 (Q1 2026):** JS/TS + Java cross-file dependency resolution + unified schema
- **v1.2 (Q2 2026):** Add Rust/Go/PHP single-symbol extraction; add JS/TS/Java dependency accuracy hardening
- **v1.3 (Q3 2026):** Ruby/Kotlin extraction + dependency decoders; performance tuning
- **v1.4 (Q4 2026):** Polyglot validation (accuracy + perf) and confidence calibration across languages


## Current Capabilities (v1.0)

### Community Tier
- ✅ Extract functions by name
- ✅ Extract classes by name
- ✅ Extract methods from classes
- ✅ Intra-file context extraction (Python, optional via `include_context`)
- ✅ Multi-language single-symbol extraction (Python, JavaScript, TypeScript, Java)
- ⚠️ **Limits:** Cross-file dependency resolution is disabled; max dependency depth is clamped to tier limits

### Pro Tier
- ✅ All Community features
- ✅ Cross-file dependency extraction (Python only)
- ✅ Tier-limited recursion depth for dependencies (default: direct dependencies)
- ✅ Confidence scoring metadata for cross-file dependencies
- ✅ React component extraction metadata (JSX/TSX) for TypeScript/JavaScript symbols
- ✅ Decorator/annotation preservation
- ✅ Type hint preservation

### Enterprise Tier
- ✅ All Pro features
- ✅ Organization-wide resolution (monorepo / multi-repo workspace analysis)
- ✅ Custom extraction patterns (regex/import/function-call)
- ✅ Service boundary detection
- ✅ Function-to-microservice packaging (Dockerfile + API spec) via advanced options
- ⚠️ **Note:** Audit logging, policy-only extraction, and extract-and-analyze “pipelines” are roadmap items unless explicitly implemented as separate MCP tools

### Tier Contract Notes (v1.0)
- **Depth enforcement:** `context_depth` is clamped to each tier’s `max_depth` when `include_context` or `include_cross_file_deps` is enabled.
- **Cross-file scope:** Cross-file dependencies are currently implemented for **Python**; non-Python extraction uses the polyglot path and returns the extracted symbol + metadata, but does not resolve cross-file dependencies.
- **Confidence semantics:** Each external dependency is annotated with `(depth, confidence)`, where confidence decays with depth.

---
## MCP Request/Response Examples

### MCP Request Format

```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "mcp_code-scalpel_extract_code",
    "arguments": {
      "file_path": "/home/user/project/src/utils.py",
      "target_type": "function",
      "target_name": "calculate_tax",
      "include_context": true
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
    "symbol_name": "calculate_tax",
    "symbol_type": "function",
    "file_path": "/home/user/project/src/utils.py",
    "code": "def calculate_tax(amount: float, rate: float = 0.1) -> float:\n    \"\"\"Calculate tax for a given amount.\"\"\"\n    if rate > 1:\n        rate = rate / 100\n    return amount * rate",
    "start_line": 15,
    "end_line": 20,
    "language": "python",
    "context": {
      "imports": ["from decimal import Decimal"],
      "preceding_code": "# Tax calculation utilities\n",
      "following_code": "\n\ndef format_currency(amount):\n    ..."
    },
    "decorators": [],
    "docstring": "Calculate tax for a given amount.",
    "cross_file_deps": [],
    "cross_file_deps_note": "Cross-file dependency resolution disabled for Community tier"
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
    "symbol_name": "calculate_tax",
    "symbol_type": "function",
    "file_path": "/home/user/project/src/utils.py",
    "code": "def calculate_tax(amount: float, rate: float = 0.1) -> float:\n    \"\"\"Calculate tax for a given amount.\"\"\"\n    if rate > 1:\n        rate = rate / 100\n    return amount * rate",
    "start_line": 15,
    "end_line": 20,
    "language": "python",
    "context": {
      "imports": ["from decimal import Decimal", "from .config import DEFAULT_TAX_RATE"],
      "preceding_code": "# Tax calculation utilities\n",
      "following_code": "\n\ndef format_currency(amount):\n    ..."
    },
    "decorators": [],
    "docstring": "Calculate tax for a given amount.",
    "type_hints": {
      "params": {"amount": "float", "rate": "float"},
      "return": "float"
    },
    "cross_file_deps": [
      {
        "symbol": "DEFAULT_TAX_RATE",
        "source_file": "/home/user/project/src/config.py",
        "depth": 1,
        "confidence": 0.9,
        "code": "DEFAULT_TAX_RATE = 0.1"
      }
    ],
    "react_metadata": null
  },
  "id": 1
}
```

### Pro Tier Response (React/TSX)

```json
{
  "jsonrpc": "2.0",
  "result": {
    "success": true,
    "symbol_name": "TaxCalculator",
    "symbol_type": "function",
    "file_path": "/home/user/project/src/components/TaxCalculator.tsx",
    "code": "export function TaxCalculator({ rate }: Props) {\n  const [amount, setAmount] = useState(0);\n  const tax = calculateTax(amount, rate);\n  return <div className=\"calculator\">...</div>;\n}",
    "start_line": 10,
    "end_line": 25,
    "language": "tsx",
    "decorators": [],
    "react_metadata": {
      "component_type": "functional",
      "is_server_component": false,
      "has_server_action": false,
      "hooks_used": ["useState"],
      "props_interface": "Props"
    },
    "cross_file_deps": [
      {
        "symbol": "calculateTax",
        "source_file": "/home/user/project/src/utils/tax.ts",
        "depth": 1,
        "confidence": 0.9
      }
    ]
  },
  "id": 1
}
```

### Enterprise Tier Response


## Known Gaps for Polyglot Shape

### Gap #1: Cross-File Dependencies Python-Only
**Issue:** Dependency extraction + confidence scoring exist only for Python. JS/TS/Java return single-symbol without deps.

**Status:** 🔴 BLOCKING polyglot shape

**Resolution Target:** v1.1 (Q1 2026) — Add JS/TS/Java dependency resolvers with unified schema

**Acceptance Criteria:**
- JS/TS/Java support `cross_file_deps` with depth + confidence
- Tier clamping enforced for all languages
- ≥90% correctness on benchmark repos

### Gap #2: Missing Language Implementations (Go/Rust/PHP/Ruby/Kotlin)
**Issue:** Languages listed in roadmap have no extraction implementation.

**Status:** 🟡 MAJOR

**Resolution Target:** v1.2 (Q2 2026) — Add single-symbol extraction for Go/Rust/PHP; plan Ruby/Kotlin for v1.3

**Acceptance Criteria:**
- ≥95% single-symbol extraction success on curated corpus per new language
- Median extraction latency <200ms for files <1k LOC

### Gap #3: No Cross-Language Dependency Equivalence
**Issue:** Dependency payload shape and confidence semantics are not defined for non-Python languages.

**Status:** 🟡 MAJOR

**Resolution Target:** v1.1 (Q1 2026)

**Acceptance Criteria:**
- Documented schema for `cross_file_deps` across languages
- Confidence decay model applied consistently
- Tests covering multi-language dependency cases

### Gap #4: React Metadata Without Dependency Context
**Issue:** React metadata exists for JS/TS but is not linked to cross-file deps.

**Status:** 🟠 MINOR (dependent on Gap #1)

**Resolution Target:** v1.2 (Q2 2026)

**Acceptance Criteria:**
- React components include cross-file deps for hooks/utilities
- Metadata and deps share consistent confidence scoring

---

## Roadmap

### Polyglot Blockers (Must Complete First)
- [ ] **Gap #1:** Add JS/TS/Java cross-file dependency resolution with depth + confidence (target v1.1)
- [ ] **Gap #3:** Define unified `cross_file_deps` schema and confidence semantics across languages (target v1.1)
```json
  "result": {
    "success": true,
    "symbol_name": "calculate_tax",
    "symbol_type": "function",
    "file_path": "/home/user/project/src/utils.py",
    "code": "def calculate_tax(amount: float, rate: float = 0.1) -> float:\n    \"\"\"Calculate tax for a given amount.\"\"\"\n    if rate > 1:\n        rate = rate / 100\n    return amount * rate",
    "start_line": 15,
    "end_line": 20,
    "language": "python",
    "context": {
      "imports": ["from decimal import Decimal", "from .config import DEFAULT_TAX_RATE"],
      "preceding_code": "# Tax calculation utilities\n",
      "following_code": "\n\ndef format_currency(amount):\n    ..."
    },
    "decorators": [],
    "docstring": "Calculate tax for a given amount.",
    "type_hints": {
      "params": {"amount": "float", "rate": "float"},
      "return": "float"
    },
    "cross_file_deps": [
      {
        "symbol": "DEFAULT_TAX_RATE",
        "source_file": "/home/user/project/src/config.py",
        "depth": 1,
        "confidence": 0.9,
        "code": "DEFAULT_TAX_RATE = 0.1"
      },
      {
        "symbol": "TaxConfig",
        "source_file": "/home/user/project/src/config.py",
        "depth": 2,
        "confidence": 0.81,
        "code": "class TaxConfig:\n    ..."
      }
    ],
    "organization_context": {
      "module_owner": "@tax-team",
      "service_boundary": "billing-service",
      "api_visibility": "internal"
    },
    "custom_extraction_patterns": [],
    "packaging_hints": {
      "dockerfile_ready": true,
      "standalone_capable": true,
      "external_deps": ["decimal"]
    }
  },
  "id": 1
}
```

---
## Roadmap

## Cross-Cutting Research Topics (applies across v1.1–v1.4)

### RQ1 — Symbol Boundary Accuracy
- How often does extraction return the *exact* intended symbol (decorators, docstrings, nested defs, overloads)?
- What are the top failure modes by language and symbol type?

### RQ2 — Dependency Relevance vs. Token Budget
- Which dependency selection strategies maximize “useful context per token”?
- Can we automatically cap context while preserving compilation/runtime correctness?

### RQ3 — Import & Module Resolution Correctness
- Which import styles cause the most misses (relative imports, re-exports, star imports, namespace packages)?
- How do we detect and annotate unresolved imports without hallucinating?

### RQ4 — Confidence Scoring Calibration
- Does a depth-based decay model correlate with actual correctness?
- What threshold(s) best predict “safe to trust” vs. “needs verification”?

### RQ5 — Tier-Limited Behavior UX
- Do users understand clamping/truncation warnings without upsell messaging?
- What wording reduces confusion while preserving security and tier constraints?

### v1.1 (Q1 2026): Enhanced Dependency Resolution

#### Community Tier
- [ ] Improved error messages for missing symbols (include suggestions: closest matches, available symbols)
- [ ] Support for nested class extraction (Python)
- [ ] Basic circular dependency detection (intra-file)

**Community Research Queries**
- What missing-symbol error phrasing leads to faster user recovery?
- Which nested-class naming conventions are most common in the wild?

**Community Success Metrics**
- <1% of failures are “unknown error” (actionable error text coverage)
- ≥80% of missing-symbol failures include a useful suggestion (closest symbol or available list)

#### Pro Tier
- [ ] Smart dependency ordering (imports → types/classes → helpers → target)
- [ ] Conditional import handling (`TYPE_CHECKING`, platform guards)
- [ ] Cross-file resolution: stronger re-export following + alias handling
- [ ] Optional: include test-only dependencies (opt-in, bounded)
- [ ] **Deliver JS/TS/Java cross-file dependency resolution** with depth + confidence (addresses Gap #1)

**Pro Research Queries**
- Does dependency ordering measurably improve downstream LLM task success?
- What heuristics best identify “type-only” vs runtime dependencies?

**Pro Success Metrics**
- ≥10% reduction in “missing name/import” errors in downstream LLM outputs (A/B)
- ≥95% correct ordering for common patterns (measured on a curated corpus)

#### Enterprise Tier
- [ ] Dependency graph visualization output (Mermaid)
- [ ] Custom dependency filters (deny/allow modules, stdlib-only, etc.)
- [ ] Extraction templates (preset bundles for security review, refactor, docs)

**Enterprise Research Queries**
- Which graph views are most actionable: call graph, import graph, or mixed?
- What template bundles are repeatedly requested by real users?

**Enterprise Success Metrics**
- ≥90% of enterprise extractions can optionally emit a valid Mermaid graph
- ≥3 reusable templates adopted across multiple repos

### v1.2 (Q2 2026): Language Expansion

#### All Tiers
- [ ] Rust function extraction (single-symbol)
- [ ] Go function extraction (single-symbol)
- [ ] PHP function extraction (single-symbol)
- [ ] Harden JS/TS/Java cross-file dependency accuracy (precision/recall targets)

**All-Tiers Research Queries**
- Which parsing backend yields best stability/latency per language (tree-sitter vs native parsers)?
- What minimal feature set is “v1 useful” per language (functions only vs methods/classes)?

**All-Tiers Success Metrics**
- ≥95% extraction success on a representative OSS corpus per new language
- <200ms median extraction time for single symbol on typical files (<1k LOC)

#### Pro Tier
- [ ] Ruby method extraction
- [ ] Kotlin function extraction

**Pro Research Queries**
- How should we map language-specific method resolution semantics into a unified API?
- What naming conventions (e.g., receiver types) reduce ambiguity for method targeting?

**Pro Success Metrics**
- ≥98% correct method extraction for canonical patterns in Ruby/Kotlin test suite

### v1.3 (Q3 2026): Performance Optimization

#### All Tiers
- [ ] Parallel extraction for batch operations
- [ ] Streaming extraction for large symbols
- [ ] Memory optimization

**All-Tiers Research Queries**
- What are safe cut points for streaming symbol output while preserving syntax?
- Which caches provide wins without returning stale code after edits?

**All-Tiers Success Metrics**
- ≥2× throughput improvement for batch extraction (same hardware)
- <1% stale extraction results under file-edit churn (measured via integration tests)

#### Pro Tier
- [ ] Incremental extraction (delta mode)
- [ ] Smart caching with invalidation

**Pro Research Queries**
- Which invalidation signals are reliable across editors/CI (mtime, hash, git index)?
- How do we persist caches safely across sessions without leaking source?

**Pro Success Metrics**
- ≥50% latency reduction on repeated extractions in the same repo session

#### Enterprise Tier
- [ ] Distributed extraction across workers
- [ ] Real-time extraction monitoring

**Enterprise Research Queries**
- What work partitioning yields best cost/performance: by file, by symbol, by language?
- What telemetry is most useful without collecting sensitive source?

**Enterprise Success Metrics**
- Linear-ish scaling to N workers on large monorepos (≥0.8×N speedup)
- Monitoring dashboard shows p50/p95 latency and error taxonomy

### v1.4 (Q4 2026): Advanced Features

#### Pro Tier
- [ ] Extract with related documentation
- [ ] Extract with usage examples
- [ ] Extract with test coverage info

**Pro Research Queries**
- Which usage examples are most useful: call sites, integration tests, or docs?
- Can we rank examples by relevance (closest call graph distance, most recent change)?

**Pro Success Metrics**
- ≥80% of returned examples are judged “useful” in blinded human review

#### Enterprise Tier
- [ ] Extract with security context
- [ ] Extract with compliance metadata
- [ ] Custom post-extraction hooks

**Enterprise Research Queries**
- Which security contexts reduce vuln-introducing refactors (taint sources/sinks, auth boundaries)?
- What minimal compliance metadata is actionable (PII zones, retention tags, audit trails)?

**Enterprise Success Metrics**
- ≥25% reduction in policy-violating suggestions in extract→refactor workflows
- Hooks API adopted in ≥3 internal integrations

---

## Known Issues & Limitations

### Current Limitations
- **Dynamic symbols:** Cannot extract dynamically generated functions
- **Complex generics:** Some complex TypeScript generics may not preserve fully
- **Cross-file deps (polyglot):** Cross-file dependency resolution is currently Python-only
- **Macro-generated code:** Future C/C++ support will need macro strategy

### Planned Fixes
- v1.1: Improved generic handling
- v1.2: Partial macro support
- v1.3: Dynamic symbol inference (best effort)

---

## Success Metrics

### Performance Targets
- **Extraction time:** <50ms for single symbol
- **Accuracy:** >99% correct symbol extraction
- **Dependency resolution:** >95% accuracy

### Reliability Targets
- **Tier clamp correctness:** 100% of requests honor configured `max_depth` (unit tests + fuzz)
- **Confidence calibration:** ≥0.7 AUC for predicting correct dependency resolution (benchmark set)

### Adoption Metrics
- **Usage:** 500K+ extractions per month by Q4 2026
- **Error rate:** <1% failed extractions

---

## Dependencies

### Internal Dependencies
- `src/code_scalpel/surgery/surgical_extractor.py` - Python extraction + cross-file dependency resolution
- `src/code_scalpel/surgery/unified_extractor.py` - Polyglot extraction (JS/TS/Java) + JSX/TSX metadata
- `src/code_scalpel/mcp/server.py` - MCP tool wrapper + tier enforcement
- `src/code_scalpel/licensing/features.py` - Tier capability matrix (limits + capabilities)
- `src/code_scalpel/mcp/path_resolver.py` - Secure/robust path resolution

### External Dependencies
- `tree-sitter` (where applicable) - polyglot parsing backend
- Language-specific parsers (as needed per language roadmap)

---

## Breaking Changes

None planned for v1.x series.

**API Stability Promise:**
- Tool signature stable through v1.x
- Return format backward compatible
- New optional parameters only

---

## v1.0 Validation Status

**Validated:** January 11, 2026  
**Validator:** GitHub Copilot Agent  
**Test Suite:** `tests/tools/extract_code/` - **126 tests passing**

### Improvements Made

| Change | Type | Description |
|--------|------|-------------|
| Community max_depth fix | BUGFIX | Fixed limits.toml Community max_depth (was 1, now 0 to match features.py) |
| Output metadata fields | FEATURE | Added tier_applied, language_detected, cross_file_deps_enabled, max_depth_applied to ContextualExtractionResult |
| Metadata test suite | TEST | Added test_output_metadata.py with 7 validation tests |

### Test Breakdown

| Test File | Tests | Coverage |
|-----------|-------|----------|
| test_language_support.py | 13 | Python, JS, TS, Java |
| test_edge_cases.py | 14 | Decorators, async, nested, inherited |
| test_line_numbers.py | 10 | start_line/end_line accuracy |
| test_pro_enterprise_features.py | 17 | Pro (6), Enterprise (5), Gating (3), License (2) |
| test_resolve_organization_wide.py | 42+ | Org-wide resolution (Enterprise) |
| test_detect_service_boundaries.py | varies | Service boundary detection |
| test_extract_with_custom_pattern.py | varies | Custom extraction patterns |
| test_output_metadata.py | 7 | NEW: Metadata field validation |
| **TOTAL** | **126** | ✅ All passing |

### Configuration Verified

- **limits.toml**: Community max_depth=0, Pro max_depth=1, Enterprise unlimited
- **features.py**: Capabilities matrix aligned with limits.toml
- **Output metadata**: All extraction returns include tier/language/config transparency

---

**Last Updated:** January 11, 2026  
**Next Review:** March 31, 2026
