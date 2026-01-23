import textwrap

import pytest

from code_scalpel.licensing.features import get_tool_capabilities
from code_scalpel.mcp.helpers import analyze_helpers
from code_scalpel.mcp.helpers.analyze_helpers import _analyze_code_sync

# [20260121_TEST] Tier validation for analyze_code


def _python_sample():
    return textwrap.dedent("""
        import math

        def foo(x):
            return x + 1

        class Bar:
            def method(self, y):
                return y * 2
        """)


def _javascript_sample():
    return textwrap.dedent("""
        import util from "./util.js";
        function foo(x) { return x + 1; }
        class Bar { method(y) { return y * 2; } }
        """)


def _typescript_sample():
    return textwrap.dedent("""
        import { Util } from "./util";
        export function foo(x: number): number { return x + 1; }
        export class Bar { method(y: number): number { return y * 2; } }
        """)


def _java_sample():
    return textwrap.dedent("""
        import java.util.*;
        public class Foo {
            public int add(int x) { return x + 1; }
        }
        """)


class TestAnalyzeCodeCommunityTier:
    @pytest.fixture(autouse=True)
    def _tier(self, monkeypatch):
        monkeypatch.setattr(analyze_helpers, "get_current_tier_from_license", lambda: "community")
        self.caps = get_tool_capabilities("analyze_code", "community")
        self.cap_set = set(self.caps.get("capabilities", set()))
        self.limit_mb = self.caps.get("limits", {}).get("max_file_size_mb")

    def test_capabilities_present(self):
        assert {
            "basic_ast",
            "function_inventory",
            "class_inventory",
            "imports",
            "complexity_metrics",
        }.issubset(self.cap_set)
        assert self.limit_mb == 1

    def test_python_parsing(self):
        result = _analyze_code_sync(_python_sample(), language="python")
        assert result.success
        assert result.language_detected == "python"
        assert result.tier_applied == "community"
        assert "foo" in result.functions
        assert any(cls.name == "Bar" for cls in result.class_details)
        assert result.complexity > 0
        assert result.lines_of_code > 0

    def test_js_parsing(self):
        result = _analyze_code_sync(_javascript_sample(), language="javascript")
        assert result.success
        assert result.language_detected == "javascript"

    def test_ts_parsing(self):
        result = _analyze_code_sync(_typescript_sample(), language="typescript")
        assert result.success
        assert result.language_detected == "typescript"

    def test_java_parsing(self):
        result = _analyze_code_sync(_java_sample(), language="java")
        assert result.success
        assert result.language_detected == "java"

    def test_function_class_and_method_extraction(self):
        result = _analyze_code_sync(_python_sample(), language="python")
        assert "foo" in result.functions
        cls = next(c for c in result.class_details if c.name == "Bar")
        assert "method" in cls.methods
        assert result.imports[0].startswith("math")

    def test_docstrings_not_included(self):
        code = 'def foo():\n    """doc"""\n    return 1\n'
        result = _analyze_code_sync(code, language="python")
        assert "foo" in result.functions
        assert all("doc" not in f for f in result.functions)

    def test_path_limit_enforced(self):
        large = "a" * (2 * 1024 * 1024)  # 2 MB
        result = _analyze_code_sync(large, language="python")
        assert not result.success
        assert "limit of 1 MB" in result.error

    def test_unsupported_language_error(self):
        result = _analyze_code_sync("fn main(){}", language="rust")
        assert not result.success
        assert "Unsupported language" in result.error
        assert "Go/Rust" in result.error


class TestAnalyzeCodeProTier:
    @pytest.fixture(autouse=True)
    def _tier(self, monkeypatch):
        monkeypatch.setattr(analyze_helpers, "get_current_tier_from_license", lambda: "pro")
        self.caps = get_tool_capabilities("analyze_code", "pro")
        self.cap_set = set(self.caps.get("capabilities", set()))
        self.limit_mb = self.caps.get("limits", {}).get("max_file_size_mb")

    def test_capabilities_present(self):
        expected = {
            "code_smells",
            "halstead_metrics",
            "cognitive_complexity",
            "duplicate_code_detection",
            "dependency_graph",
            "framework_detection",
            "dead_code_detection",
            "decorator_analysis",
        }
        assert expected.issubset(self.cap_set)
        assert self.limit_mb == 10

    def test_python_advanced_metrics(self):
        code = _python_sample() + "\n" + _python_sample()
        result = _analyze_code_sync(code, language="python")
        assert result.success
        assert result.cognitive_complexity >= 0
        assert result.halstead_metrics is not None
        assert result.dependency_graph is not None
        assert result.duplicate_code_blocks is not None
        assert result.tier_applied == "pro"

    def test_framework_and_dead_code_detection(self):
        code = "from flask import Flask\napp = Flask(__name__)\n\n" + _python_sample()
        result = _analyze_code_sync(code, language="python")
        assert result.success
        assert result.frameworks is not None
        assert result.dead_code_hints is not None
        assert result.decorator_summary is not None
        assert result.type_summary is not None

    def test_limit_enforced(self, monkeypatch):
        monkeypatch_caps = {
            **self.caps,
            "limits": {"max_file_size_mb": 0.001},
        }
        monkeypatch.setattr(
            analyze_helpers,
            "get_tool_capabilities",
            lambda _name, _tier: monkeypatch_caps,
        )
        small_over_limit = "a" * 5000
        result = _analyze_code_sync(small_over_limit, language="python")
        assert not result.success
        assert "limit" in result.error


class TestAnalyzeCodeEnterpriseTier:
    @pytest.fixture(autouse=True)
    def _tier(self, monkeypatch):
        monkeypatch.setattr(analyze_helpers, "get_current_tier_from_license", lambda: "enterprise")
        self.caps = get_tool_capabilities("analyze_code", "enterprise")
        self.cap_set = set(self.caps.get("capabilities", set()))

    def test_capabilities_present(self):
        expected = {
            "custom_rules",
            "compliance_checks",
            "organization_patterns",
            "architecture_patterns",
            "technical_debt_scoring",
            "api_surface_analysis",
            "priority_ordering",
            "complexity_trends",
        }
        assert expected.issubset(self.cap_set)

    def test_enterprise_enrichments(self):
        code = _python_sample() + "\n" + "eval('x')\n" + "password = 'p'\n"
        result = _analyze_code_sync(code, language="python", file_path="/tmp/sample.py")
        assert result.success
        assert result.custom_rule_violations
        assert result.compliance_issues
        assert result.organization_patterns is not None
        assert result.architecture_patterns is not None
        assert result.technical_debt is not None
        assert result.api_surface is not None
        assert result.prioritized is True
        assert result.complexity_trends is not None
        assert result.tier_applied == "enterprise"

    def test_enterprise_limit(self, monkeypatch):
        monkeypatch_caps = {**self.caps, "limits": {"max_file_size_mb": 0.001}}
        monkeypatch.setattr(
            analyze_helpers,
            "get_tool_capabilities",
            lambda _name, _tier: monkeypatch_caps,
        )
        small_over_limit = "a" * 5000
        result = _analyze_code_sync(small_over_limit, language="python")
        assert not result.success
        assert "limit" in result.error


class TestAnalyzeCodeCrossTierGating:
    def test_pro_features_absent_in_community(self):
        comm = set(get_tool_capabilities("analyze_code", "community").get("capabilities", set()))
        assert "cognitive_complexity" not in comm
        assert "code_smells" not in comm
        assert "halstead_metrics" not in comm

    def test_enterprise_features_absent_in_pro(self):
        pro = set(get_tool_capabilities("analyze_code", "pro").get("capabilities", set()))
        assert "custom_rules" not in pro
        assert "compliance_checks" not in pro
        assert "architecture_patterns" not in pro


class TestAnalyzeCodeLanguageConsistency:
    @pytest.mark.parametrize(
        "lang, sample",
        [
            ("python", _python_sample()),
            ("javascript", _javascript_sample()),
            ("typescript", _typescript_sample()),
            ("java", _java_sample()),
        ],
    )
    def test_languages_all_tiers(self, lang, sample, monkeypatch):
        for tier in ["community", "pro", "enterprise"]:
            monkeypatch.setattr(analyze_helpers, "get_current_tier_from_license", lambda t=tier: t)
            result = _analyze_code_sync(sample, language=lang)
            assert result.success
            assert result.language_detected == lang
            assert result.tier_applied == tier


class TestAnalyzeCodeErrorHandling:
    def test_unsupported_languages_listed(self, monkeypatch):
        monkeypatch.setattr(analyze_helpers, "get_current_tier_from_license", lambda: "community")
        result = _analyze_code_sync("fn main(){}", language="go")
        assert not result.success
        assert "supported" in result.error.lower()

    def test_graceful_rejection(self, monkeypatch):
        monkeypatch.setattr(analyze_helpers, "get_current_tier_from_license", lambda: "community")
        result = _analyze_code_sync("bad", language="rust")
        assert not result.success
        assert result.functions == []


class TestAnalyzeCodeConfigurationAlignment:
    def test_limits_match_config_community(self):
        limits = get_tool_capabilities("analyze_code", "community")["limits"]
        assert limits["max_file_size_mb"] == 1

    def test_limits_match_config_pro(self):
        limits = get_tool_capabilities("analyze_code", "pro")["limits"]
        assert limits["max_file_size_mb"] == 10

    def test_limits_match_config_enterprise(self):
        limits = get_tool_capabilities("analyze_code", "enterprise")["limits"]
        assert limits["max_file_size_mb"] == 100
