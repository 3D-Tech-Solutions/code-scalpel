"""
Polyglot Surgical Extractor Demo - Multi-Language Support.

[20251221_FEATURE] Demonstrates extraction across Python, JavaScript, TypeScript, and Java.

This example shows how the PolyglotExtractor provides a unified interface
for extracting code elements from multiple programming languages.
"""

from code_scalpel.polyglot_extractor import PolyglotExtractor, extract_from_file


def demo_javascript_extraction():
    """Demo: Extract JavaScript functions and classes."""
    print("\n" + "=" * 70)
    print("DEMO 1: JavaScript Extraction")
    print("=" * 70)

    js_code = """
function calculateTax(amount, rate) {
    return amount * rate;
}

const formatCurrency = (value) => {
    return `$${value.toFixed(2)}`;
};

class PaymentProcessor {
    constructor(provider) {
        this.provider = provider;
        this.transactions = [];
    }

    async processPayment(amount) {
        const tax = calculateTax(amount, 0.1);
        const total = amount + tax;
        
        this.transactions.push({
            amount: total,
            timestamp: Date.now()
        });
        
        return formatCurrency(total);
    }

    getTotal() {
        return this.transactions.reduce((sum, t) => sum + t.amount, 0);
    }
}
"""

    extractor = PolyglotExtractor(js_code, language="javascript")

    # Extract function
    print("\n1. Extracting calculateTax function:")
    result = extractor.get_function("calculateTax")
    print(f"   ✓ Success: {result.success}")
    print(f"   ✓ Lines: {result.line_start}-{result.line_end}")
    print(f"   ✓ Code:\n{result.code}")

    # Extract arrow function
    print("\n2. Extracting formatCurrency arrow function:")
    result = extractor.get_function("formatCurrency")
    print(f"   ✓ Success: {result.success}")
    print(f"   ✓ Code preview: {result.code[:50]}...")

    # Extract class
    print("\n3. Extracting PaymentProcessor class:")
    result = extractor.get_class("PaymentProcessor")
    print(f"   ✓ Success: {result.success}")
    print(f"   ✓ Lines: {result.line_start}-{result.line_end}")
    print(f"   ✓ Contains async method: {'async processPayment' in result.code}")

    # List all
    print("\n4. Listing all elements:")
    print(f"   Functions: {extractor.list_functions()}")
    print(f"   Classes: {extractor.list_classes()}")


def demo_typescript_extraction():
    """Demo: Extract TypeScript with type annotations."""
    print("\n" + "=" * 70)
    print("DEMO 2: TypeScript Extraction")
    print("=" * 70)

    ts_code = """
interface User {
    id: number;
    name: string;
    email: string;
}

type PaymentStatus = 'pending' | 'completed' | 'failed';

function validateUser(user: User): boolean {
    return user.email.includes('@') && user.name.length > 0;
}

class UserService {
    private users: Map<number, User>;

    constructor() {
        this.users = new Map();
    }

    addUser(user: User): void {
        if (!validateUser(user)) {
            throw new Error('Invalid user');
        }
        this.users.set(user.id, user);
    }

    getUser(id: number): User | undefined {
        return this.users.get(id);
    }
}

async function fetchUser(id: number): Promise<User> {
    const response = await fetch(`/api/users/${id}`);
    return response.json();
}
"""

    extractor = PolyglotExtractor(ts_code, language="typescript")

    # Extract typed function
    print("\n1. Extracting validateUser function (with type annotations):")
    result = extractor.get_function("validateUser")
    print(f"   ✓ Success: {result.success}")
    print(
        f"   ✓ Has type annotations: {'User' in result.code and 'boolean' in result.code}"
    )
    print(f"   ✓ Code:\n{result.code}")

    # Extract generic class
    print("\n2. Extracting UserService class:")
    result = extractor.get_class("UserService")
    print(f"   ✓ Success: {result.success}")
    print(f"   ✓ Has private fields: {'private' in result.code}")
    print(f"   ✓ Lines: {result.line_start}-{result.line_end}")

    # Extract async function
    print("\n3. Extracting async function with Promise return type:")
    result = extractor.get_function("fetchUser")
    print(f"   ✓ Success: {result.success}")
    print(f"   ✓ Has async/await: {'async' in result.code and 'await' in result.code}")


def demo_java_extraction():
    """Demo: Extract Java methods and classes."""
    print("\n" + "=" * 70)
    print("DEMO 3: Java Extraction")
    print("=" * 70)

    java_code = """
import java.util.ArrayList;
import java.util.List;

public class PaymentProcessor {
    private double balance;
    private List<Transaction> transactions;

    public PaymentProcessor() {
        this.balance = 0.0;
        this.transactions = new ArrayList<>();
    }

    public double calculateTax(double amount, double rate) {
        return amount * rate;
    }

    public void processPayment(double amount) throws PaymentException {
        if (amount <= 0) {
            throw new PaymentException("Invalid amount");
        }

        double tax = calculateTax(amount, 0.1);
        double total = amount + tax;

        this.balance += total;
        this.transactions.add(new Transaction(total));
    }

    public double getBalance() {
        return this.balance;
    }

    private void validateTransaction(Transaction transaction) {
        if (transaction == null) {
            throw new IllegalArgumentException("Null transaction");
        }
    }
}
"""

    extractor = PolyglotExtractor(java_code, language="java")

    # Extract public method
    print("\n1. Extracting calculateTax method:")
    result = extractor.get_function("calculateTax")
    print(f"   ✓ Success: {result.success}")
    print(f"   ✓ Type: {result.node_type}")
    print(f"   ✓ Code:\n{result.code}")

    # Extract method with exceptions
    print("\n2. Extracting processPayment method (with exception handling):")
    result = extractor.get_function("processPayment")
    print(f"   ✓ Success: {result.success}")
    print(f"   ✓ Has exception: {'throws' in result.code}")
    print(f"   ✓ Lines: {result.line_start}-{result.line_end}")

    # Extract class
    print("\n3. Extracting PaymentProcessor class:")
    result = extractor.get_class("PaymentProcessor")
    print(f"   ✓ Success: {result.success}")
    print(f"   ✓ Has constructor: {'public PaymentProcessor()' in result.code}")
    print(f"   ✓ Total lines: {result.line_end - result.line_start + 1}")

    # List methods
    print("\n4. Listing all methods:")
    methods = extractor.list_functions()
    print(f"   Methods found: {methods}")


def demo_auto_detection():
    """Demo: Automatic language detection."""
    print("\n" + "=" * 70)
    print("DEMO 4: Automatic Language Detection")
    print("=" * 70)

    samples = [
        ("Python", "def calculate_tax(amount, rate):\n    return amount * rate"),
        (
            "JavaScript",
            "function calculateTax(amount, rate) {\n    return amount * rate;\n}",
        ),
        (
            "TypeScript",
            "function calculateTax(amount: number, rate: number): number {\n    return amount * rate;\n}",
        ),
        (
            "Java",
            "public class Calculator {\n    public double calculateTax(double amount, double rate) {\n        return amount * rate;\n    }\n}",
        ),
    ]

    for expected_lang, code in samples:
        extractor = PolyglotExtractor(code)
        detected = extractor.language
        print(
            f"\n{expected_lang:12} → Detected as: {detected:12} {'✓' if detected.lower() == expected_lang.lower() else '✗'}"
        )
        print(f"   Code preview: {code[:60]}...")


def demo_token_counting():
    """Demo: Token counting across languages."""
    print("\n" + "=" * 70)
    print("DEMO 5: Token Counting Across Languages")
    print("=" * 70)

    codes = {
        "Python": "def calculate_tax(amount, rate):\n    return amount * rate",
        "JavaScript": "function calculateTax(amount, rate) { return amount * rate; }",
        "TypeScript": "function calculateTax(amount: number, rate: number): number { return amount * rate; }",
        "Java": "public double calculateTax(double amount, double rate) { return amount * rate; }",
    }

    print("\nComparing token counts for equivalent 'calculateTax' implementations:\n")

    for lang, code in codes.items():
        extractor = PolyglotExtractor(code)

        if lang == "Python":
            result = extractor.get_function("calculate_tax")
        elif lang == "Java":
            result = extractor.get_function("calculateTax")
        else:
            result = extractor.get_function("calculateTax")

        if result.success:
            token_count = result.get_token_count("gpt-4")
            print(f"{lang:12} {token_count:3} tokens │ {result.code[:50]}...")


def demo_file_extraction(tmp_path):
    """Demo: Extracting from actual files."""
    print("\n" + "=" * 70)
    print("DEMO 6: File-Based Extraction")
    print("=" * 70)

    # Create sample files
    files = {
        "utils.js": """
function formatCurrency(value) {
    return `$${value.toFixed(2)}`;
}

function calculateTax(amount, rate = 0.1) {
    return amount * rate;
}
""",
        "Calculator.java": """
public class Calculator {
    public int add(int a, int b) {
        return a + b;
    }

    public int multiply(int a, int b) {
        return a * b;
    }
}
""",
        "service.ts": """
async function fetchData(): Promise<any> {
    const response = await fetch('/api/data');
    return response.json();
}
""",
    }

    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        for filename, content in files.items():
            file_path = tmpdir_path / filename
            file_path.write_text(content)

        print("\nCreated temporary files:")
        for filename in files.keys():
            print(f"   - {filename}")

        # Extract from JavaScript file
        print("\n1. Extracting from utils.js:")
        js_path = tmpdir_path / "utils.js"
        result = extract_from_file(str(js_path), "formatCurrency")
        print(f"   ✓ Function: {result.name}")
        print(f"   ✓ Success: {result.success}")

        # Extract from Java file
        print("\n2. Extracting from Calculator.java:")
        java_path = tmpdir_path / "Calculator.java"
        result = extract_from_file(str(java_path), "Calculator", "class")
        print(f"   ✓ Class: {result.name}")
        print(f"   ✓ Success: {result.success}")

        # Extract from TypeScript file
        print("\n3. Extracting from service.ts:")
        ts_path = tmpdir_path / "service.ts"
        result = extract_from_file(str(ts_path), "fetchData")
        print(f"   ✓ Function: {result.name}")
        print(f"   ✓ Has async: {'async' in result.code}")


def demo_error_handling():
    """Demo: Error handling and edge cases."""
    print("\n" + "=" * 70)
    print("DEMO 7: Error Handling")
    print("=" * 70)

    js_code = """
function foo() {
    return 42;
}

class Bar {
    constructor() {}
}
"""

    extractor = PolyglotExtractor(js_code, language="javascript")

    # Try to extract non-existent function
    print("\n1. Extracting non-existent function:")
    result = extractor.get_function("nonexistent")
    print(f"   ✓ Success: {result.success}")
    print(f"   ✓ Error message: {result.error}")

    # Try to extract non-existent class
    print("\n2. Extracting non-existent class:")
    result = extractor.get_class("MissingClass")
    print(f"   ✓ Success: {result.success}")
    print(f"   ✓ Error includes suggestions: {'Available' in result.error}")

    # Unsupported language
    print("\n3. Attempting unsupported language:")
    try:
        PolyglotExtractor("code", language="rust")
        print("   ✗ Should have raised ValueError")
    except ValueError as e:
        print(f"   ✓ Caught ValueError: {str(e)[:50]}...")


def demo_comparison_with_python():
    """Demo: Compare with Python surgical extractor."""
    print("\n" + "=" * 70)
    print("DEMO 8: Comparison with Python Extractor")
    print("=" * 70)

    python_code = """
def calculate_tax(amount: float, rate: float = 0.1) -> float:
    '''Calculate tax on an amount.'''
    return amount * rate

class TaxCalculator:
    '''Tax calculation service.'''
    
    def __init__(self, default_rate: float = 0.1):
        self.default_rate = default_rate
    
    def calculate(self, amount: float) -> float:
        return calculate_tax(amount, self.default_rate)
"""

    # Using polyglot extractor
    print("\n1. Using PolyglotExtractor (delegates to Python extractor):")
    polyglot = PolyglotExtractor(python_code, language="python")
    result = polyglot.get_function("calculate_tax")
    print(f"   ✓ Success: {result.success}")
    print(f"   ✓ Detected language: {polyglot.language}")
    print(f"   ✓ Has docstring: {result.docstring is not None}")
    print(f"   ✓ Has signature: {result.signature is not None}")

    # Direct comparison
    print("\n2. Feature parity with SurgicalExtractor:")
    print(f"   ✓ Metadata extraction: {result.docstring is not None}")
    print(f"   ✓ Line tracking: Lines {result.line_start}-{result.line_end}")
    print(f"   ✓ Token counting: {result.get_token_count('gpt-4')} tokens")


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("POLYGLOT SURGICAL EXTRACTOR - MULTI-LANGUAGE DEMO")
    print("=" * 70)
    print("\nDemonstrating surgical code extraction across:")
    print("  • Python")
    print("  • JavaScript")
    print("  • TypeScript")
    print("  • Java")

    demo_javascript_extraction()
    demo_typescript_extraction()
    demo_java_extraction()
    demo_auto_detection()
    demo_token_counting()

    import tempfile

    demo_file_extraction(tempfile.mkdtemp())

    demo_error_handling()
    demo_comparison_with_python()

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print("\nPolyglotExtractor provides:")
    print("  ✓ Unified API across 4 languages")
    print("  ✓ Automatic language detection")
    print("  ✓ Token-efficient extraction")
    print("  ✓ Robust error handling")
    print("  ✓ File-based and string-based extraction")
    print("  ✓ Compatible with existing SurgicalExtractor features")
    print("\nReady for production use! 🚀")
    print("=" * 70 + "\n")
