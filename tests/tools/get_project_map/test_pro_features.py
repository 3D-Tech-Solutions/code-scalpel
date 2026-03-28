"""Pro feature tests for get_project_map.

Validates Pro tier features:
- Coupling analysis (fan-in, fan-out metrics)
- Code ownership mapping (git blame integration)
- Architectural layer detection
- Module relationship visualization

[20260103_TEST] v3.3.1 - Pro tier feature validation
"""

import pytest


class TestProFeatureCoupling:
    """Test Pro tier coupling analysis features."""

    @pytest.mark.asyncio
    async def test_coupling_metrics_accessible(self, pro_server, flask_project):
        """Pro tier: coupling_metrics field accessible."""
        result = await pro_server.get_project_map(
            project_root=str(flask_project), include_complexity=True
        )

        result_dict = (
            result.model_dump() if hasattr(result, "model_dump") else vars(result)
        )

        # coupling_metrics should exist in Pro tier model
        assert (
            "coupling_metrics" in result_dict
        ), f"Pro tier missing coupling_metrics. Available: {list(result_dict.keys())}"

    @pytest.mark.asyncio
    async def test_community_no_coupling_metrics(self, community_server, flask_project):
        """Community tier: coupling_metrics not populated."""
        result = await community_server.get_project_map(
            project_root=str(flask_project), include_complexity=True
        )

        result_dict = (
            result.model_dump() if hasattr(result, "model_dump") else vars(result)
        )

        # If field exists, it should be empty
        if "coupling_metrics" in result_dict:
            value = result_dict["coupling_metrics"]
            assert value in [
                None,
                {},
                [],
            ], f"Community should not have coupling_metrics data, got: {value}"


class TestProFeatureOwnership:
    """Test Pro tier code ownership mapping features."""

    @pytest.mark.asyncio
    async def test_git_ownership_accessible(self, pro_server, simple_project):
        """Pro tier: git_ownership field accessible."""
        result = await pro_server.get_project_map(
            project_root=str(simple_project), include_complexity=False
        )

        result_dict = (
            result.model_dump() if hasattr(result, "model_dump") else vars(result)
        )

        # git_ownership should exist in Pro tier model
        assert (
            "git_ownership" in result_dict
        ), f"Pro tier missing git_ownership. Available: {list(result_dict.keys())}"

    @pytest.mark.asyncio
    async def test_community_no_git_ownership(self, community_server, simple_project):
        """Community tier: git_ownership not populated."""
        result = await community_server.get_project_map(
            project_root=str(simple_project), include_complexity=False
        )

        result_dict = (
            result.model_dump() if hasattr(result, "model_dump") else vars(result)
        )

        # If field exists, it should be empty
        if "git_ownership" in result_dict:
            value = result_dict["git_ownership"]
            assert value in [
                None,
                {},
                [],
            ], f"Community should not have git_ownership data, got: {value}"


class TestProFeatureArchitecturalLayers:
    """Test Pro tier architectural layer detection."""

    @pytest.mark.asyncio
    async def test_architectural_layers_accessible(self, pro_server, flask_project):
        """Pro tier: architectural_layers field accessible."""
        result = await pro_server.get_project_map(
            project_root=str(flask_project), include_complexity=False
        )

        result_dict = (
            result.model_dump() if hasattr(result, "model_dump") else vars(result)
        )

        # architectural_layers should exist in Pro tier model
        assert (
            "architectural_layers" in result_dict
        ), f"Pro tier missing architectural_layers. Available: {list(result_dict.keys())}"

    @pytest.mark.asyncio
    async def test_flask_layer_detection(self, pro_server, flask_project):
        """Pro tier: Detect Flask architectural layers (presentation, business, data)."""
        result = await pro_server.get_project_map(
            project_root=str(flask_project), include_complexity=False
        )

        result_dict = (
            result.model_dump() if hasattr(result, "model_dump") else vars(result)
        )

        # For Flask project, architectural_layers might detect layers
        # This is a capability test - field should exist even if detection varies
        assert (
            "architectural_layers" in result_dict
        ), "Pro tier should have architectural_layers field for Flask project"

    @pytest.mark.asyncio
    async def test_community_no_architectural_layers(
        self, community_server, flask_project
    ):
        """Community tier: architectural_layers not populated."""
        result = await community_server.get_project_map(
            project_root=str(flask_project), include_complexity=False
        )

        result_dict = (
            result.model_dump() if hasattr(result, "model_dump") else vars(result)
        )

        # If field exists, it should be empty
        if "architectural_layers" in result_dict:
            value = result_dict["architectural_layers"]
            assert value in [
                None,
                {},
                [],
            ], f"Community should not have architectural_layers data, got: {value}"


class TestProFeatureModuleRelationships:
    """Test Pro tier module relationship visualization."""

    @pytest.mark.asyncio
    async def test_module_relationships_accessible(self, pro_server, simple_project):
        """Pro tier: module_relationships field accessible."""
        result = await pro_server.get_project_map(
            project_root=str(simple_project), include_complexity=False
        )

        result_dict = (
            result.model_dump() if hasattr(result, "model_dump") else vars(result)
        )

        # module_relationships should exist in Pro tier model
        assert (
            "module_relationships" in result_dict
        ), f"Pro tier missing module_relationships. Available: {list(result_dict.keys())}"

    @pytest.mark.asyncio
    async def test_dependency_diagram_accessible(self, pro_server, flask_project):
        """Pro tier: dependency_diagram field accessible."""
        result = await pro_server.get_project_map(
            project_root=str(flask_project), include_complexity=False
        )

        result_dict = (
            result.model_dump() if hasattr(result, "model_dump") else vars(result)
        )

        # dependency_diagram should exist in Pro tier model
        assert (
            "dependency_diagram" in result_dict
        ), f"Pro tier missing dependency_diagram. Available: {list(result_dict.keys())}"

    @pytest.mark.asyncio
    async def test_community_no_module_relationships(
        self, community_server, simple_project
    ):
        """Community tier: module_relationships not populated."""
        result = await community_server.get_project_map(
            project_root=str(simple_project), include_complexity=False
        )

        result_dict = (
            result.model_dump() if hasattr(result, "model_dump") else vars(result)
        )

        # If field exists, it should be empty
        if "module_relationships" in result_dict:
            value = result_dict["module_relationships"]
            assert value in [
                None,
                {},
                [],
            ], f"Community should not have module_relationships data, got: {value}"

    @pytest.mark.asyncio
    async def test_pro_typescript_module_relationships(self, pro_server, tmp_path):
        """[20260307_TEST] Pro tier should build module relationships for a local TS import edge."""
        root = tmp_path / "ts_project_map"
        src = root / "src"
        src.mkdir(parents=True)

        (src / "util.ts").write_text(
            "export function helper(): number {\n    return 1\n}\n",
            encoding="utf-8",
        )
        (src / "main.ts").write_text(
            'import { helper } from "./util"\n\n'
            "export function entry(): number {\n    return helper()\n}\n",
            encoding="utf-8",
        )

        result = await pro_server.get_project_map(
            project_root=str(root), include_complexity=True
        )

        assert result.success is True
        assert result.total_files == 2
        assert result.languages.get("typescript") == 2

        modules = {module.path: module for module in result.modules}
        assert "src/main.ts" in modules
        assert "src/util.ts" in modules
        assert "entry" in modules["src/main.ts"].functions
        assert "helper" in modules["src/util.ts"].functions

        result_dict = (
            result.model_dump() if hasattr(result, "model_dump") else vars(result)
        )
        relationships = result_dict.get("module_relationships") or []
        assert any(
            rel.get("source") == "src/main.ts" and rel.get("target") == "src/util.ts"
            for rel in relationships
        )

    @pytest.mark.asyncio
    async def test_pro_javascript_module_relationships(self, pro_server, tmp_path):
        """[20260308_TEST] Pro tier should build module relationships for a local JS import edge."""
        root = tmp_path / "js_project_map"
        src = root / "src"
        src.mkdir(parents=True)

        (src / "util.js").write_text(
            "export function helper() {\n    return 1\n}\n",
            encoding="utf-8",
        )
        (src / "main.js").write_text(
            'import { helper } from "./util"\n\n'
            "export function entry() {\n    return helper()\n}\n",
            encoding="utf-8",
        )

        result = await pro_server.get_project_map(
            project_root=str(root), include_complexity=True
        )

        assert result.success is True
        assert result.total_files == 2
        assert result.languages.get("javascript") == 2

        modules = {module.path: module for module in result.modules}
        assert "src/main.js" in modules
        assert "src/util.js" in modules
        assert "entry" in modules["src/main.js"].functions
        assert "helper" in modules["src/util.js"].functions

        result_dict = (
            result.model_dump() if hasattr(result, "model_dump") else vars(result)
        )
        relationships = result_dict.get("module_relationships") or []
        assert any(
            rel.get("source") == "src/main.js" and rel.get("target") == "src/util.js"
            for rel in relationships
        )

    @pytest.mark.asyncio
    async def test_pro_typescript_dependency_diagram(self, pro_server, tmp_path):
        """[20260307_TEST] Pro tier dependency diagram should include the local TS edge."""
        root = tmp_path / "ts_project_diagram"
        src = root / "src"
        src.mkdir(parents=True)

        (src / "util.ts").write_text(
            "export function helper(): number {\n    return 1\n}\n",
            encoding="utf-8",
        )
        (src / "main.ts").write_text(
            'import { helper } from "./util"\n\n'
            "export function entry(): number {\n    return helper()\n}\n",
            encoding="utf-8",
        )

        result = await pro_server.get_project_map(
            project_root=str(root), include_complexity=False
        )

        result_dict = (
            result.model_dump() if hasattr(result, "model_dump") else vars(result)
        )
        dependency_diagram = result_dict.get("dependency_diagram") or ""

        assert "graph TD" in dependency_diagram
        assert "src_main_ts" in dependency_diagram
        assert "src_util_ts" in dependency_diagram
        assert "-->" in dependency_diagram

    @pytest.mark.asyncio
    async def test_pro_typescript_tsconfig_alias_relationships(
        self, pro_server, tmp_path
    ):
        """[20260314_TEST] Pro tier should resolve tsconfig path aliases into TypeScript module relationships."""
        root = tmp_path / "ts_project_aliases"
        src = root / "src"
        ui = src / "ui"
        ui.mkdir(parents=True)

        (root / "tsconfig.json").write_text(
            '{\n'
            '  "compilerOptions": {\n'
            '    "baseUrl": ".",\n'
            '    "paths": {\n'
            '      "@ui/*": ["src/ui/*"]\n'
            '    }\n'
            '  }\n'
            '}\n',
            encoding="utf-8",
        )
        (ui / "button.ts").write_text(
            "export function renderButton(): string {\n"
            '    return "button"\n'
            "}\n",
            encoding="utf-8",
        )
        (src / "main.ts").write_text(
            'import { renderButton } from "@ui/button"\n\n'
            "export function run(): string {\n"
            "    return renderButton()\n"
            "}\n",
            encoding="utf-8",
        )

        result = await pro_server.get_project_map(
            project_root=str(root), include_complexity=False
        )

        assert result.success is True
        assert result.languages.get("typescript") == 2

        result_dict = (
            result.model_dump() if hasattr(result, "model_dump") else vars(result)
        )
        relationships = result_dict.get("module_relationships") or []
        assert any(
            rel.get("source") == "src/main.ts"
            and rel.get("target") == "src/ui/button.ts"
            for rel in relationships
        )

        dependency_diagram = result_dict.get("dependency_diagram") or ""
        assert "graph TD" in dependency_diagram
        assert "src_main_ts" in dependency_diagram
        assert "src_ui_button_ts" in dependency_diagram
        assert "-->" in dependency_diagram

    @pytest.mark.asyncio
    async def test_pro_javascript_dependency_diagram(self, pro_server, tmp_path):
        """[20260308_TEST] Pro tier dependency diagram should include the local JS edge."""
        root = tmp_path / "js_project_diagram"
        src = root / "src"
        src.mkdir(parents=True)

        (src / "util.js").write_text(
            "export function helper() {\n    return 1\n}\n",
            encoding="utf-8",
        )
        (src / "main.js").write_text(
            'import { helper } from "./util"\n\n'
            "export function entry() {\n    return helper()\n}\n",
            encoding="utf-8",
        )

        result = await pro_server.get_project_map(
            project_root=str(root), include_complexity=False
        )

        result_dict = (
            result.model_dump() if hasattr(result, "model_dump") else vars(result)
        )
        dependency_diagram = result_dict.get("dependency_diagram") or ""

        assert "graph TD" in dependency_diagram
        assert "src_main_js" in dependency_diagram
        assert "src_util_js" in dependency_diagram
        assert "-->" in dependency_diagram

    @pytest.mark.asyncio
    async def test_pro_java_module_relationships_and_diagram(
        self, pro_server, tmp_path
    ):
        """[20260308_TEST] Pro tier should build Java module relationships for explicit imports."""
        root = tmp_path / "java_project_map"
        package_dir = root / "demo"
        package_dir.mkdir(parents=True)

        (package_dir / "Helper.java").write_text(
            "package demo;\n\n"
            "public class Helper {\n"
            "    public static void tool() {\n"
            "    }\n"
            "}\n",
            encoding="utf-8",
        )
        (package_dir / "App.java").write_text(
            "package demo;\n\n"
            "import static demo.Helper.tool;\n\n"
            "public class App {\n"
            "    public static void entry() {\n"
            "        tool();\n"
            "    }\n"
            "}\n",
            encoding="utf-8",
        )

        result = await pro_server.get_project_map(
            project_root=str(root), include_complexity=False
        )

        assert result.success is True
        assert result.total_files == 2
        assert result.languages.get("java") == 2

        modules = {module.path: module for module in result.modules}
        assert "demo/App.java" in modules
        assert "demo/Helper.java" in modules
        assert "App.entry" in modules["demo/App.java"].functions
        assert "Helper.tool" in modules["demo/Helper.java"].functions

        result_dict = (
            result.model_dump() if hasattr(result, "model_dump") else vars(result)
        )
        relationships = result_dict.get("module_relationships") or []
        assert any(
            rel.get("source") == "demo/App.java"
            and rel.get("target") == "demo/Helper.java"
            for rel in relationships
        )

        dependency_diagram = result_dict.get("dependency_diagram") or ""
        assert "graph TD" in dependency_diagram
        assert "demo_App_java" in dependency_diagram
        assert "demo_Helper_java" in dependency_diagram
        assert "-->" in dependency_diagram

    @pytest.mark.asyncio
    async def test_pro_java_package_imports_and_main_entrypoint(
        self, pro_server, tmp_path
    ):
        """[20260308_TEST] Pro tier should resolve Java package imports and expose main entry points."""
        root = tmp_path / "java_project_map_packages"
        app_dir = root / "demo"
        util_dir = app_dir / "util"
        util_dir.mkdir(parents=True)

        (util_dir / "Helper.java").write_text(
            "package demo.util;\n\n"
            "public class Helper {\n"
            "    public static int tool() {\n"
            "        return 1;\n"
            "    }\n"
            "}\n",
            encoding="utf-8",
        )
        (app_dir / "App.java").write_text(
            "package demo;\n\n"
            "import demo.util.Helper;\n\n"
            "public class App {\n"
            "    public static void main(String[] args) {\n"
            "        Helper.tool();\n"
            "    }\n"
            "}\n",
            encoding="utf-8",
        )

        result = await pro_server.get_project_map(
            project_root=str(root), include_complexity=False
        )

        assert result.success is True
        assert result.total_files == 2
        assert result.languages.get("java") == 2

        modules = {module.path: module for module in result.modules}
        assert "demo/App.java" in modules
        assert "demo/util/Helper.java" in modules
        assert "App.main" in modules["demo/App.java"].functions
        assert "Helper.tool" in modules["demo/util/Helper.java"].functions
        assert "demo/App.java:App.main" in result.entry_points

        result_dict = (
            result.model_dump() if hasattr(result, "model_dump") else vars(result)
        )
        relationships = result_dict.get("module_relationships") or []
        assert any(
            rel.get("source") == "demo/App.java"
            and rel.get("target") == "demo/util/Helper.java"
            for rel in relationships
        )

        dependency_diagram = result_dict.get("dependency_diagram") or ""
        assert "graph TD" in dependency_diagram
        assert "demo_App_java" in dependency_diagram
        assert "demo_util_Helper_java" in dependency_diagram
        assert "-->" in dependency_diagram

    @pytest.mark.asyncio
    async def test_pro_java_wildcard_import_relationships(self, pro_server, tmp_path):
        """[20260314_TEST] Pro tier should expand Java wildcard package imports into module relationships."""
        root = tmp_path / "java_project_map_wildcard"
        app_dir = root / "demo"
        util_dir = app_dir / "util"
        util_dir.mkdir(parents=True)

        (util_dir / "Helper.java").write_text(
            "package demo.util;\n\n"
            "public class Helper {\n"
            "    public static int tool() {\n"
            "        return 1;\n"
            "    }\n"
            "}\n",
            encoding="utf-8",
        )
        (app_dir / "App.java").write_text(
            "package demo;\n\n"
            "import demo.util.*;\n\n"
            "public class App {\n"
            "    public static int entry() {\n"
            "        return Helper.tool();\n"
            "    }\n"
            "}\n",
            encoding="utf-8",
        )

        result = await pro_server.get_project_map(
            project_root=str(root), include_complexity=False
        )

        result_dict = (
            result.model_dump() if hasattr(result, "model_dump") else vars(result)
        )
        relationships = result_dict.get("module_relationships") or []

        assert any(
            rel.get("source") == "demo/App.java"
            and rel.get("target") == "demo/util/Helper.java"
            for rel in relationships
        )

    @pytest.mark.asyncio
    async def test_pro_java_same_package_type_relationships(self, pro_server, tmp_path):
        """[20260314_TEST] Pro tier should resolve same-package Java type references without explicit imports."""
        root = tmp_path / "java_project_map_same_package"
        package_dir = root / "demo"
        package_dir.mkdir(parents=True)

        (package_dir / "BaseWorker.java").write_text(
            "package demo;\n\n"
            "public class BaseWorker {\n"
            "}\n",
            encoding="utf-8",
        )
        (package_dir / "Worker.java").write_text(
            "package demo;\n\n"
            "public class Worker extends BaseWorker {\n"
            "    public static void entry() {\n"
            "    }\n"
            "}\n",
            encoding="utf-8",
        )

        result = await pro_server.get_project_map(
            project_root=str(root), include_complexity=False
        )

        result_dict = (
            result.model_dump() if hasattr(result, "model_dump") else vars(result)
        )
        relationships = result_dict.get("module_relationships") or []

        assert any(
            rel.get("source") == "demo/Worker.java"
            and rel.get("target") == "demo/BaseWorker.java"
            for rel in relationships
        )
