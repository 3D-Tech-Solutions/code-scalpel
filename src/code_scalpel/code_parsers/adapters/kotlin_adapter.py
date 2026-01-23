"""Kotlin Parser Adapter - IParser interface for Kotlin parser.

[20251224_FEATURE] Stub adapter for Kotlin parsing support.

"""

from typing import Any

from ..interface import IParser, ParseResult


class KotlinParserAdapter(IParser):
    """
    Adapter for Kotlin parsing (STUB - Not Yet Implemented).

    [20251224_STUB] Placeholder for Kotlin parser integration.

    To implement:
        1. Choose backend and integrate parser
        2. Implement parse() method
        3. Add Kotlin-specific extraction methods
        4. Support Kotlin version detection
        5. Add framework pattern detection
    """

    def __init__(self):
        """Initialize the Kotlin parser adapter (stub)."""
        raise NotImplementedError(
            "KotlinParserAdapter not yet implemented. " "See TODO items in this file for implementation roadmap."
        )

    def parse(self, code: str) -> ParseResult:
        """Parse Kotlin code (stub)."""
        raise NotImplementedError("Kotlin parsing not yet implemented")

    def get_functions(self, ast_tree: Any) -> list[str]:
        """Get function names from Kotlin AST (stub)."""
        raise NotImplementedError("Kotlin function extraction not yet implemented")

    def get_classes(self, ast_tree: Any) -> list[str]:
        """Get class names from Kotlin AST (stub)."""
        raise NotImplementedError("Kotlin class extraction not yet implemented")
