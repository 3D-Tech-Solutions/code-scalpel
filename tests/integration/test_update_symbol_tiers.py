"""Tests for update_symbol tier features per roadmap v1.0.

[20250101_TEST] Tests for:
- Community: Session limit enforcement (10 updates/session)
- Community: Polyglot support (Python/JS/TS/Java)
- Pro: Pre/post hooks
- Pro: Cross-file updates
- Enterprise: Code review approval
- Enterprise: Compliance checking
- Enterprise: Audit trail
"""

from unittest.mock import MagicMock

import pytest

from code_scalpel.licensing.features import get_tool_capabilities

# Test imports
from code_scalpel.mcp.server import (
    _SESSION_AUDIT_TRAIL,
    _SESSION_UPDATE_COUNTS,
    _add_audit_entry,
    _check_code_review_approval,
    _check_compliance,
    _get_audit_trail,
    _get_session_update_count,
    _increment_session_update_count,
    _run_post_update_hook,
    _run_pre_update_hook,
)
from code_scalpel.surgery.surgical_patcher import (
    PatchLanguage,
    PolyglotPatcher,
    SurgicalPatcher,
)


class TestSessionTracking:
    """Test session update counting for Community tier limits."""

    def setup_method(self):
        """Reset session state before each test."""
        _SESSION_UPDATE_COUNTS.clear()
        _SESSION_AUDIT_TRAIL.clear()

    def test_session_count_starts_at_zero(self):
        """Test that session count starts at zero."""
        assert _get_session_update_count("update_symbol") == 0

    def test_increment_session_count(self):
        """Test incrementing session count."""
        count1 = _increment_session_update_count("update_symbol")
        assert count1 == 1

        count2 = _increment_session_update_count("update_symbol")
        assert count2 == 2

    def test_separate_tool_counts(self):
        """Test that different tools have separate counts."""
        _increment_session_update_count("update_symbol")
        _increment_session_update_count("update_symbol")
        _increment_session_update_count("rename_symbol")

        assert _get_session_update_count("update_symbol") == 2
        assert _get_session_update_count("rename_symbol") == 1
        assert _get_session_update_count("other_tool") == 0


class TestAuditTrail:
    """Test Enterprise tier audit trail functionality."""

    def setup_method(self):
        """Reset audit trail before each test."""
        _SESSION_AUDIT_TRAIL.clear()

    def test_add_audit_entry(self):
        """Test adding audit entries."""
        _add_audit_entry(
            tool_name="update_symbol",
            file_path="/project/src/utils.py",
            target_name="calculate_tax",
            operation="replace",
            success=True,
            tier="enterprise",
            metadata={"lines_before": 10, "lines_after": 15},
        )

        trail = _get_audit_trail()
        assert len(trail) == 1

        entry = trail[0]
        assert entry["tool"] == "update_symbol"
        assert entry["file_path"] == "/project/src/utils.py"
        assert entry["target_name"] == "calculate_tax"
        assert entry["operation"] == "replace"
        assert entry["success"] is True
        assert entry["tier"] == "enterprise"
        assert entry["metadata"]["lines_before"] == 10
        assert "timestamp" in entry

    def test_audit_trail_is_copy(self):
        """Test that get_audit_trail returns a copy."""
        _add_audit_entry(
            tool_name="test",
            file_path="/test.py",
            target_name="test",
            operation="test",
            success=True,
            tier="enterprise",
        )

        trail = _get_audit_trail()
        trail.clear()

        # Original should not be affected
        assert len(_get_audit_trail()) == 1


class TestComplianceCheck:
    """Test Enterprise tier compliance checking."""

    @pytest.mark.asyncio
    async def test_compliance_detects_hardcoded_secrets(self):
        """Test that compliance check detects hardcoded secrets."""
        code_with_secret = """
def connect():
    password = "supersecret123"
    return database.connect(password)
"""
        result = await _check_compliance("/test.py", "connect", code_with_secret)

        assert result["compliant"] is True  # Warnings don't fail compliance
        assert len(result["warnings"]) > 0
        assert any("password" in w.lower() for w in result["warnings"])

    @pytest.mark.asyncio
    async def test_compliance_detects_eval(self):
        """Test that compliance check detects eval usage."""
        code_with_eval = """
def process(data):
    return eval(data)
"""
        result = await _check_compliance("/test.py", "process", code_with_eval)

        assert len(result["warnings"]) > 0
        assert any("eval" in w.lower() for w in result["warnings"])

    @pytest.mark.asyncio
    async def test_compliance_passes_clean_code(self):
        """Test that clean code passes compliance."""
        clean_code = """
def add(a, b):
    return a + b
"""
        result = await _check_compliance("/test.py", "add", clean_code)

        assert result["compliant"] is True
        assert len(result["violations"]) == 0


class TestCodeReviewApproval:
    """Test Enterprise tier code review approval."""

    @pytest.mark.asyncio
    async def test_approval_for_sensitive_path(self):
        """Test that sensitive paths are flagged."""
        result = await _check_code_review_approval(
            "/project/security/auth.py",
            "authenticate",
            "function",
            "def authenticate(): pass",
        )

        assert result["requires_review"] is True
        assert "security" in result.get("reason", "").lower()

    @pytest.mark.asyncio
    async def test_approval_for_normal_path(self):
        """Test that normal paths don't require review."""
        result = await _check_code_review_approval(
            "/project/utils/helpers.py",
            "format_date",
            "function",
            "def format_date(): pass",
        )

        assert result["approved"] is True


class TestPrePostHooks:
    """Test Pro tier pre/post update hooks."""

    @pytest.mark.asyncio
    async def test_pre_hook_default_continues(self):
        """Test that pre-hook defaults to continue."""
        result = await _run_pre_update_hook(
            "/nonexistent/path.py",
            "test_func",
            "function",
            "def test_func(): pass",
        )

        assert result["continue"] is True

    @pytest.mark.asyncio
    async def test_post_hook_returns_warnings(self):
        """Test that post-hook returns warnings list."""
        mock_result = MagicMock()
        mock_result.success = True

        result = await _run_post_update_hook(
            "/nonexistent/path.py",
            "test_func",
            "function",
            mock_result,
        )

        assert "warnings" in result


class TestPolyglotSupport:
    """Test Community tier polyglot support (Python/JS/TS/Java)."""

    def test_python_patcher_creation(self):
        """Test Python patcher creation."""
        code = "def hello(): return 'world'"
        patcher = SurgicalPatcher(code)
        assert patcher is not None

    def test_javascript_patcher_creation(self):
        """Test JavaScript patcher creation."""
        code = "function hello() { return 'world'; }"
        patcher = PolyglotPatcher(code, PatchLanguage.JAVASCRIPT)
        assert patcher is not None

    def test_typescript_patcher_creation(self):
        """Test TypeScript patcher creation."""
        code = "function hello(): string { return 'world'; }"
        patcher = PolyglotPatcher(code, PatchLanguage.TYPESCRIPT)
        assert patcher is not None

    def test_java_patcher_creation(self):
        """Test Java patcher creation."""
        code = """
public class Hello {
    public String hello() {
        return "world";
    }
}
"""
        patcher = PolyglotPatcher(code, PatchLanguage.JAVA)
        assert patcher is not None


class TestJavaScriptUpdate:
    """Test JavaScript function updates."""

    def test_update_js_function(self):
        """Test updating a JavaScript function."""
        code = """
function oldFunc() {
    return 1;
}

function otherFunc() {
    return 2;
}
"""
        patcher = PolyglotPatcher(code, PatchLanguage.JAVASCRIPT)

        new_code = """function oldFunc() {
    return 42;
}"""

        result = patcher.update_function("oldFunc", new_code)

        assert result.success is True
        modified = patcher.get_modified_code()
        assert "return 42" in modified
        assert "return 2" in modified  # otherFunc preserved

    def test_update_js_arrow_function(self):
        """Test updating a JavaScript arrow function."""
        code = """
const add = (a, b) => {
    return a + b;
};

const multiply = (a, b) => a * b;
"""
        patcher = PolyglotPatcher(code, PatchLanguage.JAVASCRIPT)

        # List symbols to see what's available
        symbols = patcher.list_symbols()
        symbol_names = [s.name for s in symbols]

        # Arrow functions should be found
        assert "add" in symbol_names


class TestTypeScriptUpdate:
    """Test TypeScript function updates."""

    def test_update_ts_function_with_types(self):
        """Test updating a TypeScript function with type annotations."""
        code = """
function greet(name: string): string {
    return "Hello, " + name;
}

function farewell(name: string): string {
    return "Goodbye, " + name;
}
"""
        patcher = PolyglotPatcher(code, PatchLanguage.TYPESCRIPT)

        new_code = """function greet(name: string): string {
    return `Hello, ${name}!`;
}"""

        result = patcher.update_function("greet", new_code)

        assert result.success is True
        modified = patcher.get_modified_code()
        assert "Hello, ${name}!" in modified
        assert "Goodbye" in modified  # farewell preserved


class TestJavaUpdate:
    """Test Java method updates."""

    def test_update_java_method(self):
        """Test updating a Java method."""
        code = """
public class Calculator {
    public int add(int a, int b) {
        return a + b;
    }

    public int multiply(int a, int b) {
        return a * b;
    }
}
"""
        patcher = PolyglotPatcher(code, PatchLanguage.JAVA)

        new_code = """public int add(int a, int b) {
        // Now with logging
        System.out.println("Adding " + a + " + " + b);
        return a + b;
    }"""

        result = patcher.update_method("Calculator", "add", new_code)

        assert result.success is True
        modified = patcher.get_modified_code()
        assert "System.out.println" in modified
        assert "multiply" in modified  # other method preserved


class TestTierCapabilities:
    """Test that tier capabilities are correctly defined."""

    def test_community_tier_has_basic_replacement(self):
        """Test Community tier has basic replacement capability."""
        caps = get_tool_capabilities("update_symbol", "community")
        assert "basic_replacement" in caps["capabilities"]

    def test_community_tier_has_session_limit(self):
        """Test Community tier has session limit."""
        caps = get_tool_capabilities("update_symbol", "community")
        assert caps["limits"]["max_updates_per_call"] == 10

    def test_pro_tier_is_unlimited(self):
        """Test Pro tier has unlimited updates."""
        caps = get_tool_capabilities("update_symbol", "pro")
        assert caps["limits"]["max_updates_per_call"] == -1

    def test_pro_tier_has_hooks(self):
        """Test Pro tier has pre/post hooks."""
        caps = get_tool_capabilities("update_symbol", "pro")
        assert "pre_update_hook" in caps["capabilities"]
        assert "post_update_hook" in caps["capabilities"]

    def test_enterprise_tier_has_audit_trail(self):
        """Test Enterprise tier has audit trail."""
        caps = get_tool_capabilities("update_symbol", "enterprise")
        assert "audit_trail" in caps["capabilities"]

    def test_enterprise_tier_has_compliance(self):
        """Test Enterprise tier has compliance check."""
        caps = get_tool_capabilities("update_symbol", "enterprise")
        assert "compliance_check" in caps["capabilities"]

    def test_enterprise_tier_has_approval(self):
        """Test Enterprise tier has code review approval."""
        caps = get_tool_capabilities("update_symbol", "enterprise")
        assert "code_review_approval" in caps["capabilities"]


class TestLimitsTomlIntegration:
    """Test that limits.toml values are used."""

    def test_limits_toml_community_tier(self):
        """Test limits.toml Community tier values."""
        from code_scalpel.licensing.config_loader import get_tool_limits

        limits = get_tool_limits("update_symbol", "community")

        # Should have the values from limits.toml
        assert limits.get("backup_enabled", False) is True
        assert limits.get("validation_level", "none") == "syntax"

    def test_limits_toml_pro_tier(self):
        """Test limits.toml Pro tier values."""
        from code_scalpel.licensing.config_loader import get_tool_limits

        limits = get_tool_limits("update_symbol", "pro")

        assert limits.get("backup_enabled", False) is True
        assert limits.get("validation_level", "none") == "semantic"
