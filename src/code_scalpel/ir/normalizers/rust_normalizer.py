"""
Rust Normalizer — Converts Rust CST (tree-sitter-rust) to Unified IR.

[20260305_FEATURE] Rust language support for surgical extraction and analysis.

Key Mappings:
    source_file              -> IRModule
    use_declaration          -> IRImport          (use std::collections::HashMap)
    struct_item              -> IRClassDef        (_metadata["kind"]="struct")
    enum_item                -> IRClassDef        (_metadata["kind"]="enum")
    trait_item               -> IRClassDef        (_metadata["kind"]="trait")
    impl_item                -> IRClassDef        (_metadata["kind"]="impl")
    function_item            -> IRFunctionDef     (fn foo(...) -> T)
    function_signature_item  -> IRFunctionDef     (trait fn with no body)
    let_declaration          -> IRAssign          (let mut x: T = expr)
    assignment_expression    -> IRAssign / IRAugAssign
    if_expression            -> IRIf
    if_let_expression        -> IRIf              (_metadata["kind"]="if_let")
    for_expression           -> IRFor
    while_expression         -> IRWhile
    loop_expression          -> IRWhile           (_metadata["kind"]="loop")
    while_let_expression     -> IRWhile           (_metadata["kind"]="while_let")
    match_expression         -> IRIf              (_metadata["kind"]="match")
    return_expression        -> IRReturn
    break_expression         -> IRBreak
    continue_expression      -> IRContinue
    call_expression          -> IRCall
    method_call_expression   -> IRCall
    macro_invocation         -> IRCall            (println!, vec!, panic!, etc.)
    closure_expression       -> IRFunctionDef     (_metadata["kind"]="closure")

Tree-sitter field names used:
    function_item:    name (identifier), parameters, return_type, body (block)
    impl_item:        type (type_identifier), body (declaration_list)
    trait_item:       name (type_identifier), body (declaration_list)
    struct_item:      name (type_identifier), body (field_declaration_list)
    enum_item:        name (type_identifier), body (enum_variant_list)
    for_expression:   pattern (identifier/...), value (iter), body (block)
    let_declaration:  pattern (identifier), type (type_annotation), value (expr)
    parameter:        pattern (identifier), type (type_annotation)
    use_declaration:  argument (scoped_identifier/use_list/identifier)

Rust version: Rust 2021 edition (tree-sitter-rust 0.23+)
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Union, cast

import tree_sitter_rust
from tree_sitter import Language, Parser

from ..nodes import (
    IRAugAssign,
    IRAssign,
    IRBinaryOp,
    IRBoolOp,
    IRBreak,
    IRCall,
    IRClassDef,
    IRCompare,
    IRConstant,
    IRContinue,
    IRFor,
    IRFunctionDef,
    IRIf,
    IRImport,
    IRModule,
    IRName,
    IRNode,
    IRParameter,
    IRReturn,
    IRWhile,
    SourceLocation,
)
from ..operators import AugAssignOperator, BinaryOperator, BoolOperator, CompareOperator
from .base import BaseNormalizer
from .tree_sitter_visitor import TreeSitterVisitor

# ---------------------------------------------------------------------------
# Operator mappings
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

_COMPARE_MAP: Dict[str, CompareOperator] = {
    "==": CompareOperator.EQ,
    "!=": CompareOperator.NE,
    "<": CompareOperator.LT,
    "<=": CompareOperator.LE,
    ">": CompareOperator.GT,
    ">=": CompareOperator.GE,
}

_BOOLOP_MAP: Dict[str, BoolOperator] = {
    "&&": BoolOperator.AND,
    "||": BoolOperator.OR,
}

_AUG_ASSIGN_MAP: Dict[str, AugAssignOperator] = {
    "+=": AugAssignOperator.ADD,
    "-=": AugAssignOperator.SUB,
    "*=": AugAssignOperator.MUL,
    "/=": AugAssignOperator.DIV,
    "%=": AugAssignOperator.MOD,
    "&=": AugAssignOperator.BIT_AND,
    "|=": AugAssignOperator.BIT_OR,
    "^=": AugAssignOperator.BIT_XOR,
    "<<=": AugAssignOperator.LSHIFT,
    ">>=": AugAssignOperator.RSHIFT,
}


# ---------------------------------------------------------------------------
# Visitor
# ---------------------------------------------------------------------------


class RustVisitor(TreeSitterVisitor):
    """Visitor that converts tree-sitter Rust CST nodes to Unified IR.

    [20260305_FEATURE] Handles Rust 2021 edition grammar nodes.
    """

    @property
    def language(self) -> str:
        return "rust"

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

    def _unwrap_single(
        self, result: Union[IRNode, List[IRNode], None]
    ) -> Optional[IRNode]:
        """Unwrap visit() result to a single node, handling lists."""
        if result is None:
            return None
        if isinstance(result, list):
            return result[0] if result else None
        return result

    # ------------------------------------------------------------------
    # Module (root)
    # ------------------------------------------------------------------

    def visit_source_file(self, node: Any) -> IRModule:
        """Top-level Rust source file → IRModule."""
        module = IRModule(
            body=[],
            source_language="rust",
            loc=self._get_location(node),
        )
        for child in node.named_children:
            result = self.visit(child)
            if result is None:
                continue
            elif isinstance(result, list):
                module.body.extend(result)
            else:
                module.body.append(result)
        return module

    # ------------------------------------------------------------------
    # Imports
    # ------------------------------------------------------------------

    def visit_use_declaration(self, node: Any) -> IRImport:
        """use std::... → IRImport."""
        # Get the full text of the use path
        path_text = ""
        # The argument (path) is the first named child that isn't a semicolon
        for child in node.named_children:
            if child.type not in ("attribute_item", "visibility_modifier"):
                path_text = self._get_text(child)
                break
        # Strip braces from use lists for display: use foo::{A, B} → "foo::{A, B}"
        return IRImport(
            module=path_text,
            names=[],
            loc=self._get_location(node),
        )

    # ------------------------------------------------------------------
    # Struct / Enum / Trait / Impl
    # ------------------------------------------------------------------

    def visit_struct_item(self, node: Any) -> IRClassDef:
        """struct Foo { ... } → IRClassDef(_metadata["kind"]="struct")."""
        name_node = node.child_by_field_name("name")
        name = self._get_text(name_node) if name_node else "<struct>"
        body_node = node.child_by_field_name("body")
        body: List[IRNode] = []
        if body_node:
            body = self._visit_block_body(body_node)
        return IRClassDef(
            name=name,
            bases=[],
            body=body,
            loc=self._get_location(node),
            _metadata={"kind": "struct"},
        )

    def visit_enum_item(self, node: Any) -> IRClassDef:
        """enum Color { Red, Green } → IRClassDef(_metadata["kind"]="enum")."""
        name_node = node.child_by_field_name("name")
        name = self._get_text(name_node) if name_node else "<enum>"
        body_node = node.child_by_field_name("body")
        body: List[IRNode] = []
        if body_node:
            body = self._visit_enum_body(body_node)
        return IRClassDef(
            name=name,
            bases=[],
            body=body,
            loc=self._get_location(node),
            _metadata={"kind": "enum"},
        )

    def visit_trait_item(self, node: Any) -> IRClassDef:
        """trait Foo { fn bar(); } → IRClassDef(_metadata["kind"]="trait")."""
        name_node = node.child_by_field_name("name")
        name = self._get_text(name_node) if name_node else "<trait>"
        body_node = node.child_by_field_name("body")
        body: List[IRNode] = []
        if body_node:
            body = self._visit_block_body(body_node)
        return IRClassDef(
            name=name,
            bases=[],
            body=body,
            loc=self._get_location(node),
            _metadata={"kind": "trait"},
        )

    def visit_impl_item(self, node: Any) -> IRClassDef:
        """impl Foo { fn bar() { } } → IRClassDef(_metadata["kind"]="impl")."""
        type_node = node.child_by_field_name("type")
        name = self._get_text(type_node) if type_node else "<impl>"
        # Handle impl Trait for Type
        trait_node = node.child_by_field_name("trait")
        if trait_node:
            trait_name = self._get_text(trait_node)
            name = f"{trait_name} for {name}"
        body_node = node.child_by_field_name("body")
        body: List[IRNode] = []
        if body_node:
            body = self._visit_block_body(body_node)
        return IRClassDef(
            name=name,
            bases=[],
            body=body,
            loc=self._get_location(node),
            _metadata={"kind": "impl"},
        )

    # ------------------------------------------------------------------
    # Functions
    # ------------------------------------------------------------------

    def visit_function_item(self, node: Any) -> IRFunctionDef:
        """fn foo(x: i32) -> i32 { ... } → IRFunctionDef."""
        name_node = node.child_by_field_name("name")
        name = self._get_text(name_node) if name_node else "<fn>"

        params = self._extract_params(node)
        return_type = self._extract_return_type(node)
        body_node = node.child_by_field_name("body")
        body: List[IRNode] = []
        if body_node:
            body = self._visit_block_body(body_node)

        return IRFunctionDef(
            name=name,
            params=params,
            body=body,
            return_type=return_type,
            loc=self._get_location(node),
        )

    def visit_function_signature_item(self, node: Any) -> IRFunctionDef:
        """Trait fn signature without body → IRFunctionDef(body=[])."""
        name_node = node.child_by_field_name("name")
        name = self._get_text(name_node) if name_node else "<fn>"
        params = self._extract_params(node)
        return_type = self._extract_return_type(node)
        return IRFunctionDef(
            name=name,
            params=params,
            body=[],
            return_type=return_type,
            loc=self._get_location(node),
            _metadata={"kind": "signature"},
        )

    def visit_closure_expression(self, node: Any) -> IRFunctionDef:
        """|a, b| expr  or  |a: i32| -> T { body } → IRFunctionDef(kind="closure")."""
        # Parameters are inside the closure_parameters node
        params: List[IRParameter] = []
        for child in node.named_children:
            if child.type == "closure_parameters":
                for p in child.named_children:
                    if p.type in ("identifier", "closure_parameter", "parameter"):
                        p_name = ""
                        if p.type == "identifier":
                            p_name = self._get_text(p)
                        else:
                            id_child = p.child_by_field_name("pattern")
                            if id_child is None:
                                # fall back first named child
                                nc = [
                                    c
                                    for c in p.named_children
                                    if c.type == "identifier"
                                ]
                                id_child = nc[0] if nc else None
                            p_name = self._get_text(id_child) if id_child else "_"
                        if p_name:
                            params.append(IRParameter(name=p_name))
        body: List[IRNode] = []
        for child in node.named_children:
            if child.type == "block":
                body = self._visit_block_body(child)
                break
            elif child.type not in (
                "closure_parameters",
                "type_identifier",
                "primitive_type",
                "generic_type",
                "scoped_type_identifier",
            ):
                result = self.visit(child)
                if result:
                    body = [result] if not isinstance(result, list) else result
        return IRFunctionDef(
            name="<closure>",
            params=params,
            body=body,
            return_type=None,
            loc=self._get_location(node),
            _metadata={"kind": "closure"},
        )

    # ------------------------------------------------------------------
    # Variable declarations
    # ------------------------------------------------------------------

    def visit_let_declaration(self, node: Any) -> IRAssign:
        """let [mut] x: T = expr → IRAssign."""
        # pattern is the variable name (can be identifier, tuple pattern, etc.)
        pattern_node = node.child_by_field_name("pattern")
        target_name = self._get_text(pattern_node) if pattern_node else "_"
        # Handle mutable specifier — it appears as a named child before pattern
        # target may include mut in name, use plain identifier
        if pattern_node is None:
            for c in node.named_children:
                if c.type == "identifier":
                    target_name = self._get_text(c)
                    break
        target = IRName(id=target_name, loc=self._get_location(pattern_node or node))
        value_node = node.child_by_field_name("value")
        value: IRNode
        if value_node:
            visited = self.visit(value_node)
            value = visited if visited is not None else IRConstant(value=None)
        else:
            value = IRConstant(value=None)
        return IRAssign(
            targets=[target],
            value=value,
            loc=self._get_location(node),
        )

    def visit_assignment_expression(self, node: Any) -> IRAssign:
        """x = expr → IRAssign."""
        children = node.named_children
        if len(children) >= 2:
            left_node = children[0]
            right_node = children[-1]
            left = self.visit(left_node) or IRName(id=self._get_text(left_node))
            right = self.visit(right_node) or IRConstant(value=None)
            return IRAssign(
                targets=[left],
                value=right,
                loc=self._get_location(node),
            )
        return IRAssign(
            targets=[], value=IRConstant(value=None), loc=self._get_location(node)
        )

    def visit_compound_assignment_expr(self, node: Any) -> IRAugAssign:
        """x += expr → IRAugAssign."""
        children = node.named_children
        # operator is an unnamed child between named children
        op_text = None
        for child in node.children:
            if not child.is_named:
                txt = self._get_text(child)
                if txt in _AUG_ASSIGN_MAP:
                    op_text = txt
                    break
        if len(children) >= 2 and op_text:
            left_node = children[0]
            right_node = children[-1]
            left = self.visit(left_node) or IRName(id=self._get_text(left_node))
            right = self.visit(right_node) or IRConstant(value=None)
            return IRAugAssign(
                target=left,
                op=_AUG_ASSIGN_MAP[op_text],
                value=right,
                loc=self._get_location(node),
            )
        return IRAugAssign(
            target=IRName(id="_"),
            op=AugAssignOperator.ADD,
            value=IRConstant(value=None),
            loc=self._get_location(node),
        )

    # ------------------------------------------------------------------
    # Control flow
    # ------------------------------------------------------------------

    def visit_if_expression(self, node: Any) -> IRIf:
        """if cond { ... } [else { ... }] → IRIf."""
        condition_node = node.child_by_field_name("condition")
        consequence_node = node.child_by_field_name("consequence")
        alternative_node = node.child_by_field_name("alternative")

        condition: IRNode = IRConstant(value=None)
        if condition_node:
            visited = self.visit(condition_node)
            if visited:
                condition = visited
            else:
                condition = IRName(id=self._get_text(condition_node))

        body: List[IRNode] = []
        if consequence_node:
            body = self._visit_block_body(consequence_node)

        orelse: List[IRNode] = []
        if alternative_node:
            # else_clause contains the else branch (block or another if_expression)
            for child in alternative_node.named_children:
                result = self.visit(child)
                if result is not None:
                    orelse = result if isinstance(result, list) else [result]
                    break
            if not orelse:
                orelse = self._visit_block_body(alternative_node)

        return IRIf(
            test=condition,
            body=body,
            orelse=orelse,
            loc=self._get_location(node),
        )

    def visit_if_let_expression(self, node: Any) -> IRIf:
        """if let Some(x) = expr { ... } → IRIf(_metadata["kind"]="if_let")."""
        return IRIf(
            test=IRName(id=self._get_text(node)[:30]),
            body=self._collect_body_from_blocks(node),
            orelse=[],
            loc=self._get_location(node),
            _metadata={"kind": "if_let"},
        )

    def visit_for_expression(self, node: Any) -> IRFor:
        """for i in iter { ... } → IRFor."""
        pattern_node = node.child_by_field_name("pattern")
        value_node = node.child_by_field_name("value")
        body_node = node.child_by_field_name("body")

        target_name = self._get_text(pattern_node) if pattern_node else "_"
        target = IRName(id=target_name, loc=self._get_location(pattern_node))

        iter_expr: IRNode = IRConstant(value=None)
        if value_node:
            visited = self.visit(value_node)
            iter_expr = visited or IRName(id=self._get_text(value_node))

        body: List[IRNode] = []
        if body_node:
            body = self._visit_block_body(body_node)

        return IRFor(
            target=target,
            iter=iter_expr,
            body=body,
            orelse=[],
            loc=self._get_location(node),
        )

    def visit_while_expression(self, node: Any) -> IRWhile:
        """while cond { ... } → IRWhile."""
        condition_node = node.child_by_field_name("condition")
        body_node = node.child_by_field_name("body")

        test: IRNode = IRConstant(value=True)
        if condition_node:
            visited = self.visit(condition_node)
            test = visited or IRName(id=self._get_text(condition_node))

        body: List[IRNode] = []
        if body_node:
            body = self._visit_block_body(body_node)

        return IRWhile(
            test=test,
            body=body,
            orelse=[],
            loc=self._get_location(node),
        )

    def visit_while_let_expression(self, node: Any) -> IRWhile:
        """while let Some(x) = iter { ... } → IRWhile(_metadata["kind"]="while_let")."""
        body: List[IRNode] = []
        for child in node.named_children:
            if child.type == "block":
                body = self._visit_block_body(child)
                break
        return IRWhile(
            test=IRName(id=self._get_text(node)[:30]),
            body=body,
            orelse=[],
            loc=self._get_location(node),
            _metadata={"kind": "while_let"},
        )

    def visit_loop_expression(self, node: Any) -> IRWhile:
        """loop { ... } → IRWhile(_metadata["kind"]="loop")."""
        body_node = node.child_by_field_name("body")
        body: List[IRNode] = []
        if body_node:
            body = self._visit_block_body(body_node)
        return IRWhile(
            test=IRConstant(value=True),
            body=body,
            orelse=[],
            loc=self._get_location(node),
            _metadata={"kind": "loop"},
        )

    def visit_match_expression(self, node: Any) -> IRIf:
        """match x { arm1, arm2 } → IRIf(_metadata["kind"]="match")."""
        value_node = node.child_by_field_name("value")
        subject: IRNode = IRConstant(value=None)
        if value_node:
            visited = self.visit(value_node)
            subject = visited or IRName(id=self._get_text(value_node))

        body_node = node.child_by_field_name("body")
        arms: List[IRNode] = []
        if body_node:
            arms = self._visit_block_body(body_node)

        return IRIf(
            test=subject,
            body=arms,
            orelse=[],
            loc=self._get_location(node),
            _metadata={"kind": "match"},
        )

    # ------------------------------------------------------------------
    # Return / break / continue
    # ------------------------------------------------------------------

    def visit_return_expression(self, node: Any) -> IRReturn:
        """return expr → IRReturn."""
        value: Optional[IRNode] = None
        for child in node.named_children:
            value = self.visit(child)
            if value:
                break
        return IRReturn(value=value, loc=self._get_location(node))

    def visit_break_expression(self, node: Any) -> IRBreak:
        """break [label] → IRBreak."""
        return IRBreak(loc=self._get_location(node))

    def visit_continue_expression(self, node: Any) -> IRContinue:
        """continue [label] → IRContinue."""
        return IRContinue(loc=self._get_location(node))

    # ------------------------------------------------------------------
    # Calls and macros
    # ------------------------------------------------------------------

    def visit_call_expression(self, node: Any) -> IRCall:
        """foo(args) → IRCall."""
        func_node = node.child_by_field_name("function")
        args_node = node.child_by_field_name("arguments")

        func_name = self._get_text(func_node) if func_node else "<call>"
        args: List[IRNode] = []
        if args_node:
            for arg in args_node.named_children:
                visited = self.visit(arg)
                if visited:
                    args.append(visited)

        return IRCall(
            func=IRName(id=func_name),
            args=args,
            loc=self._get_location(node),
        )

    def visit_method_call_expression(self, node: Any) -> IRCall:
        """obj.method(args) → IRCall."""
        receiver_node = node.child_by_field_name("receiver")
        name_node = node.child_by_field_name("name")
        args_node = node.child_by_field_name("arguments")

        receiver = self._get_text(receiver_node) if receiver_node else ""
        method = self._get_text(name_node) if name_node else "<method>"
        full_name = f"{receiver}.{method}" if receiver else method

        args: List[IRNode] = []
        if args_node:
            for arg in args_node.named_children:
                visited = self.visit(arg)
                if visited:
                    args.append(visited)

        return IRCall(
            func=IRName(id=full_name),
            args=args,
            loc=self._get_location(node),
        )

    def visit_macro_invocation(self, node: Any) -> IRCall:
        """println!(...) / vec![...] / panic!(...) → IRCall."""
        # Macro path is the first named child of type identifier/scoped_identifier
        macro_name = "<macro>"
        for child in node.named_children:
            if child.type in ("identifier", "scoped_identifier"):
                macro_name = self._get_text(child) + "!"
                break
        return IRCall(
            func=IRName(id=macro_name),
            args=[],
            loc=self._get_location(node),
        )

    # ------------------------------------------------------------------
    # Expressions (literals, identifiers, binops)
    # ------------------------------------------------------------------

    def visit_identifier(self, node: Any) -> IRName:
        return IRName(id=self._get_text(node), loc=self._get_location(node))

    def visit_self(self, node: Any) -> IRName:
        return IRName(id="self", loc=self._get_location(node))

    def visit_integer_literal(self, node: Any) -> IRConstant:
        text = self._get_text(node)
        try:
            return IRConstant(
                value=int(
                    text.replace("_", "").rstrip("uUiI0123456789").rstrip("uUiI")
                    or text
                ),
                loc=self._get_location(node),
            )
        except ValueError:
            return IRConstant(value=text, loc=self._get_location(node))

    def visit_float_literal(self, node: Any) -> IRConstant:
        text = self._get_text(node)
        try:
            return IRConstant(
                value=float(text.replace("_", "").rstrip("f3264")),
                loc=self._get_location(node),
            )
        except ValueError:
            return IRConstant(value=text, loc=self._get_location(node))

    def visit_string_literal(self, node: Any) -> IRConstant:
        return IRConstant(value=self._get_text(node), loc=self._get_location(node))

    def visit_raw_string_literal(self, node: Any) -> IRConstant:
        return IRConstant(value=self._get_text(node), loc=self._get_location(node))

    def visit_boolean_literal(self, node: Any) -> IRConstant:
        text = self._get_text(node)
        return IRConstant(value=(text == "true"), loc=self._get_location(node))

    def visit_binary_expression(self, node: Any) -> IRNode:
        """x + y  /  x == y  /  x && y → IRBinaryOp / IRCompare / IRBoolOp."""
        children = node.named_children
        op_text = None
        for child in node.children:
            if not child.is_named:
                txt = self._get_text(child).strip()
                if txt:
                    op_text = txt
                    break

        if len(children) < 2:
            return IRName(id=self._get_text(node))

        left = cast(Any, self._unwrap_single(self.visit(children[0]))) or IRName(
            id=self._get_text(children[0])
        )
        right = cast(Any, self._unwrap_single(self.visit(children[-1]))) or IRName(
            id=self._get_text(children[-1])
        )

        if op_text in _COMPARE_MAP:
            return IRCompare(
                left=left,
                ops=[_COMPARE_MAP[op_text]],
                comparators=[right],
                loc=self._get_location(node),
            )
        if op_text in _BOOLOP_MAP:
            return IRBoolOp(
                op=_BOOLOP_MAP[op_text],
                values=[left, right],
                loc=self._get_location(node),
            )
        if op_text in _BINOP_MAP:
            return IRBinaryOp(
                left=left,
                op=_BINOP_MAP[op_text],
                right=right,
                loc=self._get_location(node),
            )
        return IRBinaryOp(
            left=left,
            op=BinaryOperator.ADD,
            right=right,
            loc=self._get_location(node),
        )

    def visit_unary_expression(self, node: Any) -> IRNode:
        """! x / - x / * x → pass through to child."""
        for child in node.named_children:
            result = self._unwrap_single(self.visit(child))
            if result:
                return result
        return IRName(id=self._get_text(node))

    def visit_reference_expression(self, node: Any) -> IRNode:
        """&x / &mut x → pass through to inner expression."""
        for child in node.named_children:
            result = self._unwrap_single(self.visit(child))
            if result:
                return result
        return IRName(id=self._get_text(node))

    def visit_field_expression(self, node: Any) -> IRName:
        """obj.field → IRName."""
        return IRName(id=self._get_text(node), loc=self._get_location(node))

    def visit_index_expression(self, node: Any) -> IRName:
        """arr[i] → IRName."""
        return IRName(id=self._get_text(node), loc=self._get_location(node))

    def visit_try_expression(self, node: Any) -> IRNode:
        """expr? → pass through to inner expr."""
        for child in node.named_children:
            result = self._unwrap_single(self.visit(child))
            if result:
                return result
        return IRName(id=self._get_text(node))

    def visit_await_expression(self, node: Any) -> IRNode:
        """expr.await → pass through."""
        for child in node.named_children:
            result = self._unwrap_single(self.visit(child))
            if result:
                return result
        return IRName(id=self._get_text(node))

    def visit_type_cast_expression(self, node: Any) -> IRNode:
        """expr as Type → pass through."""
        value_node = node.child_by_field_name("value")
        if value_node:
            result = self._unwrap_single(self.visit(value_node))
            if result:
                return result
        return IRName(id=self._get_text(node))

    # ------------------------------------------------------------------
    # Expression statements (unwrap)
    # ------------------------------------------------------------------

    def visit_expression_statement(self, node: Any) -> Optional[IRNode]:
        """Transparent wrapper — visit the inner expression."""
        for child in node.named_children:
            result = self._unwrap_single(self.visit(child))
            if result is not None:
                return result
        return None

    def visit_block(self, node: Any) -> List[IRNode]:
        """Inline block → list of statements."""
        return self._visit_block_body(node)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _visit_block_body(self, node: Any) -> List[IRNode]:
        """Walk the named children of a block/declaration_list and collect IR."""
        stmts: List[IRNode] = []
        for child in node.named_children:
            result = self.visit(child)
            if result is None:
                continue
            elif isinstance(result, list):
                stmts.extend(result)
            else:
                stmts.append(result)
        return stmts

    def _visit_enum_body(self, node: Any) -> List[IRNode]:
        """Walk enum variants and collect as IRAssign stubs."""
        stmts: List[IRNode] = []
        for child in node.named_children:
            if child.type == "enum_variant":
                name_child = child.child_by_field_name("name")
                if name_child is None:
                    for c in child.named_children:
                        if c.type == "identifier":
                            name_child = c
                            break
                if name_child:
                    stmts.append(
                        IRAssign(
                            targets=[IRName(id=self._get_text(name_child))],
                            value=IRConstant(value=None),
                            loc=self._get_location(child),
                        )
                    )
        return stmts

    def _extract_params(self, node: Any) -> List[IRParameter]:
        """Extract parameters from a function_item or function_signature_item."""
        params: List[IRParameter] = []
        params_node = node.child_by_field_name("parameters")
        if params_node is None:
            return params
        for child in params_node.named_children:
            if child.type in ("parameter", "self_parameter"):
                if child.type == "self_parameter":
                    params.append(IRParameter(name="self"))
                    continue
                # parameter: pattern (identifier), type
                pattern_node = child.child_by_field_name("pattern")
                if pattern_node is None:
                    for c in child.named_children:
                        if c.type == "identifier":
                            pattern_node = c
                            break
                p_name = self._get_text(pattern_node) if pattern_node else "_"
                params.append(IRParameter(name=p_name))
            elif child.type == "self":
                params.append(IRParameter(name="self"))
        return params

    def _extract_return_type(self, node: Any) -> Optional[str]:
        """Extract return type from a function_item, if present."""
        ret_node = node.child_by_field_name("return_type")
        if ret_node:
            return self._get_text(ret_node)
        return None

    def _collect_body_from_blocks(self, node: Any) -> List[IRNode]:
        """Collect body from any block child recursively."""
        for child in node.named_children:
            if child.type == "block":
                return self._visit_block_body(child)
        return []


# ---------------------------------------------------------------------------
# Normalizer (public interface)
# ---------------------------------------------------------------------------


class RustNormalizer(BaseNormalizer):
    """Normalizer that converts Rust source code to Unified IR.

    [20260305_FEATURE] Uses tree-sitter-rust grammar for full CST parsing.

    Usage:
        normalizer = RustNormalizer()
        ir_module = normalizer.normalize(rust_source_code)
    """

    def __init__(self) -> None:
        self._ts_language = Language(tree_sitter_rust.language())
        self._parser = Parser(self._ts_language)

    @property
    def language(self) -> str:
        return "rust"

    def normalize(self, source: str, filename: str = "<string>") -> IRModule:
        """
        Parse Rust source code and return a Unified IR module.

        Args:
            source: Rust source code as a string.
            filename: Optional filename for error reporting.

        Returns:
            IRModule containing the full IR representation.
        """
        if not source or not source.strip():
            return IRModule(body=[], source_language="rust")

        tree = self._parser.parse(source.encode("utf-8"))
        visitor = RustVisitor(source=source)
        result = visitor.visit(tree.root_node)

        # Normalize the result to an IRModule
        if isinstance(result, IRModule):
            module = result
        elif isinstance(result, list):
            module = IRModule(body=result, source_language="rust")
        else:
            module = IRModule(body=[], source_language="rust")

        if hasattr(module, "_metadata"):
            module._metadata["source_file"] = filename
        return module

    def normalize_node(self, node: Any) -> None:
        """[20260305_FEATURE] Node-level dispatch handled by visitor traversal."""
        return None
