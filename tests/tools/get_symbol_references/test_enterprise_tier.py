import pytest


@pytest.mark.asyncio
async def test_enterprise_codeowners_and_ownership(make_project, patch_tier, patch_capabilities):
    """[20260104_TEST] Enterprise should attribute owners via CODEOWNERS when enabled."""
    import code_scalpel.mcp.tools.context as server

    project = make_project(
        {
            "CODEOWNERS": """
* @global
src/app/** @app-team
""",
            "src/app/service.py": """
from shared.target import target

def use():
    return target()
""",
            "shared/target.py": """
def target():
    return 1
""",
        }
    )

    patch_tier("enterprise")
    patch_capabilities(
        {
            "limits": {},
            "capabilities": [
                "usage_categorization",
                "codeowners_integration",
                "ownership_attribution",
            ],
        }
    )

    result = await server.get_symbol_references("target", project_root=str(project))

    assert result.success is True
    assert result.owner_counts is not None
    assert any(ref.owners for ref in result.references)


@pytest.mark.asyncio
async def test_enterprise_impact_analysis(make_project, patch_tier, patch_capabilities):
    """[20260104_TEST] Enterprise impact analysis fields should populate when enabled."""
    import code_scalpel.mcp.tools.context as server

    project = make_project(
        {
            "CODEOWNERS": """
* @global
src/** @app-team
""",
            "src/a.py": """
from shared.target import target

def a():
    return target()
""",
            "src/b.py": """
from shared.target import target

def b():
    return target()
""",
            "shared/target.py": """
def target():
    return 1
""",
        }
    )

    patch_tier("enterprise")
    patch_capabilities(
        {
            "limits": {},
            "capabilities": [
                "usage_categorization",
                "codeowners_integration",
                "ownership_attribution",
                "impact_analysis",
                "change_risk_assessment",
            ],
        }
    )

    result = await server.get_symbol_references("target", project_root=str(project))

    assert result.success is True
    assert result.risk_score is not None
    assert result.blast_radius is not None
    assert result.change_risk is not None
    # impact fields should be present when enabled
    assert result.complexity_hotspots is not None
    assert result.impact_mermaid is not None
