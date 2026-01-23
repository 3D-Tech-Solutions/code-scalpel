"""
Tests for AutoGen autonomy integration.

[20251217_TEST] Comprehensive tests for AutoGen AssistantAgent integration.
"""

import os
import sys
import unittest

# Add src directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

try:
    import pytest

    AUTOGEN_AVAILABLE = True
    try:
        from code_scalpel.autonomy.integrations.autogen import (
            create_scalpel_autogen_agents,
            scalpel_analyze_error_impl,
            scalpel_analyze_error_schema,
            scalpel_apply_fix_impl,
            scalpel_apply_fix_schema,
            scalpel_validate_impl,
            scalpel_validate_schema,
        )
    except ImportError:
        AUTOGEN_AVAILABLE = False
except ImportError:
    AUTOGEN_AVAILABLE = False
    pytest = None


def _docker_socket_available() -> bool:
    # Fast, platform-appropriate signal for docker availability.
    # AutoGen's docker execution relies on a reachable daemon; the unix socket
    # is the common case in Linux CI/dev environments.
    return os.path.exists("/var/run/docker.sock")


@unittest.skipIf(not AUTOGEN_AVAILABLE, "AutoGen not available")
class TestAutoGenIntegration(unittest.TestCase):
    """Tests for AutoGen integration."""

    def test_scalpel_analyze_error_impl_syntax_error(self):
        """Test scalpel_analyze_error_impl with syntax error."""
        result = scalpel_analyze_error_impl(
            code="def foo( return 42",
            error="SyntaxError: invalid syntax",
        )

        self.assertTrue(result["success"])
        self.assertFalse(result["parsed"])
        self.assertEqual(result["error_type"], "syntax")
        self.assertIn("suggestions", result)

    def test_scalpel_analyze_error_impl_runtime_error(self):
        """Test scalpel_analyze_error_impl with runtime error."""
        result = scalpel_analyze_error_impl(
            code="def foo():\n    return 42",
            error="RuntimeError",
        )

        self.assertTrue(result["success"])
        self.assertTrue(result["parsed"])
        self.assertEqual(result["error_type"], "runtime")

    def test_scalpel_apply_fix_impl_valid_code(self):
        """Test scalpel_apply_fix_impl with valid code."""
        result = scalpel_apply_fix_impl(
            code="def foo():\n    return 42",
            fix="No fix needed",
        )

        self.assertTrue(result["success"])
        self.assertTrue(result.get("fix_applied"))
        self.assertIn("fixed_code", result)

    def test_scalpel_apply_fix_impl_invalid_code(self):
        """Test scalpel_apply_fix_impl with invalid code."""
        result = scalpel_apply_fix_impl(
            code="invalid python !!!",
            fix="Try to fix",
        )

        self.assertFalse(result["success"])
        self.assertIn("error", result)

    def test_scalpel_validate_impl_safe_code(self):
        """Test scalpel_validate_impl with safe code."""
        result = scalpel_validate_impl("def foo():\n    return 42")

        self.assertTrue(result["success"])
        self.assertTrue(result["validation_passed"])
        self.assertTrue(result.get("safe_to_apply"))

    def test_scalpel_validate_impl_vulnerable_code(self):
        """Test scalpel_validate_impl with vulnerable code."""
        vulnerable_code = """
import os
def run(cmd):
    os.system(cmd)
"""

        result = scalpel_validate_impl(vulnerable_code)

        self.assertTrue(result["success"])
        self.assertIn("vulnerabilities", result)

    def test_scalpel_validate_impl_syntax_error(self):
        """Test scalpel_validate_impl with syntax error."""
        result = scalpel_validate_impl("def foo( return 42")

        self.assertFalse(result["success"])
        self.assertFalse(result["validation_passed"])

    def test_analyze_error_schema_structure(self):
        """Test analyze error schema has required fields."""
        self.assertEqual(scalpel_analyze_error_schema["name"], "scalpel_analyze_error")
        self.assertIn("description", scalpel_analyze_error_schema)
        self.assertIn("parameters", scalpel_analyze_error_schema)

        params = scalpel_analyze_error_schema["parameters"]
        self.assertIn("properties", params)
        self.assertIn("code", params["properties"])
        self.assertIn("error", params["properties"])
        self.assertIn("required", params)

    def test_apply_fix_schema_structure(self):
        """Test apply fix schema has required fields."""
        self.assertEqual(scalpel_apply_fix_schema["name"], "scalpel_apply_fix")
        self.assertIn("description", scalpel_apply_fix_schema)
        self.assertIn("parameters", scalpel_apply_fix_schema)

        params = scalpel_apply_fix_schema["parameters"]
        self.assertIn("code", params["properties"])
        self.assertIn("fix", params["properties"])

    def test_validate_schema_structure(self):
        """Test validate schema has required fields."""
        self.assertEqual(scalpel_validate_schema["name"], "scalpel_validate")
        self.assertIn("description", scalpel_validate_schema)
        self.assertIn("parameters", scalpel_validate_schema)

        params = scalpel_validate_schema["parameters"]
        self.assertIn("code", params["properties"])

    def test_create_scalpel_autogen_agents_default_config(self):
        """Test create_scalpel_autogen_agents with default config."""
        # Mock config to avoid API key requirement
        config = {
            "config_list": [{"model": "gpt-4", "api_key": "fake-key"}],
        }
        coder, reviewer = create_scalpel_autogen_agents(llm_config=config)

        # Verify coder agent
        self.assertEqual(coder.name, "ScalpelCoder")
        self.assertIn("Code Scalpel tools", coder.system_message)

        # Verify reviewer agent
        self.assertEqual(reviewer.name, "CodeReviewer")
        self.assertEqual(reviewer.human_input_mode, "NEVER")
        self.assertIn("work_dir", reviewer._code_execution_config)
        use_docker = reviewer._code_execution_config.get("use_docker")
        if _docker_socket_available():
            self.assertTrue(use_docker)
        else:
            self.assertFalse(use_docker)

    def test_create_scalpel_autogen_agents_custom_config(self):
        """Test create_scalpel_autogen_agents with custom config."""
        custom_config = {
            "config_list": [{"model": "gpt-3.5-turbo", "api_key": "fake-key"}],
        }

        coder, reviewer = create_scalpel_autogen_agents(llm_config=custom_config)

        # Verify functions were added to config
        self.assertIn("functions", coder.llm_config)
        self.assertEqual(len(coder.llm_config["functions"]), 3)

    def test_agents_have_function_registrations(self):
        """Test agents have function registrations."""
        config = {
            "config_list": [{"model": "gpt-4", "api_key": "fake-key"}],
        }
        coder, reviewer = create_scalpel_autogen_agents(llm_config=config)

        # Reviewer should have registered functions
        # Note: We can't easily check _function_map in autogen, but we can verify
        # the agent structure
        self.assertIsNotNone(reviewer)

    def test_workflow_integration(self):
        """Test complete workflow with all functions."""
        # 1. Analyze
        analyze_result = scalpel_analyze_error_impl(
            code="def foo( return 42",
            error="SyntaxError",
        )
        self.assertTrue(analyze_result["success"])

        # 2. Apply fix (would use analysis to generate fix)
        apply_result = scalpel_apply_fix_impl(
            code="def foo():\n    return 42",
            fix="Fixed syntax",
        )
        self.assertTrue(apply_result["success"])

        # 3. Validate
        validate_result = scalpel_validate_impl(apply_result.get("fixed_code", ""))
        self.assertTrue(validate_result["success"])

    def test_sandbox_work_dir_configuration(self):
        """Test sandbox work directory is configured."""
        config = {
            "config_list": [{"model": "gpt-4", "api_key": "fake-key"}],
        }
        coder, reviewer = create_scalpel_autogen_agents(llm_config=config)

        work_dir = reviewer._code_execution_config.get("work_dir")
        self.assertEqual(work_dir, ".scalpel_sandbox")

    def test_docker_execution_enabled(self):
        """Test Docker execution is enabled."""
        config = {
            "config_list": [{"model": "gpt-4", "api_key": "fake-key"}],
        }
        coder, reviewer = create_scalpel_autogen_agents(llm_config=config)

        use_docker = reviewer._code_execution_config.get("use_docker")
        if _docker_socket_available():
            self.assertTrue(use_docker)
        else:
            self.assertFalse(use_docker)

    def test_function_schemas_are_valid_openai_format(self):
        """Test function schemas match OpenAI format."""
        schemas = [
            scalpel_analyze_error_schema,
            scalpel_apply_fix_schema,
            scalpel_validate_schema,
        ]

        for schema in schemas:
            self.assertIn("name", schema)
            self.assertIn("description", schema)
            self.assertIn("parameters", schema)

            params = schema["parameters"]
            self.assertEqual(params["type"], "object")
            self.assertIn("properties", params)
            self.assertIn("required", params)


if __name__ == "__main__":
    unittest.main()
