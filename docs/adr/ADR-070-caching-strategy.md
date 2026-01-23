<!-- [20251215_DOCS] ADR-007: Analysis Caching Strategy -->

# ADR-007: Analysis Caching Strategy

**Status:** Accepted  
**Date:** 2025-12-15  
**Authors:** Code Scalpel Team  
**Supersedes:** None

---

## Context

Code analysis operations (AST parsing, PDG building, symbolic execution) can be expensive. When analyzing large projects or making incremental changes, re-analyzing unchanged code wastes resources.

### Requirements

| Requirement | Priority |
|-------------|----------|
| Cache AST and PDG analysis results | Must Have |
| Invalidate cache when source changes | Must Have |
| Support incremental analysis | Should Have |
| Configurable cache size limits | Should Have |
| Thread-safe cache access | Must Have |

---

## Decision

We will implement a **Content-Hash Based Caching** system with LRU eviction.

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Source Code                             │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
              ┌───────────────────────┐
              │   Content Hash        │
              │   (SHA-256)           │
              └───────────────────────┘
                          │
                          ▼
              ┌───────────────────────┐
              │   Cache Lookup        │
              │   (LRU Cache)         │
              └───────────────────────┘
                    │           │
              ┌─────┘           └─────┐
              ▼                       ▼
        [Cache Hit]             [Cache Miss]
              │                       │
              ▼                       ▼
        Return Result           Run Analysis
                                      │
                                      ▼
                                Store in Cache
                                      │
                                      ▼
                                Return Result
```

### Cache Key Generation

```python
def generate_cache_key(code: str, analysis_type: str, options: dict) -> str:
    content_hash = hashlib.sha256(code.encode()).hexdigest()[:16]
    options_hash = hashlib.sha256(json.dumps(options, sort_keys=True).encode()).hexdigest()[:8]
    return f"{analysis_type}:{content_hash}:{options_hash}"
```

### Cache Configuration

```python
CACHE_CONFIG = {
    "max_entries": 1000,
    "max_memory_mb": 500,
    "ttl_seconds": 3600,  # 1 hour
    "persist_to_disk": False,
    "cache_dir": ".code_scalpel_cache"
}
```

---

## Cached Analysis Types

| Analysis | Cache Key Includes | TTL |
|----------|-------------------|-----|
| AST Parse | code hash | 1 hour |
| PDG Build | code hash + options | 1 hour |
| Security Scan | code hash + config | 30 min |
| Symbolic Execution | code hash + depth + fuel | 15 min |

### Cache Invalidation

Automatic invalidation occurs when:
1. Source code content changes (different hash)
2. Analysis options change
3. TTL expires
4. Cache size limit exceeded (LRU eviction)

Manual invalidation:
```python
analyzer.clear_cache()  # Clear all
analyzer.clear_cache(file_path="/path/to/file.py")  # Clear specific
```

---

## Implementation Details

### Thread Safety

```python
from threading import RLock

class AnalysisCache:
    def __init__(self):
        self._cache = {}
        self._lock = RLock()
    
    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            return self._cache.get(key)
    
    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self._cache[key] = value
```

### Memory Management

```python
def _evict_if_needed(self):
    while self._current_size > self._max_size:
        oldest_key = self._access_order.pop(0)
        del self._cache[oldest_key]
```

---

## Consequences

### Positive

1. **Performance:** 10-100x speedup for repeated analysis
2. **Incremental Analysis:** Only changed files re-analyzed
3. **Resource Efficiency:** Reduced CPU and memory usage
4. **Predictability:** Same input = same output (deterministic)

### Negative

1. **Memory Usage:** Cache consumes memory
2. **Staleness Risk:** Bugs if invalidation fails
3. **Complexity:** Additional code paths to maintain

### Mitigations

- Configurable cache size limits
- Content-hash ensures automatic invalidation
- Comprehensive cache tests

---

## Implementation

- **Location:** `src/code_scalpel/cache/`
- **Files:**
  - `analysis_cache.py` - Main cache implementation
  - `incremental_analyzer.py` - Incremental analysis orchestration
  - `parallel_parser.py` - Parallel parsing with caching

---

## References

- [Architecture: Scalability Analysis](../architecture/SCALABILITY_ANALYSIS.md)
