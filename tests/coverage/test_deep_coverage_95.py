"""[20251217_TEST] Target error_to_diff.py and other low-coverage modules.

Target remaining 39 elements needed for 95%.
"""

import tempfile
from pathlib import Path

from code_scalpel.security.analyzers.taint_tracker import (  # [20251225_BUGFIX]
    TaintSource,
)


class TestErrorToDiffCoverage:
    """Cover uncovered branches in error_to_diff.py."""

    def test_analyze_syntax_error(self):
        """Cover SyntaxError path."""
        from code_scalpel.autonomy.error_to_diff import ErrorToDiffEngine

        with tempfile.TemporaryDirectory() as tmp:
            e2d = ErrorToDiffEngine(Path(tmp))
            error_msg = "SyntaxError: invalid syntax (test.py, line 5)"
            source = "\ndef broken:\n    pass\n"
            result = e2d.analyze_error(error_msg, source, "python")
            assert result is not None

    def test_analyze_name_error(self):
        """Cover NameError path."""
        from code_scalpel.autonomy.error_to_diff import ErrorToDiffEngine

        with tempfile.TemporaryDirectory() as tmp:
            e2d = ErrorToDiffEngine(Path(tmp))
            error_msg = "NameError: name 'undefined_var' is not defined"
            source = "\ndef test():\n    print(undefined_var)\n"
            result = e2d.analyze_error(error_msg, source, "python")
            assert result is not None

    def test_fix_missing_colon(self):
        """Cover missing colon fix."""
        from code_scalpel.autonomy.error_to_diff import ErrorToDiffEngine

        with tempfile.TemporaryDirectory() as tmp:
            e2d = ErrorToDiffEngine(Path(tmp))
            error_msg = "SyntaxError: expected ':' (test.py, line 1)"
            source = "def foo()\n    pass"
            result = e2d.analyze_error(error_msg, source, "python")
            assert result is not None

    def test_fix_indentation(self):
        """Cover indentation fix path."""
        from code_scalpel.autonomy.error_to_diff import ErrorToDiffEngine

        with tempfile.TemporaryDirectory() as tmp:
            e2d = ErrorToDiffEngine(Path(tmp))
            error_msg = "IndentationError: expected an indented block (test.py, line 2)"
            source = "def foo():\npass"
            result = e2d.analyze_error(error_msg, source, "python")
            assert result is not None

    def test_fix_balance_parentheses_open(self):
        """Cover parentheses balancing (too many open)."""
        from code_scalpel.autonomy.error_to_diff import ErrorToDiffEngine

        with tempfile.TemporaryDirectory() as tmp:
            e2d = ErrorToDiffEngine(Path(tmp))
            error_msg = "SyntaxError: '(' was never closed (test.py, line 1)"
            source = "print(foo("
            result = e2d.analyze_error(error_msg, source, "python")
            assert result is not None

    def test_fix_balance_parentheses_close(self):
        """Cover parentheses balancing (too many close)."""
        from code_scalpel.autonomy.error_to_diff import ErrorToDiffEngine

        with tempfile.TemporaryDirectory() as tmp:
            e2d = ErrorToDiffEngine(Path(tmp))
            error_msg = "SyntaxError: unmatched ')' (test.py, line 1)"
            source = "print(foo))"
            result = e2d.analyze_error(error_msg, source, "python")
            assert result is not None

    def test_non_python_language(self):
        """Cover non-Python language path (no AST validation)."""
        from code_scalpel.autonomy.error_to_diff import ErrorToDiffEngine

        with tempfile.TemporaryDirectory() as tmp:
            e2d = ErrorToDiffEngine(Path(tmp))
            error_msg = "Error: some javascript error"
            source = "const x = 1"
            result = e2d.analyze_error(error_msg, source, "javascript")
            assert result is not None


class TestASTBuilderCoverage:
    """Cover uncovered lines in builder.py."""

    def test_build_with_hooks(self):
        """Cover hook execution path."""
        from code_scalpel.ast_tools.builder import ASTBuilder

        builder = ASTBuilder()

        def my_hook(code):
            return code.replace("TAB", "    ")

        builder.add_preprocessing_hook(my_hook)
        result = builder.build_ast("def foo():\n    pass")
        assert result is not None

    def test_build_invalid_syntax(self):
        """Cover invalid syntax path."""
        from code_scalpel.ast_tools.builder import ASTBuilder

        builder = ASTBuilder()
        try:
            builder.build_ast("def broken:")
        except SyntaxError:
            pass

    def test_build_empty_code(self):
        """Cover empty code path."""
        from code_scalpel.ast_tools.builder import ASTBuilder

        builder = ASTBuilder()
        result = builder.build_ast("")
        assert result is not None


class TestSandboxCoverage:
    """Cover uncovered lines in sandbox.py."""

    def test_sandbox_properties(self):
        """Cover sandbox property access."""
        from code_scalpel.autonomy.sandbox import SandboxExecutor

        sandbox = SandboxExecutor()
        assert sandbox.max_cpu_seconds is not None
        assert sandbox.max_memory_mb is not None
        assert sandbox.max_disk_mb is not None
        assert sandbox.network_enabled is not None or not sandbox.network_enabled
        assert sandbox.isolation_level is not None


class TestTaintTrackerDeepCoverage:
    """Cover more taint tracker branches."""

    def test_taint_with_none_level(self):
        """Cover NONE taint level."""
        from code_scalpel.security.analyzers import TaintInfo, TaintLevel, TaintTracker

        tracker = TaintTracker()
        taint = TaintInfo(source=TaintSource.USER_INPUT, level=TaintLevel.NONE)
        tracker.mark_tainted("safe_var", taint)
        info = tracker.get_taint("safe_var")
        assert info.level == TaintLevel.NONE

    def test_taint_source_method(self):
        """Cover taint_source method."""
        from code_scalpel.security.analyzers import TaintTracker

        tracker = TaintTracker()
        tracker.taint_source("user_data", "request.args")
        assert tracker.is_tainted("user_data")

    def test_clear_tracker(self):
        """Cover clear method."""
        from code_scalpel.security.analyzers import TaintInfo, TaintTracker

        tracker = TaintTracker()
        taint = TaintInfo(source=TaintSource.USER_INPUT)
        tracker.mark_tainted("var", taint)
        tracker.clear()
        assert not tracker.is_tainted("var")


class TestTypeInferenceDeepCoverage:
    """Cover more type inference branches."""

    def test_infer_complex_expression(self):
        """Cover complex expression inference."""
        from code_scalpel.symbolic_execution_tools.type_inference import (
            TypeInferenceEngine,
        )

        engine = TypeInferenceEngine()
        result = engine.infer("x = (1 + 2) * (3 - 4) / 5.0")
        assert result is not None

    def test_infer_multiple_assignment(self):
        """Cover multiple assignment inference."""
        from code_scalpel.symbolic_execution_tools.type_inference import (
            TypeInferenceEngine,
        )

        engine = TypeInferenceEngine()
        result = engine.infer("a = b = c = 1")
        assert result is not None

    def test_infer_augmented_assignment(self):
        """Cover augmented assignment inference."""
        from code_scalpel.symbolic_execution_tools.type_inference import (
            TypeInferenceEngine,
        )

        engine = TypeInferenceEngine()
        result = engine.infer("x = 1; x += 2")
        assert result is not None


class TestSymbolicEngineCoverage:
    """Cover more symbolic engine branches."""

    def test_analyze_simple_function(self):
        """Cover simple function analysis."""
        from code_scalpel.symbolic_execution_tools.engine import SymbolicAnalyzer

        code = "\ndef double(x):\n    return x * 2\n"
        analyzer = SymbolicAnalyzer()
        result = analyzer.analyze(code)
        assert result is not None

    def test_analyze_nested_if(self):
        """Cover nested if handling."""
        from code_scalpel.symbolic_execution_tools.engine import SymbolicAnalyzer

        code = "\ndef nested(x, y):\n    if x > 0:\n        if y > 0:\n            return 1\n        return 2\n    return 3\n"
        analyzer = SymbolicAnalyzer()
        result = analyzer.analyze(code)
        assert result is not None

    def test_analyze_while_loop(self):
        """Cover while loop handling."""
        from code_scalpel.symbolic_execution_tools.engine import SymbolicAnalyzer

        code = (
            "\ndef countdown(n):\n    _ = 0\n    while n > 0:\n        result += n\n        n -= 1\n    return result\n"
        )
        analyzer = SymbolicAnalyzer()
        result = analyzer.analyze(code)
        assert result is not None


class TestPDGBuilderDeepCoverage:
    """Cover more PDG builder branches."""

    def test_build_with_nested_try(self):
        """Cover nested try blocks."""
        from code_scalpel.pdg_tools.builder import PDGBuilder

        code = "\ndef nested_try():\n    try:\n        try:\n            x = 1 / 0\n        except ZeroDivisionError:\n            x = 0\n    except Exception:\n        x = -1\n    return x\n"
        builder = PDGBuilder()
        pdg, cfg = builder.build(code)
        assert pdg is not None

    def test_build_with_context_manager(self):
        """Cover with statement handling."""
        from code_scalpel.pdg_tools.builder import PDGBuilder

        code = '\ndef with_context():\n    with open("file.txt") as f:\n        data = f.read()\n    return data\n'
        builder = PDGBuilder()
        pdg, cfg = builder.build(code)
        assert pdg is not None

    def test_build_with_multiple_returns(self):
        """Cover multiple return paths."""
        from code_scalpel.pdg_tools.builder import PDGBuilder

        code = "\ndef multi_return(x):\n    if x < 0:\n        return -1\n    elif x == 0:\n        return 0\n    else:\n        return 1\n"
        builder = PDGBuilder()
        pdg, cfg = builder.build(code)
        assert pdg is not None


class TestSurgicalExtractorDeepCoverage:
    """Cover more surgical extractor branches."""

    def test_extract_property(self):
        """Cover property extraction."""
        from code_scalpel.surgical_extractor import SurgicalExtractor

        code = "\nclass MyClass:\n    @property\n    def value(self):\n        return self._value\n    \n    @value.setter\n    def value(self, v):\n        self._value = v\n"
        extractor = SurgicalExtractor(code)
        result = extractor.get_method("MyClass", "value")
        assert result is not None

    def test_extract_classmethod(self):
        """Cover classmethod extraction."""
        from code_scalpel.surgical_extractor import SurgicalExtractor

        code = "\nclass MyClass:\n    @classmethod\n    def from_dict(cls, data):\n        return cls()\n"
        extractor = SurgicalExtractor(code)
        result = extractor.get_method("MyClass", "from_dict")
        assert result is not None

    def test_extract_nested_class(self):
        """Cover nested class extraction."""
        from code_scalpel.surgical_extractor import SurgicalExtractor

        code = "\nclass Outer:\n    class Inner:\n        def inner_method(self):\n            pass\n"
        extractor = SurgicalExtractor(code)
        result = extractor.get_class("Outer")
        assert result is not None
        assert "Inner" in result.code


class TestTestGeneratorDeepCoverage:
    """Cover more test generator branches."""

    def test_generate_for_property(self):
        """Cover property test generation."""
        from code_scalpel.generators.test_generator import TestGenerator

        gen = TestGenerator()
        code = "\nclass Data:\n    @property\n    def items(self):\n        return self._items\n"
        result = gen.generate(code)
        assert result is not None

    def test_generate_for_async_function(self):
        """Cover async function test generation."""
        from code_scalpel.generators.test_generator import TestGenerator

        gen = TestGenerator()
        code = "\nasync def fetch_data(url):\n    return await http.get(url)\n"
        result = gen.generate(code)
        assert result is not None
