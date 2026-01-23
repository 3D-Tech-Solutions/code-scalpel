"""Swift Parser Adapter - IParser interface for Swift parser.

[20251224_FEATURE] Stub adapter for Swift parsing support.

"""

from typing import Any

from ..interface import IParser, ParseResult


class SwiftParserAdapter(IParser):
    """
    Adapter for Swift parsing (STUB - Not Yet Implemented).

    [20251224_STUB] Placeholder for Swift parser integration.

    To implement:
        1. Choose backend and integrate parser
        2. Implement parse() method
        3. Add Swift-specific extraction methods
        4. Support Swift version detection
        5. Add framework pattern detection
    """

    def __init__(self):
        """Initialize the Swift parser adapter (stub)."""
        raise NotImplementedError(
            "SwiftParserAdapter not yet implemented. " "See TODO items in this file for implementation roadmap."
        )

    def parse(self, code: str) -> ParseResult:
        """Parse Swift code (stub)."""
        raise NotImplementedError("Swift parsing not yet implemented")

    def get_functions(self, ast_tree: Any) -> list[str]:
        """Get function names from Swift AST (stub)."""
        raise NotImplementedError("Swift function extraction not yet implemented")

    def get_classes(self, ast_tree: Any) -> list[str]:
        """Get class names from Swift AST (stub)."""
        raise NotImplementedError("Swift class extraction not yet implemented")
