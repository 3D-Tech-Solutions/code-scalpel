"""Parser Interface - Unified parser contract across all languages."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any


class Language(Enum):
    """Supported programming languages."""

    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    JAVA = "java"
    CPP = "cpp"
    UNKNOWN = "unknown"


@dataclass
class ParseResult:
    """Result of code parsing."""

    ast: Any  # AST structure (language-dependent)
    errors: list[dict[str, Any]]
    warnings: list[str]
    metrics: dict[str, Any]
    language: Language


class IParser(ABC):
    """Interface for language-specific parsers."""

    @abstractmethod
    def parse(self, code: str) -> ParseResult:
        """Parse source code into an AST."""
        pass

    @abstractmethod
    def get_functions(self, ast_tree: Any) -> list[str]:
        """Get list of function names."""
        pass

    @abstractmethod
    def get_classes(self, ast_tree: Any) -> list[str]:
        """Get list of class names."""
        pass
