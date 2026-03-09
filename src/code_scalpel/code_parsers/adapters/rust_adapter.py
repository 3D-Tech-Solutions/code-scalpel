"""Rust Parser Adapter - IParser interface for the Rust normalizer.

[20260305_FEATURE] Real implementation using tree-sitter-rust.

"""

from typing import Any, List

from ..interface import IParser, Language as IParserLanguage, ParseResult


class RustParserAdapter(IParser):
    """
    Adapter wrapping RustNormalizer for the IParser interface.

    [20260305_FEATURE] Full implementation using tree-sitter-rust.
    """

    def __init__(self) -> None:
        """Initialise the adapter, loading RustNormalizer lazily."""
        from code_scalpel.ir.normalizers.rust_normalizer import RustNormalizer

        self._normalizer = RustNormalizer()

    def parse(self, code: str) -> ParseResult:
        """Parse Rust source code and return a ParseResult wrapping an IRModule."""
        ir_module = self._normalizer.normalize(code)
        return ParseResult(
            ast=ir_module,
            errors=[],
            warnings=[],
            metrics={},
            language=IParserLanguage.RUST,
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
        """Return top-level struct/enum/trait/impl names from a parsed IRModule."""
        from code_scalpel.ir.nodes import IRClassDef

        return [
            n.name
            for n in getattr(ast_tree, "body", [])
            if isinstance(n, IRClassDef)
        ]
