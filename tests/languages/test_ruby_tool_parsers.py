#!/usr/bin/env python3
"""Tests for Ruby tool parsers — Phase 2 implementations.

[20260304_TEST] Comprehensive fixture-based tests for all 7 Ruby parsers.
No external Ruby tools need to be installed.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Lazy import helpers
# ---------------------------------------------------------------------------


def _import_rubocop():
    from code_scalpel.code_parsers.ruby_parsers.ruby_parsers_RuboCop import (
        RuboCopParser,
        RuboCopViolation,
        RuboCopSeverity,
        RuboCopConfig,
    )
    return RuboCopParser, RuboCopViolation, RuboCopSeverity, RuboCopConfig


def _import_brakeman():
    from code_scalpel.code_parsers.ruby_parsers.ruby_parsers_brakeman import (
        BrakemanParser,
        BrakemanVulnerability,
        VulnerabilityType,
    )
    return BrakemanParser, BrakemanVulnerability, VulnerabilityType


def _import_reek():
    from code_scalpel.code_parsers.ruby_parsers.ruby_parsers_Reek import (
        ReekParser,
        ReekSmell,
        SmellType,
    )
    return ReekParser, ReekSmell, SmellType


def _import_bundler():
    from code_scalpel.code_parsers.ruby_parsers.ruby_parsers_bundler import (
        BundlerParser,
        Gem,
    )
    return BundlerParser, Gem


def _import_fasterer():
    from code_scalpel.code_parsers.ruby_parsers.ruby_parsers_fasterer import (
        FastererParser,
        PerformanceIssue,
    )
    return FastererParser, PerformanceIssue


def _import_simplecov():
    from code_scalpel.code_parsers.ruby_parsers.ruby_parsers_simplecov import (
        SimpleCovParser,
        FileCoverage,
        CoverageMetrics,
    )
    return SimpleCovParser, FileCoverage, CoverageMetrics


def _import_ast():
    from code_scalpel.code_parsers.ruby_parsers.ruby_parsers_ast import (
        RubyASTParser,
        RubyClass,
        RubyMethod,
    )
    return RubyASTParser, RubyClass, RubyMethod


def _import_registry():
    from code_scalpel.code_parsers.ruby_parsers import RubyParserRegistry
    return RubyParserRegistry


# ---------------------------------------------------------------------------
# RuboCop tests
# ---------------------------------------------------------------------------


class TestRuboCopParser:
    """[20260304_TEST] Tests for RuboCopParser."""

    _RUBOCOP_OUTPUT = json.dumps({
        "files": [
            {
                "path": "app/models/user.rb",
                "offenses": [
                    {
                        "cop_name": "Style/StringLiterals",
                        "severity": "convention",
                        "message": "Prefer single-quoted strings.",
                        "location": {"line": 5},
                    },
                    {
                        "cop_name": "Metrics/MethodLength",
                        "severity": "warning",
                        "message": "Method has too many lines.",
                        "location": {"line": 10},
                    },
                ],
            }
        ]
    })

    def test_imports(self):
        RuboCopParser, RuboCopViolation, RuboCopSeverity, RuboCopConfig = _import_rubocop()
        assert RuboCopParser is not None

    def test_parse_json_output(self):
        RuboCopParser, *_ = _import_rubocop()
        parser = RuboCopParser()
        violations = parser.parse_json_output(self._RUBOCOP_OUTPUT)
        assert len(violations) == 2
        assert violations[0].file_path == "app/models/user.rb"
        assert violations[0].cop_name == "Style/StringLiterals"

    def test_categorize_violations(self):
        RuboCopParser, *_ = _import_rubocop()
        parser = RuboCopParser()
        violations = parser.parse_json_output(self._RUBOCOP_OUTPUT)
        cats = parser.categorize_violations(violations)
        assert isinstance(cats, dict)

    def test_generate_report(self):
        RuboCopParser, *_ = _import_rubocop()
        parser = RuboCopParser()
        violations = parser.parse_json_output(self._RUBOCOP_OUTPUT)
        report = parser.generate_report(violations)
        data = json.loads(report)
        assert data["tool"] == "rubocop"
        assert data["total_violations"] == 2

    def test_calculate_metrics(self):
        RuboCopParser, *_ = _import_rubocop()
        parser = RuboCopParser()
        violations = parser.parse_json_output(self._RUBOCOP_OUTPUT)
        metrics = parser.calculate_metrics(violations)
        assert metrics["total"] == 2

    def test_execute_returns_list_when_tool_absent(self):
        """execute_rubocop returns [] when rubocop not installed."""
        import shutil
        if shutil.which("rubocop"):
            pytest.skip("rubocop is installed — skipping graceful-degradation test")
        RuboCopParser, *_ = _import_rubocop()
        parser = RuboCopParser()
        result = parser.execute_rubocop([Path(".")])
        assert result == []


# ---------------------------------------------------------------------------
# Brakeman tests
# ---------------------------------------------------------------------------


class TestBrakemanParser:
    """[20260304_TEST] Tests for BrakemanParser."""

    _BRAKEMAN_OUTPUT = json.dumps({
        "warnings": [
            {
                "warning_type": "SQL Injection",
                "message": "Possible SQL injection via user input",
                "file": "app/controllers/users_controller.rb",
                "line": 25,
                "confidence": "High",
                "code": "User.where(params[:query])",
            },
            {
                "warning_type": "Cross-Site Scripting",
                "message": "Unescaped user input in HTML output",
                "file": "app/views/users/index.html.erb",
                "line": 10,
                "confidence": "Medium",
                "code": "raw user_data",
            },
        ]
    })

    def test_imports(self):
        _import_brakeman()

    def test_parse_json_output(self):
        BrakemanParser, BrakemanVulnerability, _ = _import_brakeman()
        parser = BrakemanParser()
        vulns = parser.parse_json_output(self._BRAKEMAN_OUTPUT)
        assert len(vulns) == 2
        assert vulns[0].vuln_type == "SQL Injection"
        assert vulns[0].file_path == "app/controllers/users_controller.rb"

    def test_categorize_vulnerabilities(self):
        BrakemanParser, *_ = _import_brakeman()
        parser = BrakemanParser()
        vulns = parser.parse_json_output(self._BRAKEMAN_OUTPUT)
        cats = parser.categorize_vulnerabilities(vulns)
        assert isinstance(cats, dict)

    def test_detect_sql_injection(self):
        BrakemanParser, *_ = _import_brakeman()
        parser = BrakemanParser()
        vulns = parser.parse_json_output(self._BRAKEMAN_OUTPUT)
        sql_vulns = parser.detect_sql_injection(vulns)
        assert len(sql_vulns) == 1

    def test_generate_security_report(self):
        BrakemanParser, *_ = _import_brakeman()
        parser = BrakemanParser()
        vulns = parser.parse_json_output(self._BRAKEMAN_OUTPUT)
        report = parser.generate_security_report(vulns)
        data = json.loads(report)
        assert data["tool"] == "brakeman"
        assert data["total_vulnerabilities"] == 2

    def test_cwe_map_populated(self):
        from code_scalpel.code_parsers.ruby_parsers.ruby_parsers_brakeman import BRAKEMAN_CWE_MAP
        assert "SQL Injection" in BRAKEMAN_CWE_MAP

    def test_execute_returns_list_when_tool_absent(self):
        import shutil
        if shutil.which("brakeman"):
            pytest.skip("brakeman is installed")
        BrakemanParser, *_ = _import_brakeman()
        parser = BrakemanParser()
        assert parser.execute_brakeman([Path(".")]) == []


# ---------------------------------------------------------------------------
# Reek tests
# ---------------------------------------------------------------------------


class TestReekParser:
    """[20260304_TEST] Tests for ReekParser."""

    _REEK_OUTPUT = json.dumps([
        {
            "smell_type": "LongMethod",
            "message": "UserService#process has approx 25 statements",
            "context": "UserService#process",
            "source": "app/services/user_service.rb",
            "lines": [5, 30],
        },
        {
            "smell_type": "FeatureEnvy",
            "message": "Order#calculate uses target more than self",
            "context": "Order#calculate",
            "source": "app/models/order.rb",
            "lines": [15],
        },
    ])

    def test_imports(self):
        _import_reek()

    def test_parse_json_output(self):
        ReekParser, ReekSmell, SmellType = _import_reek()
        parser = ReekParser()
        smells = parser.parse_json_output(self._REEK_OUTPUT)
        assert len(smells) == 2
        assert smells[0].smell_type == "LongMethod"

    def test_categorize_smells(self):
        ReekParser, *_ = _import_reek()
        parser = ReekParser()
        smells = parser.parse_json_output(self._REEK_OUTPUT)
        cats = parser.categorize_smells(smells)
        assert isinstance(cats, dict)
        assert "LongMethod" in cats

    def test_detect_long_methods(self):
        ReekParser, *_ = _import_reek()
        parser = ReekParser()
        smells = parser.parse_json_output(self._REEK_OUTPUT)
        long_methods = parser.detect_long_methods(smells)
        assert len(long_methods) == 1

    def test_generate_report(self):
        ReekParser, *_ = _import_reek()
        parser = ReekParser()
        smells = parser.parse_json_output(self._REEK_OUTPUT)
        report = parser.generate_report(smells)
        data = json.loads(report)
        assert data["tool"] == "reek"
        assert data["total_smells"] == 2

    def test_execute_returns_list_when_tool_absent(self):
        import shutil
        if shutil.which("reek"):
            pytest.skip("reek is installed")
        ReekParser, *_ = _import_reek()
        parser = ReekParser()
        assert parser.execute_reek([Path(".")]) == []


# ---------------------------------------------------------------------------
# Bundler tests
# ---------------------------------------------------------------------------


class TestBundlerParser:
    """[20260304_TEST] Tests for BundlerParser."""

    _GEMFILE_CONTENT = """\
source 'https://rubygems.org'

gem 'rails', '~> 7.0'
gem 'pg', '>= 1.1'
gem 'puma', '~> 5.0'
gem 'devise', '~> 4.8'
"""

    _LOCKFILE_CONTENT = """\
GEM
  remote: https://rubygems.org/
  specs:
    rails (7.0.4)
    pg (1.4.5)
    puma (5.6.5)
    devise (4.8.1)

BUNDLED WITH
   2.3.7
"""

    def test_imports(self):
        _import_bundler()

    def test_extract_gems_from_gemfile_text(self):
        BundlerParser, Gem = _import_bundler()
        parser = BundlerParser()
        gems = parser.extract_gems(self._GEMFILE_CONTENT)
        names = [g.name for g in gems]
        assert "rails" in names
        assert "pg" in names

    def test_extract_locked_versions(self):
        BundlerParser, Gem = _import_bundler()
        parser = BundlerParser()
        locked = parser.extract_locked_versions(self._LOCKFILE_CONTENT)
        assert isinstance(locked, dict)
        assert "rails" in locked
        assert locked["rails"] == "7.0.4"

    def test_generate_dependency_report(self):
        BundlerParser, Gem = _import_bundler()
        parser = BundlerParser()
        gems = parser.extract_gems(self._GEMFILE_CONTENT)
        report = parser.generate_dependency_report(gems)
        data = json.loads(report)
        assert data["tool"] == "bundler"
        assert "gems" in data

    def test_scan_for_vulnerabilities_returns_list_without_tool(self):
        import shutil
        if shutil.which("bundler-audit"):
            pytest.skip("bundler-audit is installed")
        BundlerParser, Gem = _import_bundler()
        parser = BundlerParser()
        gems = parser.extract_gems(self._GEMFILE_CONTENT)
        result = parser.scan_for_vulnerabilities(gems)
        assert isinstance(result, list)


# ---------------------------------------------------------------------------
# Fasterer tests
# ---------------------------------------------------------------------------


class TestFastererParser:
    """[20260304_TEST] Tests for FastererParser."""

    _FASTERER_OUTPUT = """\
app/services/data_processor.rb
  Line 15: shuffle.first is slower than sample.
  Line 23: sort.first is slower than min.
app/models/report.rb
  Line 8: Use map instead of each_with_object.
"""

    def test_imports(self):
        _import_fasterer()

    def test_parse_text_output(self):
        FastererParser, PerformanceIssue = _import_fasterer()
        parser = FastererParser()
        issues = parser.parse_text_output(self._FASTERER_OUTPUT)
        assert len(issues) == 3
        assert issues[0].file_path == "app/services/data_processor.rb"
        assert issues[0].line_number == 15

    def test_categorize_issues(self):
        FastererParser, PerformanceIssue = _import_fasterer()
        parser = FastererParser()
        issues = parser.parse_text_output(self._FASTERER_OUTPUT)
        cats = parser.categorize_issues(issues)
        assert isinstance(cats, dict)

    def test_generate_optimization_report(self):
        FastererParser, PerformanceIssue = _import_fasterer()
        parser = FastererParser()
        issues = parser.parse_text_output(self._FASTERER_OUTPUT)
        report = parser.generate_optimization_report(issues)
        data = json.loads(report)
        assert data["tool"] == "fasterer"
        assert data["total_issues"] == 3

    def test_calculate_performance_metrics(self):
        FastererParser, PerformanceIssue = _import_fasterer()
        parser = FastererParser()
        issues = parser.parse_text_output(self._FASTERER_OUTPUT)
        metrics = parser.calculate_performance_metrics(issues)
        assert metrics["total_issues"] == 3

    def test_execute_returns_list_when_tool_absent(self):
        import shutil
        if shutil.which("fasterer"):
            pytest.skip("fasterer is installed")
        FastererParser, _ = _import_fasterer()
        parser = FastererParser()
        assert parser.execute_fasterer([Path(".")]) == []

    def test_empty_output(self):
        FastererParser, _ = _import_fasterer()
        parser = FastererParser()
        issues = parser.parse_text_output("")
        assert issues == []


# ---------------------------------------------------------------------------
# SimpleCov tests
# ---------------------------------------------------------------------------


class TestSimpleCovParser:
    """[20260304_TEST] Tests for SimpleCovParser."""

    _RESULTSET = {
        "RSpec": {
            "coverage": {
                "app/models/user.rb": {
                    "lines": [None, 5, 3, 0, None, 2, 0, 1]
                },
                "app/controllers/users_controller.rb": {
                    "lines": [1, 1, 0, 0, None]
                },
            }
        }
    }

    def test_imports(self):
        _import_simplecov()

    def test_parse_coverage_data(self):
        SimpleCovParser, FileCoverage, CoverageMetrics = _import_simplecov()
        parser = SimpleCovParser()
        files = parser.parse_coverage_data(
            {k: v["lines"] for k, v in self._RESULTSET["RSpec"]["coverage"].items()}
        )
        assert len(files) == 2
        user_file = next(f for f in files if "user" in f.file_path)
        assert user_file.covered_lines == 4
        assert user_file.uncovered_lines == 2

    def test_calculate_coverage_metrics(self):
        SimpleCovParser, FileCoverage, CoverageMetrics = _import_simplecov()
        parser = SimpleCovParser()
        files = parser.parse_coverage_data(
            {k: v["lines"] for k, v in self._RESULTSET["RSpec"]["coverage"].items()}
        )
        metrics = parser.calculate_coverage_metrics(files)
        assert metrics.total_files == 2
        assert metrics.covered_lines + metrics.uncovered_lines == metrics.total_lines

    def test_identify_uncovered_lines(self):
        SimpleCovParser, FileCoverage, CoverageMetrics = _import_simplecov()
        parser = SimpleCovParser()
        files = parser.parse_coverage_data(
            {k: v["lines"] for k, v in self._RESULTSET["RSpec"]["coverage"].items()}
        )
        user_file = next(f for f in files if "user" in f.file_path)
        uncovered = parser.identify_uncovered_lines(user_file)
        assert isinstance(uncovered, list)
        assert len(uncovered) == 2

    def test_identify_coverage_hotspots(self):
        SimpleCovParser, FileCoverage, CoverageMetrics = _import_simplecov()
        parser = SimpleCovParser()
        files = parser.parse_coverage_data(
            {k: v["lines"] for k, v in self._RESULTSET["RSpec"]["coverage"].items()}
        )
        metrics = parser.calculate_coverage_metrics(files)
        hotspots = parser.identify_coverage_hotspots(metrics.files, threshold=100.0)
        assert isinstance(hotspots, list)

    def test_generate_coverage_report(self):
        SimpleCovParser, FileCoverage, CoverageMetrics = _import_simplecov()
        parser = SimpleCovParser()
        files = parser.parse_coverage_data(
            {k: v["lines"] for k, v in self._RESULTSET["RSpec"]["coverage"].items()}
        )
        metrics = parser.calculate_coverage_metrics(files)
        report = parser.generate_coverage_report(metrics)
        data = json.loads(report)
        assert data["tool"] == "simplecov"
        assert "coverage_percent" in data

    def test_parse_resultset_json(self, tmp_path):
        import json as _json
        SimpleCovParser, FileCoverage, CoverageMetrics = _import_simplecov()
        rs_file = tmp_path / ".resultset.json"
        rs_file.write_text(_json.dumps(self._RESULTSET), encoding="utf-8")
        parser = SimpleCovParser()
        metrics = parser.parse_resultset_json(rs_file)
        assert metrics.total_files == 2

    def test_analyze_coverage_trends(self):
        SimpleCovParser, FileCoverage, CoverageMetrics = _import_simplecov()
        parser = SimpleCovParser()
        m1 = CoverageMetrics(total_files=1, covered_lines=40, uncovered_lines=10, total_lines=50, coverage_percent=80.0)
        m2 = CoverageMetrics(total_files=1, covered_lines=45, uncovered_lines=5, total_lines=50, coverage_percent=90.0)
        trends = parser.analyze_coverage_trends([m1, m2])
        assert trends["direction"] == "improving"


# ---------------------------------------------------------------------------
# RubyASTParser tests
# ---------------------------------------------------------------------------


class TestRubyASTParser:
    """[20260304_TEST] Tests for RubyASTParser (fixture-based, no Ruby IR needed)."""

    def test_imports(self):
        _import_ast()

    def test_parse_code_returns_something(self):
        """parse_code should return an IRModule (or None on missing tree-sitter-ruby)."""
        try:
            RubyASTParser, RubyClass, RubyMethod = _import_ast()
            parser = RubyASTParser()
            from code_scalpel.ir.normalizers.ruby_normalizer import RubyNormalizer  # noqa
        except ImportError:
            pytest.skip("tree-sitter-ruby not installed")
        result = parser.parse_code("def hello; 'world'; end")
        assert result is not None

    def test_extract_classes_from_ir(self):
        """extract_classes reads IRClass nodes correctly."""
        try:
            from code_scalpel.ir.normalizers.ruby_normalizer import RubyNormalizer
        except ImportError:
            pytest.skip("tree-sitter-ruby not installed")
        RubyASTParser, RubyClass, RubyMethod = _import_ast()
        parser = RubyASTParser()
        ir = parser.parse_code("class Foo; def bar; end; end")
        classes = parser.extract_classes(ir)
        assert any(c.name == "Foo" for c in classes)

    def test_extract_methods_from_ir(self):
        """extract_methods returns top-level methods."""
        try:
            from code_scalpel.ir.normalizers.ruby_normalizer import RubyNormalizer
        except ImportError:
            pytest.skip("tree-sitter-ruby not installed")
        RubyASTParser, RubyClass, RubyMethod = _import_ast()
        parser = RubyASTParser()
        ir = parser.parse_code("def greet(name)\n  'hello '\n end")
        methods = parser.extract_methods(ir)
        assert any(m.name == "greet" for m in methods)

    def test_generate_report_returns_json(self):
        """generate_report returns valid JSON."""
        try:
            from code_scalpel.ir.normalizers.ruby_normalizer import RubyNormalizer
        except ImportError:
            pytest.skip("tree-sitter-ruby not installed")
        RubyASTParser, RubyClass, RubyMethod = _import_ast()
        parser = RubyASTParser()
        ir = parser.parse_code("class Foo; end")
        report = parser.generate_report(ir)
        data = json.loads(report)
        assert data["tool"] == "ruby_ast"


# ---------------------------------------------------------------------------
# RubyParserRegistry tests
# ---------------------------------------------------------------------------


class TestRubyParserRegistry:
    """[20260304_TEST] Tests for RubyParserRegistry factory."""

    def test_import_registry(self):
        _import_registry()

    def test_available_tools(self):
        RubyParserRegistry = _import_registry()
        reg = RubyParserRegistry()
        tools = reg.available_tools()
        assert "rubocop" in tools
        assert "brakeman" in tools
        assert "reek" in tools
        assert "bundler-audit" in tools
        assert "fasterer" in tools
        assert "simplecov" in tools
        assert "ast" in tools

    def test_get_parser_returns_instance(self):
        RubyParserRegistry = _import_registry()
        reg = RubyParserRegistry()
        rubocop = reg.get_parser("rubocop")
        from code_scalpel.code_parsers.ruby_parsers.ruby_parsers_RuboCop import RuboCopParser
        assert isinstance(rubocop, RuboCopParser)

    def test_get_parser_cached(self):
        RubyParserRegistry = _import_registry()
        reg = RubyParserRegistry()
        p1 = reg.get_parser("rubocop")
        p2 = reg.get_parser("rubocop")
        assert p1 is p2

    def test_get_parser_unknown_raises(self):
        RubyParserRegistry = _import_registry()
        reg = RubyParserRegistry()
        with pytest.raises(ValueError, match="Unknown Ruby parser"):
            reg.get_parser("nonexistent")
