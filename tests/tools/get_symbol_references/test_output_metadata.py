"""MCP tests for get_symbol_references output metadata fields.

[20260111_TEST] v3.3.2 - Verify tier transparency via output metadata fields.
These tests ensure that clients can understand what limits and capabilities
were applied to their request.
"""

import pytest


@pytest.mark.asyncio
async def test_community_tier_output_metadata(make_project, patch_tier, patch_capabilities):
    """[20260111_TEST] Community tier should populate output metadata with limits."""
    import code_scalpel.mcp.tools.context as server

    project = make_project(
        {f"src/file_{i}.py": """
from shared.target import target

def use():
    return target()
""" for i in range(5)}
        | {
            "shared/target.py": """
def target():
    return 1
""",
        }
    )

    patch_tier("community")
    patch_capabilities(
        {
            "limits": {"max_files_searched": 3, "max_references": 10},
            "capabilities": ["ast_based_find_usages", "exact_reference_matching"],
        }
    )

    result = await server.get_symbol_references("target", project_root=str(project))

    assert result.success is True
    # Verify output metadata fields are populated
    assert result.tier_applied == "community"
    assert result.max_files_applied == 3
    assert result.max_references_applied == 10
    # Community has no Pro/Enterprise features
    assert result.pro_features_enabled is None
    assert result.enterprise_features_enabled is None


@pytest.mark.asyncio
async def test_pro_tier_output_metadata(make_project, patch_tier, patch_capabilities):
    """[20260111_TEST] Pro tier should show unlimited and list enabled features."""
    import code_scalpel.mcp.tools.context as server

    project = make_project(
        {
            "src/app/target.py": """
def target():
    return 1
""",
            "src/app/consumer.py": """
from app.target import target

result = target()
""",
        }
    )

    patch_tier("pro")
    patch_capabilities(
        {
            "limits": {},  # Unlimited
            "capabilities": [
                "ast_based_find_usages",
                "exact_reference_matching",
                "usage_categorization",
                "read_write_classification",
                "scope_filtering",
                "test_file_filtering",
            ],
        }
    )

    result = await server.get_symbol_references("target", project_root=str(project))

    assert result.success is True
    # Verify output metadata
    assert result.tier_applied == "pro"
    assert result.max_files_applied is None  # Unlimited
    assert result.max_references_applied is None  # Unlimited
    # Pro features should be listed
    assert result.pro_features_enabled is not None
    assert "usage_categorization" in result.pro_features_enabled
    assert "scope_filtering" in result.pro_features_enabled
    # No Enterprise features
    assert result.enterprise_features_enabled is None


@pytest.mark.asyncio
async def test_enterprise_tier_output_metadata(make_project, patch_tier, patch_capabilities):
    """[20260111_TEST] Enterprise tier should show all features enabled."""
    import code_scalpel.mcp.tools.context as server

    project = make_project(
        {
            "CODEOWNERS": """
* @global
src/** @app-team
""",
            "src/app/target.py": """
def target():
    return 1
""",
            "src/app/consumer.py": """
from app.target import target

result = target()
""",
        }
    )

    patch_tier("enterprise")
    patch_capabilities(
        {
            "limits": {},  # Unlimited
            "capabilities": [
                "ast_based_find_usages",
                "exact_reference_matching",
                "usage_categorization",
                "read_write_classification",
                "scope_filtering",
                "test_file_filtering",
                "codeowners_integration",
                "ownership_attribution",
                "impact_analysis",
                "change_risk_assessment",
            ],
        }
    )

    result = await server.get_symbol_references("target", project_root=str(project))

    assert result.success is True
    # Verify output metadata
    assert result.tier_applied == "enterprise"
    assert result.max_files_applied is None  # Unlimited
    assert result.max_references_applied is None  # Unlimited
    # Pro features should be listed
    assert result.pro_features_enabled is not None
    assert "usage_categorization" in result.pro_features_enabled
    # Enterprise features should be listed
    assert result.enterprise_features_enabled is not None
    assert "codeowners_integration" in result.enterprise_features_enabled
    assert "impact_analysis" in result.enterprise_features_enabled
