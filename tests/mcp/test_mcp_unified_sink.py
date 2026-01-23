"""
Tests for MCP unified sink detection tool.

[20251216_TEST] Integration tests for unified_sink_detect MCP tool.
"""

import pytest

from code_scalpel.mcp.tools.security import unified_sink_detect


@pytest.mark.asyncio
class TestMCPUnifiedSinkDetect:
    """Test MCP unified_sink_detect tool."""

    async def test_python_sql_injection_detection(self):
        """Test detecting SQL injection in Python code."""
        code = """
import sqlite3
user_input = input()
cursor.execute("SELECT * FROM users WHERE id=" + user_input)
"""

        result = await unified_sink_detect(code=code, language="python", confidence_threshold=0.8)

        assert result.success
        assert result.language == "python"
        assert result.sink_count > 0
        assert len(result.sinks) > 0

        # Should detect cursor.execute (Taint boosted to 0.95)
        sql_sinks = [s for s in result.sinks if s.pattern == "cursor.execute"]
        assert len(sql_sinks) > 0
        assert sql_sinks[0].confidence == 0.95
        assert sql_sinks[0].sink_type == "SQL_QUERY"

    async def test_typescript_xss_detection(self):
        """Test detecting XSS in TypeScript code."""
        code = "element.innerHTML = userInput;"

        result = await unified_sink_detect(code=code, language="typescript", confidence_threshold=0.8)

        assert result.success
        assert result.language == "typescript"
        assert result.sink_count > 0

        # Should detect innerHTML
        xss_sinks = [s for s in result.sinks if s.pattern == "innerHTML"]
        assert len(xss_sinks) > 0
        assert xss_sinks[0].confidence == 1.0

    async def test_javascript_command_injection(self):
        """Test detecting command injection in JavaScript."""
        code = "eval(userCode);"

        result = await unified_sink_detect(code=code, language="javascript", confidence_threshold=0.8)

        assert result.success
        assert result.sink_count > 0

        # Should detect eval
        eval_sinks = [s for s in result.sinks if s.pattern == "eval"]
        assert len(eval_sinks) > 0

    async def test_confidence_filtering(self):
        """Test confidence threshold filtering."""
        code = """
cursor.execute(query)
open(filename)
"""

        # High confidence filter (0.7 default)
        # BOTH are now 0.5 (Base confidence for Python) because they are untainted.
        result_std = await unified_sink_detect(code=code, language="python", confidence_threshold=0.7)
        assert result_std.success
        assert result_std.sink_count == 0

        # Lower confidence filter (0.4)
        # Should catch both
        result_low = await unified_sink_detect(code=code, language="python", confidence_threshold=0.4)
        assert result_low.success
        patterns_low = [s.pattern for s in result_low.sinks]
        assert "cursor.execute" in patterns_low
        assert "open" in patterns_low

    async def test_owasp_category_mapping(self):
        """Test OWASP category mapping in results."""
        code = "cursor.execute(query)"

        result = await unified_sink_detect(code=code, language="python", confidence_threshold=0.4)

        assert result.success
        assert len(result.sinks) > 0

        # SQL injection should map to A03:2021
        sql_sink = result.sinks[0]
        assert sql_sink.owasp_category == "A03:2021 – Injection"

    async def test_coverage_summary(self):
        """Test coverage summary in results."""
        code = "cursor.execute(query)"

        result = await unified_sink_detect(code=code, language="python", confidence_threshold=0.8)

        assert result.success
        assert result.coverage_summary
        assert "total_patterns" in result.coverage_summary
        assert "by_language" in result.coverage_summary
        assert result.coverage_summary["total_patterns"] > 0

    async def test_unsupported_language(self):
        """Test handling of unsupported language."""
        code = "some code"

        result = await unified_sink_detect(code=code, language="rust", confidence_threshold=0.8)

        assert not result.success
        assert result.error
        assert "Unsupported language" in result.error

    async def test_invalid_confidence(self):
        """Test handling of invalid confidence values."""
        code = "cursor.execute(query)"

        result = await unified_sink_detect(code=code, language="python", confidence_threshold=1.5)

        assert not result.success
        assert result.error
        assert "between 0.0 and 1.0" in result.error

    async def test_clean_code_no_sinks(self):
        """Test clean code returns no sinks."""
        code = """
def add(a, b):
    return a + b
"""

        result = await unified_sink_detect(code=code, language="python", confidence_threshold=0.8)

        assert result.success
        assert result.sink_count == 0
        assert len(result.sinks) == 0
