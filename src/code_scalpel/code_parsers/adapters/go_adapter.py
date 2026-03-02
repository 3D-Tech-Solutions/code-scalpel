"""Go Parser Adapter - IParser interface for Go parser.

[20260302_FEATURE] Full implementation using GoNormalizer (tree-sitter-go).
"""

from typing import Any, List

from ..interface import IParser, ParseResult


class GoParserAdapter(IParser):
    """
    Adapter wrapping GoNormalizer to implement the IParser interface.

    [20260302_FEATURE] Replaces the NotImplementedError stub with a real
    implementation backed by tree-sitter-go via GoNormalizer.
    """

    def __init__(self) -> None:
        """Initialize the Go parser adapter."""
        from code_scalpel.ir.normalizers.go_normalizer import GoNormalizer

        self._normalizer = GoNormalizer()

    def parse(self, code: str) -> ParseResult:
        """Parse Go source code and return a ParseResult with the IR module."""
        from ..interface import Language as IParserLanguage

        ir_module = self._normalizer.normalize(code)
        return ParseResult(
            ast=ir_module,
            errors=[],
            warnings=[],
            metrics={},
            language=IParserLanguage.GO,
        )

    def get_functions(self, ast_tree: Any) -> List[str]:
        """Return names of all top-level functions and methods."""
        from code_scalpel.ir.nodes import IRFunctionDef

        return [
            n.name
            for n in getattr(ast_tree, "body", [])
            if isinstance(n, IRFunctionDef)
        ]

    def get_classes(self, ast_tree: Any) -> List[str]:
        """Return names of all struct and interface type declarations."""
        from code_scalpel.ir.nodes import IRClassDef

        return [
            n.name for n in getattr(ast_tree, "body", []) if isinstance(n, IRClassDef)
        ]
