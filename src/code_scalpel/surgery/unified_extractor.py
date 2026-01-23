"""
Unified Extractor - Universal code extraction across all languages.

# [20251224_REFACTOR] Moved from code_scalpel/unified_extractor.py to
# code_scalpel/surgery/unified_extractor.py as part of Issue #2
# in PROJECT_REORG_REFACTOR.md Phase 1.

[20251221_FEATURE] v3.1.0 - Consolidates surgical_extractor + polyglot
into single interface backed by code_parser analysis layer.

This module provides a unified interface for extracting code elements
(functions, classes, methods) from any supported programming language.

Architecture:
    - Python: Routes to surgical_extractor (rich dependency resolution)
    - JS/TS/Java: Routes to polyglot (JSX/React support via IR)
    - Future: Routes to code_parser for remaining 7 languages

Usage:
    from code_scalpel.surgery import UnifiedExtractor

    # Extract from Python
    extractor = UnifiedExtractor.from_file("utils.py")
    result = extractor.extract("function", "calculate_tax")

    # Extract from JavaScript
    extractor = UnifiedExtractor.from_file("utils.js")
    result = extractor.extract("function", "calculateTax")

    # Extract from Java
    extractor = UnifiedExtractor.from_file("Utils.java")
    result = extractor.extract("method", "Calculator.add")
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class Language(Enum):
    """
    Supported programming languages.

    """

    AUTO = "auto"
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    JAVA = "java"
    GO = "go"
    CSHARP = "csharp"
    CPP = "cpp"
    KOTLIN = "kotlin"
    RUBY = "ruby"
    SWIFT = "swift"
    PHP = "php"


@dataclass
class SymbolInfo:
    """
    Information about an extractable symbol.

    [20251221_FEATURE] Used by list_symbols() for symbol discovery.
    """

    name: str
    symbol_type: str  # "function", "class", "method"
    line_start: int
    line_end: int
    parent: str | None = None  # For methods: containing class name
    is_async: bool = False
    decorators: list[str] = field(default_factory=list)

    @property
    def qualified_name(self) -> str:
        """Get fully qualified name (e.g., 'ClassName.method_name')."""
        if self.parent:
            return f"{self.parent}.{self.name}"
        return self.name


@dataclass
class ImportInfo:
    """
    Information about an import statement.

    [20251221_FEATURE] Used by get_imports() for dependency analysis.
    """

    module: str  # The module being imported (e.g., "os.path")
    names: list[str] = field(default_factory=list)  # Specific names imported
    alias: str | None = None  # Alias if "import x as y" or "from x import y as z"
    is_from_import: bool = False  # True for "from x import y"
    is_relative: bool = False  # True for relative imports (from . import)
    level: int = 0  # Relative import level (dots)
    line_number: int = 0

    @property
    def import_statement(self) -> str:
        """Reconstruct the import statement."""
        if self.is_from_import:
            dots = "." * self.level
            module_part = f"{dots}{self.module}" if self.module else dots
            names_part = ", ".join(self.names) if self.names else "*"
            return f"from {module_part} import {names_part}"
        else:
            if self.alias:
                return f"import {self.module} as {self.alias}"
            return f"import {self.module}"


@dataclass
class FileSummary:
    """
    Quick summary of a file's structure.

    [20251221_FEATURE] Used by get_summary() for file overview.
    """

    file_path: str | None
    language: str
    total_lines: int
    num_functions: int
    num_classes: int
    num_methods: int
    num_imports: int
    symbols: list[SymbolInfo] = field(default_factory=list)
    imports: list[ImportInfo] = field(default_factory=list)

    def to_markdown(self) -> str:
        """Format summary as Markdown."""
        parts = []
        if self.file_path:
            parts.append(f"# File Summary: `{Path(self.file_path).name}`")
        else:
            parts.append("# File Summary")
        parts.append("")
        parts.append(f"- **Language:** {self.language}")
        parts.append(f"- **Total Lines:** {self.total_lines}")
        parts.append(f"- **Functions:** {self.num_functions}")
        parts.append(f"- **Classes:** {self.num_classes}")
        parts.append(f"- **Methods:** {self.num_methods}")
        parts.append(f"- **Imports:** {self.num_imports}")
        parts.append("")

        if self.symbols:
            parts.append("## Symbols")
            parts.append("")
            for sym in self.symbols:
                prefix = "  " if sym.parent else ""
                async_mark = "async " if sym.is_async else ""
                dec_mark = f" [{', '.join(sym.decorators)}]" if sym.decorators else ""
                parts.append(
                    f"{prefix}- `{async_mark}{sym.symbol_type}` **{sym.name}**{dec_mark} (L{sym.line_start}-{sym.line_end})"
                )

        return "\n".join(parts)

    def to_json(self, indent: int = 2) -> str:
        """Serialize to JSON."""
        import json

        data = {
            "file_path": self.file_path,
            "language": self.language,
            "total_lines": self.total_lines,
            "counts": {
                "functions": self.num_functions,
                "classes": self.num_classes,
                "methods": self.num_methods,
                "imports": self.num_imports,
            },
            "symbols": [
                {
                    "name": s.name,
                    "type": s.symbol_type,
                    "qualified_name": s.qualified_name,
                    "lines": [s.line_start, s.line_end],
                    "is_async": s.is_async,
                    "decorators": s.decorators,
                }
                for s in self.symbols
            ],
            "imports": [
                {
                    "module": i.module,
                    "names": i.names,
                    "statement": i.import_statement,
                    "line": i.line_number,
                }
                for i in self.imports
            ],
        }
        return json.dumps(data, indent=indent)


@dataclass
class SignatureInfo:
    """
    Function/method signature information.

    [20251221_FEATURE] Used by extract_signatures() for API documentation.
    """

    name: str
    qualified_name: str
    parameters: list[str]  # Parameter strings including type hints
    return_type: str | None = None
    decorators: list[str] = field(default_factory=list)
    is_async: bool = False
    docstring: str | None = None
    line_number: int = 0

    @property
    def signature_string(self) -> str:
        """Get the full signature as a string."""
        async_prefix = "async " if self.is_async else ""
        params = ", ".join(self.parameters)
        ret = f" -> {self.return_type}" if self.return_type else ""
        return f"{async_prefix}def {self.name}({params}){ret}"

    def to_stub(self) -> str:
        """Generate .pyi stub format."""
        lines = []
        for dec in self.decorators:
            lines.append(f"@{dec}")
        lines.append(f"{self.signature_string}: ...")
        return "\n".join(lines)


@dataclass
class UnifiedExtractionResult:
    """
    Result of code extraction across any language.

    [20251221_FEATURE] Unified result format for all languages.

    """

    success: bool
    target_name: str
    target_type: str
    language: str
    code: str = ""
    start_line: int = 0
    end_line: int = 0
    dependencies: list[str] = field(default_factory=list)
    imports_needed: list[str] = field(default_factory=list)
    file_path: str | None = None
    token_estimate: int = 0
    error: str | None = None

    # JS/TS specific fields
    jsx_normalized: bool = False
    is_server_component: bool = False
    is_server_action: bool = False
    component_type: str | None = None

    # Python specific fields
    context_code: str = ""
    context_items: list[str] = field(default_factory=list)

    @property
    def line_count(self) -> int:
        """Number of lines in the extracted code."""
        if not self.code:
            return 0
        return len(self.code.splitlines())

    @property
    def full_code_with_context(self) -> str:
        """Get code combined with context (if any)."""
        if self.context_code:
            return f"{self.context_code}\n\n{self.code}"
        return self.code

    def to_json(self, indent: int = 2) -> str:
        """
        Serialize extraction result to JSON.

        [20251221_FEATURE] Structured output for programmatic use.

        Args:
            indent: JSON indentation level (default: 2)

        Returns:
            JSON string representation
        """
        data = {
            "success": self.success,
            "target_name": self.target_name,
            "target_type": self.target_type,
            "language": self.language,
            "code": self.code,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "line_count": self.line_count,
            "dependencies": self.dependencies,
            "imports_needed": self.imports_needed,
            "file_path": self.file_path,
            "token_estimate": self.token_estimate,
            "error": self.error,
        }
        # Add context if present
        if self.context_code:
            data["context_code"] = self.context_code
            data["context_items"] = self.context_items
        # Add JS/TS fields if relevant
        if self.jsx_normalized:
            data["jsx_normalized"] = self.jsx_normalized
        if self.component_type:
            data["component_type"] = self.component_type
            data["is_server_component"] = self.is_server_component
            data["is_server_action"] = self.is_server_action
        return json.dumps(data, indent=indent)

    def to_markdown(self, include_metadata: bool = True) -> str:
        """
        Format extraction result as Markdown.

        [20251221_FEATURE] Documentation-friendly output format.

        Args:
            include_metadata: Include metadata header (default: True)

        Returns:
            Markdown formatted string
        """
        parts = []

        if not self.success:
            return f"## Extraction Failed\n\n**Error:** {self.error}"

        if include_metadata:
            parts.append(f"## {self.target_type.title()}: `{self.target_name}`")
            parts.append("")
            parts.append(f"**Language:** {self.language}")
            if self.file_path:
                parts.append(f"**File:** `{self.file_path}`")
            parts.append(f"**Lines:** {self.start_line}-{self.end_line} ({self.line_count} lines)")
            parts.append(f"**Token Estimate:** ~{self.token_estimate}")
            if self.dependencies:
                parts.append(f"**Dependencies:** {', '.join(f'`{d}`' for d in self.dependencies)}")
            if self.imports_needed:
                parts.append(f"**Imports:** {', '.join(f'`{i}`' for i in self.imports_needed)}")
            parts.append("")

        # Add context if present
        if self.context_code:
            parts.append("### Context")
            parts.append("")
            parts.append(f"```{self.language}")
            parts.append(self.context_code)
            parts.append("```")
            parts.append("")
            parts.append("### Code")
            parts.append("")

        # Main code block
        parts.append(f"```{self.language}")
        parts.append(self.code)
        parts.append("```")

        return "\n".join(parts)

    def to_prompt(self, instruction: str | None = None) -> str:
        """
        Format extraction for LLM prompt consumption.

        [20251221_FEATURE] Token-efficient format for AI agents.

        Args:
            instruction: Optional instruction to prepend

        Returns:
            LLM-ready prompt string
        """
        parts = []

        if instruction:
            parts.append(instruction)
            parts.append("")

        if not self.success:
            return f"Error extracting {self.target_name}: {self.error}"

        # Compact header
        header = f"# {self.target_type}: {self.target_name}"
        if self.file_path:
            header += f" (from {Path(self.file_path).name})"
        parts.append(header)

        # Context first if present
        if self.context_code:
            parts.append("")
            parts.append("## Dependencies:")
            parts.append(self.context_code)

        # Main code
        parts.append("")
        parts.append(self.code)

        # Dependencies hint
        if self.dependencies and not self.context_code:
            parts.append("")
            parts.append(f"# Uses: {', '.join(self.dependencies)}")

        return "\n".join(parts)

    # - has_documentation: bool - Whether docstring exists
    # - is_complex: bool - Whether complexity exceeds threshold


def detect_language(file_path: str | None = None, code: str | None = None) -> Language:
    """
    Detect programming language from file path or code content.

    [20251221_FEATURE] Language detection with fallback chain.

    Args:
        file_path: Optional file path for extension-based detection
        code: Optional code content for heuristic detection

    Returns:
        Detected Language enum value
    """
    # Try file extension first
    if file_path:
        ext = Path(file_path).suffix.lower()
        ext_map = {
            ".py": Language.PYTHON,
            ".pyw": Language.PYTHON,
            ".pyi": Language.PYTHON,
            ".js": Language.JAVASCRIPT,
            ".mjs": Language.JAVASCRIPT,
            ".cjs": Language.JAVASCRIPT,
            ".jsx": Language.JAVASCRIPT,
            ".ts": Language.TYPESCRIPT,
            ".mts": Language.TYPESCRIPT,
            ".cts": Language.TYPESCRIPT,
            ".tsx": Language.TYPESCRIPT,
            ".java": Language.JAVA,
            ".go": Language.GO,
            ".cs": Language.CSHARP,
            ".cpp": Language.CPP,
            ".cc": Language.CPP,
            ".cxx": Language.CPP,
            ".hpp": Language.CPP,
            ".h": Language.CPP,
            ".kt": Language.KOTLIN,
            ".kts": Language.KOTLIN,
            ".rb": Language.RUBY,
            ".swift": Language.SWIFT,
            ".php": Language.PHP,
        }
        if ext in ext_map:
            return ext_map[ext]

    # Try shebang line detection
    if code:
        first_line = code.split("\n", 1)[0].strip()
        if first_line.startswith("#!"):
            shebang = first_line.lower()
            if "python" in shebang:
                return Language.PYTHON
            elif "node" in shebang or "nodejs" in shebang:
                return Language.JAVASCRIPT
            elif "ruby" in shebang:
                return Language.RUBY
            elif "php" in shebang:
                return Language.PHP

    # Try code heuristics
    if code:
        # Python indicators
        if "def " in code or "import " in code or "class " in code:
            if "function " not in code and "var " not in code:
                return Language.PYTHON

        # JavaScript/TypeScript indicators
        if "function " in code or "const " in code or "let " in code:
            if ": " in code and "interface " in code:
                return Language.TYPESCRIPT
            return Language.JAVASCRIPT

        # Java indicators
        if "public class " in code or "private class " in code:
            return Language.JAVA

        # Go indicators
        if "package " in code and "func " in code:
            return Language.GO

        # Ruby indicators
        if "def " in code and "end" in code and "require " in code:
            return Language.RUBY

    # Default to Python for backward compatibility
    return Language.PYTHON


class UnifiedExtractor:
    """
    Universal code extractor for all supported languages.

    [20251221_FEATURE] v3.1.0 - Single interface consolidating:
        - surgical_extractor (Python)
        - polyglot (JS/TS/Java)
        - code_parser (future: Go, C#, C++, etc.)

    Architecture:
        This is a ROUTING LAYER that delegates to language-specific
        extractors. It does not duplicate parsing logic.

    Example:
        >>> extractor = UnifiedExtractor.from_file("utils.py")
        >>> result = extractor.extract("function", "calculate_tax")
        >>> print(result.code)

    ============================================

    Core Extraction:

    Context & Dependencies:

    Search & Discovery:

    Multi-File Operations:

    Output Formatting:

    Performance:
    """

    def __init__(
        self,
        code: str,
        file_path: str | None = None,
        language: Language = Language.AUTO,
    ):
        """
        Initialize the unified extractor.

        Args:
            code: Source code to analyze
            file_path: Optional path to source file
            language: Language to use (AUTO for auto-detection)
        """
        self.code = code
        self.file_path = file_path

        if language == Language.AUTO:
            self.language = detect_language(file_path, code)
        else:
            self.language = language

        self._impl = None  # Lazy-loaded language-specific implementation

    @classmethod
    def from_file(cls, file_path: str, language: Language = Language.AUTO, encoding: str = "utf-8") -> UnifiedExtractor:
        """
        Create extractor by reading from file.

        [20251221_FEATURE] Token-efficient mode - Agent specifies path,
        server reads file (0 token cost to Agent).

        Args:
            file_path: Path to source file
            language: Language override (AUTO to detect from extension)
            encoding: File encoding

        Returns:
            UnifiedExtractor instance
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        code = path.read_text(encoding=encoding)
        return cls(code, file_path=str(path.resolve()), language=language)

    def list_symbols(self, symbol_types: list[str] | None = None) -> list[SymbolInfo]:
        """
        List all extractable symbols in the code.

        [20251221_FEATURE] Symbol discovery for exploration and tooling.

        Args:
            symbol_types: Filter by type(s), e.g., ["function", "class"]
                         If None, returns all symbol types.

        Returns:
            List of SymbolInfo objects describing each symbol

        Example:
            >>> extractor = UnifiedExtractor.from_file("utils.py")
            >>> symbols = extractor.list_symbols(["function"])
            >>> for sym in symbols:
            ...     print(f"{sym.name} at line {sym.line_start}")
        """
        if self.language == Language.PYTHON:
            return self._list_symbols_python(symbol_types)
        elif self.language in (Language.JAVASCRIPT, Language.TYPESCRIPT, Language.JAVA):
            return self._list_symbols_polyglot(symbol_types)
        else:
            return []  # Not yet implemented for other languages

    def _list_symbols_python(self, symbol_types: list[str] | None) -> list[SymbolInfo]:
        """List symbols in Python code."""
        import ast

        symbols: list[SymbolInfo] = []

        # [20260119_REFACTOR] Use unified parser for deterministic behavior
        try:
            from code_scalpel.parsing import ParsingError, parse_python_code

            tree, _ = parse_python_code(self.code, filename=self.file_path or None)
        except (ParsingError, SyntaxError):
            return symbols

        # Track current class for method detection
        class SymbolVisitor(ast.NodeVisitor):
            def __init__(self):
                self.current_class: str | None = None

            def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
                if symbol_types and "function" not in symbol_types and "method" not in symbol_types:
                    self.generic_visit(node)
                    return

                decorators = [self._get_decorator_name(d) for d in node.decorator_list]
                is_method = self.current_class is not None
                sym_type = "method" if is_method else "function"

                if symbol_types is None or sym_type in symbol_types:
                    symbols.append(
                        SymbolInfo(
                            name=node.name,
                            symbol_type=sym_type,
                            line_start=node.lineno,
                            line_end=getattr(node, "end_lineno", node.lineno),
                            parent=self.current_class,
                            is_async=False,
                            decorators=decorators,
                        )
                    )
                self.generic_visit(node)

            def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
                if symbol_types and "function" not in symbol_types and "method" not in symbol_types:
                    self.generic_visit(node)
                    return

                decorators = [self._get_decorator_name(d) for d in node.decorator_list]
                is_method = self.current_class is not None
                sym_type = "method" if is_method else "function"

                if symbol_types is None or sym_type in symbol_types:
                    symbols.append(
                        SymbolInfo(
                            name=node.name,
                            symbol_type=sym_type,
                            line_start=node.lineno,
                            line_end=getattr(node, "end_lineno", node.lineno),
                            parent=self.current_class,
                            is_async=True,
                            decorators=decorators,
                        )
                    )
                self.generic_visit(node)

            def visit_ClassDef(self, node: ast.ClassDef) -> None:
                if symbol_types is None or "class" in symbol_types:
                    decorators = [self._get_decorator_name(d) for d in node.decorator_list]
                    symbols.append(
                        SymbolInfo(
                            name=node.name,
                            symbol_type="class",
                            line_start=node.lineno,
                            line_end=getattr(node, "end_lineno", node.lineno),
                            decorators=decorators,
                        )
                    )

                # Visit methods inside class
                old_class = self.current_class
                self.current_class = node.name
                self.generic_visit(node)
                self.current_class = old_class

            def _get_decorator_name(self, node: ast.expr) -> str:
                if isinstance(node, ast.Name):
                    return node.id
                elif isinstance(node, ast.Attribute):
                    return node.attr
                elif isinstance(node, ast.Call):
                    return self._get_decorator_name(node.func)
                return "unknown"

        visitor = SymbolVisitor()
        visitor.visit(tree)
        return symbols

    def _list_symbols_polyglot(self, symbol_types: list[str] | None) -> list[SymbolInfo]:
        """List symbols in JS/TS/Java code."""
        # Delegate to polyglot if available
        try:
            from code_scalpel.polyglot import Language as PolyglotLang
            from code_scalpel.polyglot import PolyglotExtractor

            lang_map = {
                Language.JAVASCRIPT: PolyglotLang.JAVASCRIPT,
                Language.TYPESCRIPT: PolyglotLang.TYPESCRIPT,
                Language.JAVA: PolyglotLang.JAVA,
            }

            poly = PolyglotExtractor(self.code, self.file_path, lang_map[self.language])
            # Use polyglot's list_symbols if available
            list_symbols_method = getattr(poly, "list_symbols", None)
            if list_symbols_method is not None:
                return list_symbols_method(symbol_types)  # type: ignore[no-any-return]
        except ImportError:
            pass

        return []  # Fallback: not implemented

    def extract_multiple(
        self,
        targets: list[tuple[str, str]],
        include_context: bool = False,
    ) -> list[UnifiedExtractionResult]:
        """
        Extract multiple symbols in a single operation.

        [20251221_FEATURE] Batch extraction for efficiency.

        Args:
            targets: List of (target_type, target_name) tuples
                    e.g., [("function", "foo"), ("class", "Bar")]
            include_context: Include context for functions (Python only)

        Returns:
            List of UnifiedExtractionResult, one per target

        Example:
            >>> extractor = UnifiedExtractor.from_file("utils.py")
            >>> results = extractor.extract_multiple([
            ...     ("function", "calculate_tax"),
            ...     ("function", "format_currency"),
            ...     ("class", "TaxCalculator"),
            ... ])
            >>> successful = [r for r in results if r.success]
        """
        results: list[UnifiedExtractionResult] = []
        for target_type, target_name in targets:
            result = self.extract(target_type, target_name, include_context=include_context)
            results.append(result)
        return results

    def extract_by_line(self, line_number: int, include_context: bool = False) -> UnifiedExtractionResult:
        """
        Extract the symbol that contains a specific line number.

        [20251221_FEATURE] Line-based extraction for editor integration.

        Args:
            line_number: 1-indexed line number
            include_context: Include surrounding context (Python only)

        Returns:
            UnifiedExtractionResult for symbol at that line,
            or error result if no symbol found

        Example:
            >>> extractor = UnifiedExtractor.from_file("utils.py")
            >>> # User clicks on line 42, extract that function
            >>> result = extractor.extract_by_line(42)
        """
        symbols = self.list_symbols()

        # Find innermost symbol containing this line
        # (innermost = smallest range, handles nested functions/methods)
        containing: list[SymbolInfo] = [s for s in symbols if s.line_start <= line_number <= s.line_end]

        if not containing:
            return UnifiedExtractionResult(
                success=False,
                target_name="",
                target_type="",
                language=self.language.value,
                error=f"No symbol found at line {line_number}",
            )

        # Pick the innermost (smallest range)
        best = min(containing, key=lambda s: s.line_end - s.line_start)

        return self.extract(
            best.symbol_type,
            best.qualified_name,
            include_context=include_context,
        )

    def find_by_type(self, symbol_type: str) -> list[SymbolInfo]:
        """
        Find all symbols of a specific type.

        [20251221_FEATURE] Type-filtered symbol discovery.

        Args:
            symbol_type: "function", "class", or "method"

        Returns:
            List of matching SymbolInfo objects
        """
        return self.list_symbols([symbol_type])

    def extract_all_of_type(self, symbol_type: str, include_context: bool = False) -> list[UnifiedExtractionResult]:
        """
        Extract all symbols of a specific type.

        [20251221_FEATURE] Bulk extraction by type.

        Args:
            symbol_type: "function", "class", or "method"
            include_context: Include context (Python only)

        Returns:
            List of extraction results

        Example:
            >>> extractor = UnifiedExtractor.from_file("utils.py")
            >>> all_functions = extractor.extract_all_of_type("function")
        """
        symbols = self.find_by_type(symbol_type)
        targets = [(s.symbol_type, s.qualified_name) for s in symbols]
        return self.extract_multiple(targets, include_context=include_context)

    def get_imports(self) -> list[ImportInfo]:
        """
        Get all import statements in the code.

        [20251221_FEATURE] Import analysis for dependency tracking.

        Returns:
            List of ImportInfo objects

        Example:
            >>> extractor = UnifiedExtractor.from_file("utils.py")
            >>> imports = extractor.get_imports()
            >>> for imp in imports:
            ...     print(imp.import_statement)
        """
        if self.language == Language.PYTHON:
            return self._get_imports_python()
        # Future: Add JS/TS import detection
        return []

    def _get_imports_python(self) -> list[ImportInfo]:
        """Get imports from Python code."""
        import ast

        imports: list[ImportInfo] = []

        # [20260119_REFACTOR] Use unified parser for deterministic behavior
        try:
            from code_scalpel.parsing import ParsingError, parse_python_code

            tree, _ = parse_python_code(self.code, filename=self.file_path or None)
        except (ParsingError, SyntaxError):
            return imports

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(
                        ImportInfo(
                            module=alias.name,
                            alias=alias.asname,
                            is_from_import=False,
                            line_number=node.lineno,
                        )
                    )
            elif isinstance(node, ast.ImportFrom):
                names = [alias.name for alias in node.names]
                imports.append(
                    ImportInfo(
                        module=node.module or "",
                        names=names,
                        is_from_import=True,
                        is_relative=node.level > 0,
                        level=node.level,
                        line_number=node.lineno,
                    )
                )

        return imports

    def get_summary(self) -> FileSummary:
        """
        Get a quick summary of the file structure.

        [20251221_FEATURE] Fast overview without full extraction.

        Returns:
            FileSummary with counts and symbol list

        Example:
            >>> extractor = UnifiedExtractor.from_file("utils.py")
            >>> summary = extractor.get_summary()
            >>> print(f"{summary.num_functions} functions, {summary.num_classes} classes")
        """
        symbols = self.list_symbols()
        imports = self.get_imports()

        num_functions = sum(1 for s in symbols if s.symbol_type == "function")
        num_classes = sum(1 for s in symbols if s.symbol_type == "class")
        num_methods = sum(1 for s in symbols if s.symbol_type == "method")

        return FileSummary(
            file_path=self.file_path,
            language=self.language.value,
            total_lines=len(self.code.splitlines()),
            num_functions=num_functions,
            num_classes=num_classes,
            num_methods=num_methods,
            num_imports=len(imports),
            symbols=symbols,
            imports=imports,
        )

    def find_by_decorator(self, decorator_name: str) -> list[SymbolInfo]:
        """
        Find all symbols with a specific decorator.

        [20251221_FEATURE] Decorator-based symbol discovery.

        Args:
            decorator_name: Name of decorator (e.g., "property", "staticmethod",
                          "pytest.fixture", "app.route")

        Returns:
            List of SymbolInfo objects with the specified decorator

        Example:
            >>> extractor = UnifiedExtractor.from_file("test_utils.py")
            >>> fixtures = extractor.find_by_decorator("pytest.fixture")
            >>> routes = extractor.find_by_decorator("app.route")
        """
        symbols = self.list_symbols()
        return [s for s in symbols if any(decorator_name in d or d == decorator_name for d in s.decorators)]

    def extract_signatures(self, symbol_types: list[str] | None = None) -> list[SignatureInfo]:
        """
        Extract function/method signatures without full code.

        [20251221_FEATURE] Lightweight extraction for API documentation.

        Args:
            symbol_types: Filter by type(s), defaults to ["function", "method"]

        Returns:
            List of SignatureInfo objects

        Example:
            >>> extractor = UnifiedExtractor.from_file("utils.py")
            >>> sigs = extractor.extract_signatures()
            >>> for sig in sigs:
            ...     print(sig.signature_string)
            >>> # Generate stubs
            >>> stubs = "\n\n".join(sig.to_stub() for sig in sigs)
        """
        if self.language == Language.PYTHON:
            return self._extract_signatures_python(symbol_types)
        return []

    def _extract_signatures_python(self, symbol_types: list[str] | None) -> list[SignatureInfo]:
        """Extract signatures from Python code."""
        import ast

        if symbol_types is None:
            symbol_types = ["function", "method"]

        signatures: list[SignatureInfo] = []

        # [20260119_REFACTOR] Use unified parser for deterministic behavior
        try:
            from code_scalpel.parsing import ParsingError, parse_python_code

            tree, _ = parse_python_code(self.code, filename=self.file_path or None)
        except (ParsingError, SyntaxError):
            return signatures

        class SignatureVisitor(ast.NodeVisitor):
            def __init__(self):
                self.current_class: str | None = None

            def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
                self._process_function(node, is_async=False)
                self.generic_visit(node)

            def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
                self._process_function(node, is_async=True)
                self.generic_visit(node)

            def visit_ClassDef(self, node: ast.ClassDef) -> None:
                old_class = self.current_class
                self.current_class = node.name
                self.generic_visit(node)
                self.current_class = old_class

            def _process_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef, is_async: bool) -> None:
                is_method = self.current_class is not None
                sym_type = "method" if is_method else "function"

                if sym_type not in symbol_types:
                    return

                # Extract parameters
                params = self._get_params(node.args)

                # Extract return type
                return_type = None
                if node.returns:
                    return_type = ast.unparse(node.returns)

                # Extract decorators
                decorators = [self._get_decorator_str(d) for d in node.decorator_list]

                # Extract docstring
                docstring = ast.get_docstring(node)

                qualified = f"{self.current_class}.{node.name}" if self.current_class else node.name

                signatures.append(
                    SignatureInfo(
                        name=node.name,
                        qualified_name=qualified,
                        parameters=params,
                        return_type=return_type,
                        decorators=decorators,
                        is_async=is_async,
                        docstring=docstring,
                        line_number=node.lineno,
                    )
                )

            def _get_params(self, args: ast.arguments) -> list[str]:
                """Extract parameter strings with type hints."""
                params = []

                # Regular args
                defaults_offset = len(args.args) - len(args.defaults)
                for i, arg in enumerate(args.args):
                    param = arg.arg
                    if arg.annotation:
                        param += f": {ast.unparse(arg.annotation)}"
                    # Add default if exists
                    default_idx = i - defaults_offset
                    if default_idx >= 0:
                        param += f" = {ast.unparse(args.defaults[default_idx])}"
                    params.append(param)

                # *args
                if args.vararg:
                    param = f"*{args.vararg.arg}"
                    if args.vararg.annotation:
                        param += f": {ast.unparse(args.vararg.annotation)}"
                    params.append(param)

                # Keyword-only args
                kw_defaults = args.kw_defaults
                for i, arg in enumerate(args.kwonlyargs):
                    param = arg.arg
                    if arg.annotation:
                        param += f": {ast.unparse(arg.annotation)}"
                    default = kw_defaults[i]
                    if default is not None:
                        param += f" = {ast.unparse(default)}"
                    params.append(param)

                # **kwargs
                if args.kwarg:
                    param = f"**{args.kwarg.arg}"
                    if args.kwarg.annotation:
                        param += f": {ast.unparse(args.kwarg.annotation)}"
                    params.append(param)

                return params

            def _get_decorator_str(self, node: ast.expr) -> str:
                """Get decorator as string."""
                return ast.unparse(node)

        visitor = SignatureVisitor()
        visitor.visit(tree)
        return signatures

    def get_docstring(self, target_type: str, target_name: str) -> str | None:
        """
        Get just the docstring for a symbol.

        [20251221_FEATURE] Lightweight docstring extraction.

        Args:
            target_type: "function", "class", or "method"
            target_name: Name of symbol (use "ClassName.method" for methods)

        Returns:
            Docstring if present, None otherwise

        Example:
            >>> extractor = UnifiedExtractor.from_file("utils.py")
            >>> doc = extractor.get_docstring("function", "calculate_tax")
        """
        if self.language == Language.PYTHON:
            return self._get_docstring_python(target_type, target_name)
        return None

    def _get_docstring_python(self, target_type: str, target_name: str) -> str | None:
        """Get docstring from Python code."""
        import ast

        # [20260119_REFACTOR] Use unified parser for deterministic behavior
        try:
            from code_scalpel.parsing import ParsingError, parse_python_code

            tree, _ = parse_python_code(self.code, filename=self.file_path or None)
        except (ParsingError, SyntaxError):
            return None

        # Handle method names
        class_name = None
        method_name = target_name
        if "." in target_name:
            class_name, method_name = target_name.split(".", 1)

        for node in ast.walk(tree):
            if target_type == "class" and isinstance(node, ast.ClassDef):
                if node.name == target_name:
                    return ast.get_docstring(node)

            elif target_type == "function" and isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name == target_name:
                    return ast.get_docstring(node)

            elif target_type == "method" and isinstance(node, ast.ClassDef):
                if node.name == class_name:
                    for item in node.body:
                        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            if item.name == method_name:
                                return ast.get_docstring(item)

        return None

    def generate_stubs(self) -> str:
        """
        Generate .pyi stub file content.

        [20251221_FEATURE] Type stub generation from code.

        Returns:
            String containing .pyi stub content

        Example:
            >>> extractor = UnifiedExtractor.from_file("utils.py")
            >>> stubs = extractor.generate_stubs()
            >>> Path("utils.pyi").write_text(stubs)
        """
        if self.language != Language.PYTHON:
            return "# Stub generation only supported for Python\n"

        lines = []
        lines.append("# Auto-generated type stubs")
        lines.append("# Generated by Code Scalpel")
        lines.append("")

        # Add imports for typing
        lines.append("from typing import Any, Optional")
        lines.append("")

        signatures = self.extract_signatures()
        current_class: str | None = None

        for sig in signatures:
            # Check if we need to start/end a class
            if "." in sig.qualified_name:
                cls_name = sig.qualified_name.split(".")[0]
                if cls_name != current_class:
                    if current_class is not None:
                        lines.append("")  # End previous class
                    lines.append(f"class {cls_name}:")
                    current_class = cls_name
                # Indent method
                stub = sig.to_stub()
                for line in stub.split("\n"):
                    lines.append(f"    {line}")
            else:
                if current_class is not None:
                    lines.append("")  # End previous class
                    current_class = None
                lines.append(sig.to_stub())
            lines.append("")

        return "\n".join(lines)

    def extract(
        self,
        target_type: str,
        target_name: str,
        include_context: bool = False,
        include_dependencies: bool = False,
    ) -> UnifiedExtractionResult:
        """
        Extract a code element by type and name.

        [20251221_FEATURE] Unified extraction across all supported languages.

        Args:
            target_type: "function", "class", "method"
            target_name: Name of element. For methods: "ClassName.methodName"
            include_context: Include surrounding context (Python only)
            include_dependencies: Include dependencies (Python only)

        Returns:
            UnifiedExtractionResult with extracted code
        """
        if self.language == Language.PYTHON:
            return self._extract_python(target_type, target_name, include_context)
        elif self.language in (Language.JAVASCRIPT, Language.TYPESCRIPT, Language.JAVA):
            return self._extract_polyglot(target_type, target_name)
        else:
            # Future: Route to code_parser for other languages
            return self._extract_via_code_parser(target_type, target_name)

    def _extract_python(self, target_type: str, target_name: str, include_context: bool) -> UnifiedExtractionResult:
        """
        Extract from Python code using surgical_extractor.

        [20251221_FEATURE] Delegates to surgical_extractor for rich Python support
        including cross-file dependency resolution.

        """
        from code_scalpel.surgical_extractor import ExtractionResult, SurgicalExtractor

        try:
            extractor = SurgicalExtractor(self.code, self.file_path)

            # Handle contextual extraction separately due to different return type
            if target_type == "function" and include_context:
                ctx_result = extractor.get_function_with_context(target_name)
                # ContextualExtraction has .target (ExtractionResult) and .context_code
                if not ctx_result.target.success:
                    return UnifiedExtractionResult(
                        success=False,
                        target_name=target_name,
                        target_type=target_type,
                        language=self.language.value,
                        error=ctx_result.target.error or f"{target_type} '{target_name}' not found",
                    )
                return UnifiedExtractionResult(
                    success=True,
                    target_name=target_name,
                    target_type=target_type,
                    language=self.language.value,
                    code=ctx_result.target.code,
                    start_line=ctx_result.target.line_start,
                    end_line=ctx_result.target.line_end,
                    dependencies=ctx_result.target.dependencies,
                    imports_needed=ctx_result.target.imports_needed,
                    file_path=self.file_path,
                    token_estimate=ctx_result.token_estimate,
                    context_code=ctx_result.context_code,
                    context_items=ctx_result.context_items,
                )

            # Standard extraction (returns ExtractionResult)
            result: ExtractionResult
            if target_type == "function":
                result = extractor.get_function(target_name)
            elif target_type == "class":
                result = extractor.get_class(target_name)
            elif target_type == "method":
                if "." in target_name:
                    class_name, method_name = target_name.split(".", 1)
                    result = extractor.get_method(class_name, method_name)
                else:
                    return UnifiedExtractionResult(
                        success=False,
                        target_name=target_name,
                        target_type=target_type,
                        language=self.language.value,
                        error="Method extraction requires 'ClassName.methodName' format",
                    )
            else:
                return UnifiedExtractionResult(
                    success=False,
                    target_name=target_name,
                    target_type=target_type,
                    language=self.language.value,
                    error=f"Unsupported target_type for Python: {target_type}",
                )

            if not result.success:
                return UnifiedExtractionResult(
                    success=False,
                    target_name=target_name,
                    target_type=target_type,
                    language=self.language.value,
                    error=result.error or f"{target_type} '{target_name}' not found",
                )

            return UnifiedExtractionResult(
                success=True,
                target_name=target_name,
                target_type=target_type,
                language=self.language.value,
                code=result.code,
                start_line=result.line_start,
                end_line=result.line_end,
                dependencies=result.dependencies,
                imports_needed=result.imports_needed,
                file_path=self.file_path,
                token_estimate=len(result.code) // 4,
            )

        except Exception as e:
            return UnifiedExtractionResult(
                success=False,
                target_name=target_name,
                target_type=target_type,
                language=self.language.value,
                error=str(e),
            )

    def _extract_polyglot(self, target_type: str, target_name: str) -> UnifiedExtractionResult:
        """
        Extract from JS/TS/Java using polyglot extractor.

        [20251221_FEATURE] Delegates to polyglot for JSX/React/IR support.

        """
        # [20251228_BUGFIX] Avoid deprecated code_scalpel.polyglot re-export.
        # Prefer the consolidated implementation in code_parsers/.
        try:
            from code_scalpel.code_parsers import PolyglotExtractor
            from code_scalpel.code_parsers import PolyglotLanguage as PolyglotLang
        except Exception:  # pragma: no cover
            from code_scalpel.polyglot import Language as PolyglotLang
            from code_scalpel.polyglot import PolyglotExtractor

        try:
            # Map unified language to polyglot language
            lang_map = {
                Language.JAVASCRIPT: PolyglotLang.JAVASCRIPT,
                Language.TYPESCRIPT: PolyglotLang.TYPESCRIPT,
                Language.JAVA: PolyglotLang.JAVA,
            }

            polyglot_extractor = PolyglotExtractor(self.code, self.file_path, lang_map[self.language])

            result = polyglot_extractor.extract(target_type, target_name)

            if not result.success:
                return UnifiedExtractionResult(
                    success=False,
                    target_name=target_name,
                    target_type=target_type,
                    language=self.language.value,
                    error=result.error,
                )

            return UnifiedExtractionResult(
                success=True,
                target_name=target_name,
                target_type=target_type,
                language=self.language.value,
                code=result.code,
                start_line=result.start_line,
                end_line=result.end_line,
                dependencies=result.dependencies,
                file_path=self.file_path,
                token_estimate=result.token_estimate,
                jsx_normalized=result.jsx_normalized,
                is_server_component=result.is_server_component,
                is_server_action=result.is_server_action,
                component_type=result.component_type,
            )

        except Exception as e:
            return UnifiedExtractionResult(
                success=False,
                target_name=target_name,
                target_type=target_type,
                language=self.language.value,
                error=str(e),
            )

    def _extract_via_code_parser(self, target_type: str, target_name: str) -> UnifiedExtractionResult:
        """
        Extract using code_parser for languages not yet supported.

        [20251221_FEATURE] Placeholder for future language support.
        Will use code_parser once extraction methods are added.

        """
        return UnifiedExtractionResult(
            success=False,
            target_name=target_name,
            target_type=target_type,
            language=self.language.value,
            error=f"Language {self.language.value} extraction not yet implemented. "
            f"Supported: Python, JavaScript, TypeScript, Java",
        )


# Convenience functions for backward compatibility
def extract_from_file(
    file_path: str,
    target_type: str,
    target_name: str,
    language: Language = Language.AUTO,
) -> UnifiedExtractionResult:
    """
    Extract code element from a file.

    [20251221_FEATURE] Convenience function for single-call extraction.

    Args:
        file_path: Path to source file
        target_type: "function", "class", "method"
        target_name: Name of element
        language: Language override (AUTO to detect)

    Returns:
        UnifiedExtractionResult
    """
    extractor = UnifiedExtractor.from_file(file_path, language)
    return extractor.extract(target_type, target_name)


def extract_from_code(
    code: str,
    target_type: str,
    target_name: str,
    language: Language = Language.PYTHON,
) -> UnifiedExtractionResult:
    """
    Extract code element from code string.

    [20251221_FEATURE] Convenience function for single-call extraction.

    Args:
        code: Source code
        target_type: "function", "class", "method"
        target_name: Name of element
        language: Language (must specify, cannot auto-detect)

    Returns:
        UnifiedExtractionResult
    """
    extractor = UnifiedExtractor(code, language=language)
    return extractor.extract(target_type, target_name)


__all__ = [
    "UnifiedExtractor",
    "UnifiedExtractionResult",
    "SymbolInfo",
    "ImportInfo",
    "FileSummary",
    "SignatureInfo",
    "Language",
    "detect_language",
    "extract_from_file",
    "extract_from_code",
]
