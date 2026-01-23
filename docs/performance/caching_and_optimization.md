# Performance Configuration Guide <!-- [20251214_DOCS] v1.5.5 -->

## Overview

Code Scalpel v1.5.5 introduces significant performance optimizations for large project analysis:
- **Caching Layer:** Memory + disk cache with content-based hash invalidation
- **Parallel Parsing:** Batched ProcessPoolExecutor for multi-core utilization
- **Incremental Analysis:** Dependency-aware cache invalidation for single-file updates
- **Memory-Mapped I/O:** Efficient hashing for large files (>1MB)

## Performance Targets

| Operation | 1000+ Files | Target |
|-----------|-------------|--------|
| Full project analysis | 3.1s | <10s [COMPLETE] |
| Incremental update | <1ms | <1s [COMPLETE] |
| Cache hit rate (warm) | 100% | - |

## Configuration Options

### AnalysisCache

```python
from code_scalpel.cache import AnalysisCache

# Default: cache in .code_scalpel_cache/
cache = AnalysisCache()

# Custom cache directory
cache = AnalysisCache(cache_dir="/path/to/cache")

# Access statistics
stats = cache.stats.to_dict()
# {memory_hits, disk_hits, misses, stores, invalidations, hit_rate, ...}
```

### ParallelParser

```python
from code_scalpel.cache import ParallelParser, AnalysisCache

cache = AnalysisCache()

# Default: max_workers=os.cpu_count(), batch_size=100
parser = ParallelParser(cache)

# Custom configuration
parser = ParallelParser(
    cache,
    max_workers=8,      # Limit worker processes
    batch_size=50       # Files per batch (reduce for low memory)
)
```

### Memory-Mapped File Hashing

Files larger than 1MB are automatically hashed using memory-mapped I/O. This is controlled by the `MMAP_THRESHOLD_BYTES` constant:

```python
from code_scalpel.cache.analysis_cache import MMAP_THRESHOLD_BYTES
# Default: 1MB (1 * 1024 * 1024)
```

## Tuning Guidelines

### For Large Projects (1000+ files)

1. **Cold Start:** Expect 3-5s for initial analysis
2. **Warm Start:** Subsequent runs benefit from disk cache
3. **Batch Size:** Default 100 is optimal; reduce to 50 for memory-constrained environments

### For Incremental Updates

1. Use `IncrementalAnalyzer.get_dependents(file)` to identify affected modules
2. Re-parse only affected files instead of full project
3. Single-file operations complete in <1ms

### Memory Trade-offs

| Setting | Memory | Speed |
|---------|--------|-------|
| batch_size=100 | Higher | Faster |
| batch_size=25 | Lower | Slower |
| Disk cache enabled | Disk I/O | Persistent |

## Cache Management

### Clear Cache

```python
import shutil
shutil.rmtree(".code_scalpel_cache", ignore_errors=True)
```

### Invalidate Single File

```python
cache.invalidate("/path/to/modified_file.py")
```

### Monitor Cache Effectiveness

```python
print(f"Hit rate: {cache.stats.hit_rate:.1%}")
print(f"Memory hits: {cache.stats.memory_hits}")
print(f"Disk hits: {cache.stats.disk_hits}")
print(f"Misses: {cache.stats.misses}")
```

## Known Limitations

1. **Warm vs Cold:** Disk cache can be slower than cold start for bulk analysis due to serial I/O. Disk cache is optimized for incremental updates, not full re-analysis.

2. **Windows Pickling:** Parallel parser uses top-level functions to avoid Windows spawn pickling issues. Custom parse functions must be picklable.

3. **Large Files:** Files >10MB may still cause memory pressure even with mmap. Consider chunked analysis for very large files.
