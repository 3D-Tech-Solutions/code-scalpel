"""PHP Parser Adapter - IParser interface wrapping PHPNormalizer.

[20260303_FEATURE] Full implementation replacing the NotImplementedError stub.
"""

from typing import Any, List

from ..interface import IParser, ParseResult


class PHPParserAdapter(IParser):
    """
    Adapter for PHP parsing via tree-sitter-php + PHPNormalizer.

    [20260303_FEATURE] Thin wrapper over PHPNormalizer; delegates all parsing
    to the IR layer and exposes function/class names from the resulting IRModule.
    """

    def __init__(self) -> None:
        from code_scalpel.ir.normalizers.php_normalizer import PHPNormalizer

        self._normalizer = PHPNormalizer()

    def parse(self, code: str) -> ParseResult:
        """Parse PHP code and return a ParseResult with the IR module."""
        from ..interface import Language as IParserLanguage

        ir_module = self._normalizer.normalize(code)
        return ParseResult(
            ast=ir_module,
            errors=[],
            warnings=[],
            metrics={},
            language=IParserLanguage.PHP,
        )

    def get_functions(self, ast_tree: Any) -> List[str]:
        """Return top-level and method function names from the IRModule."""
        from code_scalpel.ir.nodes import IRClassDef, IRFunctionDef, IRModule

        module = (
            ast_tree
            if isinstance(ast_tree, IRModule)
            else getattr(ast_tree, "ast_tree", None)
        )
        if module is None:
            return []
        names: List[str] = []
        for node in module.body:
            if isinstance(node, IRFunctionDef):
                names.append(node.name)
            elif isinstance(node, IRClassDef):
                for item in node.body:
                    if isinstance(item, IRFunctionDef):
                        names.append(f"{node.name}.{item.name}")
        return names

    def get_classes(self, ast_tree: Any) -> List[str]:
        """Return class names from the IRModule."""
        from code_scalpel.ir.nodes import IRClassDef, IRModule

        module = (
            ast_tree
            if isinstance(ast_tree, IRModule)
            else getattr(ast_tree, "ast_tree", None)
        )
        if module is None:
            return []
        return [node.name for node in module.body if isinstance(node, IRClassDef)]
