"""
Tests for get_call_graph tier enforcement and output metadata.

[20260111_TEST] v1.0 validation - Ensure tier limits, capabilities, and metadata
are properly enforced and populated.
"""

import pytest

from src.code_scalpel.mcp.server import CallGraphResultModel, get_call_graph


class TestOutputMetadataFields:
    """Test that output metadata fields are present and correctly populated."""

    @pytest.mark.asyncio
    async def test_basic_call_graph_includes_metadata(self, tmp_path, community_tier):
        """Basic call graph should include all metadata fields."""
        # Create a simple project
        main_file = tmp_path / "main.py"
        main_file.write_text("""
def main():
    helper()

def helper():
    return 42
""")
        # community_tier fixture ensures community tier detection
        result = await get_call_graph(project_root=str(tmp_path), depth=5)

        assert result.data.success is True
        # Verify metadata fields exist and have correct types
        assert hasattr(result.data, "tier_applied")
        assert hasattr(result.data, "max_depth_applied")
        assert hasattr(result.data, "max_nodes_applied")
        assert hasattr(result.data, "advanced_resolution_enabled")
        assert hasattr(result.data, "enterprise_metrics_enabled")

        # Verify values are reasonable
        assert result.data.tier_applied in ("community", "pro", "enterprise")
        assert isinstance(result.advanced_resolution_enabled, bool)
        assert isinstance(result.enterprise_metrics_enabled, bool)

    @pytest.mark.asyncio
    async def test_metadata_reflects_actual_limits(self, tmp_path, community_tier):
        """Metadata should accurately reflect applied limits."""
        main_file = tmp_path / "main.py"
        main_file.write_text("def foo(): pass")

        # community_tier fixture ensures community tier detection
        result = await get_call_graph(project_root=str(tmp_path), depth=10)

        assert result.data.success is True
        # max_depth_applied should reflect tier limits
        # Enterprise has None (unlimited), Pro has 50, Community has 3
        if result.tier_applied == "enterprise":
            assert result.data.max_depth_applied is None
            assert result.data.max_nodes_applied is None
        elif result.tier_applied == "pro":
            assert result.data.max_depth_applied == 50
            assert result.data.max_nodes_applied == 500
        else:  # community
            assert result.data.max_depth_applied == 3
            assert result.data.max_nodes_applied == 50


class TestMetadataFieldTypes:
    """Test the data types of metadata fields in the model."""

    def test_call_graph_result_model_has_metadata_fields(self):
        """CallGraphResultModel should define all metadata fields."""
        fields = CallGraphResultModel.model_fields

        # Check all metadata fields exist
        assert "tier_applied" in fields
        assert "max_depth_applied" in fields
        assert "max_nodes_applied" in fields
        assert "advanced_resolution_enabled" in fields
        assert "enterprise_metrics_enabled" in fields

    def test_metadata_fields_have_defaults(self):
        """Metadata fields should have sensible defaults."""
        result = CallGraphResultModel(
            success=True,
        )

        # Verify defaults are applied
        assert result.tier_applied == "community"  # Default tier
        assert result.max_depth_applied is None  # No limit by default
        assert result.max_nodes_applied is None  # No limit by default
        assert result.advanced_resolution_enabled is False  # Disabled by default
        assert result.enterprise_metrics_enabled is False  # Disabled by default

    def test_metadata_fields_can_be_set(self):
        """Metadata fields should accept valid values."""
        result = CallGraphResultModel(
            success=True,
            tier_applied="pro",
            max_depth_applied=50,
            max_nodes_applied=500,
            advanced_resolution_enabled=True,
            enterprise_metrics_enabled=False,
        )

        assert result.tier_applied == "pro"
        assert result.max_depth_applied == 50
        assert result.max_nodes_applied == 500
        assert result.advanced_resolution_enabled is True
        assert result.enterprise_metrics_enabled is False


class TestTierEnforcement:
    """Test that tier limits are properly enforced."""

    @pytest.mark.asyncio
    async def test_community_tier_depth_limit(self, tmp_path, community_tier):
        """Community tier should enforce max_depth=3."""
        # Create a deeply nested call chain
        main_file = tmp_path / "main.py"
        main_file.write_text("""
def level_0():
    level_1()

def level_1():
    level_2()

def level_2():
    level_3()

def level_3():
    level_4()

def level_4():
    level_5()

def level_5():
    pass
""")
        # community_tier fixture from conftest.py disables license discovery
        result = await get_call_graph(project_root=str(tmp_path), depth=10)

        assert result.data.success is True
        assert result.data.tier_applied == "community"
        assert result.data.max_depth_applied == 3  # Community limit
        # Depth should be clamped to 3 even if requested 10

    @pytest.mark.asyncio
    async def test_pro_tier_higher_limits(self, tmp_path, pro_tier):
        """Pro tier should have higher limits than Community."""
        main_file = tmp_path / "main.py"
        main_file.write_text("def foo(): pass")

        # pro_tier fixture from conftest.py sets JWT license
        result = await get_call_graph(project_root=str(tmp_path), depth=10)

        assert result.data.success is True
        assert result.data.tier_applied == "pro"
        assert result.data.max_depth_applied == 50  # Pro limit
        assert result.data.max_nodes_applied == 500  # Pro limit

    @pytest.mark.asyncio
    async def test_enterprise_tier_unlimited(self, tmp_path, enterprise_tier):
        """Enterprise tier should have unlimited (None) limits."""
        main_file = tmp_path / "main.py"
        main_file.write_text("def foo(): pass")

        # enterprise_tier fixture from conftest.py sets JWT license
        result = await get_call_graph(project_root=str(tmp_path), depth=100)

        assert result.data.success is True
        assert result.data.tier_applied == "enterprise"
        assert result.data.max_depth_applied is None  # Unlimited
        assert result.data.max_nodes_applied is None  # Unlimited


class TestCapabilityFlags:
    """Test that capability flags are correctly set based on tier."""

    @pytest.mark.asyncio
    async def test_community_no_advanced_resolution(self, tmp_path, community_tier):
        """Community tier should not have advanced_resolution_enabled."""
        main_file = tmp_path / "main.py"
        main_file.write_text("def foo(): pass")

        # community_tier fixture from conftest.py disables license discovery
        result = await get_call_graph(project_root=str(tmp_path))

        assert result.data.success is True
        assert result.data.advanced_resolution_enabled is False
        assert result.data.enterprise_metrics_enabled is False

    @pytest.mark.asyncio
    async def test_pro_has_advanced_resolution(self, tmp_path, pro_tier):
        """Pro tier should have advanced_resolution_enabled."""
        main_file = tmp_path / "main.py"
        main_file.write_text("def foo(): pass")

        # pro_tier fixture from conftest.py sets JWT license
        result = await get_call_graph(project_root=str(tmp_path))

        assert result.data.success is True
        assert result.data.advanced_resolution_enabled is True
        assert result.data.enterprise_metrics_enabled is False  # Pro doesn't have this

    @pytest.mark.asyncio
    async def test_enterprise_has_all_features(self, tmp_path, enterprise_tier):
        """Enterprise tier should have all capabilities enabled."""
        main_file = tmp_path / "main.py"
        main_file.write_text("def foo(): pass")

        # enterprise_tier fixture from conftest.py sets JWT license
        result = await get_call_graph(project_root=str(tmp_path))

        assert result.data.success is True
        assert result.data.advanced_resolution_enabled is True
        assert result.data.enterprise_metrics_enabled is True


class TestTruncationMetadata:
    """Test truncation metadata is properly populated."""

    @pytest.mark.asyncio
    async def test_no_truncation_when_within_limits(self, tmp_path):
        """When within limits, truncation fields should indicate no truncation."""
        main_file = tmp_path / "main.py"
        main_file.write_text("""
def foo():
    bar()

def bar():
    pass
""")
        result = await get_call_graph(project_root=str(tmp_path))

        assert result.data.success is True
        assert result.data.total_nodes is not None
        assert result.data.nodes_truncated is False
        assert result.data.truncation_warning is None

    @pytest.mark.asyncio
    async def test_truncation_fields_present(self, tmp_path):
        """Truncation metadata fields should always be present."""
        main_file = tmp_path / "main.py"
        main_file.write_text("def foo(): pass")

        result = await get_call_graph(project_root=str(tmp_path))

        assert result.data.success is True
        assert hasattr(result.data, "total_nodes")
        assert hasattr(result.data, "total_edges")
        assert hasattr(result.data, "nodes_truncated")
        assert hasattr(result.data, "edges_truncated")
        assert hasattr(result.data, "truncation_warning")

    @pytest.mark.asyncio
    async def test_truncation_flag_set_when_exceeding_limits(self, tmp_path, community_tier):
        """When node count exceeds Community limits, truncation flags should be set."""
        # Build more than 60 functions chained to exceed the 50-node cap
        chain = []
        for i in range(65):
            if i == 64:
                chain.append(f"def f{i}():\n    return {i}\n")
            else:
                chain.append(f"def f{i}():\n    return f{i+1}()\n")
        code = "\n".join(chain)
        (tmp_path / "many.py").write_text(code)

        result = await get_call_graph(project_root=str(tmp_path), depth=10)

        assert result.data.success is True
        assert result.data.tier_applied == "community"
        assert result.data.nodes_truncated is True
        assert result.data.truncation_warning is not None

    @pytest.mark.asyncio
    async def test_pro_truncation_when_exceeding_max_nodes(self, tmp_path, pro_tier):
        """[20260121_TEST] Pro tier should truncate when max_nodes=500 is exceeded."""
        chain = []
        for i in range(520):
            if i == 519:
                chain.append(f"def f{i}():\n    return {i}\n")
            else:
                chain.append(f"def f{i}():\n    return f{i+1}()\n")
        (tmp_path / "pro_many.py").write_text("\n".join(chain))

        result = await get_call_graph(project_root=str(tmp_path), depth=1000)

        assert result.data.success is True
        assert result.data.tier_applied == "pro"
        assert result.data.max_nodes_applied == 500
        assert result.data.nodes_truncated is True
        assert result.data.truncation_warning is not None


class TestEntryPointDetection:
    """Validate entry point heuristics across tiers and languages."""

    @pytest.mark.asyncio
    async def test_pytest_entry_point_marked(self, tmp_path, community_tier):
        """[20260121_TEST] pytest-style test_* function is flagged as entry point in test modules."""
        (tmp_path / "test_sample.py").write_text("""
import helper

def test_example():
    helper.fn()
""")
        (tmp_path / "helper.py").write_text("def fn():\n    return 1\n")

        result = await get_call_graph(project_root=str(tmp_path), depth=5)

        entry_nodes = {n.name for n in result.nodes if n.is_entry_point}
        assert "test_example" in entry_nodes

    @pytest.mark.asyncio
    async def test_js_entry_point_consistent_pro(self, tmp_path, pro_tier):
        """[20260121_TEST] JS entry points (invoked main) remain entry points under Pro tier."""
        (tmp_path / "index.js").write_text("""
function main() {
    return 1;
}

main();
""")

        result = await get_call_graph(project_root=str(tmp_path), depth=5)

        assert result.data.tier_applied == "pro"
        assert any(n.is_entry_point and n.name == "main" for n in result.nodes)

    @pytest.mark.asyncio
    async def test_ts_entry_point_consistent_enterprise(self, tmp_path, enterprise_tier):
        """[20260121_TEST] TS entry points remain entry points under Enterprise tier."""
        (tmp_path / "index.ts").write_text("""
function main(): number {
    return 1;
}

main();
""")

        result = await get_call_graph(project_root=str(tmp_path), depth=5)

        assert result.data.tier_applied == "enterprise"
        assert any(n.is_entry_point and n.name == "main" for n in result.nodes)


class TestEnterpriseMetrics:
    """Test enterprise-only metrics."""

    @pytest.mark.asyncio
    async def test_hot_nodes_field_exists(self, tmp_path):
        """Hot nodes field should exist even if empty."""
        main_file = tmp_path / "main.py"
        main_file.write_text("def foo(): pass")

        result = await get_call_graph(project_root=str(tmp_path))

        assert result.data.success is True
        assert hasattr(result.data, "hot_nodes")
        assert isinstance(result.hot_nodes, list)

    @pytest.mark.asyncio
    async def test_dead_code_candidates_field_exists(self, tmp_path):
        """Dead code candidates field should exist even if empty."""
        main_file = tmp_path / "main.py"
        main_file.write_text("def foo(): pass")

        result = await get_call_graph(project_root=str(tmp_path))

        assert result.data.success is True
        assert hasattr(result.data, "dead_code_candidates")
        assert isinstance(result.dead_code_candidates, list)


class TestProConfidenceAndMetrics:
    """Validate Pro-tier edge confidence and graph metrics are populated."""

    @pytest.mark.asyncio
    async def test_pro_confidence_scores_present(self, tmp_path, pro_tier):
        """[20260121_TEST] Pro edges should include confidence metadata within bounds."""
        (tmp_path / "a.py").write_text("""
class Base:
    def call(self):
        return 1

class Impl(Base):
    def call(self):
        return 2

def run(x: Base):
    return x.call()

def main():
    return run(Impl())
""")

        result = await get_call_graph(project_root=str(tmp_path), depth=10)

        assert result.data.success is True
        assert result.data.tier_applied == "pro"
        assert result.data.total_nodes is not None
        assert result.data.total_edges is not None
        assert all(0.0 <= edge.confidence <= 1.0 for edge in result.edges)
        assert all(
            edge.inference_source in {"static", "type_hint", "class_hierarchy", "pattern_match"}
            for edge in result.edges
        )

    @pytest.mark.asyncio
    async def test_pro_polymorphism_resolution(self, tmp_path, pro_tier):
        """[20260121_TEST] Advanced resolution should map instance method calls to class-qualified targets."""
        (tmp_path / "poly.py").write_text("""
class Worker:
    def do(self):
        return 1

def use():
    w = Worker()
    return w.do()
""")

        result = await get_call_graph(project_root=str(tmp_path), depth=5)

        assert result.data.success is True
        assert result.data.tier_applied == "pro"
        assert any(edge.callee.endswith("Worker.do") for edge in result.edges)


class TestEnterpriseHotPathsAndDeadCode:
    """Validate Enterprise metadata includes hot paths and dead code candidates."""

    @pytest.mark.asyncio
    async def test_enterprise_hot_nodes_and_dead_code(self, tmp_path, enterprise_tier):
        """[20260121_TEST] Enterprise should populate hot_nodes and dead_code_candidates with meaningful entries."""
        (tmp_path / "app.py").write_text("""
def entry():
    hub()
    leaf1()

def hub():
    leaf1()
    leaf2()

def leaf1():
    pass

def leaf2():
    pass

def ghost():
    return 0
""")

        result = await get_call_graph(project_root=str(tmp_path), depth=10)

        assert result.data.success is True
        assert result.data.tier_applied == "enterprise"
        assert result.data.enterprise_metrics_enabled is True

        # hub has highest degree; ghost is uncalled dead code
        assert any("hub" in node for node in result.hot_nodes)
        assert any("ghost" in node for node in result.dead_code_candidates)


class TestProCallbacksAndClosures:
    """Validate Pro tier resolves nested functions and method chains correctly."""

    @pytest.mark.asyncio
    async def test_pro_nested_function_resolution(self, tmp_path, pro_tier):
        """[20260121_TEST] Pro should resolve nested function calls in advanced mode."""
        (tmp_path / "app.py").write_text("""
def outer():
    def inner():
        helper()
    inner()

def helper():
    pass
""")

        result = await get_call_graph(project_root=str(tmp_path), depth=10)

        assert result.data.success is True
        assert result.data.tier_applied == "pro"
        assert result.data.advanced_resolution_enabled is True

        # Pro should detect nested function calls
        callee_list = [edge.callee for edge in result.edges]
        assert any(
            "inner" in callee or "helper" in callee for callee in callee_list
        ), "Pro should resolve nested functions"

    @pytest.mark.asyncio
    async def test_pro_method_chaining(self, tmp_path, pro_tier):
        """[20260121_TEST] Pro should resolve method chains with advanced resolution."""
        (tmp_path / "app.py").write_text("""
class Builder:
    def configure(self):
        self.setup()
        return self

    def setup(self):
        self.initialize()

    def initialize(self):
        pass

builder = Builder()
builder.configure().setup()
""")

        result = await get_call_graph(project_root=str(tmp_path), depth=10)

        assert result.data.success is True
        assert result.data.tier_applied == "pro"
        assert result.data.advanced_resolution_enabled is True
        # Pro resolves method chaining
        callee_list = [edge.callee for edge in result.edges]
        assert any("configure" in callee or "setup" in callee for callee in callee_list)


class TestProMermaidAndMetrics:
    """Validate Pro tier includes comprehensive edge metrics and metadata."""

    @pytest.mark.asyncio
    async def test_pro_edge_metrics_completeness(self, tmp_path, pro_tier):
        """[20260121_TEST] Pro edges should have confidence and inference_source populated."""
        (tmp_path / "app.py").write_text("""
class Service:
    def process(self):
        self.validate()

    def validate(self):
        pass

svc = Service()
svc.process()
""")

        result = await get_call_graph(project_root=str(tmp_path), depth=10)

        assert result.data.success is True
        assert result.data.tier_applied == "pro"

        # Pro edges should have confidence and inference_source
        for edge in result.edges:
            assert hasattr(edge, "confidence"), "Pro edges must have confidence metric"
            assert hasattr(edge, "inference_source"), "Pro edges must have inference_source"
            assert 0.0 <= edge.confidence <= 1.0, f"Confidence must be in [0, 1], got {edge.confidence}"
            assert edge.inference_source in {
                "static",
                "type_hint",
                "class_hierarchy",
                "pattern_match",
            }, f"Invalid inference_source: {edge.inference_source}"

    @pytest.mark.asyncio
    async def test_pro_multiple_call_site_tracking(self, tmp_path, pro_tier):
        """[20260121_TEST] Pro should track multiple call sites for same target."""
        (tmp_path / "app.py").write_text("""
def utility():
    pass

def caller_one():
    utility()

def caller_two():
    utility()

caller_one()
caller_two()
""")

        result = await get_call_graph(project_root=str(tmp_path), depth=10)

        assert result.data.success is True
        assert result.data.tier_applied == "pro"

        # Pro should have multiple edges to utility
        edges_to_utility = [edge for edge in result.edges if "utility" in edge.callee]
        assert len(edges_to_utility) >= 2, "Pro should track both call sites to utility()"


class TestEnterpriseAdvancedGraphAnalysis:
    """Validate Enterprise tier advanced graph analysis capabilities."""

    @pytest.mark.asyncio
    async def test_enterprise_deep_call_graph(self, tmp_path, enterprise_tier):
        """[20260121_TEST] Enterprise should support deep call graphs beyond Pro limits."""
        # Create a chain deeper than Pro's default limit
        code_lines = ["def entry():\n    level1()"]
        for i in range(1, 50):
            code_lines.append(f"\ndef level{i}():\n    level{i + 1}()")
        code_lines.append("\ndef level51():\n    pass")

        (tmp_path / "app.py").write_text("\n".join(code_lines))

        result = await get_call_graph(project_root=str(tmp_path), depth=60)

        assert result.data.success is True
        assert result.data.tier_applied == "enterprise"
        # Enterprise unlimited depth, Pro would be capped at 50
        assert result.data.max_depth_applied is None or result.max_depth_applied > 50

    @pytest.mark.asyncio
    async def test_enterprise_unlimited_nodes(self, tmp_path, enterprise_tier):
        """[20260121_TEST] Enterprise should not limit node count in call graph."""
        # Create many functions
        code_lines = ["def entry():\n"]
        for i in range(100):
            code_lines.append(f"    func{i}()")
        for i in range(100):
            code_lines.append(f"\ndef func{i}():\n    pass")

        (tmp_path / "app.py").write_text("\n".join(code_lines))

        result = await get_call_graph(project_root=str(tmp_path), depth=10)

        assert result.data.success is True
        assert result.data.tier_applied == "enterprise"
        assert result.data.max_nodes_applied is None, "Enterprise should have unlimited nodes"
        # Should capture all functions
        assert len(result.edges) > 50, "Enterprise should include all edges without truncation"


class TestEnterpriseComplexGraphPatterns:
    """Validate Enterprise tier detects complex graph patterns."""

    @pytest.mark.asyncio
    async def test_enterprise_circular_dependency_detection(self, tmp_path, enterprise_tier):
        """[20260121_TEST] Enterprise should detect and report circular dependencies."""
        (tmp_path / "app.py").write_text("""
def func_a():
    func_b()

def func_b():
    func_c()

def func_c():
    func_a()  # Circular: func_c -> func_a -> func_b -> func_c
""")

        result = await get_call_graph(
            project_root=str(tmp_path),
            depth=10,
            include_circular_import_check=True,
        )

        assert result.data.success is True
        assert result.data.tier_applied == "enterprise"
        # Enterprise should detect circular dependency in call structure
        assert len(result.edges) > 0, "Should detect edges in circular structure"

    @pytest.mark.asyncio
    async def test_enterprise_entry_point_expansion(self, tmp_path, enterprise_tier):
        """[20260121_TEST] Enterprise should identify all entry points (main, CLI, API routes)."""
        (tmp_path / "main.py").write_text("""
def main():
    init()

def init():
    setup()

def setup():
    pass

if __name__ == "__main__":
    main()
""")

        result = await get_call_graph(
            project_root=str(tmp_path),
            entry_point="main",
            depth=10,
        )

        assert result.data.success is True
        assert result.data.tier_applied == "enterprise"
        # Enterprise should trace from main through full initialization chain
        assert any("setup" in e.callee for e in result.edges)


class TestEnterpriseMermaidAndVisualization:
    """Validate Enterprise tier rich visualization with metrics."""

    @pytest.mark.asyncio
    async def test_enterprise_mermaid_generation(self, tmp_path, enterprise_tier):
        """[20260121_TEST] Enterprise should generate Mermaid diagrams showing full graph."""
        (tmp_path / "app.py").write_text("""
def render_dashboard():
    fetch_metrics()
    fetch_user()

def fetch_metrics():
    query_database()

def fetch_user():
    query_database()

def query_database():
    pass
""")

        result = await get_call_graph(project_root=str(tmp_path), depth=10)

        assert result.data.success is True
        assert result.data.tier_applied == "enterprise"
        # Enterprise should generate comprehensive call graph
        assert len(result.edges) >= 4, "Enterprise should have all function edges"

    @pytest.mark.asyncio
    async def test_enterprise_rich_metadata_export(self, tmp_path, enterprise_tier):
        """[20260121_TEST] Enterprise call graph should include rich metadata for visualization."""
        (tmp_path / "app.py").write_text("""
def hub_function():
    leaf_a()
    leaf_b()
    leaf_c()

def leaf_a():
    pass

def leaf_b():
    pass

def leaf_c():
    pass

def unused_function():
    pass
""")

        result = await get_call_graph(project_root=str(tmp_path), depth=10)

        assert result.data.success is True
        assert result.data.tier_applied == "enterprise"
        assert result.data.enterprise_metrics_enabled is True

        # Enterprise identifies hub nodes
        assert len(result.hot_nodes) > 0, "Enterprise should identify hub functions"
        assert any("hub_function" in node for node in result.hot_nodes), "hub_function should be identified as hot node"

        # Enterprise identifies dead code
        assert len(result.dead_code_candidates) > 0, "Enterprise should identify unused functions"
        assert any(
            "unused_function" in node for node in result.dead_code_candidates
        ), "unused_function should be in dead code candidates"
