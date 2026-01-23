"""
[20251216_TEST] Adversarial Tests for v3.0.0 "Autonomy".

Covers:
- Error-to-diff / fix-hint fidelity
- Sandbox containment (no FS/network side effects)
- Loop termination guardrails
- Cross-language self-repair hints
- Confidence transparency
"""

import builtins

import pytest

from code_scalpel.ast_tools.cross_file_extractor import calculate_confidence
from code_scalpel.generators.refactor_simulator import RefactorSimulator
from code_scalpel.polyglot.contract_breach_detector import (
    ContractBreachDetector,
    Edge,
    Node,
    UnifiedGraph,
)
from code_scalpel.symbolic_execution_tools.engine import SymbolicAnalyzer


class TestADV300FixHints:
    """
    [20251216_TEST] Error-to-diff / fix-hint fidelity for contract breaches.
    """

    def _build_graph(self, edge_confidence: float = 0.95) -> UnifiedGraph:
        graph = UnifiedGraph()

        server = Node(
            node_id="java::UserController:getUser",
            node_type="endpoint",
            language="java",
            fields={"id", "email"},
            metadata={
                "path": "/api/users/{id}",
                "response_format": {"id": "int", "email": "str"},
            },
        )
        client = Node(
            node_id="ts::fetchUser",
            node_type="function",
            language="typescript",
            metadata={
                "target_path": "/api/users/get",
                "referenced_fields": {"userId"},
                "expected_format": {"id": "string", "email": "string"},
            },
        )

        graph.add_node(server)
        graph.add_node(client)
        graph.add_edge(
            Edge(
                from_id=client.node_id,
                to_id=server.node_id,
                edge_type="type_reference",
                confidence=edge_confidence,
            )
        )
        graph.add_edge(
            Edge(
                from_id=client.node_id,
                to_id=server.node_id,
                edge_type="http_call",
                confidence=edge_confidence,
            )
        )
        return graph

    def test_fix_hint_emitted_for_field_and_path_drift(self):
        graph = self._build_graph(edge_confidence=0.95)
        detector = ContractBreachDetector(graph)

        breaches = detector.detect_breaches("java::UserController:getUser", min_confidence=0.8)
        assert breaches, "Expected breaches for contract drift"

        hints = [b.fix_hint for b in breaches]
        joined = " ".join(hints)
        assert "Update ts::fetchUser" in joined
        assert "references fields" in breaches[0].description or "path changed" in breaches[0].description
        assert all(0.0 <= b.confidence <= 1.0 for b in breaches)

    def test_low_confidence_edges_are_rejected(self):
        graph = self._build_graph(edge_confidence=0.2)
        detector = ContractBreachDetector(graph)

        breaches = detector.detect_breaches("java::UserController:getUser", min_confidence=0.8)
        assert breaches == [], "Low-confidence edges must be ignored"


class TestADV301SandboxContainment:
    """
    [20251216_TEST] Sandbox containment: ensure refactor simulation avoids side effects.
    """

    def test_refactor_simulator_has_no_fs_writes(self, tmp_path, monkeypatch):
        simulator = RefactorSimulator()
        sentinel = tmp_path / "outside.txt"
        sentinel.write_text("baseline")

        # Fail if any file open is attempted during simulation
        def _no_open(*args, **kwargs):  # pragma: no cover - defensive
            raise AssertionError("RefactorSimulator must not touch filesystem")

        monkeypatch.setattr(builtins, "open", _no_open)

        original = "def add(x, y):\n    return x + y\n"
        patch = "@@ -1,2 +1,3 @@\n def add(x, y):\n-    return x + y\n+    return x + y  # safe change\n"

        result = simulator.simulate(original_code=original, patch=patch)
        assert result.patched_code, "Simulation should return patched code without side effects"
        assert sentinel.read_text() == "baseline"


class TestADV302LoopTermination:
    """
    [20251216_TEST] Loop termination guardrails: bounded unrolling enforced.
    """

    def test_symbolic_analyzer_bounds_infinite_loop(self):
        analyzer = SymbolicAnalyzer(max_loop_iterations=3, solver_timeout=500, enable_cache=False)
        code = """
while True:
    x = 1
        """
        result = analyzer.analyze(code)
        assert result.total_paths <= analyzer.max_loop_iterations, "Loop should be pruned by fuel limit"
        assert result.feasible_count >= 1, "Analyzer should still produce at least one feasible path"


class TestADV303ConfidenceTransparency:
    """
    [20251216_TEST] Confidence transparency: clamp >1.0, reject negatives.
    """

    def test_confidence_clamps_and_rejects_invalid(self):
        assert calculate_confidence(depth=0, decay_factor=1.5) == 1.0
        with pytest.raises(ValueError):
            calculate_confidence(depth=1, decay_factor=-0.1)


class TestADV304CrossLanguageSelfRepair:
    """
    [20251216_TEST] Cross-language self-repair hints must align server and client.
    """

    def test_contract_breach_fix_hint_is_actionable(self):
        graph = UnifiedGraph()
        server = Node(
            node_id="java::OrderApi:getOrder",
            node_type="endpoint",
            language="java",
            metadata={"path": "/api/v2/orders/{id}"},
        )
        client = Node(
            node_id="js::fetchOrder",
            node_type="function",
            language="javascript",
            metadata={"target_path": "/api/v1/orders/{id}"},
        )
        graph.add_node(server)
        graph.add_node(client)
        graph.add_edge(
            Edge(
                from_id=client.node_id,
                to_id=server.node_id,
                edge_type="http_call",
                confidence=0.92,
            )
        )

        breaches = ContractBreachDetector(graph).detect_breaches("java::OrderApi:getOrder", min_confidence=0.8)
        assert breaches, "Breach should be detected for endpoint drift"
        hint = breaches[0].fix_hint
        assert "/api/v2/orders" in hint and "fetchOrder" in hint
        assert breaches[0].breach_type.name == "ENDPOINT_PATH_CHANGED"
