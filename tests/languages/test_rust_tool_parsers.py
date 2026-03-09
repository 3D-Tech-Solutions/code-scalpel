"""Tests for Rust tool parsers — Phase 2.

[20260305_TEST] Fixture-based tests for all Rust static analysis tool parsers.
No tools need to be installed; all tests use pre-baked fixture strings.

Follows the pattern established by test_swift_tool_parsers.py.
"""

from __future__ import annotations

import json

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_CLIPPY_WARNING_MSG = json.dumps(
    {
        "reason": "compiler-message",
        "message": {
            "level": "warning",
            "message": "unused variable: `x`",
            "code": {"code": "clippy::unused_variables", "explanation": None},
            "spans": [
                {
                    "file_name": "src/main.rs",
                    "is_primary": True,
                    "line_start": 10,
                    "column_start": 9,
                }
            ],
            "children": [
                {"level": "help", "message": "prefix with underscore: `_x`"}
            ],
        },
    }
)

_CLIPPY_ERROR_MSG = json.dumps(
    {
        "reason": "compiler-message",
        "message": {
            "level": "error",
            "message": "cannot borrow as mutable",
            "code": {"code": "E0596", "explanation": None},
            "spans": [
                {
                    "file_name": "src/lib.rs",
                    "is_primary": True,
                    "line_start": 25,
                    "column_start": 5,
                }
            ],
            "children": [],
        },
    }
)

_CLIPPY_ABORT_MSG = json.dumps(
    {
        "reason": "compiler-message",
        "message": {
            "level": "error",
            "message": "aborting due to 2 previous errors",
            "code": None,
            "spans": [],
            "children": [],
        },
    }
)

_CLIPPY_NON_COMPILER_MSG = json.dumps(
    {
        "reason": "build-script-executed",
        "package_id": "foo 0.1.0",
    }
)

_CARGO_AUDIT_JSON = json.dumps(
    {
        "database": {},
        "lockfile": {},
        "vulnerabilities": {
            "found": True,
            "count": 1,
            "list": [
                {
                    "advisory": {
                        "id": "RUSTSEC-2023-0001",
                        "package": "openssl",
                        "title": "Use after free",
                        "description": "A use-after-free vulnerability.",
                        "severity": "high",
                        "url": "https://rustsec.org/advisories/RUSTSEC-2023-0001",
                    },
                    "versions": {"patched": [">=1.1.1u"], "unaffected": []},
                    "affected": {},
                }
            ],
        },
    }
)

_CARGO_AUDIT_CLEAN = json.dumps(
    {
        "database": {},
        "lockfile": {},
        "vulnerabilities": {"found": False, "count": 0, "list": []},
    }
)

_CARGO_CHECK_ERROR = json.dumps(
    {
        "reason": "compiler-message",
        "message": {
            "level": "error",
            "message": "expected `;`, found `}`",
            "code": {"code": "E0001", "explanation": None},
            "spans": [
                {
                    "file_name": "src/main.rs",
                    "is_primary": True,
                    "line_start": 5,
                    "column_start": 1,
                }
            ],
            "children": [],
        },
    }
)

_CARGO_CHECK_WARNING = json.dumps(
    {
        "reason": "compiler-message",
        "message": {
            "level": "warning",
            "message": "unused import: `std::io`",
            "code": {"code": "unused_imports", "explanation": None},
            "spans": [
                {
                    "file_name": "src/lib.rs",
                    "is_primary": True,
                    "line_start": 1,
                    "column_start": 5,
                }
            ],
            "children": [],
        },
    }
)

_LSP_PUBLISH = json.dumps(
    {
        "method": "textDocument/publishDiagnostics",
        "params": {
            "uri": "file:///home/user/project/src/main.rs",
            "diagnostics": [
                {
                    "range": {
                        "start": {"line": 9, "character": 4},
                        "end": {"line": 9, "character": 8},
                    },
                    "severity": 1,
                    "code": "E0308",
                    "message": "mismatched types",
                    "source": "rust-analyzer",
                }
            ],
        },
    }
)


# ===========================================================================
# ClippyParser
# ===========================================================================


class TestClippyParserEmpty:
    """[20260305_TEST] ClippyParser handles empty / no-tool cases."""

    def test_parse_empty_string(self):
        from code_scalpel.code_parsers.rust_parsers.rust_parsers_clippy import (
            ClippyParser,
        )

        parser = ClippyParser()
        assert parser.parse_output("") == []

    def test_parse_whitespace_only(self):
        from code_scalpel.code_parsers.rust_parsers.rust_parsers_clippy import (
            ClippyParser,
        )

        parser = ClippyParser()
        assert parser.parse_output("   \n\n  ") == []

    def test_parse_invalid_json_lines(self):
        from code_scalpel.code_parsers.rust_parsers.rust_parsers_clippy import (
            ClippyParser,
        )

        parser = ClippyParser()
        assert parser.parse_output("not json\nalso not json") == []


class TestClippyParserWarning:
    """[20260305_TEST] ClippyParser parses warning messages correctly."""

    @pytest.fixture(autouse=True)
    def parsed(self):
        from code_scalpel.code_parsers.rust_parsers.rust_parsers_clippy import (
            ClippyParser,
        )

        parser = ClippyParser()
        self.findings = parser.parse_output(_CLIPPY_WARNING_MSG)
        self.parser = parser

    def test_finds_one_warning(self):
        assert len(self.findings) == 1

    def test_warning_level(self):
        assert self.findings[0].level == "warning"

    def test_warning_message(self):
        assert "unused variable" in self.findings[0].message

    def test_warning_code(self):
        assert self.findings[0].code == "clippy::unused_variables"

    def test_warning_file_path(self):
        assert self.findings[0].file_path == "src/main.rs"

    def test_warning_line(self):
        assert self.findings[0].line == 10

    def test_warning_column(self):
        assert self.findings[0].column == 9

    def test_warning_suggestion(self):
        assert self.findings[0].suggestion is not None
        assert "underscore" in self.findings[0].suggestion

    def test_to_dict_keys(self):
        d = self.findings[0].to_dict()
        assert set(d.keys()) == {
            "level", "message", "code", "file_path", "line", "column", "suggestion"
        }


class TestClippyParserError:
    """[20260305_TEST] ClippyParser parses error-level messages."""

    @pytest.fixture(autouse=True)
    def parsed(self):
        from code_scalpel.code_parsers.rust_parsers.rust_parsers_clippy import (
            ClippyParser,
        )

        parser = ClippyParser()
        self.findings = parser.parse_output(_CLIPPY_ERROR_MSG)

    def test_error_level(self):
        assert self.findings[0].level == "error"

    def test_error_code(self):
        assert self.findings[0].code == "E0596"

    def test_error_file_path(self):
        assert self.findings[0].file_path == "src/lib.rs"

    def test_error_line(self):
        assert self.findings[0].line == 25


class TestClippyParserFilters:
    """[20260305_TEST] ClippyParser skips noise entries."""

    def test_skip_abort_message(self):
        from code_scalpel.code_parsers.rust_parsers.rust_parsers_clippy import (
            ClippyParser,
        )

        parser = ClippyParser()
        findings = parser.parse_output(_CLIPPY_ABORT_MSG)
        assert findings == []

    def test_skip_non_compiler_message(self):
        from code_scalpel.code_parsers.rust_parsers.rust_parsers_clippy import (
            ClippyParser,
        )

        parser = ClippyParser()
        findings = parser.parse_output(_CLIPPY_NON_COMPILER_MSG)
        assert findings == []

    def test_multiple_lines_mixed(self):
        from code_scalpel.code_parsers.rust_parsers.rust_parsers_clippy import (
            ClippyParser,
        )

        raw = "\n".join(
            [_CLIPPY_NON_COMPILER_MSG, _CLIPPY_WARNING_MSG, _CLIPPY_ABORT_MSG]
        )
        parser = ClippyParser()
        findings = parser.parse_output(raw)
        assert len(findings) == 1
        assert findings[0].level == "warning"


class TestClippyCategorize:
    """[20260305_TEST] ClippyParser.categorize() maps codes to categories."""

    @pytest.fixture(autouse=True)
    def setup(self):
        from code_scalpel.code_parsers.rust_parsers.rust_parsers_clippy import (
            ClippyDiagnostic,
            ClippyParser,
        )

        self.parser = ClippyParser()
        self.Diag = ClippyDiagnostic

    def _make(self, code, level="warning", message=""):
        return self.Diag(
            level=level, message=message, code=code, file_path=None, line=0, column=0
        )

    def test_error_level_is_error(self):
        d = self._make("E0001", level="error")
        assert self.parser.categorize(d) == "error"

    def test_clippy_style(self):
        d = self._make("clippy::style_check")
        assert self.parser.categorize(d) == "style"

    def test_clippy_perf(self):
        d = self._make("clippy::perf_hint")
        assert self.parser.categorize(d) == "performance"

    def test_unknown_code(self):
        d = self._make("some_other_lint")
        assert self.parser.categorize(d) == "unknown"


# ===========================================================================
# RustfmtParser
# ===========================================================================


class TestRustfmtParserEmpty:
    """[20260305_TEST] RustfmtParser handles empty output."""

    def test_parse_empty(self):
        from code_scalpel.code_parsers.rust_parsers.rust_parsers_rustfmt import (
            RustfmtParser,
        )

        parser = RustfmtParser()
        assert parser.parse_output("") == []

    def test_parse_whitespace(self):
        from code_scalpel.code_parsers.rust_parsers.rust_parsers_rustfmt import (
            RustfmtParser,
        )

        parser = RustfmtParser()
        assert parser.parse_output("  \n  \n") == []


class TestRustfmtParserDiff:
    """[20260305_TEST] RustfmtParser parses diff-at-line-N output."""

    @pytest.fixture(autouse=True)
    def parsed(self):
        from code_scalpel.code_parsers.rust_parsers.rust_parsers_rustfmt import (
            RustfmtParser,
        )

        self.parser = RustfmtParser()
        raw = "Diff in src/main.rs at line 5:\n<<<\n>>>\n"
        self.findings = self.parser.parse_output(raw)

    def test_finds_one(self):
        assert len(self.findings) == 1

    def test_file_path(self):
        assert self.findings[0].file_path == "src/main.rs"

    def test_line_number(self):
        assert self.findings[0].line == 5

    def test_message(self):
        assert "reformat" in self.findings[0].message


class TestRustfmtParserWouldReformat:
    """[20260305_TEST] RustfmtParser handles 'Would reformat:' lines."""

    @pytest.fixture(autouse=True)
    def parsed(self):
        from code_scalpel.code_parsers.rust_parsers.rust_parsers_rustfmt import (
            RustfmtParser,
        )

        self.parser = RustfmtParser()
        raw = "Would reformat: src/lib.rs"
        self.findings = self.parser.parse_output(raw)

    def test_finds_one(self):
        assert len(self.findings) == 1

    def test_file_path(self):
        assert self.findings[0].file_path == "src/lib.rs"

    def test_line_zero(self):
        assert self.findings[0].line == 0

    def test_case_insensitive(self):
        from code_scalpel.code_parsers.rust_parsers.rust_parsers_rustfmt import (
            RustfmtParser,
        )

        parser = RustfmtParser()
        findings = parser.parse_output("would reformat: src/bar.rs")
        assert len(findings) == 1
        assert findings[0].file_path == "src/bar.rs"

    def test_to_dict_keys(self):
        d = self.findings[0].to_dict()
        assert set(d.keys()) == {"file_path", "line", "message"}


# ===========================================================================
# CargoAuditParser
# ===========================================================================


class TestCargoAuditParserEmpty:
    """[20260305_TEST] CargoAuditParser handles empty / clean output."""

    def test_parse_empty(self):
        from code_scalpel.code_parsers.rust_parsers.rust_parsers_cargo_audit import (
            CargoAuditParser,
        )

        parser = CargoAuditParser()
        assert parser.parse_output("") == []

    def test_parse_clean(self):
        from code_scalpel.code_parsers.rust_parsers.rust_parsers_cargo_audit import (
            CargoAuditParser,
        )

        parser = CargoAuditParser()
        assert parser.parse_output(_CARGO_AUDIT_CLEAN) == []


class TestCargoAuditParserVulnerability:
    """[20260305_TEST] CargoAuditParser parses vulnerability records."""

    @pytest.fixture(autouse=True)
    def parsed(self):
        from code_scalpel.code_parsers.rust_parsers.rust_parsers_cargo_audit import (
            CargoAuditParser,
        )

        parser = CargoAuditParser()
        self.findings = parser.parse_output(_CARGO_AUDIT_JSON)

    def test_finds_one(self):
        assert len(self.findings) == 1

    def test_advisory_id(self):
        assert self.findings[0].advisory_id == "RUSTSEC-2023-0001"

    def test_package(self):
        assert self.findings[0].package == "openssl"

    def test_severity(self):
        assert self.findings[0].severity == "high"

    def test_url(self):
        assert self.findings[0].url is not None
        assert "RUSTSEC-2023-0001" in self.findings[0].url

    def test_title(self):
        assert "Use after free" in self.findings[0].title

    def test_patched_versions(self):
        assert len(self.findings[0].patched_versions) >= 1

    def test_to_dict_keys(self):
        d = self.findings[0].to_dict()
        assert set(d.keys()) == {
            "advisory_id", "package", "title", "description",
            "severity", "url", "patched_versions",
        }


# ===========================================================================
# CargoCheckParser
# ===========================================================================


class TestCargoCheckParserEmpty:
    """[20260305_TEST] CargoCheckParser handles empty output."""

    def test_parse_empty(self):
        from code_scalpel.code_parsers.rust_parsers.rust_parsers_cargo_check import (
            CargoCheckParser,
        )

        parser = CargoCheckParser()
        assert parser.parse_output("") == []


class TestCargoCheckParserError:
    """[20260305_TEST] CargoCheckParser parses compiler errors."""

    @pytest.fixture(autouse=True)
    def parsed(self):
        from code_scalpel.code_parsers.rust_parsers.rust_parsers_cargo_check import (
            CargoCheckParser,
        )

        parser = CargoCheckParser()
        self.findings = parser.parse_output(_CARGO_CHECK_ERROR)

    def test_finds_one(self):
        assert len(self.findings) == 1

    def test_error_level(self):
        assert self.findings[0].level == "error"

    def test_file_path(self):
        assert self.findings[0].file_path == "src/main.rs"

    def test_line(self):
        assert self.findings[0].line == 5


class TestCargoCheckParserWarning:
    """[20260305_TEST] CargoCheckParser parses compiler warnings."""

    @pytest.fixture(autouse=True)
    def parsed(self):
        from code_scalpel.code_parsers.rust_parsers.rust_parsers_cargo_check import (
            CargoCheckParser,
        )

        parser = CargoCheckParser()
        self.findings = parser.parse_output(_CARGO_CHECK_WARNING)

    def test_finds_one(self):
        assert len(self.findings) == 1

    def test_warning_level(self):
        assert self.findings[0].level == "warning"

    def test_file_path(self):
        assert self.findings[0].file_path == "src/lib.rs"

    def test_skip_non_compiler_message(self):
        from code_scalpel.code_parsers.rust_parsers.rust_parsers_cargo_check import (
            CargoCheckParser,
        )

        parser = CargoCheckParser()
        non_msg = json.dumps({"reason": "build-finished", "success": True})
        assert parser.parse_output(non_msg) == []


# ===========================================================================
# RustAnalyzerParser
# ===========================================================================


class TestRustAnalyzerExecuteRaises:
    """[20260305_TEST] execute_rust_analyzer raises NotImplementedError."""

    def test_raises_not_implemented(self):
        from code_scalpel.code_parsers.rust_parsers.rust_parsers_rust_analyzer import (
            RustAnalyzerParser,
        )

        parser = RustAnalyzerParser()
        with pytest.raises(NotImplementedError):
            parser.execute_rust_analyzer([])

    def test_error_mentions_lsp(self):
        from code_scalpel.code_parsers.rust_parsers.rust_parsers_rust_analyzer import (
            RustAnalyzerParser,
        )

        parser = RustAnalyzerParser()
        try:
            parser.execute_rust_analyzer([])
        except NotImplementedError as exc:
            assert "LSP" in str(exc)

    def test_error_mentions_rustup(self):
        from code_scalpel.code_parsers.rust_parsers.rust_parsers_rust_analyzer import (
            RustAnalyzerParser,
        )

        parser = RustAnalyzerParser()
        try:
            parser.execute_rust_analyzer([])
        except NotImplementedError as exc:
            assert "rustup" in str(exc)


class TestRustAnalyzerParseLspNotification:
    """[20260305_TEST] parse_lsp_notification processes publishDiagnostics."""

    @pytest.fixture(autouse=True)
    def parsed(self):
        import json

        from code_scalpel.code_parsers.rust_parsers.rust_parsers_rust_analyzer import (
            RustAnalyzerParser,
        )

        parser = RustAnalyzerParser()
        self.parser = parser
        self.diags = parser.parse_lsp_notification(json.loads(_LSP_PUBLISH))

    def test_finds_one(self):
        assert len(self.diags) == 1

    def test_severity_error(self):
        assert self.diags[0].severity == "error"

    def test_code(self):
        assert self.diags[0].code == "E0308"

    def test_message(self):
        assert "mismatched types" in self.diags[0].message

    def test_file_uri(self):
        assert self.diags[0].file_uri is not None
        assert "main.rs" in self.diags[0].file_uri

    def test_line_1_based(self):
        # LSP line 9 → 1-based line 10
        assert self.diags[0].line == 10

    def test_column_1_based(self):
        # LSP char 4 → 1-based column 5
        assert self.diags[0].column == 5

    def test_wrong_method_returns_empty(self):
        other = {"method": "window/logMessage", "params": {"message": "init"}}
        assert self.parser.parse_lsp_notification(other) == []

    def test_to_dict_keys(self):
        d = self.diags[0].to_dict()
        assert set(d.keys()) == {
            "severity", "message", "code", "file_uri", "line", "column", "source"
        }


class TestRustAnalyzerSeverityMapping:
    """[20260305_TEST] LSP severity integers map to string levels."""

    def _make_lsp(self, severity: int) -> str:
        return json.dumps(
            {
                "method": "textDocument/publishDiagnostics",
                "params": {
                    "uri": "file:///src/lib.rs",
                    "diagnostics": [
                        {
                            "range": {"start": {"line": 0, "character": 0}},
                            "severity": severity,
                            "message": "test message",
                            "source": "rust-analyzer",
                        }
                    ],
                },
            }
        )

    def _parse(self, lsp_str: str):
        from code_scalpel.code_parsers.rust_parsers.rust_parsers_rust_analyzer import (
            RustAnalyzerParser,
        )

        return RustAnalyzerParser().parse_output(lsp_str)

    def test_severity_1_error(self):
        assert self._parse(self._make_lsp(1))[0].severity == "error"

    def test_severity_2_warning(self):
        assert self._parse(self._make_lsp(2))[0].severity == "warning"

    def test_severity_3_information(self):
        assert self._parse(self._make_lsp(3))[0].severity == "information"

    def test_severity_4_hint(self):
        assert self._parse(self._make_lsp(4))[0].severity == "hint"


class TestRustAnalyzerParseOutput:
    """[20260305_TEST] parse_output handles newline-delimited LSP JSON."""

    def test_parse_multiple_notifications(self):
        from code_scalpel.code_parsers.rust_parsers.rust_parsers_rust_analyzer import (
            RustAnalyzerParser,
        )

        raw = "\n".join([_LSP_PUBLISH, _LSP_PUBLISH])
        parser = RustAnalyzerParser()
        diags = parser.parse_output(raw)
        assert len(diags) == 2

    def test_parse_empty(self):
        from code_scalpel.code_parsers.rust_parsers.rust_parsers_rust_analyzer import (
            RustAnalyzerParser,
        )

        assert RustAnalyzerParser().parse_output("") == []

    def test_parse_diagnostics_array(self):
        from code_scalpel.code_parsers.rust_parsers.rust_parsers_rust_analyzer import (
            RustAnalyzerParser,
        )

        raw_arr = [
            {
                "range": {"start": {"line": 4, "character": 2}},
                "severity": 2,
                "message": "unused import",
                "source": "rust-analyzer",
            }
        ]
        parser = RustAnalyzerParser()
        diags = parser.parse_diagnostics_array(
            raw_arr, file_uri="file:///src/main.rs"
        )
        assert len(diags) == 1
        assert diags[0].severity == "warning"
        assert diags[0].line == 5  # 0-based line 4 → 1-based 5


# ===========================================================================
# RustParserRegistry
# ===========================================================================


class TestRustParserRegistry:
    """[20260305_TEST] RustParserRegistry factory and dispatch."""

    def test_get_clippy(self):
        from code_scalpel.code_parsers.rust_parsers import RustParserRegistry
        from code_scalpel.code_parsers.rust_parsers.rust_parsers_clippy import (
            ClippyParser,
        )

        reg = RustParserRegistry()
        assert isinstance(reg.get_parser("clippy"), ClippyParser)

    def test_get_rustfmt(self):
        from code_scalpel.code_parsers.rust_parsers import RustParserRegistry
        from code_scalpel.code_parsers.rust_parsers.rust_parsers_rustfmt import (
            RustfmtParser,
        )

        reg = RustParserRegistry()
        assert isinstance(reg.get_parser("rustfmt"), RustfmtParser)

    def test_get_cargo_audit_underscore(self):
        from code_scalpel.code_parsers.rust_parsers import RustParserRegistry
        from code_scalpel.code_parsers.rust_parsers.rust_parsers_cargo_audit import (
            CargoAuditParser,
        )

        reg = RustParserRegistry()
        assert isinstance(reg.get_parser("cargo_audit"), CargoAuditParser)

    def test_get_cargo_audit_hyphen_alias(self):
        from code_scalpel.code_parsers.rust_parsers import RustParserRegistry
        from code_scalpel.code_parsers.rust_parsers.rust_parsers_cargo_audit import (
            CargoAuditParser,
        )

        reg = RustParserRegistry()
        assert isinstance(reg.get_parser("cargo-audit"), CargoAuditParser)

    def test_get_cargo_check(self):
        from code_scalpel.code_parsers.rust_parsers import RustParserRegistry
        from code_scalpel.code_parsers.rust_parsers.rust_parsers_cargo_check import (
            CargoCheckParser,
        )

        reg = RustParserRegistry()
        assert isinstance(reg.get_parser("cargo_check"), CargoCheckParser)

    def test_get_rust_analyzer_hyphen_alias(self):
        from code_scalpel.code_parsers.rust_parsers import RustParserRegistry
        from code_scalpel.code_parsers.rust_parsers.rust_parsers_rust_analyzer import (
            RustAnalyzerParser,
        )

        reg = RustParserRegistry()
        assert isinstance(reg.get_parser("rust-analyzer"), RustAnalyzerParser)

    def test_unknown_tool_raises(self):
        from code_scalpel.code_parsers.rust_parsers import RustParserRegistry

        reg = RustParserRegistry()
        with pytest.raises(ValueError):
            reg.get_parser("nonexistent_tool")

    def test_analyze_returns_dict(self):
        from code_scalpel.code_parsers.rust_parsers import RustParserRegistry

        reg = RustParserRegistry()
        # Analyze with clippy providing a raw fixture string
        result = reg.analyze(_CLIPPY_WARNING_MSG, tools=["clippy"])
        assert isinstance(result, dict)
        assert "clippy" in result

    def test_analyze_no_tools_returns_all_tools(self):
        from code_scalpel.code_parsers.rust_parsers import RustParserRegistry

        reg = RustParserRegistry()
        # tools=[] is falsy → registry defaults to running all tools
        result = reg.analyze("", tools=[])
        assert isinstance(result, dict)
        assert len(result) > 0
