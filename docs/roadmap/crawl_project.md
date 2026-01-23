# crawl_project Tool Roadmap

**Tool Name:** `crawl_project`  
**Tool Version:** v1.0  
**Code Scalpel Version:** v3.3.0  
**Current Status:** Stable ✅ Pre-release validated  
**Primary Module:** `src/code_scalpel/analysis/project_crawler.py`  
**Tier Availability:** All tiers (Community, Pro, Enterprise)  
**Test Coverage:** 76 tests passing (60 baseline + 16 v1.0 validation)

---

## v1.0 Pre-Release Validation (2026-01-06)

### Issues Identified and Resolved

**Gap #1: limits.toml vs features.py Pro tier mismatch** ✅ RESOLVED
- **Problem:** limits.toml had `max_files = 1000` for Pro tier while features.py defined `max_files = None` (unlimited)
- **Fix:** Removed hardcoded limit from limits.toml to match features.py (Pro tier now unlimited)
- **File:** `.code-scalpel/limits.toml` line 94

### Output Transparency Improvements

**New metadata fields added to `ProjectCrawlResult`:**
- `tier_applied`: Which tier's rules were used ("community"/"pro"/"enterprise")
- `crawl_mode`: Which crawl mode was used ("discovery" for Community, "deep" for Pro/Enterprise)
- `files_limit_applied`: Max files limit applied (None = unlimited, integer = capped)

### Test Suite Expansion
- **New tests:** `tests/tools/crawl_project/test_v1_0_improvements.py` (16 tests)
  - TestOutputMetadata: Validates metadata fields are populated correctly per tier
  - TestConfigAlignment: Ensures limits.toml and features.py stay in sync
  - TestCrawlModeCapabilities: Validates discovery vs deep mode behaviors
  - TestModelSchema: Validates schema changes are backward compatible

---

## Overview

The `crawl_project` tool analyzes entire project directories, providing structure, complexity, and (Enterprise) compliance-oriented signals.

Notes on how v1.0 works:
- **Python files** get AST-based structure extraction (functions/classes/imports) and cyclomatic-ish complexity.
- **JavaScript/TypeScript/Java** currently get **lightweight heuristic** imports + basic complexity estimates (deterministic and fast).
- The returned schema is backward compatible; extra tier-gated fields are added using `extra="allow"`.

---

## Current Capabilities (v1.0)

### Community Tier
- ✅ Project-wide file scanning
- ✅ Language detection
- ✅ Basic complexity metrics
- ✅ File count and LOC statistics
- ✅ Supports Python, JavaScript/JSX, TypeScript/TSX, Java
- ⚠️ **Limits:** Max 100 files analyzed

**Output highlights (Community):**
- `files[*].language` and `files[*].complexity_score`
- `language_breakdown` (counts by detected language)

### Pro Tier
- ✅ All Community features (unlimited files)
- ✅ Parallel file processing
- ✅ Incremental crawling (cache results)
- ✅ Framework detection
- ✅ Dependency mapping
- ✅ Code hotspot identification

**Implementation notes (Pro):**
- Parallelism uses a thread pool (deterministic output ordering).
- Incremental crawling stores reusable file results in `.scalpel_cache/crawl_cache_v1.json`.
- Dependency mapping is exposed as `dependency_graph` (file -> imports list).

### Enterprise Tier
- ✅ All Pro features
- ✅ Distributed crawling
- ✅ Repository-wide analysis (single-root crawl; monorepo signals included when detected)
- ✅ Historical trend analysis
- ✅ Custom crawl rules
- ✅ Compliance scanning

**Implementation notes (Enterprise):**
- “Distributed” is process-based parallelism on the local machine (uses `spawn` for safety).
- Historical trend analysis persists simple run summaries to `.scalpel_cache/crawl_history.jsonl`.
- Custom crawl rules (best-effort) can be provided via `.code-scalpel/crawl_project.json`:
	- `include_extensions`: list of file extensions (e.g., `[".py", ".ts"]`)
	- `exclude_dirs`: list of directory names to exclude
- Compliance scanning is best-effort and currently targets analyzed Python files via `code_policy_check` engine; returned as `compliance_summary`.

---
## MCP Request/Response Examples

### MCP Request Format

```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "mcp_code-scalpel_crawl_project",
    "arguments": {
      "root_path": "/home/user/my-project",
      "complexity_threshold": 10,
      "include_report": true
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
    "summary": {
      "total_files": 45,
      "total_lines": 3250,
      "total_functions": 87,
      "total_classes": 12,
      "average_complexity": 4.2
    },
    "files": [
      {
        "path": "src/main.py",
        "language": "python",
        "lines": 150,
        "functions": 8,
        "classes": 2,
        "complexity_score": 6
      },
      {
        "path": "src/utils.py",
        "language": "python",
        "lines": 80,
        "functions": 5,
        "classes": 0,
        "complexity_score": 3
      }
    ],
    "language_breakdown": {
      "python": 30,
      "javascript": 10,
      "typescript": 5
    },
    "complexity_hotspots": [
      {
        "file": "src/parser.py",
        "function": "parse_complex_expression",
        "complexity": 15,
        "line": 42
      }
    ],
    "truncated": false,
    "files_analyzed": 45,
    "files_limit": 100
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
    "summary": {
      "total_files": 245,
      "total_lines": 18500,
      "total_functions": 412,
      "total_classes": 58,
      "average_complexity": 5.1
    },
    "files": [
      {
        "path": "src/main.py",
        "language": "python",
        "lines": 150,
        "functions": 8,
        "classes": 2,
        "complexity_score": 6,
        "imports": ["os", "sys", "utils"],
        "frameworks_detected": ["flask"]
      }
    ],
    "language_breakdown": {
      "python": 150,
      "javascript": 60,
      "typescript": 35
    },
    "complexity_hotspots": [
      {
        "file": "src/parser.py",
        "function": "parse_complex_expression",
        "complexity": 15,
        "line": 42,
        "cognitive_complexity": 22
      }
    ],
    "dependency_graph": {
      "src/main.py": ["src/utils.py", "src/config.py"],
      "src/api/routes.py": ["src/services/user.py", "src/models/user.py"]
    },
    "framework_detection": {
      "flask": {"confidence": 0.95, "files": ["src/main.py", "src/api/routes.py"]},
      "sqlalchemy": {"confidence": 0.88, "files": ["src/models/user.py"]}
    },
    "hotspot_analysis": {
      "by_complexity": ["src/parser.py", "src/validator.py"],
      "by_churn": ["src/api/routes.py", "src/main.py"]
    },
    "cache_hit": true,
    "incremental": false
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
    "summary": {
      "total_files": 1250,
      "total_lines": 95000,
      "total_functions": 2100,
      "total_classes": 320,
      "average_complexity": 5.8
    },
    "files": [
      {
        "path": "src/main.py",
        "language": "python",
        "lines": 150,
        "functions": 8,
        "classes": 2,
        "complexity_score": 6,
        "imports": ["os", "sys", "utils"],
        "frameworks_detected": ["flask"],
        "ownership": ["@backend-team"],
        "last_modified": "2025-12-15T10:30:00Z"
      }
    ],
    "language_breakdown": {
      "python": 800,
      "javascript": 300,
      "typescript": 150
    },
    "monorepo_modules": [
      {
        "name": "backend",
        "path": "packages/backend",
        "files": 400,
        "primary_language": "python"
      },
      {
        "name": "frontend",
        "path": "packages/frontend",
        "files": 350,
        "primary_language": "typescript"
      }
    ],
    "dependency_graph": {},
    "compliance_summary": {
      "files_checked": 800,
      "violations": 23,
      "critical": 2,
      "high": 5,
      "medium": 16
    },
    "historical_trends": {
      "complexity_trend": "increasing",
      "previous_average": 5.2,
      "current_average": 5.8,
      "runs_compared": 5
    },
    "custom_rules_applied": ["exclude-vendor", "python-only-src"],
    "distributed_stats": {
      "workers_used": 4,
      "wall_time_ms": 2500,
      "cpu_time_ms": 8500
    }
  },
  "id": 1
}
```

---
## Roadmap

### Cross-Cutting Research Topics

**Research queries (cross-cutting):**
- What are our FP/FN budgets for (a) language detection, (b) import/dependency extraction, (c) hotspot identification, and how do we measure them per release?
- What does “deterministic output” mean for `crawl_project` (ordering, counts, cache hits) across OS/filesystems, and how do we prove it?
- When should `crawl_project` omit fields vs return partial “best-effort” values, and how do we encode confidence/quality signals without breaking schema stability?
- What is the safe/secure boundary for stored crawl artifacts (cache/history) to avoid leaking secrets or proprietary code paths in logs/reports?
- What is the minimal, stable schema for multi-repo/monorepo signals (modules, dependency edges, ownership) that can evolve without churn?

**Research topics (cross-cutting):**
- Evaluation harness: curated repos + golden fixtures + regression scoring for per-tier contracts
- Determinism guarantees: stable file ordering, stable aggregation, stable cache rehydration
- Cache correctness: invalidation keys, partial corruption recovery, and monotonic schema upgrades
- Performance envelopes: throughput/memory targets by project size; parallelism safety; backpressure
- Privacy & security: redaction strategy for logs/artifacts; safe defaults for writing cache/history
- Versioning strategy: backward-compatible schema evolution, field deprecation policy, CI gates

**Success metrics (cross-cutting):**
- Determinism: identical results for identical inputs across supported OS/filesystems within the compatibility matrix
- Contract stability: no breaking schema changes in v1.x; compatibility tests in CI for output fields
- Cache safety: no stale-result regressions on a benchmark suite; graceful recovery from cache corruption
- Security hygiene: zero known secret exfiltration paths in cache/history artifacts; routine scanning in CI

### v1.1 (Q1 2026): Performance Optimization

#### Community Tier
- [ ] Faster file scanning
- [ ] Better progress reporting
- [ ] Configurable exclusion patterns

**Research topics (v1.1 / Community):**
- Fast directory walking strategies that remain deterministic across filesystems
- Progress reporting semantics that remain stable under parallelism (counts, phases, time estimation)
- Exclusion patterns UX: glob semantics, precedence rules, and safe defaults

**Success metrics (v1.1 / Community):**
- Throughput improvement on representative repos without changing output ordering
- Progress reporting accuracy within defined error bounds on large repos
- Exclusions: reproducible results when patterns are applied (no platform-specific drift)

#### Pro Tier
- [ ] Smart caching with invalidation
- [ ] Incremental updates (delta mode)
- [ ] Adaptive parallelization

**Research topics (v1.1 / Pro):**
- Cache invalidation: file hash vs metadata vs semantic hash tradeoffs and failure modes
- Delta mode UX: how to report “what changed” with low noise and stable ordering
- Adaptive parallelization: worker sizing heuristics that preserve determinism and avoid resource spikes

**Success metrics (v1.1 / Pro):**
- Cache correctness: no stale results in benchmark suite; schema upgrades don’t break rehydration
- Delta mode: stable outputs with bounded churn; clear cache hit/miss reporting
- Parallelism: measurable speedups on multi-core while preserving identical aggregated results

#### Enterprise Tier
- [ ] Distributed crawling across workers
- [ ] Real-time crawl monitoring
- [ ] Multi-repository orchestration

**Research topics (v1.1 / Enterprise):**
- Worker orchestration model: shard boundaries, retries, partial failures, and consistent aggregation
- Monitoring: what telemetry is safe and useful (phases, slow dirs, IO contention) without leaking paths
- Multi-repo orchestration: consistent identity for repos/modules and cross-repo caching boundaries

**Success metrics (v1.1 / Enterprise):**
- Distributed: predictable scaling on large repos with clear failure semantics
- Monitoring: actionable signals with low overhead; safe redaction defaults
- Multi-repo: deterministic aggregation across repos and stable module identifiers

### v1.2 (Q2 2026): Enhanced Analysis

#### All Tiers
- [ ] Better monorepo support
- [ ] Git history integration
- [ ] Submodule handling

**Research topics (v1.2 / All):**
- Monorepo heuristics: module boundary detection (package managers, build files, directory conventions)
- Git history integration: what signals matter (churn, hotspots over time) and safe data retention
- Submodule handling semantics: treat as separate roots vs included content; caching strategy

**Success metrics (v1.2 / All):**
- Monorepo: correct module boundary identification on curated fixtures
- Git integration: stable trend outputs with clear retention policy and reproducibility
- Submodules: consistent behavior across platforms and shallow clones

#### Pro Tier
- [ ] Code ownership mapping
- [ ] Team contribution analysis
- [ ] Technical debt scoring

**Research topics (v1.2 / Pro):**
- Ownership sources: CODEOWNERS vs git blame vs directory ownership; conflict resolution
- Contribution analysis: noise reduction (bots, bulk renames), identity mapping, privacy controls
- Debt scoring: signal selection and calibration (complexity, churn, ownership dispersion)

**Success metrics (v1.2 / Pro):**
- Ownership: stable mappings with explainability (“why this owner?”)
- Contribution: consistent aggregation despite renames and rebases; low churn in outputs
- Debt: correlates with later remediation effort on benchmark repos; conservative confidence

#### Enterprise Tier
- [ ] Organization-wide indexing
- [ ] Cross-repository dependency tracking
- [ ] Compliance dashboard generation

**Research topics (v1.2 / Enterprise):**
- Indexing: storage model, retention, and access controls for org-scale metadata
- Cross-repo dependencies: identity resolution and avoiding false edges across similarly named packages
- Compliance dashboards: report provenance, audit trail, and “best-effort” transparency

**Success metrics (v1.2 / Enterprise):**
- Indexing: bounded storage growth with clear retention/aggregation policy
- Cross-repo deps: measured precision/recall on curated dependency benchmarks
- Dashboards: reproducible reports with stable schema and clear audit metadata

### v1.3 (Q3 2026): AI-Enhanced Crawling

#### Pro Tier
- [ ] ML-based hotspot prediction
- [ ] Intelligent file prioritization
- [ ] Anomaly detection

**Research topics (v1.3 / Pro):**
- Ground truth for “hotspot”: labeling strategy and evaluation harness
- Prioritization UX: how to explain ranking decisions and avoid overconfidence
- Anomaly detection: defining baselines per repo/team and managing false positives

**Success metrics (v1.3 / Pro):**
- Hotspots: measurable lift over heuristic baselines with calibrated confidence
- Prioritization: stable ordering under small repo changes; explainable signals
- Anomalies: false-positive rate within defined budgets; easy suppression workflows

#### Enterprise Tier
- [ ] Custom ML model training
- [ ] Predictive maintenance scoring
- [ ] Risk forecasting

**Research topics (v1.3 / Enterprise):**
- Org-trained models: data governance, opt-in boundaries, reproducibility
- Predictive scoring calibration: how to avoid misleading “single-number” risk metrics
- Risk forecasting: what outcomes to predict (incidents, regressions) and validation strategy

**Success metrics (v1.3 / Enterprise):**
- Training: reproducible pipelines with clear data lineage and opt-out controls
- Predictive scores: calibrated uncertainty; tracked precision/recall against post-merge outcomes
- Forecasting: conservative confidence with measurable lift over baselines

### v1.4 (Q4 2026): Integration & Visualization

#### Community Tier
- [ ] HTML report generation
- [ ] JSON export
- [ ] CSV export

**Research topics (v1.4 / Community):**
- Minimal report schema: stable fields, versioning, and size controls for large repos
- Export determinism: stable ordering, consistent escaping/encoding, and portability

**Success metrics (v1.4 / Community):**
- Reports: reproducible outputs for identical inputs; stable schema with compatibility tests
- Exports: validated with round-trip parsing on representative datasets

#### Pro Tier
- [ ] Interactive web dashboard
- [ ] Real-time visualization
- [ ] IDE integration

**Research topics (v1.4 / Pro):**
- Visualization semantics: how to visualize hotspots/deps without misrepresenting confidence
- IDE integration: LSP vs extension APIs; performance budgets and incremental updates
- Real-time UX: streaming updates while preserving stable final aggregates

**Success metrics (v1.4 / Pro):**
- Dashboard: stable views with bounded latency on large repos
- IDE: interactive latency within defined bounds; robust offline behavior
- Real-time: partial updates are schema-valid; stable final results

#### Enterprise Tier
- [ ] Custom dashboard development
- [ ] SonarQube export
- [ ] JIRA integration

**Research topics (v1.4 / Enterprise):**
- Interop formats: SARIF vs Sonar formats vs custom JSON; compatibility testing
- Work-item integration: deduping, routing, and severity mapping to avoid ticket spam
- Auditability: provenance links from dashboards/tickets back to specific crawl versions

**Success metrics (v1.4 / Enterprise):**
- Exports: validated compatibility with at least one reference pipeline per target system
- Integrations: low duplicate rates; configurable routing by severity/category
- Audit trail: complete, reproducible linkage from artifacts to crawl inputs/settings

---

## Known Issues & Limitations

### Current Limitations
- **Large projects:** Very large projects (>10K files) may be slow
- **Binary files:** Binary files skipped (no analysis)
- **Generated code:** May include generated code in metrics
- **Non-Python depth:** JS/TS/Java analysis is currently heuristic (no full AST symbol extraction in v1.0)
- **Compliance scope:** Enterprise compliance scan is currently best-effort and Python-focused

**Research topics (limitations):**
- Large projects: IO bottlenecks vs CPU bottlenecks profiling; deterministic parallel walking; backpressure and cancellation semantics
- Binary files: detection heuristics, false positives, and when to fingerprint vs fully skip
- Generated code: detection strategies (path-based, file headers, tooling markers) and how to avoid excluding real source
- Non-Python depth: AST options per language and staged rollout plan (heuristics → partial AST → full symbol extraction)
- Compliance scope: multi-language policy coverage model; confidence and “best-effort” transparency in outputs

**Success metrics (limitations):**
- Large projects: completes within defined time/memory envelopes on a curated large-repo benchmark
- Generated code: measurable reduction in generated-code noise without regressions in real-source coverage
- Non-Python depth: per-language extraction accuracy meets defined baselines before enabling by default
- Compliance: documented scope + confidence signals; reproducible outputs with audit-friendly provenance

### Planned Fixes
- v1.1: Better performance for large projects
- v1.2: Generated code detection
- v1.3: Smart sampling for huge projects

---

## Success Metrics

### Quality Targets
- **Determinism:** Identical outputs for identical inputs across supported OS/filesystems
- **Cache correctness:** No stale-result regressions on benchmark suite; graceful recovery from partial corruption
- **Schema stability:** Backward-compatible output evolution only in v1.x; compatibility checks in CI

### Performance Targets
- **Crawl speed:** >100 files/second
- **Memory usage:** <500MB for 10K files
- **Accuracy:** >99% correct file classification

### Adoption Metrics
- **Usage:** 50K+ crawls per month by Q4 2026
- **Project size:** Average 1K+ files per project

---

## Dependencies

### Internal Dependencies
- `analysis/project_crawler.py` - Core crawler and per-file analyzers
- `mcp/server.py` - MCP tool wrapper, tier gating, and report augmentation
- `policy_engine/code_policy_check/analyzer.py` - Enterprise compliance scanning integration (best-effort)

### External Dependencies
- None (v1.0 implementation uses the Python standard library)

---

## Breaking Changes

None planned for v1.x series.

---

**Last Updated:** December 30, 2025  
**Next Review:** March 31, 2026
