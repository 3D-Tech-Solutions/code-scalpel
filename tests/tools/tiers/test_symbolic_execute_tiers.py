from code_scalpel.licensing.features import get_tool_capabilities
from code_scalpel.mcp.helpers.symbolic_helpers import _symbolic_execute_sync

# [20260121_TEST] Tier validation for symbolic_execute


def _branchy_python_code() -> str:
    return """

def classify(x: int):
    if x > 10:
        return "high"
    if x > 5:
        return "med"
    if x == 5:
        return "mid"
    if x < 0:
        return "neg"
    if x % 2 == 0:
        return "even"
    if x % 3 == 0:
        return "tri"
    return "other"
"""


class TestSymbolicExecuteCommunityTier:
    def setup_method(self) -> None:
        self.caps = get_tool_capabilities("symbolic_execute", "community")
        self.cap_set = set(self.caps.get("capabilities", set()))
        self.limits = self.caps.get("limits", {})

    def test_basic_symbolic_execution_capability(self) -> None:
        assert "basic_symbolic_execution" in self.cap_set
        assert "path_exploration" in self.cap_set

    def test_simple_constraints_and_types(self) -> None:
        assert "simple_constraints" in self.cap_set
        assert set(self.limits.get("constraint_types", [])) == {
            "int",
            "bool",
            "string",
            "float",
        }

    def test_loop_unrolling_and_depth_limit(self) -> None:
        assert "loop_unrolling" in self.cap_set
        assert self.limits.get("max_depth") == 10

    def test_max_paths_limit_community(self) -> None:
        assert self.limits.get("max_paths") == 50
        result = _symbolic_execute_sync(
            _branchy_python_code(),
            max_paths=self.limits["max_paths"],
            max_depth=self.limits["max_depth"],
            constraint_types=self.limits["constraint_types"],
            tier="community",
            capabilities=self.caps,
        )
        assert result.paths_explored <= 50

    def test_python_language_support(self) -> None:
        result = _symbolic_execute_sync(
            "def f(x: int):\n    return x + 1\n",
            max_paths=self.limits["max_paths"],
            max_depth=self.limits["max_depth"],
            constraint_types=self.limits["constraint_types"],
            tier="community",
            capabilities=self.caps,
        )
        assert result.success


class TestSymbolicExecuteProTier:
    def setup_method(self) -> None:
        self.caps = get_tool_capabilities("symbolic_execute", "pro")
        self.cap_set = set(self.caps.get("capabilities", set()))
        self.limits = self.caps.get("limits", {})

    def test_unlimited_paths_and_deeper_loops(self) -> None:
        assert self.limits.get("max_paths") is None
        assert self.limits.get("max_depth") == 100

    def test_pro_capabilities_present(self) -> None:
        expected = {
            "basic_symbolic_execution",
            "simple_constraints",
            "path_exploration",
            "loop_unrolling",
            "complex_constraints",
            "string_constraints",
            "smart_path_prioritization",
            "constraint_optimization",
            "deep_loop_unrolling",
            "list_dict_types",
            "concolic_execution",
        }
        assert expected.issubset(self.cap_set)

    def test_list_dict_and_constraint_types(self) -> None:
        assert set(self.limits.get("constraint_types", [])) == {
            "int",
            "bool",
            "string",
            "float",
            "list",
            "dict",
        }

    def test_concolic_execution_flag(self) -> None:
        assert "concolic_execution" in self.cap_set


class TestSymbolicExecuteEnterpriseTier:
    def setup_method(self) -> None:
        self.caps = get_tool_capabilities("symbolic_execute", "enterprise")
        self.cap_set = set(self.caps.get("capabilities", set()))
        self.limits = self.caps.get("limits", {})

    def test_unlimited_paths_and_depth_enterprise(self) -> None:
        assert self.limits.get("max_paths") is None
        assert self.limits.get("max_depth") is None
        assert self.limits.get("constraint_types") == "all"

    def test_enterprise_capabilities_present(self) -> None:
        expected = {
            "basic_symbolic_execution",
            "simple_constraints",
            "path_exploration",
            "loop_unrolling",
            "complex_constraints",
            "string_constraints",
            "smart_path_prioritization",
            "constraint_optimization",
            "deep_loop_unrolling",
            "list_dict_types",
            "concolic_execution",
            "custom_path_prioritization",
            "distributed_execution",
            "state_space_reduction",
            "complex_object_types",
            "memory_modeling",
            "custom_solvers",
            "advanced_types",
            "formal_verification",
            "equivalence_checking",
        }
        assert expected.issubset(self.cap_set)


class TestSymbolicExecuteCrossTierGating:
    def test_pro_features_absent_in_community(self) -> None:
        community_caps = set(get_tool_capabilities("symbolic_execute", "community").get("capabilities", set()))
        assert "smart_path_prioritization" not in community_caps
        assert "constraint_optimization" not in community_caps
        assert "concolic_execution" not in community_caps

    def test_enterprise_features_absent_in_pro(self) -> None:
        pro_caps = set(get_tool_capabilities("symbolic_execute", "pro").get("capabilities", set()))
        assert "custom_path_prioritization" not in pro_caps
        assert "distributed_execution" not in pro_caps
        assert "state_space_reduction" not in pro_caps
        assert "memory_modeling" not in pro_caps
        assert "custom_solvers" not in pro_caps
        assert "formal_verification" not in pro_caps
        assert "equivalence_checking" not in pro_caps
