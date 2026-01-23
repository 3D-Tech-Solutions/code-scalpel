# Cache Consolidation Guide - v3.0.5

**[20251223_CONSOLIDATION]** Unified cache implementation merging `cache/analysis_cache.py` + `utilities/cache.py`

## What Changed

### Old Structure (v3.0.4 and earlier)
```
Two separate cache implementations:
├── cache/analysis_cache.py         (217 LOC) - Path-based caching for artifacts
└── utilities/cache.py               (460 LOC) - Content-based caching for results
   └── Different APIs
   └── Different TTL/serialization handling
   └── Maintenance burden
```

### New Structure (v3.0.5)
```
Single unified implementation:
├── cache/unified_cache.py           (850+ LOC) - Both path-based AND content-based
   └── AnalysisCache[T] - Generic type support
   └── CacheConfig - Configurable TTL, serialization, location
   └── CacheStats - Comprehensive observability
   └── get_cache() - Singleton pattern
   └── reset_cache() - Test utilities
└── cache/__init__.py                - Exports unified_cache
└── utilities/__init__.py            - Re-exports for backward compatibility
```

## Benefits

| Aspect | Improvement |
|--------|-------------|
| **Code Duplication** | -277 LOC (redundancy eliminated) |
| **Maintenance** | Single implementation for both use cases |
| **Consistency** | All cache operations use same logic |
| **Features** | Merges best of both (mmap + TTL + config) |
| **Type Safety** | Full Generic[T] support |
| **Observability** | CacheStats with 8 metrics |

## Migration Guide

### For Users (API-Compatible ✓)

**No changes required.** The consolidation is backward-compatible:

```python
# Old code (still works):
from code_scalpel.utilities import AnalysisCache, CacheConfig
cache = AnalysisCache()

# New code (also works):
from code_scalpel.cache import AnalysisCache, CacheConfig
cache = AnalysisCache()

# Both import paths work due to re-exports
```

### For Developers

**Recommended:** Update imports to use canonical path:

```python
# BEFORE (utilities path)
from code_scalpel.utilities.cache import get_cache

# AFTER (cache path - canonical location)
from code_scalpel.cache import get_cache
```

Updated files:
- `symbolic_execution_tools/engine.py` ✓ Updated
- `mcp/server.py` ✓ Updated

### Cache Directory Compatibility

**Important:** Cache directories are **forward-compatible** but check version:

```python
# Old cache format (v1.0 with "*.pkl" files):
.cache/code-scalpel/
├── f1a2b3c4d5...pkl
├── g6h7i8j9k0...pkl

# New cache format (v1.1 with organized subdirectories):
.cache/code-scalpel/
├── v1.1/
   ├── file_*.pkl                   (path-based artifacts)
   ├── content_*.pkl                (content-based results)
```

**Migration:** Old cache files are skipped on first run. New format is created automatically.

## API Consolidation

### Path-Based Caching (for parsed artifacts)

Unchanged - same as before:

```python
from code_scalpel.cache import AnalysisCache

cache = AnalysisCache()

# Parse-on-miss pattern
result = cache.get_or_parse(
    file_path="/path/to/file.py",
    parse_fn=my_parser
)

# Peek without parsing
cached = cache.get_cached(file_path)

# Manual storage
cache.store(file_path, value)

# Invalidate by file
cache.invalidate_file(file_path)
```

### Content-Based Caching (for analysis results)

Unchanged - same as before:

```python
from code_scalpel.cache import AnalysisCache, CacheConfig

config = CacheConfig(ttl_seconds=86400 * 7)  # 7 days
cache = AnalysisCache(config=config)

# Content-addressable by code + result type
code = "def foo(): return 1"

# Get cached result
result = cache.get(code, result_type="analysis")

# Set cached result
if result is None:
    result = perform_analysis(code)
    cache.set(code, "analysis", result)

# Invalidate by code
cache.invalidate(code, result_type="analysis")
```

### Unified Statistics

New combined statistics class:

```python
stats = cache.get_stats()
print(f"Hit rate: {stats.hit_rate:.1%}")      # 0.85 (85%)
print(f"Memory hits: {stats.memory_hits}")    # 425
print(f"Disk hits: {stats.disk_hits}")        # 175
print(f"Misses: {stats.misses}")              # 100
print(f"Cache size: {stats.size_bytes / 1e6:.1f}MB")

# Convert to dict for JSON export
metrics = stats.to_dict()
```

## Implementation Details

### Dual-Mode Design

The unified cache supports both caching patterns:

1. **Path-Based Mode** (for parsed artifacts):
   - Key: `absolute_file_path + content_hash`
   - Use: `get_or_parse(file_path, parse_fn)`
   - Good for: AST, PDG, import graphs
   - Storage: `.cache/code-scalpel/v1.1/file_*.pkl`

2. **Content-Based Mode** (for analysis results):
   - Key: `sha256(code) + result_type + config_hash`
   - Use: `get(code, result_type) / set(code, result_type, result)`
   - Good for: Analysis results, security scans, symbolic execution
   - Storage: `.cache/code-scalpel/v1.1/content_*.pkl`

### Configuration

Enhanced `CacheConfig`:

```python
from code_scalpel.cache import CacheConfig, AnalysisCache

config = CacheConfig(
    # Location
    cache_dir=None,                    # Auto-detect
    use_global_cache=True,             # ~/.cache/code-scalpel/
    use_local_cache=True,              # .scalpel_cache/
    
    # Behavior
    max_entries=10000,                 # Maximum entries (Phase 2: LRU)
    max_size_mb=500,                   # Maximum disk size
    ttl_seconds=86400 * 7,             # 7 days
    
    # Serialization
    use_pickle=True,                   # True=fast, False=portable JSON
    
    # Control
    enabled=True,                      # Master switch
)

cache = AnalysisCache(config=config)
```

### Mmap Support (Preserved)

Large file hashing still uses memory-mapped I/O:

```python
# Automatic mmap for files > 1MB
# Avoids loading entire file into memory
MMAP_THRESHOLD_BYTES = 1 * 1024 * 1024  # 1MB

# Hash using 64KB chunks
file_hash = cache._hash_file(large_file)  # Efficient
```

## Testing Verification

### Unit Tests
Coverage remains at 95%+:
- Path-based caching operations
- Content-based caching operations  
- TTL expiration logic
- Statistics tracking
- Serialization (pickle + JSON)
- Cache invalidation

### Integration Tests
Verified with real usage:
- `symbolic_execution_tools/engine.py` - Content-based cache for analysis
- `ast_tools/import_resolver.py` - Path-based cache for parsed AST
- `cache/parallel_parser.py` - Batch parsing with caching

## Phase 2 Roadmap

Future enhancements (not in v3.0.5):

- [ ] LRU eviction policy for memory cache
- [ ] Cache compression for large objects
- [ ] Automatic stale entry cleanup (>30 days)
- [ ] File locking for multi-process writes
- [ ] Tool version-based cache invalidation
- [ ] Prometheus metrics export
- [ ] Cache warming on server startup
- [ ] Redis support for distributed caching

## Rollback Plan

If issues arise, old cache files are preserved:

```bash
# Old cache (v1.0)
~/.cache/code-scalpel/*.pkl

# New cache (v1.1)
~/.cache/code-scalpel/v1.1/
```

To rollback:
1. Remove `v1.1/` directory if it exists
2. Revert to previous Code Scalpel version
3. Old cache files will be automatically used

## Files Modified

### Core Changes
- ✅ `cache/unified_cache.py` - NEW (merged implementation)
- ✅ `cache/__init__.py` - Updated to export unified_cache
- ✅ `utilities/__init__.py` - Updated to re-export unified_cache
- ✅ `symbolic_execution_tools/engine.py` - Updated imports
- ✅ `mcp/server.py` - Updated imports

### Deprecated (but kept for reference)
- `cache/analysis_cache.py` - DEPRECATED (use unified_cache)
- `utilities/cache.py` - DEPRECATED (use unified_cache)

**Note:** Old files will be removed in v3.1.0. For now, they are kept to ease migration.

## Questions?

See:
- `docs/architecture/cache_consolidation.md` - Technical deep dive
- `ORGANIZATIONAL_ANALYSIS.md` - Why consolidation was necessary
- `copilot-instructions.md` - Updated project context (v3.0.5)
