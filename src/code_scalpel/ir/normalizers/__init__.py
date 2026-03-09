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

# [20260304_FEATURE] TypeScript normalizer — requires tree-sitter-typescript
try:
    from .typescript_normalizer import TypeScriptNormalizer

    _HAS_TYPESCRIPT = True
except ImportError:
    TypeScriptNormalizer = None  # type: ignore[assignment]
    _HAS_TYPESCRIPT = False

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

if _HAS_TYPESCRIPT:
    __all__.append("TypeScriptNormalizer")

if _HAS_C:
    __all__ += ["CNormalizer", "CVisitor"]

if _HAS_CPP:
    __all__ += ["CppNormalizer", "CppVisitor"]

if _HAS_CSHARP:
    __all__ += ["CSharpNormalizer", "CSharpVisitor"]

if _HAS_GO:
    __all__ += ["GoNormalizer", "GoVisitor"]

# [20260303_FEATURE] Kotlin normalizer — requires tree-sitter-kotlin
try:
    from .kotlin_normalizer import KotlinNormalizer, KotlinVisitor

    _HAS_KOTLIN = True
except ImportError:
    KotlinNormalizer = None  # type: ignore[assignment]
    KotlinVisitor = None  # type: ignore[assignment]
    _HAS_KOTLIN = False

if _HAS_KOTLIN:
    __all__ += ["KotlinNormalizer", "KotlinVisitor"]

# [20260303_FEATURE] PHP normalizer — requires tree-sitter-php
try:
    from .php_normalizer import PHPNormalizer, PHPVisitor

    _HAS_PHP = True
except ImportError:
    PHPNormalizer = None  # type: ignore[assignment]
    PHPVisitor = None  # type: ignore[assignment]
    _HAS_PHP = False

if _HAS_PHP:
    __all__ += ["PHPNormalizer", "PHPVisitor"]

# [20260304_FEATURE] Ruby normalizer — requires tree-sitter-ruby
try:
    from .ruby_normalizer import RubyNormalizer, RubyVisitor

    _HAS_RUBY = True
except ImportError:
    RubyNormalizer = None  # type: ignore[assignment]
    RubyVisitor = None  # type: ignore[assignment]
    _HAS_RUBY = False

if _HAS_RUBY:
    __all__ += ["RubyNormalizer", "RubyVisitor"]

# [20260304_FEATURE] Swift normalizer — requires tree-sitter-swift
try:
    from .swift_normalizer import SwiftNormalizer, SwiftVisitor

    _HAS_SWIFT = True
except ImportError:
    SwiftNormalizer = None  # type: ignore[assignment]
    SwiftVisitor = None  # type: ignore[assignment]
    _HAS_SWIFT = False

if _HAS_SWIFT:
    __all__ += ["SwiftNormalizer", "SwiftVisitor"]

# [20260305_FEATURE] Rust normalizer — requires tree-sitter-rust
try:
    from .rust_normalizer import RustNormalizer, RustVisitor

    _HAS_RUST = True
except ImportError:
    RustNormalizer = None  # type: ignore[assignment]
    RustVisitor = None  # type: ignore[assignment]
    _HAS_RUST = False

if _HAS_RUST:
    __all__ += ["RustNormalizer", "RustVisitor"]
