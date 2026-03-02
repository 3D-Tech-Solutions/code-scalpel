"""
Go Normalizer - Converts Go CST (tree-sitter-go) to Unified IR.

[20260302_FEATURE] Go language support for surgical extraction and analysis.

Key Mappings:
    source_file           -> IRModule
    package_clause        -> (records package name on module, no IR node)
    import_declaration    -> IRImport (handles single and grouped imports)
    function_declaration  -> IRFunctionDef
    method_declaration    -> IRFunctionDef (receiver stored in metadata)
    type_declaration      -> IRClassDef (struct or interface via type_spec)
    var_declaration       -> IRAssign
    const_declaration     -> IRAssign
    short_var_declaration -> IRAssign  (:= syntax)
    assignment_statement  -> IRAssign
    return_statement      -> IRReturn
    if_statement          -> IRIf
    for_statement         -> IRFor (handles classic, range, and while-style)
    expression_statement  -> IRExprStmt
    call_expression       -> IRCall
    binary_expression     -> IRBinaryOp
    selector_expression   -> IRName  (e.g. fmt.Println -> "fmt.Println")
    identifier            -> IRName
    interpreted/raw string -> IRConstant
    int/float literal     -> IRConstant
    true / false / nil    -> IRConstant

Tree-sitter field names used:
    function_declaration:  name, parameters, result, body
    method_declaration:    receiver, name, parameters, result, body
    type_spec:             name, type
    var_spec:              (named children: identifier, type?, expression_list?)
    const_spec:            name, value
    short_var_declaration: left, right
    assignment_statement:  left, right
    if_statement:          condition, consequence, alternative
    for_statement:         body  (children include for_clause or range_clause)
    call_expression:       function, arguments
    binary_expression:     left, operator, right
    selector_expression:   operand, field
    import_spec:           (named children: [alias?], path_string)
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, cast

import tree_sitter_go
from tree_sitter import Language, Parser

from ..nodes import (
    IRAssign,
    IRBinaryOp,
    IRBreak,
    IRCall,
    IRClassDef,
    IRConstant,
    IRContinue,
    IRExpr,
    IRExprStmt,
    IRFor,
    IRFunctionDef,
    IRIf,
    IRImport,
    IRModule,
    IRName,
    IRNode,
    IRParameter,
    IRReturn,
    SourceLocation,
)
from ..operators import BinaryOperator
from .base import BaseNormalizer
from .tree_sitter_visitor import TreeSitterVisitor

# ---------------------------------------------------------------------------
# Operator mapping
# ---------------------------------------------------------------------------

_BINOP_MAP: Dict[str, BinaryOperator] = {
    "+": BinaryOperator.ADD,
    "-": BinaryOperator.SUB,
    "*": BinaryOperator.MUL,
    "/": BinaryOperator.DIV,
    "%": BinaryOperator.MOD,
    "&": BinaryOperator.BIT_AND,
    "|": BinaryOperator.BIT_OR,
    "^": BinaryOperator.BIT_XOR,
    "<<": BinaryOperator.LSHIFT,
    ">>": BinaryOperator.RSHIFT,
}

# ---------------------------------------------------------------------------
# Visitor
# ---------------------------------------------------------------------------


class GoVisitor(TreeSitterVisitor):
    """Visitor that converts tree-sitter Go CST nodes to Unified IR."""

    @property
    def language(self) -> str:
        return "go"

    def __init__(self, source: str = "") -> None:
        super().__init__()
        self.ctx.source = source

    # ------------------------------------------------------------------
    # Required abstract helpers
    # ------------------------------------------------------------------

    def _get_node_type(self, node: Any) -> str:
        return node.type

    def _get_text(self, node: Any) -> str:
        return self.ctx.source[node.start_byte : node.end_byte]

    def _get_location(self, node: Any) -> Optional[SourceLocation]:
        if node is None:
            return None
        return SourceLocation(
            line=node.start_point[0] + 1,
            column=node.start_point[1],
            end_line=node.end_point[0] + 1,
            end_column=node.end_point[1],
        )

    def _get_children(self, node: Any) -> List[Any]:
        return node.children

    def _get_named_children(self, node: Any) -> List[Any]:
        return [c for c in node.children if c.is_named]

    def _get_child_by_field(self, node: Any, field_name: str) -> Optional[Any]:
        return node.child_by_field_name(field_name)

    def _get_children_by_field(self, node: Any, field_name: str) -> List[Any]:
        return node.children_by_field_name(field_name)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _visit_block(self, block_node: Any) -> List[IRNode]:
        """
        Visit a Go `block` node.

        Go blocks contain a `statement_list` child, not statements directly.
        Handle both the direct statement_list and any degenerate cases.
        """
        if block_node is None:
            return []
        results: List[IRNode] = []
        for child in block_node.named_children:
            if child.type == "statement_list":
                for stmt in child.named_children:
                    res = self.visit(stmt)
                    if res is None:
                        continue
                    if isinstance(res, list):
                        results.extend(r for r in res if r is not None)
                    else:
                        results.append(cast(IRNode, res))
            else:
                res = self.visit(child)
                if res is None:
                    continue
                if isinstance(res, list):
                    results.extend(r for r in res if r is not None)
                else:
                    results.append(cast(IRNode, res))
        return results

    def _text_of(self, node: Any) -> str:
        """Get text of a node, or empty string if None."""
        if node is None:
            return ""
        return self._get_text(node)

    def _parse_parameters(self, params_node: Any) -> List[IRParameter]:
        """Parse a Go parameter_list into IRParameter list.

        Go parameter_declaration has named children: identifier(s) + type.
        The last named child is always the type; preceding ones are names.
        Variadic: variadic_parameter_declaration has same structure but with
        slice_type or '...' type.
        """
        if params_node is None:
            return []
        params: List[IRParameter] = []
        for child in params_node.named_children:
            if child.type == "parameter_declaration":
                named = child.named_children
                if not named:
                    continue
                # Last named child is the type; all before it are names
                type_node = named[-1]
                name_nodes = named[:-1]
                type_ann = self._text_of(type_node)
                if name_nodes:
                    for n in name_nodes:
                        params.append(
                            IRParameter(
                                name=self._text_of(n),
                                type_annotation=type_ann,
                            )
                        )
                else:
                    # Unnamed parameter (e.g. in interface method signatures)
                    params.append(IRParameter(name="", type_annotation=type_ann))
            elif child.type == "variadic_parameter_declaration":
                named = child.named_children
                type_ann = self._text_of(named[-1]) if named else "..."
                name_nodes = named[:-1] if len(named) > 1 else []
                name = self._text_of(name_nodes[0]) if name_nodes else "..."
                params.append(IRParameter(name=name, type_annotation=f"...{type_ann}"))
        return params

    def _parse_field_list(self, fdl_node: Any) -> List[IRNode]:
        """Parse a field_declaration_list (struct body) into IRAssign stubs."""
        if fdl_node is None:
            return []
        result: List[IRNode] = []
        for child in fdl_node.named_children:
            if child.type == "field_declaration":
                named = child.named_children
                if not named:
                    continue
                # Last named child is the type; all before are field names
                type_node = named[-1]
                type_ann = self._text_of(type_node)
                name_nodes = named[:-1]
                for n in name_nodes:
                    fld = IRAssign(
                        targets=[IRName(id=self._text_of(n))],
                        value=IRConstant(value=None),
                        loc=self._get_location(n),
                        source_language=self.language,
                    )
                    fld._metadata["type_annotation"] = type_ann
                    result.append(fld)
        return result

    def _expr_from_list(self, expr_list_node: Any) -> Optional[Any]:
        """Extract a single expression from an expression_list node."""
        if expr_list_node is None:
            return None
        nc = expr_list_node.named_children
        if not nc:
            return None
        res = self.visit(nc[0])
        return cast(Any, res) if res is not None else None

    # ------------------------------------------------------------------
    # Root
    # ------------------------------------------------------------------

    def visit_source_file(self, node: Any) -> IRModule:
        """Root node of a Go file."""
        body: List[IRNode] = []
        module = IRModule(body=body, source_language=self.language)
        for child in node.named_children:
            if child.type == "package_clause":
                # Record the package name on the module metadata
                for nc in child.named_children:
                    if nc.type == "package_identifier":
                        module._metadata["package"] = self._text_of(nc)
                        break
                continue
            res = self.visit(child)
            if res is None:
                continue
            if isinstance(res, list):
                body.extend(r for r in res if r is not None)
            else:
                body.append(cast(IRNode, res))
        return module

    # ------------------------------------------------------------------
    # Imports
    # ------------------------------------------------------------------

    def visit_import_declaration(self, node: Any) -> Optional[List[IRImport]]:
        """
        import "fmt"
        import ( "fmt"; myfmt "fmt"; _ "os" )

        Handles both single import_spec and grouped import_spec_list.
        """
        imports: List[IRImport] = []
        for child in node.named_children:
            if child.type == "import_spec":
                imp = self._visit_import_spec(child)
                if imp:
                    imports.append(imp)
            elif child.type == "import_spec_list":
                for spec in child.named_children:
                    if spec.type == "import_spec":
                        imp = self._visit_import_spec(spec)
                        if imp:
                            imports.append(imp)
        return imports if imports else None

    def _visit_import_spec(self, node: Any) -> Optional[IRImport]:
        """Parse a single import_spec node."""
        named = node.named_children
        if not named:
            return None
        # Last named child is always the path (interpreted_string_literal)
        path_node = named[-1]
        # Strip surrounding quotes and get module name
        raw = self._text_of(path_node).strip('"')
        # Alias is the first named child if it is package_identifier or blank_identifier
        alias: Optional[str] = None
        if len(named) >= 2:
            alias_node = named[0]
            if alias_node.type in ("package_identifier", "blank_identifier"):
                alias = self._text_of(alias_node)
        return IRImport(
            module=raw,
            names=[],
            alias=alias,
            is_star=False,
            loc=self._get_location(node),
            source_language=self.language,
        )

    # ------------------------------------------------------------------
    # Functions and methods
    # ------------------------------------------------------------------

    def visit_function_declaration(self, node: Any) -> IRFunctionDef:
        """
        func hello() string { return "hi" }
        func add(a, b int) int { return a + b }
        """
        name_node = node.child_by_field_name("name")
        params_node = node.child_by_field_name("parameters")
        result_node = node.child_by_field_name("result")
        body_node = node.child_by_field_name("body")

        name = self._text_of(name_node) if name_node else "unknown"
        params = self._parse_parameters(params_node)
        return_type = self._text_of(result_node) if result_node else None
        body = self._visit_block(body_node)

        return IRFunctionDef(
            name=name,
            params=params,
            body=body,
            return_type=return_type,
            source_language=self.language,
            loc=self._get_location(node),
        )

    def visit_method_declaration(self, node: Any) -> IRFunctionDef:
        """
        func (p Point) Distance() float64 { ... }
        func (p *Point) Scale(f float64) { ... }

        The receiver is stored in metadata["receiver"] for taint tracking.
        """
        receiver_node = node.child_by_field_name("receiver")
        name_node = node.child_by_field_name("name")
        params_node = node.child_by_field_name("parameters")
        result_node = node.child_by_field_name("result")
        body_node = node.child_by_field_name("body")

        name = self._text_of(name_node) if name_node else "unknown"
        params = self._parse_parameters(params_node)
        return_type = self._text_of(result_node) if result_node else None
        body = self._visit_block(body_node)

        fn = IRFunctionDef(
            name=name,
            params=params,
            body=body,
            return_type=return_type,
            source_language=self.language,
            loc=self._get_location(node),
        )
        if receiver_node:
            fn._metadata["receiver"] = self._text_of(receiver_node)
            fn._metadata["kind"] = "method"
        return fn

    # ------------------------------------------------------------------
    # Type declarations (structs + interfaces)
    # ------------------------------------------------------------------

    def visit_type_declaration(self, node: Any) -> Optional[IRClassDef]:
        """
        type Point struct { X, Y float64 }
        type Stringer interface { String() string }
        type MyInt int  (simple alias — skipped)
        """
        for child in node.named_children:
            if child.type == "type_spec":
                return self._visit_type_spec(child)
        return None

    def _visit_type_spec(self, node: Any) -> Optional[IRClassDef]:
        """Parse a type_spec node (name + underlying type)."""
        name_node = node.child_by_field_name("name")
        type_node = node.child_by_field_name("type")
        if name_node is None or type_node is None:
            return None

        name = self._text_of(name_node)
        kind: str
        body: List[IRNode] = []

        if type_node.type == "struct_type":
            kind = "struct"
            fdl = type_node.named_children[0] if type_node.named_children else None
            if fdl and fdl.type == "field_declaration_list":
                body = self._parse_field_list(fdl)

        elif type_node.type == "interface_type":
            kind = "interface"
            # Interface methods become IRFunctionDef stubs in the body
            for elem in type_node.named_children:
                if elem.type == "method_elem":
                    method_name_node = (
                        elem.named_children[0] if elem.named_children else None
                    )
                    params_node = None
                    result_node = None
                    for enc in elem.named_children[1:]:
                        if enc.type == "parameter_list":
                            if params_node is None:
                                params_node = enc
                            else:
                                result_node = enc
                        elif enc.type not in ("parameter_list",):
                            result_node = enc
                    method_name = (
                        self._text_of(method_name_node) if method_name_node else "?"
                    )
                    body.append(
                        IRFunctionDef(
                            name=method_name,
                            params=self._parse_parameters(params_node),
                            body=[],
                            return_type=(
                                self._text_of(result_node) if result_node else None
                            ),
                            source_language=self.language,
                            loc=self._get_location(elem),
                        )
                    )
        else:
            # Simple type alias (type MyInt int) — skip
            return None

        cls = IRClassDef(
            name=name,
            bases=[],
            body=body,
            source_language=self.language,
            loc=self._get_location(node),
        )
        cls._metadata["kind"] = kind
        return cls

    # ------------------------------------------------------------------
    # Variable and constant declarations
    # ------------------------------------------------------------------

    def visit_var_declaration(self, node: Any) -> Optional[List[IRAssign]]:
        """var x int = 5  /  var ( x int; y = "hi" )"""
        results: List[IRAssign] = []
        for child in node.named_children:
            if child.type == "var_spec":
                assigns = self._visit_var_spec(child)
                results.extend(assigns)
        return results if results else None

    def _visit_var_spec(self, node: Any) -> List[IRAssign]:
        """Parse a var_spec: identifier [type] [= expr]"""
        named = node.named_children
        if not named:
            return []
        # named children: identifier(s), optional type_identifier, optional expression_list
        # Collect names until we hit a type or expression_list
        name_nodes: List[Any] = []
        type_node: Optional[Any] = None
        val_node: Optional[Any] = None

        for nc in named:
            if nc.type == "identifier":
                name_nodes.append(nc)
            elif nc.type == "expression_list":
                val_node = nc
            else:
                type_node = nc  # type annotation

        type_ann = self._text_of(type_node) if type_node else None
        val_ir = self._expr_from_list(val_node) if val_node else IRConstant(value=None)

        results: List[IRAssign] = []
        for n in name_nodes:
            a = IRAssign(
                targets=[IRName(id=self._text_of(n))],
                value=cast(Any, val_ir) if val_ir else IRConstant(value=None),
                loc=self._get_location(n),
                source_language=self.language,
            )
            if type_ann:
                a._metadata["type_annotation"] = type_ann
            results.append(a)
        return results

    def visit_const_declaration(self, node: Any) -> Optional[List[IRAssign]]:
        """const Pi = 3.14  /  const ( A = 1; B = 2 )"""
        results: List[IRAssign] = []
        for child in node.named_children:
            if child.type == "const_spec":
                name_node = child.child_by_field_name("name")
                val_node = child.child_by_field_name("value")
                if name_node is None:
                    continue
                val_ir = (
                    self._expr_from_list(val_node)
                    if val_node
                    else IRConstant(value=None)
                )
                a = IRAssign(
                    targets=[IRName(id=self._text_of(name_node))],
                    value=cast(Any, val_ir) if val_ir else IRConstant(value=None),
                    loc=self._get_location(child),
                    source_language=self.language,
                )
                a._metadata["const"] = True
                results.append(a)
        return results if results else None

    def visit_short_var_declaration(self, node: Any) -> Optional[IRAssign]:
        """x := expr  /  x, y := expr1, expr2"""
        left_node = node.child_by_field_name("left")
        right_node = node.child_by_field_name("right")
        # Get the first name from the left expression_list
        name = "?"
        if left_node and left_node.named_children:
            name = self._text_of(left_node.named_children[0])
        val_ir = self._expr_from_list(right_node)
        return IRAssign(
            targets=[IRName(id=name)],
            value=cast(Any, val_ir) if val_ir else IRConstant(value=None),
            loc=self._get_location(node),
            source_language=self.language,
        )

    def visit_assignment_statement(self, node: Any) -> Optional[IRAssign]:
        """x = expr  /  x += expr"""
        left_node = node.child_by_field_name("left")
        right_node = node.child_by_field_name("right")
        name = "?"
        if left_node and left_node.named_children:
            name_res = self.visit(left_node.named_children[0])
            if isinstance(name_res, IRName):
                name = name_res.id
            elif name_res is None:
                name = self._text_of(left_node.named_children[0])
        val_ir = self._expr_from_list(right_node)
        return IRAssign(
            targets=[IRName(id=name)],
            value=cast(Any, val_ir) if val_ir else IRConstant(value=None),
            loc=self._get_location(node),
            source_language=self.language,
        )

    # ------------------------------------------------------------------
    # Statements
    # ------------------------------------------------------------------

    def visit_return_statement(self, node: Any) -> IRReturn:
        """return  /  return expr  /  return x, err"""
        value: Optional[IRExpr] = None
        for child in node.named_children:
            if child.type == "expression_list":
                value = cast(Any, self._expr_from_list(child))
                break
        return IRReturn(
            value=value,
            loc=self._get_location(node),
            source_language=self.language,
        )

    def visit_if_statement(self, node: Any) -> IRIf:
        """
        if cond { ... }
        if cond { ... } else { ... }
        if init; cond { ... }  (init clause stored in metadata)
        """
        cond_node = node.child_by_field_name("condition")
        cons_node = node.child_by_field_name("consequence")
        alt_node = node.child_by_field_name("alternative")

        cond = cast(Any, self.visit(cond_node)) if cond_node else IRConstant(value=True)
        cons = self._visit_block(cons_node)
        # alternative can be a block or another if_statement
        alt: List[IRNode] = []
        if alt_node:
            if alt_node.type == "block":
                alt = self._visit_block(alt_node)
            else:
                res = self.visit(alt_node)
                if res is not None:
                    alt = (
                        [cast(IRNode, res)]
                        if not isinstance(res, list)
                        else cast(List[IRNode], res)
                    )

        return IRIf(
            test=cond,
            body=cons,
            orelse=alt,
            loc=self._get_location(node),
            source_language=self.language,
        )

    def visit_for_statement(self, node: Any) -> IRFor:
        """
        Go's unified loop construct — handles three variants:
          1. for { ... }                            (infinite)
          2. for cond { ... }                       (while-style)
          3. for init; cond; post { ... }           (classic, via for_clause)
          4. for k, v := range collection { ... }  (range, via range_clause)
        """
        body_node = node.child_by_field_name("body")
        body = self._visit_block(body_node)

        for_node = IRFor(
            target=None,
            iter=IRConstant(value=True),
            body=body,
            loc=self._get_location(node),
            source_language=self.language,
        )

        for child in node.named_children:
            if child.type == "for_clause":
                # Classic for loop: init; cond; post
                for_node._metadata["kind"] = "for_clause"
                for_node._metadata["source"] = self._text_of(child)
            elif child.type == "range_clause":
                # for k, v := range collection
                for_node._metadata["kind"] = "range"
                for_node._metadata["source"] = self._text_of(child)
            elif child.type == "binary_expression":
                # while-style: for cond { ... }
                for_node.iter = cast(Any, self.visit(child))

        return for_node

    def visit_break_statement(self, node: Any) -> IRBreak:
        return IRBreak(loc=self._get_location(node), source_language=self.language)

    def visit_continue_statement(self, node: Any) -> IRContinue:
        return IRContinue(loc=self._get_location(node), source_language=self.language)

    def visit_expression_statement(self, node: Any) -> Optional[IRExprStmt]:
        """expr;"""
        for child in node.named_children:
            res = self.visit(child)
            if res is not None and not isinstance(res, list):
                return IRExprStmt(
                    value=cast(Any, res),
                    loc=self._get_location(node),
                    source_language=self.language,
                )
        return None

    def visit_go_statement(self, node: Any) -> Optional[IRExprStmt]:
        """go goroutine() — treat as expression statement."""
        for child in node.named_children:
            res = self.visit(child)
            if res is not None and not isinstance(res, list):
                stmt = IRExprStmt(
                    value=cast(Any, res),
                    loc=self._get_location(node),
                    source_language=self.language,
                )
                stmt._metadata["goroutine"] = True
                return stmt
        return None

    def visit_defer_statement(self, node: Any) -> Optional[IRExprStmt]:
        """defer cleanup() — treat as expression statement."""
        for child in node.named_children:
            res = self.visit(child)
            if res is not None and not isinstance(res, list):
                stmt = IRExprStmt(
                    value=cast(Any, res),
                    loc=self._get_location(node),
                    source_language=self.language,
                )
                stmt._metadata["defer"] = True
                return stmt
        return None

    # ------------------------------------------------------------------
    # Expressions
    # ------------------------------------------------------------------

    def visit_call_expression(self, node: Any) -> IRCall:
        """f(args...)  /  pkg.Func(args...)"""
        func_node = node.child_by_field_name("function")
        args_node = node.child_by_field_name("arguments")
        func = cast(Any, self.visit(func_node)) if func_node else IRName(id="unknown")
        args: List[Any] = []
        if args_node:
            for child in args_node.named_children:
                res = self.visit(child)
                if res is not None and not isinstance(res, list):
                    args.append(cast(Any, res))
        return IRCall(
            func=cast(Any, func),
            args=args,
            loc=self._get_location(node),
            source_language=self.language,
        )

    def visit_binary_expression(self, node: Any) -> IRNode:
        """a + b, x == y, x && y, etc."""
        left_node = node.child_by_field_name("left")
        right_node = node.child_by_field_name("right")
        op_node = node.child_by_field_name("operator")
        op_str = self._text_of(op_node) if op_node else "+"
        op = _BINOP_MAP.get(op_str)
        if op is None:
            # Comparison/logical ops — return raw constant with source text
            return IRConstant(value=self._text_of(node), loc=self._get_location(node))
        left = cast(Any, self.visit(left_node)) if left_node else IRConstant(value=0)
        right = cast(Any, self.visit(right_node)) if right_node else IRConstant(value=0)
        return IRBinaryOp(
            left=left,
            op=op,
            right=right,
            loc=self._get_location(node),
            source_language=self.language,
        )

    def visit_unary_expression(self, node: Any) -> Optional[IRNode]:
        """!x, -x, *ptr, &x, <-ch — descend into operand."""
        operand_node = node.child_by_field_name("operand")
        if operand_node:
            return cast(Any, self.visit(operand_node))
        for child in node.named_children:
            return cast(Any, self.visit(child))
        return None

    def visit_selector_expression(self, node: Any) -> IRName:
        """pkg.Name  /  obj.Field  -> return as dotted IRName."""
        operand_node = node.child_by_field_name("operand")
        field_node = node.child_by_field_name("field")
        base = self._text_of(operand_node) if operand_node else ""
        field = self._text_of(field_node) if field_node else ""
        return IRName(
            id=f"{base}.{field}",
            loc=self._get_location(node),
            source_language=self.language,
        )

    def visit_index_expression(self, node: Any) -> IRName:
        """arr[i]  /  m[key] — return name of the collection."""
        operand_node = node.child_by_field_name("operand")
        name = self._text_of(operand_node) if operand_node else "arr"
        return IRName(
            id=name, loc=self._get_location(node), source_language=self.language
        )

    def visit_parenthesized_expression(self, node: Any) -> Optional[IRNode]:
        """( expr ) — unwrap."""
        for child in node.named_children:
            return cast(Any, self.visit(child))
        return None

    def visit_type_assertion_expression(self, node: Any) -> Optional[IRNode]:
        """x.(Type) — return the operand."""
        for child in node.named_children:
            return cast(Any, self.visit(child))
        return None

    def visit_slice_expression(self, node: Any) -> IRName:
        """s[low:high] — return name of the slice."""
        operand_node = node.child_by_field_name("operand")
        name = self._text_of(operand_node) if operand_node else "slice"
        return IRName(
            id=name, loc=self._get_location(node), source_language=self.language
        )

    # ------------------------------------------------------------------
    # Literals / leaves
    # ------------------------------------------------------------------

    def visit_identifier(self, node: Any) -> IRName:
        return IRName(
            id=self._text_of(node),
            loc=self._get_location(node),
            source_language=self.language,
        )

    def visit_field_identifier(self, node: Any) -> IRName:
        return IRName(
            id=self._text_of(node),
            loc=self._get_location(node),
            source_language=self.language,
        )

    def visit_int_literal(self, node: Any) -> IRConstant:
        text = self._text_of(node)
        try:
            v: Any = int(text, 0)
        except (ValueError, TypeError):
            v = text
        return IRConstant(value=v, loc=self._get_location(node))

    def visit_float_literal(self, node: Any) -> IRConstant:
        text = self._text_of(node)
        try:
            v: Any = float(text)
        except (ValueError, TypeError):
            v = text
        return IRConstant(value=v, loc=self._get_location(node))

    def visit_imaginary_literal(self, node: Any) -> IRConstant:
        return IRConstant(value=self._text_of(node), loc=self._get_location(node))

    def visit_interpreted_string_literal(self, node: Any) -> IRConstant:
        return IRConstant(value=self._text_of(node), loc=self._get_location(node))

    def visit_raw_string_literal(self, node: Any) -> IRConstant:
        return IRConstant(value=self._text_of(node), loc=self._get_location(node))

    def visit_rune_literal(self, node: Any) -> IRConstant:
        return IRConstant(value=self._text_of(node), loc=self._get_location(node))

    def visit_true(self, node: Any) -> IRConstant:
        return IRConstant(value=True, loc=self._get_location(node))

    def visit_false(self, node: Any) -> IRConstant:
        return IRConstant(value=False, loc=self._get_location(node))

    def visit_nil(self, node: Any) -> IRConstant:
        return IRConstant(value=None, loc=self._get_location(node))


# ---------------------------------------------------------------------------
# Normalizer
# ---------------------------------------------------------------------------


class GoNormalizer(BaseNormalizer):
    """
    Normalizes Go source code to Unified IR using tree-sitter-go.

    [20260302_FEATURE] Go language support for:
    - Function and method extraction (extract_code)
    - Struct and interface extraction as IRClassDef
    - Import tracking via IRImport
    - Variable/constant declarations via IRAssign
    - Control flow: if / for (all variants) / break / continue
    - Expression analysis: binary ops, calls, selectors, assignments

    Supported file extensions: .go
    """

    @property
    def language(self) -> str:
        return "go"

    _MAX_CACHE: int = 16
    _tree_cache: Dict[int, Any] = {}

    def __init__(self) -> None:
        self._ts_language = Language(tree_sitter_go.language())  # type: ignore[call-arg]
        self._parser = Parser()
        self._parser.language = self._ts_language
        self._visitor: Optional[GoVisitor] = None

    def normalize(self, source: str, filename: str = "<string>") -> IRModule:
        """Parse Go source and return a Unified IRModule."""
        tree = self._parse_cached(source)
        self._visitor = GoVisitor(source)
        result = self._visitor.visit(tree.root_node)
        module = cast(IRModule, result)
        module._metadata["source_file"] = filename
        return module

    def _parse_cached(self, source: str) -> Any:
        key = hash(source)
        cached = self._tree_cache.get(key)
        if cached is not None:
            return cached
        tree = self._parser.parse(bytes(source, "utf-8"))
        if len(self._tree_cache) >= self._MAX_CACHE:
            self._tree_cache.pop(next(iter(self._tree_cache)))
        self._tree_cache[key] = tree
        return tree

    def normalize_node(self, node: Any) -> Any:
        if self._visitor is None:
            raise RuntimeError("normalize() must be called before normalize_node()")
        return self._visitor.visit(node)
