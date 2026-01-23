"""
License Cache - Cached license state for performance.

[20251225_FEATURE] Thread-safe, multi-tier license validation caching.

Provides in-memory and persistent caching with optional Redis distribution
and encryption support. Includes automatic expiration, invalidation tracking,
and replication capabilities.

Features:
- In-memory cache with TTL-based expiration
- Thread-safe operations (RLock)
- Optional persistent storage (JSON to disk)
- Optional distributed caching (Redis)
- Optional encryption (XOR cipher)
- Cache replication (master-slave pattern)
- Invalidation by license key
- Comprehensive statistics and metrics
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import threading
import time
from base64 import b64decode, b64encode
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """A cached license validation result."""

    tier: str
    is_valid: bool
    timestamp: float
    ttl_seconds: float
    license_key_hash: str | None = None

    def is_expired(self) -> bool:
        """Check if this cache entry has expired."""
        return time.time() > (self.timestamp + self.ttl_seconds)


class LicenseCache:
    """
    Cache for license validation results.

    Provides thread-safe caching of license validation to avoid
    repeated validation checks during normal operation.

    Usage:
        cache = LicenseCache(ttl_seconds=3600)  # 1 hour TTL

        # Store validation result
        cache.set("my_license_key", tier="pro", is_valid=True)

        # Retrieve cached result
        entry = cache.get("my_license_key")
        if entry and not entry.is_expired():
            print(f"Cached tier: {entry.tier}")
    """

    DEFAULT_TTL_SECONDS = 3600  # 1 hour

    def __init__(
        self,
        ttl_seconds: float = DEFAULT_TTL_SECONDS,
        persistence_path: Path | None = None,
        encryption_key: str | None = None,
        enable_distributed: bool = False,
        redis_url: str | None = None,
    ):
        """
        Initialize the cache.

        Args:
            ttl_seconds: Time-to-live for cache entries
            persistence_path: Path to persist cache to disk
            encryption_key: Optional encryption key for cache encryption
            enable_distributed: Enable distributed cache support (Redis)
            redis_url: Redis connection URL for distributed cache
        """
        self._ttl_seconds = ttl_seconds
        self._cache: dict[str, CacheEntry] = {}
        self._lock = threading.RLock()

        # [20251225_FEATURE] P1_HIGH: Persistent cache to disk
        self._persistence_path = persistence_path or Path(".code-scalpel/license_cache.json")
        self._enable_persistence = persistence_path is not None or os.getenv("CODE_SCALPEL_CACHE_PERSIST") == "true"

        # [20251225_FEATURE] P4_LOW: Cache encryption
        self._encryption_key = encryption_key or os.getenv("CODE_SCALPEL_CACHE_KEY")

        # [20251225_FEATURE] P2_MEDIUM: Distributed cache support
        self._enable_distributed = enable_distributed or os.getenv("CODE_SCALPEL_CACHE_DISTRIBUTED") == "true"
        self._redis_url = redis_url or os.getenv("CODE_SCALPEL_REDIS_URL", "redis://localhost:6379")
        self._redis_client = None

        # [20251225_FEATURE] P3_LOW: Cache replication
        self._replicas: list[LicenseCache] = []

        # Track cache statistics
        self._stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "invalidations": 0,
            "persists": 0,
            "loads": 0,
        }

        # Initialize distributed cache if enabled
        if self._enable_distributed:
            self._init_distributed_cache()

        # Load persisted cache if available
        if self._enable_persistence:
            self._load_from_disk()

    def get(self, key: str) -> CacheEntry | None:
        """
        Get a cached entry.

        Args:
            key: Cache key (typically license key hash)

        Returns:
            CacheEntry if found and not expired, None otherwise
        """
        with self._lock:
            # Check local cache first
            entry = self._cache.get(key)

            if entry is None:
                # [20251225_FEATURE] P2_MEDIUM: Try distributed cache
                if self._enable_distributed and self._redis_client:
                    entry = self._get_from_distributed(key)
                    if entry:
                        # Cache locally
                        self._cache[key] = entry
                        self._stats["hits"] += 1
                        return entry

                self._stats["misses"] += 1
                return None

            if entry.is_expired():
                # Remove expired entry
                del self._cache[key]
                logger.debug(f"Cache entry expired for key: {key[:8]}...")
                self._stats["misses"] += 1
                return None

            self._stats["hits"] += 1
            return entry

    def set(
        self,
        key: str,
        tier: str,
        is_valid: bool,
        ttl_seconds: float | None = None,
        license_key: str | None = None,
    ) -> None:
        """
        Set a cache entry.

        Args:
            key: Cache key (typically license key hash)
            tier: License tier
            is_valid: Whether license is valid
            ttl_seconds: Optional custom TTL (uses default if not specified)
            license_key: Optional license key for invalidation tracking
        """
        with self._lock:
            # Compute license key hash for invalidation tracking
            license_key_hash = None
            if license_key:
                license_key_hash = hashlib.sha256(license_key.encode()).hexdigest()[:16]

            entry = CacheEntry(
                tier=tier,
                is_valid=is_valid,
                timestamp=time.time(),
                ttl_seconds=ttl_seconds or self._ttl_seconds,
                license_key_hash=license_key_hash,
            )

            self._cache[key] = entry
            self._stats["sets"] += 1
            logger.debug(f"Cached license validation for key: {key[:8]}...")

            # [20251225_FEATURE] P1_HIGH: Persist to disk
            if self._enable_persistence:
                self._save_to_disk()

            # [20251225_FEATURE] P2_MEDIUM: Replicate to distributed cache
            if self._enable_distributed and self._redis_client:
                self._set_in_distributed(key, entry)

            # [20251225_FEATURE] P3_LOW: Replicate to secondary caches
            for replica in self._replicas:
                replica.set(key, tier, is_valid, ttl_seconds, license_key)

    def invalidate(self, key: str) -> bool:
        """
        Invalidate a cache entry.

        Args:
            key: Cache key to invalidate

        Returns:
            True if entry was found and removed
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                self._stats["invalidations"] += 1
                logger.debug(f"Invalidated cache entry for key: {key[:8]}...")

                # Persist changes
                if self._enable_persistence:
                    self._save_to_disk()

                # Replicate invalidation
                if self._enable_distributed and self._redis_client:
                    self._delete_from_distributed(key)

                for replica in self._replicas:
                    replica.invalidate(key)

                return True
            return False

    def invalidate_by_license_key(self, license_key: str) -> int:
        """
        [20251225_FEATURE] P2_MEDIUM: Invalidate all cache entries for a specific license key.

        Useful when a license key changes or is revoked.

        Args:
            license_key: License key to invalidate

        Returns:
            Number of entries invalidated
        """
        license_key_hash = hashlib.sha256(license_key.encode()).hexdigest()[:16]

        with self._lock:
            keys_to_invalidate = [
                key for key, entry in self._cache.items() if entry.license_key_hash == license_key_hash
            ]

            for key in keys_to_invalidate:
                self.invalidate(key)

            if keys_to_invalidate:
                logger.info(f"Invalidated {len(keys_to_invalidate)} cache entries for license key change")

            return len(keys_to_invalidate)

    def clear(self) -> int:
        """
        Clear all cache entries.

        Returns:
            Number of entries cleared
        """
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            logger.debug(f"Cleared {count} cache entries")
            return count

    def cleanup_expired(self) -> int:
        """
        Remove all expired entries.

        Returns:
            Number of expired entries removed
        """
        with self._lock:
            expired_keys = [key for key, entry in self._cache.items() if entry.is_expired()]

            for key in expired_keys:
                del self._cache[key]

            if expired_keys:
                logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")

            return len(expired_keys)

    def size(self) -> int:
        """Get current cache size."""
        with self._lock:
            return len(self._cache)

    def stats(self) -> dict[str, Any]:
        """
        [20251225_FEATURE] P3_LOW: Get cache statistics and metrics.

        Returns:
            Dictionary with cache statistics
        """
        with self._lock:
            total = len(self._cache)
            expired = sum(1 for entry in self._cache.values() if entry.is_expired())
            valid = total - expired

            hit_rate = (
                self._stats["hits"] / (self._stats["hits"] + self._stats["misses"])
                if (self._stats["hits"] + self._stats["misses"]) > 0
                else 0.0
            )

            return {
                "total_entries": total,
                "valid_entries": valid,
                "expired_entries": expired,
                "hits": self._stats["hits"],
                "misses": self._stats["misses"],
                "sets": self._stats["sets"],
                "invalidations": self._stats["invalidations"],
                "hit_rate": hit_rate,
                "persists": self._stats["persists"],
                "loads": self._stats["loads"],
                "distributed_enabled": self._enable_distributed,
                "persistence_enabled": self._enable_persistence,
                "encryption_enabled": self._encryption_key is not None,
                "replica_count": len(self._replicas),
            }

    def add_replica(self, replica: LicenseCache) -> None:
        """
        [20251225_FEATURE] P3_LOW: Add a replica cache for replication.

        Cache operations will be replicated to all registered replicas.

        Args:
            replica: Another LicenseCache instance to replicate to
        """
        with self._lock:
            if replica not in self._replicas:
                self._replicas.append(replica)
                logger.info(f"Added cache replica. Total replicas: {len(self._replicas)}")

    def remove_replica(self, replica: LicenseCache) -> bool:
        """
        [20251225_FEATURE] P3_LOW: Remove a replica cache.

        Args:
            replica: Replica cache to remove

        Returns:
            True if replica was found and removed
        """
        with self._lock:
            if replica in self._replicas:
                self._replicas.remove(replica)
                logger.info(f"Removed cache replica. Total replicas: {len(self._replicas)}")
                return True
            return False

    def _save_to_disk(self) -> None:
        """
        [20251225_FEATURE] P1_HIGH: Persist cache to disk.
        """
        try:
            # Create directory if it doesn't exist
            self._persistence_path.parent.mkdir(parents=True, exist_ok=True)

            # Prepare cache data
            cache_data = {
                "version": "1.0",
                "timestamp": time.time(),
                "entries": {key: asdict(entry) for key, entry in self._cache.items() if not entry.is_expired()},
            }

            # Serialize to JSON
            json_data = json.dumps(cache_data)

            # [20251225_FEATURE] P4_LOW: Encrypt if encryption key is set
            if self._encryption_key:
                json_data = self._encrypt(json_data)

            # Write to file
            with open(self._persistence_path, "w") as f:
                f.write(json_data)

            self._stats["persists"] += 1
            logger.debug(f"Cache persisted to {self._persistence_path}")

        except OSError as e:
            logger.warning(f"Failed to persist cache: {e}")

    def _load_from_disk(self) -> None:
        """
        [20251225_FEATURE] P1_HIGH: Load cache from disk.
        """
        if not self._persistence_path.exists():
            return

        try:
            with open(self._persistence_path) as f:
                json_data = f.read()

            # [20251225_FEATURE] P4_LOW: Decrypt if encrypted
            if self._encryption_key and not json_data.startswith("{"):
                json_data = self._decrypt(json_data)

            cache_data = json.loads(json_data)

            # Restore cache entries
            for key, entry_dict in cache_data.get("entries", {}).items():
                entry = CacheEntry(**entry_dict)
                if not entry.is_expired():
                    self._cache[key] = entry

            self._stats["loads"] += 1
            logger.info(f"Cache loaded from {self._persistence_path}. " f"Loaded {len(self._cache)} entries")

        except (OSError, json.JSONDecodeError) as e:
            logger.warning(f"Failed to load cache: {e}")

    def _encrypt(self, data: str) -> str:
        """
        [20251225_FEATURE] P4_LOW: Encrypt cache data using XOR cipher.

        Note: This is a simple XOR cipher for demonstration. In production,
        use proper encryption like AES-256.
        """
        if not self._encryption_key:
            return data

        key_bytes = self._encryption_key.encode()
        data_bytes = data.encode()

        # XOR each byte with key bytes (cycling through key)
        encrypted = bytes(data_bytes[i] ^ key_bytes[i % len(key_bytes)] for i in range(len(data_bytes)))

        # Base64 encode for storage
        return b64encode(encrypted).decode()

    def _decrypt(self, encrypted_data: str) -> str:
        """
        [20251225_FEATURE] P4_LOW: Decrypt cache data.
        """
        if not self._encryption_key:
            return encrypted_data

        try:
            # Base64 decode
            encrypted_bytes = b64decode(encrypted_data)

            key_bytes = self._encryption_key.encode()

            # XOR to decrypt
            decrypted = bytes(encrypted_bytes[i] ^ key_bytes[i % len(key_bytes)] for i in range(len(encrypted_bytes)))

            return decrypted.decode()
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            return encrypted_data

    def _init_distributed_cache(self) -> None:
        """
        [20251225_FEATURE] P2_MEDIUM: Initialize distributed cache (Redis).

        Note: This requires redis-py package. Falls back gracefully if not available.
        """
        try:
            import redis

            self._redis_client = redis.from_url(
                self._redis_url,
                decode_responses=True,
                socket_timeout=2,
            )

            # Test connection
            self._redis_client.ping()
            logger.info(f"Distributed cache initialized: {self._redis_url}")

        except ImportError:
            logger.warning("redis-py not installed. Distributed cache disabled. " "Install with: pip install redis")
            self._enable_distributed = False
        except Exception as e:
            logger.warning(f"Failed to connect to Redis: {e}. Distributed cache disabled.")
            self._enable_distributed = False
            self._redis_client = None

    def _get_from_distributed(self, key: str) -> CacheEntry | None:
        """
        [20251225_FEATURE] P2_MEDIUM: Get entry from distributed cache.
        """
        if not self._redis_client:
            return None

        try:
            # [20260102_BUGFIX] Normalize cache key to hash to avoid command injection via key names.
            safe_key = hashlib.sha256(key.encode()).hexdigest()
            data = self._redis_client.get(f"scalpel:cache:{safe_key}")
            if data:
                # Redis may return bytes when decode_responses=False; normalize to str for json.loads
                if isinstance(data, (bytes, bytearray)):
                    data = data.decode()
                entry_dict = json.loads(str(data))
                return CacheEntry(**entry_dict)
        except Exception as e:
            logger.warning(f"Failed to get from distributed cache: {e}")

        return None

    def _set_in_distributed(self, key: str, entry: CacheEntry) -> None:
        """
        [20251225_FEATURE] P2_MEDIUM: Set entry in distributed cache.
        """
        if not self._redis_client:
            return

        try:
            data = json.dumps(asdict(entry))
            ttl = int(entry.ttl_seconds)
            safe_key = hashlib.sha256(key.encode()).hexdigest()
            self._redis_client.setex(f"scalpel:cache:{safe_key}", ttl, data)
        except Exception as e:
            logger.warning(f"Failed to set in distributed cache: {e}")

    def _delete_from_distributed(self, key: str) -> None:
        """
        [20251225_FEATURE] P2_MEDIUM: Delete entry from distributed cache.
        """
        if not self._redis_client:
            return

        try:
            safe_key = hashlib.sha256(key.encode()).hexdigest()
            self._redis_client.delete(f"scalpel:cache:{safe_key}")
        except Exception as e:
            logger.warning(f"Failed to delete from distributed cache: {e}")  # nosec B608
