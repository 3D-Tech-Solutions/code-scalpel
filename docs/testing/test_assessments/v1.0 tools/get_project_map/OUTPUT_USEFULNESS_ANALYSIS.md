# get_project_map Output Usefulness Analysis

**Date**: 2026-01-04
**Analyzed Version**: 3.3.0 (Enterprise tier)
**Sample Project**: code-scalpel (2,028 files, 6.8 MB output)

---

## Executive Summary

**Overall Assessment**: ⚠️ **NEEDS IMPROVEMENT** - Data is comprehensive but presentation dramatically reduces usefulness

**Key Issues**:
1. **Signal-to-Noise Ratio**: ~99% of output is redundant package/module listings
2. **Buried Insights**: High-value data (circular imports, complexity hotspots) hidden at the end
3. **Flat Structure**: No hierarchical organization or quick navigation
4. **Overwhelming Size**: 228,436 lines makes it practically unusable in chat
5. **Missing Context**: No actionable recommendations or prioritization

**Verdict**: The tool collects excellent data but presents it in a way that makes it nearly impossible to extract value from the output.

---

## What's Good: High-Value Data (Currently Hidden)

### 1. **Git History & Churn Analysis** ✅ EXCELLENT

**Location**: Lines 228,370-228,429 (last 60 lines!)

**What's there**:
```json
"git_history": {
  "most_active_files": [
    {"file": "src/code_scalpel/mcp/server.py", "changes": 318},
    {"file": "src/code_scalpel/licensing/features.py", "changes": 87}
  ],
  "activity_by_date": {
    "2026-01-02": 15,
    "2025-12-16": 111
  },
  "stability_score": 0.57
}
```

**Why it's valuable**:
- Identifies files under active development (risky for refactoring)
- Shows velocity trends
- Stability score indicates code maturity

**Problem**: Buried at the very end of 228K lines

---

### 2. **Circular Import Detection** ✅ CRITICAL

**What's there** (if any found):
```json
"circular_imports": [
  ["module_a", "module_b", "module_a"],
  ["service_x", "utils_y", "service_x"]
]
```

**Why it's valuable**:
- Critical architectural smell
- Can cause runtime errors
- Immediate action item

**Problem**: Empty list doesn't highlight that this is a GOOD thing

---

### 3. **Complexity Hotspots** ✅ ACTIONABLE

**What's there**:
```json
"complexity_hotspots": [
  "src/code_scalpel/mcp/server.py",
  "src/code_scalpel/ast_tools/call_graph.py"
]
```

**Why it's valuable**:
- Technical debt indicators
- Refactoring candidates
- Testing priorities

**Problem**: No metrics (how complex? what's the threshold?)

---

### 4. **Entry Points** ✅ USEFUL

**What's there**:
```json
"entry_points": [
  "src/code_scalpel/cli.py::main",
  "src/code_scalpel/mcp/server.py::serve"
]
```

**Why it's valuable**:
- Understanding execution paths
- Testing strategies
- Deployment validation

**Problem**: No categorization (CLI vs API vs test runners)

---

### 5. **Language Breakdown** ✅ GOOD

**What's there**:
```json
"languages": {
  "python": 2028,
  "json": 518,
  "markdown": 554,
  "javascript": 2
}
```

**Why it's valuable**:
- Multi-language project awareness
- Migration planning
- Tooling selection

**Problem**: No breakdown by directory (src vs tests vs docs)

---

## What's Bad: Low-Value Noise (99% of Output)

### 1. **Massive Package Listings** ❌ TOO VERBOSE

**Current state**:
- 127 packages listed
- Each package shows ALL modules (redundant with `modules` array)
- Each package shows ALL subpackages (redundant nesting)

**Example redundancy**:
```json
{
  "name": "code_scalpel",
  "modules": [
    "src/code_scalpel/__init__.py",
    "src/code_scalpel/agents/__init__.py",
    "src/code_scalpel/agents/base_agent.py",
    // ... 847 more modules (already listed in main modules array)
  ],
  "subpackages": [
    "agents",
    "analysis",
    "ast_tools",
    // ... (already listed as separate packages)
  ]
}
```

**Problem**: Contributes 6+ MB with zero incremental value

---

### 2. **Flat Module Array** ❌ UNNAVIGABLE

**Current state**:
- 2,028 modules listed linearly
- No grouping or hierarchy
- Same information repeated in packages

**Example**:
```json
"modules": [
  "src/code_scalpel/__init__.py",
  "src/code_scalpel/agents/__init__.py",
  "src/code_scalpel/agents/base_agent.py",
  // ... 2,025 more identical format entries
]
```

**Problem**: Impossible to scan, duplicate of package data

---

### 3. **Missing Insights** ❌ NO INTERPRETATION

**What's missing**:
- No summary statistics (avg complexity, test coverage if available)
- No recommendations (e.g., "Consider refactoring server.py - 318 changes in 30 days")
- No health score or quality metrics
- No comparison to best practices

---

## Proposed Improvements

### **Option 1: Tiered Summary (Recommended for All Tiers)**

**Replace current structure with:**

```json
{
  "success": true,
  "summary": {
    "project_root": "/path/to/project",
    "total_files": 2028,
    "total_lines": 148000,
    "languages": {"python": 2028, "json": 518},

    "health_score": {
      "overall": 78,
      "components": {
        "architecture": 85,
        "code_quality": 72,
        "maintainability": 75,
        "stability": 57
      }
    },

    "key_metrics": {
      "packages": 127,
      "entry_points": 12,
      "circular_imports": 0,
      "complexity_hotspots": 8,
      "active_development_files": 23
    }
  },

  "insights": {
    "critical": [
      {
        "type": "complexity_hotspot",
        "severity": "high",
        "file": "src/code_scalpel/mcp/server.py",
        "details": "20,540 lines, 318 changes in 30 days",
        "recommendation": "Consider splitting into smaller modules"
      },
      {
        "type": "high_churn",
        "severity": "medium",
        "file": "src/code_scalpel/licensing/features.py",
        "details": "87 changes in 30 days",
        "recommendation": "Requirements may be unstable - add integration tests"
      }
    ],

    "warnings": [
      {
        "type": "large_file",
        "file": "src/code_scalpel/mcp/server.py",
        "lines": 20540,
        "recommendation": "Files > 1000 lines are hard to maintain"
      }
    ],

    "positive": [
      {
        "type": "no_circular_imports",
        "message": "No circular import cycles detected",
        "impact": "Good architectural hygiene"
      }
    ]
  },

  "architecture": {
    "top_level_packages": [
      {
        "name": "code_scalpel",
        "path": "src/code_scalpel",
        "modules_count": 847,
        "subpackages_count": 15,
        "role": "core",
        "key_subpackages": ["agents", "analysis", "ast_tools", "mcp"]
      },
      {
        "name": "tests",
        "path": "tests",
        "modules_count": 412,
        "role": "testing"
      }
    ],

    "layering": {
      "cli": ["src/code_scalpel/cli.py"],
      "mcp_server": ["src/code_scalpel/mcp/server.py"],
      "core_analysis": ["src/code_scalpel/analysis/*", "src/code_scalpel/ast_tools/*"],
      "utilities": ["src/code_scalpel/cache/*", "src/code_scalpel/utils/*"]
    }
  },

  "git_activity": {
    "most_active_files": [
      {"file": "src/code_scalpel/mcp/server.py", "changes": 318, "last_7_days": 45},
      {"file": "src/code_scalpel/licensing/features.py", "changes": 87, "last_7_days": 12}
    ],
    "velocity": {
      "commits_last_30_days": 302,
      "files_changed_last_30_days": 147,
      "hotspot_threshold": 50
    },
    "stability_score": 0.57
  },

  "detailed_data": {
    "format": "chunked",
    "location": ".code-scalpel/outputs/project_map_20260104_153022/",
    "files": {
      "packages.json": "Full package hierarchy (1.2 MB)",
      "modules.json": "All module metadata (3.8 MB)",
      "dependencies.json": "Import graph (892 KB)",
      "git_history.json": "Detailed commit data (643 KB)",
      "diagram.mmd": "Mermaid architecture diagram (143 KB)"
    }
  }
}
```

**Size comparison**:
- Current: 6.8 MB JSON (228K lines)
- Proposed summary: ~15 KB JSON (600 lines)
- Detailed data: Still 6.8 MB but in organized chunks

**Benefits**:
- 450x size reduction in chat
- Actionable insights front and center
- Navigate to detailed data only when needed
- Health scores for quick assessment

---

### **Option 2: Interactive Navigation (Enterprise)**

**Add navigation metadata**:

```json
{
  "summary": { /* as above */ },

  "navigation": {
    "available_views": [
      "architecture_layers",
      "module_dependencies",
      "complexity_analysis",
      "git_hotspots",
      "test_coverage"
    ],

    "quick_queries": {
      "get_package_details": "get_project_map --package=code_scalpel.mcp",
      "get_complexity_report": "get_project_map --focus=complexity",
      "get_git_analysis": "get_project_map --focus=git_activity"
    }
  }
}
```

**Usage**:
```bash
# First call: Get summary
result = get_project_map(project_root="./")
# Returns: 15 KB summary

# Follow-up: Get details on specific package
details = get_project_map(project_root="./", focus="package", package="code_scalpel.mcp")
# Returns: Just that package's data (~100 KB)
```

---

### **Option 3: Progressive Disclosure (All Tiers)**

**Return different detail levels**:

```python
# Community tier
get_project_map(detail="summary")
# Returns: 5 KB - just counts, languages, top insights

# Pro tier
get_project_map(detail="standard")
# Returns: 50 KB - summary + top packages + key metrics

# Enterprise tier
get_project_map(detail="comprehensive")
# Returns: Full 6.8 MB but organized by sections
```

---

## Tier-Specific Recommendations

### **Community Tier**: Summary Only

**Return**:
```json
{
  "summary": {
    "total_files": 2028,
    "languages": {"python": 2028, "json": 518},
    "top_packages": ["code_scalpel", "tests"],
    "health_score": 78
  },
  "insights": {
    "critical": ["High complexity in server.py"],
    "warnings": ["Large file detected"]
  },
  "upgrade_hint": "Unlock full architecture analysis with Pro tier"
}
```

**Size**: ~2 KB
**Value**: Quick health check

---

### **Pro Tier**: Summary + Top Insights

**Return**:
```json
{
  "summary": { /* full summary */ },
  "insights": { /* all insights */ },
  "architecture": { /* top-level only */ },
  "git_activity": { /* top 20 files */ },
  "output_file": ".code-scalpel/outputs/full_project_map.json"
}
```

**Size**: ~50 KB in chat + 6.8 MB file
**Value**: Actionable insights + full data available

---

### **Enterprise Tier**: Chunked + Queryable

**Return**:
```json
{
  "summary": { /* full summary */ },
  "insights": { /* all insights */ },
  "output_format": "chunked",
  "output_directory": ".code-scalpel/outputs/project_map_20260104/",
  "chunks": [
    {"file": "summary.json", "description": "Quick overview"},
    {"file": "packages.json", "description": "Package hierarchy"},
    {"file": "modules.json", "description": "Module metadata"},
    {"file": "dependencies.json", "description": "Import graph"},
    {"file": "git_history.json", "description": "Commit activity"}
  ],
  "query_api": {
    "available": true,
    "examples": [
      "get_project_map --query='packages where modules_count > 100'",
      "get_project_map --query='files where complexity > high'"
    ]
  }
}
```

**Size**: ~50 KB in chat + 6.8 MB chunked
**Value**: Full power + navigability

---

## Implementation Priority

### **Phase 1: Immediate (2-3 hours)**

**Add summary section at the top**:
1. Move `git_history`, `circular_imports`, `complexity_hotspots` to top
2. Add `health_score` calculation
3. Add `insights` array with recommendations
4. Auto-file output when > 1 MB (already recommended)

**Changes**:
- Modify `get_project_map` function to calculate insights
- Reorder JSON output (summary first)
- Add scoring logic

---

### **Phase 2: Short-term (4-6 hours)**

**Implement progressive disclosure**:
1. Add `detail` parameter (summary | standard | comprehensive)
2. Implement chunking for Enterprise tier
3. Create separate files for each major section

**Changes**:
- Add detail level routing
- Implement chunking logic
- Update return model

---

### **Phase 3: Medium-term (8-12 hours)**

**Add interactive queries**:
1. Implement `--focus` parameter
2. Add package-specific queries
3. Create query language for Enterprise

**Changes**:
- New query parser
- Filtering logic
- Documentation

---

## Recommended Immediate Action

**Top Priority**: Restructure output to put insights first

**Quick win implementation**:

```python
# In get_project_map function, before returning result:

# Calculate health score
health_score = calculate_health_score(
    complexity_hotspots=len(complexity_hotspots),
    circular_imports=len(circular_imports),
    total_files=total_files,
    git_stability=git_stability_score
)

# Generate insights
insights = generate_insights(
    complexity_hotspots=complexity_hotspots,
    git_history=git_history,
    circular_imports=circular_imports,
    total_files=total_files
)

# Restructure result
result_dict = result.model_dump()

# Create new summary-first structure
summary_first = {
    "summary": {
        "total_files": result_dict["total_files"],
        "total_lines": result_dict["total_lines"],
        "languages": result_dict["languages"],
        "health_score": health_score,
        "key_metrics": {
            "packages": len(result_dict["packages"]),
            "entry_points": len(result_dict["entry_points"]),
            "circular_imports": len(result_dict["circular_imports"]),
            "complexity_hotspots": len(result_dict["complexity_hotspots"])
        }
    },
    "insights": insights,
    "architecture": extract_architecture_summary(result_dict),
    "git_activity": result_dict.get("git_history", {}),

    # Detailed data either in file or chunked
    "detailed_data": {
        "format": "file" if len(json.dumps(result_dict)) > 1_000_000 else "inline",
        "location": output_file if large_output else None,
        "packages": result_dict["packages"] if not large_output else None,
        "modules": result_dict["modules"] if not large_output else None
    }
}

return summary_first
```

**Effort**: 2-3 hours
**Impact**: Transforms tool from "data dump" to "actionable intelligence"

---

## Conclusion

**Current State**: get_project_map collects excellent data but buries it in 6.8 MB of redundant listings

**Recommended Path**:
1. **Phase 1 (Immediate)**: Restructure output to put insights/summary first - solves 80% of usability problems
2. **Phase 2 (Short-term)**: Add auto-file output for large projects - solves the 6.8 MB chat problem
3. **Phase 3 (Medium-term)**: Add interactive queries for Enterprise - unlocks full power

**Expected Outcome**: Transform from "overwhelming data dump" to "intelligent architectural advisor"
