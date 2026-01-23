#!/usr/bin/env python3
"""Tree-sitter JavaScript Parser - Fast native JavaScript/TypeScript parsing.

Tree-sitter provides incremental parsing with excellent performance for large files.
This parser supports JavaScript, TypeScript, JSX, and TSX.

Features:
    Parsing:
        - Fast incremental parsing (re-parse on edits)
        - Syntax error recovery (partial parsing)
        - JavaScript, TypeScript, JSX, TSX support
        - Old tree reuse for incremental updates

    Node Traversal:
        - Cursor-based tree walking
        - Generator-based node iteration
        - Find by predicate or node type
        - Source range extraction

    Symbol Extraction:
        - Function declarations and expressions
        - Arrow functions with name inference
        - Class declarations and expressions
        - Variable declarations (const, let, var)
        - Method definitions
        - Parameter extraction

    Module Analysis:
        - Import statement extraction
        - Export statement extraction
        - Default/named/namespace imports
        - Re-export detection

    JSX Analysis:
        - Component detection (PascalCase)
        - Prop extraction
        - Self-closing tag detection
        - Children analysis

    Error Handling:
        - Syntax error extraction with locations
        - Context snippet for errors

Future Enhancements:
    - Syntax highlighting via tree-sitter queries
    - Code folding range detection
    - Scope analysis
    - Custom query pattern matching
"""

from __future__ import annotations

from collections.abc import Callable, Generator
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

try:
    from tree_sitter import Language, Node, Parser, Tree  # type: ignore[import-untyped]

    TREE_SITTER_AVAILABLE = True
except ImportError:
    TREE_SITTER_AVAILABLE = False
    # Stub types for when tree-sitter is not installed
    Language = type(None)  # type: ignore[misc,assignment]
    Parser = type(None)  # type: ignore[misc,assignment]
    Node = type(None)  # type: ignore[misc,assignment]
    Tree = type(None)  # type: ignore[misc,assignment]


def _set_parser_language(parser: Any, language: Any) -> None:
    """[20260122_BUGFIX] Support tree-sitter >=0.24 which dropped set_language()."""
    if hasattr(parser, "set_language"):
        parser.set_language(language)  # type: ignore[attr-defined]
    else:
        parser.language = language  # type: ignore[attr-defined,assignment]


class JSLanguageVariant(Enum):
    """JavaScript language variants supported by tree-sitter."""

    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    TSX = "tsx"
    JSX = "jsx"  # Parsed as JavaScript with JSX


@dataclass
class TreeSitterNode:
    """Wrapper for tree-sitter node with convenient accessors."""

    node: Any  # tree_sitter.Node
    source_code: bytes

    @property
    def type(self) -> str:
        """Node type name."""
        return self.node.type if self.node else ""

    @property
    def text(self) -> str:
        """Node text content."""
        if not self.node:
            return ""
        return self.source_code[self.node.start_byte : self.node.end_byte].decode("utf-8")

    @property
    def start_line(self) -> int:
        """1-indexed start line."""
        return self.node.start_point[0] + 1 if self.node else 0

    @property
    def start_column(self) -> int:
        """0-indexed start column."""
        return self.node.start_point[1] if self.node else 0

    @property
    def end_line(self) -> int:
        """1-indexed end line."""
        return self.node.end_point[0] + 1 if self.node else 0

    @property
    def end_column(self) -> int:
        """0-indexed end column."""
        return self.node.end_point[1] if self.node else 0

    @property
    def children(self) -> list[TreeSitterNode]:
        """Get all child nodes."""
        if not self.node:
            return []
        return [TreeSitterNode(c, self.source_code) for c in self.node.children]

    @property
    def named_children(self) -> list[TreeSitterNode]:
        """Get named child nodes (excludes punctuation, etc.)."""
        if not self.node:
            return []
        return [TreeSitterNode(c, self.source_code) for c in self.node.named_children]

    def child_by_field(self, name: str) -> TreeSitterNode | None:
        """Get child by field name."""
        if not self.node:
            return None
        child = self.node.child_by_field_name(name)
        return TreeSitterNode(child, self.source_code) if child else None

    @property
    def is_error(self) -> bool:
        """Check if this is an error node."""
        return self.node.is_error if self.node else False

    @property
    def has_error(self) -> bool:
        """Check if this node or any descendant has an error."""
        return self.node.has_error if self.node else False


@dataclass
class SyntaxError:
    """Represents a syntax error in the parsed code."""

    message: str
    line: int
    column: int
    end_line: int
    end_column: int
    context: str = ""  # Surrounding code context


@dataclass
class JSSymbol:
    """A JavaScript/TypeScript symbol (function, class, variable, etc.)."""

    name: str
    kind: str  # "function", "class", "variable", "const", "let", "import", "export", etc.
    line: int
    column: int
    end_line: int | None = None
    end_column: int | None = None
    is_exported: bool = False
    is_default_export: bool = False
    is_async: bool = False
    is_generator: bool = False
    parent_name: str | None = None  # For methods, the class name
    parameters: list[str] = field(default_factory=list)
    return_type: str | None = None  # TypeScript only
    jsdoc: str | None = None


@dataclass
class JSXComponent:
    """A JSX/TSX component usage."""

    name: str
    line: int
    column: int
    is_self_closing: bool = False
    props: list[str] = field(default_factory=list)
    children_count: int = 0


@dataclass
class ImportStatement:
    """An import statement."""

    module: str
    line: int
    is_type_only: bool = False  # TypeScript: import type
    default_import: str | None = None
    namespace_import: str | None = None  # import * as name
    named_imports: list[tuple[str, str | None]] = field(default_factory=list)  # [(name, alias)]
    is_dynamic: bool = False  # import()


@dataclass
class ExportStatement:
    """An export statement."""

    name: str
    line: int
    kind: str  # "default", "named", "all", "declaration"
    source_module: str | None = None  # For re-exports
    is_type_only: bool = False  # TypeScript: export type


@dataclass
class TreeSitterParseResult:
    """Result of parsing with tree-sitter."""

    tree: Any  # tree_sitter.Tree
    root_node: TreeSitterNode
    errors: list[SyntaxError]
    symbols: list[JSSymbol]
    imports: list[ImportStatement]
    exports: list[ExportStatement]
    jsx_components: list[JSXComponent]
    language_variant: JSLanguageVariant
    parse_time_ms: float = 0.0


class TreeSitterJSParser:
    """
    Fast JavaScript/TypeScript parser using tree-sitter.

    Tree-sitter provides:
    - Incremental parsing (fast re-parsing on edits)
    - Error recovery (partial parsing despite syntax errors)
    - Consistent AST structure
    - Fast queries via S-expression patterns

    Example usage:
        parser = TreeSitterJSParser()

        # Parse JavaScript
        result = parser.parse(code)

        # Parse TypeScript
        result = parser.parse(code, variant=JSLanguageVariant.TYPESCRIPT)

        # Get all functions
        functions = parser.get_functions(result)

        # Find all imports
        imports = result.imports
    """

    def __init__(self, language_path: str | None = None) -> None:
        """
        Initialize tree-sitter parser.

        :param language_path: Optional path to compiled language .so file.
        """
        if not TREE_SITTER_AVAILABLE:
            raise ImportError("tree-sitter not installed. Install with: pip install tree-sitter")

        self._parsers: dict[JSLanguageVariant, Any] = {}
        self._languages: dict[JSLanguageVariant, Any] = {}
        self._language_path = language_path

        # Try to load languages
        self._init_languages()

    def _init_languages(self) -> None:
        """Initialize tree-sitter languages."""
        # [20260121_BUGFIX] Guard against missing tree-sitter base package.
        # If the base `tree_sitter` package is not available, do not attempt
        # any fallbacks that rely on its `Parser`/`Language` classes. Other
        # parsers will handle JS/TS via non-tree-sitter paths.
        if not TREE_SITTER_AVAILABLE:
            return
        try:
            # Try tree-sitter-languages package first (easiest setup)
            import tree_sitter_languages  # type: ignore[import-untyped]

            for variant in JSLanguageVariant:
                lang_name = variant.value
                if variant == JSLanguageVariant.JSX:
                    lang_name = "javascript"  # JSX uses JS parser

                try:
                    lang = tree_sitter_languages.get_language(lang_name)
                    parser = tree_sitter_languages.get_parser(lang_name)
                    self._languages[variant] = lang
                    self._parsers[variant] = parser
                except Exception:
                    pass

        except ImportError:
            # [20260103_BUGFIX] Fallback to individual tree-sitter language packages
            try:
                import tree_sitter_javascript  # type: ignore[import-untyped]
                import tree_sitter_typescript  # type: ignore[import-untyped]

                # JavaScript and JSX use the same parser
                js_lang = Language(tree_sitter_javascript.language())  # type: ignore[operator]
                js_parser = Parser()
                _set_parser_language(js_parser, js_lang)
                self._languages[JSLanguageVariant.JAVASCRIPT] = js_lang
                self._parsers[JSLanguageVariant.JAVASCRIPT] = js_parser
                self._languages[JSLanguageVariant.JSX] = js_lang
                self._parsers[JSLanguageVariant.JSX] = js_parser

                # TypeScript
                ts_lang = Language(tree_sitter_typescript.language_typescript())  # type: ignore[operator]
                ts_parser = Parser()
                _set_parser_language(ts_parser, ts_lang)
                self._languages[JSLanguageVariant.TYPESCRIPT] = ts_lang
                self._parsers[JSLanguageVariant.TYPESCRIPT] = ts_parser

                # TSX
                tsx_lang = Language(tree_sitter_typescript.language_tsx())  # type: ignore[operator]
                tsx_parser = Parser()
                _set_parser_language(tsx_parser, tsx_lang)
                self._languages[JSLanguageVariant.TSX] = tsx_lang
                self._parsers[JSLanguageVariant.TSX] = tsx_parser

            except ImportError:
                # Final fallback to manual language loading
                if self._language_path:
                    self._load_language_from_path(self._language_path)

    def _load_language_from_path(self, path: str) -> None:
        """Load language from compiled .so file."""
        try:
            lang_path = Path(path)
            if lang_path.exists():
                js_lang = Language(str(lang_path))  # type: ignore[operator]
                ts_lang = Language(str(lang_path))  # type: ignore[operator]
                tsx_lang = Language(str(lang_path))  # type: ignore[operator]

                for variant, lang in [
                    (JSLanguageVariant.JAVASCRIPT, js_lang),
                    (JSLanguageVariant.JSX, js_lang),
                    (JSLanguageVariant.TYPESCRIPT, ts_lang),
                    (JSLanguageVariant.TSX, tsx_lang),
                ]:
                    parser = Parser()
                    _set_parser_language(parser, lang)
                    self._parsers[variant] = parser
                    self._languages[variant] = lang
        except Exception:  # noqa: BLE001
            pass

    def is_language_available(self, variant: JSLanguageVariant) -> bool:
        """Check if a language variant is available."""
        return variant in self._parsers

    def parse(
        self,
        code: str,
        variant: JSLanguageVariant = JSLanguageVariant.JAVASCRIPT,
        old_tree: Any | None = None,
    ) -> TreeSitterParseResult:
        """
        Parse JavaScript/TypeScript code.

        :param code: Source code to parse.
        :param variant: Language variant (JS, TS, JSX, TSX).
        :param old_tree: Previous tree for incremental parsing.
        :return: TreeSitterParseResult with AST and extracted information.
        """
        import time

        start_time = time.time()

        if variant not in self._parsers:
            raise RuntimeError(
                f"Language {variant.value} not available. "
                "Install tree-sitter-languages: pip install tree-sitter-languages"
            )

        parser = self._parsers[variant]
        source_bytes = code.encode("utf-8")

        # Parse with optional incremental update
        if old_tree:
            tree = parser.parse(source_bytes, old_tree)
        else:
            tree = parser.parse(source_bytes)

        root = TreeSitterNode(tree.root_node, source_bytes)

        # Extract information
        errors = self._extract_errors(root, code)
        symbols = self._extract_symbols(root)
        imports = self._extract_imports(root)
        exports = self._extract_exports(root)
        jsx_components = (
            self._extract_jsx_components(root) if variant in (JSLanguageVariant.JSX, JSLanguageVariant.TSX) else []
        )

        parse_time = (time.time() - start_time) * 1000

        return TreeSitterParseResult(
            tree=tree,
            root_node=root,
            errors=errors,
            symbols=symbols,
            imports=imports,
            exports=exports,
            jsx_components=jsx_components,
            language_variant=variant,
            parse_time_ms=parse_time,
        )

    def parse_file(
        self,
        file_path: str,
        variant: JSLanguageVariant | None = None,
    ) -> TreeSitterParseResult:
        """
        Parse a JavaScript/TypeScript file.

        :param file_path: Path to file.
        :param variant: Language variant (auto-detected if None).
        :return: TreeSitterParseResult.
        """
        path = Path(file_path)
        code = path.read_text(encoding="utf-8")

        # Auto-detect variant from extension
        if variant is None:
            ext = path.suffix.lower()
            variant = {
                ".js": JSLanguageVariant.JAVASCRIPT,
                ".jsx": JSLanguageVariant.JSX,
                ".ts": JSLanguageVariant.TYPESCRIPT,
                ".tsx": JSLanguageVariant.TSX,
                ".mjs": JSLanguageVariant.JAVASCRIPT,
                ".cjs": JSLanguageVariant.JAVASCRIPT,
                ".mts": JSLanguageVariant.TYPESCRIPT,
                ".cts": JSLanguageVariant.TYPESCRIPT,
            }.get(ext, JSLanguageVariant.JAVASCRIPT)

        return self.parse(code, variant)

    def _extract_errors(self, root: TreeSitterNode, code: str) -> list[SyntaxError]:
        """Extract syntax errors from the tree."""
        errors: list[SyntaxError] = []
        lines = code.split("\n")

        def visit(node: TreeSitterNode) -> None:
            if node.is_error:
                context = ""
                if 0 < node.start_line <= len(lines):
                    context = lines[node.start_line - 1].strip()

                errors.append(
                    SyntaxError(
                        message=(
                            f"Syntax error: unexpected '{node.text[:50]}...' "
                            if len(node.text) > 50
                            else f"Syntax error: unexpected '{node.text}'"
                        ),
                        line=node.start_line,
                        column=node.start_column,
                        end_line=node.end_line,
                        end_column=node.end_column,
                        context=context,
                    )
                )

            for child in node.children:
                visit(child)

        visit(root)
        return errors

    def _extract_symbols(self, root: TreeSitterNode) -> list[JSSymbol]:
        """Extract all symbols from the tree."""
        symbols: list[JSSymbol] = []
        current_class: str | None = None

        def visit(node: TreeSitterNode, is_exported: bool = False, is_default: bool = False) -> None:
            nonlocal current_class

            node_type = node.type

            # Function declarations
            if node_type == "function_declaration":
                name_node = node.child_by_field("name")
                params_node = node.child_by_field("parameters")

                symbols.append(
                    JSSymbol(
                        name=name_node.text if name_node else "<anonymous>",
                        kind="function",
                        line=node.start_line,
                        column=node.start_column,
                        end_line=node.end_line,
                        end_column=node.end_column,
                        is_exported=is_exported,
                        is_default_export=is_default,
                        is_async="async" in [c.type for c in node.children],
                        is_generator=any(c.type == "*" for c in node.children),
                        parameters=self._extract_params(params_node),
                    )
                )

            # Arrow functions assigned to variables
            elif node_type == "lexical_declaration" or node_type == "variable_declaration":
                for declarator in [c for c in node.named_children if c.type == "variable_declarator"]:
                    name_node = declarator.child_by_field("name")
                    value_node = declarator.child_by_field("value")

                    if value_node and value_node.type == "arrow_function":
                        params_node = value_node.child_by_field("parameters")
                        symbols.append(
                            JSSymbol(
                                name=name_node.text if name_node else "<anonymous>",
                                kind="function",
                                line=node.start_line,
                                column=node.start_column,
                                end_line=node.end_line,
                                is_exported=is_exported,
                                is_async="async" in value_node.text,
                                parameters=self._extract_params(params_node),
                            )
                        )
                    elif name_node:
                        kind = (
                            "const"
                            if node_type == "lexical_declaration" and "const" in node.text[:10]
                            else "let" if "let" in node.text[:10] else "var"
                        )
                        symbols.append(
                            JSSymbol(
                                name=name_node.text,
                                kind=kind,
                                line=node.start_line,
                                column=node.start_column,
                                is_exported=is_exported,
                            )
                        )

            # Class declarations
            elif node_type == "class_declaration":
                name_node = node.child_by_field("name")
                class_name = name_node.text if name_node else "<anonymous>"

                symbols.append(
                    JSSymbol(
                        name=class_name,
                        kind="class",
                        line=node.start_line,
                        column=node.start_column,
                        end_line=node.end_line,
                        end_column=node.end_column,
                        is_exported=is_exported,
                        is_default_export=is_default,
                    )
                )

                # Extract methods
                old_class = current_class
                current_class = class_name
                body = node.child_by_field("body")
                if body:
                    for child in body.named_children:
                        visit(child)
                current_class = old_class
                return  # Already visited body

            # Method definitions
            elif node_type == "method_definition":
                name_node = node.child_by_field("name")
                params_node = node.child_by_field("parameters")

                symbols.append(
                    JSSymbol(
                        name=name_node.text if name_node else "<anonymous>",
                        kind="method",
                        line=node.start_line,
                        column=node.start_column,
                        end_line=node.end_line,
                        parent_name=current_class,
                        is_async="async" in [c.type for c in node.children],
                        is_generator=any(c.type == "*" for c in node.children),
                        parameters=self._extract_params(params_node),
                    )
                )

            # Export statements
            elif node_type == "export_statement":
                is_default_export = any(c.type == "default" for c in node.children)
                declaration = node.child_by_field("declaration")
                if declaration:
                    visit(declaration, is_exported=True, is_default=is_default_export)
                    return

            # TypeScript-specific: interface declarations
            elif node_type == "interface_declaration":
                name_node = node.child_by_field("name")
                symbols.append(
                    JSSymbol(
                        name=name_node.text if name_node else "<anonymous>",
                        kind="interface",
                        line=node.start_line,
                        column=node.start_column,
                        end_line=node.end_line,
                        is_exported=is_exported,
                    )
                )

            # TypeScript-specific: type alias
            elif node_type == "type_alias_declaration":
                name_node = node.child_by_field("name")
                symbols.append(
                    JSSymbol(
                        name=name_node.text if name_node else "<anonymous>",
                        kind="type",
                        line=node.start_line,
                        column=node.start_column,
                        is_exported=is_exported,
                    )
                )

            # TypeScript-specific: enum
            elif node_type == "enum_declaration":
                name_node = node.child_by_field("name")
                symbols.append(
                    JSSymbol(
                        name=name_node.text if name_node else "<anonymous>",
                        kind="enum",
                        line=node.start_line,
                        column=node.start_column,
                        end_line=node.end_line,
                        is_exported=is_exported,
                    )
                )

            # Recurse into children
            for child in node.named_children:
                visit(child)

        visit(root)
        return symbols

    def _extract_params(self, params_node: TreeSitterNode | None) -> list[str]:
        """Extract parameter names from a parameter list node."""
        if not params_node:
            return []

        params: list[str] = []
        for child in params_node.named_children:
            if child.type == "identifier":
                params.append(child.text)
            elif child.type == "required_parameter" or child.type == "optional_parameter":
                pattern = child.child_by_field("pattern")
                if pattern:
                    params.append(pattern.text)
            elif child.type == "rest_pattern" or child.type == "rest_parameter":
                params.append(f"...{child.text.lstrip('.')}")
            elif child.type == "assignment_pattern":
                left = child.child_by_field("left")
                if left:
                    params.append(f"{left.text}=")

        return params

    def _extract_imports(self, root: TreeSitterNode) -> list[ImportStatement]:
        """Extract all import statements."""
        imports: list[ImportStatement] = []

        def visit(node: TreeSitterNode) -> None:
            if node.type == "import_statement":
                source = node.child_by_field("source")
                module = source.text.strip("\"'") if source else ""

                import_stmt = ImportStatement(
                    module=module,
                    line=node.start_line,
                    is_type_only="import type" in node.text[:15],
                )

                # Check for default import
                for child in node.named_children:
                    if child.type == "identifier":
                        import_stmt.default_import = child.text
                    elif child.type == "import_clause":
                        for clause_child in child.named_children:
                            if clause_child.type == "identifier":
                                import_stmt.default_import = clause_child.text
                            elif clause_child.type == "namespace_import":
                                name = clause_child.child_by_field("name")
                                if name:
                                    import_stmt.namespace_import = name.text
                            elif clause_child.type == "named_imports":
                                for spec in clause_child.named_children:
                                    if spec.type == "import_specifier":
                                        name = spec.child_by_field("name")
                                        alias = spec.child_by_field("alias")
                                        if name:
                                            import_stmt.named_imports.append(
                                                (
                                                    name.text,
                                                    alias.text if alias else None,
                                                )
                                            )

                imports.append(import_stmt)

            # Dynamic imports
            elif node.type == "call_expression":
                func = node.child_by_field("function")
                if func and func.type == "import":
                    args = node.child_by_field("arguments")
                    if args and args.named_children:
                        first_arg = args.named_children[0]
                        if first_arg.type == "string":
                            imports.append(
                                ImportStatement(
                                    module=first_arg.text.strip("\"'"),
                                    line=node.start_line,
                                    is_dynamic=True,
                                )
                            )

            for child in node.named_children:
                visit(child)

        visit(root)
        return imports

    def _extract_exports(self, root: TreeSitterNode) -> list[ExportStatement]:
        """Extract all export statements."""
        exports: list[ExportStatement] = []

        def visit(node: TreeSitterNode) -> None:
            if node.type == "export_statement":
                is_default = any(c.type == "default" for c in node.children)
                source = node.child_by_field("source")
                source_module = source.text.strip("\"'") if source else None

                # Export declaration
                declaration = node.child_by_field("declaration")
                if declaration:
                    name = "<default>" if is_default else "<declaration>"
                    name_node = declaration.child_by_field("name")
                    if name_node:
                        name = name_node.text

                    exports.append(
                        ExportStatement(
                            name=name,
                            line=node.start_line,
                            kind="default" if is_default else "declaration",
                        )
                    )

                # Named exports
                for child in node.named_children:
                    if child.type == "export_clause":
                        for spec in child.named_children:
                            if spec.type == "export_specifier":
                                name = spec.child_by_field("name")
                                if name:
                                    exports.append(
                                        ExportStatement(
                                            name=name.text,
                                            line=node.start_line,
                                            kind="named",
                                            source_module=source_module,
                                        )
                                    )
                    elif child.type == "*":
                        exports.append(
                            ExportStatement(
                                name="*",
                                line=node.start_line,
                                kind="all",
                                source_module=source_module,
                            )
                        )

            for child in node.named_children:
                visit(child)

        visit(root)
        return exports

    def _extract_jsx_components(self, root: TreeSitterNode) -> list[JSXComponent]:
        """Extract JSX/TSX component usages."""
        components: list[JSXComponent] = []

        def visit(node: TreeSitterNode) -> None:
            if node.type in ("jsx_element", "jsx_self_closing_element"):
                is_self_closing = node.type == "jsx_self_closing_element"

                # Get component name
                name = ""
                props: list[str] = []

                if is_self_closing:
                    name_node = node.child_by_field("name")
                    if name_node:
                        name = name_node.text

                    # Get attributes
                    for child in node.named_children:
                        if child.type == "jsx_attribute":
                            attr_name = child.child_by_field("name")
                            if attr_name:
                                props.append(attr_name.text)
                else:
                    # Regular element
                    opening = None
                    for child in node.named_children:
                        if child.type == "jsx_opening_element":
                            opening = child
                            break

                    if opening:
                        name_node = opening.child_by_field("name")
                        if name_node:
                            name = name_node.text

                        for child in opening.named_children:
                            if child.type == "jsx_attribute":
                                attr_name = child.child_by_field("name")
                                if attr_name:
                                    props.append(attr_name.text)

                # Count children (for non-self-closing)
                children_count = 0
                if not is_self_closing:
                    for child in node.named_children:
                        if child.type not in (
                            "jsx_opening_element",
                            "jsx_closing_element",
                        ):
                            children_count += 1

                # Only track component usages (PascalCase names)
                if name and (name[0].isupper() or "." in name):
                    components.append(
                        JSXComponent(
                            name=name,
                            line=node.start_line,
                            column=node.start_column,
                            is_self_closing=is_self_closing,
                            props=props,
                            children_count=children_count,
                        )
                    )

            for child in node.named_children:
                visit(child)

        visit(root)
        return components

    def walk(self, root: TreeSitterNode) -> Generator[TreeSitterNode, None, None]:
        """
        Walk the tree depth-first.

        :param root: Root node to start from.
        :yield: Each node in the tree.
        """
        yield root
        for child in root.children:
            yield from self.walk(child)

    def find_nodes(self, root: TreeSitterNode, predicate: Callable[[TreeSitterNode], bool]) -> list[TreeSitterNode]:
        """
        Find all nodes matching a predicate.

        :param root: Root node to search from.
        :param predicate: Function that returns True for matching nodes.
        :return: List of matching nodes.
        """
        return [node for node in self.walk(root) if predicate(node)]

    def find_by_type(self, root: TreeSitterNode, node_type: str) -> list[TreeSitterNode]:
        """
        Find all nodes of a specific type.

        :param root: Root node to search from.
        :param node_type: Type name to search for.
        :return: List of matching nodes.
        """
        return self.find_nodes(root, lambda n: n.type == node_type)

    def get_functions(self, result: TreeSitterParseResult) -> list[JSSymbol]:
        """Get all function symbols."""
        return [s for s in result.symbols if s.kind in ("function", "method")]

    def get_classes(self, result: TreeSitterParseResult) -> list[JSSymbol]:
        """Get all class symbols."""
        return [s for s in result.symbols if s.kind == "class"]

    def get_variables(self, result: TreeSitterParseResult) -> list[JSSymbol]:
        """Get all variable symbols."""
        return [s for s in result.symbols if s.kind in ("const", "let", "var")]
