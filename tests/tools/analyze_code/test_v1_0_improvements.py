"""
[20260110_TEST] v1.0 - Pre-release validation tests for analyze_code improvements.

Tests added for v1.0 pre-release:
1. Language validation (reject unsupported languages explicitly)
2. Output metadata (language_detected, tier_applied)
3. Configuration alignment verification
"""

from importlib.util import find_spec

from code_scalpel.mcp.server import _analyze_code_sync


def _parser_module_available(module_name: str) -> bool:
    return find_spec(module_name) is not None


class TestLanguageValidation:
    """Test explicit language validation added in v1.0."""

    def test_supported_language_accepted_go(self):
        """Go should be analyzed through the shared language dispatch."""
        code = """
package main

func main() {
    println("Hello")
}
"""
        result = _analyze_code_sync(code=code, language="go")

        if _parser_module_available("tree_sitter_go"):
            assert result.success is True
            assert result.language_detected == "go"
            assert "main" in result.functions
        else:
            assert result.success is False
            assert result.error is not None
            assert "unsupported language" not in result.error.lower()
            assert "tree_sitter_go" in result.error

    def test_supported_language_accepted_rust(self):
        """Rust should be analyzed through the shared language dispatch."""
        code = """
fn main() {
    println!("Hello");
}
"""
        result = _analyze_code_sync(code=code, language="rust")

        if _parser_module_available("tree_sitter_rust"):
            assert result.success is True
            assert result.language_detected == "rust"
            assert "main" in result.functions
        else:
            assert result.success is False
            assert result.error is not None
            assert "unsupported language" not in result.error.lower()
            assert "tree_sitter_rust" in result.error

    def test_unsupported_language_lists_supported(self):
        """Error message should list actually supported languages."""
        result = _analyze_code_sync(code="object Main extends App", language="scala")

        assert "python" in result.error.lower()
        assert "javascript" in result.error.lower()
        assert "typescript" in result.error.lower()
        assert "java" in result.error.lower()
        assert "rust" in result.error.lower()
        assert "swift" in result.error.lower()

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
        code = (
            "public class Calculator { public int calculate(int x) { return x * 2; } }"
        )
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

    def test_rust_analysis_populates_language_detected(self):
        """Rust analysis should populate language_detected field."""
        code = "fn add(a: i32, b: i32) -> i32 { a + b }"
        result = _analyze_code_sync(code=code, language="rust")

        if _parser_module_available("tree_sitter_rust"):
            assert result.success is True
            assert result.language_detected == "rust"
        else:
            assert result.success is False
            assert result.error is not None
            assert "unsupported language" not in result.error.lower()
            assert "tree_sitter_rust" in result.error


class TestConfigurationAlignment:
    """Test that configuration and implementation are aligned."""

    def test_limits_toml_matches_implementation(self):
        """Verify .code-scalpel/limits.toml doesn't advertise unsupported languages."""
        from pathlib import Path

        import tomli

        # Load limits.toml
        limits_path = (
            Path(__file__).parent.parent.parent.parent
            / "src"
            / "code_scalpel"
            / "capabilities"
            / "limits.toml"
        )
        with open(limits_path, "rb") as f:
            limits = tomli.load(f)

        # Check Pro tier languages
        pro_langs = set(
            limits.get("pro", {}).get("analyze_code", {}).get("languages", [])
        )

        # [20260305_FEATURE] Rust and Swift implemented in v2.1.0 — added to expected set
        assert pro_langs == {
            "python", "javascript", "typescript", "java",
            "c", "cpp", "csharp", "go",
            "kotlin", "php", "ruby", "swift", "rust",
        }

    def test_community_tier_languages_match_pro(self):
        """Community and Pro should have same languages (Pro differs only in limits)."""
        from pathlib import Path

        import tomli

        limits_path = (
            Path(__file__).parent.parent.parent.parent
            / "src"
            / "code_scalpel"
            / "capabilities"
            / "limits.toml"
        )
        with open(limits_path, "rb") as f:
            limits = tomli.load(f)

        community_langs = set(
            limits.get("community", {}).get("analyze_code", {}).get("languages", [])
        )
        pro_langs = set(
            limits.get("pro", {}).get("analyze_code", {}).get("languages", [])
        )

        assert (
            community_langs == pro_langs
        ), "Language support should be consistent across tiers"
