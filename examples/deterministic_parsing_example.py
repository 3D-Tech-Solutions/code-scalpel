"""
Reference implementation: Refactoring PDG Builder to use deterministic parsing.

BEFORE (non-deterministic):
```python
def build(self, code: str) -> tuple[nx.DiGraph, nx.DiGraph]:
    tree = ast.parse(code)  # ❌ NO ERROR HANDLING
    self.visit(tree)
    return self.graph, self.call_graph
```

AFTER (deterministic):
```python
from code_scalpel.parsing import parse_python_code, ParsingError

def build(self, code: str) -> tuple[nx.DiGraph, nx.DiGraph]:
    try:
        tree, report = parse_python_code(code)
    except ParsingError as e:
        # Deterministic error - same input always produces same error
        raise ValueError(
            f"Cannot build PDG: {e}\\n"
            f"Location: {e.location}\\n"
            f"Suggestion: {e.suggestion}"
        ) from e

    # Track if code was modified
    if report.was_sanitized:
        self._sanitization_report = report

    self.visit(tree)
    return self.graph, self.call_graph
```

Benefits:
1. ✅ Deterministic: Same code + same config = same result
2. ✅ Controlled by response_config.json (no code changes needed)
3. ✅ Consistent error messages across all entry points
4. ✅ Sanitization tracking available to caller
"""

# Example refactor of PDGBuilder
from code_scalpel.parsing import ParsingError, SanitizationReport, parse_python_code


class RefactoredPDGBuilder:
    """PDG Builder with deterministic parsing."""

    def __init__(self):
        self.graph = None
        self.call_graph = None
        self._sanitization_report: SanitizationReport | None = None

    def build(self, code: str):
        """
        Build PDG with deterministic error handling.

        Raises:
            ValueError: When code cannot be parsed
        """
        try:
            tree, report = parse_python_code(code)
        except ParsingError as e:
            # Convert to ValueError to maintain backward compatibility
            # But now with consistent error messages
            msg = f"Cannot build PDG: {e}"
            if e.location:
                msg += f"\nLocation: {e.location}"
            if e.suggestion:
                msg += f"\nSuggestion: {e.suggestion}"
            raise ValueError(msg) from e

        # Track sanitization for reporting
        if report.was_sanitized:
            self._sanitization_report = report

        # Continue with existing logic
        # self.visit(tree)
        # return self.graph, self.call_graph
        return tree, report  # Simplified for example

    @property
    def was_code_modified(self) -> bool:
        """Check if input code was sanitized during parsing."""
        return self._sanitization_report is not None

    def get_sanitization_report(self) -> SanitizationReport | None:
        """Get details of code modifications during parsing."""
        return self._sanitization_report


# Example usage
if __name__ == "__main__":
    builder = RefactoredPDGBuilder()

    # Test 1: Clean code
    clean_code = "def foo(): pass"
    tree, report = builder.build(clean_code)
    print(f"Clean code: sanitized={report.was_sanitized}")

    # Test 2: Code with merge conflict (fails in strict mode)
    dirty_code = """
def calculate_tax(amount):
<<<<<<< HEAD
    return amount * 0.05
=======
    return amount * 0.08
>>>>>>> feature-branch
"""

    try:
        tree, report = builder.build(dirty_code)
        print(f"Dirty code: sanitized={report.was_sanitized}")
        if report.was_sanitized:
            print(f"Changes: {report.changes}")
    except ValueError as e:
        print(f"Expected error in strict mode: {e}")

    # To make it work, update response_config.json:
    # {"parsing": {"mode": "permissive"}}
