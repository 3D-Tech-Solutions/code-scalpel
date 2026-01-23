"""PHP Parser Adapter - IParser interface for PHP parser.

[20251224_FEATURE] Stub adapter for PHP parsing support.

"""

from typing import Any

from ..interface import IParser, ParseResult


class PHPParserAdapter(IParser):
    """
    Adapter for PHP parsing (STUB - Not Yet Implemented).

    [20251224_STUB] Placeholder for PHP parser integration.

    To implement:
        1. Choose backend and integrate parser
        2. Implement parse() method
        3. Add PHP-specific extraction methods
        4. Support PHP version detection
        5. Add framework pattern detection
    """

    def __init__(self):
        """Initialize the PHP parser adapter (stub)."""
        raise NotImplementedError(
            "PHPParserAdapter not yet implemented. " "See TODO items in this file for implementation roadmap."
        )

    def parse(self, code: str) -> ParseResult:
        """Parse PHP code (stub)."""
        raise NotImplementedError("PHP parsing not yet implemented")

    def get_functions(self, ast_tree: Any) -> list[str]:
        """Get function names from PHP AST (stub)."""
        raise NotImplementedError("PHP function extraction not yet implemented")

    def get_classes(self, ast_tree: Any) -> list[str]:
        """Get class names from PHP AST (stub)."""
        raise NotImplementedError("PHP class extraction not yet implemented")
