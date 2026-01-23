from __future__ import annotations

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.asyncio


async def test_community_enforces_limit_and_discovery_mode(large_python_project: Path, community_env: None) -> None:
    from code_scalpel.mcp.tools.context import crawl_project

    result = await crawl_project(root_path=str(large_python_project), include_report=False)
    assert result.success is True

    # Community limit should cap analyzed files
    assert result.summary.total_files <= 100
    assert len(result.files) <= 100

    # Discovery mode should not include deep function/class details
    assert result.summary.total_functions == 0
    assert result.summary.total_classes == 0
    assert all(len(f.functions) == 0 for f in result.files)
    assert all(len(f.classes) == 0 for f in result.files)


async def test_community_blocks_enterprise_pattern_feature(small_python_project: Path, community_env: None) -> None:
    from code_scalpel.mcp.tools.context import crawl_project

    result = await crawl_project(
        root_path=str(small_python_project),
        include_report=False,
        pattern="def",
        pattern_type="regex",
    )
    pattern_success = getattr(result, "pattern_success", None)
    pattern_error = getattr(result, "pattern_error", "")

    assert pattern_success is False
    assert "requires" in pattern_error.lower()


async def test_enterprise_creates_incremental_cache(
    small_python_project: Path,
    enterprise_env: None,
    clean_cache,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from code_scalpel.licensing import get_tool_capabilities
    from code_scalpel.mcp.tools.context import crawl_project

    caps = get_tool_capabilities("crawl_project", "enterprise")
    advertised_caps = set(caps.get("capabilities", set()))
    assert "incremental_indexing" in advertised_caps

    # Force tier for test to exercise Enterprise path without a license
    monkeypatch.setenv("CODE_SCALPEL_TEST_FORCE_TIER", "1")

    clean_cache(small_python_project)
    cache_file = Path(small_python_project) / ".scalpel_cache" / "crawl_cache.json"

    first = await crawl_project(root_path=str(small_python_project), include_report=False)
    assert first.success is True
    assert cache_file.exists()

    data = json.loads(cache_file.read_text(encoding="utf-8"))
    assert len(data) >= 1

    second = await crawl_project(root_path=str(small_python_project), include_report=False)
    assert second.success is True
    assert cache_file.exists()


async def test_invalid_tier_env_falls_back_to_community_limits(
    large_python_project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from code_scalpel.mcp.tools.context import crawl_project

    # Disable license discovery without setting tier -> should fall back to community
    monkeypatch.setenv("CODE_SCALPEL_DISABLE_LICENSE_DISCOVERY", "1")
    monkeypatch.delenv("CODE_SCALPEL_TIER", raising=False)
    monkeypatch.delenv("CODE_SCALPEL_LICENSE_PATH", raising=False)

    result = await crawl_project(root_path=str(large_python_project), include_report=False)
    assert result.success is True

    # Fallback should enforce community limits when license invalid/missing
    assert result.summary.total_files <= 100
    assert len(result.files) <= 100
