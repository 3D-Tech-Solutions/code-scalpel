"""Ruby Parser Adapter - IParser interface for Ruby parser.

[20251224_FEATURE] Stub adapter for Ruby parsing support.

"""

from typing import Any

from ..interface import IParser, ParseResult


class RubyParserAdapter(IParser):
    """
    Adapter for Ruby parsing (STUB - Not Yet Implemented).

    [20251224_STUB] Placeholder for Ruby parser integration.

    To implement:
        1. Choose backend and integrate parser
        2. Implement parse() method
        3. Add Ruby-specific extraction methods
        4. Support Ruby version detection
        5. Add framework pattern detection
    """

    def __init__(self):
        """Initialize the Ruby parser adapter (stub)."""
        raise NotImplementedError(
            "RubyParserAdapter not yet implemented. " "See TODO items in this file for implementation roadmap."
        )

    def parse(self, code: str) -> ParseResult:
        """Parse Ruby code (stub)."""
        raise NotImplementedError("Ruby parsing not yet implemented")

    def get_functions(self, ast_tree: Any) -> list[str]:
        """Get function names from Ruby AST (stub)."""
        raise NotImplementedError("Ruby function extraction not yet implemented")

    def get_classes(self, ast_tree: Any) -> list[str]:
        """Get class names from Ruby AST (stub)."""
        raise NotImplementedError("Ruby class extraction not yet implemented")
