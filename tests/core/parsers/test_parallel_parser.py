from pathlib import Path

from code_scalpel.cache.parallel_parser import ParallelParser
from code_scalpel.cache.unified_cache import AnalysisCache


def parse_len(path: Path) -> int:
    return len(path.read_text(encoding="utf-8"))


def parse_fail(path: Path) -> int:
    raise ValueError(f"boom:{path.name}")


def test_parallel_parser_uses_cache_and_parses_misses(tmp_path: Path) -> None:
    cache_dir = tmp_path / "cache"
    cache = AnalysisCache[int](cache_dir=cache_dir)

    hit = tmp_path / "hit.py"
    miss = tmp_path / "miss.py"
    hit.write_text("hit", encoding="utf-8")
    miss.write_text("miss", encoding="utf-8")

    # Seed cache for hit
    cache.get_or_parse(hit, parse_fn=parse_len)

    parser = ParallelParser(cache, max_workers=2)
    results, errors = parser.parse_files([hit, miss], parse_fn=parse_len)

    assert errors == []
    assert results[str(hit.resolve())] == len("hit")
    assert results[str(miss.resolve())] == len("miss")


def test_parallel_parser_collects_errors(tmp_path: Path) -> None:
    cache = AnalysisCache[int](cache_dir=tmp_path / "cache")
    bad = tmp_path / "bad.py"
    bad.write_text("bad", encoding="utf-8")

    parser = ParallelParser(cache, max_workers=1)
    results, errors = parser.parse_files([bad], parse_fn=parse_fail)

    assert results == {}
    assert errors == [str(bad.resolve())]


def test_parallel_parser_handles_unpicklable_callable(tmp_path: Path) -> None:
    cache = AnalysisCache[int](cache_dir=tmp_path / "cache")
    target = tmp_path / "target.py"
    target.write_text("x", encoding="utf-8")

    # Lambdas/closures are not picklable on Windows spawn; expect failure recorded.
    parser = ParallelParser(cache, max_workers=1)
    results, errors = parser.parse_files([target], parse_fn=lambda p: 1)  # type: ignore[arg-type]

    assert results == {}
    assert errors == [str(target.resolve())]
