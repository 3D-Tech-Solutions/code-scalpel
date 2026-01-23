"""
Tests for generate_unit_tests output metadata fields.

[20260111_TEST] v1.0 validation - Ensure metadata fields are populated correctly
for transparency about tier, framework, and feature settings.
"""

import pytest

from src.code_scalpel.mcp.server import GenerationResult, generate_unit_tests


class TestOutputMetadataFields:
    """Test that output metadata fields are present and correctly populated."""

    @pytest.mark.asyncio
    async def test_basic_generation_includes_metadata(self):
        """Basic pytest generation should include all metadata fields."""
        code = """
def calculate_total(items):
    return sum(items)
"""
        result = await generate_unit_tests(code=code, framework="pytest")

        assert result.success is True
        # Verify metadata fields exist and have correct types
        assert hasattr(result, "tier_applied")
        assert hasattr(result, "framework_used")
        assert hasattr(result, "max_test_cases_limit")
        assert hasattr(result, "data_driven_enabled")
        assert hasattr(result, "bug_reproduction_enabled")

        # Verify values are reasonable
        assert result.tier_applied in ("community", "pro", "enterprise")
        assert result.framework_used == "pytest"
        assert result.data_driven_enabled is False
        assert result.bug_reproduction_enabled is False

    @pytest.mark.asyncio
    async def test_unittest_framework_metadata(self):
        """Unittest framework should be reflected in metadata."""
        code = """
def add(a, b):
    return a + b
"""
        result = await generate_unit_tests(code=code, framework="unittest")

        assert result.success is True
        assert result.framework_used == "unittest"
        assert result.tier_applied in ("community", "pro", "enterprise")

    @pytest.mark.asyncio
    async def test_data_driven_flag_in_metadata(self):
        """Data-driven mode should be reflected in metadata."""
        code = """
def is_positive(x):
    return x > 0
"""
        result = await generate_unit_tests(code=code, framework="pytest", data_driven=True)

        # May succeed or fail based on tier, but metadata should be present
        assert hasattr(result, "data_driven_enabled")
        # If success, data_driven should be True
        if result.success:
            assert result.data_driven_enabled is True

    @pytest.mark.asyncio
    async def test_metadata_present_regardless_of_code_complexity(self):
        """Metadata should be present even with trivial/edge-case code."""
        # Trivial code that may produce minimal tests
        code = "pass"

        result = await generate_unit_tests(code=code, framework="pytest")

        # Metadata should always be populated regardless of outcome
        assert hasattr(result, "tier_applied")
        assert hasattr(result, "framework_used")
        assert hasattr(result, "max_test_cases_limit")
        assert result.framework_used == "pytest"
        assert result.tier_applied in ("community", "pro", "enterprise")


class TestMetadataFieldTypes:
    """Test the data types of metadata fields in the model."""

    def test_test_generation_result_has_metadata_fields(self):
        """GenerationResult model should define all metadata fields."""
        fields = GenerationResult.model_fields

        # Check all metadata fields exist
        assert "tier_applied" in fields
        assert "framework_used" in fields
        assert "max_test_cases_limit" in fields
        assert "data_driven_enabled" in fields
        assert "bug_reproduction_enabled" in fields

    def test_metadata_fields_have_defaults(self):
        """Metadata fields should have sensible defaults."""
        # Create a minimal result with only required fields
        result = GenerationResult(
            success=True,
            function_name="test_func",
            test_count=1,
        )

        # Verify defaults are applied
        assert result.tier_applied == "community"  # Default tier
        assert result.framework_used == "pytest"  # Default framework
        assert result.max_test_cases_limit is None  # No limit by default
        assert result.data_driven_enabled is False  # Disabled by default
        assert result.bug_reproduction_enabled is False  # Disabled by default

    def test_metadata_fields_can_be_set(self):
        """Metadata fields should accept valid values."""
        result = GenerationResult(
            success=True,
            function_name="test_func",
            test_count=5,
            tier_applied="pro",
            framework_used="unittest",
            max_test_cases_limit=20,
            data_driven_enabled=True,
            bug_reproduction_enabled=False,
        )

        assert result.tier_applied == "pro"
        assert result.framework_used == "unittest"
        assert result.max_test_cases_limit == 20
        assert result.data_driven_enabled is True
        assert result.bug_reproduction_enabled is False


class TestFeatureGatingMetadata:
    """Test that feature gating errors include metadata."""

    @pytest.mark.asyncio
    async def test_unsupported_framework_error_has_metadata(self):
        """Unsupported framework error should include metadata."""
        code = """
def simple():
    return 1
"""
        # Try to use an unsupported framework name (not in allowed list)
        result = await generate_unit_tests(code=code, framework="mocha")

        # The framework is not allowed for Community tier
        # But metadata should still be present
        assert hasattr(result, "tier_applied")
        assert hasattr(result, "framework_used")
        if not result.success:
            assert result.framework_used == "mocha"  # Should reflect what was requested
