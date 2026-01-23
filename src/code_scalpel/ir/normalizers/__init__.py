"""
Normalizers - Convert language-specific AST/CST to Unified IR.

Each normalizer converts its language's native parse tree to our Unified IR.
The IR preserves source_language for semantic dispatch.

Available Normalizers:
    - PythonNormalizer: Python ast.* -> IR
    - JavaNormalizer: Java tree-sitter CST -> IR (v2.0.0)
    - JavaScriptNormalizer: JavaScript tree-sitter CST -> IR (v0.4.0)
    - TypeScriptNormalizer: TypeScript tree-sitter CST -> IR (v2.0.0)

Base Classes:
    - BaseNormalizer: Abstract interface for all normalizers
    - TreeSitterVisitor: Base class for tree-sitter based normalizers
"""

from .base import BaseNormalizer
from .java_normalizer import JavaNormalizer  # [20251215_FEATURE] Export Java normalizer
from .python_normalizer import PythonNormalizer
from .tree_sitter_visitor import TreeSitterVisitor, VisitorContext

# JavaScript normalizer requires tree-sitter, import conditionally
try:
    from .javascript_normalizer import JavaScriptNormalizer

    _HAS_JAVASCRIPT = True
except ImportError:
    JavaScriptNormalizer = None
    _HAS_JAVASCRIPT = False

__all__ = [
    "BaseNormalizer",
    "PythonNormalizer",
    "JavaNormalizer",
    "TreeSitterVisitor",
    "VisitorContext",
]

if _HAS_JAVASCRIPT:
    __all__.append("JavaScriptNormalizer")
