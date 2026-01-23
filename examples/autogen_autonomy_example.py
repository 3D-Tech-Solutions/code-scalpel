"""
Example demonstrating AutoGen autonomy integration with Code Scalpel.

[20251217_FEATURE] AutoGen AssistantAgent example for function-calling fixes.

This example shows how to use the Code Scalpel AutoGen integration
to create agents that use function calling to analyze, fix, and validate code.
"""

import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

try:
    from code_scalpel.autonomy.integrations.autogen import (
        create_scalpel_autogen_agents,
        scalpel_analyze_error_impl,
        scalpel_apply_fix_impl,
        scalpel_validate_impl,
    )

    print("=== AutoGen Autonomy Integration Demo ===\n")

    # Example 1: Test the function implementations directly
    print("=== Example 1: Direct Function Calls ===")

    buggy_code = """
def calculate(x, y)
    return x + y
"""

    # Analyze error
    print("1. Analyzing error...")
    analysis = scalpel_analyze_error_impl(buggy_code, "SyntaxError: invalid syntax")
    print(f"   Analysis: {analysis}")

    # Apply fix (in real scenario, would apply actual fix)
    print("\n2. Applying fix...")
    fixed = scalpel_apply_fix_impl(buggy_code, "Add colon after function definition")
    print(f"   Fix result: {fixed.get('success')}")

    # Validate
    print("\n3. Validating fix...")
    valid_code = """
def calculate(x, y):
    return x + y
"""
    validation = scalpel_validate_impl(valid_code)
    print(f"   Validation: {validation}")

    # Example 2: Create agents (requires LLM config)
    print("\n=== Example 2: Agent Creation ===")

    try:
        # Create agents with minimal config
        # Note: This requires proper LLM configuration to actually run
        coder, reviewer = create_scalpel_autogen_agents(
            llm_config={
                "functions": [],  # Will be populated by function
                "config_list": [
                    {
                        "model": "gpt-4",
                        # API key would go here for actual usage
                    }
                ],
            }
        )

        print("Created agents:")
        print(f"  - Coder: {coder.name}")
        print(f"  - Reviewer: {reviewer.name}")

        print("\nAgent capabilities:")
        print("  Coder system message preview:")
        print(f"    {coder.system_message[:100]}...")

        print("\n  Reviewer config:")
        print(f"    Work dir: {reviewer.code_execution_config.get('work_dir')}")
        print(f"    Use Docker: {reviewer.code_execution_config.get('use_docker')}")

        print("\n  Available functions:")
        print("    - scalpel_analyze_error")
        print("    - scalpel_apply_fix")
        print("    - scalpel_validate")

    except Exception as e:
        print(f"Agent creation demo (requires LLM config): {e}")

    # Example 3: Workflow demonstration
    print("\n=== Example 3: Workflow Overview ===")
    print("AutoGen workflow with Code Scalpel:")
    print("  1. User/Reviewer initiates chat with Coder agent")
    print("  2. Coder calls scalpel_analyze_error to understand the issue")
    print("  3. Coder calls scalpel_apply_fix to generate a fix")
    print("  4. Coder calls scalpel_validate to verify fix is safe")
    print("  5. If validation passes, fix is returned")
    print("  6. If validation fails, Coder tries alternative fix")

    # Example 4: Security vulnerability example
    print("\n=== Example 4: Security Vulnerability Detection ===")

    vulnerable_code = """
import subprocess

def run_command(user_input):
    subprocess.run(user_input, shell=True)
"""

    print("Code to analyze:")
    print(vulnerable_code)

    validation = scalpel_validate_impl(vulnerable_code)
    print("\nValidation result:")
    print(f"  Safe to apply: {validation.get('safe_to_apply')}")
    print(f"  Vulnerabilities found: {validation.get('vulnerabilities', 0)}")

    print("\n=== AutoGen Integration Demo Complete ===")
    print("The agents use function calling to work with Code Scalpel tools")
    print("Docker sandbox execution provides isolation for testing code changes")

except ImportError as e:
    print(f"Error: {e}")
    print("\nTo use AutoGen autonomy integration, install required dependencies:")
    print("  pip install pyautogen")
    print("\nOr install all Code Scalpel dependencies:")
    print("  pip install -r requirements.txt")
