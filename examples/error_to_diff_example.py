"""
Example usage of Error-to-Diff Engine (v3.0.0 Autonomy).

This demonstrates how AI agents can convert compiler errors, linter warnings,
and test failures into actionable code diffs.

[20251217_FEATURE] v3.0.0 Autonomy - Error-to-Diff Engine example
"""

from code_scalpel.autonomy import ErrorToDiffEngine


def example_python_syntax_error():
    """Example: Fix Python syntax error (missing colon)."""
    print("=" * 80)
    print("Example 1: Python Syntax Error (Missing Colon)")
    print("=" * 80)

    engine = ErrorToDiffEngine(project_root=".")

    # Simulate a syntax error from Python compiler
    error_output = """  File "script.py", line 1
    def calculate_total()
                        ^
SyntaxError: expected ':' after function definition"""

    source_code = """def calculate_total()
    return sum([1, 2, 3])"""

    analysis = engine.analyze_error(error_output, "python", source_code)

    print(f"\nError Type: {analysis.error_type.value}")
    print(f"File: {analysis.file_path}, Line: {analysis.line}")
    print(f"Requires Human Review: {analysis.requires_human_review}")
    print(f"\nNumber of Fixes: {len(analysis.fixes)}")

    for i, fix in enumerate(analysis.fixes, 1):
        print(f"\nFix #{i}:")
        print(f"  Confidence: {fix.confidence:.2f}")
        print(f"  Explanation: {fix.explanation}")
        print(f"  Diff: {fix.diff}")
        print(f"  AST Valid: {fix.ast_valid}")


def example_python_name_error():
    """Example: Fix Python NameError (typo correction)."""
    print("\n" + "=" * 80)
    print("Example 2: Python NameError (Typo Correction)")
    print("=" * 80)

    engine = ErrorToDiffEngine(project_root=".")

    error_output = """NameError: name 'calcualte_total' is not defined"""

    source_code = """def calculate_total(items):
    return sum(items)

result = calcualte_total([1, 2, 3])"""

    analysis = engine.analyze_error(error_output, "python", source_code)

    print(f"\nError Type: {analysis.error_type.value}")
    print(f"Requires Human Review: {analysis.requires_human_review}")
    print(f"\nNumber of Fixes: {len(analysis.fixes)}")

    for i, fix in enumerate(analysis.fixes, 1):
        print(f"\nFix #{i}:")
        print(f"  Confidence: {fix.confidence:.2f}")
        print(f"  Explanation: {fix.explanation}")
        print(f"  Diff: {fix.diff}")


def example_test_failure():
    """Example: Fix test assertion failure."""
    print("\n" + "=" * 80)
    print("Example 3: Test Assertion Failure")
    print("=" * 80)

    engine = ErrorToDiffEngine(project_root=".")

    error_output = """AssertionError: assert 42 == 41"""

    source_code = """def test_calculate_tax():
    assert calculate_tax(100) == 41"""

    analysis = engine.analyze_error(error_output, "python", source_code)

    print(f"\nError Type: {analysis.error_type.value}")
    print(f"Requires Human Review: {analysis.requires_human_review}")
    print(f"\nNumber of Fixes: {len(analysis.fixes)}")

    for i, fix in enumerate(analysis.fixes, 1):
        print(f"\nFix #{i}:")
        print(f"  Confidence: {fix.confidence:.2f}")
        print(f"  Explanation: {fix.explanation}")
        print(f"  Diff: {fix.diff}")


def example_typescript_error():
    """Example: Fix TypeScript type error."""
    print("\n" + "=" * 80)
    print("Example 4: TypeScript Type Error")
    print("=" * 80)

    engine = ErrorToDiffEngine(project_root=".")

    error_output = """user.ts(10,5): error TS2741: Property 'email' is missing in type '{ name: string }'"""

    source_code = """interface User {
    name: string;
    email: string;
}

const user: User = { name: 'John' };"""

    analysis = engine.analyze_error(error_output, "typescript", source_code)

    print(f"\nError Type: {analysis.error_type.value}")
    print(f"File: {analysis.file_path}, Line: {analysis.line}, Column: {analysis.column}")
    print(f"Requires Human Review: {analysis.requires_human_review}")
    print(f"\nNumber of Fixes: {len(analysis.fixes)}")

    for i, fix in enumerate(analysis.fixes, 1):
        print(f"\nFix #{i}:")
        print(f"  Confidence: {fix.confidence:.2f}")
        print(f"  Explanation: {fix.explanation}")
        print(f"  Diff: {fix.diff}")


def example_indentation_error():
    """Example: Fix Python indentation error."""
    print("\n" + "=" * 80)
    print("Example 5: Python Indentation Error")
    print("=" * 80)

    engine = ErrorToDiffEngine(project_root=".")

    error_output = """  File "script.py", line 3
    pass
    ^
IndentationError: unexpected indent"""

    source_code = """def foo():
    if True:
    pass"""

    analysis = engine.analyze_error(error_output, "python", source_code)

    print(f"\nError Type: {analysis.error_type.value}")
    print(f"File: {analysis.file_path}, Line: {analysis.line}")
    print(f"Requires Human Review: {analysis.requires_human_review}")
    print(f"\nNumber of Fixes: {len(analysis.fixes)}")

    for i, fix in enumerate(analysis.fixes, 1):
        print(f"\nFix #{i}:")
        print(f"  Confidence: {fix.confidence:.2f}")
        print(f"  Explanation: {fix.explanation}")
        print(f"  Diff: {fix.diff}")
        print(f"  AST Valid: {fix.ast_valid}")


def example_java_error():
    """Example: Fix Java compiler error."""
    print("\n" + "=" * 80)
    print("Example 6: Java Compiler Error")
    print("=" * 80)

    engine = ErrorToDiffEngine(project_root=".")

    error_output = """Main.java:25: error: cannot find symbol
  symbol:   variable logger
  location: class Main"""

    source_code = """public class Main {
    public static void main(String[] args) {
        logger.info("test");
    }
}"""

    analysis = engine.analyze_error(error_output, "java", source_code)

    print(f"\nError Type: {analysis.error_type.value}")
    print(f"File: {analysis.file_path}, Line: {analysis.line}")
    print(f"Requires Human Review: {analysis.requires_human_review}")
    print(f"\nNumber of Fixes: {len(analysis.fixes)}")

    for i, fix in enumerate(analysis.fixes, 1):
        print(f"\nFix #{i}:")
        print(f"  Confidence: {fix.confidence:.2f}")
        print(f"  Explanation: {fix.explanation}")
        print(f"  Diff: {fix.diff}")


def main():
    """Run all examples."""
    print("\n" + "=" * 80)
    print("Error-to-Diff Engine Examples")
    print("Code Scalpel v3.0.0 'Autonomy'")
    print("=" * 80)

    example_python_syntax_error()
    example_python_name_error()
    example_test_failure()
    example_typescript_error()
    example_indentation_error()
    example_java_error()

    print("\n" + "=" * 80)
    print("Examples Complete!")
    print("=" * 80)


if __name__ == "__main__":
    main()
