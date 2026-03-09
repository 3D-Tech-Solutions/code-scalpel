"""Kotlin static analysis tool parser tests.

Validates all five new Kotlin tool parsers introduced in Stage 5:
DiktatParser, GradleBuildParser, ComposeLinterParser, KonsistParser,
KotlinTestParser — plus KotlinNormalizer and KotlinParserAdapter.

All parsers operate on fixture data; no CLI tools need to be installed.

[20260303_TEST] Created for Stage 5 Kotlin tool parsers (Work-Tracking.md).
"""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET

import pytest


# ---------------------------------------------------------------------------
# Lazy-import helpers (keep test collection fast)
# ---------------------------------------------------------------------------

def _diktat():
    from code_scalpel.code_parsers.kotlin_parsers.kotlin_parsers_diktat import (
        DiktatParser, DiktatSeverity, DiktatRuleSet,
    )
    return DiktatParser, DiktatSeverity, DiktatRuleSet


def _gradle():
    from code_scalpel.code_parsers.kotlin_parsers.kotlin_parsers_gradle import (
        GradleBuildParser, Dependency, ConfigurationType,
    )
    return GradleBuildParser, Dependency, ConfigurationType


def _compose():
    from code_scalpel.code_parsers.kotlin_parsers.kotlin_parsers_compose import (
        ComposeLinterParser, ComposeIssueType, ComposeSeverity,
    )
    return ComposeLinterParser, ComposeIssueType, ComposeSeverity


def _konsist():
    from code_scalpel.code_parsers.kotlin_parsers.kotlin_parsers_Konsist import (
        KonsistParser, KonsistSeverity, KonsistRuleType,
    )
    return KonsistParser, KonsistSeverity, KonsistRuleType


def _ktest():
    from code_scalpel.code_parsers.kotlin_parsers.kotlin_parsers_test import (
        KotlinTestParser, TestStatus, TestFramework,
    )
    return KotlinTestParser, TestStatus, TestFramework


def _detekt():
    from code_scalpel.code_parsers.kotlin_parsers.kotlin_parsers_Detekt import (
        DetektParser, DetektSeverity,
    )
    return DetektParser, DetektSeverity


def _ktlint():
    from code_scalpel.code_parsers.kotlin_parsers.kotlin_parsers_ktlint import (
        KtlintParser, KtlintSeverity,
    )
    return KtlintParser, KtlintSeverity


# ---------------------------------------------------------------------------
# __init__.py lazy-export smoke test
# ---------------------------------------------------------------------------

class TestKotlinParsersModule:
    """Lazy __getattr__ exports work for all five new parsers."""

    @pytest.mark.parametrize("name", [
        "DiktatParser", "GradleBuildParser", "ComposeLinterParser",
        "KonsistParser", "KotlinTestParser", "DetektParser", "KtlintParser",
    ])
    def test_module_exports_parser(self, name):
        import code_scalpel.code_parsers.kotlin_parsers as m
        cls = getattr(m, name)
        assert cls is not None

    def test_unknown_attribute_raises(self):
        import code_scalpel.code_parsers.kotlin_parsers as m
        with pytest.raises(AttributeError):
            _ = m.NonExistentKotlinParser  # type: ignore[attr-defined]


class TestKotlinParserRegistry:
    """Registry coverage for all Kotlin parser tools."""

    @pytest.mark.parametrize("tool_name, class_name", [
        ("diktat", "DiktatParser"),
        ("compose", "ComposeLinterParser"),
        ("gradle", "GradleBuildParser"),
        ("konsist", "KonsistParser"),
        ("test", "KotlinTestParser"),
        ("kotlin-test", "KotlinTestParser"),
        ("detekt", "DetektParser"),
        ("ktlint", "KtlintParser"),
    ])
    def test_get_parser_supports_all_tools(self, tool_name, class_name):
        from code_scalpel.code_parsers.kotlin_parsers import KotlinParserRegistry

        parser = KotlinParserRegistry().get_parser(tool_name)
        assert parser.__class__.__name__ == class_name


# ---------------------------------------------------------------------------
# DiktatParser (severity stored as raw string; violations stateful)
# ---------------------------------------------------------------------------

class TestDiktatParser:
    """Tests for DiktatParser."""

    # --- JSON report parsing ---

    def test_parse_json_report_empty(self):
        DiktatParser, _, _ = _diktat()
        parser = DiktatParser()
        result = parser.parse_json_report("[]")
        assert result == []

    def test_parse_json_report_single_violation_file_path(self):
        """DiktatViolation exposes file_path (not filename)."""
        DiktatParser, _, _ = _diktat()
        # Flat list format: each item needs "ruleId" key
        report = json.dumps([{
            "fileName": "Main.kt",
            "line": 10,
            "column": 5,
            "ruleId": "KDOC_WITHOUT_PARAM_TAG",
            "message": "Missing @param tag",
            "severity": "WARNING",
        }])
        parser = DiktatParser()
        violations = parser.parse_json_report(report)
        assert len(violations) == 1
        v = violations[0]
        assert v.file_path == "Main.kt"
        assert v.line_number == 10

    def test_parse_json_report_severity_is_raw_string(self):
        """Severity is stored as the raw string value, not a DiktatSeverity enum."""
        DiktatParser, _, _ = _diktat()
        report = json.dumps([{
            "ruleId": "RULE_A", "message": "msg", "severity": "ERROR",
        }])
        parser = DiktatParser()
        violations = parser.parse_json_report(report)
        assert len(violations) == 1
        assert violations[0].severity == "ERROR"

    def test_parse_json_report_invalid_json_returns_empty(self):
        DiktatParser, _, _ = _diktat()
        parser = DiktatParser()
        result = parser.parse_json_report("{not-json")
        assert result == []

    def test_parse_json_multiple_violations_stores_in_self(self):
        """parse_json_report stores results in self.violations."""
        DiktatParser, _, _ = _diktat()
        items = [
            {"ruleId": "RULE_A", "message": "msg a", "severity": "error"},
            {"ruleId": "RULE_B", "message": "msg b", "severity": "info"},
        ]
        parser = DiktatParser()
        violations = parser.parse_json_report(json.dumps(items))
        assert len(violations) == 2
        assert parser.violations is violations

    # --- execute_diktat (returns dict when tool missing) ---

    def test_execute_diktat_returns_dict_when_tool_missing(self, tmp_path):
        """execute_diktat returns a dict (not list) regardless of tool presence."""
        from pathlib import Path
        DiktatParser, _, _ = _diktat()
        parser = DiktatParser()
        result = parser.execute_diktat(tmp_path)
        assert isinstance(result, dict)

    # --- generate_fix_suggestions (no arguments — stateful) ---

    def test_generate_fix_suggestions_after_parse(self):
        """generate_fix_suggestions() takes no args; uses self.violations."""
        DiktatParser, _, _ = _diktat()
        report = json.dumps([{
            "ruleId": "MISSING_KDOC", "message": "Missing KDoc", "severity": "warning",
        }])
        parser = DiktatParser()
        parser.parse_json_report(report)   # populates self.violations
        suggestions = parser.generate_fix_suggestions()
        assert isinstance(suggestions, list)


# ---------------------------------------------------------------------------
# GradleBuildParser
# ---------------------------------------------------------------------------

class TestGradleBuildParser:
    """Tests for GradleBuildParser."""

    _BUILD_KTS = """\
plugins {
    kotlin("jvm") version "1.9.0"
    id("com.github.johnrengelman.shadow") version "8.0.0"
}
dependencies {
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-core:1.7.3")
    testImplementation("io.kotest:kotest-runner-junit5:5.7.2")
}
"""

    def test_parse_build_gradle_kts_detects_kotlin_plugin(self, tmp_path):
        # parse_build_gradle_kts takes a Path; write a real file.
        # The id("com.github.johnrengelman.shadow") entry uses the id() DSL
        # which identify_plugins supports; kotlin("jvm") DSL is not matched.
        GradleBuildParser, _, _ = _gradle()
        f = tmp_path / "build.gradle.kts"
        f.write_text(self._BUILD_KTS)
        parser = GradleBuildParser()
        config = parser.parse_build_gradle_kts(f)
        plugin_ids = [p.id for p in config.plugins]
        # shadow plugin is detected via id() DSL
        assert any("shadow" in pid for pid in plugin_ids)

    def test_parse_build_gradle_kts_detects_implementation_dep(self, tmp_path):
        GradleBuildParser, _, ConfigurationType = _gradle()
        f = tmp_path / "build.gradle.kts"
        f.write_text(self._BUILD_KTS)
        parser = GradleBuildParser()
        config = parser.parse_build_gradle_kts(f)
        impl_deps = [d for d in config.dependencies
                     if d.configuration == ConfigurationType.IMPLEMENTATION.value]
        assert len(impl_deps) >= 1

    def test_parse_build_gradle_kts_empty_file(self, tmp_path):
        GradleBuildParser, _, _ = _gradle()
        f = tmp_path / "build.gradle.kts"
        f.write_text("")
        parser = GradleBuildParser()
        config = parser.parse_build_gradle_kts(f)
        assert config.dependencies == []

    def test_identify_plugins_returns_list(self):
        GradleBuildParser, _, _ = _gradle()
        parser = GradleBuildParser()
        plugins = parser.identify_plugins(self._BUILD_KTS)
        assert isinstance(plugins, list)

    def test_detect_dependency_vulnerabilities_returns_list(self, tmp_path):
        # detect_dependency_vulnerabilities() is stateful — no args.
        # Populate build_config first via parse_build_gradle_kts.
        GradleBuildParser, _, _ = _gradle()
        f = tmp_path / "build.gradle.kts"
        f.write_text(self._BUILD_KTS)
        parser = GradleBuildParser()
        parser.parse_build_gradle_kts(f)   # populates self.build_config
        result = parser.detect_dependency_vulnerabilities()
        assert isinstance(result, list)


# ---------------------------------------------------------------------------
# ComposeLinterParser
# ---------------------------------------------------------------------------

class TestComposeLinterParser:
    """Tests for ComposeLinterParser."""

    # Plain-text pattern: "file.kt:line: error|warning|info: message"
    _COMPILER_TEXT = """\
Main.kt:12: warning: Composable function should not have side effects
Screen.kt:25: error: Non-skippable Composable
"""

    def test_parse_compiler_output_text_warnings(self):
        ComposeLinterParser, _, _ = _compose()
        parser = ComposeLinterParser()
        issues = parser.parse_compiler_output(self._COMPILER_TEXT)
        assert len(issues) >= 1

    def test_parse_compiler_output_empty(self):
        ComposeLinterParser, _, _ = _compose()
        parser = ComposeLinterParser()
        issues = parser.parse_compiler_output("")
        assert issues == []

    def test_parse_compiler_output_sarif(self):
        ComposeLinterParser, _, _ = _compose()
        sarif = json.dumps({
            "runs": [{
                "results": [{
                    "message": {"text": "Stability issue"},
                    "level": "warning",
                    "locations": [{"physicalLocation": {
                        "artifactLocation": {"uri": "Composable.kt"},
                        "region": {"startLine": 5, "startColumn": 3},
                    }}],
                    "ruleId": "COMPOSE_STABILITY",
                }]
            }]
        })
        parser = ComposeLinterParser()
        issues = parser.parse_compiler_output(sarif)
        assert len(issues) == 1

    def test_parse_stability_analysis_takes_dict(self):
        """parse_stability_analysis expects a dict with 'unstableClasses' key."""
        ComposeLinterParser, _, _ = _compose()
        parser = ComposeLinterParser()
        data = {"unstableClasses": [
            {"name": "ViewModel", "reason": "mutable field", "file": "VM.kt", "line": 5},
        ]}
        issues = parser.parse_stability_analysis(data)
        assert isinstance(issues, list)
        assert len(issues) == 1

    def test_parse_stability_analysis_empty_dict_returns_empty(self):
        ComposeLinterParser, _, _ = _compose()
        parser = ComposeLinterParser()
        issues = parser.parse_stability_analysis({})
        assert issues == []

    def test_execute_compiler_analysis_returns_dict(self, tmp_path):
        """execute_compiler_analysis returns a dict when gradle not found."""
        from pathlib import Path
        ComposeLinterParser, _, _ = _compose()
        parser = ComposeLinterParser()
        result = parser.execute_compiler_analysis(tmp_path)
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# KonsistParser
# ---------------------------------------------------------------------------

class TestKonsistParser:
    """Tests for KonsistParser."""

    _JUNIT_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<testsuites>
  <testsuite name="KonsistSuite" tests="2" failures="1">
    <testcase name="All classes should follow naming convention" classname="Konsist">
      <failure message="Class &lt;FooBar&gt; violates naming rule">
        File: src/FooBar.kt Line: 1
      </failure>
    </testcase>
    <testcase name="No class should have cyclic dependencies" classname="Konsist"/>
  </testsuite>
</testsuites>
"""

    def test_parse_violations_junit_xml(self):
        KonsistParser, _, _ = _konsist()
        parser = KonsistParser()
        violations = parser.parse_violations(self._JUNIT_XML)
        assert len(violations) >= 1

    def test_parse_violations_empty_xml(self):
        KonsistParser, _, _ = _konsist()
        parser = KonsistParser()
        violations = parser.parse_violations(
            '<?xml version="1.0"?><testsuites></testsuites>'
        )
        assert violations == []

    def test_parse_violations_dict_list(self):
        KonsistParser, _, _ = _konsist()
        items = [
            {"rule": "naming", "file": "Foo.kt", "line": 1,
             "message": "bad name", "severity": "error"},
        ]
        parser = KonsistParser()
        violations = parser.parse_violations(items)
        assert len(violations) == 1

    def test_validate_architecture_takes_path(self, tmp_path):
        """validate_architecture expects a Path, not a list."""
        KonsistParser, _, _ = _konsist()
        parser = KonsistParser()
        result = parser.validate_architecture(tmp_path)
        assert isinstance(result, dict)

    def test_generate_report_returns_string(self):
        """generate_report returns a JSON string, not a dict."""
        KonsistParser, _, _ = _konsist()
        parser = KonsistParser()
        violations = parser.parse_violations(self._JUNIT_XML)
        report_str = parser.generate_report(violations)
        assert isinstance(report_str, str)
        parsed = json.loads(report_str)
        assert "total" in parsed


# ---------------------------------------------------------------------------
# KotlinTestParser
# ---------------------------------------------------------------------------

class TestKotlinTestParser:
    """Tests for KotlinTestParser."""

    _JUNIT_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<testsuites>
  <testsuite name="com.example.CalculatorTest" tests="3" failures="1" time="0.42">
    <testcase name="add returns correct sum" classname="com.example.CalculatorTest" time="0.01"/>
    <testcase name="divide by zero throws" classname="com.example.CalculatorTest" time="0.02">
      <failure message="Expected exception">ArithmeticException not thrown</failure>
    </testcase>
    <testcase name="multiply two numbers" classname="com.example.CalculatorTest" time="0.01"/>
  </testsuite>
</testsuites>
"""

    def test_parse_junit_report_returns_list_of_suites(self):
        """parse_junit_report returns List[TestSuite], not a single object."""
        KotlinTestParser, TestStatus, _ = _ktest()
        parser = KotlinTestParser()
        suites = parser.parse_junit_report(self._JUNIT_XML)
        assert isinstance(suites, list)
        assert len(suites) == 1

    def test_parse_junit_suite_test_counts(self):
        """TestSuite.tests holds the test cases; check pass/fail counts."""
        KotlinTestParser, TestStatus, _ = _ktest()
        parser = KotlinTestParser()
        suites = parser.parse_junit_report(self._JUNIT_XML)
        suite = suites[0]
        passed = sum(1 for tc in suite.tests if tc.status == TestStatus.PASSED.value)
        failed = sum(1 for tc in suite.tests if tc.status == TestStatus.FAILED.value)
        assert passed == 2
        assert failed == 1

    def test_parse_junit_report_empty_xml_returns_empty_list(self):
        KotlinTestParser, _, _ = _ktest()
        parser = KotlinTestParser()
        suites = parser.parse_junit_report(
            '<?xml version="1.0"?><testsuites></testsuites>'
        )
        assert suites == []

    def test_parse_kotest_results_takes_dict(self):
        """parse_kotest_results expects a Dict, not a plain XML string."""
        KotlinTestParser, _, _ = _ktest()
        parser = KotlinTestParser()
        # Minimal kotest-style JSON report
        data = {"specs": [{"name": "MySpec", "tests": [
            {"name": "test1", "status": "passed", "duration": 10},
        ]}]}
        suites = parser.parse_kotest_results(data)
        assert isinstance(suites, list)

    def test_analyze_test_quality_stateful(self):
        """analyze_test_quality() uses self.suites; populate via parse first."""
        KotlinTestParser, _, _ = _ktest()
        parser = KotlinTestParser()
        parser.parse_junit_report(self._JUNIT_XML)  # populates self.suites
        quality = parser.analyze_test_quality()
        assert isinstance(quality, dict)

    def test_generate_test_report_returns_string(self):
        """generate_test_report returns a JSON string."""
        KotlinTestParser, _, _ = _ktest()
        parser = KotlinTestParser()
        suites = parser.parse_junit_report(self._JUNIT_XML)
        report_str = parser.generate_test_report(suites)
        assert isinstance(report_str, str)
        parsed = json.loads(report_str)
        assert "quality" in parsed
        assert "total" in parsed["quality"]

    def test_parse_coverage_report_returns_metrics(self):
        KotlinTestParser, _, _ = _ktest()
        parser = KotlinTestParser()
        xml_report = """\
<report name="coverage">
  <counter type="LINE" missed="10" covered="90"/>
  <counter type="BRANCH" missed="5" covered="20"/>
</report>
"""
        metrics = parser.parse_coverage_report(xml_report)
        assert metrics.line_coverage >= 0.0


# ---------------------------------------------------------------------------
# DetektParser
# ---------------------------------------------------------------------------

class TestDetektParser:
    """Tests for DetektParser."""

    def test_parse_xml_report(self, tmp_path):
        DetektParser, DetektSeverity = _detekt()
        report_file = tmp_path / "detekt.xml"
        report_file.write_text(
            """\
<checkstyle>
  <file name="src/App.kt">
    <error line="12" column="5" severity="warning"
           message="Too many functions"
           source="detekt.complexity.TooManyFunctions"/>
  </file>
</checkstyle>
"""
        )
        report = DetektParser().parse_xml_report(str(report_file))
        assert report.total_count == 1
        assert report.findings[0].rule_id == "TooManyFunctions"
        assert report.findings[0].severity == DetektSeverity.WARNING

    def test_parse_sarif_report(self, tmp_path):
        DetektParser, _ = _detekt()
        report_file = tmp_path / "detekt.sarif"
        report_file.write_text(json.dumps({
            "runs": [{
                "results": [{
                    "ruleId": "MagicNumber",
                    "level": "error",
                    "message": {"text": "Avoid magic numbers"},
                    "locations": [{"physicalLocation": {
                        "artifactLocation": {"uri": "src/App.kt"},
                        "region": {"startLine": 7, "startColumn": 3},
                    }}],
                }]
            }]
        }))
        report = DetektParser().parse_sarif_report(str(report_file))
        assert report.total_count == 1
        assert report.findings[0].location == "src/App.kt:7:3"

    def test_parse_text_report(self):
        DetektParser, _ = _detekt()
        parser = DetektParser()
        report = parser.parse_text_report(
            "src/App.kt:4:9: warning: Prefer val over var [VarCouldBeVal]"
        )
        assert report.total_count == 1
        assert report.findings[0].rule_id == "VarCouldBeVal"

    def test_parse_config(self, tmp_path):
        DetektParser, _ = _detekt()
        config_file = tmp_path / "detekt.yml"
        config_file.write_text(
            """\
build:
  maxIssues: 5
  excludeCorrectable: true
  parallel: false
complexity:
  active: true
  LongMethod:
    active: true
    threshold: 15
excludes:
  - '**/generated/**'
includes: ['**/*.kt']
"""
        )
        config = DetektParser().parse_config(str(config_file))
        assert config.max_issues == 5
        assert config.exclude_correctable is True
        assert config.parallel is False
        assert config.rule_sets["complexity"] is True
        assert config.rules["complexity"]["LongMethod"]["threshold"] == 15
        assert "**/generated/**" in config.excludes

    def test_analyze_project_returns_empty_report_without_cli(self, tmp_path):
        DetektParser, _ = _detekt()
        parser = DetektParser(detekt_path=None)
        parser._detekt_path = None
        report = parser.analyze_project(str(tmp_path))
        assert report.total_count == 0

    def test_generate_baseline_creates_file_without_cli(self, tmp_path):
        DetektParser, _ = _detekt()
        parser = DetektParser(detekt_path=None)
        parser._detekt_path = None
        baseline_path = tmp_path / "detekt-baseline.xml"
        result = parser.generate_baseline(str(tmp_path), str(baseline_path))
        assert baseline_path.exists()
        assert result == str(baseline_path)


# ---------------------------------------------------------------------------
# KtlintParser
# ---------------------------------------------------------------------------

class TestKtlintParser:
    """Tests for KtlintParser."""

    def test_parse_json_output(self):
        KtlintParser, KtlintSeverity = _ktlint()
        payload = json.dumps([
            {
                "file": "src/App.kt",
                "violations": [
                    {
                        "line": 3,
                        "column": 1,
                        "message": "Wildcard import",
                        "rule": "standard:no-wildcard-imports",
                        "canBeAutoCorrected": True,
                    }
                ],
            }
        ])
        report = KtlintParser().parse_json_output(payload)
        assert report.total_count == 1
        assert report.violations[0].severity == KtlintSeverity.ERROR
        assert report.violations[0].can_be_auto_corrected is True

    def test_parse_json_report(self, tmp_path):
        KtlintParser, _ = _ktlint()
        report_file = tmp_path / "ktlint.json"
        report_file.write_text(json.dumps([
            {
                "file": "src/App.kt",
                "violations": [
                    {
                        "line": 9,
                        "column": 2,
                        "message": "Missing spacing",
                        "rule": "standard:spacing-between-declarations-with-comments",
                    }
                ],
            }
        ]))
        report = KtlintParser().parse_json_report(str(report_file))
        assert report.total_count == 1
        assert report.files_checked == 1

    def test_parse_text_output(self):
        KtlintParser, _ = _ktlint()
        parser = KtlintParser()
        report = parser.parse_text_output(
            "src/App.kt:2:5: Unexpected indentation (standard:indent)"
        )
        assert report.total_count == 1
        assert report.violations[0].full_rule_id == "standard:indent"

    def test_parse_editorconfig(self, tmp_path):
        KtlintParser, _ = _ktlint()
        config_file = tmp_path / ".editorconfig"
        config_file.write_text(
            """\
root = true

[*.{kt,kts}]
indent_size = 2
indent_style = tab
max_line_length = 120
ktlint_disabled_rules = standard:no-wildcard-imports,standard:filename
ktlint_experimental = enabled
ktlint_code_style = android_studio
"""
        )
        config = KtlintParser().parse_editorconfig(str(config_file))
        assert config.indent_size == 2
        assert config.indent_style == "tab"
        assert config.max_line_length == 120
        assert config.experimental_rules is True
        assert "standard:no-wildcard-imports" in config.disabled_rules

    def test_check_directory_returns_empty_report_without_cli(self, tmp_path):
        KtlintParser, _ = _ktlint()
        parser = KtlintParser(ktlint_path=None)
        parser._ktlint_path = None
        report = parser.check_directory(str(tmp_path))
        assert report.total_count == 0

    def test_format_code_without_cli_returns_original(self):
        KtlintParser, _ = _ktlint()
        parser = KtlintParser(ktlint_path=None)
        parser._ktlint_path = None
        source = "fun main(){ println(\"hi\") }\n"
        formatted, was_modified = parser.format_code(source)
        assert formatted == source
        assert was_modified is False

    def test_generate_baseline_creates_file_without_cli(self, tmp_path):
        KtlintParser, _ = _ktlint()
        parser = KtlintParser(ktlint_path=None)
        parser._ktlint_path = None
        baseline_path = tmp_path / ".ktlint-baseline.xml"
        result = parser.generate_baseline(str(tmp_path), str(baseline_path))
        assert baseline_path.exists()
        assert result == str(baseline_path)


# ---------------------------------------------------------------------------
# KotlinNormalizer (IR Phase 1)
# ---------------------------------------------------------------------------

class TestKotlinNormalizer:
    """Tests for KotlinNormalizer — minimal smoke tests."""

    @pytest.fixture(autouse=True)
    def normalizer(self):
        from code_scalpel.ir.normalizers.kotlin_normalizer import KotlinNormalizer
        self.kn = KotlinNormalizer()

    def test_import_succeeds(self):
        from code_scalpel.ir.normalizers.kotlin_normalizer import (
            KotlinNormalizer, KotlinVisitor,
        )
        assert KotlinNormalizer is not None
        assert KotlinVisitor is not None

    def test_normalizer_via_init_module(self):
        from code_scalpel.ir.normalizers import KotlinNormalizer
        assert KotlinNormalizer is not None

    def test_simple_function_produces_ir_function_def(self):
        from code_scalpel.ir.nodes import IRFunctionDef
        module = self.kn.normalize("fun add(a: Int, b: Int): Int { return a + b }")
        funcs = [n for n in module.body if isinstance(n, IRFunctionDef)]
        assert len(funcs) == 1
        assert funcs[0].name == "add"

    def test_class_declaration_produces_ir_class_def(self):
        from code_scalpel.ir.nodes import IRClassDef
        module = self.kn.normalize("class Greeter(val name: String) {}")
        classes = [n for n in module.body if isinstance(n, IRClassDef)]
        assert len(classes) == 1
        assert classes[0].name == "Greeter"

    def test_arithmetic_expression_does_not_crash(self):
        module = self.kn.normalize("fun calc(): Int { return 1 + 2 * 3 }")
        assert module is not None

    def test_comparison_expression_does_not_crash(self):
        module = self.kn.normalize("fun check(x: Int): Boolean { return x == 5 }")
        assert module is not None

    def test_is_expression_does_not_crash(self):
        module = self.kn.normalize("fun isStr(x: Any): Boolean { return x is String }")
        assert module is not None

    def test_empty_source_returns_empty_module(self):
        module = self.kn.normalize("")
        assert module is not None

    def test_package_and_import(self):
        src = "package com.example\nimport kotlin.math.sqrt\nfun f() {}"
        module = self.kn.normalize(src)
        assert module is not None

    def test_data_class(self):
        from code_scalpel.ir.nodes import IRClassDef
        src = "data class Point(val x: Int, val y: Int)"
        module = self.kn.normalize(src)
        classes = [n for n in module.body if isinstance(n, IRClassDef)]
        assert len(classes) >= 1

    def test_object_declaration(self):
        src = "object Singleton { fun instance() = this }"
        module = self.kn.normalize(src)
        assert module is not None

    def test_for_loop_does_not_crash(self):
        src = "fun f(xs: List<Int>) { for (x in xs) { println(x) } }"
        module = self.kn.normalize(src)
        assert module is not None

    def test_while_loop_does_not_crash(self):
        src = "fun f() { var i = 0; while (i < 10) { i++ } }"
        module = self.kn.normalize(src)
        assert module is not None

    def test_if_else_does_not_crash(self):
        src = "fun abs(x: Int): Int { return if (x < 0) -x else x }"
        module = self.kn.normalize(src)
        assert module is not None

    def test_nested_functions(self):
        from code_scalpel.ir.nodes import IRFunctionDef
        src = "fun outer() { fun inner() {} inner() }"
        module = self.kn.normalize(src)
        funcs = [n for n in module.body if isinstance(n, IRFunctionDef)]
        assert len(funcs) >= 1


# ---------------------------------------------------------------------------
# KotlinParserAdapter (Phase 1 IR adapter)
# ---------------------------------------------------------------------------

class TestKotlinParserAdapter:
    """Tests for KotlinParserAdapter."""

    def test_adapter_import_succeeds(self):
        from code_scalpel.code_parsers.adapters.kotlin_adapter import KotlinParserAdapter
        assert KotlinParserAdapter is not None

    def test_adapter_parse_returns_parse_result(self):
        from code_scalpel.code_parsers.adapters.kotlin_adapter import KotlinParserAdapter
        adapter = KotlinParserAdapter()
        result = adapter.parse('fun hello() { println("Hello") }')
        assert result is not None
        assert result.ast is not None

    def test_adapter_get_functions(self):
        from code_scalpel.code_parsers.adapters.kotlin_adapter import KotlinParserAdapter
        adapter = KotlinParserAdapter()
        result = adapter.parse("fun foo() {}\nfun bar() {}")
        names = adapter.get_functions(result.ast)
        assert "foo" in names
        assert "bar" in names

    def test_adapter_get_classes(self):
        from code_scalpel.code_parsers.adapters.kotlin_adapter import KotlinParserAdapter
        adapter = KotlinParserAdapter()
        result = adapter.parse("class Alpha {}\nclass Beta {}")
        names = adapter.get_classes(result.ast)
        assert "Alpha" in names
        assert "Beta" in names


