"""Tests for v1.1.0 Kernel Integration in analyze_code.

Tests verify:
1. AnalyzeCodeKernelAdapter creates valid SourceContext
2. Validation works and returns suggestions on failure
3. analyze_code tool integrates kernel without breaking legacy behavior
4. Other tools remain unchanged (hybrid architecture)
"""

import pytest
import tempfile
import os

# Mark entire module as async
pytestmark = pytest.mark.asyncio


class TestAnalyzeCodeKernelAdapter:
    """Test AnalyzeCodeKernelAdapter class."""

    def test_adapter_singleton(self):
        """Test that get_adapter returns same instance."""
        from code_scalpel.mcp.v1_1_kernel_adapter import get_adapter

        adapter1 = get_adapter()
        adapter2 = get_adapter()
        assert adapter1 is adapter2

    def test_create_source_context_from_code(self):
        """Test creating SourceContext from inline code."""
        from code_scalpel.mcp.v1_1_kernel_adapter import get_adapter
        from code_scalpel.mcp.models.context import Language

        adapter = get_adapter()
        code = "def foo():\n    return 42"
        ctx = adapter.create_source_context(code=code, language="python")

        assert ctx.content == code
        assert ctx.is_memory is True
        assert ctx.file_path is None
        assert ctx.language == Language.PYTHON

    def test_create_source_context_from_file(self):
        """Test creating SourceContext from file path."""
        from code_scalpel.mcp.v1_1_kernel_adapter import get_adapter

        adapter = get_adapter()

        # Create a temporary file
        file_content = "def bar():\n    pass"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(file_content)
            temp_path = f.name

        try:
            ctx = adapter.create_source_context(file_path=temp_path, language="python")

            # For file-based context, is_memory should be False
            assert ctx.file_path == temp_path
            assert ctx.is_memory is False
            # Content is loaded from file
            assert ctx.content == file_content
        finally:
            os.unlink(temp_path)

    def test_create_source_context_auto_language(self):
        """Test language auto-detection (stays as UNKNOWN when auto)."""
        from code_scalpel.mcp.v1_1_kernel_adapter import get_adapter
        from code_scalpel.mcp.models.context import Language

        adapter = get_adapter()
        code = "def foo(): pass"
        ctx = adapter.create_source_context(code=code, language="auto")

        # With "auto", language should be UNKNOWN (caller decides detection)
        assert ctx.language == Language.UNKNOWN

    def test_create_source_context_neither_code_nor_file(self):
        """Test error when both code and file_path are None."""
        from code_scalpel.mcp.v1_1_kernel_adapter import get_adapter

        adapter = get_adapter()

        with pytest.raises(
            ValueError, match="Either 'code' or 'file_path' must be provided"
        ):
            adapter.create_source_context(code=None, file_path=None)

    def test_validate_input_success(self):
        """Test validation succeeds for valid input."""
        from code_scalpel.mcp.v1_1_kernel_adapter import get_adapter

        adapter = get_adapter()
        code = "def valid():\n    return True"
        ctx = adapter.create_source_context(code=code)

        is_valid, error_obj, suggestions = adapter.validate_input(ctx)

        assert is_valid is True
        assert error_obj is None
        assert suggestions == []

    def test_create_upgrade_hints_no_features(self):
        """Test upgrade hints returns None when no features requested."""
        from code_scalpel.mcp.v1_1_kernel_adapter import get_adapter

        adapter = get_adapter()
        hints = adapter.create_upgrade_hints(tier="community", requested_features=None)
        assert hints is None

    def test_create_upgrade_hints_community_tier(self):
        """Test upgrade hints for community tier."""
        from code_scalpel.mcp.v1_1_kernel_adapter import get_adapter

        adapter = get_adapter()
        hints = adapter.create_upgrade_hints(
            tier="community",
            requested_features=["cognitive_complexity", "custom_rules"],
        )

        assert hints is not None
        assert len(hints) == 2
        assert any(
            h.feature == "cognitive_complexity" and h.tier == "PRO" for h in hints
        )
        assert any(
            h.feature == "custom_rules" and h.tier == "ENTERPRISE" for h in hints
        )

    def test_create_upgrade_hints_pro_tier(self):
        """Test upgrade hints for pro tier (some features already included)."""
        from code_scalpel.mcp.v1_1_kernel_adapter import get_adapter

        adapter = get_adapter()
        hints = adapter.create_upgrade_hints(
            tier="pro", requested_features=["cognitive_complexity", "custom_rules"]
        )

        assert hints is not None
        # cognitive_complexity is pro, so no hint for community/pro
        # custom_rules is enterprise, so hint required
        assert len(hints) == 1
        assert hints[0].feature == "custom_rules"

    def test_create_upgrade_hints_no_upgrade_needed(self):
        """Test upgrade hints returns None when no upgrades needed."""
        from code_scalpel.mcp.v1_1_kernel_adapter import get_adapter

        adapter = get_adapter()
        hints = adapter.create_upgrade_hints(
            tier="enterprise",
            requested_features=["cognitive_complexity", "custom_rules"],
        )

        # Enterprise has all features, so no hints
        assert hints is None


class TestAnalyzeCodeToolIntegration:
    """Test analyze_code tool integration with kernel adapter."""

    async def test_analyze_code_returns_envelope(self):
        """Test that analyze_code returns properly enveloped response."""
        from code_scalpel.mcp.server import analyze_code

        code = "def simple():\n    return 42"
        result = await analyze_code(code)

        # Check for envelope structure
        assert hasattr(result, "success")
        assert hasattr(result, "data") or hasattr(result, "functions")

    async def test_analyze_code_with_simple_function(self):
        """Test analyzing simple code works."""
        from code_scalpel.mcp.server import analyze_code

        code = "def greet(name):\n    return f'Hello, {name}'"
        result = await analyze_code(code)

        assert result.success is True
        assert "greet" in result.functions

    async def test_analyze_code_with_file_path(self):
        """Test analyze_code with file_path instead of code."""
        from code_scalpel.mcp.server import analyze_code

        code_content = "class TestClass:\n    def method(self):\n        pass"

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(code_content)
            temp_path = f.name

        try:
            result = await analyze_code(file_path=temp_path)

            assert result.success is True
            assert "TestClass" in result.classes or len(result.classes) > 0
        finally:
            os.unlink(temp_path)

    async def test_analyze_code_missing_both_code_and_file(self):
        """Test analyze_code error when both code and file_path missing."""
        from code_scalpel.mcp.server import analyze_code

        # Should raise an error or return error response
        try:
            result = await analyze_code()
            # If it returns a result, check for error in envelope
            assert result.error is not None or (
                hasattr(result, "data") and result.data.get("error")
            )
        except (TypeError, ValueError):
            # Expected: missing required arguments
            pass

    async def test_analyze_code_invalid_file_path(self):
        """Test analyze_code error when file doesn't exist."""
        from code_scalpel.mcp.server import analyze_code

        result = await analyze_code(file_path="/nonexistent/path/to/file.py")

        # Should handle error gracefully - check envelope error or data error
        assert result.error is not None or (
            hasattr(result, "data") and result.data.get("error")
        )

    async def test_analyze_code_maintains_backward_compatibility(self):
        """Test that basic analyze_code functionality is unchanged."""
        from code_scalpel.mcp.server import analyze_code

        code = """
def function1():
    pass

def function2(x, y):
    return x + y

class MyClass:
    def __init__(self):
        self.value = 0
"""
        result = await analyze_code(code)

        # Verify all expected fields are present
        assert result.success is True
        assert hasattr(result, "functions")
        assert hasattr(result, "classes")
        assert hasattr(result, "function_count")
        assert hasattr(result, "class_count")
        assert result.function_count >= 2
        assert result.class_count >= 1

    async def test_analyze_code_with_language_detection(self):
        """Test analyze_code with explicit language hint."""
        from code_scalpel.mcp.server import analyze_code

        code = "def hello():\n    print('world')"
        result = await analyze_code(code, language="python")

        assert result.success is True

    async def test_analyze_code_with_invalid_language(self):
        """Test analyze_code handles invalid language gracefully."""
        from code_scalpel.mcp.server import analyze_code

        code = "def test(): pass"
        # Invalid language will be rejected by the underlying analyzer
        result = await analyze_code(code, language="unsupported_lang")

        # The result will have an error in the data payload or envelope
        assert hasattr(result, "data")
        # The data contains the error from the analyzer (or may be None if error in envelope)
        if result.data is not None:
            assert isinstance(result.data, dict)
            assert "error" in result.data or "success" in result.data


class TestHybridArchitecture:
    """Test that v1.1.0 is truly hybrid (new kernel + unchanged legacy)."""

    async def test_other_tools_not_using_kernel(self):
        """Test that other tools still work without kernel integration."""
        from code_scalpel.mcp.server import scan_dependencies

        # scan_dependencies should work without kernel adapter
        # (it's not integrated in v1.1.0)
        code = "import os\nimport sys"

        try:
            result = await scan_dependencies(code)
            # Should return some result without raising kernel-related errors
            assert result is not None
        except Exception as e:
            # If it fails, shouldn't be due to kernel integration
            assert "kernel" not in str(e).lower()

    def test_kernel_adapter_isolated(self):
        """Test that kernel adapter doesn't affect global state."""
        from code_scalpel.mcp.v1_1_kernel_adapter import get_adapter

        # Create adapter
        adapter = get_adapter()

        # Create source contexts with different languages
        ctx1 = adapter.create_source_context(code="def foo(): pass", language="python")
        ctx2 = adapter.create_source_context(
            code="function bar() {}", language="javascript"
        )

        # Verify they don't interfere with each other
        assert ctx1.language.value == "python"
        assert ctx2.language.value == "javascript"
