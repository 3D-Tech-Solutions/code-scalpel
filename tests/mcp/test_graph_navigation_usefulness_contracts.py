"""Public usefulness-contract tests for the highest-value graph and discovery tools.

[20260314_TEST] Verify the documented usefulness slice for get_symbol_references,
get_call_graph, get_graph_neighborhood, get_cross_file_dependencies, get_project_map, and
get_file_context at the public MCP boundary.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest


pytestmark = pytest.mark.asyncio


async def test_get_symbol_references_python_is_core_useful(tmp_path: Path) -> None:
    from code_scalpel.mcp.server import get_symbol_references

    (tmp_path / "utils.py").write_text(
        "def helper_function():\n    return 42\n",
        encoding="utf-8",
    )
    (tmp_path / "main.py").write_text(
        "from utils import helper_function\n\n"
        "def main():\n    return helper_function()\n",
        encoding="utf-8",
    )

    result = await get_symbol_references("helper_function", str(tmp_path))

    assert result.success is True
    assert result.definition_file is not None
    assert result.total_references >= 2


async def test_get_symbol_references_javascript_is_bounded_useful(
    tmp_path: Path,
) -> None:
    from code_scalpel.mcp.server import get_symbol_references

    (tmp_path / "util.js").write_text(
        "export function helper() {\n  return 1;\n}\n",
        encoding="utf-8",
    )
    (tmp_path / "index.js").write_text(
        "import { helper } from './util.js';\n\n"
        "export function main() {\n  return helper();\n}\n",
        encoding="utf-8",
    )

    result = await get_symbol_references("helper", str(tmp_path))

    assert result.success is True
    assert result.total_references >= 2


async def test_get_symbol_references_typescript_is_bounded_useful(
    tmp_path: Path,
) -> None:
    from code_scalpel.mcp.server import get_symbol_references

    (tmp_path / "util.ts").write_text(
        "export function helper(value: number): number {\n  return value + 1;\n}\n",
        encoding="utf-8",
    )
    (tmp_path / "index.ts").write_text(
        "import { helper } from './util.ts';\n\n"
        "export function main(): number {\n  return helper(1);\n}\n",
        encoding="utf-8",
    )

    result = await get_symbol_references("helper", str(tmp_path))

    assert result.success is True
    assert result.total_references >= 2


async def test_get_symbol_references_typescript_tracks_named_import_alias_calls(
    tmp_path: Path,
) -> None:
    from code_scalpel.mcp.server import get_symbol_references

    (tmp_path / "util.ts").write_text(
        "export function helper(value: number): number {\n  return value + 1;\n}\n",
        encoding="utf-8",
    )
    (tmp_path / "index.ts").write_text(
        "import { helper as localHelper } from './util.ts';\n\n"
        "export function main(): number {\n  return localHelper(1);\n}\n",
        encoding="utf-8",
    )

    result = await get_symbol_references("helper", str(tmp_path))

    assert result.success is True
    assert result.total_references >= 3
    assert any(
        ref.file == "index.ts" and "localHelper(1)" in ref.context
        for ref in result.references
    )


async def test_get_symbol_references_java_is_bounded_useful(tmp_path: Path) -> None:
    from code_scalpel.mcp.server import get_symbol_references

    (tmp_path / "App.java").write_text(
        "public class App {\n"
        "  public static void helper() {}\n"
        "  public static void main(String[] args) { helper(); }\n"
        "}\n",
        encoding="utf-8",
    )

    result = await get_symbol_references("helper", str(tmp_path))

    assert result.success is True
    assert result.total_references >= 2


async def test_get_symbol_references_java_pro_tracks_static_wildcard_imports(
    tmp_path: Path,
) -> None:
    from code_scalpel.mcp.server import get_symbol_references

    demo = tmp_path / "demo"
    demo.mkdir()
    (demo / "Helper.java").write_text(
        "package demo;\n\n"
        "public class Helper {\n"
        "  public static int tool() {\n"
        "    return 1;\n"
        "  }\n"
        "}\n",
        encoding="utf-8",
    )
    (demo / "App.java").write_text(
        "package demo;\n\n"
        "import static demo.Helper.*;\n\n"
        "public class App {\n"
        "  public int run() {\n"
        "    return tool();\n"
        "  }\n"
        "}\n",
        encoding="utf-8",
    )

    with patch("code_scalpel.mcp.tools.context._get_current_tier", return_value="pro"):
        result = await get_symbol_references("tool", str(tmp_path))

    assert result.success is True
    assert result.tier_applied in {"pro", "enterprise"}
    assert result.definition_file == "demo/Helper.java"
    assert result.category_counts is not None
    assert result.category_counts.get("import", 0) >= 1
    assert result.category_counts.get("call", 0) >= 1
    assert any(
        ref.file == "demo/App.java"
        and "import static demo.Helper.*;" in ref.context
        for ref in result.references
    )


async def test_get_call_graph_python_is_core_useful(tmp_path: Path) -> None:
    from code_scalpel.mcp.server import get_call_graph

    (tmp_path / "graph_sample.py").write_text(
        "def helper():\n    return 1\n\n"
        "def main():\n    return helper()\n",
        encoding="utf-8",
    )

    result = await get_call_graph(project_root=str(tmp_path))

    assert result.success is True
    assert len(result.nodes) >= 2
    assert len(result.edges) >= 1
    assert result.mermaid.startswith("graph TD")


async def test_get_call_graph_javascript_is_bounded_useful(tmp_path: Path) -> None:
    from code_scalpel.mcp.server import get_call_graph

    (tmp_path / "util.js").write_text(
        "export function foo() {\n  return 1;\n}\n",
        encoding="utf-8",
    )
    (tmp_path / "index.js").write_text(
        "import { foo } from './util.js';\n\n"
        "function main() {\n  foo();\n}\n\n"
        "main();\n",
        encoding="utf-8",
    )

    result = await get_call_graph(
        project_root=str(tmp_path), include_circular_import_check=False
    )

    assert result.error is None
    assert result.success is True
    assert any(node.file == "index.js" for node in result.nodes)
    assert any(edge.caller.endswith(":main") for edge in result.edges)


async def test_get_call_graph_typescript_is_bounded_useful(tmp_path: Path) -> None:
    from code_scalpel.mcp.server import get_call_graph

    (tmp_path / "util.ts").write_text(
        "export function foo(value: number): number {\n  return value + 1;\n}\n",
        encoding="utf-8",
    )
    (tmp_path / "index.ts").write_text(
        "import { foo } from './util.ts';\n\n"
        "function main(): number {\n  return foo(1);\n}\n\n"
        "main();\n",
        encoding="utf-8",
    )

    result = await get_call_graph(
        project_root=str(tmp_path), include_circular_import_check=False
    )

    assert result.error is None
    assert result.success is True
    assert result.language_parity["javascript"] == "runtime_slice"
    assert result.language_parity["typescript"] == "runtime_slice"
    assert any(node.file == "index.ts" for node in result.nodes)
    assert any(edge.caller.endswith(":main") for edge in result.edges)


async def test_get_call_graph_typescript_tracks_tsconfig_alias_imports(
    tmp_path: Path,
) -> None:
    from code_scalpel.mcp.server import get_call_graph

    (tmp_path / "tsconfig.json").write_text(
        '{"compilerOptions": {"baseUrl": ".", "paths": {"@lib/*": ["src/lib/*"]}}}',
        encoding="utf-8",
    )
    lib_dir = tmp_path / "src" / "lib"
    lib_dir.mkdir(parents=True)
    (lib_dir / "helper.ts").write_text(
        "export function helper(value: number): number {\n  return value + 1;\n}\n",
        encoding="utf-8",
    )
    (tmp_path / "index.ts").write_text(
        "import { helper } from '@lib/helper';\n\n"
        "function main(): number {\n  return helper(1);\n}\n\n"
        "main();\n",
        encoding="utf-8",
    )

    result = await get_call_graph(
        project_root=str(tmp_path), include_circular_import_check=False
    )

    assert result.error is None
    assert result.success is True
    assert any(node.file == "src/lib/helper.ts" and node.name == "helper" for node in result.nodes)
    assert any(
        edge.caller == "index.ts:main" and edge.callee == "src/lib/helper.ts:helper"
        for edge in result.edges
    )


async def test_get_call_graph_java_is_bounded_useful(tmp_path: Path) -> None:
    from code_scalpel.mcp.server import get_call_graph

    (tmp_path / "App.java").write_text(
        "public class App {\n"
        "  public static void main(String[] args) {\n"
        "    helper();\n"
        "  }\n\n"
        "  private static void helper() {\n"
        "    utility();\n"
        "  }\n\n"
        "  private static void utility() {}\n"
        "}\n",
        encoding="utf-8",
    )

    result = await get_call_graph(
        project_root=str(tmp_path), include_circular_import_check=False
    )

    assert result.error is None
    assert result.success is True
    names = {node.name for node in result.nodes}
    assert {"App.main", "App.helper", "App.utility"}.issubset(names)


async def test_get_cross_file_dependencies_python_is_core_useful(
    tmp_path: Path,
) -> None:
    from code_scalpel.mcp.server import get_cross_file_dependencies

    (tmp_path / "helper.py").write_text(
        "def helper():\n    return 'help'\n",
        encoding="utf-8",
    )
    (tmp_path / "main.py").write_text(
        "from helper import helper\n\n"
        "def main():\n    return helper()\n",
        encoding="utf-8",
    )

    result = await get_cross_file_dependencies(
        target_file="main.py",
        target_symbol="main",
        project_root=str(tmp_path),
    )

    assert result.success is True
    assert result.target_name == "main"
    assert len(result.extracted_symbols) >= 1
    assert "def main():" in result.combined_code


async def test_get_cross_file_dependencies_javascript_is_bounded_useful(
    tmp_path: Path,
) -> None:
    from code_scalpel.mcp.server import get_cross_file_dependencies

    (tmp_path / "helper.js").write_text(
        "export function helper() {\n  return 'help';\n}\n",
        encoding="utf-8",
    )
    (tmp_path / "main.js").write_text(
        "import { helper } from './helper.js';\n\n"
        "export function main() {\n  return helper();\n}\n",
        encoding="utf-8",
    )

    result = await get_cross_file_dependencies(
        target_file="main.js",
        target_symbol="main",
        project_root=str(tmp_path),
    )

    assert result.success is True
    assert len(result.extracted_symbols) >= 1


async def test_get_cross_file_dependencies_typescript_is_bounded_useful(
    tmp_path: Path,
) -> None:
    from code_scalpel.mcp.server import get_cross_file_dependencies

    (tmp_path / "helper.ts").write_text(
        "export function helper(value: number): number {\n  return value + 1;\n}\n",
        encoding="utf-8",
    )
    (tmp_path / "main.ts").write_text(
        "import { helper } from './helper.ts';\n\n"
        "export function main(): number {\n  return helper(1);\n}\n",
        encoding="utf-8",
    )

    result = await get_cross_file_dependencies(
        target_file="main.ts",
        target_symbol="main",
        project_root=str(tmp_path),
    )

    assert result.success is True
    assert len(result.extracted_symbols) >= 1


async def test_get_cross_file_dependencies_typescript_tracks_tsconfig_alias_imports(
    tmp_path: Path,
) -> None:
    from code_scalpel.mcp.server import get_cross_file_dependencies

    (tmp_path / "tsconfig.json").write_text(
        '{"compilerOptions": {"baseUrl": ".", "paths": {"@lib/*": ["src/lib/*"]}}}',
        encoding="utf-8",
    )
    lib_dir = tmp_path / "src" / "lib"
    lib_dir.mkdir(parents=True)
    (lib_dir / "helper.ts").write_text(
        "export function helper(value: number): number {\n  return value + 1;\n}\n",
        encoding="utf-8",
    )
    (tmp_path / "main.ts").write_text(
        "import { helper } from '@lib/helper';\n\n"
        "export function main(): number {\n  return helper(1);\n}\n",
        encoding="utf-8",
    )

    result = await get_cross_file_dependencies(
        target_file="main.ts",
        target_symbol="main",
        project_root=str(tmp_path),
    )

    assert result.success is True
    assert any(
        symbol.file == "src/lib/helper.ts" and symbol.name == "helper"
        for symbol in result.extracted_symbols
    )


async def test_get_cross_file_dependencies_java_is_bounded_useful(
    tmp_path: Path,
) -> None:
    from code_scalpel.mcp.server import get_cross_file_dependencies

    (tmp_path / "App.java").write_text(
        "public class App {\n"
        "  public static void main(String[] args) {\n"
        "    helper();\n"
        "  }\n\n"
        "  private static void helper() {}\n"
        "}\n",
        encoding="utf-8",
    )

    result = await get_cross_file_dependencies(
        target_file="App.java",
        target_symbol="main",
        project_root=str(tmp_path),
    )

    assert result.success is True
    assert len(result.extracted_symbols) >= 2
    symbol_names = {symbol.name for symbol in result.extracted_symbols}
    assert "App.main" in symbol_names
    assert "App.helper" in symbol_names


async def test_get_cross_file_dependencies_java_pro_resolves_static_wildcard_imports(
    tmp_path: Path,
) -> None:
    from code_scalpel.mcp.server import get_cross_file_dependencies

    demo = tmp_path / "demo"
    demo.mkdir()
    (demo / "Helper.java").write_text(
        "package demo;\n\n"
        "public class Helper {\n"
        "  public static void tool() {}\n"
        "}\n",
        encoding="utf-8",
    )
    (demo / "App.java").write_text(
        "package demo;\n\n"
        "import static demo.Helper.*;\n\n"
        "public class App {\n"
        "  public static void entry() {\n"
        "    tool();\n"
        "  }\n"
        "}\n",
        encoding="utf-8",
    )

    result = await get_cross_file_dependencies(
        target_file="demo/App.java",
        target_symbol="entry",
        project_root=str(tmp_path),
    )

    assert result.success is True
    extracted = {(symbol.name, symbol.file) for symbol in result.extracted_symbols}
    assert ("App.entry", "demo/App.java") in extracted
    assert ("Helper.tool", "demo/Helper.java") in extracted
    assert result.import_graph == {"demo/App.java": ["demo/Helper.java"]}


async def test_get_project_map_python_is_core_useful(tmp_path: Path) -> None:
    from code_scalpel.mcp.server import get_project_map

    (tmp_path / "helper.py").write_text(
        "def helper():\n    return 1\n",
        encoding="utf-8",
    )
    (tmp_path / "main.py").write_text(
        "from helper import helper\n\n"
        "def main():\n    return helper()\n",
        encoding="utf-8",
    )

    result = await get_project_map(
        project_root=str(tmp_path), include_circular_check=False
    )

    assert result.success is True
    assert result.languages.get("python") == 2
    assert result.total_files == 2
    assert any(entry.endswith("main.py:main") for entry in result.entry_points)
    module_paths = {module.path for module in result.modules}
    assert {"helper.py", "main.py"}.issubset(module_paths)
    assert result.mermaid.startswith("graph TD")


async def test_get_project_map_javascript_is_bounded_useful(
    tmp_path: Path,
) -> None:
    from code_scalpel.mcp.server import get_project_map

    (tmp_path / "helper.js").write_text(
        "export function helper() {\n  return 1;\n}\n",
        encoding="utf-8",
    )
    (tmp_path / "processor.js").write_text(
        "import { helper } from './helper.js';\n\n"
        "export function run() {\n  return helper();\n}\n\n"
        "export class Worker {}\n",
        encoding="utf-8",
    )

    result = await get_project_map(
        project_root=str(tmp_path), include_circular_check=False
    )

    assert result.success is True
    assert result.languages.get("javascript") == 2
    modules = {module.path: module for module in result.modules}
    assert "processor.js" in modules
    assert "helper.js" in modules
    assert "run" in modules["processor.js"].functions
    assert "Worker" in modules["processor.js"].classes
    assert "./helper.js" in modules["processor.js"].imports


async def test_get_project_map_typescript_is_bounded_useful(
    tmp_path: Path,
) -> None:
    from code_scalpel.mcp.server import get_project_map

    src = tmp_path / "src"
    api = src / "api"
    api.mkdir(parents=True)

    (api / "index.ts").write_text(
        "export interface User {\n  name: string;\n}\n\n"
        "export function buildUser(name: string): User {\n"
        "  return { name };\n"
        "}\n",
        encoding="utf-8",
    )
    (src / "main.ts").write_text(
        'import { buildUser } from "./api";\n\n'
        "export function run(): User {\n"
        '  return buildUser("demo");\n'
        "}\n",
        encoding="utf-8",
    )

    result = await get_project_map(
        project_root=str(tmp_path), include_circular_check=False
    )

    assert result.success is True
    assert result.languages.get("typescript") == 2
    modules = {module.path: module for module in result.modules}
    assert "src/main.ts" in modules
    assert "src/api/index.ts" in modules
    assert "run" in modules["src/main.ts"].functions
    assert "buildUser" in modules["src/api/index.ts"].functions
    assert "./api" in modules["src/main.ts"].imports
    assert any(
        "src/main.ts:run" in entry_point for entry_point in result.entry_points
    )


async def test_get_project_map_typescript_pro_resolves_tsconfig_alias_relationships(
    tmp_path: Path,
) -> None:
    from code_scalpel.mcp.server import get_project_map

    (tmp_path / "tsconfig.json").write_text(
        '{"compilerOptions": {"baseUrl": ".", "paths": {"@lib/*": ["src/lib/*"]}}}',
        encoding="utf-8",
    )
    lib_dir = tmp_path / "src" / "lib"
    lib_dir.mkdir(parents=True)
    (lib_dir / "helper.ts").write_text(
        "export function helper(value: number): number {\n  return value + 1;\n}\n",
        encoding="utf-8",
    )
    (tmp_path / "src" / "main.ts").write_text(
        "import { helper } from '@lib/helper';\n\n"
        "export function run(): number {\n  return helper(1);\n}\n",
        encoding="utf-8",
    )

    with patch("code_scalpel.mcp.tools.graph._get_current_tier", return_value="pro"):
        result = await get_project_map(
            project_root=str(tmp_path), include_circular_check=False
        )

    assert result.success is True
    assert result.tier_applied == "pro"
    assert result.module_relationships is not None
    assert {
        "source": "src/main.ts",
        "target": "src/lib/helper.ts",
        "type": "import",
    } in result.module_relationships


async def test_get_project_map_go_is_bounded_useful(tmp_path: Path) -> None:
    from code_scalpel.mcp.server import get_project_map

    (tmp_path / "main.go").write_text(
        "package main\n\n"
        'import "fmt"\n\n'
        "func helper() {}\n"
        'func main() { helper(); fmt.Println("x") }\n',
        encoding="utf-8",
    )

    result = await get_project_map(
        project_root=str(tmp_path), include_circular_check=False
    )

    assert result.success is True
    assert result.languages.get("go") == 1
    assert result.total_files == 1
    assert any(module.path == "main.go" for module in result.modules)
    modules = {module.path: module for module in result.modules}
    assert "helper" in modules["main.go"].functions
    assert "main" in modules["main.go"].functions
    assert "fmt" in modules["main.go"].imports
    assert any(entry_point.endswith("main.go:main") for entry_point in result.entry_points)


async def test_get_project_map_java_is_bounded_useful(
    tmp_path: Path,
) -> None:
    from code_scalpel.mcp.server import get_project_map

    demo = tmp_path / "demo"
    util = demo / "util"
    util.mkdir(parents=True)
    (util / "Helper.java").write_text(
        "package demo.util;\n\n"
        "public class Helper {\n"
        "  public static int run() {\n"
        "    return 1;\n"
        "  }\n"
        "}\n",
        encoding="utf-8",
    )
    (demo / "Worker.java").write_text(
        "package demo;\n\n"
        "import demo.util.Helper;\n\n"
        "public class Worker {\n"
        "  public static void main(String[] args) {\n"
        "    Helper.run();\n"
        "  }\n\n"
        "  public static void run() {}\n"
        "}\n",
        encoding="utf-8",
    )

    result = await get_project_map(
        project_root=str(tmp_path), include_circular_check=False
    )

    assert result.success is True
    assert result.languages.get("java") == 2
    modules = {module.path: module for module in result.modules}
    assert "demo/Worker.java" in modules
    assert "demo/util/Helper.java" in modules
    assert "Worker" in modules["demo/Worker.java"].classes
    assert "Worker.main" in modules["demo/Worker.java"].functions
    assert "Worker.run" in modules["demo/Worker.java"].functions
    assert "demo.util.Helper" in modules["demo/Worker.java"].imports
    package_paths = {package.path: package for package in result.packages}
    assert "demo" in package_paths
    assert "demo/util" in package_paths
    assert "demo/Worker.java" in package_paths["demo"].modules
    assert "demo/util/Helper.java" in package_paths["demo/util"].modules
    assert "util" in package_paths["demo"].subpackages
    assert any(
        entry_point.endswith("Worker.main") for entry_point in result.entry_points
    )


async def test_get_project_map_java_pro_resolves_same_package_relationships(
    tmp_path: Path,
) -> None:
    from code_scalpel.mcp.server import get_project_map

    demo = tmp_path / "demo"
    demo.mkdir()
    (demo / "Helper.java").write_text(
        "package demo;\n\n"
        "public class Helper {\n"
        "  public static int tool() {\n"
        "    return 1;\n"
        "  }\n"
        "}\n",
        encoding="utf-8",
    )
    (demo / "App.java").write_text(
        "package demo;\n\n"
        "public class App {\n"
        "  public static void main(String[] args) {\n"
        "    Helper.tool();\n"
        "  }\n"
        "}\n",
        encoding="utf-8",
    )

    with patch("code_scalpel.mcp.tools.graph._get_current_tier", return_value="pro"):
        result = await get_project_map(
            project_root=str(tmp_path), include_circular_check=False
        )

    assert result.success is True
    assert result.tier_applied == "pro"
    assert result.module_relationships is not None
    assert {
        "source": "demo/App.java",
        "target": "demo/Helper.java",
        "type": "import",
    } in result.module_relationships


async def test_get_project_map_kotlin_is_not_yet_useful(tmp_path: Path) -> None:
    from code_scalpel.mcp.server import get_project_map

    (tmp_path / "Worker.kt").write_text(
        "class Worker {\n    fun run() {}\n}\n",
        encoding="utf-8",
    )

    result = await get_project_map(
        project_root=str(tmp_path), include_circular_check=False
    )

    assert result.success is True
    assert result.total_files == 0
    assert result.languages == {}
    assert result.modules == []
    assert result.entry_points == []


async def test_get_project_map_cpp_is_not_yet_useful(tmp_path: Path) -> None:
    from code_scalpel.mcp.server import get_project_map

    (tmp_path / "worker.h").write_text(
        "void run_worker();\n",
        encoding="utf-8",
    )
    (tmp_path / "worker.cpp").write_text(
        '#include "worker.h"\n\n'
        "void run_worker() {}\n"
        "int main() { run_worker(); return 0; }\n",
        encoding="utf-8",
    )

    result = await get_project_map(
        project_root=str(tmp_path), include_circular_check=False
    )

    assert result.success is True
    assert result.total_files == 0
    assert result.languages == {}
    assert result.modules == []
    assert result.entry_points == []


async def test_get_file_context_python_is_core_useful(tmp_path: Path) -> None:
    from code_scalpel.mcp.server import get_file_context

    source_file = tmp_path / "context_target.py"
    source_file.write_text(
        "import os\n\n"
        "def helper_function():\n    return 42\n\n"
        "class MyClass:\n    pass\n",
        encoding="utf-8",
    )

    result = await get_file_context(str(source_file))

    assert result.success is True
    assert result.language == "python"
    assert any(getattr(item, "name", item) == "helper_function" for item in result.functions)
    assert any(getattr(item, "name", item) == "MyClass" for item in result.classes)
    assert "os" in result.imports
    assert result.complexity_score >= 0
    assert result.summary


async def test_get_file_context_javascript_is_bounded_useful(
    tmp_path: Path,
) -> None:
    from code_scalpel.mcp.server import get_file_context

    source_file = tmp_path / "processor.js"
    source_file.write_text(
        "import { helper } from './helper.js';\n\n"
        "export function run() {\n  return helper();\n}\n\n"
        "export class Worker {}\n",
        encoding="utf-8",
    )

    result = await get_file_context(str(source_file))

    assert result.success is True
    assert result.language == "javascript"
    assert "run" in result.functions
    assert "Worker" in result.classes
    assert "./helper.js" in result.imports
    assert "Javascript module" in result.summary


async def test_get_file_context_typescript_is_bounded_useful(
    tmp_path: Path,
) -> None:
    from code_scalpel.mcp.server import get_file_context

    source_file = tmp_path / "user.ts"
    source_file.write_text(
        "export interface User {\n  name: string;\n}\n\n"
        "export function buildUser(name: string): User {\n"
        "  return { name };\n"
        "}\n",
        encoding="utf-8",
    )

    result = await get_file_context(str(source_file))

    assert result.success is True
    assert result.language == "typescript"
    assert "buildUser" in result.functions
    assert "Typescript module" in result.summary


async def test_get_file_context_java_is_bounded_useful(tmp_path: Path) -> None:
    from code_scalpel.mcp.server import get_file_context

    source_file = tmp_path / "Worker.java"
    source_file.write_text(
        "public class Worker {\n"
        "  public static void main(String[] args) {\n"
        "    run();\n"
        "  }\n\n"
        "  public static void run() {}\n"
        "}\n",
        encoding="utf-8",
    )

    result = await get_file_context(str(source_file))

    assert result.success is True
    assert result.language == "java"
    assert "Worker" in result.classes
    assert "main" in result.functions
    assert "run" in result.functions
    assert "Java module" in result.summary


async def test_get_file_context_cpp_is_bounded_useful(tmp_path: Path) -> None:
    from code_scalpel.mcp.server import get_file_context

    source_file = tmp_path / "worker.cpp"
    source_file.write_text(
        "#include <string>\n\n"
        "class Worker { public: void run() {} };\n"
        "int main() { Worker w; w.run(); return 0; }\n",
        encoding="utf-8",
    )

    result = await get_file_context(str(source_file))

    assert result.success is True
    assert result.language == "cpp"
    assert "run" in result.functions
    assert "main" in result.functions
    assert "Worker" in result.classes
    assert "string" in result.imports
    assert "Cpp module" in result.summary


async def test_get_file_context_csharp_is_bounded_useful(tmp_path: Path) -> None:
    from code_scalpel.mcp.server import get_file_context

    source_file = tmp_path / "Worker.cs"
    source_file.write_text(
        "using System;\n\n"
        "namespace Demo;\n\n"
        "public class Worker\n"
        "{\n"
        "    public static void Run() {}\n"
        "    public void Execute() {}\n"
        "}\n",
        encoding="utf-8",
    )

    result = await get_file_context(str(source_file))

    assert result.success is True
    assert result.language == "csharp"
    assert "Run" in result.functions
    assert "Execute" in result.functions
    assert "Worker" in result.classes
    assert "System" in result.imports
    assert "Csharp module" in result.summary


async def test_get_file_context_go_is_bounded_useful(tmp_path: Path) -> None:
    from code_scalpel.mcp.server import get_file_context

    source_file = tmp_path / "main.go"
    source_file.write_text(
        "package main\n\n"
        'import "fmt"\n\n'
        "func helper() {}\n"
        'func main() { helper(); fmt.Println("x") }\n',
        encoding="utf-8",
    )

    result = await get_file_context(str(source_file))

    assert result.success is True
    assert result.language == "go"
    assert "helper" in result.functions
    assert "main" in result.functions
    assert "fmt" in result.imports
    assert "Go module" in result.summary


async def test_get_file_context_kotlin_is_bounded_useful(tmp_path: Path) -> None:
    from code_scalpel.mcp.server import get_file_context

    source_file = tmp_path / "Worker.kt"
    source_file.write_text(
        "package demo\n\n"
        "import kotlin.collections.List\n\n"
        "class Worker {\n"
        "    fun run() {}\n"
        "}\n\n"
        "fun main() { Worker().run() }\n",
        encoding="utf-8",
    )

    result = await get_file_context(str(source_file))

    assert result.success is True
    assert result.language == "kotlin"
    assert "run" in result.functions
    assert "main" in result.functions
    assert "Worker" in result.classes
    assert "kotlin.collections.List" in result.imports
    assert "Kotlin module" in result.summary


async def test_get_file_context_c_is_bounded_useful(tmp_path: Path) -> None:
    from code_scalpel.mcp.server import get_file_context

    source_file = tmp_path / "math.c"
    source_file.write_text(
        "#include <stdio.h>\n\n"
        "int add(int a, int b) { return a + b; }\n"
        "int main(void) { return add(1, 2); }\n",
        encoding="utf-8",
    )

    result = await get_file_context(str(source_file))

    assert result.success is True
    assert result.language == "c"
    assert "add" in result.functions
    assert "main" in result.functions
    assert "stdio.h" in result.imports
    assert "C module" in result.summary


async def test_get_file_context_rust_is_bounded_useful(tmp_path: Path) -> None:
    from code_scalpel.mcp.server import get_file_context

    source_file = tmp_path / "lib.rs"
    source_file.write_text(
        "use std::fmt;\n\n"
        "pub fn helper() {}\n"
        "pub fn run() { helper(); }\n",
        encoding="utf-8",
    )

    result = await get_file_context(str(source_file))

    assert result.success is True
    assert result.language == "rust"
    assert "helper" in result.functions
    assert "run" in result.functions
    assert "std::fmt" in result.imports
    assert "Rust module" in result.summary


async def test_get_file_context_ruby_is_bounded_useful(tmp_path: Path) -> None:
    from code_scalpel.mcp.server import get_file_context

    source_file = tmp_path / "worker.rb"
    source_file.write_text(
        'require "json"\n\n'
        "class Worker\n"
        "  def run\n"
        "  end\n"
        "end\n",
        encoding="utf-8",
    )

    result = await get_file_context(str(source_file))

    assert result.success is True
    assert result.language == "ruby"
    assert "run" in result.functions
    assert "Worker" in result.classes
    assert "json" in result.imports
    assert "Ruby module" in result.summary


async def test_get_file_context_php_is_bounded_useful(tmp_path: Path) -> None:
    from code_scalpel.mcp.server import get_file_context

    source_file = tmp_path / "index.php"
    source_file.write_text(
        "<?php\n"
        'require_once "db.php";\n'
        "function run() { return 1; }\n"
        "class Worker {}\n",
        encoding="utf-8",
    )

    result = await get_file_context(str(source_file))

    assert result.success is True
    assert result.language == "php"
    assert "run" in result.functions
    assert "Worker" in result.classes
    assert "Php module" in result.summary


async def test_get_file_context_swift_is_bounded_useful(tmp_path: Path) -> None:
    from code_scalpel.mcp.server import get_file_context

    source_file = tmp_path / "Worker.swift"
    source_file.write_text(
        "import Foundation\n\n"
        "class Worker {\n"
        "    func run() {}\n"
        "}\n\n"
        "func main() { Worker().run() }\n",
        encoding="utf-8",
    )

    result = await get_file_context(str(source_file))

    assert result.success is True
    assert result.language == "swift"
    assert "run" in result.functions
    assert "main" in result.functions
    assert "Worker" in result.classes
    assert "Foundation" in result.imports
    assert "Swift module" in result.summary


async def test_get_file_context_unknown_extension_is_not_yet_useful(
    tmp_path: Path,
) -> None:
    from code_scalpel.mcp.server import get_file_context

    source_file = tmp_path / "sample.xyz"
    source_file.write_text("plain text\n", encoding="utf-8")

    result = await get_file_context(str(source_file))

    assert result.success is False
    assert result.language == "unknown"
    assert "Unsupported language 'unknown'" in (result.error or "")


async def test_get_file_context_routes_by_extension_for_python_code_in_javascript_file(
    tmp_path: Path,
) -> None:
    from code_scalpel.mcp.server import get_file_context

    source_file = tmp_path / "looks_like_python.js"
    source_file.write_text("def helper():\n    return 1\n", encoding="utf-8")

    result = await get_file_context(str(source_file))

    assert result.success is True
    assert result.language == "javascript"
    assert result.summary.startswith("Javascript module")


async def test_get_file_context_routes_by_extension_for_javascript_code_in_python_file(
    tmp_path: Path,
) -> None:
    from code_scalpel.mcp.server import get_file_context

    source_file = tmp_path / "looks_like_javascript.py"
    source_file.write_text("export function run() { return 1; }\n", encoding="utf-8")

    result = await get_file_context(str(source_file))

    assert result.success is False
    assert result.language == "python"
    assert result.error == "Invalid Python syntax and sanitization failed."


# [20260314_TEST] Neighborhood usefulness-contract coverage is runtime-backed
# and uses the exact canonical node-ID slice observed through the public wrapper.
async def test_get_graph_neighborhood_python_is_core_useful(
    tmp_path: Path,
) -> None:
    from code_scalpel.mcp.server import get_graph_neighborhood

    (tmp_path / "main.py").write_text(
        "def helper():\n    return 1\n\n"
        "def main():\n    return helper()\n",
        encoding="utf-8",
    )

    result = await get_graph_neighborhood(
        center_node_id="python::main::function::main",
        project_root=str(tmp_path),
        k=2,
        max_nodes=20,
    )

    assert result.success is True
    assert result.center_node_id == "python::main::function::main"
    assert "python::main::function::main" in {node.id for node in result.nodes}
    assert "python::main::function::helper" in {node.id for node in result.nodes}
    assert len(result.edges) >= 1
    assert result.mermaid.startswith("graph TD")


async def test_get_graph_neighborhood_javascript_is_bounded_useful(
    tmp_path: Path,
) -> None:
    from code_scalpel.mcp.server import get_graph_neighborhood

    (tmp_path / "helper.js").write_text(
        "export function helper() {\n  return 1;\n}\n",
        encoding="utf-8",
    )
    (tmp_path / "index.js").write_text(
        "import { helper } from './helper.js';\n"
        "export function main() {\n  return helper();\n}\n",
        encoding="utf-8",
    )

    result = await get_graph_neighborhood(
        center_node_id="javascript::index::function::main",
        project_root=str(tmp_path),
        k=2,
        max_nodes=20,
    )

    assert result.success is True
    assert result.center_node_id == "javascript::index::function::main"
    assert "javascript::index::function::main" in {node.id for node in result.nodes}
    assert len(result.edges) >= 1


async def test_get_graph_neighborhood_typescript_is_bounded_useful(
    tmp_path: Path,
) -> None:
    from code_scalpel.mcp.server import get_graph_neighborhood

    (tmp_path / "user.ts").write_text(
        "export function buildUser(name: string): string {\n"
        "  return name.toUpperCase();\n"
        "}\n\n"
        "export function run(): string {\n"
        "  return buildUser('x');\n"
        "}\n",
        encoding="utf-8",
    )

    result = await get_graph_neighborhood(
        center_node_id="typescript::user::function::run",
        project_root=str(tmp_path),
        k=2,
        max_nodes=20,
    )

    assert result.success is True
    assert result.center_node_id == "typescript::user::function::run"
    assert "typescript::user::function::run" in {node.id for node in result.nodes}
    assert "typescript::user::function::buildUser" in {node.id for node in result.nodes}
    assert len(result.edges) >= 1


async def test_get_graph_neighborhood_typescript_tracks_tsconfig_alias_imports(
    tmp_path: Path,
) -> None:
    from code_scalpel.mcp.server import get_graph_neighborhood

    (tmp_path / "tsconfig.json").write_text(
        '{"compilerOptions": {"baseUrl": ".", "paths": {"@lib/*": ["src/lib/*"]}}}',
        encoding="utf-8",
    )
    lib_dir = tmp_path / "src" / "lib"
    lib_dir.mkdir(parents=True)
    (lib_dir / "helper.ts").write_text(
        "export function helper(value: number): number {\n  return value + 1;\n}\n",
        encoding="utf-8",
    )
    (tmp_path / "src" / "main.ts").write_text(
        "import { helper } from '@lib/helper';\n\n"
        "export function run(): number {\n  return helper(1);\n}\n",
        encoding="utf-8",
    )

    result = await get_graph_neighborhood(
        center_node_id="typescript::src/main::function::run",
        project_root=str(tmp_path),
        k=2,
        max_nodes=20,
    )

    assert result.success is True
    node_ids = {node.id for node in result.nodes}
    assert "typescript::src/main::function::run" in node_ids
    assert "typescript::src/lib/helper::function::helper" in node_ids
    assert any(
        edge.from_id == "typescript::src/main::function::run"
        and edge.to_id == "typescript::src/lib/helper::function::helper"
        for edge in result.edges
    )


async def test_get_graph_neighborhood_java_is_bounded_useful(
    tmp_path: Path,
) -> None:
    from code_scalpel.mcp.server import get_graph_neighborhood

    demo = tmp_path / "demo"
    demo.mkdir()
    (demo / "App.java").write_text(
        "package demo;\n\n"
        "public class App {\n"
        "  public static void main(String[] args) {\n"
        "    helper();\n"
        "  }\n\n"
        "  private static void helper() {}\n"
        "}\n",
        encoding="utf-8",
    )

    result = await get_graph_neighborhood(
        center_node_id="java::demo/App::method::App:main",
        project_root=str(tmp_path),
        k=2,
        max_nodes=20,
    )

    assert result.success is True
    assert result.center_node_id == "java::demo/App::method::App:main"
    assert "java::demo/App::method::App:main" in {node.id for node in result.nodes}
    assert result.total_nodes >= 1


async def test_get_graph_neighborhood_go_is_bounded_useful(tmp_path: Path) -> None:
    from code_scalpel.mcp.server import get_graph_neighborhood

    cmd = tmp_path / "cmd"
    cmd.mkdir()
    (cmd / "main.go").write_text(
        "package main\n\n"
        "func helper() {}\n"
        "func main() { helper() }\n",
        encoding="utf-8",
    )

    result = await get_graph_neighborhood(
        center_node_id="go::cmd/main::function::main",
        project_root=str(tmp_path),
        k=2,
        max_nodes=20,
    )

    assert result.success is True
    assert result.center_node_id == "go::cmd/main::function::main"
    assert "go::cmd/main::function::main" in {node.id for node in result.nodes}
    assert "go::cmd/main::function::helper" in {node.id for node in result.nodes}
    assert len(result.edges) >= 1


async def test_get_graph_neighborhood_extensionful_javascript_id_is_rejected(
    tmp_path: Path,
) -> None:
    from code_scalpel.mcp.server import get_graph_neighborhood

    (tmp_path / "index.js").write_text(
        "export function main() {\n  return 1;\n}\n",
        encoding="utf-8",
    )

    result = await get_graph_neighborhood(
        center_node_id="javascript::index.js::function::main",
        project_root=str(tmp_path),
        k=2,
        max_nodes=20,
    )

    assert result.success is False
    assert result.error is not None
    assert "Center node not found" in str(result.error)