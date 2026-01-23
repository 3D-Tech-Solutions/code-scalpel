"""
Example: Using the Unified Security Sink Detector

[20251216_EXAMPLE] Demonstrates polyglot sink detection with confidence scoring.

This example shows how to use the UnifiedSinkDetector to detect security sinks
across multiple programming languages with explicit confidence scoring.
"""

from code_scalpel.security.analyzers import UnifiedSinkDetector


def example_python_detection():
    """Detect sinks in Python code."""
    print("=" * 70)
    print("Example 1: Python SQL Injection Detection")
    print("=" * 70)

    detector = UnifiedSinkDetector()

    code = """
import sqlite3

def get_user(user_id):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    # VULNERABLE: String concatenation in SQL query
    query = "SELECT * FROM users WHERE id=" + user_id
    cursor.execute(query)
    
    return cursor.fetchone()
"""

    sinks = detector.detect_sinks(code, "python", min_confidence=0.8)

    print(f"\nFound {len(sinks)} security sink(s):\n")
    for sink in sinks:
        owasp = detector.get_owasp_category(sink.vulnerability_type)
        print(f"Pattern: {sink.pattern}")
        print(f"Type: {sink.sink_type.name}")
        print(f"Confidence: {sink.confidence}")
        print(f"Line: {sink.line}")
        print(f"OWASP: {owasp}")
        print(f"Snippet: {sink.code_snippet}")
        print()


def example_typescript_xss():
    """Detect XSS vulnerabilities in TypeScript."""
    print("=" * 70)
    print("Example 2: TypeScript XSS Detection")
    print("=" * 70)

    detector = UnifiedSinkDetector()

    code = """
function displayUserComment(comment: string) {
    const element = document.getElementById('comment-box');
    
    // VULNERABLE: Direct HTML injection
    element.innerHTML = comment;
    
    // VULNERABLE: React dangerous HTML
    return <div dangerouslySetInnerHTML={{__html: comment}} />;
}
"""

    sinks = detector.detect_sinks(code, "typescript", min_confidence=0.8)

    print(f"\nFound {len(sinks)} security sink(s):\n")
    for sink in sinks:
        print(f"Pattern: {sink.pattern}")
        print(f"Type: {sink.sink_type.name}")
        print(f"Confidence: {sink.confidence}")
        print(f"Line: {sink.line}")
        print()


def example_javascript_command_injection():
    """Detect command injection in JavaScript."""
    print("=" * 70)
    print("Example 3: JavaScript Command Injection Detection")
    print("=" * 70)

    detector = UnifiedSinkDetector()

    code = """
const userInput = req.query.command;

// VULNERABLE: Executing user input
eval(userInput);

// VULNERABLE: Child process with user input
exec('ls ' + userInput, (err, stdout) => {
    console.log(stdout);
});
"""

    sinks = detector.detect_sinks(code, "javascript", min_confidence=0.8)

    print(f"\nFound {len(sinks)} security sink(s):\n")
    for sink in sinks:
        print(f"Pattern: {sink.pattern}")
        print(f"Type: {sink.sink_type.name}")
        print(f"Confidence: {sink.confidence}")
        print(f"Line: {sink.line}")
        print()


def example_confidence_filtering():
    """Demonstrate confidence threshold filtering."""
    print("=" * 70)
    print("Example 4: Confidence Threshold Filtering")
    print("=" * 70)

    detector = UnifiedSinkDetector()

    code = """
import sqlite3

def process_data(filename, query):
    # High confidence sink (1.0)
    cursor.execute(query)
    
    # Lower confidence sink (0.8)
    with open(filename, 'r') as f:
        data = f.read()
    
    return data
"""

    # High confidence only
    print("\nHigh confidence sinks (1.0):")
    high_sinks = detector.detect_sinks(code, "python", min_confidence=1.0)
    for sink in high_sinks:
        print(f"  - {sink.pattern} (confidence: {sink.confidence})")

    # Medium confidence
    print("\nMedium+ confidence sinks (0.8):")
    medium_sinks = detector.detect_sinks(code, "python", min_confidence=0.8)
    for sink in medium_sinks:
        print(f"  - {sink.pattern} (confidence: {sink.confidence})")

    # All sinks
    print("\nAll sinks (0.5+):")
    all_sinks = detector.detect_sinks(code, "python", min_confidence=0.5)
    for sink in all_sinks:
        print(f"  - {sink.pattern} (confidence: {sink.confidence})")


def example_coverage_report():
    """Display coverage statistics."""
    print("=" * 70)
    print("Example 5: Coverage Report")
    print("=" * 70)

    detector = UnifiedSinkDetector()
    report = detector.get_coverage_report()

    print(f"\nTotal security sink patterns: {report['total_patterns']}")
    print("\nPatterns by language:")
    for lang, count in report["by_language"].items():
        print(f"  {lang}: {count}")

    print("\nPatterns by vulnerability type:")
    for vuln_type, langs in report["by_vulnerability"].items():
        total = sum(langs.values())
        print(f"  {vuln_type}: {total}")

    print("\nOWASP Top 10 2021 Coverage:")
    for category, stats in report["owasp_coverage"].items():
        pct = stats["percentage"]
        print(f"  {category}")
        print(f"    Coverage: {stats['covered']}/{stats['total']} ({pct:.1f}%)")


def example_multi_language():
    """Detect sinks across multiple languages."""
    print("=" * 70)
    print("Example 6: Multi-Language Detection")
    print("=" * 70)

    detector = UnifiedSinkDetector()

    examples = {
        "python": 'cursor.execute("SELECT * FROM users")',
        "java": 'Statement.executeQuery("SELECT * FROM users");',
        "typescript": 'connection.query("SELECT * FROM users");',
        "javascript": 'db.query("SELECT * FROM users");',
    }

    for language, code in examples.items():
        sinks = detector.detect_sinks(code, language, min_confidence=0.8)
        print(f"\n{language.upper()}:")
        if sinks:
            for sink in sinks:
                print(f"  Pattern: {sink.pattern}")
                print(f"  Confidence: {sink.confidence}")
        else:
            print("  No sinks detected")


def main():
    """Run all examples."""
    examples = [
        example_python_detection,
        example_typescript_xss,
        example_javascript_command_injection,
        example_confidence_filtering,
        example_coverage_report,
        example_multi_language,
    ]

    for example in examples:
        try:
            example()
            print("\n")
        except Exception as e:
            print(f"Error in {example.__name__}: {e}\n")


if __name__ == "__main__":
    main()
