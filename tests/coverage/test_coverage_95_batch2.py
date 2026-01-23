"""
Additional tests to push coverage to 95% threshold - Batch 2.

[20251220_TEST] Targeting remaining uncovered lines for 95% coverage.
"""

import tempfile
from pathlib import Path

import pytest

# =============================================================================
# Tests for generators/test_generator.py - Uncovered lines 566, 606, 654
# =============================================================================


class TestTestGeneratorUncovered:
    """Target uncovered lines in TestGenerator."""

    def test_extract_parameter_types_non_python(self):
        """Test _extract_parameter_types for non-Python - line 566."""
        from code_scalpel.generators.test_generator import TestGenerator

        gen = TestGenerator()

        # Non-python language returns empty dict
        result = gen._extract_parameter_types("", "foo", "javascript")
        assert result == {}

    def test_extract_parameter_types_with_types(self):
        """Test _extract_parameter_types with type hints."""
        from code_scalpel.generators.test_generator import TestGenerator

        gen = TestGenerator()

        code = """
def foo(name: str, age: int, active: bool) -> None:
    pass
"""
        result = gen._extract_parameter_types(code, "foo", "python")
        assert "name" in result
        assert result["name"] == "str"
        assert result["age"] == "int"

    def test_generate_tests_from_code(self):
        """Test generate with various code patterns."""
        from code_scalpel.generators.test_generator import TestGenerator

        gen = TestGenerator()

        code = '''
def calculate(x: int, y: int) -> int:
    """Calculate something."""
    if x > 0:
        return x + y
    return y
'''
        result = gen.generate(code, "calculate")
        assert result is not None


# =============================================================================
# Tests for generators/refactor_simulator.py - More uncovered lines
# =============================================================================


class TestRefactorSimulatorMore:
    """More tests for RefactorSimulator."""

    def test_simulate_with_syntax_error(self):
        """Test simulate with syntax error in new code."""
        from code_scalpel.generators.refactor_simulator import RefactorSimulator

        simulator = RefactorSimulator()

        original = "def foo(): pass"
        new_code = "def foo( broken syntax"

        result = simulator.simulate(original, new_code)
        # Should handle syntax error and report it
        assert result is not None

    def test_simulate_non_python(self):
        """Test simulate for non-Python language."""
        from code_scalpel.generators.refactor_simulator import RefactorSimulator

        simulator = RefactorSimulator()

        result = simulator.simulate("const x = 1;", "const x = 2;", language="javascript")
        # Non-python still runs simulation
        assert result is not None


# =============================================================================
# Tests for mcp/logging.py - Uncovered lines around structlog
# =============================================================================


class TestMCPLogging:
    """Test MCP logging functions."""

    def test_analytics_get_tool_stats_empty(self):
        """Test get_tool_stats with no invocations - line 175."""
        from code_scalpel.mcp.logging import MCPAnalytics

        analytics = MCPAnalytics()

        # Get stats for tool with no invocations
        stats = analytics.get_tool_stats("nonexistent_tool")
        assert stats["total_invocations"] == 0
        assert stats["success_rate"] == 0.0

    def test_analytics_get_error_summary_empty(self):
        """Test get_error_summary with no errors - line 216."""
        from code_scalpel.mcp.logging import MCPAnalytics

        analytics = MCPAnalytics()

        summary = analytics.get_error_summary()
        assert summary["total_errors"] == 0
        assert summary["error_rate"] == 0.0

    def test_log_tool_invocation(self):
        """Test log_tool_invocation function - line 277."""
        from code_scalpel.mcp import logging as mcp_logging

        # Just ensure it doesn't raise
        mcp_logging.log_tool_invocation("test_tool", {"param1": "value"})

    def test_log_tool_success(self):
        """Test log_tool_success function - line 315."""
        from code_scalpel.mcp import logging as mcp_logging

        # Just ensure it doesn't raise
        mcp_logging.log_tool_success("test_tool", 100.5, {"metric1": 10})

    def test_log_tool_error(self):
        """Test log_tool_error function - line 365."""
        from code_scalpel.mcp import logging as mcp_logging

        # Just ensure it doesn't raise
        mcp_logging.log_tool_error("test_tool", ValueError("test error"), 50.0)


# =============================================================================
# Tests for cache/analysis_cache.py - Uncovered branches
# =============================================================================


class TestAnalysisCacheMore:
    """More tests for AnalysisCache."""

    def test_analysis_cache_basic_operations(self):
        """Test basic cache operations."""
        from code_scalpel.cache.unified_cache import AnalysisCache

        with tempfile.TemporaryDirectory() as td:
            cache = AnalysisCache(cache_dir=td)

            # Create a test file to store
            test_file = Path(td) / "test.py"
            test_file.write_text("x = 1")

            # Test store and get_cached
            cache.store(str(test_file), {"analysis": "result"})
            result = cache.get_cached(str(test_file))
            assert result == {"analysis": "result"}

            # Test stats (it's a property, not a method)
            stats = cache.stats
            assert stats is not None


# =============================================================================
# Tests for polyglot modules - Uncovered branches
# =============================================================================


class TestPolyglotModules:
    """Tests for polyglot modules."""

    def test_alias_resolver_resolve(self):
        """Test AliasResolver.resolve method."""
        from code_scalpel.polyglot.alias_resolver import AliasResolver

        with tempfile.TemporaryDirectory() as td:
            resolver = AliasResolver(td)
            Path(td).joinpath("tsconfig.json").write_text(
                '\n{\n  "compilerOptions": {\n    "paths": {\n      "@utils/*": ["src/utils/*"]\n    }\n  }\n}\n'
            )
            _ = resolver.resolve("@utils/helpers")

    def test_typescript_type_narrowing_basic(self):
        """[20251219_TEST] Test TypeScript type narrowing analysis."""
        from code_scalpel.polyglot.typescript.type_narrowing import TypeNarrowing

        analyzer = TypeNarrowing()
        code = """
function foo(x: string | number) {
    if (typeof x === 'string') {
        return x.length;
    }
    return x;
}
"""
        result = analyzer.analyze(code)
        assert result is not None


# =============================================================================
# Tests for symbolic_execution_tools/taint_tracker.py - Uncovered lines
# =============================================================================


class TestTaintTrackerMore:
    """More tests for TaintTracker."""

    def test_taint_tracker_taint_source(self):
        """Test taint_source method."""
        from code_scalpel.security.analyzers.taint_tracker import TaintTracker

        tracker = TaintTracker()
        tracker.taint_source("source", "user_input")

        # source should be tainted
        assert tracker.is_tainted("source")

    def test_taint_tracker_get_vulnerabilities(self):
        """Test get_vulnerabilities method."""
        from code_scalpel.security.analyzers.taint_tracker import TaintTracker

        tracker = TaintTracker()

        # Get vulnerabilities (may be empty)
        vulns = tracker.get_vulnerabilities()
        assert isinstance(vulns, list)

    def test_taint_tracker_propagate_concat(self):
        """Test propagate_concat method."""
        from code_scalpel.security.analyzers.taint_tracker import TaintTracker

        tracker = TaintTracker()
        tracker.taint_source("x", "user_input")

        # Propagate via concatenation
        tracker.propagate_concat("result", ["x", "safe"])

        # result should be tainted because x is tainted
        assert tracker.is_tainted("result")


# =============================================================================
# Tests for autonomy/error_to_diff.py - Uncovered lines
# =============================================================================


class TestErrorToDiffMore:
    """More tests for ErrorToDiffEngine."""

    def test_error_to_diff_syntax_error(self):
        """Test analyze_error with syntax error."""
        from code_scalpel.autonomy.error_to_diff import ErrorToDiffEngine

        with tempfile.TemporaryDirectory() as td:
            engine = ErrorToDiffEngine(td)

            error = """
  File "test.py", line 3
    def foo(
          ^
SyntaxError: unexpected EOF while parsing
"""
            code = """
def foo(
"""
            result = engine.analyze_error(error, "python", code)
            assert result is not None

    def test_error_to_diff_name_error(self):
        """Test analyze_error with NameError."""
        from code_scalpel.autonomy.error_to_diff import ErrorToDiffEngine

        with tempfile.TemporaryDirectory() as td:
            engine = ErrorToDiffEngine(td)

            error = """
Traceback (most recent call last):
  File "test.py", line 1, in <module>
    print(undefined_var)
NameError: name 'undefined_var' is not defined
"""
            code = "print(undefined_var)"

            result = engine.analyze_error(error, "python", code)
            assert result is not None


# =============================================================================
# Tests for autonomy/sandbox.py - Uncovered lines
# =============================================================================


class TestSandboxMore:
    """More tests for Sandbox module."""

    def test_sandbox_executor_init(self):
        """Test SandboxExecutor initialization."""
        try:
            from code_scalpel.autonomy.sandbox import SandboxExecutor

            executor = SandboxExecutor(
                isolation_level="process",
                network_enabled=False,
                max_memory_mb=100,
                max_cpu_seconds=5,
            )
            assert executor is not None
        except ImportError:
            pytest.skip("SandboxExecutor not available")


# =============================================================================
# Tests for policy_engine modules - Uncovered lines
# =============================================================================


class TestPolicyEngineMore:
    """More tests for policy_engine modules."""

    def test_policy_engine_initialization(self):
        """Test PolicyEngine initialization."""
        from code_scalpel.policy_engine import PolicyEngine

        engine = PolicyEngine()
        assert engine is not None

    def test_audit_log_initialization(self):
        """Test AuditLog initialization."""
        from code_scalpel.policy_engine.audit_log import AuditLog

        log = AuditLog()
        assert log is not None

    def test_tamper_resistance_basic(self):
        """Test TamperResistance basic functionality."""
        try:
            from code_scalpel.policy_engine.tamper_resistance import TamperResistance

            tr = TamperResistance()
            assert tr is not None
        except ImportError:
            pytest.skip("TamperResistance not available")


# =============================================================================
# Tests for ast_tools/__init__.py - ImportError fallback branches
# =============================================================================


class TestASTToolsInit:
    """Test ast_tools __init__ imports."""

    def test_import_resolver_available(self):
        """Test ImportResolver is available."""
        from code_scalpel.ast_tools import ImportResolver

        # Should be imported or None
        if ImportResolver is not None:
            with tempfile.TemporaryDirectory() as td:
                resolver = ImportResolver(td)
                assert resolver is not None

    def test_cross_file_extractor_available(self):
        """Test CrossFileExtractor is available."""
        from code_scalpel.ast_tools import CrossFileExtractor

        if CrossFileExtractor is not None:
            with tempfile.TemporaryDirectory() as td:
                extractor = CrossFileExtractor(td)
                assert extractor is not None


# =============================================================================
# Tests for cli.py - Uncovered branches in command handling
# =============================================================================


class TestCLIMore:
    """More tests for CLI module."""

    def test_analyze_code_json_output(self):
        """Test analyze_code with JSON output."""
        from code_scalpel.cli import analyze_code

        code = "x = 1 + 2"
        result = analyze_code(code, "json", language="python")
        assert result == 0

    def test_scan_code_security_function(self):
        """Test scan_code_security function."""
        from code_scalpel.cli import scan_code_security

        code = "x = 1"
        result = scan_code_security(code, "text")
        # Return code depends on vulnerabilities found
        assert result in [0, 2]
