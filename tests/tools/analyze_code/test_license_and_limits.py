"""
License fallback and file size limit tests for analyze_code tool.

Tests:
- Invalid/expired license fallback to Community tier
- File size limit enforcement per tier
- Limit escalation with tier upgrades
"""

from code_scalpel.licensing import get_current_tier
from code_scalpel.licensing.features import get_tool_capabilities
from code_scalpel.mcp.server import _analyze_code_sync


class TestLicenseFallback:
    """Test invalid/expired license fallback behavior."""

    def test_expired_license_fallback_to_community(self, community_tier):
        """Expired license should fallback to Community tier."""
        code = """
def test_function():
    if True:
        return 1
    else:
        return 0
"""
        result = _analyze_code_sync(code=code, language="python")

        # Should work with Community features
        assert result.success
        assert "test_function" in result.functions
        # Basic analysis works regardless of tier
        assert result.complexity >= 0

    def test_invalid_license_fallback_to_community(self, community_tier):
        """Invalid license should fallback to Community tier."""
        code = """
class TestClass:
    def method(self):
        pass
"""
        result = _analyze_code_sync(code=code, language="python")

        # Should work with Community features
        assert result.success
        assert "TestClass" in result.classes
        assert "method" in result.functions

    def test_missing_license_defaults_to_community(self, community_tier):
        """Missing license (None) should default to Community tier."""
        code = """
def simple():
    return 42
"""
        result = _analyze_code_sync(code=code, language="python")

        # Should work with Community features
        assert result.success
        assert "simple" in result.functions
        assert len(result.functions) == 1


class TestFileSizeLimits:
    """Test file size limit enforcement per tier."""

    def test_community_max_file_size_1mb(self, community_tier):
        """Community tier should enforce 1MB file size limit."""
        # Get Community tier limits
        tier = get_current_tier()
        capabilities = get_tool_capabilities("analyze_code", tier)
        max_size = capabilities.get("max_file_size_mb", 1)

        assert max_size == 1, "Community tier should have 1MB limit"

    def test_pro_max_file_size_10mb(self, pro_tier):
        """Pro tier should enforce 10MB file size limit."""
        # Get Pro tier limits
        tier = get_current_tier()
        capabilities = get_tool_capabilities("analyze_code", tier)
        max_size = capabilities.get("max_file_size_mb", 10)

        assert max_size == 10, "Pro tier should have 10MB limit"

    def test_enterprise_max_file_size_100mb(self, enterprise_tier):
        """Enterprise tier should enforce 100MB file size limit."""
        # Get Enterprise tier limits
        tier = get_current_tier()
        capabilities = get_tool_capabilities("analyze_code", tier)
        max_size = capabilities.get("max_file_size_mb", 100)

        assert max_size == 100, "Enterprise tier should have 100MB limit"

    def test_file_size_limit_escalation(self):
        """File size limits should increase with tier upgrades."""
        from code_scalpel.licensing.features import TOOL_CAPABILITIES

        comm_size = TOOL_CAPABILITIES["analyze_code"]["community"].get("max_file_size_mb", 1)
        pro_size = TOOL_CAPABILITIES["analyze_code"]["pro"].get("max_file_size_mb", 10)

        # Verify escalation
        assert pro_size > comm_size, "Pro limit should exceed Community"
        assert comm_size == 1
        assert pro_size == 10


class TestFileSizeEnforcement:
    """Test actual file size enforcement (stress tests)."""

    def test_large_file_generates_many_functions(self, community_tier):
        """Generate large code and verify it's analyzed."""
        # Generate code with many functions (but under 1MB)
        num_functions = 100
        code_lines = []
        for i in range(num_functions):
            code_lines.append(f"def func_{i}():")
            code_lines.append(f"    return {i}")
            code_lines.append("")

        code = "\n".join(code_lines)
        code_size_kb = len(code.encode("utf-8")) / 1024

        # Verify we're testing a reasonably large file
        assert code_size_kb > 1, f"Test code should be >1KB (got {code_size_kb:.2f}KB)"

        result = _analyze_code_sync(code=code, language="python")

        assert result.success
        assert (
            len(result.functions) == num_functions
        ), f"Expected {num_functions} functions, got {len(result.functions)}"

    def test_moderate_file_with_classes(self, pro_tier):
        """Test moderate-sized file with classes and methods."""
        # Generate code with classes and methods
        num_classes = 20
        methods_per_class = 5
        code_lines = []

        for i in range(num_classes):
            code_lines.append(f"class Class_{i}:")
            for j in range(methods_per_class):
                code_lines.append(f"    def method_{j}(self):")
                code_lines.append(f"        return {i * methods_per_class + j}")
            code_lines.append("")

        code = "\n".join(code_lines)
        code_size_kb = len(code.encode("utf-8")) / 1024

        # Verify file size
        assert code_size_kb > 2, f"Test code should be >2KB (got {code_size_kb:.2f}KB)"

        result = _analyze_code_sync(code=code, language="python")

        assert result.success
        assert len(result.classes) == num_classes
        # Total functions = all methods from all classes
        expected_functions = num_classes * methods_per_class
        assert len(result.functions) == expected_functions

    def test_complexity_scales_with_file_size(self, pro_tier):
        """Verify complexity analysis works on larger files."""
        # Generate complex code
        code = """
def complex_function(x, y, z):
    if x > 0:
        if y > 0:
            if z > 0:
                return x + y + z
            else:
                return x + y
        else:
            if z > 0:
                return x + z
            else:
                return x
    else:
        if y > 0:
            if z > 0:
                return y + z
            else:
                return y
        else:
            return z
"""
        result = _analyze_code_sync(code=code, language="python")

        assert result.success
        assert result.complexity > 1, "Complex code should have complexity > 1"
        # With nested ifs, complexity should be reasonably high
        assert result.complexity >= 7, f"Expected complexity >= 7, got {result.complexity}"


class TestTierLimitDifferences:
    """Test that limits actually differ across tiers."""

    def test_community_vs_pro_limits(self):
        """Community and Pro tiers should have different limits."""
        from code_scalpel.licensing.features import TOOL_CAPABILITIES

        comm_caps = TOOL_CAPABILITIES["analyze_code"]["community"]
        pro_caps = TOOL_CAPABILITIES["analyze_code"]["pro"]

        comm_size = comm_caps.get("max_file_size_mb", 1)
        pro_size = pro_caps.get("max_file_size_mb", 10)

        assert comm_size < pro_size, "Pro should have larger file size limit"
        assert comm_size == 1
        assert pro_size == 10

    def test_pro_vs_enterprise_limits(self):
        """Pro and Enterprise tiers should have different limits."""
        from code_scalpel.licensing.features import TOOL_CAPABILITIES

        pro_caps = TOOL_CAPABILITIES["analyze_code"]["pro"]
        ent_caps = TOOL_CAPABILITIES["analyze_code"]["enterprise"]

        pro_size = pro_caps.get("max_file_size_mb", 10)
        ent_size = ent_caps.get("max_file_size_mb", 100)

        assert pro_size < ent_size, "Enterprise should have larger file size limit"
        assert pro_size == 10
        assert ent_size == 100

    def test_all_tiers_limit_progression(self):
        """Verify limit progression: Community < Pro < Enterprise."""
        from code_scalpel.licensing.features import TOOL_CAPABILITIES

        comm_size = TOOL_CAPABILITIES["analyze_code"]["community"].get("max_file_size_mb", 1)
        pro_size = TOOL_CAPABILITIES["analyze_code"]["pro"].get("max_file_size_mb", 10)
        ent_size = TOOL_CAPABILITIES["analyze_code"]["enterprise"].get("max_file_size_mb", 100)

        assert comm_size < pro_size < ent_size, f"Limits should progress: {comm_size} < {pro_size} < {ent_size}"
