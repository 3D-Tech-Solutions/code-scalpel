# Feature Extraction Plan - Community/Pro/Enterprise Package Separation

**Status**: 🟢 STRATEGIC PLANNING DOCUMENT
**Created**: January 8, 2026
**Version**: v1.0
**Purpose**: Define exact code extraction strategy for separating Code Scalpel into Community (public) + Pro/Enterprise plugins (private)

---

## 1. Architecture Overview

### Current Architecture (v3.3.0 - Incorrect for Public Release)
```
code-scalpel/
├── src/code_scalpel/
│   ├── licensing/         # License validation infrastructure
│   ├── tiers/             # Tier detection and feature registry
│   └── mcp/               # MCP server with all 22 tools
│       └── tools/         # All tools have PRO/ENTERPRISE code
```

**Problem**: All code visible in public repo, tier enforcement via environment variable.

### Target Architecture (Correct - Package Separation)
```
code-scalpel (Community - MIT, Public)
├── src/code_scalpel/
│   ├── licensing/         # License validation, JWT parser, tier detector
│   ├── tiers/             # Feature registry, tier constants
│   ├── plugins/           # Plugin system infrastructure (NEW)
│   │   ├── registry.py    # FeatureRegistry, FeaturePlugin interface
│   │   └── loader.py      # Plugin discovery and loading
│   └── mcp/
│       ├── server.py      # Initialize with plugin loading (MODIFIED)
│       └── tools/         # Only COMMUNITY tier implementations
│
code-scalpel-pro (Pro - Commercial, Private)
├── setup.py               # Depends on code-scalpel
└── src/code_scalpel_pro/
    ├── __init__.py        # Register Pro features
    └── mcp/
        └── tools/         # Pro implementations for each applicable tool
│
code-scalpel-enterprise (Enterprise - Commercial, Private)
├── setup.py               # Depends on code-scalpel-pro
└── src/code_scalpel_enterprise/
    ├── __init__.py        # Register Enterprise features
    └── mcp/
        └── tools/         # Enterprise implementations for each tool
```

**Advantage**: Clean separation, Pro/Enterprise code never in public repo.

---

## 2. Licensing System Architecture

### Key Components (Remain in Community Package)

#### JWT License Validation (`src/code_scalpel/licensing/jwt_validator.py`)
**Purpose**: Validate cryptographically signed JWT license tokens

**Components**:
- `JWTLicenseValidator` - RS256/HS256 JWT validation
- `JWTLicenseData` - Parsed JWT claims (tier, customer_id, features, expiration)
- Public key embedded: `src/code_scalpel/licensing/public_key/vault-prod-2026-01.pem`

**Claims Structure**:
```json
{
  "tier": "pro|enterprise",
  "sub": "customer_id_12345",
  "iss": "code-scalpel-licensing",
  "aud": "code-scalpel-users",
  "exp": 1735689600,
  "iat": 1704153600,
  "jti": "unique-token-id",
  "nbf": 1767287075,
  "org": "Organization Name",
  "seats": 10,
  "features": ["feature1", "feature2"]
}
```

**Two-Stage Validation**:
1. **Offline** (Always): RSA signature verification using public key
2. **Online** (Every 24h): Remote verifier checks revocation status
   - Grace period: 24h if verifier offline, 48h total

**Location Discovery** (priority order):
1. `CODE_SCALPEL_LICENSE_PATH` env var (explicit override)
2. `.code-scalpel/license/license.jwt` (project location)
3. `~/.config/code-scalpel/license.jwt` (user XDG location)
4. `~/.code-scalpel/license.jwt` (legacy user location)
5. `.scalpel-license` (legacy location)

#### Tier Detector (`src/code_scalpel/licensing/tier_detector.py`)
**Purpose**: Detect current tier from multiple sources

**Detection Priority**:
1. `CODE_SCALPEL_TIER` env var (highest priority)
2. License JWT file (parsed by JWTLicenseValidator)
3. Config file `.code-scalpel/license.json`
4. Organization-based detection (`CODE_SCALPEL_ORGANIZATION`)
5. Default to COMMUNITY (lowest priority)

**Return Value**: `TierDetectionResult` with:
- `tier`: "community", "pro", or "enterprise"
- `source`: Where tier was detected
- `confidence`: 0.0 to 1.0
- `is_validated`: Whether JWT signature was valid

#### License Manager (`src/code_scalpel/licensing/license_manager.py`)
**Purpose**: Centralized license state management

**Key Methods**:
- `validate()` - Full license validation (offline + online)
- `get_current_tier()` - Current tier detection
- `is_feature_available(feature_name)` - Check if feature enabled
- `get_license_info()` - Return license metadata
- `check_expiration()` - Check if license expired (with grace period)

**Caching**:
- In-memory cache: 24h TTL (per JWT spec)
- File cache: `~/.code-scalpel/cache/` for persistence
- Force refresh: `force_refresh=True` param

**Grace Period**:
- Pro/Enterprise: 30-day grace period after expiration
- Enterprise: 7-day grace period (additional for Enterprise)
- Community: No license required

#### Feature Registry (`src/code_scalpel/tiers/feature_registry.py`)
**Purpose**: Central registry of features and tier requirements

**Interface**:
```python
registry = FeatureRegistry()
is_enabled = registry.is_enabled("security_scan")  # Check if available
tier = registry.get_tier("analyze_code")           # Get min required tier
features = registry.get_available_features()       # List all available
unavailable = registry.get_unavailable_features()  # Features requiring upgrade
```

**Feature Definition**:
```python
Feature(
    name="security_scan",
    tier="pro",  # "community", "pro", or "enterprise"
    description="Taint-based vulnerability detection",
    category="security",
    deprecated=False,
    beta=False,
    metadata={"max_findings": "unlimited", "languages": "python|js|ts|java"}
)
```

**Tier Hierarchy**:
- Community < Pro < Enterprise
- Feature available at tier ≥ minimum required tier

### New Plugin System (Remain in Community Package)

#### Plugin Registry (`src/code_scalpel/plugins/registry.py`)
**Purpose**: Central registry for plugin-based feature installation

**Interface**:
```python
class FeaturePlugin:
    """Base class for all feature plugins."""
    
    def register_features(self) -> List[Feature]:
        """Return features provided by this plugin."""
        pass
    
    def register_tools(self) -> List[MCPTool]:
        """Return MCP tools provided by this plugin."""
        pass
    
    def validate_license(self, license_data: JWTLicenseData) -> bool:
        """Check if license tier supports this plugin."""
        pass

class PluginRegistry:
    """Plugin discovery and registration."""
    
    def register_plugin(self, plugin: FeaturePlugin) -> None:
        """Register a plugin at startup."""
        pass
    
    def discover_plugins(self) -> List[FeaturePlugin]:
        """Auto-discover installed plugins."""
        pass
    
    def get_features_by_tier(self, tier: str) -> List[Feature]:
        """Get all available features for a tier."""
        pass
```

**Plugin Discovery Mechanism**:
```python
# In setup.py
entry_points={
    "code_scalpel.plugins": [
        "pro = code_scalpel_pro:ProPlugin",           # Pro tier features
        "enterprise = code_scalpel_enterprise:EnterprisePlugin"  # Enterprise features
    ]
}
```

**MCP Server Initialization** (`src/code_scalpel/mcp/server.py`):
```python
async def initialize_server():
    # Load license and detect tier
    tier = get_current_tier()
    license_data = validate_license()
    
    # Load base Community features
    registry = FeatureRegistry()
    tools = list(COMMUNITY_TOOLS)  # Base 22 tools
    
    # Discover and load plugins based on license tier
    if tier in ("pro", "enterprise"):
        plugins = discover_plugins()
        for plugin in plugins:
            if plugin.validate_license(license_data):
                tools.extend(plugin.register_tools())
                registry.register_features(plugin.register_features())
    
    # Return combined tool set
    return MCP_SERVER(tools)
```

---

## 3. Tool-by-Tool Extraction Strategy

### Tier Levels Reference

| Tier | Features | File Count Limit | Depth Limit | Language Support |
|------|----------|------------------|-------------|------------------|
| **Community** | Base features only | Based on tool | Limited | Python/JS/TS/Java |
| **Pro** | Enhanced analysis, advanced options | 10x Community limit | 5x Community limit | All + semantic analysis |
| **Enterprise** | Unlimited, custom, org-wide | Unlimited | Unlimited | All + formal verification |

---

## 4. Analysis Tools - Extraction Detail

### Tool 1: `analyze_code` (Analysis)

**Community Tier**:
- Parse Python/JavaScript/TypeScript/Java
- Extract: functions, classes, imports, complexity metrics
- Max file size: 1MB
- Output: Flat structure (no cross-file analysis)
- **Location**: `src/code_scalpel/analysis/code_parser.py` (STAYS in Community)

**Pro Tier** (NEW - Add in plugin):
- Code smell detection
- Advanced metrics: cyclomatic complexity, depth
- Integration with code policies
- **Location**: `code_scalpel_pro/analysis/code_smell_detector.py` (NEW in Pro plugin)

**Enterprise Tier** (NEW - Add in plugin):
- Custom analyzer definitions
- Parallel analysis of entire codebases
- AST customization hooks
- **Location**: `code_scalpel_enterprise/analysis/custom_analyzer.py` (NEW in Enterprise plugin)

**Extraction Rule**: 
- Keep `_parse_code()`, `get_ast()`, `extract_structure()` in Community
- Move `detect_smells()`, `calculate_metrics()` to Pro plugin (depends on Community)
- Move `custom_analyzer_api` to Enterprise plugin

---

### Tool 2: `code_policy_check` (Governance)

**Community Tier**:
- Basic style rule validation (Python PEP8, JavaScript standard style)
- Rule discovery from built-in rules
- Max 50 rules to check
- **Location**: `src/code_scalpel/governance/policy_rules.py` (STAYS)

**Pro Tier** (NEW - Add in plugin):
- Custom rule definitions
- Compliance rule templates (HIPAA, GDPR, SOC2)
- Team-level policy enforcement
- **Location**: `code_scalpel_pro/governance/custom_rules.py` (NEW)

**Enterprise Tier** (NEW - Add in plugin):
- Compliance auditing and reporting
- Policy change history and approval workflows
- Enterprise-wide policy inheritance
- **Location**: `code_scalpel_enterprise/governance/compliance_audit.py` (NEW)

**Extraction Rule**:
- Keep built-in PEP8/Eslint rules in Community
- Move rule customization/generation to Pro
- Move compliance auditing to Enterprise

---

### Tool 3: `crawl_project` (Analysis)

**Community Tier**:
- Single-threaded project crawl
- Max 100 files per analysis
- File pattern matching (glob)
- Python file analysis only
- **Location**: `src/code_scalpel/project/crawler.py` (STAYS)

**Pro Tier** (NEW):
- Parallel multi-threaded crawling
- Max unlimited files
- All language support
- Caching of analysis results
- **Location**: `code_scalpel_pro/project/parallel_crawler.py` (NEW)

**Enterprise Tier** (NEW):
- Distributed crawling across machines
- Real-time incremental updates
- Compliance validation during crawl
- **Location**: `code_scalpel_enterprise/project/distributed_crawler.py` (NEW)

**Extraction Rule**:
- Keep `Crawler` class and single-threaded impl in Community
- Move `ParallelCrawler` to Pro
- Move `DistributedCrawler` to Enterprise

---

### Tool 4: `cross_file_security_scan` (Security)

**Community Tier**:
- Taint tracking: depth=3 max
- Module limit: 10 files max
- Python only
- Basic sinks: SQL injection, Command injection, Path traversal
- **Location**: `src/code_scalpel/security/taint_tracker.py` (STAYS, limited impl)

**Pro Tier** (NEW):
- Depth limit: 10
- Module limit: 100 files
- Multi-language (JS/TS)
- Additional sinks: NoSQL, LDAP, CSRF, SSRF
- **Location**: `code_scalpel_pro/security/advanced_taint_tracker.py` (NEW)

**Enterprise Tier** (NEW):
- Unlimited depth and modules
- All languages + custom sinks
- Formal verification of taint flows
- **Location**: `code_scalpel_enterprise/security/formal_taint_analysis.py` (NEW)

**Extraction Rule**:
- Keep `TaintTracker` base class in Community (limited to depth=3)
- Extract Pro enhancements to Pro plugin (override depth limit)
- Extract Enterprise capabilities to Enterprise plugin

---

### Tool 5: `extract_code` (Surgery)

**Community Tier**:
- Single symbol extraction (function/class/method)
- By symbol name only
- Same file only, no cross-file dependencies
- Include function body + immediate context
- **Location**: `src/code_scalpel/surgery/code_extractor.py` (STAYS)

**Pro Tier** (NEW):
- Cross-file dependency resolution
- Dependency injection suggestions
- Microservice packaging (extract as runnable module)
- Closure detection
- **Location**: `code_scalpel_pro/surgery/cross_file_extractor.py` (NEW)

**Enterprise Tier** (NEW):
- Organization-wide extraction (find same symbol across repos)
- Custom microservice scaffolding
- Dependency graph visualization
- **Location**: `code_scalpel_enterprise/surgery/org_extractor.py` (NEW)

**Extraction Rule**:
- Keep basic symbol extraction in Community
- Move `get_cross_file_dependencies()` to Pro
- Move `get_org_wide_references()` to Enterprise
- Keep shared util `_parse_symbol_name()` in Community

---

### Tool 6: `generate_unit_tests` (Testing)

**Community Tier**:
- Symbolic execution for test generation
- Max 5 test cases per function
- pytest only (no unittest)
- Int/Bool/String/Float types only
- Loop depth: 10 max
- **Location**: `src/code_scalpel/testing/test_generator.py` (STAYS)

**Pro Tier** (NEW):
- Data-driven/parametrized tests
- Max 20 test cases
- unittest + pytest support
- Complex types (List, Dict, custom classes)
- Loop depth: 100
- **Location**: `code_scalpel_pro/testing/advanced_test_generator.py` (NEW)

**Enterprise Tier** (NEW):
- Unlimited test cases
- Bug reproduction from crash logs
- Formal verification of test coverage
- Custom framework support
- **Location**: `code_scalpel_enterprise/testing/formal_test_generator.py` (NEW)

**Extraction Rule**:
- Keep basic symbolic execution in Community
- Move parametrization logic to Pro
- Move crash log parsing + formal verification to Enterprise

---

### Tool 7: `get_call_graph` (Analysis)

**Community Tier**:
- Call graph up to depth=3
- Max 50 nodes
- Single language (Python)
- Text output format only
- **Location**: `src/code_scalpel/analysis/call_graph.py` (STAYS)

**Pro Tier** (NEW):
- Depth up to 50
- Max 500 nodes
- Multi-language (JS/TS/Java)
- Mermaid diagram generation
- Hot path detection
- **Location**: `code_scalpel_pro/analysis/advanced_call_graph.py` (NEW)

**Enterprise Tier** (NEW):
- Unlimited depth/nodes
- Custom graph queries
- Performance bottleneck detection
- **Location**: `code_scalpel_enterprise/analysis/enterprise_call_graph.py` (NEW)

---

### Tool 8: `get_cross_file_dependencies` (Analysis)

**Community Tier**:
- Analyze imports up to depth=1
- Max 50 files
- Basic import resolution (Python imports)
- Confidence scoring: Basic (valid/missing only)
- **Location**: `src/code_scalpel/analysis/dependency_analyzer.py` (STAYS)

**Pro Tier** (NEW):
- Depth up to 5
- Max 500 files
- Multi-language imports
- Confidence scoring: Advanced (by analysis method)
- Circular dependency detection
- **Location**: `code_scalpel_pro/analysis/advanced_dependency_analyzer.py` (NEW)

**Enterprise Tier** (NEW):
- Unlimited depth/files
- Architectural firewall enforcement
- Custom dependency rules
- **Location**: `code_scalpel_enterprise/analysis/architectural_analyzer.py` (NEW)

---

### Tool 9: `get_file_context` (Analysis)

**Community Tier**:
- Max 20 imports to list
- Security warnings only (no quality metrics)
- Max 500 line preview
- Python file context only
- **Location**: `src/code_scalpel/analysis/file_context.py` (STAYS)

**Pro Tier** (NEW):
- Semantic summarization of file purpose
- Max 2000 line preview
- All languages
- Complexity metrics
- **Location**: `code_scalpel_pro/analysis/semantic_context.py` (NEW)

**Enterprise Tier** (NEW):
- Quality metrics (maintainability index, technical debt)
- Compliance flags per file
- Risk scoring
- **Location**: `code_scalpel_enterprise/analysis/enterprise_context.py` (NEW)

---

### Tool 10: `get_graph_neighborhood` (Analysis)

**Community Tier**:
- K-hop neighborhood: k=1 only
- Max 50 nodes in neighborhood
- Truncation detection
- Mermaid diagram generation
- **Location**: `src/code_scalpel/analysis/graph_neighborhood.py` (STAYS)

**Pro Tier** (NEW):
- K up to 5 hops
- Max 500 nodes
- Semantic neighbors (imports, calls, data flow)
- Direction filtering
- **Location**: `code_scalpel_pro/analysis/advanced_neighborhood.py` (NEW)

**Enterprise Tier** (NEW):
- Unlimited k hops
- Graph query language (GQL)
- Custom traversal rules
- **Location**: `code_scalpel_enterprise/analysis/graph_query_engine.py` (NEW)

---

### Tool 11: `get_project_map` (Analysis)

**Community Tier**:
- Package hierarchy only
- Complexity scoring (basic LOC/functions)
- Text output
- **Location**: `src/code_scalpel/analysis/project_map.py` (STAYS)

**Pro Tier** (NEW):
- Architecture pattern detection (MVC, microservices, etc.)
- City map visualization (3D-like ASCII diagram)
- Module relationship graph
- **Location**: `code_scalpel_pro/analysis/architecture_map.py` (NEW)

**Enterprise Tier** (NEW):
- Compliance validation during mapping
- Technical debt scoring
- Custom architecture rules
- **Location**: `code_scalpel_enterprise/analysis/enterprise_map.py` (NEW)

---

### Tool 12: `get_symbol_references` (Analysis)

**Community Tier**:
- Find references up to 10 files
- Python only
- No risk scoring
- **Location**: `src/code_scalpel/analysis/symbol_references.py` (STAYS)

**Pro Tier** (NEW):
- Unlimited file search
- Multi-language (JS/TS/Java/Python)
- Reference categorization (import/call/type annotation)
- **Location**: `code_scalpel_pro/analysis/advanced_references.py` (NEW)

**Enterprise Tier** (NEW):
- Risk scoring (breaking change impact)
- CODEOWNERS-based ownership attribution
- Custom reference filters
- **Location**: `code_scalpel_enterprise/analysis/enterprise_references.py` (NEW)

---

## 5. Surgery Tools - Extraction Detail

### Tool 13: `rename_symbol` (Surgery)

**Community Tier**:
- Rename within same file only
- No dependency tracking
- **Location**: `src/code_scalpel/surgery/renamer.py` (STAYS)

**Pro Tier** (NEW):
- Cross-file renames (updates all references)
- Batch rename operations
- Dependency checking before rename
- **Location**: `code_scalpel_pro/surgery/advanced_renamer.py` (NEW)

**Enterprise Tier** (NEW):
- Audit trail of all renames
- Breaking change detection
- Team coordination hooks
- **Location**: `code_scalpel_enterprise/surgery/enterprise_renamer.py` (NEW)

---

### Tool 14: `update_symbol` (Surgery)

**Community Tier**:
- Single symbol replacement
- Automatic backup creation
- Syntax validation
- **Location**: `src/code_scalpel/surgery/code_updater.py` (STAYS)

**Pro Tier** (NEW):
- Multi-file atomic updates
- Transactional updates
- Policy enforcement during updates
- **Location**: `code_scalpel_pro/surgery/advanced_updater.py` (NEW)

**Enterprise Tier** (NEW):
- Full audit trail
- Team coordination (locking, approval)
- Policy enforcement with history
- **Location**: `code_scalpel_enterprise/surgery/enterprise_updater.py` (NEW)

---

## 6. Security Tools - Extraction Detail

### Tool 15: `scan_dependencies` (Security)

**Community Tier**:
- CVE scanning (max 50 dependencies)
- OSV API integration
- **Location**: `src/code_scalpel/security/dependency_scanner.py` (STAYS)

**Pro Tier** (NEW):
- Unlimited dependencies
- License scanning (compliance)
- Supply chain risk analysis
- **Location**: `code_scalpel_pro/security/advanced_dependency_scanner.py` (NEW)

**Enterprise Tier** (NEW):
- SBOM generation
- Real-time threat intelligence
- Custom security policies
- **Location**: `code_scalpel_enterprise/security/sbom_generator.py` (NEW)

---

### Tool 16: `security_scan` (Security)

**Community Tier**:
- Taint analysis (basic)
- Max 50 findings
- Basic sinks: SQL injection, XSS, Command injection, Path traversal
- Python only
- **Location**: `src/code_scalpel/security/security_scanner.py` (STAYS)

**Pro Tier** (NEW):
- Unlimited findings
- Advanced sinks: NoSQL injection, LDAP injection, CSRF, SSRF, Secret detection
- Multi-language
- Confidence scoring
- Context-aware analysis
- **Location**: `code_scalpel_pro/security/advanced_scanner.py` (NEW)

**Enterprise Tier** (NEW):
- Custom vulnerability definitions
- Organization-specific sinks
- Compliance rule integration
- Formal verification of fixes
- **Location**: `code_scalpel_enterprise/security/enterprise_scanner.py` (NEW)

---

### Tool 17: `simulate_refactor` (Surgery/Testing)

**Community Tier**:
- Basic refactor verification
- Syntax checking only
- **Location**: `src/code_scalpel/surgery/refactor_simulator.py` (STAYS)

**Pro Tier** (NEW):
- Code smell detection before/after
- Performance impact estimation
- **Location**: `code_scalpel_pro/surgery/advanced_refactor_simulator.py` (NEW)

**Enterprise Tier** (NEW):
- Full behavioral analysis
- Rollback strategy generation
- Policy violation detection
- **Location**: `code_scalpel_enterprise/surgery/enterprise_refactor_simulator.py` (NEW)

---

### Tool 18: `symbolic_execute` (Analysis/Testing)

**Community Tier**:
- Z3-based symbolic execution
- Max 50 execution paths
- Loop fuel: 10 max
- Supported types: Int, Bool, String, Float
- **Location**: `src/code_scalpel/symbolic_execution_tools/` (STAYS)

**Pro Tier** (NEW):
- Unlimited execution paths
- Loop fuel: 100
- Additional types: List, Dict
- Concolic execution (hybrid concrete + symbolic)
- Path prioritization (crash-triggering)
- **Location**: `code_scalpel_pro/symbolic_execution_tools/` (NEW)

**Enterprise Tier** (NEW):
- Unbounded execution (no path limits)
- Custom constraint solvers
- Formal verification integration
- **Location**: `code_scalpel_enterprise/symbolic_execution_tools/` (NEW)

---

### Tool 19: `type_evaporation_scan` (Security/TypeScript)

**Community Tier**:
- Frontend-only analysis
- Max 50 files
- Explicit any detection (not implicit)
- TypeScript/JavaScript
- **Location**: `src/code_scalpel/security/type_evaporation.py` (STAYS)

**Pro Tier** (NEW):
- Frontend + backend correlation
- Implicit any detection
- Network boundary analysis (fetch, axios, XMLHttpRequest)
- Library boundary tracking (localStorage, postMessage)
- **Location**: `code_scalpel_pro/security/advanced_type_evaporation.py` (NEW)

**Enterprise Tier** (NEW):
- Zod schema generation for TypeScript
- Pydantic model generation for Python
- API contract validation
- Schema coverage metrics
- **Location**: `code_scalpel_enterprise/security/schema_validator.py` (NEW)

---

### Tool 20: `unified_sink_detect` (Security)

**Community Tier**:
- Polyglot sink detection (Python/Java/JS/TS)
- CWE mapping
- Min confidence: 0.7
- **Location**: `src/code_scalpel/security/sink_detector.py` (STAYS)

**Pro Tier** (NEW):
- Confidence scoring (0.0-1.0)
- Context-aware sinks
- Custom sink patterns per organization
- **Location**: `code_scalpel_pro/security/advanced_sink_detector.py` (NEW)

**Enterprise Tier** (NEW):
- Organization-specific sink rules
- Custom vulnerability definitions
- Integration with enterprise SIEM
- **Location**: `code_scalpel_enterprise/security/enterprise_sinks.py` (NEW)

---

## 7. Governance Tools - Extraction Detail

### Tool 21: `validate_paths` (Utilities)

**Status**: Same across all tiers
- Path accessibility checking
- Docker environment detection
- Batch validation
- **Location**: `src/code_scalpel/utilities/path_validator.py` (STAYS in Community)

---

### Tool 22: `verify_policy_integrity` (Governance)

**Community Tier**:
- Basic HMAC-SHA256 verification
- Detects tampering
- **Location**: `src/code_scalpel/governance/policy_verifier.py` (STAYS)

**Pro Tier** (NEW):
- Certificate chain verification
- Key rotation support
- CRL (Certificate Revocation List) checking
- **Location**: `code_scalpel_pro/governance/advanced_verifier.py` (NEW)

**Enterprise Tier** (NEW):
- Custom Certificate Authorities (CA)
- Hardware Security Module (HSM) support
- Multi-tenant policy isolation
- Real-time revocation checking
- **Location**: `code_scalpel_enterprise/governance/enterprise_verifier.py` (NEW)

---

## 8. Shared Utilities - Classification

### Utilities Staying in Community (Shared Foundation)

```python
# Core analysis utilities
src/code_scalpel/analysis/
├── ast_parser.py           # Python AST parsing (shared)
├── pdg_builder.py          # Program Dependency Graph (shared)
├── pdg_analyzer.py         # PDG analysis (shared)
└── pdg_slicer.py           # PDG slicing (shared)

# Core licensing/tier infrastructure
src/code_scalpel/licensing/
├── jwt_validator.py        # JWT validation (shared)
├── tier_detector.py        # Tier detection (shared)
├── license_manager.py      # License state (shared)
└── features.py             # Feature registry (shared)

# Plugin system
src/code_scalpel/plugins/
├── registry.py             # Plugin registry (shared)
├── loader.py               # Plugin loader (shared)
└── interfaces.py           # Plugin interfaces (shared)

# Common utilities
src/code_scalpel/utilities/
├── cache.py                # Unified cache (shared)
├── logger.py               # Logging (shared)
├── exceptions.py           # Exception types (shared)
└── validators.py           # Shared validation logic
```

### Utilities Moving to Pro Plugin

```python
# Advanced analysis (requires Pro)
code_scalpel_pro/analysis/
├── advanced_ast.py         # Extended AST analysis
├── semantic_analyzer.py    # Semantic analysis
└── cache_optimizer.py      # Optimized caching

# Advanced security (requires Pro)
code_scalpel_pro/security/
├── confidence_scorer.py    # Vulnerability confidence scoring
├── context_analyzer.py     # Contextual analysis
└── pattern_matcher.py      # Advanced pattern matching
```

### Utilities Moving to Enterprise Plugin

```python
# Enterprise-grade tools
code_scalpel_enterprise/analysis/
├── formal_verifier.py      # Formal verification
├── performance_analyzer.py # Performance analysis
└── compliance_checker.py   # Compliance checking

# Enterprise infrastructure
code_scalpel_enterprise/infrastructure/
├── distributed_cache.py    # Distributed caching
├── audit_logger.py         # Audit logging
└── hsm_interface.py        # HSM integration
```

---

## 9. Interface Contracts Between Packages

### Community Package Exports (Public API)

```python
# licensing module
from code_scalpel.licensing import (
    get_current_tier,              # () -> "community"|"pro"|"enterprise"
    validate_license,              # (path?) -> ValidationResult
    get_license_info,              # () -> dict
    JWTLicenseValidator,           # Class
    JWTLicenseData,                # Class
)

# tiers module
from code_scalpel.tiers import (
    FeatureRegistry,               # Class
    Feature,                       # Class
    TIER_LEVELS,                   # Dict[str, int]
)

# plugins module
from code_scalpel.plugins import (
    FeaturePlugin,                 # Abstract base class
    PluginRegistry,                # Class
)

# MCP server
from code_scalpel.mcp.server import (
    initialize_server,             # async () -> MCPServer
    register_tool,                 # (MCPTool) -> None
)
```

### Pro Plugin Interface (code_scalpel_pro)

```python
# setup.py entry point
[options.entry_points]
code_scalpel.plugins =
    pro = code_scalpel_pro:ProFeaturePlugin

# code_scalpel_pro/__init__.py
class ProFeaturePlugin(FeaturePlugin):
    def register_features(self) -> List[Feature]:
        """Return Pro-specific features."""
        return [
            Feature("advanced_analysis", "pro", ...),
            Feature("enterprise_integration", "pro", ...),
        ]
    
    def register_tools(self) -> List[MCPTool]:
        """Return Pro MCP tools."""
        return [
            # Tool overrides with Pro features enabled
        ]
    
    def validate_license(self, license: JWTLicenseData) -> bool:
        """Check if license includes Pro features."""
        return "pro" in (license.tier,)
```

### Enterprise Plugin Interface (code_scalpel_enterprise)

```python
# setup.py entry point
[options.entry_points]
code_scalpel.plugins =
    enterprise = code_scalpel_enterprise:EnterpriseFeaturePlugin

# code_scalpel_enterprise/__init__.py
class EnterpriseFeaturePlugin(FeaturePlugin):
    def register_features(self) -> List[Feature]:
        """Return Enterprise-specific features."""
        return [
            Feature("formal_verification", "enterprise", ...),
            Feature("hsm_support", "enterprise", ...),
        ]
    
    def register_tools(self) -> List[MCPTool]:
        """Return Enterprise MCP tools."""
        return [
            # Tool overrides with Enterprise features enabled
        ]
    
    def validate_license(self, license: JWTLicenseData) -> bool:
        """Check if license includes Enterprise features."""
        return license.tier == "enterprise"
```

---

## 10. Extraction Sequence (Step-by-Step)

### Phase 1: Plugin System Implementation (Community Package)
**Priority**: P0 - Must complete first

1. Create `src/code_scalpel/plugins/registry.py`
   - `FeaturePlugin` abstract base class
   - `PluginRegistry` implementation
   - Plugin discovery via entry points

2. Create `src/code_scalpel/plugins/loader.py`
   - `load_plugins()` - Discover via pkg_resources
   - `validate_plugin()` - Check tier compatibility
   - Error handling for missing plugins

3. Update `src/code_scalpel/mcp/server.py`
   - Call `load_plugins()` at startup
   - Merge plugin tools with base tools
   - Validate license before loading plugins

4. Create integration tests
   - Test plugin discovery
   - Test license validation before loading
   - Test graceful fallback if plugin missing

### Phase 2: Extract Community Code (Community Package)
**Priority**: P1 - Extract base implementations

1. Identify all `COMMUNITY` tier code
   - Mark with `# [COMMUNITY TIER]` comment
   - Verify no Pro/Enterprise imports
   - Create isolated unit tests

2. Remove Pro/Enterprise code from tools
   - Delete Pro-specific parameters
   - Delete Enterprise-specific logic branches
   - Keep stubs with "upgrade to Pro" messages

3. Refactor for plugin compatibility
   - Replace `if tier == "pro"` checks with plugin registration
   - Use FeatureRegistry for feature checks
   - Document expected plugin behavior

4. Run tests
   - Verify Community-only functionality works
   - Test graceful degradation
   - Test missing plugin scenarios

### Phase 3: Create Pro Plugin Package (Private Repo)
**Priority**: P2 - Pro tier features

1. Initialize `code_scalpel_pro` package
   - Create setup.py with `install_requires=['code-scalpel>=3.4.0']`
   - Create plugin entrypoint definition
   - Create `src/code_scalpel_pro/__init__.py`

2. Extract Pro implementations
   - Copy Pro-marked code from Community tools
   - Create tool overrides that extend Community implementations
   - Add Pro-specific parameters and features

3. Implement plugin interface
   ```python
   class ProPlugin(FeaturePlugin):
       def register_features(self):
           return [
               Feature("advanced_analysis", "pro", ...),
               # ... all Pro features
           ]
       
       def register_tools(self):
           # Return tool implementations with Pro features
           return [
               analyze_code_pro,  # Override base tool
               # ...
           ]
   ```

4. Test with license validation
   - Create test Pro license
   - Test plugin loading with Pro license
   - Test feature availability
   - Test graceful degradation without license

### Phase 4: Create Enterprise Plugin Package (Private Repo)
**Priority**: P3 - Enterprise tier features

1. Initialize `code_scalpel_enterprise` package
   - Create setup.py with `install_requires=['code-scalpel-pro>=3.4.0']`
   - Create plugin entrypoint definition
   - Create `src/code_scalpel_enterprise/__init__.py`

2. Extract Enterprise implementations
   - Copy Enterprise-marked code
   - Create tool overrides that extend Pro implementations
   - Add Enterprise-specific parameters and features

3. Implement plugin interface
   ```python
   class EnterprisePlugin(FeaturePlugin):
       def register_features(self):
           return [
               Feature("formal_verification", "enterprise", ...),
               # ... all Enterprise features
           ]
       
       def register_tools(self):
           # Return tool implementations with Enterprise features
           return [
               analyze_code_enterprise,  # Override Pro tool
               # ...
           ]
   ```

4. Test with license validation
   - Create test Enterprise license
   - Test plugin loading with Enterprise license
   - Test feature availability
   - Test hierarchical plugin loading (Pro + Enterprise)

### Phase 5: Publish Packages
**Priority**: P4 - Public release

1. Community package
   - `pip install code-scalpel` (public PyPI)
   - MIT license
   - Full documentation

2. Pro package
   - `pip install code-scalpel-pro` (private PyPI/repo)
   - Commercial license
   - Requires valid Pro license at runtime

3. Enterprise package
   - `pip install code-scalpel-enterprise` (private PyPI/repo)
   - Commercial license
   - Requires valid Enterprise license at runtime

---

## 11. Migration Example: `security_scan` Tool

### Current Implementation (v3.3.0 - All in one package)

```python
# src/code_scalpel/security/security_scanner.py

def scan(code: str, tier: str = "community") -> SecurityResult:
    """Main scanning function."""
    result = SecurityResult()
    
    # Community tier: Basic sinks
    if True:  # Always run
        result.findings.extend(_find_sql_injection(code))
        result.findings.extend(_find_xss(code))
        result.findings.extend(_find_command_injection(code))
    
    # Pro tier: Advanced sinks
    if tier in ("pro", "enterprise"):
        result.findings.extend(_find_nosql_injection(code))
        result.findings.extend(_find_ldap_injection(code))
        result.findings.extend(_find_secret_keys(code))
    
    # Enterprise tier: Custom rules
    if tier == "enterprise":
        result.findings.extend(_apply_custom_rules(code))
        result.findings.extend(_apply_compliance_checks(code))
    
    return result
```

### Target Implementation (After Extraction)

**Community Package** (`src/code_scalpel/security/security_scanner.py`):
```python
def scan(code: str) -> SecurityResult:
    """Community tier: Basic vulnerability detection."""
    result = SecurityResult()
    
    # Community tier: Only basic sinks
    result.findings.extend(_find_sql_injection(code))
    result.findings.extend(_find_xss(code))
    result.findings.extend(_find_command_injection(code))
    result.findings.extend(_find_path_traversal(code))
    
    # Limit to first 50 findings
    result.findings = result.findings[:50]
    
    return result
```

**Pro Plugin** (`code_scalpel_pro/security/advanced_security_scanner.py`):
```python
class ProSecurityScanner(FeaturePlugin):
    def register_tools(self) -> List[MCPTool]:
        return [scan_advanced]
    
    def register_features(self) -> List[Feature]:
        return [
            Feature("nosql_injection_detection", "pro", ...),
            Feature("ldap_injection_detection", "pro", ...),
            Feature("secret_detection", "pro", ...),
        ]

def scan_advanced(code: str) -> SecurityResult:
    """Pro tier: Community findings + advanced sinks."""
    # Get base findings from Community
    result = security_scanner.scan(code)
    
    # Add Pro-tier findings
    result.findings.extend(_find_nosql_injection(code))
    result.findings.extend(_find_ldap_injection(code))
    result.findings.extend(_find_secret_keys(code))
    result.findings.extend(_find_csrf_issues(code))
    result.findings.extend(_find_ssrf_issues(code))
    
    # No limit on findings in Pro
    
    return result
```

**Enterprise Plugin** (`code_scalpel_enterprise/security/enterprise_security_scanner.py`):
```python
class EnterpriseSecurityScanner(FeaturePlugin):
    def register_tools(self) -> List[MCPTool]:
        return [scan_enterprise]
    
    def register_features(self) -> List[Feature]:
        return [
            Feature("custom_vulnerability_rules", "enterprise", ...),
            Feature("compliance_scanning", "enterprise", ...),
        ]

def scan_enterprise(code: str, custom_rules: Dict = None) -> SecurityResult:
    """Enterprise tier: All features + custom rules."""
    # Get Pro findings
    result = advanced_security_scanner.scan_advanced(code)
    
    # Add Enterprise: Custom rules
    if custom_rules:
        result.findings.extend(_apply_custom_rules(code, custom_rules))
        result.findings.extend(_apply_compliance_checks(code))
    
    return result
```

**MCP Tool Definition** (stays the same across tiers):
```python
# src/code_scalpel/mcp/tools/security_scan.py
security_scan_tool = MCPTool(
    name="security_scan",
    schema=SecurityScanSchema,
    handler=_dispatch_to_tier,  # Route to Community/Pro/Enterprise
)

def _dispatch_to_tier(code: str, **kwargs):
    """Route to appropriate implementation based on license tier."""
    tier = get_current_tier()
    
    if tier == "enterprise":
        return enterprise_security_scanner.scan_enterprise(code, **kwargs)
    elif tier == "pro":
        return advanced_security_scanner.scan_advanced(code, **kwargs)
    else:
        return security_scanner.scan(code)
```

---

## 12. Dependency Graph

### Community Package Dependencies
```
code-scalpel (root)
├── PyJWT[crypto]           # License validation
├── cryptography            # RSA signature verification
└── Z3-solver              # Symbolic execution (optional for Community tier)
```

### Pro Package Dependencies
```
code-scalpel-pro
├── code-scalpel            # Base package
├── scikit-learn           # Advanced metrics
└── networkx               # Graph analysis
```

### Enterprise Package Dependencies
```
code-scalpel-enterprise
├── code-scalpel-pro       # Includes code-scalpel transitively
├── Z3-solver              # Formal verification
└── pydantic               # Schema validation
```

---

## 13. Testing Strategy

### Community Tier Tests (Remain in main repo)
```python
# tests/tools/community/
├── test_analyze_code.py
├── test_extract_code.py
├── test_security_scan_community.py
└── ... (all 22 tools, Community features only)
```

### Pro Tier Tests (In Pro plugin repo)
```python
# tests/tools/pro/
├── test_advanced_analysis.py
├── test_advanced_security.py
└── ... (Pro-specific features)
```

### Enterprise Tier Tests (In Enterprise plugin repo)
```python
# tests/tools/enterprise/
├── test_formal_verification.py
├── test_enterprise_security.py
└── ... (Enterprise-specific features)
```

### Integration Tests (Community repo)
```python
# tests/integration/
├── test_plugin_loading.py          # Load plugins
├── test_license_validation.py       # Validate licenses
├── test_feature_gating.py           # Feature availability per tier
└── test_graceful_degradation.py     # Work without Pro/Enterprise plugins
```

---

## 14. Documentation Requirements

### Community Package (Public)
- README: Feature overview, installation, Community tier usage
- USAGE.md: Examples of Community features
- API_REFERENCE.md: All Community tool documentation
- UPGRADING.md: How to upgrade to Pro/Enterprise
- LICENSE: MIT license

### Pro Package (Private)
- README: Pro-specific features
- INSTALLATION.md: How to install with Pro license
- API_REFERENCE.md: Pro tool enhancements
- PRICING.md: Pro tier pricing

### Enterprise Package (Private)
- README: Enterprise features
- INSTALLATION.md: Enterprise deployment guide
- API_REFERENCE.md: Enterprise tool features
- SLA.md: Service-level agreements

---

## 15. Timeline for Implementation

**Week 1 (Jan 13-17)**: Plugin system implementation
- Day 1-2: Design review, finalize interfaces
- Day 3-4: Implement plugin registry & loader
- Day 5: Integration tests, documentation

**Week 2 (Jan 20-24)**: Extract Community code
- Day 1-2: Mark all code with tier comments
- Day 3: Remove Pro/Enterprise code from tools
- Day 4: Refactor for plugin compatibility
- Day 5: Full test suite validation

**Week 3 (Jan 27-31)**: Create Pro package
- Day 1-2: Initialize repo, setup.py
- Day 3-4: Extract Pro implementations
- Day 5: Pro plugin tests, documentation

**Week 4 (Feb 3-7)**: Create Enterprise package
- Day 1-2: Initialize repo, setup.py
- Day 3-4: Extract Enterprise implementations
- Day 5: Enterprise tests, documentation

**Week 5 (Feb 10-14)**: Public release preparation
- Day 1-2: Final testing, license validation
- Day 3: Publish Community to public PyPI
- Day 4: Announce on GitHub, ProductHunt
- Day 5: Monitor adoption, fix issues

---

## 16. Success Criteria

✅ **Code Organization**
- [ ] All 22 tools have clean Community/Pro/Enterprise separation
- [ ] No Pro/Enterprise code visible in public repo
- [ ] Plugin system working for all tools
- [ ] Interface contracts stable and documented

✅ **Licensing Integration**
- [ ] JWT validation working correctly
- [ ] License detection from all 5 locations
- [ ] Plugin loading based on license tier
- [ ] Graceful degradation without plugins

✅ **Testing**
- [ ] All Community tier tests passing (4,700+ tests)
- [ ] Pro tier tests passing (500+ tests)
- [ ] Enterprise tier tests passing (500+ tests)
- [ ] Integration tests for plugin loading (50+ tests)
- [ ] Overall coverage ≥ 90%

✅ **Documentation**
- [ ] Public README for Community tier
- [ ] API reference for all Community tools
- [ ] Upgrade guide (Community → Pro → Enterprise)
- [ ] Private docs for Pro/Enterprise packages

✅ **Public Release**
- [ ] Community package on public PyPI
- [ ] GitHub repo public with MIT license
- [ ] No Pro/Enterprise code exposed
- [ ] License validation prevents feature access

---

## 17. Risk Mitigation

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|-----------|
| Plugin loading fails silently | Medium | High | Comprehensive logging, test coverage, clear error messages |
| License validation bypass | Low | Critical | JWT signature verification, offline detection, rate limiting |
| Missing shared utility breaks Pro | Medium | Medium | Explicit interface contracts, stability tests, gradual rollout |
| Version compatibility issues | High | Low | Pinned dependency versions, semantic versioning, test matrix |
| Circular imports in plugins | Medium | Medium | Clear import boundaries, dependency injection, layer validation |

---

## Conclusion

This feature extraction plan enables Code Scalpel to:

1. **Maintain MIT open-source Community tier** - All base functionality public
2. **Protect commercial code** - Pro/Enterprise never exposed in public repo
3. **Scale revenue** - Clean plugin system enables easy upselling
4. **Maintain quality** - Strong interface contracts, comprehensive testing
5. **Support customers** - Clear license validation, graceful degradation

The plugin architecture is production-ready and has been proven in other successful open-core projects (Terraform, HashiCorp, Databricks, etc.).

**Next Steps**: 
1. Review this plan with stakeholders
2. Create plugin system (Week 1)
3. Extract code (Weeks 2-4)
4. Publish packages (Week 5)
5. Execute Week 1 launch plan (Jan 6-12 already underway)
