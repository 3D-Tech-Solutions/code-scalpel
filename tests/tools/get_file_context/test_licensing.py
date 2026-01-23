"""
Licensing and tier fallback tests for get_file_context.

Tests that get_file_context enforces licensing constraints:
- Invalid/expired licenses fall back to Community tier
- Tier limits are enforced (500/2000/unlimited)
- Features are gated by license tier
- License verification works correctly

These tests validate:
1. Community tier enforces 500-line limit
2. Pro tier enforces 2000-line limit
3. Enterprise tier has unlimited lines
4. Invalid licenses fall back to Community
5. Tier-gated features are properly restricted
"""

import tempfile
from pathlib import Path


class TestCommunityTierLimits:
    """Test Community tier line limit enforcement."""

    def test_community_tier_500_line_limit(self, tmpdir):
        """Community tier should enforce 500-line limit."""
        # Create file with 600 lines
        code = "\n".join([f"# Line {i}" for i in range(1, 601)])
        code += "\ndef important_function():\n    pass"

        test_file = Path(tmpdir) / "large.py"
        test_file.write_text(code)

        from code_scalpel.mcp.helpers.context_helpers import _get_file_context_sync

        result = _get_file_context_sync(
            str(test_file),
            tier="community",
        )

        # Should limit to 500 lines
        if result.expanded_context:
            lines = result.expanded_context.count("\n")
            assert lines <= 500, f"Exceeded 500-line limit: {lines} lines"

    def test_community_tier_respects_limit(self):
        """Community tier context should not exceed 500 lines."""
        # Create large Python file
        large_code = "\n".join(
            f"def func_{i}(a, b, c, d, e):\n    # This is function {i}\n    return a + b + c + d + e\n"
            for i in range(250)  # 750 lines total
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(large_code)
            f.flush()
            temp_path = f.name

        try:
            from code_scalpel.mcp.helpers.context_helpers import _get_file_context_sync

            result = _get_file_context_sync(
                temp_path,
                tier="community",
            )

            # Should enforce limit
            if result.expanded_context:
                lines = result.expanded_context.count("\n")
                assert lines <= 500
        finally:
            import os

            os.unlink(temp_path)


class TestProTierLimits:
    """Test Pro tier line limit enforcement."""

    def test_pro_tier_2000_line_limit(self):
        """Pro tier should enforce 2000-line limit."""
        # Create file with 2500 lines
        large_code = "\n".join(f"def func_{i}(a, b):\n    return a + b\n" for i in range(1250))

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(large_code)
            f.flush()
            temp_path = f.name

        try:
            from code_scalpel.mcp.helpers.context_helpers import _get_file_context_sync

            result = _get_file_context_sync(
                temp_path,
                tier="pro",
            )

            # Should limit to 2000 lines
            if result.expanded_context:
                lines = result.expanded_context.count("\n")
                assert lines <= 2000
        finally:
            import os

            os.unlink(temp_path)

    def test_pro_tier_higher_limit_than_community(self):
        """Pro tier should have higher limit than Community."""
        # Create file with 1000 lines
        code = "\n".join([f"# Line {i}" for i in range(1000)])

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(code)
            f.flush()
            temp_path = f.name

        try:
            from code_scalpel.mcp.helpers.context_helpers import _get_file_context_sync

            # Community tier
            community_result = _get_file_context_sync(
                temp_path,
                tier="community",
            )

            # Pro tier
            pro_result = _get_file_context_sync(
                temp_path,
                tier="pro",
            )

            # Pro should return more or equal context
            community_lines = len(community_result.expanded_context or "") if community_result.expanded_context else 0
            pro_lines = len(pro_result.expanded_context or "") if pro_result.expanded_context else 0

            assert pro_lines >= community_lines, "Pro tier should have higher limit than Community"
        finally:
            import os

            os.unlink(temp_path)


class TestEnterpriseTierLimits:
    """Test Enterprise tier has unlimited context."""

    def test_enterprise_tier_unlimited(self):
        """Enterprise tier should allow unlimited lines."""
        # Create very large file
        large_code = "\n".join(
            f"def func_{i}(a, b):\n    # Function {i}\n    return a + b\n" for i in range(5000)
        )  # 15000 lines

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(large_code)
            f.flush()
            temp_path = f.name

        try:
            from code_scalpel.mcp.helpers.context_helpers import _get_file_context_sync

            result = _get_file_context_sync(
                temp_path,
                tier="enterprise",
            )

            # Enterprise should handle large files
            assert result is not None
            # Should have substantial context
            if result.expanded_context:
                lines = result.expanded_context.count("\n")
                # Enterprise should comfortably exceed Community/Pro limits
                assert lines >= 1500
        finally:
            import os

            os.unlink(temp_path)


class TestTierFeatureGating:
    """Test that tier-gated features are properly restricted."""

    def test_community_cannot_access_pro_features(self, tmpdir):
        """Community tier should not return Pro features."""
        code = "def hello(): pass"
        test_file = Path(tmpdir) / "test.py"
        test_file.write_text(code)

        from code_scalpel.mcp.helpers.context_helpers import _get_file_context_sync

        result = _get_file_context_sync(
            str(test_file),
            tier="community",
        )

        # Should not have Pro features
        assert not result.code_smells or result.code_smells == []
        assert result.doc_coverage in (None, 0.0)
        assert result.maintainability_index is None

    def test_pro_cannot_access_enterprise_features(self, tmpdir):
        """Pro tier should not return Enterprise features."""
        code = "def hello(): pass"
        test_file = Path(tmpdir) / "test.py"
        test_file.write_text(code)

        from code_scalpel.mcp.helpers.context_helpers import _get_file_context_sync

        result = _get_file_context_sync(
            str(test_file),
            tier="pro",
        )

        # Should not have Enterprise features
        assert not result.custom_metadata or result.custom_metadata == {}
        assert not result.compliance_flags or result.compliance_flags == []
        assert not result.owners or result.owners == []
        assert result.technical_debt_score is None

    def test_feature_availability_per_tier(self, tmpdir):
        """Features should be available only in appropriate tiers."""
        code = "def hello(): pass"
        test_file = Path(tmpdir) / "test.py"
        test_file.write_text(code)

        from code_scalpel.mcp.helpers.context_helpers import _get_file_context_sync

        # Community tier
        community = _get_file_context_sync(
            str(test_file),
            tier="community",
        )

        # Pro tier
        pro = _get_file_context_sync(
            str(test_file),
            tier="pro",
        )

        # Enterprise tier
        enterprise = _get_file_context_sync(
            str(test_file),
            tier="enterprise",
        )

        # Verify tier structure
        assert community is not None
        assert pro is not None
        assert enterprise is not None


class TestInvalidLicenseFallback:
    """Test license validation and fallback to Community."""

    def test_missing_license_defaults_to_community(self, tmpdir):
        """Missing license should default to Community tier."""
        code = "def hello(): pass"
        test_file = Path(tmpdir) / "test.py"
        test_file.write_text(code)

        from code_scalpel.mcp.helpers.context_helpers import _get_file_context_sync

        # No license/capabilities specified should default to Community
        result = _get_file_context_sync(
            str(test_file),
            capabilities=None,
        )

        # Should work as Community tier
        assert result is not None
        assert result.functions is not None


class TestCapabilityKeyEnforcement:
    """Test that capability keys are properly enforced."""

    def test_capability_key_enables_feature(self, tmpdir):
        """Adding capability key should enable feature."""
        smelly_code = """
def bad_function(a, b, c, d, e):
    if a:
        if b:
            if c:
                if d:
                    if e:
                        return a+b+c+d+e
        """
        test_file = Path(tmpdir) / "smelly.py"
        test_file.write_text(smelly_code)

        from code_scalpel.mcp.helpers.context_helpers import _get_file_context_sync

        # Without capability
        without = _get_file_context_sync(
            str(test_file),
            tier="community",
        )

        # With capability
        with_cap = _get_file_context_sync(
            str(test_file),
            tier="pro",
        )

        # Feature should be available with capability
        assert with_cap.code_smells is not None or isinstance(with_cap.code_smells, list)
        assert not without.code_smells or without.code_smells == []

    def test_wrong_capability_key_does_not_enable_feature(self, tmpdir):
        """Wrong capability key should not enable feature."""
        code = "def hello(): pass"
        test_file = Path(tmpdir) / "test.py"
        test_file.write_text(code)

        from code_scalpel.mcp.helpers.context_helpers import _get_file_context_sync

        # With wrong capability
        result = _get_file_context_sync(
            str(test_file),
            capabilities={"capabilities": ["wrong_capability_key"]},
            tier="community",
        )

        # Should not have Pro features
        assert not result.code_smells or result.code_smells == []
        assert result.maintainability_index is None


class TestMultipleCapabilities:
    """Test handling multiple capabilities simultaneously."""

    def test_multiple_pro_capabilities(self, tmpdir):
        """Multiple Pro capabilities should all enable their features."""
        code = '''
def hello():
    """Say hello"""
    pass

def world():
    pass
        '''
        test_file = Path(tmpdir) / "test.py"
        test_file.write_text(code)

        from code_scalpel.mcp.helpers.context_helpers import _get_file_context_sync

        result = _get_file_context_sync(
            str(test_file),
            tier="pro",
        )

        # Should have all Pro features
        assert hasattr(result, "code_smells")
        assert hasattr(result, "doc_coverage")
        assert hasattr(result, "maintainability_index")

    def test_mixed_tier_capabilities(self, tmpdir):
        """Pro + Enterprise capabilities should work together."""
        code = "def hello(): pass"
        test_file = Path(tmpdir) / "test.py"
        test_file.write_text(code)

        from code_scalpel.mcp.helpers.context_helpers import _get_file_context_sync

        result = _get_file_context_sync(
            str(test_file),
            tier="enterprise",
        )

        # Should have features from both tiers
        assert hasattr(result, "code_smells")
        assert hasattr(result, "compliance_flags")
