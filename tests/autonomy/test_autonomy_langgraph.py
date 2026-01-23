"""
Tests for LangGraph autonomy integration.

[20251217_TEST] Comprehensive tests for LangGraph StateGraph integration.
"""

import os
import sys
import unittest

# Add src directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

try:
    import pytest

    LANGGRAPH_AVAILABLE = True
    try:
        from code_scalpel.autonomy.integrations.langgraph import (
            ScalpelState,
            analyze_error_node,
            apply_fix_node,
            create_scalpel_fix_graph,
            escalate_node,
            fix_passed,
            generate_fix_node,
            has_valid_fixes,
            validate_fix_node,
        )
    except ImportError:
        LANGGRAPH_AVAILABLE = False
except ImportError:
    LANGGRAPH_AVAILABLE = False
    pytest = None


@unittest.skipIf(not LANGGRAPH_AVAILABLE, "LangGraph not available")
class TestLangGraphIntegration(unittest.TestCase):
    """Tests for LangGraph integration."""

    def test_analyze_error_node_syntax_error(self):
        """Test analyze_error_node with syntax error."""
        state: ScalpelState = {
            "code": "def foo( return 42",
            "language": "python",
            "error": "SyntaxError: invalid syntax",
            "fix_attempts": [],
            "success": False,
        }

        result = analyze_error_node(state)

        self.assertIn("fix_attempts", result)
        self.assertGreater(len(result["fix_attempts"]), 0)
        self.assertEqual(result["fix_attempts"][-1]["step"], "analyze_error")
        self.assertIn("analysis", result["fix_attempts"][-1])

    def test_analyze_error_node_runtime_error(self):
        """Test analyze_error_node with runtime error."""
        state: ScalpelState = {
            "code": "def divide(a, b):\n    return a / b",
            "language": "python",
            "error": "ZeroDivisionError: division by zero",
            "fix_attempts": [],
            "success": False,
        }

        result = analyze_error_node(state)

        self.assertIn("fix_attempts", result)
        self.assertGreater(len(result["fix_attempts"]), 0)
        analysis = result["fix_attempts"][-1].get("analysis", {})
        self.assertTrue(analysis.get("parsed"))

    def test_generate_fix_node_with_analysis(self):
        """Test generate_fix_node generates fix based on analysis."""
        state: ScalpelState = {
            "code": "def foo():\n    pass",
            "language": "python",
            "error": None,
            "fix_attempts": [
                {
                    "step": "analyze_error",
                    "analysis": {
                        "type": "syntax_error",
                        "line": 1,
                        "parsed": False,
                    },
                }
            ],
            "success": False,
        }

        result = generate_fix_node(state)

        self.assertIn("fix_attempts", result)
        self.assertGreater(len(result["fix_attempts"]), 1)
        fix = result["fix_attempts"][-1]
        self.assertEqual(fix["step"], "generate_fix")
        self.assertTrue(fix.get("has_fix"))

    def test_validate_fix_node_valid_code(self):
        """Test validate_fix_node with valid code."""
        state: ScalpelState = {
            "code": "def foo():\n    return 42",
            "language": "python",
            "error": None,
            "fix_attempts": [
                {
                    "step": "generate_fix",
                    "has_fix": True,
                }
            ],
            "success": False,
        }

        result = validate_fix_node(state)

        self.assertIn("fix_attempts", result)
        validation = result["fix_attempts"][-1]
        self.assertEqual(validation["step"], "validate_fix")
        self.assertIn("validation", validation)

    def test_apply_fix_node(self):
        """Test apply_fix_node marks fix as applied."""
        state: ScalpelState = {
            "code": "def foo():\n    return 42",
            "language": "python",
            "error": None,
            "fix_attempts": [],
            "success": False,
        }

        result = apply_fix_node(state)

        self.assertIn("fix_attempts", result)
        self.assertGreater(len(result["fix_attempts"]), 0)
        self.assertEqual(result["fix_attempts"][-1]["step"], "apply_fix")
        self.assertTrue(result["fix_attempts"][-1]["applied"])
        self.assertTrue(result["success"])

    def test_escalate_node(self):
        """Test escalate_node marks escalation."""
        state: ScalpelState = {
            "code": "invalid code",
            "language": "python",
            "error": "Multiple errors",
            "fix_attempts": [],
            "success": False,
        }

        result = escalate_node(state)

        self.assertIn("fix_attempts", result)
        self.assertGreater(len(result["fix_attempts"]), 0)
        self.assertEqual(result["fix_attempts"][-1]["step"], "escalate")
        self.assertTrue(result["fix_attempts"][-1]["requires_human"])
        self.assertFalse(result["success"])

    def test_has_valid_fixes_true(self):
        """Test has_valid_fixes returns True when fix available."""
        state: ScalpelState = {
            "code": "",
            "language": "python",
            "error": None,
            "fix_attempts": [{"has_fix": True}],
            "success": False,
        }

        self.assertTrue(has_valid_fixes(state))

    def test_has_valid_fixes_false(self):
        """Test has_valid_fixes returns False when no fix."""
        state: ScalpelState = {
            "code": "",
            "language": "python",
            "error": None,
            "fix_attempts": [{"has_fix": False}],
            "success": False,
        }

        self.assertFalse(has_valid_fixes(state))

    def test_fix_passed_true(self):
        """Test fix_passed returns True when validation passes."""
        state: ScalpelState = {
            "code": "",
            "language": "python",
            "error": None,
            "fix_attempts": [{"validation": "passed"}],
            "success": False,
        }

        self.assertTrue(fix_passed(state))

    def test_fix_passed_false(self):
        """Test fix_passed returns False when validation fails."""
        state: ScalpelState = {
            "code": "",
            "language": "python",
            "error": None,
            "fix_attempts": [{"validation": "failed"}],
            "success": False,
        }

        self.assertFalse(fix_passed(state))

    def test_create_scalpel_fix_graph(self):
        """Test create_scalpel_fix_graph returns compiled graph."""
        graph = create_scalpel_fix_graph()

        # Verify graph has invoke method (is compiled)
        self.assertTrue(hasattr(graph, "invoke"))

    def test_graph_execution_syntax_error(self):
        """Test full graph execution with syntax error."""
        graph = create_scalpel_fix_graph()

        result = graph.invoke(
            {
                "code": "def foo( return 42",
                "language": "python",
                "error": "SyntaxError",
                "fix_attempts": [],
                "success": False,
            }
        )

        # Should have gone through nodes
        self.assertIn("fix_attempts", result)
        self.assertGreater(len(result["fix_attempts"]), 0)

    def test_graph_execution_valid_code(self):
        """Test full graph execution with valid code."""
        graph = create_scalpel_fix_graph()

        result = graph.invoke(
            {
                "code": "def foo():\n    return 42",
                "language": "python",
                "error": None,
                "fix_attempts": [],
                "success": False,
            }
        )

        # Should have attempted analysis and fix
        self.assertIn("fix_attempts", result)
        self.assertGreater(len(result["fix_attempts"]), 0)


if __name__ == "__main__":
    unittest.main()
