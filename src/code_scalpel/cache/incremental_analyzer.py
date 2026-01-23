from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path
from typing import Generic, TypeVar

# [20251223_CONSOLIDATION] Import from unified_cache
from .unified_cache import AnalysisCache

logger = logging.getLogger(__name__)

T = TypeVar("T")


class IncrementalAnalyzer(Generic[T]):
    """[20251214_FEATURE] Dependency-aware incremental analysis."""

    def __init__(self, cache: AnalysisCache[T]) -> None:
        self.cache = cache
        self.dependency_graph: dict[str, set[str]] = {}
        # # TODO Phase 2: Add reverse graph for faster lookups

    def record_dependency(self, source: Path | str, depends_on: Path | str) -> None:
        source_key = str(Path(source).resolve())
        target_key = str(Path(depends_on).resolve())
        self.dependency_graph.setdefault(target_key, set()).add(source_key)

    def get_dependents(self, file_path: Path | str) -> set[str]:
        return set(self.dependency_graph.get(str(Path(file_path).resolve()), set()))

    def update_file(self, file_path: Path | str, recompute_fn: Callable[[Path], T]) -> set[str]:
        """Update a file and return affected dependents."""
        path = Path(file_path).resolve()
        key = str(path)

        # Invalidate the changed file and recompute
        # [20251222_BUGFIX] AnalysisCache stores file artifacts keyed by resolved path.
        # invalidate() targets analysis-result entries; invalidate_file() clears file entries.
        self.cache.invalidate_file(key)
        self.cache.get_or_parse(path, parse_fn=recompute_fn)

        affected = self.get_dependents(key)
        for dependent in affected:
            self.cache.invalidate_file(dependent)
        return affected
