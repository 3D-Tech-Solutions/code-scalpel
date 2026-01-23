"""
[20260110_TEST] v1.0 - Pre-release validation tests for analyze_code improvements.

Tests added for v1.0 pre-release:
1. Language validation (reject unsupported languages explicitly)
2. Output metadata (language_detected, tier_applied)
3. Configuration alignment verification
"""

from code_scalpel.mcp.server import _analyze_code_sync


class TestLanguageValidation:
    """Test explicit language validation added in v1.0."""

    def test_unsupported_language_rejected_go(self):
        """Go should be explicitly rejected with helpful error until Q1 2026."""
        code = """
package main

func main() {
    println("Hello")
}
"""
        result = _analyze_code_sync(code=code, language="go")

        assert result.success is False
        assert result.error is not None
        assert "unsupported language" in result.error.lower()
        assert "go" in result.error.lower()
        assert "q1 2026" in result.error.lower()

    def test_unsupported_language_rejected_rust(self):
        """Rust should be explicitly rejected with helpful error until Q1 2026."""
        code = """
fn main() {
    println!("Hello");
}
"""
        result = _analyze_code_sync(code=code, language="rust")

        assert result.success is False
        assert result.error is not None
        assert "unsupported language" in result.error.lower()
        assert "rust" in result.error.lower()

    def test_unsupported_language_lists_supported(self):
        """Error message should list actually supported languages."""
        result = _analyze_code_sync(code="fn main() {}", language="rust")

        assert "python" in result.error.lower()
        assert "javascript" in result.error.lower()
        assert "typescript" in result.error.lower()
        assert "java" in result.error.lower()

    def test_supported_language_python_accepted(self):
        """Python should still be accepted."""
        code = "def hello(): pass"
        result = _analyze_code_sync(code=code, language="python")

        assert result.success is True
        assert "hello" in result.functions

    def test_supported_language_java_accepted(self):
        """Java should still be accepted."""
        code = "public class Test { public void hello() {} }"
        result = _analyze_code_sync(code=code, language="java")

        assert result.success is True
        assert len(result.functions) > 0 or len(result.classes) > 0


class TestOutputMetadata:
    """Test new metadata fields added in v1.0."""

    def test_python_analysis_populates_language_detected(self):
        """Python analysis should populate language_detected field."""
        code = "def calculate(x): return x * 2"
        result = _analyze_code_sync(code=code, language="python")

        assert result.success is True
        assert result.language_detected == "python"

    def test_javascript_analysis_populates_language_detected(self):
        """JavaScript analysis should populate language_detected field."""
        code = "function calculate(x) { return x * 2; }"
        result = _analyze_code_sync(code=code, language="javascript")

        assert result.success is True
        assert result.language_detected == "javascript"

    def test_typescript_analysis_populates_language_detected(self):
        """TypeScript analysis should populate language_detected field."""
        code = "function calculate(x: number): number { return x * 2; }"
        result = _analyze_code_sync(code=code, language="typescript")

        assert result.success is True
        assert result.language_detected == "typescript"

    def test_java_analysis_populates_language_detected(self):
        """Java analysis should populate language_detected field."""
        code = "public class Calculator { public int calculate(int x) { return x * 2; } }"
        result = _analyze_code_sync(code=code, language="java")

        assert result.success is True
        assert result.language_detected == "java"

    def test_analysis_populates_tier_applied(self):
        """Analysis should populate tier_applied field."""
        code = "def simple(): pass"
        result = _analyze_code_sync(code=code, language="python")

        assert result.success is True
        assert result.tier_applied is not None
        assert result.tier_applied in {"community", "pro", "enterprise"}

    def test_auto_detection_populates_language_detected(self):
        """Auto-detection should still populate language_detected."""
        code = "def hello(): pass"
        result = _analyze_code_sync(code=code, language="auto")

        assert result.success is True
        assert result.language_detected == "python"


class TestConfigurationAlignment:
    """Test that configuration and implementation are aligned."""

    def test_limits_toml_matches_implementation(self):
        """Verify .code-scalpel/limits.toml doesn't advertise unsupported languages."""
        from pathlib import Path

        import tomli

        # Load limits.toml
        limits_path = Path(__file__).parent.parent.parent.parent / ".code-scalpel" / "limits.toml"
        with open(limits_path, "rb") as f:
            limits = tomli.load(f)

        # Check Pro tier languages
        pro_langs = set(limits.get("pro", {}).get("analyze_code", {}).get("languages", []))

        # Should NOT contain go or rust
        assert "go" not in pro_langs, "Pro tier should not advertise Go until implemented"
        assert "rust" not in pro_langs, "Pro tier should not advertise Rust until implemented"

        # Should only contain implemented languages
        assert pro_langs == {"python", "javascript", "typescript", "java"}

    def test_community_tier_languages_match_pro(self):
        """Community and Pro should have same languages (Pro differs only in limits)."""
        from pathlib import Path

        import tomli

        limits_path = Path(__file__).parent.parent.parent.parent / ".code-scalpel" / "limits.toml"
        with open(limits_path, "rb") as f:
            limits = tomli.load(f)

        community_langs = set(limits.get("community", {}).get("analyze_code", {}).get("languages", []))
        pro_langs = set(limits.get("pro", {}).get("analyze_code", {}).get("languages", []))

        assert community_langs == pro_langs, "Language support should be consistent across tiers"
