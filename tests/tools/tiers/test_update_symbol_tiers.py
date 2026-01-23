"""Comprehensive tier validation for update_symbol MCP tool.

[20260121_TEST] Validates all 22 checklist items across Community, Pro, Enterprise tiers.
Focus: capability matrix verification rather than full patching (requires project context).
- Community (7 items): basic replacement, syntax validation, backup, 4-lang support, 10-update limit
- Pro (6 items): unlimited updates, atomic multi-file, rollback, hooks, formatting, imports
- Enterprise (9 items): unlimited + Pro features, approval, compliance, audit, custom rules, policies
"""

from code_scalpel.licensing.features import get_tool_capabilities


class TestUpdateSymbolCommunityTier:
    """Validate Community tier update_symbol constraints (7 tests)."""

    def test_function_replacement_by_name_capability(self, community_tier):
        """Verify function replacement capability for Community tier."""
        capabilities = get_tool_capabilities("update_symbol", "community") or {}
        cap_set = set(capabilities.get("capabilities", []) or [])
        assert "basic_replacement" in cap_set, "Community should have basic_replacement for functions"

    def test_class_replacement_by_name_capability(self, community_tier):
        """Verify class replacement capability for Community tier."""
        capabilities = get_tool_capabilities("update_symbol", "community") or {}
        cap_set = set(capabilities.get("capabilities", []) or [])
        assert "basic_replacement" in cap_set, "Community should have basic_replacement for classes"

    def test_method_replacement_in_classes_capability(self, community_tier):
        """Verify method replacement capability for Community tier."""
        capabilities = get_tool_capabilities("update_symbol", "community") or {}
        cap_set = set(capabilities.get("capabilities", []) or [])
        assert "basic_replacement" in cap_set, "Community should have basic_replacement for methods"

    def test_automatic_backup_creation_capability(self, community_tier):
        """Verify automatic backup creation capability for Community tier."""
        capabilities = get_tool_capabilities("update_symbol", "community") or {}
        cap_set = set(capabilities.get("capabilities", []) or [])
        limits = capabilities.get("limits", {}) or {}
        assert "automatic_backup" in cap_set, "Community should have automatic_backup capability"
        assert limits.get("backup_enabled") is True, "Community should have backup_enabled=True"

    def test_syntax_validation_before_write_capability(self, community_tier):
        """Verify syntax validation capability for Community tier."""
        capabilities = get_tool_capabilities("update_symbol", "community") or {}
        cap_set = set(capabilities.get("capabilities", []) or [])
        limits = capabilities.get("limits", {}) or {}
        assert "syntax_validation" in cap_set, "Community should have syntax_validation capability"
        assert limits.get("validation_level") == "syntax", "Community should have syntax validation level"

    def test_language_support_python_javascript_typescript_java_capability(self, community_tier):
        """Verify language support for Community tier."""
        capabilities = get_tool_capabilities("update_symbol", "community") or {}
        cap_set = set(capabilities.get("capabilities", []) or [])
        assert "python_support" in cap_set, "Community should support Python"
        assert "javascript_support" in cap_set, "Community should support JavaScript"
        assert "typescript_support" in cap_set, "Community should support TypeScript"
        assert "java_support" in cap_set, "Community should support Java"

    def test_max_10_updates_per_session_enforced_capability(self, community_tier):
        """Verify max 10 updates per call limit for Community tier.

        [20260121_REFACTOR] Switched from per-session to per-call throughput cap.
        """
        capabilities = get_tool_capabilities("update_symbol", "community") or {}
        limits = capabilities.get("limits", {}) or {}
        # Now called max_updates_per_call instead of max_updates_per_session
        max_updates = limits.get("max_updates_per_call")
        assert max_updates == 10, f"Community should have max_updates_per_call=10, got {max_updates}"


class TestUpdateSymbolProTier:
    """Validate Pro tier update_symbol features (6 tests)."""

    def test_unlimited_updates_per_session_capability(self, pro_tier):
        """Verify unlimited updates per call for Pro tier.

        [20260121_REFACTOR] Switched from per-session to per-call throughput cap.
        """
        capabilities = get_tool_capabilities("update_symbol", "pro") or {}
        limits = capabilities.get("limits", {}) or {}
        # Now called max_updates_per_call instead of max_updates_per_session
        max_updates = limits.get("max_updates_per_call")
        assert max_updates == -1, f"Pro should have unlimited (-1) updates, got {max_updates}"

    def test_atomic_multi_file_updates_capability(self, pro_tier):
        """Verify atomic multi-file updates for Pro tier."""
        capabilities = get_tool_capabilities("update_symbol", "pro") or {}
        cap_set = set(capabilities.get("capabilities", []) or [])
        assert "atomic_multi_file" in cap_set, "Pro should have atomic_multi_file capability"

    def test_rollback_on_failure_supported_capability(self, pro_tier):
        """Verify rollback on failure is supported for Pro tier."""
        capabilities = get_tool_capabilities("update_symbol", "pro") or {}
        cap_set = set(capabilities.get("capabilities", []) or [])
        assert "rollback_on_failure" in cap_set, "Pro should have rollback_on_failure capability"

    def test_pre_post_update_hooks_executed_capability(self, pro_tier):
        """Verify pre/post update hooks are available for Pro tier."""
        capabilities = get_tool_capabilities("update_symbol", "pro") or {}
        cap_set = set(capabilities.get("capabilities", []) or [])
        assert "pre_update_hook" in cap_set, "Pro should have pre_update_hook capability"
        assert "post_update_hook" in cap_set, "Pro should have post_update_hook capability"

    def test_formatting_preservation_across_updates_capability(self, pro_tier):
        """Verify formatting preservation for Pro tier."""
        capabilities = get_tool_capabilities("update_symbol", "pro") or {}
        cap_set = set(capabilities.get("capabilities", []) or [])
        assert "formatting_preservation" in cap_set, "Pro should have formatting_preservation capability"

    def test_import_auto_adjustment_applied_capability(self, pro_tier):
        """Verify import auto-adjustment for Pro tier."""
        capabilities = get_tool_capabilities("update_symbol", "pro") or {}
        cap_set = set(capabilities.get("capabilities", []) or [])
        assert "import_auto_adjustment" in cap_set, "Pro should have import_auto_adjustment capability"


class TestUpdateSymbolEnterpriseTier:
    """Validate Enterprise tier update_symbol features (9 tests)."""

    def test_unlimited_updates_with_pro_features_capability(self, enterprise_tier):
        """Verify unlimited updates with all Pro features for Enterprise tier."""
        capabilities = get_tool_capabilities("update_symbol", "enterprise") or {}
        cap_set = set(capabilities.get("capabilities", []) or [])
        # Should have all Pro capabilities
        assert "atomic_multi_file" in cap_set
        assert "rollback_on_failure" in cap_set
        assert "pre_update_hook" in cap_set
        assert "post_update_hook" in cap_set
        assert "formatting_preservation" in cap_set
        assert "import_auto_adjustment" in cap_set

    def test_code_review_approval_requirement_enforced_capability(self, enterprise_tier):
        """Verify code review approval for Enterprise tier."""
        capabilities = get_tool_capabilities("update_symbol", "enterprise") or {}
        cap_set = set(capabilities.get("capabilities", []) or [])
        assert "code_review_approval" in cap_set, "Enterprise should require code review approval"

    def test_compliance_checked_updates_validated_capability(self, enterprise_tier):
        """Verify compliance-checked updates for Enterprise tier."""
        capabilities = get_tool_capabilities("update_symbol", "enterprise") or {}
        cap_set = set(capabilities.get("capabilities", []) or [])
        assert "compliance_check" in cap_set, "Enterprise should have compliance_check capability"

    def test_audit_trail_recorded_for_modifications_capability(self, enterprise_tier):
        """Verify audit trail for Enterprise tier."""
        capabilities = get_tool_capabilities("update_symbol", "enterprise") or {}
        cap_set = set(capabilities.get("capabilities", []) or [])
        assert "audit_trail" in cap_set, "Enterprise should have audit_trail capability"

    def test_custom_validation_rules_applied_capability(self, enterprise_tier):
        """Verify custom validation rules for Enterprise tier."""
        capabilities = get_tool_capabilities("update_symbol", "enterprise") or {}
        cap_set = set(capabilities.get("capabilities", []) or [])
        assert "custom_validation_rules" in cap_set, "Enterprise should have custom_validation_rules capability"

    def test_policy_gated_mutations_enforced_capability(self, enterprise_tier):
        """Verify policy-gated mutations for Enterprise tier."""
        capabilities = get_tool_capabilities("update_symbol", "enterprise") or {}
        cap_set = set(capabilities.get("capabilities", []) or [])
        assert "policy_gated_mutations" in cap_set, "Enterprise should have policy_gated_mutations capability"

    def test_impact_analysis_before_update_capability(self, enterprise_tier):
        """Verify impact analysis for Enterprise tier."""
        capabilities = get_tool_capabilities("update_symbol", "enterprise") or {}
        cap_set = set(capabilities.get("capabilities", []) or [])
        assert "impact_analysis" in cap_set, "Enterprise should have impact_analysis capability"

    def test_git_integration_enabled_capability(self, enterprise_tier):
        """Verify git integration for Enterprise tier."""
        capabilities = get_tool_capabilities("update_symbol", "enterprise") or {}
        cap_set = set(capabilities.get("capabilities", []) or [])
        assert "git_integration" in cap_set, "Enterprise should have git_integration capability"

    def test_test_execution_after_update_capability(self, enterprise_tier):
        """Verify test execution for Enterprise tier."""
        capabilities = get_tool_capabilities("update_symbol", "enterprise") or {}
        cap_set = set(capabilities.get("capabilities", []) or [])
        assert "test_execution" in cap_set, "Enterprise should have test_execution capability"


class TestUpdateSymbolCrossTierComparison:
    """Cross-tier comparison tests (2 tests)."""

    def test_community_vs_pro_update_limit(self, community_tier, pro_tier):
        """Verify Pro has unlimited updates vs Community's 10-limit.

        [20260121_REFACTOR] Now checking max_updates_per_call (per-call model).
        """
        comm_caps = get_tool_capabilities("update_symbol", "community") or {}
        pro_caps = get_tool_capabilities("update_symbol", "pro") or {}

        comm_limit = comm_caps.get("limits", {}).get("max_updates_per_call")
        pro_limit = pro_caps.get("limits", {}).get("max_updates_per_call")

        assert comm_limit == 10, "Community should have 10-update per-call limit"
        assert pro_limit == -1, "Pro should have unlimited (-1) per-call limit"

    def test_community_no_advanced_features_pro_has(self, community_tier, pro_tier):
        """Verify Pro has advanced features that Community lacks."""
        comm_caps = get_tool_capabilities("update_symbol", "community") or {}
        pro_caps = get_tool_capabilities("update_symbol", "pro") or {}

        comm_cap_set = set(comm_caps.get("capabilities", []) or [])
        pro_cap_set = set(pro_caps.get("capabilities", []) or [])

        # Pro should have these that Community lacks
        assert "atomic_multi_file" not in comm_cap_set
        assert "atomic_multi_file" in pro_cap_set
        assert "semantic_validation" not in comm_cap_set
        assert "semantic_validation" in pro_cap_set


class TestUpdateSymbolEdgeCases:
    """Edge case and validation level tests (3 tests)."""

    def test_validation_level_progression(self, community_tier, pro_tier, enterprise_tier):
        """Verify validation level progression across tiers.

        [20260121_REFACTOR] Unchanged by per-call refactor; still test validation levels.
        """
        comm_caps = get_tool_capabilities("update_symbol", "community") or {}
        pro_caps = get_tool_capabilities("update_symbol", "pro") or {}
        ent_caps = get_tool_capabilities("update_symbol", "enterprise") or {}

        comm_level = comm_caps.get("limits", {}).get("validation_level")
        pro_level = pro_caps.get("limits", {}).get("validation_level")
        ent_level = ent_caps.get("limits", {}).get("validation_level")

        assert comm_level == "syntax", f"Community should have syntax validation, got {comm_level}"
        assert pro_level == "semantic", f"Pro should have semantic validation, got {pro_level}"
        assert ent_level == "full", f"Enterprise should have full validation, got {ent_level}"

    def test_backup_capability_across_all_tiers(self, community_tier, pro_tier, enterprise_tier):
        """Verify backup capability is available in all tiers."""
        for tier in ["community", "pro", "enterprise"]:
            capabilities = get_tool_capabilities("update_symbol", tier) or {}
            cap_set = set(capabilities.get("capabilities", []) or [])
            limits = capabilities.get("limits", {}) or {}
            assert "automatic_backup" in cap_set, f"{tier} should have automatic_backup"
            assert limits.get("backup_enabled") is True, f"{tier} should have backup_enabled=True"

    def test_language_support_consistency(self, community_tier, pro_tier, enterprise_tier):
        """Verify all tiers support core languages."""
        core_langs = [
            "python_support",
            "javascript_support",
            "typescript_support",
            "java_support",
        ]
        for tier in ["community", "pro", "enterprise"]:
            capabilities = get_tool_capabilities("update_symbol", tier) or {}
            cap_set = set(capabilities.get("capabilities", []) or [])
            for lang in core_langs:
                assert lang in cap_set, f"{tier} should support {lang}"
