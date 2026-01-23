"""Unified Analysis Cache for Code Scalpel.

[20251223_CONSOLIDATION] v3.0.5 - Merged analysis_cache.py + utilities cache.py

This module provides a unified caching layer supporting:
- File-based caching (for parsed artifacts with path-aware keys)
- Content-addressable caching (for analysis results with SHA-256 keys)
- Memory + disk hybrid with configurable TTL
- Multiple result types: "analysis", "security", "symbolic", "tests"
- Mmap support for large files
- Statistics tracking for observability

The cache uses two complementary approaches:
1. Path-based keys (file path + content hash) for parsed code artifacts
2. Content-based keys (SHA-256 hash) for analysis results

Example:
    >>> from code_scalpel.cache import AnalysisCache, CacheConfig
    >>>
    >>> # Path-based caching (for parsed artifacts)
    >>> cache = AnalysisCache()
    >>> result = cache.get_or_parse(file_path, parse_fn=parser)
    >>>
    >>> # Content-based caching (for analysis results)
    >>> code = "def foo(): return 1"
    >>> security_result = cache.get(code, "security")
    >>> if security_result is None:
    ...     security_result = perform_security_scan(code)
    ...     cache.set(code, "security", security_result)
"""

from __future__ import annotations

import hashlib
import json
import logging
import mmap
import os
import pickle
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Generic, TypedDict, TypeVar


class CacheStatsDict(TypedDict):
    """Cache statistics dictionary for JSON serialization."""

    memory_hits: int
    disk_hits: int
    misses: int
    stores: int
    invalidations: int
    evictions: int
    total_entries: int
    size_bytes: int
    total_requests: int
    hit_rate: float
    memory_hit_rate: float
    disk_hit_rate: float


# Import tool version for cache invalidation
try:
    from code_scalpel import __version__ as TOOL_VERSION
except ImportError:
    TOOL_VERSION = "unknown"

logger = logging.getLogger(__name__)

T = TypeVar("T")

# [20251214_PERF] Threshold for memory-mapped file reading (1MB default)
MMAP_THRESHOLD_BYTES = 1 * 1024 * 1024


# ============================================================================
# Configuration and Data Classes
# ============================================================================


@dataclass
class CacheConfig:
    """Configuration for the analysis cache.

    [20251223_CONSOLIDATION] Merged from utilities/cache.py CacheConfig
    """

    # Cache location
    cache_dir: Path | None = None  # None = auto-detect
    use_global_cache: bool = True  # Use ~/.cache/code-scalpel/
    use_local_cache: bool = True  # Use .scalpel_cache/

    # Cache behavior
    max_entries: int = 10000  # Maximum cache entries
    max_size_mb: int = 500  # Maximum cache size in MB
    ttl_seconds: int = 86400 * 7  # Time-to-live: 7 days

    # Serialization
    use_pickle: bool = True  # True = pickle (fast), False = JSON (portable)

    # Performance
    enabled: bool = True  # Master switch to disable caching


@dataclass
class CacheEntry:
    """A single cache entry with metadata.

    [20251223_CONSOLIDATION] Merged from utilities/cache.py CacheEntry
    """

    result: Any
    timestamp: float
    code_hash: str
    result_type: str
    config_hash: str = ""
    hits: int = 0


@dataclass
class CacheStats:
    """Statistics about cache performance.

    [20251223_CONSOLIDATION] Merged stats from both implementations
    """

    # From analysis_cache.py
    memory_hits: int = 0
    disk_hits: int = 0
    misses: int = 0
    stores: int = 0
    invalidations: int = 0

    # From utilities/cache.py
    evictions: int = 0
    total_entries: int = 0
    size_bytes: int = 0

    def __init__(self, **kwargs):
        """Initialize with backward compatibility for 'hits' parameter."""
        # Handle legacy 'hits' parameter
        if "hits" in kwargs:
            # Split hits evenly between memory and disk for backward compat
            total_hits = kwargs.pop("hits")
            kwargs.setdefault("memory_hits", total_hits)
            kwargs.setdefault("disk_hits", 0)

        # Set all fields
        for field in [
            "memory_hits",
            "disk_hits",
            "misses",
            "stores",
            "invalidations",
            "evictions",
            "total_entries",
            "size_bytes",
        ]:
            setattr(self, field, kwargs.get(field, 0))

    @property
    def total_requests(self) -> int:
        """Total requests to the cache."""
        return self.memory_hits + self.disk_hits + self.misses

    @property
    def hits(self) -> int:
        """Total cache hits (backward compatibility property)."""
        return self.memory_hits + self.disk_hits

    @property
    def hit_rate(self) -> float:
        """Overall cache hit rate (0.0-1.0)."""
        total = self.total_requests
        return (self.memory_hits + self.disk_hits) / total if total > 0 else 0.0

    @property
    def memory_hit_rate(self) -> float:
        """Memory cache hit rate (0.0-1.0)."""
        total = self.total_requests
        return self.memory_hits / total if total > 0 else 0.0

    @property
    def disk_hit_rate(self) -> float:
        """Disk cache hit rate (0.0-1.0)."""
        total = self.total_requests
        return self.disk_hits / total if total > 0 else 0.0

    def to_dict(self) -> CacheStatsDict:
        """Convert statistics to dictionary."""
        return {
            "memory_hits": self.memory_hits,
            "disk_hits": self.disk_hits,
            "misses": self.misses,
            "stores": self.stores,
            "invalidations": self.invalidations,
            "evictions": self.evictions,
            "total_entries": self.total_entries,
            "size_bytes": self.size_bytes,
            "total_requests": self.total_requests,
            "hit_rate": round(self.hit_rate, 4),
            "memory_hit_rate": round(self.memory_hit_rate, 4),
            "disk_hit_rate": round(self.disk_hit_rate, 4),
        }

    def reset(self) -> None:
        """Reset all statistics."""
        self.memory_hits = 0
        self.disk_hits = 0
        self.misses = 0
        self.stores = 0
        self.invalidations = 0
        self.evictions = 0
        self.total_entries = 0
        self.size_bytes = 0


# ============================================================================
# Unified AnalysisCache - Dual-Mode (Path-Based + Content-Based)
# ============================================================================


class AnalysisCache(Generic[T]):
    """Unified memory+disk cache for code analysis artifacts and results.

    [20251223_CONSOLIDATION] Merged cache/analysis_cache.py + utilities/cache.py

    Supports two complementary caching modes:

    1. Path-Based Mode (for parsed artifacts):
       - Cache by file path + content hash
       - Good for: Parsed AST, PDG, import resolved artifacts
       - Memory + disk with mmap support for large files
       - Use: cache.get_or_parse(file_path, parse_fn)

    2. Content-Based Mode (for analysis results):
       - Cache by SHA-256 of source code
       - Good for: Analysis results, security scans, symbolic execution
       - Multiple result types per code hash
       - TTL support for stale result invalidation
       - Use: cache.get(code, result_type) / cache.set(code, result_type, result)

    """

    VERSION = "1.1"  # [20251223_CONSOLIDATION] Bumped from 1.0 due to consolidation

    def __init__(self, cache_dir: Path | str | None = None, config: CacheConfig | None = None) -> None:
        """Initialize the unified cache.

        Args:
            cache_dir: Override cache directory (legacy parameter, use config instead)
            config: Cache configuration object
        """
        # Support both old (cache_dir) and new (config) initialization patterns
        # Handle case where config is passed as first positional argument
        if isinstance(cache_dir, CacheConfig):
            config = cache_dir
            cache_dir = None

        if config is None:
            config = CacheConfig()
            if cache_dir:
                config.cache_dir = Path(cache_dir)

        self.config = config
        self.stats = CacheStats()

        # Path-based mode: file path → parsed artifact
        self._memory_cache: dict[str, T] = {}
        self._hash_cache: dict[str, str] = {}

        # Content-based mode: code hash → result entries
        self._content_cache: dict[str, CacheEntry] = {}

        # Resolve cache directory
        self._cache_dir: Path | None = None
        if self.config.enabled:
            self._cache_dir = self._resolve_cache_dir()
            if self._cache_dir:
                self._cache_dir.mkdir(parents=True, exist_ok=True)
                logger.debug(f"Cache initialized at {self._cache_dir}")

    def _resolve_cache_dir(self) -> Path | None:
        """Resolve the cache directory location."""
        if self.config.cache_dir:
            return self.config.cache_dir

        # Try local cache first (project-specific)
        if self.config.use_local_cache:
            local_cache = Path.cwd() / ".scalpel_cache"
            if local_cache.exists() or self._can_create_dir(local_cache):
                return local_cache

        # Fall back to global cache
        if self.config.use_global_cache:
            if os.name == "nt":  # Windows
                base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
            else:  # Unix
                base = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
            return base / "code-scalpel"

        return None

    def _can_create_dir(self, path: Path) -> bool:
        """Check if we can create a directory at the given path."""
        try:
            path.mkdir(parents=True, exist_ok=True)
            return True
        except (PermissionError, OSError):
            return False

    # ========================================================================
    # Path-Based Caching (from analysis_cache.py)
    # ========================================================================

    def get_or_parse(self, file_path: Path | str, parse_fn: Callable[[Path], T]) -> T:
        """Get cached parse result or compute it fresh.

        Args:
            file_path: Path to file to parse
            parse_fn: Function to parse the file

        Returns:
            Parsed artifact (from cache or freshly computed)
        """
        path = Path(file_path).resolve()
        key = str(path)
        file_hash = self._hash_file(path)

        # Memory cache check
        cached_hash = self._hash_cache.get(key)
        if cached_hash == file_hash and key in self._memory_cache:
            self.stats.memory_hits += 1
            return self._memory_cache[key]

        # Disk cache check
        cache_path = self._cache_path_for_file(path)
        if cache_path and cache_path.exists():
            try:
                with cache_path.open("rb") as f:
                    # [20251218_SECURITY] pickle.load safe here: internal cache with hash validation (B301)
                    payload = pickle.load(f)  # nosec B301
                if payload.get("hash") == file_hash:
                    value: T = payload["value"]
                    self._memory_cache[key] = value
                    self._hash_cache[key] = file_hash
                    self.stats.disk_hits += 1
                    return value
            except Exception as exc:  # pragma: no cover
                logger.warning("Cache read failed for %s: %s", cache_path, exc)

        # Parse fresh
        self.stats.misses += 1
        value = parse_fn(path)
        self._memory_cache[key] = value
        self._hash_cache[key] = file_hash
        payload = {"hash": file_hash, "value": value}
        try:
            if cache_path:
                cache_path.parent.mkdir(parents=True, exist_ok=True)
                with cache_path.open("wb") as f:
                    pickle.dump(payload, f)
        except Exception as exc:  # pragma: no cover
            logger.warning("Cache write failed for %s: %s", cache_path, exc)
        return value

    def get_cached(self, file_path: Path | str) -> T | None:
        """Peek at cached result without parsing.

        Args:
            file_path: Path to file

        Returns:
            Cached artifact or None if not found / invalid
        """
        path = Path(file_path).resolve()
        key = str(path)
        file_hash = self._hash_file(path)

        cached_hash = self._hash_cache.get(key)
        if cached_hash == file_hash and key in self._memory_cache:
            self.stats.memory_hits += 1
            return self._memory_cache[key]

        cache_path = self._cache_path_for_file(path)
        if cache_path and cache_path.exists():
            try:
                with cache_path.open("rb") as f:
                    # [20251218_SECURITY] pickle.load safe here: internal cache with hash validation (B301)
                    payload = pickle.load(f)  # nosec B301
                if payload.get("hash") == file_hash:
                    value: T = payload["value"]
                    self._memory_cache[key] = value
                    self._hash_cache[key] = file_hash
                    self.stats.disk_hits += 1
                    return value
            except Exception as exc:  # pragma: no cover
                logger.warning("Cache read failed for %s: %s", cache_path, exc)
        self.stats.misses += 1
        return None

    def store(self, file_path: Path | str, value: T) -> None:
        """Store a parsed artifact.

        Args:
            file_path: Path to file
            value: Parsed artifact to store
        """
        path = Path(file_path).resolve()
        key = str(path)
        file_hash = self._hash_file(path)
        self._memory_cache[key] = value
        self._hash_cache[key] = file_hash
        self.stats.stores += 1
        payload = {"hash": file_hash, "value": value}
        cache_path = self._cache_path_for_file(path)
        try:
            if cache_path:
                cache_path.parent.mkdir(parents=True, exist_ok=True)
                with cache_path.open("wb") as f:
                    pickle.dump(payload, f)
        except Exception as exc:  # pragma: no cover
            logger.warning("Cache write failed for %s: %s", cache_path, exc)

    def invalidate_file(self, file_path: Path | str) -> None:
        """Invalidate cache entry for a file.

        Args:
            file_path: Path to file
        """
        path = Path(file_path).resolve()
        key = str(path)
        self._memory_cache.pop(key, None)
        self._hash_cache.pop(key, None)
        self.stats.invalidations += 1
        cache_path = self._cache_path_for_file(path)
        if cache_path:
            cache_path.unlink(missing_ok=True)

    def _hash_file(self, path: Path) -> str:
        """Hash file contents, using memory-mapped I/O for large files."""
        try:
            file_size = path.stat().st_size
            if file_size > MMAP_THRESHOLD_BYTES:
                return self._hash_file_mmap(path)
            data = path.read_bytes()
            return hashlib.sha256(data).hexdigest()
        except Exception:
            # [20251223_BUGFIX] Return consistent hash on read error
            return hashlib.sha256(str(path).encode()).hexdigest()

    def _hash_file_mmap(self, path: Path) -> str:
        """Hash large file using memory-mapped I/O."""
        hasher = hashlib.sha256()
        with path.open("rb") as f:
            with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
                # Read in chunks to avoid memory pressure on very large files
                chunk_size = 64 * 1024  # 64KB chunks
                for i in range(0, len(mm), chunk_size):
                    hasher.update(mm[i : i + chunk_size])
        return hasher.hexdigest()

    def _cache_path_for_file(self, path: Path) -> Path | None:
        """Get cache path for a file artifact."""
        if self._cache_dir is None:
            return None
        # Combine path + content hash seed to avoid collisions by filename alone
        seed = hashlib.sha256(str(path).encode("utf-8")).hexdigest()
        return self._cache_dir / f"v{self.VERSION}" / f"file_{seed}.pkl"

    # Backward compatibility alias
    _cache_path_for = _cache_path_for_file

    # ========================================================================
    # Content-Based Caching (from utilities/cache.py)
    # ========================================================================

    def get(
        self,
        code: str,
        result_type: str,
        config: dict[str, Any] | None = None,
    ) -> Any | None:
        """Retrieve a cached analysis result.

        Args:
            code: Source code that was analyzed
            result_type: Type of result ("analysis", "security", "symbolic", "tests")
            config: Configuration used for analysis (affects cache key)

        Returns:
            Cached result if found and valid, None otherwise
        """
        if not self.config.enabled:
            return None

        code_hash = self._hash_code(code)
        config_hash = self._hash_config(config)
        cache_key = self._cache_key(code_hash, result_type, config_hash)

        # Check in-memory cache first
        if cache_key in self._content_cache:
            entry = self._content_cache[cache_key]
            if self._is_valid(entry):
                entry.hits += 1
                self.stats.memory_hits += 1
                logger.debug(f"Cache hit (memory): {result_type} for {code_hash[:8]}...")
                return entry.result

        # Check disk cache
        cache_path = self._cache_path_for_content(cache_key)
        if cache_path and cache_path.exists():
            try:
                entry = self._load_entry(cache_path)
                if entry and self._is_valid(entry):
                    # Promote to memory cache
                    self._content_cache[cache_key] = entry
                    entry.hits += 1
                    self.stats.disk_hits += 1
                    logger.debug(f"Cache hit (disk): {result_type} for {code_hash[:8]}...")
                    return entry.result
            except Exception as e:
                logger.warning(f"Failed to load cache entry: {e}")

        self.stats.misses += 1
        logger.debug(f"Cache miss: {result_type} for {code_hash[:8]}...")
        return None

    def set(
        self,
        code: str,
        result_type: str,
        result: Any,
        config: dict[str, Any] | None = None,
    ) -> bool:
        """Store an analysis result in the cache.

        Args:
            code: Source code that was analyzed
            result_type: Type of result
            result: The analysis result to cache
            config: Configuration used for analysis

        Returns:
            True if successfully cached, False otherwise
        """
        if not self.config.enabled:
            return False

        code_hash = self._hash_code(code)
        config_hash = self._hash_config(config)
        cache_key = self._cache_key(code_hash, result_type, config_hash)

        entry = CacheEntry(
            result=result,
            timestamp=time.time(),
            code_hash=code_hash,
            result_type=result_type,
            config_hash=config_hash,
        )

        # Store in memory
        self._content_cache[cache_key] = entry

        # Store on disk
        cache_path = self._cache_path_for_content(cache_key)
        if cache_path:
            try:
                cache_path.parent.mkdir(parents=True, exist_ok=True)
                self._save_entry(cache_path, entry)
                self.stats.stores += 1
                logger.debug(f"Cached: {result_type} for {code_hash[:8]}...")
                return True
            except Exception as e:
                logger.warning(f"Failed to save cache entry: {e}")

        return False

    def _hash_code(self, code: str) -> str:
        """Generate SHA-256 hash of code content."""
        return hashlib.sha256(code.encode("utf-8")).hexdigest()

    def _hash_config(self, config: dict[str, Any] | None = None) -> str:
        """Generate hash of configuration that affects analysis.

        The hash includes the tool version to automatically invalidate
        cache entries when code-scalpel is upgraded.
        """
        effective_config = {"_tool_version": TOOL_VERSION}
        if config:
            effective_config.update(config)

        config_str = json.dumps(effective_config, sort_keys=True)
        return hashlib.sha256(config_str.encode("utf-8")).hexdigest()[:16]

    def _cache_key(self, code_hash: str, result_type: str, config_hash: str) -> str:
        """Generate cache key from components."""
        return f"{code_hash}_{result_type}_{config_hash}"

    def _cache_path_for_content(self, cache_key: str) -> Path | None:
        """Get the file path for a content cache entry."""
        if self._cache_dir is None:
            return None
        ext = ".pkl" if self.config.use_pickle else ".json"
        return self._cache_dir / f"v{self.VERSION}" / f"content_{cache_key}{ext}"

    def _is_valid(self, entry: CacheEntry) -> bool:
        """Check if a cache entry is still valid."""
        if self.config.ttl_seconds <= 0:
            return True
        age = time.time() - entry.timestamp
        return age < self.config.ttl_seconds

    def _load_entry(self, path: Path) -> CacheEntry | None:
        """Load a cache entry from disk."""
        try:
            if self.config.use_pickle:
                with open(path, "rb") as f:
                    # [20251218_SECURITY] pickle.load safe here: internal cache with CacheEntry validation (B301)
                    return pickle.load(f)  # nosec B301
            else:
                with open(path) as f:
                    data = json.load(f)
                    return CacheEntry(**data)
        except Exception:
            return None

    def _save_entry(self, path: Path, entry: CacheEntry) -> None:
        """Save a cache entry to disk."""
        if self.config.use_pickle:
            with open(path, "wb") as f:
                pickle.dump(entry, f, protocol=pickle.HIGHEST_PROTOCOL)
        else:
            with open(path, "w") as f:
                data = {
                    "result": self._to_json_serializable(entry.result),
                    "timestamp": entry.timestamp,
                    "code_hash": entry.code_hash,
                    "result_type": entry.result_type,
                    "config_hash": entry.config_hash,
                    "hits": entry.hits,
                }
                json.dump(data, f)

    def _to_json_serializable(self, obj: Any) -> Any:
        """Convert object to JSON-serializable form."""
        if hasattr(obj, "model_dump"):
            return obj.model_dump()
        if hasattr(obj, "__dict__"):
            return obj.__dict__
        return obj

    def invalidate(self, code: str | Path, result_type: str | None = None) -> int:
        """Invalidate cache entries for specific code or file.

        Args:
            code: Source code string or file path to invalidate
            result_type: Specific result type, or None for all types

        Returns:
            Number of entries invalidated
        """
        # Handle file path input (from old analysis_cache API)
        if isinstance(code, Path):
            file_path = str(code.resolve())
            # Invalidate file-based cache
            if file_path in self._memory_cache:
                del self._memory_cache[file_path]
                self.stats.invalidations += 1
                count = 1
            else:
                count = 0

            # Also invalidate hash cache
            if file_path in self._hash_cache:
                del self._hash_cache[file_path]

            return count

        # Original content-based invalidation
        code_hash = self._hash_code(code)
        count = 0

        # Invalidate memory cache
        keys_to_remove = [
            k for k in self._content_cache if k.startswith(code_hash) and (result_type is None or result_type in k)
        ]
        for key in keys_to_remove:
            del self._content_cache[key]
            count += 1

        # Invalidate disk cache
        if self._cache_dir:
            version_dir = self._cache_dir / f"v{self.VERSION}"
            if version_dir.exists():
                pattern = f"content_{code_hash}_{result_type or '*'}_*"
                for path in version_dir.glob(pattern + ".*"):
                    path.unlink()
                    count += 1

        self.stats.invalidations += count
        return count

    def clear(self) -> int:
        """Clear all cache entries.

        Returns:
            Number of entries cleared
        """
        count = len(self._memory_cache) + len(self._content_cache)
        self._memory_cache.clear()
        self._content_cache.clear()

        if self._cache_dir and self._cache_dir.exists():
            import shutil

            for item in self._cache_dir.iterdir():
                if item.is_dir():
                    shutil.rmtree(item)
                elif item.is_file():
                    item.unlink()

        self.stats = CacheStats()
        logger.info(f"Cache cleared: {count} entries removed")
        return count

    def get_stats(self) -> CacheStats:
        """Get cache statistics."""
        self.stats.total_entries = len(self._memory_cache) + len(self._content_cache)

        # Calculate disk size
        if self._cache_dir and self._cache_dir.exists():
            total_size = sum(f.stat().st_size for f in self._cache_dir.rglob("*") if f.is_file())
            self.stats.size_bytes = total_size

        return self.stats


# ============================================================================
# Global Cache Instance and Helpers
# ============================================================================

# Global cache instance (singleton pattern)
_global_cache: AnalysisCache | None = None


def get_cache(config: CacheConfig | None = None) -> AnalysisCache:
    """Get the global cache instance.

    Args:
        config: Cache configuration (only used on first call)

    Returns:
        The global AnalysisCache instance
    """
    global _global_cache
    if _global_cache is None:
        _global_cache = AnalysisCache(config=config)
    return _global_cache


def reset_cache() -> None:
    """Reset the global cache instance."""
    global _global_cache
    if _global_cache:
        _global_cache.clear()
    _global_cache = None
