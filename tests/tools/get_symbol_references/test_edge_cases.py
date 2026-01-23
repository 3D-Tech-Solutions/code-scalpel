import pytest


@pytest.mark.asyncio
async def test_decorator_and_annotation_references(make_project, patch_tier, patch_capabilities):
    """[20260104_TEST] Decorators and annotations should be reported when categorization is enabled."""
    import code_scalpel.mcp.tools.context as server

    project = make_project(
        {
            "mod.py": """
from target_mod import target

@target
def decorated() -> target:
    pass

value: target = target()
""",
            "target_mod.py": """
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
                "read_write_classification",
                "import_classification",
            ],
        }
    )

    result = await server.get_symbol_references("target", project_root=str(project))

    assert result.success is True
    assert any(ref.reference_type == "decorator" for ref in result.references)
    assert any(ref.reference_type == "type_annotation" for ref in result.references)


@pytest.mark.asyncio
async def test_import_alias_references(make_project, patch_tier, patch_capabilities):
    """[20260109_TEST] Import aliases (import X as Y) should be found when searching for original symbol."""
    import code_scalpel.mcp.tools.context as server

    project = make_project(
        {
            "mod.py": """
from target_mod import target as alias_target
from target_mod import target

# Using both original and alias names
result1 = target()
result2 = alias_target()

def process(x: target):
    return x
""",
            "target_mod.py": """
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
                "read_write_classification",
                "import_classification",
            ],
        }
    )

    result = await server.get_symbol_references("target", project_root=str(project))

    assert result.success is True
    # Should find all references including the aliased import
    assert len(result.references) >= 3  # definition, import target, import as alias


@pytest.mark.asyncio
async def test_from_import_alias_references(make_project, patch_tier, patch_capabilities):
    """[20260109_TEST] From-import aliases (from X import Y as Z) should find both definitions and usages."""
    import code_scalpel.mcp.tools.context as server

    project = make_project(
        {
            "mod.py": """
from target_mod import target as my_target
from target_mod import target

value1 = my_target()
value2 = target()
""",
            "target_mod.py": """
def target():
    return 42
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

    result = await server.get_symbol_references("target", project_root=str(project))

    assert result.success is True
    # Should find: definition, direct import, aliased import, and usages
    assert result.total_references >= 3


@pytest.mark.asyncio
async def test_star_import_references(make_project, patch_tier, patch_capabilities):
    """[20260109_TEST] Star imports (from X import *) should find all references including via star import."""
    import code_scalpel.mcp.tools.context as server

    project = make_project(
        {
            "mod.py": """
from target_mod import *

# target is now available via star import
result = target()
""",
            "target_mod.py": """
def target():
    return 1

def helper():
    return 2
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

    result = await server.get_symbol_references("target", project_root=str(project))

    assert result.success is True
    # Should find definition and star-import usage
    assert len(result.references) >= 2


@pytest.mark.asyncio
async def test_multiple_star_imports(make_project, patch_tier, patch_capabilities):
    """[20260109_TEST] Multiple star imports should all be tracked."""
    import code_scalpel.mcp.tools.context as server

    project = make_project(
        {
            "mod1.py": """
from target_mod import *
from other_mod import *

value = target()
""",
            "mod2.py": """
from target_mod import *

x = target()
""",
            "target_mod.py": """
def target():
    return 1
""",
            "other_mod.py": """
def other_func():
    pass
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

    result = await server.get_symbol_references("target", project_root=str(project))

    assert result.success is True
    # Should find definition, both star imports, and both usages
    assert result.total_references >= 3
