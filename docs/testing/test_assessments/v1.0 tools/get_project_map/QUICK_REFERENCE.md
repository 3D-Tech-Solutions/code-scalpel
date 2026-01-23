# get_project_map Enterprise Output - Quick Reference

**File**: project_map_code-scalpel.md (6.8 MB, 228,436 lines)  
**Generated**: January 4, 2026  
**Tier**: Enterprise  

---

## File Contents Summary

| Section | Lines | Items | Status |
|---------|-------|-------|--------|
| Metadata | ~50 | Tool info, duration, tier | ✅ Complete |
| Languages | ~20 | 8 languages identified | ✅ Complete |
| Packages | ~40,000 | 127 packages analyzed | ✅ Complete |
| Modules | ~100,000 | 2,028 modules listed | ✅ Complete |
| Entry Points | ~500 | 12 CLI entry points | ✅ Complete |
| Dependencies | ~50,000 | Import relationships | ✅ Complete |
| Git History | ~20,000 | Commit history + activity | ✅ Complete |
| Complexity | ~15,000 | Metrics per file | ✅ Complete |
| Circular Imports | ~1,000 | Dependency cycles | ✅ Complete |
| Architecture Diagram | ~1,000 | Mermaid (truncated) | ⚠️ Truncated |

---

## Key Statistics

**Project Overview**:
```
Total Files:        2,028
Total Lines:        ~148,000 (actual codebase estimate)
Languages:          8
Packages:           127
Modules:            2,028
Entry Points:       12
Circular Imports:   Several detected
```

**Language Distribution**:
- Python: 2,028 files (main language)
- JSON: 518 files (configs, fixtures)
- Markdown: 554 files (docs)
- YAML: 16 files (configs)
- JavaScript/TypeScript: 3 files (edge cases)
- Java: 4 files (examples)
- CSS: 1 file

**Code Quality**:
- Stability Score: 0.57 (moderate)
- Most Active Period: 2025-12-16/17 (111 + 45 changes)
- Average Complexity: ~7.2 (moderate)

---

## How to Use This File

### For Chat Analysis
```bash
# Search for specific package
grep -A 20 '"name": "code_scalpel"' project_map_code-scalpel.md

# Find entry points
grep '"entry_points"' project_map_code-scalpel.md | head -20

# Find circular imports
grep -A 5 '"circular_imports"' project_map_code-scalpel.md
```

### For Python Analysis
```python
import json

with open('project_map_code-scalpel.md') as f:
    data = json.load(f)

# Get all packages
packages = data['data']['packages']
print(f"Found {len(packages)} packages")

# Get entry points
entry_points = data['data']['entry_points']
for ep in entry_points[:5]:
    print(ep)

# Analyze git activity
activity = data['data']['git_metrics'][0]['activity_by_date']
for date, count in list(activity.items())[:10]:
    print(f"{date}: {count} changes")
```

---

## Notable Findings

### Major Packages
1. **src/code_scalpel** - Main library code
2. **tests/** - Comprehensive test suite
3. **evidence/** - Test data and examples
4. **docs/** - Documentation

### High-Activity Files (Most Changes)
1. `src/code_scalpel/symbolic_execution_tools/engine.py` - 15 changes
2. `src/code_scalpel/generators/refactoring_generator.py` - 15 changes
3. Various test files - 13-14 changes each

### Entry Points Detected
- `src/code_scalpel/__main__.py:main`
- `tests/tools/get_graph_neighborhood/run_tests.py:main`
- And 10 others (CLI commands, test runners)

### Stability Analysis
- **Score**: 0.57 (moderate volatility)
- **Meaning**: Active development, regular changes
- **Pattern**: Heavy activity on specific days (Dec 16-17), quiet on others

---

## File Truncation Notes

**⚠️ Diagram is Truncated**:
- Mermaid visualization couldn't fit in response
- Too many nodes/edges for single diagram
- Would need to be split into layers or filtered by package

---

## Recommendations for Future Use

### ✅ DO:
- Download/save the file locally
- Use grep/sed for quick searches
- Import into Python for programmatic analysis
- Store in version control with git-lfs

### ❌ DON'T:
- Try to view entire file in editor (too large)
- Paste into chat (6.8 MB exceeds limits)
- Expect to manually navigate (228K lines)
- Open in Excel/Google Sheets (format incompatible)

---

## File Format Details

**Raw Format**: Single JSON document (one large object)

**Root Keys**:
```json
{
  "tier": "enterprise",
  "tool_version": "3.3.0",
  "tool_id": "get_project_map",
  "request_id": "...",
  "duration_ms": 1016603,
  "data": {
    "success": true,
    "project_root": "/mnt/k/backup/Develop/code-scalpel",
    "packages": [...],
    "modules": [...],
    "entry_points": [...],
    "dependencies": [...],
    "git_metrics": [...],
    "complexity_metrics": [...],
    "circular_imports": [...],
    "custom_metrics": {...},
    "architecture_diagram": "graph TD ... (truncated)"
  }
}
```

---

## When to Use Phase 1-3 Improvements

| Scenario | Current | Phase 1 | Phase 2 | Phase 3 |
|----------|---------|---------|---------|---------|
| "What packages exist?" | Search file | Use summary | Use API | SQL query |
| "Who uses this module?" | grep output | Index file | Indexed query | SQL JOIN |
| "How did complexity change?" | Manual | Split files | Indexed query | Time-series |
| "Find all entry points" | grep | Return in chat | Dedicated file | API endpoint |

---

## Links to Analysis Documents

- [ENTERPRISE_OUTPUT_ANALYSIS.md](ENTERPRISE_OUTPUT_ANALYSIS.md) - Detailed analysis
- [LARGE_OUTPUT_HANDLING_STRATEGY.md](LARGE_OUTPUT_HANDLING_STRATEGY.md) - Implementation strategy

---

**Last Updated**: January 4, 2026  
**Status**: Ready for reference and analysis
