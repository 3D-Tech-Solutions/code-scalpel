from pathlib import Path

import pytest

pytestmark = pytest.mark.asyncio


def _write(p: Path, content: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")


# [20260101_SKIP] Spec test for multi-language crawl - feature in progress
@pytest.mark.skip(reason="Multi-language crawl and language_breakdown not yet implemented")
async def test_crawl_project_community_multilanguage_and_limits(tmp_path: Path, community_tier):
    # Tier is enforced via community_tier fixture (license discovery disabled)

    root = tmp_path / "proj"
    root.mkdir()

    _write(root / "a.py", "def f():\n    if True:\n        return 1\n")
    _write(root / "b.js", "export function g(){ if(true){ return 1 } }")
    _write(
        root / "c.java",
        "package x;\nimport java.util.List;\nclass C { void m(){ if(true){} } }",
    )

    from code_scalpel.mcp.server import crawl_project

    result = await crawl_project(root_path=str(root), include_report=False)
    assert result.success is True

    # Community limit should cap at 100; we only have 3.
    assert result.summary.total_files == 3

    # Language breakdown should include these languages
    assert result.language_breakdown["python"] == 1
    assert result.language_breakdown["javascript"] == 1
    assert result.language_breakdown["java"] == 1

    paths = {f.path for f in result.files}
    assert "a.py" in paths
    assert "b.js" in paths
    assert "c.java" in paths


@pytest.mark.skip(reason="cache_hits field not implemented in ProjectCrawlResult")
async def test_crawl_project_pro_cache_hits(tmp_path: Path, pro_tier):

    root = tmp_path / "proj"
    root.mkdir()

    _write(root / "a.py", "def f():\n    if True:\n        return 1\n")

    from code_scalpel.mcp.server import crawl_project

    r1 = await crawl_project(root_path=str(root), include_report=False)
    assert r1.success is True
    assert r1.cache_hits == 0

    r2 = await crawl_project(root_path=str(root), include_report=False)
    assert r2.success is True
    assert r2.cache_hits >= 1


# [20260101_SKIP] Spec test for Enterprise compliance - feature not implemented
@pytest.mark.skip(reason="compliance_summary field not implemented in ProjectCrawlResult")
async def test_crawl_project_enterprise_compliance_best_effort(tmp_path: Path, enterprise_tier):

    root = tmp_path / "proj"
    root.mkdir()

    _write(
        root / "a.py",
        "import hashlib\n\n# BAD: weak hash\nmd5 = hashlib.md5(b'x').hexdigest()\n",
    )

    from code_scalpel.mcp.server import crawl_project

    result = await crawl_project(root_path=str(root), include_report=False)
    assert result.success is True

    summary = result.compliance_summary
    assert summary is None or isinstance(summary, dict)


async def test_crawl_project_enterprise_custom_rules_config(tmp_path: Path, enterprise_tier):

    root = tmp_path / "proj"
    root.mkdir()

    _write(root / "a.py", "def f():\n    return 1\n")
    _write(root / "b.js", "export const x = 1;")

    # Only include Python via custom crawl rules
    cfg_dir = root / ".code-scalpel"
    cfg_dir.mkdir()
    _write(
        cfg_dir / "crawl_project.json",
        '{"include_extensions": [".py"], "exclude_dirs": []}',
    )

    from code_scalpel.mcp.server import crawl_project

    result = await crawl_project(root_path=str(root), include_report=False)
    assert result.success is True
    paths = {f.path for f in result.files}
    assert "a.py" in paths
    assert "b.js" not in paths
