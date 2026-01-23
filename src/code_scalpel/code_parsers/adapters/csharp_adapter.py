"""C# Parser Adapter - IParser interface for C# parser.

[20251224_FEATURE] Stub adapter for C# parsing support.

"""

from typing import Any

from ..interface import IParser, ParseResult


class CSharpParserAdapter(IParser):
    """
    Adapter for C# parsing (STUB - Not Yet Implemented).

    [20251224_STUB] Placeholder for C# parser integration.

    To implement:
        1. Choose backend (tree-sitter-csharp or Roslyn)
        2. Implement parse() method
        3. Add C#-specific extraction methods
        4. Support C# version detection
        5. Add .NET framework detection
    """

    def __init__(self):
        """Initialize the C# parser adapter (stub)."""
        raise NotImplementedError(
            "CSharpParserAdapter not yet implemented. " "See TODO items in this file for implementation roadmap."
        )

    def parse(self, code: str) -> ParseResult:
        """Parse C# code (stub)."""
        raise NotImplementedError("C# parsing not yet implemented")

    def get_functions(self, ast_tree: Any) -> list[str]:
        """Get method names from C# AST (stub)."""
        raise NotImplementedError("C# method extraction not yet implemented")

    def get_classes(self, ast_tree: Any) -> list[str]:
        """Get class names from C# AST (stub)."""
        raise NotImplementedError("C# class extraction not yet implemented")
