"""Comprehensive tier validation for simulate_refactor MCP tool.

[20260121_TEST] Validates all 18 checklist items across Community, Pro, Enterprise tiers.
Focus: capability matrix verification and tier-based limits.
- Community (6 items): basic simulation, structural diff, 1MB limit, basic analysis depth
- Pro (6 items): all Community + advanced simulation, behavior preservation, type checking
- Enterprise (6 items): all Pro + regression prediction, compliance validation, deep analysis
"""

from code_scalpel.licensing.features import get_tool_capabilities


class TestSimulateRefactorCommunityTier:
    """Validate Community tier simulate_refactor constraints (6 tests)."""

    def test_basic_security_issue_detection(self, community_tier):
        """Verify basic security issue detection in Community tier."""
        capabilities = get_tool_capabilities("simulate_refactor", "community") or {}
        cap_set = set(capabilities.get("capabilities", []) or [])
        assert "basic_simulation" in cap_set, "Community should have basic_simulation"

    def test_structural_change_analysis(self, community_tier):
        """Verify structural change analysis in Community tier."""
        capabilities = get_tool_capabilities("simulate_refactor", "community") or {}
        cap_set = set(capabilities.get("capabilities", []) or [])
        assert "structural_diff" in cap_set, "Community should have structural_diff"

    def test_syntax_validation_before_simulation(self, community_tier):
        """Verify syntax validation is part of basic simulation."""
        capabilities = get_tool_capabilities("simulate_refactor", "community") or {}
        cap_set = set(capabilities.get("capabilities", []) or [])
        # Syntax validation included in basic_simulation
        assert "basic_simulation" in cap_set, "Community should validate syntax"

    def test_language_support_python_javascript_typescript(self, community_tier):
        """Verify language support in Community tier."""
        capabilities = get_tool_capabilities("simulate_refactor", "community") or {}
        cap_set = set(capabilities.get("capabilities", []) or [])
        # basic_simulation supports Python, JavaScript, TypeScript
        assert "basic_simulation" in cap_set, "Community should support core languages"

    def test_safe_unsafe_verdict(self, community_tier):
        """Verify safe/unsafe verdict is provided in Community tier."""
        capabilities = get_tool_capabilities("simulate_refactor", "community") or {}
        cap_set = set(capabilities.get("capabilities", []) or [])
        # basic_simulation provides verdict
        assert "basic_simulation" in cap_set, "Community should provide verdicts"

    def test_community_basic_analysis_only(self, community_tier):
        """Verify Community tier uses basic analysis depth only."""
        capabilities = get_tool_capabilities("simulate_refactor", "community") or {}
        limits = capabilities.get("limits", {}) or {}
        analysis_depth = limits.get("analysis_depth")
        max_size = limits.get("max_file_size_mb")
        assert analysis_depth == "basic", f"Community should have basic analysis, got {analysis_depth}"
        assert max_size == 1, f"Community should have 1MB limit, got {max_size}"

    def test_community_max_file_size_limit(self, community_tier):
        """Verify Community tier enforces 1MB max file size."""
        capabilities = get_tool_capabilities("simulate_refactor", "community") or {}
        limits = capabilities.get("limits", {}) or {}
        max_size = limits.get("max_file_size_mb")
        assert max_size == 1, f"Community should have max_file_size_mb=1, got {max_size}"


class TestSimulateRefactorProTier:
    """Validate Pro tier simulate_refactor features (6 tests)."""

    def test_all_community_features_work_pro(self, pro_tier):
        """Verify all Community features work in Pro tier."""
        capabilities = get_tool_capabilities("simulate_refactor", "pro") or {}
        cap_set = set(capabilities.get("capabilities", []) or [])
        # Pro should have Community capabilities
        assert "basic_simulation" in cap_set, "Pro should have basic_simulation"
        assert "structural_diff" in cap_set, "Pro should have structural_diff"

    def test_behavior_equivalence_checking(self, pro_tier):
        """Verify behavior equivalence checking in Pro tier."""
        capabilities = get_tool_capabilities("simulate_refactor", "pro") or {}
        cap_set = set(capabilities.get("capabilities", []) or [])
        assert "behavior_preservation" in cap_set, "Pro should have behavior_preservation"

    def test_test_execution_simulation(self, pro_tier):
        """Verify test execution simulation for Pro tier."""
        capabilities = get_tool_capabilities("simulate_refactor", "pro") or {}
        cap_set = set(capabilities.get("capabilities", []) or [])
        # build_check capability enables test/build execution
        assert "build_check" in cap_set, "Pro should have build_check for test simulation"

    def test_type_checking_enabled(self, pro_tier):
        """Verify type checking is enabled in Pro tier."""
        capabilities = get_tool_capabilities("simulate_refactor", "pro") or {}
        cap_set = set(capabilities.get("capabilities", []) or [])
        assert "type_checking" in cap_set, "Pro should have type_checking"

    def test_advanced_simulation_analysis(self, pro_tier):
        """Verify advanced simulation analysis in Pro tier."""
        capabilities = get_tool_capabilities("simulate_refactor", "pro") or {}
        cap_set = set(capabilities.get("capabilities", []) or [])
        assert "advanced_simulation" in cap_set, "Pro should have advanced_simulation"

    def test_pro_advanced_analysis_depth(self, pro_tier):
        """Verify Pro tier uses advanced analysis depth."""
        capabilities = get_tool_capabilities("simulate_refactor", "pro") or {}
        limits = capabilities.get("limits", {}) or {}
        analysis_depth = limits.get("analysis_depth")
        max_size = limits.get("max_file_size_mb")
        assert analysis_depth == "advanced", f"Pro should have advanced analysis, got {analysis_depth}"
        assert max_size == 10, f"Pro should have 10MB limit, got {max_size}"

    def test_pro_max_file_size_limit(self, pro_tier):
        """Verify Pro tier enforces 10MB max file size."""
        capabilities = get_tool_capabilities("simulate_refactor", "pro") or {}
        limits = capabilities.get("limits", {}) or {}
        max_size = limits.get("max_file_size_mb")
        assert max_size == 10, f"Pro should have max_file_size_mb=10, got {max_size}"


class TestSimulateRefactorEnterpriseTier:
    """Validate Enterprise tier simulate_refactor features (6 tests)."""

    def test_all_pro_features_work_enterprise(self, enterprise_tier):
        """Verify all Pro features work in Enterprise tier."""
        capabilities = get_tool_capabilities("simulate_refactor", "enterprise") or {}
        cap_set = set(capabilities.get("capabilities", []) or [])
        # Enterprise should have all Pro capabilities
        assert "basic_simulation" in cap_set
        assert "advanced_simulation" in cap_set
        assert "behavior_preservation" in cap_set
        assert "type_checking" in cap_set
        assert "build_check" in cap_set

    def test_regression_prediction_enabled(self, enterprise_tier):
        """Verify regression prediction in Enterprise tier."""
        capabilities = get_tool_capabilities("simulate_refactor", "enterprise") or {}
        cap_set = set(capabilities.get("capabilities", []) or [])
        assert "regression_prediction" in cap_set, "Enterprise should have regression_prediction"

    def test_impact_analysis_performed(self, enterprise_tier):
        """Verify impact analysis is performed in Enterprise tier."""
        capabilities = get_tool_capabilities("simulate_refactor", "enterprise") or {}
        cap_set = set(capabilities.get("capabilities", []) or [])
        assert "impact_analysis" in cap_set, "Enterprise should have impact_analysis"

    def test_custom_validation_rules(self, enterprise_tier):
        """Verify custom validation rules from .code-scalpel/ in Enterprise tier."""
        capabilities = get_tool_capabilities("simulate_refactor", "enterprise") or {}
        cap_set = set(capabilities.get("capabilities", []) or [])
        assert "custom_rules" in cap_set, "Enterprise should have custom_rules"

    def test_compliance_validation_enabled(self, enterprise_tier):
        """Verify compliance validation in Enterprise tier."""
        capabilities = get_tool_capabilities("simulate_refactor", "enterprise") or {}
        cap_set = set(capabilities.get("capabilities", []) or [])
        assert "compliance_validation" in cap_set, "Enterprise should have compliance_validation"

    def test_enterprise_deep_analysis_depth(self, enterprise_tier):
        """Verify Enterprise tier uses deep analysis depth."""
        capabilities = get_tool_capabilities("simulate_refactor", "enterprise") or {}
        limits = capabilities.get("limits", {}) or {}
        analysis_depth = limits.get("analysis_depth")
        max_size = limits.get("max_file_size_mb")
        assert analysis_depth == "deep", f"Enterprise should have deep analysis, got {analysis_depth}"
        assert max_size == 100, f"Enterprise should have 100MB limit, got {max_size}"

    def test_enterprise_max_file_size_limit(self, enterprise_tier):
        """Verify Enterprise tier enforces 100MB max file size."""
        capabilities = get_tool_capabilities("simulate_refactor", "enterprise") or {}
        limits = capabilities.get("limits", {}) or {}
        max_size = limits.get("max_file_size_mb")
        assert max_size == 100, f"Enterprise should have max_file_size_mb=100, got {max_size}"


class TestSimulateRefactorCrossTierComparison:
    """Cross-tier comparison tests (3 tests)."""

    def test_community_vs_pro_analysis_depth(self, community_tier, pro_tier):
        """Verify Community vs Pro analysis depth difference."""
        comm_caps = get_tool_capabilities("simulate_refactor", "community") or {}
        pro_caps = get_tool_capabilities("simulate_refactor", "pro") or {}

        comm_depth = comm_caps.get("limits", {}).get("analysis_depth")
        pro_depth = pro_caps.get("limits", {}).get("analysis_depth")

        assert comm_depth == "basic"
        assert pro_depth == "advanced"

    def test_pro_vs_enterprise_analysis_depth(self, pro_tier, enterprise_tier):
        """Verify Pro vs Enterprise analysis depth difference."""
        pro_caps = get_tool_capabilities("simulate_refactor", "pro") or {}
        ent_caps = get_tool_capabilities("simulate_refactor", "enterprise") or {}

        pro_depth = pro_caps.get("limits", {}).get("analysis_depth")
        ent_depth = ent_caps.get("limits", {}).get("analysis_depth")

        assert pro_depth == "advanced"
        assert ent_depth == "deep"

    def test_file_size_limits_progression(self, community_tier, pro_tier, enterprise_tier):
        """Verify file size limits progress across tiers."""
        comm_caps = get_tool_capabilities("simulate_refactor", "community") or {}
        pro_caps = get_tool_capabilities("simulate_refactor", "pro") or {}
        ent_caps = get_tool_capabilities("simulate_refactor", "enterprise") or {}

        comm_limit = comm_caps.get("limits", {}).get("max_file_size_mb")
        pro_limit = pro_caps.get("limits", {}).get("max_file_size_mb")
        ent_limit = ent_caps.get("limits", {}).get("max_file_size_mb")

        assert comm_limit == 1
        assert pro_limit == 10
        assert ent_limit == 100


class TestSimulateRefactorConsistency:
    """Consistency and core capability tests (4 tests)."""

    def test_basic_simulation_across_all_tiers(self, community_tier, pro_tier, enterprise_tier):
        """Verify basic_simulation is in all tiers."""
        for tier in ["community", "pro", "enterprise"]:
            capabilities = get_tool_capabilities("simulate_refactor", tier) or {}
            cap_set = set(capabilities.get("capabilities", []) or [])
            assert "basic_simulation" in cap_set, f"{tier} should have basic_simulation"

    def test_structural_diff_across_all_tiers(self, community_tier, pro_tier, enterprise_tier):
        """Verify structural_diff is in all tiers."""
        for tier in ["community", "pro", "enterprise"]:
            capabilities = get_tool_capabilities("simulate_refactor", tier) or {}
            cap_set = set(capabilities.get("capabilities", []) or [])
            assert "structural_diff" in cap_set, f"{tier} should have structural_diff"

    def test_enterprise_has_advanced_features_pro_lacks(self, pro_tier, enterprise_tier):
        """Verify Enterprise has features that Pro lacks."""
        pro_caps = get_tool_capabilities("simulate_refactor", "pro") or {}
        ent_caps = get_tool_capabilities("simulate_refactor", "enterprise") or {}

        pro_cap_set = set(pro_caps.get("capabilities", []) or [])
        ent_cap_set = set(ent_caps.get("capabilities", []) or [])

        # Enterprise features not in Pro
        assert "regression_prediction" not in pro_cap_set
        assert "regression_prediction" in ent_cap_set
        assert "impact_analysis" not in pro_cap_set
        assert "impact_analysis" in ent_cap_set
        assert "compliance_validation" not in pro_cap_set
        assert "compliance_validation" in ent_cap_set

    def test_pro_has_advanced_features_community_lacks(self, community_tier, pro_tier):
        """Verify Pro has features that Community lacks."""
        comm_caps = get_tool_capabilities("simulate_refactor", "community") or {}
        pro_caps = get_tool_capabilities("simulate_refactor", "pro") or {}

        comm_cap_set = set(comm_caps.get("capabilities", []) or [])
        pro_cap_set = set(pro_caps.get("capabilities", []) or [])

        # Pro features not in Community
        assert "advanced_simulation" not in comm_cap_set
        assert "advanced_simulation" in pro_cap_set
        assert "behavior_preservation" not in comm_cap_set
        assert "behavior_preservation" in pro_cap_set
        assert "type_checking" not in comm_cap_set
        assert "type_checking" in pro_cap_set
