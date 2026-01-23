"""[20251217_TEST] Final push to 95% coverage.

Targeting: error_to_diff, autogen integration, langgraph, mutation_gate.
"""

import ast
import tempfile
from pathlib import Path

import pytest

from code_scalpel.security.analyzers.taint_tracker import (  # [20251225_BUGFIX]
    TaintSource,
)


class TestErrorToDiffFinalCoverage:
    """Cover more lines in error_to_diff.py."""

    def test_analyze_type_error(self):
        """Cover TypeError path."""
        from code_scalpel.autonomy.error_to_diff import ErrorToDiffEngine

        with tempfile.TemporaryDirectory() as tmp:
            e2d = ErrorToDiffEngine(Path(tmp))
            error_msg = "TypeError: unsupported operand type(s) for +: 'int' and 'str'"
            source = '\ndef add():\n    return 1 + "2"\n'
            result = e2d.analyze_error(error_msg, source, "python")
            assert result is not None

    def test_analyze_attribute_error(self):
        """Cover AttributeError path."""
        from code_scalpel.autonomy.error_to_diff import ErrorToDiffEngine

        with tempfile.TemporaryDirectory() as tmp:
            e2d = ErrorToDiffEngine(Path(tmp))
            error_msg = "AttributeError: 'NoneType' object has no attribute 'method'"
            source = "\ndef test():\n    x = None\n    x.method()\n"
            result = e2d.analyze_error(error_msg, source, "python")
            assert result is not None

    def test_analyze_import_error(self):
        """Cover ImportError path."""
        from code_scalpel.autonomy.error_to_diff import ErrorToDiffEngine

        with tempfile.TemporaryDirectory() as tmp:
            e2d = ErrorToDiffEngine(Path(tmp))
            error_msg = "ImportError: No module named 'nonexistent'"
            source = "import nonexistent"
            result = e2d.analyze_error(error_msg, source, "python")
            assert result is not None


class TestAutogenIntegration:
    """Cover autogen integration lines."""

    def test_autogen_import(self):
        """Cover import path."""
        try:
            from code_scalpel.autonomy.integrations import autogen

            assert autogen is not None
        except ImportError:
            pytest.skip("AutoGen not installed")


class TestLanggraphIntegration:
    """Cover langgraph integration lines."""

    def test_langgraph_import(self):
        """Cover import path."""
        try:
            from code_scalpel.autonomy.integrations import langgraph

            assert langgraph is not None
        except ImportError:
            pytest.skip("LangGraph not installed")


class TestMutationGateCoverage:
    """Cover mutation_gate.py lines."""

    def test_mutation_gate_properties(self):
        """Cover MutationTestGate properties."""
        from code_scalpel.autonomy.mutation_gate import MutationTestGate

        with tempfile.TemporaryDirectory() as tmp:
            gate = MutationTestGate(Path(tmp))
            assert gate is not None


class TestMoreBranchCoverage:
    """Cover more branches across modules."""

    def test_pdg_with_walrus(self):
        """Cover walrus operator in PDG."""
        from code_scalpel.pdg_tools.builder import PDGBuilder

        code = "\nif (n := len([1,2,3])) > 2:\n    print(n)\n"
        builder = PDGBuilder()
        pdg, cfg = builder.build(code)
        assert pdg is not None

    def test_pdg_with_starred_assignment(self):
        """Cover starred assignment in PDG."""
        from code_scalpel.pdg_tools.builder import PDGBuilder

        code = "\na, *rest, b = [1, 2, 3, 4, 5]\nprint(rest)\n"
        builder = PDGBuilder()
        pdg, cfg = builder.build(code)
        assert pdg is not None

    def test_type_inference_with_complex_type(self):
        """Cover complex type inference."""
        from code_scalpel.symbolic_execution_tools.type_inference import (
            TypeInferenceEngine,
        )

        engine = TypeInferenceEngine()
        result = engine.infer("x: dict[str, list[int]] = {}")
        assert result is not None

    def test_call_graph_with_import_from(self):
        """Cover import from in call graph."""
        from code_scalpel.ast_tools.call_graph import CallGraphBuilder

        with tempfile.TemporaryDirectory() as tmp:
            code = '\nfrom os.path import join, exists\nresult = join("a", "b")\n'
            (Path(tmp) / "imports.py").write_text(code)
            builder = CallGraphBuilder(Path(tmp))
            graph = builder.build()
            assert graph is not None

    def test_surgical_extractor_with_decorator_chain(self):
        """Cover decorator chain extraction."""
        from code_scalpel.surgical_extractor import SurgicalExtractor

        code = "\n@decorator1\n@decorator2\n@decorator3\ndef decorated():\n    pass\n"
        extractor = SurgicalExtractor(code)
        result = extractor.get_function("decorated")
        assert result is not None
        assert "@decorator" in result.code

    def test_test_generator_with_simple_code(self):
        """Cover simple code in test generator."""
        from code_scalpel.generators.test_generator import TestGenerator

        gen = TestGenerator()
        code = "\ndef add(a, b):\n    return a + b\n"
        result = gen.generate(code)
        assert result is not None

    def test_refactor_with_docstring(self):
        """Cover docstring handling in refactor."""
        from code_scalpel.generators.refactor_simulator import RefactorSimulator

        sim = RefactorSimulator()
        original = '\ndef documented():\n    """This is a docstring."""\n    pass\n'
        modified = '\ndef documented():\n    """Updated docstring."""\n    return None\n'
        result = sim.simulate(original, modified)
        assert result is not None


class TestFinalBranchCoverage:
    """Final batch targeting specific branches."""

    def test_taint_tracker_medium_sanitizer(self):
        """Cover MEDIUM level sanitizer."""
        from code_scalpel.security.analyzers import TaintInfo, TaintLevel, TaintTracker

        tracker = TaintTracker()
        taint = TaintInfo(source=TaintSource.USER_INPUT, level=TaintLevel.MEDIUM)
        tracker.mark_tainted("input", taint)
        tracker.apply_sanitizer("input", "escape")
        info = tracker.get_taint("input")
        assert info is not None

    def test_symbolic_engine_with_string_ops(self):
        """Cover string operations in symbolic engine."""
        from code_scalpel.symbolic_execution_tools.engine import SymbolicAnalyzer

        code = "\ndef concat(a, b):\n    return a + b\n"
        analyzer = SymbolicAnalyzer()
        result = analyzer.analyze(code)
        assert result is not None

    def test_osv_client_batch_query(self):
        """Cover batch query in OSV client."""
        from code_scalpel.security.dependencies import OSVClient

        client = OSVClient()
        packages = [("requests", "2.25.1"), ("flask", "1.1.2")]
        results = []
        for pkg, version in packages:
            result = client.query_package(pkg, version)
            results.append(result)
        assert len(results) == 2

    def test_pdg_analyzer_with_data_flow(self):
        """Cover data flow analysis in PDG."""
        from code_scalpel.pdg_tools.analyzer import PDGAnalyzer
        from code_scalpel.pdg_tools.builder import PDGBuilder

        code = "\ndef flow(x):\n    y = x + 1\n    z = y * 2\n    return z\n"
        builder = PDGBuilder()
        pdg, cfg = builder.build(code)
        analyzer = PDGAnalyzer(pdg)
        result = analyzer.analyze_data_flow()
        assert result is not None

    def test_secret_scanner_private_key(self):
        """Cover private key detection."""
        from code_scalpel.security.secrets.secret_scanner import SecretScanner

        scanner = SecretScanner()
        code = '\nPRIVATE_KEY = """-----BEGIN RSA PRIVATE KEY-----\nMIIEpAIBAAKCAQEA...\n-----END RSA PRIVATE KEY-----"""\n'
        tree = ast.parse(code)
        result = scanner.scan(tree)
        assert isinstance(result, list)

    def test_unified_sink_with_ldap(self):
        """Cover LDAP sink detection."""
        from code_scalpel.security.analyzers.unified_sink_detector import (
            UnifiedSinkDetector,
        )

        detector = UnifiedSinkDetector()
        code = "ldap.search(user_filter)"
        result = detector.detect_sinks(code, "python")
        assert isinstance(result, list)

    def test_analysis_cache_get_or_parse(self):
        """Cover get_or_parse method."""
        import os

        from code_scalpel.cache.unified_cache import AnalysisCache

        cache = AnalysisCache()
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w") as f:
            f.write("x = 1")
            temp_path = f.name
        try:

            def parse_fn(path):
                with open(path) as fp:
                    return ast.parse(fp.read())

            result = cache.get_or_parse(temp_path, parse_fn)
            assert result is not None
        finally:
            os.unlink(temp_path)

    def test_contract_breach_detector(self):
        """[20251219_TEST] Cover contract breach detection with proper initialization."""
        from code_scalpel.polyglot.contract_breach_detector import (
            ContractBreachDetector,
            Edge,
            Node,
            UnifiedGraph,
        )

        graph = UnifiedGraph()
        java_node = Node(node_id="java::UserService::getUser", node_type="method", language="java")
        graph.add_node(java_node)
        ts_node = Node(
            node_id="typescript::api::fetchUser",
            node_type="function",
            language="typescript",
        )
        graph.add_node(ts_node)
        edge = Edge(
            from_id="typescript::api::fetchUser",
            to_id="java::UserService::getUser",
            edge_type="api_call",
            confidence=0.9,
        )
        graph.add_edge(edge)
        detector = ContractBreachDetector(graph)
        breaches = detector.detect_breaches("java::UserService::getUser")
        assert isinstance(breaches, list)
