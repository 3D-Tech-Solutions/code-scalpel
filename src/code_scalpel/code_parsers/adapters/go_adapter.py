"""Go Parser Adapter - IParser interface for Go parser.

[20251224_FEATURE] Stub adapter for Go parsing support.

"""

from typing import Any

from ..interface import IParser, ParseResult


class GoParserAdapter(IParser):
    """
    Adapter for Go parsing (STUB - Not Yet Implemented).

    [20251224_STUB] Placeholder for Go parser integration.

    To implement:
        1. Choose backend (tree-sitter-go or go/parser stdlib)
        2. Implement parse() method
        3. Add Go-specific extraction methods
        4. Support Go version detection
        5. Add concurrency pattern detection
    """

    def __init__(self):
        """Initialize the Go parser adapter (stub)."""
        raise NotImplementedError(
            "GoParserAdapter not yet implemented. " "See TODO items in this file for implementation roadmap."
        )

    def parse(self, code: str) -> ParseResult:
        """Parse Go code (stub)."""
        raise NotImplementedError("Go parsing not yet implemented")

    def get_functions(self, ast_tree: Any) -> list[str]:
        """Get function names from Go AST (stub)."""
        raise NotImplementedError("Go function extraction not yet implemented")

    def get_classes(self, ast_tree: Any) -> list[str]:
        """Get struct/interface names from Go AST (stub)."""
        raise NotImplementedError("Go type extraction not yet implemented")
