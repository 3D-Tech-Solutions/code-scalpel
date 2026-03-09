#!/usr/bin/env python3
"""Tests for Swift tool parsers — Phase 2 implementations.

[20260304_TEST] Comprehensive fixture-based tests for all 4 Swift parsers.
No external Swift tools need to be installed.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Lazy import helpers
# ---------------------------------------------------------------------------


def _import_swiftlint():
    from code_scalpel.code_parsers.swift_parsers.swift_parsers_SwiftLint import (
        SwiftLintParser,
        SwiftLintViolation,
        SwiftLintSeverity,
        SwiftLintConfig,
    )
    return SwiftLintParser, SwiftLintViolation, SwiftLintSeverity, SwiftLintConfig


def _import_tailor():
    from code_scalpel.code_parsers.swift_parsers.swift_parsers_Tailor import (
        TailorParser,
        TailorMetric,
        MetricType,
        TailorConfig,
    )
    return TailorParser, TailorMetric, MetricType, TailorConfig


def _import_sourcekitten():
    from code_scalpel.code_parsers.swift_parsers.swift_parsers_sourcekitten import (
        SourceKittenParser,
        SwiftSymbol,
        SwiftComplexity,
    )
    return SourceKittenParser, SwiftSymbol, SwiftComplexity


def _import_swiftformat():
    from code_scalpel.code_parsers.swift_parsers.swift_parsers_swiftformat import (
        SwiftFormatParser,
        FormattingIssue,
    )
    return SwiftFormatParser, FormattingIssue


def _import_registry():
    from code_scalpel.code_parsers.swift_parsers import SwiftParserRegistry
    return SwiftParserRegistry


# ---------------------------------------------------------------------------
# SwiftLint tests
# ---------------------------------------------------------------------------

_SWIFTLINT_JSON = json.dumps([
    {
        "character": None,
        "file": "/project/Sources/AppDelegate.swift",
        "line": 10,
        "reason": "Trailing whitespace.",
        "rule_id": "trailing_whitespace",
        "severity": "Warning",
        "type": "Trailing Whitespace",
    },
    {
        "character": 5,
        "file": "/project/Sources/AppDelegate.swift",
        "line": 25,
        "reason": "Force casts should be avoided.",
        "rule_id": "force_cast",
        "severity": "Error",
        "type": "Force Cast",
        "correctable": False,
    },
    {
        "character": 1,
        "file": "/project/Sources/ViewController.swift",
        "line": 3,
        "reason": "Lines should not span many characters.",
        "rule_id": "line_length",
        "severity": "Warning",
        "type": "Line Length",
        "correctable": True,
    },
])


class TestSwiftLintParser:
    """[20260304_TEST] Tests for SwiftLintParser."""

    def test_parse_json_output_count(self):
        SwiftLintParser, *_ = _import_swiftlint()
        parser = SwiftLintParser()
        results = parser.parse_json_report_output(_SWIFTLINT_JSON)
        assert len(results) == 3

    def test_parse_json_severity_warning(self):
        SwiftLintParser, SwiftLintViolation, SwiftLintSeverity, _ = _import_swiftlint()
        parser = SwiftLintParser()
        results = parser.parse_json_report_output(_SWIFTLINT_JSON)
        warnings = [r for r in results if r.severity == SwiftLintSeverity.WARNING]
        assert len(warnings) == 2

    def test_parse_json_severity_error(self):
        SwiftLintParser, SwiftLintViolation, SwiftLintSeverity, _ = _import_swiftlint()
        parser = SwiftLintParser()
        results = parser.parse_json_report_output(_SWIFTLINT_JSON)
        errors = [r for r in results if r.severity == SwiftLintSeverity.ERROR]
        assert len(errors) == 1
        assert errors[0].rule_id == "force_cast"

    def test_parse_json_file_path(self):
        SwiftLintParser, *_ = _import_swiftlint()
        parser = SwiftLintParser()
        results = parser.parse_json_report_output(_SWIFTLINT_JSON)
        assert results[0].file_path == "/project/Sources/AppDelegate.swift"

    def test_parse_json_line_number(self):
        SwiftLintParser, *_ = _import_swiftlint()
        parser = SwiftLintParser()
        results = parser.parse_json_report_output(_SWIFTLINT_JSON)
        assert results[0].line_number == 10

    def test_parse_json_correctable(self):
        SwiftLintParser, *_ = _import_swiftlint()
        parser = SwiftLintParser()
        results = parser.parse_json_report_output(_SWIFTLINT_JSON)
        correctable = [r for r in results if r.correctable]
        assert len(correctable) == 1
        assert correctable[0].rule_id == "line_length"

    def test_parse_empty_output(self):
        SwiftLintParser, *_ = _import_swiftlint()
        assert SwiftLintParser().parse_json_report_output("") == []

    def test_parse_invalid_json(self):
        SwiftLintParser, *_ = _import_swiftlint()
        assert SwiftLintParser().parse_json_report_output("not json") == []

    def test_categorize_violations(self):
        SwiftLintParser, *_ = _import_swiftlint()
        parser = SwiftLintParser()
        violations = parser.parse_json_report_output(_SWIFTLINT_JSON)
        cats = parser.categorize_violations(violations)
        # rule_ids: trailing_whitespace → "Trailing", force_cast → "Force", line_length → "Line"
        assert len(cats) == 3

    def test_calculate_metrics(self):
        SwiftLintParser, *_ = _import_swiftlint()
        parser = SwiftLintParser()
        violations = parser.parse_json_report_output(_SWIFTLINT_JSON)
        metrics = parser.calculate_metrics(violations)
        assert metrics["total"] == 3
        assert metrics["correctable"] == 1
        assert "error" in metrics["by_severity"]

    def test_generate_report_json(self):
        SwiftLintParser, *_ = _import_swiftlint()
        parser = SwiftLintParser()
        violations = parser.parse_json_report_output(_SWIFTLINT_JSON)
        report = parser.generate_report(violations, format="json")
        parsed = json.loads(report)
        assert len(parsed) == 3
        assert parsed[0]["rule_id"] == "trailing_whitespace"

    def test_generate_report_text(self):
        SwiftLintParser, *_ = _import_swiftlint()
        parser = SwiftLintParser()
        violations = parser.parse_json_report_output(_SWIFTLINT_JSON)
        report = parser.generate_report(violations, format="text")
        assert "trailing_whitespace" in report
        assert "force_cast" in report

    def test_detect_ios_specific(self):
        SwiftLintParser, *_ = _import_swiftlint()
        parser = SwiftLintParser()
        violations = parser.parse_json_report_output(_SWIFTLINT_JSON)
        ios_issues = parser.detect_ios_specific_issues(violations)
        # force_cast is in the iOS rules set
        assert any(v.rule_id == "force_cast" for v in ios_issues)

    def test_load_config(self, tmp_path):
        SwiftLintParser, _, __, SwiftLintConfig = _import_swiftlint()
        config_file = tmp_path / ".swiftlint.yml"
        config_file.write_text("disabled_rules:\n  - trailing_whitespace\n")
        parser = SwiftLintParser()
        cfg = parser.load_config(config_file)
        assert isinstance(cfg, SwiftLintConfig)
        assert cfg.config_file == config_file

    def test_execute_returns_list_when_tool_absent(self, monkeypatch):
        """execute_swiftlint should return [] gracefully if swiftlint is absent."""
        import shutil
        SwiftLintParser, *_ = _import_swiftlint()
        monkeypatch.setattr(shutil, "which", lambda _: None)
        parser = SwiftLintParser()
        result = parser.execute_swiftlint([Path("/tmp/fake.swift")])
        assert result == []


# ---------------------------------------------------------------------------
# Tailor tests
# ---------------------------------------------------------------------------

_TAILOR_JSON = json.dumps({
    "files": [
        {
            "path": "Sources/MyApp/ContentView.swift",
            "violations": [
                {
                    "location": {"line": 5, "column": 1},
                    "severity": "warning",
                    "rule": "trailing-whitespace",
                    "message": "Trailing whitespace is not allowed",
                },
                {
                    "location": {"line": 12, "column": 3},
                    "severity": "error",
                    "rule": "cyclomatic-complexity",
                    "message": "Function is too complex",
                },
            ],
        },
        {
            "path": "Sources/MyApp/Model.swift",
            "violations": [
                {
                    "location": {"line": 2, "column": 0},
                    "severity": "warning",
                    "rule": "line-length",
                    "message": "Line is too long (120 chars)",
                },
            ],
        },
    ],
    "summary": {"violations": 3},
})


class TestTailorParser:
    """[20260304_TEST] Tests for TailorParser."""

    def test_parse_json_count(self):
        TailorParser, *_ = _import_tailor()
        parser = TailorParser()
        results = parser.parse_json_report(_TAILOR_JSON)
        assert len(results) == 3

    def test_parse_json_file_path(self):
        TailorParser, *_ = _import_tailor()
        results = TailorParser().parse_json_report(_TAILOR_JSON)
        assert results[0].file_path == "Sources/MyApp/ContentView.swift"

    def test_parse_json_line_number(self):
        TailorParser, *_ = _import_tailor()
        results = TailorParser().parse_json_report(_TAILOR_JSON)
        assert results[0].line_number == 5

    def test_parse_json_severity(self):
        TailorParser, *_ = _import_tailor()
        results = TailorParser().parse_json_report(_TAILOR_JSON)
        warnings = [r for r in results if r.severity == "warning"]
        errors = [r for r in results if r.severity == "error"]
        assert len(warnings) == 2
        assert len(errors) == 1

    def test_parse_metric_type_complexity(self):
        TailorParser, TailorMetric, MetricType, _ = _import_tailor()
        results = TailorParser().parse_json_report(_TAILOR_JSON)
        complexity = [r for r in results if r.metric_type == MetricType.COMPLEXITY]
        assert len(complexity) == 1

    def test_parse_empty_output(self):
        TailorParser, *_ = _import_tailor()
        assert TailorParser().parse_json_report("") == []

    def test_parse_invalid_json(self):
        TailorParser, *_ = _import_tailor()
        assert TailorParser().parse_json_report("not json") == []

    def test_categorize_metrics(self):
        TailorParser, TailorMetric, MetricType, _ = _import_tailor()
        parser = TailorParser()
        metrics = parser.parse_json_report(_TAILOR_JSON)
        cats = parser.categorize_metrics(metrics)
        assert "COMPLEXITY" in cats or "STYLE" in cats or "LENGTH" in cats

    def test_detect_complexity_issues(self):
        TailorParser, TailorMetric, MetricType, _ = _import_tailor()
        parser = TailorParser()
        metrics = parser.parse_json_report(_TAILOR_JSON)
        complex_issues = parser.detect_complexity_issues(metrics)
        assert len(complex_issues) == 1

    def test_calculate_code_metrics(self):
        TailorParser, *_ = _import_tailor()
        parser = TailorParser()
        metrics = parser.parse_json_report(_TAILOR_JSON)
        result = parser.calculate_code_metrics(metrics)
        assert result["total"] == 3
        assert "by_type" in result
        assert "by_severity" in result

    def test_generate_report_json(self):
        TailorParser, *_ = _import_tailor()
        parser = TailorParser()
        metrics = parser.parse_json_report(_TAILOR_JSON)
        report = parser.generate_report(metrics, format="json")
        parsed = json.loads(report)
        assert len(parsed) == 3

    def test_generate_report_text(self):
        TailorParser, *_ = _import_tailor()
        parser = TailorParser()
        metrics = parser.parse_json_report(_TAILOR_JSON)
        report = parser.generate_report(metrics, format="text")
        assert "ContentView.swift" in report

    def test_analyze_metric_trends_empty(self):
        TailorParser, *_ = _import_tailor()
        assert TailorParser().analyze_metric_trends([]) == {}

    def test_analyze_metric_trends_improving(self):
        TailorParser, *_ = _import_tailor()
        data = [{"total": 10}, {"total": 7}, {"total": 4}]
        result = TailorParser().analyze_metric_trends(data)
        assert result["trend"] == "improving"
        assert result["delta"] == -6

    def test_execute_returns_list_when_absent(self, monkeypatch):
        import shutil
        TailorParser, *_ = _import_tailor()
        monkeypatch.setattr(shutil, "which", lambda _: None)
        assert TailorParser().execute_tailor([Path("/tmp/fake.swift")]) == []


# ---------------------------------------------------------------------------
# SourceKitten tests
# ---------------------------------------------------------------------------

_SOURCEKITTEN_JSON = json.dumps({
    "key.substructure": [
        {
            "key.kind": "source.lang.swift.decl.class",
            "key.name": "MyViewController",
            "key.parsed_range.start.line": 1,
            "key.parsed_range.start.column": 0,
            "key.accessibility": "public",
            "key.substructure": [
                {
                    "key.kind": "source.lang.swift.decl.function.method.instance",
                    "key.name": "viewDidLoad",
                    "key.parsed_range.start.line": 5,
                    "key.parsed_range.start.column": 4,
                    "key.accessibility": "internal",
                    "key.substructure": [],
                },
                {
                    "key.kind": "source.lang.swift.decl.var.instance",
                    "key.name": "label",
                    "key.parsed_range.start.line": 3,
                    "key.parsed_range.start.column": 4,
                    "key.accessibility": "internal",
                    "key.substructure": [],
                },
            ],
        },
        {
            "key.kind": "source.lang.swift.decl.function.free",
            "key.name": "setupApp",
            "key.parsed_range.start.line": 20,
            "key.parsed_range.start.column": 0,
            "key.accessibility": "internal",
            "key.substructure": [],
        },
    ]
})


class TestSourceKittenParser:
    """[20260304_TEST] Tests for SourceKittenParser."""

    def test_extract_symbols_via_dict(self):
        SourceKittenParser, SwiftSymbol, _ = _import_sourcekitten()
        parser = SourceKittenParser()
        import json
        data = json.loads(_SOURCEKITTEN_JSON)
        symbols = parser.extract_symbols(data)
        assert len(symbols) == 2  # top-level: class + free function

    def test_extract_class_name(self):
        SourceKittenParser, *_ = _import_sourcekitten()
        import json
        data = json.loads(_SOURCEKITTEN_JSON)
        symbols = SourceKittenParser().extract_symbols(data)
        names = [s.name for s in symbols]
        assert "MyViewController" in names

    def test_extract_class_kind(self):
        SourceKittenParser, *_ = _import_sourcekitten()
        import json
        data = json.loads(_SOURCEKITTEN_JSON)
        symbols = SourceKittenParser().extract_symbols(data)
        cls = next(s for s in symbols if s.name == "MyViewController")
        assert cls.kind == "class"

    def test_extract_children_count(self):
        SourceKittenParser, *_ = _import_sourcekitten()
        import json
        data = json.loads(_SOURCEKITTEN_JSON)
        symbols = SourceKittenParser().extract_symbols(data)
        cls = next(s for s in symbols if s.name == "MyViewController")
        assert len(cls.children) == 2

    def test_extract_function_kind(self):
        SourceKittenParser, *_ = _import_sourcekitten()
        import json
        data = json.loads(_SOURCEKITTEN_JSON)
        symbols = SourceKittenParser().extract_symbols(data)
        func = next(s for s in symbols if s.name == "setupApp")
        assert func.kind == "function"

    def test_extract_accessibility(self):
        SourceKittenParser, *_ = _import_sourcekitten()
        import json
        data = json.loads(_SOURCEKITTEN_JSON)
        symbols = SourceKittenParser().extract_symbols(data)
        cls = next(s for s in symbols if s.name == "MyViewController")
        assert cls.accessibility == "public"

    def test_parse_sourcekitten_output_from_file(self, tmp_path):
        SourceKittenParser, *_ = _import_sourcekitten()
        json_file = tmp_path / "ast.json"
        json_file.write_text(_SOURCEKITTEN_JSON, encoding="utf-8")
        symbols = SourceKittenParser().parse_sourcekitten_output(json_file)
        assert len(symbols) == 2

    def test_parse_sourcekitten_missing_file(self, tmp_path):
        SourceKittenParser, *_ = _import_sourcekitten()
        result = SourceKittenParser().parse_sourcekitten_output(tmp_path / "missing.json")
        assert result == []

    def test_analyze_complexity(self):
        SourceKittenParser, *_ = _import_sourcekitten()
        import json
        data = json.loads(_SOURCEKITTEN_JSON)
        symbols = SourceKittenParser().extract_symbols(data)
        # flatten children that are methods
        all_symbols = symbols + [c for s in symbols for c in s.children]
        complexities = SourceKittenParser().analyze_complexity(all_symbols)
        assert any(c.symbol_name == "viewDidLoad" for c in complexities)

    def test_extract_documentation(self):
        SourceKittenParser, SwiftSymbol, _ = _import_sourcekitten()
        sym = SwiftSymbol(
            name="doSomething",
            kind="function",
            file_path="File.swift",
            line_number=1,
            column=0,
            documentation="Does something useful.",
        )
        doc_map = SourceKittenParser().extract_documentation([sym])
        assert "doSomething" in doc_map
        assert doc_map["doSomething"] == "Does something useful."

    def test_extract_documentation_skips_undocumented(self):
        SourceKittenParser, SwiftSymbol, _ = _import_sourcekitten()
        sym = SwiftSymbol(
            name="silent",
            kind="function",
            file_path="f.swift",
            line_number=1,
            column=0,
        )
        assert SourceKittenParser().extract_documentation([sym]) == {}

    def test_generate_ast_report(self):
        SourceKittenParser, *_ = _import_sourcekitten()
        import json
        data = json.loads(_SOURCEKITTEN_JSON)
        symbols = SourceKittenParser().extract_symbols(data)
        report = SourceKittenParser().generate_ast_report(symbols)
        parsed = json.loads(report)
        assert len(parsed) == 2
        assert parsed[0]["kind"] == "class"

    def test_execute_raises_not_implemented(self):
        SourceKittenParser, *_ = _import_sourcekitten()
        with pytest.raises(NotImplementedError, match="sourcekitten"):
            SourceKittenParser().execute_sourcekitten([Path("/tmp/File.swift")])


# ---------------------------------------------------------------------------
# SwiftFormat tests
# ---------------------------------------------------------------------------

_SWIFTFORMAT_OUTPUT = """\
/project/Sources/AppDelegate.swift:5:1: warning: indent
/project/Sources/AppDelegate.swift:12:20: warning: trailingCommas
/project/Sources/ViewModel.swift:8:3: warning: braces
  /project/Sources/OldFile.swift  would reformat
"""


class TestSwiftFormatParser:
    """[20260304_TEST] Tests for SwiftFormatParser."""

    def test_parse_lint_output_count(self):
        SwiftFormatParser, _ = _import_swiftformat()
        parser = SwiftFormatParser()
        issues = parser.parse_lint_output(_SWIFTFORMAT_OUTPUT)
        # 3 structured lines + 1 "would reformat" line
        assert len(issues) == 4

    def test_parse_lint_output_file_path(self):
        SwiftFormatParser, _ = _import_swiftformat()
        issues = SwiftFormatParser().parse_lint_output(_SWIFTFORMAT_OUTPUT)
        assert issues[0].file_path == "/project/Sources/AppDelegate.swift"

    def test_parse_lint_output_line_number(self):
        SwiftFormatParser, _ = _import_swiftformat()
        issues = SwiftFormatParser().parse_lint_output(_SWIFTFORMAT_OUTPUT)
        assert issues[0].line_number == 5

    def test_parse_lint_output_column(self):
        SwiftFormatParser, _ = _import_swiftformat()
        issues = SwiftFormatParser().parse_lint_output(_SWIFTFORMAT_OUTPUT)
        assert issues[0].column == 1

    def test_parse_lint_output_issue_type(self):
        SwiftFormatParser, _ = _import_swiftformat()
        issues = SwiftFormatParser().parse_lint_output(_SWIFTFORMAT_OUTPUT)
        assert issues[0].issue_type == "warning"

    def test_parse_lint_reformat_entry(self):
        SwiftFormatParser, _ = _import_swiftformat()
        issues = SwiftFormatParser().parse_lint_output(_SWIFTFORMAT_OUTPUT)
        reformat = [i for i in issues if i.issue_type == "reformat"]
        assert len(reformat) == 1
        assert "OldFile.swift" in reformat[0].file_path

    def test_parse_empty_output(self):
        SwiftFormatParser, _ = _import_swiftformat()
        assert SwiftFormatParser().parse_lint_output("") == []

    def test_detect_formatting_violations(self):
        SwiftFormatParser, _ = _import_swiftformat()
        parser = SwiftFormatParser()
        issues = parser.parse_lint_output(_SWIFTFORMAT_OUTPUT)
        violations = parser.detect_formatting_violations(issues)
        # "warning" and "reformat" are NOT "info"/"debug"; all 4 should pass
        assert len(violations) == 4

    def test_generate_format_report(self):
        SwiftFormatParser, _ = _import_swiftformat()
        parser = SwiftFormatParser()
        issues = parser.parse_lint_output(_SWIFTFORMAT_OUTPUT)
        report = parser.generate_format_report(issues)
        assert "AppDelegate.swift" in report
        assert "ViewModel.swift" in report

    def test_parse_format_config_simple(self, tmp_path):
        SwiftFormatParser, _ = _import_swiftformat()
        config_file = tmp_path / ".swiftformat"
        config_file.write_text("--indent 4\n--maxwidth 120\n# comment line\n")
        cfg = SwiftFormatParser().parse_format_config(config_file)
        assert cfg.get("indent") == "4"
        assert cfg.get("maxwidth") == "120"

    def test_parse_format_config_missing_file(self, tmp_path):
        SwiftFormatParser, _ = _import_swiftformat()
        cfg = SwiftFormatParser().parse_format_config(tmp_path / "missing")
        assert cfg == {}

    def test_execute_returns_list_when_absent(self, monkeypatch):
        import shutil
        SwiftFormatParser, _ = _import_swiftformat()
        monkeypatch.setattr(shutil, "which", lambda _: None)
        assert SwiftFormatParser().execute_swiftformat([Path("/tmp/fake.swift")]) == []


# ---------------------------------------------------------------------------
# SwiftParserRegistry tests
# ---------------------------------------------------------------------------


class TestSwiftParserRegistry:
    """[20260304_TEST] Tests for SwiftParserRegistry."""

    def test_get_swiftlint_parser(self):
        SwiftParserRegistry = _import_registry()
        from code_scalpel.code_parsers.swift_parsers.swift_parsers_SwiftLint import SwiftLintParser
        parser = SwiftParserRegistry().get_parser("swiftlint")
        assert isinstance(parser, SwiftLintParser)

    def test_get_tailor_parser(self):
        SwiftParserRegistry = _import_registry()
        from code_scalpel.code_parsers.swift_parsers.swift_parsers_Tailor import TailorParser
        parser = SwiftParserRegistry().get_parser("tailor")
        assert isinstance(parser, TailorParser)

    def test_get_sourcekitten_parser(self):
        SwiftParserRegistry = _import_registry()
        from code_scalpel.code_parsers.swift_parsers.swift_parsers_sourcekitten import SourceKittenParser
        parser = SwiftParserRegistry().get_parser("sourcekitten")
        assert isinstance(parser, SourceKittenParser)

    def test_get_swiftformat_parser(self):
        SwiftParserRegistry = _import_registry()
        from code_scalpel.code_parsers.swift_parsers.swift_parsers_swiftformat import SwiftFormatParser
        parser = SwiftParserRegistry().get_parser("swiftformat")
        assert isinstance(parser, SwiftFormatParser)

    def test_unknown_tool_raises(self):
        SwiftParserRegistry = _import_registry()
        with pytest.raises(ValueError, match="Unknown Swift parser tool"):
            SwiftParserRegistry().get_parser("nonexistent_tool")

    def test_case_insensitive_lookup(self):
        SwiftParserRegistry = _import_registry()
        from code_scalpel.code_parsers.swift_parsers.swift_parsers_SwiftLint import SwiftLintParser
        parser = SwiftParserRegistry().get_parser("SwiftLint")
        assert isinstance(parser, SwiftLintParser)
