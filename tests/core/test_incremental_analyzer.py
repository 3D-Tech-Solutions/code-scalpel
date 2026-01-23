from pathlib import Path

from code_scalpel.cache.incremental_analyzer import IncrementalAnalyzer
from code_scalpel.cache.unified_cache import AnalysisCache


def parse_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_incremental_analyzer_invalidation_and_dependents(tmp_path: Path) -> None:
    cache = AnalysisCache[str](cache_dir=tmp_path / "cache")
    dep = tmp_path / "dep.py"
    user = tmp_path / "user.py"

    dep.write_text("one", encoding="utf-8")
    user.write_text("use dep", encoding="utf-8")

    cache.get_or_parse(dep, parse_fn=parse_text)
    cache.get_or_parse(user, parse_fn=parse_text)

    analyzer = IncrementalAnalyzer[str](cache)
    analyzer.record_dependency(user, dep)

    dep.write_text("two", encoding="utf-8")
    affected = analyzer.update_file(dep, recompute_fn=parse_text)

    # Dependent should be listed and invalidated
    assert str(user.resolve()) in affected
    # After invalidation, cache for user should be None
    cached_user = cache.get_cached(user)
    assert cached_user is None

    # Updated file should now be cached with new content
    assert cache.get_or_parse(dep, parse_fn=parse_text) == "two"


def test_incremental_analyzer_no_dependents(tmp_path: Path) -> None:
    cache = AnalysisCache[str](cache_dir=tmp_path / "cache")
    lone = tmp_path / "lone.py"
    lone.write_text("solo", encoding="utf-8")

    cache.get_or_parse(lone, parse_fn=parse_text)

    analyzer = IncrementalAnalyzer[str](cache)
    affected = analyzer.update_file(lone, recompute_fn=parse_text)

    assert affected == set()
