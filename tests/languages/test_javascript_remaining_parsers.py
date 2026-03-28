#!/usr/bin/env python3
# [20260303_FEATURE] Test suite for Stage 4b JavaScript parser implementations
"""
Tests for the five JavaScript stub-to-complete parser implementations:
  - javascript_parsers_npm_audit
  - javascript_parsers_jsdoc
  - javascript_parsers_package_json
  - javascript_parsers_test_detection
  - javascript_parsers_webpack

All tests are pure (no external tools required).
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

# ---------------------------------------------------------------------------
# TestNpmAuditParser
# ---------------------------------------------------------------------------


class TestNpmAuditParser:
    """Tests for NpmAuditParser (npm audit --json v2 format)."""

    _JSON_OUTPUT = json.dumps(
        {
            "auditReportVersion": 2,
            "vulnerabilities": {
                "lodash": {
                    "name": "lodash",
                    "severity": "high",
                    "range": "<4.17.21",
                    "via": [
                        {
                            "source": 1084,
                            "name": "lodash",
                            "dependency": "lodash",
                            "url": "https://npmjs.com/advisories/1084",
                            "severity": "high",
                            "cwe": ["CWE-1321"],
                        }
                    ],
                },
                "axios": {
                    "name": "axios",
                    "severity": "critical",
                    "range": "<1.6.0",
                    "via": [
                        {
                            "source": 2000,
                            "url": "https://npmjs.com/advisories/2000",
                            "severity": "critical",
                            "cwe": ["CWE-918", "CWE-601"],
                        }
                    ],
                },
            },
            "metadata": {"vulnerabilities": {"total": 2, "high": 1, "critical": 1}},
        }
    )

    def _get_parser(self):
        from code_scalpel.code_parsers.javascript_parsers.javascript_parsers_npm_audit import (
            NpmAuditParser,
        )

        return NpmAuditParser()

    def test_parse_v2_json_basic(self):
        """parse_v2_json returns one finding per vulnerable package."""
        parser = self._get_parser()
        findings = parser.parse_v2_json(self._JSON_OUTPUT)
        assert len(findings) == 2
        names = {f.package_name for f in findings}
        assert "lodash" in names
        assert "axios" in names

    def test_parse_v2_json_severity_and_range(self):
        """Severity and vulnerable range are extracted correctly."""
        parser = self._get_parser()
        findings = parser.parse_v2_json(self._JSON_OUTPUT)
        lodash = next(f for f in findings if f.package_name == "lodash")
        assert lodash.severity == "high"
        assert lodash.vulnerable_range == "<4.17.21"

    def test_map_to_cwe(self):
        """map_to_cwe groups findings by CWE ID."""
        parser = self._get_parser()
        findings = parser.parse_v2_json(self._JSON_OUTPUT)
        cwe_map = parser.map_to_cwe(findings)
        assert "CWE-1321" in cwe_map
        assert cwe_map["CWE-1321"][0].package_name == "lodash"
        assert "CWE-918" in cwe_map

    def test_get_severity_summary(self):
        """get_severity_summary returns correct counts per level."""
        parser = self._get_parser()
        findings = parser.parse_v2_json(self._JSON_OUTPUT)
        summary = parser.get_severity_summary(findings)
        assert summary["high"] == 1
        assert summary["critical"] == 1
        assert summary["moderate"] == 0

    def test_execute_npm_audit_no_npm(self, monkeypatch):
        """execute_npm_audit returns [] when npm is not on PATH."""
        monkeypatch.setattr(shutil, "which", lambda _: None)
        parser = self._get_parser()
        assert parser.execute_npm_audit(".") == []

    def test_generate_report_structure(self):
        """generate_report produces valid JSON with expected top-level keys."""
        parser = self._get_parser()
        findings = parser.parse_v2_json(self._JSON_OUTPUT)
        report_str = parser.generate_report(findings)
        report = json.loads(report_str)
        assert report["tool"] == "npm-audit"
        assert report["total"] == 2
        assert "findings" in report
        assert "severity_summary" in report

    def test_parse_v2_json_invalid_json_returns_empty(self):
        """parse_v2_json returns [] on unparseable input."""
        parser = self._get_parser()
        assert parser.parse_v2_json("not json at all") == []

    def test_parse_v2_json_empty_vulnerabilities(self):
        """parse_v2_json handles a clean audit with no vulnerabilities."""
        clean = json.dumps(
            {
                "auditReportVersion": 2,
                "vulnerabilities": {},
                "metadata": {"vulnerabilities": {"total": 0}},
            }
        )
        parser = self._get_parser()
        assert parser.parse_v2_json(clean) == []

    def test_cwe_ids_populated(self):
        """CWE IDs are correctly extracted into finding.cwe_ids."""
        parser = self._get_parser()
        findings = parser.parse_v2_json(self._JSON_OUTPUT)
        axios = next(f for f in findings if f.package_name == "axios")
        assert "CWE-918" in axios.cwe_ids
        assert "CWE-601" in axios.cwe_ids


# ---------------------------------------------------------------------------
# TestJsDocParser
# ---------------------------------------------------------------------------


class TestJsDocParser:
    """Tests for JsDocParser (regex-based JSDoc extraction)."""

    _CODE = """\
/**
 * Add two numbers together.
 * @param {number} a - First operand
 * @param {number} b - Second operand
 * @returns {number} Sum
 */
export function add(a, b) {
    return a + b;
}

/**
 * Multiply two numbers.
 * @param {number} x
 * @param {number} y
 */
export async function multiply(x, y) {
    return x * y;
}

export function undocumented() {
    return 42;
}
"""

    def _get_parser(self):
        from code_scalpel.code_parsers.javascript_parsers.javascript_parsers_jsdoc import (
            JsDocParser,
        )

        return JsDocParser()

    def test_extract_jsdoc_comments_count(self):
        """extract_jsdoc_comments finds all documented symbols."""
        parser = self._get_parser()
        comments = parser.extract_jsdoc_comments(self._CODE)
        assert len(comments) == 2

    def test_extract_jsdoc_description(self):
        """Description text is captured from the first doc-block."""
        parser = self._get_parser()
        comments = parser.extract_jsdoc_comments(self._CODE)
        assert "Add two numbers" in comments[0].description

    def test_extract_jsdoc_tags_present(self):
        """@param and @returns tags are parsed."""
        parser = self._get_parser()
        comments = parser.extract_jsdoc_comments(self._CODE)
        tag_names = {t["tag"] for t in comments[0].tags}
        assert "param" in tag_names
        assert "returns" in tag_names

    def test_get_documentation_coverage(self):
        """Coverage reflects 2 documented out of 3 total."""
        parser = self._get_parser()
        cov = parser.get_documentation_coverage(self._CODE)
        assert cov["total_functions"] == 3
        assert cov["documented"] == 2
        assert 60.0 <= cov["coverage_pct"] <= 70.0

    def test_list_undocumented_exports(self):
        """undocumented function is returned by list_undocumented_exports."""
        parser = self._get_parser()
        unset = parser.list_undocumented_exports(self._CODE)
        assert "undocumented" in unset
        assert "add" not in unset

    def test_parse_jsdoc_json_basic(self):
        """parse_jsdoc_json handles jsdoc -X style output."""
        parser = self._get_parser()
        jsdoc_output = json.dumps(
            [
                {
                    "comment": "/** Get user by ID. */",
                    "meta": {"filename": "users.js", "lineno": 10},
                }
            ]
        )
        results = parser.parse_jsdoc_json(jsdoc_output)
        assert len(results) == 1
        assert results[0].file_path == "users.js"
        assert results[0].line == 10

    def test_generate_report_structure(self):
        """generate_report returns valid JSON with tool key."""
        parser = self._get_parser()
        comments = parser.extract_jsdoc_comments(self._CODE)
        report = json.loads(parser.generate_report(comments))
        assert report["tool"] == "jsdoc"
        assert "data" in report


# ---------------------------------------------------------------------------
# TestPackageJsonParser
# ---------------------------------------------------------------------------


class TestPackageJsonParser:
    """Tests for PackageJsonParser (pure JSON file reader)."""

    _PKG = {
        "name": "my-app",
        "version": "1.2.3",
        "description": "A sample app",
        "license": "MIT",
        "main": "index.js",
        "dependencies": {"react": "^18.0.0", "react-dom": "^18.0.0"},
        "devDependencies": {"jest": "^29.0.0", "typescript": "^5.0.0"},
        "scripts": {"test": "jest", "build": "tsc"},
        "engines": {"node": ">=18.0.0"},
    }

    def _get_parser(self):
        from code_scalpel.code_parsers.javascript_parsers.javascript_parsers_package_json import (
            PackageJsonParser,
        )

        return PackageJsonParser()

    def _write_pkg(self, tmp_path: Path) -> Path:
        p = tmp_path / "package.json"
        p.write_text(json.dumps(self._PKG), encoding="utf-8")
        return p

    def test_parse_package_json_fields(self, tmp_path):
        """Basic fields are populated from the JSON file."""
        parser = self._get_parser()
        pkg = parser.parse_package_json(self._write_pkg(tmp_path))
        assert pkg.name == "my-app"
        assert pkg.version == "1.2.3"
        assert pkg.license == "MIT"

    def test_get_dependencies(self, tmp_path):
        """get_dependencies returns correct tuples."""
        parser = self._get_parser()
        pkg = parser.parse_package_json(self._write_pkg(tmp_path))
        deps = dict(parser.get_dependencies(pkg))
        assert "react" in deps
        assert "react-dom" in deps

    def test_get_dev_dependencies(self, tmp_path):
        """get_dev_dependencies returns devDeps."""
        parser = self._get_parser()
        pkg = parser.parse_package_json(self._write_pkg(tmp_path))
        dev_deps = dict(parser.get_dev_dependencies(pkg))
        assert "jest" in dev_deps
        assert "typescript" in dev_deps

    def test_detect_framework_react(self, tmp_path):
        """React is detected from dependencies."""
        parser = self._get_parser()
        pkg = parser.parse_package_json(self._write_pkg(tmp_path))
        assert parser.detect_framework(pkg) == "react"

    def test_get_node_engine_requirement(self, tmp_path):
        """engines.node is returned correctly."""
        parser = self._get_parser()
        pkg = parser.parse_package_json(self._write_pkg(tmp_path))
        assert parser.get_node_engine_requirement(pkg) == ">=18.0.0"

    def test_get_scripts(self, tmp_path):
        """scripts dict is accessible."""
        parser = self._get_parser()
        pkg = parser.parse_package_json(self._write_pkg(tmp_path))
        scripts = parser.get_scripts(pkg)
        assert scripts["test"] == "jest"
        assert scripts["build"] == "tsc"

    def test_generate_report_structure(self, tmp_path):
        """generate_report returns valid JSON."""
        parser = self._get_parser()
        pkg = parser.parse_package_json(self._write_pkg(tmp_path))
        report = json.loads(parser.generate_report(pkg))
        assert report["tool"] == "package-json"
        assert report["name"] == "my-app"
        assert report["framework"] == "react"

    def test_detect_framework_unknown(self, tmp_path):
        """Returns 'unknown' when no recognised framework is present."""
        parser = self._get_parser()
        p = tmp_path / "package.json"
        p.write_text(
            json.dumps({"name": "plain", "dependencies": {"lodash": "4.17.21"}}),
            encoding="utf-8",
        )
        pkg = parser.parse_package_json(p)
        assert parser.detect_framework(pkg) == "unknown"


# ---------------------------------------------------------------------------
# TestTestDetectionParser
# ---------------------------------------------------------------------------


class TestTestDetectionParser:
    """Tests for TestDetectionParser."""

    _JEST_PKG = {
        "name": "jest-project",
        "devDependencies": {"jest": "^29.0.0", "babel-jest": "^29.0.0"},
        "scripts": {"test": "jest"},
        "jest": {"testEnvironment": "node"},
    }

    _MOCHA_PKG = {
        "name": "mocha-project",
        "devDependencies": {"mocha": "^10.0.0"},
        "scripts": {"test": "mocha tests/"},
    }

    def _get_parser(self):
        from code_scalpel.code_parsers.javascript_parsers.javascript_parsers_test_detection import (
            TestDetectionParser,
        )

        return TestDetectionParser()

    def test_detect_jest_framework(self):
        """Jest is identified from devDependencies."""
        parser = self._get_parser()
        assert parser.detect_test_framework(self._JEST_PKG) == "jest"

    def test_detect_mocha_framework(self):
        """Mocha is identified from devDependencies."""
        parser = self._get_parser()
        assert parser.detect_test_framework(self._MOCHA_PKG) == "mocha"

    def test_detect_unknown_framework(self):
        """'unknown' is returned when no test dep is present."""
        parser = self._get_parser()
        assert (
            parser.detect_test_framework({"devDependencies": {"lodash": "^4"}})
            == "unknown"
        )

    def test_find_test_files(self, tmp_path):
        """find_test_files discovers .test.js and .spec.js files."""
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "app.test.js").touch()
        (tmp_path / "src" / "utils.spec.js").touch()
        (tmp_path / "src" / "index.js").touch()  # not a test file
        (tmp_path / "node_modules").mkdir()
        (tmp_path / "node_modules" / "lib.test.js").touch()  # must be excluded

        parser = self._get_parser()
        files = parser.find_test_files(tmp_path)
        assert "src/app.test.js" in files
        assert "src/utils.spec.js" in files
        assert "src/index.js" not in files
        # node_modules must be excluded
        assert not any("node_modules" in f for f in files)

    def test_get_test_config(self):
        """Jest config is extracted from the package.json dict."""
        parser = self._get_parser()
        config = parser.get_test_config(self._JEST_PKG)
        assert "jest" in config
        assert config["jest"]["testEnvironment"] == "node"

    def test_generate_report_structure(self):
        """generate_report produces valid JSON with 'tool' key."""
        parser = self._get_parser()
        findings = {
            "framework": "jest",
            "test_files": ["src/app.test.js"],
            "config": {},
            "total_test_files": 1,
        }
        report = json.loads(parser.generate_report(findings))
        assert report["tool"] == "test-detection"
        assert report["framework"] == "jest"


# ---------------------------------------------------------------------------
# TestWebpackParser
# ---------------------------------------------------------------------------


class TestWebpackParser:
    """Tests for WebpackConfigParser (regression-free static analysis)."""

    _CONFIG_TEXT = """\
const path = require('path');
const TerserPlugin = require('terser-webpack-plugin');
const MiniCssExtractPlugin = require('mini-css-extract-plugin');
const HtmlWebpackPlugin = require('html-webpack-plugin');

module.exports = {
  mode: 'production',
  entry: {
    main: './src/index.js',
    vendor: './src/vendor.js',
  },
  output: {
    path: path.resolve(__dirname, 'dist'),
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src'),
      'Components': './src/components',
    },
  },
  module: {
    rules: [
      { test: /\\.jsx?$/, use: 'babel-loader' },
      { test: /\\.css$/, use: ['style-loader', 'css-loader'] },
    ],
  },
  plugins: [
    new HtmlWebpackPlugin({ template: './public/index.html' }),
    new MiniCssExtractPlugin(),
    new TerserPlugin(),
  ],
};
"""

    def _get_parser(self):
        from code_scalpel.code_parsers.javascript_parsers.javascript_parsers_webpack import (
            WebpackConfigParser,
        )

        return WebpackConfigParser()

    def test_extract_entry_points(self):
        """Entry points from the object form are extracted."""
        parser = self._get_parser()
        entries = parser.extract_entry_points(self._CONFIG_TEXT)
        assert "./src/index.js" in entries
        assert "./src/vendor.js" in entries

    def test_extract_loaders(self):
        """babel-loader and css-loader are discovered."""
        parser = self._get_parser()
        loaders = parser.extract_loaders(self._CONFIG_TEXT)
        assert "babel-loader" in loaders
        assert "css-loader" in loaders

    def test_detect_optimization_plugins(self):
        """TerserPlugin and MiniCssExtractPlugin are detected."""
        parser = self._get_parser()
        plugins = parser.detect_optimization_plugins(self._CONFIG_TEXT)
        assert "TerserPlugin" in plugins
        assert "MiniCssExtractPlugin" in plugins
        assert "HtmlWebpackPlugin" in plugins

    def test_parse_webpack_config_from_file(self, tmp_path):
        """parse_webpack_config reads a real file and returns WebpackConfig."""
        cfg_file = tmp_path / "webpack.config.js"
        cfg_file.write_text(self._CONFIG_TEXT, encoding="utf-8")
        parser = self._get_parser()
        config = parser.parse_webpack_config(cfg_file)
        assert "./src/index.js" in config.entry_points
        assert "babel-loader" in config.loaders
        assert "TerserPlugin" in config.plugins
        assert config.mode == "production"

    def test_generate_report_structure(self):
        """generate_report produces valid JSON with 'tool' key."""
        from code_scalpel.code_parsers.javascript_parsers.javascript_parsers_webpack import (
            WebpackConfig,
        )

        parser = self._get_parser()
        config = WebpackConfig(
            entry_points=["./src/index.js"],
            loaders=["babel-loader"],
            plugins=["TerserPlugin"],
            mode="production",
        )
        report = json.loads(parser.generate_report(config))
        assert report["tool"] == "webpack"
        assert report["mode"] == "production"
        assert "babel-loader" in report["loaders"]

    def test_string_entry_form(self):
        """extract_entry_points handles the string entry form."""
        parser = self._get_parser()
        single_entry = "module.exports = { entry: './src/main.js' };"
        entries = parser.extract_entry_points(single_entry)
        assert "./src/main.js" in entries

    def test_no_plugins_returns_empty(self):
        """detect_optimization_plugins returns [] for minimal config."""
        parser = self._get_parser()
        minimal = "module.exports = { entry: './src/index.js' };"
        assert parser.detect_optimization_plugins(minimal) == []
