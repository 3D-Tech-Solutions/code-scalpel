"""
Tests for Unified Security Sink Detector.

[20251216_TEST] Comprehensive tests for polyglot sink detection with confidence scoring.
"""

import textwrap

import pytest

from code_scalpel.symbolic_execution_tools import (
    OWASP_COVERAGE,
    UNIFIED_SINKS,
    DetectedSink,
    SecuritySink,
    SinkDefinition,
    TaintInfo,
    TaintLevel,
    TaintSource,
    UnifiedSinkDetector,
)


class TestUnifiedSinksStructure:
    """Test the UNIFIED_SINKS data structure."""

    def test_all_owasp_categories_mapped(self):
        """All OWASP Top 10 2021 categories should be mapped."""
        expected_categories = [
            "A01:2021 – Broken Access Control",
            "A02:2021 – Cryptographic Failures",
            "A03:2021 – Injection",
            "A04:2021 – Insecure Design",
            "A05:2021 – Security Misconfiguration",
            "A06:2021 – Vulnerable and Outdated Components",
            "A07:2021 – Identification and Authentication Failures",
            "A08:2021 – Software and Data Integrity Failures",
            "A09:2021 – Security Logging and Monitoring Failures",
            "A10:2021 – Server-Side Request Forgery",
        ]

        for category in expected_categories:
            assert category in OWASP_COVERAGE, f"Missing OWASP category: {category}"

    def test_python_sinks_defined_with_confidence(self):
        """Python sinks should be defined with confidence scores."""
        assert "sql_injection" in UNIFIED_SINKS
        assert "python" in UNIFIED_SINKS["sql_injection"]

        python_sinks = UNIFIED_SINKS["sql_injection"]["python"]
        assert len(python_sinks) > 0

        for sink in python_sinks:
            assert isinstance(sink, SinkDefinition)
            assert 0.0 <= sink.confidence <= 1.0
            assert sink.pattern
            assert sink.sink_type

    def test_java_sinks_defined_with_confidence(self):
        """Java sinks should be defined with confidence scores."""
        assert "sql_injection" in UNIFIED_SINKS
        assert "java" in UNIFIED_SINKS["sql_injection"]

        java_sinks = UNIFIED_SINKS["sql_injection"]["java"]
        assert len(java_sinks) > 0

        for sink in java_sinks:
            assert isinstance(sink, SinkDefinition)
            assert 0.0 <= sink.confidence <= 1.0
            assert sink.pattern
            assert sink.sink_type

    def test_typescript_sinks_defined_with_confidence(self):
        """TypeScript sinks should be defined with confidence scores."""
        assert "sql_injection" in UNIFIED_SINKS
        assert "typescript" in UNIFIED_SINKS["sql_injection"]

        ts_sinks = UNIFIED_SINKS["sql_injection"]["typescript"]
        assert len(ts_sinks) > 0

        for sink in ts_sinks:
            assert isinstance(sink, SinkDefinition)
            assert 0.0 <= sink.confidence <= 1.0
            assert sink.pattern
            assert sink.sink_type

    def test_javascript_sinks_defined_with_confidence(self):
        """JavaScript sinks should be defined with confidence scores."""
        assert "sql_injection" in UNIFIED_SINKS
        assert "javascript" in UNIFIED_SINKS["sql_injection"]

        js_sinks = UNIFIED_SINKS["sql_injection"]["javascript"]
        assert len(js_sinks) > 0

        for sink in js_sinks:
            assert isinstance(sink, SinkDefinition)
            assert 0.0 <= sink.confidence <= 1.0
            assert sink.pattern
            assert sink.sink_type


class TestSQLInjectionDetection:
    """Test SQL injection detection across languages."""

    def test_python_sql_injection_100_percent_confidence(self):
        """Python cursor.execute should be detected with 1.0 confidence."""
        detector = UnifiedSinkDetector()
        code = textwrap.dedent("""
            import sqlite3
            user_input = input()
            cursor.execute("SELECT * FROM users WHERE id=" + user_input)
        """)

        sinks = detector.detect_sinks(code, "python", min_confidence=0.8)

        assert len(sinks) > 0
        sql_sinks = [s for s in sinks if s.sink_type == SecuritySink.SQL_QUERY]
        assert len(sql_sinks) > 0
        assert sql_sinks[0].confidence == 1.0
        assert sql_sinks[0].pattern == "cursor.execute"

    def test_python_sqlalchemy_execute_detected(self):
        """SQLAlchemy session.execute should be detected."""
        detector = UnifiedSinkDetector()
        code = textwrap.dedent("""
            from sqlalchemy import create_engine
            session.execute("SELECT * FROM users")
        """)

        sinks = detector.detect_sinks(code, "python", min_confidence=0.8)

        assert len(sinks) > 0
        sql_sinks = [s for s in sinks if s.pattern == "session.execute"]
        assert len(sql_sinks) > 0
        assert sql_sinks[0].confidence >= 0.95

    def test_typescript_sql_injection_detected(self):
        """TypeScript connection.query should be detected."""
        detector = UnifiedSinkDetector()
        code = textwrap.dedent("""
            const query = "SELECT * FROM users WHERE id=" + userId;
            connection.query(query);
        """)

        sinks = detector.detect_sinks(code, "typescript", min_confidence=0.8)

        assert len(sinks) > 0
        sql_sinks = [s for s in sinks if s.pattern == "connection.query"]
        assert len(sql_sinks) > 0
        assert sql_sinks[0].confidence == 1.0

    def test_javascript_sequelize_query_detected(self):
        """JavaScript sequelize.query should be detected."""
        detector = UnifiedSinkDetector()
        code = 'sequelize.query("SELECT * FROM users WHERE id=" + userId);'

        sinks = detector.detect_sinks(code, "javascript", min_confidence=0.8)

        assert len(sinks) > 0
        sql_sinks = [s for s in sinks if s.pattern == "sequelize.query"]
        assert len(sql_sinks) > 0
        assert sql_sinks[0].confidence >= 0.8


class TestXSSDetection:
    """Test XSS detection across languages."""

    def test_typescript_innerhtml_100_percent_confidence(self):
        """TypeScript innerHTML should be detected with 1.0 confidence."""
        detector = UnifiedSinkDetector()
        code = "element.innerHTML = userInput;"

        sinks = detector.detect_sinks(code, "typescript", min_confidence=0.8)

        assert len(sinks) > 0
        xss_sinks = [s for s in sinks if s.sink_type == SecuritySink.DOM_XSS]
        assert len(xss_sinks) > 0
        assert xss_sinks[0].confidence == 1.0

    def test_javascript_document_write_detected(self):
        """JavaScript document.write should be detected."""
        detector = UnifiedSinkDetector()
        code = "document.write(userInput);"

        sinks = detector.detect_sinks(code, "javascript", min_confidence=0.8)

        assert len(sinks) > 0
        xss_sinks = [s for s in sinks if s.pattern == "document.write"]
        assert len(xss_sinks) > 0
        assert xss_sinks[0].confidence == 1.0

    def test_python_jinja2_template_detected(self):
        """Python jinja2.Template should be detected as SSTI."""
        detector = UnifiedSinkDetector()
        code = "jinja2.Template(user_template).render()"

        sinks = detector.detect_sinks(code, "python", min_confidence=0.8)

        assert len(sinks) > 0
        ssti_sinks = [s for s in sinks if s.sink_type == SecuritySink.SSTI]
        assert len(ssti_sinks) > 0


class TestCommandInjectionDetection:
    """Test command injection detection across languages."""

    def test_python_os_system_100_percent_confidence(self):
        """Python os.system should be detected with 1.0 confidence."""
        detector = UnifiedSinkDetector()
        code = 'os.system("rm -rf " + user_path)'

        sinks = detector.detect_sinks(code, "python", min_confidence=0.8)

        assert len(sinks) > 0
        cmd_sinks = [s for s in sinks if s.sink_type == SecuritySink.SHELL_COMMAND]
        assert len(cmd_sinks) > 0
        assert cmd_sinks[0].confidence == 1.0

    def test_python_subprocess_call_detected(self):
        """Python subprocess.call should be detected."""
        detector = UnifiedSinkDetector()
        code = 'subprocess.call(["ls", user_input])'

        sinks = detector.detect_sinks(code, "python", min_confidence=0.8)

        assert len(sinks) > 0
        cmd_sinks = [s for s in sinks if s.pattern == "subprocess.call"]
        assert len(cmd_sinks) > 0
        assert cmd_sinks[0].confidence >= 0.9

    def test_typescript_child_process_exec_detected(self):
        """TypeScript child_process.exec should be detected."""
        detector = UnifiedSinkDetector()
        code = 'child_process.exec("ls " + userInput);'

        sinks = detector.detect_sinks(code, "typescript", min_confidence=0.8)

        assert len(sinks) > 0
        cmd_sinks = [s for s in sinks if s.pattern == "child_process.exec"]
        assert len(cmd_sinks) > 0
        assert cmd_sinks[0].confidence == 1.0

    def test_python_eval_detected(self):
        """Python eval should be detected as code injection."""
        detector = UnifiedSinkDetector()
        code = "eval(user_code)"

        sinks = detector.detect_sinks(code, "python", min_confidence=0.8)

        assert len(sinks) > 0
        eval_sinks = [s for s in sinks if s.sink_type == SecuritySink.EVAL]
        assert len(eval_sinks) > 0
        assert eval_sinks[0].confidence == 1.0


class TestPathTraversalDetection:
    """Test path traversal detection across languages."""

    def test_python_open_detected(self):
        """Python open() should be detected with appropriate confidence."""
        detector = UnifiedSinkDetector()
        code = 'open(user_filename, "r")'

        sinks = detector.detect_sinks(code, "python", min_confidence=0.5)

        assert len(sinks) > 0
        file_sinks = [s for s in sinks if s.sink_type == SecuritySink.FILE_PATH]
        assert len(file_sinks) > 0
        # open() is context-dependent, should have lower confidence
        assert file_sinks[0].confidence <= 0.9

    def test_typescript_fs_readfile_detected(self):
        """TypeScript fs.readFile should be detected."""
        detector = UnifiedSinkDetector()
        code = "fs.readFile(userPath, callback);"

        sinks = detector.detect_sinks(code, "typescript", min_confidence=0.8)

        assert len(sinks) > 0
        file_sinks = [s for s in sinks if s.pattern == "fs.readFile"]
        assert len(file_sinks) > 0
        assert file_sinks[0].confidence >= 0.8


class TestSSRFDetection:
    """Test SSRF detection across languages."""

    def test_python_requests_get_detected(self):
        """Python requests.get should be detected."""
        detector = UnifiedSinkDetector()
        code = "requests.get(user_url)"

        sinks = detector.detect_sinks(code, "python", min_confidence=0.8)

        assert len(sinks) > 0
        ssrf_sinks = [s for s in sinks if s.sink_type == SecuritySink.SSRF]
        assert len(ssrf_sinks) > 0
        assert ssrf_sinks[0].confidence >= 0.9

    def test_typescript_fetch_detected(self):
        """TypeScript fetch should be detected."""
        detector = UnifiedSinkDetector()
        code = "fetch(userUrl);"

        sinks = detector.detect_sinks(code, "typescript", min_confidence=0.8)

        assert len(sinks) > 0
        ssrf_sinks = [s for s in sinks if s.pattern == "fetch"]
        assert len(ssrf_sinks) > 0
        assert ssrf_sinks[0].confidence >= 0.9


class TestMinimumConfidenceFiltering:
    """Test confidence threshold filtering."""

    def test_high_confidence_filter(self):
        """Filtering at 1.0 should only return perfect matches."""
        detector = UnifiedSinkDetector()
        code = textwrap.dedent("""
            cursor.execute(query)
            open(filename)
        """)

        sinks = detector.detect_sinks(code, "python", min_confidence=1.0)

        # cursor.execute has 1.0 confidence, open has lower
        assert len(sinks) >= 1
        assert all(s.confidence == 1.0 for s in sinks)

    def test_medium_confidence_filter(self):
        """Filtering at 0.8 should include most sinks."""
        detector = UnifiedSinkDetector()
        code = textwrap.dedent("""
            cursor.execute(query)
            open(filename)
            session.execute(query)
        """)

        sinks = detector.detect_sinks(code, "python", min_confidence=0.8)

        # Should get cursor.execute (1.0) and session.execute (0.95)
        assert len(sinks) >= 2
        assert all(s.confidence >= 0.8 for s in sinks)

    def test_low_confidence_filter(self):
        """Filtering at 0.5 should include context-dependent sinks."""
        detector = UnifiedSinkDetector()
        code = 'open(filename, "r")'

        sinks = detector.detect_sinks(code, "python", min_confidence=0.5)

        # open() has 0.8 confidence
        assert len(sinks) >= 1


class TestVulnerabilityAssessment:
    """Test vulnerability assessment with taint analysis."""

    def test_vulnerable_with_tainted_data(self):
        """Sink is vulnerable when tainted data reaches it."""
        detector = UnifiedSinkDetector()

        sink = DetectedSink(
            pattern="cursor.execute",
            sink_type=SecuritySink.SQL_QUERY,
            confidence=1.0,
            line=5,
            column=10,
            code_snippet="cursor.execute(query)",
            vulnerability_type="sql_injection",
        )

        taint = TaintInfo(
            source=TaintSource.USER_INPUT,
            level=TaintLevel.HIGH,
            source_location=(3, 5),
            propagation_path=["user_input", "query"],
        )

        is_vuln, explanation = detector.is_vulnerable(sink, taint)

        assert is_vuln
        assert "cursor.execute" in explanation

    def test_not_vulnerable_with_sanitized_data(self):
        """Sink is not vulnerable when data is sanitized."""
        detector = UnifiedSinkDetector()

        sink = DetectedSink(
            pattern="cursor.execute",
            sink_type=SecuritySink.SQL_QUERY,
            confidence=1.0,
            line=5,
            column=10,
            code_snippet="cursor.execute(query)",
            vulnerability_type="sql_injection",
        )

        # Create taint info with sanitizer applied
        taint = TaintInfo(
            source=TaintSource.USER_INPUT,
            level=TaintLevel.HIGH,
            source_location=(3, 5),
            propagation_path=["user_input", "query"],
        )
        # Apply sanitizer
        taint = taint.apply_sanitizer("parameterized_query")

        is_vuln, explanation = detector.is_vulnerable(sink, taint)

        assert not is_vuln
        assert "sanitized" in explanation.lower()

    def test_not_vulnerable_with_clean_data(self):
        """Sink is not vulnerable when data is not tainted."""
        detector = UnifiedSinkDetector()

        sink = DetectedSink(
            pattern="cursor.execute",
            sink_type=SecuritySink.SQL_QUERY,
            confidence=1.0,
            line=5,
            column=10,
            code_snippet="cursor.execute(query)",
            vulnerability_type="sql_injection",
        )

        taint = TaintInfo(
            source=TaintSource.USER_INPUT,
            level=TaintLevel.NONE,
            source_location=(3, 5),
        )

        is_vuln, explanation = detector.is_vulnerable(sink, taint)

        assert not is_vuln
        assert "No tainted data" in explanation


class TestOWASPMapping:
    """Test OWASP Top 10 category mapping."""

    def test_get_owasp_category_for_sql_injection(self):
        """SQL injection should map to A03:2021 Injection."""
        detector = UnifiedSinkDetector()

        category = detector.get_owasp_category("sql_injection")

        assert category == "A03:2021 – Injection"

    def test_get_owasp_category_for_ssrf(self):
        """SSRF should map to A10:2021."""
        detector = UnifiedSinkDetector()

        category = detector.get_owasp_category("ssrf")

        assert category == "A10:2021 – Server-Side Request Forgery"

    def test_get_owasp_category_for_path_traversal(self):
        """Path traversal should map to A01:2021."""
        detector = UnifiedSinkDetector()

        category = detector.get_owasp_category("path_traversal")

        assert category == "A01:2021 – Broken Access Control"


class TestCoverageReport:
    """Test coverage reporting functionality."""

    def test_coverage_report_structure(self):
        """Coverage report should have correct structure."""
        detector = UnifiedSinkDetector()

        report = detector.get_coverage_report()

        assert "total_patterns" in report
        assert "by_language" in report
        assert "by_vulnerability" in report
        assert "owasp_coverage" in report

        assert report["total_patterns"] > 0
        assert "python" in report["by_language"]
        assert "java" in report["by_language"]
        assert "typescript" in report["by_language"]
        assert "javascript" in report["by_language"]

    def test_coverage_report_counts(self):
        """Coverage report should have reasonable counts."""
        detector = UnifiedSinkDetector()

        report = detector.get_coverage_report()

        # Should have at least 50 total patterns across all languages
        assert report["total_patterns"] >= 50

        # Each language should have some patterns
        assert report["by_language"]["python"] > 0
        assert report["by_language"]["java"] > 0
        assert report["by_language"]["typescript"] > 0
        assert report["by_language"]["javascript"] > 0

    def test_owasp_coverage_percentages(self):
        """OWASP coverage should show percentages."""
        detector = UnifiedSinkDetector()

        report = detector.get_coverage_report()

        for _category, stats in report["owasp_coverage"].items():
            assert "total" in stats
            assert "covered" in stats
            assert "percentage" in stats
            assert 0 <= stats["percentage"] <= 100


class TestFalsePositiveRate:
    """Test false positive rate on clean code."""

    def test_clean_python_code_no_false_positives(self):
        """Clean Python code should not trigger false positives."""
        detector = UnifiedSinkDetector()
        code = textwrap.dedent("""
            def calculate_total(items):
                total = 0
                for item in items:
                    total += item.price
                return total

            def format_name(first, last):
                return f"{first} {last}"
        """)

        sinks = detector.detect_sinks(code, "python", min_confidence=0.8)

        # Should have no sinks in this clean code
        assert len(sinks) == 0

    def test_safe_parameterized_query_lower_confidence(self):
        """Parameterized queries should have lower confidence scores."""
        # Note: This is aspirational - actual detection would need
        # AST analysis to distinguish parameterized vs concatenated queries
        # For now, we verify that PreparedStatement has lower confidence

        java_sinks = UNIFIED_SINKS["sql_injection"]["java"]
        prepared_stmt = [s for s in java_sinks if "PreparedStatement" in s.pattern]

        assert len(prepared_stmt) > 0
        # PreparedStatement should have lower confidence (0.5) as it's safer
        assert prepared_stmt[0].confidence <= 0.6


class TestUnsupportedLanguage:
    """Test handling of unsupported languages."""

    def test_unsupported_language_raises_error(self):
        """Unsupported language should raise ValueError."""
        detector = UnifiedSinkDetector()

        with pytest.raises(ValueError, match="Unsupported language"):
            detector.detect_sinks("some code", "rust", min_confidence=0.8)


class TestSinkDefinitionValidation:
    """Test SinkDefinition validation."""

    def test_valid_confidence_score(self):
        """Valid confidence scores should be accepted."""
        sink = SinkDefinition(
            pattern="test",
            confidence=0.8,
            sink_type=SecuritySink.SQL_QUERY,
            description="Test sink",
        )
        assert sink.confidence == 0.8

    def test_invalid_confidence_too_high(self):
        """Confidence > 1.0 should raise ValueError."""
        with pytest.raises(ValueError, match="Confidence must be between 0.0 and 1.0"):
            SinkDefinition(
                pattern="test",
                confidence=1.5,
                sink_type=SecuritySink.SQL_QUERY,
                description="Invalid",
            )

    def test_invalid_confidence_negative(self):
        """Negative confidence should raise ValueError."""
        with pytest.raises(ValueError, match="Confidence must be between 0.0 and 1.0"):
            SinkDefinition(
                pattern="test",
                confidence=-0.1,
                sink_type=SecuritySink.SQL_QUERY,
                description="Invalid",
            )
