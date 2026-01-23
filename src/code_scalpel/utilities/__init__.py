"""Code Scalpel Utilities.

[20251223_CONSOLIDATION] v3.0.5 - Cache consolidated into cache/unified_cache.py

Common utilities for caching, configuration, and helpers.
"""

# [20251223_CONSOLIDATION] Re-export from unified cache for backward compatibility
from code_scalpel.cache import AnalysisCache, CacheConfig

__all__ = [
    "AnalysisCache",
    "CacheConfig",
]
