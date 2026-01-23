# get_project_map Tool Roadmap

**Tool Name:** `get_project_map`  
**Tool Version:** V1.0  
**Code Scalpel Version:** v3.3.1  
**Current Status:** Stable  
**Primary Module:** `src/code_scalpel/mcp/server.py`  
**Tier Availability:** All tiers (Community, Pro, Enterprise)

---

## Configuration Files

| File | Purpose |
|------|---------|
| `src/code_scalpel/licensing/features.py` | Tier capability definitions |
| `.code-scalpel/limits.toml` | Numeric limits (max_files, max_modules) |
| `.code-scalpel/response_config.json` | Output filtering (exclude metadata fields) |
| `.code-scalpel/architecture.toml` | Custom architectural rules (Enterprise) |

---

## Overview

The `get_project_map` tool generates comprehensive project structure maps showing packages, modules, complexity hotspots, and architecture patterns.

**Why AI Agents Need This:**
- **Context bootstrapping:** Rapidly understand unfamiliar codebases before making changes
- **Navigation:** Find the right files to modify without hallucinating paths
- **Architecture awareness:** Understand layered architecture to avoid coupling violations
- **Onboarding acceleration:** New developers (and AI agents) can orient themselves in minutes
- **Technical debt visibility:** Identify complexity hotspots and churn areas for prioritization

---

## Research Queries for Future Development

### Foundational Research
| Topic | Query | Purpose |
|-------|-------|---------|
| Architecture Recovery | "automated software architecture recovery from source code" | Improve pattern detection |
| Code Metrics | "cyclomatic complexity vs cognitive complexity modern comparison" | Better complexity scoring |
| Monorepo Analysis | "monorepo dependency analysis tools comparison" | Handle large-scale projects |
| City Metaphor | "code city visualization research effectiveness" | Enhance city map feature |

### Language-Specific Research
| Topic | Query | Purpose |
|-------|-------|---------|
| Python Packaging | "python package structure best practices 2025" | Better Python analysis |
| JavaScript Modules | "es modules vs commonjs detection heuristics" | Improve JS/TS support |
| Java Architecture | "java project structure spring boot microservices" | Add Java patterns |
| Polyglot Projects | "polyglot repository structure analysis" | Multi-language support |

### Advanced Techniques
| Topic | Query | Purpose |
|-------|-------|---------|
| ML Architecture | "machine learning code architecture classification" | AI-powered pattern detection |
| Graph Clustering | "community detection algorithms software modules" | Auto-detect boundaries |
| Technical Debt | "technical debt quantification automated tools" | Debt scoring improvement |
| Architecture Drift | "architecture conformance checking tools" | Compliance validation |

---

## Current Capabilities (V1.0)

### Community Tier
- ✅ Package/module hierarchy (`packages`, `modules` fields)
- ✅ File count statistics (`total_files`, `total_lines`)
- ✅ Language distribution (`languages` field)
- ✅ Basic complexity metrics (`complexity_hotspots`)
- ✅ Mermaid diagram export (`mermaid` field)
- ✅ Entry point detection (`entry_points` field)
- ✅ Circular import detection (`circular_imports` field)
- ⚠️ **Limits:** max_files=100, max_modules=50

### Pro Tier
- ✅ All Community features
- ✅ Complexity hotspot identification (`complexity_hotspots`)
- ✅ Architecture pattern detection (`architectural_layers`)
- ✅ Dependency cluster analysis (`coupling_metrics`)
- ✅ Code ownership mapping (`git_ownership` via git blame)
- ✅ Module relationships (`module_relationships`)
- ✅ Dependency diagram (`dependency_diagram`)
- ⚠️ **Limits:** max_files=1000, max_modules=200

### Enterprise Tier
- ✅ All Pro features
- ✅ Multi-repository maps (`multi_repo_summary`)
- ✅ Historical architecture trends (`historical_trends` via git log)
- ✅ Custom map metrics (`custom_metrics` from architecture.toml)
- ✅ Compliance overlay (`compliance_overlay` via architectural rules)
- ✅ Technical debt visualization (`churn_heatmap`, `bug_hotspots`)
- ✅ City map visualization (`city_map_data`)
- ✅ Force-directed graph (`force_graph`)
- ⚠️ **Limits:** max_files=unlimited, max_modules=1000

---

## Return Model: ProjectMapResult

```python
class ProjectMapResult(BaseModel):
    # Core fields (All Tiers)
    success: bool                           # Whether mapping succeeded
    packages: list[PackageInfo]             # Package hierarchy
    modules: list[ModuleInfo]               # Module listing
    total_files: int                        # Total files found
    total_lines: int                        # Total lines of code
    languages: dict[str, int]               # Language distribution
    entry_points: list[str]                 # Detected entry points
    circular_imports: list[CircularImport]  # Detected circular dependencies
    complexity_hotspots: list[HotspotInfo]  # High complexity areas
    mermaid: str                            # Mermaid diagram of structure
    
    # Pro Tier
    architectural_layers: list[str]         # Detected layers (UI, service, data)
    coupling_metrics: dict[str, float]      # Module coupling scores
    git_ownership: dict[str, str]           # File -> owner mapping
    module_relationships: list[Relationship] # Module dependencies
    dependency_diagram: str                 # Dependency Mermaid diagram
    
    # Enterprise Tier
    multi_repo_summary: dict[str, RepoInfo] # Cross-repo analysis
    historical_trends: TrendData            # Architecture evolution over time
    custom_metrics: dict[str, Any]          # User-defined metrics
    compliance_overlay: ComplianceReport    # Rule violations
    churn_heatmap: dict[str, float]         # Change frequency by file
    bug_hotspots: list[str]                 # High-bug-rate files
    city_map_data: CityMapData              # 3D city visualization data
    force_graph: ForceGraphData             # Force-directed graph data
    
    # Output Metadata (All Tiers) - v1.1
    # [20260111_FEATURE] Added for tier transparency to AI agents
    tier_applied: str                       # Which tier was used: "community"|"pro"|"enterprise"
    max_files_applied: int | None           # Effective file limit (None=unlimited)
    max_modules_applied: int | None         # Effective module limit (None=unlimited)
    pro_features_enabled: bool              # Whether Pro features are available
    enterprise_features_enabled: bool       # Whether Enterprise features are available
```

### Output Metadata Fields

> [20260111_FEATURE] These fields provide transparency to AI agents about which tier configuration was applied.

| Field | Type | Purpose |
|-------|------|---------|
| `tier_applied` | `str` | Which license tier was applied: `"community"`, `"pro"`, or `"enterprise"` |
| `max_files_applied` | `int \| None` | The file limit that was enforced. `None` indicates unlimited (Enterprise). |
| `max_modules_applied` | `int \| None` | The module limit that was enforced. `None` indicates unlimited. |
| `pro_features_enabled` | `bool` | `True` if Pro-tier features (coupling metrics, git ownership, etc.) are available |
| `enterprise_features_enabled` | `bool` | `True` if Enterprise-tier features (city map, compliance overlay, etc.) are available |

**Why These Fields Matter:**
- AI agents can verify they're operating with expected permissions
- Debugging tier configuration issues becomes straightforward
- Output is self-documenting - no need to check external config files
- Consistent with `get_file_context` tool pattern for cross-tool consistency

---

## Usage Examples

### Community Tier
```python
result = await get_project_map(
    project_root="/path/to/project"
)
# Returns: packages, modules, languages, entry_points, circular_imports,
#          complexity_hotspots, mermaid diagram
# Limited to max 100 files, 50 modules
```

### Pro Tier
```python
result = await get_project_map(
    project_root="/path/to/project",
    include_git_analysis=True
)
# Additional: architectural_layers, coupling_metrics, git_ownership,
#             module_relationships, dependency_diagram
# Up to 1000 files, 200 modules
```

### Enterprise Tier
```python
result = await get_project_map(
    project_root="/path/to/project",
    additional_roots=["/path/to/other/repo"],
    include_historical=True,
    compliance_rules="architecture.toml"
)
# Additional: multi_repo_summary, historical_trends, custom_metrics,
#             compliance_overlay, churn_heatmap, bug_hotspots,
#             city_map_data, force_graph
# Unlimited files and modules
```

---

## MCP Request/Response Examples

### MCP Request Format

```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "mcp_code-scalpel_get_project_map",
    "arguments": {
      "project_root": "/home/user/my-project"
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
    "packages": [
      {"name": "src", "path": "/home/user/my-project/src", "modules": 8},
      {"name": "tests", "path": "/home/user/my-project/tests", "modules": 5}
    ],
    "modules": [
      {"name": "main", "path": "src/main.py", "lines": 150, "complexity": 5},
      {"name": "utils", "path": "src/utils.py", "lines": 80, "complexity": 3},
      {"name": "handlers", "path": "src/handlers.py", "lines": 200, "complexity": 12}
    ],
    "total_files": 45,
    "total_lines": 3500,
    "languages": {
      "python": 35,
      "javascript": 8,
      "json": 2
    },
    "entry_points": ["src/main.py:main", "src/cli.py:cli"],
    "circular_imports": [],
    "complexity_hotspots": [
      {
        "file": "src/handlers.py",
        "function": "process_request",
        "complexity": 15,
        "line": 42
      }
    ],
    "mermaid": "graph TD\n  src[src/]\n  src --> main.py\n  src --> utils.py\n  src --> handlers.py",
    "truncated": false,
    "files_limit": 100,
    "modules_limit": 50,
    "tier_applied": "community",
    "max_files_applied": 100,
    "max_modules_applied": 50,
    "pro_features_enabled": false,
    "enterprise_features_enabled": false
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
    "packages": [
      {"name": "src", "path": "/home/user/my-project/src", "modules": 45}
    ],
    "modules": [
      {"name": "main", "path": "src/main.py", "lines": 150, "complexity": 5}
    ],
    "total_files": 250,
    "total_lines": 18500,
    "languages": {
      "python": 180,
      "javascript": 50,
      "typescript": 20
    },
    "entry_points": ["src/main.py:main", "src/cli.py:cli", "src/api/app.py:create_app"],
    "circular_imports": [
      {
        "cycle": ["models/user.py", "models/order.py", "models/user.py"],
        "severity": "warning"
      }
    ],
    "complexity_hotspots": [
      {
        "file": "src/handlers.py",
        "function": "process_request",
        "complexity": 15,
        "cognitive_complexity": 22,
        "line": 42
      }
    ],
    "mermaid": "graph TD\n  ...",
    "architectural_layers": ["presentation", "application", "domain", "infrastructure"],
    "coupling_metrics": {
      "src/handlers.py": 0.72,
      "src/utils.py": 0.25,
      "src/db/queries.py": 0.68
    },
    "git_ownership": {
      "src/handlers.py": "@alice",
      "src/utils.py": "@bob",
      "src/db/": "@data-team"
    },
    "module_relationships": [
      {"from": "handlers.py", "to": "utils.py", "type": "import"},
      {"from": "handlers.py", "to": "db/queries.py", "type": "import"}
    ],
    "dependency_diagram": "graph LR\n  handlers --> utils\n  handlers --> db/queries",
    "tier_applied": "pro",
    "max_files_applied": 1000,
    "max_modules_applied": 200,
    "pro_features_enabled": true,
    "enterprise_features_enabled": false
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
    "packages": [
      {"name": "src", "path": "/home/user/my-project/src", "modules": 250}
    ],
    "modules": [],
    "total_files": 1250,
    "total_lines": 95000,
    "languages": {
      "python": 800,
      "javascript": 300,
      "typescript": 150
    },
    "entry_points": [],
    "circular_imports": [],
    "complexity_hotspots": [],
    "mermaid": "...",
    "architectural_layers": ["presentation", "application", "domain", "infrastructure"],
    "coupling_metrics": {},
    "git_ownership": {},
    "module_relationships": [],
    "dependency_diagram": "...",
    "multi_repo_summary": {
      "main-project": {"files": 800, "lines": 60000},
      "shared-lib": {"files": 200, "lines": 15000},
      "config-repo": {"files": 50, "lines": 5000}
    },
    "historical_trends": {
      "complexity_trend": "increasing",
      "monthly_stats": [
        {"month": "2025-10", "avg_complexity": 5.2, "total_files": 1100},
        {"month": "2025-11", "avg_complexity": 5.5, "total_files": 1180},
        {"month": "2025-12", "avg_complexity": 5.8, "total_files": 1250}
      ]
    },
    "custom_metrics": {
      "api_surface_size": 45,
      "test_coverage_estimate": 78.5
    },
    "compliance_overlay": {
      "violations": [
        {
          "rule": "no_direct_db_from_controller",
          "file": "src/api/routes.py",
          "severity": "critical"
        }
      ],
      "passed_rules": 15,
      "failed_rules": 1
    },
    "churn_heatmap": {
      "src/handlers.py": 0.85,
      "src/utils.py": 0.12,
      "src/db/queries.py": 0.67
    },
    "bug_hotspots": ["src/handlers.py", "src/auth/oauth.py"],
    "city_map_data": {
      "buildings": [
        {"module": "handlers", "height": 15, "area": 200, "color": "#ff6b6b"},
        {"module": "utils", "height": 3, "area": 80, "color": "#4ecdc4"}
      ]
    },
    "force_graph": {
      "nodes": [],
      "links": []
    },
    "tier_applied": "enterprise",
    "max_files_applied": null,
    "max_modules_applied": 1000,
    "pro_features_enabled": true,
    "enterprise_features_enabled": true
  },
  "id": 1
}
```

---

## Integration Points

### Related Tools
| Tool | Relationship |
|------|--------------|
| `get_call_graph` | Detailed function-level edges within modules |
| `get_cross_file_dependencies` | Deeper import/dependency analysis |
| `crawl_project` | Complementary file-level metrics |
| `get_file_context` | Per-file detail view |
| `scan_dependencies` | External package analysis |

### Export Formats
| Format | Status | Use Case |
|--------|--------|----------|
| **Mermaid** | ✅ V1.0 | Documentation, README diagrams |
| **JSON** | ✅ V1.0 | Programmatic analysis |
| **HTML Report** | 🔄 v1.2 | Stakeholder presentations |
| **SARIF** | 🔄 v1.3 | CI/CD integration |

---

## Competitive Analysis

| Tool | Strengths | Weaknesses | Our Differentiation |
|------|-----------|------------|---------------------|
| **SonarQube** | Mature, CI integration | Heavy, self-hosted | Lightweight, MCP-native |
| **CodeClimate** | Easy setup, GitHub | Limited architecture | Deeper structure analysis |
| **Understand (SciTools)** | Comprehensive | Expensive, closed source | Open, tiered pricing |
| **Sourcetrail** | Great visualization | Discontinued | Active development |
| **Arcan** | Academic, rigorous | Complex setup | Simpler API, AI-focused |

---

## Roadmap

### v1.2 (Q1 2026): Enhanced Visualization

#### Community Tier
- [ ] Mermaid diagram export
- [ ] JSON/YAML export
- [ ] HTML report generation

#### Pro Tier
- [ ] Interactive web-based map
- [ ] Drill-down navigation
- [ ] Real-time map updates

#### Enterprise Tier
- [ ] Custom visualization themes
- [ ] Embedded dashboards
- [ ] 3D architecture visualization

### v1.2 (Q2 2026): Advanced Analysis

#### All Tiers
- [ ] Entry point detection
- [ ] Dead code identification
- [ ] Test coverage overlay

#### Pro Tier
- [ ] Microservice boundaries
- [ ] API surface mapping
- [ ] Framework pattern detection

#### Enterprise Tier
- [ ] Cross-repository architecture
- [ ] Service mesh visualization
- [ ] Infrastructure integration

### v1.3 (Q3 2026): AI-Enhanced Mapping

#### Pro Tier
- [ ] ML-based pattern recognition
- [ ] Anomaly detection
- [ ] Architecture smell detection

#### Enterprise Tier
- [ ] Custom pattern training
- [ ] Predictive architecture analysis
- [ ] Automated architecture validation

### v1.4 (Q4 2026): Integration & Automation

#### Community Tier
- [ ] CI/CD integration
- [ ] GitHub Pages export
- [ ] Markdown documentation

#### Pro Tier
- [ ] IDE integration
- [ ] Real-time architecture monitoring
- [ ] Slack/Teams notifications

#### Enterprise Tier
- [ ] Architecture compliance gates
- [ ] Automated governance checks
- [ ] CMDB integration

---

## Known Issues & Limitations

### Current Limitations
- **Large projects:** Very large projects (>10K files) may be slow
- **Monorepos:** Complex monorepo structures may need tuning
- **External services:** Cannot map external service dependencies
- **Multi-repo:** Requires `additional_roots` parameter (placeholder implementation)

### Planned Fixes
- v1.2: Better performance for large projects
- v1.3: Monorepo-aware mapping
- v1.4: External service inference

---

## Success Metrics

### Performance Targets
- **Map generation:** <10s for 1K files
- **Memory usage:** <500MB for 10K files
- **Accuracy:** >95% correct structure

### Adoption Metrics
- **Usage:** 20K+ map generations per month by Q4 2026
- **Use case:** Architecture documentation

---

## Dependencies

### Internal Dependencies
- `mcp/server.py` - MCP tool handler and implementation
- `ast_tools/call_graph.py` - Circular import detection
- `ast_tools/architectural_rules.py` - Compliance overlay (Enterprise)
- `licensing/features.py` - Tier capability definitions

### External Dependencies
- Git CLI (optional, for ownership/trends analysis)

---

## Breaking Changes

None planned for v1.x series.

---

## Changelog

### V1.0 (December 31, 2025)
- **Pro Tier:** Added `git_blame_integration` and `code_ownership_mapping` capabilities
- **Enterprise:** Added `multi_repository_maps` capability with `multi_repo_summary` field
- **Enterprise:** Added `historical_architecture_trends` capability with `historical_trends` field
- **Enterprise:** Added `custom_map_metrics` capability with `custom_metrics` field
- **Enterprise:** Added `compliance_overlay` capability integrating with architectural rules engine
- **Documentation:** Updated roadmap to reflect actual implementation fields

---

**Last Updated:** December 31, 2025  
**Next Review:** March 31, 2026
