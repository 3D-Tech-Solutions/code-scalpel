# get_cross_file_dependencies Tool Roadmap

**Tool Name:** `get_cross_file_dependencies`  
**Tool Version:** v1.0  
**Code Scalpel Version:** v3.3.0  
**Current Status:** Stable  
**Primary Modules:**
- `src/code_scalpel/mcp/server.py` (MCP tool handler)
- `src/code_scalpel/ast_tools/cross_file_extractor.py` (extraction engine)
- `src/code_scalpel/ast_tools/import_resolver.py` (import resolution)
- `src/code_scalpel/ast_tools/architectural_rules.py` (architectural rule engine) **NEW**
**Tier Availability:** All tiers (Community, Pro, Enterprise)

---

## Overview

The `get_cross_file_dependencies` tool analyzes import/require statements and traces dependency chains across file boundaries with confidence scoring. It extracts complete code context for AI-assisted editing by following import chains and providing confidence-decayed scores for deep dependencies.

**Key Value Proposition:** Enable AI agents to understand complete code context without hallucinating dependencies.

---

## Current Capabilities (v1.0.0)

### Community Tier
- ✅ Direct import mapping (file → imported files)
- ✅ Circular import detection
- ✅ Import graph generation
- ✅ Mermaid diagram visualization
- ✅ Confidence scoring with decay (0.9^depth)
- ✅ Combined code output for AI consumption
- **Limits:** max_depth: 1 (direct only), max_files: 50

### Pro Tier
- ✅ All Community features
- ✅ Transitive dependency mapping (A → B → C chains)
- ✅ Dependency chain visualization (up to 25 chains)
- ✅ Deep coupling analysis (deps/files ratio score)
- ✅ **Import alias resolution** (`import X as Y` → origin tracking) **ENHANCED v3.3.0**
- ✅ **Wildcard import handling** (`from x import *` → `__all__` expansion) **ENHANCED v3.3.0**
- ✅ **Re-export chain resolution** (package `__init__.py` → original module) **NEW v3.3.0**
- ✅ **Chained alias resolution** (multi-hop alias tracking) **NEW v3.3.0**
- **Limits:** max_depth: 5, max_files: 500

### Enterprise Tier
- ✅ All Pro features
- ✅ Architectural firewall (layer boundary enforcement)
- ✅ Boundary violation alerts (presentation → data detection)
- ✅ Layer constraint enforcement (upward dependency detection)
- ✅ **Configurable dependency rule engine** (user-defined rules via architecture.toml) **ENHANCED v3.3.0**
- ✅ **Custom architectural rules** (allow/deny patterns with severity levels) **NEW v3.3.0**
- ✅ **Coupling limit validation** (fan-in, fan-out, depth limits) **NEW v3.3.0**
- ✅ **Exemption patterns** (exclude tests, utilities from rule checking) **NEW v3.3.0**
- ✅ Architectural alerts with recommendations
- **Limits:** unlimited depth, unlimited files

---

## MCP Request/Response Examples

### MCP Request Format

```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "mcp_code-scalpel_get_cross_file_dependencies",
    "arguments": {
      "file_path": "/home/user/project/src/main.py",
      "max_depth": 3,
      "include_code": true
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
    "source_file": "/home/user/project/src/main.py",
    "dependencies": [
      {
        "file": "/home/user/project/src/utils.py",
        "imports": ["helper_func", "format_output"],
        "depth": 1,
        "confidence": 0.9
      },
      {
        "file": "/home/user/project/src/config.py",
        "imports": ["DEFAULT_SETTINGS"],
        "depth": 1,
        "confidence": 0.9
      }
    ],
    "circular_imports": [],
    "import_graph": {
      "main.py": ["utils.py", "config.py"]
    },
    "mermaid_diagram": "graph LR\n  main.py --> utils.py\n  main.py --> config.py",
    "combined_code": "# From utils.py\ndef helper_func(x):\n    return x + 1\n\ndef format_output(data):\n    return str(data)\n\n# From config.py\nDEFAULT_SETTINGS = {'debug': True}",
    "files_analyzed": 3,
    "max_depth_reached": 1,
    "truncated": false
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
    "source_file": "/home/user/project/src/main.py",
    "dependencies": [
      {
        "file": "/home/user/project/src/utils.py",
        "imports": ["helper_func", "format_output"],
        "depth": 1,
        "confidence": 0.9,
        "import_type": "from_import"
      },
      {
        "file": "/home/user/project/src/config.py",
        "imports": ["DEFAULT_SETTINGS", "Settings"],
        "depth": 1,
        "confidence": 0.9,
        "import_type": "from_import"
      },
      {
        "file": "/home/user/project/src/core/engine.py",
        "imports": ["Engine"],
        "depth": 2,
        "confidence": 0.81,
        "import_type": "transitive"
      }
    ],
    "circular_imports": [],
    "transitive_chains": [
      {
        "chain": ["main.py", "utils.py", "core/engine.py"],
        "symbols": ["helper_func", "Engine"]
      }
    ],
    "dependency_chains": [
      ["main.py", "utils.py", "core/engine.py", "core/base.py"]
    ],
    "coupling_score": 0.35,
    "alias_resolutions": [
      {
        "alias": "cfg",
        "original_module": "config",
        "file": "main.py"
      }
    ],
    "wildcard_expansions": [
      {
        "file": "utils.py",
        "from_module": "helpers",
        "expanded_symbols": ["func_a", "func_b", "ClassC"]
      }
    ],
    "reexport_chains": [
      {
        "symbol": "Engine",
        "apparent_source": "core/__init__.py",
        "actual_source": "core/engine.py"
      }
    ],
    "import_graph": {
      "main.py": ["utils.py", "config.py"],
      "utils.py": ["core/engine.py"]
    },
    "mermaid_diagram": "graph LR\n  main.py --> utils.py\n  main.py --> config.py\n  utils.py --> core/engine.py",
    "combined_code": "...",
    "files_analyzed": 8,
    "max_depth_reached": 3
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
    "source_file": "/home/user/project/src/main.py",
    "dependencies": [
      {
        "file": "/home/user/project/src/utils.py",
        "imports": ["helper_func", "format_output"],
        "depth": 1,
        "confidence": 0.9,
        "import_type": "from_import",
        "layer": "application"
      },
      {
        "file": "/home/user/project/src/db/queries.py",
        "imports": ["get_user"],
        "depth": 2,
        "confidence": 0.81,
        "import_type": "transitive",
        "layer": "infrastructure"
      }
    ],
    "circular_imports": [],
    "architectural_violations": [
      {
        "type": "layer_violation",
        "from_file": "src/api/routes.py",
        "from_layer": "presentation",
        "to_file": "src/db/queries.py",
        "to_layer": "infrastructure",
        "rule": "no_direct_db_access_from_presentation",
        "severity": "critical",
        "recommendation": "Use repository pattern via application layer"
      }
    ],
    "boundary_alerts": [
      {
        "type": "upward_dependency",
        "from_layer": "domain",
        "to_layer": "application",
        "files": ["models/user.py", "services/user_service.py"],
        "severity": "warning"
      }
    ],
    "coupling_violations": [
      {
        "file": "src/utils.py",
        "metric": "fan_in",
        "value": 25,
        "limit": 20,
        "severity": "warning"
      }
    ],
    "layer_mapping": {
      "presentation": ["api/", "controllers/"],
      "application": ["services/"],
      "domain": ["models/"],
      "infrastructure": ["db/", "repositories/"]
    },
    "exempted_files": ["tests/", "conftest.py"],
    "import_graph": {},
    "combined_code": "...",
    "files_analyzed": 45,
    "max_depth_reached": 10,
    "rules_applied": [
      "no_direct_db_access_from_presentation",
      "downward_only_layer_direction",
      "max_fan_in_20"
    ]
  },
  "id": 1
}
```

---

## Recent Implementations (v3.3.0)

### Pro Tier Enhancements

#### Wildcard Import `__all__` Expansion
```python
# Now correctly expands:
# utils.py: __all__ = ["helper_func", "HelperClass"]
# main.py: from utils import *
# → Resolves to: helper_func, HelperClass (not _private symbols)

resolver.expand_wildcard_import("utils")  # ['helper_func', 'HelperClass']
resolver.expand_all_wildcards("main")     # {'utils': ['helper_func', ...]}
```

#### Re-export Chain Resolution
```python
# Package __init__.py re-exports are now tracked:
# mypackage/__init__.py: from mypackage.internal import helper_func
# mypackage/__init__.py: __all__ = ['helper_func']

resolver.detect_reexports("mypackage")  # {'helper_func': 'mypackage.internal'}
resolver.get_all_reexports()            # All re-exports across project
```

#### Chained Alias Resolution
```python
# Multi-hop alias chains are now resolved:
# internal.py: def original_func(): ...
# wrapper.py: from internal import original_func as wrapped_func
# main.py: from wrapper import wrapped_func as my_func

resolver.resolve_alias_chain("main", "my_func")
# → ('internal', 'original_func', ['main', 'wrapper', 'internal'])
```

### Enterprise Tier Enhancements

#### Configurable Architectural Rules
Configuration file: `.code-scalpel/architecture.toml`

```toml
[layers]
order = ["presentation", "application", "domain", "infrastructure"]

[layers.mapping]
presentation = ["**/controllers/**", "**/api/**"]
application = ["**/services/**"]
domain = ["**/models/**", "**/domain/**"]
infrastructure = ["**/database/**", "**/repositories/**"]

[rules]
layer_direction = "downward_only"  # Higher layers can only depend on lower layers

[[rules.custom]]
name = "no_direct_db_access_from_presentation"
from_pattern = "**/controllers/**"
to_pattern = "**/database/**"
action = "deny"
severity = "critical"

[rules.coupling]
max_fan_in = 20
max_fan_out = 15
max_dependency_depth = 10

[exemptions]
patterns = ["**/tests/**", "**/test_*.py"]
modules = ["__init__", "utils", "helpers"]
```

---

## Roadmap

### v2.6.0 (Q1 2026): Enhanced Resolution & Error Handling

#### Community Tier
- [ ] Better error messages for unresolved imports with suggestions
- [ ] Relative import path resolution improvements
- [x] Package alias handling (`import X as Y`) **Completed v3.3.0**
- [ ] Progress reporting during extraction

#### Pro Tier
- [ ] Dynamic import detection (`importlib.import_module()`, `__import__()`)
- [ ] Conditional import tracking (`if TYPE_CHECKING:`)
- [x] Module re-export handling (`__all__` traversal) **Completed v3.3.0**
- [ ] Lazy import detection

#### Enterprise Tier
- [ ] Monorepo workspace resolution (Nx, Turborepo, Lerna)
- [ ] Private package registry support (Artifactory, Nexus)
- [x] Custom module resolution rules (configurable via architecture.toml) **Completed v3.3.0**
- [ ] Import cost analysis (bundle size impact)

**Research Queries:**
- "How do modern build tools resolve module aliases?"
- "What patterns indicate conditional/lazy imports in Python/TypeScript?"
- "How to detect re-exports in barrel files?"

### v2.7.0 (Q2 2026): Language Expansion

#### All Tiers
- [ ] Java dependency analysis (Maven pom.xml, Gradle build.gradle)
- [ ] Go module dependency analysis (go.mod)
- [ ] Rust crate dependency analysis (Cargo.toml)

#### Pro Tier
- [ ] C/C++ include dependency tracking (#include resolution)
- [ ] PHP namespace/use resolution
- [ ] Ruby require/gem dependency tracking

#### Enterprise Tier
- [ ] Multi-language dependency graphs (unified view)
- [ ] Cross-language dependency detection (Python calling Rust, JS calling WASM)
- [ ] Language boundary security analysis

**Research Queries:**
- "How does Maven resolve transitive dependencies with version conflicts?"
- "What are the common patterns for FFI boundaries (Python↔Rust, Node↔C++)?"
- "How to detect WASM imports in JavaScript projects?"

### v2.8.0 (Q3 2026): Performance & Scalability

#### All Tiers
- [ ] Incremental dependency analysis (only reanalyze changed files)
- [ ] Parallel dependency resolution (multi-threaded extraction)
- [ ] Smart caching with file modification tracking
- [ ] Memory-efficient streaming for large codebases

#### Pro Tier
- [ ] Delta dependency updates (diff from last analysis)
- [ ] Dependency graph diff (compare two commits)
- [ ] Hot path optimization (pre-computed common dependencies)

#### Enterprise Tier
- [ ] Distributed dependency analysis (cluster support)
- [ ] Real-time dependency monitoring (file watcher integration)
- [ ] Historical dependency trends (time-series analysis)
- [ ] Dependency change impact prediction

**Research Queries:**
- "How do LSP servers implement incremental parsing efficiently?"
- "What graph algorithms work best for dependency diff computation?"
- "How to implement distributed AST parsing with consistent results?"

**Performance Targets:**
- Incremental: <50ms for single-file change
- Full scan: <5s for 10K file project
- Memory: <500MB for 100K file project

### v2.9.0 (Q4 2026): Advanced Features & AI Integration

#### Pro Tier
- [ ] Interactive dependency visualization (D3.js/Mermaid)
- [ ] Impact analysis ("what depends on this symbol?")
- [ ] Automated refactoring suggestions based on coupling
- [ ] Dead dependency detection (unused imports)
- [ ] Dependency health scoring

#### Enterprise Tier
- [ ] Dependency risk scoring (CVE correlation, maintainer activity)
- [ ] Compliance-based dependency rules (license checks, approved lists)
- [ ] Automated dependency updates with PR generation
- [ ] Dependency policy-as-code (Rego/OPA integration)
- [ ] SBOM (Software Bill of Materials) generation

**Research Queries:**
- "What metrics best predict dependency-related bugs?"
- "How to correlate dependency graphs with CVE databases efficiently?"
- "What's the state of the art in automated dependency update safety?"

### v3.0.0 (Q1 2027): Semantic Understanding

#### Pro Tier
- [ ] Semantic dependency analysis (not just imports, but actual usage)
- [ ] Type flow tracking across file boundaries
- [ ] Interface/protocol dependency mapping
- [ ] Test coverage correlation with dependencies

#### Enterprise Tier
- [ ] AI-powered dependency refactoring suggestions
- [ ] Dependency injection container analysis (Spring, Angular, NestJS)
- [ ] Microservice boundary detection from code
- [ ] API contract extraction from dependencies
- [ ] Dependency documentation generation

**Research Queries:**
- "How to detect semantic coupling beyond syntactic imports?"
- "What ML models work best for code dependency prediction?"
- "How to extract API contracts from code without running it?"

---

## Known Issues & Limitations

### Current Limitations (v2.5.0)
| Limitation | Impact | Workaround | Planned Fix |
|------------|--------|------------|-------------|
| Dynamic imports not detected | May miss runtime dependencies | Document known dynamic imports | v2.6.0 |
| Complex path aliases (tsconfig/webpack) | May not resolve all imports | Use explicit paths | v2.6.0 |
| External package internals | Third-party code not analyzed | N/A (by design) | Optional in v2.7.0 |
| No Java/Go/Rust support | Limited to Python/JS/TS | Use language-specific tools | v2.7.0 |
| Single-repo only | No cross-repo analysis | Analyze repos separately | v2.6.0 Enterprise |

### Technical Debt
- [ ] Unify `dependency_parser.py` and `cross_file_extractor.py` APIs
- [ ] Add comprehensive integration tests for all tier combinations
- [ ] Improve confidence decay algorithm (consider branching factor)

---

## Success Metrics

### Performance Targets
| Metric | Target | Current | Status |
|--------|--------|---------|--------|
| Resolution time per dependency | <100ms | ~80ms | ✅ Met |
| Accuracy (import detection) | >98% | ~97% | 🔄 In progress |
| Coverage (imports resolved) | >95% | ~92% | 🔄 In progress |
| Timeout protection | 100% | 100% | ✅ Met |
| Confidence scoring accuracy | >90% | ~95% | ✅ Met |

### Adoption Metrics (Targets for Q4 2026)
| Metric | Target | Tracking |
|--------|--------|----------|
| Monthly dependency queries | 100K+ | TBD |
| Avg depth traced | 3+ levels | TBD |
| Enterprise architectural alerts acted on | 80%+ | TBD |
| Community → Pro conversion (via this tool) | 5%+ | TBD |

### Quality Metrics
| Metric | Target | Current |
|--------|--------|---------|
| Test coverage | >95% | 94% |
| Zero false positives for circular imports | 100% | 100% |
| Mermaid diagram generation success | >99% | 99.5% |

---

## Dependencies

### Internal Dependencies
| Module | Purpose | Version |
|--------|---------|---------|
| `ast_tools/import_resolver.py` | Import resolution engine | v1.6.0+ |
| `ast_tools/cross_file_extractor.py` | Code extraction | v1.5.1+ |
| `ast_tools/architectural_rules.py` | Architectural rule engine | v3.3.0+ **NEW** |
| `licensing/features.py` | Tier capability gating | v3.0.0+ |
| `mcp/server.py` | MCP tool handler | v3.3.0+ |

### External Dependencies
| Package | Purpose | Version |
|---------|---------|---------|
| None required | - | - |

### Optional Dependencies (for future features)
| Package | Purpose | Planned Version |
|---------|---------|-----------------|
| `networkx` | Graph algorithms for v2.8.0 | v2.8.0 |
| `libcst` | Better Python AST for v3.0.0 | v3.0.0 |

---

## Breaking Changes

### v2.5.0 → v2.6.0
- None planned

### v2.x → v3.0.0
- `dependency_chains` output format may change to include semantic metadata
- `coupling_score` algorithm may be updated (will provide migration guide)

---

## Competitive Analysis

| Feature | Code Scalpel | Madge | dependency-cruiser | Sourcegraph |
|---------|--------------|-------|-------------------|-------------|
| Python support | ✅ | ❌ | ❌ | ✅ |
| TypeScript support | ✅ | ✅ | ✅ | ✅ |
| Confidence scoring | ✅ | ❌ | ❌ | ❌ |
| Architectural rules | ✅ Enterprise | ❌ | ✅ | ❌ |
| AI-optimized output | ✅ | ❌ | ❌ | ❌ |
| MCP integration | ✅ | ❌ | ❌ | ❌ |
| Circular detection | ✅ All tiers | ✅ | ✅ | ✅ |
| Transitive chains | ✅ Pro+ | ✅ | ✅ | ✅ |

**Unique Value:** Code Scalpel is the only tool designed specifically for AI agent consumption with confidence-scored, context-window-aware output.

---

## References

- [Verification Document](../analysis/tool_validation/GET_CROSS_FILE_DEPENDENCIES_VERIFICATION.md)
- [Tier Configuration](../../src/code_scalpel/licensing/features.py)
- [MCP Tool Implementation](../../src/code_scalpel/mcp/server.py)
- [Architecture Configuration](../../.code-scalpel/architecture.toml) **NEW**
- [Response Config](../../.code-scalpel/response_config.json)

---

**Last Updated:** December 31, 2025  
**Next Review:** March 31, 2026  
**Owner:** Code Scalpel Core Team
