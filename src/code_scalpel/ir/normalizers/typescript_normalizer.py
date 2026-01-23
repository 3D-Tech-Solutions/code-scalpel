"""
TypeScript Normalizer - Convert tree-sitter-typescript CST to Unified IR.

[20251214_FEATURE] v2.0.0 - TypeScript support for polyglot extraction.

This normalizer extends the JavaScript normalizer to handle TypeScript-specific
constructs like:
- Type annotations
- Interface declarations
- Type aliases
- Generic types
- Decorators

The normalizer uses tree-sitter-typescript for parsing, which handles both
.ts and .tsx files.
"""

from __future__ import annotations

from ..nodes import (
    IRCall,
    IRClassDef,
    IRConstant,
    IRExpr,
    IRExprStmt,
    IRFunctionDef,
    IRName,
)
from .javascript_normalizer import JavaScriptNormalizer

# [20251215_REFACTOR] Trim unused imports and locals for lint compliance (no behavior change).


class TypeScriptNormalizer(JavaScriptNormalizer):
    """
    Normalizes TypeScript CST (from tree-sitter) to Unified IR.

    [20251214_FEATURE] v2.0.0 - TypeScript support extending JavaScript normalizer.

    Extends JavaScriptNormalizer to handle TypeScript-specific syntax:
    - interface declarations
    - type aliases
    - type annotations on functions and parameters
    - generic type parameters

    Example:
        >>> normalizer = TypeScriptNormalizer()
        >>> ir = normalizer.normalize('''
        ... interface User {
        ...     name: string;
        ...     age: number;
        ... }
        ...
        ... function greet(user: User): string {
        ...     return `Hello ${user.name}`;
        ... }
        ... ''')
        >>> ir.body[0]  # Interface becomes a class-like structure

    Tree-sitter dependency:
        Requires tree_sitter and tree_sitter_typescript packages:
        pip install tree-sitter tree-sitter-typescript


    COMMUNITY TIER (Core TypeScript Type Normalization):

    PRO TIER (Advanced TypeScript Features):

    ENTERPRISE TIER (Advanced Analysis & Optimization):
    """

    def _ensure_parser(self) -> None:
        """Initialize tree-sitter parser for TypeScript."""
        if self._parser is not None:
            return

        try:
            import tree_sitter_typescript as ts_ts
            from tree_sitter import Language, Parser

            self._language = Language(ts_ts.language_typescript())
            self._parser = Parser(self._language)
        except ImportError as e:
            raise ImportError(
                "TypeScriptNormalizer requires tree-sitter packages. "
                "Install with: pip install tree-sitter tree-sitter-typescript"
            ) from e

    @property
    def language(self) -> str:
        return "typescript"

    # =========================================================================
    # TypeScript-specific normalizers
    # =========================================================================

    def _normalize_interface_declaration(self, node) -> IRClassDef:
        """
        Normalize TypeScript interface declaration.

        [20251214_FEATURE] Interface -> IRClassDef representation.

        CST structure:
            interface_declaration:
                "interface"
                name: type_identifier
                type_parameters? (optional generics)
                extends_type_clause? (optional)
                object_type: body

            - Generic type parameters and constraints <T extends Base>
            - Union types (string | number) as metadata
            - Intersection types (&) preservation
            - Readonly modifier detection
            - Type guard function patterns (is Type)

            - Mapped types: { [K in keyof T]: ... }
            - Conditional types: T extends U ? X : Y
            - Index signatures and computed types
            - Template literal types
        """
        name_node = self._child_by_field(node, "name")
        body_node = self._child_by_field(node, "body")

        name = self._get_text(name_node) if name_node else "Anonymous"

        # Process interface body (property signatures, method signatures)
        body = []
        if body_node:
            for child in body_node.children:
                if not child.is_named:
                    continue

                if child.type == "property_signature":
                    # Property signatures become class attributes
                    prop = self._normalize_property_signature(child)
                    if prop:
                        body.append(prop)
                elif child.type == "method_signature":
                    # Method signatures become function definitions
                    method = self._normalize_method_signature(child)
                    if method:
                        body.append(method)

        # [20251220_BUGFIX] _set_language returns IRNode, cast to IRClassDef
        from typing import cast

        return cast(
            IRClassDef,
            self._set_language(
                IRClassDef(
                    name=name,
                    body=body,
                    loc=self._make_loc(node),
                )
            ),
        )

    def _normalize_property_signature(self, node) -> IRExprStmt | None:
        """
        Normalize interface property signature.

        CST structure:
            property_signature:
                name: property_identifier
                type_annotation?: type
        """
        name_node = self._child_by_field(node, "name")
        if not name_node:
            return None

        name = self._get_text(name_node)

        # Create a simple name expression for the property
        # [20251220_BUGFIX] _set_language returns IRNode, cast to IRExprStmt
        from typing import cast

        return cast(
            IRExprStmt,
            self._set_language(
                IRExprStmt(
                    value=IRName(id=name, loc=self._make_loc(name_node)),
                    loc=self._make_loc(node),
                )
            ),
        )

    def _normalize_method_signature(self, node) -> IRFunctionDef | None:
        """
        Normalize interface method signature.

        CST structure:
            method_signature:
                name: property_identifier
                parameters: formal_parameters
                return_type?: type_annotation
        """
        name_node = self._child_by_field(node, "name")
        params_node = self._child_by_field(node, "parameters")

        if not name_node:
            return None

        name = self._get_text(name_node)
        params = self._normalize_parameters(params_node) if params_node else []

        # [20251220_BUGFIX] _set_language returns IRNode, cast to IRFunctionDef
        from typing import cast

        return cast(
            IRFunctionDef,
            self._set_language(
                IRFunctionDef(
                    name=name,
                    params=params,
                    body=[],  # Interface methods have no body
                    loc=self._make_loc(node),
                )
            ),
        )

    def _normalize_type_alias_declaration(self, node) -> IRClassDef:
        """
        Normalize TypeScript type alias.

        [20251214_FEATURE] Type alias -> IRClassDef representation.

        CST structure:
            type_alias_declaration:
                "type"
                name: type_identifier
                type_parameters? (optional generics)
                "="
                value: type
        """
        name_node = self._child_by_field(node, "name")
        name = self._get_text(name_node) if name_node else "Anonymous"

        # Type aliases are represented as empty classes
        # The actual type is captured in metadata if needed
        # [20251220_BUGFIX] _set_language returns IRNode, cast to IRClassDef
        from typing import cast

        return cast(
            IRClassDef,
            self._set_language(
                IRClassDef(
                    name=name,
                    bases=[],
                    body=[],
                    loc=self._make_loc(node),
                )
            ),
        )


class TypeScriptTSXNormalizer(TypeScriptNormalizer):
    """
    Normalizes TSX (TypeScript + JSX) CST to Unified IR.

    [20251214_FEATURE] v2.0.0 - TSX support.

    Extends TypeScriptNormalizer to handle JSX syntax within TypeScript:
    - JSX elements
    - JSX fragments
    - JSX expressions
    """

    def _ensure_parser(self) -> None:
        """Initialize tree-sitter parser for TSX."""
        if self._parser is not None:
            return

        try:
            import tree_sitter_typescript as ts_ts
            from tree_sitter import Language, Parser

            # Use TSX language for .tsx files
            self._language = Language(ts_ts.language_tsx())
            self._parser = Parser(self._language)
        except ImportError as e:
            raise ImportError(
                "TypeScriptTSXNormalizer requires tree-sitter packages. "
                "Install with: pip install tree-sitter tree-sitter-typescript"
            ) from e

    @property
    def language(self) -> str:
        return "typescriptreact"  # Match VS Code language ID

    # =========================================================================
    # JSX Handlers - [20251215_FEATURE] v2.0.0 - JSX support for TSX files
    # =========================================================================

    def _normalize_jsx_element(self, node) -> IRCall:
        """
        Normalize JSX element to IRCall (React.createElement equivalent).

        [20251215_FEATURE] JSX elements become function calls for analysis.

        CST structure:
            jsx_element:
                open_tag: jsx_opening_element
                children: jsx_text | jsx_expression | jsx_element | ...
                close_tag: jsx_closing_element

        Returns:
            IRCall representing createElement(tag, props, ...children)
        """
        tag_name = "unknown"
        children = []

        for child in node.children:
            if child.type == "jsx_opening_element":
                name_node = self._child_by_field(child, "name")
                if name_node:
                    tag_name = self._get_text(name_node)
            elif child.type in (
                "jsx_text",
                "jsx_expression",
                "jsx_element",
                "jsx_self_closing_element",
                "jsx_fragment",
            ):
                child_ir = self.normalize_node(child)
                if child_ir:
                    children.append(child_ir)

        # Represent as createElement(tag, props, ...children)
        # [20251220_BUGFIX] _set_language returns IRNode, cast to IRCall
        from typing import cast

        return cast(
            IRCall,
            self._set_language(
                IRCall(
                    func=IRName(id=f"JSX:{tag_name}"),
                    args=children,
                    loc=self._make_loc(node),
                )
            ),
        )

    def _normalize_jsx_self_closing_element(self, node) -> IRCall:
        """
        Normalize self-closing JSX element (<Component />).

        [20251215_FEATURE] Self-closing elements have no children.
        """
        name_node = self._child_by_field(node, "name")
        tag_name = self._get_text(name_node) if name_node else "unknown"

        # [20251220_BUGFIX] _set_language returns IRNode, cast to IRCall
        from typing import cast

        return cast(
            IRCall,
            self._set_language(
                IRCall(
                    func=IRName(id=f"JSX:{tag_name}"),
                    args=[],
                    loc=self._make_loc(node),
                )
            ),
        )

    def _normalize_jsx_fragment(self, node) -> IRCall:
        """
        Normalize JSX fragment (<>...</>).

        [20251215_FEATURE] Fragments become calls to Fragment.
        """
        children = []
        for child in self._get_named_children(node):
            if child.type not in ("jsx_opening_fragment", "jsx_closing_fragment"):
                child_ir = self.normalize_node(child)
                if child_ir:
                    children.append(child_ir)

        # [20251220_BUGFIX] _set_language returns IRNode, cast to IRCall
        from typing import cast

        return cast(
            IRCall,
            self._set_language(
                IRCall(
                    func=IRName(id="JSX:Fragment"),
                    args=children,
                    loc=self._make_loc(node),
                )
            ),
        )

    def _normalize_jsx_expression(self, node) -> IRExpr:
        """
        Normalize JSX expression ({expression}).

        [20251215_FEATURE] JSX expressions are embedded JavaScript.
        """
        # JSX expression is { expr }, extract the inner expression
        # [20251220_BUGFIX] Handle union return from normalize_node, cast to IRExpr
        from typing import cast

        for child in self._get_named_children(node):
            result = self.normalize_node(child)
            if isinstance(result, IRExpr):
                return cast(IRExpr, result)
        # Default: return a placeholder expression
        return cast(IRExpr, IRConstant(value=None, loc=self._make_loc(node)))

    def _normalize_jsx_text(self, node) -> IRConstant:
        """
        Normalize JSX text content.

        [20251215_FEATURE] Text nodes become string constants.
        """
        # [20251220_BUGFIX] Extract text, handle None case, cast _set_language return
        from typing import cast

        text = self._get_text(node).strip()
        if not text:
            return cast(IRConstant, IRConstant(value="", loc=self._make_loc(node)))
        return cast(
            IRConstant,
            self._set_language(
                IRConstant(
                    value=text,
                    loc=self._make_loc(node),
                )
            ),
        )
