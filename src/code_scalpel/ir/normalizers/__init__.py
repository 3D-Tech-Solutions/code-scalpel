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
    JavaScriptNormalizer = None  # type: ignore[assignment]
    _HAS_JAVASCRIPT = False

# [20260224_FEATURE] C/C++ normalizers — require tree-sitter-c / tree-sitter-cpp
try:
    from .c_normalizer import CNormalizer, CVisitor

    _HAS_C = True
except ImportError:
    CNormalizer = None  # type: ignore[assignment]
    CVisitor = None  # type: ignore[assignment]
    _HAS_C = False

try:
    from .cpp_normalizer import CppNormalizer, CppVisitor

    _HAS_CPP = True
except ImportError:
    CppNormalizer = None  # type: ignore[assignment]
    CppVisitor = None  # type: ignore[assignment]
    _HAS_CPP = False

# [20260224_FEATURE] C# normalizer — requires tree-sitter-c-sharp
try:
    from .csharp_normalizer import CSharpNormalizer, CSharpVisitor

    _HAS_CSHARP = True
except ImportError:
    CSharpNormalizer = None  # type: ignore[assignment]
    CSharpVisitor = None  # type: ignore[assignment]
    _HAS_CSHARP = False

# [20260302_FEATURE] Go normalizer — requires tree-sitter-go
try:
    from .go_normalizer import GoNormalizer, GoVisitor

    _HAS_GO = True
except ImportError:
    GoNormalizer = None  # type: ignore[assignment]
    GoVisitor = None  # type: ignore[assignment]
    _HAS_GO = False

__all__ = [
    "BaseNormalizer",
    "PythonNormalizer",
    "JavaNormalizer",
    "TreeSitterVisitor",
    "VisitorContext",
]

if _HAS_JAVASCRIPT:
    __all__.append("JavaScriptNormalizer")

if _HAS_C:
    __all__ += ["CNormalizer", "CVisitor"]

if _HAS_CPP:
    __all__ += ["CppNormalizer", "CppVisitor"]

if _HAS_CSHARP:
    __all__ += ["CSharpNormalizer", "CSharpVisitor"]

if _HAS_GO:
    __all__ += ["GoNormalizer", "GoVisitor"]
