"""Swift Parser Adapter - IParser interface for the Swift normalizer.

[20260304_FEATURE] Real implementation replacing stub adapter.

"""

from typing import Any, List

from ..interface import IParser, Language as IParserLanguage, ParseResult


class SwiftParserAdapter(IParser):
    """
    Adapter wrapping SwiftNormalizer for the IParser interface.

    [20260304_FEATURE] Full implementation using tree-sitter-swift.
    """

    def __init__(self) -> None:
        """Initialise the adapter, loading SwiftNormalizer lazily."""
        from code_scalpel.ir.normalizers.swift_normalizer import SwiftNormalizer

        self._normalizer = SwiftNormalizer()

    def parse(self, code: str) -> ParseResult:
        """Parse Swift source code and return a ParseResult wrapping an IRModule."""
        ir_module = self._normalizer.normalize(code)
        return ParseResult(
            ast=ir_module,
            errors=[],
            warnings=[],
            metrics={},
            language=IParserLanguage.SWIFT,
        )

    def get_functions(self, ast_tree: Any) -> List[str]:
        """Return top-level function names from a parsed IRModule."""
        from code_scalpel.ir.nodes import IRFunctionDef

        return [
            n.name
            for n in getattr(ast_tree, "body", [])
            if isinstance(n, IRFunctionDef)
        ]

    def get_classes(self, ast_tree: Any) -> List[str]:
        """Return top-level class/struct/enum names from a parsed IRModule."""
        from code_scalpel.ir.nodes import IRClassDef

        return [
            n.name
            for n in getattr(ast_tree, "body", [])
            if isinstance(n, IRClassDef)
        ]
