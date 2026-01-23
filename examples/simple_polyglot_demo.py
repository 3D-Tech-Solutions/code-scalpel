#!/usr/bin/env python3
"""
Simple Polyglot Demo - Direct usage without package installation.

[20251221_FEATURE] Quick demonstration of multi-language support.
[20260114_BUGFIX] Updated to use current PolyglotExtractor API.

Run from code-scalpel root: python examples/simple_polyglot_demo.py
"""

import sys
from pathlib import Path

# Add src to path for direct import
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def demo_java():
    """Show Java method extraction."""
    from code_scalpel.code_parsers.extractor import Language, PolyglotExtractor

    print("\n" + "=" * 60)
    print(" JAVA EXTRACTION ".center(60, "="))
    print("=" * 60)

    java_code = """
public class Calculator {
    public double add(double a, double b) {
        return a + b;
    }

    public double multiply(double a, double b) {
        return a * b;
    }
}
"""

    extractor = PolyglotExtractor(java_code, language=Language.JAVA)

    print(f"Language: {extractor.language}")

    result = extractor.extract("method", "add")
    print("\nExtracted method 'add':")
    print(f"  Success: {result.success}")
    if result.success:
        print(f"  Lines: {result.start_line}-{result.end_line}")
        print(f"\nCode:\n{result.code}")
    else:
        print(f"  Error: {result.error}")


def demo_javascript():
    """Show JavaScript function extraction."""
    from code_scalpel.code_parsers.extractor import Language, PolyglotExtractor

    print("\n" + "=" * 60)
    print(" JAVASCRIPT EXTRACTION ".center(60, "="))
    print("=" * 60)

    js_code = """
function calculateTax(amount) {
    return amount * 0.1;
}

async function processPayment(amount) {
    const tax = calculateTax(amount);
    return amount + tax;
}

const formatCurrency = (value) => {
    return `$${value.toFixed(2)}`;
};
"""

    extractor = PolyglotExtractor(js_code, language=Language.JAVASCRIPT)

    print(f"Language: {extractor.language}")

    result = extractor.extract("function", "processPayment")
    print("\nExtracted async function 'processPayment':")
    print(f"  Success: {result.success}")
    if result.success:
        print(f"  Lines: {result.start_line}-{result.end_line}")
        print(f"\nCode:\n{result.code}")
    else:
        print(f"  Error: {result.error}")


def demo_typescript():
    """Show TypeScript function extraction."""
    from code_scalpel.code_parsers.extractor import Language, PolyglotExtractor

    print("\n" + "=" * 60)
    print(" TYPESCRIPT EXTRACTION ".center(60, "="))
    print("=" * 60)

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

    print(f"Language: {extractor.language}")

    result = extractor.extract("function", "greet")
    print("\nExtracted function 'greet':")
    print(f"  Success: {result.success}")
    if result.success:
        print(f"  Lines: {result.start_line}-{result.end_line}")
        print(f"\nCode:\n{result.code}")
    else:
        print(f"  Error: {result.error}")


def demo_auto_detection():
    """Show automatic language detection."""
    from code_scalpel.code_parsers.extractor import Language, PolyglotExtractor

    print("\n" + "=" * 60)
    print(" AUTO-DETECTION ".center(60, "="))
    print("=" * 60)

    test_cases = [
        ("function test() { return 1; }", "javascript"),
        ("public class Test { }", "java"),
        ("def test(): pass", "python"),
        ("const add = (a: number): number => a", "typescript"),
    ]

    for code, expected_lang in test_cases:
        extractor = PolyglotExtractor(code, language=Language.AUTO)
        detected = extractor.language.value
        status = "✓" if expected_lang.lower() == detected.lower() else "?"
        print(f"{status} Detected {detected:12s} for: {code[:35]}")


def main():
    """Run all demos."""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " POLYGLOT EXTRACTION DEMO ".center(58) + "║")
    print("║" + " Java • JavaScript • TypeScript ".center(58) + "║")
    print("╚" + "=" * 58 + "╝")

    try:
        demo_java()
        demo_javascript()
        demo_typescript()
        demo_auto_detection()

        print("\n" + "=" * 60)
        print(" ✓ ALL DEMOS COMPLETED SUCCESSFULLY ".center(60))
        print("=" * 60)
        print("\nKey Features:")
        print("  • Unified API for all languages")
        print("  • Auto-detection from code or file extension")
        print("  • Surgical extraction with line numbers")
        print("  • Same interface as Python extractor")
        print()

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
