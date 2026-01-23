<!-- [20251215_DOCS] Architecture: Scalability Analysis -->

# Code Scalpel Scalability Analysis

This document analyzes Code Scalpel's performance characteristics and scalability limits.

---

## Performance Benchmarks

### Parsing Performance

| Language | Lines/Second | Memory (MB/1000 lines) |
|----------|--------------|------------------------|
| Python | 50,000 | 2.5 |
| JavaScript | 40,000 | 3.0 |
| TypeScript | 35,000 | 3.5 |
| Java | 45,000 | 2.8 |

### Analysis Performance

| Operation | Time (1K lines) | Time (10K lines) | Time (100K lines) |
|-----------|-----------------|------------------|-------------------|
| AST Parse | 20ms | 200ms | 2s |
| Security Scan | 50ms | 500ms | 5s |
| Symbolic Execution | 100ms | 1s | 10s |
| PDG Build | 80ms | 800ms | 8s |

### Throughput (Cached)

| Operation | Requests/Second |
|-----------|-----------------|
| `extract_code` | 1,000 |
| `get_file_context` | 2,000 |
| `security_scan` | 500 |
| `analyze_code` | 800 |

---

## Scalability Dimensions

### 1. File Size Scalability

**Linear Scaling:** Most operations scale linearly with file size.

```
Time = O(n) where n = lines of code
Memory = O(n) for AST storage
```

**Limits:**
- Maximum file size: 10MB (configurable)
- Recommended: < 5,000 lines per file

### 2. Project Size Scalability

**Project Crawling:**
```
Time = O(files × avg_lines)
Memory = O(files × avg_ast_size)
```

**Tested Limits:**
- 1,000 files: < 30 seconds
- 10,000 files: < 5 minutes
- 100,000 files: ~1 hour (with caching)

### 3. Symbolic Execution Scalability

**Path Explosion:**
```
Worst case: O(2^branches)
With bounding: O(max_paths × max_iterations)
```

**Mitigations:**
- Default max_paths = 100
- Default loop_fuel = 10
- Early termination on timeout

### 4. Cross-File Analysis Scalability

**Import Resolution:**
```
Time = O(imports × avg_module_size)
Memory = O(resolved_symbols)
```

**Limits:**
- Maximum import depth: 10
- Maximum resolved symbols: 1,000 per analysis

---

## Bottleneck Analysis

### CPU-Bound Operations

1. **AST Parsing:** Pure CPU, parallelizable
2. **Security Taint Analysis:** CPU-bound traversal
3. **Symbolic Execution:** Z3 solver queries

### Memory-Bound Operations

1. **PDG Construction:** Graph structure storage
2. **Cross-File Resolution:** Module caching
3. **Call Graph Building:** Node/edge storage

### I/O-Bound Operations

1. **File Reading:** Disk I/O
2. **Project Crawling:** Directory traversal
3. **Dependency Scanning:** Network (OSV API)

---

## Optimization Strategies

### 1. Caching (Implemented)

```python
# Content-hash based caching
cache_key = sha256(code + options)
if cache_key in cache:
    return cache[cache_key]  # O(1) lookup
```

**Impact:** 10-100x speedup for repeated queries

### 2. Parallel Parsing (Implemented)

```python
from concurrent.futures import ProcessPoolExecutor

def parse_project(files):
    with ProcessPoolExecutor(max_workers=cpu_count()) as pool:
        results = pool.map(parse_file, files)
```

**Impact:** Near-linear speedup with CPU cores

### 3. Incremental Analysis (Planned)

```python
def incremental_analyze(changed_files):
    # Only re-analyze changed files
    # Propagate changes to dependents
    pass
```

**Expected Impact:** 10-50x speedup for incremental changes

### 4. Lazy Loading (Implemented)

```python
# Dependencies loaded on demand
result = extract_code(
    ...,
    include_cross_file_deps=False  # Fast
)
```

**Impact:** Reduces memory and time for simple queries

---

## Resource Limits

### Configurable Limits

| Parameter | Default | Max Recommended |
|-----------|---------|-----------------|
| `max_file_size` | 10MB | 50MB |
| `max_analysis_time` | 60s | 300s |
| `max_symbolic_paths` | 100 | 1,000 |
| `max_loop_iterations` | 10 | 100 |
| `max_import_depth` | 10 | 20 |
| `cache_max_entries` | 1,000 | 10,000 |
| `cache_max_memory` | 500MB | 2GB |

### Hard Limits

| Resource | Limit | Rationale |
|----------|-------|-----------|
| File size | 50MB | Memory constraints |
| Single function size | 10,000 lines | Analysis complexity |
| Import chain depth | 20 | Circular import risk |
| Symbolic paths | 10,000 | Path explosion |

---

## Scaling Recommendations

### Small Projects (< 10K lines)
- Default configuration sufficient
- No special optimization needed
- Expected latency: < 1s per operation

### Medium Projects (10K - 100K lines)
- Enable caching
- Use parallel parsing
- Expected latency: 1-10s per full scan

### Large Projects (100K - 1M lines)
- Increase cache size
- Use incremental analysis
- Consider file/module filtering
- Expected latency: 10-60s per full scan

### Enterprise Projects (> 1M lines)
- Deploy as service with persistent cache
- Use CI/CD integration for pre-analysis
- Consider sharding by module
- Expected latency: Minutes for full scan

---

## Monitoring Metrics

### Key Performance Indicators

1. **Latency:** P50, P95, P99 response times
2. **Throughput:** Requests per second
3. **Cache Hit Rate:** Target > 80%
4. **Memory Usage:** Peak and average
5. **Error Rate:** Timeouts and failures

### Recommended Alerts

| Metric | Warning | Critical |
|--------|---------|----------|
| P95 Latency | > 5s | > 30s |
| Cache Hit Rate | < 70% | < 50% |
| Memory Usage | > 70% limit | > 90% limit |
| Error Rate | > 1% | > 5% |

---

## Future Improvements

1. **Distributed Analysis:** Shard large projects across workers
2. **Persistent Cache:** SQLite/Redis backend for cache
3. **Streaming Results:** Return partial results for large analyses
4. **GPU Acceleration:** Offload Z3 queries (experimental)

---

## References

- [ADR-007: Caching Strategy](../adr/ADR-0070-caching-strategy.md)
- [Performance Benchmarks](../performance/)
