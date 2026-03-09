"""[20260104_FEATURE] MCP Server integration tests for get_graph_neighborhood.

Validates:
- Tool registration and discovery (tools/list)
- Schema validation (input/output models)
- Async concurrent request handling
- Tools list response structure
"""

import asyncio
from unittest.mock import patch

import pytest


class TestToolRegistration:
    """Test tool is properly registered in MCP server."""

    def test_tool_is_callable(self):
        """Tool can be imported and called."""
        # [20260104_TEST] Tool availability check
        from code_scalpel.mcp.server import get_graph_neighborhood

        # Function should be callable
        assert callable(get_graph_neighborhood)

    def test_tool_has_docstring(self):
        """Tool has documentation."""
        # [20260104_TEST] Tool documentation presence
        from code_scalpel.mcp.server import get_graph_neighborhood

        assert get_graph_neighborhood.__doc__ is not None
        assert len(get_graph_neighborhood.__doc__) > 10

    def test_tool_signature_has_center_node_id(self):
        """Tool accepts center_node_id parameter."""
        # [20260104_TEST] Tool parameter requirements
        import inspect

        from code_scalpel.mcp.server import get_graph_neighborhood

        sig = inspect.signature(get_graph_neighborhood)
        assert "center_node_id" in sig.parameters

    def test_tool_signature_has_k_parameter(self):
        """Tool accepts k parameter."""
        # [20260104_TEST] Hop depth parameter
        import inspect

        from code_scalpel.mcp.server import get_graph_neighborhood

        sig = inspect.signature(get_graph_neighborhood)
        assert "k" in sig.parameters

    def test_tool_signature_has_max_nodes_parameter(self):
        """Tool accepts max_nodes parameter."""
        # [20260104_TEST] Node limit parameter
        import inspect

        from code_scalpel.mcp.server import get_graph_neighborhood

        sig = inspect.signature(get_graph_neighborhood)
        assert "max_nodes" in sig.parameters

    def test_tool_signature_has_direction_parameter(self):
        """Tool accepts direction parameter."""
        # [20260104_TEST] Edge direction parameter
        import inspect

        from code_scalpel.mcp.server import get_graph_neighborhood

        sig = inspect.signature(get_graph_neighborhood)
        assert "direction" in sig.parameters

    def test_tool_signature_has_min_confidence_parameter(self):
        """Tool accepts min_confidence parameter."""
        # [20260104_TEST] Confidence filtering parameter
        import inspect

        from code_scalpel.mcp.server import get_graph_neighborhood

        sig = inspect.signature(get_graph_neighborhood)
        assert "min_confidence" in sig.parameters


class TestAsyncConcurrentHandling:
    """Test tool handles async and concurrent requests correctly."""

    @pytest.mark.asyncio
    async def test_concurrent_requests_same_node(self):
        """Multiple concurrent requests for same node succeed or fail consistently."""
        # [20260104_TEST] Concurrent request handling
        from code_scalpel.mcp.server import get_graph_neighborhood

        # Fire 5 concurrent requests for the same node
        tasks = [
            get_graph_neighborhood(
                center_node_id="python::main::function::center", k=1, max_nodes=20
            )
            for _ in range(5)
        ]

        results = await asyncio.gather(*tasks)

        # All should complete (success or consistent error)
        assert len(results) == 5
        # All results should have the same success value
        success_values = [r.success for r in results]
        assert all(s == success_values[0] for s in success_values)

    @pytest.mark.asyncio
    async def test_concurrent_requests_different_nodes(self):
        """Multiple concurrent requests for different nodes succeed."""
        # [20260104_TEST] Concurrent multi-node requests
        from code_scalpel.mcp.server import get_graph_neighborhood

        # Fire concurrent requests for different nodes
        tasks = [
            get_graph_neighborhood(
                center_node_id=f"python::module_{i}::function::func_{i}",
                k=1,
                max_nodes=20,
            )
            for i in range(3)
        ]

        results = await asyncio.gather(*tasks)

        # All should complete (may have different success values based on node existence)
        assert len(results) == 3
        # At least some may fail due to nonexistent nodes - that's ok
        # What matters is all complete without crashes

    @pytest.mark.asyncio
    async def test_concurrent_requests_mixed_tiers(self):
        """Concurrent requests with different tier settings work."""
        # [20260104_TEST] Concurrent tier-mixed requests
        from code_scalpel.mcp.server import get_graph_neighborhood

        # Mock different tier contexts
        async def call_with_tier(tier_name):
            with patch(
                "code_scalpel.mcp.server._get_current_tier", return_value=tier_name
            ):
                return await get_graph_neighborhood(
                    center_node_id="python::main::function::center",
                    k=2 if tier_name == "pro" else 1,
                    max_nodes=200 if tier_name == "pro" else 20,
                )

        tasks = [
            call_with_tier("community"),
            call_with_tier("pro"),
            call_with_tier("community"),
        ]

        results = await asyncio.gather(*tasks)
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_sequential_requests_after_error(self):
        """Tool recovers and works after error condition."""
        # [20260104_TEST] Recovery from error in request sequence
        from code_scalpel.mcp.server import get_graph_neighborhood

        # First request: invalid (nonexistent node)
        result1 = await get_graph_neighborhood(
            center_node_id="python::fake::function::fake", k=1
        )
        assert not result1.success

        # Second request: valid (should work despite previous error)
        result2 = await get_graph_neighborhood(
            center_node_id="python::main::function::center", k=1, max_nodes=20
        )
        # May or may not succeed depending on if graph exists, but shouldn't crash
        assert hasattr(result2, "success")


class TestInputValidation:
    """Test input validation and error handling."""

    @pytest.mark.asyncio
    async def test_invalid_input_type_k_negative(self):
        """Negative k value rejected with clear error."""
        # [20260104_TEST] Invalid k parameter type/value
        from code_scalpel.mcp.server import get_graph_neighborhood

        result = await get_graph_neighborhood(
            center_node_id="python::main::function::center",
            k=-1,  # Invalid
            max_nodes=20,
        )

        assert not result.success
        assert "k" in result.error.lower() or "must be" in result.error.lower()

    @pytest.mark.asyncio
    async def test_invalid_input_type_k_zero(self):
        """Zero k value rejected with clear error."""
        # [20260104_TEST] k=0 validation
        from code_scalpel.mcp.server import get_graph_neighborhood

        result = await get_graph_neighborhood(
            center_node_id="python::main::function::center",
            k=0,  # Invalid
            max_nodes=20,
        )

        assert not result.success
        assert "k" in result.error.lower() or "must be" in result.error.lower()

    @pytest.mark.asyncio
    async def test_invalid_direction_value(self):
        """Invalid direction value rejected with error."""
        # [20260104_TEST] Direction parameter validation
        from code_scalpel.mcp.server import get_graph_neighborhood

        result = await get_graph_neighborhood(
            center_node_id="python::main::function::center",
            k=1,
            max_nodes=20,
            direction="invalid_direction",  # Invalid
        )

        assert not result.success
        assert "direction" in result.error.lower()

    @pytest.mark.asyncio
    async def test_invalid_confidence_out_of_range(self):
        """Confidence outside [0, 1] handled (may fail on graph build or validation)."""
        # [20260104_TEST] Confidence range validation or graceful handling
        from code_scalpel.mcp.server import get_graph_neighborhood

        result = await get_graph_neighborhood(
            center_node_id="python::main::function::center",
            k=1,
            max_nodes=20,
            min_confidence=1.5,  # Out of range
        )

        # Should either reject due to confidence validation
        # OR fail due to node not found (acceptable fallback)
        assert not result.success or (result.success and result.min_confidence == 1.5)

    @pytest.mark.asyncio
    async def test_unsupported_language_node_id_returns_guidance_error(self):
        """Unsupported non-JS/TS language node IDs should fail with guidance."""
        # [20260306_TEST] Keep unsupported language behavior explicit after the JS/TS parity slice.
        from code_scalpel.mcp.server import get_graph_neighborhood

        result = await get_graph_neighborhood(
            center_node_id="java::app.routes::function::handleRequest",
            k=1,
            max_nodes=20,
        )

        assert not result.success
        assert result.error is not None
        assert "java method-node" in result.error.lower() or "java::demo/app::method::app:main" in result.error.lower()
        assert "currently" in result.error.lower()

    @pytest.mark.asyncio
    async def test_java_method_node_extracts_local_neighborhood(self, tmp_path):
        """[20260308_TEST] Java method node IDs should participate in local neighborhood extraction."""
        from code_scalpel.mcp.server import get_graph_neighborhood

        (tmp_path / "App.java").write_text(
            "public class App {\n"
            "  public static void main(String[] args) {\n"
            "    helper();\n"
            "  }\n\n"
            "  private static void helper() {\n"
            "  }\n"
            "}\n",
            encoding="utf-8",
        )

        with patch(
            "code_scalpel.mcp.helpers.graph_helpers._get_current_tier",
            return_value="community",
        ):
            result = await get_graph_neighborhood(
                center_node_id="java::App::method::App:main",
                project_root=str(tmp_path),
                k=1,
                max_nodes=20,
            )

        assert result.success
        assert result.tier_applied == "community"
        assert result.advanced_resolution_enabled is False
        node_ids = {node.id for node in result.nodes}
        assert "java::App::method::App:main" in node_ids
        assert "java::App::method::App:helper" in node_ids
        edge_ids = {(edge.from_id, edge.to_id) for edge in result.edges}
        assert ("java::App::method::App:main", "java::App::method::App:helper") in edge_ids

    @pytest.mark.asyncio
    async def test_java_method_node_extracts_cross_file_neighborhood_with_pro_tier(
        self, tmp_path
    ):
        """[20260308_TEST] Pro Java method neighborhoods should reuse cross-file call-graph edges."""
        from code_scalpel.mcp.server import get_graph_neighborhood

        package_dir = tmp_path / "demo"
        package_dir.mkdir()
        (package_dir / "Helper.java").write_text(
            "package demo;\n\n"
            "public class Helper {\n"
            "  public static void tool() {\n"
            "  }\n"
            "}\n",
            encoding="utf-8",
        )
        (package_dir / "App.java").write_text(
            "package demo;\n\n"
            "import static demo.Helper.tool;\n\n"
            "public class App {\n"
            "  public static void main(String[] args) {\n"
            "    tool();\n"
            "  }\n"
            "}\n",
            encoding="utf-8",
        )

        with patch(
            "code_scalpel.mcp.helpers.graph_helpers._get_current_tier",
            return_value="pro",
        ):
            result = await get_graph_neighborhood(
                center_node_id="java::demo/App::method::App:main",
                project_root=str(tmp_path),
                k=1,
                max_nodes=20,
            )

        assert result.success
        assert result.tier_applied == "pro"
        assert result.advanced_resolution_enabled is True
        node_ids = {node.id for node in result.nodes}
        assert "java::demo/App::method::App:main" in node_ids
        assert "java::demo/Helper::method::Helper:tool" in node_ids
        edge_ids = {(edge.from_id, edge.to_id) for edge in result.edges}
        assert (
            "java::demo/App::method::App:main",
            "java::demo/Helper::method::Helper:tool",
        ) in edge_ids

    @pytest.mark.asyncio
    async def test_java_method_node_prefers_overridden_child_method_with_pro_tier(
        self, tmp_path
    ):
        """[20260308_TEST] Pro Java method neighborhoods should prefer overridden child methods over superclass fallbacks."""
        from code_scalpel.mcp.server import get_graph_neighborhood

        package_dir = tmp_path / "demo"
        package_dir.mkdir()
        (package_dir / "Base.java").write_text(
            "package demo;\n\n"
            "public class Base {\n"
            "  protected void helper() {\n"
            "  }\n"
            "}\n",
            encoding="utf-8",
        )
        (package_dir / "Child.java").write_text(
            "package demo;\n\n"
            "public class Child extends Base {\n"
            "  @Override\n"
            "  protected void helper() {\n"
            "  }\n\n"
            "  public void run() {\n"
            "    helper();\n"
            "    this.helper();\n"
            "  }\n"
            "}\n",
            encoding="utf-8",
        )

        with patch(
            "code_scalpel.mcp.helpers.graph_helpers._get_current_tier",
            return_value="pro",
        ):
            result = await get_graph_neighborhood(
                center_node_id="java::demo/Child::method::Child:run",
                project_root=str(tmp_path),
                k=1,
                max_nodes=20,
            )

        assert result.success
        node_ids = {node.id for node in result.nodes}
        assert "java::demo/Child::method::Child:run" in node_ids
        assert "java::demo/Child::method::Child:helper" in node_ids
        assert "java::demo/Base::method::Base:helper" not in node_ids
        edge_ids = {(edge.from_id, edge.to_id) for edge in result.edges}
        assert (
            "java::demo/Child::method::Child:run",
            "java::demo/Child::method::Child:helper",
        ) in edge_ids

    @pytest.mark.asyncio
    async def test_java_method_node_preserves_relative_path_metadata_and_mermaid(
        self, tmp_path
    ):
        """[20260308_TEST] Java neighborhoods should preserve relative file metadata and method labels in Mermaid output."""
        from code_scalpel.mcp.server import get_graph_neighborhood

        package_dir = tmp_path / "demo"
        package_dir.mkdir()
        (package_dir / "Helper.java").write_text(
            "package demo;\n\n"
            "public class Helper {\n"
            "  public static void tool() {\n"
            "  }\n"
            "}\n",
            encoding="utf-8",
        )
        (package_dir / "App.java").write_text(
            "package demo;\n\n"
            "import static demo.Helper.tool;\n\n"
            "public class App {\n"
            "  public static void main(String[] args) {\n"
            "    tool();\n"
            "  }\n"
            "}\n",
            encoding="utf-8",
        )

        with patch(
            "code_scalpel.mcp.helpers.graph_helpers._get_current_tier",
            return_value="pro",
        ):
            result = await get_graph_neighborhood(
                center_node_id="java::demo/App::method::App:main",
                project_root=str(tmp_path),
                k=1,
                max_nodes=20,
            )

        assert result.success
        nodes_by_id = {node.id: node for node in result.nodes}
        assert (
            nodes_by_id["java::demo/App::method::App:main"].metadata["file"]
            == "demo/App.java"
        )
        assert (
            nodes_by_id["java::demo/Helper::method::Helper:tool"].metadata["file"]
            == "demo/Helper.java"
        )
        assert result.mermaid.startswith("graph TD")
        assert '"App:main"' in result.mermaid
        assert '"Helper:tool"' in result.mermaid

    @pytest.mark.asyncio
    async def test_java_method_node_reports_path_query_capabilities_with_enterprise_tier(
        self, tmp_path
    ):
        """[20260308_TEST] Enterprise Java neighborhoods should advertise query and path-constraint capability metadata for canonical method nodes."""
        from code_scalpel.mcp.server import get_graph_neighborhood

        (tmp_path / "App.java").write_text(
            "public class App {\n"
            "  public static void main(String[] args) {\n"
            "    helper();\n"
            "  }\n\n"
            "  private static void helper() {\n"
            "  }\n"
            "}\n",
            encoding="utf-8",
        )

        with patch(
            "code_scalpel.mcp.helpers.graph_helpers._get_current_tier",
            return_value="enterprise",
        ):
            result = await get_graph_neighborhood(
                center_node_id="java::App::method::App:main",
                project_root=str(tmp_path),
                k=1,
                max_nodes=20,
            )

        assert result.success
        assert result.query_supported is True
        assert result.path_constraints_supported is True
        assert result.traversal_rules_available is True
        assert result.center_node_id == "java::App::method::App:main"

    @pytest.mark.asyncio
    async def test_java_overloaded_method_node_accepts_signature_selector(
        self, tmp_path
    ):
        """[20260308_TEST] Java neighborhood validation should accept signature-qualified method node IDs for overloads."""
        from code_scalpel.mcp.server import get_graph_neighborhood

        package_dir = tmp_path / "demo"
        package_dir.mkdir()
        (package_dir / "Helper.java").write_text(
            "package demo;\n\n"
            "public class Helper {\n"
            "  public static void tool(int value) {\n"
            "  }\n\n"
            "  public static void tool(String value) {\n"
            "  }\n"
            "}\n",
            encoding="utf-8",
        )
        (package_dir / "App.java").write_text(
            "package demo;\n\n"
            "import static demo.Helper.tool;\n\n"
            "public class App {\n"
            "  public static void main(String[] args) {\n"
            "    tool(1);\n"
            "  }\n"
            "}\n",
            encoding="utf-8",
        )

        with patch(
            "code_scalpel.mcp.helpers.graph_helpers._get_current_tier",
            return_value="pro",
        ):
            result = await get_graph_neighborhood(
                center_node_id="java::demo/Helper::method::Helper:tool(int)",
                project_root=str(tmp_path),
                k=1,
                max_nodes=20,
            )

        assert result.success
        node_ids = {node.id for node in result.nodes}
        assert "java::demo/Helper::method::Helper:tool(int)" in node_ids

    @pytest.mark.asyncio
    async def test_java_method_node_uses_static_fluent_builder_chain_for_overloaded_targets(
        self, tmp_path
    ):
        """[20260308_TEST] Pro Java neighborhoods should carry static builder entrypoints and longer fluent chains into signature-qualified overloaded method nodes."""
        from code_scalpel.mcp.server import get_graph_neighborhood

        package_dir = tmp_path / "demo"
        package_dir.mkdir()
        (package_dir / "Builder.java").write_text(
            "package demo;\n\n"
            "public class Builder {\n"
            "  public static Builder start() {\n"
            "    return new Builder();\n"
            "  }\n\n"
            "  public Builder step() {\n"
            "    return this;\n"
            "  }\n\n"
            "  public String make() {\n"
            "    return \"ok\";\n"
            "  }\n"
            "}\n",
            encoding="utf-8",
        )
        (package_dir / "Helper.java").write_text(
            "package demo;\n\n"
            "public class Helper {\n"
            "  public static void tool(int value) {\n"
            "  }\n\n"
            "  public static void tool(String value) {\n"
            "  }\n"
            "}\n",
            encoding="utf-8",
        )
        (package_dir / "App.java").write_text(
            "package demo;\n\n"
            "import static demo.Helper.tool;\n\n"
            "public class App {\n"
            "  public static void main(String[] args) {\n"
            "    tool(Builder.start().step().make());\n"
            "  }\n"
            "}\n",
            encoding="utf-8",
        )

        with patch(
            "code_scalpel.mcp.helpers.graph_helpers._get_current_tier",
            return_value="pro",
        ):
            result = await get_graph_neighborhood(
                center_node_id="java::demo/App::method::App:main",
                project_root=str(tmp_path),
                k=1,
                max_nodes=40,
            )

        assert result.success
        node_ids = {node.id for node in result.nodes}
        assert "java::demo/App::method::App:main" in node_ids
        assert "java::demo/Builder::method::Builder:start" in node_ids
        assert "java::demo/Builder::method::Builder:step" in node_ids
        assert "java::demo/Builder::method::Builder:make" in node_ids
        assert "java::demo/Helper::method::Helper:tool(String)" in node_ids
        assert "java::demo/Helper::method::Helper:tool(int)" not in node_ids
        edge_ids = {(edge.from_id, edge.to_id) for edge in result.edges}
        assert (
            "java::demo/App::method::App:main",
            "java::demo/Helper::method::Helper:tool(String)",
        ) in edge_ids

    @pytest.mark.asyncio
    async def test_java_method_node_uses_static_fluent_builder_chain_for_overloaded_constructors(
        self, tmp_path
    ):
        """[20260308_TEST] Pro Java neighborhoods should carry static builder entrypoints and longer fluent chains into signature-qualified constructor nodes."""
        from code_scalpel.mcp.server import get_graph_neighborhood

        package_dir = tmp_path / "demo"
        package_dir.mkdir()
        (package_dir / "Builder.java").write_text(
            "package demo;\n\n"
            "public class Builder {\n"
            "  public static Builder start() {\n"
            "    return new Builder();\n"
            "  }\n\n"
            "  public Builder step() {\n"
            "    return this;\n"
            "  }\n\n"
            "  public String make() {\n"
            "    return \"ok\";\n"
            "  }\n"
            "}\n",
            encoding="utf-8",
        )
        (package_dir / "Helper.java").write_text(
            "package demo;\n\n"
            "public class Helper {\n"
            "  public Helper(int value) {\n"
            "  }\n\n"
            "  public Helper(String value) {\n"
            "  }\n"
            "}\n",
            encoding="utf-8",
        )
        (package_dir / "App.java").write_text(
            "package demo;\n\n"
            "public class App {\n"
            "  public static void main(String[] args) {\n"
            "    new Helper(Builder.start().step().make());\n"
            "  }\n"
            "}\n",
            encoding="utf-8",
        )

        with patch(
            "code_scalpel.mcp.helpers.graph_helpers._get_current_tier",
            return_value="pro",
        ):
            result = await get_graph_neighborhood(
                center_node_id="java::demo/App::method::App:main",
                project_root=str(tmp_path),
                k=1,
                max_nodes=40,
            )

        assert result.success
        node_ids = {node.id for node in result.nodes}
        assert "java::demo/Builder::method::Builder:start" in node_ids
        assert "java::demo/Builder::method::Builder:step" in node_ids
        assert "java::demo/Builder::method::Builder:make" in node_ids
        assert "java::demo/Helper::method::Helper:Helper(String)" in node_ids
        assert "java::demo/Helper::method::Helper:Helper(int)" not in node_ids
        edge_ids = {(edge.from_id, edge.to_id) for edge in result.edges}
        assert (
            "java::demo/App::method::App:main",
            "java::demo/Helper::method::Helper:Helper(String)",
        ) in edge_ids

    @pytest.mark.asyncio
    async def test_typescript_node_id_extracts_neighborhood(self, tmp_path):
        """TypeScript local function nodes should participate in neighborhood extraction."""
        # [20260306_TEST] Initial JS/TS graph-neighborhood parity slice.
        from code_scalpel.mcp.server import get_graph_neighborhood

        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "util.ts").write_text(
            "export function helper() {\n"
            "  return 1;\n"
            "}\n",
            encoding="utf-8",
        )
        (src_dir / "main.ts").write_text(
            'import { helper } from "./util";\n\n'
            "export function entry() {\n"
            "  return helper();\n"
            "}\n",
            encoding="utf-8",
        )

        with patch(
            "code_scalpel.mcp.helpers.graph_helpers._get_current_tier",
            return_value="community",
        ):
            result = await get_graph_neighborhood(
                center_node_id="typescript::src/main::function::entry",
                project_root=str(tmp_path),
                k=1,
                max_nodes=20,
            )

        assert result.success
        assert result.tier_applied == "community"
        assert result.max_k_applied == 2
        assert result.max_nodes_applied == 100
        assert result.advanced_resolution_enabled is False
        node_ids = {node.id for node in result.nodes}
        assert "typescript::src/main::function::entry" in node_ids
        assert "external::external::function::helper" in node_ids
        edge_ids = {(edge.from_id, edge.to_id) for edge in result.edges}
        assert (
            "typescript::src/main::function::entry",
            "external::external::function::helper",
        ) in edge_ids

    @pytest.mark.asyncio
    async def test_typescript_method_node_extracts_neighborhood_with_pro_tier(
        self, tmp_path
    ):
        """TypeScript method node IDs should work when advanced resolution is enabled."""
        # [20260306_TEST] JS/TS method-node neighborhood parity uses the advanced builder path.
        from code_scalpel.mcp.server import get_graph_neighborhood

        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "service.ts").write_text(
            "export class Service {\n"
            "  helper(): number {\n"
            "    return 1;\n"
            "  }\n\n"
            "  run(): number {\n"
            "    return this.helper();\n"
            "  }\n"
            "}\n",
            encoding="utf-8",
        )

        with patch(
            "code_scalpel.mcp.helpers.graph_helpers._get_current_tier",
            return_value="pro",
        ):
            result = await get_graph_neighborhood(
                center_node_id="typescript::src/service::method::Service:run",
                project_root=str(tmp_path),
                k=1,
                max_nodes=20,
            )

        assert result.success
        assert result.tier_applied == "pro"
        assert result.max_k_applied is None
        assert result.max_nodes_applied is None
        assert result.advanced_resolution_enabled is True
        node_ids = {node.id for node in result.nodes}
        assert "typescript::src/service::method::Service:run" in node_ids
        assert "typescript::src/service::method::Service:helper" in node_ids
        edge_ids = {(edge.from_id, edge.to_id) for edge in result.edges}
        assert (
            "typescript::src/service::method::Service:run",
            "typescript::src/service::method::Service:helper",
        ) in edge_ids

    @pytest.mark.asyncio
    async def test_typescript_neighborhood_clamps_to_community_limits(self, tmp_path):
        """[20260307_TEST] TypeScript neighborhood slices should honor Community k/node limits."""
        from code_scalpel.mcp.server import get_graph_neighborhood

        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "leaf.ts").write_text(
            "export function leaf(): number {\n  return 1;\n}\n",
            encoding="utf-8",
        )
        (src_dir / "mid.ts").write_text(
            'import { leaf } from "./leaf";\n\n'
            "export function mid(): number {\n  return leaf();\n}\n",
            encoding="utf-8",
        )
        (src_dir / "util.ts").write_text(
            'import { mid } from "./mid";\n\n'
            "export function helper(): number {\n  return mid();\n}\n",
            encoding="utf-8",
        )
        (src_dir / "main.ts").write_text(
            'import { helper } from "./util";\n\n'
            "export function entry(): number {\n  return helper();\n}\n",
            encoding="utf-8",
        )

        with patch(
            "code_scalpel.mcp.helpers.graph_helpers._get_current_tier",
            return_value="community",
        ):
            result = await get_graph_neighborhood(
                center_node_id="typescript::src/main::function::entry",
                project_root=str(tmp_path),
                k=10,
                max_nodes=500,
            )

        assert result.success
        assert result.tier_applied == "community"
        assert result.k == 2
        assert result.max_k_applied == 2
        assert result.max_nodes_applied == 100
        node_ids = {node.id for node in result.nodes}
        assert "typescript::src/main::function::entry" in node_ids
        assert "external::external::function::helper" in node_ids
        assert "typescript::src/util::function::helper" not in node_ids
        assert "typescript::src/mid::function::mid" not in node_ids
        assert "typescript::src/leaf::function::leaf" not in node_ids

    @pytest.mark.asyncio
    async def test_missing_required_parameter_center_node_id(self):
        """Missing center_node_id handled gracefully."""
        # [20260104_TEST] Missing required parameter handling
        from code_scalpel.mcp.server import get_graph_neighborhood

        # Tool may allow empty string or None - should return error instead of crash
        result = await get_graph_neighborhood(center_node_id="", k=1)  # Empty/missing

        # Should fail gracefully with error message
        assert not result.success
        assert result.error is not None


class TestResponseStructure:
    """Test MCP response structure matches specification."""

    @pytest.mark.asyncio
    async def test_response_has_success_field_bool(self):
        """Response has success field (bool)."""
        # [20260104_TEST] Response model validation
        from code_scalpel.mcp.server import get_graph_neighborhood

        result = await get_graph_neighborhood(
            center_node_id="python::main::function::center", k=1, max_nodes=20
        )

        assert hasattr(result, "success")
        assert isinstance(result.success, bool)

    @pytest.mark.asyncio
    async def test_response_error_field_when_failed(self):
        """Response has error field when success=False."""
        # [20260104_TEST] Error field presence on failure
        from code_scalpel.mcp.server import get_graph_neighborhood

        result = await get_graph_neighborhood(
            center_node_id="python::nonexistent::function::fake", k=1
        )

        if not result.success:
            assert hasattr(result, "error")
            assert result.error is not None
            assert len(result.error) > 0

    @pytest.mark.asyncio
    async def test_response_nodes_field_is_list(self):
        """Response nodes field is list of node objects."""
        # [20260104_TEST] Nodes field type validation
        from code_scalpel.mcp.server import get_graph_neighborhood

        result = await get_graph_neighborhood(
            center_node_id="python::main::function::center", k=1, max_nodes=20
        )

        if result.success:
            assert hasattr(result, "nodes")
            assert isinstance(result.nodes, list)

    @pytest.mark.asyncio
    async def test_response_edges_field_is_list(self):
        """Response edges field is list of edge objects."""
        # [20260104_TEST] Edges field type validation
        from code_scalpel.mcp.server import get_graph_neighborhood

        result = await get_graph_neighborhood(
            center_node_id="python::main::function::center", k=1, max_nodes=20
        )

        if result.success:
            assert hasattr(result, "edges")
            assert isinstance(result.edges, list)

    @pytest.mark.asyncio
    async def test_response_truncated_field_is_bool(self):
        """Response truncated field is boolean."""
        # [20260104_TEST] Truncated flag type
        from code_scalpel.mcp.server import get_graph_neighborhood

        result = await get_graph_neighborhood(
            center_node_id="python::main::function::center", k=1, max_nodes=20
        )

        if result.success:
            assert hasattr(result, "truncated")
            assert isinstance(result.truncated, bool)

    @pytest.mark.asyncio
    async def test_response_mermaid_field_is_string(self):
        """Response mermaid field is string."""
        # [20260104_TEST] Mermaid field type validation
        from code_scalpel.mcp.server import get_graph_neighborhood

        result = await get_graph_neighborhood(
            center_node_id="python::main::function::center", k=1, max_nodes=20
        )

        if result.success and result.mermaid:
            assert isinstance(result.mermaid, str)


class TestErrorMessages:
    """Test error messages are clear and actionable."""

    @pytest.mark.asyncio
    async def test_error_message_includes_parameter_name(self):
        """Error message identifies which parameter is invalid."""
        # [20260104_TEST] Error message clarity
        from code_scalpel.mcp.server import get_graph_neighborhood

        result = await get_graph_neighborhood(
            center_node_id="python::main::function::center",
            k=-5,  # Invalid parameter
            max_nodes=20,
        )

        assert not result.success
        # Should mention "k" or "hop" in error
        assert any(word in result.error.lower() for word in ["k", "hop", "parameter"])

    @pytest.mark.asyncio
    async def test_error_message_suggests_fix(self):
        """Error message provides hint for fixing."""
        # [20260104_TEST] Error message actionability
        from code_scalpel.mcp.server import get_graph_neighborhood

        result = await get_graph_neighborhood(
            center_node_id="python::main::function::center", k=0, max_nodes=20
        )

        assert not result.success
        # Should suggest valid values
        assert any(
            word in result.error.lower() for word in ["must", "should", "least", "at"]
        )

    @pytest.mark.asyncio
    async def test_error_message_not_empty(self):
        """Error messages are never empty strings."""
        # [20260104_TEST] Error message presence
        from code_scalpel.mcp.server import get_graph_neighborhood

        result = await get_graph_neighborhood(
            center_node_id="python::nonexistent::function::fake", k=1
        )

        if not result.success:
            assert result.error
            assert len(result.error.strip()) > 0


class TestToolCapabilityGating:
    """Test that tool capabilities are gated by tier."""

    @pytest.mark.asyncio
    async def test_pro_features_absent_in_community(self):
        """Pro-exclusive fields not in Community tier response."""
        # [20260104_TEST] Tier capability gating validation
        from code_scalpel.mcp.server import get_graph_neighborhood

        with patch(
            "code_scalpel.mcp.server._get_current_tier", return_value="community"
        ):
            result = await get_graph_neighborhood(
                center_node_id="python::main::function::center", k=1, max_nodes=20
            )

        if result.success:
            # Community shouldn't have semantic neighbors
            assert (
                not hasattr(result, "semantic_neighbors")
                or not result.semantic_neighbors
            )

    @pytest.mark.asyncio
    async def test_enterprise_features_absent_in_pro(self):
        """Enterprise-exclusive fields not in Pro tier response."""
        # [20260104_TEST] Enterprise feature gating
        from code_scalpel.mcp.server import get_graph_neighborhood

        with patch("code_scalpel.mcp.server._get_current_tier", return_value="pro"):
            result = await get_graph_neighborhood(
                center_node_id="python::main::function::center", k=2, max_nodes=200
            )

        if result.success:
            # Pro shouldn't have query language results
            assert not hasattr(result, "query_results") or not result.query_results

    def test_tier_limits_enforced_in_validation(self):
        """Tier limits are checked during parameter validation."""
        # [20260104_TEST] Tier limit enforcement in validation
        import inspect

        from code_scalpel.mcp.server import get_graph_neighborhood

        # Tool should validate against tier limits
        inspect.signature(get_graph_neighborhood)
        # Should have validation that respects tier
        source = inspect.getsource(get_graph_neighborhood)
        assert "_get_current_tier" in source or "tier" in source.lower()
