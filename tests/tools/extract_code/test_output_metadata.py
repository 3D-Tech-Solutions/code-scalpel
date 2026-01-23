"""
Tests for extract_code output metadata fields.

[20260111_TEST] v1.0 validation - Ensure metadata fields are populated correctly
for transparency about tier, language, and feature availability.
"""

import pytest

from code_scalpel.mcp.models.core import ContextualExtractionResult
from code_scalpel.mcp.tools.extraction import extract_code


class TestOutputMetadataFields:
    """Test that output metadata fields are present and correctly populated."""

    @pytest.mark.asyncio
    async def test_python_extraction_includes_metadata(self):
        """Python extraction should include all metadata fields."""
        code = """
def calculate_total(items):
    return sum(item.price for item in items)
"""
        result = await extract_code(
            target_type="function",
            target_name="calculate_total",
            code=code,
        )

        assert result.success is True
        # Verify metadata fields exist and have correct types
        assert hasattr(result, "tier_applied")
        assert hasattr(result, "language_detected")
        assert hasattr(result, "cross_file_deps_enabled")
        assert hasattr(result, "max_depth_applied")

        # Verify values are reasonable
        assert result.tier_applied in ("community", "pro", "enterprise")
        assert result.language_detected == "python"
        assert isinstance(result.cross_file_deps_enabled, bool)
        # max_depth_applied can be int or None (None means unlimited)
        assert result.max_depth_applied is None or isinstance(result.max_depth_applied, int)

    @pytest.mark.asyncio
    async def test_javascript_extraction_includes_metadata(self):
        """JavaScript extraction should include language metadata."""
        code = """
function calculateTotal(items) {
    return items.reduce((sum, item) => sum + item.price, 0);
}
"""
        result = await extract_code(
            target_type="function",
            target_name="calculateTotal",
            code=code,
            language="javascript",
        )

        assert result.success is True
        assert result.language_detected == "javascript"
        assert result.tier_applied in ("community", "pro", "enterprise")
        # Cross-file deps not yet supported for non-Python
        assert result.cross_file_deps_enabled is False

    @pytest.mark.asyncio
    async def test_typescript_extraction_includes_metadata(self):
        """TypeScript extraction should include language metadata."""
        code = """
function greet(name: string): string {
    return `Hello, ${name}!`;
}
"""
        result = await extract_code(
            target_type="function",
            target_name="greet",
            code=code,
            language="typescript",
        )

        assert result.success is True
        assert result.language_detected == "typescript"
        assert result.tier_applied in ("community", "pro", "enterprise")

    @pytest.mark.asyncio
    async def test_metadata_in_error_responses(self):
        """Error responses should include metadata defaults."""
        # Try to extract a non-existent function
        code = """
def existing_function():
    pass
"""
        result = await extract_code(
            target_type="function",
            target_name="non_existent_function",
            code=code,
        )

        # Should fail but still have metadata
        assert result.success is False
        assert hasattr(result, "tier_applied")
        assert hasattr(result, "language_detected")
        # Defaults should be present
        assert result.tier_applied in ("community", "pro", "enterprise")


class TestMetadataFieldTypes:
    """Test the data types of metadata fields in the model."""

    def test_contextual_extraction_result_has_metadata_fields(self):
        """ContextualExtractionResult model should define all metadata fields."""
        fields = ContextualExtractionResult.model_fields

        # Check all metadata fields exist
        assert "tier_applied" in fields
        assert "language_detected" in fields
        assert "cross_file_deps_enabled" in fields
        assert "max_depth_applied" in fields

    def test_metadata_fields_have_defaults(self):
        """Metadata fields should have sensible defaults."""
        # Create a minimal result with only required fields
        result = ContextualExtractionResult(
            success=True,
            target_name="test",
            target_code="def test(): pass",
            context_code="",
            full_code="def test(): pass",
        )

        # Verify defaults are applied
        assert result.tier_applied == "community"  # Default tier
        assert result.language_detected is None  # No language specified
        assert result.cross_file_deps_enabled is False  # Disabled by default
        assert result.max_depth_applied is None  # None means not specified

    def test_metadata_fields_can_be_set(self):
        """Metadata fields should accept valid values."""
        result = ContextualExtractionResult(
            success=True,
            target_name="test",
            target_code="def test(): pass",
            context_code="",
            full_code="def test(): pass",
            tier_applied="pro",
            language_detected="python",
            cross_file_deps_enabled=True,
            max_depth_applied=3,
        )

        assert result.tier_applied == "pro"
        assert result.language_detected == "python"
        assert result.cross_file_deps_enabled is True
        assert result.max_depth_applied == 3
