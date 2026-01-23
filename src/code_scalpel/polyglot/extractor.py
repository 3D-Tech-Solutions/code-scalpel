"""
Polyglot Code Extractor - Multi-language surgical code extraction.

[20251214_FEATURE] v2.0.0 - Multi-language support for extract_code MCP tool.

This module provides a unified interface for extracting code elements
(functions, classes, methods) from Python, TypeScript, JavaScript, and Java.

Architecture:
    1. Language detection (from file extension or explicit parameter)
    2. Language-specific parsing (Python ast, tree-sitter for others)
    3. Normalization to Unified IR
    4. Extraction from IR (language-agnostic)
    5. Source code retrieval using line numbers from IR

Supported Languages:
    - Python: Full support via ast module
    - JavaScript: Full support via tree-sitter-javascript
    - TypeScript: Full support via tree-sitter-typescript (planned)
    - Java: Full support via tree-sitter-java




"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

# [20251215_REFACTOR] Remove unused typing import for lint compliance.


# [20251214_FEATURE] Language enum for explicit language specification
class Language(Enum):
    """Supported programming languages."""

    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    JAVA = "java"
    AUTO = "auto"  # Auto-detect from file extension


# [20251214_FEATURE] File extension to language mapping
EXTENSION_MAP: dict[str, Language] = {
    ".py": Language.PYTHON,
    ".pyw": Language.PYTHON,
    ".js": Language.JAVASCRIPT,
    ".mjs": Language.JAVASCRIPT,
    ".cjs": Language.JAVASCRIPT,
    ".jsx": Language.JAVASCRIPT,
    ".ts": Language.TYPESCRIPT,
    ".tsx": Language.TYPESCRIPT,
    ".mts": Language.TYPESCRIPT,
    ".cts": Language.TYPESCRIPT,
    ".java": Language.JAVA,
}


@dataclass
class PolyglotExtractionResult:
    """Result of polyglot code extraction."""

    success: bool
    code: str = ""
    language: str = "unknown"
    target_type: str = ""
    target_name: str = ""
    start_line: int = 0
    end_line: int = 0
    dependencies: list[str] = field(default_factory=list)
    error: str | None = None

    # Metadata
    file_path: str | None = None
    token_estimate: int = 0

    # [20251216_FEATURE] v2.0.2 - JSX/TSX metadata
    jsx_normalized: bool = False
    is_server_component: bool = False
    is_server_action: bool = False
    component_type: str | None = None


def detect_language(file_path: str | None, code: str | None = None) -> Language:
    """
    Detect the programming language from file extension or content.

    [20251214_FEATURE] Auto-detection for polyglot support.

    Args:
        file_path: Path to the source file
        code: Source code string (for content-based detection)

    Returns:
        Detected Language enum value
    """
    if file_path:
        ext = Path(file_path).suffix.lower()
        if ext in EXTENSION_MAP:
            return EXTENSION_MAP[ext]

    # Content-based detection (heuristics)
    if code:
        # TypeScript indicators - check first as it's more specific
        # [20251214_BUGFIX] Better TypeScript detection - interface/type keywords are TS-specific
        if any(
            kw in code
            for kw in [
                "interface ",
                "type ",
                ": string",
                ": number",
                ": boolean",
                ": any",
            ]
        ):
            return Language.TYPESCRIPT

        # Java indicators
        if "public class " in code or "private class " in code or "package " in code:
            return Language.JAVA

        # JavaScript indicators (after ruling out TS)
        if any(kw in code for kw in ["function ", "const ", "let ", "var ", "=>"]):
            return Language.JAVASCRIPT

        # Default to Python
        if "def " in code or "class " in code or "import " in code:
            return Language.PYTHON

    return Language.PYTHON  # Default


class PolyglotExtractor:
    """
    Multi-language code extractor.

    [20251214_FEATURE] Unified interface for extracting code from any supported language.

    Example (Python):
        >>> extractor = PolyglotExtractor.from_file("utils.py")
        >>> result = extractor.extract("function", "calculate_tax")

    Example (JavaScript):
        >>> extractor = PolyglotExtractor.from_file("utils.js")
        >>> result = extractor.extract("function", "calculateTax")

    Example (Java):
        >>> extractor = PolyglotExtractor.from_file("Utils.java")
        >>> result = extractor.extract("method", "Calculator.add")
    """

    def __init__(
        self,
        code: str,
        file_path: str | None = None,
        language: Language = Language.AUTO,
    ):
        """
        Initialize the polyglot extractor.

        Args:
            code: Source code to analyze
            file_path: Optional path to source file
            language: Language to use (AUTO for auto-detection)
        """
        self.code = code
        self.file_path = file_path
        self.source_lines = code.splitlines()

        # Detect language if AUTO
        if language == Language.AUTO:
            self.language = detect_language(file_path, code)
        else:
            self.language = language

        # Language-specific state
        self._ir_module = None
        self._parsed = False

    @classmethod
    def from_file(
        cls, file_path: str, language: Language = Language.AUTO, encoding: str = "utf-8"
    ) -> "PolyglotExtractor":
        """
        Create extractor by reading from file.

        [20251214_FEATURE] Token-efficient mode - Agent specifies path,
        server reads file (0 token cost to Agent).

        Args:
            file_path: Path to source file
            language: Language override (AUTO to detect from extension)
            encoding: File encoding

        Returns:
            PolyglotExtractor instance
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        code = path.read_text(encoding=encoding)
        return cls(code, file_path=str(path.resolve()), language=language)

    def _parse(self) -> None:
        """Parse source code into IR."""
        if self._parsed:
            return

        if self.language == Language.PYTHON:
            self._parse_python()
        elif self.language == Language.JAVASCRIPT:
            self._parse_javascript()
        elif self.language == Language.TYPESCRIPT:
            self._parse_typescript()
        elif self.language == Language.JAVA:
            self._parse_java()
        else:
            raise ValueError(f"Unsupported language: {self.language}")

        self._parsed = True

    def _parse_python(self) -> None:
        """Parse Python code using ast module."""
        # Delegate to existing SurgicalExtractor for Python
        from code_scalpel.surgical_extractor import SurgicalExtractor

        self._python_extractor = SurgicalExtractor(self.code, self.file_path)

    def _parse_javascript(self) -> None:
        """
        Parse JavaScript code using tree-sitter.

        [20251215_FEATURE] v2.0.0 P1 - JSX support via TSX parser.
        For .jsx files, use TSX parser which handles JSX syntax.
        """
        # Check if this is a JSX file
        is_jsx = self.file_path and self.file_path.endswith(".jsx")

        if is_jsx:
            # Use TSX normalizer for JSX files (TSX parser handles JSX syntax)
            from code_scalpel.ir.normalizers.typescript_normalizer import (
                TypeScriptTSXNormalizer,
            )

            normalizer = TypeScriptTSXNormalizer()
        else:
            from code_scalpel.ir.normalizers.javascript_normalizer import (
                JavaScriptNormalizer,
            )

            normalizer = JavaScriptNormalizer()

        self._ir_module = normalizer.normalize(self.code)

    def _parse_typescript(self) -> None:
        """
        Parse TypeScript code using tree-sitter-typescript.

        [20251215_FEATURE] v2.0.0 P1 - TSX support for React TypeScript files.
        For .tsx files, use TSX-specific normalizer with JSX handlers.

        [20251215_BUGFIX] v2.0.1 - Auto-detect JSX in code content when no file path.
        """
        # Check if this is a TSX file by extension
        is_tsx = self.file_path and self.file_path.endswith(".tsx")

        # [20251215_BUGFIX] Also detect JSX syntax in code content
        # This handles cases where code is passed directly without file_path
        if not is_tsx and "</" in self.code:
            # Check for JSX patterns: <Component>, <tag>, </tag>, </>
            import re

            jsx_pattern = r"<[A-Za-z][A-Za-z0-9]*[\s/>]|</[A-Za-z]|<>"
            if re.search(jsx_pattern, self.code):
                is_tsx = True

        if is_tsx:
            from code_scalpel.ir.normalizers.typescript_normalizer import (
                TypeScriptTSXNormalizer,
            )

            normalizer = TypeScriptTSXNormalizer()
        else:
            from code_scalpel.ir.normalizers.typescript_normalizer import (
                TypeScriptNormalizer,
            )

            normalizer = TypeScriptNormalizer()

        self._ir_module = normalizer.normalize(self.code)

    def _parse_java(self) -> None:
        """Parse Java code using tree-sitter."""
        from code_scalpel.ir.normalizers.java_normalizer import JavaNormalizer

        normalizer = JavaNormalizer()
        self._ir_module = normalizer.normalize(self.code)

    def extract(
        self, target_type: str, target_name: str, include_dependencies: bool = False
    ) -> PolyglotExtractionResult:
        """
        Extract a code element by type and name.

        [20251214_FEATURE] Unified extraction across all supported languages.

        Args:
            target_type: "function", "class", "method", "interface", "type"
            target_name: Name of element. For methods: "ClassName.methodName"
            include_dependencies: Include local dependencies

        Returns:
            PolyglotExtractionResult with extracted code
        """
        self._parse()

        # Python uses existing extractor
        if self.language == Language.PYTHON:
            return self._extract_python(target_type, target_name)

        # Other languages use IR-based extraction
        return self._extract_from_ir(target_type, target_name)

    def _extract_python(self, target_type: str, target_name: str) -> PolyglotExtractionResult:
        """Extract from Python code using existing SurgicalExtractor."""
        try:
            if target_type == "function":
                result = self._python_extractor.get_function(target_name)
            elif target_type == "class":
                result = self._python_extractor.get_class(target_name)
            elif target_type == "method":
                if "." in target_name:
                    class_name, method_name = target_name.split(".", 1)
                    result = self._python_extractor.get_method(class_name, method_name)
                else:
                    return PolyglotExtractionResult(
                        success=False,
                        error="Method extraction requires 'ClassName.methodName' format",
                        language=self.language.value,
                        target_type=target_type,
                        target_name=target_name,
                    )
            else:
                return PolyglotExtractionResult(
                    success=False,
                    error=f"Unsupported target_type for Python: {target_type}",
                    language=self.language.value,
                    target_type=target_type,
                    target_name=target_name,
                )

            return PolyglotExtractionResult(
                success=True,
                code=result.code,
                language=self.language.value,
                target_type=target_type,
                target_name=target_name,
                start_line=result.line_start,  # [20251214_BUGFIX] Use correct attribute name
                end_line=result.line_end,  # [20251214_BUGFIX] Use correct attribute name
                dependencies=result.dependencies,
                file_path=self.file_path,
                token_estimate=len(result.code) // 4,
            )
        except Exception as e:
            return PolyglotExtractionResult(
                success=False,
                error=str(e),
                language=self.language.value,
                target_type=target_type,
                target_name=target_name,
            )

    def _extract_from_ir(self, target_type: str, target_name: str) -> PolyglotExtractionResult:
        """
        Extract from IR (for JS/TS/Java).

        [20251214_FEATURE] IR-based extraction for non-Python languages.
        [20251216_BUGFIX] Handle IRExport nodes wrapping functions/classes.
        """
        from code_scalpel.ir.nodes import IRClassDef, IRExport, IRFunctionDef

        if not self._ir_module:
            return PolyglotExtractionResult(
                success=False,
                error="Failed to parse code",
                language=self.language.value,
                target_type=target_type,
                target_name=target_name,
            )

        # Search for target in IR
        target_node = None

        for node in self._ir_module.body:
            # [20251216_BUGFIX] Unwrap IRExport nodes
            actual_node = node.declaration if isinstance(node, IRExport) else node

            if target_type == "function" and isinstance(actual_node, IRFunctionDef):
                if actual_node.name == target_name:
                    target_node = actual_node
                    break
            elif target_type == "class" and isinstance(actual_node, IRClassDef):
                if actual_node.name == target_name:
                    target_node = actual_node
                    break
            elif target_type == "method" and isinstance(actual_node, IRClassDef):
                # Search within class
                if "." in target_name:
                    class_name, method_name = target_name.split(".", 1)
                    if actual_node.name == class_name:
                        for member in actual_node.body:
                            if isinstance(member, IRFunctionDef) and member.name == method_name:
                                target_node = member
                                break

        if not target_node:
            return PolyglotExtractionResult(
                success=False,
                error=f"{target_type} '{target_name}' not found",
                language=self.language.value,
                target_type=target_type,
                target_name=target_name,
            )

        # Extract source lines using location info from IR
        if target_node.loc:
            start_line = target_node.loc.line
            end_line = target_node.loc.end_line or start_line

            # Extract source code
            code_lines = self.source_lines[start_line - 1 : end_line]
            code = "\n".join(code_lines)

            # [20251216_FEATURE] v2.0.2 - Detect React components for TSX/JSX
            jsx_normalized = False
            is_server_component = False
            is_server_action = False
            component_type = None

            if self.language in (Language.TYPESCRIPT, Language.JAVASCRIPT):
                from code_scalpel.polyglot.tsx_analyzer import (
                    is_react_component,
                    normalize_jsx_syntax,
                )

                # Analyze for React component patterns
                react_info = is_react_component(target_node, code)

                # [20251216_BUGFIX] Set metadata even for non-component functions
                # (e.g., Server Actions without JSX)
                component_type = react_info.component_type
                is_server_component = react_info.is_server_component
                is_server_action = react_info.is_server_action

                # Mark as JSX normalized if it has JSX or is a React component
                if react_info.has_jsx or react_info.component_type:
                    jsx_normalized = True
                    # Normalize JSX if present
                    code = normalize_jsx_syntax(code)

            return PolyglotExtractionResult(
                success=True,
                code=code,
                language=self.language.value,
                target_type=target_type,
                target_name=target_name,
                start_line=start_line,
                end_line=end_line,
                file_path=self.file_path,
                token_estimate=len(code) // 4,
                jsx_normalized=jsx_normalized,
                is_server_component=is_server_component,
                is_server_action=is_server_action,
                component_type=component_type,
            )
        else:
            return PolyglotExtractionResult(
                success=False,
                error="No location information in IR node",
                language=self.language.value,
                target_type=target_type,
                target_name=target_name,
            )


# [20251214_FEATURE] Convenience functions
def extract_from_file(
    file_path: str,
    target_type: str,
    target_name: str,
    language: Language = Language.AUTO,
) -> PolyglotExtractionResult:
    """
    Extract code element from a file.

    Args:
        file_path: Path to source file
        target_type: "function", "class", "method"
        target_name: Name of element
        language: Language override (AUTO to detect)

    Returns:
        PolyglotExtractionResult
    """
    extractor = PolyglotExtractor.from_file(file_path, language)
    return extractor.extract(target_type, target_name)


def extract_from_code(
    code: str, target_type: str, target_name: str, language: Language = Language.AUTO
) -> PolyglotExtractionResult:
    """
    Extract code element from source string.

    Args:
        code: Source code string
        target_type: "function", "class", "method"
        target_name: Name of element
        language: Language (AUTO for content-based detection)

    Returns:
        PolyglotExtractionResult
    """
    extractor = PolyglotExtractor(code, language=language)
    return extractor.extract(target_type, target_name)
