"""Parser Interface - Unified parser contract across all languages."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List


class Language(Enum):
    """Supported programming languages."""

    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    JAVA = "java"
    C = "c"  # [20260225_FEATURE]
    CPP = "cpp"
    CSHARP = "csharp"  # [20260225_FEATURE]
    GO = "go"  # [20260302_FEATURE]
    KOTLIN = "kotlin"  # [20260303_FEATURE]
    PHP = "php"  # [20260304_FEATURE]
    RUBY = "ruby"  # [20260304_FEATURE]
    SWIFT = "swift"  # [20260304_FEATURE] Swift language support
    RUST = "rust"  # [20260305_FEATURE] Rust language support
    UNKNOWN = "unknown"


@dataclass
class ParseResult:
    """Result of code parsing."""

    ast: Any  # AST structure (language-dependent)
    errors: List[Dict[str, Any]]
    warnings: List[str]
    metrics: Dict[str, Any]
    language: Language


class IParser(ABC):
    """Interface for language-specific parsers."""

    @abstractmethod
    def parse(self, code: str) -> ParseResult:
        """Parse source code into an AST."""
        pass

    @abstractmethod
    def get_functions(self, ast_tree: Any) -> List[str]:
        """Get list of function names."""
        pass

    @abstractmethod
    def get_classes(self, ast_tree: Any) -> List[str]:
        """Get list of class names."""
        pass
