"""Ruby Parser Adapter - IParser interface wrapping RubyNormalizer.

[20260304_FEATURE] Full implementation replacing the Phase-2 stub.
Delegates parse() to RubyNormalizer and extracts function/class lists
from the resulting IRModule via simple IR traversal.
"""

from __future__ import annotations

from typing import Any, List

from ..interface import IParser, Language, ParseResult


class RubyParserAdapter(IParser):
    """
    Adapter for Ruby parsing using the RubyNormalizer IR layer.

    [20260304_FEATURE] Thin wrapper that satisfies the IParser interface
    by delegating code parsing to RubyNormalizer.normalize().

    Usage:
        adapter = RubyParserAdapter()
        result  = adapter.parse(ruby_source)
        funcs   = adapter.get_functions(result.ast)
        classes = adapter.get_classes(result.ast)
    """

    def __init__(self) -> None:
        """Initialize the Ruby parser adapter."""
        # [20260304_FEATURE] Lazy-import normalizer to avoid hard IR dependency
        from code_scalpel.ir.normalizers.ruby_normalizer import RubyNormalizer  # type: ignore
        self._normalizer = RubyNormalizer()

    def parse(self, code: str) -> ParseResult:
        """
        Parse Ruby source code and return a ParseResult.

        [20260304_FEATURE] ast_tree is the IRModule produced by RubyNormalizer.
        """
        ir_module = self._normalizer.normalize(code)
        return ParseResult(
            ast=ir_module,
            errors=[],
            warnings=[],
            metrics={},
            language=Language.RUBY,
        )

    def get_functions(self, ast_tree: Any) -> List[str]:
        """
        Extract function/method names from an IRModule.

        [20260304_FEATURE] Walks top-level and class-level IRFunction nodes.
        """
        from code_scalpel.ir.nodes import IRClassDef, IRFunctionDef  # type: ignore
        names: List[str] = []
        body = getattr(ast_tree, "body", []) or []
        for node in body:
            if isinstance(node, IRFunctionDef):
                names.append(node.name)
            elif isinstance(node, IRClassDef):
                for child in (getattr(node, "body", []) or []):
                    if isinstance(child, IRFunctionDef):
                        names.append(f"{node.name}#{child.name}")
        return names

    def get_classes(self, ast_tree: Any) -> List[str]:
        """
        Extract class names from an IRModule.

        [20260304_FEATURE] Returns names of all top-level IRClass nodes
        that are not modules (kind != 'module').
        """
        from code_scalpel.ir.nodes import IRClassDef  # type: ignore
        names: List[str] = []
        body = getattr(ast_tree, "body", []) or []
        for node in body:
            if isinstance(node, IRClassDef):
                meta = getattr(node, "_metadata", {}) or {}
                if meta.get("kind") != "module":
                    names.append(node.name)
        return names
