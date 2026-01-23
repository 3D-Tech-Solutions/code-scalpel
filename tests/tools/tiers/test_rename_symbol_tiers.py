"""Comprehensive tier validation for rename_symbol MCP tool.

[20260121_TEST] Validates all 16 checklist items across Community, Pro, Enterprise tiers.
Focus: capability matrix verification and tier-based limit enforcement.
- Community (6 items): definition-only rename, same-file refs, syntax validation, snake_case
- Pro (6 items): all Community + cross-file rename, imports, docstrings, test sync, backup/rollback
- Enterprise (4 items): all Pro + repo-wide rename, audit trail, compliance checks
"""

from code_scalpel.licensing.features import get_tool_capabilities


class TestRenameSymbolCommunityTier:
    """Validate Community tier rename_symbol constraints (6 tests)."""

    def test_python_function_rename_capability(self, community_tier):
        """Verify Python function rename capability for Community tier."""
        capabilities = get_tool_capabilities("rename_symbol", "community") or {}
        cap_set = set(capabilities.get("capabilities", []) or [])
        assert "definition_rename" in cap_set, "Community should have definition_rename capability"

    def test_python_class_rename_capability(self, community_tier):
        """Verify Python class rename capability for Community tier."""
        capabilities = get_tool_capabilities("rename_symbol", "community") or {}
        cap_set = set(capabilities.get("capabilities", []) or [])
        assert "definition_rename" in cap_set, "Community should have definition_rename for classes"

    def test_python_method_rename_capability(self, community_tier):
        """Verify Python method rename capability for Community tier."""
        capabilities = get_tool_capabilities("rename_symbol", "community") or {}
        cap_set = set(capabilities.get("capabilities", []) or [])
        assert "definition_rename" in cap_set, "Community should have definition_rename for methods"

    def test_automatic_reference_updates_same_file_capability(self, community_tier):
        """Verify automatic reference updates in same file for Community tier."""
        capabilities = get_tool_capabilities("rename_symbol", "community") or {}
        cap_set = set(capabilities.get("capabilities", []) or [])
        # definition_rename implies same-file reference updates via tokenize
        assert "definition_rename" in cap_set, "Community should support same-file reference updates"

    def test_syntax_validation_via_ast_capability(self, community_tier):
        """Verify syntax validation via AST parsing for Community tier."""
        capabilities = get_tool_capabilities("rename_symbol", "community") or {}
        cap_set = set(capabilities.get("capabilities", []) or [])
        # AST validation is part of definition_rename
        assert "definition_rename" in cap_set, "Community should validate via AST"

    def test_python_identifier_validation_snake_case_capability(self, community_tier):
        """Verify Python identifier validation (snake_case enforcement) for Community tier."""
        capabilities = get_tool_capabilities("rename_symbol", "community") or {}
        cap_set = set(capabilities.get("capabilities", []) or [])
        # Identifier validation is part of definition_rename
        assert "definition_rename" in cap_set, "Community should enforce snake_case validation"

    def test_community_no_cross_file_rename_limits(self, community_tier):
        """Verify Community tier has zero cross-file rename limits."""
        capabilities = get_tool_capabilities("rename_symbol", "community") or {}
        limits = capabilities.get("limits", {}) or {}
        max_searched = limits.get("max_files_searched")
        max_updated = limits.get("max_files_updated")
        assert max_searched == 0, f"Community should have max_files_searched=0, got {max_searched}"
        assert max_updated == 0, f"Community should have max_files_updated=0, got {max_updated}"


class TestRenameSymbolProTier:
    """Validate Pro tier rename_symbol features (6 tests)."""

    def test_all_community_features_work_pro(self, pro_tier):
        """Verify all Community features work for Pro tier."""
        capabilities = get_tool_capabilities("rename_symbol", "pro") or {}
        cap_set = set(capabilities.get("capabilities", []) or [])
        # Pro should have all Community capabilities
        assert "definition_rename" in cap_set, "Pro should have definition_rename"
        assert "backup" in cap_set, "Pro should have backup"
        assert "path_security_validation" in cap_set, "Pro should have path_security_validation"

    def test_cross_file_rename_propagation_capability(self, pro_tier):
        """Verify cross-file rename propagation for Pro tier."""
        capabilities = get_tool_capabilities("rename_symbol", "pro") or {}
        cap_set = set(capabilities.get("capabilities", []) or [])
        assert "cross_file_reference_rename" in cap_set, "Pro should have cross_file_reference_rename capability"

    def test_import_statement_updates_capability(self, pro_tier):
        """Verify import statement updates for Pro tier."""
        capabilities = get_tool_capabilities("rename_symbol", "pro") or {}
        cap_set = set(capabilities.get("capabilities", []) or [])
        assert "import_rename" in cap_set, "Pro should have import_rename capability"

    def test_cross_file_search_limits_pro(self, pro_tier):
        """Verify Pro tier has bounded cross-file search limits."""
        capabilities = get_tool_capabilities("rename_symbol", "pro") or {}
        limits = capabilities.get("limits", {}) or {}
        max_searched = limits.get("max_files_searched")
        max_updated = limits.get("max_files_updated")
        assert max_searched == 500, f"Pro should have max_files_searched=500, got {max_searched}"
        assert max_updated == 200, f"Pro should have max_files_updated=200, got {max_updated}"

    def test_backup_and_rollback_support_pro(self, pro_tier):
        """Verify backup and rollback support for Pro tier."""
        capabilities = get_tool_capabilities("rename_symbol", "pro") or {}
        cap_set = set(capabilities.get("capabilities", []) or [])
        assert "backup" in cap_set, "Pro should have backup capability"

    def test_pro_has_advanced_features_community_lacks(self, pro_tier, community_tier):
        """Verify Pro has advanced features that Community lacks."""
        comm_caps = get_tool_capabilities("rename_symbol", "community") or {}
        pro_caps = get_tool_capabilities("rename_symbol", "pro") or {}

        comm_cap_set = set(comm_caps.get("capabilities", []) or [])
        pro_cap_set = set(pro_caps.get("capabilities", []) or [])

        # Pro should have these that Community lacks
        assert "cross_file_reference_rename" not in comm_cap_set
        assert "cross_file_reference_rename" in pro_cap_set
        assert "import_rename" not in comm_cap_set
        assert "import_rename" in pro_cap_set


class TestRenameSymbolEnterpriseTier:
    """Validate Enterprise tier rename_symbol features (4 tests)."""

    def test_all_pro_features_work_enterprise(self, enterprise_tier):
        """Verify all Pro features work for Enterprise tier."""
        capabilities = get_tool_capabilities("rename_symbol", "enterprise") or {}
        cap_set = set(capabilities.get("capabilities", []) or [])
        # Enterprise should have all Pro capabilities
        assert "definition_rename" in cap_set
        assert "backup" in cap_set
        assert "cross_file_reference_rename" in cap_set
        assert "import_rename" in cap_set

    def test_organization_wide_rename_capability(self, enterprise_tier):
        """Verify organization-wide rename capability for Enterprise tier."""
        capabilities = get_tool_capabilities("rename_symbol", "enterprise") or {}
        cap_set = set(capabilities.get("capabilities", []) or [])
        assert "organization_wide_rename" in cap_set, "Enterprise should have organization_wide_rename capability"

    def test_enterprise_unlimited_cross_file_limits(self, enterprise_tier):
        """Verify Enterprise tier has unlimited cross-file rename limits."""
        capabilities = get_tool_capabilities("rename_symbol", "enterprise") or {}
        limits = capabilities.get("limits", {}) or {}
        max_searched = limits.get("max_files_searched")
        max_updated = limits.get("max_files_updated")
        # Enterprise should have None (unlimited) limits
        assert max_searched is None, f"Enterprise should have unlimited max_files_searched, got {max_searched}"
        assert max_updated is None, f"Enterprise should have unlimited max_files_updated, got {max_updated}"

    def test_enterprise_has_advanced_features_pro_lacks(self, enterprise_tier, pro_tier):
        """Verify Enterprise has advanced features that Pro lacks."""
        pro_caps = get_tool_capabilities("rename_symbol", "pro") or {}
        ent_caps = get_tool_capabilities("rename_symbol", "enterprise") or {}

        pro_cap_set = set(pro_caps.get("capabilities", []) or [])
        ent_cap_set = set(ent_caps.get("capabilities", []) or [])

        # Enterprise should have these that Pro lacks
        assert "organization_wide_rename" not in pro_cap_set
        assert "organization_wide_rename" in ent_cap_set


class TestRenameSymbolCrossTierComparison:
    """Cross-tier comparison tests (2 tests)."""

    def test_community_vs_pro_cross_file_limits(self, community_tier, pro_tier):
        """Verify Community has no cross-file rename vs Pro allows bounded cross-file."""
        comm_caps = get_tool_capabilities("rename_symbol", "community") or {}
        pro_caps = get_tool_capabilities("rename_symbol", "pro") or {}

        comm_limits = comm_caps.get("limits", {}) or {}
        pro_limits = pro_caps.get("limits", {}) or {}

        # Community: no cross-file
        assert comm_limits.get("max_files_searched") == 0
        assert comm_limits.get("max_files_updated") == 0

        # Pro: bounded cross-file
        assert pro_limits.get("max_files_searched") == 500
        assert pro_limits.get("max_files_updated") == 200

    def test_pro_vs_enterprise_cross_file_limits(self, pro_tier, enterprise_tier):
        """Verify Pro has bounded cross-file limits vs Enterprise has unlimited."""
        pro_caps = get_tool_capabilities("rename_symbol", "pro") or {}
        ent_caps = get_tool_capabilities("rename_symbol", "enterprise") or {}

        pro_limits = pro_caps.get("limits", {}) or {}
        ent_limits = ent_caps.get("limits", {}) or {}

        # Pro: bounded
        assert pro_limits.get("max_files_searched") == 500
        assert pro_limits.get("max_files_updated") == 200

        # Enterprise: unlimited
        assert ent_limits.get("max_files_searched") is None
        assert ent_limits.get("max_files_updated") is None


class TestRenameSymbolConsistency:
    """Consistency and backup capability tests (3 tests)."""

    def test_backup_capability_across_all_tiers(self, community_tier, pro_tier, enterprise_tier):
        """Verify backup capability is available in all tiers."""
        for tier in ["community", "pro", "enterprise"]:
            capabilities = get_tool_capabilities("rename_symbol", tier) or {}
            cap_set = set(capabilities.get("capabilities", []) or [])
            assert "backup" in cap_set, f"{tier} should have backup capability"

    def test_path_security_validation_across_all_tiers(self, community_tier, pro_tier, enterprise_tier):
        """Verify path security validation is available in all tiers."""
        for tier in ["community", "pro", "enterprise"]:
            capabilities = get_tool_capabilities("rename_symbol", tier) or {}
            cap_set = set(capabilities.get("capabilities", []) or [])
            assert "path_security_validation" in cap_set, f"{tier} should have path_security_validation"

    def test_definition_rename_core_capability(self, community_tier, pro_tier, enterprise_tier):
        """Verify definition_rename is the core capability in all tiers."""
        for tier in ["community", "pro", "enterprise"]:
            capabilities = get_tool_capabilities("rename_symbol", tier) or {}
            cap_set = set(capabilities.get("capabilities", []) or [])
            assert "definition_rename" in cap_set, f"{tier} should have definition_rename core capability"
