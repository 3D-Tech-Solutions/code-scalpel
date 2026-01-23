"""
Example demonstrating LangGraph integration with Code Scalpel.

[20251217_FEATURE] LangGraph StateGraph example for autonomous code fixing.

This example shows how to use the Code Scalpel LangGraph integration
to create an autonomous fix loop that analyzes, fixes, validates, and
applies code corrections.
"""

import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

try:
    from code_scalpel.autonomy.integrations.langgraph import (
        create_scalpel_fix_graph,
    )

    # Example 1: Fix a syntax error
    print("=== Example 1: Syntax Error Fix ===")
    graph = create_scalpel_fix_graph()

    buggy_code = """
def calculate_sum(a, b)
    return a + b
"""

    result = graph.invoke(
        {
            "code": buggy_code,
            "language": "python",
            "error": "SyntaxError: invalid syntax at line 2",
            "fix_attempts": [],
            "success": False,
        }
    )

    print(f"Fix successful: {result['success']}")
    print(f"Fix attempts: {len(result['fix_attempts'])}")
    for i, attempt in enumerate(result["fix_attempts"]):
        print(f"  Attempt {i+1}: {attempt.get('step')}")

    # Example 2: Runtime error
    print("\n=== Example 2: Runtime Error ===")
    graph = create_scalpel_fix_graph()

    runtime_error_code = """
def divide(a, b):
    return a / b

result = divide(10, 0)
"""

    result = graph.invoke(
        {
            "code": runtime_error_code,
            "language": "python",
            "error": "ZeroDivisionError: division by zero",
            "fix_attempts": [],
            "success": False,
        }
    )

    print(f"Fix successful: {result['success']}")
    print(f"Fix attempts: {len(result['fix_attempts'])}")
    for i, attempt in enumerate(result["fix_attempts"]):
        step = attempt.get("step")
        validation = attempt.get("validation", "N/A")
        print(f"  Attempt {i+1}: {step} (validation: {validation})")

    # Example 3: Security vulnerability
    print("\n=== Example 3: Security Vulnerability ===")
    graph = create_scalpel_fix_graph()

    vulnerable_code = """
import os

def execute_command(user_input):
    os.system(user_input)
"""

    result = graph.invoke(
        {
            "code": vulnerable_code,
            "language": "python",
            "error": "Security: Command injection vulnerability",
            "fix_attempts": [],
            "success": False,
        }
    )

    print(f"Fix successful: {result['success']}")
    print(f"Fix attempts: {len(result['fix_attempts'])}")
    for i, attempt in enumerate(result["fix_attempts"]):
        step = attempt.get("step")
        vulnerabilities = attempt.get("vulnerabilities", "N/A")
        print(f"  Attempt {i+1}: {step} (vulnerabilities: {vulnerabilities})")

    print("\n=== LangGraph Integration Demo Complete ===")
    print("The graph automatically routes through analyze → generate → validate → apply/escalate")

except ImportError as e:
    print(f"Error: {e}")
    print("\nTo use LangGraph integration, install required dependencies:")
    print("  pip install langgraph")
    print("\nOr install all Code Scalpel dependencies:")
    print("  pip install -r requirements.txt")
