# Large Output Handling Strategy for MCP Tools

**Created**: January 4, 2026  
**Context**: Analysis of get_project_map Enterprise output (6.8 MB)  
**Status**: DESIGN COMPLETE - READY FOR IMPLEMENTATION

---

## Problem Statement

MCP tools can produce massive outputs (> 1 MB) that are:
- **Too large for chat display** (token/character limits)
- **Difficult to work with** (cannot be copy-pasted)
- **Not efficiently queryable** (monolithic JSON)
- **Problematic for streaming** (long transfer times)

**Example**: `get_project_map` on 2,028-file project → 6.8 MB output

---

## Decision Tree for Output Size

```
Tool execution complete
    │
    ├─ Output size < 100 KB
    │  └─ Return in chat (normal response)
    │
    ├─ Output size 100 KB - 1 MB
    │  └─ Return in chat + mention file saved
    │
    ├─ Output size 1 MB - 10 MB
    │  ├─ Output to file automatically
    │  ├─ Return summary + file path
    │  └─ (CURRENT: get_project_map Enterprise)
    │
    └─ Output size > 10 MB
       ├─ Chunk into multiple files
       ├─ Provide index file
       └─ Return navigation guide
```

---

## Implementation Options

### Option 1: Automatic File Output (RECOMMENDED for v1)

**When to use**: Project with 500+ files

**Behavior**:
```python
def get_project_map(project_root, ...):
    result = analyze_project(project_root)
    
    # Check output size
    output_json = json.dumps(result)
    size_mb = len(output_json) / (1024 * 1024)
    
    if size_mb > 1:  # Automatic file output
        output_file = f"project_map_{timestamp}.json"
        with open(output_file, 'w') as f:
            f.write(output_json)
        
        return {
            "status": "success",
            "file": output_file,
            "size_mb": size_mb,
            "summary": {
                "total_files": result["total_files"],
                "packages": len(result["packages"]),
                "entry_points": len(result["entry_points"])
            }
        }
    else:
        return result  # Return in chat as normal
```

**Advantages**:
- ✅ Simple to implement
- ✅ No breaking changes
- ✅ Works immediately for large projects
- ✅ Users still see summary in chat

**Disadvantages**:
- ❌ Still monolithic files (not chunked)
- ❌ No performance improvement (16+ min still slow)
- ❌ Limited queryability

---

### Option 2: Chunked Output with Index (RECOMMENDED for v2)

**When to use**: Projects > 1,000 files

**Structure**:
```
project_map_20260104_1200/
├── index.json                    (navigation + metadata)
├── summary.json                  (statistics only)
├── packages_0.json              (packages 0-99)
├── packages_1.json              (packages 100-199)
├── modules_0.json               (modules 0-999)
├── modules_1.json               (modules 1000-1999)
├── modules_2.json               (modules 2000-2028)
├── dependencies.json            (all import relationships)
├── git_history.json             (commit activity)
└── diagram.mmd                  (architecture diagram)
```

**Index file example**:
```json
{
  "version": "1.0",
  "generated": "2026-01-04T12:00:00Z",
  "total_size_mb": 6.8,
  "execution_time_seconds": 1016,
  "chunks": {
    "packages": {
      "total": 127,
      "files": ["packages_0.json", "packages_1.json"],
      "items_per_file": 100
    },
    "modules": {
      "total": 2028,
      "files": ["modules_0.json", "modules_1.json", "modules_2.json"],
      "items_per_file": 1000
    }
  },
  "quick_stats": {
    "total_files": 2028,
    "languages": {"python": 2028, "json": 518, ...},
    "complexity_avg": 7.2,
    "stability_score": 0.57
  },
  "entry_points": [
    "src/code_scalpel/__main__.py:main",
    "tests/run_tests.py:main"
  ]
}
```

**Advantages**:
- ✅ Modular and organized
- ✅ Can load specific chunks only
- ✅ Easy to version control (diffs per chunk)
- ✅ Supports incremental updates
- ✅ Better for pagination

**Disadvantages**:
- ❌ More complex implementation
- ❌ Requires index parsing first
- ❌ Still doesn't solve performance issue

---

### Option 3: Database Backend (RECOMMENDED for v3+)

**When to use**: Interactive queries needed

**Architecture**:
```
get_project_map()
  ├─ Create/update SQLite database
  ├─ Load packages table
  ├─ Load modules table
  ├─ Load dependencies table (indexed)
  ├─ Load git_history table
  └─ Return database path + quick stats

User can then:
  └─ Query for specific packages
  └─ Find all dependents of a module
  └─ Analyze import patterns
  └─ Track file changes
```

**API Example**:
```python
# Get all modules in a package
SELECT * FROM modules WHERE package = 'code_scalpel' LIMIT 100;

# Find circular dependencies
SELECT a, b FROM dependencies WHERE b IN (
  SELECT source FROM dependencies WHERE target = a
);

# Most changed files
SELECT file, change_count FROM git_history 
ORDER BY change_count DESC LIMIT 10;
```

**Advantages**:
- ✅ Interactive queries
- ✅ Efficient filtering
- ✅ Scalable to very large projects
- ✅ Supports incremental updates
- ✅ Natural pagination

**Disadvantages**:
- ❌ Complex implementation
- ❌ Requires schema design
- ❌ More dependencies (sqlite3, etc.)
- ❌ Not human-readable (need query tool)

---

## Phased Implementation Plan

### Phase 1: Immediate (Next Release)
**Goal**: Stop outputting 6.8 MB to chat

**Implementation**:
1. Add size check in all large-output tools
2. Auto-write to file if > 1 MB
3. Return summary in chat instead
4. Document file location for users

**Tools affected**: 
- `get_project_map` (MAIN CASE)
- `crawl_project` (potentially)
- `cross_file_security_scan` (on large projects)

**Effort**: 2-3 hours

---

### Phase 2: Short-term (v1.1)
**Goal**: Improve queryability and structure

**Implementation**:
1. Implement chunked output for > 1 MB
2. Create index files
3. Add `--format` flag (json/chunked/summary)
4. Add progress indicators

**Tools affected**: 
- `get_project_map`
- `crawl_project`

**Effort**: 4-6 hours

---

### Phase 3: Medium-term (v1.2)
**Goal**: Solve performance and interactivity

**Implementation**:
1. Parallel analysis for get_project_map
2. Incremental analysis support
3. Basic query helpers
4. Caching layer

**Tools affected**: 
- `get_project_map` (main optimization target)

**Effort**: 8-12 hours

---

### Phase 4: Long-term (v2.0)
**Goal**: Production-grade solution

**Implementation**:
1. Full database backend
2. Query API
3. Web UI for exploration
4. Export formats (JSON, CSV, etc.)

**Effort**: 20+ hours

---

## Recommendation for code-scalpel Project

### Immediate Action (Next 24 hours)

✅ **DOCUMENT & DECIDE**: This analysis document is ready to guide decisions

**Key decision**: Should get_project_map auto-output to file?
- **YES**: Implement Phase 1 immediately
- **MAYBE**: Add flag `--auto-file` for testing
- **NO**: Require manual `--output-file` flag

---

## Configuration Approach

### Environment Variable
```bash
export SCALPEL_AUTO_FILE_SIZE_MB=1
# Tool will automatically write to file if output > 1 MB
```

### Command-line Flag
```bash
python -m code_scalpel.tools.get_project_map \
  --project /path/to/code \
  --auto-file              # Enable auto-file output
  --chunk-size 100         # If chunking, chunk at 100 items
  --output-dir ./results   # Where to save files
```

### Configuration File
```toml
# .code-scalpel/limits.toml
[tools.get_project_map]
auto_file_size_mb = 1
chunk_size = 1000
output_format = "chunked"  # json, chunked, database
```

---

## Testing Strategy for Large Output Handling

### Test Cases

1. **Small project** (< 10 files)
   - Verify output goes to chat
   - No file created

2. **Medium project** (100-500 files)
   - Verify output goes to chat + file
   - File can be read and parsed

3. **Large project** (500+ files)
   - Verify auto-file output works
   - Verify summary is accurate
   - Verify file is valid JSON/chunks

4. **Chunked output**
   - Verify all chunks can be loaded
   - Verify index is accurate
   - Verify no data loss

5. **Performance**
   - Measure analysis time vs project size
   - Identify bottlenecks
   - Profile memory usage

---

## Deliverables

✅ **Completed**:
- [x] Output analysis (ENTERPRISE_OUTPUT_ANALYSIS.md)
- [x] Implementation strategy (this document)
- [x] Decision framework
- [x] Phased implementation plan

📋 **Next Steps**:
- [ ] Implement Phase 1 (auto-file output)
- [ ] Add size warnings
- [ ] Update tool documentation
- [ ] Add test cases
- [ ] Monitor actual usage

---

## Summary Table

| Aspect | Current | Phase 1 | Phase 2 | Phase 3+ |
|--------|---------|---------|---------|----------|
| Output Method | Chat | File | Chunked | Database |
| Max Size | 6.8 MB | 1 MB per file | 100 KB per file | Unlimited |
| Query Support | None | grep only | Index queries | SQL |
| Performance | 16+ min | 16+ min | < 1 min | < 1 min |
| Scalability | Limited | 5K files | 50K files | 1M+ files |
| Implementation Effort | - | 2-3 hrs | 4-6 hrs | 20+ hrs |

---

**Status**: ANALYSIS COMPLETE & ACTIONABLE  
**Ready for**: Team discussion and Phase 1 implementation planning
