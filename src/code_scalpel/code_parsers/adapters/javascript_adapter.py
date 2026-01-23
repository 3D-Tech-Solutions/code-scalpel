from typing import Any

from ..interface import IParser, Language, ParseResult

# Try to import the JavaScript parser
try:
    from ..base_parser import ParseResult as BaseParseResult
    from ..javascript_parsers.javascript_parsers_esprima import (
        JavaScriptParser as EsprimaParser,
    )

    JAVASCRIPT_PARSER_AVAILABLE = True
except ImportError:
    JAVASCRIPT_PARSER_AVAILABLE = False
    EsprimaParser = None  # type: ignore
    BaseParseResult = None  # type: ignore


class JavaScriptParserAdapter(IParser):
    """
    Adapter that wraps JavaScriptParser to implement IParser interface.

    [20251221_FEATURE] Enables JavaScript parsing through unified factory.

    Example:
        >>> adapter = JavaScriptParserAdapter()
        >>> result = adapter.parse("function hello() { return 'world'; }")
        >>> print(result.language)
        Language.JAVASCRIPT
    """

    def __init__(self):
        """Initialize the JavaScript parser adapter."""
        if not JAVASCRIPT_PARSER_AVAILABLE or EsprimaParser is None:
            raise ImportError("JavaScriptParser not available. Install esprima: pip install esprima")
        # Note: JavaScriptParser has an abstract method (parse_code) but we only use
        # its internal _parse_javascript method, so this is safe at runtime
        self._parser: Any = EsprimaParser()  # type: ignore[abstract]
        self._last_ast: Any | None = None
        self._last_functions: list[str] = []
        self._last_classes: list[str] = []

    def parse(self, code: str) -> ParseResult:
        """
        Parse JavaScript code into an AST.

        Args:
            code: JavaScript source code

        Returns:
            ParseResult with AST, errors, warnings, and metrics
        """
        try:
            # Use the underlying parser's internal parse method
            internal_result = self._parser._parse_javascript(code)

            # Cache the AST
            self._last_ast = internal_result.ast

            # Extract names from AST
            self._extract_names_from_ast(internal_result.ast)

            # Convert to IParser ParseResult format
            return ParseResult(
                ast=internal_result.ast,
                errors=self._convert_errors(internal_result.errors),
                warnings=getattr(internal_result, "warnings", []) or [],
                metrics=getattr(internal_result, "metrics", {}) or {},
                language=Language.JAVASCRIPT,
            )
        except Exception as e:
            return ParseResult(
                ast=None,
                errors=[{"message": str(e), "line": 0, "column": 0}],
                warnings=[],
                metrics={},
                language=Language.JAVASCRIPT,
            )

    def get_functions(self, ast_tree: Any) -> list[str]:
        """
        Get list of function names from the AST.

        Args:
            ast_tree: Parsed AST (can be None to use last parsed)

        Returns:
            List of function names
        """
        if ast_tree is None:
            return self._last_functions

        self._extract_names_from_ast(ast_tree)
        return self._last_functions

    def get_classes(self, ast_tree: Any) -> list[str]:
        """
        Get list of class names from the AST.

        Args:
            ast_tree: Parsed AST (can be None to use last parsed)

        Returns:
            List of class names
        """
        if ast_tree is None:
            return self._last_classes

        self._extract_names_from_ast(ast_tree)
        return self._last_classes

    def _extract_names_from_ast(self, ast: Any) -> None:
        """Extract function and class names from AST using parser methods."""
        self._last_functions = []
        self._last_classes = []

        if ast is None:
            return

        # Use the parser's extract_functions if available
        if hasattr(self._parser, "extract_functions"):
            try:
                funcs = self._parser.extract_functions(ast)
                self._last_functions = [f.name for f in funcs if f.name and f.name != "<anonymous>"]
            except Exception:
                pass

        # Note: JavaScriptParser doesn't have extract_classes, so we rely on AST traversal
        # for class extraction. Manual traversal handles both functions and classes.
        self._traverse_ast(ast)

    def _traverse_ast(self, node: Any, depth: int = 0) -> None:
        """Recursively traverse AST to find functions and classes."""
        if node is None or depth > 100:  # Prevent infinite recursion
            return

        node_type = getattr(node, "type", None)

        if node_type == "FunctionDeclaration":
            name = self._get_node_name(node)
            if name:
                self._last_functions.append(name)

        elif node_type == "VariableDeclaration":
            # Handle arrow functions: const foo = () => {}
            declarations = getattr(node, "declarations", [])
            for decl in declarations:
                init = getattr(decl, "init", None)
                if init and getattr(init, "type", None) in (
                    "ArrowFunctionExpression",
                    "FunctionExpression",
                ):
                    name = self._get_node_name(decl.id) if hasattr(decl, "id") else None
                    if name:
                        self._last_functions.append(name)

        elif node_type == "ClassDeclaration":
            name = self._get_node_name(node)
            if name:
                self._last_classes.append(name)

        # Recurse into child nodes
        for attr in ["body", "consequent", "alternate", "declarations", "properties"]:
            child = getattr(node, attr, None)
            if child is None:
                continue
            if isinstance(child, list):
                for item in child:
                    self._traverse_ast(item, depth + 1)
            else:
                self._traverse_ast(child, depth + 1)

    def _get_node_name(self, node: Any) -> str | None:
        """Extract name from a node."""
        if node is None:
            return None

        # Direct name attribute
        if hasattr(node, "name"):
            return node.name

        # id.name pattern
        if hasattr(node, "id") and hasattr(node.id, "name"):
            return node.id.name

        return None

    def _convert_errors(self, errors: Any) -> list[dict[str, Any]]:
        """Convert parser errors to standard format."""
        if errors is None:
            return []

        if isinstance(errors, list):
            result = []
            for err in errors:
                if isinstance(err, dict):
                    result.append(err)
                elif isinstance(err, str):
                    result.append({"message": err, "line": 0, "column": 0})
                else:
                    result.append(
                        {
                            "message": str(err),
                            "line": getattr(err, "line", 0),
                            "column": getattr(err, "column", 0),
                        }
                    )
            return result

        return [{"message": str(errors), "line": 0, "column": 0}]

    def _extract_metrics(self, result: Any) -> dict[str, Any]:
        """Extract metrics from parse result."""
        metrics = {}

        if hasattr(result, "metrics"):
            if isinstance(result.metrics, dict):
                metrics = result.metrics
            elif hasattr(result.metrics, "__dict__"):
                metrics = result.metrics.__dict__

        return metrics


class TypeScriptParserAdapter(JavaScriptParserAdapter):
    """
    Adapter for TypeScript parsing using JavaScriptParser with TS mode.

    [20251221_FEATURE] Enables TypeScript parsing through unified factory.

    Note: This is a basic adapter. For full TypeScript support with type
    checking, consider using the dedicated TypeScript parser when available.
    """

    def parse(self, code: str) -> ParseResult:
        """
        Parse TypeScript code.

        Note: This strips type annotations for parsing. For full TS support,
        use a dedicated TypeScript parser.
        """
        # Basic type annotation stripping for compatibility
        # A full TypeScript parser would handle this properly
        stripped_code = self._strip_type_annotations(code)

        result = super().parse(stripped_code)
        # Update language to TypeScript
        return ParseResult(
            ast=result.ast,
            errors=result.errors,
            warnings=result.warnings,
            metrics=result.metrics,
            language=Language.TYPESCRIPT,
        )

    def _strip_type_annotations(self, code: str) -> str:
        """
        Basic type annotation stripping for TS → JS conversion.

        Note: This is a simplified implementation. For production use,
        consider using a proper TypeScript transpiler.
        """
        import re

        # Remove type annotations after colons (simplified)
        # function foo(x: number): string { }
        # This is NOT comprehensive - just basic support
        # Remove interface/type declarations
        code = re.sub(
            r"^\s*(?:export\s+)?interface\s+\w+\s*\{[^}]*\}",
            "",
            code,
            flags=re.MULTILINE,
        )
        code = re.sub(r"^\s*(?:export\s+)?type\s+\w+\s*=\s*[^;]+;", "", code, flags=re.MULTILINE)

        # Remove : Type from parameters and return types (very basic)
        code = re.sub(r":\s*\w+(?:\[\])?(?:\s*\|\s*\w+(?:\[\])?)*(?=\s*[,)=\{])", "", code)

        # Remove <T> generics (basic)
        code = re.sub(r"<\w+(?:\s*,\s*\w+)*>", "", code)

        # Remove 'as Type' assertions
        code = re.sub(r"\s+as\s+\w+", "", code)

        return code
