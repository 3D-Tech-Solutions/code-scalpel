import pytest


@pytest.mark.asyncio
async def test_pro_reference_categorization_and_counts(make_project, patch_tier, patch_capabilities):
    """[20260104_TEST] Pro tier should emit category_counts and typed references."""
    import code_scalpel.mcp.tools.context as server

    project = make_project(
        {
            "src/app/target.py": """
@target
def wrapped():
    return target()

x: target = target()
y = x
""",
            "src/app/consumer.py": """
from app import target

result = target()
""",
        }
    )

    patch_tier("pro")
    patch_capabilities(
        {
            "limits": {},
            "capabilities": [
                "usage_categorization",
                "read_write_classification",
                "import_classification",
            ],
        }
    )

    result = await server.get_symbol_references(symbol_name="target", project_root=str(project))

    assert result.success is True
    assert result.category_counts is not None
    assert result.total_references > 0
    # Ensure at least call/definition categories are tracked.
    assert "call" in result.category_counts or "definition" in result.category_counts
    # All reference_type values must be present when categorization enabled.
    assert all(ref.reference_type is not None for ref in result.references)


@pytest.mark.asyncio
async def test_pro_scope_filtering_and_test_exclusion(make_project, patch_tier, patch_capabilities):
    """[20260104_TEST] Pro filtering gates scope_prefix and include_tests flags."""
    import code_scalpel.mcp.tools.context as server

    project = make_project(
        {
            "src/feature/use_target.py": """
from shared.target import target

def run():
    return target()
""",
            "src/other/use_target.py": """
from shared.target import target

def call():
    return target()
""",
            "tests/test_target.py": """
from shared.target import target

def test_call():
    target()
""",
            "shared/target.py": """
def target():
    return 1
""",
        }
    )

    patch_tier("pro")
    patch_capabilities(
        {
            "limits": {},
            "capabilities": [
                "usage_categorization",
                "scope_filtering",
                "test_file_filtering",
            ],
        }
    )

    result = await server.get_symbol_references(
        symbol_name="target",
        project_root=str(project),
        scope_prefix="src/feature",
        include_tests=False,
    )

    assert result.success is True
    assert all(ref.file.startswith("src/feature") for ref in result.references)
    assert all("tests/" not in ref.file for ref in result.references)
