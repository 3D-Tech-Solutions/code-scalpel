#!/usr/bin/env python3
"""
Practical Polyglot Usage Example - Using the built-in polyglot module.

[20251221_DOCS] Shows how to use Code Scalpel's existing multi-language support.

Code Scalpel already supports:
- Python (via AST)
- JavaScript (via tree-sitter)
- TypeScript (via tree-sitter)
- Java (via tree-sitter)

This example demonstrates the proper API usage.
"""

import sys
from pathlib import Path

# Add src to path for direct import
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def example_1_extract_java():
    """Extract Java method - shows the proper API."""
    from code_scalpel.polyglot import Language, PolyglotExtractor

    print("\n" + "=" * 70)
    print(" EXAMPLE 1: Extract Java Method ".center(70, "="))
    print("=" * 70)

    java_code = """
public class Calculator {
    /**
     * Add two numbers.
     */
    public double add(double a, double b) {
        return a + b;
    }

    public double multiply(double a, double b) {
        return a * b;
    }
}
"""

    # Create extractor with explicit language
    extractor = PolyglotExtractor(java_code, language=Language.JAVA)

    # Extract a method - NOTE: Use "method" with "ClassName.methodName" format
    result = extractor.extract("method", "Calculator.add")

    print(f"✓ Language: {result.language}")
    print(f"✓ Success: {result.success}")
    print(f"✓ Target: {result.target_name} ({result.target_type})")
    print(f"✓ Lines: {result.start_line}-{result.end_line}")
    print("\n✓ Extracted Code:")
    print(result.code)

    # Also extract the class
    class_result = extractor.extract("class", "Calculator")
    print("\n✓ Can also extract whole class:")
    print(f"  Success: {class_result.success}")
    print(f"  Lines: {class_result.start_line}-{class_result.end_line}")


def example_2_extract_javascript():
    """Extract JavaScript function - async and arrow functions."""
    from code_scalpel.polyglot import Language, PolyglotExtractor

    print("\n" + "=" * 70)
    print(" EXAMPLE 2: Extract JavaScript Functions ".center(70, "="))
    print("=" * 70)

    js_code = """
// Regular function
function calculateTax(amount) {
    return amount * 0.1;
}

// Async function
async function processPayment(amount) {
    const tax = calculateTax(amount);
    return amount + tax;
}

// Arrow function  
const formatCurrency = (value) => `$${value.toFixed(2)}`;
"""

    extractor = PolyglotExtractor(js_code, language=Language.JAVASCRIPT)

    # Extract async function
    result = extractor.extract("function", "processPayment")
    print("✓ Extracted async function 'processPayment':")
    print(f"  Success: {result.success}, Lines: {result.start_line}-{result.end_line}")
    print(f"\n{result.code}\n")


def example_3_extract_typescript():
    """Extract TypeScript function with types."""
    from code_scalpel.polyglot import Language, PolyglotExtractor

    print("\n" + "=" * 70)
    print(" EXAMPLE 3: Extract TypeScript with Types ".center(70, "="))
    print("=" * 70)

    ts_code = """
interface User {
    id: number;
    name: string;
}

function greet(user: User): string {
    return `Hello, ${user.name}!`;
}

class UserService {
    getUser(id: number): User {
        return { id, name: "Test" };
    }
}
"""

    extractor = PolyglotExtractor(ts_code, language=Language.TYPESCRIPT)

    # Extract typed function
    result = extractor.extract("function", "greet")
    print("✓ Extracted TypeScript function with types:")
    print(f"  Target: {result.target_name}, Type: {result.target_type}")
    print(f"\n{result.code}\n")

    # Extract class
    result_class = extractor.extract("class", "UserService")
    print("✓ Extracted TypeScript class:")
    print(f"  Target: {result_class.target_name}")
    print(f"  Lines: {result_class.start_line}-{result_class.end_line}")


def example_4_auto_detect():
    """Demonstrate automatic language detection."""
    from code_scalpel.polyglot import Language, detect_language

    print("\n" + "=" * 70)
    print(" EXAMPLE 4: Automatic Language Detection ".center(70, "="))
    print("=" * 70)

    # Detect from file extension
    test_cases = [
        ("app.py", None, Language.PYTHON),
        ("service.java", None, Language.JAVA),
        ("utils.js", None, Language.JAVASCRIPT),
        ("component.ts", None, Language.TYPESCRIPT),
        ("button.tsx", None, Language.TYPESCRIPT),
    ]

    print("✓ Detection from file extension:")
    for filename, code, expected in test_cases:
        detected = detect_language(filename, code)
        status = "✓" if detected == expected else "✗"
        print(f"  {status} {filename:20s} → {detected.value}")

    # Detect from content
    print("\n✓ Detection from code content:")
    content_tests = [
        ("public class Test {}", Language.JAVA),
        ("def hello(): pass", Language.PYTHON),
        ("function test() {}", Language.JAVASCRIPT),
        ("const add = (a: number) => a", Language.TYPESCRIPT),
    ]

    for code, expected in content_tests:
        detected = detect_language(None, code)
        status = "✓" if detected == expected else "✗"
        print(f"  {status} {code[:30]:32s} → {detected.value}")


def example_5_extract_from_file():
    """Convenience function for code extraction."""
    from code_scalpel.polyglot import extract_from_code

    print("\n" + "=" * 70)
    print(" EXAMPLE 5: Convenience Functions ".center(70, "="))
    print("=" * 70)

    java_code = """
public class Math {
    public int add(int a, int b) { return a + b; }
}
"""

    # One-liner extraction - NOTE: Use "method" for Java
    result = extract_from_code(java_code, "method", "Math.add")

    print("✓ One-liner extraction: extract_from_code()")
    print(f"  Language: {result.language}")
    print(f"  Success: {result.success}")
    print(f"  Target: {result.target_name}")
    print(f"\nCode:\n{result.code}")


def example_6_error_handling():
    """Demonstrate error handling."""
    from code_scalpel.polyglot import Language, PolyglotExtractor

    print("\n" + "=" * 70)
    print(" EXAMPLE 6: Error Handling ".center(70, "="))
    print("=" * 70)

    java_code = """
public class Calculator {
    public double add(double a, double b) { return a + b; }
}
"""

    extractor = PolyglotExtractor(java_code, language=Language.JAVA)

    # Try to extract non-existent method
    result = extractor.extract("method", "Calculator.multiply")

    print("✓ Attempted to extract non-existent method:")
    print(f"  Success: {result.success}")
    print(f"  Error: {result.error}")

    # Extract existing method
    result = extractor.extract("method", "Calculator.add")
    print("\n✓ Extracted existing method:")
    print(f"  Success: {result.success}")
    print(f"  Target: {result.target_name}")


def main():
    """Run all examples."""
    print("\n")
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 68 + "║")
    print("║" + " POLYGLOT USAGE GUIDE - Multi-Language Support ".center(68) + "║")
    print("║" + " Code Scalpel v3.1.0 ".center(68) + "║")
    print("║" + " " * 68 + "║")
    print("╚" + "=" * 68 + "╝")

    try:
        example_1_extract_java()
        example_2_extract_javascript()
        example_3_extract_typescript()
        example_4_auto_detect()
        example_5_extract_from_file()
        example_6_error_handling()

        print("\n" + "=" * 70)
        print(" ✓ ALL EXAMPLES COMPLETED ".center(70))
        print("=" * 70)
        print("\nPolyglot API Summary:")
        print("  • PolyglotExtractor(code, language=Language.JAVA)")
        print("  • extractor.extract('function', 'methodName')")
        print("  • extractor.extract('class', 'ClassName')")
        print("  • detect_language(filename, code)")
        print("  • extract_from_code(code, 'function', 'name')")
        print("\nSupported Languages:")
        print("  • Language.PYTHON")
        print("  • Language.JAVA")
        print("  • Language.JAVASCRIPT")
        print("  • Language.TYPESCRIPT")
        print("\nDocs: docs/parsers/DOCUMENTATION_INDEX.md")
        print()

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
