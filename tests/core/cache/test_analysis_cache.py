from pathlib import Path

import pytest

# [20251221_BUGFIX] v3.1.0 - Use unified_cache after v3.0.5 consolidation
from code_scalpel.cache.unified_cache import AnalysisCache


class DummyParseError(Exception):
    """Custom error for testing."""


@pytest.fixture()
def sample_file(tmp_path: Path) -> Path:
    file_path = tmp_path / "example.py"
    file_path.write_text("print('hi')\n", encoding="utf-8")
    return file_path


def test_memory_cache_hits_without_reparsing(sample_file: Path, tmp_path: Path) -> None:
    calls: list[int] = []

    def parse_fn(path: Path) -> int:
        calls.append(1)
        return len(path.read_text(encoding="utf-8"))

    cache = AnalysisCache(cache_dir=tmp_path / "cache")

    first = cache.get_or_parse(sample_file, parse_fn=parse_fn)
    second = cache.get_or_parse(sample_file, parse_fn=parse_fn)

    assert first == second == len("print('hi')\n")
    assert len(calls) == 1  # parse_fn invoked once due to memory cache


def test_disk_cache_persists_across_instances(sample_file: Path, tmp_path: Path) -> None:
    cache_dir = tmp_path / "cache"

    def parse_fn(path: Path) -> str:
        return path.read_text(encoding="utf-8")

    cache = AnalysisCache(cache_dir=cache_dir)
    expected = cache.get_or_parse(sample_file, parse_fn=parse_fn)

    calls: list[int] = []

    def parse_fn_second(path: Path) -> str:
        calls.append(1)
        return path.read_text(encoding="utf-8")

    cache_reload = AnalysisCache(cache_dir=cache_dir)
    observed = cache_reload.get_or_parse(sample_file, parse_fn=parse_fn_second)

    assert observed == expected
    assert calls == []  # served from disk cache; no parse call


def test_invalidate_removes_cache(sample_file: Path, tmp_path: Path) -> None:
    cache_dir = tmp_path / "cache"
    cache = AnalysisCache(cache_dir=cache_dir)

    calls: list[int] = []

    def parse_fn(path: Path) -> int:
        calls.append(1)
        return len(path.read_text(encoding="utf-8"))

    first = cache.get_or_parse(sample_file, parse_fn=parse_fn)
    cache.invalidate(sample_file)

    # Modify file to ensure fresh hash
    sample_file.write_text("print('hello')\n", encoding="utf-8")

    second = cache.get_or_parse(sample_file, parse_fn=parse_fn)

    assert second != first
    assert len(calls) == 2  # re-parsed after invalidation


def test_corrupt_cache_file_triggers_reparse(sample_file: Path, tmp_path: Path) -> None:
    cache_dir = tmp_path / "cache"
    cache = AnalysisCache(cache_dir=cache_dir)

    def parse_fn(path: Path) -> dict:
        return {"len": len(path.read_text(encoding="utf-8"))}

    cache.get_or_parse(sample_file, parse_fn=parse_fn)

    cache_file = cache._cache_path_for(sample_file)  # type: ignore[attr-defined]
    cache_file.write_bytes(b"corrupt")

    calls: list[int] = []

    def parse_fn_second(path: Path) -> dict:
        calls.append(1)
        return {"len": len(path.read_text(encoding="utf-8"))}

    cache_reload = AnalysisCache(cache_dir=cache_dir)
    result = cache_reload.get_or_parse(sample_file, parse_fn=parse_fn_second)

    assert result == {"len": len("print('hi')\n")}
    assert len(calls) == 1  # re-parsed after corruption


# [20251214_TEST] CacheStats tracking tests
def test_cache_stats_tracks_memory_hits(sample_file: Path, tmp_path: Path) -> None:
    """Test that memory cache hits are tracked."""
    cache = AnalysisCache(cache_dir=tmp_path / "cache")

    def parse_fn(path: Path) -> str:
        return path.read_text(encoding="utf-8")

    # First call - miss
    cache.get_or_parse(sample_file, parse_fn=parse_fn)
    assert cache.stats.misses == 1
    assert cache.stats.memory_hits == 0

    # Second call - memory hit
    cache.get_or_parse(sample_file, parse_fn=parse_fn)
    assert cache.stats.memory_hits == 1
    assert cache.stats.misses == 1  # unchanged


def test_cache_stats_tracks_disk_hits(sample_file: Path, tmp_path: Path) -> None:
    """Test that disk cache hits are tracked across instances."""
    cache_dir = tmp_path / "cache"

    def parse_fn(path: Path) -> str:
        return path.read_text(encoding="utf-8")

    # First instance - miss
    cache1 = AnalysisCache(cache_dir=cache_dir)
    cache1.get_or_parse(sample_file, parse_fn=parse_fn)
    assert cache1.stats.misses == 1

    # New instance - disk hit
    cache2 = AnalysisCache(cache_dir=cache_dir)
    cache2.get_or_parse(sample_file, parse_fn=parse_fn)
    assert cache2.stats.disk_hits == 1
    assert cache2.stats.misses == 0


def test_cache_stats_to_dict(tmp_path: Path) -> None:
    """Test that stats.to_dict() returns correct structure."""
    cache = AnalysisCache(cache_dir=tmp_path / "cache")
    cache.stats.memory_hits = 10
    cache.stats.disk_hits = 5
    cache.stats.misses = 5

    result = cache.stats.to_dict()

    assert result["memory_hits"] == 10
    assert result["disk_hits"] == 5
    assert result["misses"] == 5
    assert result["total_requests"] == 20
    assert result["hit_rate"] == 0.75  # 15/20
    assert result["memory_hit_rate"] == 0.5  # 10/20
    assert result["disk_hit_rate"] == 0.25  # 5/20


def test_cache_stats_stores_and_invalidations(sample_file: Path, tmp_path: Path) -> None:
    """Test that store and invalidate operations are tracked."""
    cache = AnalysisCache(cache_dir=tmp_path / "cache")

    cache.store(sample_file, "test_value")
    assert cache.stats.stores == 1

    cache.invalidate(sample_file)
    assert cache.stats.invalidations == 1


# [20251214_TEST] Memory-mapped file hashing tests
def test_hash_file_mmap_for_large_files(tmp_path: Path) -> None:
    """Test that large files use memory-mapped hashing."""
    from code_scalpel.cache.unified_cache import MMAP_THRESHOLD_BYTES

    cache = AnalysisCache(cache_dir=tmp_path / "cache")

    # Create a file larger than threshold
    large_file = tmp_path / "large.py"
    content = b"x = 1\n" * (MMAP_THRESHOLD_BYTES // 6 + 1000)
    large_file.write_bytes(content)

    # Hash should work via mmap path
    hash1 = cache._hash_file(large_file)
    assert len(hash1) == 64  # SHA256 hex length

    # Verify hash is consistent
    hash2 = cache._hash_file(large_file)
    assert hash1 == hash2


def test_hash_file_small_uses_read_bytes(tmp_path: Path) -> None:
    """Test that small files use regular read_bytes."""
    from code_scalpel.cache.unified_cache import MMAP_THRESHOLD_BYTES

    cache = AnalysisCache(cache_dir=tmp_path / "cache")

    small_file = tmp_path / "small.py"
    small_file.write_text("x = 1\n", encoding="utf-8")

    assert small_file.stat().st_size < MMAP_THRESHOLD_BYTES

    hash1 = cache._hash_file(small_file)
    assert len(hash1) == 64  # SHA256 hex length
