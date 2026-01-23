from __future__ import annotations

import logging
import os
import threading
from collections.abc import Callable, Sequence
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Generic, TypeVar

# [20251223_CONSOLIDATION] Import from unified_cache
from .unified_cache import AnalysisCache

logger = logging.getLogger(__name__)

T = TypeVar("T")


# [20251214_PERF] Batch worker - parse multiple files per worker
def _batch_parse_worker(file_paths: list[str], parse_fn: Callable[[Path], T]) -> list[tuple[str, T | None, str | None]]:
    """Parse a batch of files, returning (path, result, error) tuples."""
    results = []
    for file_path in file_paths:
        try:
            path = Path(file_path)
            value = parse_fn(path)
            results.append((file_path, value, None))
        except Exception as exc:
            results.append((file_path, None, str(exc)))
    return results


class ParallelParser(Generic[T]):
    """[20251214_FEATURE] Parallel file parsing with cache reuse."""

    # [20251214_PERF] Default batch size to amortize pickle overhead
    DEFAULT_BATCH_SIZE = 100

    def __init__(
        self,
        cache: AnalysisCache[T],
        max_workers: int | None = None,
        batch_size: int | None = None,
    ) -> None:
        self.cache = cache
        self.max_workers = max_workers or os.cpu_count() or 1
        self.batch_size = batch_size or self.DEFAULT_BATCH_SIZE

    def parse_files(self, files: Sequence[Path | str], parse_fn: Callable[[Path], T]) -> tuple[dict[str, T], list[str]]:
        """Parse multiple files in parallel with caching."""
        results: dict[str, T] = {}
        errors: list[str] = []
        to_parse: list[str] = []

        for file_path in files:
            path = Path(file_path).resolve()
            cached = self.cache.get_cached(path)
            if cached is not None:
                results[str(path)] = cached
            else:
                to_parse.append(str(path))

        if to_parse:
            # [20251214_PERF] Batch files to reduce per-file pickle overhead
            batches = [to_parse[i : i + self.batch_size] for i in range(0, len(to_parse), self.batch_size)]

            # Spawning/forking processes from a non-main thread can hang on some
            # platforms/configs. Since this parser may be invoked from MCP tool
            # handlers running in worker threads (e.g., stdio/async transports),
            # fall back to threads when not on the main thread.
            executor_cls = (
                ProcessPoolExecutor if threading.current_thread() is threading.main_thread() else ThreadPoolExecutor
            )

            with executor_cls(max_workers=self.max_workers) as executor:
                futures = {executor.submit(_batch_parse_worker, batch, parse_fn): batch for batch in batches}
                for future in as_completed(futures):
                    batch = futures[future]
                    try:
                        batch_results = future.result()
                        for file_path, value, error in batch_results:
                            if error is None and value is not None:
                                results[file_path] = value
                                self.cache.store(file_path, value)
                            else:
                                logger.warning("Parse failed for %s: %s", file_path, error)
                                errors.append(file_path)
                    except Exception as exc:
                        logger.warning("Batch parse failed for %d files: %s", len(batch), exc)
                        errors.extend(batch)

        return results, errors
