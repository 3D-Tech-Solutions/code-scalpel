# get_project_map Flag System Design

**Purpose**: Give users control over output verbosity and format while maintaining intelligent defaults

**Date**: 2026-01-04
**Status**: DESIGN PROPOSAL

---

## Design Philosophy

**Core Principles**:
1. **Smart defaults** - 95% of users get useful output without flags
2. **Progressive disclosure** - Flags unlock more detail when needed
3. **Tier-appropriate** - Higher tiers get more powerful flags
4. **No breaking changes** - Existing usage still works
5. **Escape hatches** - Power users can get raw data if needed

---

## Key Features (ready for implementation)

- **Smart Defaults**: 95% of users get useful output with no flags.
- **Escape Hatches**: Power users can still pull the full 228K-line payload when explicitly requested.
- **Warnings, Not Errors**: Inline mode still returns data, even when oversized, but emits a warning.
- **Tier-Appropriate**: Community (1 MB cap, basic flags), Pro (10 MB cap, advanced flags), Enterprise (100 MB cap, all flags + chunking).
- **Backward Compatible**: Existing `get_project_map(project_root="./")` keeps working (auto-routing behind the scenes).

**Recommended default routing example**:
```python
get_project_map(output_mode="inline", max_inline_size_mb=10.0)
# ⚠️ Warning: "Output is 6.8 MB. Consider using output_mode='file'"
# Still returns full data (user explicitly asked for it)
```

---

## Implementation Plan

### Phase 1: Core Flags (3-4 hours) — 🔥 Recommend immediate
Add parameters:
```python
@mcp.tool()
async def get_project_map(
    project_root: str,
    output_mode: Literal["auto", "summary", "inline", "file"] = "auto",
    detail_level: Literal["minimal", "standard", "detailed", "comprehensive"] = "standard",
    max_inline_size_mb: float = 1.0,
    # ... existing params
) -> dict:
    # 1) Generate full analysis
    # 2) Apply detail_level filter
    # 3) Route based on output_mode + size
    # 4) Return summary/inline/file metadata as appropriate
```

Testing (essentials):
- **Auto-routing**: small → inline; large → returns `output_file`.
- **Forced inline**: large + `output_mode="inline"`, `max_inline_size_mb=10.0` → returns data + warning present.
- **Summary**: `detail_level="minimal"` → JSON payload < ~5 KB.

### Phase 2: Section Control (2-3 hours)
- `include` / `exclude` section filtering
- `focus` deep-dive (Pro+)

### Phase 3: Advanced (6-8 hours)
- `query` (Enterprise query language)
- `format` (markdown / CSV export)
- `chunk_by` (chunking strategies)

**Why Phase 1 first**: Solves the “6.8 MB in chat” problem immediately, keeps escape hatches, supports CI/CD minimal output, and preserves backward compatibility with ~3-4 hours of effort.

---

## Proposed Flag System

### **Universal Flags (All Tiers)**

#### 1. `--output-mode` (or `output_mode` parameter)

**Purpose**: Control how output is delivered

**Values**:
- `"auto"` (default) - Intelligent routing based on size
- `"summary"` - Always return compact summary (2-50 KB)
- `"inline"` - Return full data inline (ignores size - use with caution!)
- `"file"` - Always save to file, return summary + path
- `"chunked"` - Split into multiple files (Enterprise only)

**Examples**:
```python
# Default: Smart routing
get_project_map(project_root="./")
# If < 1 MB: returns inline
# If > 1 MB: auto-saves to file, returns summary

# Force summary only (good for CI/CD health checks)
get_project_map(project_root="./", output_mode="summary")
# Always returns: ~50 KB summary

# Force inline (warning if > 10 MB)
get_project_map(project_root="./", output_mode="inline")
# Returns: Full 6.8 MB (with warning)

# Force file output
get_project_map(project_root="./", output_mode="file")
# Always saves to file, returns summary + path

# Enterprise: Chunked
get_project_map(project_root="./", output_mode="chunked")
# Creates directory with organized chunks
```

---

#### 2. `--detail-level` (or `detail_level` parameter)

**Purpose**: Control granularity of information

**Values**:
- `"minimal"` - Just counts and health score (~2 KB)
- `"standard"` (default) - Summary + insights + top packages (~50 KB)
- `"detailed"` - Include all packages, top 100 modules (~500 KB)
- `"comprehensive"` - Everything (full 6.8 MB)

**Tier Restrictions**:
- Community: `minimal` or `standard` only
- Pro: All except `comprehensive`
- Enterprise: All levels

**Examples**:
```python
# Community: Minimal health check
get_project_map(project_root="./", detail_level="minimal")
# Returns: {
#   "total_files": 2028,
#   "health_score": 78,
#   "top_insight": "High complexity in server.py"
# }

# Pro: Standard (default)
get_project_map(project_root="./", detail_level="standard")
# Returns: Summary + insights + architecture + git activity

# Enterprise: Comprehensive
get_project_map(project_root="./", detail_level="comprehensive")
# Returns: Everything (auto-filed if > 1 MB)
```

---

#### 3. `--include` / `--exclude` (or `include`/`exclude` parameters)

**Purpose**: Fine-grained control over sections

**Available Sections**:
- `"packages"` - Package hierarchy
- `"modules"` - Module listings
- `"entry_points"` - Entry point detection
- `"circular_imports"` - Circular import analysis
- `"complexity"` - Complexity hotspots
- `"git_history"` - Git activity analysis
- `"mermaid"` - Mermaid diagram
- `"dependencies"` - Dependency graph (Enterprise)
- `"architecture"` - Architectural layers (Pro+)
- `"metrics"` - Custom metrics (Enterprise)

**Examples**:
```python
# Only want git history for velocity tracking
get_project_map(
    project_root="./",
    include=["git_history", "complexity"]
)
# Returns: Just those two sections

# Exclude heavy sections
get_project_map(
    project_root="./",
    exclude=["modules", "packages"]
)
# Returns: Everything except module/package listings

# Combination
get_project_map(
    project_root="./",
    detail_level="standard",
    exclude=["mermaid"]  # Skip diagram generation
)
```

---

#### 4. `--max-inline-size-mb` (or `max_inline_size_mb` parameter)

**Purpose**: Control when auto-file kicks in

**Values**: Float (MB), default `1.0`

**Tier Limits**:
- Community: Max `1.0` MB
- Pro: Max `10.0` MB
- Enterprise: Max `100.0` MB (or unlimited with warning)

**Examples**:
```python
# Pro tier: Willing to accept 5 MB inline
get_project_map(
    project_root="./",
    max_inline_size_mb=5.0
)
# Returns inline if < 5 MB, otherwise saves to file

# Enterprise: Get everything inline (risky!)
get_project_map(
    project_root="./",
    max_inline_size_mb=100.0,
    output_mode="inline"
)
# Returns: Full 6.8 MB with warning
```

---

### **Pro/Enterprise Flags**

#### 5. `--focus` (or `focus` parameter)

**Purpose**: Drill down into specific areas (Pro+)

**Values**:
- `"architecture"` - Detailed package/module structure
- `"complexity"` - Full complexity analysis
- `"git_activity"` - Detailed commit history
- `"dependencies"` - Full dependency graph
- `"security"` - Security-focused analysis (Enterprise)
- `"performance"` - Performance metrics (Enterprise)

**Examples**:
```python
# Pro: Deep dive into complexity
get_project_map(
    project_root="./",
    focus="complexity"
)
# Returns: {
#   "summary": {...},
#   "complexity_analysis": {
#     "files_by_complexity": [...],
#     "hotspots": [...],
#     "recommendations": [...]
#   }
# }

# Enterprise: Security focus
get_project_map(
    project_root="./",
    focus="security"
)
# Returns: Security-oriented analysis
```

---

#### 6. `--package-filter` (or `package_filter` parameter)

**Purpose**: Analyze specific packages only (Pro+)

**Examples**:
```python
# Analyze only the 'mcp' package
get_project_map(
    project_root="./",
    package_filter="code_scalpel.mcp"
)
# Returns: Just that package's analysis

# Multiple packages (Enterprise)
get_project_map(
    project_root="./",
    package_filter=["code_scalpel.mcp", "code_scalpel.ast_tools"]
)
```

---

### **Enterprise-Only Flags**

#### 7. `--query` (or `query` parameter)

**Purpose**: Query-based filtering (Enterprise only)

**Syntax**: Simple query language

**Examples**:
```python
# Find complex files
get_project_map(
    project_root="./",
    query="files where complexity > high"
)

# Find high-churn packages
get_project_map(
    project_root="./",
    query="packages where git_changes > 50"
)

# Combination
get_project_map(
    project_root="./",
    query="files where complexity > high AND git_changes > 20"
)
```

---

#### 8. `--format` (or `format` parameter)

**Purpose**: Output format control (Enterprise only)

**Values**:
- `"json"` (default) - Standard JSON
- `"yaml"` - YAML format
- `"toml"` - TOML format
- `"csv"` - CSV (for modules/packages)
- `"markdown"` - Human-readable report

**Examples**:
```python
# Generate markdown report
get_project_map(
    project_root="./",
    format="markdown",
    output_mode="file"
)
# Creates: project_map_report.md

# CSV export for Excel
get_project_map(
    project_root="./",
    format="csv",
    include=["modules"]
)
# Returns: CSV of all modules
```

---

#### 9. `--chunk-by` (or `chunk_by` parameter)

**Purpose**: Control chunking strategy (Enterprise only)

**Values**:
- `"size"` (default) - Split by size (1 MB chunks)
- `"section"` - One file per section
- `"package"` - One file per top-level package
- `"custom"` - Custom chunking rules

**Examples**:
```python
# Chunk by section
get_project_map(
    project_root="./",
    output_mode="chunked",
    chunk_by="section"
)
# Creates:
# - summary.json
# - packages.json
# - modules.json
# - git_history.json

# Chunk by package
get_project_map(
    project_root="./",
    output_mode="chunked",
    chunk_by="package"
)
# Creates:
# - code_scalpel.json
# - tests.json
# - docs.json
```

---

## Complete Flag Reference Table

| Flag | Type | Default | Community | Pro | Enterprise | Description |
|------|------|---------|-----------|-----|------------|-------------|
| `output_mode` | str | `"auto"` | ✅ | ✅ | ✅ | Output delivery method |
| `detail_level` | str | `"standard"` | ✅* | ✅ | ✅ | Information granularity |
| `include` | list | `None` | ✅ | ✅ | ✅ | Sections to include |
| `exclude` | list | `None` | ✅ | ✅ | ✅ | Sections to exclude |
| `max_inline_size_mb` | float | `1.0` | ✅* | ✅* | ✅* | Auto-file threshold |
| `focus` | str | `None` | ❌ | ✅ | ✅ | Deep-dive analysis area |
| `package_filter` | str/list | `None` | ❌ | ✅ | ✅ | Specific package analysis |
| `query` | str | `None` | ❌ | ❌ | ✅ | Query-based filtering |
| `format` | str | `"json"` | ❌ | ❌ | ✅ | Output format |
| `chunk_by` | str | `"size"` | ❌ | ❌ | ✅ | Chunking strategy |

*Restricted values based on tier

---

## Usage Examples by Scenario

### **Scenario 1: CI/CD Health Check**

**Goal**: Quick pass/fail health score

```python
get_project_map(
    project_root="./",
    detail_level="minimal",
    include=["health_score", "circular_imports", "complexity"]
)

# Returns: ~2 KB
{
  "health_score": 78,
  "circular_imports": 0,
  "complexity_hotspots": 8,
  "status": "pass" if health_score > 70 else "fail"
}
```

---

### **Scenario 2: Developer Onboarding**

**Goal**: Understand project structure

```python
get_project_map(
    project_root="./",
    detail_level="standard",
    include=["architecture", "entry_points", "mermaid"],
    output_mode="file"
)

# Returns: ~50 KB summary + file with full data
# Mermaid diagram for visualization
```

---

### **Scenario 3: Refactoring Planning**

**Goal**: Find complexity hotspots and high-churn files

```python
# Pro tier
get_project_map(
    project_root="./",
    focus="complexity",
    include=["complexity", "git_history"]
)

# Enterprise tier (with query)
get_project_map(
    project_root="./",
    query="files where complexity > high AND git_changes > 30"
)

# Returns: Targeted analysis of risky files
```

---

### **Scenario 4: Architecture Documentation**

**Goal**: Generate comprehensive documentation

```python
get_project_map(
    project_root="./",
    detail_level="comprehensive",
    format="markdown",
    output_mode="file",
    include=["architecture", "packages", "mermaid", "dependencies"]
)

# Creates: project_map_report.md (human-readable)
```

---

### **Scenario 5: Data Analysis/Export**

**Goal**: Export data for external analysis

```python
# CSV for Excel
get_project_map(
    project_root="./",
    format="csv",
    include=["modules"],
    output_mode="file"
)
# Creates: modules.csv

# Chunked JSON for processing
get_project_map(
    project_root="./",
    output_mode="chunked",
    chunk_by="section",
    detail_level="comprehensive"
)
# Creates: Multiple JSON files by section
```

---

### **Scenario 6: "I Really Want All 6.8 MB Inline"**

**Goal**: Power user needs raw data (the question you asked!)

```python
# Pro tier (up to 10 MB)
get_project_map(
    project_root="./",
    output_mode="inline",
    detail_level="comprehensive",
    max_inline_size_mb=10.0
)
# Returns: Full 6.8 MB inline with warning

# Enterprise tier (unlimited)
get_project_map(
    project_root="./",
    output_mode="inline",
    detail_level="comprehensive",
    max_inline_size_mb=100.0,
    force_inline=True  # Explicit confirmation
)
# Returns: Full 6.8 MB inline
# Warning: "Output size exceeds recommended limit. Consider using output_mode='file'."
```

---

## Implementation Strategy

### **Phase 1: Core Flags (Immediate - 3-4 hours)**

**Implement**:
1. `output_mode` - Auto-file routing
2. `detail_level` - Summary vs full
3. `max_inline_size_mb` - Size threshold

**Changes needed**:
```python
@mcp.tool()
async def get_project_map(
    project_root: str,
    output_mode: Literal["auto", "summary", "inline", "file", "chunked"] = "auto",
    detail_level: Literal["minimal", "standard", "detailed", "comprehensive"] = "standard",
    max_inline_size_mb: float = 1.0,
    # ... existing parameters
) -> dict:
    """Get project architecture map with configurable output.

    Args:
        output_mode: How to deliver output
            - "auto": Smart routing based on size (default)
            - "summary": Always compact summary
            - "inline": Full data inline (warning if large)
            - "file": Always save to file
            - "chunked": Split into multiple files (Enterprise)

        detail_level: Information granularity
            - "minimal": Counts + health score (~2 KB)
            - "standard": Summary + insights (~50 KB, default)
            - "detailed": Include packages (~500 KB)
            - "comprehensive": Everything (may be large)

        max_inline_size_mb: Auto-file threshold
            - Community: Max 1.0 MB
            - Pro: Max 10.0 MB
            - Enterprise: Max 100.0 MB
    """

    # Get tier
    tier = get_current_tier()

    # Validate parameters
    validate_flags(tier, output_mode, detail_level, max_inline_size_mb)

    # Generate full analysis
    full_result = generate_project_map(project_root)

    # Apply detail level filtering
    filtered_result = apply_detail_level(full_result, detail_level, tier)

    # Route output based on mode and size
    return route_output(
        filtered_result,
        output_mode=output_mode,
        max_inline_size_mb=max_inline_size_mb,
        tier=tier
    )
```

---

### **Phase 2: Section Control (Short-term - 2-3 hours)**

**Implement**:
1. `include` / `exclude` - Section filtering
2. `focus` - Deep-dive analysis (Pro+)
3. `package_filter` - Package-specific analysis (Pro+)

---

### **Phase 3: Advanced (Medium-term - 6-8 hours)**

**Implement**:
1. `query` - Query language (Enterprise)
2. `format` - Multiple output formats (Enterprise)
3. `chunk_by` - Chunking strategies (Enterprise)

---

## Default Behavior (No Flags)

**What happens with no flags**:

```python
# Simple call
get_project_map(project_root="./")

# Equivalent to:
get_project_map(
    project_root="./",
    output_mode="auto",
    detail_level="standard",
    max_inline_size_mb=1.0
)
```

**Routing logic**:
1. Generate full analysis
2. Calculate output size
3. If < 1 MB: Return inline (standard detail level)
4. If >= 1 MB: Save to file, return summary + file path

**Result for code-scalpel (6.8 MB)**:
```json
{
  "summary": {
    "total_files": 2028,
    "health_score": 78,
    "key_metrics": {...}
  },
  "insights": {
    "critical": [...],
    "warnings": [...]
  },
  "architecture": {...},
  "git_activity": {...},
  "output_saved_to": ".code-scalpel/outputs/project_map_20260104_153022.json",
  "output_size_mb": 6.8,
  "note": "Full data saved to file due to size. Use output_mode='inline' to force inline output."
}
```

---

## Flag Validation & Error Messages

### **Tier Restrictions**

```python
# Community trying to use Pro flag
get_project_map(project_root="./", focus="complexity")
# Error: "focus parameter requires Pro or Enterprise tier"

# Community trying comprehensive detail
get_project_map(project_root="./", detail_level="comprehensive")
# Error: "detail_level='comprehensive' requires Enterprise tier"

# Pro exceeding size limit
get_project_map(project_root="./", max_inline_size_mb=15.0)
# Error: "max_inline_size_mb cannot exceed 10.0 MB for Pro tier"
```

---

### **Conflicting Flags**

```python
# Conflicting modes
get_project_map(project_root="./", output_mode="summary", detail_level="comprehensive")
# Warning: "output_mode='summary' overrides detail_level. Using summary."

# Invalid combination
get_project_map(project_root="./", output_mode="chunked", format="csv")
# Error: "format='csv' not compatible with output_mode='chunked'"
```

---

## Benefits of This Design

### **1. Backwards Compatibility** ✅
- Existing calls work unchanged
- Intelligent defaults handle 95% of cases

### **2. Progressive Disclosure** ✅
- Basic users get simple output
- Power users unlock advanced features
- No overwhelming flag count for beginners

### **3. Tier-Appropriate** ✅
- Community: Simple, educational
- Pro: Production-ready, efficient
- Enterprise: Maximum flexibility

### **4. Escape Hatches** ✅
- Users CAN get 6.8 MB inline if they really want it
- Warnings prevent accidental misuse
- Explicit flags required for dangerous operations

### **5. Flexibility** ✅
- Mix and match flags for custom workflows
- Support CI/CD, documentation, analysis use cases
- Future-proof (easy to add new flags)

---

## Recommendation

**Implement in phases**:

1. **Phase 1 (Immediate)**: `output_mode`, `detail_level`, `max_inline_size_mb`
   - Solves the 6.8 MB problem
   - Gives users control over verbosity
   - Maintains backwards compatibility

2. **Phase 2 (Short-term)**: `include`, `exclude`, `focus`
   - Enables targeted analysis
   - Reduces noise for specific use cases

3. **Phase 3 (Medium-term)**: `query`, `format`, `chunk_by`
   - Enterprise power features
   - Advanced workflows

**Total effort**: ~12-15 hours spread across 3 releases

**Impact**: Transforms tool from "one-size-fits-all" to "configurable intelligence"
