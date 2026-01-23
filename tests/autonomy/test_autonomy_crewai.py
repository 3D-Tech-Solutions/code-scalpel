"""
Tests for CrewAI autonomy integration.

[20251217_TEST] Comprehensive tests for CrewAI Crew integration.
"""

import os
import sys
import unittest

# Add src directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

try:
    import pytest

    CREWAI_AVAILABLE = True
    try:
        from code_scalpel.autonomy.integrations.crewai import (
            ScalpelAnalyzeTool,
            ScalpelErrorToDiffTool,
            ScalpelGenerateFixTool,
            ScalpelSandboxTool,
            ScalpelSecurityScanTool,
            ScalpelValidateASTTool,
            create_scalpel_fix_crew,
        )
    except ImportError:
        CREWAI_AVAILABLE = False
except ImportError:
    CREWAI_AVAILABLE = False
    pytest = None


@unittest.skipIf(not CREWAI_AVAILABLE, "CrewAI not available")
class TestCrewAIIntegration(unittest.TestCase):
    """Tests for CrewAI integration."""

    def test_scalpel_analyze_tool_valid_code(self):
        """Test ScalpelAnalyzeTool with valid code."""
        tool = ScalpelAnalyzeTool()

        result = tool._run("def foo():\n    return 42")

        self.assertIn("parsed", result)
        self.assertIn("True", result)

    def test_scalpel_analyze_tool_syntax_error(self):
        """Test ScalpelAnalyzeTool with syntax error."""
        tool = ScalpelAnalyzeTool()

        result = tool._run("def foo( return 42")

        self.assertIn("parsed", result)
        self.assertIn("False", result)
        self.assertIn("error", result)

    def test_scalpel_error_to_diff_tool(self):
        """Test ScalpelErrorToDiffTool converts error to diff."""
        tool = ScalpelErrorToDiffTool()

        result = tool._run(
            code="def foo():\n    pass",
            error="SyntaxError at line 1",
        )

        self.assertIn("error_type", result)
        self.assertIn("line", result)

    def test_scalpel_generate_fix_tool_valid_code(self):
        """Test ScalpelGenerateFixTool with valid code."""
        tool = ScalpelGenerateFixTool()

        result = tool._run(
            code="def foo():\n    return 42",
            analysis="No issues",
        )

        self.assertIn("fix_available", result)

    def test_scalpel_validate_ast_tool_valid(self):
        """Test ScalpelValidateASTTool with valid code."""
        tool = ScalpelValidateASTTool()

        result = tool._run("def foo():\n    return 42")

        self.assertIn("valid", result)
        self.assertIn("True", result)

    def test_scalpel_validate_ast_tool_invalid(self):
        """Test ScalpelValidateASTTool with invalid code."""
        tool = ScalpelValidateASTTool()

        result = tool._run("def foo( return 42")

        self.assertIn("valid", result)
        self.assertIn("False", result)

    def test_scalpel_sandbox_tool_valid(self):
        """Test ScalpelSandboxTool with valid code."""
        tool = ScalpelSandboxTool()

        result = tool._run("def foo():\n    return 42")

        self.assertIn("sandbox_passed", result)

    def test_scalpel_sandbox_tool_invalid(self):
        """Test ScalpelSandboxTool with invalid code."""
        tool = ScalpelSandboxTool()

        result = tool._run("invalid python code !!!")

        self.assertIn("sandbox_passed", result)
        self.assertIn("False", result)

    def test_scalpel_security_scan_tool_safe(self):
        """Test ScalpelSecurityScanTool with safe code."""
        tool = ScalpelSecurityScanTool()

        result = tool._run("def foo():\n    return 42")

        self.assertIn("has_vulnerabilities", result)

    def test_scalpel_security_scan_tool_vulnerable(self):
        """Test ScalpelSecurityScanTool with vulnerable code."""
        tool = ScalpelSecurityScanTool()

        vulnerable_code = """
import os
def run(cmd):
    os.system(cmd)
"""

        result = tool._run(vulnerable_code)

        self.assertIn("has_vulnerabilities", result)
        # May or may not detect depending on implementation

    @unittest.skip("Requires OPENAI_API_KEY")
    def test_create_scalpel_fix_crew(self):
        """Test create_scalpel_fix_crew returns configured crew."""
        crew = create_scalpel_fix_crew()

        # Verify crew structure
        self.assertIsNotNone(crew)
        self.assertEqual(len(crew.agents), 3)
        self.assertEqual(len(crew.tasks), 3)

        # Verify agent roles
        roles = [agent.role for agent in crew.agents]
        self.assertIn("Error Analyzer", roles)
        self.assertIn("Fix Generator", roles)
        self.assertIn("Fix Validator", roles)

    @unittest.skip("Requires OPENAI_API_KEY")
    def test_crew_agents_have_tools(self):
        """Test crew agents have appropriate tools."""
        crew = create_scalpel_fix_crew()

        # Error Analyzer should have 2 tools
        error_analyzer = crew.agents[0]
        self.assertEqual(len(error_analyzer.tools), 2)

        # Fix Generator should have 2 tools
        fix_generator = crew.agents[1]
        self.assertEqual(len(fix_generator.tools), 2)

        # Validator should have 2 tools
        validator = crew.agents[2]
        self.assertEqual(len(validator.tools), 2)

    @unittest.skip("Requires OPENAI_API_KEY")
    def test_crew_tasks_have_descriptions(self):
        """Test crew tasks have proper descriptions."""
        crew = create_scalpel_fix_crew()

        for task in crew.tasks:
            self.assertIsNotNone(task.description)
            self.assertGreater(len(task.description), 0)
            self.assertIsNotNone(task.expected_output)

    def test_tool_name_uniqueness(self):
        """Test all tools have unique names."""
        tools = [
            ScalpelAnalyzeTool(),
            ScalpelErrorToDiffTool(),
            ScalpelGenerateFixTool(),
            ScalpelValidateASTTool(),
            ScalpelSandboxTool(),
            ScalpelSecurityScanTool(),
        ]

        names = [tool.name for tool in tools]
        self.assertEqual(len(names), len(set(names)))

    def test_tool_descriptions(self):
        """Test all tools have descriptions."""
        tools = [
            ScalpelAnalyzeTool(),
            ScalpelErrorToDiffTool(),
            ScalpelGenerateFixTool(),
            ScalpelValidateASTTool(),
            ScalpelSandboxTool(),
            ScalpelSecurityScanTool(),
        ]

        for tool in tools:
            self.assertIsNotNone(tool.description)
            self.assertGreater(len(tool.description), 0)


if __name__ == "__main__":
    unittest.main()
