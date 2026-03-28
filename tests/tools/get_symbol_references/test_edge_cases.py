import pytest


@pytest.mark.asyncio
async def test_decorator_and_annotation_references(
    make_project, patch_tier, patch_capabilities
):
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
async def test_from_import_alias_references(
    make_project, patch_tier, patch_capabilities
):
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


@pytest.mark.asyncio
async def test_typescript_definition_import_and_call_references(
    make_project, patch_tier, patch_capabilities
):
    """[20260307_TEST] TypeScript symbol references should include local definition, import, and call sites."""
    import code_scalpel.mcp.tools.context as server

    project = make_project(
        {
            "src/target.ts": """
export function target(): number {
    return 1
}
""",
            "src/consumer.ts": """
import { target } from "./target"

const value = target()
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

    data = (
        result.data if hasattr(result, "data") and isinstance(result.data, dict) else {}
    )
    assert data.get("success", getattr(result, "success", False)) is True
    assert data.get("definition_file") == "src/target.ts"
    assert data.get("tier_applied") == "pro"
    assert data.get("max_files_applied") is None
    assert data.get("max_references_applied") is None
    category_counts = data.get("category_counts") or {}
    assert category_counts.get("definition", 0) >= 1
    assert category_counts.get("import", 0) >= 1
    assert category_counts.get("call", 0) >= 1
    references = data.get("references") or []
    assert any(ref.get("file") == "src/consumer.ts" for ref in references)


@pytest.mark.asyncio
async def test_java_definition_import_and_call_references(
    make_project, patch_tier, patch_capabilities
):
    """[20260308_TEST] Java symbol references should include local definition, import, and call sites."""
    import code_scalpel.mcp.tools.context as server

    project = make_project(
        {
            "src/demo/Helper.java": """
package demo;

public class Helper {
    public static int tool() {
        return 1;
    }
}
""",
            "src/demo/App.java": """
package demo;

import static demo.Helper.tool;

public class App {
    public int run() {
        return tool();
    }
}
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

    result = await server.get_symbol_references("tool", project_root=str(project))

    data = (
        result.data if hasattr(result, "data") and isinstance(result.data, dict) else {}
    )
    assert data.get("success", getattr(result, "success", False)) is True
    assert data.get("definition_file") == "src/demo/Helper.java"
    assert data.get("tier_applied") == "pro"
    category_counts = data.get("category_counts") or {}
    assert category_counts.get("definition", 0) >= 1
    assert category_counts.get("import", 0) >= 1
    assert category_counts.get("call", 0) >= 1
    references = data.get("references") or []
    assert any(ref.get("file") == "src/demo/App.java" for ref in references)


@pytest.mark.asyncio
async def test_java_static_wildcard_import_references(
    make_project, patch_tier, patch_capabilities
):
    """[20260315_TEST] Java symbol references should classify static wildcard imports for local members."""
    import code_scalpel.mcp.tools.context as server

    project = make_project(
        {
            "src/demo/Helper.java": """
package demo;

public class Helper {
    public static int tool() {
        return 1;
    }
}
""",
            "src/demo/App.java": """
package demo;

import static demo.Helper.*;

public class App {
    public int run() {
        return tool();
    }
}
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

    result = await server.get_symbol_references("tool", project_root=str(project))

    data = (
        result.data if hasattr(result, "data") and isinstance(result.data, dict) else {}
    )
    assert data.get("success", getattr(result, "success", False)) is True
    assert data.get("definition_file") == "src/demo/Helper.java"
    category_counts = data.get("category_counts") or {}
    assert category_counts.get("definition", 0) >= 1
    assert category_counts.get("import", 0) >= 1
    assert category_counts.get("call", 0) >= 1
    references = data.get("references") or []
    assert any(
        ref.get("file") == "src/demo/App.java"
        and "import static demo.Helper.*;" in ref.get("context", "")
        for ref in references
    )
    assert any(
        ref.get("file") == "src/demo/App.java"
        and "return tool();" in ref.get("context", "")
        for ref in references
    )


@pytest.mark.asyncio
async def test_go_definition_and_call_references(
    make_project, patch_tier, patch_capabilities
):
    """[20260311_TEST] Go symbol references should include local definitions and call sites."""
    import code_scalpel.mcp.tools.context as server

    pytest.importorskip("tree_sitter_go")

    project = make_project(
        {
            "src/helper/helper.go": """
package helper

func Tool() int {
    return 1
}
""",
            "src/main.go": """
package main

import "src/helper"

func run() int {
    return helper.Tool()
}
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

    result = await server.get_symbol_references("Tool", project_root=str(project))

    data = (
        result.data if hasattr(result, "data") and isinstance(result.data, dict) else {}
    )
    assert data.get("success", getattr(result, "success", False)) is True
    assert data.get("definition_file") == "src/helper/helper.go"
    category_counts = data.get("category_counts") or {}
    assert category_counts.get("definition", 0) >= 1
    assert category_counts.get("call", 0) >= 1
    references = data.get("references") or []
    assert any(
        ref.get("file") == "src/main.go" and "helper.Tool()" in ref.get("context", "")
        for ref in references
    )


@pytest.mark.asyncio
async def test_go_method_definition_and_call_references(
    make_project, patch_tier, patch_capabilities
):
    """[20260311_TEST] Go symbol references should include receiver methods and method calls."""
    import code_scalpel.mcp.tools.context as server

    pytest.importorskip("tree_sitter_go")

    project = make_project(
        {
            "src/worker.go": """
package demo

type Worker struct{}

func (w Worker) Run() {
}

func execute(worker Worker) {
    worker.Run()
}
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

    result = await server.get_symbol_references("Run", project_root=str(project))

    data = (
        result.data if hasattr(result, "data") and isinstance(result.data, dict) else {}
    )
    assert data.get("success", getattr(result, "success", False)) is True
    assert data.get("definition_file") == "src/worker.go"
    category_counts = data.get("category_counts") or {}
    assert category_counts.get("definition", 0) >= 1
    assert category_counts.get("call", 0) >= 1
    references = data.get("references") or []
    assert any(
        ref.get("file") == "src/worker.go" and "worker.Run()" in ref.get("context", "")
        for ref in references
    )


@pytest.mark.asyncio
async def test_java_overloaded_methods_clear_singular_definition_metadata(
    make_project, patch_tier, patch_capabilities
):
    """[20260308_TEST] Java overload ambiguity should avoid claiming a singular definition."""
    import code_scalpel.mcp.tools.context as server

    project = make_project(
        {
            "src/demo/Helper.java": """
package demo;

public class Helper {
    public void tool() {
    }

    public void tool(int value) {
    }

    public void run() {
        tool();
        tool(1);
    }
}
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

    result = await server.get_symbol_references("tool", project_root=str(project))

    data = (
        result.data if hasattr(result, "data") and isinstance(result.data, dict) else {}
    )
    assert data.get("success", getattr(result, "success", False)) is True
    assert data.get("definition_file") is None
    assert data.get("definition_line") is None
    assert data.get("ambiguity_kind") == "multiple_definitions"
    warnings = data.get("warnings", getattr(result, "warnings", [])) or []
    assert any(
        "ambiguous java definition metadata" in warning.lower() for warning in warnings
    )
    candidates = data.get("ambiguity_candidates") or []
    selectors = {candidate.get("selector") for candidate in candidates}
    assert "Helper.tool()" in selectors
    assert "Helper.tool(int)" in selectors
    references = data.get("references") or []
    definition_refs = [ref for ref in references if ref.get("is_definition")]
    assert len(definition_refs) >= 2
    category_counts = data.get("category_counts") or {}
    assert category_counts.get("definition", 0) >= 2


@pytest.mark.asyncio
async def test_java_inherited_override_clears_singular_definition_metadata(
    make_project, patch_tier, patch_capabilities
):
    """[20260308_TEST] Java inherited overrides should avoid claiming a singular definition."""
    import code_scalpel.mcp.tools.context as server

    project = make_project(
        {
            "src/demo/Base.java": """
package demo;

public class Base {
    protected void helper() {
    }
}
""",
            "src/demo/Child.java": """
package demo;

public class Child extends Base {
    @Override
    protected void helper() {
    }

    public void run() {
        helper();
        this.helper();
    }
}
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

    result = await server.get_symbol_references("helper", project_root=str(project))

    data = (
        result.data if hasattr(result, "data") and isinstance(result.data, dict) else {}
    )
    assert data.get("success", getattr(result, "success", False)) is True
    assert data.get("definition_file") is None
    assert data.get("definition_line") is None
    assert data.get("ambiguity_kind") == "multiple_definitions"
    warnings = data.get("warnings", getattr(result, "warnings", [])) or []
    assert any(
        "ambiguous java definition metadata" in warning.lower() for warning in warnings
    )
    candidates = data.get("ambiguity_candidates") or []
    selectors = {candidate.get("selector") for candidate in candidates}
    assert "Base.helper()" in selectors
    assert "Child.helper()" in selectors
    references = data.get("references") or []
    definition_files = {
        ref.get("file") for ref in references if ref.get("is_definition")
    }
    assert {"src/demo/Base.java", "src/demo/Child.java"} <= definition_files


@pytest.mark.asyncio
async def test_java_structured_selector_resolves_exact_overload(
    make_project, patch_tier, patch_capabilities
):
    """[20260309_TEST] Java structured selectors should resolve an exact overload without leaving singular definition metadata ambiguous."""
    import code_scalpel.mcp.tools.context as server

    project = make_project(
        {
            "src/demo/Helper.java": """
package demo;

public class Helper {
    public static void tool(int value) {
    }

    public static void tool(String value) {
    }
}
""",
            "src/demo/App.java": """
package demo;

import static demo.Helper.tool;

public class App {
    public void run() {
        tool(1);
        tool("x");
    }
}
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

    result = await server.get_symbol_references(
        "Helper.tool(int)", project_root=str(project)
    )

    data = (
        result.data if hasattr(result, "data") and isinstance(result.data, dict) else {}
    )
    assert data.get("success", getattr(result, "success", False)) is True
    assert data.get("definition_file") == "src/demo/Helper.java"
    assert data.get("definition_line") is not None
    assert data.get("ambiguity_kind") is None
    references = data.get("references") or []
    assert any(
        ref.get("file") == "src/demo/App.java" and "tool(1)" in ref.get("context", "")
        for ref in references
    )
    assert not any(
        ref.get("file") == "src/demo/App.java" and 'tool("x")' in ref.get("context", "")
        for ref in references
    )


@pytest.mark.asyncio
async def test_java_structured_selector_colon_form_resolves_exact_overload(
    make_project, patch_tier, patch_capabilities
):
    """[20260309_TEST] Java structured selectors should accept Class:method(type) as an exact overload key."""
    import code_scalpel.mcp.tools.context as server

    project = make_project(
        {
            "src/demo/Helper.java": """
package demo;

public class Helper {
    public static void tool(int value) {
    }

    public static void tool(String value) {
    }
}
""",
            "src/demo/App.java": """
package demo;

import static demo.Helper.tool;

public class App {
    public void run() {
        tool(1);
        tool("x");
    }
}
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

    result = await server.get_symbol_references(
        "Helper:tool(int)", project_root=str(project)
    )

    data = (
        result.data if hasattr(result, "data") and isinstance(result.data, dict) else {}
    )
    assert data.get("success", getattr(result, "success", False)) is True
    assert data.get("definition_file") == "src/demo/Helper.java"
    assert data.get("ambiguity_kind") is None
    references = data.get("references") or []
    assert any(
        ref.get("file") == "src/demo/App.java" and "tool(1)" in ref.get("context", "")
        for ref in references
    )
    assert not any(
        ref.get("file") == "src/demo/App.java" and 'tool("x")' in ref.get("context", "")
        for ref in references
    )


@pytest.mark.asyncio
async def test_java_constructor_selector_resolves_exact_overload(
    make_project, patch_tier, patch_capabilities
):
    """[20260311_TEST] Java structured selectors should resolve exact constructor overloads."""
    import code_scalpel.mcp.tools.context as server

    project = make_project(
        {
            "src/demo/Helper.java": """
package demo;

public class Helper {
    public Helper(int value) {
    }

    public Helper(String value) {
    }
}
""",
            "src/demo/App.java": """
package demo;

public class App {
    public void run() {
        new Helper(1);
        new Helper("x");
    }
}
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

    result = await server.get_symbol_references(
        "Helper.Helper(int)", project_root=str(project)
    )

    data = (
        result.data if hasattr(result, "data") and isinstance(result.data, dict) else {}
    )
    assert data.get("success", getattr(result, "success", False)) is True
    assert data.get("definition_file") == "src/demo/Helper.java"
    assert data.get("ambiguity_kind") is None
    references = data.get("references") or []
    assert any(
        ref.get("file") == "src/demo/App.java"
        and "new Helper(1)" in ref.get("context", "")
        for ref in references
    )
    assert not any(
        ref.get("file") == "src/demo/App.java"
        and 'new Helper("x")' in ref.get("context", "")
        for ref in references
    )


@pytest.mark.asyncio
async def test_java_constructor_selector_colon_form_resolves_exact_overload(
    make_project, patch_tier, patch_capabilities
):
    """[20260311_TEST] Java structured selectors should accept Class:Class(type) constructor keys."""
    import code_scalpel.mcp.tools.context as server

    project = make_project(
        {
            "src/demo/Helper.java": """
package demo;

public class Helper {
    public Helper(int value) {
    }

    public Helper(String value) {
    }
}
""",
            "src/demo/App.java": """
package demo;

public class App {
    public void run() {
        new Helper(1);
        new Helper("x");
    }
}
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

    result = await server.get_symbol_references(
        "Helper:Helper(String)", project_root=str(project)
    )

    data = (
        result.data if hasattr(result, "data") and isinstance(result.data, dict) else {}
    )
    assert data.get("success", getattr(result, "success", False)) is True
    assert data.get("definition_file") == "src/demo/Helper.java"
    assert data.get("ambiguity_kind") is None
    references = data.get("references") or []
    assert any(
        ref.get("file") == "src/demo/App.java"
        and 'new Helper("x")' in ref.get("context", "")
        for ref in references
    )
    assert not any(
        ref.get("file") == "src/demo/App.java"
        and "new Helper(1)" in ref.get("context", "")
        for ref in references
    )
