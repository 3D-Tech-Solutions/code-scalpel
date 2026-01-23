"""ParserFactory - Language-aware parser instantiation.

[20251221_FEATURE] Factory pattern for multi-language code parsing.

"""

from .interface import IParser, Language
from .python_parser import PythonParser


class ParserFactory:
    """Factory for creating language-specific parsers.

    [20251221_FEATURE] Unified parser instantiation across all languages.
    """

    _parsers: dict[Language, type[IParser]] = {
        Language.PYTHON: PythonParser,
    }

    # Extended extension mapping for comprehensive language detection
    _extension_map: dict[str, Language] = {
        # Python
        "py": Language.PYTHON,
        "pyw": Language.PYTHON,
        "pyi": Language.PYTHON,
        # JavaScript
        "js": Language.JAVASCRIPT,
        "mjs": Language.JAVASCRIPT,
        "cjs": Language.JAVASCRIPT,
        "jsx": Language.JAVASCRIPT,
        # TypeScript
        "ts": Language.TYPESCRIPT,
        "mts": Language.TYPESCRIPT,
        "cts": Language.TYPESCRIPT,
        "tsx": Language.TYPESCRIPT,
        # Java
        "java": Language.JAVA,
        # C/C++
        "c": Language.CPP,
        "cpp": Language.CPP,
        "cc": Language.CPP,
        "cxx": Language.CPP,
        "h": Language.CPP,
        "hpp": Language.CPP,
        "hxx": Language.CPP,
    }

    @classmethod
    def get_parser(cls, language: Language, backend: str | None = None) -> IParser:
        """Get a parser instance for the specified language.

        Args:
            language: Target programming language
            backend: Optional parser backend (e.g., "tree-sitter", "ast", "regex")

        Returns:
            Parser instance for the language

        Raises:
            ValueError: If no parser is registered for the language
        """
        parser_cls = cls._parsers.get(language)
        if not parser_cls:
            raise ValueError(f"No parser registered for language: {language}")
        return parser_cls()

    @classmethod
    def register_parser(cls, language: Language, parser_cls: type[IParser]) -> None:
        """Register a new parser for a language.

        Args:
            language: Target programming language
            parser_cls: Parser class implementing IParser
        """
        cls._parsers[language] = parser_cls

    @classmethod
    def is_registered(cls, language: Language) -> bool:
        """Check if a parser is registered for the language."""
        return language in cls._parsers

    @classmethod
    def list_registered(cls) -> list[Language]:
        """List all registered languages."""
        return list(cls._parsers.keys())

    @classmethod
    def detect_language(cls, filename: str) -> Language:
        """Detect language from filename extension.

        Args:
            filename: File path or name with extension

        Returns:
            Detected Language enum value, or Language.UNKNOWN
        """
        ext = filename.split(".")[-1].lower() if "." in filename else ""
        return cls._extension_map.get(ext, Language.UNKNOWN)

    @classmethod
    def from_file(cls, filepath: str, backend: str | None = None) -> IParser:
        """Create parser by detecting language from file path.

        [20251221_FEATURE] Convenience method for file-based parsing.

        Args:
            filepath: Path to source file
            backend: Optional parser backend preference

        Returns:
            Appropriate parser for the file's language

        Raises:
            ValueError: If language cannot be detected or no parser available
        """
        language = cls.detect_language(filepath)
        if language == Language.UNKNOWN:
            raise ValueError(f"Cannot detect language for file: {filepath}")
        return cls.get_parser(language, backend)


# Auto-register additional parsers when their modules are available
def _register_available_parsers() -> None:
    """Register parsers that are available in the installation.

    [20251221_FEATURE] Uses IParser adapters for unified interface.
    """
    # JavaScript parser via adapter
    try:
        from .adapters.javascript_adapter import JavaScriptParserAdapter

        ParserFactory.register_parser(Language.JAVASCRIPT, JavaScriptParserAdapter)
    except ImportError:
        pass

    # TypeScript parser via adapter
    try:
        from .adapters.javascript_adapter import TypeScriptParserAdapter

        ParserFactory.register_parser(Language.TYPESCRIPT, TypeScriptParserAdapter)
    except ImportError:
        pass

    # Java parser via adapter
    try:
        from .adapters.java_adapter import JavaParserAdapter

        ParserFactory.register_parser(Language.JAVA, JavaParserAdapter)
    except ImportError:
        pass


# Run auto-registration on module load
_register_available_parsers()
