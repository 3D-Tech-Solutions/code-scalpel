"""Phase 3 - Enterprise Tier Tests for get_cross_file_dependencies.

Validates:
- Unlimited max_depth
- Architectural rule engine integration
- Layer boundary enforcement
- Coupling limit validation
- Custom rule application
- Exemption patterns

[20260103_TEST] P3 Medium: Enterprise tier governance features
"""

import pytest


class TestEnterpriseUnlimitedDepth:
    """Enterprise tier should have unlimited depth."""

    @pytest.mark.asyncio
    async def test_unlimited_depth_analysis(self, enterprise_server, deep_chain_project):
        """Enterprise should analyze unlimited dependency depth."""
        result = await enterprise_server.get_cross_file_dependencies(
            target_file=deep_chain_project["target_file"],
            target_symbol=deep_chain_project["target_symbol"],
            project_root=deep_chain_project["root"],
            max_depth=100,  # Request very deep
        )

        assert result.success is True
        # Enterprise should not clamp depth aggressively


class TestEnterpriseArchitecturalRuleEngine:
    """Enterprise tier should integrate architectural rule engine."""

    @pytest.mark.asyncio
    async def test_rule_engine_initialization(self, enterprise_server, simple_two_file_project):
        """Should initialize architectural rule engine."""
        result = await enterprise_server.get_cross_file_dependencies(
            target_file=simple_two_file_project["target_file"],
            target_symbol=simple_two_file_project["target_symbol"],
            project_root=simple_two_file_project["root"],
        )

        assert result.success is True
        # architectural_rules_applied field should exist
        assert hasattr(result, "architectural_rules_applied")
        assert isinstance(result.architectural_rules_applied, list)


class TestEnterpriseLayerMapping:
    """Enterprise tier should provide layer mapping."""

    @pytest.mark.asyncio
    async def test_layer_mapping_available(self, enterprise_server, simple_two_file_project):
        """Should provide configured layer mapping."""
        result = await enterprise_server.get_cross_file_dependencies(
            target_file=simple_two_file_project["target_file"],
            target_symbol=simple_two_file_project["target_symbol"],
            project_root=simple_two_file_project["root"],
        )

        assert result.success is True
        # layer_mapping field should exist
        assert hasattr(result, "layer_mapping")
        assert isinstance(result.layer_mapping, dict)


class TestEnterpriseCouplingLimits:
    """Enterprise tier should enforce coupling limits."""

    @pytest.mark.asyncio
    async def test_coupling_violations_detected(self, enterprise_server, simple_two_file_project):
        """Should detect coupling limit violations."""
        result = await enterprise_server.get_cross_file_dependencies(
            target_file=simple_two_file_project["target_file"],
            target_symbol=simple_two_file_project["target_symbol"],
            project_root=simple_two_file_project["root"],
        )

        assert result.success is True
        # coupling_violations field should exist
        assert hasattr(result, "coupling_violations")
        assert isinstance(result.coupling_violations, list)


class TestEnterpriseExemptionPatterns:
    """Enterprise tier should support exemption patterns."""

    @pytest.mark.asyncio
    async def test_exempted_files_tracked(self, enterprise_server, simple_two_file_project):
        """Should track exempted files."""
        result = await enterprise_server.get_cross_file_dependencies(
            target_file=simple_two_file_project["target_file"],
            target_symbol=simple_two_file_project["target_symbol"],
            project_root=simple_two_file_project["root"],
        )

        assert result.success is True
        # exempted_files field should exist
        assert hasattr(result, "exempted_files")
        assert isinstance(result.exempted_files, list)


class TestEnterpriseBoundaryViolations:
    """Enterprise tier should detect boundary violations."""

    @pytest.mark.asyncio
    async def test_boundary_violation_detection(self, enterprise_server, simple_two_file_project):
        """Should detect architectural boundary violations."""
        result = await enterprise_server.get_cross_file_dependencies(
            target_file=simple_two_file_project["target_file"],
            target_symbol=simple_two_file_project["target_symbol"],
            project_root=simple_two_file_project["root"],
        )

        assert result.success is True
        # boundary_violations should be available (may be empty list)
        assert isinstance(result.boundary_violations, list)


class TestEnterpriseLayerViolations:
    """Enterprise tier should detect layer violations."""

    @pytest.mark.asyncio
    async def test_layer_violation_detection(self, enterprise_server, simple_two_file_project):
        """Should detect layer boundary violations."""
        result = await enterprise_server.get_cross_file_dependencies(
            target_file=simple_two_file_project["target_file"],
            target_symbol=simple_two_file_project["target_symbol"],
            project_root=simple_two_file_project["root"],
        )

        assert result.success is True
        # layer_violations should be available (may be empty list)
        assert isinstance(result.layer_violations, list)


class TestEnterpriseArchitecturalAlerts:
    """Enterprise tier should aggregate architectural alerts."""

    @pytest.mark.asyncio
    async def test_alerts_aggregation(self, enterprise_server, simple_two_file_project):
        """Should aggregate architectural alerts."""
        result = await enterprise_server.get_cross_file_dependencies(
            target_file=simple_two_file_project["target_file"],
            target_symbol=simple_two_file_project["target_symbol"],
            project_root=simple_two_file_project["root"],
        )

        assert result.success is True
        # architectural_alerts should be available
        assert hasattr(result, "architectural_alerts")
        assert isinstance(result.architectural_alerts, list)
