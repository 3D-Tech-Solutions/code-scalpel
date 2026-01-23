"""Cache utilities for Code Scalpel.

[20251223_CONSOLIDATION] v3.0.5 - Unified cache merges analysis_cache.py + utilities/cache.py
"""

from .incremental_analyzer import IncrementalAnalyzer
from .parallel_parser import ParallelParser

# [20251223_CONSOLIDATION] Export from unified cache implementation
from .unified_cache import (
    AnalysisCache,
    CacheConfig,
    CacheEntry,
    CacheStats,
    get_cache,
    reset_cache,
)

__all__ = [
    "AnalysisCache",
    "CacheConfig",
    "CacheEntry",
    "CacheStats",
    "ParallelParser",
    "IncrementalAnalyzer",
    "get_cache",
    "reset_cache",
]
