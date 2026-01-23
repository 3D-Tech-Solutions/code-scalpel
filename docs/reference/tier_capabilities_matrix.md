# Tier Capabilities Matrix

[20251225_DOCS] Comprehensive reference showing what each tier gets for each of the 20 MCP tools.

## Overview

**Key Principle**: All 20 tools are available at all tiers. What differs is the **depth, scale, and advanced features** within each tool.

- **COMMUNITY**: Full functionality for small-scale use cases, basic features
- **PRO**: Removes limits, adds advanced analysis capabilities
- **ENTERPRISE**: Adds organization-wide features, compliance, custom integrations

---

## Quick Reference

| Tool | Community Limits | Pro Unlocks | Enterprise Adds |
|------|------------------|-------------|-----------------|
| `security_scan` | 10 findings max | Unlimited + remediation | Compliance + custom rules |
| `symbolic_execute` | 3 paths | 10 paths | Unlimited paths |
| `crawl_project` | 100 files, discovery | 1000 files, deep parse | Unlimited + org indexing |
| `extract_code` | Single-file only | Cross-file deps (depth 1) | Unlimited depth |
| `generate_unit_tests` | 5 tests | 20 tests | Unlimited + coverage |
| `get_call_graph` | 3 hops | 10 hops | Unlimited depth |
| `get_graph_neighborhood` | k=1, 50 nodes | k=2, 100 nodes | Unlimited |
| `scan_dependencies` | 50 deps | Unlimited | + Auto-remediation |
| `get_cross_file_dependencies` | depth=1 | depth=3 | Unlimited depth |
| `cross_file_security_scan` | depth=2, 50 modules | depth=5, 500 modules | Unlimited |
| `rename_symbol` | Definition rename only | + Cross-file reference/import updates (bounded) | + Org-wide/unlimited scope |

All other tools: **Fully available at all tiers** (no restrictions).

---

## Detailed Capability Matrix

### 1. `analyze_code` - Code Structure Analysis

**Purpose**: Parse and extract code structure (functions, classes, imports)

| Capability | Community | Pro | Enterprise |
|------------|-----------|-----|------------|
| **Availability** | ✅ | ✅ | ✅ |
| Languages | Python, JS, TS, Java | Python, JS, TS, Java | Python, JS, TS, Java |
| AST parsing | ✅ | ✅ | ✅ |
| Complexity metrics | ✅ | ✅ | ✅ |
| **Restrictions** | None | None | None |

**Summary**: Fully available at all tiers with no restrictions.

---

### 2. `extract_code` - Surgical Code Extraction

**Purpose**: Extract functions/classes/methods by name with dependencies

| Capability | Community | Pro | Enterprise |
|------------|-----------|-----|------------|
| **Availability** | ✅ | ✅ | ✅ |
| Single-file extraction | ✅ | ✅ | ✅ |
| Cross-file dependencies | ❌ | ✅ depth=1 | ✅ unlimited |
| Max dependency depth | 0 | 1 | Unlimited |
| Org-wide symbol resolution | ❌ | ❌ | ✅ |

**Community Example**:
```python
# Extract function from single file only
extract_code(
    file_path="utils.py",
    target_type="function",
    target_name="calculate_tax",
    include_cross_file_deps=False  # Community restriction
)
```

**Pro Example**:
```python
# Extract with 1-level dependencies
extract_code(
    file_path="services/order.py",
    target_type="function",
    target_name="process_order",
    include_cross_file_deps=True,
    max_depth=1  # Pro: depth=1
)
```

**Enterprise Example**:
```python
# Extract with unlimited depth + org-wide resolution
extract_code(
    file_path="services/order.py",
    target_type="function",
    target_name="process_order",
    include_cross_file_deps=True,
    max_depth=10  # Enterprise: unlimited
)
# Result includes org_symbols from entire codebase
```

---

### 3. `update_symbol` - Safe Code Modification

**Purpose**: Replace functions/classes/methods with backup and validation

| Capability | Community | Pro | Enterprise |
|------------|-----------|-----|------------|
| **Availability** | ✅ | ✅ | ✅ |
| Symbol replacement | ✅ | ✅ | ✅ |
| Backup creation | ✅ | ✅ | ✅ |
| Syntax validation | ✅ | ✅ | ✅ |
| **Restrictions** | None | None | None |

**Summary**: Fully available at all tiers with no restrictions.

---

### 3b. `rename_symbol` - Safe Symbol Renaming

**Purpose**: Rename a function, class, or method safely.

| Capability | Community | Pro | Enterprise |
|------------|-----------|-----|------------|
| **Availability** | ✅ | ✅ | ✅ |
| Definition rename | ✅ | ✅ | ✅ |
| Backup creation | ✅ | ✅ | ✅ |
| Cross-file reference updates | ❌ | ✅ bounded | ✅ unlimited |
| Import updates | ❌ | ✅ bounded | ✅ unlimited |

**Summary**:
- Community stays single-file (definition-only).
- Pro adds conservative cross-file reference/import updates within configured limits.
- Enterprise removes those limits (org-wide/unlimited scope by omission in `limits.toml`).

---

### 4. `security_scan` - Security Vulnerability Detection

**Purpose**: Taint-based vulnerability scanning (SQL injection, XSS, etc.)

| Capability | Community | Pro | Enterprise |
|------------|-----------|-----|------------|
| **Availability** | ✅ | ✅ | ✅ |
| Basic vulnerabilities | ✅ | ✅ | ✅ |
| Max findings | **50** | Unlimited | Unlimited |
| Vulnerability types | SQL, XSS, Command Injection | All types | All + custom |
| Single-file taint | ✅ | ✅ | ✅ |
| Advanced taint flow | ❌ | ✅ | ✅ |
| Remediation suggestions | ❌ | ✅ | ✅ |
| OWASP categorization | ❌ | ✅ | ✅ |
| Cross-file taint | ❌ | ❌ | ✅ |
| Compliance reporting | ❌ | ❌ | ✅ SOC2, HIPAA |
| Custom security rules | ❌ | ❌ | ✅ |
| Automated remediation | ❌ | ❌ | ✅ |

**Community Example**:
```json
{
  "tier": "community",
  "vulnerabilities": [50 findings],
  "truncated": true,
  "total_vulnerabilities": 75,
  "upgrade_hints": [
    "Showing 50/75 vulnerabilities.",
    "Upgrade to PRO for unlimited findings and remediation suggestions."
  ]
}
```

**Pro Example**:
```json
{
  "tier": "pro",
  "vulnerabilities": [25 findings],
  "taint_flows": [...],
  "remediation": ["Use parameterized queries", ...],
  "owasp_categories": {"A03:2021": 5}
}
```

**Enterprise Example**:
```json
{
  "tier": "enterprise",
  "vulnerabilities": [25 findings + custom rules],
  "taint_flows": [...],
  "remediation": [...],
  "compliance_report": {
    "soc2": "passed",
    "hipaa": "passed"
  },
  "automated_fixes": [...]
}
```

---

### 5. `unified_sink_detect` - Polyglot Sink Detection

**Purpose**: Detect dangerous functions across languages (Python, Java, JS, TS)

| Capability | Community | Pro | Enterprise |
|------------|-----------|-----|------------|
| **Availability** | ✅ | ✅ | ✅ |
| All languages | ✅ | ✅ | ✅ |
| Confidence thresholds | ✅ | ✅ | ✅ |
| CWE mapping | ✅ | ✅ | ✅ |
| **Restrictions** | None | None | None |

**Summary**: Fully available at all tiers with no restrictions.

---

### 6. `cross_file_security_scan` - Multi-File Taint Analysis

**Purpose**: Track taint flow across file boundaries

| Capability | Community | Pro | Enterprise |
|------------|-----------|-----|------------|
| **Availability** | ✅ | ✅ | ✅ |
| Cross-file taint | ✅ limited | ✅ full | ✅ full |
| Max call depth | **2** | **5** | Unlimited |
| Max modules | **50** | **500** | Unlimited |
| Timeout | 30s | 120s | Configurable |
| Mermaid diagram | ✅ | ✅ | ✅ |

**Community Example**:
```python
cross_file_security_scan(
    project_root="/app",
    max_depth=2,  # Community: max 2
    max_modules=50  # Community: max 50
)
# May timeout on large codebases
```

---

### 7. `symbolic_execute` - Symbolic Path Exploration

**Purpose**: Explore execution paths using symbolic execution (Z3 solver)

| Capability | Community | Pro | Enterprise |
|------------|-----------|-----|------------|
| **Availability** | ✅ | ✅ | ✅ |
| Symbolic paths | ✅ | ✅ | ✅ |
| Max paths | **50** | **100** | Unlimited |
| Z3 constraint solving | ✅ basic | ✅ advanced | ✅ advanced |
| Path prioritization | ❌ | ✅ | ✅ |
| Branch coverage | ❌ | ✅ | ✅ |

**Community Example**:
```json
{
  "tier": "community",
  "paths_explored": 50,
  "paths": [50 paths],
  "upgrade_hints": [
    "Limited to 50 paths. Upgrade to PRO for 100 paths."
  ]
}
```

---

### 8. `generate_unit_tests` - Test Generation

**Purpose**: Generate unit tests from symbolic execution paths

| Capability | Community | Pro | Enterprise |
|------------|-----------|-----|------------|
| **Availability** | ✅ | ✅ | ✅ |
| Test generation | ✅ | ✅ | ✅ |
| Max test cases | **5** | **20** | Unlimited |
| Frameworks | pytest | pytest, unittest | All + custom |
| Coverage targeting | ❌ | ✅ | ✅ |

**Community Example**:
```python
{
  "tier": "community",
  "test_cases": [5 tests],
  "upgrade_hints": [
    "Generated 5/15 possible tests. Upgrade for more."
  ]
}
```

---

### 9. `simulate_refactor` - Refactor Safety Check

**Purpose**: Verify code changes preserve behavior before applying

| Capability | Community | Pro | Enterprise |
|------------|-----------|-----|------------|
| **Availability** | ✅ | ✅ | ✅ |
| Safety simulation | ✅ | ✅ | ✅ |
| Security checks | ✅ | ✅ | ✅ |
| Structural analysis | ✅ | ✅ | ✅ |
| **Restrictions** | None | None | None |

**Summary**: Fully available at all tiers with no restrictions.

---

### 10. `crawl_project` - Project-Wide Analysis

**Purpose**: Analyze entire project structure and complexity

| Capability | Community | Pro | Enterprise |
|------------|-----------|-----|------------|
| **Availability** | ✅ | ✅ | ✅ |
| File discovery | ✅ | ✅ | ✅ |
| Max files | **100** | **1,000** | Unlimited |
| Mode | Discovery | Deep AST parsing | Deep + org indexing |
| Entrypoint detection | ✅ | ✅ | ✅ |
| AST parsing | ❌ | ✅ | ✅ |
| Complexity analysis | ❌ | ✅ | ✅ |
| Dependency graph | ❌ | ✅ | ✅ |
| Org indexing | ❌ | ❌ | ✅ |
| Custom metrics | ❌ | ❌ | ✅ |

**Community Example** (Discovery Mode):
```json
{
  "tier": "community",
  "mode": "discovery",
  "file_count": 100,
  "files": ["file1.py", "file2.py", ...],
  "entrypoints": ["main", "app.run"],
  "basic_stats": {
    "total_lines": 5000,
    "languages": ["python", "javascript"]
  },
  "upgrade_hints": [
    "Discovery mode: basic file inventory only.",
    "Upgrade to PRO for deep AST parsing and complexity analysis."
  ]
}
```

**Pro Example** (Deep Mode):
```json
{
  "tier": "pro",
  "mode": "deep",
  "file_count": 1000,
  "functions": ["func1", "func2", ...],
  "classes": ["Class1", "Class2", ...],
  "complexity_warnings": [...],
  "dependency_graph": {...}
}
```

---

### 11. `scan_dependencies` - Vulnerability Scanning

**Purpose**: Scan dependencies for known CVEs (OSV database)

| Capability | Community | Pro | Enterprise |
|------------|-----------|-----|------------|
| **Availability** | ✅ | ✅ | ✅ |
| OSV database lookup | ✅ | ✅ | ✅ |
| Max dependencies | **50** | Unlimited | Unlimited |
| Vulnerability details | Basic | Full | Full + remediation |
| Auto-update PR | ❌ | ❌ | ✅ |

**Community Example**:
```json
{
  "tier": "community",
  "dependencies_scanned": 50,
  "truncated": true,
  "total_dependencies": 150,
  "vulnerabilities": [...],
  "upgrade_hints": [
    "Scanned 50/150 dependencies. Upgrade for full scan."
  ]
}
```

---

### 12. `get_file_context` - File Overview

**Purpose**: Get file structure without reading full content

| Capability | Community | Pro | Enterprise |
|------------|-----------|-----|------------|
| **Availability** | ✅ | ✅ | ✅ |
| File structure | ✅ | ✅ | ✅ |
| Functions/classes | ✅ | ✅ | ✅ |
| Complexity score | ✅ | ✅ | ✅ |
| **Restrictions** | None | None | None |

**Summary**: Fully available at all tiers with no restrictions.

---

### 13. `get_symbol_references` - Symbol Usage

**Purpose**: Find all references to a function/class/variable

| Capability | Community | Pro | Enterprise |
|------------|-----------|-----|------------|
| **Availability** | ✅ | ✅ | ✅ |
| Symbol search | ✅ | ✅ | ✅ |
| All references | ✅ | ✅ | ✅ |
| Line numbers | ✅ | ✅ | ✅ |
| Max files | **100** | Unlimited | Unlimited |
| Max references | **100** | Unlimited | Unlimited |

**Community Example**:
```python
get_symbol_references(
    symbol_name="process_order",
    project_root="/app"
)  # Community: max 100 files, 100 references
```

---

### 14. `get_cross_file_dependencies` - Dependency Resolution

**Purpose**: Analyze cross-file dependency chains with confidence scoring

| Capability | Community | Pro | Enterprise |
|------------|-----------|-----|------------|
| **Availability** | ✅ | ✅ | ✅ |
| Dependency resolution | ✅ | ✅ | ✅ |
| Max depth | **1** | **5** | Unlimited |
| Confidence decay | ✅ | ✅ | ✅ |
| Circular detection | ✅ | ✅ | ✅ |
| Mermaid diagram | ✅ | ✅ | ✅ |

**Community Example**:
```python
get_cross_file_dependencies(
    target_file="services/order.py",
    target_symbol="process_order",
    max_depth=1  # Community: max 1
)
```

---

### 15. `get_call_graph` - Function Call Analysis

**Purpose**: Build call graph showing function relationships

| Capability | Community | Pro | Enterprise |
|------------|-----------|-----|------------|
| **Availability** | ✅ | ✅ | ✅ |
| Call graph building | ✅ | ✅ | ✅ |
| Max depth | **3 hops** | **10 hops** | Unlimited |
| Entry point detection | ✅ | ✅ | ✅ |
| Circular import check | ✅ | ✅ | ✅ |
| Mermaid diagram | ✅ | ✅ | ✅ |

**Community Example**:
```json
{
  "tier": "community",
  "depth_used": 3,
  "nodes": [...],
  "edges": [...],
  "upgrade_hints": [
    "Call graph limited to 3 hops. Upgrade to PRO for 10 hops."
  ]
}
```

---

### 16. `get_graph_neighborhood` - Graph Subgraph Extraction

**Purpose**: Extract k-hop neighborhood around a center node

| Capability | Community | Pro | Enterprise |
|------------|-----------|-----|------------|
| **Availability** | ✅ | ✅ | ✅ |
| Neighborhood extraction | ✅ | ✅ | ✅ |
| Max k-hops | **1** | **5** | Unlimited |
| Max nodes | **50** | **100** | Unlimited |
| Confidence filtering | ✅ | ✅ | ✅ |
| Direction filtering | ✅ | ✅ | ✅ |

**Community Example**:
```python
get_graph_neighborhood(
    center_node_id="python::services::function::process_order",
    k=1,  # Community: max k=1
    max_nodes=50  # Community: max 50
)
```

---

### 17. `get_project_map` - Project Structure Map

**Purpose**: High-level overview of project structure

| Capability | Community | Pro | Enterprise |
|------------|-----------|-----|------------|
| **Availability** | ✅ | ✅ | ✅ |
| Package structure | ✅ | ✅ | ✅ |
| Module inventory | ✅ | ✅ | ✅ |
| Complexity hotspots | ✅ | ✅ | ✅ |
| Entry point detection | ✅ | ✅ | ✅ |
| **Restrictions** | None | None | None |

**Summary**: Fully available at all tiers with no restrictions.

---

### 18. `validate_paths` - Path Accessibility Check

**Purpose**: Validate paths are accessible (Docker deployment helper)

| Capability | Community | Pro | Enterprise |
|------------|-----------|-----|------------|
| **Availability** | ✅ | ✅ | ✅ |
| Path validation | ✅ | ✅ | ✅ |
| Docker detection | ✅ | ✅ | ✅ |
| Volume mount suggestions | ✅ | ✅ | ✅ |
| **Restrictions** | None | None | None |

**Summary**: Fully available at all tiers with no restrictions.

---

### 19. `verify_policy_integrity` - Policy File Verification

**Purpose**: Cryptographic verification of policy file integrity

| Capability | Community | Pro | Enterprise |
|------------|-----------|-----|------------|
| **Availability** | ✅ | ✅ | ✅ |
| HMAC-SHA256 verification | ✅ | ✅ | ✅ |
| Tamper detection | ✅ | ✅ | ✅ |
| Manifest sources | ✅ | ✅ | ✅ |
| **Restrictions** | None | None | None |

**Summary**: Fully available at all tiers with no restrictions.

---

### 20. `type_evaporation_scan` - Type System Vulnerability Detection

**Purpose**: Detect TypeScript type evaporation vulnerabilities

| Capability | Community | Pro | Enterprise |
|------------|-----------|-----|------------|
| **Availability** | ✅ | ✅ | ✅ |
| Frontend scanning | ✅ | ✅ | ✅ |
| Backend scanning | ✅ | ✅ | ✅ |
| Cross-file correlation | ✅ | ✅ | ✅ |
| **Restrictions** | None | None | None |

**Summary**: Fully available at all tiers with no restrictions.

---

## Summary

### Tools with Restrictions

**11 tools** have tier-based limits:

1. `security_scan` - Max findings (50 → unlimited)
2. `symbolic_execute` - Max paths (50 → 100 → unlimited)
3. `crawl_project` - Max files (100 → 1000 → unlimited), mode (discovery → deep)
4. `extract_code` - Cross-file depth (0 → 1 → unlimited)
5. `generate_unit_tests` - Max tests (5 → 20 → unlimited)
6. `get_call_graph` - Max depth (3 → 10 → unlimited)
7. `get_graph_neighborhood` - Max k-hops (1 → 5 → unlimited)
8. `scan_dependencies` - Max deps (50 → unlimited)
9. `get_cross_file_dependencies` - Max depth (1 → 5 → unlimited)
10. `get_symbol_references` - Max files/refs (100 → unlimited)
11. `cross_file_security_scan` - Max depth/modules (limited → full)

### Tools with NO Restrictions

**9 tools** are fully available at all tiers:

1. `analyze_code`
2. `update_symbol`
3. `unified_sink_detect`
4. `simulate_refactor`
5. `get_file_context`
6. `get_project_map`
7. `validate_paths`
8. `verify_policy_integrity`
9. `type_evaporation_scan`

---

## Upgrade Decision Guide

### When to Upgrade from Community to Pro

You need PRO if:
- Security scans find more than 50 vulnerabilities (you want to see them all)
- You need symbolic execution to explore more than 50 paths
- Your project has more than 100 files and you need deep analysis
- You want cross-file dependency resolution beyond 1 hop
- You want more than 5 generated test cases
- You need call graphs deeper than 3 hops
- You need symbol references across more than 100 files

### When to Upgrade from Pro to Enterprise

You need ENTERPRISE if:
- You need compliance reporting (SOC2, HIPAA)
- You want custom security rules
- You need organization-wide code indexing
- You want automated remediation for vulnerabilities
- You need unlimited depth for all analyses
- You want custom metrics and integrations

---

## See Also

- [TIER_CONFIGURATION.md](../TIER_CONFIGURATION.md) - Configuration guide
- [features.py](../../src/code_scalpel/licensing/features.py) - Capability definitions
- [implementing_feature_gating.md](../guides/implementing_feature_gating.md) - Implementation guide
