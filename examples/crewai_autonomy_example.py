"""
Example demonstrating CrewAI autonomy integration with Code Scalpel.

[20251217_FEATURE] CrewAI Crew example for collaborative code fixing.

This example shows how to use the Code Scalpel CrewAI integration
to create a multi-agent crew that collaboratively analyzes, fixes,
and validates code.
"""

import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

try:
    from code_scalpel.autonomy.integrations.crewai import (
        create_scalpel_fix_crew,
    )

    print("=== CrewAI Autonomy Integration Demo ===\n")

    # Try to create the crew (requires LLM configuration)
    try:
        crew = create_scalpel_fix_crew()
        crew_created = True
    except Exception as e:
        crew_created = False
        print("Note: Crew creation requires LLM configuration (e.g., OPENAI_API_KEY)")
        print(f"Error: {e}\n")

    if crew_created:
        print("Crew created with agents:")
        for agent in crew.agents:
            print(f"  - {agent.role}: {agent.goal}")

        print("\nTasks:")
        for i, task in enumerate(crew.tasks):
            print(f"  {i+1}. {task.description}")
    else:
        print("Crew structure (would be created with proper configuration):")
        print("  - Error Analyzer: Analyze code errors and identify root causes")
        print("  - Fix Generator: Generate correct code fixes based on error analysis")
        print("  - Fix Validator: Validate fixes don't break existing functionality")

    # Example 1: Simple syntax error
    print("\n=== Example 1: Syntax Error ===")
    buggy_code = """
def greet(name)
    print(f"Hello {name}")
"""

    # Note: Running the crew requires LLM configuration (OpenAI API key, etc.)
    # This is a demonstration of the structure
    print(f"Code to fix:\n{buggy_code}")
    print("\nTo run this crew, you need to configure an LLM (OpenAI, Anthropic, etc.)")
    print("Set environment variables like OPENAI_API_KEY")

    # Example 2: Security vulnerability
    print("\n=== Example 2: Security Vulnerability ===")
    vulnerable_code = """
def run_query(user_input):
    query = f"SELECT * FROM users WHERE name = '{user_input}'"
    cursor.execute(query)
"""

    print(f"Code to fix:\n{vulnerable_code}")
    print("\nThe crew would:")
    print("  1. Error Analyzer: Identify SQL injection vulnerability (CWE-89)")
    print("  2. Fix Generator: Generate parameterized query using ? placeholders")
    print("  3. Fix Validator: Validate fix is secure and functionally correct")

    # Example 3: Demonstrating the tools
    print("\n=== Available Tools ===")
    print("Each agent has access to specialized Code Scalpel tools:")
    print("\nError Analyzer:")
    print("  - scalpel_analyze: AST-based code analysis")
    print("  - scalpel_error_to_diff: Convert errors to actionable diffs")
    print("\nFix Generator:")
    print("  - scalpel_generate_fix: Generate code fixes")
    print("  - scalpel_validate_ast: Validate AST structure")
    print("\nFix Validator:")
    print("  - scalpel_sandbox: Test code in sandbox")
    print("  - scalpel_security_scan: Scan for vulnerabilities")

    print("\n=== CrewAI Integration Demo Complete ===")
    print("The crew provides multi-agent collaboration for code fixing")

except ImportError as e:
    print(f"Error: {e}")
    print("\nTo use CrewAI autonomy integration, install required dependencies:")
    print("  pip install crewai")
    print("\nOr install all Code Scalpel dependencies:")
    print("  pip install -r requirements.txt")
